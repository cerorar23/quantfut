"""Convierte el archivo local de SofaScore (torneo 132 = NBA) en un archivo compacto, un partido terminado por línea, que lee el cargador.

    python apps/nba/ops/sofascore_a_jsonl.py RAIZ_V3 SALIDA.jsonl.gz

Lee `tournaments/132/seasons/<id>/schedule/*.json.gz` (calendario y marcadores) y, de cada `events/<id[:2]>/<id[2:5]>/<id>/`, `lineups.json.gz`
y `manifest.json` (hora de observación). Solo partidos terminados con alineaciones; lo demás se cuenta y se informa. Los originales no se tocan:
el archivo compacto guarda la huella sha256 de los de cada partido.
"""
import collections
import datetime
import glob
import gzip
import hashlib
import json
import os
import sys
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
TEMPORADAS = {"38191": "2021-22", "45096": "2022-23", "54105": "2023-24", "65360": "2024-25", "80229": "2025-26", "100772": "2026-27"}
CLAVES = ("points", "rebounds", "assists", "steals", "blocks", "turnovers", "personalFouls", "plusMinus", "fieldGoalsMade", "fieldGoalAttempts",
          "threePointsMade", "threePointAttempts", "freeThrowsMade", "freeThrowAttempts", "offensiveRebounds", "defensiveRebounds", "secondsPlayed")


def leer_gz(ruta):
    with gzip.open(ruta, "rt", encoding="utf8") as f:
        return json.load(f)


def equipo(e):
    return {"id": e["id"], "codigo": e.get("nameCode"), "nombre": e.get("name")}


def periodos(score):
    return [score[f"period{i}"] for i in range(1, 5) if f"period{i}" in score]


def convertir(raiz, salida):
    cuenta = collections.Counter()
    vistos = set()
    with gzip.open(salida, "wt", encoding="utf8") as out:
        for sid, temporada in TEMPORADAS.items():
            archivos = sorted(glob.glob(os.path.join(raiz, "tournaments", "132", "seasons", sid, "schedule", "*.json.gz")))
            for f in archivos:
                for e in leer_gz(f).get("events", []):
                    if e["id"] in vistos:
                        continue
                    vistos.add(e["id"])
                    if e["status"]["type"] != "finished":
                        cuenta["no_terminado"] += 1
                        continue
                    i = str(e["id"])
                    d = os.path.join(raiz, "events", i[:2], i[2:5], i)
                    if not os.path.exists(os.path.join(d, "lineups.json.gz")):
                        cuenta["sin_alineaciones"] += 1
                        continue
                    ruta_l = os.path.join(d, "lineups.json.gz")
                    lu = leer_gz(ruta_l)
                    manifest = json.load(open(os.path.join(d, "manifest.json"), encoding="utf8"))
                    jugadores = []
                    for lado, clave in (("local", "home"), ("visitante", "away")):
                        for p in lu.get(clave, {}).get("players", []):
                            st = p.get("statistics") or {}
                            jugadores.append({"id": p["player"]["id"], "nombre": p["player"].get("name"), "equipo": lado, "titular": not p.get("substitute", True),
                                              "stats": {k: st[k] for k in CLAVES if k in st}})
                    inicio = datetime.datetime.fromtimestamp(e["startTimestamp"], datetime.UTC)
                    linea = {"id": e["id"], "temporada": temporada, "fecha_et": inicio.astimezone(ET).date().isoformat(), "inicio_utc": inicio.isoformat(),
                             "local": equipo(e["homeTeam"]), "visitante": equipo(e["awayTeam"]),
                             "marcador": {"local": {"total": e["homeScore"].get("current"), "periodos": periodos(e["homeScore"])},
                                          "visitante": {"total": e["awayScore"].get("current"), "periodos": periodos(e["awayScore"])}},
                             "observado_utc": manifest["observation"]["observed_at_utc"], "sha256_alineaciones": hashlib.sha256(open(ruta_l, "rb").read()).hexdigest(),
                             "jugadores": jugadores}
                    out.write(json.dumps(linea, ensure_ascii=False, separators=(",", ":")) + "\n")
                    cuenta["partidos"] += 1
                    cuenta[f"partidos_{temporada}"] += 1
                    cuenta["filas_jugador"] += len(jugadores)
                    cuenta["con_minutos"] += sum(1 for j in jugadores if j["stats"].get("secondsPlayed"))
    return cuenta


if __name__ == "__main__":
    c = convertir(sys.argv[1], sys.argv[2])
    print(dict(c), "bytes", os.path.getsize(sys.argv[2]))
