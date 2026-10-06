"""La línea de alta probabilidad entra en el lote sellado y nunca rompe el job."""
from dataclasses import replace
from datetime import date

import pytest

from qf.config import settings
from qf.publish import daily, hashchain


def _collect(monkeypatch, dia, desde):
    sqls = []
    monkeypatch.setattr(hashchain, "LOTE_ALTA_PROB_DESDE", desde)
    monkeypatch.setattr(hashchain, "query",
                        lambda sql, params=None: sqls.append(sql) or
                        ([{"alta_id": "a1"}] if "alta_prob_picks" in sql else []))
    return hashchain._collect(dia), sqls


def test_sin_fecha_de_corte_no_hay_bloque(monkeypatch):
    payload, sqls = _collect(monkeypatch, date(2026, 10, 7), None)
    assert "alta_probabilidad" not in payload
    assert not any("alta_prob_picks" in s for s in sqls)


def test_lotes_anteriores_al_corte_no_cambian(monkeypatch):
    payload, _ = _collect(monkeypatch, date(2026, 10, 6), date(2026, 10, 7))
    assert "alta_probabilidad" not in payload


def test_desde_el_corte_va_el_bloque(monkeypatch):
    payload, sqls = _collect(monkeypatch, date(2026, 10, 7), date(2026, 10, 7))
    assert payload["alta_probabilidad"] == [{"alta_id": "a1"}]
    assert payload["n_alta_prob"] == 1


@pytest.fixture
def job(monkeypatch):
    orden = []
    monkeypatch.setattr(daily, "generate_predictions",
                        lambda: [{"match_id": "m1", "confidence_tier": "high", "teams": ("A", "B")}])
    monkeypatch.setattr(daily, "_sharp_only_upcoming", lambda hours=36: [])
    monkeypatch.setattr(daily, "seal", lambda: orden.append("seal") or {"chain_sha256": "ab" * 32})
    monkeypatch.setattr(daily.alta_prob_datos, "select_and_persist",
                        lambda: orden.append("alta") or {"elegidos": 2, "estado": "activa", "motivos": []})
    alerts = []
    monkeypatch.setattr(daily.tg, "alert", alerts.append)
    return orden, alerts


def test_alta_se_elige_antes_de_sellar(monkeypatch, job):
    orden, _ = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=True))
    out = daily.run()
    assert orden == ["alta", "seal"]
    assert out["alta_prob"]["elegidos"] == 2


def test_apagada_no_se_llama(monkeypatch, job):
    orden, _ = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=False))
    daily.run()
    assert orden == ["seal"]


def test_un_fallo_de_la_linea_no_impide_sellar(monkeypatch, job):
    orden, alerts = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=True))

    def roto():
        raise RuntimeError("snapshot corrupto")
    monkeypatch.setattr(daily.alta_prob_datos, "select_and_persist", roto)
    out = daily.run()
    assert orden == ["seal"] and out["sealed"] is True
    assert any("alta probabilidad" in a.lower() for a in alerts)


def test_elegidos_sin_sellar_avisan(monkeypatch, job):
    orden, alerts = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=True))
    monkeypatch.setattr(daily, "seal", lambda: orden.append("seal") or {})
    daily.run()
    assert any("SIN SELLAR" in a for a in alerts)


def test_lote_lleva_alta_es_la_unica_fuente_de_verdad(monkeypatch):
    corte = date(2026, 10, 7)
    monkeypatch.setattr(hashchain, "LOTE_ALTA_PROB_DESDE", None)
    assert hashchain.lote_lleva_alta(date(2026, 10, 7)) is False
    assert hashchain.lote_lleva_alta(date(2030, 1, 1)) is False
    monkeypatch.setattr(hashchain, "LOTE_ALTA_PROB_DESDE", corte)
    assert hashchain.lote_lleva_alta(date(2026, 10, 6)) is False   # antes
    assert hashchain.lote_lleva_alta(corte) is True                # el mismo día
    assert hashchain.lote_lleva_alta(date(2026, 10, 8)) is True    # después


def test_sin_corte_se_sella_igual_y_avisa(monkeypatch, job):
    orden, alerts = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=True))
    monkeypatch.setattr(daily.alta_prob_datos, "select_and_persist",
                        lambda: orden.append("alta") or
                        {"elegidos": 0, "estado": "sin_corte",
                         "motivos": ["El lote de hoy no lleva bloque de alta probabilidad"]})
    out = daily.run()
    assert orden == ["alta", "seal"] and out["sealed"] is True
    assert out["alta_prob"]["estado"] == "sin_corte"
    assert any("ALTA PROBABILIDAD" in a for a in alerts)
