# PropLine: cuota horaria compartida y archivo prospectivo

Decisión del titular, 23-oct-2026: PropLine es la fuente fija de cuotas para los motores, pronósticos y consultas. Capturar una vez cada hora, compartir el archivo entre consumidores y conservar la mayor cantidad de datos para evaluación y reentrenamiento posteriores. Esta decisión sustituye la captura personal de cierres cada dos horas, no las fuentes de estadísticas, resultados oficiales o lesiones.

## Archivo y presupuesto

`qf.ingest.propline_shared` funciona también como archivo Python independiente, sin instalar dependencias en el servidor. Configuración: `scripts/propline_shared_config.json`. Documentación técnica contrastada: https://api.prop-line.com/docs y su `/openapi.json` (parámetros `markets`, `period`, `includeLinks`, `includeBookIds`, `includePregameOnly`, `includeRestricted`; `markets` predeterminado es `h2h`). Catálogo actual: 59 entradas deportivas, incluidas 31 competiciones de fútbol. Se solicita cada grupo activo, todas las casas disponibles, periodos, identificadores y campos de restricciones. La lista documentada de mercados se divide por familia; un descubrimiento por evento/deporte/día añade las claves vistas en un partido real. Eso no prueba cobertura universal de cada mercado de todos los eventos.

La prueba real detectó dos límites: omitir `markets` devuelve solo `h2h`; más de 50 claves devuelve HTTP 400. Además, una consulta conjunta de líneas y props NBA agotó el tiempo de respuesta. Por eso los lotes generales son de diez claves; baloncesto separa líneas principales, solicita puntos/rebotes/asistencias individualmente y divide los demás props en cinco claves. El libro cuenta conservadoramente todos los intentos, también fallos ambiguos. No reintenta automáticamente una solicitud de una hora ya reservada.

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
