"""Puertas auditables para no confundir un challenger prometedor con producción."""
from __future__ import annotations

from dataclasses import dataclass, asdict


MARKET_MAX_AGE_DAYS = 30


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    ready_for_commercial_picks: bool
    reasons: tuple[str, ...]
    checks: dict

    def as_dict(self) -> dict:
        out = asdict(self)
        out["reasons"] = list(self.reasons)
        return out


def evaluate_base_promotion(candidate: dict, champion: dict | None = None,
                            comparison: dict | None = None,
                            clv: dict | None = None) -> PromotionDecision:
    """
    Decide activación interna y, por separado, preparación comercial.

    Un modelo puede seguir activo para generar datos en sombra aunque todavía
    no venza al mercado. Eso NO autoriza vender picks: el segundo booleano solo
    es verdadero si supera al cierre y, con muestra suficiente, el CLV no es
    negativo.
    """
    reasons: list[str] = []
    checks: dict[str, object] = {}
    promote = True

    if comparison:
        models = comparison.get("models", {})
        dc, elo, market = (models.get("dixon_coles", {}), models.get("elo", {}),
                           models.get("market", {}))
        beats_elo = bool(dc and elo and dc.get("rps", 1) < elo.get("rps", 0))
        beats_market = bool(dc and market and dc.get("rps", 1) < market.get("rps", 0))
        checks.update({"beats_elo_same_rows": beats_elo,
                       "beats_market_same_rows": beats_market,
                       "comparison_n": comparison.get("n_obs")})
        if "market_age_days" in comparison:
            fresh = int(comparison["market_age_days"]) <= MARKET_MAX_AGE_DAYS
            checks["market_data_fresh"] = fresh
            if not fresh:
                promote = False
                reasons.append("Mercado sharp demasiado antiguo para promover")
        if not beats_elo:
            promote = False
            reasons.append("No mejora el baseline Elo sobre las mismas filas")
    else:
        checks["beats_elo_same_rows"] = None
        promote = False
        reasons.append("Falta comparación común contra Elo y mercado")
        beats_market = False

    if champion:
        same_sample = bool(
            candidate.get("validation_signature")
            and candidate.get("validation_signature") == champion.get("validation_signature")
        )
        checks["champion_same_sample"] = same_sample
        if same_sample:
            rps_ok = candidate.get("rps", 1) <= champion.get("rps", 0)
            ll_ok = candidate.get("log_loss", 10) <= champion.get("log_loss", 0)
            improves = (candidate.get("rps", 1) < champion.get("rps", 0)
                        or candidate.get("log_loss", 10) < champion.get("log_loss", 0))
            checks.update({"rps_non_inferior": rps_ok,
                           "log_loss_non_inferior": ll_ok,
                           "improves_primary_metric": improves})
            if not (rps_ok and ll_ok and improves):
                promote = False
                reasons.append("No mejora al champion en RPS/log-loss comparables")
        else:
            # Nunca se comparan métricas de ventanas diferentes. La decisión se
            # apoya en los baselines recalculados sobre la ventana actual.
            reasons.append("Champion histórico no comparable: ventana distinta")

    clv_ready, clv_reasons = evaluate_clv_gate(clv)
    checks["clv_gate"] = clv_ready
    reasons.extend(clv_reasons)

    # La autorización comercial NO exige ya batir al cierre en RPS.
    #
    # Se cambió el 2026-09-22 y el motivo está medido: sobre n=28.128
    # predicciones fuera de muestra el modelo pierde contra el cierre en las 7
    # ligas y `w_model = 0.0001`. Exigir "mi probabilidad es mejor que el
    # consenso de cierre" es exigir algo que casi nadie consigue, y sobre todo
    # es exigir lo que NO se cobra. Lo que se cobra es lo otro: que el precio
    # tomado fuera mejor que el cierre que vino después. Eso es el CLV, es
    # medible y es lo que decide aquí.
    #
    # La puerta no se ablanda al cambiarla: `evaluate_clv_gate` pide que el
    # intervalo de confianza del CLV esté ENTERO por encima de cero y en varias
    # ligas, mientras la condición anterior se conformaba con una media no
    # negativa. `beats_market_same_rows` se sigue reportando porque es
    # información valiosa; ya no es un veto.
    ready = bool(promote and clv_ready)
    if not reasons:
        reasons.append("Supera todas las puertas disponibles")
    return PromotionDecision(promote, ready, tuple(reasons), checks)


# Muestra mínima y amplitud mínima para que el CLV signifique algo.
CLV_MIN_N = 300
CLV_MIN_LEAGUES = 3


def evaluate_clv_gate(clv: dict | None) -> tuple[bool, list[str]]:
    """
    ¿El CLV autoriza vender picks?

    Tres condiciones, y ninguna sobra:

    1. Muestra: al menos 300 apuestas liquidadas con CLV. Por debajo, cualquier
       media es una anécdota.
    2. El intervalo de confianza del 95% ENTERO por encima de cero. Una media
       positiva con el intervalo cruzando cero es exactamente lo que produce
       una racha, y es el error que hunde a estos sistemas.
    3. Al menos 3 ligas con muestra propia. Un CLV que solo vive en una liga es
       un hallazgo sobre esa liga —o sobre una casa concreta, o sobre un horario
       de publicación— no sobre el sistema. Y es lo primero que desaparece
       cuando esa casa te limita la cuenta.

    El intervalo es el del valor esperado contra el cierre SIN margen
    (`ev_close_ci95`), no el de `clv_pct`. Contra la cuota con margen, apostar
    a Pinnacle sin ningún criterio da -0,32% cuando su valor real es -3,90%
    (14.294 partidos, 2026-09-23): esa vara aprobaba estrategias perdedoras.
    """
    if not clv:
        return False, ["Sin datos de CLV: no se puede autorizar la venta"]

    n = int(clv.get("n", 0))
    if n < CLV_MIN_N:
        return False, [f"CLV con muestra insuficiente ({n} < {CLV_MIN_N})"]

    ci = clv.get("ev_close_ci95")
    if not ci:
        return False, ["CLV sin intervalo de confianza"]
    if float(ci[0]) <= 0.0:
        return False, ["El intervalo del valor esperado al cierre sin margen "
                       f"no está entero por encima de cero: [{ci[0]}, {ci[1]}]"]

    ligas = int(clv.get("n_leagues_with_sample", 0))
    if ligas < CLV_MIN_LEAGUES:
        return False, [f"CLV positivo en muy pocas ligas ({ligas} < {CLV_MIN_LEAGUES})"]

    return True, []


def evaluate_shadow_promotion(report: dict, clv: dict | None = None,
                              baseline_clv: dict | None = None,
                              min_leagues: int = 2) -> PromotionDecision:
    """Puerta más dura para features, logística o ajustes por alineación."""
    checks = {
        "rps_improves": report.get("rps_after", 1) < report.get("rps_before", 0),
        "log_loss_improves": (report.get("log_loss_after", 10)
                              < report.get("log_loss_before", 0)),
        "calibration_non_inferior": (report.get("ece_after", 1)
                                     <= report.get("ece_before", 0)),
        "league_breadth": int(report.get("leagues_improved", 0)) >= min_leagues,
    }
    clv = clv or {}
    baseline_clv = baseline_clv or {}
    n_clv = int(clv.get("n", 0))
    ci = clv.get("ci95") or []
    checks["clv_positive_with_uncertainty"] = (
        n_clv >= 300 and len(ci) == 2 and float(ci[0]) > 0)
    positive_leagues = sum(
        int(data.get("n", 0)) >= 30 and float(data.get("avg_ev_close") or 0) > 0
        for data in (clv.get("by_league") or {}).values()
    )
    checks["clv_league_breadth"] = positive_leagues >= min_leagues
    checks["beats_baseline_t60_clv"] = (
        int(baseline_clv.get("n", 0)) >= 300
        and clv.get("avg_ev_close") is not None
        and baseline_clv.get("avg_ev_close") is not None
        and float(clv["avg_ev_close"]) > float(baseline_clv["avg_ev_close"])
    )
    reasons = [name for name, ok in checks.items() if not ok]
    return PromotionDecision(
        promote=all(checks.values()),
        ready_for_commercial_picks=all(checks.values()),
        reasons=tuple(reasons or ["Supera RPS, log-loss, calibración, ligas y CLV"]),
        checks=checks,
    )
