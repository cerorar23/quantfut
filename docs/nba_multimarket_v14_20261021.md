# NBA — multimercado v1.4 (doble conteo de bajas y G League): no mejora los mercados de equipo

Protocolo congelado antes de correr: `apps/nba/multimarket_v14_protocol.json` (sha256 `54a622d2…`, registrado en `nba_f6_v14_20261021/protocol_frozen.json`; el programa se niega a correr si cambia). Código: `nba.multimarket_v14`. Resultados: `apps/nba/.local/normalized/nba_f6_v14_20261021/comparison_v14.json`. RUN071, v1.2, v1.3 y la cohorte en vivo no se tocaron; todo es retrospectivo y `actionable=false`. El programa comprueba antes de comparar que su variante «v1.3» reproduce `multimarket_v13` al decimal 1e-12.

## Qué se probó
- **Arreglo 1 (relativo a la forma):** puntos/minutos perdidos = valor del jugador × (fracción de los últimos 20 partidos del equipo que jugó − probabilidad de jugar hoy). Una baja que ya estaba en la forma aporta ~0; un regreso aporta valor negativo.
- **Arreglo 2 (G League):** las filas con motivo «G League» (Two-Way / On Assignment) forman una categoría propia, sea cual sea su estado.
- Se corrieron además cada arreglo por separado, para saber cuál mueve qué.

## Resultado (diferencia de Brier frente a v1.3; negativo = mejor; IC95 por fechas)
| Mercado | 2024-25 | 2025-26 |
| --- | --- | --- |
| Ganador | +0,0005 [−0,0015; +0,0026] | +0,0007 [−0,0017; +0,0034] |
| Puntos de equipo | +0,0008 [−0,0002; +0,0019] | +0,0006 [−0,0007; +0,0021] |
| Total del partido | −0,0002 [−0,0010; +0,0006] | −0,0005 [−0,0017; +0,0006] |
| Puntos de jugador | −0,0013 [−0,0017; −0,0010] | −0,0014 [−0,0021; −0,0009] |
| Rebotes / asistencias / triples | −0,0012 / −0,0008 / −0,0005 | −0,0011 / −0,0008 / −0,0004 |
| Robos / tapones | −0,0003 / −0,0001 | −0,0003 / −0,0001 |

Por arreglo: el **arreglo 2 es neutro en todo** (|Δ| ≤ 0,0001). Toda la diferencia viene del **arreglo 1**.

## Lectura
- **El diagnóstico del doble conteo era correcto en el mecanismo:** la masa media de puntos perdidos por partido baja de 32-36 a 13 y los coeficientes del ganador crecen un 50-70 % (−0,10/+0,06 → −0,16/+0,14 por cada 10 puntos; en puntos de equipo, −0,58 → −0,89 y −0,67 → −1,06).
- **Pero no mejora la predicción de equipo:** ganador y puntos de equipo quedan ligeramente peores (no significativo) y el total apenas mejora (no significativo). **Regla de decisión del protocolo** (cota superior del IC ≤ +0,0005 en ganador y puntos de equipo, ambas temporadas): **no se cumple**, así que los arreglos no se adoptan para los mercados de equipo y el modo en vivo sigue en v1.3.
- **Los mercados de jugador sí mejoran de forma significativa** con el arreglo 1 (−0,0003 a −0,0014 en cinco de seis; tapones −0,0001, IC en el borde). Es pequeño, pero consistente en las dos temporadas. Los jugadores no se sellan en vivo (no hay lista verificada de quién juega).
- **Hipótesis (no probada):** el término absoluto de v1.3 funcionaba además como indicador de profundidad de plantilla lesionada, información que el Elo y la forma captan con retraso; al restarle lo ya incorporado se pierde esa señal. Habría que probar un modelo con ambos términos (absoluto y relativo) para separarlas.
- **La verosimilitud de participación empeora** (0,49 → 0,50 en 2024-25; 0,45 → 0,52 en 2025-26). Corrección posterior (v1.4b): la causa no son los «Out» por lesión sin suelo —juegan solo el 0,7 % de las veces y un suelo empeora la medida—, sino la propia separación de G League, que no mejora la participación en ninguna población. Ver docs/nba_multimarket_v14b_20261021.md.
- «Available» sube de 0,69-0,75 a 0,77-0,81 al sacar la G League, y G League queda en 0,03-0,04: la mezcla que señalaba la auditoría existía, pero apenas afectaba a las predicciones.

## Límites
Exploratorio: las temporadas ya se inspeccionaron con v1.1-v1.3 y no se corrige por comparaciones múltiples (9 mercados × 3 variantes). Un reporte por día en el histórico (13:30 o 17:30 ET). Sin cuotas ni CLV.

## Qué sigue
1. Probar absoluto + relativo juntos en equipo antes de descartar la idea.
2. Ponerle suelo a la tabla de participación (p. ej. Beta(1,1) → previo informativo por categoría).
3. Dejar los mercados de equipo en v1.3 y concentrar el esfuerzo donde la auditoría marcó más margen: reportes cercanos a T-60, ratings ajustados por rival y prior de pretemporada.
