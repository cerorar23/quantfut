"""Paridad del adaptador NBA del contrato con la web: mismos datos de entrada -> lo que construyen `nbaV2Events` /
`nbaPickMarkets` (`frontend/sports-data.js`) coincide en id, home, away, start, status, score, sellos y mercado ganador."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from nba_contrato_datos import AHORA, DIAS, NbaApiFalsa, instalar, partido

from qf.api.deportes_nba import AdaptadorNba

RAIZ = Path(__file__).resolve().parents[1]
GUION = """
import {nbaV2Events} from './sports-data.js';
const datos = JSON.parse(process.argv[1]), ahora = new Date(process.argv[2]);
console.log(JSON.stringify(nbaV2Events(datos, ahora)));
"""


def _web(partidos, ahora):
    r = subprocess.run(['node', '--input-type=module', '-e', GUION, json.dumps(partidos), ahora.isoformat()],
                       cwd=RAIZ / 'frontend', capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _t(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')) if s else None


@pytest.mark.skipif(shutil.which('node') is None, reason='node no está instalado')
def test_eventos_del_contrato_coinciden_con_nbaV2Events(monkeypatch):
    instalar(monkeypatch)
    partidos = [p for dia in DIAS.values() for p in dia]
    web = {str(e['id']): e for e in _web(partidos, AHORA)}
    contrato = {e.id: e for e in AdaptadorNba().cartelera(datetime(2026, 11, 1, tzinfo=timezone.utc),
                                                           datetime(2026, 12, 1, tzinfo=timezone.utc))}
    assert set(contrato) == set(web) == {'99', '100', '101', '102', '103'}
    for id, c in contrato.items():
        w = web[id]
        assert (c.home, c.away, c.league, c.status, c.score, c.seal) == (w['home'], w['away'], w['league'], w['status'], w['score'], w['seal'])
        assert c.start == _t(w['start']) and c.sealed_at == _t(w['sealed_at']) and c.planned_seal == _t(w['planned_seal'])
        assert len(c.markets) == len(w['markets'])
        for m, wm in zip(c.markets, w['markets']):
            assert (m.id, m.label, m.market, m.selection, m.probability, m.outcome, m.eligible) == (
                wm['id'], wm['label'], wm['market'], wm['selection'], wm['probability'], wm['outcome'], wm['eligible'])
            assert m.sealed_at == _t(wm['sealed_at']) and m.reference == wm['reference']
        assert c.team_projection == w['team_projection']          # «Puntos esperados» de la web


DESTACADO = """
import {nbaV2Events, featuredSportMarket} from './sports-data.js';
const datos = JSON.parse(process.argv[1]), ahora = new Date(process.argv[2]);
console.log(JSON.stringify(nbaV2Events(datos, ahora).map(e => [String(e.id), featuredSportMarket(e)?.id ?? null, e.markets.length, e.team_projection])));
"""


@pytest.mark.skipif(shutil.which('node') is None, reason='node no está instalado')
def test_destacado_y_mercados_de_la_cartelera_coinciden_con_la_web(monkeypatch):
    """Mismo pronóstico -> `featuredSportMarket` de la web y `Evento.destacado` del contrato dan el mismo id; incluye los bordes
    del 75 % y el 83,3 %, el visitante favorito, la revisión posterior al inicio y un partido sin pronóstico."""
    probs = [0.75, 0.7499, 0.80, 0.83, 0.8333, 0.8334, 0.84, 0.95, 0.62, 0.5, 0.25, 0.20, 0.17, 0.16, 0.30]
    partidos = [partido(1000 + i, 'Boston Celtics', 'Utah Jazz', '2026-11-12', '2026-11-13T00:00:00+00:00', p_local=p) for i, p in enumerate(probs)]
    partidos += [partido(2000, 'Boston Celtics', 'Utah Jazz', '2026-11-12', '2026-11-13T00:00:00+00:00', p_local=0.78, sellado='despues'),
                 partido(2001, 'Boston Celtics', 'Utah Jazz', '2026-11-12', '2026-11-13T00:00:00+00:00', sellado=None)]
    instalar(monkeypatch, NbaApiFalsa(dias={'2026-11-12': partidos}))
    web = {i: (d, n, mu) for i, d, n, mu in json.loads(_web_destacado(partidos, AHORA))}
    contrato = {e.id: e for e in AdaptadorNba().cartelera(datetime(2026, 11, 12, tzinfo=timezone.utc), datetime(2026, 11, 15, tzinfo=timezone.utc))}
    assert set(contrato) == set(web) and len(web) == len(probs) + 2
    for id, e in contrato.items():
        destacado_web, n_web, mu_web = web[id]
        assert e.destacado == destacado_web, id
        assert len(e.markets) == n_web and e.team_projection == mu_web, id        # el ganador siempre sale (también revisado)
    assert web['2000'][0] is None and web['2000'][1] == 1                           # revisión: sin destacado, pero con su mercado
    assert sum(1 for d, _, _ in web.values() if d) == 7                            # los que caen en la franja


def _web_destacado(partidos, ahora):
    r = subprocess.run(['node', '--input-type=module', '-e', DESTACADO, json.dumps(partidos), ahora.isoformat()],
                       cwd=RAIZ / 'frontend', capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout
