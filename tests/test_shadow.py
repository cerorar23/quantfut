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


def test_sin_challenger_propio_usa_el_ultimo_validado(monkeypatch, tmp_path):
    import os
    from dataclasses import replace

    from qf.model import shadow
    from qf.model.lineup_challenger import LineupLambdaChallenger, LineupParams

    def guardar(nombre, validado, mtime):
        c = LineupLambdaChallenger(LineupParams([0.0], [1.0], [0.0, 0.0], [0.0, 0.0],
                                                -0.05, 0.5, 700, validado))
        ruta = tmp_path / nombre
        c.save(str(ruta))
        os.utime(ruta, (mtime, mtime))

    guardar("lineup_viejo.pkl", True, 1_000)
    guardar("lineup_nuevo_sin_validar.pkl", False, 2_000)
    monkeypatch.setattr(shadow, "settings", replace(shadow.settings, artifact_dir=str(tmp_path)))
    elegido = shadow._challenger_validado("version_activa_sin_artefacto")
    assert elegido is not None and elegido.params.offline_validated
    guardar("lineup_version_activa.pkl", False, 3_000)
    assert shadow._challenger_validado("version_activa").params.offline_validated


def test_la_sombra_no_toma_un_brazo_de_valor_por_el_xi_simple(monkeypatch, tmp_path):
    import os
    from dataclasses import replace

    from qf.model import shadow
    from qf.model.lineup_challenger import LINEUP_FEATURES, LineupLambdaChallenger, LineupParams

    def guardar(nombre, features, mtime):
        n = len(features)
        c = LineupLambdaChallenger(LineupParams([0.0] * n, [1.0] * n, [0.0] * (n + 1),
                                                [0.0] * (n + 1), -0.05, 0.5, 700, True,
                                                list(features)))
        ruta = tmp_path / nombre
        c.save(str(ruta))
        os.utime(ruta, (mtime, mtime))

    guardar("lineup_v1.pkl", LINEUP_FEATURES, 1_000)
    guardar("lineup_valor_v2.pkl", ["home_d_tiros"], 2_000)
    monkeypatch.setattr(shadow, "settings", replace(shadow.settings, artifact_dir=str(tmp_path)))
    assert shadow._challenger_validado("v2").params.features == LINEUP_FEATURES
