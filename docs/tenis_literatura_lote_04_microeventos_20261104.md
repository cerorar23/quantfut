# Tenis — literatura, lote 04: microeventos (saque, juegos, sets, tiebreaks, momentum)

Fecha: 2026-11-04. Rediseño del motor de tenis ATP/WTA con probabilidad calibrada y
distribución completa del marcador. Lote: los 17 PDF de
`BIBLIOTECA_TENIS_COMPLETA/pdfs/04_microeventos/` (índice: `INDICE_COMPLETO.txt`,
solo metadatos). Texto extraído con `pdftotext -layout`; cada afirmación cita página
o sección del propio artículo. «No consta» = el artículo no lo dice.

Estado: en redacción (las fichas se añaden al terminar cada estudio).

## (a) Tabla resumen

(se completa al final)

## (b) Fichas por estudio

### A06 — Ingram (2019), modelo jerárquico bayesiano basado en puntos

1. **Referencia.** Martin Ingram, «A point-based Bayesian hierarchical model to predict
   the outcome of tennis matches», *J. Quant. Anal. Sports* 15(4):313-325, 2019. Artículo
   de revista (13 pp.). Leído íntegro.
2. **Modelo** (§2.2, ecs. 1-11). Cada partido se parte en dos «serve-matches»:
   - Verosimilitud: `y_i ~ Binomial(n_i, θ_i)` (puntos ganados al saque sobre jugados; asume IID).
   - `logit(θ_i) = (α_{s,p} − β_{r,p}) + (γ_{s,m} − γ_{r,m}) + δ_t + θ_0`
     (α saque del sacador en el periodo p, β resto del restador, γ preferencia por superficie
     m —la misma γ entra con signo + para el sacador y − para el restador—, δ intercepto por
     torneo, θ_0 intercepto global).
   - Priors: `α_{·1} ~ N(0, σ_{α0}²)`, `β_{·1} ~ N(0, σ_{β0}²)`, `γ ~ N(0, σ_γ²)`,
     `δ ~ N(0, σ_δ²)`, todas las σ ~ media-normal H(0,1); paseo aleatorio gaussiano
     `α_{·,p+1} ~ N(α_{·,p}, σ_α²)`, `β_{·,p+1} ~ N(β_{·,p}, σ_β²)` con varianza común a
     todos los jugadores (como Glicko). Ajuste NUTS/Stan, 4000 draws, R̂ < 1,1.
   - Predicción del partido: se promedia la probabilidad IID de ganar el partido sobre cada
     pareja de draws posteriores (integra la incertidumbre de θ en lugar de usar la media).
     Jugadores y torneos no vistos se sacan del prior de grupo (§2.2.3).
3. **Datos.** ATP; partidos raspados de MatchStat.com con puntos jugados/ganados al saque;
   se descartan retiros, walkovers y partidos sin estadísticas (§2.1). Validación = temporada
   ATP 2014: 60 torneos, 2208 partidos (Tabla 1: 22 tierra/736, 5 hierba/232, 33 dura/1240).
   ~80 puntos de saque por jugador y partido; 64 % ganados (62 % tierra, 67 % hierba).
   Ajuste desde 2011, 2012 o 2013. Nº de partidos de entrenamiento: no consta.
4. **Validación.** Temporal y sin fuga: «to predict each period of 2014, the model is fit
   with all data up to but excluding that period» (§2.2.3). Métricas: acierto, log loss y
   RMSE de θ_i+θ_j y θ_i−θ_j. Referencias: modelo «opponent-adjusted» de Barnett–Clarke
   (mejor modelo por puntos de Kovalchik 2016) y Elo de FiveThirtyEight desde 1968.
   Calibración (curva de fiabilidad): no consta.
5. **Resultados** (Tabla 2, 2014 fuera de muestra; mejor modelo = inicio 2011, periodos de
   2 meses): acierto 68,8 % / log loss 0,592 / RMSE suma 0,0904 / RMSE diferencia 0,125;
   Barnett–Clarke 66,3 % / 0,641 / 0,0993 / 0,130; Elo 538 69,5 % / 0,586 / — / —.
   Bajar de 12 a 2 meses mejora; de 2 a 1 mes no mejora; empezar antes (más datos) mejora
   (§3.1, Fig. 1-2). Posteriores (Tabla 3, mediana [2,5 %; 97,5 %], escala logit):
   σ_{α0}=0,154 [0,138; 0,172], σ_{β0}=0,124 [0,109; 0,140], σ_γ=0,067 [0,059; 0,076],
   σ_δ=0,069 [0,057; 0,082], paseo aleatorio por bimestre σ_α=0,039 [0,034; 0,044],
   σ_β=0,027 [0,023; 0,031], θ_0=0,503 [0,473; 0,533] → 62,3 % al saque para dos
   jugadores iguales en torneo y superficie medios. Superficie: rango clay +0,16 (Nadal) a
   −0,11; hierba +0,12 a −0,18; dura +0,10 a −0,11 (Tablas 6-7). Interceptos de torneo:
   Halle +0,15, Wimbledon +0,14, Montecarlo −0,14, Umag −0,13 (§3.6). Ejemplo RG 2014:
   P(Nadal)=58 %, resultado más probable Nadal en 4 sets (Fig. 8).
6. **Límites.** Declarados: IID; habilidad constante dentro del periodo; misma varianza de
   paseo para todos (no capta lesiones; propone Glicko-2, §4.2); priors de superficie
   independientes aunque clay y hierba se correlacionan negativamente (Fig. 5); 80 min de
   ajuste, lo que limita la historia usable; algo peor que Elo en ganador. Detectados: solo
   ATP; una temporada de validación; sin intervalos para las métricas; sin calibración;
   no evalúa mercados derivados (sets, juegos) aunque los deriva (Fig. 8-9).
7. **¿Replicable con nuestros datos?** Parcialmente. Necesita puntos jugados/ganados al
   saque por partido, que NO tenemos para todos los partidos. Opciones: (i) ajustar con el
   subconjunto del Match Charting Project (7,6 mil ATP / 4,3 mil WTA, con sesgo de selección
   hacia partidos grabados); (ii) cambiar la verosimilitud a juegos de saque/sets (no
   probado en el artículo). La estructura jerárquica (habilidad + superficie + torneo +
   paseo aleatorio) y las magnitudes de la Tabla 3 sirven como priors iniciales. Código
   público (GitHub del autor, citado en §2.2.3).
8. **Mercados.** Ganador; sets y marcador por sets (Fig. 8-9); en principio todo lo derivable
   del modelo IID (juegos, tiebreak) pero no validado aquí.
9. **Preguntas.** (b) Es la referencia directa: encogimiento jerárquico, ajuste por
   oponente (α−β), superficie (γ) y torneo (δ), incertidumbre propagada por draws. (a) Cita
   que las desviaciones de IID son pequeñas (Klaassen–Magnus 2001) y robustas (Newton–Aslam)
   pero no las mide. (c) Usa el modelo IID (Barnett/O'Malley/Newton–Keller) sin transcribir
   fórmulas.

### A19 — Di Feo (2025/26), «Gioco, Partita e Incontro: Modellizzazione Markoviana del Tennis»

1. **Referencia.** Antonio Di Feo, tesis de grado (triennale) en Matemáticas, Università di
   Bologna, A.A. 2024/2025 (relator A. Pascucci), en italiano, 43 pp. Se apoya en Carrari et
   al. (2017) y Newton–Keller (2005). Leída íntegra (cap. 1 de preliminares de Markov
   leído en diagonal: es teoría estándar de libro, Norris 1998).
2. **Modelo.**
   - Juego como cadena de Markov de 17 estados (Tabla 2.1). Probabilidad de punto del
     sacador `p` hasta 30-30 y `p̄` desde 30-30 (30-30 se identifica con deuce; 40-30 y
     30-40 con ventaja) para captar «tensión» (§2.1). Probabilidad de absorción (Teor. 2.1):
     `h1(p,p̄) = p²·[5p² − 4p³ + 4(p−1)²·p·p̄ − 2(p−1)²·p̄²·(p(4p̄−2) − 2p̄ − 3)/(2p̄² − 2p̄ + 1)]`
     (comprobado: `h1(0,5;0,5)=0,500`, `h1(0,6;0,6)=0,736`, igual que la Tabla 2.2; con
     `p=p̄` se reduce a la fórmula clásica). Tabla 2.2 da `h1` para p, p̄ ∈ {0,1…1}.
   - Duración del juego: cadena condicionada `t'_ij = t_ij·h_j/h_i` (Teor. 2.2) y tiempos
     medios de absorción (Teor. 2.3); `E[puntos] = k1(p,p̄)h1(p,p̄) + k1(1−p,1−p̄)h1(1−p,1−p̄)`
     (Tablas 2.3-2.4: con p=p̄=0,5 → 6,75 puntos; p=0,6 → 6,565).
   - Tiebreak: cadena de 53 estados (5-5 ≡ 6-6); `p_A^T = Σ_{j=0}^{5} p_A(7,j) + p_A(6,6)·Σ_{n≥0} p_A(n+2,n)`
     (ec. 2.3, tomada de Newton–Keller pp. 266-268, sin resolver aquí); número esperado de
     puntos en forma cerrada (polinomio en p_A, p_B; Tabla 2.5: 11,74 con 0,5/0,5; 11,84 con
     0,6/0,6; 12,18 con 0,7/0,7).
   - Set: se enumeran los vectores X = (primer sacador, aA, aB, bB, bA) (juegos ganados por
     cada uno según quién saca) y se multiplican potencias de las probabilidades de juego con
     coeficientes combinatorios; p.ej. `Pa[6-4] = Σ_h C(5,h)·C(4,5−h)·(P_aA)^h(P_aB)^{5−h}(P_bB)^{h−1}(P_bA)^{6−h}`
     (coeficientes 1, 20, 60, 40, 5). `Pa[7-6] = Pa[gana TB | 6-6]·Pa[6-6]`; simetría
     `Pa[(B,A)] = S_{A,B}(P_aB, P_aA, P_bA, P_bB)`. Duración del set por esperanza
     condicionada (ec. 2.5, Tabla 2.6).
3. **Datos.** atptour.com, enfrentamientos Nadal-Djokovic-Federer 2009-2014: 57 partidos,
   160 sets, 1544 juegos (Tabla 3.1). Solo ATP, solo 3 jugadores.
4. **Validación.** Dentro de muestra: p y p̄ se estiman con las mismas partidas que se
   comparan («ottimizzato tramite un'opportuna scelta dei parametri», Introducción). Sin
   métrica formal, sin test, sin intervalos. Los sets con tiebreak se excluyen de la
   comparación de duración (§3.2).
5. **Resultados.** Probabilidad de juego modelo vs observada (Tablas 3.2-3.4), p.ej. Nadal
   vs Djokovic: P(Nadal mantiene) 0,724 (p=p̄) / 0,715 (p≠p̄) vs 0,712 observada; Djokovic
   0,791 / 0,777 vs 0,756. Estimaciones p→p̄: Nadal 0,605→0,572, Djokovic 0,639→0,597 (vs
   Nadal); Federer 0,619→0,586 (vs Nadal); Nadal 0,641→0,668 (vs Federer); Federer
   0,636→0,608, Djokovic 0,619→0,632 (vs Federer). Duración del set: discrepancias de hasta
   10 puntos (Nadal-Djokovic aA: 49,5 observado vs 59,8 modelo, Tabla 3.8).
6. **Límites.** Declarados: pocos datos; variables externas (superficie, clima) no
   modeladas; simplificaciones por brevedad (§3.3). Detectados: (i) **error en los
   coeficientes de 6-6** (§2.3.2): escribe 1, 26, 125, 200, 125, 26, 1, pero el número de
   órdenes es C(6,h)² = 1, 36, 225, 400, 225, 36, 1 (suma 924 = C(12,6)); los de 6-0…7-5 sí
   cuadran; (ii) término espurio «20[(P_aA)^4 P_aB]» en Pa[6-4]; (iii) en §2.3.2 escribe
   primero X=(0,3,0,3,0) para 6-0 y luego (0,3,0,0,3); (iv) Tabla 3.4: p_B global 0,6449 no
   está entre los valores pre/post-deuce 0,6186 y 0,6321 (incoherente); (v) Tablas 3.9 y 3.10
   tienen la misma columna observada (58,37/58,02/50,96/59,80) para dos parejas distintas;
   (vi) el «efecto presión» p≠p̄ se mide sin error estándar con 3 jugadores.
7. **¿Replicable con nuestros datos?** Sí: las fórmulas solo piden p (y p̄); p̄ se podría
   estimar con el Match Charting Project (puntos desde 30-30). No usar sus coeficientes de
   6-6 ni sus tablas empíricas.
8. **Mercados.** Ganar juego, marcador exacto del set (incluido número de breaks por
   jugador), tiebreak, duración en puntos (no en juegos totales de partido).
9. **Preguntas.** (a) Introduce un «p post-deuce» pero la evidencia es anecdótica (4 de 6
   cifras bajan 3-4 pp, 2 suben); no sirve para fijar un factor clutch. (c) Da forma cerrada
   del juego y del TB (duración) y enumeración exacta del set: no hace falta Monte Carlo.
   (e) La enumeración por set con primer sacador explícito es exactamente la distribución
   conjunta de juegos por set. (f) Distingue Pa/Pb (quién saca primero) pero no mide el
   efecto. (h) TB a 7 en forma de sistema recursivo; super-tiebreak: no consta.

### A26 — Klaassen y Magnus (2003), «Forecasting the winner of a tennis match»

1. **Referencia.** F.J.G.M. Klaassen, J.R. Magnus, *European Journal of Operational
   Research* 148:257-267, 2003. Artículo de revista (11 pp.). Leído íntegro.
2. **Modelo.**
   - Programa TENNISPROB: con puntos IID (dependen solo de quién saca), la probabilidad de
     ganar juego/set/partido desde cualquier marcador se calcula **exactamente** (no por
     simulación) a partir de `p_a`, `p_b`, el formato y el sacador (§2).
     Juego al saque: `g_a = p_a⁴(−8p_a³ + 28p_a² − 34p_a + 15) / (p_a² + (1−p_a)²)` (ec. 1).
     Punto decisivo en deuce («no-ad»): `g*_a = p_a⁴(−20p_a³ + 70p_a² − 84p_a + 35)` (ec. 2);
     con p_a=0,65, g=0,830 y g*=0,800 (el break sube de 17 % a 20 %).
   - Importancia de un punto (Morris 1977): P(A gana partido | gana el punto) − P(A gana |
     lo pierde).
   - Previa al partido por ranking: `R = 8 − log2(RANK)`, `P(mejor gana) = logistic(λ·(R_a − R_b))`
     (ecs. 3-4); probados λ dependiente de R_a±R_b: no significativo (nota 5).
   - Suma `p_a + p_b` con datos punto a punto: modelo lineal de probabilidad con efecto
     aleatorio por partido, `y_at = x_a'β + η_a + ε_at`, `x_a' = (1, R_a−R_b, R_a+R_b)`,
     `var(η)=σ²`, `cov(η_a,η_b)=c`, `var(ε_at) = x_a'β(1−x_a'β) − σ²` (ecs. 5-12); estimado
     por MV con medias normales. Luego `p̂_a + p̂_b = 2(β̂_0 + (R_a+R_b)β̂_2)` y la diferencia
     se obtiene **invirtiendo TENNISPROB** a partir de la probabilidad de partido estimada
     con resultados (§4-5).
3. **Datos.** Wimbledon 1992-1995: 495 partidos masculinos y 504 femeninos (sin
   abandonos) para el logit de ranking; punto a punto de 481 partidos (258 M / 223 F;
   57.319 y 28.979 puntos; sin puntos de tiebreak) solo de las 5 pistas de exhibición,
   reponderados por la inversa de la tasa de muestreo (§3-4).
4. **Validación.** No hay validación fuera de muestra ni métricas de pronóstico: todo se
   ajusta con 1992-1995 y se ilustra con dos finales. Bandas al 95 % por la incertidumbre de
   λ (Fig. 3) y de p_a+p_b (Fig. 5).
5. **Resultados.** λ̂ = 0,3986 (EE 0,0461) hombres y 0,7150 (0,0683) mujeres; nº1 vs nº16:
   0,8312 (M) y 0,9458 (F); el mejor ranking ganó 68 % (M) y 75 % (F) (§3). Tabla 1 (M / F):
   β_0 0,6276 (0,0044) / 0,5486 (0,0051); β_1 0,0112 (0,0013) / 0,0212 (0,0015); β_2 0,0036
   (0,0009) / 0,0022 (0,0010); varianza del efecto aleatorio σ² 0,0026 (0,0002) / 0,0016
   (0,0003) → DE de la «forma del día» en p ≈ 0,051 (M) y 0,040 (F); correlación c/σ²
   −0,448 (0,085) / −0,635 (0,202): si A saca mejor de lo esperado, B saca peor.
   Fig. 1: al inicio del partido la probabilidad de ganar depende casi solo de `p_a − p_b`
   (para 0,8 < p_a+p_b < 1,6); lo mismo al inicio del 3.er y del 5.º set; a 5-5 del set
   final y con marcadores desiguales (5-4, 4-5) la suma pesa mucho más (Fig. 2). A igualdad
   de marcador la probabilidad no depende de quién saca (§2). Efecto «magnificación»: la
   curva derivada del punto converge a 1 más rápido que la de resultados → prefieren estimar
   la diferencia con resultados y la suma con puntos (correlación entre ambas < 0,10, §4).
   Ejemplos: Sampras-Becker 1995 p̂=0,598 → p̂_a=0,6824, p̂_b=0,6663; Graf-Novotna 1993
   p̂=0,906 → 0,6265/0,5273; puntos más importantes imp=0,19 y 0,27 (§5).
6. **Límites.** Declarados: IID («deviations from i.i.d. are small», citando K&M 2001);
   p no se actualiza durante el partido (propone actualización bayesiana; «open question»,
   §6). Detectados: solo hierba y solo Wimbledon de 1992-1995; muestra punto a punto sesgada
   a pistas grandes; el ranking es la única medida de calidad; sin métrica de pronóstico.
7. **¿Replicable con nuestros datos?** Sí. TENNISPROB es replicable con recursiones; la
   estrategia de calibración «diferencia desde resultados de partido, suma desde datos de
   punto (MCP)» encaja con nuestros datos (tenemos resultados de todos los partidos y
   punto a punto solo del MCP). El efecto aleatorio de partido se puede reestimar con MCP.
8. **Mercados.** Ganador previo y en vivo; juego (break), set; la suma `p_a+p_b` gobierna
   duración y totales (implícito en §2 y en A06).
9. **Preguntas.** (a) Asume IID con base en K&M 2001; no mide la violación aquí. Aporta en
   cambio una varianza entre partidos de p (σ≈0,04-0,05) que es una fuente de dispersión
   distinta de la dependencia entre puntos. (b) Propone separar diferencia y suma y
   calibrar la diferencia contra resultados. (c) Cálculo exacto, sin simulación. (f) Con
   marcador igualado, la probabilidad de partido no depende de quién saca (§2).

### A31 — Newton y Keller (2005), «Probability of Winning at Tennis I. Theory and Data»

1. **Referencia.** P.K. Newton, J.B. Keller, *Studies in Applied Mathematics* 114:241-269,
   2005. Artículo de revista (29 pp.). Leído íntegro, incluido el apéndice.
2. **Modelo** (todo bajo IID: `p_A^R`, `p_B^R` constantes durante el partido).
   - Juego (ecs. 1-5): `p_A^G = p⁴(1 + 4q + 10q²) + 20p³q³·p²·(1 − 2pq)⁻¹`, con p = p_A^R,
     q = 1−p (coincide con Carter–Crews 1974).
   - Set (ecs. 6-10): `p_A^S = Σ_{j=0}^{4} p_A^S(6,j) + p_A^S(7,5) + p_A^S(6,6)·p_A^T`, con la
     recursión `p_A^S(i,j) = p_A^S(i−1,j)p_A^G + p_A^S(i,j−1)q_A^G` si i−1+j es par (saca A) y
     `= p_A^S(i−1,j)q_B^G + p_A^S(i,j−1)p_B^G` si es impar; soluciones cerradas en (A.1)-(A.7),
     p.ej. `p_A^S(6,0) = (p_A^G)³(q_B^G)³`, `p_A^S(6,1) = 3(p_A^G)³q_A^G(q_B^G)³ + 3(p_A^G)⁴p_B^G(q_B^G)²`,
     `p_A^S(7,5)` con coeficientes 1, 25, 100, 100, 25, 1 (verificados: suman C(10,5)=252).
   - Tiebreak a 7 (ecs. 11-16): `p_A^T = Σ_{j=0}^{5} p_A^T(7,j) + p_A^T(6,6)·p_A q_B·(1 − p_A p_B − q_A q_B)⁻¹`
     (orden de saque A, BB, AA, …; recursión 14-15; cerradas A.8-A.14; comprobé que los
     coeficientes de 7-5 —6, 75, 200, 150, 30, 1— suman C(11,5)=462).
   - Partido (ecs. 35-52): se sigue quién saca el primer y el último juego de cada set
     (`p^S_AA`, `p^S_AB`, …) con la recursión (43)-(44); como el set es neutral al saque se
     reduce a `p^M = s² + 2s²(1−s)` (2 de 3) y `p^M = s³ + 3s³(1−s) + 6s³(1−s)²` (3 de 5).
   - Torneo de 128: producto de matrices por bloques (ecs. 53-67).
   - No-IID propuesto (§7, ec. 69): `p̂_A^R = p_A^R + δ·p_AB^R(i,j)`, δ ≪ 1, tratado como
     perturbación (no desarrollado).
3. **Datos.** US Open y Wimbledon 2002: puntos y juegos al saque de los semifinalistas
   (Tablas 1-2) y de sus rivales de 1.ª ronda agregados; 117 partidos completos del US Open
   masculino para la Fig. 2 (agrupados por p_B^R = 0,50/0,60/0,70 ± 0,01: 9, 33 y 20
   partidos).
4. **Validación.** Dentro de muestra y visual: p_R observado frente a % de juegos ganados
   en los mismos partidos; sin test ni intervalos. La predicción del campeón tras cuartos
   usa p_R acumulado del propio torneo (ec. 68). Sin métricas de pronóstico.
5. **Resultados.** Juego al saque observado vs teórico (ec. 5): Sampras 0,73 → 0,95 vs
   0,93; S. Williams (USO) 0,69 → 0,91 vs 0,89; Nalbandian 0,61 → 0,73 vs 0,76; Mauresmo
   (Wimbledon) 0,64 → 0,88 vs 0,81 (mayor desvío). Tablas 3-4: p^M para p_A^R, p_B^R ∈
   {0…1}: p.ej. 0,6 vs 0,5 → 0,9513 (3 de 5) y 0,9079 (2 de 3); 0,5 vs 0,4 igual; 0,7 vs
   0,6 → 0,9380 / 0,8909. **Teorema (§3.3): la probabilidad de ganar el set —y por tanto el
   partido— no depende de quién saca primero**, y `p_A^T = q_B^T` en el tiebreak; vale para
   cualquier sistema «service neutral» (juegos sacados por A menos por B ∈ {−1,0,1}). Pero
   los marcadores individuales sí dependen del primer sacador: solo son invariantes P(6-0),
   P(6-1)+P(6-2), P(6-3)+P(6-4), P(7-5) y P(6-6) (Fig. 4) y, en el TB, P(7-0)+P(7-1),
   P(7-2)+P(7-3), P(7-4)+P(7-5) y P(6-6) (Fig. 5). Tras cuartos, el favorito del modelo ganó
   el torneo en 2 de 4 cuadros (Figs. 7-10).
6. **Límites.** Declarados: IID; cita «first game effect» (el primer juego es el más
   difícil de romper, Magnus–Klaassen 1999), «hot hand» y «back-to-the-wall» (Jackson–
   Mosurski 1997), pequeños en datos agregados pero quizá mayores en duelos concretos (§7).
   Detectados: validación anecdótica y circular; solo Grand Slams 2002.
7. **¿Replicable con nuestros datos?** Totalmente: las recursiones solo piden p_A^R y
   p_B^R; son la base exacta del motor (distribución de marcadores por set y TB con primer
   sacador explícito).
8. **Mercados.** Ganador, sets (2-0, 2-1, 3-x), marcador exacto de set, tiebreak (sí/no,
   resultado), por extensión hándicap y totales de juegos.
9. **Preguntas.** (c) Fórmulas cerradas/recursiones exactas para juego, TB, set, partido:
   Monte Carlo innecesario bajo IID. (e) La recursión por set con primer sacador es la
   distribución conjunta coherente; para encadenar sets hay que propagar quién saca
   (ecs. 35-44), no re-sortearlo en cada set. (f) Bajo IID el primer sacador no cambia
   ganador ni sets, pero sí marcadores exactos de set/TB (y, por T31, totales); promediar
   50/50 es correcto si no se conoce. (a) Solo cualitativo.

### A32 — Newton y Aslam (2009), «Monte Carlo Tennis: A Stochastic Markov Chain Model»

1. **Referencia.** P.K. Newton, K. Aslam, *J. Quant. Anal. Sports* 5(3), art. 7, 2009
   (44 pp., de las que ~18 son histogramas de torneos simulados). Leído íntegro (las
   Figs. 22-33 solo tienen pies de figura; sin datos numéricos extraíbles).
2. **Modelo.** Mismas recursiones exactas que A31 (juego ec. 5, set 6-10, TB 11-14, partido
   3 de 5 ec. 15), pero `p` de saque y de resto de cada jugador son variables aleatorias
   **gaussianas truncadas** en [0,1] (ecs. 1-4), con media y DE «contra el campo». Ajuste
   por rival aditivo: `p̃_A^s = μ_A^s − (μ_B^r − μ_f^r)` (ecs. 16-34; p.ej. Federer
   0,70714 − 0,06259 = 0,64455 contra Nadal). Monte Carlo: (i) sortear p_A, p_B; (ii)
   calcular p^M analíticamente; (iii) repetir 30.000 veces (§2.5). Ranking por autovector
   de Perron-Frobenius de la matriz de preferencias (Keener; ecs. 35-38).
3. **Datos.** ATP 2007: 330 jugadores, 59 torneos, N = 5245 observaciones jugador-partido;
   «campo» μ_s = 0,63316, σ = 0,094779 (normalidad aceptada por χ² = 11,45 < 14,68,
   α = 0,10); Grand Slams 2007 (Tabla 1): AO 0,6236 (σ 0,101), RG 0,6168 (0,081),
   Wimbledon 0,6599 (0,077), USO 0,6368 (0,090). Jugadores (Tabla 2): Federer μ_s 0,707
   σ_s 0,072, μ_r 0,413 σ_r 0,071; Nadal 0,688/0,083/0,429/0,101; Roddick
   0,731/0,084/0,344/0,081; Blake 0,674/0,078/0,391/0,074.
4. **Validación.** Ninguna fuera de muestra: parámetros y comparaciones con la misma
   temporada 2007; coherencia anecdótica con los cara a cara de 2007 y con el ranking ATP
   final de 4 jugadores.
5. **Resultados.** Tabla 3: Federer-Nadal 0,5074; Federer-Roddick 0,6073; Federer-Blake
   0,6365; Nadal-Blake 0,6131; Nadal-Roddick 0,5883; Roddick-Blake 0,5206 (DE ≈ 0,028).
   Consistencia (Figs. 14-15): con μ_A=0,71 vs μ_B=0,68, P^M_A = 0,677 − 0,826·σ_A; con
   μ_A=0,68 vs 0,71, P^M_A = 0,323 + 0,720·σ_A → la variabilidad entre partidos empuja la
   probabilidad hacia 0,5. Convergencia del Monte Carlo en ley de potencias
   `|μ̂(N) − μ(∞)| ∼ N^−0,49` (Fig. 11, ≈ 1/√N). Torneos (1000 simulaciones): Federer gana
   11,5 % / 12 % / 12,2 % / 9,4 % de AO/RG/W/USO con cuadro real (Tabla 4) cuando en 2007
   ganó 3 de 4 — los autores lo llaman «perhaps surprisingly low».
6. **Límites.** Declarados: no usa cara a cara; puede infravalorar «bestias negras» (§3.1).
   Detectados (comprobación propia): (i) la DE observada del % de saque por partido
   (0,07-0,095) incluye el ruido binomial de ~80 puntos (≈0,05) y la heterogeneidad de
   rivales; tratarla como «inconsistencia» y además simular los puntos duplica varianza y
   explica probabilidades demasiado cercanas a 0,5 (torneos); (ii) las DE ≈ 0,028 de la
   Tabla 3 coinciden con el error binomial de la fracción de victorias en lotes de 300
   partidos (√(p(1−p)/300) ≈ 0,028; los histogramas usan «bin size 300 matches»): miden
   ruido de simulación, no incertidumbre del jugador; (iii) Figs. 12-13 no son
   reproducibles con la ec. 5 (p^G(0,633) = 0,800 y p^G(0,8) = 0,978 frente a medias
   simuladas 0,744 y 0,928; el texto alterna σ y σ² para 0,094779).
7. **¿Replicable con nuestros datos?** La idea (integrar la variabilidad de p entre
   partidos) sí; los parámetros no: requiere % de saque y resto por partido, que no
   tenemos para todos (sí en MCP). Si se usa, separar varianza binomial de la real
   (σ_real² = σ_obs² − p(1−p)/n), como hace el efecto aleatorio de A26.
8. **Mercados.** Ganador y torneo; por construcción, cualquier mercado derivable del
   modelo de Markov.
9. **Preguntas.** (b) Aporta la idea de que la incertidumbre/variabilidad de p acerca las
   probabilidades a 0,5 (Figs. 14-15). (d) Error Monte Carlo ∝ N^−1/2 (β = 0,49). (c)
   Combina fórmula cerrada (dentro del partido) con Monte Carlo solo sobre p: es el
   esquema eficiente (Monte Carlo sobre parámetros, exacto sobre el marcador).

### B11 — Barr, Scott y Sugden (2019), «Tie-Break Tennis Matches: A Case Study for First Year Level Statistics Teaching»

1. **Referencia.** G.D.I. Barr, L. Scott, S.J. Sugden, *Spreadsheets in Education* 12(1),
   2019 (23 pp.). Artículo docente (hoja de cálculo). Leído íntegro.
2. **Modelo.** Formato TBX: gana quien llega a X puntos con 2 de ventaja (TB7 = tiebreak
   clásico, TB10 = super-tiebreak). **Probabilidad de punto constante `p_A` para todo punto,
   sin distinguir quién saca** (la justifican como promedio de saque y resto, §2.3, Tabla 1:
   0,70 al saque y 0,40 al resto ≈ 0,55). Fórmula cerrada:
   `P(B gana TBX) = Σ_{k=0}^{X−3} C(X+k−1, k)·p_A^k·p_B^X + C(2X−3, X−1)·p_A^{X−2}·p_B^X / (1 − 2p_A p_B)`;
   para TB7: `p_B⁷(1 + 7p_A + 28p_A² + 84p_A³ + 210p_A⁴) + 462p_A⁵p_B⁷/(1 − 2p_A p_B)`
   (comprobado: da 0,5 con p=0,5). Longitud: `E(L) = Σ L·p(L)` y DE por la fórmula usual,
   truncando en 20-18. Además, con autómatas finitos (minimización de estados, §2.2):
   declarar «deuce» a 30-30 o a 40-40 es equivalente (40-30 ≡ ventaja); en un TB(n), deuce a
   n−1 iguales ≡ a n−2 iguales (el TB7 puede tratarse con deuce en 5-5).
3. **Datos.** Ninguno real: tablas teóricas y 1000 partidos simulados para un ejercicio de
   clase (§4.1).
4. **Validación.** No aplica (didáctico); solo comprobaciones internas (suma 0,5 con
   jugadores iguales).
5. **Resultados.** P(no favorito gana) (Tabla 3), con p_A = 0,55: TB7 0,346, TB10 0,321,
   TB15 0,287, TB20 0,259; con 0,60: 0,213 / 0,174 / 0,128 / 0,097; con 0,65: 0,113 / 0,078 /
   0,043 / 0,024. Longitud TB7 con 0,5: E(L) = 11,743 puntos, DE 2,905 (con 0,6: 11,208 y
   2,744). TB10 con 0,5: E(L) = 17,032, DE 3,153 (Tablas 5-6).
6. **Límites.** Declarados: ninguno salvo el nivel docente. Detectados: ignora la
   alternancia de saque (la probabilidad del TB con p de saque y resto distintos no es la de
   un p medio; no cuantifica el error); sin datos reales; Tabla 5 mal maquetada.
7. **¿Replicable?** Sí, trivial. Útil para el super-tiebreak (TB10) si se sustituye el p
   medio por la recursión con alternancia de A31.
8. **Mercados.** Tiebreak / super-tiebreak (ganador, puntos totales), partidos de dobles o
   formatos con match tiebreak.
9. **Preguntas.** (h) Fórmula cerrada para TB a X puntos (incluido TB10) y su longitud, con
   la salvedad del p medio. (c) Cerrada, sin simulación.

### B16 — Souza de Melo (2026), «Modelos de regressão para placares de jogos divididos em sets»

1. **Referencia.** Thiago Souza de Melo, tesis doctoral en Estadística (PIPGEs ICMC-USP /
   DEs-UFSCar), versión revisada enero 2026, en portugués, 79 pp. de texto (82 de PDF).
   Leídos íntegros caps. 1-5; apéndice A (derivadas, score e información de Fisher) leído
   en diagonal: solo álgebra.
2. **Modelo.** «Placar» = **número de sets ganados** (3-0, 3-1, 3-2…), no juegos por set.
   - Sets independentes (cap. 2): `P(X=x, Y=y) = C(x+y−1, k−1)·p^x(1−p)^y` si max(x,y)=k
     (ec. 2.1; binomial negativa truncada); regresión `g(p_i) = z_i'β` con enlace logit
     (también probit, cloglog, loglog), MV por BFGS, Wald/RV, residuos cuantílicos
     aleatorizados con envolvente simulada (§2.2-2.4).
   - Dependencia markoviana entre sets (cap. 3): `p0` = P(A gana el 1.er set), `p00` =
     P(A gana | ganó el anterior), `p11` = P(B gana | B ganó el anterior). Para 3 de 5
     (ec. 3.1): `a30 = p0·p00²`; `a31 = p1·p00²(1−p11) + 2p0·p00(1−p00)(1−p11)`;
     `a32 = 2p0·p00·p11(1−p00)(1−p11) + 2p1·p00(1−p11)²(1−p00) + p0(1−p00)²(1−p11)² + p1·p00²·p11(1−p11)`;
     `a03 = p1·p11²`; `a13`, `a23` simétricas (verifiqué a31 y a23 enumerando las secuencias).
   - Regresión con los tres parámetros (cap. 4): `g1(p0_i)=z_i1'β1`, `g2(p00_i)=z_i2'β2`,
     `g3(p11_i)=z_i3'β3` (ec. 4.1); score y Fisher en forma cerrada; influencia global por
     «likelihood displacement» LD_i (ec. 4.5).
3. **Datos.** (i) Eliminatorias de Copa Davis 2024: n = 12 series (marcador = partidos
   ganados, k=3); (ii) Mundial de tenis de mesa 2023, femenino, 1.ª ronda: n = 61;
   (iii) **1.ª ronda masculina de Roland Garros, Wimbledon y US Open 2024: n = 190**
   partidos a 5 sets; covariables: ranking, puntos, torneos jugados y puntos a defender de
   la ATP previos al torneo (§4.4). (El pie de la Tabla 4.2 dice «2025»: errata, el texto y
   el caso Sinner-Hanfmann son 2024.)
4. **Validación.** Simulación Monte Carlo (5000 réplicas) del sesgo y REQM del EMV
   (Tablas 2.4, 3.4, 4.1): con n ≤ 100 el modelo dependiente tiene sesgos enormes en β1
   (p.ej. 3,58 con REQM 20,9 para n=50), aceptables desde n ≈ 500. Aplicación real **solo
   dentro de muestra** (AIC/BIC, residuos, frecuencias ajustadas); sin validación temporal
   ni métricas de pronóstico (log loss, Brier).
5. **Resultados.** Grand Slams 2024 (Tabla 4.3): independiente (logit p ~ Ddrop) AIC
   630,08 / BIC 636,57; dependiente AIC 609,69 / BIC 629,17. Tabla 4.4: p0: intercepto
   −0,3306 (EE 0,3916), Dpts 0,0007 (0,0004; p=0,07); p00: intercepto 0,9520 (0,2123;
   p<0,0001), Ddrop 0,0015 (0,0009; p=0,09); p11: intercepto 0,4270 (0,2738), Rpts −0,1393
   (0,0764; p=0,07). Frecuencias (Tabla 4.6; observada / dependiente / independiente):
   3-0 64 / 64,9 / 52,9; 3-1 47 / 42,3 / 50,1; 3-2 23 / 28,9 / 36,4; 0-3 21 / 20,6 / 10,1;
   1-3 15 / 16,5 / 18,3; 2-3 20 / 16,8 / 22,4. El modelo de sets independientes con un p por
   partido infraestima los resultados desequilibrados y sobreestima los 3-2.
6. **Límites.** Declarados: otras estructuras de dependencia y correcciones de Bartlett
   como trabajo futuro (§5.0.1); en Copa Davis p no es constante (juegan distintos
   jugadores, §2.6.1). Detectados: (i) **confusión heterogeneidad/dependencia**: con
   covariables débiles (solo ranking/puntos), ganar el 1.er set revela que el jugador es
   mejor de lo que dicen las covariables; eso produce «p00 > p0» aunque los sets sean
   independientes dado el nivel real; la tesis no lo discute ni compara con un modelo de
   mezcla/efecto aleatorio; (ii) la definición `Dpts = POINTS_Y − POINTS_X` contradice la
   interpretación del signo (§4.4); (iii) muestra pequeña (190), solo hombres, solo
   1.ª ronda; (iv) no usa la estructura punto-juego-set.
7. **¿Replicable con nuestros datos?** Sí (solo necesita sets ganados y ranking/puntos,
   que tenemos para todos los partidos). Útil como **prueba de diagnóstico**: comparar las
   frecuencias 2-0/2-1/3-0/3-1/3-2 que produce nuestro motor (con incertidumbre de p
   integrada) contra las observadas; si el motor infraestima los resultados desequilibrados,
   falta varianza entre partidos o dependencia.
8. **Mercados.** Resultado exacto en sets (3-0, 3-1, 3-2 / 2-0, 2-1), total de sets.
9. **Preguntas.** (a) Evidencia (débil, dentro de muestra) de que sets IID con un p fijo
   por partido no reproducen la distribución de marcadores en sets; no separa momentum de
   heterogeneidad. (e) Ofrece la distribución conjunta a nivel set, no a nivel juego.

### T31 — Mohammadi (2026), «First server's effect on the expected number of games in tennis»

1. **Referencia.** Ali Mohammadi, preprint arXiv:2605.04867v2 [math.PR], 2 jun 2026 (9 pp.).
   Leído íntegro.
2. **Modelo.** IID con P_A, P_B constantes; juego `G(x) = x⁴·[15 − 4x − 10x²/(1 − 2x(1−x))]`
   (forma equivalente a A31; comprobado G(0,6)=0,736), `G'(x) = 20x³(1−x)³(3 + 4x(x−1))/(2(x−1)x+1)²`
   > 0 (Lema 1.1). Marcadores de set S^A_nm con las fórmulas de Newton–Keller (apéndice).
   Resultados exactos para **2 de 3 sets** con G_A ≥ G_B y G_A + G_B > 1:
   - Prop. 2.1: `T^set_A < T^set_B` (menos juegos esperados si saca primero el mejor
     sacador), vía `π7^A − π7^B = 3(G_A−G_B)(G_A+G_B−1)(G_A+G_B−2G_AG_B)(1−G_A−G_B+2G_AG_B) > 0`
     y π8, π9, π10 análogos; π6, π12, π13 no dependen del primer sacador.
   - Prop. 2.2: margen de juegos `H^set_A > H^set_B`.
   - Claim 3.1 y Props. 3.2-3.3: el efecto en el partido es
     `T^match_A − T^match_B = (T^set_A − T^set_B)(M_A − M_B)`, con
     `M_A − M_B = 1 + x + y + 2xy > 0` (x = α_e − γ_o, y = β_e − δ_o, paridad de la longitud de
     cada set): el sacador del set siguiente se propaga por la paridad de juegos.
3. **Datos.** Resultados de Jeff Sackmann 2010-2024 (≈30.000 partidos por circuito en la
   Fig. 4): ATP 32.059 partidos, primer sacador inferido en 14.324 (44,7 %); WTA 38.409 y
   16.161 (42,1 %) (Tabla 1), deduciendo el sacador de la paridad de juegos y de los juegos
   de saque/breaks registrados (§4.4).
4. **Validación.** Numérica para la teoría (malla 0,50 ≤ P_B ≤ P_A ≤ 0,70). La parte empírica
   calcula residuos «total observado − esperado» con P_W y P_L **del propio partido**
   (porcentajes de saque realizados), separados por ganador/perdedor: es análisis
   dentro de muestra condicionado al resultado, no pronóstico.
5. **Resultados.** El primer sacador desplaza el total esperado y el margen **hasta ~0,4
   juegos** (Figs. 1-2), más relevante en mercados del 1.er set que del partido (§4.1);
   P(total > 19,5) cambia hasta ~9 pp con P_A=0,7, P_B=0,6 (máximos en 19,5 con (0,7; 0,6)
   y en 21,5 con (0,7; 0,55), Fig. 3). Residuos de juegos totales (Tabla 2): ATP, saca
   primero el perdedor: media 1,847 (DE 4,221, EE 0,059, n=5135); el ganador: 0,201 (4,080;
   0,043; 9189); WTA 1,332 (3,744; 0,046; 6677) y 0,582 (3,677; 0,038; 9484). Sesgo medio del
   modelo IID: **infraestima el total en 0,79 juegos (ATP, EE 0,035) y 0,89 (WTA, EE
   0,029)** (Tabla 3), concentrado en partidos igualados (P_W ≈ P_L, Fig. 4). Logit «el
   ganador sacó primero» ~ ΔS = P_W − P_L: β = 2,027 (OR 7,59; IC 5,17-11,15) ATP y 0,587
   (OR 1,80; 1,29-2,51) WTA (Tabla 4).
6. **Límites.** Declarados: el supuesto de p constante es más frágil en partidos igualados
   (§4.3). Detectados: (i) P_W, P_L son porcentajes realizados (fuga total si se leyera como
   pronóstico); (ii) sacador identificable solo en ~43-45 % (selección no aleatoria); (iii)
   la diferencia de residuos ganador/perdedor (1,6 juegos ATP) es 4 veces mayor que el
   efecto teórico máximo (0,4) y está condicionada al resultado: no mide el efecto del
   saque inicial; (iv) la lectura «los mejores eligen sacar» de la Tabla 4 también está
   confundida por usar ΔS realizado y la identidad del ganador; (v) solo 2 de 3 sets; la
   «ineficiencia» de casas que no actualizan tras el sorteo (Observación 4.1) no se prueba.
7. **¿Replicable con nuestros datos?** Sí: la teoría solo pide p de saque; la inferencia
   del primer sacador exige juegos de saque o breaks por jugador (Sackmann sí los trae
   para gran parte del ATP). El sesgo +0,8 juegos en partidos igualados es contrastable
   con nuestro histórico de marcadores por set.
8. **Mercados.** Totales de juegos (partido y 1.er set), hándicap de juegos; efecto nulo
   sobre ganador y sets.
9. **Preguntas.** (f) Cuantifica el efecto del primer sacador bajo IID: ≤0,4 juegos de
   media y ≤~9 pp en una línea de totales; si no se conoce, la mezcla 50/50 es la marginal
   correcta (más ancha que cada condicional) y el sacador de los sets siguientes debe
   propagarse por paridad. (a) Indicio de violación: el modelo IID con p constante
   infraestima los juegos totales ~0,8-0,9 en promedio, sobre todo en partidos igualados.
   (e) Totales y margen deben salir de la misma distribución de marcadores por set.

### T32 — Peña, Das y Wu (2026), «"Game, Set, Match": Double Delight Watching a Grand Slam Tennis Match»

1. **Referencia.** E.A. Peña, D. Das, Y. Wu (Univ. South Carolina), preprint
   arXiv:2603.02360v2 [math.PR], 18 oct 2026 (41 pp.). Artículo pedagógico-teórico. Leído
   íntegro.
2. **Modelo** (IID, p_A y p_B constantes; reglas actuales de Grand Slam: TB a 7 en sets
   1-4 / 1-2 y **TB a 10 en el set decisivo**).
   - Deuce: `θ_GT(p) = p²/(p² + q²)`; juego `θ_G(p) = p⁴ + 4p⁴q + 10p⁴q² + 20p³q³·θ_GT(p)`
     (Teor. 2.3); fmp del nº de puntos del juego en forma cerrada (Teor. 2.4) y media y
     varianza (Teor. 2.5): con p=0,5, media 6,750, var 7,6875; con p=0,6, media 6,484, var
     6,708, retención 0,736 (Tabla 2).
   - «Tiebreak del tiebreak» (desde K−1 iguales): `θ_STT = p_A q_B/(p_A q_B + q_A p_B) = OR/(1+OR)`,
     OR = (p_A/q_A)/(p_B/q_B) (Prop. 3.2); termina con probabilidad 1 salvo p_A=p_B∈{0,1}.
   - Tiebreak a K puntos (Prop. 3.4): `θ_ST(p_A,p_B,K) = P{Bin(K−1,p_A) + Bin(K−1,q_B) ≥ K} + P{… = K−1}·θ_STT`
     (en los primeros 2K−2 puntos cada uno saca K−1 veces); `θ_ST(p,p,K) = 1/2` (Cor. 3.4.1);
     fmp del nº de puntos (Teor. 3.5): con 0,5/0,5 y K=7, media 11,744, DE 2,909; con
     0,9/0,9, media 16,07, DE 8,48 (Fig. 5).
   - Set (Teor. 3.6): `θ_S = P{Bin(5,θ_G(p_A)) + Bin(5,1−θ_G(p_B)) ≥ 6} + P{… = 5}·[θ_G(p_A)(1−θ_G(p_B)) + {θ_G(p_A)θ_G(p_B) + (1−θ_G(p_A))(1−θ_G(p_B))}·θ_ST]`;
     probabilidad de cada marcador θ_S(6,h), θ_S(7,5), θ_S(6,6) y media/varianza de puntos
     por esperanza y varianza iteradas (Teor. 3.7).
   - Partido 2Q+1 sets con K0 (sets normales) y K1 (decisivo) (Teor. 4.1):
     `θ_M = P{Bin(Q,θ_S(K0)) + Bin(Q,1−θ_S(p_B,p_A,K0)) ≥ Q+1} + P{… = Q}·θ_S(K1)`; fmp
     conjunta de sets ganados (binomial negativa truncada en sets, porque el set es neutral
     al saque).
3. **Datos.** Ninguno empírico (solo anécdotas de tiebreaks largos). Simulación propia en R
   con 50.000 réplicas para verificar las fórmulas (§4.3).
4. **Validación.** Teoría frente a simulación (Tabla 7): diferencias ≤ ~0,004 en todas las
   probabilidades (p.ej. P(gana el set el primer sacador) 0,66946 simulada vs 0,66948;
   partido 0,79472 vs 0,7948). Sin validación contra partidos reales.
5. **Resultados.** Con p_A=0,60, p_B=0,55 (Tablas 4, 6, 7): set 0,669 (TB 0,138; media 64,4
   puntos, var 267); partido a 5 sets 0,795 (3-0 0,300; 3-1 0,298; 3-2 0,197; media 254,9
   puntos, DE ≈ 61). **El marcador exacto del set depende mucho de quién saca primero**
   aunque la probabilidad de ganar el set no: A gana 6-1 con 0,0947 si saca primero y 0,0485
   si saca B; 6-2: 0,0952 vs 0,1414; 6-3: 0,2042 vs 0,1046; 6-4: 0,1053 vs 0,2049; las
   sumas 6-1+6-2 y 6-3+6-4 coinciden (Tabla 7). La media de puntos del TB y del set también
   depende del primer sacador (Prop. 3.4 y §3.5). Al subir K del TB el favorito gana más
   (Fig. 18). Eficiencias (Tabla 9, prior Be(2,1)⊗Be(2,1)): set 0,7046 con TB7, partido a 5
   con TB10 final 0,7814… (tabla mal maquetada; ver texto). Un «mejor de 45 juegos» con
   desempate por 2 juegos iguala la eficiencia del 3 de 5 sets.
6. **Límites.** Declarados: IID «unrealistic» (momentum, público, lesiones), aceptado como
   aproximación (§6); la duración del partido se calcula suponiendo que A saca primero en
   todos los sets y se corrige promediando 50/50 (aproximación, §4.2). Detectados: sin
   datos; la errata «μ_ST(.6,.55,7)» por K=3 (§3.3); Tabla 9 desordenada en el PDF.
7. **¿Replicable?** Totalmente (fórmulas cerradas). Es la referencia más completa y al día
   para TB10 en el set final y para la distribución del número de puntos.
8. **Mercados.** Ganador, sets exactos, marcador exacto del set, tiebreak (prob. y
   duración), super-tiebreak/TB10, número de puntos; base para juegos totales.
9. **Preguntas.** (c) Todo en forma cerrada: no hace falta Monte Carlo bajo IID. (d) Con
   50.000 réplicas el error frente a la fórmula es ≤ ~0,004 (coherente con 1/√N). (f) El
   primer sacador no cambia ganador ni set, pero cambia mucho los marcadores exactos
   (6-3 vs 6-4) y la duración: la mezcla 50/50 es imprescindible en marcador exacto.
   (h) TB7, TB10 y «tiebreak del tiebreak» con fórmula cerrada y fmp de la longitud.

