# NBA: recuperación con servicios auxiliares — 5 de octubre de 2026

Se ejecutaron cinco capturas acotadas desde la cuenta Apify existente. La nueva versión de investigación incorpora **67 partidos y 1,713 filas jugador-partido**, conserva las 157,375 filas anteriores y queda en **159,088 filas**. La temporada regular del universo auditado pasa de 5,989 a **6,052 de 6,150 partidos (98.41%)**. La descarga no completa todo el histórico ni acredita rentabilidad del modelo.

## Capturas, coste y utilidad real

| Servicio / lote | Partidos | Registros guardados | Coste mostrado USD | Límite por ejecución USD |
|---|---:|---:|---:|---:|
| Flashscore: piloto de fechas 2025-10-22..23 UTC | 14 | 393 | 0.118 | 0.25 |
| Calendario NBA: piloto 2025-10-02 | 1 | 1 | 0.001 | 0.25 |
| Flashscore: pendientes 2025–26 | 146 | 4,468 | 1.302 | 2.00 |
| Calendario NBA: 2025-10-02..24 | 99 | 99 | 0.101 | 0.25 |
| Flashscore: pendientes 2023–24 / 2024–25 | 67 | 1,770 | 0.542 | 1.25 |
| **Total de esta ampliación** | | **6,731** | **2.064** | |

Los tres lotes Flashscore suman 227 eventos distintos y 6,631 registros únicos: 227 partidos y 6,404 filas de jugadores, incluidos suplentes que no participaron. Los dos lotes de calendario comparten el partido del piloto; el rango ampliado contiene 99 IDs únicos. No se debe sumar eventos de distintas fuentes como partidos nuevos.

El coste procede del importe mostrado por cada ejecución, no de una factura independiente. Se utilizaron créditos disponibles de la cuenta; no se contrató plan, recarga o programación. **Cero créditos de The Odds API**. El piloto Black Falcon anterior costó US$0.142 y no forma parte del total de US$2.064; ambas intervenciones suman US$2.206 mostrado.

Servicios empleados:

- [Flashscore Match Stats — incognito_mode](https://apify.com/incognito_mode/flashscore-match-stats-scraper): boxscores individuales con minutos decimales. Su utilidad se comprobó en estos lotes; no se presume fiabilidad general por estar en un marketplace.
- [NBA Scores & Schedule — rl1987](https://apify.com/rl1987/nba-api-scraper): calendario y resultados de origen NBA. No entrega boxscores individuales ni lesiones prepartido.

Se descartó ampliar servicios que ofrecen medias de temporada o minutos enteros: no solucionan el requisito de segundos individuales. Black Falcon/ESPN sigue conservado como fuente de contraste de P/R/A y calendario, sin inventar segundos.

## Qué se incorporó

| Competición | Partidos recuperados | Pendientes conocidos tras el lote |
|---|---:|---:|
| Temporada regular | 63: 61 de 2025–26, uno de 2024–25 y uno de 2023–24 | 98 |
| Playoffs | 3 | 0 del inventario actual |
| Play-in | 1 | 0 del inventario actual |
| Pretemporada | 0 boxscores completos | 71 |

Los ceros de playoffs/play-in se refieren a la lista de pendientes conocida, **no certifican un censo completo de todas las temporadas**. El denominador 6,150 solo corresponde a la regular del universo auditado.

Cada uno de los 67 partidos se volvió a conciliar íntegramente desde los originales. Hay 1,470 participantes y 243 no participantes corroborados en las nuevas filas. Las 1,400 comparaciones con relojes previos válidos coinciden al segundo. Se conservaron estadísticas, identidad, contexto, origen, hash y método de reconstrucción de minutos por fila.

Versión nueva: `apps/nba/.local/normalized/flashscore/final_v2_20261005/player_games.jsonl.gz`.

SHA-256: `f10b5e8e5dc8ba7dc85dac184fdf90ac25c17b64fe48a7e14b00f5d8885a13fd`.

La versión previa de Basketball Reference sigue intacta. El modelo no se reentrenó y ninguna puerta G0–G9 fue promovida.

## Calendario y pretemporada

El rango NBA descargado contiene los **71 IDs de pretemporada pendientes** y 28 regulares. Cada partido tiene IDs canónicos, equipos, marcador final y parciales. Se verificaron unicidad, estado final, suma de cuartos/prórrogas y fechas. Cinco partidos presentan diferencias frente a la referencia anterior: cuatro discrepancias de localía y dos de marcador, contadas por registro de equipo. Se documentaron en el informe y no se sobrescribieron las referencias automáticamente.

El proveedor etiqueta `dateEastern` con `Z` aunque su contenido es hora de pared del Este. Se conservó ese valor raw y se usa `dateUtc` convertido con `America/New_York` para instantes y fechas. En sedes neutrales, la asignación NBA de home/away no implica ventaja física de local.

Ya se guardaron boxscores Flashscore de 62 de los 71 candidatos de pretemporada. Siguen separados porque faltan cruces inequívocos de jugadores o conciliación de referencias. Nueve no encontraron candidato en el calendario Flashscore. Descargar un candidato no equivale a aceptar el partido.

## Criterios y registros rechazados

De 227 eventos Flashscore, 67 se incorporaron, 11 ya tenían datos aceptados y 149 quedaron separados por el primer control que falló. Un mismo partido puede tener más problemas que el primer motivo registrado.

- Identidad única por NBA ID, partido y equipo. Nombres completos, acentos y puntuación se normalizan; no se empareja por similitud o por estadísticas.
- Tres alias revisados con páginas oficiales NBA e IDs canónicos: Bones/Nah’Shon Hyland, Bub/Carlton Carrington y Nigel Hayes/Nigel Hayes-Davis. La lista y enlaces exactos están en `identity_aliases.json`.
- Cuando hace falta, se exige una plantilla ESPN del mismo partido/equipo, nombre NBA, dorsal único, apellido e inicial corroborados. Los namespaces ESPN, Flashscore y NBA se mantienen explícitos.
- Puntos, rebotes y asistencias de cada participante deben coincidir con la referencia NBA previa. Deben coincidir fecha, localía y marcadores; ningún participante conocido se omite, aunque tenga cero P/R/A.
- Los minutos decimales se interpretan conforme al README del servicio como minutos fraccionarios redondeados a dos decimales. Se exige un único segundo entero compatible; por ejemplo, 38.57 representa 38:34. **No se capturó el reloj MM:SS original de Flashscore**: esta interpretación permanece como supuesto documentado.
- Todos los relojes NBA previos válidos deben coincidir. No se reparan cadenas como `33:60`, ni se distribuye un error entre jugadores. Las discrepancias de uno o más segundos permanecen separadas.

Existe un contraejemplo real en el piloto WAS–MIL: errores individuales de +41 y −41 segundos se cancelan en el total de equipo. Por eso conservar 240 minutos por equipo no basta para validar minutos individuales.

Los recibos actuales son posteriores al partido: sirven para resultados retrospectivos. No demuestran qué se sabía antes del salto inicial. `first_received_at_utc` es el momento local de guardado completo del original, nunca una fecha histórica inventada. La disponibilidad prepartido original permanece desconocida.

## Auditoría y continuación

Originales, entradas efectivas, páginas JSON, planes, logs, screenshots y recibos están en `apps/nba/.local/raw/apify/services_20261005/`. Las 34 páginas Flashscore se cotejaron contra los tres JSON completos, sin páginas faltantes o claves duplicadas. El informe de verificación vuelve a comprobar cada partido aceptado y aplica 17 controles adversariales, incluidos cambio de P/R/A, identidad duplicada, participante omitido, relojes intercambiados, fecha/localía/marcador incorrectos y precisión inválida.

Los scripts y la configuración se congelan en snapshots; se comprobaron los hashes de las 139 evidencias anteriores y los 39 archivos de código NBA congelados. El registro de fases y la cadena SQLite reciben una nueva entrada de investigación. La cadena local detecta modificaciones; no constituye un sello externo de tiempo ni revisión independiente.

Pendiente para una próxima recuperación: resolver identidades/referencias de los 98 regulares y 71 boxscores de pretemporada; obtener lesiones con publicación histórica y recibo verificable; actualizar plantillas actuales; reconstruir rotaciones/PBP; capturar cuotas históricas de props con líneas, casa, precio y hora. Ninguno de esos conjuntos se sustituye por DNP o por estadísticas posteriores. No ampliar capturas masivas de la misma fuente mientras el problema sea identidad, precisión o desacuerdo ya observado.
