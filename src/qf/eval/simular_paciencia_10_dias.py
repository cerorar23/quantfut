"""
Simulación Cuantitativa: ¿Ayuda la paciencia / selectividad en la ventana de 10 días?
Compara tomar picks todos los días (p >= 0.69) vs esperar a los días con favoritos de élite (p >= 0.74, 0.78, 0.82).
"""
import sys
from pathlib import Path
from decimal import Decimal
import pandas as pd
import numpy as np

from qf.publish import escalera as es
from qf.eval import escalera_multideporte as em

TARGETS = (2.8, 4.5)
MAX_PASOS = 6
STAKE = 10.0
FREEROLL_X = 2.5
DIAS_MAX = 10
POR_DIA = 1

def run():
    print("Cargando candidatos multideporte...")
    c = em.candidatos(Path(".local/fd_cache"), em.NBA, em.TENIS)
    
    # Filtrar cuotas permitidas
    c_base = c[(c["price"] >= 1.25) & (c["price"] <= 2.10)].copy()
    c_base["dia"] = c_base["fecha"].dt.normalize()
    
    print("\n" + "=" * 75)
    print("COMPARATIVA DE SELECTIVIDAD Y PACIENCIA EN LA VENTANA DE 10 DÍAS")
    print("=" * 75)
    
    thresholds = [0.69, 0.74, 0.78, 0.82]
    
    for pm in thresholds:
        # Filtrar solo candidatos con prob >= pm
        d = c_base[(c_base["p"] >= pm) & (c_base["p"] <= c_base["deporte"].map(em.TOPE))].copy()
        pool = {k: g.sort_values(["p", "price"], ascending=[False, False]) for k, g in d.groupby("dia")}
        
        desde = "2023-10-24"
        hasta = "2025-05-25"
        calendario = pd.date_range(pd.Timestamp(desde), pd.Timestamp(hasta), freq="D")
        
        print(f"\n--- UMBRAL PROB_MIN = {pm:.2f} ({len(d):,} picks disponibles en el histórico) ---")
        
        for t in TARGETS:
            target_cobro = STAKE * t
            retos = []
            i = 0
            
            while i < len(calendario):
                g = pool.get(calendario[i])
                if g is None or g.empty:
                    i += 1
                    continue
                    
                saldo = STAKE
                retirado = 0.0
                ganados = 0
                estado = "expirado"
                fin = DIAS_MAX - 1
                freeroll_activado = False
                dias_con_pick = 0
                
                for j in range(min(DIAS_MAX, len(calendario) - i)):
                    g_dia = pool.get(calendario[i + j])
                    if g_dia is None or g_dia.empty:
                        continue  # PACIENCIA: No hay pick élite hoy, se espera al siguiente día
                        
                    hoy = 0
                    usados = set()
                    for row in g_dia.itertuples():
                        if hoy >= POR_DIA:
                            break
                        if row.evento in usados or row.p < pm:
                            continue
                            
                        usados.add(row.evento)
                        hoy += 1
                        dias_con_pick += 1
                        
                        if not row.won:
                            estado = "fallido"
                            saldo = 0.0
                            break
                            
                        saldo *= row.price
                        ganados += 1
                        
                        if FREEROLL_X and not freeroll_activado and saldo >= FREEROLL_X * STAKE:
                            retirado = STAKE
                            saldo -= STAKE
                            freeroll_activado = True
                            
                        if (saldo + retirado) >= target_cobro or ganados >= MAX_PASOS:
                            estado = "completado"
                            break
                            
                    if estado != "expirado":
                        fin = j
                        break
                        
                ganancia = (saldo + retirado) - STAKE
                retos.append({
                    "estado": estado,
                    "dias": fin + 1,
                    "dias_con_pick": dias_con_pick,
                    "ganados": ganados,
                    "freeroll": freeroll_activado,
                    "ganancia": ganancia
                })
                i += fin + 1
                
            df = pd.DataFrame(retos)
            n_tot = len(df)
            comp = (df["estado"] == "completado").mean() * 100
            fall = (df["estado"] == "fallido").mean() * 100
            expi = (df["estado"] == "expirado").mean() * 100
            free = df["freeroll"].mean() * 100
            roi = (df["ganancia"].sum() / (n_tot * STAKE)) * 100
            dias_prom = df["dias"].mean()
            
            print(f"Target x{t:<3} | Completados: {comp:>5.2f}% | Freeroll: {free:>5.2f}% | Expirados: {expi:>4.2f}% | Días Promedio: {dias_prom:.2f} | ROI: {roi:>+6.2f}% (Total Retos: {n_tot})")

if __name__ == "__main__":
    run()
