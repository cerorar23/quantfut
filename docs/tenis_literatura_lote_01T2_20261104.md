# Tenis — literatura, lote 01T2: modelos y algoritmos (T09 a T16)

Fecha: 2026-11-04. Rediseño desde cero del motor de tenis ATP/WTA con enfoque en
**probabilidad calibrada**. Lote: los 8 PDF `T09`–`T16` de
`BIBLIOTECA_TENIS_COMPLETA/pdfs/01_modelos/`. El índice `INDICE_COMPLETO.txt` se
usó solo para metadatos; cuando contradice al artículo, manda el artículo y se
anota en la sección (d).

Método: texto extraído con `pdftotext -layout` (y `-enc UTF-8` para los PDF con
acentos) y leído completo por tramos. Ningún PDF del lote es escaneado: los 8
devolvieron texto. Cada afirmación cita página (número impreso en el PDF) o
sección. «No consta» = el documento no lo dice. Lo que es inferencia o cálculo
nuestro (no del autor) va marcado **[nuestro]**. Las tablas que `pdftotext`
desalinea se reconstruyeron con el texto que las comenta; cuando eso fue
necesario se dice.

Nuestros datos de referencia para la columna «replicable»: resultados con
marcador por set y tiebreak (TML/Tennis-Data/SofaScore/API-Tennis), ranking y
puntos, superficie, ronda, nivel, edad/altura/mano, duración por set (solo
SofaScore y solo tras el partido), cuotas de cierre Pinnacle/bet365
(Tennis-Data), Match Charting Project (punto a punto, ≈7,6 mil partidos ATP y
4,3 mil WTA), **sin** estadísticas sistemáticas de saque/resto ni aces.

Estado: en redacción (las fichas se añaden al terminar cada estudio).

## (a) Tabla resumen

| Código | Modelo | Datos | Validación | Resultado | Límites | ¿Replicable? | Mercado |
|---|---|---|---|---|---|---|---|
| T09 | GRA + función difusa del ranking; KNN, XGBoost, RL | Wimbledon 2023 masc. (COMAP); dice «300 + 100 partidos» | Partición única + CV aleatoria de 5; sin referencia externa | Exactitud 0,707–0,720; AUC 0,706–0,718; la RL tiene mejor AUC y exactitud que XGBoost | Variables del propio punto (fuga); tamaño imposible; métricas incoherentes | Solo intra-partido, en parte con MCP | Ninguno pre-partido |
| T10 | Elo por superficie (K por nivel, ronda, inactividad, margen); 10 ML; 17 MLP; Elo+ML | ATP Sackmann 1968–2024, 133.138 partidos G/M/A | Temporal 80/2,5/17,5; prueba única; McNemar | Elo 65,87 % (Brier 0,2120) → Elo+ML 67,52 % (0,2071); red ECE 0,0077 | Sin cuotas en la misma muestra; filas espejo en la prueba; conteos incoherentes; Elo sin rating global | Sí, casi entero | Ganador |
| T11 | Agentes talento/azar calibrados con algoritmo genético | ATP 1991–2021, 108.411 partidos | Calibración de distribuciones agregadas; sin predicción | Peso del talento a ≈ 0,18–0,20 («azar ≈ 80 %») | No identificable sin supuestos externos; sin saque; no predictivo | Parcial; no da predictor | Ninguno (simulación de cuadros) |
| T12 | Árbol y GBM (h2o) con y sin estadísticas del año previo | GS + M1000; predicción solo de 2024 (1.201 partidos) | Aleatoria dentro de 2024 (60/15/25) | GBM en prueba 69,4–71,3 %, por debajo del 72,0 % de «gana el mejor clasificado» en esa misma prueba | No supera la base trivial; muestra pequeña; solo exactitud | Sí, salvo estadísticas de saque/resto | Ganador |
| T13 | EWMA + Elo adaptativo + árbol/RL/RF/XGBoost; apuestas simuladas | ATP 1998–2024 (81.831); cuotas de GS 2010–2024 | `TimeSeriesSplit` anidada (5 × 3) | GS: RF Brier 0,1600 frente a casa 0,1608; ROI 10,33 % con umbral elegido a posteriori; 2020–2024 en pérdidas | Umbrales a posteriori; posibles fugas por orden intra-torneo; casa de referencia no identificada | Parcial (sin saque/resto) | Ganador |
| T14 | «Momentum» por entropía + RF, RL, CatBoost y votación | Punto a punto Wimbledon + US Open 2017–2023 | Temporal: 2017–2022 → 2023 | Prueba: 0,72–0,75 con el 25 % del partido; 0,90–0,92 con el 100 %; el 97,5 % es de entrenamiento | En vivo; titular con exactitud de entrenamiento; sin referencia | No (velocidad, distancia) | En vivo |
| T15 | Momentum lineal con pesos a mano + RF + Mann-Kendall | Wimbledon 2023 masc. («12 partidos», 7.284 puntos) | Pesos ajustados en una semifinal; CV aleatoria de 10 | 74 % (umbral 50 %); 78,1 % (umbral 55 %, descarta 5 %) | Circular; pruebas estadísticas mal usadas; incoherencias numéricas | No para pre-partido | Ninguno pre-partido |
| T16 | Entropía + análisis gris + EMA + XGBoost + SHAP | COMAP Wimbledon 2023 + webs oficiales de GS | 7:3 (tipo: no consta) | «Exactitud» 0,999 / 0,993; otras pruebas 0,862–0,965 | Objetivo construido con las entradas; métrica sin definir | No | Ninguno pre-partido |

## (b) Fichas por estudio

### T09 — XGBoost, KNN y regresión logística sobre el «flujo de puntos» de Wimbledon 2023

1. **Referencia.** T09. Rui Bai, Kar Hing Chong, Haoyuan Li, Jia Yew Teh
   (Xiamen University Malaysia). *Proceedings of Machine Learning Research*
   vol. 245:1–11, 2024 (2024 International Conference on Machine Learning and
   Intelligent Computing). Ponencia de congreso, 11 pp. Datos del concurso MCM
   de COMAP 2024 (agradecimientos, p. 10).
2. **Modelo.**
   - Selección de variables por Análisis Relacional Gris (GRA). Grado
     relacional gris γ_i = (1/n)·Σ_{k=1..n} ξ_i(k) (ec. 3, p. 4), con
     coeficiente distintivo ρ = 0,5 (§3.1, p. 8). La fórmula del coeficiente
     ξ_i(k) no se transcribe en el artículo: no consta.
   - «Presión psicológica» por diferencia de ranking x como conjunto difuso
     trapezoidal (ec. 1–2, p. 4): A = {(x, μ_A(x)) | x ∈ U}, μ_A: U → [0, 1];
     μ_A(x) = 0 si x < −50; (x + 50)/40 si −50 ≤ x ≤ −10; 1 si −10 ≤ x ≤ 10;
     (50 − x)/40 si 10 ≤ x ≤ 50; 0 si x > 50. Soporte [−50, 50], núcleo
     [−10, 10]. Los límites son supuestos, no estimados.
   - Variables (Tabla 1, p. 3): x1 estado de saque; x2 «estado de victoria
     previo»; x3 juegos ganados en el set actual; x4 velocidad del saque (mph);
     x5 distancia recorrida **durante el punto** (m); x6 diferencia de ranking;
     x7 error no forzado del jugador; x8 marcador de ventaja (descartada por
     GRA); Y = «current victory status» del jugador. Dirección del saque en
     one-hot (Tabla 2, p. 4).
   - Clasificadores (§2.4, p. 5): KNN (distancia euclídea), XGBoost y
     regresión logística con umbral 0,5. Hiperparámetros: no constan.
3. **Datos.** Wimbledon 2023, individual masculino, conjunto MCM/COMAP 2024
   (§2.4, p. 5); ranking tomado de la web ATP (p. 3). Dice usar «300 partidos»
   para entrenar y «100 partidos» para probar (p. 5; el resumen dice «300
   training sets and 100 testing sets»).
4. **Validación.** Partición única entrenamiento/prueba (aleatoria o temporal:
   no consta) y después validación cruzada de 5 pliegues sin orden temporal
   (Algoritmo 1 y Tabla 7, p. 8). No hay referencia externa (ni cuotas, ni
   ranking, ni Elo): solo se comparan los tres modelos entre sí. **Fuga
   [nuestro]:** x4, x5 y x7 son del propio punto (velocidad de ese saque,
   distancia recorrida en ese punto, error no forzado en ese punto) y x2–x3 son
   estado del partido; la predicción es intra-partido y, en x5 y x7,
   contemporánea al resultado que se predice. Nada es pre-partido.
5. **Resultados** (Tabla 4, p. 7). XGBoost: AUC 0,7130; F1 0,7159; precisión
   0,6978; recall 0,7348; exactitud 0,7127. Regresión logística: AUC 0,7182;
   F1 0,6739; precisión 0,5871; recall 0,7201; exactitud 0,7201. KNN: AUC
   0,7063; F1 0,6866; precisión 0,7257; recall 0,6515; exactitud 0,7071.
   Puntuación propia 3/2/1 por métrica (Tabla 5): XGBoost 12, RL 10, KNN 8.
   CV de XGBoost (Tabla 7): 72,48 %, 74,67 %, 71,79 %, 74,95 %, 72,18 %. GRG con
   ρ = 0,5 (Tabla 8): x1 0,940; x3 0,916; x6 0,914; x5 0,913; x4 0,912; x2
   0,890; x7 0,866; x8 0,707; el orden no cambia con ρ ∈ [0,40; 0,60]. Sin
   intervalos.
6. **Límites.** Declarados (§4.3, pp. 9–10): poca precisión a largo plazo,
   necesita flujo continuo de datos nuevos, difícil con poca historia,
   integración en tiempo real costosa. Detectados **[nuestro]**:
   - Contradicción interna: el resumen dice que detrás de XGBoost van KNN y
     luego RL; §2.5 y la Tabla 5 dicen RL segunda y KNN última.
   - La RL tiene la mejor AUC y la mejor exactitud; XGBoost «gana» solo por un
     sistema de puntos inventado. No se reporta log-loss ni Brier.
   - Fila de la RL incoherente: con precisión 0,5871 y recall 0,7201 el F1
     sería ≈ 0,647, no 0,674; y su recall coincide exactamente con su
     exactitud (0,720149), señal de una métrica ponderada mezclada.
   - Tamaño imposible: el cuadro de Wimbledon masculino tiene 127 partidos;
     «300 + 100 partidos» no existe. Las tres exactitudes son múltiplos exactos
     de 1/536 (382, 386 y 379 aciertos de 536), lo que apunta a 536 filas de
     prueba (¿puntos?), no a 100 partidos.
   - El objetivo Y no está bien definido («current victory status» en la
     Tabla 1; «whether a point has been won» en §2.1).
   - Afirma que la superficie no es significativa y que vale para la WTA
     (§4.1, p. 9) sin tener datos de otra superficie ni femeninos.
   - No reporta la línea base «gana el sacador», que es justo la variable que
     GRA pone primera.
7. **¿Replicable con nuestros datos?** Solo como ejercicio intra-partido con el
   Match Charting Project (sacador, marcador y tipo de error salen de MCP).
   Velocidad del saque y distancia recorrida: no las tenemos. Nada de esto sirve
   para pronóstico pre-partido.
8. **Mercado.** Ninguno pre-partido; como mucho «siguiente punto» en vivo, fuera
   de nuestro alcance.
9. **Transversales.** El saque domina el resultado del punto (coherente con la
   asimetría saque/resto); la «presión» se modela con una función difusa del
   ranking sin validarla; no trata IID, fatiga ni mercado.

### T10 — Banco de pruebas unificado: Elo, 10 modelos clásicos, 17 redes y Elo+ML (ATP 1968–2024)

1. **Referencia.** T10. Khem Poudel, Lilly-Sophie Schmidt, Clifford N. Jones,
   Saroj Baral, Thuan Nhan, Satish Wagle, Jorge Vargas (Middle Tennessee State
   University). *Analytics* (MDPI) 2026, 5, 22; recibido 22-may-2026,
   aceptado 27-jun-2026, publicado 3-jul-2026. Revisado por pares. Código:
   `github.com/LillySchmidt/TennisPredictor` (p. 19).
2. **Modelo.**
   - Elo (ec. 1, p. 5): R_nuevo = R_previo + K·(S − E), con
     E_A = 1 / (1 + 10^((R_B − R_A)/400)). Mejoras (p. 5): **cuatro ratings
     independientes por superficie** (inicio 1500; cada partido solo actualiza
     la de su superficie; no hay rating global ni mezcla); K = 48 en Grand Slam,
     36 en Masters 1000 y 32 en ATP 250/500; multiplicador de ronda de 1,25 en
     finales bajando hasta 0,90 en primeras rondas (valores intermedios: no
     constan); decaimiento de 0,5 puntos/día tras 60 días de inactividad, con
     tope de 200; S escalado por margen de victoria (cita a Kovalchik 2020;
     fórmula exacta: no consta). Control anti-fuga: recálculo independiente con
     diferencia máxima < 10⁻⁶, y una variante deliberadamente sesgada
     (actualizar antes de capturar) daba ≈ 16 puntos de desviación media (p. 5).
   - 16 variables comunes (p. 4): ranking ATP de cada jugador, diferencia de
     ranking, log-rankings, |diferencia de log-ranking|, superficie en one-hot
     (dura, tierra, hierba, moqueta), nivel de torneo, ronda, best-of, tamaño
     del cuadro y año.
   - 10 clasificadores de scikit-learn 1.3 (RL, Ridge, Naive Bayes, KNN, árbol,
     RF, Extra Trees, GB, HistGB, AdaBoost); rejilla con CV estratificada de 5
     pliegues dentro del entrenamiento; prueba usada una vez (pp. 5–6, 8).
   - 17 MLP planos y residuales: h^(l) = ReLU(LayerNorm(W^(l)·Dropout(h^(l−1))
     + b^(l))) (ec. 2, p. 7); de 207 mil a 21 millones de parámetros; AdamW,
     coseno 10⁻³ → 10⁻⁶, entropía cruzada binaria, parada temprana (paciencia
     20) sobre la validación (p. 8).
   - ELO-ML: las 16 variables + Elo de A, Elo de B y su diferencia, en RL,
     Ridge y AdaBoost; GB/HGB excluidos a propósito (p. 8).
   - Aumentos solo en entrenamiento: dos filas por partido (simetría) y ruido
     gaussiano con DE = 1 % de la DE de cada variable continua (+0,2–0,3 pp)
     (p. 4).
   - Métricas: exactitud, precisión, recall, F1, ROC-AUC, log-loss, Brier y
     ECE = Σ_m (|B_m|/N)·|acc(B_m) − conf(B_m)| con 10 bins (ec. 3, p. 8);
     McNemar entre pares.
3. **Datos.** Base ATP de Jeff Sackmann (espejo Kaggle de G. Servera):
   693.552 partidos entre el 29-ago-1968 y el 4-nov-2024, filtrados a Grand
   Slam, Masters 1000 y ATP 250/500 → 133.138 partidos, 266.276 observaciones
   jugador-partido, 1.707 jugadores (Tabla 1, pp. 3–4). Rankings faltantes
   rellenados hacia delante; ranking 300 a quien no tiene ranking previo (p. 3).
   Solo masculino.
4. **Validación.** Partición cronológica 80 / 2,5 / 17,5 %
   (entrenamiento / validación / prueba = 396.299 / 12.384 / 86.691
   observaciones); fechas de corte: no constan. Preprocesado ajustado solo en
   entrenamiento (pp. 3–4). Elo calculado en orden cronológico y verificado.
   **Fuga:** no detecto variables posteriores al partido (el ranking de
   Sackmann es el de la fecha del torneo) [nuestro]. **Referencia de mercado:**
   no se evalúa sobre el mismo conjunto; solo cita el 70–72 % de acierto de las
   casas de Kovalchik (p. 15; en §4.3, p. 18, escribe «70–75 %»).
5. **Resultados** (Tabla 3, p. 9; Tablas 4, 6, 7 y 9). Elo: 65,87 % / AUC
   0,7245 / Brier 0,2120 / log-loss 0,6234 / ECE 0,0189. Mejor clásico (HGB):
   66,30 / 0,7253 / 0,2101 / 0,6192 / 0,0142. Mejor red (Small-Residual,
   1,3 M parámetros): 66,22 / 0,7250 / 0,2098 / 0,6187 / 0,0077. ELO-ML
   AdaBoost: 67,52 / 0,7305 / 0,2071 / 0,6154 / 0,0089. ELO-ML RL: 67,45 %
   (AUC 0,7312, Brier 0,2067); ELO-ML Ridge: 67,38 %. Las tres variables Elo
   suman +1,57 a +1,65 pp (McNemar p < 0,001). HGB frente a la red: +0,08 pp,
   p = 0,31; ELO-ML RL frente a AdaBoost: −0,07 pp, p = 0,18 (texto de §3.6.2;
   la Tabla 8 sale desalineada en la extracción). Las 17 redes caen en
   66,15–66,22 %. Peor clásico: Naive Bayes, 61,23 %. Elo por superficie (p. 9):
   tierra 67,3 %, dura 66,1 %, moqueta 65,8 %, hierba 64,2 %. El Elo está bien
   calibrado para diferencias de ±200 puntos y es algo sobreconfiado por
   encima de 300 (p. 9). SHAP en RF sobre 500 observaciones: ranking 77 %,
   superficie 12 %, contexto de torneo 11 % (Tabla 5). DE entre pliegues: 0,12
   pp (HGB), 0,15 (GB), 0,18 (RF). Los IC del 95 % solo están en la Fig. 7, sin
   cifras.
6. **Límites.** Declarados (§4.4, p. 18): sin estadísticas de saque/resto,
   punto a punto, forma física ni lesiones; solo ATP; solo MLP; sin evaluación
   contra cuotas históricas; SHAP solo en RF. Detectados **[nuestro]**:
   - Inconsistencia numérica: declara 266.276 observaciones, pero los tres
     subconjuntos suman 495.374.
   - La prueba contiene cada partido dos veces (espejo); en p. 16 las llama
     «86,691 held-out matches». McNemar trata las filas como independientes:
     los p-valores son optimistas.
   - Elo solo por superficie, sin rating global ni mezcla: más débil que los
     Elo habituales de la literatura, lo que puede inflar la ganancia de ELO-ML
     (el ranking aporta la información «global»). Los K son fijos: no consta
     que el Elo se ajustara en la validación pese a llamarlo «tuned».
   - La métrica principal es la exactitud; en Brier la mejora total es
     0,2120 → 0,2071.
   - El 70–72 % de las casas viene de otra muestra (Kovalchik 2016, 2014): no
     es comparable con su conjunto de prueba.
   - 56 años en una sola partición con deriva fuerte (moqueta, formatos).
7. **¿Replicable con nuestros datos?** Sí, casi entero: ranking, superficie,
   ronda, nivel, best-of, cuadro y año salen de TML/Sackmann, y el Elo se
   construye con los resultados. Con las cuotas de cierre de Tennis-Data
   podemos hacer lo que ellos no hacen: medir en el mismo periodo frente al
   mercado. La WTA hay que replicarla aparte.
8. **Mercado.** Ganador del partido, con probabilidad calibrada.
9. **Transversales.** Superficie (Elo por superficie; la hierba es la menos
   predecible); ratings (K por nivel, decaimiento por inactividad, margen de
   victoria); jugadores sin historia (Elo 1500, ranking 300 por defecto);
   calibración (ECE, diagramas de fiabilidad); estructura del marcador: cita
   que el 4,18–4,78 % de los partidos ATP los gana quien hizo menos puntos
   (Lisi et al., pp. 15–16). No trata IID, fatiga ni eficiencia de mercado.

### T11 — Modelo basado en agentes (talento frente a azar) calibrado con algoritmo genético

1. **Referencia.** T11. Salvatore Prestipino, Andrea Rapisarda (Universidad de
   Catania; INFN; Complexity Science Hub). *Mathematical and Computational
   Applications* (MDPI) 2024, 29, 77; recibido 12-jun-2024, publicado
   11-sep-2024. Artículo revisado, 15 pp.
2. **Modelo** (ec. 1–3, pp. 4–7).
   - P1(t) = 1/2 + d12(t)/2; P2(t) = 1/2 − d12(t)/2;
     d12(t) = a·(T1 − T2) + (1 − a)·[2·C(t) − 1].
   - a ∈ [0, 1] es el peso del talento (1 − a, el del azar); T_i ~ N(0,5; σ_t)
     truncada en [0, 1] y fija para cada agente; C(t) ~ N(0,5; σ_c) truncada en
     [0, 1] y re-muestreada en cada iteración (cada punto).
   - El punto se asigna al agente con mayor P, es decir al 1 si d12 > 0 (§2.3,
     p. 5). Puntos i.i.d. dado el par y **sin distinción de sacador**
     [nuestro: el texto nunca introduce el saque en el mecanismo].
   - Se reproducen las reglas de juego, set y partido y torneos de 128 agentes
     en 7 rondas, con emparejamiento inicial aleatorio y agentes nuevos en cada
     torneo (pp. 5–6).
   - Dato observado = proporción de puntos ganados en el partido por ganador y
     perdedor (simétricas respecto a 0,5) (p. 3); se comparan el histograma y
     su anchura a media altura (FWHM) por ronda.
   - Ajuste: fitness f(p, q) = 1/d(p, q), con d la distancia euclídea entre
     histogramas normalizados (ec. 3, p. 7); algoritmo genético (PyGAD),
     población 30, 100 generaciones, 7 corridas, rejilla de 0,01 en
     [0,01; 1,00]³ (10⁶ combinaciones), con umbrales de fitness cada 0,10 que
     añaden 100 torneos simulados cada uno (p. 7). Segunda etapa: 1.450 puntos
     sobre la «superficie de máximo fitness», 7.000 torneos por punto,
     comparando la tendencia del FWHM («verosimilitud») (p. 8).
3. **Datos.** 108.411 partidos individuales masculinos ATP en 2.125 torneos,
   1991–2021 (Grand Slam, Masters 1000, 500 y 250); fuentes: web ATP, datahub y
   Sackmann (p. 2; refs. 22–24). Solo usa los puntos totales ganados por cada
   jugador.
4. **Validación.** Ninguna predictiva: es calibración de distribuciones
   agregadas dentro de muestra. No hay partición, ni partidos individuales, ni
   identidad de jugadores, ni comparación con cuotas, ranking o Elo. Fuga: no
   aplica.
5. **Resultados.** El buen ajuste se concentra en una superficie fina del
   espacio (a, σ_t, σ_c) (Fig. 4; se muestran fitness > 0,46). Dos regiones
   (Tabla 1, verosimilitud normalizada > 0,774): (0,34; 0,07; 0,16) y
   (0,66; 0,04; 0,67). Solo desde octavos (Tabla 2, > 0,321): máxima
   verosimilitud (0,17; 0,09; 0,08), media ponderada (0,23; 0,07; 0,07);
   región alternativa (0,78; 0,03; 0,90), media (0,80; 0,02; 0,79). Fijando
   σ_t = 0,1 con media 0,6 (distribución del cociente intelectual tomada de
   trabajos previos) y σ_c = 0,12: a ∈ [0,18; 0,20], tres valores con
   verosimilitud > 0,85 (§3.5, p. 11). Conclusión de los autores: el azar pesa
   ≈ 80 % (p. 13).
6. **Límites.** Declarados: redundancia entre a y σ_c (dos soluciones
   igualmente buenas), modelo deliberadamente simple, diferencias entre
   torneos en primeras rondas, centros fijos en 0,5 (pp. 9–14). Detectados
   **[nuestro]**:
   - El «80 % de azar» es un parámetro de este modelo, no una probabilidad de
     sorpresa en un partido; y la ambigüedad se resuelve imponiendo una
     distribución de talento derivada del cociente intelectual humano, no de
     datos de tenis.
   - Incoherencias internas: §2.2 centra el talento en 0,5 y §3.5 usa 0,6; las
     conclusiones hablan de desviaciones típicas «around 0.01» (p. 13) cuando
     las ajustadas son 0,07–0,12.
   - Sin saque ni resto: el punto es simétrico, contra la estructura básica
     del tenis. Formato (mejor de 3 o 5) y tiebreak simulados: no consta cómo.
   - Agentes nuevos en cada torneo: no hay persistencia de talento.
7. **¿Replicable con nuestros datos?** Solo en parte: rondas y resultados sí,
   pero la proporción de puntos ganados exige estadísticas de puntos que
   nuestras fuentes no traen de forma sistemática; podría sustituirse por la
   proporción de juegos (sí la tenemos por el marcador). No da un predictor.
8. **Mercado.** Ninguno directo; conceptualmente, simulación de cuadros
   (ganador del torneo).
9. **Transversales.** IID implícito; efecto de selección por rondas (el FWHM
   baja ronda a ronda porque avanzan los de más talento: «paradoja del
   talento»); entre jugadores de nivel parecido el azar domina. No trata
   superficie, ratings, fatiga ni mercado.

### T12 — TFG: árboles y GBM para Masters 1000 y Grand Slam de 2024

1. **Referencia.** T12. Juan Piedras Martínez. Trabajo Fin de Grado, Doble
   Grado en Física y Matemáticas, Universidad de Sevilla, junio de 2025. 80 pp.
   (texto pp. 1–45, código R pp. 47–71, bibliografía pp. 73–74). No revisado
   por pares. Leídos íntegros: caps. 1 (introducción), 2 (métodos: GBM), 3
   (datos), 4 (predicción y conclusiones) y del apéndice las secciones de
   construcción de datos, partición y modelos (pp. 47–54 y 62–71); no leído en
   detalle: pp. 55–61 (imputaciones repetitivas y gráficos descriptivos).
2. **Modelo.**
   - Árbol de clasificación (`rpart`, minbucket = 20) (§4.2.1, p. 34).
   - GBM (`h2o`, distribución bernoulli). Teoría del cap. 2:
     f_M(x) = Σ_{m=1..M} T(x; θ_m) (2.2); pseudo-residuos
     r_im = −[∂L(y_i, f(x_i))/∂f(x_i)] en f = f_{m−1} (2.6); actualización con
     velocidad de aprendizaje f_m = f_{m−1} − ν·ρ_m·g_m (§2.7.1);
     p_k(x) = e^{f_k(x)} / Σ_l e^{f_l(x)} con desviación multinomial (§2.4);
     importancia I_l² = (1/M)·Σ_m I_l²(T_m) (§2.8.1); dependencia parcial
     (§2.8.2); SHAP φ(i) = Σ_{S ⊆ F∖{i}} |S|!·(p − |S| − 1)!/p! ·
     [val(S ∪ {i}) − val(S)] (2.8; el factorial de |S| se pierde en la
     extracción).
   - Hiperparámetros por rejilla según AUC de validación: learn_rate 0,01 y
     max_depth 4 (Tabla 4.3, p. 36); ntrees = 500, min_rows = 5, parada
     temprana por error de clasificación (tolerancia 0,1 %, 3 evaluaciones,
     cada 5 árboles) (p. 37).
   - Variables: (1) nivel, ronda, superficie; mano, altura, edad y ranking de
     ambos; diferencias de edad, altura, ranking y log-ranking; (2) lo anterior
     más las diferencias de ≈ 37 estadísticas de la temporada anterior (aces,
     dobles faltas, % de primeros, % de puntos ganados con 1.º y 2.º, % de
     juegos de saque ganados, % de puntos de resto, tasa de break, break
     points, partidos y victorias por superficie, partidos y victorias en
     cuartos-semis-final, torneos ganados) (§3.3, pp. 24–25; §4, pp. 29–30).
     Jugador sin registros el año previo: se le imputan estadísticas «malas»
     (mínimo de aces, máximo de dobles faltas…) (p. 30).
   - Objetivo: Ganador = 1 si gana el mejor clasificado («Jugador 1») (p. 29).
   - Variante «balanceada»: submuestreo de la clase mayoritaria al 70 %
     (`sample_rate_per_class = c(1, 0.7)`, p. 68).
3. **Datos.** Sackmann `tennis_atp`, 1991–2024, solo Grand Slam y Masters
   1000: ≈ 35.000 partidos y ≈ 1.400 jugadores; base anual de 7.073 filas × 40
   columnas (pp. 22–25). Minutos faltantes imputados con la media; filas con
   otros faltantes eliminadas (≈ 2 %) (p. 24). **La predicción se hace solo
   sobre 2024** (1.201 partidos con ranking, Tabla 4.2) con estadísticas de
   2023.
4. **Validación.** Partición **aleatoria dentro de 2024**: árboles 70/30
   (`set.seed(123)`, p. 62); GBM 60/15/25 entrenamiento/validación/prueba con
   `h2o.splitFrame` → 728 partidos de entrenamiento y 307 de prueba (Tablas
   4.4–4.5); umbral elegido maximizando la exactitud en validación (p. 38).
   No es temporal: partidos posteriores de 2024 sirven para predecir otros
   anteriores [nuestro]. Variables pre-partido (ranking de la fecha del
   torneo, edad, estadísticas del año previo): sin fuga del propio partido.
   Dudas **[nuestro]**: el código selecciona las columnas 51:68, que incluyen
   los nombres de los jugadores, y usa «todos los predictores disponibles»
   (pp. 53, 64); no aparecen en la Fig. 4.6, así que su uso no consta. La
   explicación SHAP de la final de Wimbledon usa un umbral que maximiza F1
   sobre la propia prueba (p. 44). Referencia: «gana el mejor clasificado».
5. **Resultados.** En 2024 el mejor clasificado gana el 67,94 % (816 de 1.201)
   (Tabla 4.1, p. 30); por ronda (Tabla 4.2, reconstruida): R128 66,91 %,
   R64 67,45 %, R32 71,15 %, R16 72,12 %, QF 59,62 % (n = 52), SF 65,38 %,
   F 69,23 %. Árboles: error de prueba 32,41 % sin estadísticas y 37,4 % con
   ellas; ninguno supera a la clase mayoritaria (pp. 35–36). Rejilla GBM: mejor
   AUC de validación 0,629 (Tabla 4.3). GBM (Tabla 4.10, p. 45): exactitud de
   entrenamiento 73,90 / 79,26 / 80,77 %; de prueba 71,01 / 69,38 / 71,34 %;
   acierto en victorias del peor clasificado 15,12 / 17,44 / 20,93 % (modelo
   inicial / con estadísticas / con estadísticas y submuestreo). Variable más
   importante: diferencia de log-ranking sin estadísticas; diferencia de
   partidos en rondas finales con ellas (pp. 38, 43). Tendencia 1991–2024: el
   % de juegos de saque ganados crece de forma significativa; en 2023, 87 %
   entre ganadores de torneo y 75 % en el global (p. 28).
6. **Límites.** Declarados: clases desequilibradas, sobreajuste al añadir
   estadísticas; propone forma reciente, cara a cara y Elo como trabajo futuro
   (p. 45). Detectados **[nuestro]**:
   - En el mismo conjunto de prueba (307 partidos: 86 victorias del peor
     clasificado y 221 del mejor, Tabla 4.5), elegir siempre al mejor
     clasificado acierta 221/307 = **72,0 %**, por encima de los tres GBM
     (71,0 / 69,4 / 71,3 %). El TFG se compara con el 67,94 % del año completo,
     no con la base de su propia muestra: ningún modelo supera la línea base
     trivial.
   - La «mejora» de 71,01 a 71,34 % equivale a 1 partido de 307.
   - Solo exactitud con umbral: ni Brier, ni log-loss, ni calibración, aunque
     el GBM da probabilidades.
   - Muestra pequeña (728 de entrenamiento) y partición aleatoria
     intra-temporada; imputación «pesimista» ad hoc para quien no tiene
     historia.
7. **¿Replicable con nuestros datos?** Sí la parte de ranking, edad, altura,
   mano, superficie, ronda y nivel. Partidos y victorias del año previo por
   superficie y en rondas finales: sí (salen de los resultados). Las
   estadísticas de saque/resto del año previo: no, no las tenemos de forma
   sistemática.
8. **Mercado.** Ganador del partido.
9. **Transversales.** Jugadores con poca historia (imputación pesimista);
   ranking en logaritmos; edad (en mediana gana el más joven, p. 32); la tasa
   del favorito por ronda no es monótona (cae en cuartos); deriva temporal del
   dominio del saque. No trata IID, fatiga ni mercado.

### T13 — Tesis de grado VU: variables históricas con EWMA, Elo adaptativo, 4 clasificadores y apuestas simuladas en Grand Slam

1. **Referencia.** T13. Jakub Olaf Dryja. Tesis de grado (BSc Computer
   Science), Vrije Universiteit Amsterdam, 15-jul-2025; director Wan Fokkink.
   47 pp. No revisada por pares. Código:
   `github.com/qdryja/Data-Driven-Prediction-of-ATP-Tennis` (p. 17). Leída
   íntegra (caps. 1–7 y apéndices A–C).
2. **Modelo.**
   - Variables **relacionales**: cada métrica se calcula para cada jugador solo
     con partidos anteriores y se resta (J1 − J2) (§5.3.1, p. 20). Una «API»
     recorre los partidos en orden, calcula `generate_features_for_match()` con
     el estado acumulado y solo después actualiza el estado con el resultado
     (§5.3.2, pp. 20–21).
   - Tasas normalizadas (aces y dobles faltas por juego de saque, % de break
     points, etc.) suavizadas con EWMA_t = α·m_t + (1 − α)·EWMA_{t−1} (las
     fórmulas del texto son imágenes y no se extraen; se reconstruyen con la
     definición de variables de p. 21), con α = 0,18 (vida media ≈ 3,5
     partidos) y α = 0,05 (≈ 14 partidos).
   - Elo global con K dinámico «al estilo FiveThirtyEight» en función del
     número de partidos n, con parámetros K, offset y shape (p. 23);
     decaimiento hacia 1500 tras 90 días de inactividad gobernado por λ y los
     días sin jugar, y K aumentado temporalmente al volver (p. 24). Elo por
     superficie con K fijo y sin decaimiento (p. 25). **Los valores de K,
     offset, shape y λ no constan.**
   - Compuestas (pp. 25–27): ventaja de saque = % de puntos de saque ganados
     propio − % de puntos de resto ganados del rival; «completitud» = % puntos
     de saque × % puntos de resto; «momentum» compuesto a partir de
     m_i = EWMA corta − EWMA larga de N métricas y sign(m_i) (fórmula en
     imagen).
   - Lista de variables (Tablas A.1–A.2, pp. 44–45): edad, altura, ranking y
     puntos ATP, Elo, Elo de superficie, Elo corto/largo, % de victorias
     corto/largo, % en tiebreaks, % frente a la mano del rival, cara a cara,
     aces, dobles faltas, % primeros, % ganados con 1.º y 2.º, % puntos y
     juegos de saque, % puntos y juegos de resto, conversión y salvación de
     break points, ventaja de saque, completitud, momentum.
   - Clasificadores: árbol, regresión logística (L1, C = 0,215), Random Forest
     (600 árboles, profundidad 10, min_samples_leaf 4) y XGBoost (500,
     profundidad 5, η = 0,01, γ = 0,2, λ = 1, submuestreo 0,8) (Tabla B.1,
     p. 46).
   - Probabilidad de la casa: p_i = 1/O_i normalizada por la suma,
     p̂_i = (1/O_i)/(1/O_1 + 1/O_2); cita a Štrumbelj sobre el método de Shin
     pero usa la normalización simple (§4.2, p. 12).
3. **Datos.** Sackmann ATP 1998–2024: 81.831 partidos (27 CSV). Estratos
   (Tabla 5.2, p. 18): S₁ todos (81.831), S₂ partidos con alguno de los 599
   jugadores que jugaron un cuadro final de Grand Slam 2010–2024 (64.900), S₃
   partidos de Grand Slam 2010–2024 (7.493). Se eliminan 412 walkovers y
   partidos no terminados y las filas sin estadísticas; quedan 74.553 / 61.147
   / 7.461 (Tabla 5.3, p. 19). Imputaciones: altura con la media, ranking
   faltante = 2000, puntos = 0, minutos = juegos × 6 (p. 19). Cuotas: 59 CSV de
   tennis-data.co.uk de Grand Slam 2010–2024 (Betfair, Ladbrokes, Pinnacle,
   Stan James, Bet365) (§2.2, p. 7; §5.1, p. 18). **Qué casa o qué columna se
   usa como referencia: no consta.**
4. **Validación.** Validación cruzada temporal anidada: 5 pliegues externos
   `TimeSeriesSplit` con ventana creciente y 3 internos para la búsqueda
   aleatoria de 40 combinaciones (§5.4, pp. 27–28). Métricas: exactitud,
   log-loss, Brier y AUC, con curvas de calibración por pliegue (pp. 28–30).
   Grand Slam 2010–2024 se describe como ventana «chronologically held-out»
   (p. 31); cómo se ensamblan exactamente esas predicciones: no consta.
   Referencia: probabilidad normalizada de la casa. **Riesgos de fuga
   [nuestro]:** (i) Sackmann solo trae la fecha de inicio del torneo y el autor
   admite no tener la hora del partido (p. 41); si dentro de un torneo el orden
   no respeta la ronda, la API podría usar resultados de rondas posteriores (no
   consta cómo se ordena); (ii) el estrato S₂ se define con información futura
   (haber jugado un Grand Slam hasta 2024) y decide qué filas se conservan.
5. **Resultados.** Conjunto completo (Tabla 6.1, p. 31): árbol 0,6611 / AUC
   0,7234 / log-loss 0,6118 / Brier 0,2117; RL 0,6756 / 0,7440 / 0,5948 /
   0,2048; RF 0,6748 / 0,7402 / 0,5985 / 0,2063; XGBoost 0,6767 / 0,7448 /
   0,5942 / 0,2046. Grand Slam 2010–2024 (Tabla 6.2, p. 32, desalineada en la
   extracción y reconstruida con el texto de pp. 32–33): árbol 0,7347 / 0,8138
   / 0,5283 / 0,1768; RL 0,7468 / 0,8271 / 0,5133 / 0,1712; **RF 0,7642 /
   0,8525 / 0,4876 / 0,1600**; XGBoost 0,7518 / 0,8352 / 0,5054 / 0,1676;
   **casas 0,7653 / 0,8452 / 0,4888 / 0,1608**. Apuestas a 10 unidades fijas:
   (a) apostar siempre al favorito del modelo (Tabla 6.3, p. 33): árbol
   −1.583,34 (−2,12 %), RL −1.276,94 (−1,71 %), RF +1.616,26 (+2,17 %), XGBoost
   −655,94 (−0,88 %), favorito de la casa −1.219,84 (−1,63 %); (b) umbral
   (cuota ≤ U y P_modelo > P_casa): mejor ROI con RF y U = 1,71: 2.045
   apuestas, +2.113,1, ROI 10,33 %, acierto 0,859 (Tabla 6.4, p. 36); mayor
   beneficio con RF y U = 3,97: 4.882 apuestas, +3.578,5, ROI 7,33 % (Tabla
   6.5); (c) acuerdo (todos los modelos con P > 0,76): RF solo 2.652 apuestas,
   ROI 4,32 %; RF+XGB+LR 2.323 apuestas, +679,46 (Tabla 6.6, p. 38). Año a año
   (Tabla C.1, p. 47): RF suma +1.896,35 en 2010–2019 y **−280,09 en
   2020–2024** [nuestro, suma de la tabla; el total 1.616,26 cuadra].
6. **Límites.** Declarados (§7, pp. 40–41): solo ATP; una sola foto de cuotas
   pre-partido; faltan velocidad de saque, errores no forzados, fatiga y hora
   exacta; apuestas solo en Grand Slam; desaconseja usarlo para ganar dinero.
   Detectados **[nuestro]**:
   - Umbrales (1,71; 3,97; 0,76) elegidos a posteriori sobre la misma muestra
     tras barrer muchos valores (Fig. 6.2): sesgo de selección; no hay periodo
     nuevo con el umbral fijado antes.
   - El resumen dice «ROI 10,65 % en 2.047 apuestas»; la Tabla 6.4 da 10,33 %
     en 2.045. El texto dice XGBoost ≈ −0,6 % y la tabla −0,88 %. En la Tabla
     6.6, 679,46/23.230 = 2,92 %, no 2,29 %. Tabla 5.3: pasar de 7.493 a 7.461
     es eliminar el 0,43 %, no el 0,01 % (y 8,9 %/5,8 % en S₁/S₂, no
     8,4 %/5,3 %). En p. 36 habla de apuestas mayores cuando la apuesta es fija.
   - Que un RF con datos de Sackmann gane a la casa en log-loss y Brier en
     Grand Slam sería un resultado extraordinario; descansa en los posibles
     puntos de fuga de arriba y en una referencia de casa no identificada.
   - La ventaja desaparece en el tramo más reciente (2020–2024 en pérdidas).
   - Sin intervalos ni contraste de significación del ROI.
7. **¿Replicable con nuestros datos?** Parcialmente. Sí: Elo global y por
   superficie, EWMA del % de victorias, % en tiebreaks (tenemos el marcador con
   tiebreak), % frente a zurdos/diestros, cara a cara, ranking/puntos, edad,
   altura, y la comparación con cuotas de cierre de Tennis-Data. No: todas las
   variables de saque/resto (aces, % de primeros, puntos de saque/resto, break
   points, ventaja de saque, completitud), que salen de las estadísticas de
   Sackmann y no tenemos de forma sistemática.
8. **Mercado.** Ganador del partido (y estrategias de apuesta sobre él).
9. **Transversales.** Ratings (K que baja con la experiencia, decaimiento por
   inactividad, impulso de K al volver, Elo por superficie); jugadores con poca
   historia (Elo 1500; la calibración mejora en los pliegues tardíos al
   estabilizarse el Elo, p. 30); walkovers y partidos no terminados eliminados;
   fatiga no modelable sin hora del partido; mercado: el margen del ejemplo es
   3,9 % y apostar siempre al favorito de la casa pierde −1,63 %; «momentum»
   como forma reciente (EWMA corta − larga), no intra-partido.

### T14 — Predicción a mitad de partido con «momentum psicológico» y variables físicas (Wimbledon y US Open)

1. **Referencia.** T14. Boyuan Li, Zihui Deng, Jinger Li, Yixuan Miao, Gaurav
   Gupta (Wenzhou-Kean University; Hangzhou Normal University). PDF guardado:
   preprint de Research Square, publicado en línea el 25-jul-2024
   (doi 10.21203/rs.3.rs-4597222/v1); versión final en *Journal of Big Data*
   (8-jul-2025, doi 10.1186/s40537-025-01216-4), que **no** se ha leído. 20 pp.
   Las palabras clave del preprint son de otro artículo («Media platforms,
   two-sided markets…», pp. 1–2).
2. **Modelo.**
   - Imputación KNN (k = 5, distancia de Minkowski
     ‖x′ − x_j‖_p = (Σ_i |x′_i − x_{j,i}|^p)^{1/p}; media para numéricas y moda
     para categóricas) (§3.1.1, ec. 1–2, p. 5).
   - «Momentum psicológico» por pesos de entropía (§3.2, ec. 3–4, pp. 6–7):
     E = −k·Σ p·log p, con k = 1/ln(n) (n = número de muestras), y
     w = (1 − E)/Σ(1 − E). Eventos positivos: ace, punto ganado en la red,
     winner, break conseguido, punto ganado en peloteo < 15 golpes y > 15
     golpes; negativos: doble falta, punto perdido en la red, break point
     fallado, error no forzado. Cómo se acumula en el tiempo (ventana, signo):
     no consta.
   - Otras variables (§3.3, p. 7): distancia recorrida relativa entre jugadores
     **durante el punto**, velocidad del saque, número de golpes del peloteo
     (numéricas); sacador, zona del saque y profundidad del resto
     (categóricas).
   - Clasificadores: regresión logística (p = 1/(1 + e^(−z)),
     z = b0 + Σ b_i·x_i; ec. 5–6), Random Forest, CatBoost (H_t = H_{t−1} +
     α·g_t, g_t = argmin_g E[L(y, H_{t−1}(X) + g(X))]; ec. 7–9) y votación
     suave RF + CatBoost (§3.4, pp. 7–9). Hiperparámetros: no constan.
3. **Datos.** Base punto a punto de Grand Slam de Jeff Sackmann
   (`tennis_slam_pointbypoint`), Wimbledon y US Open: 2017–2022 para entrenar
   (1.592 partidos tras quitar los que tienen muchos huecos) y 363 partidos de
   2023 para probar (resumen, p. 1; §3.1, p. 5; p. 12). Si incluye cuadro
   masculino y femenino: no consta.
4. **Validación.** Partición temporal (entrenar 2017–2022, probar 2023): es lo
   mejor del artículo. Se predice el ganador del partido con lo observado en el
   primer 25 %, 50 %, 75 % o 100 % del partido (p. 12). Unidad de predicción
   (punto o partido) y forma de agregar: no constan. Métricas: exactitud, F1,
   AUC y curvas de calibración (Fig. 4) sin cifras de calibración. **Fuga
   [nuestro]:** por diseño es información intra-partido; con «100 %» ya se
   conoce el partido entero, así que no es una predicción. No hay referencia
   externa: ni un modelo de Markov a partir del marcador, ni el favorito
   pre-partido, ni cuotas en vivo.
5. **Resultados** (Tabla 1, p. 12, desalineada en la extracción y reconstruida
   con el texto de la misma página). Entrenamiento, exactitud / F1: RF
   0,908 / 0,911; RL 0,912 / 0,912; CatBoost 0,912 / 0,912; votación 0,975 /
   0,974. **Prueba 2023** (exactitud) RF / RL / CatBoost / votación: con el 25 %
   del partido 0,746 / 0,738 / 0,734 / 0,724; con el 50 % 0,770 / 0,784 /
   0,773 / 0,768; con el 75 % 0,798 / 0,820 / 0,809 / 0,826; con el 100 %
   0,900 / 0,922 / 0,900 / 0,914. AUC (Fig. 5): RL 0,97, RF 0,97, CatBoost
   0,97, XGBoost 0,96, LightGBM 0,96, SVM 0,93. Importancia: el «momentum
   psicológico» es la variable más importante en RF y CatBoost; la
   profundidad del resto, la menos (p. 13).
6. **Límites.** Declarados (p. 13–14): depende de la calidad de los datos,
   falta validar en otros torneos, coste computacional del tiempo real;
   futuro: clima, superficie, fatiga. Detectados **[nuestro]**:
   - El 97,5 % del resumen y de las conclusiones es exactitud **de
     entrenamiento**; en la prueba de 2023 el mejor con el partido entero es
     0,922 (RL), y con el 25 % del partido 0,724–0,746.
   - Con el 25 % del partido no supera ni al favorito pre-partido del mercado:
     en Grand Slam masculino 2010–2024 la casa acierta 0,765 antes de empezar
     (T13, Tabla 6.2). La comparación es aproximada (T14 puede incluir
     cuadro femenino), pero indica que el modelo no aporta.
   - El «momentum» es un recuento ponderado de sucesos que ganan o pierden
     puntos (aces, winners, breaks, errores): su importancia es casi
     tautológica y no prueba que exista momentum psicológico.
   - Incoherencias: dice que se queda con «Random Forest y Naive Bayes»
     (p. 11) y Naive Bayes nunca aparece; describe «BreakPointMissed» como
     ganar el juego al resto (p. 6); palabras clave de otro artículo.
7. **¿Replicable con nuestros datos?** Solo la parte de sucesos del punto con
   el Match Charting Project (aces, winners, errores no forzados, red, break
   points, longitud del peloteo). Velocidad del saque, distancia recorrida y
   profundidad del resto: no las tenemos (vienen de la base punto a punto de
   Grand Slam de Sackmann, que no está en nuestra lista). No aplicable a
   pre-partido.
8. **Mercado.** Ganador del partido **en vivo**; nada pre-partido.
9. **Transversales.** IID/momentum: cita literatura de momentum (Meier et al.,
   Depken et al., Jackson y Mosurski) pero su medida no permite contrastar
   independencia de puntos; saque: el sacador figura entre las variables
   importantes; superficie y fatiga: fuera.

### T15 — «Cambios de momentum» en Wimbledon 2023 con análisis factorial, Kendall y Random Forest

1. **Referencia.** T15. Yuean Xia, Changfeng Li, Tanran Zhang (Soochow
   University). *Applied Sciences* (MDPI) 2025, 15, 2018; recibido
   10-ene-2025, aceptado 10-feb-2025, publicado 14-feb-2025. Revisado por
   pares, 20 pp. La parte de tenis de mesa (§3.5.2) se leyó pero no se usa, por
   indicación del índice.
2. **Modelo.**
   - Momentum lineal (ec. 1, p. 4): M_i = k1·p_iw + k2·p_ig + k3·p_is +
     k4·p_ia + k5·p_inetptwon + k6·p_ib + k7·p_ibw + k8·s − k9·d − k10·p_id −
     k11·sn − k12·p_iu − k13·p_ibm, i = 1, 2. Según la Tabla 1 (pp. 2–3, leída
     en orden): p_iw winners, p_ig juegos ganados, p_is sets ganados, p_ia
     aces, p_inetptwon puntos ganados en la red, p_ib ocasiones de break,
     p_ibw breaks logrados, s sacador, d diferencia de distancia recorrida,
     p_id doble falta (el mismo símbolo se usa también para la distancia
     recorrida), sn número de set, p_iu errores no forzados, p_ibm breaks
     fallados.
   - Pesos k «asignados artificialmente» y ajustados a la evolución de la
     semifinal Sinner–Djokovic (p. 4); valores (Tabla 6, p. 9): k1 0,202; k2
     0,397; k3 0,612; k4 0,106; k5 0,099; k6 0,108; k7 0,113; k8 0,120; k9
     −0,142; k10 −0,296; k11 −0,107; k12 −0,098; k13 −0,124. Redondeados y ×10
     (ec. 2 = ec. 9): M_i = 2·p_iw + 4·p_ig + 6·p_is + p_ia + p_inetptwon +
     p_ib + p_ibw + s − d − 3·p_id − sn − p_iu − p_ibm.
   - Variables derivadas: Δm (diferencia de momentum) y Δṁ («variación de la
     diferencia de momentum») (Tabla 1; §3.3).
   - «Independencia» de variables con Kendall/Spearman y prueba de tendencia
     de Mann-Kendall (§2.4.3, pp. 5–6): S = Σ_{i<j} sgn(X_j − X_i);
     Z = (S − 1)/√Var(S) si S > 0, 0 si S = 0, (S + 1)/√Var(S) si S < 0;
     pendiente β = mediana((X_j − X_i)/(j − i)); versión secuencial
     S_k = Σ_{j≤k} r_j, E[S_k] = k(k − 1)/4, Var[S_k] = k(k − 1)(2k + 5)/72,
     UF_k = (S_k − E[S_k])/√Var[S_k], UB_k = −UF_k (ec. 3–8).
   - Random Forest: 100 árboles, profundidad 8, min_samples_split 5,
     min_samples_leaf 2, max_features sqrt (Tabla 2, p. 5). Qué variables
     entran exactamente: no consta. El resumen menciona un algoritmo genético
     y §3.5 una red neuronal; ninguno se describe en el texto.
3. **Datos.** Datos oficiales de Wimbledon 2023, individual masculino,
   «después de la segunda ronda» (p. 3) o «después de la tercera ronda»
   (p. 4); dice «12 partidos entre 12 jugadores» (p. 3), pero analiza 7.284
   muestras (Tabla 8, p. 10). Material suplementario Tabla S1. Para
   «generalizar»: Qatar Open 2017 (pista dura) y un partido de tenis de mesa.
4. **Validación.** Pesos ajustados a mano sobre una semifinal y «predicción»
   del ganador de esa misma semifinal (p. 5: dentro de muestra). Prueba sobre
   la final de Wimbledon 2023 punto a punto (334 puntos) y validación cruzada
   aleatoria de 10 pliegues (Tabla 11). La prueba en pista dura entrena con el
   Qatar Open 2017 y «prueba» en un partido de ese mismo torneo, solo de forma
   visual (pp. 13–15). Referencia: «aprendizaje automático tradicional» sin
   especificar (Tabla 10). **Fuga [nuestro]:** M incluye juegos y sets ya
   ganados (el marcador), winners, errores y breaks: es información del propio
   partido; los pliegues aleatorios mezclan puntos contiguos y
   autocorrelacionados del mismo partido.
5. **Resultados.** Ajuste lineal del momentum en la semifinal: 320 de 334
   puntos «cerca» del ajuste (95,8 %); media real 92,17 frente a 91,25
   ajustada; F = 208; p ≤ 0,001 (Tabla 5, pp. 8–9). Kendall W = 0,035,
   χ² = 254,335, p < 0,001 (Tabla 4). Δṁ (7.284 muestras): media 0,087,
   mediana −0,048, DE 12,288, asimetría 0,143, curtosis 20,152, Shapiro-Wilk
   0,846 (p < 0,001) (Tabla 8). Final de Wimbledon (Tabla 9): umbral 50 % →
   74 % de acierto sin descartes; 55 % → 78,1 % descartando el 5 %; 60 % →
   81,2 % descartando el 34 %; «tradicional» (Tabla 10): 63,4 / 69,8 / 76,4 %
   (descartes 0 / 8 / 28 %). 261 de 334 aciertos. Validación cruzada de 10
   pliegues (Tabla 11): de 73,1 % a 82,9 %.
6. **Límites.** Declarados (p. 18): el momentum lineal se basa en factores muy
   correlados y omite no linealidades; los k cambian con la sede. Detectados
   **[nuestro]**:
   - Circularidad: los pesos se ajustan a la evolución de un partido y luego
     se «predice» ese partido.
   - El objetivo es el ganador de cada punto de un solo partido (la final); no
     es pronóstico de partidos.
   - Incoherencias: 12 partidos frente a 7.284 puntos (saldrían ≈ 607 puntos
     por partido); 2.ª frente a 3.ª ronda; el texto atribuye la carga 0,929 a
     «puntos ganados por el jugador 1» y la Tabla 3 a «setno»; signos de k9–k13
     restados dos veces en la ec. 1; el significado de k cambia entre la ec. 1
     y §3.5 (p. ej., k3 = sets ganados en la ec. 1 y «saques ganados» en p. 14;
     k10 = dobles faltas en la ec. 1 y «desgaste por sets» en p. 14); dice que
     la validación cruzada queda entre 75 % y 80 % y su tabla va de 73,1 % a
     82,9 %; las conclusiones afirman que una t de Student ajusta mejor cuando
     en resultados solo se especula.
   - Mal uso de pruebas: Mann-Kendall contrasta tendencia, no independencia;
     comunalidades bajas no significan «contribuciones independientes»; W de
     Kendall mide concordancia entre evaluadores.
   - Elegir el umbral de 55 % mirando la propia prueba y descartar
     predicciones dudosas infla la exactitud.
7. **¿Replicable con nuestros datos?** El recuento de sucesos por punto, sí,
   con el Match Charting Project (winners, aces, errores no forzados, red,
   break points); la distancia recorrida, no. No hay nada que trasladar a un
   pronóstico pre-partido.
8. **Mercado.** Ninguno pre-partido; como mucho «siguiente punto» en vivo.
9. **Transversales.** Momentum: lo define y lo afirma, pero no contrasta IID
   frente a una referencia (p. ej., un modelo de puntos i.i.d. con
   probabilidad de saque constante). Superficie: la ajusta cambiando pesos a
   mano (Tabla 12). Sin ratings, fatiga ni mercado.

### T16 — «Sistema de captura y predicción de momentum» con entropía, análisis gris, XGBoost y SHAP (Wimbledon 2023)

1. **Referencia.** T16. Chang Liu, Tongyuan Yang, Yan Zhao (Beijing Normal
   University). Preprint arXiv:2408.01544v1 [cs.LG], 2-ago-2024. No revisado,
   20 pp. Por su estructura («Task 1–4», archivo
   «Wimbledon_featured_matches.csv») es la memoria de una solución del
   concurso MCM 2024 de COMAP [nuestro].
2. **Modelo.**
   - Pesos por entropía (§4.1, ec. 1–6, pp. 5–6): x_ij = (x̃_ij − min_i
     x̃_ij)/(max_i x̃_ij − min_i x̃_ij) + ε; p_ij = x_ij/Σ_i x_ij;
     e_j = −(1/ln n)·Σ_i p_ij·ln p_ij; ω̃_j = (1 − e_j)/Σ_i(1 − e_i); «factor
     de ventaja de saque» ω′_j = ω̃_j + ξ si j = 1 y ω̃_j en otro caso, con
     ξ ∈ [0,05; 0,15] y ξ = 0,1; ω_j = ω′_j/Σ_j ω′_j; n = 62 objetos
     (jugador-partido) y m = 10 indicadores.
   - Indicadores (Tabla 2, p. 4, leída en orden): ventaja de saque, aces,
     errores no forzados, ventaja en puntos, distancia recorrida, juegos y
     sets ganados, profundidad del resto, profundidad del saque, velocidad de
     recepción, frecuencia de derechas.
   - Análisis relacional gris (§4.2, ec. 7–13, pp. 6–7): referencia X0 =
     margen de puntuación; x′_i(k) = x_i(k)/media_i;
     Δ_i(k) = |x′_0(k) − x′_i(k)|; γ_0i(k) = (mín + ξ·MÁX)/(Δ_i(k) + ξ·MÁX)
     con ξ = 0,5 (el mismo símbolo que el factor de saque);
     Γ_0i = Σ_k ω_i·γ_0i(k). Puntuación de rendimiento S = Σ_i Γ_0i·x_i con
     ventana deslizante de 10 puntos (ec. 14).
   - «Momentum» = tendencia de S suavizada (§5.1, ec. 15, p. 9):
     EMA_t = [y_t + (1 − α)·y_{t−1} + … + (1 − α)^t·y_0] / [1 + (1 − α) + … +
     (1 − α)^t], con α = 0,9 y «periodo» de 10.
   - «Prueba de aleatoriedad» (§5.2): 1.000 conjuntos simulados «sin
     momentum» con probabilidades presupuestas (cuáles: no consta) frente a
     los 62 reales; Mann-Whitney U (U = mín{U1, U2},
     U1 = n1·n2 + n1(n1 + 1)/2 − R1) y Kolmogorov-Smirnov
     (D = sup|F1 − F2|).
   - XGBoost en regresión con todas las variables del archivo como entradas y
     la puntuación S del modelo 1 en el conjunto de datos; SHAP para explicar
     (§6, pp. 11–14). Hiperparámetros: no constan.
3. **Datos.** Archivo del concurso con partidos de Wimbledon 2023 masculino
   (n = 62 jugador-partido, compatible con 31 partidos [nuestro]); para
   «generalizar», estadísticas de las webs oficiales de Roland Garros y Open de
   Australia 2023 (masculino) y de Wimbledon y US Open (femenino; año: no
   consta) (Tabla 1, p. 4; §7.1, p. 15). Supuesto 3: no usa historia previa de
   los jugadores, solo el propio partido (p. 3).
4. **Validación.** División 7:3 entrenamiento/prueba (aleatoria o temporal: no
   consta) y prueba en la final Alcaraz–Djokovic (p. 12). Qué es exactamente
   la variable objetivo («swings», «fluctuations») y cómo se define
   «accuracy» en una regresión: no consta. **Fuga [nuestro]:** S se calcula
   con las mismas variables del partido que entran al XGBoost (ventana de 10
   puntos), así que el modelo reconstruye una transformación de sus propias
   entradas; las cifras ≈ 0,999 lo reflejan. Sin referencia externa.
5. **Resultados.** Mann-Whitney p = 0,0043; Kolmogorov-Smirnov p = 0,00128
   (pp. 10–11). «Exactitud» 0,9990134 en varios partidos y 0,992738 en la final
   (p. 12). SHAP: distancia recorrida de ambos, 0,1077 y 0,1042 (resumen; la
   Tabla 4 de p. 13 sale desalineada). Generalización (p. 16): Roland Garros
   masculino 0,9112; Open de Australia masculino 0,9467; Wimbledon femenino
   0,9651; US Open femenino 0,8620. Estabilidad frente a ξ: varianza extrema
   0,02579 y varianza de la diferencia 0,00058 (p. 17). La Tabla 3 (pesos y
   grados grises) no es reconstruible con seguridad desde la extracción.
6. **Límites.** Declarados (§9.2, p. 18): exige datos de calidad; supuestos
   estrictos; faltan factores psicológicos. Detectados **[nuestro]**:
   - Objetivo construido con las entradas: el 0,999 no mide capacidad de
     pronóstico.
   - La «prueba de aleatoriedad» compara con datos simulados cuyas
     probabilidades presupone el autor: rechazar H0 solo dice que la
     simulación no se parece a los datos.
   - Interpreta SHAP grande como «modelo menos estable» (p. 17) y una
     generalización alta como «robustez»; el mismo símbolo ξ para dos cosas.
   - Consejos tácticos (pp. 16–17) que no se derivan de ningún resultado.
7. **¿Replicable con nuestros datos?** No: distancia recorrida, velocidad y
   profundidades no las tenemos, y no hay nada pre-partido.
8. **Mercado.** Ninguno pre-partido.
9. **Transversales.** Saque: lo trata con un peso ad hoc ξ = 0,1; momentum:
   definido como tendencia de una puntuación de rendimiento, sin contraste
   frente a puntos i.i.d.; superficie y sexo: solo como «generalización».
