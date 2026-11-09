"""Respaldo de cuotas de FÚTBOL para la consulta (decisión del titular, 9-nov-2026): PropLine -> The Odds API ->
SportsAPIPro.

Solo alimenta la LECTURA de cuotas de casas que ve el usuario (`partido_mercados.cuotas_casas`). El motor, los
picks, la escalera y la alta probabilidad siguen leyendo `odds_snapshots` con `source = 'propline'`: aquí no se
escribe en esa tabla (es inmutable y la leen los sellados), sino en una caché JSON aparte, igual que NBA y tenis.

Hueco = partido programado de una liga activa que empieza en las próximas 36 h y al que PropLine no le dio cuota
de 1X2 de ninguna casa de los suscriptores. Un hueco se resuelve así:
  1. The Odds API, cuota ACTUAL (no histórica) de la liga entera: 1 petición por liga con hueco, coste
     mercados x regiones (`_markets_for` decide los mercados, como en el worker histórico). Comparte clave,
     suelo y tope diario con el respaldo de NBA/tenis.
  2. SportsAPIPro, si el nivel 1 no lo resolvió (sin clave, sin créditos, tope diario o evento no encontrado):
     una petición por partido (1X2 y totales), con el id del partido tomado del calendario ya archivado por el
     módulo del once (cero peticiones extra para el calendario).
Cada hueco se reintenta como mucho `INTENTOS_MAX` veces por nivel y bloque de 6 h, y la cuota de una entrada deja de
servir pasadas 6 h (la misma edad máxima que usa `cuotas_casas` con PropLine).
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qf.config import settings
from qf.db import query
from qf.ingest import cuotas_respaldo as cr
from qf.ingest import cuotas_sportsapipro as csp
from qf.ingest import cuotas_therundown as crd

log = logging.getLogger(__name__)
VENTANA = timedelta(hours=36)
EDAD_MAX = timedelta(hours=6)          # misma que `partido_mercados.EDAD_MAX_CUOTA`
BLOQUE = timedelta(hours=6)
SRC_O, SRC_S, SRC_R = "the-odds-api", "sportsapipro", "therundown"
NOMBRE_CASA_SP = "sofascore"


def _sp():
    from qf.ingest import sportsapipro_alineaciones as sp   # perezoso: arrastra la base de datos (ver cuotas_sportsapipro)
    return sp


def ruta_cache(cache_path=None) -> Path | None:
    base = cache_path if cache_path is not None else getattr(settings, "cuotas_respaldo_cache", None)
    return Path(base).with_name("cuotas_respaldo_futbol.json") if base else None


# --- caché (la API solo lee) ---------------------------------------------------------------------------------

_lectura: dict = {}


def leer_cache(path) -> dict:
    """{match_id: entrada}; ausente o ilegible -> {}. Se relee solo si el archivo cambió (la usa la API)."""
    if not path:
        return {}
    try:
        mt = os.stat(path).st_mtime_ns
        previo = _lectura.get(str(path))
        if previo and previo[0] == mt:
            return previo[1]
        doc = json.loads(Path(path).read_bytes())
        entries = doc.get("entries") if isinstance(doc, dict) else None
        entries = entries if isinstance(entries, dict) else {}
        _lectura[str(path)] = (mt, entries)
        return entries
    except (OSError, ValueError):
        return {}


def escribir_cache(path, entries: Mapping, now: datetime) -> None:
    vivas = {}
    for k, e in entries.items():
        try:
            # TheRundown Free: la licencia no permite guardar sus datos más de 24 h.
            limite = timedelta(hours=24) if k.endswith(SUFIJO_RD) else timedelta(days=2)
            if pl_time(e["captured_at"]) >= now - limite:
                vivas[k] = e
        except Exception:  # noqa: BLE001
            continue
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + ".tmp")
    tmp.write_text(json.dumps(dict(generated_at=now.isoformat(), entries=vivas), separators=(",", ":"),
                              ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, destino)
    _lectura.pop(str(destino), None)


def pl_time(texto) -> datetime:
    from qf.ingest import propline_shared as pl
    return pl.parse_time(texto)


SUFIJO_SP = "|sp"
SUFIJO_RD = "|rd"
CLAVES_1X2 = {"h2h:home:None", "h2h:draw:None", "h2h:away:None"}


def _mejores(e: Mapping, hasta: datetime, soft_books, canonical) -> dict:
    try:
        t = pl_time(e["captured_at"])
    except Exception:  # noqa: BLE001
        return {}
    if t > hasta or hasta - t > EDAD_MAX:
        return {}
    if e.get("fuente") == SRC_R and not crd.mostrar():
        return {}
    out: dict = {}
    for r in e.get("rows") or []:
        try:
            casa = canonical(str(r["bookmaker"]))
            if e.get("fuente") not in (SRC_S, SRC_R) and casa not in soft_books:
                continue
            clave = f"{r['market']}:{r['selection']}:{None if r.get('line') is None else float(r['line']) + 0.0}"
            cand = (float(r["price"]), casa, t)
        except (KeyError, TypeError, ValueError):
            continue
        actual = out.get(clave)
        if actual is None or (-cand[0], cand[1]) < (-actual[0], actual[1]):
            out[clave] = cand
    return out


def cuotas_de_cache(entradas: Mapping, match_id: str, hasta: datetime, soft_books, canonical) -> dict:
    """Mejor cuota por clave `market:selection:line` de las entradas vigentes del partido, como `cuotas_casas`:
    `clave -> (cuota, casa, hora de captura)`. The Odds API respeta las casas de los suscriptores y gana donde
    cotiza; SportsAPIPro (entrada `<id>|sp`) trae una sola casa sin identificar y solo rellena lo que falte."""
    out = _mejores(entradas.get(match_id) or {}, hasta, soft_books, canonical)
    for sufijo in (SUFIJO_SP, SUFIJO_RD):
        for clave, cand in _mejores(entradas.get(match_id + sufijo) or {}, hasta, soft_books, canonical).items():
            out.setdefault(clave, cand)
    return out


# --- huecos --------------------------------------------------------------------------------------------------

def huecos(now: datetime, *, propline_ok=None) -> list[dict]:
    """Partidos que empiezan en las próximas 36 h sin cuota de 1X2 de PropLine para los suscriptores."""
    from qf.api import partido_mercados as pm
    filas = query("""SELECT m.match_id, m.league_id, m.kickoff_utc, l.odds_api_key
                     FROM matches m JOIN leagues l ON l.league_id = m.league_id AND l.active
                     WHERE m.status = 'scheduled' AND m.kickoff_utc > %s AND m.kickoff_utc <= %s
                     ORDER BY m.kickoff_utc""", (now, now + VENTANA))
    ok = propline_ok or (lambda mid: {"h2h:home:None", "h2h:draw:None", "h2h:away:None"} <= set(pm.cuotas_casas(mid)))
    return [dict(f) for f in filas if not ok(f["match_id"])]


def _bloque(now: datetime) -> str:
    return str(int(now.timestamp() // BLOQUE.total_seconds()))


def _filas_odds_api(ev: dict, match_id: str, now: datetime, kickoff: datetime) -> list[dict]:
    from qf.ingest import odds_worker as ow
    return [dict(bookmaker=r[1], market=r[2], selection=r[3], line=r[4], price=r[5])
            for r in ow._parse_event(ev, match_id, "respaldo", now, kickoff)]


def nivel2(cli: "cr.Cliente", pend: list[dict], entries: dict, intentos: dict, now: datetime, regiones: str,
           salida=print) -> int:
    """The Odds API, cuota actual: una petición por liga con hueco."""
    from qf.ingest import odds_worker as ow
    por_liga: dict[str, list[dict]] = {}
    for h in pend:
        if h.get("odds_api_key") and cr.intento_permitido(intentos, f"fut|{h['match_id']}|{_bloque(now)}", 2, now):
            por_liga.setdefault(h["odds_api_key"], []).append(h)
    nuevas = 0
    for sport_key, hs in por_liga.items():
        mercados = ow._markets_for(sport_key)
        coste = len(mercados.split(",")) * len(regiones.split(","))
        eventos = cli.eventos_actuales(sport_key, mercados, regiones, coste)   # puede lanzar Parar
        for h in hs:
            cr.marca_intento(intentos, f"fut|{h['match_id']}|{_bloque(now)}", 2, now)
        if not eventos:
            continue
        meta = ow.match_meta([h["match_id"] for h in hs])
        for ev, match_id in ow.match_events(eventos, meta):
            filas = _filas_odds_api(ev, match_id, now, meta[match_id]["kickoff_utc"])
            if filas:
                entries[match_id] = dict(fuente=SRC_O, captured_at=now.isoformat(), rows=filas)
                nuevas += 1
    return nuevas


def _filas_sportsapipro(ms: list[dict]) -> list[dict]:
    return csp.filas_futbol(ms)


def nivel3(cli: "csp.Cliente", pend: list[dict], entries: dict, intentos: dict, now: datetime, db, salida=print) -> int:
    nuevas = 0
    for h in pend:
        k = f"fut|{h['match_id']}|{_bloque(now)}"
        previa = entries.get(h["match_id"] + SUFIJO_SP)
        if (previa and now - pl_time(previa["captured_at"]) <= EDAD_MAX) or not cr.intento_permitido(intentos, k, 3, now):
            continue
        eid = _sp().event_id(db, h) if db is not None else None
        if eid is None:
            continue                        # sin calendario archivado no se gasta ninguna petición
        try:
            recibido, doc = cli.get(f"football/api/match/{eid}/odds/pre-match", "cuotas_futbol", str(eid))
        except csp.SinCupo as e:
            salida(f"sportsapipro (fútbol): {e}")
            break
        cr.marca_intento(intentos, k, 3, now)
        filas = _filas_sportsapipro(csp.mercados(doc)) if doc else []
        if filas:
            entries[h["match_id"] + SUFIJO_SP] = dict(fuente=SRC_S, captured_at=recibido.isoformat(), rows=filas)
            nuevas += 1
    return nuevas


def _resolutor_equipos():
    """nombre de TheRundown -> nombre canónico propio, solo por alias EXACTO (no registra nada en `unresolved_names`)."""
    from qf.db import query_one
    from qf.normalize import match_team

    def canon(nombre):
        for fuente in ("odds_api", "propline", "fotmob", "sofascore"):
            tid, _, score = match_team(nombre, fuente)
            if tid and score >= 100.0:
                fila = query_one("SELECT canonical_name FROM teams WHERE team_id = %s", (tid,))
                if fila:
                    return fila["canonical_name"]
        return None

    def igual(nombre_rd, canonico):
        return crd.norm(nombre_rd) == crd.norm(canonico) or (canon(nombre_rd) or "") == canonico
    return igual


def nivel4(cli: "crd.Cliente", pend: list[dict], entries: dict, intentos: dict, now: datetime, meta: dict,
           igual, salida=print) -> int:
    """TheRundown: un calendario por liga y fecha UTC. Solo ligas de su catálogo; 1X2, hándicap y totales."""
    nuevas, memo = 0, {}
    for h in pend:
        k = f"fut|{h['match_id']}|{_bloque(now)}"
        sid = crd.SPORT_FUTBOL.get(h.get("odds_api_key") or "")
        previa = entries.get(h["match_id"] + SUFIJO_RD)
        if (sid is None or h["match_id"] not in meta or not cr.intento_permitido(intentos, k, 4, now)
                or (previa and now - pl_time(previa["captured_at"]) <= EDAD_MAX)):
            continue
        fecha = h["kickoff_utc"].astimezone(timezone.utc).date().isoformat()
        try:
            if (sid, fecha) not in memo:
                memo[(sid, fecha)] = cli.eventos(sid, fecha)
        except crd.SinCupo as e:
            salida(f"therundown (fútbol): {e}")
            break
        cr.marca_intento(intentos, k, 4, now)
        m = meta[h["match_id"]]
        ev = crd.busca_evento(memo[(sid, fecha)], m["home"], m["away"], h["kickoff_utc"], tenis=False, resuelve=igual)
        filas = crd.filas_futbol(ev, m["home"], m["away"], igual) if ev else []
        if filas:
            entries[h["match_id"] + SUFIJO_RD] = dict(fuente=SRC_R, captured_at=now.isoformat(), rows=filas)
            nuevas += 1
    return nuevas


def correr(*, ejecutar=False, max_creditos=cr.MAX_CREDITOS, get=None, now=None, salida=print, key=None, sp_key=None,
           sp_call=None, sp_raiz=None, cache_path=None, info=None, lista_huecos=None, regiones=None, rd_key=None,
           rd_call=None, rd_sleep=None, resolutor=None) -> dict:
    now = now or datetime.now(timezone.utc)
    key = key if key is not None else getattr(settings, "odds_api_respaldo_key", None)
    sp_key = sp_key if sp_key is not None else getattr(settings, "sportsapipro_key", None)
    cache = ruta_cache(cache_path if cache_path is not None else None)
    rd_key = rd_key if rd_key is not None else getattr(settings, "therundown_key", None)
    if cache is None or not (key or sp_key or rd_key):
        return {"estado": "sin_configuracion"}
    entries = dict(leer_cache(cache))
    from qf.publish.picks import canonical_book
    soft = tuple(getattr(settings, "soft_books", ()))

    def cubierto(h) -> bool:
        return CLAVES_1X2 <= set(cuotas_de_cache(entries, h["match_id"], now, soft, canonical_book))
    # Un partido con la cuota ya servida por una entrada vigente deja de ser hueco.
    pend = [h for h in (lista_huecos if lista_huecos is not None else huecos(now)) if not cubierto(h)]
    salida(f"fútbol: {len(pend)} partidos sin cuota de PropLine")
    if not ejecutar or not pend:
        return {"estado": "seco" if not ejecutar else "sin_huecos", "huecos": len(pend)}
    intentos = cr.leer_intentos(cache)
    n2 = n3 = 0
    cli = cr.Cliente(get or cr._transporte(key or ""), cr.Presupuesto(max_creditos), regiones or settings.odds_api_regions)
    if key and max_creditos > 0:
        try:
            cli.saldo()
            n2 = nivel2(cli, pend, entries, intentos, now, regiones or settings.odds_api_regions, salida)
        except cr.Parar as e:
            salida(f"parado: {e} (lo que falte pasa a SportsAPIPro)")
    cli3 = None
    if sp_key:
        raiz = sp_raiz if sp_raiz is not None else (
            Path(settings.artifact_dir) / "sportsapipro_cuotas" if getattr(settings, "artifact_dir", None) else None)
        cli3 = csp.Cliente(sp_key, call=sp_call, clock=lambda: now, raiz=raiz,
                           tope=int(getattr(settings, "cuotas_sportsapipro_diario", 0) or 0))
        db = None
        try:
            db = _sp().abrir(_sp().carpeta())     # calendario archivado por el módulo del once; solo se lee
        except Exception:  # noqa: BLE001
            log.warning("respaldo fútbol: sin índice de calendario de SportsAPIPro")
        # Nivel 3: lo que, tras el nivel 2, la ficha seguiría sin poder mostrar (casas que no son de los suscriptores
        # no cuentan).
        n3 = nivel3(cli3, [h for h in pend if not cubierto(h)], entries, intentos, now, db, salida)
    n4, cli4 = 0, None
    if rd_key:
        from qf.ingest import odds_worker as ow
        cli4 = crd.Cliente(rd_key, call=rd_call, reserva=int(getattr(settings, "cuotas_therundown_reserva", crd.RESERVA)),
                           **({"sleep": rd_sleep} if rd_sleep else {}))
        candidatos = [h for h in pend if not cubierto(h)]
        meta = ow.match_meta([h["match_id"] for h in candidatos]) if candidatos else {}
        n4 = nivel4(cli4, candidatos, entries, intentos, now, meta, resolutor or _resolutor_equipos(), salida)
    if n2 or n3 or n4:
        escribir_cache(cache, entries, now)
    if intentos:
        try:
            cr.escribir_intentos(cache, intentos, now)
        except OSError:
            log.exception("respaldo fútbol: no se pudo guardar el registro de intentos")
    out = dict(estado="ok", huecos=len(pend), the_odds_api=n2, sportsapipro=n3, therundown=n4, gastado=cli.p.gastado,
               saldo=cli.p.saldo, peticiones_sportsapipro=cli3.peticiones if cli3 else 0,
               peticiones_therundown=cli4.peticiones if cli4 else 0, puntos_therundown=cli4.puntos if cli4 else 0)
    if info is not None:
        info.update(out)
    salida(f"fútbol: The Odds API {n2} partidos, SportsAPIPro {n3}; créditos {cli.p.gastado}")
    return out


def main(argv=None) -> int:
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="Respaldo de cuotas de fútbol (consulta): seco por defecto")
    ap.add_argument("--ejecutar", action="store_true", help="hace las peticiones (por defecto: seco)")
    ap.add_argument("--max-creditos", type=int, default=cr.MAX_CREDITOS)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    print(correr(ejecutar=a.ejecutar, max_creditos=a.max_creditos))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
