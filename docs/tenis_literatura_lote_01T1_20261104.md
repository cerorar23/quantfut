# Literatura de tenis — lote 01T1 (T01–T08), lectura completa

Fecha: 4-nov-2026. Proyecto sin fines de lucro. Objetivo: extraer de los artículos (no de sus resúmenes) lo que sirve
para rediseñar desde cero el motor de pronósticos de tenis ATP/WTA.

**Fuente.** `BIBLIOTECA_TENIS_COMPLETA/pdfs/01_modelos/T01…T08` (índice `INDICE_COMPLETO.txt`, usado solo para
metadatos). Texto extraído con `pdftotext -enc UTF-8` (modos `-layout` y normal); los ocho PDF tienen capa de texto
(ninguno escaneado). Leí cada texto íntegro, incluidos apéndices y referencias; además miré como imagen las páginas
con cifras que solo están en figuras: T01 pp. 5–6 (Figs. 2–4) y T07 p. 13 (Fig. 16).

**Convenciones.** «[Declarado]» = lo dice el artículo; «[Detectado]» = observación mía al leerlo; «(inferencia mía)»
= propuesta o cálculo mío, no del artículo. «No consta» = el artículo no lo dice. Páginas = numeración impresa del
artículo (en T06, que no la imprime, página del PDF). Nuestros datos de referencia: resultados con marcador por set y
tie-break (TML/Tennis-Data/SofaScore/API-Tennis), ranking y puntos, superficie, ronda, nivel, edad/altura/mano,
duración por set (solo SofaScore, solo posterior al partido), cuotas de cierre Pinnacle/bet365 (Tennis-Data), Match
Charting Project (MCP, punto a punto, ~7,6 mil ATP y ~4,3 mil WTA), **sin** estadísticas de saque/resto ni aces de
forma sistemática.

**Aviso de lote.** De los ocho estudios, solo dos son modelos **pre-partido** con validación temporal (T05 y T08);
T01 es en vivo con una pieza pre-partido aprovechable; T02 es pre-partido pero con fuga; T03, T04, T06 y T07 son
estudios de «momentum» dentro del partido, tres de ellos ligados al concurso MCM 2024 sobre los mismos datos de
Wimbledon 2023.

<!-- TABLA_RESUMEN -->

## (b) Fichas detalladas

### T01 — Xie y Muppidi (2026), «Forecasting the Winner of a Live Tennis Match»

**1. Referencia.** T01. Charles Xie (estudiante, Natick High School, EE. UU.) y Aneesh Muppidi (mentor, Universidad
de Oxford). Preprint arXiv:2609.07617v1 [cs.LG], 7-sep-2026, 9 pp. Sin revisión por pares. Código publicado
(github.com/cx-57/live-tennis-research; no lo ejecuté).

**2. Modelo (§2.2 y §3, pp. 2–4).** Cinco modelos que se apilan:

- *Elo pre-partido* (§2.2, p. 2), «como Kovalchik»: todos empiezan en 1500, orden cronológico, Elo separado ATP y
  WTA, no por superficie, guardado antes del resultado.
  `q_i,t = 1 / (1 + 10^((R_j,t − R_i,t)/400))` (ec. 1);
  `R_i,t+1 = R_i,t + K_i,t·(S_i,t − q_i,t)`, `K_i,t = 250 / (m_i,t + 5)^0,4` (ec. 2), con `m` = partidos previos.
- *Recursión de Markov del marcador* (§3.1, p. 3), columna vertebral de todos salvo el HGBM. Estado
  `s = (S1, S2, G1, G2, P1, P2, σ, τ, b)` (sets, juegos, puntos codificados 0/15/30/40/AD = 0–4, sacador, tie-break,
  formato). Probabilidad de ganar el punto: `q = p1` si saca J1, `q = 1 − p2` si saca J2 (ec. 3).
  `V(s) = q(s)·V(T1(s)) + (1 − q(s))·V(T2(s))` (ec. 5); terminal `V = 1` si `S1 = m(b) = ⌈b/2⌉`, `V = 0` si
  `S2 = m(b)` (ec. 6); desde deuce `D(q) = q² / (q² + (1 − q)²)` (ec. 7); tie-break con orden de saque 1,2,2,1,1,2,2…
  (ec. 8). Supone puntos independientes con probabilidad constante por sacador (implícito; no se contrasta).
- *Markov simétrico* (§3.2): `pa = pb = p`; p elegido en validación en {0,60…0,65}: 0,65 / 0,64 / 0,60 a 25/50/75 %
  del partido. Aísla el valor del marcador.
- *Markov Elo-asimétrico* (§3.3, p. 3): `d = Elo1 − Elo2` (ec. 10); `e = clip(α·d, −0,15, 0,15)` (ec. 11);
  `pa = clip(β + e, 0,45, 0,88)`, `pb = clip(β − e, 0,45, 0,88)` (ec. 12–13); β = probabilidad media de ganar el punto
  al saque (rejilla 0,59–0,65), α en {4, 6, 9, 13, 18, 22}·10⁻⁵. Elegidos (β, α) = (0,64; 1,3·10⁻⁴), (0,59; 1,3·10⁻⁴),
  (0,59; 1,3·10⁻⁴) a 25/50/75 %. (Inferencia mía: con α = 1,3·10⁻⁴, una diferencia de 200 puntos Elo da e = 0,026,
  es decir ±2,6 pp de probabilidad de punto al saque; el tope de 0,15 exige ~1150 puntos.)
- *Serve-shrink* (§3.4, pp. 3–4), versión simplificada del enfoque bayesiano de Colin y Bechler (A14 del índice):
  `θ̂ = n/(n+κ)·θ̂_vivo + κ/(n+κ)·θ_prior` (ec. 14);
  `pa = (n1·r1 + κ·π1)/(n1 + κ)`, `pb = (n2·r2 + κ·π2)/(n2 + κ)` (ec. 15), con π = probabilidad al saque del Elo,
  r = % de puntos al saque ganados en el partido, n = puntos al saque observados. κ ∈ {40, 80, 160, 320, 640}:
  elegido 640 / 160 / 40 a 25/50/75 % (más prior al principio).
- *HGBM* (§3.5, p. 4): `p̂_H = g(z)`, `HistGradientBoostingClassifier` de scikit-learn solo con marcador y rasgos en
  vivo; 4 configuraciones (lr, iteraciones, hojas, L2) por log-loss de validación; XGBoost y LightGBM probados y
  descartados.
- *Trace* (§3.6, p. 4): `x(s) = [p̂_M, p̂_S, logit p̂_M, logit p̂_S, p̂_S − p̂_M, z(s)]` (ec. 17),
  `p̂_Trace = f(x(s))` (ec. 19), f = HGBM (lr ∈ {0,03; 0,05}, hojas ∈ {7; 15}, L2 ∈ {1; 3}, ≤250 iteraciones, parada
  temprana). Un modelo distinto por punto de control (semillas 19/30/6).

**3. Datos (§2, pp. 1–2; Tablas 1 y 3).** Jeff Sackmann: Grand Slam point-by-point (marcador, sacador, ganador del
punto, resultado del saque, longitud del rally, break points) y resultados ATP/WTA para el Elo (año de inicio del Elo:
no consta). Tras limpieza: 8.222 partidos de Grand Slam (ATP 4.181; WTA 4.041) y 1.505.355 estados-punto.
Entrenamiento 2011–2021: 6.774 partidos / 1.238.084 puntos; validación 2022: 473 / 87.439; prueba 2023–2024:
975 / 179.832. Excluidos 2.286 partidos brutos (21,8 %); Elo emparejado en 7.896 (96,0 %). Filtros: marcador final
válido, ganador con 2 o 3 sets, >20 puntos, sacador y ganador identificables (fuera walkovers). Rasgos: marcador
(best_of, sets, juegos, puntos, sacador, tie-break), % de puntos ganados al saque y su n antes del punto, longitud
media de rally (total y reciente), tasa de aces, diferencias de sets/juegos/puntos, puntos jugados.

**4. Validación (§2.3 y §4).** [Declarado] Temporal estricta: 2011–2021 entrenamiento, 2022 validación/ajuste,
2023–2024 prueba; reentreno en entrenamiento+validación antes de la prueba. Métricas: precisión a 25/50/75 % del
partido y sobre todos los puntos; log-loss binaria (ec. 20) a 25/50/75 %; diagrama de fiabilidad por intervalos
(ec. 21–22, Fig. 3). Referencias: Markov simétrico (solo marcador), Elo-asimétrico, HGBM sin Markov; DeepTennis
(Lerner et al. 2019) solo como contexto. **Sin cuotas.** Fuga: [Declarado] ninguna (Elo antes del partido, rasgos
anteriores al punto). [Detectado] (i) el punto de control «25 % del partido» se fija con la longitud total del
partido, que solo se conoce al final, y hay modelos y parámetros (p, β, κ) distintos por punto de control: en vivo no
se sabe en qué % del partido se está, y en ese corte el rasgo `pts_played` codifica la longitud final (fuga sutil
por selección de estados); (ii) la precisión «sobre todos los puntos» promedia ~180 mil estados muy autocorrelados de
solo 975 partidos y no lleva intervalos; (iii) la Tabla 6 reevalúa con el esquema no cronológico de DeepTennis
(2011–2019, desarrollo 2017, prueba 2014) y los autores advierten de su posible fuga.

**5. Resultados (Tablas 4–6, pp. 5–7).**

| Modelo | Acc 25 % | Acc 50 % | Acc 75 % | Acc todos | LL 25 % | LL 50 % | LL 75 % |
|---|---|---|---|---|---|---|---|
| Markov simétrico | 0,6851 | 0,7703 | 0,8544 | 73,21 % | 0,6292 | 0,5363 | 0,3498 |
| Markov Elo-asimétrico | 0,7575 | 0,8050 | 0,8648 | 77,56 % | 0,5210 | 0,4549 | 0,3096 |
| Serve-shrink | 0,7564 | 0,7946 | 0,8720 | 77,68 % | 0,5142 | 0,4266 | 0,2842 |
| HGBM | 0,6944 | 0,7918 | 0,8738 | 73,98 % | 0,5376 | 0,3788 | 0,2299 |
| Trace | 0,7606 | 0,8215 | 0,8834 | 77,84 % | 0,4753 | 0,3530 | 0,2002 |

Esquema no cronológico (Tabla 6): Trace 77,66 / 83,84 / 88,96 / 81,30 %; Elo-asimétrico 77,40 / 83,05 / 88,70 /
81,12 %. Figura 2 (lectura aproximada mía): hacia el 5 % del partido los tres modelos con Elo rondan el 71 % y los dos
sin Elo el 57–59 %. Figura 4 (lectura aproximada): al inicio ≈ 69 % ATP y ≈ 72 % WTA; la curva WTA oscila más.
Figura 3: calibración razonable a 25 y 50 %; a 75 % se aparta en el tramo 0,45–0,6. Hallazgos declarados: el
serve-shrink mejora sobre todo el log-loss, no la precisión (p. 7); el HGBM es débil al principio y el mejor modelo
individual al final; Trace gana en todos los cortes, con ventaja máxima entre el 40 y el 70 %.

**6. Límites.** [Declarado] (§5, pp. 7–8): solo saque (sin resto); sin superficie (Elo único); sin fatiga, lesiones,
clima, mano ni estilo; solo Grand Slams, quizá no generalizable al circuito. [Detectado] es **en vivo**: lo único
trasladable a pre-partido es la cadena Elo → p_saque → Markov (y la idea de encoger hacia el prior); la tabla no da el
punto 0 % (solo se ve en las figuras); un único β para ATP y WTA (no consta separación por circuito); diferencias
entre modelos sin intervalos ni contraste (Trace vs serve-shrink: 0,16 pp sobre todos los puntos); punto de control
dependiente del futuro; sin comparación con cuotas en vivo.

**7. ¿Replicable con nuestros datos?** Sí la parte pre-partido: Elo con la K de Kovalchik desde nuestros resultados y
la recursión de Markov para P(set), P(partido), sets exactos, juegos y tie-breaks. El artículo afina α y β por log-loss
del ganador en vivo; sin estadísticas de saque, podríamos estimar β (por circuito y superficie) y α por máxima
verosimilitud sobre los marcadores por set y tie-breaks que sí tenemos (inferencia mía). La parte en vivo
(serve-shrink, HGBM con rally y aces) solo con MCP o con el repositorio Grand Slam point-by-point de Sackmann (no está
en nuestra lista de datos).

**8. Mercado.** Ganador en vivo. Pre-partido, la pieza Elo→Markov serviría para ganador, sets, hándicap de juegos y
sets, total de juegos y probabilidad de tie-break (no evaluado en el artículo).

**9. Temas transversales.** IID: supuesta dentro del Markov, no contrastada; el HGBM capta no linealidades que el
Markov no, sin atribuirlas a momentum. Saque vs resto: solo saque. Superficie: no; oponente: vía diferencia Elo.
Ratings: Elo con K decreciente, cobertura 96 %. Fatiga/descanso: no. Mercado: no; cita (no resultado propio) que en
Kovalchik (2016) el Elo de carrera quedó segundo tras las cuotas con ~70 % de acierto. Micro-eventos: aces y rally
como rasgos; tie-break en la recursión. Retiradas/walkovers: excluidos. Poca historia: K decreciente con los partidos
y seudoconteo κ hacia el prior; no se evalúa aparte. ATP vs WTA: la WTA oscila más en vivo; explicación propuesta,
no contrastada: menor ventaja al saque (cita retención de saque ≈79 % hombres vs ≈66 % mujeres).

<!-- FIN_FICHAS -->
