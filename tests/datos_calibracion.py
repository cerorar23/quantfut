"""Datos de calibración de ejemplo, con la forma de los reales (`/calibration` de fútbol y `/nba/v1/calibracion`)."""
from datetime import datetime, timezone

BINS = [
    {"n": 125, "se": 0.0191, "bin": "0.0-0.1", "gap": -0.026, "observed": 0.048, "predicted": 0.074, "within_2se": True},
    {"n": 897, "se": 0.0118, "bin": "0.1-0.2", "gap": -0.0171, "observed": 0.1472, "predicted": 0.1643, "within_2se": True},
    {"n": 4076, "se": 0.0068, "bin": "0.2-0.3", "gap": -0.0057, "observed": 0.2485, "predicted": 0.2542, "within_2se": True},
    {"n": 2100, "se": 0.0107, "bin": "0.3-0.4", "gap": 0.031, "observed": 0.381, "predicted": 0.350, "within_2se": False},
    {"n": 1500, "se": 0.0128, "bin": "0.4-0.5", "gap": -0.004, "observed": 0.446, "predicted": 0.450, "within_2se": True},
]

FUTBOL = [
    {"model_version": "2026.11.09-063559", "window_start": "2025-11-09", "window_end": "2026-11-09", "n_obs": 3222, "rps": 0.2091,
     "rps_market": 0.2009, "log_loss": 1.0081, "brier": 0.6032, "bins": BINS, "created_at": datetime(2026, 11, 9, 14, 8, 48, tzinfo=timezone.utc)},
    {"model_version": "2026.10.26-020600", "window_start": "2025-10-25", "window_end": "2026-10-25", "n_obs": 2045, "rps": 0.2037,
     "rps_market": 0.1941, "log_loss": 1.0028, "brier": 0.5993, "bins": BINS, "created_at": datetime(2026, 10, 26, 2, 10, 59, tzinfo=timezone.utc)},
    {"model_version": "2026.10.22-185314", "window_start": "2025-10-22", "window_end": "2026-10-22", "n_obs": 2024, "rps": 0.2036,
     "rps_market": 0.1946, "log_loss": 0.9993, "brier": 0.5972, "bins": BINS, "created_at": datetime(2026, 10, 22, 18, 56, 36, tzinfo=timezone.utc)},
]

NBA = {
    "historico": {"temporada": "2025-26", "metodo": "hacia adelante",
                  "equipo": {"modelo": {"brier_ganador": 0.2063, "pendiente_ganador": 1.07}, "mercado": {"brier_ganador": 0.1981},
                             "n": {"ganador": 1269, "handicap": 1126, "total": 1113}}},
    "prospectivo": {"version_modelo": "equipo-2.2", "sellados": 17, "con_resultado": 17, "brier_ganador": 0.16953078955294118,
                    "logloss_ganador": 0.5155517897792995, "estado_evidencia": "descriptiva", "calibracion_certificada": False,
                    "fiabilidad": [{"desde": 0.0, "hasta": 0.2, "n": 2, "prob_media": 0.16995, "tasa_observada": 0.0},
                                   {"desde": 0.2, "hasta": 0.4, "n": 2, "prob_media": 0.317215, "tasa_observada": 0.0},
                                   {"desde": 0.4, "hasta": 0.6, "n": 11, "prob_media": 0.5379454545454545, "tasa_observada": 0.5454545454545454},
                                   {"desde": 0.6, "hasta": 0.8, "n": 1, "prob_media": 0.75693, "tasa_observada": 1.0},
                                   {"desde": 0.8, "hasta": 1.0, "n": 1, "prob_media": 0.876, "tasa_observada": 1.0}]},
}
