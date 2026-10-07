"""Correo transaccional (Proton por SMTP): envío, enlaces y rutas que lo usan."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import cuenta_web, cuentas as api
from qf.comercial import correo, cuentas
from test_cuentas_api import FakeRedis


class FakeSMTP:
    sent = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.calls = host, port, []
        FakeSMTP.last = self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user))

    def send_message(self, msg):
        self.calls.append("send")
        FakeSMTP.sent.append(msg)


@pytest.fixture
def proton(monkeypatch):
    FakeSMTP.sent = []
    monkeypatch.setattr(correo.smtplib, "SMTP", FakeSMTP)
    for k, v in {"SMTP_HOST": "smtp.protonmail.ch", "SMTP_PORT": "587",
                 "SMTP_USERNAME": "no-responder@quantfut.test", "SMTP_PASSWORD": "token-smtp",
                 "SMTP_FROM": "no-responder@quantfut.test", "PUBLIC_BASE_URL": "https://quantfut.test"}.items():
        monkeypatch.setenv(k, v)


def test_starttls_antes_de_mandar_la_contrasena(proton):
    correo.send("ana@correo.test", "Asunto", "Hola")
    s = FakeSMTP.last
    assert (s.host, s.port) == ("smtp.protonmail.ch", 587)
    assert s.calls == ["starttls", ("login", "no-responder@quantfut.test"), "send"]
    msg = FakeSMTP.sent[0]
    assert msg["From"] == "QuantFut <no-responder@quantfut.test>" and msg["To"] == "ana@correo.test"
    assert msg["Message-ID"].endswith("@quantfut.test>")


def test_sin_configurar_no_envia(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    assert not correo.configurado()
    with pytest.raises(correo.CorreoNoConfigurado):
        correo.send("a@b.com", "x", "y")
    assert correo.enviar_verificacion(1, "a@b.com") is False


def test_seguridad_desconocida_no_cae_a_texto_plano(proton, monkeypatch):
    monkeypatch.setenv("SMTP_SECURITY", "none")
    with pytest.raises(correo.CorreoNoConfigurado):
        correo.send("a@b.com", "x", "y")


def test_enlaces_apuntan_a_las_paginas_de_cuenta(proton):
    _, texto = correo.verification_message("tok123", 48)
    assert "https://quantfut.test/cuenta/verificar?token=tok123" in texto
    _, texto = correo.reset_message("tok456", 60)
    assert "https://quantfut.test/cuenta/restablecer?token=tok456" in texto


def test_fallo_smtp_no_rompe_la_peticion(proton, monkeypatch):
    def boom(*_a, **_k):
        raise OSError("sin red")
    monkeypatch.setattr(correo.smtplib, "SMTP", boom)
    assert correo.send_safely("a@b.com", "x", "y") is False


# --- Rutas -------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    monkeypatch.setattr(api, "_redis", FakeRedis())
    app = FastAPI()
    app.include_router(api.router)
    app.include_router(cuenta_web.router)
    return TestClient(app)


def test_olvido_responde_igual_exista_o_no_la_cuenta(monkeypatch, client):
    enviados = []
    monkeypatch.setattr(correo, "enviar_restablecimiento", lambda aid, email: enviados.append(aid))
    monkeypatch.setattr(cuentas, "account_for_reset",
                        lambda email: {"account_id": 9, "email": email} if email == "si@b.com" else None)
    a = client.post("/app/v1/auth/password/forgot", json={"email": "si@b.com"})
    b = client.post("/app/v1/auth/password/forgot", json={"email": "no@b.com"})
    assert a.status_code == b.status_code == 202 and a.json() == b.json()
    assert enviados == [9]


def test_olvido_limita_enlaces_por_correo(monkeypatch, client):
    enviados = []
    monkeypatch.setattr(correo, "enviar_restablecimiento", lambda aid, email: enviados.append(aid))
    monkeypatch.setattr(cuentas, "account_for_reset", lambda email: {"account_id": 9, "email": email})
    for i in range(5):
        client.post("/app/v1/auth/password/forgot", json={"email": "si@b.com"},
                    headers={"X-Forwarded-For": f"10.1.0.{i}"})
    assert enviados == [9, 9, 9]


def test_reenviar_verificacion_sin_smtp_lo_dice(monkeypatch, client):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setattr(cuentas, "account_from_access", lambda _r, t: {
        "account_id": 1, "email": "a@b.com", "email_verified_at": None, "session_id": 1})
    r = client.post("/app/v1/auth/verify/resend", headers={"Authorization": "Bearer x"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "correo_no_configurado"


def test_abrir_el_enlace_no_gasta_el_token(monkeypatch, client):
    consumidos = []
    monkeypatch.setattr(cuentas, "email_token_valid", lambda tok, purpose: tok == "bueno")
    monkeypatch.setattr(cuentas, "confirm_email", lambda tok: consumidos.append(tok) or tok == "bueno")
    page = client.get("/cuenta/verificar?token=bueno")
    assert page.status_code == 200 and 'value="bueno"' in page.text and consumidos == []
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert client.get("/cuenta/verificar?token=malo").status_code == 400
    done = client.post("/cuenta/verificar", data={"token": "bueno"})
    assert done.status_code == 200 and "Correo confirmado" in done.text and consumidos == ["bueno"]


def test_restablecer_exige_las_dos_contrasenas_iguales(monkeypatch, client):
    monkeypatch.setattr(cuentas, "reset_password", lambda *a: pytest.fail("no debía cambiarla"))
    r = client.post("/cuenta/restablecer",
                    data={"token": "t", "password": "una-clave-larga", "password2": "otra-clave-larga"})
    assert r.status_code == 422 and "no coinciden" in r.text


def test_token_del_formulario_se_escapa(monkeypatch, client):
    monkeypatch.setattr(cuentas, "email_token_valid", lambda tok, purpose: True)
    r = client.get('/cuenta/restablecer?token="><script>alert(1)</script>')
    assert "<script>alert(1)" not in r.text and "&lt;script&gt;" in r.text
