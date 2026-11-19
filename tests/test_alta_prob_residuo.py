"""Medición del límite del ajuste de goles (eval/alta_prob_residuo.py): estadística por partido y criterio de decisión."""
import math

import numpy as np
import pandas as pd
import pytest

from qf.eval import alta_prob_residuo as ar
from qf.model.market_anchor import market_lambdas
from qf.publish import alta_prob as ap


def _frame(filas):
    return pd.DataFrame(filas, columns=["match", "liga", "residuo", "mercado", "prob", "won"])


def test_los_grupos_cortan_en_los_limites_del_protocolo():
    assert ar.grupo_de(0.0) == "A" and ar.grupo_de(0.010) == "A"
    assert ar.grupo_de(0.0100001) == "B" and ar.grupo_de(0.015) == "B"
    assert ar.grupo_de(0.0150001) == "C" and ar.grupo_de(0.020) == "C"
    assert ar.grupo_de(0.0200001) == "D" and ar.grupo_de(0.030) == "D"
    assert ar.grupo_de(0.0300001) == "E" and ar.grupo_de(0.9) == "E"


def test_brecha_con_un_solo_candidato_por_partido_es_la_diferencia_simple():
    g = _frame([(f"m{i}", "x", 0.02, "totals over 1.5", 0.8, i < 8) for i in range(10)])    # real 80 % frente a 80 %
    b = ar.brecha(g)
    assert b["n"] == 10 and b["partidos"] == 10 and b["brecha_pts"] == pytest.approx(0.0)
    g = _frame([(f"m{i}", "x", 0.02, "totals over 1.5", 0.8, i < 6) for i in range(10)])    # real 60 % frente a 80 %
    assert ar.brecha(g)["brecha_pts"] == pytest.approx(-20.0)


def test_el_error_estandar_por_partido_es_mayor_si_los_candidatos_de_un_partido_se_mueven_juntos():
    # Mismos 40 candidatos y misma brecha, pero en un caso son 40 partidos independientes y en el otro 4 partidos de 10 candidatos
    # que ganan o pierden todos a la vez.
    indep = _frame([(f"m{i}", "x", 0.02, "t", 0.5, i % 2 == 0) for i in range(40)])
    juntos = _frame([(f"m{i // 10}", "x", 0.02, "t", 0.5, (i // 10) % 2 == 0) for i in range(40)])
    assert ar.brecha(indep)["brecha_pts"] == pytest.approx(ar.brecha(juntos)["brecha_pts"])
    assert ar.brecha(juntos)["se_pts"] > 3 * ar.brecha(indep)["se_pts"]


def test_brecha_de_un_grupo_vacio_no_revienta():
    assert ar.brecha(_frame([]))["n"] == 0


def test_candidatos_dependientes_no_incluye_el_handicap_cero_ni_el_1x2():
    p = {"home": 0.42, "draw": 0.27, "away": 0.31}
    fit = market_lambdas(p["home"], p["draw"], p["away"], rho=-0.0347, totals={2.5: 0.52})
    dep = ar.candidatos_dependientes(p, {"lambda": fit.lam, "mu": fit.mu, "rho": -0.0347, "linea": 2.5, "residuo": fit.residual})
    marcas = {(c.market, c.selection, c.line) for c in dep}
    assert ("totals", "over", 1.5) in marcas and ("totals", "under", 3.5) in marcas
    assert not any(c.market in ("h2h", "double_chance") for c in dep)
    assert not any(c.market == "spreads" and c.line == 0.0 for c in dep)
    assert any(c.market == "spreads" and c.line == 1.0 for c in dep)


def _incremento(brecha_pts, partidos=400, por_partido=3, residuo=0.012, mercado="totals over 1.5"):
    """Candidatos de `partidos` partidos con residuo dado y una brecha media de `brecha_pts` puntos (prob 0,8)."""
    filas = []
    n = partidos * por_partido
    ganados = round(n * (0.8 + brecha_pts / 100))
    k = 0
    for i in range(partidos):
        for j in range(por_partido):
            filas.append((f"i{i}", "x", residuo, mercado, 0.8, k < ganados))
            k += 1
    return filas


def _base(partidos=600, por_partido=3):
    return _frame([(f"b{i}", "x", 0.005, "totals over 1.5", 0.8, (i * 3 + j) % 10 < 8)
                   for i in range(partidos) for j in range(por_partido)])


def test_un_incremento_bien_calibrado_se_acepta():
    c = pd.concat([_base(), _frame(_incremento(0.0))])
    ev = ar.evaluar_limite(c, 0.015)
    assert ev["cond1_brecha_conjunta"] and ev["cond3_no_peor_que_base"] and ev["partidos_suficientes"]
    assert ev["acepta"] is True


def test_un_incremento_con_deficit_se_rechaza_por_brecha_conjunta():
    c = pd.concat([_base(), _frame(_incremento(-4.0))])
    ev = ar.evaluar_limite(c, 0.015)
    assert ev["cond1_brecha_conjunta"] is False and ev["acepta"] is False


def test_un_incremento_pequeno_no_concluye():
    c = pd.concat([_base(), _frame(_incremento(0.0, partidos=100))])
    ev = ar.evaluar_limite(c, 0.015)
    assert ev["partidos_suficientes"] is False and ev["acepta"] is False


def test_la_decision_propone_el_mayor_limite_que_cumple_y_si_ninguno_mantiene_el_vigente():
    bueno = pd.concat([_base(), _frame(_incremento(0.0, residuo=0.012)), _frame(_incremento(0.0, residuo=0.018)),
                       _frame(_incremento(-6.0, residuo=0.025))])
    d = ar.decision(bueno)
    assert d["limite_propuesto"] == 0.020          # 0,03 mezcla un grupo con −6 puntos y falla; 0,02 sigue bien
    malo = pd.concat([_base(), _frame(_incremento(-6.0, residuo=0.012))])
    assert ar.decision(malo)["limite_propuesto"] == ar.BASE


def test_la_diferencia_contra_la_base_trae_un_intervalo_que_contiene_el_punto():
    c = pd.concat([_base(), _frame(_incremento(-1.0))])
    d = ar.diferencia_ic(c[c["residuo"] <= ar.BASE], c[c["residuo"] > ar.BASE])
    assert d["ic95"][0] <= d["diff_pts"] <= d["ic95"][1] and math.isfinite(d["diff_pts"])
