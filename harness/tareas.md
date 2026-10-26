# Backlog — QuantFut

## Pendientes vivos — limpieza del 25-oct-2026

De 250 tareas abiertas, 134 se cerraron en su sitio con el motivo «(cerrada 25-oct: …)»: hechas, duplicadas, de
fuentes retiradas (API-Football, PitchAPI, soccerdata/ZenRows), de ligas retiradas o estados viejos de NBA. Quedan
116, todas en su sección original; esta lista es el índice. Regla para no volver a inflarla: solo bloquea lo que
hace perder dinero o datos; una idea nueva va a «Mejoras», no a «Fallos».

**Fallos que afectan a dinero o datos (Claude, primero):**
- ~~Cierres: desde el 22-oct 18:50 UTC no entraba ningún `close` en `odds_snapshots`~~ → resuelto en el PR #127
  (`qf.ingest.propline_cierres`, la liquidación espera al cierre hasta 48 h).
- ~~Clasificación y marcador en vivo sin fuente desde que se retiró API-Football~~ → resuelto el 25-oct: la
  clasificación se calcula con nuestros resultados y el vivo sale del listado diario de FotMob.
- ~~`estadisticas_jugador` convierte un dato ausente en 0~~ → cerrada: solo la escribía API-Football (última, 22-oct);
  las fuentes vivas (FotMob, SofaScore) guardan NULL.
- ~~Sombra del XI parada desde el 22-oct (solo cuotas `post_xi`), ERA5 con 175 celdas rechazadas al día, API con
  código anterior al 22-oct, lector de cuotas sin los alias `propline`~~ → resueltos el 25-oct (noche),
  `docs/auditoria_motores_datos_20261025_noche.md`.
- ~~Alta probabilidad publicada sin cuota (25-oct: 18 de 22; ampliada 323 de 385)~~ → resuelto el 25-oct (noche):
  captura con casas de los suscriptores y solo candidatos con cuota (`alta_prob_datos.cotizador`). Falta desplegar
  en el worker antes de la selección de las 08:00 UTC.

**Del titular (27):** credenciales y cuentas (Meta, Whop, AdMob, RevU/BitLabs, Tapjoy, Apple/iOS), revisión legal y
avisos legales en la web, Sentry, copia de seguridad fuera del servidor (destino), compilar y publicar la app,
decisiones abiertas (`SOFT_BOOKS`, push al sellar, cuotas de cierre de tenis, paquete de The Odds API para props,
lesiones ESPN en NBA, captura `nba-live13-price`, desplegar el productor NBA, apagar la automatización de Codex).

**Esperan datos, fecha o condición (31, y aparte la historia de once SofaScore):** compras y comprobaciones del 1-nov (cierres de Pinnacle, NBA); muestras
para puertas (calibración, residuo, cuatro brazos, `ajuste_xi`, alineación en F7, altitud, tarjetas y córners del
parley, 1xBet y la ampliada); tenis prospectivo; referidos cuando la app esté en Play; compromiso-revelación antes de
`CHAIN_GIT_REMOTE`; alinear `select_daily` antes de publicar picks; historia de once SofaScore para `availability`.

**Mejoras e ideas (55):** fases del motor F3-F6 y F8-F12, ideas de la literatura, mejoras NBA de la segunda auditoría,
tenis (viajes, cobertura histórica, identidades externas), app y web (contenidos, iOS, CSP, rutas internas en
`/model-card`), estadios duplicados.


## Tenis — datos y arquitectura inicial (2026-10-16)

Autorización del usuario (16-oct): extraer todo el catálogo y continuar un motor local independiente. Implementación en el checkout gestionado `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec`, bajo `apps/tennis`; preparación temporal en `.local/tennis_engine_build_20261016/` por permisos de escritura.

- [x] Descargar catálogo completo TML y completar los originales MCP: 214/214 archivos, 593.347.344 bytes, hashes verificados, cero fallos.
- [x] Consolidar TML: 492.251 partidos, 249.938 con conteos/formato aptos; originales y conflictos conservados, fechas sin hora inventada.
- [x] Implementar puntuación/distribución de mercados, candidato binomial bayesiano regularizado y evaluación cronológica frente a Elo probabilístico.
- [x] Comprobar matemática (17 pruebas, incluida simulación independiente), ajustar candidatos ATP/WTA y guardar métricas reales de 2025/2026. Sin promoción ni consumo de cuotas. Ver `docs/tenis_primera_version_y_resultados_20261016.md`.
- [x] (cerrada 25-oct: superada por el motor v7 (19-oct), que ya gana a Elo en acierto) Mejorar habilidades/calibración con validación separada y nueva prueba futura: el candidato inicial pierde en log-loss frente a Elo. No convertir el 2026 ya observado en prueba intacta de nuevas variantes.

- [x] Revisar completa la conversación adjunta y documentar modelo bayesiano/Markov y requisitos de datos en `docs/tenis_modelo_y_datos_20261016.md`.
- [x] Auditar la fuente Match Charting Project indicada por el usuario: versión fija, originales y hashes, contraste punto a punto con Overview y observaciones de investigación. Ver `data/tennis/mcp_20261016/AUDIT_README.md`.
- [x] Verificar gmalbert, panaC, Live Tennis API y Apify; localizar TennisMyLife directo y auditar 11.364 filas de muestras de 2026/en curso. Ver `docs/tenis_fuentes_y_repositorios_20261016.md`.
- [x] Descargar y consolidar TennisMyLife completo con cobertura, clasificación de cuadros por archivo, conflicto de claves y exclusiones explícitas.
- [ ] Completar calendario próximo con IDs/hora y cronología real; no confundir resultados en curso con agenda ni semana del torneo con inicio del partido.
- [ ] Resolver permiso comercial de MCP (licencia publicada CC BY-NC-SA 4.0), cobertura reciente completa y agenda/identidades; precisar plan/casas de The Odds API antes de gastar créditos.
- [x] Primera implementación del motor de puntuación y comparación cronológica; modelos entrenados de investigación, sin resultados económicos ni aprobación predictiva para publicar.

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

## Arreglos de la auditoría de datos (2026-10-25) — `docs/auditoria_datos_motores_20261025.md`
Orden del titular (25-oct): arreglar lo que falla, aplicar las recomendaciones y usar FotMob para completar partidos y
datos. Regla desde el 25-oct: el error que aparece al desplegar o probar se arregla en la misma sesión, no se apunta.
- [x] `qf.ingest.propline_cierres`: cierres archivados (`/odds/closing`) a `odds_snapshots` como `close`, fuente
  `propline`. Un único `captured_at` por partido (el de-vig del CLV no mezcla momentos): el último instante en que
  todas las líneas usadas seguían a la vista, a ≤ 10 min del inicio; fuera `is_stale`, periodos y recibos previos al
  saque. Mismas casas y mercados que la captura horaria. Cron cada 3 h tras el recolector.
- [x] Recolector SofaScore: Liga MX pedía el Clausura (`11620`, vacío); el Apertura es `11621`. MLS en eliminatorias
  trae `round: null` y el recolector abandonaba: sin jornada se lista sin jornada (último y próximo).
- [x] (25-oct, worker `ffe42ee`) Desplegado; cierres de 79 partidos cargados, MLS y Liga MX ya en SofaScore.
- [x] (25-oct 17:41 UTC) La captura de PropLine usa la imagen sin etiquetas `com.docker.compose.*`
  (`propline-shared-capture:sin-etiquetas`): un despliegue del worker ya no la toma por réplica.
- [ ] **Enero de 2027:** volver Liga MX a `11620` (Clausura) en `scripts/sofascore_apify_config.json` y en el VPS.
- [x] `matches.stats` (fichas de la web y serie del Motor C) desde SofaScore y, si falta, FotMob, con las claves de
  `estadisticas.TIPOS` más centros; relleno de lo ya cargado. Solo donde está NULL.
- [x] FotMob como complemento: además de xG/córners/tarjetas, `completar` rellena `stats`.
- [x] (25-oct) Tarjetas a cero de FotMob: en Argentina, Brasil y parte de México el bloque de estadísticas trae
  `[0, 0]` aunque la cronología tiene cada tarjeta. `extraer` cuenta la cronología cuando el bloque viene a cero
  (sin cuerpo técnico) y `--reparar-tarjetas` corrigió lo guardado. Ver README «Tarjetas a cero de FotMob».
- [ ] Sin cambios (decisión del titular): `SOFT_BOOKS`, licencia de BetsAPI, fuente de calendario de copas, tope
  mensual de Apify (el ritmo medido el 24–25 oct supera los 15 USD/mes).

## Auditoría de fuentes y backtest (2026-10-24) — `docs/auditoria_motores_20261024.md`
- [x] Auditoría de solo lectura: uso de PropLine por motor, backtest temporal del A (RPS, log-loss, Brier, ECE, Kelly), calibración real de B y C.
- [x] **Titular (24-oct):** API-Football en plan gratuito desde el 22-oct → se sustituye: resultados y calendario con PropLine, xG y estadísticas con SofaScore/Apify (tope 15 USD/mes y 40 partidos/día, solo las 13 ligas con modelo, fútbol antes que tenis/NBA).
  Plan: `qf.ingest.propline_partidos` (lee `/scores` del archivo, sin HTTP; enlaza `external_ids.propline`; cierra con
  marcador y córners del box score; nunca da de alta equipos) tras `RESULTS_PROVIDER=propline` en `results`/`fixtures`;
  `qf.ingest.sofascore_partidos` (lee el archivo Apify montado en el worker; empareja por liga, ±36 h, nombres y MISMO
  marcador; xG con la hora real de recepción; tabla inmutable `sofascore_detalles`); salud que mire resultados y la
  fuente de cuotas activa. Casas nuevas solo a ≤ 48 h y cada 3 h (volumen).
- [x] (cerrada 25-oct: hecho: worker alineado con main desde el 25-oct (ab82dcb y siguientes)) Worker con `estadisticas_mercado.py` y `alta_prob.py` de `main` (alta probabilidad, escalera y parley fallan desde el 24-oct). Con visto bueno.
- [x] (25-oct) Cargar los cierres de PropLine a `odds_snapshots` como `close`: `qf.ingest.propline_cierres`.
- [ ] **Titular:** `SOFT_BOOKS` frente a las casas de PropLine (solo 1xbet coincide).
- [ ] Chequeo diario: detectar plan gratuito y calendario sin altas; `httpx` a WARNING (el token del bot sale en los registros).
- [x] (25-oct) Ligue 2 y Superliga danesa fuera de los motores (db/086; sin cuotas en PropLine). Historial conservado.
- [x] (25-oct) Serie B, LaLiga 2, Allsvenskan y Super League suiza fuera (db/088). Quedan 15 ligas + 2 copas.
  Ver `docs/cobertura_ligas_propline_sofascore_20261025.md`.
- [x] (25-oct) FotMob reactivado como complemento diario en las ligas activas (`referencias`, `previos`,
  `posteriores`, `sedes`) y nuevo `fotmob_captura completar` (09:15 UTC, solo NULL, > 36 h tras el saque).
- [x] (25-oct) Championship, 2. Bundesliga, Turquía y Noruega añadidas al recolector SofaScore.
- [x] (25-oct) Hueco del ~20-sep al 25-oct: no hacía falta SofaScore (~6 USD). La captura FotMob del 18-oct ya lo
  cubría; `posteriores --dias-atras 46` guardó los 39 que faltaban y `completar` rellenó 261. Los 15 sin xG son de
  las últimas 36 h y entran con la carga diaria.
- [x] (25-oct) Respaldo de resultados con FotMob (`fotmob_captura resultados`, cada 3 h a las :55): cierra y liquida lo
  que PropLine deja abierto más de 6 h, solo si terminó en el tiempo reglamentario y con los mismos dos equipos.
- [x] (25-oct) Sustituir lo que aún leía API-Football: once previsto y bajas de SofaScore (#118); clasificación calculada
  con nuestros resultados (`ingest/standings.py`: coincide equipo a equipo con la última foto de API-Football en las 19
  ligas salvo la sanción de Southampton, que va en `SANCIONES`); marcador en vivo desde el listado diario de FotMob (una
  petición por pasada; `/scores` de PropLine gastaría del presupuesto diario que necesitan las cuotas). Calendario y
  resultados van por PropLine (`RESULTS_PROVIDER=propline`); en el cron ya no queda ningún job de API-Football.
- [x] (25-oct) `docker-compose.yml` del repo igual al del servidor (imágenes, montajes y variables; sin secretos).

## Auditoría de los tres motores (2026-10-21) — `docs/auditoria_motores_20261021.md`
Cada paso a producción requiere confirmación del titular. Orden recomendado:
- [x] (22-oct, #70, en producción; modelo 2026.10.22-185314) A1-A4: `dixon_coles.fit` con gradiente analítico (prototipo `dc_rapido.py` de la auditoría), suma cero ponderada por muestra efectiva, ridge en partidos equivalentes (0,5-1), media vida 270; registrar y exigir `res.success`. Reentrenar y pasar la puerta (ΔRPS medido −0,00084 [−0,00137, −0,00031] en 11.920 partidos).
- [x] (22-oct, en producción) A5: retirar el calibrador afín del 1X2 o reajustarlo con la verosimilitud del marcador exacto; la puerta debe medir más/menos y ambos marcan, no solo el 1X2.
- [x] (22-oct, en producción) A8: agenda de la app con `both_teams_known=false` → 1X2 del mercado o sin porcentaje.
- [ ] B2: lista de mercados del partido con calibración empírica por mercado derivado (o solo líneas probadas); investigar cópula + conteos Weibull (Boshnakov 2017). Poisson bivariado probado: peor que DC.
- [x] (22-oct) C2: córners por equipo con el contexto del Motor A (medido sin cuotas: +0,025/+0,017 nats); repetir la prueba de líneas antes de habilitar. C3 (tarjetas): mixto con el A, no se cambia.
- [ ] A7: escalar el xG de cada fuente a goles antes de mezclar. A6: inflación de la diagonal.
- [x] (26-oct) Investigación: modelo dinámico y prior de ascendidos medidos en local (`docs/modelo_dinamico_y_ascendidos_20261026.md`). Prior: sin señal. Dinámico: mezcla DC multi-vida + Kalman −0,0008 de RPS en el año de producción; despliegue pendiente de decisión del titular (estado de Kalman diario + 3 DC).
- [ ] Repetir `apilado_mercado.py`/`estaca.py` sobre totales, córners y tarjetas cuando haya ~2.000 partidos con cierre de Pinnacle (hoy 459 de totales, 127 de córners, 75 de tarjetas): `docs/investigacion_modelos_y_factores_20261026.md`.

## Recuperación de cierres Pinnacle (2026-10-14)

- [x] Carga OddsPapi autorizada (15-oct): 2.918 cierres reconstruidos / 8.754 cuotas y 25 referencias para revisión, los 2.943 con procedencia inmutable. Originales verificados, respaldo completo en servidor, reversión e idempotencia comprobadas; 1.237 pruebas y huecos reducidos de 6.185 a 3.267. Detalle: docs/oddspapi_carga_20261015.md.

- [x] Validar la clave OddsPapi del usuario, descargar calendarios, asociar 6.094 pendientes con nombres revisados y recuperar un primer lote de 51 ternas prepartido. Fuente, marcas horarias y originales conservados; sin carga en producción.
- [x] Terminar y comprobar el lote OddsPapi (15-oct, 03:46 CDMX): 6.094 consultados, 2.943 ternas reconstruidas (23 requieren revisión), 3.151 sin histórico; CSV final y recibos conservados, seguimiento desactivado. Cero cargas automáticas.
- [ ] (Medido 18-oct: en las ligas modeladas faltan 697 de 12.008 partidos desde 2024; quedan por comprar 527 snapshots tras el reset del 1-nov, ~5.270 créditos.) Resolver los 3.267 cierres pendientes tras la carga: 3.151 sin histórico, 87 sin fixture, cuatro cancelados en la fuente y 25 referencias retenidas para revisión. Recorrer la cola no acredita cobertura completa ni cierre oficial.

- [x] Descargar y archivar 60 CSV: 14.381 ternas explícitas desde 2024, todas ya presentes.
- [x] Ensayo Football-data de asociación sin escrituras: 0 candidatos nuevos; siguen los 6.185 huecos en producción.
- [x] OddsHarvester con ZenRows GB/CA/CL y control Champions 2025: 0 ternas Pinnacle en las muestras. Versión actual 0.20.0 aislada.
- [x] PySBR adaptado a OddsTrader y ZenRows residencial: 149 meses de 13 competiciones, 586 ternas anteriores al inicio; 272 candidatas de la lista exacta (147 UCL, 114 UEL, 9 Championship, 2 MX), cierre definitivo todavía sin acreditar. Ver docs/pysbr_zenrows_20261014.md.
- [x] Ejecutar omkarcloud y M3MONs Flashscore con ZenRows; corregir la ruta histórica del segundo en un adaptador. Leen otras casas; cero Pinnacle en las muestras. Archivo original intacto, resultado de búsqueda para las 6.185 filas. Ver docs/flashscore_pinnacle_20261014.md.
- [x] Guardar por petición del usuario las 272 candidatas y las 586 ternas con originales y hashes en `data/pinnacle_recovery/20261014/`; marcadas como cierre sin verificar, sin carga en producción.
- [x] Reintento explícito de OddsHarvester: cuatro sesiones nuevas, dos partidos de la lista, tres payloads de todas las casas verificados, cero Pinnacle nuevo. Resultado por fila y evidencia en `data/pinnacle_recovery/20261014_oddsharvester_retry/`; no son 6.185 consultas individuales.
- [x] Recuperar con la clave OddsPapi autorizada: catálogo y asociación exacta, cola histórica terminada, originales y corte prepartido conservados; resultado y carga documentados arriba.
- [x] (cerrada 25-oct: duplicada de la anterior (cierres de Pinnacle pendientes)) Conseguir fuente/acceso con Pinnacle para los cierres pendientes (cifra vigente: ver la línea anterior), validar muestra y coste antes del lote. Detalle: docs/pinnacle_recuperacion_20261014.md.

## Señales nuevas en el motor principal (2026-10-14)

- [x] Prueba aislada LanusStats/365Scores (15-oct): nueve huecos reales, tres por liga; tres parejas nuevas en LaLiga 2 y cero en las muestras de Serie B/Ligue 2. Control positivo, identidad y hashes comprobados; acceso directo HTTP 200, sin gasto de proxy ni carga en la base. Granada–Albacete requiere revisar una hora de diferencia. Evidencia: data/xg_recovery/20261015_lanusstats/.
- [x] Carga autorizada de las tres parejas 365Scores (15-oct, 16:49 UTC): identidad corroborada con FotMob, respaldo selectivo, ensayo revertido e idempotencia cero. Recepción real y seis originales verificados tras el commit; quedan 1.219 huecos, 233 de LaLiga 2. Detalle: docs/lanusstats_carga_20261015.md.
- [x] (cerrada 25-oct: Serie B, LaLiga 2 y Ligue 2 retiradas (db/086, db/088)) Ampliar la cobertura de 365Scores sobre los 233 huecos restantes de LaLiga 2, validar fechas y procedencia antes de cualquier carga; las muestras negativas de Serie B/Ligue 2 requieren otra comprobación/fuente y no acreditan una ausencia universal.

Pedido del usuario: llevar al motor principal XI y valor de jugadores, bajas, tiros/PSxG,
árbitro, sede y clima, cuotas de apertura/cierre. Spec:
docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md. Regla: una
señal entra solo si mejora RPS, log-loss y ECE fuera de muestra en >=2 ligas.
Decisión del usuario: sello tardío (un sello por partido a T-30/XI) y capa de ajuste
de lambdas. Clima: Open-Meteo plan Standard (sin APIs históricas).

- [x] F0 — Archivo FotMob a `matches` y `estadios` (db/067). Detalle: docs/f0_archivo_a_matches_20261014.md.
- [x] F1 — Capa de ajuste `qf.model.ajuste` (puerta con referencia de nivel y significancia) y línea base: el XI simple pasa la puerta estricta (dRPS -0,0013, 9 de 12 ligas). Sin reentrenar: el del 12-oct ya usó el xG nuevo y el cron repite el 1-nov. Detalle: docs/f1_capa_de_ajuste_20261014.md.
- [~] F2 — Cierres de Pinnacle: faltan 2.103 (697 en las 13 modeladas, antes 6.185/3.526). Football-data no aporta; The Odds API fase 1 hecha (8.000 créditos, +1.164 cierres). Hecho: filtro de los cierres de 60 min de OddsPapi (F2c, desplegado en el worker). Pendiente: ~5.270 créditos para 527 snapshots tras el 1-nov, alias de Champions/Europa y sincronizar `~/quantfut/src` y la API con el repositorio. Bloque `mercado` (movimiento) cuando haya muestra. Detalle: docs/f2_cierres_pinnacle_20261015.md.
- [ ] F3 — Bajas y sanciones como minutos perdidos (bloque `bajas`).
- [ ] F4 — Puente de identidades FotMob/API-Football; XI con valor de jugador (bloque `xi`).
- [ ] F5 — Árbitro: penaltis, expulsiones y tarjetas; unificar identidades (bloque `arbitro`).
- [ ] F6 — Sede, viaje, altitud y clima (bloque `sede_clima`): historial desde Copernicus ERA5 (decisión del usuario), pronóstico en vivo y altitud con Open-Meteo Standard. Requiere antes: cuenta CDS, licencia aceptada y token personal del usuario.
- [x] (cerrada 25-oct: hecho: F7 en producción (qf.publish.sello_tardio en el cron)) F7 — Sello tardío en producción (un lote por partido, `batch_kind`).
- **Orden:** cualquier cambio de probabilidad o selección pasa la puerta de evaluación; el worker no se recrea mientras
  corre el reentrenamiento (1-nov, 03:00-08:00 UTC). Reejecutar `python -m qf.model.ajuste` sobre el nuevo OOS, comprar
  los 527 snapshots de The Odds API (~5.270 créditos) y diseñar **F7** (es lo que deja entrar al XI en el motor y mejora los picks
  con cuotas de última hora; toca la cadena de hashes). Luego F3, F6, F5 y F4. Fecha de control: ~10-nov, CLV en sombra a 300.
- **Ampliación del plan (2026-10-15, documentos de recomendaciones y de revisión del usuario):** spec
  docs/superpowers/specs/2026-10-15-mejoras-tres-motores-plan.md. Ya no espera al 1-nov (25-oct). Orden nuevo:
  F7 (+ bajas FotMob donde API-Football no las da) → F9 con F8 evaluada en paralelo sin tocar picks vendidos → descanso/calendario →
  archivo FotMob a tablas y F3, F6, F5, F4 → activar F8 y F10. F11 puede adelantarse (no toca el motor).
- [ ] F8 — Conectar el modelo propio con los picks: mezcla A/B por familia de mercado sobre la distribución de marcadores (base `meta.py`); debe aportar sobre B **del mismo momento**; la mezcla no evita sola el doble conteo; predicciones honestas, peso cero válido, periodo reservado; C con su propio mercado. Evaluada en paralelo, activada al final.
- [ ] F9 — Evaluación en dos preguntas (probabilidades sin cambiar selección; luego selección a volumen constante). Cuatro versiones: B 03:00 · B al horario de F7 · A+B al horario de F7 · más nueva selección. Puerta reforzada: magnitud con IC, estabilidad por periodo y liga, alternativa sencilla, registro de variantes probadas. Solo para cambios de probabilidad o selección.
- [ ] F10 — Selección y exposición: alternativas de un partido contra la jornada con registro; exposición al mismo partido entre productos (medir/mostrar, no limitar); correlación en parley/escalera; volumen diario en `/control`.
- [ ] F11 — App: etiquetar la fuente de cada cifra (modelo, mercado, pick) e indicador de calidad de datos separado de la probabilidad; 6 idiomas.
- [ ] F12 — Factores sin fase: descanso/partidos acumulados (primero; falta calendario de copas y otras competiciones), ida/vuelta y global, necesidad de puntos, entrenador y estilos (ambos en el archivo FotMob), motor C ampliado (media y dispersión).
- [x] (cerrada 25-oct: hecho: archivo FotMob en tablas (db/075), altitud (db/076), calendario (db/078) y ERA5 (db/082); lo que falta está en F12) Datos (spec §5): llevar a tablas el archivo FotMob 2024→hoy (XI, minutos, bajas, entrenador, ronda, estilos); descargar calendario de copas/continentales/FIFA, altitud de 758 sedes y ERA5 (token del usuario); bajas de Argentina/Liga MX/Portugal desde FotMob previo (API-Football reporta 0) y captura diaria del archivo FotMob (hoy importación puntual). No comprar cuotas históricas a T-60 (≈14.000–31.000 créditos por temporada).
- [ ] Antes de `PUBLISH_PICKS_ENABLED=1`: `picks.select_daily()` solo ve `predictions` (13 ligas) y la sombra mide 22; alinear cobertura.
- [ ] Vigilar la ampliada 73–95 %: en picks con cuota de referencia (n=223) real 78,0 % frente a 81,4 % prometido; ROI a referencia −7,5 % (base −3,0 %, n=91; esperado en una línea de acierto).
- [x] (cerrada 25-oct: Serie B, LaLiga 2 y Ligue 2 retiradas (db/086, db/088); los huecos de Argentina son de ene-abr 2024) Huecos de xG desde 2024 (1.222; Serie B, LaLiga 2, Ligue 2): requieren una fuente nueva, decisión del usuario.
- [x] (cerrada 25-oct: Serie B, LaLiga 2 y Ligue 2 retiradas (db/086, db/088); duplicada de la anterior) Huecos de xG desde 2024 (1.219 tras tres parejas 365Scores; Serie B 588, LaLiga 2 233, Argentina 208, Ligue 2 144 y otros 46): ampliar fuentes; la muestra 365Scores no acredita cobertura completa.

## Buscar datos restantes de las 23 competiciones (2026-10-13)

Pedido del usuario tras eliminar Chile y Brasil B: buscar los datos que faltan.
Saldo nuevo verificado 4.012; sin compras, entrenamiento o reintroducción de
ligas retiradas. Autoriza la recuperación/importación ya acordada en este chat.

- [x] Auditar huecos vigentes y fuente/temporada; arnés previo 1.049/24.
- [x] (cerrada 25-oct: fuentes decididas el 25-oct (PropLine, SofaScore, FotMob); soccerdata/ZenRows ya no se usan) Reutilizar originales y muestrear fuentes históricas con soccerdata y
  ZenRows CLI/MCP; separar métrica no publicada de errores de acceso.
- [x] (cerrada 25-oct: fuentes decididas el 25-oct; soccerdata/ZenRows ya no se usan) Descargar datos faltantes acreditados con presupuesto/concurrencia
  compartidos, revisar identidades y conservar recibos/reloj por observación.
- [x] (cerrada 25-oct: fuentes decididas el 25-oct; soccerdata/ZenRows ya no se usan) Importar lo recuperado sin reemplazar originales/xG congelados; verificar
  reversión, repetición, modelo y servicios; documentar cobertura y pendientes.

## Eliminar Chile y Brasil B (2026-10-13)

Orden del usuario: eliminarlas por completo. Autoriza expresamente el borrado
del historial protegido, después de revisar sus dependencias. Série A permanece.

- [x] Auditar partidos, clubes, cuotas y selecciones protegidas; arnés previo.
- [x] Preparar respaldo selectivo y eliminación transaccional de dependencias,
  incluyendo tickets/retos afectados sin dejar productos incompletos.
- [x] Retirar las dos competiciones de recolectores, catálogo y tareas futuras;
  impedir su reintroducción por archivos históricos y migraciones anteriores.
- [x] Probar reversión y eliminación, restaurar protecciones, cotejar otras
  ligas, modelo/API y evidencia; documentar y registrar solo esta retirada.

Eliminación confirmada: 1.806 partidos, 1.784 originales, 36 clubes, cuotas y
dependencias; dos retos completos y un parley afectados. Cero datos operativos
de ambas, 23 ligas, Série A intacta, 15 lotes originales verificados y modelo
conservado. Guardas de reintroducción, respaldo COPY, 1.049/24 pruebas y API/app
200. Detalle: docs/eliminacion_chile_brasil_b_20261013.md.

## Recuperación adicional con clave nueva ZenRows (2026-10-13)

El usuario proporciona otra clave y solicita aplicar la documentación oficial
para descargar más datos con eficiencia. Clave cifrada localmente con DPAPI,
fuera de Git; la configuración compartida conserva su cuenta anterior.

- [x] Validar autenticación, saldo y concurrencia sin comprar ni cambiar planes.
- [x] Aplicar modo automático, caché de éxitos y selección por huecos; probar
  calendarios bloqueados con país alternativo solo cuando aporte información.
- [x] Medir cobertura histórica con muestras antes de ampliar solicitudes;
  recuperar calendarios actuales sin repetir fallos ni inventar xG ausente.
- [x] Revisar asociaciones, importar nuevos originales y verificar reversión,
  idempotencia y preservación del modelo, ligas y datos históricos anteriores.
- [x] Documentar métricas y consumo comprobados, ejecutar arnés final y
  comitear solo esta ampliación; credencial cifrada y originales fuera de Git.

Carga adicional confirmada: 125 originales, 101 asociaciones, 36 parejas xG
nuevas, 228 XI, 4.137 registros de jugadores y 294 bajas históricas. 24 identidades
europeas pendientes; cero clubes/partidos canónicos nuevos. Saldo nuevo:
988/5.000 utilizados, 4.012 restantes; arnés 1.045/24 y modelo/API conservados.
Detalle: docs/zenrows_clave_nueva_futbol_20261013.md.

## Completar fútbol con soccerdata + ZenRows (2026-10-13)

Cambio del usuario: scraper anterior detenido; usar probberechts/soccerdata
1.9.1, revisión e120471e424a173e83e8aeeaaf4d954ab9d38ee4 (Apache-2.0).
Documentación: https://soccerdata.readthedocs.io/en/latest/.
Arquitectura: lectores reales con transporte MCP ZenRows y originales recibidos;
selección por huecos, caché verificada y normalización por proveedor antes de
reutilizar el importador histórico. No confundir cobertura declarada con datos
efectivamente recuperados; registrar bloqueos y datos inexistentes por separado.

- [x] Auditar huecos actuales y detener el scraper anterior; comprobar licencia,
  versión y límites de los lectores de soccerdata antes de seleccionar fuentes.
- [x] Adaptar su cliente al MCP ZenRows con proxies automáticos, recibos/hash,
  caché, control del saldo existente y reserva de 100 créditos; sin compras.
- [x] Comprobar cobertura real de xG/XI/jugadores/bajas antes de ampliar descargas;
  conservar información ausente y conflictos sin fabricar valores.
- [x] Importar los nuevos originales y datos verificados al VPS, resolver las
  correspondencias seguras y medir qué huecos se cerraron y cuáles persisten.
- [x] Validar idempotencia/recepción temporal, conservar modelo/puertas/publicación,
  registrar evidencia, ejecutar arnés y comitear únicamente esta ampliación.

Carga verificada: 586 originales, 574 asociaciones, 54 parejas xG nuevas,
138 XI de equipo, 2.789 registros de jugadores y 269 bajas históricas.
Diez identidades de copas pendientes y dos conflictos conservados; sin nuevos
partidos/clubes canónicos. 1.033 pruebas, transacción reversible e idempotencia;
modelo/API verificados. Detalle: docs/soccerdata_zenrows_20261013.md.

- [x] (cerrada 25-oct: Serie B, LaLiga 2 y Ligue 2 retiradas (db/086, db/088); el resto de huecos se cubre con SofaScore y FotMob) Completar los 2.073 huecos xG de las 23 ligas restantes cuando una fuente acredite cobertura:
  muestras 2024 sin xG o con error; no convertir ausencia/bloqueo en cero.
- [x] Recuperar calendarios actuales antes bloqueados de Brasil B, Bundesliga 2, Dinamarca,
  Suecia y Europa League; conservar cuota y originales de cada configuración.
- [x] (cerrada 25-oct: fuentes decididas el 25-oct; soccerdata ya no se usa) Extender esos calendarios a toda la historia cuando respondan los originales;
  la recuperación de jornadas actuales no acredita temporadas anteriores.
- [x] (cerrada 25-oct: duplicada de F4 (puente de identidades) y F3 (bajas)) Resolver identidades de copas pendientes y adaptar consumidores históricos
  de XI/jugadores/bajas; los datos almacenados no activan modelos por sí solos.

## Viabilidad de recuperar fútbol con ZenRows (2026-10-13)

Pedido del usuario: comprobar xG, alineaciones, bajas y estadísticas de jugadores
para las 12 ligas sin modelo y huecos de las 13 actuales.

- [x] Auditar el archivo FotMob ya descargado: originales, hashes, xG, XI y
  estadísticas por competición; separar los datos guardados de los importados.
- [x] Probar SofaScore con ZenRows existente: hasta cuatro solicitudes y reserva
  de 100 créditos, sin compras ni descarga masiva; registrar cobertura real.
- [x] Entregar matriz de viabilidad y límites del histórico/recepción temporal.
  No activar captura_completa, ligas o un candidato por disponer de más datos.
- [x] Importación realizada: emparejar/importar el archivo verificado, extender
  el control temporal a FotMob/SofaScore y separar bajas/XI históricos de PIT.
  Detalle: docs/futbol_scraping_viabilidad_20261013.md.

Importación autorizada por el usuario el 13-oct:

- [x] Preparar emparejamiento revisable contra equipos, alias, fechas y marcadores;
  resolver Brasil B/Chile sin duplicar partidos ni dar de alta equipos en copas.
- [x] Añadir almacenamiento histórico con IDs por proveedor, originales/recibos
  y tablas separadas de XI, jugadores y bajas; conservar datos previos.
- [x] Extender la disponibilidad del xG a nuevas fuentes y validar la carga
  idempotente, conflictos y restricciones en PostgreSQL antes de ejecutar.
- [x] Desplegar protección temporal, importar al VPS y comprobar conteos,
  correspondencias, modelo activo, servicios y evidencia; documentar y commit.

Resultado: 22.456 originales, 44.912 XI de equipo, 940.386 registros de jugadores
y 48.571 bajas históricas guardados; 1.554 partidos nuevos y 14.629 parejas xG
incorporadas. 400 originales mantienen asociación pendiente/conflicto. Modelo
activo y puertas sin cambios; 1.007 pruebas, prueba PostgreSQL e idempotencia.
Detalle: docs/importacion_fotmob_20261013.md.

- [x] 379 «identidades» de copas = 379 partidos de 110 equipos; ninguno con ambos equipos probados, no resoluble sin dar de alta clubes externos (prohibido en `eu.*`). Medido el 18-oct, docs/ordenar_identidades_20261018.md.
- [x] Arsenal corregido (33 partidos, `db/073`) y 4 alias de The Odds API (+45 cierres de copa), 18-oct. Quedan 20 conflictos de vinculación: 7 son de Arsenal (el partido ya tiene el equipo correcto, pero el archivo FotMob conserva su estado `conflict` hasta volver a vincularlos) y 13 por revisar uno a uno (marcador o estado, liga o prórroga).
- [x] Datos al motor 18-oct (`docs/datos_al_motor_20261018.md`): tablas FotMob con `match_id`, altitud, calendario de equipos (cron diario), equivalencias de árbitros, puente de jugadores, vista de descanso.
- [x] 18-oct tarde: captura de FotMob autorizada y montada (`db/081`, cron con flock, pronóstico de clima incluido); token de CDS recibido y descarga ERA5 en curso (`db/082`); Open-Meteo descartada por licencia.
- [x] ERA5 terminado (20.193 partidos), `qf.ingest.sedes` con cron horario y ERA5 incremental (arregla el defecto de cache por celda).
- [x] (cerrada 25-oct: token de Copernicus conservado por decisión del titular, ERA5 en cron 06:20; F7 hecho; estadios duplicados pasa a mejoras) Pendiente: regenerar el token de CDS; poner el ERA5 incremental en cron al recrear el worker (necesita la variable); estadios duplicados (182 grupos); minutos con selección nacional; convertir la captura previa en entrada de F7 (alineación y bajas a T-70/T-40).
- [x] (cerrada 25-oct: duplicada de F4) Adaptar consumidores de jugadores/XI/bajas a IDs FotMob y validar sus modelos
  respetando recepción temporal; las tablas nuevas ya están importadas.

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

Inicio autorizado el 2026-10-12: instalar Firebase en Flutter por fases.
Ampliación autorizada el mismo día: instalar y configurar los restantes
servicios del plan (Auth/Google, FCM, Analytics, Crashlytics, Performance,
Remote Config y App Check). Android primero; iOS preparado, sin APNs porque
el usuario todavía no tiene cuenta/clave Apple. El registro primero y el
vínculo seguro con cuentas existentes forman parte de esta integración.

- [x] Instalar plugins P0/P1, configurar Google/huellas, Remote Config y App Check
  en consola; recursos Android/iOS. Compilación Android correcta.
- [x] Integrar sesión Google, consentimiento, enlace de cuenta y restauración;
  desplegar puente en API. Activación Google pendiente de documentos publicados.
- [x] Integrar preferencias FCM, dispositivos, recepción, bandeja y apertura
  segura; cola/emisor preparados. Envío real y campañas todavía pendientes.
- [x] Integrar medición consentida, fallos, trazas, banners y App Check.
- [x] Validar pruebas, compilación y ejecución Android; documentar límites iOS.
  38 pruebas Flutter, 924 del arnés y ocho escenarios PostgreSQL aislados.
  Detalle: `apps/mobile/docs/FIREBASE_SERVICIOS_20261012.md`.
- [x] Redactar borradores de términos y privacidad por autorización del titular:
  Saptain LTD, Seychelles. `docs/legal/`; fuentes oficiales consultadas.
- [x] Recibir datos del titular: Saptain LTD, E Coast Rd, Victoria, Seychelles;
  admin@pronosticosdeportivos.pro (corregido); edad mínima 18; Estados Unidos, Europa y
  Latinoamérica como mercados previstos.
- [ ] Completar datos operativos y revisión legal; publicar documentos y activar
  la primera pantalla de Google. No registrar
  aceptación de borradores como si ya fueran documentos vigentes.

- [x] Fase 1: instalar Firebase CLI/FlutterFire y `firebase_core`, preparar
  arranque condicionado a configuración real y validar análisis/tests/APK.
  Base instalada el 2026-10-12; configuración real generada. Detalle:
  `apps/mobile/docs/FIREBASE_INSTALACION_20261012.md`.
- [x] Elegir proyecto Firebase e identificadores de Android/iOS, autenticar
  la CLI y generar configuración real con FlutterFire. No inventar valores.
  Proyecto indicado por el usuario: `pronosticos-deportivos-85ffa`.
  Identificadores definitivos indicados después de la pausa: nombre QuantFut,
  Android/iOS `com.saptain.quantfut`. Configuración regenerada para esas apps.
- [x] Eliminar de Firebase los dos registros de ejemplo `com.example.gobet`,
  por petición del usuario; solo quedan QuantFut Android e iOS activos.
- [x] Comprobar el arranque de Firebase con la nueva identidad en Android:
  APK instalado, inicialización correcta y navegación real en emulator-5556.
- [ ] Compilar y comprobar el arranque de Firebase en iOS con Mac/Xcode.
- [x] Fase 2 implementada: Google Auth y vínculo seguro con cuentas existentes;
  registro primero, restauración y conservación de permisos/saldo/referidos.
- [x] Fase 3 implementada: FCM, dispositivos, preferencias, bandeja y enlaces
  autorizados. Prueba de entrega y activación de eventos pendientes.
- [x] Fase 4 implementada: consentimiento, Analytics, Crashlytics y rendimiento.
- [ ] Validar Google con usuario real, entrega FCM y fallo controlado en cuenta
  de prueba. Acceso ya activo (2026-10-12); falta que el titular inicie sesión con
  su cuenta Google en un dispositivo (el emulador no tiene cuenta y no se
  introducen credenciales) y pruebe un aviso FCM.

Ampliación del 2026-10-12: el usuario pidió «termina los pendientes» y corrigió
el contacto a admin@pronosticosdeportivos.pro (buzón existente); ubicación del
VPS declarada por el titular: Berlín, Alemania.

- [x] Cerrar textos con datos confirmados y retención efectiva; preparar páginas
  legales públicas y procedimiento de solicitudes, sin inventar certificaciones.
  Hecho 2026-10-12: textos finales de contenido, páginas en `/legal/*` (prueba
  `tests/test_legal.py`), procedimiento en `docs/legal/OPERACION_PRIVACIDAD.md`,
  estado en `docs/legal/REVISION_Y_PUBLICACION.md`. Publicadas en producción el 2026-10-12 por orden del titular.
- [ ] Del titular, para publicar: revisión por profesional habilitado, país
  contractual de Contabo/Proton y sus DPA, atender el buzón de contacto, plazos
  legales por categoría. Activar Google (`FIREBASE_AUTH_ENABLED`) sigue pendiente de su decisión.
- [x] Configurar conservación y limpieza de datos operativos Firebase; respaldo
  privado con rotación acotada, separado de los registros deportivos inmutables.
  Programado en el VPS el 2026-10-12 (03:40 UTC), probado y con alerta Telegram;
  detalle en `docs/legal/OPERACION_PRIVACIDAD.md`.
- [x] Publicar documentos y activar el acceso Google coordinadamente; comprobar
  Android y pruebas reales que no requieran credenciales personales del usuario.
  Hecho 2026-10-12: servidor `FIREBASE_AUTH_ENABLED=1`, Remote Config con
  `qf_google_auth_enabled=true` y URLs legales. Ver `harness/progreso.md`.
- [x] Preparar clave/firma Android de distribución y comprobar APK firmado.
  Verificado el 2026-10-12; ver `apps/mobile/docs/FIRMA_ANDROID.md` (falta respaldo
  externo del almacén y Play App Signing al publicar).
- [x] Instalar y configurar Sentry (errores) en backend, worker y app Flutter, solo con
  diagnóstico consentido en la app y sin datos personales. Proyectos `quantfut-api` y
  `quantfut-app` en `saptain.sentry.io`. Ver `harness/progreso.md` y
  `docs/legal/OPERACION_PRIVACIDAD.md`.
- [ ] Sentry, del titular: confirmar retención del plan tras la prueba Business (~26-oct),
  ajustes de organización (IPs, Data Scrubber, issues compartidos, 2FA) y probar en un
  dispositivo real (activar diagnóstico y provocar un error).
- [ ] Dejar iOS reproducible para Mac/Apple; APNs y firma requieren Apple Developer.

## Traducciones completas de la app (es, en, pt, fr, it, de) — 2026-10-12

Decisión del usuario: traducir toda la app a los 6 idiomas y mantenerlo SIEMPRE al día:
cualquier texto nuevo o modificado en la app se traduce en el mismo cambio (ver memoria
`traducciones-siempre-en-la-app`). Alcance real: los 29 archivos alcanzables desde
`main.dart` (~8.200 líneas, ~450 textos); 60 archivos de la plantilla original y 5 de
`lib/product` (market_screens, match_detail, match_visuals, profile_settings,
vip_performance) son código muerto y no se traducen.

- [x] Fase 1 — Base: `flutter_localizations` + `gen-l10n` (ARB, plantilla `app_es.arb`),
  `LocaleController` persistente (funciona sin Firebase), selector de idioma (bienvenida,
  Perfil, acceso), idioma del dispositivo como sugerencia, español como respaldo y prueba
  que exige las mismas claves/placeholders en los 6 ARB.
- [x] Fase 2 — Migrar todos los textos fijos de los 29 archivos a ARB (con plurales y
  parámetros) y formatear fechas, horas, números y porcentajes según el idioma.
- [x] Fase 3 — Textos que llegan del servidor: el pronóstico (`texto`) se genera en la app
  desde `market`/`selection`/`line`/equipos (misma lógica que `alta_prob.texto`); grupos y
  títulos de mercado, estados y motivos con catálogos propios.
- [x] Fase 4 — Mensajes del backend (errores `detail`, términos de monedas, avisos FCM,
  correos) según el idioma de la cuenta; revisión humana de las traducciones antes de publicar.
  Hecho el 2026-10-12 salvo: revisión por hablantes nativos (pendiente, antes de publicar), textos
  legales públicos y correos de cuenta (requieren revisión jurídica). Ver `apps/mobile/docs/TRADUCCIONES.md`.

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
- [x] Enlaces FCM (`route=match` abre el partido, con prueba en
  `firebase_security_test.dart`) y traducciones del detalle (ARB, 6 idiomas).

- [x] Analizar app, backend y documentación oficial; documentar integración.
- [x] Adaptar las primeras pantallas de mercados a las métricas del proyecto,
  sin promover muestras pequeñas o confundir retrospectivo/publicado.
- [ ] Primera pantalla de registro/acceso con Google mediante Firebase,
  marca QuantFut, beneficios con métricas reales, selector de idioma y aceptación
  de términos/privacidad según captura `codex-clipboard-9da919e1-f27f-400b-8c67-6b5038e0fb25.png`.
  Registro antes de las bienvenidas/contenido para personas sin sesión; restaurar
  sesión existente y vincular permisos/saldo del backend. Implementación
  autorizada el 12-oct e incorporada; activación pendiente de documentos
  legales publicados y conexión del backend de producción.
- [x] Idioma en la primera pantalla de registro, antes de la bienvenida:
  español, inglés, portugués, francés,
  italiano y alemán; persistir preferencia y cambio desde Perfil.
- [x] Localización completa Flutter y contratos backend: textos, errores,
  descripciones de mercados, formatos y preferencia sincronizada app/web.
- [x] Firebase en el idioma elegido: Auth/correos, FCM/bandeja, preferencias
  por instalación y medición; evitar avisos duplicados por idioma.
  Detalle: `apps/mobile/docs/IDIOMAS_APP_BACKEND_FIREBASE_20261011.md`.
- [x] Fase 0: recibir ideas de pantallas, contrastarlas con fútbol/NBA y web,
  proponer mejoras y acordar navegación y alcance de la primera versión.
- [x] (cerrada 25-oct: genérica, sustituida por las tareas concretas de la app) Convertir el diseño acordado en fases con entregables y criterios de
  aceptación: base Firebase, identidad compartida, contenido real, avisos,
  medición/control, cobros y lanzamiento.
- [x] (cerrada 25-oct: genérica, sustituida por las tareas concretas de la app) Implementar las fases según sus dependencias y validar cada entrega.

Estado actual: integración real autorizada y desplegada. Firebase Core instalado
y configurado; identidad Firebase, traducciones, notificaciones y cobros siguen
pendientes; las secciones sin integración muestran
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
10. [x] Patas de cuota 1,20 a 1,80 (2026-10-13, pedido del usuario): la cuota TOTAL sigue en los 5
    escalones de 1,90-5,00; cada pata debe cotizar entre 1,20 y 1,80 (`parley.CUOTA_MIN_PATA/MAX_PATA`).
    Rige desde el primer sellado tras desplegar el worker.
11. [ ] **Esperar a tener más casos** antes de ponderar la elección del parley por el acierto REAL por
    mercado (hoy solo elige por probabilidad calculada; el acierto real solo pausa escalones). Muestra
    del 2026-10-13 en Alta probabilidad: 5 a 41 liquidados por mercado (hándicap 41, goles 29, doble
    oportunidad 25, córners 15, goles local 14, córners local 12, goles visita 10, 1X2 6, córners visita
    5): con esos n, 73 % frente a 100 % puede ser azar y se favorecerían mercados por suerte. Revisar
    cuando haya ~50 liquidados POR mercado (`historial.por_mercado` de `/alta-probabilidad` y el
    resumen del parley); entonces medir calibración real/prometida por mercado antes de ponderar.

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
8. [x] Cancelado: Chile y Série B fueron eliminadas por orden del titular el
   13-oct-2026. La ampliación de modelo pendiente queda en diez ligas; los
   diagnósticos anteriores de esta sección corresponden al alcance del 11-oct.

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
- [x] (cerrada 25-oct: fecha pasada; la escalera funciona y se liquida) Revisar el primer sellado con escalera (09-oct, 08:00 UTC): reto creado,
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
- [x] (cerrada 25-oct: hecho: tarjetas desplegadas en el worker (DEPLOYS 22-oct)) Desplegar (api + worker), con autorización del usuario.
- [x] (cerrada 25-oct: decisión registrada (no meter tarjetas en alta probabilidad), sin acción) Tarjetas en alta probabilidad: NO por ahora (alta va 71,9 % real frente
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
- [x] (cerrada 25-oct: hecho: procesador elegido (Whop, código en main)) Elegir procesador de pago (decisión del usuario) → checkout + webhook
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
- [x] NBA: cuotas de bet365 (BetsAPI) normalizadas y unidas a game_id con protocolo v1.1 congelado; docs/nba_cuotas_betsapi_normalizadas_20261024.md.
- [x] NBA: normalizado ampliado (tiros, pérdidas, rebotes ofensivos, posesiones, play-in/playoffs) con protocolo congelado; docs/nba_normalizado_ampliado_20261024.md.
- [x] NBA: modelo de props anclado en el mercado con protocolo congelado (nba.props_residual); docs/nba_props_residual_20261024.md.
- [x] NBA: entrenamiento y calibración de todos los mercados con protocolos congelados (nba.team_markets, nba.engine_calibration); docs/nba_calibracion_motor_20261024.md.
- [x] NBA: productor vivo 1.3.2 con las sumas de puntos, rebotes y asistencias, chequeo previo con protocolo congelado y runbook de despliegue (no desplegado); docs/nba_productor_combinaciones_20261024.md.
- [x] NBA: hash del módulo vivo independiente de los saltos de línea y comando `compare` para validar el modelo antes de desplegar; docs/nba_productor_combinaciones_20261024.md.
- [x] NBA: productor vivo 1.4.0 validado pieza por pieza con protocolo congelado (nba_live14_protocol.json); docs/nba_productor_14_20261025.md.
- [x] NBA: datos del vivo = RUN071 + columnas nuevas (pérdidas, tiros, rebote ofensivo, posesiones) y mercado de pérdidas, validados con nba_live14b_protocol.json; docs/nba_productor_14b_20261025.md.

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
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F0 / G0:** alcance, decisiones y protocolo preregistrado. Presupuesto,
      operadores/proveedor y canal de pruebas pendientes de definición.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F1 / G1:** aplicación `apps/nba/`, dependencias/despliegue, Postgres/
      Redis, configuración y recuperación propios. Aplicación/entorno/config
      locales implementados; Postgres/Redis y recuperación aún pendientes.
      Arnés resuelto y verificado; no importar `qf`.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F2 / G2:** cobertura E0, identidad, contratos/reglas, gasto y familia
      prepartido inicial elegida por datos. Puede avanzar con F1 después de F0.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F3 / G3:** ingesta versionada, raw, cuarentena, reconciliación y PIT.
      E18 continúa en todas las fases; referencias/hash y anclaje de evidencia.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F4 / G4:** baselines y distribución de minutos E1, priors encogidos,
      roles/carga y coherencia deportiva; no usar minutos reales como feature.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F5 / G5:** tasa/distribución de estadística, E8 básico, E21 cuando
      proceda y E22/E23 básicos. Candidato y criterios congelados antes del test.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F6 / G6:** Telegram de pruebas, sellado/outbox, caducidad, revalidación,
      disponibilidad E5/E17 y resiliencia E19. Resolución y demoras explícitas.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F7 / G7:** confirmación prospectiva E26 y revisión de promoción propia.
      300 partidos/60 días/3 bloques son piso propuesto, no prueba suficiente
      de ROI. Separar métricas deportivas, simulación y datos informados.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F8 / G8:** challengers de lesiones/rol/oportunidades E2/E3/E7/E8/
      E9/E13. Núcleo F6 y datos suficientes; cada candidato nuevo vuelve a F7.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) **F9 / G9:** operación evaluada, capacidad/utilidad del producto y
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
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Verificar correspondencias ESPN/NBA y disponibilidad actual; incorporar
      rol/rotación, calibración/abstención y coherencia conjunta de minutos al
      arranque. Rookies y ausencia de datos no se convierten en ceros.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Validar lesiones históricas contra PDFs, IDs y corte temporal; muestras
      de props siguen sin contratos/PIT suficientes para ROI o CLV.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Recuperar registros en cuarentena contrastando otra fuente; unir IDs
      ESPN→NBA con evidencia y cubrir 2023-24 individual incompleto.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Captura gratuita actual con rosters, calendario y disponibilidad PIT;
      contratos/cuotas y destino NBA privado de pruebas siguen pendientes.

## Histórico FotMob (2026-10-03, alcance del usuario)

- [x] (cerrada 25-oct: hecho: archivo FotMob 2024-oct 2026 importado (db/075, 20.331 partidos)) Descargar a archivos locales el histórico del 1-ene-2024 al 3-oct-2026
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
- [x] (cerrada 25-oct: resuelto por compromiso-revelación de la cadena; su despliegue está en «Comprometer-revelar de la cadena») **ALTA antes de publicar la cadena — el lote lleva también los PICKS,
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
- [x] **Fuente de xG reciente — API-Football conectada el 12-oct-2026**
      por decisión explícita del usuario. Primera pareja válida congelada,
      timestamp real y protección temporal en entrenamiento; reconsulta diaria
      acotada de partidos sin dato. Cobertura sostenida pendiente; entrenamiento
      `2026.10.12-221104` terminado el 12-oct a las 20:55 CDMX, candidato
      rechazado frente a Elo (RPS 0,19873 > 0,19657 en 1.051 partidos comunes).
      El modelo anterior sigue activo. Ver docs/xg_api_football_20261012.md y
      docs/entrenamiento_xg_20261012.md.
      **Antecedente, medido el 3-oct: el xG APORTA** (regla
      fijada antes: IC95 entero bajo cero y ≥ mitad de ligas). Ventana
      jul-2023→ene-2025: RPS 0,20154 con xG frente a 0,20440 solo goles,
      delta −0,00287 [−0,00376, −0,00200], 12 de 13 ligas. Es del orden de
      lo que Dixon-Coles saca a Elo y ~40% del hueco con Pinnacle. Hoy
      (xG viejo) aún aporta −0,00055 [−0,00100, −0,00018] y se irá
      apagando con la media vida de 180 días. La elección quedó resuelta el 12-oct.
      FotMob usa xG de Opta, como FBref: medir antes la coherencia con el xG
      guardado en el solape 2024-25 (correlación y sesgo por liga).
      **3-oct: medido el xG de API-Football** (progreso): mismos valores que
      FBref (corr. 0,96-1,00) pero llega con días/semanas de retraso e
      irregular en Argentina/Liga MX. Usarlo exige revertir la regla del
      README y CLAUDE.md: decisión tomada y documentos actualizados el 12-oct.

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
- [x] (cerrada 25-oct: hecho: alta probabilidad activa y liquidándose) Tras el sellado del 7-oct (08:00 UTC): verify y recibo con `n_alta_prob: 0`;
      luego activar `ALTA_PROB_ENABLED=1` con visto bueno del usuario.
- [x] Más goles (2026-10-06): `af_odds` guarda las líneas de goles de la misma
      petición (db/041) y la línea las lee de la misma respuesta. Desplegado
      19:58 UTC; vista previa 9 de 15 partidos (7 de goles, antes 0).
- [x] (cerrada 25-oct: af_odds (API-Football) retirado el 25-oct) Vigilar a las 24 h: filas/día de `af_odds_snapshots` y duración de la
      pasada (hoy 15 s, ~40 filas por partido). Chequeo de frescura de
      `af_odds` en `health.py` (hoy un fallo de escritura solo queda en el log).
- [x] (cerrada 25-oct: cubierto por compromiso-revelación de la cadena) Antes de configurar `CHAIN_GIT_REMOTE`: el lote lleva `prob` exacta y el
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
- [x] (cerrada 25-oct: hecho: cuentas en /app/v1 y cobro con Whop) Fase comercial posterior: cuentas, sesiones, suscripciones y cobros
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
- [x] (cerrada 25-oct: hecho: webhook de Whop (api/whop.py)) **API — cobros.** Webhook del procesador de pago → `UPDATE subscribers`.
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
- [x] (cerrada 25-oct: duplicada de F3 (bajas como minutos perdidos)) **Feature de disponibilidad a partir de bajas.** `injuries.py` solo
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
- [x] (cerrada 25-oct: sustituida por «Impacto por jugador» (ajuste_xi, 19-oct)) **Fuerza por jugador (diseño aprobado 2026-09-29,
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
      - [x] (cerrada 25-oct: descartada (tachada)) ~~Fase B2, sombra en vivo~~ DESCARTADA mientras el reentreno
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
- [x] (cerrada 25-oct: medido el 25-oct: SofaScore da el XI confirmado 29-65 min antes) **El XI llega tarde: medir antes de comprar otra fuente (2026-10-01).**
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
- [x] (cerrada 25-oct: duplicada de «Impacto por jugador» (medir ajuste_xi tras ~150 partidos)) **Validar el ajuste de XI con datos nuevos.** El challenger que estima
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
- [x] (cerrada 25-oct: cubierta por F8/F9) **Fase 2 — superar el mercado sharp actual.** Elo ya está implementado
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
- [x] (cerrada 25-oct: hecho: web en producción) **Frontend de la web (Fase 3, posterior).** El prototipo visual vive en
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
      - [x] (cerrada 25-oct: hecho: cuentas, suscripciones y cobro en el mismo FastAPI) Integración comercial posterior: suscriptores, pagos y
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
- [x] (cerrada 25-oct: alcance cerrado el 25-oct: 15 ligas + 2 copas) **¿Bélgica, Rusia, Ucrania, Turquía, Grecia?** Sumarían ~1.160 cruces
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

- [x] (cerrada 25-oct: duplicada de F7 (hecho)) **XI a T-60** (ya construido, sin muestra). Ya no lo bloquea el plan
      (Pro desde 2026-09-22; `lineups` corre cada 5 min en el servidor). Lo
      bloquean la muestra y, como a 2.B, la falta de modelo activo. Es el de
      mejor relación valor/esfuerzo del proyecto.
- [x] **Bajas/lesiones.** Superado por algo mejor que un LLM leyendo prensa:
      `/injuries` de API-Football ya da el dato estructurado (jugador, tipo de
      baja, motivo) con el mismo proveedor ya contratado. Ingesta en
      `src/qf/ingest/injuries.py`, sellada con `captured_at`. Falta la
      feature de disponibilidad que entra en 2.B (ver Pendientes 🔴 arriba).
- [x] (cerrada 25-oct: duplicada de «Fase 5 — movimiento de línea») **Movimiento de línea (fase 5).** Predecir la dirección del movimiento
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
- [x] (cerrada 25-oct: hecho: criterio sharp en producción (shadow_sharp)) **PLAN (2026-09-23) — sustituir el criterio de selección por "casa blanda
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
- [x] (cerrada 25-oct: probado sin valor y archivado (harness/archivo)) **PLAN (2026-09-25) — Más mercados en el criterio sharp: goles y
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
- [x] (cerrada 25-oct: superada: la sombra mide todas las casas desde el 28-sep) **Idea aparcada (2026-09-27, el usuario prefirió no hacerlo): medir más
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
- [x] (cerrada 25-oct: hecho: ligas añadidas (db/023, db/033) y alcance cerrado el 25-oct) **PLAN (2026-09-25) — Más ligas en 1X2 para tener picks a diario.**
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
- [x] (cerrada 25-oct: hecho: desplegado y con muestra) **Desplegar y esperar la muestra.** Nada de lo anterior produce datos
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
      - [x] (cerrada 25-oct: resuelto: resultados al día (PropLine + respaldo FotMob)) **Resultados de la temporada en curso sin cargar (revisado
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
- [x] (cerrada 25-oct: descartada (tachada)) ~~Calibrar `UNCERTAINTY_Z` contra ROI~~
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
- [x] (cerrada 25-oct: descartada (tachada)) ~~**Cerrar los 163 alias que siguen sin emparejar.**~~ Tras el bootstrap con
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

- [x] (cerrada 25-oct: cubierta por F9) **Fase 2–4 — evaluación y challengers point-in-time (orden solicitado
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
- [x] (cerrada 25-oct: los canales de picks de Telegram están vacíos a propósito) Configuración activa del bot/chat de fútbol disponible en el entorno/ruta autorizados; ejecutar prueba técnica real y medir entrega.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Disponibilidad por partido y rol/minutos validados; diez identidades no resueltas y rookies sin historial conservan abstención.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Fuente de props, contratos y frescura utilizables; supervivencia de precio, límites compartidos del bot y confirmación prospectiva antes de promover/publicar.

### Scrapers y datos adicionales NBA — 2026-10-05
- [x] Inventariar repos públicos, fijar commits y revisar código/datos reales sin ejecutar proyectos de terceros: diez repos y 52 archivos verificados.
- [x] Auditar horarios históricos y muestras de reportes de lesiones: calendarios sin horas; PDF actual 403. No se acredita PIT histórico.
- [x] Integrar observaciones con namespace/captura explícitos y auditoría: alineaciones previstas RotoWire y piloto de quintetos PBP Stats; ninguna promoción médica o comercial.
- [x] Ejecutar pruebas relevantes, conservar evidencia y actualizar registro de fases: 100 NBA y 606 fútbol pasan.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Ampliar quintetos en lotes auditados y obtener sustituciones cronológicas del PBP; validar reloj/IDs de alineaciones y publicación médica por partido antes de usar contexto en pronósticos.

### NBA — The Odds API existente, revisión 2026-10-05

- [x] Comprobar con la clave existente deportes NBA/pretemporada, eventos y muestra real de cuotas; cuatro créditos usados, sin guardar clave o activar polling.
- [x] Documentar mercados, latencia efectiva, acceso histórico todavía no probado y presupuesto compartido con fútbol.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Implementar cliente NBA persistente con reserva coordinada de créditos y evaluación específica de props alternativos; verificar reglas, reloj e identidades antes de promover contratos.
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
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Completar huecos estadísticos con consultas por temporada y competición, sin importar el proyecto externo o sus precios supuestos.
- [x] Auditar ahorro/cobertura: 320 partidos regulares pendientes en cinco temporadas; prueba oficial gratuita terminó en ReadTimeout, cero filas o créditos nuevos.
- [x] Documentar uso de fuentes gratuitas y presupuesto separado para precios reales; sin activar descarga masiva de cuotas.

### NBA — recuperación gratuita de históricos, autorizada 2026-10-05

- [x] Crear lista exacta de pendientes por ID/temporada y diagnóstico reproducible: 395 partidos conocidos pendientes, incluidos 320 regulares; 299 regulares contienen minutos inválidos en la fuente.
- [x] Implementar captura NBA acotada y reanudable de boxscores/rotaciones; guardar originales, hashes y errores, detener lote ante acceso fallido.
- [x] Probar boxscores y GameRotation en muestra real: API oficial ReadTimeout y CDN 403; cero partidos o stints importados. Validadores conservan las restricciones existentes.
- [x] Probar lesiones históricas: tres PDF oficiales, ocho páginas verificadas, 84 observaciones de 30 jugadores; usar hora de cabecera, no nombre del archivo. Identidades y disponibilidad original siguen sin acreditar.
- [x] Validar con 136 pruebas NBA y 609 de harness; congelar 37 archivos propios y registrar NBA-RUN-024–026, 100 evidencias verificadas y 60 eventos de ledger; puertas pendientes.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Recuperar físicamente los 395 pendientes con una fuente accesible y validar cada partido antes de importar; certificar calendarios de playoffs anteriores.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Obtener rotaciones reales y conciliar tiempos, quintetos y minutos; los validadores probados con fixtures no acreditan cobertura real.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Resolver IDs y horarios oficiales de las lesiones; ampliar archivo histórico y capturar disponibilidad prospectiva antes de habilitar señales médicas en picks.

### NBA — contraste de alternativas propuesto por el usuario, 2026-10-05

- [x] Fijar siete repositorios y comprobar interfaz, fuentes, actualización real y límites; no ejecutar proyectos externos.
- [x] Descargar archivo de transacciones JaseZiv y release ESPN 2025–26, comprobar hashes y cobertura. Mantener separados del dataset principal.
- [x] Probar fuente independiente Basketball Reference y conciliar un partido pendiente: 20 participantes, 240 minutos por equipo y estadísticas concordantes, sin errores del validador.
- [x] Documentar candidatos ESPN para 88 pendientes recientes, ausencia de pretemporada y límites de precisión/IDs/PIT; sin cuotas de apuestas o créditos The Odds API.
- [x] Formalizar adaptador Basketball Reference y cruce de IDs con caché/validación: ampliación de 159 partidos y 3,317 filas a versión nueva, linaje conservado; recuperación completa sigue pendiente.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Recuperar pretemporada por separado; no equiparar tipo de temporada ESPN a prefijos NBA sin contraste del calendario.

### NBA — ampliación Basketball Reference autorizada 2026-10-05

- [x] Formalizar parser diario y cruce por fecha/localía/equipos/identidad: nombres exactos con acentos y variantes únicas de sufijos/puntos; sin apodos, generaciones contradictorias o candidatos múltiples. No reparar minutos o inferir DNP.
- [x] Capturar con caché, lotes de hasta 20 y seis segundos entre solicitudes: 140 páginas válidas, parada y respuesta conservada ante 403 del 2024-03-11; fechas posteriores no solicitadas.
- [x] Probar identidad/estadística/reloj/caché/integridad: 172 NBA y 609 harness aprobadas. Nueva versión con 159 partidos/3,317 filas; código propio congelado en 39 archivos.
- [x] Verificar todos los nuevos valores contra páginas raw y volver a conciliar los 159 partidos; 597 identidades consistentes, 154,058 filas previas conservadas; dataset ampliado 157,375 filas, modelo/fútbol/puertas preservados.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Corroborar los nueve casos recibidos separados (siete diferencias de REB/AST, una referencia parcial y un estado desconocido) sin forzar aceptación.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Recuperar los 152 regulares sin página válida tras el 403 y pendientes de otras competiciones: total restante 161 regulares, 71 pretemporada, tres playoffs y un play-in.

### NBA — Black Falcon / Apify, autorizado 2026-10-05

- [x] Preparar piloto de diez pendientes con IDs ESPN candidatos y referencias NBA; seis regulares, dos playoffs, un play-in y uno de pretemporada.
- [x] Ejecutar desde la sesión Apify existente: 282 filas descargadas, US$0.142 mostrado, máximo US$0.25; entrada/log/recibo/screenshot/JSON íntegro y hashes conservados, cero créditos The Odds API.
- [x] Validar identidad, estadística, DNP y precisión temporal: 247 candidatos NBA, cero diferencias P/R/A entre participantes; 53 diferencias null/cero DNP preservadas. Enteros de minutos no importados, pretemporada sin localía/IDs corroborados; dataset aceptado preservado.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Recuperar segundos de minutos y referencias faltantes mediante fuente adecuada: Black Falcon repite los nueve partidos del ESPN previo; no ampliar ese flujo para solucionar precisión que no ofrece.

### NBA — servicios auxiliares para completar datos, autorizado 2026-10-05

- [x] Verificar cobertura real y precisión de servicios Apify; promedios de temporada/minutos enteros descartados; Flashscore decimal condicionado a concordancia individual y calendario NBA contrastado.
- [x] Ejecutar tres capturas Flashscore y dos de calendario NBA con límites: 6,631 registros Flashscore y 100 de calendario; US$2.064 mostrado, cero créditos Odds API; originales/entradas/logs/recibos conservados.
- [x] Ampliar fuentes útiles y conciliar íntegramente: 67 partidos/1,713 filas agregados, 157,375 filas previas conservadas; 6,052/6,150 regulares, 98 regulares y 71 pretemporada aún pendientes.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Resolver identidades y discrepancias de los 169 boxscores restantes; 62 candidatos de pretemporada y calendario de sus 71 IDs ya capturados. No repetir descarga masiva para corregir problemas de conciliación.

### NBA — continuación de pendientes autorizada 2026-10-05

- [x] Auditar los169 candidatos:166 resúmenes ESPN;16 partidos/515 filas adicionales (3regular,13pretemporada),159603 filas finales. Mantener separados95regular y58pretemporada pendientes; no forzar IDs ni discrepancias.
- [x] Ampliar reportes médicos:486PDFs/36300 registros nominales; timestamp de cabecera y recibo actual;43675 filas enlazadas a partido,36063 a jugador. Segundo motor verifica todos; HTTP403 conservado y descarga detenida.
- [x] Recuperar rotaciones cronológicas:5161partidos/217334tramos; cinco jugadores, períodos/prórrogas, continuidad y minutos con cuantización por intervalo continuo del jugador;891partidos separados.
- [x] Ampliar props históricos acotados:20partidos/40snapshots de rebotes/2961pares válidos,420créditos de límite500; originales/temporalidad/cortes preservados, sin picks ni ROI.
- [x] Verificar datasets y preservación:19controles,6replaysPBP,40replayscuotas,486PDFs con segundo motor;609pruebas antes/después,39archivos NBA congelados y152evidencias previas verificados; NBA-RUN-033.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Completar95regular/58pretemporada,330fechas médicas/cortes intradía y13nombres sin ID,891rotaciones separadas; ampliar puntos/asistencias/temporadas de props tras definir próximo presupuesto y reglas de liquidación. Informe:docs/nba_pendientes_recuperacion_20261005.md.

### NBA — fuentes Apify adicionales, autorizado 2026-10-06

- [x] Verificar cobertura y saldo; seis capturas de dos actores, US$2.341 del crédito gratuito. PBP sin acreditación de quintetos; cuotas sin timestamp original. Sin suscripciones/recargas ni créditos Odds API.
- [x] Conservar JSON completos, entradas, recibos, IDs y hashes; agregar Clippers–Nuggets 0012500052, 40 filas/30 participantes y diez DNP explícitos. Segundos exactos por equipo y PRA corroborados; 13 etiquetas de equipo contradictorias conservadas sin uso.
- [x] Sellar NBA-RUN-034: 159643 filas, 95 regulares/57 pretemporada pendientes; 71 calendarios/68 cruces exactos, 385 precios sin tiempo y 19 lesiones no históricas excluidos. 181 evidencias verificadas, 39 archivos NBA intactos, 609 pruebas antes/después. Informe: docs/nba_apify_fuentes_adicionales_20261006.md.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Ampliar boxscores después de definir saldo/límite: diez partidos de 30 filas cuestan aproximadamente US$5 al precio observado, tope propuesto US$6; saldo disponible aproximado US$0.45. Resolver identidades y conflictos antes de importar. Props con timestamps, lesiones archivadas y rotaciones siguen requiriendo fuentes adecuadas.

### NBA — recuperación API-NBA autorizada 2026-10-06

- [x] Configurar la clave local excluida de Git; comprobar autenticación, plan y cuota sin conservar datos personales o secretos en evidencias. Plan NBA real Free; estado final declara70/100usadas.
- [x] Descubrir temporadas y calendario del proveedor; cruzar sus IDs con los 95 regulares y 57 de pretemporada pendientes. 72cruces únicos;80pendientes2025-26rechazados por plan. Sin contratación o exceso del límite local95.
- [x] Recuperar candidatos mediante consultas acotadas/reanudables; conservar originales, fechas y hashes.72boxscores/1543filas con minutos enteros;0partidos nuevos aceptados.159643filas previas preservadas. No inventar segundos ni resolver discrepancias por votación de fuentes.
- [x] Verificar el lote, documentar recuperación y bloqueos reales, ejecutar harness posterior y registrar evidencia NBA aislada sin modificar el modelo, fútbol, puertas o publicación.693pruebas antes/después;10controles;194evidencias,81eventos deledger; NBA-RUN-035.
- [x] (cerrada 25-oct: superada por el motor NBA v1.3-1.5 (21-25 oct); lo vigente está en docs/nba_auditoria_datos_entrenamiento_20261024.md) Obtener segundos individuales verificables y resolver discrepancias estadísticas/IDs para los72candidatos; acceso2025bloqueado para23regulares/57pretemporadas. Ampliar un plan no garantiza precisión ni recuperación; informe docs/nba_api_nba_recuperacion_20261006.md.

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
- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) Pendientes actualizados en NBA-RUN-039: una excepción de boxscore regular, 37 rotaciones del censo y props históricos; pretemporada y censo médico diario completados. Véase docs/nba_completar_validar_20261006.md.


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

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) Pendientes verificados de NBA-RUN-039: excepción MM:SS subsegundo 0022400942; 37 rotaciones; intradía médico/PIT original; props multitemporada y reglas de liquidación. Véase docs/nba_completar_validar_20261006.md.

### NBA — segundos oficiales y rotaciones pendientes, autorizado 2026-10-06

- [x] Añadir al normalizador soporte optativo de segundos subsegundo acreditados por intervalos oficiales completos; conservar MM:SS original y rechazar DNP, fuentes alteradas, IDs contradictorios y gaps.
- [x] Reimportar el roster completo de Tony Bradley en una nueva versión; preservar las 164190 filas anteriores y los originales sellados.
- [x] Diagnosticar las 37 rotaciones mediante PBP CDN/V2 e intervalos locales; recuperar únicamente casos corroborados y conservar conflictos por evento.
- [x] Buscar fuentes alternativas acotadas para las capturas aún ausentes dentro de los límites vigentes, sin compras ni llamadas a props.
- [x] Ejecutar pruebas NBA, arnés posterior y verificación de las 2105 evidencias anteriores; registrar nueva corrida, informe y pendientes reales.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) Pendientes de NBA-RUN-040: nueve rotaciones con eventos/titulares sin corroborar; intradía médico/PIT original; props multitemporada y reglas de liquidación antes del backtest. Véase docs/nba_segundos_y_rotaciones_20261006.md.

### NBA — continuar pendientes de RUN-040, autorizado 2026-10-06

- [x] Obtener pruebas oficiales de titulares de prórroga y auditar eventos sin tiempo positivo de nueve rotaciones, sin inventar alineaciones ni modificar evidencias selladas.
- [x] Descubrir índices médicos intradía, capturar reportes anteriores al inicio y comparar encabezados, entidades y cambios de estado; conservar recepción actual y límites PIT.
- [x] Revisar históricos de props públicos fijando commits y contratos de datos; conservar límite local500 agotado y preparar una ampliación concreta si las fuentes gratuitas no contienen precios/cortes históricos.
- [x] Verificar preservación, controles, pruebas y arnés posterior; registrar nueva corrida y pendientes con cobertura real.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) Estado histórico de NBA-RUN-041 (sustituido por RUN-042): tres rotaciones; corte médico24-oct-2023, intradía completo/recepción original; autorización720créditos para piloto de props y reglas históricas. Véase docs/nba_pendientes_intradia_20261006.md.


### NBA — continuar pendientes de RUN-041, autorizado 2026-10-06

- [x] Fijar y recuperar el archivo público de props con timestamps, verificar blobs y cruzar eventos/identidades/cronología sin gastar nuevos créditos OddsAPI.
- [x] Revisar las rutas oficiales de actas de las tres rotaciones con transporte acotado y conservar conflictos sin inventar intervalos.
- [x] Inventariar cortes del primer día2023-24 y versiones intradía de fechas de muestra; distinguir ausencia de publicación/acceso de un bloqueo deIP y conservar límites de recepción histórica.
- [x] Verificar evidencias4939,41corridas y89eventos previos, presupuestos/pruebas/arnés posterior; sellar nuevas versiones y pendientes reales.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) Pendientes de NBA-RUN-042: props de rebotes/asistencias e historia/cortes faltantes; intradía de otras fechas, recepción original y reglas de liquidación. Rotaciones regulares6150/6150. Véase docs/nba_props_y_rotaciones_20261007.md.

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
- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) Fase posterior propuesta: alimentar el nuevo tablero con la agenda real,
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

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-043: 21 juegos sin selección médica T−60 concordante; versiones intradía adicionales, props/cortes faltantes, relojes de 27.151 candidatos, recepción histórica y liquidación. Informe: docs/nba_recuperacion_medica_y_props_20261007.md.

### NBA — continuar pendientes de RUN-043, autorizado 2026-10-07

- [x] Diagnosticar los 21 contextos médicos pendientes con relojes literales y fuentes independientes; conservar toda discrepancia sin corregir horarios por suposición.
- [x] Recuperar pruebas oficiales adicionales con llamadas acotadas y reservas dentro del techo ZenRows ya autorizado de 3.200; cero llamadas OddsAPI nuevas.
- [x] Validar selecciones retrospectivas nuevas y controles adversariales, preservando versiones selladas, recepción histórica y gates.
- [x] Verificar evidencias, cadena y arnés real antes/después; sellar NBA-RUN-044 y documentar pendientes reales.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-044: contexto médico BOS@NYK ausente en diez PDFs; versiones intradía, props/cortes, relojes de candidatos, recepción original y liquidación. Informe: docs/nba_horarios_medicos_corroborados_20261007.md.

### NBA — props, recepción y liquidación tras RUN-044, autorizado 2026-10-07

- [x] Recuperar archivos públicos adicionales de props con commits y blobs verificados; adoptar solo identidad/evento/precios/relojes acreditados y conservar candidatos separados.
- [x] Auditar recibos históricos, distinguir snapshot del proveedor de recepción original y registrar pruebas o faltantes sin retrofechar capturas.
- [x] Recuperar reglas primarias versionadas por casa/jurisdicción; documentar participación, prórroga, push, abandono, correcciones y vigencia, conservando aplicabilidad desconocida.
- [x] Verificar los datos y evidencias previos, controles y arnés posterior; sellar NBA-RUN-045 y el informe con presupuestos actuales sin compras.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-045: rebotes/asistencias y cortes faltantes; cuotas de casas LATAM, otros países/casas, recepción original/vigencia por ticket, relojes de candidatos y pendientes médicos. Informe: docs/nba_props_y_reglas_latam_20261007.md.

### NBA — aplicación de reglas y recepción tras RUN-045, autorizado 2026-10-07

- [x] Preservar y verificar las 45 corridas, 19.165 evidencias y 94 eventos anteriores; inventariar archivos de tickets/recibos en el alcance local.
- [x] Recuperar reglas oficiales adicionales de México y pruebas archivadas de versiones anteriores, con solicitudes acotadas y cero créditos pagados nuevos.
- [x] Preparar evaluación reproducible por ticket/mercado/periodo con estados desconocidos explícitos; probar participación, prórroga, push, integridad y jurisdicción sin atribuir contratos históricos inexistentes.
- [x] Validar datasets/gates y arnés posterior; sellar NBA-RUN-046 y documentar las entradas que todavía falten.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-046: aplicar únicamente con tickets/contratos reales; recepción histórica original ausente según usuario; cuotas LATAM, otras casas/países, rebotes/asistencias/cortes y pendientes médicos. Informe: docs/nba_reglas_archivadas_y_liquidacion_20261007.md.

- [x] NBA — corregir en una versión documental nueva el total final de pruebas RUN-046 usando el log y verificación sellados; conservar informe y corridas originales.

Informe canónico corregido de RUN-046: docs/nba_reglas_archivadas_y_liquidacion_v2_20261007.md; corrección documental NBA-RUN-047.

### NBA — todas las casas de la lista hispanohablante, autorizado 2026-10-07

- [x] Verificar el baseline RUN-047 y registrar las 22 combinaciones casa/país de México, Colombia, Perú y España; preservar los cinco perfiles anteriores.
- [x] Recuperar fuentes oficiales y revisar reglas NBA por mercado: participación, prórroga, push, suspensión y correcciones; separar páginas generales, contenido educativo, bloqueo y documentos con jurisdicción distinta.
- [x] Consultar historia archivada de forma acotada; verificar replays recuperables y no inferir recepción original ni vigencia contractual de tickets.
- [x] Crear catálogo y matriz completa con procedencia, hashes y desconocidos; validar preservación, arnés posterior y checkpoint NBA-RUN-048 sin liquidaciones ni créditos pagados nuevos.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-048: recuperar reglamentos NBA pendientes (BetPlay, Apuesta Total, BetMéxico, DoradoBet, Betsson Perú, Inkabet, Sportium Colombia), validar Te Apuesto online/Luckia y push/correcciones; obtener tickets/contratos y ampliar props LATAM/REB/AST. Matriz: docs/nba_casas_hispanohablantes_reglas_20261007.md.

### NBA — recuperación acotada con MCP tras RUN-048, autorizado 2026-10-07

- [x] Verificar las 48 corridas, 19.636 evidencias y 97 eventos previos antes de recuperar nuevas fuentes.
- [x] Probar seis reglamentos oficiales mediante ZenRows MCP con país explícito, reserva inicial de 150 y seguimiento explícito de 100 créditos; cota final 2.232/3.200; registrar contenido, gastos y fallos sin reintentos automáticos.
- [x] Auditar dos repositorios adicionales fijando commits y blobs; separar recomendaciones y líneas sintéticas de cuotas históricas verificables, sin llamadas OddsAPI.
- [x] Validar nuevas pruebas y preservación, ejecutar arnés posterior y sellar NBA-RUN-049 con los pendientes reales.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-049: Apuesta Total/BetMéxico/DoradoBet/Betsson Perú/Inkabet específicos NBA; Te Apuesto online/Luckia, ambigüedades BetPlay/Sportium CO y push/correcciones; contratos por ticket, cuotas LATAM/REB/AST/cortes, relojes de candidatos y contexto médico BOS–NYK. BetPlay y Sportium Colombia avanzaron con18 cláusulas. Informe: docs/nba_reglas_colombia_y_props_candidatos_20261007.md.

### NBA — consolidación deportiva y validación F4, autorizado 2026-10-07

- [x] Verificar RUN-049, 19.744 evidencias y cadena de 98 eventos; fijar fuentes y protocolo antes de calcular resultados nuevos.
- [x] Consolidar minutos de regulación desde rotaciones aceptadas y rosters con IDs NBA, conservando DNP, prórrogas, integridad y límites de recepción original.
- [x] Comparar distribución histórica de diez apariciones con referencia reciente de cinco encogida hacia veinte; evaluar tres temporadas/tres bloques, intervalos por fecha, abstenciones y estratos definidos por historial.
- [x] Probar exclusión de resultados del día/futuro e invariantes; ejecutar suite NBA/arnés, sellar RUN-050 y documentar avances y requisitos pendientes de F4.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-050: completar F4.1 por rol/contexto, F4.2 disponibilidad y minutos jerárquicos con variables as-of, F4.3 escenarios y conservación conjunta; calibrar/confirmar en cortes separados. G0–G9 pendientes. Informe: docs/nba_f4_minutos_regulacion_20261007.md.

### NBA — corregir calibración y coherencia F4, autorizado 2026-10-07

- [x] Verificar RUN-050 y fijar un protocolo antes de ajustar: train 2021-22, validación 2022-23, evaluación exploratoria 2023-24–2025-26; conservar la advertencia de histórico ya inspeccionado.
- [x] Ajustar amplitud por historial de minutos exclusivamente en train, con soporte 0–48 y estado explícito de validación; congelar parámetros antes de evaluar temporadas posteriores.
- [x] Implementar distribuciones conjuntas de minutos que sumen 240 por equipo y respeten activo/DNP, con abstención ante escenarios inviables; separar escenario de disponibilidad acreditada.
- [x] Probar separación temporal y restricciones, evaluar datos y escenarios completos sin atribuir información prepartido inexistente, ejecutar arnés posterior y sellar RUN-051 con límites y siguiente fase.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-051: continuar F5 en investigación con protocolo de tasa por minuto y splits congelados; excluir OT sin estadísticas por periodo. Conservar RUN-050 como referencia CRPS. Disponibilidad/rol y dependencia de rotación prospectiva de F4 siguen pendientes; G0–G9 no aprobados. Informe: docs/nba_f4_calibracion_y_coherencia_20261007.md.

### NBA — distribución de rebotes F5, autorizado 2026-10-07

- [x] Verificar RUN-051, traspaso y fuentes; fijar protocolo de rebotes sin OT, prior heredado, train2021-22/validación2022-23/evaluación2023-26 y métricas antes de ajustar.
- [x] Construir tasas con historia previa noOT y combinar con minutos RUN-050; ajustar dispersión NB solo en train, comparar Poisson de media reciente/mezcla Poisson/Gamma-Poisson/NB en validación y congelar elección antes de evaluación.
- [x] Evaluar CRPS/NLL/Brier/PIT discreto y masa central por fecha/temporada/bloques; separar diagnóstico de minutos ampliados y push/void sin contratos ni disponibilidad inventados.
- [x] Probar probabilidades, colas, temporalidad y contaminación; ejecutar suite NBA/arnés posterior, verificar evidencias y sellar RUN-052 con la referencia elegida y pendientes reales de F5/F6.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-052: F6 auditoría PIT/fugas/contexto y protocolo de confirmación futura; F5 calibración completa/rol/ritmo y OT con estadísticas por periodo. Disponibilidad/recepción/contratos y G0–G9 siguen pendientes. Informe: docs/nba_f5_distribucion_rebotes_20261007.md.

### NBA — ensayos locales de entrega y observación F6, autorizado 2026-10-07

- [x] Verificar RUN-052 y preservar sus 52 corridas, 19.873 evidencias y cadena de 109 eventos; fijar protocolo antes de los ensayos.
- [x] Probar reinicios, exclusión de duplicados, expiración, 429 y timeout del outbox local; conservar incertidumbre sin reintentos ciegos y registrar relojes de envío reales.
- [x] Evaluar demoras 0/15/30/60/120/300 segundos con snapshots de contrato/versionado; excluir revisiones recibidas después del corte y reportar observaciones censuradas sin interpolar cuotas.
- [x] Ejecutar suite NBA y arnés, revisar/sellar NBA-RUN-053 y documentar requisitos reales de Postgres, canal, recepción/contratos y confirmación F7. Ensayos sintéticos locales, cero mensajes externos y cero APIs pagadas; G6 pendiente.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-053: integrar outbox/ledger NBA aislados en Postgres, ensayar canal con configuración privada y medir contratos/acuse reales; completar F6 antes de activar F7. Propuesta F7 sin iniciar; disponibilidad/OT/recepción externa y G0–G9 pendientes. Informe: docs/nba_f6_entrega_y_observaciones_20261007.md.

### NBA — outbox Postgres aislado F6, autorizado 2026-10-08

- [x] Verificar RUN-053 y conservar 53 corridas/19.920 evidencias/111 eventos; usar PostgreSQL16 instalado fuera de PATH para clúster temporal NBA, autenticación privada y solo loopback.
- [x] Implementar esquema y adaptador NBA con sellado+cola y reclamación+intento atómicos, inmutabilidad, deduplicación y ausencia de reintentos ante incertidumbre.
- [x] Probar transacciones reales, concurrencia, rollback, interrupción, caducidad y reinicio del servidor; exportar evidencia sin credenciales y detener el clúster de ensayo.
- [x] Ejecutar suite NBA/arnés posterior, revisar y sellar RUN-054; conservar G6 pendiente hasta canal y cuotas reales, sin cambios en fútbol ni mensajes externos.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-054: configurar canal operativo privado y medir acuses/contratos reales para cerrar F6; operación/backup/rendimiento Postgres por validar antes de desplegar. F7 no iniciado, disponibilidad/OT/recepción anclada y gates pendientes. Informe: docs/nba_f6_postgres_durable_20261008.md.

### NBA — restauración y métricas de entrega F6, autorizado 2026-10-08

- [x] Verificar RUN-054: 54 corridas/19.962 evidencias/113 eventos; conservar código y datos fuente, sin valores privados en logs.
- [x] Probar pg_dump/pg_restore reales sobre una segunda base NBA; verificar igualdad de ledger/cola y permisos, sin modificar la base de fútbol ni la fuente del backup.
- [x] Preparar métricas comunes de ledger con acuses faltantes y anomalías temporales explícitas; usar credenciales de fútbol en el VPS según respuesta directa, con un único mensaje operativo NBA y sin copiar secretos al equipo local.
- [x] Ejecutar suite NBA en la base restaurada y arnés posterior, detener servidor, revisar/sellar RUN-055; canal/cuotas reales y F7 permanecen pendientes si no llegan credenciales.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-055: mejorar recorrido de entrega desde VPS y reunir muestra de acuses; capturar disponibilidad/contratos reales y anclar recepción. Backup en otro servidor/roles/retención y operación continua pendientes. Un mensaje aceptado no aprueba G6; F7 sin iniciar. Informe: docs/nba_f6_backup_y_canal_vps_20261008.md.

### NBA — entrega reutilizable, recuperación fuera del equipo y captura F6, autorizado 2026-10-08

- [x] Verificar RUN-055, congelar protocolo y preservar 55 corridas/20.038 evidencias/116 eventos; cero APIs de datos pagadas nuevas.
- [x] Probar transporte SSH reutilizable con máximo tres mensajes técnicos, relojes separados, caducidad y ausencia de reintentos; conservar muestras pequeñas sin aprobar p95.
- [x] Restaurar backup NBA en contenedor nuevo aislado del VPS, reconstruir roles sin contraseñas previas, comparar datos/permisos y conservar copia con hashes fuera del equipo.
- [x] Preparar captura propia de respuestas/contratos/contexto con procedencia, desconocidos y operación prospectiva; recuperar contexto NBA público si disponible sin retrofechar históricos.
- [x] Probar controles, verificar evidencias, ejecutar arnés posterior y sellar RUN-056; documentar entradas reales pendientes sin iniciar F7 por suposición.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-056: fuente funcional de cuotas/contratos LATAM y disponibilidad/rol previos, prórroga compatible, anclaje independiente, control de relojes, muestra operativa completa y backups periódicos/retención. Dos acuses calientes0,42/0,48s no aprueban p95. Copia/restauración VPS del ledger de ensayo verificadas; no respaldo integral histórico. Tres capturasNBA403. F7 draft_not_started. Informe: docs/nba_f6_transporte_y_recuperacion_vps_20261008.md.

### NBA — fuentes accesibles, anclaje y operación de captura, autorizado 2026-10-08

- [x] Verificar RUN056 y preservar56 corridas/20.143 evidencias/123eventos; fijar protocolo de recuperación gratuito antes de nuevas capturas.
- [x] Recuperar fuentes públicas NBA/ESPN y catálogos de cuotas LATAM, distinguir temporada/competición/roster/lesiones/estado y obtener datos originales accesibles sin APIs pagadas nuevas.
- [x] Implementar y probar anclaje RFC3161 externo con hash/nonce/cadena de certificados; acreditar existencia nueva sin retrofechar recibos históricos.
- [x] Preparar operación de captura NBA aislada y respaldos verificables con retención explícita; corregir controles de reloj/prórroga según evidencia disponible.
- [x] Validar controles y preservación, ejecutar arnés final, sellar RUN057 y señalar únicamente los requisitos reales aún no satisfechos.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-057: props individuales LATAM con contratos/reglas completos; disponibilidad/rol por partido y membresía oficial actual; modelo compatible con prórroga; muestra operativa completa/p95 y caducidad entre relojes; respaldo integral y copia periódica fuera del VPS. Captura de investigación activa cada 15 minutos, siete archivos diarios configurados, dos manifiestos RFC3161 verificados; Caliente VPS403. F7 draft_not_started. Informe: docs/nba_f6_captura_anclada_y_operacion_20261008.md.

### NBA — partido completo, contexto oficial y contratos, autorizado 2026-10-08

- [x] Preservar RUN057 y fijar fuentes/protocolo antes de consultar o ajustar modelos; excluir trabajo de copias periódicas por petición explícita del usuario.
- [x] Recuperar contexto oficial de equipos/partidos y mercados públicos disponibles, verificar IDs actuales y separar pertenencia, diagnóstico y disponibilidad por evento.
- [x] Construir una referencia causal de rebotes de partido completo que conserve juegos con prórroga, con protocolo retrospectivo fijado y evaluación de todos los partidos elegibles sin exclusión por OT posterior.
- [x] Revisar contratos/reglas aplicables y controles de reloj/caducidad; mantener desconocidos y límites de fuente, sin habilitar compras, apuestas o publicación comercial.
- [x] Validar cambios, verificar preservación y arnés final, actualizar propuesta F7 y sellar RUN058; dejar fuera nuevas copias periódicas.

- [x] (cerrada 25-oct: estado de un run NBA antiguo, sustituido por el estado NBA del 24-25 oct) NBA-RUN-058: contratos reales de props LATAM, disponibilidad/rol y universo previo, dos identidades actuales, confirmación F7/revisión independiente, muestra operativa p95 y prueba real de caducidad. Referencia fullgame conserva OT y mejora CRPS retrospectivo; no promoción. Copias periódicas excluidas por el usuario. Nuevo manifiesto local preparado; envío de hash a DigiCert rechazado por revisión automática, requiere autorización específica. Informe: docs/nba_f6_partido_completo_y_contexto_oficial_20261008.md.

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

## Alta probabilidad ampliada 62–95 % (2026-10-11, decisión del usuario)

- [x] Medición de los tramos 62–80 % (`eval/alta_prob_calibracion.py --amplio`).
- [x] `db/057`, `publish/alta_prob_ext.py`, sellado `alta_ext`, liquidación, app.
- [x] (hecho 12-oct) Desplegar: aplicar db/057, `ALTA_PROB_EXT_ENABLED=1` antes del sellado del
      12-oct (08:00 UTC), `preview` y verify del primer lote; si se retrasa, mover
      `LOTE_ALTA_EXT_DESDE`. Recompilar la app (texto 62–95 %).

## Tapjoy: HTML visible al abrir ofertas (2026-10-12)

- [x] Sustituir errores crudos del SDK por códigos y avisos en los seis idiomas; evitar solicitudes simultáneas, limitar la espera y actualizar SDK Android a 14.8.0.
- [x] Verificar la regresión de HTML, reintento y concurrencia: 16 pruebas Flutter y análisis sin incidencias; arnés final 977 aprobadas/24 omitidas.
- [x] Confirmar apertura del proveedor en la sesión de prueba del usuario; detalle en el seguimiento de BlueStacks.
- [ ] Confirmar acreditación de una oferta real; aprobación comercial pendiente.
- [x] Generar APK release con Tapjoy 14.8.0, comprobar firma vigente y entregar artefacto `.local/artifacts/QuantFut-ofertas-corregidas-20261012.apk`.

- [x] Seguimiento Tapjoy: identificar `no_currency`, verificar clave/moneda/tarjeta y registrar BlueStacks como prueba con autorización explícita. Offerwall abrió Tapjoy Test CPA de 7 monedas.
- [ ] Tapjoy comercial: aprobación de cuenta/aplicación y prueba de acreditación de una oferta confirmada; las ofertas de prueba no acreditan este hito.

## Continuar recuperación xG LaLiga 2 y Ligue 2 — 2026-10-13

- [x] Revisar estado, arnés y nuevas fuentes públicas históricas.
- [x] (cerrada 25-oct: Serie B, LaLiga 2 y Ligue 2 retiradas (db/086, db/088)) Incorporar únicamente parejas verificadas de archivos FBref con recepción real, resultados e identidades corroboradas.
- [x] (cerrada 25-oct: Serie B, LaLiga 2 y Ligue 2 retiradas (db/086, db/088)) Verificar y terminar la carga SofaScore pendiente; conservar modelo activo.
- [x] (cerrada 25-oct: Serie B, LaLiga 2 y Ligue 2 retiradas (db/086, db/088)) Completar los huecos restantes con fuentes por partido verificables, sin promedios ni valores inventados.

## PitchAPI — histórico de las 23 competiciones (2026-10-14)

- [x] Descargar listas y estadísticas de PitchAPI con recibos y hash; sin fallos.
- [x] Importar xG emparejados con identidad corroborada (5.355), con ensayo revertido.
- [x] (cerrada 25-oct: Serie B, LaLiga 2 y Ligue 2 retiradas (db/086, db/088)) Huecos restantes desde 2024: Serie B 588, LaLiga 2 236, Argentina 208, Ligue 2 144; PitchAPI no los cubre.
- [x] (cerrada 25-oct: PitchAPI retirado el 25-oct) PitchAPI aún no se usa para alineaciones, jugadores ni eventos (`/lineups`, `/players`); no se descargaron.

## PitchAPI como respaldo y cotejo de API-Football (2026-10-14)

Decisión del usuario: PitchAPI descarga sola, con la clave editable desde el
panel `/control`, como verificador y respaldo de API-Football. Resultados:
solo AVISOS de discrepancia, nunca relleno ni cierre automático (IDs de
partido inestables, sin SLA, sin términos publicados). Relleno automático
solo de xG. Pendiente del usuario: preguntar al proveedor por uso comercial y
almacenamiento, y conseguir una clave `pk_live_` (la `pk_test_` anterior se
revocó sola el 14-oct).

- [x] `db/065`/`066` (semilla de 496 equivalencias): `pitchapi_settings` (singleton: activo, clave cifrada, pista),
  `leagues.pitchapi_id`, `pitchapi_teams` (equivalencias con evidencia),
  `pitchapi_team_votes`, `pitchapi_discrepancies`, `pitchapi_originals`.
- [x] Job `qf.ingest.pitchapi_respaldo` (cron 12:40 UTC, tras el xG de AF):
  `/v1/date/{d}` de los últimos 10 días (1 llamada por día), equivalencias de
  clubes por corroboración, discrepancias (marcador distinto, resultado sin
  cerrar, partido ausente), alerta por Telegram operativo, health en
  `ingest_health`. Sin clave o desactivado: no hace nada ni falla.
- [x] xG de respaldo: solo terminados hace más de 48 h sin xG (AF tiene su
  oportunidad primero), `xg_source='pitchapi'`, `xg_recorded_at` = recepción
  real, original guardado con hash. Nunca sobrescribe.
- [x] Panel `/control/respaldo`: clave cifrada (AES-GCM, solo escritura, pista
  de 4 caracteres, `admin_audit`), activar, probar conexión, última pasada,
  discrepancias abiertas con "marcar revisada", xG rellenados.
- [x] Pruebas (18) y arnés 1.067 aprobadas; commit hecho.
- [x] Desplegado el 14-oct (migraciones, worker, API, cron) con la clave cifrada en la base y el respaldo activo; ver docs/pitchapi_respaldo_20261014.md.
- [x] (cerrada 25-oct: PitchAPI retirado el 25-oct) Clave `pk_live_` y consulta al proveedor sobre uso comercial y almacenamiento.

## Auditoría de datos y entradas del motor — 2026-10-14

- [x] Revisar las 23 competiciones en producción, históricos desde 2024/2025,
  próximos siete días, XI, jugadores, bajas, clima, sede, árbitro y cuotas;
  distinguir disponibilidad archivada, integración y recepción previa al partido.
  Informe: `docs/auditoria_datos_modelo_20261014.md`. Solo lectura; modelo intacto.
- [x] (cerrada 25-oct: `estadisticas_jugador` solo la escribía API-Football, retirada; FotMob y SofaScore guardan NULL)
  Preservar dato ausente frente a cero en estadísticas individuales antes
  de ampliar los ratings; integrar identidades y campos archivados y evaluar
  cualquier nuevo modelo antes de promoverlo (propuesta, sin implementación).

## App — historial del Reto Escalera con detalle (2026-10-14)

- [x] Los retos cerrados se abren y enseñan sus escalones (partido, selección en el
  idioma del usuario, cuota, marcador, fecha); un solo reto desplegado a la vez. El
  historial enseña los 9 últimos retos cumplidos y el último fallido (decisión del
  titular, 2026-10-14), sin filtros. Backend: `_paso_publico` añade `selection` y
  `line`. Pruebas en `live_ladder_test.dart` y `tests/test_escalera.py`.

- [x] Cuota de la doble oportunidad en alta probabilidad (2026-10-14): `_ref_nuevos` la lee de API-Football; prueba en `tests/test_alta_prob_datos.py`.
- [x] Hándicap sin cuota en alta probabilidad (2026-10-14): captura del bet 4 de API-Football en `af_odds` y lectura en `_ref_nuevos`. Medir en 1-2 días qué parte sale con cuota.
- [x] Tope de 4 gratis en Inicio y Alta probabilidad (2026-10-14): `cap_free` en `api/mobile.py`; texto de la app en 6 idiomas.
- [x] El parley excluye las patas de mercados bloqueados por el control de alta probabilidad (2026-10-14): `pl.sin_bloqueados`, `pd.mercados_bloqueados`.
- [ ] Medir la calibración de tarjetas y córners en el parley (dominan los tickets y no tienen historial propio) antes de dar más peso a esos mercados.
- [x] Seguimiento sin publicar de tarjetas (db/068, `publish/tarjetas_seg.py`, sellado desde 2026-10-15) e informe `eval/calibracion_mercados.py` de prometido frente a real por mercado (2026-10-14).
- [ ] Revisar el informe de calibración cuando `tarjetas_seg` tenga ~100 liquidadas; decidir entonces si tarjetas necesita bloqueo, calibración suave o más peso en el parley.
- [x] Compartir el código de referido con enlace `/i/CODIGO` (página del servidor en 6 idiomas) y «Pegar código» en Coins (2026-10-14).

## Referidos al subir la app a la Play Store (anotado el 2026-10-14, para ese día)

**Estado hoy.** El código se comparte con `https://pronosticosdeportivos.pro/i/CODIGO` (página del
servidor, 6 idiomas, `api/invitacion.py`) y el invitado lo escribe o pega en Coins («Pegar código»
acepta el código, el enlace o el mensaje entero) dentro de los 7 primeros días de su cuenta. La app
aún se distribuye como APK y no lee nada al instalarse. Reglas del servidor sin cambios: invitador
verificado y anterior, un código por invitado, no auto-invitación; los premios (+200 invitador,
+100 invitado) se dan cuando el invitado completa ofertas confirmadas por ≥100 monedas
(`rewards.qualify_referral`) y se revierten si las ofertas se anulan. Detalle: `progreso.md`
(2026-10-14, «Compartir el código de referido…») y
`apps/mobile/docs/APP_REAL_MONEDAS_REFERIDOS_20261011.md`.

**Qué se hace el día que haya app en la Play Store** (empezar con una instalación REAL desde una pista
de pruebas internas: la lectura del referrer no se puede probar sin Play):

- [ ] Poner `APP_DOWNLOAD_URL` en el `.env` de la API con el enlace de la ficha
      (`https://play.google.com/store/apps/details?id=com.saptain.quantfut`). La página `/i/CODIGO`
      enseña entonces «Descargar la app». Cambiarlo exige recrear solo el contenedor de la API
      (`up -d --no-deps api`); el worker no lo lee.
- [ ] En `api/invitacion.py`: si la URL es de Play, añadir `&referrer=invite%3DCODIGO` (codificado) para
      que el código viaje con la instalación. Prueba: el enlace generado lleva el código bien
      codificado y no se añade nada a URLs que no sean de Play.
- [ ] En la app, leer el referrer de instalación de Google Play en el primer arranque (paquete
      `android_play_install_referrer` o equivalente; solo Android y solo si se instaló desde Play), guardar
      el código en el teléfono y registrarlo SOLO cuando la cuenta esté creada y con el correo
      verificado (la API exige `verified_account`), dentro de los 7 días. Si el servidor lo rechaza,
      dejar el campo de Coins relleno para que el usuario lo vea. Sin permisos nuevos que haya que
      declarar; sí revisar la sección de seguridad de datos de la ficha.
- [ ] App Links: servir `/.well-known/assetlinks.json` con la huella SHA-256 de la clave de firma FINAL
      de Play (con Play App Signing NO es la de `C:/1. llave/llave.jks`: se copia de la Play Console →
      Integridad de la app), `intent-filter` con `autoVerify` para `/i/*` en el manifiesto y leer el
      enlace al abrir (paquete `app_links`). Efecto: quien ya tiene la app abre el enlace directo en
      Coins con el código relleno. Registrar también la huella en Firebase (ya se hizo con las otras claves).
- [ ] Caddy/Cloudflare: comprobar que `/.well-known/assetlinks.json` llega sin caché agresiva y con
      `Content-Type: application/json`.
- [ ] Probar el recorrido completo con dos cuentas reales: A comparte, B instala desde la pista de
      pruebas, crea cuenta, verifica, completa ofertas por ≥100 y comprobar +200/+100 en el
      movimiento de cada una y en `/control/recompensas`.
- [ ] Traducciones en los 6 idiomas de cualquier texto nuevo de la app (regla del proyecto) y nota en
      `progreso.md` con lo medido.

**No cubierto por Play (decisión pendiente).**
- [ ] iOS: no existe un referrer equivalente. Opciones: servicio de terceros (Branch, AppsFlyer, Adjust),
      que añade SDK y política de privacidad, o dejarlo manual como hoy. Firebase Dynamic Links está
      retirado por Google. Decidir cuando haya fecha para iOS.
- [x] (cerrada 25-oct: nota, no tarea) Instalaciones por APK suelto: no traen referrer; seguirán con «Pegar código».

**Límites a recordar.** Un código que llega por referrer es tan falsificable como uno escrito: lo que
protege es la condición de completar ofertas. El referrer de Play solo se conserva unos 90 días y
puede tardar en estar disponible tras instalar; reintentar en los primeros arranques.

## Videos con recompensa de AdMob (2026-10-14)

Detalle en `docs/admob_recompensas_20261014.md`.

- [x] Migración `db/069`, verificación SSV, tickets con tope/pausa/día UTC, callback que acredita, panel
      `/control/anuncios`, `app-ads.txt`, flujo y tarjeta en la app, 6 idiomas. Apagado y en modo prueba.
- [x] Autorización de AdMob: el titular indica que AdMob ya está autorizado para la app (sin documento
      adjunto en el repo). Sigue siendo prudente bloquear la categoría de apuestas en los controles de AdMob.
- [x] Política de privacidad redactada con AdMob (tabla de datos, elección opcional, proveedor, CCPA) en
      `docs/legal/PRIVACIDAD_QUANTFUT.md` y regenerada en `legal_pages/privacidad.html`. **Sin versión nueva a
      propósito:** `CONSENT_VERSION` (servidor) y `'2026-10-12'` (app, `live_api.dart`) deben coincidir o se
      rechazan los registros; subirla exige publicar app y servidor a la vez. **Desplegada** (imagen
      `quantfut-api-admob:20261014c`). Revisión legal hecha: el titular lo confirma (sin documento adjunto en
      el repo). Términos de uso (sección 5) redactados con los videos con recompensa y regenerados en
      `legal_pages/terminos.html`, sin subir la versión por la misma razón. **Desplegados** (imagen
      `quantfut-api-admob:20261014d`). Revisión legal hecha: el titular lo confirma (sin documento adjunto en
      el repo).
- [x] `db/069` aplicada y API desplegada el 15-oct (imagen `quantfut-api-admob:20261014b`, worker intacto,
      anuncios apagados y en modo prueba). Falta configurar el bloque con SSV en AdMob y el panel, probar
      con la herramienta de SSV de AdMob y en un teléfono con bloques de prueba.
- [x] Anuncios ACTIVADOS en producción en modo prueba (a petición del titular): `ads_enabled=TRUE`,
      `ad_test_mode=TRUE`, sin IDs reales; entrega los bloques de prueba oficiales de Google. Fila en
      `admin_audit`. La app instalada no muestra nada (aún no tiene el código); el APK de depuración de la rama
      sí, con IDs de app de ejemplo, y apunta a producción.
- [ ] Sustituir el ID de APP de ejemplo por el real (AndroidManifest / Info.plist); declaraciones de Play.
      Pendiente de que el titular consiga una cuenta de AdMob (el Chrome conectado no tiene una).
- [ ] Más adelante, con datos reales: mediación (Unity Ads, AppLovin) sobre AdMob.


## Integracion de datos disponibles al motor — 2026-10-15

Peticion del titular: cargar el archivo disponible, identidades verificadas y contexto; iniciar capturas prospectivas sin comprar cierres de cuotas.

- [x] (cerrada 25-oct: duplicada de F4) Migracion aditiva y puente de jugadores con evidencia por partido; conservar NULL y recepcion real.
- [x] (cerrada 25-oct: hecho: XI, jugadores, bajas, entrenadores y ronda en tablas (db/075)) Incorporar XI, suplentes, estadisticas, bajas, entrenadores, ronda y estilo, con ensayo y carga idempotente.
- [x] (cerrada 25-oct: hecho: captura FotMob previa y posterior (db/081, reactivada el 25-oct)) Capturas FotMob previa/posterior y calendario; altitud y pronosticos con credencial contratada.
- [x] (cerrada 25-oct: duplicada de F12) Derivados de descanso, eliminatorias y clasificacion; identidades arbitrales y de copas sin uniones ambiguas.
- [x] (cerrada 25-oct: ERA5 hecho; los 527 snapshots están en «Recuperación de cierres Pinnacle») Verificar en produccion, documentar conteos y pendientes concretos. ERA5 requiere token; 527 snapshots expresamente pendientes.


## Meta (App Events + CAPI) y suscripciones en la app — 2026-10-15

Diseño aprobado: `docs/superpowers/specs/2026-10-15-meta-compras-design.md`. Procesador de pago de la
APP decidido por el titular: Google Play Billing / StoreKit, suscripción renovable sin prueba gratis
(la web sigue pendiente). Seguimiento encendido por defecto en todo el mundo, desactivable en Perfil.
Google Sign-In ya existe: no se rehace.

- [x] Leer la documentación oficial (Meta, pub.dev, Google Play, Apple) y aprobar el diseño por secciones.
- [x] Revisar la spec (titular) y escribir el plan de implementación:
      `docs/superpowers/plans/2026-10-15-meta-compras.md` (17 tareas, rama `feat/meta-compras`).
- [x] `db/071`: `store_transactions`, `meta_events`, `meta_identities`, columnas de tienda en `plans`,
      `accounts.store_account_token`. Aditiva; sin tocar triggers de `subscriptions`.
- [x] Servidor: verificación Play (subscriptionsv2) y Apple (JWS), RTDN y notificaciones V2, `grant`/`revoke`
      idempotentes por `order_id`; `STORE_PURCHASES_ENABLED=0`.
- [x] Servidor: cola y envío CAPI (`action_source=app`), normalización y hash, `META_CAPI_ENABLED=0`.
- [x] App: `in_app_purchase` en la pantalla VIP, `facebook_app_events` con inicio controlado, ATT, ID de
      publicidad, eventos del mapa, interruptor en Perfil; 6 idiomas.
- [x] Política, términos y `CONSENT_VERSION` nuevos (servidor acepta la anterior y la nueva en la transición).
- [ ] Del titular: credenciales de Meta, productos y cuenta de servicio de Play, Pub/Sub, pruebas internas.
- [x] API y `db/071` desplegadas el 2026-10-15 (apagadas); rama `feat/meta-compras`, ver `DEPLOYS.md`.
- [ ] Tras tus credenciales: probar en «Probar eventos» y en el entorno de pruebas de Play; alinear el worker (cron `meta_capi`) ANTES de `META_CAPI_ENABLED=1`; publicar la app en Play.

## API-Tennis: prueba autorizada (2026-10-17)
- [x] Validar conexion y muestra acotada de calendario, resultados, estadisticas y precision temporal; seis respuestas correctas, originales con hashes y sin clave. Informe docs/tenis_api_tennis_prueba_20261017.md.

## Tenis: evaluador comun y carga observable (2026-10-17)
- [x] Implementar contratos tipados, evaluador de muestra comun, extractor con disponibilidad previa y limites temporales; sin viajes/clima.
- [x] Conectar modelo actual y ajuste regularizado de carga con validaciones temporales; ajuste real pendiente de muestra valida, abstencion explicita.
- [x] Probar fugas, duplicados, datos faltantes y simetria; 75 pruebas tenis aprobadas. Dos predicciones reales base y cero comparaciones evaluables; informe docs/tenis_carga_evaluacion_fase1_20261017.md.

## Tenis: captura de estados y Weighted Elo (2026-10-17)
- [x] Capturador API-Tennis acotado con originales, recibos, estados e historial inmutable; dos consultas reales y 113 nuevas observaciones.
- [x] Weighted Elo con formula publicada y adaptacion por periodos; evaluado ATP/WTA, inferior al hibrido actual y conservado como referencia.
- [x] 96 pruebas tenis aprobadas, muestra real limitada e informe docs/tenis_estados_weighted_elo_20261017.md; sin promover modelos por resultados de desarrollo.

## Web: rediseño futurista integral (2026-10-17)
- [x] Rediseñar todas las vistas del frontend con una capa HUD responsive; conservar contratos, estados y accesibilidad.
- [x] Actualizar identidad, navegación, controles, tarjetas, tablas, productos, acceso, cuenta, modales y navegación móvil.
- [x] Documentar la adaptación de CYBERCORE CSS / Cyberpunk CSS y verificar las 25 pruebas del frontend.
- [x] Integrar CYBERCORE CSS 0.3.0 como dependencia exacta, vendorizar CSS/licencia para uso sin CDN y aplicar sus clases reales en toda la interfaz.
- [x] Adoptar la paleta oficial, tarjetas recortadas, controles HUD, efectos de escaneo/datos e iconografía SVG; adaptar Cyberpunk CSS sin cargar sus reglas globales conflictivas.

## Tenis: registro de sedes por edicion (2026-10-17)
- [x] Registro de sedes con fuentes, disponibilidad, vigencia y enlaces exactos; techo real desconocido.
- [x] Ocho recintos para siete ediciones; 102/102 encuentros ATP/WTA de la muestra enlazados. 126 restantes sin sede y 48 discrepancias de temporada marcadas.
- [x] Calendario enriquecido, 116 pruebas tenis aprobadas y cobertura documentada sin modificar probabilidades. Altitudes pendientes por falta de fuente disponible.

## Tenis: Open-Meteo sin clave, alcance no comercial (2026-10-17)
- [x] Registrar aclaracion del titular: proyecto de tenis no monetizado; usar acceso gratuito sin clave. No trasladar condiciones comerciales de futbol a esta investigacion.
- [x] Una consulta exitosa para ocho recintos; altitudes Copernicus GLO-90 con originales, recibo y SHA-256. Registro append-only y calendario v3 con 102 encuentros enriquecidos.
- [x] Validar orden/coordenadas, rangos, fuentes, cobertura e invariancia temporal; 116 pruebas tenis aprobadas. Quedan 126 encuentros sin sede y 48 discrepancias; pronostico meteorologico aun no capturado.

## Tenis: completar sedes y revisar temporada (2026-10-18)
- [x] Contrastar 37 grupos pendientes con fuentes primarias, registrar sedes y coordenadas solo donde haya evidencia.
- [x] Implementar revisiones por evento con evidencia, disponibilidad previa, original intacto y pruebas; reconstruir cobertura sin ocultar pendientes.

- [x] Revisados 37 grupos y 31 ediciones: 27 recintos nuevos, 126 encuentros enlazados; total 228/228 con sede principal. Coordenadas nuevas desconocidas, sin imputacion de ciudad.
- [x] FixtureReviews append-only por evento y digest: 48 temporadas corregidas (Guangzhou22,Lisboa18,Cali8), original conservado y disponibilidad estricta. Informe reproducido desde codigo entregado.
- [x] 126 pruebas tenis aprobadas, arnes general1300/88omitidas/2avisos; doce hashes del modelo intactos. Auditoria real as-of previa mantiene102sedes y48discrepancias, sin retroactividad. Ver docs/tenis_sedes_temporadas_completadas_20261018.md.

## Tenis: coordenadas y alcance de viajes entre torneos (2026-10-18)
- [x] Verificar27recintos con evidencia y precision, consultar elevacion de puntos aceptados y actualizar registro sin retroactividad. Cerrado: ver fase coordenadas completas mas abajo.
- [x] Respetar instruccion: viajes solo entre torneos; diferencia horaria con DST, transporte probable como proxy y tiempo entre salida previa/debut, sin inferir efecto deportivo ni itinerario real. Implementado; acreditacion de transiciones reales pendiente.


## Tenis: criterios de viaje contrastados (2026-10-18)
- [x] Contrastar ORS, OSRM, Amadeus y Arcascope; separar rutas/ofertas/simulaciones de viajes reales y rechazar score de fatiga sin calibracion. Ver docs/tenis_viajes_criterios_20261018.md.
- [ ] Tras georreferenciar, implementar transiciones entre ediciones con incertidumbre temporal, DST, transporte candidato y evaluacion temporal; eliminacion-debut no equivale a llegada-debut.


## Tenis: coordenadas completas y viajes experimentales (2026-10-18)
- [x] 27 recintos nuevos WGS84 con fuentes y tolerancia espacial; elevaciones en una consulta Open-Meteo sin clave. Total35recintos/52enlaces/112fuentes,228/228 coordenadas y terreno, anteriorasof102/228 intacto.
- [x] InterTournamentTravelExtractor entregado: solo ediciones distintas con procedencia, consecutividad/debut/cierre/dobles; distancia,DST,direccion,altitud,transporte candidato e intervalo salida-debut programado. Contexto anterior ya no infiere viaje entre partidos.
- [x] 143 pruebas tenis aprobadas (17 nuevas), doce hashes congelados intactos; auditoria historial183/456 con candidato,0transiciones completas verificadas. Sin consultas deportivas/creditosOdds/rutas/vuelos ni cambios probabilisticos.
- [ ] Verificar participacion por jugador/edicion y datos temporales antes de activar variables de viaje en comparacion temporal. Informe docs/tenis_coordenadas_viajes_20261018.md.


## Tenis: comparacion espacial y sensibilidad (2026-10-18)
- [x] Preparar comparador Base/Base+Espaciales/Experimental con interseccion comun y ajuste solo en entrenamiento; experimentos horarios separados y solo con dias verificados.
- [x] Auditar viabilidad temporal sobre archivos reales, ejecutar comparacion o registrar abstencion por falta de muestra sin inventar metricas; mantener holdout/modelos congelados.


- [ ] Acreditar participaciones y acumular muestra temporal antes de ajustar/comparar: ejecucion real devuelve0filascomunes, sinmetricas. Ver docs/tenis_comparacion_espacial_20261018.md.

## Tenis: reconstruccion historica 2024/2025 autorizada (2026-10-18)
- [x] Catalogar472bloques/11240partidos, enlazar187ediciones con evidencia de su temporada (160georreferenciadas,27concoordenadas pendientes);122fuentes recibidas hoy, sin disponibilidad antigua simulada.
- [x] Rama retrospectiva separada: ultima sede observada, kilometros/deltaaltitud/deltahuso; sin descanso ni itinerario real, sin saltar antecedentes desconocidos. Guarda conservadora de7dias porperiodo de fuente.
- [x] Dataset con2982partidos espacialmente aptos, particiones de ediciones completas,2025exploratorio;165pruebas tenis aprobadas,12hashescongelados intactos. Informe docs/tenis_dataset_historico_20261018.md.
- [ ] Ampliar cobertura:52ediciones individuales sinenlacehistorico,17recintos identificados sincoordenadas(27ediciones);233bloquespor equipos/multisede requieren detalle por eliminatoria. Cola data/tennis/historical_venues_20261018/pending_editions.json.
- [ ] Comparar Base/Base+Espaciales en interseccion de predicciones validas y con ajuste soloen entrenamiento;2982es cohorte con datos, nointerseccion ya puntuada. LogLoss/Brier/calibracion pendientes; variantehoraria siguependiente dediasindividuales acreditados.

## Tenis: completar cobertura historica (2026-10-18)
- [ ] Recuperar evidencia de las52ediciones WTA pendientes con archivos por temporada y revisar sedes exactas.
- [ ] Resolver17recintos sincoordenadas con consultas refinadas, objetos revisados y elevacionDEM; no usar respuestas bloqueadas como evidencia.
- [ ] Revisar233bloquesporequipos por eliminatoria/partido, admitir multiples sedes y conservar desconocidos justificados.
- [ ] Reconstruir dataset ampliado separado del original, probar contratos y fuentes, reportar cobertura real restante.

## Comprometer-revelar de la cadena y plan de F7 (2026-10-18)
- [x] `hashchain.py`: al repo público sube solo el compromiso (recibos y `LEDGER.md`); el JSON del lote sube cuando todos los partidos que cita terminaron y pasaron 4 h (tope de 7 días). `verify` recorre por recibos y cuenta aparte los lotes sin revelar. Pruebas: `tests/test_hashchain_revelado.py`. `CHAIN_GIT_REMOTE` sigue vacío: aún no se publica nada.
- [ ] Antes de configurar `CHAIN_GIT_REMOTE`: desplegar este cambio (ensayo + `DEPLOYS.md`) y comprobar `verify` contra los lotes reales del servidor.
- [x] (cerrada 25-oct: hecho: F7 implementado y en producción (19-oct)) F7: plan en `docs/superpowers/plans/2026-10-18-f7-sello-tardio.md` (borrador; tres decisiones del titular al final).

## Web: rediseño CYBERCORE en producción (2026-10-18)
- [x] Integrar CYBERCORE CSS 0.3.0, adaptar Cyberpunk CSS, conservar el logo previo y validar 25/25 pruebas del frontend.
- [x] Fusionar PR #12 y hotfix de assets FastAPI PR #13 con los arneses de GitHub aprobados.
- [x] Desplegar solo la API desde una imagen derivada de la que estaba en ejecución; comprobar dominio, hashes, modelo y cadena; documentar reversión.

- [x] Resuelta la cola original de 52 ediciones individuales, 17 recintos y 233 bloques por equipos. Ampliación separada en historical_coverage_20261018; detalle abajo.
- [x] Comparar Base/Base+Espaciales en intersección de predicciones y con ajuste solo en entrenamiento: ampliación de5798aptos,2965desarrollo/2833evaluación2025exploratoria. Métricas e intervalos entregados; sin mejora clara. Variante horaria sigue pendiente de días individuales acreditados.
- [x] Recuperar evidencia de las 52 ediciones WTA pendientes por temporada; distinguir PDF originales, extractos y corroboración estructurada.
- [x] Resolver 17 recintos originales con puntos WGS84 y terreno DEM; Kempes/Jiujiang conservan referencia de complejo y tolerancia amplia.
- [x] Revisar 233 bloques por equipos: 225 Davis, dos finales BJK, seis multicidad con 178 enlaces por partido; preservar seis revisiones de identidad/fase sin reescribir originales.
- [x] Dataset separado con 11.240 sedes identificadas, 10.510 destinos con coordenadas, 5.798 partidos aptos; 173 pruebas y regresión de 2.982 aprobadas; 12 artefactos congelados intactos. Informe docs/tenis_cobertura_historica_completada_20261018.md.
- [ ] Verificar coordenadas de 88 entradas adicionales identificadas en la ampliación. Comparación y sensibilidad ya ejecutadas, sin evidencia clara para activar la corrección. Sin horas imputadas.

## Tenis: comparación retrospectiva de variables espaciales (2026-10-18)
- [x] Reconstruir base híbrida Markov/Elo por orígenes2023/24/25 con calibraciones anteriores y embargo35días; modelos actuales congelados no reutilizados hacia atrás.
- [x] Corrección ridge1 en2965partidos de2024; muestra común de2833en2025exploratoria, competiciones completas y cobertura52,68%.
- [x] Sensibilidad2851entrenamiento/2718evaluación; LogLoss/Brier/ECE y1000remuestreos por competición. Nueve pruebas nuevas;182tenis aprobadas.
- [x] Auditoría reproduce ajustes y métricas, fuentes e identidades verificadas;12artefactos congelados intactos. Informe docs/tenis_resultados_espaciales_historicos_20261018.md. Sin activación: mejora minúscula e intervalos que incluyen cero,0créditos Odds.

## Tenis: carga observable por rondas anteriores (2026-10-18)
- [x] Auditar ventanas diarias:152observaciones terminales sin límite inferior de finalización acreditado;3/7d conservadas bloqueadas, sin imputación horaria.
- [x] Contadores de rondas previas individuales, orden de cuadro, desconocidos explícitos y exclusión objetivo/futuro; todos los equipos y round-robin fuera del alcance. Primera versión retirada por alcance BJK; válida draw_load_20261018_v2.
- [x] Base/Cobertura/Cobertura+Carga:2130train2024/1957test2025exploratorio, sensibilidad1882/1700; intervalos incluyen cero, sin activación. Informe docs/tenis_carga_rondas_resultados_20261018.md.
- [x] 194pruebas tenis aprobadas (12nuevas), extracción/precedencia/ajustes/métricas reproducidos,12artefactos congelados intactos.0consultas deportivas/0créditosOdds. Cola88sedes priorizada por730destinos; primeras5afectan264.

## Cobro web con Whop + Meta EMQ (2026-10-18)

Diseño: `docs/superpowers/specs/2026-10-18-whop-checkout-meta-design.md`.

- [x] Login Google en la web (Firebase JS → `/app/v1/firebase/web-session`); probado en local. Despliegue: `docs/despliegue_google_web_20261018.md`.
- [x] Fase A: db/083, `comercial/whop.py` (firma, checkout, aplicar pago), rutas y pruebas (11 en `tests/test_whop.py`, 8 con Postgres real).
- [x] Fase B: CAPI web (`action_source=website`: Purchase, Subscribe, InitiateCheckout) + Pixel con advanced matching y `eventID` compartido. Pendiente: CompleteRegistration web y aviso de cookies.
- [x] Fase C: vista de pedido con `Checkout` embebido de Whop (probada en local con clave falsa y webhook firmado simulado; el formulario real de Whop no se pudo ver sin `WHOP_API_KEY`).
- [ ] Datos del titular: `WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`, `plan_` por plan, `META_PIXEL_ID`, token CAPI, aviso de cookies.

## Tenis: cinco recintos prioritarios (2026-10-18)
- [x] Referencias WGS84 verificadas de Hua Hin,Yucatán,Seúl,AbuDabi yMartínCarpena. Yucatán1800mreferenciadecomplejo, restotolerancias400–500m; no pistas históricas exactas simuladas.
- [x] Una consulta pública de terrenoDEM para5puntos, enlaces históricos2024/25 yarchivos previos intactos.294fuentesSHA;157entradas con coordenadas.
- [x] Datasetnuevo historical_geography_top5_20261018:10774destinos/11240,6244aptos(+446),5943sinreferenciasamplias;264destinosrecuperados. Cola83entradas/466destinos. Sin ajuste/activación de modelos.
- [x] Auditoría de fuentes,identidades,particiones,oldfeatures y12artefactos congelados aprobada;194pruebas tenis. Informe docs/tenis_cinco_sedes_verificadas_20261018.md yconstructores entregados al motoraislado.
- [x] Whop configurado (18-oct): producto QuantFut con 3 planes, clave de API (solo IP del VPS) y webhook de producción; claves en el `.env` del VPS. Pendiente al desplegar: `UPDATE plans SET whop_plan_id…` (en `docs/despliegue_google_web_20261018.md`) y `META_PIXEL_ID`.
- [x] Reembolsos: `refund.created/updated` (status succeeded) revocan el periodo del pago; webhook de Whop ya los envía (18-oct).
- [x] Meta web (18-oct): CompleteRegistration web, EMQ con ciudad/estado/zip/teléfono (13 claves), aviso de medición con Rechazar, envío por cron del host, probado con test_event_code.
- [x] Meta a eventos reales: `META_TEST_EVENT_CODE` quitado del `.env` del VPS y API recreada (18-oct, DEPLOYS 21:00 UTC).
- [x] Worker alineado con `meta_capi` (parche del contenedor, DEPLOYS 18-oct 21:25) y cron del host retirado. Pendiente: que la imagen del worker del 1-nov los lleve de serie.
- [ ] Probar un cobro real con Whop (plan de 14,99) y ver el Purchase en Meta con el mismo event_id del Pixel.

## Pronósticos bloqueados difuminados con «Acceso VIP» (2026-10-18, decisión del titular)

- [x] App: la tarjeta de candados de Alta probabilidad va **desplegada por defecto** (se puede plegar); cada fila lleva una franja difuminada (`LockedBlur`, bloques, no texto real) con la cuota a la vista, y el botón pasa a **«Acceso VIP»** (nueva cadena `vipAccessButton` en los 6 idiomas) en la tarjeta de candados, en el candado genérico y en el detalle del partido. 257 pruebas de Flutter y `flutter analyze` limpios.
- Lo gratis sin VIP ya era lo decidido y no cambia: 4 de alta probabilidad (`FREE_MAX`), 1 paso de escalera, 1 parley al día.
- Seguridad del bloqueo: el servidor no envía selección ni probabilidad de un pronóstico bloqueado (`mobile.metadata`), así que el difuminado es solo visual.
- El botón lleva a la pantalla VIP de la app, que compra con Play / App Store. **No** se enlaza a Whop desde la app (las tiendas exigen su sistema para suscripciones digitales); Whop es la pasarela de la web.
- La web no pinta pronósticos reales bloqueados (solo datos liquidados y una maqueta ficticia): sin cambio.
- [ ] Falta una compilación nueva de la app para que los usuarios lo vean (publicación en tiendas: la hace el titular).

- [x] Web (18-oct, tras preguntar el titular si la web también los difuminaba: no lo hacía, ignoraba `vip`): la vista de Alta probabilidad pinta los bloqueados difuminados (`lockedPicksHtml` en `frontend/public-data.js`, bloques sin selección, probabilidad ni cuota) con la **cuota también difuminada** (decisión del titular, 18-oct) y un botón «Acceso VIP» a Suscripciones (Whop). La ruta pública `/alta-probabilidad` ya no envía la `cuota` de lo bloqueado, para que el difuminado proteja algo; **la app no se toca** (lee `/mobile/v1/home` y sigue igual, con su cuota a la vista). 28 pruebas de node, 12 de la web y comprobación visual en navegador. **Falta desplegar** (la web va en la imagen de la API: reconstruir con el procedimiento de `DEPLOYS.md`).
- [x] Escalera y parley en la web (18-oct, pedido del titular): los bloqueados de la escalera salen difuminados (`lockedPicksHtml`) y los parlays bloqueados como tarjeta difuminada con el escalón (`lockedParleyHtml`). Esto arregla además un fallo de la vista de parley: hacía `t.patas.map` sobre todos los tickets y los bloqueados llegan sin `patas`. La ruta pública `/escalera` tampoco envía ya la cuota de lo bloqueada. **La app no se toca.**

- [x] Web pública: **un solo pronóstico gratis visible por sección** (decisión del titular, 18-oct, respuesta «uno por sección»). `/alta-probabilidad` deja visible 1 (el de mayor probabilidad) y pasa los demás a bloqueados difuminados (`WEB_PUBLICO_GRATIS_ALTA = 1` en `api/main.py`); escalera (1 paso) y parley (1 ticket) ya eran uno. **La app no cambia: sigue con 4 / 1 / 1.** Prueba: el bloque de la app conserva sus 4.

- [x] Web: **la cuenta VIP ve todos los pronósticos** (decisión del titular, 18-oct). `/alta-probabilidad` y `/escalera` usan la dependencia `member` (como ya hacía `/parley`): con suscripción activa devuelven todo desbloqueado y `Vary: Authorization`; el visitante sigue viendo 1 por sección. La web envía su sesión (solo en memoria) únicamente a esas tres rutas (`sessionFetch`) y recarga los datos al iniciar o cerrar sesión o activarse la suscripción; una sesión caducada cae a visitante. 32 pruebas de node y las de las rutas con una cuenta VIP simulada. **No probado de punta a punta con una suscripción real** (no hay una cuenta de prueba con pago).

## La información nueva en el motor (2026-10-19, pedido del titular)

- [x] Medición bloque a bloque con el walk-forward del 12-oct (`python -m qf.model.contexto`, solo lectura): **solo la altitud pasa la puerta**, con evidencia débil (ΔRPS −0,0002 a −0,0003 con la semántica de producción, significativo en 1 de 4 particiones). Clima, descanso, bajas y valor del once no mejoran. Detalle: `docs/contexto_en_el_motor_20261019.md`.
- [x] Altitud en el motor A en **modo sombra** (`AJUSTE_ALTITUD_MODO`): `daily.py` calcula el factor y lo anota en `data_completeness.ajuste_altitud` sin alterar los lambdas publicados.
- [ ] Pasar la altitud a `activo` con partidos reales (≥150 con salto > 0,5 km medidos hacia adelante).
- [ ] Reajustar el artefacto en cada reentrenamiento (hoy es del walk-forward del 12-oct) y repetir `qf.model.contexto` cuando haya semanas de `fotmob_previo`.
- [x] (cerrada 25-oct: duplicada de F8/F9) Para que algo llegue a alta probabilidad, escalera y parley (motor B) hace falta F8/F9: mezcla A + B evaluada contra el mercado del mismo momento.

## Córners (2026-10-19, primera mejora pedida por el titular)

- [x] Diagnóstico a fondo (`python -m qf.eval.corners_diagnostico`, `docs/corners_diagnostico_20261019.md`): el modelo está calibrado (41.815 partidos, a menos de 0,6 puntos en todas las líneas y ligas); el déficit de los «menos de» publicados (−5,0 ±3,6, z = −1,4) es ruido de 170 partidos con picks correlacionados. **Corrijo lo que dije el 19-oct: no hay que recalibrar.** Ninguna variable de contexto mejora la predicción del total.
- [ ] Añadir el número de partidos distintos (y error estándar por partido) a las tablas por mercado de `/alta-probabilidad` y del panel: hoy cuentan picks, que son hasta 4 por partido.

## Motor B y copas por partido (2026-10-19)

- [x] Motor B medido por partido (`docs/motor_b_por_partido_20261019.md`): ningún mercado se desvía de forma significativa (|z| < 1,7): totales −1,2, ganador −1,0, ambos marcan −0,5. No hay nada que corregir en las probabilidades.
- [x] Copas europeas: empates reales 20,3 % (Champions) y 24,1 % (Europa League) en el historial, frente a 21,9 % y 25,9 % del modelo: sin sesgo; 2025-26 fue una temporada baja. No se toca.
- [x] **Corregido:** el «fallo grosero» de `alta_prob.control` suponía picks independientes (la ampliada tiene 2.420 picks en 222 partidos) y podía bloquear un grupo por ruido; ahora usa la varianza por partido (la mayor de las dos). Historial y tabla de la web muestran partidos distintos y margen por partido.

## F7 sello tardío (2026-10-19)

- [x] Fases 1-4 implementadas y ensayadas (PR #38, sin fusionar a propósito): migración `db/084`, lectores solo con lotes diarios, `hashchain.seal_partido`/verify/revelado de `partido/…`, `publish/sello_tardio.py` (cron cada 5 min, apagado con `LOTE_POR_PARTIDO_DESDE=None`).
- [x] Desplegado el 19-oct (apagado, `LOTE_POR_PARTIDO_DESDE=None`): #38, migración 084, worker, API y crontab; ver DEPLOYS.md.
- [ ] Fijar `LOTE_POR_PARTIDO_DESDE` (primer día sin lote diario sellado) cuando algún bloque de alineación pase la puerta; hasta entonces no aporta.
- [ ] Medir si algún bloque de alineación (`lineup_challenger`) pasa la puerta con el once confirmado; solo entonces la predicción final difiere de la diaria.
- [ ] Decidir si se envía push al sellar un pick de partido (sigue sin responder).

## Impacto por jugador (2026-10-19)

- [x] `qf.model.jugadores` + bloques `epi_total`/`epi_grupos`/`xi_habitual_valor` en `contexto.py`; medición y robustez en `docs/impacto_jugador_20261019.md`. `epi_total` y `epi_grupos` pasan la puerta (ΔRPS −0,0005/−0,0006, 3 de 4 particiones, placebo limpio); el valor del once vs habitual no.
- [x] Producción: `ajuste_xi` en MODO SOMBRA en la predicción final y `LOTE_POR_PARTIDO_DESDE=2026-10-20` (19-oct; ver DEPLOYS.md).
- [ ] Tras ~150 partidos con efecto: `python -m qf.model.ajuste_xi --medir` y decidir si pasa a `activo` (hoy ese modo no existe en el código).
- [x] Walk-forward ampliado terminado (20-oct): efecto ≈ −0,0002, 5/5 tramos favorables, artefacto reajustado (docs/impacto_jugador_20261019.md).
- [x] Comparado contra el mercado de cada momento: la brecha no se cierra antes del cierre (docs/brecha_mercado_20261019.md).
- [ ] Ampliar el walk-forward del A a 2024-2026 para duplicar la potencia (tarda horas).

## Tenis: segundo bloque de cinco sedes (2026-10-18)
- [x] Chennai, Palermo, Riad, Hengqin y Shenzhen: referencias WGS84 con alcance y tolerancias explícitos. Palermo inferencia de complejo, no cancha exacta. Enlaces históricos intactos; 309 fuentes verificadas.
- [x] Una consulta DEM de cinco puntos; nueva versión historical_geography_batch2_20261018: 10.895 destinos, 6.414 aptos (+170), 6.107 sin referencias >1 km. Cola: 78 entradas y 345 destinos.
- [x] Protocolo espacial fijo repetido: 3.306 entrenamiento/3.108 evaluación; comparación adicional sobre 2.833 IDs originales. Sin mejora clara, sin búsqueda sobre 2025 ni activación.
- [x] 194 pruebas tenis, auditoría desde motor aislado, seis modelos base y 12 artefactos congelados intactos; cuatro scripts e informe entregados. Comprobación general final: 1.315 aprobadas, 95 omitidas y dos avisos; Docker ausente.

## Tenis: tercer bloque de sedes (2026-10-18)
- [x] Taipei, SuperTennis BolognaFiere, AO Arena, SEB y Swiss Tennis Arena con evidencia histórica intacta y WGS84; tres husos completados. Biel referencia de complejo 600 m, huella exacta de arena no acreditada; Taipei fuente del operador mediante extracto de buscador.
- [x] Una consulta DEM de cinco puntos; versión historical_geography_batch3_20261018: 10.954 destinos, 6.442 aptos (+28), 6.135 sin referencias >1 km. 324 fuentes verificadas; cola 73 entradas/286 destinos.
- [x] Protocolo fijo repetido: 3.322 desarrollo/3.120 evaluación; muestras comunes de 3.108 y 2.833 IDs, sensibilidad y calibración. Sin mejora clara, sin selección/activación.
- [x] 194 pruebas tenis, auditoría desde motor aislado, seis modelos base y 12 artefactos congelados intactos; cuatro scripts e informe entregados. Chequeo general final: 1.315 aprobadas, 95 omitidas y dos avisos en 130,60 s; Docker ausente.

## Tenis: cierre integral solicitado (2026-10-18)
- [x] Revisar las 73 entradas geográficas pendientes y sus alias, sin límite de cinco sedes por entrega.
- [x] Consolidar todas las referencias acreditables, husos, DEM y dataset versionado; resolver o documentar individualmente cada entrada.
- [x] Repetir evaluación fija y auditar cobertura, temporalidad y bloqueos restantes del motor.
- [x] Entrega integral con pruebas, fuentes, métricas, límites reales y estado único actualizado.

## Tenis: preparación operativa y validación financiera (18-oct-2026)
- [x] Capturar y normalizar pronósticos Open-Meteo con disponibilidad real y vínculo a coordenadas; techo desconocido permanece desconocido.
- [x] Incorporar registro de selecciones simuladas y evaluación financiera con cuotas archivadas, resultados y retiros, sin fabricar evidencia futura ni ejecutar apuestas.
- [x] Definir controles por variante/mercado: datos opcionales solo bloquean si el modelo los usa; separar aptitud técnica, muestra y ventaja acreditada.
- [x] Probar con capturas reales acotadas, pruebas de integridad/temporalidad y entregar un estado operativo único. 225 pruebas específicas y 1.315 generales aprobadas; informe docs/tenis_preparacion_apuestas_20261018.md.
- [ ] Reunir evidencia prospectiva real bajo financial_policy_v2.json. Cero órdenes financieras; seguimiento predictivo programado por separado, sin aprobación de apuestas ni garantía de reunir la muestra mínima.

## Tenis: nueva auditoría y pronósticos con evidencia (19-oct-2026 UTC)
- [x] Reauditar integridad, pruebas, modelos y registros previos; no reinterpretar resultados futuros inexistentes como aprobados.
- [x] Buscar evidencia específica de Palm Hills 2025 y documentar la conclusión sin inventar campus u horas. Campus no acreditado: tres exclusiones espaciales explícitas, no bloqueo general.
- [x] Actualizar calendario API-Tennis y archivar programas oficiales actuales; resolver identidades con nombres completos contrastados. Cuatro PDF revisados visualmente; ambigüedades excluidas.
- [x] Emitir pronósticos de investigación para encuentros futuros acreditables, con datos/modelos sellados y bloqueo explícito de apuestas, conservando el protocolo financiero congelado. Ocho ATP; 20 parejas revisadas, 12 exclusiones.
- [x] Entregar informe único con cobertura, probabilidades y requisitos reales por variante; ejecutar las comprobaciones finales. 246 pruebas específicas, 1.315 generales; docs/tenis_auditoria_pronosticos_20261019.md.
- [x] (cerrada 25-oct: corregido en el motor v7 (alias de identidad)) Corregir en una nueva versión los puentes de identidad acreditados: 50 nombres WTA y uno ATP tienen varios IDs en el modelo congelado. No escoger automáticamente ni fusionar por similitud.

## Tenis: integración completa de familias de mercados (19-oct-2026)
- [x] Añadir una ampliación versionada sin cambiar los módulos y artefactos del estudio financiero congelado. Ocho módulos nuevos;37 anteriores/12 artefactos conservados.
- [x] Unificar contratos, probabilidades win/push/loss y cuotas justas para ganador, sets, juegos, hándicaps, marcador por sets y tiebreak, incluidas líneas por set. Diez familias/624 filas ilustrativas.
- [x] Conectar las claves reales documentadas de The Odds API; conservar explícitos los mercados que el proveedor no ofrezca y probar una captura acotada. Trece claves implementadas, siete observadas; seis créditos de prueba inicial y500 por cada clave suministrada después.
- [x] Implementar comparación de líneas y liquidación por contrato, con retiros y reglas desconocidas visibles.
- [x] Entregar un archivo utilizable de mercados, pruebas y estado verificable de integración, calibración y evidencia financiera. 294 pruebas; evaluación exploratoria3.498 encuentros/56.804 probabilidades. No hay rentabilidad demostrada.
- [x] Corregir la identificación de la segunda clave, que coincide con la cuenta compartida; consolidar500 créditos en el registro central y añadir detección preventiva. Primeros informes conservados con corrección explícita, sin ocultar el error.
- [ ] Resolver cobertura externa ausente, calibración completa, identidades/calendarios conflictivos y muestra financiera prospectiva antes de aprobar apuestas.

## Tenis: auditoría de acreditación financiera (19-oct-2026)
- [x] Ejecutar el evaluador congelado y auditar todos los registros originales, cuotas, órdenes, cierres y resultados sin convertir descargas repetidas en apuestas.
- [x] Añadir un control independiente de evidencia y un procedimiento reproducible que distinga preparación, prueba simulada y ejecución real; preservar candidatos y periodos congelados.
- [x] Probar rechazos por cronología, duplicación, evidencia ausente y costes; entregar informe con cobertura y pendientes acreditables, sin declarar beneficios futuros.

## Tenis: acreditación de calidad predictiva (19-oct-2026)
- [x] Auditar versiones y excluir identidades ambiguas sin fusionarlas por nombre; conservar los modelos congelados.
- [x] Ejecutar comparación común de seis variantes y evaluación por mercado, con incertidumbre por bloques, calibración, cobertura y bandas de confianza.
- [x] Entregar protocolo predictivo futuro, registro de pronósticos verificables y compuertas que impidan acreditar datos retrospectivos como confirmatorios.
- [x] Probar controles temporales, identidad, orientación, duplicados y confianza; entregar resultados reales y requisitos que dependan de encuentros futuros.

- [x] (cerrada 25-oct: corregido en el motor v7 (alias de identidad)) Recuperar cobertura mediante puentes de identidad acreditados y una nueva versión reentrenada; reunir resultados confirmatorios futuros y validar los otros mercados en sus propios protocolos.

- [x] Sellado externo del nuevo protocolo predictivo, autorizado explícitamente por el usuario: DigiCert19-oct16:54:10UTC, firma/nonce/digest y prueba negativa verificados. El estado pendiente del sello queda resuelto, sin cambiar los criterios de calidad.

## Tenis: continuidad autónoma autorizada (19-oct-2026)
- [x] Preparar capturador compartido con intervalo4h, máximo12consultasAPI-Tennis/día y bloqueo temporal ante401/403/429, sin consumir cuotas.
- [x] Conectar revisiones de programas oficiales a la emisión sin cuotas y al evaluador congelado; ejecutar una pasada real y conservar exclusiones/resultados no acreditables.
- [x] Probar idempotencia, concurrencia, presupuestos y evidencia; registrar seguimiento recurrente en este chat, sin avisos repetidos de estado idéntico.
- [x] Entregar operación y automatización verificadas, conservando protocolos sellados y trabajos ajenos.

### Tenis: validación prospectiva de los diez mercados (19-oct-2026)
- [x] Añadir protocolo independiente e inmutable con líneas/periodos fijos, candidato Markov coherente y evaluación por contrato/circuito/formato; conservar calidad_v3 sellada.
- [x] Probar cronología, integridad, pushes, sets no disputados, marcador multiclase, retiros y cobertura; emitir nuevos registros antes de los partidos admisibles:18partidos/990tareas/110grupos,0rechazos,367pruebas del motor entregado.
- [x] Integrar la ampliación en la continuidad existente, entregar informe y comprobar las suites sin gastar créditos de cuotas; automatización verificadaACTIVA,25pruebas específicas nuevas.
- [ ] Completar la muestra futura por contrato y revisión independiente: cero resultados iniciales, no acreditar calidad/rentabilidad anticipadamente. No es una tarea que se cierre con pruebas de software.

### Tenis: cerrar la incorporación de resultados y explicar evidencia disponible (19-oct)
- [x] Automatizar el cruce de resultados archivados con los eventos realmente pronosticados, conservando evidencia, pendientes y conflictos; no sustituir tiempos físicos por horas programadas. Entregado tennis_evidence_v1,29pruebas nuevas.
- [x] Generar evaluación histórica legible de las diez familias con contratos exactos y marcador multiclase; separar muestras ya inspeccionadas de confirmación futura:2788partidosterminados/39grupos,curvas/ECE/calibración/balance de clases.
- [x] Ejecutar reconciliación y auditoría financiera actualizadas, integrar en continuidad, probar y entregar diagnóstico fechado:18programadosfuturos/0terminalesdeellos,396pruebas motor y1315generales aprobadas.
- [ ] Incorporar resultados futuros verificables y cumplir muestra/periodo: primeros18aúnfuturos19-oct18:35UTC,primerinicioestimado22:15México. Financiero0órdenes: no acumula ROI automáticamente sin cuotas/órdenes/autorizaciones válidas. No cerrar esos requisitos con datos históricos o pruebas de software.

## Tenis: auditoría y motor v7 (2026-10-19)
- [x] Alias de una semana en 2026_wta.csv (47) y fusiones por fecha de nacimiento (5; 14 homónimos confirmados distintos): `tennis_identity_v2/v3`, datos `identity_bridge_v3_20261019`.
- [x] Sobredispersión por partido para todos los mercados (`tennis_core_v4`).
- [x] Ranking, puntos y edad saneada (`tennis_core_v5.features`).
- [x] Elo dinámico ordenado por ronda con inactividad/carga/experiencia (`tennis_dynamic_v2`) y apilador v7; protocolo `core_v7_prospective_20261019`, 17 pronósticos sellados.
- [x] Punto de entrada único `tennis_motor` + README; 413 pruebas.
- [ ] Cuotas de cierre históricas como entrada (pendiente de autorización del titular para descargar/gastar).
- [x] (cerrada 25-oct: automatización de Codex pausada el 20-oct) Apagar o actualizar la automatización de Codex que sigue usando el protocolo de diez mercados retirado.
- [ ] Evaluar v7 con resultados reales a medida que se jueguen (`python -m tennis_motor evaluate`).
- [x] Cuotas históricas Tennis-Data (descarga manual del titular): cruce 53.853 partidos; el mercado sin margen supera a v7; `--odds-a/--odds-b` en `tennis_motor`.
- [x] (cerrada 25-oct: decidido: cuotas de tenis de PropLine (24-oct)) Fuente de cuotas previas en vivo para pronósticos automáticos (decisión del titular: The Odds API u otra).
- [x] Cuotas previas en vivo: `tennis_odds_live_v1` (h2h, eu, 2 fotos/día, tope 400/mes, reserva para fútbol) + tarea programada + motor v8.
- [x] Motor en git: rama `tennis/motor-v8`, PR #46.
- [x] Entrada automática `tennis_intake_v1` en la tarea programada (cuotas -> calendario -> sello -> evaluación).
- [ ] Apagar la automatización de Codex «continuidad-de-validaci-n-predictiva-de-tenis» (solo el titular puede hacerlo desde Codex).
- [ ] Actualización semanal de datos (TennisMyLife -> identidades -> Elo dinámico) para que ranking y Elo no caduquen.
- [x] Actualización semanal de datos (`tennis_refresh_v1`, lunes 04:00), PR #49.
- [x] Pausar la automatización de Codex (archivo local).
- [x] Reentreno semanal del modelo de saque; validación con Match Charting Project. PR #50.
- [ ] Primeras cifras de acierto con resultados reales (`data/tennis/intake_v1/evaluation_latest.json`).
- [x] Motor de tenis en el VPS (imagen propia + cron de `qf`), PR #53/#54; tareas de Windows desactivadas.
### NBA — pronósticos prospectivos v1.3 con lesiones, 2026-10-21
- [x] Forecast v1.3 con reporte oficial de lesiones (≥60 min), cohorte sellada por fecha, ajuste único anclado por hash.
- [x] Ciclo de resultados (recibo oficial de nba.com, final, reintento) y marcador Brier por mercado.
- [x] Página: sección v1.3 con versión, estado de disponibilidad y `actionable=false`; RUN071 intacto.
- [x] Ensayo local (11 partidos reales), navegador sin errores, 15 pruebas nuevas, plan de despliegue con vuelta atrás.
- [x] Desplegar (PR a `main`, arnés verde, confirmación del titular) y programar el productor diario; comprobar salida del servidor a nba.com/ak-static. (Hecho el 21-oct; hoy 1.4b, ver DEPLOYS.md.)
- [x] Preparar la comparación con Pinnacle (alias Clippers, snapshot del mismo día, brazo alineado, protocolo congelado, ensayo sintético de punta a punta). docs/nba_comparacion_pinnacle_20261101.md.
- [x] Desde el 1-nov: comprar 20 snapshots, revisar `load`, comprar el resto (3.250 créditos) y correr `nba.market_compare`; órdenes en el documento. (Comprado y comparado el 23-oct por decisión del titular.)
- [x] Captura del precio de Pinnacle al sellar cada cohorte (`nba.live_market`, offline, bloqueada antes del 1-nov) y comparación prospectiva con protocolo congelado. docs/nba_mercado_prospectivo_20261101.md.
- [x] Captura del precio en el servidor, opción A aprobada: código (`live_market`: clave del servidor, carpeta de precios aparte, libro 2/día y 70/mes con `halt`, `capture-pending` con fases sello y cierre; 24 pruebas), clave copiada a `live13/private/odds_key` sin leerla, imagen y envoltorio de cron preparados. NO desplegado. docs/nba_captura_precio_servidor_propuesta_20261022.md.
- [x] Paso de precios desplegado (22-oct 23:05 UTC, PR #77): imagen `nba-live13-price:20261022`, red `nba-price`, `price.sh` y cron cada 5 min; bloqueado en código hasta el 2026-11-01. Entrada en DEPLOYS.md con la vuelta atrás.
- [x] (cerrada 25-oct: cron de `price.sh` retirado; PropLine es la fuente fija de cuotas en vivo y ya trae Pinnacle, ver docs/nba_auditoria_20261025.md) 1-nov: comprobar el primer sellado con precio.

### NBA — tercera auditoría (motor, props, vivo, cierres y créditos), 2026-10-25
Detalle en docs/nba_auditoria_20261025.md; todo corregido y desplegado en la misma sesión.
- [x] Completar el despliegue 1.4b a medias (datos RUN071 + columnas, modelo `5314c9ef…`, imagen `20261025b`) tras ensayo con la hora real.
- [x] Productor con 1 GB (1.4b pica ~573 MB; el límite era 512 MB).
- [x] Panel: un salto movido más tarde ya no deja el resultado en `validation_hold` (Rockets–Spurs, 23-oct).
- [x] PropLine: reintento sin periodos cuando la petición principal da 5xx (hándicap/total al sellar), lotes saltados tras una principal vacía y marcadores de competiciones sin motor cada 6 h.
- [x] Retirar el cron de `price.sh` (The Odds API en vivo desde el 1-nov).

### NBA — mejoras de la auditoría del motor, 2026-10-21
Detalle y medidas en docs/nba_auditoria_motor_20261021.md.
- [x] v1.4 (protocolo congelado): puntos perdidos relativos a la forma. Hecho: no mejora equipo (falla la regla de decisión), mejora jugadores; vivo sigue en v1.3. docs/nba_multimarket_v14_20261021.md.
- [x] v1.4b: absoluto + relativo juntos y suelo de participación: sin mejora en equipo, el suelo empeora la participación. v1.3 se queda. docs/nba_multimarket_v14b_20261021.md.
- [x] Separar «Available»/«Out» por motivo G League: neutro en todos los mercados (v1.4).
- [ ] Backfill gratuito de reportes de lesiones cercanos a T-60 y tabla condicionada a horas antes del salto (hoy: un reporte/día, 13:30 o 17:30 ET).
- [x] Caché por partido en `multimarket_v13_live.completed()` (juegos finales y días cerrados, `--cache`) y fallo explícito ante un partido pasado en curso; un aplazado (estado 1) se registra en `completed_games.json`. Modelo reajustado en `nba_f6_live13_model_20261021b` con parámetros idénticos (solo cambia el hash del módulo).
- [x] Backfill T-60 (`nba.injury_t60`): 1.910 PDF (2023-24..2025-26) descargados, parseados y unidos; partidos con reporte a ≤1 h del corte de 2-4 % a 99,8-99,9 %. docs/nba_cache_completed_y_backfill_t60_20261021.md.
- [x] v1.5 (protocolo congelado): v1.3 con reportes T-60. Jugadores mejoran de forma significativa (Brier −0,0003 a −0,0022) y la participación pasa de 0,45-0,49 a 0,31-0,38; equipo sin efecto probado (falla la regla de decisión), el vivo conserva sus reportes. docs/nba_multimarket_v15_20261021.md.
- [x] (cerrada 25-oct: duplicada de «Modelo único del marcador» (segunda auditoría NBA)) Ratings ataque/defensa ajustados por rival y ritmo, una sola distribución del marcador para ganador/puntos/total.
- [x] (cerrada 25-oct: duplicada de «Recalibración móvil… prior de pretemporada» (segunda auditoría NBA)) Prior de pretemporada para los primeros 15-20 partidos (oct-nov empeora el Brier del ganador ~0,01).
- [x] (cerrada 25-oct: duplicada de «Jugadores: distribución de puntos corregida» (segunda auditoría NBA)) Puntos de jugador: modelo 2P/3P/TL o dispersión ajustada; rangos desde la distribución calibrada (hoy el 80 % cubre 73 %).

### NBA — cuotas históricas de ganador compradas y comparación con Pinnacle, 2026-10-23
- [x] Compra de los 325 snapshots h2h de 2024-25 y 2025-26 (3.250 créditos) por instrucción del titular, antes del bloqueo del 1-nov; cobertura 98,8 % y 99,8 %.
- [x] Comparación congelada contra Pinnacle sin margen: el modelo no supera al mercado (Brier +0,0040 y +0,0057; peso de información c = 0,25 y 0,09, con IC que incluye 0). Veredicto: sin evidencia de información añadida. docs/nba_comparacion_pinnacle_resultado_20261023.md.
- [x] Arreglo: la API exige la fecha con sufijo Z (HTTP 422 con +00:00), en `odds_history.api_time`, con prueba.
- [x] (cerrada 25-oct: duplicada de «Desde el 1-nov: comprar 20 snapshots…» (3.250 créditos)) Comprar el mercado `totals` (≈3.250 créditos) tras la renovación del 1-nov para comparar el total del partido; puntos de equipo y jugadores solo de forma prospectiva.
- [x] (cerrada 25-oct: las cuotas de fútbol en vivo salen de PropLine desde el 23-oct) Fútbol queda con 294 créditos (≈1 día) hasta el reset del 1-nov: decisión del titular (opción 3); revisar la captura en vivo de fútbol.
- [x] (cerrada 25-oct: duplicada de la siguiente (paquete de The Odds API para props)) Props de jugador retrospectivos: viables con un mes del plan 5M de The Odds API ($119; ≈345.000 créditos) o, de forma barata, 100 partidos × 2 mercados (2.000 créditos); falta el módulo de comparación y su protocolo congelado. docs/nba_props_jugadores_viabilidad_20261023.md.
- [ ] Paquete de The Odds API para el retrospectivo de props (decisión del titular): recomendado un mes del plan 5M ($119) desde el 1-nov y hacer el escenario E (~249.000 créditos: 4 mercados × 2 temporadas × 2 snapshots + team_totals + totals/spreads de Pinnacle); antes, piloto de 2.000 créditos. docs/nba_props_sonda_y_paquete_20261023.md.

### NBA — segunda auditoría del motor, 2026-10-23
Enfoque del titular: probabilidad estadística calibrada frente al resultado real, no ganar a las cuotas. Detalle en docs/nba_auditoria_motor_20261023.md.
- [x] Auditoría del vivo, de v1.4-v1.5 y del piloto PropLine (0 créditos, servidor sin tocar).
- [x] Errores 1-6 del productor corregidos en `nba/productor-correcciones` (sellado por partido 65-90 min antes del salto, horas reales, caché, control de bloqueo, filas de jugador de 2026-27); modelo reajustado con parámetros idénticos. docs/nba_productor_correcciones_20261023.md.
- [x] (cerrada 25-oct: duplicada de «Desplegar (PR a main…) y programar el productor diario») Desplegar el productor corregido (PR a `main`, confirmación del titular; runbook y vuelta atrás en el documento).
- [ ] Decidir antes del 1-nov si se retira la captura de precios `nba-live13-price` (desplegada el 22-oct; con varias cohortes por día su libro de 2 peticiones/día rechazará la mayoría).
- [x] Play-in y playoffs (004/005/006) en el productor, resultados y página.
- [x] Reloj de `tests/test_paper_bundle.py` fijado (`paper_bundle.DEADLINE_UTC`, mismo valor).
- [x] Mercados de jugador en vivo: puntos, rebotes y asistencias a la línea de PropLine (moda de ≥2 casas), condicionados a jugar, modelo de jugador v1.3 con recalibración en rejilla de umbrales (mejor Brier fuera de muestra en los tres). docs/nba_productor_correcciones_20261023.md.
- [x] (cerrada 25-oct: duplicada de «Desplegar (PR a main…) y programar el productor diario») Desplegar productor y panel 1.3.1 (montaje `readonly` del volumen de PropLine, caché, modelo `…20261023`); runbook en el documento.
- [x] PropLine: cierres y liquidaciones diarios de NBA/tenis/fútbol en el recolector (PR #96, desplegado el 24-oct 13:51 UTC por otra sesión). Pendiente: PR, despliegue con anotación en DEPLOYS.md y un lector para los motores.
- [x] Recalibración móvil de total y puntos de equipo y prior de arranque: protocolo congelado `nba_live15`, ningún candidato entra (el modelo ya está calibrado en sus líneas en 2025-26; recalibrar con la temporada anterior empeora). docs/nba_live15_recalibracion_20261026.md.
- [x] Jugadores sin línea de PropLine (o sin archivo reciente): umbral estadístico para la rotación (L1, productor 1.5.0); arregla la cohorte del 25-oct 19:30 ET sellada sin jugadores y las pérdidas que nunca se sellaban.
- [x] `nba_api` por proxy (ZenRows, tope 450 créditos, gasto 106): 86 de los 95 partidos regulares sin conteos extendidos recuperados y validados; rotaciones 1 de 9 (el resto da 422). docs/nba_api_proxy_recuperacion_20261026.md.
- [ ] Fusionar los 86 partidos recuperados (`.local/normalized/nba_stats_proxy_recovery_20261026`) en el conjunto extendido en el próximo reajuste con protocolo congelado; decidir el caso `0:00` con tiros libres (0022100151).
- [ ] Prior de pretemporada por plantilla (traspasos y novatos por minutos esperados): el prior estadístico de `nba_live15` no mostró evidencia.
- [ ] Modelo único del marcador (posesiones × eficiencia, ajuste por rival y ritmo): ganador, margen, total y puntos de equipo coherentes y a varios umbrales; medias partes.
- [ ] Jugadores: distribución de puntos corregida (2P/3P/TL o dispersión ajustada) y rangos recalibrados con su cobertura publicada.

## PropLine: capturas posteriores al partido (24-oct-2026)
- [x] Recolector (sobre la liquidación del PR #96): box score `/stats` de NBA y fútbol al final de la cola de liquidación; lesiones NBA cada hora; lectores sin red `read_closing`, `read_results`, `read_stats` + `team_stats`, `read_injuries`.
- [x] Desplegar el recolector nuevo: release `5a9cde0` activa desde el 24-oct 14:18 UTC (DEPLOYS.md).
- [x] Verificada la release `5a9cde0` con la clave nueva (pasadas 15:07-17:07 UTC); `team_stats` corregido y desplegado en `fc20390` (DEPLOYS.md).
- [x] (cerrada 25-oct: duplicada de «Cargar los cierres de PropLine a odds_snapshots») Puerta CLV de fútbol con el cierre de `read_closing` (fecha de corte).
- [x] (cerrada 25-oct: cubierta: córners y tarjetas llegan de SofaScore y del completado de FotMob) Liquidar córners y tarjetas con `team_stats`.
- [ ] Decidir si las lesiones de ESPN entran en NBA como segunda señal (nuevo protocolo, no el sellado 1.3.1).

## PropLine: cobertura de mercados (24-oct-2026)
- [x] Medir en el archivo horario qué mercados trae PropLine por deporte y liga, con y sin Pinnacle. docs/propline_cobertura_20261024.md.
- [x] Goles por equipo: sí está, en `totals` con `team`, con Pinnacle; el ingestor ya lo separa.
- [ ] Remedir props NBA el día del partido (primer sellado 1.3.1) y Champions/Europa League en semana de copa.
- [x] Leer toda la referencia de PropLine (`llms-full.txt`) y listar las funciones útiles por deporte. docs/propline_funciones_utiles_20261024.md.
- [x] Añadir al recolector `/odds/closing` (cierre real) para fútbol y NBA: lo hizo el PR #96 (también tenis).
- [x] Emparejar props NBA por `player_id`: ya lo hacía `apps/nba/src/nba/prop_lines.py`. En tenis PropLine no da `player_id`.
- [x] `/results` y `/odds/closing` están en Hobby (petición real del 24-oct, `redacted: false`).

## Bajas y once previo desde SofaScore (25-oct-2026)
Las fuentes de API-Football y FotMob quedaron fuera del cron el 25-oct; SofaScore (rl1987 `event_detail` con `includeLineups`) trae, para partidos futuros, el once previsto (`lineups.confirmed=false`, formación y 11 titulares) y las bajas (`missingPlayers`: tipo missing/doubtful, motivo, fecha de regreso). Medido el 25-oct en la Premier (3 partidos).
- [x] (cerrada 25-oct: hecho (PR #118, worker 117feb7)) db/087: `injuries.source`/`expected_return` y tabla `lineups_previstas` (once previsto y oficial con recepción real).
- [x] (cerrada 25-oct: hecho (PR #118, worker 117feb7)) Recolector: orden `lineups` (cron cada 10 min): captura «previa» una vez por partido entre T-30 h y T-65 min, y «oficial» entre T-65 y T-20 min hasta que `confirmed=true` (máx. 5 intentos).
- [x] (cerrada 25-oct: hecho (PR #118, worker 117feb7)) Cargador del worker `qf.ingest.sofascore_alineaciones`: bajas → `injuries`; once previsto → `lineups_previstas`; once confirmado → `lineups` (lo que lee `sello_tardio`).
- [x] (cerrada 25-oct: hecho (PR #118, worker 117feb7)) `availability()` solo compara contra historia de la misma fuente de ids (SofaScore ≠ API-Football): sin historia suficiente devuelve «insuficiente», no basura.
- [x] (cerrada 25-oct: hecho (PR #118, worker 117feb7); la historia de once SofaScore queda en «espera datos») Ensayo, respaldo, despliegue (worker + cron host) y entrada en DEPLOYS.md. Pendiente aparte: historia de once SofaScore para que `availability` funcione.

## App — auditoría de datos, pronósticos y ergonomía (2026-10-25)

- [x] Pick abierto con otro lado o línea que el análisis (Barcelona o empate frente a «12» del modelo) desaparecía de «Mercados del partido»: `partido_mercados.aplicar_acceso` lo añade como fila propia.
- [x] La fila de un pick abierto enseñaba la probabilidad del análisis (79 %) y el destacado la sellada (76 %): ahora ambas son la sellada.
- [x] Patas del Parley sin `selection`/`line` (siempre en español en la app) y con `canonical_name`: `parley_datos._pata_publica` las envía y usa el nombre visible.
- [x] Textos en español fijos en la app: etiqueta del pronóstico en Inicio, escalones del historial de la Escalera y patas del Parley pasan por `pickText`.
- [x] «Goles de equipo» decía «Marca X» con cualquier línea o lado (app y `alta_prob.texto`); tarjetas y córners por equipo traducidos.
- [x] Partido con el saque pasado y sin resultado: «Esperando resultado» (Inicio, cabecera y banner del pronóstico) en lugar de «Hora local»/«En juego» a las 3 h. Clave nueva en 6 idiomas.
- [x] Casas con nombre comercial (`bookName`: BetOnline, Bovada…), fecha del historial del Parley en el idioma del usuario, textos de 8 px a 10 px y aviso «sin destacado» con coma decimal.
- [x] API desplegada el 26-oct 00:53 UTC (`98bdfcc-app-8c57b05`, `main` `f227fd9`).
- [ ] Compilar y publicar el APK 1.0.0+4 (la app nueva trae los textos traducidos y «Esperando resultado").
