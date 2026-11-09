# Backtest de las ligas nuevas — 9-nov-2026

Modelo candidato: Dixon-Coles + xG de producción (semivida 270, mezcla 0,65) entrenado en local con 21 competiciones
(`2026.11.09-063559`, 82.421 partidos; solo en la copia local, nada subido). Código: `src/qf/eval/backtest_ligas_nuevas.py`;
resultados crudos y reproducción: `.local/backtest_ligas_nuevas/` (4 variantes, pasos de 30 días desde 2025-07-01).

## Resumen

- **Aprueban los criterios fijados de antemano (C1-C3 y C4): Turquía, LaLiga 2, Serie B y Allsvenskan.**
- **Noruega y Suiza se quedan en observación**: pasan C1 y C2 con holgura, pero fallan C3 por muy poco (sesgo medio por resultado
  0,0528 y 0,0536 frente al límite 0,05). Con ~300 partidos el error típico de ese sesgo es ≈ 0,027, así que es ruido
  plausible, pero el criterio estaba fijado antes de medir y no se mueve ahora: se vuelven a medir con más partidos.
- **Championship y 2. Bundesliga no aprueban**: el modelo apenas mejora a la frecuencia de la liga (skill 1,3-1,5 %, intervalo
  que incluye 0). Son ligas muy parejas; no hay evidencia de que el modelo aporte algo.
- **Añadir las 8 ligas no empeora lo ya publicado (C4)**: ninguna de las 13 competiciones actuales empeora; Primeira mejora
  (−0,0020, IC [−0,0030, −0,0010]).
- **El xG parcial no estorba**: en Serie B (38 % con xG) y LaLiga 2 (69 %) el resultado sin xG es prácticamente idéntico al de
  `pit` (log-loss 1,0452 frente a 1,0466 y 1,0533 frente a 1,0537). El hueco permanente de xG no es motivo para descartarlas.
- **El mercado sigue ganando**: en las 8 ligas el RPS de Pinnacle/PropLine sin margen es mejor que el del modelo (diferencias de
  0,004 a 0,014). Coherente con el rediseño del 1-nov: donde hay cuota se publica la probabilidad del mercado; el modelo solo
  cubre lo que el mercado no cotiza. Muestras con cuota: 104-421 partidos por liga.

## Límites que hay que conocer

1. **Solo 1X2 y cinco mercados de goles.** El resto de familias (goles completos, hándicap, marcador exacto, primera mitad, córners y tarjetas) se midió después en [backtest_mercados_ligas_nuevas_20261109.md](backtest_mercados_ligas_nuevas_20261109.md). No hay props de jugador de fútbol publicados.
2. **La base del criterio C2 es débil** (frecuencia de local/empate/visitante de la liga): superarla no equivale a competir
   con un modelo de fuerza de equipos; por eso se informa también el mercado.
3. **Sesgo de goles en todo el modelo, no solo en las ligas nuevas.** En el tramo medido el Dixon-Coles crudo predice menos
   goles que los reales en 16 de 21 competiciones y en 11 la diferencia es de 0,10 goles por partido o más (Bundesliga −0,18,
   Eredivisie −0,22, MLS −0,17, Champions −0,29; Championship −0,15, Noruega −0,26, Suiza −0,25). No cambia al quitar el xG. Consecuencia: `over`/`ambos marcan`
   salen 3-9 puntos por debajo de lo real en varias ligas (p. ej. over 2,5 en Suiza: 59,8 % predicho frente a 68,7 % real) y su
   skill de Brier sobre la frecuencia del periodo es negativo en la mayoría. Producción publica ese modelo sin calibrar (el
   calibrador lo rechazó su puerta). Abre una tarea propia: medir el sesgo en las 13 actuales y decidir una corrección de nivel
   (semivida corta para el nivel de goles o ajuste por temporada) antes de mostrar over/ambos marcan como alta probabilidad.
4. **xG recibido tarde**: el xG de las ligas nuevas con procedencia solo cuenta desde su recepción real (`pit`). Un backtest que
   lo trate como siempre disponible (`reconstruccion`) mejora Allsvenskan, Suiza y 2. Bundesliga hasta 0,01 de log-loss: ese
   número es optimista y no decide nada.
5. **Muestra corta**: 278-706 partidos por liga en 16 meses; los intervalos son anchos y se ven sobre todo en Suiza y Noruega.
6. **No se comparó contra el artefacto exacto de producción**, sino contra el mismo código sin las 8 ligas (`sin_nuevas`); la
   puerta de `train` marca «champion histórico no comparable: ventana distinta».

Walk-forward desde 2025-07-01, reentrenado cada 30 dias solo con partidos anteriores al corte.
Criterios fijados antes de medir: n_min = 150, ece_max = 0.05, sesgo_max = 0.05, regresion_max = 0.005.

## Veredicto (variante `pit`)

| Liga | n | log-loss | base previa | skill | IC95 dif. vs base | ECE | sesgo max | C1 | C2 | C3 | Veredicto |
|---|---:|---:|---:|---:|---|---:|---:|:-:|:-:|:-:|---|
| gb.championship | 706 | 1.0652 | 1.0787 | 0.0125 | [-0.0306, 0.0037] | 0.0193 | 0.0110 | si | no | si | **DEPENDE_DE_XG_RECIBIDO_TARDE** |
| de.bundesliga2 | 390 | 1.0465 | 1.0620 | 0.0146 | [-0.0361, 0.0051] | 0.0093 | 0.0363 | si | no | si | **DEPENDE_DE_XG_RECIBIDO_TARDE** |
| tr.super_lig | 375 | 0.9924 | 1.0808 | 0.0818 | [-0.1277, -0.0491] | 0.0178 | 0.0154 | si | si | si | **APRUEBA** |
| no.eliteserien | 346 | 0.9349 | 1.0303 | 0.0927 | [-0.1306, -0.0604] | 0.0335 | 0.0528 | si | si | no | **NO_APRUEBA** |
| es.laliga2 | 555 | 1.0537 | 1.0818 | 0.0260 | [-0.0458, -0.0103] | 0.0082 | 0.0286 | si | si | si | **APRUEBA** |
| it.serie_b | 427 | 1.0466 | 1.0740 | 0.0255 | [-0.0530, -0.0017] | 0.0286 | 0.0392 | si | si | si | **APRUEBA** |
| se.allsvenskan | 325 | 1.0317 | 1.0764 | 0.0415 | [-0.0818, -0.0076] | 0.0330 | 0.0417 | si | si | si | **APRUEBA** |
| ch.super_league | 278 | 1.0404 | 1.0804 | 0.0371 | [-0.0653, -0.0148] | 0.0414 | 0.0536 | si | si | no | **DEPENDE_DE_XG_RECIBIDO_TARDE** |

## Cuanto aporta el xG y que pasa si se reconstruye

| Liga | log-loss `pit` | `reconstruccion` | sin xG (`goles`) | RPS `pit` | RPS sin xG |
|---|---:|---:|---:|---:|---:|
| gb.championship | 1.0652 | 1.0610 | 1.0655 | 0.2244 | 0.2244 |
| de.bundesliga2 | 1.0465 | 1.0393 | 1.0451 | 0.2220 | 0.2215 |
| tr.super_lig | 0.9924 | 0.9891 | 0.9903 | 0.1988 | 0.1981 |
| no.eliteserien | 0.9349 | 0.9375 | 0.9341 | 0.1991 | 0.1987 |
| es.laliga2 | 1.0537 | 1.0541 | 1.0533 | 0.2254 | 0.2253 |
| it.serie_b | 1.0466 | 1.0464 | 1.0452 | 0.2089 | 0.2084 |
| se.allsvenskan | 1.0317 | 1.0217 | 1.0319 | 0.2220 | 0.2221 |
| ch.super_league | 1.0404 | 1.0308 | 1.0390 | 0.2228 | 0.2223 |

## Frente al mercado (informativo, no decide)

| Liga | n con cuota | RPS modelo | RPS mercado | log-loss modelo | log-loss mercado |
|---|---:|---:|---:|---:|---:|
| gb.championship | 421 | 0.2270 | 0.2183 | 1.0725 | 1.0467 |
| de.bundesliga2 | 174 | 0.2245 | 0.2193 | 1.0398 | 1.0271 |
| tr.super_lig | 198 | 0.1975 | 0.1840 | 0.9909 | 0.9428 |
| no.eliteserien | 220 | 0.1913 | 0.1802 | 0.9283 | 0.8938 |
| es.laliga2 | 281 | 0.2357 | 0.2281 | 1.0989 | 1.0796 |
| it.serie_b | 128 | 0.2160 | 0.2041 | 1.1024 | 1.0580 |
| se.allsvenskan | 236 | 0.2257 | 0.2176 | 1.0261 | 1.0008 |
| ch.super_league | 104 | 0.2308 | 0.2287 | 1.0386 | 1.0329 |

## Mercados de goles (variante `pit`; informa, no decide)

Probabilidad media predicha frente a la frecuencia real, y mejora (skill) sobre predecir siempre la frecuencia del periodo.

| Liga | Mercado | n | predicha | real | dif. | skill Brier |
|---|---|---:|---:|---:|---:|---:|
| gb.championship | btts | 735 | 0.502 | 0.580 | -0.078 | -0.0289 |
| gb.championship | doble_oportunidad | 2205 | 0.667 | 0.667 | +0.000 | 0.0291 |
| gb.championship | over_1.5 | 735 | 0.719 | 0.766 | -0.047 | -0.0373 |
| gb.championship | over_2.5 | 735 | 0.463 | 0.533 | -0.070 | -0.0517 |
| gb.championship | over_3.5 | 735 | 0.253 | 0.279 | -0.026 | -0.0248 |
| de.bundesliga2 | btts | 405 | 0.599 | 0.588 | +0.011 | -0.0390 |
| de.bundesliga2 | doble_oportunidad | 1215 | 0.667 | 0.667 | +0.000 | 0.0545 |
| de.bundesliga2 | over_1.5 | 405 | 0.807 | 0.795 | +0.012 | -0.0242 |
| de.bundesliga2 | over_2.5 | 405 | 0.583 | 0.578 | +0.005 | -0.0347 |
| de.bundesliga2 | over_3.5 | 405 | 0.363 | 0.314 | +0.049 | -0.0476 |
| tr.super_lig | btts | 405 | 0.514 | 0.523 | -0.009 | -0.0164 |
| tr.super_lig | doble_oportunidad | 1215 | 0.667 | 0.667 | +0.000 | 0.1002 |
| tr.super_lig | over_1.5 | 405 | 0.752 | 0.770 | -0.019 | -0.0032 |
| tr.super_lig | over_2.5 | 405 | 0.510 | 0.546 | -0.036 | 0.0148 |
| tr.super_lig | over_3.5 | 405 | 0.297 | 0.286 | +0.011 | 0.0306 |
| no.eliteserien | btts | 353 | 0.567 | 0.603 | -0.036 | -0.0151 |
| no.eliteserien | doble_oportunidad | 1059 | 0.667 | 0.667 | +0.000 | 0.1705 |
| no.eliteserien | over_1.5 | 353 | 0.803 | 0.861 | -0.059 | -0.0695 |
| no.eliteserien | over_2.5 | 353 | 0.580 | 0.640 | -0.060 | -0.0028 |
| no.eliteserien | over_3.5 | 353 | 0.364 | 0.416 | -0.052 | -0.0466 |
| es.laliga2 | btts | 588 | 0.497 | 0.549 | -0.053 | -0.0100 |
| es.laliga2 | doble_oportunidad | 1764 | 0.667 | 0.667 | +0.000 | 0.0372 |
| es.laliga2 | over_1.5 | 588 | 0.714 | 0.719 | -0.006 | -0.0041 |
| es.laliga2 | over_2.5 | 588 | 0.461 | 0.500 | -0.039 | -0.0087 |
| es.laliga2 | over_3.5 | 588 | 0.254 | 0.279 | -0.025 | 0.0215 |
| it.serie_b | btts | 470 | 0.498 | 0.547 | -0.049 | -0.0290 |
| it.serie_b | doble_oportunidad | 1410 | 0.667 | 0.667 | +0.000 | 0.0371 |
| it.serie_b | over_1.5 | 470 | 0.717 | 0.760 | -0.042 | -0.0173 |
| it.serie_b | over_2.5 | 470 | 0.461 | 0.491 | -0.030 | -0.0221 |
| it.serie_b | over_3.5 | 470 | 0.252 | 0.255 | -0.003 | -0.0167 |
| se.allsvenskan | btts | 334 | 0.534 | 0.527 | +0.007 | -0.0024 |
| se.allsvenskan | doble_oportunidad | 1002 | 0.667 | 0.667 | +0.000 | 0.0744 |
| se.allsvenskan | over_1.5 | 334 | 0.767 | 0.796 | -0.030 | -0.0271 |
| se.allsvenskan | over_2.5 | 334 | 0.529 | 0.545 | -0.016 | 0.0101 |
| se.allsvenskan | over_3.5 | 334 | 0.315 | 0.311 | +0.004 | 0.0033 |
| ch.super_league | btts | 294 | 0.600 | 0.660 | -0.060 | -0.0092 |
| ch.super_league | doble_oportunidad | 882 | 0.667 | 0.667 | +0.000 | 0.0650 |
| ch.super_league | over_1.5 | 294 | 0.816 | 0.854 | -0.038 | 0.0002 |
| ch.super_league | over_2.5 | 294 | 0.598 | 0.687 | -0.089 | -0.0157 |
| ch.super_league | over_3.5 | 294 | 0.380 | 0.425 | -0.045 | -0.0254 |

## C4: las 13 competiciones actuales no empeoran

Evaluado: si. Competiciones peores: ninguna.

| Liga | dif. log-loss (con nuevas - sin nuevas) | IC95 |
|---|---:|---|
| ar.primera | 0.00010 | [-0.00019, 0.00039] |
| br.serie_a | -0.00014 | [-0.00041, 0.00014] |
| de.bundesliga | -0.00414 | [-0.01401, 0.00572] |
| es.laliga | -0.00184 | [-0.00860, 0.00491] |
| eu.ucl | -0.01106 | [-0.03230, 0.01017] |
| eu.uel | -0.02595 | [-0.05793, 0.00602] |
| fr.ligue_1 | -0.00023 | [-0.00129, 0.00083] |
| gb.premier_league | 0.01019 | [-0.00638, 0.02675] |
| it.serie_a | 0.00418 | [-0.00457, 0.01292] |
| mx.liga_mx | 0.00004 | [-0.00038, 0.00046] |
| nl.eredivisie | -0.00071 | [-0.00183, 0.00041] |
| pt.primeira | -0.00199 | [-0.00300, -0.00097] |
| us.mls | 0.00002 | [-0.00020, 0.00024] |
