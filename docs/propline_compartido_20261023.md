# PropLine: cuota horaria compartida y archivo prospectivo

Decisión del titular, 23-oct-2026: PropLine es la fuente fija de cuotas para los motores, pronósticos y consultas. Capturar una vez cada hora, compartir el archivo entre consumidores y conservar la mayor cantidad de datos para evaluación y reentrenamiento posteriores. Esta decisión sustituye la captura personal de cierres cada dos horas, no las fuentes de estadísticas, resultados oficiales o lesiones. Por indicación expresa del titular, el alcance horario queda limitado a todas las competiciones `soccer_*`, `tennis` y `basketball_nba`. Las observaciones de otros deportes recibidas durante la primera verificación se conservan y no se vuelven a consultar.

## Archivo y presupuesto

`qf.ingest.propline_shared` funciona también como archivo Python independiente, sin instalar dependencias en el servidor. Configuración: `scripts/propline_shared_config.json`. Documentación técnica contrastada: https://api.prop-line.com/docs y su `/openapi.json` (parámetros `markets`, `period`, `includeLinks`, `includeBookIds`, `includePregameOnly`, `includeRestricted`; `markets` predeterminado es `h2h`). Catálogo actual: 59 entradas deportivas, incluidas 31 competiciones de fútbol. Se solicita cada grupo activo, todas las casas disponibles, periodos, identificadores y campos de restricciones. La lista documentada de mercados se divide por familia; un descubrimiento por evento/deporte/día añade las claves vistas en un partido real. Eso no prueba cobertura universal de cada mercado de todos los eventos.

La prueba real detectó dos límites: omitir `markets` devuelve solo `h2h`; más de 50 claves devuelve HTTP 400. Además, una consulta conjunta de líneas y props NBA agotó el tiempo de respuesta. Por eso los lotes generales son de diez claves; baloncesto separa líneas principales, solicita puntos/rebotes/asistencias individualmente y divide los demás props en cinco claves. En fútbol las líneas principales van separadas y los 26 mercados restantes se dividen en dos lotes de trece, pues mezclar líneas y props produjo HTTP 504 en el primer despliegue. NFL y competiciones equivalentes separan también las líneas principales y dividen los 33 props restantes en tres lotes de once. Las consultas aceptan una respuesta del caché de PropLine con antigüedad máxima de 3.600 segundos; el archivo conserva las marcas reales que entrega el proveedor. El libro cuenta conservadoramente todos los intentos, también fallos ambiguos. No reintenta automáticamente una solicitud de una hora ya reservada.

Tope propio: 4.500 solicitudes/día; reserva de cuenta: 500. Se leen las cabeceras reales y se detiene ante 401/403/429 o falta de presupuesto. Cuotas primero; resultados cada seis horas; identidades y futuros una vez al día. El presupuesto de otros consumidores se observa en las cabeceras, pero este libro no coordina clientes externos ajenos al recolector.

Cada respuesta original se guarda comprimida por SHA-256. Las observaciones horarias tienen recibos separados aunque los bytes no cambien; no se sobrescriben ni se purgan automáticamente. El capturador se detiene si el volumen dispone de menos de 5 GiB libres. SQLite indexa recepción real UTC, ruta/parámetros sin clave, estado HTTP, hash, conteos y cuota. Los recibos rechazan UPDATE/DELETE. Los hashes detectan cambios respecto del índice conservado; no son un anclaje externo ni almacenamiento WORM.

La lectura `newest()` reúne los lotes de una misma hora disponibles antes de `as_of`, verifica cada objeto y rechaza archivos vencidos. Los originales preservan mercados, periodos, equipo, jugador, IDs de fuente/casa, líneas, precios Americanos, marcas de entrega/cambio/publicación, restricciones y liquidez si la respuesta la incluye. Las cuotas decimales se derivan explícitamente; una fecha de publicación ausente permanece desconocida.

## Consumo por los motores

La clave solo la recibe el recolector. `latest` y `export` son lecturas sin consultas al proveedor. Todos los motores pueden compartir la misma raíz de archivo, evitando solicitudes por partido o motor.

`qf.ingest.propline_ingest` enlaza los eventos con el calendario de fútbol y carga los mercados soportados a `odds_snapshots`, manteniendo `source='propline'` y recepción real. Esta tabla operativa recibe las casas configuradas para los motores; el archivo conserva todas las casas y mercados para investigación. La escritura del lote y su control se hace en una transacción con bloqueo; no duplica el lote tras reiniciar. Una captura horaria no se etiqueta como `close` ni `post_xi`.

El proveedor se fija mediante `ODDS_PROVIDER=propline` o mediante `provider.json` en la raíz compartida. En ese modo, el worker lee el archivo sin HTTP y las ráfagas/descargas de cuotas API-Football quedan inactivas. Los lectores de 1X2, totales, hándicap y ofertas de los motores de fútbol distinguen la fuente y usan la misma captura. Las identidades ambiguas y los mercados sin adaptador permanecen en el archivo para investigación; no se inventan precios o probabilidades para incorporarlos a picks.

Los pronósticos NBA/tenis y sus protocolos sellados conservan su identidad y validaciones. El archivo común provee los precios para nuevas consultas/adaptadores; no convierte automáticamente un experimento previo con The Odds API en otro con PropLine ni aprueba publicación o reentrenamiento. La API de cuotas no sustituye las estadísticas que usan esos modelos.

Los consumidores excluyen precios en juego o suspendidos, periodos parciales confundidos con partido completo, DFS tratados como apuestas simples y contratos de intercambio sin reglas. El archivo conserva esas filas con su contexto para análisis. Las fuentes secundarias de resultados/estadísticas conservan su procedencia.

## Operación

```text
python propline_shared.py capture --root ARCHIVO --key-file ARCHIVO_PRIVADO --config propline_shared_config.json
python propline_shared.py latest --root ARCHIVO --sport basketball_nba
python propline_shared.py export --root ARCHIVO --sport basketball_nba --as-of 2026-10-24T00:00:00Z
```

Programación horaria con bloqueo externo. Un volumen persistente común evita depender de la vida del contenedor. Conservar el capturador y archivo anteriores como respaldo; al revertir, restaurar la programación/configuración anterior y el código respaldado. Las respuestas ya recibidas no se eliminan.

Antes de entrenar: crear un conjunto versionado con tiempos de recepción y resolución, separar mercados y tipos de precio, resolver identidades, congelar el protocolo y reservar una muestra nueva. La captura no entrena ni cambia un modelo por sí sola.

## Verificación

Arnés inicial del checkout: 1.316 aprobadas, 95 omitidas. Primer arnés con el archivo y adaptadores: 1.339 aprobadas, 95 omitidas. Pruebas específicas cubren reserva de cuota, fallos/duplicados, integridad, lectura punto en el tiempo, conversión Americana, exclusión de contratos incompatibles y separación de fuentes. Arnés de la rama limpia basada en main: **1.468 aprobadas, 104 omitidas** (incluye las 27 pruebas del proveedor compartido). El último piloto NBA obtuvo cinco respuestas 200, 55 observaciones de eventos y 112.154 observaciones de cuotas, sin errores; son observaciones entre lotes, no partidos únicos. Los pilotos y fallos reales quedan en `.local/propline_shared_pilot_20261023`; el estado operativo final se registra en DEPLOYS.md.

## Estado en producción (verificado el 2026-10-24 02:20 UTC, solo lectura)

- **Activado.** `provider.json` (`{"provider": "propline"}`) está en el volumen `artifacts` (`/srv/quantfut/artifacts/propline_shared`); el worker y la API corren `quantfut-{worker,api}-propline:3babeb4` (recreados 01:35 UTC). Captura horaria: cron `7 * * * *` del usuario `qf` con `flock`, en un contenedor aislado `propline-shared-capture` (última pasada 02:18 UTC, `exit_code 0`, todo 200).
- El worker lee el archivo sin HTTP: `odds_worker` informa `source: propline, calls: 0` y las ráfagas de API-Football `consultas: 0` (`shared_hourly_capture`).
- **Alias de ligas (PR #86) desplegado el 24-oct** (worker `a521569`): `stale_sports` baja de 7 a 4; las cuatro restantes no están en el catálogo de PropLine (ver abajo).
- Adaptadores de NBA y tenis: lectura disponible (ver abajo); los motores aún no están conectados.
- Los pilotos no acreditan cobertura continua de todos los mercados.

Historia: hasta el 23-oct el estado era «implementado y probado localmente (commit `5ff66cf`), no activado».
## Ligas fuera del catálogo y adaptadores de NBA y tenis (24-oct-2026)

- **Segunda División, Serie B, Ligue 2 y Superliga danesa no están en el catálogo de PropLine** (59 deportes, 31 de fútbol; verificado en `/v1/sports` archivado). No era un fallo de alias: no hay captura posible. `ingest_hourly` las informa ahora en `sin_cobertura` (solo si hay catálogo archivado de ≤3 días) y deja `stale_sports` para archivos realmente atrasados. The Odds API no es fallback automático (decisión del 23-oct): esas ligas siguen sin cuotas del archivo hasta que el titular decida otra fuente.
- **Adaptadores de NBA y tenis:** `propline_shared.two_way_feed` y `read_two_way(root, sport, as_of)` (solo `basketball_nba` y `tennis`; lectura sin red, punto en el tiempo, misma ventana de edad que el resto). Devuelven eventos con la forma de The Odds API para moneyline, hándicap y totales del partido completo y línea principal; sin periodos, props de jugador, bandas marcadas (en juego, suspendidas, DFS, bolsas) ni mercados de un solo lado. `last_update` solo si la casa publicó `book_updated_at` (nunca la hora de recepción). Comprobado contra el archivo real: NBA 29 eventos/68 casas, tenis 145 eventos/37 casas.
- **Tenis conectado (24-oct):** `tennis_motor` lee el ganador sin margen de `tennis_odds_propline_v1` (sobre `read_two_way`) con `odds_provider: propline`; el cron del VPS ya no toma fotos de The Odds API y no hay respaldo. Fecha de corte: los sellados de la entrada automática desde el despliegue registran `live.provider = propline`; los anteriores conservan su foto de The Odds API. `tennis_odds_live_v1` no se modifica porque el protocolo v8 congela el hash de su código. Ver `apps/tennis/README.md` y DEPLOYS.md.
- **NBA (partido completo) sin recablear:** el productor 1.3.1 ya lee las líneas de jugador del archivo; el paso de precios de equipo sigue con The Odds API. Conectarlo exige decidir fecha de corte y no mezclar proveedores dentro de protocolos ya sellados; con la forma de The Odds API el cambio en `live_market.price_rows` es pequeño, pero ese parser exige `last_update` y deberá aceptar su ausencia.

## Cierre, box score, liquidación y lesiones (24-oct-2026, sin desplegar)

El recolector añade dos fases a cada pasada horaria, siempre **después** de las cuotas y los marcadores:

- **Lesiones NBA** (`injuries_sports`): `/v1/sports/basketball_nba/injuries` una vez por hora (24 peticiones/día). Lectura: `read_injuries(root, sport, as_of)`, con nuestra hora de recepción en cada fila. Es una segunda señal (ESPN, con `status_code` y `status_since`); el protocolo v1.3 sigue usando el PDF oficial.
- **Después del partido, una vez por evento** (`post_game`): los objetivos salen del último `/scores` archivado, así que localizarlos no cuesta peticiones. Al pasar la hora de inicio se pide `/events/{id}/odds/closing` (apertura y cierre por casa); con el partido en `final`, `retired` o `walkover`, `/events/{id}/stats` (box score) y `/events/{id}/results` (liquidación de PropLine). Mercados y casas por familia en `scripts/propline_shared_config.json` (fútbol, NBA y tenis ATP/WTA, igual que el antiguo `propline_captura.py`).
- Comprobado con la clave el 24-oct: **`/results` y `/odds/closing` están incluidos en Hobby** (`redacted: false`). `/stats` de fútbol trae córners y tarjetas por equipo; el nombre del club puede llevar tildes que el evento no tiene.
- **Presupuesto:** cada pasada horaria gasta ~130 peticiones (~3.350/día con marcadores, IDs y futuros); el tope local es 4.500. La fase posterior al partido tiene su propio tope (`per_run` 60, `daily_max` 600) para que nunca deje sin cuotas a las pasadas siguientes. Una petición fallida (p. ej. 404 de un evento fusionado) se reintenta en horas siguientes hasta `max_attempts` (3) y se informa aparte, en `post_game.failures`, sin marcar como fallida la pasada de cuotas. Una liquidación capturada antes de que PropLine califique todo se vuelve a pedir.
- **Lectores sin red:** `read_closing` (filas con `closing_at`, `opening_*` y bandera `pre_kickoff_capture` si se capturó antes del inicio), `read_stats` + `team_stats` (córners y tarjetas por lado; un nombre que no coincide se descarta, nunca se adivina), `read_results`.
- **No se recablearon los motores.** La puerta CLV, la liquidación de córners y tarjetas y el uso de lesiones en NBA deben leer estos datos en cambios propios, con fecha de corte. El emparejamiento por `player_id` de NBA ya existía (`apps/nba/src/nba/prop_lines.py`); en tenis PropLine no da `player_id`.
