"""Final del partido desde cdn.nba.com (vía Scrapfly): marcador del día, box score y jugada a jugada.

Solo hacia adelante y con tope diario de créditos de pago. `obtener(url)` devuelve (estado, cuerpo, créditos).
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from .. import carga, equipos, identidad
from ..carga import DatoNuevo, EventoNuevo

FUENTE = "nba_oficial"
ET = ZoneInfo("America/New_York")
BASE = "https://cdn.nba.com/static/json/liveData/"
URL_MARCADOR = BASE + "scoreboard/todaysScoreboard_00.json"


def url_box(game_id: str) -> str:
    return f"{BASE}boxscore/boxscore_{game_id}.json"


def url_pbp(game_id: str) -> str:
    return f"{BASE}playbyplay/playbyplay_{game_id}.json"


@dataclass(frozen=True)
class PartidoCDN:
    game_id: str
    fecha_et: date
    local: str
    visitante: str
    estado: int          # 1 programado, 2 en juego, 3 final


def minutos(iso: str | None) -> float | None:
    """`PT33M15.00S` → 33.25."""
    m = re.fullmatch(r"PT(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", iso or "")
    if not m or not (m.group(1) or m.group(2)):
        return None
    return int(m.group(1) or 0) + float(m.group(2) or 0) / 60


def parsear_marcador(texto: str) -> list[PartidoCDN]:
    partidos = []
    for g in json.loads(texto)["scoreboard"]["games"]:
        fecha = datetime.strptime(g["gameCode"].split("/")[0], "%Y%m%d").date()
        partidos.append(PartidoCDN(g["gameId"], fecha, equipos.canonico(FUENTE, g["homeTeam"]["teamTricode"]),
                                   equipos.canonico(FUENTE, g["awayTeam"]["teamTricode"]), int(g["gameStatus"])))
    return partidos


# métrica canónica → clave de estadística de cdn
JUGADOR = {"puntos": "points", "minutos": None, "tiros_campo_anotados": "fieldGoalsMade",
           "tiros_campo_intentados": "fieldGoalsAttempted", "triples_anotados": "threePointersMade",
           "triples_intentados": "threePointersAttempted", "tiros_libres_anotados": "freeThrowsMade",
           "tiros_libres_intentados": "freeThrowsAttempted", "rebotes_ofensivos": "reboundsOffensive",
           "rebotes_defensivos": "reboundsDefensive", "rebotes": "reboundsTotal", "asistencias": "assists",
           "robos": "steals", "tapones": "blocks", "perdidas": "turnovers", "faltas": "foulsPersonal",
           "mas_menos": "plusMinusPoints"}
EQUIPO = dict(JUGADOR, rebotes="reboundsPersonal", faltas="foulsPersonal")   # rebotes de equipo = suma de jugadores
EQUIPO.pop("mas_menos")


def cargar_boxscore(db, texto: str, recibido_en: datetime, captura_id: int) -> int:
    g = json.loads(texto)["game"]
    if int(g["gameStatus"]) != 3:
        raise ValueError("el partido aún no es final")
    fecha = datetime.strptime(g["gameCode"].split("/")[0], "%Y%m%d").date()
    local, visitante = (equipos.canonico(FUENTE, g[k]["teamTricode"]) for k in ("homeTeam", "awayTeam"))
    partido = identidad.partido(db, FUENTE, g["gameId"], fecha, identidad.equipo(db, local),
                                identidad.equipo(db, visitante), identidad.temporada(fecha))
    base = dict(partido_id=partido, fase="final", fuente=FUENTE, recibido_en=recibido_en, captura_id=captura_id)
    filas = [DatoNuevo(entidad_id=partido, metrica="estado_partido", etiqueta="final", **base)]
    if g.get("attendance"):
        filas.append(DatoNuevo(entidad_id=partido, metrica="asistencia", valor=float(g["attendance"]), **base))
    periodos = max(len(g["homeTeam"]["periods"]), len(g["awayTeam"]["periods"]))
    filas.append(DatoNuevo(entidad_id=partido, metrica="prorrogas", valor=float(max(0, periodos - 4)), **base))
    for o in g.get("officials", []):
        arbitro = identidad.arbitro(db, FUENTE, str(o["personId"]), o["name"])
        filas.append(DatoNuevo(entidad_id=arbitro, metrica="arbitro_asignado", valor=1.0, **base))
    for lado in ("homeTeam", "awayTeam"):
        e = g[lado]
        equipo = identidad.equipo(db, equipos.canonico(FUENTE, e["teamTricode"]))
        for metrica, clave in EQUIPO.items():
            valor = minutos(e["statistics"].get("minutes")) if metrica == "minutos" else e["statistics"].get(clave)
            if valor is not None:
                filas.append(DatoNuevo(entidad_id=equipo, metrica=metrica, valor=float(valor), **base))
        if e["statistics"].get("reboundsTeam") is not None:
            filas.append(DatoNuevo(entidad_id=equipo, metrica="rebotes_equipo",
                                   valor=float(e["statistics"]["reboundsTeam"]), **base))
        for p in e["periods"]:
            filas.append(DatoNuevo(entidad_id=equipo, metrica="puntos", periodo=int(p["period"]),
                                   valor=float(p["score"]), **base))
        for j in e["players"]:
            jugador = identidad.jugador(db, FUENTE, str(j["personId"]), j["name"])
            jugo = j.get("played") == "1"
            filas.append(DatoNuevo(entidad_id=jugador, metrica="jugo", valor=1.0 if jugo else 0.0, **base))
            filas.append(DatoNuevo(entidad_id=jugador, metrica="titular", valor=1.0 if j.get("starter") == "1" else 0.0,
                                   **base))
            if not jugo:
                continue  # sin minutos no se inventan estadísticas en cero
            for metrica, clave in JUGADOR.items():
                valor = minutos(j["statistics"].get("minutes")) if metrica == "minutos" else j["statistics"].get(clave)
                if valor is not None:
                    filas.append(DatoNuevo(entidad_id=jugador, metrica=metrica, valor=float(valor), **base))
    return carga.guardar_datos(db, filas)


def cargar_pbp(db, texto: str, partido_id: int, recibido_en: datetime, captura_id: int) -> int:
    acciones = json.loads(texto)["game"]["actions"]
    eventos = []
    for a in acciones:
        tricode = a.get("teamTricode")
        persona = a.get("personId")
        puntos = None
        if a.get("shotResult") == "Made" or (a["actionType"] == "freethrow" and a.get("shotResult") == "Made"):
            puntos = {"2pt": 2, "3pt": 3, "freethrow": 1}.get(a["actionType"])
        eventos.append(EventoNuevo(
            partido_id=partido_id, fuente=FUENTE, secuencia=int(a["actionNumber"]), periodo=int(a["period"]),
            reloj_s=minutos(a.get("clock")) * 60 if minutos(a.get("clock")) is not None else 0.0,
            tipo=a["actionType"], subtipo=a.get("subType"), recibido_en=recibido_en, captura_id=captura_id,
            equipo_id=identidad.equipo(db, equipos.canonico(FUENTE, tricode)) if tricode else None,
            jugador_id=identidad.jugador(db, FUENTE, str(persona), a.get("playerNameI") or str(persona)) if persona else None,
            x=a.get("x"), y=a.get("y"),
            acierto=(a["shotResult"] == "Made") if a.get("shotResult") in ("Made", "Missed") else None,
            puntos=puntos,
            marcador_local=int(a["scoreHome"]) if a.get("scoreHome") not in (None, "") else None,
            marcador_visit=int(a["scoreAway"]) if a.get("scoreAway") not in (None, "") else None))
    return carga.guardar_eventos(db, eventos)


def gastado_hoy(db, ahora: datetime) -> float:
    desde = ahora.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return float(db.execute("SELECT coalesce(sum(creditos), 0) FROM nba.captura WHERE fuente = %s AND creditos > 0 "
                            "AND solicitado_en >= %s AND solicitado_en < %s",
                            (FUENTE, desde, desde + timedelta(days=1))).fetchone()[0])


def _captura_ok(db, objetivo: str) -> bool:
    return db.execute("SELECT EXISTS (SELECT 1 FROM nba.captura WHERE fuente = %s AND objetivo = %s AND ok)",
                      (FUENTE, objetivo)).fetchone()[0]


def _fallos_recientes(db, objetivo: str, ahora: datetime) -> int:
    return db.execute("SELECT count(*) FROM nba.captura WHERE fuente = %s AND objetivo = %s AND NOT ok "
                      "AND solicitado_en > %s", (FUENTE, objetivo, ahora - timedelta(hours=24))).fetchone()[0]


def _finales_pendientes(db, ahora: datetime, dias: int = 3) -> list[tuple[int, str, datetime]]:
    """Partidos que ESPN da por finales, con id de la NBA conocido, cuyos últimos `dias` días ET aún no tienen box score."""
    desde = (ahora.astimezone(ET) - timedelta(days=dias)).date()
    return db.execute(
        "SELECT p.entidad_id, a.id_en_fuente, min(d.recibido_en) FROM nba.entidad p "
        "JOIN nba.entidad a ON a.canonica_id = p.entidad_id AND a.fuente = %s AND a.tipo = 'partido' AND a.id_en_fuente ~ '^[0-9]{10}$' "
        "JOIN nba.dato d ON d.partido_id = p.entidad_id AND d.entidad_id = p.entidad_id AND d.fase = 'final' "
        "JOIN nba.metrica m ON m.metrica_id = d.metrica_id AND m.nombre = 'estado_partido' AND d.etiqueta = 'final' "
        "WHERE p.tipo = 'partido' AND p.canonica_id = p.entidad_id AND p.fecha_juego_et >= %s "
        "GROUP BY p.entidad_id, a.id_en_fuente ORDER BY min(d.recibido_en) DESC", (FUENTE, desde)).fetchall()


def capturar(db, obtener: Callable[[str], tuple], raiz: Path, ahora: datetime, tope_diario: float = 25,
             espera_final_min: float = 10, max_fallos: int = 2) -> dict:
    """1) marcador del día (una vez, para conocer los id de la NBA); 2) box score de cada final; 3) jugada a jugada
    con el presupuesto que quede. Nunca pasa del tope diario de créditos."""
    resumen = {"ok": True, "creditos": 0.0, "marcador": 0, "box": 0, "pbp": 0, "datos": 0, "eventos": 0, "sin_presupuesto": False}

    def pedir(url: str):
        if gastado_hoy(db, ahora) >= tope_diario:
            resumen["sin_presupuesto"] = True
            return None
        try:
            estado, cuerpo, creditos = obtener(url)
        except Exception as e:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="final", solicitado_en=ahora, ok=False,
                                    error=f"{type(e).__name__}: {e}")
            resumen["ok"] = False
            return None
        resumen["creditos"] += creditos
        if estado != 200:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="final", solicitado_en=ahora, ok=False,
                                    recibido_en=ahora, http_status=estado, creditos=creditos)
            resumen["ok"] = False
            return None
        ruta, huella = carga.guardar_original(raiz, FUENTE, cuerpo, ahora)
        return dict(fuente=FUENTE, objetivo=url, fase="final", solicitado_en=ahora, ok=True, recibido_en=ahora,
                    http_status=200, sha256=huella, bytes_=len(cuerpo), ruta=ruta, creditos=creditos), cuerpo.decode("utf-8")

    # 1) marcador del día: una vez por día ET, a partir de las 10:00 ET, si hay partidos de hoy sin id de la NBA
    ahora_et = ahora.astimezone(ET)
    ya_hoy = db.execute("SELECT EXISTS (SELECT 1 FROM nba.captura WHERE fuente = %s AND objetivo = %s AND ok "
                        "AND recibido_en > %s)", (FUENTE, URL_MARCADOR, ahora - timedelta(hours=20))).fetchone()[0]
    sin_id = db.execute(
        "SELECT count(*) FROM nba.entidad p WHERE p.tipo = 'partido' AND p.canonica_id = p.entidad_id AND p.fecha_juego_et = %s "
        "AND NOT EXISTS (SELECT 1 FROM nba.entidad a WHERE a.canonica_id = p.entidad_id AND a.fuente = %s "
        "AND a.id_en_fuente ~ '^[0-9]{10}$')", (ahora_et.date(), FUENTE)).fetchone()[0]
    if ahora_et.hour >= 10 and not ya_hoy and sin_id > 0 and _fallos_recientes(db, URL_MARCADOR, ahora) < max_fallos:
        r = pedir(URL_MARCADOR)
        if r is not None:
            ficha, texto = r
            captura = carga.registrar_captura(db, **ficha)
            for p in parsear_marcador(texto):
                identidad.partido(db, FUENTE, p.game_id, p.fecha_et, identidad.equipo(db, p.local),
                                  identidad.equipo(db, p.visitante), identidad.temporada(p.fecha_et))
            resumen["marcador"] = 1
            resumen["captura_marcador"] = captura

    # 2) y 3) finales pendientes: primero todos los box scores, luego la jugada a jugada
    pendientes = [(p, g, t) for p, g, t in _finales_pendientes(db, ahora) if ahora - t >= timedelta(minutes=espera_final_min)]
    for partido, game_id, _ in pendientes:
        url = url_box(game_id)
        if _captura_ok(db, url) or _fallos_recientes(db, url, ahora) >= max_fallos:
            continue
        r = pedir(url)
        if r is None:
            continue
        ficha, texto = r
        if int(json.loads(texto)["game"]["gameStatus"]) != 3:  # la NBA aún no lo da por final: se reintenta luego
            carga.registrar_captura(db, **dict(ficha, ok=False, error="el partido aún no es final para la NBA"))
            resumen["ok"] = False
            continue
        captura = carga.registrar_captura(db, **ficha)
        resumen["datos"] += cargar_boxscore(db, texto, ahora, captura)
        resumen["box"] += 1
    for partido, game_id, _ in pendientes:
        url = url_pbp(game_id)
        if not _captura_ok(db, url_box(game_id)) or _captura_ok(db, url) or _fallos_recientes(db, url, ahora) >= max_fallos:
            continue
        r = pedir(url)
        if r is None:
            continue
        ficha, texto = r
        captura = carga.registrar_captura(db, **ficha)
        resumen["eventos"] += cargar_pbp(db, texto, partido, ahora, captura)
        resumen["pbp"] += 1
    return resumen


def obtener_scrapfly(url: str, clave: str) -> tuple[int, bytes, float]:
    """Scrapfly con ASP (≈1 crédito por archivo; los fallos upstream también se cobran): devuelve (estado, cuerpo, créditos)."""
    import httpx
    r = httpx.get("https://api.scrapfly.io/scrape", timeout=90, params={
        "key": clave, "url": url, "asp": "true", "render_js": "false", "cost_budget": "25"})
    datos = r.json()
    resultado = datos.get("result") or {}
    creditos = float((datos.get("context") or {}).get("cost", {}).get("total") or 0)
    return int(resultado.get("status_code") or r.status_code), (resultado.get("content") or "").encode("utf-8"), creditos
