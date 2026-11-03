"""Tramos de quinteto con su cambio de marcador (insumo del experimento S3c: impacto por jugador estimado sobre tramos).

    python apps/nba/ops/preparar_stints_s3c.py ROTACIONES.jsonl.gz DATASETS_PBP CARPETA_EVAL SALIDA.pkl

ROTACIONES: quintetos por juego (nba_pending_rotations_v6); DATASETS_PBP: carpeta de shufinskiy/nba_data con los
`nbastatsv3_<año>.tar.xz` y `nbastatsv3_po_<año>.tar.xz` (jugada a jugada con marcador); CARPETA_EVAL: la de evaluar_s3b
(s3b_partidos.csv y s3b_jugadores.csv dan los ids canónicos y s3_juegos.csv las fechas). Cada fila: (pid, día, segundos,
cambio de margen local - visitante, jugadores locales, jugadores visitantes) con ids canónicos.
"""
import bisect
import csv
import gzip
import io
import json
from pathlib import Path
import pickle
import re
import sys
import tarfile
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nba.v2.fuentes.historico_rotaciones import fin_periodo  # noqa: E402

RELOJ = re.compile(r"PT(\d+)M([\d.]+)S")


def marcadores(datasets: Path):
    """game_id -> (local_team_id, [elapsed], [margen local - visitante]) con el marcador tras cada jugada con marcador."""
    juegos = {}
    for tar in sorted(datasets.glob("nbastatsv3_*.tar.xz")):
        with tarfile.open(tar) as t:
            for miembro in t.getmembers():
                if not miembro.name.endswith(".csv"):
                    continue
                lector = csv.DictReader(io.TextIOWrapper(t.extractfile(miembro), encoding="utf8"))
                actual = {}
                for r in lector:
                    g = r["gameId"].zfill(10)
                    if g not in actual:
                        actual[g] = {"local": None, "t": [], "m": [], "ultimo": (0, 0)}
                    d = actual[g]
                    if r["location"] == "h" and r["teamId"] != "0":
                        d["local"] = int(r["teamId"])
                    if r["scoreHome"] == "" or r["scoreAway"] == "":
                        continue
                    m = RELOJ.match(r["clock"])
                    if not m:
                        continue
                    elapsed = fin_periodo(int(r["period"])) - (int(m.group(1)) * 60 + float(m.group(2)))
                    margen = int(r["scoreHome"]) - int(r["scoreAway"])
                    if d["t"] and elapsed < d["t"][-1]:
                        continue                                  # orden de la fuente: no retroceder en el tiempo
                    d["t"].append(elapsed)
                    d["m"].append(margen)
                juegos.update({g: (d["local"], d["t"], d["m"]) for g, d in actual.items()})
    return juegos


def main(rotaciones: Path, datasets: Path, carpeta: Path, salida: Path):
    pbp = marcadores(datasets)
    canon_p, canon_j, fecha = {}, {}, {}
    for r in csv.DictReader(open(carpeta / "s3b_partidos.csv", encoding="utf8")):
        if r["fuente"] == "nba_oficial" and r["id_en_fuente"].isdigit() and len(r["id_en_fuente"]) == 10:
            canon_p[r["id_en_fuente"]] = int(r["canonica_id"])
    for r in csv.DictReader(open(carpeta / "s3b_jugadores.csv", encoding="utf8")):
        if r["fuente"] == "nba_oficial" and r["id_en_fuente"].isdigit():
            canon_j[int(r["id_en_fuente"])] = int(r["canonica_id"])
    for r in csv.DictReader(open(carpeta / "s3_juegos.csv", encoding="utf8")):
        fecha[int(r["partido_id"])] = date.fromisoformat(r["fecha"]).toordinal()
    filas, descartados = [], {"sin_pbp": 0, "sin_catalogo": 0, "sin_local": 0, "jugador": 0}
    with gzip.open(rotaciones, "rt", encoding="utf8") as f:
        for linea in f:
            j = json.loads(linea)
            g = j["game_id"]
            pid = canon_p.get(g)
            if pid is None or pid not in fecha:
                descartados["sin_catalogo"] += 1
                continue
            if g not in pbp or not pbp[g][1]:
                descartados["sin_pbp"] += 1
                continue
            local, tiempos, margenes = pbp[g]
            if local is None:
                descartados["sin_local"] += 1
                continue

            def margen_en(instante):
                i = bisect.bisect_right(tiempos, instante)
                return margenes[i - 1] if i else 0

            por_periodo = {}
            for t in j["chronological_lineups"]:
                por_periodo.setdefault(t["period"], {}).setdefault(t["team_id"], []).append(
                    (t["start_elapsed_seconds"], t["end_elapsed_seconds"], t["nba_player_ids"]))
            for periodo, equipos in sorted(por_periodo.items()):
                if local not in equipos or len(equipos) != 2:
                    continue
                visit = next(e for e in equipos if e != local)
                instantes = sorted({ini for lst in equipos.values() for ini, _, _ in lst})
                fin = float(fin_periodo(periodo))
                for k, ini in enumerate(instantes):
                    sig = instantes[k + 1] if k + 1 < len(instantes) else fin
                    a = next((p for i, f_, p in equipos[local] if i <= ini < f_), None)
                    b = next((p for i, f_, p in equipos[visit] if i <= ini < f_), None)
                    if a is None or b is None or sig <= ini:
                        continue
                    try:
                        ca, cb = tuple(canon_j[p] for p in a), tuple(canon_j[p] for p in b)
                    except KeyError:
                        descartados["jugador"] += 1
                        continue
                    filas.append((pid, fecha[pid], sig - ini, margen_en(sig) - margen_en(ini), ca, cb))
    pickle.dump(filas, open(salida, "wb"))
    print(len(filas), "tramos;", descartados)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
