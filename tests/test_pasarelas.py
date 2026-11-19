"""Pasarelas de pago en /control (db/117): claves cifradas, sandbox solo para cuentas de prueba, webhook propio."""
import uuid
from datetime import datetime, timezone

import pytest

from qf.comercial import cifrado, pasarelas, whop
from test_whop import SECRET, _Http, _cuenta, _evento, _pago, pg, pool, sign  # noqa: F401 - fixtures compartidas

ACTOR = "panel:prueba"


@pytest.fixture
def clave_maestra(monkeypatch):
    monkeypatch.setenv(cifrado.ENV_KEY, cifrado.generar_clave())


@pytest.fixture
def bd(pool):
    """La base de pruebas se comparte: cada prueba deja limpia la configuración de pasarelas."""
    from qf import db

    def limpiar():
        with db.conn() as c:
            c.execute("DELETE FROM pasarela_config")
            c.execute("DELETE FROM pasarela_cuentas_prueba")
            c.execute("UPDATE plans SET whop_plan_id_sandbox = NULL")
    limpiar()
    yield
    limpiar()


@pytest.fixture
def sin_entorno(monkeypatch):
    for k in ("WHOP_API_KEY", "WHOP_WEBHOOK_SECRET", "WHOP_ACCOUNT_ID"):
        monkeypatch.delenv(k, raising=False)


def test_mascara_solo_muestra_los_ultimos_cuatro():
    assert pasarelas.mascara("apik_abcdefgh1234") == "••••1234"
    assert pasarelas.mascara("corta") == "••••"
    assert pasarelas.mascara(None) == ""


def test_el_sandbox_usa_su_propia_api():
    assert pasarelas.api_base("sandbox") == "https://sandbox-api.whop.com/api/v1"
    assert "sandbox" not in pasarelas.api_base("live")


def test_guardar_valida_prefijos_y_exige_clave_maestra(monkeypatch):
    monkeypatch.delenv(cifrado.ENV_KEY, raising=False)
    with pytest.raises(pasarelas.PasarelaError) as e:
        pasarelas.guardar("sandbox", ACTOR, api_key="apik_x")
    assert e.value.code == "sin_clave_maestra"
    monkeypatch.setenv(cifrado.ENV_KEY, cifrado.generar_clave())
    with pytest.raises(pasarelas.PasarelaError) as e:
        pasarelas.guardar("sandbox", ACTOR, api_key="sk_live_no")
    assert e.value.code == "clave_invalida"
    with pytest.raises(pasarelas.PasarelaError) as e:
        pasarelas.guardar("sandbox", ACTOR, webhook_secret="abc")
    assert e.value.code == "secreto_invalido"
    with pytest.raises(pasarelas.PasarelaError) as e:
        pasarelas.guardar("otro", ACTOR, api_key="apik_x")
    assert e.value.code == "modo_invalido"


def test_plan_sandbox_exige_prefijo():
    with pytest.raises(pasarelas.PasarelaError) as e:
        pasarelas.plan_sandbox("plus_1m", "prod_123", ACTOR)
    assert e.value.code == "plan_invalido"


@pg
def test_claves_se_guardan_cifradas_y_el_panel_solo_ve_la_mascara(bd, clave_maestra, sin_entorno):
    from qf import db
    assert pasarelas.credenciales("sandbox") is None
    assert pasarelas.guardar("sandbox", ACTOR, api_key="apik_sandbox_ABCD", webhook_secret="ws_sandbox_WXYZ",
                             account_id="biz_prueba") == ["api_key", "webhook_secret", "account_id"]
    with db.conn() as c:
        fila = c.execute("SELECT * FROM pasarela_config WHERE modo = 'sandbox'").fetchone()
        auditoria = c.execute("SELECT detail FROM admin_audit WHERE action = 'pasarela.guardar' "
                              "ORDER BY audit_id DESC LIMIT 1").fetchone()
    assert "apik_sandbox_ABCD" not in fila["api_key_enc"] and fila["api_key_enc"].startswith("v1:")
    assert pasarelas.credenciales("sandbox") == {"api_key": "apik_sandbox_ABCD",
                                                 "webhook_secret": "ws_sandbox_WXYZ", "account_id": "biz_prueba"}
    est = pasarelas.estado("sandbox")
    assert est["api_key"] == "••••ABCD" and est["webhook_secret"] == "••••WXYZ"
    assert "apik_sandbox" not in str(auditoria["detail"])        # la auditoría guarda qué campos, nunca el valor
    # Vacío = conservar; no pisa lo guardado.
    assert pasarelas.guardar("sandbox", ACTOR, account_id="") == []
    assert pasarelas.credenciales("sandbox")["api_key"] == "apik_sandbox_ABCD"


@pg
def test_el_secreto_cifrado_de_un_modo_no_se_puede_pasar_a_otro(bd, clave_maestra, sin_entorno):
    from qf import db
    pasarelas.guardar("sandbox", ACTOR, api_key="apik_sandbox_ABCD", webhook_secret="ws_s")
    with db.conn() as c:
        c.execute("INSERT INTO pasarela_config (proveedor, modo, api_key_enc, webhook_secret_enc) "
                  "SELECT proveedor, 'live', api_key_enc, webhook_secret_enc FROM pasarela_config "
                  "WHERE modo = 'sandbox' ON CONFLICT (proveedor, modo) DO UPDATE SET api_key_enc = EXCLUDED.api_key_enc")
    assert pasarelas.credenciales("live") is None      # no descifra: se trata como no guardado, sin romper el cobro


@pg
def test_produccion_sigue_con_el_entorno_si_no_hay_claves_guardadas(bd, monkeypatch):
    monkeypatch.setenv("WHOP_API_KEY", "clave_env")
    monkeypatch.setenv("WHOP_WEBHOOK_SECRET", SECRET)
    assert pasarelas.credenciales("live")["api_key"] == "clave_env"
    assert whop.enabled()


def _plan_sandbox(plan_code="plus_1m"):
    plan_id = "plan_sbx_" + uuid.uuid4().hex[:8]
    assert pasarelas.plan_sandbox(plan_code, plan_id, ACTOR)
    return plan_id


@pg
def test_quien_no_es_de_prueba_siempre_paga_en_produccion_aunque_haya_sandbox(bd, clave_maestra, sin_entorno, monkeypatch):
    monkeypatch.setenv("WHOP_API_KEY", "clave_live")
    monkeypatch.setenv("WHOP_WEBHOOK_SECRET", SECRET)
    pasarelas.guardar("sandbox", ACTOR, api_key="apik_sbx", webhook_secret="ws_sbx")
    _plan_sandbox()
    from test_whop import _plan
    plan_live = _plan()
    acc, http = _cuenta(), _Http()
    out = whop.create_checkout(acc, "plus_1m", fbp=None, fbc=None, client_ip=None, user_agent=None,
                               source_url=None, client=http)
    url, body, headers = http.calls[0]
    assert out["environment"] == "production" and "sandbox" not in url
    assert body["plan_id"] == plan_live and headers["Authorization"] == "Bearer clave_live"


@pg
def test_cuenta_de_prueba_va_al_sandbox_con_su_plan_y_sin_meta(bd, clave_maestra, sin_entorno, monkeypatch):
    from qf import db
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    pasarelas.guardar("sandbox", ACTOR, api_key="apik_sbx", webhook_secret="ws_sbx", account_id="biz_sbx")
    plan_sbx = _plan_sandbox()
    acc, http = _cuenta(), _Http()
    with db.conn() as c:
        email = c.execute("SELECT email FROM accounts WHERE account_id = %s", (acc["account_id"],)).fetchone()["email"]
    pasarelas.agregar_cuenta_prueba(str(email), ACTOR)
    out = whop.create_checkout(acc, "plus_1m", fbp=None, fbc=None, client_ip=None, user_agent=None,
                               source_url=None, client=http)
    url, body, headers = http.calls[0]
    assert out["environment"] == "sandbox" and url.startswith("https://sandbox-api.whop.com/")
    assert body["plan_id"] == plan_sbx and body["account_id"] == "biz_sbx"
    assert headers["Authorization"] == "Bearer apik_sbx"
    with db.conn() as c:
        assert c.execute("SELECT modo FROM whop_checkouts WHERE checkout_id = %s",
                         (out["checkout_id"],)).fetchone()["modo"] == "sandbox"
        assert c.execute("SELECT count(*) AS n FROM meta_events WHERE account_id = %s AND event_name = 'InitiateCheckout'",
                         (acc["account_id"],)).fetchone()["n"] == 0


@pg
def test_cuenta_de_prueba_sin_claves_de_sandbox_no_cae_a_produccion(bd, clave_maestra, sin_entorno, monkeypatch):
    monkeypatch.setenv("WHOP_API_KEY", "clave_live")
    monkeypatch.setenv("WHOP_WEBHOOK_SECRET", SECRET)
    from qf import db
    acc = _cuenta()
    with db.conn() as c:
        email = c.execute("SELECT email FROM accounts WHERE account_id = %s", (acc["account_id"],)).fetchone()["email"]
    pasarelas.agregar_cuenta_prueba(str(email), ACTOR)
    with pytest.raises(whop.WhopError) as e:
        whop.create_checkout(acc, "plus_1m", fbp=None, fbc=None, client_ip=None, user_agent=None, source_url=None,
                             client=_Http())
    assert e.value.code == "sandbox_sin_configurar"


@pg
def test_pago_sandbox_concede_a_cuenta_de_prueba_con_importe_cero_y_sin_meta(bd, clave_maestra, sin_entorno):
    from qf import db
    plan_sbx = _plan_sandbox()
    acc = _cuenta()
    with db.conn() as c:
        email = c.execute("SELECT email FROM accounts WHERE account_id = %s", (acc["account_id"],)).fetchone()["email"]
    pasarelas.agregar_cuenta_prueba(str(email), ACTOR)
    pay = "pay_" + uuid.uuid4().hex[:8]
    res = whop.handle_event(*_evento("payment.succeeded", _pago(plan_sbx, acc["account_id"], pay)), modo="sandbox")
    assert res["estado"] == "concedido"
    with db.conn() as c:
        sub = c.execute("SELECT price_cents, note FROM subscriptions WHERE account_id = %s", (acc["account_id"],)).fetchone()
        fila = c.execute("SELECT modo FROM whop_payments WHERE payment_id = %s", (pay,)).fetchone()
        meta = c.execute("SELECT count(*) AS n FROM meta_events WHERE account_id = %s AND event_name IN ('Purchase', 'Subscribe')",
                         (acc["account_id"],)).fetchone()["n"]
    assert sub["price_cents"] == 0 and sub["note"] == f"whop-sandbox:{pay}"
    assert fila["modo"] == "sandbox" and meta == 0


@pg
def test_pago_sandbox_de_cuenta_no_autorizada_no_concede(bd, clave_maestra, sin_entorno, monkeypatch):
    from qf import db
    monkeypatch.setattr(whop, "_alert", lambda text: None)
    plan_sbx = _plan_sandbox()
    acc = _cuenta()                                              # NO está en pasarela_cuentas_prueba
    res = whop.handle_event(*_evento("payment.succeeded", _pago(plan_sbx, acc["account_id"], "pay_" + uuid.uuid4().hex[:8])),
                            modo="sandbox")
    assert res["estado"] == "cuenta_no_autorizada"
    with db.conn() as c:
        assert c.execute("SELECT count(*) AS n FROM subscriptions WHERE account_id = %s",
                         (acc["account_id"],)).fetchone()["n"] == 0


@pg
def test_pago_de_produccion_no_acepta_el_plan_de_sandbox(bd, clave_maestra, sin_entorno, monkeypatch):
    monkeypatch.setattr(whop, "_alert", lambda text: None)
    plan_sbx = _plan_sandbox()
    acc = _cuenta()
    res = whop.handle_event(*_evento("payment.succeeded", _pago(plan_sbx, acc["account_id"], "pay_" + uuid.uuid4().hex[:8])))
    assert res["estado"] == "plan_desconocido"


@pg
def test_webhooks_cada_uno_con_su_secreto(bd, clave_maestra, sin_entorno, monkeypatch):
    import json
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from qf.api import whop as api
    monkeypatch.setenv("WHOP_API_KEY", "clave_live")
    monkeypatch.setenv("WHOP_WEBHOOK_SECRET", SECRET)
    pasarelas.guardar("sandbox", ACTOR, api_key="apik_sbx", webhook_secret="ws_sandbox_distinto")
    app = FastAPI()
    app.include_router(api.webhooks)
    cli = TestClient(app)
    body = json.dumps({"type": "otro.evento", "data": {}}).encode()
    # Firma de producción en la ruta del sandbox → rechazada; y al revés.
    assert cli.post("/webhooks/whop-sandbox", content=body, headers=sign(body, secret=SECRET)).status_code == 400
    assert cli.post("/webhooks/whop", content=body, headers=sign(body, secret="ws_sandbox_distinto")).status_code == 400
    assert cli.post("/webhooks/whop-sandbox", content=body,
                    headers=sign(body, secret="ws_sandbox_distinto")).status_code == 200
    assert cli.post("/webhooks/whop", content=body, headers=sign(body, msg_id="m2")).status_code == 200


@pg
def test_webhook_sandbox_cerrado_sin_claves(bd, sin_entorno):
    import json
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from qf.api import whop as api
    app = FastAPI()
    app.include_router(api.webhooks)
    body = json.dumps({"type": "x"}).encode()
    assert TestClient(app).post("/webhooks/whop-sandbox", content=body, headers=sign(body)).status_code == 503


@pg
def test_pagina_de_pasarelas_no_muestra_las_claves(bd, clave_maestra, sin_entorno, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from qf.api import console, panel, pasarelas_panel
    pasarelas.guardar("sandbox", ACTOR, api_key="apik_secreta_ABCD", webhook_secret="ws_secreto_WXYZ")
    app = FastAPI()
    app.include_router(pasarelas_panel.router)
    app.dependency_overrides[console.require_console] = lambda: "admin"
    cli = TestClient(app)
    html = cli.get("/control/pasarelas").text
    assert "••••ABCD" in html and "apik_secreta" not in html and "ws_secreto" not in html
    assert "/webhooks/whop-sandbox" in html
    # Un POST sin token CSRF se rechaza.
    assert cli.post("/control/pasarelas/sandbox", data={"api_key": "apik_x"}).status_code == 403
