"""Arma la carpeta de entrenamiento/evaluación a partir de la exportación `exportar_entrenamiento.sql` (prioridad de fuentes ya resuelta).

    python apps/nba/ops/preparar_datos_entrenamiento.py CARPETA_DE_CSV_S5 CARPETA_DESTINO [CARPETA_CON_CUOTAS]

Deja en el destino los nombres que leen `evaluar_s3.py`, `evaluar_s3b.py`, `evaluar_s4.py`, `entrenar_props.py` y `entrenar_impacto.py`:
s3_juegos.csv, players.jsonl.gz, s2_estados.csv, s3b_jugadores.csv y s3b_partidos.csv. Los ids son los CANÓNICOS de `nba_datos` (el partido y el
jugador de la caja se escriben como su propio id, y los mapas de alias incluyen una fila de identidad para cada canónico), así que una caja de
SofaScore y una de nba_oficial del mismo jugador quedan en el mismo id. Las cuotas (s3_cierres.csv, s3_pinnacle.csv, s4_props.csv.gz) no
dependen de la caja y se copian de la carpeta indicada.
"""
import csv
import gzip
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nba.v2.equipos import NBA_IDS  # noqa: E402

TEAM_ID = {tri: team_id for team_id, tri in NBA_IDS.items()}


def main(origen: Path, destino: Path, cuotas: Path | None):
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origen / "s5_juegos.csv", destino / "s3_juegos.csv")
    shutil.copyfile(origen / "s5_estados.csv", destino / "s2_estados.csv")
    equipo = {int(r["entidad_id"]): r["id_en_fuente"] for r in csv.DictReader(open(origen / "s5_equipos.csv", encoding="utf8"))}
    n = 0
    with gzip.open(destino / "players.jsonl.gz", "wt", encoding="utf8") as out:
        for r in csv.DictReader(open(origen / "s5_caja.csv", encoding="utf8")):
            tri = equipo.get(int(r["equipo_id"]))
            if tri not in TEAM_ID:
                continue
            out.write(json.dumps({"game_id": r["partido_id"], "player_id": int(r["jugador_id"]), "team_id": TEAM_ID[tri], "participated": True,
                                  "minutes": float(r["minutos"]), "points": float(r["puntos"] or 0), "rebounds": float(r["rebotes"] or 0),
                                  "assists": float(r["asistencias"] or 0), "threes": float(r["triples"] or 0),
                                  "plus_minus": float(r["mas_menos"]) if r["mas_menos"] else None}) + "\n")
            n += 1
    for nombre, destino_nombre in (("s5_jugadores.csv", "s3b_jugadores.csv"), ("s5_partidos.csv", "s3b_partidos.csv")):
        filas = list(csv.DictReader(open(origen / nombre, encoding="utf8")))
        canonicos = {int(r["canonica_id"]) for r in filas if r["canonica_id"]} | {int(r["entidad_id"]) for r in filas if not r["canonica_id"]}
        with open(destino / destino_nombre, "w", encoding="utf8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["entidad_id", "canonica_id", "fuente", "id_en_fuente"])
            for r in filas:
                w.writerow([r["entidad_id"], r["canonica_id"] or r["entidad_id"], r["fuente"], r["id_en_fuente"]])
            for c in sorted(canonicos):                      # identidad: el id canónico se escribe a sí mismo (la caja exportada usa ids canónicos)
                w.writerow([c, c, "nba_oficial", str(c)])
    if cuotas:
        for nombre in ("s3_cierres.csv", "s3_pinnacle.csv", "s4_props.csv.gz"):
            shutil.copyfile(cuotas / nombre, destino / nombre)
    print("filas de caja", n, "->", destino)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) > 3 else None)
