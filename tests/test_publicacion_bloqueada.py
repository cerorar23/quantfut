"""
Con PUBLISH_PICKS_ENABLED apagado, el job diario predice y sella, pero no
selecciona, guarda ni difunde picks. Un pick sellado es permanente, y el
criterio de selección actual está medido como anti-señal.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from qf.config import settings
from qf.publish import daily


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
