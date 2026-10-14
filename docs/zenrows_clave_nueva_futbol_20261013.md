# Fútbol: recuperación adicional con la clave nueva de ZenRows

Importación confirmada el 13-oct-2026 a las 18:55 de México
(14-oct 00:55 UTC). Esta carga amplía la anterior de
`docs/soccerdata_zenrows_20261013.md`; no sustituye sus originales.

## Resultado comprobado en PostgreSQL

| Dato | Resultado adicional |
| --- | ---: |
| Originales de partidos guardados | 125 |
| Asociados con partidos existentes | 101 |
| Asociación pendiente de clubes en Europa League | 24 |
| Parejas xG presentes en los originales | 97 |
| Parejas xG añadidas a partidos canónicos vacíos | 36 |
| Alineaciones de equipo | 228 |
| Registros de estadísticas de jugadores | 4.137 |
| Registros de bajas por partido | 294 |
| Partidos con ambos XI completos en los originales | 91 |
| Nuevos partidos o clubes canónicos | 0 |

De las 97 parejas xG, once pertenecen a originales sin asociación canónica
y cincuenta corresponden a partidos cuyo xG previo se conservó. Solo 36
rellenan huecos. Los datos de jugadores, XI y bajas se guardan en las tablas
históricas por proveedor; su almacenamiento no acredita una integración nueva
con los consumidores del modelo ni una disponibilidad previa al partido.

| Competición | Originales | Asociados | xG nuevos | Sin xG después, desde 2024 |
| --- | ---: | ---: | ---: | ---: |
| Brasil B | 29 | 29 | 16 | 384 |
| Bundesliga 2 | 30 | 30 | 9 | 0 |
| Dinamarca | 12 | 12 | 3 | 3 |
| Suecia | 24 | 24 | 8 | 2 |
| Europa League | 30 | 6 | 0 | 12 |

La cobertura se mide sobre 22.607 encuentros terminados con fecha desde
2024-01-01 y anterior a 2026-10-15 UTC, con los datos disponibles al verificar.
Los huecos xG pasan de 3.154 a **3.118**. Los principales pendientes siguen
en LaLiga 2 (714), Chile (661), Serie B italiana (589), Ligue 2 (502), Brasil B
(384) y Argentina (212). Disponer de calendario no demuestra que la fuente
publique xG para toda esa historia.

## Descarga y coste

Se aplicó la documentación oficial de
[inicio](https://docs.zenrows.com/first-steps/welcome),
[modo automático](https://docs.zenrows.com/fetch/features/adaptive-stealth-mode),
[concurrencia](https://docs.zenrows.com/fetch/features/concurrency),
[CLI](https://docs.zenrows.com/cli/fetch/introduction) y
[errores](https://docs.zenrows.com/api-error-codes).

- CLI oficial fijada en `@zenrows/cli@1.5.0`; MCP existente 2.4.0 para lectura
  de cuota y pruebas acotadas. Sin registro automático ni compras.
- Modo automático sin forzar JavaScript, proxy premium o país en cada llamada.
  Las pruebas con país alternativo se conservaron por separado.
- El host público `www.sofascore.com/api/v1/` permitió leer jornadas donde la
  ruta `api.sofascore.com` había fallado. Se usó el parser de calendarios de
  soccerdata 1.9.1, con respuestas originales y transporte sustituidos.
- Tres descargas simultáneas frente al límite verificado de cinco.
- Presupuesto compartido: reservar hasta 25 créditos antes de cada llamada,
  devolver solo el coste comunicado por la CLI y conservar 100 de reserva.
  Coste desconocido permanece reservado; autenticación o cuota agotada
  detienen llamadas siguientes. No asumir gratuitos todos los errores:
  `RESP008` es una excepción de facturación documentada.
- Originales y recibos por hash; reutilización de éxitos. Los fallos quedan
  registrados y no se repiten automáticamente. Dinamarca se procesó por
  jornadas independientes para evitar que el fallo de la octava impidiera
  recuperar la novena y décima.
- La descarga principal hizo 233 solicitudes CLI y el complemento danés 26.
  Las pruebas de acceso anteriores también forman parte del consumo total.

La cuenta nueva se validó con 5.000 créditos, estado `TRIALING` y consumo inicial
cero. Última lectura: **988 utilizados y 4.012 restantes**, concurrencia activa
cero, el 14-oct 00:51:57 UTC. El saldo procede de la cuenta, no de suponer que
las consultas fallidas no cuestan. La configuración y cuenta compartidas
anteriores se conservan. La clave nueva está cifrada con DPAPI en `.local`,
fuera de Git, y se facilita a los procesos solo mediante su entorno; no se
envió al VPS.

Las muestras históricas de tiros en España y Francia sí respondieron, pero
sus tiros no contienen xG. No se convierten coordenadas de disparos en xG
publicado ni se inventan ceros. Los calendarios actuales recuperados tampoco
acreditan el acceso a todas las temporadas anteriores.

## Asociación, carga y conservación

Se reutilizaron identidades SofaScore ya corroboradas en la base. Se revisaron
seis equivalencias danesas (Nordsjælland, Odense, Brøndby, København, AGF y
Sønderjyske), con país DK, nombres y dos partidos independientes por club
coincidentes en fecha y marcador. La identidad doméstica de AGF también
permitió asociar su encuentro europeo. No se usó correspondencia difusa ni
se crearon equipos bajo una copa.

Los 586 IDs SofaScore de la carga anterior se excluyeron antes de descargar
detalles; su primer original y recepción siguen congelados. Los 24 originales
europeos pendientes y sus datos secundarios se conservaron como tales.

Antes de la carga definitiva se aplicó el mismo archivo dos veces dentro de
una transacción revertida: la segunda pasada hizo cero escrituras adicionales
y la reversión conservó los conteos. La carga real confirmó después:

- 125 normalizaciones idénticas a sus bundles; cuerpos HTTP originales
  comprobados por hash, URL, contenido y recepción.
- 22.632 registros de partidos previos conservados, incluyendo los valores
  xG existentes, marcadores y las identificaciones de proveedores.
- 23.042 originales históricos anteriores conservados con sus hashes,
  recepción y decisión de asociación.
- 36 xG nuevos ocultos antes de su recepción y disponibles después.
- Modelo `2026.09.27-010508`, ligas y captura completa conservados; lotes
  sellados y tablas antiguas de jugadores/XI de API-Football conservados.
- API interna y pública `/model-card`: HTTP 200 y la misma versión; lectura
  pública desde el equipo local con `User-Agent: Mozilla/5.0`.
- Arnés: **1.045 aprobadas, 24 omitidas**, dos avisos; comprobación de sintaxis
  aprobada. Docker no está instalado localmente y su comprobación se omitió.

No se desplegó código nuevo del modelo ni se reinició el worker para esta
carga. No hubo entrenamiento nuevo, activación de ligas, cambios de puertas,
cuotas, picks o configuración de publicación, ni mensajes externos manuales.
La recepción actual del xG no demuestra una mejora retroactiva del backtest.

## Evidencia y pendientes

Evidencia local: `.local/zenrows_key_20261013/prepared/` y `verified/`.
Evidencia del worker:
`/srv/quantfut/artifacts/imports/zenrows-new-key-20261013/`.
Incluye `result.json`, `verification.json`, plan y equivalencias revisadas,
pruebas de reversión/idempotencia, copia previa de partidos y cobertura final.
Los originales deportivos se transfirieron sin la credencial cifrada.

Pendientes: 3.118 huecos xG, asociación de clubes europeos aún desconocidos,
historia completa de las ligas recuperadas y adaptación de los consumidores
de jugadores/XI/bajas históricos. Se conservan las cuarentenas anteriores de
Troyes–Valenciennes y Catanzaro–Brescia.
