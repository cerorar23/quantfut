# Otros modelos y factores de la literatura para el Motor A (26-oct-2026)

Pedido del titular: investigar otros modelos y datos o factores no contemplados, de estudios doctorales o experimentales, para
mejorar el pronóstico. Se revisó la literatura (solo resúmenes y páginas de las revistas; no se leyeron los textos completos) y lo
que es medible con nuestros datos se midió **en local** sobre el walk-forward de 3 años del modelo `2026.10.26-020600`
(12.878 partidos; 10.572 con cierre de Pinnacle). Protocolo: origen rodante, el año 2 se prueba con lo ajustado en el año 1 y el
año 3 con lo ajustado en los años 1 y 2; todo lo calculado usa solo partidos anteriores. **Nada cambia producción.**

## Conclusión corta

1. **En el 1X2 no queda un factor de estos que añada información sobre el cierre de Pinnacle.** Probados contra el mercado, todos
   quedan en cero o peor; el propio Dixon-Coles tampoco añade nada sobre el mercado (+0,0004 de RPS).
2. Contra nuestro Dixon-Coles solo los **tiros** (forma de tiros y tiros a puerta) dan una mejora pequeña y consistente
   (−0,0005 en los dos años), con intervalo al borde de cero. Pi-ratings, forma de xG, viaje, descanso, forma y motivación no.
3. Los árboles de gradiente (lo que ganó los retos de predicción de fútbol) **empeoran** (+0,0009 a +0,0029): con 4.000-8.600 filas
   de entrenamiento sobreajustan, y nuestro modelo base ya incluye xG, que es lo que esos retos no tenían.
4. El hueco de 0,0096 contra el mercado es **información** (alineaciones, bajas y noticias que el mercado ya descontó), no
   forma del modelo. Lo que ya está medido y suma: altitud + once (−0,0007 a −0,0010) y la mezcla dinámica (−0,0008).
   Juntos ~−0,0017, un 18 % del hueco.
5. Donde la literatura sí documenta ventaja es en **mercados distintos al 1X2** (totales, córners, tarjetas, con estadísticas de
   partido). Hoy no se puede probar: solo hay 459 partidos con cierre de totales de Pinnacle.

## Qué dice la literatura y qué medimos

| Idea (fuente) | Qué sostiene | Qué medimos | Resultado |
|---|---|---|---|
| Pi-ratings (Constantinou y Fenton, 2013) | Rating por goles con localía/visita, base de los mejores modelos de los retos 2017 y 2023 | Pi-ratings propios como característica sobre el DC y sobre el mercado | Nada: +0,00006 (años 2-3) sobre el DC; +0,00008 sobre el mercado |
| Árboles de gradiente y ratings (Berrar et al., 2019; Hubáček et al., 2019; CatBoost con pi-ratings, 2024) | Mejor familia de modelos sin cuotas | HistGradientBoosting sobre los logits del DC + factores | Peor: +0,0009 a +0,0029 |
| Estadísticas de partido: tiros, córners (Wheatcroft, 2020, 2021) | Tiros y tiros a puerta predicen mejor que goles; añaden sobre las cuotas | Forma de tiros (5 partidos), forma de xG (5 y 10) | Tiros −0,00047 (p95 +0,00005) sobre el DC; sobre el mercado −0,00035 en el año 3 pero +0,0004 en el año 2. xG: sin efecto |
| Viaje y desfase horario (Gilbert et al., 2020; Tyranny of distance) | Más ventaja local con viajes largos y al este | Distancia entre el estadio habitual del visitante y la sede, horas de huso | Nada: +0,0002 |
| Motivación / nada en juego (Scarf y Shi; Buraimo y Forrest) | Los partidos sin nada en juego cambian el ritmo; difícil de medir | Carreras vivas (título, Champions, descenso) desde el 60 % de la temporada, 8 ligas | Nada: +0,0002; con un equipo «muerto» los resultados salen casi iguales a lo previsto |
| Cuotas como dato (Egidi et al., 2018; Wunderlich y Memmert, 2018) | Las cuotas mejoran los modelos | Apilado anclado al cierre | El mercado no mejora con nada; el modelo pesa 0,0001 en la mezcla modelo/mercado |
| Modelo dinámico (Koopman y Lit, 2015, 2019) | Fuerzas que cambian en el tiempo | Ya medido el mismo día | −0,0008 con la mezcla; ver `modelo_dinamico_y_ascendidos_20261026.md` |
| Cambio de entrenador (estudios sobre «rebote») | El rebote es regresión a la media, no efecto del entrenador | No se mide | Descartado por la literatura |
| Conteo Weibull/COM-Poisson (Boshnakov et al., 2017) | Mejor ajuste que Poisson | No se mide | El bivariado ya salió peor que el DC; ganancia reportada en apuestas, no en RPS |
| Plus-minus por jugador (Arntzen y Hvattum, 2021) | Valor del once sobre Elo | Ya implementado (`masmenos.py`, `jugadores.py`) | Es la señal «impacto del once» (−0,0005) |
| Cuotas en vivo y movimiento de línea | — | No se mide | Sin datos suficientes de apertura |

## Resultados

### Apilado sobre el Dixon-Coles (ΔRPS frente al DC sin tocar; entre paréntesis el p95 del remuestreo)

| Configuración | Año 2 | Año 3 | Años 2-3 |
|---|---:|---:|---:|
| Solo recalibrar | −0,00010 (+0,00042) | +0,00040 (+0,00080) | +0,00015 |
| Tiros | −0,00045 (+0,00036) | −0,00049 (+0,00025) | **−0,00047 (+0,00005)** |
| Pi-ratings | −0,00013 | +0,00025 | +0,00006 |
| Forma de xG | +0,00077 | −0,00024 | +0,00027 |
| Viaje | −0,00004 | +0,00045 | +0,00020 |
| Descanso | +0,00017 | +0,00059 | +0,00038 |
| Elo + forma + tiros (lo que hay hoy en producción como sombra) | +0,00027 | −0,00054 | −0,00013 |
| Todo | +0,00209 | −0,00081 | +0,00066 |
| Árboles, todo | +0,00284 | +0,00086 | +0,00186 |

El apilado `elo + forma + tiros` que ya corre en sombra mejoró −0,0018 en su ventana de un año, pero con
origen rodante en 3 años queda en −0,0001: no se sostiene.

### Apilado anclado al cierre de Pinnacle (ΔRPS frente al mercado, 10.572 partidos)

| Configuración | Año 2 | Año 3 | Años 2-3 |
|---|---:|---:|---:|
| Solo recalibrar el mercado | +0,00015 | −0,00013 | +0,00006 |
| Mercado + modelo DC | +0,00060 | −0,00005 | +0,00039 |
| Mercado + tiros | +0,00040 | −0,00035 | +0,00016 |
| Mercado + forma de xG | +0,00032 | −0,00022 | +0,00014 |
| Mercado + pi-ratings | +0,00009 | +0,00004 | +0,00008 |
| Mercado + viaje | +0,00018 | +0,00005 | +0,00014 |
| Mercado + todo | +0,00325 | +0,00064 | +0,00242 |

Ninguno supera la prueba: un factor que añadiera información sobre el cierre daría un valor negativo en los dos años.

### Motivación

8 ligas con tabla (8.251 partidos), 766 con algún equipo sin nada en juego. Con el local «muerto» (n=526): gana el visitante 32,7 %
frente a 30,4 % previsto y el empate sale 23,2 % frente a 25,2 %; con el visitante «muerto» (n=495) todo queda a ≤ 1,6 puntos. Efecto
sobre el RPS: +0,00018. La definición es una aproximación a la «importancia» de la literatura, que pide simulación.

## Qué haría falta para ir más lejos

- **Totales, córners y tarjetas con estadísticas de partido** (Wheatcroft). Es donde se documenta ventaja sobre el mercado, y el
  Motor C ya vive ahí. Falta muestra: 459 partidos con cierre de totales de Pinnacle, 127 de córners y 75 de tarjetas. Con la
  captura actual se llega a ~2.000 partidos en tres o cuatro meses. **Recomendación: conservar el cierre de todos los mercados y
  repetir esta prueba sobre totales cuando haya 2.000 partidos.**
- **Movimiento de línea (apertura → cierre) como señal de CLV.** No se mide porque no hay aperturas de Pinnacle suficientes; las
  capturas horarias de PropLine las irán acumulando.
- **Información de equipo a T-60**: es la parte del hueco que el mercado sí tiene y nosotros solo en parte (once: F1/F4;
  bajas: F3). Lo que ya está medido y suma sigue siendo lo mejor: altitud + once + mezcla dinámica.

## Lo que no se recomienda

- Más características de forma, tiros o ratings de equipo para el 1X2: el mercado ya las tiene.
- Árboles de gradiente con la muestra actual.
- Pasar a un modelo de otra familia solo por estar en el estado del arte: los retos de predicción no usaban xG ni mercado.

Reproducir: `apilado.py`, `apilado_mercado.py`, `estaca.py` en `scripts/entrenamiento_local/mediciones/`.

## Fuentes revisadas (resúmenes)

- Berrar, Lopes y Dubitzky (2019), [Incorporating domain knowledge in machine learning for soccer outcome prediction](https://oro.open.ac.uk/96634).
- Hubáček, Šourek y Železný (2019), [Learning to Predict Soccer Results from Relational Data with Gradient Boosted Trees](https://mlanthology.org/mlj/2019/hubacek2019mlj-learning).
- Yeung et al. (2024), [Evaluating Soccer Match Prediction Models](https://mlanthology.org/mlj/2024/yeung2024mlj-evaluating).
- Egidi, Pauli y Torelli (2018), [Combining historical data and bookmakers' odds in modelling football scores](https://arxiv.org/abs/1802.08848).
- Constantinou (2012), [tesis doctoral, Queen Mary](https://qmro.qmul.ac.uk/xmlui/handle/123456789/8404).
- Wheatcroft (2020), [Forecasting football matches by predicting match statistics](https://arxiv.org/pdf/2001.09097); y [A probabilistic model for predicting shot success](https://arxiv.org/abs/2101.02104v1).
- Koopman y Lit (2019), [score-driven time series models](https://papers.tinbergen.nl/17062.pdf).
- Wunderlich y Memmert (2018), [The betting odds rating system](https://fis.dshs-koeln.de/en/publications/the-betting-odds-rating-system-using-soccer-forecasts-to-forecast/).
- Arntzen y Hvattum (2021), [Statistical Modelling 21(5)](https://statmod.org/smij/Vol21/Iss5/Arntzen/Abstract.html).
- Boshnakov, Kharrat y McHale (2017), [bivariate Weibull count model](https://salford-repository.worktribe.com/output/1395286/a-bivariate-weibull-count-model-for-forecasting-association-football-scores).
- Scarf y Shi, [la importancia de un partido en un torneo](https://salford-repository.worktribe.com/output/1445742/the-importance-of-a-match-in-a-tournament).
- Gilbert, Dixon y Loughead (2020) y [Tyranny of distance](https://lida.sport-iat.de/dfb/Record/4030929) sobre viajes en el fútbol de clubes.
- [Irrational managerial changes remain the norm](https://www.eur.nl/en/ese/news/irrational-managerial-changes-remain-norm-europes-top-football-leagues) (Erasmus), sobre el «rebote» del entrenador.
