"""Cobro web con Whop: firma, rutas y Conversions API web. Las pruebas con base real
(`QF_TEST_PG_DSN`, esquema aislado con db/*.sql) están al final."""
import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import whop as api
from qf.comercial import meta_capi, whop

SECRET = "ws_secreto_de_prueba"


def sign(body: bytes, msg_id="msg_1", stamp=None, secret=SECRET) -> dict:
    stamp = str(stamp if stamp is not None else int(time.time()))
    mac = hmac.new(secret.encode(), f"{msg_id}.{stamp}.".encode() + body, hashlib.sha256).digest()
    return {"webhook-id": msg_id, "webhook-timestamp": stamp,
            "webhook-signature": "v1," + base64.b64encode(mac).decode()}


def test_firma_valida_y_rechazos():
    body = b'{"type":"payment.succeeded"}'
    whop.verify_signature(SECRET, sign(body), body)
    with pytest.raises(whop.WhopError) as e:
        whop.verify_signature(SECRET, sign(body), body + b" ")
    assert e.value.code == "firma_invalida"
    with pytest.raises(whop.WhopError) as e:
        whop.verify_signature(SECRET, sign(body, secret="otro"), body)
    assert e.value.code == "firma_invalida"
    with pytest.raises(whop.WhopError) as e:
        whop.verify_signature(SECRET, sign(body, stamp=int(time.time()) - 301), body)
    assert e.value.code == "firma_caducada"
    with pytest.raises(whop.WhopError) as e:
        whop.verify_signature(SECRET, {}, body)
    assert e.value.code == "firma_ausente"


def test_firma_acepta_varias_firmas_en_la_cabecera():
    body = b"{}"
    h = sign(body)
    h["webhook-signature"] = "v1,AAAA " + h["webhook-signature"]
    whop.verify_signature(SECRET, h, body)


def _client(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    monkeypatch.setenv("WHOP_WEBHOOK_SECRET", SECRET)
    app = FastAPI()
    app.include_router(api.webhooks)
    return TestClient(app)


def test_webhook_rechaza_firma_mala_y_procesa_la_buena(monkeypatch):
    client = _client(monkeypatch)
    seen = []
    monkeypatch.setattr(whop, "handle_event",
                        lambda wid, ev: seen.append((wid, ev["type"])) or {"estado": "concedido"})
    body = json.dumps({"type": "payment.succeeded", "data": {}}).encode()
    bad = client.post("/webhooks/whop", content=body, headers={**sign(body), "webhook-signature": "v1,xx"})
    assert bad.status_code == 400 and seen == []
    ok = client.post("/webhooks/whop", content=body, headers=sign(body, msg_id="msg_9"))
    assert ok.status_code == 200 and ok.json() == {"ok": True, "estado": "concedido"}
    assert seen == [("msg_9", "payment.succeeded")]


def test_webhook_cerrado_sin_secreto(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.delenv("WHOP_WEBHOOK_SECRET")
    assert client.post("/webhooks/whop", content=b"{}").status_code == 503


def test_evento_web_de_meta_lleva_los_parametros_de_emq():
    row = {"event_name": "Purchase", "event_id": "purchase:ch_1", "action_source": "website",
           "event_time": datetime(2026, 10, 18, 12, tzinfo=timezone.utc),
           "custom_data": {"currency": "USD", "value": 33.99, "_country": "MX"},
           "web_context": {"fbp": "fb.1.1.2", "fbc": "fb.1.1.AbC", "client_ip": "203.0.113.9",
                           "user_agent": "UA/1.0", "source_url": "https://pronosticosdeportivos.pro/#checkout"}}
    account = {"account_id": 7, "email": "Ana@Ejemplo.com", "display_name": "Ana Pérez"}
    event = meta_capi.build_event(row, account, None)
    user = event["user_data"]
    assert event["action_source"] == "website" and event["event_id"] == "purchase:ch_1"
    assert event["event_source_url"].endswith("#checkout") and "app_data" not in event
    assert user["client_ip_address"] == "203.0.113.9" and user["client_user_agent"] == "UA/1.0"
    assert user["fbp"] == "fb.1.1.2" and user["fbc"] == "fb.1.1.AbC"
    assert user["em"] == [hashlib.sha256(b"ana@ejemplo.com").hexdigest()]
    assert user["fn"] == [hashlib.sha256("ana".encode()).hexdigest()]
    assert user["country"] == [hashlib.sha256(b"mx").hexdigest()]
    assert "external_id" in user and "_country" not in event["custom_data"]


# --- Con Postgres real -------------------------------------------------------------------------------

DSN = os.getenv("QF_TEST_PG_DSN")
pg = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture
def pool():
    from psycopg_pool import ConnectionPool
    from qf import db
    p = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, p
    yield p
    db._pool = old
    p.close()


def _cuenta():
    from qf.comercial import cuentas
    return cuentas.create_account(f"w-{uuid.uuid4().hex[:10]}@ejemplo.com", "clave-de-prueba-1", "Ana Pérez")


def _plan(plan_code="plus_1m"):
    from qf import db
    plan_id = "plan_" + uuid.uuid4().hex[:10]
    with db.conn() as c:
        c.execute("UPDATE plans SET whop_plan_id = %s WHERE plan_code = %s", (plan_id, plan_code))
    return plan_id


def _pago(plan_id, account_id, pay, **extra):
    return {"id": pay, "status": "paid", "plan_id": plan_id, "currency": "usd",
            "total": {"amount": "14.99", "currency": "usd"}, "membership_id": "mem_" + uuid.uuid4().hex[:8],
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"qf_account_id": str(account_id)}, **extra}


def _evento(tipo, data):
    return "wh_" + uuid.uuid4().hex, {"type": tipo, "data": data}


@pg
def test_pago_concede_una_vez_y_encadena_renovaciones(pool):
    from qf.comercial import suscripciones
    acc, plan_id = _cuenta(), _plan()
    pay = "pay_" + uuid.uuid4().hex[:8]
    first = whop.handle_event(*_evento("payment.succeeded", _pago(plan_id, acc["account_id"], pay)))
    assert first["estado"] == "concedido"
    dup = whop.handle_event(*_evento("payment.succeeded", _pago(plan_id, acc["account_id"], pay)))
    assert dup["estado"] == "duplicado"
    assert suscripciones.active_subscription(acc["account_id"])["plan_code"] == "plus_1m"
    renewal = whop.handle_event(*_evento("payment.succeeded", _pago(plan_id, acc["account_id"], pay + "r")))
    assert renewal["ends_at"] - first["ends_at"] == timedelta(days=30)


@pg
def test_misma_entrega_dos_veces_no_duplica(pool):
    acc, plan_id = _cuenta(), _plan()
    wid, event = _evento("payment.succeeded",
                         _pago(plan_id, acc["account_id"], "pay_" + uuid.uuid4().hex[:8]))
    assert whop.handle_event(wid, event)["estado"] == "concedido"
    assert whop.handle_event(wid, event)["estado"] == "duplicado"


@pg
def test_pago_sin_cuenta_o_plan_desconocido_no_concede(pool, monkeypatch):
    alerts = []
    monkeypatch.setattr(whop, "_alert", lambda t: alerts.append(t))
    plan_id = _plan()
    nobody = _pago(plan_id, 0, "pay_" + uuid.uuid4().hex[:8])
    assert whop.handle_event(*_evento("payment.succeeded", nobody))["estado"] == "sin_cuenta"
    acc = _cuenta()
    unknown = _pago("plan_inexistente", acc["account_id"], "pay_" + uuid.uuid4().hex[:8])
    assert whop.handle_event(*_evento("payment.succeeded", unknown))["estado"] == "plan_desconocido"
    assert len(alerts) == 2


@pg
def test_membresia_cancelada_revoca_el_acceso(pool):
    from qf.comercial import suscripciones
    acc, plan_id = _cuenta(), _plan()
    mem = "mem_" + uuid.uuid4().hex[:8]
    whop.handle_event(*_evento("payment.succeeded", _pago(
        plan_id, acc["account_id"], "pay_" + uuid.uuid4().hex[:8], membership_id=mem)))
    assert suscripciones.active_subscription(acc["account_id"])
    out = whop.handle_event(*_evento("membership.updated", {"id": mem, "status": "canceled"}))
    assert out["periodos"] == 1 and suscripciones.active_subscription(acc["account_id"]) is None


@pg
def test_membresia_desactivada_revoca_y_activa_no(pool):
    from qf.comercial import suscripciones
    acc, plan_id = _cuenta(), _plan()
    mem = "mem_" + uuid.uuid4().hex[:8]
    whop.handle_event(*_evento("payment.succeeded", _pago(
        plan_id, acc["account_id"], "pay_" + uuid.uuid4().hex[:8], membership_id=mem)))
    assert whop.handle_event(*_evento("membership.updated", {"id": mem, "status": "active"}))["estado"] == "ignorado"
    assert suscripciones.active_subscription(acc["account_id"])
    out = whop.handle_event(*_evento("membership.deactivated", {"id": mem}))
    assert out["periodos"] == 1 and suscripciones.active_subscription(acc["account_id"]) is None


class _Resp:
    def __init__(self, data): self._d = data
    def raise_for_status(self): pass
    def json(self): return self._d


class _Http:
    def __init__(self): self.calls = []
    def post(self, url, json, headers, timeout):
        self.calls.append((url, json, headers))
        return _Resp({"id": "ch_" + uuid.uuid4().hex[:10]})


@pg
def test_checkout_lo_crea_el_servidor_y_el_purchase_comparte_event_id(pool, monkeypatch):
    from qf import db
    monkeypatch.setenv("WHOP_API_KEY", "clave")
    monkeypatch.setenv("WHOP_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    acc, plan_id = _cuenta(), _plan()
    http = _Http()
    out = whop.create_checkout(acc, "plus_1m", fbp="fb.1.1.2", fbc="fb.1.1.AbC", client_ip="203.0.113.9",
                               user_agent="UA/1.0", source_url="https://x.test/#checkout", client=http)
    url, body, headers = http.calls[0]
    assert url.endswith("/checkout_configurations") and headers["Authorization"] == "Bearer clave"
    assert body["plan_id"] == plan_id and body["metadata"]["qf_account_id"] == str(acc["account_id"])
    assert out["event_id"] == f"purchase:{out['checkout_id']}"
    whop.handle_event(*_evento("payment.succeeded", {
        **_pago(plan_id, acc["account_id"], "pay_" + uuid.uuid4().hex[:8]),
        "checkout_configuration_id": out["checkout_id"], "billing_address": {"country": "MX"}}))
    with db.conn() as c:
        rows = c.execute("SELECT event_name, event_id, action_source, web_context, custom_data "
                         "FROM meta_events WHERE account_id = %s ORDER BY event_name",
                         (acc["account_id"],)).fetchall()
    purchase = next(r for r in rows if r["event_name"] == "Purchase")
    assert purchase["event_id"] == out["event_id"] and purchase["action_source"] == "website"
    assert purchase["web_context"]["fbp"] == "fb.1.1.2" and purchase["custom_data"]["_country"] == "MX"
    assert {"Purchase", "Subscribe"} <= {r["event_name"] for r in rows}


@pg
def test_checkout_rechaza_plan_sin_whop_y_pagos_apagados(pool, monkeypatch):
    acc = _cuenta()
    monkeypatch.delenv("WHOP_API_KEY", raising=False)
    with pytest.raises(whop.WhopError) as e:
        whop.create_checkout(acc, "plus_1m", fbp=None, fbc=None, client_ip=None, user_agent=None, source_url=None)
    assert e.value.code == "pagos_deshabilitados"
    monkeypatch.setenv("WHOP_API_KEY", "clave")
    monkeypatch.setenv("WHOP_WEBHOOK_SECRET", SECRET)
    with pytest.raises(whop.WhopError) as e:
        whop.create_checkout(acc, "plus_6m_sin_whop", fbp=None, fbc=None, client_ip=None, user_agent=None, source_url=None)
    assert e.value.code == "plan_inexistente"


def _request(headers: dict, cookies: str | None = None):
    from starlette.requests import Request
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    if cookies:
        raw.append((b"cookie", cookies.encode()))
    return Request({"type": "http", "headers": raw, "client": ("203.0.113.9", 4000), "method": "POST", "path": "/"})


def test_contexto_web_sale_de_cookies_y_cabeceras_solo_en_la_web():
    from qf.api import cuentas as accounts_api
    web = _request({"x-qf-client": "web", "user-agent": "UA/1.0", "referer": "https://pronosticosdeportivos.pro/#acceso"},
                   "_fbp=fb.1.1.2; _fbc=fb.1.1.AbC")
    ctx = accounts_api.web_context(web)
    assert ctx["fbp"] == "fb.1.1.2" and ctx["fbc"] == "fb.1.1.AbC" and ctx["user_agent"] == "UA/1.0"
    assert ctx["source_url"].endswith("#acceso") and ctx["client_ip"]
    assert accounts_api.web_context(_request({"user-agent": "app"}, "_fbp=fb.1.1.2")) is None
    assert meta_capi.web_kwargs(None) == {}
    assert meta_capi.web_kwargs(ctx)["action_source"] == "website"


@pg
def test_registro_web_encola_evento_website_y_el_de_la_app_no(pool, monkeypatch):
    from qf import db
    from qf.comercial import cuentas
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    ctx = {"fbp": "fb.1.1.2", "client_ip": "203.0.113.9", "user_agent": "UA/1.0", "source_url": "https://x.test/#acceso"}
    web = cuentas.create_account(f"w-{uuid.uuid4().hex[:10]}@ejemplo.com", "clave-de-prueba-1", "Ana Pérez", web_context=ctx)
    app = cuentas.create_account(f"a-{uuid.uuid4().hex[:10]}@ejemplo.com", "clave-de-prueba-1", "Beto")
    with db.conn() as c:
        w = c.execute("SELECT action_source, web_context, event_id FROM meta_events WHERE account_id = %s",
                      (web["account_id"],)).fetchone()
        a = c.execute("SELECT action_source, web_context FROM meta_events WHERE account_id = %s",
                      (app["account_id"],)).fetchone()
    assert w["action_source"] == "website" and w["web_context"]["fbp"] == "fb.1.1.2"
    assert w["event_id"] == f"reg:{web['account_id']}"
    assert a["action_source"] == "app" and a["web_context"] is None


@pg
def test_reembolso_exitoso_revoca_el_periodo_y_pendiente_no(pool):
    from qf.comercial import suscripciones
    acc, plan_id = _cuenta(), _plan()
    pay = "pay_" + uuid.uuid4().hex[:8]
    whop.handle_event(*_evento("payment.succeeded", _pago(plan_id, acc["account_id"], pay)))
    assert suscripciones.active_subscription(acc["account_id"])
    pending = whop.handle_event(*_evento("refund.created", {"id": "rf_1", "payment_id": pay, "status": "pending"}))
    assert pending["estado"] == "ignorado" and suscripciones.active_subscription(acc["account_id"])
    done = whop.handle_event(*_evento("refund.updated", {"id": "rf_1", "payment_id": pay, "status": "succeeded"}))
    assert done["estado"] == "revocado" and suscripciones.active_subscription(acc["account_id"]) is None
    again = whop.handle_event(*_evento("refund.updated", {"id": "rf_1", "payment_id": pay, "status": "succeeded"}))
    assert again["estado"] == "ya_revocado"


@pg
def test_reembolso_de_pago_desconocido_alerta(pool, monkeypatch):
    alerts = []
    monkeypatch.setattr(whop, "_alert", lambda t: alerts.append(t))
    out = whop.handle_event(*_evento("refund.created", {"id": "rf_9", "payment_id": "pay_nope", "status": "succeeded"}))
    assert out["estado"] == "pago_desconocido" and len(alerts) == 1


def test_purchase_web_lleva_ciudad_estado_zip_y_telefono_cifrados():
    row = {"event_name": "Purchase", "event_id": "purchase:ch_2", "action_source": "website",
           "event_time": datetime(2026, 10, 18, 12, tzinfo=timezone.utc),
           "custom_data": {"currency": "USD", "value": 14.99, "_country": "MX", "_ct": "Monterrey", "_st": "NL",
                           "_zp": "64000", "_ph": "+52 81 1234 5678"},
           "web_context": {"client_ip": "203.0.113.9", "user_agent": "UA/1.0"}}
    event = meta_capi.build_event(row, {"account_id": 7, "email": "a@b.com", "display_name": "Ana"}, None)
    assert {"ct", "st", "zp", "ph", "em", "country", "external_id", "fn"} <= set(event["user_data"])
    assert not any(k.startswith("_") for k in event["custom_data"])
    assert event["user_data"]["ph"] == [hashlib.sha256(b"528112345678").hexdigest()]
