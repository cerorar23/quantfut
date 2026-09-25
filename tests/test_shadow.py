from qf.model import shadow
from qf.model.shadow import select_h2h_candidates


def test_shadow_selecciona_mejor_cuota_sin_publicar():
    probs = {"home": 0.55, "draw": 0.25, "away": 0.20}
    quotes = [
        {"selection": "home", "price": 2.00, "bookmaker": "a"},
        {"selection": "home", "price": 2.10, "bookmaker": "b"},
        {"selection": "draw", "price": 3.20, "bookmaker": "a"},
        {"selection": "away", "price": 4.00, "bookmaker": "a"},
    ]
    out = select_h2h_candidates(probs, quotes, shrinkage=0.55,
                                min_edge_pct=3.0)
    assert len(out) == 1
    assert out[0]["selection"] == "home"
    assert out[0]["bookmaker"] == "b"


def test_shadow_espera_cuota_posterior_al_xi(monkeypatch):
    monkeypatch.setattr(shadow, "_quotes", lambda *_: [])

    def forbidden(*_args, **_kwargs):
        raise AssertionError("No debe insertar una predicción sin cuota fresca")

    monkeypatch.setattr(shadow, "query_one", forbidden)
    match = {"match_id": "m", "prediction_id": "p", "as_of": object()}
    assert shadow._insert_shadow(match, "v1", 1.4, 1.1, 0.0,
                                 {"home": 0.5, "draw": 0.3, "away": 0.2},
                                 {}) is None
