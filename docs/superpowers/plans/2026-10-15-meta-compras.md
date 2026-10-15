# Meta (App Events + CAPI) y suscripciones en la app — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vender QuantFut Plus como suscripción renovable de Google Play / App Store, con el acceso decidido solo por el servidor tras verificar con la tienda, y mandar a Meta instalación, embudo y cobros reales (SDK + Conversions API) con la mejor coincidencia posible.

**Architecture:** El servidor es la única fuente de los eventos de valor: verifica cada cobro con la tienda (`purchases.subscriptionsv2` / JWS de Apple), concede con una fila nueva en `subscriptions` (que solo admite revocar), guarda el cobro en `store_transactions` (solo inserción) y encola `Subscribe`/`Purchase` en `meta_events`, que un trabajo periódico envía por CAPI (`action_source=app`). La app solo registra con el SDK lo que únicamente ella conoce (ver contenido, buscar, pulsar comprar…) y manda a la API los identificadores del dispositivo (`anon_id`, `madid`, `extinfo`).

**Tech Stack:** Python 3.12, FastAPI, psycopg 3, httpx, google-auth (ya instalado vía firebase-admin), `app-store-server-library` 3.1.2; Flutter con `in_app_purchase` ^3.3.1, `facebook_app_events` ^0.31.0, `app_tracking_transparency` ^2.0.7, `package_info_plus`.

**Spec:** `docs/superpowers/specs/2026-10-15-meta-compras-design.md`

## Global Constraints

- Todo llega **apagado**: `STORE_PURCHASES_ENABLED=0`, `META_CAPI_ENABLED=0` en el servidor; `QF_META_ENABLED=false` (dart-define) en la app hasta tener credenciales.
- El token de CAPI, el JSON de la cuenta de servicio de Play y la clave `.p8` de Apple viven **solo** en el servidor (`.env` / ficheros montados). Nunca en la app, en el repo ni en el chat.
- No tocar los triggers de `subscriptions` (`db/043`) ni de ninguna tabla inmutable. Las migraciones son **aditivas** (`db/071`).
- La app nunca escribe `plus`, vigencia ni plan; `completePurchase()` solo tras la respuesta `concedido` (o `sin_acceso`) del servidor.
- Ningún evento sale a la vez del SDK y del servidor. Registro automático de compras del SDK: apagado.
- Seguimiento (Analytics, diagnóstico, Meta) **encendido por defecto en todo el mundo**; una negativa explícita previa se conserva (`getBool(...) ?? true`, nunca sobrescribir un `false` guardado).
- Cualquier texto visible nuevo en la app va en los 6 idiomas (es, en, pt, fr, it, de) en el mismo cambio con `python apps/mobile/tool/l10n_add.py`; mensajes de error de la API en `src/qf/api/mensajes.py` (orden de la tupla: en, pt, fr, it, de).
- Graph API fijada a `v24.0`. Paquete Android/bundle iOS: `com.saptain.quantfut`.
- IDs de tienda: Play `quantfut_plus` con planes base `plus-1m`, `plus-3m`, `plus-6m`; Apple `quantfut_plus_1m`, `quantfut_plus_3m`, `quantfut_plus_6m`.
- Nueva versión de consentimiento: `2026-10-16`; el servidor acepta `2026-10-12` y `2026-10-16` durante la transición.
- Trabajar en una rama propia (`feat/meta-compras`) en su propio `git worktree`: en `main` hay cambios sin confirmar de otras sesiones. No desplegar nada: el despliegue es después del 1-nov y sigue `DEPLOYS.md`.
- Python del proyecto: `.venv/Scripts/python.exe` con `PYTHONPATH=src`. Flutter: `C:\flutter\bin\flutter.bat` (no está en el PATH), ejecutado desde `apps/mobile`.
- Pruebas con PostgreSQL: necesitan `QF_TEST_PG_DSN` apuntando a una base **desechable** con el esquema aplicado (`PGBASE=... .venv/Scripts/python.exe scripts/ci_aplicar_esquema.py` crea `qf_test`). Nunca contra producción.

## Review Focus

1. **La notificación RTDN llega antes que la llamada de la app.** El servidor debe resolver la cuenta por `obfuscatedExternalAccountId` → `accounts.store_account_token` y conceder igual; la llamada posterior de la app devuelve lo ya concedido. (Prueba en Task 7.)
2. **Usuario con Plus vigente pulsa otro plan.** La app no lanza una compra nueva (Play exigiría cambio de plan); enseña el enlace de gestión de la tienda. (Prueba en Task 13.)
3. **Reembolso de una sola renovación.** Solo se revoca la fila de `subscriptions` ligada a ese `order_id`; los demás periodos siguen. (Prueba en Task 7.)
4. **Compra de prueba (tester con licencia) en producción.** Concede acceso pero no se manda a Meta (`environment='sandbox'`). (Prueba en Task 7.)
5. **Moneda sin decimales (COP, CLP, JPY).** El valor que recibe Meta es `price_micros / 1e6` exacto, nunca derivado de `price_cents`. (Prueba en Task 3.)

---

## Mapa de archivos

**Servidor (crear)**
- `db/071_meta_compras.sql` — tablas `store_transactions`, `meta_events`, `meta_identities`; columnas de tienda en `plans`; `accounts.store_account_token`; `firebase_preferences.ads_measurement`.
- `src/qf/comercial/meta_datos.py` — normalización y SHA-256 de `user_data`, `external_id`, validación de `extinfo` (puro, sin BD).
- `src/qf/comercial/meta_capi.py` — encolar (en la transacción del hecho), construir el evento y enviar por CAPI; ejecutable como trabajo periódico.
- `src/qf/comercial/tiendas/__init__.py` — `Cobro`, `TiendaError`.
- `src/qf/comercial/tiendas/google_play.py` — consulta y reconocimiento con la Play Developer API; parseo.
- `src/qf/comercial/tiendas/app_store.py` — verificación JWS con la librería oficial de Apple; parseo.
- `src/qf/comercial/tiendas/compras.py` — aplicar un cobro verificado (idempotente) y revocar.
- `src/qf/api/compras.py` — `POST /app/v1/compras/verificar`, `/google/rtdn`, `/apple/notificaciones`.
- `src/qf/api/meta.py` — `POST /app/v1/meta/dispositivo`.
- Pruebas: `tests/test_meta_datos.py`, `tests/test_meta_capi.py`, `tests/test_meta_capi_pg.py`, `tests/test_tiendas.py`, `tests/test_compras_pg.py`, `tests/test_compras_api.py`, `tests/test_meta_api.py`, `tests/fixtures/play_subscription_v2.json`.

**Servidor (modificar)**
- `src/qf/comercial/suscripciones.py` — `grant_store()`, `revoke_in()`; `plans()` devuelve los IDs de tienda.
- `src/qf/comercial/cuentas.py` — `_PUBLIC` incluye `store_account_token`; `create_account` encola `CompleteRegistration`.
- `src/qf/comercial/firebase.py` — versión de consentimiento nueva y aceptación de la anterior; encolar `CompleteRegistration` al crear cuenta con Google.
- `src/qf/api/cuentas.py` — `MeOut` con `store_account_token` y `meta_external_id`; `PlanOut` con IDs de tienda.
- `src/qf/api/firebase.py` — `PreferencesIn.ads_measurement`.
- `src/qf/api/rewards.py` — encolar `SpentCredits` al desbloquear.
- `src/qf/api/main.py` — registrar routers nuevos.
- `src/qf/api/mensajes.py` — mensajes de compra en 6 idiomas.
- `requirements.txt`, `.env.example`, `scripts/crontab`.
- `docs/legal/PRIVACIDAD_QUANTFUT.md`, `docs/legal/TERMINOS_QUANTFUT.md`, `src/qf/api/legal_pages/*.html` (regeneradas).

**App (crear)**
- `apps/mobile/lib/core/meta_events.dart` — fachada del SDK de Meta con inicio controlado por el ajuste, eventos del mapa y datos del dispositivo.
- `apps/mobile/lib/product/store_purchases.dart` — `StoreController` sobre `in_app_purchase`.
- `apps/mobile/android/meta.properties.example`, `apps/mobile/ios/Flutter/Meta.xcconfig`.
- `apps/mobile/ios/Runner/{es,en,pt,fr,it,de}.lproj/InfoPlist.strings`.
- Pruebas: `apps/mobile/test/meta_events_test.dart`, `apps/mobile/test/store_purchases_test.dart`, `apps/mobile/test/consent_defaults_test.dart`.

**App (modificar)**
- `apps/mobile/pubspec.yaml`, `android/app/build.gradle`, `android/app/src/main/AndroidManifest.xml`, `MainActivity.kt`, `ios/Runner/Info.plist`, `ios/Flutter/{Debug,Release}.xcconfig`.
- `lib/core/firebase_services.dart` (valores por defecto y ajuste de Meta), `lib/core/firebase_startup.dart`, `lib/core/firebase_preferences.dart`.
- `lib/product/live_api.dart` (verificar compra, dispositivo, versión de consentimiento), `live_shell.dart`, `live_vip.dart`, `live_detail.dart`, `live_home.dart`, `live_guide.dart`, `live_ads.dart`, `live_rewards.dart`.
- `lib/l10n/app_*.arb` (vía `l10n_add.py`).

**Documentación**
- `apps/mobile/docs/META_COMPRAS_TITULAR.md` (guía de consolas para el titular), `harness/tareas.md`, `harness/progreso.md`, `PENDIENTES.md`.

---

## Task 0: Rama y carpeta de trabajo

**Files:** ninguno de código.

- [ ] **Step 1: Crear el worktree desde `main`**

```bash
cd "C:/Users/huye/Documents/apuesta proyec"
git worktree add ../quantfut-meta-compras -b feat/meta-compras main
```

- [ ] **Step 2: Copiar la spec y este plan (no están en `main` todavía) y confirmarlos**

```bash
cp docs/superpowers/specs/2026-10-15-meta-compras-design.md ../quantfut-meta-compras/docs/superpowers/specs/
mkdir -p ../quantfut-meta-compras/docs/superpowers/plans
cp docs/superpowers/plans/2026-10-15-meta-compras.md ../quantfut-meta-compras/docs/superpowers/plans/
cd ../quantfut-meta-compras
git add docs/superpowers/specs/2026-10-15-meta-compras-design.md docs/superpowers/plans/2026-10-15-meta-compras.md
git commit -m "Meta y compras: spec y plan de implementación"
```

- [ ] **Step 3: Comprobar el arnés en el worktree**

Run: `./scripts/harness_check.sh` (crear antes el venv del worktree o reutilizar el del repo con `PY=../apuesta\ proyec/.venv/Scripts/python.exe`).
Expected: `OK. El repo está en buen estado.`

Todas las rutas del resto del plan son relativas al worktree.

---

## Task 1: Migración `db/071`

**Files:**
- Create: `db/071_meta_compras.sql`
- Test: `tests/test_compras_pg.py` (solo las pruebas de esquema en esta tarea)

**Interfaces:**
- Produces: tablas `store_transactions(store, order_id, original_id, account_id, plan_code, product_id, base_plan_id, period_start, period_end, price_micros, currency, region_code, environment, subscription_id, verified_payload, created_at)` con UNIQUE `(store, order_id)` e inmutable; `meta_events(event_id PK, account_id, event_name, event_time, custom_data, status, attempts, last_error, created_at, sent_at)`; `meta_identities(account_id, anon_id, platform, madid, advertiser_tracking_enabled, extinfo, client_ip, user_agent, updated_at)` PK `(account_id, anon_id)`; `plans.play_product_id/play_base_plan_id/apple_product_id`; `accounts.store_account_token UUID UNIQUE NOT NULL`; `firebase_preferences.ads_measurement BOOLEAN NULL` (NULL = nunca eligió = activo).

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_compras_pg.py`:

```python
"""Compras de tienda y cola de Meta contra un Postgres real (db/*.sql aplicados).

Se omite sin `QF_TEST_PG_DSN`. Nunca apuntarlo a producción: crea filas en tablas
que no admiten DELETE.
"""
import os
import uuid

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.comercial import cuentas

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


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
                     product_id, period_start, period_end, environment, verified_payload)
                     VALUES ('google_play', %s, 'tok', %s, 'plus_1m', 'quantfut_plus',
                             now(), now() + interval '30 days', 'sandbox', '{}')""",
                  (f"GPA.{uuid.uuid4().hex}", acc["account_id"]))
    for sql in ("UPDATE store_transactions SET currency = 'EUR' WHERE account_id = %s",
                "DELETE FROM store_transactions WHERE account_id = %s"):
        with pytest.raises(Exception, match="INMUTABLE"):
            with db.conn() as c:
                c.execute(sql, (acc["account_id"],))
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src QF_TEST_PG_DSN=postgresql://.../qf_test .venv/Scripts/python.exe -m pytest tests/test_compras_pg.py -v`
Expected: FAIL (`KeyError: 'store_account_token'` y `relation "store_transactions" does not exist`).

- [ ] **Step 3: Escribir la migración**

`db/071_meta_compras.sql`:

```sql
-- Suscripciones de Google Play / App Store y eventos para Meta (2026-10-15).
-- Spec: docs/superpowers/specs/2026-10-15-meta-compras-design.md. Aditiva: no toca
-- los triggers de subscriptions (db/043), que solo admite revocar.

ALTER TABLE plans ADD COLUMN IF NOT EXISTS play_product_id   TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS play_base_plan_id TEXT;
ALTER TABLE plans ADD COLUMN IF NOT EXISTS apple_product_id  TEXT;
UPDATE plans SET play_product_id = 'quantfut_plus', play_base_plan_id = 'plus-1m',
                 apple_product_id = 'quantfut_plus_1m' WHERE plan_code = 'plus_1m';
UPDATE plans SET play_product_id = 'quantfut_plus', play_base_plan_id = 'plus-3m',
                 apple_product_id = 'quantfut_plus_3m' WHERE plan_code = 'plus_3m';
UPDATE plans SET play_product_id = 'quantfut_plus', play_base_plan_id = 'plus-6m',
                 apple_product_id = 'quantfut_plus_6m' WHERE plan_code = 'plus_6m';
CREATE UNIQUE INDEX IF NOT EXISTS plans_play_ids ON plans (play_product_id, play_base_plan_id)
    WHERE play_product_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS plans_apple_id ON plans (apple_product_id)
    WHERE apple_product_id IS NOT NULL;

-- UUID opaco que la app pasa como obfuscatedAccountId (Play) y appAccountToken (StoreKit 2).
-- Liga cada compra a una cuenta sin dar a la tienda datos personales.
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS store_account_token UUID NOT NULL DEFAULT gen_random_uuid();
CREATE UNIQUE INDEX IF NOT EXISTS accounts_store_account_token ON accounts (store_account_token);

-- NULL = la persona nunca eligió = activo (decisión del titular, 2026-10-15).
ALTER TABLE firebase_preferences ADD COLUMN IF NOT EXISTS ads_measurement BOOLEAN;

CREATE TABLE IF NOT EXISTS store_transactions (
    store            TEXT NOT NULL CHECK (store IN ('google_play', 'app_store')),
    order_id         TEXT NOT NULL,              -- orderId de Play / transactionId de Apple
    original_id      TEXT NOT NULL,              -- purchaseToken / originalTransactionId
    account_id       BIGINT NOT NULL REFERENCES accounts(account_id),
    plan_code        TEXT NOT NULL REFERENCES plans(plan_code),
    product_id       TEXT NOT NULL,
    base_plan_id     TEXT,
    period_start     TIMESTAMPTZ NOT NULL,
    period_end       TIMESTAMPTZ NOT NULL,
    price_micros     BIGINT CHECK (price_micros IS NULL OR price_micros >= 0),
    currency         TEXT CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$'),
    region_code      TEXT,
    environment      TEXT NOT NULL CHECK (environment IN ('production', 'sandbox')),
    subscription_id  BIGINT REFERENCES subscriptions(subscription_id),
    verified_payload JSONB NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (store, order_id),
    CHECK (period_end > period_start)
);
CREATE INDEX IF NOT EXISTS store_transactions_original ON store_transactions (store, original_id, period_end);
CREATE INDEX IF NOT EXISTS store_transactions_account ON store_transactions (account_id, created_at);

CREATE OR REPLACE FUNCTION store_transactions_inmutable() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'REGISTRO INMUTABLE: store_transactions no admite %', TG_OP;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS store_transactions_inmutable ON store_transactions;
CREATE TRIGGER store_transactions_inmutable BEFORE UPDATE OR DELETE ON store_transactions
    FOR EACH ROW EXECUTE FUNCTION store_transactions_inmutable();

-- Cola de Conversions API. event_id determinista (reg:/sub:/pur:/spend:) = idempotencia.
CREATE TABLE IF NOT EXISTS meta_events (
    event_id    TEXT PRIMARY KEY,
    account_id  BIGINT NOT NULL REFERENCES accounts(account_id),
    event_name  TEXT NOT NULL,
    event_time  TIMESTAMPTZ NOT NULL DEFAULT now(),
    custom_data JSONB NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'pendiente'
                CHECK (status IN ('pendiente', 'enviado', 'omitido', 'fallido')),
    attempts    INTEGER NOT NULL DEFAULT 0,
    last_error  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS meta_events_pendientes ON meta_events (created_at) WHERE status = 'pendiente';

-- Datos operativos del dispositivo para user_data/app_data de CAPI. Entra en la limpieza
-- programada de datos operativos (docs/legal/OPERACION_PRIVACIDAD.md).
CREATE TABLE IF NOT EXISTS meta_identities (
    account_id  BIGINT NOT NULL REFERENCES accounts(account_id),
    anon_id     TEXT NOT NULL,
    platform    TEXT NOT NULL CHECK (platform IN ('android', 'ios')),
    madid       TEXT,
    advertiser_tracking_enabled BOOLEAN NOT NULL,
    extinfo     JSONB NOT NULL,
    client_ip   TEXT,
    user_agent  TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, anon_id)
);
CREATE INDEX IF NOT EXISTS meta_identities_reciente ON meta_identities (account_id, updated_at DESC);
```

- [ ] **Step 4: Exponer el token en las cuentas**

En `src/qf/comercial/cuentas.py` línea 62, sustituir `_PUBLIC`:

```python
_PUBLIC = ("account_id, email::text AS email, display_name, status, email_verified_at, created_at, "
           "store_account_token::text AS store_account_token")
```

(`firebase.identity_account` antepone `a.` a cada parte separada por comas: `a.store_account_token::text AS store_account_token` es SQL válido.)

- [ ] **Step 5: Aplicar el esquema a la base desechable y ejecutar**

Run: `PGBASE=postgresql://... .venv/Scripts/python.exe scripts/ci_aplicar_esquema.py` y después el pytest del Step 2.
Expected: 3 PASS.

- [ ] **Step 6: Suite rápida sin BD (el cambio de `_PUBLIC` no rompe nada)**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_cuentas_api.py tests/test_firebase.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add db/071_meta_compras.sql src/qf/comercial/cuentas.py tests/test_compras_pg.py
git commit -m "db/071: transacciones de tienda, cola de Meta y token de cuenta para compras"
```

---

## Task 2: Normalización y hash de datos para Meta

**Files:**
- Create: `src/qf/comercial/meta_datos.py`
- Test: `tests/test_meta_datos.py`

**Interfaces:**
- Produces:
  - `sha256(value: str) -> str`
  - `external_id(account_id: int) -> str` — `sha256(f"qf:{account_id}")`, ya en hex; se manda tal cual (no se vuelve a cifrar) y es el mismo valor que recibe `setUserID` en la app.
  - `split_name(display_name: str | None) -> tuple[str | None, str | None]`
  - `user_data(account: dict, identity: dict | None, country: str | None) -> dict`
  - `valid_extinfo(values: list[str], platform: str) -> list[str]` (lanza `ValueError`)
  - `EXTINFO_LEN = 16`

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_meta_datos.py`:

```python
"""Normalización de user_data según «Customer information parameters» de Meta."""
import hashlib

import pytest

from qf.comercial import meta_datos as m


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def test_email_se_recorta_y_pasa_a_minusculas_antes_del_hash():
    ud = m.user_data({"account_id": 7, "email": "  Ana.Perez@Ejemplo.COM ", "display_name": None},
                     None, None)
    assert ud["em"] == [h("ana.perez@ejemplo.com")]


def test_external_id_es_estable_y_no_se_cifra_dos_veces():
    assert m.external_id(7) == h("qf:7")
    ud = m.user_data({"account_id": 7, "email": "a@b.co", "display_name": None}, None, None)
    assert ud["external_id"] == [h("qf:7")]


def test_nombre_se_parte_por_el_primer_espacio_sin_puntuacion():
    assert m.split_name("José  María O'Neil") == ("josé", "maría oneil")
    assert m.split_name("Ana") == ("ana", None)
    assert m.split_name("  ") == (None, None)
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": "Ana Pérez"}, None, None)
    assert ud["fn"] == [h("ana")] and ud["ln"] == [h("pérez")]


def test_pais_en_minusculas_y_cifrado_solo_si_es_alfa2():
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": None}, None, "CO")
    assert ud["country"] == [h("co")]
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": None}, None, "COL")
    assert "country" not in ud


def test_identificadores_del_dispositivo_van_sin_cifrar():
    ident = {"anon_id": "XZabc", "madid": "38400000-8cf0-11bd-b23e-10b96e40000d",
             "client_ip": "2001:db8::1", "user_agent": "QuantFut/1.0 (Android; Flutter)"}
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": None}, ident, None)
    assert ud["anon_id"] == "XZabc"
    assert ud["madid"] == "38400000-8cf0-11bd-b23e-10b96e40000d"
    assert ud["client_ip_address"] == "2001:db8::1"
    assert ud["client_user_agent"] == "QuantFut/1.0 (Android; Flutter)"


def test_sin_madid_no_se_manda_el_campo():
    ident = {"anon_id": "XZabc", "madid": None, "client_ip": None, "user_agent": None}
    ud = m.user_data({"account_id": 1, "email": "a@b.co", "display_name": None}, ident, None)
    assert "madid" not in ud and "client_ip_address" not in ud


def test_extinfo_exige_16_posiciones_y_version_de_plataforma():
    ok = ["a2", "com.saptain.quantfut", "1.0.0", "1", "14", "Pixel 8", "es_CO", "COT", "", "1080",
          "2400", "2.75", "8", "", "", "America/Bogota"]
    assert m.valid_extinfo(ok, "android") == ok
    with pytest.raises(ValueError):
        m.valid_extinfo(ok[:15], "android")
    with pytest.raises(ValueError):
        m.valid_extinfo(ok, "ios")              # a2 no es iOS
    with pytest.raises(ValueError):
        m.valid_extinfo(["a2"] + ["x" * 101] * 15, "android")
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_meta_datos.py -v`
Expected: FAIL (`ModuleNotFoundError: qf.comercial.meta_datos`).

- [ ] **Step 3: Implementar**

`src/qf/comercial/meta_datos.py`:

```python
"""user_data de Conversions API normalizado y cifrado como pide Meta
(«Customer information parameters»). Puro: sin BD ni red.

Cifrados con SHA-256: em, external_id, fn, ln, country. Sin cifrar: madid, anon_id,
client_ip_address, client_user_agent. No se recoge teléfono: nunca se manda `ph`.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

EXTINFO_LEN = 16
_PUNTUACION = re.compile(r"[^\w\s]", re.UNICODE)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def external_id(account_id: int) -> str:
    return sha256(f"qf:{account_id}")


def _name_part(value: str) -> str:
    value = unicodedata.normalize("NFC", value).lower()
    return _PUNTUACION.sub("", value).strip()


def split_name(display_name: str | None) -> tuple[str | None, str | None]:
    parts = (display_name or "").split(None, 1)
    if not parts:
        return None, None
    first = _name_part(parts[0]) or None
    last = " ".join(_name_part(parts[1]).split()) if len(parts) > 1 else ""
    return first, last or None


def user_data(account: dict, identity: dict | None, country: str | None) -> dict:
    out: dict = {"external_id": [external_id(account["account_id"])]}
    email = (account.get("email") or "").strip().lower()
    if "@" in email:
        out["em"] = [sha256(email)]
    first, last = split_name(account.get("display_name"))
    if first:
        out["fn"] = [sha256(first)]
    if last:
        out["ln"] = [sha256(last)]
    if country and re.fullmatch(r"[A-Za-z]{2}", country):
        out["country"] = [sha256(country.lower())]
    if identity:
        out["anon_id"] = identity["anon_id"]
        for src, dst in (("madid", "madid"), ("client_ip", "client_ip_address"),
                         ("user_agent", "client_user_agent")):
            if identity.get(src):
                out[dst] = identity[src]
    return out


def valid_extinfo(values: list[str], platform: str) -> list[str]:
    if len(values) != EXTINFO_LEN:
        raise ValueError("extinfo debe tener 16 posiciones")
    if values[0] != {"android": "a2", "ios": "i2"}[platform]:
        raise ValueError("extinfo[0] no corresponde a la plataforma")
    if any(not isinstance(v, str) or len(v) > 100 for v in values):
        raise ValueError("extinfo con valores no válidos")
    return values
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_meta_datos.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/qf/comercial/meta_datos.py tests/test_meta_datos.py
git commit -m "Meta: normalización y hash de user_data"
```

---

## Task 3: Cola y envío de Conversions API

**Files:**
- Create: `src/qf/comercial/meta_capi.py`
- Modify: `scripts/crontab`, `.env.example`
- Test: `tests/test_meta_capi.py` (sin BD), `tests/test_meta_capi_pg.py` (con BD)

**Interfaces:**
- Consumes: `meta_datos.user_data`, tablas `meta_events`, `meta_identities`, `firebase_preferences.ads_measurement` (Task 1).
- Produces:
  - `enabled() -> bool`
  - `allowed(c, account_id: int) -> bool`
  - `enqueue(c, account_id: int, event_name: str, event_id: str, custom_data: dict | None = None) -> bool` — se llama **dentro** de la transacción del hecho.
  - `build_event(row: dict, account: dict, identity: dict | None) -> dict`
  - `send_pending(limit: int = 500, client: httpx.Client | None = None) -> dict` → `{"enviados": n, "omitidos": n, "fallidos": n}`
  - `value(price_micros: int) -> float`
  - Ejecutable: `python -m qf.comercial.meta_capi`.

- [ ] **Step 1: Escribir las pruebas sin BD que fallan**

`tests/test_meta_capi.py`:

```python
"""Construcción y envío de eventos CAPI con transporte simulado (sin BD ni red)."""
import json
from datetime import datetime, timezone

import httpx

from qf.comercial import meta_capi


ACC = {"account_id": 7, "email": "a@b.co", "display_name": "Ana Pérez"}
IDENT = {"anon_id": "XZ1", "platform": "android", "madid": None,
         "advertiser_tracking_enabled": True,
         "extinfo": ["a2", "com.saptain.quantfut", "1.0.0", "1", "14", "", "", "", "", "", "",
                     "", "", "", "", ""],
         "client_ip": "203.0.113.9", "user_agent": "QuantFut/1.0"}


def _row(**kw):
    base = {"event_id": "pur:GPA.1", "account_id": 7, "event_name": "Purchase",
            "event_time": datetime(2026, 10, 15, 12, tzinfo=timezone.utc),
            "custom_data": {"currency": "COP", "value": 54900.0, "content_ids": ["plus_1m"]}}
    return {**base, **kw}


def test_evento_de_app_lleva_action_source_app_data_y_event_id():
    ev = meta_capi.build_event(_row(), ACC, IDENT)
    assert ev["action_source"] == "app"
    assert ev["event_id"] == "pur:GPA.1"
    assert ev["event_name"] == "Purchase"
    assert ev["event_time"] == 1792065600          # 2026-10-15 12:00 UTC
    assert ev["app_data"] == {"advertiser_tracking_enabled": 1, "application_tracking_enabled": 1,
                              "extinfo": IDENT["extinfo"]}
    assert ev["user_data"]["anon_id"] == "XZ1"
    assert ev["custom_data"]["currency"] == "COP"


def test_sin_dispositivo_conocido_se_manda_extinfo_minimo_con_version_y_so():
    ev = meta_capi.build_event(_row(), ACC, None)
    assert ev["app_data"]["advertiser_tracking_enabled"] == 0
    assert len(ev["app_data"]["extinfo"]) == 16 and ev["app_data"]["extinfo"][0] == "a2"


def test_moneda_sin_decimales_conserva_el_valor_exacto():
    # 54.900 pesos colombianos = 54_900_000_000 micros: Meta debe recibir 54900.0, no 549.0.
    assert meta_capi.value(54_900_000_000) == 54900.0
    assert meta_capi.value(4_990_000) == 4.99


def test_envio_en_lote_con_token_y_codigo_de_prueba(monkeypatch):
    monkeypatch.setenv("META_DATASET_ID", "123")
    monkeypatch.setenv("META_CAPI_TOKEN", "secreto")
    monkeypatch.setenv("META_TEST_EVENT_CODE", "TEST42")
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"events_received": 1})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    received = meta_capi._post([meta_capi.build_event(_row(), ACC, IDENT)], client)
    assert received == 1
    assert seen["url"] == "https://graph.facebook.com/v24.0/123/events"
    assert seen["body"]["access_token"] == "secreto"
    assert seen["body"]["test_event_code"] == "TEST42"
    assert seen["body"]["data"][0]["event_id"] == "pur:GPA.1"
```

- [ ] **Step 2: Escribir las pruebas con BD que fallan**

`tests/test_meta_capi_pg.py`:

```python
"""Cola de Meta contra Postgres real. Se omite sin QF_TEST_PG_DSN."""
import os
import uuid

import httpx
import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.comercial import cuentas, meta_capi

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
    # Avisa al tercer intento. `>= 1` y no `== 1`: la base de pruebas es compartida y puede
    # traer eventos pendientes de otras pruebas que lleguen al tercer intento en otra pasada.
    assert len(alerts) >= 1


def test_limpieza_borra_dispositivos_y_eventos_terminados_antiguos():
    from qf.comercial import firebase_mantenimiento
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
```

- [ ] **Step 3: Ejecutar y ver que fallan**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_meta_capi.py tests/test_meta_capi_pg.py -v`
Expected: FAIL (`ModuleNotFoundError: qf.comercial.meta_capi`).

- [ ] **Step 4: Implementar**

`src/qf/comercial/meta_capi.py`:

```python
"""Conversions API de Meta para eventos de app (action_source=app).

El servidor es la única fuente de los eventos de valor (registro, suscripción, cobros,
desbloqueos): ninguno sale también del SDK, así que no hay deduplicación que depender.
`enqueue` va dentro de la transacción del hecho; `send_pending` (cron cada 5 min) envía.
Apagado por defecto: META_CAPI_ENABLED=1 para encolar y enviar.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

from ..db import conn
from . import meta_datos

log = logging.getLogger(__name__)
GRAPH_VERSION = "v24.0"
MAX_ATTEMPTS = 5
ALERT_AT = 3
# Meta rechaza eventos con más de 7 días de antigüedad.
MAX_AGE = timedelta(days=7)


def enabled() -> bool:
    return os.getenv("META_CAPI_ENABLED", "0") == "1"


def allowed(c, account_id: int) -> bool:
    row = c.execute("SELECT ads_measurement FROM firebase_preferences WHERE account_id = %s",
                    (account_id,)).fetchone()
    return row is None or row["ads_measurement"] is not False


def value(price_micros: int) -> float:
    return price_micros / 1_000_000


def enqueue(c, account_id: int, event_name: str, event_id: str,
            custom_data: dict | None = None) -> bool:
    if not enabled() or not allowed(c, account_id):
        return False
    row = c.execute(
        """INSERT INTO meta_events (event_id, account_id, event_name, custom_data)
           VALUES (%s, %s, %s, %s) ON CONFLICT (event_id) DO NOTHING RETURNING event_id""",
        (event_id, account_id, event_name, json.dumps(custom_data or {}))).fetchone()
    return row is not None


def _minimal_extinfo(platform: str) -> list[str]:
    values = [""] * meta_datos.EXTINFO_LEN
    values[0] = "i2" if platform == "ios" else "a2"
    values[1] = "com.saptain.quantfut"
    return values


def build_event(row: dict, account: dict, identity: dict | None) -> dict:
    platform = identity["platform"] if identity else "android"
    tracking = bool(identity and identity["advertiser_tracking_enabled"])
    custom = dict(row["custom_data"] or {})
    country = custom.pop("_country", None)
    return {
        "event_name": row["event_name"],
        "event_time": int(row["event_time"].timestamp()),
        "event_id": row["event_id"],
        "action_source": "app",
        "user_data": meta_datos.user_data(account, identity, country),
        "app_data": {
            "advertiser_tracking_enabled": int(tracking),
            "application_tracking_enabled": 1,
            "extinfo": identity["extinfo"] if identity else _minimal_extinfo(platform),
        },
        "custom_data": custom,
    }


def _post(events: list[dict], client: httpx.Client) -> int:
    body = {"data": events, "access_token": os.environ["META_CAPI_TOKEN"]}
    if os.getenv("META_TEST_EVENT_CODE"):
        body["test_event_code"] = os.environ["META_TEST_EVENT_CODE"]
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{os.environ['META_DATASET_ID']}/events"
    r = client.post(url, json=body, timeout=20)
    r.raise_for_status()
    return int(r.json().get("events_received", 0))


def _alert(text: str) -> None:
    from ..publish import telegram
    telegram.alert(text)


def send_pending(limit: int = 500, client: httpx.Client | None = None) -> dict:
    counts = {"enviados": 0, "omitidos": 0, "fallidos": 0}
    if not enabled():
        return counts
    client = client or httpx.Client()
    with conn() as c:
        rows = c.execute(
            """SELECT e.*, a.email::text AS email, a.display_name
               FROM meta_events e JOIN accounts a USING (account_id)
               WHERE e.status = 'pendiente' ORDER BY e.created_at LIMIT %s
               FOR UPDATE OF e SKIP LOCKED""", (limit,)).fetchall()
        now = datetime.now(timezone.utc)
        batch, ids = [], []
        for row in rows:
            if not allowed(c, row["account_id"]) or now - row["event_time"] > MAX_AGE:
                c.execute("UPDATE meta_events SET status = 'omitido' WHERE event_id = %s",
                          (row["event_id"],))
                counts["omitidos"] += 1
                continue
            identity = c.execute(
                """SELECT * FROM meta_identities WHERE account_id = %s
                   ORDER BY updated_at DESC LIMIT 1""", (row["account_id"],)).fetchone()
            batch.append(build_event(row, row, identity))
            ids.append(row["event_id"])
        if not batch:
            return counts
        try:
            _post(batch, client)
        except Exception as exc:  # noqa: BLE001 — se reintenta en la siguiente pasada
            error = str(exc)[:300]
            failed = c.execute(
                """UPDATE meta_events SET attempts = attempts + 1, last_error = %s,
                          status = CASE WHEN attempts + 1 >= %s THEN 'fallido' ELSE 'pendiente' END
                   WHERE event_id = ANY(%s) RETURNING attempts""",
                (error, MAX_ATTEMPTS, ids)).fetchall()
            counts["fallidos"] = len(ids)
            if any(r["attempts"] == ALERT_AT for r in failed):
                _alert(f"Meta CAPI falla {ALERT_AT} veces seguidas: {error}")
            return counts
        c.execute("""UPDATE meta_events SET status = 'enviado', sent_at = now(),
                            attempts = attempts + 1, last_error = NULL
                     WHERE event_id = ANY(%s)""", (ids,))
        counts["enviados"] = len(ids)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("meta_capi: %s", send_pending())
```

Nota: `build_event(row, row, identity)` reutiliza la fila de la consulta como cuenta porque trae `account_id`, `email` y `display_name`.

Limpieza (la spec pide que estos datos entren en la limpieza diaria de datos operativos). En `src/qf/comercial/firebase_mantenimiento.py`, dentro de `clean()`, antes del `return`:

```python
        meta_identities = c.execute(
            "DELETE FROM meta_identities WHERE updated_at < now()-interval '90 days'").rowcount
        # Solo eventos ya resueltos: un pendiente se reintenta o caduca por MAX_AGE en meta_capi.
        meta_events = c.execute(
            """DELETE FROM meta_events WHERE status <> 'pendiente'
               AND created_at < now()-interval '90 days'""").rowcount
```

y devolver también `"meta_identities": meta_identities, "meta_events": meta_events`. Añadir una línea a la tabla de conservación de `docs/legal/OPERACION_PRIVACIDAD.md`: «Datos de dispositivo y eventos enviados a Meta: 90 días desde la última actualización».

- [ ] **Step 5: Ejecutar y ver que pasan**

Run: `PYTHONPATH=src QF_TEST_PG_DSN=... .venv/Scripts/python.exe -m pytest tests/test_meta_capi.py tests/test_meta_capi_pg.py tests/test_firebase_operations.py -v`
Expected: 4 + 7 PASS y las de mantenimiento existentes también.

- [ ] **Step 6: Cron y variables documentadas**

Añadir al final de `scripts/crontab`:

```
# Conversions API de Meta (db/071): envía la cola meta_events. Sin META_CAPI_ENABLED=1 no hace nada.
*/5 * * * * cd /app && python -m qf.comercial.meta_capi >> /var/log/meta_capi.log 2>&1
```

Añadir a `.env.example`:

```
# --- Meta Conversions API (db/071). Apagado por defecto. El token es de un usuario del sistema
# del Business Manager y vive SOLO aquí, nunca en la app.
META_CAPI_ENABLED=0
META_DATASET_ID=
META_CAPI_TOKEN=
# Opcional: código de «Probar eventos» de Events Manager. Vaciar en producción real.
META_TEST_EVENT_CODE=
```

- [ ] **Step 7: Commit**

```bash
git add src/qf/comercial/meta_capi.py src/qf/comercial/firebase_mantenimiento.py docs/legal/OPERACION_PRIVACIDAD.md tests/test_meta_capi.py tests/test_meta_capi_pg.py scripts/crontab .env.example
git commit -m "Meta: cola y envío de Conversions API para eventos de app"
```

---

## Task 4: Datos del dispositivo, preferencia de Meta y `/me`

**Files:**
- Create: `src/qf/api/meta.py`
- Modify: `src/qf/api/cuentas.py` (`MeOut`, `me()`, `PlanOut`), `src/qf/api/firebase.py` (`PreferencesIn`, `save_preferences`, `preferences`), `src/qf/comercial/suscripciones.py` (`plans()`), `src/qf/api/main.py`
- Test: `tests/test_meta_api.py`

**Interfaces:**
- Consumes: `meta_datos.valid_extinfo`, `meta_datos.external_id`, `ratelimit.client_ip`, `api.current_account`, `api.require_enabled`.
- Produces:
  - `POST /app/v1/meta/dispositivo` (204) con cuerpo `{anon_id, platform, madid|null, advertiser_tracking_enabled, extinfo[16]}`.
  - `GET /app/v1/me` → añade `store_account_token: str | null` y `meta_external_id: str`.
  - `POST /app/v1/firebase/preferences` acepta `ads_measurement: bool | null` (null = no cambiar).
  - Catálogo de planes con `play_product_id`, `play_base_plan_id`, `apple_product_id`.

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_meta_api.py`:

```python
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
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_meta_api.py -v`
Expected: FAIL (`ImportError: cannot import name 'meta'`).

- [ ] **Step 3: Implementar el router**

`src/qf/api/meta.py`:

```python
"""Datos del dispositivo para Conversions API (db/071). La app los manda tras iniciar
sesión y al arrancar; el servidor añade IP y user agent de la propia petición."""
from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from . import cuentas as api
from .ratelimit import client_ip
from ..comercial import meta_datos
from ..db import execute

router = APIRouter(prefix="/app/v1/meta", tags=["app"], dependencies=[Depends(api.require_enabled)])
_UUID = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


class DispositivoIn(BaseModel):
    anon_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_\-:.]+$")
    platform: Literal["android", "ios"]
    madid: str | None = Field(default=None, pattern=_UUID)
    advertiser_tracking_enabled: bool
    extinfo: list[str] = Field(min_length=16, max_length=16)


def _save(**row) -> None:
    execute(
        """INSERT INTO meta_identities (account_id, anon_id, platform, madid,
               advertiser_tracking_enabled, extinfo, client_ip, user_agent)
           VALUES (%(account_id)s, %(anon_id)s, %(platform)s, %(madid)s,
                   %(advertiser_tracking_enabled)s, %(extinfo_json)s, %(client_ip)s, %(user_agent)s)
           ON CONFLICT (account_id, anon_id) DO UPDATE SET platform = EXCLUDED.platform,
               madid = EXCLUDED.madid, advertiser_tracking_enabled = EXCLUDED.advertiser_tracking_enabled,
               extinfo = EXCLUDED.extinfo, client_ip = EXCLUDED.client_ip,
               user_agent = EXCLUDED.user_agent, updated_at = now()""",
        {**row, "extinfo_json": json.dumps(row["extinfo"])})


@router.post("/dispositivo", status_code=204)
def dispositivo(body: DispositivoIn, request: Request, acc: dict = Depends(api.current_account)):
    try:
        extinfo = meta_datos.valid_extinfo(body.extinfo, body.platform)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    _save(account_id=acc["account_id"], anon_id=body.anon_id, platform=body.platform,
          madid=body.madid, advertiser_tracking_enabled=body.advertiser_tracking_enabled,
          extinfo=extinfo, client_ip=client_ip(request),
          user_agent=(request.headers.get("user-agent") or "")[:300] or None)
    return Response(status_code=204)
```

- [ ] **Step 4: `/me` y catálogo**

En `src/qf/api/cuentas.py`, sustituir `MeOut` y `PlanOut` y `me()`:

```python
class MeOut(BaseModel):
    account: AccountOut
    plus: bool
    subscription: SubscriptionOut | None
    # Lo pasa la app a la tienda (obfuscatedAccountId / appAccountToken): no es secreto
    # ni dato personal, solo liga la compra a esta cuenta.
    store_account_token: str | None = None
    # SHA-256 de qf:{account_id}: el mismo external_id que manda el servidor a Meta.
    meta_external_id: str


class PlanOut(BaseModel):
    plan_code: str
    name: str
    duration_days: int | None
    price_cents: int
    currency: str
    play_product_id: str | None = None
    play_base_plan_id: str | None = None
    apple_product_id: str | None = None
```

```python
@router.get("/me", response_model=MeOut)
def me(acc: dict = Depends(current_account)):
    sub = suscripciones.active_subscription(acc["account_id"])
    return MeOut(account=_account_out(acc), plus=sub is not None,
                 subscription=SubscriptionOut(**sub) if sub else None,
                 store_account_token=acc.get("store_account_token"),
                 meta_external_id=meta_datos.external_id(acc["account_id"]))
```

Añadir `meta_datos` al import: `from ..comercial import correo, cuentas, meta_datos, suscripciones`.

En `src/qf/comercial/suscripciones.py`, `plans()`:

```python
def plans(only_active: bool = False) -> list[dict]:
    return query(
        """SELECT plan_code, name, duration_days, price_cents, currency, active, sort_order,
                  play_product_id, play_base_plan_id, apple_product_id
           FROM plans WHERE active OR NOT %s ORDER BY sort_order, plan_code""", (only_active,))
```

- [ ] **Step 5: Preferencia de Meta en el servidor**

En `src/qf/api/firebase.py`:

```python
class PreferencesIn(BaseModel):
    language: Language = 'es'
    analytics: bool = False
    diagnostics: bool = False
    push_enabled: bool = False
    # None = no tocar lo guardado (apps antiguas no lo envían). NULL en BD = activo.
    ads_measurement: bool | None = None


@router.get('/preferences')
def preferences(account: dict = Depends(api.current_account)):
    row = query_one('''SELECT language, analytics, diagnostics, push_enabled,
                              coalesce(ads_measurement, true) AS ads_measurement
                       FROM firebase_preferences WHERE account_id=%s''', (account['account_id'],))
    return row or {**PreferencesIn().model_dump(), 'ads_measurement': True}


@router.post('/preferences')
def save_preferences(body: PreferencesIn, account: dict = Depends(api.current_account)):
    with conn() as c:
        c.execute('''INSERT INTO firebase_preferences (account_id, language, analytics, diagnostics,
                                                       push_enabled, ads_measurement)
                     VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (account_id) DO UPDATE SET
                     language=EXCLUDED.language, analytics=EXCLUDED.analytics, diagnostics=EXCLUDED.diagnostics,
                     push_enabled=EXCLUDED.push_enabled,
                     ads_measurement=coalesce(EXCLUDED.ads_measurement, firebase_preferences.ads_measurement),
                     updated_at=now()''',
                  (account['account_id'], body.language, body.analytics, body.diagnostics,
                   body.push_enabled, body.ads_measurement))
        if not body.push_enabled:
            c.execute('UPDATE push_devices SET enabled=false WHERE account_id=%s', (account['account_id'],))
    return body
```

- [ ] **Step 6: Registrar el router**

En `src/qf/api/main.py`, junto a los demás imports de routers añadir `from .meta import router as meta_router` y tras `app.include_router(firebase_router)`:

```python
app.include_router(meta_router)
```

- [ ] **Step 7: Ejecutar pruebas**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_meta_api.py tests/test_cuentas_api.py tests/test_firebase.py tests/test_mobile_identidad_firebase.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/qf/api/meta.py src/qf/api/cuentas.py src/qf/api/firebase.py src/qf/api/main.py src/qf/comercial/suscripciones.py tests/test_meta_api.py
git commit -m "Meta: datos del dispositivo, preferencia de medición y token de tienda en /me"
```

---

## Task 5: Eventos de servidor — registro y desbloqueo con monedas

**Files:**
- Modify: `src/qf/comercial/cuentas.py` (`create_account`), `src/qf/comercial/firebase.py` (`connect_identity`), `src/qf/api/rewards.py` (`unlock`)
- Test: `tests/test_meta_capi_pg.py` (añadir)

**Interfaces:**
- Consumes: `meta_capi.enqueue(c, account_id, event_name, event_id, custom_data)`.
- Produces: filas `reg:{account_id}` (`CompleteRegistration`, `custom_data={"registration_method": "email"|"google"}`) y `spend:{account_id}:{stream}:{pick_key}` (`SpentCredits`, `{"content_ids": [pick_key], "value": coste}`).

- [ ] **Step 1: Escribir las pruebas que fallan**

Añadir a `tests/test_meta_capi_pg.py`:

```python
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
```

(El desbloqueo con monedas se prueba a mano en Task 16 en «Probar eventos»: `unlock` depende de los picks vivos de `mobile.high_probability()`.)

- [ ] **Step 2: Ejecutar y ver que fallan**

Run: `PYTHONPATH=src QF_TEST_PG_DSN=... .venv/Scripts/python.exe -m pytest tests/test_meta_capi_pg.py -k registration -v`
Expected: FAIL (`row is None`).

- [ ] **Step 3: Implementar**

En `src/qf/comercial/cuentas.py`, `create_account`:

```python
def create_account(email: str, password: str, display_name: str | None = None) -> dict:
    email = normalize_email(email)
    validate_password(password)
    name = (display_name or "").strip()[:80] or None
    with conn() as c:
        row = c.execute(
            f"""INSERT INTO accounts (email, password_hash, display_name)
                VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING
                RETURNING {_PUBLIC}""",
            (email, _ph.hash(password), name)).fetchone()
        if row is not None:
            from . import meta_capi
            meta_capi.enqueue(c, row["account_id"], "CompleteRegistration",
                              f"reg:{row['account_id']}", {"registration_method": "email"})
    if row is None:
        raise CuentaError("email_en_uso", "Ya existe una cuenta con ese correo")
    return row
```

En `src/qf/comercial/firebase.py`, dentro de `connect_identity`, en la rama que crea cuenta, justo después de `account_id = row["account_id"]`:

```python
                account_id = row["account_id"]
                from . import meta_capi
                meta_capi.enqueue(c, account_id, "CompleteRegistration", f"reg:{account_id}",
                                  {"registration_method": "google"})
```

En `src/qf/api/rewards.py`, `unlock`, después del `INSERT INTO reward_unlocks`:

```python
        from ..comercial import meta_capi
        meta_capi.enqueue(c, account['account_id'], 'SpentCredits',
                          f"spend:{account['account_id']}:{body.stream}:{body.pick_key}",
                          {'content_ids': [body.pick_key], 'content_type': 'product',
                           'value': cfg['unlock_cost']})
```

(`SpentCredits` no es evento estándar de CAPI web; llega como evento personalizado. Comprobarlo en «Probar eventos».)

- [ ] **Step 4: Ejecutar y ver que pasan**

Run: el comando del Step 2 y además `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_cuentas_api.py tests/test_rewards*.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/qf/comercial/cuentas.py src/qf/comercial/firebase.py src/qf/api/rewards.py tests/test_meta_capi_pg.py
git commit -m "Meta: CompleteRegistration y SpentCredits desde el servidor"
```

---

## Task 6: Clientes de tienda — Google Play y App Store

**Files:**
- Create: `src/qf/comercial/tiendas/__init__.py`, `src/qf/comercial/tiendas/google_play.py`, `src/qf/comercial/tiendas/app_store.py`, `tests/fixtures/play_subscription_v2.json`
- Modify: `requirements.txt`, `.env.example`
- Test: `tests/test_tiendas.py`

**Interfaces:**
- Produces:
  - `Cobro` (dataclass congelada): `store, order_id, original_id, account_token, product_id, base_plan_id, period_start, period_end, price_micros, currency, region_code, environment, state, payload`. `state ∈ {"activa", "pendiente", "sin_acceso"}`.
  - `TiendaError(code: str, message: str)`.
  - `google_play.fetch(token: str, session=None) -> dict`, `google_play.parse(token: str, data: dict) -> Cobro`, `google_play.acknowledge(product_id: str, token: str, session=None) -> None`, `google_play.verify_push(authorization: str | None) -> None`.
  - `app_store.verify_transaction(jws: str) -> Cobro`, `app_store.verify_notification(signed_payload: str) -> tuple[str, Cobro | None, str | None]` → `(notification_type, cobro, transaction_id)`, `app_store.parse(tx) -> Cobro`.

- [ ] **Step 1: Fixture grabada de Play**

`tests/fixtures/play_subscription_v2.json` (forma de `SubscriptionPurchaseV2`, valores de prueba):

```json
{
  "kind": "androidpublisher#subscriptionPurchaseV2",
  "regionCode": "CO",
  "startTime": "2026-10-15T12:00:00.000Z",
  "subscriptionState": "SUBSCRIPTION_STATE_ACTIVE",
  "latestOrderId": "GPA.3345-1234-5678-90123",
  "acknowledgementState": "ACKNOWLEDGEMENT_STATE_PENDING",
  "externalAccountIdentifiers": {"obfuscatedExternalAccountId": "0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c"},
  "lineItems": [{
    "productId": "quantfut_plus",
    "expiryTime": "2026-11-15T12:00:00.000Z",
    "latestSuccessfulOrderId": "GPA.3345-1234-5678-90123",
    "autoRenewingPlan": {"autoRenewEnabled": true,
                         "recurringPrice": {"currencyCode": "COP", "units": "54900", "nanos": 0}},
    "offerDetails": {"basePlanId": "plus-1m"}
  }]
}
```

- [ ] **Step 2: Escribir las pruebas que fallan**

`tests/test_tiendas.py`:

```python
"""Parseo de respuestas verificadas de Google Play y App Store (sin red)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from qf.comercial.tiendas import TiendaError, app_store, google_play

PLAY = json.loads((Path(__file__).parent / "fixtures" / "play_subscription_v2.json").read_text("utf-8"))


def test_play_activa_se_convierte_en_cobro_con_micros_exactos():
    c = google_play.parse("tok-1", PLAY)
    assert (c.store, c.order_id, c.original_id) == ("google_play", "GPA.3345-1234-5678-90123", "tok-1")
    assert c.account_token == "0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c"
    assert (c.product_id, c.base_plan_id) == ("quantfut_plus", "plus-1m")
    assert c.period_end == datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
    assert (c.price_micros, c.currency, c.region_code) == (54_900_000_000, "COP", "CO")
    assert (c.environment, c.state) == ("production", "activa")


def test_play_compra_de_prueba_es_sandbox():
    c = google_play.parse("tok-1", {**PLAY, "testPurchase": {}})
    assert c.environment == "sandbox"


@pytest.mark.parametrize("estado,esperado", [
    ("SUBSCRIPTION_STATE_CANCELED", "activa"),          # cancelada: dura hasta expiryTime
    ("SUBSCRIPTION_STATE_IN_GRACE_PERIOD", "activa"),
    ("SUBSCRIPTION_STATE_PENDING", "pendiente"),
    ("SUBSCRIPTION_STATE_ON_HOLD", "sin_acceso"),
    ("SUBSCRIPTION_STATE_EXPIRED", "sin_acceso"),
])
def test_play_estados(estado, esperado):
    assert google_play.parse("tok-1", {**PLAY, "subscriptionState": estado}).state == esperado


def test_play_push_sin_token_se_rechaza(monkeypatch):
    monkeypatch.setenv("PLAY_RTDN_AUDIENCE", "https://x/app/v1/compras/google/rtdn")
    with pytest.raises(TiendaError):
        google_play.verify_push(None)


def _apple_tx(**kw):
    base = dict(transactionId="2000000123", originalTransactionId="2000000100",
                productId="quantfut_plus_3m", purchaseDate=1760529600000, expiresDate=1768305600000,
                appAccountToken="0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c", price=19990, currency="USD",
                environment=SimpleNamespace(value="Production"), revocationDate=None)
    return SimpleNamespace(**{**base, **kw})


def test_apple_transaccion_se_convierte_en_cobro():
    c = app_store.parse(_apple_tx())
    assert (c.store, c.order_id, c.original_id) == ("app_store", "2000000123", "2000000100")
    assert c.period_start == datetime(2025, 10, 15, 12, tzinfo=timezone.utc)
    assert c.period_end == datetime(2026, 1, 13, 12, tzinfo=timezone.utc)
    assert c.price_micros == 19_990_000 and c.currency == "USD"
    assert c.environment == "production" and c.state == "activa"


def test_apple_revocada_no_da_acceso():
    assert app_store.parse(_apple_tx(revocationDate=1760600000000)).state == "sin_acceso"


def test_apple_sandbox():
    assert app_store.parse(_apple_tx(environment=SimpleNamespace(value="Sandbox"))).environment == "sandbox"
```

- [ ] **Step 3: Ejecutar y ver que fallan**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_tiendas.py -v`
Expected: FAIL (`ModuleNotFoundError: qf.comercial.tiendas`).

- [ ] **Step 4: Implementar el módulo común**

`src/qf/comercial/tiendas/__init__.py`:

```python
"""Cobros verificados con Google Play y App Store. El acceso se decide aquí, en el
servidor, con lo que devuelve la tienda: la app solo transporta el token o el JWS."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class TiendaError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass(frozen=True)
class Cobro:
    store: str                 # 'google_play' | 'app_store'
    order_id: str              # orderId (Play) / transactionId (Apple): un cobro
    original_id: str           # purchaseToken (Play) / originalTransactionId (Apple): la suscripción
    account_token: str | None  # obfuscatedExternalAccountId / appAccountToken
    product_id: str
    base_plan_id: str | None
    period_start: datetime
    period_end: datetime
    price_micros: int | None
    currency: str | None
    region_code: str | None
    environment: str           # 'production' | 'sandbox'
    state: str                 # 'activa' | 'pendiente' | 'sin_acceso'
    payload: dict
```

- [ ] **Step 5: Implementar Google Play**

`src/qf/comercial/tiendas/google_play.py`:

```python
"""Google Play Developer API: purchases.subscriptionsv2 y reconocimiento de compras.
Cuenta de servicio en PLAY_SERVICE_ACCOUNT_FILE (solo en el servidor)."""
from __future__ import annotations

import os
from datetime import datetime

from . import Cobro, TiendaError

SCOPE = "https://www.googleapis.com/auth/androidpublisher"
BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
_ACTIVA = {"SUBSCRIPTION_STATE_ACTIVE", "SUBSCRIPTION_STATE_CANCELED", "SUBSCRIPTION_STATE_IN_GRACE_PERIOD"}
_PENDIENTE = {"SUBSCRIPTION_STATE_PENDING"}


def package() -> str:
    return os.getenv("PLAY_PACKAGE_NAME", "com.saptain.quantfut")


def _session():
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account
    path = os.getenv("PLAY_SERVICE_ACCOUNT_FILE", "")
    if not path:
        raise TiendaError("tienda_no_configurada", "Las compras todavía no están disponibles")
    creds = service_account.Credentials.from_service_account_file(path, scopes=[SCOPE])
    return AuthorizedSession(creds)


def fetch(token: str, session=None) -> dict:
    s = session or _session()
    r = s.get(f"{BASE}/{package()}/purchases/subscriptionsv2/tokens/{token}", timeout=20)
    if r.status_code in (400, 404, 410):
        raise TiendaError("compra_no_valida", "La tienda no reconoce esta compra")
    r.raise_for_status()
    return r.json()


def acknowledge(product_id: str, token: str, session=None) -> None:
    s = session or _session()
    r = s.post(f"{BASE}/{package()}/purchases/subscriptions/{product_id}/tokens/{token}:acknowledge",
               json={}, timeout=20)
    r.raise_for_status()


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse(token: str, data: dict) -> Cobro:
    item = (data.get("lineItems") or [{}])[0]
    state = data.get("subscriptionState", "")
    price = (item.get("autoRenewingPlan") or {}).get("recurringPrice") or {}
    micros = (int(price["units"]) * 1_000_000 + int(price.get("nanos", 0)) // 1000) if "units" in price else None
    order = item.get("latestSuccessfulOrderId") or data.get("latestOrderId")
    if not order or not item.get("expiryTime"):
        raise TiendaError("compra_no_valida", "La tienda no reconoce esta compra")
    return Cobro(
        store="google_play", order_id=order, original_id=token,
        account_token=(data.get("externalAccountIdentifiers") or {}).get("obfuscatedExternalAccountId"),
        product_id=item.get("productId", ""),
        base_plan_id=(item.get("offerDetails") or {}).get("basePlanId"),
        period_start=_time(data["startTime"]), period_end=_time(item["expiryTime"]),
        price_micros=micros, currency=price.get("currencyCode"), region_code=data.get("regionCode"),
        environment="sandbox" if "testPurchase" in data else "production",
        state="activa" if state in _ACTIVA else "pendiente" if state in _PENDIENTE else "sin_acceso",
        payload=data)


def verify_push(authorization: str | None) -> None:
    """Pub/Sub firma cada push con un token OIDC de la cuenta de servicio configurada."""
    if not authorization or not authorization.startswith("Bearer "):
        raise TiendaError("rtdn_no_autenticado", "Notificación sin autenticar")
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token
    try:
        claims = id_token.verify_oauth2_token(authorization[7:], Request(),
                                              audience=os.environ["PLAY_RTDN_AUDIENCE"])
    except Exception:  # noqa: BLE001
        raise TiendaError("rtdn_no_autenticado", "Notificación sin autenticar") from None
    if not claims.get("email_verified") or claims.get("email") != os.getenv("PLAY_RTDN_SERVICE_ACCOUNT"):
        raise TiendaError("rtdn_no_autenticado", "Notificación sin autenticar")
```

- [ ] **Step 6: Implementar App Store**

Añadir a `requirements.txt` (tras `firebase-admin`):

```
# Verificación de transacciones y notificaciones de App Store (JWS firmado por Apple).
app-store-server-library==3.1.2
```

Run: `.venv/Scripts/python.exe -m pip install app-store-server-library==3.1.2`

`src/qf/comercial/tiendas/app_store.py`:

```python
"""App Store: transacciones StoreKit 2 y App Store Server Notifications V2, ambas como JWS
que se verifican con la cadena de certificados de Apple (librería oficial). Las raíces
(AppleRootCA-G3.cer…) se descargan de apple.com/certificateauthority y se montan en
APPLE_ROOT_CERTS_DIR."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from . import Cobro, TiendaError

_TIPOS_COBRO = {"SUBSCRIBED", "DID_RENEW"}
_TIPOS_REVOCACION = {"REFUND", "REVOKE"}


def _verifier(environment):
    from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
    folder = os.getenv("APPLE_ROOT_CERTS_DIR", "")
    if not folder:
        raise TiendaError("tienda_no_configurada", "Las compras todavía no están disponibles")
    roots = [p.read_bytes() for p in sorted(Path(folder).glob("*.cer"))]
    app_id = os.getenv("APPLE_APP_ID")
    return SignedDataVerifier(roots, True, environment, os.getenv("APPLE_BUNDLE_ID", "com.saptain.quantfut"),
                              int(app_id) if app_id else None)


def _verify(method: str, signed: str):
    from appstoreserverlibrary.models.Environment import Environment
    from appstoreserverlibrary.signed_data_verifier import VerificationException
    last = None
    for env in (Environment.PRODUCTION, Environment.SANDBOX):
        try:
            return getattr(_verifier(env), method)(signed)
        except VerificationException as exc:
            last = exc
    raise TiendaError("compra_no_valida", "La tienda no reconoce esta compra") from last


def _ms(value: int | None) -> datetime | None:
    return datetime.fromtimestamp(value / 1000, timezone.utc) if value else None


def parse(tx) -> Cobro:
    expires = _ms(tx.expiresDate)
    if expires is None:
        raise TiendaError("compra_no_valida", "La tienda no reconoce esta compra")
    env = getattr(tx.environment, "value", str(tx.environment))
    return Cobro(
        store="app_store", order_id=str(tx.transactionId), original_id=str(tx.originalTransactionId),
        account_token=str(tx.appAccountToken) if tx.appAccountToken else None,
        product_id=tx.productId, base_plan_id=None,
        period_start=_ms(tx.purchaseDate), period_end=expires,
        price_micros=tx.price * 1000 if tx.price is not None else None, currency=tx.currency,
        region_code=None, environment="production" if env == "Production" else "sandbox",
        state="sin_acceso" if tx.revocationDate else "activa",
        payload={"transactionId": str(tx.transactionId), "productId": tx.productId})


def verify_transaction(jws: str) -> Cobro:
    return parse(_verify("verify_and_decode_signed_transaction", jws))


def verify_notification(signed_payload: str) -> tuple[str, Cobro | None, str | None]:
    note = _verify("verify_and_decode_notification", signed_payload)
    kind = getattr(note.notificationType, "value", str(note.notificationType))
    signed_tx = note.data.signedTransactionInfo if note.data else None
    if not signed_tx:
        return kind, None, None
    tx = _verify("verify_and_decode_signed_transaction", signed_tx)
    if kind in _TIPOS_COBRO:
        return kind, parse(tx), str(tx.transactionId)
    if kind in _TIPOS_REVOCACION:
        return kind, None, str(tx.transactionId)
    return kind, None, None
```

- [ ] **Step 7: Variables documentadas**

Añadir a `.env.example`:

```
# --- Compras en tiendas (db/071). Apagado por defecto.
STORE_PURCHASES_ENABLED=0
PLAY_PACKAGE_NAME=com.saptain.quantfut
# JSON de la cuenta de servicio con acceso a la Play Developer API (montado, no en el repo).
PLAY_SERVICE_ACCOUNT_FILE=
# Push de Pub/Sub (RTDN): audiencia OIDC = URL del endpoint, y cuenta de servicio que firma.
PLAY_RTDN_AUDIENCE=https://pronosticosdeportivos.pro/app/v1/compras/google/rtdn
PLAY_RTDN_SERVICE_ACCOUNT=
APPLE_BUNDLE_ID=com.saptain.quantfut
APPLE_APP_ID=
APPLE_ROOT_CERTS_DIR=
```

- [ ] **Step 8: Ejecutar y ver que pasan**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_tiendas.py -v`
Expected: 10 PASS.

- [ ] **Step 9: Commit**

```bash
git add src/qf/comercial/tiendas tests/test_tiendas.py tests/fixtures/play_subscription_v2.json requirements.txt .env.example
git commit -m "Compras: verificación de Google Play (subscriptionsv2) y App Store (JWS)"
```

---

## Task 7: Aplicar cobros verificados (idempotente) y revocar

**Files:**
- Create: `src/qf/comercial/tiendas/compras.py`
- Modify: `src/qf/comercial/suscripciones.py` (`grant_store`, `revoke_in`, `revoke` usa `revoke_in`)
- Test: `tests/test_compras_pg.py` (añadir)

**Interfaces:**
- Consumes: `Cobro`, `TiendaError` (Task 6), `meta_capi.enqueue` (Task 3), `meta_capi.value`.
- Produces:
  - `suscripciones.grant_store(c, account_id, plan_code, starts_at, ends_at, *, price_cents, currency, note) -> dict`
  - `suscripciones.revoke_in(c, subscription_id, actor, reason) -> dict | None`
  - `compras.aplicar(cobro: Cobro, account_id: int | None) -> dict` → `{"estado": "concedido"|"pendiente"|"sin_acceso", "ends_at": datetime|None, "account_id": int}`
  - `compras.revocar_orden(store: str, order_id: str, motivo: str) -> bool`
  - `compras.revocar_original(store: str, original_id: str, motivo: str) -> int`

- [ ] **Step 1: Escribir las pruebas que fallan**

Añadir a `tests/test_compras_pg.py`:

```python
from datetime import datetime, timedelta, timezone

from qf.comercial import meta_capi, suscripciones
from qf.comercial.tiendas import Cobro, TiendaError, compras

NOW = datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture(autouse=True)
def _meta_on(monkeypatch):
    monkeypatch.setenv("META_CAPI_ENABLED", "1")


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
```

- [ ] **Step 2: Ejecutar y ver que fallan**

Run: `PYTHONPATH=src QF_TEST_PG_DSN=... .venv/Scripts/python.exe -m pytest tests/test_compras_pg.py -v`
Expected: FAIL (`ModuleNotFoundError: qf.comercial.tiendas.compras`).

- [ ] **Step 3: Concesión y revocación dentro de una transacción**

En `src/qf/comercial/suscripciones.py`, añadir y refactorizar `revoke`:

```python
def grant_store(c, account_id: int, plan_code: str, starts_at, ends_at, *, price_cents: int,
                currency: str, note: str, actor: str = "tienda") -> dict:
    """Periodo cobrado por una tienda: fechas reales de la tienda, en la transacción
    del cobro (la llama tiendas.compras, que ya bloqueó la suscripción)."""
    row = c.execute(
        """INSERT INTO subscriptions (account_id, plan_code, starts_at, ends_at, source,
                                      price_cents, currency, note, created_by)
           VALUES (%s, %s, %s, %s, 'payment', %s, %s, %s, %s)
           RETURNING subscription_id, plan_code, starts_at, ends_at""",
        (account_id, plan_code, starts_at, ends_at, price_cents, currency, note[:300], actor)).fetchone()
    audit(c, actor, "suscripcion.conceder", account_id,
          {"subscription_id": row["subscription_id"], "plan": plan_code, "source": "payment",
           "ends_at": row["ends_at"].astimezone(timezone.utc).isoformat()})
    return row


def revoke_in(c, subscription_id: int, actor: str, reason: str) -> dict | None:
    reason = (reason or "").strip()[:300]
    if not reason:
        raise CuentaError("motivo_requerido", "Indica el motivo de la revocación")
    row = c.execute(
        """UPDATE subscriptions SET revoked_at = now(), revoked_by = %s, revoke_reason = %s
           WHERE subscription_id = %s AND revoked_at IS NULL
           RETURNING subscription_id, account_id, plan_code""",
        (actor, reason, subscription_id)).fetchone()
    if row:
        audit(c, actor, "suscripcion.revocar", row["account_id"],
              {"subscription_id": subscription_id, "motivo": reason})
    return row


def revoke(subscription_id: int, actor: str, reason: str) -> dict | None:
    with conn() as c:
        return revoke_in(c, subscription_id, actor, reason)
```

(Comprobar con `tests/test_cuentas_pg.py` que `revoke` sigue igual: la validación del motivo ocurre ahora dentro de la conexión, mismo resultado.)

- [ ] **Step 4: Implementar `compras.py`**

`src/qf/comercial/tiendas/compras.py`:

```python
"""Aplica cobros ya verificados con la tienda. Idempotente por (store, order_id):
la app y la notificación de la tienda pueden llegar en cualquier orden y repetidas."""
from __future__ import annotations

import json

from ...db import conn
from .. import meta_capi, suscripciones
from . import Cobro, TiendaError


def _plan(c, cobro: Cobro) -> str:
    if cobro.store == "google_play":
        row = c.execute("SELECT plan_code FROM plans WHERE play_product_id = %s AND play_base_plan_id = %s",
                        (cobro.product_id, cobro.base_plan_id)).fetchone()
    else:
        row = c.execute("SELECT plan_code FROM plans WHERE apple_product_id = %s",
                        (cobro.product_id,)).fetchone()
    if row is None:
        raise TiendaError("producto_desconocido", "No se reconoce el producto comprado")
    return row["plan_code"]


def _owner(c, cobro: Cobro, account_id: int | None) -> int:
    if not cobro.account_token:
        raise TiendaError("compra_sin_cuenta", "La compra no está asociada a ninguna cuenta")
    row = c.execute("SELECT account_id FROM accounts WHERE store_account_token::text = %s",
                    (cobro.account_token,)).fetchone()
    if row is None:
        raise TiendaError("compra_sin_cuenta", "La compra no está asociada a ninguna cuenta")
    if account_id is not None and row["account_id"] != account_id:
        raise TiendaError("compra_de_otra_cuenta", "Esta compra pertenece a otra cuenta")
    return row["account_id"]


def aplicar(cobro: Cobro, account_id: int | None) -> dict:
    with conn() as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                  (f"tienda:{cobro.store}:{cobro.original_id}",))
        owner = _owner(c, cobro, account_id)
        done = c.execute("SELECT period_end FROM store_transactions WHERE store = %s AND order_id = %s",
                         (cobro.store, cobro.order_id)).fetchone()
        if done:
            return {"estado": "concedido", "ends_at": done["period_end"], "account_id": owner}
        if cobro.state != "activa":
            return {"estado": cobro.state, "ends_at": None, "account_id": owner}
        plan_code = _plan(c, cobro)
        prev = c.execute(
            """SELECT count(*) AS n,
                      max(period_end) FILTER (WHERE period_end < %s) AS last_end
               FROM store_transactions WHERE store = %s AND original_id = %s""",
            (cobro.period_end, cobro.store, cobro.original_id)).fetchone()
        start = max(cobro.period_start, prev["last_end"]) if prev["last_end"] else cobro.period_start
        if cobro.period_end <= start:
            return {"estado": "sin_acceso", "ends_at": None, "account_id": owner}
        price_cents = round(cobro.price_micros / 10_000) if cobro.price_micros is not None else 0
        sub = suscripciones.grant_store(c, owner, plan_code, start, cobro.period_end,
                                        price_cents=price_cents, currency=cobro.currency or "USD",
                                        note=f"{cobro.store}:{cobro.order_id}")
        c.execute(
            """INSERT INTO store_transactions (store, order_id, original_id, account_id, plan_code,
                   product_id, base_plan_id, period_start, period_end, price_micros, currency,
                   region_code, environment, subscription_id, verified_payload)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (cobro.store, cobro.order_id, cobro.original_id, owner, plan_code, cobro.product_id,
             cobro.base_plan_id, start, cobro.period_end, cobro.price_micros, cobro.currency,
             cobro.region_code, cobro.environment, sub["subscription_id"], json.dumps(cobro.payload)))
        if cobro.environment == "production" and cobro.price_micros is not None and cobro.currency:
            custom = {"currency": cobro.currency, "value": meta_capi.value(cobro.price_micros),
                      "content_ids": [plan_code], "content_type": "product", "num_items": 1,
                      "_country": cobro.region_code}
            meta_capi.enqueue(c, owner, "Purchase", f"pur:{cobro.order_id}", custom)
            if prev["n"] == 0:
                meta_capi.enqueue(c, owner, "Subscribe", f"sub:{cobro.order_id}",
                                  {**custom, "order_id": cobro.order_id})
        return {"estado": "concedido", "ends_at": cobro.period_end, "account_id": owner}


def revocar_orden(store: str, order_id: str, motivo: str) -> bool:
    with conn() as c:
        row = c.execute("SELECT subscription_id FROM store_transactions WHERE store = %s AND order_id = %s",
                        (store, order_id)).fetchone()
        if not row or row["subscription_id"] is None:
            return False
        return suscripciones.revoke_in(c, row["subscription_id"], "tienda", motivo) is not None


def revocar_original(store: str, original_id: str, motivo: str) -> int:
    with conn() as c:
        rows = c.execute(
            """SELECT subscription_id FROM store_transactions
               WHERE store = %s AND original_id = %s AND period_end > now()""",
            (store, original_id)).fetchall()
        return sum(1 for r in rows
                   if suscripciones.revoke_in(c, r["subscription_id"], "tienda", motivo))
```

(`_country` lo extrae `meta_capi.build_event` para `user_data.country` y no llega a `custom_data`.)

- [ ] **Step 5: Ejecutar y ver que pasan**

Run: `PYTHONPATH=src QF_TEST_PG_DSN=... .venv/Scripts/python.exe -m pytest tests/test_compras_pg.py tests/test_cuentas_pg.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/qf/comercial/tiendas/compras.py src/qf/comercial/suscripciones.py tests/test_compras_pg.py
git commit -m "Compras: aplicar cobros verificados de forma idempotente y revocar reembolsos"
```

---

## Task 8: API de compras y notificaciones de tienda

**Files:**
- Create: `src/qf/api/compras.py`
- Modify: `src/qf/api/main.py`, `src/qf/api/mensajes.py`
- Test: `tests/test_compras_api.py`

**Interfaces:**
- Consumes: `google_play.fetch/parse/acknowledge/verify_push`, `app_store.verify_transaction/verify_notification`, `compras.aplicar/revocar_orden/revocar_original`, `api.current_account`, `api.require_enabled`.
- Produces:
  - `POST /app/v1/compras/verificar` `{store, product_id, purchase_token?, jws?}` → `{estado, plus, ends_at}`; 409 con `code` ante `TiendaError`; 503 `tienda_no_disponible` si la tienda falla.
  - `POST /app/v1/compras/google/rtdn` → 204.
  - `POST /app/v1/compras/apple/notificaciones` `{signedPayload}` → 204.
  - Las tres rutas exigen `STORE_PURCHASES_ENABLED=1` (503 `compras_deshabilitadas`).

- [ ] **Step 1: Escribir la prueba que falla**

`tests/test_compras_api.py`:

```python
"""Endpoints de compras con la tienda y la BD simuladas."""
import base64
import json
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import compras as api_compras, cuentas as api
from qf.comercial import suscripciones
from qf.comercial.tiendas import Cobro, TiendaError, app_store, compras, google_play
from test_cuentas_api import FakeRedis

ACC = {"account_id": 7, "email": "a@b.com", "display_name": None, "status": "active",
       "email_verified_at": None, "created_at": "2026-10-07T00:00:00Z",
       "store_account_token": "0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c"}
END = datetime(2026, 11, 15, tzinfo=timezone.utc)
COBRO = Cobro("google_play", "GPA.1", "tok", ACC["store_account_token"], "quantfut_plus", "plus-1m",
              datetime(2026, 10, 15, tzinfo=timezone.utc), END, 4_990_000, "USD", "US",
              "production", "activa", {"acknowledgementState": "ACKNOWLEDGEMENT_STATE_PENDING"})


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ACCOUNTS_ENABLED", "1")
    monkeypatch.setenv("STORE_PURCHASES_ENABLED", "1")
    monkeypatch.setattr(api, "_redis", FakeRedis())   # el límite por IP usa Redis
    app = FastAPI()
    app.include_router(api_compras.router)
    app.include_router(api_compras.store_router)
    app.dependency_overrides[api.current_account] = lambda: dict(ACC)
    monkeypatch.setattr(suscripciones, "active_subscription", lambda _id: {"plan_code": "plus_1m"})
    return TestClient(app)


def test_apagado_devuelve_503(monkeypatch, client):
    monkeypatch.setenv("STORE_PURCHASES_ENABLED", "0")
    r = client.post("/app/v1/compras/verificar",
                    json={"store": "google_play", "product_id": "quantfut_plus", "purchase_token": "tok"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "compras_deshabilitadas"


def test_verificar_play_concede_y_reconoce(monkeypatch, client):
    acks = []
    monkeypatch.setattr(google_play, "fetch", lambda tok: COBRO.payload)
    monkeypatch.setattr(google_play, "parse", lambda tok, data: COBRO)
    monkeypatch.setattr(google_play, "acknowledge", lambda pid, tok: acks.append((pid, tok)))
    monkeypatch.setattr(compras, "aplicar",
                        lambda c, acc: {"estado": "concedido", "ends_at": END, "account_id": acc})
    r = client.post("/app/v1/compras/verificar",
                    json={"store": "google_play", "product_id": "quantfut_plus", "purchase_token": "tok"})
    assert r.status_code == 200
    assert r.json()["estado"] == "concedido" and r.json()["plus"] is True
    assert acks == [("quantfut_plus", "tok")]


def test_compra_de_otra_cuenta_devuelve_409_con_codigo(monkeypatch, client):
    monkeypatch.setattr(app_store, "verify_transaction", lambda jws: COBRO)

    def boom(c, acc):
        raise TiendaError("compra_de_otra_cuenta", "Esta compra pertenece a otra cuenta")

    monkeypatch.setattr(compras, "aplicar", boom)
    r = client.post("/app/v1/compras/verificar",
                    json={"store": "app_store", "product_id": "quantfut_plus_1m", "jws": "x.y.z"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "compra_de_otra_cuenta"


def test_tienda_caida_devuelve_503(monkeypatch, client):
    def caida(tok):
        raise ConnectionError("timeout")

    monkeypatch.setattr(google_play, "fetch", caida)
    r = client.post("/app/v1/compras/verificar",
                    json={"store": "google_play", "product_id": "quantfut_plus", "purchase_token": "tok"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "tienda_no_disponible"


def _push(payload):
    return {"message": {"data": base64.b64encode(json.dumps(payload).encode()).decode(),
                        "messageId": "1"}, "subscription": "projects/p/subscriptions/s"}


def test_rtdn_renovacion_vuelve_a_consultar_a_la_tienda(monkeypatch, client):
    applied = []
    monkeypatch.setattr(google_play, "verify_push", lambda auth: None)
    monkeypatch.setattr(google_play, "fetch", lambda tok: COBRO.payload)
    monkeypatch.setattr(google_play, "parse", lambda tok, data: COBRO)
    monkeypatch.setattr(google_play, "acknowledge", lambda pid, tok: None)
    monkeypatch.setattr(compras, "aplicar",
                        lambda c, acc: applied.append(acc) or {"estado": "concedido", "ends_at": END,
                                                               "account_id": 7})
    r = client.post("/app/v1/compras/google/rtdn", headers={"authorization": "Bearer t"},
                    json=_push({"packageName": "com.saptain.quantfut",
                                "subscriptionNotification": {"notificationType": 2,
                                                             "purchaseToken": "tok",
                                                             "subscriptionId": "quantfut_plus"}}))
    assert r.status_code == 204 and applied == [None]


def test_rtdn_reembolso_revoca_la_orden(monkeypatch, client):
    revoked = []
    monkeypatch.setattr(google_play, "verify_push", lambda auth: None)
    monkeypatch.setattr(compras, "revocar_orden", lambda s, o, m: revoked.append((s, o)) or True)
    r = client.post("/app/v1/compras/google/rtdn", headers={"authorization": "Bearer t"},
                    json=_push({"voidedPurchaseNotification": {"purchaseToken": "tok",
                                                               "orderId": "GPA.9"}}))
    assert r.status_code == 204 and revoked == [("google_play", "GPA.9")]


def test_rtdn_sin_autenticar_devuelve_401(monkeypatch, client):
    r = client.post("/app/v1/compras/google/rtdn", json=_push({"testNotification": {}}))
    assert r.status_code == 401


def test_apple_reembolso_revoca(monkeypatch, client):
    revoked = []
    monkeypatch.setattr(app_store, "verify_notification", lambda sp: ("REFUND", None, "2000000123"))
    monkeypatch.setattr(compras, "revocar_orden", lambda s, o, m: revoked.append((s, o)) or True)
    r = client.post("/app/v1/compras/apple/notificaciones", json={"signedPayload": "x.y.z"})
    assert r.status_code == 204 and revoked == [("app_store", "2000000123")]
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_compras_api.py -v`
Expected: FAIL (`ImportError: cannot import name 'compras' from 'qf.api'`).

- [ ] **Step 3: Implementar**

`src/qf/api/compras.py`:

```python
"""Compras de suscripción en Google Play y App Store (db/071).

La app manda el token (Play) o el JWS (Apple); el servidor verifica con la tienda y
concede. Las notificaciones de la tienda solo despiertan: se vuelve a consultar a la
tienda antes de actuar. Apagado por defecto (STORE_PURCHASES_ENABLED=1 para abrir).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from . import cuentas as api
from ..comercial import suscripciones
from ..comercial.tiendas import TiendaError, app_store, compras, google_play

log = logging.getLogger(__name__)
_REVOCADA = 12  # SUBSCRIPTION_REVOKED en RTDN


def require_store() -> None:
    if os.getenv("STORE_PURCHASES_ENABLED", "0") != "1":
        raise HTTPException(503, {"code": "compras_deshabilitadas",
                                  "message": "Las compras todavía no están disponibles"})


router = APIRouter(prefix="/app/v1/compras", tags=["app"],
                   dependencies=[Depends(api.require_enabled), Depends(require_store)])
# Llamadas de las tiendas: sin sesión de cuenta, autenticadas por firma/OIDC.
store_router = APIRouter(prefix="/app/v1/compras", include_in_schema=False,
                         dependencies=[Depends(require_store)])


class VerificarIn(BaseModel):
    store: Literal["google_play", "app_store"]
    product_id: str = Field(min_length=1, max_length=100)
    purchase_token: str | None = Field(default=None, max_length=4096)
    jws: str | None = Field(default=None, max_length=16384)


class VerificarOut(BaseModel):
    estado: Literal["concedido", "pendiente", "sin_acceso"]
    plus: bool
    ends_at: datetime | None


def _tienda_error(e: TiendaError):
    status = 503 if e.code == "tienda_no_configurada" else 409
    raise HTTPException(status, {"code": e.code, "message": e.message})


def _no_disponible(exc: Exception):
    log.warning("tienda no disponible: %s", type(exc).__name__)
    raise HTTPException(503, {"code": "tienda_no_disponible",
                              "message": "La tienda no está disponible. Inténtalo de nuevo"})


@router.post("/verificar", response_model=VerificarOut)
def verificar(body: VerificarIn, request: Request, acc: dict = Depends(api.current_account)):
    api._limit(request, "compras_verificar", 30, 300)
    try:
        if body.store == "google_play":
            if not body.purchase_token:
                raise HTTPException(422, "Falta el token de compra")
            data = google_play.fetch(body.purchase_token)
            cobro = google_play.parse(body.purchase_token, data)
        else:
            if not body.jws:
                raise HTTPException(422, "Falta la transacción firmada")
            cobro = app_store.verify_transaction(body.jws)
        result = compras.aplicar(cobro, acc["account_id"])
        if (body.store == "google_play" and result["estado"] == "concedido"
                and cobro.payload.get("acknowledgementState") != "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"):
            google_play.acknowledge(cobro.product_id, body.purchase_token)
    except TiendaError as e:
        _tienda_error(e)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — red o tienda caída: la app reintentará
        _no_disponible(exc)
    plus = suscripciones.active_subscription(acc["account_id"]) is not None
    return VerificarOut(estado=result["estado"], plus=plus, ends_at=result["ends_at"])


@store_router.post("/google/rtdn", status_code=204)
def google_rtdn(envelope: dict, request: Request):
    # Síncrona a propósito: consulta a Play y a la BD con llamadas bloqueantes; FastAPI la
    # ejecuta en su grupo de hilos sin bloquear el bucle de eventos.
    try:
        google_play.verify_push(request.headers.get("authorization"))
    except TiendaError:
        raise HTTPException(401, "No autenticado") from None
    try:
        note = json.loads(base64.b64decode(envelope["message"]["data"]))
    except (KeyError, ValueError, TypeError):
        return Response(status_code=204)          # mensaje mal formado: no reintentar
    try:
        if voided := note.get("voidedPurchaseNotification"):
            compras.revocar_orden("google_play", voided["orderId"], "Reembolso o anulación en Google Play")
        elif sub := note.get("subscriptionNotification"):
            token = sub["purchaseToken"]
            if sub.get("notificationType") == _REVOCADA:
                compras.revocar_original("google_play", token, "Suscripción revocada en Google Play")
            else:
                data = google_play.fetch(token)
                cobro = google_play.parse(token, data)
                result = compras.aplicar(cobro, None)
                if (result["estado"] == "concedido" and
                        data.get("acknowledgementState") != "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"):
                    google_play.acknowledge(cobro.product_id, token)
    except TiendaError as e:
        log.warning("RTDN descartada: %s", e.code)   # cuenta o producto desconocido: no reintentar
    except Exception as exc:  # noqa: BLE001 — Pub/Sub reintenta ante 5xx
        _no_disponible(exc)
    return Response(status_code=204)


class AppleIn(BaseModel):
    signedPayload: str = Field(min_length=1, max_length=65536)


@store_router.post("/apple/notificaciones", status_code=204)
def apple_notificaciones(body: AppleIn):
    try:
        kind, cobro, transaction_id = app_store.verify_notification(body.signedPayload)
        if cobro is not None:
            compras.aplicar(cobro, None)
        elif kind in ("REFUND", "REVOKE") and transaction_id:
            compras.revocar_orden("app_store", transaction_id, f"{kind} en App Store")
    except TiendaError as e:
        if e.code == "compra_no_valida":
            raise HTTPException(401, "Firma no válida") from None
        log.warning("Notificación de Apple descartada: %s", e.code)
    except Exception as exc:  # noqa: BLE001
        _no_disponible(exc)
    return Response(status_code=204)
```

En `src/qf/api/main.py`: `from .compras import router as compras_router, store_router as compras_store_router` y

```python
app.include_router(compras_router)
app.include_router(compras_store_router)
```

- [ ] **Step 4: Mensajes en 6 idiomas**

Añadir a `CATALOGO` en `src/qf/api/mensajes.py` (sección nueva `# --- compras en tiendas ---`):

```python
    # --- compras en tiendas ---
    "Las compras todavía no están disponibles": (
        "Purchases are not available yet", "As compras ainda não estão disponíveis",
        "Les achats ne sont pas encore disponibles", "Gli acquisti non sono ancora disponibili",
        "Käufe sind noch nicht verfügbar"),
    "La tienda no está disponible. Inténtalo de nuevo": (
        "The store is not available. Please try again", "A loja não está disponível. Tente novamente",
        "La boutique n'est pas disponible. Réessayez", "Lo store non è disponibile. Riprova",
        "Der Store ist nicht verfügbar. Bitte versuche es erneut"),
    "Esta compra pertenece a otra cuenta": (
        "This purchase belongs to another account", "Esta compra pertence a outra conta",
        "Cet achat appartient à un autre compte", "Questo acquisto appartiene a un altro account",
        "Dieser Kauf gehört zu einem anderen Konto"),
    "La compra no está asociada a ninguna cuenta": (
        "The purchase is not linked to any account", "A compra não está associada a nenhuma conta",
        "L'achat n'est associé à aucun compte", "L'acquisto non è associato a nessun account",
        "Der Kauf ist mit keinem Konto verknüpft"),
    "No se reconoce el producto comprado": (
        "The purchased product is not recognized", "O produto comprado não é reconhecido",
        "Le produit acheté n'est pas reconnu", "Il prodotto acquistato non è riconosciuto",
        "Das gekaufte Produkt wird nicht erkannt"),
    "La tienda no reconoce esta compra": (
        "The store does not recognize this purchase", "A loja não reconhece esta compra",
        "La boutique ne reconnaît pas cet achat", "Lo store non riconosce questo acquisto",
        "Der Store erkennt diesen Kauf nicht"),
    "Falta el token de compra": (
        "The purchase token is missing", "Falta o token da compra", "Le jeton d'achat est manquant",
        "Manca il token di acquisto", "Das Kauf-Token fehlt"),
    "Falta la transacción firmada": (
        "The signed transaction is missing", "Falta a transação assinada",
        "La transaction signée est manquante", "Manca la transazione firmata",
        "Die signierte Transaktion fehlt"),
```

- [ ] **Step 5: Ejecutar y ver que pasan**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_compras_api.py tests/test_mensajes.py -v`
Expected: PASS (`test_mensajes.py` comprueba que cada mensaje del código está en el catálogo).

- [ ] **Step 6: Arnés completo**

Run: `./scripts/harness_check.sh`
Expected: `OK. El repo está en buen estado.`

- [ ] **Step 7: Commit**

```bash
git add src/qf/api/compras.py src/qf/api/main.py src/qf/api/mensajes.py tests/test_compras_api.py
git commit -m "Compras: verificación desde la app y notificaciones de Google Play y App Store"
```

---

## Task 9: Dependencias y configuración nativa de la app

**Files:**
- Modify: `apps/mobile/pubspec.yaml`, `apps/mobile/android/app/build.gradle`, `apps/mobile/android/app/src/main/AndroidManifest.xml`, `apps/mobile/android/app/src/main/kotlin/com/saptain/quantfut/MainActivity.kt`, `apps/mobile/ios/Runner/Info.plist`, `apps/mobile/ios/Flutter/Debug.xcconfig`, `apps/mobile/ios/Flutter/Release.xcconfig`, `apps/mobile/.gitignore`
- Create: `apps/mobile/android/meta.properties.example`, `apps/mobile/ios/Flutter/Meta.xcconfig`, `apps/mobile/ios/Runner/{es,en,pt,fr,it,de}.lproj/InfoPlist.strings`

**Interfaces:**
- Produces: canal nativo `quantfut/device`, método `advertising` → `{"id": String?, "limited": bool, "model": String, "os": String}` (Android). Recursos `@string/facebook_app_id`, `@string/facebook_client_token` (vacíos sin `meta.properties`).

- [ ] **Step 1: Paquetes**

Run (desde `apps/mobile`):
`C:\flutter\bin\flutter.bat pub add facebook_app_events:^0.31.0 in_app_purchase:^3.3.1 app_tracking_transparency:^2.0.7 package_info_plus`
Expected: `Changed N dependencies!`

- [ ] **Step 2: IDs de Meta sin inventarlos**

`apps/mobile/android/meta.properties.example`:

```
# Copiar a meta.properties con los valores de developers.facebook.com → App → Configuración básica
# (App ID) y Configuración avanzada (Client Token). El client token está pensado para ir en la app;
# el token de Conversions API NUNCA va aquí.
appId=
clientToken=
```

En `apps/mobile/android/app/build.gradle`, tras el bloque `releaseKeys`:

```groovy
def metaFile = rootProject.file('meta.properties')
def metaProps = new Properties()
if (metaFile.exists()) {
    metaFile.withInputStream { metaProps.load(it) }
}
```

y dentro de `defaultConfig`:

```groovy
        resValue 'string', 'facebook_app_id', metaProps.getProperty('appId', '')
        resValue 'string', 'facebook_client_token', metaProps.getProperty('clientToken', '')
```

y en `dependencies`:

```groovy
    implementation 'com.google.android.gms:play-services-ads-identifier:18.2.0'
```

(`meta.properties` no es secreto, pero se añade a `apps/mobile/.gitignore` hasta que el titular decida versionarlo, para no confirmar un archivo con valores vacíos por error.)

- [ ] **Step 3: Manifiesto**

En `AndroidManifest.xml`, dentro de `<application>` tras los `meta-data` de Firebase:

```xml
        <!-- Meta (spec 2026-10-15): sin arranque ni registro automáticos. Dart inicia el SDK
             solo si la medición de Meta está activa (por defecto sí, desactivable en Perfil).
             El registro automático de compras se apaga además en el panel de Meta: las compras
             las manda el servidor por Conversions API. -->
        <meta-data android:name="com.facebook.sdk.ApplicationId" android:value="@string/facebook_app_id" />
        <meta-data android:name="com.facebook.sdk.ClientToken" android:value="@string/facebook_client_token" />
        <meta-data android:name="com.facebook.sdk.AutoInitEnabled" android:value="false" />
        <meta-data android:name="com.facebook.sdk.AutoLogAppEventsEnabled" android:value="false" />
        <meta-data android:name="com.facebook.sdk.AdvertiserIDCollectionEnabled" android:value="false" />
```

- [ ] **Step 4: Canal del ID de publicidad**

En `MainActivity.kt` añadir el import `import com.google.android.gms.ads.identifier.AdvertisingIdClient` y, al final de `configureFlutterEngine`:

```kotlin
        // ID de publicidad para Meta (madid). Nunca en el hilo principal. Si la persona limitó o
        // borró el ID en los ajustes del teléfono, no se devuelve (política de Google Play).
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "quantfut/device").setMethodCallHandler { call, result ->
            if (call.method != "advertising") { result.notImplemented(); return@setMethodCallHandler }
            Thread {
                val info = try { AdvertisingIdClient.getAdvertisingIdInfo(applicationContext) } catch (e: Exception) { null }
                val limited = info?.isLimitAdTrackingEnabled ?: true
                val id = info?.id?.takeIf { !limited && it != "00000000-0000-0000-0000-000000000000" }
                runOnUiThread {
                    result.success(mapOf("id" to id, "limited" to limited,
                        "model" to Build.MODEL, "os" to Build.VERSION.RELEASE))
                }
            }.start()
        }
```

- [ ] **Step 5: iOS (preparado; se compila en Mac)**

`apps/mobile/ios/Flutter/Meta.xcconfig`:

```
// Valores de developers.facebook.com. Vacíos hasta que el titular los entregue.
QF_FACEBOOK_APP_ID =
QF_FACEBOOK_CLIENT_TOKEN =
```

Añadir al final de `Debug.xcconfig` y `Release.xcconfig`: `#include "Meta.xcconfig"`.

En `Info.plist`, en el diccionario raíz:

```xml
    <key>FacebookAppID</key><string>$(QF_FACEBOOK_APP_ID)</string>
    <key>FacebookClientToken</key><string>$(QF_FACEBOOK_CLIENT_TOKEN)</string>
    <key>FacebookDisplayName</key><string>QuantFut</string>
    <key>FacebookAutoInitEnabled</key><false/>
    <key>FacebookAutoLogAppEventsEnabled</key><false/>
    <key>FacebookAdvertiserIDCollectionEnabled</key><false/>
    <key>NSUserTrackingUsageDescription</key>
    <string>QuantFut uses this identifier to measure which ads bring new users. You can turn it off at any time.</string>
```

y dentro del array `CFBundleURLTypes` → `CFBundleURLSchemes` existente, un segundo esquema `<string>fb$(QF_FACEBOOK_APP_ID)</string>`.

`InfoPlist.strings` (una carpeta `xx.lproj` por idioma en `ios/Runner/`):

- `es.lproj`: `"NSUserTrackingUsageDescription" = "QuantFut usa este identificador para medir qué anuncios atraen nuevos usuarios. Puedes desactivarlo cuando quieras.";`
- `en.lproj`: `"NSUserTrackingUsageDescription" = "QuantFut uses this identifier to measure which ads bring new users. You can turn it off at any time.";`
- `pt.lproj`: `"NSUserTrackingUsageDescription" = "O QuantFut usa este identificador para medir quais anúncios trazem novos usuários. Você pode desativá-lo quando quiser.";`
- `fr.lproj`: `"NSUserTrackingUsageDescription" = "QuantFut utilise cet identifiant pour mesurer quelles publicités attirent de nouveaux utilisateurs. Vous pouvez le désactiver à tout moment.";`
- `it.lproj`: `"NSUserTrackingUsageDescription" = "QuantFut usa questo identificatore per misurare quali annunci portano nuovi utenti. Puoi disattivarlo in qualsiasi momento.";`
- `de.lproj`: `"NSUserTrackingUsageDescription" = "QuantFut verwendet diese Kennung, um zu messen, welche Anzeigen neue Nutzer bringen. Du kannst sie jederzeit deaktivieren.";`

(Registrar las seis carpetas en el proyecto Xcode es un paso de Mac: queda anotado en `PENDIENTES.md` en Task 16.)

- [ ] **Step 6: Compilar Android**

Run: `C:\flutter\bin\flutter.bat build apk --debug`
Expected: `Built build\app\outputs\flutter-apk\app-debug.apk`.

- [ ] **Step 7: Commit**

```bash
git add apps/mobile/pubspec.yaml apps/mobile/pubspec.lock apps/mobile/android apps/mobile/ios apps/mobile/.gitignore
git commit -m "App: dependencias y configuración nativa de Meta, compras y ATT"
```

---

## Task 10: Fachada de Meta en la app

**Files:**
- Create: `apps/mobile/lib/core/meta_events.dart`
- Modify: `apps/mobile/lib/core/firebase_startup.dart`
- Test: `apps/mobile/test/meta_events_test.dart`

**Interfaces:**
- Consumes: `FirebaseServices.adsAllowed` (Task 11 lo añade; en esta tarea `MetaEvents` recibe el valor por `apply`).
- Produces:
  - `const metaConfigured = bool.fromEnvironment('QF_META_ENABLED')`
  - `abstract class MetaSink { Future<void> start({required bool tracking}); Future<void> stop(); Future<void> identify(String externalId, String? email); Future<void> forget(); Future<void> log(String name, Map<String, Object> parameters, {double? valueToSum}); Future<String?> anonymousId(); }`
  - `class MetaEvents { static MetaEvents? current; MetaEvents(MetaSink sink, {bool configured}); bool get active; Future<void> apply(bool allowed); Future<void> identify(Map<String, dynamic> me); Future<void> forget(); Future<void> viewMatch(String id); Future<void> viewVip(); Future<void> search(String text); Future<void> initiateCheckout(String planCode, double price, String currency); Future<void> completeTutorial(); Future<void> adImpression(); Future<void> invite(); Future<Map<String, dynamic>?> device(); }`
  - `List<String> extinfo({required bool ios, required String package, required String version, required String build, required String os, required String model, required String locale, required String tzAbbr, required double width, required double height, required double density, required int cores, required String tzName})`

- [ ] **Step 1: Escribir la prueba que falla**

`apps/mobile/test/meta_events_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/meta_events.dart';

class FakeSink implements MetaSink {
  final calls = <String>[];
  final logs = <(String, Map<String, Object>, double?)>[];
  @override
  Future<void> start({required bool tracking}) async => calls.add('start:$tracking');
  @override
  Future<void> stop() async => calls.add('stop');
  @override
  Future<void> identify(String externalId, String? email) async =>
      calls.add('identify:$externalId:$email');
  @override
  Future<void> forget() async => calls.add('forget');
  @override
  Future<void> log(String name, Map<String, Object> parameters, {double? valueToSum}) async =>
      logs.add((name, parameters, valueToSum));
  @override
  Future<String?> anonymousId() async => 'XZ1';
}

void main() {
  test('Sin configurar (sin App ID) no arranca el SDK aunque el ajuste esté activo', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: false);
    await meta.apply(true);
    await meta.viewVip();
    expect(sink.calls, isEmpty);
    expect(sink.logs, isEmpty);
  });

  test('Activo: arranca y registra eventos estándar con nombres de Meta', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: true, tracking: () async => true);
    await meta.apply(true);
    await meta.viewMatch('m-1');
    await meta.initiateCheckout('plus_1m', 4.99, 'USD');
    expect(sink.calls, ['start:true']);
    expect(sink.logs[0].$1, 'fb_mobile_content_view');
    expect(sink.logs[0].$2, {'fb_content_type': 'product', 'fb_content_id': 'match:m-1'});
    expect(sink.logs[1].$1, 'fb_mobile_initiated_checkout');
    expect(sink.logs[1].$2['fb_currency'], 'USD');
    expect(sink.logs[1].$3, 4.99);
  });

  test('Desactivar para el SDK y deja de registrar', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: true, tracking: () async => true);
    await meta.apply(true);
    await meta.apply(false);
    await meta.search('barcelona');
    expect(sink.calls, ['start:true', 'stop']);
    expect(sink.logs, isEmpty);
  });

  test('La búsqueda se recorta a 100 caracteres', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: true, tracking: () async => true);
    await meta.apply(true);
    await meta.search('x' * 150);
    expect((sink.logs.single.$2['fb_search_string'] as String).length, 100);
  });

  test('Identificar usa el external_id del servidor, no el id de cuenta', () async {
    final sink = FakeSink();
    final meta = MetaEvents(sink, configured: true, tracking: () async => true);
    await meta.apply(true);
    await meta.identify({
      'account': {'account_id': 7, 'email': 'a@b.co'},
      'meta_external_id': 'abc123',
    });
    expect(sink.calls.last, 'identify:abc123:a@b.co');
  });

  test('extinfo tiene 16 posiciones en el orden de Meta', () {
    final values = extinfo(
      ios: false, package: 'com.saptain.quantfut', version: '1.0.0', build: '1', os: '14',
      model: 'Pixel 8', locale: 'es_CO', tzAbbr: 'COT', width: 1080, height: 2400,
      density: 2.75, cores: 8, tzName: 'America/Bogota');
    expect(values.length, 16);
    expect(values[0], 'a2');
    expect(values[4], '14');
    expect(values[9], '1080');
    expect(values[15], 'America/Bogota');
  });
}
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `C:\flutter\bin\flutter.bat test test/meta_events_test.dart`
Expected: FAIL (`Target of URI doesn't exist: 'package:gobet/core/meta_events.dart'`).

- [ ] **Step 3: Implementar**

`apps/mobile/lib/core/meta_events.dart`:

```dart
import 'dart:io';
import 'dart:ui' as ui;

import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:facebook_app_events/facebook_app_events.dart';
import 'package:flutter/services.dart';
import 'package:package_info_plus/package_info_plus.dart';

// Sin `typedef JsonMap`: live_api.dart ya lo define e importa este archivo; dos typedefs con
// el mismo nombre harían ambiguo el import en store_purchases.dart.

/// Sin App ID real no se arranca el SDK (los recursos nativos quedan vacíos).
const metaConfigured = bool.fromEnvironment('QF_META_ENABLED');

/// Lo que la app manda a Meta con el SDK: solo lo que únicamente ella conoce. Registro,
/// suscripciones, cobros y desbloqueos los manda el servidor por Conversions API.
abstract class MetaSink {
  Future<void> start({required bool tracking});
  Future<void> stop();
  Future<void> identify(String externalId, String? email);
  Future<void> forget();
  Future<void> log(String name, Map<String, Object> parameters, {double? valueToSum});
  Future<String?> anonymousId();
}

class FacebookSink implements MetaSink {
  final _fb = FacebookAppEvents();
  bool _initialized = false;

  @override
  Future<void> start({required bool tracking}) async {
    if (!_initialized) {
      await _fb.initializeSdk();
      _initialized = true;
    }
    await _fb.setAdvertiserTracking(enabled: tracking);
    await _fb.setAdvertiserIdCollectionEnabled(tracking);
    await _fb.setAutoLogAppEventsEnabled(true);
    await _fb.activateApp();
  }

  @override
  Future<void> stop() async {
    if (!_initialized) return;
    await _fb.setAutoLogAppEventsEnabled(false);
    await _fb.setAdvertiserIdCollectionEnabled(false);
    await _fb.clearUserID();
    await _fb.clearUserData();
  }

  @override
  Future<void> identify(String externalId, String? email) async {
    await _fb.setUserID(externalId);
    if (email != null) await _fb.setUserData(email: email);
  }

  @override
  Future<void> forget() async {
    if (!_initialized) return;
    await _fb.clearUserID();
    await _fb.clearUserData();
  }

  @override
  Future<void> log(String name, Map<String, Object> parameters, {double? valueToSum}) =>
      _fb.logEvent(name: name, parameters: parameters, valueToSum: valueToSum);

  @override
  Future<String?> anonymousId() => _initialized ? _fb.getAnonymousId() : Future.value(null);
}

/// iOS: pide ATT una vez; Android: el ID de publicidad decide (canal nativo).
Future<bool> platformTracking() async {
  if (!Platform.isIOS) return true;
  var status = await AppTrackingTransparency.trackingAuthorizationStatus;
  if (status == TrackingStatus.notDetermined) {
    status = await AppTrackingTransparency.requestTrackingAuthorization();
  }
  return status == TrackingStatus.authorized;
}

class MetaEvents {
  MetaEvents(this.sink, {this.configured = metaConfigured, Future<bool> Function()? tracking})
    : _tracking = tracking ?? platformTracking;
  static MetaEvents? current;
  final MetaSink sink;
  final bool configured;
  final Future<bool> Function() _tracking;
  bool _active = false, _trackingAllowed = false;
  bool get active => _active;

  Future<void> apply(bool allowed) async {
    if (!configured) return;
    try {
      if (allowed && !_active) {
        _trackingAllowed = await _tracking();
        await sink.start(tracking: _trackingAllowed);
        _active = true;
      } else if (!allowed && _active) {
        await sink.stop();
        _active = false;
      }
    } catch (_) {
      /* La medición nunca puede impedir usar la app. */
    }
  }

  Future<void> identify(Map<String, dynamic> me) async {
    final id = me['meta_external_id'];
    if (!_active || id is! String) return;
    final email = (me['account'] as Map?)?['email'] as String?;
    try {
      await sink.identify(id, email);
    } catch (_) {}
  }

  Future<void> forget() async {
    try {
      await sink.forget();
    } catch (_) {}
  }

  Future<void> _log(String name, Map<String, Object> parameters, {double? valueToSum}) async {
    if (!_active) return;
    try {
      await sink.log(name, parameters, valueToSum: valueToSum);
    } catch (_) {}
  }

  Future<void> viewMatch(String id) => _log('fb_mobile_content_view',
      {'fb_content_type': 'product', 'fb_content_id': 'match:$id'});
  Future<void> viewVip() => _log('fb_mobile_content_view',
      {'fb_content_type': 'product_group', 'fb_content_id': 'vip'});
  Future<void> search(String text) => _log('fb_mobile_search', {
    'fb_search_string': text.length > 100 ? text.substring(0, 100) : text,
    'fb_success': 1,
  });
  Future<void> initiateCheckout(String planCode, double price, String currency) => _log(
    'fb_mobile_initiated_checkout',
    {'fb_content_id': planCode, 'fb_content_type': 'product', 'fb_currency': currency,
     'fb_num_items': 1, 'fb_payment_info_available': 1},
    valueToSum: price,
  );
  Future<void> completeTutorial() =>
      _log('fb_mobile_tutorial_completion', {'fb_success': 1, 'fb_content_id': 'guide'});
  Future<void> adImpression() => _log('AdImpression', {'ad_type': 'rewarded_video'});
  Future<void> invite() => _log('Invite', {});

  /// Datos para POST /app/v1/meta/dispositivo; null si Meta no está activo.
  Future<Map<String, dynamic>?> device() async {
    if (!_active) return null;
    final anon = await sink.anonymousId();
    if (anon == null) return null;
    final info = await PackageInfo.fromPlatform();
    String? madid;
    var model = '', os = Platform.operatingSystemVersion;
    if (Platform.isAndroid) {
      final ad = await const MethodChannel('quantfut/device')
          .invokeMapMethod<String, Object?>('advertising');
      madid = ad?['id'] as String?;
      model = ad?['model'] as String? ?? '';
      os = ad?['os'] as String? ?? os;
    } else if (_trackingAllowed) {
      final idfa = await AppTrackingTransparency.getAdvertisingIdentifier();
      if (idfa != '00000000-0000-0000-0000-000000000000') madid = idfa;
    }
    final view = ui.PlatformDispatcher.instance.views.first;
    final now = DateTime.now();
    return {
      'anon_id': anon,
      'platform': Platform.isIOS ? 'ios' : 'android',
      'madid': madid,
      'advertiser_tracking_enabled': _trackingAllowed && madid != null,
      'extinfo': extinfo(
        ios: Platform.isIOS, package: info.packageName, version: info.version,
        build: info.buildNumber, os: os, model: model, locale: Platform.localeName,
        tzAbbr: now.timeZoneName, width: view.physicalSize.width,
        height: view.physicalSize.height, density: view.devicePixelRatio,
        cores: Platform.numberOfProcessors, tzName: now.timeZoneName),
    };
  }
}

/// Orden fijo de «extinfo» (Conversions API para apps); cadenas vacías donde falte.
List<String> extinfo({
  required bool ios, required String package, required String version, required String build,
  required String os, required String model, required String locale, required String tzAbbr,
  required double width, required double height, required double density, required int cores,
  required String tzName,
}) => [
  ios ? 'i2' : 'a2', package, version, build, os, model, locale, tzAbbr, '',
  width.round().toString(), height.round().toString(), density.toStringAsFixed(2),
  '$cores', '', '', tzName,
].map((v) => v.length > 100 ? v.substring(0, 100) : v).toList();
```

- [ ] **Step 4: Crear la instancia al arrancar**

En `apps/mobile/lib/core/firebase_startup.dart`:

```dart
import 'meta_events.dart';
...
Future<void> initializeFirebase() async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  await FirebaseServices.initialize();
  MetaEvents.current ??= MetaEvents(FacebookSink());
}
```

(El SDK no se inicia aquí: lo inicia `LiveShell` tras el primer fotograma —Task 12—, porque en iOS la ventana de ATT necesita la app visible.)

- [ ] **Step 5: Ejecutar y ver que pasa**

Run: `C:\flutter\bin\flutter.bat test test/meta_events_test.dart`
Expected: 6 PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/mobile/lib/core/meta_events.dart apps/mobile/lib/core/firebase_startup.dart apps/mobile/test/meta_events_test.dart
git commit -m "App: fachada de Meta con arranque controlado y eventos estándar"
```

---

## Task 11: Seguimiento encendido por defecto y ajuste de Meta en Perfil

**Files:**
- Modify: `apps/mobile/lib/core/firebase_services.dart`, `apps/mobile/lib/core/firebase_preferences.dart`, `apps/mobile/lib/product/live_api.dart` (`syncPreferences`)
- Modify: ARB vía `apps/mobile/tool/l10n_add.py`
- Test: `apps/mobile/test/consent_defaults_test.dart`

**Interfaces:**
- Consumes: `MetaEvents.current.apply(bool)`.
- Produces: `FirebaseServices.adsAllowed` (clave `ads_consent`), `FirebaseServices.setAdsConsent(bool)`, función pura `bool consentDefault(bool? stored) => stored ?? true`.

- [ ] **Step 1: Escribir la prueba que falla**

`apps/mobile/test/consent_defaults_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/core/firebase_services.dart';

void main() {
  test('Quien nunca eligió queda con el seguimiento activo', () {
    expect(consentDefault(null), isTrue);
  });
  test('Una negativa explícita guardada se conserva', () {
    expect(consentDefault(false), isFalse);
  });
  test('Una aceptación guardada se conserva', () {
    expect(consentDefault(true), isTrue);
  });
}
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `C:\flutter\bin\flutter.bat test test/consent_defaults_test.dart`
Expected: FAIL (`The function 'consentDefault' isn't defined`).

- [ ] **Step 3: Implementar en `FirebaseServices`**

En `apps/mobile/lib/core/firebase_services.dart`:

1. Import: `import 'meta_events.dart';`
2. Tras la clase (nivel superior):

```dart
/// Seguimiento encendido por defecto en todo el mundo (decisión del titular, 2026-10-15);
/// lo que la persona eligió antes, incluido un «no», se respeta siempre.
bool consentDefault(bool? stored) => stored ?? true;
```

3. Campo nuevo junto a los demás: `bool adsAllowed = true;`
4. En `initialize()` sustituir las dos lecturas y añadir la de Meta:

```dart
    services.analyticsAllowed = consentDefault(
      await services.preferences.getBool('analytics_consent'),
    );
    services.diagnosticsAllowed = consentDefault(
      await services.preferences.getBool('diagnostics_consent'),
    );
    services.adsAllowed = consentDefault(
      await services.preferences.getBool('ads_consent'),
    );
```

5. Método nuevo tras `setConsent`:

```dart
  Future<void> setAdsConsent(bool allowed) async {
    adsAllowed = allowed;
    await preferences.setBool('ads_consent', allowed);
    await MetaEvents.current?.apply(allowed);
    notifyListeners();
  }
```

6. En `clearAccountData()` añadir al final: `await MetaEvents.current?.forget();`

- [ ] **Step 4: Enviar la preferencia al servidor**

En `apps/mobile/lib/product/live_api.dart`, `syncPreferences()`, añadir al cuerpo:

```dart
        'ads_measurement': services.adsAllowed,
```

- [ ] **Step 5: Textos en 6 idiomas**

Crear `%TEMP%\meta_l10n.json` (fuera del repo, para no confirmarlo) con:

```json
{
  "prefsAdsTitle": {"es": "Medición de anuncios (Meta)", "en": "Ad measurement (Meta)", "pt": "Medição de anúncios (Meta)", "fr": "Mesure des publicités (Meta)", "it": "Misurazione degli annunci (Meta)", "de": "Anzeigenmessung (Meta)"},
  "prefsAdsBody": {"es": "Comparte con Meta datos cifrados de tu cuenta, del dispositivo y de tus compras para medir qué anuncios funcionan. En California equivale a «No compartir mis datos» cuando lo desactivas.", "en": "Shares encrypted account, device and purchase data with Meta to measure which ads work. In California, turning it off means “Do not share my data”.", "pt": "Compartilha com a Meta dados criptografados da sua conta, do dispositivo e das suas compras para medir quais anúncios funcionam. Na Califórnia, desativá-lo equivale a «Não compartilhar meus dados».", "fr": "Partage avec Meta des données chiffrées de votre compte, de l'appareil et de vos achats pour mesurer quelles publicités fonctionnent. En Californie, le désactiver équivaut à « Ne pas partager mes données ».", "it": "Condivide con Meta dati cifrati del tuo account, del dispositivo e dei tuoi acquisti per misurare quali annunci funzionano. In California, disattivarlo equivale a «Non condividere i miei dati».", "de": "Teilt verschlüsselte Konto-, Geräte- und Kaufdaten mit Meta, um zu messen, welche Anzeigen wirken. In Kalifornien bedeutet das Deaktivieren „Meine Daten nicht teilen“."}
}
```

Run (desde `apps/mobile`): `../../.venv/Scripts/python.exe tool/l10n_add.py "$TEMP/meta_l10n.json"` y luego `C:\flutter\bin\flutter.bat gen-l10n`.

- [ ] **Step 6: Interruptor en Preferencias**

En `apps/mobile/lib/core/firebase_preferences.dart`, tras el `SwitchListTile` de diagnóstico:

```dart
        SwitchListTile(
          key: const ValueKey('prefs-ads'),
          title: Text(context.l10n.prefsAdsTitle),
          subtitle: Text(context.l10n.prefsAdsBody),
          value: services.adsAllowed,
          onChanged: busy
              ? null
              : (value) => change(() async {
                  await services.setAdsConsent(value);
                  await widget.api.syncPreferences();
                }),
        ),
```

(`change` ya gestiona `busy` y errores en esa pantalla; si `widget.api.syncPreferences` no está disponible sin sesión, `syncPreferences` vuelve sin hacer nada.)

- [ ] **Step 7: Ejecutar pruebas**

Run: `C:\flutter\bin\flutter.bat test test/consent_defaults_test.dart test/l10n_test.dart test/firebase_security_test.dart`
Expected: PASS. Ejecutar después `C:\flutter\bin\flutter.bat test` completo: si alguna prueba existente suponía consentimiento apagado por defecto, actualizar su expectativa al nuevo valor por defecto (es la decisión del titular), sin tocar las que guardan un `false` explícito.

- [ ] **Step 8: Commit**

```bash
git add apps/mobile/lib apps/mobile/test/consent_defaults_test.dart
git commit -m "App: seguimiento activo por defecto, ajuste de Meta en Preferencias (6 idiomas)"
```

---

## Task 12: Eventos del SDK en las pantallas y datos del dispositivo

**Files:**
- Modify: `apps/mobile/lib/product/live_shell.dart`, `live_detail.dart`, `live_home.dart`, `live_guide.dart`, `live_ads.dart`, `live_rewards.dart`, `live_api.dart`
- Test: `apps/mobile/test/meta_events_test.dart` (añadir prueba de `syncMetaDevice`)

**Interfaces:**
- Consumes: `MetaEvents.current` y sus métodos (Task 10), `FirebaseServices.adsAllowed` (Task 11).
- Produces: `QuantFutApi.syncMetaDevice() -> Future<void>`; `updateAccount()` llama a `MetaEvents.current?.identify(account)`.

- [ ] **Step 1: Escribir la prueba que falla**

Añadir a `apps/mobile/test/meta_events_test.dart`:

```dart
  test('Sin sesión no se manda el dispositivo', () async {
    final api = QuantFutApi(base: Uri.parse('https://example.invalid'));
    await api.syncMetaDevice(); // no lanza ni hace peticiones
    expect(api.signedIn, isFalse);
  });
```

(import `package:gobet/product/live_api.dart`).

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `C:\flutter\bin\flutter.bat test test/meta_events_test.dart`
Expected: FAIL (`The method 'syncMetaDevice' isn't defined`).

- [ ] **Step 3: API de la app**

En `apps/mobile/lib/product/live_api.dart` (import `../core/meta_events.dart`):

```dart
  Future<void> updateAccount() async {
    if (!signedIn) return;
    account = jsonMap(await request('/app/v1/me'));
    notifyListeners();
    await MetaEvents.current?.identify(account!);
  }
```

```dart
  /// IDs del dispositivo para Conversions API (anon_id, madid, extinfo). Solo con sesión y
  /// con Meta activo; un fallo no afecta al uso de la app.
  Future<void> syncMetaDevice() async {
    if (!signedIn) return;
    final device = await MetaEvents.current?.device();
    if (device == null) return;
    try {
      await request('/app/v1/meta/dispositivo', body: device);
    } catch (_) {
      /* Se reintenta en el próximo arranque. */
    }
  }
```

- [ ] **Step 4: Arranque del SDK en la pantalla principal**

En `live_shell.dart`, `initState`, sustituir `WidgetsBinding.instance.addPostFrameCallback((_) => openNotification());` por:

```dart
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      openNotification();
      await MetaEvents.current?.apply(services?.adsAllowed ?? true);
      await api.syncMetaDevice();
    });
```

(import `../core/meta_events.dart`.)

- [ ] **Step 5: Eventos en cada pantalla**

- `live_detail.dart`, `_LiveMatchDetailState`: añadir

```dart
  @override
  void initState() {
    super.initState();
    MetaEvents.current?.viewMatch(widget.id);
  }
```

- `live_vip.dart`, `_LiveVipScreenState`: añadir `initState` con `MetaEvents.current?.viewVip();` (Task 13 añade el resto de esta pantalla).
- `live_home.dart`, `_toggleSearch()`: antes de `setState`, `if (_searching && search.trim().isNotEmpty) MetaEvents.current?.search(search.trim());` (se registra al cerrar la búsqueda con texto, no en cada tecla).
- `live_guide.dart`: envolver el `ListView` en

```dart
      body: NotificationListener<ScrollEndNotification>(
        onNotification: (n) {
          if (n.metrics.extentAfter == 0) MetaEvents.current?.completeTutorial();
          return false;
        },
        child: ListView(
```

  (y cerrar el paréntesis). El SDK de Meta agrupa eventos repetidos; registrar más de una vez por sesión no rompe nada.
- `live_ads.dart`, `show()`: tras `await ad.show(...)` y antes de `await closed.future`, `MetaEvents.current?.adImpression();`
- `live_rewards.dart`, botón `coins-share`: `onPressed: () { MetaEvents.current?.invite(); SharePlus.instance.share(ShareParams(text: inviteShareText(l10n, base, '$myCode'))); },`

- [ ] **Step 6: Ejecutar pruebas y análisis**

Run: `C:\flutter\bin\flutter.bat analyze` y `C:\flutter\bin\flutter.bat test`
Expected: sin incidencias; todas PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/mobile/lib apps/mobile/test/meta_events_test.dart
git commit -m "App: eventos de Meta en pantallas y envío de datos del dispositivo"
```

---

## Task 13: Compras en la pantalla VIP

**Files:**
- Create: `apps/mobile/lib/product/store_purchases.dart`
- Modify: `apps/mobile/lib/product/live_api.dart` (`verifyPurchase`), `live_vip.dart`, `live_shell.dart`
- Modify: ARB vía `l10n_add.py`
- Test: `apps/mobile/test/store_purchases_test.dart`

**Interfaces:**
- Consumes: `QuantFutApi.account['store_account_token']`, `QuantFutApi.plus`, `POST /app/v1/compras/verificar` (Task 8), catálogo con `play_product_id`/`play_base_plan_id`/`apple_product_id` (Task 4), `MetaEvents.current.initiateCheckout`.
- Produces:
  - `QuantFutApi.verifyPurchase({required String store, required String productId, required String token}) -> Future<JsonMap>`
  - `enum StoreState { idle, loading, unavailable, verifying, pending, granted, failed, manage }`
  - `abstract class StoreBackend { Stream<List<PurchaseDetails>> get purchases; Future<bool> available(); Future<List<ProductDetails>> products(Set<String> ids); Future<bool> buy(ProductDetails product, String accountToken); Future<void> complete(PurchaseDetails purchase); Future<void> restore(String accountToken); }`
  - `class StoreController extends ChangeNotifier { StoreController(QuantFutApi api, {StoreBackend? backend, bool? ios}); StoreState state; String? error; Map<String, ProductDetails> byPlan; void listen(); Future<void> load(List<JsonMap> plans); Future<void> buy(String planCode); Future<void> restore(); }`
  - `String? storeProductId(JsonMap plan, {required bool ios})`, `String? basePlanOf(ProductDetails p)`, `Uri manageSubscriptionsUri({required bool ios})`.

- [ ] **Step 1: Escribir la prueba que falla**

`apps/mobile/test/store_purchases_test.dart`:

```dart
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:gobet/product/live_api.dart';
import 'package:gobet/product/store_purchases.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

class FakeApi extends QuantFutApi {
  FakeApi({this.plusNow = false, this.answer = 'concedido'}) : super(base: Uri.parse('https://x.invalid'));
  final bool plusNow;
  final String answer;
  final verified = <String>[];
  @override
  bool get plus => plusNow;
  @override
  bool get signedIn => true;
  @override
  JsonMap? get account => {'store_account_token': '0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c'};
  @override
  Future<JsonMap> verifyPurchase({required String store, required String productId,
      required String token}) async {
    verified.add('$store:$productId:$token');
    if (answer == 'error') throw const ApiFailure('La tienda no está disponible', 503);
    return {'estado': answer, 'plus': answer == 'concedido'};
  }
  @override
  Future<void> updateAccount() async {}
}

class FakeBackend implements StoreBackend {
  final controller = StreamController<List<PurchaseDetails>>.broadcast();
  final bought = <String>[];
  final completed = <String>[];
  @override
  Stream<List<PurchaseDetails>> get purchases => controller.stream;
  @override
  Future<bool> available() async => true;
  @override
  Future<List<ProductDetails>> products(Set<String> ids) async => [
    ProductDetails(id: 'quantfut_plus_1m', title: 'Plus', description: '', price: r'$4.99',
        rawPrice: 4.99, currencyCode: 'USD'),
  ];
  @override
  Future<bool> buy(ProductDetails product, String accountToken) async {
    bought.add('${product.id}:$accountToken');
    return true;
  }
  @override
  Future<void> complete(PurchaseDetails purchase) async => completed.add(purchase.productID);
  @override
  Future<void> restore(String accountToken) async {}
}

PurchaseDetails _purchase(PurchaseStatus status) => PurchaseDetails(
  productID: 'quantfut_plus_1m',
  verificationData: PurchaseVerificationData(
      localVerificationData: '', serverVerificationData: 'jws-123', source: 'app_store'),
  transactionDate: '0',
  status: status,
)..pendingCompletePurchase = true;

const plans = [
  {'plan_code': 'plus_1m', 'apple_product_id': 'quantfut_plus_1m',
   'play_product_id': 'quantfut_plus', 'play_base_plan_id': 'plus-1m'},
];

// La verificación encadena varios `await`: un retardo real (no un solo microtask) deja
// terminar el manejador del stream antes de comprobar.
Future<void> _flush() => Future<void>.delayed(const Duration(milliseconds: 10));

void main() {
  test('Comprar pasa el token de cuenta a la tienda', () async {
    final backend = FakeBackend();
    final store = StoreController(FakeApi(), backend: backend, ios: true)..listen();
    await store.load(plans);
    await store.buy('plus_1m');
    expect(backend.bought, ['quantfut_plus_1m:0b8f3a7e-1f9b-4c2e-9d55-0c6e3f1a2b3c']);
  });

  test('Solo se completa la compra cuando el servidor concede', () async {
    final backend = FakeBackend();
    final api = FakeApi();
    final store = StoreController(api, backend: backend, ios: true)..listen();
    backend.controller.add([_purchase(PurchaseStatus.purchased)]);
    await _flush();
    await _flush();
    expect(api.verified, ['app_store:quantfut_plus_1m:jws-123']);
    expect(backend.completed, ['quantfut_plus_1m']);
    expect(store.state, StoreState.granted);
  });

  test('Si el servidor falla no se completa: la tienda la re-entrega después', () async {
    final backend = FakeBackend();
    final store = StoreController(FakeApi(answer: 'error'), backend: backend, ios: true)..listen();
    backend.controller.add([_purchase(PurchaseStatus.purchased)]);
    await _flush();
    await _flush();
    expect(backend.completed, isEmpty);
    expect(store.state, StoreState.failed);
  });

  test('Compra pendiente muestra pendiente y no verifica', () async {
    final backend = FakeBackend();
    final api = FakeApi();
    final store = StoreController(api, backend: backend, ios: true)..listen();
    backend.controller.add([_purchase(PurchaseStatus.pending)]);
    await _flush();
    expect(store.state, StoreState.pending);
    expect(api.verified, isEmpty);
  });

  test('Con Plus vigente no se lanza otra compra: se gestiona en la tienda', () async {
    final backend = FakeBackend();
    final store = StoreController(FakeApi(plusNow: true), backend: backend, ios: true)..listen();
    await store.load(plans);
    await store.buy('plus_1m');
    expect(backend.bought, isEmpty);
    expect(store.state, StoreState.manage);
  });

  test('Enlace de gestión según la tienda', () {
    expect(manageSubscriptionsUri(ios: false).toString(),
        'https://play.google.com/store/account/subscriptions?package=com.saptain.quantfut');
    expect(manageSubscriptionsUri(ios: true).toString(),
        'https://apps.apple.com/account/subscriptions');
  });
}
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `C:\flutter\bin\flutter.bat test test/store_purchases_test.dart`
Expected: FAIL (`Target of URI doesn't exist: 'package:gobet/product/store_purchases.dart'`).

- [ ] **Step 3: Verificación en el cliente HTTP**

En `apps/mobile/lib/product/live_api.dart`:

```dart
  Future<JsonMap> verifyPurchase({
    required String store,
    required String productId,
    required String token,
  }) async => jsonMap(
    await request(
      '/app/v1/compras/verificar',
      body: {
        'store': store,
        'product_id': productId,
        if (store == 'google_play') 'purchase_token': token else 'jws': token,
      },
    ),
  );
```

y en `apiTraceName`: `if (path.startsWith('/app/v1/compras/')) return 'qf_store_request';`

- [ ] **Step 4: Implementar el controlador**

`apps/mobile/lib/product/store_purchases.dart`:

```dart
import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:in_app_purchase_android/in_app_purchase_android.dart';

import '../core/meta_events.dart';
import 'live_api.dart';

enum StoreState { idle, loading, unavailable, verifying, pending, granted, failed, manage }

String? storeProductId(JsonMap plan, {required bool ios}) =>
    (ios ? plan['apple_product_id'] : plan['play_product_id']) as String?;

/// En Play cada plan base de una suscripción llega como un ProductDetails propio.
String? basePlanOf(ProductDetails p) {
  if (p is! GooglePlayProductDetails) return null;
  final i = p.subscriptionIndex;
  final offers = p.productDetails.subscriptionOfferDetails;
  if (i == null || offers == null) return null;
  return offers[i].offerId == null ? offers[i].basePlanId : null;
}

Uri manageSubscriptionsUri({required bool ios}) => ios
    ? Uri.parse('https://apps.apple.com/account/subscriptions')
    : Uri.parse('https://play.google.com/store/account/subscriptions?package=com.saptain.quantfut');

abstract class StoreBackend {
  Stream<List<PurchaseDetails>> get purchases;
  Future<bool> available();
  Future<List<ProductDetails>> products(Set<String> ids);
  Future<bool> buy(ProductDetails product, String accountToken);
  Future<void> complete(PurchaseDetails purchase);
  Future<void> restore(String accountToken);
}

class PluginStore implements StoreBackend {
  InAppPurchase get _iap => InAppPurchase.instance;
  @override
  Stream<List<PurchaseDetails>> get purchases => _iap.purchaseStream;
  @override
  Future<bool> available() => _iap.isAvailable();
  @override
  Future<List<ProductDetails>> products(Set<String> ids) async =>
      (await _iap.queryProductDetails(ids)).productDetails;
  @override
  Future<bool> buy(ProductDetails product, String accountToken) => _iap.buyNonConsumable(
    // applicationUserName → obfuscatedAccountId (Play) / appAccountToken (StoreKit 2).
    purchaseParam: product is GooglePlayProductDetails
        ? GooglePlayPurchaseParam(productDetails: product, applicationUserName: accountToken)
        : PurchaseParam(productDetails: product, applicationUserName: accountToken),
  );
  @override
  Future<void> complete(PurchaseDetails purchase) => _iap.completePurchase(purchase);
  @override
  Future<void> restore(String accountToken) =>
      _iap.restorePurchases(applicationUserName: accountToken);
}

/// El acceso lo concede el servidor tras verificar con la tienda; la app solo transporta
/// el token/JWS y completa la compra cuando el servidor contesta.
class StoreController extends ChangeNotifier {
  StoreController(this.api, {StoreBackend? backend, bool? ios})
    : backend = backend ?? PluginStore(),
      ios = ios ?? Platform.isIOS;
  final QuantFutApi api;
  final StoreBackend backend;
  final bool ios;
  StoreState state = StoreState.idle;
  String? error;
  final Map<String, ProductDetails> byPlan = {};
  StreamSubscription<List<PurchaseDetails>>? _sub;

  String get _store => ios ? 'app_store' : 'google_play';
  String? get _token => api.account?['store_account_token'] as String?;

  void _set(StoreState value, [String? message]) {
    state = value;
    error = message;
    notifyListeners();
  }

  /// Desde el arranque: la tienda re-entrega aquí compras sin completar.
  void listen() => _sub ??= backend.purchases.listen(_onPurchases);

  Future<void> load(List<JsonMap> plans) async {
    listen();
    _set(StoreState.loading);
    try {
      if (!await backend.available()) return _set(StoreState.unavailable);
      final ids = plans.map((p) => storeProductId(p, ios: ios)).whereType<String>().toSet();
      final found = await backend.products(ids);
      byPlan.clear();
      for (final plan in plans) {
        final id = storeProductId(plan, ios: ios);
        final match = found.where((p) =>
            p.id == id && (ios || basePlanOf(p) == plan['play_base_plan_id']));
        if (match.isNotEmpty) byPlan[plan['plan_code'] as String] = match.first;
      }
      _set(byPlan.isEmpty ? StoreState.unavailable : StoreState.idle);
    } catch (_) {
      _set(StoreState.unavailable);
    }
  }

  Future<void> buy(String planCode) async {
    if (api.plus) return _set(StoreState.manage);
    final product = byPlan[planCode], token = _token;
    if (product == null || token == null) return _set(StoreState.unavailable);
    await MetaEvents.current?.initiateCheckout(planCode, product.rawPrice, product.currencyCode);
    try {
      await backend.buy(product, token);
    } catch (_) {
      _set(StoreState.failed);
    }
  }

  Future<void> restore() async {
    final token = _token;
    if (token == null) return _set(StoreState.unavailable);
    _set(StoreState.verifying);
    await backend.restore(token);
  }

  Future<void> _onPurchases(List<PurchaseDetails> list) async {
    for (final p in list) {
      switch (p.status) {
        case PurchaseStatus.pending:
          _set(StoreState.pending);
        case PurchaseStatus.error:
        case PurchaseStatus.canceled:
          if (p.pendingCompletePurchase) await backend.complete(p);
          _set(p.status == PurchaseStatus.error ? StoreState.failed : StoreState.idle);
        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          _set(StoreState.verifying);
          try {
            final r = await api.verifyPurchase(
              store: _store,
              productId: p.productID,
              token: p.verificationData.serverVerificationData,
            );
            // «sin_acceso» (caducada o reembolsada) también se completa: no hay nada que dar.
            if (p.pendingCompletePurchase) await backend.complete(p);
            await api.updateAccount();
            _set(r['estado'] == 'concedido' ? StoreState.granted : StoreState.idle);
          } on ApiFailure catch (e) {
            // Sin completar: Play/App Store la re-entregan y se vuelve a verificar.
            _set(StoreState.failed, e.message);
          }
      }
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
```

- [ ] **Step 5: Ejecutar y ver que pasa**

Run: `C:\flutter\bin\flutter.bat test test/store_purchases_test.dart`
Expected: 6 PASS.

- [ ] **Step 6: Textos en 6 idiomas**

JSON para `l10n_add.py` (`%TEMP%\vip_l10n.json`, fuera del repo; mismo comando que en Task 11):

```json
{
  "vipSubscribe": {"es": "Suscribirme", "en": "Subscribe", "pt": "Assinar", "fr": "M'abonner", "it": "Abbonati", "de": "Abonnieren"},
  "vipRestore": {"es": "Restaurar compras", "en": "Restore purchases", "pt": "Restaurar compras", "fr": "Restaurer les achats", "it": "Ripristina acquisti", "de": "Käufe wiederherstellen"},
  "vipVerifying": {"es": "Verificando la compra con la tienda…", "en": "Verifying the purchase with the store…", "pt": "Verificando a compra com a loja…", "fr": "Vérification de l'achat auprès de la boutique…", "it": "Verifica dell'acquisto con lo store…", "de": "Kauf wird beim Store überprüft…"},
  "vipPending": {"es": "Pago pendiente. Te daremos acceso en cuanto la tienda lo confirme.", "en": "Payment pending. You will get access as soon as the store confirms it.", "pt": "Pagamento pendente. Você terá acesso assim que a loja confirmar.", "fr": "Paiement en attente. Vous aurez accès dès que la boutique le confirmera.", "it": "Pagamento in sospeso. Avrai accesso appena lo store lo conferma.", "de": "Zahlung ausstehend. Du erhältst Zugang, sobald der Store sie bestätigt."},
  "vipGranted": {"es": "¡Listo! Tu acceso VIP está activo.", "en": "Done! Your VIP access is active.", "pt": "Pronto! Seu acesso VIP está ativo.", "fr": "C'est fait ! Votre accès VIP est actif.", "it": "Fatto! Il tuo accesso VIP è attivo.", "de": "Fertig! Dein VIP-Zugang ist aktiv."},
  "vipStoreFailed": {"es": "No se pudo confirmar la compra. Lo reintentaremos al volver a abrir la app.", "en": "The purchase could not be confirmed. We will retry when you reopen the app.", "pt": "Não foi possível confirmar a compra. Tentaremos de novo quando você reabrir o app.", "fr": "Impossible de confirmer l'achat. Nous réessaierons à la prochaine ouverture de l'app.", "it": "Impossibile confermare l'acquisto. Riproveremo quando riaprirai l'app.", "de": "Der Kauf konnte nicht bestätigt werden. Wir versuchen es beim nächsten Öffnen der App erneut."},
  "vipStoreUnavailable": {"es": "La tienda no está disponible en este dispositivo.", "en": "The store is not available on this device.", "pt": "A loja não está disponível neste dispositivo.", "fr": "La boutique n'est pas disponible sur cet appareil.", "it": "Lo store non è disponibile su questo dispositivo.", "de": "Der Store ist auf diesem Gerät nicht verfügbar."},
  "vipManage": {"es": "Ya tienes Plus. Cambia o cancela tu plan en la tienda.", "en": "You already have Plus. Change or cancel your plan in the store.", "pt": "Você já tem o Plus. Altere ou cancele seu plano na loja.", "fr": "Vous avez déjà Plus. Modifiez ou résiliez votre forfait dans la boutique.", "it": "Hai già Plus. Cambia o annulla il tuo piano nello store.", "de": "Du hast bereits Plus. Ändere oder kündige deinen Plan im Store."},
  "vipStoreTerms": {"es": "Se renueva automáticamente al mismo precio hasta que la canceles en la tienda.", "en": "Renews automatically at the same price until you cancel it in the store.", "pt": "Renova automaticamente pelo mesmo preço até você cancelar na loja.", "fr": "Se renouvelle automatiquement au même prix jusqu'à ce que vous le résiliiez dans la boutique.", "it": "Si rinnova automaticamente allo stesso prezzo finché non lo annulli nello store.", "de": "Verlängert sich automatisch zum gleichen Preis, bis du im Store kündigst."}
}
```

Run: `l10n_add.py` con ese archivo y `flutter gen-l10n`.

- [ ] **Step 7: Pantalla VIP**

En `live_shell.dart`: campo `late final store = StoreController(api)..listen();` en el estado (junto a `api`), `store.dispose()` en `dispose()`, y pasar `store: store` a `LiveVipScreen(...)` (línea ~154).

En `live_vip.dart`:

1. `LiveVipScreen` gana `this.store` (`final StoreController? store;`).
2. En `initState`: `MetaEvents.current?.viewVip(); widget.store?.load(jsonRows(widget.data['plans']).take(3).toList()); widget.store?.addListener(_storeChanged);` y en `dispose` `widget.store?.removeListener(_storeChanged);` con

```dart
  void _storeChanged() {
    if (!mounted) return;
    final l10n = context.l10n, s = widget.store!;
    final text = switch (s.state) {
      StoreState.pending => l10n.vipPending,
      StoreState.granted => l10n.vipGranted,
      StoreState.failed => s.error ?? l10n.vipStoreFailed,
      StoreState.manage => l10n.vipManage,
      _ => null,
    };
    if (text != null) liveNotice(context, text);
    if (s.state == StoreState.manage) {
      launchUrl(manageSubscriptionsUri(ios: s.ios), mode: LaunchMode.externalApplication);
    }
    setState(() {});
  }
```

3. Precio de cada tarjeta: si `widget.store?.byPlan[plan['plan_code']]` existe, mostrar su `price` (precio localizado de la tienda) en lugar de `_price(plan)` y ocultar la línea de moneda/mensual del catálogo interno.
4. Botón dorado. En `build`, tras `final purchases = ...`:

```dart
    final store = widget.store;
    final canBuy = purchases && store != null && store.byPlan.isNotEmpty;
    final verifying = store?.state == StoreState.verifying;
```

   y sustituir `onPressed`, `icon` y `label` del `TextButton.icon` dorado por:

```dart
                      onPressed: verifying
                          ? null
                          : canBuy
                          ? () => store.buy(shown[selected]['plan_code'] as String)
                          : () => liveNotice(
                              context,
                              purchases
                                  ? l10n.vipPaymentRequired
                                  : featureMessage(widget.data, 'compras'),
                            ),
                      icon: verifying
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2, color: liveBg),
                            )
                          : const Icon(Icons.workspace_premium),
                      label: Text(
                        canBuy ? l10n.vipSubscribe : l10n.vipActivate,
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
                      ),
```
5. Bajo el botón, sustituir el `liveText(purchases ? l10n.vipPricesNote : l10n.vipPurchasesPending, ...)` por:

```dart
                Center(
                  child: liveText(
                    canBuy
                        ? l10n.vipStoreTerms
                        : purchases && store?.state == StoreState.unavailable
                        ? l10n.vipStoreUnavailable
                        : purchases
                        ? l10n.vipPricesNote
                        : l10n.vipPurchasesPending,
                    size: 11,
                    color: liveMuted,
                  ),
                ),
                if (canBuy)
                  Center(
                    child: TextButton(
                      onPressed: verifying ? null : store.restore,
                      child: Text(l10n.vipRestore),
                    ),
                  ),
```

(imports: `../core/meta_events.dart`, `store_purchases.dart`, `package:url_launcher/url_launcher.dart`.)

- [ ] **Step 8: Pruebas y análisis**

Run: `C:\flutter\bin\flutter.bat analyze` y `C:\flutter\bin\flutter.bat test`
Expected: sin incidencias; todas PASS (incluida `l10n_test.dart`).

- [ ] **Step 9: Commit**

```bash
git add apps/mobile/lib apps/mobile/test/store_purchases_test.dart
git commit -m "App: suscripción en la pantalla VIP con verificación en el servidor (6 idiomas)"
```

---

## Task 14: Política, términos y versión de consentimiento

**Files:**
- Modify: `docs/legal/PRIVACIDAD_QUANTFUT.md`, `docs/legal/TERMINOS_QUANTFUT.md`, `src/qf/api/legal_pages/*.html` (regeneradas), `src/qf/comercial/firebase.py`, `apps/mobile/lib/product/live_api.dart`, `apps/mobile/lib/product/live_shell.dart`
- Modify: ARB vía `l10n_add.py`
- Test: `tests/test_legal.py` (sin cambios: comprueba `CONSENT_VERSION` en la página), `tests/test_firebase.py` (añadir)

**Interfaces:**
- Produces: `firebase.CONSENT_VERSION = "2026-10-16"`, `firebase.ACCEPTED_CONSENT_VERSIONS = frozenset({"2026-10-12", "2026-10-16"})`; en la app `const consentVersion = '2026-10-16'`.

- [ ] **Step 1: Escribir la prueba que falla**

Añadir a `tests/test_firebase.py`:

```python
def test_version_anterior_de_consentimiento_se_acepta_en_la_transicion():
    from qf.comercial import firebase
    assert firebase.CONSENT_VERSION == "2026-10-16"
    assert {"2026-10-12", "2026-10-16"} <= firebase.ACCEPTED_CONSENT_VERSIONS
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_firebase.py -k transicion -v`
Expected: FAIL.

- [ ] **Step 3: Servidor**

En `src/qf/comercial/firebase.py`:

```python
CONSENT_VERSION = "2026-10-16"
# La app publicada antes del cambio envía 2026-10-12: se acepta mientras se actualiza
# (spec 2026-10-15). Retirar la anterior cuando la versión nueva de la app sea la mínima.
ACCEPTED_CONSENT_VERSIONS = frozenset({"2026-10-12", CONSENT_VERSION})
```

y en `connect_identity` sustituir las dos comprobaciones:

```python
            if terms_version not in ACCEPTED_CONSENT_VERSIONS or privacy_version != terms_version:
                raise CuentaError("consentimiento_requerido", "Acepta los términos y la política de privacidad")
```

```python
        if terms_version in ACCEPTED_CONSENT_VERSIONS and privacy_version == terms_version:
```

- [ ] **Step 4: Texto de la política**

En `docs/legal/PRIVACIDAD_QUANTFUT.md`:

1. Línea 3: `**Versión 2026-10-16 — vigente desde su publicación. Actualizada en octubre de 2026 para informar de la medición de anuncios con Meta, de las compras en Google Play y App Store y de que la medición y el diagnóstico vienen activados.**`
2. Sustituir en la sección 3 las viñetas de «Medición de uso» y «Diagnóstico» y el párrafo final por:

```markdown
- **Medición de uso:** viene activada. Se registran pantallas visibles y eventos
  de uso para conocer qué funciones se utilizan y mejorar la aplicación. Puedes
  desactivarla en Preferencias.
- **Diagnóstico:** viene activado. Se envían informes de fallos y mediciones de
  rendimiento, con información técnica de la aplicación y del dispositivo. Puedes
  desactivarlo en Preferencias.
- **Medición de anuncios (Meta):** viene activada. Para saber qué anuncios de
  QuantFut en Facebook e Instagram atraen usuarios y suscripciones, compartimos con
  Meta Platforms tu correo y un identificador de tu cuenta cifrados (SHA-256), tu
  nombre cifrado si lo tenemos, identificadores del dispositivo (identificador de
  instalación y, si el sistema lo permite, el ID de publicidad), la dirección IP y
  datos técnicos de la aplicación y del dispositivo, y los eventos de uso y de
  compra (registro, suscripción, renovaciones e importe, desbloqueos y pantallas
  de contenido). En iOS solo se usa el ID de publicidad si lo autorizas en el aviso
  de Apple; en Android, si lo limitas o lo borras en los ajustes del teléfono, no
  se usa. Puedes desactivar esta medición en Preferencias: dejamos de compartir
  nuevos datos con Meta desde ese momento. En California, desactivarla equivale a
  ejercer tu derecho a que no compartamos tus datos para publicidad.
```

```markdown
La aceptación de los términos o de este aviso no equivale a aceptar todas
estas finalidades. La medición de uso, el diagnóstico y la medición de anuncios
vienen activados y puedes desactivar cada uno cuando quieras en las preferencias
de la aplicación. Los anuncios solo se muestran si eliges ver un video con
recompensa; Google AdMob puede mostrar anuncios personalizados o no según tu
elección en su formulario de consentimiento (donde se aplica) y los ajustes de
anuncios de tu dispositivo y de tu cuenta de Google.
```

3. En la sección 4 (proveedores), tras el párrafo de Google AdMob:

```markdown
**Meta Platforms** (Meta Platforms Ireland Ltd. y Meta Platforms, Inc.) recibe los
datos descritos en «Medición de anuncios» para medir y optimizar nuestras
campañas en Facebook e Instagram, como proveedor propio bajo sus condiciones y su
política de privacidad. Puede tratarlos fuera de tu país, incluidos los Estados
Unidos.

**Google Play y Apple App Store** gestionan el pago de las suscripciones dentro de
la aplicación como vendedores o procesadores de pago, bajo sus propias condiciones.
Nosotros no recibimos los datos de tu tarjeta: recibimos de la tienda el
identificador del pedido, el producto, las fechas del periodo pagado, el importe,
la moneda y el país de la compra, para darte acceso y atender reembolsos.
```

4. Quitar la frase que dice que el proveedor de pagos «se identificará» (línea ~56) y sustituir la afirmación de la sección 6 «QuantFut no vende datos personales» por: `QuantFut no vende datos personales a cambio de dinero. Compartir datos con Meta para medir anuncios puede considerarse «compartir» según la ley de California; puedes oponerte desactivando la medición de anuncios en Preferencias.`

- [ ] **Step 5: Texto de los términos**

En `docs/legal/TERMINOS_QUANTFUT.md`, actualizar la versión a `2026-10-16` y añadir a la sección de planes:

```markdown
Las suscripciones de la aplicación se compran en Google Play o en App Store y se
renuevan automáticamente al mismo precio y por el mismo periodo hasta que las
canceles en la tienda; la cancelación se aplica al final del periodo pagado y
mantienes el acceso hasta entonces. Los reembolsos los gestiona la tienda según
sus reglas; si la tienda reembolsa o anula un pago, retiramos el acceso de ese
periodo.
```

- [ ] **Step 6: Regenerar páginas y probar**

Run: `npm install --prefix "$TEMP/marked13" marked@13`, después `NODE_PATH="$TEMP/marked13/node_modules" node scripts/build_legal_pages.cjs` y `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_legal.py tests/test_firebase.py -v`
Expected: PASS (las páginas contienen `2026-10-16`).

- [ ] **Step 7: App — versión nueva y aviso de cambios**

En `live_api.dart`: `const consentVersion = '2026-10-16';` (nivel superior) y en `connectFirebase` usar `consentVersion` en lugar de los dos literales `'2026-10-12'`.

Textos (JSON para `l10n_add.py`):

```json
{
  "privacyUpdateTitle": {"es": "Actualizamos la privacidad", "en": "We updated our privacy notice", "pt": "Atualizamos a privacidade", "fr": "Nous avons mis à jour la confidentialité", "it": "Abbiamo aggiornato la privacy", "de": "Wir haben den Datenschutz aktualisiert"},
  "privacyUpdateBody": {"es": "Ahora puedes suscribirte con Google Play o App Store, y la medición de uso, el diagnóstico y la medición de anuncios con Meta vienen activados. Puedes desactivarlos en Preferencias.", "en": "You can now subscribe with Google Play or the App Store, and usage measurement, diagnostics and Meta ad measurement are turned on. You can turn them off in Preferences.", "pt": "Agora você pode assinar pelo Google Play ou pela App Store, e a medição de uso, o diagnóstico e a medição de anúncios da Meta vêm ativados. Você pode desativá-los em Preferências.", "fr": "Vous pouvez désormais vous abonner via Google Play ou l'App Store, et la mesure d'utilisation, le diagnostic et la mesure publicitaire Meta sont activés. Vous pouvez les désactiver dans Préférences.", "it": "Ora puoi abbonarti con Google Play o App Store, e la misurazione dell'uso, la diagnostica e la misurazione degli annunci di Meta sono attive. Puoi disattivarle in Preferenze.", "de": "Du kannst jetzt über Google Play oder den App Store abonnieren, und Nutzungsmessung, Diagnose und Meta-Anzeigenmessung sind aktiviert. Du kannst sie in den Einstellungen deaktivieren."},
  "privacyUpdateRead": {"es": "Leer la política", "en": "Read the policy", "pt": "Ler a política", "fr": "Lire la politique", "it": "Leggi l'informativa", "de": "Richtlinie lesen"},
  "privacyUpdateOk": {"es": "Entendido", "en": "Got it", "pt": "Entendi", "fr": "Compris", "it": "Ho capito", "de": "Verstanden"}
}
```

En `live_shell.dart`, dentro del `addPostFrameCallback` de Task 12, antes de `apply`:

```dart
      final prefs = services?.preferences;
      if (prefs != null && api.signedIn &&
          await prefs.getString('consent_notice') != consentVersion && mounted) {
        await showDialog<void>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: Text(dialogContext.l10n.privacyUpdateTitle),
            content: Text(dialogContext.l10n.privacyUpdateBody),
            actions: [
              TextButton(
                onPressed: () => launchUrl(
                  Uri.parse('https://pronosticosdeportivos.pro/legal/privacidad'),
                  mode: LaunchMode.externalApplication,
                ),
                child: Text(dialogContext.l10n.privacyUpdateRead),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: Text(dialogContext.l10n.privacyUpdateOk),
              ),
            ],
          ),
        );
        await prefs.setString('consent_notice', consentVersion);
      }
```

- [ ] **Step 8: Pruebas**

Run: `C:\flutter\bin\flutter.bat analyze`, `C:\flutter\bin\flutter.bat test` y `./scripts/harness_check.sh`
Expected: todo PASS.

- [ ] **Step 9: Commit**

```bash
git add docs/legal src/qf/api/legal_pages src/qf/comercial/firebase.py tests/test_firebase.py apps/mobile/lib
git commit -m "Privacidad y términos 2026-10-16: Meta, compras en tiendas y seguimiento activo por defecto"
```

---

## Task 15: Guía del titular para las consolas

**Files:**
- Create: `apps/mobile/docs/META_COMPRAS_TITULAR.md`

- [ ] **Step 1: Escribir la guía**

Contenido (sin valores inventados; cada paso dice dónde se pega cada dato):

```markdown
# Meta y compras: lo que hace el titular en las consolas

## Meta (developers.facebook.com y Events Manager)
1. Crear la app de Meta (tipo «Empresa») y añadir la plataforma Android: paquete
   `com.saptain.quantfut`, clase `com.saptain.quantfut.MainActivity`, hashes de la clave de
   firma (debug y la de Play App Signing; ver `FIRMA_ANDROID.md`).
2. Copiar App ID y Client Token a `apps/mobile/android/meta.properties` (plantilla
   `meta.properties.example`) y a `ios/Flutter/Meta.xcconfig`. Compilar con
   `--dart-define=QF_META_ENABLED=true`.
3. Configuración básica → tarjeta Android (y luego iOS): **desactivar el registro automático de
   compras en la aplicación**. Las compras las manda el servidor.
4. Events Manager: crear o elegir un dataset y **vincular la app** (Configuración → Fuentes de datos).
5. Business Manager → Usuarios del sistema: crear uno, darle el dataset y generar un token con
   permiso `ads_management`. Ponerlo SOLO en el `.env` del servidor como `META_CAPI_TOKEN`, con
   `META_DATASET_ID`. No pegarlo en el chat.
6. Probar: Events Manager → Probar eventos → copiar el código a `META_TEST_EVENT_CODE`, activar
   `META_CAPI_ENABLED=1` en un ensayo y comprobar `CompleteRegistration`, `Purchase`, `Subscribe` y
   `SpentCredits`, y la calidad de coincidencia de cada uno. Vaciar el código después.
7. Revisar si los anuncios necesitan autorización de Meta por estar relacionados con apuestas.

## Google Play Console
1. Subir un AAB a **Pruebas internas** y añadir tu cuenta como tester y como **tester de licencias**
   (Configuración → Pruebas de licencias): así las compras no se cobran.
2. Monetizar → Suscripciones: crear `quantfut_plus` con planes base `plus-1m` (mensual), `plus-3m`
   (cada 3 meses) y `plus-6m` (cada 6 meses), renovación automática, sin prueba gratis, con precios.
3. Google Cloud (mismo proyecto que Play): crear una cuenta de servicio, descargar su JSON y en
   Play Console → Usuarios y permisos invitarla con «Ver datos financieros» y «Gestionar pedidos y
   suscripciones». El JSON va al servidor (`PLAY_SERVICE_ACCOUNT_FILE`), nunca al repo.
4. Pub/Sub: crear el tema, dar permiso de publicación a `google-play-developer-notifications@system.gserviceaccount.com`,
   crear una suscripción push a `https://pronosticosdeportivos.pro/app/v1/compras/google/rtdn` con
   autenticación (cuenta de servicio = `PLAY_RTDN_SERVICE_ACCOUNT`, audiencia = `PLAY_RTDN_AUDIENCE`),
   y en Play Console → Monetización → configurar el tema en «Notificaciones en tiempo real».
5. Contenido de la app → Seguridad de los datos: declarar correo, nombre, ID de usuario, ID de
   dispositivo/publicidad, historial de compras, interacciones en la app, diagnósticos; compartidos con
   Meta para publicidad/analítica; cifrados en tránsito; borrables a petición. Declaración del ID de
   publicidad: sí, para analítica y publicidad.

## Apple (cuando exista la cuenta)
1. App Store Connect → grupo de suscripción «QuantFut Plus» con `quantfut_plus_1m`, `_3m`, `_6m`.
2. Claves → Compras dentro de la app: generar la `.p8`, anotar Key ID e Issuer ID.
3. App Store Server Notifications V2 → URL `https://pronosticosdeportivos.pro/app/v1/compras/apple/notificaciones`.
4. Descargar `AppleRootCA-G3.cer` de apple.com/certificateauthority a `APPLE_ROOT_CERTS_DIR`.
5. En Xcode (Mac): registrar las carpetas `*.lproj/InfoPlist.strings`, compilar y probar ATT.
6. Etiquetas de privacidad equivalentes a la sección de Play.
```

- [ ] **Step 2: Commit**

```bash
git add apps/mobile/docs/META_COMPRAS_TITULAR.md
git commit -m "Guía del titular: Meta, Play Console y Apple para compras y medición"
```

---

## Task 16: Verificación final y registro

**Files:**
- Modify: `harness/tareas.md`, `harness/progreso.md`, `PENDIENTES.md`

- [ ] **Step 1: Arnés y pruebas con BD**

Run: `./scripts/harness_check.sh` y `PYTHONPATH=src QF_TEST_PG_DSN=... .venv/Scripts/python.exe -m pytest tests/test_compras_pg.py tests/test_meta_capi_pg.py tests/test_cuentas_pg.py -v`
Expected: `OK. El repo está en buen estado.` y todas PASS.

- [ ] **Step 2: App**

Run (desde `apps/mobile`): `C:\flutter\bin\flutter.bat analyze`, `C:\flutter\bin\flutter.bat test`, `C:\flutter\bin\flutter.bat build apk --release`
Expected: sin incidencias, todas PASS, APK firmado generado.

- [ ] **Step 3: Prueba en emulador (sin Meta configurado)**

Instalar el APK de depuración en `emulator-5556`, abrir Perfil → Preferencias y comprobar que aparece «Medición de anuncios (Meta)» activado; abrir VIP y comprobar que, sin productos de Play, se ve «La tienda no está disponible en este dispositivo» y no se rompe nada. Captura de pantalla como evidencia.

- [ ] **Step 4: Registro**

- `harness/tareas.md`: marcar las casillas de la sección «Meta (App Events + CAPI) y suscripciones en la app» hechas en el repo; dejar abiertas las del titular y las pruebas reales.
- `harness/progreso.md`: entrada con la decisión clave de implementación (p. ej. por qué el periodo de cada cobro sale de la tienda y no de `duration_days`; por qué las compras de prueba no van a Meta).
- `PENDIENTES.md`: en «Para poder vender picks», actualizar la fila de Meta y compras: código hecho en la rama `feat/meta-compras`, pendiente de credenciales, pruebas reales (Probar eventos, sandbox de Play) y despliegue tras el 1-nov; añadir «Registrar `*.lproj/InfoPlist.strings` en Xcode (Mac)».

- [ ] **Step 5: Commit**

```bash
git add harness/tareas.md harness/progreso.md PENDIENTES.md
git commit -m "Meta y compras: registro de estado y pendientes"
```

- [ ] **Step 6: Entregar**

No fusionar ni desplegar. Informar al titular de la rama, de lo verificado y de lo que falta (credenciales, pruebas reales, despliegue coordinado tras el 1-nov según `DEPLOYS.md`).
