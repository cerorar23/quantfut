# Registro de despliegues — QuantFut

Una sola regla de fondo: **lo que corre en producción es lo que dice `main`**. Todo cambio en el servidor se
anota aquí en el mismo momento, y solo despliega una sesión a la vez.

## Repositorio
Privado en GitHub: `cerorar23/quantfut` (rama `main`). Cada push ejecuta el arnés en GitHub Actions
(`.github/workflows/pruebas.yml`, con Postgres 16 real). **GitHub no permite proteger ramas en repos privados del
plan gratuito**, así que la regla es por costumbre: rama + pull request + arnés verde antes de fusionar a `main`.
El servidor todavía NO despliega desde aquí (pendiente: clave de despliegue de solo lectura y `git pull` de una etiqueta).

## Estado medido el 2026-10-15 (antes de ordenar; el worker ya quedó en 0 diferencias, ver el registro)
Comparando cada `.py` de `src/` contra `main`:

| Lugar | Archivos | Distintos a `main` | Faltan de `main` |
|---|---|---|---|
| `main` | 130 | — | — |
| Carpeta `~/quantfut/src` del servidor | 90 | 29 | 40 |
| Contenedor worker (cron y reentrenamiento) | 107 | 12 | 23 |
| Contenedor API | 113 | 24 | 17 |

La carpeta `~/quantfut/src` y la API llevan versiones antiguas de `train.py` y `clv.py`. **No reconstruir ninguna
imagen desde esa carpeta sin sincronizarla** con `main`: revertiría código.

## Procedimiento (objetivo)
0. `scripts/deploy.sh estado` antes de empezar: dice qué corre realmente frente a `main`.
1. Árbol limpio, cambio en `main`, arnés en verde (GitHub Actions o `./scripts/harness_check.sh`).
2. Comparar lo desplegado con el commit base anterior: si hay diferencias que no son tuyas, parar y averiguar.
3. Respaldar lo que se va a cambiar (archivos y, si toca la base, la tabla).
4. Construir y desplegar **solo el servicio necesario**; no tocar el worker el día del reentrenamiento.
5. Verificar hashes, salud (API 200) y modelo activo.
6. Anotar la entrada de abajo con la vuelta atrás.

## Registro (lo más reciente arriba)

### 2026-10-18 19:10 UTC · Comprometer-revelar de la cadena · worker (un archivo), rama `codex/force-update-deployment` (`a1e725d`, PR #11)
- Cambio: `publish/hashchain.py` (al repo público sube solo el compromiso; el JSON se revela al terminar los partidos). **Desplegado antes de fusionar a `main`** por orden del titular; al fusionar el PR, `main` queda igual que el worker.
- Método: `docker cp` de ese único archivo al contenedor worker (como F2c): **parche del contenedor, no de la imagen**; se pierde si el worker se recrea, así que la alineación del 1-nov debe construirse desde un `main` que ya lo incluya.
- Antes de copiar, el `hashchain.py` del worker era idéntico a la base (`912aa8c21708`). Hash final `252693f570e9`, igual al commit.
- Ensayo en el worker: `hashchain verify` OK en 20 lotes (0 sin revelar), importa sin error. `CHAIN_GIT_REMOTE` sigue vacío: `seal()` no ejecuta ninguna rama de git, así que el sellado de las 08:00 UTC se comporta igual. Sin reinicios; modelo, API y base intactos.
- Falta: configurar `CHAIN_GIT_REMOTE` (decisión del titular) y probar `revelables` contra el repo real cuando exista.
- Vuelta atrás: `docker cp ~/quantfut/deployments/hashchain-revelado-20261018/antes/hashchain.py <worker>:/app/src/qf/publish/hashchain.py`.
- Observado de paso: el servidor se reinició a las 19:00 UTC (contenedores con 3 min de actividad al llegar) y la API corre `quantfut-api-cybercore:2d8cfef`, que no figura en este registro (otra sesión): anotarlo quien la desplegó.

### 2026-10-18 02:20 UTC · Rediseño CYBERCORE de la web · API
- PR #12 (`a30c799`) y hotfix de rutas FastAPI PR #13 (`2d8cfef`), con los dos arneses de cada PR aprobados.
- Imagen `quantfut-api-cybercore:2d8cfef` (`8d81ce9c10c6`), derivada de la imagen que ya corría
  `quantfut-api-force-update:b8f74ae`. Solo reemplaza `frontend/` y `src/qf/api/web.py`; no reconstruye
  desde la carpeta desactualizada del servidor ni modifica el resto del código de la API.
- Respaldo previo de frontend, `web.py`, imagen y compose en
  `~/quantfut/releases/cybercore-2d8cfef/backup/`. Worker, base de datos, Caddy y Grafana intactos.
- Ensayo aislado y dominio real: `/`, `/health`, `/future.css`,
  `/vendor/cybercore/cybercore.min.css` y `/app.js` responden 200; contenido y cinco hashes iguales a
  `main`. Comprobación visual correcta y consola del navegador sin errores. Modelo activo
  `2026.09.27-010508`; publicación pausada por la puerta comercial; 19 lotes de la cadena verificados.
- Vuelta atrás: restaurar `backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` y
  ejecutar `docker compose up -d --no-deps --no-build --force-recreate api`. La imagen anterior es
  `quantfut-api-force-update:b8f74ae` (`9188e2950838`).

### 2026-10-16 · Force Update desde el panel · API + `db/072`
- PR #10 integrado (`b8f74ae`), arnés del PR y de `main` en verde.
- Imagen `quantfut-api-force-update:b8f74ae`, derivada de `quantfut-api-admob:20261015b` con solo los tres archivos de Force Update. Base previa comprobada y hashes finales verificados.
- Migración aditiva aplicada en transacción; respaldo de esquema y compose en `~/quantfut/releases/force-update-b8f74ae/`.
- Ensayo: 108 rutas, renderizado de panel y configuración correctos. Dominio real: salud 200 y siete campos nuevos en `/mobile/v1/config`; logs sin errores. Modelo `2026.09.27-010508`; mismo contenedor del worker.
- Estado inicial: obligación desactivada, mínimos 0 y versiones/enlaces vacíos. Requiere nueva compilación móvil para que los dispositivos apliquen la política.
- Reversión: restaurar `docker-compose.before.yml` del respaldo y ejecutar `docker compose up -d --no-deps --no-build api`. La tabla añadida puede permanecer.
- Detalle y estado móvil: `docs/despliegue_force_update_20261016.md`.

### 2026-10-15 23:30 UTC · Compras de tienda y Meta (CAPI) · API + `db/071` (rama `feat/meta-compras`, commits `4db6616`, `ca818ce`)
- Orden del titular: desplegar el mismo día (antes se había dejado la API para después del 1-nov). El worker NO se tocó
  (mismo contenedor `28330d835ca9`), así que no interfiere con el reentrenamiento.
- **Base de datos:** `db/071` aplicada en una transacción. Solo añade: columnas de tienda en `plans`, `accounts.store_account_token`,
  `firebase_preferences.ads_measurement` y tablas `store_transactions` (inmutable), `meta_events`, `meta_identities`.
  Respaldo previo: `~/backups/pre_meta_071_20261015.sql.gz` (accounts, plans, firebase_preferences).
- **API:** imagen `quantfut-api-admob:20261015b` = la `20261015a` + SOLO 20 archivos de la rama + `app-store-server-library==3.1.2`.
  Antes de sobrescribir se comprobó que los 12 archivos existentes que se cambian eran idénticos a `main` en el contenedor
  (los otros 8 son nuevos), por lo que las demás diferencias de la API frente a `main` no se tocaron.
  Ensayo en contenedor aparte: 104 rutas = 100 + 4 nuevas. Compose del servidor fijado en `20261015b`
  (copia previa: `~/backups/docker-compose.pre-meta-20261015.yml`).
- **Verificado en el dominio real:** `/health` 200; `/app/v1/plans` con los IDs de tienda; las 3 páginas `/legal/*` muestran
  2026-10-16; `compras/verificar` y `google/rtdn` responden 503 `compras_deshabilitadas`; `meta/dispositivo` sin sesión 401;
  callbacks de recompensas idénticos a la imagen anterior; sin errores en los logs.
- **Apagado:** `STORE_PURCHASES_ENABLED` y `META_CAPI_ENABLED` no están en el `.env` (valen 0). Faltan credenciales del titular.
- **Pendiente en el worker:** la tarea `qf.comercial.meta_capi` del cron y la limpieza de `meta_*` en `firebase_mantenimiento`
  llegan con la próxima alineación del worker (después del 1-nov). Hacerla ANTES de activar `META_CAPI_ENABLED`.
- **Vuelta atrás:** `sed -i 's#20261015b#20261015a#' ~/quantfut/docker-compose.yml && docker compose up -d --no-deps --no-build api`.
  La migración es aditiva: no hace falta deshacerla (las columnas y tablas nuevas no las usa el código anterior).
- **Legal:** las páginas públicas ya describen Meta, las compras en tiendas y la medición activada por defecto (versión 2026-10-16);
  el servidor acepta también la 2026-10-12 de la app publicada. Falta la revisión del profesional habilitado.
### 2026-10-15 16:49 UTC · LanusStats/365Scores · tres parejas xG — base de datos
- Carga explícitamente solicitada: Granada–Albacete 1,58/1,43; Almería–Deportivo 1,89/0,84;
  Zaragoza–Málaga 1,41/0,32. Solo cuatro campos xG de tres partidos vacíos, sin tocar fechas/resultados.
- Tres detalles originales y tres respuestas de estadísticas conservados en el archivo existente,
  con hashes y recepción real del 15-oct-2026. Ensayo revertido y repetición sin escrituras.
- Respaldo selectivo: volumen del worker, `/srv/quantfut/artifacts/imports/lanusstats-xg-20261015/carga/tres_partidos_antes.json.gz`.
  Vuelta atrás: restaurar solo los cuatro campos xG de esos tres registros, comprobando que conservan
  exactamente esta fuente/recepción/valores; conservar el archivo de procedencia. No se deshabilitan triggers.
- Lectura tras commit: 3/3 parejas, 6/6 hashes y API 200; 1.219 huecos restantes. Modelo/flags/sellos
  y demás partidos conservados. Sin despliegue de aplicación, reinicios ni entrenamiento.
- Detalle: `docs/lanusstats_carga_20261015.md`; importador auditado bajo el volumen de archivos,
  sin modificaciones del código en ejecución.

### 2026-10-15 15:52 UTC · Worker alineado con `main` (`495053a`) — recreado
- Imagen `quantfut-worker:candidato-495053a` (`896c5009c1ac`), construida desde `main` con el `requirements.txt` corregido
  (incluye `cryptography` y `firebase-admin`). `latest` = esa imagen. El worker pasó de 12 archivos distintos a **0**.
- **Ensayo previo** (worker actual frente a candidata, solo lectura, `scripts/ensayo_worker.py`): 0 módulos con error, 21/21
  entradas del cron importables, `hashchain verify` OK en 17 lotes y conjunto de entrenamiento idéntico (49.509 filas,
  46.226 con cierre, misma huella).
- Se recreó **solo el worker** justo cuando no había trabajos en curso. El ciclo de cron de las 16:00 corrió limpio
  (cuotas, bajas, alineaciones, marcador, sombra) y no hay errores posteriores al cambio.
- **Vuelta atrás:** `docker tag quantfut-worker:en-ejecucion-20261015 quantfut-worker:latest &&
  docker compose up -d --no-deps --force-recreate worker` (el estado exacto de antes, con el parche F2c).
- Receta usada: `git archive HEAD Dockerfile requirements.txt src frontend` → carpeta `~/quantfut/releases/worker-<commit>` →
  `docker build -t quantfut-worker:candidato-<commit>` → ensayo → `docker tag ... latest` → `docker compose up -d --no-deps
  --force-recreate worker`.
- **Nota sobre lotes sellados:** regenerar desde la base 8 de los 17 lotes ya no reproduce el contenido sellado (también pasaba
  antes del cambio). Causa: 93 ítems de Chile y Brasil B eliminados el 13-oct (autorizado) y 4 predicciones de partidos
  reprogramados. Los archivos sellados siguen intactos y la verificación de la cadena da OK; lo que cambia es que ya no se
  puede reconstruir desde la base. No es un fallo de esta alineación.

### 2026-10-15 · Orden de imágenes del worker — sin reiniciar nada
- `quantfut-worker:latest` (la imagen que se usaría al recrear el contenedor) era **más antigua** que el worker en
  ejecución: 16 archivos distintos, entre ellos `publish/daily.py` y `publish/hashchain.py` (sellado de la cadena).
  Recrear el worker habría retrocedido ese código y roto la verificación de lotes recientes.
- Se fijó el estado en ejecución: `scripts/deploy.sh congelar worker`. Etiquetas: `latest` = `en-ejecucion-20261015`
  (`11cd07f588be`, con el parche F2c); la anterior queda como `latest-previo-20261015` (`2cac1af32eed`).
  El contenedor no se tocó (en ejecución desde 2026-10-14).
- Vuelta atrás de esta operación: `docker tag quantfut-worker:latest-previo-20261015 quantfut-worker:latest`.
- Diferencia worker vs `main` que queda: 12 archivos. Los relevantes son pequeños y de bajo riesgo (`config.py`: un ajuste
  nuevo `APP_DOWNLOAD_URL`; `eval/alta_prob_calibracion.py`: ampliación aditiva de un script de evaluación sin cron;
  `ingest/history_fd.py` y `model/lineup_challenger.py`: trabajo de F1/F2, probado). El resto es código de la API.

### 2026-10-16 · Credenciales de Google Play y RTDN — API
- Estado final autorizado: `STORE_PURCHASES_ENABLED=1`, misma imagen, solo API recreada. Respaldo previo: `deployments/play-credentials-20261016/docker-compose.before-enable.yml`. RTDN validado con 204; consulta real de QuantFut Plus por Publisher API con 200 y tres planes ACTIVE. Compra interna `sandbox` y acceso VIP comprobados. Meta no activado por esta sesión.
- Conservada imagen `quantfut-api-admob:20261015b`; recreada solo API sin build. Worker intacto.
- JSON privado con modo 600 en `/home/qf/.config/quantfut/google-play.json`, montado solo lectura en `/run/secrets/quantfut-play.json`.
- Configuradas variables PLAY de cuenta, paquete y OIDC; instalación inicial con compras apagadas y posterior activación comprobada.
- Respaldo de compose previo: `deployments/play-credentials-20261016/docker-compose.before.yml` en servidor.
- Producción 1.0.0 y ficha enviadas a revisión de Google; todavía no se confirma disponibilidad pública.

### Trampas conocidas (no repetirlas)
- **`requirements.txt` del servidor no tiene `cryptography` ni `firebase-admin`** (el de `main` sí). El worker en ejecución
  los tiene instalados a mano. Reconstruir una imagen desde `~/quantfut` tal cual **perdería `cryptography`**, que descifra
  la clave de PitchAPI guardada en la base.
- **`docker-compose.yml` de `main` fija una imagen antigua de la API** (`quantfut-api-tapjoy:20261012-msg`); el servidor usa
  `quantfut-api-admob:20261015a`. Desplegar con el compose del repo retrocedería la API.
- La API (`api`) y la carpeta `~/quantfut/src` llevan código antiguo (ver tabla de arriba); la API no se ha alineado.

### 2026-10-15 · F2c · filtro del cierre reconstruido — worker
- Commit `976b448`. `docker cp` de `eval/cierre.py`, `eval/clv.py`, `model/train.py`, `model/shadow.py`,
  `publish/shadow_sharp.py` al contenedor worker. Hashes verificados contra `main`.
- Respaldo de lo anterior: servidor `~/quantfut/deployments/f2c-filtro-cierre/antes`.
- **Es un parche del contenedor, no de la imagen**: se pierde si el worker se recrea. Comprobar antes del 1-nov.
- La API no se tocó (sus `train.py` y `clv.py` son antiguos).
- Vuelta atrás: `docker cp` de `antes/` al worker.

### 2026-10-15 · F2b · cierres de Pinnacle de The Odds API — base de datos
- 3.492 filas en `odds_snapshots` (`source='the_odds_api_hist'`); 8.000 créditos; saldo 7.367.
- Respaldo: `~/backups/odds_snapshots_pre_f2b_20261015.sql.gz`. Detalle: `docs/f2_cierres_pinnacle_20261015.md`.

### 2026-10-15 · OddsPapi · cierres reconstruidos — base de datos (otra sesión)
- 2.918 cierres, migración `db/070`. Ver `docs/oddspapi_carga_20261015.md`.

### 2026-10-14 · F0 · archivo FotMob a `matches` y `estadios` — base de datos
- Migración `db/067` y relleno de columnas vacías. Respaldo: `~/backups/matches_pre_f0_20261014.sql.gz`.
  Detalle y reversión: `docs/f0_archivo_a_matches_20261014.md`.

### Antes del 2026-10-14
Ver `harness/progreso.md` (despliegues de la API con imágenes `quantfut-api-admob:*`, AdMob, invitaciones, etc.).
