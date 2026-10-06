"""/alta-probabilidad es público y no expone nada privado."""
from fastapi.testclient import TestClient

INFORME = {"estado": "activa", "motivos": [], "historial": {"n": 0},
           "proximos": [{"match_id": "m1", "texto": "Cruzeiro o empate", "prob": 0.87}]}


def _client(monkeypatch):
    from qf.api import main
    from qf.publish import alta_prob_datos
    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *_a: False)
    monkeypatch.setattr(alta_prob_datos, "informe_publico", lambda: INFORME)
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
