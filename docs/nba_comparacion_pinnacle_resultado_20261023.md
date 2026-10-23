# NBA — resultado de la comparación con Pinnacle (23-oct-2026)

Protocolo congelado antes de comprar precios: `apps/nba/nba_vs_market_protocol.json` (sha256 `1df12d71…`, sin cambios). Código: `nba.market_compare`. Salida: `apps/nba/.local/normalized/nba_f6_market_20261101/market_comparison.json`. Una sola ejecución. Retrospectivo y exploratorio; no genera apuestas ni picks.

## Veredicto del protocolo: **sin evidencia de información añadida**
La probabilidad de ganador de la v1.3 **no supera a Pinnacle sin margen** y su peso de información no es distinguible de cero. Es el resultado esperable en un mercado eficiente y es válido.

## Datos
- 325 snapshots de The Odds API (región `eu`, mercado `h2h`, Pinnacle), uno por día de partidos de 2024-25 y 2025-26, tomados 30 min antes del primer salto. Coste 3.250 créditos más 10 de una petición de diagnóstico cuya respuesta no se guardó (se volvió a comprar ese día).
- Cobertura: **98,8 %** (2024-25: 1.203 de 1.218 partidos con salto conocido) y **99,8 %** (2025-26: 1.195 de 1.197); el mínimo del protocolo era 85 %. Margen medio de Pinnacle 2,8 %; mediana de 104 min entre el precio y el salto.
- Los pocos partidos sin precio son partidos que nuestro histórico excluyó a propósito (los 42 con discrepancias de box score) o sin Pinnacle en su snapshot.

## Resultado (brazo principal «alineado»: el modelo solo ve información hasta la hora del precio)
| | 2024-25 | 2025-26 |
| --- | --- | --- |
| Brier modelo / mercado | 0,2039 / 0,2000 | 0,2006 / 0,1949 |
| Diferencia (modelo − mercado), IC95 por fechas | +0,0040 [−0,0013; +0,0089] | **+0,0057 [+0,0017; +0,0106]** |
| Log loss modelo / mercado | 0,5925 / 0,5831 | 0,5852 / 0,5707 |
| Peso de información *c* (0 = basta el mercado, 1 = basta el modelo) | 0,25 [−0,05; 0,57] | 0,09 [−0,23; 0,37] |
| Mezcla 50/50, diferencia frente al mercado | −0,0001 [−0,0025; +0,0022] | +0,0009 [−0,0010; +0,0032] |
| Correlación modelo-mercado | 0,91 | 0,92 |

- El mercado gana en las dos temporadas (significativamente en 2025-26). El brazo con la regla publicada (informes hasta T-60) da lo mismo (+0,0035 y +0,0059): alinear la información no cambió la conclusión.
- Peso con 2024-25 aplicado a 2025-26 (walk-forward): *c* = 0,25 y diferencia de la mezcla −0,0000 [−0,0010; +0,0011].
- Sensibilidad al método de quitar el margen (potencia en lugar de proporcional): idéntica (+0,0038 y +0,0058; *c* 0,28 y 0,12).
- **Cuando el modelo discrepa mucho, acierta el mercado.** En los partidos donde el modelo da al local ≥10 puntos más que Pinnacle (148 y 119 partidos), el modelo decía ~54 %, el mercado ~38-39 % y el local ganó el ~41 %. En las discrepancias a la baja pasa lo mismo (resultado ≈ mercado).
- La ventaja del mercado crece cuanto más cerca del salto está el precio (2025-26: 0,0108 de Brier en los snapshots a menos de 60 min del salto; 0,0026 a más de 3 h): Pinnacle incorpora información tardía (alineaciones y bajas confirmadas) que nuestros reportes no tienen.

## Qué significa
- El ganador NBA de la v1.3 es una versión más ruidosa del precio de Pinnacle: no hay base para venderlo como pick. Sirve como línea base: cualquier mejora futura del motor (ratings por rival y ritmo, prior de pretemporada) se mide ahora contra el Brier del mercado, 0,195-0,200.
- Lo que el modelo sí aporta: probabilidades razonables y bien calibradas (Brier 0,200-0,204), un marco de evaluación honesto y la infraestructura de prueba prospectiva (desde el 1-nov).

## ¿Queda completo el motor?
No. Esta compra cubre **solo el mercado de ganador** (moneyline) en 2024-25 y 2025-26.
- **Total del partido:** requiere otros ~3.250 créditos (mercado `totals`, mismas fechas). Con la renovación se puede comprar; el código y el protocolo ya existen para el ganador y habría que extenderlos.
- **Puntos de equipo:** `team_totals` existe como mercado adicional por evento (casas de EE. UU., no Pinnacle) con histórico desde mayo de 2023; cuesta 10 créditos por partido y snapshot (≈24.000 para las dos temporadas).
- **Jugadores (puntos, rebotes, asistencias, triples, robos, tapones):** **corrección del 23-oct:** la cifra de ~145.000 créditos (6 mercados × 2.415 partidos × 10) es correcta, pero la conclusión de «no viable» no: un mes del plan 5M de The Odds API cuesta $119 y cubre todo con margen, y no hace falta una lista verificada de jugadores (el mercado define el universo; el emparejado funcionó 17 de 17). Falta construir y correr la comparación, y es probable que el mercado gane. Detalle, coste y propuesta por fases en `docs/nba_props_jugadores_viabilidad_20261023.md`.
- **Prospectivo:** el paso de precios desplegado el 22-oct empieza a capturar el 1-nov y es la única prueba sin sesgo de selección.

## Créditos
Saldo antes 3.560 → después 294 (esta compra 3.260 incluyendo el diagnóstico; el resto, consumo normal de fútbol). **Fútbol necesita ~25-35 créditos al día entre semana y bastante más en fin de semana; con 294 se agotará en cerca de un día y su captura de cuotas en vivo quedará sin créditos hasta el reset del 1-nov.** Decisión del titular (opción 3), que renueva con más créditos para noviembre.

## Fallo corregido
La API exige la fecha en formato `YYYY-MM-DDTHH:MM:SSZ`; `nba.odds_history.fetch` enviaba `+00:00` y recibía HTTP 422 (`INVALID_HISTORICAL_TIMESTAMP`, sin coste). Corregido con `api_time` y una prueba que fija el formato. Las pruebas con cliente falso no podían detectarlo.
