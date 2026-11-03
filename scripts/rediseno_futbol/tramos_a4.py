"""Construcción y comprobación del candidato A4 por tramos; once histórico reconstruido, sin promoción."""
import argparse
import json
from pathlib import Path
import pandas as pd
from qf.model.tramos_jugador import segmentar,PlusMinusTramos

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--datos',required=True); ap.add_argument('--salida',required=True)
    a=ap.parse_args(); src,dst=Path(a.datos),Path(a.salida); dst.mkdir(parents=True,exist_ok=False)
    j=pd.read_csv(src/'jugadores.csv.gz',low_memory=False)
    i=pd.read_csv(src/'incidencias.csv.gz',low_memory=False)
    p=pd.read_csv(src/'partidos.csv.gz',parse_dates=['kickoff_utc'],low_memory=False)
    s,rech=segmentar(j,i,p)
    rech.to_csv(dst/'rechazados.csv.gz',index=False)
    if not s.empty: s.to_csv(dst/'tramos.csv.gz',index=False)
    res={'promocion':False,'disponibilidad':'once_historico_reconstruido','partidos':int(s.match_id.nunique()) if not s.empty else 0,
         'tramos':len(s),'rechazados':len(rech),'motivos':rech.motivo.value_counts().to_dict() if not rech.empty else {},
         'limites':['sin tracking ni posesiones','no incluye prior de edad','no acredita once a T-60','sin nueva reserva prospectiva']}
    if not s.empty:
        corte=s.kickoff_utc.max()+pd.Timedelta(days=1)
        modelo=PlusMinusTramos().fit(s,corte)
        res.update(jugadores_ajustados=len(modelo.coef),corte=str(corte))
        (dst/'ratings.json').write_text(json.dumps(modelo.coef,indent=2),encoding='utf-8')
    (dst/'estado.json').write_text(json.dumps(res,indent=2),encoding='utf-8')
    print(json.dumps(res,indent=2),flush=True)

if __name__=='__main__': main()
