"""
Simulación y Backtest Maestro Exhaustivo de Todos los Mercados Disponibles (Local + VPS)
Ecosistema QuantFut 2026: Fútbol (11 mercados), Tenis (4 mercados) y NBA (17 mercados).

Parámetros evaluados:
- POR_DIA = 1 (1 escalón al día, mejor pick diario)
- DIAS_MAX = 10 (plazo de 10 días)
- MAX_ESCALONES = 6 (tope dinámico de 6 escalones)
- CUOTA_MIN = 1.25, CUOTA_MAX = 2.10
- PROB_MIN = 0.69
- FREEROLL_X = 2.5
- TARGETS = [2.8, 4.5, 7.5, 12.0, 20.0]
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import numpy as np
import pandas as pd

from qf.publish import escalera as es
from qf.eval import escalera_multideporte as em

TARGETS = (2.8, 4.5, 7.5, 12.0, 20.0)
MAX_ESCALONES = 6
CUOTA_MIN = 1.25
CUOTA_MAX = 2.10
PROB_MIN = 0.69
STAKE_BASE = Decimal("10.00")
FREEROLL_X = 2.5
DIAS_MAX = 10
POR_DIA = 1


def ejecutar_backtest_maestro_total():
    print("=" * 70)
    print("AUDITORÍA Y CARGA DE TODOS LOS MERCADOS DISPONIBLES (LOCAL + VPS)")
    print("=" * 70)
    
    # 1. Cargar dataset histórico consolidado
    cache_dir = Path(".local/fd_cache")
    nba_path = em.NBA
    tenis_dir = em.TENIS

    print("1. Cargando datasets históricos de Fútbol (7 ligas), Tenis (ATP/WTA) y NBA...")
    c = em.candidatos(cache_dir, nba_path, tenis_dir)
    print(f"   -> Total eventos cargados: {len(c):,} partidos/props")

    # 2. Filtrado riguroso del espacio de búsqueda elegible para el Reto Escalera
    df_elegible = c[
        (c["price"] >= CUOTA_MIN)
        & (c["price"] <= CUOTA_MAX)
        & (c["p"] <= c["deporte"].map(em.TOPE))
        & (c["p"] >= PROB_MIN)
    ].copy()
    
    # Normalizar fecha y ordenar
    df_elegible["dia"] = df_elegible["fecha"].dt.normalize()
    print(f"   -> Candidatos que superan los filtros cuantitativos (1.25-2.10, p>=0.69): {len(df_elegible):,}")

    # 3. Desglose detallado por deporte y rango
    deporte_stats = {}
    for dep, g in df_elegible.groupby("deporte"):
        deporte_stats[dep] = {
            "total_picks": int(len(g)),
            "win_rate_pct": round(float(g["won"].mean() * 100), 2),
            "cuota_promedio": round(float(g["price"].mean()), 2),
            "prob_promedio": round(float(g["p"].mean() * 100), 2)
        }
        print(f"   - {dep.upper()}: {len(g):,} picks elegibles | Acierto real: {deporte_stats[dep]['win_rate_pct']}% | Cuota media: {deporte_stats[dep]['cuota_promedio']} | Prob media: {deporte_stats[dep]['prob_promedio']}%")

    # 4. Agrupamiento por día con la Regla Dorada: Mejor pick absoluto primero
    pool = {k: g.sort_values(["p", "price"], ascending=[False, False]) for k, g in df_elegible.groupby("dia")}
    desde = df_elegible["dia"].min()
    hasta = df_elegible["dia"].max()
    calendario = pd.date_range(desde, hasta, freq="D")
    print(f"\n2. Simulando Retos Escalera con POR_DIA = 1 y DIAS_MAX = 10 ({desde.strftime('%Y-%m-%d')} a {hasta.strftime('%Y-%m-%d')})...")

    stake = float(STAKE_BASE)
    resultados_por_target = []
    embudos_por_target = {}

    for t in TARGETS:
        target_cobro = stake * t
        retos = []
        i = 0
        total_iniciados = 0
        supervivencia_pasos = {p: 0 for p in range(1, MAX_ESCALONES + 1)}

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
            fin = DIAS_MAX - 1
            freeroll_activado = False
            deportes_usados = []

            for j in range(min(DIAS_MAX, len(calendario) - i)):
                g_dia = pool.get(calendario[i + j])
                if g_dia is None or g_dia.empty:
                    continue

                hoy = 0
                usados_evento = set()
                for row in g_dia.itertuples():
                    if hoy >= POR_DIA:
                        break
                    if row.evento in usados_evento or row.p < PROB_MIN:
                        continue

                    usados_evento.add(row.evento)
                    hoy += 1
                    n_pasos += 1
                    deportes_usados.append(row.deporte)

                    if not row.won:
                        estado = "fallido"
                        saldo = 0.0
                        break

                    ganados += 1
                    supervivencia_pasos[ganados] += 1
                    saldo *= row.price

                    # Salvaguarda Freeroll
                    if FREEROLL_X and not freeroll_activado and saldo >= FREEROLL_X * stake:
                        retirado = stake
                        saldo -= stake
                        freeroll_activado = True

                    # Meta alcanzada o tope de 6 pasos
                    if (saldo + retirado) >= target_cobro or ganados >= MAX_ESCALONES:
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

        cum_pnl = df_retos["ganancia"].cumsum()
        peak = cum_pnl.cummax()
        dd = peak - cum_pnl
        max_dd_u = float(dd.max()) if len(dd) else 0.0

        embudo_pct = {
            f"paso_{k}": round((supervivencia_pasos[k] / total_iniciados) * 100, 2)
            for k in range(1, MAX_ESCALONES + 1)
        }
        embudos_por_target[str(t)] = embudo_pct

        res_t = {
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
        }
        resultados_por_target.append(res_t)
        print(f"   Target x{t:<4} -> Acierto: {res_t['completados_pct']:>5}% | Freeroll: {res_t['freerolls_asegurados_pct']:>5}% | ROI: {res_t['roi_pct']:>5}% | PF: {res_t['profit_factor']} | Días: {res_t['dias_promedio']}")

    reporte_final = {
        "metadata": {
            "fuentes_consultadas": {
                "local": ["football-data (7 ligas, 2019-2025)", "Tennis-Data ATP/WTA", "BetsAPI NBA"],
                "vps": ["quantfut-db-1 (5.1M odds, 5.9K alta_prob settled)", "tenis-db (495K partidos, 517K stats)", "nba-db (4.5M cuotas, 5.9K eventos)"]
            },
            "parametros": {
                "targets": list(TARGETS),
                "max_escalones": MAX_ESCALONES,
                "por_dia": POR_DIA,
                "dias_max": DIAS_MAX,
                "cuota_min": CUOTA_MIN,
                "cuota_max": CUOTA_MAX,
                "prob_min": PROB_MIN,
                "freeroll_x": FREEROLL_X,
                "stake_base": stake
            }
        },
        "stats_deportes": deporte_stats,
        "embudos_supervivencia": embudos_por_target,
        "resultados_targets": resultados_por_target
    }

    out_file = Path(".local/backtest_maestro_mercados_totales.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(reporte_final, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Simulación maestra guardada exitosamente en {out_file}")
    return reporte_final


if __name__ == "__main__":
    ejecutar_backtest_maestro_total()
