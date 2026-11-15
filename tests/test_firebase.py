"""Security boundaries of the Firebase/legacy identity bridge."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from qf.api import cuentas as accounts_api, firebase as api
from qf.comercial import cuentas, firebase
from qf.comercial.cuentas import CuentaError
from qf.comercial.firebase_notificaciones import enqueue, message_for


def request(headers=None):
    return Request({"type":"http", "headers":[(key.lower().encode(), value.encode())
                    for key, value in (headers or {}).items()]})


def test_firebase_tokens_require_explicit_identity_header(monkeypatch):
    legacy = []
    monkeypatch.setattr(accounts_api, "redis_client", lambda: object())
    monkeypatch.setattr(cuentas, "account_from_access", lambda redis, token: legacy.append(token) or None)
    monkeypatch.setattr(firebase, "verify_identity", lambda token: pytest.fail("must not guess JWT provider"))
    with pytest.raises(Exception) as error:
        accounts_api.current_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials="firebase-looking-token"), request())
    assert error.value.status_code == 401
    assert legacy == ["firebase-looking-token"]


def test_firebase_identity_preserves_account_permissions(monkeypatch):
    monkeypatch.setattr(api, "check_app_token", lambda req: None)
    monkeypatch.setattr(firebase, "verify_identity", lambda token: {"uid":"verified"})
    monkeypatch.setattr(firebase, "identity_account", lambda claims: {"account_id":7,"status":"active"})
    monkeypatch.setattr(cuentas, "account_from_access", lambda *args: pytest.fail("no fallback to opaque token"))
    account = accounts_api.current_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials="verified-id-token"),
                                          request({"X-QF-Identity":"firebase"}))
    assert account["account_id"] == 7 and account["_identity"] == "firebase"
    assert "plus" not in account  # Entitlements remain the database's decision.


def test_disabled_or_unknown_local_account_rejected(monkeypatch):
    monkeypatch.setattr(api, "check_app_token", lambda req: None)
    monkeypatch.setattr(firebase, "verify_identity", lambda token: {"uid":"valid"})
    monkeypatch.setattr(firebase, "identity_account", lambda claims: None)
    with pytest.raises(Exception) as error:
        api.firebase_account(HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid"), request())
    assert error.value.status_code == 401


def test_check_revocation_and_project_required(monkeypatch):
    from firebase_admin import auth
    monkeypatch.setenv("FIREBASE_AUTH_ENABLED", "1")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "our-project")
    monkeypatch.setattr(firebase, "admin_app", lambda: "admin-app")
    calls = []
    monkeypatch.setattr(auth, "verify_id_token", lambda token, **kw: calls.append(kw) or {"aud":"wrong-project","uid":"user"})
    with pytest.raises(CuentaError, match="Sesión no válida"):
        firebase.verify_identity("untrusted")
    assert calls == [{"app":"admin-app", "check_revoked":True}]


def test_revoked_firebase_token_has_no_legacy_fallback(monkeypatch):
    from firebase_admin import auth
    monkeypatch.setenv("FIREBASE_AUTH_ENABLED", "1")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "our-project")
    monkeypatch.setattr(firebase, "admin_app", lambda: object())
    def revoked(*args, **kwargs):
        raise auth.RevokedIdTokenError("revoked")
    monkeypatch.setattr(auth, "verify_id_token", revoked)
    with pytest.raises(CuentaError) as error:
        firebase.verify_identity("revoked-token")
    assert error.value.code == "firebase_token_invalido"


def test_google_email_must_be_verified_before_database(monkeypatch):
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "our-project")
    monkeypatch.setattr(firebase, "conn", lambda: pytest.fail("unverified identity must not reach DB"))
    with pytest.raises(CuentaError) as error:
        firebase.connect_identity({"email":"u@example.com","uid":"uid","email_verified":False},
                                  firebase.CONSENT_VERSION, firebase.CONSENT_VERSION, "es")
    assert error.value.code == "firebase_correo_no_verificado"


def test_connect_rejects_invalid_legacy_proof_without_linking(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    monkeypatch.setattr(accounts_api, "_limit", lambda *args: None)
    monkeypatch.setattr(api, "check_app_token", lambda req: None)
    monkeypatch.setattr(accounts_api, "redis_client", lambda: object())
    monkeypatch.setattr(cuentas, "account_from_access", lambda *args: None)
    monkeypatch.setattr(firebase, "connect_identity", lambda *args: pytest.fail("bad proof must not link"))
    app = FastAPI(); app.include_router(api.router)
    client = TestClient(app)
    result = client.post("/app/v1/firebase/connect", json={"id_token":"id"}, headers={"Authorization":"Bearer forged"})
    assert result.status_code == 401


def test_appcheck_observation_and_enforcement(monkeypatch):
    monkeypatch.setenv("FIREBASE_APPCHECK_ENFORCE", "0")
    api.check_app_token(request())
    monkeypatch.setenv("FIREBASE_APPCHECK_ENFORCE", "1")
    with pytest.raises(Exception) as error:
        api.check_app_token(request())
    assert error.value.status_code == 403


def test_unregistered_routes_do_not_expose_notifications(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    monkeypatch.setattr(api, "query", lambda *args: pytest.fail("no unauthenticated DB read"))
    app = FastAPI(); app.include_router(api.router)
    client = TestClient(app)
    assert client.get("/app/v1/firebase/notifications").status_code == 401
    assert client.get("/app/v1/firebase/preferences").status_code == 401


def test_notification_payload_does_not_leak_pick_or_external_url():
    row={"token":"private-device-token","language":"en","notification_id":17,
         "match_id":"match-1","expires_at":datetime.now(timezone.utc)+timedelta(minutes=10),
         "selection":"secret pick", "url":"https://untrusted.example"}
    message=message_for(row)
    assert message.data == {"event_id":"17","route":"match","match_id":"match-1"}
    assert message.android.notification.channel_id == "quantfut_predictions"
    assert "secret pick" not in message.notification.body
    assert "selection" not in message.data and "url" not in message.data


def test_expired_notifications_cannot_be_enqueued():
    with pytest.raises(ValueError, match="future"):
        enqueue(7,"publication",datetime.now(timezone.utc)-timedelta(minutes=1))
    with pytest.raises(ValueError, match="identifier"):
        enqueue(7,"publication",datetime.now(timezone.utc)+timedelta(hours=1),"https://wrong.example")


def test_version_anterior_de_consentimiento_se_acepta_en_la_transicion():
    from qf.comercial import firebase
    assert firebase.CONSENT_VERSION == "2026-10-16"
    assert {"2026-10-12", "2026-10-16"} <= firebase.ACCEPTED_CONSENT_VERSIONS


def _web_client(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    monkeypatch.setattr(accounts_api, "redis_client", lambda: object())
    monkeypatch.setattr(accounts_api, "_limit", lambda *args: None)
    monkeypatch.setattr(accounts_api, "settings", type("S", (), {"app_env": "development"})())
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def test_web_config_closed_until_configured(monkeypatch):
    client = _web_client(monkeypatch)
    for name in ("FIREBASE_AUTH_ENABLED", "FIREBASE_WEB_API_KEY", "FIREBASE_WEB_APP_ID", "FIREBASE_WEB_AUTH_DOMAIN"):
        monkeypatch.delenv(name, raising=False)
    assert client.get("/app/v1/firebase/web-config").status_code == 503
    monkeypatch.setenv("FIREBASE_AUTH_ENABLED", "1")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "proj")
    monkeypatch.setenv("FIREBASE_WEB_API_KEY", "key")
    monkeypatch.setenv("FIREBASE_WEB_APP_ID", "1:2:web:3")
    monkeypatch.setenv("FIREBASE_WEB_AUTH_DOMAIN", "proj.firebaseapp.com")
    body = client.get("/app/v1/firebase/web-config").json()
    assert body["projectId"] == "proj" and body["apiKey"] == "key"


def test_web_session_sets_cookie_and_requires_consent_for_new_accounts(monkeypatch):
    client = _web_client(monkeypatch)
    seen = []
    monkeypatch.setattr(firebase, "verify_identity", lambda token: {"uid": "u"})
    def connect(claims, terms, privacy, language, existing=None, web_context=None):
        seen.append((terms, privacy))
        if terms is None:
            raise CuentaError("consentimiento_requerido", "Acepta los términos")
        return {"account_id": 5}
    monkeypatch.setattr(firebase, "connect_identity", connect)
    monkeypatch.setattr(cuentas, "open_session", lambda *a: {"access_token": "acc", "refresh_token": "ref",
                                                             "token_type": "bearer", "expires_in": 900})
    headers = {"X-QF-Client": "web"}
    refused = client.post("/app/v1/firebase/web-session", json={"id_token": "t"}, headers=headers)
    assert refused.status_code == 409 and refused.json()["detail"]["code"] == "consentimiento_requerido"
    ok = client.post("/app/v1/firebase/web-session", json={"id_token": "t", "accepted_terms": True}, headers=headers)
    assert ok.status_code == 200 and ok.json()["refresh_token"] is None
    assert "qf_refresh" in ok.cookies
    assert seen[-1] == (firebase.CONSENT_VERSION, firebase.CONSENT_VERSION)


class _Cur:
    def __init__(self, log, row=None):
        self.log, self.row = log, row

    def execute(self, sql, params=()):
        self.log.append((" ".join(sql.split()), params))
        return self

    def fetchone(self):
        return self.row


class _Conn:
    def __init__(self, log, row=None):
        self.cur = _Cur(log, row)

    def __enter__(self):
        return self.cur

    def __exit__(self, *exc):
        return False


def test_preferencias_push_por_deporte_validan_y_no_pisan_apps_antiguas(monkeypatch):
    from pydantic import ValidationError
    assert api.PreferencesIn().push_sports is None
    assert api.PreferencesIn(push_sports=["nba", "tenis"]).push_sports == ["nba", "tenis"]
    with pytest.raises(ValidationError):
        api.PreferencesIn(push_sports=["cricket"])
    log = []
    monkeypatch.setattr(api, "conn", lambda: _Conn(log))
    account = {"account_id": 7}
    api.save_preferences(api.PreferencesIn(push_enabled=True), account)
    insert = log[0]
    assert insert[1][-2:] == (None, False)          # app antigua: no se toca lo guardado
    api.save_preferences(api.PreferencesIn(push_enabled=True, push_sports=["tenis", "nba", "nba"]), account)
    assert log[1][1][-2:] == (["nba", "tenis"], True)
    api.save_preferences(api.PreferencesIn(push_enabled=True, push_sports=[]), account)
    assert log[2][1][-2:] == ([], True)             # lista vacía = ningún deporte


def test_preferencias_get_devuelve_todos_los_deportes_si_no_hay_filtro(monkeypatch):
    seen = []
    monkeypatch.setattr(api, "query_one", lambda sql, params: seen.append(params) or None)
    assert api.preferences({"account_id": 7})["push_sports"] == ["futbol", "nba", "tenis"]
    assert seen[0][0] == ["futbol", "nba", "tenis"]


def test_enqueue_filtra_por_deporte_y_rechaza_deporte_invalido(monkeypatch):
    from qf.comercial import firebase_notificaciones as notif
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    with pytest.raises(ValueError, match="sport"):
        enqueue(7, "k", future, sport="cricket")
    log = []
    monkeypatch.setattr(notif, "conn", lambda: _Conn(log, {"notification_id": 9, "language": "es"}))
    assert enqueue(7, "k", future, "match-1", sport="nba") == 9
    insert_notif, insert_outbox = log[1], log[2]
    assert insert_notif[1][-1] == "nba"
    assert "p.push_sports IS NULL OR %s::text = ANY(p.push_sports)" in insert_outbox[0]
    assert insert_outbox[1] == (9, 7, "nba", "nba")


def test_entrega_vuelve_a_comprobar_el_deporte():
    import inspect
    from qf.comercial import firebase_notificaciones as notif
    assert "n.sport = ANY(p.push_sports)" in " ".join(inspect.getsource(notif.deliver).split())
