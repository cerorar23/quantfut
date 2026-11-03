# Cuotas de referencia en los mercados de NBA y tenis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cada mercado de NBA y tenis que publica la app muestra su cuota de referencia real (mejor precio de cualquier casa no DFS, con el nombre de la casa y la hora de la captura) o «—» cuando no existe ninguna.

**Architecture:** Un *overlay* en la API (no un campo sellado): para cada evento publicado se relee la observación del archivo PropLine compartido que ya usó el sello (inmutable) y se extrae el mejor precio por mercado, línea y lado. Dos endpoints nuevos (`/web/deportes/nba/cuotas`, `/web/deportes/tenis/cuotas`) devuelven esos precios; la app los pide aparte y los une a sus mercados. No se reescribe ningún sello, no se toca el hash, no hay cambios de esquema SQL ni peticiones nuevas a PropLine.

**Tech Stack:** Python 3.12 + FastAPI (src/qf/api), archivo PropLine (`qf.ingest.propline_shared`), pytest; Flutter/Dart (apps/mobile), ARB en 6 idiomas.

**Spec:** `.superpowers/reconocimiento_cuotas_nba_tenis.md` (reconocimiento del 31-oct, en el checkout principal; copiado a `docs/cuotas_nba_tenis_reconocimiento_20261031.md` en la Task 0) y las decisiones del titular del 31-oct (abajo).

## Global Constraints

- Decisiones del titular (31-oct-2026): (1) la cuota mostrada es **la mejor cuota de cualquier casa no DFS** de la observación usada al sellar, con `book` y `as_of`; (2) donde no haya ninguna fuente (tie-break de tenis, filas NBA con umbral estadístico, hándicap NBA, partidos de tenis sin emparejar) se muestra **«—»** con el pronóstico visible: nunca se inventa una cuota, nunca se usa «cuota justa».
- Un precio válido es un precio de **dos lados en la misma línea** del mercado publicado, partido completo, sin banderas DFS, intercambio ni en juego. Selección: máximo precio decimal entre las casas elegibles; empate → la casa de orden alfabético menor (determinista).
- Los sellos y su hash (`bundle.seal.json` de NBA, `payload_sha256` de tenis) **no se modifican**. La cuota se etiqueta «cuota de referencia de la observación usada al sellar», fuera del sello; solo se lee `received_at ≤ sealed_at` (sin retrospectiva).
- Cero peticiones nuevas a PropLine: solo se leen objetos ya archivados. Prohibido llamar a `/odds` desde la API.
- NBA: unión por IDs oficiales (`nba:<teamId>`, `nba:<personId>`) como en `apps/nba/src/nba/prop_lines.py:42-91`; tenis: por `forecast.market_board.event_id` y `snapshot_id` ya sellados (`tennis_odds_propline_v1`). Sin uniones por parecido de nombres.
- El resultado por cohorte/evento es inmutable: se cachea en memoria por clave de recibo (sha256). Un evento sin recibo o sin precio devuelve `null`, no 500.
- Endpoints públicos, `Cache-Control: no-store`, sin datos de cuentas, mismo límite de peticiones que `/web/*`. Respuesta con `state` (`ok|partial|unavailable`), `generated_at`, `source: "PropLine"`.
- App: textos en los 6 idiomas con `l10n_add.py`; el precio en la fuente mono, la casa y la hora en texto secundario; el ámbar sigue reservado a compra; nunca se muestra un precio sin su `book` y `as_of`. Una cuota de un mercado distinto al mostrado (otra línea, otro lado) nunca se enseña.
- Base de trabajo: rama `cuotas-nba-tenis` desde `app/nba-tenis-rediseno` (PR #220 abierto); el PR de esta rama apunta a esa rama. Protocolo CLAUDE.md: antes de tocar código del servidor, el arnés de fútbol/API debe estar en verde (Task 0). **No se despliega nada**: el despliegue sigue DEPLOYS.md y la decide el titular.
- Pendiente del titular, fuera de este código: revisar los términos de PropLine (plan Hobby) para mostrar cuotas públicamente; no hay ninguna nota en el repo.

## Review Focus

1. Un recibo ausente o ilegible (504 intermitente del recolector): el evento sale sin precio, la respuesta es 200 con `state: partial`, nunca 500. → prueba en Task 3 y Task 4.
2. La línea publicada no coincide con ninguna línea del recibo (umbral estadístico NBA): precio `null`, no el de la línea más cercana. → prueba en Task 2 y Task 3.
3. Mismo precio en varias casas, o precios con un solo lado, o `price <= 1`: se descartan los de un lado; empate resuelto de forma determinista. → prueba en Task 1.
4. El lado mostrado: la app enseña «Más de» (NBA) o el ganador elegido; debe recibir el precio de **ese** lado, no el del contrario. → prueba en Task 3 (overlay) y Task 6 (app).
5. Cuota más vieja que el sello o posterior a él: se rechaza. → prueba en Task 1.

---

### Task 0: Rama, arnés base y documentos

**Files:**
- Create: `docs/cuotas_nba_tenis_reconocimiento_20261031.md` (copia del reconocimiento)
- Modify: ninguno de código

- [ ] **Step 1:** Crear la rama `cuotas-nba-tenis` desde `app/nba-tenis-rediseno` en el worktree `C:/Users/huye/Documents/qf-app-nba-tenis`; copiar el plan y el reconocimiento (`C:/Users/huye/Documents/apuesta proyec/.superpowers/reconocimiento_cuotas_nba_tenis.md`) y commitear.
- [ ] **Step 2:** Dar al worktree acceso de solo lectura al `.venv` del checkout principal (enlace/junction, git-ignored) y ejecutar `./scripts/test_local_windows.ps1 -Suite all` (o las suites de fútbol/API que cubren `src/qf/api`) para fijar la línea base: anotar los conteos exactos en el informe de la tarea. Si algo falla en la base, es la única tarea hasta arreglarlo (CLAUDE.md).
- [ ] **Step 3:** Commit `Docs: plan y reconocimiento de cuotas de NBA y tenis`.

### Task 1: Selección de la mejor cuota (núcleo puro)

**Files:**
- Create: `src/qf/ingest/cuotas_referencia.py`
- Test: `tests/test_cuotas_referencia.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Quote: price: float; book: str; as_of: str; books: int` y `def best_quote(outcomes: Iterable[Mapping], *, line: float | None, side: str, sealed_at: datetime, received_at: datetime) -> Quote | None`. `outcomes` son filas del archivo (usar el esquema real que lea `propline_shared`: casa, precio decimal, línea, lado, banderas). `side ∈ {"home","away","over","under","A","B","yes","no"}`.

- [ ] **Step 1: tests (rojo)** `test_best_quote_*`: (a) máximo entre casas no DFS en la misma línea y lado → `Quote(price=max, book=…, books=N)`; (b) empate de precio → casa alfabéticamente menor; (c) casa DFS / intercambio / en juego / periodo distinto de partido completo → excluida; (d) una casa con solo un lado → excluida; (e) `price <= 1.0` o no finito → excluida; (f) línea distinta de `line` → `None` (no se usa la más cercana); (g) `received_at > sealed_at` → `None`; (h) lista vacía → `None`.
- [ ] **Step 2:** `pytest tests/test_cuotas_referencia.py -v` → FAIL (módulo inexistente).
- [ ] **Step 3: Implementar** `best_quote` reutilizando las funciones de flags/normalización de `src/qf/ingest/propline_shared.py` y `apps/tennis/tennis_odds_propline_v1` en lugar de duplicarlas (leerlas antes; si viven en otro paquete, importar o extraer lo mínimo).
- [ ] **Step 4:** el test pasa. **Step 5: Commit** `Cuotas: selección de la mejor cuota no DFS`.

### Task 2: Overlay de tenis

**Files:**
- Create: `src/qf/api/cuotas_tenis.py`
- Test: `tests/test_cuotas_tenis.py` (con un archivo PropLine sintético mínimo en `tmp_path`)

**Interfaces:**
- Consumes: `best_quote` (Task 1); lector del archivo (`propline_shared.read`/`newest` por `snapshot_id`/sha256); `forecast.market_board` sellado.
- Produces: `def tennis_quotes(event: Mapping, archive: Path) -> dict[str, QuoteOut | None]` con claves iguales a los `id` de mercado del feed (`winner`, `games_total-3`, …) y `QuoteOut = {price, book, as_of, books, side}`; `def tennis_overlay(archive: Path, feed: Mapping) -> dict` con el formato del endpoint (`{state, generated_at, source, events: {event_id: {market_id: QuoteOut|None}}}`).
- Mapeo mercado→familia: el de `FAMILIES` de `tennis_odds_propline_v1` (winner→h2h, games_total→totals/total_games, games_handicap→spreads, sets_total→total_sets, sets_handicap→set_spread, set_winner→h2h+periodo sN, tiebreak→total_tiebreaks).

- [ ] **Step 1: tests (rojo):** ganador con precio de dos casas → mejor precio y casa; `games_total` con la línea del mercado presente/ausente (ausente → `null`); `tiebreak` sin cotización → `null`; evento sin `market_board` o sin recibo → todos `null` y `state: partial`; selección «B» devuelve el precio del jugador B y no el de A; el recibo se lee una sola vez por evento (contador en un archivo falso).
- [ ] **Step 2:** FAIL. **Step 3: Implementar** con caché en memoria por `snapshot_id`. **Step 4:** PASS. **Step 5: Commit** `Cuotas: overlay de tenis`.

### Task 3: Overlay de NBA

**Files:**
- Create: `src/qf/api/cuotas_nba.py`
- Test: `tests/test_cuotas_nba.py`

**Interfaces:**
- Consumes: `best_quote`; sellos de cohorte (`prop_lines.sha256`, `received_at_utc`, `slot`, `component_requests`) en el JSON de `/nba/api/data` o en `live13/cohorts`; unión por IDs NBA como `prop_lines.py:42-91`.
- Produces: `def nba_quotes(cohort: Mapping, archive: Path) -> dict[str, dict[str, QuoteOut | None]]` indexado por `event_id` y por clave de fila `"{market}|{player_id or ''}|{line or ''}"`, con `QuoteOut` por lado (`{"over": …, "under": …}` para mercados con línea; `{"home": …, "away": …}` para `winner`); `def nba_overlay(archive: Path, data: Mapping) -> dict` con el mismo formato de endpoint que tenis.
- Para hallar las cohortes y sellos en la API: leer la misma fuente que ya sirve `/nba/api/data` (investigar cómo la API accede a las cohortes; si el panel `nba-dashboard` es el único que las lee, la API debe leer los ficheros de `live13/cohorts` montados en solo lectura o pedir `/nba/api/data` internamente — el implementador debe decidir con evidencia y dejarlo en el informe; no montar nada en producción en esta tarea).

- [ ] **Step 1: tests (rojo):** `winner` con precio → `home` y `away`; `player_points` con línea PropLine presente → `over` y `under`; fila con umbral estadístico (sin línea en el recibo) → `null`; `steals/blocks` solo en casas DFS → `null`; jugador sin `nba:<id>` en el recibo → `null`; cohorte con `sin_archivo_reciente` → todo `null` y `state: partial`; resultado idéntico en dos llamadas con un solo acceso al archivo (caché por sha256).
- [ ] **Step 2:** FAIL. **Step 3: Implementar.** **Step 4:** PASS. **Step 5: Commit** `Cuotas: overlay de NBA`.

### Task 4: Endpoints de la API

**Files:**
- Modify: `src/qf/api/web.py` (dos rutas) y, si hace falta, `src/qf/api/main.py` (límite/scope)
- Test: `tests/test_web_cuotas.py`

**Interfaces:** `GET /web/deportes/tenis/cuotas` y `GET /web/deportes/nba/cuotas` → JSON del overlay, `Cache-Control: no-store`, `state ∈ {ok, partial, unavailable}`; nunca 500 por falta de archivo (devuelve `unavailable`).

- [ ] **Step 1: tests (rojo):** 200 con formato exacto y cabecera `no-store`; archivo ausente → 200 `unavailable`; recibo corrupto en un evento → 200 `partial` con el resto bien; sin credenciales ni campos de cuenta en la respuesta.
- [ ] **Step 2:** FAIL. **Step 3: Implementar** reutilizando los overlays de las Tasks 2-3; añadir un tope de tiempo/tamaño razonable. **Step 4:** PASS + suite de fútbol/API en verde (`-Suite all` o la de API) sin regresiones. **Step 5: Commit** `Cuotas: endpoints públicos de cuotas de NBA y tenis`.

### Task 5: Modelo y carga en la app

**Files:**
- Modify: `apps/mobile/lib/product/sports_feed.dart` (`SportMarket.quote`), crear `apps/mobile/lib/product/sports_quotes.dart`
- Test: `apps/mobile/test/sports_quotes_test.dart` + fixtures `test/fixtures/quotes_nba.json`, `quotes_tennis.json`

**Interfaces:**
- Produces: `class SportQuote { double price; String book; DateTime asOf; int books; }`; `SportQuote? quoteFor(SportEvent e, SportMarket m, QuotesOverlay overlay)` que aplica el lado correcto (NBA: «Más de» → `over`; ganador → el lado elegido; tenis: por `id`); `class QuotesOverlay { static const empty; factory QuotesOverlay.fromJson(Object? json); }` (JSON nulo, listas o tipos raros → `empty`); `Future<QuotesOverlay> loadQuotes(QuantFutApi api, SportKind sport)` (nunca lanza); `SportMarket` gana `SportQuote? quote` (no obligatorio).

- [ ] **Step 1: tests (rojo):** lado correcto (ganador visitante recibe el precio del visitante); `price <= 1` o no finito → sin cuota; overlay corrupto → `empty`; feed de cuotas caído → los mercados quedan sin cuota y el resto funciona; precio presente sin `book` → se descarta.
- [ ] **Step 2:** FAIL. **Step 3: Implementar**; la carga se hace en el shell junto a la del feed del deporte (reutilizar el cargador perezoso existente; un fallo no pisa un overlay bueno anterior). **Step 4:** PASS. **Step 5: Commit** `App: carga y unión de cuotas de NBA y tenis`.

### Task 6: Pintar la cuota en las pantallas

**Files:**
- Modify: `apps/mobile/lib/product/home_sport.dart`, `sport_predictions.dart`, `sport_detail.dart` (+ `sport_markets.dart` si muestra líneas), l10n ARB
- Test: ampliar `home_sport_test.dart`, `sport_predictions_test.dart`, `sport_detail_test.dart`; **cambiar** las pruebas que afirmaban «sin `@`» por «nunca una cuota inventada»

**Interfaces:** `Widget quoteLabel(BuildContext, SportQuote?)`: con cuota → `@1,90` (mono, `QfColors.text`) y debajo `{book} · {hora}` (texto secundario); sin cuota → `—` con semántica «sin cuota». Claves l10n nuevas (6 idiomas): `quoteReference` («Cuota de referencia al sellar»), `quoteNone`, `quoteBookAt` (`{book} · {time}`).

- [ ] **Step 1: tests (rojo):** con overlay: la tarjeta de Predicciones y la fila de la ficha muestran `@1,90` y la casa; sin cuota muestran `—` y siguen mostrando probabilidad; nunca aparece un `@` en un mercado sin `SportQuote`; el formato decimal sigue el idioma (coma/punto); en la ficha aparece una vez la leyenda `quoteReference`.
- [ ] **Step 2:** FAIL. **Step 3: Implementar.** **Step 4:** análisis limpio y `flutter test` completo en verde; `l10n_test` pasa. **Step 5: Commit** `App: cuotas de referencia en los mercados de NBA y tenis`.

### Task 7: Verificación y registro

- [ ] **Step 1:** Servidor: arnés completo en verde (conteos). App: `flutter analyze` y `flutter test` completos.
- [ ] **Step 2:** Con datos reales de solo lectura: ejecutar los overlays contra una copia/lectura del archivo (`ssh quantfut`, `docker exec quantfut-api-1 python …` **sin escribir**, sin red) para 3 partidos NBA y 3 de tenis recientes; anotar cobertura medida por mercado y comparar con la tabla del reconocimiento (±5 puntos).
- [ ] **Step 3:** Actualizar `harness/tareas.md` y `harness/progreso.md` (decisión clave: overlay fuera del sello, mejor cuota no DFS, «—» sin fuente) y `DEPLOYS.md` con la propuesta de despliegue y vuelta atrás (sin desplegar).
- [ ] **Step 4:** Commit `Docs: registro de las cuotas de NBA y tenis`; push de la rama `cuotas-nba-tenis` y PR hacia `app/nba-tenis-rediseno` **solo si el titular lo confirma**.

---

## Fuera de alcance

1. Sellar el precio en los productores (cambio de protocolo con fecha de corte): solo tras validar el overlay.
2. Cuota justa (1/probabilidad) y cualquier cuota inventada.
3. Mostrar cuotas «en vivo»: siempre es la observación usada al sellar.
4. Despliegue a producción, montar el archivo en `nba-dashboard` y revisar los términos de PropLine.
