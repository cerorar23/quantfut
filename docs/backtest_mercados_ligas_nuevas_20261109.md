# Backtest de todos los mercados de las ligas nuevas — 9-nov-2026

Completa [backtest_ligas_nuevas_20261109.md](backtest_ligas_nuevas_20261109.md) (que solo medía el 1X2 y cinco mercados de
goles) con las cuatro familias que se muestran: **goles** (todas las líneas, hándicap, marcador exacto, margen), **primera mitad**,
**córners** (total, local, visitante) y **tarjetas totales**. Código: `src/qf/eval/backtest_mercados.py`. Mismo tramo limpio
(desde 2025-07-01) y mismas 21 competiciones; córners y tarjetas se reproducen como producción (un acumulador por liga y
estadística, cada partido se predice antes de entrar al acumulador). Datos reales de liquidación con cobertura ≥ 98 % en
todas las ligas (goles, goles al descanso, córners, amarillas, rojas); no hay props de jugador de fútbol publicados.

## Resumen

1. **Criterios fijados antes de ejecutar (A1-A3): las cuatro familias cumplen en las 4 ligas aprobadas** (Turquía, LaLiga 2, Serie B,
   Allsvenskan), en las 8 ligas nuevas y en las 13 actuales.
2. **Ese resultado es más fácil de lo que parece** y por eso añadí, DESPUÉS de verlo, una lectura estricta (marcada como posterior):
   A1 contaba líneas y no partidos (un partido aporta decenas de líneas correlacionadas) y el total lo dominaban líneas triviales.
   Por franja de probabilidad y con el intervalo remuestreando partidos completos:
   - **Goles, córners y tarjetas cumplen en todas las franjas** (0,75-0,80, 0,80-0,85, 0,85-0,90, ≥ 0,90) de las 4 ligas aprobadas.
   - **Primera mitad cumple en 0,75-0,85, pero sobrepromete en 0,85-0,90**: promete 86,6 % y cumple 81,0 % (331 partidos, IC95 de la
     diferencia +1,8 a +9,9 puntos). `gol en 1T: sí` (+3,3 puntos) y `más de 1,5 en 1T: no` (+4,4) quedan por encima en toda la franja alta.
3. **Mercados concretos que incumplen (A2)**: hándicap ±0,75 y −0,25 (+6 a +8 puntos), que **no** se muestran en la ficha. De las líneas
   que sí se muestran, −1,5 (n = 1.119, −1,0 puntos) y +1,5 (n = 1.539, 0,0) cuadran; −1,0 casi no llega al 75 % (n = 6) y no hay evidencia. **Empate no acción** es ambiguo: n = 196 queda 4,2 puntos por
   DEBAJO de lo prometido (conservador) y n = 42 queda 7,4 por ENCIMA; con esa muestra no se concluye.
4. **Calibrado no es informativo.** El skill de Brier frente a la frecuencia de la propia liga es:
   - claro en tarjetas (6-8 %), doble oportunidad (6,8 %), 1X2 (4,6 %), goles por equipo (2-5 %) y ganador del 1T (1,8 %);
   - casi nulo en ambos marcan (−0,9 %), más/menos 1,5 y 2,5 (≈ 0), córners (0,8-1,6 %), gol en 1T y más de 1,5 en 1T (≈ 0, algo negativo).
   Es decir, esas probabilidades reproducen bien el nivel de la liga pero apenas distinguen unos partidos de otros. Los goles totales
   tienen un skill de RMSE de 0,6 %.
5. **«Más de 2,5» y «ambos marcan» casi nunca llegan al 75 %** en estas ligas (n < 10 lados): no entran en la alta probabilidad. El sesgo de
   goles del Dixon-Coles crudo (−0,10 a −0,29 goles por partido) se nota en la zona media (3-9 puntos bajos, ficha del partido), no en la
   alta probabilidad, que sale calibrada.

## Alcance y límites

- **Solo la probabilidad del modelo.** El job de alta probabilidad ancla las lambdas a Pinnacle (`market_anchor`) donde hay cuota y recorta
  los córners a la probabilidad sin margen de la casa; eso no se mide aquí (lo mide `scripts/rediseno_futbol/remedir_semana.py`). Este informe
  cubre lo que muestra la ficha del partido y lo que se publica donde no hay cuota.
- **Muestra por liga corta**: la decisión se toma sobre las 4 aprobadas juntas; por liga, con `n alta` < 30 no se concluye (Suiza y
  Allsvenskan quedan ≈ 2 puntos por encima en goles; no es concluyente).
- Los parámetros de córners, tarjetas y 1T se ajustaron con datos de 2019-2022 y el Dixon-Coles con datos hasta 2025-06: el tramo medido es posterior a todos.
- La ventana de historia de córners y tarjetas parte de 2021-07 (≈ 4 años antes del inicio), como la de `escalera_datos.Modelos`; al final del tramo
  es algo más larga que la de producción, con un efecto despreciable frente a la media vida.
- Cuotas de mercado no intervienen: no se mide ROI ni CLV.

## Recomendaciones (decisión tuya; no se ha cambiado código)

1. Mantener goles, córners y tarjetas en alta probabilidad en las 4 ligas.
2. Limitar la primera mitad a ≤ 0,85 en estas ligas, o dejar `gol en 1T: sí` y `más de 1,5 en 1T: no` fuera hasta tener más partidos.
3. No mostrar hándicap ±0,75 ni −0,25 como alta probabilidad (hoy no se muestran).
4. Presentar ambos marcan, más/menos y córners como probabilidad, no como señal: su skill sobre la base de la liga es ≈ 0.
5. Corregir el nivel de goles del Dixon-Coles antes de promocionar más/menos y ambos marcan en la franja media.

Walk-forward desde 2025-07-01. Alta probabilidad = lado con probabilidad >= 0.75.
Criterios fijados antes de ejecutar: n_alta_min = 100; promesa_max = 0.03; mercado_n_min = 30; mercado_promesa_max = 0.05.

## Veredicto por familia (alta probabilidad)

| Familia | Grupo | n alta | predicha | real | promesa − realidad | IC95 inf. real | Veredicto | Mercados fuera (A2) |
|---|---|---:|---:|---:|---:|---:|---|---|
| Goles (todas las líneas, hándicap, marcador, margen) | aprobadas | 31422 | 0.877 | 0.870 | 0.007 | 0.866 | **APRUEBA** | ah_0.75|directo, ah_-0.75|complemento, ah_-0.25|directo, ah_0.0|complemento |
| Goles (todas las líneas, hándicap, marcador, margen) | nuevas | 62987 | 0.873 | 0.865 | 0.008 | 0.863 | **APRUEBA** | ah_0.75|directo, ah_-0.75|complemento, local_over_1.5|complemento, ah_-0.25|directo, local_over_1.5|directo, 1x2|directo … |
| Goles (todas las líneas, hándicap, marcador, margen) | actuales | 110471 | 0.877 | 0.877 | 0.000 | 0.875 | **APRUEBA** | ah_-0.25|directo, ah_0.5|complemento |
| Primera mitad | aprobadas | 1975 | 0.810 | 0.793 | 0.017 | 0.775 | **APRUEBA** | - |
| Primera mitad | nuevas | 3876 | 0.804 | 0.789 | 0.014 | 0.776 | **APRUEBA** | mas_1_5_1t|complemento |
| Primera mitad | actuales | 7022 | 0.807 | 0.800 | 0.007 | 0.791 | **APRUEBA** | - |
| Córners (total, local, visitante) | aprobadas | 15291 | 0.841 | 0.841 | 0.000 | 0.835 | **APRUEBA** | - |
| Córners (total, local, visitante) | nuevas | 31364 | 0.840 | 0.845 | -0.006 | 0.841 | **APRUEBA** | - |
| Córners (total, local, visitante) | actuales | 52362 | 0.839 | 0.843 | -0.004 | 0.840 | **APRUEBA** | - |
| Tarjetas totales | aprobadas | 6731 | 0.868 | 0.876 | -0.007 | 0.867 | **APRUEBA** | - |
| Tarjetas totales | nuevas | 13863 | 0.882 | 0.887 | -0.005 | 0.882 | **APRUEBA** | - |
| Tarjetas totales | actuales | 23196 | 0.879 | 0.883 | -0.004 | 0.878 | **APRUEBA** | - |

## Lectura estricta por franja de probabilidad (posterior a los criterios; IC95 remuestreando partidos)

| Familia | Grupo | Franja | líneas | partidos | predicha | real | promesa − realidad | IC95 | Estado |
|---|---|---|---:|---:|---:|---:|---:|---|---|
| goles | aprobadas | 0.75-0.80 | 5964 | 1630 | 0.775 | 0.764 | 0.011 | [-0.001, 0.022] | **CUMPLE** |
| goles | aprobadas | 0.80-0.85 | 5608 | 1668 | 0.825 | 0.815 | 0.010 | [-0.002, 0.023] | **CUMPLE** |
| goles | aprobadas | 0.85-0.90 | 6429 | 1682 | 0.876 | 0.873 | 0.003 | [-0.007, 0.014] | **CUMPLE** |
| goles | aprobadas | 0.90-1.00 | 13421 | 1682 | 0.945 | 0.939 | 0.006 | [-0.001, 0.014] | **CUMPLE** |
| goles | actuales | 0.75-0.80 | 21138 | 5700 | 0.775 | 0.775 | -0.000 | [-0.007, 0.006] | **CUMPLE** |
| goles | actuales | 0.80-0.85 | 20426 | 5807 | 0.825 | 0.823 | 0.002 | [-0.005, 0.008] | **CUMPLE** |
| goles | actuales | 0.85-0.90 | 21887 | 5829 | 0.876 | 0.873 | 0.003 | [-0.003, 0.009] | **CUMPLE** |
| goles | actuales | 0.90-1.00 | 47020 | 5841 | 0.946 | 0.947 | -0.001 | [-0.005, 0.002] | **CUMPLE** |
| 1t | aprobadas | 0.75-0.80 | 828 | 740 | 0.775 | 0.767 | 0.008 | [-0.021, 0.037] | **CUMPLE** |
| 1t | aprobadas | 0.80-0.85 | 812 | 812 | 0.824 | 0.813 | 0.011 | [-0.016, 0.038] | **CUMPLE** |
| 1t | aprobadas | 0.85-0.90 | 331 | 331 | 0.866 | 0.810 | 0.056 | [0.018, 0.099] | **INCIERTO** |
| 1t | aprobadas | 0.90-1.00 | 4 | 4 | 0.905 | 1.000 | -0.095 | [-0.098, -0.093] | **SIN_MUESTRA** |
| 1t | actuales | 0.75-0.80 | 3386 | 3006 | 0.774 | 0.767 | 0.008 | [-0.006, 0.022] | **CUMPLE** |
| 1t | actuales | 0.80-0.85 | 2508 | 2501 | 0.823 | 0.816 | 0.007 | [-0.008, 0.023] | **CUMPLE** |
| 1t | actuales | 0.85-0.90 | 1035 | 1035 | 0.868 | 0.864 | 0.004 | [-0.017, 0.026] | **CUMPLE** |
| 1t | actuales | 0.90-1.00 | 93 | 93 | 0.913 | 0.892 | 0.021 | [-0.034, 0.086] | **SIN_MUESTRA** |
| corners | aprobadas | 0.75-0.80 | 3553 | 1547 | 0.775 | 0.778 | -0.003 | [-0.016, 0.009] | **CUMPLE** |
| corners | aprobadas | 0.80-0.85 | 5840 | 1667 | 0.824 | 0.822 | 0.002 | [-0.007, 0.013] | **CUMPLE** |
| corners | aprobadas | 0.85-0.90 | 3235 | 1681 | 0.875 | 0.874 | 0.000 | [-0.010, 0.012] | **CUMPLE** |
| corners | aprobadas | 0.90-1.00 | 2663 | 1703 | 0.926 | 0.928 | -0.002 | [-0.012, 0.009] | **CUMPLE** |
| corners | actuales | 0.75-0.80 | 15210 | 5371 | 0.775 | 0.777 | -0.003 | [-0.009, 0.004] | **CUMPLE** |
| corners | actuales | 0.80-0.85 | 15796 | 5297 | 0.825 | 0.827 | -0.002 | [-0.008, 0.004] | **CUMPLE** |
| corners | actuales | 0.85-0.90 | 13132 | 5557 | 0.873 | 0.879 | -0.006 | [-0.012, -0.001] | **CUMPLE** |
| corners | actuales | 0.90-1.00 | 8224 | 5646 | 0.929 | 0.938 | -0.009 | [-0.013, -0.003] | **CUMPLE** |
| tarjetas | aprobadas | 0.75-0.80 | 1193 | 1093 | 0.775 | 0.795 | -0.021 | [-0.042, 0.001] | **CUMPLE** |
| tarjetas | aprobadas | 0.80-0.85 | 1421 | 1158 | 0.826 | 0.821 | 0.005 | [-0.013, 0.024] | **CUMPLE** |
| tarjetas | aprobadas | 0.85-0.90 | 1873 | 1415 | 0.875 | 0.889 | -0.014 | [-0.028, -0.000] | **CUMPLE** |
| tarjetas | aprobadas | 0.90-1.00 | 2244 | 1571 | 0.939 | 0.941 | -0.003 | [-0.013, 0.010] | **CUMPLE** |
| tarjetas | actuales | 0.75-0.80 | 4276 | 3556 | 0.775 | 0.777 | -0.002 | [-0.014, 0.010] | **CUMPLE** |
| tarjetas | actuales | 0.80-0.85 | 3944 | 3266 | 0.825 | 0.829 | -0.004 | [-0.015, 0.008] | **CUMPLE** |
| tarjetas | actuales | 0.85-0.90 | 4996 | 4177 | 0.875 | 0.882 | -0.007 | [-0.016, 0.002] | **CUMPLE** |
| tarjetas | actuales | 0.90-1.00 | 9980 | 5436 | 0.946 | 0.949 | -0.003 | [-0.008, 0.003] | **CUMPLE** |

## Por liga nueva (contexto; con n alta < 30 no se concluye)

| Familia | Liga | n alta | predicha | real | promesa − realidad |
|---|---|---:|---:|---:|---:|
| goles | tr.super_lig | 7125 | 0.878 | 0.879 | -0.002 |
| goles | es.laliga2 | 10299 | 0.876 | 0.865 | 0.011 |
| goles | it.serie_b | 7923 | 0.878 | 0.882 | -0.003 |
| goles | se.allsvenskan | 6075 | 0.875 | 0.851 | 0.024 |
| goles | ch.super_league | 5036 | 0.863 | 0.843 | 0.021 |
| goles | no.eliteserien | 6508 | 0.872 | 0.859 | 0.013 |
| goles | gb.championship | 12978 | 0.876 | 0.870 | 0.006 |
| goles | de.bundesliga2 | 7043 | 0.858 | 0.857 | 0.001 |
| 1t | tr.super_lig | 469 | 0.803 | 0.808 | -0.005 |
| 1t | es.laliga2 | 659 | 0.814 | 0.780 | 0.034 |
| 1t | it.serie_b | 479 | 0.817 | 0.808 | 0.009 |
| 1t | se.allsvenskan | 368 | 0.804 | 0.780 | 0.024 |
| 1t | ch.super_league | 312 | 0.781 | 0.763 | 0.018 |
| 1t | no.eliteserien | 399 | 0.793 | 0.815 | -0.021 |
| 1t | gb.championship | 777 | 0.814 | 0.799 | 0.015 |
| 1t | de.bundesliga2 | 413 | 0.779 | 0.748 | 0.031 |
| corners | tr.super_lig | 3348 | 0.840 | 0.840 | 0.000 |
| corners | es.laliga2 | 5108 | 0.840 | 0.842 | -0.002 |
| corners | it.serie_b | 3954 | 0.838 | 0.834 | 0.005 |
| corners | se.allsvenskan | 2881 | 0.850 | 0.853 | -0.003 |
| corners | ch.super_league | 2700 | 0.834 | 0.857 | -0.023 |
| corners | no.eliteserien | 3044 | 0.849 | 0.855 | -0.007 |
| corners | gb.championship | 6614 | 0.838 | 0.849 | -0.010 |
| corners | de.bundesliga2 | 3715 | 0.833 | 0.840 | -0.007 |
| tarjetas | tr.super_lig | 1483 | 0.863 | 0.844 | 0.019 |
| tarjetas | es.laliga2 | 2141 | 0.850 | 0.856 | -0.006 |
| tarjetas | it.serie_b | 1725 | 0.863 | 0.876 | -0.013 |
| tarjetas | se.allsvenskan | 1382 | 0.908 | 0.938 | -0.030 |
| tarjetas | ch.super_league | 1143 | 0.868 | 0.891 | -0.022 |
| tarjetas | no.eliteserien | 1523 | 0.923 | 0.925 | -0.002 |
| tarjetas | gb.championship | 2974 | 0.907 | 0.899 | 0.008 |
| tarjetas | de.bundesliga2 | 1492 | 0.865 | 0.875 | -0.010 |

## Mercados del grupo «aprobadas» con muestra en alta probabilidad

| Familia | Mercado | Lado | n | predicha | real | promesa − realidad |
|---|---|---|---:|---:|---:|---:|
| goles | over_0.5 | directo | 1682 | 0.917 | 0.927 | -0.010 |
| goles | over_5.5 | complemento | 1680 | 0.943 | 0.948 | -0.005 |
| goles | visitante_over_3.5 | complemento | 1678 | 0.963 | 0.964 | -0.001 |
| goles | local_over_3.5 | complemento | 1650 | 0.934 | 0.936 | -0.002 |
| goles | ah_1.75 | directo | 1613 | 0.915 | 0.877 | 0.037 |
| goles | over_4.5 | complemento | 1579 | 0.877 | 0.875 | 0.001 |
| goles | visitante_over_2.5 | complemento | 1567 | 0.894 | 0.884 | 0.011 |
| goles | ah_1.5 | directo | 1539 | 0.886 | 0.886 | -0.000 |
| goles | ah_2.0 | directo | 1514 | 0.953 | 0.951 | 0.002 |
| goles | ah_1.25 | directo | 1485 | 0.879 | 0.887 | -0.008 |
| goles | ah_-1.75 | complemento | 1400 | 0.862 | 0.826 | 0.037 |
| goles | ah_-2.0 | complemento | 1391 | 0.908 | 0.905 | 0.003 |
| goles | local_over_2.5 | complemento | 1328 | 0.852 | 0.842 | 0.010 |
| goles | doble_oportunidad | directo | 1238 | 0.798 | 0.796 | 0.002 |
| goles | ah_1.0 | directo | 1167 | 0.875 | 0.875 | 0.000 |
| goles | ah_-1.5 | complemento | 1119 | 0.836 | 0.845 | -0.010 |
| goles | ah_0.75 | directo | 1047 | 0.828 | 0.761 | 0.067 |
| goles | ah_-1.25 | complemento | 939 | 0.832 | 0.850 | -0.018 |
| goles | local_over_0.5 | directo | 877 | 0.817 | 0.815 | 0.002 |
| goles | over_3.5 | complemento | 774 | 0.805 | 0.786 | 0.019 |
| goles | over_1.5 | directo | 713 | 0.807 | 0.801 | 0.006 |
| goles | ah_-1.0 | complemento | 598 | 0.833 | 0.819 | 0.014 |
| goles | ah_0.5 | directo | 579 | 0.811 | 0.801 | 0.010 |
| goles | visitante_over_1.5 | complemento | 482 | 0.794 | 0.757 | 0.036 |
| goles | ah_0.25 | directo | 381 | 0.813 | 0.845 | -0.032 |
| goles | visitante_over_0.5 | directo | 339 | 0.808 | 0.829 | -0.021 |
| goles | ah_-0.75 | complemento | 316 | 0.810 | 0.750 | 0.060 |
| goles | ah_0.0 | directo | 196 | 0.815 | 0.857 | -0.042 |
| goles | ah_-0.5 | complemento | 116 | 0.813 | 0.819 | -0.006 |
| goles | local_over_1.5 | complemento | 109 | 0.788 | 0.761 | 0.027 |
| goles | ah_-0.25 | complemento | 82 | 0.811 | 0.817 | -0.006 |
| goles | ah_-0.25 | directo | 68 | 0.803 | 0.721 | 0.082 |
| goles | ah_0.0 | complemento | 42 | 0.812 | 0.738 | 0.074 |
| 1t | ambos_1t_si | complemento | 1526 | 0.821 | 0.810 | 0.011 |
| 1t | gol_1t_si | directo | 250 | 0.777 | 0.744 | 0.033 |
| 1t | mas_1_5_1t | complemento | 199 | 0.773 | 0.729 | 0.044 |
| corners | corners_local_over_1.5 | directo | 1706 | 0.935 | 0.931 | 0.004 |
| corners | corners_local_over_2.5 | directo | 1706 | 0.841 | 0.834 | 0.007 |
| corners | corners_over_6.5 | directo | 1706 | 0.821 | 0.817 | 0.005 |
| corners | corners_visitante_over_1.5 | directo | 1706 | 0.878 | 0.884 | -0.006 |
| corners | corners_visitante_over_7.5 | complemento | 1706 | 0.883 | 0.880 | 0.002 |
| corners | corners_visitante_over_6.5 | complemento | 1549 | 0.820 | 0.818 | 0.002 |
| corners | corners_local_over_7.5 | complemento | 1450 | 0.804 | 0.809 | -0.005 |
| corners | corners_over_12.5 | complemento | 1385 | 0.827 | 0.828 | -0.001 |
| corners | corners_over_11.5 | complemento | 683 | 0.766 | 0.742 | 0.023 |
| corners | corners_visitante_over_2.5 | directo | 541 | 0.787 | 0.800 | -0.013 |
| corners | corners_over_7.5 | directo | 345 | 0.812 | 0.791 | 0.020 |
| corners | corners_visitante_over_5.5 | complemento | 331 | 0.763 | 0.798 | -0.035 |
| corners | corners_local_over_3.5 | directo | 313 | 0.777 | 0.827 | -0.050 |
| corners | corners_local_over_6.5 | complemento | 114 | 0.761 | 0.798 | -0.037 |
| corners | corners_over_8.5 | directo | 50 | 0.759 | 0.760 | -0.001 |
| tarjetas | cards_over_8.5 | complemento | 1706 | 0.931 | 0.930 | 0.001 |
| tarjetas | cards_over_7.5 | complemento | 1683 | 0.875 | 0.883 | -0.008 |
| tarjetas | cards_over_2.5 | directo | 1427 | 0.858 | 0.849 | 0.009 |
| tarjetas | cards_over_6.5 | complemento | 1147 | 0.823 | 0.844 | -0.021 |
| tarjetas | cards_over_3.5 | directo | 411 | 0.783 | 0.796 | -0.013 |
| tarjetas | cards_over_5.5 | complemento | 323 | 0.821 | 0.876 | -0.055 |
| tarjetas | cards_over_4.5 | complemento | 32 | 0.773 | 0.906 | -0.133 |
