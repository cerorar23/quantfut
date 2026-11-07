# Auditoria de tenis, punto 1.1: inventario de datos

Estado: solo lectura. Ninguna fuente se modifico. Ninguna API de pago se llamo.
Medido: SofaScore local el 2026-11-05 03:06 UTC; VPS y copias de SQLite el 2026-11-05 entre 03:10 y 08:00 UTC.
Cada cifra indica el comando o script que la produjo. "NO MEDIDO" significa que no se pudo medir y por que. Un faltante nunca se cuenta como 0.

Scripts (en `apps/tennis/ops/`):
- `inventario_sofascore.py`: recorre `SOFASCORE/data/v3` (schedules y `events/`).
- `inventario_datos.py`: secciones `locales`, `canonico`, `identidad`, `solapes`.
- Salidas: `docs/tenis_auditoria_tablas/*.csv`. El inventario del VPS esta en `vps_inventario_tenis_medido.csv`.

Notas de entorno:
- El Python 3.12 de `.venv` no podia escribir dentro del worktree (PermissionError, verificado). Todos los scripts se ejecutaron con `C:\Users\huye\AppData\Local\Programs\Python\Python312\python.exe` (3.12.10, con pandas, pyarrow, openpyxl, numpy). Los ficheros descargados se leyeron con `-I`.
- Las copias de los SQLite del VPS (`ledger`, `states`, `equivalencias`) se trajeron por `scp` a un directorio temporal fuera del repo. Se abrieron en modo `mode=ro`.
- No se ejecuto `harness_check.sh`: esta tarea solo anade scripts de inventario y un informe. No toca codigo del producto.

## 1. Fuentes y ubicacion

| Fuente | Ubicacion | Contenido | Escribe | Original o derivado |
|---|---|---|---|---|
| TML (Tennis Match Level/Jeff Sackmann) `full_20261016/tml/originals` | local (151 CSV + 20 quali) y VPS (`weekly/*/tml/originals`, 152 CSV por snapshot) | partidos ATP/WTA/Challenger/quali 1967-2026 | descarga manual y refresh semanal (`tennis_refresh_v1`, cron lunes 11:00 hora del servidor, Europe/Berlin) | original con hash en `download_manifest.json` |
| TML canonico `full_20261016/canonical/matches.parquet` | local; y VPS `weekly/*/canonical_raw` | 492.251 partidos | `normalize` | derivado |
| Match Charting Project `full_20261016/mcp/originals` y `mcp_20261016` | local | 40 CSV de puntos y estadisticas + matches (7.566 ATP y 4.264 WTA en filas de matches) | descarga MCP fijada a commit | original |
| tennis-data.co.uk `tennis_data_manual/*` | local (47 xls/xlsx, 2000-2026) | resultados y **cuotas** (B365, PS, Max, Avg) | descarga manual | original (cuotas: inventario del otro agente) |
| `tennis_data_manual_processed` | local | `odds_matched.parquet`, `odds_raw.parquet` | proceso | derivado (cuotas) |
| SofaScore archivo | local `SOFASCORE/data/v3` (scraper en curso) y VPS `~/sofascore-scraper/data/v3` | local: tenis; VPS: solo futbol | scraper local y cron VPS 06:30/18:30 | original (event.json.gz, manifest con hash) |
| API-Tennis (originales) | local `intake_v1/api_tennis/originals` (2 carpetas) y VPS (147 carpetas, 293 ficheros) | fixtures, estados y resultados en vivo | `tennis_intake_v1` cron horario `:25` | original con receipt.json y response.json |
| API-Tennis estados y ledger | local `intake_v1/*.sqlite` (desfasado) y VPS | `states.sqlite`, `ledger.sqlite`, `api_tennis/states.sqlite` | intake | derivado del original |
| SportsAPIPro equivalencias | VPS `~/tenis-equivalencias` (5,9 MB) | 191 jugadores, 182 partidos emparejados con SofaScore | cron 04:20 y 16:20 UTC+1 | derivado |
| PropLine, The Odds API, live_odds | local `live_odds_v1`, VPS `live_odds_v1` (37 ficheros), VPS `propline-shared` | **cuotas** | otros agentes | fuera de este inventario (ver seccion 6) |
| Identidad (puentes) | local `identity_bridge_20261019` (49 ficheros, 154 MB), `identity_bridge_v3_20261019` (6 ficheros, 62 MB), `operations_20261016/identities.sqlite` (names 16.039, bindings 8) | puentes de ids | scripts de identidad | derivado |
| Rankings | solo dentro de TML (`winner_rank`, `loser_rank` y puntos de ambos; 2025: ganador 99,7 %, perdedor 98,2 % rellenos, comprobado el 5-nov) | ver seccion 7 | TML | original |

## 2. Inventario local (`inventario_local_*.csv`)

Comando: `python -I apps/tennis/ops/inventario_datos.py --data-root "C:/Users/huye/Documents/apuesta proyec/data/tennis" --out docs/tenis_auditoria_tablas --seccion locales`

| Carpeta (data/tennis) | Ficheros | Bytes | Fecha de modificacion (UTC) |
|---|---|---|---|
| full_20261016 | 256 | 637.194.195 | 2026-10-17 01:34-01:57 |
| weekly | 188 | 225.101.968 | 2026-10-17 01:34 - |
| mcp_20261016 | 24 | 217.720.814 | 2026-10-16 23:59 |
| identity_bridge_20261019 | 49 | 154.057.562 | 2026-10-19 22:11 - 2026-10-20 02:49 |
| identity_bridge_v3_20261019 | 6 | 62.005.234 | 2026-10-19 23:43 |
| historical_venues_20261018 | 492 | 71.944.330 | 2026-10-18 |
| historical_coverage_20261018 | 819 | 52.774.111 | 2026-10-18 |
| tennis_data_manual | 48 | 32.795.275 | 2026-10-20 00:27 |
| intake_v1 | 47 | 5.826.470 | 2026-10-20 00:52 - 03:09 |
| tennis_data_manual_processed | 4 | 6.226.835 | 2026-10-20 |

Los 57 elementos de primer nivel estan en `inventario_local_carpetas.csv`. Parquet (`inventario_local_parquet.csv`): canonico `full_20261016` 492.251 filas x 31 columnas; `identity_bridge_v3` 492.251 x 58; `audit_20261017_v1/canonical_v2` 492.251 x 56. Los `matches_spatial` historicos tienen 11.240 filas x 63. SQLite (`inventario_local_sqlite.csv`): `intake_v1/api_tennis/states.sqlite` observations 113, `operations_20261016/identities.sqlite` names 16.039.

Originales por fuente (`inventario_local_originales_por_fuente.csv`): TML 151 ficheros (92.855.460 B), TML quali 20 (6.061.346 B), MCP 40 (493.940.768 B), tennis-data 47 (32.795.261 B), API-Tennis 2 respuestas (2.428.518 B).

## 3. Canonico TML (`canon_*.csv`)

Comando: `... --seccion canonico`. Fuente: `full_20261016/canonical/matches.parquet`.

| Metrica | Valor | Fuente |
|---|---|---|
| Filas canonicas | 492.251 | `canon_calidad.csv` |
| Partidos ATP / WTA | 394.592 / 97.659 | `coverage.json` (`by_circuit`) y `canon_circuito_ano.csv` |
| Filas antes de deduplicar | 492.346 | `coverage.json` |
| Conflictos / filas invalidas | 15 / 3.923 | `coverage.json` |
| match_id duplicados | 0 | `canon_calidad.csv` |
| Elegibles para el modelo (`eligible_model`) | 249.938 (ATP 202.951, WTA 46.987) | `coverage.json`, `canon_calidad.csv` |
| Mejor de 3 / 5 | 449.335 / 42.916 | `canon_circuito_mejor_de.csv` |
| Grupo de fuente: tour / challenger / qualifying | 297.133 / 165.689 / 29.429 | `canon_circuito_grupo_fuente.csv` |
| Superficie | Hard 222.518; Clay 194.048; Grass 41.812; Carpet 33.873 | `canon_circuito_superficie.csv` |
| Nivel TML (`tourney_level`) | C 165.689; A 68.949; 250 67.069; G 55.902; M 25.161; D 23.052; 500 21.922; I 11.350; T2 9.792; T1 8.697; T3 7.725; T4 7.020 | `canon_circuito_nivel.csv` (significado de codigos no verificado) |
| Rondas | R32 178.882; R16 93.040; R64 52.997; QF 46.928; R128 28.998; RR 26.054; SF 23.772; Q1 17.669; F 11.968; Q2 9.188; Q3 2.572 | `canon_circuito_ronda.csv` |
| Partidos completados (`completed_standard`) | 469.527 (no completados 22.724) | `canon_calidad.csv` |
| Minutos nulos / w_svpt nulos | 260.099 / 233.386 | `canon_calidad.csv` |
| Dobles (nombres con "/") | 0 | `canon_calidad.csv` |
| Rango de `tourney_date` | 1967-02-27 .. 2026-10-16 | `canon_calidad.csv` |
| `received_at` | 168 valores distintos, todos 2026-10-17 01:34:40 .. 01:35:48 UTC | `canon_calidad.csv` |
| `date_precision` | "tournament_week_or_source_date; match_time_not_verified" en 492.251 filas (0 con hora verificada) | `canon_calidad.csv` |

Por ano, ver `canon_circuito_ano.csv` (97 filas) y `canon_circuito_ano_grupo.csv` (166 filas).

Recuento de cuarentena: `canon_cuarentena_resumen.csv` (claves de `quarantine.json`; cifras por clave no incluidas en este informe).

## 4. SofaScore archivo local

Comando: `python -I apps/tennis/ops/inventario_sofascore.py --root "C:/Users/huye/Documents/SOFASCORE/data/v3" --out docs/tenis_auditoria_tablas`

| Medida | Valor |
|---|---|
| Schedules leidos (`tournaments/*/seasons/*/schedule/round_*.json.gz`) | 1.697; errores 0 |
| Carpetas en `events/` recorridas | 43.177; sin event.json.gz 0; errores 0 |
| Partidos de tenis en schedules | 1.283 |
| Partidos de tenis en `events/` | 21.913 |
| Total unico | 21.974 (solo_events 20.691; ambos 1.222; solo_schedule 61) |
| Estado | finished 21.913; canceled 61 |
| Rango de fechas (`fecha_utc`) | 2022-12-30 .. 2026-11-03 |
| Carpetas de evento | 21.913 con carpeta; 61 sin carpeta |
| Circuito | ATP 11.186; WTA 10.788 |
| Anos (temporada) | 2023 ATP 2.732 / WTA 2.478; 2024 ATP 2.751 / WTA 2.708; 2025 ATP 2.877 / WTA 2.759; 2026 ATP 2.826 / WTA 2.843 |
| Mejor de (`defaultPeriodCount`) | 3: 19.881; 5: 2.032; sin dato: 61 |
| Dobles | 0 (archivo solo individuales) |
| Superficie | Hardcourt outdoor, Red clay, Grass, Green clay, Hardcourt indoor, Red clay indoor |
| Nivel (`tennisPoints`) | Grand Slam, ATP Finals, Masters 1000 / WTA 1000, 500, 250 |
| Ficheros por evento | 20.816 con event, h2h, point_by_point, statistics, team_streaks; 1.058 sin point_by_point ni statistics; 38 sin point_by_point; 1 sin statistics |
| `observed_at_utc` (cuando se capturo, no la fecha del partido) | 2026-11-02T21:01:21Z .. 2026-11-05T03:07:13Z |

Todas las cifras de esta seccion estan en `sofascore_local_resumen_*.csv` y en `sofascore_local_tenis_eventos.csv` (este ultimo pesa 13 MB: **no esta versionado**; se regenera con `inventario_sofascore.py` y una copia vive en `data/tennis/rediseno_20261104/tablas/`) (una fila por partido, con `archivo_origen`, `ficheros_evento`, `sha256_event_json`, `observed_at_utc`).

Observaciones:
- Hay 459 y 458 partidos con ronda vacia, y los nombres de ronda varian en mayusculas ("Qualification round 1" / "Qualification Round 1"). Hace falta normalizar.
- La descarga sigue en curso. Las cifras son de la hora indicada arriba.
- La carpeta `Downloads\event-15624961.json` (Indian Wells 2026, octavos) es un evento de tenis de 2026 que no esta en el archivo indexado; no se ha comprobado si el id existe en `events/`.

## 5. Fuentes de partidos: cobertura y solape

Comando: `... --seccion solapes --api-tennis-states <copia de states.sqlite>`

| Fuente | Partidos con fecha | Rango | Circuitos |
|---|---|---|---|
| TML canonico | 492.251 | 1967-02-27 .. 2026-10-16 | atp, wta |
| SofaScore local | 21.913 | 2022-12-30 .. 2026-11-03 | atp, wta |
| Match Charting Project | 11.811 (con fecha valida) | 1960-05-29 .. 2026-09-09 | atp, wta |
| tennis-data.co.uk | 119.456 | 2000-01-03 .. 2026-10-18 | atp, wta |
| API-Tennis (copia VPS states) | 527 eventos | 2026-10-18 .. 2026-11-06 | atp, wta |

Solape aproximado (apellido final; TML con regla de 0 a 14 dias tras `tourney_date`; resto con fecha +-1 dia). Fuente: `solapes_pares_fuentes.csv`.

| Par | Partidos A con pareja | Partidos B con pareja |
|---|---|---|
| TML - SofaScore | 13.797 de 492.251 (A) | 13.739 de 21.913 (SofaScore) |
| TML - MCP | 10.931 | 10.793 |
| TML - tennis-data | 103.185 | 102.942 |
| SofaScore - MCP | 2.838 | 2.840 |
| SofaScore - tennis-data | 12.352 | 12.351 |
| MCP - tennis-data | 7.860 | 7.859 |
| SofaScore - API-Tennis | 266 | 267 |
| TML - API-Tennis | 3 | 3 |
| API-Tennis - tennis-data | 1 | 1 |

Lectura: el emparejamiento por apellido da solapes de un 60-63 % de SofaScore frente a TML, y de un 50 % frente a tennis-data. Son cifras aproximadas. Hay homonimos y errores de apellido compuesto. No es una clave de identidad. Para una medida fiable haria falta emparejar por ids de jugador.

Hallazgo: TML tiene `tourney_date` (inicio de semana), no la hora del partido. Por eso la comparacion con TML necesita una ventana de 0 a 14 dias. Con ventana de 1 dia el solape bajaria de forma artificial.

## 6. Cuotas (solo anotacion)

No se inventariaron cuotas en detalle; eso lo hace el otro agente. Anotaciones:
- tennis-data.co.uk: columnas B365W/L, PSW/PSL, MaxW/L, AvgW/L en los 47 ficheros locales (ver `inventario_local_originales_por_fuente.csv`).
- VPS: `~/quantfut-tenis/data/live_odds_v1` (37 ficheros, 452 KB) y `~/propline-shared` (lectura solo de ls).
- Local: `live_odds_v1` (7 ficheros, 79.916 B).
- Las tablas de cuotas de otro agente estan en `docs/tenis_auditoria_tablas/cuotas_*.csv`.

## 7. Identidad

Comando: `... --seccion identidad`. Fuentes: `full_20261016/canonical/matches.parquet` (crudo) e `identity_bridge_v3_20261019/canonical/matches.parquet` (puente v3).

Ids alternos WTA (`wta:3xxxxx`, criterio de la auditoria del 19-oct). En ATP no hay criterio fiable por prefijo: NO MEDIDO.

| Ano WTA | Partidos crudo | Con id 3xxxxx crudo | Partidos puente v3 | Con id 3xxxxx puente v3 | Elegibles crudo | Elegibles v3 |
|---|---|---|---|---|---|---|
| 2022 | 2.612 | 0 | 2.612 | 0 | 2.413 | 2.413 |
| 2023 | 2.801 | 0 | 2.801 | 0 | 2.483 | 2.483 |
| 2024 | 2.695 | 0 | 2.695 | 0 | 2.571 | 2.571 |
| 2025 | 2.519 | 0 | 2.519 | 0 | 2.417 | 2.417 |
| 2026 | 2.299 | 89 | 2.299 | 47 | 2.146 | 2.146 |

- El problema de alias sigue en 2026: 47 de 2.299 partidos WTA (2,0 %) tienen todavia un id 3xxxxx en el puente v3. Antes eran 89 (3,9 %).
- La semana 2026-06-08 (torneos 2026-822 y 2026-1111) tenia 45 partidos con id alterno en el crudo y 2 en el puente v3 (`identidad_semana_2026_06_08_wta.csv`).
- La cifra de la auditoria del 19-oct (1.161 de 2.146 excluidos, 54 %) no se reproduce con el canonico: 2.146 es el numero de partidos elegibles WTA 2026 y los excluidos de los que habla el dato no estan en esta tabla. Medir la exclusion real del motor requiere el join del motor: NO MEDIDO.
- Puente v2 (`identity_bridge_20261019/alias_report.json`): 47 aliases fusionados, 403 filas reescritas, 62 ambiguos todavia. Puente v3 (`identity_report.json`): 5 fusiones por fecha de nacimiento y 14 distintos confirmados.
- Nombres normalizados con mas de un id en el crudo: 94 (`identidad_nombre_con_varios_ids_crudo.csv`); ids con mas de un nombre normalizado: 41. Incluye ATP. Los homonimos no se han separado: NO MEDIDO.
- Ids de API-Tennis: son claves numericas del proveedor (`player_a`, `player_b`), no nombres. Se mapean por `tenis-equivalencias` (191 jugadores) y el ledger registra exclusiones "Player unknown" y "Player ambiguous" (92 exclusiones en VPS).
- Dobles mezclados: 0 en TML, 0 en SofaScore, 0 nombres con "/" en MCP. No hay dobles en el archivo.

## 8. Rankings

- TML trae `winner_rank`, `loser_rank` y `*_rank_points` por partido. Rellenos: 2024 3.052 de 3.076; 2025 2.935 de 2.944; 2026 2.479 de 2.481 (`pandas` sobre `full_20261016/tml/originals/{2024,2025,2026}.csv`).
- Ese ranking se presume del momento del torneo (semana), no una serie semanal; qué fecha de publicación usa cada fila NO está verificado. Corrección del 5-nov: el resumen del subagente mencionaba solo `winner_rank`; `loser_rank` y los puntos del perdedor también existen en el original.
- No se encontro en el repo ninguna descarga de ranking semanal (grep en `apps/tennis/tennis_engine` por rank/url/csv/monday/lunes: sin resultados). Que ATP/WTA publiquen los lunes y que haya historico semanal: NO MEDIDO.

## 9. Punto en el tiempo (PIT)

| Fuente | Se puede reconstruir lo que se sabia antes del partido | Motivo |
|---|---|---|
| TML canonico | parcial | Fecha = inicio de semana (sin hora). Rank por partido es del momento del torneo. Estadisticas del partido (svpt, etc.) son posteriores. Historial previo si se ordena por fecha. |
| TML originals (rank) | parcial | `winner_rank` por torneo: util como rango del momento; sin fecha exacta |
| SofaScore local | no | `observed_at` es la captura (2026-11-02..05), no un snapshot previo. point_by_point y statistics son post-partido. h2h y team_streaks: sin fecha de captura por campo: NO MEDIDO |
| MCP | no | Datos de puntos post-partido; fecha del partido sin hora |
| tennis-data | parcial | Resultado de la fecha del partido; si las cuotas son de cierre o de apertura: NO MEDIDO |
| API-Tennis estados | parcial | `received_at` por observacion desde 2026-10-20; hay estados previos al inicio (`scheduled_unverified`), pero solo para 2026 |
| API-Tennis ledger (predicciones selladas) | si | `sealed_at` y `payload_sha256`; 350 predicciones, 2026-10-20..2026-11-04 |

## 10. Diferencias entre local y VPS

| Recurso | Local | VPS | Fuente de la medida |
|---|---|---|---|
| TML 2024.csv | 3.077 lineas; sha `d1127519...` | 3.077 lineas; sha `bf6d2f18...` (distinto) | `wc -l`, `sha256sum` |
| TML 2026.csv | 2.482 lineas; sha `a2bb4af3...` | 2.658 lineas; sha `d69f95b1...` | `wc -l`, `sha256sum` |
| API-Tennis originals | 2 carpetas (ambas en el VPS) | 147 carpetas, 293 ficheros, 65 MB | `ls`, `find`, `du` |
| API-Tennis states | 2 requests, 113 observaciones | 147 requests, 4.747 observaciones, 527 eventos | sqlite `mode=ro` |
| API-Tennis ledger | 34 sealed / 16 excluded (`intake_v1/ledger.sqlite` local) | 350 sealed / 92 excluded | sqlite `mode=ro` |
| SofaScore | 21.913 partidos de tenis | 0 partidos de tenis (10.748 eventos, todos futbol) | `find events -name event.json.gz`, `zcat` y `grep` del campo `sport.slug` |
| Weekly | 188 ficheros (un snapshot, 2026-10-19) | 4 snapshots (20261019, 20261020, 20261026, 20261102), 216 MB cada uno | `ls`, `du`, `find` |
| Equivalencias | no | `~/tenis-equivalencias` (5,9 MB, index.sqlite) | `du`, `scp` |

El VPS tiene datos mas recientes que la copia local (TML hasta 2026-11-02 frente a 2026-10-16).

Base de datos Postgres en el VPS: `quantfut` (esquemas `public` y `futbol`, 137 tablas y vistas) no tiene tablas de tenis. Medido con `SELECT` en `pg_class` dentro de `BEGIN TRANSACTION READ ONLY`. Bases: `postgres`, `quantfut`, `template0`, `template1`. La base `nba-db` no se reviso: NO MEDIDO.

Volumen Docker `quantfut_artifacts`: `/var/lib/docker/volumes/quantfut_artifacts/_data` da "Permission denied" para el usuario qf. No se uso `docker run` (no esta en la lista de lectura). Contenido: NO MEDIDO.

## 11. Cron y escritores (VPS, `crontab -l` del usuario qf)

| Entrada | Frecuencia | Escribe |
|---|---|---|
| `25 * * * * vps_run.sh hourly` | cada hora, minuto 25 | intake API-Tennis (fixtures 00 y 12 UTC; resto de horas sellan y piden resultados) |
| `0 11 * * 1 vps_run.sh weekly` | lunes 11:00 | `tennis_refresh_v1` (TML, canonico, puentes, modelos) |
| `20 4,16 * * *` tenis-equivalencias capture+match | 2 veces al dia | SportsAPIPro e equivalencias |
| `17 */2 * * *` publicar_tenis_estadisticas | cada 2 h | publicacion |
| `2-59/5 * * * *` publicar_tenis_web | cada 5 min | publicacion web |
| `30 6,18 * * *` sofascore-local-sync | 2 veces al dia | SofaScore (todos los deportes; en VPS solo futbol) |

## 12. Hallazgos que requieren decision

1. El archivo SofaScore local tiene 21.974 partidos de tenis (ATP y WTA, 2022-12 .. 2026-11) pero ningun partido de Challenger ni ITF. Las capturas de otros circuitos no existen.
2. TML no tiene hora del partido. Cualquier backtest que use orden dentro del dia depende de un orden no verificado.
3. El alias WTA 3xxxxx sigue en 47 partidos de 2026 (puente v3). No es cero.
4. La exclusion del 54 % de la auditoria del 19-oct no se reproduce con este canonico: hay que medirla en el motor.
5. La copia local de intake esta desfasada respecto al VPS (113 frente a 4.747 observaciones). Cualquier analisis local de API-Tennis debe usar la copia del VPS.
6. Las copias de SQLite en el VPS contienen rutas Windows locales en `receipts.source_path`. Esto indica que las observaciones se generaron o copiaron desde la maquina local. No se ha medido cuantas.

## 13. Lo NO medido

- Ids alternos ATP: no hay un criterio fiable por prefijo; el puente v2 fusiono aliases ATP, pero no se han medido de forma separada.
- Exclusion real del motor WTA 2026 (cifra de 54 %).
- Homonimos y dobles mezclados en el canonico (solo se mide nombres con "/").
- Ranking semanal ATP/WTA: fuente y frecuencia.
- Cuotas de cierre o apertura en tennis-data (inventario de cuotas, otro agente).
- Volumen `quantfut_artifacts` (permiso denegado).
- Base `nba-db`.
- Contenido de `h2h` y `team_streaks` en SofaScore: sin fecha de captura por campo.
- Fuentes de publicacion `~/quantfut-public-sports` (no se midio su almacen de datos).
