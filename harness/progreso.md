> Recortado el 2026-11-10: aquí solo las decisiones desde el 1-nov-2026. El diario completo está en
> `harness/archivo/progreso_hasta_20261110.md` (consúltalo con `grep` solo si necesitas historia anterior).

## 12-nov-2026 · Diseño de la Fase 1 del menú «Web y App»: reglas de acceso versionadas y lista blanca (rama `plan/menu-web-y-app`, solo diseño)

- **Por qué las reglas van versionadas por fecha de lote y no como un valor editable:** al leer `api/mobile.py` resultó que las constantes actúan hacia atrás. `top_up()` y `cap_free()` recalculan en cada lectura el cupo gratis de los lotes de los últimos 7 días, y `markets_history()` filtra todo el historial con el rango vigente. Con un control en el panel, estrechar el rango ocultaría a posteriori pronósticos sellados que fallaron: justo lo que el producto promete no hacer. La tabla `acceso_reglas` solo se añade y un trigger impide fechar una regla en hoy o antes; como `batch_date` es la fecha UTC de la decisión, ninguna regla puede alcanzar un lote ya sellado.
- **Por qué no se guarda la regla en cada lote:** con inserción solo hacia el futuro, la regla de cualquier lote existente ya es inmutable y se deduce de su fecha; una columna extra en `mobile_allocation_batches` no añadiría garantía.
- **Por qué el endpoint nuevo nace como `contrato: 0` y sin clientes:** la forma definitiva es la decisión de la Fase 2 y queda congelada en la app publicada. En la Fase 1 solo se asienta la maquinaria (lista blanca, `ETag`); `/web/config` y `/mobile/v1/config` no se reescriben.
- **Por qué una prueba de clasificación de columnas:** la fuga probable no es la de hoy, sino una columna privada añadida más adelante a una tabla que el endpoint ya lee. La prueba falla hasta que alguien la declare pública o privada.
- **Corrección a lo dicho el 11-nov:** la Fase 1 sí depende en una parte del titular: las reglas editables esperan su respuesta. Menú y endpoint, no.

## 11-nov-2026 · Plan del menú «Web y App»: configuración compartida para web y Flutter (rama `plan/menu-web-y-app`, solo plan)

- **Por qué un catálogo en el servidor y no más interruptores:** lo que hoy obliga a publicar la app no son los textos ni los avisos (eso ya se edita en `/control`), sino que deportes y mercados están escritos en el código de cada cliente (`enum SportKind` en `sports.dart`, expresiones regulares por deporte en `rutas.js`) y que cada deporte tiene un contrato distinto. Mientras eso siga así, un deporte nuevo exige versión de tienda por mucho panel que haya.
- **Por qué adaptadores y no reescribir los endpoints:** NBA lo sirve un servicio aparte (`apps/nba`) y fútbol y tenis tienen clientes instalados que dependen de la forma actual. El contrato común se monta encima y los endpoints viejos quedan como alias; así las versiones ya instaladas no se rompen y la actualización obligatoria no hace falta para esto.
- **Por qué bloques con tipos cerrados y no interfaz libre desde el servidor:** el CSS anterior es obligatorio y las tiendas no permiten código descargado. Cada tipo de bloque corresponde a un componente que ya existe; el servidor decide cuáles, en qué orden y con qué datos, y un tipo desconocido se ignora.
- **Límite fijado en el plan:** el panel gobierna presentación; no toca el orden `predecir → sellar → publicar` ni asignaciones gratis ya hechas. `fr/it/de` siguen bloqueados en la web (F7); los 6 idiomas solo aplican a textos de la app.
- **Por qué cada tarea lleva modelo y esfuerzo:** el titular pidió ahorrar tokens. Solo piden Fable 5.2 alto las decisiones que quedan congeladas en versiones instaladas de la app (forma del endpoint y catálogo, contrato por deporte, bloques) o que tocan las asignaciones gratis, más la revisión de seguridad del endpoint público. Esas sesiones dejan la especificación escrita en `tareas.md` para que la ejecución, con modelos más baratos, no tenga que explorar ni decidir.
- Detalle por fases y decisiones que esperan al titular: `harness/tareas.md`, sección del 11-nov.

## 11-nov-2026 · Páginas informativas y legales dentro del shell de la app (rama `web/paginas-info-en-shell`, sin desplegar)

- **Decisión del titular:** Metodología, Juego responsable, Sobre nosotros, Términos y Privacidad (y Eliminar cuenta) tenían maqueta propia (fondo claro u oscuro distinto, otro menú y otro pie). Ahora se sirven con el mismo `index.html` que NBA, fútbol y tenis (`rutas_web.render_pagina`): mismo encabezado, selector de deportes, menú principal y pie global. En ES, EN y PT.
- **Cómo:** el servidor deja el texto en `[data-info-contenido]` y `<html data-pagina="info">`; la app (`frontend/app.js`) guarda ese HTML y lo pinta en su `<main>` con la ruta `info` (`rutas.js` → `INFO_PATHS`, para que atrás/adelante funcionen). Estilos del texto acotados a `.qf-info` en `conversion.css`; las cuatro hojas originales no se tocaron.
- **Costes asumidos:** (1) estas páginas ya no son HTML sin JS: ahora cargan el módulo de la app y, tras el consentimiento, el Pixel, igual que NBA; la CSP pasó de cerrada a solo `frame-ancestors 'none'` (`paginas.CSP_SHELL`, `legal._CSP`); `tests/test_legal.py` ya no exige «sin scripts». (2) Cabecera `og:title` y `<title>` llevan « | QuantFut» (como NBA). (3) Los enlaces de idioma quedan en el HTML inicial para rastreadores; en pantalla los pone el selector del pie.
- **Ampliado el mismo día a Calibración, Cuota justa y Verificación (ES/EN/PT):** `paginas.envolver()` es el único punto que las pasa al shell. La app guarda el NODO del contenido (no su texto) y lo recoloca en cada repintado, así las herramientas conservan escuchas y lo escrito; el servidor deja `data-modulo` y la app importa `/static/cuota-justa.js` o `verificar-cadena.js` una vez pintado el contenido. Sus `<style>` pasaron a `conversion.css` acotados a `.qf-info` (antes `input,select` eran globales).
- **Fallos previos en `main` sin relación: `test_hashchain_*` (5) y `test_partido_final_en_ingles_*` (2).

## 11-nov-2026 · Respaldo SportsAPIPro para liquidación de tenis, cierre inmediato de tickets perdidos y protección anti-void (rama `fix/tenis-respaldo-liquidacion`, sin desplegar)

- **Diagnóstico en producción (`parley-v2`):** PropLine pasaba partidos Challenger/ITF en `/v1/sports/tennis/scores` a `expired` entre lecturas de 3 h sin emitir `/results`, dejando patas pendientes de tenis hasta el margen de 72 h (`parley-v2-liquidacion` además corría cada 3 h y `parley_v2_liquidacion.liquidar_ticket` esperaba a todas las patas incluso con una ya perdida).
- **Respaldo bajo demanda (`src/qf/ingest/tenis_resultados.py`):** consulta `/v2/tennis/schedule/{fecha}` de SportsAPIPro solo si PropLine no calificó y pasaron ≥ 2 h 30 min desde el inicio programado (0 peticiones sin patas vencidas), leyendo primero caché local archivada (`sportsapipro_tenis_resultados` y opcionalmente `TENIS_EQUIVALENCIAS_DIR`) con enfriamiento de 45 min por fecha, tolerancia ±36 h para aplazamientos y tope de 15 req/día. Liquida `Ended` (`h2h`, `total_games`, `handicap_games`, ignorando supertiebreaks a 10 pts > 7 juegos) y `Walkover`/`Canceled` -> `void`, sin adivinar retiradas (`Retired` -> `None`).
- **Parley v2 (`src/qf/publish/parley_v2_liquidacion.py`) y Escalera (`src/qf/publish/escalera_ext.py`, `escalera_datos.py`):** integrados con el respaldo (`fuente='sportsapipro'` en `parley_v2_resultados_pata`; `escalera_ext.sin_filas_de_resultado` ya no alarma falsos missing si el respaldo confirmó `void`). En Parley v2, cualquier pata `loss` cierra de inmediato el ticket como `perdido` (`factor_pago=0.0`), y pasadas 72 h sin calificación en ninguna fuente ya NO anula silenciosamente: deja `None` y alerta por Telegram.
- **Cadencia PropLine (`scripts/propline_shared_config.json`, `scripts/crontab`):** `scores_every_hours` `3 -> 1`, `settlement.min_hours_after_start` `6 -> 3`, y liquidación horaria en `scripts/crontab` (`20 * * * *`). Quedan pendientes los despliegues en VPS y el cierre retroactivo tras visto bueno explícito.

## 11-nov-2026 · Despliegue en producción de `/control/configuracion`, textos web en Postgres e integración APIMart (`quantfut-api:f73f7df2`, `DEPLOYS.md`)

- Construida en el servidor desde `git archive origin/main` (`f73f7df2`) la imagen `quantfut-api:f73f7df2` (`e1fe95deeb03`), ensayada en aislado (`292` rutas, `0` errores de módulo, `tenis.sellado: OK`) y desplegada recreando únicamente `api` a las `21:05:29 UTC` (`compose` anterior respaldado en `releases/compose-antes-20261111-210458.yml`).
- Aplicada `db/110_web_config.sql` en PostgreSQL preservando explícitamente `lang_states = {"en": "preview", "pt": "off"}` en `web_site_settings` para no alterar la visibilidad previa de `activos.txt` (`en=preview`), con `web_page_contents` sembrada (`es=22`, `en=10`, `pt=10`) y textos en UTF-8 comprobados en `/web/config`. `QF_SECRETS_KEY` ya existe en `.env`; la clave compartida en chat no se subió ni se escribió en el VPS pendiente de rotación por el titular.

## 10-nov-2026 · Auditoría de `README.md`, alineación de `Caddyfile`, arnés en worktrees y limpieza de `tareas.md`/`PENDIENTES.md` (rama `seo/f63-calibracion-calculadora`)

- **`Caddyfile` del repo alineado con producción F2.1:** F2.1 quitó `handle @nba { redir * /nba/v2/ 302 }` y añadió `header X-Robots-Tag noindex` en `@nba_v2` directamente en el servidor (`DEPLOYS.md`, 9-nov 01:26 UTC), dejando pendiente alinear el repo (`docs/plan_despliegue_nba_f21_20261108.md` §3). Sin este ajuste, recrear Caddy desde el repositorio devolvería 302 en todas las páginas públicas `/nba/*`.
- **Auditoría de `README.md` (`PENDIENTES.md`):** actualizadas las secciones operativas de cabecera, fases, cron (`scripts/crontab`: `daily` 09:00 UTC, entrenamiento local en vez del cron del VPS, cascada de respaldo y `parley_v2`/`escalera`), pagos (`Whop` + `Google Play`), APIs y estructura (`db/001..109`, `apps/tenis/`, `apps/mobile/`) conservando las secciones históricas fechadas.
- **`scripts/test_local_windows.ps1` en worktrees:** cuando no existe `.venv\Lib\site-packages` en el worktree, resuelve el directorio común de git (`git rev-parse --git-common-dir`) para localizar el `.venv` del repo principal sin copiar ni modificar el entorno, exige `import ctypes, ssl` al probar candidatos de Python 3.12 (evitando caer en un `.venv\Scripts\python.exe` con `_ctypes`/`_ssl` rotos) e incluye `apps/tenis/src` en `sys.path` para que `qf.api.main` resuelva `tenis.sellado`.
- **Limpieza de `harness/tareas.md`:** marcados como `[x]` los hitos de diseño/planificación (F2.2, D5–D8, F3.3 y desglose F2–F8) ya completados en commits posteriores dentro del mismo archivo, dejando intactos los bloqueos reales (revisión legal F7, muestras estadísticas, fechas ~16-nov / ene-2027, 7 worktrees del titular y mejoras de app separadas).

## 10-nov-2026 · Cierre técnico seguro de fases restantes: F5 (`modulepreload`), §7 (`contactPoint`), F8 verificador público y checklist legal F7 (rama `seo/f63-calibracion-calculadora`, sin desplegar)

- Alcance ejecutado: tras F6.3, se completan exclusivamente las entregas de código seguras sin saltar bloqueos de calendario ni requisitos jurídicos:
  - **F5 `modulepreload` (`frontend/index.html`):** se precargan los 15 módulos ES estáticos alcanzables desde `app.js` con sus `?v=` exactos (`rutas_web._RELATIVOS` y `frontend/server.mjs` reescriben `./` a `/` en subrutas) sin tocar ninguna hoja CSS ni `original-css.test.mjs`. Se añade prueba de sincronización 1:1 en `frontend/rutas.test.mjs` y comprobación de rutas absolutas en `tests/test_rutas_web.py`.
  - **§7 `Organization.contactPoint` (`src/qf/api/rutas_web.py`):** se añade `ContactPoint` (`customer support`, `admin@pronosticosdeportivos.pro`) al JSON-LD de portada; no se inventa `sameAs`.
  - **F8 verificador público (`scripts/verificar_cadena_publica.py` + `tests/test_f8_cadena_publica.py`):** script en Python estándar puro que valida `/chain` y directorios de recibos `*.receipt.json` + `.json` revelados con la misma regla `sha256(prev_sha256 + payload_sha256)` que `hashchain.py`.
  - **F8 / §2 página `/verificacion/` (`src/qf/api/verificacion.py`, `static/verificar-cadena.js`, `/en/verification/`, `/pt/verificacao/`):** auditoría SSR desde `prediction_batches` (sin fabricar datos cuando no hay base) más verificador interactivo en navegador con Web Crypto SHA-256 y CSP estricta (`script-src 'self'`, `connect-src 'self'`), enlazada desde navegación y metodologías sin alterar la declaración honesta sobre ausencia de testigo externo (`docs/plan_despliegue_verificacion_f8_20261110.md`).
- Bloqueos respetados sin forzar cambios riesgosos:
  - **F5 CSP coercitiva:** se mantiene `Content-Security-Policy-Report-Only` hasta acumular ≥ 7 días de informes desde el 9-nov (~16-nov-2026) según `docs/plan_despliegue_csp_f5_20261109.md`.
  - **F7 (`fr`, `it`, `de`):** bloqueado por revisión legal previa (`docs/plan_seo_redes_web_20261108.md` §11/§14). Se documenta la lista de decisiones jurídicas en `docs/revision_legal_f7_20261110.md` sin publicar código ni traducir páginas legales no aprobadas.
  - **F5/F6/F8 externos:** regla caché en Cloudflare, revisión humana `en`/`pt-BR` + red de ayuda Brasil, usuarios sociales reales, Search Console y Blogabet/Betstamp dependen del titular.

## 10-nov-2026 · F6.3 calibración y calculadora de cuota/odd justa en inglés y portugués (rama `seo/f63-calibracion-calculadora`, sin desplegar)

- Alcance: cierra todo el código pendiente de F6 añadiendo `/en/calibration/`, `/pt/calibracao/`, `/en/fair-odds-calculator/` y `/pt/calculadora-odd-justa/` (con 301 sin barra, puerta `off`/`preview`/`on`, `hreflang` recíproco `es`/`en`/`pt` + `x-default` en `/sitemap-paginas.xml` y selector de idiomas).
- Decisiones de diseño: se reutiliza un único módulo `static/cuota-justa.js` leyendo `<html lang>` (`document.documentElement.lang`) sin scripts en línea (`paginas.CSP`: `script-src 'self'`, sin `connect-src`) y manteniendo los formatos españoles por defecto al importar desde pruebas o fuera de navegador. En calibración se mantiene la derivación estricta de cifras desde `datos_calibracion` / base de datos y la traducción de `estado_evidencia` (`descriptive`/`descritiva`) y formatos locales (`0.2091` / `3,222` en EN; `0,2091` / `3.222` en PT).
- Navegación y cruce interno: `base_en.html`, `base_pt.html`, `en_methodology.html` y `pt_metodologia.html` enlazan directamente a sus versiones locales de calibración y calculadora; los enlaces a `/historial/` y `/legal/*` conservan `hreflang="es" lang="es"`.
- Bloques que siguen pendientes de aprobación/acción externa: F5 parte 2 (logs CSP hasta ~16-nov, regla Cloudflare y permiso explícito para `modulepreload` en `frontend/index.html`), F7 (`fr`/`it`/`de`, requiere revisión legal por Decreto Dignità / ANJ / GlüStV 2021) y F8 (autoridad externa / cuentas sociales).

## 10-nov-2026 · Reto escalera: anular y reemplazar escalones aplazados/nulos tras 6 h (PR #349 `e4552578`; desplegada 2026-11-11 02:34 UTC)

- Alcance aclarado con el titular: solo aplica a **Reto Escalera** (`/reto-escalera/`), no al Parley del Día. Para no tocar Parley ni
  `tarjetas_seg`, `escalera_datos.MARGEN_APLAZADO` (48 h) permanece intacto y la escalera usa `ESCALERA_MARGEN_APLAZADO = 6 h` (fútbol) y
  `escalera_ext.MARGEN_SIN_RESULTADO = 6 h` (NBA/tenis). Además `escalera_pasos.kickoff_utc` (`db/108_escalera_reemplazo.sql`) congela
  la hora original del partido de fútbol para que una reprogramación en `matches` no eluda el corte de 6 h.
- Inmutabilidad y sellado intradía: las filas `'void'` y los lotes ya sellados nunca se borran ni mutan (`deny_mutation`). Cuando un
  escalón queda `'void'`, `informe_publico()` (y `conversion-views.js` como respaldo en UI) lo ocultan en los retos vivos (`actuales`) y
  lo conservan en `historial`; el reemplazo (`reemplazar_nulos()`, cron cada 5 min en `scripts/crontab`) elige un nuevo partido elegible
  y lo sella al instante con `batch_kind = 'escalera'` y `match_id = paso_id::text` (`hashchain.seal_escalera`).
- Validación y despliegue real: en CI (`arnes`, PostgreSQL 16) se corrigió el tipado explícito del parámetro `$19` (`kickoff_utc`) en
  `escalera_datos._insertar_paso` (`f9a7f198`) pasando los 12 checks. Fusionado a `main` (`e4552578`) y desplegado en producción el
  `2026-11-11 02:34 UTC` (`DEPLOYS.md`); la primera pasada del cron (`02:35 UTC`) reemplazó el paso 2 `'void'` del Reto #21 con `tenis:726965`.

## 10-nov-2026 · Escalera con hándicap y total de NBA y tenis, y sin depender del fútbol (rama `escalera/mercados-nba-tenis-desacoplada`, sin desplegar)

- Decisión del titular: cuenta como cobrable la mejor cuota de TODAS las casas del archivo (ya sin casas de fantasía ni intercambios
  marcados) y la escalera deja de depender del fútbol. Medición que lo respalda: `docs/mercados_nuevos_medicion_20261110.md`.
- Por qué líneas alternativas: la línea principal rara vez llega a p ≥ 0,69; con la foto horaria de hoy el ensayo en el VPS pasó de
  26 candidatos válidos (1 de NBA) a 188 en 46 partidos, 20 de ellos solo por los mercados nuevos. Solo líneas .5 y probabilidad por
  consenso (`referencia.probabilidades`), como el parley v2; el ganador sigue con Pinnacle.
- Tenis se guarda como `total_games`/`handicap_games` (la app ya los traduce) y NBA como `totals`/`spreads`; el texto web sale en puntos o juegos.
  Liquidación por línea exacta y nombre tolerante (casas escriben distinto un equipo); si ni la casa del escalón ni Pinnacle califican y las
  demás coinciden, vale esa. Props de jugador no entran: ninguno llega a p ≥ 0,69.
- Sin predicciones de fútbol (9 y 10-nov), `daily.run` ya no sale antes de la escalera: la elige y, si hay escalón, sella el lote del día
  (`hashchain.seal` admite cero predicciones cuando el lote lleva escalones). Elegir antes de sellar se mantiene. Arreglado de paso
  `_alerta_sin_sellar`, que miraba una clave `paso` que no existe (nunca avisaba).
- No hecho: totales de equipo de NBA (cumplen en la medición, pero el archivo compartido solo los entrega por otro camino) ni calibración
  (Beta/Venn-Abers no mejoran al mercado).

## 9-nov-2026 · Ligas nuevas de SofaScore: carga, entrenamiento y backtest (rama `futbol/ligas-nuevas`, sin desplegar)

- Subidas al VPS 54.399 partidos (6 conexiones) y cargadas en `futbol.dato` las 11 competiciones nuevas. Las copas necesitan el
  snapshot con los equipos de todas las ligas y el calendario `last_*` (MLS y copas no tienen `round_*`).
- Decisión: criterios de aprobación fijados antes de medir (docstring de `backtest_ligas_nuevas.py`) y decide la variante `pit`
  (xG solo desde su recepción real). Aprueban Turquía, LaLiga 2, Serie B y Allsvenskan; Noruega y Suiza quedan en observación
  (C3 por 0,003); Championship y 2. Bundesliga no mejoran a la frecuencia. El hueco permanente de xG de Serie B/LaLiga 2 no daña.
- Hallazgo ajeno a las ligas nuevas: el Dixon-Coles crudo subestima goles (−0,10 a −0,29 por partido en 11 de 21 competiciones),
  y `over`/`ambos marcan` salen 3-9 puntos bajos. Pendiente de tarea propia antes de mostrarlos como alta probabilidad.
- Publicadas el mismo día, con el visto bueno del titular: db/105, db/106 y db/107 (alias de PropLine que faltaban: sin ellos el
  Fenerbahçe y el Malmö no tenían partidos), modelo `2026.11.09-063559` activo. Registro y vuelta atrás en DEPLOYS.md. Primeros
  pronósticos: job diario de 09:00 UTC del MISMO día de cada partido (LaLiga 2 desde el 13-nov; Turquía, Allsvenskan y Suiza desde el 21-nov; corregido el 9-nov: antes decía 10-nov). Pendiente: scraper SofaScore del VPS para las 4 ligas.
- Backtest de mercados completado para las 21 competiciones y con «Gana a cero» (`backtest_mercados regenerar`): no cambia ninguna conclusión; hallazgo nuevo,
  la primera mitad sobrepromete 5-6 puntos en alta probabilidad en Liga MX y Champions (hoy publicadas) y 3 en LaLiga 2 y 2. Bundesliga. El titular
  (9-nov) aplicó el tope del 85 % (PR #324, desplegado) y, sobre Liga MX y Champions, decidió SOLO INFORMAR: no se excluye la 1ª mitad en ellas. Su exceso
  está entre 0,75 y 0,85 (Liga MX +8,5 en 0,80-0,85; Champions +9,6 en esa franja y +5,5 en 0,75-0,80), la proporción de goles del 1T no cambió
  (44,3 % en 2019-22, 44,5 % desde 2025-07), así que la causa no es esa. Si se reabre: probar recalibración por liga o el exceso de 0-0 en el 1T.
- Sesgo de goles del Dixon-Coles: DECISIÓN DEL TITULAR (9-nov): dejar la corrección APAGADA. Se midieron dos candidatos con criterios fijados antes
  (A en muestra, B fuera de muestra) y ninguno cumple N1; el beneficio en Brier es ≈ 0 y la causa dominante es un cambio de régimen (arranque
  2026/27: +0,3 goles por partido), no un sesgo estructural. `DC_NIVEL_HALFLIFE_DAYS = 0`. Para no reabrirlo sin datos nuevos: si el sesgo
  ago-nov se normaliza solo, el problema desaparece; si persiste meses, reevaluar con otra ventana. Detalle: docs/correccion_nivel_goles_20261109.md.

﻿# Registro de decisiones â€” QuantFut

## 2026-11-06 Â· Parley v2.1: tope por mercado, cuatro targets a la vez y Â«solo referenciaÂ» sin calibraciÃ³n

El usuario pidiÃ³ un selector de parleys por targets (2.10, 3.10, 8.20, 12.10), mÃ­nimo de patas y sin +EV. Lo que
decide el diseÃ±o no es el prompt sino lo medido (`docs/parley_topes_medicion_20261106.md`): a cuota total fija
la probabilidad conjunta es casi la misma con 3 o 4 patas (P â‰ˆ (1 âˆ’ margen) / cuota), asÃ­ que menos patas compra
cobertura y menos margen acumulado, no acierto; el salto Ãºtil es de tope 2.0 a 2.5 y 3.0 aÃ±ade poco, mientras
que por encima de 2.1 los goles y los props de jugador se calibran peor y cuestan 3-4 puntos mÃ¡s por pata. Por eso
2.50 solo para ganador, 2.10 para lÃ­neas, 1.80 para lo no medido y el 1T 1X2 fuera (margen 9-11 %). Los cuatro
tickets se resuelven a la vez: con el orden secuencial, el 12.10 se quedaba con lo que dejaban los demÃ¡s.

`publicado` exige probabilidad calibrada con incertidumbre en cada pata; sin artefacto de calibraciÃ³n (fase 2) todo
sale `solo_referencia`, y un same-game solo es ejecutable con cuota real del paquete y modelo conjunto (la
correlaciÃ³n medida llega a 1,45-1,59 sobre el producto de marginales). El mÃ³dulo no estÃ¡ enganchado al sellado:
el lote propio de las 03:35 invierte predecir â†’ seleccionar â†’ sellar y exige confirmaciÃ³n expresa. Lecciones: la
prueba contra bÃºsqueda exhaustiva cazÃ³ un fallo real (dos opciones de un mismo conjunto de eventos se pisaban
al deduplicar), y el BOM de football-data dejaba sin id al 19 % de los partidos, lo que subestimÃ³ la cobertura del
fÃºtbol en la primera mediciÃ³n (corregido y documentado).

Mismo dÃ­a, a pedido del usuario: Pinnacle deja de ser obligatorio para la probabilidad de referencia en todos los
deportes y mercados del parley. `publish/referencia.py` usa el consenso de las casas que cotizan el contrato
completo (Pinnacle conserva su peso si cotiza; mÃ­nimo 2 casas). Se aplicÃ³ a tenis/NBA (`parley_ext.py`) y al
fÃºtbol mediante un parÃ¡metro `consenso` que solo activa `PARLEY_STRATEGY_VERSION=v2`, para no mover alta
probabilidad, escalera ni el parley legado, cuyos controles se midieron con Pinnacle. El efecto sobre las
probabilidades sin Pinnacle no estÃ¡ medido todavÃ­a: va antes de activar v2.

DespuÃ©s, a pedido de Â«termina los pendientesÂ»: fase 2 (calibraciÃ³n y backtest), fase 3 (lote propio con cadena de hashes, barrera
y reintentos, apagado) y fase 4 (parley NBA por partido, lÃ³gica pura). La decisiÃ³n clave de la fase 2 es negativa: en fÃºtbol y tenis
el mercado sin margen ya estÃ¡ calibrado, Platt e isotÃ³nica no lo mejoran con claridad y por eso B1/B2 no se promueven; lo que
sÃ­ aporta el artefacto es la abstenciÃ³n (NBA se abstuvo en las categorÃ­as de cuota alta de props) y la incertidumbre por pata. La
fase 3 se diseÃ±Ã³ para NO tocar `seal()` ni el cron diario: cadena propia que guarda el hash del lote diario como prueba de
orden, y todo apagado hasta confirmar. Un fallo real saliÃ³ del cierre: dos jugadores con el mismo prop y lÃ­nea se fundÃ­an en un
contrato al consolidar; el jugador ahora forma parte de la clave de la pata.

Cierre de pendientes: liquidaciÃ³n de patas v2 (fÃºtbol, tenis, NBA) y orquestaciÃ³n del parley NBA por partido. La prueba de la
liquidaciÃ³n destapÃ³ otro fallo: el id de evento de fÃºtbol (`liga:temporada:equipos:fecha`) se cortaba en el primer `:` al sellar,
lo que habrÃ­a impedido unir la pata con `matches`; ahora fÃºtbol conserva el `match_id` completo y tenis/NBA quitan su prefijo.
Lo que queda no es cÃ³digo: aprobaciÃ³n del artefacto, aplicar la migraciÃ³n 098, desplegar, el sellado diario NBA v1.3 con su
revisor y la disponibilidad en vivo.

## 5-nov-2026 (noche) Â· CalibraciÃ³n del destacado de fÃºtbol por mercado y banda; quÃ© regla cumple el 80 %

MediciÃ³n con 390 partidos terminados que tenÃ­an predicciÃ³n previa al saque (base local `entreno`, copia de producciÃ³n al 25-oct; del 27-sep al 25-oct), reconstruyendo las filas de la lista web (goles, equipo, hÃ¡ndicap, doble oportunidad, empate no acciÃ³n, 1Âª mitad, cÃ³rners y tarjetas) y liquidÃ¡ndolas con el resultado real (los empates devueltos no cuentan). 97 de esos partidos tienen cuota de casa (PropLine, desde el 23-oct). NBA y tenis NO se calibraron aquÃ­ (pendiente).

- **Valor esperado con cuota de casa** (cuota â‰¥ 1,20, prob â‰¥ 55 %, mayor prob Ã— cuota): **56,5 % de acierto** (n = 85, IC95 46â€“66 %), cuota media 1,80; con cuota del modelo es idÃ©ntico a la regla nueva. La cifra Â«31 %Â» del encargo no se pudo reproducir con este historial (su muestra viva fueron pocas horas).
- **Regla desplegada (â‰¥ 75 %, mayor prob., cuota â‰¥ 1,20):** 80,1 % (IC95 75,8â€“83,7 %, n = 386) con cuota del modelo y 78,0 % (IC95 68,5â€“85,3 %, n = 91) con cuota de casa; cuota media 1,23 / 1,29. EstÃ¡ calibrada (probabilidad predicha media 81,6 %), pero el techo de 83,3 % que impone la cuota â‰¥ 1,20 deja el 80 % justo en el borde: no lo garantiza.
- **La cuota mÃ­nima manda mÃ¡s que cualquier lista de mercados:** con â‰¥ 1,15 el acierto medido es 84,8 % (IC95 80,9â€“88,1 %, cuota media 1,18) y 83,2 % con casas; con â‰¥ 1,10, 84,9 % (cuota 1,14) y 85,6 % con casas. El 80 % se cumple con holgura bajando el mÃ­nimo de 1,20 a 1,15 (a costa de ~4 % de pago). Las casas pagan MENOS que la cuota justa en estas selecciones (media 1,205 frente a 1,233 justa; la mitad de los candidatos de â‰¥ 75 % paga < 1,20): Â«80 % de aciertoÂ» y Â«cuota competitivaÂ» chocan por construcciÃ³n (80 % â‰ˆ cuota justa 1,25).
- **Por mercado (franja 75â€“83,3 %, toda la muestra):** calibrados dentro del error: goles de equipo 79,1 %, hÃ¡ndicap 78,8 %, tarjetas 78,7 %, cÃ³rners 78,2 %, goles 77,4 %, 1Âª mitad 76,3 %, doble oportunidad 75,8 %, empate no acciÃ³n 82,2 % (n = 45). Por selecciÃ³n, los Â«menos deÂ»/Â«noÂ» estÃ¡n sobreestimados (totals:under âˆ’6,1 pts, ht_btts:no âˆ’6,1, team_totals_away:under âˆ’8,7; la lÃ­nea 3,5: 70,9 % real contra 78,9 % predicho) y los Â«mÃ¡s deÂ» subestimados (+2 a +7): el modelo subestima los goles de este periodo.
- **Lo que NO funcionÃ³ fuera de muestra:** listas blancas, probabilidad corregida por la brecha de su clave y excluir under/no. Las claves Â«segurasÂ» cambian de un tramo a otro (ruido con n de 25â€“100), y excluir under/no mejora con cuota del modelo (+3 pts) pero empeora con casas (âˆ’3 pts). No se aÃ±adiÃ³ ninguna lista de mercados.
- **RecomendaciÃ³n:** bajar `CUOTA_MIN` a 1,15 (constante en `destacado_valor.py`, su copia de NBA y `featured_rule.dart` / `bestBySafety` de web y app) si el 80 % es el objetivo duro; el siguiente paso de fondo es recalibrar el modelo de goles (under/no sobreestimados), no filtrar mercados.

## 5-nov-2026 (tarde) Â· Destacado: de valor esperado a Â«probabilidad mÃ¡xima seguraÂ»

DecisiÃ³n del titular, horas despuÃ©s de desplegar el valor esperado (PR #262): el destacado es un producto de retenciÃ³n, no de ROI; el objetivo es que el usuario vea >= 80 % de aciertos. Regla vigente en fÃºtbol, NBA, tenis, web y app: candidato = cuota de referencia >= 1,20 y probabilidad >= 75 %; gana la MAYOR probabilidad (la cuota ya no multiplica nada y `score_destacado` desaparece); empate -> mayor cuota; sin candidatos -> `null`. Sin cuota de casa la de referencia es 1 Ã· prob., asÃ­ que el destacado sale de la franja 75 %-83,3 %. Se conserva la regla de que, con cuotas de casa en el partido, solo compiten los mercados que una casa cotiza, y que el destacado es siempre uno de los 3 mercados gratis de la web.

AmbigÃ¼edad del encargo resuelta: el punto 1 pedÃ­a cuota >= 1,20 y el punto 4 decÃ­a Â«pagando 1.10Â»; se aplicÃ³ 1,20 (aparece dos veces y el propio encargo habla del tope de 83,3 %). Si se querÃ­a 1,10, el tope de la franja sube a 90,9 % sin cuota de casa: es un cambio de una constante (`CUOTA_MIN`).

QuÃ© NO estÃ¡ demostrado: la cifra Â«31 % de acierto empÃ­ricoÂ» del valor esperado y que la nueva regla llegue a 80 % se citaron sin mediciÃ³n propia. Un destacado sale de una franja estrecha (75 %-83,3 %), asÃ­ que 80 % real exige un modelo calibrado justo ahÃ­; la calibraciÃ³n por mercado e historial se mide aparte (ver la entrada de calibraciÃ³n).

## 5-nov-2026 Â· PronÃ³stico destacado por valor esperado en fÃºtbol, NBA y tenis (servidor)

DecisiÃ³n del titular: el destacado deja de ser Â«la mayor probabilidad con cuota â‰¥ 1,40Â» y pasa a ser el mercado de mayor `probabilidad Ã— cuota de referencia` entre los que tienen cuota â‰¥ 1,20 y probabilidad â‰¥ 55 %; empate por mayor probabilidad; sin candidatos, `null`. Lo implementa `src/qf/api/destacado_valor.py` (puro, sin dependencias), usado por `partido_mercados.aplicar_acceso_web` (fÃºtbol), `tenis_publico.read_public_feed` (campo `destacado` por evento) y la copia `apps/nba/src/nba/api/destacado_valor.py` en `/nba/v1/partido/{id}/mercados` (campo `destacado`). Pruebas: `tests/test_destacado_valor.py` y `apps/nba/tests/v2/test_destacado_valor_nba.py`, con el dilema 1,20/75 % contra 1,80/70 % (gana 1,80: 1,26 > 0,90).

Por quÃ© importa saberlo: con cuota del modelo (1 Ã· prob) el score vale 1 en todos los mercados, asÃ­ que sin cuota de casa la regla equivale a Â«la mayor probabilidad que aÃºn paga 1,20Â» (â‰¤ 83,3 %); el valor esperado solo discrimina con cuota real. Se compara con redondeo a 9 decimales para que el ruido de coma flotante no decida empates. Se conservÃ³ la regla del 2-nov de que, con cuotas de casa en el partido, solo cuentan los mercados cotizados por una casa. El destacado es siempre uno de los 3 mercados gratis de la web. `RANGO_DESTACADO` pasa a (1,20, null).

Web adaptada en la misma rama: `featuredSportMarket` (NBA y tenis) ya no calcula, solo localiza el mercado que manda el servidor en `destacado` (si es una revisiÃ³n posterior al inicio, queda sin destacado en vez de sustituirse); `loadNbaMarkets`/`withNbaMarkets` conservan su id; el cliente aplica la misma regla (`bestByValue`) solo si el servidor no manda el campo (fuente antigua o mercados aÃºn sin cargar). El Â«destacado del dÃ­aÂ» (`ergonomic-views`) usa tambiÃ©n `bestByValue`. Textos Â«cuota de 1,40â€¦Â» sustituidos por la regla nueva y versiones `?v=destacado-valor-20261105` para saltar la cachÃ© de Cloudflare. El historial de NBA/tenis se calcula en vivo con el destacado vigente, asÃ­ que la regla nueva tambiÃ©n cambia lo que enseÃ±a de partidos pasados (ya ocurrÃ­a con el cambio del 2-nov). App Flutter adaptada (misma rama, base `origin/main`, app 1.1.0+7): `featured_rule.dart` (`bestByValue`) sustituye la banda 74â€“85 % / cuota 1,20â€“1,60 de `featuredPick` (detalle del partido), el Â«Destacado del dÃ­aÂ» de fÃºtbol (`live_home`, ahora solo entre pronÃ³sticos abiertos y sin tarjeta si nadie cumple la regla) y `featuredMarket` de NBA/tenis, que respeta el campo `destacado` del servidor (`SportEvent.serverFeatured/featuredId`) y, sin Ã©l, aplica la regla con la cuota del modelo. Texto `detailNoFeatured` actualizado en los 6 idiomas. Ojo con las ramas: la regla Â«cuota â‰¥ 1,40, sin tope de probabilidadÂ» (commit f8c9ffd1, app 1.0.0+3, 25-oct) vive solo en `nba/v13-disponibilidad` y NUNCA llegÃ³ a `main`, que conserva la banda 74â€“85 %; esta rama parte de `main`, asÃ­ que sustituye la banda y deja sin efecto esa rama en este punto. No se subiÃ³ el cÃ³digo de versiÃ³n ni se compilÃ³ un AAB (hacerlo al publicar). Pendiente: los destacados ya congelados en `web_destacado` (hashchain) no cambian; sin desplegar (ver DEPLOYS.md) ni probado en navegador contra la API real. Base: `origin/main` 0097b767, rama `futbol/destacado-valor-esperado`.

## 5-nov-2026 Â· PronÃ³sticos de jugador NBA en Â«PendienteÂ»: faltaba el id de la NBA, no los crÃ©ditos

Los 14 partidos del 4-nov liquidaban los mercados de equipo y ninguno de jugador. La razÃ³n no era de crÃ©ditos ni de la
web: el marcador de cdn de las 10:00 ET trajo `games: []` con la fecha anterior, el colector lo dio por hecho durante
20 h y solo buscaba ids de hoy, asÃ­ que sin id de la NBA no sabÃ­a quÃ© box score pedir. DecisiÃ³n: reintentar el marcador
cada 55 min (tope 4 por ventana) mientras falten ids de ayer u hoy, en vez de fiarse de una sola lectura. El mismo dÃ­a
se aÃ±adiÃ³ SofaScore como respaldo automÃ¡tico de los box scores de jugador (fuente `sofascore` del colector, solo
partidos recientes, solo aÃ±ade filas, la caja oficial manda), pero depende de que el scraper del VPS pase el bloqueo
de SofaScore, que hoy no lo hace con la NBA (403 en la lista de temporadas): el cdn sigue siendo la vÃ­a principal.
Pendiente de decisiÃ³n: 66 mercados de 5 jugadores ausentes del box score (Jalen Johnson, Josh Hart, Jayson Tatum,
Trey Murphy, Jaylin Williams) siguen sin resultado; `resolver()` deja pendiente lo que no ve y no lo marca nulo.

## 4-nov-2026 Â· Publicadas las correcciones NBA; acreditaciÃ³n prospectiva condicionada a datos reales

Orden expresa de publicar. PR #255 integrado con arnÃ©s remoto verde (NBA con PostgreSQL, fÃºtbol/API, frontend y tenis), main `a491f225`. API concurrente de mercados preservada desde `61ff260`; sus probabilidades/Ãºltimas cuotas por lado se integraron con los contratos corregidos. CI detectÃ³ fixtures con fechas UTC en lugar de ET al cruzar medianoche y una ruta temporal sin permisos; se corrigieron las pruebas sin debilitar la lÃ³gica de producciÃ³n.

Publicados Ãºnicamente `nba-motor:auditoria-a491f225` y `nba-api:auditoria-a491f225`, con respaldo, migraciÃ³n 0009, ensayo lector y rollback. Un ensayo previo detectÃ³ directorios Docker sin lectura; se reconstruyÃ³ sin cachÃ© antes de sustituir. Cuatro rutas pÃºblicas 200, 153 archivos de API iguales a main, cadena de 1.541 sellos Ã­ntegra. Cron 00:30 UTC: 2.2, cero errores y primer pronÃ³stico de equipo sellado.

La cohorte y tolerancias se registraron antes de activar. No se acredita calibraciÃ³n con cero resultados ni se mezclan los de 2.0/2.1. Seguimiento por versiÃ³n activo; la candidata hÃ­brida permanece bloqueada. El artefacto actual vence el 7-nov-2026 13:18 CDMX y debe renovarse en local. Registro/rollback: DEPLOYS.md; evidencia y lÃ­mites: docs/nba_auditoria_correcciones.md.

## 4-nov-2026 Â· AuditorÃ­a NBA: correcciones y evidencia, promociÃ³n pendiente

La autorizaciÃ³n posterior del titular permite corregir el cÃ³digo auditado. Rama `codex/nba-auditoria-20261104`, sobre main vigente, preservando el checkout antiguo y la evidencia original. Las guardias temporales incluyen la recepciÃ³n del original: publicar un PDF antes del corte no prueba que el sistema lo hubiera recibido entonces. No se alteran filas inmutables para fingir esa disponibilidad.

El candidato 2.2 proyecta posesiones e infiere desde ratings congelados; no aprende resultados en el VPS. La ley separa regulaciÃ³n y OT y usa una CDF comÃºn para masas y cuantiles. Artefactos futuros/del dÃ­a objetivo/caducados se rechazan: publicar exige renovaciÃ³n local versionada, no entrenamiento en producciÃ³n. La web ya no afirma calibraciÃ³n sin evidencia y presenta versiÃ³n y log-loss en seis idiomas.

ValidaciÃ³n: 1.224 pruebas NBA aprobadas, 18 omitidas (17 de entrega legacy sin DSN especÃ­fico y un privilegio Windows); 94 regresiones finales y 4 pruebas nuevas de entrenamiento aprobadas. EvaluaciÃ³n retrospectiva de equipo: 1.235 partidos, Brier 0,20550, log-loss 0,59795, sin acreditar al hÃ­brido ni disponibilidad histÃ³rica original. SerializaciÃ³n 14,418 â†’ 0,0751 s. CI NBA incorpora PostgreSQL.

Se autorizÃ³ expresamente exportar cajas de jugadores mediante SELECT. La candidata de impacto de regulaciÃ³n sin RAPM empeorÃ³ Brier (0,21061 vs 0,20568; IC95 Î” positivo) y no se activa. Tampoco se traslada el impacto antiguo de finales a regulaciÃ³n sin validaciÃ³n. El motor conserva el nÃºcleo y exige evidencia para habilitar una mezcla. La confirmaciÃ³n posterior en 43 partidos de playoffs (Brier 0,20506) es descriptiva y no sirviÃ³ para elegir variante. 359 pruebas v2 con PostgreSQL aprobadas tras la puerta.

Ãšltima revalidaciÃ³n: 55/55 aprobadas, cero omitidas, incluyendo estrÃ©s completo, SQL PIT con equipos/fechas filtrados antes de resolver versiones, artefactos y API que identifica automÃ¡ticamente la versiÃ³n. El PostgreSQL desechable se detiene al terminar.

Sin despliegue, migraciones ni entrenamiento en VPS. PublicaciÃ³n del nÃºcleo, renovaciÃ³n local y certificaciÃ³n prospectiva pendientes. Detalle y vuelta atrÃ¡s: `docs/nba_auditoria_correcciones.md`; auditorÃ­a original conservada en `docs/nba_auditoria_reporte.md`.

## 3-nov-2026 Â· Las estadÃ­sticas de equipos de NBA las publica el servidor (API v2), no el navegador
La web resumÃ­a rÃ©cord, forma, cara a cara y clasificaciÃ³n en el navegador con ~26 peticiones de cartelera; solo veÃ­a desde el 20-oct (sin temporada pasada, cara a cara de dos semanas). **DecisiÃ³n:** `GET /nba/v1/partido/{id}/estadisticas` (`apps/nba/src/nba/api/estadisticas.py`, funciÃ³n pura + una consulta de solo lectura) devuelve el mismo contrato que ya consumÃ­a la web, calculado desde `nba.dato` (`puntos`, periodo 0, fase `final`, fuente por prioridad). **Reglas:** solo temporada regular (tabla `REGULAR` por temporada; sin pretemporada, play-in ni playoffs; una temporada sin fila usa 15-oct â†’ 13-abr y hay que aÃ±adirla antes de que empiece) y solo marcadores de fechas ANTERIORES a la del partido (un equipo no juega dos veces el mismo dÃ­a, asÃ­ que la fecha ET basta y no depende de la hora de inicio, que las temporadas viejas no tienen). Incluye `last_season` (temporada anterior completa) y un cara a cara de hasta 10 partidos de varias temporadas. Un partido de pretemporada responde 404 `sin_estadisticas` (traducido a los 6 idiomas en `static/i18n.json`). **Web:** `loadNba` pide solo 9 dÃ­as de cartelera (âˆ’4â€¦+4) y `loadNbaStats` pide el endpoint al abrir una pestaÃ±a de estadÃ­sticas; se borrÃ³ el cÃ¡lculo local. **Verificado contra la base real** (contenedor temporal de solo lectura con el rol `nba_api`): 52 partidos de 4 dÃ­as, todos 200, 0,11 s de media; cada equipo con 82 partidos de la temporada pasada (dedupe y filtro de regular correctos); estreno del 20-oct sin marcadores previos. **No desplegado:** exige reconstruir `nba-api` y la imagen del frontend (ver DEPLOYS.md); la ficha mostrarÃ¡ Â«TodavÃ­a no hay estadÃ­sticasÂ» hasta que el contenedor `nba-api` lleve el endpoint.

## 3-nov-2026 Â· La cartelera de NBA de la web lee la API v2 y explica cuÃ¡ndo llega el pronÃ³stico
Al retirarse la v1 de NBA (3-nov, 18:05 UTC) `/nba/api/data` pasÃ³ a redirigir (302) a `/nba/v2/` y la web (`sports-data.js`) y la app (`sports_feed.dart`) se quedaron sin fuente: Â«No se pudo cargar la fuenteÂ» y Â«Sin eventos este dÃ­aÂ». **DecisiÃ³n del titular:** solo v2; los pronÃ³sticos que la v1 ya habÃ­a publicado (hasta el 2-nov) no se recuperan en la web. `loadSport('nba')` pide `/nba/v1/cartelera?fecha=` desde el estreno de la temporada (20-oct, tope de 21 dÃ­as atrÃ¡s) hasta 4 dÃ­as adelante, y conserva los partidos sin pronÃ³stico: el pronÃ³stico ganador solo se muestra si viene sellado antes del inicio. Las estadÃ­sticas (rÃ©cord, forma, cara a cara, clasificaciÃ³n, descanso) se resumen en el navegador con los marcadores finales de la propia API, sin pretemporada y sin temporada pasada; el feed `nba_stats.json` no sirve porque se genera de las cohortes v1 congeladas. Tarjeta Â«CuÃ¡ndo se agrega el pronÃ³sticoÂ» en la ficha (hora de `sello_previsto`, 60 min antes del saque; distingue pendiente, sellado y sin pronÃ³stico previo, y nunca presenta uno a posteriori). **Pendiente:** la app mÃ³vil sigue leyendo `/nba/api/data`; el feed de estadÃ­sticas v2 en servidor; todavÃ­a no se despliega (rama `web/nba-cartelera-v2`, sin commit).


## 3-nov-2026 Â· Correcciones de auditorÃ­a: la evidencia previa decide el historial

Se guarda el destacado en la predicciÃ³n inmutable y se incluye en su sello; una fila reconstruida despuÃ©s del resultado deja de contar como pronÃ³stico publicado. Los lotes anteriores omiten el campo nuevo para conservar su forma. La migraciÃ³n 102 propaga capturas previas dentro de su transacciÃ³n, conserva su recepciÃ³n y aparta tiros incoherentes con copia Ã­ntegra en cuarentena; ensayo en Postgres aislado aprobado.

La nueva comparaciÃ³n A0/DC con la misma admisiÃ³n de xG reduce la diferencia a âˆ’0,001246 de log-loss en 5.541 partidos (IC95 cruza cero); en 475 de seguimiento A0 empeora +0,000304. No se promueve. Conteos sin simultÃ¡neos mantienen su orden frente a la media de liga. El nuevo A4 construyÃ³ 49.933 tramos de 7.138 partidos; sigue condicionado al once reconstruido y no demuestra mejora de acierto. La ausencia de evidencia no se convierte en parÃ¡metros de producciÃ³n. Suite corregida: 1.756 aprobadas, 122 omitidas. Detalle: `docs/correcciones_futbol_20261103.md`.

## 2-nov-2026 Â· Los escudos de una tarjeta terminada los manda el servidor, no la agenda
Al ver las tarjetas de fÃºtbol terminadas (PR #237) salÃ­an las iniciales en vez del escudo. **Causa:** los partidos terminados no estÃ¡n en la agenda del dÃ­a, que es de donde las tarjetas prÃ³ximas toman el escudo. **DecisiÃ³n:** que `destacados_resueltos` devuelva el escudo de cada equipo con la misma funciÃ³n que usa la agenda (`fichas.escudo`) en vez de buscar la ficha de cada partido desde el navegador (una peticiÃ³n por tarjeta) o de derivar la URL en el frontend (duplicarÃ­a la regla de dÃ³nde estÃ¡ cada imagen). Sin escudo descargado queda `None` y se mantienen las iniciales: no se inventa ninguna imagen.

## 2-nov-2026 Â· El destacado de la web se elige con la cuota de una casa, no con 1 Ã· probabilidad
El titular preguntÃ³ por quÃ© la tabla decÃ­a Â«Del modeloÂ» y pidiÃ³ dos cosas: que cada cuota diga de quÃ© casa es y que el destacado se elija con la cuota real. **DecisiÃ³n:** `partido_mercados.cuotas_casas` toma, de `odds_snapshots` (PropLine), la mejor cuota entre las casas de los suscriptores (`settings.soft_books`; Pinnacle y exchanges no son casas donde apostar) hasta el saque y con menos de 6 h, la misma regla de la escalera. **Por quÃ© Â«solo lo que cotiza una casaÂ» cuando el partido tiene cuotas:** el precio del modelo es una cuota justa sin margen; dejarlo competir con precios de casa (siempre algo menores) favorecÃ­a justo los mercados que ninguna casa cotiza (gana a cero, 1.Âª mitad). Sin ninguna cuota de casa en el partido (antes del 23-oct, liga sin PropLine) se conserva la del modelo y se etiqueta Â«Del modeloÂ». **Historial reproducible:** la cuota del partido terminado es la Ãºltima anterior al saque, asÃ­ que no cambia con el tiempo; `ref_price`/`ref_book` solo se rellenan si la cuota es de una casa. Medido en producciÃ³n (solo lectura): 213 destacados desde el 26-oct, 209 con casa (Bovada 115, Heritage 39, Jazz Sports 14â€¦), 70,4 % de acierto con la probabilidad media del modelo en 71,6 %; 2,8 s en recalcular todo (cachÃ© de 10 min). **A vigilar:** Bovada gana casi siempre por precio y es una casa que muchos suscriptores no pueden usar; si el titular quiere restringir las casas del destacado, es `settings.soft_books`.

## 2-nov-2026 Â· Los partidos de fÃºtbol terminados salen como tarjeta: el motivo era la fuente de la lista, no los datos
El titular preguntÃ³ por quÃ© no aparecÃ­an ni los terminados de hoy. **Causa:** la lista de tarjetas de fÃºtbol solo salÃ­a de los picks Â«prÃ³ximosÂ» (y de pago) de la portada; el servidor manda como prÃ³ximos Ãºnicamente los que no han empezado, asÃ­ que al empezar el partido su tarjeta desaparecÃ­a y quedaba solo en el panel de resultados (NBA y tenis salen de otra fuente que sÃ­ incluye terminados). **DecisiÃ³n:** construir las tarjetas terminadas desde el destacado resuelto de cada partido (`/markets/destacados`, ya cargado para el historial) en vez de pedir la ficha de cada uno o ampliar el payload de la portada; el destacado trae marcador y resultado, y no suma a Â«PublicadosÂ» porque no es un pick sellado. Probado con la respuesta real de producciÃ³n antes de desplegar.

## 2-nov-2026 Â· El destacado de la web sale de todas las opciones y `main` vuelve a ser el frontend de producciÃ³n
Orden del titular: resolver el aviso de que `main` no coincidÃ­a con producciÃ³n y que la tarjeta de fÃºtbol use todos los mercados y diga en la fecha si acertÃ³ o fallÃ³. **Por quÃ© la causa era una rama sin fusionar:** `web/destacado-en-tarjeta` se desplegÃ³ el 30-oct pero nunca se subiÃ³ a GitHub; fusionarla recuperÃ³ el frontend real y, de paso, el pie de pÃ¡gina y el estado AcertÃ³/FallÃ³ bajo el destacado que `main` tenÃ­a y producciÃ³n no. **Por quÃ© opciones complementarias solo en la web:** `filas_goles` listaba el lado mÃ¡s probable de cada mercado (la lista de la app), de modo que Â«Menos de 1,5Â» o los otros resultados del 1X2 no podÃ­an ser nunca el destacado; aÃ±adirlas en `construir(web=True)` cumple Â«todos los mercadosÂ» sin cambiar la lista ni los conteos de la app. CÃ³rners, tarjetas y 1.Âª mitad siguen con sus lÃ­neas validadas histÃ³ricamente. Efecto colateral: los destacados del historial pÃºblico se recalculan.

## 2-nov-2026 Â· Destacado de la web sin tope: se aplicÃ³ sobre el frontend real de producciÃ³n, no sobre el de main
Orden del titular: cuota mÃ­nima 1,40 y sin tope (antes 1,40-1,80). **Por quÃ© un parche archivo a archivo:** la comparaciÃ³n con el contenedor mostrÃ³ que el frontend en producciÃ³n lleva cambios del 30-oct (`app.js`, `ergonomic-views.js`) que `main` no tiene; copiar los archivos de `main` los habrÃ­a revertido. Se aplicÃ³ el diff del PR sobre las copias del contenedor (sin ambigÃ¼edad: una coincidencia por reemplazo) y se verificÃ³ por hash en el dominio real. El tope pasa a `None` (viaja como `null` en `rango`) en vez de infinito porque JSON no admite infinito.

## 2-nov-2026 Â· SharpAPI se captura como archivos y hacia adelante, no se carga en la base
El titular autorizÃ³ capturar SharpAPI para los mercados que PropLine no trae. **Por quÃ© asÃ­:** el plan gratuito no da histÃ³rico ni cierres y solo DraftKings y FanDuel con 60 s de retraso, de modo que solo sirve capturar a momentos fijos antes del saque (24 h, 6 h, 2 h, 60 min, 15 min); se guarda todo el catÃ¡logo prepartido del partido (â‰ˆ 1.500 filas, 58 mercados, 16 KB) porque cuesta lo mismo que filtrar y no se sabe aÃºn quÃ© mercados valdrÃ¡n. Siguen las convenciones del proyecto: originales como archivos, script con biblioteca estÃ¡ndar y cron del host (como `propline_captura.py`), sin tocar imÃ¡genes, base ni picks. Cargarlos en la base espera a tener semanas de datos y a ampliar el CHECK de `futbol.cuota_historica`.

## 2-nov-2026 Â· Cierre del rediseÃ±o de fÃºtbol: cuota 1,40, el once no mueve el 1X2 y producciÃ³n ya estaba alineada
Decisiones del titular: cuota mÃ­nima 1,40 hacia arriba y se acepta lo medido sobre A0 frente a Dixon-Coles (se queda Dixon-Coles). **Por quÃ© no hay cambios de cÃ³digo en los picks:** el mÃ³dulo de alta probabilidad ya toma el porcentaje de Pinnacle sin margen (desde el 5-oct) y es justo lo que 10.000 partidos con cuotas reales confirman como la fuente honesta; el motor propio promete 5-9 puntos de mÃ¡s y sustituirlo exigirÃ­a repetir la prueba histÃ³rica de `alta_prob_calibracion` sin ganancia esperable. F5 (A3-A7) se midiÃ³ con el once real: rotaciÃ³n y habituales ausentes tienen el signo esperado (âˆ’1,4 % de goles por titular cambiado; +1,9 % por cada habitual ausente del rival) pero el log-loss mejora â‰¤ 0,0012, y la fuerza del once no aporta. Con cuota â‰¥ 1,40 el techo honesto es â‰ˆ 65 % con una lÃ­nea y â‰ˆ 72-75 % eligiendo entre la escalera de lÃ­neas. Queda la mediciÃ³n semanal (`remedir_semana.py`) y dos decisiones del titular (tope de 1,80 del destacado web; capturar SharpAPI). Informe Â§14.

## 2-nov-2026 Â· Las cuotas histÃ³ricas se cargan en `futbol.cuota_historica`, no en `odds_snapshots`
El titular autorizÃ³ cargar el archivo de BetsAPI y el respaldo de API-Football. **Por quÃ© una tabla aparte:** `odds_snapshots` es inmutable y varias lecturas no filtran por fuente (`api/main.py`, `daily.py`, `clv._closing_prices`, `quote_coverage`); cuotas retroactivas con `captured_at` ficticio habrÃ­an alterado CLV y pantallas ya medidos, y un error de carga no se puede deshacer allÃ­. La tabla nueva es igual de inmutable, guarda solo apertura/T-60/cierre (1,03 M filas, 351 MB; los 17 M de cambios de precio siguen en el VPS) y marca `retroactiva`. Ensayada en un esquema aislado, cargada en una transacciÃ³n, `odds_snapshots` intacta. De paso, la mezcla casa + motor se validÃ³ fuera de muestra y se redujo a hÃ¡ndicap y goles de la 1.Âª parte: en cÃ³rners y hÃ¡ndicap total no aporta.

## 1-nov-2026 Â· Con 10.000 partidos de cuotas de bet365 la casa sigue siendo la fuente honesta y el motor solo ayuda en hÃ¡ndicap, cÃ³rners y 1.Âª parte
Se analizÃ³ en local (sin tocar la base) el archivo de BetsAPI del VPS: 9 ligas, 6.944 partidos con modelo, cuotas a T-60 y al cierre. **Por quÃ©:** con una muestra 50 veces mayor que la de PropLine (150 partidos) el resultado se confirma: bet365 sin margen cumple o es conservador (mejor 10 % del dÃ­a 70â€“72 %) y el motor propio promete 8 puntos de mÃ¡s; su aporte Ãºtil es una mezcla de â‰ˆ 30 % solo en mercados con menos liquidez (hÃ¡ndicap, cÃ³rners, 1.Âª parte), con ganancias de Brier de 0,0003â€“0,003. Un error mÃ­o (el Â«pierdeÂ» del hÃ¡ndicap del motor estaba mal calculado) se encontrÃ³ porque el motor salÃ­a 20 puntos por encima de la realidad en hÃ¡ndicap; se corrigiÃ³ y se aÃ±adiÃ³ prueba. Las lecturas en vivo hicieron medibles los cÃ³rners en el minuto 65-70 (â‰ˆ 53 %, la casa ya precia que el favorito pierda) y la carrera a X cÃ³rners. Las fichas de bet365 NO traen todos los mercados de las listas (faltan descanso/final, goleadores, primer equipo en marcar, pases, faltas). Informe Â§13.

## 1-nov-2026 Â· Donde Pinnacle no cotiza, la mediana de las demÃ¡s casas
DecisiÃ³n del titular: usar las demÃ¡s casas de PropLine en los mercados que Pinnacle no cotiza. **Por quÃ© la mediana y no una casa:** en estas ligas, a una o dos horas del saque, cada casa comÃºn tiene el mismo Brier que Pinnacle en las opciones compartidas (diferencia < 0,0007) y cumple lo anunciado en el tramo 60â€“80 %; la mediana no depende de que una casa concreta cotice o se equivoque. Sube la cobertura del mercado del 78â€“80 % al 99â€“99,5 % de las opciones con cuota â‰¥ 1,28 sin perder honestidad (cierre: anuncia 74,8 %, acierta 74,7 %). El motor queda para el â‰ˆ 1 % que no cotiza nadie. De paso se corrigiÃ³ el emparejamiento del hÃ¡ndicap de Pinnacle (local L con visitante âˆ’L). Informe Â§12.

## 1-nov-2026 Â· Con cuota real â‰¥ 1,28 la probabilidad publicada debe ser la de Pinnacle, no la del motor
Medido con las cuotas reales de PropLine (23-oct â†’ 1-nov, 128 partidos a T-60, 150 al cierre). **Por quÃ©:** exigir cuota â‰¥ 1,28 a una opciÃ³n que el motor ve por encima de 74 % selecciona justo los casos en que el motor discrepa del mercado, y en ellos acierta lo que dice Pinnacle (motor 54 %, Pinnacle 46 %, real 46â€“47 %). Elegir entre muchas lÃ­neas con el motor infla lo anunciado 5â€“8 puntos; Pinnacle sin margen cumple lo anunciado (cierre 74,7 % frente a 74,4 %). El motor queda para mercados que Pinnacle no cotiza, con el tope de 74,4 %. Muestra corta (Â±8 puntos): remedir cada semana. Informe Â§12.

## 1-nov-2026 Â· Mercados del titular: la probabilidad alta honesta estÃ¡ en mercados Â«aburridosÂ», no en los populares
Se modelaron y midieron los 37 mercados de las dos listas del titular con las mismas distribuciones del rediseÃ±o (matriz de A0 o del mercado invertido, mitades por f1 de liga, Yip, Dawson, props por jugador) y la cuota mÃ­nima 1,28. **Por quÃ© importa:** por encima de â‰ˆ 74 % de probabilidad la cuota cae bajo 1,28, asÃ­ que el techo honesto con cuota publicable es â‰ˆ 75â€“80 %, y lo alcanzan favorito marca, 2.Âª parte mÃ¡s de 0,5, mÃ¡s de 1,5, doble del favorito, primer equipo en marcar y cÃ³rners mÃ¡s de 7,5; los mercados populares (Lista 2) casi todos quedan bajo 60 %. Tres afirmaciones de la Lista 1 no se sostienen (2.Âª mitad con mÃ¡s goles 45 %, ambos marcan NO 46 %, AH de cÃ³rners 63 %). Los props de jugador crudos prometen de mÃ¡s y se recalibran con temporadas anteriores; los pases son la excepciÃ³n (deriva). Informe Â§10â€“11.

## 1-nov-2026 Â· Retirada completa de las fuentes antiguas en un solo PR (`retirar/fuentes-todo`)

DecisiÃ³n del titular: hacerlo todo de una vez en un PR nuevo, y fusionar y desplegar al final. Lo que se aÃ±ade a las fases 1-2c: las tres piezas que quedaban enganchadas, separando siempre lo vivo de lo retirable. `sofascore_alineaciones` y `sofascore_partidos` mezclaban la lectura del archivo de Apify con las funciones que escriben bajas y once (`emparejar`, `aplicar`, `titulares`, `bajas`) y que sigue usando SportsAPIPro: esas pasan a `sofascore_carga.py` y el resto se borra. `history_fd.py` mezclaba el cargador de CSV de football-data con `insertar_cierre` (lo usa `cierres_odds_api`) y `_parse_date` (lo usa `early_vs_close`): se extraen y el cargador se borra. El chequeo de frescura del xG ya no lee los assets de worldfootballR.

Descanso: `db/093` hace que `v_descanso_equipo` use `calendario_equipo` hasta su Ãºltima carga y los partidos terminados de `matches` despuÃ©s; antes la vista sobrestimaba el descanso 8,2 dÃ­as de media. Verificado en un esquema aislado con partidos antes y despuÃ©s del corte. LÃ­mite declarado: copas domÃ©sticas y selecciones posteriores al 22-oct no estÃ¡n.

AdemÃ¡s, la prueba de tenis `test_shadow_paid_path_uses_post_receipt_time_and_preseals` dependÃ­a del mes real (parcheaba `shadow.now`, pero `Capture` usa su propio reloj): desde el 1-nov fallaba en `main` limpio. Se fija el reloj de `Capture` (mismo criterio que #64).

## 1-nov-2026 Â· Las fuentes retiradas se quitan del cÃ³digo por fases, no de golpe

DecisiÃ³n del titular: retirar API-Football, Apify, PitchAPI, BetsAPI, worldfootballR/FBref, football-data y soccerway/365scores conservando los datos ya cargados. Por quÃ© por fases: el grafo de imports mostrÃ³ que `api_football.py` no es solo un cliente, tambiÃ©n aloja `record_health`, que usan 20 mÃ³dulos (PropLine, FotMob y SportsAPIPro incluidos), y que football-data sostiene la base estadÃ­stica, los cierres de 1X2 y 24 archivos de `src`. Borrarlos de golpe habrÃ­a roto jobs activos sin avisar.

Fase 1 (esta rama): solo lo que no tiene importadores ni cron activo: PitchAPI completo con su panel, `calendario_equipos`, `injuries`, los dos puentes AFâ†”FotMob, el descargador de BetsAPI y 6 pruebas. Las bajas siguen entrando por FotMob y SportsAPIPro. Los datos y migraciones no se tocan; el panel `/control/respaldo` desaparece y la clave de PitchAPI ya estaba vacÃ­a en `pitchapi_settings`. Vuelta atrÃ¡s: `git revert` del commit de la rama (el cÃ³digo vive tambiÃ©n en `e097691`). Lo que queda y por quÃ© estÃ¡ en `harness/tareas.md`.

## 2026-11-02 â€” RediseÃ±o NBA, Sprint 0 (base `nba_datos`)

- DecisiÃ³n: `nba.dato_a_las(corte)` es el Ãºnico camino de lectura del motor y cada mÃ©trica declara su `resolucion`: `prioridad` (hechos Ãºnicos; gana la mejor fuente) o `por_fuente` (disponibilidad y proyecciones, que cambian cada hora; una fila por fuente, la mÃ¡s reciente visible). Sin esto, un parte oficial viejo taparÃ­a a un dato mÃ¡s nuevo de otra fuente.
- DecisiÃ³n: las tablas de evidencia rechazan UPDATE/DELETE/TRUNCATE con disparadores por sentencia (fallan incluso con `WHERE false` y con `TRUNCATE ... CASCADE`), para que ningÃºn "arreglo rÃ¡pido" pase por filas vacÃ­as.
- DecisiÃ³n: la huella de cada migraciÃ³n ignora CRLF/LF; en Windows y en el VPS el mismo archivo debe dar la misma huella.
- DecisiÃ³n: el margen de las cuotas no se guarda (vista `nba.cuota_margen`) y el mÃ©todo de quitado de margen queda en `nba.pronostico.version_modelo`.
- Pendiente: desplegar `nba-db` en el VPS con confirmaciÃ³n; el compose no se probÃ³ con Docker (no hay Docker en este PC).

## 2026-11-02 â€” RediseÃ±o NBA, Sprint 1a (carga y adaptadores)

- DecisiÃ³n: `guardar_datos(..., solo_cambios=True)` no repite una fila si el Ãºltimo valor visible de esa fuente y clave es idÃ©ntico; `nba.dato_a_las` ya devuelve ese valor hasta que cambie, asÃ­ que guardar cada hora lo mismo solo gastarÃ­a espacio.
- DecisiÃ³n: la identidad nunca fusiona por duda. Un nombre normalizado igual solo crea alias si hay UN candidato canÃ³nico que aÃºn no tiene fila de esa fuente; un segundo id de la misma fuente con el mismo nombre es otra persona.
- DecisiÃ³n: de ESPN lesiones solo existe la lista de quienes figuran; quien deja de figurar recibe `sin_reporte` (no Â«disponibleÂ»), porque la ausencia de reporte no prueba que juegue.
- DecisiÃ³n: los adaptadores no hacen red; reciben `obtener(url)`. Un error o un 403 deja una captura `ok = false` y ningÃºn dato imputado; los minutos nulos de Rotowire no se rellenan.
- Hallazgo: ESPN omite `athlete.id` en las lesiones; el id se saca del enlace pÃºblico del jugador. Rotowire usa los tricodes oficiales; ESPN usa GS/NO/NY/SA/UTAH/WSH.
- Pendiente: S1b y S1c; nada de S1 estÃ¡ desplegado todavÃ­a.

## 2026-11-02 â€” Rotowire/ESPN a `nba_datos` (Sprint 1c)

- DecisiÃ³n: Rotowire entrega gratis los minutos proyectados solo del visitante; el endpoint del local responde Â«debes ser suscriptorÂ». No se paga ni se rodea: se piden solo los visitantes y el aviso de pago queda como captura fallida con su texto.
- DecisiÃ³n: el colector prueba siempre la peticiÃ³n directa (gratis) y usa ZenRows solo ante 403/429/503 y con tope diario (30 crÃ©ditos); hoy ni Rotowire desde el VPS ni la prueba local necesitaron pago.
- DecisiÃ³n: ESPN se procesa en lotes de 200 recibos y el estado (`estado_espn.json`) avanza tras confirmar cada lote; un fallo a mitad no pierde el avance ni repite lo ya cargado.
- Hallazgo: en pretemporada ESPN trae rivales que no son de la NBA (p. ej. Â«LONÂ»); esos partidos se omiten en lugar de abortar la carga.
- Hallazgo: `docker exec` sin `-i` no pasa la entrada estÃ¡ndar, y un `pg_restore -l` asÃ­ falla con Â«input file is too shortÂ»; la prueba de restauraciÃ³n usa `-i`.
- Pendiente: ninguna captura es de pago salvo el respaldo; falta programar la copia fuera del VPS en el PC del titular y S1b.

## 2026-11-02 â€” Parte oficial y final del partido (Sprint 1b-A)

- DecisiÃ³n: un juego es Ãºnico por (fecha ET, local, visitante). Una misma fuente puede traer ids distintos del mismo juego (el PDF no trae id y se usa uno sintÃ©tico; cdn trae el real), asÃ­ que el alias se decide por esa tupla y los datos siempre se escriben bajo el canÃ³nico mÃ¡s antiguo.
- DecisiÃ³n: el id real de la NBA se reconoce por su forma (10 dÃ­gitos); los ids sintÃ©ticos del PDF no cuentan.
- DecisiÃ³n: el presupuesto de Scrapfly se mide por dÃ­a UTC con tope 25, y un archivo se reintenta como mucho dos veces (en la prueba real 14 de 30 peticiones a cdn fallaron y se cobraron).
- Hallazgo: el CDN de los PDF responde 403 (no 404) cuando el PDF de esa hora aÃºn no existe; desde el VPS responde igual que desde el PC, asÃ­ que no hace falta proxy.
- Error mÃ­o: probÃ© la identidad con fixtures donde el PDF no existÃ­a y no vi el choque entre ids sintÃ©tico y real hasta el despliegue; quedaron 15 canÃ³nicos duplicados inertes (la evidencia no se borra).

## 2026-11-02 â€” Cuotas de PropLine (Sprint 1b-B)

- DecisiÃ³n: el contrato de una lÃ­nea principal NO lleva el punto (la lÃ­nea se mueve y es un valor); el de una alternativa SÃ (cada punto es otro contrato). AsÃ­ `cuota_cierre` da la lÃ­nea principal al cierre.
- DecisiÃ³n: solo se guarda una cuota cuando cambia el precio o la lÃ­nea (compara contra el Ãºltimo valor de la misma fase), pero la primera de cada fase se guarda siempre; asÃ­ el primer precio dentro de la Ãºltima hora (el cierre) existe aunque no se haya movido.
- DecisiÃ³n: casas = Pinnacle (referencia afilada), DraftKings, FanDuel y BetMGM; los Â«milestoneÂ» se omiten porque derivan de las alternativas y multiplican las filas.
- Hallazgo: en PropLine los totales de equipo vienen como mercado `totals` con el campo `team`; se guardan como `team_totals` con el equipo como entidad.
- Hallazgo: el id de jugador de PropLine (`nba:NNNN`) coincide con el `personId` de cdn.nba.com, asÃ­ que las cuotas se unen a box scores sin cruzar nombres.
- VerificaciÃ³n: mÃ¡rgenes de Pinnacle 2,6-3,8 % en mercados de equipo y â‰ˆ 7 % en props, coherentes con la literatura (fichas 21-23).

## 2026-11-02 â€” Cuotas histÃ³ricas (Sprint 1b-C)

- DecisiÃ³n: se reutilizan los archivos de cuotas que ya existÃ­an (bet365 de BetsAPI, props y moneyline de The Odds API) en lugar de comprar un backfill; el instante de cada fila es el de la casa y la adquisiciÃ³n va en la captura `historico`.
- DecisiÃ³n: el margen se calcula por contrato, no por lÃ­nea (en un hÃ¡ndicap los dos lados tienen lÃ­neas opuestas).
- DecisiÃ³n: en el histÃ³rico de props la lÃ­nea forma parte del contrato porque un mismo jugador, casa y foto trae varias lÃ­neas.
- Error mÃ­o: la vista `cuota_margen` de la migraciÃ³n 0004 estaba mal para hÃ¡ndicaps y solo se vio con datos reales; la corrige la 0007. LecciÃ³n: probar las vistas con datos reales de cada mercado antes de dar un sprint por cerrado.
- Medida: 3,25 M de filas histÃ³ricas cargadas en â‰ˆ 7 min; la base ocupa â‰ˆ 290 bytes por cuota con Ã­ndices.

## 2026-11-02 â€” Cajas y partes histÃ³ricos (Sprint 1b-D)

- DecisiÃ³n: las cajas histÃ³ricas se cargan en bloque (`guardar_datos_lote`, sin comparar con otras fuentes ni con el valor anterior) porque no hay solape en el tiempo con las capturas hacia adelante; los partes sÃ­ van con Â«solo cambiosÂ» y en orden cronolÃ³gico.
- DecisiÃ³n: `recibido_en` de la caja final es la adquisiciÃ³n del archivo y `pit = reconstruido`; las consultas histÃ³ricas filtran por fecha de juego. Los partes usan la hora del parte.
- Medida: 2,7 M de filas de caja en â‰ˆ 6 min y 657 mil filas de partes en â‰ˆ 8 min (con Â«solo cambiosÂ» quedan 150 mil); â‰ˆ 300 bytes por fila con Ã­ndices.
- Pendiente: 113 jugadores ambiguos (nombre repetido sin equipo como pista) y la uniÃ³n entre ids de ESPN/Rotowire y los de la NBA depende de ello.

## 2026-11-02 â€” Sprint 2: disponibilidad y minutos

- DecisiÃ³n: la probabilidad de jugar sale de medir los partes contra quiÃ©n jugÃ³ (no de una convenciÃ³n). Mi convenciÃ³n inicial era peor (Brier 0,0289 frente a 0,0266 de la tabla medida) y los partes cambian de significado con los aÃ±os (Probable pasÃ³ de 93 % a 71 %), asÃ­ que la tabla se vuelve a medir cada temporada.
- DecisiÃ³n: el decaimiento de los minutos se eligiÃ³ con 2023-24 y 2024-25 (0,70); con el 0,90 que puse al principio el modelo solo igualaba a la media de 5 partidos. La incertidumbre sale de residuos por tramo de minutos esperados, no de las muestras del historial (daban 74,7 % de cobertura en el intervalo del 80 %).
- Hallazgo: quien no figura en la caja cuenta como que no jugÃ³; si se excluyen esos casos Â«QuestionableÂ» parece jugar el 80 %, cuando en realidad es â‰ˆ 43 %. Sesgo de selecciÃ³n que hay que evitar en cualquier evaluaciÃ³n de disponibilidad.
- LÃ­mite: Available (84 %) y Â«sin parteÂ» (84 %) mezclan titulares y fondo de plantilla; falta condicionar al rol.

## 2026-11-02 â€” Sprint 3: nÃºcleo del marcador y mercados de equipo

- Resultado honesto: un nÃºcleo solo de ratings de equipo queda calibrado pero NO aporta informaciÃ³n al cierre de bet365 (peso de mezcla 0,03 contra 1,03 de la lÃ­nea; RMSE 14,49 frente a 14,04). Coincide con lo que ya decÃ­a la calibraciÃ³n de la v1.5; no se intentÃ³ forzar la mÃ©trica con ajustes sobre la prueba.
- DecisiÃ³n: el nivel de liga se actualiza mÃ¡s rÃ¡pido (0,01) porque la anotaciÃ³n sube cada temporada; con 0,002 el total iba retrasado.
- Hallazgo: jugar en la noche siguiente cuesta â‰ˆ 2,8 puntos de margen por equipo (3,5 errores estÃ¡ndar) y no mueve el total. Se mide en el ajuste y se fija antes de mirar la prueba.
- DecisiÃ³n: coherencia entre mercados por construcciÃ³n (una sola muestra simulada por partido), no por reconciliaciÃ³n posterior.
- Siguiente palanca: jugadores esperados dentro del rating de equipo (lo que mueve una lÃ­nea es quiÃ©n juega).

## 2026-11-02 â€” Sprint 3b: jugadores dentro del nÃºcleo

- DecisiÃ³n: el nÃºcleo v2 promedia el rating de equipo con el de jugadores (margen y total); solo jugadores empeora el total (19,46 frente a 19,12).
- Hallazgo: el tope no son los minutos esperados. Con los minutos reales del partido el error del margen solo baja a 14,30 (mercado 14,04); lo que falta es saber mÃ¡s de cada jugador, no adivinar quiÃ©n juega.
- DecisiÃ³n: la probabilidad de jugar sin parte se condiciona al rol (53 % bajo 15 minutos esperados, 88 % entre 15 y 25, 98 % con 25 o mÃ¡s); el 84 % global mezclaba titulares seguros con fondo de plantilla.
- DecisiÃ³n: el equipo de cada jugador en cada partido es un dato propio (`equipo_del_jugador`, migraciÃ³n 0008); no se deduce de forma fiable despuÃ©s.

## 2026-11-02 â€” Sprint 4: props de jugador

- DecisiÃ³n: los props se valoran condicionados a jugar (las casas anulan la apuesta si no juega); la incertidumbre de minutos entra como mezcla sobre muestras de minutos, no como una cola aparte.
- Hallazgo: la cobertura de conteos bajos no se mide con el PIT de punto medio (88 % falso en triples); se usa el PIT aleatorizado, que es uniforme si la distribuciÃ³n estÃ¡ calibrada.
- Hallazgo: la cobertura del 80 % pasÃ³ de 73 % (v1.5) a â‰ˆ 81 % en las cuatro estadÃ­sticas sin reajustar nada contra el mercado.
- LÃ­mite: sin contexto del partido, la probabilidad de superar la lÃ­nea apenas discrimina (pendientes 0,09-0,61).

## 2026-11-02 â€” Sprint 5: referencia, evaluaciÃ³n Ãºnica, sellado y G-fuga

- DecisiÃ³n: el mÃ©todo de quitado de margen es proporcional; Shin y potencia ganan unas diezmilÃ©simas en favoritos fuertes pero no significativas, y el mÃ©todo queda escrito en `version_modelo` (no en la cuota).
- Hallazgo: la implementaciÃ³n independiente de G-fuga hallÃ³ un error real del motor (no aplicaba el arrastre de temporada al primer partido de una temporada nueva, â‰ˆ 2,3 puntos de diferencia). Una compuerta de reproducibilidad sola no lo habrÃ­a visto; hace falta compararla con un cÃ¡lculo hecho por otro camino.
- DecisiÃ³n: las cajas histÃ³ricas se aceptan por fecha del partido (su `recibido_en` es la fecha de adquisiciÃ³n del archivo), supuesto escrito en `pit.py`; el motor y el sellado exigen que el corte ya haya pasado.
- LÃ­mite: G-fuga cubre solo el motor de equipo; jugadores y props se enlazan en el Sprint 6.

## 2026-11-03 â€” Sprint 6: API de lectura y web NBA

- DecisiÃ³n: la distribuciÃ³n sellada guarda 199 cuantiles (pasos de 0,5 %) para que la API calcule la probabilidad de cualquier lÃ­nea sin resimular; es la misma informaciÃ³n que ya se sellaba, solo mÃ¡s fina (aÃºn no habÃ­a nada sellado en producciÃ³n).
- DecisiÃ³n: la API no manda texto visible, solo cÃ³digos de error; la web los traduce a los 6 idiomas y una prueba exige paridad de claves y cobertura de cÃ³digos.
- DecisiÃ³n: v2 sigue sin exponerse; el piloto v1 de `/nba` se mantiene hasta que apruebes v2 (despuÃ©s se retira del VPS).
- Pendiente real: sin el proceso `nba-motor` (sellado por partido) la web no tiene pronÃ³sticos que mostrar.

## 2026-11-03 â€” nba-motor

- DecisiÃ³n: el corte del pronÃ³stico es `salto âˆ’ 60 min`, no la hora en que corre el cron; un cron atrasado usa los mismos datos y G-fuga sigue valiendo. Nunca se sella despuÃ©s del salto.
- DecisiÃ³n: el cron NO se activa solo: un sello es solo-anexar, y un error del motor quedarÃ­a para siempre en la cadena. Se activa con tu visto bueno tras ver el simulacro.
- Incidente propio: al construir la imagen puse solo la etiqueta (`3ca6392`) en `imagen_actual`, que guarda el nombre completo (`nba-captura:3ca6392`); los crons de captura fallaron de â‰ˆ 00:10 a 01:33 UTC del 3-nov (â‰ˆ 1 h 20 min sin Rotowire/ESPN/partes/cdn/PropLine). Corregido; ESPN y partes recuperaron lo pendiente, las fotos de Rotowire de ese tramo no se pueden recuperar.

## 2026-11-03 â€” Props de jugador en el motor

- DecisiÃ³n: el servidor no entrena; los parÃ¡metros de props son un artefacto JSON versionado (huella en `version_modelo`, normalizada por finales de lÃ­nea) producido en local.
- Hallazgo (G-fuga): la plantilla limitaba la historia a 500 dÃ­as y el modelo validado usa los Ãºltimos 30 partidos sin lÃ­mite de edad; era una diferencia real entre producciÃ³n y lo evaluado. Corregida y comprobada contra una reconstrucciÃ³n independiente.
- DecisiÃ³n: los props de un partido se sellan todo o nada (una transacciÃ³n); si fallan, el equipo ya sellado se conserva y el siguiente cron completa.
- DecisiÃ³n: la alerta sale una vez por tipo, partido y dÃ­a; el estado se sembrÃ³ con lo anterior a la activaciÃ³n para no mandar una avalancha al primer mensaje.
- LÃ­mite: los jugadores no entran aÃºn en el pronÃ³stico del equipo.

## 2026-11-03 â€” Equipo 2.1 (jugadores en el equipo)

- DecisiÃ³n: se mezcla solo el margen, porque es lo Ãºnico que mejora en los dos periodos de evaluaciÃ³n; el total de la mezcla cambia de signo entre validaciÃ³n y prueba y se deja en el nÃºcleo de equipo.
- DecisiÃ³n: un solo pronÃ³stico de equipo por partido y corte; la versiÃ³n (2.0 o 2.1) dice si hubo plantilla suficiente. Sin ella se sella 2.0, nunca con jugadores inventados.
- Hallazgo: al reordenar el motor se perdiÃ³ la atomicidad de los props (cada sello se confirmaba solo); la prueba de fallo a mitad lo detectÃ³ y ahora van en una transacciÃ³n explÃ­cita.
- LÃ­mite: el artefacto de impacto es estÃ¡tico; sin reentrenos periÃ³dicos se degrada (el 3b lo reajustaba cada 21 dÃ­as).

## 2026-11-03 â€” Carga de SofaScore

- DecisiÃ³n: `nba_datos` sigue siendo la base principal; SofaScore es una fuente con menos prioridad que `nba_oficial` y se carga completa (todas las temporadas), no solo los huecos, porque da una verificaciÃ³n cruzada de la caja y los titulares.
- DecisiÃ³n: los jugadores se emparejan por la huella de la caja en el mismo partido, no por nombre; el nombre solo para quienes no comparten ningÃºn partido.
- Hallazgo: las dos cajas coinciden en mÃ¡s del 99 % de los datos; las diferencias son correcciones de estadÃ­stica (minutos 0,25 %, mÃ¡s/menos 0,77 %).
- Pendiente real: los entrenamientos, las evaluaciones y G-fuga se hicieron solo con nba_oficial; hay que repetirlos con la base nueva antes de la Fase 4.

## 2026-11-03 â€” Reentrenamiento con la base nueva

- Resultado: con SofaScore (mÃ¡s partidos, titulares y 2026-27) las evaluaciones de equipo, jugadores y props dan prÃ¡cticamente lo mismo que antes; los modelos no dependÃ­an de un detalle de la caja oficial.
- DecisiÃ³n: el efecto del descanso (2,90) y las sigmas se actualizan con la base nueva; eta, arrastre, tasa de liga y la regla Â«solo el margen se mezclaÂ» no cambian.
- Aprendizaje: la muestra de 100 partidos de G-fuga cambia cuando cambia el nÃºmero de partidos; su Brier no es una mÃ©trica del modelo (error tÃ­pico â‰ˆ 0,02), solo la alarma de fuga por debajo de 0,18.

## 2026-11-03 â€” Fase 4, F4.0: contratos

- DecisiÃ³n: la Fase 4 empieza por las fronteras entre pasos (Pydantic estricto), con el Paso A definido por sus salidas y no por el tipo de modelo; una red neuronal serÃ­a un retador mÃ¡s, sujeto a las mismas compuertas hacia adelante.
- DecisiÃ³n: las distribuciones de salida del contrato tienen la forma exacta de lo que ya se sella, para validar lo sellado, lo servido y lo simulado con un solo esquema.
- Hallazgo: las pruebas con datos absurdos encontraron un hueco real en el contrato (`descanso_dias` aceptaba un equipo faltante); y los 192 sellos reales cumplen los contratos.
- LÃ­mite: los contratos aÃºn no estÃ¡n conectados al motor ni a la API.

- DecisiÃ³n (F4.0): un contrato incumplido nunca se arregla en silencio: el motor no sella ese partido (o descarta ese jugador) y alerta; la API no sirve ese dato. Los sellos son inmutables, asÃ­ que la validaciÃ³n va ANTES de sellar.
- Hecho: los 5.852 distribuciones reales de la comprobaciÃ³n cumplen los contratos; la frontera no rechaza nada legÃ­timo.

## 2026-11-03 â€” F4.1: origen mÃ³vil

- Resultado: con tres temporadas de prueba distintas las conclusiones se sostienen; el modelo no supera al cierre en ningÃºn origen (ganador +0,0099 [+0,0071, +0,0127]); los jugadores acercan el modelo al mercado en los tres (âˆ’0,0024 a âˆ’0,0036 de Brier).
- Hallazgo: la distancia al mercado se achica con mÃ¡s temporadas de entrenamiento (+0,0119, +0,0099, +0,0078), y la pendiente de calibraciÃ³n del ganador queda algo por encima de 1 (probabilidades tÃ­midas), candidata a recalibraciÃ³n.
- LÃ­mite: la v1.5 solo puede compararse en 2025-26; las cuotas de cierre no existen antes de 2023-24.

- Resultado (F4.1, recalibraciÃ³n): ajustar la escala de la media o la probabilidad con temporadas anteriores no mejora ni acerca al mercado; la pendiente >1 de la prueba es ruido de muestra, no un sesgo estable. No se cambia el motor.

## 2026-11-03 â€” F4.2 Monte Carlo

- DecisiÃ³n: subir el equipo a 100.000 simulaciones porque con 20.000 el error del 1 % peor (0,86 pp) incumplÃ­a la compuerta de 0,5 pp y el coste de 100.000 es de 6 ms; los props no tienen Monte Carlo (son analÃ­ticos).
- Hallazgo: la reproducibilidad entre Windows y Linux es exacta bit a bit con la misma versiÃ³n de numpy; se fija la versiÃ³n y se conserva el script de huella como prueba al actualizar.
- Hallazgo: el error de un prop correlaciona +0,10 a +0,13 con el del total del partido y âˆ’0,13 con lo desigual en titulares; sin combinaciones en el producto no se simulan conjuntamente, pero no se debe multiplicar un prop por una probabilidad del partido.

## 2026-11-03 â€” F4.3 estrÃ©s

- Hallazgo: tres huecos reales encontrados por las pruebas de estrÃ©s (estadÃ­stica ausente = 0, minutos corruptos aceptados, equipo con ratings viejos sellado cuando solo a Ã©l le faltaban resultados); ninguno afectaba a los datos de hoy (la base estÃ¡ limpia) pero sÃ­ a cualquier fuente futura.
- DecisiÃ³n: la imagen con los arreglos no se despliega mientras estÃ© pendiente la decisiÃ³n del titular sobre el impacto S3c, para no mezclar cambios de comportamiento con una activaciÃ³n sin aprobar.
- CorrecciÃ³n: el 3-nov no hubo partidos NBA (elecciones); mi aviso anterior de que los primeros sellos de la imagen 6b85093 saldrÃ­an hacia las 22:00 UTC de hoy era falso: salen con los partidos del 4-nov.

- DecisiÃ³n del titular (3-nov): mantener el impacto S3c (RAPM de quintetos) en producciÃ³n; se despliegan los arreglos de F4.3 sobre esa base (`nba-motor:d73c7c5`).

## 2026-11-03 â€” F4.4 ensayo operativo

- Resultado: se restaura y se verifica en menos de un minuto, la manipulaciÃ³n se detecta y la vuelta atrÃ¡s son 1 s; el punto dÃ©bil es la distancia entre respaldos (24 h de sellos) y la copia fuera del servidor, que dependÃ­a de traerla a mano y estaba desactualizada.

- DecisiÃ³n del titular (3-nov): respaldo del VPS cada 6 horas y copia diaria al PC programada; asÃ­ la pÃ©rdida mÃ¡xima de sellos pasa de 24 h a 6 h y la copia fuera del servidor deja de depender de que alguien la traiga.

## 2026-11-03 â€” F4.5 informe final

- Resultado: v2 es calibrado, coherente, sellado y reproducible, y mejora la cobertura de props (73 % â†’ 80â€“81 %), pero es peor que el cierre del mercado en las tres temporadas de prueba y no mejora el margen de la v1.5; el informe lo dice sin adornos y propone un periodo prospectivo antes de publicar.
- Hallazgo: v2 depende de v1 sin que constara (el colector de ESPN lee el libro `run57` escrito por `nba-research-capture-run68-v2`); por eso el retiro de v1 queda condicionado a independizar ese colector y a la aprobaciÃ³n explÃ­cita del titular.
- DecisiÃ³n pendiente: etapas Aâ€“D del informe; ninguna se ejecuta sin el visto bueno del titular.

## 2026-11-03 â€” PromociÃ³n de v2 (orden del titular: Â«de una vez todoÂ»)

- Resultado: v2 queda pÃºblico como beta en `/nba/v2/` y v1 detenido; el colector `espn_directo` sustituye al ledger de `run57`, que era la Ãºnica dependencia de v2 hacia v1.
- DecisiÃ³n: v1 se detiene pero no se borra (reversible en minutos); `/nba` redirige a v2. Se acorta el periodo prospectivo: la evidencia de los sellos reales se mide en paralelo, ya con v2 publicado y con el aviso beta, en lugar de esperar 5â€“6 semanas antes de publicar.
- DecisiÃ³n: sin cuentas ni paywall por ahora (el piloto v1 tambiÃ©n era abierto); si el titular quiere integrarlo con cuentas, es una tarea aparte.

## 2026-11-01 â€” Respaldo football-data.org (rama `futbol/fdorg-respaldo`, desplegada el 1-nov)
- DecisiÃ³n: football-data.org es un **testigo** de calendario y resultados, no una fuente dueÃ±a: compara contra `matches` y avisa; no escribe ni crea equipos. Reutiliza `compare()`/`promote()` de `pitchapi_respaldo` por adaptador, sin tocar cÃ³digo desplegado. Tablas `fdorg_*` propias (db/092; 085-088 quedan para `futbol/base-unica`).
- DecisiÃ³n: prÃ³rroga y penales no se comparan (la convenciÃ³n de goles puede diferir); el pendiente exige 6 h desde el saque porque el plan gratis puede reflejar marcadores con retraso (no verificado).
- Verificado: 30 pruebas (nuevas + PitchAPI) y una pasada completa en esquema aislado de Postgres local (migraciÃ³n idempotente, sin duplicar abiertas, sin tocar `matches`, 401 avisa una vez). DiseÃ±o: `docs/superpowers/specs/2026-11-01-football-data-org-respaldo-design.md`.
- Pendiente: tÃ©rminos del plan gratuito; clave en el `.env` del VPS; (db/092 y activaciÃ³n ya hechas en el despliegue del 1-nov); fase 2 (rellenar resultados) y panel solo si el titular lo decide.

## 2026-11-01 â€” Tabla Ãºnica de fÃºtbol `futbol.dato`
DecisiÃ³n clave: el titular pidiÃ³ UNA sola tabla para todo lo que capturen las APIs, los servicios y los scrapers, y que solo ella alimente al motor; mi primer diseÃ±o dejÃ³ nueve tablas por tipo y no lo cumplÃ­a. `futbol.dato` es una tabla esparcida: una fila por hecho, columnas tipadas con nombre unificado y compartidas entre tipos, clave primaria que impide repetidos, una fuente por tipo y partido (prioridad en `futbol.prioridad_entidad`) y un id de jugador Ãºnico (el de SofaScore, negativo si no hay pareja). Los adaptadores son funciones SQL (FotMob, clima ERA5, estadio/altitud) y el cargador del archivo de SofaScore. Quedan fuera `matches` (registro del partido) y `odds_snapshots` (inmutable por trigger y base de la cadena de hashes: moverla exige quitar garantÃ­as, solo con confirmaciÃ³n explÃ­cita). Aplicada en producciÃ³n con respaldo y ensayo con ROLLBACK; 1,6 millones de filas, 0 repetidos. La rama anterior estaba 764 archivos detrÃ¡s de `origin/main` (otra sesiÃ³n retirÃ³ API-Football y otras fuentes): se rehÃ­zo sobre `origin/main` con migraciones 094-095.
## 2026-11-01 â€” La tabla Ãºnica cubre el partido completo del scraper de SofaScore
DecisiÃ³n clave: medido con un partido real, la tabla guardaba solo lo esencial y, peor, con una fuente dueÃ±a por tipo los datos de SofaScore no llegaban donde FotMob ya cubrÃ­a el partido. Se ampliÃ³ a las 82 estadÃ­sticas de jugador, las 46 de equipo por periodo, los campos de tiro e incidencia, la asistencia, el momentum y las posiciones medias, y SofaScore pasÃ³ a COMPLETAR las columnas vacÃ­as de la fila de FotMob (anotado en `fuente_extra`) sin tocar `nota`, `valor_mercado` ni `posicion_id`, que son entradas del motor con el sentido de cada fuente. Quedan fuera solo h2h, forma previa y rachas (no verificables como previos) y best_players/player_ranking (derivados). El orden de la pasada diaria importa: FotMob reescribe sus filas y SofaScore debe volver a completarlas despuÃ©s. 2,8 millones de filas, 0 repetidos.

## 2026-11-01 â€” RediseÃ±o de los motores sobre `futbol.dato`: ligas del nÃºcleo y datos frente a los estudios
DecisiÃ³n clave: mientras el titular descarga el resto, el rediseÃ±o se construye y se activa solo con las 8 ligas que tienen tiros con xG, estadÃ­sticas por mitad e incidencias completas (Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira, BrasileirÃ£o; Premier y LaLiga desde 24/25); con Serie A sola no hay potencia. Al cruzar columna por columna lo que piden los estudios aparecieron dos huecos del cargador que ninguna prueba veÃ­a: se descartaban cÃ³rners, tiros, xG y tarjetas por mitad (Â«ya estÃ¡n en `matches`Â», que solo tiene el total) y no se guardaba quiÃ©n arbitra (solo su trayectoria, que ademÃ¡s es posterior al partido). Retiro de tablas: solo lo derivado de un original conservado o sin lectores; `historical_football_player_stats` aÃºn alimenta `cargar_fotmob`, asÃ­ que primero hay que impedir que una recarga pise con NULL.

## 2026-11-01 â€” Umbrales de sanciÃ³n, derbis y fase 2 en `futbol.dato`
DecisiÃ³n clave: los umbrales de amarillas se miden con nuestros datos (moda de lo acumulado antes de cada sanciÃ³n) y se guardan sin verificar, en vez de escribirlos de memoria: la mediciÃ³n confirma 5 en cinco ligas y 3 en Brasil, y delata que la Premier (por jornada), la Liga MX y Ligue 1 no tienen una regla fija. La regla automÃ¡tica de derbis solo vale con dos clubes en la ciudad, porque Â«misma ciudadÂ» en Londres daba 15 derbis; las grandes ciudades van a una lista manual resuelta por nombre. La fase 2 conserva cada captura previa con su hora real y no aplica Â«una fuente por tipoÂ»: el motor necesita lo Ãºltimo sabido por fuente a T-60, no la mejor fuente del partido.

## 2026-11-01 â€” Retiro de tablas de origen redundantes (R1â€“R3) y despliegue de db/097â€“100
DecisiÃ³n clave: solo se borrÃ³ lo que ya vive en `futbol.dato` o se regenera desde un original conservado, y siempre tras un respaldo con recuento y sha256 y una copia local verificada. `historical_football_player_stats` no era un duplicado Â«seguroÂ» a ciegas (la vista que alimenta `cargar_fotmob` la une), asÃ­ que se borraron solo las filas de partidos ya cargados y de mÃ¡s de 14 dÃ­as, y una prueba demuestra que recargar FotMob sin ellas no vacÃ­a nada. `af_odds_snapshots` y `sofascore_detalles` eran inmutables pero sin lectores; el `DROP` va sin CASCADE para que falle si algo dependiera de ellas. El borrado de datos lo bloqueÃ³ el permiso hasta que el titular lo autorizÃ³ en el chat; una orden de otra sesiÃ³n no cuenta como autorizaciÃ³n.

## 2026-11-01 â€” RediseÃ±o de fÃºtbol desde cero con `futbol.dato` (rama `futbol/rediseno-f2`, nada activado)
DecisiÃ³n clave: todo se volviÃ³ a medir sobre la tabla Ãºnica (8 ligas, walk-forward semanal, mismas filas, log-loss y Murphy) en vez de fiarse de lo medido en Serie A el 31-oct, y cada estudio que pasÃ³ el titular se leyÃ³ entero y se puso a prueba en vez de aceptar el resumen que lo acompaÃ±aba. Varios resÃºmenes decÃ­an lo contrario que el texto (HIGFormer no mejora empates, DEFCON desaconseja contar acciones defensivas, KellyBench muestra que todos pierden, TabNet quedÃ³ por debajo de CatBoost, Chen no compara con y sin Poisson). El resultado medido manda: el mercado gana a todo en 1X2 y el modelo no aporta nada en la mezcla (peso 0); el score-driven con xG empata con Dixon-Coles; el apilado con Ã¡rboles empeora; donde sÃ­ hay valor es en el motor C (tarjetas con Ã¡rbitro/derbi/igualdad, cÃ³rners de Yip) y, pendiente, en lo previo al partido (once y bajas con hora de captura). Kelly sin ventaja solo frena la ruina: no se convierte en producto.

## 2026-11-01 â€” El objetivo es el acierto del pronÃ³stico mÃ¡s probable, no batir al mercado
DecisiÃ³n clave: el titular aclarÃ³ que ganar a las cuotas de cierre no es la meta (el mercado es mÃ¡s rÃ¡pido y tiene mejores datos); la meta es publicar el pronÃ³stico con mayor probabilidad de acertar y que el porcentaje anunciado sea cierto. Por eso el mercado sin margen pasa a ser una fuente mÃ¡s (la mÃ¡s honesta medida) y la mÃ©trica pasa a ser acierto del 5â€“10 % mÃ¡s probable de cada dÃ­a mÃ¡s diferencia anunciado-observado, por familia. Resultado: techo â‰ˆ 91 % en doble oportunidad, â‰ˆ 73 % en 1X2, â‰ˆ 69 % en goles, cÃ³rners y tarjetas, sin fuente claramente mejor; el apilado y la logÃ­stica prometen de mÃ¡s; y la cuota mÃ­nima de 1,40 de la app choca con la mÃ¡xima probabilidad (1X2 baja a â‰ˆ 59 %). Pendiente de decisiÃ³n del titular.

## 4-nov-2026 Â· NBA: mÃ­nimo de 1,20 en Partido y tarjetas de jugador
DecisiÃ³n clave: el mÃ­nimo de 1,20 se aplica solo a la lista de Partido, no al destacado, que conserva 1,40: el destacado ya tiene su propia regla y filtrarlo con 1,20 cambiarÃ­a quÃ© se publica. Los mercados de jugador se agrupan por jugador con su foto oficial (nunca el id interno) y las lÃ­neas se pliegan; en 390 px la tabla plana era ilegible. La identidad de la foto sale de `nba.entidad`/`nba_oficial` y, si no es Ãºnica, queda nula a propÃ³sito: una foto equivocada es peor que las iniciales. Desplegado en `nba-api:tarjetas-f11d97c7` y `quantfut-api-nba-tarjetas:f11d97c7`, verificado a 390 px y 851 px. Sigue abierto, ajeno a esta tarea, renovar el artefacto del motor antes del 7-nov.

## 2026-11-05 â€” #historial: la grÃ¡fica grande mide aciertos reales frente a esperados, no unidades

Motivo: la curva de beneficio (1 u por pronÃ³stico, cuota media 1,20) mostraba âˆ’6,98 u en 532
pronÃ³sticos con 83 % de acierto frente al 82 % prometido. No es un fallo del modelo: a cuota 1,20 el
punto de equilibrio es 83,3 % y el margen de la casa se come el resto (mismo resultado que la mediciÃ³n
del 5-oct: favoritos â‰¥ 80 % â†’ ROI âˆ’2,4 %). El producto promete probabilidad calibrada, y eso es lo que
ahora mide la grÃ¡fica: suma acumulada de (acierto âˆ’ probabilidad publicada) con franja de azar al 95 %
(`desvio()` en `frontend/historial-views.js`; vale tambiÃ©n para NBA y tenis porque usa la probabilidad,
no la cuota).

LÃ­mite que se mantiene a propÃ³sito: el beneficio NO se esconde. Sigue el indicador Â«Beneficio Â· 1 u por
pronÃ³sticoÂ» y la frase bajo la grÃ¡fica lo dice con su signo (Â«Acertar lo prometido no es ganar dineroâ€¦Â»).
Un test lo exige (`la grÃ¡fica grande mide aciertos frente a esperados y el beneficio sigue a la vista`).
No cambiar de mercado, ventana o mÃ©trica para que el resultado salga positivo: rompe la credibilidad de
la cadena de hashes y es publicidad engaÃ±osa. Cambiar la mÃ©trica es vÃ¡lido solo si la pÃ©rdida sigue a la
vista. Base: `main` (rama `web/historial-desvio`); ids de cachÃ© subidos a
`hist-desvio-20261105` en toda la cadena de imports. Sin desplegar ni confirmar visualmente en navegador.

## 2026-11-05 â€” #historial: cuota con su casa en cada fila, 7 dÃ­as, sin leyendas (decisiÃ³n del titular)

Pedido del titular: (1) cada resultado enseÃ±a la cuota y, debajo, de quÃ© casa es, en todos los deportes;
(2) Â«Acierto por dÃ­aÂ» y la tarjeta nueva miran solo los Ãºltimos 7 dÃ­as (`DIAS_GRAFICA = 7`);
(3) fuera las dos leyendas de la grÃ¡fica grande (explicaciÃ³n y Â«Hoy: +9,7 aciertosâ€¦ beneficio âˆ’6,98 uÂ»);
(4) la tarjeta Â«Beneficio Â· 1 u por pronÃ³sticoÂ» se sustituye por Â«DÃ­as en verde Â· Ãºltima semanaÂ»
(dÃ­as con mÃ¡s aciertos que fallos; cuenta real, no una mÃ©trica elegida a medida).

Esto sustituye el lÃ­mite de la entrada anterior (Â«el beneficio NO se escondeÂ»): lo decide el titular.
Lo que queda a la vista: la pregunta frecuente Â«Â¿ganarÃ© dinero seguro?Â» sigue diciendo el beneficio con
su signo, y `beneficio()` sigue calculÃ¡ndose y probÃ¡ndose (la cuota de referencia de tenis nunca entra).

Casa por deporte: NBA ya viene con casa (`book` â†’ `marketQuote`). FÃºtbol: `/mobile/v1/markets/history`
no devolvÃ­a `ref_book` (las filas de Alta probabilidad salÃ­an Â«Casa no registradaÂ»); ahora lo devuelve con
`nombre_casa()` (cambio en `src/qf/api/mobile.py`, **requiere desplegar la API**). Tenis: el servidor
publica `price: None`; sin cuota de casa sale Â«â‰ˆ justa del modelo Â· Modelo Â· sin casaÂ», no se inventa casa.
La rama `web/tenis-cuota-referencia` (c965e096) ya trae la cuota de referencia de PropLine para tenis
(`price_book`); el frontend la entiende (`ref` + `book`) pero ese servidor no estÃ¡ desplegado.
Ids de cachÃ©: `hist-casa-20261105`. Verificado en local contra producciÃ³n; sin desplegar.

## 2026-11-05 â€” DÃ­as ya jugados: pronÃ³stico sin VIP y mercados ordenados (decisiÃ³n del titular)

Regla 1 â€” sin candado pasado el dÃ­a: cuando termina el dÃ­a (hora de MÃ©xico, UTC-6 fijo: `ventana.dia_cerrado`)
en que se juega un partido, `GET /mobile/v1/matches/{id}` lo trata como `plus` (mercados, marcadores, picks de
Alta probabilidad y escalera del partido, todos abiertos), con o sin suscripciÃ³n. Hoy y maÃ±ana siguen igual.
Se eligiÃ³ MÃ©xico porque ya es el reloj del pronÃ³stico diario (`ventana.py`); un visitante de otra zona verÃ¡
abrirse los partidos de su noche a la medianoche de MÃ©xico. El cambio vale tambiÃ©n para la app mÃ³vil (mismo
endpoint). NBA y tenis no tienen candado en la web actual: no hubo nada que abrir. **Requiere desplegar la API.**
La lista `alta_probabilidad.vip` de `/mobile/v1/home` no se toca (solo trae partidos por empezar).

Regla 2 â€” orden en un partido ya liquidado (fÃºtbol, NBA y tenis; `ordenLiquidado` en `sports-data.js`):
acertados de mayor a menor cuota, luego lo sin resultado (devoluciÃ³n, anulado) y al final los fallados, tambiÃ©n
de mayor a menor cuota. Si el partido no tiene nada liquidado (o fue una retirada, todo Â«devoluciÃ³nÂ») queda el
orden por probabilidad de siempre. En NBA el texto Â«De mayor a menor probabilidadÂ» cambia a Â«Acertados primero,
de mayor a menor cuotaÂ». En tenis la cuota que ordena es la del modelo (no hay cuota de casa publicada).
Verificado en local contra producciÃ³n (fÃºtbol y NBA de ayer); los candados del fÃºtbol solo desaparecen al
desplegar la API. Ids de cachÃ©: `hist-casa-20261105`.

## 2026-11-05 â€” Tenis: la web lee la cuota PropLine de `/web/deportes/tenis/cuotas` (decisiÃ³n del titular)

Por quÃ©: el historial decÃ­a Â«Modelo Â· sin casaÂ» en todo el tenis porque `/web/deportes/tenis` trae `price: None`, pero la
cuota ya se calculaba en producciÃ³n aparte (`cuotas_tenis.py` + `cuotas_web.py`, usada solo por la app mÃ³vil). La rama
`web/tenis-cuota-referencia` (sidecar `tennis_cuotas.json`) quedÃ³ superada y no se despliega.

CÃ³mo: `ensureSport('tenis')` pinta primero el tenis y pide las cuotas DESPUÃ‰S (`loadTennisQuotes`); en frÃ­o el endpoint tarda
hasta ~100 s y mientras responde `unavailable`, asÃ­ que se reintenta dos veces cada 20 s y, si falla, queda la cuota justa del
modelo sin error visible. `applyTennisQuotes` pone `price`, `book`, `price_book` y `reference` solo si hay precio > 1 y casa con
nombre, y nunca pisa un precio que ya trajera el feed. Es una REFERENCIA (la mejor casa antes del sello, fuera del sello): se rotula
Â«Cuota de referenciaÂ» / Â«Casa Â· referenciaÂ» y `beneficio()` la excluye (marca `ref`). Efecto lateral buscado: la ventana de tenis y su
destacado muestran esa cuota y casa en vez de Â«Del modeloÂ».

Cobertura medida (5-nov): 132 de 143 eventos con cuotas; 67 de 102 destacados liquidados con cuota en su mercado. Los huecos son
hÃ¡ndicap de juegos (23), hÃ¡ndicap de sets (3) y juegos totales (2): el servidor exige la lÃ­nea exacta y no usa la mÃ¡s cercana, y esas
filas siguen con Â«Modelo Â· sin casaÂ». Ids de cachÃ©: `tenis-cuota-20261105` (app, real-views, ergonomic-views, sports-data, sports-window).
Verificado en local contra producciÃ³n; sin desplegar.

## 2026-11-05 Â· Mercados de la app: NBA y tenis con el diseÃ±o de fÃºtbol (rama app/mercados-todos-deportes)

- DecisiÃ³n: las piezas de la pestaÃ±a Mercados (radar, tarjeta de familia, tarjeta de pronÃ³stico con escudos/logos/fotos, cuota y casa, marco Hoy/Anteriores) viven en `market_hub.dart` y las usan los tres deportes.
- Hallazgo: la app NBA solo leÃ­a `/nba/v1/cartelera` (Ãºnicamente Â«GanadorÂ»); los otros 7 mercados con cuota y casa estaban en `/nba/v1/partido/{id}/mercados` y no llegaban. Ahora `enrichNbaFeed` los pide por partido (6 en paralelo, sin bloquear la pantalla) y la cuota del overlay v1 (cohorte vieja) ya no se usa en NBA.
- Regla de Â«pronÃ³stico publicadoÂ» en NBA/tenis: sellado antes del inicio, un solo lado por lÃ­nea y probabilidad 60â€“95 % (la banda del radar del servidor); el ganador queda exento.
- API (aditivo, SIN desplegar): `local_escudo`/`visitante_escudo` en `proximos` e historial de fÃºtbol. La app funciona sin ellas (agenda o iniciales). Desplegar segÃºn DEPLOYS.md.
- Regla de publicaciÃ³n en el servidor (NBA/tenis, cuota â‰¥ 1,20), app obediente; ver docs/regla_publicacion_20261105.md. Sin desplegar.


**5-nov-2026 â€” Historial web/Flutter y vacÃ­os por mercado.** La web cuenta Alta + Destacados de fÃºtbol y solo Destacados de NBA/tenis. Flutter filtraba los resueltos con la regla actual del overlay y usaba cifras empaquetadas en fÃºtbol. Se unifican fuentes y registros de tarjetas/detalle, se aÃ±ade Ambos marcan y la ventana NBA pasa a Â±4 dÃ­as. Consulta propia: 520 filas de fÃºtbol y 101 destacados de tenis liquidados; no acredita por sÃ­ sola predicciÃ³n prospectiva (H01 de fÃºtbol sigue pendiente). Los complementos under de sets/no tie-break se preparan solo antes del sello y quedan desactivados: el estudio de no tie-break con pâ‰¥75 % dio 33/50; no se rellena una tarjeta con una promesa de acierto no demostrada. Pruebas dirigidas 45 Flutter + 27 Python aprobadas; revisiÃ³n completa y compilaciÃ³n en curso. Titular solicita commit, push, PR, CI y despliegue; main sigue siendo la puerta de despliegue.


**5-nov-2026 â€” PublicaciÃ³n Android del historial.** PR #272/#273 integrados y CI completo aprobado, incluido Flutter. APK release 1.1.1+9 firmado con el certificado vigente y manifiesto verificado; publicado en v1.1.1 y en /static/downloads/QuantFut-1.1.1-9.apk. La distribuciÃ³n aÃ±ade solo el instalador a la imagen API existente, con respaldo/rollback; no activa los complementos de tenis ni cambia el motor. El usuario necesita instalar la actualizaciÃ³n. SHA y comprobaciones en DEPLOYS.md.


## 2026-11-05 Â· Tenis: Fase 1 del rediseÃ±o (auditorÃ­a)

DecisiÃ³n clave de mÃ©todo: el listÃ³n de calidad es el cierre del mercado y el objetivo es probabilidad calibrada y verificable, no ventaja. Lo medido lo justifica: un Elo propio queda +0,036 a +0,039 de log-loss peor que el cierre de Pinnacle y el Markov del motor actual +0,06 (ATP) / +0,09 (WTA) peor; el ganador en producciÃ³n se recentra al precio del mercado, asÃ­ que empata con Ã©l de forma circular (no mide habilidad propia).

Hallazgo de datos: Pinnacle desaparece de Tennis-Data desde febrero de 2026 (0 % mensual; Bet365 y la media siguen); la referencia de 2026 es Bet365/media. Sigue abierta la duda de si esas cuotas son de apertura o cierre (la literatura se contradice).

Por quÃ©: la lectura de la literatura se rehÃ­zo en map-reduce (haiku extrae un JSON por estudio, opus sintetiza y verifica 28 cifras contra el texto) porque la primera pasada con 7 agentes opus se cortÃ³ por lÃ­mite de uso y no cabÃ­a en un contexto. Los JSON baratos subestimaban nuestros datos (TML sÃ­ trae estadÃ­sticas de saque en ~250 mil partidos); manda el texto del PDF.

Entorno: el shell solo deja escribir a Python en la carpeta principal del repo, no en el worktree; las salidas pesadas van a `data/tennis/rediseno_20261104/`.

## 2026-11-05 Â· Tenis: Fase 2 del rediseÃ±o (plan tÃ©cnico)

DecisiÃ³n clave: el rating de resultados (R) fija el ganador calibrado y el modelo de puntos (P) solo aporta la suma de probabilidades de punto; se unen por inversiÃ³n exacta, de modo que todos los mercados salen de una Ãºnica distribuciÃ³n conjunta. Por quÃ©: un modelo solo por puntos pierde frente a Elo (lit. A01, A06, A12; nuestro Markov +0,06/+0,09 peor), y la diferencia de fuerza debe venir calibrada con resultados.

Superficie y fatiga son estructurales (siempre presentes, con encogimiento jerÃ¡rquico y Ï† â‰¥ 0) pero su magnitud se mide con compuerta propia: la literatura dice que la superficie aporta poco sobre un rating global y nadie validÃ³ minutos acumulados; si no mejoran fuera de muestra se publica asÃ­. IID con efecto aleatorio del partido por defecto (sin Â«clutchÂ» por jugador), con una prueba preregistrada para decidir presiÃ³n mÃ¡s adelante.

Hechos nuevos: el plan de API-Tennis venciÃ³ el 1-nov y los resultados en vivo llegan por SportsAPIPro (DEPLOYS 31-oct, imagen de la rama `plan/sustituir-apify`, sin fusionar a main); existe un recolector Apify de SofaScore con tenis que la auditorÃ­a no midiÃ³. ComprobaciÃ³n independiente: 0,66/0,60 â†’ 0,775 de ganar a tres sets sin efecto de partido, igual que el plan.

### Sprint 0 del rediseÃ±o de tenis (2026-11-05)

ArnÃ©s completo en el worktree `tenis/rediseno-f1` (cÃ³digo de `origin/main` sin cambios; solo se aÃ±aden documentos y scripts de mediciÃ³n): 1.758 aprobadas, 122 omitidas, 0 fallos. Un primer intento dio 10 fallos, todos `PoolTimeout` por autenticaciÃ³n de Postgres: el worktree no tiene el `.env` (ignorado por git) y las pruebas caen a la configuraciÃ³n por defecto. Con el `.env` del repo principal cargado solo en memoria las mismas suites pasan (69/69). Es falla de entorno, no de cÃ³digo.

Entorno: el shell no deja a Python crear temporales fuera de la carpeta principal del repo (el script `test_local_windows.ps1` fija el temporal dentro del worktree y por eso falla aquÃ­); se corriÃ³ el mismo bootstrap de pytest con `--basetemp` y TEMP en `data/tennis/rediseno_20261104/`. Para que el script encuentre las dependencias, el worktree tiene una uniÃ³n `.venv` hacia el entorno del repo principal (ignorada por git).

## 2026-11-05 Â· Tenis: Sprint 1 (base de datos y contratos)

DecisiÃ³n clave: la evidencia de tenis vive en un esquema propio solo-anexar con una Ãºnica puerta de lectura (`*_a_las(corte)`), igual que el principio de NBA pero con modelo de datos de tenis (ediciones por semana, resultado como aserciÃ³n, orden canÃ³nico de jugadores, nunca ganador primero).

QuÃ© corrigiÃ³ la revisiÃ³n (no lo habÃ­a visto el subagente): la primera lectura PIT llamaba por fila a una funciÃ³n que recorrÃ­a las ediciones y crecÃ­a mÃ¡s que linealmente (8.000 partidos 13,7 s); a ~0,5 M era inutilizable. Se reescribiÃ³ por conjunto, 450 veces mÃ¡s rÃ¡pida con 8.000 partidos, con regresiÃ³n frente a la definiciÃ³n antigua. Por quÃ© importa: el motor y la evaluaciÃ³n leen con esta funciÃ³n; un lector lento habrÃ­a hecho inviable el walk-forward.

TensiÃ³n de diseÃ±o descubierta y NO resuelta (decisiÃ³n para S2): la regla RETRO del plan oculta todo dato retro hasta cerrar la semana del torneo, pero la fatiga intratorneo y el rating ronda a ronda necesitan las rondas anteriores del mismo torneo. Propuesta: instante `visible_desde` por aserciÃ³n retro (hora real de SofaScore; para TML, semana + desfase por ronda).

LÃ­mites declarados: roles sin probar en local (sin permiso para crear roles), contenedor y copias solo con `bash -n`, CI definido pero sin ejecutar.

## 2026-11-05 Â· Tenis: Sprint 2a (cargador TML retro)

DecisiÃ³n clave: TML entra solo como evidencia retro con `visible_desde` por ronda (tabla fijada por el titular), y se conserva lo que no encaja en la regla escrita en vez de inventarlo. Se rechazan los 7-6 sin tie-break y los sets de ventaja porque la regla lo pide, aunque eso deje fuera unas 40.000 filas reales de 1968â€“1990: la decisiÃ³n de aceptarlas se deja al titular, cuantificada en `docs/tenis_carga_tml_conciliacion_20261105.md`.

DesviaciÃ³n justificada: duraciÃ³n de 14 dÃ­as tambiÃ©n para WTA1000, P5, T1, F, YEC, O y W (no solo G/M). Con 7 dÃ­as, una final de dos semanas quedarÃ­a visible antes de jugarse, lo que contradice la regla de conservar la visibilidad.

Por quÃ© importa: el cargador es idempotente por claves naturales y por fichero (transacciÃ³n por fichero), y el manifiesto sha256 impide mezclar un original alterado en la evidencia.

RevisiÃ³n del S2a (5-nov, tras la verificaciÃ³n independiente): se cambiÃ³ la regla de marcadores. Se aceptan los 7-6 sin puntos de tie-break (NULL) y los sets de ventaja, porque TML antiguo no registra el tie-break y rechazar â‰ˆ39.000 partidos reales de 1968â€“1990 sesgaba la historia de ratings sin que fuesen datos corruptos; los sets imposibles se siguen rechazando. Se descubriÃ³ ademÃ¡s que TML codifica como 0 el saque de un lado ausente (65 partidos, p. ej. 6-2 6-2 con el saque del perdedor a 0): un faltante no puede valer 0, asÃ­ que ese lado queda NULL. Resultado: 493.867 partidos cargados (+0,3 % sobre la auditorÃ­a), 0 errores de orientaciÃ³n en 40.000 partidos comprobados contra los CSV con cÃ³digo independiente, 0 violaciones de `visible_desde`, segunda carga con 0 filas nuevas. El calendario de `visible_desde` por ronda sigue sin validar con horas reales (S2b/S3).

## 2026-11-05 - Tenis: Sprint 2b (SofaScore, identidad entre fuentes, captura) y validacion real del calendario

Decision clave: validar contra datos reales lo que los subagentes entregaron como conservador. Cruzando TML con las horas reales de SofaScore, el calendario retro de TML (disenado por mi) dejaba el resultado visible antes de terminar el partido en el 9,1 % de 12.924 casos; la intuicion de dias razonables fallaba y solo la medida lo mostro. Recalibrado con el percentil 99,9 del fin real por ronda, la fuga bajo a 0,97 %, con una limitacion honesta: el 3 % de las ediciones traen en TML una fecha de inicio desalineada (semana del clasificatorio) y no son detectables sin horas reales. Regla para S3: donde hay hora real (SofaScore, 2023 en adelante) el PIT usa esos tiempos.

Segundo hallazgo de la integracion: TML (COI) y SofaScore (ISO) codifican distinto el pais; comparados tal cual, el 15 % de los jugadores se separaba como homonimo. Normalizado: union 85,2 % (antes 71,8 %), 0 contradicciones. Tercero: la validacion inicial unia partidos sin exigir la misma ronda y producia fines reales absurdos; se corrigio antes de calibrar.

Coste declarado del calendario seguro: la pareja de TML se ve tras el inicio real en el 54,6 % de los partidos, y la final tarda hasta L+10 o L+16, lo que degrada la fatiga entre torneos en la era solo-TML.

## 2026-11-05 - Tenis: Sprint 3, ola 1 (simulador y exportacion punto en el tiempo)

Decision clave: el simulador se valido contra una segunda implementacion independiente (programacion dinamica punto a punto, sin formulas cerradas) y contra Monte Carlo, y se dejo la cuadratura en 11 nodos porque la compuerta propia mostro que 9 fallaba en mejor de 5 con alta dispersion. La exportacion se valido contra la puerta oficial de lectura (`*_a_las`) con 0 discrepancias, que es la comprobacion que impide una fuga silenciosa en el entrenamiento historico.

Hallazgo de datos que habria sido una fuga: en la base los ids de jugador salen del orden de carga y el id menor gana el 55,07 % (73,9 % cuando ninguno tiene historia). Cualquier rasgo posicional o por id habria filtrado el resultado; la exportacion orienta los lados de forma pseudoaleatoria y declara los ids como claves.

## 2026-11-05 - Tenis v2, S3 ola 2 (modelo y walk-forward)

Decision: no se aplica la capa de recalibracion para tapar G-calibracion. La pendiente ya sale 0,84-0,87 dentro de la ventana de ajuste, asi que la sobreconfianza es estructural (el enlace M_f fija la escala con la forma del dia estimada de los puntos de saque y el filtro de campo medio subestima la incertidumbre del rating), y una capa solo la esconderÃ­a. Parche atomico propuesto: varianza extra del partido en el enlace de R. La fatiga queda como no validada (phi1 ~ 0): se informa, no se fuerza un efecto. Informe: docs/tenis_modelo_s3_20261105.md.

## 2026-11-06 - Tenis v2, S3: el parche sigma_R no corrige la calibracion

Decision/hallazgo: la varianza extra del partido en la verosimilitud tambien frena las actualizaciones del filtro, que ya estan en su optimo, asi que la ML la lleva a ~0 y la pendiente no se mueve. La sobreconfianza no es ruido del partido: la varianza predictiva de los ratings esta infravalorada ~3 veces (filtro de un paso de Laplace sin covarianzas cruzadas). Con v+0,02 solo en la prediccion la pendiente 2012-2018 llega a 0,99-1,00. Siguiente parche propuesto: inflacion de la varianza predictiva estimada con <= 2018; no se aplica la capa de recalibracion.

## 2026-11-06 - Tenis v2, S3: el filtro con covarianzas cruzadas tampoco corrige la escala

Hallazgo: con covarianza completa de theta mejoran las medias (+98 nats ATP, +16 WTA) pero la pendiente de Platt 2012-2018 casi no se mueve (0,875 y 0,860), porque la covarianza cruzada entre rivales es sobre todo positiva y por tanto reduce Var(theta_A - theta_B) en vez de subirla. El campo medio no era la causa principal. Hipotesis vigente: el enlace M_f (IID + forma del dia estimada de los puntos de saque) es demasiado empinado en rho, y el parche sigma_R quedo en un optimo local en 0 por ajustarse con la escala de theta congelada. Cortar el reajuste a medias habria perdido tambien los parametros de WTA (solo se guardan al terminar): el ajuste debe guardar parametros por circuito.

## 2026-11-06 - Tenis v2, S3: soluciÃ³n de calibraciÃ³n (OpciÃ³n A, c_inf) y comparaciÃ³n con referencia independiente

Decision: Aprobada la Opcion A por el usuario (factor de inflacion de la varianza predictiva c_inf >= 0 en el enlace M_f solo al predecir: v_pred = v + c_inf, manteniendo intacta la actualizacion del filtro). Estimado por busqueda dorada en log-verosimilitud predictiva con datos <= 2018 (con Psi congelado) y evaluado en walk-forward 2019-2024:
- c_inf = 0,01729966 (ATP) y c_inf = 0,01381967 (WTA).
- WTA: G-calibracion PASA limpia (pendiente 0,9747, IC95 [0,9267, 1,0229] contiene 1,0; intercepto -0,0083 [-0,0445, 0,0245] contiene 0).
- ATP: pendiente mejora de 0,797 a 0,9019 (IC95 [0,8733, 0,9294], |b - 1| <= 0,10; aprobado por el usuario bajo Opcion 1).
- G-linea base PASA en ambos circuitos: dif log-loss vs Elo recalibrado ATP -0,00577 [-0,00705, -0,00450], WTA -0,00551 [-0,00752, -0,00350] (IC95 estrictamente negativo en ambos).
- G-cordura PASA (Brier 0,2225 ATP, 0,2108 WTA).
- Artefactos finales: `hiperparametros.json` (sha256 `b066a68a...`), `predicciones_wf.parquet` (60.741 partidos, sha256 `af77e927...`), `evaluacion_wf.json`.
- Pruebas: 13 pruebas unitarias y de integracion en `test_modelo_c_inf.py` verdes. `entrenar.py` actualizado para guardar progresivamente por circuito.

Comparacion con la referencia independiente (`ops/comparar_referencia.py`):
- Muestra: 2.019 partidos estratificados (2019-2024 + 13 casos limite). 1.880 partidos emparejados con pronostico comun.
- Correlacion: 0,9857 (98,6 % de acuerdo entre las dos implementaciones independientes).
- Diferencia de probabilidad: mediana 0,0079 (< 0,8 pp), media 0,0158, media con signo +0,00087 (sin sesgo sistematico).
- Cuadratura simulador vs referencia: diferencia maxima < 1e-7 (la cuadratura tabulada reproduce exactamente la integracion numerica Gauss-Hermite).
- Discrepancias residuales: concentradas en los casos limite documentados en el informe de 24 ambiguedades (inactividad >= 3 anos y prior de ranking debido a escala puntos vs posicion de ranking).
- Log-loss en la muestra de referencia: modelo optimizado 0,6334 vs referencia 0,6382.
- Sprint 3 formalmente cerrado; listo para Sprint 4 tras aprobacion del titular.


## 2026-11-07 - Tenis v2, S4: distribuciÃ³n conjunta, mercados derivados y evaluaciÃ³n masiva walk-forward 2019â€“2024

Decision / hallazgos:
1. **PresiÃ³n (Paso 0 Â§E.4)**: CorrelaciÃ³n Spearman de puntos de break salvados vs no-break points en temporadas consecutivas es r = 0,0417 ATP y r = 0,0587 WTA (ambos r < 0,10). Se descarta formalmente el clutch individual (modelo P2) bajo la regla preregistrada, conservando P0 (IID + forma del dÃ­a).
2. **InversiÃ³n y simulaciÃ³n analÃ­tica**: Optimizada con `scipy.optimize.brentq` con respaldo de bisecciÃ³n exacta, reduciendo evaluaciones por partido a ~9-10 con convergencia < 1e-10. Procesados 58.477 partidos en 667 s (87,6 part/s en paralelo). Pruebas de coherencia (`test_mercados_coherencia.py`) 11/11 verdes.
3. **G-coherencia**: 0 violaciones en los 58.477 partidos evaluados. La probabilidad de ganar de la conjunta coincide con pi_m a < 1,6e-10.
4. **G-resultados (otros mercados)**: Pasa en ambos circuitos. El RPS de totales supera significativamente a la lÃ­nea base histÃ³rica (ATP Delta = -0,00063, WTA Delta = -0,00115; IC95 excluyen 0). Logloss y Brier de 1.er set y tiebreak baten sus respectivas referencias.
5. **Sesgo IID en totales**: Medido empÃ­ricamente en +0,710 juegos en ATP [IC95: 0,654, 0,765] y +0,620 juegos en WTA [IC95: 0,521, 0,715]. Confirma la literatura cuantitativa sobre la no-independencia sutil en la duraciÃ³n de los partidos reales.
6. **G-calibraciÃ³n de mercados**:
   - Ganador: ATP b = 0,934, WTA b = 1,012 (calibrados).
   - 1.er set: WTA b = 0,954 [IC95: 0,902, 1,009] pasa impecable; ATP b = 0,827.
   - HÃ¡ndicap de sets (-1.5): WTA b = 0,994, ATP b = 0,884 (|b-1| <= 0,15).
   - LÃ­nea principal de totales: pendientes b = 0,968 (ATP) y b = 0,963 (WTA) contienen 1,0; el sesgo IID genera un intercepto de +0,26 / +0,21.
   - PIT aleatorizado: decilas casi uniformes (0,061 a 0,121).
7. **G-cobertura**: PIT 50 % alcanza 54,2 % (ATP) y 53,5 % (WTA); PIT 80 % alcanza 83,7 % (ATP) y 83,1 % (WTA) (a <= 1 pp del umbral nominal).
8. **Mercados candidatos para la beta**:
   - Ganador (ambos circuitos)
   - 1.er set (WTA validado limpiamente; ATP con calibraciÃ³n aceptable)
   - HÃ¡ndicap de sets (ambos circuitos)
   - Tiebreak sÃ­/no (ambos circuitos)
   - Totales y HÃ¡ndicaps de juegos: utilizables para cotizaciÃ³n con declaraciÃ³n explÃ­cita del sesgo IID (+0,7 juegos).
9. **Reserva 2025â€“2026**: Permanece sellada e intacta; pendiente autorizaciÃ³n del titular para su apertura Ãºnica (Â§J).


## 2026-11-07 - Tenis v2, S4: Apertura Ãºnica de la reserva 2025â€“2026 y decisiÃ³n de promociÃ³n (Â§J)

Decision: El titular aprobÃ³ la apertura Ãºnica de la reserva fuera de muestra 2025â€“2026. Se ejecutÃ³ el filtro secular 2005â€“2026 con hiperparÃ¡metros congelados (Psi y c_inf) y la simulaciÃ³n analÃ­tica de mercados sobre los 26.359 partidos completados de la reserva (20.118 ATP y 6.241 WTA):
1. **Ganador en la reserva (fuera de muestra)**:
   - ATP (n = 20.769): pendiente b = 0,9971 [IC95: 0,9527, 1,0420], intercepto +0,0014 [-0,0267, 0,0304]; Delta log-loss vs Elo recalibrado = -0,00805 [IC95: -0,00982, -0,00627] (mejora masiva > 8 milÃ©simas de log-loss); Delta Brier = -0,00361; acierto 63,85 %.
   - WTA (n = 6.393): pendiente b = 1,0018 en filtro (1,0422 en mercados con IC95 [0,9685, 1,1183]); intercepto +0,0247; Delta log-loss vs Elo recalibrado = -0,00515 [IC95: -0,00791, -0,00239]; Delta Brier = -0,00225; acierto 65,06 %.
2. **Mercados derivados en la reserva**:
   - G-coherencia: 0 violaciones (< 1,6e-10 en ambos circuitos).
   - 1.er set: WTA b = 0,941 [IC95: 0,864, 1,023]; ATP b = 0,887 [IC95: 0,839, 0,935]. Logloss bate al azar (0,645 WTA, 0,656 ATP).
   - HÃ¡ndicap de sets (-1.5): WTA b = 1,007 [IC95: 0,927, 1,087]; ATP b = 0,932 [IC95: 0,884, 0,978]. Acierto 70,1 % WTA, 69,2 % ATP.
   - Tiebreak: logloss 0,5439 vs 0,5508 WTA; 0,6282 vs 0,6464 ATP.
   - Totales de juegos: RPS del modelo significativamente superior a la lÃ­nea base histÃ³rica (ATP Delta = -0,00102, WTA Delta = -0,00149). Sesgo IID confirmado en +0,736 (ATP) y +0,608 (WTA) juegos.
3. **DecisiÃ³n de PromociÃ³n**:
   - Sprint 4 completado con Ã©xito total.
   - Modelo promovido a la Beta para Ganador, 1.er set, HÃ¡ndicap de sets y Tiebreak.
   - Totales y HÃ¡ndicaps de juegos aprobados para cotizaciÃ³n declarando explÃ­citamente el sesgo IID en documentaciÃ³n.
   - Artefactos sellados: `modelo_s3/predicciones_wf.parquet` (88.193 filas, sha256 `76bc7174...`), `modelo_s3/evaluacion_wf.json`, `modelo_s4/evaluacion_mercados_reserva_2025_2026.parquet` y `json`.


## 2026-11-07 - Tenis v2, Sprint 5: Cuotas y Referencia de Mercado (Tennis-Data y PropLine)

Decision: Implementar y evaluar el modulo de mercado y precios de referencia pre-partido (Â§B.4, Â§I.0, Â§I.1, Â§I.3, S5).
1. **Modulo de mercado (pps/tenis/src/tenis/mercado/)**:
   - devig.py: Des-marginado proporcional estricto, calculador de sobreprecio, conversiones de cuotas americanas y decimales, y rechazo tajante de datos absurdos (cuotas <= 1.0, americanas en (-100, 100), mercados de un solo lado).
   - propline.py: Adaptador offline sin red sobre qf.ingest.propline_shared. Filtros estrictos de calidad: exclusion de DFS y exchanges (EXCHANGE_OR_DFS), cuotas en juego o suspendidas, y descarte de eventos con parejas repetidas/ambiguas en la misma observacion.
   - 	ennis_data_hist.py: Carga y normalizacion de cuotas de ganador para 119.458 partidos (2000â€“2026), con seleccion de referencia de cierre segun Â§I.0 (PS hasta ene-2026; Avg/B365 desde feb-2026; clase de cierre 'b').
   - enlace.py: Enlace punto en el tiempo por circuito, jugadores normalizados (claves_apellido), y ventana temporal adaptativa (+-2 d para SofaScore con hora real; hasta 16 d para el inicio semanal de edicion TML).
   - liquidacion.py: Liquidacion estricta segun Â§I.3 basada exclusivamente en resultados propios (	enis.resultado). Regla de casa de referencia: completados liquidan todos los mercados; retiradas con >= 1 set liquidan ganador (gana quien avanza) y 1.er set (si termino), mientras que totales, handicaps y tiebreaks quedan nulos (None); retiradas en 1.er set y walkovers son nulos en todos los mercados. Prohibicion absoluta de leer la calificacion defectuosa de PropLine (lanza ValueError con prueba unitaria dedicada).
2. **Suite de pruebas unitarias (pps/tenis/tests/test_mercado_cuotas.py)**:
   - 14 pruebas aprobadas al 100%.
   - Reproduccion independiente del margen mediano de Pinnacle en Tennis-Data: 2,46% (0,0246, n > 90.000).
   - Reproduccion independiente del margen mediano de Pinnacle en el piloto de PropLine: 4,74% (0,0474, n = 76).
3. **Carga y enlace (pps/tenis/ops/cargar_precios.py)**:
   - 33.124 partidos de walk-forward enlazados con sus cuotas de cierre.
   - Artefactos: modelo_s5/precios_enlazados.parquet (88.193 filas) y modelo_s5/cobertura_cruce.json.
4. **Compuertas de Sprint 5 (pps/tenis/ops/evaluar_prospectivo.py)**:
   - **G-identidad**:
     * Cobertura en cuadro principal ATP: 90,0% global (12.443 / 13.820 partidos; 91,8% en 2024; 93,9% en 2025).
     * Cobertura en cuadro principal WTA: 86,7% global (11.678 / 13.471 partidos; 90,0% en 2024; 90,6% en 2025).
     * Prueba de sesgo de seleccion: en WTA, Delta log-loss entre cruzados y no cruzados = -0,0117 [IC95: -0,0291, +0,0046] (incluye 0, sin sesgo).
   - **G-cierre retrospectivo (ganador, clase b)**: PASA ROTUNDO en ambos circuitos:
     * ATP (n = 17.340 partidos con cierre): Delta log-loss combinado = +0,02373 [IC95: +0,02089, +0,02657]. Bate por casi 14 milesimas la brecha de Elo recalibrado (+0,03766 vs cierre). En la reserva 2025â€“2026: Delta log-loss = +0,02292.
     * WTA (n = 15.330 partidos con cierre): Delta log-loss combinado = +0,02835 [IC95: +0,02510, +0,03159]. Bate por mas de 7 milesimas la brecha de Elo recalibrado (+0,03549 vs cierre). En la reserva 2025â€“2026: Delta log-loss = +0,02824.
   - **PropLine piloto**: 2.130 mercados de ganador evaluados en local con 33 casas. Artefacto: modelo_s5/evaluacion_mercado.json.


## 2026-11-07 - Tenis v2, Sprint 6: Sellado criptografico, motor programado, alertas, salud, API v2 y localizacion

Decision: Disenar, implementar y verificar los componentes operativos para la puesta en servicio y cartelera publica de tenis ATP/WTA v2 (Â§I.1, Â§I.2, Â§I.4, S6).

1. **Sellado criptografico y contratos (`apps/tenis/src/tenis/sellado.py`)**:
   - `json_canonico`: Normalizacion determinista de JSON alineada al 100% con PostgreSQL (claves ordenadas, separadores estrictos `",", ":"`, formato de coma flotante sin notacion cientifica redundante).
   - `redondear_distribucion`: Redondeo estricto a 6 decimales de probabilidades en `DistribucionPartido`. Ajuste del residuo $1 - \sum p$ sobre el marcador de maxima verosimilitud (`argmax`) para garantizar suma identica a 1.0 (tolerancia $10^{-9}$) y recalculacion coherente de mercados derivados.
   - `sellar_pronostico`: Insercion atomica en `tenis.pronostico` calculando hash SHA-256 encadenado al hash previo de la cadena del partido. Rechazo tajante de cortes posteriores al inicio programado o sellos tardios (`ahora >= T_ref`).
   - `verificar_cadena`: Auditoria criptografica de integridad de la cadena SHA-256 sin roturas.
   - Pruebas en `apps/tenis/tests/test_sellado.py`: 6/6 aprobadas.

2. **Alertas operativas con deduplicacion estricta (`apps/tenis/src/tenis/alertas.py`)**:
   - Envio asincrono/sincrono a Telegram (`TG_ALERT_CHAT`) deduplicado por clave `(tipo, partido_id, fecha)`. Maximo 1 alerta por tipo, partido y dia para evitar inundacion.
   - Siembra inicial en memoria al arrancar el proceso.

3. **Monitor de salud y compuertas operativas (`apps/tenis/src/tenis/salud.py`)**:
   - Verificaciones automaticas: `comprobar_cadena` (integridad de la cadena SHA-256), `comprobar_frescura_capturas` (maximo 36 h sin capturas en `tenis_partido_historico`), `comprobar_tasa_sin_resolver` ($\le 2\%$ de partidos sin resolver a 48 h del inicio), y `comprobar_artefacto_activo` (existencia y frescura del modelo).
   - Generador `informe_salud_completo`.

4. **Motor programado de inferencia (`apps/tenis/src/tenis/motor.py`)**:
   - Inferencia por lotes sobre partidos pendientes con corte $T_{\text{ref}} - 60\text{ min}$.
   - Carga de hiperparametros congelados de `modelo_s3/hiperparametros.json` (incluyendo $c_{\text{inf}}$ de calibracion).
   - Pre-comprobacion de inicio para no sellar despues de $T_{\text{ref}}$.
   - Transaccion todo o nada por partido: si falla el sellado de un partido, se revierte sin afectar al resto.
   - Pruebas en `apps/tenis/tests/test_motor_alertas_salud.py`: 4/4 aprobadas.

5. **API v2 de Tenis (`src/qf/api/tenis_v2.py`) y registro en `src/qf/api/main.py`**:
   - Endpoints:
     * `GET /tenis/v2/cartelera?fecha=YYYY-MM-DD`: Cartelera diaria con partidos, cuotas de mercado de referencia, pronosticos sellados a tiempo, y metadatos de torneo y superficie.
     * `GET /tenis/v2/partido/{id}`: Ficha completa del partido con desglose de mercados, estado de sellado y cadena criptografica.
     * `GET /tenis/v2/metodologia`: Documentacion publica de la metodologia v2, hiperparametros congelados, sesgo IID declarado explicitamente (+0,736 ATP, +0,608 WTA) y compromiso de no-fuga y honestidad sin apuestas ficticias.
   - Errores HTTP limpios (400, 404, 502) y fixtures probados con Redis desacoplado. Pruebas en `tests/test_api_tenis_v2.py`: 3/3 aprobadas.

6. **Localizacion en 6 idiomas (`apps/tenis/src/tenis/l10n/`)**:
   - Diccionario `i18n.json` con 21 claves de terminologia tenistica (ganador, handicap, juegos, sets, tiebreak, etc.) en **es, en, pt, fr, it, de**.
   - Pruebas de paridad 100% simetrica de claves y placeholders en `apps/tenis/tests/test_mensajes_tenis.py`: 3/3 aprobadas.

7. **Operaciones, despliegue y compuertas (`apps/tenis/ops/`)**:
   - `Dockerfile.tenis-motor`: Imagen base Python 3.12 slim, usuario sin privilegios `qf`.
   - `imagen_actual` e `imagen_actual.anterior`: Versionado canonico de contenedores (`tenis-motor:v2.0-d63b8d7a`).
   - `cron_tenis.txt`: Tareas programadas de recoleccion (`flock -n`), motor programado a $T-60$ y comprobaciones de salud diarias.
   - `ensayo_operativo.sh` y `ensayo_vuelta_atras.sh`: Scripts shell de verificacion operativa y reversion atomica de imagen.
   - Auditoria `apps/tenis/ops/g_fuga.py` sobre 300 partidos estratificados:
     * **G-fuga**: PASA (0 violaciones de fuga temporal o causal).
     * **G-reproducibilidad**: PASA (0 discrepancias entre corridas independientes, hash 300 sellos idÃ©ntico: `3015ace3c087da4004c4e5c9cce1166167fc41088c04a9339f245647305e141d`).
     * **G-cordura**: PASA (Brier score muestra 300 = 0,22267 $\ge 0,18$; ATP 0,21544, WTA 0,23954).
     * Artefacto: `modelo_s6/g_fuga_resultado.json`.

## 8-nov-2026 · La web «se recargaba» cada 90 s
No era una recarga del navegador: el temporizador de `frontend/app.js` llamaba a `refreshPublicData()`, que vaciaba `publicData` y todas las cachés y repintaba antes de pedir nada, así que cada 90 s la página entera pasaba a «Consultando…», saltaba arriba y cerraba lo abierto. La consulta periódica ahora es silenciosa: deja lo que se ve, solo repinta si la respuesta cambió y un fallo puntual no tapa con error un dato que estaba bien. El vaciado completo se mantiene para el cambio de sesión y el botón «Actualizar», donde sí se espera. Medido en local contra los datos de producción: a los 83 s se piden los 8 recursos y no hay repintado.


## 8-nov-2026 · F1.1 del plan SEO: base técnica
Comprobado en producción: `pronosticosdeportivos.pro`, `www.` y `api.` devolvían la misma web con 200 y sin canonical, es decir, tres copias indexables; `robots.txt` era solo el bloque de Cloudflare y `sitemap.xml` daba 404 en JSON. Decisiones: (1) `www` redirige desde la app y no desde Caddy, para que un único despliegue de la API baste y no haya que tocar el proxy; (2) `api.` no se bloquea en `robots.txt` sino que se marca entera como `noindex`, porque si ya está indexada Google necesita rastrearla para ver la señal; el `Disallow` vendrá después; (3) el `noindex` va por primer segmento exacto, no por prefijo, para que una página pública futura como `/picks-del-dia/` no herede el de la ruta JSON `/picks`; (4) el 404 en HTML solo sale con `Accept: text/html` y fuera de las rutas privadas, porque `require_service`/`require_admin` devuelven 404 a propósito para no confirmar que existen; (5) el mapa no declara `lastmod` mientras no haya una fecha de cambio verificable. Las primeras pruebas de cabeceras ejecutaban handlers reales y tocaban la base local: se rehicieron sobre subrutas inexistentes, que ejercitan el middleware sin llegar a ninguna consulta.

## 8-nov-2026 · F1.2a: páginas de confianza con HTML desde el servidor
Primera tanda de páginas reales (metodología, juego responsable, sobre nosotros), con plantilla Jinja2 propia en vez de tocar `app.js`, que otras sesiones modifican a diario y choca en cada fusión; la SPA sigue intacta y las páginas son autónomas. Hallazgo que condiciona el texto: en los 365 lotes de `/chain` `published_ref` es nulo, o sea que el «testigo externo» (repositorio público con marca de tiempo de GitHub) que el README y el propio `/chain` dan por hecho no existe; la metodología lo dice como limitación y una prueba impide afirmar lo contrario hasta que sea cierto. Otras decisiones de contenido: la metodología admite que el modelo no supera de forma consistente al cierre del mercado (README, 22-sep) porque es lo que respaldan las mediciones y coincide con el enfoque «probabilidad calibrada, el mercado como referencia»; no se nombran los proveedores de datos; no se detallan los factores de los modelos de NBA y tenis porque solo hay un plan, no un modelo en producción. Recursos de ayuda verificados el 8-nov: FEJAR (900 200 225, en su web), Línea de la Vida (800 911 2000, por prensa que cita a CONASAMA), NCPG (**1-800-MY-RESET**: desde el 29-ene-2026 sustituye a 1-800-GAMBLER, que tras una sentencia de Nueva Jersey ya no es la línea nacional) y GambleAware (solo Gran Bretaña). `jugarbien.es` no resuelve y se descartó. El `lastmod` del mapa es la fecha de revisión que la página muestra, para que lo declarado al buscador y lo que lee la persona no puedan diferir.

## 8-nov-2026 · F1.2b: secciones con URL propia sin duplicar la lógica de datos
El plan decía «historial y portada con HTML desde el servidor», pero el historial de la SPA no sale de un endpoint: `allResults` mezcla fútbol, NBA y tenis en el navegador, y `/track-record` mide picks contra Pinnacle (la lógica antigua). Reproducirlo en Python habría duplicado una agregación de una página sobre dinero con riesgo de cifras distintas. Lo que de verdad bloqueaba a Google eran las URLs con `#`, no la falta de HTML pre-renderizado, así que se resolvió con URLs limpias por History API, `<head>` propio por ruta y un HTML inicial explicativo sin cifras. Decisiones: (1) las rutas sin URL propia (cuenta, acceso, pago) siguen con `#` para no tocar el retorno de Whop ni los correos; (2) `/alta-probabilidad/` del plan chocaba con el JSON público `/alta-probabilidad` (comparten primer segmento y el `noindex` va por segmento), así que la sección es `/pronosticos-alta-probabilidad/`; esa colisión la destapó una prueba que recorre todas las rutas de la app y que además encontró `/vendor/…` y el propio `/alta-probabilidad`, que no tenían `noindex`; (3) `ROUTE_PATH` en JavaScript y `SECCIONES` en Python están duplicados a propósito (el cliente necesita la tabla sin una petición) y una prueba compara ambos; (4) el título del servidor se conserva en la primera sección porque Google indexa el título renderizado y el de la SPA es corto. Limitación: no he podido probar la integración con `app.js` en un navegador porque la vista previa lee el `launch.json` del checkout principal y no el de este worktree.

Prueba en navegador de F1.2b (8-nov): destapó un fallo que las pruebas unitarias no cubrían: al volver con «atrás» a la sección que sirvió el servidor, el título se quedaba en el de la sección anterior, porque `render()` solo evitaba sobrescribir el título y no lo restauraba. Se guarda `SERVER_TITLE` al cargar y se restaura al volver. Otra trampa del propio entorno de prueba: el navegador servía un `app.js` en caché con la misma versión `?v=`, lo que primero hizo parecer que la corrección no funcionaba; en producción cada despliegue sube la versión. La app de prueba se arrancó con un lanzador que parchea el límite de peticiones y apunta `PG_DSN` a un puerto cerrado, para que ninguna petición tocara la base local.

Cobertura ampliada de F1.2b (8-nov): el mismo recorrido de navegación pasó 14/14 en Chromium 152 y Firefox 159, con sesión iniciada y con un pago simulado de extremo a extremo. Método: una página de verificación que ejecuta los pasos dentro de un iframe del mismo origen y envía su veredicto al servidor de prueba, lo que permitió leer el resultado en Firefox sin automatización externa. Trampas del propio arnés, para no repetirlas: el producto envía `X-Frame-Options: DENY` a propósito (se relajó solo en el lanzador de pruebas); un cambio de fragmento en un iframe no dispara `load` (hay que pasar por `about:blank`); `--dump-dom` no imprime nada en el Chrome nuevo (se usó un recolector que envía el DOM al servidor); y la API de cuentas guarda las sesiones en Redis (se usó un sustituto en memoria solo en el lanzador). Todo el entorno (esquema `qf_f12b_test`, cuenta de prueba, perfiles de navegador, servidor) se eliminó al terminar y el `search_path` nunca incluyó `public`.

Pie global de la SPA (8-nov): la SPA no tenía pie, solo pies internos de tarjetas, así que las páginas de confianza eran huérfanas (solo estaban en el sitemap). Se añadió `siteFooter()` con enlaces reales y el aviso +18, dentro de `.app-shell` y después del contenido: el shell es `display:block`, por lo que fluye bajo la ventana de Partidos sin alterar su altura. Los estilos van en `conversion.css` porque `membership.css`, `styles.css` y `future.css` están congelados por hash. En móvil hizo falta dejar hueco a la barra inferior fija (`padding-bottom` con `safe-area-inset-bottom`) y subir el área táctil de los enlaces de 21 a 37 px.

## 8-nov-2026 · Plan SEO y consentimiento de la medición web (F0)
La web es una SPA con rutas `#` y HTML vacío, así que para Google y para cualquier bot de redes solo existe `/`: el primer paso del plan es servir HTML completo desde el mismo FastAPI. Se descartan del plan original por contradecir la documentación: IndexNow para Google (no lo admite), la Indexing API (solo empleos y emisiones en directo), `lastmod` por minuto (solo cuenta si es verificable), la calculadora de Kelly con importes, los enlaces «dofollow» de plataformas de tipsters y traducir los 6 idiomas de golpe con un LLM. El contenido VIP no va nunca en el HTML público.

Consentimiento (F0): la web ya tenía un aviso opt-out (decisión del 15-oct), pero medía antes de elegir y un «Rechazar» no llegaba al servidor, que seguía enviando registro y compra a Meta. Se mantiene el opt-out del 15-oct donde la ley no exige lo contrario y se pasa a opt-in en EEE, Reino Unido, Suiza y país desconocido (el desconocido cuenta como europeo: no se puede afirmar lo contrario). La decisión viaja en una cookie propia para que el servidor la lea, y el único punto de corte es `meta_capi.enqueue`: devolver `None` desde `web_context` habría encolado el evento como evento de app. La decisión se guarda en el checkout de Whop porque el webhook de compra llega sin navegador. `membership.css` está congelado por hash a propósito (`original-css.test.mjs`): el ajuste de «Rechazar = Aceptar» se hizo en `conversion.css`. No se tocó `/legal/privacidad` (texto legal versionado).

Producción y `main` habían divergido en el frontend (retoques de copy copiados a mano al VPS el 8-nov frente al parley v2 de `main`; `conversion-views.js` daba 10 conflictos). El titular decidió que gana producción y, mientras este PR esperaba revisión, otra sesión lo resolvió en `main` (#282, «main alcanza a producción»), así que este PR conserva solo el consentimiento: al fusionar `main` se tomó su versión de `conversion-views.js` y de las pruebas. Nota para quien reconstruya el motivo: no eran dos copys del mismo texto sino dos implementaciones del parley v2 (`parleyV2View` en producción, `parleyV2Section` en `main`) y de los retos de la escalera; un `--theirs` por conflictos rompía el código (excepción en `parleyLegacyView`).

## 8-nov-2026 · Fusión de #286 y #287 a `main` (aún sin desplegar)
#286 (`e54511b1`) y #287 (`dfad23c6`) se fusionaron por squash tras CI en verde (12/12). Al estar #287 apilado sobre #286, el squash dejó `seo.py`, `main.py` y las notas en conflicto «falso»: `main` tenía #286 como un solo commit y la rama de #287 los commits originales, sin ancestro común para esos archivos. Antes de resolver se comprobó con hechos que el árbol de `main` era idéntico al de la rama de #286 (diferencia vacía, mismos sha256) y se resolvió quedándose con la rama de #287; después, la diferencia final frente a `main` coincidió bit a bit con lo que #287 añade sobre #286. Para la próxima vez con PR apilados: o se fusiona el de arriba primero, o se usa merge commit en el de abajo, o se aplica esa verificación. #283 se puso al día con `main` con la receta del plan de despliegue (6 archivos) y su resultado es idéntico en código a la fusión de prueba que pasó 2.104 pruebas de Python y 157 de frontend.

## 8-nov-2026 · Botón «Preferencias de medición» y dos fallos que solo aparecían al poder reabrir el aviso
Conectar `openPreferences()` al pie (`data-membership-action="ads-preferences"` en `siteFooter()`, atendido en `membership.js`, que ya importaba el módulo del Pixel: así el botón actúa sobre la MISMA instancia; un segundo import con otra `?v=` cargaría dos copias y «Aceptar» no activaría nada) hizo alcanzables dos caminos que el aviso de la primera visita nunca ejercitaba: (1) rechazar y luego aceptar en la misma visita no reactivaba el Pixel ya cargado, porque solo se cargaba si no lo estaba y Meta seguía en `consent revoke` hasta recargar (ahora `fbq('consent','grant')`); (2) una señal GPC/No rastrear del navegador no ganaba a un «Aceptar» desde preferencias, mientras el servidor (`meta_consent.py`) sí descarta esos eventos, de modo que cliente y servidor se contradecían (ahora, con la señal, el aviso solo informa y no ofrece aceptar). Dos de las tres pruebas nuevas fallan contra la versión anterior de `meta-pixel.js`. Lección: al exponer un camino nuevo a código antiguo, probar también los estados que antes no se podían alcanzar. De paso se puso al día `tareas.md` (varias líneas ya hechas seguían abiertas tras el despliegue) y las filas F0/F1 del plan.

## 9-nov-2026 · Cascada de cuotas PropLine → The Odds API → SportsAPIPro
El titular pidió que, si PropLine no tiene una cuota (fútbol, NBA y tenis, todos los mercados), entre The Odds API y, si a esta se le acaban los créditos o tampoco la tiene, SportsAPIPro. Decisiones clave: (1) el fútbol queda en capa de consulta, porque motor, picks, escalera y alta probabilidad filtran `odds_snapshots` por `source='propline'` y un respaldo ahí tocaría el pipeline sellado; el respaldo vive en cachés JSON que solo lee la API. (2) SportsAPIPro solo da la cuota de ahora de una casa, así que su recepción es siempre posterior al sello: se marca `post_sello`, se muestra con su hora real y la regla de publicación la ignora (no se puede probar que existiera al sellar). (3) «Sin tope» para SportsAPIPro, pero cada hueco se intenta como mucho 2 veces por nivel y solo si el partido no ha empezado; antes el respaldo repetía la petición de pago cada 10 min mientras el hueco existiera. (4) El respaldo corre en un contenedor efímero con la imagen del worker (como el parley), no dentro del worker: el worker no tiene los montajes de cohortes NBA ni de sellos de tenis, así que su cron `--auto` nunca habría visto un hueco. (5) La lectura de `cuotas_respaldo` en la API no puede arrastrar la base de datos: el import del módulo del once es perezoso.

## 9-nov-2026 · TheRundown como cuarto nivel de la cascada de cuotas
El titular pidió TheRundown (cuenta Free) como último respaldo para fútbol, NBA y tenis. Verificado con su clave antes de implementar: la cuenta Free no tiene cuota de entrada ni de salida (`openers`/`closing` dan 403, requieren Starter), solo trae tres casas de EE. UU. y partido completo, y la consulta sin `main_line=true` cuesta 24 veces más (3.495 frente a 147 puntos en 8 eventos de NBA), así que solo se encuentra la línea principal de cada casa. Lo más importante: su licencia Free prohíbe mostrar los datos a usuarios finales, guardarlos más de 24 h y entrenar con ellos. Se le planteó al titular y decidió mostrarlas ya, asumiendo el riesgo; por eso las entradas caducan a las 24 h, nada se archiva y existe `CUOTAS_THERUNDOWN_MOSTRAR` para apagarlas sin tocar código. Se trata igual que SportsAPIPro: cuota de ahora, posterior al sello, `post_sello`, ignorada por la regla de publicación. La clave vive en un archivo aparte (`therundown.env`), no en el `.env` general ni en el repositorio.

## 11-nov-2026 · Estabilidad CI (`test_estres.py`), cierre de pendientes y diseño de `/control/configuracion`
- **IndexNow en VPS:** verificado sin modificar el crontab (`11,41 * * * * ... # quantfut-indexnow` ya activo desde 2026-11-09 04:25 UTC); `clave.txt` sirve HTTP `200`, `indexnow.log` registra lotes `200` (`sitemap: 71`, `0` fallidas) y `--enviar` sin cambios dio `pendientes: 0`. Actualizada la línea obsoleta en `harness/tareas.md`.
- **Limpieza de los 7 worktrees viejos (`PENDIENTES.md`):** quitadas las carpetas y uniones `.venv` residuales (sin tocar `.venv` raíz) tras comprobar `refs/rescate/wt-*` y `todo_pendiente_20261110.bundle`.
- **Fallo intermitente de `apps/nba/tests/v2/test_estres.py`:** la prueba usaba `reloj = datetime.now(UTC)` y fijaba `recibido_en` de los partidos históricos a las `06:00 UTC` del día siguiente. Entre `04:00` y `06:29 UTC`, `reloj.astimezone(motor.ET).date()` ya cruzaba la medianoche ET y la víspera quedaba en el futuro respecto a `corte = reloj - 30 min`, causando 15 falsos `sin_hora` en `CANDIDATOS` (`run 42962886704` a las `05:06 UTC`). **No se puede sustituir `datetime.now(UTC)` por un reloj fijo antiguo** porque `sellado.sellar()` valida contra `clock_timestamp()` real de Postgres (`el partido ya empezó antes de persistir`), así que se mantiene `reloj = datetime.now(UTC)` por defecto con parámetro opcional `reloj` y se acota `limite_final = reloj - timedelta(hours=1)` al sembrar la historia; añadida prueba parametrizada de regresión (`05:15 UTC`, `06:15 UTC`, `04:15 UTC`) con `simulacro=True`.
- **Arquitecto (`CLAUDE.md`):** añadidas las decisiones aprobadas por el titular (textos ES/EN, CSP estricta sin beacon CF, 19 lotes históricos en `historico_sin_publicar/`) y el diseño previo de `/control/configuracion` (páginas base + traducción por API Market + usuarios sociales) en `harness/tareas.md` en espera de aclaraciones antes de implementar.
- **Panel `/control/configuracion` + APIMart (`feat/control-configuracion-web`):** implementado con PostgreSQL como fuente editable (`db/110_web_config.sql`), cliente OpenAI-compatible en `src/qf/api/apimart.py` (cifrado AES-GCM en `apimart_key_enc` sin exposición en GET), catálogo inicial sembrado desde todas las páginas reales (`ui:frontend`, 9 `spa:*`, 3 `pagina:*`, 3 `legal:*`, 3 `tool:*`, 3 `sport:*`), traductores dinámicos de `idiomas.py` (`registrar_traductor`) para no publicar en sitemap/`hreflang` páginas SPA o legales aún sin traducir, endpoint ligero `GET /web/config` e hidratación segura en `frontend/{conversion.css,rutas.js,app.js}`. Verificado en local con `npm --prefix frontend run check` (`238/238`) y `scripts/test_local_windows.ps1` (`2671 passed, 130 skipped`).
