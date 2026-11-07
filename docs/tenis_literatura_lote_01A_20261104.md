# Tenis — literatura, lote 01A: modelos (A01, A04, A05, A07, A10, A12, A14, A17, A21, A22, B08)

Fecha: 2026-11-04. Rediseño desde cero del motor de pronósticos de tenis ATP/WTA.
Lote: los PDF que empiezan por `A` y `B08_` de
`BIBLIOTECA_TENIS_COMPLETA/pdfs/01_modelos/`. El índice (`INDICE_COMPLETO.txt`)
solo trae metadatos (título, autores, fecha, idioma, tipo, tema): no trae resúmenes.
Texto extraído con `pdftotext -layout`; las tablas se verificaron con
`pdftotext -raw` porque el modo `-layout` desordena columnas (en A01, A04, A05 y A07
el modo `-layout` asignaba cifras a la fila equivocada). Las letras griegas de
algunas fórmulas se pierden en la extracción; cuando pasa, se indica.

Convenciones: cada afirmación de un estudio cita página (pág. del PDF o de la
numeración impresa, se indica cuál) o sección. «No consta» = el documento no lo dice.
«Detectado» = juicio nuestro, no del autor.

Estado: en redacción (las fichas se añaden al terminar cada estudio).

## (a) Tabla resumen

(se completa al final)

## (b) Fichas por estudio

### A01 — Kovalchik (2016), «Searching for the GOAT of tennis win prediction»

**1. Referencia.** A01. Stephanie A. Kovalchik (Tennis Australia / Victoria University).
2016. Artículo de revista: *Journal of Quantitative Analysis in Sports* 12(3):127-138.

**2. Modelo.** Comparación de 11 modelos publicados + un consenso de casas (Tabla 1, pág. 128):

- Regresión. Forma general probit `π_ij = Φ(x_ij)` (pág. 128).
  - *Logistic* (Klaassen y Magnus 2003): `log(π_ij/(1−π_ij)) = β·log(R_i/R_j)` (ec. 1; el
    coeficiente se pierde en la extracción; el log del cociente de rankings es el único predictor).
  - *Basic probit* (Boulier y Stekler 1999): diferencia de cabezas de serie + indicador de
    rival no cabeza de serie.
  - *Probit plus* (Del Corral y Prieto-Rodríguez 2010): diferencia de ranking, top-10 en
    carrera, altura, edad, mano, ronda, nivel de torneo.
  - *Prize probit* (Gilsdorf y Sukhatme 2008): diferencia de premio en juego, edad, H2H,
    rondas restantes, diferencia de puntos ATP, victorias de carrera en la superficie,
    indicador Masters o superior (Tabla 2, pág. 129).
- Por punto (supuesto IID; probabilidad de partido en forma cerrada a partir de la
  probabilidad de ganar el punto al saque y al resto):
  - *Basic IID* (Newton y Keller 2005): % de puntos ganados al saque y al resto en los 12
    meses previos.
  - *Opponent-adjusted IID* (Barnett y Clarke 2005): media del torneo ajustada por la
    ventaja al saque del jugador y la ventaja al resto del rival.
  - *Low-level IID* (Spanias y Knottenbelt 2012): estados del punto al saque (ace, punto con
    primer saque…), promediados y ajustados por rival.
  - *Common-opponent IID* (Knottenbelt, Spanias y Madurska 2012).
- Comparación por pares:
  - *Bradley-Terry* (McHale y Morton 2011): `π_ij = α_i/(α_i+α_j)` (ec. 2), habilidades
    estimadas con **juegos** ganados y decaimiento exponencial:
    `l(α) = Σ_i Σ_{j∈M_i} exp(λ·(t−t_j))·[g_ij·log α_i + (g_j−g_ij)·log α_k(i) − g_j·log(α_i+α_k(i))]`
    (ec. 3; el símbolo del parámetro de semivida se pierde en la extracción). Estratificado
    por superficie.
  - *Elo FiveThirtyEight*: `E_i(t+1) = E_i(t) + K·(π̂_ij(t) − W_i(t))` (ec. 4, impreso así;
    el signo estándar es `W − π̂`, probable errata), `K = 250/(m(t)+5)^0.4` con `m(t)` =
    partidos de carrera, ×1.1 en Grand Slam; `π̂_ij(t) = [1 + 10^((E_j(t)−E_i(t))/400)]^(−1)`
    (ec. 5); arranque 1500 (pág. 130).
- *Bookmaker consensus model* (BCM, Leitner, Zeileis y Hornik 2009):
  `logit(π̂_ij) = K^(−1)·Σ_k logit(π̂_ijk)`, con margen quitado por el método de Shin (1993)
  (ec. 6, págs. 130-131).

**3. Datos.** Validación: 2.395 partidos ATP individuales de 2014, excluidos 105 walkovers o
retiradas (pág. 131). 20,1 % Grand Slam, 22,9 % Masters, 57,0 % resto; 55 % dura, 33 %
tierra, 12 % hierba; ganó el mejor clasificado el 68,1 % (Tabla 3). Entrada: ventana móvil
de 52 semanas (salvo predictores de carrera); Elo desde inicio de 2013 (538-1) o de carrera
(538-2); BT1 con 1 año, BT2 con 2 años y peso ½ al año más antiguo. Grand Slam + ATP por
encima de Challenger. BCM: cuotas previas de 7 casas de tennis-data.co.uk. Datos con el
paquete R `deuce`. Faltantes imputados a la media del grupo de ranking (<100 / ≥100).

**4. Validación.** Temporal fuera de muestra: toda la temporada 2014, cada predicción con datos
anteriores (ventana móvil). Métricas (pág. 132): precisión; **cociente de calibración** =
Σ prob. del mejor clasificado / victorias del mejor clasificado (IC 95 %); log-loss;
discriminación = media de prob. en victorias del favorito − media en sorpresas (IDI).
Referencia: BCM. Fuga: no detectada (ranking «at the time of the match»; parámetros de los
modelos publicados, no ajustados con 2014).

**5. Resultados** (Tabla 4, pág. 133; verificada con `-raw`):

| Modelo | Precisión % | Calibración (IC 95 %) | Log-loss | Discrim. % |
|---|---|---|---|---|
| Media regresión | 65 | 0,96 (0,94-0,99) | 0,61 | 5 |
| Basic probit | 59 | 0,92 (0,88-0,97) | 0,63 | 3 |
| Prize probit | 68 | 0,98 (0,93-1,03) | 0,61 | 4 |
| Probit plus | 67 | 0,98 (0,93-1,03) | 0,60 | 7 |
| Logistic (ranking) | 67 | 0,97 (0,92-1,02) | 0,60 | 6 |
| Media por punto | 64 | 0,91 (0,88-0,93) | 0,66 | 9 |
| Basic IID | 63 | 0,89 (0,85-0,93) | 0,67 | 7 |
| Opponent adjusted | 67 | 0,98 (0,93-1,03) | 0,63 | 9 |
| Low level | 64 | 0,87 (0,83-0,91) | 0,68 | 12 |
| Common opponent | 63 | 0,89 (0,84-0,93) | 0,66 | 7 |
| Bradley-Terry 1 | 62 | 0,80 (0,76-0,83) | 0,67 | 3 |
| Bradley-Terry 2 | 65 | 0,80 (0,76-0,84) | 0,65 | 3 |
| Elo 538 (1 año) | 67 | 0,98 (0,93-1,03) | 0,60 | 9 |
| Elo 538 (carrera) | 70 | 1,03 (0,98-1,08) | 0,59 | 11 |
| BCM (casas) | 72 | 0,98 (0,93-1,03) | 0,55 | 14 |

Por subgrupo (Tabla 5, pág. 134, precisión %): top-30 vs resto — regresión 74 vs 56, punto
70 vs 58, Elo carrera 75 vs 64, BCM 76 vs 67. Grand Slam / Masters / 250-500 — Elo carrera
74/72/67, BCM 78/72/70. Tierra / hierba / dura — Elo carrera 67/72/71, BCM 70/76/72.
La historia de carrera sube el Elo en jugadores fuera del top 30 de 59 % a 64 %, sin cambio
en el top 30 (75 %) (pág. 134-135). Los modelos IID (salvo opponent-adjusted) y BT
**subestiman al favorito** (predicen más sorpresas de las que hay) (pág. 132).

**6. Límites.** Declarados (pág. 137): un solo año; sin WTA; solo pre-partido (no evalúa
actualización en juego, «fortaleza potencial» de los modelos por punto). Detectados: la
calibración se mide con un cociente agregado, no con curvas por tramos; no hay pruebas de
significación entre modelos en precisión ni log-loss; «pre-match odds» sin decir si son de
cierre; el Elo no incluye Challengers, lo que puede explicar parte del peor rendimiento
fuera del top 30; los modelos por punto usan parámetros tal como se publicaron.

**7. ¿Replicable con nuestros datos?** Sí: Elo 538 (resultados + recuento de partidos de
carrera), logit de ranking, Probit plus (ranking, edad, altura, mano, ronda, nivel), BT con
juegos (marcador por set) y BCM con Shin (cuotas de Tennis-Data). Parcial: Prize probit
(premios: no constan en nuestras fuentes). No: los cuatro modelos IID necesitan % de puntos
ganados al saque/resto (y el low-level, aces y primeros saques), que no tenemos de forma
sistemática; solo con el MCP, muestra sesgada hacia partidos destacados.

**8. Mercado.** Ganador del partido. (BT por juegos e IID podrían servir para juegos y
hándicap, pero el artículo no lo evalúa.)

**9. Temas transversales.** IID: «se sabe incorrecto» pero buena aproximación (Klaassen y
Magnus 2001); no comprobado en partidos recientes; relajarlo podría reducir el sesgo de los
modelos por punto (pág. 136). Superficie: BT estratificado; tierra es la superficie peor
predicha. Ajuste por rival: el IID ajustado por rival es el único modelo por punto bien
calibrado; el Elo ajusta por rival en cada partido. Ratings: Elo > BT; el BT con juegos es
el peor calibrado (0,80) — la autora lo atribuye a medir habilidad por juegos en vez de
partidos (pág. 137). Mercado: BCM gana en todas las métricas; ningún modelo le gana.
Retiradas/walkovers: excluidos de la validación. Poca historia: imputación a la media del
grupo de ranking; todos los modelos pierden 10-20 pp fuera del top 30. Fatiga, micro-eventos,
momentum: no constan.

### A04 — Candila (2023), «welo: An R package for weighted and standard Elo rates»

**1. Referencia.** A04. Vincenzo Candila (Univ. de Salerno). 2023. Artículo de revista
(*Statistica Applicata – Italian Journal of Applied Statistics* 35(1)). Es un artículo de
software: describe el paquete R `welo`, con un único ejemplo numérico; no es un estudio de
validación amplio.

**2. Modelo** (sección 2, págs. 3-5; numeración impresa).
- Elo: `p̂_ij(t) = 1/(1 + 10^((E_j(t)−E_i(t))/400))` (ec. 1);
  `E_i(t+1) = E_i(t) + K_i(t)·[W_i(t) − p̂_ij(t)]` (ec. 2).
- WElo (Angelini, Candila y De Angelis 2022, EJOR):
  `E*_i(t+1) = E*_i(t) + K_i(t)·[W_i(t) − p̂*_ij(t)]·f(G_ij(t))` (ec. 3), con
  `f = NG_i/(NG_i+NG_j)` si i ganó y `f = NG_j/(NG_i+NG_j)` si i perdió (ec. 4); `NG` = juegos
  ganados. Es decir, la actualización se multiplica por la cuota de juegos del **ganador**:
  una victoria ajustada mueve menos el rating que una paliza. Variante con sets (ec. 5).
- `K_i(t) = 250/(N_i(t)+5)^0.4` (ec. 6, tomada de Kovalchik 2016), `N_i` = partidos jugados;
  alternativas: K constante, o K×1,1 si es Grand Slam o una superficie elegida. Arranque 1500.
  Errores estándar de los ratings por bootstrap (Angelini et al. 2022; B=1000, α=0,05).
- Regla de apuesta (ec. 7, pág. 13): apostar 1 $ si `P̂_ij(t)/q_ij(t) > r` y `q_ij(t) > q`, con
  `q_ij` = inversa de la cuota de **Bet365** (probabilidad implícita sin quitar margen). Se
  cobra por defecto a la **mejor cuota entre todas las casas** («Best_odds», pág. 14).

**3. Datos.** Ejemplo: tennis-data.co.uk, ATP 2021: 2.489 partidos → 1.771 tras la función
`clean` (307 → 121 jugadores) (págs. 5-6). La limpieza quita partidos incompletos, faltantes
de cuota B365, ranking, juegos o sets, cuotas B365 iguales, **jugadores con <10 partidos en
la base** (MNM=10) y jugadores con ranking >500 (MRANK=500).

**4. Validación.** El Elo es secuencial (cada probabilidad usa solo partidos previos), pero no
hay periodo de calentamiento: todos arrancan en 1500 en enero de 2021 y se evalúan los 1.771
partidos (el autor admite que hace falta *burn-in*, pág. 11). Métricas: Brier y log-loss;
ROI con IC bootstrap (R=2000, α=0,1, es decir IC 90 %) y comparación con apuestas al azar
con los mismos filtros. Sesgos detectados: (i) el filtro MNM=10 usa los partidos de todo el
año (información futura: selección de supervivientes); (ii) se quitan retiradas y partidos
sin cuota; (iii) r y q no se eligen fuera de muestra y se publican 7 valores de r
(comparaciones múltiples); (iv) cobro a la mejor cuota del mercado.

**5. Resultados** (págs. 7-15).
- Brier / log-loss sobre 1.771 partidos: por juegos y K variable, WElo 0,2274 / 0,6451 frente
  a Elo 0,2325 / 0,6581; WElo por sets 0,2301 / 0,6521; K=100 constante: WElo 0,2274 /
  0,6450, Elo 0,2340 / 0,6619; K×1,1 en Grand Slam: WElo 0,2272 / 0,6447, Elo 0,2325 / 0,6584;
  arranque 1000 = arranque 1500.
- ROI con q=0,3 (cobro a mejor cuota): WElo r=1,00: 1.002 apuestas, +10,05 % (IC90 3,48 a
  16,22) … r=1,30: 265 apuestas, +16,58 % (1,60 a 31,78). Elo r=1,00: 1.096 apuestas, +6,91 %
  (1,43 a 12,67) … r=1,25: 409, +9,31 % (−1,19 a 20,27); r=1,30: 329, +11,56 % (−0,77 a
  23,22).
- **Apuesta al azar** con los mismos filtros: WElo +2,59 % a +4,29 %; Elo +2,33 % a +3,51 %
  (pág. 15). Que apostar al azar dé ROI positivo indica que el ROI está inflado por el cobro
  a la mejor cuota y por los filtros, no solo por el modelo (detectado).
- Finales de Grand Slam 2021 (Tabla 2, pág. 10): p.ej. US Open Djokovic 1943,4 vs Medvedev
  1837,0, p̂=0,649 (ganó Medvedev).

**6. Límites.** Declarados: hace falta calentamiento. Detectados: un año, sin conjunto de
prueba separado; sin prueba de significación de la diferencia de Brier WElo–Elo; no compara
con la probabilidad del mercado como pronóstico; el autor llama «inesperado» que el arranque
1000 dé lo mismo que 1500, cuando es matemáticamente obligado (todos arrancan igual y solo
cuentan diferencias), lo que resta confianza en el análisis.

**7. ¿Replicable con nuestros datos?** Sí, completo: marcador por set → juegos y sets ganados;
cuotas B365/Pinnacle de Tennis-Data. Hay que fijar una regla para retiradas (el paquete las
elimina).

**8. Mercado.** Ganador. El margen de juegos que usa el WElo es la variable natural para
hándicap y totales, pero no se evalúa.

**9. Temas transversales.** Ratings: Elo y WElo con K decreciente con la experiencia (los
jugadores con poca historia se mueven más). Superficie: solo como multiplicador de K, no hay
Elo por superficie. Mercado: probabilidad implícita de B365 sin quitar margen; cobro a mejor
cuota. Retiradas: eliminadas. Poca historia: se excluye a quien jugó <10 partidos (con
información futura). Fatiga, IID, micro-eventos: no constan.

### A05 — Yue, Chou, Hsieh y Hsiao (2022), «A study of forecasting tennis matches via the Glicko model»

**1. Referencia.** A05. Jack C. Yue, Elizabeth P. Chou, Ming-Hui Hsieh, Li-Chen Hsiao (National
Chengchi University). 2022. Artículo de revista: *PLOS ONE* 17(4): e0266838.

**2. Modelo.** Glicko (Glickman 1999) con el paquete R `PlayerRatings`: fuerza
`θ | r, RD² ~ N(r, RD²)`, resultados por Bradley-Terry; antes de cada periodo
`RD = min(√(RD_old² + c²·t), RD_0)`, con t = periodos desde el último partido (pág. 4).
Parámetros: r=1500, RD=350, c=10 «tras varios experimentos». El rating y su desviación entran
como variables en una regresión logística («Glicko»); versión con variables Glicko por
superficie («Glicko (Courts)»). Comparadores: *baseline* (gana el mejor clasificado),
logística, SVM, red neuronal y LightGBM con «todas las variables disponibles» (pág. 8).
Análisis exploratorio: el percentil 80 del ranking que alcanza cada ronda sigue una ley de
potencia, `log(x_s)` lineal en la ronda s (R²>0,9; Tabla 1, pág. 6).

**3. Datos.** Cuadros individuales masculino y femenino de los cuatro Grand Slam 2000-2019,
datos de Jeff Sackmann (GitHub, 49 variables) (págs. 2-3). Variables: residencia, edad, año
de inicio, mano, altura, ranking y puntos, superficie. Número final de partidos: no consta
(máximo teórico 127 por cuadro).

**4. Validación.** «Moving window»: 4 años de entrenamiento y 2 de prueba, 15 ventanas,
promedio (pág. 8). «Non-moving window»: 4 años al azar para entrenar y 2 de los 16 restantes
para probar (permite entrenar con el futuro). Métricas: precisión y AUC; sin log-loss ni
Brier (no evalúa calibración). Las variables finales se eligen «tras múltiples experimentos
con validación cruzada» quedándose con el subconjunto de mayor precisión (pág. 7): selección
con los datos de evaluación (optimista, detectado). No consta sobre qué partidos ni con qué
periodo de rating se calcula el Glicko, ni si es estrictamente previo al partido.
Hiperparámetros en la Tabla S1, que no viene en el PDF. Sin comparación con cuotas.

**5. Resultados** (Tablas 2-4, págs. 9-10, verificadas con `-raw`; AUC / precisión):

| Modelo | ATP móvil | WTA móvil | ATP no móvil | WTA no móvil |
|---|---|---|---|---|
| Baseline (ranking) | — / 0,724 | — / 0,701 | — / 0,717 | — / 0,704 |
| Logística | 0,691 / 0,727 | 0,656 / 0,699 | 0,685 / 0,718 | 0,661 / 0,704 |
| SVM | — / 0,719 | — / 0,700 | — / 0,721 | — / 0,709 |
| Red neuronal | 0,657 / 0,724 | 0,648 / 0,701 | 0,700 / 0,720 | 0,690 / 0,707 |
| LightGBM | 0,688 / 0,723 | 0,667 / 0,700 | 0,705 / 0,717 | 0,694 / 0,707 |
| Glicko | 0,715 / 0,734 | 0,695 / 0,712 | 0,704 / 0,723 | 0,696 / 0,713 |
| Glicko (Courts) | 0,731 / 0,738 | 0,691 / 0,709 | 0,728 / 0,732 | 0,697 / 0,714 |

Exploratorio: la probabilidad de que gane el mejor clasificado sube con la diferencia de
ranking y se aplana en ≈0,8 hacia una diferencia de 80 puestos (Fig. 2, pág. 5). Percentil 80
del ranking por ronda: campeón 5, final 9, semifinal 15, cuartos 25, 4.ª ronda 41, 3.ª 64,
2.ª 98 (Tabla 1). Conclusión de los autores: el ranking contiene casi toda la información en
Grand Slam; Glicko mejora ≈1 pp (pág. 11).

**6. Límites.** Declarados: resultados dependientes de los datos; solo Grand Slam, donde los
jugadores son homogéneos. Detectados: sin intervalos ni pruebas; con ≈1.000 partidos por
ventana de prueba el error estándar de la precisión es ≈1,4 pp, así que diferencias de ≈1 pp
no se distinguen del ruido; AUC del baseline no publicada; selección de variables con el
conjunto de evaluación; la variante «no móvil» mezcla futuro y pasado.

**7. ¿Replicable con nuestros datos?** Sí: Glicko a partir de resultados, ranking, puntos,
edad, altura, mano, superficie. Hay que definir el periodo de rating y usar solo partidos
previos.

**8. Mercado.** Ganador.

**9. Temas transversales.** Ratings: Glicko añade una desviación RD que crece con la
inactividad, útil para jugadores con poca historia o que vuelven de un parón. Superficie:
variables Glicko por superficie mejoran en ATP (ventana móvil) pero no en WTA. Ranking casi
suficiente dentro de Grand Slam. Fatiga, mercado, retiradas, IID: no constan.

### A07 — Sipko (2015), «Machine Learning for the Prediction of Professional Tennis Matches»

**1. Referencia.** A07. Michal Sipko (director: William Knottenbelt). 15-jun-2015. Proyecto
final de MEng, Imperial College London, 64 págs. Leído íntegro.

**2. Modelo.**
- Variables como **diferencias** entre jugadores (modelo simétrico, sin intercepto, pág. 13 y
  28). Promedios históricos con tres técnicas (cap. 3): rivales comunes; descuento temporal
  `W(t) = min(f^t, f)` con t en años y f=0,8 (ec. 3.2); ponderación por superficie con la
  correlación entre superficies del % de victorias de carrera (ec. 3.3), medida en
  2004-2010: dura–tierra 0,28; dura–indoor 0,35; dura–hierba 0,24; tierra–indoor 0,31;
  tierra–hierba 0,14; indoor–hierba 0,25 (Fig. 3.4).
- Incertidumbre de las variables: `U = 1/(S_1·S_2)` con `S_i` = suma de pesos de los partidos
  previos (ec. 3.4); con rivales comunes `U = 1/Σ_j S_1(C_j)·S_2(C_j)` (ec. 3.5).
- Variables construidas (sección 3.4): `WSP = W1SP·FS + W2SP·(1−FS)`;
  `COMPLETE = WSP·WRP`; `SERVEADV = (WSP_1 − WRP_2) − (WSP_2 − WRP_1)`; `FATIGUE` = juegos
  jugados en los 3 días previos con descuento 0,75 por día (p.ej. 50 juegos hace 2 días →
  50·0,75² = 28); `RETIRED` = 1 si es el primer partido tras una retirada;
  `DIRECT = H2H(1,2) − H2H(2,1)` (ec. 3.6). 22 variables (Tabla 3.2); RANK y POINTS se
  excluyen a propósito porque producen probabilidades demasiado concentradas (pág. 28,
  Fig. 4.1).
- Modelos: (i) logística L2 (C=0,2), selección hacia delante con log-loss → 12 variables:
  SERVEADV, DIRECT, FATIGUE, ACES, TPW, DF, BP, RETIRED, COMPLETE, NA, W1SP, A1S (pág. 32);
  (ii) logística con interacciones por pares (173 variables, eliminación hacia atrás, C=0,1);
  (iii) red MLP de 1 capa oculta de 100 neuronas tanh, salida logística, sin sesgo, tasa
  0,0004, *weight decay* 0,002, momento 0,55, parada temprana a 10 épocas, *bagging* de 20
  redes (Apéndice B).
- Referencia: modelo Common-Opponent de Knottenbelt sobre las fórmulas jerárquicas de
  Barnett y Clarke: `P_game(x,y) = p·P_game(x+1,y) + (1−p)·P_game(x,y+1)` (ec. 2.2) con
  frontera en deuce `p²/(p²+(1−p)²)`; `f_i = a_i·b_i + (1−a_i)·c_i`,
  `g_i = a_av·d_i + (1−a_av)·e_i` (ec. 2.3); `f_AB = f_t + (f_i − f_av) − (g_j − g_av)` (ec. 2.4).
- Estrategias de apuesta (sección 2.3.2): E1 apostar q al favorito del modelo; E2 apostar q
  si `p_modelo > p_implícita`; E3 Kelly `s = q·(p(b+1) − 1)/b` si `p > p_implícita`, con q
  fijo.

**3. Datos.** OnCourt (comercial): >500.000 partidos ATP desde 1990, >40.000 con cuotas
(Marathonbet, Pinnacle) y estadísticas por partido (primeros saques, aces, dobles faltas,
errores no forzados, puntos ganados con 1.º/2.º saque y al resto, winners, break points,
subidas a la red, velocidad de saque) (Tabla 2.1). ATP 2004-2014: entrenamiento 2004-2010
(≈39.000), validación 2011-2012 (≈6.200), prueba 2013-2014 (≈12.600) (pág. 26). Se elimina
el 80 % de los partidos de entrenamiento más inciertos (pág. 33). Prueba final: **6.315
partidos ATP con cuota Pinnacle**, tras quitar el 50 % más incierto (pág. 46).

**4. Validación.** Partición temporal por años completos; sin validación cruzada;
hiperparámetros ajustados en validación, modelos reentrenados con 2004-2012 y evaluados una
vez en 2013-2014 (págs. 26-27 y 46). Métricas: log-loss y ROI de las tres estrategias con
cuotas Pinnacle. Todo se evalúa solo sobre el 50 % de partidos menos inciertos (criterio
previo al partido, legítimo, pero es una subpoblación). Fuga: no detectada (todas las
variables vienen de partidos anteriores). Decisiones guiadas por ROI: el 80 % de descarte de
entrenamiento se fijó en el pico de ROI; la búsqueda de hiperparámetros es voraz y «guiada
por decisiones humanas» (pág. 32). No consta si las cuotas Pinnacle son de cierre. No se
publica la log-loss del mercado.

**5. Resultados** (cap. 7, págs. 46-50, cifras verificadas con `-raw`).
- ROI % (E1 / E2 / E3): logística 1,46 / 3,62 / 4,17; logística con interacciones 0,73 / 1,69
  / 4,08; red 0,70 / 2,07 / **4,35**; Common-Opponent 0,20 / 1,89 / 2,40 (Fig. 7.1).
- Log-loss validación → prueba: logística 0,5761 → 0,6129; interacciones 0,5727 → 0,6122;
  red 0,5766 → 0,6111; Common-Opponent 0,5895 → 0,6228 (Fig. 7.2).
- Volumen E3 (Tabla 7.1; apuestas / invertido / retorno / neto): logística 3.181 / 709,53 /
  739,12 / 29,59; interacciones 3.140 / 670,69 / 698,08 / 27,39; red 3.183 / 695,60 /
  725,85 / 30,26; Common-Opponent 2.515 / 489,10 / 500,84 / 11,75.
- Desviación típica de las probabilidades predichas: 0,2005 / 0,2002 / 0,2029 / 0,1573
  (Common-Opponent, demasiado concentrado); la de las probabilidades implícitas es 0,2354
  (Fig. 5.8): todos los modelos quedan más concentrados que el mercado.
- Validación (Tabla 4.1): selección hacia delante con log-loss 0,5743 y ROI 9,7 % frente a
  todas las variables 0,5762 y 7,8 %; seleccionar por ROI dio 11,3 % en validación pero
  generaliza mal: el autor desaconseja optimizar por ROI (págs. 30-31 y 52).
- Fatiga: el jugador más fatigado perdió el 55,1 % (2004-2010); primer partido tras retirada:
  perdió el 51,5 % (Fig. 3.5). Sin distinguir superficie, la logística pierde >6 % de ROI; lo
  mejor es rivales comunes + ponderación por correlación de superficie (Fig. 7.5).
- Simulación de banca (100 £, apuesta máxima 10 % de la banca): red 1.051,55 £;
  Common-Opponent 58,41 £ (pierde en 2014) (pág. 49).

**6. Límites.** Declarados (sección 7.4): cajas negras; sin predicción en juego; coste de
recolectar datos; solo ATP; parámetros del Common-Opponent tomados de la publicación.
Detectados: sin intervalos de confianza del ROI; la log-loss de prueba (≈0,611) es muy peor
que la del consenso de casas que A01 mide en ATP 2014 (0,55, otra muestra), lo que hace
frágil el ROI positivo; salto validación→prueba grande (0,576 → 0,611), que el autor atribuye
a años «más difíciles»; la red solo mejora 0,0018 de log-loss a la logística; incoherencias
internas (6.315 vs «6135» partidos de prueba en la introducción; validación «2010-2011» en la
sección 5.3.2 vs 2011-2012 en la 4.1).

**7. ¿Replicable con nuestros datos?** En su núcleo, no: SERVEADV, ACES, DF, TPW, BP, NA,
W1SP, A1S y COMPLETE requieren estadísticas de saque/resto por partido que no tenemos de forma
sistemática (solo el MCP, subconjunto). Sí se puede: el marco de rivales comunes aplicado a %
de victorias o % de juegos ganados, el descuento temporal, la ponderación por correlación de
superficie, FATIGUE (juegos de los 3 días previos a partir del marcador por set), RETIRED y
DIRECT (H2H).

**8. Mercado.** Ganador pre-partido. Menciona como extensión el número de juegos.

**9. Temas transversales.** IID: Klaassen y Magnus muestran que los puntos no son IID pero las
desviaciones son pequeñas (pág. 1, nota). Superficie: correlaciones bajas entre superficies
(tierra–hierba 0,14); separar por superficie deja sin datos; ponderar por correlación es lo
mejor. Ajuste por rival: rivales comunes. Fatiga: juegos de 3 días con descuento 0,75. Lesión:
RETIRED como aproximación. Mercado: Pinnacle; E3 (Kelly) la más rentable; la regularización
fuerte sube el ROI y empeora la log-loss (probabilidades más moderadas apuestan solo en los
desajustes grandes, pág. 41). Poca historia: medida de incertidumbre, se descartan porcentajes
extremos (0 o 1) y no se apuesta en partidos muy inciertos. Edad: curva de envejecimiento
citada (Fig. 3.2), sin variable de edad. Ratings tipo Elo: no constan.

### A10 — Nogara (2023), «Construção de modelos para previsão de resultados em partidas de tênis utilizando machine learning»

**1. Referencia.** A10. Walter Zolcsak Neto Nogara (director: Klaus Schlünzen Junior). 2023.
Trabajo de fin de grado (Bacharelado em Estatística, FCT/Unesp, Presidente Prudente), 44 págs.
En portugués. Leído íntegro.

**2. Modelo.** Árbol de decisión (`rpart`, R) con 32 variables y regresión logística (`glm`):
`logit(p) = β0 + β1·x1 + … + βp·xp`, estimada por máxima verosimilitud (sección 2.3.2). La
clase es «vitória» si gana el mejor clasificado y «derrota» si hay sorpresa (sección 4.1).

**3. Datos.** Kaggle «ATP Matches dataset» (2000-2017, 53.119 partidos, sección 3.1). Se
dice que se excluyen 2000-2010 y 2017 (sección 3.3), pero luego se usa 2010-2016: 20.872
partidos y 48 variables (sección 4.1; contradicción interna sobre 2010). Variables: medias de
saque, dobles faltas, puntos con 1.º y 2.º saque y break points de partidos anteriores,
organizadas en un grupo «vencedor» y otro «perdedor» (sección 3.5). Clase: 66,78 % victorias
del mejor clasificado (13.939) y 33,22 % sorpresas (6.933) (Tabla 4.1).

**4. Validación.** Partición temporal: entrenamiento 2010-2014 (14.973), prueba 2015-2016
(5.899) (pág. 34). Métricas: exactitud, precisión, revocación y F1 (macro y ponderados). Sin
métricas de probabilidad, sin referencia trivial, sin cuotas. No consta cómo se pasa de las
variables «vencedor/perdedor» a las del mejor clasificado, ni si las medias excluyen el partido
que se predice; la base trae la duración del partido y no consta si se usó.

**5. Resultados.** Matrices de confusión en prueba (Tablas 4.2 y 4.5): árbol VN 1.069, FP
877, FN 1.848, VP 2.105 → exactitud 53,8 % en el texto (53,6 % en la Tabla 4.4); logística
1.099 / 847 / 1.874 / 2.079 → 53,9 %. F1 «derrota» 43,9 % (árbol) y 44,6 % (logística);
«vitória» 60,7 % y 60,4 % (Tabla 4.8). Con esas mismas matrices, la regla trivial «gana el
mejor clasificado» acierta 3.953/5.899 = **67,0 %** (cálculo nuestro): ambos modelos quedan
≈13 pp por **debajo** de la referencia trivial, y el autor no lo advierte.

**6. Límites.** Declarados (cap. 5): factores no medibles (estado psicológico, lesiones, falta
de ritmo, material); propone añadir superficie, premios y rivales comunes. Detectados: las
definiciones de precisión y revocación están invertidas (pág. 26: «precisão = VP/(VP+FN)»,
«recall = VP/(VP+FP)») y la Tabla 4.3 aplica esa inversión; la conclusión confunde F1 con
exactitud (atribuye al árbol una «taxa de acerto» de 60,7 %) y cambia las cifras de un modelo a
otro; clasificador peor que no hacer nada; sin calibración.

**7. ¿Replicable con nuestros datos?** Técnicamente sí, pero no hay nada aprovechable; además
sus variables de saque no las tenemos de forma sistemática.

**8. Mercado.** Ganador (formulado como «gana o no el favorito por ranking»).

**9. Temas transversales.** Solo justifica descartar años antiguos por la rotación de
jugadores. Superficie, fatiga, mercado, IID, retiradas y poca historia: no constan (la
superficie solo como propuesta).

### A12 — Zukal (2022), «Predikce výsledků tenisových utkání»

**1. Referencia.** A12. Martin Zukal (director: Ondřej Hubáček; en colaboración con la empresa
Ematiq a.s.). Tesis de máster (Diplomová práce), Facultad de Informática, ČVUT Praga, fechada el
3 de mayo de 2022. 75 págs., en checo. Leída íntegra; el capítulo 2 (revisión) resume sobre
todo a A01 y repite su Tabla 4.

**2. Modelo.**
- Referencia: Elo FiveThirtyEight, `E_a = 1/(1 + 10^((R_b−R_a)/400))`, `R'_a = R_a + K(S − E_a)`,
  `K = 250/(m(t)+5)^0.4`, ×1,1 en Grand Slam, arranque 1500 (sección 2.3.2).
- Red neuronal clasificadora: 1-5 capas lineales de 4-128 neuronas, activación ReLU, tanh,
  sigmoide o ninguna, salida sigmoide, pérdida log-loss, Adam o SGD; hiperparámetros con
  Optuna (cap. 4-5). La mejor por log-loss: conjunto «ewm all», rasgos realized + allowed +
  realized adjusted + allowed adjusted, Adam, **1 capa de 7 neuronas sin activación**
  (Tabla 5.3), es decir, casi una regresión logística.
- Modelo por punto: red con 2 salidas que predice la probabilidad de ganar el punto al saque de
  cada jugador (pérdida: error absoluto medio; la mejor, 1 capa de 78 neuronas ReLU, MAE de
  validación 0,0644), que se pasa a un modelo jerárquico ya existente con el número de sets
  (secciones 5.1.2 y 6.3).
- Rasgos (cap. 3): 13 «realized» (estadísticas propias del partido en %: aces, break points,
  puntos al resto, puntos con 1.º/2.º saque, `p = (w1s+w2s)/(w1sof+w2sof)`…), 13 «allowed»
  (las mismas del rival en ese partido), y 13+13 «adjusted» (realized del jugador menos la media
  expansiva de lo que el rival suele conceder, y viceversa). Agregación previa al partido: media
  móvil con k ∈ {3, 5, 10, 25} (por superficie k ∈ {3, 5}), media expansiva (carrera) y media
  exponencial `y_t = Σ(1−α)^i·x_{t−i} / Σ(1−α)^i` con α = 0,95 o `α = 1 − exp(−ln2/halflife)`,
  semivida 10 partidos (por superficie) y 30 (global).
- Apuestas (sección 6.4): `value = predicción − 1/cuota` (sin quitar margen); estrategia «0-3»:
  apostar un % de la banca igual al value cuando está entre 0 y 3 %; estrategia «fix 3»: 3 % fijo
  de la banca en cada oportunidad con value. Banca inicial 100.000.

**3. Datos.** Ematiq a.s.: partidos de 1993 a febrero de 2022; estadísticas por partido desde 2003;
hombres y mujeres; niveles de torneo de 0 (ITF < 10.000 $) a 6 (sección 3.1); no consta si se
filtraron niveles ni si se separaron circuitos. Cuotas previas de «una de las mayores casas» y
dos casas extranjeras sin nombre para la rentabilidad. ≈250.000 filas (cada partido aparece dos
veces, una por jugador, de ahí el 50 % exacto de victorias); entrenamiento hasta fin de 2015
(127.000), validación 2016-2017 (42.000), prueba 2018-feb 2022 (≈70.000) (sección 4.5).

**4. Validación.** Temporal entrenamiento / validación / prueba. Métricas: log-loss y precisión.
1.000 experimentos de Optuna sobre la validación; la prueba se usa al final. Fuga: los rasgos se
describen como las estadísticas con las que el jugador «entra» al partido, pero no se detalla el
desfase de las ventanas; no consta que las dos filas de un partido den probabilidades que sumen 1.

**5. Resultados** (prueba 2018-2022, cap. 6): Elo log-loss 0,6474 y precisión 62,26 %; red
clasificadora 0,6408 y 63,24 %; modelo por punto 0,6537 y 63,90 % (más preciso, peor
log-loss). Validación: mejor log-loss 0,6243; mejor precisión 65,21 %. Rentabilidad: ningún
modelo bate a las casas a largo plazo con ninguna estrategia (Figs. 6.1-6.4; solo gráficos, sin
cifras de ROI). Descriptivos: el 4,4 % de los partidos los gana quien gana menos puntos
(Fig. 3.2); correlación con la victoria de estadísticas del propio partido: break points 0,605,
puntos al resto 0,467, puntos totales 0,438, 1.er saque 0,272, 2.º saque 0,271, aces 0,222,
errores no forzados −0,133, dobles faltas −0,181 (Tabla 3.8).

**6. Límites.** Declarados (cap. 7): faltan hiperparámetros y regularización; propone embeddings
de jugador + superficie. Detectados: sin intervalos; ROI solo en gráficos y con casas anónimas;
mezcla de niveles y circuitos no aclarada (probable causa de que el Elo solo acierte 62 %, frente
al 70 % de A01 en ATP de primer nivel); probabilidad implícita con margen; la mejora de log-loss
sobre el Elo (0,0066) es pequeña.

**7. ¿Replicable con nuestros datos?** Elo: sí. Red clasificadora y modelo por punto: no (necesitan
estadísticas de saque y resto por partido); solo con el MCP. El esquema realized / allowed /
adjusted sí se puede aplicar a lo que tenemos (juegos, sets, tiebreaks ganados y concedidos).

**8. Mercado.** Ganador. El modelo por punto daría distribución de sets y juegos, pero no se evalúa.

**9. Temas transversales.** Superficie: medias por superficie. Ajuste por rival: rasgos
«adjusted» frente a lo que el rival concede. IID: implícito en el modelo jerárquico, no se
discute. Mercado: no se le gana. Fatiga, retiradas, poca historia: no constan.

### A14 — Colin y Bechler (2015), «Informative prior distributions for a binomial model to predict professional tennis results»

**1. Referencia.** A14. Pierre Colin y Aurélien Bechler. 2015. Artículo de revista: *Journal de la
Société Française de Statistique* 156(2):25-38.

**2. Modelo** (secciones 2-3).
- Beta-Binomial: `R_ij ~ Bernoulli(π_ij)`, `π_ij ~ Beta(α_ij, β_ij)`, `α_ij = p_ij·(1+ess)`,
  `β_ij = (1−p_ij)·(1+ess)`; posterior `Beta(α_ij + v_ij, β_ij + v_ji)`; predicción
  `E(π_ij | v) = [p_ij·(1+ess) + v_ij] / [(1+ess) + v_ij + v_ji]` (ec. 2); varianza a priori
  `p(1−p)/(2+ess)`. `v_ij` = victorias previas de i sobre j (H2H de 2 años). `ess` = tamaño
  muestral equivalente del prior, en «partidos H2H».
- Prior Elo: `Δ = S_i − S_j`, `p = (1 + 10^(−Δ/400))^(−1)`, `S_{t+1} = S_t + K(W − p)`, K = 27;
  se usa el último valor (paquete `PlayerRatings`).
- Prior Bradley-Terry: `δ = λ_i − λ_j`, `p = (1 + e^(−δ))^(−1)`, λ por máxima verosimilitud
  `∏_i ∏_{j>i} p_ij^{v_ij}(1−p_ij)^{v_ji}` (ec. 5-6), habilidades fijas en el periodo.
- Prior Markov por simulación de puntos con las MatchFacts de la ATP, por superficie: primer saque
  dentro ~ Bernoulli(p_s1); el sacador gana el punto con prob. `p_sw1/(p_sw1 + p_rw1)` tras primer
  saque o `p_sw2/(p_sw2 + p_rw2)` tras segundo; en break point `p_bs/(p_bs + p_bc)`; sacador
  inicial al azar; 100.000 simulaciones por partido (sección 3.3). El artículo usa el mismo índice
  k para las dos tasas; se entiende sacador (sw) y restador (rw).

**3. Datos.** ATP. Entrenamiento 2011-2012: 5.947 partidos → 5.326 retenidos, 377 jugadores, máx. 10
H2H; «first seen» 2013: 2.866 → 2.529, 232 jugadores, máx. 6 H2H (Tabla 2). Se quitan
descalificaciones, «by-pass» y retiradas. MatchFacts del sitio de la ATP; periodo no consta.

**4. Validación.** Se entrena con 2011-2012 y se predice todo 2013 sin actualizar (la Fig. 4 muestra
cómo se degrada con los días desde el corte). La `ess` (0 a 50) se elige maximizando el AUROC,
aparentemente sobre el mismo 2013 (no se describe un conjunto de validación aparte): optimista.
Métricas: AUROC (Brier «similar», no mostrado) y % de aciertos suavizado en el tiempo. Sin cuotas.
Posible fuga: no consta de qué periodo son las MatchFacts.

**5. Resultados.** `ess` óptima: Elo 5, BT 6, Markov 10 (Fig. 3; AUROC en un eje de 0,73 a 0,79, el
Markov el más alto; **no hay tabla de cifras**). % de aciertos durante 2013 (Fig. 4, eje 0,60-0,75):
el Markov siempre por encima. Ranking «Ultimate Player»: correlación con el ranking ATP 0,55 (todas),
0,58 (dura), 0,47 (tierra), 0,50 (hierba). Simulación del Open de Australia 2014: 6 de 8
cuartofinalistas acertados.

**6. Límites.** Declarados (sección 5): la independencia de los puntos es una hipótesis fuerte,
contradicha por la persistencia (rachas en momentos clave por estrés o ventaja física temporal); no
distingue pista cubierta/exterior; el tiebreak podría modelarse aparte; propone evaluar nº de sets,
juegos del primer set y aparición de tiebreak. Detectados: sin cifras tabuladas; `ess` elegida sobre
la evaluación; Elo y BT sin superficie y congelados a fin de 2012; la combinación
`p_sw/(p_sw + p_rw)` es ad hoc y no se justifica.

**7. ¿Replicable con nuestros datos?** Elo/BT + actualización Beta con el H2H: sí. Markov con
MatchFacts: no (necesita % de saque y resto por jugador y superficie), salvo con el MCP.

**8. Mercado.** Ganador y simulación de cuadro (ganador del torneo); sugiere sets, juegos y tiebreak.

**9. Temas transversales.** IID: crítica explícita. Superficie: solo en el Markov, al que atribuyen su
ventaja. H2H: tratado como evidencia bayesiana con peso `ess` frente al prior. Poca historia: sin H2H
manda el prior. Mercado: menciona el sesgo favorito/no favorito y por nacionalidad como uso posible,
sin estudiarlo.

### A17 — Ünal (2023), «Predicting tennis match outcome: a machine learning approach using the SRP-CRISP-DM framework»

**1. Referencia.** A17. Toyan Ünal (directora: Sevgi Özkan Yıldırım). Tesis de MSc, Middle East
Technical University, 7-dic-2023. 101 págs. (85 de cuerpo). Leída íntegra; los apéndices A y B
(tablas de rejilla) se revisaron sin leer fila a fila.

**2. Modelo.**
- Marco SRP-CRISP-DM; regresión logística, SVM y XGBoost; selección de variables por información
  mutua (umbral 0,010) y por selección hacia delante con Brier (sección 3.4).
- Técnicas de rasgos (sección 3.3.3): diferencias simétricas; medias históricas; rivales comunes;
  descuento `W(t) = min(f^t, f)` con t en días agrupados por periodo (p.ej. «0,8 cada 30 días»);
  ventana temporal; umbral de incertidumbre `U = 1/(S_1·S_2)`.
- Variables (sección 3.3.3.3): `diff_Avg_implied` (probabilidad implícita media de 6 casas, margen
  quitado por Shin), puntos y ranking ATP (y sus logaritmos), cabeza de serie, edad, distancia a la
  edad de máximo personal (`diff_agePersonalPeak`) y a la mediana general (26,75 años), localía, mano,
  Grand Slam (el favorito gana 73,35 % en Grand Slam frente a 64,17 %), ventaja de superficie, ex
  top-10, «momentum» de ranking, fatiga por juegos, duración media, % de victorias global, por
  superficie y H2H, rachas, y ratios de saque/resto, completeness, aces, dobles faltas y break points.
- Modelo final XGB-FS con 8 variables (Tabla 6, verificada con `-table`): `diff_Avg_implied`,
  `diff_rankpt_log`, `diff_overallServeWinRatio`, `diff_surfaceWinRatio`, `diff_rank`, `diff_age`,
  `diff_winLossStreak`, `diff_agePersonalPeak`; learning_rate 0,05, max_depth 3, min_child_weight 4,
  subsample 0,5, colsample_bytree 1, alpha 0, lambda 0, 50 árboles (Tabla 10).
- Referencias: BOI `p_1 = (1 + diff_Avg_implied)/2` (el mercado); RPI = 1 / 0,5 / 0 según el signo de
  la diferencia de puntos; «ERS» aparece en la Tabla 8 sin definirse en el texto.

**3. Datos.** Tennis-Data (cuotas de cierre de Bet365, Expekt, Ladbrokes, Pinnacle, Stan James y
Unibet) unido a `atp_matches` de Sackmann; solo ATP masculino de circuito principal (Grand Slam,
Finals, Masters, 500, 250); 2009-2022: 34.121 partidos tras quitar retiradas, descalificaciones y
walkovers; 946 jugadores; jugador 1 asignado al azar (17.107 / 17.014) (sección 3.2).

**4. Validación.** Prueba fuera de muestra 2021-2022; validación cruzada temporal expansiva de 10
pliegues (2009-2010→2011 … 2009-2019→2020), con 2020 (1.237 partidos) pesando el doble en el
promedio (sección 4.4.1). Rejilla de 174.960 modelos XGB. Métricas: Brier y precisión. Fugas
detectadas: (i) `diff_agePersonalPeak` usa la edad a la que cada jugador alcanzó su máximo de puntos
**en toda la base** (Tabla 4: sin promedio histórico), es decir información futura, y está en el
modelo final; (ii) los 51 partidos sin cuota se imputan por KNN usando `p1_points_ratio`, que son
los puntos ganados en ese mismo partido (sección 3.3.2). La referencia de mercado (BOI) **no se
publica en la prueba**, solo en validación.

**5. Resultados.**
- Validación (Tabla 8): BOI 0,1957 / 0,6940; RPI 0,3396 / 0,6604; ERS 0,2203 / 0,6732; LR-MI
  0,1905 / 0,7080; SVM-MI 0,1916 / 0,7075; XGB-MI 0,1905 / 0,7028; LR-FS 0,1906 / 0,7076; SVM-FS
  0,1904 / 0,7078; XGB-FS 0,1902 / 0,7077 (Brier / precisión).
- Prueba 2021-2022 (Tabla 9): LR-MI 0,1913 / 0,7055; SVM-FS 0,1920 / 0,7039; XGB-FS 0,1913 / 0,7050.
- Importancia en XGB-FS: `diff_Avg_implied` 0,743; el resto entre 0,026 y 0,042 (la edad, la
  siguiente) (sección 4.4.3). Información mutua: implícita 0,135; log puntos 0,093; puntos 0,091;
  cabeza de serie 0,074; ranking 0,072; % victorias global 0,047; por superficie 0,046; % puntos al
  saque 0,046 (Tabla 5). χ²: H2H 138,3; % victorias global 103,4; por superficie 92,3; % puntos al
  saque 44,6; fatiga 1,76 (p=0,18) (Tabla 4).

**6. Límites.** Declarados (sección 5.4): recursos de cálculo; solo dos fuentes públicas; el autor
admite que «no se superaron los benchmarks existentes» (sección 5.3), lo que contradice su respuesta
a la pregunta 3 (que el aprendizaje automático supera a las cuotas). Detectados: la fuga de
`diff_agePersonalPeak`; sin BOI en prueba; sin intervalos ni pruebas de diferencia; no consta
calibración de la SVM; la mejora sobre el mercado en validación (0,0055 de Brier) no se verifica en
prueba y podría deberse a la fuga.

**7. ¿Replicable con nuestros datos?** Casi todo sí (Tennis-Data + resultados + ranking), salvo los
ratios de saque/resto. Lo útil: BOI con Shin; diferencia logarítmica de puntos ATP; % de victorias
por superficie con rivales comunes y descuento; rachas; fatiga por juegos; H2H con umbral de
incertidumbre.

**8. Mercado.** Ganador.

**9. Temas transversales.** Mercado: el consenso de casas domina (importancia 0,743); el modelo
apenas lo retoca. Superficie: % de victorias por superficie. Fatiga: juegos de los 5 días previos
con descuento 0,99 por día, asociación débil. Retiradas y walkovers: excluidos. Poca historia:
umbral de incertidumbre; ranking faltante imputado a 2200 con 0 puntos. IID: no se trata.

