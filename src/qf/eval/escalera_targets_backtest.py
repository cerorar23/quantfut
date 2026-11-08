"""
Backtest riguroso de los 6 Retos Escalera con Objetivos de Cuota (2026):
TARGETS = [5.5, 10.2, 15.3, 20.5, 30.3, 40.2]

Reglas:
- Cuotas tomables: 1.20 a 2.10
- Probabilidad mínima por escalón: >= 69.0 %
- Tope máximo de escalones: 10
- Freeroll: al llegar a 2.5x stake inicial (25.00 u en base 10), se asegura el stake (10 u)
  y se continúa jugando a riesgo cero.
- Multideporte: Fútbol (football-data 7 ligas), Tenis (Tennis-Data ATP/WTA) y NBA (BetsAPI)
- Preservación de Push / Void: si hay empate en línea entera, se preserva el saldo.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
import numpy as np
import pandas as pd

from qf.config import settings
from qf.publish import escalera as es
from qf.eval import escalera_multideporte as em

TARGETS = (5.5, 10.2, 15.3, 20.5, 30.3, 40.2)
MAX_ESCALONES = 10
STAKE_BASE = Decimal("10.00")
FREEROLL_X = 2.5


def simular_target(c: pd.DataFrame, deportes: tuple[str, ...], desde: str, hasta: str,
                   target: float, max_pasos: int = MAX_ESCALONES,
                   freeroll_x: float = FREEROLL_X,
                   dias: int = es.DIAS_MAX, por_dia: int = es.POR_DIA) -> dict:
    d = c[c["deporte"].isin(deportes) & (c["price"] >= es.CUOTA_MIN)
          & (c["price"] <= es.CUOTA_MAX) & (c["p"] <= c["deporte"].map(em.TOPE))
          & (c["p"] >= es.PROB_MIN)]
    d = d[(d["fecha"] >= desde) & (d["fecha"] <= hasta)].assign(dia=lambda x: x["fecha"].dt.normalize())
    
    # Orden científico 2026: el más probable primero, luego mejor cuota
    pool = {k: g.sort_values(["p", "price"], ascending=[False, False]) for k, g in d.groupby("dia")}
    calendario = pd.date_range(pd.Timestamp(desde), pd.Timestamp(hasta), freq="D")
    
    retos = []
    i = 0
    stake = float(STAKE_BASE)
    target_cobro = stake * target
    
    while i < len(calendario):
        g = pool.get(calendario[i])
        if g is None or g.empty:
            i += 1
            continue
            
        saldo = stake
        retirado = 0.0
        ganados = 0
        n_pasos = 0
        estado = "expirado"
        fin = dias - 1
        freeroll_activado = False
        prob_conjunta = 1.0
        
        for j in range(min(dias, len(calendario) - i)):
            g_dia = pool.get(calendario[i + j])
            if g_dia is None or g_dia.empty:
                continue
                
            hoy = 0
            usados = set()
            for row in g_dia.itertuples():
                if hoy >= por_dia:
                    break
                if row.evento in usados or row.p < es.PROB_MIN:
                    continue
                    
                usados.add(row.evento)
                hoy += 1
                n_pasos += 1
                prob_conjunta *= row.p
                
                # Resultado
                if not row.won:
                    estado = "fallido"
                    saldo = 0.0
                    break
                    
                saldo *= row.price
                ganados += 1
                
                # Check Freeroll
                if freeroll_x and not freeroll_activado and saldo >= freeroll_x * stake:
                    retirado = stake
                    saldo -= stake
                    freeroll_activado = True
                    
                # Check Meta de cobro alcanzada o tope de pasos
                if (saldo + retirado) >= target_cobro or ganados >= max_pasos:
                    estado = "completado"
                    break
                    
            if estado != "expirado":
                fin = j
                break
                
        ganancia_neta = (saldo + retirado) - stake
        retos.append({
            "target": target,
            "estado": estado,
            "dias": fin + 1,
            "escalones": ganados,
            "freeroll": freeroll_activado,
            "cobro_total": saldo + retirado,
            "ganancia": ganancia_neta,
            "prob_conjunta": prob_conjunta
        })
        i += fin + 1
        
    if not retos:
        return {"target": target, "retos": 0}
        
    df = pd.DataFrame(retos)
    n_tot = len(df)
    comp = df["estado"] == "completado"
    fall = df["estado"] == "fallido"
    expi = df["estado"] == "expirado"
    free = df["freeroll"]
    
    # Drawdown acumulado
    cum_pnl = df["ganancia"].cumsum()
    peak = cum_pnl.cummax()
    dd = peak - cum_pnl
    max_dd = float(dd.max()) if len(dd) else 0.0
    
    return {
        "target": target,
        "retos_totales": n_tot,
        "completados_n": int(comp.sum()),
        "completados_pct": round(float(comp.mean()) * 100, 2),
        "fallidos_n": int(fall.sum()),
        "fallidos_pct": round(float(fall.mean()) * 100, 2),
        "expirados_n": int(expi.sum()),
        "expirados_pct": round(float(expi.mean()) * 100, 2),
        "freerolls_asegurados_pct": round(float(free.mean()) * 100, 2),
        "escalones_promedio_completados": round(float(df.loc[comp, "escalones"].mean()), 2) if comp.any() else None,
        "dias_promedio": round(float(df["dias"].mean()), 2),
        "ganancia_neta_total_u": round(float(df["ganancia"].sum()), 2),
        "roi_pct": round(float(df["ganancia"].sum() / (n_tot * stake)) * 100, 2),
        "max_drawdown_u": round(max_dd, 2)
    }


def ejecutar_backtest():
    cache_dir = Path(".local/fd_cache")
    nba_path = em.NBA
    tenis_dir = em.TENIS
    
    print("Cargando datasets históricos (fútbol, NBA, tenis)...")
    c = em.candidatos(cache_dir, nba_path, tenis_dir)
    print(f"Total candidatos cargados: {len(c)}")
    print(c["deporte"].value_counts().to_dict())
    
    # Ventana multideporte completa
    desde, hasta = "2023-10-24", "2025-05-25"
    deportes = ("futbol", "nba", "tenis")
    
    resultados = []
    for t in TARGETS:
        res = simular_target(c, deportes, desde, hasta, target=t)
        resultados.append(res)
        print(f"Target {t}: Completados={res.get('completados_pct')}% | Fallidos={res.get('fallidos_pct')}% | Freeroll={res.get('freerolls_asegurados_pct')}% | ROI={res.get('roi_pct')}% | Escalones prom={res.get('escalones_promedio_completados')}")
        
    out_path = Path(".local/escalera_targets_backtest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    ejecutar_backtest()
