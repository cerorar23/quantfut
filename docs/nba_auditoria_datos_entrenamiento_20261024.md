# NBA — auditoría de datos para entrenar todos los mercados (24-oct-2026)

Pregunta del titular: ¿ya está toda la data conectada para empezar a entrenar todos los mercados, props de jugador incluidos?
Medido sobre `apps/nba/.local` y lectura (sin cambios) del VPS. Cero créditos, nada desplegado.

**Respuesta corta: no toda.** Se puede empezar a entrenar ganador, puntos de equipo/total (sin cuotas) y los 4 props
principales (puntos, rebotes, asistencias, triples) con cuotas. El resto de mercados tiene la estadística pero no el
precio, o tiene la data cruda descargada pero no normalizada en el conjunto que leen los modelos.

## Lo que leen hoy los modelos
`normalized/nba_f6_run71_20261009/data/` (`players.jsonl.gz` + `games.json`), base de v1.1–v1.5 y del vivo:
- 157.962 filas jugador-partido, 6.108 partidos, 2021-22 a 2025-26 (~1.220/temporada), **solo temporada regular**.
- Columnas de jugador: puntos, rebotes, asistencias, triples, robos, tapones, minutos (130.380 con valor), participó, estado.
- Columnas de equipo: puntos, triples, robos, tapones. **No hay** tiros de campo/libres intentados, pérdidas, rebote
  ofensivo, faltas, posesiones ni marcador por periodo.
- Lesiones: 1.910 reportes T-60 (2023-24 a 2025-26, ≤1 h del corte en 99,8-99,9 %); 2021-22/2022-23 solo 13:30/17:30.

## Cuotas históricas disponibles
| Fuente | Contenido | Estado |
| --- | --- | --- |
| The Odds API h2h (`raw/nba_odds_h2h_202611`) | 325 snapshots diarios, 2024-25/2025-26, 15 casas EU + Pinnacle | Comprado el 23-oct (3.250 créditos); ya comparado (`nba_f6_market_20261101`): 2.407 partidos emparejados. |
| The Odds API props (`normalized/nba_props_odds_20261024`) | 893.165 filas, 2.421 partidos, 4 mercados, 8 casas EE. UU., una captura a T-30 | Unido a `player_id` al 99,99 %; 2.283 filas de no participantes. Comparado con v1 (peor que el mercado). |
| BetsAPI NBA (VPS `~/betsapi/data/nba`) | 3.996 eventos de mercados principales (ganador, hándicap, total), 29 `prematch` completos (props) | **No conectado**: no hay normalizador ni copia local; los props completos solo existen para los últimos ~30 días. |
| PropLine compartido (VPS `~/propline-shared`) | Captura horaria común, cierres, liquidaciones, box score y lesiones NBA | Activo (`current` → release `fc20390`, cron horario). El productor 1.3.1 lee sus líneas de puntos/rebotes/asistencias en vivo; es archivo prospectivo, no histórico para entrenar. |

## Matriz por mercado
| Mercado | Estadística | Cuotas históricas | ¿Entrenable ya? |
| --- | --- | --- | --- |
| Ganador | Sí (5 temp.) | h2h 2 temp. | **Sí** |
| Hándicap / margen | Sí (puntos de equipo) | No (solo BetsAPI sin conectar) | Solo contra resultado; falta modelo único del marcador |
| Total / puntos de equipo | Sí, pero sin posesiones/ritmo normalizados | No (totales planeados para diciembre) | Contra resultado sí; ritmo exige ampliar el normalizado |
| Medias partes / cuartos | No normalizado (PBP crudo existe) | No | No |
| Puntos, rebotes, asistencias, triples (jugador) | Sí | Sí, 2024-25/2025-26, una captura | **Sí** (anclado en el mercado) |
| Robos, tapones (jugador) | Sí | No | Solo contra resultado |
| P+R+A, P+R, P+A, doble-doble | Derivable del box | No | Solo contra resultado |
| Minutos / probabilidad de jugar | Sí (minutos + T-60) | — | Sí |
| Play-in, playoffs, Copa NBA | Crudo sí (sportsdataverse `season_type_id` 4/5/6, ~2.400 filas/temp.) | No | No: el normalizado los excluye |

## Huecos concretos, por orden de impacto
1. **El normalizado tira columnas que ya están en disco.** `player_boxscores_*.parquet` trae FGA/FTA/3PA, rebote
   ofensivo/defensivo, pérdidas, faltas y +/-; `gamelog_*.parquet` trae posesiones, ritmo y ratings. Sin ellas no hay
   modelo de ritmo × eficiencia ni puntos de jugador por 2P/3P/TL. Es trabajo local, sin coste.
2. **Playoffs/play-in fuera del conjunto** aunque están descargados.
3. **Sin cuotas de hándicap ni totales.** BetsAPI ya las tiene en el VPS; falta normalizar e identificar partidos.
4. **Props solo 4 mercados y una captura** (no cierre): robos, tapones y combinados sin precio.

Corrección (24-oct, tras revisar `main`): el productor 1.3.1 (PR #91) ya añade las filas de jugador de 2026-27 a la
historia (error 6), sella play-in/playoffs en vivo, lee PropLine y arregló las pruebas caducadas; esta auditoría se hizo
primero sobre una rama atrasada.

## Recomendación
Empezar ya, con protocolo congelado antes de correr, el **modelo de residuo de props anclado en el logit del mercado**
(4 mercados, entrena 2024-25, evalúa 2025-26) y la recalibración de equipo. En paralelo, ampliar el normalizado
(punto 1 y 2) antes del modelo único del marcador. Conectar BetsAPI solo si se quiere medir hándicap/total contra precio.
