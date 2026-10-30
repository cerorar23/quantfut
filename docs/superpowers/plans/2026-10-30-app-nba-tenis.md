# App Flutter: NBA y tenis + rediseño v3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La app Flutter muestra fútbol, NBA y tenis con un selector de deporte global y la piel v3 (azul + ámbar, estética CyberCore), en todas sus ventanas.

**Architecture:** El deporte es estado de `ProductShell` (como `tab` y `stream`) y filtra Inicio, Predicciones y Mercados. Fútbol sigue usando `/mobile/v1/home`. NBA y tenis se leen de los feeds públicos que ya usa la web (`/nba/api/data`, `/web/deportes/tenis`), adaptados en Dart con la misma semántica que `frontend/sports-data.js`. Las imágenes vienen del servidor (`/web/escudos`, `/web/imagenes/...`). La piel nueva entra por tokens: las constantes `live*` pasan a apuntar a la paleta v3, así que no hay que tocar cada archivo para el color.

**Tech Stack:** Flutter ≥3.47.7 / Dart ≥3.13.5, `provider`, `shared_preferences`, `flutter_test`, `intl` + ARB (6 idiomas).

**Spec:** `apps/mobile/docs/REDISENO_NBA_TENIS_20261030.md` (v3, con §5 bis y §5 ter). Prototipo navegable: https://claude.ai/artifact/MhCwwt744pDkBbbhJLvhr7

## Global Constraints

- Base de trabajo: worktree nuevo desde `origin/main` (`45bf003` o posterior), rama `app/nba-tenis-rediseno`. **No** desde `nba/v13-disponibilidad`, que tiene cambios ajenos sin commitear. La `main` local está atrasada.
- Flutter: `C:\flutter\bin\flutter` (no está en el PATH). Pruebas: `C:\flutter\bin\flutter test` en `apps/mobile`.
- Textos visibles: en los 6 idiomas (es, en, pt, fr, it, de) en el mismo commit, con `python apps/mobile/tool/l10n_add.py`. Ninguna cadena fija en los widgets. `test/l10n_test.dart` debe pasar.
- Paleta (exacta): `bg #070B14`, `surface #0F1829`, `surface2 #16223A`, `border #26365A`, `text #EEF3FF`, `text2 #9DACCB`, `muted #7F8DAD`, `primary #4C8DFF`, `cta #FFB020`, `success #2BD99F`, `danger #FF6B6B`; deportes `football #22D3EE`, `nba #B58CFF`, `tennis #D4F53C`. Texto sobre `cta`: `#1A1200`. Texto sobre `primary`: `#04122E` (nunca blanco).
- Una sola acción ámbar por pantalla. El ámbar solo se usa para VIP, desbloquear y monedas.
- La probabilidad va en `primary`. Las cuotas, cuando existan, en `text` con la fuente mono.
- Fuentes: Rajdhani 500/700 (titulares y chips, en mayúsculas), JetBrains Mono 500 (cifras y hashes), Gilroy (cuerpo). Licencia OFL, empaquetadas en `apps/mobile/fonts/`.
- Esquinas cortadas: 12 dp en tarjetas y 8 dp en chips (arriba-derecha y abajo-izquierda). Brillo como mucho en un elemento por pantalla.
- Objetivos táctiles ≥ 44 dp. Animaciones a cero con `MediaQuery.disableAnimations`. El color nunca es la única señal (✓ / ✗ / candado).
- NBA y tenis: nunca se inventan cuotas (`price` nulo = no se muestra cuota). Se descartan `validation_hold` y probabilidades fuera de (0,1). Solo cuenta como acierto lo sellado antes del inicio (`eligible`).
- Imágenes: solo URLs del servidor. Si falta una o falla, se muestran iniciales o bandera, nunca la foto de otra persona. Las fotos de tenis (CC BY-SA) llevan crédito visible.
- Cada build para Play sube `version:` en `pubspec.yaml`. La actual es `1.0.0+3`; la nueva será `1.1.0+4`.
- Sin cambios de servidor en esta entrega: todos los endpoints que se usan ya existen en `origin/main`.

## Review Focus

1. Un feed caído (por ejemplo `/nba/api/data` devuelve 503): solo ese deporte muestra el aviso con «Reintentar»; fútbol y tenis siguen funcionando. → pruebas en Task 4 y Task 7.
2. Imagen ausente o 404 (Sinner, un jugador NBA sin caché): se ven iniciales o la bandera, nunca el icono de imagen rota. → prueba en Task 5.
3. El usuario oculta el deporte que tenía por defecto, o intenta ocultarlos todos: se abre el primero visible y siempre queda al menos uno. → pruebas en Task 3 y Task 10.
4. Un partido cuya hora local cruza la medianoche: se agrupa por el día local del usuario, como hace `groupAgenda`. → prueba en Task 7.
5. Una preferencia guardada con un id desconocido (versión vieja o dato corrupto): vuelve a fútbol sin fallar. → prueba en Task 3.

---

### Task 1: Tokens v3, fuentes y piel global

**Files:**
- Create: `apps/mobile/lib/product/qf_theme.dart`
- Modify: `apps/mobile/lib/product/live_widgets.dart:7-21` (las constantes `live*` y `liveTheme()` delegan en `QfColors` y `qfTheme()`)
- Modify: `apps/mobile/pubspec.yaml` (fuentes `Rajdhani` 500/700 y `JetBrains Mono` 500; `version: 1.1.0+4`)
- Create: `apps/mobile/fonts/Rajdhani-Medium.ttf`, `Rajdhani-Bold.ttf`, `JetBrainsMono-Medium.ttf`, `apps/mobile/fonts/OFL-Rajdhani.txt`, `OFL-JetBrainsMono.txt`
- Test: `apps/mobile/test/qf_theme_test.dart`

**Interfaces:**
- Produces: `abstract final class QfColors` con las constantes de la paleta (nombres: `bg, surface, surface2, border, text, text2, muted, primary, onPrimary, cta, onCta, success, danger, football, nba, tennis`); `ThemeData qfTheme()`; `double contrastRatio(Color a, Color b)` (WCAG 2.1); `const qfDisplay = 'Rajdhani'`, `const qfMono = 'JetBrains Mono'`.
- `liveBg → QfColors.bg`, `livePanel → QfColors.surface`, `liveCyan → QfColors.primary`, `liveGold → QfColors.cta`, `liveGreen → QfColors.success`, `liveMuted → QfColors.text2`.

- [ ] **Step 0: Preparar el worktree.** Crear el worktree desde `origin/main` en la rama `app/nba-tenis-rediseno`. Copiar a él este plan y la especificación (`apps/mobile/docs/REDISENO_NBA_TENIS_20261030.md`), que están sin commitear en la rama `nba/v13-disponibilidad`, y commitearlos: `Docs: diseño y plan de NBA y tenis en la app`.
- [ ] **Step 1: Write the failing test** `qf_theme_test.dart`:
  - `test('texto legible en los tres fondos')`: para cada color de `[text, text2, muted, primary, cta, success, danger, football, nba, tennis]` y cada fondo de `[bg, surface, surface2]`, `expect(contrastRatio(c, f), greaterThanOrEqualTo(4.5))`.
  - `test('texto sobre botones')`: `contrastRatio(onCta, cta) >= 4.5`, `contrastRatio(onPrimary, primary) >= 4.5`, y `contrastRatio(Colors.white, primary) < 4.5` (documenta por qué no se usa blanco).
  - `test('los alias live* apuntan a la paleta v3')`: `expect(liveBg, QfColors.bg)` y lo mismo para los seis alias.
- [ ] **Step 2: Run** `C:\flutter\bin\flutter test test/qf_theme_test.dart` → FAIL (`QfColors` no existe).
- [ ] **Step 3: Implement** `qf_theme.dart` y los alias. Las fuentes OFL salen de los repos oficiales de Google Fonts (`google/fonts` → `ofl/rajdhani`, `ofl/jetbrainsmono`), con su `OFL.txt`.
- [ ] **Step 4: Run** el test → PASS. Run `C:\flutter\bin\flutter test` (toda la suite) → las pruebas que comparaban colores literales viejos se actualizan a `QfColors`; ninguna otra cambia.
- [ ] **Step 5: Commit** `App: tokens v3 (azul y ámbar), Rajdhani y JetBrains Mono, versión 1.1.0+4`

### Task 2: Piezas visuales reutilizables

**Files:**
- Create: `apps/mobile/lib/product/qf_shapes.dart`
- Test: `apps/mobile/test/qf_shapes_test.dart`

**Interfaces:**
- Consumes: `QfColors`, `qfMono` (Task 1).
- Produces:
  - `class CutCornerBorder extends OutlinedBorder { const CutCornerBorder({double cut = 12, BorderSide side = BorderSide.none}); }`
  - `class QfCard extends StatelessWidget { const QfCard({required Widget child, Color? accent, VoidCallback? onTap, EdgeInsets padding = const EdgeInsets.all(12)}); }`, con corchetes de 16 dp y 2 dp en `accent` cuando no es nulo, y `InkWell` recortado por la forma.
  - `class QfBadge extends StatelessWidget { const QfBadge(String label, {required Color color, IconData? icon}); }`: mayúsculas, borde 1 dp y relleno al 13 %.
  - `class SegmentedBar extends StatelessWidget { const SegmentedBar({required int total, required int filled, Color color = QfColors.primary, int? current}); }`
  - `class ProbabilityBar extends StatelessWidget { const ProbabilityBar({required List<(String label, double value)> parts}); }` para 2 o 3 partes (la mayor en `primary`) con su leyenda mono.
  - `class SealLine extends StatelessWidget { const SealLine({required String seal, required DateTime publishedAt}); }`, que muestra `> SELLO abcd…wxyz` y `> PUBLICADO HH:mm UTC · VERIFICADO`.

- [ ] **Step 1: Write the failing tests:**
  - `testWidgets('SegmentedBar pinta filled de total')`: con `total: 6, filled: 3`, hay 6 segmentos y 3 con `color`.
  - `testWidgets('ProbabilityBar acepta 2 y 3 partes y rechaza otras')`: con 1 o 4 partes lanza `AssertionError`; con `[('LAL',.41),('BOS',.59)]` muestra `LAL 41 %` y `BOS 59 %` (separador de `realPercent`).
  - `testWidgets('SealLine acorta el hash')`: `seal: '9f3a1234567890c21e'` muestra `9f3a…c21e`.
  - `testWidgets('QfCard es pulsable a 44 dp o más')`: `tester.getSize(find.byType(InkWell)).height >= 44`.
- [ ] **Step 2: Run** `C:\flutter\bin\flutter test test/qf_shapes_test.dart` → FAIL.
- [ ] **Step 3: Implement** `qf_shapes.dart`. `CutCornerBorder.getOuterPath` construye el polígono de 6 puntos con corte arriba-derecha y abajo-izquierda.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `App: piezas visuales v3 (tarjeta con corte, insignia, barras, sello)`

### Task 3: Deportes, preferencias y selector

**Files:**
- Create: `apps/mobile/lib/product/sports.dart`, `apps/mobile/lib/product/sport_selector.dart`
- Modify: `apps/mobile/lib/l10n/app_*.arb` (claves `sportFootball`, `sportNba`, `sportTennis`, `sportSelectorLabel`, `sportMore`)
- Test: `apps/mobile/test/sports_test.dart`

**Interfaces:**
- Produces:
  - `enum SportKind { football, nba, tennis }` con `String get id` (`'futbol'|'nba'|'tenis'`) y `static SportKind? fromId(String?)`.
  - `class SportSpec { final SportKind kind; final Color accent; final IconData icon; final Set<String> streams; String label(AppLocalizations l10n); }` y `const sportSpecs = <SportKind, SportSpec>{...}`. `streams`: fútbol `{'high','ladder','parley'}`; NBA y tenis `{'high'}`.
  - `class SportPrefs { SportPrefs({required Future<String?> Function(String key) read, required Future<void> Function(String key, String value) write}); Future<List<SportKind>> order(); Future<Set<SportKind>> hidden(); Future<SportKind> initial(); Future<void> save({required List<SportKind> order, required Set<SportKind> hidden}); Future<void> remember(SportKind last); }`. Claves: `sports_order`, `sports_hidden`, `sports_last`.
  - `class SportSelector extends StatelessWidget { const SportSelector({required List<SportKind> sports, required SportKind value, required ValueChanged<SportKind> onChanged, Map<SportKind,int> counts = const {}}); }`: chips de 44 dp con icono y texto, `Semantics(selected:)`; con más de 4 deportes la fila se desplaza y el último chip dice `sportMore`.

- [ ] **Step 1: Write the failing tests** (`sports_test.dart`, con `read` y `write` sobre un `Map` en memoria):
  - `test('id desconocido vuelve a fútbol')`: con `sports_last='baloncesto'`, `initial()` devuelve `SportKind.football`.
  - `test('no se pueden ocultar todos')`: con `save(order: SportKind.values, hidden: SportKind.values.toSet())`, `hidden()` devuelve un conjunto de tamaño 2 que no incluye `order.first`.
  - `test('si el por defecto está oculto, abre el primero visible')`: con `order=[nba, football, tennis]`, `hidden={nba}` y sin `sports_last`, `initial()` devuelve `football`.
  - `testWidgets('SportSelector marca el seleccionado y avisa al tocar')`: `find.bySemanticsLabel(RegExp('NBA'))` con `selected: true`; un toque en «Tenis» llama a `onChanged(SportKind.tennis)`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Iconos: `Icons.sports_soccer`, `Icons.sports_basketball`, `Icons.sports_tennis`. Textos por `context.l10n` (añadidos con `l10n_add.py` en los 6 idiomas).
- [ ] **Step 4: Run** `flutter test test/sports_test.dart test/l10n_test.dart` → PASS.
- [ ] **Step 5: Commit** `App: deportes, preferencias de orden y selector`

### Task 4: Feeds de NBA y tenis

**Files:**
- Create: `apps/mobile/lib/product/sports_feed.dart`
- Create: `apps/mobile/test/fixtures/nba_feed.json`, `apps/mobile/test/fixtures/tennis_feed.json` (recortes reales de producción: 2 eventos cada uno, sin datos de cuentas)
- Test: `apps/mobile/test/sports_feed_test.dart`

**Interfaces:**
- Consumes: `QuantFutApi.request(String path)` (existente), `SportKind` (Task 3).
- Produces:
  - `class SportMarket { String id, label, selection; double probability; String? market, player, playerId; double? line; DateTime sealedAt; bool eligible; String? outcome; }`
  - `class SportEvent { String id; SportKind sport; String home, away, league; String? surface, score; DateTime start; String status; String seal; DateTime sealedAt; List<SportMarket> markets; JsonMap? availability; }`
  - `List<SportEvent> nbaEvents(JsonMap data)` y `List<SportEvent> tennisEvents(JsonMap data)`: lanzan `FormatException` si la forma no es la esperada.
  - `class SportFeed { final bool ready; final List<SportEvent> events; }` y `Future<SportFeed> loadSport(QuantFutApi api, SportKind sport)`, que usa `/nba/api/data` o `/web/deportes/tenis`; ante cualquier fallo devuelve `SportFeed(ready: false, events: [])`.
  - `SportMarket? featuredMarket(SportEvent e)`: el mercado con mayor probabilidad entre los `eligible`.

- [ ] **Step 1: Write the failing tests.** Cada prueba de `frontend/sports-data.test.mjs` (origin/main) se pasa a Dart con los mismos datos:
  - `test('NBA usa el lado y la probabilidad publicados')`: con fila `winner`, `probability_over .3` y `actual 0`, queda `selection == 'B'`, `probability == .7` y `outcome == 'win'`.
  - `test('revisión posterior al inicio no cuenta')`: con `performance_eligible:false` o `sealed_at_utc` posterior a `tipoff_utc`, queda `outcome == null` y `eligible == false`.
  - `test('NBA descarta cuarentena y probabilidades ausentes; usa la revisión más reciente')`.
  - `test('tenis exige estado ok/partial, sello y probabilidad')`: `seal: null` produce 0 eventos; sin `state` lanza `FormatException`.
  - `test('un feed caído no tumba al otro')`: con un `api` falso donde `/nba/api/data` lanza error, `loadSport(nba).ready == false` y `loadSport(tennis).ready == true`.
  - `test('fixtures reales se leen sin errores')`: cada fixture produce eventos con `markets.isNotEmpty` y `price` nunca presente.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** como port directo de `nbaEvents` y `tennisEvents` de `frontend/sports-data.js`, sin añadir lógica propia.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `App: lectura de los feeds públicos de NBA y tenis`

### Task 5: Imágenes del servidor y avatar

**Files:**
- Create: `apps/mobile/lib/product/sport_images.dart`
- Modify: `apps/mobile/lib/product/live_widgets.dart` (`TeamCrest` pasa a usar `QfAvatar`)
- Modify: ARB (`imageCredits`, `imageUnavailable`)
- Test: `apps/mobile/test/sport_images_test.dart`

**Interfaces:**
- Consumes: `QuantFutApi.base`, `QuantFutApi.request('/web/imagenes/manifiesto.json')`.
- Produces:
  - `class ImageCatalog { factory ImageCatalog.fromManifest(JsonMap m); String? nbaLogo(String abbr); TennisPhoto? tennisPhoto(String fullName); static const empty; }`. `nbaLogo` devuelve `/web/imagenes/nba/{ABBR}.png`. `tennisPhoto` busca por nombre en minúsculas sin tildes. Un manifiesto nulo o con listas da `ImageCatalog.empty`.
  - `class TennisPhoto { String path, author, license, page; }`
  - `String nbaPlayerPhoto(String playerId)` → `/web/imagenes/jugadores/nba/{id}.png`. Solo acepta ids `^[1-9][0-9]{0,7}$`; en otro caso devuelve `''` y el avatar cae a iniciales.
  - `class QfAvatar extends StatelessWidget { const QfAvatar({String? url, required String name, double size = 32, AvatarShape shape = AvatarShape.contain, String? countryCode, Color? ring}); }`. `contain` sirve para escudos y logos; `circle` para retratos, con `cover` al 15 % superior. `errorBuilder` y url vacía muestran las iniciales (2 letras) y, si hay `countryCode`, una bandera de 14×10.
  - `Future<ImageCatalog> loadImageCatalog(QuantFutApi api)`, que se cachea en memoria y vuelve a intentar al refrescar si falló.

- [ ] **Step 1: Write the failing tests:**
  - `test('manifiesto inválido da catálogo vacío')`: con `null`, `{'nba': []}` o `{'tenis': 'x'}` el resultado es `ImageCatalog.empty`.
  - `test('tenis encuentra por nombre con tildes y mayúsculas')`: con `{'tenis': {'carlos alcaraz': {'f':'carlos-alcaraz.jpg','a':'X','l':'CC BY-SA 4.0','p':'https://commons...'}}}`, `tennisPhoto('Carlos Alcaraz')?.path == '/web/imagenes/tenis/carlos-alcaraz.jpg'` y `tennisPhoto('Jannik Sinner') == null`.
  - `test('id NBA inválido no produce URL')`: `nbaPlayerPhoto('0') == ''` y `nbaPlayerPhoto('../x') == ''`.
  - `testWidgets('imagen que falla muestra iniciales, no icono roto')`: `QfAvatar(url: '/no-existe.png', name: 'Jannik Sinner')` con `HttpOverrides` de prueba que devuelve 404 → `find.text('JS')` y ningún `Icon(Icons.broken_image)`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Las imágenes se resuelven con `api.base.resolve(path)` y el `User-Agent` de `TeamCrest`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `App: escudos, logos y fotos desde el servidor con respaldo de iniciales`

### Task 6: Shell con deporte, cabecera y barra v3

**Files:**
- Modify: `apps/mobile/lib/product/live_shell.dart` (estado `SportKind sport`, carga de `SportPrefs`, `SportSelector` encima del contenido en Inicio, Predicciones y Mercados; cabecera `// QUANTFUT`; `NavigationBar` v3)
- Modify: `apps/mobile/lib/product/predictions_switcher.dart` (indicador `primary`, texto `onPrimary`; `segments` se recibe por parámetro desde `sportSpecs[sport].streams`; iconos `track_changes`, `stairs_outlined` y `confirmation_number_outlined` encima del texto, como hoy)
- Test: `apps/mobile/test/product_navigation_test.dart` (ampliar), `apps/mobile/test/predictions_ui_test.dart` (ampliar)

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: `ProductShell` expone `SportKind sport` a sus hijos por parámetro; `PredictionsSwitcher({required String value, required ValueChanged<String> onChanged, required List<String> streams, Map<String,int> badges})`; `PredictionsSwitcher.swipe(current, velocity, streams)`.

- [ ] **Step 1: Write the failing tests:**
  - `testWidgets('el selector aparece en Inicio, Predicciones y Mercados y no en Coins ni Perfil')`.
  - `testWidgets('en NBA el switcher solo muestra Alta prob.')`: `find.byKey(ValueKey('streams-ladder'))` no aparece.
  - `testWidgets('cambiar de deporte no cambia de pestaña y se recuerda')`: tras tocar «Tenis», `sports_last == 'tenis'` y `tab` sigue igual.
  - `testWidgets('deslizar cambia de tipo, no de deporte')`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** toda la suite → PASS.
- [ ] **Step 5: Commit** `App: selector de deporte global y cabecera y barra v3`

### Task 7: Inicio por deporte (destacado con imagen y agenda con miniaturas)

**Files:**
- Create: `apps/mobile/lib/product/home_hero.dart` (tarjeta «Destacado del día» con `CustomPainter` de la cancha por deporte: campo, pista NBA, pista de tenis; con los dos avatares grandes y la probabilidad)
- Create: `apps/mobile/lib/product/home_sport.dart` (Inicio de NBA y tenis: destacado, resumen, boletos, `DayStrip`, fila «Jugadores con pronóstico» solo en NBA y agenda)
- Modify: `apps/mobile/lib/product/live_home.dart` (fútbol: destacado arriba, `MatchRow` con `QfAvatar` de 32 dp, piel v3)
- Modify: `apps/mobile/lib/product/home_agenda.dart` (agrupación: fútbol por competición, NBA por hora, tenis por torneo y ronda; `groupAgenda` sigue usando el día local)
- Modify: ARB (`homeFeatured`, `homePlayersWithPicks`, `homeFeedError`, `homePhotoCredits`)
- Test: `apps/mobile/test/home_screen_test.dart` (ampliar), `apps/mobile/test/home_sport_test.dart`

**Interfaces:**
- Consumes: `SportFeed`, `featuredMarket`, `ImageCatalog`, `QfAvatar`, `QfCard`, `SportSelector`.
- Produces: `HomeSport({required SportKind sport, required SportFeed feed, required ImageCatalog images, required ValueChanged<SportEvent> onOpen, required Future<void> Function() onRetry})`; `class HomeHero extends StatelessWidget { const HomeHero({required SportKind sport, required Widget left, required Widget right, required String probability, required String pick, required String kicker, VoidCallback? onTap}); }`.

- [ ] **Step 1: Write the failing tests:**
  - `testWidgets('NBA muestra logos en la agenda y fotos en jugadores')`: con el fixture NBA, hay `QfAvatar` con url `/web/imagenes/nba/NYK.png` y otro con `/web/imagenes/jugadores/nba/1628973.png`.
  - `testWidgets('tenis muestra foto y bandera, y el crédito al pie')`: aparece `homePhotoCredits`.
  - `testWidgets('feed NBA caído: aviso y reintento solo en NBA')`: con `SportFeed(ready:false)` se ve `homeFeedError` y un botón que llama a `onRetry`; al cambiar a fútbol la agenda de fútbol se ve normal.
  - `testWidgets('partido 23:30 local del día 30 que en UTC es el 31 se agrupa el 30')`.
  - `testWidgets('el destacado abre el partido')`: un toque en `HomeHero` llama a `onOpen` con el evento del `featuredMarket` de mayor probabilidad.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `App: Inicio por deporte con destacado e imágenes`

### Task 8: Predicciones y Mercados de NBA y tenis

**Files:**
- Create: `apps/mobile/lib/product/sport_predictions.dart` (Alta prob. de NBA y tenis: tarjetas con avatares, selección, probabilidad y fecha de sello; sin cuota)
- Create: `apps/mobile/lib/product/sport_markets.dart` (familias por `market`; pestañas internas NBA *Partido | Jugadores* y tenis *Partido | Juegos*; % de acierto con `SegmentedBar` sobre los `eligible` resueltos)
- Modify: `apps/mobile/lib/product/live_shell.dart` (enruta por deporte)
- Modify: ARB (`marketsTabGame`, `marketsTabPlayers`, `marketsTabGames`, `predictionsSealedAt`)
- Test: `apps/mobile/test/sport_predictions_test.dart`

**Interfaces:**
- Consumes: `SportFeed`, `SportEvent`, `SportMarket`, `QfCard`, `QfBadge`, `SegmentedBar`.
- Produces: `SportPredictions({required SportFeed feed, required ImageCatalog images, required ValueChanged<SportEvent> onOpen})`; `SportMarkets({required SportKind sport, required SportFeed feed})`; `Map<String, ({int won, int resolved})> hitRateByFamily(List<SportEvent>)`.

- [ ] **Step 1: Write the failing tests:**
  - `test('hitRateByFamily cuenta solo eligible con outcome win/loss; push no cuenta')`.
  - `testWidgets('NBA/tenis nunca muestran cuota')`: no aparece ningún texto que empiece por `@`.
  - `testWidgets('pestaña Jugadores solo lista mercados player_*')`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `App: predicciones y mercados de NBA y tenis`

### Task 9: Ficha de partido NBA y tenis

**Files:**
- Create: `apps/mobile/lib/product/sport_detail.dart` (hoja inferior: cabecera NBA `VIS @ LOC` con logos o tenis con marcador por sets, fotos y bandera; pestañas Pronósticos, Análisis, H2H y Alertas; `SealLine`; crédito de las fotos de tenis)
- Modify: `apps/mobile/lib/product/live_shell.dart` (`detail()` abre `SportDetail` cuando el evento no es de fútbol)
- Modify: `apps/mobile/lib/product/live_detail.dart` (fútbol: piel v3, escudos con `QfAvatar`, `SealLine`)
- Modify: ARB (las etiquetas que falten; las pestañas ya existen: `detailTabPredictions`, `detailTabStats`, `detailTabH2h`, `detailTabAlerts`)
- Test: `apps/mobile/test/sport_detail_test.dart`

**Interfaces:**
- Consumes: `/web/deportes/nba/estadisticas/{event_id}` (id de 10 dígitos) y `/web/deportes/tenis/estadisticas/{event_id}`; si responden 404, la pestaña Análisis lo dice y el resto de la ficha funciona. Disponibilidad NBA: `SportEvent.availability`.
- Produces: `Future<void> showSportDetail(BuildContext context, {required QuantFutApi api, required SportEvent event, required ImageCatalog images})`.

- [ ] **Step 1: Write the failing tests:**
  - `testWidgets('estadísticas 404: Análisis avisa y Pronósticos sigue')`.
  - `testWidgets('tenis muestra el crédito de cada foto usada')`: aparecen autor y licencia de `TennisPhoto`.
  - `testWidgets('NBA lista disponibilidad con insignia y texto, no solo color')`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `App: ficha de partido de NBA y tenis`

### Task 10: Perfil con «Mis deportes» y resto de ventanas en v3

**Files:**
- Modify: `apps/mobile/lib/product/live_profile.dart` («Mis deportes»: orden con flechas, interruptor por deporte y deporte por defecto; usa `SportPrefs.save`. Fila «Versión de la app» que abre la comprobación de actualización)
- Modify, solo piel y textos: `live_more.dart` (más el acceso a «Mis deportes»), `live_guide.dart` (acordeón), `live_vip.dart` (acierto por deporte con `ImageCatalog` y el beneficio nuevo), `live_rewards.dart` (asistencia en 7 casillas y una sola acción ámbar), `core/firebase_preferences.dart`, `core/firebase_access.dart` (`FirebaseInbox` con etiqueta de deporte), `core/access_screen.dart` (error junto a la casilla en lugar de botón deshabilitado), `onbonding_screen/second_screen.dart`, `l10n/language_selection_screen.dart`, `l10n/language_picker.dart`, `core/app_update.dart`
- Modify: ARB (`welcome1Title` → «Fútbol, NBA y tenis,\ncon otra perspectiva», `welcome3Body` con props NBA y juegos de tenis, `vipBenefitSports*`, `profileMySports*`, `accessConsentRequired`), en los 6 idiomas
- Test: `apps/mobile/test/access_screen_test.dart`, `coins_ui_test.dart`, `app_update_test.dart` y `language_selection_test.dart` (actualizar), más `apps/mobile/test/profile_sports_test.dart`

**Interfaces:**
- Consumes: `SportPrefs`, `SportSelector`, `QfCard`, `QfBadge`, `SegmentedBar`, `QfColors`.

- [ ] **Step 1: Write the failing tests:**
  - `testWidgets('Acceso sin consentimiento muestra el error junto a la casilla y no inicia sesión')`.
  - `testWidgets('Mis deportes no permite apagar el último visible')`.
  - `testWidgets('Coins tiene una sola acción ámbar')`: hay exactamente 1 `FilledButton` con `backgroundColor == QfColors.cta`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**, ventana por ventana, con el [prototipo](https://claude.ai/artifact/MhCwwt744pDkBbbhJLvhr7) como referencia visual.
- [ ] **Step 4: Run** `C:\flutter\bin\flutter test` (toda la suite, incluida `test/l10n_test.dart`) y `python -m pytest tests/test_mensajes.py` → PASS.
- [ ] **Step 5: Commit** `App: Perfil con Mis deportes y piel v3 en todas las ventanas`

### Task 11: Verificación final y registro

**Files:**
- Modify: `harness/tareas.md` (marcar la tarea), `harness/progreso.md` (decisión clave), `apps/mobile/docs/REDISENO_NBA_TENIS_20261030.md` (estado «implementado»)

- [ ] **Step 1: Run** `./scripts/test_local_windows.ps1 -Suite all` → todo en verde (fútbol/API, NBA y frontend).
- [ ] **Step 2: Run** `C:\flutter\bin\flutter build apk --release` en `apps/mobile` → APK generado con `1.1.0+4`.
- [ ] **Step 3: Probar en el emulador real** (`emulator-5556`, build release) contra `https://pronosticosdeportivos.pro`: cambiar de deporte en las 3 pestañas; abrir un partido de cada deporte; ver logos NBA, fotos NBA y de tenis y escudos; apagar el wifi en NBA (aviso y reintento); ocultar un deporte en Perfil. Hacer capturas de cada caso.
- [ ] **Step 4: Commit** `App: NBA y tenis listos para revisión` y abrir el PR a `main`. La publicación en Play y la activación de la versión mínima las hace el titular desde `/control/configuracion-app`.

---

## Fuera de alcance (decisiones del titular antes o después de esta entrega)

1. **VIP y monedas para NBA y tenis.** Sus feeds son públicos en la web (`actionable:false`), así que un candado en la app no protegería nada. Esta entrega los muestra abiertos y sin candados. Para venderlos haría falta que el servidor sirva una versión con acceso aplicado, como hace `high_probability()` con fútbol.
2. **Cuotas en NBA y tenis.** Los feeds no las publican (`price: null`), así que no se muestran. Las «@1,90» del prototipo son ilustrativas.
3. **Notificaciones por deporte.** Requieren que el servidor envíe por deporte. En esta entrega no se añade el interruptor por deporte.
4. **Escalera y Parley en NBA y tenis.** No existen en los feeds; siguen siendo solo de fútbol.
5. **Chip «HOY»** (lo mejor de cada deporte en Inicio): pendiente de decidir; no entra en esta entrega.
6. **Archivar pantallas heredadas** (`sign_in/`, `log_in/`, `forget_password/`, `market_screens.dart`, `match_detail.dart`, `profile_settings.dart`): cambio aparte, con confirmación.
