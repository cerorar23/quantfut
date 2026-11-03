"""Invariantes temporales que faltaban en la auditoría del 3-nov-2026."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from qf.eval.temporal import medias_previas
from qf.eval.rediseno import historia_disponible, mercado_1x2
from qf.model.conteos import RegresionNB
from qf.model.fit_checks import AjusteNoConvergente
from qf.model.score_driven import ScoreDriven, INICIO
from qf.publish import destacado_web as dw
from qf.api import partido_mercados as pm

T = datetime(2026,11,3,18,tzinfo=timezone.utc)


def test_los_resultados_simultaneos_o_no_recibidos_no_entran_en_la_media():
    dates=pd.to_datetime(['2026-01-01','2026-01-08','2026-01-08','2026-01-15'],utc=True)
    vals=pd.Series([5.,50.,100.,8.]); grupos=pd.Series(['x']*4)
    m,n=medias_previas(vals,grupos,dates,dates+pd.Timedelta(hours=3))
    assert np.isnan(m.iloc[0]) and m.iloc[1:3].tolist()==[5.,5.]
    assert n.tolist()==[0,1,1,3]
    vals.iloc[1]=500
    otro,_=medias_previas(vals,grupos,dates,dates+pd.Timedelta(hours=3))
    assert otro.iloc[2]==m.iloc[2]  # la fila previa en orden no es un resultado ya disponible


def test_ewm_es_invariante_al_orden_de_capturas_simultaneas():
    dates=pd.to_datetime(['2026-01-01','2026-01-01','2026-01-08'],utc=True)
    a,_=medias_previas(pd.Series([2.,8.,1.]),pd.Series(['x']*3),dates,dates,8.)
    b,_=medias_previas(pd.Series([8.,2.,1.]),pd.Series(['x']*3),dates,dates,8.)
    assert a.iloc[2] == b.iloc[2] and a.iloc[2] == pytest.approx(5.)


def _historia():
    return pd.DataFrame({'kickoff_utc':pd.to_datetime(['2022-01-01','2023-01-01','2023-09-01'],utc=True),
        'home_team':['A']*3,'away_team':['B']*3,'league_id':['x']*3,'home_goals':[1]*3,'away_goals':[1]*3,
        'home_xg':[8.]*3,'away_xg':[8.]*3,'xg_source':['fotmob']*3,
        'xg_recorded_at':pd.to_datetime(['2026-01-01']*3,utc=True)})


def test_a0_y_dc_reciben_el_mismo_xg_admisible():
    h=_historia(); corte=pd.Timestamp('2024-07-01',tz='UTC')
    visible=historia_disponible(h,corte)
    assert visible.home_xg.isna().all() and visible.away_xg.isna().all()
    m=ScoreDriven(corte,w_xg=.65); m._as_of=corte
    hx,ax=m._observado(h)
    assert np.array_equal(hx,h.home_goals) and np.array_equal(ax,h.away_goals)
    assert h.home_xg.eq(8).all()  # el original no cambia


def test_xg_derivado_sin_recepcion_no_se_disfraza_de_xg_disponible():
    h=_historia(); h['home_npxg_o_xg']=9.; h['away_npxg_o_xg']=9.
    h['xg_recorded_at']=pd.Timestamp('2023-02-01',tz='UTC')
    m=ScoreDriven('2024-07-01',w_xg=1.,columna_xg='npxg_o_xg')
    hx,_=m._observado(h)
    assert (hx==8.).all()


def test_a0_espera_el_fin_real_de_estimacion_y_rechaza_historia_futura(monkeypatch):
    h=_historia(); fin=pd.Timestamp('2024-07-01',tz='UTC'); calls=[]
    def ajustar(fun,init,args,**kw):
        calls.append(len(args[0]))
        return SimpleNamespace(x=INICIO.copy(),success=True,fun=10.,message='ok',nit=1)
    monkeypatch.setattr('qf.model.score_driven.minimize',ajustar)
    m=ScoreDriven(fin)
    m.ajustar(h.iloc[:2],pd.Timestamp('2023-07-01',tz='UTC'))
    assert calls==[] and m.estimado_hasta is None
    m.ajustar(h,fin)
    assert calls==[3] and m.estimado_hasta==fin
    with pytest.raises(ValueError,match='posteriores'):
        m.ajustar(h,pd.Timestamp('2023-01-01',tz='UTC'))


@pytest.mark.parametrize('success,x,fun',[(False,[0.,0.,2.],1.),(True,[np.nan,0.,2.],1.),(True,[0.,0.,2.],np.inf)])
def test_nb_rechaza_fallos_y_coeficientes_no_finitos(monkeypatch,success,x,fun):
    monkeypatch.setattr('qf.model.conteos.minimize',lambda *a,**kw: SimpleNamespace(
        success=success,x=np.array(x),fun=fun,message='failed',nit=0))
    m=RegresionNB()
    with pytest.raises(AjusteNoConvergente): m.fit(np.ones((3,1)),[1,2,3])
    assert m.beta is None


def test_gradiente_nb_coincide_con_derivadas_numericas_independientes():
    from scipy.optimize._numdiff import approx_derivative
    m=RegresionNB()
    X,Z=m._partes(np.array([[0.],[1.],[-1.],[2.]]),np.array([[1.],[0.],[-1.],[2.]]))
    y=np.array([0.,3.,2.,7.]); theta=np.array([1.,.2,2.,-.3])
    _,grad=m._objetivo(theta,X,Z,y)
    numerico=approx_derivative(lambda t:m._nll(t,X,Z,y),theta).ravel()
    assert grad==pytest.approx(numerico,abs=1e-6)


def test_el_prior_que_entrena_la_calibracion_de_props_no_conoce_su_futuro():
    from qf.eval.rediseno_jugadores import previos,STATS
    j=pd.DataFrame({'jugador_id':[1,2,1,2,1], 'kickoff_utc':pd.date_range('2025-01-01',periods=5,tz='UTC'),
                    'minutos':[90.]*5,'titular':[True]*5,'posicion':['F']*5,
                    **{k:[1.,2.,1.,2.,1.] for k in STATS}})
    a=previos(j,'2026-01-01')
    j.loc[4,STATS]=999.
    b=previos(j,'2026-01-01')
    np.testing.assert_allclose(a.loc[:3,'r_gol'],b.loc[:3,'r_gol'],equal_nan=True)


def _cuotas(duplicar=False,desfase=0):
    q=pd.DataFrame({'match_id':['m']*3,'source':['propline']*3,'bookmaker':['pinnacle']*3,
        'market':['h2h']*3,'selection':['home','draw','away'],'price':[2.,3.,4.],
        'captured_at':[T,T,T+timedelta(minutes=desfase)],'mins_to_kickoff':[60.]*3})
    return pd.concat([q,q.iloc[:1].assign(price=4.)],ignore_index=True) if duplicar else q


def test_el_mercado_nunca_promedia_contratos_duplicados_y_exige_ternas_coherentes():
    assert mercado_1x2(_cuotas(True)).empty
    assert mercado_1x2(_cuotas(desfase=16)).empty
    assert mercado_1x2(_cuotas()).odd_home.iloc[0]==2.
    assert mercado_1x2(_cuotas().drop(columns='captured_at')).empty


def _snapshot():
    return {'version':1,'decidido_en':(T-timedelta(hours=1)).isoformat(),'kickoff_utc':T.isoformat(),
        'fila':pm._fila('GOLES','Goles totales','totals','over',1.5,'Más de 1,5 goles',.7)}


def test_destacado_leido_exige_sello_y_recepcion_previa():
    visto={}
    def consulta(sql,args): visto['sql']=sql; return {'snapshot':_snapshot()}
    assert dw.obtener('m',consulta=consulta)['fila']['prob']==.7
    assert 'prediction_batches' in visto['sql'] and 'p.generated_at < m.kickoff_utc' in visto['sql']
    s=_snapshot(); s['decidido_en']=T.isoformat()
    assert dw.obtener('m',consulta=lambda *a:{'snapshot':s}) is None


def test_congelar_no_cambia_un_destacado_ya_registrado_ni_lo_crea_despues_del_inicio(monkeypatch):
    s=_snapshot()
    monkeypatch.setattr(dw,'obtener',lambda *a,**kw:s)
    p={'match_id':'m','kickoff_utc':T}
    assert dw.congelar(p,(4.,.2,0.),T-timedelta(minutes=5))==s
    assert dw.congelar(p,(4.,.2,0.),T) is None


def test_api_corta_el_estado_de_un_partido_pasado_a_su_inicio(monkeypatch):
    visto=[]
    monkeypatch.setattr(pm,'query_one',lambda *a:{'league_id':'x','kickoff_utc':T-timedelta(days=1),
        'home_team_id':1,'away_team_id':2,'referee':None})
    class Acc:
        def lambdas(self,*a): return (5.,4.)
    monkeypatch.setattr(pm,'_acumulador',lambda liga,mk,corte:visto.append(corte) or Acc())
    assert pm.lambdas_estadisticas('m')==((5.,4.),(5.,4.))
    assert visto==[T-timedelta(days=1)]*2


def test_historial_no_inventa_un_destacado_sin_registro_previo(monkeypatch):
    monkeypatch.setattr(pm,'lambdas_goles',lambda *a:(1.8,.8,0.))
    monkeypatch.setattr(pm,'lambdas_estadisticas',lambda *a:(None,None))
    monkeypatch.setattr(pm,'cuotas_casas',lambda *a:{})
    monkeypatch.setattr(pm,'query_one',lambda *a:None)
    monkeypatch.setattr(pm,'datos_partido',lambda *a:{'status':'finished','home_goals':2,'away_goals':0})
    assert pm.construir('m','A','B',{},False,web=True)['destacado'] is None


def test_historial_y_fila_conservan_el_porcentaje_congelado(monkeypatch):
    monkeypatch.setattr(pm,'lambdas_goles',lambda *a:(3.,1.,0.))
    monkeypatch.setattr(pm,'lambdas_estadisticas',lambda *a:((8.,1.),(4.,1.)))
    monkeypatch.setattr(pm,'cuotas_casas',lambda *a:{})
    monkeypatch.setattr(pm,'query_one',lambda *a:{'snapshot':_snapshot()})
    monkeypatch.setattr(pm,'datos_partido',lambda *a:{'status':'finished','home_goals':2,'away_goals':0})
    out=pm.construir('m','A','B',{},False,web=True)
    assert out['destacado']['prob']==.7 and out['destacado']['resultado']=='win'
    fila=next(f for f in out['filas'] if f['id']==out['destacado']['id'])
    assert fila['prob']==.7


def test_el_payload_del_sello_incluye_snapshot_y_conserva_los_lotes_anteriores(monkeypatch):
    from qf.publish import hashchain as hc
    monkeypatch.setattr(hc,'query',lambda sql,*a:[{'match_id':'m','web_destacado':_snapshot()}] if 'FROM predictions p' in sql else [])
    assert hc._collect_partido('m')['predictions'][0]['web_destacado']==_snapshot()
    monkeypatch.setattr(hc,'query',lambda sql,*a:[{'match_id':'m','web_destacado':None}] if 'FROM predictions p' in sql else [])
    assert 'web_destacado' not in hc._collect_partido('m')['predictions'][0]
