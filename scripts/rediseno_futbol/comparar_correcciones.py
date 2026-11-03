"""Comparación nueva, conservando datos y resultados originales. Nunca promueve un artefacto."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from qf.eval import rediseno as R
from qf.eval import rediseno_conteos as C
from qf.model.referencias import DixonColesRef
from qf.model.score_driven import ScoreDriven


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--datos',required=True)
    ap.add_argument('--salida',required=True)
    ap.add_argument('--familia',choices=['a','c'],required=True)
    ap.add_argument('--disponibilidad',choices=['recepcion','reconstruida'],default='recepcion')
    args=ap.parse_args()
    src,dst=Path(args.datos),Path(args.salida)
    dst.mkdir(parents=True,exist_ok=False)
    d=R.cargar(src); df=R.tabla_partidos(d)
    protocolo={'familia':args.familia,'disponibilidad':args.disponibilidad,'promocion':False,
        'periodo_2627_ya_observado':True,'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.glob('*.csv.gz')}}
    (dst/'protocolo.json').write_text(json.dumps(protocolo,indent=2),encoding='utf-8')
    sal={}
    if args.familia=='a':
        modelos={'dc_prod':DixonColesRef(disponibilidad=args.disponibilidad),
                 'a0_xg':ScoreDriven('2024-07-01',w_xg=.65,disponibilidad=args.disponibilidad)}
        pred=R.walk_forward(df,modelos,'2023-07-01',disponibilidad=args.disponibilidad)
        pred.to_csv(dst/'predicciones.csv.gz',index=False)
        (dst/'fallos.json').write_text(json.dumps(pred.attrs['fallos_ajuste'],indent=2),encoding='utf-8')
        for etiqueta,desde,hasta in [('seleccion','2024-07-01','2026-07-01'),('seguimiento_ya_observado','2026-07-01',None)]:
            res,comp=R.evaluar(pred,df,desde,hasta,referencia='dc_prod')
            sal[etiqueta]={'resumen':res.to_dict('records'),'comparacion':comp.to_dict('records')}
            print(etiqueta,res.to_string(index=False),flush=True)
    else:
        derbis=pd.read_csv(src/'derbis.csv.gz')
        for obj,variantes in [('corners',['c0_liga','c1_equipos','c2_yip']),
                              ('yellow',['c0_liga','t1_equipos','t2_arbitro','t3_dawson'])]:
            L=C.rasgos(df,d.contexto,derbis,d.equipo,obj,disponibilidad=args.disponibilidad)
            pred=C.walk_forward(L,obj,variantes,'2024-07-01')
            (dst/f'fallos_{obj}.json').write_text(json.dumps(pred.attrs.get('fallos_ajuste',[]),indent=2),encoding='utf-8')
            pred.to_csv(dst/f'pred_{obj}.csv.gz',index=False)
            for etiqueta,desde,hasta in [('seleccion','2024-07-01','2026-07-01'),('seguimiento_ya_observado','2026-07-01',None)]:
                res,comp=C.evaluar(pred,L,obj,desde,hasta)
                sal[f'{obj}_{etiqueta}']={'resumen':res.to_dict('records'),'comparacion':comp.to_dict('records')}
                print(obj,etiqueta,res.to_string(index=False),flush=True)
    (dst/'metricas.json').write_text(json.dumps(sal,indent=2,default=str),encoding='utf-8')


if __name__=='__main__': main()
