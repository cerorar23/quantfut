"""
Prueba histórica del reto escalera al 80 % en 7 días con fútbol, NBA y tenis
(decisión del usuario, 2026-10-28: «buscamos el acierto, no la cuota»; el reto
puede esperar al pronóstico seguro, tener varios escalones un día y durar como
mucho 7 días).

Datos (ninguno se descarga aquí):
- Fútbol: football-data, 7 ligas 2019-2025 (`.local/fd_cache`), 1X2 y goles
  2,5, Pinnacle sin margen y la mejor cuota de la lista (`escalera_prueba.candidatos`).
- NBA: ganador al cierre de bet365 vía BetsAPI (2023-2026, normalizado en
  `apps/nba/.local/normalized/nba_betsapi_odds_20261024`), sin margen por Shin.
- Tenis: Tennis-Data ATP y WTA (`data/tennis/tennis_data_manual`, descargado a
  mano por el titular, uso sin lucro), Pinnacle sin margen y la cuota de bet365.
  Se excluyen los «walkover»; en las retiradas gana el que pasa de ronda.

Cada candidato es un lado de un partido con su probabilidad justa `p`, la cuota
que se puede tomar y si ganó. La simulación recorre los días en orden y repite
la regla de `publish/escalera.py`: un reto de PASOS escalones, cada uno con
p ≥ `escalera.umbral(0,80, ∏ p elegidos, faltan)`, el más probable primero,
hasta POR_DIA el mismo día en partidos distintos, y DIAS_MAX días; pasado el
plazo queda «expirado». Un reto a la vez: el siguiente empieza al cerrarse.

LÍMITES: solo ganador (y goles 2,5 en fútbol); en vivo hay más líneas. Las
cuotas de NBA y tenis son de cierre (la decisión real es antes). La NBA no
tiene Pinnacle en estos datos: su probabilidad sale de bet365 sin margen.

Uso: python -m qf.eval.escalera_multideporte [--out .local/escalera_multideporte.json]
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import two_way_devig
from ..publish import escalera as es
from . import alta_prob_calibracion as apc
from . import escalera_prueba as ep
from . import soft_vs_sharp as sv

NBA = Path("apps/nba/.local/normalized/nba_betsapi_odds_20261024/odds.jsonl.gz")
TENIS = Path("data/tennis/tennis_data_manual")
# Tope por escalón: lo calibrado. Fútbol y NBA, el de la escalera; tenis, 0,95-1,00
# medido en Tennis-Data 2019-2026 (n=201, 95,8 % prometido, 98,0 % real).
TOPE = {"futbol": es.PROB_MAX, "nba": es.PROB_MAX, "tenis": 0.97}
TRAMOS = (0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.0)


def futbol(cache_dir: Path) -> pd.DataFrame:
    raw, _ = sv.load_csvs(apc.LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    return ep.candidatos(raw, 1.01, 2.0).assign(deporte="futbol")


def nba(path: Path) -> pd.DataFrame:
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for linea in f:
            d = json.loads(linea)
            if d["market"] != "ml_game" or not d.get("close_fresh") or d.get("y_close") is None:
                continue
            c = d["close"]
            p1, p2 = two_way_devig(c["p1"], c["p2"], settings.devig_method)
            for p, price, won in ((p1, c["p1"], d["y_close"] == 1), (p2, c["p2"], d["y_close"] == 0)):
                rows.append({"fecha": pd.Timestamp(d["date"]), "evento": "n" + d["event_id"],
                             "p": float(p), "price": float(price), "won": bool(won)})
    return pd.DataFrame(rows).assign(deporte="nba")


def tenis(base: Path, desde: int = 2019) -> pd.DataFrame:
    rows = []
    for tour in ("atp", "wta"):
        for f in sorted((base / tour).glob("*.xls*")):
            if int(f.name[:4]) < desde:
                continue
            d = pd.read_excel(f)
            d = d[d["Comment"].astype(str).str.startswith(("Completed", "Retired"))]
            for i, r in enumerate(d.to_dict("records")):
                cuotas = [r.get(k) for k in ("PSW", "PSL", "B365W", "B365L")]
                if not all(isinstance(x, (int, float)) and np.isfinite(x) and x > 1 for x in cuotas):
                    continue
                pw, pl = two_way_devig(float(cuotas[0]), float(cuotas[1]), settings.devig_method)
                for p, price, won in ((pw, cuotas[2], True), (pl, cuotas[3], False)):
                    rows.append({"fecha": pd.Timestamp(r["Date"]), "evento": f"t{tour}{f.name[:4]}_{i}",
                                 "p": float(p), "price": float(price), "won": won})
    return pd.DataFrame(rows).assign(deporte="tenis")


def candidatos(cache_dir: Path, nba_path: Path, tenis_dir: Path) -> pd.DataFrame:
    c = pd.concat([futbol(cache_dir), nba(nba_path), tenis(tenis_dir)], ignore_index=True)
    return c[["fecha", "deporte", "evento", "p", "price", "won"]]


def calibracion(c: pd.DataFrame) -> list[dict]:
    """Prometido frente a real por deporte y tramo, con el valor esperado a la cuota tomable."""
    c = c[c["price"] >= es.CUOTA_MIN].assign(tramo=lambda d: pd.cut(d["p"], TRAMOS, right=False))
    out = []
    for (dep, tramo), g in c.groupby(["deporte", "tramo"], observed=True):
        out.append({"deporte": dep, "tramo": str(tramo), "n": int(len(g)),
                    "prometido": round(float(g["p"].mean()) * 100, 2),
                    "real": round(float(g["won"].mean()) * 100, 2),
                    "cuota": round(float(g["price"].mean()), 3),
                    "ev_pct": round(float((g["p"] * g["price"] - 1).mean()) * 100, 2),
                    "roi_pct": round(float(np.where(g["won"], g["price"] - 1, -1).mean()) * 100, 2)})
    return out


def simular(c: pd.DataFrame, deportes: tuple[str, ...], desde: str, hasta: str,
            pasos: int = 2, por_dia: int = es.POR_DIA, dias: int = es.DIAS_MAX,
            objetivo: float = es.PROB_RETO, orden: str = "p") -> dict:
    """La regla de `escalera.py` sobre los días de [desde, hasta]. `orden`: "p" o "valor"."""
    d = c[c["deporte"].isin(deportes) & (c["price"] >= es.CUOTA_MIN)
          & (c["price"] <= es.CUOTA_MAX) & (c["p"] <= c["deporte"].map(TOPE))]
    d = d[(d["fecha"] >= desde) & (d["fecha"] <= hasta)].assign(dia=lambda x: x["fecha"].dt.normalize())
    clave = ["p", "price"] if orden == "p" else ["ev", "p"]
    d = d.assign(ev=d["p"] * d["price"])
    pool = {k: g.sort_values(clave, ascending=False) for k, g in d.groupby("dia")}
    calendario = pd.date_range(pd.Timestamp(desde), pd.Timestamp(hasta), freq="D")
    primero = es.umbral(objetivo, 1.0, pasos)
    retos, i = [], 0
    while i < len(calendario):
        # El reto se crea con su primer escalón: un día sin ninguno no abre plazo.
        g = pool.get(calendario[i])
        if g is None or not (g["p"] >= primero).any():
            i += 1
            continue
        saldo, prob, n, estado, fin = 1.0, 1.0, 0, "expirado", dias - 1
        for j in range(min(dias, len(calendario) - i)):
            g = pool.get(calendario[i + j])
            hoy, usados = 0, set()
            for row in ([] if g is None else g.itertuples()):
                if hoy >= por_dia:
                    break
                if row.evento in usados or row.p < es.umbral(objetivo, prob, pasos - n):
                    continue
                usados.add(row.evento)
                hoy, n, prob = hoy + 1, n + 1, prob * row.p
                if not row.won:
                    estado = "fallido"
                    break
                saldo *= row.price
                if n >= pasos:
                    estado = "completado"
                    break
            if estado != "expirado":
                fin = j
                break
        retos.append({"estado": estado, "dias": fin + 1, "escalones": n, "saldo": saldo,
                      "prob": prob, "ganancia": -1.0 if estado == "fallido" else saldo - 1.0})
        i += fin + 1
    if not retos:
        return {"retos": 0}
    r = pd.DataFrame(retos)
    comp = r["estado"] == "completado"
    años = (pd.Timestamp(hasta) - pd.Timestamp(desde)).days / 365.25
    return {"retos": int(len(r)), "por_año": round(len(r) / años, 1),
            "completados_pct": round(float(comp.mean()) * 100, 1),
            "fallidos_pct": round(float((r["estado"] == "fallido").mean()) * 100, 1),
            "expirados_pct": round(float((r["estado"] == "expirado").mean()) * 100, 1),
            "prometido_pct": round(float(r.loc[r["estado"] != "expirado", "prob"].mean()) * 100, 1),
            "dias_medios": round(float(r["dias"].mean()), 1),
            "cobro_completado": round(float(r.loc[comp, "saldo"].mean()), 3) if comp.any() else None,
            "roi_pct": round(float(r["ganancia"].mean()) * 100, 1)}


VENTANAS = {
    "futbol_tenis_2019_2025": (("futbol", "tenis"), "2019-08-02", "2025-05-25"),
    "tres_deportes_2023_2025": (("futbol", "nba", "tenis"), "2023-10-24", "2025-05-25"),
    "solo_futbol_2023_2025": (("futbol",), "2023-10-24", "2025-05-25"),
    "solo_tenis_2019_2025": (("tenis",), "2019-01-01", "2026-01-14"),
}


def run(cache_dir: Path, nba_path: Path, tenis_dir: Path) -> dict:
    c = candidatos(cache_dir, nba_path, tenis_dir)
    variantes = {"regla": {}, "un_escalon_al_dia": {"por_dia": 1},
                 "el_de_mas_valor": {"orden": "valor"}, "tres_escalones": {"pasos": 3}}
    return {"candidatos": {k: int(v) for k, v in c["deporte"].value_counts().items()},
            "calibracion": calibracion(c),
            "retos": {f"{v}_{nombre}": simular(c, deps, a, b, **kw)
                      for v, (deps, a, b) in VENTANAS.items() for nombre, kw in variantes.items()}}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    a.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    a.add_argument("--nba", type=Path, default=NBA)
    a.add_argument("--tenis", type=Path, default=TENIS)
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    txt = json.dumps(run(args.cache, args.nba, args.tenis), indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(txt, encoding="utf-8")
    print(txt)
