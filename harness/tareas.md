# Backlog — QuantFut

Orden de dependencia (ver "Huecos concretos que quedan" en README.md).
No reordenar sin razón: cada ítem depende del anterior.

## Decisión de alcance (2026-09-21)

El usuario **no usa Telegram**. La venta de picks es 100% en su web propia.
El bot de Telegram y el auth por Telegram quedan fuera de alcance (no se
borran, pero no se desarrollan más). Prioridad actual: la API que sirve
predicciones a la web. Auth de suscriptor no-Telegram y cobros son "después",
no ahora.

**Ampliación NBA (2026-10-03, indicación nueva del usuario):** las señales NBA
se prevén por notificación inmediata de Telegram. Esta excepción corresponde
al diseño de NBA; no activa publicación de fútbol ni reutiliza el canal
operativo como canal de clientes.

## Pendientes 🔴

## App Flutter + Firebase — contenido real y monedas (2026-10-11)

Decisión más reciente del usuario: conectar datos completos reales y omitir el
modo demo; cada sección se podrá activar/desactivar desde configuración backend
con una leyenda de entrenamiento. Las ideas de pantallas recibidas se adaptaron
al calendario, pronósticos, detalle, VIP, Perfil, Monedas y Referidos.

Estado y documentación actual:
`apps/mobile/docs/APP_REAL_MONEDAS_REFERIDOS_20261011.md`.

- [x] Inicio por calendario y hora local con enfrentamientos reales.
- [x] Alta Probabilidad 75–90 %, UNO gratuito por mercado, el de mayor probabilidad (antes 10 % por mejor cuota, cambio 2026-10-12);
  asignación fija por lote y resto VIP sin revelar el contenido protegido.
- [x] Escalera: un solo pendiente gratuito de mayor probabilidad entre todos
  los retos activos; resto VIP. Historial de resultados conservado.
- [x] API móvil, permisos de cuenta, configuración por sección y mensajes
  de entrenamiento; desplegada sin alterar workers de fútbol/NBA.
- [x] Coins: cuarta pestaña directamente a recompensas, sin menú intermedio;
  saldo, asistencia, ofertas y referidos en la misma pantalla. Eliminadas las
  tarjetas de entrada Monedas/Referidos por corrección posterior del usuario.
- [x] Monedas y Referidos; asistencia, saldo, registro de movimientos
  y canje atómico de un pick. Panel de reglas, premios y proveedores.
- [x] Adaptadores RevU y BitLabs con callbacks verificados, deduplicación y
  anulaciones; elección documentada con fuentes oficiales y reseñas.
- [ ] Cuentas de editor aprobadas RevU/BitLabs, IDs públicos y secretos del
  servidor; piloto de ofertas y comprobación comercial de cobros. El usuario
  confirmó que todavía no tiene cuentas: proveedores desactivados.
- [ ] Tapjoy/Unity, ayeT, adjoe y Torox: evaluar tras el piloto e implementar
  únicamente los proveedores adicionales aprobados para la audiencia.
- [ ] Persistencia segura de sesión, firma de distribución y pruebas iOS.

Referencia: `apps/mobile/docs/FIREBASE_INTEGRACION_CON_BACKEND_20261011.md`.

Primer diseño implementado a partir de las referencias del usuario:
`apps/mobile/docs/PANTALLAS_BIENVENIDA_INICIO_VIP_20261011.md`.
Cinco bienvenidas animadas y cinco pestañas inferiores. Este documento conserva
la fase de prototipo anterior; la navegación actual ya consume datos reales.
18 pruebas Flutter aprobadas, análisis limpio y APK Android compilado.

Actualización de mercados: tercera pestaña **Mercados**, con respaldo
retrospectivo separado del historial público guardado; 18 pruebas aprobadas.
Referencia: `apps/mobile/docs/MERCADOS_MODELO_APP_20261011.md`.

- [x] Adaptar tarjeta VIP, ventana de pronóstico con tres pestañas y página VIP
  con rendimiento publicado, comparación de beneficios y botón fijo.
  Detalle: `apps/mobile/docs/DETALLE_PRONOSTICO_Y_VIP_20261011.md`.
- [x] Conectar detalle autorizado: picks, cuotas, probabilidades disponibles,
  H2H, alineaciones y bajas; distinguir datos ausentes de confirmados.
- [x] Pestaña Pronósticos del detalle con el formato de la referencia «Pronósticos IA»:
  pronóstico destacado con cuota y probabilidad, cuatro indicadores (probabilidad,
  xG proyectado, favorito 1X2, tendencia de goles) y dictamen. Solo datos reales;
  Elo, «confianza IA» y briefing de la referencia no se copian. El xG proyectado
  requiere `implied_goals` (ya desplegado) (`src/qf/api/mobile.py`); sin eso muestra «—».
- [x] Pantalla de acceso VIP con el formato de la referencia «AiAD VIP ELITE»
  (cabecera, acierto registrado, beneficios, tres planes, botón dorado). Solo datos
  del servidor: aciertos del historial, planes y precios del catálogo, «mejor
  precio» y equivalente mensual calculados. No se copiaron miembros, reseña, «3
  días gratis», 87,6 % ni «Google Play»: no existen o no están contratados.
  Detalle: `apps/mobile/lib/product/live_vip.dart`.
- [ ] Ampliar contrato para Poisson, marcadores probables y árbitro con fuentes
  existentes; favoritos de cuenta, rachas y notificaciones reales.
- [x] Rediseñar Estadísticas dentro del pick según las seis capturas: resumen
  1X2, forma, radar fl_chart morado/verde con datos disponibles, comparaciones,
  clasificación y cara a cara. Detalle: `apps/mobile/docs/ESTADISTICAS_PICK_20261011.md`.
- [ ] Datos para goles por minuto, disciplina agregada y récords de temporada
  completa; encuestas de aficionados con votos reales y control de duplicados.
- [x] Conectar rendimiento publicado, catálogo de planes y permisos VIP del
  servidor; compra/restauración pendiente de proveedor de pagos.
- [ ] Enlaces FCM y traducciones del detalle.

- [x] Analizar app, backend y documentación oficial; documentar integración.
- [x] Adaptar las primeras pantallas de mercados a las métricas del proyecto,
  sin promover muestras pequeñas o confundir retrospectivo/publicado.
- [ ] Primera pantalla de registro/acceso con Google mediante Firebase,
  marca QuantFut, beneficios con métricas reales, selector de idioma y aceptación
  de términos/privacidad según captura `codex-clipboard-9da919e1-f27f-400b-8c67-6b5038e0fb25.png`.
  Registro antes de las bienvenidas/contenido para personas sin sesión; restaurar
  sesión existente y vincular permisos/saldo del backend. **Solo plan registrado:
  el usuario pidió no ejecutar todavía.** Detalle y aceptación en el plan Firebase.
- [ ] Idioma en la primera pantalla de registro, antes de la bienvenida:
  español, inglés, portugués, francés,
  italiano y alemán; persistir preferencia y cambio desde Perfil.
- [ ] Localización completa Flutter y contratos backend: textos, errores,
  descripciones de mercados, formatos y preferencia sincronizada app/web.
- [ ] Firebase en el idioma elegido: Auth/correos, FCM/bandeja, preferencias
  por instalación y medición; evitar avisos duplicados por idioma.
  Detalle: `apps/mobile/docs/IDIOMAS_APP_BACKEND_FIREBASE_20261011.md`.
- [x] Fase 0: recibir ideas de pantallas, contrastarlas con fútbol/NBA y web,
  proponer mejoras y acordar navegación y alcance de la primera versión.
- [ ] Convertir el diseño acordado en fases con entregables y criterios de
  aceptación: base Firebase, identidad compartida, contenido real, avisos,
  medición/control, cobros y lanzamiento.
- [ ] Implementar las fases según sus dependencias y validar cada entrega.

Estado actual: integración real autorizada y desplegada. Firebase, traducciones,
notificaciones y cobros siguen pendientes; las secciones sin integración muestran
su estado real. No sustituir información ausente por ejemplos de producción.

## Parley del día (2026-10-11, pedido del usuario)

Pestaña "Parley" en Fútbol con historial: cada día, 1-5 parlays de cuota
1,90-5,00 por escalones (≈2,0 · 2,5 · 3,0 · 4,0 · 5,0), en cada uno la
combinación MÁS PROBABLE de todos los mercados; un partido por parlay y
ninguno repetido en el día; solo probabilidad (sin filtro de valor, decisión
del usuario: pierde el margen en cada pata y el historial lo enseña). Diseño:
`docs/superpowers/specs/2026-10-11-parley-design.md`.

1. [x] Especificación aprobada y plan detallado:
   `docs/superpowers/plans/2026-10-11-parley.md` (ejecución nativa).
2. [x] `db/053_parley.sql` (tickets, patas con hora original, resultados).
3. [x] `publish/parley.py`: escalones, filtro, mochila sobre ln(cuota) sin poda
   de dominadas, liquidación, control. Fuerza bruta en tests; 4,5 s con 60
   partidos × 8 patas.
4. [x] `publish/parley_datos.py`: elegir (una transacción con candado por
   día), liquidar (nula a las 48 h de la hora ORIGINAL), informe.
5. [x] Enganches: `daily.run` antes de `seal()`, `_collect` desde
   `LOTE_PARLEY_DESDE`, `clv.settle_pending`, `PARLEY_ENABLED`, alerta.
6. [x] Control prometido/real por escalón (50, 10 semanas, IC99, z ≤ −4).
7. [x] `GET /parley` y pestaña web. Revisión final independiente: 4 fallos
   importantes arreglados con test (commit 059372a).
8. [x] Desplegado APAGADO 2026-10-12 00:10 UTC (commit d28af15,
   `LOTE_PARLEY_DESDE` = 12-oct): db/053 aplicada (triggers probados en real
   con ROLLBACK), imágenes = las de producción (`*:before-parley`, con la app
   móvil sin commitear) + SOLO los archivos del parley; los cambios de
   tarjetas/córners del 10-oct siguen sin desplegar. Respaldo
   `~/release-parley/antes.dump`. Ensayo en seco: 5 parlays de 2 patas
   (1,90 · 2,22 · 2,76 · 3,41 · 4,42) con 26 partidos.
9. [ ] Activar: `PARLEY_ENABLED=1` en `.env` y recrear `worker` fuera de
   07:50-08:40 UTC, con el visto bueno del usuario.

## Modelo propio en las 12 ligas "solo sharp" (2026-10-11, pedido del usuario)

"Activa todas esas ligas en el modelo propio": Championship, LaLiga 2,
2. Bundesliga, Serie B, Ligue 2, Eliteserien, Allsvenskan, Superliga danesa,
Super League suiza, Süper Lig, Primera chilena y Série B brasileña. Hoy tienen
`model_enabled = FALSE` y su historial empieza en jul-ago 2026 (57-106
partidos): el modelo no puede valorar a sus equipos ni a los recién
ascendidos de Primera (Racing y Deportivo 7 partidos, Troyes 5).

Riesgos encontrados antes de tocar nada:
- `history_fd._ensure_team` solo busca el club en la liga que carga: el
  historial de Segunda crearía un segundo Racing, Leeds, Troyes… y partiría
  su historial en dos sin error. Hay que resolver como `resolve_or_register`
  (alias del país, hermanas exactas, dudosos a revisión, nunca crear sobre
  un parecido).
- `model_enabled` también decide qué se paga a los proveedores: The Odds API
  pasaría de `h2h` (1 crédito) a 3 mercados en 12 ligas; lineups, bajas y
  estadísticas por jugador gastan API-Football. Separarlo ANTES de activar.
- Al cargar Segunda, los clubes que subieron/bajaron conectan las divisiones
  por el término `strength`: CAMBIA la valoración de equipos de Primera ya
  medidos. Es lo buscado, pero exige validar que no empeora (la puerta de
  RPS de `train` lo hace) y comparar por liga contra el mercado.
- Chile y Série B no están en football-data: historial desde API-Football.

Plan:
1. [x] Catálogo football-data (db/049): E1, SP2, D2, I2, F2, T1 (principal;
   cierre de Pinnacle y estadísticas) y NOR, SWE, DNK, SWZ (extra). Chile
   fuera: `new/CHL.csv` redirige a la Superliga china.
2. [x] Cargador sin duplicados (`normalize.clasificar_historial`, alias del
   país + exacto de cualquier fuente, dudosos a revisión) + `csv_ajeno`
   (CSV de otra liga) + lectura UTF-8 + `history_fd ensayo|cargar`. Tests.
3. [x] Ensayo en el servidor y revisión a mano: db/050 (fusión del
   "Arminia Bielefeld" duplicado, 25 alias, 61 clubes que solo se parecen) y
   db/051 (91 clubes sin parecido creados antes de cargar). Ensayo final:
   0 nuevos, 0 dudosos.
4. [x] Carga real (2026-10-11, respaldos `~/release-ligas-modelo/*.dump`):
   39.842 partidos, 0 equipos creados, 0 duplicados, ~93 % con cierre de
   Pinnacle. Racing 7 → 259 partidos, Troyes 5 → 442.
5. [x] `leagues.captura_completa` (db/052) separa el gasto de proveedores
   de `model_enabled`; `train --incluir` entrena con ligas aún apagadas;
   el chequeo de xG ignora ligas sin fuente. Desplegado 2026-10-11
   (imágenes `*:before-ligas`, respaldo `~/release-ligas-modelo/backup.tgz`):
   sin cambio de comportamiento mientras `model_enabled` siga apagado.
6. [x] Sombra (mismo año que el OOS del 2026-10-01, 486 min): ligas ya
   medidas RPS 0,20800 → 0,20752 en los mismos 4.106 partidos (mejoran
   Bundesliga, LaLiga, Ligue 1: las de ascendidos; Eredivisie 0,1983 →
   0,1994). Nuevas: modelo 0,2208 frente a mercado 0,2116 (gana en Ligue 2,
   Eliteserien y Suiza). Visto bueno del usuario el 2026-10-11.
7. [ ] Activar. Intento del 2026-10-11 (`~/release-ligas-modelo/activar.sh`,
   9 h 40 min): artefacto `2026.10.11-135412` NO promovido, "no mejora el
   baseline Elo sobre las mismas filas" (Dixon-Coles 0,20517 frente a Elo
   0,20468, mercado 0,19928, n=1.541). No es por las ligas nuevas: el
   entrenamiento del 2026-10-01 SIN ellas ya falló igual (0,20074 frente a
   0,19995) y el activo (09-27) pasó por 0,0002. `model_enabled` sigue
   apagado; decisión del usuario pendiente (forzar la activación saltándose
   la puerta, o investigar antes por qué Dixon-Coles ya no gana a Elo).
8. [ ] Chile y Série B: sin football-data; historial por API-Football
   (temporadas pasadas con `fixtures.ingest_league(season=…)`), pasos 2-7.

## Reto escalera (2026-10-08, pedido del usuario)

Sección nueva de la web con historial y ganancias propios. Regla del texto
del usuario (cuota 1,25-1,40, 5-7 pasos, retirar la inversión al llegar a
×2,5, sin prisa), mejorada con lo medido:
- Histórico (football-data, 7 ligas, 2019-2025, bet365/1xBet): en 1,25-1,40
  la probabilidad real es 72,6 % y se acierta 74,3 % (calibrado), pero cada
  escalón pierde −3,4 % de EV. La escalera de 6 de la regla del texto se
  completa el 15,7 % y pierde −23,7 % por reto (−19,2 % con freeroll).
- En vivo desde el 24-sep: 20 candidatos en rango, EV medio −2,0 %; 4 con
  cuota ≥ precio justo (Betano/1xBet, 1X2).
- Mejora: probabilidad real de Pinnacle sin margen (no la implícita), solo
  escalones con cuota ≥ justa (EV ≥ 0) en las casas de la lista, 6 pasos,
  freeroll a ×2,5, un escalón al día y ninguno si no hay candidato.

- [x] `db/045_escalera.sql`: retos, pasos y resultados inmutables; el estado
      se deriva, no se actualiza.
- [x] `publish/escalera.py` (regla y máquina de estados) +
      `publish/escalera_datos.py` (elegir antes de sellar, liquidar, informe).
- [x] Bloque `escalera` en el lote sellado (`LOTE_ESCALERA_DESDE`), paso en
      `daily` antes de `seal()`, liquidación en `clv.settle_pending`.
- [x] `GET /escalera` y pestaña «Reto escalera» en la web.
- [x] `eval/escalera_prueba.py`: la comparación histórica, reproducible.
- [x] Retos de 3 a 6 escalones, varios a la vez: 3 por defecto, 6 como
      mucho 3 al mes, 4 y 5 si ya hay uno abierto (decisión del usuario,
      2026-10-08). `escalera.planificar` / `longitud_nuevo`.
- [x] Hándicap asiático (−1 a +2, enteras y medias) tras pasar la prueba
      `eval/escalera_handicap.py`; −1,5 fuera.
- [x] Desplegado 2026-10-08 21:08 UTC (commit 37aa902): `db/045`,
      `LOTE_ESCALERA_DESDE = 2026-10-09`, `ESCALERA_ENABLED=1`, api y worker.
- [ ] Revisar el primer sellado con escalera (09-oct, 08:00 UTC): reto creado,
      escalón en el lote y visible en `/escalera`.

## Escalera por probabilidad con córners, tarjetas, goles y ambos anotan (2026-10-08, decisión del usuario)

El usuario cambia la regla: la escalera elige el pronóstico MÁS PROBABLE entre
cuotas 1,25-1,40, sin filtro de valor ("saldrían pocas"), y suma córners,
tarjetas amarillas (con el árbitro), goles y ambos anotan. Sin peticiones
nuevas para árbitros/tarjetas históricas: football-data y lo que ya llega.
Medido antes (escalera_prueba, regla "más probable"): −11,5 % por reto a 3
pasos y −26 % a 6. Se publica igual que antes, con su historial entero.

- [x] `db/046`: amarillas, rojas y árbitro en `matches`; mercados nuevos en
      `escalera_pasos`; `ev_min` NULL (sin filtro).
- [x] Datos: tarjetas y árbitro de football-data (`history_fd tarjetas`) y,
      desde ya, de API-Football en `results`/`fixtures`.
- [x] Modelo estadístico de córners y tarjetas con prueba de calibración:
      córners pasan en 6 líneas; tarjetas solo menos de 6,5.
- [x] Ambos marcan desde el ajuste de goles: "sí" pasa, "no" no.
- [x] Cuotas de bets 8/45/80 de la respuesta de API-Football ya pedida.
- [x] Escalera: el más probable en 1,25-1,40; liquidación de córners/tarjetas.
- [x] Web: textos y regla nueva.
- [x] Desplegado 2026-10-08 23:20 UTC (commit abe3da4) y `history_fd tarjetas`
      ejecutado (27.398 partidos con tarjetas; árbitro en 4.610 de la Premier).

## Tarjetas con árbitro y revisión de líneas con datos completos (2026-10-10, pedido del usuario)

- [x] `eval/tarjetas_arbitro.py`: Premier + Championship con y sin árbitro,
      criterio fijado antes. El árbitro apenas mejora (z=1,07; peor en la
      Premier): sin regla propia para Inglaterra.
- [x] BOM en 9 CSV de football-data: `soft_vs_sharp.load_csvs` perdía la
      columna `Div` y `escalera_estadistica` descartaba 2024/25 y la Premier
      2021/22. Arreglado + test; `--fijos` arreglado (KeyError `corners_equipo`).
- [x] Repetida la prueba de las líneas en producción con datos completos:
      escalera sin más de 6,5 / 9,5 córners ni visitante menos de 7,5, con
      menos de 4,5 / 5,5 tarjetas; alta probabilidad sin local más de 2,5.
- [ ] Desplegar (api + worker), con autorización del usuario.
- [ ] Tarjetas en alta probabilidad: NO por ahora (alta va 71,9 % real frente
      a 82,9 % prometido en sus primeros 57; antes entender eso). Necesitaría
      prueba con los tramos 80-95, migración y liquidación.

## Fase comercial desbloqueada (2026-10-07, decisión del usuario)

El usuario desbloquea cuentas, suscripciones y panel de administración ya,
sin esperar a la puerta de CLV. La puerta sigue decidiendo si hay picks que
vender (`PUBLISH_PICKS_ENABLED`); las cuentas existen aunque esté cerrada.
Un único FastAPI sirve a la web, a la futura app Flutter y al panel.

- [x] `db/043_cuentas.sql`: `accounts`, `plans` (1/3/6 meses + Club),
      `subscriptions` (solo se revocan, nunca se borran), `sessions` con
      rotación de refresh y detección de reuso, `admin_audit` inmutable.
- [x] `/app/v1/*` (`src/qf/api/cuentas.py`): registro, login, refresh,
      logout, `me`, planes y picks según derecho. Bearer opaco de 15 min en
      Redis + refresh de 30 días hasheado en Postgres. Argon2id. OpenAPI
      propio en `/app/v1/openapi.json` para generar el cliente Dart.
      Interruptor `ACCOUNTS_ENABLED` (apagado por defecto: falla cerrado).
- [x] Panel `/control` tipo dashboard (Tabler + Tabler Icons + Chart.js,
      servidos desde el propio dominio): KPIs, usuarios, suscripciones,
      planes, auditoría y la vista de sistema anterior. Acciones
      comerciales con CSRF y auditadas; el pipeline sigue siendo de solo
      lectura desde el panel (no lanza jobs ni publica).
- [ ] Elegir procesador de pago (decisión del usuario) → checkout + webhook
      firmado e idempotente (contrato en `frontend/ACCESS_FLOW.md`).
- [x] Envío de correo con Proton Mail (decisión del usuario, 2026-10-07):
      `comercial/correo.py` por SMTP, `db/044` (enlaces de un solo uso,
      solo su sha256), verificación y restablecimiento en `/app/v1` y
      páginas `/cuenta/*`, botones en el panel. Bridge opcional en Compose.
- [x] Configurar Proton en producción (2026-10-07): DNS completo (SPF,
      DKIM x3, DMARC, MX), token SMTP de `no-responder@` en `.env`, login
      STARTTLS verificado desde el contenedor.
- [x] Conectar la web a `/app/v1` (2026-10-07): `frontend/cuenta-api.js`,
      refresh en cookie HttpOnly, acceso en memoria, sesión recuperada al
      recargar, Mi cuenta con el plan real.
      Desplegado en producción (commit 9b9d180).
- [x] Conectar la app Flutter a `/app/v1` (2026-10-11): cliente Dart con registro,
      login/refresh, perfil, verificación, recuperación y suscripción. Firebase
      y persistencia segura de sesión continúan pendientes.
- [x] Web: precios desde `/app/v1/plans` (2026-10-07). El panel decide
      importe, duración y qué se vende; la web solo guarda los textos.
- [x] Desplegar commit 3d40e05 (2026-10-07): `db/043` y `db/044` aplicados,
      imagen `quantfut-api:3d40e05`, solo `api` recreado.
- [x] Altas abiertas en producción (`ACCOUNTS_ENABLED=1`, 2026-10-07, decisión del usuario).
- [x] `/control` daba 503: `ADMIN_CONSOLE_PASSWORD_HASH` había quedado vacío
      en el `.env` del VPS. Restaurado desde `.env.bak-2026-10-07` con
      permiso del usuario; vuelve a pedir credenciales tras Access.

## NBA 2026-27 — investigación y experimentos (2026-10-03)

- [x] Revisar arquitectura y contrastar literatura académica, doctorados,
      maestrías y el texto aportado. Plan integrado con fuentes, modelos,
      datos, presupuesto y 27 experimentos propuestos E0–E26:
      `docs/nba_2026_27_investigacion_y_plan.md`.
- [x] Contrastar el segundo texto y ampliar el plan con calibración,
      incertidumbre, SBC, conformal online/control de riesgo y Kelly robusto.
      Separar cobertura predictiva, acierto, retorno y ejecución. E21–E26
      son diseños pendientes de ejecución, no estrategias validadas.
- [x] Documentar aislamiento recomendado a petición del usuario:
      `docs/nba_arquitectura_aislada.md`. Aplicación/dependencias/despliegue,
      Postgres/Redis, credenciales, presupuestos y Telegram NBA propios;
      sin imports entre deportes ni refactor inicial de fútbol.
- [x] Revisar crítica operativa de props/Telegram/noticias y acotar MVP:
      `docs/nba_mvp_ejecucion_y_capacidad.md`. Rangos de límites/reacción no
      corroborados se tratan como hipótesis; 27 experimentos siguen como backlog.
- [x] Consolidar plan maestro por fases F0–F9 y registro estructurado:
      `docs/nba_plan_fases_auditable.md` y
      `docs/nba_plan_fases_auditoria.json`. Plan documentado; ninguna fase
      de implementación ni puerta G0–G9 se considera aprobada por escribirlo.
- [x] Revisar viabilidad antes del inicio (4-oct): quedan 16 días al 20-oct.
      Aplicación NBA inexistente y cero ejecuciones registradas. Objetivo
      condicionado: MVP estadístico acotado; priorizar histórico deportivo
      reciente y datos actuales. Sin prometer históricos completos, modelo
      avanzado ni validación comercial para la fecha de apertura.
- [x] Incorporar pretemporada al arranque y revisar preparación del plan:
      `docs/nba_pretemporada_arranque.md`. Captura actual, históricos recientes,
      separación de regímenes y métricas; pruebas no sustituyen F7 regular.
      Plan preparado para iniciar trabajo local; implementación pendiente.
- [x] Contrastar texto adicional sobre CLV, sharp/soft, lesiones y QNN:
      `docs/nba_revision_critica_clv_fuentes.md`. CLV complementario con cierre
      comparable; liderazgo por mercado/latencia observada; minutos separados
      de USG%. Sin garantizar ventaja de props o modelos cuánticos.
- [x] Integrar correcciones en plan maestro NBA 1.1 y registro: CLV complementario, cierre comparable, latencia/linaje, USG y pretemporada. Versiones previas preservadas; fases de implementacion pendientes.
- [ ] **F0 / G0:** alcance, decisiones y protocolo preregistrado. Presupuesto,
      operadores/proveedor y canal de pruebas pendientes de definición.
- [ ] **F1 / G1:** aplicación `apps/nba/`, dependencias/despliegue, Postgres/
      Redis, configuración y recuperación propios. Aplicación/entorno/config
      locales implementados; Postgres/Redis y recuperación aún pendientes.
      Arnés resuelto y verificado; no importar `qf`.
- [ ] **F2 / G2:** cobertura E0, identidad, contratos/reglas, gasto y familia
      prepartido inicial elegida por datos. Puede avanzar con F1 después de F0.
- [ ] **F3 / G3:** ingesta versionada, raw, cuarentena, reconciliación y PIT.
      E18 continúa en todas las fases; referencias/hash y anclaje de evidencia.
- [ ] **F4 / G4:** baselines y distribución de minutos E1, priors encogidos,
      roles/carga y coherencia deportiva; no usar minutos reales como feature.
- [ ] **F5 / G5:** tasa/distribución de estadística, E8 básico, E21 cuando
      proceda y E22/E23 básicos. Candidato y criterios congelados antes del test.
- [ ] **F6 / G6:** Telegram de pruebas, sellado/outbox, caducidad, revalidación,
      disponibilidad E5/E17 y resiliencia E19. Resolución y demoras explícitas.
- [ ] **F7 / G7:** confirmación prospectiva E26 y revisión de promoción propia.
      300 partidos/60 días/3 bloques son piso propuesto, no prueba suficiente
      de ROI. Separar métricas deportivas, simulación y datos informados.
- [ ] **F8 / G8:** challengers de lesiones/rol/oportunidades E2/E3/E7/E8/
      E9/E13. Núcleo F6 y datos suficientes; cada candidato nuevo vuelve a F7.
- [ ] **F9 / G9:** operación evaluada, capacidad/utilidad del producto y
      extensiones a periodos/live/modelos avanzados con validación específica.
      No heredar puertas de fútbol ni operar apuestas/cuentas de clientes.

- [x] **Primer incremento NBA autorizado (4-oct):** entorno independiente,
      fuentes gratuitas, box scores auditados, baseline de minutos/rebotes,
      replay temporal y ledger local. 22 pruebas NBA y 606 de fútbol correctas.
      `docs/nba_arranque_resultados.md`; no aprueba G0–G9 ni activa Telegram.
- [x] **Buscar y descargar repositorios GitHub NBA:** shufinskiy PBP/tiros
      (30 temporadas disponibles, 124 archivos) y hoopR box scores/calendario
      (66 archivos) como complemento a llimllib. Inventario/cobertura en
      `docs/nba_fuentes_github.md`; ausencia de huecos requiere auditoría propia.
- [x] **Auditar fuentes para huecos NBA (5-oct):** 30 Parquet individuales
      SportsDataverse (1996-97 a 2025-26), lesiones con snapshots y muestras
      de props descargados con hashes. Resultados y límites en
      `docs/nba_fuentes_github_huecos_20261005.md`; candidatos no integrados.
- [x] **Integrar históricos NBA (5-oct):** importador SportsDataverse
      2021-22 a 2025-26, fechas/IDs/tipos conciliados, 154.058 registros en
      snapshot propio; minutos dudosos en cuarentena. Replay congelado y
      referencia anterior preservados. `docs/nba_avance_fases_20261005.md`.
- [x] **Captura experimental actual (5-oct):** 30 plantillas ESPN 2026-27,
      606 jugadores, recepción UTC/namespace propios. Lesiones incluidas
      conservadas raw, con auditoría de fechas; no disponibilidad verificada.
- [x] **Experimento de arranque (5-oct):** priors del año anterior para
      primeras diez apariciones observadas, protocolo separado, 8.264 casos
      históricos y escenario 2026-27; abstiene sin prior suficiente. Resultado
      exploratorio, condicional a participación, sin promoción ni publicación.
- [ ] Verificar correspondencias ESPN/NBA y disponibilidad actual; incorporar
      rol/rotación, calibración/abstención y coherencia conjunta de minutos al
      arranque. Rookies y ausencia de datos no se convierten en ceros.
- [ ] Validar lesiones históricas contra PDFs, IDs y corte temporal; muestras
      de props siguen sin contratos/PIT suficientes para ROI o CLV.
- [ ] Recuperar registros en cuarentena contrastando otra fuente; unir IDs
      ESPN→NBA con evidencia y cubrir 2023-24 individual incompleto.
- [ ] Captura gratuita actual con rosters, calendario y disponibilidad PIT;
      contratos/cuotas y destino NBA privado de pruebas siguen pendientes.

## Histórico FotMob (2026-10-03, alcance del usuario)

- [ ] Descargar a archivos locales el histórico del 1-ene-2024 al 3-oct-2026
      de las 23 ligas y Champions/Europa League. Inventariar temporadas reales,
      filtrar partidos terminados y deduplicar por ID de FotMob. Conservar JSON
      comprimido y hora de captura, exportar xG/estadísticas y cobertura por
      competición. Descarga reanudable; detenerse ante denegación de acceso o
      límite del proveedor. Sin escrituras en Postgres ni jobs recurrentes:
      los partidos futuros vendrán de otra API por decisión del usuario.
      **En curso:** inventario completo de 22.461 partidos en 96 temporadas;
      detalles descargándose a `.local/fotmob-history/2024-01-01_2026-10-03/`.
      `coverage.json` indica cuándo termina; no marcar HECHO hasta entonces.

## Ideas de la literatura (2026-10-03, aprobadas por el usuario) — en orden

Cruzadas con lo ya medido (2.D, 2.E): solo entra lo que no se ha probado.

- [x] **HECHO (3-oct) — SIN SEÑAL. 1. ¿Aporta el modelo frente a la cuota
      TEMPRANA de Pinnacle?** Pendiente 0,003 [−0,008, +0,014], 4/7 ligas,
      EV −4,9 % [−5,2, −4,6], `w_model` 0,0001 también contra la temprana.
      Control positivo (media de casas): 0,38 [0,29, 0,46]. Ver progreso.md.
      Planteamiento original:
      `w_model = 0,0001` se midió contra el CIERRE. `history_fd.py` ya lee
      `PSH` (cuota de viernes/martes) pero solo como respaldo del cierre. Se
      mide con los 42 CSV de `.local/fd_cache` (7 ligas, 2019/20-2024/25) y
      las predicciones secuenciales de Kalman (xG incluido), sin tocar
      producción: `python -m qf.eval.early_vs_close`.
      **Regla fijada ANTES de ver resultados.** Prueba principal: pendiente
      de la regresión del movimiento `logit p_cierre − logit p_temprana`
      sobre el desacuerdo `logit p_modelo − logit p_temprana` (no necesita
      resultados, mucho menos ruido que el RPS). "Hay señal" si el IC95 por
      semanas de la pendiente está ENTERO por encima de cero, es positiva en
      ≥4 de 7 ligas y el EV contra el cierre justo de apostar al precio
      temprano de Pinnacle cuando el modelo ve ≥2 % de ventaja tiene el IC95
      entero por encima de cero. Informativas: `w_model` contra la temprana
      (estimado en el 70 % antiguo, RPS en el 30 % reciente) y lo mismo
      contra el cierre como control (debe salir ≈0, como en el README).
- [x] **HECHO (3-oct) — NO SE VALIDA. 2.** RPS 0,21826 → 0,21838 (peor),
      log-loss 1,0516 → 1,0521, 4/11 ligas; el XI simple sobre las mismas
      3.646 filas: 0,21686. Ver progreso.md. Código en el repo
      (`model/masmenos.py`, brazo en `player_value.comparar`); en el servidor
      solo se ejecutó una copia aparte, sin desplegar. La versión exacta con
      `/fixtures/events` NO se hace: dependía de que esta apuntara algo.
      Planteamiento original:
- [ ] **2. Valor del XI por "más-menos" regularizado** (Kharrat, McHale y
      Peña 2020; Hvattum): una sola señal por equipo en vez de las 18 de
      "XI con valor". Con `minutos` de db/035. Brazo más del reentreno
      mensual, nada en producción.
      **Decisiones del usuario (3-oct):** versión APROXIMADA por minutos (el
      diseño del 29-sep la dejaba fuera por no tener el minuto de cada
      cambio; la exacta con `/fixtures/events` queda para después si esta
      apunta algo) y ejecución en el VPS en solo lectura.
      **Diseño fijado ANTES de ver resultados** (`model/masmenos.py`):
      - Por partido, `y` = diferencia de goles local−visitante mezclada con
        la de xG (`xg_blend`, como el modelo) y centrada; fila de diseño
        `+minutos/90` por jugador local y `−minutos/90` por visitante.
        Ridge ponderado por decaimiento (vida media 180 días) con λ = 10
        (un jugador pesa como 10 partidos completos a rating 0). Un solo
        λ: no se prueban variantes sobre la validación.
      - Punto en el tiempo: reajuste cada 7 días solo con partidos
        anteriores; la semana siguiente usa esos ratings.
      - Señal: `{lado}_d_pm` = suma de ratings del XI de hoy − la del XI
        habitual (mismos 5 XI previos y mismo descarte por >3 titulares
        sin minutos que "XI con valor"). Dos señales en total.
      - Brazo `masmenos` en `player_value.comparar`, mismas filas que los
        demás. Se valida solo si pasa las exigencias de siempre Y mejora
        RPS y log-loss del XI simple, como "XI con valor".
- [~] **EN MARCHA (3-oct) — 3A y 3B desplegados; falta la LECTURA.**
      Tras 2-3 fines de semana desde el 9-oct: `python -m qf.eval.latencia`
      en el worker y aplicar la regla de abajo. Vigilar el gasto en
      `rafagas_log`.
- [ ] **3. Latencia de las casas blandas tras moverse Pinnacle** (fase 5):
      qué casa tarda más y si el cliente llega a tiempo. Choca con los
      créditos de The Odds API: elegir partidos.
      **Diagnóstico (3-oct):** hoy no se puede medir. API-Football (Bet365,
      Betano) refresca cada competición de golpe cada varias horas con UNA
      hora para todas las casas: no distingue quién reacciona. The Odds API
      sí da `last_update` por casa y mercado, pero `odds_worker` lo descarta
      y solo captura 6 ventanas por partido. Muestra de la sombra: 184
      ofertas en 28 partidos (Europa vuelve el 9-oct). Casas de los
      clientes medibles por The Odds API: Betsson, Coolbet, William Hill,
      1xBet (no Bet365 ni Betano).
      **Plan propuesto (pendiente de decisión del usuario):**
      - 3A, gratis: db/038 añade `book_updated_at` (nullable) a
        `odds_snapshots` y `odds_worker` guarda el `last_update` del mercado
        (si falta, el de la casa). Con eso, en cada captura se sabe si una
        oferta existe porque la casa blanda no ha reaccionado a un cambio de
        Pinnacle (precio blando más viejo que el último cambio de Pinnacle).
        No toca triggers: es ADD COLUMN, no UPDATE.
      - 3B, con créditos: `ingest/rafagas.py`, solo 1X2 y `bookmakers=`
        (Pinnacle + casas blandas, ≤10 → 1 crédito por llamada y liga),
        cada 5 min entre T-6h y T-15min en las ligas elegidas, a una tabla
        APARTE (`odds_rafagas`) para no tocar ventanas ni sombra, con tope de
        créditos al mes que la detiene. `last_update` da el segundo exacto de
        cada cambio, así que 5 min bastan. ~72 créditos por liga y día de
        partidos.
      - Medida fijada antes: duración de cada oferta (cuota blanda ≥2 % sobre
        el justo de Pinnacle en muestras seguidas) y minutos que tarda cada
        casa en cambiar tras un movimiento de Pinnacle ≥2 puntos de
        probabilidad justa. Se compara con el tiempo que necesita un cliente
        para apostar (dato del usuario).
      **Decisiones del usuario (3-oct):** desplegar 3A; 3B con tope de 3.000
      créditos/mes (`RAFAGAS_MAX_CREDITOS_MES`), ligas Premier, LaLiga y Liga
      MX (`RAFAGAS_LIGAS`); el cliente tarda UNA HORA O MÁS en apostar.
      **Regla de lectura fijada antes** (`python -m qf.eval.latencia`): no se
      lee antes de 200 ofertas clasificables en ≥3 casas. Si menos de la
      mitad de las ofertas de una casa dura ≥60 min, el formato actual
      (pick publicado que el cliente apuesta al rato) no captura la ventaja
      de esa casa y esa casa no debería contar para la puerta; si la mitad o
      más, sí. Las censuradas ≥60 cuentan como largas; las censuradas <60 se
      excluyen.
- [x] **HECHO (3-oct) — SIN SEÑAL. 4.** Con γ elegido en validación: EV
      contra el cierre −3,51 % [−3,78, −3,25], 0/7 ligas; γ fijo de 0 a
      0,8: −3,78 % → −3,46 %, todos con el IC entero bajo cero. La ventaja
      estimada correlaciona −0,10 con el EV real (peor quintil, el de más
      ventaja): la cartera de Sharpe pesaría más lo peor, no se prueba.
      Ver progreso.md. Planteamiento:
- [ ] **4. Decorrelación con el mercado** (Hubáček y Šír, IJF 2023):
      entrenar para discrepar donde el mercado se equivoca. Investigación.
      **Método del artículo (leído el 3-oct, arXiv 2010.12508 §4.5 y §5):**
      pérdida `Σ (t−y)² − γ·Σ (t−m)²`, `y` el resultado, `m` la probabilidad
      del bookmaker; γ ∈ {0, 0,2, …, 1}; NBA 2006-2014 contra el cierre de
      Pinnacle, walk-forward por temporadas; con apuesta uniforme siguen en
      pérdidas para todo γ, con cartera de Sharpe ganan con γ 0,2-0,8.
      **Diseño fijado ANTES de ver resultados** (`eval/decorrelacion.py`,
      solo lectura, local):
      - Mismos 14.110 partidos y Kalman sin futuro del punto 1. `m` = justo
        de Pinnacle TEMPRANO (es contra quien se apuesta).
      - Segunda etapa: softmax lineal sobre la información del modelo (log
        de sus tres probabilidades y log de las dos lambdas), pérdida del
        artículo + L2 1e-3. Sin cuotas como variable (su caso principal).
      - Walk-forward por temporadas: prueba 2021/22-2024/25, entrenando con
        todas las anteriores. γ ∈ {0, 0,2, 0,4, 0,6, 0,8}, elegido para cada
        temporada con la anterior como validación (entrenando con las de
        antes): nunca se elige mirando la prueba.
      - Apuesta uniforme: por partido, la selección de mayor `t·cuota − 1`
        si es > 0, al precio temprano de Pinnacle.
      - "Hay señal" si con el γ elegido el EV contra el cierre justo tiene
        el IC95 por semanas ENTERO por encima de cero y es positivo en ≥4 de
        7 ligas. Con el cierre insesgado, el EV contra el cierre es la misma
        esperanza que el ROI con mucho menos ruido; el ROI se informa.
        Informativo: la tabla de todos los γ y la correlación con el
        mercado. La cartera de Sharpe solo se prueba si lo uniforme apunta
        algo.
- [x] **HECHO y DESPLEGADO (3-oct) — 5.** db/039, `picks.factores()`,
      sombra con `stake_publicado_units` y `factor_incertidumbre`. Factores
      vigentes al desplegar: 1xBet 0,94, Betano 0,71, Betsson 0,65,
      Bet365 0,54, William Hill 0. Planteamiento:
- [ ] **5. Encoger el stake del criterio sharp por la incertidumbre de la
      persistencia** (Baker y McHale 2013; Uhrín y otros 2021). No es lo
      superado en 2.D: aquí la incertidumbre es la del criterio, no la del
      modelo.
      **Medido (3-oct, fd_cache, 2 %, primera oferta por partido):**
      persistencia e IC95 por semanas: 1xBet 0,72 [0,37, 1,06], Interwetten
      0,55, bwin 0,31, BetVictor 0,20, Bet365 0,13 [−0,15, 0,41] (no se
      distingue de cero), William Hill −0,15. Dispersión entre casas 0,31.
      **Decisión del usuario:** "stake sí, muestra no".
      **Diseño fijado antes de implementar:**
      - Factor por casa `k = ρ² / (ρ² + SE²)` (0 si ρ ≤ 0): la aproximación
        de Baker y McHale con la persistencia como única fuente de
        incertidumbre. Se multiplica al Kelly fraccional, que se queda en
        0,20 (es preferencia de riesgo, no estimación).
      - SE previa: 1xBet 0,17, Bet365 0,15, William Hill 0,25 (bootstrap
        por semanas de football-data); casas sin medir 0,31 (dispersión
        entre casas). En vivo, SE de la sombra por el método delta
        (`sd(ev)/(√n·media(edge))`, coincide con el bootstrap) y se mezcla
        con la previa con los MISMOS pesos que `picks.mezclar`.
      - El stake con factor es el que se publica y el que guarda la sombra
        en una columna nueva; qué oferta es publicable se sigue decidiendo
        con el stake SIN factor (`stake_units` de la sombra y
        `stake_kelly_units` del candidato): la muestra de la puerta no
        cambia.

## Auditoría fase 3 (2026-10-03) — pendientes de decisión

- [x] **HECHO (3-oct) — `/matches/{id}` ya no publica `market_consensus`**
      (sigue en `/v1/matches/{id}/predictions`).
- [x] **HECHO (3-oct, opción b del usuario) — los lotes sellados dejan de
      llevar `market_consensus` desde el 3-oct** (`LOTE_SIN_CONSENSO_DESDE`).
      Los anteriores conservan su formato: el del 2-oct regenerado desde la
      base da el mismo JSON que el sellado.
- [x] **HECHO (3-oct) — `/openapi.json` ya no se sirve** (`openapi_url=None`).
- [ ] **ALTA antes de publicar la cadena — el lote lleva también los PICKS,
      de pago incluidos** (`advised_price`, `bookmaker`, `min_price`,
      `fair_prob`). El flujo documentado en `hashchain.py` hace commit del
      JSON a un repo público "antes del primer kickoff": eso regalaría cada
      mañana los picks de pago. Lo habitual es comprometer-revelar: publicar
      solo el `chain_sha256` antes de los partidos y el JSON después del
      último inicio del día. Hoy no pasa (`CHAIN_GIT_REMOTE` vacío).
- [ ] **BAJA — `/model-card` publica rutas internas** (`*_uri` con rutas de
      archivos del servidor). Quitarlas de la respuesta pública.
- [ ] **BAJA — sin `Content-Security-Policy`.** El resto de cabeceras está.
- [ ] **ANTES DE VENDER — avisos legales en la web:** +18, juego
      responsable, privacidad/cookies y términos; no hay ninguno. Y el README
      remite a una sección "Procesadores de pago" que no existe.

## Auditoría 2026-10-03 — mejoras propuestas (pendientes de decisión)

- [x] **HECHO (3-oct, decisión del usuario) — Antelación de la DECISIÓN.**
      `picks.MIN_LEAD` (15 min) la usan la sombra y la publicación real, para
      el precio y para la decisión. La publicación (`find_candidates`) no
      tenía ninguna guarda: el job de las 08:00 habría publicado a T-5 un
      partido de las 08:05.
- [x] **HECHO (3-oct) — Segunda oportunidad del cierre.** Pasada de rescate
      `odds_worker --solo-cierre` a los minutos 5,15,…: dos intentos dentro
      de la ventana 3-12 min, misma vara, 0 créditos si el primero funcionó.
- [ ] **Vigilar 1xBet en la sombra.** Era la casa del valor histórico
      (+2,78% en el backtest, persistencia 0,72); en vivo va −0,2% en 28
      ofertas con cierre. Muestra pequeña: revisar con las europeas.

## Fase 1 — fuentes paradas (encontrado 2026-10-02)

`worldfootballR_data` no actualiza ningún fichero que usamos desde el
18-sep-2025 (ver README, "Corrección (2026-10-02)").

- [x] **HECHO (2-oct, decisión del usuario) — Resultados de copas que
      faltaban (dic-2024 → hoy).** `fixtures --copas-ensayo` y luego
      `--copas 2024-12-13 2024 2025 2026`: 351 partidos (215 UCL, 136 UEL)
      cerrados con marcador y estadísticas, 0 duplicados, 726 peticiones.
      Todo lo no resuelto son clubes de ligas fuera del catálogo; ningún
      equipo dado de alta en copa. Entran en el reentreno del 1-nov.
- [x] **HECHO (2-oct) — Chequeo de frescura del xG** (`check_xg_freshness`).
      Mira el dato, no el job. Las 13 competiciones paradas quedan
      reconocidas hasta el 1-nov-2026; desde entonces alertan cada día.
- [ ] **Fuente de xG reciente — decidir ANTES del 1-nov-2026** (el chequeo
      vuelve a fallar ese día). **Medido el 3-oct: el xG APORTA** (regla
      fijada antes: IC95 entero bajo cero y ≥ mitad de ligas). Ventana
      jul-2023→ene-2025: RPS 0,20154 con xG frente a 0,20440 solo goles,
      delta −0,00287 [−0,00376, −0,00200], 12 de 13 ligas. Es del orden de
      lo que Dixon-Coles saca a Elo y ~40% del hueco con Pinnacle. Hoy
      (xG viejo) aún aporta −0,00055 [−0,00100, −0,00018] y se irá
      apagando con la media vida de 180 días. Siguiente paso: elegir fuente.
      FotMob usa xG de Opta, como FBref: medir antes la coherencia con el xG
      guardado en el solape 2024-25 (correlación y sesgo por liga).
      **3-oct: medido el xG de API-Football** (progreso): mismos valores que
      FBref (corr. 0,96-1,00) pero llega con días/semanas de retraso e
      irregular en Argentina/Liga MX. Usarlo exige revertir la regla del
      README y CLAUDE.md: DECISIÓN DEL USUARIO pendiente.

## Línea de alta probabilidad (2026-10-05, decisión del usuario)

Diseño aprobado: `docs/superpowers/specs/2026-10-05-linea-alta-probabilidad-design.md`.
Pronósticos ≥ 80 % de probabilidad real (Pinnacle sin margen), aparte de los
picks de valor y sin tocar su puerta. Es una línea de acierto, no de valor.

- [x] Paso previo: sincronizar servidor con HEAD (lista de cambios al usuario
      antes de reconstruir).
- [x] Prueba histórica de goles (`eval/alta_prob_calibracion.py`) y fijar
      `MERCADOS_GOLES_HABILITADOS`.
- [x] `db/040`, `publish/alta_prob.py`, sellado en `hashchain`, liquidación.
- [x] `GET /alta-probabilidad`, sección web y estado en `/control`.
- [x] Despliegue con `ALTA_PROB_ENABLED=0` (2026-10-06 18:12 UTC): db/040 aplicada y
      verificada (bordes, UNIQUE, inmutabilidad), ensayo de SQL, verify 8 lotes.
- [ ] Tras el sellado del 7-oct (08:00 UTC): verify y recibo con `n_alta_prob: 0`;
      luego activar `ALTA_PROB_ENABLED=1` con visto bueno del usuario.
- [x] Más goles (2026-10-06): `af_odds` guarda las líneas de goles de la misma
      petición (db/041) y la línea las lee de la misma respuesta. Desplegado
      19:58 UTC; vista previa 9 de 15 partidos (7 de goles, antes 0).
- [ ] Vigilar a las 24 h: filas/día de `af_odds_snapshots` y duración de la
      pasada (hoy 15 s, ~40 filas por partido). Chequeo de frescura de
      `af_odds` en `health.py` (hoy un fallo de escritura solo queda en el log).
- [ ] Antes de configurar `CHAIN_GIT_REMOTE`: el lote lleva `prob` exacta y el
      ajuste de goles (anula el redondeo público). Decidir.

## Más picks sin relajar la puerta comercial (2026-09-25)

Orden experimental solicitado; ningún resultado cambia `publish/picks.py`,
`SOFT_MIN_EDGE_PCT` ni activa `PUBLISH_PICKS_ENABLED` por sí solo.

- [x] Instrumentar en solo lectura primera cuota observada, edad conocida y
      cobertura por fuente, casa y liga (`eval/quote_coverage.py`).
      `first_seen` no equivale a apertura real; The Odds API no conserva aquí
      la hora propia del bookmaker, y se reporta desconocida, nunca cero.
- [ ] Ejecutar esa auditoría en el Postgres operativo y decidir con esos
      datos si merece ampliar la captura más allá de T−72.
- [x] Comparar Shin/Power y umbrales 1–3% sobre las mismas cuotas pre-cierre
      1X2; cierre justo fijo, hash del dataset, muestra por casa e IC agrupado
      por semana (`eval/sharp_challengers.py`). Resultado exploratorio en
      `progreso.md`; no demuestra que las cuotas sigan disponibles.
- [ ] Ensayar un consenso multifuente solo cuando haya snapshots
      sincronizados, horquilla y liquidez verificables.
- [ ] Validar prospectivamente cualquier variante contra el 2% actual en
      sombra: CLV justo, cuota alcanzable, ligas/casas y riesgo. No optimizar
      y certificar sobre los mismos partidos.
- [ ] Reabrir un mercado derivado solo si una nueva muestra con la misma
      línea y cierre sharp contradice el ensayo negativo archivado.
- [ ] Ensayar filtro de acuerdo Dixon-Coles/mercado solo como ablación
      condicional; no subir stakes antes de evidencia incremental.

## Plan de integración web + administración en un solo FastAPI (2026-09-23)

Decisión del usuario posterior al prototipo: avanzar hacia **un backend
FastAPI modular único** para API, web y administración. Esto sustituye la
necesidad de un BFF como segundo servicio, no la separación de permisos:
el navegador nunca verá `SERVICE_TOKEN` ni `ADMIN_TOKEN`.

- [x] Servir el prototipo de `frontend/` desde el FastAPI existente, sin
      cambiar su carácter de demo ni llamar a rutas privadas desde JS.
- [x] Añadir un panel de operación inicial de solo lectura, con autenticación
      humana independiente del token de API y sin credenciales predeterminadas.
- [x] Restringir `/admin` y el panel también en Caddy por IP, como Grafana.
- [x] Probar el aislamiento de rutas y actualizar despliegue/documentación.
- [x] (2026-10-05, pedido del usuario) Tabla en `/control` con los picks que
      se habrían publicado en la sombra sharp (`shadow_sharp.publishable_list`).
- [x] (2026-10-05, pedido del usuario) Probabilidad real de cada pick en la
      web (`fair_prob`, Pinnacle sin margen) y acierto esperado de la lista.
- [ ] Fase comercial posterior: cuentas, sesiones, suscripciones y cobros
      dentro de este mismo backend, solo tras superar la puerta de CLV.

- [x] **API — sin cuentas de usuario, servicio único para el frontend
      (2026-09-22).** El usuario corrigió el alcance más temprano el mismo
      día: la API NO gestiona suscriptores, login ni cobros. Los pronósticos se sirven a un único cliente de confianza — el
      backend de su frontend (BFF) — que es quien maneja usuarios, pagos y
      arma los prompts del LLM. Ni el navegador ni la futura app Flutter le
      hablan a esta API directamente: le hablan al backend del frontend, y
      solo ese backend conoce el secreto de esta API. Motivo: un secreto
      embebido en un cliente que corre en el dispositivo del usuario (JS de
      navegador, binario Flutter) siempre se puede extraer con ingeniería
      inversa; uno que vive solo en un servidor, no.
      - Se revirtió por completo el trabajo de auth de suscriptor de la
        entrada anterior (`db/015_subscriber_auth.sql` eliminado antes de
        aplicarse a ningún Postgres real; `src/qf/api/auth.py` eliminado).
      - `/v1/*` ahora se protege con `require_service` (`X-Service-Token`
        contra `SERVICE_TOKEN` en `.env`, comparación en tiempo constante,
        404 si no coincide — mismo patrón que `require_admin`). Sin recorte
        de tier: quien presenta el token de servicio recibe TODOS los picks;
        el recorte free/paid para cada usuario final lo decide el backend
        del frontend con su propia base de datos, no esta API.
      - `POST /v1/auth/*` (register/login/refresh/logout/telegram)
        eliminados: no hay usuario final que autenticar a nivel de API.
      - Rate limiting por IP se mantiene (`src/qf/api/ratelimit.py`,
        movido desde el `auth.py` eliminado) — sigue haciendo falta aunque no
        haya cuentas: sin él, un service token filtrado permite scraping sin
        límite.
      - `PyJWT`, `argon2-cffi` y `email-validator` se quitaron de
        `requirements.txt`: dependencias que ya no tienen ningún consumidor.
      **Nota para cuando construyas el backend del frontend:** la tabla
      `subscribers` de `db/001_schema.sql` (con `email`, `tier`, `telegram_id`)
      ya no tiene ningún consumidor en esta API — si vas a manejar cuentas de
      pago, esa base de datos vive en tu backend de frontend, no aquí.
- [ ] **API — cobros.** Webhook del procesador de pago → `UPDATE subscribers`.
      Cero código hoy. Pospuesto.
- [x] **API — rate limiting** en las rutas públicas (revisado 2026-09-24).
      Ya existía como middleware global (todas las rutas, 60/min, Redis).
      Dos fallos corregidos: `/control` comparaba su tope de 10 contra el
      MISMO contador que la web y sus estáticos (el panel daba 429 al
      operador), y en IPv6 se contaba por dirección, esquivable rotando dentro
      del /64 del cliente. Ahora `/control` tiene contador propio e IPv6 se
      agrupa por /64. Verificado en producción con una petición IPv6 real.
- [x] **Proxy TLS (Caddy) como servicio de `docker-compose.yml`.** Antes solo
      estaba documentado como paso manual en el host (README). Ahora hay un
      `Caddyfile` en la raíz y un servicio `caddy` que expone 80/443, resuelve
      certificado solo, y proxea `api:8000` / `grafana:3000` por la red interna
      de Compose. Requiere `DOMAIN` y `GRAFANA_ALLOWED_IP` en `.env`
      (`.env.example` actualizado). Grafana sigue cerrado por IP + login.
- [x] **Ingesta de bajas/lesiones.** Decidido 2026-09-22: FUENTE es el
      endpoint `/injuries` de API-Football (mismo proveedor ya contratado,
      plan Pro), no un LLM leyendo prensa — dato ya estructurado, coste
      incremental $0. Implementado en `src/qf/ingest/injuries.py` +
      `db/014_injuries.sql`, en crontab cada 4h. Ver harness/progreso.md.
      **Corregido y desplegado el 2-oct-2026:** hasta entonces no guardó
      NINGUNA baja (comparaba el id de API-Football con el `team_id`
      interno). La muestra point-in-time empieza el 2-oct.
- [ ] **Feature de disponibilidad a partir de bajas.** `injuries.py` solo
      ingiere y almacena, igual que hizo `lineups.py` en su fase inicial.
      Falta un equivalente a `lineups.availability()` que combine bajas +
      XI confirmado en una feature de `residual.py`. Requiere haber
      acumulado datos primero (desde el 2-oct; antes la tabla está vacía).
- [x] **HECHO (2-oct) — Por qué `check_injuries_coverage()` no frenó el
      fallo de bajas.** Saltó cada mañana del 28-sep al 1-oct; el aviso iba a
      Telegram sin token y el log del cron se borraba en cada despliegue.
      Ahora: `health_runs` (db/037), `/var/log` del worker en volumen, alerta
      sin canal como ERROR, HTML escapado y fallo de envío que no tumba el job.
- [x] **HECHO (2-oct) — Bot de alertas de Telegram configurado.** El
      usuario puso `TG_BOT_TOKEN` (@NavyAnalista_bot) en el `.env` del
      servidor; `TG_ALERT_CHAT` es su chat privado. Alerta de prueba enviada
      desde el worker. `TG_CHANNEL_FREE/PAID` siguen vacíos: por Telegram
      solo salen alertas, nunca picks. Si se rota el token, revisar que el
      bot siga teniendo el chat (`getUpdates` tras un `/start`).
- [x] **Vigilancia del hueco de cobertura de `/injuries`.**
      `health.check_injuries_coverage()` detecta si alguna liga acumula
      `INJURIES_MIN_MATCHES` (15) partidos comprobados en 30 días sin NINGUNA
      baja reportada — la misma firma de "array vacío con status 200" que el
      xG. `mx.liga_mx`/`ar.primera`/`pt.primeira` ya confirmadas
      (`KNOWN_INJURY_COVERAGE_GAPS`) no vuelven a alertar cada día; una liga
      NUEVA con el mismo patrón sí dispara el chequeo diario.
- [x] **HECHO (2026-09-29, decisión del usuario: "sí, con límites") —
      Entrenar YA el ajuste por XI con alineaciones históricas.** 4.555 XI
      descargados (11 ligas; copas sin emparejar), 3.988 partidos útiles en
      el último año (se exigen 700). Se entrena en el reentreno mensual del
      1-oct 03:00 UTC: comprobar `val["lineup_challenger"]` (ok, n_fit,
      RPS/log-loss/ECE antes y después, ligas que mejoran) y que la sombra
      muestre `lineup_challenger_available: true` desde el 9-oct. Bloqueo
      medido: el challenger exige 700 partidos con predicción sellada + XI
      capturado antes del inicio; había 4 y 21 (modelo activo desde el
      27-sep, XI desde el 26-sep): llegaría hacia diciembre. Plan:
      1. [x] db/034 `lineups_historicas`, tabla APARTE: ni la sombra ni la
         predicción diaria la leen; solo el entrenamiento/validación del
         challenger. El XI se descarga tras el partido (el publicado a T-60
         casi siempre coincide): esa es la excepción al punto en el tiempo
         que el usuario autorizó, y no va más allá.
      2. [x] `ingest/lineups_historicas.py`: empareja los partidos del último
         año de las ligas con modelo con su fixture de API-Football (por
         `af_team_id` o alias exacto, ±36 h) y baja su XI. Reanudable, con
         reserva de cuota para la operación diaria.
      3. [x] El challenger se entrena con las predicciones fuera de muestra
         que `train.py` YA calcula (walk-forward del último año, ahora con su
         rho) + esos XI, además de los partidos en vivo. Mismas exigencias de
         validación (RPS, log-loss, ECE, ≥2 ligas) y promoción solo con CLV
         en sombra.
      4. [x] La sombra usa el último challenger validado si el del modelo
         activo no existe (un reentreno no promovido dejaba el brazo sin
         artefacto).
- [ ] **Fuerza por jugador (diseño aprobado 2026-09-29,
      `docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md`).**
      - [x] Fase A, datos (plan `docs/superpowers/plans/2026-09-29-fuerza-por-jugador-fase-a-datos.md`):
        db/035, `ingest/estadisticas_jugador.py`, captura al cerrar en
        `results.py`. Histórico descargado el 30-sep: 4.556 partidos, 141.458
        filas de jugador, 11 partidos sin datos.
      - [x] Fase B1, valores y comparación offline (plan
        `docs/superpowers/plans/2026-09-30-fuerza-por-jugador-fase-b1-valores.md`),
        hecha el 1-oct. "XI con valor" EMPEORA a la base (RPS 0,21818 →
        0,21912) y no gana al XI simple: no se valida. La comparación queda
        en el reentreno mensual (`val["player_value"]`) por si la muestra
        cambia la lectura.
      - [ ] ~~Fase B2, sombra en vivo~~ DESCARTADA mientras el reentreno
        mensual no muestre `player_value.valor.gana_al_simple = true`.
- [x] **HECHO (1-oct, decisión del usuario: opción B) — criterio de ECE
      del XI.** Ahora la calibración no puede empeorar más allá de su propio
      ruido (remuestreo pareado). El XI simple del reentreno del 1-oct queda
      validado y la sombra lo usa desde el 9-oct (vuelta de las ligas).
      Comprobar entonces `lineup_challenger_available: true` y que se
      registren los cuatro brazos; nada se publica sin CLV en sombra.
- [x] **HECHO (2-oct, decisión del usuario) — historia del XI desde
      `lineups_historicas` (db/036).** `availability()` toma los XI previos
      de cada equipo también de esa tabla; el XI de hoy, solo de `lineups`.
      257 de 262 equipos con partido en 14 días ya tienen ≥3 XI previos
      (faltan 5 de copas), así que los brazos de XI miden desde el 9-oct y
      no desde finales de octubre.
- [ ] **El XI llega tarde: medir antes de comprar otra fuente (2026-10-01).**
      API-Football publica el once a T-25 (22 de 22 partidos de MLS/Liga MX;
      su propia guía dice 20-40 min). Los clubes lo anuncian ~T-60 y
      Pinnacle se mueve en minutos: la ventaja de "reaccionar antes que las
      casas blandas" casi no existe con esta fuente. Desde el 9-oct, medir la
      antelación del XI en las ligas europeas (`lineups.mins_to_kickoff`). Si
      sigue en ~T-25, evaluar una fuente más temprana, con prueba gratuita y
      midiendo su antelación real antes de pagar. Ojo con el brazo
      `lineup_lambda_market`: aplica el ajuste de XI sobre cuotas de T-20 que
      ya incorporan el XI, así que mide doble efecto por diseño; leerlo
      como cota inferior, no como el valor del XI.
- [ ] **Validar el ajuste de XI con datos nuevos.** El challenger que estima
      ajustes separados sobre `log(lambda_home)` y `log(lambda_away)` y su
      ejecución en sombra ya existen, pero las tablas de predicciones y XI
      locales están vacías. Activar la captura, acumular muestra y exigir
      mejora fuera de muestra, calibración y CLV frente al baseline T-60 en
      varias ligas antes de promoverlo. Ratings por jugador quedan para una
      iteración posterior si el volumen lo permite.
- [ ] **Umbral de abstención basado en incertidumbre.** Antes de publicar un
      pick, distinguir edge medible de diferencias dentro del ruido del
      modelo. Estimar un umbral propio mediante bootstrap o variación entre
      reentrenamientos; no copiar constantes de otros sistemas ni confundir
      este filtro con el `edge_shrinkage` existente. Requiere suficiente
      histórico de predicciones point-in-time y cierres.
- [ ] **Fase 2 — superar el mercado sharp actual.** Elo ya está implementado
      y medido sobre las mismas 1.907 observaciones que Dixon-Coles/Pinnacle:
      RPS 0,20533 / 0,20245 / 0,19561. El baseline mejora, pero el mercado
      sigue delante y sus últimas cuotas locales son de enero de 2026.
      Reformulado por 2.A (abajo): el objetivo ya no es batir al cierre en RPS
      sino la puerta de CLV sobre la sombra sharp. Lo que queda es muestra.
- [x] **Poner el cron en marcha de verdad (2026-09-23).** Plan Pro de
      API-Football ya viable. The Odds API se subió al plan de pago de 20.000
      créditos/mes (nueva `ODDS_API_KEY` en `.env`). Configuración final:
      solo `eu` x `h2h,totals,spreads` (~5.800 créditos/mes), para dejar
      ~14.000 al endpoint histórico. `scripts/crontab`
      ya traía `odds_worker` cada 10 min sin comentar — con clave y crédito
      reales, `odds_worker` puede dejar de ejecutarse a mano. Pendiente real:
      desplegar el contenedor/cron de verdad (no se puede verificar Docker en
      este entorno) y confirmar en la práctica que no se agota el crédito
      antes de fin de mes.
- [~] **Extender la mezcla al hándicap asiático.** Superado (2026-09-24): la
      premisa era que ampliarlo "devolvería el AH al universo de picks", pero
      desde el paso 4 los picks salen del criterio sharp, solo 1X2, y no de
      las probabilidades mezcladas. Con `META_BLEND_ENABLED=0` y
      `w_model≈0` no cambia nada publicable. Reabrir solo si se vuelve a
      querer AH en el criterio sharp (entonces es trabajo de `find_candidates`,
      no de `_apply_blend`).
- [ ] **Frontend de la web (Fase 3, posterior).** El prototipo visual vive en
      `frontend/`; la aplicación comercial todavía no existe y consumirá la
      API cuando los pendientes de las fases anteriores estén estabilizados.
      Se tomó Pitchverse como referencia de composición visual y navegación,
      sin copiar su código, modelos ni contenido. `Pa004/scikick` queda como
      referencia adicional para posibles páginas de partido, mercados,
      calibración, temas e i18n. El frontend final deberá adaptarse a los
      endpoints y criterios de selección propios de QuantFut.
      - [x] Prototipo navegable en modo demo: seis vistas (inicio, picks
        gratuitos, ficha de partido, historial verificable, planes y área de
        suscriptor), inspirado visualmente en la navegación de Pitchverse,
        sin cobros, login real ni acceso a `/v1/*` desde el navegador.
      - [x] Definir guía visual propia (tokens, componentes, móvil y
        accesibilidad) y aplicarla a las seis vistas del prototipo, usando
        `ui-ux-pro-max-skill` solo como catálogo de referencia, no como
        dependencia ni como sustituto de la arquitectura FastAPI.
      - [x] **Mesa de mercados y rediseño de las seis vistas (2026-09-24).**
        Tras analizar propsbr.app (buscador de props por acierto L5/L10),
        se adopta su COMPOSICIÓN —lista de partidos por fecha y liga, tabla
        densa ordenable con minigráfico, detalle lateral con pestañas,
        columna de destacados, formato de cuota— pero NO su contenido:
        nada de "certeras/seguras" ni notas 0-100 sin calibrar. La mesa
        enseña lo que el sistema de verdad mide: precio justo de Pinnacle
        sin margen, mejor casa blanda de la lista, % sobre el justo en el
        mismo snapshot, `min_price`, exclusión por Pinnacle fuera de
        consenso y la sombra del criterio (solo 1X2, publicación pausada).
        El modelo aparece como diagnóstico, no como selector. Los precios
        demo salen de dos lambdas (Poisson) para que todas las vistas
        cuadren entre sí. Sigue siendo demo: sin API, sin cobros.
      - [ ] Integración comercial posterior: suscriptores, pagos y
        autorización en módulos del mismo FastAPI; condicionada a la puerta
        de validación del producto. El BFF separado de la decisión anterior
        queda sustituido por el plan 2026-09-23 de esta página.
- [ ] **Fase 5 — movimiento de línea.** Requiere 12 meses de snapshots
      PROPIOS para validar (captura en vivo desde el 24-sep-2026).
  - [ ] **Estudio exploratorio con histórico ya disponible (añadido
        2026-10-02, pedido del usuario).** Pregunta: ¿se puede predecir la
        dirección del movimiento de Pinnacle 1X2 entre el precio temprano y
        el cierre? No espera a los 12 meses porque ya hay datos:
        1. football-data.co.uk: 14.294 partidos, 7 ligas, 2019/20-2024/25,
           Pinnacle pre-cierre (`PSH/PSD/PSA`) y cierre (`PSCH/PSCD/PSCA`),
           ya cacheados para `soft_vs_sharp.py`. Límite: el precio temprano
           no tiene hora exacta.
        2. Histórico de The Odds API (desde jun-2020; cada 5 min desde
           sep-2022) con hora exacta: solo con créditos sobrantes del mes y
           fijando antes cuántos se gastan.
        Reglas: solo lectura, sin tocar producción ni picks; partición
        temporal fijada antes de mirar resultados; la base a batir es "no
        se mueve" y la media del mercado. Es descubrimiento, NO
        certificación: lo que salga se valida después en sombra con la
        captura propia, igual que la puerta de la fase 2.
- [x] **`soccerdata` retirado (2026-09-24, decisión del usuario).** Borrado
      `src/qf/ingest/xg_fbref.py` (nadie lo importaba) y quitados de
      `requirements.txt` `soccerdata`, `lxml` y `html5lib` (ningún código
      usaba los dos últimos). Los alias con fuente `fbref` se QUEDAN: los usan
      `xg_worldfootball` y `uefa_cups`. Texto original:
      Está fijado a 1.8.7, entra en
      conflicto con `lxml==5.3.0` y `pip install -r requirements.txt` falla con
      ResolutionImpossible. Queda comentado. Solo lo usa `xg_fbref.py`, que el
      README ya da por inservible (Cloudflare). O se borra el módulo o se
      afloja el pin.
- [ ] **¿Bélgica, Rusia, Ucrania, Turquía, Grecia?** Sumarían ~1.160 cruces
      europeos más, pero son cinco ligas para menos muestra de la que dieron
      tres. Rendimientos decrecientes claros: hacerlo solo si se quieren esas
      ligas por sí mismas, no por el término `strength`.

## Plan de la Fase 2 (2026-09-22) — replantear la puerta, no atacarla más fuerte

Punto de partida, ya medido y no discutible sin datos nuevos: sobre n=28.128
predicciones fuera de muestra el modelo pierde en las 7 ligas y
**`w_model = 0.0001`**. El peso óptimo del modelo en la mezcla con el mercado
es CERO. Dos motores independientes (Dixon-Coles con decaimiento y filtrado
bayesiano) aterrizan en el mismo sitio. El diagnóstico del `progreso.md` es
correcto: falta INFORMACIÓN, no técnica.

De ahí se sigue que **más matemática sobre los mismos datos no cierra el
hueco**, y que la puerta actual ("RPS del modelo < RPS del cierre") pide algo
que casi nadie consigue y que además no es lo que hace falta para vender.

### 2.A — Cambiar el objetivo: el cierre no es el rival ✅ IMPLEMENTADO

Son dos afirmaciones distintas y solo una es alcanzable:

  1. "Mi probabilidad es mejor que el consenso de cierre."  -> inalcanzable.
  2. "El precio que puedo tomar AHORA es peor que el cierre que vendrá."
     -> alcanzable, medible, y es exactamente el CLV.

Propuesta: la puerta de la fase 2 pasa a ser **CLV positivo con intervalo de
confianza sobre el precio realmente disponible**, y el precio justo se
construye del **consenso sharp de-vigado (Pinnacle + Betfair)**, no de
Dixon-Coles. El modelo deja de ser la fuente del edge y pasa a ser filtro y
desempate.

Cambia el producto, y conviene decirlo en voz alta: QuantFut deja de afirmar
"nuestro modelo bate a Pinnacle" y pasa a afirmar "detectamos casas blandas que
todavía no han convergido al precio sharp". Es honesto, es medible y **toda la
maquinaria ya existe**: 22 casas vía The Odds API, `consensus_devig` con peso
sharp, y el line shopping de `_best_prices`.

Límite real de ese negocio, para no descubrirlo tarde: no lo acota el modelo,
lo acota que las casas blandas limitan cuentas. Eso es operación, no código.

- [x] Puerta redefinida: `promotion.evaluate_clv_gate`. Exige IC del 95% del
      CLV entero por encima de cero, 300 apuestas y 3 ligas con muestra. Batir
      al cierre en RPS se sigue REPORTANDO pero ya no veta.
- [x] `eval/clv.clv_report` / `summarize_clv`: CLV con IC bootstrap y desglose
      por liga.
- [x] `GET /fair-price/{match_id}`: consenso sharp sin margen, intensidades
      implícitas y distancia de la mejor casa al precio justo.
- [x] `/model-card` publica si la puerta comercial está autorizada y por qué no.
- [ ] Frontend que consuma `/fair-price` (fase 3).
- [x] Desglose por VENTANA (t72/t24/close). Cubierto por `shadow_sharp.report`
      (`by_lead`, en publicables y en todas las ofertas), que es la muestra
      que decide la puerta; desde 2026-09-24 visible también en `/control`.
      Para `pick_results` no hace falta mientras la publicación siga pausada.

### 2.B — Anclar el residuo en el MERCADO, no en el modelo ✅ IMPLEMENTADO

Bug de diseño que se ve al leer `w_model ≈ 0` junto a `lineup_challenger.py`:
`apply()` multiplica `base_lam`, y `base_lam` viene de
`predictions.home_lambda`, es decir **las lambdas del modelo**. Si el modelo
vale cero frente al mercado, ajustar por el XI unas lambdas peores solo mueve
una estimación peor.

La única construcción en la que el XI es información ADITIVA a lo ya preciado:

    1. de-vigar el 1X2 (y los totales si están) del consenso sharp a T-60;
    2. invertir esas probabilidades a (lambda, mu) ajustando la matriz de
       marcadores de Dixon-Coles -> 2 parámetros por partido;
    3. aplicar encima  exp(beta · x_XI)  con los mismos betas ya estimados.

Así el modelo aporta la ESTRUCTURA (la matriz de marcadores, los ~150 mercados
coherentes) y el mercado aporta el NIVEL. Es la lectura correcta de w_model=0:
no "el modelo no sirve", sino "el modelo sirve para la forma, no para el nivel".

- [x] `model/market_anchor.py`: inversión de 1X2 de-vigado a (lambda, mu), con
      residuo obligatorio porque la familia no representa cualquier terna.
- [x] `model/shadow.py` gana dos brazos: `baseline_market` y
      `lineup_lambda_market`. Los cuatro sobre las mismas cuotas, de modo que
      cada comparación aísla una sola cosa.
- [ ] Acumular muestra y comparar los cuatro brazos. Es lo único que falta y no
      se acelera con código. Bloqueo real encontrado el 2026-09-24:
      `qf.model.shadow` responde "sin modelo activo" en cada pasada, así que
      los brazos no acumulan nada hasta que haya modelo. Lo destraba el
      entrenamiento `--bootstrap` (ver "Desplegar y esperar la muestra").

### 2.C — Meter información que el mercado aún no tiene

Es lo único que puede cerrar el hueco, por el propio diagnóstico:

- [ ] **XI a T-60** (ya construido, sin muestra). Ya no lo bloquea el plan
      (Pro desde 2026-09-22; `lineups` corre cada 5 min en el servidor). Lo
      bloquean la muestra y, como a 2.B, la falta de modelo activo. Es el de
      mejor relación valor/esfuerzo del proyecto.
- [x] **Bajas/lesiones.** Superado por algo mejor que un LLM leyendo prensa:
      `/injuries` de API-Football ya da el dato estructurado (jugador, tipo de
      baja, motivo) con el mismo proveedor ya contratado. Ingesta en
      `src/qf/ingest/injuries.py`, sellada con `captured_at`. Falta la
      feature de disponibilidad que entra en 2.B (ver Pendientes 🔴 arriba).
- [ ] **Movimiento de línea (fase 5).** Predecir la dirección del movimiento
      T-72 -> cierre es modelar un proceso MECÁNICO (flujo de dinero, cambios
      de límite), no uno caótico, y es donde un operador pequeño puede ganar de
      verdad. Necesita los 12 meses de snapshots: empezar a acumular hoy.

### 2.D — Modelos matemáticos: qué vale la pena y cuánto (poco)

Alternativas a Dixon-Coles publicadas como mejores, con expectativa HONESTA de
orden 0,001–0,002 de RPS cada una, frente a un hueco de 0,0065:

- [x] Conteo Weibull con cópula (Boshnakov, Kharrat & McHale, 2017). Es la
      mejora principal publicada sobre DC: trata dispersión y dependencia en
      vez del parche `tau` de 1997.
- [x] Conway-Maxwell-Poisson o Poisson bivariante (Karlis-Ntzoufras).
- [x] Probit ordenado sobre la diferencia de goles, como ruta alternativa al 1X2.

**Medido (2026-09-24), NEGATIVO:** `model/structure.py`, n=2.641 partidos
fuera de muestra del último año, walk-forward de DC real. Ningún brazo mejora
a DC `tau` con el IC entero por encima de cero en su métrica principal. Deltas
de RPS 1X2 contra `tau` (positivo = mejor que `tau`): Poisson bivariante
−0,00009 [−0,00017, +0,00001], CMP −0,00018 [−0,00029, −0,00006], Weibull con
cópula −0,00025 [−0,00045, −0,00002], probit ordenado −0,00044 [−0,00146,
+0,00055]. CMP y Weibull empeoran el 1X2 con el IC entero por debajo de cero.
Los parámetros ajustados quedan pegados al caso Poisson (ν=1,09, c=1,05,
κ=0,29, λ3=0,05): los goles del fútbol casi no tienen la sobredispersión ni
la dependencia que estos modelos saben corregir, y el `tau` (ρ≈−0,04) ya se
queda con lo poco que hay. Quitar el `tau` también empeora (−0,00006
[−0,0001, −0,00002]): se mantiene. Queda como informe en cada
entrenamiento (`val["structure"]`) por si cambia con más datos; no se activa
nada. Con esto 2.D queda cerrado: la forma de la matriz no es donde está el
hueco de 0,0065, como ya decía el diagnóstico.

Entran como challengers baratos, **nunca como el plan**: se medirían contra el
mismo conjunto de información que `w_model` ya declaró sin valor.

**Diseño acordado (2026-09-24, el usuario pidió implementarlos):**
`model/structure.py`. Los cuatro brazos de conteo conservan las MEDIAS de
Dixon-Coles (`lam`, `mu` fuera de muestra) y cambian solo la FORMA de la
matriz de marcadores: dispersión y dependencia, que es justo lo que los
papers dicen mejorar sobre el parche `tau`. Así no hace falta otro ajuste de
fuerzas por equipo (el walk-forward ya cuesta horas) y cada brazo aísla una
sola cosa. Brazos: Poisson independiente, DC `tau` (el titular, reajustado con
el mismo protocolo para que la comparación sea justa), Poisson bivariante
(λ3), CMP (ν, medias igualadas), Weibull con cópula de Frank (forma c y κ).
Aparte, probit ordenado heterocedástico sobre la diferencia de goles con
índice `log lam − log mu`. Parámetros globales reajustados por ventana
creciente mensual (sin mirar el futuro). Métricas: log-loss del marcador
exacto, over/under 2,5 y 1X2 (RPS y log-loss), con deltas contra DC `tau` e
IC por remuestreo de semanas. Solo informe en `val["structure"]`: NUNCA se
activa solo.

Lo que sí es matemática valiosa y NO está construido:

- [x] **Zona de abstención y Kelly bajo incertidumbre** (2026-09-22).
      `model/uncertainty.py`. El error estándar de cada parámetro sale del
      ajuste (estimador sándwich) y se propaga por Monte Carlo hasta el edge.
      De la misma medida salen las dos decisiones: abstenerse si
      `media - Z·sd <= 0`, y si no, encoger por `floor/media` en vez de por la
      constante 0,55. `UNCERTAINTY_ENABLED` apagado por defecto: cambia
      cuántos picks se publican al día.
- [x] **Guarda de muestra efectiva** (2026-09-22). Caso particular de la zona de
      abstención, cerrado ya porque la demostración con cuotas reales lo
      destapó: un club que vuelve a primera tras años fuera seguía en el índice
      con un parámetro extremo del ridge, `knows()` decía True, `_confidence()`
      le daba `high` (cuenta partidos de toda la vida) y se llevaba el stake
      máximo con un "edge" del 97%. Ahora `DCParams.effective_n` mide la suma
      de pesos de decaimiento y `MIN_EFFECTIVE_MATCHES` la exige.
- [~] **Validar la zona de abstención con datos reales.** Superado
      (2026-09-24): medida sin señal (ver `UNCERTAINTY_Z` abajo) y su
      integración se eliminó en el paso 4. `model/uncertainty.py` ya no lo
      importa ningún módulo; los picks no salen del edge del modelo.
- [x] **Calibrado `UNCERTAINTY_Z`: NO HAY SEÑAL QUE CALIBRAR** (2026-09-22).
      12.183 filas point-in-time sobre 4.061 partidos. La razón media/sd no
      discrimina (correlación con el acierto −0,047) y el motivo está debajo:
      el edge crudo del modelo correlaciona **−0,123** con el acierto. Es una
      anti-señal, y filtrar más fuerte sobre ella no puede ayudar. Queda
      `UNCERTAINTY_ENABLED=0` por medición, no por prudencia.
- [ ] **PLAN (2026-09-23) — sustituir el criterio de selección por "casa blanda
      contra precio sharp".** Piloto en `progreso.md`. Orden obligatorio:
      0. [x] Bloquear la publicación con el criterio viejo (2026-09-23).
         `PUBLISH_PICKS_ENABLED=0` por defecto: `daily.py` predice y sella,
         no selecciona, guarda ni difunde picks. `/model-card` lo declara.
         `tests/test_publicacion_bloqueada.py`.
      1. [x] Arreglar la vara (2026-09-23). `ev_close_pct = price ×
         closing_prob_devig − 1` en `pick_results` y `shadow_results`
         (`db/015_ev_cierre.sql`, aplicada en local). `summarize_clv`,
         `evaluate_clv_gate`, `shadow.summary` y
         `evaluate_shadow_promotion` deciden sobre él; `clv_pct` se sigue
         reportando. `closing_prob_devig` sale ahora de UN snapshot de
         cierre sharp con grupo completo. Tests: `test_ev_cierre.py`,
         `test_puerta_clv.py`. `v_clv_daily` y los paneles de CLV de Grafana
         ya muestran `ev_close_pct` (`db/019`, 2026-09-24).
      2. [x] `eval/soft_vs_sharp.py` (2026-09-23). Backtest reproducible
         sobre los CSV del formato principal, cacheados en `.local/fd_cache`
         con firma sha256; por casa, umbral y "mejor cuota entre casas
         reales"; IC por semanas; control sin criterio. Guarda
         `MAX_SHARP_DEVIATION`. 12 tests. Resultado: 1X2 +2,09% [1,21, 2,91]
         con la mejor casa real a umbral 2%; over/under sin oportunidades
         verificables.
         Decisiones que salen del backtest, para el paso 4:
         - Mercado principal 1X2. Totales solo con la guarda de referencia.
         - El encogimiento no puede ser el 0,55 constante: la persistencia
           medida va de 0,13 (Bet365) a 0,68 (1xBet); ~0,42 en conjunto.
         - La misma guarda de referencia en vivo: Pinnacle contra el
           consenso de las demás casas en el mismo snapshot.
         - Volumen: ~230 apuestas por temporada en 7 ligas con UN snapshot
           pre-cierre; la puerta pide 300. El vivo tiene más ventanas.
      3. [x] `ingest/odds_history.py` (2026-09-23). `plan` / `fetch` /
         `report` (con `--books`) con presupuesto por ejecución y reserva
         leyendo `x-requests-remaining`; respuestas crudas en
         `.local/odds_hist/`, NO en `odds_snapshots` (inmutable). 1X2,
         región `eu`. 11 tests. Descargado 2025 de Liga MX, Brasil,
         Argentina y MLS: 16.560 créditos, justo lo planificado.
         Resultado a umbral 2%: todas las casas +2,78% [1,79, 3,78] n=317;
         casas accesibles (1xBet+WH+888) +3,83% [2,36, 5,20] n=127, de las
         que 126 son 1xBet y 85 son MLS. Liga MX con casas accesibles: 7
         apuestas, negativo. Detalle en `progreso.md`.
         Decisión del usuario (2026-09-23): los suscriptores apuestan en
         casas internacionales presentes en LatAm (Bet365, 1xBet, Betway,
         William Hill, 888...). The Odds API no tiene Bet365 ni casas
         mexicanas; API-Football sí trae Bet365, Betano, 1xBet y William
         Hill junto a Pinnacle en 12 de 13 competiciones.
      3b. [x] Captura de cuotas de API-Football (2026-09-23, confirmada por
         el usuario). `src/qf/ingest/af_odds.py` + `db/016_af_odds.sql`
         (aplicada en local): tabla propia `af_odds_snapshots`, inmutable,
         con `provider_updated_at` y `fetched_at`; deduplica por la marca
         `update` del proveedor. 1X2, 9 casas, partidos en las próximas 72 h,
         cron cada hora. Verificada con dos pasadas reales (78 filas, luego
         0). 4 tests. Casa blanda y Pinnacle de la MISMA respuesta, nunca
         mezclando con el Pinnacle de The Odds API.
         Pendiente: desplegar el cron de verdad (Docker no disponible aquí)
         y, en unas semanas, medir con estas filas + el cierre de The Odds
         API el valor de Bet365 y Betano, que no tienen histórico en
         ninguna fuente.
      4. [x] `find_candidates` nuevo (2026-09-23). Precio justo = Pinnacle
         de-vigado en el MISMO snapshot que la casa blanda (API-Football o una
         captura de The Odds API, nunca cruzadas); guarda de referencia contra
         el consenso del snapshot (≥2 casas, sin exchanges); lista blanca
         `SOFT_BOOKS` con nombres unificados; edge bruto ≥ `SOFT_MIN_EDGE_PCT`
         (2%); antigüedad ≤ `SOFT_QUOTE_MAX_AGE_HOURS` (6 h); solo 1X2. Stake
         por Kelly sobre el edge esperado al cierre (× persistencia por casa,
         `picks.PERSISTENCE`). `picks` gana `fair_prob`, `min_price`,
         `odds_source`, `odds_as_of` (`db/017`, aplicada en local), que se
         sellan y salen por la API. Eliminado el criterio del modelo con sus
         integraciones (`eligible_markets`, `UNCERTAINTY_ENABLED`) y
         `tests/test_eligible_markets.py`. 13 tests nuevos. Prueba en seco con
         datos reales: 0 candidatos (ninguna casa de la lista por encima del
         justo; Liga MX con snapshot de 19 h).
         Sin validar todavía: el histórico cubrió precios 24-48 h antes del
         partido; el vivo decide a cualquier distancia. La sombra (paso 5)
         tiene que estratificar por antelación.
      5. [x] Sombra del criterio (2026-09-23). `publish/shadow_sharp.py` +
         `db/018_sombra_sharp.sql` (aplicada en local). `capture` cada hora
         a las :25 registra TODAS las ofertas (incluidas las de stake 0) de
         partidos a 72 h, sin duplicar un mismo snapshot; `settle_pending`
         se encadena desde `eval/clv.settle_pending` contra el cierre de
         Pinnacle sin margen; `report` separa "publicables" (primera pasada
         con stake por partido, la mejor de esa pasada: lo que ve la puerta)
         de todas las ofertas por antelación, casa, fuente y liga. Estado
         publicado en `/model-card` (`sombra_criterio_sharp`). 7 tests.
         Verificado contra el Postgres local: 0 ofertas hoy.
- [ ] **PLAN (2026-09-25) — Más mercados en el criterio sharp: goles y
      hándicap asiático.** Decisión del usuario: necesita picks todos los días
      y el 1X2 solo da pick en ~1 de cada 5 partidos (medido en vivo 24-25
      sep). Mismo criterio, más mercados; no se baja el umbral.
      Hechos que condicionan el diseño (sondeados el 2026-09-25):
      - API-Football trae Pinnacle, Bet365, Betano y 1xBet con goles (bet 5)
        y hándicap asiático (bet 4) en varias líneas, en la MISMA respuesta
        que el 1X2 y por la misma petición (quitando el filtro `bet`).
      - Trampa del hándicap de API-Football: las dos patas llevan la línea
        del LOCAL. 'Away -1' a 1,23 es visitante +1. Hay que invertirla.
      - Bet365 solo cotiza la línea 0 en hándicap; su valor estaría en goles.
      - The Odds API solo da UNA línea de Pinnacle por partido (la principal)
        en totals/spreads. Sin cierre de Pinnacle en esa línea, una oferta no
        se puede validar. Por eso el criterio solo mira la LÍNEA PRINCIPAL de
        Pinnacle del snapshot (la más equilibrada).
      Pasos:
      1. [x] `db/022`: columna `line` en `af_odds_snapshots` y
         `sharp_shadow_offers`; claves únicas con `line` (NULLS NOT DISTINCT,
         PG16). Nombres reales de las claves viejas comprobados en producción.
      2. [x] `af_odds`: capturar 1X2 + goles + hándicap en la misma llamada;
         pares completos por casa y línea; hándicap con la línea del lado.
      3. [x] `picks.offers`: mercados de dos vías por línea (totals/spreads):
         justo = Pinnacle sin margen de esa línea, guarda de consenso con ≥2
         casas en la misma línea, solo línea principal, umbral 2%.
         Persistencia por casa igual que 1X2 hasta tener muestra por mercado
         (suposición declarada; la sombra la mide).
      4. [x] Sombra: mercado y línea en ofertas y liquidación (`fair_close_prob`
         y `_settle_outcome` ya soportan totals/spreads); informe por mercado.
      5. [x] Tests (parseo con la trampa del hándicap, criterio por línea,
         liquidación) y harness: 413 tests.
      6. [ ] **NO desplegado: el ensayo con datos reales no encontró valor.**
         2026-09-25, 24 partidos de Liga MX y MLS, respuesta real de
         API-Football evaluada en memoria. Línea principal: las guardas pasan
         (47 de 48 mercados evaluados) pero la mejor casa de la lista queda
         en −0,1% (Betano) y el resto entre −1% y −5%. TODAS las líneas:
         0 de 1.448 precios de casas de la lista superan el justo en un 2%.
         1X2 en las mismas respuestas: 2 ofertas. Coincide con el histórico
         (over/under: 11 apuestas en 7 ligas y 6 temporadas). Las casas
         blandas copian a Pinnacle en goles y hándicap con su margen; el
         valor del 1X2 está en empates y no favoritos. Además, desplegarlo tal
         cual multiplicaría por ~50 las filas de `af_odds_snapshots` (todas
         las líneas de todas las casas). Si se despliega, guardar solo la
         línea principal de Pinnacle. Muestra corta (un día, dos ligas):
         repetir el ensayo con Europa activa antes de descartarlo del todo.
      Fuera de este paso, anotado: córners/tarjetas/mitades (Pinnacle los
      cotiza en API-Football pero no hay cierre fiable) y líneas alternativas
      de Pinnacle al cierre vía `alternate_totals` de The Odds API (coste por
      evento, a medir).
- [x] **HECHO (2026-09-25) — LaLiga 2 y Serie B en modo "solo sharp".**
      Desplegado: `db/023` y `db/024` aplicadas, worker y api reconstruidos,
      calendario cargado. Verificado en producción: 44 partidos (LaLiga 2 34,
      Serie B 10), equipos 390 → 390 tras el calendario (ningún alta
      automática), alias 941 → 1.018 (+77 revisados), pendientes 35 → 35,
      0 predicciones de estas ligas; `af_odds` las captura, lineups/bajas no,
      The Odds API solo `h2h`. Respaldo de los archivos sustituidos en
      `~/respaldo_20260925_ligas/` del servidor. Pendiente: que las primeras
      ofertas y cierres lleguen a la sombra (primer partido de LaLiga 2 hoy).
      Decisión del usuario, con la condición de no ensuciar la base. Dos
      riesgos encontrados antes de tocar nada:
      a) Duplicados: un club tiene UNA liga (`teams.league_id`). La liga nueva
         empieza sin equipos, `match_team` no encuentra a nadie y
         `resolve_or_register` crearía de nuevo a los descendidos de LaLiga y
         Serie A, con la historia partida.
      b) Cadena sellada: `daily._upcoming` predice y SELLA todo partido
         programado. El modelo no conoce a esos equipos: se publicarían
         predicciones sin base, inmutables.
      Diseño:
      1. [ ] `db/023`: `leagues.model_enabled` (TRUE por defecto; FALSE en las
         dos nuevas) y alta de `es.laliga2` / `it.serie_b`.
      2. [ ] `normalize.resolve_or_register`: antes de crear, coincidencia
         EXACTA (nombre canónico o cualquier alias) en las demás ligas
         domésticas del MISMO país; si hay un parecido dudoso allí, pendiente
         de revisión en vez de crear. Simétrico: sirve para ascensos y
         descensos entre ligas del catálogo.
      3. [ ] Fuera de todo lo que alimenta al modelo o a la cadena cuando
         `model_enabled` es FALSE: `daily._upcoming`, `train` (datos y
         `bootstrap_status`), `lineups`, `injuries`, `xg_worldfootball`.
         Dentro: calendario, resultados, `af_odds`, sombra sharp y
         `odds_worker` (solo `h2h`: 1 crédito por llamada).
      4. [ ] Ensayo en seco en el servidor (qué equipos se reutilizan, cuáles
         quedan pendientes, cuáles se crean) ANTES de aplicar.
      Sin histórico de football-data para ellas: el criterio no lo necesita y
      cargarlo mezclaría nombres de dos fuentes en ligas nuevas.
- [x] **HECHO (2026-09-27) — Fichas de partido reales en la web (estilo
      PropsBR): estadísticas, forma y H2H con datos de API-Football.**
      Desplegado: db/028 (`matches.stats`, `standings`), db/029
      (`teams.display_name`), `ingest/standings.py` (cron 06:40 y 22:40),
      `/web/partidos` y `/web/partidos/{id}` (`api/fichas.py`), vista
      «Partidos y estadísticas» y franja «Hoy en las ligas» en la portada.
      Sin probabilidades del mercado en la ficha (ver progreso).
- [x] **HECHO (2026-09-27, con el sí del usuario): cargados los partidos
      ya jugados de esta temporada de LaLiga 2 (66) y Serie B (50)** con
      `python -m qf.ingest.fixtures --temporada es.laliga2 it.serie_b`.
      0 equipos nuevos, 0 duplicados. Y escudos: db/030, 271 descargados.
      Texto original de la propuesta: Faltan
      ~90 y ~50 (anteriores al alta del 25-sep). Sin ellos, la forma de un
      descendido enseña sus partidos de mayo en Primera. Coste: 2 peticiones
      de calendario + estadísticas por partido; el modelo no los lee (ligas
      `model_enabled = false`). Vía: insertarlos como programados con su
      `external_id` y dejar que `results.close_recent(hours_back=…)` los
      cierre por el camino normal.
- [x] **HECHO (2026-09-28, lo pidió el usuario): `/fair-price` pasa a
      `/v1/fair-price/{id}` con `SERVICE_TOKEN`.** Nadie lo consumía (ni
      frontend ni tests); sin token responde 404. Aviso original:
      `/fair-price/{id}` era público y
      devuelve `best_price` y `gap_pct`,** es decir, qué casa paga por encima
      del justo en cada partido: el criterio de picks en abierto. No se ha
      tocado; decidir si pasa a `/v1` (SERVICE_TOKEN) o se recorta.
- [x] **HECHO (2026-09-28, pedido del usuario: "ejecuta todas las
      palancas") — Acelerar la muestra de la puerta sin rebajarla.**
      Desplegado: sombra con todas las casas y puerta con `SOFT_BOOKS`
      ampliada (.env del servidor actualizado), guarda de 15 min, persistencia
      recalibrada, db/033 (10 ligas, 127 equipos nuevos, 43 reutilizados) y
      guardas en daily/train para equipos de ligas sin modelo en copas.
      El usuario confirmó (2026-09-28) Betsson y Coolbet; LeoVegas y Unibet
      fuera de `SOFT_BOOKS` (la sombra las sigue midiendo igual).
      Diagnóstico previo (solo lectura): desde el 24-sep, 36 partidos; con la
      lista actual 8 con oferta, con todas las casas del feed 23. Cierre de
      Pinnacle: 10 de 10 partidos en sombra lo tienen (el "3 de 4" era un
      pick aún sin jugar). El Pinnacle de API-Football nunca baja de 2,5 h
      antes del partido: el cierre solo puede venir de The Odds API.
      1. [x] Casas: la sombra mide TODAS las casas no exchange del snapshot;
         la puerta (publicables) cuenta solo `SOFT_BOOKS`, filtrado al
         informar (sin columna nueva: se puede recalcular para cualquier
         lista). `SOFT_BOOKS` += betsson, coolbet, leovegas_se, unibet_se,
         unibet_nl, a confirmar por el usuario (el feed da precios de
         Suecia/Países Bajos para LeoVegas/Unibet).
      2. [x] Cierre: ninguna oferta de la sombra puede salir de un snapshot
         de la ventana de cierre (se liquidaría contra sí misma: EV = edge
         bruto). Se exige antelación ≥ 15 min.
      3. [x] Ligas "solo sharp" con Pinnacle en The Odds API y sin
         divisiones hermanas en la base (no duplican clubes): Chile, Turquía,
         Suiza, Dinamarca; Colombia/Perú/Ecuador si hay cobertura. Antes:
         el job diario deja de predecir partidos de copa con equipos de ligas
         sin modelo (hoy se sellarían con `both_teams_known=false`).
      4. [x] Persistencia por casa: regla fijada AHORA, antes de ver la
         muestra: media ponderada previa/medida con peso n/(n+100) partidos,
         medida = EV al cierre / edge bruto de la primera oferta por partido
         y casa, suelo 0. Solo afecta a capturas futuras (cada oferta guarda
         la persistencia con la que se decidió).
- [ ] **Idea aparcada (2026-09-27, el usuario prefirió no hacerlo): medir más
      casas en sombra.** Con TODAS las casas del feed, los partidos con oferta
      desde el 24-sep pasarían de 8 a 25; las que más aportan: LeoVegas (22),
      BetVictor (14), Unibet (13), Coolbet (7; +4,4% al cierre en el histórico
      de Liga MX). Más casas dan más picks y mejor precio, NO más acierto (sus
      cuotas medias eran 3,6-4,5). Suscriptores en Latinoamérica y España.
      Ojo si se retoma: el feed da LeoVegas/Unibet de Suecia y Países Bajos,
      no el precio de la web española o latinoamericana; Codere, Caliente,
      Sportium, Luckia, Kirolbet, Strendus y Playdoit no los da ningún
      proveedor. Propuesta que quedó sin hacer: registrar esas ofertas en la
      sombra marcadas "en medición", fuera de la puerta y sin publicar.
- [ ] **PLAN (2026-09-25) — Más ligas en 1X2 para tener picks a diario.**
      Sondeo real (API-Football `odds?date=`, 1X2, 26-28 sep, parón de
      selecciones en Europa, una foto por partido): 823 partidos con cuotas
      en 176 ligas; 491 con Pinnacle y casas de la lista en la misma
      respuesta; **14 con pick (2,9%)** en 12 ligas, frente a 2 de nuestro
      catálogo actual (Liga MX). Bet365 da 11 de los 14 (persistencia medida
      0,13: muchos quedarán con stake mínimo) y 1xBet 3. En vivo se mira cada
      hora durante 72 h, así que la tasa real será mayor (MX/MLS: 5 de 25
      partidos en 34 h frente a 2 de 24 en una foto).
      Restricción que manda: validar exige el cierre de Pinnacle y eso solo
      lo da The Odds API. De los 14, solo 5 son de competiciones que cubre
      (Nations League, Liga MX, League Two). Las demás (Segunda RFEF, WSL,
      3. liga checa, Segunda uruguaya, Primera B colombiana, Copa Chile…) NO
      se podrían validar nunca: no entran.
      Candidatas validables (en The Odds API y activas): Championship, League
      One, League Two, EFL Cup, La Liga 2, Serie B, Ligue 2, Bundesliga 2,
      3. Liga, DFB-Pokal, Bélgica, Austria, Suiza, Dinamarca, Noruega, Suecia
      (Allsvenskan y Superettan), Finlandia, Grecia, Turquía, Escocia,
      Irlanda, A-League, K League 1, Chile, Brasil Série B, Libertadores,
      Sudamericana, Conference League, Nations League.
      Backtest por liga (football-data 2021/22-2024/25, 1X2, mejor de
      Bet365/William Hill/1xBet a umbral 2%, una foto pre-cierre por partido,
      EV contra el cierre de Pinnacle sin margen). Picks por semana · EV al
      cierre [IC95]:
        National League 1,77 · +4,83% [3,0, 6,7]  (sin The Odds API: no validable)
        LaLiga 2        1,64 · +3,91% [2,5, 5,3]
        Serie B         1,43 · +5,06% [3,3, 7,1]
        Bélgica         0,85 · +3,20% [1,2, 4,9]
        Serie A         0,71 · +3,91% [1,6, 6,3]  (ya en catálogo)
        Escocia Champ.  0,23 · +4,34% [1,3, 7,2]  (sin The Odds API)
        Positivas sin demostrar: Turquía +1,95, Bundesliga 2 +1,86,
        Championship +1,43, Ligue 2 +1,15, League One/Two +1,1.
        Sin valor: Grecia −0,22 (88% Bet365), Ligue 1 −0,77, Portugal +0,17,
        Eredivisie +0,84 (IC con cero). Las tres últimas YA están en el
        catálogo: la sombra por liga debe decidir si se publican.
        Total 20 ligas: 2.158 picks, +2,48% [1,93, 3,10], persistencia 0,51.
      Cuotas (medido 2026-09-25): API-Football gasta ~350-430/día con 25
      partidos en el horizonte (1 petición por partido y hora); con Europa de
      vuelta serán ~3.000-3.500/día y con 6 ligas más ~5.000 de 7.500. Cabe,
      pero la captura por fecha lo dejaría en ~2.200 fijo. The Odds API: le
      quedan 3.205 créditos de 20.000 tras el histórico (16.560).
      **Corregido el 2026-09-27: NO es urgente.** El plan se renueva el día 1
      de cada mes (dato del usuario); el 27-sep quedaban 3.006 con un gasto
      medido de 70-100/día, así que llegan al reset con ~2.600 de sobra. Con
      Europa activa se estiman ~6.000-9.000 al mes: caben en 20.000. Pasar el
      vivo a solo `h2h` (goles y hándicap no dieron valor) queda como palanca
      para crecer en ligas sin subir de plan, no como arreglo urgente.
      Cobertura REAL de Pinnacle en The Odds API (una llamada h2h por liga,
      2026-09-25; eventos con Pinnacle / eventos): League One 4/4, League
      Two 10/10, Bundesliga 2 9/9, Ligue 2 9/9, LaLiga 2 11/12, Serie B
      10/10, Chile 9/10, Dinamarca 6/6, Finlandia 6/6, Suiza 6/6, Turquía
      9/9; PARCIAL Austria 6/12 y Brasil Série B 10/20; SIN Pinnacle: 3. Liga
      1/11, Superettan 0/7 y **Bélgica 0/9** (recomendada por el backtest:
      volver a comprobar antes de darla de alta; si sigue sin Pinnacle no es
      validable).
      Descubierto en la misma prueba: `bookmakers=` con hasta 10 casas cuesta
      1 crédito (medido: `x-requests-last=1` con 6 casas) y MEZCLA regiones:
      trajo Betway, que solo está en `uk` y es casa de los suscriptores. Usar
      `bookmakers=pinnacle,onexbet,williamhill,sport888,betway,...` en vez de
      `regions=eu` da más casas por el mismo precio. `regions=eu,uk,us`
      triplicaría el coste.
      Trabajo que implica, en orden:
      1. [ ] Catálogo: filas en `leagues` (api_football_id, clave de The Odds
         API, estilo de temporada) y calendario/resultados de esas ligas.
      2. [ ] Captura de API-Football por FECHA (`odds?date=`, ~30 páginas por
         día) en vez de una petición por partido: con ~250 partidos a 72 h la
         captura actual gastaría ~6.000 peticiones/día de 7.500.
      3. [ ] The Odds API: ligas nuevas solo `h2h` (1 crédito por llamada);
         goles y hándicap no dieron valor y cuestan 3.
      4. [ ] Sombra primero: las ligas nuevas acumulan ofertas y cierres antes
         de publicar nada; la puerta por liga ya existe (`by_league`).
      5. [x] Desacoplar el pick de la predicción (2026-09-25, desplegado).
         `db/025`: `picks.prediction_id` y `model_prob` admiten vacío (nunca
         0: se leería como "el modelo da 0%"). `daily._sharp_only_upcoming`
         añade los partidos de ligas `model_enabled = FALSE` a la selección
         sin predecirlos ni sellar predicción; el orden predecir →
         seleccionar → sellar → publicar no cambia. Con la publicación
         cerrada no se elige nada, igual que antes. Verificado: 43 partidos
         solo sharp elegibles a 30 días, 0 en la predicción sellada.
- [ ] **Desplegar y esperar la muestra.** Nada de lo anterior produce datos
      hasta que el contenedor corra el cron: `odds_worker` (cierres de
      Pinnacle), `af_odds` y `shadow_sharp capture`.
      Preparado en local (2026-09-23), falta ejecutarlo en el servidor:
      `quantfut.dump` (4 MB), `.env.server` (rellenar `DOMAIN` y
      `GRAFANA_ALLOWED_IP`), `scripts/restore_db.sh`; corregidos el entorno y
      el `PATH` del cron del worker, `.dockerignore` y `PG_PASSWORD` en
      `.env.example`. Pasos en README → "Llevar la base local al servidor".
      Tras arrancar: entrenar el primer modelo (no hay ninguno activo) y
      comprobar `/var/log/af_odds.log`. Luego, revisar
      `report` cada semana y, cuando `sombra_criterio_sharp.autorizada` sea
      true, decidir con el desglose por antelación si se restringe el tramo
      antes de poner `PUBLISH_PICKS_ENABLED=1`. Eso último es decisión del
      usuario, no del código.
      **Plan de despliegue (2026-09-24)** — VPS Contabo `31.220.72.30`,
      dominio `pronosticosdeportivos.pro` con DNS y proxy de Cloudflare
      (SSL Full strict, Origin Certificate en `/etc/ssl/quantfut/`):
      - [x] Caddy detrás de Cloudflare: `trusted_proxies` = rangos CF,
            IP real desde `CF-Connecting-IP`, `X-Forwarded-For: {client_ip}`
            hacia la API (el rate limit de `main.py` usa su primer elemento),
            `tls` con el Origin Certificate en vez de ACME.
      - [x] Sustituir la restricción por IP (`GRAFANA_ALLOWED_IP`) por
            Cloudflare Access en `panel.`, `/control` y `/admin` (decisión
            del usuario). Caddy exige además `Cf-Access-Jwt-Assertion`.
      - [x] Configurar las aplicaciones de Access en Zero Trust: Google como
            proveedor de identidad, app "QuantFut - panel de operación" con
            los 7 destinos y política "Solo el operador" (jairlopez.cc@gmail.com).
            Probado en vivo: login con Google → 503 propio de la API
            ("Panel no configurado"), no un bloqueo de Access.
      - [x] `ADMIN_CONSOLE_USER` (jairlopez.lcc@gmail.com) + hash en `.env`
            del servidor. Trampa real: el `$` del hash pbkdf2 choca con la
            interpolación de variables de `docker compose` en `.env` — sin
            escapar como `$$`, el hash se corta en el primer `$` sin avisar
            (compose solo advierte "variable is not set", nada apunta al
            valor roto). `/control` pasó de 503 a 302 tras corregirlo.
      - [x] **Bug encontrado y corregido (2026-09-24): el cron del worker no
            corría en el servidor.** `chmod 0644 /etc/cron.d/quantfut` fallaba
            contra el volumen `:ro` y el `&&` cortaba antes de `crontab`;
            `cron -f` seguía arriba pero con cero jobs, sin error visible.
            Quitado el `chmod` (no hacía falta) en `docker-compose.yml`.
            Verificado: 17 jobs cargados, `cron -f` corriendo.
      - [x] Servidor: usuario `qf`, swap 4 GB, fail2ban, ufw (solo 22) +
            cadena `DOCKER-USER` que deja 80/443 solo a rangos de Cloudflare
            (Docker se salta ufw en puertos publicados).
      - [x] `PermitRootLogin no` (2026-09-24): contraseña puesta a `qf`,
            login root por SSH desactivado y verificado (`Permission denied`
            probando con la clave). `qf` sigue entrando por clave y ahora
            tiene sudo sin contraseña (`/etc/sudoers.d/qf-nopasswd`) para no
            bloquear tareas de administración futuras. Alias `ssh quantfut`
            actualizado a `qf@` en `~/.ssh/config`.
      - [x] Subir repo + `quantfut.dump` + `.env`, `build`, `restore_db.sh`,
            `up -d`, backup diario `pg_dump -Fc`.
      - [x] Entrenar el primer modelo y cargar el calendario (2026-09-24).
            Calendario cargado (171 partidos programados). Primer
            entrenamiento corrido: NO activó modelo, correctamente —
            `market_age_days=250` en la base restaurada (cierre sharp más
            reciente de enero 2026), y la puerta exige <30 días. No es un
            fallo, es la puerta funcionando. **Resuelto el 2026-09-27:** el
            `--bootstrap` de las 01:05 entrenó con los cierres de Pinnacle
            del fin de semana y activó `2026.09.27-010508` (RPS 0,1991 frente a
            0,19345 del mercado: sigue detrás, como se esperaba); el job de
            las 08:00 selló las primeras 4 predicciones. Reentrenar cuando
            `odds_worker`/`af_odds`/`shadow_sharp` acumulen cierres frescos
            (ya corriendo desde el fix del cron).
      - [ ] Backup fuera del servidor (sin destino rclone todavía).
      - [ ] **Resultados de la temporada en curso sin cargar (revisado
            2026-09-24, 01:50 UTC del 25).** Último partido terminado en la
            base: Premier, LaLiga, Serie A, Eredivisie y Liga MX en mayo de
            2026; Brasil en diciembre de 2025. Bundesliga, Ligue 1, Portugal
            y Argentina sí tienen septiembre. Sin resultados no se liquida
            ningún cierre ni el entrenamiento ve la temporada actual.
            **Causa encontrada:** `history_fd.backfill()` tenía el rango fijo
            2014..2025 (nunca cargaba 2026/27), `fixtures` solo crea partidos
            futuros y `results` solo cierra las últimas 72 h: lo jugado antes
            del primer calendario no existía. Arreglado en local con tests:
            `default_seasons()` llega al año en curso y `_ingest_rows` salta
            la fila entera si el partido ya existe (misma liga y equipos,
            ±36 h), porque API-Football etiqueta distinto la temporada y las
            cuotas no admiten DELETE. Alias `db/021` (Racing Santander).
            **Desplegado y cargado (2026-09-25 UTC, confirmado por el
            usuario):** `db/021` aplicada y `backfill(['2627'])` con el código
            nuevo en un contenedor aparte. 991 partidos en 7 ligas, 2.973
            cuotas de cierre (3 por partido), 0 duplicados, 0 clubes nuevos;
            los 531 ya cargados y el cruce con API-Football, saltados.
            **No desbloquea el `--bootstrap`:** football-data dejó de traer
            Pinnacle a mediados de enero de 2026; los cierres nuevos son de
            Bet365 y la frescura exige el sharp. El primer Pinnacle fresco
            será la captura en vivo de los 25 partidos de Liga MX y MLS del
            26-28 de septiembre. Comprobar el 28-29: `close` de Pinnacle
            capturado, partidos cerrados por `results` y `bootstrap_status()`.
      - [x] **17.385 grupos de cuotas de cierre de football_data repetidos**
            (revisado 2026-09-25). Todos con exactamente UNA fila de más y el
            MISMO precio (0 grupos con precio distinto): recargas de Liga MX
            (3.987 partidos), Argentina (1.428) y Premier (380) anteriores a
            la guarda de `history_fd`. Ningún número medido está sesgado:
            entrenamiento, CLV, sombra, `/fair-price`, `daily`, `picks` y
            `v_closing_odds` eligen un precio por selección (`DISTINCT ON` o
            un único `captured_at`), y `soft_vs_sharp` lee los CSV, no la
            base. Único efecto: `v_odds_growth.snapshots` (count(*)) cuenta
            de más en días históricos; cosmético. No se borran (inmutable) ni
            se añade índice único: ya no se puede crear con esas filas y la
            guarda del código basta. Mismo día: 0 cierres de Pinnacle capturados en 3
            días (solo 1 partido terminado desde el arreglo del cron) y el
            `--bootstrap` de las 01:05 volvió a rechazar ("mercado de 252
            días"); los primeros cierres llegan con los 25 partidos de Liga
            MX y MLS del 26 al 28 de septiembre. Los avisos «Evento sin
            emparejar» de `odds_worker` NO son un fallo: `meta` solo contiene
            los partidos que tocan en esa ventana y el resto del feed se
            registra como sin emparejar (ruido que convendría bajar a debug).
      - [x] **Salir de "sin modelo activo" (2026-09-24, desplegado).** Sin modelo, el job
            de las 08:00 falla cada día (no sella nada) y la sombra del XI
            (2.B/2.C) no acumula. El reentrenamiento mensual es el 1-oct.
            Hecho en local, pendiente de desplegar: `train --bootstrap` diario
            a las 01:05 UTC que solo entrena (~3,5 h) si no hay modelo activo
            y el cierre sharp ya pasaría la misma puerta de frescura
            (`MARKET_MAX_AGE_DAYS`, compartido con `promotion.py`); si no,
            sale en segundos. Tarjetas nuevas en `/control`: puerta comercial
            (mismo `shadow_sharp.report` que decide) y último entrenamiento
            con sus motivos. `db/019` para `v_clv_daily`. Desplegado y
            verificado: prueba en seco "mercado de 252 días" (sale sin
            entrenar), `019` aplicada con el GRANT a `qf_readonly` intacto, y
            la tarjeta de la puerta leyendo 4 ofertas reales con stake.
- [x] **CONSECUENCIA GRAVE: `find_candidates` selecciona apuestas perdedoras.**
      Resuelto el 2026-09-23 con el paso 4: el criterio del modelo se sustituyó
      por el de precio sharp (punto 2.A), y la publicación sigue pausada hasta
      pasar la puerta.
- [ ] ~~Calibrar `UNCERTAINTY_Z` contra ROI~~
- [~] **Medir la incertidumbre RELATIVA al mercado, no la absoluta.**
      Superado (2026-09-24) por el mismo motivo: servía para decidir apuestas
      a partir del edge del modelo, y ese criterio ya no existe. Reabrir solo
      si el modelo vuelve a proponer apuestas.
- [~] **La ordenación por media/sd no arregla la selección adversa.**
      Superado: el criterio sharp no ordena por edge del modelo.

### 2.E — No volver a proponer (medido negativo, está en progreso.md)

Ajuste por estado del partido, PSxG como objetivo, más ligas, mercados
derivados como fuente de edge, Elo como sustituto, y barridos de
hiperparámetros. Todos medidos, todos negativos o en la cuarta decimal.
También (2026-10-03): el modelo contra la cuota TEMPRANA de Pinnacle; no
anticipa el movimiento (`eval/early_vs_close.py`). El más-menos por jugador
(`model/masmenos.py`). Y entrenar para apartarse del mercado (Hubáček y Šír,
`eval/decorrelacion.py`): con la información de goles y xG no hay nada de lo
que apartarse con provecho.

## Verificación pendiente CON DATOS REALES 🔬

Ya hay Postgres local con 50.079 partidos reales (11 ligas + 2 copas). Queda:

- [ ] Revisar si la calibración supera su puerta. Que la descarte NO es un
      fallo: significa que el modelo ya estaba calibrado.
- [ ] Revisar si el modelo de residuo supera la suya. Se entrena siempre pero
      solo se aplica con `RESIDUAL_ENABLED=1`.
- [x] Verificar `ingest/lineups.py` contra la API real (2026-09-22). `_parse_side`
      cuadra con la respuesta real: `formation`, 11 titulares, `pos` en G/D/M/F
      —que es lo que `availability()` cuenta por posición—, `number`, `coach` y
      `player_id`. El contrato de orden [local, visitante] también se confirma.
- [x] Verificar `ingest/fixtures.py` con una competición `cross_league` real
      (2026-09-22). `_resolve` no dio de alta ni un equipo bajo `eu.ucl` y la
      exigencia de coincidencia exacta evitó dos contaminaciones reales que el
      difuso proponía. Ver `progreso.md`.

- [x] **Nombres sin resolver en producción (2026-09-24).** 36 pendientes:
      uno real, `Coventry City` (The Odds API; el club lo dio de alta
      API-Football como `Coventry` al ascender) → alias en `db/020`; se
      estaban descartando sus cuotas de Premier. Los otros 35 son clubes de
      ligas fuera del catálogo en copas europeas (grupo 1 de abajo). La alarma
      `nombres sin emparejar` ya no los cuenta: solo alarma lo que se ve en
      una liga doméstica o sin competición anotada. `resolve_team(seen_in=)`
      anota la competición del feed de The Odds API sin acotar la búsqueda.
- [x] **Revisados (2026-09-25).** Producción: 35 pendientes, TODOS clubes de
      copas europeas fuera del catálogo (correcto rechazarlos: "Rangers"
      daba 92 contra Angers, "Celtic" 73 contra Celta). CSV: 228 nombres
      únicos, 109 ya resueltos; de los 119 restantes, 117 de copas y 2
      domésticos: "Den Bosch" (segunda neerlandesa, sin partidos esta
      temporada: nada que hacer) y "Real Racing Club de Santander", el
      nombre de The Odds API para Racing Santander, recién ascendido: SIN
      alias sus partidos de LaLiga no tenían cierre de Pinnacle → `db/027`.
      Comprobados además los 305 equipos de las 13 ligas domésticas contra
      la lista de partidos de The Odds API (gratuita): Racing era el único.
      Texto original:
- [ ] ~~**Cerrar los 163 alias que siguen sin emparejar.**~~ Tras el bootstrap con
      las dos claves quedan en `aliases_pendientes.csv`. Se reparten en tres
      grupos y solo uno es trabajo de verdad:
      1. Clubes de ligas que el catálogo NO cubre (Celtic, Rangers,
         Galatasaray, Slavia Praha, Bodø/Glimt…): aparecen en Champions y
         Europa League y son irresolubles por diseño. Se descartan, y el
         partido de copa con ellos también.
      2. Equipos que ya no están en la competición en la temporada 2024 que
         permite el plan Free.
      3. Nombres nuevos reales, que son los que hay que mapear a mano.
      Cuidado con el difuso al revisarlos: propuso `Remo`→Grêmio (80) y
      `Atlético Huracán`→Atlético Tucumán (81). Ambos falsos.

## En progreso 🟡

- [ ] **Fase 2–4 — evaluación y challengers point-in-time (orden solicitado
      2026-09-22).** Implementar sin saltarse dependencias:
      1. Elo secuencial point-in-time con 1X2 completo.
      2. Comparación Elo / Dixon-Coles / Pinnacle sobre las mismas filas.
      3. Puerta champion/challenger estricta y hash completo del dataset.
      4. Feature builder point-in-time con pruebas contra leakage.
      5. Ablaciones de descanso, Elo, forma y tiros.
      6. Logística multinomial deportiva y anclada al mercado, solo challenger.
      7. Mantener la captura de alineaciones y medir su preparación muestral.
      8. Challenger en sombra que ajuste `log(lambda_home/away)` por el XI.
      9. Registrar y liquidar CLV del periodo en sombra sin publicar apuestas.
      Ningún challenger se activa automáticamente; la promoción exige mejora
      temporal fuera de muestra y, cuando exista muestra, CLV.
      Código y migración local verificados; pendiente demostrar señal con
      cuotas recientes y acumular la muestra de sombra antes de promover.

## Completadas 🟢

- [x] **Fix: liquidación del hándicap asiático en líneas de cuarto**
      (2026-09-23). `clv._settle_outcome` devuelve ahora (outcome, fracción
      ganada, fracción devuelta) y `settle_profit` paga lo ganado a cuota y lo
      devuelto a 1. Antes medio-ganada y medio-perdida solo cuadraban a 2,00.
      `tests/test_liquidacion_ah.py`. `pick_results` estaba vacía: nada que
      rehacer.

- [x] **Plan Pro de API-Football: cadena operativa desbloqueada** (2026-09-22).
      Temporada en curso accesible, 300 req/min, 7.500/día. Primera ingesta
      real de calendario: 173 partidos programados en 12 competiciones.
      `results.py` cierra y encadena la liquidación. Quedan fuera solo los
      clubes de copa cuyas ligas no están en el catálogo, que es el diseño.
- [x] **`db/013_aliases_api_football.sql`** (2026-09-22). Cinco alias de la
      temporada en curso y cuatro altas de clubes que de verdad faltaban
      (Remo, Gimnasia Mendoza, Estudiantes Río Cuarto, Atlante). Los cuatro
      tenían un candidato difuso FALSO por encima del suelo de sugerencia.
- [x] **Dos alarmas que estaban permanentemente en rojo** (2026-09-22). El
      chequeo de calendario preguntaba por 10 días cuando la ingesta trae 21,
      así que saltaba en 10 competiciones a la vez cada parón de selecciones; y
      `history_fd._ensure_team` insertaba el alias con SQL directo en vez de
      `register_alias`, dejando 362 nombres marcados como pendientes para
      siempre. Una alarma que siempre suena no se lee el día que importa.

- [x] **Claves de API-Football y The Odds API configuradas y verificadas**
      (2026-09-22). Los 13 `odds_api_key` existen y están activos; los 13
      `api_football_id` apuntan a la competición correcta. Tres bugs del
      cliente salieron al usarlo de verdad: ritmo de llamadas 17× por encima
      del plan Free, reintento ciego del 429 y reintento de errores de plan
      (permanentes) que quemaba cuota. Ver `progreso.md`.
- [x] **Coste real de The Odds API con 13 competiciones** (2026-09-22). Medido
      sobre el calendario anunciado, no estimado: ~1.935 llamadas/mes, entre
      1.935 y 11.610 créditos/mes según mercados y regiones.
- [x] **Emparejamiento exacto obligatorio cuando no hay liga que acote**
      (2026-09-22). `resolve_team(..., exact=True)` por defecto. Cerraba un
      agujero real en `odds_worker` con los eventos de copa.

- [x] **Baseline Elo point-in-time** con empate, localía, ascendidos,
      actualización diferida del resultado y evaluación común histórica.
- [x] **Feature builder point-in-time** para Elo, descanso, forma y tiros;
      ablaciones y dos challenger multinomiales de solo diagnóstico.
- [x] **Infraestructura XI y CLV de sombra:** captura reintentable, ventana
      `post_xi` antes de cierre, ajuste de lambdas, baseline T-60, migración
      `db/012` aplicada en Postgres local y puerta de promoción estricta.
- [x] Fase 0 — captura de cuotas (`qf.ingest.odds_worker`).
- [x] Fase 1 — ingesta + modelo base (calendario, resultados, xG, aliases,
      salud, Dixon-Coles).
- [x] Arnés: `CLAUDE.md`, `scripts/harness_check.sh`, `harness/`.
- [x] Reorganización: se extrajo `pyton/quantfut.tar.gz` a la raíz del
      proyecto (era el repo completo, no solo los archivos sueltos que había
      en `pyton/`). Estructura ahora coincide con la documentada en README.md.
- [x] **Fix: bug de `tier` hardcoded en `persist()`.** `daily.py` guardaba
      TODOS los picks del día como `tier='paid'`, así que `/picks/free` y la
      vista gratuita de `/v1/picks` siempre devolvían vacío. Ahora
      `picks.assign_tiers()` decide el tier (los de mayor edge, `free`;
      configurable con `FREE_PICKS_PER_DAY`, default 2) antes de persistir, y
      `daily.py` usa ese mismo reparto para Telegram (que es opcional/no-op
      sin token) en vez de que Telegram decida el tier.
- [x] **API — endpoints de catálogo y ficha de partido.** Añadidos
      `GET /leagues`, `GET /teams`, `GET /matches/{match_id}` (público, con
      predicción recortada al tier gratuito). Antes no existía forma de que
      la web listara ligas/equipos sin tocar la BD directamente.
- [x] **API — paginación.** `limit`/`offset` en `/picks/free` y `/v1/picks`
      (antes devolvían todo sin límite).
- [x] **Modelo por liga con pooling parcial.** `model/dixon_coles.py`: ventaja
      de local e intercepto de goles POR LIGA, encogidos hacia la media global
      (equivalente MAP de un jerárquico bayesiano, sin PyMC ni GPU). De paso
      se corrigió que los equipos se indexaban solo por nombre: dos ligas con
      un "Santos" fusionaban sus historiales en silencio.
- [x] **Calibración** (`model/calibration.py`). Corrección afín en log-espacio
      sobre las lambdas, no sobre el 1X2: así los ~150 mercados siguen siendo
      coherentes entre sí. Con puerta de validación temporal que la descarta
      si no mejora fuera de muestra.
- [x] **Riesgo de portafolio correlacionado** (`publish/picks.py`). Sustituye
      el tope ingenuo de suma de stakes por una sigma conjunta con matriz de
      correlación (riesgo de modelo común + misma liga + misma dirección).
- [x] **GBM sobre el residuo del mercado** (`model/residual.py`). Se entrena
      siempre, se aplica solo con `RESIDUAL_ENABLED=1` y tras superar su
      validación. Desactivado por defecto: corrige solo el 1X2.
- [x] **Ingesta de alineaciones a T-60** (`ingest/lineups.py`). La tabla
      `lineups` existía desde el día uno y nada la escribía. En el crontab
      cada 5 min, ventana T-90..T-20.
- [x] **Suite de tests** (`tests/`, 48 casos) + `requirements-dev.txt`.
      `scripts/harness_check.sh` los ejecuta.
- [x] **Fix: desajuste de versión de artefacto.** `train.py` guardaba
      `dc_2026.09.21.pkl` pero `daily.py` cargaba `dc_{MODEL_VERSION}.pkl`.
      Habría roto el job diario en el primer reentrenamiento. Ahora se
      resuelve el modelo activo desde `model_artifacts`.
- [x] **Ponderación óptima modelo/mercado** (`model/meta.py`). Estima
      `w_model` por log-loss fuera de muestra, con pesos por liga encogidos
      hacia el global. Se estima y publica SIEMPRE en `/model-card`; aplicarla
      en producción requiere `META_BLEND_ENABLED=1`. Excluyente con el modelo
      de residuo (ambos fusionan con el mercado; juntos lo contarían dos
      veces) — `daily.py` avisa y prioriza la mezcla.
- [x] **Fix CRÍTICO: unidades del stake.** `kelly()` devolvía fracción de
      banca (0.0067) pero todo el sistema la leía como unidades. El descarte
      `stake <= 0.05` de `find_candidates` eliminaba TODOS los picks con edge
      realista (3-10%): el sistema habría publicado CERO picks para siempre
      sin dar ningún error. Contrato ahora fijado por
      `tests/test_kelly_units.py`: 1 unidad = 1% de banca.
- [x] **Ratings dinámicos con filtro de Kalman** (`model/kalman.py`). La fuerza
      como estado latente en vez de fija con decaimiento.
- [x] **Bundesliga, Ligue 1 y Primeira** (2026-09-22). `db/010` + `db/011`.
      No por sí mismas —aunque son apostables— sino porque eran las tres que
      más partidos de copa descartaban. Los cruces utilizables pasaron de 406
      a 1.111.
- [x] **MLS, Champions y Europa League** (2026-09-22). `db/007_competiciones.sql`
      separa competición (`matches.league_id`) de liga doméstica del equipo
      (`teams.league_id`); `ingest/uefa_cups.py` carga el histórico de copas
      desde los `.rds` de worldfootballR_data (única fuente gratuita: ese
      release no publica CSV); `model/dixon_coles.py` gana el término
      `strength` de fuerza relativa entre ligas, que los cruces europeos son
      lo único que identifica.
- [x] **xG de Argentina** (2026-09-22). Pasó de 0% a 62,5%. No hacía falta
      técnica nueva: la dependencia `pyreadr`, que antes no compensaba por una
      sola liga, ya era obligatoria para las copas europeas.
- [x] **Fix: `harness_check.sh` daba OK saltándose los tests.** Elegía
      `python3`, que en Windows resuelve al stub de la Microsoft Store: tiene
      `--version` y ninguna dependencia. Ahora prefiere `.venv` y FALLA si no
      encuentra pytest, en vez de avisar y seguir.

## Nota sobre `pyton/` — BORRADA (2026-09-25)

Borrada con confirmación del usuario. De sus 11 archivos, 9 tenían copia
en `src/`, `scripts/` o `db/`; `xg_fbref.py` era el módulo retirado a
propósito el 2026-09-24. Lo único sin copia, `quantfut.tar.gz` (la versión
inicial del proyecto, sin secretos), se conserva en
`harness/archivo/quantfut_version_inicial.tar.gz` porque no hay git.

### Continuación NBA autorizada 2026-10-05
- [x] F2: cruce conservador ESPN→NBA: 596/606 identidades y equipos comprobados, diez conflictos separados; capturas públicas con hash.
- [x] F3/F4: calendario y validador de disponibilidad por partido/PIT; 436 escenarios condicionales y proyección acotada de minutos implementados. Disponibilidad y rol reales siguen pendientes.
- [x] F5: diagnóstico discreto del replay comprobado, sin ajustar ni promover parámetros.
- [x] F6: contrato/revalidación de cuotas y outbox NBA; prueba local y rechazo de picks insuficientes. Enlace explícito al bot y chat de alertas de fútbol elegido por el usuario.
- [x] Evidencia NBA-EV-035–050, ejecuciones NBA-RUN-011–015, código congelado; 79 NBA/606 fútbol aprobadas, puertas pendientes.
- [ ] Configuración activa del bot/chat de fútbol disponible en el entorno/ruta autorizados; ejecutar prueba técnica real y medir entrega.
- [ ] Disponibilidad por partido y rol/minutos validados; diez identidades no resueltas y rookies sin historial conservan abstención.
- [ ] Fuente de props, contratos y frescura utilizables; supervivencia de precio, límites compartidos del bot y confirmación prospectiva antes de promover/publicar.

### Scrapers y datos adicionales NBA — 2026-10-05
- [x] Inventariar repos públicos, fijar commits y revisar código/datos reales sin ejecutar proyectos de terceros: diez repos y 52 archivos verificados.
- [x] Auditar horarios históricos y muestras de reportes de lesiones: calendarios sin horas; PDF actual 403. No se acredita PIT histórico.
- [x] Integrar observaciones con namespace/captura explícitos y auditoría: alineaciones previstas RotoWire y piloto de quintetos PBP Stats; ninguna promoción médica o comercial.
- [x] Ejecutar pruebas relevantes, conservar evidencia y actualizar registro de fases: 100 NBA y 606 fútbol pasan.
- [ ] Ampliar quintetos en lotes auditados y obtener sustituciones cronológicas del PBP; validar reloj/IDs de alineaciones y publicación médica por partido antes de usar contexto en pronósticos.

### NBA — The Odds API existente, revisión 2026-10-05

- [x] Comprobar con la clave existente deportes NBA/pretemporada, eventos y muestra real de cuotas; cuatro créditos usados, sin guardar clave o activar polling.
- [x] Documentar mercados, latencia efectiva, acceso histórico todavía no probado y presupuesto compartido con fútbol.
- [ ] Implementar cliente NBA persistente con reserva coordinada de créditos y evaluación específica de props alternativos; verificar reglas, reloj e identidades antes de promover contratos.
- [x] Verificar acceso histórico tras confirmar el usuario su plan de pago: muestra NBA `player_rebounds`, 242 cuotas, ocho casas; once créditos. Conservar discrepancias del reloj de snapshot.

### NBA — austin-pesina/nba_scrapes, 2026-10-05

- [x] Descargar rama principal completa con commit y hashes: seis archivos, 15,023 bytes.
- [x] Comprobar datasets/releases/Actions: cero archivos de datos, cero releases y cero artefactos disponibles; no ejecutar los scripts o conectar Snowflake.
- [x] Documentar cobertura real: herramientas Basketball Reference 2025–26, sin cuotas o lesiones; cero filas importadas y cero créditos The Odds API.
- [x] Sellar descarga y revisión en NBA-RUN-021 y registro de evidencias; integridad de archivos comprobada.

### NBA — EdgarParra565/player-performance-forecaster, 2026-10-05

- [x] Inventariar 365 archivos del commit y descargar 14 referencias verificadas; CSV vacío, base no publicada en main.
- [x] Revisar descarga masiva nba_api y límites de temporada/caché/PIT; separar cuotas reales de backfill con precios supuestos.
- [x] Registrar NBA-RUN-022, informe y documento; 80 evidencias verificadas, 33 archivos propios sin cambios, puertas pendientes.
- [ ] Completar huecos estadísticos con consultas por temporada y competición, sin importar el proyecto externo o sus precios supuestos.
- [x] Auditar ahorro/cobertura: 320 partidos regulares pendientes en cinco temporadas; prueba oficial gratuita terminó en ReadTimeout, cero filas o créditos nuevos.
- [x] Documentar uso de fuentes gratuitas y presupuesto separado para precios reales; sin activar descarga masiva de cuotas.

### NBA — recuperación gratuita de históricos, autorizada 2026-10-05

- [x] Crear lista exacta de pendientes por ID/temporada y diagnóstico reproducible: 395 partidos conocidos pendientes, incluidos 320 regulares; 299 regulares contienen minutos inválidos en la fuente.
- [x] Implementar captura NBA acotada y reanudable de boxscores/rotaciones; guardar originales, hashes y errores, detener lote ante acceso fallido.
- [x] Probar boxscores y GameRotation en muestra real: API oficial ReadTimeout y CDN 403; cero partidos o stints importados. Validadores conservan las restricciones existentes.
- [x] Probar lesiones históricas: tres PDF oficiales, ocho páginas verificadas, 84 observaciones de 30 jugadores; usar hora de cabecera, no nombre del archivo. Identidades y disponibilidad original siguen sin acreditar.
- [x] Validar con 136 pruebas NBA y 609 de harness; congelar 37 archivos propios y registrar NBA-RUN-024–026, 100 evidencias verificadas y 60 eventos de ledger; puertas pendientes.
- [ ] Recuperar físicamente los 395 pendientes con una fuente accesible y validar cada partido antes de importar; certificar calendarios de playoffs anteriores.
- [ ] Obtener rotaciones reales y conciliar tiempos, quintetos y minutos; los validadores probados con fixtures no acreditan cobertura real.
- [ ] Resolver IDs y horarios oficiales de las lesiones; ampliar archivo histórico y capturar disponibilidad prospectiva antes de habilitar señales médicas en picks.

### NBA — contraste de alternativas propuesto por el usuario, 2026-10-05

- [x] Fijar siete repositorios y comprobar interfaz, fuentes, actualización real y límites; no ejecutar proyectos externos.
- [x] Descargar archivo de transacciones JaseZiv y release ESPN 2025–26, comprobar hashes y cobertura. Mantener separados del dataset principal.
- [x] Probar fuente independiente Basketball Reference y conciliar un partido pendiente: 20 participantes, 240 minutos por equipo y estadísticas concordantes, sin errores del validador.
- [x] Documentar candidatos ESPN para 88 pendientes recientes, ausencia de pretemporada y límites de precisión/IDs/PIT; sin cuotas de apuestas o créditos The Odds API.
- [x] Formalizar adaptador Basketball Reference y cruce de IDs con caché/validación: ampliación de 159 partidos y 3,317 filas a versión nueva, linaje conservado; recuperación completa sigue pendiente.
- [ ] Recuperar pretemporada por separado; no equiparar tipo de temporada ESPN a prefijos NBA sin contraste del calendario.

### NBA — ampliación Basketball Reference autorizada 2026-10-05

- [x] Formalizar parser diario y cruce por fecha/localía/equipos/identidad: nombres exactos con acentos y variantes únicas de sufijos/puntos; sin apodos, generaciones contradictorias o candidatos múltiples. No reparar minutos o inferir DNP.
- [x] Capturar con caché, lotes de hasta 20 y seis segundos entre solicitudes: 140 páginas válidas, parada y respuesta conservada ante 403 del 2024-03-11; fechas posteriores no solicitadas.
- [x] Probar identidad/estadística/reloj/caché/integridad: 172 NBA y 609 harness aprobadas. Nueva versión con 159 partidos/3,317 filas; código propio congelado en 39 archivos.
- [x] Verificar todos los nuevos valores contra páginas raw y volver a conciliar los 159 partidos; 597 identidades consistentes, 154,058 filas previas conservadas; dataset ampliado 157,375 filas, modelo/fútbol/puertas preservados.
- [ ] Corroborar los nueve casos recibidos separados (siete diferencias de REB/AST, una referencia parcial y un estado desconocido) sin forzar aceptación.
- [ ] Recuperar los 152 regulares sin página válida tras el 403 y pendientes de otras competiciones: total restante 161 regulares, 71 pretemporada, tres playoffs y un play-in.

### NBA — Black Falcon / Apify, autorizado 2026-10-05

- [x] Preparar piloto de diez pendientes con IDs ESPN candidatos y referencias NBA; seis regulares, dos playoffs, un play-in y uno de pretemporada.
- [x] Ejecutar desde la sesión Apify existente: 282 filas descargadas, US$0.142 mostrado, máximo US$0.25; entrada/log/recibo/screenshot/JSON íntegro y hashes conservados, cero créditos The Odds API.
- [x] Validar identidad, estadística, DNP y precisión temporal: 247 candidatos NBA, cero diferencias P/R/A entre participantes; 53 diferencias null/cero DNP preservadas. Enteros de minutos no importados, pretemporada sin localía/IDs corroborados; dataset aceptado preservado.
- [ ] Recuperar segundos de minutos y referencias faltantes mediante fuente adecuada: Black Falcon repite los nueve partidos del ESPN previo; no ampliar ese flujo para solucionar precisión que no ofrece.

### NBA — servicios auxiliares para completar datos, autorizado 2026-10-05

- [x] Verificar cobertura real y precisión de servicios Apify; promedios de temporada/minutos enteros descartados; Flashscore decimal condicionado a concordancia individual y calendario NBA contrastado.
- [x] Ejecutar tres capturas Flashscore y dos de calendario NBA con límites: 6,631 registros Flashscore y 100 de calendario; US$2.064 mostrado, cero créditos Odds API; originales/entradas/logs/recibos conservados.
- [x] Ampliar fuentes útiles y conciliar íntegramente: 67 partidos/1,713 filas agregados, 157,375 filas previas conservadas; 6,052/6,150 regulares, 98 regulares y 71 pretemporada aún pendientes.
- [ ] Resolver identidades y discrepancias de los 169 boxscores restantes; 62 candidatos de pretemporada y calendario de sus 71 IDs ya capturados. No repetir descarga masiva para corregir problemas de conciliación.

### NBA — continuación de pendientes autorizada 2026-10-05

- [x] Auditar los169 candidatos:166 resúmenes ESPN;16 partidos/515 filas adicionales (3regular,13pretemporada),159603 filas finales. Mantener separados95regular y58pretemporada pendientes; no forzar IDs ni discrepancias.
- [x] Ampliar reportes médicos:486PDFs/36300 registros nominales; timestamp de cabecera y recibo actual;43675 filas enlazadas a partido,36063 a jugador. Segundo motor verifica todos; HTTP403 conservado y descarga detenida.
- [x] Recuperar rotaciones cronológicas:5161partidos/217334tramos; cinco jugadores, períodos/prórrogas, continuidad y minutos con cuantización por intervalo continuo del jugador;891partidos separados.
- [x] Ampliar props históricos acotados:20partidos/40snapshots de rebotes/2961pares válidos,420créditos de límite500; originales/temporalidad/cortes preservados, sin picks ni ROI.
- [x] Verificar datasets y preservación:19controles,6replaysPBP,40replayscuotas,486PDFs con segundo motor;609pruebas antes/después,39archivos NBA congelados y152evidencias previas verificados; NBA-RUN-033.
- [ ] Completar95regular/58pretemporada,330fechas médicas/cortes intradía y13nombres sin ID,891rotaciones separadas; ampliar puntos/asistencias/temporadas de props tras definir próximo presupuesto y reglas de liquidación. Informe:docs/nba_pendientes_recuperacion_20261005.md.

### NBA — fuentes Apify adicionales, autorizado 2026-10-06

- [x] Verificar cobertura y saldo; seis capturas de dos actores, US$2.341 del crédito gratuito. PBP sin acreditación de quintetos; cuotas sin timestamp original. Sin suscripciones/recargas ni créditos Odds API.
- [x] Conservar JSON completos, entradas, recibos, IDs y hashes; agregar Clippers–Nuggets 0012500052, 40 filas/30 participantes y diez DNP explícitos. Segundos exactos por equipo y PRA corroborados; 13 etiquetas de equipo contradictorias conservadas sin uso.
- [x] Sellar NBA-RUN-034: 159643 filas, 95 regulares/57 pretemporada pendientes; 71 calendarios/68 cruces exactos, 385 precios sin tiempo y 19 lesiones no históricas excluidos. 181 evidencias verificadas, 39 archivos NBA intactos, 609 pruebas antes/después. Informe: docs/nba_apify_fuentes_adicionales_20261006.md.
- [ ] Ampliar boxscores después de definir saldo/límite: diez partidos de 30 filas cuestan aproximadamente US$5 al precio observado, tope propuesto US$6; saldo disponible aproximado US$0.45. Resolver identidades y conflictos antes de importar. Props con timestamps, lesiones archivadas y rotaciones siguen requiriendo fuentes adecuadas.

### NBA — recuperación API-NBA autorizada 2026-10-06

- [x] Configurar la clave local excluida de Git; comprobar autenticación, plan y cuota sin conservar datos personales o secretos en evidencias. Plan NBA real Free; estado final declara70/100usadas.
- [x] Descubrir temporadas y calendario del proveedor; cruzar sus IDs con los 95 regulares y 57 de pretemporada pendientes. 72cruces únicos;80pendientes2025-26rechazados por plan. Sin contratación o exceso del límite local95.
- [x] Recuperar candidatos mediante consultas acotadas/reanudables; conservar originales, fechas y hashes.72boxscores/1543filas con minutos enteros;0partidos nuevos aceptados.159643filas previas preservadas. No inventar segundos ni resolver discrepancias por votación de fuentes.
- [x] Verificar el lote, documentar recuperación y bloqueos reales, ejecutar harness posterior y registrar evidencia NBA aislada sin modificar el modelo, fútbol, puertas o publicación.693pruebas antes/después;10controles;194evidencias,81eventos deledger; NBA-RUN-035.
- [ ] Obtener segundos individuales verificables y resolver discrepancias estadísticas/IDs para los72candidatos; acceso2025bloqueado para23regulares/57pretemporadas. Ampliar un plan no garantiza precisión ni recuperación; informe docs/nba_api_nba_recuperacion_20261006.md.

### NBA — auditoría de lineups Ramiro / pbpstats autorizada 2026-10-06

- [x] Fijar commit y descargar los CSV de lineups 2022–2026 con hashes y recibos; preservar boxscores y rotaciones aceptadas.
- [x] Contrastar cobertura, identidades, localía, períodos, continuidad, quintetos y minutos contra boxscores y PBP locales; separar discrepancias por partido.
- [x] Probar pbpstats sin consultas NBA automáticas; registrar formatos soportados y resultado real del contraste.
- [x] Conservar resultados reproducibles, pruebas e informe; registrar el incremento únicamente si satisface los controles existentes.

### NBA — ejecución de repositorios y scrapers históricos, autorizada 2026-10-06

- [x] Revisar y fijar código de las fuentes propuestas; ejecutar componentes de adquisición o parseo aislados y conservar resultados por repositorio.
- [x] Examinar el archivo corregido de pbpstats y contrastar PBP/quintetos de los partidos pendientes con las referencias existentes.
- [x] Procesar boxscores y PDFs disponibles, descubrir archivos médicos históricos y probar acceso público acotado; conservar bloqueos y no forzar aceptación.
- [x] Verificar preservación, cobertura incremental, pruebas e informe final; registrar lo ejecutado y las dependencias/accesos que impidan completar una fuente.

- [x] Instalar Java portátil y toolkit/MCP ZenRows solicitado para Claude Code; handshake stdio/44 herramientas, cero llamadas de proveedor.
- [ ] Pendientes actualizados en NBA-RUN-039: una excepción de boxscore regular, 37 rotaciones del censo y props históricos; pretemporada y censo médico diario completados. Véase docs/nba_completar_validar_20261006.md.


### NBA — transporte ZenRows para fuentes públicas bloqueadas, autorizado 2026-10-06

- [x] Comprobar autenticación/cuota y dirigir una muestra de solicitudes de los scrapers a ZenRows, con máximo100créditos, sin compras o suscripciones.
- [x] Conservar HTML/JSON/PDF originales y recibos, probar los componentes upstream y validar semántica; no interpretar HTTP200 como recuperación.
- [x] Integrar solo datos que pasan los controles existentes, registrar el alcance real de desbloqueo y verificar preservación/pruebas.

### NBA — completar y validar históricos, autorizado 2026-10-06

- [x] Ampliar capturas Basketball Reference por fecha para94regulares, con ZenRows y límite preventivo2500créditos; conciliar NBAStats/BRef y conservar originales, plantillas completas y overlays explícitos.
- [x] Recuperar4pretemporadas y ampliar rotaciones con PBP explícito; integrar únicamente quintetos/tiempos/estadísticas corroborados.
- [x] Revisar330fechas médicas y13identidades pendientes mediante archivos verificables y timestamps originales.
- [x] Ampliar puntos/asistencias con los80créditos restantes del límite500 de TheOddsAPI, sujeto a captura/validación; documentar presupuesto adicional que requiera el histórico completo.
- [x] Verificar preservación, cobertura, controles adversariales y harness posterior; sellar nueva corrida e informe sin promover datos rechazados.

- [ ] Pendientes verificados de NBA-RUN-039: excepción MM:SS subsegundo 0022400942; 37 rotaciones; intradía médico/PIT original; props multitemporada y reglas de liquidación. Véase docs/nba_completar_validar_20261006.md.

### NBA — segundos oficiales y rotaciones pendientes, autorizado 2026-10-06

- [x] Añadir al normalizador soporte optativo de segundos subsegundo acreditados por intervalos oficiales completos; conservar MM:SS original y rechazar DNP, fuentes alteradas, IDs contradictorios y gaps.
- [x] Reimportar el roster completo de Tony Bradley en una nueva versión; preservar las 164190 filas anteriores y los originales sellados.
- [x] Diagnosticar las 37 rotaciones mediante PBP CDN/V2 e intervalos locales; recuperar únicamente casos corroborados y conservar conflictos por evento.
- [x] Buscar fuentes alternativas acotadas para las capturas aún ausentes dentro de los límites vigentes, sin compras ni llamadas a props.
- [x] Ejecutar pruebas NBA, arnés posterior y verificación de las 2105 evidencias anteriores; registrar nueva corrida, informe y pendientes reales.

- [ ] Pendientes de NBA-RUN-040: nueve rotaciones con eventos/titulares sin corroborar; intradía médico/PIT original; props multitemporada y reglas de liquidación antes del backtest. Véase docs/nba_segundos_y_rotaciones_20261006.md.

### NBA — continuar pendientes de RUN-040, autorizado 2026-10-06

- [x] Obtener pruebas oficiales de titulares de prórroga y auditar eventos sin tiempo positivo de nueve rotaciones, sin inventar alineaciones ni modificar evidencias selladas.
- [x] Descubrir índices médicos intradía, capturar reportes anteriores al inicio y comparar encabezados, entidades y cambios de estado; conservar recepción actual y límites PIT.
- [x] Revisar históricos de props públicos fijando commits y contratos de datos; conservar límite local500 agotado y preparar una ampliación concreta si las fuentes gratuitas no contienen precios/cortes históricos.
- [x] Verificar preservación, controles, pruebas y arnés posterior; registrar nueva corrida y pendientes con cobertura real.

- [ ] Estado histórico de NBA-RUN-041 (sustituido por RUN-042): tres rotaciones; corte médico24-oct-2023, intradía completo/recepción original; autorización720créditos para piloto de props y reglas históricas. Véase docs/nba_pendientes_intradia_20261006.md.


### NBA — continuar pendientes de RUN-041, autorizado 2026-10-06

- [x] Fijar y recuperar el archivo público de props con timestamps, verificar blobs y cruzar eventos/identidades/cronología sin gastar nuevos créditos OddsAPI.
- [x] Revisar las rutas oficiales de actas de las tres rotaciones con transporte acotado y conservar conflictos sin inventar intervalos.
- [x] Inventariar cortes del primer día2023-24 y versiones intradía de fechas de muestra; distinguir ausencia de publicación/acceso de un bloqueo deIP y conservar límites de recepción histórica.
- [x] Verificar evidencias4939,41corridas y89eventos previos, presupuestos/pruebas/arnés posterior; sellar nuevas versiones y pendientes reales.

- [ ] Pendientes de NBA-RUN-042: props de rebotes/asistencias e historia/cortes faltantes; intradía de otras fechas, recepción original y reglas de liquidación. Rotaciones regulares6150/6150. Véase docs/nba_props_y_rotaciones_20261007.md.

### NBA — continuar pendientes de RUN-042, autorizado 2026-10-07

- [x] Fijar y revisar archivos públicos adicionales de props; aceptar solo cuotas con procedencia, identidad y cronología acreditadas, conservando cuarentena y cero créditos nuevos OddsAPI.
- [x] Corroborar horarios del censo regular con calendarios independientes y recuperar los PDFs elegibles a T−60 que falten; conservar encabezados y límites de recepción original.
- [x] Revisar archivos médicos públicos y uniones exactas de identidad/evento para resolver huecos con nuevas pruebas, sin modificar registros sellados ni inferir tiempos.
- [x] Verificar las 9.641 evidencias, 42 corridas y 91 eventos anteriores, presupuestos, controles y arnés posterior; registrar nuevas versiones y pendientes reales.

## Web — adaptación visual de TennisPredictions (2026-10-07)

- [x] Analizar la portada pública y conservar copia local con SingleFile CLI.
- [x] Adaptar portada, calendario semanal, búsqueda, filtros y filas por liga.
- [x] Aplicar la paleta azul noche/pizarra y verde esmeralda aportada por el usuario.
- [x] Conservar datos demo separados, fichas existentes y estados de error reales.
- [x] Revisar móvil/escritorio e integración pública; propuesta documentada en
      `docs/web_diseno_tennispredictions_20261007.md`.
- [ ] Fase posterior propuesta: alimentar el nuevo tablero con la agenda real,
      sin cambiar el criterio de publicación. No se desplegó esta versión.

## Web — acceso, cuenta y suscripciones (2026-10-07)

Alcance confirmado por el usuario: copiar el recorrido visual y el modelo de
paquetes/suscripciones de TennisPredictions; no su algoritmo predictivo.
- [x] Capturar las páginas públicas de planes y acceso; analizar panel visible.
- [x] Adaptar login/registro/recuperación, cuenta/preferencias y catálogo de picks.
- [x] Implementar planes 1/3/6 meses y club, selección y resumen del pedido.
- [x] Mantener precios de referencia y cobro/autenticación reales sin habilitar.
- [x] Validar importes, ausencia de derechos por UI y recorrido móvil/escritorio.
      13 pruebas frontend y 11 del servidor web; revisión 320/390/768/1024/1440.
      Modelo comercial documentado en docs/modelo_paquetes_suscripciones_20261007.md.

## Web — publicación autorizada (2026-10-07)

- [x] Ejecutar el arnés completo y las pruebas frontend antes de publicar.
- [x] Crear commit de producto 2266311, incluyendo solo el rediseño y sus registros.
- [x] Respaldar y publicar seis archivos de runtime en la API del servidor.
- [x] Comprobar hashes, salud y recorrido desde el dominio público; mantener
      los demás servicios sin recrear. Evidencia en docs/web_despliegue_20261007.md.

- [ ] NBA-RUN-043: 21 juegos sin selección médica T−60 concordante; versiones intradía adicionales, props/cortes faltantes, relojes de 27.151 candidatos, recepción histórica y liquidación. Informe: docs/nba_recuperacion_medica_y_props_20261007.md.

### NBA — continuar pendientes de RUN-043, autorizado 2026-10-07

- [x] Diagnosticar los 21 contextos médicos pendientes con relojes literales y fuentes independientes; conservar toda discrepancia sin corregir horarios por suposición.
- [x] Recuperar pruebas oficiales adicionales con llamadas acotadas y reservas dentro del techo ZenRows ya autorizado de 3.200; cero llamadas OddsAPI nuevas.
- [x] Validar selecciones retrospectivas nuevas y controles adversariales, preservando versiones selladas, recepción histórica y gates.
- [x] Verificar evidencias, cadena y arnés real antes/después; sellar NBA-RUN-044 y documentar pendientes reales.

- [ ] NBA-RUN-044: contexto médico BOS@NYK ausente en diez PDFs; versiones intradía, props/cortes, relojes de candidatos, recepción original y liquidación. Informe: docs/nba_horarios_medicos_corroborados_20261007.md.

### NBA — props, recepción y liquidación tras RUN-044, autorizado 2026-10-07

- [x] Recuperar archivos públicos adicionales de props con commits y blobs verificados; adoptar solo identidad/evento/precios/relojes acreditados y conservar candidatos separados.
- [x] Auditar recibos históricos, distinguir snapshot del proveedor de recepción original y registrar pruebas o faltantes sin retrofechar capturas.
- [x] Recuperar reglas primarias versionadas por casa/jurisdicción; documentar participación, prórroga, push, abandono, correcciones y vigencia, conservando aplicabilidad desconocida.
- [x] Verificar los datos y evidencias previos, controles y arnés posterior; sellar NBA-RUN-045 y el informe con presupuestos actuales sin compras.

- [ ] NBA-RUN-045: rebotes/asistencias y cortes faltantes; cuotas de casas LATAM, otros países/casas, recepción original/vigencia por ticket, relojes de candidatos y pendientes médicos. Informe: docs/nba_props_y_reglas_latam_20261007.md.

### NBA — aplicación de reglas y recepción tras RUN-045, autorizado 2026-10-07

- [x] Preservar y verificar las 45 corridas, 19.165 evidencias y 94 eventos anteriores; inventariar archivos de tickets/recibos en el alcance local.
- [x] Recuperar reglas oficiales adicionales de México y pruebas archivadas de versiones anteriores, con solicitudes acotadas y cero créditos pagados nuevos.
- [x] Preparar evaluación reproducible por ticket/mercado/periodo con estados desconocidos explícitos; probar participación, prórroga, push, integridad y jurisdicción sin atribuir contratos históricos inexistentes.
- [x] Validar datasets/gates y arnés posterior; sellar NBA-RUN-046 y documentar las entradas que todavía falten.

- [ ] NBA-RUN-046: aplicar únicamente con tickets/contratos reales; recepción histórica original ausente según usuario; cuotas LATAM, otras casas/países, rebotes/asistencias/cortes y pendientes médicos. Informe: docs/nba_reglas_archivadas_y_liquidacion_20261007.md.

- [x] NBA — corregir en una versión documental nueva el total final de pruebas RUN-046 usando el log y verificación sellados; conservar informe y corridas originales.

Informe canónico corregido de RUN-046: docs/nba_reglas_archivadas_y_liquidacion_v2_20261007.md; corrección documental NBA-RUN-047.

### NBA — todas las casas de la lista hispanohablante, autorizado 2026-10-07

- [x] Verificar el baseline RUN-047 y registrar las 22 combinaciones casa/país de México, Colombia, Perú y España; preservar los cinco perfiles anteriores.
- [x] Recuperar fuentes oficiales y revisar reglas NBA por mercado: participación, prórroga, push, suspensión y correcciones; separar páginas generales, contenido educativo, bloqueo y documentos con jurisdicción distinta.
- [x] Consultar historia archivada de forma acotada; verificar replays recuperables y no inferir recepción original ni vigencia contractual de tickets.
- [x] Crear catálogo y matriz completa con procedencia, hashes y desconocidos; validar preservación, arnés posterior y checkpoint NBA-RUN-048 sin liquidaciones ni créditos pagados nuevos.

- [ ] NBA-RUN-048: recuperar reglamentos NBA pendientes (BetPlay, Apuesta Total, BetMéxico, DoradoBet, Betsson Perú, Inkabet, Sportium Colombia), validar Te Apuesto online/Luckia y push/correcciones; obtener tickets/contratos y ampliar props LATAM/REB/AST. Matriz: docs/nba_casas_hispanohablantes_reglas_20261007.md.

### NBA — recuperación acotada con MCP tras RUN-048, autorizado 2026-10-07

- [x] Verificar las 48 corridas, 19.636 evidencias y 97 eventos previos antes de recuperar nuevas fuentes.
- [x] Probar seis reglamentos oficiales mediante ZenRows MCP con país explícito, reserva inicial de 150 y seguimiento explícito de 100 créditos; cota final 2.232/3.200; registrar contenido, gastos y fallos sin reintentos automáticos.
- [x] Auditar dos repositorios adicionales fijando commits y blobs; separar recomendaciones y líneas sintéticas de cuotas históricas verificables, sin llamadas OddsAPI.
- [x] Validar nuevas pruebas y preservación, ejecutar arnés posterior y sellar NBA-RUN-049 con los pendientes reales.

- [ ] NBA-RUN-049: Apuesta Total/BetMéxico/DoradoBet/Betsson Perú/Inkabet específicos NBA; Te Apuesto online/Luckia, ambigüedades BetPlay/Sportium CO y push/correcciones; contratos por ticket, cuotas LATAM/REB/AST/cortes, relojes de candidatos y contexto médico BOS–NYK. BetPlay y Sportium Colombia avanzaron con18 cláusulas. Informe: docs/nba_reglas_colombia_y_props_candidatos_20261007.md.

### NBA — consolidación deportiva y validación F4, autorizado 2026-10-07

- [x] Verificar RUN-049, 19.744 evidencias y cadena de 98 eventos; fijar fuentes y protocolo antes de calcular resultados nuevos.
- [x] Consolidar minutos de regulación desde rotaciones aceptadas y rosters con IDs NBA, conservando DNP, prórrogas, integridad y límites de recepción original.
- [x] Comparar distribución histórica de diez apariciones con referencia reciente de cinco encogida hacia veinte; evaluar tres temporadas/tres bloques, intervalos por fecha, abstenciones y estratos definidos por historial.
- [x] Probar exclusión de resultados del día/futuro e invariantes; ejecutar suite NBA/arnés, sellar RUN-050 y documentar avances y requisitos pendientes de F4.

- [ ] NBA-RUN-050: completar F4.1 por rol/contexto, F4.2 disponibilidad y minutos jerárquicos con variables as-of, F4.3 escenarios y conservación conjunta; calibrar/confirmar en cortes separados. G0–G9 pendientes. Informe: docs/nba_f4_minutos_regulacion_20261007.md.

### NBA — corregir calibración y coherencia F4, autorizado 2026-10-07

- [x] Verificar RUN-050 y fijar un protocolo antes de ajustar: train 2021-22, validación 2022-23, evaluación exploratoria 2023-24–2025-26; conservar la advertencia de histórico ya inspeccionado.
- [x] Ajustar amplitud por historial de minutos exclusivamente en train, con soporte 0–48 y estado explícito de validación; congelar parámetros antes de evaluar temporadas posteriores.
- [x] Implementar distribuciones conjuntas de minutos que sumen 240 por equipo y respeten activo/DNP, con abstención ante escenarios inviables; separar escenario de disponibilidad acreditada.
- [x] Probar separación temporal y restricciones, evaluar datos y escenarios completos sin atribuir información prepartido inexistente, ejecutar arnés posterior y sellar RUN-051 con límites y siguiente fase.

- [ ] NBA-RUN-051: continuar F5 en investigación con protocolo de tasa por minuto y splits congelados; excluir OT sin estadísticas por periodo. Conservar RUN-050 como referencia CRPS. Disponibilidad/rol y dependencia de rotación prospectiva de F4 siguen pendientes; G0–G9 no aprobados. Informe: docs/nba_f4_calibracion_y_coherencia_20261007.md.

### NBA — distribución de rebotes F5, autorizado 2026-10-07

- [x] Verificar RUN-051, traspaso y fuentes; fijar protocolo de rebotes sin OT, prior heredado, train2021-22/validación2022-23/evaluación2023-26 y métricas antes de ajustar.
- [x] Construir tasas con historia previa noOT y combinar con minutos RUN-050; ajustar dispersión NB solo en train, comparar Poisson de media reciente/mezcla Poisson/Gamma-Poisson/NB en validación y congelar elección antes de evaluación.
- [x] Evaluar CRPS/NLL/Brier/PIT discreto y masa central por fecha/temporada/bloques; separar diagnóstico de minutos ampliados y push/void sin contratos ni disponibilidad inventados.
- [x] Probar probabilidades, colas, temporalidad y contaminación; ejecutar suite NBA/arnés posterior, verificar evidencias y sellar RUN-052 con la referencia elegida y pendientes reales de F5/F6.

- [ ] NBA-RUN-052: F6 auditoría PIT/fugas/contexto y protocolo de confirmación futura; F5 calibración completa/rol/ritmo y OT con estadísticas por periodo. Disponibilidad/recepción/contratos y G0–G9 siguen pendientes. Informe: docs/nba_f5_distribucion_rebotes_20261007.md.

### NBA — ensayos locales de entrega y observación F6, autorizado 2026-10-07

- [x] Verificar RUN-052 y preservar sus 52 corridas, 19.873 evidencias y cadena de 109 eventos; fijar protocolo antes de los ensayos.
- [x] Probar reinicios, exclusión de duplicados, expiración, 429 y timeout del outbox local; conservar incertidumbre sin reintentos ciegos y registrar relojes de envío reales.
- [x] Evaluar demoras 0/15/30/60/120/300 segundos con snapshots de contrato/versionado; excluir revisiones recibidas después del corte y reportar observaciones censuradas sin interpolar cuotas.
- [x] Ejecutar suite NBA y arnés, revisar/sellar NBA-RUN-053 y documentar requisitos reales de Postgres, canal, recepción/contratos y confirmación F7. Ensayos sintéticos locales, cero mensajes externos y cero APIs pagadas; G6 pendiente.

- [ ] NBA-RUN-053: integrar outbox/ledger NBA aislados en Postgres, ensayar canal con configuración privada y medir contratos/acuse reales; completar F6 antes de activar F7. Propuesta F7 sin iniciar; disponibilidad/OT/recepción externa y G0–G9 pendientes. Informe: docs/nba_f6_entrega_y_observaciones_20261007.md.

### NBA — outbox Postgres aislado F6, autorizado 2026-10-08

- [x] Verificar RUN-053 y conservar 53 corridas/19.920 evidencias/111 eventos; usar PostgreSQL16 instalado fuera de PATH para clúster temporal NBA, autenticación privada y solo loopback.
- [x] Implementar esquema y adaptador NBA con sellado+cola y reclamación+intento atómicos, inmutabilidad, deduplicación y ausencia de reintentos ante incertidumbre.
- [x] Probar transacciones reales, concurrencia, rollback, interrupción, caducidad y reinicio del servidor; exportar evidencia sin credenciales y detener el clúster de ensayo.
- [x] Ejecutar suite NBA/arnés posterior, revisar y sellar RUN-054; conservar G6 pendiente hasta canal y cuotas reales, sin cambios en fútbol ni mensajes externos.

- [ ] NBA-RUN-054: configurar canal operativo privado y medir acuses/contratos reales para cerrar F6; operación/backup/rendimiento Postgres por validar antes de desplegar. F7 no iniciado, disponibilidad/OT/recepción anclada y gates pendientes. Informe: docs/nba_f6_postgres_durable_20261008.md.

### NBA — restauración y métricas de entrega F6, autorizado 2026-10-08

- [x] Verificar RUN-054: 54 corridas/19.962 evidencias/113 eventos; conservar código y datos fuente, sin valores privados en logs.
- [x] Probar pg_dump/pg_restore reales sobre una segunda base NBA; verificar igualdad de ledger/cola y permisos, sin modificar la base de fútbol ni la fuente del backup.
- [x] Preparar métricas comunes de ledger con acuses faltantes y anomalías temporales explícitas; usar credenciales de fútbol en el VPS según respuesta directa, con un único mensaje operativo NBA y sin copiar secretos al equipo local.
- [x] Ejecutar suite NBA en la base restaurada y arnés posterior, detener servidor, revisar/sellar RUN-055; canal/cuotas reales y F7 permanecen pendientes si no llegan credenciales.

- [ ] NBA-RUN-055: mejorar recorrido de entrega desde VPS y reunir muestra de acuses; capturar disponibilidad/contratos reales y anclar recepción. Backup en otro servidor/roles/retención y operación continua pendientes. Un mensaje aceptado no aprueba G6; F7 sin iniciar. Informe: docs/nba_f6_backup_y_canal_vps_20261008.md.

### NBA — entrega reutilizable, recuperación fuera del equipo y captura F6, autorizado 2026-10-08

- [x] Verificar RUN-055, congelar protocolo y preservar 55 corridas/20.038 evidencias/116 eventos; cero APIs de datos pagadas nuevas.
- [x] Probar transporte SSH reutilizable con máximo tres mensajes técnicos, relojes separados, caducidad y ausencia de reintentos; conservar muestras pequeñas sin aprobar p95.
- [x] Restaurar backup NBA en contenedor nuevo aislado del VPS, reconstruir roles sin contraseñas previas, comparar datos/permisos y conservar copia con hashes fuera del equipo.
- [x] Preparar captura propia de respuestas/contratos/contexto con procedencia, desconocidos y operación prospectiva; recuperar contexto NBA público si disponible sin retrofechar históricos.
- [x] Probar controles, verificar evidencias, ejecutar arnés posterior y sellar RUN-056; documentar entradas reales pendientes sin iniciar F7 por suposición.

- [ ] NBA-RUN-056: fuente funcional de cuotas/contratos LATAM y disponibilidad/rol previos, prórroga compatible, anclaje independiente, control de relojes, muestra operativa completa y backups periódicos/retención. Dos acuses calientes0,42/0,48s no aprueban p95. Copia/restauración VPS del ledger de ensayo verificadas; no respaldo integral histórico. Tres capturasNBA403. F7 draft_not_started. Informe: docs/nba_f6_transporte_y_recuperacion_vps_20261008.md.

### NBA — fuentes accesibles, anclaje y operación de captura, autorizado 2026-10-08

- [x] Verificar RUN056 y preservar56 corridas/20.143 evidencias/123eventos; fijar protocolo de recuperación gratuito antes de nuevas capturas.
- [x] Recuperar fuentes públicas NBA/ESPN y catálogos de cuotas LATAM, distinguir temporada/competición/roster/lesiones/estado y obtener datos originales accesibles sin APIs pagadas nuevas.
- [x] Implementar y probar anclaje RFC3161 externo con hash/nonce/cadena de certificados; acreditar existencia nueva sin retrofechar recibos históricos.
- [x] Preparar operación de captura NBA aislada y respaldos verificables con retención explícita; corregir controles de reloj/prórroga según evidencia disponible.
- [x] Validar controles y preservación, ejecutar arnés final, sellar RUN057 y señalar únicamente los requisitos reales aún no satisfechos.

- [ ] NBA-RUN-057: props individuales LATAM con contratos/reglas completos; disponibilidad/rol por partido y membresía oficial actual; modelo compatible con prórroga; muestra operativa completa/p95 y caducidad entre relojes; respaldo integral y copia periódica fuera del VPS. Captura de investigación activa cada 15 minutos, siete archivos diarios configurados, dos manifiestos RFC3161 verificados; Caliente VPS403. F7 draft_not_started. Informe: docs/nba_f6_captura_anclada_y_operacion_20261008.md.

### NBA — partido completo, contexto oficial y contratos, autorizado 2026-10-08

- [x] Preservar RUN057 y fijar fuentes/protocolo antes de consultar o ajustar modelos; excluir trabajo de copias periódicas por petición explícita del usuario.
- [x] Recuperar contexto oficial de equipos/partidos y mercados públicos disponibles, verificar IDs actuales y separar pertenencia, diagnóstico y disponibilidad por evento.
- [x] Construir una referencia causal de rebotes de partido completo que conserve juegos con prórroga, con protocolo retrospectivo fijado y evaluación de todos los partidos elegibles sin exclusión por OT posterior.
- [x] Revisar contratos/reglas aplicables y controles de reloj/caducidad; mantener desconocidos y límites de fuente, sin habilitar compras, apuestas o publicación comercial.
- [x] Validar cambios, verificar preservación y arnés final, actualizar propuesta F7 y sellar RUN058; dejar fuera nuevas copias periódicas.

- [ ] NBA-RUN-058: contratos reales de props LATAM, disponibilidad/rol y universo previo, dos identidades actuales, confirmación F7/revisión independiente, muestra operativa p95 y prueba real de caducidad. Referencia fullgame conserva OT y mejora CRPS retrospectivo; no promoción. Copias periódicas excluidas por el usuario. Nuevo manifiesto local preparado; envío de hash a DigiCert rechazado por revisión automática, requiere autorización específica. Informe: docs/nba_f6_partido_completo_y_contexto_oficial_20261008.md.

### NBA — sello externo autorizado del manifiesto RUN058, 2026-10-08

- [x] Verificar RUN058 y sus evidencias; preservar el manifiesto exacto y registrar la autorización del usuario antes del envío.
- [x] Enviar una solicitud RFC3161 con SHA256 y nonce a DigiCert, verificar contenido/cadena/nonce y rechazar controles alterados.
- [x] Documentar la prueba, ejecutar arnés posterior y sellar RUN059 sin modificar artefactos históricos ni iniciar F7 o copias periódicas.

NBA-RUN-059: el sello externo del manifiesto RUN058 queda verificado tras autorización expresa, a19:24:17UTC; el resto de pendientes F6/F7 permanece, nuevas copias periódicas excluidas. docs/nba_sello_externo_autorizado_20261008.md.

### NBA — piloto de props y contexto autorizado «ejecutalo», 2026-10-08

- [x] Preservar RUN059 y fijar diez históricos antes de consultar; reutilizar rebotes y añadir puntos/asistencias T−60 con tope incremental250 créditos, cuenta compartida y reserva conservadora.
- [x] Implementar captura acotada sin credenciales en archivos/logs ni reintentos; probar cuotas, fallos inciertos, presupuestos y cronología de pares.
- [x] Consultar máximo diez eventos actuales, contexto público y precios mexicanos disponibles; conservar ausencias, reglas/identidad/recepción desconocidas y bloquear promoción.
- [x] Verificar evidencias, controles y arnés posterior; sellar RUN060 e informar cobertura real. Sin apuestas, publicación, cambios VPS ni nuevas copias periódicas.

NBA-RUN-060: diez históricos con tres mercados al corte común y62observaciones médicas oficiales;2617pares identificados,21actuales;219/250créditos nuevos. Caliente navegador accesible, cero props individuales en dos eventos revisados. Contratos/recepción original/disponibilidad final y F6/F7 pendientes; copias periódicas excluidas. docs/nba_piloto_props_y_contexto_20261008.md.

### NBA — resolver fuentes y admisión por partido tras RUN060, 2026-10-08

- [x] Preservar las 60 corridas y evidencias previas; registrar protocolo de consultas públicas gratuitas, sin nuevos créditos pagados ni copias periódicas.
- [x] Recuperar reglas mexicanas pendientes, comprobar Betsson México y, por petición del usuario, 1xBet/Novibet México; verificar fuentes oficiales de convocatoria/estado por partido y distinguir acceso, publicación ausente y disponibilidad explícita.
- [x] Implementar admisión reproducible por evento que explique bloqueos concretos y próxima captura necesaria, sin deducir aptitud de Active ni sustituir cuotas mexicanas por estadounidenses.
- [x] Probar controles temporales, identidad y evidencia; verificar archivos y arnés posterior, registrar NBA-RUN-061 con avances y límites comprobados.

NBA-RUN-061: revisión 1xBet/Novibet México; normativa recuperada/legible y42jugadores listados por NBA. Cero pares individuales mexicanos verificados; disponibilidad final desconocida.19GETgratuitos,61pruebas. F6abierta/F7sin iniciar; nuevas copias periódicas excluidas. docs/nba_fuentes_1xbet_novibet_y_disponibilidad_20261008.md.

### NBA — selección europea solicitada, 2026-10-08

- [x] Incorporar 1xBet Europa, Betsson Europa, Codere Italia y Betano Reino Unido con sus claves oficiales y versiones diferenciadas de México.
- [x] Conectar la selección al cliente acotado y ofrecer un plan offline de descubrimiento/consulta por evento, sin nuevas consultas pagadas ni activación periódica.
- [x] Validar filtros, reservas de créditos y conservación de límites; documentar que catálogo de casas no acredita props, contratos ni disponibilidad y registrar NBA-RUN-062.

NBA-RUN-062: cuatro versiones europeas seleccionadas y conectadas al cliente acotado; plan offline,33pruebas pertinentes,0consultas API/0créditos. Cobertura de props y contratos por versión sin acreditar. F6abierta/F7sin iniciar; nuevas copias periódicas excluidas. docs/nba_casas_europeas_seleccionadas_20261008.md.

### NBA — comprobar cuotas de las cuatro versiones europeas, 2026-10-08

- [x] Preservar RUN062 y fijar un lote actual de hasta ocho eventos y56créditos antes de consultar; cuenta existente, sin reintentos ni captura periódica.
- [x] Consultar descubrimiento, mercados de equipos y PTS/REB/AST con filtro explícito; conservar precios reales, recepción, ausencias y límites por versión/evento.
- [x] Verificar recibos, presupuesto y controles; ejecutar arnés posterior y registrar NBA-RUN-063 sin convertir ausencia de muestra en ausencia universal ni habilitar operación.

NBA-RUN-063: ocho eventos/27consultas;72precios de equipos de1xBetEU,BetssonEU yBetanoUK;CodereITsin datos en muestra. Cero props PTS/REB/AST;29/56créditos. Ausencia acotada a muestra, cuatro pretemporada con inicio pasado y cuatro regulares lejanos. F6abierta/F7sin iniciar; copias periódicas excluidas. docs/nba_cuotas_europeas_comprobadas_20261008.md.

### NBA — cerrar suministro reutilizable de props, 2026-10-08

- [x] Preservar RUN063 y fijar captura nueva de props US/AU, máximo ocho eventos futuros y 32 créditos; mantener fuentes europeas como selección independiente.
- [x] Implementar captura reutilizable y exportación de pares reales PTS/REB/AST con recibos, líneas, precios y cobertura; distinguir captura funcional de admisión comercial.
- [x] Probar límites, selección exclusivamente futura, fallos y conservación; ejecutar captura real, verificar precios e identidades disponibles, registrar NBA-RUN-064.

NBA-RUN-064: suministro de props funcional y reutilizable. 36 pares nuevos (12 por mercado) de FanDuel/Sportsbet/Fanatics; 36 identidades verificadas, 2617 históricos conservados; 17/32 créditos. Captura de datos resuelta; contratos aplicables, disponibilidad final y validación operativa separados. F6 abierta/F7 sin iniciar; copias periódicas excluidas. docs/nba_props_fuente_funcional_20261008.md.

### NBA — conectar props y seguimiento prospectivo en simulación, 2026-10-08

- [x] Fijar protocolo exploratorio, conservar RUN064 y sellar predicciones antes de partidos; usar historia causal de partido completo y separar disponibilidad desconocida.
- [x] Implementar registro reproducible, selecciones hipotéticas con precios frescos y evaluación posterior contra boxscores oficiales, sin duplicar jugadores por casa ni promover modelos.
- [x] Ejecutar lote regular acotado a tres eventos/12 créditos, verificar predicciones reales pendientes y controles; arnés posterior y registro NBA-RUN-065. Sin apuestas ni nuevas copias periódicas.

NBA-RUN-065: piloto exploratorio prospectivo ejecutado. 51pares/12consultas/16créditos (12iniciales+4integrados prefijados);21versiones/15casos únicos,6frescos/2entradas hipotéticas,0apuestas. 499/17suiteNBA;800/16arnésgeneral. Evaluación oficial y resumen implementados; formato NBAweb comprobado con final2OT. IDsNBA de eventos, resultados futuros, disponibilidad final y confirmaciónF7/G7 pendientes; sin recolector ni nuevas copias periódicas. docs/nba_seguimiento_prospectivo_20261008.md.

### NBA — resolver pendientes del seguimiento y preparar su cierre verificable, 2026-10-08

- [x] Preservar RUN065 y resolver los tres vínculos NBA mediante páginas oficiales, equipos y hora exactos, sin cambiar registros sellados ni consumir nuevas cuotas.
- [x] Completar controles de disponibilidad y recepción de resultados: estado por evento, plazos de captura, vínculo de fuentes, evaluación de cohorte automática e informe de condiciones pendientes de partidos futuros.
- [x] Fijar metodología de lectura y CLV para investigación, probar flujos completos y rechazos; conservar separación entre piloto, confirmación y reglas de cuentas.
- [x] Ejecutar comprobaciones actuales, arnés final y registrar NBA-RUN-066; dejar fuera nuevas copias periódicas, apuestas y publicación.

NBA-RUN-066: tresIDsNBA resueltos con equipos/hora exactos y recibos200; cohorte15 intacta. Seguimiento local activado20–21octubre (equipo/Codex abiertos), ventanas previas, cierre mismo contrato y evaluación oficial idempotente. Cero créditos actuales/tresGETgratuitos; futurocierre máximo2créditos. Lectura/CLV congelados y borradorpotencia112días/300partidos; confirmación aún no abierta. 523/17suiteNBA;800/16arnés. Disponibilidad/finales futuros, contratos reales y recepción histórica original siguen sin acreditarse. Sin apuestas/copias periódicas. docs/nba_pendientes_resueltos_y_cierre_programado_20261008.md.

### NBA — cerrar dependencia local y consolidar pendientes por alcance, 2026-10-08

- [x] Preservar RUN066 y preparar traslado verificable de la misma cohorte a un servicio NBA aislado del VPS, sin modificar sellos ni ampliar créditos.
- [x] Probar paquete portable, identidad del ejecutor, exclusión concurrente, ventana/fin, recuperación de estado y no duplicación de consultas.
- [x] Desplegar y ejecutar un ciclo real sin tareas futuras debidas; retirar ejecución local duplicada y conservar seguimiento de salud/resultados del VPS.
- [x] Fijar requisitos científicos y comerciales por alcance, separar espera de evidencia de fallos técnicos; validación final y registro NBA-RUN-067. Sin apuestas, nuevas copias periódicas ni cambios de fútbol.

NBA-RUN-067: mismo piloto15casos en VPS,3fuentesNBA200, exclusión/reinicio/estado verificados; executorlocalretirado y protegido. Cero créditos actuales/futurocierremax2. Codex sóloobserva; captura sinPCencendido. Diseño científico/cuenta preparados; finales/estados futuros, muestra científica y contrato real requieren evidencia nueva. 531/17suiteNBA;800/16arnés. Sin apuestas/copiasperiódicas/cambiosfútbol. docs/nba_seguimiento_vps_y_pendientes_por_alcance_20261008.md.

### NBA — completar activación y alertas autónomas, 2026-10-09

- [x] Preservar RUN067, separar fuentes necesarias y cobertura opcional bloqueada; detener generación de nuevas copias periódicas sin borrar evidencia anterior.
- [x] Activar alertas operativas en el VPS con credenciales ya autorizadas, reclamación durable antes de enviar, límites y control exclusivo del contenedor piloto al terminar.
- [x] Validar ciclos reales, reinicio y conservación del estado/fútbol; dejar preparación científica y liquidación sujetas a evidencia real, sin promover puertas ni inventar disponibilidad.
- [x] Ejecutar pruebas y arnés, documentar servicios activos y límites, registrar NBA-RUN-068.

NBA-RUN-068: captura NBA, piloto y alertas operativas activos en VPS. ESPNválido/Caliente403en cuarentena explícita; nuevas copias periódicas desactivadas, originales conservados. MensajeTGconfirmado/sin reenvío; Type=notify corrige carrera inicial, exclusión y reinicio reales verificados. DosGET/0créditosactuales/futurocap2; 542/1NBA y800/16arnés. Fútbol intacto; confirmación y liquidación comercial conservan requisitos de evidencia. docs/nba_activacion_y_alertas_vps_20261009.md.

### NBA — publicar página de predicciones y resultados, 2026-10-09

- [x] Crear vista pública /nba con la cohorte sellada real, filtros y estados de resultados pendientes/evaluados; sin cuotas actuales inventadas ni acceso a secretos.
- [x] Incorporar lectura verificable de resultados oficiales y estados operativos sin ejecutar modelos ni consultas deportivas desde la web; fuentes del piloto montadas sólo para lectura.
- [x] Desplegar servicio NBA aislado y ruta en el proxy existente, validar HTTPS, conservación de fútbol y protecciones /admin y /control; comprobar página y filtros en el navegador disponible.
- [x] Ejecutar pruebas y arnés, documentar URL/operación y registrar NBA-RUN-069, conservando RUN068 y exclusión de copias periódicas.

- [ ] Completar revisión visual a 390 píxeles: el navegador mantuvo 700×572 pese a la solicitud de tamaño móvil. Reglas adaptativas implementadas; publicación y filtros verificados en el tamaño real disponible.

NBA-RUN-069: https://pronosticosdeportivos.pro/nba activa en VPS. 15 registros sellados, cinco jugadores, tres partidos; cero resultados oficiales todavía. Servicio de lectura aislado, resultados contrastados con cuerpos oficiales originales, sin claves ni nuevas consultas deportivas. Reinicio conserva proyección y estado original; fútbol y administración preservados. 558/2 NBA y 800/16 arnés. docs/nba_pagina_pronosticos_resultados_20261009.md.

### Web — menú superior Fútbol/NBA e histórico disponible, 2026-10-09

- [x] Comprobar el histórico NBA guardado y distinguir datos retrospectivos de pronósticos publicados antes de partidos.
- [x] Añadir enlaces superiores Fútbol/NBA en fútbol, conservarlos visibles en móvil y actualizar huellas de recursos públicos.
- [x] Publicar únicamente recursos web sobre la imagen actual de fútbol, con reversión, sin alterar trabajador, base ni piloto NBA; comprobar navegación de ida y vuelta.
- [x] Ejecutar comprobaciones y arnés final, documentar publicación y conservar registros sellados anteriores en NBA-RUN-070.

NBA-RUN-070: menú Fútbol/NBA publicado y navegación de ida/vuelta verificada. Histórico confirmado:164.218filas, 2021-10-19..2026-06-13; separado del piloto15casos/0resultados. Imagen derivada con tres recursos públicos, código original de backend conservado, trabajador/base/NBA sin recrear. Primer intento revertido; recuperación de arranque real pasó. 24pruebasUI y800/16arnés. Revisión visual móvil continúa pendiente por tamaño ignorado; reglas móviles implementadas. docs/nba_menu_e_historico_20261009.md.

### NBA — desarrollar todos los mercados con estadística primero, 2026-10-09

- [x] Recuperar seis estadísticas individuales y referencias oficiales de equipos mediante uniones exactas y reconciliación.
- [x] Desarrollar nueve mercados, calibrar sólo con validación anterior y comparar contra referencias con cobertura e intervalos.
- [x] Sellar extensión prospectiva separada, integrar web y lectura de resultados oficiales sin cambiar el piloto original.
- [x] Ejecutar pruebas, publicar en VPS aislado, verificar página y registrar NBA-RUN-071; conservar puertas y exclusión de copias periódicas.

NBA-RUN-071: nueve mercados desarrollados/calibrados con estadísticas sin cuotas. 157.962filas/6.108partidos regulares;42partidos discrepantes excluidos. 42pronósticos nuevos sellados y publicados,15originales conservados. Comparación2023–26 con referencias igualmente calibradas y coberturas;≥70% puntos/rebotes sobreestima acierto, no aptos como selecciones fiables70%. Lectura oficial con reconciliación/DNP separado,577/18suiteNBA+3integración y800/16arnés. Fútbol/proxy/piloto intactos;0cuotasAPI/0apuestas/sin nuevascopiasperiódicas. Puertas/confirmación y disponibilidad futura pendientes. docs/nba_nueve_mercados_estadistica_20261009.md.

### NBA — verificar clave y permisos efectivos de API-NBA, 2026-10-09

- [x] Comprobar credencial local privada existente sin imprimirla ni modificar capturas anteriores.
- [x] Consultar estado y acceso efectivo a temporadas recientes con un máximo de cinco solicitudes de datos, reserva de quince y sin reintentos automáticos.
- [x] Conservar respuestas sin datos personales, documentar limitaciones reales y corregir presupuesto operativo si el plan gratuito no permite la temporada actual. No activar tareas repetitivas sin acceso válido.

Clave existente verificada: Free activo, 100/día, temporadas 2025 y 2026 rechazadas. Calendario 2024 sin filtro de fecha válido, 1.406 partidos; fecha histórica rechazada. Cinco solicitudes de datos, dos estados, cabecera final 99 restantes. No se activa captura actual ni se contrata un plan; volumen suficiente no acredita permisos. docs/nba_api_nba_acceso_actual_20261009.md.

- [x] Marcador en vivo, backend (2026-10-11): db/056, `ingest/live.py`, cron
  cada 45 min, `partido.vivo` en el detalle móvil. Sin desplegar.
- [x] Franja de marcador en vivo en el pronóstico de Flutter (`LiveScoreStrip`).
- [x] db/056, API y cron de marcador en vivo desplegados en el VPS (2026-10-12).
- [ ] Marcador en vivo en el calendario de inicio.

- [x] Pestaña Mercados con radar y una tarjeta por familia de fútbol
  (`live_markets.dart`). Pendiente: NBA (experimental, sin tarjeta) y recompilar el APK.

- [x] Pantalla por mercado (Hoy / Anteriores) y endpoint de historial. Desplegado el 2026-10-12 (respaldo `quantfut-api-mobile-rewards:before-history`).

## Pestaña Pronósticos con todos los mercados del partido (2026-10-12)

Pedido del usuario: la pestaña Pronósticos del partido queda como su referencia (tarjeta «Análisis
estadístico» + lista de mercados con nivel + «Marcadores más probables») y los mercados se despliegan
también en el VPS. Decisiones (tomadas con el usuario): lista visible para todos con los gratis abiertos y
el resto con candado que solo dice la categoría; 1ª mitad solo si un modelo propio sale calibrado; cuota
justa (1/prob) etiquetada donde no hay cuota publicada.

- [x] Backend `api/partido_mercados.py`: filas desde (lambda, mu, rho) — mismos cálculos que `predictions.markets`
  (verificado: diferencia 0,0 en 40 predicciones) — resultado, doble oportunidad, empate no acción, goles,
  goles por equipo, ambos marcan, hándicap, gana a cero, marcadores; córners y tarjetas con
  `estadisticas_mercado`. Nivel por probabilidad (alta >=75, sólida >=60, moderada).
- [x] Acceso: abiertas = las del usuario (gratis/desbloqueadas) o todas con VIP; el resto candado sin línea,
  selección, probabilidad ni cuota, y sin orden por probabilidad (no filtra).
- [x] Flutter: pestaña Pronósticos nueva (análisis + lista + marcadores).
- [ ] 1ª mitad: modelo con los 59.752 partidos con goles al descanso + prueba de calibración. No publicar si no calibra.
- [x] Desplegado en el VPS y comprobado en el emulador (2026-10-12).
