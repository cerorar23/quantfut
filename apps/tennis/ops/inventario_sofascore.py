"""Inventario SOLO LECTURA de partidos de tenis en el archivo SofaScore local.

Dos fuentes dentro del mismo arbol (--root):
  1. tournaments/<id>/seasons/<id>/schedule/round_N.json.gz  (calendario por ronda)
  2. events/<id[:2]>/<id[2:5]>/<id>/event.json.gz            (partido completo)
Se conserva todo evento con tournament.category.sport.slug == 'tennis'. Para
cada uno se leen event.json.gz (defaultPeriodCount, fecha de observacion y
hash del manifest) y los ficheros presentes en su carpeta.

Uso (Python 3.12, desde la raiz del worktree):
  python -I apps/tennis/ops/inventario_sofascore.py --root "C:/Users/huye/Documents/SOFASCORE/data/v3" --out docs/tenis_auditoria_tablas
Escribe solo en --out. No modifica el archivo de origen.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

NIVEL_POR_PUNTOS = {2000: "Grand Slam", 1500: "ATP Finals", 1000: "Masters 1000 / WTA 1000",
                    500: "ATP/WTA 500", 250: "ATP/WTA 250"}


def _leer_gz(ruta: Path):
    with gzip.open(ruta, "rt", encoding="utf-8") as f:
        return json.load(f)


def _fecha(ts) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _es_dobles(evento: dict) -> bool:
    for lado in ("homeTeam", "awayTeam"):
        equipo = evento.get(lado) or {}
        if equipo.get("subTeams") or "/" in (equipo.get("name") or ""):
            return True
        if str(equipo.get("type") or "").lower() == "doubles":
            return True
    return "doubles" in str((evento.get("season") or {}).get("name", "")).lower()


def _registro(ev: dict, origen: str, ruta_rel: str) -> dict:
    torneo = ev.get("tournament") or {}
    cat = torneo.get("category") or {}
    ut = torneo.get("uniqueTournament") or {}
    temporada = ev.get("season") or {}
    ronda = ev.get("roundInfo") or {}
    pts = ut.get("tennisPoints")
    return {
        "event_id": ev.get("id"),
        "fuente_evento": origen,
        "archivo_origen": ruta_rel,
        "fecha_utc": _fecha(ev.get("startTimestamp")),
        "circuito_categoria": cat.get("slug") or "",
        "torneo": torneo.get("name") or "",
        "torneo_unico_id": ut.get("id"),
        "torneo_unico": ut.get("name") or "",
        "superficie": ut.get("groundType") or "",
        "tennis_points": pts,
        "nivel": NIVEL_POR_PUNTOS.get(pts, "otro/desconocido"),
        "temporada_id": temporada.get("id"),
        "temporada": temporada.get("name") or "",
        "ano_temporada": temporada.get("year") or "",
        "ronda": ronda.get("name") or (f"ronda_{ronda.get('round')}" if ronda else ""),
        "estado": (ev.get("status") or {}).get("type") or "",
        "codigo_ganador": ev.get("winnerCode"),
        "mejor_de": ev.get("defaultPeriodCount"),
        "dobles": _es_dobles(ev),
        "jugador_local": (ev.get("homeTeam") or {}).get("name") or "",
        "jugador_visitante": (ev.get("awayTeam") or {}).get("name") or "",
        "id_local": (ev.get("homeTeam") or {}).get("id"),
        "id_visitante": (ev.get("awayTeam") or {}).get("id"),
        "sets_local": (ev.get("homeScore") or {}).get("current"),
        "sets_visitante": (ev.get("awayScore") or {}).get("current"),
        "tiebreak_en_marcador": any(k.endswith("TieBreak") for k in (ev.get("homeScore") or {})),
    }


def recoger_schedule(root: Path):
    eventos: dict[int, dict] = {}
    n_archivos = 0
    errores = []
    for ruta in sorted((root / "tournaments").glob("*/seasons/*/schedule/round_*.json.gz")):
        n_archivos += 1
        try:
            datos = _leer_gz(ruta)
        except Exception as exc:
            errores.append(f"{ruta}: {type(exc).__name__}")
            continue
        for ev in datos.get("events", []):
            if ((ev.get("tournament") or {}).get("category") or {}).get("sport", {}).get("slug") != "tennis":
                continue
            if ev.get("id") is None:
                continue
            rel = str(ruta.relative_to(root)).replace("\\", "/")
            eventos.setdefault(ev["id"], _registro(ev, "schedule", rel))
    return eventos, n_archivos, errores


def recoger_events(root: Path):
    """Recorre las 43k carpetas de events/ leyendo solo event.json.gz."""
    eventos: dict[int, dict] = {}
    n_carpetas = 0
    n_sin_event = 0
    errores = []
    base = root / "events"
    for a in os.scandir(base):
        for b in os.scandir(a.path):
            for c in os.scandir(b.path):
                n_carpetas += 1
                ruta = Path(c.path) / "event.json.gz"
                if not ruta.exists():
                    n_sin_event += 1
                    continue
                try:
                    ev = _leer_gz(ruta)
                except Exception as exc:
                    errores.append(f"{ruta}: {type(exc).__name__}")
                    continue
                if ((ev.get("tournament") or {}).get("category") or {}).get("sport", {}).get("slug") != "tennis":
                    continue
                rel = str(ruta.relative_to(root)).replace("\\", "/")
                eventos[ev["id"]] = _registro(ev, "events", rel)
    return eventos, n_carpetas, n_sin_event, errores


def enriquecer_carpeta(root: Path, fila: dict) -> dict:
    eid = fila["event_id"]
    carpeta = root / "events" / str(eid)[:2] / str(eid)[2:5] / str(eid)
    extra = {"carpeta_evento_existe": carpeta.is_dir(), "ficheros_evento": "",
             "n_ficheros_evento": 0, "bytes_evento": 0, "observed_at_utc": "",
             "sha256_event_json": "", "estado_manifest": ""}
    if not carpeta.is_dir():
        return {**fila, **extra}
    archivos = [p for p in carpeta.iterdir() if p.is_file()]
    extra["ficheros_evento"] = ";".join(sorted(p.name for p in archivos))
    extra["n_ficheros_evento"] = len(archivos)
    extra["bytes_evento"] = sum(p.stat().st_size for p in archivos)
    mf = carpeta / "manifest.json"
    if mf.exists():
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
            extra["observed_at_utc"] = (m.get("observation") or {}).get("observed_at_utc", "")
            sl = (m.get("slices") or {}).get("event") or {}
            extra["sha256_event_json"] = sl.get("sha256", "")
            extra["estado_manifest"] = ";".join(
                f"{k}={v.get('state')}" for k, v in sorted((m.get("slices") or {}).items()))
        except Exception:
            extra["estado_manifest"] = "manifest_ilegible"
    return {**fila, **extra}


def escribir_csv(ruta: Path, filas: list[dict]):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if not filas:
        ruta.write_text("", encoding="utf-8")
        return
    claves = list(filas[0].keys())
    for f in filas:
        for k in f:
            if k not in claves:
                claves.append(k)
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=claves)
        w.writeheader()
        w.writerows(filas)


def resumen(filas: list[dict], claves: tuple[str, ...]) -> list[dict]:
    c = Counter(tuple(str(f.get(k, "")) for k in claves) for f in filas)
    return [dict(zip(claves, k), partidos=v) for k, v in sorted(c.items(), key=lambda x: (-x[1], x[0]))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    sched, n_sched, err_sched = recoger_schedule(args.root)
    ev_map, n_carp, n_sin, err_ev = recoger_events(args.root)

    unidos: dict[int, dict] = dict(ev_map)
    for eid, fila in sched.items():
        if eid in unidos:
            unidos[eid]["fuente_evento"] = "events+schedule"
            unidos[eid]["archivo_origen_schedule"] = fila["archivo_origen"]
        else:
            unidos[eid] = fila

    filas = [enriquecer_carpeta(args.root, f) for f in unidos.values()]
    filas.sort(key=lambda f: (f["fecha_utc"], f["event_id"] or 0))
    escribir_csv(args.out / "sofascore_local_tenis_eventos.csv", filas)

    print(f"schedule_archivos_leidos={n_sched} errores={len(err_sched)}")
    print(f"tenis_en_schedule={len(sched)}")
    print(f"carpetas_events_recorridas={n_carp} sin_event_json={n_sin} errores={len(err_ev)}")
    print(f"tenis_en_events={len(ev_map)}")
    print(f"tenis_unicos_total={len(filas)} (solo_schedule={sum(1 for f in filas if f['fuente_evento']=='schedule')}, "
          f"solo_events={sum(1 for f in filas if f['fuente_evento']=='events')}, "
          f"ambos={sum(1 for f in filas if f['fuente_evento']=='events+schedule')})")
    print(f"con_carpeta_events={sum(1 for f in filas if f['carpeta_evento_existe'])}")
    print(f"bytes_carpetas_eventos={sum(f['bytes_evento'] for f in filas)}")
    if filas:
        print(f"rango_fechas={filas[0]['fecha_utc']} .. {filas[-1]['fecha_utc']}")
    for nombre, claves in [
        ("resumen_circuito", ("circuito_categoria",)),
        ("resumen_circuito_nivel_superficie", ("circuito_categoria", "nivel", "superficie")),
        ("resumen_circuito_dobles_mejor_de", ("circuito_categoria", "dobles", "mejor_de")),
        ("resumen_ano_circuito", ("ano_temporada", "circuito_categoria")),
        ("resumen_ronda", ("circuito_categoria", "ronda")),
        ("resumen_estado", ("circuito_categoria", "estado")),
        ("resumen_torneo", ("circuito_categoria", "torneo_unico", "ano_temporada")),
    ]:
        r = resumen(filas, claves)
        escribir_csv(args.out / f"sofascore_local_{nombre}.csv", r)
        print(f"--- {nombre}: {len(r)} filas")
    if err_sched or err_ev:
        (args.out / "sofascore_local_errores_lectura.txt").write_text(
            "\n".join(err_sched + err_ev), encoding="utf-8")


if __name__ == "__main__":
    main()
