"""Quintetos en pista 2021-26 (rotaciones oficiales ya reconstruidas en archivos) hacia `nba.evento`.

Una fila `tipo='quinteto'` por cada instante en que cambia la alineación de cualquiera de los dos equipos, con los dos
quintetos completos en `en_pista_local` / `en_pista_visit` y `reloj_s` = segundos que quedan del periodo. Los tiempos del
archivo están cuantizados (no son de seguimiento exacto) y no hay recepción acreditada: `recibido_en` es la fecha de
adquisición del archivo. Se reparte por fragmentos (`i/n` por número de partido) para cargar con varias conexiones.
"""
from collections import defaultdict
from datetime import UTC, date, datetime
import json
from pathlib import Path

from .. import equipos, identidad
from .historico_cuotas import _abrir
from .historico_partidos import FUENTE, _captura, _partido

SECUENCIA_BASE = 1_000_000
COLUMNAS = ("partido_id, fuente, secuencia, periodo, reloj_s, tipo, subtipo, en_pista_local, en_pista_visit, "
            "captura_id, recibido_en")


def fin_periodo(periodo: int) -> int:
    return 720 * periodo if periodo <= 4 else 2880 + 300 * (periodo - 4)


def quintetos(juego: dict, local: int, visitante: int):
    """(periodo, reloj_s, quinteto_local, quinteto_visitante) en orden de juego; omite los instantes con un equipo sin tramo."""
    tramos: dict = defaultdict(lambda: {local: [], visitante: []})
    for t in juego["chronological_lineups"]:
        if t["team_id"] in (local, visitante):
            tramos[t["period"]][t["team_id"]].append((t["start_elapsed_seconds"], t["end_elapsed_seconds"],
                                                      sorted(t["nba_player_ids"])))

    def en(lista, instante):
        return next((p for ini, fin, p in lista if ini <= instante < fin), None)

    for periodo in sorted(tramos):
        instantes = sorted({ini for lista in tramos[periodo].values() for ini, _, _ in lista})
        for instante in instantes:
            a, b = en(tramos[periodo][local], instante), en(tramos[periodo][visitante], instante)
            if a is not None and b is not None:
                yield periodo, max(0.0, fin_periodo(periodo) - instante), a, b


def cargar_rotaciones(db, carpeta: Path, fragmento: tuple[int, int] = (0, 1)) -> dict:
    ruta = carpeta / "rotaciones.jsonl.gz"
    indice, total = fragmento
    objetivo = f"rotaciones:{ruta.name}#{indice}/{total}"
    captura = _captura(db, ruta, objetivo)
    recibido = datetime.fromtimestamp(ruta.stat().st_mtime, UTC)
    juegos = json.loads((carpeta / "games.json").read_text(encoding="utf8"))
    juegos = juegos.values() if isinstance(juegos, dict) else juegos
    equipos_juego = {g["game_id"]: (g["home"]["team_id"], g["away"]["team_id"], date.fromisoformat(g["date"])) for g in juegos}
    jugadores = dict(db.execute("SELECT id_en_fuente, entidad_id FROM nba.entidad WHERE tipo = 'jugador' AND fuente = %s",
                                (FUENTE,)).fetchall())
    cache: dict = {}
    resumen = {"ok": True, "juegos": 0, "ya_cargados": 0, "sin_catalogo": 0, "filas": 0, "sin_jugador": 0}
    cursor = db.cursor()
    with _abrir(ruta) as f:
        for numero, linea in enumerate(f):
            if numero % total != indice:
                continue
            juego = json.loads(linea)
            datos = equipos_juego.get(juego["game_id"])
            if datos is None:
                resumen["sin_catalogo"] += 1
                continue
            local_id, visit_id, fecha = datos
            partido = _partido(db, cache, juego["game_id"], fecha, equipos.NBA_IDS[local_id], equipos.NBA_IDS[visit_id])
            if db.execute("SELECT 1 FROM nba.evento WHERE partido_id = %s AND fuente = %s AND tipo = 'quinteto' LIMIT 1",
                          (partido, FUENTE)).fetchone():
                resumen["ya_cargados"] += 1
                continue
            secuencia = SECUENCIA_BASE
            filas = []
            for periodo, reloj, a, b in quintetos(juego, local_id, visit_id):
                try:
                    pista_a, pista_b = [jugadores[str(p)] for p in a], [jugadores[str(p)] for p in b]
                except KeyError:
                    resumen["sin_jugador"] += 1
                    continue
                secuencia += 1
                filas.append((partido, FUENTE, secuencia, periodo, reloj, "quinteto", None, pista_a, pista_b, captura,
                              recibido))
            with cursor.copy(f"COPY nba.evento ({COLUMNAS}) FROM STDIN") as copia:
                for fila in filas:
                    copia.write_row(fila)
            db.commit()
            resumen["filas"] += len(filas)
            resumen["juegos"] += 1
    return resumen
