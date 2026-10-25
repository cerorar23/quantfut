"""Captura recurrente de FotMob (db/081), autorizada por el titular el 18-oct-2026; reactivada el 25-oct como
complemento diario de SofaScore y PropLine, solo en las competiciones activas.

Cuatro acciones, cada una con su cron:
  referencias  qué id de FotMob es cada partido nuestro (`leagues?id=`, una petición por competición al día).
  previos      instantáneas de un partido futuro en cinco ventanas (~24 h, ~4 h, ~70, ~40 y ~30 min antes del saque):
               alineación probable o confirmada, no disponibles, entrenadores, valor del once y pronóstico de clima.
               Es lo ÚNICO anterior al saque; cada fila lleva la hora real de captura.
  posteriores  la página del partido terminado; llena fotmob_partido / fotmob_jugador_partido / fotmob_baja.
  completar    sin peticiones: con esas páginas rellena en `matches` lo que SofaScore y PropLine dejaron vacío.

Límites de uso (no se evitan controles de acceso):
- Una petición cada `ESPERA_S` segundos, en serie.
- HTTP 401, 403 o 429: se registra, se alerta y NO se vuelve a pedir nada durante `ENFRIAMIENTO_H` horas.
- Una respuesta cuyo id no coincide con el pedido, o de un partido ya empezado en la captura previa, se descarta.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from ..league_policy import RETIRED_LEAGUES
from . import fotmob_a_motor as fm
from .fotmob_history import COMPETITIONS

log = logging.getLogger(__name__)

BASE = "https://www.fotmob.com/api/data/"
ESPERA_S = 0.8
ENFRIAMIENTO_H = 12
USER_AGENT = "QuantFut-Capture/1.0"
# Ventanas de la captura previa, en minutos antes del saque: (nombre, desde, hasta).
# La alineación oficial suele publicarse ~60 min antes: «final» la toma al abrirse la ventana (~T-75) y «cierre»
# (~T-45) deja constancia de la confirmada. Solo ~56 % de los partidos la traen oficial a T-45 (19-oct-2026), así que
# «tarde» (~T-33, autorizada el 19-oct) da una última oportunidad antes de sellar. Las ventanas se solapan: en cada pasada
# se toma la primera que aún no tiene captura. El cron corre cada 5 min (solo pide a FotMob cuando hay una ventana pendiente).
VENTANAS = (("dia", 900, 1560), ("horas", 150, 300), ("final", 50, 75), ("cierre", 25, 45), ("tarde", 25, 33))
MAX_POSTERIORES = 60
# «completar» espera a que la fuente principal haya tenido su oportunidad: el detalle de SofaScore llega con
# mediana 12 h, p90 19 h y máximo 33 h tras el saque (medido el 25-oct-2026).
ESPERA_COMPLETAR = timedelta(hours=36)


class AccesoDenegado(RuntimeError):
    pass


def ventanas_de(mins_to_kickoff: float) -> list[str]:
    return [nombre for nombre, desde, hasta in VENTANAS if desde <= mins_to_kickoff <= hasta]


def ventana_de(mins_to_kickoff: float) -> str | None:
    v = ventanas_de(mins_to_kickoff)
    return v[0] if v else None


class Cliente:
    def __init__(self, espera_s: float = ESPERA_S):
        self.espera_s = espera_s
        self._ultimo = 0.0

    def get(self, endpoint: str, params: dict) -> dict:
        url = BASE + endpoint + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        error: Exception | None = None
        for intento in range(3):
            espera = self.espera_s - (time.monotonic() - self._ultimo)
            if espera > 0:
                time.sleep(espera)
            self._ultimo = time.monotonic()
            req = urllib.request.Request(url, headers={"Accept": "application/json", "Accept-Encoding": "gzip",
                                                       "User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                datos = json.loads(raw)
                if not isinstance(datos, dict) or datos.get("error"):
                    raise ValueError("respuesta sin datos válidos")
                datos["__raw__"] = raw
                return datos
            except urllib.error.HTTPError as exc:
                if exc.code in (401, 403, 429):
                    raise AccesoDenegado(f"HTTP {exc.code}: {url}") from exc
                if exc.code < 500:
                    raise
                error = exc
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                error = exc
            time.sleep(2 ** intento)
        raise error  # type: ignore[misc]


def _log(c, accion: str, detalle: dict, denegado: bool = False) -> None:
    from psycopg.types.json import Jsonb
    c.execute("INSERT INTO fotmob_captura_log (accion, detalle, denegado) VALUES (%s, %s, %s)",
              (accion, Jsonb(detalle), denegado))
    c.commit()


def en_enfriamiento(c) -> bool:
    fila = c.execute("""SELECT 1 FROM fotmob_captura_log WHERE denegado
                        AND corrida_en > now() - make_interval(hours => %s) LIMIT 1""",
                     (ENFRIAMIENTO_H,)).fetchone()
    return fila is not None


def _guardar_original(c, match_id: str, fid: str, fase: str, raw: bytes, mins: float | None) -> tuple[int, datetime]:
    fila = c.execute(
        """INSERT INTO fotmob_original (match_id, fotmob_match_id, fase, mins_to_kickoff, raw_sha256, payload_gz)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, capturado_en""",
        (match_id, fid, fase, mins, hashlib.sha256(raw).hexdigest(), gzip.compress(raw, 6))).fetchone()
    return fila["id"], fila["capturado_en"]


def _validar(payload: dict, fid: str) -> bool:
    return str((payload.get("general") or {}).get("matchId")) == str(fid)


# ---------------------------------------------------------------------------------------------- referencias
def actualizar_referencias(c, cli: Cliente, dias_atras: int = 4) -> dict:
    equipo = {r["fotmob_team_id"]: r["team_id"] for r in c.execute("SELECT fotmob_team_id, team_id FROM fotmob_equipo")}
    r = {"competiciones": 0, "nuevas": 0, "sin_equipo": 0, "sin_partido": 0}
    ahora = datetime.now(timezone.utc)
    for liga, (fid_liga, _, _) in COMPETITIONS.items():
        if liga in RETIRED_LEAGUES:
            continue
        hub = cli.get("leagues", {"id": fid_liga})
        r["competiciones"] += 1
        for m in (hub.get("fixtures") or {}).get("allMatches") or []:
            try:
                saque = datetime.fromisoformat(str(m["status"]["utcTime"]).replace("Z", "+00:00"))
                h, a = equipo.get(int(m["home"]["id"])), equipo.get(int(m["away"]["id"]))
                fx = str(m["id"])
            except (KeyError, ValueError, TypeError):
                continue
            if not (ahora - timedelta(days=dias_atras) <= saque <= ahora + timedelta(days=12)):
                continue
            if h is None or a is None:
                r["sin_equipo"] += 1
                continue
            fila = c.execute(
                """SELECT m.match_id FROM matches m WHERE m.league_id = %s AND m.home_team_id = %s
                     AND m.away_team_id = %s AND abs(extract(epoch FROM m.kickoff_utc - %s)) < 129600
                     AND NOT EXISTS (SELECT 1 FROM fotmob_referencia f WHERE f.match_id = m.match_id)
                   ORDER BY abs(extract(epoch FROM m.kickoff_utc - %s)) LIMIT 1""",
                (liga, h, a, saque, saque)).fetchone()
            if fila is None:
                r["sin_partido"] += 1
                continue
            c.execute("""INSERT INTO fotmob_referencia (match_id, fotmob_match_id, fuente)
                         VALUES (%s, %s, 'liga') ON CONFLICT DO NOTHING""", (fila["match_id"], fx))
            r["nuevas"] += 1
        c.commit()
    return r


# ---------------------------------------------------------------------------------------------- previos
def datos_previo(payload: dict, kickoff: datetime) -> dict:
    """Lo que se guarda de una página previa. Sin consultar la base."""
    x = fm.extraer(payload, kickoff)
    p = x["partido"]
    cont = payload.get("content") or {}
    w = cont.get("weather") if isinstance(cont.get("weather"), dict) else {}
    alin = cont.get("lineup") or {}
    return {
        "tipo_alineacion": fm._texto(alin.get("lineupType")),
        "formacion_local": p["formacion_local"], "formacion_visita": p["formacion_visita"],
        "valor_xi_local": p["valor_xi_local"], "valor_xi_visita": p["valor_xi_visita"],
        "entrenador_local": p["entrenador_local"], "entrenador_visita": p["entrenador_visita"],
        "clima_temperatura_c": p["clima_temperatura_c"], "clima_viento": p["clima_viento"],
        "clima_direccion": p["clima_direccion"], "clima_humedad": p["clima_humedad"],
        "clima_precipitacion": p["clima_precipitacion"], "clima_nubosidad": p["clima_nubosidad"],
        "clima_prob_precipitacion": fm._num(w.get("precipChance")),
        "clima_descripcion": p["clima_descripcion"], "clima_api": p["clima_api"],
        "clima_actualizado": p["clima_actualizado"],
        "jugadores": x["jugadores"], "bajas": x["bajas"],
    }


_COLS_PREVIO = ("tipo_alineacion", "formacion_local", "formacion_visita", "valor_xi_local", "valor_xi_visita",
                "entrenador_local", "entrenador_visita", "clima_temperatura_c", "clima_viento", "clima_direccion",
                "clima_humedad", "clima_precipitacion", "clima_prob_precipitacion", "clima_nubosidad",
                "clima_descripcion", "clima_api", "clima_actualizado")


def candidatos_previos(c, ahora: datetime) -> list[dict]:
    filas = c.execute(
        """SELECT m.match_id, m.kickoff_utc, f.fotmob_match_id,
                  extract(epoch FROM m.kickoff_utc - %s) / 60 AS mins
           FROM matches m JOIN leagues l USING (league_id) JOIN fotmob_referencia f USING (match_id)
           WHERE m.status = 'scheduled' AND l.active
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (ahora, ahora + timedelta(minutes=20), ahora + timedelta(minutes=1560))).fetchall()
    out = []
    for f in filas:
        for v in ventanas_de(float(f["mins"])):
            hecho = c.execute("SELECT 1 FROM fotmob_previo WHERE match_id = %s AND ventana = %s",
                              (f["match_id"], v)).fetchone()
            if not hecho:
                out.append({**f, "ventana": v})
                break           # una captura por pasada y partido: la siguiente ventana pendiente va en la próxima
    return out


def capturar_previos(c, cli: Cliente) -> dict:
    ahora = datetime.now(timezone.utc)
    r = {"candidatos": 0, "guardados": 0, "descartados": 0}
    for cand in candidatos_previos(c, ahora):
        r["candidatos"] += 1
        payload = cli.get("matchDetails", {"matchId": cand["fotmob_match_id"]})
        gen = payload.get("general") or {}
        if not _validar(payload, cand["fotmob_match_id"]) or gen.get("started") or gen.get("finished"):
            r["descartados"] += 1
            continue
        mins = (cand["kickoff_utc"] - datetime.now(timezone.utc)).total_seconds() / 60
        oid, cap = _guardar_original(c, cand["match_id"], cand["fotmob_match_id"], "previo", payload["__raw__"], mins)
        d = datos_previo(payload, cand["kickoff_utc"])
        with c.cursor() as w:
            w.execute(
                "INSERT INTO fotmob_previo (match_id, capturado_en, mins_to_kickoff, ventana, original_id, "
                + ", ".join(_COLS_PREVIO) + ") VALUES (%s, %s, %s, %s, %s, " + ", ".join(["%s"] * len(_COLS_PREVIO))
                + ") ON CONFLICT DO NOTHING",
                (cand["match_id"], cap, mins, cand["ventana"], oid, *[d[k] for k in _COLS_PREVIO]))
            if w.rowcount:
                w.executemany(
                    """INSERT INTO fotmob_jugador_previo (match_id, capturado_en, side, jugador_id, nombre, titular,
                                                           posicion_id, valor_mercado)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                    [(cand["match_id"], cap, j["side"], j["jugador_id"], j["nombre"], j["titular"], j["posicion_id"],
                      j["valor_mercado"]) for j in d["jugadores"]])
                w.executemany(
                    """INSERT INTO fotmob_baja_previa (match_id, capturado_en, side, jugador_id, nombre, valor_mercado,
                                                        tipo, lesion_id, regreso_texto, regreso_fecha)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                    [(cand["match_id"], cap, b["side"], b["jugador_id"], b["nombre"], b["valor_mercado"], b["tipo"],
                      b["lesion_id"], b["regreso_texto"], b["regreso_fecha"]) for b in d["bajas"]])
                r["guardados"] += 1
        c.commit()
    return r


# ---------------------------------------------------------------------------------------------- posteriores
def capturar_posteriores(c, cli: Cliente, dias_atras: int = 6, maximo: int = MAX_POSTERIORES) -> dict:
    ahora = datetime.now(timezone.utc)
    filas = c.execute(
        """SELECT m.match_id, m.kickoff_utc, f.fotmob_match_id
           FROM matches m JOIN leagues l USING (league_id) JOIN fotmob_referencia f USING (match_id)
           WHERE m.status = 'finished' AND l.active AND m.kickoff_utc BETWEEN %s AND %s
             AND NOT EXISTS (SELECT 1 FROM fotmob_partido p WHERE p.match_id = m.match_id)
           ORDER BY m.kickoff_utc LIMIT %s""",
        (ahora - timedelta(days=dias_atras), ahora - timedelta(minutes=150), maximo)).fetchall()
    r = {"candidatos": len(filas), "guardados": 0, "descartados": 0}
    for f in filas:
        payload = cli.get("matchDetails", {"matchId": f["fotmob_match_id"]})
        if not _validar(payload, f["fotmob_match_id"]) or not (payload.get("general") or {}).get("finished"):
            r["descartados"] += 1
            continue
        oid, cap = _guardar_original(c, f["match_id"], f["fotmob_match_id"], "posterior", payload["__raw__"], None)
        raw = payload["__raw__"]
        x = fm.extraer(payload, f["kickoff_utc"])
        with c.cursor() as w:
            fm.insertar(w, f["match_id"], f["fotmob_match_id"], hashlib.sha256(raw).hexdigest(), cap, x)
        c.commit()
        r["guardados"] += 1
    return r


# ------------------------------------------------------------------------------------------------ completar
def completar(c, cli: Cliente | None = None, dias_atras: int = 10) -> dict:
    """Rellena en `matches`, con la página posterior ya guardada, lo que sigue NULL tras SofaScore y PropLine.

    Solo partidos con más de ESPERA_COMPLETAR desde el saque, solo columnas en NULL, el marcador de FotMob tiene que
    coincidir con el nuestro y la procedencia queda en `matches_enriquecimiento`. El xG solo si el partido no tiene
    ninguno (primera pareja válida), con la hora real de captura de la página. No hace peticiones.
    """
    from .archivo_a_matches import COLUMNAS_MATCHES, extraer as extraer_partido
    from .fotmob_history import stat_pairs

    ahora = datetime.now(timezone.utc)
    faltan = " OR ".join(f"m.{k} IS NULL" for k in COLUMNAS_MATCHES)
    filas = c.execute(
        f"""SELECT DISTINCT ON (m.match_id) m.match_id, m.home_goals, m.away_goals, m.home_xg, m.away_xg,
                   o.fotmob_match_id, o.capturado_en, o.payload_gz, {", ".join("m." + k for k in COLUMNAS_MATCHES)}
            FROM matches m JOIN leagues l USING (league_id) JOIN fotmob_original o USING (match_id)
            WHERE o.fase = 'posterior' AND l.active AND m.status = 'finished'
              AND m.kickoff_utc BETWEEN %s AND %s
              AND (m.home_xg IS NULL OR m.away_xg IS NULL OR {faltan})
            ORDER BY m.match_id, o.capturado_en""",
        (ahora - timedelta(days=dias_atras), ahora - ESPERA_COMPLETAR)).fetchall()
    r = {"candidatos": len(filas), "completados": 0, "con_xg": 0, "conflicto_marcador": 0, "sin_datos": 0}
    for f in filas:
        payload = json.loads(gzip.decompress(bytes(f["payload_gz"])))
        equipos = (payload.get("header") or {}).get("teams") or [{}, {}]
        if tuple(e.get("score") for e in equipos[:2]) != (f["home_goals"], f["away_goals"]):
            r["conflicto_marcador"] += 1
            continue
        stats = stat_pairs((((payload.get("content") or {}).get("stats") or {}).get("Periods") or {}).get("All", {}))
        datos = extraer_partido(payload, stats, f["home_goals"], f["away_goals"])
        nuevos = {k: datos[k] for k in COLUMNAS_MATCHES if f[k] is None and datos[k] is not None}
        xg = stats.get("expected_goals") or [None, None]
        con_xg = f["home_xg"] is None and f["away_xg"] is None and len(xg) == 2 and None not in xg
        if not nuevos and not con_xg:
            r["sin_datos"] += 1
            continue
        with c.transaction():
            if nuevos:
                sets = ", ".join(f"{k} = COALESCE({k}, %({k})s)" for k in nuevos)
                c.execute(f"UPDATE matches SET {sets} WHERE match_id = %(match_id)s",
                          {**nuevos, "match_id": f["match_id"]})
            if con_xg:
                con_xg = c.execute(
                    """UPDATE matches SET home_xg = %s, away_xg = %s, xg_source = 'fotmob', xg_recorded_at = %s
                       WHERE match_id = %s AND status = 'finished' AND home_xg IS NULL AND away_xg IS NULL""",
                    (xg[0], xg[1], f["capturado_en"], f["match_id"])).rowcount > 0
            for campo in list(nuevos) + (["xg"] if con_xg else []):
                c.execute("""INSERT INTO matches_enriquecimiento (match_id, campo, provider, source_match_id, captured_at)
                             VALUES (%s, %s, 'fotmob', %s, %s) ON CONFLICT DO NOTHING""",
                          (f["match_id"], campo, f["fotmob_match_id"], f["capturado_en"]))
        r["completados"] += 1
        r["con_xg"] += bool(con_xg)
    c.commit()
    return r


# ---------------------------------------------------------------------------------------------- CLI
def correr(c, accion: str, cli: Cliente | None = None, **opciones) -> dict:
    cli = cli or Cliente()
    if en_enfriamiento(c) and accion != "completar":
        return {"omitido": f"enfriamiento de {ENFRIAMIENTO_H} h tras una denegación de FotMob"}
    funciones = {"referencias": actualizar_referencias, "previos": capturar_previos,
                 "posteriores": capturar_posteriores, "completar": completar}
    try:
        res = funciones[accion](c, cli, **opciones)
    except AccesoDenegado as exc:
        c.rollback()
        _log(c, accion, {"error": str(exc)}, denegado=True)
        try:
            from ..publish import telegram
            telegram.alert(f"FotMob denegó el acceso ({exc}). La captura se detiene {ENFRIAMIENTO_H} h.")
        except Exception:  # noqa: BLE001 — avisar no puede tumbar el job
            log.exception("no se pudo enviar la alerta")
        return {"denegado": str(exc)}
    _log(c, accion, res)
    return res


def main(argv=None) -> None:
    import argparse

    from ..db import conn

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("accion", choices=["referencias", "previos", "posteriores", "completar"])
    ap.add_argument("--dias-atras", type=int, default=None, help="relleno puntual: hasta cuántos días atrás mirar")
    ap.add_argument("--maximo", type=int, default=None, help="relleno puntual (posteriores): máximo de partidos")
    a = ap.parse_args(argv)
    opc = {}
    if a.dias_atras is not None and a.accion != "previos":
        opc["dias_atras"] = a.dias_atras
    if a.maximo is not None and a.accion == "posteriores":
        opc["maximo"] = a.maximo
    logging.basicConfig(level=logging.INFO)
    with conn() as c:
        print(json.dumps(correr(c, a.accion, **opc), indent=1, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
