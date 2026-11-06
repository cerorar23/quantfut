import math
from datetime import datetime, timezone

from qf.publish.alta_prob import Candidato
from qf.publish.escalera import Opcion
from qf.publish import parley_v2 as v2


NOW = datetime(2026, 11, 6, tzinfo=timezone.utc)


def op(match: str, price: float, prob: float, market: str = "h2h") -> Opcion:
    return Opcion(match, Candidato(market, "home", None, prob), price,
                  "book-a", "test", NOW)


def test_targets_are_four_and_tolerance_is_two_percent():
    assert v2.TARGETS == (2.10, 3.10, 8.20, 12.10)
    t = v2.Target(1, 2.10)
    assert math.isclose(t.low, 2.058) and math.isclose(t.high, 2.142)


def test_minimizes_legs_before_probability():
    # 2 legs are valid; a 3-leg alternative has a greater product probability.
    ops = [op("a", 1.40, .90), op("b", 1.50, .90),
           op("c", 1.20, .99), op("d", 1.20, .99), op("e", 1.50, .99)]
    ticket = v2.buscar(ops, v2.Target(1, 2.10))
    assert ticket is not None
    assert len(ticket.legs) == 2
    assert v2.Target(1, 2.10).low <= ticket.quote <= v2.Target(1, 2.10).high


def test_four_tickets_do_not_reuse_events():
    # Two candidates per event let the optimizer find all four targets.
    ops = []
    prices = [1.40, 1.50, 1.70, 1.80,
              1.70, 1.70, 1.70, 1.70,
              1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65]
    for i, price in enumerate(prices):
        ops.append(op(f"m{i}", price, .70))
    tickets = v2.armar_dia(ops)
    assert len(tickets) == 4
    ids = [o.match_id for t in tickets for o in t.legs]
    assert len(ids) == len(set(ids))


def test_log_totals_are_stable_and_auditable():
    ticket = v2.buscar([op("a", 1.4, .8), op("b", 1.5, .7)],
                       v2.Target(1, 2.1))
    assert ticket is not None
    logs = v2.log_totals(ticket)
    assert math.isclose(math.exp(logs["log_quote"]), ticket.quote)
    assert math.isclose(math.exp(logs["log_probability"]), ticket.probability)
