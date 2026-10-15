"""Compras de tienda y cola de Meta contra un Postgres real (db/*.sql aplicados).

Se omite sin `QF_TEST_PG_DSN`. Nunca apuntarlo a producción: crea filas en tablas
que no admiten DELETE.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.comercial import cuentas, meta_capi, suscripciones
from qf.comercial.tiendas import Cobro, TiendaError, compras

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")
NOW = datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


@pytest.fixture(autouse=True)
def _meta_on(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "1")


def _cuenta():
    return cuentas.create_account(f"t-{uuid.uuid4().hex[:10]}@ejemplo.com", "clave-de-prueba-1")


def test_cada_cuenta_tiene_token_de_tienda_unico():
    a, b = _cuenta(), _cuenta()
    assert a["store_account_token"] and b["store_account_token"]
    assert a["store_account_token"] != b["store_account_token"]
    uuid.UUID(a["store_account_token"])


def test_planes_llevan_ids_de_tienda():
    row = db.query_one("SELECT play_product_id, play_base_plan_id, apple_product_id "
                       "FROM plans WHERE plan_code = 'plus_1m'")
    assert row == {"play_product_id": "quantfut_plus", "play_base_plan_id": "plus-1m",
                   "apple_product_id": "quantfut_plus_1m"}


def test_store_transactions_no_admite_update_ni_delete():
    acc = _cuenta()
    with db.conn() as c:
        c.execute("""INSERT INTO store_transactions (store, order_id, original_id, account_id, plan_code,
                     product_id, base_plan_id, period_start, period_end, environment, verified_payload)
                     VALUES ('google_play', %s, 'tok', %s, 'plus_1m', 'quantfut_plus', 'plus-1m',
                             now(), now() + interval '30 days', 'sandbox', '{}')""",
                  (f"GPA.{uuid.uuid4().hex}", acc["account_id"]))
    for sql in ("UPDATE store_transactions SET currency = 'EUR' WHERE account_id = %s",
                "DELETE FROM store_transactions WHERE account_id = %s"):
        with pytest.raises(Exception, match="INMUTABLE"):
            with db.conn() as c:
                c.execute(sql, (acc["account_id"],))


def _cobro(acc, order=None, original=None, start=NOW, end=NOW + timedelta(days=30), **kw):
    base = dict(store="google_play", order_id=order or f"GPA.{uuid.uuid4().hex}",
                original_id=original or f"tok-{uuid.uuid4().hex}",
                account_token=acc["store_account_token"], product_id="quantfut_plus",
                base_plan_id="plus-1m", period_start=start, period_end=end,
                price_micros=54_900_000_000, currency="COP", region_code="CO",
                environment="production", state="activa", payload={})
    return Cobro(**{**base, **kw})


def _eventos(order_id):
    return {r["event_name"] for r in db.query(
        "SELECT event_name FROM meta_events WHERE event_id IN (%s, %s)",
        (f"pur:{order_id}", f"sub:{order_id}"))}


def test_primer_cobro_concede_y_encola_subscribe_y_purchase():
    acc = _cuenta()
    c = _cobro(acc)
    r = compras.aplicar(c, acc["account_id"])
    assert r["estado"] == "concedido" and r["ends_at"] == c.period_end
    assert suscripciones.active_subscription(acc["account_id"])["plan_code"] == "plus_1m"
    assert _eventos(c.order_id) == {"Subscribe", "Purchase"}
    v = db.query_one("SELECT custom_data FROM meta_events WHERE event_id = %s", (f"pur:{c.order_id}",))
    assert v["custom_data"]["value"] == 54900.0 and v["custom_data"]["currency"] == "COP"


def test_mismo_cobro_dos_veces_no_concede_dos_veces():
    acc = _cuenta()
    c = _cobro(acc)
    compras.aplicar(c, acc["account_id"])
    compras.aplicar(c, acc["account_id"])
    assert len(suscripciones.history(acc["account_id"])) == 1


def test_renovacion_solo_encola_purchase_y_encadena_periodo():
    acc = _cuenta()
    first = _cobro(acc)
    compras.aplicar(first, acc["account_id"])
    renewal = _cobro(acc, original=first.original_id, start=first.period_start,
                     end=first.period_end + timedelta(days=30))
    compras.aplicar(renewal, acc["account_id"])
    assert _eventos(renewal.order_id) == {"Purchase"}
    rows = db.query("SELECT period_start, period_end FROM store_transactions WHERE original_id = %s "
                    "ORDER BY period_end", (first.original_id,))
    assert rows[1]["period_start"] == first.period_end


def test_rtdn_antes_que_la_app_resuelve_la_cuenta_por_token():
    acc = _cuenta()
    c = _cobro(acc)
    assert compras.aplicar(c, None)["account_id"] == acc["account_id"]
    assert compras.aplicar(c, acc["account_id"])["estado"] == "concedido"
    assert len(suscripciones.history(acc["account_id"])) == 1


def test_compra_de_otra_cuenta_se_rechaza():
    duena, otra = _cuenta(), _cuenta()
    with pytest.raises(TiendaError) as e:
        compras.aplicar(_cobro(duena), otra["account_id"])
    assert e.value.code == "compra_de_otra_cuenta"


def test_compra_sin_token_de_cuenta_se_rechaza():
    acc = _cuenta()
    with pytest.raises(TiendaError) as e:
        compras.aplicar(_cobro(acc, account_token=None), acc["account_id"])
    assert e.value.code == "compra_sin_cuenta"


def test_compra_de_prueba_concede_pero_no_va_a_meta():
    acc = _cuenta()
    c = _cobro(acc, environment="sandbox")
    assert compras.aplicar(c, acc["account_id"])["estado"] == "concedido"
    assert _eventos(c.order_id) == set()


def test_pendiente_y_sin_acceso_no_conceden():
    acc = _cuenta()
    assert compras.aplicar(_cobro(acc, state="pendiente"), acc["account_id"])["estado"] == "pendiente"
    assert compras.aplicar(_cobro(acc, state="sin_acceso"), acc["account_id"])["estado"] == "sin_acceso"
    assert suscripciones.active_subscription(acc["account_id"]) is None


def test_reembolso_de_una_renovacion_solo_revoca_ese_periodo():
    acc = _cuenta()
    first = _cobro(acc)
    compras.aplicar(first, acc["account_id"])
    renewal = _cobro(acc, original=first.original_id, end=first.period_end + timedelta(days=30))
    compras.aplicar(renewal, acc["account_id"])
    assert compras.revocar_orden("google_play", renewal.order_id, "reembolso Play") is True
    vigentes = [h for h in suscripciones.history(acc["account_id"]) if h["revoked_at"] is None]
    assert len(vigentes) == 1 and vigentes[0]["ends_at"] == first.period_end


def test_producto_desconocido():
    acc = _cuenta()
    with pytest.raises(TiendaError) as e:
        compras.aplicar(_cobro(acc, base_plan_id="plus-99m"), acc["account_id"])
    assert e.value.code == "producto_desconocido"
