"""Parseo de respuestas verificadas de Google Play y App Store (sin red)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from qf.comercial.tiendas import TiendaError, app_store, google_play

PLAY = json.loads((Path(__file__).parent / "fixtures" / "play_subscription_v2.json").read_text("utf-8"))


def test_play_activa_se_convierte_en_cobro_con_micros_exactos():
    c = google_play.parse("tok-1", PLAY)
    assert (c.store, c.order_id, c.original_id) == ("google_play", "GPA.3345-1234-5678-90123", "tok-1")
    assert c.account_token == "0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c"
    assert (c.product_id, c.base_plan_id) == ("quantfut_plus", "plus-1m")
    assert c.period_end == datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
    assert (c.price_micros, c.currency, c.region_code) == (54_900_000_000, "COP", "CO")
    assert (c.environment, c.state) == ("production", "activa")


def test_play_compra_de_prueba_es_sandbox():
    c = google_play.parse("tok-1", {**PLAY, "testPurchase": {}})
    assert c.environment == "sandbox"


@pytest.mark.parametrize("estado,esperado", [
    ("SUBSCRIPTION_STATE_CANCELED", "activa"),          # cancelada: dura hasta expiryTime
    ("SUBSCRIPTION_STATE_IN_GRACE_PERIOD", "activa"),
    ("SUBSCRIPTION_STATE_PENDING", "pendiente"),
    ("SUBSCRIPTION_STATE_ON_HOLD", "sin_acceso"),
    ("SUBSCRIPTION_STATE_EXPIRED", "sin_acceso"),
])
def test_play_estados(estado, esperado):
    assert google_play.parse("tok-1", {**PLAY, "subscriptionState": estado}).state == esperado


def test_play_push_sin_token_se_rechaza(monkeypatch):
    monkeypatch.setenv("PLAY_RTDN_AUDIENCE", "https://x/app/v1/compras/google/rtdn")
    with pytest.raises(TiendaError):
        google_play.verify_push(None)


def _apple_tx(**kw):
    base = dict(transactionId="2000000123", originalTransactionId="2000000100",
                productId="quantfut_plus_3m", purchaseDate=1760529600000, expiresDate=1768305600000,
                appAccountToken="0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c", price=19990, currency="USD",
                environment=SimpleNamespace(value="Production"), revocationDate=None)
    return SimpleNamespace(**{**base, **kw})


def test_apple_transaccion_se_convierte_en_cobro():
    c = app_store.parse(_apple_tx())
    assert (c.store, c.order_id, c.original_id) == ("app_store", "2000000123", "2000000100")
    assert c.period_start == datetime(2025, 10, 15, 12, tzinfo=timezone.utc)
    assert c.period_end == datetime(2026, 1, 13, 12, tzinfo=timezone.utc)
    assert c.price_micros == 19_990_000 and c.currency == "USD"
    assert c.environment == "production" and c.state == "activa"


def test_apple_revocada_no_da_acceso():
    assert app_store.parse(_apple_tx(revocationDate=1760600000000)).state == "sin_acceso"


def test_apple_sandbox():
    assert app_store.parse(_apple_tx(environment=SimpleNamespace(value="Sandbox"))).environment == "sandbox"
