"""Adaptador de tenis de `/deportes/v1`: datos fijos, mapeo y paridad con lo que construyen la web y la app.

Los mismos datos de entrada (la forma de `tenis_publico.public_data()`) pasan por:
  * `tennisEvents` de `frontend/sports-data.js` (se ejecuta de verdad con `node`; se omite si no hay node);
  * el adaptador de tenis del contrato.
y deben coincidir en `id`, `home`, `away`, `start` (mismo instante), y por mercado en `id`, `probability` y `outcome`.
De dónde sale cada campo del contrato:
  id/home/away/league/surface/score  <- evento del feed, tal cual (`league` nulo -> '', como la app: `'${event['league'] ?? ''}'`)
  start                              <- `start` (ISO) en UTC; `tennisEvents` solo lo exige parseable
  status                             <- `status` con ESTADOS (`no_result` -> `awaiting_result`; la app lo pasa tal cual)
  sealed_at / Mercado.sealed_at      <- `sealed_at` del evento (la fuente sella por partido)
  eligible                           <- `sealed_at < start` (igual que la app: `sealTime.isBefore(start)`)
  Mercado.id/label/selection/probability/price/reference/push_probability/outcome <- mercado del feed, tal cual
  Mercado.outcome                    <- el del feed solo si el mercado es elegible (la web/app lo pasan siempre; la fuente
                                        real nunca da sellos posteriores al inicio, así que no se observa diferencia)
  destacado                          <- `destacado.id` (lo elige `elegir_destacado` en `read_public_feed`)
La app (`tennisEvents` en `sports_feed.dart`) aplica el mismo filtrado y los mismos campos; no se ejecuta aquí (Dart).
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from qf.api import deportes_tenis as dt
from qf.api import tenis_publico
from qf.api.deportes_v1 import ADAPTADORES

RAIZ = Path(__file__).resolve().parents[1]
SELLO = 'a' * 64


def _m(id, label, selection, p, *, outcome=None, push=None, secreto='CENTINELA_MERCADO'):
    return {'id': id, 'label': label, 'selection': selection, 'probability': p, 'price': None,
            'reference': 'Probabilidad del motor', 'outcome': outcome, 'push_probability': push, 'secreto': secreto}


def _evento(id, inicio, estado, mercados, *, sellado, destacado=None, seal=SELLO, score=None):
    return {'id': id, 'sport': 'tenis', 'home': f'Local {id}', 'away': f'Visitante {id}', 'start': inicio,
            'league': 'ATP · Basilea', 'surface': 'Pista dura', 'sealed_at': sellado, 'seal': seal, 'status': estado,
            'score': score, 'actionable': False, 'markets': mercados, 'fit': 'CENTINELA_FIT',
            'destacado': next((m for m in mercados if m['id'] == destacado), None)}


def datos_fijos() -> dict:
    ganador = lambda id, p, **kw: _m(id, 'Ganador del partido', 'Local', p, **kw)   # noqa: E731
    return {'sport': 'tenis', 'state': 'ok', 'generated_at': '2026-11-12T05:00:00+00:00', 'problems': 0, 'events': [
        _evento('t-b', '2026-11-12T08:00:00Z', 'scheduled', [ganador('winner', 0.61), _m('games_total-1', 'Juegos totales', 'Más de 22.5', 0.55, push=0.0)],
                sellado='2026-11-12T06:00:00Z', destacado='winner'),
        _evento('t-a', '2026-11-12T08:00:00Z', 'scheduled', [ganador('winner', 0.58)], sellado='2026-11-12T06:00:00Z',
                destacado='winner'),
        _evento('t-n', '2026-11-12T10:00:00Z', 'no_result', [ganador('winner', 0.64)], sellado='2026-11-12T06:00:00Z'),
        # sellado tras el inicio: nada es elegible ni cuenta como acierto
        _evento('t-c', '2026-11-12T20:00:00+00:00', 'finished',
                [ganador('winner', 0.62, outcome='win'),
                 _m('games_total-1', 'Juegos totales', 'Más de 22.5', 0.57, outcome='win', push=0.04),
                 _m('tiebreak-2', 'Tie-break', 'Sí', 0.70, outcome='loss'),
                 _m('sets_total-3', 'Sets totales', 'Más de 2.5', 0.66),
                 _m('ace_total-4', 'Aces', 'Más de 9.5', 0.60)],
                sellado='2026-11-12T21:00:00Z', destacado='winner', score='6-4 3-6 7-5'),
        _evento('t-d', '2026-11-13T02:00:00Z', 'scheduled', [ganador('winner', 0.52)], sellado='2026-11-12T06:00:00Z'),
        _evento('t-z', '2026-11-30T12:00:00Z', 'cancelled', [ganador('winner', 0.51, outcome='push')], sellado='2026-11-12T06:00:00Z'),
    ]}


def fijar_fuente(mp, datos=None):
    datos = datos_fijos() if datos is None else datos
    mp.setattr(tenis_publico, 'public_data', lambda: copy.deepcopy(datos))
    return datos


def _utc(t):
    return datetime.fromisoformat(t.replace('Z', '+00:00')).astimezone(timezone.utc)


AMPLIA = (_utc('2026-11-01T00:00:00Z'), _utc('2026-12-31T00:00:00Z'))


@pytest.fixture
def adaptador(monkeypatch):
    fijar_fuente(monkeypatch)
    return dt.AdaptadorTenis()


def test_se_registra_como_tenis():
    assert isinstance(ADAPTADORES['tenis'], dt.AdaptadorTenis)


# ── paridad con tennisEvents (web) ───────────────────────────────────────────

@pytest.mark.skipif(shutil.which('node') is None, reason='sin node')
def test_paridad_con_tennisEvents_de_la_web(adaptador):
    js = ("import {tennisEvents} from './frontend/sports-data.js';"
          "const d=JSON.parse(process.argv[1]);console.log(JSON.stringify(tennisEvents(d)));")
    r = subprocess.run(['node', '--input-type=module', '-e', js, json.dumps(datos_fijos())], cwd=RAIZ,
                       capture_output=True, text=True, encoding='utf-8', check=True, timeout=60)
    web = json.loads(r.stdout)
    contrato = {e.id: e for e in (adaptador.partido(x['id']) for x in web)}
    assert set(contrato) == {e['id'] for e in datos_fijos()['events']}      # la web muestra los mismos partidos
    for w in web:
        c = contrato[w['id']]
        assert (c.home, c.away) == (w['home'], w['away'])
        assert c.start == _utc(w['start']) and c.league == w['league'] and c.surface == w['surface']
        assert c.score == w['score'] and c.seal == w['seal']
        assert [m.id for m in c.markets] == [m['id'] for m in w['markets']]
        for m, mw in zip(c.markets, w['markets']):
            assert m.probability == mw['probability']
            assert m.outcome == (mw['outcome'] if m.eligible else None)
            assert (m.label, m.selection, m.price, m.reference) == (mw['label'], mw['selection'], mw['price'], mw['reference'])
        assert c.destacado == (w['destacado']['id'] if w['destacado'] else None)


def test_la_cartelera_trae_los_mismos_eventos_que_la_ventana(adaptador):
    ev = adaptador.cartelera(_utc('2026-11-12T00:00:00Z'), _utc('2026-11-13T00:00:00Z'))
    assert sorted(e.id for e in ev) == ['t-a', 't-b', 't-c', 't-n']
    for e in ev:
        assert [m.id for m in e.markets] == ([e.destacado] if e.destacado else [])


# ── mapeo ────────────────────────────────────────────────────────────────────

def test_estados_y_elegibilidad(adaptador):
    assert adaptador.partido('t-n').status == 'awaiting_result'          # no_result no existe en el contrato
    assert adaptador.partido('t-z').status == 'cancelled'
    c = adaptador.partido('t-c')
    assert c.status == 'finished' and c.score == '6-4 3-6 7-5'
    assert all(not m.eligible and m.outcome is None for m in c.markets)  # sello posterior al inicio
    b = adaptador.partido('t-b')
    assert all(m.eligible for m in b.markets) and b.bloqueados == 0 and b.imagenes is None


def test_resultado_solo_si_es_elegible(monkeypatch):
    datos = datos_fijos()
    datos['events'][3]['sealed_at'] = '2026-11-12T19:00:00Z'             # t-c sellado antes: ahora sí cuenta
    fijar_fuente(monkeypatch, datos)
    c = dt.AdaptadorTenis().partido('t-c')
    assert [m.outcome for m in c.markets] == ['win', 'win', 'loss', None, None] and all(m.eligible for m in c.markets)


def test_mercados_y_familias(adaptador):
    c = adaptador.partido('t-c')
    assert [m.market for m in c.markets] == ['winner', 'games_total', 'tiebreak', 'sets_total', 'ace_total']
    assert [adaptador.familia_de(m.market) for m in c.markets] == ['winner', 'games_total', 'tiebreak', 'sets_total', 'ace_total']
    assert [m.family for m in c.markets] == [adaptador.familia_de(m.market) for m in c.markets]
    assert c.markets[1].push_probability == 0.04 and c.markets[0].price is None
    from qf.comercial.catalogo_semilla import SEMILLA
    catalogo = {f['familia_id'] for d in SEMILLA if d['deporte_id'] == 'tenis' for f in d['familias']}
    assert {'games_total', 'games_handicap', 'set_winner', 'sets_handicap', 'sets_total', 'tiebreak'} == catalogo
    assert {adaptador.familia_de(t) for t in catalogo} == catalogo


@pytest.mark.parametrize('sello,esperado', [(SELLO, SELLO), ('A' * 64, None), ('a' * 63, None), ('g' * 64, None), (None, None)])
def test_seal_solo_si_es_sha256_valido(monkeypatch, sello, esperado):
    datos = datos_fijos()
    datos['events'][0]['seal'] = sello
    fijar_fuente(monkeypatch, datos)
    assert dt.AdaptadorTenis().partido('t-b').seal == esperado


def test_estado_desconocido_no_se_adivina(monkeypatch):
    datos = datos_fijos()
    datos['events'][0]['status'] = 'postponed'
    fijar_fuente(monkeypatch, datos)
    with pytest.raises(ValueError):
        dt.AdaptadorTenis().partido('t-b')


@pytest.mark.parametrize('estado', ['stale', 'unavailable'])
def test_fuente_caducada_o_ausente_lanza(monkeypatch, estado):
    fijar_fuente(monkeypatch, {'sport': 'tenis', 'state': estado, 'events': [], 'problems': 0})
    with pytest.raises(RuntimeError):
        dt.AdaptadorTenis().cartelera(*AMPLIA)
    with pytest.raises(RuntimeError):
        dt.AdaptadorTenis().partido('t-b')


def test_partido_inexistente_es_none(adaptador):
    assert adaptador.partido('no-existe') is None


def test_no_filtra_campos_internos(adaptador):
    for e in adaptador.cartelera(*AMPLIA) + [adaptador.partido('t-c')]:
        assert 'CENTINELA' not in e.model_dump_json()
