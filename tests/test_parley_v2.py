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


# ---------------------------------------------------------------- política v2.1
import itertools
import random
from datetime import timedelta

import pytest


def opx(match, price, prob, market="h2h", sel="home", line=None, book="book-a", as_of=NOW):
    return Opcion(match, Candidato(market, sel, line, prob), price, book, "test", as_of)


def test_familias_y_topes_por_mercado():
    assert v2.familia("h2h") == v2.GANADOR
    assert v2.familia("totals") == v2.LINEA and v2.familia("player_points") == v2.LINEA
    assert v2.familia("h2h_1t") == v2.EXCLUIDO          # margen del 9-11 %
    assert v2.familia("btts") == v2.SIN_MEDIR
    assert v2.tope(opx("a", 2, .5), 1) == 1.80 and v2.tope(opx("a", 2, .5), 4) == 2.50
    assert v2.tope(opx("a", 2, .5, "totals", "over", 2.5), 3) == 2.10
    assert v2.tope(opx("a", 2, .5, "totals", "over", 2.5), 1) == 1.95   # línea .5 en target bajo
    assert v2.tope(opx("a", 2, .5, "totals", "over", 2.0), 1) == 1.80   # línea entera: no
    assert v2.tope(opx("a", 2, .5, "h2h_1t"), 4) is None
    assert v2.tope(opx("a", 2, .5, "btts", "yes"), 4) == 1.80


def test_ganador_hasta_250_reduce_patas_en_targets_altos():
    ops = [opx("a", 2.40, .40), opx("b", 2.40, .40), opx("c", 1.42, .65)]   # 8.18
    t = v2.buscar(ops, v2.Target(3, 8.20))
    assert t is not None and len(t.legs) == 3
    # Con 2.40 en una línea (tope 2.10) esa combinación no existe.
    lineas = [opx("a", 2.40, .40, "totals", "over", 2.5), opx("b", 2.40, .40, "totals", "over", 2.5),
              opx("c", 1.42, .65, "totals", "over", 2.5)]
    assert v2.buscar(lineas, v2.Target(3, 8.20)) is None
    # En un target bajo el ganador no pasa de 1.80.
    assert v2.buscar([opx("a", 2.40, .40), opx("b", 1.30, .70)], v2.Target(1, 3.12)) is None


def test_primer_tiempo_1x2_y_cuotas_fuera_de_rango_no_entran():
    ops = [opx("a", 1.45, .7, "h2h_1t"), opx("b", 1.45, .7), opx("c", 1.19, .9), opx("d", 1.45, .7)]
    t = v2.buscar(ops, v2.Target(1, 2.10))
    assert t is not None and {o.match_id for o in t.legs} == {"b", "d"}


def test_consolidar_mejor_cuota_entre_casas_con_guarda_de_atipicas():
    def c(*precios):
        return [opx("m", p, .5, book=f"casa{i}") for i, p in enumerate(precios)]
    assert v2.consolidar(c(1.60, 1.95))[0].price == 1.95            # 2 casas: no hay base para juzgar
    assert v2.consolidar(c(1.60, 1.62, 1.95))[0].price == 1.62     # 3 casas, 1.95 > 1.62 × 1.05
    assert v2.consolidar(c(1.60, 1.62, 1.66))[0].price == 1.66     # dentro de la tolerancia
    assert len(v2.consolidar(c(1.6, 1.7) + [opx("m", 1.5, .5, "totals", "over", 2.5)])) == 2


def test_plan_cuatro_tickets_sin_reutilizar_eventos_y_estado_sin_calibracion():
    prices = [1.40, 1.50, 1.70, 1.80, 1.70, 1.70, 1.70, 1.70] + [1.65] * 7
    ops = [opx(f"m{i}", p, .70) for i, p in enumerate(prices)]
    plan = v2.armar_plan(ops)
    assert len(plan.tickets) == 4 and not plan.abstenciones
    ids = [o.match_id for t in plan.tickets for o in t.legs]
    assert len(ids) == len(set(ids))
    assert all(t.estado == "solo_referencia" for t in plan.tickets)
    assert plan.diagnostico["busqueda_completa"] is True


def test_publicado_solo_si_todas_las_patas_estan_calibradas():
    ops = [opx("a", 1.40, .70), opx("b", 1.50, .60)]
    cal = {(o.match_id, "h2h", "home", None): v2.Calibracion(.65, .60, .70, "art-1") for o in ops}
    plan = v2.armar_plan(ops, calibracion=cal)
    t = next(t for t in plan.tickets if t.target == 2.10)
    assert t.estado == "publicado" and math.isclose(t.probability, .65 * .65)
    assert math.isclose(t.p_bajo, .36) and math.isclose(t.p_alto, .49)
    parcial = v2.armar_plan(ops, calibracion={k: v for k, v in list(cal.items())[:1]})
    assert parcial.tickets[0].estado == "solo_referencia"


def test_abstencion_cuando_no_hay_combinacion_valida():
    plan = v2.armar_plan([opx("a", 1.40, .7), opx("b", 1.50, .7)])
    assert [t.target for t in plan.tickets] == [2.10]
    assert {a.target for a in plan.abstenciones} == {3.10, 8.20, 12.10}
    assert v2.armar_plan([]).tickets == ()


def test_cuota_posterior_a_la_decision_o_sin_hora_no_entra():
    ops = [opx("a", 1.40, .7), opx("b", 1.50, .7, as_of=NOW + timedelta(minutes=1)),
           opx("c", 1.50, .7, as_of=None), opx("d", 1.50, .7)]
    plan = v2.armar_plan(ops, ahora=NOW)
    legs = {o.match_id for t in plan.tickets for o in t.legs}
    assert legs <= {"a", "d"} and "b" not in legs and "c" not in legs


def test_same_game_solo_es_ejecutable_con_cuota_de_paquete_y_modelo_conjunto():
    legs = [opx("g", 1.5, .6, "h2h"), opx("g", 1.7, .55, "totals", "over", 2.5)]
    ref = v2.same_game(legs)
    assert ref.tipo == "same_game" and ref.estado == "solo_referencia" and math.isnan(ref.probability)
    assert v2.same_game(legs, cuota_paquete=2.9).estado == "solo_referencia"
    ok = v2.same_game(legs, cuota_paquete=2.9, prob_conjunta=.38)
    assert ok.estado == "publicado" and ok.quote == 2.9 and ok.probability == .38
    with pytest.raises(ValueError):
        v2.same_game([opx("g", 1.5, .6), opx("h", 1.5, .6)])


def test_resumen_registra_cuota_casa_hora_mercado_seleccion_y_probabilidad():
    t = v2.buscar([opx("a", 1.40, .7, book="x"), opx("b", 1.50, .7, book="y")], v2.Target(1, 2.10))
    r = v2.resumen(t)
    assert r["estrategia"] == "parley_objetivo" and r["tipo"] == "multievento"
    assert r["estado"] == "solo_referencia" and r["n_patas"] == 2
    pata = r["patas"][0]
    assert {"cuota", "casa", "cuota_en", "mercado", "seleccion", "prob"} <= set(pata)
    assert pata["cuota_en"] == NOW.isoformat()


@pytest.mark.parametrize("seed", range(20))
def test_buscar_coincide_con_busqueda_exhaustiva_en_casos_pequenos(seed):
    rng = random.Random(seed)
    ops = []
    for i in range(7):
        for _ in range(2):
            ops.append(opx(f"m{i}", round(rng.uniform(1.2, 1.8), 2), round(rng.uniform(.45, .8), 2)))
    target = v2.Target(3, 8.20)
    por_evento = {}
    for o in ops:
        por_evento.setdefault(o.match_id, []).append(o)
    mejor = None
    for n in range(2, 7):
        for grupos in itertools.combinations(por_evento.values(), n):
            for legs in itertools.product(*grupos):
                q = math.prod(o.price for o in legs)
                if target.low <= q <= target.high:
                    p = math.prod(o.cand.prob for o in legs)
                    if mejor is None or (n, -p) < mejor:
                        mejor = (n, -p)
        if mejor is not None:
            break
    t = v2.buscar(ops, target)
    if mejor is None:
        assert t is None
    else:
        assert t is not None and len(t.legs) == mejor[0]
        assert math.isclose(t.probability, -mejor[1], rel_tol=1e-9)
