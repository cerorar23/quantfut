"""/app/v1/meta/dispositivo y campos nuevos de /me, sin BD."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import cuentas as api, meta
from qf.comercial import meta_datos, suscripciones

ACC = {"account_id": 7, "email": "a@b.com", "display_name": None, "status": "active",
       "email_verified_at": None, "created_at": "2026-10-07T00:00:00Z",
       "store_account_token": "0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c"}
EXT = ["a2", "com.saptain.quantfut", "1.0.0", "1", "14", "Pixel 8", "es_CO", "COT", "", "1080",
       "2400", "2.75", "8", "", "", "America/Bogota"]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    app = FastAPI()
    app.include_router(api.router)
    app.include_router(meta.router)
    app.dependency_overrides[api.current_account] = lambda: dict(ACC)
    monkeypatch.setattr(suscripciones, "active_subscription", lambda _id: None)
    return TestClient(app)


def test_me_entrega_token_de_tienda_e_id_externo(client):
    body = client.get("/app/v1/me").json()
    assert body["store_account_token"] == ACC["store_account_token"]
    assert body["meta_external_id"] == meta_datos.external_id(7)


def test_dispositivo_guarda_ip_y_user_agent_de_la_peticion(monkeypatch, client):
    saved = {}
    monkeypatch.setattr(meta, "_save", lambda **kw: saved.update(kw))
    r = client.post("/app/v1/meta/dispositivo",
                    headers={"user-agent": "QuantFut/1.0 (Android; Flutter)",
                             "x-forwarded-for": "203.0.113.9"},
                    json={"anon_id": "XZ1-abc", "platform": "android", "madid": None,
                          "advertiser_tracking_enabled": True, "extinfo": EXT})
    assert r.status_code == 204
    assert saved["account_id"] == 7 and saved["anon_id"] == "XZ1-abc"
    assert saved["user_agent"] == "QuantFut/1.0 (Android; Flutter)"
    assert saved["client_ip"] == "203.0.113.9"
    assert saved["extinfo"] == EXT


def test_dispositivo_rechaza_extinfo_de_otra_plataforma(monkeypatch, client):
    monkeypatch.setattr(meta, "_save", lambda **kw: None)
    r = client.post("/app/v1/meta/dispositivo",
                    json={"anon_id": "XZ1", "platform": "ios", "madid": None,
                          "advertiser_tracking_enabled": False, "extinfo": EXT})
    assert r.status_code == 422


def test_dispositivo_rechaza_madid_que_no_es_uuid(monkeypatch, client):
    monkeypatch.setattr(meta, "_save", lambda **kw: None)
    r = client.post("/app/v1/meta/dispositivo",
                    json={"anon_id": "XZ1", "platform": "android", "madid": "no-es-uuid",
                          "advertiser_tracking_enabled": True, "extinfo": EXT})
    assert r.status_code == 422
