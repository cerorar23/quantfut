"""Parley del día: reglas puras (escalones, búsqueda, liquidación, control)."""
import itertools
import math
import random
from datetime import datetime, timedelta, timezone

from qf.publish import parley as pl
from qf.publish.alta_prob import Candidato
from qf.publish.escalera import Opcion

AHORA = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)


def _o(match, prob, price, market="totals", sel="over", line=1.5, as_of=AHORA):
    return Opcion(match, Candidato(market, sel, line, prob), price, "betano", "the_odds_api", as_of)


def _fuerza_bruta(patas, escalon):
    por = {}
    for o in patas:
        por.setdefault(o.match_id, []).append(o)
    mejor = None
    ids = sorted(por)
    for k in range(pl.MIN_PATAS, pl.MAX_PATAS + 1):
        for sub in itertools.combinations(ids, k):
            for combo in itertools.product(*(por[m] for m in sub)):
                q = math.prod(o.price for o in combo)
                if not pl.en_escalon(q, escalon):
                    continue
                p = math.prod(o.cand.prob for o in combo)
                if mejor is None or p > mejor[0] + 1e-12:
                    mejor = (p, q, combo)
    return mejor


def test_bordes_de_escalon():
    assert pl.en_escalon(1.90, 1) and not pl.en_escalon(1.8999, 1)
    assert not pl.en_escalon(2.20, 1) and pl.en_escalon(2.20, 2)
    assert pl.en_escalon(5.00, 5) and not pl.en_escalon(5.0001, 5)
    assert sum(pl.en_escalon(q, e) for q in (2.2, 2.7, 3.4, 4.3) for e in range(1, 6)) == 4


def test_cuota_erronea_fuera():
    buena, erronea = _o("a", 0.70, 1.40), _o("b", 0.18, 19.0, market="h2h", sel="away", line=None)
    assert pl.filtrar([buena, erronea], AHORA) == [buena]


def test_filtro_cuota_minima_mercado_y_hora():
    assert pl.filtrar([_o("a", 0.9, 1.10)], AHORA) == []
    assert pl.filtrar([_o("a", 0.7, 1.40, market="double_chance", sel="1X", line=None)], AHORA) == []
    assert pl.filtrar([_o("a", 0.7, 1.40, as_of=AHORA + timedelta(minutes=1))], AHORA) == []


def test_busqueda_igual_a_fuerza_bruta():
    rnd = random.Random(20261011)
    comparados = 0
    for _ in range(60):
        patas = []
        for i in range(rnd.randint(3, 7)):
            for _ in range(rnd.randint(1, 3)):
                price = round(rnd.uniform(1.15, 2.2), 2)
                prob = min(0.97, 1 / price * rnd.uniform(0.9, 1.05))
                patas.append(_o(f"m{i}", prob, price, line=rnd.choice([1.5, 2.5, 3.5])))
        for esc, lo, hi in pl.ESCALONES:
            bruta = _fuerza_bruta(patas, esc)
            sel = pl.buscar(patas, esc)
            if bruta is None:
                assert sel is None
                continue
            # La rejilla de 0,2 % puede perder un óptimo pegado al borde: solo
            # se exige igualdad cuando el óptimo no está a menos de 0,3 %.
            if min(abs(math.log(bruta[1] / lo)), abs(math.log(bruta[1] / hi))) < 0.003:
                continue
            assert sel is not None
            assert math.prod(o.cand.prob for o in sel) >= bruta[0] - 1e-9
            comparados += 1
    assert comparados > 100


def test_respeta_limites_de_patas_y_un_partido_por_parlay():
    patas = [_o(f"m{i}", 0.85, 1.16) for i in range(10)] + [_o("m0", 0.80, 1.20, line=2.5)]
    sel = pl.buscar(patas, 1)
    assert sel is not None and 2 <= len(sel) <= pl.MAX_PATAS
    assert len({o.match_id for o in sel}) == len(sel)
    assert pl.en_escalon(math.prod(o.price for o in sel), 1)


def test_dia_no_repite_partido_y_salta_escalon_imposible():
    patas = [_o(f"m{i}", 0.70, 1.40) for i in range(6)]       # 1,40^2=1,96 · 1,40^3=2,74 · 1,40^4=3,84
    dia = pl.armar_dia(patas)
    usados = [o.match_id for _, sel in dia for o in sel]
    assert len(usados) == len(set(usados))
    # Escalón 2 imposible con patas de 1,40 (1,96 o 2,74): se salta y el 3
    # sale con 3 partidos; el 4 pediría 4 y solo queda 1.
    assert [e for e, _ in dia] == [1, 3]


def test_dia_con_pocos_partidos():
    assert pl.armar_dia([]) == []
    assert pl.armar_dia([_o("a", 0.7, 1.4)]) == []            # una pata no es parlay
    assert [e for e, _ in pl.armar_dia([_o("a", 0.7, 1.4), _o("b", 0.7, 1.4)])] == [1]


def test_escalon_pausado_no_se_elige():
    patas = [_o(f"m{i}", 0.70, 1.40) for i in range(6)]
    assert 1 not in [e for e, _ in pl.armar_dia(patas, {1})]


def test_desempate_menos_patas_y_luego_match_id():
    a = [_o("b", 0.7, 1.4), _o("a", 0.7, 1.4), _o("c", 0.7, 1.4)]
    sel = pl.buscar(a, 1)
    assert [o.match_id for o in sel] == ["a", "b"]


def test_liquidacion():
    assert pl.liquidar([("win", 1.4, 0.7), (None, 1.4, 0.7)]) is None
    g = pl.liquidar([("win", 1.4, 0.7), ("win", 1.5, 0.6)])
    assert g["outcome"] == "ganado" and math.isclose(g["factor_pago"], 2.1, rel_tol=1e-6)
    assert math.isclose(g["prob_efectiva"], 0.42)
    p = pl.liquidar([("win", 1.4, 0.7), ("loss", 1.5, 0.6)])
    assert p["outcome"] == "perdido" and p["factor_pago"] == 0
    v = pl.liquidar([("win", 1.4, 0.7), ("void", 1.5, 0.6), ("push", 1.3, 0.7)])
    assert v["outcome"] == "ganado" and math.isclose(v["factor_pago"], 1.4) and math.isclose(v["prob_efectiva"], 0.7)
    n = pl.liquidar([("void", 1.4, 0.7), ("push", 1.5, 0.6)])
    assert n["outcome"] == "nulo" and n["factor_pago"] == 1.0


def _liq(escalon, prob, outcome, semana, factor=0.0):
    return {"escalon": escalon, "prob": prob, "outcome": outcome, "factor_pago": factor,
            "kickoff_utc": datetime(2026, 1, 5, tzinfo=timezone.utc) + timedelta(weeks=semana)}


def test_control_muestra_insuficiente_y_pausa_por_fallo_grosero():
    poco = [_liq(1, 0.5, "ganado", 0, 2.0)] * 10
    assert pl.control(poco)["pausados"] == []
    malo = [_liq(1, 0.5, "perdido", s % 12) for s in range(80)]
    assert pl.control(malo)["pausados"] == [1]
    assert pl.control([])["motivos"] == ["Sin parlays liquidados todavía"]


def test_resumen_unidades_y_nulos_fuera():
    filas = [_liq(1, 0.5, "ganado", 0, 2.0), _liq(1, 0.5, "perdido", 0),
             _liq(2, 0.4, "nulo", 0, 1.0)]
    r = pl.resumen(filas)
    b = r["por_escalon"]["1"]
    assert b["n"] == 2 and b["aciertos"] == 1 and b["unidades"] == 0.0 and b["roi"] == 0.0
    assert b["prob_media"] == 50.0 and b["acierto_real"] == 50.0
    assert r["total"]["n"] == 2 and "2" not in r["por_escalon"]


# --- Revisión final: borde con cuotas float4 y patas "dominadas" ---------------

def _f4(x):
    """La cuota tal como sale de una columna REAL de Postgres."""
    import struct
    return struct.unpack("f", struct.pack("f", x))[0]


def test_cuotas_float4_en_el_borde_caen_en_su_escalon():
    patas = pl.filtrar([_o("a", 0.62, _f4(1.25)),
                        _o("b", 0.55, _f4(1.76), market="h2h", sel="home", line=None)], AHORA)
    assert pl.buscar(patas, 1) is None                        # 1,25 × 1,76 = 2,20: no es del 1
    sel = pl.buscar(patas, 2)
    assert sel is not None and round(math.prod(o.price for o in sel), 6) == 2.2
    exacto = pl.filtrar([_o("a", 0.7, _f4(1.25)), _o("b", 0.7, _f4(1.52))], AHORA)
    assert pl.buscar(exacto, 1) is not None                   # 1,25 × 1,52 = 1,90: sí es del 1


def test_pata_menos_probable_y_mas_barata_sirve_para_no_pasarse_del_escalon():
    a = _o("m1", 0.80, 1.30)
    b = _o("m1", 0.75, 1.25, line=2.5)
    c = _o("m2", 0.55, 1.72, market="h2h", sel="home", line=None)
    sel = pl.buscar([a, b, c], 1)                             # A×C = 2,236 se pasa; B×C = 2,15
    assert sel is not None and sorted(o.cand.prob for o in sel) == [0.55, 0.75]
