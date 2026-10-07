"""Cuentas y suscripciones contra un Postgres real con db/*.sql aplicados.

Se omite sin `QF_TEST_PG_DSN`. Nunca apuntarlo a producción: crea filas en
tablas que no admiten DELETE. Para un clúster desechable:
    initdb -D <tmp> -U qf -A trust && pg_ctl -D <tmp> -o "-p 55433" start
    createdb -p 55433 -U qf quantfut && for f in db/*.sql; do psql ... -f $f; done
"""
import os
import uuid

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.comercial import cuentas, metricas, suscripciones
from qf.comercial.cuentas import CuentaError
from test_cuentas_api import FakeRedis

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


def _email():
    return f"t-{uuid.uuid4().hex[:10]}@Ejemplo.com"


def test_alta_login_y_correo_sin_mayusculas():
    email = _email()
    acc = cuentas.create_account(email, "clave-de-prueba-1", "Ana")
    with pytest.raises(CuentaError) as e:
        cuentas.create_account(email.lower(), "otra-clave-larga", None)
    assert e.value.code == "email_en_uso"
    assert cuentas.authenticate(email.upper(), "clave-de-prueba-1")["account_id"] == acc["account_id"]
    assert cuentas.authenticate(email, "incorrecta-123") is None
    assert cuentas.authenticate("nadie-" + email, "clave-de-prueba-1") is None


def test_refresh_rota_y_el_reuso_revoca_la_sesion():
    r = FakeRedis()
    acc = cuentas.create_account(_email(), "clave-de-prueba-1")
    t1 = cuentas.open_session(r, acc["account_id"], "pytest", "127.0.0.1")
    assert cuentas.account_from_access(r, t1["access_token"])["account_id"] == acc["account_id"]

    t2 = cuentas.rotate_refresh(r, t1["refresh_token"])
    assert t2["refresh_token"] != t1["refresh_token"]
    # Alguien presenta el refresh ya rotado: se corta todo, también el bueno.
    with pytest.raises(CuentaError) as e:
        cuentas.rotate_refresh(r, t1["refresh_token"])
    assert e.value.code == "refresh_reusado"
    with pytest.raises(CuentaError):
        cuentas.rotate_refresh(r, t2["refresh_token"])
    assert cuentas.account_from_access(r, t2["access_token"]) is None


def test_suspender_corta_el_acceso_en_el_acto():
    r = FakeRedis()
    acc = cuentas.create_account(_email(), "clave-de-prueba-1")
    t = cuentas.open_session(r, acc["account_id"], None, None)
    assert cuentas.set_status(acc["account_id"], "suspended", "pytest")
    assert cuentas.account_from_access(r, t["access_token"]) is None
    assert not cuentas.set_status(acc["account_id"], "suspended", "pytest")


def test_renovar_antes_de_tiempo_no_pierde_dias_y_revocar_es_unico():
    acc = cuentas.create_account(_email(), "clave-de-prueba-1")
    aid = acc["account_id"]
    a = suscripciones.grant(aid, "plus_1m", "pytest")
    b = suscripciones.grant(aid, "plus_3m", "pytest", note="renovación")
    assert b["starts_at"] == a["ends_at"]
    assert (b["ends_at"] - b["starts_at"]).days == 90
    assert suscripciones.active_subscription(aid)["subscription_id"] == a["subscription_id"]

    assert suscripciones.revoke(a["subscription_id"], "pytest", "prueba")["account_id"] == aid
    assert suscripciones.revoke(a["subscription_id"], "pytest", "otra vez") is None
    with pytest.raises(CuentaError):
        suscripciones.revoke(b["subscription_id"], "pytest", "  ")


def test_de_por_vida_bloquea_nuevas_concesiones():
    aid = cuentas.create_account(_email(), "clave-de-prueba-1")["account_id"]
    club = suscripciones.grant(aid, "club", "pytest")
    assert club["ends_at"] is None
    with pytest.raises(CuentaError) as e:
        suscripciones.grant(aid, "plus_1m", "pytest")
    assert e.value.code == "ya_de_por_vida"


def test_consultas_del_panel_corren():
    assert metricas.cuentas()["total"] >= 1
    assert "con_plus" in metricas.suscripciones()
    assert len(metricas.serie_diaria(30)) == 30
    assert "picks_sin_liquidar" in metricas.operacion()
    lista = metricas.lista_cuentas(q="ejemplo", filtro="plus")
    assert lista["total"] == len(lista["rows"]) or lista["pages"] > 1
    assert metricas.lista_suscripciones("todas")["total"] >= 1
    assert metricas.auditoria(limit=5)
    assert suscripciones.update_plan("plus_1m", "pytest", active=True, price_cents=1499)


def test_verificacion_por_enlace_de_un_solo_uso():
    acc = cuentas.create_account(_email(), "clave-de-prueba-1")
    viejo = cuentas.issue_email_token(acc["account_id"], "verify")
    token = cuentas.issue_email_token(acc["account_id"], "verify")
    assert not cuentas.email_token_valid(viejo, "verify"), "pedir otro anula el anterior"
    assert not cuentas.email_token_valid(token, "reset"), "un token no vale para otro propósito"
    assert cuentas.confirm_email(token)
    assert not cuentas.confirm_email(token)
    assert metricas.cuenta(acc["account_id"])["email_verified_at"] is not None


def test_restablecer_cambia_la_clave_y_cierra_sesiones():
    r = FakeRedis()
    email = _email()
    acc = cuentas.create_account(email, "clave-de-prueba-1")
    sesion = cuentas.open_session(r, acc["account_id"], None, None)
    token = cuentas.issue_email_token(acc["account_id"], "reset")
    with pytest.raises(CuentaError):
        cuentas.reset_password(token, "corta")
    assert cuentas.email_token_valid(token, "reset"), "un error de validación no gasta el enlace"
    assert cuentas.reset_password(token, "clave-nueva-larga")
    assert not cuentas.reset_password(token, "otra-clave-larga")
    assert cuentas.authenticate(email, "clave-de-prueba-1") is None
    assert cuentas.authenticate(email, "clave-nueva-larga") is not None
    assert cuentas.account_from_access(r, sesion["access_token"]) is None


def test_suspendida_no_recibe_enlace_de_acceso():
    email = _email()
    acc = cuentas.create_account(email, "clave-de-prueba-1")
    assert cuentas.account_for_reset(email.upper())["account_id"] == acc["account_id"]
    cuentas.set_status(acc["account_id"], "suspended", "pytest")
    assert cuentas.account_for_reset(email) is None


def test_gracia_web_no_revoca_dos_pestanas_que_refrescan_a_la_vez():
    r = FakeRedis()
    acc = cuentas.create_account(_email(), "clave-de-prueba-1")
    t1 = cuentas.open_session(r, acc["account_id"], None, None)
    t2 = cuentas.rotate_refresh(r, t1["refresh_token"], grace_seconds=20)
    # La segunda pestaña llega con la cookie vieja dentro de la ventana.
    t3 = cuentas.rotate_refresh(r, t1["refresh_token"], grace_seconds=20)
    assert t3["refresh_token"] is None and t3["access_token"]
    assert cuentas.account_from_access(r, t3["access_token"]) is not None
    # El refresh vigente sigue valiendo: la sesión no se revocó.
    assert cuentas.rotate_refresh(r, t2["refresh_token"])["refresh_token"]
    # Sin gracia (la app), el mismo reuso revoca la sesión entera.
    with pytest.raises(CuentaError) as e:
        cuentas.rotate_refresh(r, t1["refresh_token"])
    assert e.value.code == "refresh_reusado"
