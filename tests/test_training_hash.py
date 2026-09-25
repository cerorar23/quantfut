from datetime import datetime, timezone

import pandas as pd

from qf.model.train import dataset_hash


def _df():
    return pd.DataFrame([{
        "match_id": "m1", "kickoff_utc": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "home_goals": 1, "away_goals": 0, "home_xg": 1.2,
        "home_shots": 10, "odds_home": 2.0,
    }])


def test_hash_cambia_si_cambia_cualquier_feature():
    original = _df()
    changed = original.copy()
    changed.loc[0, "home_shots"] = 11
    assert dataset_hash(original) != dataset_hash(changed)


def test_hash_incluye_configuracion_y_es_estable_al_orden_de_columnas():
    frame = _df()
    reversed_columns = frame[list(reversed(frame.columns))]
    assert dataset_hash(frame, {"xg_blend": 0.65}) == dataset_hash(
        reversed_columns, {"xg_blend": 0.65})
    assert dataset_hash(frame, {"xg_blend": 0.65}) != dataset_hash(
        frame, {"xg_blend": 0.50})
