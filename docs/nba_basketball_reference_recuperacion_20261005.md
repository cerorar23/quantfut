# Ampliación NBA mediante Basketball Reference — 2026-10-05

**Se recuperaron 159 partidos regulares pendientes y se incorporaron 3,317 registros de jugadores a una nueva versión de investigación.** La cobertura regular de las cinco temporadas aumenta de 5,830/6,150 a **5,989/6,150 (97.38%)**. El dataset ampliado contiene **157,375 filas**; las 154,058 filas del dataset anterior permanecen iguales y su archivo conserva el hash.

## Cobertura comprobada

| Temporada regular | Antes | Después | Pendientes |
| --- | ---: | ---: | ---: |
| 2021–22 | 1,171 | **1,230** | 0 |
| 2022–23 | 1,175 | **1,229** | 1 |
| 2023–24 | 1,159 | **1,205** | 25 |
| 2024–25 | 1,179 | 1,179 | 51 |
| 2025–26 | 1,146 | 1,146 | 84 |
| Total | 5,830 | **5,989** | **161** |

El censo conocido completo pasa de 395 a **236 pendientes**: 161 regulares, 71 de pretemporada, tres de playoffs y uno de play-in. Los calendarios de playoffs antiguos no se acreditan como completos. La temporada regular 2021–22 sí queda completa respecto al calendario de 1,230 partidos verificado.

## Captura y límite real

Se programaron las 263 fechas distintas de los pendientes regulares, playoffs y play-in en lotes de hasta veinte fechas. Se reutilizó el piloto del 2021-10-20 con su recepción y hash originales, y se mantuvieron al menos seis segundos entre solicitudes nuevas.

Se recibieron **140 páginas válidas**, incluyendo el piloto reutilizado. La solicitud del 2024-03-11 respondió **HTTP 403** después de siete lotes completos. El octavo se detuvo y las solicitudes posteriores no se ejecutaron. Se conserva el cuerpo de rechazo, su receipt y una parada compartida del proveedor. No se atribuye la causa del 403 a una política concreta del sitio ni se cambiaron IPs o se hicieron reintentos. Hay 141 receipts y aproximadamente 59.8 MB de páginas conservadas, incluida la respuesta denegada.

**Cero solicitudes/créditos de The Odds API en esta ampliación.** Tampoco se ejecutaron los proyectos de scrapers externos.

## Validación e identidad

El módulo `apps/nba/src/nba/basketball_reference.py` verifica el título/fecha, tabla, link del partido con equipo local, equipos/oponentes, IDs Basketball Reference, minutos y clave de segundos, y componentes de rebotes. Cruza cada jugador con la fila NBA del mismo partido y exige P/R/A concordantes.

Se permiten variantes únicas con acentos, puntos en iniciales y sufijos generacionales omitidos. Ambos nombres, IDs y método quedan registrados. Candidatos múltiples, generaciones contradictorias y apodos no se admiten. Todas las identidades nuevas se comprobaron como correspondencias consistentes entre partidos: **597 jugadores NBA distintos**, sin cambios de identidad entre IDs NBA/Basketball Reference.

Se mantienen los umbrales del validador existente: conciliación de minutos y estadísticas contra las referencias de ambos equipos. No se corrigen minutos inválidos por una regla de acarreo como `33:60 → 34:00`; el piloto muestra que Basketball Reference puede indicar `33:59`. El dataset nuevo incluye 3,316 observaciones con participación y una fila con `0:00` observado. Ausencia de la tabla no se convierte en DNP o lesión. No se fabrican filas de no participantes.

Cada fila nueva incluye URL, hash de página, recepción real, ID externo, ID NBA, nombres, minutos originales/reemplazos y hashes de las fuentes de identidad/equipos. Las filas heredadas conservan exactamente sus valores y su linaje queda vinculado al hash del archivo anterior.

La comprobación posterior volvió a parsear las **136 páginas utilizadas por los 159 partidos importados**, comparó todas las estadísticas nuevas con esas capturas y volvió a ejecutar la conciliación por partido. Se conservaron también dos versiones parciales: 34 partidos y 111 partidos recuperados. La versión final reúne el resultado de este intento, sin sustituir ninguna versión previa.

## Casos que permanecen separados

Dentro de las fechas recibidas se mantuvieron nueve partidos sin importar:

- Siete difieren en un rebote o una asistencia entre la referencia agregada y los jugadores de la página. Ejemplo: `0022200443`, OKC: referencia 54 rebotes frente a 53 en jugadores. No se ajustó el agregado para forzar aceptación.
- `0022300835` tiene referencias parciales de 42.75 minutos de juego; sus puntos y otras estadísticas tampoco coinciden con el resultado completo de la página. Necesita una referencia final corroborada independientemente.
- `0022300810` contiene una fila NBA de Thomas Bryant con minutos vacíos, estadísticas cero y comentario vacío. Su ausencia de la página no acredita no participación; no se asignó DNP para superar la validación.

Los otros 152 pendientes regulares no tienen una página válida recibida en este intento: uno coincide con el rechazo HTTP 403 y los demás quedaron después de la parada. Playoffs/play-in recientes tampoco alcanzaron su fecha de captura. La pretemporada necesita una fuente distinta porque este adaptador diario no acredita su cobertura.

Los detalles por equipo, diferencias y filas ausentes se conservan en `apps/nba/.local/reports/bref_remaining_diagnostics_20261005.json`.

## Archivos y reproducción

Versión ampliada:

- `apps/nba/.local/normalized/basketball_reference/expanded_20261005/player_games.jsonl.gz`
- `apps/nba/.local/normalized/basketball_reference/expanded_20261005/recovery.json`
- SHA256 del dataset: `b126df7535486198d7f36a2df218325c9a6e087009c4dd3077dcd9bea768c7e8`.
- QA final: `apps/nba/.local/reports/bref_dataset_final_verification_20261005.json`.
- Capturas: `apps/nba/.local/raw/basketball_reference/days/`.
- Control de descarga: `apps/nba/.local/reports/bref_download_progress_20261005.json`.

El README NBA documenta `capture-bref` y `recover-bref`. La segunda operación debe usar un directorio de salida nuevo. La parada del proveedor impide nuevos intentos automáticos; los archivos válidos ya capturados se pueden procesar offline.

## Comprobación del código y límites del resultado

**172 pruebas NBA y 609 pruebas del harness general aprobadas**, con una advertencia del harness y Docker no disponible. Se congelaron 39 archivos propios en `apps/nba/.local/code_snapshots/bref_expansion_v2_20261005/`. La descarga se inició con el capturador v1; la importación final usó v2 para las variantes de nombre. Ambos snapshots se conservan.

Una prueba nueva de colisión falló inicialmente porque el fixture usaba otro apellido; se corrigió el fixture y la suite completa pasó. El log fallido y los logs posteriores se conservan. La revisión comprende pruebas, hashes y QA de datos; no hubo revisor independiente. Los cambios concurrentes de fútbol ya existentes se preservaron y no forman parte del código NBA congelado.

Esta es una mejora de cobertura estadística retrospectiva. Las páginas recibidas en 2026 no acreditan recepción histórica original, lesiones prepartido o cuotas de apuestas. **El modelo no se reentrenó, no se activaron envíos/picks y todas las puertas comerciales siguen pendientes.** El siguiente trabajo de datos consiste en corroborar los nueve casos separados y recuperar las fechas posteriores cuando exista acceso válido o mediante otra fuente con segundos e identidades verificables.
