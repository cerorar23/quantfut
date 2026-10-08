"""
Prueba histórica del reto escalera (pedido del usuario, 2026-10-08).

Repite escaleras sobre football-data (las 7 ligas de formato principal,
2019-2025) con las cuotas PRE-CIERRE: decide con Pinnacle temprano sin margen y
la mejor cuota de las casas de la lista disponibles en los CSV (bet365 y
1xBet; los totales 2,5 solo traen bet365). Compara la regla de partida
(cuota 1,25-1,40 elegida por probabilidad o por cuota) con la de `escalera.py`
(además, cuota ≥ precio justo).

Una escalera: un escalón por día como máximo, el siguiente al día siguiente
del anterior, todo el saldo en cada escalón. Se pierde al fallar uno. Las
cuentas del saldo son las de `escalera.estado`, las mismas que en vivo.

LÍMITES: sin doble oportunidad ni "marca un equipo" (no hay cuotas históricas)
y solo la línea 2,5 de goles. El mercado mide; el resultado solo se usa al
liquidar.

Uso: python -m qf.eval.escalera_prueba [--out .local/escalera_prueba.json]
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig, two_way_devig
from ..publish import escalera as es
from . import alta_prob_calibracion as apc
from . import soft_vs_sharp as sv

CASAS_1X2 = {"B365": "bet365", "1XB": "1xbet", "BW": "bwin", "WH": "william_hill",
             "IW": "interwetten", "VC": "betvictor"}


def _num(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) and np.isfinite(x) and x > 1.0 else None


def candidatos(raw: pd.DataFrame, cuota_min: float = es.CUOTA_MIN,
               cuota_max: float = es.CUOTA_MAX) -> pd.DataFrame:
    """Una fila por selección cuya mejor cuota de la lista cae en el rango."""
    casas = [c for c, b in CASAS_1X2.items() if b in settings.soft_books]
    rows = []
    for d in raw.to_dict("records"):
        fecha = pd.to_datetime(d.get("Date"), dayfirst=True, errors="coerce")
        q = [_num(d.get(k)) for k in ("PSH", "PSD", "PSA")]
        if pd.isna(fecha) or None in q or pd.isna(d.get("FTHG")) or pd.isna(d.get("FTAG")):
            continue
        p = devig(q, settings.devig_method)
        hg, ag = int(d["FTHG"]), int(d["FTAG"])
        ganador = 0 if hg > ag else 1 if hg == ag else 2
        for i, sel in enumerate(("home", "draw", "away")):
            precios = [x for x in (_num(d.get(f"{c}{'HDA'[i]}")) for c in casas) if x]
            if precios and cuota_min <= max(precios) <= cuota_max:
                rows.append({"fecha": fecha, "market": "h2h", "sel": sel, "p": float(p[i]),
                             "price": max(precios), "won": ganador == i})
        o, u = _num(d.get("B365>2.5")), _num(d.get("B365<2.5"))
        po, pu = _num(d.get("P>2.5")), _num(d.get("P<2.5"))
        if "bet365" in settings.soft_books and None not in (o, u, po, pu):
            p_over, p_under = two_way_devig(po, pu, settings.devig_method)
            for sel, price, prob, won in (("over", o, p_over, hg + ag > 2.5),
                                          ("under", u, p_under, hg + ag < 2.5)):
                if cuota_min <= price <= cuota_max:
                    rows.append({"fecha": fecha, "market": "totals", "sel": sel,
                                 "p": float(prob), "price": price, "won": won})
    c = pd.DataFrame(rows)
    if not c.empty:
        c["ev"] = c["p"] * c["price"] - 1.0
    return c


REGLAS = {
    # La regla de partida: dentro del rango, el más probable del día.
    "rango_mas_probable": lambda g: g.sort_values("p", ascending=False),
    # La regla de partida eligiendo la cuota más baja.
    "rango_cuota_minima": lambda g: g.sort_values("price"),
    # La de escalera.py: además cuota ≥ justa, el de mayor valor esperado.
    "valor": lambda g: g[g["ev"] >= es.EV_MIN].sort_values(["ev", "p"], ascending=False),
}


def simular(c: pd.DataFrame, regla: str, pasos: int = 3,
            freeroll_x: float | None = es.FREEROLL_X) -> dict:
    stake = es.STAKE
    retos, actual = [], []
    for _, g in sorted(c.groupby(c["fecha"].dt.date), key=lambda kv: kv[0]):
        elegidos = REGLAS[regla](g)
        if elegidos.empty:
            continue
        e = elegidos.iloc[0]
        actual.append(es.Paso(len(actual) + 1, float(e["price"]), "win" if e["won"] else "loss"))
        st = es.estado(stake, pasos, freeroll_x, actual)
        if st["estado"] in ("completado", "fallido"):
            retos.append(st)
            actual = []
    if not retos:
        return {"retos": 0}
    ganancia = sum(r["ganancia"] for r in retos)
    return {"retos": len(retos),
            "completados_pct": round(sum(r["estado"] == "completado" for r in retos)
                                     / len(retos) * 100, 1),
            "ganancia_media_por_reto": float(round(ganancia / len(retos), 2)),
            "roi_pct": float(round(ganancia / (stake * len(retos)) * 100, 1))}


def run(cache_dir: Path = Path(".local/fd_cache")) -> dict:
    raw, dataset = sv.load_csvs(apc.LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    c = candidatos(raw)

    def bloque(g: pd.DataFrame) -> dict:
        return {"n": int(len(g)), "prob_media": round(float(g["p"].mean()) * 100, 1),
                "acierto": round(float(g["won"].mean()) * 100, 1),
                "ev_medio_pct": round(float(g["ev"].mean()) * 100, 2),
                "roi_pct": round(float(np.where(g["won"], g["price"] - 1, -1).mean()) * 100, 2),
                "dias": int(g["fecha"].dt.date.nunique())} if len(g) else {"n": 0}

    return {
        "dataset": dataset,
        "rango": [es.CUOTA_MIN, es.CUOTA_MAX],
        "escalones": {"todos": bloque(c), "con_valor": bloque(c[c["ev"] >= es.EV_MIN])},
        "escaleras": {f"{regla}_{n}_pasos{'_freeroll' if fr else ''}": simular(c, regla, n, fr)
                      for regla in REGLAS for n in es.LONGITUDES for fr in (None, es.FREEROLL_X)},
    }


if __name__ == "__main__":
    a = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    a.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    rep = run(args.cache)
    txt = json.dumps(rep, indent=2, ensure_ascii=False, default=str)
    if args.out:
        args.out.write_text(txt, encoding="utf-8")
    print(txt)
