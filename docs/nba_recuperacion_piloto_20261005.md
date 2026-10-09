# Recuperación gratuita NBA: inventario, rotaciones y lesiones — 2026-10-05

Se implementaron capturas acotadas y auditorías independientes en NBA. **El piloto recuperó tres PDF oficiales de lesiones. No recuperó nuevos boxscores o rotaciones**, porque stats.nba.com agotó el tiempo de espera; el archivo CDN consultado respondió 403. Ninguna consulta utilizó The Odds API.

## Censo exacto de pendientes

El archivo `apps/nba/.local/reports/backfill_inventory_20261005.json` contiene IDs, fechas, equipos, filas presentes, fallos de conciliación y valores de minutos originales. Reproduce el validador existente por partido, sin reparar valores o sustituir el dataset aceptado.

| Tipo | Pendientes de las referencias conocidas |
| --- | ---: |
| Temporada regular, 2021–22 a 2025–26 | 320 |
| Pretemporada 2025–26 | 71 |
| Playoffs 2025–26 | 3 |
| Play-in 2025–26 | 1 |
| Total | 395 |

En 299 partidos regulares hay al menos un valor de minutos inválido. Se observan valores como `30:60`; no se convierten en `31:00` sin corroboración independiente. Los siete partidos con referencias de equipos inválidas ya tienen IDs: `0022300835`, `0022500050`, `0022500243`, `0022500720`, `0022500784`, `0022500876`, `0022501030`. Ejemplos de duración de equipo no admitida: 42.75 o 47.983333 minutos. Los problemas no se atribuyen automáticamente a nombres o a falta de identificadores.

Este censo no acredita el calendario completo de playoffs de temporadas anteriores, ni incluye All-Star como objetivo de entrenamiento. El dataset previo conserva 154,058 filas y el mismo hash; no se incorporó ningún partido rechazado.

## Captura y validación implementadas

- `backfill-inventory`: carga manifiestos verificados y el hash del dataset base; crea un nuevo inventario sin sobrescribir evidencia.
- `capture-backfill`: hasta 20 IDs distintos por lote, endpoints oficiales de boxscore V3 o GameRotation, tope de 8 MB por respuesta y parada ante cualquier fallo. Reutiliza capturas comprobadas y no reintenta un lote detenido.
- `audit_boxscore`: exige dos referencias fechadas, IDs concordantes y estadísticas de equipos coincidentes; aplica la conciliación existente de jugadores, minutos, puntos, rebotes y asistencias. Ningún umbral se relajó.
- `audit_stints`: determina unidades del reloj solo si una escala concilia con el boxscore; exige cinco jugadores distintos en cada intervalo, sin huecos/solapamientos, y valida prórrogas. Tiene pruebas controladas; no se recibió un ejemplo real de GameRotation para acreditar cobertura operativa.
- `capture-injury-reports`: hasta diez URL canónicas oficiales por lote, archivos originales con hash/recepción y parada ante error.
- `nba.injury_pdf`: parser opcional del layout de siete columnas, ejecutado con el runtime PDF de escritorio. Conserva contexto entre páginas, estados desconocidos y equipos no entregados. Usa ET/UTC con `tzdata==2026.3`, instalado únicamente en NBA; no se instaló nbainjuries o Java.

Las instrucciones de ejecución están en `apps/nba/README.md`. Los capturadores no importan automáticamente sus respuestas al dataset aceptado o al modelo. La integración médica y el cruce de IDs continúan pendientes.

## PDF históricos recibidos y verificados

Se renderizaron y revisaron visualmente las ocho páginas de estos reportes del 2025-04-25:

| Etiqueta de URL | Encabezado verificado, ET | UTC | Jugadores nombrados | Equipos no entregados |
| --- | --- | --- | ---: | ---: |
| `05PM` | 17:30 | 21:30 | 25 | 3 |
| `06PM` | 18:30 | 22:30 | 29 | 2 |
| `07PM` | 19:30 | 23:30 | 30 | 2 |

Los tres reportes aportan 84 observaciones de jugadores y 30 entidades distintas, todavía sin IDs NBA verificados. Se comprobaron cuatro cambios de estado entre los dos primeros reportes, incluido Questionable → Out. No se extrapola esa cobertura a otras fechas o layouts.

La prueba de selección con corte `2025-04-25T22:00:00Z` elige, en investigación retrospectiva, el documento cuyo encabezado es 21:30 UTC. El PDF etiquetado `06PM` contiene hora 22:30 UTC y queda fuera; usar la etiqueta como publicación habría permitido información futura. En modo prospectivo ningún documento capturado en 2026 se considera recibido en ese corte de 2025. El encabezado es una hora declarada del documento; la recepción histórica original y sus posibles revisiones no están acreditadas.

Se conservan `NOT YET SUBMITTED` y relojes de partido sin AM/PM como información incompleta. No se deduce elegibilidad individual a partir de la ausencia de un jugador o de un reporte. Los cruces con partidos, plantillas históricas y horarios de inicio necesitan verificación independiente antes de usar lesiones como variables del modelo.

## Evidencia y validación

Inventario: `apps/nba/.local/reports/backfill_inventory_20261005.json`. Comparación temporal de lesiones: `apps/nba/.local/reports/injury_pilot_comparison_20261005.json`. Capturas: `apps/nba/.local/raw/backfill_pilot/20261005T224827/`, `apps/nba/.local/raw/injury_reports/2e9dca8d4b528fdcd80904015587fee97a35d1bdec20bae30e099e2868e07298/` y el manifiesto GameRotation en `apps/nba/.local/raw/official_backfill/`.

Pasan **136 pruebas NBA** y **609 pruebas del harness general**, con una advertencia del harness y Docker no disponible. El harness inicial aprobó 606; durante esta tarea aparecieron cambios concurrentes de fútbol y tres pruebas adicionales, ajenos a los archivos NBA editados. No se atribuyen esos cambios a esta implementación. La revisión propia comprende pruebas, integridad de archivos y QA visual; no hubo revisor independiente.

**Cero créditos de The Odds API, cero nuevos partidos importados, modelo sin reentrenar y todas las puertas de validación pendientes.** Próximos pasos: fuente accesible para sustituir los 320 boxscores, ampliación controlada de layouts/fechas de lesiones y cruce temporal de partidos/IDs; las rotaciones requieren una respuesta real y su validación antes de ampliar el lote.
