import pandas as pd
import pytest
from qf.model.tramos_jugador import segmentar,PlusMinusTramos


def datos():
    t=pd.Timestamp('2025-01-01',tz='UTC')
    p=pd.DataFrame([dict(match_id='m',league_id='x',kickoff_utc=t,home_goals=2,away_goals=1)])
    j=pd.DataFrame([dict(match_id='m',side=s,jugador_id=i,titular=True) for s,r in [('home',range(1,12)),('away',range(21,32))] for i in r] +
                   [dict(match_id='m',side='home',jugador_id=12,titular=False)])
    events=[('goal',20,'home',1,None,1,0),('substitution',60,'home',1,12,None,None),
            ('goal',70,'home',12,None,2,0),('card',75,'away',21,None,None,None),('goal',80,'away',22,None,2,1)]
    inc=pd.DataFrame([dict(match_id='m',subtipo=k,minuto=m,anadido=0,side=s,jugador_id=a,jugador2_id=b,
        marcador_local=h,marcador_visita=v,clase='red' if k=='card' else None,anulada=False) for k,m,s,a,b,h,v in events])
    return j,inc,p


def test_cambios_y_rojas_delimitan_tramos_con_exposicion_y_goles_correctos():
    j,i,p=datos(); s,bad=segmentar(j,i,p)
    assert bad.empty and s.duracion.tolist()==[60.,15.,15.]
    assert s.home_goals.tolist()==[1,1,0] and s.away_goals.tolist()==[0,0,1]
    assert 1 in s.local.iloc[0] and 1 not in s.local.iloc[1] and 12 in s.local.iloc[1]
    assert len(s.visita.iloc[-1])==10
    m=PlusMinusTramos().fit(s,p.kickoff_utc.iloc[0]+pd.Timedelta(days=1))
    assert all(pd.notna(c) for c in m.coef.values())
    with pytest.raises(ValueError,match='anteriores'): m.fit(s,p.kickoff_utc.iloc[0])


def test_eventos_ambiguos_o_once_incompleto_se_apartan_sin_adivinar():
    j,i,p=datos(); i.loc[i.subtipo.eq('goal') & i.minuto.eq(70),'minuto']=60
    s,bad=segmentar(j,i,p)
    assert s.empty and 'orden' in bad.motivo.iloc[0]
    j,i,p=datos(); s,bad=segmentar(j[j.jugador_id.ne(1)],i,p)
    assert s.empty and bad.motivo.iloc[0]=='once_incompleto_o_duplicado'
