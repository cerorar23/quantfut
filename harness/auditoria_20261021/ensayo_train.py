"""Ensayo EN SECO del reentrenamiento con el código nuevo: misma validación, calibrador y puerta que
`train_and_register`, sin escribir en la base ni activar nada. Código en /tmp/qfa/src."""
import json
import sys
from datetime import timedelta

sys.path.insert(0, "/tmp/qfa/src")
import pandas as pd  # noqa: E402

import qf  # noqa: E402
from qf.db import query_one  # noqa: E402
from qf.eval.backtest import metrics_from_oos, walk_forward_oos  # noqa: E402
from qf.eval.comparison import compare_elo_dc_market  # noqa: E402
from qf.model.calibration import fit_and_validate  # noqa: E402
from qf.model.dixon_coles import DixonColes  # noqa: E402
from qf.model.elo import sequential_elo  # noqa: E402
from qf.model.promotion import evaluate_base_promotion  # noqa: E402
from qf.model.train import load_training_data  # noqa: E402

assert qf.__file__.startswith("/tmp/qfa/")
HL = 270.0
df = load_training_data()
val_start = df["kickoff_utc"].max() - timedelta(days=365)
oos = walk_forward_oos(df, val_start, halflife=HL, xg_blend=0.65)
val = metrics_from_oos(oos)
elo_all = sequential_elo(df)
comp = compare_elo_dc_market(oos, elo_all[elo_all["match_id"].isin(set(oos["match_id"]))])
modelo = DixonColes(halflife_days=HL, xg_blend=0.65).fit(df)
print("ajuste final: convergió =", modelo.params.converged, "| rho", round(modelo.params.rho, 4))
cal, rep = fit_and_validate(oos["lam"].to_numpy(), oos["mu"].to_numpy(), oos["home_goals"].to_numpy(),
                            oos["away_goals"].to_numpy(), rho=modelo.params.rho)
print("calibrador:", json.dumps({k: rep.get(k) for k in ("ok", "rps_before", "rps_after", "log_loss_before",
                                                          "log_loss_after", "score_log_loss_before",
                                                          "score_log_loss_after")}))
activo = query_one("SELECT model_version, val_metrics FROM model_artifacts WHERE is_active LIMIT 1")
am = activo["val_metrics"] if activo else {}
champion = ({**am["validation_comparable"], "validation_signature": am.get("validation_signature")}
            if am.get("validation_comparable") else None)
cand = {**comp["models"]["dixon_coles"], "validation_signature": comp["match_ids_sha256"]}
dec = evaluate_base_promotion(cand, champion, comp, None)
print("activo:", activo["model_version"] if activo else None)
print("modelos (validación último año):", json.dumps(comp["models"], default=str)[:900])
print("decisión:", json.dumps(dec.as_dict(), default=str)[:1500])
# Lo que verían los partidos de hoy en la app: equipos con muestra efectiva < 5 en el modelo nuevo.
eff = pd.Series(modelo.params.effective_n, index=modelo.params.teams)
print("equipos con muestra efectiva < 5:", int((eff < 5).sum()), "de", len(eff))
for k in ("gb.premier_league||Hull", "gb.premier_league||Coventry", "nl.eredivisie||Cambuur"):
    if k in modelo._idx:
        i = modelo._idx[k]
        print(" ", k, "eff", round(eff.iloc[i], 1), "ataque", round(modelo.params.attack[i], 3),
              "defensa", round(modelo.params.defence[i], 3))
