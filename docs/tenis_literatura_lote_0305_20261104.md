# Tenis — literatura, lote 03 + 05: mercados y cuotas; documentos complementarios

Fecha: 2026-11-04. Rediseño desde cero del motor de tenis ATP/WTA con enfoque en
**probabilidad calibrada** (no en ganar a las cuotas). Lote: los 6 PDF de
`BIBLIOTECA_TENIS_COMPLETA/pdfs/03_mercados/` y los 6 de `pdfs/05_complementos/`
(índice `INDICE_COMPLETO.txt` y `catalogo_completo.json`: solo metadatos; si
contradicen al artículo, manda el artículo y se anota en la sección (d)).

Método: texto extraído con `pdftotext -layout` y leído completo por tramos. Cada
afirmación cita página (número impreso en el PDF cuando lo hay; si no, página del
PDF) o sección del propio documento. «No consta» = el documento no lo dice. Lo que
es inferencia nuestra (no del autor) va marcado como **[nuestro]**.

Nuestros datos de referencia para la columna «replicable»: resultados con marcador
por set y tiebreak, ranking/puntos, superficie, ronda y nivel; cuotas de cierre del
mercado de ganador (Pinnacle, bet365, Max, Avg; Tennis-Data); otras cuotas parciales
(The Odds API, PropLine —calificación defectuosa en tenis—, BetsAPI); **sin**
estadísticas sistemáticas de saque/resto.

Estado: en redacción (las fichas se añaden al terminar cada estudio).

## (a) Tabla resumen

(se completa al final)

## (b) Fichas por estudio

### A30 — Inferir el marcador desde el mercado en vivo de un exchange

1. **Referencia.** A30. Dumitrescu, Huang, Knottenbelt, Spanias, Wozniak (Imperial
   College London). Ponencia, 4th Mathematics in Sport Conference (Lovaina), 2013
   según el índice; el PDF no imprime el año. 9 páginas (pp. 87–95 de las actas).
2. **Modelo/método.**
   - Modelo de Markov jerárquico punto → juego → set → partido (Liu 2001, Barnett y
     Clarke 2002), puntos i.i.d. (justificado con Klaassen y Magnus 2001: la
     desviación existe pero es pequeña), con PWOS = probabilidad de ganar un punto
     al saque, distinta para cada jugador (§2, pp. 88–89).
   - Nivel partido (al mejor de 3): con p = P(A gana un set),
     P(gana | 1-1) = p·1 + (1−p)·0 y P(gana | 1-0) = p·1 + (1−p)·P(gana | 1-1).
     Nivel set: pA en los juegos que saca A y 1−pB en los que saca B; desde 6-6 se
     usa p′ = P(A gana el tiebreak). Juego, set con ventaja y tiebreak comparten
     el «paseo aleatorio con dos estados absorbentes» (hace falta ganar dos seguidos
     desde la igualdad) (pp. 88–89). Las ecuaciones del PDF son imágenes y **no se
     extraen como texto**; el texto describe la serie geométrica desde el deuce
     (volver al deuce con prob. 2p(1−p), infinitas veces), cuya forma estándar es
     P(gana desde deuce) = p² / (1 − 2p(1−p)) **[nuestro: reconstrucción]**.
   - **Cuota → probabilidad** (§3.1, p. 90): P = 1/cuota decimal; cuando la suma
     supera 100 % (ejemplo Federer–Del Potro, JJOO 2012: 1,46 y 3,0 → 68,49 % +
     33,33 % = 101,8 %) «los valores se normalizan para que sumen 100 %», es decir,
     **de-vig proporcional** (división por la suma). En Betfair el exceso se
     atribuye al redondeo del cruce de apuestas, no a un margen de casa.
   - **PWOS adaptado al mercado** (§3.2, p. 90): suma media de PWOS 1,29 en hombres
     y 1,12 en mujeres «con poca varianza» (citando a Klaassen y Magnus 2001); la
     probabilidad de partido depende de la diferencia de PWOS, no del nivel absoluto
     (citando a O'Malley 2008). Pivote masculino 0,645:
     PWOS(A) = 0,645 + d/2, PWOS(B) = 0,645 − d/2; d se obtiene por búsqueda
     binaria hasta que la probabilidad del modelo, dado el marcador actual, iguala la
     probabilidad implícita normalizada (pseudocódigo p. 91). Pivote femenino: no
     consta (por analogía sería 1,12/2 = 0,56 **[nuestro]**).
   - Inferencia del punto (§3.3–3.4): se usa el «último precio casado» (LPM); se
     fijan umbrales alrededor de las probabilidades esperadas si el próximo punto se
     gana o se pierde; si la cuota cruza un umbral se anota el punto y se recalibra
     el PWOS. Heurísticas: volatilidad = rango intercuartílico de la cuota en los
     últimos 10 s (umbral más ancho si hay más volatilidad); detección de cambios
     grandes, bruscos y sostenidos; resincronización en cambios de saque y fin de
     set; espera mínima de 8 s entre puntos (p. 94).
3. **Datos.** API de Betfair, mercado Match Odds, captura «cada segundo o así»
   durante todo el partido (p. 90). Puntos recogidos a mano y sincronizados con el
   mercado (p. 93). Partidos citados: Federer–Del Potro (JJOO 2012),
   Schiavone–Bartoli (RG 2011), Wozniacki–Pennetta (Doha 2011), Troicki–Djokovic
   (Miami 2011) y el caso de estudio Cilic–Baghdatis (Rogers Cup 2012). Número total
   de partidos evaluados: no consta. Cuota: en vivo (no apertura ni cierre).
4. **Validación.** No hay métrica agregada (ni tasa de acierto de puntos, ni Brier,
   ni log-loss). Solo un caso de estudio cualitativo (§4).
5. **Resultados.** En Cilic–Baghdatis los puntos se detectan bien hasta 5-4 del
   primer set; después se pierde un punto clave por movimiento insuficiente de la
   cuota y el error se encadena: real 7-5 6-3, inferido 6-4 5-3 (pp. 94–95). Unos
   dos tercios de los puntos inferidos salen del cruce de umbral y el resto de la
   detección de cambios grandes (p. 93).
6. **Límites.** Declarados: falsos positivos y puntos perdidos que se propagan y
   «descarrilan» el marcador; el mercado se mueve sin punto (p. ej. un smash fallado
   en Schiavone–Bartoli, p. 92); depende de liquidez. Detectados: evidencia
   anecdótica (un partido documentado), sin tasas de error, sin muestra declarada.
7. **¿Replicable con nuestros datos?** La inferencia del marcador, **no** (exige
   cuotas de exchange segundo a segundo y punto a punto con hora). Sí es replicable
   la pieza «PWOS implícito»: con la probabilidad de cierre del ganador sin margen
   y el marcador 0-0 se puede resolver la diferencia de PWOS y, con el modelo de
   Markov, derivar probabilidades de sets, juegos, tiebreak y marcador exacto
   **[nuestro: el artículo no hace esta derivación ni la valida]**.
8. **Mercado.** Ganador en vivo; indirectamente, todos los derivados del marcador.
9. **Qué enseña.** De-vig proporcional como conversión por defecto; la probabilidad
   de partido se puede reparametrizar como una diferencia de PWOS alrededor de un
   pivote por circuito (1,29/2 hombres), lo que da una vía coherente para pasar de la
   cuota de ganador a mercados de marcador. Nada sobre calibración ni sobre reglas
   de liquidación (retiradas/walkovers): no consta.

### T30 — «Not feeling the buzz»: réplica y corrección de una estrategia WTA basada en Wikipedia

1. **Referencia.** T30. Clegg y Cartlidge (Universidad de Bristol). Estudio de
   réplica/corrección de Ramirez, Reade y Singleton (2023, IJF). Copia leída: arXiv
   2306.01740v4, 11-jul-2024, 24 pp. (versión publicada en IJF 2025 según el índice;
   no se ha cotejado con la versión editorial).
2. **Modelo/método.**
   - Marco de Mincer–Zarnowitz sobre el error de la probabilidad implícita (ec. 1,
     p. 4): e_ij = α + β1·z_ij + β2·RankDist_ij + β3·WikiBuzz_ij + S(j) + T(j) + ε_ij,
     con e = distancia entre la probabilidad implícita y el resultado (1 si gana,
     0 si pierde), efectos fijos de temporada y errores agrupados por torneo y
     partido; MCO. (Las letras griegas se pierden en la extracción; se reconstruyen
     por el texto.)
   - **Cuota → probabilidad sin quitar margen** (ec. 2, p. 5): z_ij = 1/cuota_ij con
     la cuota **media** de las casas; por tanto z_ij + z_ji = 1 + K > 1 (K =
     margen). Los autores citan como alternativas Shin (1993) y Štrumbelj (2014),
     pero no las aplican.
   - RankDist_ij = 1/rank_i − 1/rank_j (ec. 3; sin ranking → inverso 0).
     WikiBuzz_ij = ln(w_i/w̃_i) − ln(w_j/w̃_j), con w = visitas del día anterior y
     w̃ = mediana diaria del último año (ec. 4; ejemplo Collins–Ostapenko 2018:
     6,93, Apéndice A).
   - Modelo de resultado (ec. 5–6, p. 7): ŷ_ij = α + (1+β1)·z_ij + β2·RankDist +
     β3·WikiBuzz (lineal). Apuesta con Kelly (ec. 7):
     f_ij = max(ŷ_ij − (1−ŷ_ij)/b_ij, 0), b = cuota − 1, banca reiniciada a 1 en cada
     apuesta; ROI = Σ beneficio / Σ apostado (ec. 9). Significación de rendimientos:
     p_bs de Wunderlich y Memmert (2020) = proporción de 100.000 estrategias
     aleatorias con el mismo nº de apuestas que igualan o superan el rendimiento.
3. **Datos.** Tennis-Data (tennis-data.co.uk), **WTA**, julio-2015 a febrero-2020
   (réplica), con cuotas prepartido de Bet365, media y máxima de 40–60 casas
   (oddsportal) y visitas de Wikipedia (pp. 3–4). Extensión depurada: 35.274
   filas jugador-partido, 17.751 partidos, 584 jugadoras, 3-jul-2015 a 31-ago-2023
   (§4.1, p. 13; Apéndice D). Instante de la cuota: «prepartido» (Tennis-Data); el
   artículo no precisa apertura/cierre.
4. **Validación.** Temporal: ajuste 2016–2018 (el pie de la Tabla 1 dice 2015–2018)
   y prueba fuera de muestra enero-2019 a febrero-2020; extensión fuera de muestra
   hasta agosto-2023 con los coeficientes originales y reestimación en
   feb-2020/ago-2023 (§4). Métricas: coeficientes y p-valores, ROI, rendimiento
   absoluto, p_bs. Sin Brier, log-loss ni calibración.
5. **Resultados.**
   - Réplica exacta de RRS (Tabla 1, 15.854 jugador-partido, 2015–2018): modelo PM
     β1 (probabilidad implícita) = 0,025 (EE 0,029), β2 (RankDist) = 0,055 (0,029),
     β3 (WikiBuzz) = 0,009 (0,004), α = −0,043 (0,015); sin RankDist: β1 = 0,005
     (0,026), β3 = 0,010 (0,004), α = −0,033 (0,014). La constante negativa recoge el
     margen de la cuota bruta; la pendiente de z no es significativa.
   - **Error de datos «Hercog»** (Miami 2019, Hercog–Doi): Tennis-Data trae Bet365 =
     5,50 cuando la máxima del mercado es 2,10 y la media 1,85 (pp. 9–10; nota 11:
     en WTA 2019, 2.453 filas, cuota Bet365 del ganador entre 1,01 y 9, media 1,84,
     DE 0,80). Kelly apostó el 39,3 % de la banca a esa fila.
   - Bet365, fuera de muestra (Tabla 2): PM 312 apuestas, ROI 17,29 % → **−7,36 %**
     sin Hercog; PM sin RankDist 276 apuestas, ROI 28,82 % → **−6,31 %**. Margen
     medio Bet365 = 6,46 %.
   - Selección por competitividad (Tabla 3): p ∈ [0,2; 0,8] ROI 18,13 % → −3,36 %;
     **p ∈ [0,4; 0,6] ROI 29,38 % → 12,44 %** (262 apuestas, p_bs = 0,002). Margen
     medio Bet365: 6,58 % en [0,2; 0,8] y 7,01 % en [0,4; 0,6]; 5,70 % en partidos
     muy desequilibrados (Tabla C.7).
   - Extensión (Fig. 2b, §4.2): **ningún beneficio adicional después de febrero de
     2020**. Reestimación feb-2020/ago-2023 (Tabla 4, 13.913 filas): β1 = 0,039
     (p = 0,148), RankDist 0,021 (p = 0,471), WikiBuzz 0,001 (p = 0,837), α = −0,046
     (p = 0,001).
   - Mejor cuota del mercado (Tabla B.6): margen medio −0,24 % (la suma de las
     máximas queda por debajo de 1), 2.350 apuestas, ROI 3,05 %; los autores (con
     RRS) advierten que apostar a la mejor cuota justo antes del partido «no es
     realista».
6. **Límites.** Declarados: posible error también en los datos de Wikipedia; la
   pérdida de rentabilidad tras 2020 puede deberse a otros factores; los
   rendimientos de apuestas no miden la precisión de un modelo (cita a Wunderlich y
   Memmert 2020) y son muy sensibles a cuotas atípicas. Detectados: modelo de
   probabilidad lineal (sin acotar a [0,1]); probabilidad implícita con margen;
   ningún indicador de calibración; solo WTA.
7. **¿Replicable con nuestros datos?** Sí en lo esencial: la fuente (Tennis-Data,
   Bet365/Avg/Max) es la nuestra, y la regresión de Mincer–Zarnowitz del error de
   la probabilidad implícita sobre z se puede correr ya para medir el sesgo
   favorito–no favorito. WikiBuzz no (no tenemos visitas de Wikipedia). Los cuatro
   filtros de limpieza del Apéndice D se pueden aplicar tal cual.
8. **Mercado.** Ganador del partido (WTA).
9. **Qué enseña.** (i) **Control de calidad de cuotas obligatorio en Tennis-Data**:
   descartar filas con cuota de una casa > máxima del mercado, cuotas ausentes y
   filas cuya diferencia entre probabilidad implícita máxima y media supere 4 DE
   (DE = 0,014) (Apéndice D: 32, 174 y 200 filas eliminadas). (ii) La cuota media es
   un predictor muy fuerte por sí misma y un modelo puede «ganar» solo por cuotas
   atípicas (§5). (iii) El margen de Bet365 en WTA ronda el 6–7 % y es mayor en
   partidos igualados. (iv) Evaluar con métricas de probabilidad, no con ROI.
   Retiradas/walkovers: no consta.

### T27 — Dominancia intransitiva con redes neuronales de grafos (versión 2)

1. **Referencia.** T27. Clegg y Cartlidge (Universidad de Bristol). Preprint arXiv
   2510.20454v2, 18-jun-2026, 41 pp. Versión revisada de S02 (v1); cuentan como un
   solo trabajo.
2. **Modelo/método.**
   - Un grafo dirigido por circuito y superficie (dura, tierra, hierba) en cada
     «instantánea» = ronda de torneo (§4.1). Nodos = jugadores; rasgos de nodo =
     grados de entrada/salida normalizados (talla, peso, edad y mano se probaron y se
     descartaron, §4.5).
   - Puntuación de dominio (ec. 3, p. 11):
     D_n^s(u,v) = Σ_k ρ_{s,s_k}·ω_k·λ_k·g_k(u,v) / Σ_k ρ_{s,s_k}·ω_k·λ_k, con
     g_k = proporción de **juegos** ganados por u ante v en el partido k (mejor que
     sets o puntos en validación), λ_k = exp(−λ·(τ_n − τ_k)) (ec. 2), ρ = similitud
     entre superficies y ω = prestigio del torneo (al final uniforme, ω = 1). Arista
     de u a v con peso D si D > 0,5; de v a u con peso 1−D si D < 0,5.
   - Red MagNet (Zhang et al. 2021): convolución espectral con el laplaciano
     magnético normalizado L_N(q) = I − D_s^{−1/2} A_s D_s^{−1/2} ⊙ exp(iΘ(q)),
     Θ(q)(u,v) = 2πq(A(u,v) − A(v,u)), filtros de Chebyshev de orden K, salida
     softmax promediada en los dos órdenes del par (A.1–A.8). Se predice la
     **probabilidad de ganar un set** p̂ (entropía cruzada, Adam, lr 1,8·10⁻³).
   - Del set al partido con sets i.i.d. (ec. 4, p. 14):
     P̂3 = p̂² + 2p̂²(1−p̂); P̂5 = p̂³ + 3p̂³(1−p̂) + 6p̂³(1−p̂)².
   - Hiperparámetros elegidos (Tabla 2, p. 16): K = 1, 2 capas, 16 unidades, sin
     activación, q = 0,24 (texto: 0,238), decaimiento λ = 0,34 (unidad de tiempo no
     consta), edad máxima de arista 1,55, percentil mínimo de dominio 0,10,
     transferencia simétrica dura–tierra 0,41, dura–hierba 0,22, tierra–hierba 0,40.
   - **Referencia de mercado: Pinnacle con de-vig de Shin (1993)**, elegido porque
     Štrumbelj (2014) lo halla más preciso que la normalización básica (§5, p. 19).
   - Comparación: Elo (Morris y Bialik 2015), Weighted Elo (Angelini et al. 2022),
     Bradley–Terry (ventana móvil de 2 años, máxima verosimilitud regularizada).
   - Recalibración de Platt del WElo (ec. 5): logit p̂ = a0 + a1·logit WElo, con
     â1 < 1; prueba de inclusión («encompassing», ec. 6):
     logit p̂ = b0 + b1·logit WElo + b2·logit G; Diebold–Mariano unilateral; McNemar.
     Intransitividad: conteo de tríadas cíclicas T_h y medida de Hodge ponderada por
     evidencia (Apéndice C).
3. **Datos.** Tennis-Data, ATP y WTA, 8-ene-2012 a 16-oct-2025, solo Grand Slams,
   Finales, Masters/WTA 1000 y 500 (§3, p. 8). Cuota de **Pinnacle** (elegida por
   disponibilidad constante y por ser casa «sharp»); el texto llama a esas cuotas
   «closing odds» de Pinnacle en §6.2 (p. 24). 20.181 partidos masculinos (670
   jugadores) y 19.985 femeninos (640). Atributos físicos de tennisexplorer.com.
4. **Validación.** Temporal y sin fuga declarada: serie cronológica en tres tramos;
   validación 8.435 partidos (ATP 31-jul-2018 a 21-feb-2022; WTA 28-ago-2018 a
   12-mar-2022) para 250 pruebas de TPE (Optuna) y la ablación; **prueba fuera de
   muestra 12.052 partidos (2022 a oct-2025) no usados en el ajuste** (§3, §4.4).
   Ventana deslizante: grafo con el 85 % más antiguo, entrenamiento con el 15 % más
   reciente, reentrenamiento cada 38 instantáneas (≈ trimestre) (§4.3). Métricas:
   acierto, **Brier**, curvas de calibración (agrupación recursiva) y descomposición
   de Murphy corregida por sesgo.
5. **Resultados** (Tabla 4, p. 19; prueba 12.052 partidos):
   | Modelo | Acierto | Brier |
   |---|---|---|
   | GNN (MagNet) | 0,657 | 0,214 |
   | Weighted Elo | 0,658 | 0,214 |
   | Elo | 0,653 | 0,217 |
   | Bradley–Terry | 0,646 | 0,219 |
   | **Pinnacle (Shin)** | **0,687** | **0,198** |
   Por segmento, Pinnacle: hombres tierra 0,190, hierba 0,185, dura 0,199; mujeres
   tierra 0,192, hierba 0,207, dura 0,205 (Brier). Calibración (§5.1): término de
   fiabilidad < 0,0001 (GNN) frente a 0,0012 (WElo); resolución 0,035 frente a
   0,036. Platt sobre WElo: Brier 0,2142 → 0,2130 (WElo crudo **sobreconfiado**).
   Combinación WElo + GNN: 0,2113 (DM p < 0,001; b̂2 = +0,498) (p. 24). Elo por
   superficie y Bradley–Terry no añaden nada a WElo recalibrado (p = 0,28 y 0,78).
   **El mercado incluye al modelo**: añadir la GNN a Pinnacle recalibrado no mejora
   el Brier (DM p ≥ 0,47) (p. 25). El 58,2 % de los partidos de prueba enfrenta a
   jugadores que nunca se habían visto (Tabla 7); en mujeres hay un 12,3 % más de
   tríadas cíclicas (14,91 % frente a 13,27 %).
6. **Límites.** Declarados: queda claramente por detrás del mercado (0,214 frente a
   0,198); menos interpretable que WElo; pierde información al resumir el historial
   en un peso de arista; sin valor añadido sobre Pinnacle. Detectados: solo torneos
   de nivel alto (500 o más); la unidad del decaimiento no consta; un único reparto
   temporal (sin repeticiones); el modelo de sets i.i.d. no se valida contra
   marcadores reales.
7. **¿Replicable con nuestros datos?** Sí: usa exactamente Tennis-Data con juegos
   por set, superficie, ronda y Pinnacle. La puntuación de dominio por proporción de
   juegos y el WElo recalibrado con Platt son baratos de reproducir; la GNN exige
   PyTorch Geometric Signed Directed.
8. **Mercado.** Ganador. Como modela la probabilidad de ganar un set, da también
   «1.er set» y «resultado exacto en sets» bajo sets i.i.d. **[nuestro]**.
9. **Qué enseña.** (i) Referencia de mercado = Pinnacle con Shin; es el listón
   (Brier ≈ 0,198 en nivel 500+ 2022–2025). (ii) Medir con Brier + descomposición
   de Murphy (fiabilidad/resolución) y curvas de calibración; la combinación de
   pronósticos se prueba con encompassing + Diebold–Mariano, no con ROI. (iii) Los
   Elo crudos están sobreconfiados: hay que recalibrarlos (Platt) antes de
   publicarlos. (iv) El margen de victoria en **juegos** es la señal de dominio más
   útil. Retiradas/walkovers: el artículo solo dice que elimina «partidos
   incompletos» (§3); no detalla el criterio.

### S02 — Versión 1 del trabajo de grafos (con simulación de apuestas, ya superada)

1. **Referencia.** S02. Clegg y Cartlidge. arXiv 2510.20454v1, 23-oct-2025, 39 pp.
   Versión anterior de T27: **no es un estudio independiente**.
2. **Modelo/método.** El mismo esquema que T27 (dominio por proporción de juegos,
   MagNet, sets i.i.d. con la ec. 4) con diferencias: rasgos estáticos de nodo
   incluidos (talla, peso, fecha de nacimiento, mano; Tabla 2), q fijo en 0,25,
   suavizado de etiquetas 0,19 para evitar sobreconfianza, lr 0,003, 300 pruebas de
   TPE; K = 2 y 2 capas (4 saltos) (§4.2–4.4). Hiperparámetros (Tabla 3, p. 15):
   decaimiento 0,38; transferencia **asimétrica** entre superficies (de tierra a
   dura 0,01; de hierba a dura 0,37; de dura a hierba 0,45; resto 0,05–0,09);
   prestigio 1000 = 0,85, Finales = 0,94, 500 = 0,69 (Grand Slam = 1). Pinnacle con
   Shin como referencia. Apuestas: Kelly f* = (p̂·o − 1)/(o − 1) con banca reiniciada
   a 1 (ec. 11), apuesta unitaria al favorito del modelo, Sharpe anualizado =
   media/DE del beneficio diario × √365,25 (ec. 12); significación p_bs (Wunderlich y
   Memmert 2020) con 10.000 simulaciones y Bonferroni.
3. **Datos.** Tennis-Data ATP/WTA 1-ene-2014 a 8-jun-2025, nivel 500 o más; 16.663
   partidos masculinos (598 jugadores) y 16.447 femeninos (567) (§3, p. 8). Cuota
   de Pinnacle (instante: no consta en esta versión).
4. **Validación.** Temporal: ajuste con predicciones del 29-ago-2019 al
   20-nov-2022; prueba 1-ene-2023 a 8-jun-2025 (8.375 partidos). El umbral de
   intransitividad τ = 2,55 se eligió en validación (ROI Kelly 1,97 % en 1.687
   apuestas). Bootstrap por jugador (10.000 remuestreos) y Spearman para la
   tendencia (§6.2).
5. **Resultados.** Tabla 4 (p. 19): GNN 0,657 / Brier 0,215; WElo 0,664 / 0,212; Elo
   0,658 / 0,215; BT 0,648 / 0,217; **Pinnacle (Shin) 0,690 / 0,196** (por segmento:
   hombres hierba 0,176; mujeres dura 0,201). Tabla 5: el Brier de Pinnacle empeora
   con la intransitividad (0,193 sin historial directo → 0,209 en el tercil alto) y
   la desventaja de la GNN frente a Pinnacle se reduce de +0,023 a +0,007. Tabla 6
   (prueba): con τ ≥ 2,55, Kelly 1.903 apuestas, ROI **3,26 %**, Sharpe 0,61
   (p_bs = 0,005); unitaria 2.063 apuestas, ROI 1,14 % (p_bs = 0,022). Sin filtro:
   Kelly −5,49 % (7.705 apuestas), unitaria −1,64 %. WElo con el mismo filtro:
   Kelly −5,54 %, unitaria −3,38 %. Modelo preliminar (Apéndice B): ROI 7,66 % →
   2,57 % y Brier 0,218 → 0,225 al ampliar la muestra.
6. **Límites.** Declarados: queda por detrás del mercado (0,215 frente a 0,196);
   rentabilidad dependiente de la calidad de las cuotas históricas (cita a T30).
   Detectados: (i) **T27 (v2) contradice la tesis de ineficiencia**: allí Pinnacle
   recalibrado incluye al modelo también en los partidos intransitivos (DM
   p ≥ 0,47) y se elimina toda la parte de apuestas; (ii) la nota de la Tabla 5
   llama «validación» a cifras que coinciden con la prueba (N = 8.375); (iii) WElo
   aparece como 66,4 % en §5 y 66,5 % en la conclusión; (iv) no consta si los pagos
   simulados usan la cuota bruta de Pinnacle o la ajustada por Shin (§5: «estas
   cuotas también se usan» para la simulación); (v) los hiperparámetros de
   transferencia entre superficies cambian de forma drástica entre v1 y v2 (de
   tierra a dura 0,01 frente a 0,41), señal de que están mal identificados; (vi) la
   diferencia por sexo en intransitividad (11,5 % más en mujeres con la medida I) no
   se reproduce en v2 con esa misma medida (2,77 frente a 2,74).
7. **¿Replicable con nuestros datos?** Sí (mismos datos que T27), pero no tiene
   sentido replicar la simulación de apuestas: la propia revisión la retira.
8. **Mercado.** Ganador.
9. **Qué enseña.** Útil como contraejemplo: una ventaja de ROI elegida por umbral
   en validación (τ) desaparece cuando se contrasta con una prueba de inclusión
   frente al mercado. Para nosotros: evaluar con Brier/log-loss y pruebas de
   inclusión, nunca publicar «ventaja» por ROI. Retiradas/walkovers: solo «se
   eliminan partidos incompletos» (§3).

### T28 — Pronóstico de las cuotas de las casas con un grafo dinámico

1. **Referencia.** T28. Penn, Michael y Bhatt (Universidad de Copenhague; Imperial
   College). Preprint arXiv 2508.15956v1, 21/25-ago-2025, 15 pp. Código:
   github.com/mpenn114/rss-wimbledon-2025.
2. **Modelo/método.**
   - **De-vig** (ec. 3, p. 8, y §2.1.2, p. 3): «cuotas medias del conjunto de datos
     normalizadas con una constante multiplicativa para que sumen 1» = de-vig
     **proporcional** de la cuota **media** (Avg). La ec. 3 aparece como
     p = d/‖d‖₁ con d = «cuotas»; tomada literalmente invertiría el favorito, así que
     se interpreta como normalización de las probabilidades implícitas.
   - Supuesto: la casa se comporta «como si» usara un Elo dinámico por superficie
     (ec. 4): P(a gana a b) = 1/(1 + 10^(r_b − r_a)). Log-cuota transformada
     (ec. 5): x_ab = r_a − r_b, es decir, el logit en base 10 de la probabilidad sin
     margen (la extracción deja ambiguo el orden de la fracción; la forma coherente
     con la ec. 4 es log10(p/(1−p))). Aditividad: x_ab = x_ac + x_cb (ec. 6).
   - **Mejor de 5 → mejor de 3** (ec. 7, p. 8): con sets independientes se resuelve
     π tal que P(Bin(N_s, π) > N_s/2) = p_ab, para expresar las cuotas de Grand Slam
     masculino como probabilidad de set y llevarlas a 3 sets.
   - Grafo completo dirigido y ponderado: arista E_ab = media ponderada de las
     log-cuotas históricas, pesos w_ab(M) = γ^{t_M}·σ_s (t_M = días transcurridos,
     σ_s = peso de superficie) (ec. 9–11), con actualización recursiva
     W_ab ← γ^t·W_ab + w(M) (ec. 12–13). Apéndice (Teorema 1): el decaimiento
     **geométrico es el único** compatible con actualizar sin guardar el historial.
   - Ratings: mínimos cuadrados ponderados f(r) = Σ W_ab·((r_a − r_b) − E_ab)²
     (ec. 14), convexo (Gershgorin), L-BFGS-B. Libertad de una constante; problema de
     componentes desconectadas (proponen un prior) (§3.3).
   - Pesos de superficie por búsqueda en rejilla «relativamente insensible»; **los
     valores de γ y σ_s no se publican** (§3.4).
3. **Datos.** Tennis-Data (alldata), resultados, ranking y cuota media; 25
   jugadores del cuadro de Wimbledon 2025 sin partidos previos (se les asigna el
   peor ranking del torneo) (§2.1). Prueba: 7 Grand Slams (AO, RG, Wimbledon y USO
   2024; AO, RG y Wimbledon 2025), hombres y mujeres, 1.684 partidos (§2.2).
   Instante de la cuota: la de Tennis-Data (no se precisa apertura/cierre).
4. **Validación.** Pronóstico previo al torneo para todo el cuadro; se descartan
   los partidos en que el modelo da el mismo rating a ambos (media 13 por torneo).
   Métrica: **solo acierto** (y una correlación con la casa en Wimbledon 2025);
   prueba bilateral de proporciones. Sin Brier, log-loss ni calibración. No consta
   si el modelo se actualiza dentro del torneo ni un ajuste separado de γ/σ fuera
   de la muestra de prueba.
5. **Resultados.** Wimbledon 2025: ranking 171/252, modelo 182/252, casas 176/252
   (no significativo). Con datos de ambos jugadores, correlación ≈ 0,88 con la
   probabilidad de la casa, recta y = 0,88x + 0,08 (p. 4). Siete Grand Slams:
   **casas 1.249/1.684 (74,1 %), modelo 1.237 (73,5 %), ranking 1.173 (69,7 %)**;
   modelo frente a casas p = 0,40; frente a ranking p = 0,0006 (p. 7). Tabla 1
   (p. 7; diferencia de acierto frente a las casas, en puntos): gradient boosting con
   cuotas (Wilkens) +0,10; random forest −0,14; Bradley–Terry −0,32; este modelo
   −0,71; regresión logística −0,80; Elo (Kovalchik, 2014) −2,00; modelo por puntos
   (Kovalchik, 2014) −5,00. Comparación entre conjuntos distintos.
6. **Límites.** Declarados: sin ventaja de local; jugadores sin historial dan
   probabilidades extremas; las anomalías de la casa (p. ej. británicos en
   Wimbledon, posible cobertura comercial; Thompson tras retirarse lesionado) se
   trasladan a los ratings; no puede superar a la casa por construcción. Detectados:
   evaluación solo por acierto (no mide la calidad probabilística, que es lo que
   pretende reproducir); hiperparámetros no publicados; muestra pequeña y solo
   Grand Slams; comparación de la Tabla 1 entre estudios heterogéneos.
7. **¿Replicable con nuestros datos?** **Sí, íntegramente y es muy aprovechable**:
   con las cuotas de cierre (Pinnacle o Avg) sin margen se ajustan «ratings
   implícitos del mercado» por superficie con decaimiento geométrico, lo que da una
   probabilidad coherente con el mercado para cualquier pareja (rondas futuras,
   partidos sin cuota todavía) **[nuestro: usarlo como prior/ancla del motor]**.
8. **Mercado.** Ganador; vía la ec. 7, probabilidad de set (1.er set, apuesta por
   sets bajo independencia) **[nuestro]**.
9. **Qué enseña.** (i) La cuota sin margen es un conjunto de entrenamiento compacto
   y de alta calidad. (ii) Antes de mezclar partidos a 3 y a 5 sets hay que
   llevarlos a una escala común (probabilidad de set). (iii) El decaimiento
   geométrico permite actualizar en línea. (iv) Las grandes discrepancias
   modelo–cuota sirven para detectar lesiones o sesgos comerciales. No trata
   calibración ni retiradas/walkovers (no consta).

### T29 — El reloj de saque y la eficiencia del mercado ATP

1. **Referencia.** T29. McFall y Cutter. Publicado en Journal of Gambling Business
   and Economics (2026) según el índice; la copia leída es el **cuerpo del
   manuscrito** (metadatos del PDF: «body_final_gambling_journal», autor McFall,
   13-oct-2024), 34 pp., **sin portada, resumen ni números de página**: se citan
   secciones y tablas.
2. **Modelo/método.**
   - Ec. 1 (§3): logit de P(gana el favorito de las casas) sobre razones
     favorito/no favorito de rasgos físicos (edad, talla), **estadísticas del propio
     partido** (% primeros saques dentro y ganados, segundos, break points),
     información del partido (ronda, nivel, superficie, «Big Three») y sus
     interacciones con rule = 1 tras el reloj de saque.
   - Ec. 2: igual, pero con el promedio de los **últimos 5 partidos** de cada
     jugador (perfil previo) en lugar de las estadísticas del partido.
   - Comparación con el mercado: la probabilidad de esos modelos **ajustados dentro
     de la muestra** («in-sample forecasting models», §4 «Market Efficiency») frente a
     la probabilidad implícita de la cuota (sin de-vig declarado), por periodos y en
     diferencias en diferencias (Tablas 7 y 8).
   - «Algoritmo» de apuestas: 1 $ al favorito común cuando el modelo le da ≥ 5 o ≥ 10
     puntos más que el mercado; pago con la cuota de mercado.
3. **Datos.** Partidos ATP de los repositorios de Jeff Sackmann (fuente: web ATP)
   de 2017–2018 (antes) y 2021, 2022 y primer semestre de 2023 (después); se
   excluyen round robin y **partidos incompletos** («normalmente por lesión»,
   ganador por abandono) (§3, nota 2). 11.338 partidos, 534 jugadores, 292
   torneos. Cuotas de Tennis-Data, «las últimas cuotas registradas al inicio del
   partido» (≈ cierre) de **Bet365**; si el mercado iguala a ambos, cuota media.
4. **Validación.** Ninguna fuera de muestra: los modelos que se comparan con el
   mercado están ajustados en todo el periodo, con interacciones posteriores al
   cambio (sesgo de anticipación). Métricas: coeficientes, efectos marginales,
   «media» por periodo y diferencias en diferencias. Sin Brier, log-loss ni
   calibración.
5. **Resultados.**
   - Tras el reloj, edad y talla pesan más: −1 % en la razón de edad → +9,7 pp de
     probabilidad del favorito respecto a antes; +1 % de ventaja de talla → +13,4 pp;
     +1 break point salvado → +14,3 pp (Tabla 5, col. 3–4); en el modelo de perfil,
     edad → +8,6 pp. Ninguna habilidad de tenis interactuada con el cambio es
     significativa (§4).
   - Big Three: antes, +22,7 pp para el favorito si jugaba uno de ellos; después,
     −3,2 pp (no significativo); χ² = 35,56 para la diferencia del coeficiente de edad
     con/sin Big Three.
   - Tabla 7 (cuatro periodos de algo más de un año): «media» del modelo físico
     0,687 / 0,682 / 0,684 / 0,669 y del mercado 0,638 / 0,627 / 0,621 / 0,627; la
     ventaja de los modelos sobre el mercado se ensancha 0,6–0,7 pp justo después del
     cambio (p < 0,10) y 1,1–1,2 pp en la partición en seis periodos (p < 0,05,
     Tabla 8), y vuelve al nivel inicial al final de la muestra.
   - Apuestas hipotéticas: ganancias «netas» de 568 $ (umbral 5 pp) y 320 $ (10 pp)
     en el trimestre previo; 739 $ y 409 $ en el posterior; 698 $ y 343 $ en el último;
     total 1.583 / 1.837 / 1.786 $ («≈ 30 % más» tras el cambio).
6. **Límites.** Declarados: las casas maximizan beneficio, no acierto (cita a Levitt
   2004); posible efecto de la congelación del ranking por la COVID (con periodos
   4–6, −1 % en la razón de ranking → +17,9 pp). Detectados: (i) comparación
   **dentro de la muestra**; la ec. 1 usa estadísticas del propio partido (fuga
   total si se leyera como pronóstico); (ii) la variable dependiente binaria
   aparece con DE ≈ 0,2 (Tabla 1), imposible para una binaria de media 0,632 (DE
   ≈ 0,48), y las «medias» de la Tabla 7 tienen DE ≈ 0,1–0,2: no queda claro si son
   tasas de acierto o probabilidades medias; (iii) las «ganancias netas» no
   cuadran con apuestas de 1 $ a favoritos (con ≈ 360 apuestas por periodo y
   cuotas < 2, el beneficio máximo posible queda muy por debajo de 568 $); (iv)
   «ocho meses» en la introducción frente a «nueve» en la conclusión; (v) efectos
   marginales de +9,7 a +14,3 pp por un 1 % de cambio, implausiblemente grandes
   (probablemente por unidad de razón). **Estudio poco fiable para cifras.**
7. **¿Replicable con nuestros datos?** Poco: exige estadísticas de saque/resto
   (no las tenemos de forma sistemática) y edad/talla. Sí es replicable la idea de
   **vigilar la calibración del mercado de cierre por periodos** para detectar
   rupturas tras cambios de reglas o de calendario.
8. **Mercado.** Ganador (ATP).
9. **Qué enseña.** Los cambios de reglamento pueden descalibrar temporalmente al
   mercado y a los modelos; conviene medir la calibración por ventanas temporales y
   reentrenar tras rupturas, siempre fuera de muestra. Retiradas: el artículo las
   **excluye** (nota 2); no trata reglas de liquidación.

### B03 — Métodos estadísticos para detectar amaño de partidos (tesis doctoral)

1. **Referencia.** B03. Oliver Hatfield, tesis doctoral, Universidad de Lancaster
   (STOR-i), diciembre de 2019, ≈ 73.000 palabras; datos y financiación de ATASS
   Sports. Leída completa (caps. 1–9 y bibliografía). Citas por página impresa.
2. **Modelo/método.**
   - **De-vig: fórmula de Khutsishvili (método de potencia)** (§6.1, p. 140):
     p_i = o_i^(−γ), con γ tal que Σ p_i = 1, en lugar de la normalización
     multiplicativa p_i = k/o_i. Motivo declarado: Vovk y Zhdanov (2009) la hallan
     más precisa, y es coherente con cuotas multiplicativas para sucesos
     independientes (f(p1p2) = f(p1)f(p2)). Margen = Σ 1/o_i − 1; con margen pequeño
     el método da casi igual, con margen grande las probabilidades son menos
     informativas (p. 140–141). Para exchange: por pausa entre juegos, mediana de
     hasta 10 pares de cuotas del tramo de margen más bajo ([0; 0,05) fusionado,
     luego 0,05–0,1, 0,1–0,2, ≥ 0,2) (§5.1.2, p. 133).
   - **Cadena de Markov jerárquica reparametrizada** (§2.3.2, cap. 3):
     p1 = μ + δ, p2 = μ − δ; μ (media de PWOS) apenas afecta a la probabilidad
     prepartido; δ manda. μ ≈ 0,645 hombres y ≈ 0,56 mujeres (Klaassen y Magnus,
     Wimbledon 1992–95, p. 40–41). **Teorema (cap. 3): m(δ | μ, s, b) es continua y
     estrictamente creciente en δ para todo marcador s y formato b**, luego
     invertible: de una probabilidad de mercado se obtiene un δ implícito único en
     cualquier marcador. Formas cerradas útiles: tiebreak desde 6-6
     Q = p1(1−p2) / [p1(1−p2) + p2(1−p1)] (p. 72); juego desde deuce
     p1² / [p1² + (1−p1)²] (p. 73); juego completo
     g(p) = p⁴·[15 − 4p − 10p² / (p² + (1−p)²)] (p. 168; extracción dañada,
     coincide con la fórmula estándar). Aviso: en vivo, cerca del final, μ sí importa
     (p. 41).
   - **Sets → partido** (§4.3, p. 108–113): con sets independientes,
     m₃(s) = 3s² − 2s³ (FDA de Beta(2,2)) y m₅(s) = 10s³ − 15s⁴ + 6s⁵ (FDA de
     Beta(3,3)). Aproximación logística: m₅(m₃⁻¹(x)) ≈ 1 / [1 + ((1−x)/x)^K], es decir
     **logit P(mejor de 5) ≈ K · logit P(mejor de 3)**, con K teórico = √1,4 ≈ 1,183
     (la tipografía del PDF se pierde; el valor numérico cuadra) y **K ajustado =
     1,186**. En Glicko equivale a multiplicar la diferencia de ratings por K.
   - **Glicko** (Glickman 1999; cap. 4): P = 1/(1 + e^{−q(θi−θj)}), q = ln10/400;
     paseo aleatorio gaussiano de ratings entre periodos; g(σ) = (1 + 3q²σ²/π²)^{−1/2};
     actualización = aproximación de Laplace con un paso de Newton (la tesis
     demuestra la equivalencia con un modelo de espacio de estados gaussiano,
     §4.2). Periodo de 1 semana empezando en viernes; parámetro de varianza por
     periodo «115,394» (símbolo perdido en la extracción) y K = 1,186, elegidos por
     log-verosimilitud predictiva (§4.4). Sin superficie (propone ratings
     correlacionados con la matriz de Irons et al. 2014: dura–tierra 0,25,
     dura–hierba 0,5, tierra–hierba 0,01; p. 121).
   - Cuotas prepartido (cap. 6): proceso gaussiano sobre el logit de la
     probabilidad implícita, media constante μ_k por partido, varianza
     σ²·exp(β′x) decreciente con log(1+volumen), correlación exponencial ρ^{|xi−xj|} y
     «nugget»; prior bayesiano μ_k ~ N(θi − θj, κ²(σi² + σj²)) desde Glicko.
   - En vivo (cap. 7): prior de δ desde Glicko con logit Y(0) ~ N(q(θi−θj),
     c²q²(σi²+σj²)); verosimilitud binomial de juegos de saque ganados por cada uno y
     tiebreaks (ec. 7.2.3–7.2.5). Cap. 8: proceso gaussiano para el δ implícito con
     medias que suben/bajan por diferencias de juegos de saque ganados/perdidos y
     tiebreaks; ajuste conjunto de 274 partidos; distancia de Mahalanobis frente a
     χ²_{n_k}.
3. **Datos.** Cuotas: un exchange (ATASS Sports), **274 partidos ATP 2013–2016**
   (dura 172, tierra 102; Grand Slam 36, Masters 64, otros ATP 137, Challenger 37),
   prepartido en ventanas a 0, 5, 20, 60, 120, 240, 480, 720 y 10.000 min del inicio y
   en vivo en cada pausa entre juegos, con volúmenes; nombres anonimizados (§5.1).
   Resultados: Sackmann ATP 1991–2016 con Challenger, Futures y previas (§5.2). WTA
   excluida por homogeneidad (p. 135).
4. **Validación.** Glicko: parámetros por log-verosimilitud sobre todo el periodo y
   calibración **solo visual** por tramos de 0,1 (Fig. 4.4.2, p. 115: «casi
   exactamente sobre la recta», sin cifra). Modelos de cuotas: ajuste en la muestra
   (AIC/BIC, p-valores predictivos, Mahalanobis); **no hay partición temporal ni
   etiqueta de partidos amañados**, así que no hay tasa de aciertos/errores. La
   comprobación de calibración del modelo en vivo se hace con la uniformidad de
   P(M1 < y) por juego (Fig. 7.5.7) y de los p-valores de Mahalanobis (Fig. 8.3.6).
5. **Resultados.** K = 1,186 ≈ independencia de sets (p. 113). Inflación de Glicko:
   la media del top-100/200/300 sube ≈ 25 puntos en 25 años; un debutante frente a un
   top-200 pasa de 0,318 a 0,298 (p. 125). Prior en vivo: sesgo lineal (α, β) no
   significativo frente a las cuotas de apertura en vivo; c = 0,914 (p < 0,05)
   (p. 176). Priors basados en la cuota prepartido: **muy mal calibrados** (PIT
   demasiado estrecho al principio y sobredisperso al final: el δ implícito se mueve
   como un paseo aleatorio) (p. 192–193). Proceso gaussiano en vivo: p-valores de
   Mahalanobis no uniformes (≈ 150 partidos con distancia muy pequeña y ≈ 50 con
   distancia grande frente a ≈ 27 esperados por tramo) (p. 210). Partidos marcados:
   73 y 136 (señalados por otras fuentes) y cuatro con p ≈ 0, todos con oscilación
   hacia el ganador final.
6. **Límites.** Declarados: un solo exchange y 274 partidos; sin verdad de terreno;
   Glicko sin superficie; con datos por juegos se aprende poco del δ en vivo; colas
   más pesadas que la normal; anomalía al combinar tiempo y volumen; μ fijo. La
   probabilidad cerca de 0/1 queda «censurada» por falta de liquidez (partido 22,
   p. 180). Detectados: ninguna evaluación fuera de muestra; calibración sin
   métrica numérica; solo ATP.
7. **¿Replicable con nuestros datos?** Sí: Glicko con conversión 3↔5 sets (logit×K),
   de-vig de potencia sobre las dos cuotas de cierre y δ implícito por inversión de
   la cadena de Markov para derivar sets, juegos, tiebreak y marcador exacto. No:
   los modelos de cuotas prepartido/en vivo (exigen cuotas de exchange con hora y
   volumen y marcador juego a juego).
8. **Mercado.** Ganador (prepartido y en vivo); la cadena de Markov da todos los
   derivados del marcador (la tesis menciona sets y hándicap de juegos sin
   desarrollarlos, p. 32).
9. **Qué enseña.** (i) De-vig de potencia/Khutsishvili preferible al multiplicativo
   (con la cita a Vovk y Zhdanov). (ii) Trabajar en escala logit. (iii) Medir
   calibración de distribuciones predictivas con PIT (uniformidad de P(M ≤ y)) y no
   solo con diagramas de fiabilidad. (iv) La varianza del rating (Glicko) da
   incertidumbre honesta para jugadores que vuelven de lesión. (v) Sesgo
   favorito–no favorito: citado (Forrest y McHale 2007), no cuantificado
   (p. 197). Retiradas: solo se menciona que jugadores no aptos se retiran en
   primera ronda para cobrar premio, lo que puede mover la cuota (p. 11); no trata
   reglas de liquidación.

### S01 — Predicción de la dirección del primer saque con aprendizaje automático

1. **Referencia.** S01. Zhu y Naikar (Georgia State University). Copia arXiv
   2602.22527v1, 26-feb-2026, 11 pp. El catálogo la asocia a MLSA 2022 / CCIS
   Springer 2023; **el PDF no muestra esa referencia editorial** (no consta).
2. **Modelo/método.** Clasificación multiclase de la dirección del primer saque
   (abierto, al cuerpo, a la T) por lado (iguales/ventaja), un modelo por jugador.
   Rasgos (§5): conteos acumulados de saques a cada dirección y de los ganados, % de
   primeros dentro por dirección, ganador del punto anterior, «índice de carrera»
   acumulado (fatiga, inferido de la posición por tipo y dirección de golpe), índice
   de ansiedad por nivel juego/set/partido: ansiedad = incertidumbre × (esperanza +
   miedo) (ec. 1) y su suma (ec. 2); se consideraron superficie y mano del rival.
   Modelos: regresión logística multinomial, árbol, random forest (200 árboles,
   profundidad 150), SVM, red neuronal (200, 100) (§6).
3. **Datos.** Match Charting Project (anotación manual punto a punto): 3.424
   partidos de 655 hombres y 1.916 de 422 mujeres; solo jugadores con ≥ 30 partidos;
   se publican 10 hombres y 10 mujeres (§4, §6). Sin cuotas.
4. **Validación.** **Partición aleatoria 70/30 de puntos** por jugador (no temporal;
   puntos del mismo partido pueden caer en entrenamiento y prueba). Métrica: solo
   acierto; **no se informa la línea base** (clase mayoritaria) ni Brier (lo dejan
   como trabajo futuro, §8).
5. **Resultados** (Tablas 1–4): acierto medio hombres 0,49 (iguales) y 0,50
   (ventaja); mujeres 0,44 y 0,45; con más jugadores, ≈ 48 % y ≈ 43 % (§7). Rango
   por jugador 0,36 (Kerber, iguales) a 0,58 (Kerber, ventaja; Thiem 0,56). Rasgos
   más importantes (árbol): conteos acumulados por dirección, índice de carrera del
   sacador en el punto anterior y % de primeros por dirección.
6. **Límites.** Declarados: datos con errores que exigieron limpieza; rasgos aún en
   desarrollo. Detectados: sin línea base, partición aleatoria con posible fuga
   intrapartido, jugadores seleccionados, sin incertidumbre.
7. **¿Replicable con nuestros datos?** No: requiere datos golpe a golpe que no
   tenemos.
8. **Mercado.** Ninguno de forma directa (contexto para microeventos de saque; no
   predice aces ni dobles faltas).
9. **Qué enseña.** Poco para el motor: muestra por qué un acierto sin línea base ni
   métrica probabilística no es interpretable. No trata calibración ni
   liquidación.

### S03 — Revisión sistemática: aprendizaje automático para el rendimiento en tenis

1. **Referencia.** S03. Sampaio, Oliveira, Marinho, Neiva y Morais (Beira Interior /
   Bragança). Applied Sciences 14:5517, 25-jun-2024, 21 pp. Revisión sistemática
   PRISMA.
2. **Modelo/método.** Búsqueda en PubMed, Web of Science y Scopus hasta abril de
   2024 con «tennis» + términos de IA; criterios PICOS; extracción con plantilla
   Cochrane; calidad con un STROBE modificado de 10 ítems (< 7 = baja calidad)
   (§2). No hay modelo propio ni metaanálisis.
3. **Datos.** 1.720 registros → 757 duplicados → 324 excluidos por título/resumen →
   639 evaluados → 23 incluidos (455 sin ML y 161 de otros deportes excluidos)
   (§3.1). Cinco bloques: estados psicológicos (2), talento (4), predicción de
   resultado (6), análisis espacial/táctico (8), lesiones y carga (3).
4. **Validación.** No aplica (revisión). Las métricas recogidas son casi siempre
   acierto con particiones de 50–90 %; ninguna recoge Brier, log-loss ni
   calibración.
5. **Resultados** (Tablas 3–7). Predicción de resultado: Ghosh et al. 92,07–98,96 %
   (hombres) y 91,93–98,57 % (mujeres) con el «Tennis Match Statistics dataset» de
   UCI; Khder y Fujo 99,8 %; Gao y Kowalczyk ≈ 80 % (ATP 2000–2016, variables
   físicas, psicológicas, de pista y de partido); Kovalchik et al. (challenges)
   74,5 % / 79,2 %; Makino et al. (ganador del punto, MCP) 66,5 %. La revisión
   recomienda priorizar árboles de decisión por esos aciertos (§4.3). Otros:
   «la zona» 85 % con sensores; aces frente a saques devueltos 87,02 % (Whiteside y
   Reid, datos de seguimiento).
6. **Límites.** Declarados: incluye estudios de baja calidad por escasez. Detectados:
   (i) los aciertos de 92–99,8 % casi con seguridad usan estadísticas del propio
   partido (fuga), y la revisión no lo discute **[nuestro: inferencia por la
   descripción de los datos]**; (ii) la Tabla 2 (calidad) no cuadra con el texto
   (el texto da alta calidad a [37–52] y baja a [53–59], pero la tabla marca, p.
   ej., Kovalchik et al. [44] 6/10 «Low» y Ghosh et al. [54] 10/10 «High»; puede ser
   en parte desalineación de la extracción); (iii) ningún estudio de cuotas ni de
   probabilidad calibrada.
7. **¿Replicable con nuestros datos?** No aplica; ninguno de los estudios citados
   usa datos como los nuestros de forma comparable.
8. **Mercado.** Ninguno de forma directa.
9. **Qué enseña.** Sirve como mapa bibliográfico y como advertencia: aciertos
   altísimos en «predicción de partidos» suelen ser fuga de información
   posterior. No trata calibración ni liquidación.

### S04 — Temperatura alta y rendimiento (saque) en el ATP

1. **Referencia.** S04. Picchio y van Ours. IZA Discussion Paper 16431, septiembre
   de 2023 (documento de trabajo; publicado en Labour Economics 2024 según el
   índice). Leído completo, con apéndices A–B. **No** se ha leído la versión
   editorial ni el corrigendum de 2025 que cita el índice.
2. **Modelo/método.** Efectos fijos (ec. 5, p. 16):
   y_imte = f(temp_mte; β) + x′γ + τ_te + α_i + ε, con y = % de primeros saques
   dentro o % de dobles faltas por jugador y partido, τ_te = efectos fijos
   torneo×edición (identificación por la desviación diaria respecto de la media del
   torneo), α_i = efectos fijos de jugador, errores agrupados en dos dimensiones
   (torneo y jugador). f lineal, por splines (nudos cada 2 °C entre 14 y 28 °C) o por
   tramos; la linealidad no se rechaza (nota 14). Temperatura a las 15 h a 2 m de
   ERA5-Land (rejilla 0,1°). Modelo teórico potencia–precisión del primer y segundo
   saque (ec. 1–4).
3. **Datos.** Tennis-Data ATP 2003–2021 (fecha, sede, categoría, superficie,
   interior/exterior, ronda, formato, marcador por sets, ranking y puntos, y si el
   partido se completó o hubo retirada) cruzado con estadísticas de Sackmann; tras
   limpiar, 38.034 partidos al aire libre, **76.068 observaciones jugador-partido**,
   1.061 jugadores, 88 torneos (p. 9–12). Se eliminan partidos cancelados
   (**walkovers ≈ 0,5 %** de los partidos; 2 descalificaciones), duraciones < 30 min
   o > 5 h, faltantes y el 1 % extremo de temperatura. Solo hombres (las
   estadísticas femeninas solo existen desde 2016, p. 9). Sin cuotas.
4. **Validación.** Inferencia causal, no predicción: sin muestra fuera de muestra.
   Robustez: placebo con partidos bajo techo (sin efecto, Apéndice A), logaritmos
   (Tabla B.1), efectos entre torneos (Tabla B.2), retardos (Tabla 4).
5. **Resultados.** +1 °C → **−0,106 pp de primeros dentro** (EE 0,014) y
   **+0,040 pp de dobles faltas** (EE 0,006) (Tabla 2, col. 1–2), es decir −0,07 pp
   de segundos dentro. Medias: primeros dentro 60,9 %, dobles faltas 3,77 %,
   temperatura 20,7 °C (8,9–31,4). Sin condicionar: dobles faltas de ≈ 3,5 % a ≈ 4,5 %
   y primeros dentro de ≈ 62 % a ≈ 59 % entre 17 y 30 °C (Fig. 1). Heterogeneidad
   (Tabla 3): tierra −0,126 / +0,052 frente a dura/hierba −0,090 / +0,030 (p = 0,14 y
   0,055); antes de cuartos −0,116 frente a cuartos o más −0,060 (p = 0,012); top-50
   −0,089 frente a resto −0,122 (p = 0,054); edad < 25 −0,088, 25–29 −0,104, ≥ 29
   −0,129 (p = 0,025); dobles faltas sin gradiente por edad. Adaptación: la
   temperatura del partido anterior atenúa el efecto (+0,038 en primeros, −0,010 en
   dobles faltas; Tabla 4). Entre torneos: +0,020 pp de dobles faltas por °C
   (p < 0,01) (Tabla B.2).
6. **Límites.** Declarados: la temperatura es la de las 15 h (no la hora del
   partido); validez externa; pérdida de muestra en el análisis dinámico. Detectados:
   no estudia el resultado del partido; el efecto es pequeño en términos absolutos
   (≈ 0,4 pp de dobles faltas por cada 10 °C).
7. **¿Replicable con nuestros datos?** Parcialmente: tenemos resultados de
   Tennis-Data y clima ERA5/Open-Meteo, pero **no** estadísticas de saque
   sistemáticas, que son la variable dependiente. Para el motor solo serviría como
   covariable débil en mercados de dobles faltas/aces si algún día se tienen esos
   datos **[nuestro]**.
8. **Mercado.** Dobles faltas (y, de forma indirecta, % de primeros); no ganador.
9. **Qué enseña.** Calibración: nada. Liquidación/datos: en Tennis-Data los
   walkovers son ≈ 0,5 % de los partidos y el archivo marca retiradas y partidos no
   completados (p. 9), información necesaria para nuestras reglas de liquidación.
   No consta si los autores excluyen las retiradas (sí excluyen < 30 min).

