# NBA — estudios de partida y matriz por mercado antes de entrenar (24-oct-2026)

Sustituye la matriz de `nba_auditoria_datos_entrenamiento_20261024.md`. Medido en `apps/nba/.local` y en solo lectura sobre el VPS
(`~/betsapi/data/nba`, `~/sofascore-apify`, `~/propline-shared`). Cero créditos gastados, ninguna corrida de Apify, nada desplegado.

## 1. Los estudios con los que se diseñó el motor (`nba_2026_27_investigacion_y_plan.md`)

| Estudio | Qué aporta | Qué dato exige | ¿Lo tenemos? |
| --- | --- | --- | --- |
| Cervone (Harvard 2015, tesis) y Cervone et al. (JASA 2016): valor esperado de la posesión | Procesos estocásticos multirresolución del estado del juego | Tracking a 25 Hz | No. Solo PBP y tiros con coordenadas (`shotdetail`) |
| Huang (UC Merced 2018, tesis) y Bhat-Huang-Rodriguez: Markov de sustituciones | Minutos y rotaciones como cadena de cambios de quinteto | PBP con sustituciones | Sí: PBP shufinskiy 1996-2025 y stints cronológicos |
| Alameda-Basora (Iowa State 2019): red bayesiana del total en vivo | Actualizar el total al final de Q1/Q2/Q3 | Marcador por cuarto + cuota viva | Marcador por cuarto sí (BetsAPI y PBP); cuota viva solo la de BetsAPI, de una casa |
| Paul-Weinbach-Wilson (2004): eficiencia de los totales | Los totales son casi eficientes: el mercado es el baseline exigente | Cierres del total | Sí, bet365 vía BetsAPI (3 temporadas) |
| Skinner (PLOS ONE 2012), Adams-MacKay (2007, cambios de régimen), Howard et al. (2021, secuencias de confianza) | Selección de tiro, cambio de rol, lecturas repetidas sin sesgo | Series de tiros y de minutos | Sí |
| Hubáček-Šír: pérdida orientada al mercado | Un modelo anclado en el mercado, no sustituto | Cuotas con línea real | Sí para 4 props y h2h |
| Conformal (Gibbs-Candès, CQR), SBC (Talts), ensembles y calibración (Guo, Lakshminarayanan) | Intervalos y calibración medidos fuera de muestra | Predicciones sellables | Sí |
| Descanso, viaje y huso (PMC 2022) | Features de calendario, con ablación | Calendario y sedes | Sí |

Lo que la investigación dejó fijado antes de medir: prioridad rebotes y asistencias, puntos como brazo paralelo; totales y periodos en la
segunda fase; robos, tapones, primer anotador y combinados **solo si hay evidencia y datos propios**; un criterio económico
(límite inferior del IC95 del EV > 0) que necesita ≥ ~7.900 apuestas para detectar un ROI de 3 %, así que 300 partidos no certifican nada.
Lo medido después coincide: el v1 de jugador pierde contra el mercado y la lesión ya no mueve a los equipos, de modo que el camino que
sostiene la literatura (Hubáček-Šír) es un residuo anclado en el logit del mercado.

## 2. Qué trae cada fuente que indicaste

| Fuente | Rol | Histórico para entrenar |
| --- | --- | --- |
| **PropLine** (`prop-line.com/docs`, `api.prop-line.com/docs`) | Cuotas en vivo y futuras: moneyline, hándicap, total, puntos/rebotes/asistencias/triples/robos/tapones/pérdidas/combinados, doble-doble, primer enceste, cuartos y mitades; cierres, liquidación y box score | **No.** Hobby ve 30 días (Pro 90). Nuestro archivo parte de abril de 2026 (partidos) y del 20-oct (props). Es el insumo prospectivo del productor, no un histórico de temporadas |
| **Apify / SofaScore** | Box score por jugador y por cuarto, uso, plus-minus, bajas. Estadística, no cuotas | Solo lo que ya archiva el recolector del VPS (484 KB). `azzouzana/sofascore-scraper-pro` está **roto** (probado el 23-oct); el que funciona es `rl1987/sofascore-api-scraper`. Saldo de la cuenta Apify: 4,64 de 5 USD hasta el 5-nov, así que no hay presupuesto para un histórico ahora |
| BetsAPI (`~/betsapi/data/nba`) | 3.996 partidos 2023-24..2025-26 (+23 de 2026-27) con el movimiento completo de bet365 | **Sí** |
| The Odds API h2h (Pinnacle + 14 casas EU) y props (8 casas de EE. UU.) | Comprados el 23 y 24-oct | **Sí** |

## 3. Cuotas históricas de NBA realmente disponibles

- **BetsAPI, bet365, 3 temporadas, con apertura y cierre** (cada fila lleva `add_time`; el 99,97 % de los partidos tiene filas previas al salto):
  `18_1` moneyline, `18_2` hándicap, `18_3` total del partido; `18_4`-`18_6` moneyline/hándicap/total de la **primera mitad**;
  `18_7`-`18_9` de **Q1**. Identificado con las líneas: mediana previa del total 227,5 contra 228,1 reales; primera mitad 114,5 contra 114,3; Q1 57,5 contra 57,3.
  También hay marcador por cuarto y final en cada evento. Las filas en vivo (`ss` no vacío) sirven al modelo de totales de Alameda-Basora.
- **The Odds API h2h**: 325 fotos diarias (2024-25, 2025-26), Pinnacle incluida; 2.407 partidos emparejados.
- **The Odds API props**: puntos, rebotes, asistencias y triples, 893.165 filas, una captura a T-30 min, solo casas de EE. UU.

## 4. Matriz por mercado (cuota histórica = sí/parcial/no; entrenable = con precio / contra resultado / no)

| Mercado | Resultado para entrenar | Cuota histórica | Estado |
| --- | --- | --- | --- |
| Ganador | Sí (5 temporadas) | Sí: bet365 (3 temp.), Pinnacle y 14 casas (2 temp.) | **Con precio** |
| Hándicap del partido | Sí | Sí: bet365 (3 temp.), con cierre | **Con precio** (falta normalizar; los modelos actuales no lo usan) |
| Total del partido | Sí | Sí: bet365 (3 temp.) | **Con precio** (falta normalizar) |
| Puntos de cada equipo | Sí | **No** (BetsAPI no lo trae; PropLine solo hacia delante) | Contra resultado |
| Primera mitad: ganador, hándicap, total | Falta derivarlo del marcador por cuarto | Sí: bet365 (3 temp.) | **Con precio** tras derivar el resultado |
| Q1: ganador, hándicap, total | Ídem | Sí: bet365 (3 temp.) | **Con precio** tras derivar el resultado |
| Q2, Q3, Q4 y segunda mitad | Derivable de PBP/marcador | **No** | Contra resultado |
| Total en vivo entre cuartos (Alameda-Basora) | Marcador por cuarto | Parcial: filas en vivo de una casa | Exploratorio |
| Puntos, rebotes, asistencias, triples de jugador | Sí | Sí: 8 casas de EE. UU., 2 temp., una captura T-30 (sin cierre) | **Con precio** |
| Robos, tapones, pérdidas de jugador | Sí (extendido) | **No** | Contra resultado |
| PRA, P+R, P+A, R+A, doble-doble, triple-doble | Derivable del box | **No** | Contra resultado |
| Escalones de puntos (10+, 15+), primer enceste, líneas alternativas | Parcial (primer enceste desde PBP) | **No** | Contra resultado o nada |
| Minutos y probabilidad de jugar | Sí (minutos + reportes T-60) | n/a | Entrenable |
| Playoffs y play-in | Sí desde 2022-23 (normalizado ampliado, `count_source` aparte) | BetsAPI incluye partidos de playoffs de las 3 temporadas; props de Odds API no verificados para playoffs | Parcial |

## 5. Respuesta a «¿toda la data y las cuotas históricas están completas?»

**No.** Qué se puede entrenar ya con precio: ganador, hándicap, total, primera mitad y Q1 (bet365, 3 temporadas) y los cuatro props
principales (2 temporadas, T-30). Todo lo demás se puede entrenar y calibrar contra el resultado real, pero sin precio histórico; ahí la
vara de medir es la calibración (Brier, cobertura de rangos), como pidió el titular el 23-oct, no ganarle a una cuota que no tenemos.

Huecos que ninguna de las fuentes indicadas cierra:
1. Cuotas históricas de props fuera de los 4 mercados, de robos/tapones/combinados y de cualquier mercado de cuartos 2-4.
2. Cierre real de props (solo hay una foto T-30). PropLine entrega cierres, pero solo desde que lo capturamos.
3. Cuotas de puntos de cada equipo.
4. Un histórico de SofaScore: el actor que nombraste está roto y el presupuesto de Apify no alcanza.
5. Varias casas por partido en BetsAPI: solo bet365 (el consenso multicasa solo existe para h2h y los 4 props).

Hecho después (24-oct): BetsAPI quedó normalizado y unido a `game_id` (34.713 filas, 3.867 partidos; `nba_cuotas_betsapi_normalizadas_20261024.md`).
Con él, ganador, hándicap, total, primera mitad y Q1 pasan a «con precio» para 2023-24..2025-26. BetsAPI lista primero al visitante como
«home»; el normalizado ya reorienta cada fila al local oficial. Pendiente sin coste: derivar los resultados de Q2-Q4 y validar el PBP
contra el calendario (`validated_against_schedule: false`).

## 5b. Qué captura PropLine hoy (medido el 24-oct en el archivo del servidor, ~21 h, 166 respuestas de NBA, 80 partidos)
- 104 casas, de tres tipos: casas con cuota de dos lados (incluida Pinnacle), 5 de fantasy/DFS (Dabble, Pick6, PrizePicks, Sleeper,
  Underdog) y mercados de predicción (Polymarket, Polymarket US, Kalshi, Novig, ProphetX). Estos dos últimos grupos no son precio y se excluyen.
- Equipo: ganador (`h2h`), hándicap (`spreads`) y total (`totals`), con periodos `h1`, `h2` y `q1`..`q4`; primer encesto y primer tiro anotado de equipo.
  Solo ~40 de los 80 partidos traen hándicap y total (los lejanos no).
- Jugador (20 claves, 14 partidos, los del día): puntos, rebotes, asistencias, triples, robos, tapones, pérdidas, robos+tapones, P+A, P+R, R+A,
  P+R+A, doble-doble, triple-doble, puntos 10+/15+, primer encesto y primer tiro anotado. Más props: DraftKings 15, FanDuel 16, Hard Rock 14,
  BetRivers y Unibet 13, Novig 12, Fanatics 11, Courtside 10, Bovada 9, BetMGM y ProphetX 8.
- **Pinnacle**: ganador, hándicap, total, puntos y asistencias de jugador, en 14 partidos. Sin rebotes, triples, robos ni tapones.

## 5c. Continuidad pasado → futuro por mercado
No hace falta una casa con todo: hace falta una fuente que sea la misma antes y después, por mercado. Ganador: Pinnacle (The Odds API →
PropLine). Hándicap, total, mitad y Q1: bet365 (BetsAPI histórico → fotos horarias de BetsAPI en el VPS, mientras siga el plan). Props de
puntos, rebotes, asistencias y triples: consenso de 6 casas de EE. UU. presentes en los dos lados (Bovada, BetRivers, BetMGM, DraftKings,
FanDuel, Fanatics). La referencia es un consenso sin margen con la casa marcada en cada fila; Pinnacle va como serie aparte.

## 6. Orden recomendado para entrenar
1. ~~Normalizar BetsAPI~~ (hecho): lo de equipo con precio ya está listo.
2. Props: residuo anclado en el logit del mercado, entrenado en 2024-25 y evaluado en 2025-26, protocolo congelado antes.
3. Equipo: recalibración móvil del total, hándicap y primera mitad con bet365 como referencia; modelo único del marcador después.
4. Robos, tapones y combinados: solo calibración contra resultado, hasta que PropLine acumule cierres propios.
