"""
La cuota justa de un over con push no es 1/P(over). En gol entero el push
devuelve la apuesta; en cuarto de gol la apuesta se reparte entre las dos
líneas vecinas. Pinnacle cotiza así dos de cada tres partidos.
"""
import pytest

from qf.model.market_anchor import market_lambdas
from qf.model.pricing import market_1x2, market_totals, score_matrix, totals_fair_over

M = score_matrix(1.6, 1.1, -0.06)


def _p_total(k):
    n = M.shape[0]
    return float(sum(M[i, k - i] for i in range(max(0, k - n + 1), min(k, n - 1) + 1)))


def test_medio_gol_es_p_over():
    assert totals_fair_over(M, 2.5) == pytest.approx(market_totals(M, 2.5)["over"], abs=1e-12)


def test_gol_entero_excluye_el_push():
    t = market_totals(M, 3.0)
    assert totals_fair_over(M, 3.0) == pytest.approx(t["over"] / (t["over"] + t["under"]), abs=1e-12)


def test_cuarto_de_gol_reparte_entre_vecinas():
    p3 = _p_total(3)
    p4_mas = market_totals(M, 3.5)["over"]
    assert totals_fair_over(M, 2.75) == pytest.approx((p4_mas + 0.5 * p3) / (1 - 0.5 * p3), abs=1e-12)
    assert totals_fair_over(M, 3.25) == pytest.approx(p4_mas / (1 - 0.5 * p3), abs=1e-12)


@pytest.mark.parametrize("line", [2.25, 2.75, 3.0, 3.25])
def test_a_cuota_justa_el_valor_esperado_es_cero(line):
    cuota = 1 / totals_fair_over(M, line)
    partes = (line - 0.25, line + 0.25) if round(line * 4) % 2 else (line, line)
    n = M.shape[0]
    ev = 0.0
    for i in range(n):
        for j in range(n):
            tot = i + j
            retorno = sum(0.5 * (cuota if tot > c else 1.0 if tot == c else 0.0) for c in partes)
            ev += M[i, j] * retorno
    assert ev == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("line", [2.5, 2.75, 3.0])
def test_el_ajuste_recupera_las_lambdas_con_cualquier_linea(line):
    p = market_1x2(M)
    fit = market_lambdas(p["home"], p["draw"], p["away"], rho=-0.06,
                         totals={line: totals_fair_over(M, line)})
    assert fit.lam == pytest.approx(1.6, abs=2e-3)
    assert fit.mu == pytest.approx(1.1, abs=2e-3)
    assert fit.residual < 1e-3
