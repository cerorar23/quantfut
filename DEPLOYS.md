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
