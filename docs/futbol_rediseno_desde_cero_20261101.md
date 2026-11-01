# Rediseño de los motores de fútbol desde cero con `futbol.dato` (1-nov-2026)

Pedido del titular: rehacer el rediseño con la data nueva (tabla única `futbol.dato`), **sin fiarse de mediciones
anteriores**, leyendo completos los estudios que pasó en dos lotes y volviendo a hacer todas las pruebas. Este
documento sustituye a las conclusiones numéricas de `docs/serie_a_sofascore_rediseno_20261031.md` (que medía solo
Serie A con la data vieja); aquel se conserva como registro de lo leído.

**Nada se ha activado ni desplegado.** Todo se calculó en local sobre una exportación de solo lectura.

## 1. Datos y protocolo

- **Exportación** (`scripts/rediseno_futbol/exportar.sh`, solo lectura, 1-nov 11:22 UTC): `matches` de las 8 ligas del
  núcleo desde 14/15 (34.285 partidos) + Liga MX aparte; de `futbol.dato` tiros (xG, xGOT, situación, minuto),
  incidencias (goles, tarjetas, cambios con minuto), estadísticas de equipo por periodo, contexto (árbitro, asistencia,
  entrenadores, capacidad); cierres 1X2 de `odds_snapshots`; derbis y umbrales de sanción (db/098).
- **Ligas del núcleo:** Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira, Brasileirão (4 temporadas con mapa de tiros)
  y Premier, LaLiga (desde 24/25). xG por tiro sin penaltis disponible en el 22,6 % de los partidos (23/24 en adelante).
- **Mercado de referencia:** cierre de Pinnacle hasta el 14-ene-2026 y de bet365 después (margen 2,9 % frente a 5,7 %);
  Shin. 26/27 casi sin cierres en el archivo (475 partidos con mercado).
- **Walk-forward semanal:** en cada corte cada modelo ve solo partidos anteriores y predice la semana siguiente. Desde
  jul-2023 (calentamiento de calibradores); **selección = 24/25–25/26 (5.541 partidos con mercado)**, **reserva =
  26/27 (475)**, mirada solo al final.
- **Métricas:** log-loss principal; RPS, Brier; descomposición de Murphy (MCB descalibración / DSC resolución, PAV con
  empates agrupados, `eval/metrics.py`); Diebold-Mariano por semana (bloques). Todo modelo se compara sobre **las
  mismas filas**.
- **`check_leakage()`** avisa de 24.158 partidos con xG registrado más de 6 h después del saque (el histórico de
  SofaScore/FotMob es reconstrucción de oct-2026) y de saques repetidos (jornadas simultáneas; el walk-forward es por
  semana, así que no afecta). El xG histórico describe partidos pasados; su riesgo es de revisión, no de futuro.
- **Variantes probadas:** unas 27 sobre 1X2 y 7 sobre conteos. Con tantas comparaciones, un IC95 que roza el cero no es
  evidencia.

## 2. Resultados 1X2 (selección 24/25–25/26, n = 5.541)

| Modelo | Log-loss | RPS | Frente al mercado (Δlog, IC95) | Frente a A0-xG (Δlog, IC95) |
|---|---|---|---|---|
| **Mercado (Shin)** | **0,96392** | **0,19317** | — | −0,0164 [−0,0206, −0,0122] |
| LightGBM apilado + cuotas | 0,97704 | 0,19563 | +0,0131 [+0,0085, +0,0178] | −0,0034 [−0,0095, +0,0027] |
| **A0 score-driven con xG** | **0,98030** | 0,19793 | +0,0164 [+0,0122, +0,0206] | — |
| A1 (xG sin penaltis por tiro), calibrado | 0,98009 | 0,19783 | +0,0162 | ≈ 0 |
| A2 (xG por estado del partido), calibrado | 0,98033 | 0,19791 | +0,0164 | ≈ 0 |
| A0-xG + inflación diagonal | 0,98066 | 0,19814 | +0,0167 | +0,0004 [−0,0008, +0,0015] |
| Logit multinomial apilado | 0,98198 | 0,19807 | +0,0181 | +0,0015 [−0,0031, +0,0062] |
| Dixon-Coles de producción | 0,98276 | 0,19876 | +0,0188 [+0,0146, +0,0231] | +0,0021 [−0,0005, +0,0047] |
| DC + calibrador afín | 0,98303 | 0,19883 | +0,0191 | — (frente a DC: +0,0003, n.s.) |
| pi-ratings con xG | 0,98379 | 0,19921 | +0,0199 | +0,0035 [+0,0004, +0,0066] |
| A0 solo goles | 0,98494 | 0,19947 | +0,0210 | — |
| DC solo goles | 0,98689 | 0,20001 | +0,0230 | — (frente a DC: +0,0041 [+0,0022, +0,0061]) |
| LightGBM apilado sin acciones defensivas | 0,98890 | 0,19909 | +0,0250 | +0,0085 [+0,0035, +0,0134] |
| LightGBM apilado (bases + rasgos) | 0,99059 | 0,19947 | +0,0267 | +0,0102 [+0,0051, +0,0152] |
| LightGBM solo rasgos | 0,99343 | 0,20042 | +0,0295 | +0,0130 [+0,0072, +0,0188] |
| Climatología | 1,07134 | 0,22878 | +0,1074 | — |

Reserva 26/27 (n = 475): mercado 0,97656; DC 0,99135; A0-xG 0,99255; LightGBM apilado 1,00012. Ninguna diferencia
entre modelos es significativa en la reserva; el mercado sigue primero.

**Lo que esto dice:**
1. **El mercado gana con claridad** a todo modelo (≈ 0,016–0,030 de log-loss). La mezcla de Benter le asigna al modelo
   un peso de **0** en todas las semanas: el modelo no aporta nada que el cierre no tenga.
2. **El xG ayuda** de forma significativa (DC con xG frente a DC con goles: −0,0041). **A0 score-driven con xG** queda
   por delante de DC de producción (−0,0021) sin significancia (IC95 roza el cero), y en la reserva 26/27 no se
   confirma. A1 (xG por tiro sin penaltis) y A2 (estado del partido) no añaden nada sobre A0-xG.
3. **El calibrador afín y la inflación diagonal no mejoran**: la descalibración del empate ya es pequeña (MCB 0,0027).
4. **El apilado con árboles potenciados empeora** frente al mejor modelo único, incluso con 4 temporadas de
   entrenamiento; la regresión logística empata. Con las cuotas como entrada mejora a A0 pero sigue lejos del mercado
   solo. Coincide con Yeung et al. 2024 (añadir rasgos elaborados empeoró CatBoost: RPS 0,2416 frente a 0,2085).
5. **Quitar las acciones defensivas** (entradas + intercepciones + despejes) mejora el apilado en 0,0017, en la
   dirección que predice DEFCON (miden exposición, no calidad).

## 3. SHAP del apilado (auditoría)

Importancia media |SHAP| (escala log-odds) del último LightGBM apilado sobre 24/25–26/27: dominan las probabilidades
de A0-xG y de DC (0,24, 0,17, 0,17, 0,15); después el xG medio de cada equipo (0,08) y la posesión (0,06). El empate
apenas lo explica ningún rasgo con fuerza, y el árbol lo **descalibra** (MCB empate 0,0087 frente a 0,0027 de A0).
Los 5 peores partidos (p. ej. Barcelona–Las Palmas 24/25, visita ganadora con p = 0,025) se deben a los modelos base,
no a un rasgo concreto: no hay fuga visible. SHAP sirvió para **auditar**, y la auditoría dice que el árbol no aprende
nada que los modelos base no tengan.

## 4. Kelly fraccional como diagnóstico (no es el producto)

Kelly 0,25 contra el cierre real, una apuesta por partido al resultado de mayor ventaja, exposición semanal ≤ 50 %:

| Modelo | Selección (97 semanas): rentabilidad sobre lo apostado (IC95) | Capital final |
|---|---|---|
| A0-xG | −10,0 % [−15,3 %, −4,7 %] | 0,009 (ruina) |
| DC de producción | −9,9 % [−15,8 %, −4,1 %] | 0,007 (ruina) |
| LightGBM apilado + cuotas | −3,3 % [−7,7 %, +1,7 %] | 0,16 |
| Mercado sin margen | no apuesta nunca (no hay ventaja) | 1,00 |

En la reserva (10 semanas) los intervalos van de −25 % a +40 %: puro ruido. **Sin ventaja sobre el mercado, el tamaño
de la apuesta no crea rentabilidad**; Kelly fraccional solo frena la ruina. Es lo mismo que KellyBench (todos los
agentes pierden) y que el propio Vélez Jiménez (sus ganancias tienen p = 0,16–0,50).

## 5. Motor C (conteos), selección 24/25–25/26

| Mercado | Variante | Log-loss total | Δ frente a media de liga (t) | Resolución en la línea central |
|---|---|---|---|---|
| Córners | media de liga | 2,6449 | — | DSC 0,0016 (9,5) |
| Córners | equipos (concede/genera) | 2,6302 | −0,0147 (−5,7) | — |
| Córners | **Yip: + goles esperados, supremacía, dispersión variable** | **2,6203** | **−0,0246 (−14,9)** | DSC 0,0048 sobre Brier 0,2465 (≈ 2 %) |
| Amarillas | media de liga | 2,1578 | — | DSC 0,0103 (4,5) |
| Amarillas | equipos | 2,1351 | −0,0227 (−6,5) | — |
| Amarillas | + árbitro encogido | 2,1274 | −0,0304 (−7,0) | — |
| Amarillas | **Dawson: + derbi, igualdad q(1−q), supremacía, faltas** | **2,1192** | **−0,0386 (−9,0)** | DSC 0,0192 sobre Brier 0,2204 (≈ 9 %) |

Reserva 26/27: el orden se mantiene (córners −0,0207, t −2,9; amarillas −0,0560, t −7,3), pero en 26/27 hay **menos
amarillas** (3,75 reales frente a 3,97 previstas): la media de liga necesita reajuste dentro de la temporada.
Los córners tienen muy poca resolución en cualquier variante; las tarjetas, bastante más. Sin histórico de cuotas de
córners y tarjetas (PropLine solo desde el 23-oct), la comparación con el mercado es solo hacia delante.

## 6. Estudios leídos completos (1-nov) y lo que de verdad dicen

### Primer lote (10)
| Texto | Lo que se afirmaba | Lo que muestra el texto | Veredicto |
|---|---|---|---|
| Bunker, Yeung, Fujii 2024 (capítulo) | Los GBT superan al aprendizaje profundo | Revisión sin experimentos propios. Los GBT sobre pi-ratings son lo mejor **solo con datos de goles**; con estadísticas de partido «no está claro» y Random Forest a veces gana; las cuotas siguen siendo la referencia difícil de batir; recomienda log-loss | Probado: el apilado no gana aquí |
| Becerra-Patiño et al. 2026 (MDPI) | SHAP para explicar predicciones de partidos | Es **xG de fútbol para ciegos** con 164 tiros de un equipo; los árboles no se distinguen de los demás (DeLong p > 0,05); preliminar | SHAP adoptado como herramienta de auditoría |
| Gregori et al. 2026 (Frontiers) | Valida usar RF/XGBoost | Mapa descriptivo de 118 estudios, **sin metaanálisis**, casi todos con exactitud; el predominio de ensembles es de uso, no de superioridad | Solo contexto |
| BetsyScore 2026 | Guía práctica | Texto promocional sin datos; aconseja sobremuestrear empates (deforma probabilidades) | Fuera |
| Wang et al. 2025, HIGFormer | Mejora los empates | Acierta el **24,5 %** de empates, peor que MLP (37,7 %) y RNN (33,0 %); 389 partidos de una temporada, solo exactitud; exige red de pases | Fuera |
| Kim et al. 2025, DEFCON | Añadir despejes/intercepciones como fuerza defensiva | Las acciones defensivas con balón se correlacionan **negativamente** con el valor (−0,20; centrales −0,60): miden exposición. Exige tracking 25 Hz | Confirmado en sentido contrario: quitarlas mejora |
| Xenopoulos y Silva 2022 | Base para grafos | Fútbol americano y Counter-Strike, estados en vivo con tracking; no hay fútbol | Fuera |
| Pulis 2023 (tesis) | Respalda grandes ocasiones / pases clave | Valor de decisiones con tracking 360; contra puntos de la misma temporada Spearman 0,87 frente a 0,86 del xGD (20 equipos, sin prueba); no usa esas variables | Fuera |
| Lamberts 2026 (blog) | Mejor consumir xT de un proveedor | Blog sin revisión; necesita eventos Opta con coordenadas; no pronostica partidos | Fuera |
| Ide, Someya, Kawaguchi, Fujii 2026 | Límite del estado del arte | RL táctico con tracking (45 partidos J1); sus valores Q no se correlacionan con el xG (r ≤ 0,19) | Fuera |

### Segundo lote (7 + 1)
| Texto | Lo que se afirmaba | Lo que muestra el texto | Veredicto |
|---|---|---|---|
| Chen 2025 (ITM, congreso) | Poisson bivariante como entrada «incrementa radicalmente» la precisión | Autor de bachillerato; **no compara con y sin** la Poisson (solo importancia); solo exactitud (56 % frente a 50 % de bet365, usando las cuotas de bet365 como entrada); sin división temporal descrita; su Poisson no se ajusta por verosimilitud | Probado mejor aquí: el apilado empeora |
| Karlis y Ntzoufras 2003/2005 (JSS, leído el de 2005) | Inflación diagonal obligatoria si fallan los empates | En Serie A 91/92 infla el 1-1 (p = 0,09); BIC 1.763 frente a 1.767, **dentro de muestra, una temporada**; la τ de DC es un caso particular | Probado fuera de muestra: p ≈ 0,023, no mejora |
| Razali et al. (TabNet) | Supera a XGBoost | Texto original inaccesible (ResearchGate con bloqueo). Según Bunker y Yeung: TabNet RPS 0,1956, **peor** que CatBoost + pi-ratings (0,1925) | Fuera |
| Yeung et al. 2024 (Machine Learning; sustituye al anterior) | — | Aprendizaje profundo 0,2098 frente a CatBoost + pi 0,2085; pierde con las casas por un 6 %; más rasgos empeoraron CatBoost | Respalda no complicar |
| Vélez Jiménez et al. 2026 (Comput. Stat.; preprint 2023 completo, versión publicada solo resumen y apéndice) | Kelly dinámico minimiza la varianza y maximiza el retorno | 200 partidos; su red tiene entropía cruzada 1,0318 frente a 0,9966 del mercado (peor, aunque usa el cierre de Pinnacle como entrada); ganancias con **p = 0,16–0,50**; la cifra baja de 135,8 % a 35,8 % en la publicada | No demostrado; probado aquí: pierde |
| KellyBench 2026 | Confirma que la rentabilidad exige Kelly fraccional | **Todos los agentes pierden** (mejor −11 %); Kelly fraccional se asocia a evitar la ruina, no a ganar; su DC + mercado + Kelly 0,25 termina en −31 % | Coincide con lo medido |
| Hartvég et al. 2026 (citado como «Topsakal») | Los LLM con RAG ajustan el porcentaje del modelo | Mundial previo al torneo: **no mide aciertos**, solo validez del cuadro y alucinaciones | Sin evidencia de mejora de probabilidades |
| SAP Community 2026 (blog) | LLM como lector de contexto | Arquitectura sin ninguna métrica | Fuera |

## 7. Motor rediseñado (desde cero, con lo que midió esta data)

1. **Producto = probabilidades calibradas**, publicadas con la descomposición de Murphy por mercado. No se promete
   ganar al mercado: no se le gana en 1X2 con esta data.
2. **Motor A (1X2, goles):** A0 *score-driven* con xG (Koopman-Lit) como candidato a sustituir a DC de producción.
   No se activa hasta que la ventaja (−0,0021) se confirme en más semanas; hoy es empate técnico. Sin calibrador
   afín ni inflación diagonal (no aportan). El mercado sin margen se publica al lado como referencia.
3. **Motor C (conteos):** sí aporta frente a la media de liga. Córners con BN de Yip y tarjetas con el modelo de
   Dawson (árbitro encogido + derbi + igualdad + faltas). Siguiente paso: reajuste del nivel de liga dentro de la
   temporada (deriva de 26/27) y comparación hacia delante con PropLine.
4. **Descartado tras medirlo:** apilado con árboles potenciados, acciones defensivas como fuerza, TabNet/grafos/RL
   (no hay datos ni evidencia), inflación diagonal, calibrador afín, Kelly como producto, LLM como ajuste de
   probabilidades.
5. **SHAP** se queda como herramienta de auditoría de cualquier modelo de árboles futuro.

## 8. Lo que falta

- A4–A7 (aporte de jugadores por tramos, rotación, bajas, entrenador) con el once y los cambios de `futbol.dato`.
  Es lo único que el mercado podría no tener del todo. Exige lo previo al partido con hora de captura (db/099,
  cargado el 1-nov) para no usar bajas reconstruidas como si fueran previas.
- Liga MX y las 13 ligas solo-FotMob, cuando el titular termine las descargas.
- Cuotas de córners y tarjetas: solo PropLine desde el 23-oct.

Código: `src/qf/eval/rediseno.py`, `rediseno_conteos.py`, `rediseno_apilado.py`, `rediseno_kelly.py`,
`src/qf/model/referencias.py`, `score_driven.py`, `conteos.py`, `inflacion_diagonal.py`, `eval/metrics.py` (Murphy,
Diebold-Mariano), `scripts/rediseno_futbol/`. Datos y predicciones en `.local/rediseno_20261101/` (fuera de git).

## 9. Objetivo corregido por el titular (1-nov): máxima probabilidad de acertar, no ganar al mercado

El titular aclaró que no busca ganar a las cuotas de cierre (el mercado reacciona en milisegundos y tiene datos
institucionales) sino **publicar el pronóstico con mayor probabilidad de acertar, con un porcentaje que sea verdad**.
Con ese criterio el mercado deja de ser rival y pasa a ser **una fuente más**, y se mide otra cosa: cada día se
publica el 5/10/20 % más probable de cada fuente y se cuenta cuántos aciertan y si lo anunciado coincide con lo
observado (`scripts/rediseno_futbol/alta_probabilidad.py`, `eval/rediseno_acierto.py`; 24/25 → hoy, 6.016 partidos con
mercado, unos 690 días). Cobertura 5 % ≈ 1 pronóstico por día (n = 692); 10 % ≈ 1,3 por día (n = 918). IC95 de Wilson.

| Familia (opción más probable del partido) | Fuente | Acierto, 10 % más probable (IC95) | Anunciado |
|---|---|---|---|
| **Doble oportunidad** (1X, X2, 12) | Mercado sin margen | **90,8 %** [88,8; 92,5] | 89,3 % |
| | A0 con xG / Dixon-Coles | 89,4 % / 90,1 % | 87,2 % / 87,7 % |
| | LightGBM apilado con cuotas | 91,3 % | 91,3 % |
| **1X2** | Mercado sin margen | **73,1 %** [70,1; 75,9] | 72,1 % |
| | A0 con xG / Dixon-Coles | 71,7 % / 70,9 % | 68,3 % / 69,0 % |
| **Goles** (más/menos 1,5; 2,5; 3,5; ambos marcan) | A0 / DC / mercado anclado | 69,7 % / 67,6 % / 69,0 % | 69,4 % / 69,4 % / 69,6 % |
| **Córners** (líneas 8,5–10,5) | Yip (goles esperados) | 68,8 % [65,8; 71,8] | 68,0 % |
| | media de liga | 54,7 % | 62,7 % (promete 8 puntos de más) |
| **Amarillas** (líneas 3,5–5,5) | Dawson (árbitro, derbi, faltas) | 68,7 % [65,7; 71,7] | 69,2 % |
| | media de liga | 63,5 % | 69,1 % |

Con todos los partidos del día (cobertura 100 %): doble oportunidad ≈ 79–80 %, 1X2 ≈ 52–54 %, goles ≈ 64 %.

**Lo que dicen estas cifras**
1. **Ninguna fuente es claramente más certera que otra.** Las diferencias entre mercado, A0 y Dixon-Coles caen dentro de
   los intervalos (±3 puntos). El mercado sale primero en 1X2 y doble oportunidad, y es la fuente cuyo porcentaje
   anunciado más se parece a la realidad en las probabilidades medias y altas.
2. **El techo existe:** ≈ 91 % para el mejor pronóstico diario de doble oportunidad, ≈ 73 % en 1X2 y ≈ 69 % en goles,
   córners y tarjetas. No se puede prometer más con esta data; lo que sí se puede es no prometer de más.
3. **Honestidad del porcentaje.** El mercado cumple lo anunciado (diferencia entre −1,6 y +0,3 puntos). A0 y
   Dixon-Coles son *conservadores* en 1X2 (anuncian 68 %, aciertan 72 %). El apilado y la regresión logística
   **prometen de más** en 1X2 (anuncian 73–75 %, aciertan 70–72 %). Un modelo de conteos que se limita a la media de
   liga sobrepromete mucho al elegir su «opción más probable» (anuncia 63 %, acierta 55 %): el pronóstico diario **no se
   puede basar en una probabilidad casi constante**, el 5 % superior es ruido.
4. **Conflicto con la cuota mínima de 1,40** (la app exige ≥ 1,40 en el destacado): los pronósticos de 73 % en 1X2 y
   de 90 % en doble oportunidad son favoritos de cuota muy baja. Exigiendo cuota ≥ 1,40 el mejor 10 % del 1X2 baja a
   **58,8 %** (mercado) / 57,8 % (A0), y la doble oportunidad casi desaparece (solo 140–290 de 6.016 partidos llegan a
   1,40, con ≈ 66 % de acierto). Máxima probabilidad y cuota mínima se contradicen; hay que elegir una.
5. **Goles, córners y tarjetas** se midieron limitando la opción a probabilidad ≤ 71 % (equivale a cuota ≥ 1,40 *sin
   margen*; no hay histórico de cuotas de esos mercados). Con margen real de la casa la cuota sería menor, así que los
   pronósticos que de verdad superen 1,40 tendrían una probabilidad algo menor (≈ 66–68 %). Aun así son las únicas
   familias que dan ≈ 69 % **con una cuota publicable**, frente al ≈ 59 % del 1X2.

**Consecuencia para el motor:** el modelo ya no se juzga contra el mercado sino por (a) acierto del pronóstico más
probable por familia y (b) diferencia entre lo anunciado y lo ocurrido. La fuente por defecto para 1X2 y doble
oportunidad es el mercado sin margen de PropLine (disponible cada hora y archivado con su hora); los modelos propios
(A0/Dixon-Coles) quedan para lo que el mercado no da (goles, córners, tarjetas, jugador) y como respaldo si falta la
cuota. Falta medir con la cuota **a T-60** (aquí se usó el cierre, que es más informado): el acierto real al sellar
podría ser algo menor.

## 10. Con cuota mínima 1,28 (decisión del titular, 1-nov)

Mismo protocolo que el §9 (24/25 → hoy, 6.016 partidos con mercado, 10 % más probable de cada día) pero solo se
admite una opción si su cuota es ≥ 1,28. En 1X2 y doble oportunidad se usa la cuota real de cierre; en goles, córners
y tarjetas, sin histórico de cuotas, la opción se limita a probabilidad ≤ 1/(1,28 × 1,04) = 75,1 % (margen supuesto
de 4 %). `alta_probabilidad.py --cuota-min 1.28`, registro `alta_128.log`.

| Familia | Fuente | Acierto 10 % (IC95) | Anunciado | Promesa incumplida |
|---|---|---|---|---|
| 1X2 | Mercado | **67,0 %** [63,9; 70,1] | 65,7 % | −1,3 |
| | A0 con xG | 64,3 % | 62,7 % | −1,6 |
| | Dixon-Coles | 62,7 % | 63,3 % | +0,6 |
| | Apilados (logit / LightGBM) | 62,5 % / 66,6 % | 68,1 % / 69,0 % | **+5,6 / +2,4** |
| Doble oportunidad | Mercado | **72,6 %** [68,7; 76,3] | 73,7 % | +1,1 |
| | A0 / DC / apilados | 70,2–71,8 % | 75,9–78,8 % | **+4,7 a +7,9** |
| Goles | A0 con xG | **74,1 %** [71,1; 76,8] | 73,2 % | −0,9 |
| | Dixon-Coles / mercado anclado | 73,7 % / 70,6 % | 73,0 % / 72,8 % | −0,7 / +2,2 |
| Córners | Yip | 69,5 % | 68,9 % | −0,6 |
| Amarillas | Dawson | **76,3 %** [73,4; 78,9] | 73,1 % | −3,1 (conservador) |

**Pronóstico combinado del día** (la opción más probable entre todas las familias, cuota ≥ 1,28):

| Cobertura | Todas las familias | Sin doble oportunidad | Solo 1X2 y doble |
|---|---|---|---|
| 2 % | 72,3 % (anuncia 74,5) | 74,4 % (74,2) | 70,7 % (71,6) |
| 5 % | 73,4 % (74,5) | 74,7 % (74,2) | 72,3 % (72,4) |
| 10 % | 75,4 % (74,1) | 75,4 % (73,7) | 72,0 % (72,8) |

Familia ganadora del día: goles 168, doble 159, amarillas 139, 1X2 74, córners 7. **Con 1,28 el techo honesto es
≈ 74–75 %** y viene sobre todo de goles y amarillas; la doble oportunidad aporta poco por encima de 1,28 (solo
2.297 de 6.016 partidos tienen una doble ≥ 1,28) y los modelos propios prometen 5–8 puntos de más en ella. Fuente
por familia: mercado para 1X2 y doble; A0 con xG para goles; Dawson para amarillas; Yip para córners.

## 11. Los 37 mercados de las listas del titular (1-nov)

`scripts/rediseno_futbol/mercados.py` (código en `eval/rediseno_mercados.py` y `eval/rediseno_jugadores.py`). Periodo
24/25 → hoy, 8 ligas, unos 6.000 partidos y 690 días. Para cada mercado: la probabilidad de cada opción, su liquidación
real (las líneas asiáticas enteras devuelven el dinero) y el acierto del **10 % más probable de cada día**, con todas
las opciones y solo con las que tendrían **cuota ≥ 1,28** (probabilidad ≤ 1/(1,28 × 1,05) = 74,4 %, margen típico de
PropLine; no hay histórico de cuotas de estos mercados antes del 23-oct, así que el filtro es aproximado). El acierto
de las asiáticas no cuenta las devoluciones.

Cómo se calcula cada familia (todo con datos anteriores al partido):
- **Goles, mitades y hándicaps:** matriz de marcadores de A0 con xG o del mercado 1X2 invertido. Mitades: cada una
  Poisson con la parte f1 de los goles esperados (f1 por liga con temporadas previas: 0,436–0,449). Minutos 0-10:
  8,2 % de los goles. Descanso/final y «mitad con más goles» salen de las dos matrices.
- **Córners:** Yip (binomial negativa con goles esperados), con la distribución de cada equipo para el hándicap.
- **Amarillas:** Dawson (árbitro, derbi, faltas). Primera parte por adelgazamiento binomial (38,7 % de las amarillas
  caen antes del descanso).
- **Jugador** (solo titulares, el once es público a T-60): tasa por 90 de sus partidos anteriores encogida a la de su
  posición × minutos esperados; Poisson, y binomial negativa en pases (κ = 6,6). Se recalibra con 22/23–23/24
  (Platt): la probabilidad cruda **promete de más** en tiros (+6 a +9 puntos), gol (+6) y tarjeta (+11 en el 10 %
  superior); recalibrada queda a ±1. La excepción son los pases: la recalibración empeora (deriva entre temporadas) y
  se usa la cruda, que es conservadora.

### Lista 1

| # | Mercado | Base real | 10 % del día: acierto (anuncia) | Con cuota ≥ 1,28 |
|---|---|---|---|---|
| 1 | AH no favorito +1,5 | 71–72 % | 82–84 % (81–82) | **72,5–72,9 %** (69–70) |
| 1 | AH no favorito +1,0 (sin devoluciones, 25 % devuelve) | 62 % | 76–78 % | 67–70 % |
| 2 | Empate no válido, favorito (25 % devuelve) | 71–72 % | 87–89 % | 69,5 % (68,5) |
| 3 | Doble oportunidad del favorito | 78–80 % | 90–92 % | **74,7–76,6 %** (72) |
| 4 | Más de 1,5 goles | 77 % | 85–87 % | **74,9–76,7 %** (71–72) |
| 5 | Menos de 4,5 / 4,0 goles | 85 % / 82 % | 91 % | 71–76 % (solo 1 de cada 3 días hay uno) |
| 6 | 1.ª parte menos de 1,5 | 65 % | 74 % | 72,2 % (71,3) |
| 7 | 1.ª parte menos de 2,5 | 87 % | 93 % | casi nunca llega a 1,28 |
| 8 | 1.ª parte AH no favorito +0,5 / +1,0 | 59 % / 82 % | 70 % / 90 % | 70 % / 67–68 % |
| 9 | 1.ª parte amarillas menos de 2,0 asiático (24 % devuelve) | 73 % | 82,5 % | 72,1 % (69,5) |
| 10 | 2.ª parte más de 0,5 | 80 % | 86–88 % | **75,1–77,6 %** (72,5) |
| 11 | Mitad con más goles: la 2.ª | **45 %** | 43–46 % | igual: **no es un mercado de alta probabilidad** |
| 12 | Córners asiáticos en vivo min 65-70 | — | — | **no medible**: no hay córners con minuto |
| 13 | Estrella más de 0,5 tiros a puerta | 58 % | 69,6 % (71,2) | 66,3 % (68,8) |
| 14 | Finalizador más de 1,5 tiros | 63 % | 77,1 % (77,6) | **71,0 %** (71,7) |
| 15 | Pivote más pases completados, línea al 80 % de su media | 71 % | 74,0 % (65,6) | 74,0 % (conservador) |
| 15 | … línea en su media | 47 % | 49 % | 49 % |
| 16 | Córners más de 7,5 / 6,5 | 73 % / 83 % | 79 % / 88 % | **73,8 %** / 75,5 % (pocos casos) |
| 17 | AH córners favorito −1,0 / −1,5 | 51 % | 68–74 % | **63,5 %**: flojo |
| 18 | Favorito marca (más de 0,5) | 83–84 % | 93 % | **79,5 %** mercado (anuncia 71,8) / 74,4 % A0 |
| 19 | Ambos marcan: NO | **46 %** | 51–52 % (anuncia 56–61) | no es de alta probabilidad; el mercado anclado promete de más |
| 20 | Amarillas menos de 6,5 / 5,5 | 87 % / 76 % | 94 % / 87 % | 73,0 % / 71,7 % |

### Lista 2

| # | Mercado | Base real | 10 % del día: acierto (anuncia) | Con cuota ≥ 1,28 |
|---|---|---|---|---|
| 1 | 1X2 (favorito) | 53–54 % | 72–73 % | 64,8–66,3 % |
| 2 | Ambos marcan y más de 2,5 | 42–43 % | 48–50 % | igual |
| 3 | Gol en cualquier momento (delantero titular) | 24 % | 37,3 % (cal. 33,4) | igual |
| 4 | Más de 4,5 amarillas | 39 % | 58,1 % (56,5) | igual |
| 5 | Córners más de 9,5 / 10,5 | 50 % / 39 % | 57,8 % / 46,5 % | igual |
| 6 | Marcador exacto (el más probable) | 13–14 % | 18–19 % | igual |
| 7 | Gol en los minutos 0-10 | 21 % | 22–23 % | igual (córners y tarjetas del 0-10 no medidos) |
| 8 | Faltas recibidas más de 2,5 | 9 % | 29,3 % (cal. 30,1) | igual |
| 9 | Descanso/final (el más probable) | 32–34 % | 49,5–49,8 % | igual |
| 10 | Primer equipo en marcar: favorito | 59–61 % | 74–76 % | **73,9 %** mercado (anuncia 67,0) / 70,5 % A0 |
| 11 | Primer goleador (titular) | 4 % | 12,2 % (anuncia 15,9) | igual |
| 12 | Total exacto de goles (el más probable) | 24 % | 26–28 % | igual |
| 13 | Ambos marcan en la 1.ª parte | 20 % | 23 % | igual |
| 14 | Carrera a X córners | — | — | **no medible**: no hay córners con minuto |
| 15 | Más de 2,5 tiros a puerta (jugador) | 7,5 % | 15,9 % (cal. 16,0) | igual |
| 16 | Jugador recibe tarjeta | 15 % | 21,7 % (cal. 22,8) | igual |
| 17 | Gol en ambas mitades | 58 % | 66,5–70,5 % | 65,0–68,0 % (62–64) |

### Márgenes de PropLine (último precio antes del saque, desde el 23-oct)

| Mercado | Pinnacle | Resto de casas |
|---|---|---|
| 1X2 / hándicap asiático | 3,1 % / 3,1 % | 5,6 % / 5,4 % |
| Totales de goles / ambos marcan | 3,7 % / 3,6 % | 5,5 % / 7,4 % |
| Goles por equipo | 4,7 % | 7,3 % |
| Doble oportunidad | 6,0 % | 10,1 % |
| Córners / tarjetas | 5,8 % / 6,2 % | 6,7 % / 6,7 % |

### Lo que dicen

1. **Con cuota ≥ 1,28 hay un grupo de mercados que aciertan 73–80 % con un porcentaje honesto:** favorito marca
   (79,5 %), 2.ª parte más de 0,5 (77,6 %), más de 1,5 goles (76,7 %), doble oportunidad del favorito (74,7–76,6 %),
   primer equipo en marcar el favorito (73,9 %), córners más de 7,5 (73,8 %), pivote con pases al 80 % (74,0 %),
   amarillas menos de 6,5 (73,0 %), AH no favorito +1,5 (72,5–72,9 %), 1.ª parte menos de 1,5 (72,2 %), amarillas
   1.ª parte menos de 2,0 (72,1 %), finalizador más de 1,5 tiros (71,0 %). Ninguno pasa del ≈ 80 % porque por encima
   de 74 % de probabilidad la cuota cae por debajo de 1,28.
2. **Tres afirmaciones de la Lista 1 no se cumplen en esta data:** la 2.ª parte con más goles (45 %), ambos marcan NO
   (46 %) y el AH de córners del favorito (63 % en el mejor caso). Son mercados de probabilidad media, no alta.
3. **La Lista 2 es, como dice su título, de mercados populares, no de alta probabilidad:** salvo 1X2, primer equipo en
   marcar y gol en ambas mitades, todos quedan por debajo del 60 % aun eligiendo lo mejor del día. Sirven como
   pronóstico con su porcentaje honesto, no como «pick seguro».
4. **El mercado invertido subestima los goles** (anuncia 72,7 % en más de 1,5 y ocurre 77,3 %): es conservador en
   goles y promete de más en «ambos marcan NO». A0 con xG está mejor calibrado en goles; en el resto mercado y A0
   quedan dentro de ±3 puntos.
5. **Props de jugador:** la probabilidad cruda promete de más; con la recalibración por temporadas anteriores queda a
   ±1 punto. Faltan cuotas históricas de jugador para saber qué líneas existen a ≥ 1,28.

## 12. Con las cuotas reales de PropLine, a T-60 y al cierre (1-nov)

`scripts/rediseno_futbol/cuotas_reales.py` (exportación de solo lectura `exportar_cuotas_t60.sql`). Del 23-oct al
1-nov: 128 partidos con cuota a T-60 (mediana 111 min antes del saque) y 150 al cierre, en 9–10 días, 8 ligas. Unas
9.400–12.300 opciones (1X2, doble, hándicap, totales, ambos marcan, goles por equipo, córners, tarjetas; sin líneas de
cuarto). Se toma la mejor cuota entre casas y, por partido, la opción más probable con **cuota real ≥ 1,28**.
**Muestra pequeña: los intervalos son de ±8 puntos.**

Fuentes de la probabilidad:
- **Pinnacle** sin margen en el mismo mercado y línea (la doble oportunidad sale de su 1X2).
- **Otras casas** (decisión del titular, 1-nov): donde Pinnacle no cotiza, la mediana de la probabilidad sin margen de
  las demás casas que cotizan esa misma línea (Bovada, Heritage, Jazz Sports, Sportium, Marca Apuestas, Codere,
  BetOnline, 1xBet, Bookmaker.eu, Strendus). Pinnacle no cotiza el 20–22 % de las opciones con cuota ≥ 1,28 (líneas
  alternativas de totales y hándicap, goles por equipo, tarjetas, la doble a T-60); con las otras casas la cobertura
  del mercado pasa del 78–80 % al **99–99,5 %**.
- **Motor** propio (A0, Yip, Dawson).

| Fuente | T-60: acierto (anuncia) | Cierre: acierto (anuncia) |
|---|---|---|
| **Pinnacle y, donde no cotiza, las demás casas** | **70,3 %** [61,9; 77,5] (74,3) | **74,7 %** [67,2; 81,0] (74,8) |
| Solo Pinnacle | 66,4 % (74,1) | 73,3 % (74,4) |
| Solo las demás casas (mediana) | 74,0 % (72,3) | 74,7 % (74,8) |
| Motor | 71,1 % (77,0) | 72,7 % (77,5) |

Calibración de todas las opciones con cuota ≥ 1,28, tramo 70–80 %: el mercado (Pinnacle + demás) anuncia 72,6–72,7 % y
ocurre 73,7–74,2 %; el motor anuncia 74,1–74,2 % y ocurre 68,1–70,0 %; por encima de 80 % el motor anuncia 83 % y ocurre
69–71 %. En las opciones que solo cotizan las demás casas, tramo 60–80 %: anuncian 70 % y ocurre 73–75 %.

**Cada casa por separado** (Brier en las opciones que comparte con Pinnacle): todas quedan a menos de 0,0007 de
Pinnacle, y en el tramo 60–80 % cumplen lo anunciado (Bovada, Heritage, Jazz Sports, Sportium, Marca Apuestas,
Codere: diferencia ≤ 1,5 puntos). En fútbol de estas ligas y con cuotas a una o dos horas del saque, las casas
comunes son tan informativas como Pinnacle; por eso se usa la mediana, que no depende de una sola casa.

**Lo que dicen**
1. **El tope aproximado de las secciones 10–11 era correcto:** el 99,8 % de las opciones con probabilidad ≤ 74,4 %
   tienen de verdad cuota ≥ 1,28, y solo el 5–6 % de las que lo superan.
2. **Con cuota real el motor cae en la maldición del ganador.** Una opción que el motor ve por encima de 74 % y aun
   así paga ≥ 1,28 es justo un caso en que el motor discrepa del mercado, y ahí se equivoca: cuando el motor ve más
   de 5 puntos por encima del mercado (≈ 860–1.120 opciones) anuncia 54 %, el mercado 45–46 % y ocurre 42–44 %;
   cuando ve 5 puntos por debajo, ocurre lo que dice el mercado (43 %). Elegir entre muchas líneas con el motor
   infla lo anunciado 5–8 puntos.
3. **El mercado sin margen es la fuente honesta**, y sumar las demás casas no lo empeora: al cierre anuncia 74,8 % y
   acierta 74,7 %; a T-60 anuncia 74,3 % y acierta 70,3 % (dentro del intervalo; solo Pinnacle a T-60 se quedó en
   66,4 %, con el mismo intervalo amplio). Hay que vigilar T-60 cuando haya más partidos.
4. **Regla para el motor de producción:** la probabilidad publicada es la del mercado sin margen a la hora del sello:
   Pinnacle donde cotiza y, donde no, la mediana de las demás casas que cotizan esa misma línea. El motor propio solo
   se usa en lo que ninguna casa cotiza (≈ 0,5–1 % de las opciones), con las líneas estándar y el tope de 74,4 %, y
   nunca para elegir entre líneas en las que discrepa del mercado. Remedir cada semana: con 9–10 días el acierto
   real puede estar 8 puntos por encima o por debajo.

Corrección del 1-nov: la primera versión de esta sección emparejaba mal el hándicap asiático de Pinnacle (juntaba
local −0,5 con local +0,5 en vez de local −0,5 con visitante +0,5); las cifras de arriba ya son las corregidas.
