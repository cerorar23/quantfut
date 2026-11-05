"""Entrenamiento y evaluación LOCAL del híbrido de regulación; no usa minutos objetivo como entrada predictiva.

Receta fijada antes de la prueba: ridge 10 sin prior, vida 730 días, mezcla 1/2.
Coeficientes congelados por temporada; prueba 2025-26 sin seleccionar variantes con ella.
No acredita recepción histórica ni el efecto de partes de lesiones ausentes de esta exportación.
"""
from collections import defaultdict, deque
from datetime import date, datetime, UTC
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.special import expit

from entrenar_equipo import preparar, recorrer, ajustar_dispersion_ot
from nba.v2 import minutos, nucleo, plantilla, evaluacion
from nba.v2.plantilla import PartidoFila


def registrar(juegos, filas):
    por_pid={g['pid']:g for g in juegos}
    cajas=defaultdict(lambda:{'local':{},'visit':{}})
    for pid,j,tri,m,_,_ in filas:
        g=por_pid.get(pid)
        if g is None:continue
        lado='local' if tri==g['local'] else 'visit' if tri==g['visit'] else None
        if lado and 0 < m <= 60:
            cajas[pid][lado][j]=float(m)
    hist=defaultdict(lambda:deque(maxlen=30)); ultimo_eq={}; recientes=defaultdict(lambda:deque(maxlen=10))
    registros={}; entrenamiento=[]; dias=defaultdict(list); ultimo={}
    for g in juegos:dias[g['fecha']].append(g)
    for fecha in sorted(dias):
        for g in dias[fecha]:
            dia=date.fromisoformat(fecha).toordinal(); reg={}
            for lado in ('local','visit'):
                eq=g[lado]
                candidatos={j for grupo in recientes[eq] for j in grupo if ultimo_eq.get(j)==eq and len(hist[j])>=5}
                reg[lado]=[(j,minutos.punto(hist[j]),j in cajas[g['pid']][lado]) for j in sorted(candidatos)]
            descanso=float((dia-ultimo.get(g['visit'],-100)==1)-(dia-ultimo.get(g['local'],-100)==1))
            registros[g['pid']]=dict(candidatos=reg,descanso=descanso)
            caja=cajas[g['pid']]
            # Sin cajas de regulación por jugador en partidos OT: no se inventa su reparto.
            if not g['ot'] and all(238<=sum(caja[l].values())<=242 for l in ('local','visit')):
                entrenamiento.append(PartidoFila(dia,g['pl']-g['pv'],g['pl']+g['pv'],caja['local'],caja['visit'],descanso))
        for g in dias[fecha]:
            for lado in ('local','visit'):
                eq=g[lado]; ultimo[eq]=date.fromisoformat(fecha).toordinal()
                for j,m in cajas[g['pid']][lado].items():hist[j].append(m);ultimo_eq[j]=eq
                recientes[eq].append(set(cajas[g['pid']][lado]))
    return registros,entrenamiento


def tabla_rol(juegos, registros, corte):
    c=defaultdict(lambda:[0,0])
    for g in juegos:
        if g['fecha']>=corte:continue
        for lado in ('local','visit'):
            for _,mp,jugo in registros[g['pid']]['candidatos'][lado]:
                if mp is not None:
                    t=minutos.tramo(mp);c[t][0]+=int(jugo);c[t][1]+=1
    return {k:a/b for k,(a,b) in c.items() if b>=30}


def predecir(g, reg, imp, tabla):
    esperados={l:plantilla.minutos_esperados({j:(mp,tabla.get(minutos.tramo(mp),.84))
               for j,mp,_ in reg['candidatos'][l] if mp is not None}) for l in ('local','visit')}
    base=g['mu_l']-g['mu_v']
    usa=min(len(esperados[l]) for l in esperados)>=8
    margen=(base+imp.margen(esperados['local'],esperados['visit'],reg['descanso']))/2 if usa else base
    total=g['mu_l']+g['mu_v']
    return dict(g,mu_l=(total+margen)/2,mu_v=(total-margen)/2,usa_jugadores=usa)


def ejecutar(equipos_path, jugadores_path, artefacto_path, informe_path):
    if artefacto_path.exists() or informe_path.exists():raise ValueError('no se sobrescriben artefactos/evidencias')
    raw=equipos_path.read_bytes(); eq=json.loads(raw.decode('utf-8-sig'))
    with gzip.open(jugadores_path,'rt',encoding='utf8') as f:jug=json.load(f)
    corte=datetime.fromisoformat(jug['captured_at_utc'])
    if any(datetime.fromisoformat(r[-1])>corte for r in jug['rows']):raise ValueError('recepción futura')
    juegos,descartes=preparar(eq)
    regs,filas=registrar(juegos,jug['rows'])
    _,_,_,pred_base=recorrer(juegos)
    pred=[]
    for temporada in ('2023-24','2024-25','2025-26'):
        inicio=f'{temporada[:4]}-10-01'
        imp=plantilla.ajustar(filas,10.,10.,730.,dia_corte=date.fromisoformat(inicio).toordinal())
        tabla=tabla_rol(juegos,regs,inicio)
        for g in pred_base:
            if g['temporada']==temporada:pred.append(predecir(g,regs[g['pid']],imp,tabla))
    ajuste=[g for g in pred if g['temporada']<'2025-26']
    prueba=[g for g in pred if g['temporada']=='2025-26' and g['fecha']<='2026-04-30']
    dispersion=ajustar_dispersion_ot(ajuste)
    ref=float(np.mean([g['ritmo_proyectado'] for g in ajuste]))
    dispersion_base=ajustar_dispersion_ot([g for g in pred_base if '2023-10-01'<=g['fecha']<'2025-10-01'])
    referencia=float(np.mean([g['pl']>g['pv'] for g in ajuste]))
    p=[];pb=[];y=[];fechas=[];fallback=0
    por_pid={g['pid']:g for g in pred_base}
    for g in prueba:
        valores=[]
        for prediccion,d in ((g,dispersion),(por_pid[g['pid']],dispersion_base)):
            escala=np.sqrt(g['ritmo_proyectado']/ref)
            ot=float(expit(d['ot']['intercepto']+d['ot']['abs_margen']*abs(prediccion['mu_l']-prediccion['mu_v'])))
            m=nucleo.simular_con_ot(prediccion['mu_l'],prediccion['mu_v'],d['sigma_margen']*escala,
                d['sigma_total']*escala,g['ritmo_proyectado'],ot,n=20000,semilla=g['pid'])
            valores.append(float(np.mean(m.muestras[:,0]>m.muestras[:,1])))
        p.append(valores[0]);pb.append(valores[1]);y.append(float(g['pl']>g['pv']));fechas.append(g['fecha'])
        fallback+=int(not g['usa_jugadores'])
    metricas=evaluacion.informe_binario(p,y,pb,grupos=fechas)
    final=plantilla.ajustar(filas,10.,10.,730.)
    hashes={equipos_path.name:hashlib.sha256(raw).hexdigest(),jugadores_path.name:hashlib.sha256(jugadores_path.read_bytes()).hexdigest()}
    informe=dict(tipo='retrospectivo_temporal_hibrido_regulacion',calibracion_prospectiva_certificada=False,
        acredita_recepcion_historica=False,partes_lesiones_en_evaluacion=False,prueba='2025-26 hasta 30-abr-2026',
        ajuste_dispersion='2023-24 y 2024-25',hiperparametros_fijados_antes_prueba=True,
        ganador=metricas,referencia_constante=evaluacion.informe_binario(p,y,np.full(len(y),referencia),grupos=fechas),
        respaldos_equipo=fallback,hashes_entradas=hashes,partidos_entrenamiento_sin_ot=len(filas),descartes=descartes)
    artefacto=dict(formato=2,objetivo='margen_regulacion',datos_hasta=max(g['fecha'] for g in juegos),
        conocido_en_utc=max(datetime.now(UTC),datetime.fromisoformat(eq['captured_at_utc']),datetime.fromisoformat(jug['captured_at_utc'])).isoformat(),
        aprobado_para_mezcla=bool(len(p)>=500 and metricas['dif_ic95'][1]<=0),
        lam=10.,vida_media_dias=730.,a_priori={'tipo':'ninguno'},solo_partidos_sin_ot=True,
        beta=final.beta,tau=final.tau,c_margen=final.c_margen,d_margen=final.d_margen,c_total=final.c_total,d_total=final.d_total,
        sigma_margen_mezcla=dispersion['sigma_margen'],sigma_total_mezcla=dispersion['sigma_total'],
        posesiones_referencia=ref,ot=dispersion['ot'],hashes_entradas=hashes,
        validacion=informe,partidos_entrenamiento=len(filas),jugadores=len(final.beta))
    artefacto_path.write_text(json.dumps(artefacto,ensure_ascii=False,sort_keys=True,indent=2),encoding='utf8')
    informe_path.write_text(json.dumps(informe,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'n':len(p),'brier':metricas['brier'],'logloss':metricas['logloss'],
        'brier_equipo':metricas['base']['brier'],'ic95_vs_equipo':metricas['dif_ic95'],'jugadores':len(final.beta),
        'sigma_margen_regulacion':dispersion['sigma_margen'],'respaldos':fallback}))


if __name__=='__main__':ejecutar(*(Path(x) for x in sys.argv[1:]))
