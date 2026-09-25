from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from qf.model.features import FEATURE_GROUPS
from qf.model.multinomial import fit_and_validate, prepare_frame


def _frame(n=700, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    for i in range(n):
        market = rng.dirichlet([4, 3, 4])
        elo = rng.normal()
        true = market.copy()
        true[0] *= np.exp(0.25 * elo)
        true[2] *= np.exp(-0.25 * elo)
        true /= true.sum()
        row = {
            "match_id": f"m{i}", "kickoff_utc": start + timedelta(days=i),
            "league_id": f"L{i % 3}", "outcome": rng.choice(3, p=true),
            "p_home": 0.4, "p_draw": 0.27, "p_away": 0.33,
            "mk_home": market[0], "mk_draw": market[1], "mk_away": market[2],
        }
        for cols in FEATURE_GROUPS.values():
            row.update({c: rng.normal() for c in cols})
        row["elo_diff"] = elo
        rows.append(row)
    return pd.DataFrame(rows)


def test_parametrizacion_mercado_es_finita():
    frame = prepare_frame(_frame(20))
    assert np.isfinite(frame["market_log_home_draw"]).all()
    assert np.isfinite(frame["market_log_away_draw"]).all()


def test_challenger_multinomial_devuelve_probabilidades_validas():
    df = _frame()
    model, report = fit_and_validate(
        df, groups=("elo",), anchored=True, min_fit=300, min_val=100,
        c_grid=(0.1, 0.3),
    )
    assert model is not None
    probs = model.predict_proba(prepare_frame(df.tail(25)))
    assert probs.shape == (25, 3)
    assert np.allclose(probs.sum(axis=1), 1.0)
    assert report["status"] == "shadow_only"
    assert report["promotion_blocked_until_clv"]
