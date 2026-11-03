# Rediseño NBA — Sprint 2: disponibilidad y minutos (resultados)

> Evaluación hacia adelante con datos de `nba_datos` (cajas y partes 2021-22 a 2025-26); temporada de prueba 2025-26, todo lo
> ajustado usa temporadas anteriores. Reproducible con `apps/nba/ops/evaluar_s2.py` sobre dos CSV exportados de la base.

## 1. Del estado oficial a la probabilidad de jugar

Se tomó el último parte oficial antes de cada partido y se contó quién jugó de verdad (quien no figura en la caja cuenta
como que no jugó). Probabilidad de jugar por estado y temporada:

| Estado | 2021-22 | 2022-23 | 2023-24 | 2024-25 | 2025-26 |
|---|---|---|---|---|---|
| Out | 0,2 % | 0,2 % | 0,0 % | 0,0 % | 0,0 % |
| Doubtful | 3,6 % | 2,2 % | 0 % (n=21) | 0 % (n=34) | 0 % (n=19) |
| Questionable | 51,9 % | 48,9 % | 59,3 % (n=270) | 43,9 % (n=230) | 41,5 % (n=130) |
| Probable | 93,2 % | 89,3 % | 90,4 % (n=114) | 80,6 % (n=124) | 71,4 % (n=70) |
| Available | 74,4 % | 73,4 % | 83,0 % | 84,3 % | 84,7 % |

* **«Out» y «Doubtful» equivalen a no juega** (≤ 0,2 %); «Questionable» es una moneda al aire que ha ido bajando; «Probable»
  ya no es «casi seguro». «Available» (84 %) mezcla titulares y jugadores del fondo de la plantilla.
* **Los partes cambian de significado con los años**: por eso la tabla se mide con las temporadas recientes y se
  vuelve a medir cada temporada. Las muestras de 2023-24 en adelante son pequeñas para Questionable/Probable/Doubtful.
* Quien no figura en el parte y sí aparece en la caja jugó el 84 % de las veces (151.062 casos): ese número incluye
  suplentes que no juegan, así que **falta condicionar a la probabilidad de jugar por rol** (minutos esperados).

**Brier de la probabilidad de jugar en 2025-26 (14.049 jugador-partido con parte):**

| Probabilidad usada | Brier |
|---|---|
| Tasa global (sin estado) | 0,133 |
| Convención inicial que escribí antes de medir | 0,0289 |
| **Tabla medida en 2024-25** | **0,0266** |
| Tabla medida en todas las temporadas anteriores | 0,0270 |

La tabla medida mejora a la convención un 8 % y a la tasa global casi 5 veces. `disponibilidad.P_JUEGA` queda con los
valores agrupados de 2024-25 y 2025-26 (Out 0,001 · Doubtful 0,01 · Questionable 0,43 · Probable 0,77 · Available 0,845).

## 2. Minutos si juega

Pronóstico puntual = media ponderada de los últimos partidos jugados con decaimiento 0,70 por partido (ventana de 20),
elegido con 2023-24 y 2024-25 (con 0,90 el modelo solo igualaba a la línea base). Incertidumbre = cuantiles de los
residuos de temporadas anteriores, por tramo de minutos esperados (< 15, 15-25, ≥ 25).

| Prueba 2025-26 (27.251 partidos jugados) | Línea base (media de 5) | Modelo |
|---|---|---|
| Error absoluto medio (min) | 5,148 | **4,987** (MASE 0,969) |
| Cobertura del intervalo 80 % | 80,5 % (global) | **81,5 %** |
| Pérdida de cuantil (pinball) media | 1,668 | **1,598** (−4,2 %) |

Por tramo de minutos esperados, el modelo mantiene la cobertura entre 80,5 % y 82,5 % en los tres; la línea base con un
único intervalo global queda en 75,7 % (< 15), 77,4 % (15-25) y 85,4 % (≥ 25): confirma la ficha 58 (la dispersión crece
con los minutos esperados, pero relativamente menos).

**Compuertas del plan (G-props / G-disponibilidad, parte de minutos):** MASE ≤ 1,00 **cumple (0,969)**; cobertura del
rango 80 % en [77 %, 83 %] **cumple (81,5 %)**; probabilidades de jugar con Brier medido **cumplen** (mejor que cualquier
alternativa probada). La mejora de punto es real pero modesta (3 %): coincide con las fichas 10 y 47 (la media ingenua es
difícil de batir; el valor está en la distribución).

## 3. Lo que NO se ha hecho ni se debe asumir

* No se modelan compañeros ausentes (suben minutos, ficha 18) ni titular/banca, ni ventaja en el marcador (minutos de
  basura). Es la siguiente mejora esperable del error de minutos.
* No se condiciona la probabilidad de jugar al rol; para estrellas «Questionable» el 43 % es un promedio de toda la plantilla.
* La evaluación es solo de minutos; los props (puntos, rebotes...) llegan en el Sprint 4.
* Estos módulos (`distribucion`, `minutos`, `disponibilidad`) son biblioteca: no están desplegados ni conectados a ningún cron.
