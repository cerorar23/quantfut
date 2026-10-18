# Plan de despliegue — Acceso con Google en la web (2026-10-18)

Estado: **preparado, NO ejecutado**. Sigue `DEPLOYS.md`.

## Qué cambia
| Archivo | Cambio |
|---|---|
| `src/qf/api/firebase.py` | `GET /app/v1/firebase/web-config` y `POST /app/v1/firebase/web-session` |
| `frontend/google-auth.js` | nuevo: SDK web de Firebase, solo devuelve el ID token |
| `frontend/cuenta-api.js`, `membership.js`, `membership.css` | botón «Continuar con Google» + casilla de términos |
| `frontend/app.js`, `index.html` | solo las versiones `?v=` de los módulos |
| `src/qf/api/web.py`, `frontend/server.mjs` | sirven `/google-auth.js` |
| `tests/test_firebase.py`, `tests/test_web_console.py` | pruebas nuevas |

Sin migración de base de datos: usa `firebase_identities`, `account_consents` y `firebase_preferences` (db/043+).

## Estado frente a `main` (comparado el 2026-10-18, solo lectura)
La API corre `quantfut-api-cybercore:2d8cfef`. Sus `frontend/app.js`, `index.html` y `server.mjs` coinciden con el frontend Cybercore que ya está en `main`
(PR #14) más mis pocas líneas, y `membership.js`, `membership.css`, `cuenta-api.js` y `firebase.py` del servidor son idénticos a `main`. Por tanto:
1. El parche es limpio: imagen derivada de la que corre (`FROM quantfut-api-cybercore:2d8cfef`) + solo los archivos de la tabla.
2. Antes de sobrescribir, repetir `scripts/deploy.sh estado` y comparar cada archivo de la tabla con lo desplegado (otra sesión pudo desplegar entre tanto).
3. La migración es `db/083_whop_checkout.sql` (mi `073` original chocaba con la `073`/`074` que `main` ya trae).

## Variables en el `.env` del servidor (a añadir; la apiKey web no es secreto)
```
FIREBASE_WEB_API_KEY=AIzaSyDjlWPWxpQ4s2DKULi8uNMBo39pMDG2VnA
FIREBASE_WEB_APP_ID=1:68225142184:web:91fdbdc42fd7d07fe0619d
FIREBASE_WEB_AUTH_DOMAIN=pronosticos-deportivos-85ffa.firebaseapp.com
```
Ya existen en el servidor: `ACCOUNTS_ENABLED=1`, `FIREBASE_AUTH_ENABLED=1`, `FIREBASE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS` (montada).
En Firebase ya está: app Web «QuantFut Web» y `pronosticosdeportivos.pro` en dominios autorizados.

## Pasos
1. Rama + PR con estos archivos (y el trabajo Cybercore pendiente). Arnés en verde: `./scripts/harness_check.sh` (1310 pruebas pasaron en local).
2. `scripts/deploy.sh estado`; confirmar que la API sigue en `2d8cfef` y nadie más despliega.
3. Respaldo en el servidor: `~/quantfut/releases/google-web-<commit>/` con `docker-compose.yml`, `.env` (sin imprimir) y los 8 archivos actuales del contenedor.
4. Imagen `quantfut-api-google-web:<commit>` = `FROM quantfut-api-cybercore:2d8cfef` + `COPY` solo de los archivos de la tabla.
5. Añadir las 3 variables al `.env`; override de compose y `docker compose up -d --no-deps --no-build api` (worker y base sin tocar).
6. Verificar en `https://pronosticosdeportivos.pro`: `/health` 200, `GET /app/v1/firebase/web-config` 200 con `projectId`, `/google-auth.js` 200, `/app/v1/firebase/web-session` sin cuerpo → 422, logs sin errores. Probar el botón con una cuenta real.
7. Anotar la entrada en `DEPLOYS.md`.

## Vuelta atrás
Restaurar `docker-compose.yml` del respaldo y `docker compose up -d --no-deps --no-build api`; quitar las 3 variables (inofensivas si quedan: sin código que las lea, el endpoint no existe).

## Probado en local (2026-10-18)
Popup real de Google en `localhost` → token verificado por el servidor → 409 `consentimiento_requerido` (cuenta nueva sin casilla). Local usa Redis falso y credencial
anónima de Firebase Admin solo en el lanzador de pruebas; la comprobación de revocación (`check_revoked`) solo se ejercita en producción, donde existe la credencial de servicio.
Con los términos marcados: `web-session` 200, `/me` 200 y la pantalla «Mi cuenta» abierta (esquema aislado, ya borrado).

## Añadido el mismo día: cobro con Whop (mismo despliegue de API)
Archivos extra: `db/083_whop_checkout.sql` (aditiva; aplicar antes de arrancar la imagen), `src/qf/comercial/whop.py`, `src/qf/comercial/meta_capi.py`,
`src/qf/api/whop.py`, `src/qf/api/main.py`, `frontend/meta-pixel.js`, `frontend/whop-checkout.js` (+ rutas en `web.py`). Respaldar la tabla `plans` antes de la migración.
Variables nuevas (todas apagan la función si faltan): `WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`, `META_PIXEL_ID` (+ opcionales `WHOP_ACCOUNT_ID`, `WHOP_API_VERSION_DATE`).
Ya hecho en Whop el 2026-10-18 (ver DEPLOYS.md). Pasos originales: crear el plan (`plan_…`) y asignarlo: `UPDATE plans SET whop_plan_id='plan_…' WHERE plan_code='plus_3m';`;
crear el webhook `https://pronosticosdeportivos.pro/webhooks/whop` con `payment.succeeded` y `membership.updated`; copiar su `ws_…` a `WHOP_WEBHOOK_SECRET`.
Caddy: `/webhooks/whop` debe llegar a la API sin autenticación adicional. No activar `META_CAPI_ENABLED` hasta alinear el worker (ver DEPLOYS 2026-10-15).

## Pendiente del despliegue: IDs de plan de Whop (estado 2026-10-18)
Los 3 planes ya existen en Whop (renovables) y la clave y el secreto del webhook ya están en el `.env` del VPS. Tras aplicar `db/083`, ejecutar UNA vez:
```sql
UPDATE plans SET whop_plan_id = 'plan_S7DHROtI0PCn7' WHERE plan_code = 'plus_1m';  -- 14,99 USD / mes
UPDATE plans SET whop_plan_id = 'plan_vyCbaYTqBC7FC' WHERE plan_code = 'plus_3m';  -- 33,99 USD / 3 meses
UPDATE plans SET whop_plan_id = 'plan_e7WYnSudIFhqP' WHERE plan_code = 'plus_6m';  -- 53,99 USD / 6 meses
```
Importes de Whop = importes de `plans` (14,99 / 33,99 / 53,99). `META_PIXEL_ID=2253839992227148` ya está en el `.env` del VPS (añadido el 2026-10-18).
Eventos del webhook ya suscritos: `payment.succeeded`, `membership.updated`, `membership.deactivated`. Reembolsos: `refund.created`/`refund.updated` NO están suscritos
porque no se conoce su payload; añadirlos y manejarlos tras ver una entrega real (hoy un reembolso no revoca el acceso por sí solo).
