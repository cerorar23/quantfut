"""Cash prop contract validation; no fabricated odds or unknown settlement EV."""
import math

from .context import utc
from .model import contract_probabilities


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("finite numeric value required")
    return float(value)


def validate_quote(quote, as_of, max_age_seconds=60):
    required = ("event_id", "player_id", "book", "market", "period", "line", "over_decimal", "under_decimal",
                "tipoff_utc", "source_updated_at_utc", "first_received_at_utc", "rules_sha256", "source", "settlement_source", "early_exit_rule")
    if any(quote.get(k) is None for k in required):
        raise ValueError("incomplete market contract")
    if quote["market"] not in {"player_rebounds", "player_points", "player_assists"} or quote["period"] != "full_game":
        raise ValueError("unsupported market contract")
    if quote.get("payout_type") != "cash" or quote.get("rules_verified") is not True or quote.get("available") is not True:
        raise ValueError("unverified rules or unavailable cash contract")
    if (not isinstance(quote["rules_sha256"], str) or len(quote["rules_sha256"]) != 64
            or any(c not in "0123456789abcdef" for c in quote["rules_sha256"])):
        raise ValueError("invalid rules hash")
    if quote.get("overtime") not in {"included", "excluded"} or quote.get("dnp_rule") != "void" or quote.get("push_rule") != "refund":
        raise ValueError("unsupported settlement rules")
    if quote["early_exit_rule"] != "action_after_participation":
        raise ValueError("conditional early-exit void rules require a dedicated contract adapter")
    line = number(quote["line"])
    if line < 0 or line * 2 != round(line * 2):
        raise ValueError("invalid count line")
    over, under = number(quote["over_decimal"]), number(quote["under_decimal"])
    if not 1 < over <= 1000 or not 1 < under <= 1000:
        raise ValueError("invalid decimal prices")
    now, updated, received, tip = (utc(value) for value in (as_of, quote["source_updated_at_utc"], quote["first_received_at_utc"], quote["tipoff_utc"]))
    if not updated <= received <= now < tip or (now - updated).total_seconds() > max_age_seconds:
        raise ValueError("stale, future or post-tipoff quote")
    margin = 1 / over + 1 / under - 1
    return dict(overround=margin, no_vig_over=(1 / over) / (1 + margin),
                no_vig_under=(1 / under) / (1 + margin),
                age_seconds=(now - updated).total_seconds(), actionable=False)


def price_contract(pmf, quote, as_of, void_probability=None, distribution_overtime=None):
    validation = validate_quote(quote, as_of)
    if not pmf or any(number(v) < 0 for v in pmf) or abs(sum(pmf) - 1) > 1e-8:
        raise ValueError("invalid count distribution")
    probabilities = contract_probabilities(pmf, quote["line"])
    result = dict(validation=validation, probabilities_conditional_on_participation=probabilities,
                  void_probability=void_probability, actionable=False)
    if void_probability is None:
        result.update(ev=None, reason="void_probability_unknown")
        return result
    if distribution_overtime != quote["overtime"]:
        raise ValueError("distribution/contract overtime scope mismatch")
    void = number(void_probability)
    if not 0 <= void <= 1:
        raise ValueError("invalid void probability")
    result["ev"] = {side: (1 - void) * (probabilities[side] * (quote[side + "_decimal"] - 1)
                                         - probabilities["under" if side == "over" else "over"])
                    for side in ("over", "under")}
    result["reason"] = "hypothetical_cash_ev_unpromoted"
    return result


def revalidate_selection(original, latest, side, minimum_decimal, as_of):
    """Require the exact original contract and a still-acceptable fresh price."""
    validate_quote(latest, as_of)
    fields = ("event_id", "player_id", "book", "market", "period", "line", "rules_sha256", "overtime", "early_exit_rule",
              "dnp_rule", "push_rule", "payout_type", "settlement_source", "tipoff_utc")
    if any(original.get(k) != latest.get(k) for k in fields):
        raise ValueError("selected contract changed")
    if side not in {"over", "under"} or not 1 < number(minimum_decimal) <= latest[side + "_decimal"]:
        raise ValueError("price below required minimum")
    return dict(revalidated=True, actionable=False, current_decimal=latest[side + "_decimal"])
