"""
Las predicciones fuera de muestra del walk-forward se guardan con cada
entrenamiento. La Fase B de la fuerza por jugador las necesita como base para
comparar brazos del XI sin repetir un entrenamiento de 3,5 horas.
"""
from __future__ import annotations

import pandas as pd

from qf.model.train import guardar_oos


def test_se_guardan_con_su_version_y_se_leen_igual(tmp_path):
    oos = pd.DataFrame({"match_id": ["a", "b"], "lam": [1.4, 1.1], "mu": [1.0, 1.2],
                        "rho": [-0.05, -0.04],
                        "kickoff_utc": pd.to_datetime(["2026-01-01", "2026-01-08"], utc=True)})
    ruta = guardar_oos(oos, "2026.10.01-030000", str(tmp_path))
    assert ruta.endswith("oos_2026.10.01-030000.pkl")
    pd.testing.assert_frame_equal(pd.read_pickle(ruta), oos)
