"""`member` de /mobile/v1 debe reconocer la identidad Firebase (cabecera X-QF-Identity).

Regresión (2026-10-12): `mobile.py` usaba `request: Request` sin importar `Request`. Con
`from __future__ import annotations`, FastAPI no resolvía el tipo, `request` llegaba siempre
vacío y todo token de Google se validaba como sesión clásica: 401 «Sesión no válida».
"""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from qf.api import firebase as api_firebase
from qf.api import mobile
from qf.comercial import suscripciones


def _cliente(monkeypatch, vistos):
    monkeypatch.setattr(mobile.cuentas, "require_enabled", lambda: None)

    def firebase_falso(creds, request):
        vistos.append(("firebase", creds.credentials, request.headers.get("x-qf-identity")))
        return {"account_id": 7}

    monkeypatch.setattr(api_firebase, "firebase_account", firebase_falso)
    monkeypatch.setattr(mobile.cuentas, "current_account",
                        lambda creds, request=None: vistos.append(("clasica", creds.credentials)) or {"account_id": 9})
    monkeypatch.setattr(suscripciones, "active_subscription", lambda account_id: {"id": account_id})
    app = FastAPI()

    @app.get("/probe")
    def probe(plus: bool = Depends(mobile.member)):
        return {"plus": plus}

    return TestClient(app)


def test_el_token_de_google_va_por_la_ruta_firebase(monkeypatch):
    vistos = []
    c = _cliente(monkeypatch, vistos)
    r = c.get("/probe", headers={"Authorization": "Bearer tok-google", "X-QF-Identity": "firebase"})
    assert r.status_code == 200 and r.json() == {"plus": True}
    assert vistos == [("firebase", "tok-google", "firebase")]


def test_sin_la_cabecera_sigue_la_ruta_clasica(monkeypatch):
    vistos = []
    c = _cliente(monkeypatch, vistos)
    r = c.get("/probe", headers={"Authorization": "Bearer tok-clasico"})
    assert r.status_code == 200
    assert vistos == [("clasica", "tok-clasico")]


def test_sin_credenciales_no_es_miembro(monkeypatch):
    c = _cliente(monkeypatch, [])
    assert c.get("/probe").json() == {"plus": False}
