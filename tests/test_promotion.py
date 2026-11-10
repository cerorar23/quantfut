from qf.model.promotion import evaluate_base_promotion, evaluate_shadow_promotion


def _comparison(dc=0.19, elo=0.21, market=0.18):
    return {"n_obs": 2000, "models": {
        "dixon_coles": {"rps": dc}, "elo": {"rps": elo},
        "market": {"rps": market},
    }}


def test_base_puede_activarse_interno_sin_autorizar_venta():
    decision = evaluate_base_promotion(
        {"rps": 0.19, "log_loss": 1.0, "validation_signature": "x"},
        comparison=_comparison(),
    )
    assert decision.promote
    assert not decision.ready_for_commercial_picks


def test_base_no_promueve_si_no_supera_elo():
    decision = evaluate_base_promotion(
        {"rps": 0.22, "log_loss": 1.1}, comparison=_comparison(dc=0.22, elo=0.21)
    )
    assert not decision.promote


def test_no_compara_champions_de_muestras_distintas():
    decision = evaluate_base_promotion(
        {"rps": 0.19, "log_loss": 1.0, "validation_signature": "new"},
        {"rps": 0.18, "log_loss": 0.9, "validation_signature": "old"},
        comparison=_comparison(),
    )
    assert decision.promote
    assert decision.checks["champion_same_sample"] is False


def test_mercado_obsoleto_no_promueve_ni_autoriza_picks():
    stale = {**_comparison(dc=0.17, elo=0.21, market=0.18),
             "market_age_days": 250}
    decision = evaluate_base_promotion(
        {"rps": 0.17, "validation_signature": "x"},
        comparison=stale, clv={"n": 400, "avg_clv": 1.0},
    )
    assert not decision.promote
    assert not decision.ready_for_commercial_picks
    assert decision.checks["market_data_fresh"] is False


def test_shadow_exige_clv_y_varias_ligas():
    report = {"rps_before": 0.20, "rps_after": 0.19,
              "log_loss_before": 1.0, "log_loss_after": 0.98,
              "ece_before": 0.04, "ece_after": 0.03,
              "leagues_improved": 3}
    incomplete = {"n": 299, "avg_ev_close": 1.0, "ci95": [0.2, 1.8],
                  "by_league": {"L1": {"n": 100, "avg_ev_close": 0.5},
                                "L2": {"n": 100, "avg_ev_close": 0.4}}}
    complete = {**incomplete, "n": 300}
    baseline = {"n": 310, "avg_ev_close": 0.05}
    pending = evaluate_shadow_promotion(report, incomplete, baseline)
    approved = evaluate_shadow_promotion(report, complete, baseline)
    assert not pending.promote
    assert approved.promote


def _datos_calibracion(n=3000, sesgo=0.0, seed=3):
    import numpy as np
    rng = np.random.default_rng(seed)
    p_real = rng.uniform(0.2, 0.8, n)
    y = (rng.uniform(size=n) < p_real).astype(int)
    base = np.clip(p_real + sesgo, 0.01, 0.99)
    return y, p_real, base


def test_puerta_calibracion_aprueba_candidato_mejor():
    from qf.model.promotion import evaluate_calibration_gate
    y, bueno, malo = _datos_calibracion(sesgo=0.12)
    ok, motivos, m = evaluate_calibration_gate(y, bueno, malo, replicates=300)
    assert ok, motivos
    assert m["gain_ci95"][0] > 0


def test_puerta_calibracion_rechaza_empate_y_muestra_corta():
    from qf.model.promotion import evaluate_calibration_gate
    y, p, _ = _datos_calibracion()
    ok, motivos, _ = evaluate_calibration_gate(y, p, p, replicates=300)
    assert not ok and motivos
    ok, motivos, _ = evaluate_calibration_gate(y[:50], p[:50], p[:50])
    assert not ok and "insuficiente" in motivos[0]


def test_puerta_calibracion_rechaza_candidato_peor_y_acepta_grupos_y_multiclase():
    import numpy as np
    from qf.model.promotion import evaluate_calibration_gate
    y, bueno, malo = _datos_calibracion(sesgo=0.12)
    ok, _, _ = evaluate_calibration_gate(y, malo, bueno, groups=np.arange(len(y)) // 10,
                                         replicates=300)
    assert not ok
    p3 = np.tile([0.5, 0.3, 0.2], (600, 1))
    y3 = np.random.default_rng(1).choice(3, 600, p=[0.5, 0.3, 0.2])
    _, _, m = evaluate_calibration_gate(y3, p3, np.full((600, 3), 1 / 3), replicates=200)
    assert m["log_loss_gain"] > 0
