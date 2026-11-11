"""
Escalones de NBA y tenis para el reto escalera (decisión del usuario,
2026-10-28: «conéctalos»), leídos del archivo PropLine compartido, sin
peticiones nuevas (CLAUDE.md: PropLine es la fuente fija de cuotas y el
recolector horario sirve a todos).

- Mercados: ganador del partido (h2h, `eval/escalera_multideporte.py`) y, desde
  el 10-nov-2026, hándicap y total del partido en líneas .5 (NBA: puntos; tenis:
  juegos; `eval/mercados_nuevos.py`, `docs/mercados_nuevos_medicion_20261110.md`:
  con p ≥ 0,69 el consenso acierta lo prometido, hueco −1 a +3 pp con intervalos
  que incluyen 0). Los props de jugador no llegan a p ≥ 0,69 y no entran.
- Probabilidad del ganador: Pinnacle sin margen (`settings.sharp_book`, Shin a dos
  lados). Sin Pinnacle en la observación, el partido no entra: no se cambia de
  referencia en silencio. En hándicap y total: consenso de las casas que cotizan
  ese contrato (`referencia.probabilidades`, mínimo 2 casas, Pinnacle pesa más si
  cotiza), como el parley v2.
- Cuota: la mejor de TODAS las casas de la observación (decisión del titular,
  2026-11-10; el archivo ya deja fuera las casas de fantasía y los mercados de
  intercambio), con menos de `escalera.MAX_EDAD_PRECIO` si la casa dice cuándo la
  cambió.
- Liquidación: la calificación de PropLine para la casa del escalón (cada casa
  aplica su regla de retiradas en tenis); sin ella, la de Pinnacle; sin ella, la de
  las demás casas si todas coinciden; si pasan `MARGEN_SIN_RESULTADO` sin
  calificar, nulo.

Solo lee el archivo; las filas inmutables las escribe `escalera_datos`.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta

from ..config import settings
from ..ingest import propline_shared as ps
from ..model.devig import two_way_devig
from . import escalera as es
from . import picks as pk
from . import referencia
from . import ventana
from .alta_prob import Candidato

# Deporte de la escalera → deporte del archivo PropLine.
DEPORTES = {"nba": "basketball_nba", "tenis": "tennis"}
# A las 6 h desde su inicio sin calificación de las casas, el escalón pasa a
# 'void' para ocultarse en el reto vivo y permitir un reemplazo el mismo día.
MARGEN_SIN_RESULTADO = timedelta(hours=6)
RESOLUCION = {"won": "win", "win": "win", "lost": "loss", "loss": "loss",
              "push": "push", "void": "void", "cancelled": "void", "refund": "void"}


# Mercado persistido → clave de PropLine. En tenis se guardan con los nombres del parley v2
# (`total_games`, `handicap_games`) porque la app ya los traduce así; en NBA, `totals` y `spreads`.
_CLAVE_PROPLINE = {"h2h": "h2h", "spreads": "spreads", "totals": "totals",
                   "handicap_games": "spreads", "total_games": "totals"}
_MERCADO_LINEA = {("nba", "totals"): "totals", ("nba", "spreads"): "spreads",
                  ("tenis", "totals"): "total_games", ("tenis", "spreads"): "handicap_games"}


def es_externo(match_id: str | None) -> bool:
    return bool(match_id) and match_id.split(":", 1)[0] in DEPORTES


def _h2h(book: dict, local: str, visitante: str) -> dict[str, dict] | None:
    """{'home': salida, 'away': salida} del ganador de una casa, o None si no trae los dos."""
    for m in book.get("markets", []):
        if m.get("key") != "h2h":
            continue
        lados = {}
        for o in m.get("outcomes", []):
            lado = "home" if o.get("name") == local else "away" if o.get("name") == visitante else None
            if lado:
                lados[lado] = o
        if len(lados) == 2:
            return lados
    return None


def _fresca(o: dict, recibida: datetime, now: datetime) -> bool:
    cambio = o.get("last_update")
    cuando = ps.parse_time(cambio) if cambio else recibida
    return now - cuando <= es.MAX_EDAD_PRECIO


def opciones(now: datetime, root=None) -> list[es.Opcion]:
    """Candidatos de NBA y tenis en el horizonte de la escalera, ya recibidos en `now`."""
    root = root or settings.propline_archive
    sharp = pk.canonical_book(settings.sharp_book)
    fin = ventana.fin_ventana(now, es.HORIZONTE)
    out: list[es.Opcion] = []
    for deporte, sport in DEPORTES.items():
        eventos, recibo = ps.read_two_way(root, sport, now)
        if recibo is None:
            continue
        recibida = ps.parse_time(recibo["received_at"])
        # Hándicap y total, con líneas alternativas (las de p ≥ 0,69 casi nunca son la principal), leídos de
        # la misma observación sin filtrar por línea. No necesitan que Pinnacle cotice el ganador.
        crudos, _ = ps.newest(root, f"/v1/sports/{sport}/odds", now)
        for e in crudos or []:
            inicio = ps.parse_time(e["commence_time"])
            if now + pk.MIN_LEAD <= inicio <= fin:
                evento = (str(e["id"]), e.get("sport_key") or sport, inicio, e["home_team"], e["away_team"])
                out.extend(_opciones_linea(deporte, e, recibo["received_at"], evento, sharp, recibida, now))
        for e in eventos:
            inicio = ps.parse_time(e["commence_time"])
            if not now + pk.MIN_LEAD <= inicio <= fin:
                continue
            local, visitante = e["home_team"], e["away_team"]
            evento = (str(e["id"]), e.get("sport_key") or sport, inicio, local, visitante)
            casas = {pk.canonical_book(b["key"]): _h2h(b, local, visitante) for b in e["bookmakers"]}
            ref = casas.get(sharp)
            if ref is None:
                continue
            p_local, p_visit = two_way_devig(float(ref["home"]["price"]), float(ref["away"]["price"]),
                                             settings.devig_method)
            for lado, prob in (("home", p_local), ("away", p_visit)):
                precios = [(float(h[lado]["price"]), casa) for casa, h in casas.items()
                           if h and _fresca(h[lado], recibida, now)]
                if not precios:
                    continue
                precio, casa = max(precios)
                out.append(es.Opcion(f"{deporte}:{e['id']}", Candidato("h2h", lado, None, float(prob)),
                                     precio, casa, "propline", recibida, deporte, evento))
    return out


def _media(punto) -> bool:
    """Solo líneas .5: una línea entera puede devolverse y no está medida."""
    try:
        return abs(abs(float(punto)) % 1 - 0.5) < 1e-9
    except (TypeError, ValueError):
        return False


def _contratos(e: dict, recibido_en: str) -> dict[tuple, dict[str, dict]]:
    """{(mercado, línea): {casa: {lado: salida}}} con TODAS las líneas .5 del partido completo.

    Parte de las cotizaciones del archivo (sin marcas: ni casas de fantasía, ni intercambios, ni en
    juego, ni restringidas). En el hándicap la línea es la del local y el visitante lleva la opuesta.
    """
    local, visitante = e["home_team"], e["away_team"]
    puntos: dict[tuple, dict[float, dict]] = {}
    for q in ps.quotes([e], recibido_en):
        if (q["flags"] or q["period"] is not None or q["team"] is not None or q["player_id"] is not None
                or q["market"] not in ("spreads", "totals") or q["price_decimal"] is None
                or not _media(q["point"])):
            continue
        if q["market"] == "totals":
            lado = q["name"].lower() if q["name"] in ("Over", "Under") else None
        else:
            lado = q["side"] if q["side"] in ("home", "away") else None
        if lado is None:
            continue
        salida = {"price": float(q["price_decimal"])}
        if q["book_updated_at"]:
            salida["last_update"] = q["book_updated_at"]
        puntos.setdefault((pk.canonical_book(q["bookmaker"]), q["market"], lado), {}).setdefault(
            float(q["point"]), salida)
    out: dict[tuple, dict[str, dict]] = {}
    for (casa, mercado, lado), por_punto in puntos.items():
        if lado not in ("over", "home"):
            continue
        otro = "under" if lado == "over" else "away"
        contrarios = puntos.get((casa, mercado, otro), {})
        for punto, salida in por_punto.items():
            contra = contrarios.get(punto if mercado == "totals" else -punto)
            if contra is not None:
                out.setdefault((mercado, punto), {})[casa] = {lado: salida, otro: contra}
    return out


def _opciones_linea(deporte: str, e: dict, recibido_en: str, evento: tuple, sharp: str, recibida: datetime,
                    now: datetime) -> list[es.Opcion]:
    """Hándicap y total del partido: probabilidad por consenso del contrato, cuota de la mejor casa."""
    out = []
    for (clave, linea), casas in _contratos(e, recibido_en).items():
        lados = ("over", "under") if clave == "totals" else ("home", "away")
        ref = referencia.probabilidades(
            {c: {s: float(q[s]["price"]) for s in lados} for c, q in casas.items()}, lados, preferida=sharp)
        if ref is None:
            continue
        probs, _ = ref
        for lado in lados:
            precios = [(float(q[lado]["price"]), c) for c, q in casas.items() if _fresca(q[lado], recibida, now)]
            if not precios:
                continue
            precio, casa = max(precios)
            punto = -linea if (clave == "spreads" and lado == "away") else linea
            out.append(es.Opcion(f"{deporte}:{e['id']}",
                                 Candidato(_MERCADO_LINEA[(deporte, clave)], lado, punto, float(probs[lado])),
                                 precio, casa, "propline", recibida, deporte, evento))
    return out


def _nombre_objetivo(paso: dict) -> str:
    if paso["selection"] in ("over", "under"):
        return paso["selection"].capitalize()
    return paso["evento_local"] if paso["selection"] == "home" else paso["evento_visitante"]


def _apellido(nombre) -> str:
    partes = ps._fold(str(nombre).replace(".", " ").split()[-1] if str(nombre).split() else "")
    return partes if len(partes) >= 4 else ""


def _mismo_nombre(a, b, otro=None) -> bool:
    """Las casas escriben distinto un mismo equipo o jugador («LA Lakers», «Los Angeles Lakers», «J. Sinner»).

    Over/Under, exacto. Si el nombre también encajaría con el rival, solo vale el exacto.
    """
    if a == b:
        return True
    if b in ("Over", "Under"):
        return False
    def parecido(x, y):
        fx, fy = ps._fold(x), ps._fold(y)
        return ps._same_club(fx, fy) or (_apellido(x) != "" and _apellido(x) == _apellido(y))
    return parecido(a, b) and not (otro is not None and parecido(a, otro))


_RESPALDO_CORRIDA: ContextVar = ContextVar("escalera_respaldo_corrida", default=None)


@contextmanager
def respaldo_tenis_activo():
    """Comparte una única sesión de respaldo de tenis entre todos los escalones de una corrida."""
    from ..ingest import tenis_resultados as tr
    with tr.RespaldoTenis() as respaldo:
        tok = _RESPALDO_CORRIDA.set(respaldo.resolver_paso)
        try:
            yield respaldo
        finally:
            _RESPALDO_CORRIDA.reset(tok)


def _resolver_respaldo_tenis(paso: dict, now: datetime) -> str | None:
    from ..ingest import tenis_resultados as tr
    with tr.RespaldoTenis() as respaldo:
        return respaldo.resolver_paso(paso, now)


def resultado(paso: dict, now: datetime, root=None, resolver_respaldo=None) -> tuple | None:
    """(outcome, None, None, None) del escalón externo, o None si aún no se puede liquidar."""
    root = root or settings.propline_archive
    sport = DEPORTES[paso["deporte"]]
    clave = _CLAVE_PROPLINE.get(paso.get("market") or "h2h", "h2h")
    nombre = _nombre_objetivo(paso)
    rival = None if paso["selection"] in ("over", "under") else (
        paso["evento_visitante"] if paso["selection"] == "home" else paso["evento_local"])
    punto = None if clave == "h2h" else float(paso["line"])
    filas, recibo = ps.read_results(root, sport, paso["evento_id"], now)
    por_casa = {}
    for f in filas or []:
        if (f["market"] == clave and f["period"] is None and f["team"] is None and f["resolution"] is not None
                and _mismo_nombre(f["name"], nombre, rival)
                and (punto is None or (f["point"] is not None and abs(float(f["point"]) - punto) < 1e-9))):
            por_casa.setdefault(pk.canonical_book(f["bookmaker"]), RESOLUCION.get(str(f["resolution"]).lower()))
    for casa in (pk.canonical_book(paso["book"]), pk.canonical_book(settings.sharp_book)):
        if por_casa.get(casa):
            return (por_casa[casa], None, None, None)
    otras = {r for r in por_casa.values() if r}
    if len(otras) == 1:           # ni la casa del escalón ni Pinnacle lo calificaron y las demás coinciden
        return (otras.pop(), None, None, None)
    if paso["deporte"] == "tenis":
        respaldo = resolver_respaldo or _RESPALDO_CORRIDA.get() or _resolver_respaldo_tenis
        out = respaldo(paso, now)
        if out:
            return (out, None, None, None)
    if paso["evento_inicio"] < now - MARGEN_SIN_RESULTADO:
        return ("void", None, None, None)
    return None


def sin_filas_de_resultado(paso: dict, now: datetime, root=None) -> bool:
    """True si el archivo PropLine no trae NINGUNA fila de resultado del evento y el respaldo tampoco confirmó void:
    un `void` en ese caso es falta de dato, no un partido anulado (hay que avisar para revisarlo a mano)."""
    root = root or settings.propline_archive
    filas, _ = ps.read_results(root, DEPORTES[paso["deporte"]], paso["evento_id"], now)
    if filas:
        return False
    if paso["deporte"] == "tenis":
        from ..ingest import tenis_resultados as tr
        with tr.respaldo_solo_archivo() as respaldo:
            if respaldo.resolver_paso(paso, now) == "void":
                return False
    return True
