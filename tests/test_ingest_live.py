from contextlib import contextmanager

import pytest

from qf.ingest import live


def _m(fid, h, a, short, started=True, finished=False):
    return {"id": fid, "home": {"score": h}, "away": {"score": a},
            "status": {"started": started, "finished": finished, "cancelled": False,
                       "liveTime": {"short": short}}}


@pytest.fixture
def entorno(monkeypatch):
    calls, pedidos = [], []

    @contextmanager
    def conn():
        yield object()

    class Cli:
        def get(self, endpoint, params):
            pedidos.append((endpoint, params))
            return {"leagues": [{"matches": [
                _m(10, 1, 0, "48‎’‎"), _m(11, 2, 2, "FT", finished=True),
                _m(12, 0, 0, "HT"), _m(99, 0, 0, "5’")]}]}

    monkeypatch.setattr(live, "conn", conn)
    monkeypatch.setattr(live.fc, "en_enfriamiento", lambda c: False)
    monkeypatch.setattr(live.af, "record_health", lambda *a, **k: None)
    monkeypatch.setattr(live, "execute", lambda sql, p=(): calls.append(p) or 1)
    return calls, pedidos, Cli()


def test_escribe_solo_los_candidatos_en_juego(monkeypatch, entorno):
    calls, pedidos, cli = entorno
    monkeypatch.setattr(live, "_candidatos", lambda: {
        "10": {"match_id": "m1", "fecha": "20261025"}, "11": {"match_id": "m2", "fecha": "20261025"},
        "12": {"match_id": "m3", "fecha": "20261025"}})
    out = live.run(cli)
    assert out["en_juego"] == 2
    assert calls[:2] == [(1, 0, 48, "2H", "m1"), (0, 0, 45, "HT", "m3")]
    assert pedidos == [("matches", {"date": "20261025", "timezone": "UTC"})]


def test_un_pedido_por_fecha_aunque_haya_muchos_partidos(monkeypatch, entorno):
    _, pedidos, cli = entorno
    monkeypatch.setattr(live, "_candidatos", lambda: {
        "10": {"match_id": "m1", "fecha": "20261025"}, "12": {"match_id": "m3", "fecha": "20261025"},
        "13": {"match_id": "m4", "fecha": "20261026"}})
    live.run(cli)
    assert [p["date"] for _, p in pedidos] == ["20261025", "20261026"]


def test_sin_candidatos_no_pide_nada(monkeypatch, entorno):
    _, pedidos, cli = entorno
    monkeypatch.setattr(live, "_candidatos", lambda: {})
    assert live.run(cli)["en_juego"] == 0 and pedidos == []


def test_en_enfriamiento_no_pide_ni_limpia(monkeypatch, entorno):
    calls, pedidos, cli = entorno
    monkeypatch.setattr(live, "_candidatos", lambda: {"10": {"match_id": "m1", "fecha": "20261025"}})
    monkeypatch.setattr(live.fc, "en_enfriamiento", lambda c: True)
    assert "omitido" in live.run(cli) and pedidos == [] and calls == []


@pytest.mark.parametrize("corto,esperado", [
    ("43‎’‎", (43, "1H")), ("45+2’", (45, "1H")), ("HT", (45, "HT")),
    ("67’", (67, "2H")), ("105’", (105, "ET")), ("Pen", (None, "LIVE")), (None, (None, "LIVE"))])
def test_minuto_y_codigo_de_la_app(corto, esperado):
    assert live.estado(corto) == esperado
