# Rediseño del motor de tenis — Fase 1: auditoría e inventario (4/5-nov-2026)

Estado: **Fase 1 terminada, pendiente de tu «Sí»**. Rama `tenis/rediseno-f1` (worktree `C:\Users\huye\Documents\qf-tenis-rediseno`, desde `origin/main` 0097b767). Nada commiteado, nada desplegado, ningún crédito de pago gastado, producción intacta (solo lecturas en el VPS). No se escribió código del motor nuevo: solo scripts de medición en `apps/tennis/ops/`.

Cada cifra sale de un script reproducible o de uno de los informes enlazados; lo que no se pudo medir figura como **NO MEDIDO**. Las cifras de los subagentes están marcadas con su fuente y, cuando las comprobé yo, con **[verificado]**.

Documentos de esta fase:
- Inventario de datos: [tenis_auditoria_inventario_datos_20261104.md](tenis_auditoria_inventario_datos_20261104.md)
- Inventario de cuotas: [tenis_auditoria_inventario_cuotas_20261104.md](tenis_auditoria_inventario_cuotas_20261104.md)
- Literatura (76 estudios): [tenis_literatura_20261104.md](tenis_literatura_20261104.md)
- Tablas CSV: `docs/tenis_auditoria_tablas/`
- Scripts: `apps/tennis/ops/` (`linea_base_*.py`, `lit_*.py`, `inventario_*.py`)

## 1. Resumen ejecutivo

1. **El listón es el cierre del mercado y hoy está lejos.** En walk-forward 2019–2026 sobre Tennis-Data, un Elo propio queda **+0,036 a +0,039 de log-loss peor** que el cierre de Pinnacle (IC95 excluye 0) y el candidato Markov del motor actual **+0,06 (ATP) y +0,09 (WTA) peor**. La literatura (A01, T27, T10) muestra el mismo orden de magnitud y que ningún modelo con validación limpia bate al cierre. Objetivo realista: probabilidad **calibrada y verificable**, no ventaja.
2. **El motor actual es ineficiente en lo que importa.** El Markov puro por saque/resto pierde frente a Elo y está sobreconfiado (pendiente de calibración 0,43–0,54 en 2025). El motor en producción **recentra el ganador al precio del mercado**, así que su «ganador» empata con el mercado de forma circular (log-loss 0,6529 frente a 0,6531, n=145): no es evidencia de habilidad propia.
3. **Hallazgo nuevo de datos: Pinnacle desaparece de Tennis-Data desde febrero de 2026** (0 % de cobertura mensual; Bet365 y la media de casas siguen en ≥98 %). La referencia de cierre de 2026 tiene que ser Bet365/media; la brecha medida contra Pinnacle en 2026 tiene n=63 (ATP) y n=95 (WTA).
4. **Solo el ganador tiene referencia de mercado con historia.** Hándicaps, totales, sets, 1.er set, tiebreak, aces y break no tienen cierre histórico verificable en ninguna fuente (PropLine empezó el 24-oct-2026). Los demás mercados se pueden evaluar contra **resultados** (log-loss, Brier, RPS, calibración), no contra el mercado.
5. **Datos reales disponibles**: TennisMyLife 1967–2026 (492.251 partidos; 249.938 con estadísticas de saque aptas), SofaScore local 2022-12→2026-11 (21.974 partidos ATP/WTA, 20.816 con punto a punto), Match Charting Project (~11.800 partidos), Tennis-Data con cuotas del ganador. **No hay** serie semanal de rankings, hora de partido en TML, ni Challenger/ITF en SofaScore.
6. **Fugas a vigilar** (§4): ranking «de hoy» en SofaScore, `firstToServe`, duración y puntos en vivo, `h2h`/`team_streaks` capturados después, cuotas de Tennis-Data posiblemente de apertura y no de cierre.
7. **Antes de diseñar** necesito 10 decisiones tuyas (§9).

## 2. Cómo se hizo (delegación y límites)

- Inventarios 1.1 y 1.2: dos subagentes haiku (esfuerzo medium), solo lectura local y VPS.
- Literatura 1.5: método map-reduce que ordenaste. Limpieza local de los 76 PDF a texto (6,44 M → 4,86 M de caracteres, −25 %); Paso A con 16 agentes haiku (esfuerzo low, un JSON por estudio, 74/74 validados); Paso B con opus (esfuerzo max) que verificó 28 cifras contra el texto y escribió la síntesis. Dos PDF (A25, A27) son escaneados: se leyeron como imagen. La tesis B03 estaba leída parcialmente: se completó con un agente aparte.
- Mi parte (1.3 y 1.4): JSON de ejemplo, trampas y línea base walk-forward con scripts propios.
- Un intento anterior de leer la literatura con 7 agentes opus se cortó por límite de uso; sus fichas parciales se usaron solo como contraste.
- Entorno: el shell solo deja escribir a Python en la carpeta principal del repo; las salidas pesadas están en `data/tennis/rediseno_20261104/` y las tablas pequeñas se copiaron al worktree. No es un fallo del código.
- **No se ejecutó** `./scripts/test_local_windows.ps1 -Suite all`: la fase solo añade scripts de medición y documentos, y no toca código del producto. Queda pendiente antes del primer commit.

## 3. Inventario: qué hay, dónde y con qué calidad

Detalle y comandos en los informes enlazados. Resumen:

| Fuente | Dónde | Qué trae | Calidad / límite |
|---|---|---|---|
| TennisMyLife (TML) | local `full_20261016` y VPS `weekly/*` | ATP/WTA/Challenger/quali 1967→2026; 492.251 partidos canónicos (ATP 394.592, WTA 97.659); 249.938 elegibles; ranking y puntos de **ambos** jugadores **[verificado]** (2025: ganador 99,7 %, perdedor 98,2 % rellenos) | `tourney_date` = inicio de semana, 0 filas con hora verificada; estadísticas del propio partido son posteriores; el ranking se presume «del torneo», no verificado |
| TML en el VPS | `~/quantfut-tenis/data/weekly/20261102` | 2026.csv con 2.658 líneas frente a 2.482 locales; 2024.csv difiere por hash | El VPS es más reciente que el local |
| SofaScore local | `SOFASCORE/data/v3` (descarga en curso) | 21.974 partidos de tenis, solo ATP (11.186) y WTA (10.788), 2022-12-30→2026-11-03; mejor de 3: 19.881, de 5: 2.032; punto a punto y estadísticas en 20.816 | Sin Challenger/ITF ni dobles; captura de 2026-11 (no PIT); 459 partidos con ronda vacía |
| SofaScore en el VPS | `~/sofascore-scraper` | 10.748 eventos, 100 % fútbol, **0 tenis** | Todo el tenis de SofaScore vive solo en local |
| Match Charting Project | `full_20261016/mcp` | ~11.800 partidos con punto a punto (7.566 ATP, 4.264 WTA) | Sesgado a partidos destacados; CC BY-NC-SA, uso sin lucro con atribución |
| Tennis-Data | `tennis_data_manual` (47 xls) | 119.456 partidos 2000→2026 con cuotas del ganador (Pinnacle, Bet365, Max, Avg) y ranking | Sin hora; duda apertura/cierre; **sin Pinnacle desde feb-2026** **[verificado]** |
| API-Tennis | VPS (147 carpetas, 4.747 observaciones) | Fixtures, estados y resultados; sin cuotas | Solo ATP/WTA principal; copia local desfasada (113 observaciones) |
| Motor sellado | VPS `intake_v1/ledger.sqlite` | 350 pronósticos sellados (20-oct→4-nov) con `sealed_at` y hash | Única fuente con punto en el tiempo real |
| Postgres del VPS | `quantfut` | **Ninguna tabla de tenis** (137 tablas, todas fútbol) | El tenis vive en archivos y SQLite |

**Cobertura** (TML canónico): mejor de 3 449.335 / mejor de 5 42.916; superficie Hard 222.518, Clay 194.048, Grass 41.812, Carpet 33.873; torneos de gira 297.133, Challenger 165.689, previas 29.429. Tablas por año, circuito, nivel, ronda y superficie en `docs/tenis_auditoria_tablas/canon_*.csv` y `sofascore_local_*.csv`. Dobles: 0 en TML, SofaScore y MCP.

**Identidad.** Tras el puente v3 quedan **47 de 2.299** partidos WTA de 2026 con id alterno 3xxxxx (2,0 %; antes 89), 0 en 2022–2025; la semana 2026-06-08 pasó de 45 a 2. **La cifra del 19-oct («54 % de partidos WTA excluidos») no se reproduce** con el canónico: 2.146 es el número de elegibles WTA 2026, no de excluidos. La exclusión real del motor sigue **NO MEDIDA**. Además: 94 nombres normalizados con más de un id y 41 ids con más de un nombre; ids alternos ATP y homónimos: **NO MEDIDO**.

**Duplicados local/VPS**: ver §10 del informe de datos. Resumen: el VPS tiene TML más nuevo, API-Tennis completo y ledger; local tiene todo SofaScore de tenis. **No medido**: volumen Docker `quantfut_artifacts` (permiso denegado), base `nba-db`, `~/quantfut-public-sports`.

## 4. Cuotas: qué hay y qué sirve de referencia

Detalle en el informe de cuotas. Resumen:

- **Cierre verificable con instante (clase a): 0 fuentes.** Cierre declarado sin hora (clase b): Tennis-Data (Pinnacle en 96.865 partidos 2004–2026, Bet365 en 110.372; solo ganador) y PropLine producción (no medible por evento: volumen sin permiso). Resto: fotos (clase c).
- **Margen del ganador** (por contrato, sin mezclar líneas): Pinnacle en Tennis-Data mediana 2,46 % (p5 1,46 %, p95 3,20 %); Bet365 6,67 %; en el piloto de PropLine Pinnacle 4,74 % (n=76); The Odds API (WTA Ningbo) Pinnacle 2,93 % (n=29). Max y Avg son agregados, no casas.
- **PropLine** trae todos los mercados (ganador, hándicap y totales de juegos y sets, ganador de set, aces, tiebreaks…) pero solo desde el 24-oct; en el piloto solo 55 de 173 eventos (31,8 %) son ATP/WTA principal, el resto (ITF, Challenger, UTR) no tiene resultado en API-Tennis, y califica mal el tenis por juegos totales.
- **BetsAPI**: sin instante de captura en prematch; en la muestra la última actualización de la casa es posterior al inicio (mediana −0,41 h) y el 98 % de las filas de `odds` son posteriores al inicio.
- Ningún mercado distinto del ganador tiene cierre histórico verificable; resultado exacto: ninguna fuente.

## 5. Calidad y trampas (1.3)

### 5.1 JSON de ejemplo (SofaScore, Djokovic–Draper, Indian Wells R16, mejor de 3)

Todo lo siguiente sale del archivo `event-15624961.json`, comprobado con un script:

| Campo | Qué es | Veredicto para un modelo pre-partido |
|---|---|---|
| `winnerCode` (2), `homeScore/awayScore.periodN`, `periodNTieBreak` (5-7 en el 3.º) | Resultado y marcador por set | Resultado: sí. Es la etiqueta, nunca una variable |
| `tournament.uniqueTournament.groundType`, `tennisPoints` (1000), `roundInfo`, `defaultPeriodCount` (3 = sets máximos) | Superficie, nivel, ronda, formato | Sí (de la edición/fecha) |
| `homeTeamSeed` (3), `awayTeamSeed` (14) | Cabezas de serie del cuadro | Sí: son del sorteo (previos al partido) |
| `homeTeam.ranking` (11) y `playerTeamInfo.currentRanking` (11); `awayTeam.ranking` (157) y `currentRanking` (56) | Ranking | **No.** Las cabezas de serie (3 y 14) no coinciden con ninguno de los dos pares, y el archivo se descargó el 3-nov-2026: ambos son «de hoy» (foto de captura). Hay que usar un archivo semanal propio de rankings, con unión estrictamente `<=` a la fecha del partido (publicación del lunes) |
| `playerTeamInfo.prizeCurrent`, `userCount` | Premios del año y popularidad | **No** (de hoy) |
| `birthDateTimestamp`, `height`, `plays`, `turnedPro` | Atributos del jugador | Sí (edad calculada a la fecha del partido) |
| `firstToServe` (1) | Quién saca primero | **Prohibido** como predictor (sorteo 5 min antes); el simulador promedia 50/50 |
| `time.period1..3` (2079, 2868, 4391 s), `currentPeriodStartTimestamp`, `changes` | Duración por set y marcas de actualización | **Prohibido** para el propio partido (solo existen al terminar cada set). Sí como minutos de partidos **anteriores** (fatiga) |
| `homeScore.point` (5) / `awayScore.point` (6) | Residuo en vivo | **Prohibido**: no coincide con el tiebreak (5-7), es un valor en vivo caducado |
| `startTimestamp` (1773277200) | Inicio | 2026-03-12 01:00 UTC = 2026-03-11 18:00 hora de Indian Wells: la fecha UTC y la local difieren (usar el huso del torneo) |
| No trae | estadísticas de saque/resto, aces, dobles faltas, punto a punto, cuotas, tipo de entrada (Q, LL, WC) | El punto a punto y las estadísticas están en archivos aparte del mismo partido (ver §3) |

### 5.2 Reglas de oro y estado en nuestros datos

| Regla | Estado medido |
|---|---|
| Dato faltante ≠ 0 | TML: minutos nulos 260.099, `w_svpt` nulo 233.386 (de 492.251); se conservan como nulos |
| Retiradas, walkovers y abandonos aparte | TML: 22.724 no completados; Tennis-Data distingue `Retired`/`Walkover`; PropLine califica mal el tenis. El evaluador aplicará la regla de la casa (walkover sin acción; retirada con ≥1 set completado liquida el ganador) |
| Reconstruir qué se sabía antes (PIT) | TML parcial; SofaScore **no** (captura de nov-2026; `h2h` y `team_streaks` posteriores al partido); MCP no; Tennis-Data parcial; API-Tennis parcial (solo 2026); ledger de sellados **sí** |
| Ranking: join estrictamente `<=` | **No hay serie semanal**: solo el ranking por partido de TML y el de Tennis-Data. Fuente y frecuencia de publicación: NO MEDIDO |
| Falsos pre-partido (duración, aces en la misma ruta) | Confirmado en el ejemplo (`time.periodN`, `point`) |
| Qualy/Lucky Loser que entran horas antes | El JSON de SofaScore no marca el tipo de entrada; TML sí trae códigos de entrada, pero **no se midió** cómo se registra el cambio de última hora |
| Zonas horarias | Confirmado en el ejemplo; TML solo tiene semana |
| Homónimos / mismo partido en varias fuentes | 94 nombres con varios ids; solape por apellido TML–SofaScore ~60 % (aproximado, no es una clave de identidad) |
| Tennis-Data: ¿apertura o cierre? | **Abierto.** La literatura se contradice (A22 «opening», A17 y T27 «closing»); ninguna cita la nota de la fuente. Afecta directamente a la referencia (§9, decisión 1) |

## 6. Motor actual y línea base (1.4)

### 6.1 Qué es el motor actual (leído del código, sin heredar su diseño)

`tennis_motor` (v8): modelo binomial de saque/resto con superficie (MAP, priors gaussianos, ponderación por antigüedad de 365 días) → Markov por partido con sobredispersión → objetivo de ganador = mezcla Markov + Elo dinámico por rondas + ranking/puntos/edad + inactividad y carga → **recentrado al precio del mercado cuando existe** (de-vig proporcional) → todos los mercados salen de una distribución conjunta coherente. Entrena en el VPS con TML cada lunes. Sellado horario 1,5–2,5 h antes del inicio con la foto de PropLine más fresca; `market_board` guarda todas las líneas de las casas.

### 6.2 Línea base walk-forward (mis scripts, datos Tennis-Data 2019–2026)

Método: Elo propio actualizado por bloques de fecha (nunca se usa un partido de la misma fecha), logística de ranking y recalibración del Elo ajustadas **solo con temporadas anteriores**, presentación A/B aleatoria con semilla fija, referencia = probabilidad sin margen (proporcional) de Pinnacle, IC95 por bootstrap por partido (2.000 réplicas), orígenes combinados por inversa de la varianza. Se excluyen walkovers y retiradas sin set completado. Scripts: `linea_base_datos.py`, `linea_base_walkforward.py`; tablas `linea_base_*.csv`. Comprobación de cordura: el Brier del cierre de Pinnacle en ATP está entre 0,199 y 0,209 (no hay señal de fuga por debajo de ~0,18).

**Diferencia de log-loss frente al cierre de Pinnacle** (positivo = peor), combinada 2019–2026:

| Modelo | ATP (n≈16.700) | WTA (n≈15.400) |
|---|---|---|
| 50/50 | +0,105 [0,099; 0,111] | +0,102 [0,096; 0,108] |
| Ranking logístico | +0,044 [0,040; 0,049] | +0,046 [0,041; 0,050] |
| Elo | +0,039 [0,036; 0,043] | +0,036 [0,032; 0,040] |
| Elo + superficie | +0,036 [0,033; 0,040] | +0,038 [0,034; 0,041] |
| Elo recalibrado con temporadas previas | +0,038 [0,034; 0,041] | +0,036 [0,032; 0,039] |
| Bet365 sin margen (para referencia) | +0,001 [0,000; 0,001] | +0,001 [0,001; 0,002] |

- La recalibración logística con temporadas previas **no mejora de forma material** (0,001–0,002): coherente con la lección de NBA; no se arregla por una sola temporada.
- Ejemplo de calibración de 2025 (ATP, n≈2.470): cierre de Pinnacle Brier 0,2087 / log-loss 0,6027, pendiente 0,96 [0,87; 1,06]; Elo recalibrado 0,2211 / 0,6314, pendiente 0,91 [0,83; 1,03]. WTA 2025: 0,2064 / 0,5985 frente a 0,2197 / 0,6290.
- **Pinnacle no existe en Tennis-Data desde feb-2026**, así que 2026 pesa casi nada en esta tabla; ver §6.3 para 2026 contra la media de casas.

**Dónde falla** el Elo recalibrado frente al cierre (`linea_base_segmentos.csv`, segmentos con n≥200, diferencia de log-loss):
- **Favoritos fuertes** (probabilidad del favorito 0,8–1,0): ATP +0,057 [0,049; 0,066], WTA +0,070 [0,060; 0,081]; en 0,5–0,6 solo +0,031 y +0,026.
- **Jugadores con <20 partidos previos**: ATP +0,056 [0,047; 0,065], WTA +0,066 [0,056; 0,075], frente a +0,033 y +0,028 con ≥20.
- **Primera ronda** (ATP +0,046, WTA +0,048), **tierra** (ATP +0,047, WTA +0,043), **Grand Slam masculino** (+0,046) y **mejor de 5** (+0,047) son los peores segmentos.
- Retiradas: en WTA el modelo no pierde de forma distinguible (−0,022 [−0,050; 0,005], n=403); en ATP +0,042.

### 6.3 El candidato Markov del motor actual frente al mercado (2025–2026)

Se midieron las predicciones congeladas que el motor ya guardó (`heldout_predictions.parquet`, origen 1-ene de cada año, embargo de 35 días), cruzadas con Tennis-Data por apellido, inicial y fecha ±16 días: tasa de cruce ATP 2025 93,0 %, ATP 2026 86,8 %, WTA 2025 93,0 %, WTA 2026 95,1 % (ambiguos y sin cruce excluidos; no es una clave de identidad). Script `linea_base_motor_actual.py`.

Diferencia de log-loss frente a la **media de casas** (única referencia con cobertura completa en 2026; n=4.488 ATP y 4.287 WTA):

| Modelo | ATP | WTA |
|---|---|---|
| Elo propio recalibrado | +0,031 [0,025; 0,038] | +0,034 [0,028; 0,040] |
| Elo del motor actual | +0,039 [0,030; 0,047] | +0,050 [0,041; 0,059] |
| Elo+superficie del motor actual | +0,035 [0,027; 0,042] | +0,047 [0,038; 0,055] |
| **Markov MAP del motor actual** | **+0,061 [0,049; 0,072]** | **+0,095 [0,080; 0,110]** |

Frente a Pinnacle el orden es el mismo (Markov +0,064 ATP, +0,090 WTA), pero con casi todo el peso en 2025 (n≈2.300) porque Pinnacle falta en 2026. El Markov puro está además sobreconfiado: pendiente de calibración 0,54 (ATP 2025, n=2.266) y 0,43 (WTA 2025, n=2.149).

### 6.4 El motor en producción (prospectivo, leído del VPS, `evaluation_latest.json` del 5-nov 02:25 UTC)

350 sellados, 338 con resultado. Ganador ATP n=194: log-loss 0,6444, Brier 0,2273, ECE 0,084, acierto 62,4 %; WTA n=144: 0,6154, 0,2130, ECE 0,082, acierto 68,8 %. Con el ganador recentrado al mercado, motor 0,6529 frente a mercado 0,6531 (n=145); en las filas con cierre, 0,6594 frente a 0,6573 (n=142). **Esta cercanía es circular** (el motor usa el precio del mercado como objetivo). Mercados derivados (log-loss motor / mercado en las mismas líneas): totales de juegos 0,5779 / 0,5811 (n=2.634), hándicap de juegos 0,6222 / 0,6181 (n=1.789), totales del set 0,4980 / 0,4909, ganador del set 0,6693 / 0,6691. Son diferencias de ±0,01 con líneas correlacionadas dentro de cada partido: medida, no acreditación.

### 6.5 Qué falla y por qué es ineficiente

1. El núcleo por puntos pierde frente a Elo y está sobreconfiado (§6.3): la fuerza relativa debe venir calibrada con resultados, no del Markov crudo.
2. El ganador de producción **no es independiente del mercado**: no se puede medir su calidad propia mientras use el precio como objetivo.
3. La evaluación retrospectiva solo existe para 2025 y 2026 (el código rechaza años anteriores): no hay múltiples orígenes.
4. El único backtest con cuotas usa el 45,1 % de las filas de Tennis-Data (`odds_matched`, criterio de emparejamiento no documentado).
5. Conviven 21 paquetes en `apps/tennis` (`tennis_core_v4…v8`, `tennis_dynamic_v1/v2`, `tennis_identity_v2/v3`…); el motor vigente depende de protocolos congelados de versiones anteriores.
6. Retiradas, ids alternos de jugadores y semana de torneo usada como fecha: ver §3 y §5.
7. Reentrena cada lunes dentro del contenedor del VPS (refresh semanal). El rediseño debe entrenar solo en local y que el VPS infiera con artefactos versionados.

## 7. Literatura (1.5): lo que cambia el diseño

Resumen de [tenis_literatura_20261104.md](tenis_literatura_20261104.md). Pesos de evidencia: alto 10, medio 17, bajo 17, descartar 32 (in-play, fuga, circulares o sin partición temporal) de 76 estudios. Opus verificó 28 cifras contra el texto (Anexo 1 del documento); las demás cifras que cito abajo vienen de ese documento y **no las re-verifiqué una a una** en esta consolidación.

1. **El cierre del mercado es el listón.** En T27 (2022–25, 12.052 partidos) Pinnacle-Shin da Brier 0,198 frente a 0,214 del WElo; añadir el modelo a Pinnacle no mejora (p ≥ 0,47). En T30 la supuesta ineficiencia era una cuota errónea de Tennis-Data.
2. **ML sobre un buen rating gana como mucho 0,005–0,008 de log-loss** (T10: 0,6234 → 0,6154), casi todo por recalibración.
3. **Fórmulas cerradas punto→juego→set→partido verificadas** (Newton–Keller, juego, tiebreak a 7 y a 10, mejor de 3 y de 5; K = √1,4 ≈ 1,183 para pasar de 3 a 5 sets). Monte Carlo sobra dentro del partido; pero un modelo solo por puntos pierde frente a Elo (A01, A06, A12).
4. **La violación de IID es pequeña** (A02: ±0,3–0,7 pp por punto; −4,6/−4,8 pp solo en el punto más importante; fuera de muestra el modelo no-iid no mejora al iid). Ningún estudio demuestra un «clutch» persistente por jugador; los de momentum son circulares o in-play. IID infraestima el total de juegos en +0,79 (ATP) y +0,89 (WTA) en muestra (T31); no hay cifra para hándicaps. Para Fase 2: opción por defecto IID con ese margen de error conocido y recalibración de totales.
5. **Superficie real pero con poco peso sobre un rating global** (T17, T27); la evidencia apoya una desviación jerárquica con encogimiento.
6. **Los ratings salen sobreconfiados y los modelos por punto infraconfiados:** hace falta recalibrar fuera de muestra.
7. **Fatiga:** solo hay efecto en el extremo (A16: 5 sets frente a 3, −4,9 pp); los días de descanso no son significativos y nadie validó minutos acumulados intratorneo. La penalización por fatiga que pediste debe tratarse como hipótesis a medir, no como efecto establecido.
8. **Primer sacador:** no cambia ganador ni sets, sí el marcador exacto y los totales (hasta 0,4 juegos): confirma promediar 50/50 sin usarlo como predictor.
9. **Retiradas:** 1–4 % de los partidos; cada casa las liquida con su regla (A29).
10. **Sin evidencia en el corpus** para: sesgo favorito–no favorito medido, comparación de métodos de de-vig, semana previa a Grand Slam, Copa Davis/BJK/JJOO y altitud.

**Contradicciones más serias:** ¿Tennis-Data es apertura o cierre? (A22 frente a A17/T27; no se resuelve con el corpus); ML igual al mercado (T13, S02) frente a no (T27, T30, A01): sobreviven T27 y T30; momentum (T19) frente a A02: sobrevive A02. 24 preguntas abiertas para la Fase 2 en §F del documento de literatura.

Dos correcciones a los JSON del extractor barato que conviene recordar: la columna «replicable» subestimaba nuestros datos (TML sí trae estadísticas de saque en ~250 mil partidos; SofaScore trae punto a punto en 20.816), y varias fórmulas (T36, T27) venían mal extraídas.

## 8. Qué mercados son viables HOY

«Evaluable contra resultados» = log-loss, Brier, RPS y calibración con resultados reales. «Contra mercado» = hay referencia con historia suficiente.

| Mercado | Contra resultados | Contra mercado | Qué falta |
|---|---|---|---|
| Ganador | **Sí** (TML 1967–2026, SofaScore 2023–26) | **Sí**, clase (b): Tennis-Data (Pinnacle hasta ene-2026; Bet365/media después), 2004–2026, sin hora | Cierre con instante para confirmar que es cierre |
| 1.er set (ganador) | Sí | No (PropLine ~12 días, calificación defectuosa) | Historia de cuotas |
| Hándicap de sets, total de sets, resultado exacto en sets | Sí (marcador por set) | No | Historia de cuotas |
| Hándicap y totales de juegos | Sí (marcador por set y tiebreak) | No | Historia de cuotas; margen de error IID de +0,8–0,9 juegos |
| Tiebreak (sí/no, total) | Sí (7-6 en todos los partidos) | No | Historia de cuotas |
| Aces / dobles faltas | Parcial (~250 mil partidos ATP/WTA con estadísticas; no Challenger/quali) | No | Modelo de recuento validado (no hay en el corpus) e historia de cuotas |
| Break en el 1.er set | Parcial (SofaScore punto a punto 2023–26, ~20,8 mil partidos) | No | Más punto a punto e historia de cuotas |

Recomendación de alcance para la Fase 2 (a confirmar por ti): empezar por ganador, sets y juegos con compuertas contra resultados; aces, dobles faltas y break del 1.er set se evalúan pero **no se publican** sin evidencia de calibración, como pediste.

## 9. Decisiones que necesito de ti

1. **Referencia de mercado — RESUELTA por el titular (5-nov):** la fuente fija de cuotas es **PropLine** (decisión del 23-oct: recolector compartido horario, los motores leen el archivo, The Odds API solo para históricos ya autorizados). Tennis-Data queda únicamente como historia retrospectiva del ganador (clase b, sin hora, con las salvedades de §5.2 y sin Pinnacle desde feb-2026); no es fuente de cuotas del motor. La evaluación contra mercado de todos los mercados será prospectiva con PropLine.
2. **Base de entrenamiento.** El VPS tiene TML más reciente (snapshot del 2-nov) que el local (16-oct). ¿Autorizas traer ese snapshot al PC (copia de solo lectura) para entrenar siempre en local?
3. **Ranking semanal.** No existe serie histórica. ¿Autorizas buscar una fuente gratuita (publicación de los lunes) o prefieres usar el ranking por partido de TML con la salvedad de que su fecha no está verificada?
4. **Alcance de circuitos.** SofaScore y API-Tennis solo cubren ATP/WTA principal; Challenger/ITF solo están en TML (sin cuotas ni punto a punto). ¿El motor publica solo ATP/WTA principal y usa Challenger solo para ratings?
5. **Mercados de la beta.** ¿Confirmas ganador + sets + juegos (+ tiebreak y 1.er set) como primeros candidatos, evaluados contra resultados, y aces/dobles faltas/break en 1.er set solo evaluados?
6. **Motor actual.** Sigue sellando en el VPS (350 pronósticos). Propongo no tocarlo ni retirarlo durante el rediseño; sus sellados no se reescriben. ¿Confirmas?
7. **Semana previa a Grand Slam y Copa Davis/BJK/JJOO.** No hay evidencia en el corpus; propongo medirlo con nuestros datos en la Fase 2 y, hasta entonces, tratarlos como contextos marcados (sin excluirlos del todo). ¿De acuerdo?
8. **Presupuesto de pago.** Nada se ha gastado ni se necesita para la Fase 2. No hay manera de comprar cierres históricos de otros mercados: la historia de PropLine solo se acumula hacia adelante. ¿Mantengo el tope en cero hasta que lo apruebes?
9. **Identidad — aclarada por el titular (5-nov):** los partidos ATP y WTA del «54 % excluido» siguen descargándose. No es un bloqueo hoy: se vuelve a medir la exclusión real cuando termine la descarga y antes de entrenar; los alias se resuelven con fecha de nacimiento.
10. **Cierre administrativo de la Fase 1.** Falta correr `./scripts/test_local_windows.ps1 -Suite all` y hacer commit en `tenis/rediseno-f1`. ¿Lo hago ahora o lo dejamos para el primer sprint?

## 10. Riesgos abiertos

- La referencia de mercado puede ser apertura y no cierre (cambia la brecha, no el sentido).
- El único cierre con instante empieza el 24-oct-2026: la evaluación contra mercado de mercados distintos del ganador será prospectiva.
- La descarga de SofaScore local sigue en curso; las cifras son del 5-nov 03:06 UTC y cambiarán.
- Las copias SQLite del VPS contienen rutas Windows locales en `receipts.source_path`: parte de las observaciones se generaron o copiaron desde el PC (no cuantificado).
- Cifras de literatura reconstruidas o inciertas listadas en §E del documento de literatura: no citar sin volver al PDF.
- La lectura de los 76 estudios es completa salvo B03 (completada con un agente aparte) y A25/A27 (leídos como imagen).

## 11. Estado de las compuertas de la Fase 1

| Compuerta | Estado |
|---|---|
| Inventario local y VPS (solo lectura) | Hecho; huecos listados como NO MEDIDO |
| Inventario de cuotas con margen por contrato y clases a/b/c | Hecho |
| JSON de ejemplo y trampas | Hecho (§5) |
| Línea base walk-forward honesta, mismo protocolo que el nuevo | Hecha (§6): 2019–2026, bootstrap por partido, comprobación de cordura |
| Literatura leída completa | Hecha (76/76) con las reservas de §10 |
| Protocolo de arnés (`test_local_windows.ps1`) | **Pendiente** |
| Commit / PR | **Pendiente** (nada commiteado) |

¿Sí, pasar a la Fase 2 (plan técnico) una vez resueltas las decisiones de §9?
