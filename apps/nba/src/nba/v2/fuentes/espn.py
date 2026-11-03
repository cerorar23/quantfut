"""ESPN: calendario, marcadores y lesiones, leídos del ledger de captura `run57` del VPS (solo lectura).

La captura de red ya la hace el contenedor de `run57`; aquí solo se convierten sus recibos 200 en filas de `nba.*`.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo

from .. import carga, equipos, identidad
from ..carga import DatoNuevo

FUENTE = "espn"
ET = ZoneInfo("America/New_York")
ESTADOS = {"STATUS_SCHEDULED": "programado", "STATUS_DELAYED": "programado", "STATUS_IN_PROGRESS": "en_juego",
           "STATUS_HALFTIME": "en_juego", "STATUS_END_PERIOD": "en_juego", "STATUS_FINAL": "final",
           "STATUS_POSTPONED": "aplazado", "STATUS_CANCELED": "cancelado", "STATUS_SUSPENDED": "suspendido"}


@dataclass(frozen=True)
class PartidoESPN:
    id: str
    inicio_utc: datetime
    fecha_et: date
    estado: str
    local: str
    visitante: str
    asistencia: int
    puntos: dict[str, int] | None


@dataclass(frozen=True)
class LesionESPN:
    id_espn: str
    nombre: str
    equipo: str
    estado: str


def _tricode(equipo: dict) -> str:
    return equipos.ESPN_IDS.get(str(equipo.get("id"))) or equipos.canonico(FUENTE, equipo["abbreviation"])


def parsear_scoreboard(texto: str) -> list[PartidoESPN]:
    partidos = []
    for e in json.loads(texto)["events"]:
        c = e["competitions"][0]
        lado = {x["homeAway"]: x for x in c["competitors"]}
        try:
            local, visitante = _tricode(lado["home"]["team"]), _tricode(lado["away"]["team"])
        except KeyError:  # pretemporada: rivales que no son de la NBA (p. ej. equipos europeos o australianos)
            continue
        inicio = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        nombre = c["status"]["type"]["name"]
        estado = ESTADOS.get(nombre, nombre.removeprefix("STATUS_").lower())
        puntos = {local: int(lado["home"]["score"]), visitante: int(lado["away"]["score"])} if estado == "final" else None
        partidos.append(PartidoESPN(id=e["id"], inicio_utc=inicio, fecha_et=inicio.astimezone(ET).date(), estado=estado,
                                    local=local, visitante=visitante, asistencia=int(c.get("attendance") or 0),
                                    puntos=puntos))
    return partidos


def parsear_lesiones(texto: str) -> list[LesionESPN]:
    lesiones = []
    for equipo in json.loads(texto)["injuries"]:
        tricode = equipos.ESPN_IDS.get(str(equipo["id"]))
        if tricode is None:
            continue
        for i in equipo["injuries"]:
            atleta = i["athlete"]
            id_espn = str(atleta["id"]) if atleta.get("id") else None
            if id_espn is None:  # ESPN omite athlete.id en algunos registros: el enlace público lo trae
                for enlace in atleta.get("links", []):
                    m = re.search(r"/id/(\d+)", enlace.get("href", ""))
                    if m:
                        id_espn = m.group(1)
                        break
            if id_espn is None:
                continue
            lesiones.append(LesionESPN(id_espn, atleta["displayName"], tricode, i["status"]))
    return lesiones


def cargar_scoreboard(db, texto: str, recibido_en: datetime, captura_id: int) -> int:
    filas = []
    for p in parsear_scoreboard(texto):
        local, visitante = identidad.equipo(db, p.local), identidad.equipo(db, p.visitante)
        partido = identidad.partido(db, FUENTE, p.id, p.fecha_et, local, visitante, identidad.temporada(p.fecha_et))
        base = dict(partido_id=partido, fuente=FUENTE, recibido_en=recibido_en, captura_id=captura_id)
        final = p.estado == "final"
        filas.append(DatoNuevo(entidad_id=partido, metrica="inicio_programado_utc", fase="pre",
                               valor=p.inicio_utc.timestamp(), **base))
        filas.append(DatoNuevo(entidad_id=partido, metrica="estado_partido", fase="final" if final else "pre",
                               etiqueta=p.estado, **base))
        if final:
            if p.asistencia > 0:
                filas.append(DatoNuevo(entidad_id=partido, metrica="asistencia", fase="final",
                                       valor=float(p.asistencia), **base))
            for tricode, puntos in (p.puntos or {}).items():
                filas.append(DatoNuevo(entidad_id=identidad.equipo(db, tricode), metrica="puntos", fase="final",
                                       valor=float(puntos), **base))
    return carga.guardar_datos(db, filas, solo_cambios=True)


def _partidos_proximos(db, equipo_id: int, recibido_en: datetime) -> list[int]:
    """Partidos del equipo que aún no han empezado según el calendario ya cargado."""
    return [r[0] for r in db.execute(
        "SELECT c.entidad_id FROM nba.entidad c WHERE c.tipo = 'partido' AND c.canonica_id = c.entidad_id "
        "AND ((c.atributos->>'local')::bigint = %(e)s OR (c.atributos->>'visitante')::bigint = %(e)s) "
        "AND EXISTS (SELECT 1 FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = c.entidad_id "
        "AND m.nombre = 'inicio_programado_utc' AND d.valor > %(t)s AND d.recibido_en <= %(r)s)",
        {"e": equipo_id, "t": recibido_en.timestamp(), "r": recibido_en})]


def cargar_lesiones(db, texto: str, recibido_en: datetime, captura_id: int) -> int:
    por_equipo: dict[str, list[LesionESPN]] = {}
    for x in parsear_lesiones(texto):
        por_equipo.setdefault(x.equipo, []).append(x)
    filas = []
    for tricode in equipos.TRICODES:
        equipo_id = identidad.equipo(db, tricode)
        actuales = {identidad.jugador(db, FUENTE, x.id_espn, x.nombre): x.estado for x in por_equipo.get(tricode, [])}
        for partido in _partidos_proximos(db, equipo_id, recibido_en):
            base = dict(partido_id=partido, fase="pre", fuente=FUENTE, recibido_en=recibido_en, captura_id=captura_id)
            for jugador, estado in actuales.items():
                filas.append(DatoNuevo(entidad_id=jugador, metrica="estado_disponibilidad", etiqueta=estado, **base))
            # Quien estaba reportado y ya no figura: se deja constancia de que dejó de aparecer (no de que juegue).
            previos = db.execute(
                "SELECT DISTINCT ON (d.entidad_id) d.entidad_id, d.etiqueta FROM nba.dato d JOIN nba.metrica m "
                "USING (metrica_id) WHERE m.nombre = 'estado_disponibilidad' AND d.partido_id = %s AND d.fuente = %s "
                "AND d.recibido_en <= %s ORDER BY d.entidad_id, d.recibido_en DESC, d.dato_id DESC",
                (partido, FUENTE, recibido_en)).fetchall()
            for jugador, etiqueta in previos:
                if jugador not in actuales and etiqueta != "sin_reporte":
                    filas.append(DatoNuevo(entidad_id=jugador, metrica="estado_disponibilidad", etiqueta="sin_reporte",
                                           **base))
    return carga.guardar_datos(db, filas, solo_cambios=True)


URL_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={dia}"
URL_LESIONES = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries?limit=1000"


def _valido(tipo: str, texto: str) -> bool:
    try:
        cuerpo = json.loads(texto)
        if tipo == "calendario":
            return cuerpo["leagues"][0]["slug"] == "nba" and isinstance(cuerpo["events"], list)
        return isinstance(cuerpo["injuries"], list)
    except (ValueError, KeyError, IndexError, TypeError):
        return False


def capturar(db, obtener, raiz: Path, ahora: datetime, espera_lesiones_min: float = 55, reloj=None) -> dict:
    """Captura directa (sin pasar por `run57`): marcador de ayer, hoy y mañana (hora del este) y, como mucho cada hora, lesiones.

    Cada respuesta se guarda como original, se registra la captura con la hora real de recepción y se convierte con
    los mismos lectores que el ledger; un cuerpo que no es una respuesta NBA válida queda como captura fallida.
    """
    hoy = ahora.astimezone(ET).date()
    objetivos = [("calendario", URL_SCOREBOARD.format(dia=(hoy + timedelta(days=d)).strftime("%Y%m%d"))) for d in (-1, 0, 1)]
    reciente = db.execute("SELECT EXISTS (SELECT 1 FROM nba.captura WHERE fuente = %s AND objetivo = %s AND solicitado_en > %s)",
                          (FUENTE, URL_LESIONES, ahora - timedelta(minutes=espera_lesiones_min))).fetchone()[0]
    if not reciente:
        objetivos.append(("lesiones", URL_LESIONES))
    resumen = {"ok": True, "calendario": 0, "lesiones": 0, "fallidos": 0}
    for tipo, url in objetivos:
        try:
            estado, cuerpo = obtener(url)
        except Exception as e:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=ahora, ok=False,
                                    error=f"{type(e).__name__}: {e}"[:300])
            resumen["fallidos"] += 1
            continue
        recibido = reloj() if reloj else datetime.now(ahora.tzinfo)   # hora real de recepción, no la del inicio de la pasada
        if estado != 200:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=ahora, ok=False,
                                    recibido_en=recibido, http_status=estado)
            resumen["fallidos"] += 1
            continue
        ruta, huella = carga.guardar_original(raiz, FUENTE, cuerpo, recibido)
        texto = cuerpo.decode("utf-8", errors="replace")
        if not _valido(tipo, texto):
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=ahora, ok=False,
                                    recibido_en=recibido, http_status=200, sha256=huella, bytes_=len(cuerpo), ruta=ruta,
                                    error="respuesta que no es de la NBA o sin la estructura esperada")
            resumen["fallidos"] += 1
            continue
        captura = carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=ahora, ok=True,
                                          recibido_en=recibido, http_status=200, sha256=huella, bytes_=len(cuerpo), ruta=ruta)
        (cargar_scoreboard if tipo == "calendario" else cargar_lesiones)(db, texto, recibido, captura)
        resumen[tipo] += 1
    resumen["ok"] = resumen["fallidos"] == 0
    return resumen


def obtener_http(url: str) -> tuple[int, bytes]:
    import httpx
    r = httpx.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"},
                  timeout=20, follow_redirects=True)
    return r.status_code, r.content


def cargar_ledger(db, ruta_sqlite: Path, raiz_blobs: Path, desde_seq: int, limite: int | None = None) -> tuple[int, dict]:
    """Procesa los recibos de `run57` con `seq > desde_seq` (como mucho `limite`); devuelve (último seq, resumen)."""
    con = sqlite3.connect(f"{ruta_sqlite.resolve().as_uri()}?mode=ro", uri=True)
    try:
        eventos = con.execute("SELECT seq, payload FROM events WHERE seq > ? ORDER BY seq LIMIT ?",
                              (desde_seq, limite if limite is not None else -1)).fetchall()
    finally:
        con.close()
    resumen = {"calendario": 0, "lesiones": 0, "omitidos": 0}
    ultimo = desde_seq
    for seq, payload in eventos:
        ultimo = seq
        r = json.loads(payload)
        url = r.get("url", "")
        tipo = "calendario" if "/scoreboard" in url else "lesiones" if "/injuries" in url else None
        recibido = datetime.fromisoformat(r["first_received_at_utc"])
        if tipo is None:
            resumen["omitidos"] += 1
            continue
        if r.get("http_status") != 200:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=recibido, ok=False,
                                    recibido_en=recibido, http_status=r.get("http_status"), error=r.get("error"))
            resumen["omitidos"] += 1
            continue
        previa = db.execute("SELECT captura_id FROM nba.captura WHERE fuente = %s AND sha256 = %s AND recibido_en = %s",
                            (FUENTE, r["raw_sha256"], recibido)).fetchone()
        captura = previa[0] if previa else carga.registrar_captura(
            db, fuente=FUENTE, objetivo=url, fase="pre", solicitado_en=recibido, ok=True, recibido_en=recibido,
            http_status=200, sha256=r["raw_sha256"], bytes_=r.get("raw_bytes"), ruta=f"run57/{r['raw_sha256']}")
        texto = (raiz_blobs / r["raw_sha256"]).read_text(encoding="utf-8")
        (cargar_scoreboard if tipo == "calendario" else cargar_lesiones)(db, texto, recibido, captura)
        resumen[tipo] += 1
    return ultimo, resumen
