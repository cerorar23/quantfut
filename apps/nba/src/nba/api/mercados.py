"""Radar de mercados: UNA sola selección por familia, la de mayor probabilidad entre las líneas cotizadas.

Lee solo lo ya sellado (`nba.pronostico`) y cuotas de PropLine recibidas **antes** del sello (`nba.cuota`, partido
completo, fase `pre`). No calcula probabilidades nuevas: usa la distribución sellada de cada pronóstico.

Regla de la cuota (31-oct-2026, la misma de `qf.ingest.cuotas_referencia`): gana el mayor precio decimal entre las
casas que cotizan los DOS lados de esa misma línea; empate, la casa alfabéticamente menor. Una casa con un solo lado
no cuenta. Sin cuota válida no hay selección: la familia sale vacía (el cliente muestra su estado de «sin publicar»),
nunca se inventa casa, precio ni línea.

Familias (las que el motor sella de verdad; los combos R+A/PRA, robos/tapones y la primera mitad NO existen como
contrato aprobado y no se calculan): puntos, rebotes, asistencias, triples, total del partido y puntos por equipo.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta, UTC

import numpy as np
import psycopg

from ..contratos.validar import ContratoIncumplido, validar_equipo, validar_jugador
from ..v2 import props
from .comun import PARTIDOS, contrato_linea

# (familia pública, mercado en nba.cuota, mercado del sello de jugador)
FAMILIAS = (
    ("puntos", "player_points", "jugador:puntos"),
    ("rebotes", "player_rebounds", "jugador:rebotes"),
    ("asistencias", "player_assists", "jugador:asistencias"),
    ("triples", "player_threes", "jugador:triples"),
    ("total_partido", "totals", None),
    ("puntos_equipo", "team_totals", None),
)
MERCADOS = tuple(f[1] for f in FAMILIAS)
METRICA = {"puntos": "puntos", "rebotes": "rebotes", "asistencias": "asistencias", "triples": "triples_anotados"}
ULTIMOS = 5
# Banda publicable. Las líneas alternativas lejanas dan probabilidades de 0,99 a cuota 26: no son un pronóstico
# útil ni una cuota que se pueda enseñar. Fuera de la banda no hay selección (la familia sale vacía).
PROB_MIN, PROB_MAX = 0.60, 0.95
PRECIO_MIN, PRECIO_MAX = 1.20, 4.00


def _precio(valor) -> float | None:
    try:
        p = float(valor)
    except (TypeError, ValueError):
        return None
    return p if math.isfinite(p) and p > 1.0 else None


def _linea(valor) -> float | None:
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return None
    return n if math.isfinite(n) else None


def casas_por_linea(filas) -> dict:
    """{(mercado, entidad, línea): {"casas": {casa: {lado: precio}}, "recibido_en": último}}."""
    out: dict = defaultdict(lambda: {"casas": defaultdict(dict), "recibido_en": None, "recibos": {}})
    for mercado, entidad, linea, lado, casa, cuota, recibido in filas:
        precio, numero = _precio(cuota), _linea(linea)
        if precio is None or numero is None or lado not in ("over", "under") or not casa:
            continue
        grupo = out[(mercado, entidad, numero)]
        lados = grupo["casas"][casa]
        clave = (casa, lado)
        previo = grupo['recibos'].get(clave)
        if clave not in grupo['recibos'] or (recibido is not None and (previo is None or recibido >= previo)):
            lados[lado] = precio
            grupo['recibos'][clave] = recibido
        if recibido is not None and (grupo["recibido_en"] is None or recibido > grupo["recibido_en"]):
            grupo["recibido_en"] = recibido
    return out


def mejor_cuota(grupo: dict, lado: str = 'over') -> dict | None:
    """Mejor precio entre las casas con ambos lados; tie-break alfabético."""
    validas = {c: lados[lado] for c, lados in grupo["casas"].items() if "over" in lados and "under" in lados}
    if not validas:
        return None
    casa, precio = min(validas.items(), key=lambda kv: (-kv[1], kv[0]))
    recibido = grupo.get('recibos', {}).get((casa, lado), grupo["recibido_en"])
    return {"precio": round(precio, 3), "casa": casa, "casas": len(validas),
            "recibido_en": recibido.isoformat() if isinstance(recibido, datetime) else None}


def lado_y_probabilidad(p_mas: float | None) -> tuple[str, float] | None:
    """(lado, probabilidad de ese lado) si el modelo ve una ventaja publicable; None fuera de la banda o en empate."""
    if p_mas is None or not (0.0 < p_mas < 1.0):
        return None
    if p_mas > 0.5:
        lado, p = "over", round(p_mas, 4)
    elif p_mas < 0.5:
        lado, p = "under", round(1.0 - p_mas, 4)
    else:
        return None
    return (lado, p) if PROB_MIN <= p <= PROB_MAX else None


def _cuota_publicable(cuota: dict | None) -> dict | None:
    """La cuota que se puede enseñar: precio dentro de la banda y casa identificada."""
    if cuota is None or not (PRECIO_MIN <= cuota["precio"] <= PRECIO_MAX):
        return None
    return cuota


def _base(mercado: str, entidad: int | None, nombre: str | None, lado_equipo: str | None,
          linea: float, lado: str, probabilidad: float, cuota: dict) -> dict:
    return {"jugador_id": entidad, "jugador": nombre, "lado_equipo": lado_equipo,
            "linea": linea, "lado": lado, "probabilidad": probabilidad, "cuota": cuota}


def candidatos_jugador(mercado: str, sello: str, sellos: dict, casas: dict) -> list[dict]:
    """Una fila por línea cotizada de cada jugador con ese mercado sellado."""
    salida = []
    for (mer, entidad), (escenarios, distribucion) in sellos.items():
        if mer != sello or not isinstance(escenarios, dict):
            continue
        try:
            validar_jugador(distribucion)
        except ContratoIncumplido:
            continue
        pmf = distribucion.get("pmf")
        if not pmf:
            continue
        pmf = np.asarray(pmf, float)
        nombre, lado_equipo = escenarios.get("nombre"), escenarios.get("lado")
        for (mer, ent, linea), grupo in casas.items():
            if mer != mercado or ent != entidad:
                continue
            elegido = lado_y_probabilidad(float(props.prob_mas_de(pmf[None, :], np.array([linea]))[0]))
            if elegido is None:
                continue
            lado, p = elegido
            cuota = _cuota_publicable(mejor_cuota(grupo, lado))
            if cuota is None:
                continue
            salida.append(_base(mercado, entidad, nombre, lado_equipo, linea, lado, p, cuota))
    return salida


def candidatos_equipo(mercado: str, familia: str, dist: dict, casas: dict,
                      equipos: dict[int, tuple[str, str]]) -> list[dict]:
    """Totales del partido (una distribución) y puntos por equipo (una por entidad)."""
    salida = []
    paso = dist.get("paso_cuantil", 0.005)
    for (mer, entidad, linea), grupo in casas.items():
        if mer != mercado:
            continue
        if familia == "total_partido":
            if entidad is not None:
                continue
            clave, nombre, lado_equipo = 'total', None, None
        else:
            if entidad is None or entidad not in equipos:
                continue
            nombre, lado_equipo = equipos[entidad]
            clave = 'puntos_local' if lado_equipo == 'local' else 'puntos_visitante'
        if not dist.get(clave):
            continue
        contrato = contrato_linea(dist, clave, linea)
        if contrato['extremo']:
            continue
        elegido = lado_y_probabilidad(contrato['p_mas'])
        if elegido is None:
            continue
        lado, p = elegido
        cuota = _cuota_publicable(mejor_cuota(grupo, lado))
        if cuota is None:
            continue
        salida.append(_base(mercado, entidad, nombre, lado_equipo, linea, lado, p, cuota))
    return salida


def elegir(candidatos: list[dict]) -> dict | None:
    """La de mayor probabilidad; empate: línea menor y luego lado, para que el resultado sea determinista."""
    if not candidatos:
        return None
    return sorted(candidatos, key=lambda c: (-c["probabilidad"], c["linea"], c["lado"]))[0]


def _sellos_jugador(db, partido_id: int) -> dict:
    filas = db.execute(
        "SELECT DISTINCT ON (mercado, entidad_id) mercado, entidad_id, escenarios, distribucion, objetivo_en "
        "FROM nba.pronostico WHERE partido_id = %s AND mercado LIKE 'jugador:%%' AND periodo = 0 "
        "ORDER BY mercado, entidad_id, sellado_en DESC, pronostico_id DESC", (partido_id,)).fetchall()
    return {(m, e): (esc, dist) for m, e, esc, dist, _ in filas}


def _sello_equipo(db, partido_id: int):
    return db.execute(
        "SELECT distribucion, objetivo_en FROM nba.pronostico WHERE partido_id = %s AND mercado = 'equipo' "
        "AND periodo = 0 AND entidad_id IS NULL ORDER BY sellado_en DESC, pronostico_id DESC LIMIT 1",
        (partido_id,)).fetchone()


def _objetivos(db, partido_id: int) -> list[datetime]:
    filas = db.execute(
        "SELECT DISTINCT objetivo_en FROM nba.pronostico WHERE partido_id = %s AND periodo = 0 "
        "AND (mercado = 'equipo' OR mercado LIKE 'jugador:%%')", (partido_id,)).fetchall()
    return [f[0] for f in filas if f[0] is not None]


def _cuotas(db, partido_id: int, hasta: datetime) -> list:
    """Cuotas del partido completo recibidas antes del sello."""
    return db.execute(
        "SELECT DISTINCT ON (mercado, entidad_id, linea, lado, casa) mercado, entidad_id, linea, lado, casa, cuota, recibido_en FROM nba.cuota "
        "WHERE partido_id = %s AND periodo = 0 AND fase = 'pre' AND recibido_en <= %s "
        "AND mercado = ANY(%s) ORDER BY mercado, entidad_id, linea, lado, casa, recibido_en DESC, cuota_id DESC",
        (partido_id, hasta, list(MERCADOS))).fetchall()


def ultimos_valores(db, partido_id: int, jugador_id: int, metrica: str, antes: date) -> list[float]:
    """Últimos partidos terminados del jugador ANTES de la fecha del partido (solo lectura, sin fuga)."""
    filas = db.execute(
        "SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) "
        "JOIN nba.entidad e ON e.entidad_id = d.partido_id "
        "WHERE d.entidad_id = %s AND m.nombre = %s AND d.periodo = 0 AND d.fase = 'final' "
        "AND d.valor IS NOT NULL AND e.fecha_juego_et < %s "
        "ORDER BY e.fecha_juego_et DESC, d.recibido_en DESC LIMIT %s",
        (jugador_id, metrica, antes, ULTIMOS)).fetchall()
    return [float(v) for (v,) in filas]


def familias_partido(db, fila) -> dict:
    """{familia: selección} del partido; `fila` = (id, fecha, id_local, id_visit, nombre_local, nombre_visit)."""
    pid = fila[0]
    equipos = {fila[2]: (fila[4], "local"), fila[3]: (fila[5], "visitante")}
    objetivos = _objetivos(db, pid)
    if not objetivos:
        return {}
    casas = casas_por_linea(_cuotas(db, pid, min(objetivos)))
    sellos = _sellos_jugador(db, pid)
    equipo = _sello_equipo(db, pid)
    dist = None
    if equipo is not None:
        try:
            validar_equipo(equipo[0])
            dist = equipo[0]
        except ContratoIncumplido:
            dist = None
    salida = {}
    for familia, mercado, sello in FAMILIAS:
        if sello is None:
            candidatos = candidatos_equipo(mercado, familia, dist, casas, equipos) if dist else []
        else:
            candidatos = candidatos_jugador(mercado, sello, sellos, casas)
        elegido = elegir(candidatos)
        if elegido is not None:
            elegido["ultimos"] = (
                ultimos_valores(db, pid, elegido["jugador_id"], METRICA[familia], fila[1])
                if familia in METRICA and elegido.get("jugador_id") else [])
            salida[familia] = elegido
    return salida


def mercados_del_dia(dsn: str, fecha: date) -> dict:
    with psycopg.connect(dsn, autocommit=False, options="-c default_transaction_read_only=on") as db:
        filas = db.execute(PARTIDOS + " AND e.fecha_juego_et = %s ORDER BY e.entidad_id", (fecha,)).fetchall()
        partidos = []
        for fila in filas:
            pid = fila[0]
            inicio = db.execute(
                "SELECT d.valor FROM nba.dato d JOIN nba.metrica m USING (metrica_id) WHERE d.partido_id = %s "
                "AND m.nombre = 'inicio_programado_utc' ORDER BY d.recibido_en DESC LIMIT 1", (pid,)).fetchone()
            partidos.append({
                "id": pid, "fecha": fila[1].isoformat(),
                "inicio_utc": (datetime.fromtimestamp(inicio[0], UTC).isoformat() if inicio and inicio[0] else None),
                "local": {"codigo": fila[6], "nombre": fila[4]},
                "visitante": {"codigo": fila[7], "nombre": fila[5]},
                "familias": familias_partido(db, fila),
            })
    return {"fecha": fecha.isoformat(), "partidos": partidos}
