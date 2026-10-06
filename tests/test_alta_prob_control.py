"""Control de calidad e historial de la línea de alta probabilidad."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from qf.eval import soft_vs_sharp as svs
from qf.publish import alta_prob as ap

T0 = datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc)


def _filas(n, prob, tasa, market="double_chance", semanas=10, ref=None):
    aciertos = round(n * tasa)
    return [{"market": market, "prob": prob, "ref_price": ref,
             "outcome": "win" if i < aciertos else "loss",
             "kickoff_utc": T0 + timedelta(weeks=i % semanas)}
            for i in range(n)]


def test_sin_muestra_no_bloquea():
    assert ap.control([])["bloqueados"] == []
    assert ap.control(_filas(40, 0.87, 0.5))["bloqueados"] == []


def test_promete_de_mas_bloquea_todo_y_su_mercado():
    out = ap.control(_filas(120, 0.87, 0.60))
    assert "todo" in out["bloqueados"] and "double_chance" in out["bloqueados"]


def test_cumpliendo_no_bloquea():
    assert ap.control(_filas(300, 0.87, 0.87))["bloqueados"] == []


def test_calibrada_con_doce_semanas_no_bloquea():
    out = ap.control(_filas(300, 0.87, 0.87, semanas=12))
    assert out["bloqueados"] == []
    assert not any("grosero" in m or "IC99" in m for m in out["motivos"])


def test_solo_el_mercado_que_falla():
    # El conjunto cumple (z ≈ 0) y los goles fallan a lo grande (z ≈ −7): la
    # red de fallo grosero bloquea solo ese mercado.
    filas = _filas(400, 0.87, 0.92) + _filas(60, 0.86, 0.55, market="totals")
    out = ap.control(filas)
    assert out["bloqueados"] == ["totals"]
    assert any(m.startswith("totals: fallo grosero") for m in out["motivos"])


def _z(filas):
    """z = Σ(acertado − prob) / sqrt(Σ prob·(1 − prob)), a mano, sin tocar `ap`."""
    dif = sum((f["outcome"] == "win") - f["prob"] for f in filas)
    return dif / np.sqrt(sum(f["prob"] * (1 - f["prob"]) for f in filas))


def test_deficit_moderado_con_pocas_semanas_no_bloquea():
    # 120 pronósticos prometiendo 0,87 que aciertan 0,80: z ≈ −2,3, no es un
    # fallo grosero; y con 9 semanas el IC todavía no puede pausar (hacen falta 10).
    filas = _filas(120, 0.87, 0.80, semanas=9)
    assert _z(filas) > ap.Z_GROSERO
    out = ap.control(filas)
    assert out["bloqueados"] == []
    assert any("menos de 10 semanas" in m for m in out["motivos"])


def test_fallo_grosero_bloquea_aunque_haya_pocas_semanas():
    filas = _filas(120, 0.87, 0.40, semanas=3)
    assert _z(filas) <= ap.Z_GROSERO
    out = ap.control(filas)
    assert "todo" in out["bloqueados"] and "double_chance" in out["bloqueados"]
    assert any("fallo grosero" in m and "z -" in m for m in out["motivos"])


def test_fallo_grosero_exige_la_muestra_minima():
    filas = _filas(40, 0.87, 0.10, semanas=3)
    assert _z(filas) <= ap.Z_GROSERO
    assert ap.control(filas)["bloqueados"] == []


def test_deficit_claro_con_diez_semanas_bloquea_por_ic99():
    # 300 al 0,87 que aciertan 0,80: z ≈ −3,6 (no es grosero) pero el IC99 por
    # semanas queda entero bajo cero. Con 9 semanas no; con 10 sí.
    nueve = _filas(300, 0.87, 0.80, semanas=9)
    diez = _filas(300, 0.87, 0.80, semanas=10)
    assert _z(diez) > ap.Z_GROSERO
    assert ap.control(nueve)["bloqueados"] == []
    out = ap.control(diez)
    assert "todo" in out["bloqueados"]
    assert any("IC99" in m for m in out["motivos"])


def test_el_nivel_del_ic_se_puede_elegir_y_el_defecto_no_cambia():
    valores = np.array([(-1.0) ** i * 0.1 + 0.02 for i in range(120)])
    semanas = np.array([f"s{i % 12}" for i in range(120)])
    ic95 = svs._weekly_ci(valores, semanas)
    assert svs._weekly_ci(valores, semanas, level=0.95) == ic95
    ic99 = svs._weekly_ci(valores, semanas, level=0.99)
    assert ic99[0] <= ic95[0] and ic99[1] >= ic95[1] and ic99 != ic95


def test_historial():
    filas = _filas(20, 0.85, 0.90, ref=1.20) + _filas(10, 0.90, 0.80, market="h2h")
    h = ap.historial(filas)
    assert h["n"] == 30 and h["aciertos"] == 26
    assert h["acierto_prometido"] == pytest.approx(86.7, abs=0.05)
    assert h["acierto_real"] == pytest.approx(86.7, abs=0.05)
    assert h["por_mercado"]["h2h"]["n"] == 10
    assert h["rendimiento_ref"]["n"] == 20
    assert h["rendimiento_ref"]["roi"] == pytest.approx((18 * 0.2 - 2) / 20 * 100)
    assert h["diferencia_ic95"] is not None


def test_historial_vacio():
    h = ap.historial([])
    assert h["n"] == 0 and h["acierto_real"] is None and h["por_mercado"] == {}
