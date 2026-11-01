# NBA — multimercado v1.4b (término absoluto + relativo, suelo de participación): sin mejora en equipo

Protocolo congelado antes de correr: `apps/nba/multimarket_v14b_protocol.json` (sha256 `577f203b…`, en `nba_f6_v14b_20261021/protocol_frozen.json`; el programa se niega a correr si cambia). Código: `nba.multimarket_v14b`. Resultados: `apps/nba/.local/normalized/nba_f6_v14b_20261021/comparison_v14b.json`. Todo retrospectivo, `actionable=false`; RUN071, v1.2-v1.4 y la cohorte en vivo no se tocaron. La variante de referencia reproduce `multimarket_v13` a 1e-12.

## Qué se probó
Hipótesis de v1.4: el término absoluto de v1.3 también medía la profundidad de plantilla lesionada. Candidato `both`: ambos términos (absoluto y relativo a la forma) + categoría G League + suelo de 0,02 en la probabilidad de jugar (fijado a priori). Ablaciones: solo absoluto con suelo y G League, y ambos términos sin suelo.

## Resultado (Brier frente a v1.3; negativo = mejor; IC95 por fechas)
| Mercado | 2024-25 | 2025-26 |
| --- | --- | --- |
| Ganador | −0,0000 [−0,0013; +0,0014] | +0,0004 [−0,0010; +0,0018] |
| Puntos de equipo | +0,0003 [−0,0003; +0,0012] | −0,0000 [−0,0007; +0,0007] |
| Total del partido | +0,0001 [−0,0003; +0,0006] | −0,0004 [−0,0012; +0,0005] |
| Puntos / rebotes / asistencias de jugador | −0,0013 / −0,0012 / −0,0008 | −0,0014 / −0,0012 / −0,0008 |
| Triples / robos / tapones | −0,0004 / −0,0003 / −0,0001 | −0,0004 / −0,0003 / −0,0001 |

- **Equipo: sin efecto.** Todas las diferencias son ~0 con intervalos que incluyen el cero. **No se cumple la regla de decisión** (límite superior ≤ 0 en ganador o puntos de equipo en ambas temporadas): v1.3 se queda.
- **Sin suelo o con suelo, igual** (`both_nofloor` ≈ `both`), y el término relativo no añade nada sobre el absoluto con suelo (`both` vs `abs_floor` dentro de ±0,0005, IC incluye 0). La hipótesis de la profundidad de plantilla no se sostiene con estos datos.
- **Jugadores:** idéntico a v1.4 (mejora pequeña y significativa en cinco de seis). Añadir el término absoluto no cambia nada.

## Participación: el suelo y la G League empeoran
Log loss de participación en las filas listadas (menor es mejor):

| | v1.3 | G League | G League + suelo |
| --- | --- | --- | --- |
| 2024-25, solo filas con box score | 0,491 | 0,502 | 0,504 |
| 2025-26, solo filas con box score | 0,447 | 0,524 | 0,523 |
| 2024-25, todas las listadas (sin box score = no jugó) | 0,180 | 0,183 | 0,192 |
| 2025-26, todas las listadas | 0,165 | 0,185 | 0,194 |

Diagnóstico posterior (fuera del protocolo, solo para entender): **mi explicación en la nota de v1.4 era incorrecta.** El problema no eran los «Out» por lesión sin suelo: realmente juegan el 0,7 % de las veces (4 de 614 en 2025-26), de modo que llevarlos a 0,02 *empeora* la verosimilitud. El suelo no se adopta (no mejora la participación en ninguna temporada). Tampoco mejora separar la G League, ni en la población con box score ni en la completa; por tanto la regla de adopción del suelo tampoco se cumple. De paso se confirma el desajuste de poblaciones que señaló la auditoría: de 11.547 filas listadas en 2025-26 solo 3.096 tienen box score, y `play_table` cuenta las demás como «no jugó» mientras `availability_scores` las salta.

## Conclusión
La información de lesiones del reporte oficial ya aporta lo que puede aportar a los mercados de equipo con la versión v1.3: reponderar o separar sus términos no mueve el Brier. Descartada esta línea; el esfuerzo debe ir a lo que la auditoría marcó con más margen y que no es esta tabla: ratings ajustados por rival y ritmo, prior de pretemporada, reportes cercanos a T-60 y, sobre todo, las cuotas para comparar con el mercado.

## Límites
Exploratorio (temporadas ya vistas con v1.1-v1.4), 9 mercados × 4 variantes sin corrección por comparaciones múltiples, un reporte por día en el histórico, sin cuotas ni CLV.
