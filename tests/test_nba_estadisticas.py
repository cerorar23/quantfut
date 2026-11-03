"""Estadísticas de NBA de la web: la API solo lee el feed público, vigente y con números finitos."""
import json
from datetime import datetime, timedelta, timezone

from qf.api import nba_estadisticas as ne

AHORA = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
EVENTO = {'event_id': '0022600130', 'as_of': '2026-10-27', 'teams': [{'name': 'A', 'form': {'all': []}}, {'name': 'B', 'form': {'all': []}}],
          'h2h': {'matches': [], 'home_wins': 0, 'away_wins': 0, 'average_total': None}}


def escribir(ruta, generado, eventos):
    ruta.write_text(json.dumps({'generated_at': generado.isoformat(), 'source': 'NBA.com (marcadores oficiales)', 'events': eventos}), encoding='utf-8')


def test_lectura_vigente_descarta_eventos_mal_formados(tmp_path):
    feed = tmp_path / 'nba_stats.json'
    escribir(feed, AHORA - timedelta(hours=1), {'0022600130': EVENTO, '0022600131': {'teams': []}, '0022600132': {**EVENTO, 'h2h': {}}})
    leido = ne.read_feed(feed, AHORA)
    assert leido['state'] == 'ok' and list(leido['events']) == ['0022600130']


def test_feed_vencido_futuro_o_ausente_no_se_sirve(tmp_path):
    feed = tmp_path / 'nba_stats.json'
    escribir(feed, AHORA - timedelta(hours=7), {'0022600130': EVENTO})
    assert ne.read_feed(feed, AHORA) == {'state': 'stale', 'events': {}}
    escribir(feed, AHORA + timedelta(hours=1), {'0022600130': EVENTO})
    assert ne.read_feed(feed, AHORA)['state'] == 'stale'
    assert ne.read_feed(tmp_path / 'no_existe.json', AHORA)['state'] == 'unavailable'
    feed.write_text('{no es json', encoding='utf-8')
    assert ne.read_feed(feed, AHORA)['state'] == 'unavailable'


def test_un_numero_no_finito_invalida_ese_evento(tmp_path):
    feed = tmp_path / 'nba_stats.json'
    roto = {**EVENTO, 'teams': [{'name': 'A', 'form': {'all': []}, 'x': float('nan')}, EVENTO['teams'][1]]}
    feed.write_text(json.dumps({'generated_at': (AHORA - timedelta(hours=1)).isoformat(), 'events': {'0022600130': EVENTO, '0022600131': roto}}), encoding='utf-8')
    assert list(ne.read_feed(feed, AHORA)['events']) == ['0022600130']


def test_la_ruta_publica_valida_el_id(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from qf.api import web
    feed = tmp_path / 'nba_stats.json'
    escribir(feed, datetime.now(timezone.utc), {'0022600130': EVENTO})
    monkeypatch.setenv('QF_NBA_STATS_FEED', str(feed))
    ne._cached.cache_clear()
    app = FastAPI()
    app.include_router(web.router)
    client = TestClient(app)
    ok = client.get('/web/deportes/nba/estadisticas/0022600130')
    assert ok.status_code == 200 and ok.json()['source'].startswith('NBA.com') and ok.headers['cache-control'] == 'no-store'
    assert client.get('/web/deportes/nba/estadisticas/0022600999').status_code == 404
    assert client.get('/web/deportes/nba/estadisticas/abc').status_code == 404
    assert client.get('/web/deportes/nba/estadisticas/130').status_code == 404
