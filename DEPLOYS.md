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

### 2026-10-24 14:18 UTC · PropLine: box score, lesiones NBA y lectores (PR #97) · release `~/propline-shared/releases/5a9cde0` (`main` `5a9cde0`)
- Estado previo comprobado: `current` → `releases/6d459be`, cuyos tres archivos coinciden byte a byte con `main` `6d459be` (sha256 `47a7e3cd…`, `8a367cab…`, `3f4f4745…`).
- Release nueva desde `git archive 5a9cde0` con `core.autocrlf=false`: `propline_shared.py` `b162d8ea…`, `propline_shared_config.json` `c3694385…`, `propline_shared_runner.py` `3f4f4745…` (sin cambios) y `runtime.json` copiado de `6d459be` (misma imagen fijada por digest, mismo usuario, red, volumen y archivo de clave). Sin imagen nueva: el módulo solo usa la biblioteca estándar.
- Ensayo antes de activar, dentro de la imagen fijada, `--network none` y el volumen en solo lectura: el módulo carga, la configuración nueva se lee (reserva NBA 130 / fútbol 300 / tenis 300, `stats_prefixes` NBA y fútbol, lesiones NBA) y los lectores devuelven el archivo real (71 eventos NBA, 161 partidos de tenis).
- Activación: `ln -sfn releases/5a9cde0 current.tmp && mv -T current.tmp current` a las 14:18 UTC, entre pasadas. Cron sin cambios (`7 * * * *` con `flock`).
- **Sin verificar con una pasada real:** desde las 14:11:49 UTC PropLine responde `401 invalid_api_key` (ver la entrada siguiente). Pendiente: con la clave arreglada, comprobar en el informe `stop: null`, `settlement` con `stats`, un recibo de `/v1/sports/basketball_nba/injuries` y la cuota (`x-daily-used`).
- Respaldo: `~/propline-shared/backups/20261024-5a9cde0/` (`current.before`, `crontab.txt`).
- **Vuelta atrás:** `cd ~/propline-shared && ln -sfn /home/qf/propline-shared/releases/6d459be current.tmp && mv -T current.tmp current`.

### 2026-10-24 13:51 UTC (corrección de registro) · PropLine: cierres y liquidaciones (PR #96) · release `~/propline-shared/releases/6d459be` (`main` `6d459be`)
- Entrada reconstruida a las 14:20 UTC desde el servidor y desde el aviso de la sesión que desplegó; esa sesión terminó sin anotarla.
- `current` pasó de `releases/3babeb4` a `releases/6d459be` (`propline_shared.py` `47a7e3cd…`, config `8a367cab…`, runner `3f4f4745…`, `runtime.json` copiado de `3babeb4`). Coincide con `main` `6d459be`.
- Primera pasada (14:07 UTC, `release: 6d459be`): 36 peticiones correctas y después **`401 invalid_api_key`** a las 14:11:49 UTC en `/v1/sports/soccer_championship/odds`; `stop: provider_http_401`, `exit_code 1`. La clave dejó de valer a mitad de la pasada: no es un fallo del código. Con la clave rechazada, cada pasada se detiene en la primera petición y el archivo no recibe cuotas nuevas.
- **Vuelta atrás:** `ln -sfn /home/qf/propline-shared/releases/3babeb4 current.tmp && mv -T current.tmp current`.


### 2026-10-24 04:45 UTC · Tenis: cuotas del archivo de PropLine, sin The Odds API · imagen `quantfut-tenis:f391b1f` (PR #93, `main` `f391b1f`)
- Estado previo comprobado: la imagen activa `quantfut-tenis:1d2067d` coincidía con `main` anterior salvo `tennis_engine/operations.py` y `tennis_odds_live_v1/__init__.py`, a los que les faltaba el PR #61 (reloj inyectado en `Capture`, sin efecto en producción). El despliegue lo incluye. `vps_run.sh` del servidor coincidía con el del repositorio.
- Imagen construida desde `git archive` de `apps/tennis` con `core.autocrlf=false`, más `src/qf/ingest/propline_shared.py` (sha256 `d95d4661…`) en el contexto (`~/quantfut-tenis/build/66850b1/ctx`). Etiquetada `66850b1` (cabeza del PR) y `f391b1f` (fusión squash, contenido idéntico en `apps/tennis` y `propline_shared.py`).
- `vps_run.sh` nuevo (sha256 `36eaf610…`, igual a `main`): monta `quantfut_artifacts` con `volume-subpath=propline_shared` de solo lectura en `/propline` y **ya no ejecuta `tennis_odds_live_v1`**, así que deja de gastar créditos de The Odds API en tenis. Mismo crontab (`30 0,12 * * *` y `0 11 * * 1`).
- `data/motor_config.json`: añade `odds_provider: propline`, `propline_root: /propline` y `odds_provider_since: 2026-10-24`. `live_odds_root` se queda, pero no se lee con PropLine activo. La actualización semanal conserva las claves que no toca.
- Ensayo previo sin red con el archivo de las 04:08 UTC: 143 eventos, 134 partidos individuales; 60 resueltos por el modelo y los 60 con mercado; 74 sin resolver (nombres abreviados y circuitos menores) caen al apilador v7. Tras activar, con la configuración real: `Motor().forecast` de Schoolkate–Cui da `source: live_snapshot`, `provider: propline`.
- Pendiente de observar: la primera pasada de la entrada automática (22:30 UTC del 24-oct) y qué parte de los sellados sale con `live.provider = propline`.
- Respaldos en `~/quantfut-tenis/backup/20261024-propline/`: `vps_run.sh`, `IMAGE`, `motor_config.json`, `crontab.txt`.
- **Vuelta atrás:** `B=~/quantfut-tenis/backup/20261024-propline; cp -p $B/vps_run.sh $B/IMAGE ~/quantfut-tenis/ && cp -p $B/motor_config.json ~/quantfut-tenis/data/`. La imagen `1d2067d` sigue en el servidor y vuelve la foto de The Odds API, que estará bloqueada por créditos hasta el 1-nov. Los sellados hechos con PropLine se quedan.

### 2026-10-24 04:00 UTC · NBA: productor y panel 1.3.1 (sellado por partido, jugadores con líneas de PropLine) · `main` `62decf6` (PR #91)
- Estado previo comprobado: el código NBA del servidor (`build-price/src/nba`) coincidía con `main` anterior (`3bbf4d2`) salvo `odds_history.py` (no lo usa el productor ni el panel); productor `nba-live13-producer:20261021` y panel `nba-dashboard-live13:20261021`.
- Imágenes nuevas desde `git archive 62decf6` con `core.autocrlf=false` (contexto en `~/nba-isolated/live13/build-producer/`, más `propline_shared.py` de `main`): `nba-live13-producer:20261023` (`7f94bb6154c9`, derivada de `nba-dashboard-live13:20261021` + pdfplumber) y `nba-dashboard-live13:20261024` (`17b301520449`, solo `src/nba` y `web`). Hash del módulo vivo `0663ced1…` = el del modelo.
- Modelo `~/nba-isolated/live13/model/model.json` (sha256 `ded93f16…`): parte de equipo idéntica a la anterior; añade `player_fit` (puntos, rebotes, asistencias). Carpeta nueva `~/nba-isolated/live13/cache` (box scores finales y calendario).
- `producer.sh` nuevo: monta de solo lectura el volumen `quantfut_artifacts` con `volume-subpath=propline_shared` (archivo horario de PropLine) y la caché. Mismo cron `*/10`. Sella cada partido 65-90 min antes de su salto en carpetas `AAAA-MM-DD_HHMM`.
- Panel: contenedor `nba-dashboard-run69` recreado con la imagen nueva y la misma configuración (solo lectura, 256 MB, usuario 1001, mismos montajes); el anterior quedó parado como `nba-dashboard-run71-prev2` (`restart=no`).
- Ensayos previos al cambio: panel nuevo contra las 3 cohortes reales (11+2+11 partidos, sin errores) y productor con carpetas temporales (leyó calendario y archivo). Tras el cambio: `/nba/api/data` con `live_v13` `ok`, 0 problemas, las 3 cohortes y RUN071 intacto; primera pasada de cron 04:00 UTC sin errores (escribió `cache/schedule/2026-10-24.json`).
- Pendiente de observar: primer sellado real (partidos del 24-oct desde ~20:40 UTC); comprobar `prop_lines.state = archivo_aplicado` y pronósticos `player_*` en esa cohorte.
- Respaldos en `~/nba-isolated/live13/`: `crontab.before-20261024`, `model.before-20261024`, `producer.sh.before-20261024`, `dashboard.inspect.before-20261024.json`, `containers.before-20261024.txt`.
- **Vuelta atrás:** `cp producer.sh.before-20261024 producer.sh; rm -r model && cp -a model.before-20261024 model` (la imagen `nba-live13-producer:20261021` sigue en el servidor y `producer.sh` anterior la usa); panel: `docker rm -f nba-dashboard-run69 && docker rename nba-dashboard-run71-prev2 nba-dashboard-run69 && docker update --restart unless-stopped nba-dashboard-run69 && docker start nba-dashboard-run69`. Las cohortes 1.3.1 se quedan; el panel anterior no las lee.
- **Sin tocar:** `nba-live13-price` (captura de precios con The Odds API, bloqueada hasta el 1-nov): pendiente decidir si se retira, porque con varios sellados al día su libro de 2 peticiones/día rechazará la mayoría.


### 2026-10-24 (corrección de registro) · PropLine como proveedor fijo de cuotas · API + worker (imágenes `*-propline:3babeb4`), cron del usuario `qf`
- Entrada reconstruida el 24-oct desde el servidor (solo lectura); la activación original no se anotó aquí. Contenedores recreados a las 01:35 UTC con `quantfut-{api,worker}-propline:3babeb4` (PR #85); `provider.json` = `propline` en `/srv/quantfut/artifacts/propline_shared`.
- Captura horaria: `7 * * * * flock -n ~/propline-shared/capture.lock python3 ~/propline-shared/current/propline_shared_runner.py` (contenedor aislado, release `~/propline-shared/releases/3babeb4`). **Sustituye** al cron `40 */2 * * * propline_captura.py` de la entrada de abajo, que ya no está en el crontab.
- Estado medido 02:20 UTC: `odds_worker` con `source: propline, calls: 0`; 7 ligas en `stale_sports` por falta del PR #86.
- **Alias de ligas (PR #86) desplegado 2026-10-24 ~02:35 UTC, solo worker:** `update_compose.py` (respaldo en `~/propline-shared/backups/20261024-a521569/docker-compose.yml`) cambió la etiqueta a `quantfut-worker-propline:a521569` y `up -d --no-deps --no-build --force-recreate worker`. API sin tocar (`3babeb4`). Verificado: hash de `propline_ingest.py` = `2e5ae8cd54c3` (igual a `main`), `provider.json` = `propline`, cron del worker cargado (127 líneas).
- **Resultado:** `stale_sports` baja de 7 a 4. Resueltas: Championship, Suiza y Noruega. **Siguen:** Segunda División, Serie B, Ligue 2 y Superliga danesa (207 eventos sin emparejar); causa sin investigar (¿alias distintos o sin partidos en la ventana?).
- **Vuelta atrás:** copiar ese `docker-compose.yml` a `~/quantfut/` y `docker compose up -d --no-deps --no-build --force-recreate worker` (la imagen `3babeb4` sigue en el servidor).
- Respaldos de la activación original: `~/propline-shared/backups/20261023-42d6e2a/` (compose, crontab, `.env` previo, contenedores).

### 2026-10-24 01:50 UTC · Descarga de cuotas (BetsAPI) y captura PropLine · solo VPS (usuario `qf`), sin imagen ni base de datos
- Scripts `scripts/betsapi_descarga.py` y `scripts/propline_captura.py` copiados a `~/`; datos en `~/betsapi/data` y `~/propline_data` (no en el repo, no en Docker).
- Cron nuevo: `40 */2 * * * cd $HOME && python3 propline_captura.py --env betsapi/.env.propline --out propline_data`.
- Descarga BetsAPI en segundo plano (`~/betsapi/cadena2.sh`), sin tocar la API, el worker ni la base. Detalle: `docs/datos_cuotas_betsapi_propline_20261024.md`.
- Vuelta atrás: quitar la línea `propline_captura.py` del crontab y `pkill -f betsapi_descarga`; borrar `~/betsapi` y `~/propline_data`.

### 2026-10-22 23:05 UTC · NBA: paso de precios de Pinnacle (captura al sellar cada cohorte) · cron del usuario `qf` (PR #77, `main` `2b09b56`)
- Imagen `nba-live13-price:20261022` (`f4774fb18cbd`), derivada de `nba-live13-producer:20261021`; solo cambia `src/nba`. El contexto de construcción sale de `git archive` de `main` con `core.autocrlf=false` (con el `autocrlf` de Windows exportaba CRLF y habría roto el `.sh`); los 69 archivos del servidor se comprobaron byte a byte contra los blobs de `main`. Envoltorio `~/nba-isolated/live13/price.sh` (`flock` propio, sin tocar `producer.sh`).
- Contenedor de corta vida (segundos): usuario 1001, raíz de solo lectura, `--cap-drop ALL`, `no-new-privileges`, 64 procesos, 256 MB, red propia `nba-price`. Montajes: `cohorts` solo lectura, `price` y `ledger` escribibles, `private/odds_key` solo lectura en `/run/secrets/odds_key` (nunca como variable de entorno). Comprobado dentro del contenedor con los montajes reales: clave legible (600, 32 bytes) y no escribible, cohortes no escribibles, `price`/`ledger` escribibles, salida TCP a `api.the-odds-api.com:443` (sin petición).
- Clave: `~/nba-isolated/live13/private/odds_key` (carpeta 700, archivo 600), copia byte a byte (`cmp`) de la del piloto `run67` (misma cuenta compartida con fútbol), hecha sin leerla. Ningún otro contenedor la monta.
- Presupuesto fuera de las cohortes (`ledger/`): máximo 2 peticiones por día UTC y 70 créditos por mes, reserva de 2.000 sobre el último saldo conocido, y un archivo `ledger/halt` ante cualquier fallo que bloquea todo hasta que una persona lo lea y lo borre. Fases `seal` (<=15 min tras sellar) y `close` (30-10 min antes del primer salto).
- Cron nuevo: `*/5 * * * * /home/qf/nba-isolated/live13/price.sh >> ~/.local/share/quantfut/nba_live13_price.log 2>&1`. **Bloqueado en código hasta el 2026-11-01**: hasta entonces cada pasada solo escribe `blocked_until`, no lee la clave ni hace ninguna petición. Verificado: ensayo sin red y sin clave, ejecución manual de `price.sh`, segunda ejecución con el `flock` ocupado (sale sin hacer nada) y el primer tick real de cron (23:05:06 UTC).
- Sin tocar: productor (`producer.sh`, su imagen y su `model.json`), panel, API, worker, caddy, db, cache, grafana y captura de investigación; los IDs de contenedores son idénticos antes y después (`containers.before-price.txt`) y el `diff` del crontab con su respaldo es una sola línea añadida.
- Aviso del paso 0 (`scripts/deploy.sh estado`, solo lectura): deriva ajena de fútbol, API con 27 archivos distintos a `main` y 28 que faltan, worker con 1 (`api/main.py`). No se tocó; es de otra sesión.
- Si se reconstruye la imagen del productor desde `main`, hay que emparejarla con un `model.json` ajustado con el módulo actual (parámetros idénticos), porque la PR #77 cambió el hash de `multimarket_v13_live.py` (caché de `completed()`); el productor desplegado sigue con su módulo y su modelo.
- Primera captura real: desde el 2026-11-01, tras el primer sellado (17:35 ET). Revisar `price/<cohorte>/seal.json` (`credits: 1`), `ledger/requests.jsonl` (una línea) y que el sha256 de `seal_raw.json` coincida con el recibo. Procedimiento y plantilla de informe en `docs/nba_captura_precio_servidor_propuesta_20261022.md` y `docs/nba_mercado_prospectivo_20261101.md`.
- Respaldos: `~/nba-isolated/live13/crontab.before-price-20261022` y `containers.before-price.txt`; contexto de construcción en `~/nba-isolated/live13/build-price/`.
- **Vuelta atrás:** `crontab ~/nba-isolated/live13/crontab.before-price-20261022` (o borrar solo esa línea), `rm ~/nba-isolated/live13/price.sh`, `docker network rm nba-price`, `docker rmi nba-live13-price:20261022` y, si se quiere retirar la copia de la clave, `rm -r ~/nba-isolated/live13/private`. Lo guardado en `price/` y `ledger/` queda en disco sin efecto. Si aparece `ledger/halt`: leerlo y mirar `nba_live13_price.log` y `price/<cohorte>/attempts.jsonl` antes de borrarlo.

### 2026-10-22 20:30 UTC · Líneas nuevas de córners por equipo (#74, `0afd388`) · solo worker (`docker cp` + imagen congelada, sin recrear)
- **Antes:** `model/estadisticas_mercado.py`, `publish/alta_prob.py`, `publish/alta_prob_datos.py` y `publish/escalera_datos.py` del worker coincidían con `main` previo (`8c9cb5e`). Respaldo en `releases/auditoria-motores/backup/worker_lineas_*.before`.
- **Despliegue:** `docker cp` de los cuatro archivos de `main` y `docker commit` → `quantfut-worker:lineas-0afd388` (`44c280f02c98`) = `latest`. `deploy.sh estado`: worker = `main` salvo las dos diferencias ajenas ya anotadas; `latest` = lo que corre.
- **Líneas nuevas:**
  - Alta probabilidad tiene 12 líneas de córners. Las nuevas son local más de 4,5, menos de 5,5 y menos de 6,5, y visitante menos de 4,5 y 5,5; solo se ofrecen con la supremacía del Motor A.
  - La escalera y la lista de mercados suman local menos de 6,5 y visitante menos de 5,5.
- **Comprobado:** ensayo en seco de alta probabilidad y escalera sin errores (sin partidos en la ventana a esta hora). Primer uso real: el job de las 09:00 UTC del 23-oct.
- **Vuelta atrás:** `docker cp releases/auditoria-motores/backup/worker_lineas_<archivo>.before quantfut-worker-1:/app/src/qf/<ruta>` para los cuatro y `docker tag quantfut-worker:corners-c4e6378 quantfut-worker:latest`.

### 2026-10-22 19:40 UTC · Córners de cada equipo según la supremacía del Motor A (#72, `c4e6378`) · solo worker (`docker cp` + imagen congelada, sin recrear)
- **Antes:** `model/estadisticas_mercado.py`, `publish/escalera_datos.py` y `publish/alta_prob_datos.py` del worker coincidían con `main` previo (`9697aa1`). Respaldo en `releases/auditoria-motores/backup/worker_*.before`.
- **Despliegue:** `docker cp` de los tres archivos de `main` y `docker commit` → `quantfut-worker:corners-c4e6378` (`b04cebc4bf97`) = `latest`. `deploy.sh estado`: worker = `main` salvo las dos diferencias ajenas ya anotadas (`api/main.py`, `publish/tarjetas_seg.py`); `latest` = lo que corre. La API no usa los córners por equipo y no se toca.
- **Comprobado:** en ensayo en seco con las predicciones de hoy, los 10 partidos con modelo de córners reciben la supremacía (Real Madrid-Leipzig: córners del local 5,43 → 6,14). Primer uso real: alta probabilidad y escalera del job de las 09:00 UTC del 23-oct.
- **Vuelta atrás:** `docker cp releases/auditoria-motores/backup/worker_<archivo>.before quantfut-worker-1:/app/src/qf/<ruta>` para los tres y `docker tag quantfut-worker:auditoria-a779e08 quantfut-worker:latest`.

### 2026-10-22 18:50 UTC · Auditoría de los motores, pasos 1-3 (#70, `a779e08`) · worker (imagen congelada + recreate), API (imagen nueva), `.env`
- **Antes de desplegar.** `deploy.sh estado`: los 7 archivos tocados coincidían con `main` previo (`c57afe8`) en el worker. Había dos diferencias ajenas en el worker que se **conservan**:
  - `api/main.py`, versión anterior, sin uso en el worker;
  - `publish/tarjetas_seg.py`, con `LINEAS_SEGUIMIENTO`, copiado desde la rama local `tarjetas-lineas-seguimiento` (`734b50f`) sin PR ni entrada aquí. Esa sesión debe fusionarlo.
- **Worker.**
  - `deploy.sh congelar worker`: `en-ejecucion-20261022` = `820ebd5f4c67`; el `latest` anterior queda como `latest-previo-20261022` (`25bf76ea2f46`).
  - `docker cp` de `config.py`, `eval/backtest.py`, `model/{calibration,dixon_coles,train}.py` y `api/{mobile,partido_mercados}.py` (hashes iguales a `main`).
  - `docker commit` → `quantfut-worker:auditoria-a779e08` (`9db4a5780fa1`) = `latest`.
  - En `~/quantfut/.env`: `DECAY_HALFLIFE_DAYS=180` → `270`.
  - `up -d --no-deps --no-build --force-recreate worker`. Verificado: config 270 / `ridge_partidos` 0,5, cron en marcha, código = `main` salvo las dos diferencias ajenas, `latest` = lo que corre, y el artefacto activo anterior carga igual (ridge 0, media vida 180).
  - Se esperó a que no hubiera sellos tardíos pendientes; los 2 partidos de UEL de las 19:00 sin sello no tenían predicción (equipos fuera del modelo).
- **API.**
  - Imagen `quantfut-api-web-vip:auditoria-a779e08` = `web-arranque` + `api/mobile.py`, `api/partido_mercados.py` y `config.py` de `main`; compose fijado a esa imagen.
  - `/health` 200. En el dominio real, Tottenham-Coventry (equipo desconocido) muestra el 1X2 del mercado (visitante 15,2 %), no el del modelo (6,6 %).
- **Reentrenamiento** (`python -m qf.model.train`, 18:53 UTC): modelo **2026.10.22-185314 activo** (18:56 UTC; antes `2026.09.27-010508`). Convergió; en la validación del último año (2.024 partidos, mismas filas) Dixon-Coles tiene RPS 0,20359, Elo 0,20412 y mercado 0,19458. El calibrador se rechazó (calibrar empeoraba el 1X2: RPS 0,20900 → 0,20959), así que se publica sin calibrar. `ready_for_commercial_picks` sigue en falso (CLV 0 < 300). Altitud y once siguen en sombra. Primer lote con este modelo: el diario del 23-oct a las 09:00 UTC; las predicciones ya selladas no cambian.
- **Vuelta atrás.**
  1. `cp releases/auditoria-motores/backup/env.before .env`.
  2. `docker tag quantfut-worker:en-ejecucion-20261022 quantfut-worker:latest` + recreate del worker.
  3. `cp releases/auditoria-motores/backup/docker-compose.before.yml docker-compose.yml` + recreate de la API.
  4. Si el modelo nuevo quedó activo: `UPDATE model_artifacts SET is_active = (model_version = '2026.09.27-010508')`.

### 2026-10-22 03:55 UTC · Tarjetas: más líneas en el seguimiento · worker (un archivo), rama `tarjetas-lineas-seguimiento`
- Cambio: `publish/tarjetas_seg.py` guarda también «más de» 2,5-7,5 y «menos de» 3,5/7,5 en `tarjetas_seg` (solo seguimiento, no se publica; `LINEAS_HABILITADAS` intacta).
- Método: `docker cp` de ese único archivo al worker (parche del contenedor, no de la imagen: se pierde si se recrea). Antes era idéntico a `main` (`a1b677a39432`); ahora `bd63ecb7f9af`, igual a la rama. Sin reinicios.
- Verificado: importa y carga 11 líneas; `preview` sin error. Los partidos que ya tenían filas hoy no se completan (solo los nuevos); se verá en la pasada diaria de las 08:00 UTC.
- Vuelta atrás: `docker cp ~/quantfut/deployments/tarjetas-lineas-20261022/antes/tarjetas_seg.py quantfut-worker-1:/app/src/qf/publish/tarjetas_seg.py`.
- **Fusionado en `main` el 22-oct** (rama `tarjetas/lineas-seguimiento`): el archivo del worker ya coincide con `main`; desaparece la diferencia ajena anotada en las entradas del mismo día.

### 2026-10-21 · AdMob (ID de editor y bloque) y estado de Meta · SOLO configuración en la base, sin código ni reinicios
- `reward_settings` (vía `qf.api.anuncios.save_config`, auditado como `ssh:claude-titular`): `admob_publisher_id = pub-3902371555866850` y
  `ad_unit_android = ca-app-pub-3902371555866850/4169479093` (bloque Recompensado, SSV con `https://pronosticosdeportivos.pro/rewards/callback/admob`).
  Siguen `ads_enabled = true` y `ad_test_mode = true`: la app muestra bloques de prueba de Google.
- `GET /app-ads.txt` ya responde `google.com, pub-3902371555866850, DIRECT, f08c47fec0942fa0` (antes 404). AdMob tarda hasta 24 h en verificar la app.
- Comprobado por SSH: `META_PIXEL_ID`, `META_DATASET_ID`, `META_CAPI_TOKEN` definidos y `META_CAPI_ENABLED=1`; sin `META_TEST_EVENT_CODE`. El código de Whop y de Meta web
  del contenedor API es el de `main`, salvo `meta_capi.py` (el de la API no trae el extinfo de reserva; el del worker sí, y es el que envía). Cola `meta_events`: 1 `CompleteRegistration` enviado, ninguna compra aún.
- App de Meta (ID `1369265108354712`): plataforma Android con paquete y clase, tres hashes de clave y registro automático de compras apagado; app vinculada al dataset `2253839992227148`.
- Cambio de código aparte: #67 (ID de app de AdMob de Android en el manifiesto). iOS conserva el ID de ejemplo hasta registrar esa app en AdMob.
- **Vuelta atrás:** vaciar `admob_publisher_id` y `ad_unit_android` en `/control/anuncios` (la ruta vuelve a 404).

### 2026-10-21 17:05 UTC · Web: arreglo del arranque (la web quedaba en «Consultando…») · API (imagen nueva), commit `45fdb96`
- Causa: `app.js` llamaba a `render()` antes de declarar `publicAuthKey`/`publicFetch` (zona muerta temporal): ReferenceError en el primer render, el script abortaba y nunca cargaba los datos públicos. Se mueven las declaraciones antes del primer `render()` y `app-order.test.mjs` lo exige.
- Imagen `quantfut-api-web-vip:web-arranque` = `web-renovacion` + `frontend/{app.js,index.html}` (hash de ambos comprobado contra `main` previo antes de sobrescribir). `index.html` lleva el sello nuevo `app.js?v=935045b8a991`: sin re-sellar, Cloudflare sirve el script viejo bajo la URL con el sello anterior. Compose fijado; worker, base y Caddy sin tocar.
- Verificado: `/health` 200, `/` referencia `app.js?v=935045b8a991` (hash servido igual al de `main`), la pestaña Escalera carga retos e historial reales.
- Vuelta atrás: `releases/web-arranque/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` + `docker compose up -d --no-deps --no-build --force-recreate api`.

### 2026-10-21 16:43 UTC · NBA: productor diario de cohortes v1.3 · cron del usuario `qf` (PR #66)
- Imagen `nba-live13-producer:20261021` (`7a77272bba60`), derivada de `nba-dashboard-live13:20261021` + `pdfplumber==0.11.9`; envoltorio `~/nba-isolated/live13/producer.sh` (`flock`, solo un proceso, contenedor de solo lectura salvo `cohorts`, 512 MB, sin credenciales). Datos y modelo en `~/nba-isolated/live13/{data,model}`; cohortes en `~/nba-isolated/live13/cohorts` (el dashboard las monta de solo lectura).
- Cron nuevo: `*/10 * * * * /home/qf/nba-isolated/live13/producer.sh >> ~/.local/share/quantfut/nba_live13.log 2>&1`. Cada pasada recoge los resultados finales (≥3 h tras el salto) y, desde las 17:35 ET, sella una vez por fecha los partidos que no han empezado. Primera ejecución manual 16:43 UTC y primera por cron 16:50 UTC: sin errores, sin sellar (aún antes de las 17:35 ET).
- Cohorte `2026-10-21_ensayo` (11 partidos, 44 pronósticos, sellada 14:39 UTC con el reporte de las 10:30 ET) copiada a mano al servidor; el ensayo en seco del productor (carpeta de pruebas, ya borrada) selló lo mismo con el reporte de las 11:45 ET y aceptó el hash del modelo.
- Sin tocar: API, worker, caddy, db, cache, grafana, capture, paper-pilot, ni el resto del crontab (tenis, firebase).
- **Vuelta atrás:** `crontab ~/nba-isolated/live13/crontab.before-20261021` (copia del crontab anterior) o borrar solo la línea del productor; las cohortes selladas se quedan y el dashboard sigue igual.

### 2026-10-21 15:45 UTC · NBA: pronósticos prospectivos v1.3 en /nba · contenedor del dashboard NBA, `main` (`f99fdaf`, PR #63)
- Imagen `nba-dashboard-live13:20261021` (`8810415bb98e`), derivada de `nba-dashboard-run71:20261009`: solo cambia `src/nba`, `web` y el `CMD` (`nba.multimarket_live_dashboard`); mismo `public-bundle` de RUN071. Nuevo montaje de solo lectura `~/nba-isolated/live13/cohorts` en `/live-cohorts`. Mismos límites y montajes que antes (read-only, usuario 1001, sin capacidades, 256 MB, sin credenciales).
- Ensayo previo con un contenedor temporal (RUN071: 42 + 15 pronósticos; cohorte v1.3: 44). Tras el cambio: `/`, `/nba`, `/nba/app.js` 200, `/nba/.env` 404; la página muestra RUN071 intacto y la cohorte `2026-10-21_ensayo` (11 partidos sellados 14:39 UTC); consola sin errores propios. Los demás contenedores conservan su ID (API, worker, caddy, db, cache, grafana, capture, paper-pilot); Caddy sin cambios (sigue apuntando a `nba-dashboard-run69`).
- **Sin productor aún:** nadie sella cohortes nuevas ni recoge resultados en el servidor; la cohorte se copió a mano. Pendiente decidir dónde corre (el servidor sí llega a nba.com y a los PDF de lesiones, comprobado).
- Respaldo: `~/nba-isolated/dashboard/live13-20261021/backup/` (inspect del contenedor, ID de la imagen, lista de contenedores). El contenedor anterior quedó parado como `nba-dashboard-run71-prev` (restart=no).
- **Vuelta atrás:** `docker rm -f nba-dashboard-run69 && docker rename nba-dashboard-run71-prev nba-dashboard-run69 && docker update --restart unless-stopped nba-dashboard-run69 && docker start nba-dashboard-run69`.

### 2026-10-20 03:55 UTC · Motor de tenis al VPS (servicio nuevo, aislado del fútbol) · imagen `quantfut-tenis:1d2067d` + crontab de `qf`, PR #53 y #54 (`205f62b`)
- Orden del titular («haz lo que queda»): sacar el tenis del PC para que no dependa de que esté encendido. **No toca ningún servicio de fútbol**: ni contenedores, ni compose, ni el crontab del worker, ni la base.
- Imagen propia `quantfut-tenis:1d2067d` construida en el servidor desde `git archive` de `apps/tennis` (`apps/tennis/Dockerfile`, `python:3.12-slim`). El código Python de la imagen es idéntico al de `main` (`205f62b` solo cambia el script del host). Datos en `~/quantfut-tenis/data` (221 MB: base semanal, modelos, parámetros, registros de cuotas y de la entrada automática traídos del PC), claves en `~/quantfut-tenis/secrets` (700/600: `ODDS_API_KEY` y `API_TENNIS_KEY`), imagen activa en `~/quantfut-tenis/IMAGE`.
- Crontab de `qf` (hora del servidor, Europe/Berlin): `30 0,12 * * * ~/quantfut-tenis/vps_run.sh twice-daily` (foto h2h + entrada; una por media jornada UTC, también con horario de invierno) y `0 11 * * 1 ~/quantfut-tenis/vps_run.sh weekly`. Respaldo previo: `~/quantfut-tenis/backup/crontab_qf_antes_20261020.txt`.
- Verificado: entrada en seco dentro del contenedor (34 ya sellados, sin duplicar), `tennis_motor forecast` con foto de cuotas, y la tarea semanal lanzada por el mismo script (0 descargas, 171 reutilizados, base al 20-oct, reentreno y promoción de `motor_config.json`; archivos a nombre de `qf`).
- En el PC, las tareas de Windows «QuantFut tenis cuotas h2h» y «QuantFut tenis datos semanales» quedan **desactivadas** (no borradas) para no duplicar llamadas ni sellos.
- Vuelta atrás: `crontab ~/quantfut-tenis/backup/crontab_qf_antes_20261020.txt` y reactivar las dos tareas de Windows; los datos del PC en `data/tennis/{intake_v1,live_odds_v1,weekly}` se quedaron como estaban a las 03:50 UTC (para volver, copiar antes los del servidor hacia el PC).

### 2026-10-21 13:19 UTC · Web: los planes de Whop se renuevan solos y el texto lo dice antes de pagar · API (imagen nueva), PR #58 (`466a141`)
- El titular confirmó (21-oct) que los planes de Whop se renuevan automáticamente; la web decía lo contrario (preguntas frecuentes: «No… no hay cobros recurrentes»; cuenta: «Sin renovación automática»). Ahora las preguntas frecuentes, la sección de cuenta, el resumen del pedido y la sección de pago informan de que se renueva al terminar cada periodo, al mismo precio, hasta cancelar la renovación desde la cuenta de Whop. El titular confirmó el 21-oct que la renovación se cancela desde Whop; falta solo la revisión legal del texto.
- Imagen `quantfut-api-web-vip:web-renovacion` = `web-copy-pago` + `frontend/{app.js,membership.js,index.html}`; el script de despliegue comprobó el hash de los tres antes de sobrescribir. Verificado: `/health` 200, `/` referencia `app.js?v=d4f8a8a02038` y el `membership.js` versionado trae el texto nuevo.
- Nota: el job «tenis» del CI falló ese día por una prueba de `apps/tennis` que depende de la fecha (ajena a este cambio; marcada como tarea aparte). El arnés principal («arnes») pasó.
- Vuelta atrás: `releases/web-renovacion/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` + `docker compose up -d --no-deps --no-build --force-recreate api`.

### 2026-10-20 04:51 UTC · Web: los textos de pago siguen la configuración del servidor · API (imagen nueva), PR #56 (`375c720`)
- Whop está habilitado en producción (`/app/v1/whop/config` devuelve `enabled: true`, los tres planes tienen `whop_plan_id`), pero la web decía en tres sitios (planes, paquetes, preguntas y cuenta) que el pago en línea todavía no estaba habilitado. Ahora `membership.js` usa `payOn()` (la configuración del servidor) y se vuelve a pintar al cargarla. No se añade ninguna afirmación nueva sobre renovaciones.
- Archivos idénticos a lo esperado antes de sobrescribir (hash comprobado por el propio script de despliegue): `frontend/{app.js,membership.js,index.html}`. Imagen `quantfut-api-web-vip:web-copy-pago` = `a1a8dcd` + esos 3 archivos; compose fijado. Worker, base y Caddy sin tocar.
- Verificado: `/health` 200; `/` referencia `app.js?v=beb802cbd502` y este `membership.js?v=0b23a539278e` (hash del servidor coincide). La URL sin versión de `membership.js` sigue en la caché de Cloudflare, pero la página no la usa.
- Vuelta atrás: `releases/web-copy-pago/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` + `docker compose up -d --no-deps --no-build --force-recreate api`.

### 2026-10-20 03:00 UTC · Artefacto del ajuste del once reajustado con la muestra ampliada · worker (solo un archivo de datos)
- `ajuste_xi_ampliado-2024-01-01_2026-10-19.pkl` (11.920 partidos) en `/srv/quantfut/artifacts`; `calcular` carga el más reciente, así que desde ahora los factores en sombra usan este y quedan marcados con `oos_version = ampliado-...`. Sin cambios de código, sin tocar los lambdas sellados. Vuelta atrás: borrar ese archivo (vuelve al de `2026.10.19-131830`).

### 2026-10-20 01:08 UTC · Captura extra de FotMob a T-30 y sello sin once oficial a T-25 · worker (2 archivos, `docker cp`) + crontab, PR #47 (`9811b7c`)
- Orden del titular (opción 2: captura extra a T-30). Solo ~56 % de los partidos traían el once oficial a T-45 (primer sello real, 19-oct 23:40 UTC: `sin once oficial`). Nueva ventana de captura `tarde` (~T-33 a T-28), que se solapa con `cierre` (cada pasada toma la primera pendiente), y el cron de `previos` pasa de cada 15 a cada 5 min (solo pide a FotMob si hay una ventana pendiente: ~25 % más de peticiones por partido). Sin once oficial, el sello por partido espera hasta T-25 (antes T-38).
- Archivos idénticos a `main` previo antes de copiar: `ingest/fotmob_captura.py`, `publish/sello_tardio.py`. Solo cambió la línea de `previos` del crontab. Sin reinicio: el walk-forward ampliado siguió corriendo (segundo trozo terminado).
- Las pruebas del job diario dejaban de pasar al cambiar la fecha (el corte del sello por partido es 2026-10-20): se fijó el corte en None en esas pruebas y se añadió una que comprueba que con el corte activo el diario no crea picks.
- Vuelta atrás: copiar de vuelta `releases/captura-tarde-t30/backup/*` y cargar `backup/crontab_worker.txt`.

### 2026-10-19 22:06 UTC · El lote de partido lleva el factor del once · worker (2 archivos, `docker cp`) + crontab, PR #44 (`f466d94`)
- Orden del titular («sí, despliega»), antes del primer sello real. `hashchain._collect_partido` ahora incluye `sello_tardio` (disparo, minutos al saque y `ajuste_xi`) en el JSON sellado: así el factor se puede verificar por terceros al revelarse el lote. Aún no había ningún lote de partido, así que no cambia ningún hash existente. `ajuste_xi --avisar` y su cron diario (07:30 UTC) avisan una sola vez al llegar a 150 partidos con efecto.
- Archivos idénticos a `main` previo antes de copiar. Sin reinicio: el walk-forward ampliado siguió corriendo. Verificado: importa, `hashchain verify` OK con 21 lotes, `--medir` responde.
- Vuelta atrás: copiar de vuelta `releases/sello-factor-f466d94/backup/*` y cargar `backup/crontab_worker.txt`. Un lote de partido ya sellado conserva su formato.

### 2026-10-19 19:20 UTC · Ajuste del once en MODO SOMBRA y sello por partido ACTIVO desde el 20-oct · worker (5 archivos, `docker cp`) + API (imagen nueva) + crontab, PR #42 (`a1a8dcd`)
- Orden del titular (confirmó el modo sombra, el corte y el walk-forward ampliado). **`LOTE_POR_PARTIDO_DESDE = 2026-10-20`**: desde el 20-oct 00:00 UTC cada partido con predicción diaria se predice de nuevo (etapa `final`) y se sella solo, con las dos alineaciones capturadas (≤ 90 min) o a T-38 (T-45 menos 7 min de gracia, porque la captura de FotMob de T-45 corre en el mismo minuto). El lote diario de las 09:00 UTC sigue igual.
- **Ajuste del once** (`model/ajuste_xi.py`, bloque `epi_total`): calcula el factor y lo anota en `data_completeness.sello_tardio.ajuste_xi`; **no cambia los lambdas**. Artefacto `ajuste_xi_2026.10.19-131830.pkl` (4.255 partidos). El once sale de la captura oficial de FotMob (`tipo_alineacion='standard'`). Medición hacia adelante: `python -m qf.model.ajuste_xi --medir`.
- Archivos: worker `model/{jugadores,ajuste_xi}.py`, `config.py`, `publish/{sello_tardio,hashchain}.py` (idénticos a `main` previo antes de copiar). API: imagen `quantfut-api-web-vip:a1a8dcd` = `07c12bc` + `api/main.py` (`/chain` añade `batch_kind` y `match_id`), `config.py`, `hashchain.py`, `jugadores.py`, `ajuste_xi.py`, `sello_tardio.py`. Crontab recargado: solo se añade `estado_xi` cada hora (el job de sello ya estaba).
- Verificado: `/health` 200; `/chain` lleva `batch_kind`; `hashchain verify` OK con 21 lotes; `calcular` sobre 6 partidos reales con once oficial; el estado se reconstruye en ~2 min (17.332 jugadores, 495 equipos). El primer sello real será el de un partido del 20-oct.
- Vuelta atrás: poner `LOTE_POR_PARTIDO_DESDE = None` en `hashchain.py` del worker (apaga el sello por partido sin tocar nada más); o restaurar `releases/f7-sombra-a1a8dcd/backup/*` y el compose previo. Los lotes de partido ya sellados quedan en la cadena (inmutable).

### 2026-10-19 UTC · Impacto por jugador (solo medición) · worker (2 archivos, `docker cp`), PR #40 (`3284e6c`)
- `model/jugadores.py` (nuevo) y `model/contexto.py` copiados al worker para poder medir los bloques `epi_*`. No los usa ningún job ni cron: no cambia el modelo, ni lo sellado, ni la API. `contexto.py` era idéntico a `main` previo a #40.
- Verificado: importa junto con `daily`; `hashchain verify` OK con 21 lotes. Vuelta atrás: copiar de vuelta `releases/jugadores-3284e6c/backup/contexto.py` y borrar `jugadores.py`.

### 2026-10-19 13:15 UTC · F7 sello tardío por partido (APAGADO) · migración 084 + worker (8 archivos, `docker cp`) + API (imagen nueva) + crontab, PR #38 (`07c12bc`)
- Orden del titular («hazlo»). **El corte `LOTE_POR_PARTIDO_DESDE` sigue en `None`**: el job `sello_tardio` corre cada 5 min pero responde `apagado`, y el lote diario no cambia. Falta fijar el corte (decisión aparte, tras el reentrenamiento).
- **Migración `db/084`** aplicada a producción (transacción con `lock_timeout 5s`): `predictions.etapa` (387 filas `diaria`), `prediction_batches.batch_kind`/`match_id` (21 lotes `diario`) y sus restricciones. Aditiva: el código anterior la ignora.
- Antes de sobrescribir: los 7 archivos del worker eran idénticos a `main` previo a #38; en la API eran versiones anteriores (se llevan a `main`).
- **Worker:** `model/{lineup_challenger,shadow}.py`, `publish/{alta_prob_datos,daily,escalera_datos,hashchain,parley_datos,sello_tardio}.py`. **API:** imagen `quantfut-api-web-vip:07c12bc` = `8be381b` + esos archivos; compose fijado. **Crontab** recargado por stdin: solo se añadió la línea de `sello_tardio` (el resto igual, solo reordenado).
- Verificado: `/health` 200; `/alta-probabilidad` activa; `hashchain verify` OK con 21 lotes; el lote de las 09:00 UTC de hoy (sellado con el código anterior) lleva `ajuste_altitud` en las 9 predicciones.
- Vuelta atrás: restaurar `releases/f7-sello-07c12bc/backup/docker-compose.before.yml` + `up -d --no-deps --no-build --force-recreate api`; copiar de vuelta `backup/worker_*.py` y cargar `backup/crontab_worker.txt`. La migración se deja (aditiva); esquema previo en `backup/esquema_antes.sql`.

### 2026-10-19 UTC · Motor B medido por partido (control del «fallo grosero») · worker (3 archivos, `docker cp`) + API (imagen nueva), PR #36 (`8be381b`)
- Orden del titular. Sin migración. Los lotes ya sellados no cambian: solo cambia cómo el control de alta probabilidad mide el acierto (varianza por partido, la mayor de las dos) y lo que muestra el historial (`partidos`, `margen_ee` por mercado).
- Antes de sobrescribir: los 3 `publish/alta_prob*.py` del worker eran idénticos a `main` previo a #36; en la API eran una versión anterior (se llevan a `main`), y `frontend/app.js` e `index.html` eran idénticos.
- **Worker:** `alta_prob.py`, `alta_prob_datos.py`, `alta_prob_ext.py` copiados con `docker cp` (se pierden al recrear el worker; ya están en `main`). Sin reinicio ni cambio de cron.
- **API:** imagen `quantfut-api-web-vip:8be381b` = la anterior + esos 3 archivos + `frontend/app.js` + `frontend/index.html`. Ensayo previo en contenedor aparte (importa bien, 118 rutas). Compose fijado en ella.
- Verificado en el dominio real: `/health` 200; `app.js` servido con el hash de `main`; `/alta-probabilidad` devuelve `partidos` y `margen_ee` por mercado.
- Vuelta atrás: `releases/b-por-partido-8be381b/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` + `docker compose up -d --no-deps --no-build --force-recreate api`; para el worker, copiar de vuelta `backup/worker_*.py`.

### 2026-10-19 04:07 UTC · Herramienta de diagnóstico de córners · worker (un archivo nuevo, `docker cp`)
- `eval/corners_diagnostico.py` copiado al worker para ejecutarlo contra la base (solo lectura). No lo importa ningún job ni cron; no
  cambia el modelo ni lo publicado. Vuelta atrás: borrar el archivo del contenedor. Detalle: `docs/corners_diagnostico_20261019.md`.

### 2026-10-19 02:12 UTC · Altitud en el motor A en MODO SOMBRA · worker (4 archivos, `docker cp`), sin reinicio
- Orden del titular: que la información nueva entre a los motores. Se midió cada bloque (docs/contexto_en_el_motor_20261019.md): solo
  la altitud pasa la puerta, con evidencia débil; clima, descanso, bajas y valor del once no mejoran el modelo. La altitud entra en
  **modo sombra**: calcula el factor y lo anota en cada predicción, **sin cambiar los lambdas publicados**.
- Archivos (idénticos a `main` antes de copiar, `daily.py` y `config.py`; los otros dos son nuevos): `publish/daily.py`, `config.py`,
  `model/contexto.py`, `model/ajuste_altitud.py`. Originales de los dos que existían en `releases/contexto-altitud/antes/`.
  Vuelta atrás: copiar de vuelta `daily.py` y `config.py` desde esa carpeta (los dos módulos nuevos quedan sin uso).
- Artefacto `ajuste_altitud_2026.10.12-221104.pkl` en `/srv/quantfut/artifacts`. Sin migración, sin cambios en el cron.
- Modo por `AJUSTE_ALTITUD_MODO` (`off`, `sombra` por defecto, `activo`); el worker en marcha no tiene la variable, así que usa `sombra`.
- Verificado: simulación de solo lectura sobre los 145 partidos modelados de los próximos 8 días (35 con efecto > 0,5 %, lambdas
  intactos en todos). El primer sellado con el código nuevo es el de las 08:00 UTC: comprobarlo mañana (`data_completeness.ajuste_altitud`
  presente y lambdas iguales a los de antes). Modelo activo, API y base sin cambios.

### 2026-10-19 01:45 UTC · Web: bloqueados difuminados, un gratis por sección y VIP ve todo · API (7 archivos), PR #31 (`5f21e93`)
- Orden del titular («si hazlo»). Sin migración. La app móvil no se toca y sus rutas (`/mobile/v1/*`) no cambian.
- Antes de sobrescribir se comprobó que los 7 archivos eran idénticos a `origin/main` dentro de `quantfut-api-meta-web:db24a88`:
  `frontend/{app,cuenta-api,membership,public-data}.js`, `frontend/{index.html,styles.css}` y `src/qf/api/main.py`.
- **API:** imagen `quantfut-api-web-vip:5f21e93` = la anterior + esos 7 archivos (ensayo en contenedor aparte: 118 rutas en las dos;
  los hashes de la imagen coinciden con los fusionados). Compose fijado en ella. Worker, base de datos y Caddy sin tocar.
- Qué cambia para el usuario: en la web, los pronósticos bloqueados salen difuminados (cuota incluida) con «Acceso VIP» a Suscripciones;
  el visitante ve **un** gratis por sección (alta probabilidad pasa de 4 a 1); una cuenta VIP ve todos (`/alta-probabilidad` y `/escalera`
  usan `member`, como `/parley`); parley bloqueado ya no rompe la vista.
- Verificado en el dominio real: `/health`, `/`, `app.js`, `public-data.js`, `styles.css`, `membership.js` y `cuenta-api.js` responden 200;
  `/alta-probabilidad` lleva `Cache-Control: no-store` y `Vary: Authorization`; con un token falso responde 401 (la web cae a visitante).
  **No se pudo comprobar con datos en vivo** el reparto 1 visible / resto bloqueado ni lo que ve una cuenta VIP: a la 01:45 UTC no hay
  pronósticos abiertos (alta probabilidad 0, escalera sin bloqueados) porque el lote llega a las 08:00 UTC. Repetir la comprobación
  después de ese lote, y probar con una cuenta con suscripción real.
- Vuelta atrás: restaurar `releases/web-vip-5f21e93/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` y
  `docker compose up -d --no-deps --no-build --force-recreate api` (la imagen anterior sigue en el servidor).
  Respaldo de los 7 archivos previos en `releases/web-vip-5f21e93/backup/archivos-antes.tar`.

### 2026-10-18 · ERA5 automático diario · worker (entorno) + cron
- Orden del titular: conservar el token de Copernicus para la descarga automática. Cron nuevo `20 6 * * *` (06:20 UTC)
  `flock -n /tmp/era5.lock python -m qf.ingest.era5_clima` (incremental; pide solo lo que los archivos guardados no cubren).
- El worker en marcha no tenía `CDS_API_TOKEN` (el entorno de cron sale de `/etc/environment`, que se vuelca del `.env` solo al
  arrancar el contenedor). Se añadió la línea a `/etc/environment` **dentro del contenedor** (parche que se pierde al recrearlo).
  Al recrear el worker el 1-nov no hace falta repetirlo: `docker-compose.yml` usa `env_file: .env`, que ya contiene el token.
- Crontab cargado con `cat scripts/crontab | docker compose exec -T worker crontab -` y comprobado (5 líneas de FotMob, sedes y calendario
  más la de ERA5). Respaldo previo: `~/backups/crontab_pre_era5_20261018`. Vuelta atrás: restaurarlo y recargar.

### 2026-10-18 · Meta CAPI: extinfo de reserva válido · worker (un archivo, `docker cp`), PR #29
- `src/qf/comercial/meta_capi.py` copiado al contenedor worker. Antes de copiar se comprobó que era idéntico a `main`
  (`56864d212f2e`); después `37a5cb600a7f` (el del PR). Respaldo: `~/quantfut/deployments/meta-extinfo-20261018/meta_capi.py.antes`.
  **Es un parche del contenedor, no de la imagen:** se pierde si el worker se recrea hasta que el PR #29 esté en `main` y la imagen se reconstruya.
- Causa: Meta responde 400 (subcódigo 2804043) si `extinfo` no lleva versión del SO válida. Una cuenta sin dispositivo registrado
  habría fallado en su `Purchase`/`Subscribe`.
- **Incidente de la prueba (reconocido):** al validar se enviaron **2 eventos `Purchase` de prueba (4,99 USD, correo `prueba@quantfut.invalid`,
  `event_id` `test:var-1-*` y `test:var-2-*`) que Meta PROCESÓ en el dataset de producción**: el `test_event_code` TEST3656 solo desvía los
  eventos mientras la página «Probar eventos» tiene una sesión activa, y no la tenía. No se pueden borrar desde la API; no coinciden con ningún
  usuario real, así que su efecto en atribución es mínimo. Otros 2 intentos fallaron con 400 y no se registraron.
- Estado del worker tras recrearse (otra sesión, 21:58 UTC): sin `/app/meta.env`; usa el `.env` del servidor. Token verificado (dataset HTTP 200),
  `META_TEST_EVENT_CODE=TEST3656` presente.
- **Vuelta atrás:** `docker cp ~/quantfut/deployments/meta-extinfo-20261018/meta_capi.py.antes quantfut-worker-1:/app/src/qf/comercial/meta_capi.py`.
### 2026-10-18 · Token de Conversions API de Meta (usuario del sistema `quantfut-capi`) · SOLO configuración
- Sin código ni imágenes nuevas. En Business Manager («Simulador Ceneval») se creó el usuario del sistema `quantfut-capi`
  (rol Empleado) con acceso parcial al dataset QuantFut y un token con `ads_management`, sin caducidad.
- Token verificado contra Meta: consulta del dataset `2253839992227148` con HTTP 200. El token anterior del worker (205 caracteres)
  daba «Missing Permission» en esa misma consulta.
- Cambiado en dos sitios: `~/quantfut/.env` (copia previa `~/backups/env.pre-meta-token-20261018`) y `/app/meta.env` del contenedor
  worker (copia previa `/app/meta.env.bak-20261018`, dentro del contenedor; se pierde si el worker se recrea, igual que el propio `meta.env`).
  No se recreó ningún contenedor.
- Una pasada de `qf.comercial.meta_capi` tras el cambio: 0 enviados, 0 fallidos (cola vacía).
- **Pendiente:** `META_TEST_EVENT_CODE` sigue vacío, así que los primeros eventos reales irán al dataset de producción. Poner el código
  de «Probar eventos» antes de la primera compra de prueba si se quiere validar sin contar en producción.
- **Vuelta atrás:** en el worker, `cp /app/meta.env.bak-20261018 /app/meta.env`; en el servidor, restaurar `~/backups/env.pre-meta-token-20261018` sobre `.env`.
### 2026-10-18 22:10 UTC · Worker recreado desde `main` y registro público activado · worker
- Orden del titular. Imagen `quantfut-worker:candidato-d2d2735` (construida desde `main` tras los PR #25 y #27 con `git archive` en `~/quantfut/releases/worker-d2d2735`), `latest` = esa imagen. Antes de recrear: sin procesos en el worker.
- **Ensayo** (`scripts/ensayo_worker.py`, worker actual frente a candidata): 0 módulos con error, 25/25 entradas del cron importables, `verify` OK en 20 lotes, conjunto de entrenamiento idéntico (49.450 filas, 46.208 con cierre, huella `44093369780e2f31`). 8 de los 20 lotes no se regeneran desde la base (ya ocurría; ver 15-oct).
- Lo que traía el contenedor viejo como parche (hashchain, módulos de Meta, `sedes.py`, `era5_clima.py`, crontab cargado a mano) ya está en `main`/imagen o en `.env`: comprobado que las variables `META_*` de `/app/meta.env` coinciden con las del `.env` (`env_file`) y que el crontab cargado tiene 127 líneas, como el archivo montado. Archivos de la API distintos a `main` en el worker viejo: solo código que el worker no ejecuta.
- Compose del servidor (worker): `CHAIN_GIT_REMOTE=git@github.com:cerorar23/quantfut-registro.git`, `GIT_SSH_COMMAND` con la llave de despliegue y montaje de solo lectura de `/home/qf/.config/quantfut/registro` en `/run/secrets/registro`. Respaldo en `~/quantfut/deployments/worker-registro-20261018/`.
- Carpeta de la cadena (volumen `quantfut_chain`): `git init`, remoto, `git reset origin/main` (conserva los archivos), usuario local. `git push --dry-run` OK. **Los JSON de los 19 lotes ya terminados se apartaron a `historico_sin_publicar/`** (decisión conservadora: no se publica el histórico sin que el titular lo decida). Sus recibos sí subirán en el primer sellado; `verify` los cuenta como «solo con compromiso» y la cadena sigue OK. Para publicarlos: mover los JSON de vuelta a `/srv/quantfut/chain/`; el siguiente sellado los revela.
- **Prueba del compromiso (18-oct, ~22:40 UTC):** `_git_comprometer` ejecutado a mano en el worker publicó el commit `c34a04a` en `cerorar23/quantfut-registro` con `LEDGER.md` y los 20 recibos; ningún JSON de lote subió. Queda por ver la revelación.
- Primera prueba real: el sellado de las 08:00 UTC del 19-oct (commit de compromiso en el repositorio público) y, tras el último partido del 18-oct, la revelación de su JSON. Vigilarlo.
- Vuelta atrás: `cp ~/quantfut/deployments/worker-registro-20261018/docker-compose.before.yml ~/quantfut/docker-compose.yml && docker tag quantfut-worker:en-ejecucion-20261018 quantfut-worker:latest && docker compose up -d --no-deps --no-build --force-recreate worker`. Sin `CHAIN_GIT_REMOTE`, `seal()` no toca git.

### 2026-10-18 21:25 UTC · Worker alineado con el envío a Meta · worker (2 módulos + cron), sin reiniciar
- Orden del titular. Parche del contenedor con `docker cp` (como F2c y el comprometer-revelar): `comercial/meta_capi.py` y `comercial/meta_datos.py` (los mismos que corre la API = `main`).
  **Es un parche del contenedor, no de la imagen**: se pierde si el worker se recrea. La alineación del 1-nov, construida desde un `main` que ya los incluye, los traerá en la imagen.
- Las variables de Meta (`META_CAPI_ENABLED`, `META_DATASET_ID`, `META_CAPI_TOKEN`; sin código de prueba) viven en `/app/meta.env` dentro del contenedor (600), porque el entorno del worker se fijó al
  crearlo. Al recrearlo con el `.env` actual llegarán por `env_file` y el cron seguirá valiendo (lee el archivo solo si existe).
- Cron: línea `*/5` con `flock` (sustituye en `scripts/crontab` la de Meta que `main` ya traía, que no cargaba entorno). OJO para la próxima sesión: el contenedor veía una copia ANTIGUA del archivo
  montado (otra sesión lo reemplazó con `sed -i`, cambiando el inodo), así que `crontab /etc/cron.d/quantfut` dentro del contenedor recargaba lo viejo; el cron del worker se cargó con
  `docker compose exec -T worker crontab - < scripts/crontab` (127 líneas, idéntico al archivo del host). Comprobado: el worker ejecutó el envío por sí mismo a las 21:20 UTC (`enviados 0`, sin pendientes).
- Retirada la línea transitoria del cron del HOST (queda solo `firebase_operations.py daily`); copias en `releases/worker-meta-20261018/`.
- Vuelta atrás: `docker compose exec -T worker crontab - < ~/quantfut/releases/worker-meta-20261018/worker-crontab.before` y borrar `/app/meta.env`;
  si hiciera falta volver al envío por el host: `*/5 * * * * cd /home/qf/quantfut && /usr/bin/docker compose exec -T api python -m qf.comercial.meta_capi`.

### 2026-10-18 22:50 UTC · Sede de los partidos nuevos y clima ERA5 incremental · worker (2 archivos) + cron
- Hallazgo: 722 de los 729 partidos de octubre no tenían `stadium_id` (los partidos nuevos llegan de `fixtures` sin sede), así que no
  se les podía vincular altitud ni clima. Nuevo `ingest/sedes.py`: toma el estadio de la página de FotMob ya capturada, reutiliza
  uno existente por nombre o por cercanía (<330 m) y solo da de alta si no hay ninguno; procedencia en `matches_enriquecimiento`.
  Primera corrida: **449 partidos asignados, 2 estadios nuevos** (sin duplicar); quedan sin sede 273 próximos, que la reciben al
  llegar su captura de 24 h. Cron nuevo cada hora a :50.
- `ingest/era5_clima.py` corregido: antes, repetirlo reutilizaba el archivo guardado de cada celda y nunca habría pedido los
  partidos nuevos. Ahora es incremental (une los archivos de la celda y pide solo lo que no cubren, hasta hoy−7 días).
- Parche con `docker cp` de `sedes.py` (nuevo) y `era5_clima.py` (ya existía en el worker). Vuelta atrás: copiar los de `main`.
- **Trampa de despliegue encontrada:** el crontab del worker es un archivo montado (`./scripts/crontab`). Un `sed -i` en el
  servidor lo reemplaza por otro archivo y el contenedor sigue viendo el viejo: las líneas añadidas después no llegan. Se
  resolvió cargando el archivo del servidor con `crontab -` dentro del contenedor y comprobando que lo cargado es idéntico.
  Lección: añadir líneas con `>>` (no `sed -i`) o recargar siempre con `cat scripts/crontab | docker compose exec -T worker crontab -`.
  Respaldo previo: `~/backups/crontab_pre_sedes_20261018`.
- ERA5 incremental lanzado (294 celdas con partidos nuevos; 236 partidos aún sin dato de Copernicus por su retraso de ~7 días).

### 2026-10-18 · Relleno puntual del archivo de FotMob · worker (un archivo) · rama `relleno-fotmob`
- Orden del titular. `ingest/fotmob_captura.py` gana `--dias-atras` y `--maximo` (solo para relleno; los cron no cambian).
  Parche con `docker cp` de ese único archivo, que ya existía en el worker desde `main`; vuelta atrás: copiar el de `main`.
- Se ejecutó con `flock -w 900` (sin chocar con los cron): `referencias --dias-atras 20` (264 nuevas) y
  `posteriores --dias-atras 20 --maximo 400` (255 partidos guardados, 0 descartados, 0 bloqueos de FotMob).
- Resultado: ningún partido terminado desde el 3-oct queda sin su página. Totales: 20.766 partidos, 870.608 jugadores,
  48.198 bajas en `fotmob_*`. Sin gasto de créditos. Modelo, predicciones y picks sin cambios.

### 2026-10-18 21:00 UTC · Meta pasa a eventos REALES · solo configuración (sin código ni migración)
- Orden del titular: quitada `META_TEST_EVENT_CODE` del `.env` y recreada la API (misma imagen `quantfut-api-meta-web:db24a88`). Respaldo previo: `releases/meta-web-db24a88/env.antes-produccion-meta`.
- Desde ahora el cron del host envía a Meta eventos que SÍ cuentan para atribución y optimización: `CompleteRegistration`, `InitiateCheckout`, `Purchase`, `Subscribe` (y los de la app que ya se encolaban). El envío anterior (1 evento) fue de prueba.
- Verificado: API sana, contenedor sin el código de prueba, `META_CAPI_ENABLED=1`, `/app/v1/whop/config` con el Pixel.
- Vuelta atrás: añadir `META_TEST_EVENT_CODE=TEST24843` al `.env` y `docker compose up -d --no-deps --no-build api` (los eventos vuelven a ir solo a «Probar eventos»).

### 2026-10-18 20:45 UTC · Meta web: registro, EMQ con facturación, reembolsos, aviso de medición + envío de CAPI · API (rama `feat/meta-web-registro-reembolsos`, commit `db24a88`, PR #17)
- Orden del titular («resuelve lo que falta… prueba todo»). CI del PR en verde antes de desplegar. **Desplegado antes de fusionar a `main`**.
- Antes de sobrescribir, los 13 archivos que se cambian eran idénticos a `origin/main` en el contenedor `quantfut-api-google-whop:d56577d`. Sin migración nueva.
- **API:** imagen `quantfut-api-meta-web:db24a88` = la anterior + esos 13 archivos (118 rutas). Compose fijado en ella (copia previa: `releases/meta-web-db24a88/docker-compose.before.yml`; archivos
  originales en `antes/`). Worker, base, Caddy y redis sin tocar.
- **`.env`:** añadidos `META_DATASET_ID=2253839992227148`, `META_CAPI_TOKEN` (token de sistema generado SIN activar «Dataset Quality API», que Meta no deja desactivar),
  `META_TEST_EVENT_CODE=TEST24843` y `META_CAPI_ENABLED=1`. Respaldos: `releases/google-whop-d56577d/env.antes-meta` y `releases/meta-web-db24a88/env.antes-despliegue`.
  **Mientras exista `META_TEST_EVENT_CODE` los eventos van SOLO a «Probar eventos»: no cuentan para anuncios.**
- **Envío:** el worker aún no lleva `qf.comercial.meta_capi`, así que el cron del HOST (usuario `qf`) ejecuta `docker compose exec -T api python -m qf.comercial.meta_capi` cada 5 min
  (log `~/.local/share/quantfut/meta_capi.log`; copia previa en `crontab.before`). Quitar esa línea cuando el worker se alinee (no hay doble envío: `SKIP LOCKED` y estado por evento).
- **Whop:** el webhook pasó a 5 eventos (+`refund.created`, `refund.updated`).
- **Verificado en producción:** (1) registro web real (cuenta desechable id 7) → `CompleteRegistration` `website` con `fbp` de la cookie y URL de origen → enviado por la tubería real →
  visible en «Probar eventos» como *Procesado · Servidor*; (2) eventos sintéticos Purchase/Subscribe/InitiateCheckout con 13 claves de cliente (correo, nombre, apellido, ciudad, estado,
  código postal, teléfono, país, ID externo, fbp, fbc, IP, user agent); (3) Pixel `2253839992227148` carga y se registra en el navegador integrado; «Rechazar» guarda `qf_ads_consent=no` y
  no carga nada tras recargar; (4) «Prueba» de Whop → `membership.updated` firmado por Whop → 200 `ignorado` (valida la firma real con nuestro secreto).
- **Cuenta de prueba:** `prueba-meta-1792356322@ejemplo.com` (account_id 7) quedó creada en producción por la prueba; no tiene suscripción.
- **Para pasar a producción real de Meta:** quitar `META_TEST_EVENT_CODE` del `.env` y `docker compose up -d --no-deps --no-build api`. Comprobar antes en Events Manager que EMQ de «Purchase» sube.
- **Vuelta atrás:** `cp -p ~/quantfut/releases/meta-web-db24a88/docker-compose.before.yml ~/quantfut/docker-compose.yml && docker compose up -d --no-deps --no-build api` y `crontab ~/quantfut/releases/meta-web-db24a88/crontab.before`.
- **Nota:** el Chrome del titular tiene un bloqueador de rastreadores que devuelve 503 a `fbevents.js`; allí el Pixel no se ve. Los visitantes sin bloqueador sí lo cargan.

### 2026-10-18 20:20 UTC · Acceso con Google en la web + cobro con Whop + Meta web · API + `db/083` (rama `feat/google-whop-meta`, commit `d56577d`, PR #16)
- Orden del titular («despliega al vps»). CI del PR en verde (2/2) antes de desplegar. **Desplegado antes de fusionar a `main`**: al fusionar el PR, `main` queda igual que la API.
- Antes de sobrescribir se comprobó que los 10 archivos existentes que se cambian eran idénticos a `origin/main` en el contenedor `quantfut-api-cybercore:2d8cfef` (los otros 6 son nuevos).
- **Base de datos:** `db/083_whop_checkout.sql` aplicada en una transacción (solo añade: `plans.whop_plan_id`, `whop_checkouts`, `whop_webhooks`, `whop_payments`, `meta_events.action_source/web_context`). `UPDATE plans SET whop_plan_id` de los 3 planes.
  Respaldo previo de `plans`: `~/quantfut/releases/google-whop-d56577d/plans.antes.sql`.
- **API:** imagen `quantfut-api-google-whop:d56577d` = la `2d8cfef` + solo esos 16 archivos (ensayo: 118 rutas, las 8 nuevas presentes). Compose fijado en la nueva (copia previa: `releases/google-whop-d56577d/docker-compose.before.yml`).
  Worker, base, Caddy y redis sin tocar.
- **`.env`:** añadidas `FIREBASE_WEB_API_KEY/APP_ID/AUTH_DOMAIN`; ya estaban `WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`, `META_PIXEL_ID` (entrada de arriba). Respaldos `env.antes-despliegue` y `env.before` en la misma carpeta. `META_CAPI_ENABLED` NO está activo.
- **Verificado en el dominio real:** `/health` 200; `/app/v1/firebase/web-config` con `projectId`; `/app/v1/whop/config` `{"enabled":true,"pixelId":…}`; `/google-auth.js`, `/meta-pixel.js`, `/whop-checkout.js` 200;
  `web-session` sin cuerpo 422; webhook con firma mala 400 y con firma buena 200 (`ignorado`, fila de idempotencia `despliegue.ping`); logs sin errores.
  Desde el VPS, la clave de Whop crea una `checkout_configuration` (200; dos de prueba sin cobro) y la página de pago muestra «Total a pagar hoy 14,99 US$».
- **Falta:** probar el botón de Google y un cobro real con un usuario; alinear el worker (cron de CAPI con `web_context`) ANTES de activar `META_CAPI_ENABLED`; reembolsos (`refund.created` no suscrito).
- **Vuelta atrás:** `cp -p ~/quantfut/releases/google-whop-d56577d/docker-compose.before.yml ~/quantfut/docker-compose.yml && docker compose up -d --no-deps --no-build api`.
  La migración es aditiva: no hace falta deshacerla (el código anterior no usa las tablas ni columnas nuevas).

### 2026-10-18 · Whop: claves en el `.env` del servidor · SOLO configuración, sin código nuevo ni reinicios
- Por orden del titular («usa el backend para guardar claves»): añadidas `WHOP_API_KEY` y `WHOP_WEBHOOK_SECRET` al final de `~/quantfut/.env` (permisos 600).
  Son inertes: la API actual no las lee; las usará la imagen del plan `docs/despliegue_google_web_20261018.md`.
- Respaldo previo: `~/quantfut/releases/whop-env-20261018/env.before`. Vuelta atrás: `cp -p` ese archivo sobre `.env` (la clave solo se muestra una vez en Whop: habría que regenerarla).
- También `META_PIXEL_ID=2253839992227148` (Pixel de Meta, dato público), por orden del titular.
- En Whop (cuenta `biz_VHqtO4zEcnvvOK`): producto QuantFut con 3 planes renovables, clave «QuantFut Backend» (permisos: leer/crear configuraciones de checkout; solo desde 31.220.72.30)
  y webhook `https://pronosticosdeportivos.pro/webhooks/whop` (`payment.succeeded`, `membership.updated`, `membership.deactivated`). Hasta desplegar, ese endpoint no existe
  y las entregas fallarán y se reintentarán; no hay cobros posibles antes de desplegar (la web no muestra el pago).

### 2026-10-18 18:55 UTC · Captura recurrente de FotMob y clima histórico ERA5 · base de datos + worker (3 módulos) + cron
- Orden del titular: autorizó la captura diaria de FotMob y entregó su token personal de Copernicus CDS. Parche del
  contenedor worker con `docker cp`: `ingest/fotmob_captura.py` y `ingest/era5_clima.py` (nuevos) y `ingest/fotmob_a_motor.py`
  (refactor con la función `insertar`, comportamiento igual). Se pierden si el worker se recrea: construir desde `main`.
- **Base de datos** (solo se añade): `db/081` `fotmob_equipo` (495), `fotmob_referencia` (20.331 del archivo + 503 de liga),
  `fotmob_original`, `fotmob_previo`, `fotmob_jugador_previo`, `fotmob_baja_previa`, `fotmob_captura_log`; `db/082`
  `clima_era5_partido`. Vuelta atrás: `DROP` de cada una; nada existente las lee.
- **Cron** (`~/quantfut/scripts/crontab`, recargado con `crontab /etc/cron.d/quantfut`, sin reiniciar): `referencias` 05:50 UTC,
  `previos` cada 15 min, `posteriores` a :35, los tres con `flock -n /tmp/fotmob_captura.lock`. Respaldo previo:
  `~/backups/crontab_pre_fotmob_20261018`. Vuelta atrás: restaurar ese archivo y recargar.
- **Token de CDS** en `~/quantfut/.env` como `CDS_API_TOKEN` (permisos 600; el worker en marcha no lo ve, se pasa con
  `docker compose exec -e`). Respaldo previo del `.env` en `~/backups/env_pre_cds_20261018` (600). El token se compartió por
  chat: conviene regenerarlo en la cuenta de Copernicus cuando termine la descarga.
- **Descarga ERA5 en segundo plano** (423 celdas, ~5 h, 4 en paralelo): `python -m qf.ingest.era5_clima` dentro del worker, con
  registro en `/var/log/era5_clima.log`; las respuestas quedan en `/srv/quantfut/artifacts/era5`. Reanudable.
- Salvaguardas de FotMob: 0,8 s entre peticiones, un bloqueo HTTP 401/403/429 detiene todo 12 h con alerta. Primeras corridas:
  23 referencias, 8 capturas previas y 60 posteriores sin errores. API-Football y The Odds API: sin gasto.
- Verificado: modelo activo sin cambios, predicciones y picks sin cambios (los módulos no los leen ni escriben).
- Detalle: `docs/datos_al_motor_20261018.md` §6.

### 2026-10-18 17:55 UTC · Orden de identidades y datos de FotMob al motor · base de datos + worker (cinco módulos nuevos) + cron
- Orden del titular («hazlo ya», los cuatro grupos de datos). Sin imagen nueva: **parche del contenedor worker** con
  `docker cp` de cinco archivos NUEVOS (no sobrescribe ninguno): `ingest/fotmob_a_motor.py`, `estadios_altitud.py`,
  `arbitros_equivalencia.py`, `calendario_equipos.py`, `puentes_jugadores.py`. Se pierden si el worker se recrea: la
  alineación del 1-nov debe construirse desde un `main` que ya los incluya. Hashes iguales a la rama `ordenar-identidades`.
- **Datos existentes que cambian** (lo que verá el reentrenamiento del 1-nov):
  - `db/073`: 33 filas de `matches` (Champions/Europa League, 2014 → 2024-12-11) pasan de Arsenal de Sarandí (28402) a
    Arsenal (3). Auditado en `correcciones_identidad`. Respaldo: `~/backups/arsenal_sarandi_matches_pre073_20261018.csv.gz`.
    Vuelta atrás: las dos sentencias `UPDATE` comentadas al final de `db/073_corregir_arsenal_sarandi.sql`.
  - 4 alias nuevos de `odds_api` (Bayern München, Internazionale Milano, LOSC Lille, Young Boys), auditados (migración 074).
    Vuelta atrás: `DELETE` por (alias, fuente).
  - **45 cierres de Pinnacle** (135 cuotas, `source='the_odds_api_hist'`) en `odds_snapshots`. **Irreversible:** la tabla no
    admite DELETE. Cada partido tiene exactamente 3 filas; repetir la carga inserta 0.
- **Tablas y vistas nuevas** (solo se añaden; nada existente las lee): `db/075` `fotmob_partido` (20.331),
  `fotmob_jugador_partido` (852.126), `fotmob_baja` (47.140), `v_fotmob_jugador_partido`; `db/076` `estadio_altitud` (728);
  `db/077` `arbitro_equivalencia` (54) y `v_arbitro_unificado`; `db/078` `calendario_equipo` (60.979) y su log;
  `db/079` `puente_jugador` (7.834); `db/080` `v_descanso_equipo`. Vuelta atrás: `DROP` de cada una.
- **Cron:** una línea nueva en `~/quantfut/scripts/crontab` del servidor (05:40 UTC, calendario de la temporada en curso,
  ~313 llamadas de las 7.500 de API-Football), recargada con `crontab /etc/cron.d/quantfut`; sin reiniciar el worker.
  Respaldo previo: `~/backups/crontab_pre_calendario_20261018`. Vuelta atrás: restaurar ese archivo y recargar.
- Créditos y cuotas: The Odds API, 0 (snapshots ya descargados); API-Football, 1.260 llamadas (quedaba 5.238 al empezar).
- Verificado al terminar: API local 200; modelo activo `2026.09.27-010508`; 378 predicciones, 0 picks, 20 lotes de la cadena
  verificados (`verify` correcto); contenedores sin reinicios. Consultas lentas propias canceladas (la medición de jugadores
  se reescribió con funciones de ventana; las anteriores seguían activas en el servidor tras cancelarse el cliente).
- Detalle y cifras: `docs/datos_al_motor_20261018.md`, `docs/ordenar_identidades_20261018.md`.

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
