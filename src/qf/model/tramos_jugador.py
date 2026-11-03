"""Más-menos ridge por tramos con jugadores constantes; candidato de investigación.

Resolución de un minuto. Excluye partidos con cambios/rojas sin identidad, marcador incompleto
o goles simultáneos a un cambio: no adivina el orden de eventos. El once histórico reconstruido
no acredita su disponibilidad a T-60. Este módulo no activa modelos ni produce picks.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import lsqr


def segmentar(jugadores: pd.DataFrame, incidencias: pd.DataFrame, partidos: pd.DataFrame):
    salida, rechazados = [], []
    por_j={k:g for k,g in jugadores.groupby('match_id')}
    por_i={k:g for k,g in incidencias.groupby('match_id')}
    for p in partidos.itertuples():
        j,inc=por_j.get(p.match_id),por_i.get(p.match_id)
        if j is None or inc is None:
            rechazados.append({'match_id':p.match_id,'motivo':'sin_jugadores_o_incidencias'}); continue
        try:
            trozos=_partido(p,j,inc)
        except ValueError as exc:
            rechazados.append({'match_id':p.match_id,'motivo':str(exc)}); continue
        salida.extend(trozos)
    out=pd.DataFrame(salida)
    out.attrs['disponibilidad']='once_historico_reconstruido'
    return out,pd.DataFrame(rechazados)


def _partido(p,j,inc):
    titular=j.titular.astype(str).str.lower().isin(['true','t','1'])
    activos={s:set(j.loc[titular & j.side.eq(s),'jugador_id'].astype(int)) for s in ('home','away')}
    if any(len(x)!=11 or 0 in x for x in activos.values()) or activos['home'] & activos['away']:
        raise ValueError('once_incompleto_o_duplicado')
    inc=inc[inc.minuto.between(0,90)].copy()
    inc['anulada']=inc.anulada.astype(str).str.lower().isin(['true','t','1'])
    added=inc.anadido.fillna(0).clip(lower=0)
    a1=float(added[inc.minuto.eq(45)].max()) if inc.minuto.eq(45).any() else 0.
    a2=float(added[inc.minuto.eq(90)].max()) if inc.minuto.eq(90).any() else 0.
    inc['t']=inc.minuto+added+np.where(inc.minuto.gt(45),a1,0.)
    inc=inc.sort_values('t')
    gol=inc.subtipo.eq('goal') & ~inc.anulada
    cambia=inc.subtipo.eq('substitution') | (inc.subtipo.eq('card') & inc.clase.isin(['red','yellowRed']))
    if set(inc.loc[gol,'t']) & set(inc.loc[cambia,'t']):
        raise ValueError('gol_y_cambio_sin_orden_acreditado')
    total={'home':0,'away':0}; tramo={'home':0,'away':0}; inicio=0.; out=[]
    def emitir(fin):
        nonlocal inicio,tramo
        if fin>inicio:
            out.append({'match_id':p.match_id,'league_id':p.league_id,'kickoff_utc':p.kickoff_utc,
                'inicio':inicio,'fin':fin,'duracion':fin-inicio,'local':tuple(sorted(activos['home'])),
                'visita':tuple(sorted(activos['away'])),'home_goals':tramo['home'],'away_goals':tramo['away']})
        inicio=fin; tramo={'home':0,'away':0}
    for r in inc.itertuples():
        if r.subtipo=='goal' and not (pd.notna(r.anulada) and bool(r.anulada)):
            if pd.isna(r.marcador_local) or pd.isna(r.marcador_visita):
                raise ValueError('gol_sin_marcador')
            nuevo={'home':int(r.marcador_local),'away':int(r.marcador_visita)}
            delta={s:nuevo[s]-total[s] for s in total}
            if sum(delta.values())!=1 or min(delta.values())<0:
                raise ValueError('marcador_no_monotono')
            for s in total: tramo[s]+=delta[s]
            total=nuevo
        elif r.subtipo=='substitution' or (r.subtipo=='card' and r.clase in ('red','yellowRed')):
            if r.side not in activos or pd.isna(r.jugador_id) or int(r.jugador_id)==0:
                raise ValueError('evento_sin_identidad')
            pid=int(r.jugador_id)
            if r.subtipo=='substitution':
                if pd.isna(r.jugador2_id) or int(r.jugador2_id)==0 or pid not in activos[r.side] or int(r.jugador2_id) in set.union(*activos.values()):
                    raise ValueError('cambio_incompatible_con_once')
                emitir(float(r.t))
                activos[r.side].remove(pid); activos[r.side].add(int(r.jugador2_id))
            elif pid in activos[r.side]:
                emitir(float(r.t)); activos[r.side].remove(pid)
    emitir(90.+a1+a2)
    if total!={'home':int(p.home_goals),'away':int(p.away_goals)}:
        raise ValueError('goles_incompletos')
    return out


class PlusMinusTramos:
    def __init__(self,ridge: float=10.,vida_dias: float=270.):
        if ridge<=0 or vida_dias<=0: raise ValueError('Regularización y vida media positivas')
        self.ridge,self.vida_dias=ridge,vida_dias
        self.coef: dict[int,float]={}

    def fit(self,tramos: pd.DataFrame,corte):
        t=tramos[tramos.kickoff_utc<pd.Timestamp(corte)].copy()
        if t.empty or (t.duracion<=0).any(): raise ValueError('Sin tramos anteriores válidos')
        ids=sorted({i for players in pd.concat([t.local,t.visita]) for i in players})
        index={p:i for i,p in enumerate(ids)}; rr=[]; cc=[]; vv=[]
        for n,r in enumerate(t.itertuples()):
            for players,signo in ((r.local,1.),(r.visita,-1.)):
                for pid in players: rr.append(n); cc.append(index[pid]); vv.append(signo)
        X=csr_matrix((vv,(rr,cc)),shape=(len(t),len(ids)))
        expos=t.duracion.to_numpy(float)/90.
        y=(t.home_goals-t.away_goals).to_numpy(float)/expos
        edad=(pd.Timestamp(corte)-t.kickoff_utc).dt.total_seconds().to_numpy()/86400.
        w=np.sqrt(expos*2**(-edad/self.vida_dias))
        # Nivel de la competición separado de la contribución regularizada de los jugadores.
        base=t.assign(expos=expos,dif=t.home_goals-t.away_goals).groupby('league_id').agg({'dif':'sum','expos':'sum'})
        nivel=t.league_id.map(base['dif']/base['expos']).to_numpy(float)
        result=lsqr(X.multiply(w[:,None]),(y-nivel)*w,damp=np.sqrt(self.ridge),atol=1e-9,btol=1e-9)
        if result[1] not in (0,1,2,4,5) or not np.isfinite(result[0]).all():
            raise ValueError('Ridge por tramos no convergió')
        self.coef=dict(zip(ids,map(float,result[0])))
        return self

    def diferencia(self,local,visita):
        return sum(self.coef.get(i,0.) for i in local)-sum(self.coef.get(i,0.) for i in visita)
