# NBA — entrenamiento y calibración del motor en todos los mercados (24-oct-2026)

Dos corridas con protocolo congelado antes de calcular (ambas: se ajusta con 2024-25 y se evalúa sin reajustar en 2025-26; solo datos retrospectivos, no se promueve nada
y no se toca el motor vivo):

| Corrida | Qué responde | Código | Protocolo |
| --- | --- | --- | --- |
| Equipo contra el cierre de bet365 | ¿El motor mejora o calibra mejor que el precio, en 9 mercados con cuota? | `team_markets.py` | `nba_team_markets_protocol.json` (v1.1) |
| Calibración del motor contra resultados | ¿Están calibradas sus distribuciones en todas las líneas, con y sin cuota? | `engine_calibration.py` | `nba_engine_calibration_protocol.json` |

Salidas en `apps/nba/.local/normalized/nba_team_markets_20261024/` y `nba_engine_calibration_20261024/` (informes, parámetros con `promoted: false`).

## 1. Mercados de equipo con cuota de bet365 (9 mercados, ~1.100-1.200 partidos de prueba)
Ganador, hándicap y total del partido, de la primera mitad y de Q1. El motor es el modelo de equipo v1.5 (Elo con margen, medias de puntos y covarianza), convertido en una
distribución normal del margen y del total (en periodos, con una relación lineal ajustada en temporadas anteriores). Veredicto de los nueve: **sin evidencia de que mejore el cierre**.

- Con la probabilidad del motor sola, el Brier es peor que el del precio: ganador +0,0048, hándicap +0,0077, total +0,0146 (partido); +0,0021 / +0,0035 / +0,0159 (mitad); +0,0033 / +0,0035 / +0,0067 (Q1).
- Recalibrar el precio no aporta nada (|Δ Brier| ≤ 0,0004 en todos): el cierre de bet365 ya está bien calibrado (pendiente del ganador 1,08; de la mitad 0,95 y Q1 1,08).
- Añadir disponibilidad y descanso tampoco ayuda (el modelo completo contra recalibrar queda dentro de ±0,0011, con intervalos que incluyen 0).
- **Hallazgo de medida:** en hándicap y total la línea de cierre deja la probabilidad en ~50 %, así que el Brier contra el mercado casi no discrimina (≈ 0,25). Por eso la segunda corrida mide
  la distribución del motor en varias líneas.

## 2. Calibración del motor en todas las líneas

### Equipo (12 mercados; 5.845 unidades de prueba por mercado; IC 99,58 %)
Líneas: `floor(media + z·sd) + 0,5` para z de −1 a +1. «Base» = climatología (misma ley normal con la media y sd de las dos temporadas anteriores).

| Mercado | Brier motor | Brier base | Motor − base | Pendiente | Intercepto | RMSE motor / climatología |
| --- | --- | --- | --- | --- | --- | --- |
| Total del partido | 0,1911 | 0,2010 | −0,0098 | 0,97 | +0,086 | 19,27 / 20,34 |
| Margen del partido | 0,1845 | 0,2123 | −0,0278 | 1,05 | +0,013 | 14,23 / 16,36 |
| Puntos local | 0,1950 | 0,2098 | −0,0148 | 0,93 | +0,102 | 12,26 / 13,16 |
| Puntos visitante | 0,1888 | 0,2093 | −0,0204 | 1,00 | +0,083 | 11,69 / 12,95 |
| Total 1.ª mitad | 0,1885 | 0,1952 | −0,0067 | 1,01 | +0,157 | 12,51 / 12,89 |
| Margen 1.ª mitad | 0,1894 | 0,2056 | −0,0162 | 0,99 | +0,036 | 11,17 / 12,12 |
| Total Q1 | 0,1894 | 0,1953 | −0,0060 | 1,00 | +0,205 | 8,44 / 8,68 |
| Margen Q1 | 0,1863 | 0,1954 | −0,0091 | 1,03 | +0,019 | 8,25 / 8,60 |
| Total 2.ª mitad | 0,1870 | 0,1923 | −0,0052 | 1,02 | −0,044 | 14,11 / 14,52 |
| Margen 2.ª mitad | 0,1877 | 0,1956 | −0,0079 | 1,01 | +0,058 | 10,77 / 11,27 |
| Total Q2 | 0,1873 | 0,1880 | −0,0007 (sin señal) | 1,02 | +0,016 | 8,43 / 8,48 |
| Margen Q2 | 0,1923 | 0,1987 | −0,0064 | 0,96 | +0,012 | 8,41 / 8,70 |

- **Con habilidad en 11 de 12** (todos menos el total de Q2). Las pendientes son ≈ 1: la forma de la distribución está bien.
- **Calibración incompleta en totales:** el intercepto es positivo (+0,09 a +0,21) en total del partido, puntos del local, total de mitad y total de Q1 porque en 2025-26 se anotó más que lo que
  predice la tendencia de las temporadas de ajuste (el Over ocurre 1,7 a 3,9 puntos más que lo previsto). La recalibración ajustada en 2024-25 no lo corrige en 2025-26 (no mejora, intervalos con 0): es deriva de la anotación de la liga, no un error fijo.
- **La línea de bet365 es mejor centro que el motor:** RMSE del motor 19,27 contra 18,36 de la línea en el total (mitad 12,51 contra 11,79; Q1 8,44 contra 8,20; margen 14,23 contra 13,89). En el total, las desviaciones del motor
  respecto a la línea tienen peso **negativo** (β = −0,39, IC 95 % [−0,73; −0,05]; mitad −0,28 [−0,55; −0,01]) y en el margen y Q1 cero: no hay información del motor sobre la línea.
- No se evaluó Q3 ni Q4 (no están en el archivo normalizado) ni el margen por rangos.

### Jugador sin cuota (9 mercados; 24-122 mil unidades de prueba; IC 99,44 %)
Motor = ley v1 (binomial negativa + muestra empírica, peso 0,25) aplicada tal cual a cada conteo y combinación. «Base» = frecuencia empírica de los últimos 20 partidos.
«F» = recalibración más disponibilidad (reportes T-60) y entorno del partido (total, hándicap, ritmo, defensa rival, descanso, minutos), ajustado en 2024-25.

| Mercado | Brier motor | Brier base | Pendiente motor | Recalibrar mejora | Brier con variables (F) | F − recalibración | Pendiente F |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Robos | 0,1364 | 0,1395 | 0,91 | no | 0,1358 | −0,00045 | 0,99 |
| Tapones | 0,1039 | 0,1064 | 0,91 | sí (−0,0002) | 0,1035 | −0,00023 | 0,99 |
| Pérdidas | 0,1543 | 0,1576 | 0,99 | no | 0,1529 | −0,00127 | 1,01 |
| Robos + tapones | 0,1615 | 0,1649 | 0,92 | sí (−0,0002) | 0,1606 | −0,00080 | 1,00 |
| Puntos + rebotes | 0,2082 | 0,2084 | **0,78** | sí (−0,0029) | 0,2005 | −0,00477 | 1,03 |
| Puntos + asistencias | 0,2083 | 0,2075 | **0,77** | sí (−0,0034) | 0,1996 | −0,00522 | 1,02 |
| Rebotes + asistencias | 0,1914 | 0,1939 | 0,90 | sí (−0,0007) | 0,1873 | −0,00341 | 1,02 |
| Puntos + rebotes + asistencias | 0,2063 | 0,2066 | **0,79** | sí (−0,0026) | 0,1983 | −0,00543 | 1,03 |
| Doble-doble | 0,0559 | 0,0696 | 1,31 (subconfiado) | no concluyente | 0,0550 | −0,00031 (sin efecto) | 1,00 |

- **El motor v1 aplicado a las combinaciones está sobreconfiado** (pendiente ≈ 0,78, prevé de más el Over). En puntos+rebotes, puntos+asistencias y PRA no supera a la frecuencia empírica. Recalibrar corrige parte, y **las variables
  lo corrigen del todo** (pendiente ≈ 1,03 y Brier −0,005).
- **La variable que más pesa es el minutaje perdido de los compañeros** (coeficiente +0,31 en puntos+rebotes y +0,34 en PRA): sin compañeros, el jugador produce más, y la ley v1 solo mira su propio historial.
  Es información de los reportes oficiales T-60, previa al partido. Le siguen la defensa rival, los minutos recientes y el hándicap.
- **Control del placebo superado en los nueve mercados** (las mismas variables barajadas dentro de fecha no mejoran la recalibración): no hay fuga.
- Robos, tapones y pérdidas están bien calibrados y con habilidad; las variables aportan una mejora pequeña pero significativa.
- En estos mercados las variables sí ayudan, a diferencia del resultado contra el mercado de props: ese ya contiene lo mismo (descanso, ritmo, bajas). Es coherente.

## 3. Qué significa para el motor
1. **Mercados con precio** (ganador, hándicap, total, mitad, Q1, puntos/rebotes/asistencias/triples): la mejor probabilidad es la del precio (recalibrado en props). El motor no la mejora.
2. **Mercados sin precio:** el motor es utilizable y está calibrado en equipo y en robos/tapones/pérdidas. En combinaciones debe usarse **con la recalibración y las variables (F)**, no la ley v1 cruda.
3. **Pendiente de calibrar** en equipo: la deriva de anotación de la liga (intercepto en totales). Tiene sentido una recalibración móvil dentro de la temporada.
4. Los parámetros están en `engine_calibration_params.json` con `promoted: false`. **No se aplicaron al motor vivo**: eso es una decisión y un cambio de protocolo aparte.

## 4. Controles y límites
- Enmienda previa a cualquier corrida real: el placebo del protocolo de equipo se comparaba con la recalibración y sale siempre «mejor» si el modelo es informativo (conserva `model_delta`); se cambió a compararlo con el modelo solo (v1.1).
- Reproducciones exactas: el Brier del ganador de v1.5 se reprodujo a 1e-9 en 2024-25 y 2025-26.
- Un solo año de ajuste (2024-25) y uno de prueba (2025-26); los intervalos agrupan por fecha pero no por jugador. No cubre Q3/Q4, margen por rangos, triple-doble ni mercados de primer encesto.
- Los resultados contra el mercado son del cierre de bet365; una sola casa.
