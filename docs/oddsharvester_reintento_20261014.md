# Reintento de OddsHarvester con ZenRows — 14-oct-2026

**Cero cierres Pinnacle nuevos. La lista de 6.185 partidos no está completada.**
Se repitió la captura solicitada con cuatro sesiones nuevas y dos partidos de
la lista exacta. Tres sesiones acreditan el mercado 1X2 de tiempo completo y
`bookieFilter=all` en los datos que recibe el navegador; ninguna trae Pinnacle.

El archivo original sigue intacto, SHA-256
`3a418b365b51409bed24842cb7897ae5dea146b1740f4d778c80cbedaf9b1eaf`.
La ruta existente es `.local/cierres_faltantes_20261014.csv`; la ruta del mensaje
sin separador antes de `.local` se interpretó como referencia al mismo archivo.
No se escribió en producción ni se cambiaron equipos, resultados o modelos.

## Ejecuciones reales

Se confirmó que el HEAD remoto de [OddsHarvester](https://github.com/jordantete/OddsHarvester)
continúa en `5bbc0467fc5b7742bdb1b2fa2c50cdfd7721f86f`, versión 0.20.0.
Se ejecutó esa copia aislada con `upcoming --match-link` —el comando acepta
fichas históricas—, `1x2`, `full_time`, `all`, zona UTC y concurrencia uno.
No se filtró por Pinnacle al extraer para observar todas las casas devueltas.

El adaptador existente conecta Playwright por CDP a ZenRows Browser Sessions,
con `proxy_country` y una conexión nueva por ejecución, TTL de tres minutos.
La rotación residencial es una función predeterminada del servicio según la
[documentación de ZenRows](https://docs.zenrows.com/browser-sessions/features/country).
El mensaje del CLI «No proxy provided» describe su lista HTTP vacía; en estas
ejecuciones el transporte real está reemplazado por el navegador remoto.

| Partido de la lista | País solicitado al servicio | Casas extraídas | Datos del mercado y todas las casas verificados | Pinnacle |
| --- | --- | ---: | --- | ---: |
| Manchester United–Manchester City, 17-ene-2026 | Perú | 5 | No: espejo español, fecha no interpretada y filtro no confirmado | 0 |
| Mismo partido | Finlandia | 8 | Sí: evento Q5AqCTPG, mercado 1, scope 2, all | 0 |
| Mismo partido | Canadá | 11 | Sí: evento Q5AqCTPG, mercado 1, scope 2, all | 0 |
| PSG–Inter, 31-may-2025 | Canadá | 8 | Sí: evento 6LTndcTP, mercado 1, scope 2, all | 0 |

Las tres ejecuciones confirmadas leyeron inicios UTC y marcadores correctos:
United–City, 12:30 UTC y 2–0; PSG–Inter, 19:00 UTC y 5–0. El control peruano
se conserva como limitación y no se usa para acreditar asociación ni filtro.

En Finlandia solicitada aparecieron 1xBet, bet365, Betfury, Bets.io, Cloudbet,
Roobet, Stake.com y Unibet. Canadá solicitado añadió o cambió casas como
888sport, Betway, Melbet y Sports Interaction. No se usaron sus precios como
sustitutos de Pinnacle.

## Comprobación adicional de los datos

Además del HTML y del resultado del scraper, se archivaron las respuestas
públicas de precios de la ficha y el JSON descifrado que consume normalmente
su interfaz. Se amplió localmente el hook de observación que OddsHarvester ya
utiliza para comprobar mercado y período. No se accedió a una cuenta de usuario
ni se modificaron solicitudes para pedir recursos de pago.

Los tres objetos de precios comprobados contienen respectivamente 8, 11 y 8
proveedores, iguales al número de filas que extrae el scraper. Se guardan
`odds`, `openingOdd`, `changeTime`, `nav`, identificador del evento y filtro.
La representación descifrada se etiqueta expresamente como tal: su hash no se
confunde con el de la respuesta cifrada original. No se interpretan las cuotas
de apertura ni de otras casas como cierres de Pinnacle.

El parámetro `geo` de las solicitudes internas fue `BG`, incluso al solicitar
Finlandia y Canadá al servicio. Un chequeo independiente con IPinfo falló; no
se acreditó por separado el país físico de salida. Se distinguen el país
solicitado, el parámetro interno y la geolocalización efectiva sin asumir que
sean equivalentes. Los catálogos devueltos sí cambiaron entre sesiones.

Un intento de iniciar el control PSG–Inter no llegó a ejecutarse porque expiró
la revisión automática de permisos. El reintento permitido sí se ejecutó y
completó la captura; no se cuenta el intento no ejecutado como fallo del sitio.

Estos resultados acreditan ausencia de Pinnacle en las respuestas examinadas,
no su ausencia en todo país, cuenta o fecha de OddsPortal. No se realizaron
6.185 consultas individuales: cuatro sesiones corresponden a dos filas exactas.
Las muestras no acreditan cobertura para completar el lote con este acceso.

## Archivos guardados

Directorio versionable: `data/pinnacle_recovery/20261014_oddsharvester_retry/`.

- `lista_resultado.csv`: 6.185 filas, columnas originales de cierre vacías,
  272 candidatas previas en columnas separadas y estado de este reintento.
  Solo las dos filas consultadas se marcan como muestras sin Pinnacle; las
  otras 6.183 señalan que no se consultaron individualmente en el reintento.
- `informe.json`: cuatro sesiones, dos partidos distintos, cero cierres nuevos
  y la limitación de la geolocalización.
- Carpetas por ejecución: resultado de OddsHarvester, tres objetos de precios
  descifrados, respuestas originales de precios y recibos, cuando disponibles.
- `manifest.json`: hashes y tamaños de los archivos de esta ampliación.

La validación comprobó 17 recibos, integridad del archivo original, evento,
mercado, período, filtro y número de proveedores de las tres capturas completas.
Quedan las mismas 272 candidatas sin certificar como cierre final y 5.913 filas
sin candidata. La copia anterior y su commit `43c462f` se conservan intactos.

Los logs, HTML y adaptador de observación adicionales están en
`.local/oddsharvester_retry_20261014/`. Los endpoints de autenticación/sesión
no se incluyen en el paquete de datos guardado.
