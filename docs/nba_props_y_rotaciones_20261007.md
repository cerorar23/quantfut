# NBA: cuotas históricas públicas y rotaciones — 7 de octubre de 2026

**6.150/6.150 rotaciones regulares validadas; 228.324 pares nuevos de precios de puntos para 3.429 partidos; 210 PDF s médicos nuevos.** Los datos anteriores se preservan exactamente. Esta corrida completa las rotaciones del censo 2021–22 a 2025–26 y amplía el archivo de investigación; no acredita toda la historia NBA, disponibilidad prepartido original ni reglas de liquidación para un backtest.

| Datos | Antes | NBA-RUN-042 |
|---|---:|---:|
| Rotaciones regulares | 6.147 | 6.150 |
| Tramos por equipo | 259.687 | 259,826 |
| Pares de precios de props | 3.756 | 232,080 |
| Versiones de reporte médico | 1.631 | 1,841 |
| Filas médicas | 165.729 | 186,634 |

Los boxscores siguen en 164.218 filas:6.150 regulares,71 pretemporadas 2025–26 y el conjunto parcial previo de 85 playoffs,6 play-in y 1 finalCup. No se amplió ese censo en esta corrida.

## Archivo público de props

Se recuperó [NBA-Propositions-Forecasting-App](https://github.com/KamranSHussain/NBA-Propositions-Forecasting-App/tree/a95be8924f3c4fe08b44dcfd940269610ca49501) en el commit `a95be8924f3c4fe08b44dcfd940269610ca49501`. El ZIP tiene 12,526,310 bytes; se verificaron 3.665 blobs Git, incluidos 3.662 JSON históricos, mapaCSV,README ylicencia. Se extrajeron datos; no se ejecutaron modelos, entrenamiento ni código upstream. El README confirma el uso del archivoJSON y mapa para reconstruir su exportación; sus afirmaciones de rentabilidad no se adoptan aquí.

El mapa contiene 3.604 pares únicos deID NBA/evento. Se aceptan 3.496 snapshots tras verificar el evento del nombre de archivo, roster canónico, equipos/localía/fecha de un archivo NBA independiente y horario exacto de ESPN.3.429 contienen pares aceptados. Se conservan en cuarentena 95 eventos sin mapa,70 fechas de inicio contradictorias y 1 referencia sin localía única; también 8.052 rechazos de mercados actualizados después de su snapshot,11.364 identidades de cuota no resolubles/ambiguas y 59 grupos sin un par Over/Under válido. Son conteos de entidades de distinta unidad; no deben sumarse como si fueran partidos.

| Temporada | Partidos con puntos nuevos | Pares de precios nuevos |
|---|---:|---:|
| 2023-24 | 1,141 | 102,223 |
| 2024-25 | 1,155 | 42,299 |
| 2025-26 | 1,133 | 83,802 |

Las 228.324 cotizaciones son **pares Over/Under de puntos**, con 11 casas. El conjunto combinado tiene 228.927 pares de puntos,2.961 rebotes y 192 asistencias. Rebotes/asistencias conservan su cobertura piloto; esta fuente no los amplía.

El horizonte efectivo respecto al horario ESPN va de 6.07 a 16.79 horas. Se conserva la hora real del snapshot y la diferencia entre inicio del proveedor y horario ESPN. **No son cortes prescritosT−60/T−15.** Cada precio exige actualización de casa/mercado≤snapshot<ambos horarios de inicio, vecinos ordenados, precio decimal finito>1, línea válida, par exacto y nombre completo único dentro del roster del mismo partido. Las identidades postgame sirven solo para vincular ID s; no prueban roster o disponibilidad pregame.

Los calendarios ESPN 2024/2025 se descargaron de [los assets públicos de sportsdataverse](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_nba_player_boxscores), fijados porID de asset ySHA 256 publicado;2026 reutiliza el archivo sellado. Los intentos de calendario mensual del endpointESPN devolvieron 400 y se conservaron; no se usaron como evidencia de horarios.

## Las tres rotaciones restantes

ZenRows recuperó las actas oficiales completas de SAC–NOP 29-oct-2021,WAS–BKN 4-feb-2023 yBKN–MEM 13-dic-2024, de 19/20/20 páginas. Hernangómez entra/sale a 20,2 s y 18,6 s del cuarto período; TajGibson a 12,2 s; TrendonWatford a 2:36. Entrada/salida mantienen el mismo reloj detenido. Se verifican fecha/localía del PDF, nombre eID/equipo canónicos, boxscore 00:00, secuencia abreviada del PDF y ID s explícitosV 2/V 3. Morris se resuelve dentro deWAS, porque el otro equipo también tiene unMorris. Las páginas se inspeccionaron visualmente.

Se repiten todos los eventos originales y el replay de sustituciones depbpstats, sin borrar acciones, modificar minutos canónicos ni conceder segundos positivos. Los actores administrativos no pueden cubrir ningún tramo de duración positiva. Los 139 tramos nuevos coinciden conRamiro y satisfacen cinco ID s únicos, continuidad, reloj y minutos individuales. NBA/Ramiro pueden compartir origen; no se presentan como observadores independientes.

## Intradía médico

Se inventariaron 240 rutas candidatas de siete fechas:24-oct-2023,1-nov de 2021/2022/2023/2024/2025 y 1-feb-2026. Se obtuvieron 223 PDF s;13 ya estaban sellados y **210 son nuevos**,20.905 filas y 18.750 filas nominales conID. El conjunto final conserva 1.631 reportes anteriores y añade 210: **1.841 reportes/186.634 filas**. Las 22 filasCuiYongxi se vinculan por el nombre completo exacto y prueba canónica anterior, con literal médico intacto.

En 24-oct-2023 están disponibles siete cortes 17:30–23:30 ET. Las 17 rutas anteriores devolvieron 403; el inicio 17:30 coincide con la constante de arranque 2023–24 del [scraper nbainjuries](https://github.com/mxufc29/nbainjuries/blob/main/src/nbainjuries/_constants.py). El pedido previo 16:30 es anterior a ese límite documentado. Esto no prueba que jamás existiera un archivo 16:30, pero tampoco acredita un bloqueo general deIP: los cortes posteriores se descargan del mismo servidor. Las otras cinco fechas legadas tienen 24 PDF s cadauna;1-feb-2026 tiene 96 candidatos disponibles. Es un inventario completo de la nomenclatura documentada en **estas siete fechas**, no de las 816 fechas del censo ni de todas las posibles versiones históricas.

Los parsers concuerdan en entidades/estados y equipos sin reporte. Trece PDF s se rechazaron inicialmente porque el control de motivo de la última página se aplicaba también a páginas normales con muchas filas. Se acotó al caso de una fila, manteniendo geometría estricta y coincidencia literal para continuaciones escasas. En páginas normales se conservan los motivos por coordenadas y las diferencias del lector upstream que cambia el orden de líneas. No se reemplazan textos para hacerlos coincidir.

Hay 1216 horarios únicos corroborados y 1.215 selecciones retrospectivasT−60. Los campos agregados iniciales `known_scheduled_games` pueden incluir consultas vacías del diccionario; no se usan como conteo de horarios verificados. Recepción actual y encabezado antiguo no prueban recepción pregame original. `pregame_availability_verified=false`, `original_historical_receipt_known=false` y `actionable=false` permanecen.

## Verificación y costes

**189 pruebasNBA pasaron** (aviso de caché depytest sin escritura). El arnés pasó 707 antes y 732 después; el aumento pertenece a cambios concurrentes del proyecto de fútbol, que se preservaron. No se cambió producciónNBA. Se verificaron las 4.939 evidencias,41 corridas y 89 eventos de cadena previos, hashesGit/SHA 256 y preservación exacta de rosters,rotaciones,reportes y 3.756 precios previos. Se conservaron fallos de adaptadores,lecturaUTF 8 y versiones intermedias; la instantánea de auxiliares refleja sus versiones finales, no cada ejecución fallida.

**Cero llamadas/créditos nuevos de TheOddsAPI**; límite 500 agotado, propuesta 720 adicionales no autorizada ni ejecutada. ZenRows:30 créditos nuevos confirmados; riesgo conservador 1.782/3.200 incluyendo reservas anteriores inciertas. Uso de cuenta observado 1.474/5.000, no saldo en tiempo real. Sin compras ni cambios de plan. Los controles adversariales rechazan hashes/intervalos administrativos alterados, horarios posteriores, localía incorrecta, precios/líneas inválidos, pares duplicados e identidad ambigua.

Registro localNBA-RUN-042, auto revisión, sin revisor independiente ni anclaje externo. No se promovieron modelos,gates,picks o métricas deROI.

## Artefactos y pendientes

- Rotaciones: `apps/nba/.local/normalized/nba_pending42_rotations_final_20261007/combined_games.jsonl.gz`.
- Precios: `apps/nba/.local/normalized/nba_pending42_props_v2_20261007/quotes.jsonl.gz`, con snapshots,cortes reales ycuarentena.
- Médicos: `apps/nba/.local/normalized/nba_pending42_medical_identified_20261007/reports.jsonl.gz`.
- Auditoría: `apps/nba/.local/normalized/nba_pending42_validation_20261007/`.
- Originales y recibos: `apps/nba/.local/raw/nba_pending42_20261007/`.

Restan props de rebotes/asistencias a escala, puntos en los eventos/temporadas faltantes y cortesT−60/T−15, intradía de las demás fechas, recepción histórica original y reglas de liquidación por casa/fecha/jurisdicción. Las rotaciones regulares del censo ya no están pendientes. Un histórico de precios amplio permite avanzar en investigación; no autoriza un backtest que suponga datos pregame o liquidaciones aún no acreditadas.
