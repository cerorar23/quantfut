"""
Con PUBLISH_PICKS_ENABLED apagado, el job diario predice y sella, pero no
selecciona, guarda ni difunde picks. Un pick sellado es permanente, y el
criterio de selección actual está medido como anti-señal.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from qf.config import settings
from qf.publish import daily, hashchain


@pytest.fixture(autouse=True)
def _sin_sello_por_partido(monkeypatch):
    """El corte del sello por partido depende de la fecha de hoy: estas pruebas miran el job diario sin él."""
    monkeypatch.setattr(hashchain, "LOTE_POR_PARTIDO_DESDE", None)


def _no_llamar(*_a, **_k):
    raise AssertionError("no debería llamarse con la publicación de picks apagada")


@pytest.fixture
def sellados(monkeypatch):
    llamadas = []
    monkeypatch.setattr(daily, "generate_predictions",
                        lambda: [{"match_id": "m1", "confidence_tier": "high",
                                  "teams": ("A", "B")}])
    monkeypatch.setattr(daily, "_sharp_only_upcoming", lambda hours=36: [])
    monkeypatch.setattr(daily, "seal",
                        lambda: llamadas.append(1) or {"chain_sha256": "ab" * 32})
    monkeypatch.setattr(daily.pk, "select_daily", _no_llamar)
    monkeypatch.setattr(daily.pk, "persist", _no_llamar)
    monkeypatch.setattr(daily.tg, "publish_batch", _no_llamar)
    return llamadas


def test_apagado_por_defecto():
    assert settings.publish_picks_enabled is False


def test_apagado_sella_predicciones_sin_tocar_picks(monkeypatch, sellados):
    monkeypatch.setattr(daily, "settings", replace(settings, publish_picks_enabled=False))
    out = daily.run()
    assert sellados == [1]
    assert out["picks"] == 0
    assert out["picks_publishing"] == "disabled"
    assert out["sealed"] is True


def test_encendido_si_selecciona(monkeypatch, sellados):
    monkeypatch.setattr(daily, "settings", replace(settings, publish_picks_enabled=True))
    monkeypatch.setattr(daily, "_shadow_gate_allows_publication", lambda: (True, []))
    monkeypatch.setattr(daily, "_active_artifact", lambda: ("x.pkl", "v"))
    monkeypatch.setattr(daily.DixonColes, "load", staticmethod(lambda _p: None))
    with pytest.raises(AssertionError, match="no debería llamarse"):
        daily.run()


def test_interruptor_encendido_no_salta_puerta_cerrada(monkeypatch, sellados):
    monkeypatch.setattr(daily, "settings", replace(settings, publish_picks_enabled=True))
    monkeypatch.setattr(daily, "_shadow_gate_allows_publication",
                        lambda: (False, ["Muestra insuficiente"]))
    alerts = []
    monkeypatch.setattr(daily.tg, "alert", alerts.append)
    out = daily.run()
    assert sellados == [1]
    assert out["picks"] == 0 and out["picks_publishing"] == "gate_blocked"
    assert out["gate_reasons"] == ["Muestra insuficiente"]
    assert len(alerts) == 1


def test_error_al_leer_puerta_falla_cerrado(monkeypatch):
    from qf.publish import shadow_sharp

    def unavailable():
        raise RuntimeError("Base de datos temporalmente no disponible")

    monkeypatch.setattr(shadow_sharp, "report", unavailable)
    allowed, reasons = daily._shadow_gate_allows_publication()
    assert allowed is False
    assert reasons == ["Puerta de CLV no disponible"]


def test_con_el_sello_por_partido_activo_el_diario_no_crea_picks(monkeypatch, sellados):
    """Los picks de valor nacen en la predicción final de cada partido: el lote diario no los selecciona."""
    from datetime import date
    monkeypatch.setattr(hashchain, "LOTE_POR_PARTIDO_DESDE", date(2000, 1, 1))
    monkeypatch.setattr(daily, "settings", replace(settings, publish_picks_enabled=True))
    monkeypatch.setattr(daily, "_shadow_gate_allows_publication", lambda: (True, []))
    out = daily.run()                 # select_daily / persist / publish_batch fallarían si se llamaran
    assert sellados == [1]
    assert out["picks"] == 0 and out["gate_reasons"] == ["los picks de valor se sellan por partido (sello_tardio)"]
