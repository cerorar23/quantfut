# Fútbol: cobertura archivada y prueba ZenRows — 13 de octubre de 2026

Actualización posterior: el archivo FotMob se importó en PostgreSQL. Resultado
y cobertura verificados en [importación del 13-oct](importacion_fotmob_20261013.md).

Pedido del usuario: comprobar si se pueden recuperar xG, alineaciones, bajas
y estadísticas de jugadores para las doce ligas sin modelo y huecos de las
trece competiciones habilitadas. **La recuperación es técnicamente viable y
se comprobó con una muestra real. Gran parte del histórico ya está descargado,
pero no importado en las tablas del modelo.** No se ejecutó una carga masiva.

## Fuente ya disponible: archivo FotMob

Periodo: 1-ene-2024 a 3-oct-2026, conservado en
`.local/fotmob-history/2024-01-01_2026-10-03/`.

Se auditaron las 22.461 filas del inventario de las 25 competiciones. Para
cada original disponible se recomputó SHA-256 de sus bytes descomprimidos y se
cotejó con el recibo, después se validaron ID de partido, competición, equipos,
fecha y resultado final mediante el normalizador existente. Los conteos de
xG se recalcularon desde las estadísticas originales del periodo `All`.

Resultado global: 22.456 partidos verificados, 19.631 parejas de xG, 22.455
partidos con dos XI válidos y 22.396 con estadísticas de jugadores de ambos
equipos. Hay tres originales ausentes en Championship y dos discrepancias de
fecha en Brasil A (4732649 y 4732669); quedan excluidos, sin forzar aceptación.
La auditoría no realizó consultas deportivas nuevas.

Los conteos de las doce ligas son:

| Liga | Partidos verificados | Parejas xG | Ambos XI | Estadísticas de ambos equipos | Con campos de bajas no vacíos |
|---|---:|---:|---:|---:|---:|
| Championship | 1.461 | 1.461 | 1.461 | 1.461 | 1.250 |
| LaLiga 2 | 1.252 | 549 | 1.252 | 1.252 | 843 |
| Serie B Italia | 1.028 | 441 | 1.028 | 970 | 782 |
| Ligue 2 | 862 | 370 | 862 | 862 | 89 |
| Bundesliga 2 | 819 | 819 | 819 | 819 | 650 |
| Turquía | 911 | 911 | 910 | 911 | 678 |
| Suiza | 630 | 630 | 630 | 630 | 483 |
| Dinamarca | 531 | 531 | 531 | 531 | 415 |
| Noruega | 647 | 647 | 647 | 647 | 265 |
| Suecia | 656 | 656 | 656 | 656 | 301 |
| Brasil B | 1.066 | 686 | 1.066 | 1.066 | 140 |
| Chile | 662 | 0 | 662 | 661 | 117 |
| **Total** | **10.525** | **7.701** | **10.524** | **10.466** | **6.013** |

XI válido significa once IDs únicos, con el equipo correspondiente; no basta
que exista una clave `lineup`. Estadísticas detalladas significa que al menos
once registros de cada equipo incluyen un valor numérico de minutos; no implica
que todos los jugadores tengan todas las métricas. El archivo contiene 326.719
registros con minutos para estas doce ligas.

Las bajas son campos `unavailable`/`unavailability` del original: el conteo es
de partidos con información, no de personas ni de lesiones exclusivamente.
No se acredita que esa lista fuera exhaustiva o estuviera disponible antes
del partido; una ausencia de campo no equivale a cero bajas.

## Huecos de las competiciones con modelo

| Competición | Partidos verificados | Parejas xG | Ambos XI | Estadísticas de ambos equipos | Campos de bajas no vacíos |
|---|---:|---:|---:|---:|---:|
| Champions | 425 | 425 | 425 | 425 | 378 |
| Europa League | 441 | 441 | 441 | 441 | 341 |
| Argentina | 1.296 | 1.296 | 1.296 | 1.296 | 781 |
| Liga MX | 923 | 923 | 923 | 923 | 625 |
| Primeira | 845 | 845 | 845 | 845 | 660 |

Por tanto, los conteos de 5–24 partidos con xG reciente de API-Football y de
alineaciones en Postgres no describen todo lo que ya está disponible como
archivo. Importar estos datos exige todavía emparejar eventos y entidades.

La consulta actual de Postgres confirma `model_enabled=false` y
`captura_completa=false` para las doce ligas. Se mantienen los conteos de
resultados de tres años indicados por el usuario: Brasil B 222/3 parejas xG,
Chile 83/1; las otras diez sin xG. Los periodos y universos de Postgres y
FotMob difieren, por lo que no se suman como si fueran eventos disjuntos.
Brasil B y Chile tienen 1.066 y 662 resultados verificados en el archivo,
respectivamente; Chile sigue sin xG en esta fuente.

## Prueba actual SofaScore por ZenRows

Se reutilizó la cuenta existente y su cliente MCP, con límite de cuatro
solicitudes, reserva de 100 créditos, sin compras ni reintentos. Primer arranque
del MCP terminó antes de consultar; el segundo arrancó y comprobó la cuenta.
Luego se ejecutaron temporadas de Championship, eventos de su temporada y
estadísticas/alineaciones del partido seleccionado.

- Evento SofaScore `16391229`: Southampton–Portsmouth, 11-oct-2026 11:00 UTC.
- Torneo comprobado por respuesta: Championship, unique-tournament 18.
- Pareja xG del periodo `ALL`: **1,28 / 1,18**. Entradas duplicadas de grupos
  coinciden; no se mezclan con xG al arco ni con periodos parciales.
- Alineación confirmada: **11 titulares por equipo**, sin IDs duplicados.
- **40 fichas** con campos estadísticos, incluidas fichas de suplentes;
  29 tienen minutos positivos. No se afirma que jugaron los 40.
- **6 bajas declaradas** en el visitante, con códigos y descripciones;
  la lista del local está vacía en esta captura.
- Cuatro solicitudes correctas, originales y recibos con hashes verificados.
  Incremento observado de cuenta **20 créditos**: 1.804 → 1.824 de 5.000.
  Quedan 3.176 observados; no es un presupuesto autorizado para carga masiva.

Esto acredita acceso y contenido en una muestra de Championship; no acredita
la misma cobertura ni historia completa de las doce ligas. ZenRows fue el
transporte; no se acredita qué IP exacta utilizó. No se llamó API-Football
ni The Odds API para esta prueba.

Repositorio revisado y fijado para las rutas:
`tunjayoff/sofascore_scraper`, commit
`dd9f061be2c64f01a6d3a50fb34d55a102d7107b`.
El README y el LICENSE de ese commit indican PolyForm Noncommercial; versiones
anteriores conservan MIT. La URL raw de la rama principal mostró MIT desde una
caché antigua, por lo que se comprobó el archivo desde la API con ref fijo.
La prueba usó un adaptador propio hacia las rutas públicas, sin instalar ni
incorporar el código restringido del repositorio al producto. La licencia del
software no concede derechos sobre los datos del proveedor.

Fuentes primarias consultadas:
[repositorio](https://github.com/tunjayoff/sofascore_scraper),
[licencia en el commit fijado](https://github.com/tunjayoff/sofascore_scraper/blob/dd9f061be2c64f01a6d3a50fb34d55a102d7107b/LICENSE),
[ZenRows Fetch](https://docs.zenrows.com/fetch/api-reference).

## Siguiente integración y límites

Prioridad: importar primero los originales ya verificados de FotMob, resolver
los eventos faltantes de Brasil B/Chile y usar consultas SofaScore acotadas para
lo reciente o ausente. Algunas filas derivadas contienen nombres con caracteres
mal decodificados; las identidades deben salir del JSON original y cotejarse
con equipos/fechas/resultados de QuantFut, sin asociación difusa automática.

Cada fuente necesita su origen e instante real de captura. El xG FotMob fue
recibido el 3-oct; no estaba acreditado como disponible en cortes anteriores.
La protección actual nueva de xG trata explícitamente `api_football`: antes de
importar `fotmob`/`sofascore` se debe extender a estas fuentes. Las alineaciones
y bajas descargadas tras el partido se guardan como histórico, separadas de
las capturas previas; no se atribuye disponibilidad pasada.

Capturar más datos no elimina la puerta frente a Elo ni acredita mejora del
modelo. Un entrenamiento posterior debe validar sin fugas; las doce ligas
continúan deshabilitadas para el modelo y para captura completa. No hubo
importaciones, cambios de cron, activaciones ni modificación de predicciones.

Evidencia local: `.local/football_scraper_20261013/`, con `fotmob-audit.json`,
`database-baseline.json`, matrices CSV/JSON, árbol y fuentes fijadas del repo,
originales/recibos de `sofa-probe/` y `validated-summary.json`.
