"""/alta-probabilidad es público y no expone nada privado."""
from fastapi.testclient import TestClient

INFORME = {"estado": "activa", "motivos": [], "historial": {"n": 0},
           "proximos": [{"match_id": "m1", "texto": "Cruzeiro o empate", "prob": 0.87}]}


def _client(monkeypatch):
    from qf.api import main
    from qf.publish import alta_prob_datos
    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *_a: False)
    monkeypatch.setattr(alta_prob_datos, "informe_publico", lambda: INFORME)
    from qf.api import mobile
    from datetime import datetime, timedelta, timezone
    monkeypatch.setattr(mobile, 'features', lambda: {key: {'enabled': True} for key in mobile.SECTIONS})
    monkeypatch.setattr(mobile, 'high_rows', lambda: [{**INFORME['proximos'][0], 'kickoff_utc': datetime.now(timezone.utc)+timedelta(days=1), 'ref_price':1.4, 'batch_date':'2026-10-11'}])
    monkeypatch.setattr(mobile, 'allocations', lambda rows, stream: {'m1'})
    return TestClient(main.app)


def test_publico_sin_token(monkeypatch):
    r = _client(monkeypatch).get("/alta-probabilidad")
    assert r.status_code == 200
    assert r.json()["proximos"][0]["texto"] == "Cruzeiro o empate"


def test_tarjeta_del_panel_sin_lista(monkeypatch):
    from qf.api import console
    from qf.publish import alta_prob_datos
    monkeypatch.setattr(alta_prob_datos, "informe_publico", lambda: INFORME)
    card = console._alta_card()
    assert card["estado"] == "activa" and "proximos" not in card
    assert card["proximos_sellados"] == 1
