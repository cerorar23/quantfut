"""Endpoints de compras con la tienda y la BD simuladas."""
import base64
import json
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import compras as api_compras, cuentas as api
from qf.comercial import suscripciones
from qf.comercial.tiendas import Cobro, TiendaError, app_store, compras, google_play
from test_cuentas_api import FakeRedis

ACC = {"account_id": 7, "email": "a@b.com", "display_name": None, "status": "active",
       "email_verified_at": None, "created_at": "2026-10-07T00:00:00Z",
       "store_account_token": "0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c"}
END = datetime(2026, 11, 15, tzinfo=timezone.utc)
COBRO = Cobro("google_play", "GPA.1", "tok", ACC["store_account_token"], "quantfut_plus", "plus-1m",
              datetime(2026, 10, 15, tzinfo=timezone.utc), END, 4_990_000, "USD", "US",
              "production", "activa", {"acknowledgementState": "ACKNOWLEDGEMENT_STATE_PENDING"})


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    monkeypatch.setenv("STORE_PURCHASES_ENABLED", "1")
    monkeypatch.setattr(api, "_redis", FakeRedis())   # el límite por IP usa Redis
    app = FastAPI()
    app.include_router(api_compras.router)
    app.include_router(api_compras.store_router)
    app.dependency_overrides[api.current_account] = lambda: dict(ACC)
    monkeypatch.setattr(suscripciones, "active_subscription", lambda _id: {"plan_code": "plus_1m"})
    return TestClient(app)


def test_apagado_devuelve_503(monkeypatch, client):
    monkeypatch.setenv("STORE_PURCHASES_ENABLED", "0")
    r = client.post("/app/v1/compras/verificar",
                    json={"store": "google_play", "product_id": "quantfut_plus", "purchase_token": "tok"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "compras_deshabilitadas"


def test_verificar_play_concede_y_reconoce(monkeypatch, client):
    acks = []
    monkeypatch.setattr(google_play, "fetch", lambda tok: COBRO.payload)
    monkeypatch.setattr(google_play, "parse", lambda tok, data: COBRO)
    monkeypatch.setattr(google_play, "acknowledge", lambda pid, tok: acks.append((pid, tok)))
    monkeypatch.setattr(compras, "aplicar",
                        lambda c, acc: {"estado": "concedido", "ends_at": END, "account_id": acc})
    r = client.post("/app/v1/compras/verificar",
                    json={"store": "google_play", "product_id": "quantfut_plus", "purchase_token": "tok"})
    assert r.status_code == 200
    assert r.json()["estado"] == "concedido" and r.json()["plus"] is True
    assert acks == [("quantfut_plus", "tok")]


def test_compra_de_otra_cuenta_devuelve_409_con_codigo(monkeypatch, client):
    monkeypatch.setattr(app_store, "verify_transaction", lambda jws: COBRO)

    def boom(c, acc):
        raise TiendaError("compra_de_otra_cuenta", "Esta compra pertenece a otra cuenta")

    monkeypatch.setattr(compras, "aplicar", boom)
    r = client.post("/app/v1/compras/verificar",
                    json={"store": "app_store", "product_id": "quantfut_plus_1m", "jws": "x.y.z"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "compra_de_otra_cuenta"


def test_tienda_caida_devuelve_503(monkeypatch, client):
    def caida(tok):
        raise ConnectionError("timeout")

    monkeypatch.setattr(google_play, "fetch", caida)
    r = client.post("/app/v1/compras/verificar",
                    json={"store": "google_play", "product_id": "quantfut_plus", "purchase_token": "tok"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "tienda_no_disponible"


def _push(payload):
    return {"message": {"data": base64.b64encode(json.dumps(payload).encode()).decode(),
                        "messageId": "1"}, "subscription": "projects/p/subscriptions/s"}


def test_rtdn_renovacion_vuelve_a_consultar_a_la_tienda(monkeypatch, client):
    applied = []
    monkeypatch.setattr(google_play, "verify_push", lambda auth: None)
    monkeypatch.setattr(google_play, "fetch", lambda tok: COBRO.payload)
    monkeypatch.setattr(google_play, "parse", lambda tok, data: COBRO)
    monkeypatch.setattr(google_play, "acknowledge", lambda pid, tok: None)
    monkeypatch.setattr(compras, "aplicar",
                        lambda c, acc: applied.append(acc) or {"estado": "concedido", "ends_at": END,
                                                               "account_id": 7})
    r = client.post("/app/v1/compras/google/rtdn", headers={"authorization": "Bearer t"},
                    json=_push({"packageName": "com.saptain.quantfut",
                                "subscriptionNotification": {"notificationType": 2,
                                                             "purchaseToken": "tok",
                                                             "subscriptionId": "quantfut_plus"}}))
    assert r.status_code == 204 and applied == [None]


def test_rtdn_reembolso_revoca_la_orden(monkeypatch, client):
    revoked = []
    monkeypatch.setattr(google_play, "verify_push", lambda auth: None)
    monkeypatch.setattr(compras, "revocar_orden", lambda s, o, m: revoked.append((s, o)) or True)
    r = client.post("/app/v1/compras/google/rtdn", headers={"authorization": "Bearer t"},
                    json=_push({"voidedPurchaseNotification": {"purchaseToken": "tok",
                                                               "orderId": "GPA.9"}}))
    assert r.status_code == 204 and revoked == [("google_play", "GPA.9")]


def test_rtdn_sin_autenticar_devuelve_401(monkeypatch, client):
    r = client.post("/app/v1/compras/google/rtdn", json=_push({"testNotification": {}}))
    assert r.status_code == 401


def test_apple_reembolso_revoca(monkeypatch, client):
    revoked = []
    monkeypatch.setattr(app_store, "verify_notification", lambda sp: ("REFUND", None, "2000000123"))
    monkeypatch.setattr(compras, "revocar_orden", lambda s, o, m: revoked.append((s, o)) or True)
    r = client.post("/app/v1/compras/apple/notificaciones", json={"signedPayload": "x.y.z"})
    assert r.status_code == 204 and revoked == [("app_store", "2000000123")]
