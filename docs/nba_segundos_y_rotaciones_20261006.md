# NBA: segundos oficiales y rotaciones — 6 de octubre de 2026

**Boxscores: 6.150/6.150 regulares y 71/71 pretemporadas; 164.218 filas. Rotaciones: 6.141/6.150; quedan nueve.** Este cierre corresponde al censo de investigación de 2021–22 a 2025–26, con pretemporada 2025–26; no acredita toda la historia de la NBA.

| Datos | NBA-RUN-039 | NBA-RUN-040 |
|---|---:|---:|
| Boxscores regulares | 6.149 | 6.150 |
| Filas de jugadores, incluido DNP explícito | 164.190 | 164.218 |
| Boxscores de pretemporada | 71 | 71 |
| Rotaciones regulares aceptadas | 6.113 | 6.141 |
| Tramos cronológicos por equipo | 258.137 | 259.416 |
| Rotaciones pendientes | 37 | 9 |

## Tony Bradley y precisión de minutos

0022400942 (11-mar-2025) devuelve 0:00 y un rebote para Tony Bradley, ID1628396. GameRotation acredita **0,2 segundos** positivos, intervalos en décimas [14398,14400], más un intercambio administrativo [28761,28761] sin tiempo transcurrido. Se incorporó el roster completo de 28 filas en una nueva versión, conservando `minutes_raw="0:00"`, `reported_minutes=0`, estadísticas, hash y prueba de intervalos. El valor normalizado es 0,2/60 minutos.

El normalizador admite ahora fuentes oficiales verificadas mediante `subsecond_sources`, opcional y vacío por defecto. Valida todo el partido: dos equipos, IDs y nombres, intervalos y puntos, cinco jugadores durante todo el tiempo positivo, y coherencia de minutos individuales. Solo permite un segundo o menos con reloj cero y estado vacío; rechaza DNP, hashes incorrectos, overlaps, gaps y fuentes contradictorias. PRA positivos no se usan para inferir participación. Se comparó la ruta por defecto con la versión anterior archivada en las 164.190 filas previas: resultados y auditoría idénticos. Los originales sellados permanecen intactos.

## Rotaciones recuperadas y límites

Se añadieron **28 partidos** con continuidad por período, cinco IDs únicos de cada equipo, minutos individuales y comparación de quintetos/eventos. Los stints publicados de Ramiro, PBP originales CDN/V2/V3 e intervalos oficiales se usan según su disponibilidad. Pueden compartir origen NBA; no se presentan como proveedores independientes.

La auditoría de cancha con pbpstats omite coordenadas de tiro y emparejamiento de rebotes/posesiones, para evitar consultas auxiliares y reordenaciones ajenas a las rotaciones. El código de titulares y sustituciones de la librería permanece intacto; los controles externos verifican orden original, períodos, minutos y quintetos. Los estados intermedios de sustituciones sin avance del reloj se conservan en las fuentes; solo las alineaciones que cubren tiempo positivo deben cumplir los controles de cancha. Las parejas administrativas de Ramiro excluidas de una copia de comparación tienen cero tiempo, cero puntos y respaldo explícito de intervalos oficiales; se conserva cada fila original y su mapa de índices.

ZenRows recuperó seis GameRotation útiles de 16 solicitudes alternativas y 17/17 PBP oficiales V3 actuales. La primera comprobación de PBP esperaba `resource/parameters` y registró KeyError: esos originales se conservaron. La revisión posterior verificó el formato `meta/game.gameId/game.actions` contra el parser instalado de nba_api. `actionId` identifica filas únicas; `actionNumber` puede repetirse para acciones relacionadas y no se deduplicó. Se hizo una proyección a strings únicamente para el replay CSV existente, manteniendo los valores originales en los bytes capturados.

Las abreviaturas de sustitución se vinculan a IDs explícitos cuando V2 y V3 coinciden exactamente en descripción, número de acción, período e ID saliente, con reloj a un segundo como máximo. El entrante tiene ID explícito V2 del mismo roster/equipo. Un alias de identidad no acredita participación ni fuerza titulares. El replay prueba los quintetos iniciales a partir de eventos y sustituciones originales antes de compararlos con los stints; no se copian titulares de Ramiro.

**Pendientes:** 0022100074, 0022100151, 0022100353, 0022200793, 0022201007, 0022201040, 0022201205, 0022400831, 0022401211. Los diagnósticos conservan los eventos, razones y tracebacks de cada intento. Hay intercambios administrativos/actores con reloj cero o participación contradictoria, y cuatro partidos con prórroga donde los eventos no acreditan cinco titulares. En 0022201040 también hay intervalos oficiales superpuestos. No se rellenan segundos ni jugadores iniciales para cerrar el contador.

## Costes, pruebas y preservación

Se consumieron **245 créditos confirmados nuevos**: 75 de GameRotation y 170 de PBP. La suma conservadora con las reservas previas por cargos inciertos es **1.612/3.200** créditos. Uso de cuenta observado al cerrar la captura: 1304/5000, no saldo en tiempo real. Sin compras ni nuevas llamadas a props. La instalación de ZenRows MCP no redirige por sí sola todos los scrapers; esta captura pasó explícitamente por el transporte del proveedor.

**189 pruebas NBA y 707 del arnés general pasaron**. Se conserva el primer fallo de la suite NBA, un PermissionError de Windows en reemplazo de un archivo temporal; la repetición completa pasó sin cambios de código. Los 17 casos nuevos de prueba cubren subsegundos y rechazo de fuentes/identidades/DNP/estadísticas inválidas. Seis controles adicionales de dataset rechazan IDs falsos, duplicados, seis jugadores, gaps, equipo incorrecto y DNP en cancha.

Se preservan exactamente las 164.190 filas y 6.113 rotaciones previas, las **2.105 evidencias selladas anteriores** y 38 de los 39 archivos del manifiesto antiguo. El único archivo existente modificado es `ingest.py`, con su versión original archivada; se añadieron `participation.py` y sus pruebas. Las versiones intermedias y fallidas de investigación se conservan. Los auxiliares iterados se archivan en su versión final, sin atribuir retrospectivamente ese hash a cada ejecución intermedia.

## Artefactos y siguientes pendientes

- Boxscores aceptados: `apps/nba/.local/normalized/nba_subsecond_20261006/player_games.jsonl.gz`.
- Rotaciones aceptadas: `apps/nba/.local/normalized/nba_pending_rotations_v6_20261006/combined_games.jsonl.gz`.
- Cobertura, verificación y pendientes: `apps/nba/.local/normalized/nba_subsecond_rotation_validation_20261006/`.
- Fuentes actuales: `apps/nba/.local/raw/nba_pending_20261006/`.
- Eventos concretos rechazados: `apps/nba/.local/reports/nba_remaining_v3_diagnostics_20261006.log`.

Para los nueve juegos restantes hace falta corroborar los intercambios finales sin tiempo positivo y conseguir prueba oficial de titulares por período para los casos ambiguos; los clocks originales siguen siendo la referencia. Los 816 reportes médicos diarios y 3.756 pares de props del cierre anterior no se ampliaron. Siguen pendientes intradía médico completo, recepción histórica prepartido, props multitemporada y reglas de liquidación antes del backtest. Los datos recuperados son investigación retrospectiva; no se promovieron gates, entrenamiento, modelo o picks. Registro local NBA-RUN-040, auto revisión, sin revisor independiente ni anclaje externo.
