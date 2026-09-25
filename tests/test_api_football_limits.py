"""
Límites del plan de API-Football.

Los tres fallos que este módulo protege no dan error de código: se manifiestan
como cuota agotada a media mañana y feed en silencio.

  1. El intervalo entre llamadas se fijaba a 0,35 s (~170 req/min), que está
     por debajo de los planes de pago pero muy por encima del Free, que son
     10 req/min. Cuatro llamadas seguidas bastaban para empezar a recibir 429.
  2. Un 429 entraba en el reintento exponencial genérico, que reintenta
     enseguida y vuelve a chocar contra el mismo límite por minuto.
  3. Un error de PLAN ("esta temporada no está en tu suscripción") es
     permanente, y sin embargo se reintentaba cuatro veces. Cada reintento
     consume una petición de las 100 del día.
"""
from __future__ import annotations

import types

import httpx
import pytest
from tenacity import stop_after_attempt

from qf.ingest import api_football as af


def test_intervalo_derivado_del_plan():
    """10 req/min => 6 s entre llamadas, no 0,35."""
    assert af.MIN_INTERVAL == pytest.approx(60.0 / af.settings.api_football_rpm)
    assert af.settings.api_football_rpm <= 10 or af.MIN_INTERVAL < 6.0


def test_error_de_plan_no_se_reintenta(monkeypatch):
    llamadas = {"n": 0}

    class _Resp:
        status_code = 200
        headers: dict = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {"errors": {"plan": "Free plans do not have access to this season"},
                    "results": 0, "response": []}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            llamadas["n"] += 1
            return _Resp()

    monkeypatch.setattr(af, "settings", types.SimpleNamespace(api_football_key="x"))
    monkeypatch.setattr(af, "MIN_INTERVAL", 0.0)
    monkeypatch.setattr(httpx, "Client", _Client)

    with pytest.raises(af.PlanError):
        af.get("fixtures", {"league": 39, "season": 2026})

    assert llamadas["n"] == 1, "un error de plan es permanente: reintentarlo quema cuota"


def test_rate_limit_en_cuerpo_200_espera_un_minuto(monkeypatch):
    """El límite por minuto llega como HTTP 200 con `errors.rateLimit`.

    A diferencia del error de plan, este SÍ se reintenta: se resuelve solo al
    cambiar de minuto. Lo que no puede hacer es reintentar de inmediato.
    """
    class _Resp:
        status_code = 200
        headers: dict = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {"errors": {"rateLimit": "Too many requests. Your rate limit is 10 "
                                            "requests per minute."},
                    "results": 0, "response": []}

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            return _Resp()

    esperas: list[float] = []
    monkeypatch.setattr(af, "settings", types.SimpleNamespace(api_football_key="x"))
    monkeypatch.setattr(af, "MIN_INTERVAL", 0.0)
    monkeypatch.setattr(af.time, "sleep", esperas.append)
    monkeypatch.setattr(httpx, "Client", _Client)

    with pytest.raises(Exception) as exc:
        af.get.retry_with(stop=stop_after_attempt(1))("status")
    assert isinstance(exc.value.last_attempt.exception(), af.RateLimited)
    assert esperas == [60], "un 429 por minuto exige esperar al minuto siguiente"
