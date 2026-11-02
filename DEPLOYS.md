# Registro de despliegues — QuantFut

Una sola regla de fondo: **lo que corre en producción es lo que dice `main`**. Todo cambio en el servidor se
anota aquí en el mismo momento, y solo despliega una sesión a la vez.

## Repositorio
Privado en GitHub: `cerorar23/quantfut` (rama `main`). Cada push ejecuta el arnés en GitHub Actions
(`.github/workflows/pruebas.yml`, con Postgres 16 real). **GitHub no permite proteger ramas en repos privados del
plan gratuito**, así que la regla es por costumbre: rama + pull request + arnés verde antes de fusionar a `main`.
El servidor **no** despliega con `git pull` (decisión 2026-10-28): `scripts/deploy.sh construir|ensayo|desplegar` envía `git archive` de `origin/main` por SSH, sin credenciales de GitHub en el servidor.

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

### 2026-11-02 01:50 UTC · db/101 y carga de las cuotas históricas de BetsAPI y API-Football — base de datos, rama `futbol/cargar-cuotas-vps`
- Autorizado por el titular en el chat. Solo base de datos: ningún contenedor ni imagen cambia; nada del pipeline predecir → sellar → publicar lee la tabla nueva.
- db/101 crea `futbol.cuota_historica` (inmutable por `deny_mutation`, clave única que hace la carga idempotente). **No se carga en `odds_snapshots`**: esa tabla alimenta CLV, API, `daily.py` y entrenamiento y varias lecturas no filtran por fuente; cuotas retroactivas habrían cambiado resultados ya medidos (misma razón que `ingest/odds_history.py`).
- Carga con `scripts/rediseno_futbol/cargar_cuota_historica.sh` en UNA transacción (ensayada antes en un esquema aislado de la base local, dos vueltas: la segunda inserta 0): **1.033.331 filas**, 10.759 partidos: BetsAPI (bet365, retroactiva) 556.525 filas de 10.036 partidos (apertura, t60, cierre y lectura del minuto 65-70 de córners, 8 mercados incluidos los de la 1.ª parte) y API-Football (10 casas, recepción real) 476.806 filas de 723 partidos (apertura, t60, último).
- Comprobado después: `odds_snapshots` intacta (3.338.606 filas antes y después), trigger activo (un `DELETE` se rechaza), línea propia de cada selección (local −0,5 con visitante +0,5). Tabla 351 MB; base de 3.443 a 3.795 MB; disco con 42 GB libres.
- Los originales siguen intactos: `~/betsapi/data/football` (1,1 GB, cada cambio de precio) y `~/backups/retiro_af_odds_snapshots_20261101.sql.gz`.
- Vuelta atrás: `DROP TABLE futbol.cuota_historica;` (la tabla es nueva; nadie la lee).

### 2026-11-01 17:00 UTC · db/097, 098 y 099 y recarga de las 10 ligas — base de datos y scripts, rama `futbol/dato-unico`
- Respaldo previo: `~/backups/futbol_pre_097_20261101.sql.gz` (133 MB, `gzip -t` correcto; copia local en
  `Documents/respaldos_quantfut_20261101`). Ensayo con `BEGIN … ROLLBACK` sobre los datos reales antes de aplicar.
- db/097 (córners, tiros, xG y tarjetas por mitad; árbitro), db/098 (`regla_sancion`, `derbi`, `cargar_derbis()`) y
  db/099 (`baja_previa`, `once_previo`, `alineacion_previa`, `cargar_previo()`, `pit = 'previo'`). Copias en
  `~/futbol_base_unica/dato/`; `src/futbol_sofascore.py` y `futbol_diario.sh` actualizados (hashes iguales a la rama).
- Recarga `--forzar` de las 10 ligas con `~/futbol_base_unica/recarga_097.sh` (16:51–17:04 UTC): 42.520 filas de equipo
  con córners por mitad, 10.625 de 10.629 partidos con árbitro. `cargar_previo()`: ≈105.000 filas, todas `previo`;
  `cargar_derbis()`: 26 por ciudad + 26 manuales. Tabla: 3,12 M filas, 1.381 MB; base 5.109 MB.
- Vuelta atrás: `DROP SCHEMA futbol CASCADE` y restaurar el respaldo (borraría lo cargado después).
- El cron diario (08:15) ya llama a `cargar_previo` y `cargar_derbis`.
- **Retiro R1–R3 ejecutado (17:30 UTC, autorizado por el titular en el chat)**. Respaldos antes: las cinco tablas en
  `~/backups/retiro_*_20261101.sql.gz` con manifiesto de recuentos y sha256, y copia local verificada en
  `Documents/respaldos_quantfut_20261101`.
  - R1/R2: `DELETE` de lo ya cargado en `futbol.dato` y de más de 14 días: `historical_football_player_stats`
    850.899 filas (quedan 22.999), `historical_football_lineups` 40.662 (quedan 1.098) e
    `historical_football_absences` 47.140 (quedan 1.529); después `VACUUM FULL`. Se regeneran desde el original
    `historical_football_matches.raw_payload_gzip`. La vista `v_fotmob_jugador_partido` y `cargar_fotmob` siguen
    funcionando (prueba en `tests/test_futbol_sofascore.py`).
  - R3 (db/100): `DROP TABLE af_odds_snapshots` (1.537.120 filas) y `sofascore_detalles` (225), sin CASCADE.
  - Base: de 5.109 MB a 3.418 MB.
  - Vuelta atrás: restaurar el volcado de la tabla correspondiente con `gunzip -c … | psql`.

### 2026-11-01 15:35 UTC · `cargar_fotmob` conserva lo que SofaScore completó; la pasada diaria ya no recarga a la fuerza — base de datos y script
- Causa de fondo: cada carga de FotMob borraba y reescribía sus filas, y con ellas lo que SofaScore había completado (xG del jugador, pases clave, penaltis…), por eso la pasada diaria recargaba SofaScore a la fuerza. Ahora `futbol.cargar_fotmob` hace UPSERT: prepara las filas en una tabla temporal, borra solo las que FotMob ya no informa y actualiza el resto conservando las columnas que FotMob no trae y `fuente_extra`. Las entradas del motor `nota`, `valor_mercado` y `posicion_id` quedan exactamente como las da FotMob (si FotMob las pierde, quedan vacías; no se rellenan con otra fuente). Si FotMob toma un partido que tenía SofaScore, conserva lo de SofaScore como complemento (`fuente_extra`). Bajas: igual, y conservan `motivo_codigo` y `descripcion`. Función reaplicada en producción (db/094 actualizada).
- Comprobado en producción: antes y después de recargar FotMob (3 días) las filas completadas por SofaScore siguen en 345.460, el xG de jugador en 109.427 y las bajas completadas en 24.702; las filas de FotMob subieron de 886.628 a 886.668 (partidos nuevos).
- `scripts/futbol_diario.sh`: sin `--forzar` y con ventana de 4 días para SofaScore (antes 7 días forzados). Probado con el entorno mínimo de cron: 64 s. Sin cambios en el cron.
- Pruebas: 25 con Postgres; dos nuevas: conserva lo completado y `nota` siempre de FotMob.

### 2026-11-01 03:35 UTC · Argentina sube al VPS y entra en `futbol.dato` — archivos y base de datos
- Revisión del historial de hoy: las 9 ligas ya subidas estaban completas y al día en el servidor (0 faltantes); solo faltaba Argentina (torneo 155): 612 partidos en el PC que no habían llegado al VPS. Subidos con `scripts/subir_archivo_sofascore.py` (6 conexiones, 617 partidos, 22 MB): servidor 10.707 partidos, 0 dañados, 44 GB libres; catálogo del scraper reindexado (`catalog reconcile` y `verify` limpios).
- `ar.primera` no estaba en la lista de ligas del cargador ni de la pasada diaria: añadida (`scripts/futbol_diario.sh`). Primera carga: 1.138 partidos emparejados con `matches` (plan sin problemas); 597 rechazados: 592 sin descargar en el PC (2023 completo y 214 de 2024; la nota del PC dice que quedó bloqueado por 403 y presupuesto), 4 provisionales y 1 sin alineación.
- Donde FotMob ya cubría el partido (3.780 tipos), SofaScore completó 234.088 columnas vacías sin pisarlo; aportó 230 filas de jugador, 280 de baja y todo lo que FotMob no trae (tiros 27.826, incidencias 24.062, momentum 104.012, posiciones 35.282, equipo por periodo 6.828). `futbol.dato`: 3.013.027 filas, 1.183 MB, 0 repetidos, 0 ids sin ficha.
- Premier y LaLiga siguen sin 2023/24 (no descargado en el PC).

### 2026-11-01 03:00 UTC · `futbol.dato` cubre el partido completo del scraper de SofaScore (db/096) — base de datos, rama `futbol/dato-unico`
- Medido con el partido Fulham-Bournemouth (12 bloques) que la tabla guardaba lo esencial: 34 de 82 estadísticas de jugador, 28 de 46 de equipo y solo el periodo completo, sin momentum ni posiciones medias. `db/096_futbol_dato_ampliado.sql` añade 100 columnas (181 en total) y los tipos `momentum` y `posicion`; el cargador lee ahora las 82 estadísticas de jugador, las 46 de equipo por periodo (evento 0/1/2), los campos de tiro (bloqueo, tipo de gol, portero), de incidencia (lesión, descuento, VAR, red de pases del gol), la asistencia, el momentum y las posiciones medias. Respaldo: `~/backups/futbol_pre_096_20261101.sql.gz` (74 MB).
- Donde manda otra fuente (FotMob), SofaScore solo COMPLETA las columnas vacías y lo anota en `fuente_extra`; nunca `nota`, `valor_mercado` ni `posicion_id`.
- Recarga forzada de los 9.489 partidos (14 min, con `nice`): 2.813.517 filas, 0 repetidos, 0 tipos con dos fuentes, 0 ids sin ficha; 338.696 filas de FotMob completadas por SofaScore; equipo 56.934 (3 periodos), momentum 868.701, posicion 294.411, 20.314 incidencias con red de pases. `futbol.dato` 1.147 MB; base 4,82 GB; 42 GB libres.
- Corregido en `cargar_fotmob`: borraba las bajas de otra fuente aunque FotMob no informara ninguna en el partido; ahora solo sustituye cuando FotMob sí informa. Función reaplicada en producción (db/094 actualizada).
- La pasada diaria corre ahora identidad -> FotMob -> SofaScore forzado de 14 días -> clima/estadio, para que SofaScore vuelva a completar lo que FotMob reescribe.
- Vuelta atrás: restaurar `futbol_pre_096_20261101.sql.gz` (las columnas nuevas son aditivas y pueden quedarse).

### 2026-11-01 02:20 UTC · Tabla única de fútbol `futbol.dato` (db/094 y db/095) — base de datos, rama `futbol/dato-unico`
- Orden del titular: todo lo que se capture de fútbol se junta en UNA tabla con nombres de campo unificados y solo ella alimenta al motor. `db/094_futbol_dato_unico.sql` crea `futbol.dato` (10 tipos: jugador, equipo, baja, alineacion, entrenador, contexto, tiro, incidencia, clima, estadio; clave `(match_id, tipo, side, jugador_id, evento)`), la identidad única de jugador y los adaptadores SQL `cargar_fotmob`, `cargar_clima` y `cargar_estadio`. `db/095_futbol_dato_absorbe_tablas.sql` pasó a la tabla única las nueve tablas por tipo de las migraciones 085-090 de la rama anterior (aplicadas el 1-nov sin número oficial) y las retiró; comprueba fila por fila que cuadran y, si no, se deshace. No toca `matches`, `predictions`, `picks`, `odds_snapshots` ni sus triggers.
- Antes: respaldo `~/backups/futbol_pre_094_20261101.sql.gz` (60 MB) y ensayo completo con `ROLLBACK` sobre los datos reales (75 s). Aplicadas a las 02:20 UTC, sin tocar el worker ni la API; el reentrenamiento de las 03:00 UTC no se solapó.
- Resultado: 1.604.058 filas en 22.504 partidos (jugador 942.899, incidencia 198.611, tiro 247.935, baja 54.432, equipo 18.978, estadio 21.039, clima 20.983, alineación 44.852, entrenador 44.840, contexto 9.489); 591 MB; base 4,26 GB; 43 GB libres. 0 repetidos, 0 tipos con dos fuentes en un partido, 0 ids de jugador sin ficha.
- Identidad: 10.739 jugadores de SofaScore registrados, 9.604 ids de FotMob enlazados por evidencia, 6.676 de API-Football por el puente histórico y 130 ids sin ficha (tiradores, ausentes) registrados.
- Pasada diaria `scripts/futbol_diario.sh` (probada en el VPS con el entorno mínimo de cron, 60 s, con `nice`; el DSN no aparece en `ps`). **Cron instalado el 1-nov con autorización del titular:** `15 8 * * *` (hora del servidor) con `flock`, registro en `~/futbol_base_unica/work/diario.log`; copia previa del crontab en `~/crontab_antes_futbol_diario_20261101.txt` (vuelta atrás: `crontab ~/crontab_antes_futbol_diario_20261101.txt`). Cuotas (`odds_snapshots`) y `matches` quedan fuera a propósito (inmutables / registro de partidos).
- Interruptor `FUTBOL_LECTURA=canonica` (apagado por defecto) para que el motor lea `futbol.dato`; no se activa sin comparar antes el modelo.
- Vuelta atrás: `DROP SCHEMA futbol CASCADE` y restaurar `futbol_pre_094_20261101.sql.gz` (deja las nueve tablas por tipo como estaban).

### 2026-11-01 01:41 UTC · Retiro de las fuentes antiguas y descanso desde `matches` · worker `quantfut-worker:bd58d4f` (PR #226) y db/093
- Qué: fuera el código de API-Football, PitchAPI, BetsAPI, Apify, worldfootballR y el cargador de football-data (datos, tablas y migraciones se conservan); `record_health` vive en `ingest/salud.py`; bajas y once con ids de SofaScore en `ingest/sofascore_carga.py`; cotejo de football-data.org en `ingest/cotejo.py`; `v_descanso_equipo` usa `calendario_equipo` hasta su última carga (22-oct) y `matches` después.
- Punto de partida: el worker en ejecución (`fdorg-e808239`) difería de `main` `9adc2a5` solo en copias viejas de `api/*`, `config.py` y `propline_shared.py` (diferencias aditivas) y `sofascore_apify.py`. La API (`quantfut-api-cuotas:5b6f545`) NO se despliega: su imagen es un parche de varias ramas y construirla desde `main` podría revertir la web; lo que cambia en ella es código muerto.
- Migración `db/093_descanso_con_matches.sql` (vista `v_descanso_equipo` y nueva `v_partidos_jugados_equipo`), ensayada antes dentro de una transacción con ROLLBACK sobre la base real y aplicada después. Medido: el histórico (18.720 filas) sale idéntico; en las próximas 72 h el descanso medio pasa de 14,66 a 6,52 días y los lados con dato de 141 a 205 de 218; una consulta tipo `contexto.py` tarda 318 ms.
- Crontab: instalado el de `main` (56 líneas activas, LF), que añade el job de SportsAPIPro que ya corría en el servidor y quita las líneas «RETIRADO». Compose del servidor: fuera el montaje `/home/qf/sofascore-apify/data`.
- Claves retiradas antes del despliegue (sin tocar contenedores): `API_FOOTBALL_*` del `.env` y sus copias, tokens de BetsAPI y Apify, y la clave cifrada de PitchAPI vaciada en `pitchapi_settings`. `~/betsapi/.env.propline` se conserva: el recolector de PropLine lee su clave de ahí.
- Ensayo en contenedor aparte sin red: 0 módulos con error y los 24 módulos nombrados en el crontab existen en la imagen. Tras recrear: 12 módulos clave importan dentro del worker, `odds_provider` efectivo `propline` y `fotmob_alineaciones` escribe en `ingest_health` con el worker nuevo (01:42:02).
- Respaldos en `~/quantfut/releases/`: `compose-antes-retiro-fuentes-20261101-013754.yml` (antes de quitar el montaje), `compose-antes-20261031-194046.yml` (antes del cambio de etiqueta, hora local del servidor), `crontab-antes-20261101-013754.txt` y `vista-v_descanso_equipo-antes-20261101-013754.sql`.
- Vuelta atrás: restaurar `compose-antes-retiro-fuentes-20261101-013754.yml` como `docker-compose.yml` y `crontab-antes-20261101-013754.txt` como `scripts/crontab`, recrear solo el worker (`docker compose up -d --no-deps --no-build --force-recreate worker`) y, si hace falta, reaplicar la vista anterior con `psql -f releases/vista-v_descanso_equipo-antes-20261101-013754.sql` (o `db/080_descanso_equipo.sql`). La imagen anterior sigue en el servidor: `quantfut-worker:fdorg-e808239`.
- Comprobado: `API_FOOTBALL_*` ya no está en el entorno del worker recreado ni en su `/etc/environment`.
- Pendiente: el pie de la web (`frontend/app.js`) se corrigió en el repo pero la web en vivo sale de otra rama; la fuente del descanso para copas domésticas y selecciones sigue sin definir.

### 2026-11-01 02:10 UTC · Respaldo football-data.org (calendario y resultados) · worker (imagen derivada) + db/092, commit `e808239` (rama `futbol/fdorg-respaldo`, aún sin fusionar a `main`)
- Orden del titular («sí, despliega»). Solo avisa: no escribe en `matches` ni crea equipos. Diseño: `docs/superpowers/specs/2026-11-01-football-data-org-respaldo-design.md`.
- Imagen `quantfut-worker:fdorg-e808239` = `quantfut-worker:sportsapipro-fix-fc0fda7` + `src/qf/ingest/fdorg_respaldo.py` (hash comparado con el commit). Compose fijado a esa imagen; la API no se tocó. Worker recreado (unos segundos, sin trabajos en curso; los crons de entrenamiento están retirados).
- `db/092` (aplicada el 1-nov con el nombre `089_fdorg_respaldo.sql`; renombrada al fusionar con `main`, que ya tenía otra 089) aplicada (aditiva: `fdorg_*` y `leagues.fdorg_code` en 10 ligas). `FOOTBALL_DATA_ORG_KEY` añadida al `.env` del servidor (600). Cron `10 1,13 * * *` añadido en sitio a `scripts/crontab` (el archivo es un montaje; mismo inodo). `fdorg_settings.enabled = true`.
- Siembra única de equivalencias con la temporada completa de las 10 competiciones (10 peticiones, originales guardados): 173 clubes emparejados por fecha y marcador. Primera pasada real: 253 partidos, **0 diferencias** frente a 103 terminados de los últimos 7 días; `ingest_health` en verde.
- Pendiente: fusionar la rama a `main` (el servidor ya corre este código); términos del plan gratuito sin publicar (su plan muestra marcadores y horarios con retraso, posible falsa alarma de `kickoff_shift`); el módulo importa `compare`/`promote` de `pitchapi_respaldo` (cron retirado el 25-oct, archivo aún en la imagen).
- **Vuelta atrás:** `UPDATE fdorg_settings SET enabled = false` (lo apaga sin reiniciar) o restaurar `releases/fdorg-20261101/backup/docker-compose.antes.yml` y `crontab.antes` y recrear el worker. Las tablas nuevas son aditivas y pueden quedarse.
### 2026-10-31 15:44 UTC · Cuotas de referencia de NBA y tenis · API `quantfut-api-cuotas:5b6f545` (PR #220 y #221)
- Imagen basada en la API en ejecución `quantfut-api-destacado-tarjeta:3bb42c1`, sustituyendo solo `api/web.py`, `config.py`, `ingest/propline_shared.py` y añadiendo `api/cuotas_{nba,tenis,web}.py`, `ingest/cuotas_{referencia,respaldo}.py`. NO se tocó `frontend/`: el de `main` difiere del de producción en 5 archivos (`app.js`, `index.html`, `ergonomic-views.js`, `real-views.js`, `app-order.test.mjs`) y no se despliega aquí. Las diferencias de `web.py`/`config.py`/`propline_shared.py` frente a producción eran solo añadidos de estos PR. Ensayo: 0 módulos con error, 138 rutas (+2).
- Compose del servidor: montajes de solo lectura `/home/qf/nba-isolated/live13/cohorts` -> `/srv/quantfut/nba_cohorts` y `/home/qf/quantfut-tenis/data/intake_v1` -> `/srv/quantfut/tenis_sellos`; variables `NBA_COHORTS_DIR`, `TENNIS_SEALED_DIR`, `CUOTAS_RESPALDO_CACHE=/srv/quantfut/artifacts/cuotas_respaldo.json`. El archivo PropLine ya estaba en el volumen `quantfut_artifacts`. `ODDS_API_RESPALDO_KEY` está en `~/quantfut/.env` (copia `.env.bak_respaldo_20261031`).
- Medido tras desplegar: SQLite en solo lectura sobre el archivo funciona. NBA: estado `ok`, 25 eventos, 7.252 lados con precio, 970 KB sin comprimir / ~60 KB gzip, primer cálculo en frío ~49 s (la primera petición tras un reinicio devuelve `unavailable` a los 20 s; el cálculo termina en segundo plano y las siguientes ya sirven). Tenis: `partial`, 72 eventos, 1.368 mercados con precio. Respaldo de The Odds API: 0 filas (cron apagado, no se ha ejecutado). Salud API 200; dominio público sirve ambos endpoints.
- Vuelta atrás: restaurar `~/quantfut/releases/compose-antes-20261031-154355.yml` como `~/quantfut/docker-compose.yml` y recrear solo la API (`docker compose up -d --no-deps --no-build --force-recreate api`).
- Pendiente: el cron del respaldo (`scripts/crontab`) no está instalado en el servidor y `CUOTAS_RESPALDO_AUTO` está en 0; la app Flutter con cuotas llega con la próxima versión publicada; términos de PropLine (titular).

### PROPUESTA (sin desplegar) · Respaldo de cuotas NBA/tenis con The Odds API histórico · comando por lotes · rama `cuotas-nba-tenis`
- Qué: `python -m qf.ingest.cuotas_respaldo` escribe `CUOTAS_RESPALDO_CACHE` (JSON, escritura atómica) y el overlay de `/web/deportes/{nba,tenis}/cuotas` solo la lee; los lados sin cuota de PropLine salen con `src: "the-odds-api"`.
- Variables: `ODDS_API_RESPALDO_KEY` (ya en el `.env` del servidor) y `CUOTAS_RESPALDO_CACHE` (ruta en un volumen que la API monte en solo lectura). Sin ellas no hace nada.
- Uso: seco por defecto (plan y coste); `--ejecutar --max-creditos 300` pide; para si el saldo quedaría bajo 500. A mano: tras cada sellado. Automático (apagado por defecto): `python -m qf.ingest.cuotas_respaldo --auto`, en `scripts/crontab` cada 10 min con `flock`; solo actúa con `CUOTAS_RESPALDO_AUTO=1` en el `.env` del servidor, y los únicos peticionables son los huecos de pronósticos ya sellados que PropLine dejó sin cuota (sin huecos: 0 peticiones, ni la lectura del saldo). Topes: `CUOTAS_RESPALDO_AUTO_MAX` (100 por corrida) y `CUOTAS_RESPALDO_DIARIO` (300/día, persistido en `<CACHE>.gasto.json`), más el suelo de 500; alerta de Telegram solo si el saldo cae bajo el suelo. Un fallo se registra y se ignora. El sellado de NBA y tenis vive en contenedores propios, así que el respaldo corre fuera de su camino crítico, nunca dentro. Vuelta atrás: `CUOTAS_RESPALDO_AUTO=0`. Saldo medido el 31-oct: 2.855 créditos hasta el 23-nov.
- Vuelta atrás: borrar el JSON o vaciar `CUOTAS_RESPALDO_CACHE`; el overlay vuelve a PropLine puro.

### 2026-10-29 02:33 UTC · Retiro de leyendas de tenis · API `quantfut-api-sin-leyendas-tenis:7c1892f` (PR #218)
- Se retiraron las cuatro leyendas señaladas de la ventana de tenis. CI: 8 comprobaciones aprobadas; 94 pruebas del frontend aprobadas. Ensayo de imagen: módulos importables y 136 rutas.
- Imagen basada en la API en ejecución `quantfut-api-sin-leyendas:36de48b`, sustituyendo solo `sports-window.js`, `app.js` e `index.html` y conservando el resto de la versión en producción. Solo se recreó la API; salud 200 y archivos públicos verificados.
- Vuelta atrás: restaurar `~/quantfut/releases/compose-antes-20261029-023334.yml` como `~/quantfut/docker-compose.yml` y recrear solo la API.

### 2026-10-29 01:56 UTC · Retiro de leyendas · API `quantfut-api-sin-leyendas:36de48b` (PR #216)
- Se retiraron las leyendas indicadas de mercados, parley y las vistas de conversión. CI del PR: 8 comprobaciones aprobadas; 94 pruebas de frontend y 9 de conversión aprobadas. Ensayo de imagen: 0 módulos con error, 136 rutas.
- Imagen basada en la API en ejecución `quantfut-api:0287a0d`, sustituyendo solo `app.js`, `conversion-views.js` e `index.html`. Se conservó el código anterior de `app.js` en producción: `main` contiene una línea adicional de resultado destacado pendiente de despliegue. Solo se recreó la API; salud 200 y archivos públicos verificados.
- Vuelta atrás: restaurar `~/quantfut/releases/compose-antes-20261029-015602.yml` como `~/quantfut/docker-compose.yml` y recrear solo la API.

### 2026-10-28 23:19 UTC · Córners y tarjetas de FotMob sin esperar 36 h · worker `quantfut-worker:408c43f` (rama `fix/completar-fotmob-inmediato`, sin fusionar a `main`)
- Orden del titular: usar los datos de FotMob cuando falten los de SofaScore y viceversa. Los 5 partidos de Serie A del 28-oct estaban terminados y con la página de FotMob guardada, pero sin córners ni tarjetas en `matches`, y sus fichas en «Pendiente». Cambio: `completar_estadisticas` (solo NULL, marcador coincidente, sin tocar el xG) dentro de la acción `completar`, y el cron de `completar` pasa de una vez al día (09:15) a cada hora (:50).
- **Base distinta de `4907a0d`:** antes de construir, el `src` del worker en ejecución difería de `4907a0d` en tres archivos (`estadisticas.py`, `fotmob_captura.py`, `sofascore_partidos.py`): el parche de contenedor de la sesión `deploys/auditoria-api-20261028` (hora mínima del xG y `xg_corregido`, db/091). Recrear el worker desde `quantfut-worker:4907a0d` lo habría perdido. La imagen nueva es `4907a0d` + ese parche (confirmado por hashes: 168 archivos idénticos al worker en ejecución) + este cambio (commits `a3cb429` y `408c43f`). Entre la imagen nueva y el worker anterior solo difiere `fotmob_captura.py`. `main` no contiene ni esta rama ni el parche de la otra. El `docker-compose.yml` del repo ya estaba desincronizado con el del servidor (lleva otra imagen del worker) y no se tocó.
- Ensayo: 0 módulos con error. `deploy.sh` no se usó porque exige HEAD == `origin/main`; se siguieron sus mismos pasos a mano (construir con `git archive`, ensayo sin red, respaldo del compose, recrear solo el worker). Sin trabajos en curso en el worker al recrearlo.
- Verificado: `completar` manual → 9 partidos completados, 0 conflictos de marcador, 0 xG escrito por FotMob. Venezia–Inter: córners 3–6, amarillas 0–2; 0 partidos terminados de las últimas 72 h sin córners; en la web, «Córners totales · Menos de 10,5» pasa a `win`. Salud 200.
- **Vuelta atrás:** `cp -p ~/quantfut/releases/compose-antes-20261028-231908.yml ~/quantfut/docker-compose.yml` (vuelve a `quantfut-worker:4907a0d`, que NO lleva el parche de `xg_corregido`; para conservarlo, cambiar la etiqueta del worker a `quantfut-worker:a3cb429`, construida el mismo día y idéntica por hashes al worker previo), `cp -p ~/quantfut/releases/crontab-antes-20261028-231908 ~/quantfut/scripts/crontab` y `docker compose up -d --no-deps --no-build --force-recreate worker`.
### 2026-10-28 · `xg_corregido`: xG corregido junto al original, sin tocar `matches` · `db/091` + worker (un archivo); rama `deploys/auditoria-api-20261028`
- Decisión del titular (recomendación aceptada): lo ya guardado en `matches` no se reescribe; por cada partido cuyo xG se guardó antes de 20 h del saque, `xg_corregido` guarda la primera lectura de FotMob tomada pasadas 20 h junto al original (fuente, valores y hora de recepción). Tabla inmutable (`deny_mutation`).
- **Base de datos:** `db/091` aplicada tras ensayo con ROLLBACK (solo crea la tabla y su disparador). **Worker:** `ingest/fotmob_captura.py` (`cd0b5e91c8de` → `6a146643a948`; respaldo en `~/quantfut/deployments/xg-corregido-20261028/antes/`): `revisar_xg` (corre con la acción `completar`, 09:15 UTC, sin peticiones) y `refrescar_xg` ampliado a los xG guardados antes de la hora mínima. Parche del contenedor.
- Relleno de 14 días: 170 páginas de FotMob pedidas a ritmo normal (136 s, directo, 0 denegaciones) y 375 partidos registrados (12 al 26-oct). Pruebas: 1.711 aprobadas.
- **Vuelta atrás:** `DROP TABLE xg_corregido;` y restaurar `fotmob_captura.py` del respaldo.

### 2026-10-28 · Historial desde el 26 de octubre, solo Destacados y Alta probabilidad · API `quantfut-api:0287a0d` (`main` `0287a0d`, PR #212)
- Orden del titular. El historial público empieza el 26 de octubre y cuenta solo los Destacados (fútbol, NBA y tenis) y Alta probabilidad; sin leyenda nueva. Endpoint nuevo `GET /mobile/v1/markets/destacados?desde=` (destacado de fútbol de cada partido terminado, caché de 10 min). CI del PR: 8 comprobaciones aprobadas; 93 pruebas del frontend y 77 de Python.
- Antes: `deploy.sh estado` distinto a `main` en `api/mobile.py` y `api/partido_mercados.py` (mis cambios) y en `api/tenis_publico.py`: la API llevaba la copia de `4907a0d`; la de `main` es `9fa096c8…`, la misma que ya corre el proyector de tenis desde las 16:37 UTC (PR #202), así que no cambia nada en el servicio.
- Construido `quantfut-api:0287a0d`; ensayo: 0 módulos con error, 136 rutas (135 + la nueva). Solo se recreó la API; salud 200.
- Verificado en el dominio: `/mobile/v1/markets/destacados?desde=2026-10-26` responde 200 en ~1,2 s con 67 filas (incluye el día de margen; el cliente corta por día local) y el historial muestra «105 de 129 pronósticos acertados», 26 oct – 28 oct, 81 %, igual a lo medido antes de aplicar. Web con `app.js?v=hist-desde26-20261029`.
- Pendiente: la ficha de un partido puede enseñar otro destacado a quien tenga un pick abierto; el historial usa la definición fija del modelo.
- **Vuelta atrás:** restaurar `~/quantfut/releases/compose-antes-20261028-122621.yml` a `~/quantfut/docker-compose.yml` y recrear solo la API; imagen anterior `quantfut-api-hist-leyenda:cbbfba4`.
### 2026-10-28 · Hora mínima de captura del xG (20 h tras el saque) · SOLO worker (tres archivos); rama `deploys/auditoria-api-20261028`
- Decisión del titular: el xG solo se guarda si la captura es ≥ `XG_MIN_HORAS` (20 por defecto, variable de entorno) después del saque; se corrige tras el partido y la regla de «primera pareja congelada» fijaba valores provisionales (Houston 0-0 como 0,00–0,03).
- `ingest/estadisticas.py` (`4f2d62289806` → `924a82913d3e`), `ingest/sofascore_partidos.py` (`889c3f460ebe` → `9fed2c40145c`, el xG ya no se escribe antes de la hora mínima; el resto de columnas sí) e `ingest/fotmob_captura.py` (`ca50931f0f4f` → `cd0b5e91c8de`: `completar` solo usa páginas tomadas pasada la hora mínima y `refrescar_xg` pide una segunda página a los partidos sin xG cuya única página fue temprana). Las tres bases coincidían con `main`/lo desplegado antes de copiar. Parche del contenedor: se pierde si se recrea el worker.
- Probado: consultas SQL validadas en producción dentro de una transacción con ROLLBACK; una pasada real de `posteriores` → 8 candidatos, 8 páginas guardadas; 14 partidos sin xG ya tienen página válida para `completar`. Pruebas: 1.707 aprobadas.
- Consecuencia: la mediana de SofaScore llega a las 12 h, así que en la práctica el xG lo pondrá FotMob (`completar`, a partir de las 36 h) salvo que SofaScore llegue pasadas las 20 h; el xG llega más tarde pero ya no es provisional. Los xG ya guardados (≈10 % provisionales) NO se reescriben: lo decide el titular.
- **Vuelta atrás:** copiar los tres archivos de `~/quantfut/deployments/xg-hora-minima-20261028/antes/` a `/app/src/qf/ingest/` del worker, o `XG_MIN_HORAS=0` en el entorno para quitar la espera sin tocar código.

### 2026-10-28 · FotMob con respaldo por ZenRows ante un bloqueo · SOLO worker (un archivo) + `.env`; rama `deploys/auditoria-api-20261028`
- Orden del titular: si FotMob bloquea, usar los proxy de ZenRows. `ingest/fotmob_captura.py` (worker, sha `9099a3faf4dc` = `main` antes de copiar; ahora `ca50931f0f4f`): con HTTP 401/403 y `ZENROWS_API_KEY` presente repite la petición por ZenRows (proxy básico 1 crédito; si falla, premium 10), tope `FOTMOB_ZENROWS_MAX_DIA` = 150 créditos al día, sin insistir en directo durante 60 min y con aviso por Telegram. **Un 429 sigue siendo pausa de 12 h** (es límite de ritmo, no se esquiva). Estado en `$ARTIFACT_DIR/fotmob_zenrows_estado.json`.
- Clave en `~/quantfut/.env` (permisos 600, copia previa `~/backups/env.pre-zenrows-20261028`) y en `/etc/environment` del worker en ejecución (lo que lee el cron); no se imprimió en ningún momento. Parche del contenedor, no de la imagen: se pierde el archivo si se recrea, la clave no.
- Probado en el worker: una petición real FotMob → ZenRows (72 ligas, 269 partidos; ZenRows cobró 1 crédito, 3.894 → 3.895 de 5.000, plan Free hasta el 6-nov). Hallazgo: la cabecera `X-Request-Cost` viene en dólares (0,001 = 1 crédito); el contador cuenta como mínimo el nivel pedido.
- **Vuelta atrás:** `docker cp ~/quantfut/deployments/fotmob-zenrows-20261028/antes/fotmob_captura.py quantfut-worker-1:/app/src/qf/ingest/`; o `FOTMOB_ZENROWS=0` en el entorno para apagarlo sin tocar código.

### 2026-10-28 · Retirar leyenda inferior del historial · API `quantfut-api-hist-leyenda:cbbfba4` (PR #209)
- Retirada la leyenda de cuotas bajo la lista del historial, por solicitud del titular. Verificado en el historial público: leyenda, aviso, metodología y pie ausentes; la lista carga.
- CI de PR #209: 8 comprobaciones aprobadas; 91 pruebas del frontend. Ensayo: 0 módulos con error, 135 rutas; salud API 200. Imagen derivada de `quantfut-api-hist-limpio:04f6bae` con solo cinco archivos de interfaz actualizados.
- Vuelta atrás: restaurar `~/quantfut/releases/compose-antes-20261028-110927.yml` a `~/quantfut/docker-compose.yml` y recrear solo la API; imagen anterior `quantfut-api-hist-limpio:04f6bae`.


### 2026-10-28 · Historial sin aviso ni metodología y web sin pie · API `quantfut-api-hist-limpio:04f6bae` (PR #207)
- Solicitud del titular: quitar del historial el aviso y el desplegable de metodología, y quitar el pie de página de la web. Cinco archivos de interfaz, con versiones nuevas para evitar la caché.
- CI de PR #207: 8 comprobaciones aprobadas; 91 pruebas del frontend. Verificado el historial público cargado, sin ambos bloques ni el pie; salud API 200.
- Imagen construida sobre `quantfut-api:4907a0d` con solo los cinco archivos de interfaz; se compararon previamente con la base en ejecución. Ensayo: 0 módulos con error, 135 rutas. Solo se recreó la API.
- Vuelta atrás: restaurar `~/quantfut/releases/compose-antes-20261028-110205.yml` a `~/quantfut/docker-compose.yml` y recrear solo la API; imagen anterior `quantfut-api:4907a0d`.

### 2026-10-28 17:16 UTC · Consumo de APIs: SofaScore con detalles reservados y PropLine con horizonte · SOLO host (dos carpetas) + `db/090`; commit `8861347`
- Nada de imágenes ni contenedores. **PropLine:** nueva `~/propline-shared/releases/8861347` (`propline_shared.py` sha `a12ba4e01b9f`, config `3174a1d0aa6c`, mismo runner y `runtime.json`); `current` apunta ahí. Base comprobada antes: `propline_shared.py` `54387ff6d135` (= `main`). **Vuelta atrás:** `ln -sfn /home/qf/propline-shared/releases/a6dcb96 /home/qf/propline-shared/current`.
- **Apify:** `~/sofascore-apify/current/sofascore_apify.py` (sha `c7c0dbf6263f`; base `26ba76f290b5` = `main`). Respaldo en `~/sofascore-apify/respaldo_20261028_antes_reparto/` (código, config, índice). Prueba en el host: `capture` → «presupuesto agotado», gasto 0,00; `lineups` → «nada vencido». **Vuelta atrás:** copiar `sofascore_apify.py` del respaldo a `current/`.
- **Base de datos:** `db/090` (alias `propline` de `Racing de Santander` y `Tromsoe`) aplicada en transacción tras ensayo con ROLLBACK; reversión en el propio archivo.
- Por qué: detalles de partidos sin pedir desde el 26-oct (433 terminados sin estadísticas) y 70 % de las llamadas de PropLine en fútbol. Medición y plan: `docs/auditoria_consumo_apis_20261028.md`. Pruebas: 1.696 aprobadas, 111 omitidas.
- Pendiente de verificar con la corrida de las 18:07 UTC: llamadas de fútbol/hora y 0 fallos (ver `harness/progreso.md`).

### 2026-10-28 16:37 UTC · Tenis: todos los mercados liquidados y resultados cada ~2 h · imagen `quantfut-tenis:bea262b` (`main` `bea262b`, PR #202)
- Orden del titular: «despliega y fusiona». Causa: el «Pendiente» de tenis tenía dos orígenes. La proyección pública solo liquidaba el ganador (juegos, sets, hándicaps, ganador de set y tie-break quedaban abiertos aunque el partido hubiera terminado) y el calendario con resultados solo se pedía a las 00 y 12 UTC.
- Antes de construir: `main` difería del servidor solo en los archivos de este cambio (`README.md`, `scripts/vps_run.sh`, `tennis_intake_v1/__init__.py` y `__main__.py`, `tests/test_intake_v1.py`), comparados archivo por archivo con el contexto `45f5876`. `scripts/publicar_tenis_web.py` idéntico a `main` (`8a948c47…`). `propline_shared.py` de `main` (`54387ff6…`).
- Respaldo: `~/quantfut-tenis/backup/20261028-resultados/` (`IMAGE` `quantfut-tenis:45f5876`, `vps_run.sh` `2119c1f4…`, `crontab.txt`, `tenis_publico.py` y `publicar_tenis_web.py` de la versión anterior).
- Construcción: `~/quantfut-tenis/build/bea262b/ctx` (`git archive origin/main:apps/tennis` + `propline_shared.py` de `main`) → `docker build` → `quantfut-tenis:bea262b`. Ensayo con copia de los datos y `--network none`: módulos cargan y `--no-capture` sella y evalúa sin errores.
- Cambio: `IMAGE` = `quantfut-tenis:bea262b`; `vps_run.sh` = `main` (`d92a0fb2…`); proyector en `~/quantfut-public-sports/releases/bea262b/` (`tenis_publico.py` `9fa096c8…`, `publicar_tenis_web.py` `8a948c47…`) y `current` → `releases/bea262b`. Crontab sin cambios: la pasada de las :25 ya usa `--results-refresh` fuera de las 00 y 12 UTC.
- Primer error propio: `IMAGE` quedó como `bea262b` sin el nombre de la imagen; la pasada falló antes de llamar al proveedor (`docker run` sin imagen) y no escribió nada. Corregido y repetido.
- Verificado: pasada manual `vps_run.sh hourly` → `captured: [ATP, WTA]`, `capture_errors: []`, `with_result` 182 → 188. `publicar_tenis_web.py` → `state ok`, 157 eventos, 0 problemas. La API (`/web/deportes/tenis`) responde 200 con 147 terminados, 2 `no_result` (Bublik–Marozsan, Kudermetova–Ibragimova), 1 `cancelled` (Fruhvirtova–Kawa), 3 `awaiting_result` y 4 `scheduled`; 3.526 mercados liquidados (ganados, perdidos y devueltos). Sin errores en el log de la API.
- Pendiente: la web muestra `no_result` y `cancelled` con el texto genérico «En curso o por confirmar» (el frontend no se tocó). La cuota de API-Tennis sigue sin verificar: el tope de 26/día es local.
- **Vuelta atrás:** `cp -p ~/quantfut-tenis/backup/20261028-resultados/IMAGE ~/quantfut-tenis/` y `cp -p ~/quantfut-tenis/backup/20261028-resultados/vps_run.sh ~/quantfut-tenis/`; `ln -sfn ~/quantfut-public-sports/releases/67ecddf ~/quantfut-public-sports/current`; la publicación vuelve a la versión anterior en el siguiente ciclo de 5 min. Los partidos sellados se quedan.
### 2026-10-28 16:25 UTC · Reto escalera al 80 % en 7 días con NBA y tenis · migración 089 + API `quantfut-api:4907a0d` + worker `quantfut-worker:4907a0d` (`main` `4907a0d`, PR #203)
- Orden del titular: «despliega y fusiona». Regla nueva de la escalera (2 escalones con presupuesto de probabilidad hasta el 80 % del reto entero, hasta 2 el mismo día, 7 días y luego «expirado», cuota ≥ 1,03) y NBA y tenis desde el archivo PropLine (`publish/escalera_ext.py`). CI del PR 8/8 en verde.
- Antes: `deploy.sh estado` con la API (`37b1646`) y el worker (`98bdfcc-main-696bc39`) distintos de `main` solo en mis archivos (`escalera*`, `hashchain`, `api/mobile.py`) y, en el worker, en código de la API que no ejecuta; sin construcciones ni sesiones SSH en curso. El worker ve `/srv/quantfut/artifacts/propline_shared/index.sqlite` (actualizado a las 16:13 UTC); `ESCALERA_ENABLED=1`.
- **Migración `db/089`** con `lock_timeout 5s`, antes de las imágenes (el código anterior la tolera: los valores por defecto son los de fútbol). Respaldo: `~/quantfut/backups/20261028-162447-escalera-089/` (esquema de las tres tablas, conteos 16/45/42 y compose). Después, los mismos 16 retos, 45 escalones de fútbol y 42 resultados `fuente='partido'`.
- `deploy.sh construir api` → `quantfut-api:4907a0d`; `ensayo`: 0 módulos con error, 135 rutas; `desplegar api`: salud 200. `construir worker` → `quantfut-worker:4907a0d`; `ensayo`: 0 módulos con error; `desplegar worker`.
- Verificado: `/escalera` en el dominio publica `prob_reto` 0,8, `longitudes` [2], `por_dia` 2, `dias_max` 7, `cuota_min` 1,03, `umbrales` {2: 0,8944}, con los 3 retos abiertos y los 13 cerrados de antes. `escalera_datos preview` (solo lectura) en el worker: 774 opciones, 18 en el umbral (fútbol 16, tenis 2, NBA 0); abriría un reto de 2 con dos «marca el local» de la MLS (93,3 % y 92,6 %). `hashchain verify` OK (108 lotes). Sin errores en los logs de API y worker. La primera elección real es la del `daily` de las 09:00.
- **Vuelta atrás:** imágenes: `cp -p ~/quantfut/releases/compose-antes-20261028-102959.yml ~/quantfut/docker-compose.yml` y `docker compose up -d --no-deps --no-build --force-recreate worker api` (vuelven `quantfut-api:37b1646` y `quantfut-worker-propline:98bdfcc-main-696bc39`; el de la API sola es `compose-antes-20261028-102758.yml`). La migración se deja: es aditiva y el código anterior la tolera; los retos y escalones nuevos quedan (inmutables) y el código anterior no los sabe enseñar si son de NBA o tenis (no tienen `match_id`).

### 2026-10-28 · Fotos y logos de los tres deportes · API `quantfut-api:37b1646`, NBA `nba-dashboard-images:37b1646`
- PR #200 y #201 integradas con todas las comprobaciones aprobadas. Once fotos nuevas de API-Tennis y escudo Eyüpspor; retratos NBA y de fútbol; fotos de tenis en lista y encabezado; logos en el panel NBA independiente. Créditos por proveedor y sustitución accesible si falta foto.
- La primera imagen API `5aafe38` se retiró al detectar IDs SofaScore en las alineaciones. Se restauró `ed566f7`; la corrección respeta `src` y se probó aislada contra los datos reales: Maignan → SofaScore WebP, Skorupski → API-Football PNG. Fuentes desconocidas no producen fotos.
- Ensayos: módulos importables, 135 rutas, pruebas de frontend/API y panel NBA aislado. API final con salud 200. Solo presentación; motores y datos deportivos sin cambios. Xinran Sun no tiene foto de proveedor y usa iniciales.
- API: respaldo `~/quantfut/releases/compose-antes-20261028-100914.yml`; restaurarlo y recrear solo API para volver a `ed566f7`.
- NBA: copia exacta de configuración con montajes de solo lectura, usuario 1001 y límite de 256 MB. Respaldo `~/nba-isolated/releases/images-37b1646/dashboard.before.json`; contenedor anterior guardado como `nba-dashboard-before-images-37b1646` (imagen `5aafe38`). Original `v17-6c17f23` retenido en `nba-dashboard-before-images-5aafe38`. Para volver: parar el panel actual, renombrar el respaldo al nombre `nba-dashboard-run69`, restituir `restart=unless-stopped` e iniciarlo; no eliminar volúmenes.


### 2026-10-28 09:32 UTC · #historial rediseñado para convertir · API `quantfut-api:ed566f7` (`main` `ed566f7`, PR #198)
- Orden del titular: «fusionar y desplegar». Cambios: nuevo `historial-views.js` (resumen con intervalo de Wilson, prometido frente a real, curva de beneficio con cuotas registradas, acierto por día y por deporte, registro día por día con cuota y marcador), cableado en `ergonomic-views.js`, estilos `.cv-hist-*` en `conversion.css` y ruta `/historial-views.js` en `web.py`. Sin cambios de API de datos ni de base. `?v=hist-20261028` en `app.js`, `index.html`, `real-views.js` y los imports.
- Antes de construir: `deploy.sh estado` con la API distinta de `main` solo en `api/web.py` (mi cambio) y el worker sin tocar; `index.html`, `app.js`, `real-views.js`, `ergonomic-views.js`, `conversion.css` y `conversion-views.js` servidos idénticos a la base previa (`7ba7a49`).
- `deploy.sh construir api` → `quantfut-api:ed566f7`; `ensayo`: 0 módulos con error, 132 rutas. `CONFIRMO=si deploy.sh desplegar api`: solo se recreó la API; salud 200.
- Verificado en el dominio real con las URL versionadas: `app.js` `3a943998be79`, `real-views.js` `62018e5e12b9`, `ergonomic-views.js` `f850e892dbc2`, `historial-views.js` `507e1fdc9e47`, `conversion.css` `ed06ce65c48f`, `index.html` `e21406edae3f` (iguales al repo); `#historial` muestra 184 de 246 acertados con datos reales y sin errores de consola. Ojo: las URL sin `?v=` (p. ej. `/conversion.css`) siguen con la copia de Cloudflare hasta 4 h; la página usa siempre las versionadas.
- **Vuelta atrás:** `~/quantfut/releases/compose-antes-20261028-093237.yml` → `cp -p` a `~/quantfut/docker-compose.yml` y `docker compose up -d --no-deps --no-build --force-recreate api` (imagen anterior `quantfut-api:31121ba`). Para volver en la web, usar otro `?v=` en `index.html`.

### 2026-10-27 21:29 UTC · Estado real en los mercados de fútbol, #alta/#parley/#escalera centradas y sin avisos · API `quantfut-api:31121ba` (`main` `31121ba`, PR #195 y #196)
- Orden del titular: «fusiona y despliega». Cambios: `partido_mercados.resultado_fila` devuelve `resultado` (win/loss/push) por fila abierta de un partido terminado y la tabla de la web pasa de «Acceso» a «Estado»; `conversion.css` centra las tres vistas; fuera el aviso de #alta y cuatro bloques de #escalera. El PR #196 solo sube los `?v=` (`app.js?v=estado-20261028`, `conversion.css` y `conversion-views.js` `?v=conv-20261028`) por la caché de 4 h de Cloudflare.
- Antes de construir: `deploy.sh estado` con la API distinta de `main` solo en `api/partido_mercados.py` (mi cambio), y `app.js`, `index.html`, `conversion-views.js` y `conversion.css` del contenedor idénticos a `main` previo (`0221687`); sin builds ni sesiones SSH en curso. El worker no se toca (ya difería de `main` en `api/*` por la sesión anterior; no sirve la web).
- `deploy.sh construir api` → `quantfut-api:31121ba`; `ensayo`: 0 módulos con error, 131 rutas. `CONFIRMO=si deploy.sh desplegar api`: solo se recreó la API; salud 200; 0 errores en logs.
- Verificado en el dominio real: hashes servidos = repo (`index.html` `0179e0ea1dc1`, `app.js` `06b0d0c03877`, `conversion-views.js` `034cdf04be90`, `conversion.css` `f64f59a8f26d`). `GET /mobile/v1/matches/{id}?web=1` de partidos terminados trae `resultado`: Argentinos 1–0 Rivadavia, «Más de 1,5 goles» → loss y «gana (empate devuelve)» → win; Roma–Cagliari, 3 win y 1 loss; las filas con candado no llevan resultado.
- **Límite conocido:** córners, tarjetas y «gol en el 1T» quedan «Pendiente» cuando el partido no tiene esa estadística guardada (en los dos partidos de prueba faltaba). Es deliberado: no se inventa el resultado.
- **Vuelta atrás:** `~/quantfut/releases/compose-antes-20261027-212919.yml` → `cp -p` a `~/quantfut/docker-compose.yml` y `docker compose up -d --no-deps --no-build --force-recreate api` (imagen anterior `quantfut-api:0221687`). Para volver en la web, usar otro `?v=` en `index.html`.

### 2026-10-27 21:11 UTC · Logos de NBA en la ventana de partidos · API `quantfut-api:0221687` (`main` `0221687`, PR #193)
- Orden del titular: «fusiónalo» y desplegar. La ventana de NBA y tenis pintaba siempre iniciales aunque los logos ya estaban en producción; ahora `mark()` usa `/web/imagenes/nba/*.png` cuando el manifiesto cargó (`nbaCode()` en `sports-data.js`). Solo frontend; `?v=logos-20261027` en `app.js`, `index.html`, `real-views.js` y los imports.
- Antes de construir: `deploy.sh estado` con API sin diferencias frente a `main`, y los siete archivos de frontend que corrían (`app.js`, `index.html`, `real-views.js`, `ergonomic-views.js`, `sports-window.js`, `sports-data.js`, `conversion-views.js`) idénticos a `main` previo (`c999ea4`). Entre `d788025` y `main` solo había el parche de conversión (PR #192, ya en producción) y este cambio.
- `deploy.sh construir api` → `quantfut-api:0221687`; `ensayo`: 0 módulos con error, 131 rutas, 30 logos en la imagen. `CONFIRMO=si deploy.sh desplegar api`: solo se recreó la API; salud 200; worker, base y Caddy intactos.
- Verificado en el dominio real: `index.html` `fe643b69796e`, `app.js` `dae17a90a370`, `sports-window.js` `08a5ab5a657a`, `sports-data.js` `40197db04e3e` (iguales al repo); sin errores en logs ni consola; en NBA cargan los 8 logos de la lista y los 2 del encabezado.
- **Vuelta atrás:** `~/quantfut/releases/compose-antes-20261027-211131.yml` → `cp -p` a `~/quantfut/docker-compose.yml` y `docker compose up -d --no-deps --no-build --force-recreate api` (imagen anterior `quantfut-api-conversion:002ffcd-v2`). Cloudflare guarda los estáticos 4 h por URL: para volver, usar otro `?v=` en `index.html`.

### 2026-10-28 02:06 UTC · Rediseño de conversión de Alta, Parley y Escalera · API (frontend + `web.py`), parche sobre producción
- Orden del titular: «parche sobre producción». La API corría `quantfut-api-planes:d788025` con un frontend (ventana de deportes, `real-views.js`) que no está en la rama de este cambio (`nba/v13-disponibilidad`); desplegar esa rama habría revertido ese trabajo. Se parchearon SOLO cinco archivos sobre lo que corría: `frontend/app.js` (las tres vistas viejas sustituidas por `conversion-views.js`, + 3 líneas de enganche), `frontend/index.html` (enlace a `conversion.css` y `app.js?v=conv-20261027`), `conversion-views.js`, `conversion.css` y `src/qf/api/web.py` (dos rutas).
- Imagen `quantfut-api-conversion:002ffcd-v2` = `quantfut-api-planes:d788025` + esos cinco archivos. Antes de copiar, el `app.js`, `index.html` y `web.py` del contenedor eran idénticos a los de la base (`5119a1641adf`, `0e3a54536a12`, `0b473d3d9e1d`). Otra sesión había recreado la API a las 02:03 UTC solo por `.env` (`app-download-url-20261027`); imagen sin cambios.
- Ensayo en contenedor aparte (puerto 8011, red de compose): `/`, `/conversion.css`, `/conversion-views.js`, `/app.js`, `/alta-probabilidad`, `/parley`, `/escalera` 200 y hashes iguales a los del release. Vista previa local con el frontend real de producción parcheado: tres rutas sin errores de consola ni desborde horizontal a 375 px; otras rutas intactas. Solo se recreó la API (`--no-deps --no-build --force-recreate api`); worker, base, Caddy y Grafana intactos.
- Verificado en el dominio real: `/` y rutas públicas 200; hashes del dominio = release (`app.js` `ad0d520d5a5b`, `conversion-views.js` `002ffcdf8445`, `conversion.css` `521d6ba59ccc`, `index.html` `d205892445eb`); logs sin errores; las tres pestañas pintan el diseño nuevo.
- **Lección:** Cloudflare guarda los estáticos 4 h por URL completa. La primera imagen (`quantfut-api-conversion:002ffcd`) mantenía `app.js?v=planes-20261027` y el dominio seguía sirviendo el `app.js` antiguo, y mis sondeos sin `?v=` dejaron cacheado un 404 de los archivos nuevos (por eso se piden con `?v=conv-20261027`). Cambiar siempre el `?v=` de cada estático modificado.
- Esta rama (`web/conversion-alta-parley-escalera`, parte de `main` 6b1ac5f, que ya tenía el `app.js` de producción) contiene exactamente los cinco archivos desplegados: al fusionarla, `main` vuelve a ser lo que corre.
- **Respaldo y vuelta atrás:** `~/quantfut/releases/web-conversion-002ffcd/backup/` (`docker-compose.before.yml`, `frontend/app.js`, `frontend/index.html`, `src/qf/api/web.py`). Para volver: `cp -p` el compose de ahí a `~/quantfut/docker-compose.yml` y `docker compose up -d --no-deps --no-build --force-recreate api` (imagen anterior `quantfut-api-planes:d788025`). Cloudflare puede tardar hasta 4 h en soltar el `app.js?v=conv-20261027`; para volver, usar también otro `?v=` en `index.html`.


### 2026-10-28 02:03 UTC · Auditoría de estado y `APP_DOWNLOAD_URL` · SOLO configuración + recrear la API (sin código nuevo)
- **Medido con `scripts/deploy.sh estado` desde `main` `6b1ac5f`:** con la API en `quantfut-api-planes:d788025` tenía **0 archivos distintos** de `main`. El worker (`quantfut-worker-propline:98bdfcc-main-696bc39`) solo se distingue en `api/main.py`, `api/mobile.py`, `api/partido_mercados.py` y `api/web.py` y le faltan `api/nba_estadisticas.py`, `api/tenis_estadisticas.py` y `api/tenis_publico.py`: todo código de la API que el worker no ejecuta. `qf.ingest.live`, `fotmob_captura`, `propline_shared` y `propline_cierres` importan bien y sus logs avanzan (los «sin desplegar» de las entradas del 25-oct ya no aplican). `requirements.txt` del servidor = `main`; el crontab del servidor = el del repo, con el reentrenamiento mensual y el `--bootstrap` ya retirados (26-oct).
- **`docker-compose.yml` del repo** fijaba `api-propline:98bdfcc-app-8c57b05` y `worker-propline:98bdfcc-pitido-ef6f4b3`; ahora fija las de arriba. Cotejado el resto del archivo contra el del servidor: solo difería el formato YAML.
- **`scripts/deploy.sh`** gana `construir`, `ensayo` y `desplegar`. Decisión: el servidor **no** despliega con `git pull` ni con clave de despliegue; se construye con `git archive` enviado por SSH (receta del 15-oct), así no se guarda en el servidor ninguna credencial de GitHub. `construir` y `desplegar` exigen árbol limpio y `HEAD == origin/main`; `desplegar` exige `CONFIRMO=si`, respalda el compose, cambia solo la etiqueta de su servicio y recrea solo ese servicio (con comprobación de salud en la API). `estado` compara la imagen que corre con la fijada en el compose del repo (antes usaba la etiqueta `latest` del worker, que ningún compose usa y estaba vieja) y ahora nombra los archivos que faltan. `ensayo` probado de solo lectura contra las dos imágenes que corrían: 0 módulos con error, 129 rutas en la API.
- **Configuración:** `APP_DOWNLOAD_URL=https://play.google.com/store/apps/details?id=com.saptain.quantfut` en `~/quantfut/.env` (la ficha responde 200; un paquete inexistente, 404). Recreada solo la API con la misma imagen (`up -d --no-deps --no-build --force-recreate api`). Salud local y del dominio 200; `/i/<código>` enlaza a Play. Sin `referrer`: eso necesita el cambio de app y servidor aún sin fusionar.
- **Respaldo y vuelta atrás:** `~/quantfut/releases/app-download-url-20261027/env.before`; `cp -p` sobre `.env` y recrear la API con el mismo comando.
- **Otra sesión desplegó mientras tanto:** a las 02:06 UTC la API pasó a `quantfut-api-conversion:002ffcd-v2` (`releases/web-conversion-002ffcd`; ese commit no está en el repositorio remoto y `web.py` difiere de `main`). Heredó la variable nueva. Quien lo desplegó debe anotarlo aquí y fusionar su rama: **lo que corre en producción debe ser lo que dice `main`**. El compose del repo sigue en `d788025` hasta entonces.
- **Obsoleto por lo medido hoy:** `CHAIN_GIT_REMOTE` está en el worker y `hashchain verify` da OK en 107 lotes (88 revelados, 19 solo con compromiso); `/webhooks/whop` existe (GET 405, POST sin firma 400); Meta CAPI activo con `META_TEST_EVENT_CODE` puesto (8 caracteres) en el worker, tarea `meta_capi` en el cron y 3 eventos `CompleteRegistration` enviados (18 y 25-oct); `/app/meta.env` ya no existe porque el worker se recreó y las variables llegan por `.env`. Con ese código puesto los eventos van a «Probar eventos»: para que cuenten en producción hay que vaciarlo (decisión del titular).

### 2026-10-27 22:29 UTC · Header con herramientas, créditos al pie, NBA sin notas y rediseño de Planes y Paquetes · API `quantfut-api-planes:d788025` (`main` `d788025`, PR #189)
- **Motivo:** Alta probabilidad, Parley del día y Reto escalera pasan al header; los créditos de imágenes (Creative Commons) pasan al pie de toda la web y salen de Pronósticos las notas sobrantes; Pronósticos NBA pierde sus textos explicativos; Planes y Paquetes se rediseñan con CYBERCORE (la etiqueta de cada plan ya no la corta el recorte de esquinas, las tarjetas ocupan todo el ancho y cada plan enlaza directo a crear cuenta o al pedido).
- **Base comprobada (22:2x UTC):** API `quantfut-api-imagenes:4819a76` (la que corría), sin builds ni sesiones SSH en curso; los 7 archivos que toca el PR eran idénticos a `4819a76` dentro del contenedor.
- **Imagen:** `FROM quantfut-api-imagenes:4819a76` + 7 archivos de `frontend/` del commit `d788025` (`git archive`, sin CR): `app.js`, `ergonomic-views.js`, `index.html`, `membership.js`, `real-views.js`, `sports-window.js` y `window.css`. Los hashes dentro de la imagen = repo = dominio, y `styles.css`, `future.css` y `membership.css` siguen idénticas (`original-css.test.mjs`). Las URL llevan `?v=planes-20261027` para esquivar la caché de Cloudflare. Solo se recreó `api`; worker, base, Caddy y Redis sin reinicios.
- Verificado en el dominio real: `/`, `/health`, `/window.css`, `/app.js`, `/membership.js`, `/sports-window.js`, `/real-views.js`, `/ergonomic-views.js`, `/web/partidos`, `/mobile/v1/home`, `/app/v1/plans`, `/alta-probabilidad` y `/web/imagenes/creditos` en 200; `#planes` (3 planes, 7 enlaces en el header) y `#paquetes` renderizan sin errores en la consola ni desplazamiento horizontal a 1440 y 375 px.
- Respaldo y vuelta atrás: `~/quantfut/releases/planes-d788025/backup/` (compose anterior, id de la imagen y los 7 archivos). `cp -p ~/quantfut/releases/planes-d788025/backup/docker-compose.before.yml ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api` (vuelve a `quantfut-api-imagenes:4819a76`).

### 2026-10-27 21:52 UTC · Encabezado único, Pronósticos con CYBERCORE e imágenes de NBA y tenis · API `quantfut-api-imagenes:4819a76` (`main` `4819a76`, PR #186)
- **Motivo:** la ventana de Partidos usaba una cabecera propia distinta a la del resto de la web; los Pronósticos se rediseñan con componentes de CYBERCORE (cifras del día, destacado, pestañas por deporte, tarjetas con cuota y probabilidad); y se alojan en el servidor 30 logos NBA (TheSportsDB) y 168 fotos de tenistas (Wikimedia Commons, CC BY / CC BY-SA / CC0 / dominio público) con autor, licencia y enlace en `frontend/imagenes/manifiesto.json` y en `/web/imagenes/creditos`. El proyecto es sin fines de lucro (decisión del titular, 27-oct).
- **Base comprobada (21:43 UTC):** API `quantfut-api-nba-estadisticas:dde63c6` (la que corría, desplegada por la sesión anterior); sin builds, `compose` ni sesiones SSH en curso. Los 11 archivos que toca el PR (`frontend/{app,ergonomic-views,real-views,sports-data}.js`, `index.html`, `window.css`, `package.json`, `original-css.test.mjs` y `src/qf/api/{main,web}.py`) eran idénticos a `main` dentro del contenedor.
- **Imagen:** `FROM quantfut-api-nba-estadisticas:dde63c6` + 211 archivos del commit `4819a76` (`git archive`, sin CR): los 11 anteriores, `frontend/imagenes.test.mjs` y `frontend/imagenes/` (30 logos, 168 fotos, `manifiesto.json`, `creditos.html`; ~7,7 MB). Dentro de la imagen se comprobaron los 211 hashes (`sha256sum -c`), que `qf.api.main` importa y que `web.py` registra `/web/imagenes/{creditos,manifiesto.json,{carpeta}/{archivo}}`. Las rutas solo sirven las carpetas `nba` y `tenis` con nombres `[a-z0-9-]+.(png|jpg)`; llevan el mismo límite de peticiones que los escudos.
- **Activación:** en `docker-compose.yml` solo cambia la línea de imagen de `api`; recreado únicamente `api` (salud 200 en ~4 s, con restauración automática si fallaba). Worker (`0f994ebb5e20`), base, Caddy, Redis y Grafana sin reinicios; 0 errores en el registro de la API.
- **Verificado en el dominio real:** `/`, `/health`, `/window.css`, `/app.js`, `/web/imagenes/manifiesto.json`, `/web/imagenes/creditos` (con su CSP), un logo y una foto, `/mobile/v1/home`, `/app/v1/plans`, `/alta-probabilidad`, `/web/deportes/tenis` y `/web/partidos` en 200; `/web/imagenes/otra/…`, archivo inexistente, `manifiesto.json` dentro de una carpeta y `..%2f` en 404. Hashes servidos de `app.js`, `window.css`, `index.html`, `ergonomic-views.js`, `real-views.js`, `sports-data.js`, manifiesto y tres imágenes = `main`; las tres hojas originales (`styles.css`, `future.css`, `membership.css`) con los hashes de siempre. En el navegador, `/#picks` muestra los 27 pronósticos del día con escudos y fotos y sin errores de consola.
- **Respaldo y vuelta atrás:** `~/quantfut/releases/encabezado-imagenes-4819a76/backup/` (`docker-compose.before.yml`, `state.txt`, `crontab.before.txt`; el paquete y su `SHA256SUMS.txt` están en `ctx/`). Vuelta atrás: `cp -p ~/quantfut/releases/encabezado-imagenes-4819a76/backup/docker-compose.before.yml ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api` (vuelve a `quantfut-api-nba-estadisticas:dde63c6`, que sigue en el servidor). Sin cambios en base de datos, cron ni modelos.
- **Pendiente:** (1) los términos oficiales de TheSportsDB no se pudieron leer (la página dio 502); solo una copia de terceros que pide mencionar la fuente, ya mencionada en los créditos; confirmarlos antes de mostrar los logos en la app Flutter. (2) La revisión legal sobre marcas de la NBA y derecho a la propia imagen de los jugadores sigue abierta. (3) Los tenistas que aparezcan y no estén en `scripts/imagenes/tenistas.json` salen con iniciales: `python scripts/imagenes/descargar_imagenes.py faltan` los lista. (4) Cloudflare puede conservar `/app.js` sin versión hasta 4 h, pero `index.html` pide `app.js?v=imagenes-20261029`. (5) La app Flutter no usa estas imágenes todavía.

### 2026-10-27 21:23 UTC · NBA: estadísticas de equipos en la ventana de la web (comparativa, forma, cara a cara, clasificación) · API + exportador y cron del host
- PR #185 (`dde63c6`, CI verde 8/8). Imagen `quantfut-api-nba-estadisticas:dde63c6` (`d6742f3607f9`), derivada de `quantfut-api-destacado:b754429` (la que corría) con solo los 9 archivos del PR: 7 de `frontend/` (`app.js`, `index.html`, `package.json`, `sports-data.js`, `sports-window.js`, `window.css`, `nba-stats.test.mjs`) y `src/qf/api/{web,nba_estadisticas}.py`. Antes de reemplazar, los 7 archivos previos del contenedor eran idénticos a `main` (`83fb8ef`); hashes finales de la imagen = repo = dominio (las URL versionadas `?v=nbaestad-20261027`). Worker, base de datos, Caddy y el panel NBA sin reinicios.
- **Ruta nueva:** `GET /web/deportes/nba/estadisticas/{id}` (10 dígitos; otro formato o id sin datos: 404). Solo lee `/srv/quantfut/artifacts/public-sports/nba_stats.json`; el archivo vence a las 6 h y entonces la web dice «Todavía no hay estadísticas publicadas».
- **Exportador (host):** imagen `nba-web-stats:9a761d955f0d` (etiqueta `current`), derivada de `nba-dashboard-live13:v17-6c17f23` con solo `nba/web_stats.py` (build en `~/nba-isolated/live13/build-stats-9a761d955f0d/`). Script `~/quantfut-public-sports/nba-stats/publicar_nba_estadisticas.py` (= `scripts/publicar_nba_estadisticas.py` de `main`): ejecuta el contenedor sin red, de solo lectura, sin capacidades y con cohortes y datos montados en solo lectura; recoge el JSON por stdout y lo escribe de forma atómica en el volumen de la API. Sin eventos o con fallo no publica nada. No usa claves ni consulta proveedores.
- **Cron nuevo:** `*/30 * * * *` bajo `flock` → ese script (log en `nba-stats/stats.log`). Copia previa del crontab en `~/quantfut/releases/nba-estadisticas-dde63c6/backup/crontab.before.txt`; el resto del crontab quedó idéntico (comprobado con `diff`).
- Primera publicación real: 45 eventos, 6.561 partidos, 295 KB.
- Verificado en el dominio real: `/`, `/health`, `/window.css`, `/sports-window.js`, `/web/partidos`, `/web/deportes/tenis`, `/mobile/v1/home`, `/app/v1/plans` y `/nba` en 200; `/web/deportes/nba/estadisticas/0022600121` 200 y con ids inválidos o inexistentes 404; en el navegador, las cuatro pestañas con datos reales de Cleveland–Minnesota y sin errores en la consola; sin errores en los logs de la API. Nota: `/window.css` sin versión sigue en caché de Cloudflare hasta 4 h; la web usa la URL versionada.
- Respaldo y vuelta atrás: `~/quantfut/releases/nba-estadisticas-dde63c6/backup/`. Imagen: `cp -p …/backup/docker-compose.before.yml ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api` (vuelve a `quantfut-api-destacado:b754429`). Cron: `crontab …/backup/crontab.before.txt`. Sin el cron el exportador queda inerte y la web muestra «todavía no hay estadísticas» al caducar el JSON.
- Pendiente: alineaciones, estadio y cuotas por cuarto no tienen fuente validada; hace falta elegir proveedor.

### 2026-10-27 20:07 UTC · Destacado propio de la web, NBA y tenis en la ventana única, estadísticas de jugadores de tenis · API + cron del host
- PR #183 (`7db921f`, CI verde en las dos ejecuciones de cada control). Imagen `quantfut-api-destacado:b754429` (`bf23dea6ef02`), derivada de `quantfut-api-ventana:c6c6fc2` (la que corría) con solo los archivos del PR: 13 de `frontend/` (incl. `sports-window.js` nuevo) y `src/qf/api/{mobile,partido_mercados,tenis_estadisticas,web}.py`. Antes de reemplazar, `app.js`, `mobile.py`, `partido_mercados.py` y `web.py` del contenedor eran idénticos al `main` previo; hashes finales de la imagen = repo = dominio. Worker, base de datos y Caddy sin reinicios.
- **App sin cambios:** `GET /mobile/v1/matches/{id}` sin `?web=1` conserva `aplicar_acceso` (prueba incluida); la regla de la web (`aplicar_acceso_web`: destacado 1,40–1,80 de todos los mercados y 3 mercados abiertos como mínimo) solo se activa con `?web=1`. Verificado en producción: sin el parámetro 1 abierta y sin destacado; con él 4 abiertas y destacado.
- **Exportador de estadísticas de tenis (host):** `~/quantfut-public-sports/stats/` (`publicar_tenis_estadisticas.py` + `tenis_estadisticas.py`, caché en `cache/`, tope 600 llamadas/día y 140 por corrida a API-Tennis; la clave sigue en `~/quantfut-tenis/secrets`, no se imprime ni se publica). Escribe `tennis_stats.json` en el volumen de artefactos y la API lo sirve en `/web/deportes/tenis/estadisticas/{id}`. Primera corrida real: 36 partidos, 72 jugadores, 110 llamadas el día de la prueba en seco.
- **Cron nuevo** (`crontab -l`): `17 */2 * * *` → `publicar_tenis_estadisticas.py` (log en `stats/stats.log`). Copia previa del crontab en `~/quantfut/releases/destacado-gratis-926ba7e/backup/crontab.before.txt`; las líneas anteriores quedaron intactas.
- Verificado en el dominio real: `/`, `/health`, `/window.css`, `/sports-window.js`, `/web/partidos`, `/mobile/v1/home`, `/app/v1/plans`, `/alta-probabilidad`, `/web/deportes/tenis` y `/web/deportes/tenis/estadisticas/12173891` en 200 (id no numérico: 404); cuatro hojas originales idénticas; sin errores en logs ni en la consola del navegador.
- Respaldo y vuelta atrás: `~/quantfut/releases/destacado-gratis-926ba7e/backup/`. Imagen: `cp -p …/backup/docker-compose.before.yml ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api` (vuelve a `quantfut-api-ventana:c6c6fc2`). Cron: `crontab …/backup/crontab.before.txt`. El exportador queda inerte sin cron; la web muestra «todavía no hay estadísticas» si el JSON caduca (14 h).
- Pendiente: NBA aún sin forma ni cara a cara (necesita su propio exportador); la pista cubierta, la mano hábil, la estatura y el rendimiento como favorito/no favorito no existen en la fuente de tenis.

### 2026-10-27 16:53 UTC · Ventana única Partidos+Mercados (pronóstico destacado 1,30–1,80) · API (frontend + `web.py`)
- PR #180 (`c7a21e4`, que entró con el rango 1,40 antes de llegar el cambio) y #181 (`cf08c32`, rango 1,30), con el arnés de cada PR en verde; `main` = imagen (hashes de app, fichas-data, window.css y web.py iguales). Imagen `quantfut-api-ventana:c6c6fc2` (`0748393335c0`), derivada de `quantfut-api-gratis10:cf88564` (la que corría) con solo 12 archivos: `frontend/{app,ergonomic-views,fichas-data,real-views}.js`, `index.html`, `window.css` (nuevo), `server.mjs`, `DESIGN_SYSTEM.md`, tres pruebas y `src/qf/api/web.py` (ruta `/window.css`). No se tocan worker, base, Caddy ni el resto de la API.
- Antes de reemplazar se comprobó que los archivos de frontend y `web.py` del contenedor eran idénticos a `main` (`ce40c6f`); `cf88564` no está en `main`, no se tocó nada más de esa imagen. Hashes de los archivos de la imagen = hashes del commit.
- Respaldo previo (frontend, `web.py`, compose, id de imagen) en `~/quantfut/releases/ventana-unica-865f925/backup/`.
- Excepción a «solo hojas originales»: `window.css` es solo disposición (sin colores ni fuentes), `original-css.test.mjs` la admite y mantiene las cuatro hojas originales idénticas por hash. Revertir la ventana = volver al compose anterior.
- Vuelta atrás: `cp -p ~/quantfut/releases/ventana-unica-865f925/backup/docker-compose.before.yml ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api` (imagen anterior `quantfut-api-gratis10:cf88564`).
- Verificado en el dominio real: `/`, `/health`, `/window.css`, `/web/partidos`, `/mobile/v1/home`, `/app/v1/plans` y `/alta-probabilidad` en 200; hashes de las hojas y de los `.js` iguales a `main`; cuatro hojas originales idénticas; sin errores en logs ni en la consola del navegador. Worker, base y Caddy sin reinicios. Nota: Cloudflare conserva `/app.js` sin versión hasta 4 h, pero `index.html` pide `app.js?v=acomodo-20261028`, que ya sirve el archivo nuevo.

### 2026-10-27 15:45:35 UTC · Tenis: juegos ganados por jugador y nombres con nombre intermedio · imagen `quantfut-tenis:45f5876` (`main` `45f5876`, PR #177)
- **Motivo:** orden del titular: añadir `player_games_won` de PropLine al adaptador de tenis, con pruebas, y desplegarlo. Además, Leylah Fernandez – Himeno Sakatsume se selló hoy sin precio porque PropLine la lista como «Leylah Annie Fernandez».
- **Estado previo comprobado:** `IMAGE` = `quantfut-tenis:7b974ed`, `vps_run.sh` y crontab iguales a la entrada del 26-oct 19:40; `apps/tennis` y `propline_shared.py` de `7b974ed` idénticos a `main` antes del PR, así que la imagen nueva solo añade este cambio. Nadie más desplegando tenis.
- **Imagen:** `git archive 45f5876:apps/tennis` (`core.autocrlf=false`) + `src/qf/ingest/propline_shared.py` de `45f5876` (sha256 `54387ff6…`, el mismo de la imagen anterior y del recolector) en `~/quantfut-tenis/build/45f5876/ctx`. Cambio activado escribiendo `IMAGE` con `hourly.lock` tomado; `vps_run.sh`, crontab y `motor_config.json` sin cambios.
- **Ensayo antes de activar (imagen de `main`, datos en solo lectura):** los 7 partidos sellados con tablero en las últimas 24 h, recalculados con la foto de PropLine de su hora de sellado: 17 líneas de juegos por jugador, todas con probabilidad del motor, y las otras 364 líneas idénticas a lo sellado. Fernandez – Sakatsume habría tenido 55 líneas con precio.
- **Verificado:** pasada manual `vps_run.sh hourly` 15:45 UTC con código 0, evaluación recalculada (`offered_markets` sin errores). Sellado completo ejercido en una copia temporal de `ledger.sqlite` y `predictions` (borrada después): 5 partidos del 28-oct sellados, 29–51 líneas cada uno y 2–4 de juegos por jugador. Primer sellado real con la imagen: Rakhimova – Alexandrova, pasada de las 23:25 UTC.
- **Observación:** en los «más de» de juegos por jugador el motor queda por debajo del mercado, igual que en el total de juegos (−0,04 de media en 137 líneas; hándicap +0,001). No es de este cambio; lo mide `offered_markets` por familia.
- **No cambia:** la web y la app (leen `forecast.markets`, no `market_board`), el recolector de PropLine y los protocolos congelados (`tennis_markets_v2` y `tennis_allmarkets_v1` sin tocar).
- Respaldo: `~/quantfut-tenis/backup/20261027-player-games/` (`IMAGE`, `vps_run.sh`, `motor_config.json`, `crontab.txt`).
- **Vuelta atrás:** `echo quantfut-tenis:7b974ed > ~/quantfut-tenis/IMAGE` (fuera de :25-:30 hora del servidor). Los sellados nuevos se quedan (inmutables); con la imagen anterior sus filas `player_games` no se evalúan.

### 2026-10-27 15:42 UTC · App: gratis de Alta probabilidad al 10 % del día · API `quantfut-api-gratis10:cf88564` (`main` `4494869`, PR #174)
- **Motivo:** decisión del titular: es gratis el 10 % de los pronósticos publicados en el lote del día (hacia arriba), los de mayor probabilidad, sin rango de cuota. Sustituye «uno por mercado, cuota ≤ 1,60, hasta 4 abiertos». Un rango 1,40-1,50 pedido antes se descartó tras el ensayo: 0 pronósticos de la semana en ese rango.
- **Base comprobada:** API `quantfut-api-original:5ba3375` (entrada de la otra sesión, PR #176, ya cerrada); `scripts/deploy.sh estado` daba como única diferencia con la rama `api/mobile.py`. Nadie más desplegando (sin builds ni compose en curso).
- **Imagen:** `FROM quantfut-api-original:5ba3375` + solo `src/qf/api/mobile.py` (sha256 `dcf03f92460f`, = `main` `4494869`). Importa sin red.
- **Ensayo** con la imagen candidata y la base en solo lectura (`default_transaction_read_only=on`, sin escribir repartos): lote del 27-oct, 9 publicados → cupo 1 → 1 gratis (prob 0,90, cuota 1,08) en vez de 6; lotes anteriores sin cambios (ya empezados, siguen visibles).
- **Verificado en el dominio real:** `/health`, `/`, `/alta-probabilidad` y `/mobile/v1/config` 200; config con `high_probability_free_fraction: 0.1`; `/mobile/v1/home` → Alta probabilidad con 1 gratis y 8 con candado; web pública 1 gratis. Hash de `mobile.py` en el contenedor = `main`. 0 errores y 0 reinicios en los registros. Worker intacto (mismo contenedor `0f994ebb5e20`).
- **Pendiente:** la app instalada sigue diciendo «hasta 4 gratis» hasta publicar una build nueva (el texto «10 % gratis» ya está en `main`).
- **Respaldo:** `~/quantfut/releases/gratis10-cf88564/backup/` (`docker-compose.yml`, `mobile.py` anterior, `state.txt`).
- **Vuelta atrás:** `cp -p ~/quantfut/releases/gratis10-cf88564/backup/docker-compose.yml ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api` (vuelve `quantfut-api-original:5ba3375`). Los repartos que `top_up` haya añadido en `mobile_free_allocations` pueden quedarse: la regla anterior los recorta al leer.

### 2026-10-27 15:33:52 UTC · Restaurado el CSS anterior: solo acomodo multideporte · API `quantfut-api-original:5ba3375` (`main` `1866c9b`, PR #175)
- **Orden del titular:** conservar obligatoriamente el CSS anterior, incluidos colores, tarjetas y botones; el cambio solicitado es solo de acomodo. Se elimina la hoja añadida `ergonomia.css`, su carga y su ruta, y se reutilizan cabecera, tarjetas `live-pick`, paneles, botones, tablas y planes anteriores. El cajón móvil no se abre desde escritorio; las herramientas se agrupan con componentes existentes.
- **CSS idéntico a la versión previa `18f5604`:** `styles.css` `9cebbf1d…`, `future.css` `eff42cf8…`, `membership.css` `57201c52…` y CYBERCORE CSS 0.3.0 `8c4bc2fc…`. Comparación completa de hashes en servidor y pruebas; exactamente las cuatro hojas anteriores en HTML, sin capas ni estilos inline añadidos. La regla queda en `CLAUDE.md` y el CI ejecuta las 54 pruebas frontend, incluida la protección del CSS.
- **Base y activación:** anterior `quantfut-api-hub:67ecddf`, 180 archivos verificados; seis archivos de interfaz/rutas copiados desde `5ba3375896eca7aee79bcdccb670a1020047c088`, iguales a `main` `1866c9b`. Imagen `FROM` la anterior, con retirada del único CSS rechazado. Ensayo aislado, respaldo, bloqueo de despliegue y recreación exclusiva de la API; 179 archivos finales coincidentes tras retirar la hoja.
- **Verificado en producción:** `/health` `ok`, HTML `acomodo-20261027`, cuatro CSS originales, `/ergonomia.css` 404, cuatro pronósticos abiertos de fútbol y 155 registros recientes de tenis. Se conserva la integración NBA y el exportador público de tenis; worker y panel NBA mantienen sus contenedores. HTML con `no-cache, must-revalidate` para que las recargas consulten la versión vigente. Menú móvil probado a 390 px con el CSS anterior.
- **Pruebas:** 54 frontend y siete del lector público local; CI completo verde (frontend, arnés/Postgres, NBA y tenis) antes de fusionar.
- **Respaldo:** `~/quantfut/releases/web-original-5ba3375/backup/` (compose, frontend, `web.py`, estado). Paquete SHA256 `b0536c3c68c8b110a859bd2b6cc571fccac5eb1c41234b76a6b6e3a5a532fce2`; ensayo y activación en `stage-ok.json` y `deployed.json`.
- **Vuelta atrás técnica:** `cp -p ~/quantfut/releases/web-original-5ba3375/backup/docker-compose.yml ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api`, seguido de `/health`. Esa imagen recuperaría el diseño rechazado: usar solo para incidente técnico y volver a aplicar la corrección. No cambia ningún cron, modelo ni dato del motor.

### 2026-10-27 15:16:36 UTC · Web ergonómica de fútbol, NBA y tenis · API `quantfut-api-hub:67ecddf` (`main` `de06ab6`, PR #172)
- **Motivo:** ordenar la navegación y reunir los tres deportes, por petición del titular. Portada, pronósticos con búsqueda/fechas/deporte, resultados y planes; CYBERCORE CSS 0.3.0 conservado. Fútbol mantiene gratis/Plus, NBA sus probabilidades estadísticas y tenis sus publicaciones selladas.
- **Base y paquete:** API anterior `quantfut-api-real:138b2ab`; 176 archivos existentes coinciden con `main` base `18f5604`. Nueve archivos de aplicación copiados desde el commit `67ecddfaf1f5351e2ca97f67fc97de2bfec9d96c`, idénticos a `main` `de06ab6`. Paquete SHA256 `f764400e2aa0ce32d9fbfe869b8d27ecf0bd58ed67ef1970f3dafbc189aade25`. Imagen `FROM` la anterior, sin reconstruir desde el árbol antiguo del servidor.
- **Ensayo y activación:** contenedor aislado, consultas de base de datos de solo lectura; `/health`, cuatro módulos/estilos y fuentes de fútbol/tenis válidos. Bloqueo de publicación, respaldo y comparación de compose/crontab antes de actuar. Solo se recreó `api`; 180 hashes finales coinciden con la versión revisada. Worker y panel NBA conservan sus identificadores; los montajes de la API son exactamente los anteriores.
- **Tenis sin montajes privados:** `~/quantfut-public-sports/releases/67ecddf/` contiene el exportador y proyector revisados, con enlace `current`. Cada cinco minutos (`2-59/5`) el host verifica sellos y recibos y sustituye exclusivamente el JSON público en `/srv/quantfut/artifacts/public-sports/tennis.json`, dentro del volumen existente. No copia modelos, parámetros, credenciales ni originales a la API; no hace consultas a proveedores ni altera el cron del motor. La API repite el recorte de campos y caduca la salida a las dos horas.
- **Comprobado en el dominio:** página con `ergonomia-20261027` y CYBERCORE 0.3.0, salud `ok`, cuatro pronósticos abiertos de fútbol y cinco reservados; tenis `ok`, 155 eventos recientes y cero problemas; NBA `ok`, 18 cohortes. UI móvil de 390 px sin desbordamiento horizontal; navegación a la jornada NBA real del 26-oct y detalle agrupado por partido/jugadores. Los recálculos posteriores al inicio no se cuentan como pronósticos previos.
- **Pruebas:** 51 frontend, 58 de API/entrega/publicación iniciales y siete del lector público final; arnés completo con Postgres, NBA y tenis verdes en GitHub antes de fusionar. Sin cambios en modelos, puertas de publicación, datos originales, productores ni sus trabajos programados.
- **Respaldo:** `~/quantfut/releases/web-ergonomia-67ecddf/backup/` contiene `docker-compose.yml`, `crontab.txt`, frontend anterior, `web.py` y estado previo. Ensayo y comprobante en `stage-ok.json` y `deployed.json`.
- **Vuelta atrás:** `cp -p ~/quantfut/releases/web-ergonomia-67ecddf/backup/docker-compose.yml ~/quantfut/docker-compose.yml && crontab ~/quantfut/releases/web-ergonomia-67ecddf/backup/crontab.txt && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api`; comprobar `/health`. Los sellos originales no se tocan; la salida pública y el código del exportador pueden conservarse sin la tarea programada. El activador restaura la API anterior y el cron si falla la comprobación.

### 2026-10-27 14:14:55 UTC · Web con pronósticos reales · API `quantfut-api-real:138b2ab` (`main` `b05e085`, PR #170)
- **Motivo:** retirar el catálogo ficticio y mostrar los pronósticos calculados y sellados que ya entrega el motor. Se conserva el diseño anterior y CYBERCORE CSS 0.3.0; CSS, modelos, datos, cron y permisos VIP sin cambios.
- **Base comprobada:** API `quantfut-api-propline:98bdfcc-main-696bc39`; los 162 Python de `src/` y los cuatro archivos frontend existentes coincidían con la base `843b286`. Los seis archivos publicados coinciden con `main` `b05e085` (commit de origen `138b2ab7ffadada39a60791e1811d272d903a46a`).
- **Publicación:** imagen construida desde la API que estaba funcionando, copiando únicamente `frontend/{app.js,fichas-data.js,index.html,membership.js,real-views.js}` y `src/qf/api/web.py`. Ensayo en contenedor aislado con base de datos de solo lectura; después, bloqueo de despliegue, comparación de compose y recreación exclusiva de `api`, sin reconstruir desde el árbol antiguo del servidor.
- **Verificado:** arnés, NBA y tenis verdes en GitHub; 44 pruebas frontend y 52 de rutas/entrega/publicación. Salud 200, agenda de 180 partidos, cuatro pronósticos gratuitos con sello y cinco bloqueados; web pública `/#picks` muestra las selecciones reales del 27-oct, con cuota, probabilidad y registro. Sin catálogo simulado. Worker y NBA conservan exactamente sus contenedores anteriores.
- **Motor:** modelo `2026.10.26-020600` ya activo; la corrida diaria de las 09:00 UTC había calculado la jornada. La puerta separada de picks de valor conserva su validación y su interruptor: no se habilita artificialmente con una muestra insuficiente.
- **Respaldo:** `~/quantfut/releases/web-real-138b2ab/backup/` contiene compose, frontend anterior, `web.py` y estado de los contenedores. Paquete SHA256 `0e31ae0365eb08fdafc97437c872e0c34b5a97ae220a86f0262e7612d0a06e85`; ensayo y despliegue en `stage-ok.json` y `deployed.json`.
- **Vuelta atrás:** `cp -p ~/quantfut/releases/web-real-138b2ab/backup/docker-compose.yml ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api`. Comprobar `/health` después. El script de publicación también restaura automáticamente la imagen anterior si falla su comprobación.

### 2026-10-27 03:26 UTC · Fútbol: worker y API alineados con `main` · imágenes `quantfut-{worker,api}-propline:98bdfcc-main-696bc39` (`main` `696bc39`; el último cambio de `src/` es `f227fd9`)
- **Motivo:** instrucción del titular (26-oct): el motor de fútbol debe estar en producción en todas sus fases. Desde las entradas del 26-oct (01:41 worker, 00:53 API) el worker y la API llevaban cada uno cambios que el otro no tenía: worker distinto de `main` en `partido_mercados.py`, `parley_datos.py`, `alta_prob.py` y `propline_shared.py`; API distinta en `archivo_a_matches.py`, `fotmob_captura.py`, `live.py`, `propline_shared.py`, `alta_prob_datos.py`, `alta_prob_ext.py` y `escalera_datos.py` (medido con `scripts/deploy.sh estado`).
- **Estado previo comprobado (03:20 UTC):** worker `98bdfcc-pitido-ef6f4b3` y API `98bdfcc-app-8c57b05`; `scripts/crontab` instalado = `main` (`f08504f1…`); modelo activo `2026.10.26-020600`; nadie más desplegando (sin builds, compose ni sesiones ssh); `src/` de `main` sin cambios desde `f227fd9`.
- **Imágenes:** cada una `FROM` la imagen que corría + solo los archivos distintos de `main` (`git archive`, sin CR). Comprobado por hash que las dos contienen los 162 `.py` de `src/` idénticos a `main`, y que todos los módulos de `qf` importan sin error en un contenedor sin red. Compose: solo cambian las dos etiquetas; recreados `api` y `worker` a las 03:26 (fuera de :07-:25).
- **Verificado:** `/health`, `/parley`, `/model-card` y `/mobile/v1/config` 200 en el dominio real; `/health` 200 dentro de la API; `crontab` del worker = `main`; las pasadas de las 03:30 (`live`, `sello_tardio`, `rafagas`) corrieron sin errores; 0 reinicios y 0 errores en los registros de ambos.
- **No cambia:** `PUBLISH_PICKS_ENABLED` sigue apagado (decisión del titular: se enciende al cumplirse la puerta de CLV, hoy n=235 de 300); modelo, base de datos, cron y las fases F3–F12 que esperan muestra fuera de muestra no se tocan.
- Respaldo: `~/quantfut/backups/20261027-futbol-main-696bc39/` (`docker-compose.yml.antes-despliegue`, `crontab.antes-despliegue`, `imagenes.txt`).
- **Vuelta atrás** (fuera de :07-:25): `B=~/quantfut/backups/20261027-futbol-main-696bc39; cp -p $B/docker-compose.yml.antes-despliegue ~/quantfut/docker-compose.yml && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api worker` (vuelven `98bdfcc-app-8c57b05` y `98bdfcc-pitido-ef6f4b3`; las imágenes siguen en el servidor).

### 2026-10-27 02:02 UTC · NBA 1.7.0: fuerza individual activa, temporada actual y revisiones de lo publicado · main `7a5c71a` (PR #167)
- Autorización explícita del titular: «fusiona el PR #167 en main y activa la 1.7 en producción con el activador preparado». CI del PR en verde (fútbol/arnés, NBA, tenis); 857 pruebas NBA locales, 18 omitidas por Postgres aislado/permisos de Windows.
- Verificado antes de activar: el código NBA de main `7a5c71a` es idéntico (`git diff` vacío) al commit `6c17f23` con el que se construyeron las imágenes `nba-live13-producer:v17-6c17f23` y `nba-dashboard-live13:v17-6c17f23` y se entrenó el modelo; el modelo registra los hashes de sus cuatro módulos y coinciden con la imagen.
- Modelo `9e2dcb72bef765ba6932ad1429a235386b6b6bb0a97bc45fab8b10fcbdbe2ab6`: 2024-25 y 2025-26 más 43 partidos y 524 jugadores de 2026-27 anteriores al corte del 26-oct; base consolidada de 6.552 partidos y 170.627 filas sin columnas faltantes. Fuerza individual (ridge 25, peso 0,25) activa; historial de partido regular solo de temporada regular. Detalle: `docs/nba_recalibracion_17_20261026.md`.
- Ensayo previo en una copia de las 18 cohortes: 0 problemas en el panel; 1.061 resultados, Brier 0,2490 frente a 0,2482 del original (total del partido 0,2215 → 0,2041; ganador 0,2019 → 0,2119), sin que una semana de partidos lo distinga del azar.
- Activación (panel, modelo, datos y productor bajo `producer.lock`, con reversión automática): migración completa de las 18 cohortes, 3.217 probabilidades modificadas, 0 errores; panel `/nba/api/data` 200 con 18 cohortes, 0 problemas, las 18 con fecha de recálculo; pasada del cron de las 02:10 sin errores. Los originales sellados no se modificaron: cada recálculo es una revisión aparte en `cohorts/*/updates/`. Los recálculos de partidos ya iniciados llevan `performance_eligible=false` y no cuentan en el marcador. Cada pasada del productor revisa los partidos aún no iniciados y descarta la revisión que no cambie nada.
- Servicios y cron sin cambios. Respaldo: `~/nba-isolated/live13/backup-v17-6c17f23/` (`producer.sh`, `crontab.txt`, `dashboard.inspect.json`, modelo anterior y `deployment.json`); panel anterior `nba-dashboard-before-v17-6c17f23`; modelo anterior `model.before-v17-6c17f23`; datos anteriores `data.before-v17-6c17f23`.
- Vuelta atrás bajo `producer.lock`: restaurar `producer.sh` del respaldo; renombrar `model` y `data` actuales a otro nombre y devolver `model.before-v17-6c17f23` y `data.before-v17-6c17f23`; detener/eliminar el panel nuevo, renombrar `nba-dashboard-before-v17-6c17f23` a `nba-dashboard-run69`, restablecer `restart=unless-stopped` e iniciarlo. Las carpetas `updates/` pueden dejarse: el panel 1.6 las ignora, y quitarlas devuelve las probabilidades originales. No borrar cohortes. Comprobado el 27-oct con la imagen del panel 1.6 sobre una copia de una cohorte con `updates/`: la lee sin error y muestra los originales.
- Aprendido: con el activador, la migración completa tarda unos 9 minutos; el tiempo límite de la sesión SSH la dejó en segundo plano, pero terminó y escribió `deployment.json`. La primera revisión de un partido pendiente se ejercita con los partidos del 27-oct.

### 2026-10-26 23:32 UTC · NBA 1.6.0: pertenencia oficial y fuerza individual en sombra · main `74a05cc` (PR #166)
- Autorización explícita del titular: «Sí, subir, integrar y desplegar». CI de main y PR en verde (fútbol, NBA y tenis); 838 pruebas NBA locales, 18 omitidas por Postgres aislado/permisos de Windows.
- Base verificada por hashes: productor `nba-live13-producer:20261026` y panel `nba-dashboard-live13:20261025c` coinciden con `03f4ada` en los componentes activos. Imágenes `nba-live13-producer:rosters-7d87fe1` y `nba-dashboard-live13:rosters-7d87fe1`, código de `7d87fe1` idéntico a main `74a05cc` para NBA; misma base y configuración. Datos, cron y otros servicios sin cambios.
- Modelo reajustado con código exacto, hash `a3bf6b5b4a1a1c6852a2625c738587cf56d82c1c3fdf552a6957e5391d2737c4`. Comparación dentro del servidor: 14 comprobaciones aprobadas, equipo, participación y los 12 mercados de jugador idénticos. Se activa `official_rosters`; el candidato de fuerza permanece separado en esta versión.
- Ensayo real: 2 partidos, 542 pronósticos (534 de jugador), 71 pertenencias verificadas; ningún valor experimental se publica. Panel compatible con todas las cohortes previas. Activación panel primero, modelo/productor después; `/nba/api/data` 200, 17 cohortes, 0 problemas. Pasada manual sin errores, sin nuevos partidos por sellar.
- Un primer activador falló antes de modificar servicios por Python 3.10 del host; después una ruta de salud equivocada provocó reversión automática correcta. Ambos problemas se corrigieron antes de la activación final. Respaldo final `~/nba-isolated/live13/backup-rosters-74a05cc-b/`; panel anterior `nba-dashboard-before-rosters-74a05cc-b`; modelo anterior `model.before-rosters-74a05cc-b`.
- Vuelta atrás bajo `producer.lock`: restaurar `producer.sh` del respaldo, renombrar el modelo actual a otra carpeta y devolver `model.before-rosters-74a05cc-b` a `model`; detener/eliminar el panel nuevo, renombrar el panel anterior a `nba-dashboard-run69`, restablecer `restart=unless-stopped` e iniciarlo. No borrar cohortes.
- Instrucción posterior del titular, 26-oct: activar también el ajuste de fuerza, entrenar con los datos actuales y recalcular lo publicado. Autoriza revisiones con nueva fecha/versionado; no presentar un recálculo posterior al resultado como un pronóstico anterior al partido.

### 2026-10-26 21:50 UTC · Tenis: doble apellido · imagen `quantfut-tenis:7b974ed` (PR #161)
- Misma construcción que la entrada de las 19:40 (`git archive 7b974ed:apps/tennis`, `propline_shared.py` idéntico, `vps_run.sh` igual al activo). Solo cambia `tennis_intake_v1`: «D. Merida Aguilar» resuelve a «Daniel Merida».
- Comprobado con los 3 partidos en espera del 27-oct: Sun–Sawangkaew y Griekspoor–Nakashima con precio de PropLine, Merida–Medvedev con el apilador; los tres se habrían excluido antes de la auditoría.
- **Vuelta atrás:** `echo quantfut-tenis:5b3040b > ~/quantfut-tenis/IMAGE`.

### 2026-10-26 19:50 UTC · NBA: productor vivo 1.5.0 (umbral estadístico para jugadores sin línea de PropLine) · imagen `nba-live13-producer:20261026` (`main` `926daee`, PR #152) + modelo `e48da3bb…`
- **Motivo:** el titular pidió recalibración, corregir los errores del vivo y dejarlo en producción. La recalibración de equipo no entra (protocolo congelado `nba_live15`, `docs/nba_live15_recalibracion_20261026.md`). Errores corregidos: la cohorte `2026-10-25_1930` se selló sin jugadores porque el recolector de PropLine se saltó la captura de las 23:00 UTC (reserva de cuota) y `player_turnovers` nunca se sellaba (menos de 2 casas).
- **Estado previo comprobado (19:47 UTC):** `producer.sh` con `nba-live13-producer:20261025b` y `--memory 1g`, modelo 1.4.0 `5314c9ef…`, datos `e5326b7f…`/`c2c13b36…` (no cambian); panel `nba-dashboard-run69` (`nba-dashboard-live13:20261025c`, no cambia). Nadie más desplegando NBA (la entrada de tenis de las 19:40 tocó solo su imagen y su crontab).
- **Imagen:** `FROM nba-live13-producer:20261025b` + `src/nba`, los tres protocolos y `propline_shared.py` de `git archive 926daee` (`~/nba-isolated/live13/build-926daee`, manifiesto igual al de la imagen ensayada). Módulo `5b704d44…`, versión `nba-multimarket-live-1.5.0`.
- **Modelo:** reajustado en local con los mismos datos y opciones que 1.4.0; `compare` sin `--retrain`: equipo, tabla de participación y los 12 mercados de jugador idénticos, solo cambia `live_module_sha256`.
- **Ensayo (19:3x UTC, carpetas temporales, imagen de la rama):** los 9 partidos del 26-oct sellados a la hora real: 2.130 pronósticos (827 con línea de PropLine de las 19:07, el resto en umbral estadístico; 147 de pérdidas), 16-22 jugadores estadísticos por partido, todos con partidos de esta temporada; 43 s y 805 MB. El panel en marcha lee esa cohorte (2.130 filas en 0,08 s). Un primer ensayo sacó jugadores que ya no están en la plantilla (último partido la temporada pasada): corregido antes de fusionar.
- **Cambio (19:49:51 UTC, con `producer.lock` tomado):** `model` ← `model.next-20261026`; `producer.sh`: imagen `nba-live13-producer:20261026` y `--memory 1536m` (margen para noches con muchos partidos a la vez). Pasada manual 19:49 sin errores (sin partidos que sellar).
- Respaldos en `~/nba-isolated/live13/`: `producer.sh.before-20261026`, `model.before-20261026`, `crontab.before-20261026` (sin cambios), `containers.before-20261026.txt`.
- **Verificado (21:30 UTC, primer sellado real):** cohorte `2026-10-26_1730` (MIN @ CLE, WAS @ CHA) con versión `nba-multimarket-live-1.5.0` y modelo `e48da3bb…`; 447 filas: 222 con línea de PropLine (archivo de las 21:08 UTC), 217 en umbral estadístico y 8 de equipo; sin errores en `nba_live13.log`. Equipos comprobados: ningún jugador pronosticado sin partidos esta temporada; los 28 jugadores cotizados por PropLine tienen pronóstico (0 descartados); cruce con el informe oficial de lesiones sin discrepancias (2 coinciden, 10 `Out` omitidos). PropLine no trae el equipo del jugador: un traspasado sin partidos de temporada regular se descarta, no se asigna mal.
- **Vuelta atrás:** `cd ~/nba-isolated/live13 && flock producer.lock -c 'cp -p producer.sh.before-20261026 producer.sh && rm -r model && cp -a model.before-20261026 model'`. Las cohortes ya selladas se quedan (inmutables).

### 2026-10-26 19:40 UTC · Tenis: auditoría (sellado horario, todas las líneas de PropLine, superficie, nombres, jugadores sin saque) · imagen `quantfut-tenis:5b3040b` + crontab de `qf` (PR #153 `9231dbe`, PR #155 `5b3040b`)
- Estado previo comprobado: imagen activa `quantfut-tenis:f391b1f`, `vps_run.sh` igual al de la imagen; `propline_shared.py` de la imagen (`d95d4661…`) anterior a los cierres de PropLine, la nueva lleva el de `main` (`54387ff6…`, tiene `read_closing`).
- Imagen construida desde `git archive 5b3040b:apps/tennis` con `core.autocrlf=false` más `src/qf/ingest/propline_shared.py` de `5b3040b` (`~/quantfut-tenis/build/5b3040b/ctx`). Hubo una intermedia `quantfut-tenis:9231dbe` (19:28 UTC, solo PR #153).
- `vps_run.sh` nuevo (sha256 `2119c1f4…`, igual a `main`): modo `hourly` con `flock`; el calendario de API-Tennis solo en las pasadas de las 00 y 12 UTC (`date -u`), el resto `--no-capture`.
- Crontab: `30 0,12 * * * … twice-daily` → `25 * * * * /home/qf/quantfut-tenis/vps_run.sh hourly` (la línea `weekly` no cambia). Motivo: tras el cambio de horario la pasada de las 00:30 de Berlín caía a las 23:30 UTC, sin foto de PropLine (cupo diario agotado), y 15 partidos se sellaron sin precio.
- Pasada manual 19:28 UTC: código 0, 0 sellados (3 en espera de su ventana), evaluación al día. Ensayo con el archivo real: 41-48 líneas por partido en `market_board`.
- Respaldos en `~/quantfut-tenis/backup/20261026-auditoria/`: `vps_run.sh`, `IMAGE` (`f391b1f`), `motor_config.json`, `crontab.txt`.
- **Vuelta atrás:** `B=~/quantfut-tenis/backup/20261026-auditoria; cp -p $B/vps_run.sh $B/IMAGE ~/quantfut-tenis/ && crontab $B/crontab.txt`. Los sellados nuevos se quedan.

### 2026-10-26 14:33 UTC · Cron del worker sin reentrenamientos del Motor A · solo `scripts/crontab` (`main` `6bce572`, PR #150), sin imagen ni recreación
- **Motivo:** orden del titular: el Motor A se entrena en local y se sube; el servidor no entrena. Comentados («RETIRADO») el mensual `0 3 1 * *` y el arranque diario `--bootstrap`.
- **Estado previo comprobado (14:32 UTC):** `scripts/crontab` del servidor e instalado = `e3e8a7b0…` (entrada de las 01:41); worker `98bdfcc-pitido-ef6f4b3`; nadie más desplegando.
- **Hecho:** `scripts/crontab` = `main` (`f08504f1…`) e instalado con `docker exec -i quantfut-worker-1 crontab - < scripts/crontab`: 28 tareas, 0 de entrenamiento. Pasada de las 14:35 (vivo y sello tardío) normal.
- **Trampa vista:** sustituí el archivo con `mv`; el contenedor monta el archivo por inodo y siguió viendo el viejo en `/etc/cron.d/quantfut`, así que `crontab /etc/cron.d/quantfut` reinstaló lo viejo. Para cambiar el cron sin recrear: escribir encima (`cp`, `cat >`) o instalar por stdin como arriba. En la próxima recreación el contenedor montará el archivo nuevo, que es `main`.
- Respaldo: `~/quantfut/backups/20261026-cron-sin-entreno/` (`crontab.antes`, `crontab_instalado.antes`).
- **Vuelta atrás:** `docker exec -i quantfut-worker-1 crontab - < ~/quantfut/backups/20261026-cron-sin-entreno/crontab_instalado.antes` y `cp ~/quantfut/backups/20261026-cron-sin-entreno/crontab.antes ~/quantfut/scripts/crontab`.

### 2026-10-26 02:12 UTC · Modelo del Motor A `2026.10.26-020600`, entrenado en local y subido · solo datos (`model_artifacts`, `calibration_runs`) y 11 artefactos en `/srv/quantfut/artifacts`, sin imágenes, código ni cron
- **Motivo:** el titular pidió reentrenar ya y fijó que **el entrenamiento se hace en local y luego se sube**. Un entrenamiento lanzado antes en el worker (01:59 UTC) se detuvo a las 02:00, en la validación walk-forward, sin haber escrito nada.
- **Estado previo comprobado:** activo `2026.10.22-185314`; nadie desplegando (entrada de las 01:41 de esta misma sesión).
- **Copia local:** `scripts/entrenamiento_local/copiar.sh` (pg_dump de solo lectura del esquema y de las 19 tablas que lee `qf.model.train`, 26 MB comprimidos) y `preparar.py` (esquema `entreno` de la base local, sin FK; 93.257 partidos, 1,08 M cuotas, último terminado 25-oct 23:00 UTC). xG: SofaScore frente a FotMob en los mismos partidos, cociente 0,994 y correlación 0,999 (misma escala; no hace falta corregir).
- **Entrenamiento (`entrenar.sh`, `main` `6dae4c1`):** configuración del worker de producción (`DECAY_HALFLIFE_DAYS=270`; el `.env` local tenía 180), Telegram y Sentry apagados. 2 min. Validación RPS 0,20370 (mercado 0,19409, n=2.045); gana a Elo, mercado sharp reciente, converge; calibración descartada (no mejora fuera de muestra, igual que la del 22-oct); residuo validado; 49.553 partidos, 13 ligas. Comparado además con el modelo anterior en los **4.161 partidos fuera de muestra comunes**: RPS 0,20597 frente a 0,20611 y log-loss 1,00912 frente a 1,00963 (mejor en las dos, por poco).
- **Subida (`exportar.py`, `subir.sh`, `registrar.py`):** 11 artefactos copiados al volumen sin pisar ninguno; ensayo dentro del worker (hashes iguales, el modelo carga, `converged True`) y después, en una transacción, `model_artifacts` con el nuevo activo y su `calibration_runs` (rutas `.local/…` reescritas a `/srv/quantfut/artifacts/…`).
- **Verificado:** por el camino del job diario (`daily._active_artifact`, calibrador, residuo y mezcla): carga `2026.10.26-020600` y predice (Tijuana–Santos 1,52-1,20). Primera predicción real: el sello tardío de las 02:35 selló Tijuana–Santos con `2026.10.26-020600` (lote por partido, `chain=fba50bf2…`), sin fallos.
- **Ojo:** el cron del worker sigue teniendo el reentrenamiento mensual en el servidor (`0 3 1 * *`, el 1-nov) y el `--bootstrap` diario (solo entrena sin modelo activo). Con la regla nueva, el del 1-nov debería hacerse en local: pendiente de que el titular confirme quitarlo del cron.
- Respaldo: `~/quantfut/backups/20261026-modelo-local/` (`model_artifacts_antes.txt`, `subida_2026.10.26-020600.json`, `registrar.py`).
- **Vuelta atrás:** `docker compose exec -T db psql -U qf -d quantfut -c "BEGIN; UPDATE model_artifacts SET is_active=FALSE WHERE model_version='2026.10.26-020600'; UPDATE model_artifacts SET is_active=TRUE WHERE model_version='2026.10.22-185314'; COMMIT;"`. Las predicciones ya selladas con el nuevo se quedan (inmutables) y llevan su `model_version`.

### 2026-10-26 01:41 UTC · Resultado al pitido con FotMob · worker `quantfut-worker-propline:98bdfcc-pitido-ef6f4b3` (`main` `ef6f4b3`, PR #137) + cron
- **Motivo:** orden del titular (25-oct): la app muestra el marcador final al pitido y el resultado se cierra con la primera fuente disponible. #137 llevaba fusionado desde las 20:56 UTC **sin desplegar** (lo anotó la entrada de las 23:05).
- **Estado previo comprobado (01:40 UTC):** worker `98bdfcc-alta-a53dfd3` y API `98bdfcc-app-8c57b05` (entradas de 23:39 y 00:53). Nadie más desplegando (sin sesiones ssh, builds ni Python en el worker; sin captura de PropLine). `scripts/crontab` instalado = `d856401d…`; el de `main` solo difiere en mis líneas (vivo y respaldo de resultados).
- **Worker:** imagen `FROM quantfut-worker-propline:98bdfcc-alta-a53dfd3` + solo `fotmob_captura.py` (`9099a3fa…`) y `live.py` (`4bc737e7…`) de `main` (`~/quantfut/build/pitido-ef6f4b3`); comparada con el worker en marcha, difiere en esos dos archivos y en ningún otro. Compose: solo cambia la etiqueta del worker. `scripts/crontab` = `main` (`e3e8a7b0…`): el respaldo `fotmob_captura resultados` pasa a cada hora (`55 * * * *`) y a las 2 h 30 min del saque. API sin tocar.
- **Verificado:** pasada real del vivo de las 01:45 UTC: 2 partidos cerrados con FotMob (River–Racing 1-0, Atlas–Puebla 4-3, ambos de anoche, recogidos en la primera pasada) y 1 alta probabilidad liquidada; `/health` 200.
- **Incidencia propia, sin efecto en producción:** a las 01:38 UTC lancé el despliegue con imágenes construidas a las 20:56 sobre la base `98bdfcc`, sin volver a leer el compose del servidor, que otras sesiones habían cambiado entretanto. El `sed` dejó en `docker-compose.yml` etiquetas inexistentes (`…ef6f4b3-app-8c57b05`) y copié mi `crontab` encima del del servidor. `docker compose up` falló al resolver la imagen **antes de parar nada** (API y worker siguieron arriba: 46 min y 2 h). A las 01:39 devolví el compose a las etiquetas que corrían y el `crontab` al instalado; las imágenes `quantfut-{worker,api}-propline:ef6f4b3` (base vieja) no se usan y habrían pisado el trabajo de las otras sesiones. Lección: releer compose y contenedores justo antes de recrear, y construir siempre sobre la imagen que corre.
- **Distinto de `main` en el worker (de otras sesiones, no es mío):** `partido_mercados.py`, `parley_datos.py`, `alta_prob.py` (#146, textos de la API) y `propline_shared.py` (recolector).
- Respaldo: `~/quantfut/backups/20261025-resultado-pitido/` (`docker-compose.yml.antes-despliegue`, `crontab.antes-despliegue`, `fotmob_captura.antes.py`, `live.antes.py`, `worker_image.txt`; más `docker-compose.roto-mio-0139.yml` y `crontab.mio-ef6f4b3` de la incidencia).
- **Vuelta atrás** (fuera de :07-:25): `B=~/quantfut/backups/20261025-resultado-pitido; cp -p $B/docker-compose.yml.antes-despliegue ~/quantfut/docker-compose.yml && cp -p $B/crontab.antes-despliegue ~/quantfut/scripts/crontab && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker`. Los partidos ya cerrados se quedan (resultados inmutables).

### 2026-10-26 00:53 UTC · API: mercados del partido y patas del Parley desde `main` · API `quantfut-api-propline:98bdfcc-app-8c57b05` (`main` `f227fd9`, PR #146)
- **Motivo:** auditoría de la app (`harness/progreso.md`, 25-oct): la fila de un pick abierto enseñaba otra probabilidad que el destacado (76 % frente a 79 %), un pick gratis de lado distinto al del análisis desaparecía de «Mercados del partido», y las patas del Parley no traían `selection`/`line` (la app no podía traducirlas).
- **Estado previo comprobado (00:52 UTC):** API `98bdfcc`; `partido_mercados.py` `b396d4bf…`, `parley_datos.py` `f9788ab4…` y `alta_prob.py` `f59a8832…` = `main` `bf1204e`; worker `98bdfcc-alta-a53dfd3` sin tocar; nadie más desplegando.
- **API:** imagen `FROM quantfut-api-propline:98bdfcc` + solo esos tres archivos de `git archive` (sha256 `276ca189…`, `dfdc1b53…`, `baee7a8b…`, idénticos a `main` `f227fd9`). Ensayo previo en contenedor desechable sin puertos: Barcelona–Real Madrid y Central Córdoba–Vélez con una sola probabilidad por selección y el pick gratis presente en la lista; pata del Parley con `market/selection/line`. Compose: solo cambia la etiqueta de la API; recreado solo `api`.
- **Verificado en el dominio real:** `/health`, `/parley`, `/mobile/v1/home`, `/mobile/v1/config`, `/model-card` y `/mobile/v1/markets/history` 200; ficha de Barcelona–Real Madrid con «Barcelona o empate» 75 % cuota 1,29 en la lista; sin errores en el registro de la API.
- **No incluye:** el APK `1.0.0+4` (la app lee estos datos igual con la versión anterior; los textos nuevos llegan al compilarlo).
- Respaldo: `~/quantfut/backups/20261026-api-app-auditoria/` (`docker-compose.yml`, `api_image.txt`).
- **Vuelta atrás:** `cp -p ~/quantfut/backups/20261026-api-app-auditoria/docker-compose.yml ~/quantfut/ && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate api` (vuelve a `98bdfcc`; la imagen sigue en el servidor).

### 2026-10-25 23:39 UTC · Alta probabilidad solo con cuota · worker `quantfut-worker-propline:98bdfcc-alta-a53dfd3` (`main` `a53dfd3`, PR #142)
- **Motivo:** el 25-oct se sellaron 18 de 22 pronósticos de alta probabilidad (323 de 385 en la ampliada) sin cuota. La selección tomaba la última captura de PropLine, que casi siempre trae solo a Pinnacle, y el modelo proponía líneas que nadie cotiza. Orden del titular: no publicar nada sin cuota y desplegar antes de la selección diaria (`qf.publish.daily`, 09:00 UTC).
- **Estado previo comprobado (23:35 UTC):** worker `98bdfcc-tarjetas-3b8e342` (entrada de abajo; la sesión que lo desplegó confirmó que había terminado). `alta_prob_datos.py`, `alta_prob_ext.py` y `escalera_datos.py` en el worker = `main` `a3b7168` (antes del #142). Ningún proceso Python ni captura de PropLine en marcha. Sin reentrenamiento hoy.
- **Worker (23:39):** imagen `FROM quantfut-worker-propline:98bdfcc-tarjetas-3b8e342` + solo esos tres archivos de `git archive a53dfd3` (`~/quantfut/build/a53dfd3-alta`; sha256 `1203a370…`, `90fa1b52…`, `c196ae2a…`). Compose: solo cambia la etiqueta del worker. Recreado con `docker compose up -d --no-deps --no-build --force-recreate worker`, fuera de :07-:25.
- **No se subió `src/` completo de `main`:** siguen sin desplegar `ingest/fotmob_captura.py` y `ingest/live.py` (#137) e `ingest/propline_shared.py` (#138), igual que antes de este cambio. Queda pendiente decidir su despliegue.
- **Ensayo previo** en un contenedor desechable con la imagen nueva (con el volumen `artifacts` en solo lectura; sin él, `provider.json` no se lee y el proveedor cae a `the_odds_api`): repetida la selección del 25-oct en seco, alta 27/27 con cuota (desplegado: 5/28), ampliada 303/303 (desplegado: 62/385). **Verificado tras el cambio:** imagen y hashes en el contenedor, `odds_provider=propline`, módulos de `daily` importan y cron cargado.
- Respaldo: `~/quantfut/backups/20261026-alta-solo-cuota/` (`docker-compose.yml`, `worker_image.txt`, `antes/` con los tres archivos anteriores).
- **Vuelta atrás** (fuera de :07-:25): `cp -p ~/quantfut/backups/20261026-alta-solo-cuota/docker-compose.yml ~/quantfut/ && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker` (vuelve a `98bdfcc-tarjetas-3b8e342`). Lo que se selle antes de volver atrás se queda: las tablas son inmutables.

### 2026-10-25 23:05–23:27 UTC · Tarjetas a cero de FotMob: reparación de datos + worker `quantfut-worker-propline:98bdfcc-tarjetas-3b8e342` (`main` `3b8e342`, PR #140 y #141)
- **Motivo:** el titular vio «menos de 6,5 tarjetas» al 100 % (media 1,7) en Independiente–Boca. FotMob deja las amarillas del bloque de estadísticas en `[0, 0]` en Argentina, Brasil y parte de México (2026) aunque la cronología trae cada tarjeta; `archivo_a_matches` las guardó como dato. Orden del titular: corregir, reparar con respaldo y anotar aquí.
- **Estado previo comprobado:** worker y API `98bdfcc` (= entrada de las 19:30). `main` tenía además #137 (resultado al pitido: `fotmob_captura.py`, `live.py`) y el `propline_shared.py` de #138, **sin desplegar y sin entrada aquí**. No se suben con este cambio: la imagen es `FROM quantfut-worker-propline:98bdfcc` + solo `src/qf/ingest/archivo_a_matches.py` de `main` `3b8e342` (sha256 `5c39bf50…`). `scripts/deploy.sh estado` después: worker distinto a `main` solo en esos 3 archivos ajenos; la API sigue con el `archivo_a_matches.py` anterior, que no ejecuta (lo usa el worker).
- **Datos (base, tabla `matches`):** `qf.ingest.archivo_a_matches` `reparar_tarjetas()` con el archivo de `main`, en dos pasadas: 607 partidos con las cuatro a cero (`84beeac`, PR #140) y 169 con amarillas a cero y alguna roja (`3b8e342`, PR #141). 0 a NULL, 0 sin original; 150 sin cambio (la cronología tampoco tiene amarillas). Medias de tarjetas por trimestre de 2026: Argentina de 0,2–0,6 a 4,6–5,3; Brasil de ~0,5 a 4,6–5,1; México 3,9–4,8. Independiente–Boca: media 4,7, «menos de 6,5» 80 % (calculado en un proceso nuevo; la API refresca su caché del modelo de tarjetas en ≤ 1 h).
- **Worker (23:26):** recreado con `docker compose up -d --no-deps --no-build --force-recreate worker` fuera de :07-:25, sin trabajos de Python en curso; `docker-compose.yml` solo cambia la etiqueta del worker. Hash del archivo verificado dentro; pasada de `fotmob_captura previos` de las 23:30 sin errores; API local 200.
- Respaldos: `~/quantfut/backups/20261025-tarjetas-fotmob/` (`docker-compose.yml`, `worker_image.txt`, `tarjetas_antes.csv` con las 741 filas de la 1.ª pasada, `tarjetas_antes_pasada2.csv` con las 319 de la 2.ª, e informes `reparacion_informe*.json` con cada cambio).
- **Vuelta atrás:** worker: `B=~/quantfut/backups/20261025-tarjetas-fotmob; cp -p $B/docker-compose.yml ~/quantfut/ && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker`. Datos (solo si hiciera falta; vuelve a dejar los ceros falsos): cargar `tarjetas_antes_pasada2.csv` y luego `tarjetas_antes.csv` en una tabla temporal y `UPDATE matches m SET home_yellow=t.home_yellow, away_yellow=t.away_yellow, home_red=t.home_red, away_red=t.away_red FROM t WHERE m.match_id=t.match_id`, primero la 2.ª y después la 1.ª.
- **Pendiente ajeno:** desplegar #137 y el `propline_shared.py` de #138 (o decidir no hacerlo); este despliegue no los incluye.

### 2026-10-25 21:34–22:20 UTC · NBA: productor 1.4b completado, panel `20261025c`, recolector PropLine `a6dcb96` y retiro de `price.sh` · `main` `a6dcb96` (PR #138)
- **Motivo:** tercera auditoría NBA pedida por el titular con la orden de corregir y desplegar en el momento (`docs/nba_auditoria_20261025.md`).
- **Estado previo comprobado (21:06 UTC):** panel `nba-dashboard-live13:20261025b` (cambiado hacia las 02:00 UTC del 25-oct **sin entrada en este registro**: el despliegue 1.4b de #114 quedó a medias); productor `producer.sh` con `nba-live13-producer:20261025`, datos RUN071 (`players` `3c37c3d0…`) y modelo 1.4.0 (`78473e54…`); preparados sin activar `data.next-20261025b` y `model.next-20261025b`. Recolector `releases/3ea6e4c`. Otra sesión preparaba el worker/API `ef6f4b3` (no se tocó).
- **Productor (21:34):** ensayo previo con la hora real (21:32) sobre los 3 partidos de las 23:00 UTC en carpetas temporales: 362 pronósticos, igual que el 1.4.0 real. Cambio: `data` ← `data.next-20261025b` (`players` `e5326b7f…`, `games` `c2c13b36…`), `model` ← `model.next-20261025b` (`5314c9ef…`, mismo módulo `20c2adb3…`), `producer.sh` con la imagen `nba-live13-producer:20261025b` (código NBA = `main`) y `--memory 1g` (1.4b pica ~573 MB). Pasada manual 21:34 sin errores. **Verificado:** cohorte `2026-10-25_1800` (22:00 UTC) con el modelo `5314c9ef`, 77 pronósticos, hándicap y total presentes.
- **Panel (22:12):** imagen `nba-dashboard-live13:20261025c` (`562b7554…`, `FROM nba-dashboard-live13:20261021` + `src/nba` y `web` de `git archive a6dcb96`; solo cambia `multimarket_live_dashboard.py`). Ensayo previo contra las cohortes reales: 444 evaluados, 0 `validation_hold` (antes 440 y 4). Al cambiar, el nombre `nba-dashboard-run71-prev5` ya existía y `/nba` dio 502 ~45 s; el anterior quedó parado como `nba-dashboard-run71-prev6` (`restart=no`). Después: `/nba` 200, `live_v13` `ok`, 11 cohortes, 0 problemas.
- **Recolector PropLine (22:20):** `~/propline-shared/current` → `releases/a6dcb96` (solo cambia `propline_shared.py` = `main`; configuración, runner y `runtime.json` iguales a `3ea6e4c`). Ensayo sin red con el archivo en solo lectura (módulo y configuración cargan, lector devuelve los 119 eventos NBA). Activado sin captura en marcha. La pasada de las 22:07 ya había llegado a la reserva (499 restantes): la de las 23:07 no capturará y el partido de las 01:00 UTC (Grizzlies–Kings) se sellará sin props; el ahorro rige desde el reinicio de las 00:00 UTC.
- **Cron (21:22):** quitada la línea `*/5 … live13/price.sh` (captura de precios con The Odds API, bloqueada hasta el 1-nov; nunca gastó créditos). PropLine ya trae Pinnacle para NBA.
- Respaldos: `~/nba-isolated/live13/` (`producer.sh.before-20261025c`, `model.before-20261025c`, `data.before-20261025c`, `crontab.before-20261025c`, `dashboard.inspect.before-20261025c.json`, `containers.before-20261025c.txt`); `~/propline-shared/backups/20261025-nba-auditoria/`.
- **Vuelta atrás:** productor: `cd ~/nba-isolated/live13 && cp producer.sh.before-20261025c producer.sh && rm -r model data && cp -a model.before-20261025c model && cp -a data.before-20261025c data`. Panel: `docker rm -f nba-dashboard-run69 && docker rename nba-dashboard-run71-prev6 nba-dashboard-run69 && docker update --restart unless-stopped nba-dashboard-run69 && docker start nba-dashboard-run69`. Recolector: `cd ~/propline-shared && ln -sfn /home/qf/propline-shared/releases/3ea6e4c current.tmp && mv -T current.tmp current`. Cron de precios: `crontab ~/nba-isolated/live13/crontab.before-20261025c`. Las cohortes selladas se quedan.

### 2026-10-25 19:30 UTC · Auditoría de la noche: worker y API desde `main`, recolector PropLine, alias · worker `quantfut-worker-propline:98bdfcc` + API `quantfut-api-propline:98bdfcc` (`main` `98bdfcc`, PR #132 y #133) + release `~/propline-shared/releases/3ea6e4c` (PR #135) + datos (`team_aliases`, `unresolved_names`)
- **Motivo:** auditoría pedida por el titular (`docs/auditoria_motores_datos_20261025_noche.md`), con la orden de arreglar en el momento. La sombra del XI no registraba nada desde el 22-oct (solo `post_xi`); ERA5 rechazado en 175 de 177 celdas al día (peticiones simultáneas); 26 partidos nuestros sin documento de cierre porque la liquidación de fútbol del recolector gastaba el tope en ligas sin motor; la reserva de PropLine cortaba las pasadas de las 22-23 UTC; la API corría código anterior al 22-oct.
- **Estado previo comprobado (19:03 UTC):** worker `d2a1b5e` con 0 archivos distintos de `main` `d7ed031`; API `3babeb4` con **37 distintos y 33 que faltan** (la nota de «Trampas conocidas» decía que solo `config.py`); recolector `releases/2f343ce` idéntico a `main`; `scripts/crontab` = `main` (`d856401d…`, no cambia); nadie más desplegando.
- **Datos (19:04 y 19:28 UTC, una transacción cada uno):** 16 alias (`odds_api` y `propline`) para Tromso IL, Sarpsborg 08, Botafogo FR RJ, New York RB, COL Rapids, Clube Do Remo PA, Cruzeiro MG y LR Vicenza; 9 filas de `unresolved_names` marcadas `resolved` (con SBV Excelsior, que ya resuelve el código nuevo).
- **API (19:16, después 19:30):** imagen `FROM quantfut-api-propline:3babeb4` con `src/` completo de `main` (mismos paquetes que el worker). Ensayo antes del cambio en un contenedor desechable: `/health`, `/mobile/v1/home` y la ficha 200; las 118 rutas son las mismas que en `3babeb4`; la lista de mercados de la ficha, idéntica. Tras el cambio: web, inicio, ficha, `/model-card` y `/mobile/v1/markets/history` 200; `/control` 302; sin errores en el registro.
- **Worker (19:26, después 19:30):** imagen `FROM quantfut-worker-propline:d2a1b5e` con `src/` de `main`, recreado fuera de :07-:25, sin captura de PropLine en marcha y sin trabajos en curso. `scripts/deploy.sh estado`: worker y API con 162/162 `.py` idénticos a `main` `98bdfcc`.
- **Recolector PropLine (19:29 `releases/98bdfcc`; 20:18 `releases/3ea6e4c`):** `propline_shared.py` `ca8079d6…`, config `387ba52e…`, runner `3f4f4745…`, `runtime.json` copiado del vigente (imagen `sin-etiquetas`, entrada de las 17:41). La liquidación de fútbol solo pide nuestras 15 ligas y 2 copas, sin `results`; las competiciones sin motor se capturan cada 6 h (con 3 h, medido en la pasada de las 20:07, la reserva seguía cortando las de la noche).
- **Verificado:** pasada real del recolector de las 20:07: 93 peticiones (antes 150-200), 0 fallos, liquidación solo de las 17 nuestras; quedan 696 del día. Sombra del XI: Barcelona–Real Madrid y Sporting–Académico registrados (base y mercado), las primeras filas desde el 22-oct. ERA5: 74 celdas descargadas y 0 errores a las 20:18 (antes 175 rechazos por pasada). Salud (sin persistir ni alertar) 10 de 11 en verde, y el aviso restante eran nombres nuevos que se dieron de alta; cierres en 79 de 113 jugados; xG en 147/147; SofaScore con previsto en 23/23. La puesta al día de ERA5 sigue en segundo plano con su `flock`. `propline_cierres` manual: carga Guimarães–Marítimo, que no emparejaba.
- Respaldo: `~/quantfut/backups/20261025-auditoria-noche/` (`docker-compose.yml`, `crontab`, `worker_image.txt`, `api_image.txt`, `propline_release_2f343ce/`, `propline_current.txt`, `team_aliases_unresolved.sql`, `alias_insertados.tsv`, `unresolved_marcados.txt`).
- **Vuelta atrás** (fuera de :07-:25): `B=~/quantfut/backups/20261025-auditoria-noche; cp -p $B/docker-compose.yml ~/quantfut/ && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker api`; recolector: `cd ~/propline-shared && ln -sfn /home/qf/propline-shared/releases/2f343ce current.tmp && mv -T current.tmp current` (su `runtime.json` ya apunta a la imagen `sin-etiquetas`); alias: borrar de `team_aliases` las filas de `alias_insertados.tsv` y `UPDATE unresolved_names SET resolved=FALSE WHERE id IN (…unresolved_marcados.txt)`. Lo cargado (cierres, sombra, clima) se queda: son tablas de solo inserción.
### 2026-10-25 17:41 UTC · Captura horaria de PropLine con imagen sin etiquetas de compose · solo `runtime.json` del recolector, sin código ni cron
- **Motivo:** visto bueno del titular para el arreglo de fondo de la trampa del 25-oct 16:22: la imagen `9db4a578…` heredaba las etiquetas `com.docker.compose.*` del servicio worker, y `docker compose up --force-recreate worker` (y `docker compose cp worker`) tomaba la captura por una réplica del worker y la mataba a mitad de pasada.
- **Estado previo comprobado (17:41 UTC):** ninguna captura en marcha; `~/propline-shared/current` → `releases/2f343ce`, `runtime.json` con `sha256:9db4a578…`.
- **Hecho:** imagen `propline-shared-capture:sin-etiquetas` (`sha256:0599acdba462…`) = `FROM` la anterior (etiquetada `propline-shared-capture:base-9db4a578`) con las once etiquetas `com.docker.compose.*` vacías; mismo Python 3.12.15. `runtime.json` de `releases/2f343ce` apunta a ella (escritura atómica, mismos campos). Código del recolector, configuración y cron sin cambios.
- **Verificado:** pasada de las 18:07 UTC con la imagen `0599acdba462` (visto en `docker ps` a las 18:15), 196 peticiones, 0 fallos, código 0. Pasada de las 19:07: 150 peticiones, un 504 de PropLine en `basketball_nba/odds` (error del proveedor) y código 1; el resto, 200.
- **Presupuesto (dato, sin cambio):** a las 19:14 UTC quedaban 790 de 5.000 peticiones diarias con ~150-200 por pasada: la captura llegará a la reserva de 500 antes de medianoche y se detendrá sola (`account_reserve`), como ya prevé el recolector.
- Respaldo: `~/quantfut/backups/20261025-vivo-clasificacion/propline_runtime_antes_cambio.json`.
- **Vuelta atrás** (fuera de :07-:25): `cp -p ~/quantfut/backups/20261025-vivo-clasificacion/propline_runtime_antes_cambio.json ~/propline-shared/releases/2f343ce/runtime.json`. La imagen anterior sigue en el servidor (`propline-shared-capture:base-9db4a578`).

### 2026-10-25 17:35 UTC · Clasificación calculada y marcador en vivo de FotMob · worker `quantfut-worker-propline:d2a1b5e` (`main` `d2a1b5e`, PR #130) + cron + carpeta `~/quantfut`
- **Motivo:** orden del titular («limpia y arregla»): clasificación y marcador en vivo estaban parados desde el 22-oct (API-Football). La clasificación se calcula con nuestros resultados; el vivo sale del listado diario de FotMob (una petición cada 5 min).
- **Estado previo comprobado (17:34 UTC):** worker `ffe42ee` (= entrada anterior), `scripts/crontab` = `main` anterior (`beab2c30…`); ninguna captura de PropLine en marcha; nadie más desplegando.
- **Worker:** imagen `FROM quantfut-worker-propline:ffe42ee` + `src/` de `git archive d2a1b5e` (`~/quantfut/build/d2a1b5e`); 162/162 `.py` idénticos a `main`. Compose con la etiqueta `d2a1b5e`. `scripts/crontab` = `main` (`d856401d…`): `qf.ingest.standings` cada hora a las :50 y `qf.ingest.live` cada 5 min. Recreado fuera de :07-:25 y sin captura en marcha (trampa de abajo): sin incidencias.
- **Carpeta del servidor:** `~/quantfut/src`, `requirements.txt`, `requirements-dev.txt` y `Dockerfile` = `main` `d2a1b5e` (162/162 `.py`). Quedan 6 `.pyc` de root en `src/qf/__pycache__` y `src/qf/ingest/__pycache__` que `qf` no puede borrar; Python los ignora al no coincidir con su fuente.
- **Ensayo previo sin escrituras (≈17:20 UTC):** vivo 36 candidatos, 20 en juego enlazados; clasificación de las 19 ligas; contra la foto de API-Football del 22-oct 06:40 coincide equipo a equipo salvo Southampton (−4, en `SANCIONES`).
- **Verificado:** pasadas reales 17:36 UTC: vivo 18 en juego; clasificación 19 ligas (406 filas antes, mismas ligas). En `https://pronosticosdeportivos.pro/mobile/v1/matches/gb.premier_league:2627:sunderland-leeds:20261025`: vivo 0-0, minuto 50, `2H`; tabla de 20 equipos actualizada a las 17:36. API sin tocar (`3babeb4`).
- Respaldo: `~/quantfut/backups/20261025-vivo-clasificacion/` (`docker-compose.yml`, `crontab`, `worker_image.txt`, `src_servidor.tgz`, `requirements*.txt`, `Dockerfile`, `standings_antes.csv`, `propline_runtime.json`).
- **Vuelta atrás** (fuera de :07-:25): `B=~/quantfut/backups/20261025-vivo-clasificacion; cp -p $B/docker-compose.yml ~/quantfut/ && cp -p $B/crontab ~/quantfut/scripts/crontab && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker`. La tabla anterior: `\copy standings FROM` de `standings_antes.csv` tras vaciarla. La carpeta: `rm -rf src && tar -xzf $B/src_servidor.tgz` (no hace falta: no la monta ningún contenedor).

### 2026-10-25 16:22 UTC · Cierres de PropLine, Liga MX/MLS en SofaScore y `stats` · worker `quantfut-worker-propline:ffe42ee` (`main` `ffe42ee`, PR #127) + cron + recolector SofaScore
- **Motivo:** auditoría de datos (`docs/auditoria_datos_motores_20261025.md`, PR #125): sin cierres desde el 22-oct 18:50 aunque PropLine los archiva; MLS y Liga MX sin ningún partido en SofaScore; `matches.stats` vacío desde el 22-oct. Orden del titular: fusionar #125 y #127, desplegar worker, cron y recolector con respaldo, cargar los cierres y verificar.
- **Estado previo comprobado (16:20 UTC):** worker `2db3f61` (= entrada anterior) con 161/161 `.py` idénticos a `main`; `scripts/crontab` (`8e7ad146…`), `config.json` (`9304fda1…`) y `sofascore_apify.py` (`4960defa…`) del recolector = `main`; ningún trabajo en curso en el worker; nadie más desplegando. La 088 sigue programada en el cron del host (01:30 UTC del 26-oct) y no se toca.
- **Worker:** imagen `FROM quantfut-worker-propline:2db3f61` + `src/` de `git archive ffe42ee` (`~/quantfut/build/ffe42ee`); `.py` idénticos a `main`. Compose con la etiqueta `ffe42ee`. `scripts/crontab` = `main` (`beab2c30…`): suma `propline_cierres` a las :40 cada 3 h.
- **Recolector SofaScore:** `config.json` (`a1ae2f77…`, Liga MX al Apertura `11621`) y `sofascore_apify.py` (`26ba76f2…`, competiciones sin jornada) = `main`.
- **Incidencia:** `docker compose up --force-recreate worker` tomó por réplica del worker el contenedor de la captura horaria de PropLine (`propline-shared-capture`, que corría desde las 16:07) y lo mató: la pasada de las 16:07 terminó con código 137 (lo recibido hasta entonces queda archivado; la siguiente es a las 17:07). El worker quedó en «Created» con nombre temporal: se arrancó con `docker compose up -d --no-deps --no-build worker` y se renombró a `quantfut-worker-1`. Ver «Trampas conocidas».
- **Verificado:** `propline_cierres` real 16:24 UTC: 79 partidos y 25.437 filas de 17 ligas (Pinnacle 1X2, hándicap, goles, córners, tarjetas, totales por equipo, ambos marcan, doble oportunidad), un solo `captured_at` por partido, 0–9 min antes del inicio. Último partido con cierre sharp: 22-oct → 25-oct 03:00 (frescura del reentrenamiento). Desde el 22-oct, 89 de 132 terminados con cierre. Las ofertas de esos partidos ya estaban liquidadas sin cierre (inmutable): no ganan CLV; las nuevas esperan al cierre hasta 48 h. Recolector SofaScore (pasada manual 16:25–16:31, 1,14 USD): MLS 111 partidos descubiertos (antes 0), Liga MX 9 (antes 0); tras cargar: MLS 13/14 con xG y 14/14 con tarjetas, árbitro y `stats`; Liga MX 10/10. `stats` rellenado en 80 partidos ya cargados; 107 de 132 desde el 22-oct.
- Respaldo: `~/quantfut/backups/20261025-cierres-propline/` (`docker-compose.yml`, `crontab`, `sofascore_current/`, `worker_image.txt`).
- **Vuelta atrás** (fuera de :07–:25 por la trampa de abajo): `B=~/quantfut/backups/20261025-cierres-propline; cp -p $B/docker-compose.yml ~/quantfut/ && cp -p $B/crontab ~/quantfut/scripts/crontab && cp -p $B/sofascore_current/config.json $B/sofascore_current/sofascore_apify.py ~/sofascore-apify/current/ && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker`. Las filas de cierre (`window_tag='close'`, `source='propline'`) son inmutables y se quedan; con el código anterior no se cargan más.

### 2026-10-25 15:20 UTC · Respaldo de resultados con FotMob · worker `quantfut-worker-propline:2db3f61` (`main` `2db3f61`, PR #123) + cron
- **Motivo:** 19 partidos de ligas activas seguían abiertos más de 6 h después del saque porque PropLine no les dio resultado (`expired`: liga suiza entera y partidos sueltos de Serie B, LaLiga 2, Noruega, Turquía, MLS y Europa League). Hoffenheim–Lyon (UEL, 22-oct) tenía alta probabilidad, escalera y parley sin liquidar. Orden del titular: fusionar, desplegar y cerrar los atascados.
- **Estado previo comprobado:** worker `e5a29a7` (= entrada anterior) y `scripts/crontab` = `main` (`d874a026…`); nadie más había desplegado.
- **Worker:** imagen `FROM quantfut-worker-propline:e5a29a7` + `src/` de `git archive 7e27331` (árbol idéntico a `main` `2db3f61` tras el squash; etiquetada también `2db3f61`); 161/161 `.py` idénticos. Compose con la etiqueta `2db3f61`. `scripts/crontab` = `main` (`8e7ad146…`): suma `fotmob_captura resultados` cada 3 h a las :55.
- **Ensayo de solo lectura antes de cerrar:** 18 de 18 candidatos con página FotMob del mismo partido, terminados en el tiempo reglamentario (FT) y con los dos equipos en el mismo orden.
- **Verificado (pasada manual 15:23 UTC):** 18 cerrados, 0 abiertos, 0 equipos distintos; liquidación encadenada: alta probabilidad 1 (Hoffenheim–Lyon, ganada), escalera 1 (perdida, 3-0), sombra sharp 23, sombra XI 2. 0 partidos atascados después. La pata de parley de Hoffenheim–Lyon ya se había anulado a las 02:24 UTC por el margen de aplazado y se queda así (inmutable); el ticket ya estaba perdido por la otra pata (Juventus–Rennes 2-2).
- Respaldo: `~/quantfut/backups/20261025-resultados-fotmob/` (`docker-compose.yml`, `crontab`, `worker_image.txt`).
- **Vuelta atrás:** `B=~/quantfut/backups/20261025-resultados-fotmob; cp -p $B/docker-compose.yml ~/quantfut/ && cp -p $B/crontab ~/quantfut/scripts/crontab && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker`. Los cierres y liquidaciones hechos se quedan (resultados inmutables); cada cierre lleva `external_ids.fotmob` y su página en `fotmob_original`.

### 2026-10-25 15:00 UTC · Retiro de 4 ligas y FotMob como complemento diario · worker `quantfut-worker-propline:e5a29a7` (`main` `e5a29a7`, PR #121) + cron + recolector SofaScore; migración 088 programada
- **Motivo:** orden del titular tras `docs/cobertura_ligas_propline_sofascore_20261025.md`: quedan 15 ligas + 2 copas; fuera Serie B, LaLiga 2, Allsvenskan y Super League suiza; FotMob vuelve como complemento diario.
- **Estado previo comprobado:** worker `117feb7` con 0 archivos distintos de `main` salvo los dos del PR; `scripts/crontab` (`8c8c0493…`), `config.json` del recolector (`bc054cb0…`) y `sofascore_apify.py` (`4960defa…`) iguales a `main`; nadie más había desplegado.
- **Worker:** imagen `FROM quantfut-worker-propline:117feb7` + `src/` de `git archive e5a29a7` (`~/quantfut/build/e5a29a7`); 161/161 `.py` idénticos a `main`. Compose con la etiqueta `e5a29a7`. `scripts/crontab` = `main` (`d874a026…`): vuelven `fotmob_captura referencias/previos/posteriores` y `sedes`, y entra `fotmob_captura completar` a las 09:15 UTC.
- **Recolector SofaScore:** `config.json` = `main` (`9304fda1…`): suma Championship (18), 2. Bundesliga (44), Süper Lig (52) y Eliteserien (20). El script no cambia.
- **Verificado:** primera pasada FotMob: `referencias` 17 competiciones (ninguna retirada), 6 nuevas; `posteriores` 60 guardados, 0 descartados; `completar` 222 partidos rellenados (18 con xG), 0 conflictos de marcador. 507 de 509 partidos activos de −4 a +12 días tienen referencia FotMob.
- **Migración 088, aplazada a propósito:** `results.py` solo cierra partidos de ligas activas y había productos de hoy en esas ligas (5 alta probabilidad, 1 paso de escalera, 1 pata de parley). Cron del host de una sola vez `30 2 26 10 *` (hora del host, CET = 01:30 UTC del 26-oct; movida a las 16:15 UTC desde las 22:30 UTC para que el respaldo de FotMob de las 00:55 UTC pueda cerrar Verona–Pisa, 16:15 UTC, con una pata de parley, si PropLine no lo cierra): `~/quantfut/deployments/20261025-088/aplicar_088.sh` registra en `sin_liquidar.txt` los productos que sigan sin cerrar, aplica `088.sql`, avisa por Telegram de alertas y se quita del cron. Ensayada antes con ROLLBACK (4 filas). Thun–Lugano no se liquidará de ninguna forma: PropLine no da resultados de la liga suiza (`expired`).
- Respaldos: `~/quantfut/backups/20261025-retiro-ligas-fotmob/` (`docker-compose.yml`, `crontab`, `crontab_qf.txt`, `sofascore_current/`, `worker_image.txt`, `leagues_antes.tsv`).
- **Vuelta atrás:** `B=~/quantfut/backups/20261025-retiro-ligas-fotmob; cp -p $B/docker-compose.yml ~/quantfut/ && cp -p $B/crontab ~/quantfut/scripts/crontab && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker`; `cp -p $B/sofascore_current/* ~/sofascore-apify/current/`; `crontab $B/crontab_qf.txt` (quita también la 088 si aún no corrió). 088 se revierte con `UPDATE leagues SET active=TRUE, model_enabled=FALSE, captura_completa=FALSE WHERE league_id IN ('it.serie_b','es.laliga2','se.allsvenskan','ch.super_league')` (los valores previos están en `leagues_antes.tsv`). Lo rellenado por `completar` solo ocupó NULL y queda en `matches_enriquecimiento` (`provider='fotmob'`).

### 2026-10-25 13:36 UTC · Alias de PropLine para el lector de cuotas · solo datos (`team_aliases`, `unresolved_names`), sin imágenes, código ni cron
- **Motivo:** auditoría del 25-oct (`docs/auditoria_motores_20261025.md`): PropLine trae los partidos, pero 19 de 63 de la corrida del 25-oct se quedaron sin precio del Motor B (Inter–Fiorentina, Lecce–Juventus, River–Racing, Independiente–Boca…). Causa: el calendario y los resultados de PropLine aprenden alias con fuente `propline` (`propline_partidos.APRENDIDO`), pero el lector de cuotas (`odds_worker.match_events`) solo consulta `odds_api`. Orden del titular: dar de alta los alias de las ligas activas revisados a mano. La corrida de las 09:00 UTC ya había pasado cuando llegó la orden (28 de alta probabilidad, 19 sin precio).
- **Estado previo comprobado:** worker `117feb7` (= entrada anterior), nadie más había desplegado; 420 alias `odds_api`, 169 `propline`; ningún alias nuevo chocaba con uno existente.
- **Hecho (una transacción, `ON CONFLICT DO NOTHING`):** 150 alias `odds_api` nuevos. 132 son copia de los `propline` ya aprendidos (los 169 revisados uno por uno contra su equipo; los demás ya existían). 18 manuales revisados contra el rival y la fecha del evento de PropLine: Talleres (×2), Instituto, Coritiba (×2), Vitória, Palmeiras, `1. FC Cologne` → FC Koln, `Albacete Balompie`, `Besiktas Istanbul`, `Olympique Lyonnais`, `Stade Rennais` (×2), `SL Benfica`, `Lillestrøm`, `Sarpsborg`, `Aalesunds FK` y `Virtus` → Vicenza Virtus (rival Modena el 27-oct; Virtus Entella juega a la misma hora contra Avellino). Rechazadas las conjeturas del difuso (Lanús → San Luis, Brugge → Brage, Sporting CP → Porto, Cologne → Kaiserslautern). 101 filas de `unresolved_names` marcadas `resolved`.
- **Sin alias a propósito:** clubes de Champions/Europa League fuera del catálogo (Shakhtar, LASK, Celtic, Salzburg, Olympiacos…); por la regla de copas no se dan de alta equipos bajo `eu.ucl`/`eu.uel`.
- **Verificado (solo lectura, contra el archivo de PropLine):** de 277 partidos próximos con archivo, 229 emparejan; todos los de hoy que estaban sin precio emparejan ya. Los 48 restantes son de 29-oct a 2-nov y PropLine aún no los publica, o los publica con otra fecha (reprogramaciones que corrige el calendario). Tras el alta, el sondeo solo deja sin alias a clubes fuera del catálogo. **Pasada real de `odds_worker` 13:40 UTC:** 2.510 filas de 48 partidos que antes no emparejaban (`unmatched_events` 187 → 123); Lecce–Juventus, Castellón–Sporting, Nacional–Braga, Molde–Fredrikstad, Independiente–Boca, Sporting–Académico y River–Racing ya tienen el 1X2 y las líneas de Pinnacle (55-69 filas cada uno). Su pronóstico de alta probabilidad no se recupera hoy: la corrida es una vez al día.
- Respaldo: `~/quantfut/backups/20261025-alias-propline/` (`team_aliases_unresolved.sql` = `pg_dump --data-only` de las dos tablas antes del cambio; `alias_insertados.tsv` y `unresolved_marcados.tsv` = filas exactas del cambio).
- **Vuelta atrás:** `B=~/quantfut/backups/20261025-alias-propline; cd ~/quantfut && cut -f1 $B/alias_insertados.tsv > /tmp/a.txt && cut -f1 $B/unresolved_marcados.tsv > /tmp/u.txt && docker compose cp /tmp/a.txt db:/tmp/a.txt && docker compose cp /tmp/u.txt db:/tmp/u.txt && docker compose exec -T db psql -U qf -d quantfut -c "CREATE TEMP TABLE a(alias text); COPY a FROM '/tmp/a.txt'; CREATE TEMP TABLE u(id bigint); COPY u FROM '/tmp/u.txt'; DELETE FROM team_aliases WHERE source='odds_api' AND alias IN (SELECT alias FROM a); UPDATE unresolved_names SET resolved=FALSE WHERE id IN (SELECT id FROM u);"`. Las cuotas ya importadas con estos alias se quedan (`odds_snapshots` es inmutable).
- **Pendiente:** que `odds_worker` consulte también la fuente `propline` (cambio de código, evita repetir esto con cada nombre nuevo).

### 2026-10-25 04:25 UTC · Bajas y once desde SofaScore · worker `quantfut-worker-propline:117feb7` (`main` `117feb7`, PR #118) + migración 087 + recolector
- **Estado previo comprobado:** worker `ab82dcb`; `src/db/scripts` de `main` sin cambios desde entonces; recolector `a8da9388…` con `config.json` `1861f119…`; nadie más había desplegado.
- **Migración `db/087`** (aditiva; ensayada antes con ROLLBACK): `injuries.source` y `injuries.expected_return`, tabla `lineups_previstas`. 36.489 filas previas en `injuries`, intactas.
- **Worker:** imagen `FROM quantfut-worker-propline:ab82dcb` + `src/` de `git archive 117feb7`; 0 archivos distintos de `main`. Compose con la etiqueta `117feb7`; `scripts/crontab` = `main` (suma `qf.ingest.sofascore_alineaciones` cada 10 min, minutos 3-59/10).
- **Recolector (host):** `sofascore_apify.py` `4960defa0bc4` y `config.json` `bc054cb0e24e` (sección `lineups`). Cron nuevo `*/10` con `flock` (`lineups.lock`) y log `logs/lineups.log`; el diario de las 07:40 no cambia.
- **Verificado:** primera captura real 0,16 USD (40 partidos, previa). Carga: 37 partidos, 193 bajas (con motivo y fecha de regreso), 70 onces previstos, 0 oficiales (aún no había partidos en T-65..T-20). Copia a `lineups` solo para oficial completo; se vigila el primer partido real.
- **Pendiente:** primer once oficial real en `lineups` y que `sello_tardio` lo use; historia de onces SofaScore para que `availability` deje de dar «insuficiente».
- Respaldos: `~/quantfut/backups/20261025-bajas-once/` (`docker-compose.yml`, `crontab`, `crontab_qf.txt`, `sofascore_current/`, `worker_image.txt`).
- **Vuelta atrás:** `B=~/quantfut/backups/20261025-bajas-once; cp -p $B/docker-compose.yml ~/quantfut/ && cp -p $B/crontab ~/quantfut/scripts/crontab && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker`; `cp $B/sofascore_current/* ~/sofascore-apify/current/`; `crontab $B/crontab_qf.txt`. Las columnas/tablas de 087 se pueden dejar (no estorban).

### 2026-10-25 02:23 UTC · Resultados y calendario desde PropLine, xG desde SofaScore, cron sin API-Football ni FotMob · worker `quantfut-worker-propline:ab82dcb` (`main` `ab82dcb`, PR #113 y #115) + migraciones 085/086 + recolectores
- **Motivo:** API-Football en plan gratuito desde el 22-oct (sin resultados ni calendario; 76 partidos sin cerrar) y el worker `a521569` mezclaba versiones (`estadisticas_mercado.py` de `ba66746`, `alta_prob.py` de `8be381b`): el diario del 24-oct no produjo alta probabilidad, escalera ni parley (`AttributeError: … 'disponible'`). Además el crontab montado era del 18-oct y había perdido el sello por partido (F7). Orden del titular: sustituir las fuentes por PropLine y SofaScore y retirar las tareas de API-Football y FotMob.
- Estado previo comprobado: worker `a521569` con 6 archivos distintos de `main` y 1 ausente; `~/propline-shared/current` → `releases/fc20390` (igual a `main` salvo la configuración); `~/sofascore-apify/current` = versión por deporte (rl1987 fútbol, scrapesage NBA y tenis) que no estaba en `main` y que el PR #113 incorporó.
- **Migraciones:** `085_sofascore_detalles.sql` (tabla inmutable con trigger) y `086_retirar_ligue2_superliga.sql` (Ligue 2 y Superliga danesa `active=false`, historial intacto). Respaldo de sus filas de `leagues` y esquema en `~/quantfut/backups/20261025-propline-resultados/`.
- **Worker:** imagen `FROM quantfut-worker-propline:a521569` + `src/` completo de `git archive ab82dcb` (`core.autocrlf=false`); comprobado dentro de la imagen: 160/160 `.py` idénticos a `main`. Compose: etiqueta `ab82dcb` y montaje `/home/qf/sofascore-apify/data:/srv/quantfut/sofascore:ro`. `.env`: `RESULTS_PROVIDER=propline` y `SOFT_BOOKS` con las 10 casas nuevas (la API no se recreó: sigue con las anteriores hasta su próximo despliegue). `scripts/crontab` = `main` (sha256 `9a81ae83…`): 20 tareas activas, 14 comentadas con «RETIRADO» (API-Football, FotMob, PitchAPI, worldfootball/FBref) y vuelven F7, `estado_xi`, `ajuste_xi` y `sofascore_partidos`.
- **Recolectores:** PropLine release `~/propline-shared/releases/2f343ce` (solo cambia la configuración: `/scores` cada 3 h; `runtime.json` copiado de `fc20390`). SofaScore `~/sofascore-apify/current` con `sofascore_apify.py` `a8da9388…` y `config.json` `1861f119…` (13 ligas con modelo + NBA, 15 USD/mes, 40 detalles por pasada, fútbol y lo más reciente primero).
- **Verificado:** primera pasada de resultados: 83 cerrados (78 con córners), liquidados 3 de alta probabilidad, 1 escalera, 2 parleys, 164 ofertas de la sombra (18 con cierre justo). Pasada manual del recolector SofaScore (0,42 USD) y carga: 30 partidos con estadísticas, 25 con xG, **0 conflictos de marcador** con PropLine. Calendario: 280 enlazados, 3 altas, 4 reprogramados, 13 cruces invertidos rechazados. Vista previa del Motor B sin errores. Salud: resultados, cuotas, xG y liquidación al día.
- **Pendiente:** 15 partidos huérfanos (Serie B, LaLiga 2 y Hoffenheim–Lyon: PropLine no trae o escribe distinto sus eventos) y 99 nombres sin emparejar; sin fuente conectada para bajas, once previo, clasificación y marcador en vivo.
- Respaldos: `~/quantfut/backups/20261025-propline-resultados/` (`docker-compose.yml`, `.env`, `crontab`, `worker_image.txt`, `sofascore_current/`, `crontab_qf.txt`) y `~/propline-shared/backups/20261025-2f343ce/`.
- **Vuelta atrás:** `B=~/quantfut/backups/20261025-propline-resultados; cp -p $B/docker-compose.yml $B/.env ~/quantfut/ && cp -p $B/crontab ~/quantfut/scripts/crontab && cd ~/quantfut && docker compose up -d --no-deps --no-build --force-recreate worker` (la imagen `a521569` sigue en el servidor, pero vuelve el fallo del Motor B); PropLine: `cd ~/propline-shared && ln -sfn /home/qf/propline-shared/releases/fc20390 current.tmp && mv -T current.tmp current`; SofaScore: `cp -p $B/sofascore_current/* ~/sofascore-apify/current/`. Las migraciones se dejan: 085 es aditiva; 086 se revierte con `UPDATE leagues SET active=TRUE WHERE league_id IN ('fr.ligue_2','dk.superliga')`. Lo ya cerrado y liquidado se queda (inmutable).

### 2026-10-25 00:31 UTC · NBA: productor y panel 1.4.0 (reentrenado con reportes T-60, entorno del partido y 4 mercados nuevos) · `main` `9808f66` (PR #111)
- Qué cambia: modelo ajustado con los reportes antiguos + T-60, calibración de jugador con el entorno del partido (total y hándicap previos, localía, descanso, minutos) y mercados nuevos de triples, robos, tapones y robos+tapones. Cada pieza validada antes con protocolo congelado (`nba_live14_protocol.json`; informe `docs/nba_productor_14_20261025.md`); play-in/playoffs y el ajuste del nivel de anotación se probaron y no entran. Datos del servidor sin cambio (RUN071).
- Estado previo comprobado: modelo `01a116cf…`, `producer.sh` con `nba-live13-producer:20261024b`, panel `nba-dashboard-live13:20261024b` y cron: idénticos a lo que dejó la entrada anterior (nadie más tocó el servidor).
- Contexto desde `git -c core.autocrlf=false archive 9808f66` en `~/nba-isolated/live13/build-20261025/` (101 archivos comprobados por sha256). Imágenes `nba-dashboard-live13:20261025` (`2dce0f80de44`) y `nba-live13-producer:20261025` (`e162782b9721`), mismas bases. Hash normalizado del módulo `20c2adb3…`, igual en la imagen y en el modelo.
- Modelo `~/nba-isolated/live13/model/model.json` (sha256 `78473e54…`), ajustado con `--options accepted_options.json --bets` y validado con `compare --retrain` contra el 1.3.2: las 6 comprobaciones de reentrenamiento en verde; entre los insumos solo cambian reportes, opciones, líneas, módulo y protocolo.
- Ensayos previos con la imagen y el límite reales (512 MB, solo lectura, carpetas temporales): panel nuevo contra las 7 cohortes reales sin errores; productor sellando los partidos del 24-oct aún no empezados: 3 partidos, 190 pronósticos de jugador con los mercados nuevos, caché reescrita con los conteos nuevos. Memoria máxima 572 MB, igual que el 1.3.2 en el mismo ensayo (574 MB; el contenedor tiene swap). `game_lines` vacío en ese momento porque PropLine devolvía 504 a `h2h,spreads,totals`: el entorno toma 0 y lo anota.
- Cambio hecho después de que el 1.3.2 sellara el último partido del día (cohorte `2026-10-24_2030`). Orden: panel primero (`nba-dashboard-run69` recreado con la misma configuración; el anterior parado como `nba-dashboard-run71-prev4`), después modelo y `producer.sh` (etiqueta `20261025`). `/nba` 200, `live_v13` `ok`, 7 cohortes, 0 problemas; pasada manual 00:31 UTC sin errores (sin partidos por sellar).
- Respaldos en `~/nba-isolated/live13/`: `model.before-20261025`, `producer.sh.before-20261025`, `cache.before-20261025` (formato 1.3.x), `crontab.before-20261025`, `dashboard.inspect.before-20261025.json`, `containers.before-20261025.txt`.
- **Vuelta atrás:** productor: `cp producer.sh.before-20261025 producer.sh; rm -r model && cp -a model.before-20261025 model; rm -r cache && cp -a cache.before-20261025 cache` (la caché hay que restaurarla: el 1.3.2 rechaza las entradas con los conteos nuevos). Panel: se queda el nuevo (lee 1.3.x y 1.4); si hiciera falta, `docker rm -f nba-dashboard-run69 && docker rename nba-dashboard-run71-prev4 nba-dashboard-run69 && docker update --restart unless-stopped nba-dashboard-run69 && docker start nba-dashboard-run69`.
- Pendiente de observar: primer sellado real 1.4 (partidos del 25-oct): `game_lines.state`, pronósticos de triples/robos/tapones y que la caché se reescriba sin errores.

### 2026-10-24 22:45 UTC · NBA: productor y panel 1.3.2 (sumas de P/R/A) y arreglo del minutaje `:60` · `main` `5e120e2` (PR #107, #108, #109)
- **Motivo urgente:** desde el 24-oct ~20:20 UTC el productor no sellaba nada: 16 fallos `ValueError: invalid box score minutes '10:60'` al leer un box score terminado (nba.com escribe un minuto completo como `:60`). PR #109 lo lee como el minuto siguiente. Se perdieron al menos los 2 partidos de las 23:30 UTC del 24-oct (su ventana de sellado pasó con el fallo); los de las 00:00 UTC se sellaron en la primera pasada tras el cambio.
- Estado previo comprobado: `multimarket_v13_live.py`, `…_producer.py`, `multimarket_live_dashboard.py`, `prop_lines.py` y `availability.py` de las imágenes `nba-live13-producer:20261023` y `nba-dashboard-live13:20261024` idénticos byte a byte a `main` `62decf6`.
- Contexto de construcción desde `git -c core.autocrlf=false archive 5e120e2` (más `propline_shared.py` de `main`) en `~/nba-isolated/live13/build-20261024b/`, 99 archivos comprobados por sha256 contra el local. Imágenes: `nba-dashboard-live13:20261024b` (`e5ddb7ce7b07`, desde `nba-dashboard-live13:20261021` + `src/nba` + `web`) y `nba-live13-producer:20261024b` (`265a4bd7c112`, misma base + pdfplumber).
- Modelo `~/nba-isolated/live13/model/model.json` (sha256 `01a116cf…`), ajustado con los mismos insumos y validado con `compare` contra el anterior (`ded93f16…`): equipo, tabla de participación y pesos de puntos, rebotes y asistencias idénticos; añade las 4 sumas. Hash normalizado del módulo `057a7b92…`, igual dentro de la imagen y en el modelo.
- Orden: **panel primero** (el anterior rechaza un mercado desconocido). Panel `nba-dashboard-run69` recreado con la imagen nueva y la misma configuración (solo lectura, 256 MB, usuario 1001, mismos montajes y red); el anterior quedó parado como `nba-dashboard-run71-prev3` (`restart=no`). Ensayo previo del panel nuevo contra las 3 cohortes reales sin errores; tras el cambio `/nba` 200 y `live_v13` `ok`, 0 problemas.
- Productor: `producer.sh` con la etiqueta `nba-live13-producer:20261024b` (resto idéntico a `ops/live13_producer.sh` de `main`). Pasada manual 22:52 UTC: cohorte `2026-10-24_1852`, versión 1.3.2, 2 partidos, 142 pronósticos (134 de jugador: puntos 24, P+R 21, rebotes 21, P+R+A 18, asistencias 17, P+A 17, R+A 16), `prop_lines.state = archivo_aplicado`, reporte 18:45 ET aplicado. El panel la muestra.
- Respaldos en `~/nba-isolated/live13/`: `model.before-20261024b`, `producer.sh.before-20261024b`, `crontab.before-20261024b`, `dashboard.inspect.before-20261024b.json`, `containers.before-20261024b.txt`.
- **Vuelta atrás:** productor: `cp producer.sh.before-20261024b producer.sh; rm -r model && cp -a model.before-20261024b model` (la imagen `nba-live13-producer:20261023` sigue en el servidor, pero esa versión vuelve a caerse con `:60`). Panel: se queda el nuevo (lee 1.3.1 y 1.3.2); solo si hiciera falta: `docker rm -f nba-dashboard-run69 && docker rename nba-dashboard-run71-prev3 nba-dashboard-run69 && docker update --restart unless-stopped nba-dashboard-run69 && docker start nba-dashboard-run69` (no mostraría las cohortes 1.3.2).
- **Sin tocar:** `nba-live13-price`, datos `~/nba-isolated/live13/data` (RUN071), cron, resto de servicios.

### 2026-10-24 18:11 UTC · PropLine: `team_stats` empareja clubes escritos distinto (PR #100) · release `~/propline-shared/releases/fc20390` (`main` `fc20390`)
- Estado previo comprobado: `current` → `releases/5a9cde0`, idéntica a `main` `5a9cde0`. De `5a9cde0` a `fc20390` solo cambia `propline_shared.py` (el PR #99 no toca el recolector).
- Release desde `git archive fc20390` con `core.autocrlf=false`: `propline_shared.py` `a10df212…`, config `c3694385…` y runner `3f4f4745…` (sin cambios), `runtime.json` copiado de `5a9cde0`.
- Ensayo antes de activar (imagen fijada, `--network none`, volumen en solo lectura): `team_stats` empareja los dos equipos en **95 de 98** box scores de fútbol del archivo (antes 46); los 3 restantes no traen filas de equipo o no se pueden distinguir con seguridad. Lesiones (75) y tenis (182) se leen igual.
- Activación: `ln -sfn … current.tmp && mv -T current.tmp current` a las 18:11 UTC, con la pasada de las 18:07 en curso (fija su release al arrancar, así que termina con `5a9cde0`). Primera pasada con `fc20390`: 19:07 UTC.
- Respaldo: `~/propline-shared/backups/20261024-fc20390/` (`current.before`, `crontab.txt`).
- **Vuelta atrás:** `cd ~/propline-shared && ln -sfn /home/qf/propline-shared/releases/5a9cde0 current.tmp && mv -T current.tmp current`.

### 2026-10-24 · Verificación de la release `5a9cde0` (PR #97) y cambio de clave de PropLine
- **Clave:** desde las 14:11:49 UTC PropLine respondía `401 invalid_api_key` a la clave de `~/betsapi/.env.propline`. El titular dio una clave nueva; a las 14:24 UTC se escribió en ese archivo por SSH (600, `qf`; la anterior queda en `~/betsapi/.env.propline.bak-20261024-401`). Comprobada con `/v1/sports`: 200.
- **Pasada 15:07 UTC** (primera con `5a9cde0` y clave válida): 33 min, `stop: null`, 672 peticiones. Liquidación de los 3 días atrasados: 212 cierres, 205 liquidaciones y 124 box scores (NBA 25/25/25; fútbol 100 de cada uno, justo la reserva de 300; tenis 88 cierres y 81 liquidaciones). Informe de lesiones NBA con 75 jugadores. 6 fallos, todos `504` de PropLine (cierres y un box score), que se reintentan otro día; por ellos el `exit_code` fue 1.
- **Pasadas 16:07 y 17:07 UTC:** `stop: null`, 135 y 131 peticiones (solo 2 cierres y 2 liquidaciones nuevas), 1 y 0 fallos; la de 17:07 terminó con `exit_code 0`. Cuota de la cuenta a las 17:15: 3.599 de 5.000 usadas.
- **Lectores sobre el archivo real:** un cierre de fútbol con 3.170 filas (200 de Pinnacle, ninguna capturada antes del inicio) y su liquidación con 2.958 filas, todas calificadas. `team_stats` solo emparejaba 46 de 98 partidos: corregido en la release `fc20390` (entrada anterior).


### 2026-10-31 (noche) · Fase 1: huecos de once con SportsAPIPro · worker `quantfut-worker:sportsapipro-6256290` (rama `plan/sustituir-apify`, **sin fusionar a `main`**)
- Imagen delgada `FROM quantfut-worker:fotmob-alin-e2ff6a6` que solo añade `ingest/sportsapipro_alineaciones.py` (nuevo, `6256290a6650`). Ensayo sin red: importable.
- `SPORTSAPIPRO_KEY` añadida a `~/quantfut/.env` (600; copia previa `~/backups/env.pre-sportsapipro-20261031-212736`); llega al cron por `/etc/environment` del worker. Crontab del host: línea `4-59/5` (copia previa `releases/crontab-antes-sportsapipro-20261031-212736`). Solo se recreó el worker; la API siguió con `quantfut-api-cuotas:5b6f545` (200).
- Qué hace: si un partido empieza en 15-45 min y no tiene `lineups` de los dos lados, consulta SportsAPIPro (calendario cada 6 h como mucho; 2 intentos por partido con 7 min de espera; tope 40 peticiones/día) y carga con `sofascore_alineaciones.aplicar`. Sin hueco, 0 peticiones. Estado y recibos en `artifact_dir/sportsapipro/`.
- Primera pasada real: 0 huecos, 0 peticiones (sin partidos en la ventana a esa hora). Falta ver una jornada con partidos.
- **Vuelta atrás:** `cp -p ~/quantfut/releases/compose-antes-sportsapipro-20261031-212736.yml ~/quantfut/docker-compose.yml`, `cp -p ~/quantfut/releases/crontab-antes-sportsapipro-20261031-212736 ~/quantfut/scripts/crontab` y recrear solo el worker; o quitar `SPORTSAPIPRO_KEY` del `.env` para apagarlo sin tocar código (el módulo no hace nada sin clave).

### 2026-10-31 (noche) · Corrección de `sportsapipro_alineaciones` · worker `quantfut-worker:sportsapipro-fix-fc0fda7` (rama `plan/sustituir-apify`, PR 223)
- Error mío en la versión anterior (`sportsapipro-6256290`): `refrescar_calendario` usaba `ahora` antes de definirla y lanzaba `NameError` con un calendario ya archivado y un partido sin evento en caché (lo detectó `test_nombres_indefinidos` en el CI). Imagen delgada sobre `sportsapipro-6256290` que solo cambia `ingest/sportsapipro_alineaciones.py` (`6256290a6650` → `fc0fda7eb2de`); solo se recreó el worker, API 200, clave y cron intactos.
- **Vuelta atrás:** `cp -p ~/quantfut/releases/compose-antes-sportsapipro-fix-20261031-221211.yml ~/quantfut/docker-compose.yml` y recrear solo el worker (vuelve a la versión con el error: mejor apagar poniendo `SPORTSAPIPRO_KEY` vacía).

### 2026-10-31 (noche) · Apify retirado: once y bajas de fútbol desde FotMob · worker `quantfut-worker:fotmob-alin-e2ff6a6` + crontab del host (rama `plan/sustituir-apify`, **sin fusionar a `main`**)
- Motivo: Apify devuelve 403 (tope del plan gratuito) desde las 19:40 UTC y el titular no vuelve a pagarlo. Plan y mediciones: `docs/plan_sustituir_apify_20261031.md`.
- **Base:** imagen delgada `FROM quantfut-worker:408c43f` que solo copia tres archivos: `ingest/fotmob_alineaciones.py` (nuevo, `ae72e581289e`), `ingest/lineups.py` (`bc0b15722284` → `d85b2ba0a82a`, `_fuente` reconoce `fotmob`) e `ingest/health.py` (`2c1d5fed473a` → `cbb7880c954c`, cuenta once y bajas de SofaScore o FotMob). Antes de construir, `lineups.py` y `health.py` del worker eran idénticos a `main`; el resto de la imagen no se tocó.
- **Crontab del host** (`~/quantfut/scripts/crontab`, montado en el worker; difiere de `main` en la línea `cuotas_respaldo`, que no se tocó): `sofascore_partidos` y `sofascore_alineaciones` con «RETIRADO» y nueva línea `2-59/5` de `fotmob_alineaciones`. También se quitaron del crontab del usuario `qf` las dos líneas de `sofascore-apify` (copia en `~/sofascore-apify/crontab_antes_quitar_20261031.txt`).
- Ensayo sin red: módulos importables. Solo se recreó el worker (`--no-deps --no-build --force-recreate`); la API siguió con `quantfut-api-cuotas:5b6f545` y respondió 200. Sin trabajos en curso en el worker al recrear; el reentrenamiento ya no corre allí.
- Primera pasada real: 436 capturas de FotMob leídas, 138 de once oficial, 298 previstas y 3.269 bajas copiadas.
- **Vuelta atrás:** `cp -p ~/quantfut/releases/compose-antes-20261031-211732.yml ~/quantfut/docker-compose.yml`, `cp -p ~/quantfut/releases/crontab-antes-20261031-211732 ~/quantfut/scripts/crontab` y `docker compose up -d --no-deps --no-build --force-recreate worker`. Las filas `source = 'fotmob'` ya escritas pueden quedarse: no estorban a las de SofaScore.

### 2026-10-31 (noche) · Tenis T3: estadísticas públicas con respaldo cuando API-Tennis falle · SOLO host (`~/quantfut-public-sports/stats/` y `~/tenis-equivalencias/current/`; rama `plan/sustituir-apify`, **sin fusionar a `main`**)
- `publicar_tenis_estadisticas.py` (`9fe4499d42c7` → `9d27585a1182`; respaldo `publicar_tenis_estadisticas.py.antes_20261031_9fe4499d42c7`) y nuevo `~/tenis-equivalencias/current/tenis_estadisticas_respaldo.py` (`tenis_estadisticas.py` no cambia). El cron `17 */2 * * *` no cambia.
- API-Tennis sigue primero. Si falla (o con `QF_AT_CAIDO=1`, que se corta al primer error): clasificación desde SportsAPIPro (ATP `/rankings/type/5` = oficial; WTA `/rankings/wta`; tope propio de 6 peticiones/día en `cache/budget_sp.json`), H2H y forma del archivo propio de partidos unido a la caché antigua, perfiles de la caché. Límite: 500 jugadores por circuito (API-Tennis ~2.400); los jugadores nuevos salen sin temporada ni carrera.
- Prueba en copia del VPS con la caché vencida: 25 de 25 eventos, ranking/puntos/movimiento iguales en 26 de 50 jugadores (13 distintos por clasificación más reciente o «live» de la WTA, 1 fuera del top 500). Ejecución real tras desplegar: 25 eventos publicados, 11 llamadas a API-Tennis, API 200. Sigue rotulando `source: "API-Tennis"` en la respuesta.
- **Vuelta atrás:** copiar `publicar_tenis_estadisticas.py.antes_20261031_9fe4499d42c7` sobre `publicar_tenis_estadisticas.py`; el módulo de respaldo puede quedarse (no lo usa nadie sin ese cambio).

### 2026-10-31 (noche) · Tenis: el motor pasa a `--source auto` (API-Tennis y, al vencer, SportsAPIPro) · imagen `quantfut-tenis:sp-258629e` (rama `plan/sustituir-apify`, **sin fusionar a `main`**)
- Motivo: el plan de API-Tennis vence el 1-nov-2026 y no se renueva. Imagen delgada `FROM quantfut-tenis:bea262b` que añade `tennis_engine/tenis_formato_api_tennis.py`, `tennis_engine/tenis_transporte_sportsapipro.py` y sustituye `tennis_intake_v1/__main__.py` (copia en `scripts/tenis_overlay/`).
- `~/quantfut-tenis/vps_run.sh`: montajes `~/tenis-equivalencias/data` → `/equivalencias` (ro) y `.env.sportsapipro` → `/sp.env` (ro); las dos líneas de `tennis_intake_v1` llevan `--sportsapipro-key-file /sp.env --source auto`. `IMAGE` pasa de `quantfut-tenis:bea262b` a `quantfut-tenis:sp-258629e`. El cron (`25 * * * *` y semanal) no cambia.
- `auto`: API-Tennis primero; si falla (excepción, HTTP ≠ 200 o `success ≠ 1`) contesta SportsAPIPro con el mismo formato, conservando `event_key`, `player_key` y `tournament_key` de API-Tennis cuando la tabla los conoce (sintéticos 9.000.000.000 + id si no). Cada ejecución informa `answered_by`. Gasto de SportsAPIPro al caer API-Tennis: 5 peticiones por captura ancha (00 y 12 UTC) y 2 por refresco de resultados.
- Ensayo en sombra (raíz aparte, sin tocar el estado): 84 de 84 partidos comunes con mismo `event_key`, jugadores y orden; 48 de 48 terminados con mismo estado y ganador; con clave de API-Tennis inválida contestó SportsAPIPro. Pasada horaria real tras el corte: sin errores, `source: auto`.
- **Vuelta atrás:** copiar `~/quantfut-tenis/backup/vps_run.sh.antes_sportsapipro_20261031-214508` a `vps_run.sh` y `IMAGE.antes_sportsapipro_20261031-214508` a `IMAGE`.
- Pendiente: la web de estadísticas de tenis (`publicar_tenis_estadisticas.py`: rankings, perfiles y H2H) sigue usando solo API-Tennis.

### 2026-10-31 (noche) · Tenis T2: la tabla de equivalencias guarda orientación y torneos · SOLO host (`~/tenis-equivalencias/current/`)
- `tenis_equivalencias.py` (`d9d277c8debf` → `503edf86fcdf`; respaldo `tenis_equivalencias.py.antes_20261031_d9d277c8debf`): `partidos_emparejados` gana `first_key`, `second_key`, `directo`, `tournament_key`, `utid` y hay tabla `torneos`; `match` rehace los partidos antiguos sin duplicar la cuenta de jugadores. Nuevo `tenis_formato_api_tennis.py` (`d8356bbe93fb`, aún sin cron: conversor SportsAPIPro → `get_fixtures`; lo usará el motor).
- Corrida real tras actualizar: 96 partidos, 134 jugadores, 7 torneos, 0 conflictos. El cron `20 4,16 * * *` no cambia.
- **Vuelta atrás:** copiar el archivo `.antes_…` sobre `tenis_equivalencias.py`; las columnas nuevas no estorban a la versión antigua.

### 2026-10-31 (noche) · Equivalencia de jugadores de tenis API-Tennis ↔ SofaScore (T1) · SOLO host, sin contenedores
- Nuevo `~/tenis-equivalencias/` (700): `current/tenis_equivalencias.py` (= `src/qf/ingest/tenis_equivalencias.py`, sha256 `d9d277c8debf`, rama `plan/sustituir-apify`, **aún sin fusionar a `main`**), `.env.sportsapipro` (600, clave de SportsAPIPro), `data/` (índice SQLite + calendarios gzip con la hora real de recepción) y `logs/`.
- Cron `20 4,16 * * *` con flock: `capture` (3 peticiones a SportsAPIPro) y `match` contra `~/quantfut-tenis/data/intake_v1/api_tennis/originals` (solo lectura). No toca el motor ni la web de tenis.
- Primera ejecución: 3 calendarios (847 eventos), 96 partidos emparejados, 134 de 271 `player_key`, 0 conflictos. Consumo: 6 de las 100 peticiones diarias de SportsAPIPro.
- **Vuelta atrás:** `crontab -e` y quitar la línea de `tenis-equivalencias` (copia previa en `~/tenis-equivalencias/crontab_antes_20261031.txt`); los datos archivados no se borran.

### 2026-10-24 (noche) · Recolector SofaScore: NBA y tenis pasan a scrapesage · SOLO host
- Decisión del titular: `scrapesage/sofascore-scraper` para NBA y tenis, `rl1987` para fútbol. `current/sofascore_apify.py` (sha256 `273a61fedc7f`, = `src/qf/ingest/sofascore_apify.py` con finales LF) y `current/config.json` (`provider` por objetivo, `list_max` 100; sha256 `60b020855`). Cron sin cambios.
- Probado antes: 6 pruebas unitarias; corrida real en carpeta temporal del VPS (NBA, 5 partidos listados, 3 detalles; tope 0,30 USD). Descubrimiento de torneos de tenis sigue con rl1987 (scrapesage no tiene modo por fecha). Cada recibo anota el actor en `params._actor`.
- **Respaldo y vuelta atrás:** `~/sofascore-apify/respaldo_20261024_antes_scrapesage/` (`current/`, `index.sqlite`, `crontab.txt`). Para volver: copiar `current/*` de ahí a `~/sofascore-apify/current/`.

### 2026-10-24 · Recolector SofaScore (Apify, actor rl1987) · SOLO host, sin imágenes ni contenedores
- Nuevo `~/sofascore-apify/` (700): `current/sofascore_apify.py` (= `src/qf/ingest/sofascore_apify.py`, sha256 `c29386542180`), `current/config.json`, `.env.apify` (600, token Apify), `data/` (índice SQLite + objetos gzip inmutables con la hora real de recepción) y `logs/`.
- Cron `40 7 * * *` con flock. Alcance: NBA (torneo 132) + 23 competiciones de `sofascore_history.TOURNAMENTS`; detalle (estadísticas, alineaciones, incidencias) solo de partidos terminados, una vez. **Tenis: ATP/WTA individuales, torneos localizados cada 6 días barriendo un día de calendario (~0,6 USD); hash vigente `c29386542180`.
- Topes: 15 USD/mes (gasto de la cuenta Apify), 1,20 USD por corrida, 40 detalles por corrida. El arranque (jornadas de las 24 ligas) cuesta ~1 USD y cubre ~2 días.
- **Vuelta atrás:** `crontab -e` y quitar la línea de sofascore-apify; los datos archivados no se borran.

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

### 2026-10-21 · Anuncios con recompensa a producción (modo prueba apagado) · SOLO configuración en base, sin imágenes nuevas
- `reward_settings`: `ad_test_mode` de true a false (con `save_config`, auditado como `admin:claude-code`). Ya estaban el bloque real de Android
  `ca-app-pub-3902371555866850/4169479093` y el editor `pub-3902371555866850`; iOS sin bloque. `app-ads.txt` responde 200. Sigue 10 monedas, 5/día, pausa 180 s.
- App: `AndroidManifest.xml` con el ID de app real `ca-app-pub-3902371555866850~8333839408` y versión `1.0.0+2`; AAB release compilado
  (`apps/mobile/build/app/outputs/bundle/release/app-release.aab`). **Aún no subido a Play**: hasta que lo esté, las versiones con el ID de ejemplo no cargarán el bloque real.
- Con el modo prueba apagado, `/test-credit` queda desactivado: el único crédito es el callback firmado de Google.
- **Vuelta atrás:** en `/control/anuncios` encender «modo prueba» (usa los bloques de prueba de Google y reactiva el crédito simulado para los correos de `QF_ADS_TEST_CREDIT_EMAILS`).

### 2026-10-21 21:18 UTC · Crédito simulado de anuncios para `ceo@saptain.ru` · SOLO configuración + recrear la API
- Con el modo prueba encendido, el video de prueba no acreditaba porque el correo del titular no estaba en `QF_ADS_TEST_CREDIT_EMAILS`
  (solo había un gmail). Añadido `ceo@saptain.ru` al final de esa variable en `~/quantfut/.env`.
- Recreada solo la API (`docker compose up -d --no-deps --force-recreate --no-build api`), misma imagen `quantfut-api-web-vip:web-arranque`.
  Salud local y del dominio: 200. Variable verificada dentro del contenedor.
- Respaldo previo: `~/quantfut/releases/ads-test-credit-20261021/env.before`.
- **Vuelta atrás:** `cp -p` ese archivo sobre `.env` y recrear la API con el mismo comando. Apagar el modo prueba en `/control/anuncios` desactiva igualmente la vía simulada.

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
- **No recrear el worker entre las :07 y las ~:25.** La imagen de la captura horaria de PropLine (`9db4a578…`, hecha
  desde un contenedor de compose) conserva las etiquetas `com.docker.compose.*` del servicio worker: `docker compose up
  --force-recreate worker` mata `propline-shared-capture` a mitad de pasada y deja el worker en «Created» con nombre
  temporal (25-oct 16:22). Si pasa: `docker compose up -d --no-deps --no-build worker` y `docker rename <id>_quantfut-worker-1
  quantfut-worker-1`. **Resuelto el 25-oct 17:41 UTC:** la captura usa `propline-shared-capture:sin-etiquetas`
  (`sha256:0599acdb…`, etiquetas `com.docker.compose.*` vacías). Una release nueva del recolector debe fijar esa imagen (o
  una igual de limpia) en su `runtime.json`, nunca una imagen hecha desde un contenedor de compose.
- **`docker compose cp worker …` también copia al contenedor de la captura de PropLine** (por las mismas etiquetas). Usar
  `docker cp quantfut-worker-1:…` y `docker exec quantfut-worker-1 …` con el nombre exacto.
- (Resuelto el 25-oct) `requirements.txt`, `Dockerfile` y `~/quantfut/src` del servidor ya son los de `main`, y el
  `docker-compose.yml` del repo es igual al del servidor. Corrección del 25-oct (noche): la API `3babeb4` NO era `main`
  (37 archivos distintos y 33 que faltaban; la imagen se hizo sobre la API anterior). Desde `98bdfcc` la API se
  construye con el `src/` completo de `main`, igual que el worker; comprobar siempre las dos con `deploy.sh estado`.

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
