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
    monkeypatch.setattr(live, "record_health", lambda *a, **k: None)
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


def _fin(fid, h, a, motivo="FT"):
    m = _m(fid, h, a, None, finished=True)
    m["status"]["reason"] = {"short": motivo}
    return m


class _Cli:
    def __init__(self, partidos):
        self.partidos = partidos

    def get(self, endpoint, params):
        return {"leagues": [{"matches": self.partidos}]}


class _Con:
    def rollback(self):
        pass


def test_al_pitido_cierra_con_fotmob_sin_rellenar_y_liquida(monkeypatch, entorno):
    """Decisión del titular (25-oct): el resultado se cierra al pitido con la primera fuente que lo tenga."""
    cerrados, liquidado = [], []
    monkeypatch.setattr(live, "_candidatos", lambda: {
        "20": {"match_id": "m20", "fecha": "20261025"}, "21": {"match_id": "m21", "fecha": "20261025"},
        "22": {"match_id": "m22", "fecha": "20261025"}})
    monkeypatch.setattr(live.fc, "cerrar_partido",
                        lambda c, cli, f, rellenar=True: cerrados.append((f["match_id"], rellenar)) or "cerrados")
    import qf.eval.clv as clv
    monkeypatch.setattr(clv, "settle_pending", lambda: liquidado.append(1) or {"settled": 1})
    out = live.run(_Cli([_fin(20, 2, 1), _fin(21, 1, 1, "AET"), _fin(22, 0, 0, "Pen")]))
    assert cerrados == [("m20", False)]                 # prórroga y penaltis: PropLine o el respaldo
    assert out["cierres"] == {"cerrados": 1} and liquidado == [1]


def test_un_cierre_fallido_no_deja_sin_marcador_al_resto(monkeypatch, entorno):
    calls, _, _ = entorno
    monkeypatch.setattr(live, "conn", lambda: _ctx(_Con()))
    monkeypatch.setattr(live, "_candidatos", lambda: {
        "20": {"match_id": "m20", "fecha": "20261025"}, "10": {"match_id": "m1", "fecha": "20261025"}})

    def falla(c, cli, f, rellenar=True):
        raise RuntimeError("red")

    monkeypatch.setattr(live.fc, "cerrar_partido", falla)
    out = live.run(_Cli([_fin(20, 2, 1), _m(10, 1, 0, "48’")]))
    assert out["en_juego"] == 1 and out["cierres"] == {"error": 1}
    assert calls[0] == (1, 0, 48, "2H", "m1")


@contextmanager
def _ctx(valor):
    yield valor


def test_no_cierra_partidos_de_ligas_retiradas():
    cand = {"20": {"match_id": "m20", "activa": False}, "21": {"match_id": "m21", "activa": True}}
    assert [c["match_id"] for c in live.terminados({"leagues": [{"matches": [_fin(20, 1, 0), _fin(21, 0, 0)]}]}, cand)] \
        == ["m21"]
