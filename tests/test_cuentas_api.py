"""API de clientes (/app/v1) y acciones del panel, sin base de datos."""
from dataclasses import replace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import cuentas as api, panel
from qf.comercial import cuentas, suscripciones
from qf.comercial.cuentas import CuentaError


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, k):
        return self.data.get(k)

    def setex(self, k, _ttl, v):
        self.data[k] = str(v)

    def delete(self, k):
        self.data.pop(k, None)

    def incr(self, k):
        self.data[k] = int(self.data.get(k, 0)) + 1
        return self.data[k]

    def expire(self, *_a):
        pass


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    fake = FakeRedis()
    monkeypatch.setattr(api, "_redis", fake)
    app = FastAPI()
    app.include_router(api.router)
    app.include_router(api.public_router)
    app.include_router(api.openapi_router)
    c = TestClient(app)
    c.redis = fake
    return c


def _logged(monkeypatch, client, plus: bool):
    acc = {"account_id": 7, "email": "a@b.com", "display_name": None, "status": "active",
           "email_verified_at": None, "created_at": "2026-10-07T00:00:00Z", "session_id": 1}
    monkeypatch.setattr(cuentas, "account_from_access",
                        lambda _r, tok: dict(acc) if tok == "buen-token" else None)
    sub = {"subscription_id": 1, "plan_code": "plus_1m", "plan_name": "Plus · 1 mes",
           "starts_at": "2026-10-01T00:00:00Z", "ends_at": "2026-10-31T00:00:00Z", "source": "manual"}
    monkeypatch.setattr(suscripciones, "active_subscription", lambda _id: sub if plus else None)
    return {"Authorization": "Bearer buen-token"}


def test_apagado_por_defecto_no_abre_altas(monkeypatch, client):
    monkeypatch.delenv("ACCOUNTS_ENABLED")
    r = client.post("/app/v1/auth/register", json={"email": "a@b.com", "password": "x" * 12})
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "cuentas_deshabilitadas"


def test_precios_publicos_aunque_las_altas_esten_cerradas(monkeypatch, client):
    monkeypatch.delenv("ACCOUNTS_ENABLED")
    monkeypatch.setattr(suscripciones, "plans", lambda only_active=False: [
        {"plan_code": "plus_1m", "name": "Plus · 1 mes", "duration_days": 30, "price_cents": 1299,
         "currency": "USD", "active": True, "sort_order": 10}] if only_active else pytest.fail("solo activos"))
    r = client.get("/app/v1/plans")
    assert r.status_code == 200 and r.json()[0]["price_cents"] == 1299
    assert "active" not in r.json()[0]
    assert "/app/v1/plans" in client.get("/app/v1/openapi.json").json()["paths"]


def test_sin_token_no_hay_picks_ni_perfil(client):
    assert client.get("/app/v1/picks").status_code == 401
    assert client.get("/app/v1/me").status_code == 401
    # Un token de servicio no es una sesión de cliente.
    assert client.get("/app/v1/picks", headers={"X-Service-Token": "x"}).status_code == 401


def test_sin_plus_solo_recibe_tier_free(monkeypatch, client):
    pedidos = []
    monkeypatch.setattr(api, "picks_for_tiers", lambda tiers, **_kw: pedidos.append(tiers) or [])
    headers = _logged(monkeypatch, client, plus=False)
    body = client.get("/app/v1/picks", headers=headers).json()
    assert body["plus"] is False and pedidos == [("free",)]


def test_con_plus_recibe_free_y_paid(monkeypatch, client):
    pedidos = []
    monkeypatch.setattr(api, "picks_for_tiers", lambda tiers, **_kw: pedidos.append(tiers) or [])
    monkeypatch.setattr(api, "settings", replace(api.settings, publish_picks_enabled=False))
    headers = _logged(monkeypatch, client, plus=True)
    body = client.get("/app/v1/picks", headers=headers).json()
    assert body == {"plus": True, "publicacion_activa": False, "picks": []}
    assert pedidos == [("free", "paid")]
    me = client.get("/app/v1/me", headers=headers).json()
    assert me["plus"] is True and me["subscription"]["plan_code"] == "plus_1m"


def test_login_fallido_y_suspendido(monkeypatch, client):
    monkeypatch.setattr(cuentas, "authenticate", lambda e, p: None)
    r = client.post("/app/v1/auth/login", json={"email": "a@b.com", "password": "mala-clave-12"})
    assert r.status_code == 401
    monkeypatch.setattr(cuentas, "authenticate", lambda e, p: {"account_id": 1, "status": "suspended"})
    r = client.post("/app/v1/auth/login", json={"email": "a@b.com", "password": "buena-clave-12"})
    assert r.status_code == 403


def test_login_limitado_por_correo(monkeypatch, client):
    monkeypatch.setattr(cuentas, "authenticate", lambda e, p: None)
    codes = [client.post("/app/v1/auth/login", headers={"X-Forwarded-For": f"10.0.0.{i}"},
                         json={"email": "victima@b.com", "password": "x" * 12}).status_code
             for i in range(12)]
    assert codes[:10] == [401] * 10 and codes[10:] == [429, 429]


def test_registro_valida_y_no_duplica(monkeypatch, client):
    def create(email, password, name, web_context=None):
        cuentas.normalize_email(email)
        cuentas.validate_password(password)
        raise CuentaError("email_en_uso", "Ya existe")
    monkeypatch.setattr(cuentas, "create_account", create)
    assert client.post("/app/v1/auth/register",
                       json={"email": "no-es-correo", "password": "x" * 12}).status_code == 422
    assert client.post("/app/v1/auth/register",
                       json={"email": "a@b.com", "password": "corta"}).status_code == 422
    assert client.post("/app/v1/auth/register",
                       json={"email": "a@b.com", "password": "x" * 12}).status_code == 409


def test_openapi_solo_documenta_rutas_de_clientes(client):
    spec = client.get("/app/v1/openapi.json").json()
    paths = set(spec["paths"])
    assert "/app/v1/picks" in paths and "/app/v1/auth/login" in paths
    assert all(p.startswith("/app/v1/") for p in paths)
    assert "X-Service-Token" not in str(spec) and "X-Admin-Token" not in str(spec)


# --- Panel -----------------------------------------------------------------

@pytest.fixture
def panel_client(monkeypatch):
    import hashlib
    salt = b"1234567890abcdef"
    digest = hashlib.pbkdf2_hmac("sha256", b"clave-del-panel-larga", salt, 600_000)
    monkeypatch.setenv("ADMIN_CONSOLE_USER", "operador")
    monkeypatch.setenv("ADMIN_CONSOLE_PASSWORD_HASH", f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}")
    app = FastAPI()
    app.include_router(panel.router)
    c = TestClient(app, base_url="https://testserver")
    c.auth = ("operador", "clave-del-panel-larga")
    return c


def test_acciones_del_panel_exigen_csrf_y_mismo_origen(monkeypatch, panel_client):
    concedidas = []
    monkeypatch.setattr(suscripciones, "grant", lambda *a, **kw: concedidas.append((a, kw)))
    url = "/control/usuarios/5/suscripcion"
    assert panel_client.post(url, data={"plan_code": "plus_1m"}).status_code == 403
    token = panel.csrf_token("operador")
    r = panel_client.post(url, data={"plan_code": "plus_1m", "csrf": token},
                          headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403
    r = panel_client.post(url, data={"plan_code": "plus_1m", "csrf": token},
                          headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert concedidas == []

    r = panel_client.post(url, data={"plan_code": "plus_1m", "csrf": token, "nota": "cortesía"},
                          headers={"Origin": "https://testserver", "Sec-Fetch-Site": "same-origin",
                                   "Cf-Access-Authenticated-User-Email": "op@x.com"},
                          follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("m=concedida")
    (args, kw), = concedidas
    assert args == (5, "plus_1m", "panel:operador (op@x.com)") and kw == {"note": "cortesía"}


def test_panel_sin_credenciales_no_ejecuta_acciones(monkeypatch, panel_client):
    monkeypatch.setattr(suscripciones, "grant", lambda *a, **kw: pytest.fail("no debía conceder"))
    panel_client.auth = None
    r = panel_client.post("/control/usuarios/5/suscripcion",
                          data={"plan_code": "plus_1m", "csrf": panel.csrf_token("operador")})
    assert r.status_code == 401


def test_mensaje_tras_accion_no_refleja_texto_de_la_url(monkeypatch, panel_client):
    monkeypatch.setattr(panel.metricas, "auditoria", lambda **_kw: [])
    r = panel_client.get("/control/auditoria?m=<script>alert(1)</script>")
    assert r.status_code == 200 and "alert(1)" not in r.text
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert "unsafe-inline" not in r.headers["content-security-policy"]


@pytest.mark.parametrize("texto,cents", [("14,99", 1499), ("14.99", 1499), ("0", 0), ("179.9", 17990)])
def test_precio_en_centimos_sin_float(texto, cents):
    assert panel.parse_price(texto) == cents


@pytest.mark.parametrize("texto", ["-1", "abc", "1.999", "nan", "inf", ""])
def test_precio_invalido(texto):
    with pytest.raises(CuentaError):
        panel.parse_price(texto)



# --- Modo web: refresh en cookie HttpOnly ------------------------------------

def test_web_recibe_el_refresh_solo_en_cookie_httponly(monkeypatch, client):
    monkeypatch.setattr(cuentas, "authenticate", lambda e, p: {"account_id": 3, "status": "active"})
    monkeypatch.setattr(cuentas, "open_session", lambda *a: {
        "access_token": "acc", "refresh_token": "ref-secreto", "token_type": "bearer", "expires_in": 900})
    r = client.post("/app/v1/auth/login", headers={"X-QF-Client": "web"},
                    json={"email": "a@b.com", "password": "una-clave-larga"})
    assert r.status_code == 200 and r.json()["refresh_token"] is None
    cookie = r.headers["set-cookie"]
    assert "qf_refresh=ref-secreto" in cookie and "HttpOnly" in cookie
    assert "Path=/app/v1/auth" in cookie and "SameSite=strict" in cookie and "Secure" in cookie
    pista = [c for c in r.headers.get_list("set-cookie") if c.startswith("qf_hay_sesion=1")]
    assert pista and "HttpOnly" not in pista[0] and "ref-secreto" not in pista[0]
    # La app (sin cabecera) sigue recibiendo el refresh en el cuerpo y sin cookie.
    r = client.post("/app/v1/auth/login", json={"email": "a@b.com", "password": "una-clave-larga"})
    assert r.json()["refresh_token"] == "ref-secreto" and "set-cookie" not in r.headers


def test_refresh_web_usa_la_cookie_con_gracia_y_la_app_no(monkeypatch, client):
    vistos = []
    def rotate(_r, token, grace_seconds=0):
        vistos.append((token, grace_seconds))
        return {"access_token": "acc2", "refresh_token": "ref2", "token_type": "bearer", "expires_in": 900}
    monkeypatch.setattr(cuentas, "rotate_refresh", rotate)
    client.cookies.set("qf_refresh", "ref1", path="/app/v1/auth")
    r = client.post("/app/v1/auth/refresh", headers={"X-QF-Client": "web"})
    assert r.status_code == 200 and r.json()["refresh_token"] is None
    assert "qf_refresh=ref2" in r.headers["set-cookie"]
    # Sin la cabecera la cookie no cuenta: otra web no puede añadir X-QF-Client sin preflight.
    client.post("/app/v1/auth/refresh")
    assert vistos == [("ref1", api.WEB_GRACE_SECONDS), ("", 0)]


def test_refresh_web_invalido_borra_la_cookie(monkeypatch, client):
    def rotate(*_a, **_k):
        raise CuentaError("refresh_invalido", "Sesión no válida")
    monkeypatch.setattr(cuentas, "rotate_refresh", rotate)
    client.cookies.set("qf_refresh", "muerto", path="/app/v1/auth")
    r = client.post("/app/v1/auth/refresh", headers={"X-QF-Client": "web"})
    borradas = r.headers.get_list("set-cookie")
    assert r.status_code == 401 and r.json()["detail"]["code"] == "refresh_invalido"
    assert any(c.startswith('qf_refresh=""') and "Max-Age=0" in c for c in borradas)
    assert any(c.startswith('qf_hay_sesion=""') and "Max-Age=0" in c for c in borradas)
