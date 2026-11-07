"""Árbol `data/v3` del scraper de SofaScore del VPS (torneo 132 = NBA) → `nba.dato` mediante `sofascore.cargar`.

Respaldo de la caja oficial de cdn.nba.com: lee solo los partidos TERMINADOS con alineaciones cuyo inicio cae en los últimos `dias` días,
con la hora real en que el scraper los observó (`manifest.json`). Es idempotente (la carga ignora lo ya guardado) y solo añade filas:
no toca otras fuentes, y donde existe la caja oficial gana esta (prioridad 2 de SofaScore en `nba.dato_a_las`).
La conversión es la de `ops/sofascore_a_jsonl.py` (archivo histórico del titular), restringida por fecha.
"""
from collections import Counter
from datetime import UTC, datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from . import sofascore

ET = ZoneInfo("America/New_York")
TORNEO = "132"
TEMPORADAS = {"80229": "2025-26", "100772": "2026-27"}
CLAVES = ("points", "rebounds", "assists", "steals", "blocks", "turnovers", "personalFouls", "plusMinus", "fieldGoalsMade", "fieldGoalAttempts",
          "threePointsMade", "threePointAttempts", "freeThrowsMade", "freeThrowAttempts", "offensiveRebounds", "defensiveRebounds", "secondsPlayed")


def _leer_gz(ruta: Path):
    with gzip.open(ruta, "rt", encoding="utf8") as f:
        return json.load(f)


def _equipo(e: dict) -> dict:
    return {"id": e["id"], "codigo": e.get("nameCode"), "nombre": e.get("name")}


def _periodos(score: dict) -> list:
    return [score[f"period{i}"] for i in range(1, 5) if f"period{i}" in score]


def convertir(raiz: Path, salida: Path, desde: datetime) -> Counter:
    """Escribe `salida` (un partido terminado por línea) con los partidos que empiezan desde `desde`; cuenta lo descartado."""
    raiz, cuenta, vistos = Path(raiz), Counter(), set()
    with gzip.open(salida, "wt", encoding="utf8") as out:
        for sid, temporada in TEMPORADAS.items():
            for calendario in sorted((raiz / "tournaments" / TORNEO / "seasons" / sid / "schedule").glob("*.json.gz")):
                for e in _leer_gz(calendario).get("events", []):
                    if e["id"] in vistos:
                        continue
                    vistos.add(e["id"])
                    if e["status"]["type"] != "finished":
                        cuenta["no_terminado"] += 1
                        continue
                    inicio = datetime.fromtimestamp(e["startTimestamp"], UTC)
                    if inicio < desde:
                        cuenta["viejos"] += 1
                        continue
                    i = str(e["id"])
                    carpeta = raiz / "events" / i[:2] / i[2:5] / i
                    if not (carpeta / "lineups.json.gz").exists() or not (carpeta / "manifest.json").exists():
                        cuenta["sin_alineaciones"] += 1
                        continue
                    alineaciones = _leer_gz(carpeta / "lineups.json.gz")
                    manifest = json.loads((carpeta / "manifest.json").read_text(encoding="utf8"))
                    jugadores = []
                    for lado, clave in (("local", "home"), ("visitante", "away")):
                        for p in alineaciones.get(clave, {}).get("players", []):
                            st = p.get("statistics") or {}
                            jugadores.append({"id": p["player"]["id"], "nombre": p["player"].get("name"), "equipo": lado,
                                              "titular": not p.get("substitute", True), "stats": {k: st[k] for k in CLAVES if k in st}})
                    linea = {"id": e["id"], "temporada": temporada, "fecha_et": inicio.astimezone(ET).date().isoformat(), "inicio_utc": inicio.isoformat(),
                             "local": _equipo(e["homeTeam"]), "visitante": _equipo(e["awayTeam"]),
                             "marcador": {"local": {"total": e["homeScore"].get("current"), "periodos": _periodos(e["homeScore"])},
                                          "visitante": {"total": e["awayScore"].get("current"), "periodos": _periodos(e["awayScore"])}},
                             "observado_utc": manifest["observation"]["observed_at_utc"],
                             "sha256_alineaciones": hashlib.sha256((carpeta / "lineups.json.gz").read_bytes()).hexdigest(),
                             "jugadores": jugadores}
                    out.write(json.dumps(linea, ensure_ascii=False, separators=(",", ":")) + "\n")
                    cuenta["partidos"] += 1
    return cuenta


def cargar_recientes(db, raiz: Path, carpeta: Path, ahora: datetime, dias: int = 4) -> dict:
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"nba_sofascore_{ahora:%Y%m%d}.jsonl.gz"
    cuenta = convertir(raiz, ruta, ahora - timedelta(days=dias))
    resumen = {"ok": True, "eventos": 0, "filas_nuevas": 0, **{f"descartados_{k}": v for k, v in cuenta.items() if k != "partidos"}}
    if cuenta["partidos"]:
        resumen.update(sofascore.cargar(db, ruta))
    return resumen
