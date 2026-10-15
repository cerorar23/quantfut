"""Cola de Meta contra Postgres real. Se omite sin QF_TEST_PG_DSN."""
import os
import uuid

import httpx
import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.comercial import cuentas, firebase_mantenimiento, meta_capi

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "1")
    monkeypatch.setenv("META_DATASET_ID", "123")
    monkeypatch.setenv("META_CAPI_TOKEN", "t")


def _cuenta():
    return cuentas.create_account(f"t-{uuid.uuid4().hex[:10]}@ejemplo.com", "clave-de-prueba-1")


def _status(event_id):
    return db.query_one("SELECT status, attempts FROM meta_events WHERE event_id = %s", (event_id,))


def test_encolar_es_idempotente_por_event_id():
    acc = _cuenta()
    eid = f"pur:{uuid.uuid4().hex}"
    with db.conn() as c:
        assert meta_capi.enqueue(c, acc["account_id"], "Purchase", eid, {"value": 1.0}) is True
        assert meta_capi.enqueue(c, acc["account_id"], "Purchase", eid, {"value": 1.0}) is False


def test_apagado_no_encola(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "0")
    acc = _cuenta()
    with db.conn() as c:
        assert meta_capi.enqueue(c, acc["account_id"], "Purchase", f"pur:{uuid.uuid4().hex}") is False


def test_quien_desactivo_meta_no_se_encola():
    acc = _cuenta()
    db.execute("INSERT INTO firebase_preferences (account_id, ads_measurement) VALUES (%s, false)",
               (acc["account_id"],))
    with db.conn() as c:
        assert meta_capi.enqueue(c, acc["account_id"], "Purchase", f"pur:{uuid.uuid4().hex}") is False


def test_quien_nunca_eligio_se_encola():
    acc = _cuenta()
    db.execute("INSERT INTO firebase_preferences (account_id) VALUES (%s)", (acc["account_id"],))
    with db.conn() as c:
        assert meta_capi.enqueue(c, acc["account_id"], "Purchase", f"pur:{uuid.uuid4().hex}") is True


def test_desactivar_despues_de_encolar_omite_el_envio():
    acc = _cuenta()
    eid = f"pur:{uuid.uuid4().hex}"
    with db.conn() as c:
        meta_capi.enqueue(c, acc["account_id"], "Purchase", eid)
    db.execute("""INSERT INTO firebase_preferences (account_id, ads_measurement) VALUES (%s, false)
                  ON CONFLICT (account_id) DO UPDATE SET ads_measurement = false""",
               (acc["account_id"],))
    client = httpx.Client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"events_received": 1})))
    meta_capi.send_pending(client=client)
    assert _status(eid)["status"] == "omitido"


def test_fallo_de_meta_reintenta_y_marca_fallido_al_quinto(monkeypatch):
    alerts = []
    monkeypatch.setattr(meta_capi, "_alert", alerts.append)
    acc = _cuenta()
    eid = f"pur:{uuid.uuid4().hex}"
    with db.conn() as c:
        meta_capi.enqueue(c, acc["account_id"], "Purchase", eid)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500, json={})))
    for _ in range(5):
        meta_capi.send_pending(client=client)
    assert _status(eid) == {"status": "fallido", "attempts": 5}
    # Avisa al tercer intento; `>= 1` porque la base de pruebas puede traer otros eventos.
    assert len(alerts) >= 1


def test_alta_por_correo_encola_complete_registration():
    acc = _cuenta()
    row = db.query_one("SELECT event_name, custom_data FROM meta_events WHERE event_id = %s",
                       (f"reg:{acc['account_id']}",))
    assert row == {"event_name": "CompleteRegistration",
                   "custom_data": {"registration_method": "email"}}


def test_alta_con_google_encola_complete_registration(monkeypatch):
    from qf.comercial import firebase
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "pytest-proj")
    claims = {"uid": uuid.uuid4().hex, "email": f"g-{uuid.uuid4().hex[:8]}@ejemplo.com",
              "email_verified": True, "name": "Ana Pérez",
              "firebase": {"sign_in_provider": "google.com"}}
    acc = firebase.connect_identity(claims, firebase.CONSENT_VERSION, firebase.CONSENT_VERSION, "es")
    row = db.query_one("SELECT custom_data FROM meta_events WHERE event_id = %s",
                       (f"reg:{acc['account_id']}",))
    assert row == {"custom_data": {"registration_method": "google"}}


def test_limpieza_borra_dispositivos_y_eventos_terminados_antiguos():
    acc = _cuenta()
    db.execute("""INSERT INTO meta_identities (account_id, anon_id, platform, advertiser_tracking_enabled,
                      extinfo, updated_at)
                  VALUES (%s, 'viejo', 'android', false, '[]', now() - interval '91 days'),
                         (%s, 'nuevo', 'android', false, '[]', now())""",
               (acc["account_id"], acc["account_id"]))
    eid = f"pur:{uuid.uuid4().hex}"
    db.execute("""INSERT INTO meta_events (event_id, account_id, event_name, status, created_at)
                  VALUES (%s, %s, 'Purchase', 'enviado', now() - interval '91 days')""",
               (eid, acc["account_id"]))
    out = firebase_mantenimiento.clean()
    assert out["meta_identities"] >= 1 and out["meta_events"] >= 1
    left = db.query("SELECT anon_id FROM meta_identities WHERE account_id = %s", (acc["account_id"],))
    assert [r["anon_id"] for r in left] == ["nuevo"]
    assert _status(eid) is None
