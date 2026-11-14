# Rediseño CyberCore — plan de implementación (parte 2: fases, pasos, pruebas y aceptación)

Fecha: 14-nov-2026 · Lee antes **[PLAN_REDISENO_CYBERCORE_20261114.md](PLAN_REDISENO_CYBERCORE_20261114.md)** (reglas, decisiones, tokens, widgets, contratos de datos). Este documento dice **qué hacer, en qué orden y cómo comprobar que está bien**.

## A. Mapa de fases y dependencias

```
F0 Preparación ─► F1 Fundaciones ─► F2 Cáscara ─┬─► F3 Pantallas principales (3a…3e)
                                                  ├─► F4 Ficha de partido (4a…4g) ──(4f usa F7a)
                                                  ├─► F5 Conversión y primer arranque (5a…5d)
                                                  └─► F6 Imágenes (cliente) ──(fotos nuevas usan F7b)
F7 Servidor (7a bajas, 7b fotos de tenistas, 7c comprobaciones)  ← en paralelo, PR separado, deploy solo con permiso del titular
F8 Cierre: traducciones, QA, release
```

| Fase | Tamaño | Rama sugerida | Depende de |
|---|---|---|---|
| F0 | S | `app/rediseno-f0-preparacion` | — |
| F1 | L | `app/rediseno-f1-fundaciones` | F0 |
| F2 | M | `app/rediseno-f2-cascara` | F1 |
| F3a Inicio | M | `app/rediseno-f3a-inicio` | F2 |
| F3b Predicciones | L | `app/rediseno-f3b-predicciones` | F2 |
| F3c Mercados y detalle | L | `app/rediseno-f3c-mercados` | F2 |
| F3d Coins y Movimientos | M | `app/rediseno-f3d-coins` | F2 |
| F3e Perfil, Preferencias, Avisos, Menú, Guía | L | `app/rediseno-f3e-perfil-menu` | F2 |
| F4a Contenedor de ficha | L | `app/rediseno-f4a-ficha` | F2 |
| F4b Pronóstico + Props | M | `app/rediseno-f4b-pronostico-props` | F4a |
| F4c Análisis fútbol | L | `app/rediseno-f4c-analisis-futbol` | F4a |
| F4d Análisis NBA | L | `app/rediseno-f4d-analisis-nba` | F4a |
| F4e Análisis tenis | L | `app/rediseno-f4e-analisis-tenis` | F4a |
| F4f Alertas + alineaciones | M | `app/rediseno-f4f-alertas` | F4a (+ F7a para foto/posición) |
| F4g H2H | S | `app/rediseno-f4g-h2h` | F4a |
| F5a Desbloquear | M | `app/rediseno-f5a-desbloquear` | F2 |
| F5b VIP | L | `app/rediseno-f5b-vip` | F2 |
| F5c Idioma + Bienvenida + Acceso | L | `app/rediseno-f5c-primer-arranque` | F1 |
| F5d Actualización + Privacidad | S | `app/rediseno-f5d-dialogos` | F1 |
| F6 Imágenes (cliente) | M | `app/rediseno-f6-imagenes` | F1 |
| F7a Servidor: bajas | M | `servidor/bajas-con-foto-y-posicion` | — |
| F7b Servidor: fotos de tenistas | M | `servidor/fotos-tenistas-sofascore` | — |
| F8 Cierre y release | M | `app/rediseno-f8-cierre` | todas |

S ≈ medio día, M ≈ 1–2 días, L ≈ 2–4 días de trabajo.

### Reglas para **cada** PR (lista de comprobación)
1. Worktree nuevo desde `origin/main`; `./scripts/harness_check.sh` verde antes de empezar.
2. `grep`/`ls` antes de editar cualquier archivo citado aquí (las rutas son del 14-nov).
3. Textos nuevos: **primero** `grep -n "<texto>" apps/mobile/lib/l10n/app_es.arb` (reutiliza si existe) y, si no existe, añádelo con `tool/l10n_add.py` en los 6 idiomas (Apéndice A).
4. `flutter analyze --no-pub` sin avisos nuevos, `flutter test --no-pub` en verde (CI usa Flutter `3.47.7`, ver `.github/workflows/pruebas.yml`).
5. Prueba **release** en `emulator-5556` a 390×844 y 360×800, en `es` y `de`; compara con `render_cybercore_20261114/capturas/<lámina>.png`.
6. Estados de cada pantalla: cargando, vacío, error, sin imagen, bloqueado, con/sin VIP, sesión sin iniciar (los que apliquen).
7. Anota la decisión clave en `harness/progreso.md` y marca la tarea en `harness/tareas.md`.
8. PR a `main` con capturas «antes/después» y la lista de claves nuevas. No mezcles fases en un PR.

---

## F0 — Preparación (S)

**Objetivo:** partir de una línea base medida.
1. `git worktree add -b app/rediseno-f0-preparacion ../qf-app-rediseno origin/main`; entra en `apps/mobile`.
2. `flutter pub get`, `flutter analyze --no-pub`, `flutter test --no-pub`. **Anota cuántas pruebas pasan** (la línea base).
3. Compila el release y guarda capturas «antes» de: Inicio, Predicciones, Mercados, Coins, Perfil, ficha de fútbol (4 pestañas), ficha NBA, ficha tenis, VIP, Acceso (a 390×844) en la descripción del PR de la fase 1.
4. Comprueba `python tool/l10n_add.py` (ver cabecera del archivo) y `docs/TRADUCCIONES.md`.
5. Añade a `harness/tareas.md` la sección **«Rediseño CyberCore de la app (14-nov-2026)»** con una casilla por fase de este documento, y a `harness/progreso.md` una entrada que enlace los dos planes.
6. (Opcional) copia `render_cybercore_20261114/datos/*.json` a `apps/mobile/test/fixtures/` con nombres cortos (`ficha_futbol_real.json`, `nba_estadisticas_real.json`, `tenis_estadisticas_real.json`) cuando los uses en la fase 4.

**Aceptación:** línea base verde documentada; tareas creadas.

---

## F1 — Fundaciones: tokens, fuentes y piezas base (L)

**Objetivo:** que **todo lo que ya existe** se vea con los colores/tipos nuevos sin cambiar su diseño, y que existan las piezas reutilizables con sus pruebas.

**Archivos:**
- `apps/mobile/fonts/` → añadir `Exo2-Regular.ttf`, `Exo2-Medium.ttf`, `Exo2-SemiBold.ttf`, `Exo2-Bold.ttf`, `JetBrainsMono-Bold.ttf`, `OFL-Exo2.txt` (descarga de Google Fonts; son OFL).
- `apps/mobile/pubspec.yaml` → declarar `Exo 2` (400/500/600/700), `JetBrains Mono` (500/700), `Rajdhani` (500/700); mantener `Gilroy*`. `adaptive_icon_background: '#090f1a'` → `'#07080C'`.
- `lib/product/qf_theme.dart` → **reemplazar `QfColors`** por la tabla de §3.1 del plan principal; añadir `QfText` (estilos precalculados por rol de §3.2), `QfSpace`, `qfGreenGradient`; `qfTheme()` con `fontFamily: 'Exo 2'`; conservar `contrastRatio`. **Elimina** `football`, `nba`, `tennis` de `QfColors` y arregla los usos (`grep -rn "QfColors.football\|QfColors.nba\|QfColors.tennis" lib`): el acento de deporte pasa a ser cian; los colores por familia de mercado quedan locales en `market_hub.dart`.
- `lib/product/live_widgets.dart` → los alias `liveBg`, `livePanel`, `liveCyan`, `liveGold`, `liveGreen`, `liveMuted` **siguen existiendo** apuntando a los tokens nuevos: `liveCyan → cyan`, `liveGold → yellow` (**ojo:** hoy `liveGold` es el ámbar de «acción»; busca dónde se usa como botón principal y pásalo a verde en la fase de esa pantalla), `liveGreen → green`, `livePanel → surface`. Reestiliza `liveCard`, `liveButton`, `liveHeading` para que las pantallas aún sin migrar no queden desencajadas.
- `lib/product/qf_shapes.dart` → `QfCard` con `strong`/`glow`/`cut`; `QfBadge` con `kind` (`free, won, vip, lost, live, review, voided, doubt`); `SegmentedBar`/`ProbabilityBar`/`SealLine` al nuevo color. **No borres** `SealLine` (otros usos) aunque el render ya no muestre la línea terminal del sello: déjala sin usar en las pantallas del render y decide su retiro en F8.
- **Archivos nuevos** (cada uno con su prueba, ver §4 del plan principal): `lib/product/qf_controls.dart` (`QfButton`, `QfSwitch`, `QfCheckbox`, `QfTabs`, `QfSectionNav`, `QfStepDots`), `lib/product/qf_charts.dart` (`QfRing`, `QfRadar`, `QfDivergingRow`, `QfDominanceDots`, `QfFormPills`, `QfMarginBars`, `QfStackedBar`, `QfSeasonTrack`, `QfPips`, `QfSegmentedChart`), `lib/product/qf_sheets.dart` (`QfBottomSheet`, `QfDialogCard`), `lib/product/qf_standings.dart` (`QfStandingsTable`).
- `lib/product/sport_images.dart` → `QfAvatar` con `kind` (persona = círculo + aro cian 2 dp + iniciales; logo = cuadrado `contain`).

**Pasos recomendados:** (1) tokens + fuentes y que compile; (2) arreglar usos eliminados; (3) widgets uno a uno con prueba; (4) `test/qf_gallery_test.dart` que dibuja todos los widgets a 360 dp.

**Pruebas:** actualizar `qf_theme_test.dart` (contraste de los 3 fondos con la paleta nueva; `onGreen`/`onYellow` ≥ 4,5; alias `live*`); `qf_shapes_test.dart`; nuevas `qf_controls_test.dart`, `qf_charts_test.dart`, `qf_sheets_test.dart`: cada widget (a) se dibuja sin desbordar a 360 dp, (b) objetivos táctiles ≥ 44 dp, (c) `Semantics` correcta, (d) **estado vacío/valores extremos** (0 %, 100 %, listas vacías, textos largos en `de`).

**Aceptación:** `flutter test` verde; ninguna pantalla existente rota (compílala y ábrela); la app ya se ve con la paleta nueva aunque los diseños sean los de antes; los widgets de la galería coinciden con `capturas/Sistema.png`.

---

## F2 — Cáscara de navegación (M)

**Objetivo:** cabecera, barra inferior, selector de deporte y selector de tipo con el diseño nuevo.
**Archivos:** `product/live_shell.dart` (`AppBar`, `BottomNavigationBar`), `product/sport_selector.dart`, `product/predictions_switcher.dart`, `product/live_widgets.dart`.
**Pasos:**
1. **Cabecera** (§5.1): `leading` = `☰` 44 dp (conserva `showMoreSheet(context, onMySports: openMySports)`), `title` = marca `QUANT` + `FUT` (cian), `actions` = chip de monedas (`_CoinsChip`, restilar amarillo, 44 dp de alto, **oculto en Coins**) + corona VIP 44 dp (abre VIP). Alto 56, borde inferior cian 20 %.
2. **Barra inferior**: sustituir `BottomNavigationBar` por una `QfBottomNav` propia (64 dp) con 5 destinos; **mantén los mismos índices (0–4) y el `onTap` actual** (analítica `services?.screen(...)`, recarga de saldo al salir de Coins). Etiqueta del 2.º destino: **`navPicks`** (nueva).
3. **Selector de deporte** (`SportSelector`): nuevo aspecto (chips de 44 dp, activo cian, icono + texto + contador). Conserva API (`sports`, `value`, `onChanged`, `counts`), las claves `ValueKey('sport-${sport.id}')`, el comportamiento de >4 deportes (fila desplazable + «Más») y que **no** cambia de pestaña.
4. **Selector de tipo** (`PredictionsSwitcher`): pasa a `QfTabs` segmentado (texto, sin icono como en la lámina) conservando `order`, `swipe()` y las claves de las pestañas.
**Textos nuevos:** `navPicks` («Picks»).
**Pruebas:** actualizar `product_navigation_test.dart` (etiqueta y que el selector sigue solo en 0, 1, 2; a 360 dp no se recorta en los 6 idiomas) y `home_screen_test.dart`.
**Aceptación:** cabecera, barra y selector idénticos a `capturas/Main.png`; navegar entre las 5 pestañas conserva estado como hoy; el ☰ abre el menú.

---

## F3 — Pantallas principales

### F3a — Inicio (M)
**Archivos:** `product/live_home.dart` (`HomeTab`, `_CoinsCard`, `_HitCard`, `_TicketCard`), `home_hero.dart` (`HomeHero`, `CourtPainter`), `home_sport.dart`, `home_agenda.dart` (`DayStrip`, `MatchRow`, `AgendaDay`).
**Pasos (de arriba abajo, igual que la lámina):**
1. Avisos (banner/mantenimiento) → tarjeta de información cian (no amarilla; el amarillo es VIP/monedas).
2. **Destacado del día** → `QfCard(strong: true, glow: true)`: etiqueta verde «DESTACADO DEL DÍA» + «liga · día hora», dos escudos 58 dp, probabilidad 42 px mono con brillo, texto del mercado, barra de 2–3 partes y leyenda, **botón verde** «Ver pronóstico gratis» → ficha. Para NBA/tenis la misma tarjeta con logos/fotos redondas (`QfAvatar`).
3. Dos tarjetas: acierto 30 días **del deporte elegido** (`{won} de {total} picks sellados`) y monedas (`Te alcanza para N desbloqueos`).
4. `DayStrip` de 5 días: contador por día **del deporte elegido**; HOY resaltado.
5. **Agenda:** `MatchRow` = hora mono · dos imágenes solapadas 30 dp · «Local – Visitante» + liga · a la derecha `%` verde / candado VIP / «desde HH:MM». NBA agrupa por hora; tenis por torneo → ronda.
**Datos:** los que ya usa (`/mobile/v1/home`, `sports_feed`). No cambies contratos.
**Pruebas:** `home_screen_test.dart`, `home_sport_test.dart`, `featured_pick_test.dart`, `published_history_test.dart` (ajustar finders si cambian textos; añade prueba de fila con imagen y sin imagen).
**Aceptación:** `capturas/Main.png`; mismo patrón al cambiar a NBA y tenis; sin overflow a 360 dp.

### F3b — Predicciones (L)
**Archivos:** `product/live_picks.dart` (`HighProbabilityView`, `PickTile`, `LockedPicksGroup`), `live_ladder.dart` (`LadderChallengeCard`, `_RingPainter`), `live_parley.dart` (`ParleyTab`, `_TicketCard`), `sport_predictions.dart`, `live_widgets.dart` (`RealPickCard`, `LockedBlur`).
**Pasos:**
1. **Alta prob.:** `PickTile`/`_PickCard` con meta (liga · hora), insignia GRATIS/VIP, imágenes solapadas 36 dp, nombre, selección Rajdhani 17 cian, probabilidad mono 26 y cuota con casa. Bloqueado → `QfLockedBlur`. Tarjeta de confianza (`_TrustCard`) sin la línea del sello.
2. **Escalera:** barra de 5 segmentos con el escalón activo cian con brillo, «cuota acumulada», «prob. de este escalón», lista de escalones ganados con ✓, texto «si un escalón falla, vuelve a empezar». Historial (`LadderHistoryCard`) con la misma piel.
3. **Parley:** 3 selecciones con deporte, imágenes y probabilidad; «probabilidad conjunta» y «cuota combinada»; aviso de no-certeza. Soporte de parley v2 (tenis/NBA/props) como hoy.
4. **Barra fija inferior** `DESBLOQUEAR · {coste}` (verde) + `VIP` (amarillo) que abre la hoja de **F5a** (hasta entonces, el diálogo actual). El ámbar «única acción» pasa a **verde**.
**Decisiones abiertas aplicables:** #4 del plan principal (Escalera/Parley en NBA/tenis).
**Pruebas:** `predictions_ui_test.dart`, `live_ladder_test.dart`, `ladder_progress_test.dart`, `live_parley_test.dart`, `pick_labels_test.dart`.
**Aceptación:** `capturas/Predicciones.png` (los 3 estados del segmento); deslizar cambia de tipo, no de deporte (`product_navigation_test`).

### F3c — Mercados y detalle (L)
**Archivos:** `product/live_markets.dart` (`MarketsDashboard`), `market_hub.dart` (`MarketsHero`, `MarketTile`, `MarketTilesGrid`, `MarketRateCard`, `MarketScaffold`, `_look`, `RadarClock`, `_RadarPainter`), `sport_markets.dart`, `live_market_detail.dart`.
**Pasos:**
1. **Hero** (captura del titular): insignia «MODELO ACTIVO» con punto verde, «N familias de mercado en el radar» (N 54 px), «Historial web desde …», píldora `{won}/{total} publicados acertados · {pct} %`, radar decorativo (reutiliza `RadarClock`/`_RadarPainter`).
2. **Rejilla** 2 columnas de `MarketTile`: anillo con % (`QfRing` con el color de la familia), icono, nombre, «Abiertos N · Resueltos M», «Publicado a/b», **fila de 10 puntos** (círculo lleno = acierto, hueco = pendiente) y fila «HOY» con 4 imágenes solapadas (equipos/jugadores del día de esa familia). Sin publicaciones → anillo gris con «–» y «Sin publicaciones aún».
3. **Pestañas internas por deporte** con `QfTabs`: fútbol PARTIDO | GOLES, NBA PARTIDO | JUGADORES, tenis PARTIDO | JUEGOS (según el catálogo).
4. **Detalle** (`MarketScaffold`): cabecera con insignia de línea, tarjeta de acierto global + «hoy», `QfTabs` «HOY (n) · ANTERIORES», filas con dos imágenes + resultado + insignia, barra fija de desbloqueo.
**Datos:** `assets/model/market_evidence.json`, `MarketFamily`, `MarketLine`; no cambies el catálogo.
**Pruebas:** `live_markets_test.dart`, `market_catalog_test.dart`, `market_family_catalog_test.dart`, `match_markets_sin_modelo_test.dart`.
**Aceptación:** `capturas/Mercados.png` y `Mercado.png`; familia sin datos y estado de error/cargando existentes siguen funcionando.

### F3d — Coins y Movimientos (M)
**Archivos:** `product/live_rewards.dart` (`RewardsScreen`, `_Hero`, `_AttendanceCard`, `_OffersCard`, `_InviteCard`, `_Ledger`, `_Terms`), `rewards_progress.dart`, `coin_burst.dart`.
**Pasos:** hero de saldo (48 px amarillo, brillo amarillo, insignia de racha, `QfPips` de desbloqueos disponibles) · «GANA MONEDAS HOY» (asistencia con 7 casillas + **botón verde** «Marcar asistencia · +N»; video; ofertas; invitar con código mono + «Copiar») · «Mis movimientos» como fila que abre la lista (nueva pantalla `Movimientos`: tarjeta de saldo/ganadas/gastadas, grupos por día, icono por tipo, +verde/−gris, «Ver más/menos» 5→todos, vacío).
**Datos:** `/mobile/v1/rewards` (+ el ledger que ya muestra `_Ledger`; **calcula «ganadas/gastadas» sumando el ledger visible o pídelo al servidor, no inventes**).
**Pruebas:** `coins_ui_test.dart`, `rewards_ads_card_test.dart`, `ladder_progress_test.dart` si toca.
**Aceptación:** `capturas/Coins.png`, `capturas/Movimientos.png` (+ vacío).

### F3e — Perfil, Preferencias, Avisos, Menú y Guía (L)
**Archivos:** `product/live_profile.dart`, `my_sports.dart`, `core/firebase_preferences.dart` (`FirebasePreferencesScreen`, `FirebaseInbox`, `_InboxRow`), `product/live_more.dart` (`showMoreSheet`), `live_guide.dart`.
**Pasos:**
1. **Perfil:** tarjeta de cuenta (iniciales, correo enmascarado, insignias, botón «Ver planes VIP» amarillo), «Mis deportes» (`QfSwitch` + asa de reordenar + «Por defecto»; mínimo uno visible), filas de preferencias que abren `Preferencias`, versión, cerrar sesión magenta.
2. **Preferencias:** secciones `// NOTIFICACIONES` (general + por deporte + «Bandeja de avisos» con contador), `// IDIOMA`, `// MEDICIÓN Y DIAGNÓSTICO` (3 `QfSwitch`, «Ver más» en Meta), `// TUS DERECHOS` (derechos, **eliminar cuenta** en magenta claro) + nota final. **Las notificaciones por deporte requieren que el servidor/Firebase las soporte** (`/app/v1/firebase/preferences`): revisa el contrato; si hoy solo hay un interruptor global, deja los de deporte detrás de una bandera y anótalo como pendiente de servidor en `harness/tareas.md`.
3. **Avisos:** chips de deporte con contador, filas con imagen + etiqueta + tipo + partido + detalle + hora + punto cian si no leído (abre el partido), vacío. **No inventes tipos de aviso**: pinta los que llegan.
4. **Menú ☰:** hoja con fila «Acceso VIP», `// APRENDE`, `// APP`, `// LEGAL`, versión. Conserva las acciones (`launchUrl` de términos/privacidad, `share_plus`, tienda).
5. **Guía:** `QfTabs` modo chips con 6 temas, un gráfico ilustrativo por tema (§5.7), «Anterior/Siguiente». Textos largos = los `guideBody1..6` actuales.
**Pruebas:** `profile_sports_test.dart`, `inbox_sport_test.dart`, `consent_defaults_test.dart`, `app_smoke_test.dart`; nuevas para Guía y Menú.
**Aceptación:** `capturas/Perfil.png`, `Preferencias(Completa).png`, `Avisos.png`, `Menu.png`, `Guia(Completa).png`.

---

## F4 — Ficha de partido (los 3 deportes)

### F4a — Contenedor común (L)
**Objetivo:** una sola ficha con la **misma cabecera, hero, pestañas y barra inferior** en fútbol, NBA y tenis.
**Archivos:** `product/live_detail.dart` (`LiveMatchDetail`, fútbol), `sport_detail.dart` (`SportDetail`, NBA/tenis; `_TabButton`, `_Header`, `_SealCard`, `_MarketRow`), `live_statistics.dart` (`MatchFixtureHeader`), `match_visuals.dart` (`MatchTeams`, `LockedVipMatchCard`).
**Pasos:**
1. Extrae un `MatchShell` (cabecera «liga + fecha/hora + cerrar», hero, `QfTabs`, contenido, barra fija «DESBLOQUEAR TODO · {coste}» + «VIP») que reciban `header`, `tabs` y `body`. Reemplaza las dos implementaciones de pestañas (`live_detail.dart` ~línea 230 y `_TabButton` de `sport_detail.dart`).
2. **Hero:** imágenes (escudos/logos 58 dp o fotos redondas 58–76 dp), probabilidad grande, etiqueta («GANA MALLORCA»), subtítulo (forma `E G G P E`, «VISITANTE · 8-3», «29 AÑOS · N.º 12»), barra de 2–3 partes y leyenda. NBA: visitante a la izquierda (`VIS @ LOC`).
3. Pestañas por deporte: fútbol `Pronóstico · Análisis · H2H · Alertas`; NBA `Pronóstico · Props · Análisis · H2H · Alertas`; tenis `Pronóstico · Análisis · H2H · Alertas`. Con 5 pestañas, fuente 11 dp.
**Cuidado:** **mantén** los estados existentes (`detailNoPicks`, `detailNoSealedModel`, `nbaSeal*`, error, cargando) y la regla de qué ve un usuario gratis/VIP (`detail_no_sealed_test.dart`, `match_facts_test.dart`).
**Pruebas:** `detail_no_sealed_test.dart`, `generic_sport_ui_test.dart`, `live_score_strip_test.dart`, `match_facts_test.dart`.
**Aceptación:** cabecera/hero/pestañas/barra = `capturas/Partido.png`, `PartidoNBA.png`, `PartidoTenis.png`.

### F4b — Pestaña Pronóstico + Props NBA (M)
**Archivos:** `live_forecast.dart` (`ForecastPanel`), `live_match_markets.dart` (`MatchMarkets`, `_OpenRow`, `_LockedRow`), `sport_detail.dart` (`_Predictions`, `_MarketRow`), nuevo `product/sport_props.dart`.
**Pasos:**
1. **Pronóstico:** tarjeta «PICK DESTACADO · GRATIS» + «MERCADOS DEL MODELO» (filas con 1–2 imágenes, mercado, selección, a la derecha prob. + `@cuota` + «casa · hora»). Bloqueado = difuminado + «VIP» + «con monedas o VIP».
2. **Props (NBA):** filtro `QfTabs` modo chips `TODOS · PUNTOS · REBOTES · ASIST. · TRIPLES` + tarjetas: foto redonda 52 dp con logo del equipo (20 dp) en la esquina, nombre, selección («Puntos · Más de 25,5»), barra de 5 casillas «N de los últimos 5», prob./cuota/casa. **Fuente:** mercados `player_points|player_rebounds|player_assists|player_threes` ya parseados en `sports_feed.dart` (`SportMarket.player/playerId`), cuota/casa de `sports_quotes.dart`; foto con `nbaPlayerPhoto(playerId)` (`sport_images.dart`). **«Últimos 5»**: usa el dato que ya traiga el mercado; **si no existe, omite la barra** (no la inventes) y anótalo en `harness/tareas.md`.
**Pruebas:** `generic_sport_ui_test.dart`, `quote_label_test.dart`, nueva `sport_props_test.dart` (con y sin cuota, sin foto, jugador bloqueado, filtro).
**Aceptación:** `capturas/Partido.png`, `PartidoProps.png`.

### F4c — Análisis de fútbol (L)
**Archivos:** nuevo `product/analysis_football.dart`; adaptar `live_statistics.dart` (`MatchStatistics`, `HistoricalComparison`, `MatchProbabilitySummary`) y `live_match_facts.dart` (`MatchFacts`, `_TeamFacts`, `_ResultRow`).
**Pasos:** (cada sección = una `QfCard(strong: true)` con `// ETIQUETA` + h2; `QfSectionNav` fija arriba con RESUMEN · FORMA · CARA A CARA · TABLA)
1. **Resumen «Cómo llegan»:** interruptor TODOS | CASA·FUERA (estado local; casa/fuera usa `promedios.casa` del local y `promedios.fuera` del visitante); cabecera con escudos y rayita de color; `QfDominanceDots` (10); `QfRadar` (§5.9 para las fórmulas); 10 `QfDivergingRow` (orden de la lámina; formatos: goles 1 decimal con coma en `es`, xG 2 decimales, porcentajes con la regla de espacio del idioma (`percentText`)).
2. **Forma:** por equipo, 5 `QfFormPills` **de más antiguo (izq.) a más reciente (der.)** (invierte la lista de la API), escudo del rival (`rival_escudo`), marcador `gf–gc`, CASA/FUERA, etiqueta ÚLTIMO; chips de racha («5 sin perder» = racha de no-derrotas desde el más reciente) y «`gf` GF · `gc` GC»; «PTS DE 15» = `resumen.puntos`.
3. **Cara a cara:** `QfStackedBar` (`victorias_local` / `empates` / `victorias_visitante`), chips (`goles_media`, `pct_ambos_marcan`, `pct_mas_2_5`), los 3 últimos con escudos (cuidado con quién fue local: campo `local`) y resultado visto desde el local (G/E/P), botón «Ver los N partidos» → pestaña H2H.
4. **Tabla:** `QfStandingsTable` con las filas alrededor de ambos equipos (separador «···» si no son contiguas), zonas por competición (**no hardcodees LaLiga 2**: lee `descripcion` de la tabla si trae «Promoción/Descenso…»; si no hay datos de zona, no pintes zona), forma en 5 barritas (**invertir**: la API la da más reciente primero), callout «X está N puntos por encima de Y».
**Datos:** ficha `GET /web/partidos/{id}` (§7.1). Usa `render_cybercore_20261114/datos/ficha_futbol_*.json` como fixture.
**Estados:** sin `promedios.casa/fuera` → ocultar el interruptor; sin forma → ocultar sección; sin tabla → ocultar; datos parciales (xG `null`) → mostrar «—» en esa fila.
**Pruebas:** nueva `analysis_football_test.dart` con el fixture real + variantes (sin tabla, sin xG, sin cara a cara, interruptor casa/fuera, 360 dp en `de`); mantener `match_facts_test.dart`, `match_statistics_real` fixture.
**Aceptación:** `capturas/PartidoAnalisis.png` y `PartidoAnalisisCompleto.png`; el botón «Ver los 6 partidos» salta a H2H.

### F4d — Análisis de NBA (L)
**Archivos:** nuevo `product/analysis_nba.dart`; retirar el listado plano de `SportAnalysis.nbaTeam` en `sport_detail_tabs.dart`.
**Secciones** (`QfSectionNav` desplazable con 6 chips): **Probabilidad** (2 tarjetas grandes + barra + 4 «factores del partido» **calculados** desde las estadísticas: récord, rendimiento de visitante/local, descanso (`rest_days`/`back_to_back`), racha), **Comparativa** (7 `QfDivergingRow`: récord %, visitante·local %, puntos a favor, puntos en contra (menos = mejor), diferencial, últimos 6 %, descanso), **Forma** (`QfFormPills` de 6 con `QfMarginBars` = margen `puntos − rival`), **Cara a cara** (`home_wins`/`away_wins`, `average_total`, 4 últimos), **Clasificación** (`QfSeasonTrack` 15 casillas: 1–6 cian, 7–10 `slate`, 11–15 pista; marcadores con logo en `rank`), **Disponibilidad** (por equipo: estado del reporte, `N jugadores en el reporte`, minutos de bajas con indicador de color, back-to-back; **los datos salen de `event.availability`** ya parseado en `SportAlerts`: léelo de ahí, no lo recalcules).
**Probabilidad de ganar:** viene del mercado `winner` del partido sellado; **si no hay mercado sellado, muestra la sección sin porcentaje** («Pronóstico pendiente», `sportAvailPending`/`nbaSealPending*`) y deja el resto.
**Datos:** `GET /nba/v1/partido/{id}/estadisticas` (§7.2); fixture `datos/nba_estadisticas_*.json`.
**Pruebas:** nueva `analysis_nba_test.dart` (fixture real; sin `form`; sin `standing`; sin disponibilidad; back-to-back); mantener `generic_sport_ui_test.dart`.
**Aceptación:** `capturas/PartidoNBA.png`, `PartidoNBAAnalisisCompleto.png`.

### F4e — Análisis de tenis (L)
**Archivos:** nuevo `product/analysis_tennis.dart`; retirar `SportAnalysis.tennisPlayer`.
**Secciones** (`QfSectionNav`: PROBABILIDAD · FORMA · SUPERFICIE · CARA A CARA · MODELO): **Probabilidad** (fotos 76 dp, `winner` del evento, ranking/puntos/`movement` ▲▼, edad, país, brecha de ranking), **Forma** (`form.index` 0–100 con barra; 5 últimos con rival, **ronda traducida** (mapa en `pick_labels.dart`: Round of 64 → «Ronda de 64»…), marcador, racha `form.streak`, `over_2_5_sets` % «a 3 sets», `tiebreaks` % «con tie-break»), **Superficie** (`event.surface`: Hard/Clay/Grass → «PISTA DURA/TIERRA/HIERBA»; filas dura-carrera, dura-temporada, tierra, hierba con `QfDivergingRow` sobre `rate`, números `won–lost`; la de hoy con «HOY»), **Cara a cara** (si `matches` vacío: «0 – 0 · PRIMER DUELO» + texto; si no, resumen + lista), **Modelo** (a partir de `markets` del evento: duración en sets desde `sets_total` («más de 2,5 sets» = % a 3 sets), «gana cada set» desde `set_winner-*`, barras de «más de» juegos totales desde `games_total-*` (**solo las líneas que existan**), hándicap `games_handicap-*` (−1,5/−3,5/−5,5 si existen), `tiebreak-*`, «juegos esperados ≈ N» = línea donde cruza 50 %).
**Trampas:** nombres invertidos en `players[]` (usa los del evento); `estadisticas/{id}` da 404 en partidos terminados → estado vacío existente.
**Pruebas:** nueva `analysis_tennis_test.dart` (fixtures `tenis_estadisticas_*` y `tenis_evento_*`; sin h2h; sin superficie; sin mercados de juegos; ronda desconocida → texto crudo); mantener `generic_sport_ui_test.dart`.
**Aceptación:** `capturas/PartidoTenisAnalisis.png`, `PartidoTenisAnalisisCompleto.png`, `PartidoTenis.png`.

### F4f — Alertas y alineaciones (M)
**Archivos:** `product/live_alerts.dart` (`AlertsTab`, `_AbsenceCard`, `_Section`, `_TeamSwitcher`), `live_match_facts.dart`, nuevo `product/lineup_pitch.dart` (`QfPitch`), `core`: traducción de motivos en `l10n/pick_labels.dart`.
**Pasos:**
1. **Fila de baja** (68 dp): `QfAvatar(persona)` 44 dp con escudo 20 dp en la esquina; nombre; «POS · Equipo» (omitir POS si no hay); **motivo traducido**; insignia: `injury`→LESIÓN, `internationalDuty`→SELECCIÓN, `suspension`→SANCIÓN, «Doubtful»→DUDA, «Back in training»→VUELVE. **Regreso:** si el servidor ya manda `regreso_fecha` (F7a) usa esa fecha formateada («vuelve a principios de dic.»); si no, **interpreta el texto en inglés** («Early/Mid/Late <Month> <Year>») con una función pura probada en `pick_labels.dart`; texto desconocido → muestra tal cual.
2. **Alineaciones** al final (tras la lista de bajas): por equipo con once → `QfPitch` (formación `4-3-1-2` → líneas de 4-3-1-2 + portero; 11 fotos redondas 42 dp con dorsal y apellido; orden vertical GK abajo); sin once → tarjeta discontinua «{Equipo} · sin alineación guardada — …». Datos: `local.ultimo_once` / `alineaciones.home|away`.
3. NBA: una fila por equipo con el estado del reporte (sin nombres). Tenis: una fila por jugador «SIN ALERTAS» si no hay datos.
**Foto del jugador en bajas:** solo cuando F7a la entregue y el titular lo apruebe (decisión abierta #7); hasta entonces **iniciales**.
**Pruebas:** `alerts_tab_test.dart`, `alerts_model_test.dart`, nueva `lineup_pitch_test.dart` (formaciones 4-3-3, 4-4-2, 3-5-2, 4-2-3-1, 4-3-1-2; menos de 11 jugadores), traducción de motivos (todas las combinaciones + desconocido).
**Aceptación:** `capturas/PartidoAlertas.png`, `PartidoAlertasCompleto.png`.

### F4g — H2H (S)
`SportH2h` y la pestaña H2H de fútbol con la piel nueva: resumen con imagen y número grande, `QfStackedBar`, lista de partidos con dos imágenes y marcador, **estado «primer duelo»** (tenis 0–0). **Aceptación:** `capturas/PartidoTenis.png`.

---

## F5 — Conversión y primer arranque

### F5a — Desbloquear (M)
**Archivos:** `product/live_shell.dart` (el diálogo con `ValueKey('unlock-confirm')`, `shellUnlockBody` y `needCoins()`), `live_widgets.dart`.
**Pasos:** sustituir los dos diálogos por **`QfBottomSheet`** con las dos variantes de la lámina (con saldo / sin saldo). Mantener la lógica: `POST /mobile/v1/rewards/unlock` con `stream` y `pick_key`; `monedas_insuficientes` → variante «Te faltan N monedas» (calcula `faltan = coste − saldo`); éxito → `reload()` y abrir el partido. Tres atajos de ganar monedas llevan a Coins (asistencia/video/ofertas). Salida VIP con el **precio mensual real** (del plan más corto) en «desde $X al mes»; si no hay precio, omite la parte del precio.
**Compatibilidad de pruebas:** conserva `ValueKey('unlock-confirm')` en el botón verde (o actualiza `product_navigation_test.dart` y quien lo use).
**Aceptación:** `capturas/Desbloquear.png`, `DesbloquearSinMonedas.png`.

### F5b — VIP (L)
**Archivos:** `product/live_vip.dart` (`LiveVipScreen`: `_plan`, `_monthly`, `_period`, `_price`, `_monthlyText`), `vip_performance.dart` (`VipPerformancePanel`, `VipFeatureComparison`), `store_purchases.dart`.
**Pasos:** reordena como §5.12: tarjetas de deporte → titular → **prueba** (anillo de ayer + barras de 7 días desde `VipPerformancePanel`) → **planes como filas radio** (anual preseleccionado = el de mayor duración/mejor precio; **etiqueta de ahorro** calculada contra el plan más corto; «equivale a $X al mes» y «al día» desde `duration_days`) → «Qué desbloqueas» (4 líneas) + comparación Gratis vs VIP plegable (`VipFeatureComparison`) → sellos → preguntas frecuentes (5) → nota. **Pie fijo** con CTA «EMPEZAR VIP {PLAN} · {PRECIO}» y la frase de renovación del plan elegido. «Restaurar compras» y política abajo.
**Reglas:** precios **solo** de la tienda (`widget.store?.byPlan`) o del plan; nunca del texto. Si no hay planes → `vipPlansSoon`. Cuenta no iniciada → flujo actual (`vipCheckSignIn`). Mantén `vip-plan-best` / `vip-plan-$index`.
**Analítica:** no cambies los eventos de compra (`meta_events.dart`); si añades interacción (elegir plan, abrir comparación) usa `services?.…` solo si ya hay un método análogo y **pide permiso** antes de añadir eventos nuevos.
**Pruebas:** pruebas existentes de VIP/compras; nueva para 1, 2 y 3 planes, plan único, sin planes, cuenta VIP activa, tienda no disponible.
**Aceptación:** `capturas/Vip.png`, `VipCompleto.png`.

### F5c — Idioma, Bienvenida y Acceso (L)
**Archivos:** `l10n/language_selection_screen.dart`, `onbonding_screen/second_screen.dart` (+ `splesh_screen.dart`), `product/welcome_art.dart`, `core/access_screen.dart`, `core/access_illustrations.dart`.
**Pasos:**
1. **Idioma:** órbitas (`_OrbitIcon`/`_OrbitPainter` existen) + insignia + 6 filas (código, nombre nativo, liga, «DETECTADO» en el idioma del dispositivo). Conserva `first-language-$code` y `selectLanguage`.
2. **Bienvenida:** 5 páginas con las ilustraciones de §5.13 (reescribe `welcome_art.dart`: tres tarjetas con imagen; radar; fichas con anillo; anillo + historial con ✓/✗; escudo con «NO ES UNA CERTEZA»), `QfStepDots`, «Saltar», «Siguiente/Empezar» verde.
3. **Acceso:** carrusel de 5 mensajes (puntos pulsables 30×44), tarjeta inferior con título, frase, etiquetas «Gratis para empezar»/«Sin tarjeta» (**nuevas**), botón Google blanco (logo oficial; ya existe `GoogleLogo`), casilla 18+ con enlaces, error en línea (no deshabilitar el botón), aviso. **Conserva** el flujo de vincular cuenta anterior y los estados `busy`/`docsReady`.
**Pruebas:** `language_selection_test.dart`, `access_screen_test.dart`, `consent_defaults_test.dart`.
**Aceptación:** `capturas/Idioma.png`, `Bienvenida.png`, `BienvenidaTodas.png`, `Acceso.png`.

### F5d — Actualización y Privacidad (S)
**Archivos:** `core/app_update.dart` (`AppUpdateDialog`), diálogo `privacyUpdateTitle` en `live_shell.dart` (~línea 260).
**Pasos:** `QfDialogCard`; **opcional** (título, versión, novedades, «Actualizar ahora», «Más tarde») y **obligatorio** (sin salida; el botón de atrás no cierra). Las novedades salen del servidor/Remote Config si existen; **si no hay lista, muestra solo el texto base** (`updateOptional`/`updateRequired`). Privacidad: dos puntos + texto actual + «Entendido» (verde) y «Leer la política · ajustar preferencias».
**Pruebas:** `app_update_test.dart`.
**Aceptación:** `capturas/Actualizacion.png`, `ActualizacionObligatoria.png`, `PrivacidadActualizada.png`.

---

## F6 — Imágenes (cliente) (M)

**Objetivo:** reglas únicas de imagen en toda la app.
**Archivos:** `product/sport_images.dart` (`ImageCatalog`, `TennisPhoto`, `nbaPlayerPhoto`, `QfAvatar`, `_Fallback`, `_initials`), `live_widgets.dart` (`TeamCrest`), `home_sport.dart` (`sportAvatar`, `eventAvatar`).
**Reglas (obligatorias):**
1. **Personas** (tenistas, jugadores NBA, futbolistas): círculo, aro cian 2 dp, `BoxFit.cover` con foco en el rostro (alineación superior), fondo `surface2`; sin imagen → **iniciales** (Rajdhani 700, color cian).
2. **Escudos y logos:** cuadrado, `BoxFit.contain`, padding 2–3 dp, sin aro ni recorte.
3. **Nunca** mostrar la foto de otra persona: si el id/origen no coincide, iniciales.
4. Crédito de fotos: la ficha de tenis muestra hoy un crédito CC BY-SA (`sportPhotoCredit`, `imageCredits`): **mantenlo mientras las fotos sean de Wikimedia** y retíralo **solo cuando** F7b esté desplegada y el titular lo confirme.
5. Pide cada imagen **una sola vez** (caché del catálogo ya existente) y con tamaño ≈ 3× el mostrado para no pedir imágenes enormes.
**Tenistas (cliente):** `ImageCatalog` resuelve la foto por **nombre normalizado** del evento (`home`/`away`). Extiende para leer el nuevo bloque del manifiesto (F7b) y **preferirlo** si existe; si no, el actual. Casos: nombre invertido, acentos, duplicados (`Coleman Wong`), sin foto (p. ej. «Ruien Zhang») → iniciales.
**Pruebas:** nueva `sport_images_test.dart` (persona vs logo; fallback; nombre invertido; duplicado; sin conexión); revisa las pruebas que usen `TeamCrest`/`sportAvatar`.
**Aceptación:** todas las capturas con imagen se parecen (tamaños y forma).

---

## F7 — Servidor (PRs al backend, aparte de la app)

> **No despliegues nada sin confirmación expresa del titular y sin seguir `DEPLOYS.md`.** Cada PR lleva sus pruebas Python (`tests/`).

### F7a — Bajas con id, fuente, posición, foto y fecha de regreso (M)
**Estado actual (verificado el 14-nov):** `_bajas()` en `src/qf/api/fichas.py` solo devuelve `jugador`, `tipo`, `motivo`. La tabla `injuries` **ya guarda** `player_id`, `source` (`api_football` | `fotmob` | `sofascore`, migración `db/087`) y `expected_return DATE`. Las fotos las sirve `src/qf/api/imagenes.py` (`photo_url`, `lineup_photo`) **solo** para `api_football` (→ `futbol`) y `sofascore` (→ `sofascore`); `fotmob` no tiene fuente de imagen.
**Pasos:**
1. En `_bajas()`: seleccionar también `player_id`, `source`, `expected_return`; devolver por baja: `jugador`, `tipo`, `motivo`, `regreso_fecha` (ISO o `null`), `jugador_id`, `foto` = `lineup_photo({"src": source, "player_id": player_id})` (o `null`), `posicion`.
2. **Posición** (`G|D|M|F`): del último once conocido de ese `player_id` en la misma fuente (`lineups` → `starters[].pos`; ver `src/qf/ingest/lineups.py` ~línea 95–110, que ya arma `positions`). `null` si nunca fue titular.
3. Mantén los campos antiguos (**compatibilidad con la app publicada**); solo se añaden campos.
4. Pruebas en `tests/test_fichas.py` (con y sin `source`, sin foto para `fotmob`, sin posición).
**Aceptación:** `GET /web/partidos/{id}` devuelve los campos nuevos; la app actual sigue funcionando sin cambios.

### F7b — Fotos de tenistas de SofaScore (M)
**Estado actual:** 179 JPG de Wikimedia en `frontend/imagenes/tenis/{slug}.jpg` + `frontend/imagenes/manifiesto.json` (bloque `tenis`: clave = nombre normalizado → `{f, n, a, l, lu, p, q}`); la app lo lee de `/web/imagenes/manifiesto.json`. Origen nuevo: `C:\Users\huye\Documents\SOFASCORE\data\images\tenistas` (1.182 `.webp` 150×150 RGBA + `tenistas_metadata.csv/json` con `id, nombre, archivo, genero, posicion, ranking_tipo, puntos, pais, pais_codigo, slug`). **Decisión del titular (13-nov): reemplazar por completo.** Medición previa: 178 de las 179 actuales emparejan por nombre; no empareja «Ruien Zhang»; hay un nombre duplicado en el CSV («Coleman Wong», ids 289106 y 406729).
**Pasos:**
1. Script `scripts/imagenes/tenistas_sofascore.py` (nuevo): lee el CSV, normaliza el nombre con la **misma `norm()`** de `scripts/imagenes/descargar_imagenes.py`, genera `frontend/imagenes/tenis/<slug>.webp` (o `<id>.webp`) y un bloque nuevo en `manifiesto.json` (`tenis_sofascore`: nombre normalizado → `{id, f, pais, genero, ranking}`; duplicados → lista). **No borres** los JPG ni el bloque `tenis` viejo hasta confirmar el despliegue (vuelta atrás).
2. Actualizar `frontend/imagenes/creditos.html` y cualquier texto de crédito CC BY-SA **cuando** el bloque nuevo sea el activo.
3. Subida: `scripts/subir_archivo_sofascore.py` (6 conexiones en paralelo) siguiendo `DEPLOYS.md`; despliegue con `scripts/deploy.sh construir|ensayo|desplegar`. **Pide confirmación al titular antes de subir y antes de desplegar.**
4. Pruebas: `tests/test_web_imagenes.py` (manifiesto con el bloque nuevo; duplicado; ausente).
**Aceptación:** la app muestra la foto nueva de los 178 emparejados y las iniciales del que no tiene; la vuelta atrás está anotada en `DEPLOYS.md`.

### F7c — Comprobaciones sin cambio de código (S)
- **Notificaciones por deporte** (F3e): comprobar si `/app/v1/firebase/preferences` ya guarda preferencias por deporte; si no, abrir tarea de servidor (campo nuevo) y dejar la UI detrás de bandera.
- **Planes VIP:** comprobar que `plans` devuelve los 3 planes con `duration_days` y que existen los productos en Play/App Store; si no, avisar al titular.
- **Disponibilidad NBA:** confirmar en `sports_feed.dart`/`SportAlerts` qué claves trae `availability` (estado, jugadores, minutos) y si hay nombres; el render **no** asume nombres.

---

## F8 — Cierre y release (M)

1. **Traducciones:** una pasada final para que **no quede ningún texto fijo** ni clave sin traducir; revisa las claves nuevas del Apéndice A en los 6 idiomas (alemán y francés a 360 dp). `flutter test test/l10n_test.dart` y `l10n_runtime_test.dart` en verde.
2. **Retirar andamios:** alias `live*` sin uso, `SealLine` si nadie la usa, `QfColors.football/nba/tennis` si quedaron, constantes de la paleta v3. `docs/REDISENO_NBA_TENIS_20261030.md` → añade cabecera «sustituido por PLAN_REDISENO_CYBERCORE_20261114.md».
3. **Icono y ficha de Play:** fondo del icono adaptativo `#07080C`; si cambia la identidad visual, regenerar capturas de la ficha con `tool/make_play_store_assets.py` (`docs/play_store/`).
4. **Versión:** `pubspec.yaml` → **`1.2.0+13`** (o la siguiente libre; hoy `1.1.1+12`). Firma y bundle según `docs/FIRMA_ANDROID.md` y `docs/PLAY_CONSOLE_20261015.md`.
5. **QA completo:** recorrer el Apéndice C en emulador (es y de), sesión sin iniciar y con sesión, usuario gratis y VIP, sin red, con la API lenta. Rendimiento: perfilar scroll en Inicio, Mercados, Análisis (60 fps en el emulador no es la medida; usa el modo *profile* o un dispositivo real si hay).
6. **Actualización obligatoria:** **no** activarla; si el titular lo pide, `docs/FORCE_UPDATE.md` (orden en `/control/configuracion-app`).
7. `harness/progreso.md` con las decisiones clave del rediseño y `PENDIENTES.md` con lo que quedó abierto.

---

## Apéndice A — Textos nuevos (español de partida)

> **Antes de crear una clave, busca si el texto ya existe** (`grep -n "<texto>" apps/mobile/lib/l10n/app_es.arb`): muchísimos ya existen (`welcome*`, `access*`, `guide*`, `prefs*`, `ledger*`, `inbox*`, `vip*`, `sportStat*`, `parley*`, `ladder*`, `mmTitle`…). Los nombres de clave son **sugerencias**; sigue la convención del archivo (`area` + `Cosa`). Las cifras entre `{}` son parámetros ICU. Traduce a es, en, pt, fr, it, de con `tool/l10n_add.py`.

| Pantalla | Textos nuevos (es) |
|---|---|
| Cáscara | «Picks» (`navPicks`) |
| Inicio | «Ver pronóstico gratis» · «Acierto · 30 días» · «{won} de {total} picks sellados» · «Agenda» · «desde {hora}» |
| Predicciones | «Desbloquear · {coste}» · «VIP» · «Cuota acumulada» · «Prob. de este escalón» · «Probabilidad conjunta» · «Cuota combinada» |
| Mercados | «Modelo activo» · «{n} familias de mercado en el radar» · «{won}/{total} publicados acertados · {pct}» · «Hoy» |
| Coins / Movimientos | «Saldo» · «Ganadas» · «Gastadas» · «Marcar asistencia · +{n}» · «Todavía no hay movimientos» (ya existe) |
| Perfil / Preferencias | «Elige de qué deportes quieres recibir avisos.» · «Desactivadas» · «Comparte datos cifrados para medir qué anuncios funcionan.» (resumen corto) · «Ver más» / «Ver menos» (comunes) · «Detectado» |
| Avisos | «Todos» · tipos que envíe el servidor (p. ej. «Nuevo pronóstico», «Bajas actualizadas», «Reporte de lesiones», «Resultado») · «Aquí verás los pronósticos nuevos, las bajas y los resultados de tus deportes.» |
| Menú | «Acceso VIP» · «Todos los pronósticos, sin monedas» |
| Guía | «75 % = 3 de cada 4» · «Probabilidad del modelo» · «La que implica la cuota {cuota}» · «Comparar ambas ayuda a ver si el precio es razonable.» · «Publicado / con su cuota» · «Partido / sin cambios» · «Resultado / al historial» · «En juego» · «Solo con dinero que puedas perder» · «Solo si eres mayor de edad» · «Si deja de ser un pasatiempo, pide ayuda» · «Anterior» / «Siguiente» |
| Ficha (común) | «Props» (pestaña) · «Desbloquear todo · {coste}» · «Pick destacado · gratis» · «con monedas o VIP» |
| Props | «Todos» · «Puntos» · «Rebotes» · «Asist.» · «Triples» · «{n} de los últimos 5» |
| Análisis (secciones) | «Resumen» · «Forma» · «Cara a cara» · «Tabla» · «Probabilidad» · «Comparativa» · «Clasificación» · «Disponibilidad» · «Superficie» · «Modelo» · «Cómo llegan» · «Promedios · últimos 10» · «Todos» · «Casa · fuera» · «{equipo} mejor en {n} de {total}» · «Ataque / Creación / Remate / Córners / Defensa» · «Último» · «Casa / Fuera» · «{n} sin perder» · «Victorias / Empates» · «Goles por partido» · «Ver los {n} partidos» · «Ascenso / Play-off / Descenso» |
| Análisis NBA | «Factores del partido» · «Mejor récord» · «Rinde fuera de casa» · «Más descanso» · «Mejor racha» · «Playoffs directos (1–6)» · «Play-in (7–10)» · «Fuera (11–15)» · «Reporte aplicado» · «{n} jugadores en el reporte» (ya existe `sportAvailListed`) · «Back-to-back · jugó ayer» · «Descansó {n} día(s)» · «Margen en victoria / derrota» |
| Análisis tenis | «Pista dura / Tierra batida / Hierba» · «Hoy» · «Índice de forma» · «{n} % a 3 sets» · «{n} % con tie-break» · «Primer duelo» · «Nunca se han enfrentado…» · «Duración del partido» · «{n} % en 2 sets / 3 sets» · «Gana cada set» · «El 3.er set solo se juega si hay empate 1–1.» · «Juegos totales · probabilidad de «más de»» · «Hándicap de juegos» · «Habrá tie-break» · «Juegos esperados» · rondas («Semifinal», «Cuartos», «Octavos», «Ronda de 32/64», «Final de clasificación») |
| Alertas | «Lesión» · «Selección» · «Sanción» · «Duda» · «Vuelve» · «Con su selección · vuelve {fecha}» · «Ya entrena con el grupo» · «Duda para el partido» · «Vuelve a {aprox}» · «Alineaciones» · «Último once conocido» · «último once, vs {rival} · {fecha}» · «{equipo} · sin alineación guardada» · «El once se confirma una hora antes del partido y aparecerá aquí con foto.» · «Sin alertas» · «Sin incidencias en los últimos 7 días» |
| Desbloquear | «Desbloquear pronóstico» · «Se abre al instante» · «El pronóstico, su probabilidad y la cuota» · «Análisis, cara a cara y alertas del partido» · «Se queda abierto para este partido» · «Costo» · «Tu saldo» · «Te quedarán {n} monedas» · «Necesitas {coste} · tienes {saldo}» · «Desbloquear · {coste} monedas» · «Te faltan {n} monedas» · «Gana monedas en unos minutos o hazte VIP» · «Ganar {n} monedas» · «O desbloquea todos con VIP» · «Sin gastar monedas · desde {precio} al mes» · «Las monedas se ganan dentro de la app. No se cobra dinero.» |
| VIP | «Todos los pronósticos de hoy, desbloqueados.» · «{n} picks de fútbol, NBA y tenis, cada uno sellado antes del partido.» · «Elige tu plan» · «Ahorra {pct} %» · «Equivale a {precio} al mes» · «{precio} al mes · {precio} al día» · «Qué desbloqueas» · 4 beneficios (título + línea) · «Ver gratis vs VIP» / «Ocultar comparación» · filas de la tabla · 3 sellos («Sellado antes del partido», «Cancela cuando quieras», «Pago por Google Play») · 5 preguntas con respuesta · «Empezar VIP {plan} · {precio}» · «Se renueva por {precio} {periodo}. Cancela cuando quieras en Google Play › Suscripciones.» |
| Idioma / Acceso | «Gratis para empezar» · «Sin tarjeta» · «Podrás cambiarlo después desde tu Perfil.» |
| Actualización / Privacidad | «Versión {v}» · 3 novedades (si el servidor las da) · «Suscripciones con Google Play o App Store» · «Medición de uso, diagnóstico y anuncios (Meta): activados» · «Leer la política · ajustar preferencias» |

## Apéndice B — Pruebas existentes que probablemente haya que tocar

`qf_theme_test`, `qf_shapes_test`, `product_navigation_test`, `home_screen_test`, `home_sport_test`, `featured_pick_test`, `predictions_ui_test`, `live_ladder_test`, `ladder_progress_test`, `live_parley_test`, `live_markets_test`, `market_catalog_test`, `market_family_catalog_test`, `coins_ui_test`, `rewards_ads_card_test`, `profile_sports_test`, `inbox_sport_test`, `consent_defaults_test`, `detail_no_sealed_test`, `generic_sport_ui_test`, `match_facts_test`, `alerts_tab_test`, `alerts_model_test`, `access_screen_test`, `language_selection_test`, `app_update_test`, `l10n_test`, `l10n_runtime_test`, `app_smoke_test`. Regla: **no relajes una aserción para que pase**; si el diseño cambió, cambia el finder y conserva lo que la prueba protege.

## Apéndice C — Lista de verificación visual (36 láminas)

Para cada captura: forma de las esquinas (10/16/18), borde y brillo, tipografía por rol, mayúsculas y espaciado de letras, **una sola acción verde**, color + icono/texto (nunca solo color), objetivos ≥ 44 dp, imagen correcta (persona redonda / logo cuadrado / iniciales), estados vacío/cargando/error, 360 dp sin desbordes, `de` sin recortes.

`Main` · `Predicciones` · `Mercados` · `Mercado` · `Coins` · `Movimientos` · `Perfil` · `Preferencias` · `PreferenciasCompleta` · `Avisos` · `Menu` · `Guia` · `GuiaCompleta` · `Partido` · `PartidoProps` · `PartidoNBA` · `PartidoNBAAnalisisCompleto` · `PartidoTenis` · `PartidoTenisAnalisis` · `PartidoTenisAnalisisCompleto` · `PartidoAnalisis` · `PartidoAnalisisCompleto` · `PartidoAlertas` · `PartidoAlertasCompleto` · `Desbloquear` · `DesbloquearSinMonedas` · `Vip` · `VipCompleto` · `Idioma` · `Bienvenida` · `BienvenidaTodas` · `Acceso` · `Actualizacion` · `ActualizacionObligatoria` · `PrivacidadActualizada` · `Sistema`.
