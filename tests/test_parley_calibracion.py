from datetime import datetime, timezone

import numpy as np
import pytest

from qf.eval import parley_calibracion as pc
from qf.publish import parley_v2 as v2
from qf.publish.alta_prob import Candidato
from qf.publish.escalera import Opcion

NOW = datetime(2026, 11, 6, tzinfo=timezone.utc)


def datos(n, sesgo_entreno=0.0, sesgo_test=0.0, semilla=1):
    rng = np.random.default_rng(semilla)
    fechas = np.datetime64("2024-01-01") + rng.integers(0, 600, n).astype("timedelta64[D]")
    p = rng.uniform(0.55, 0.80, n)
    corte = np.datetime64("2024-01-01") + np.timedelta64(480, "D")
    real = np.where(fechas < corte, p + sesgo_entreno, p + sesgo_test)
    return fechas, p, (rng.uniform(size=n) < np.clip(real, 0.01, 0.99)).astype(float)


def test_particion_60_20_20_con_embargo_y_sin_solapes():
    fechas = np.datetime64("2024-01-01") + np.arange(1000).astype("timedelta64[D]")
    tr, va, te = pc.particion_temporal(fechas, embargo_dias=7)
    assert not (set(tr) & set(va)) and not (set(va) & set(te)) and not (set(tr) & set(te))
    assert fechas[tr].max() < fechas[va].min() and fechas[va].max() < fechas[te].min()
    assert (fechas[va].min() - fechas[tr].max()) >= np.timedelta64(7, "D")
    assert (fechas[te].min() - fechas[va].max()) >= np.timedelta64(7, "D")
    assert abs(len(tr) / 1000 - 0.6) < 0.01 and abs(len(va) / 1000 - 0.2) < 0.03


def test_bandas_y_categoria():
    assert pc.banda(1.5) == "1.20-1.80" and pc.banda(1.80) == "1.80-2.10" and pc.banda(2.5) == "2.10-2.50"
    assert pc.banda(1.1) is None and pc.banda(2.6) is None
    assert pc.categoria("tenis", "total_games", 1.9) == "tenis|linea|1.80-2.10"


def test_mercado_bien_calibrado_queda_ok_y_se_queda_con_el_baseline():
    f, p, y = datos(9000)
    r = pc.ajustar_categoria(f, p, y, repeticiones=60)
    assert r["estado"] == "ok" and r["metricas_test"]["ece"] <= pc.ECE_MAX
    assert r["n"]["entreno"] >= 400 and "nodos" in r


def test_sesgo_estable_se_corrige_y_la_mejora_tiene_ic_positivo():
    f, p, y = datos(12000, sesgo_entreno=-0.10, sesgo_test=-0.10)
    r = pc.ajustar_categoria(f, p, y, repeticiones=60)
    assert r["estado"] == "ok" and r["metodo"] in ("platt", "isotonica")
    assert r["mejora_brier_ic95"][1] > 0
    assert r["metricas_test"]["brier"] < r["metricas_test_mercado"]["brier"]


def test_cambio_de_regimen_en_el_test_provoca_abstencion():
    f, p, y = datos(12000, sesgo_entreno=0.0, sesgo_test=-0.20)
    r = pc.ajustar_categoria(f, p, y, repeticiones=30)
    assert r["estado"] == "abstencion" and "ECE" in r["motivo"]


def test_muestra_insuficiente_se_abstiene():
    f, p, y = datos(500)
    assert pc.ajustar_categoria(f, p, y)["motivo"] == "muestra insuficiente"


def _registros(n=9000, mercado="h2h", deporte="futbol"):
    f, p, y = datos(n)
    return [dict(fecha=a, deporte=deporte, mercado=mercado, cuota=1.5, p=float(b), gana=float(c)) for a, b, c in zip(f, p, y)]


def test_artefacto_calibrador_y_filtro_de_abstencion(tmp_path):
    art = pc.construir_artefacto(_registros())
    assert art["aprobado"] is False and art["categorias"]["futbol|ganador|1.20-1.80"]["estado"] == "ok"
    ruta = tmp_path / "a.json"
    import json
    ruta.write_text(json.dumps(art), encoding="utf-8")
    cal = pc.Calibrador.desde_archivo(ruta)
    c = cal.calibrar("futbol", "h2h", 1.5, 0.7)
    assert c is not None and 0 < c.p_bajo <= c.p_prudente <= c.p_alto < 1
    assert cal.calibrar("futbol", "h2h", 2.9, 0.7) is None            # fuera de bandas
    assert cal.calibrar("tenis", "h2h", 1.5, 0.7) is None              # sin artefacto del deporte
    op = lambda m, price: Opcion(m, Candidato("h2h", "home", None, 0.7), price, "b", "t", NOW)
    ops = [op("a", 1.5), op("b", 1.5), op("c", 2.9)]
    mapa = cal.para_opciones(ops)
    assert [o.match_id for o in pc.filtrar_calibradas(ops, mapa)] == ["a", "b"]


def test_el_selector_publica_solo_con_patas_calibradas():
    art = pc.construir_artefacto(_registros())
    cal = pc.Calibrador(art)
    ops = [Opcion("a", Candidato("h2h", "home", None, 0.7), 1.40, "b", "t", NOW),
           Opcion("b", Candidato("h2h", "home", None, 0.7), 1.50, "b", "t", NOW)]
    plan = v2.armar_plan(ops, calibracion=cal.para_opciones(ops))
    assert plan.tickets[0].estado == "publicado" and plan.tickets[0].p_bajo < plan.tickets[0].probability
