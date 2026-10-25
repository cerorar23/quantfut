# Cobertura por liga con PropLine + SofaScore (rl1987) — 25 de octubre de 2026

Consultas reales del 25-oct: PropLine (36 competiciones, eventos, mercados, `/scores`, `/stats`), SofaScore
`rl1987/sofascore-api-scraper` (detalle de partidos actuales y de temporadas pasadas) y la base de producción
(solo lectura, partidos terminados desde el 1-ene-2024). Las muestras de SofaScore son de 2 a 24 partidos por
liga y temporada: sirven para saber si el dato **existe**, no para dar un porcentaje exacto.

Fuentes vigentes (decisión del titular del 25-oct): PropLine y SofaScore. FotMob y API-Football ya no se usan;
su archivo histórico sigue en la base (`historical_football_*`) y se puede usar.

## Decisión del titular (25-oct-2026, misma tarde)

Se quedan 15 ligas y 2 copas: Premier, LaLiga, Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira, Brasil, Liga MX,
MLS, Championship, 2. Bundesliga, Turquía, Noruega, Argentina, Champions y Europa League. Se retiran Serie B, LaLiga 2,
Allsvenskan y Super League suiza (db/088), además de Ligue 2 y Dinamarca (db/086). No se borra el historial.

FotMob vuelve como **complemento diario** (orden del titular): referencias, previos y posteriores en las competiciones
activas, y una pasada a las 09:15 UTC (`fotmob_captura completar`) que rellena en `matches` lo que SofaScore y PropLine
dejaron vacío en partidos de hace más de 36 h, solo NULL y con el mismo marcador. Championship, 2. Bundesliga,
Turquía y Noruega entran en el recolector SofaScore (antes solo estaban las 13 ligas con modelo).

## Qué rellena cada fuente

| Dato | Base hoy (desde 2024) | PropLine | SofaScore (rl1987) |
|---|---|---|---|
| Goles, tiros, tiros a puerta, córners, amarillas | 99–100 % (Argentina 86 %, copas 93–98 %) | `/stats` desde abr-2026, ~1 h tras el final | Sí, todas las temporadas probadas |
| Faltas, fueras de juego, paradas | Columnas canónicas solo en 1.521 partidos; el archivo FotMob los tiene en casi todos desde 2024 | Sí (por jugador y equipo), desde abr-2026 | Sí, todas las temporadas probadas |
| Asistencias, goles por jugador | `estadisticas_jugador` solo en 11 ligas (~40 %) | Sí, desde abr-2026 | Sí (≈80 métricas por jugador, xG/xA incluidos) |
| xG | 100 % salvo Serie B 44 %, LaLiga 2 82 %, Ligue 2 84 %, Argentina 86 % | **No tiene** | Casi todas las ligas; ver excepciones abajo |
| Árbitro | 72–100 % (Liga MX 72 %, Serie B 76 %, Brasil y Suecia 82 %) | No | Sí, en todas las ligas probadas salvo Eerste Divisie |
| Incidencias (minuto de goles y tarjetas, cambios) | No hay tabla canónica | No | Sí |
| XI y jugadores **posteriores** al partido | Archivo FotMob ~100 % desde 2024 hasta ~20-sep-2026; no integrado | No | Sí, también de temporadas pasadas |
| XI **antes** del inicio | 0–7 % | No | Solo hacia delante (captura cada 10 min desde el 25-oct) |
| Bajas con motivo | Archivo FotMob 60–90 % (Ligue 2 10 %, Noruega 41 %, Suecia 46 %, MLS 50 %), capturadas tras el partido | No (404 en fútbol) | Solo partidos recientes: en 13 partidos de 2024-25 devolvió 0 bajas |

Conclusión: **combinadas sí rellenan** los 20 tipos de estadística, el árbitro, las incidencias y el XI de los
partidos pasados. El hueco que **no** se puede rellenar hacia atrás es todo lo que tenía que conocerse **antes**
del partido (XI previsto y bajas): eso solo existe desde que lo capturamos nosotros (point-in-time).

### xG: dónde el hueco se puede cerrar y dónde no

| Hueco en la base | Partidos | SofaScore | Resultado |
|---|---:|---|---|
| Serie B, ago-2024 → may-2025 (temporada 63812) | ~390 | xG 3/3 | **Recuperable** |
| Serie B, ene → jun-2024 (temporada 52947) | ~200 | Sin xG 0/2 | Permanente |
| LaLiga 2, ago → dic-2024 (62048) | ~230 | Sin xG (0/3 en oct-2024 y 0/2 en mar-2025) | Permanente |
| Ligue 2, ago → dic-2024 (61737) | ~145 | Sin xG (0/3 y 0/2) | Permanente |
| Argentina, ene → abr-2024 (Copa de la Liga) | ~200 | Sin probar | Pendiente; peso bajo por antigüedad |

Hacia delante, sin FotMob ni API-Football:

- **Ligue 2:** SofaScore no da xG en la temporada actual (0/5) ni bajas.
- **LaLiga 2:** xG intermitente (0/5 en una muestra y 3/3 en otra).
- **Suecia:** xG de equipo sí; el xG de jugador falla a menudo (2/7).
- **Argentina:** muestras de 6/21 y 3/3; la base tiene 26/30 en mayo-2026.

## Cuándo llega cada dato (medido)

| Dato | Llega | Consecuencia |
|---|---|---|
| PropLine `/stats` | ~1 h después del final (≈2,9 h tras el inicio); a 1,9 h el partido ya era `final`, con 0 filas | Utilizable desde ~3 h después del inicio |
| PropLine sin resultado (`expired`) | Suiza 3 de 3; Noruega, Turquía, Bélgica y MLS 1 cada una | En Suiza los resultados y estadísticas tienen que salir de SofaScore |
| SofaScore, detalle post-partido (nuestro recolector) | Mediana 12,3 h, p90 19,2 h, máximo 33 h tras el inicio; quedan 22 partidos terminados sin capturar | Llega antes del siguiente partido del equipo salvo con calendario muy apretado |
| xG | Los proveedores lo revisan días después | Se mantiene la regla: primera pareja válida congelada con su hora de recepción |
| SofaScore, once previsto y bajas | Mediana 11,6 h antes del inicio (entre 30 h y 7 h) | Puede entrar en una predicción hecha la víspera |
| SofaScore, XI oficial confirmado | Entre 65 y 29 min antes (mediana ~45 min) | Solo sirve para una predicción hecha en la última hora |

Regla para entrenar: cada valor se usa **desde su hora de recepción real**, no desde el inicio del partido. Un dato
capturado tarde sirve como antecedente de partidos posteriores, nunca para el partido al que pertenece. El
archivo FotMob de bajas y XI se capturó después de los partidos: vale como historia, no como información previa.

## Recomendación por liga

Todas tienen goles suficientes para Dixon-Coles (543 a 1.548 partidos terminados desde 2024 y más de 2.300 desde
2014). Lo que decide es si se puede **operar**: cuotas de PropLine (fuente fija) y datos que sigan llegando sin
FotMob ni API-Football.

| Liga | Recomendación | Motivo |
|---|---|---|
| Premier, LaLiga, Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira, Brasil, Liga MX, MLS, Champions, Europa League | **Se quedan** | Cuotas completas en PropLine (20–36 claves), xG y XI en SofaScore, estadísticas en las dos |
| Championship, 2. Bundesliga, Turquía, Noruega | **Se quedan** | xG 100 % en la base y en SofaScore; PropLine sin props de jugador (no hacen falta para el modelo) |
| Argentina | **Se queda** | xG presente en lo reciente; vigilar la tasa de xG de SofaScore |
| Serie B | **Se queda** si se recupera la temporada 2024-25 desde SofaScore | Hoy tiene 44 % de xG; con la recuperación sube a ~80 % y lo actual llega con xG |
| Suecia | **Se queda**, sin variables de xG por jugador | xG de equipo bien; xG de jugador irregular |
| Suiza | **Se queda solo si los resultados salen de SofaScore** | PropLine tiene cuotas, pero no da resultados ni estadísticas (3/3 `expired`) |
| LaLiga 2 | **En observación** 4 jornadas; si el xG de SofaScore baja del 80 %, se retira | Hueco permanente en ago-dic 2024 y xG intermitente hacia delante |
| Ligue 2 | **Quitar** | Sin cuotas en PropLine, sin xG en SofaScore (0/5 actual, 0/5 en 2024-25), sin bajas. Ya está `active=false` |
| Superliga de Dinamarca | **Quitar** | Sin cuotas en PropLine: no se puede vender ni comparar con el mercado. SofaScore sí tiene datos. Ya está `active=false` |

"Quitar" aquí significa dejar de capturar y de entrenar, no borrar el historial. El borrado físico (como el de
Chile y Brasil B el 13-oct) solo con confirmación expresa del titular.

Ligas que **no** están en el catálogo y que tienen las dos fuentes (cuotas en PropLine, y xG, XI y árbitro en
SofaScore 3/3): Escocia, Bélgica, Grecia, Arabia Saudí, J1, A-League, Conference League, Libertadores y
Sudamericana. Ninguna tiene historial en la base: entrarían sin muestra propia. La DFB-Pokal no tiene xG (0/3).
No se verificaron J2 ni League Two: el id de torneo que se probó era el de otra competición.

## Trabajo para cerrar los huecos (por orden)

1. **Integrar el archivo FotMob ya guardado** (sin peticiones nuevas) en las columnas canónicas: faltas, fueras
   de juego, paradas, árbitro, XI y jugadores 2024 → 20-sep-2026. Es el mayor salto y no cuesta nada.
2. **Recuperar desde SofaScore el hueco que dejó FotMob**: del ~20-sep-2026 al 25-oct en las 21 ligas
   (~950 partidos, ~6 USD a 0,006 USD/partido), y la Serie B 2024-25 (~390 partidos, ~2,3 USD). Repartir en
   varios días por el tope mensual de Apify (15 USD).
3. **Resultados de Suiza desde SofaScore**, porque PropLine no los da.
4. **Medir 4 jornadas de LaLiga 2** y decidir.
5. No reentrenar ni promover nada solo por haber capturado: cualquier modelo nuevo pasa por la evaluación
   habitual.

Gasto de esta consulta: ~1,5 USD en Apify (incluida la consulta anterior del mismo día) y ~750 peticiones de
PropLine del cupo diario compartido (5.000).
