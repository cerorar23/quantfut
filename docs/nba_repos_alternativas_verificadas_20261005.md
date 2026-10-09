# Repositorios propuestos: revisión y recuperación alternativa NBA

Fecha del cliente: 2026-10-05, México. Las capturas de esta revisión son del 2026-10-06 UTC. **La lista aporta fuentes útiles, pero no demuestra que todas estén actualizadas, funcionen en esta conexión o cubran todos los huecos.** Se verificaron siete repositorios con commit, árbol y archivos de referencia, sin ejecutar sus proyectos ni instalar sus dependencias. Cero consultas a The Odds API.

## Resultado práctico de esta revisión

1. Basketball Reference respondió HTTP 200 para el día 2021-10-20. Se extrajeron 235 jugadores de la página y se conciliaron los 20 participantes de Denver–Phoenix, GameID NBA `0022100012`. Cada equipo suma 240 minutos y sus puntos, rebotes y asistencias coinciden con la referencia NBA. El validador existente no produjo errores. Se conserva el resultado en staging, sin reemplazar el dataset principal de 154,058 filas ni declarar cerrado el censo de pendientes.
2. El archivo NBA de Michael Porter Jr. contenía `33:60`; Basketball Reference indica **`33:59`**. Otros jugadores difieren un segundo entre fuentes. La evidencia demuestra que convertir automáticamente segundos 60 al minuto siguiente habría introducido una corrección incorrecta. El reemplazo del piloto usa los minutos completos de la fuente independiente y conserva ambos valores para auditoría.
3. Se descargó `player_box_2026.parquet` de la release ESPN NBA de SportsDataverse: 606,444 bytes, 34,883 filas, 1,326 eventos, fechas 2025-10-21 a 2026-06-13. Su SHA256 coincide con el digest publicado por GitHub. Cruce exploratorio por fecha y nombres de ambos equipos: candidatos únicos para 84/84 pendientes regulares recientes, 3/3 playoffs y 1/1 play-in; 0/71 pretemporada. **Son candidatos, no un cruce oficial o una importación.** ESPN usa IDs propios y minutos enteros; no permite acreditar segundos exactos. Los 1,235 eventos de tipo ESPN 2 tampoco se deben equiparar automáticamente a 1,230 partidos regulares NBA.
4. Se descargó el JSON completo de JaseZiv: 8,803,596 bytes, 73,306 filas de transacciones/lesiones. SHA256 y Git blob coinciden con el commit fijado. Fecha máxima 2025-05-13; una fecha inválida `1899-12-30` y 16 registros sin equipo, sin duplicados exactos. No contiene IDs oficiales, hora de publicación o estados de disponibilidad por corte. Se conserva como archivo auxiliar sin incorporarlo al modelo.

## Fuentes y correcciones a la propuesta

| Repositorio | Utilidad comprobada y límite |
| --- | --- |
| [swar/nba_api](https://github.com/swar/nba_api/tree/52c0fb0b81c4b785d6cebeb9988799e5d796dfd7) | Cliente de stats.nba.com. El código contempla `Regular Season`, `Pre Season`, `PlayIn` y `Playoffs`; que exista el parámetro no acredita cobertura de cada endpoint. Instalar el wrapper no elimina nuestros timeouts del servidor. Último commit verificado 2026-08-16. |
| [sportsdataverse/hoopR](https://github.com/sportsdataverse/hoopR/tree/02726d420b0c82e438d662ecc75194b22b3a734a) | `load_nba_player_box` y `load_nba_schedule` cargan releases ESPN en RDS; el histórico NBA Stats utiliza otras funciones/assets. No son un mismo dataset ni un esquema interchangeable con nba_api. La release también ofrece Parquet y se descargó la alternativa reciente. Commit 2026-10-05. |
| [jaebradley/basketball_reference_web_scraper](https://github.com/jaebradley/basketball_reference_web_scraper/tree/1ec892df21e7f206ab253ed0a3ade3fc4be2e16e) | Métodos por día, jugador/temporada regular y playoffs. La página de prueba funcionó; el paquete no se ejecutó. Los IDs Basketball Reference son distintos de NBA y las ausencias de la tabla diaria no prueban un DNP o una lesión. La función del scraper usa `dailyleaders.cgi`; nuestra captura independiente empleó `dailyleaders.fcgi`, por lo que no acredita ejecución de su función. Commit 2026-09-05. |
| [dblackrun/pbpstats](https://github.com/dblackrun/pbpstats/tree/e7ccf2fb6326da630a3cf1665aac964a1e108f4c) | Cliente documentado: `from pbpstats.client import Client`, recursos `EnhancedPbp` y `Possessions`, fuentes web/archivo. `DataEngine` no es la entrada demostrada por su guía. Los overrides y correcciones de orden de eventos son parte del proceso; no se garantiza reconstrucción exacta automática de todos los partidos. Último commit observado 2024-04-17. |
| [shufinskiy/nba-on-court](https://github.com/shufinskiy/nba-on-court/tree/6791ac6264e6f3f7ef061d7812a87d011cf2803b) | Infere diez jugadores por evento a partir de sustituciones y puede cargar los dumps ya disponibles. No aporta tracking espacial o una observación continua independiente de quién estaba en cancha. El código importa NBA BoxScore V2 para ciertos casos: instalarlo no garantiza procesamiento totalmente offline. Último commit 2024-12-19. |
| [mxufc29/nbainjuries](https://github.com/mxufc29/nbainjuries/tree/57603738fb28185e3c1bf4d71d75af0f85514ac1) | Interfaz real `injury.get_reportdata(datetime(...), return_df=True)`. Extrae PDF con Java/tabula y layouts por temporadas. El ejemplo devuelve siete columnas médicas; el timestamp solicitado no viene automáticamente como prueba de publicación en cada fila. Su README advierte huecos y falta de pretemporada. Nuestro parser conserva cabecera/recepción y ya tiene tres PDF comprobados. Commit 2026-02-10. |
| [JaseZiv/NBA_data](https://github.com/JaseZiv/NBA_data/tree/217ce05b967b201d1b7a474f20b4a6cab273de66) | Archivo útil para contexto de ausencias prolongadas. Contiene un workflow diario, pero el último commit observado es 2025-05-16 y el archivo termina el 2025-05-13. El cron escrito no acredita que siga actualizándose. No sustituye reportes NBA con corte horario. |

Guía primaria de pbpstats: [uso y problemas del PBP](https://pbpstats.readthedocs.io/en/latest/quickstart.html). Documentación de lesiones: [firma real de get_reportdata](https://github.com/mxufc29/nbainjuries/blob/57603738fb28185e3c1bf4d71d75af0f85514ac1/Documentation.md).

## Censo y cronología que se mantienen

El inventario sigue identificando 395 partidos conocidos pendientes del dataset principal: 320 regulares, 71 pretemporada, tres playoffs y un play-in. Los siete problemas de referencias de equipo **ya tienen GameID**. En 299 pendientes regulares se encontraron minutos inválidos; no hay evidencia para atribuir todos los 313 restantes a una misma causa o solución.

Estos repositorios ofrecen estadísticas, PBP y contexto médico. La revisión no aporta cuotas de apuestas históricas de props con casa, línea, precio y hora. Para esas cuotas se requiere una fuente distinta y su presupuesto/validación.

El corte médico debe exigir hora declarada de cabecera, conversión ET/UTC, recepción, identidad y comienzo del partido. Descargar en 2026 un reporte de 2025 permite investigación retrospectiva y no acredita su disponibilidad original. El archivo JaseZiv carece de esa precisión; no se convierte una fecha de transacción en hora de noticia.

## Orden de las siguientes fases

- F2/F3: formalizar el adaptador de Basketball Reference con caché por fecha, capturas limitadas y cruce separado de IDs. Antes de importar, exigir fecha, local/visitante, equipos, unicidad del jugador, estadísticas concordantes y validación completa de minutos. El piloto acredita un partido, no la fiabilidad del histórico entero.
- F3: usar los candidatos ESPN para verificar nombres/estadísticas y localizar eventos; recuperar segundos exactos por otra fuente. Obtener calendario y boxscores de pretemporada por separado, porque el Parquet recibido no los contiene. Corregir las siete referencias de equipo con corroboración independiente, sin bajar el umbral del validador.
- F4: procesar primero los PBP locales ya descargados. Ensayar una muestra con pbpstats o algoritmo propio auditado, registrar overrides y comprobar cinco jugadores por equipo, aperturas de cuarto, prórrogas y conciliación de minutos. GameRotation sigue como verificación adicional cuando sea accesible.
- F3/F4: ampliar reportes PDF por temporada/layout, conservar desconocidos y cruzar IDs/horas oficiales. JaseZiv queda como contraste de largo plazo con cuarentena de fechas inválidas.
- F6: publicar alertas solo después de validar modelos, disponibilidad y contratos/precios reales. Ninguna de estas descargas habilita picks comerciales por sí sola.

## Evidencia y comprobación

Capturas bajo `apps/nba/.local/raw/source_review_20261005/`: `public/manifest.json`, `pilot/manifest.json`, `espn2026/manifest.json`. Los scripts de investigación están bajo `.local/reports/`, separados del código de producción; los proyectos externos no se ejecutaron.

`bref_reconciled_pilot_20261005.json` contiene los veinte jugadores, valores originales/reemplazos, método de cruce y resultado del validador. `espn_pending_candidates_20261005.json` contiene cada candidato y sus límites. El informe de verificación registra los hashes de capturas y scripts.

El harness de esta revisión pasa 609 pruebas, con una advertencia y Docker no disponible. Se verifican sin cambios los 37 archivos del snapshot NBA y las 100 evidencias anteriores. Las 136 pruebas NBA de la versión anterior siguen vinculadas a ese mismo código; no se atribuye una nueva ejecución NBA a esta revisión. **Dataset principal y modelo sin cambios, un partido conciliado en staging, cero créditos de The Odds API y todas las puertas pendientes.**
