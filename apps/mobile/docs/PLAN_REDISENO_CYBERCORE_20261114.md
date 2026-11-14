# Rediseño CyberCore de la app Flutter — plan de implementación (parte 1: qué y con qué)

Fecha: 14-nov-2026 · Estado: **render aprobado, código Flutter sin empezar** · App: `apps/mobile` (paquete `gobet`, versión actual `1.1.1+12`).
Este documento va con otro: **[PLAN_REDISENO_FASES_20261114.md](PLAN_REDISENO_FASES_20261114.md)** (qué hacer, en qué orden, con qué pruebas). Lee primero este, luego el de fases.

Está escrito para que lo ejecute **otra IA o persona sin haber visto la conversación original**. Todo lo que hace falta saber está aquí o en los archivos que enlaza. Si algo contradice a `CLAUDE.md`, gana `CLAUDE.md`.

---

## 0. Antes de tocar nada (reglas del proyecto que aplican a este trabajo)

Resumen de `CLAUDE.md` (léelo entero; esto no lo sustituye):

1. **Responde y documenta en español.**
2. **Protocolo de inicio:** ejecuta `./scripts/harness_check.sh` en la raíz. Si falla, tu única tarea es arreglarlo. Lee `PENDIENTES.md` y las últimas 120 líneas de `harness/progreso.md`.
3. **Un `git worktree` por tarea**, desde `origin/main`: `git worktree add -b <rama> <carpeta> origin/main`. **Una rama por fase (o sub-fase) y un PR a `main`.** No dejes cambios sin confirmar ni ramas sin PR. La rama actual del titular (`sesion/principal`) tiene muchos archivos sin seguimiento: **no trabajes ahí**.
4. **Traducciones:** todo texto visible que se añada o cambie se traduce a **es, en, pt, fr, it, de en el mismo cambio**. Sin cadenas fijas en widgets: `context.l10n.clave` + `python apps/mobile/tool/l10n_add.py` (ver `apps/mobile/docs/TRADUCCIONES.md`). Las pruebas `test/l10n_test.dart` lo exigen (mismas claves en los 6 idiomas, ningún `Text('literal')`, ninguna traducción copia del español salvo siglas).
5. **Versión de la app:** sube el código de versión en `pubspec.yaml` en cada build que vaya a Play (ver `docs/FORCE_UPDATE.md`). Plan: `1.2.0+13` al cerrar la fase 5; ver fase 8.
6. **Entorno local:** Flutter vive en `C:\flutter` (fuera del PATH; en esta máquina también aparece `C:\src\flutter\bin` en el PATH, comprueba cuál usa `flutter --version`). Emulador real: `emulator-5556` (usa timeouts; prueba siempre el **release**). Ver `docs/AUDITORIA_STACK.md` y la memoria del proyecto si la tienes.
7. **Servidor:** NUNCA despliegues ni subas archivos al VPS sin **confirmación expresa del titular**, y siempre siguiendo `DEPLOYS.md` (un despliegue a la vez, compara lo desplegado con `main`, anota la vuelta atrás). La app solo consume la API; los cambios de servidor van en PR aparte (fase 7).
8. **No toques** triggers de base de datos ni el orden `predecir → seleccionar → sellar → publicar`. Este rediseño es de presentación.
9. **No inventes** que un archivo o módulo existe: `ls`/`grep` antes. Lo que aquí se cita con ruta existía el 14-nov-2026.
10. Al cerrar cada fase: marca la tarea en `harness/tareas.md` y añade a `harness/progreso.md` la decisión clave (el porqué, no el qué).
11. La app es **sin fines de lucro** (decisión del titular del 27-oct-2026). Eso cuenta como uso no comercial para licencias de datos e imágenes, pero **no cambia** el derecho a la propia imagen de jugadores ni las marcas de equipos y ligas, que se revisan aparte.
12. No añadas manejo de errores ni respaldos para escenarios de proveedor que el README ya descarta.

---

## 1. Qué se construye y qué decidió el titular

Rediseñar **toda la app** (menús, submenús, pestañas, subpestañas, hojas, diálogos) con la estética **CyberCore** que ya usa la web (`frontend/vendor/cybercore`), con **el mismo formato en fútbol, NBA y tenis** en cada pestaña, ergonómica, fácil de leer, atractiva y orientada a conversión (marketing) **sin patrones oscuros**.

Decisiones del titular, en orden cronológico (no las deshagas sin preguntarle):

| # | Fecha | Decisión |
|---|---|---|
| 1 | 30-oct | NBA y tenis están aprobados para publicar picks. **No** añadir etiquetas «En validación». |
| 2 | 13-nov | La app adopta el **tema CyberCore de la web** (cian, verde, amarillo, magenta sobre fondo casi negro; Rajdhani + JetBrains Mono + Exo 2; esquinas cortadas). **Sustituye** a la «paleta v3 azul + ámbar» propuesta el 30-oct (`docs/REDISENO_NBA_TENIS_20261030.md`). |
| 3 | 13-nov | Mismo formato de pestañas/subpestañas para fútbol, NBA y tenis. |
| 4 | 13-nov | La pestaña **Mercados** adopta el acabado de la captura que aportó el titular: tarjetas de color por familia con anillo de acierto, hoja de radar, barra de puntos. |
| 5 | 13-nov | Todos los enfrentamientos llevan imagen: **escudos** (fútbol), **logos** (NBA), **fotos** (tenistas, jugadores). Retratos de personas **redondos con aro cian**; escudos y logos **cuadrados, sin recortar**. |
| 6 | 13-nov | NBA: nueva pestaña **PROPS** de jugadores (foto, pronóstico, probabilidad, cuota, casa de apuestas, últimos 5). |
| 7 | 13-nov | Fútbol → Alertas: jugador con **foto, posición, lesión/motivo y fecha de regreso**; las **Alineaciones** van al final de Alertas, debajo de las bajas. |
| 8 | 13-nov | Fútbol → Análisis reúne **Resumen («Cómo llegan»), Forma, Cara a cara y Tabla** en una sola pestaña con gráficos. NBA: probabilidad, comparativa, forma, cara a cara, clasificación, disponibilidad. Tenis: probabilidad, forma, superficie, cara a cara, modelo. |
| 9 | 13-nov | VIP: **3 planes** (mensual, 3 meses, anual). La pantalla se rediseña para convertir sin presión (ver §5.12). |
| 10 | 13-nov | **Fotos de tenistas: reemplazar por completo** las 179 de Wikimedia por las de SofaScore (`C:\Users\huye\Documents\SOFASCORE\data\images\tenistas`, 1.182 archivos). **Hacerlo dentro de este rediseño**; subir y desplegar solo con confirmación expresa del titular. |
| 11 | 14-nov | Se **quitó** la línea terminal «> SELLO 9f3a…» de todas las pantallas. Se **conservan** las menciones en texto («sellado antes del partido», «picks sellados»). |

**Fuera de alcance** (no lo hagas): pantallas heredadas de la plantilla «gobet» (`lib/sign_in/`, `lib/log_in/`, `lib/forget_password/`, `product/market_screens.dart`, `product/match_detail.dart`, `product/profile_settings.dart`); nuevos deportes; cambios en el motor, en los picks o en la regla de publicación; cambiar precios o planes (vienen de la tienda y del servidor).

---

## 2. Material de referencia (la fuente de verdad visual)

Todo está en **`apps/mobile/docs/render_cybercore_20261114/`**:

| Carpeta/archivo | Qué es |
|---|---|
| `capturas/*.png` | **Una captura por lámina** (36). Es lo que debe parecerse la app. Ancho 390, alto según la lámina; las «vista completa» son pantallas largas desplegadas. |
| `pantallas/*.dc.html` | Fuente de cada lámina. **Sí sirven como especificación numérica**: cada elemento lleva `style="…"` con tamaños, colores, tipografía y espaciados exactos. Los `{{campos}}` son datos y los `<sc-if>`/`<sc-for>` son condicionales/bucles. **No se abren solos en un navegador** (necesitan el runtime del lienzo): usa las capturas para ver y el código para medir. |
| `canvas.json` | Índice del lienzo: posición, tamaño y título de cada lámina, y el orden. |
| `ASSETS.md` + `assets/` | Las 49 imágenes del render y su origen real (los `/_blob/<id>` del HTML). |
| `README.md` | Cómo leer los `.dc.html` (equivalencias CSS → Flutter). |

Enlace al lienzo original (privado; puede no abrirse): https://claude.ai/artifact/MxGtiSQnzhVcizzkiCbL73

**Reglas de lectura de la medición:** el render está a **390 × 844 px; 1 px = 1 dp**. La app debe verse bien de **360 a 430 dp de ancho** (hay pruebas a 360 dp). Las alturas del render son las de un teléfono de referencia; en Flutter el contenido debe **desplazarse** (`ListView`/`SingleChildScrollView`) y la cabecera, la barra de pestañas y la barra de acciones inferiores quedan fijas donde el render las fija.

### 2.1 Inventario de láminas → archivos de Flutter → fase

| Lámina (captura) | Qué muestra | Archivos Flutter a cambiar (`lib/…`) | Fase |
|---|---|---|---|
| `Main` | Inicio | `product/live_home.dart` (HomeTab), `home_hero.dart`, `home_sport.dart`, `home_agenda.dart` | 3a |
| `Predicciones` | Alta prob. / Escalera / Parley por deporte | `product/live_picks.dart`, `live_ladder.dart`, `live_parley.dart`, `sport_predictions.dart`, `predictions_switcher.dart` | 3b |
| `Mercados` | Familias de mercado con anillo y radar | `product/live_markets.dart`, `market_hub.dart`, `sport_markets.dart` | 3c |
| `Mercado` | Detalle de mercado Hoy / Anteriores | `product/live_market_detail.dart`, `market_hub.dart` (`MarketScaffold`) | 3c |
| `Coins` | Saldo, asistencia, video, ofertas, invitar | `product/live_rewards.dart` | 3d |
| `Movimientos` | Historial de monedas | `product/live_rewards.dart` (`_Ledger`) | 3d |
| `Perfil` | Cuenta, mis deportes, preferencias | `product/live_profile.dart`, `my_sports.dart` | 3e |
| `Preferencias`, `PreferenciasCompleta` | Privacidad y preferencias | `core/firebase_preferences.dart` | 3e |
| `Avisos` | Bandeja de avisos | `core/firebase_preferences.dart` (`FirebaseInbox`) | 3e |
| `Menu` | Hoja «Más» (☰) | `product/live_more.dart` | 3e |
| `Guia`, `GuiaCompleta` | Guía de pronósticos | `product/live_guide.dart` | 3e |
| `Partido` | Ficha, pestaña Pronóstico (fútbol) | `product/live_detail.dart`, `live_forecast.dart`, `live_match_markets.dart`, `match_visuals.dart`, `live_statistics.dart` (`MatchFixtureHeader`) | 4a, 4b |
| `PartidoProps` | NBA, pestaña Props | `product/sport_detail.dart`, nuevo `sport_props.dart` | 4b |
| `PartidoAnalisis`, `PartidoAnalisisCompleto` | Fútbol, Análisis | `product/live_statistics.dart`, `live_match_facts.dart`; nuevo `analysis_football.dart` | 4c |
| `PartidoNBA`, `PartidoNBAAnalisisCompleto` | NBA, Análisis | `product/sport_detail_tabs.dart` (`SportAnalysis`); nuevo `analysis_nba.dart` | 4d |
| `PartidoTenisAnalisis`, `PartidoTenisAnalisisCompleto` | Tenis, Análisis | `product/sport_detail_tabs.dart`; nuevo `analysis_tennis.dart` | 4e |
| `PartidoAlertas`, `PartidoAlertasCompleto` | Fútbol, Alertas + alineaciones | `product/live_alerts.dart`, `live_match_facts.dart`; nuevo `lineup_pitch.dart` | 4f |
| `PartidoTenis` | Tenis, H2H (estado «primer duelo») | `product/sport_detail_tabs.dart` (`SportH2h`) | 4g |
| `Desbloquear`, `DesbloquearSinMonedas` | Hoja de desbloqueo | `product/live_shell.dart` (diálogos `unlock-confirm` y `needCoins`) | 5a |
| `Vip`, `VipCompleto` | Acceso VIP (3 planes) | `product/live_vip.dart`, `vip_performance.dart` | 5b |
| `Idioma`, `Bienvenida`, `BienvenidaTodas`, `Acceso` | Primer arranque | `l10n/language_selection_screen.dart`, `onbonding_screen/second_screen.dart`, `product/welcome_art.dart`, `core/access_screen.dart`, `core/access_illustrations.dart` | 5c |
| `Actualizacion`, `ActualizacionObligatoria`, `PrivacidadActualizada` | Diálogos de arranque | `core/app_update.dart`, `product/live_shell.dart` (diálogo `privacyUpdateTitle`) | 5d |
| `Sistema` | Hoja de componentes y tokens | (referencia; ver §3 y §4) | 1 |

> Antes de editar un archivo de la tabla, **ábrelo y verifica** que sigue teniendo esa clase (`grep -n "^class " <archivo>`). Esta tabla es del 14-nov.

---

## 3. Sistema de diseño (tokens)

### 3.1 Color — sustituye a `QfColors` v3 en `product/qf_theme.dart`

| Token (nombre sugerido) | Hex | Uso | Contraste sobre `bg` / `surface` / `surface2` |
|---|---|---|---|
| `bg` | `#07080C` | Fondo de pantalla | — |
| `surface` | `#12141D` | Tarjetas, hojas, barras | — |
| `surface2` | `#181A25` | Chips, campos, fila destacada | — |
| `text` | `#F0F1F5` | Texto principal | 17,7 / 16,3 / 15,3 |
| `text2` | `#B2B7C7` | Texto secundario | 10,0 / 9,2 / 8,6 |
| `muted` | `#939AB0` | Metadatos, etiquetas | 7,1 / 6,5 / 6,2 |
| `cyan` | `#00F0FF` | **Navegación, selección, dato/probabilidad**, bordes y brillos | 14,2 / 13,0 / 12,3 |
| `green` | `#05FFA1` | **Acción principal** y acierto/éxito | 15,1 / 13,8 / 13,0 |
| `yellow` | `#FCEE0A` | **VIP y monedas** | 16,6 / 15,2 / 14,3 |
| `magenta` | `#FF2A6D` | Fallo, error, «en vivo» | 5,5 / 5,1 / 4,8 |
| `magentaText` | `#FF7AA3` | Texto de error/peligro sobre fondo oscuro | 8,2 / 7,5 / 7,1 |
| `chrome` | `#D1D4DE` | El **«otro» lado** en comparaciones (visitante/rival) | 13,5 / 12,4 / 11,7 |
| `slate` | `#747D99` | Empate, neutro, barras apagadas | 4,5 sobre `surface` (solo no-texto) |
| `track` | `#2A2D3A` | Pista de barras vacías | — |
| `onGreen` | `#03110F` | Texto sobre verde/cian (14,5:1) | — |
| `onYellow` | `#1A1800` | Texto sobre amarillo (14,8:1) | — |

Derivados con transparencia (todos sobre `cyan` salvo indicación): borde de tarjeta `cyan @ 20 %` (`--b`), borde fuerte `cyan @ 48 %` (`--bs`), línea divisoria `#747D99 @ 22 %` (`--ln`), fondo de chip activo `cyan @ 10 %`, fondo de insignia `color @ 9 %` con borde `color @ 40 %`.

**Reglas de uso (obligatorias):**
1. **Una sola acción verde por pantalla.** Las demás acciones son secundarias (borde cian) o VIP (borde amarillo).
2. **El color nunca es la única señal.** Acierto = ✓ + verde; fallo = ✗ + magenta; VIP = candado + amarillo; empate = «E» + gris.
3. El **amarillo es solo VIP/monedas**; el **magenta es solo fallo/error/en vivo**.
4. En toda comparación de dos lados: **local/primero = cian**, **visitante/segundo = `chrome`**. El valor que gana se muestra en negrita y color pleno; el que pierde, atenuado (`@ 35 %`). En métricas donde «menos es mejor» (goles/xG en contra, puntos en contra) gana el menor.
5. Quita `QfColors.football`, `nba` y `tennis` como acentos de deporte: **el chip de deporte activo es siempre cian**. Los colores por familia de mercado (naranja, violeta, lima, azul, verde, ámbar) viven **solo** en las tarjetas de Mercados y en la bienvenida (ver `market_hub.dart` → `_look`).
6. `contrastRatio()` (en `qf_theme.dart`) debe seguir pasando ≥ 4,5:1 para todo texto sobre `bg`, `surface` y `surface2` (actualiza `test/qf_theme_test.dart`; `slate` no lleva texto).

`ThemeData`: `ThemeData.dark(useMaterial3: true)` con `scaffoldBackgroundColor: bg`, `colorScheme` (`primary: cyan`, `onPrimary: onGreen`, `secondary: yellow`, `onSecondary: onYellow`, `surface`, `onSurface: text`, `error: magenta`, `outline: cyan@20%`) y el `textTheme` con `Exo 2`.

### 3.2 Tipografía

| Familia | Dónde | Pesos | Estado en el repo |
|---|---|---|---|
| **Rajdhani** | Títulos, etiquetas, pestañas, botones, insignias. Casi siempre **MAYÚSCULAS** con `letterSpacing` .06–.2 em | 500, 600, 700 | `fonts/Rajdhani-Medium.ttf`, `Rajdhani-Bold.ttf` ya declaradas. Usa 500 y 700 (el 600 del render → 700). |
| **JetBrains Mono** | Cifras, porcentajes, cuotas, horas, hashes, contadores | 500, 700 | Solo `JetBrainsMono-Medium.ttf`. **Añadir `JetBrainsMono-Bold.ttf`** (OFL). |
| **Exo 2** | Cuerpo de texto, nombres, descripciones | 400, 500, 600, 700 | **No está.** Añadir `Exo2-Regular/Medium/SemiBold/Bold.ttf` (OFL, Google Fonts) + `OFL-Exo2.txt` en `fonts/` y declararlas en `pubspec.yaml`. |

Reemplaza `fontFamily: 'Gilroy Medium'` del `textTheme` por `Exo 2`. **No borres Gilroy**: las pantallas heredadas lo siguen usando.

Escala (px = dp del render):

| Rol | Familia | Tamaño / peso / tracking |
|---|---|---|
| Marca «QUANTFUT» | Rajdhani | 21 / 700 / .14 em (QUANT blanco + FUT cian) |
| Título de pantalla (hero) | Rajdhani | 30–34 / 700 / .01–.03 em, interlineado 1,02–1,05 |
| Título de sección (h2) | Rajdhani | 22 / 700 / .04 em |
| Etiqueta de sección (`// TÍTULO`) | Rajdhani | 11 / 700 / .16–.18 em, color cian, **lleva el prefijo `// `** |
| Pestaña / chip / botón | Rajdhani | 12–15 / 700 / .06–.1 em |
| Insignia | Rajdhani | 11 / 700 / .12 em |
| Cifra grande (probabilidad) | JetBrains Mono | 34–54 / 700 (brillo de texto cian) |
| Cifra media / fila | JetBrains Mono | 14–20 / 700 |
| Meta (hora, liga, hash) | JetBrains Mono | 10–12 / 500 |
| Cuerpo | Exo 2 | 14 / 400, 13 secundario, 11–12 nota |
| Nombre de equipo / jugador | Exo 2 | 14–15 / 600–700 |

### 3.3 Forma, bordes, brillos, movimiento

- **Esquinas cortadas** (ya existe `CutCornerBorder` en `product/qf_shapes.dart`: corta arriba-derecha y abajo-izquierda, igual que el `clip-path` del render): **10 dp** en chips, botones, filas y tarjetas pequeñas; **16 dp** en tarjetas grandes y hero; hojas inferiores: **18 dp en las dos esquinas superiores** (nuevo `BottomSheetShape`). Con borde 1 dp.
- **Tarjeta fuerte** (hero, destacado, mercado activo): borde `cyan@48%`, fondo `surface` + **líneas de barrido** (`repeating-linear-gradient 0deg, cyan@3% 1px, transparente 4px` → `CustomPainter` con una línea cada 4 dp) y, si es el elemento destacado de la pantalla, un brillo `0 0 22px cyan@14%`.
- **Brillo (glow)** solo en: cifra grande, chip/tarjeta activa, botón principal (`0 8px 28px green@16%`), icono de la ficha. Estático (`BoxShadow`), un elemento por zona.
- **Movimiento:** transiciones ≤ 200 ms; **respeta `MediaQuery.disableAnimations`** (sin glitch, sin parpadeo). Nada de contadores falsos ni urgencia artificial.
- **Objetivos táctiles ≥ 44 dp** (el render ya los cumple; mantenlo). `Semantics` con `selected`/`checked`/`label` en chips, pestañas, interruptores y casillas.
- **Iconos:** trazo 2 dp, esquinas redondeadas, 18–24 dp (Tabler/Lucide MIT o `Icons.*` de Material con trazo equivalente). Los paths SVG del render están en los `.dc.html` (`<path d="…">`) por si se quieren portar tal cual con `flutter_svg` (ya es dependencia).

### 3.4 Equivalencias CSS del render → Flutter

| En el render | En Flutter |
|---|---|
| `clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px))` | `CutCornerBorder(cut: 10)` como `shape` de `Material`/`Ink`/`DecoratedBox` (+ `side` para el borde) |
| `--cut2` (16 px) | `CutCornerBorder(cut: 16)` |
| `border: 1px solid var(--b)` | `BorderSide(color: cyan.withValues(alpha: .2))` |
| `linear-gradient(120deg,#05ffa1,#8affdf)` | `LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [green, Color(0xFF8AFFDF)])` |
| `conic-gradient(#05ffa1 0 76%, #ff2a6d 0)` (anillo) | `CustomPainter` con `drawArc` (ver `_RingPainter` en `live_ladder.dart`, ya existe) |
| `filter: blur(6px)` (pick bloqueado) | `ImageFiltered(imageFilter: ImageFilter.blur(sigmaX: 6, sigmaY: 6))` sobre el texto; ya existe `LockedBlur` en `live_widgets.dart` |
| `position: sticky` (barra de acceso a secciones) | `SliverPersistentHeader(pinned: true)` o `Column` con cabecera fija y contenido en `ListView` |
| `href="#id"` (saltar a sección) | `Scrollable.ensureVisible(key.currentContext!, duration: 250ms)` con una `GlobalKey` por sección |
| `overflow-x: auto` (chips en fila) | `ListView(scrollDirection: Axis.horizontal)` o `SingleChildScrollView(scrollDirection: Axis.horizontal)` |
| `white-space: pre-line` (saltos `\n` de títulos) | `Text` con `\n` en la cadena (ya lo hace la bienvenida) |
| `<svg>` radar / pista | `CustomPainter` |
| Interruptor `role="switch"` 52×30 | `QfSwitch` (nuevo, ver §4) — **no** el `Switch` de Material |

---

## 4. Piezas nuevas (widgets) — contrato mínimo

Todas en `lib/product/` salvo indicación. Reutiliza lo que ya existe en `qf_shapes.dart` (`CutCornerBorder`, `QfCard`, `QfBadge`, `SegmentedBar`, `ProbabilityBar`, `qfTitle`, `qfError`) y `live_widgets.dart` (`liveButton`, `LockedBlur`, `TeamCrest`, `RealPickCard`). **Cada pieza lleva prueba de widget** (`test/qf_widgets_*_test.dart`).

| Pieza | Qué es | Parámetros clave | Usada en |
|---|---|---|---|
| `QfTheme` (tokens) | Las constantes de §3.1 como `abstract final class QfColors` + `QfText` (estilos precalculados) + `QfSpace`. Mantén los **alias `live*`** (`liveBg`, `livePanel`, `liveCyan`, `liveGold`, `liveGreen`, `liveMuted`) apuntando a los tokens nuevos mientras queden pantallas sin migrar; retíralos al final de la fase 3. | — | todo |
| `QfCard` (ampliar) | Tarjeta con corte 10/16, `strong: true` activa borde 48 % + líneas de barrido, `glow: true` | `cut`, `strong`, `glow`, `padding`, `onTap` | todo |
| `QfButton` | Principal (gradiente verde), secundario (borde cian), VIP (borde amarillo), peligro (texto magenta claro), Google (blanco) | `variant`, `label`, `icon`, `onPressed`, `busy` | todo |
| `QfTabs` | **Una sola pieza de pestañas.** Modo `segmented` (2–5 pestañas, contenedor con borde, activa con subrayado interior 2 dp cian) y modo `chips` (desplazable, cada chip con borde; activa = borde y texto cian, fondo cian 10 %) | `labels`, `index`, `onChanged`, `mode`, `counts` | Pronóstico/Props/Análisis/H2H/Alertas, Hoy/Anteriores, Predicciones (Alta prob./Escalera/Parley), Mercados (Partido/Goles), filtros |
| `QfSectionNav` | Barra fija de chips que **salta a secciones** de una pestaña larga | `sections: [(label, GlobalKey)]` | Análisis de fútbol/NBA/tenis, Guía |
| `QfSportSelector` | Los 3 chips Fútbol/NBA/Tenis (icono + texto + contador). **Reemplaza** el estilo de `sport_selector.dart` (mantén su lógica, `SportKind` y el comportamiento por `deporte_id`) | `sports`, `value`, `counts` | Inicio, Predicciones, Mercados |
| `QfBadge` (ampliar) | Estados: `free`, `won`, `vip`(candado), `lost`, `live`, `review`, `voided`, `doubt` | `kind` | todo |
| `QfSwitch`, `QfCheckbox` | Interruptor 52×30 con borde y perilla cuadrada; casilla 22×22 con ✓ negro | `value`, `onChanged`, `semanticLabel` | Preferencias, Acceso |
| `QfPips` | Barra de casillas (12 por defecto): llenas, «se gastan» (cian discontinuo), «faltan» (magenta discontinuo) | `total`, `filled`, `spend`, `missing` | Desbloquear, Coins, Escalera |
| `QfRing` | Anillo de porcentaje con cifra al centro | `value`, `color`, `trackColor`, `size`, `stroke` | Mercados (tiles), Inicio, VIP, Bienvenida |
| `QfRadar` | Radar de 5 ejes con 2 polígonos (local cian relleno 26 %, rival `chrome` discontinuo) + 4 anillos | `labels`, `a`, `b` (0–1) | Análisis fútbol, Bienvenida 2 |
| `QfDivergingRow` | Fila comparativa: valor izq., etiqueta centro, valor der., barras que crecen desde el centro. Resalta al ganador | `label`, `a`, `b`, `lowerIsBetter`, `format` | Comparativa/Resumen/Superficie |
| `QfDominanceDots` | N rombos (10 en fútbol, 7 en NBA) cian/`chrome`/gris + frase «X mejor en N de M» | `winners` | Resumen, Comparativa |
| `QfFormPills` | 5–6 píldoras G/E/P (letra + color + marcador + rival + local/visita), la última con borde 2 dp y brillo y etiqueta «ÚLTIMO» | `results` | Forma (los 3 deportes) |
| `QfMarginBars` | Barras de margen por partido (arriba verde = victoria, abajo magenta = derrota) con eje | `margins` | Forma NBA |
| `QfStackedBar` | Barra apilada proporcional (victorias/empates/victorias; 2 o 3 partes) | `parts` | Cara a cara, probabilidad |
| `QfSeasonTrack` | Cinta de N casillas numeradas por zonas (playoffs/play-in/fuera) con marcadores de equipos encima | `size`, `zones`, `marks` | Clasificación NBA |
| `QfStandingsTable` | Mini tabla con zonas laterales, escudo, PJ, DG, PTS y forma en 5 barritas; filas destacadas | `rows`, `highlight` | Tabla fútbol |
| `QfPitch` | Campo vertical con 11 jugadores por formación (`4-3-1-2` → líneas) y foto redonda + dorsal + apellido | `formation`, `players` | Alineaciones |
| `QfAvatar` (en `sport_images.dart`, ampliar) | **Retrato de persona**: círculo, aro cian 2 dp, iniciales si falla la imagen. **Logo/escudo**: cuadrado `contain`, sin aro | `kind: person/logo`, `url`, `size`, `name` | todo |
| `QfBottomSheet`, `QfDialogCard` | Hoja inferior con esquinas superiores cortadas 18 dp, asa de 44×4, borde cian y brillo superior; diálogo centrado con corte 16 | — | Desbloquear, Menú, Actualización, Privacidad |
| `QfStepDots` | Puntos de paginación (activo 26×6 cian, resto 6×6 `#3A3F55`) | `count`, `index` | Bienvenida, Acceso |
| `QfLockedBlur` | Contenido bloqueado: `ImageFiltered` blur 6 + candado + insignia VIP | `child`, `onTap` | Picks, Props, Mercados |
| `QfSegmentedChart` utilidades | Barras verticales (sets, juegos totales) con valor encima y etiqueta debajo | `bars` | Tenis · Modelo |

---

## 5. Especificación por pantalla (qué debe hacer cada una)

Para cada pantalla: **mira la captura y mide en el `.dc.html`**. Aquí solo van las reglas que no se ven en una imagen.

### 5.1 Cáscara (cabecera, barra inferior, selector de deporte)
- **Cabecera** (56 dp, borde inferior cian 20 %): `☰` (44 dp, abre `showMoreSheet`), marca «QUANT**FUT**», chip de **monedas** (altura 44, amarillo, lleva a Coins) y **corona VIP** 44 dp (lleva a VIP). En Coins el chip de monedas no se muestra (la pantalla ya es de monedas). El `AppBar` actual está en `product/live_shell.dart` (~línea 780).
- **Barra inferior** (64 dp, `surface`, borde superior cian 20 %): 5 destinos **Inicio · Picks · Mercados · Coins · Perfil**. Activo: color cian, fondo cian 7 %, línea interior superior de 2 dp. Etiqueta Rajdhani 11. «Picks» es etiqueta **nueva** (clave `navPicks`; hoy es `navPredictions` = «Predicciones», demasiado larga a 360 dp).
- **Selector de deporte**: solo en **Inicio, Predicciones y Mercados** (hay una prueba que lo exige: `product_navigation_test.dart`). Tres chips de 44 dp (activo = fondo cian y texto `onGreen`). Cambiar de deporte **no** cambia de pestaña ni se guarda como deporte de arranque. El orden y la visibilidad vienen de «Mis deportes».

### 5.2 Inicio (`Main`)
Destacado del día (tarjeta fuerte con escudos 58 dp, probabilidad 42 px, barra de 3 partes, botón verde «VER PRONÓSTICO GRATIS» → ficha) · dos tarjetas (acierto 30 días del **deporte elegido** con «N de M picks sellados»; monedas con «Te alcanza para N desbloqueos») · franja de **5 días** (HOY activo) · **Agenda** (hora, dos escudos solapados 30 dp, «Local – Visitante», competición, y a la derecha % verde / candado VIP / «desde HH:MM»). Para NBA y tenis la **misma anatomía**: NBA por hora con logos; tenis por torneo/ronda con las dos fotos redondas. (La lámina solo muestra fútbol; el resto es la misma plantilla con otros datos.)

### 5.3 Predicciones
`QfSportSelector` → **`QfTabs` segmentado** «ALTA PROB. · ESCALERA · PARLEY» → (si aplica) lista. Pick: meta (liga · hora), insignia GRATIS/VIP, escudos/fotos (36 dp, solapados −8), nombre, selección en Rajdhani 17 cian, cuota y probabilidad a la derecha (Mono 26). Bloqueado = `QfLockedBlur`. **Barra inferior fija** con `DESBLOQUEAR · 40` (verde) y `VIP` (amarillo) → hoja de desbloqueo (§5.11). Escalera: barra de 5 segmentos, cuota acumulada, probabilidad del escalón, lista de escalones ganados. Parley: 3 selecciones con deporte + escudos/fotos, probabilidad conjunta y cuota combinada, aviso «Una probabilidad no es una certeza…». **Sigue valiendo la regla actual**: NBA solo muestra Alta prob. si el servidor no ofrece Escalera/Parley (el selector de tipo se oculta por deporte según el catálogo; ver `predictions_switcher.dart`).

### 5.4 Mercados y detalle de mercado
Selector de deporte · título «Mercados y resultados» · **hero** (insignia «MODELO ACTIVO» con punto verde, «N familias de mercado en el radar», «Historial web desde …», píldora «510/622 publicados acertados · 82,0 %», radar decorativo 110 dp) · **rejilla 2 columnas** de tarjetas de familia: anillo con %, icono, nombre, «Abiertos N · Resueltos M», «Publicado a/b», **fila de 10 puntos** (llenos = acierto) y fila «HOY» con 4 imágenes solapadas (escudos/logos/fotos del día). Color por familia (ver `_look`). Familia sin publicaciones: anillo gris con «–» y «Sin publicaciones aún». El **detalle**: cabecera con insignia de línea (CONFIRMADA / NO DESPLEGADA / CORTA / EN REVISIÓN), tarjeta de acierto global + «hoy», `QfTabs` «HOY (n) · ANTERIORES», filas con dos escudos y resultado (GANADO/FALLADO/ANULADO), barra fija de desbloqueo.

### 5.5 Coins y Movimientos
Saldo grande amarillo (48 px mono con brillo amarillo), insignia de racha, barra `QfPips` de «desbloqueos disponibles» · «GANA MONEDAS HOY»: asistencia (7 casillas L-D, hechas con ✓ verde, hoy con borde amarillo, **botón verde «MARCAR ASISTENCIA · +10»**), video (+5), ofertas (+200), invitar (código en mono + «COPIAR») · «Mis movimientos» abre la lista: tarjeta de saldo/ganadas/gastadas, grupos HOY/AYER/ANTES, icono por tipo (desbloqueo, asistencia, video, oferta, invitación, anulación), importe verde si suma y gris si resta, «Ver más/Ver menos» (5 → todos), estado vacío. Tipos y textos ya existen: `ledgerUnlock`, `ledgerAttendance`, `ledgerAd`, `ledgerOffer`, `ledgerReferrer`, `ledgerInvitee`, `ledgerReversal`, `ledgerReferralReversal`.

### 5.6 Perfil y Mis deportes
Tarjeta de cuenta (iniciales, correo enmascarado, insignias «PLAN GRATUITO»/«VERIFICADO» o «ACCESO VIP»), botón «VER PLANES VIP» (amarillo) · «MIS DEPORTES»: lista **reordenable** con asa, interruptor de visibilidad y «POR DEFECTO» en el primero (ya existe `my_sports.dart`; hay que dejar **al menos uno visible**) · Preferencias (notificaciones por deporte, idioma, formato de cuotas, privacidad y medición) · versión · cerrar sesión (magenta).

### 5.7 Menú ☰ y Guía
Hoja «Más»: fila «Acceso VIP» (amarilla), `// APRENDE` (Guía), `// APP` (Mis deportes → Perfil, Evaluar, Compartir), `// LEGAL` (Términos, Privacidad), versión. **Guía**: 6 temas (`guideTopic1..6`, `guideHead1..6`, `guideBody1..6` ya traducidos) con chips y un **gráfico por tema** (probabilidad 3 de 4; cuota vs probabilidad implícita `1/cuota`; línea de tiempo del sello; producto 80·75·70 = 42 %; escalera de 5 peldaños; escudo «18+»). Los números de esos gráficos son **ilustrativos fijos** (no son datos).

### 5.8 Ficha de partido (contenedor común a los 3 deportes)
Cabecera (liga + fecha/hora; cerrar) → **hero** con escudos/logos 58 dp o fotos redondas, probabilidad grande, barra de 2–3 partes y leyenda → `QfTabs` → contenido → barra fija «DESBLOQUEAR TODO · 40» + «VIP».
Pestañas por deporte: **Fútbol** Pronóstico · Análisis · H2H · Alertas. **NBA** Pronóstico · **Props** · Análisis · H2H · Alertas (5 pestañas: fuente 11 dp). **Tenis** Pronóstico · Análisis · H2H · Alertas.
- **Pronóstico:** tarjeta «PICK DESTACADO · GRATIS» (selección Rajdhani 20, cuota + casa + hora, probabilidad Mono 30 verde) y «MERCADOS DEL MODELO»: filas con 1–2 imágenes, nombre del mercado, selección (Rajdhani 16 verde), y a la derecha probabilidad (Mono 17 cian), cuota `@1.85` y «casa · hora». Bloqueado = difuminado + «VIP» + «con monedas o VIP».
- **Props (NBA):** filtro `TODOS · PUNTOS · REBOTES · ASIST. · TRIPLES` + tarjetas de jugador: foto redonda 52 dp con logo del equipo en la esquina, nombre, selección («Puntos · Más de 25,5»), **barra de 5 casillas** con «N de los últimos 5», y a la derecha probabilidad, cuota y casa. Datos: los mercados `player_points|player_rebounds|player_assists|player_threes` que **ya** parsea `sports_feed.dart`.
- **Análisis, H2H, Alertas:** ver 5.9, 5.10 y fase 4.

### 5.9 Análisis (el corazón del rediseño)
**Barra fija de acceso a secciones** (`QfSectionNav`) y tarjetas con `// ETIQUETA` + h2h:
- **Fútbol:** **Resumen «Cómo llegan»** (interruptor TODOS | CASA·FUERA; cabecera con escudos; `QfDominanceDots`; `QfRadar` con ejes ATAQUE/CREACIÓN/REMATE/CÓRNERS/DEFENSA; 10 `QfDivergingRow`: goles a favor/en contra, xG a favor/en contra, tiros, tiros a puerta, córners, ambos marcan, más de 2,5, portería a cero) · **Forma** (por equipo: 5 `QfFormPills` + chips de racha y goles) · **Cara a cara** (`QfStackedBar`, 3 chips: goles/partido, ambos marcan, +2,5; últimos 3 con escudos; botón «VER LOS N PARTIDOS» → pestaña H2H) · **Tabla** (filas alrededor de ambos equipos + zonas + callout de diferencia de puntos).
- **NBA:** Probabilidad de ganar (2 tarjetas grandes con logo, % y barra + 4 «factores del partido») · Comparativa (7 filas) · Forma (6 partidos con `QfMarginBars`) · Cara a cara (últimos 10: 5–5, promedio de puntos totales, 4 resultados) · Clasificación (`QfSeasonTrack` de 15 casillas, zonas 1–6 / 7–10 / 11–15) · Disponibilidad (estado del reporte, jugadores en el reporte, **minutos de bajas** con indicador verde < 20 / amarillo < 50 / magenta ≥ 50, back-to-back).
- **Tenis:** Probabilidad (fotos 76 dp, %, ranking/puntos/tendencia ▲▼, edad, país, «Fritz está N puestos por encima») · Forma (índice 0–100 con barra + 5 últimos con rival, ronda traducida, marcador + racha, % a 3 sets, % con tie-break) · Superficie (cabecera «PISTA DURA»; filas dura-carrera, dura-temporada, tierra, hierba con `QfDivergingRow`; la de hoy resaltada con «HOY») · Cara a cara (estado vacío «0 – 0 · PRIMER DUELO» o lista) · Modelo (duración 2/3 sets, ganar cada set, **barras de «más de» juegos totales**, hándicap −1,5/−3,5/−5,5, tie-break %, «juegos esperados ≈ N»).
- **Cálculo de los gráficos** (para que no dependa del servidor): radar → `ataque = min(gf/2.5,1)`, `creación = min(xGf/2.5,1)`, `remate = min(tirosPuerta/7,1)`, `córners = min(c/9,1)`, `defensa = 1 − min(gc/2.5,1)`, mínimo visual 0,08. Probabilidad implícita de una cuota = `1/cuota`. Juegos esperados ≈ la línea donde «más de» cruza 50 %.

### 5.10 Alertas y alineaciones (fútbol)
Filas de baja (alto 68 dp): foto redonda 44 dp (**iniciales** si no hay foto) con escudo de 20 dp en la esquina, **nombre**, «POS · Equipo» (la posición se **omite** si no se conoce), motivo traducido («Con su selección · vuelve a mediados de nov.») y a la derecha la insignia (LESIÓN, SELECCIÓN, SANCIÓN, DUDA, VUELVE). Debajo: **Alineaciones** (`QfPitch` con el último once conocido de cada equipo: formación, 11 fotos redondas con dorsal y apellido) y, si un equipo no tiene once guardado, la tarjeta discontinua «Córdoba · sin alineación guardada — el once se confirma una hora antes del partido». **NBA** muestra por equipo el estado del reporte (sin nombres: la API solo da conteos y minutos). **Tenis** muestra una fila por jugador «SIN ALERTAS».

### 5.11 Desbloquear (conversión)
Hoja sobre la lista atenuada: partido con escudos y pick difuminado → «Qué obtienes» (3 líneas con ✓) → **bloque de costo**: «COSTO 40 MONEDAS · TU SALDO N» + `QfPips` + frase («Te quedarán 80 monedas» / «Necesitas 40 · tienes 20») → **una** acción verde («DESBLOQUEAR · 40 MONEDAS»; sin saldo: tres atajos +5/+10/+200 y «GANAR 20 MONEDAS») → salida VIP en amarillo («O desbloquea todos con VIP — desde $X al mes») → «Las monedas se ganan dentro de la app. No se cobra dinero.» Sustituye a los diálogos `unlock-confirm` (única acción ámbar actual) y `needCoins` de `live_shell.dart`. **Mantén las claves de prueba** (`ValueKey('unlock-confirm')`) o actualiza las pruebas que las usan.

### 5.12 VIP (conversión)
Orden fijo, de arriba abajo (**prueba antes que precio**): 3 tarjetas de deporte con imagen y contador → titular «TODOS LOS PRONÓSTICOS DE HOY, DESBLOQUEADOS.» + frase → **prueba**: anillo del acierto de ayer (aciertos/fallos) + barras de los 7 días → **«ELIGE TU PLAN»**: lista de **filas seleccionables** (radio + nombre + insignia de ahorro + equivalente por mes/día + precio), **anual preseleccionado** → «QUÉ DESBLOQUEAS» (4 líneas) + botón «VER GRATIS VS VIP» (tabla plegada de 6 filas) → 3 sellos de confianza → preguntas frecuentes plegables (5) → nota de «no es certeza». **Pie fijo**: botón verde «EMPEZAR VIP <PLAN> · <PRECIO>», frase de renovación (**del plan elegido**), «Restaurar compras», «Política de privacidad».
- **Los planes, precios, ahorros y textos de renovación NO se escriben a mano:** salen de `plans` del servidor (`plan_code`, `price_cents`, `duration_days`, `currency`, `play_product_id`/`apple_product_id`) y del precio real de la tienda (`widget.store?.byPlan[...]`). El «ahorro» se calcula contra el plan de menor duración; el equivalente por mes/día se calcula con `duration_days`. Hoy `live_vip.dart` ya lo hace con `_monthly()`, `_period()` y `_plan()`: **conserva esa lógica** y cambia la piel. Con 1, 2 o 3 planes la lista debe verse bien.
- **Anti patrones prohibidos:** sin testimonios inventados, sin «usuarios activos» ni «tasa de ganancia» falsos, sin cuenta atrás, sin «solo quedan N», sin comparar con vicios. Las cifras de la prueba (ayer, 7 días, acierto por deporte) son **reales** (`vip_performance.dart`/API), nunca de relleno.
- La tabla Gratis vs VIP del render dice «10 % del día» y «Parcial»: **verifícalo contra la regla real de publicación** antes de dejarlo (memoria del titular: gratis = alta probabilidad 10 % del día por mayor probabilidad, escalera 1, parley 1).

### 5.13 Primer arranque (Idioma → Bienvenida → Acceso)
- **Idioma:** órbitas + globo, insignia «CONFIGURACIÓN DE IDIOMA», 6 filas (código en tile, nombre nativo, liga), la del idioma del dispositivo con «DETECTADO». Tocar una fila guarda y avanza (comportamiento actual).
- **Bienvenida:** 5 pantallas con los textos `welcome1..5Title/Body`; ilustración propia por pantalla (1 tres tarjetas con escudo/logo/retrato, 2 radar y pestañas, 3 fichas de mercado con anillo, 4 anillo de acierto + historial con ✓/✗, 5 escudo con «NO ES UNA CERTEZA»), `QfStepDots`, «SALTAR» arriba, «SIGUIENTE»/«EMPEZAR» verde.
- **Acceso:** carrusel de 5 mensajes (`accessKicker/Title/Body1..5`) + tarjeta inferior fija: título, frase, **etiquetas «GRATIS PARA EMPEZAR» · «SIN TARJETA»** (nuevas), botón **Google** (blanco, logo oficial), casilla de **18 años y términos**, error en línea «Marca la casilla para continuar con Google.» (no se deshabilita el botón), aviso «Solo con fines informativos…». Conserva el flujo de vincular cuenta anterior (`accessLink*`) que ya existe aunque la lámina no lo muestra.

### 5.14 Avisos, Actualización, Privacidad
- **Avisos:** chips por deporte con contador; cada aviso = imagen (escudo/logo/foto), etiqueta de deporte, tipo, partido, detalle, hora y punto cian si no leído; abre el partido. Vacío: «TODAVÍA NO TIENES AVISOS». **Los tipos de aviso y el texto salen del servidor** (`FirebaseInbox`); no inventes tipos: renderiza los que lleguen.
- **Actualización:** opcional (título, versión, 3 novedades, «ACTUALIZAR AHORA», «MÁS TARDE») y obligatoria (sin salida). La versión y las novedades vienen de `checkAppUpdate`/Remote Config (`docs/FORCE_UPDATE.md`); la lista de 3 novedades del render es **ilustrativa**.
- **Privacidad actualizada / Preferencias:** textos reales `privacyUpdate*` y `prefs*` (ya traducidos). Interruptores con valores por defecto **activados** para medición de uso, diagnóstico y anuncios Meta (así lo dice el texto actual y `consent_defaults_test.dart`).

---

## 6. Datos reales de ejemplo del render y de dónde sale cada dato

El render usa **datos reales del 14-nov-2026** (partidos y estadísticas consultados en la API pública `https://pronosticosdeportivos.pro`), salvo lo marcado como **ejemplo**.

| Dato en el render | Origen real en la app |
|---|---|
| Fútbol: Mallorca–Córdoba, forma, promedios casa/fuera, cara a cara, tabla, último once, bajas | `GET /web/partidos/{match_id}` (ver §7.1). Agenda: `GET /web/partidos?fecha=&dias=` |
| Escudos | `/web/escudos/{team_id}.png` (campo `escudo` de la API) |
| NBA: Heat–Pistons, récords, forma, h2h, clasificación | `GET /nba/v1/partido/{id}/estadisticas` y `/nba/v1/cartelera?fecha=` (§7.2) |
| NBA: probabilidades 62/38, props (cuotas, casas, últimas 5), disponibilidad (1 y 2 jugadores, 12 y 31 min) | **Ejemplo.** Reales: mercados `player_*` y `/nba/v1/partido/{id}/mercados` cuando el partido está sellado; disponibilidad en `event.availability` (ver `SportAlerts`) |
| Tenis: Fritz–Tirante, forma, superficies, mercados del modelo | `GET /web/deportes/tenis` (`markets[]`) y `GET /web/deportes/tenis/estadisticas/{id}` (§7.3) |
| Cuotas y casas (FanDuel, Pinnacle, BetMGM…), horas de cuota | **Ejemplo** en el render; reales vía `sports_quotes.dart` / mercados con `price` y `reference` |
| Logos NBA | `frontend/imagenes/nba/{SIGLA}.png` servido como `/web/imagenes/nba/{SIGLA}.png` |
| Retratos NBA | `/web/imagenes/jugadores/nba/{player_id}.png` |
| Fotos de futbolistas | `/web/imagenes/jugadores/futbol/{id}.png` (cada titular trae `foto`) |
| Fotos de tenistas | Hoy `/web/imagenes/tenis/{slug}.jpg` (manifiesto). Destino: SofaScore (fase 6/7) |
| VIP: precios $259/$549/$1,199, ahorros 29 %/61 %, anillo 76 %, barras 7 días, 27 picks, acierto por deporte | **Ejemplo.** Reales: `plans` del servidor + tienda + `vip_performance.dart` |
| Coins: 120 monedas, 40 por desbloqueo, +285/−240, movimientos | **Ejemplo.** Reales: `/mobile/v1/rewards` (+ ledger) |
| Avisos, novedades de actualización, versión 1.2.0 | **Ejemplo** |
| Guía: 75 %, 62 % vs 56 %, 80·75·70, escalones | **Ilustrativos fijos** (son parte del diseño) |

---

## 7. Contratos de datos (JSON reales, recortados) que alimentan las pantallas

### 7.1 Ficha de fútbol — `GET /web/partidos/{match_id}` (`src/qf/api/fichas.py`)
```
{ partido:{match_id,kickoff_utc,estado,liga{id,nombre},marcador,xg,estadisticas},
  local:{ id, nombre, escudo,
          forma:{ resumen:{G,E,P,gf,gc,puntos,racha,n},   // racha: ¡más reciente PRIMERO! ("GEEGE")
                  partidos:[{match_id,fecha,competicion,local(bool),rival,rival_escudo,gf,gc,res("G|E|P"),marcador,
                             xg:[a,b],tiros:[a,b],tiros_puerta:[a,b],corners:[a,b]}] },   // más reciente primero
          promedios:{ todos|casa|fuera:{ n,goles_favor,goles_contra,xg_favor,xg_contra,tiros_favor,tiros_contra,
                                         tiros_puerta_favor,corners_favor,corners_contra,
                                         pct_ambos_marcan,pct_mas_2_5,pct_porteria_cero } },
          ultimo_once:{ formacion, rival, fecha, titulares:[{nombre,pos("G|D|M|F"),numero,foto}] } | null,
          clasificacion:{ posicion,puntos,jugados,ganados,empatados,perdidos,goles_favor,goles_contra,forma } },
  visitante:{ …igual… },
  cara_a_cara:{ resumen:{n,victorias_local,empates,victorias_visitante,goles_media,pct_ambos_marcan,pct_mas_2_5},
                partidos:[{fecha,local(bool),rival,gf,gc,res,marcador,…}] },     // vistos desde el equipo local
  tabla:[{posicion,team_id,equipo,puntos,jugados,ganados,empatados,perdidos,goles_favor,goles_contra,
          forma("WDDWD" más reciente primero),escudo}],
  alineaciones:{ home|away:{formacion,titulares:[{nombre,pos,numero,foto}],capturada} },   // {} si no hay
  bajas:{ comprobada, home:[{jugador,tipo,motivo}], away:[…] } | null }
```
Trampas: `marcador` está en orden **local–visitante del partido**, no del equipo; usa `gf`/`gc` para el marcador «desde el equipo». `racha` y `forma` de la tabla vienen **más reciente primero**: invierte para dibujar de izquierda (antiguo) a derecha (último). `bajas.tipo` ∈ `injury`, `internationalDuty`, `suspension`, …; `motivo` es texto crudo en **inglés** («Early December 2026», «Doubtful», «Back in training»): hay que **traducirlo** (ver fase 7). `_bajas()` (en `src/qf/api/fichas.py`) **solo selecciona `side, player_name, status_type, reason`**: aunque la tabla `injuries` también guarda **`player_id`, `source`** (`api_football`/`fotmob`/`sofascore`) y **`expected_return`** (una `DATE` real), la API **no los devuelve**, y tampoco hay posición (saldría de `lineups`). Con eso el servidor puede dar foto y fecha de regreso exacta sin analizar el texto en inglés (fase 7a).

### 7.2 NBA — `GET /nba/v1/partido/{id}/estadisticas`
```
{ temporada:"2026-27", fecha, games_used,
  teams:[{ name, conference, season{won,lost,rate}, home{…}, away{…},
           scoring{games,points_for,points_against}, last6{won,lost,rate,games,points_for,points_against},
           streak(int, + = victorias), rest_days, back_to_back(bool), last_season{…},
           form:{ all:[{date,opponent,home(bool),points,opponent_points,won}] (reciente primero), home:[…], away:[…] },
           standing:{rank,of,conference} }],
  h2h:{ matches:[{date,home,away,home_points,away_points}], home_wins, away_wins, average_total } }
```
Cartelera: `GET /nba/v1/cartelera?fecha=YYYY-MM-DD` → `partidos[{id,fecha,local{codigo,nombre},visitante{codigo,nombre},inicio_utc,sello_previsto,resultado,pronostico}]`. Mercados: `GET /nba/v1/partido/{id}/mercados` → `{partido_id,markets[],projections[],destacado}`. **Si `markets` está vacío** (aún sin sello) la pestaña Pronóstico muestra el estado «sin pronóstico sellado» que ya existe (`detailNoSealedModel*`, `nbaSeal*`), y la probabilidad grande del hero se oculta o muestra «—».

### 7.3 Tenis — `GET /web/deportes/tenis` y `GET /web/deportes/tenis/estadisticas/{id}`
```
lista:  { sport,state,generated_at, events:[{ id,sport,home,away,start,league,surface("Hard|Clay|Grass"),sealed_at,seal,status,score,
                                              actionable, markets:[{id,label,selection,probability,price,reference,push_probability,outcome}], destacado }] }
        // markets.id: winner, tiebreak-N, games_total-N, games_handicap-N, sets_total-N, sets_handicap-N, set_winner-N
stats:  { state,generated_at,source,event_id,surface,circuit,
          players:[{ key,name,country,age,rank,points,movement("up|down"),
                     season{season,titles,won,lost,rate}, career{won,lost,rate},
                     surfaces:{ hard|clay|grass:{ career{won,lost,rate}, season{…} } },
                     ranking_history:[{season,rank,titles,won,lost,rate}],
                     form:{ matches:[{date,won,opponent,tournament,round,stage,qualification,score,sets,tiebreak,retired,complete}],
                            windows,streak,index,complete_matches,over_2_5_sets,tiebreaks,stages,qualification } }],
          h2h:{ first_wins, second_wins, matches:[…] } }
```
Trampa: el nombre de algunos jugadores viene invertido («Agustin Tirante Thiago»); usa el nombre del evento (`home`/`away`) para mostrar y el de `players[]` solo para datos. `estadisticas/{id}` devuelve 404 para partidos ya terminados: la pestaña Análisis muestra su estado vacío existente (`sportStatsUnavailable`).

---

## 8. Decisiones que siguen abiertas (pregunta al titular antes de cerrar la fase indicada)

| # | Pregunta | Fase | Mientras tanto |
|---|---|---|---|
| 1 | **Licencia de las fotos de SofaScore** (no son CC BY-SA; cambian los créditos). El titular ya decidió reemplazar, falta su confirmación para **subir y desplegar**. | 6/7 | Construir el cliente para que acepte cualquiera de las dos fuentes |
| 2 | Valores reales de la tabla **Gratis vs VIP** (10 % del día, «Parcial», 40 monedas por pick) | 5b | Leerlos de la configuración del servidor si existen; si no, preguntar |
| 3 | ¿Existe el **plan de 3 meses** en las tiendas? (el titular dice que hay 3 planes; el código ya soporta N planes) | 5b | Renderizar los que lleguen |
| 4 | **Escalera y Parley en NBA y tenis**, ¿desde ya o solo Alta prob.? ¿Un parley puede mezclar deportes? (el render muestra un parley mixto) | 3b | Respetar el catálogo del servidor (`knownSportStreams`) |
| 5 | Inicio de **NBA y tenis**: la lámina solo muestra fútbol; ¿se acepta la misma plantilla con datos de cada deporte? | 3a | Sí (por defecto) |
| 6 | Textos nuevos del render (etiquetas «GRATIS PARA EMPEZAR», «SIN TARJETA», `navPicks`, novedades de actualización) | 5 | Redactarlos como en el render y pedir visto bueno |
| 7 | **Foto o no** de futbolistas en bajas (derecho a la propia imagen). Solo hay foto para ids de `api_football` y `sofascore`; los de `fotmob` no tienen fuente de imágenes (`src/qf/api/imagenes.py`) | 7 | Mostrar iniciales hasta que el titular lo apruebe |

---

## 9. Riesgos y trampas conocidas

1. **Las pruebas de traducción son estrictas.** Un `Text('literal')` o una clave que falte en un idioma rompe `l10n_test.dart`. Añade cada texto con `tool/l10n_add.py` **antes** de usarlo.
2. **Contraste:** cualquier color nuevo de texto debe pasar `contrastRatio ≥ 4,5` en los tres fondos (`qf_theme_test.dart`). `slate` y `track` **no** son para texto.
3. **A 360 dp** no puede haber etiquetas recortadas (hay pruebas por idioma en `product_navigation_test.dart`). Las cadenas alemanas y francesas son las más largas: usa `FittedBox`/elipsis solo donde el render lo hace, y prueba en `de`.
4. **Rendimiento:** `ImageFiltered`/`BackdropFilter` y muchos `CustomPainter` en listas largas pueden costar fotogramas. Envuelve los painters estáticos en `RepaintBoundary`, no animes brillos, y limita el blur a elementos bloqueados visibles.
5. **`InkWell` con `CutCornerBorder`:** pasa siempre `customBorder: shape` o la onda se sale de la forma (ya lo hace `QfCard`).
6. **Datos que pueden faltar** (el render muestra el caso feliz): sin foto → iniciales; sin posición → se omite; sin once → tarjeta vacía; sin estadísticas → mensaje neutro; sin cuota → «—»; sin línea → «EN REVISIÓN». Cada pieza nueva debe tener su estado vacío probado.
7. **No rompas pruebas existentes por claves**: `ValueKey('unlock-confirm')`, `vip-plan-best`, `vip-plan-$index`, `sport-<id>`, `first-language-<code>`, `consent` están referenciadas por pruebas. Conserva las claves o actualiza las pruebas **en el mismo cambio**.
8. **Fuentes:** los `.ttf` deben ser OFL y llevar su texto de licencia. No uses `google_fonts` (descarga en ejecución); empaquétalas.
9. **Imágenes del render:** son de ejemplo. En la app vienen del servidor con **iniciales de respaldo**; **nunca** muestres la foto de otra persona si el id de fuente no coincide (ver `imagenes.py`: los ids de SofaScore **no** son los de API-Football).
10. **Pantallas heredadas** (`sign_in/`, `forget_password/`, …) siguen importando `Gilroy` y `utils/color.dart`: no las toques ni borres esas fuentes.
11. El render es una **maqueta HTML**: respeta números, jerarquía y comportamiento, no copies la estructura DOM.

---

## 10. Cómo verificar que «quedó como el render»

Para cada pantalla: (1) captura del emulador a **390×844** y a **360×800**; (2) ponla junto a `capturas/<lámina>.png`; (3) revisa **espaciados, tamaños, color, tipografía, estados** (vacío, cargando, error, bloqueado, desbloqueado, con y sin imagen); (4) `flutter analyze`, `flutter test` y el build **release** en `emulator-5556`; (5) ejecuta la app en `es` y `de`. El detalle de criterios de aceptación por fase está en [PLAN_REDISENO_FASES_20261114.md](PLAN_REDISENO_FASES_20261114.md).
