"""Adaptador de demostración `prueba`: cumple el contrato bajo cualquier id de deporte del catálogo."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from qf.api import deportes_demo, deportes_v1 as dv, ratelimit  # noqa: F401
from qf.api.main import app
from qf.comercial import catalogo
from tests.test_deportes_v1 import fijar_catalogo


@pytest.fixture
def c(monkeypatch):
    monkeypatch.setattr(ratelimit, 'rate_limited', lambda *a, **k: False)
    return TestClient(app)


def _get(c, mp, deporte, ruta, **kw):
    fijar_catalogo(mp, deporte, 'prueba')
    return c.get(f'/deportes/v1/{deporte}/{ruta}', params={'cliente': 'web', **kw})


@pytest.mark.parametrize('deporte', ['golf_prueba', 'rugby_prueba'])
def test_cartelera_detalle_y_mercados(c, monkeypatch, deporte):
    hoy = datetime.now(timezone.utc).date()
    r = _get(c, monkeypatch, deporte, 'cartelera', desde=(hoy - timedelta(days=1)).isoformat(), dias=4)
    assert r.status_code == 200, r.text
    evs = r.json()['eventos']
    assert [e['id'] for e in evs] == ['demo-1', 'demo-2', 'demo-3', 'demo-4']
    assert all(e['sport'] == deporte and e['league'] == 'Demostración' and e['seal'] is None for e in evs)
    assert [e['status'] for e in evs] == ['finished', 'finished', 'scheduled', 'scheduled']

    r = _get(c, monkeypatch, deporte, 'partido/demo-1', lang='es')
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['evento']['score'] == '2-1'
    assert [b['tipo'] for b in j['bloques']] == ['tabla', 'barras', 'pares', 'texto']
    assert 'demostración' in j['bloques'][3]['cuerpo'].lower()

    r = _get(c, monkeypatch, deporte, 'partido/demo-1/mercados')
    assert r.status_code == 200, r.text
    ms = [m for f in r.json()['familias'] for m in f['mercados']]
    assert {m['outcome'] for m in ms} == {'win', 'loss'} and all(m['eligible'] for m in ms)
    r = _get(c, monkeypatch, deporte, 'partido/demo-3/mercados')
    assert all(m['outcome'] is None for f in r.json()['familias'] for m in f['mercados'])


def test_partido_ajeno_es_404(c, monkeypatch):
    assert _get(c, monkeypatch, 'golf_prueba', 'partido/no-existe').status_code == 404


def test_catalogo_acepta_el_adaptador():
    assert 'prueba' in catalogo.ADAPTADORES and 'prueba' in dv.ADAPTADORES
