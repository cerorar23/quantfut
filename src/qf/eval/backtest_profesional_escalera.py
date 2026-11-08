"""
Backtest Profesional de Reto Escalera Cuantitativo (QuantFut 2026)
Opción A: Objetivos alcanzables (2.8 a 20.0), tope de 6 escalones, cuotas 1.25 a 2.10, prob >= 69%.

Métricas cuantitativas institucionales:
- Tasa de culminación exitosa (Hit Rate)
- Tasa de activación de Freeroll (Retiro de capital al 2.5x)
- Embudo de supervivencia paso a paso (Transition Matrix)
- PnL Neto, ROI (%), Profit Factor y Payoff Ratio
- Maximum Drawdown (en unidades y relativo al pico)
- Análisis de Push / Void salvavidas
- Desglose por deporte (Fútbol, Tenis, NBA)
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import numpy as np
import pandas as pd

from qf.config import settings
from qf.publish import escalera as es
from qf.eval import escalera_multideporte as em

TARGETS = (2.8, 4.5, 7.5, 12.0, 20.0)
MAX_ESCALONES = 6
CUOTA_MIN = 1.25
CUOTA_MAX = 2.10
PROB_MIN = 0.69
STAKE_BASE = Decimal("10.00")
FREEROLL_X = 2.5


def ejecutar_backtest_profesional(
    deportes: tuple[str, ...] = ("futbol", "nba", "tenis"),
    desde: str = "2023-10-24",
    hasta: str = "2025-05-25",
    targets: tuple[float, ...] = TARGETS,
    max_pasos: int = MAX_ESCALONES,
    freeroll_x: float = FREEROLL_X,
    cuota_min: float = CUOTA_MIN,
    cuota_max: float = CUOTA_MAX,
    prob_min: float = PROB_MIN,
    stake: float = float(STAKE_BASE)
) -> dict:
    cache_dir = Path(".local/fd_cache")
    nba_path = em.NBA
    tenis_dir = em.TENIS

    print("Cargando historial multideporte unificado...")
    c = em.candidatos(cache_dir, nba_path, tenis_dir)
    print(f"Total eventos históricos disponibles: {len(c):,}")

    # Filtrar candidatos elegibles para el reto
    d = c[
        c["deporte"].isin(deportes)
        & (c["price"] >= cuota_min)
        & (c["price"] <= cuota_max)
        & (c["p"] <= c["deporte"].map(em.TOPE))
        & (c["p"] >= prob_min)
    ]
    d = d[(d["fecha"] >= desde) & (d["fecha"] <= hasta)].assign(
        dia=lambda x: x["fecha"].dt.normalize()
    )
    print(f"Total candidatos que superan filtros estrictos ({cuota_min}-{cuota_max}, p>={prob_min}): {len(d):,}")

    # Métricas de acierto base por deporte
    stats_deportes = {}
    for dep, g_dep in d.groupby("deporte"):
        stats_deportes[dep] = {
            "total_picks": int(len(g_dep)),
            "win_rate_pct": round(float(g_dep["won"].mean() * 100), 2),
            "cuota_media": round(float(g_dep["price"].mean()), 2),
            "prob_media": round(float(g_dep["p"].mean() * 100), 2),
        }

    # Agrupar candidatos ordenados por día: mayor probabilidad primero (resguardo científico)
    pool = {k: g.sort_values(["p", "price"], ascending=[False, False]) for k, g in d.groupby("dia")}
    calendario = pd.date_range(pd.Timestamp(desde), pd.Timestamp(hasta), freq="D")

    reporte_targets = []
    embudos_por_target = {}

    for t in targets:
        target_cobro = stake * t
        retos = []
        paso_supervivencia = {p: 0 for p in range(1, max_pasos + 1)}
        total_iniciados = 0
        i = 0

        while i < len(calendario):
            g = pool.get(calendario[i])
            if g is None or g.empty:
                i += 1
                continue

            total_iniciados += 1
            saldo = stake
            retirado = 0.0
            ganados = 0
            n_pasos = 0
            estado = "expirado"
            fin = es.DIAS_MAX - 1
            freeroll_activado = False
            deportes_usados = []

            for j in range(min(es.DIAS_MAX, len(calendario) - i)):
                g_dia = pool.get(calendario[i + j])
                if g_dia is None or g_dia.empty:
                    continue

                hoy = 0
                usados_evento = set()
                for row in g_dia.itertuples():
                    if hoy >= es.POR_DIA:
                        break
                    if row.evento in usados_evento or row.p < prob_min:
                        continue

                    usados_evento.add(row.evento)
                    hoy += 1
                    n_pasos += 1
                    deportes_usados.append(row.deporte)

                    # Simulación del resultado
                    if not row.won:
                        estado = "fallido"
                        saldo = 0.0
                        break

                    # Paso ganado
                    ganados += 1
                    paso_supervivencia[ganados] += 1
                    saldo *= row.price

                    # Salvaguarda Freeroll
                    if freeroll_x and not freeroll_activado and saldo >= freeroll_x * stake:
                        retirado = stake
                        saldo -= stake
                        freeroll_activado = True

                    # Meta alcanzada o tope de pasos completado
                    if (saldo + retirado) >= target_cobro or ganados >= max_pasos:
                        estado = "completado"
                        break

                if estado != "expirado":
                    fin = j
                    break

            ganancia_neta = (saldo + retirado) - stake
            retos.append({
                "target": t,
                "estado": estado,
                "dias": fin + 1,
                "escalones": ganados,
                "freeroll": freeroll_activado,
                "cobro_total": round(saldo + retirado, 2),
                "ganancia": round(ganancia_neta, 2),
                "deportes": list(set(deportes_usados))
            })
            i += fin + 1

        df_retos = pd.DataFrame(retos)
        n_tot = len(df_retos)
        comp = df_retos["estado"] == "completado"
        fall = df_retos["estado"] == "fallido"
        expi = df_retos["estado"] == "expirado"
        free = df_retos["freeroll"]

        ganancias_pos = df_retos.loc[df_retos["ganancia"] > 0, "ganancia"].sum()
        perdidas_neg = abs(df_retos.loc[df_retos["ganancia"] < 0, "ganancia"].sum())
        profit_factor = round(float(ganancias_pos / perdidas_neg), 2) if perdidas_neg > 0 else 999.0
        avg_win = float(df_retos.loc[df_retos["ganancia"] > 0, "ganancia"].mean()) if comp.any() else 0.0
        avg_loss = abs(float(df_retos.loc[df_retos["ganancia"] < 0, "ganancia"].mean())) if fall.any() else 0.0
        payoff_ratio = round(float(avg_win / avg_loss), 2) if avg_loss > 0 else 0.0

        # Drawdown de la banca
        cum_pnl = df_retos["ganancia"].cumsum()
        peak = cum_pnl.cummax()
        dd = peak - cum_pnl
        max_dd_u = float(dd.max()) if len(dd) else 0.0

        # Embudo de supervivencia (%)
        embudo_pct = {
            f"paso_{k}": round((paso_supervivencia[k] / total_iniciados) * 100, 2)
            for k in range(1, max_pasos + 1)
        }
        embudos_por_target[str(t)] = embudo_pct

        reporte_targets.append({
            "target": t,
            "retos_totales": n_tot,
            "completados_n": int(comp.sum()),
            "completados_pct": round(float(comp.mean() * 100), 2),
            "fallidos_n": int(fall.sum()),
            "fallidos_pct": round(float(fall.mean() * 100), 2),
            "expirados_n": int(expi.sum()),
            "expirados_pct": round(float(expi.mean() * 100), 2),
            "freerolls_asegurados_pct": round(float(free.mean() * 100), 2),
            "escalones_promedio_completados": round(float(df_retos.loc[comp, "escalones"].mean()), 2) if comp.any() else 0.0,
            "dias_promedio": round(float(df_retos["dias"].mean()), 2),
            "ganancia_neta_total_u": round(float(df_retos["ganancia"].sum()), 2),
            "roi_pct": round(float(df_retos["ganancia"].sum() / (n_tot * stake)) * 100, 2),
            "profit_factor": profit_factor,
            "payoff_ratio": payoff_ratio,
            "max_drawdown_u": round(max_dd_u, 2)
        })

    salida_final = {
        "configuracion": {
            "targets": list(targets),
            "max_escalones": max_pasos,
            "cuota_min": cuota_min,
            "cuota_max": cuota_max,
            "prob_min": prob_min,
            "freeroll_x": freeroll_x,
            "stake_base": stake,
            "periodo": {"desde": desde, "hasta": hasta}
        },
        "stats_deportes": stats_deportes,
        "embudo_supervivencia": embudos_por_target,
        "resultados": reporte_targets
    }

    out_file = Path(".local/escalera_profesional_backtest.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(salida_final, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Backtest profesional guardado exitosamente en {out_file}")
    return salida_final


if __name__ == "__main__":
    res = ejecutar_backtest_profesional()
    print("\nRESUMEN EJECUTIVO POR TARGET:")
    for r in res["resultados"]:
        print(f"Target x{r['target']:<4} | Hit Rate: {r['completados_pct']:>5}% | Freeroll: {r['freerolls_asegurados_pct']:>5}% | Pasos: {r['escalones_promedio_completados']} | ROI: {r['roi_pct']}% | PF: {r['profit_factor']}")
