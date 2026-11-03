"""SofaScore NBA (archivo del titular, torneo 132): marcadores, cajas por jugador y titulares de 2021-22 a 2026-27.

Entrada: el archivo compacto de `ops/sofascore_a_jsonl.py` (un partido terminado por línea). Fuente `sofascore` (prioridad 2, detrás de
`nba_oficial`): donde las dos tienen el mismo dato gana la oficial en `nba.dato_a_las`; donde solo hay SofaScore (partidos que la caja oficial
no trae, y 2026-27 hasta que llegue cdn.nba.com), es la fuente. Todo `pit = reconstruido` con `recibido_en` = hora real en que se observó.

Identidad de jugadores: primero por la HUELLA de la caja (en un partido que ya tiene caja oficial, el jugador de SofaScore con los mismos
minutos, puntos, rebotes y asistencias en el mismo equipo es el mismo, aunque el nombre se escriba distinto); solo los jugadores sin ningún
partido en común se resuelven por nombre normalizado, con la regla anti-falsa-fusión de `identidad`.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, UTC
import gzip
import hashlib
import json
from pathlib import Path

from .. import carga, equipos, identidad
from ..carga import DatoNuevo

FUENTE = "sofascore"
METRICAS = {"points": "puntos", "rebounds": "rebotes", "assists": "asistencias", "steals": "robos", "blocks": "tapones", "turnovers": "perdidas",
            "personalFouls": "faltas", "plusMinus": "mas_menos", "fieldGoalsMade": "tiros_campo_anotados", "fieldGoalAttempts": "tiros_campo_intentados",
            "threePointsMade": "triples_anotados", "threePointAttempts": "triples_intentados", "freeThrowsMade": "tiros_libres_anotados",
            "freeThrowAttempts": "tiros_libres_intentados", "offensiveRebounds": "rebotes_ofensivos", "defensiveRebounds": "rebotes_defensivos"}
LOTE = 20000

HUELLAS = """
SELECT d.partido_id, d.entidad_id,
       max(CASE WHEN m.nombre = 'minutos' THEN d.valor END), max(CASE WHEN m.nombre = 'puntos' THEN d.valor END),
       max(CASE WHEN m.nombre = 'rebotes' THEN d.valor END), max(CASE WHEN m.nombre = 'asistencias' THEN d.valor END),
       max(CASE WHEN m.nombre = 'equipo_del_jugador' THEN d.valor END)
FROM nba.dato d JOIN nba.metrica m ON m.metrica_id = d.metrica_id
WHERE d.partido_id = ANY(%s) AND d.fuente = 'nba_oficial' AND d.fase = 'final' AND d.periodo = 0
  AND m.nombre IN ('minutos', 'puntos', 'rebotes', 'asistencias', 'equipo_del_jugador')
GROUP BY d.partido_id, d.entidad_id
HAVING max(CASE WHEN m.nombre = 'equipo_del_jugador' THEN d.valor END) IS NOT NULL AND max(CASE WHEN m.nombre = 'minutos' THEN d.valor END) > 0
"""


def leer(ruta: Path) -> list[dict]:
    with gzip.open(ruta, "rt", encoding="utf8") as f:
        return [json.loads(x) for x in f]


def _equipo(db, e: dict) -> int:
    return identidad.equipo(db, equipos.canonico(FUENTE, e["codigo"]))


def _huellas_oficiales(db, partidos: list[int]) -> dict:
    """{partido: {equipo_id: [(jugador, minutos, puntos, rebotes, asistencias)]}} de la caja oficial ya cargada."""
    salida: dict = defaultdict(lambda: defaultdict(list))
    for i in range(0, len(partidos), 500):
        for pid, jug, mn, pts, reb, ast, eq in db.execute(HUELLAS, (partidos[i:i + 500],)).fetchall():
            salida[pid][int(eq)].append((jug, mn, pts, reb, ast))
    return salida


def _votar(eventos, partidos, equipos_ids, huellas) -> Counter:
    votos: dict = defaultdict(Counter)
    for ev in eventos:
        fp = huellas.get(partidos[ev["id"]])
        if not fp:
            continue
        for j in ev["jugadores"]:
            s = j["stats"]
            if not s.get("secondsPlayed"):
                continue
            minutos = s["secondsPlayed"] / 60
            cand = [c[0] for c in fp.get(equipos_ids[ev["id"]][j["equipo"]], [])
                    if abs(c[1] - minutos) < 0.02 and c[2] == s.get("points", 0) and c[3] == s.get("rebounds", 0) and c[4] == s.get("assists", 0)]
            if len(cand) == 1:
                votos[j["id"]][cand[0]] += 1
    return votos


def cargar(db, ruta: Path) -> dict:
    eventos = leer(ruta)
    ruta_bytes = ruta.read_bytes()
    adquirido = datetime.fromtimestamp(ruta.stat().st_mtime, UTC)
    captura = db.execute("SELECT captura_id FROM nba.captura WHERE fuente = %s AND objetivo = %s AND ok", (FUENTE, f"nba_eventos:{ruta.name}")).fetchone()
    captura_id = captura[0] if captura else carga.registrar_captura(
        db, fuente=FUENTE, objetivo=f"nba_eventos:{ruta.name}", fase="historico", solicitado_en=adquirido, ok=True, recibido_en=adquirido,
        sha256=hashlib.sha256(ruta_bytes).hexdigest(), bytes_=len(ruta_bytes), ruta=ruta.name)
    resumen = Counter()
    partidos, equipos_ids = {}, {}
    for ev in eventos:
        fecha = date.fromisoformat(ev["fecha_et"])
        local, visita = _equipo(db, ev["local"]), _equipo(db, ev["visitante"])
        equipos_ids[ev["id"]] = {"local": local, "visitante": visita}
        existente = identidad._juego_canonico(db, fecha, local, visita)
        partidos[ev["id"]] = identidad.partido(db, FUENTE, str(ev["id"]), fecha, local, visita, ev["temporada"])
        resumen["partidos_nuevos" if existente is None else "partidos_existentes"] += 1
    db.commit()

    votos = _votar(eventos, partidos, equipos_ids, _huellas_oficiales(db, sorted(set(partidos.values()))))
    jugadores: dict[int, int] = {}
    nombres = {j["id"]: j["nombre"] for ev in eventos for j in ev["jugadores"]}
    for sid, nombre in nombres.items():
        if votos[sid]:
            (canon, n), *resto = votos[sid].most_common()
            if resto:
                resumen["jugadores_con_votos_en_conflicto"] += 1
            jugadores[sid] = identidad.alias_jugador(db, FUENTE, str(sid), nombre or str(sid), canon)
            resumen["jugadores_por_huella"] += 1
    for sid, nombre in nombres.items():
        if sid not in jugadores:
            jugadores[sid] = identidad.jugador(db, FUENTE, str(sid), nombre or str(sid))
            resumen["jugadores_por_nombre"] += 1
    db.commit()

    buffer: list[DatoNuevo] = []
    nuevas = leidas = 0

    def volcar():
        nonlocal buffer, nuevas, leidas
        if buffer:
            leidas += len(buffer)
            nuevas += carga.guardar_datos_lote(db, buffer)
            db.commit()
            buffer = []

    for ev in eventos:
        pid = partidos[ev["id"]]
        recibido = datetime.fromisoformat(ev["observado_utc"])
        base = dict(partido_id=pid, fase="final", fuente=FUENTE, recibido_en=recibido, captura_id=captura_id, pit="reconstruido")
        buffer.append(DatoNuevo(entidad_id=pid, metrica="estado_partido", etiqueta="final", **base))
        for lado in ("local", "visitante"):
            eq, marc = equipos_ids[ev["id"]][lado], ev["marcador"][lado]
            if marc.get("total") is not None:
                buffer.append(DatoNuevo(entidad_id=eq, metrica="puntos", valor=float(marc["total"]), **base))
            for k, p in enumerate(marc.get("periodos", []), start=1):
                buffer.append(DatoNuevo(entidad_id=eq, metrica="puntos", periodo=k, valor=float(p), **base))
        for j in ev["jugadores"]:
            s = j["stats"]
            if not s.get("secondsPlayed"):
                continue
            jug = jugadores[j["id"]]
            b = dict(base, entidad_id=jug)
            buffer.append(DatoNuevo(metrica="equipo_del_jugador", valor=float(equipos_ids[ev["id"]][j["equipo"]]), **b))
            buffer.append(DatoNuevo(metrica="jugo", valor=1.0, **b))
            buffer.append(DatoNuevo(metrica="titular", valor=1.0 if j["titular"] else 0.0, **b))
            buffer.append(DatoNuevo(metrica="minutos", valor=s["secondsPlayed"] / 60, **b))
            for k, nombre in METRICAS.items():
                if s.get(k) is not None:
                    buffer.append(DatoNuevo(metrica=nombre, valor=float(s[k]), **b))
        if len(buffer) >= LOTE:
            volcar()
    volcar()
    resumen.update({"eventos": len(eventos), "filas_leidas": leidas, "filas_nuevas": nuevas})
    return dict(resumen)


COMPARAR = """
SELECT m.nombre, count(*) AS comparables,
       count(*) FILTER (WHERE abs(s.valor - o.valor) > CASE WHEN m.nombre = 'minutos' THEN 0.02 ELSE 0.001 END) AS distintos
FROM nba.dato s JOIN nba.dato o ON o.partido_id = s.partido_id AND o.entidad_id = s.entidad_id AND o.periodo = s.periodo AND o.metrica_id = s.metrica_id
     AND o.fase = s.fase AND o.fuente = 'nba_oficial'
JOIN nba.metrica m ON m.metrica_id = s.metrica_id
WHERE s.fuente = 'sofascore' AND s.fase = 'final' AND m.nombre = ANY(%s) AND s.valor IS NOT NULL AND o.valor IS NOT NULL
GROUP BY m.nombre ORDER BY m.nombre
"""


def auditar(db) -> dict:
    """Compara, partido a partido, lo que dicen SofaScore y la caja oficial en lo que tienen en común."""
    nombres = ["minutos", "puntos", "rebotes", "asistencias", "robos", "tapones", "perdidas", "faltas", "mas_menos", "triples_anotados",
               "tiros_campo_anotados", "tiros_libres_anotados"]
    return {n: {"comparables": c, "distintos": d} for n, c, d in db.execute(COMPARAR, (nombres,)).fetchall()}
