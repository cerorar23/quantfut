# NBA: recuperación médica y cuotas — 7 de octubre de 2026

**2,784 reportes médicos nuevos y 1.350 pares adicionales de precios de puntos.** Se corroboraron horarios para los 6.150 partidos regulares del censo 2021–22 a 2025–26 y se construyó una selección médica retrospectiva a T−60. Los datos conservan las restricciones de recepción histórica y liquidación; no se promovieron modelos ni picks.

| Datos | Antes | NBA-RUN-043 |
|---|---:|---:|
| Reportes médicos | 1.841 | 4,625 |
| Filas médicas | 186.634 | 555,536 |
| Pares de precios con controles de cronología completos | 232.080 | 233.430 |
| Pares candidatos con cronología incompleta, separados | 0 | 27.151 |

Los boxscores y rotaciones regulares permanecen en 6.150/6.150. El conjunto de boxscores conserva 164.218 filas y la cobertura parcial anterior de pretemporada/playoffs/play-in/Cup. Esta corrida no amplía ese censo ni acredita toda la historia NBA.

## Reportes médicos y selección T−60

Se fijaron y verificaron por hash los calendarios ESPN 2022 y 2023 de [sportsdataverse-data](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_nba_player_boxscores), junto con los archivos 2024–2026 ya conservados. La unión normal verifica fecha y localía NBA independientes. En diez partidos, la referencia NBA marca ambos equipos como visitantes: se conserva esa anomalía de sede neutral y se acepta solamente la fecha y el par de equipos exactos, con designación home/away de ESPN. No se afirma localía física ni hora del salto inicial.

El inventario principal tiene 3.221 URLs nominales anteriores a T−60 para 6.140 partidos; la elegibilidad real exige comprobar el encabezado. Reutiliza 444 PDFs anteriores. También se recuperaron 97 PDFs originales del archivo [NBA_AI_Player_Analysis](https://github.com/Torgo28/NBA_AI_Player_Analysis/tree/7a0dc8da4d0097337e18544294900756c85d2d58), con blobs Git verificados; 95 rutas son adicionales al inventario. De esos archivos adicionales, 93 ya estaban en el conjunto previo con idéntico hash: se conserva su recibo nuevo sin contarlos como reportes nuevos ni cambiar los registros anteriores. No se adoptan las etiquetas procesadas ni modelos de ese repositorio. La captura directa aplica un máximo de 3.000 solicitudes y una solicitud por segundo; se efectuaron 2,795, sin transporte pagado.

Cada PDF nuevo exige encabezados coherentes entre páginas, fecha compatible con su nombre, lectura por coordenadas y acuerdo independiente de entidades, estados y equipos no enviados con el parser de mrees002. Las diferencias literales de motivos se conservan. En páginas finales de una fila se exige acuerdo de motivo, con excepciones acreditadas por límites de fila y continuaciones de página ligados al hash original. Se repararon once lecturas: equipo explícito en la última fila, motivo que continúa desde la página anterior o folio que contiene solo la continuación de un motivo. Se conservan los errores y desacuerdos originales; no se cambian los datos sellados anteriores. Los nombres requieren prueba oficial de ID y se preserva el literal del PDF. Nuevas filas nominales: 353,592; con ID NBA: 353,592. Nombres sin resolver: 0.

Hay reportes elegibles y contextos/horarios concordantes para **6,129/6.150 partidos**; faltan 21. De los seleccionados, 6037 tienen ambos equipos enviados y 0 conservan algún `NOT YET SUBMITTED`; 92 contienen algún equipo no listado, con estado explícitamente desconocido. Estas dos últimas categorías pueden solaparse. La ausencia no se interpreta como equipo sano o enviado. Que exista un reporte no equivale a tener disponibilidad nominal completa. Se elige la última versión capturada cuyo encabezado sea ≤T−60, con fecha, equipos presentes, matchup y reloj ET del partido concordantes. Los diez partidos neutrales se resuelven por su par exacto, sin modificar registros anteriores.

La recepción acreditada es la actual, en octubre de 2026. No prueba que el pipeline original dispusiera del PDF antes del partido. `original_historical_receipt_known=False`, `pregame_availability_verified=False`, `actionable=False`. No se recuperaron todas las versiones intradía de cada fecha.

Los pendientes T−60 son veinte discrepancias de reloj literal frente a ESPN y un partido no presente en los reportes capturados. Dos consultas directas al boxscore JSON de NBA CDN respondieron 403 y no aportaron prueba de horario; los originales/respuestas se conservan. Sumadas a los PDFs, hubo 2,797 solicitudes directas, todavía dentro de 3.000. Las dos pruebas CDN se hicieron secuencialmente sin la pausa de un segundo aplicada por los capturadores PDF. No se concluye por esos errores que exista un bloqueo general de IP. Las rutas con minutos explícitos de algunos alias antiguos tampoco estaban disponibles; se mantienen la hora literal y el corte conservador.

## Cuotas recuperadas con alias explícitos

Se revisaron 1.585 snapshots ya sellados de [NBA-Propositions-Forecasting-App](https://github.com/KamranSHussain/NBA-Propositions-Forecasting-App/tree/a95be8924f3c4fe08b44dcfd940269610ca49501). Se recuperaron 1.350 pares de puntos para 308 partidos mediante alias de nombre completo explícitamente vinculados al mismo ID NBA: Nicolas/Nic Claxton, Carlton/Bub Carrington, Mohamed/Mo Bamba, Cameron/Cam Reddish y dos variantes de capitalización. Cada alias conserva sus pruebas oficiales y debe corresponder al ID y nombre canónico del mismo partido. No se usan apellidos aislados, abreviaciones supuestas ni estadísticas.

Se mantienen los controles originales: reloj de casa y mercado ≤snapshot, vecinos ordenados, snapshot anterior a ambos horarios de inicio, par Over/Under exacto, línea válida y precio decimal finito. Los 232.080 pares previos se preservan exactamente. El total es 233.430: 230.277 puntos, 2.961 rebotes y 192 asistencias. Los horizontes siguen siendo los reales del archivo; estas cuotas no se presentan como cortes prescritos T−60/T−15.

## Archivo multimercado en cuarentena

El commit [73892a6d de NBA-Betting](https://github.com/mostgood1/NBA-Betting/tree/73892a6daba2a9a67d4baf8691a106a2f67a9ca6) contiene seis CSV de props: 70.973 filas y seis snapshots. Se obtuvieron 27.151 pares candidatos, con identidad y evento/fecha/localía/horario corroborados, para 34 partidos y ocho casas. Sus horizontes son 24.97–602.13 minutos. Su exportación usa `market.last_update or bookmaker.last_update`: no permite acreditar por separado ambos relojes ni los vecinos del snapshot. Se conservan `book_update_utc=None`, `market_update_utc=None`, `strict_chronology_eligible=False` y `actionable=False`. Estos candidatos **no se suman** a los 233.430 pares validados.

| Mercado | Pares candidatos |
|---|---:|
| player_assists | 2,267 |
| player_blocks | 420 |
| player_points | 5,641 |
| player_points_assists | 2,605 |
| player_points_rebounds | 3,596 |
| player_points_rebounds_assists | 5,132 |
| player_rebounds | 3,019 |
| player_rebounds_assists | 1,743 |
| player_steals | 208 |
| player_threes | 2,500 |
| player_turnovers | 20 |

Se conservan los rechazos por precios posteriores al inicio, actualización posterior al snapshot, pares incompletos/conflictivos e identidad no resoluble. [PP_Research_Tool](https://github.com/cgpropz/PP_Research_Tool), [nba-props-app](https://github.com/ANickFlower/nba-props-app) y [nba-main](https://github.com/Gen3ratorX/nba-main) quedan documentados: faltan relojes de captura/inicio, pares completos o se trata de cuotas de partido en lugar de props. Las fechas de archivo no sustituyen una hora de captura.

## Validación y límites

Se verificaron las 9.641 evidencias, 42 corridas y 91 eventos previos; los datos sellados se preservan exactamente. Sin cambios de producción NBA: 38 archivos conservan el manifiesto original y `ingest.py` mantiene el cambio previamente autorizado de RUN-040. El arnés pasó 732 pruebas antes y 732 después; los cambios concurrentes de fútbol/web se preservaron. Se ejecutaron 19 controles de alias, cronología, contexto y aislamiento. Se conservaron fallos de ejecución y versiones finales de auxiliares; auto revisión local, sin revisor independiente ni anclaje externo.

**Cero llamadas nuevas a Odds API o ZenRows.** Odds API conserva el límite 500 agotado; los 720 créditos adicionales propuestos no fueron autorizados ni utilizados. ZenRows conserva el riesgo presupuestado previo de 1.782/3.200; no representa una lectura actual del saldo. No se realizaron compras ni cambios de plan.

## Artefactos y pendientes

- Datos médicos: `apps/nba/.local/normalized/nba_pending43_medical_final_20261007/reports.jsonl.gz`.
- Selección médica: `apps/nba/.local/normalized/nba_pending43_medical_final_20261007/retrospective_T60_selection.json`.
- Cuotas con controles completos: `apps/nba/.local/normalized/nba_pending43_props_verified_20261007/quotes.jsonl.gz`.
- Candidatos separados: `apps/nba/.local/normalized/nba_pending43_props_candidates_20261007/candidate_pairs.jsonl.gz`.
- Originales/recibos: `apps/nba/.local/raw/nba_pending43_20261007/`.
- Auditoría: `apps/nba/.local/normalized/nba_pending43_validation_20261007/`.

Restan los huecos médicos indicados, versiones intradía adicionales, props históricos de rebotes/asistencias y cortes prescritos a escala, relojes faltantes del nuevo archivo, recepción histórica original y reglas de liquidación por casa/fecha/jurisdicción. Ninguno se considera resuelto por instalar un scraper o un proxy.
