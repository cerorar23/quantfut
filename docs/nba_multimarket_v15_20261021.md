# NBA — multimercado v1.5: reportes a T-60 en la v1.3 (mejora los jugadores, no se prueba efecto en equipo)

Protocolo congelado antes de correr: `apps/nba/multimarket_v15_protocol.json` (sha256 `4fe8773a…`, en `nba_f6_v15_20261021/protocol_frozen.json`; el programa se niega a correr si cambia). Código: `nba.multimarket_v15`. Resultados: `apps/nba/.local/normalized/nba_f6_v15_20261021/comparison_v15.json`. Es exactamente el código v1.3: **solo cambian los reportes**. La referencia reproduce el Brier publicado de v1.3 a 1e-9 en todos los mercados y temporadas (si no, el programa aborta). Retrospectivo, `actionable=false`; RUN071, v1.2-v1.4b y la cohorte en vivo no se tocaron.

## Qué se comparó
- **Referencia:** v1.3 con los 816 reportes originales (uno por día, 13:30 o 17:30 ET).
- **Candidato:** el mismo v1.3 con esos 816 + los 1.910 reportes T-60 de `docs/nba_cache_completed_y_backfill_t60_20261021.md` (el último válido ≥60 min antes del salto gana). Entrena y evalúa con ellos.
- 2025-26 es la temporada **primaria** (sus dos temporadas de entrenamiento están completas en T-60). 2024-25 es secundaria: su entrenamiento incluye 2022-23, que sigue con reportes antiguos.

## Resultado (Brier; diferencia candidato − referencia, negativo = mejor; IC95 por fechas)
| Mercado | 2024-25 | 2025-26 |
| --- | --- | --- |
| Ganador | +0,0003 [−0,0018; +0,0022] | −0,0004 [−0,0023; +0,0015] |
| Puntos de equipo | **−0,0013 [−0,0025; −0,0001]** | −0,0006 [−0,0016; +0,0005] |
| Total del partido | −0,0001 [−0,0009; +0,0007] | +0,0002 [−0,0007; +0,0012] |
| Puntos de jugador | **−0,0019 [−0,0030; −0,0011]** | **−0,0022 [−0,0028; −0,0017]** |
| Rebotes | **−0,0014** | **−0,0011** |
| Asistencias | **−0,0015** | **−0,0011** |
| Triples | **−0,0009** | **−0,0007** |
| Robos | **−0,0003** | **−0,0004** |
| Tapones | +0,0000 | −0,0001 (IC en el borde) |

(En negrita, el IC excluye 0.) Participación (log loss sobre las mismas filas listadas con box score): **0,491 → 0,383** en 2024-25 y **0,447 → 0,314** en 2025-26. La tabla se afila: «Out» 0,4 % → 0,1-0,2 %, «Doubtful» 2,5-3,3 % → 1,5-1,7 %, «Available» 69-75 % → 76-81 %.

## Regla de decisión (fijada antes de correr)
Adoptar los reportes T-60 para el entrenamiento del modelo vivo si, en 2025-26, el límite superior del IC ≤ 0 en ganador o puntos de equipo, **y** ningún mercado de equipo supera +0,0010 de límite superior en ninguna temporada.
- Primera condición: 2025-26 ganador +0,0015 y puntos de equipo +0,0005 → **no se cumple**.
- Segunda: ganador +0,0022 / +0,0015 y total +0,0012 superan +0,0010 → **no se cumple**.
- **Veredicto del protocolo: los mercados de equipo del modelo vivo conservan sus reportes actuales.** Los de jugador son informativos, no decisivos.

## Lectura
- El efecto es real donde la tabla de participación actúa directamente: la verosimilitud de participación mejora ~25-30 % y los seis mercados de jugador mejoran de forma significativa en las dos temporadas (puntos −0,002; más que cualquier arreglo anterior).
- En equipo la mejora es pequeña y ruidosa: puntos de equipo mejora (significativa en 2024-25), el ganador no se mueve. Con ~1.200 partidos por temporada el IC del ganador es de ±0,002, así que **no se puede descartar** una mejora de 0,001: es ausencia de evidencia, no evidencia de ausencia. Los pesos de los términos de bajas casi no cambian (−0,11/+0,08 en ganador), es decir, el efecto de equipo ya estaba capturado por el modelo y la fuente, no por la antigüedad del reporte.
- Desplazamiento: el sesgo de los mercados de jugador sube ~+1 punto (p. ej. puntos +0,001 → +0,012); mejora el Brier pero la calibración queda ligeramente alta. Conviene recalibrar si se usan.
- Argumento aparte (fuera de la regla): el modelo vivo **sirve** estados a T-60, por lo que entrenarlo con estados del mismo tipo es coherente; la regla de decisión pide evidencia en equipo y no la hay. Es una decisión del titular, no de este protocolo.

## Límites
Exploratorio (temporadas ya vistas con v1.1-v1.4b); 9 mercados × 2 temporadas sin corrección por comparaciones múltiples; 2022-23 sin T-60; recepción retrospectiva de los reportes; sin cuotas ni CLV.

## Qué sigue
Los mercados de equipo no se mueven por la calidad del reporte: lo que queda con margen es el ajuste por rival y ritmo, el prior de pretemporada y, sobre todo, las cuotas (desde el 1-nov) para saber si el modelo supera al mercado. Los mercados de jugador, si se publican algún día, deberían usar T-60 y recalibrarse.
