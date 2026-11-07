# Inventario de cuotas de tenis (auditoría 1.2)

Fecha: 2026-11-04 (lectura del VPS hasta 2026-11-05 02:16 UTC). Solo lectura. Sin llamadas a APIs con cuota ni al MCP de PropLine. Rama `tenis/rediseno-f1`, sin commit.

Todas las cifras salen de `apps/tennis/ops/inventario_cuotas.py` (tablas en `docs/tenis_auditoria_tablas/cuotas_*.csv`) o de los comandos indicados en la sección 9. Lo no medido aparece como **NO MEDIDO** con el motivo.

## 1. Resumen ejecutivo

- Hay cuatro fuentes con cuotas de tenis: **Tennis-Data** (ganador, cierre sin hora, 2000-2026), **PropLine** (archivo horario compartido, mercados completos, desde 24-oct-2026), **The Odds API** (solo ganador WTA Ningbo, 2 fotos/día) y **BetsAPI/bet365** (prematch sin instante de captura, en directo mayoritariamente). API-Tennis no contiene cuotas (147 registros, todos `get_fixtures`).
- **Cierre verificable (a): 0 eventos medidos.** Solo hay cierre declarado sin instante por evento (b): Tennis-Data (ganador, 96.865 partidos PS, 2004-2026) y PropLine en producción (desde el 24-oct, sin instante por evento medible). Todo lo demás es foto de un instante (c).
- **Viabilidad hoy:** solo el ganador tiene historia larga evaluable (Tennis-Data, cierre b). Hándicaps, totales, sets, juegos y aces no tienen cierre histórico verificable en ninguna fuente medida.
- PropLine califica mal el tenis: en el piloto, 55 de 173 eventos (31,8 %) son ATP/WTA principal; el resto (ITF, Challenger, UTR, sin tour) no tiene resultado en API-Tennis.
- Postgres del VPS no tiene cuotas de tenis (0 filas; ver 9.6).

## 2. Fuentes y clasificación

Fuente: `cuotas_fuentes_clasificacion.csv`. Clase de cierre según el criterio del encargo: (a) cierre verificable con instante a pocos minutos del inicio; (b) cierre declarado por la fuente sin instante; (c) foto de un instante.

| Fuente | Ubicación | Mercados | Instante de recepción | Instante casa | Inicio | Clase | Referencia de calibración |
|---|---|---|---|---|---|---|---|
| Tennis-Data | local `data/tennis/tennis_data_manual_processed/odds_raw.parquet` (47 ficheros del manifiesto) | ganador | NO (solo fecha) | NO | NO (solo fecha) | (b) | sí, a nivel partido, sin hora |
| PropLine piloto | local `.local/propline_shared_pilot_20261023` | todos (ver §3) | SÍ (`received_at`) | SÍ en algunos contratos (`book_updated_at`) | SÍ (`commence_time`) | (c) | no |
| PropLine producción | VPS, volumen `quantfut_artifacts` | cierre por evento (todos los mercados) y horario | en archivo, **NO accesible** (permiso denegado) | NO medido | en archivo, no leído | (b) para cierre; (c) horario | no, hasta verificar instante por evento |
| PropLine precursor | VPS `~/propline_data/tennis` (23-oct) | cierre por evento | SÍ (`captured_at`) | NO | SÍ | (b) | pendiente |
| The Odds API | local `data/tennis/live_odds_v1` y VPS `~/quantfut-tenis/data/live_odds_v1` | ganador (h2h), región eu | SÍ (`received_at`) | SÍ (`last_update` por casa) | SÍ | (c) | no |
| BetsAPI prematch | VPS `~/betsapi/data/tennis/prematch` | bet365: to_win_match, 1st_set_winner, etc. | NO | SÍ (`updated_at`) | SÍ (`time`) | sin instante de captura | no |
| BetsAPI odds | VPS `~/betsapi/data/tennis/odds` | en directo (`13_1`) | SÍ por fila (`add_time`) | SÍ | SÍ | (c) en directo | no |
| BetsAPI upcoming | VPS `~/betsapi/data/tennis/upcoming` | bet365 prematch | SÍ (época en el nombre de archivo) | SÍ | SÍ | (c) | no |
| API-Tennis | VPS `~/quantfut-tenis/data/intake_v1/api_tennis` | ninguno (fixtures y resultados) | SÍ (`receipt`) | no aplica | SÍ | no es cuota | resultados, no cuotas |

Notas de clasificación:

- Max y Avg de Tennis-Data son agregados (mejor cuota y media de casas), no una casa. Sus márgenes no son márgenes de casa.
- BFE y EX son exchanges (margen no comparable).
- En PropLine, `EXCHANGE_OR_DFS` (de `propline_shared.py`) marca exchanges y DFS. Se excluyen del margen.

## 3. Mercados por fuente

### 3.1 PropLine piloto (local, 3 recibos de `/v1/sports/tennis/odds` con 200, 1 con 400)

Fuente: `cuotas_propline_piloto_recibos_tenis.csv`, `cuotas_propline_piloto_mercados.csv`.

- 173 eventos únicos, 30.966 cotizaciones de tenis. Tours (recuento por evento): ATP 25, WTA 30, Challenger 21, ITF 62, UTR 27, sin tour 8.
- 49 casas distintas; 34 sin exchanges ni DFS.
- Mercados (cotizaciones / casas / eventos):

| Mercado | Periodo | Tipo | Cotizaciones | Casas | Eventos |
|---|---|---|---|---|---|
| totals | - | alternate | 3.034 | 28 | 99 |
| h2h (ganador) | - | main | 2.938 | 44 | 171 |
| spreads | - | alternate | 2.441 | 23 | 110 |
| totals | - | main | 1.403 | 39 | 122 |
| spreads | - | main | 1.347 | 35 | 124 |
| h2h | s1 | main | 873 | 18 | 148 |
| player_games_won | - | main | 653 | 13 | 86 |
| total_sets | - | main | 515 | 15 | 107 |
| totals | s1 | alternate | 400 | 6 | 75 |
| h2h | s2 | main | 356 | 11 | 114 |
| total_games | - | alternate | 346 | 2 | 30 |
| total_games | - | main | 100 | 5 | 34 |
| set_spread | - | main | 61 | 1 | 61 |
| total_tiebreaks | - | main | 12 | 2 | 11 |
| player_aces | - | main | 11 | 1 | 11 |
| player_break_points_won | - | main | 9 | 3 | 7 |

Hay además marcado `total_games` milestone, `h2h` s3, `spreads`/`totals` s2 y s3 en pocas cotizaciones (ver el CSV completo). Los mercados `player_games_won` son el caso de "ganador por juegos" que PropLine califica mal (CLAUDE.md, memoria 28-oct): no se usan como resultado.

- Marcas de calidad (`propline_shared.quotes`, recuentos sobre cotizaciones): `in_play_or_started` 3.218, `stale_provider_delivery` 2.584, `exchange_contract_requires_rules` 3.462, `dfs_not_single_bet` 1.983, `frozen_pregame_book` 938, `suspended` 86, `restricted_side` 2.

### 3.2 PropLine producción (VPS, logs de `~/propline-shared/logs`)

Fuente: `cuotas_propline_produccion_runs_tenis.csv` (270 pasadas, 2026-10-24 15:07 UTC a 2026-11-05 02:07 UTC).

- Logs no desglosan por mercado ni por casa. El mercado y la casa de producción son **NO MEDIDO**.
- Agregado de las 270 pasadas: peticiones de cierre de tenis 615 (612 con cotizaciones); cotizaciones de cierre 583.678; mediana de cotizaciones por evento de cierre 998,5; peticiones horarias de tenis 562 con 13.108.666 cotizaciones; resultados de tenis con datos 589; fallos 188.
- El volumen del archivo horario (`quantfut_artifacts`, `propline_shared`) está en `/var/lib/docker/volumes/...` con permiso denegado para `qf`. No se pudo leer el índice. NO MEDIDO: instante por recibo y cobertura por mercado en producción.

### 3.3 PropLine precursor (VPS `~/propline_data/tennis`, 23-oct)

Fuente: `cuotas_apitennis_propline_precursor.csv`.

- 59 ficheros `.json.gz` (la carpeta tiene además 42 marcadores `.final`; 101 entradas en total).
- Cierre con cotizaciones: 56; cierre vacío: 3. `captured_at` entre 2026-10-23 05:11 y 2026-10-24 00:40 UTC.
- Es el capturador anterior al compartido. No se usa como referencia.

### 3.4 The Odds API (ganador, WTA Ningbo)

Fuentes: `cuotas_theoddsapi_vps_snapshots.csv`, `cuotas_margen_ganador_theoddsapi.csv`.

- VPS: 5 instantáneas de tenis con 32 eventos (de 13 capturas totales, las demás son listados de deportes sin cuotas), 20 casas distintas. Hay `h2h_lay` de Betfair (excluido del margen).
- Local (`data/tennis/live_odds_v1`): `runs/2026-10-20T003931`, 9 eventos, 1 crédito, `ledger/credits.sqlite` y `slots.sqlite`. Las respuestas no están guardadas en local: las cuotas de la ejecución local son **NO MEDIDO**.
- Límite: 400 créditos/mes (`monthly_cap`), 2 instantáneas por día por torneo (AM/PM).

### 3.5 BetsAPI (VPS, muestras)

Fuente: `cuotas_betsapi_vps_resumen.csv`. Solo muestras: 150 archivos de prematch, 150 de odds y 57 de upcoming con contenido. Los censos de nombres de archivo son completos.

- `prematch`: 2.569 archivos (VPS). Claves de mercado en la muestra: `first_set_player_to_break_serve` 356, `1st_set_winner` 286, `set_betting` 236, `to_win_match` 145, `total_sets` 128, etc. Sin instante de captura por archivo (el `mtime` del VPS es la copia del 24-oct). Mediana de (inicio − última actualización de la casa) en la muestra: **−0,41 h**, es decir, la última actualización es posterior al inicio. No es un prematch limpio.
- `odds`: 31.136 archivos (VPS). En la muestra, 29.421 filas de cotización: 573 antes del inicio y 28.848 después; `time_status` = 3 (finalizado) en los 150. Es histórico en directo, no prematch.
- `upcoming`: 2.792 archivos de captura en 237 eventos, de 2026-10-24 06:18 a 2026-10-25 05:01 UTC. Nombre de archivo = época de captura: es la única fuente de BetsAPI con instante de recepción.
- `list`: 414 archivos diarios (2025-09-07 a 2026-10-25).

### 3.6 API-Tennis

Fuente: `cuotas_apitennis_propline_precursor.csv`.

- 147 registros: 147 `get_fixtures`, 146 con HTTP 200. `event_type_key` 265 (ATP) y 266 (WTA). Ninguna llamada de cuotas.
- En 146 respuestas (primeros 4 KB de cada una) no aparece la clave `odds`. El escaneo completo de los 137 MB no se hizo: NO MEDIDO fuera de la cabecera.

### 3.7 Tennis-Data (local, ganador)

Fuentes: `cuotas_tennisdata_cobertura_anual.csv`, `cuotas_tennisdata_series.csv`, `cuotas_margen_ganador_casa.csv`.

- 119.458 partidos (ATP 71.707 de 2000-2026; WTA 47.751 de 2007-2026).
- Series ATP: ATP250 19.074, Grand Slam 13.589, International 12.204, Masters 1000 10.310, ATP500 7.202, Masters 5.183, International Gold 3.755, Masters Cup 390. Series WTA (columna Tier): International 11.631, Premier 10.432, Grand Slam 10.033, WTA250 4.759, WTA1000 3.956, WTA500 2.705, Tier 1-4, Tour Championships 360, y varios códigos WTA25x-WTA27x con 1 partido cada uno (número exacto de códigos NO MEDIDO). En las columnas Series/Tier no aparecen etiquetas de Challenger ni ITF (verificado en `cuotas_tennisdata_series.csv`).
- Casas con cuota de ganador (partidos con cuota ambas caras, años): PS (Pinnacle) 96.865, 2004-2026; B365 110.372, 2002-2026; Max 81.642, 2010-2026 (agregado); Avg 81.644, 2010-2026 (agregado); BFE 5.767, 2025-2026 (exchange); EX 68.242, 2004-2018 (exchange); LB 54.339, 2008-2018; UB 17.592, 2006-2009; SJ 29.711, 2009-2014; CB 19.934, 2001-2007; GB 5.055, 2001-2002; IW 13.358, 2001-2005; SB 5.423, 2001-2003; B&W 1.097, 2003.
- **Cierre:** el fichero solo tiene fecha (`Date`, sin hora). El cierre es una convención de la fuente (columnas PS/B365). No hay instante verificable en el fichero: clase (b).

## 4. Margen (overround) por contrato y casa

Definición: para dos resultados del mismo contrato (mismo evento, casa, mercado, periodo, línea y descripción), margen = Σ(1/cuota) − 1. Las líneas distintas no se mezclan. Exchanges, DFS y `h2h_lay` se excluyen. Percentiles lineales.

### 4.1 Ganador por casa — Tennis-Data (cierre b, todos los años)

Fuente: `cuotas_margen_ganador_casa.csv`.

| Casa | Tipo | n (TODOS) | Mediana | p5 | p25 | p75 | p95 |
|---|---|---|---|---|---|---|---|
| PS (Pinnacle) ATP | casa | 54.272 | 0,0241 | 0,0143 | 0,0200 | 0,0277 | 0,0318 |
| PS WTA | casa | 42.582 | 0,0255 | 0,0154 | 0,0212 | 0,0290 | 0,0325 |
| PS todos | casa | 96.854 | 0,0246 | 0,0146 | 0,0205 | 0,0283 | 0,0320 |
| B365 todos | casa | 110.262 | 0,0667 | 0,0460 | 0,0550 | 0,0761 | 0,0819 |
| LB todos | casa | 54.278 | 0,0667 | 0,0471 | 0,0530 | 0,0700 | 0,0814 |
| UB todos | casa | 17.592 | 0,0637 | 0,0558 | 0,0580 | 0,0677 | 0,0677 |
| SJ todos | casa | 29.691 | 0,0697 | 0,0516 | 0,0600 | 0,0800 | 0,0857 |
| CB todos | casa | 19.932 | 0,0650 | 0,0528 | 0,0580 | 0,0700 | 0,0838 |
| BFE todos | exchange | 5.767 | 0,0067 | 0,0019 | 0,0040 | 0,0090 | 0,0129 |
| EX todos | exchange | 68.215 | 0,0695 | 0,0532 | 0,0600 | 0,0800 | 0,0925 |
| Max todos | agregado | 81.642 | 0,0025 | −0,0332 | −0,0088 | 0,0117 | 0,0268 |
| Avg todos | agregado | 81.640 | 0,0580 | 0,0483 | 0,0520 | 0,0630 | 0,0668 |

Lectura: el margen de Pinnacle (~2,5 %) es el de referencia de mercado; Max da márgenes negativos porque toma la mejor cuota de cada lado de casas distintas, así que no es un margen de casa. Cifras redondeadas a 4 decimales desde el CSV.

### 4.2 Ganador por casa — PropLine piloto (todos los tours; no es cierre)

Fuente: `cuotas_margen_ganador_propline_piloto.csv`. Pinnacle: n 76, mediana 0,0474, p5 0,0289, p95 0,0661. DraftKings: n 10, mediana 0,0482. Este margen (~4,7 %) es mayor que el de Pinnacle en Tennis-Data (~2,5 %) y en The Odds API (ver 4.3). El desglose por tour no se calculó: **NO MEDIDO** si la diferencia viene del tour (ITF/UTR) o de la fuente.

### 4.3 Ganador — The Odds API (WTA Ningbo, VPS)

Fuente: `cuotas_margen_ganador_theoddsapi.csv`. Pinnacle: n 29, mediana 0,0293, p5 0,0225, p95 0,0369. Otras: Winamax DE 0,037; Betsson 0,060; Tipico 0,082. Muestra de 5 instantáneas.

### 4.4 Totales y hándicaps por línea — PropLine piloto

Fuente: `cuotas_margen_linea_propline_piloto.csv` (989 filas, una por mercado, periodo, tipo de línea, línea absoluta y casa). Ejemplo de las primeras líneas de hándicap (`spreads`, main, línea absoluta 0,5; solo se muestran 12 filas del CSV, no es un resumen completo): admiralbet n=4, mediana 0,0904; betmgm n=3, 0,0867; betrivers n=10, 0,0757; ladbrokes_be n=12, 0,0968. Las líneas con n<5 tienen poca base. El CSV completo tiene todas las líneas y casas; la tabla no se duplica aquí.

## 5. Instante de recepción frente a publicación y frente al inicio

Fuente: `cuotas_propline_piloto_recibos_tenis.csv`, `cuotas_theoddsapi_vps_snapshots.csv`, scripts en §7.

- **PropLine piloto:** `received_at` por recibo (UTC). Minutos entre recepción e inicio: mínimo −384, mediana 486. 37 eventos empezados antes de la recepción (contados por recibo). 3 eventos a 0-10 min antes del inicio (contados por recibo, `eventos_ventana_0_10_min_antes`).
- **The Odds API VPS:** `received_at` por instantánea. Minutos entre recepción e inicio: −192,2 a +1.769,9. Mediana de (recepción − `last_update` de la casa) 0,41 min. Un evento a 0-10 min del inicio; 2 empezados antes de la recepción.
- **BetsAPI:** `upcoming` con época de captura (rango de 2026-10-24 06:18 a 2026-10-25 05:01). `prematch` sin instante de captura; su `updated_at` es posterior al inicio en mediana (−0,41 h).
- **PropLine producción:** el instante de cada recibo está en el archivo del VPS (**NO ACCESIBLE**). El log solo tiene la pasada (`started_at`).
- **Qué sabía el mercado antes:** solo es verificable con PropLine piloto (recibos) y The Odds API (instantáneas), y con BetsAPI `upcoming`. Tennis-Data no permite decir qué se sabía antes: su único instante es la fecha.

## 6. Cierre: clasificación por fuente y mercado

| Fuente / mercado | Clase | Eventos con instante ≤ 10 min antes del inicio | Uso |
|---|---|---|---|
| Tennis-Data, ganador | (b) | NO (sin hora) | calibración a nivel partido |
| PropLine producción, cierre por evento | (b) | NO MEDIDO (sin instante por evento) | conteo; falta instante |
| PropLine piloto, horario | (c) | 3 (recibo-evento) | no es cierre; 1 receipt |
| The Odds API, ganador | (c) | 1 (instantánea-evento) | no es cierre |
| BetsAPI prematch | sin instante de captura | NO | no |
| BetsAPI upcoming | (c) | NO MEDIDO (sin hora de inicio en el censo) | no |

**(a) cierre verificable: 0 fuentes con n suficiente.** (b) cierre declarado sin instante: Tennis-Data (ganador, 96.865 partidos con PS) y PropLine producción (no medible por evento). Estas dos son las referencias de calibración que el encargo admite.

## 7. Identificadores y enlace

- **PropLine:** `event.id` numérico, `home_team`/`away_team` (nombre), `commence_time`, `tour`, `tournament`. Clave estable por evento; los nombres de jugador son textuales.
- **The Odds API:** `id` hash de 32 caracteres, nombres en `home_team`/`away_team`, `commence_time`, `sport_key` (torneo).
- **BetsAPI:** `event.id` numérico, `home.name`/`away.name`, `time` (época), `league.name`. Los jugadores tienen `id` propio.
- **API-Tennis:** `event_key` numérico, `event_first_player`/`event_second_player` (formato "N. Apellido"), `event_date`/`event_time`, `tournament_name`.
- **Tennis-Data:** sin id; nombre, fecha, `Tournament`, `Series`, `Tier`.
- **Enlace Tennis-Data con el motor:** `odds_matched.parquet` tiene `match_id`: 53.853 de 119.458 filas (45,1 %). El criterio de emparejamiento no está documentado en el repo: **NO MEDIDO** cuál es el criterio exacto.
- **Enlace PropLine con API-Tennis:** NO MEDIDO (no hay un cruce ejecutado en esta auditoría).

## 8. Viabilidad hoy por mercado

| Mercado | Fuentes con historia | Cierre verificable (a) | Cierre declarado (b) | Viable para evaluar |
|---|---|---|---|---|
| Ganador | Tennis-Data (2000-2026) | 0 | PS 96.865 partidos, 2004-2026; B365 110.372, 2002-2026 | sí, como referencia b (sin instante) |
| Ganador WTA/ATP vivo | PropLine desde 24-oct; Odds API desde 19-oct | 0 | PropLine producción (no medible por evento) | no (historia de 12 días) |
| Hándicap de sets / juegos, totales | PropLine (desde 24-oct) | 0 | PropLine producción | no |
| 1.er set, tiebreak, sets, aces, break | PropLine piloto (1 día) | 0 | 0 | no |
| Resultado exacto | ninguna medida | 0 | 0 | no |

## 9. Rarezas y comandos

### 9.1 Rarezas

- Tennis-Data: los campos `Series` (ATP) y `Tier` (WTA) se reparten entre circuitos; el análisis los trata juntos.
- `Max` y `Avg` no son casas. Max da márgenes negativos (ver §4.1).
- `BFE` y `EX` son exchanges.
- BetsAPI `prematch` tiene la última actualización después del inicio en la mediana de la muestra.
- BetsAPI `odds` es histórico en directo: 98 % de las filas en la muestra son posteriores al inicio.
- PropLine: `player_games_won` es el mercado que califica mal al tenis.
- PropLine producción: 188 fallos de petición en 270 pasadas.
- The Odds API: solo guarda el ganador; el ledger local no conserva las respuestas.
- Postgres del VPS (`quantfut-db-1`, base `quantfut`, esquemas `public` y `futbol`): no hay tablas de tenis. Consulta `information_schema`: ninguna tabla con `tenn|odd|cuota|propline|closing|prematch|bet365|line|market|sport|event|match|pinn|book` contiene tenis. `matches.league_id` (23 ligas de la consulta, `LIMIT 40`) solo tiene fútbol. `odds_snapshots.match_id ILIKE '%tenn%'` = 0. Fuentes de `odds_snapshots`: propline 3.491.359, football_data 286.623, the_odds_api 280.620, oddspapi_reconstructed 8.754, the_odds_api_hist 3.627 (son fútbol, no tenis: no contienen tenis por `match_id`).
- `sharpapi` (VPS) solo cubre fútbol en su muestra de log (`captura.log`): no se leyó tenis.

### 9.2 Comandos principales

- Local: `python -I apps/tennis/ops/inventario_cuotas.py --repo "C:/Users/huye/Documents/apuesta proyec" --vps-dir <copias> --emit`. Python no puede escribir en el worktree en esta sesión, así que la salida va a stdout y se separa con `awk` en `docs/tenis_auditoria_tablas/`.
- Copias del VPS (solo `ssh` con `head`, `zcat`, `find`, `ls`, `du`, `docker exec` con SELECT en transacción de solo lectura):
  - `head -c 4000000 ~/propline-shared/logs/2026-10.log` y `2026-11.log`.
  - `head` de `~/quantfut-tenis/data/live_odds_v1/runs/*.json` y `ledger/snapshots/*/{receipt,response}.json`.
  - `zcat ~/propline_data/tennis/*.json.gz | head -c 20000`.
  - `zcat ~/betsapi/data/tennis/{prematch,odds}/<primeros 150>` y `upcoming/<dirs>` con `head -c`.
  - `head -c 4000` de `~/quantfut-tenis/data/intake_v1/api_tennis/originals/*/response.json`; `head -c 500` de cada `receipt.json`.
  - `find ~/betsapi/data/tennis/upcoming -type f -printf "%P\n"` y `find ... -printf "%TY-%Tm-%Td\n"`.
  - Postgres: `docker exec -i quantfut-db-1 psql -U qf -d quantfut -At` con `BEGIN READ ONLY; ... ROLLBACK;`.
- Lectura local de Tennis-Data con `pyarrow` (`odds_raw.parquet`, `odds_matched.parquet`).

### 9.3 NO MEDIDO

- Archivo horario completo de PropLine en el VPS: permiso denegado en `/var/lib/docker/volumes/quantfut_artifacts/_data`.
- Cuotas de producción de PropLine por mercado, casa e instante: depende del archivo anterior.
- BetsAPI completa (solo muestras de 150/150/57 archivos).
- API-Tennis sin cuotas en el cuerpo completo: solo 4 KB de cabecera por respuesta.
- Respuestas de The Odds API del ledger local: no están guardadas.
- Enlace entre fuentes (tasa de cruce PropLine ↔ API-Tennis ↔ Tennis-Data).
- Criterio de `match_id` en `odds_matched.parquet`.
- Desglose por tour del margen PropLine (¿la diferencia de ~4,7 % frente a ~2,5 % de Pinnacle viene de ITF/UTR?).
- Xls originales de Tennis-Data: se usó `odds_raw.parquet`, derivado del manifiesto. No se reanalizaron los 47 ficheros.

## 10. Archivos

- Script: `apps/tennis/ops/inventario_cuotas.py`.
- Tablas: `docs/tenis_auditoria_tablas/cuotas_*.csv` (13 ficheros).
- Informe: este documento.
