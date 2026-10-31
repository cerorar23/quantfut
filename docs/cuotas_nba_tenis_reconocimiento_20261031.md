# Reconocimiento: cuotas reales para los mercados de NBA y tenis (30/31-oct-2026)

Solo lectura. Código de `origin/main`; producción leída por `ssh quantfut` (consultas `sqlite ?mode=ro`, `ls`, `docker exec ... python` sin escribir). No se pidió nada a PropLine (cero peticiones de cuota gastadas). Scripts de medición: scratchpad de la sesión (`nba_host.py`, `nba_cont.py`, `ten_host.py`, `ten_cont.py`).

## 1. Dónde viven hoy las cuotas de NBA y tenis

- **No están en Postgres.** `odds_snapshots` solo recibe fútbol (`src/qf/ingest/propline_ingest.py:100-143`, une con `matches`). NBA y tenis viven solo en el **archivo PropLine compartido**.
- Archivo: volumen Docker `quantfut_artifacts`, subcarpeta `propline_shared` (dentro de la API: `/srv/quantfut/artifacts/propline_shared`; `index.sqlite` + `objects/` por SHA-256 + `runs/` + `provider.json`). **3,8 GB.** Tablas `requests(slot,path,params,started_at,state)` y `receipts(request_id,received_at,status,sha256,body_path,headers,error,events,outcomes)`; los recibos rechazan UPDATE/DELETE.
- Recolector **activo**: cron `7 * * * *` de `qf` → `/home/qf/propline-shared/current/propline_shared_runner.py` (contenedor aislado, `runtime.json`: volumen `quantfut_artifacts`). Última pasada 31-oct 02:16 UTC. Varias pasadas salen con `exit_code 1` (16:18, 17:15, 20:14, 23:17 del 30-oct; 00:23-02:16 del 31-oct) por algún 504 suelto (en el último tramo del log: 490×200, 3×504); las cuotas se siguen archivando.
- Recibos `/odds` por día (todos con status 200 salvo 1-4):

| Día | NBA `/basketball_nba/odds` (pasadas, outcomes) | Tenis `/tennis/odds` (pasadas, outcomes) |
|---|---|---|
| 28-oct | 196 recibos / 24 horas, 3,93 M | 48 / 24, 1,19 M |
| 29-oct | 240 / 24, 1,65 M | 48 / 24, 0,93 M |
| 30-oct | 242 / 24, 4,07 M | 48 / 24, 0,66 M |

  Lotes NBA por hora: `h2h,spreads,totals` (también con `period=all`), `player_points`, `player_rebounds`, `player_assists`, `player_threes,steals,blocks,blocks_steals,turnovers`, combinados, etc. Tenis: `h2h,spreads,totals,total_games,total_sets,set_spread,total_tiebreaks,player_aces,player_double_faults,player_games_won` + `player_break_points_won,total_aces`, todos con `period=all`.
- Además: cierres (`/events/{id}/odds/closing`) y liquidaciones (`/results`) por partido terminado (NBA y tenis), lectores `read_closing`/`read_results` en `src/qf/ingest/propline_shared.py:461-515`.
- Montajes: el productor NBA (`/home/qf/nba-isolated/live13/producer.sh`) y el motor de tenis (`/home/qf/quantfut-tenis/vps_run.sh`) montan el archivo **de solo lectura**. El contenedor del panel NBA (`nba-dashboard-run69`) **no** lo monta (solo `live13/cohorts` y datos de investigación). La API (`quantfut-api-1`) sí.

## 2. Mapeo por mercado y cobertura real

Método: para cada pronóstico sellado (NBA: 30 cohortes 25-30 oct, 50 partidos; tenis: 63 partidos sellados desde el 27-oct, cuando empezó `market_board`) se releyó **la misma observación del archivo usada al sellar** (`ps.newest` en `received_at` del sello, ventana 10 s) y se buscó precio a dos lados en la **misma línea** (sin banderas: no DFS, no intercambios, no en juego, partido completo). «Blanda» = alguna casa de `settings.soft_books` (la lista que usa el fútbol, `src/qf/config.py:158-163`).

### NBA (`apps/nba/src/nba/multimarket_v13_live.py`)

| Mercado publicado | Clave PropLine | Origen de la línea publicada | Con precio a 2 lados, misma línea | Con casa blanda | Casas (mediana) |
|---|---|---|---|---|---|
| winner | `h2h` | — | 41/44 | 40/44 (Pinnacle 40) | 87 |
| game_total | `totals` (alternativas) | umbral estadístico `floor(baseline)+0,5` (`:441-444`) | 40/44 | 30/44 | 30 |
| team_points | `totals` con `team` | umbral estadístico | 73/88 | 58/88 | 7 |
| spread | `spreads` | **no se publica** (solo se usa como rasgo, `game_lines`) | — | — | 75 casas en la línea principal |
| player_points | `player_points` | línea PropLine (consenso ≥2 casas) | 475/517 | 446/517 | 11 |
| | | umbral estadístico (sin línea) | 3/319 | 0 | |
| player_rebounds | `player_rebounds` | PropLine | 463/505 | 407/505 | 12 |
| | | estadístico | 9/331 | 0 | |
| player_assists | `player_assists` | PropLine | 416/454 | 292/454 | 11 |
| | | estadístico | 36/381 | 0 | |
| player_threes | `player_threes` | PropLine | 398/434 | 336/434 | 12 |
| | | estadístico | 20/401 | 1 | |
| combos P+R / P+A / R+A / PRA | `player_points_rebounds` etc. | PropLine | 456/495, 395/423, 390/419, 410/440 | 416, 306, 295, 320 | 7-8 |
| | | estadístico | 0-4 por mercado | 0 | |
| steals / blocks / blocks_steals / turnovers | mismas claves | PropLine | 314/336, 253/271, 231/244, 158/158 | **0** en todos | 2-3 |
| | | estadístico | 54-78 por mercado | 0 | |

(Filas «team_statistical» de los mercados de jugador = cohortes del 25-oct sin `line_source`; con precio 100 %.) Lectura: aproximadamente la mitad de las filas de jugador publicadas usan un umbral estadístico y **casi nunca** tienen cuota; robos/tapones/pérdidas solo los cotizan casas fuera de la lista blanda (EE. UU./DFS-like).

### Tenis (`src/qf/api/tenis_publico.py`, `apps/tennis/tennis_odds_propline_v1/__init__.py`)

Desde el 27-oct cada sello guarda `forecast.market_board` (`tennis_motor/__init__.py:156-162`) con `event_id` PropLine, `snapshot_id` (= sha256 del recibo), `received_at` y, por línea, la **probabilidad sin margen media de casas** (`market`) y `books`; no guarda precios. 53/63 sellos (84 %) tienen board y `winner.live`; los 10 restantes no encontraron el partido en PropLine.

| Mercado publicado | Clave PropLine (`FAMILIES`, `tennis_odds_propline_v1:83-87`) | Líneas publicadas con fila en el board | Casas (mediana) | Con casa blanda (aprox.) | Pinnacle |
|---|---|---|---|---|---|
| winner | `h2h` | 53/63 | 34 | 53 | 53 |
| games_total | `totals` / `total_games` | 425/567 (75 %) | 12 | 73 | 181 |
| games_handicap | `spreads` | 275/441 (62 %) | 7 | 34 | 128 |
| sets_total | `total_sets` | 53/63 | 9 | 0 | 53 |
| sets_handicap | `set_spread` | 75/126 | **1** | 0 | 0 |
| set_winner | `h2h` + `period=sN` | 137/189 (72 %) | 7 | 53 | 53 |
| tiebreak | `total_tiebreaks` | **0/63** | — | 0 | 0 |

Casas blandas vistas en tenis: solo `bovada`, `betonlineag`, `strendus`. Con la lista blanda del fútbol, el tenis quedaría casi sin cuota fuera de ganador; con «cualquier casa no DFS» o Pinnacle, sí hay.

## 3. Unión de eventos e identidades

- **Fútbol:** `propline_ingest._ingest_hourly` → `football_feed` + `odds_worker.match_events(feed, meta, otras_fuentes=("propline",))` por **nombres** (alias de ligas/equipos) y `|commence_time − kickoff| ≤ 900 s` (`propline_ingest.py:124-131`); escribe en `odds_snapshots` con `source='propline'`.
- **NBA:** ya resuelta y fiable. PropLine trae `home_team_id/away_team_id = "nba:<teamId>"` y `player_id = "nba:<personId>"`; `prop_lines.py:79-91` une por par de IDs oficiales de equipo + `tipoff` ±3 h y por `player_id` NBA (`nba_id()`, `:42-45`). Medido: todas las cohortes con `archivo_aplicado` unieron 100 % de sus partidos (1 cohorte del 25-oct quedó `sin_archivo_reciente`). El sello guarda `prop_lines.sha256`, `received_at_utc`, `slot`, `component_requests` → la observación exacta es reproducible. No hace falta mapa de nombres.
- **Tenis:** `player_id` siempre nulo en PropLine. `provider_pair`/`same_player` (`tennis_odds_propline_v1:36-61`): nombre normalizado exacto o mismo nombre+apellido con nombres intermedios extra; nunca por parecido; dos listados del mismo par → sin mercado. La unión **ya está hecha y sellada**: `forecast.market_board.event_id` y `winner.live.event_id`. Fiabilidad: 53/63 (84 %) emparejados; los fallos son partidos sin listar o grafías distintas (apellidos compuestos, abreviaturas de API-Tennis `T. Fritz`). El `event_key` de API-Tennis no se cruza con PropLine por ID.

## 4. Cómo elige el fútbol la cuota mostrada y qué entra en el sello

- Captura: la más reciente vigente que tenga **1X2 de Pinnacle completo y alguna casa blanda** (`alta_prob_datos._snapshot`, `:167-186`); edad ≤ `MAX_EDAD_PRECIO` y antes de `kickoff − MIN_LEAD`.
- Cuota: **la mejor (máximo) entre `soft_books` en esa misma captura** (`_ref`, `:296-315`; hándicap por su propia fuente `_ref_nuevos`). `ref_book` = la casa de ese máximo; `odds_as_of` = hora de la captura; `odds_source`.
- Escalera NBA/tenis ya hace lo mismo con el archivo: Pinnacle sin margen como probabilidad, mejor casa blanda como cuota, solo `h2h` (`src/qf/publish/escalera_ext.py:63-95`).
- **Sello:** `ref_price, ref_book, odds_source, odds_as_of` forman parte del payload de la cadena (`src/qf/publish/hashchain.py:164-217`, payload `:223`). `mobile.quote_of` (`src/qf/api/mobile.py:262-268`) solo muestra lo sellado.
- **NBA/tenis:** sus sellos son propios (tenis `payload_sha256` por archivo; NBA `bundle.seal.json`) y no contienen precios. Un **overlay en servidor** es seguro si: (a) lee solo el recibo cuyo sha256/`received_at` ya está en el sello (inmutable, `received_at ≤ sealed_at`, sin retrospectiva); (b) no reescribe el JSON sellado ni el `seal`; (c) se etiqueta como «cuota de referencia de la observación usada al sellar», no como parte del sello; (d) la regla de elección (qué casa, mejor/Pinnacle/media) se fija antes y es determinista. Nada toca `odds_snapshots` ni triggers.
- Tenis ya sella algo útil sin leer nada más: `market_board.rows[].market` (prob. sin margen) y `books` → «cuota justa» `1/market` está **dentro del sello** hoy.

## 5. Presupuesto y licencia

- Overlay = 0 peticiones nuevas: solo lee objetos ya archivados. Uso real: 2.582 / 2.502 / 2.513 peticiones (28/29/30-oct) del tope 5.000; cabecera más reciente `x-daily-used 446` a las 02:16 UTC.
- Coste de lectura: las observaciones NBA son grandes (hasta 4 M outcomes/día; un `newest()` fusiona ~10 lotes). Conviene precalcular por recibo y cachear (el recibo es inmutable) en vez de leer en cada petición HTTP.
- Licencia: **no hay ninguna nota** en el repo ni en la memoria sobre términos de PropLine para mostrar cuotas en una app/feed público (búsqueda en docs/harness/memoria: 0 resultados). Precedente: el fútbol ya muestra en la app cuotas de PropLine (`ref_price`) y la escalera NBA/tenis también. Pendiente que el titular revise los términos de PropLine (plan Hobby) antes de ampliar; el proyecto es sin fines de lucro (CLAUDE.md, 27-oct).

## 6. Recomendación

**Overlay en servidor, leído del recibo sellado, sin campo sellado nuevo** (al menos de entrada):

1. **Tenis** (más fácil): el projector (`tenis_publico.projection`, corre en el host y escribe `tennis.json` vía `docker exec` en la API) añade por mercado `price` + `price_kind` + `books` + `odds_as_of`:
   - fase 1, sin leer el archivo: `fair_price = 1/market` del `market_board` sellado en la misma línea/selección (o `1/(1−market)` para la otra cara/`under`), con `books`. Es dato sellado; cobertura igual que la tabla de §2.
   - fase 2 (opcional): mejor precio real por casa leyendo `snapshot_id` del archivo; requiere que el cálculo corra donde está montado el volumen (la API o un contenedor con montaje RO), no en el host.
   - **Obligatorio**: `read_public_feed` hoy **descarta** cualquier mercado con `price` no nulo (`tenis_publico.py:206`) y añade `reference` fija; hay que cambiar ese filtro y los textos.
2. **NBA**: módulo nuevo en la API (o en el productor, como fichero aparte junto a la cohorte, no dentro de `bundle.json`) que, por cohorte, abre el recibo `prop_lines.sha256/received_at_utc`, une por `player_id` NBA / IDs de equipo y saca por fila: mejor casa blanda en la línea publicada (+ Pinnacle si existe), `books`, `odds_as_of`. Cachear por cohorte (inmutable). El panel `nba-dashboard` no monta el archivo: o se monta RO, o el overlay se sirve desde la API.
3. Regla de cuota única para los tres deportes (recomendado: la del fútbol, mejor `soft_books` en la misma observación, con `ref_book`), y para tenis/NBA defensivos aceptar Pinnacle o «mejor casa no DFS» si no hay blanda — decisión del titular.
4. Solo cuando esté validado, sellar el precio en los productores nuevos con fecha de corte (como se hizo con `live.provider = propline`); nunca reescribir sellos previos.

**Tamaño aproximado:** tenis 1-2 archivos (`tenis_publico.py` + tests) y textos en 6 idiomas en la app; NBA 1 módulo nuevo (`nba_cuotas.py` o similar) + endpoint/campo en `multimarket_live_dashboard.py` (`PUBLIC`/`PLAYER_PUBLIC` no incluyen precios hoy, `:20-23`) + tests; app: mostrar `price`, `ref_book`, `odds_as_of` (6 idiomas, `l10n_add.py`). Sin cambios de esquema SQL.

**Riesgos:** (1) confundir overlay con dato sellado — etiquetar y mantener fuera del hash; (2) líneas estadísticas de NBA casi sin precio (≈0 %), mostrar «sin cuota» en vez de inventar; (3) precios de alternativas lejos de la línea principal (totales NBA) pueden ser poco representativos; (4) lista blanda casi vacía en tenis y en robos/tapones/pérdidas NBA; (5) coste de E/S del archivo NBA (cachear); (6) recolector con `exit_code 1` intermitente (504) — un recibo ausente deja la hora sin precio; (7) términos de PropLine sin revisar.

**No posible hoy (sin fuente):** tenis tie-break (0/63, PropLine casi no cotiza `total_tiebreaks` fuera de DFS); NBA filas con umbral estadístico (~50 % de las filas de jugador; precio solo en 0-20 % y nunca en casa blanda); robos/tapones/robos+tapones/pérdidas con casa blanda (0 %); los 16 % de partidos de tenis sin emparejar en PropLine; sets_handicap de tenis con 1 sola casa (Fanatics), sin de-vig fiable.

Nota: `.superpowers/` **no** aparece como ignorado por `git check-ignore`; revisar antes de cualquier `git add -A`.
