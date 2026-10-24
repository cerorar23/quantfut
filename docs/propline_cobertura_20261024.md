# Cobertura real de mercados en el archivo de PropLine — 24 de octubre de 2026

Medición de solo lectura del archivo horario compartido (`quantfut_artifacts/propline_shared`,
leído desde `quantfut-worker-1` con `index.sqlite` en `mode=ro`; el servidor no se tocó).
Ventana: recepciones del 23-oct 23:15 al 24-oct 04:17 UTC, 674 respuestas (667 con 200 y 7 con
504). Son unas cinco horas: sirve para saber **qué mercados existen**, no para afirmar
cobertura continua. Solo cuentan los partidos previos al inicio (`live=false`) y el partido
completo, salvo que se indique un periodo.

"Cerca" = empieza en las 36 h siguientes a la última recepción; "lejos" = después. Las casas
publican córners, tarjetas y props de jugador sobre todo cuando se acerca el partido, así que la
columna que importa es "cerca".

## Fútbol (ligas del modelo y copas)

Partidos cerca con el mercado / de ellos con Pinnacle.

| Liga | Cerca | 1X2 | Totales | Hándicap | BTTS | Doble op. | Córners tot. | Córners equipo | Tarjetas tot. | Tarjetas equipo | Goles equipo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Premier League | 8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 8/8 | 0 |
| LaLiga | 6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 | 6/4 | 6/4 | 0 |
| Serie A | 7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 0 |
| Bundesliga | 7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 0 |
| Ligue 1 | 7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/6 | 6/6 | 7/7 | 7/7 | 0 |
| Primeira Liga | 4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 3/0 | 0 | 0 |
| Liga MX | 3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/0 | 0 | 0 |
| Brasileirão | 7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 7/7 | 0 |
| Argentina | 4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/0 | 4/0 | 0 |
| MLS | 14 | 14/14 | 14/14 | 14/14 | 14/12 | 14/14 | 14/14 | 14/14 | 14/14 | 14/14 | 0 |

Champions y Europa League no tenían partidos cerca. Lejos, Champions trae 1X2, totales,
hándicap y doble oportunidad con Pinnacle en 18 partidos y córners totales sin Pinnacle; Europa
League, 1X2, totales y hándicap con Pinnacle, sin córners ni tarjetas. Hay que remedirlas en
semana de copa.

Además existen en casi todas las ligas: resultado exacto, primer equipo en marcar, margen de
victoria, hándicap europeo, sin empate, combinados (resultado+goles, BTTS+goles), goleador, tiros
y tiros a puerta de jugador, y periodos `h1`/`h2`.

**Goles por equipo (`team_totals`) no existe en PropLine**: no está en `openapi.json` ni en
`prop-line.com/docs`, y no aparece en ninguna respuesta. La escalera usa ese mercado; su precio
de mercado tiene que salir de otra fuente o el escalón queda sin `prudente`.

## NBA

| Mercado | Cerca (8 partidos) | Con Pinnacle | Lejos (56) |
|---|---|---|---|
| Moneyline / hándicap / total | 8 / 8 / 8 | 4 | 56 / 20 / 18 |
| Puntos, rebotes, asistencias, triples y PRA de jugador | 2 | 0 | 0 |

Sobre todo el archivo (incluidos los partidos ya jugados del 23-oct), los props de jugador
aparecen en 8 partidos y Pinnacle los da en puntos y asistencias en 6 de ellos. Los 8 partidos
"cerca" empiezan unas 19 h después de la medición, y las casas suelen publicar los props el día
del partido: **los 2/8 no prueban falta de cobertura**. Hay que remedirlo con el primer sellado
real del productor 1.3.1 (`prop_lines.state = archivo_aplicado`). Hay además cuartos, mitades,
dobles-dobles, primer enceste y escalones de puntos (10+, 15+). 104 casas en total, incluidas
bolsas de predicción (Polymarket, Kalshi) que el productor ya excluye.

## Tenis

147 partidos cerca, 49 casas. Ganador 147 (Pinnacle en 92); hándicap de juegos 109/92; total de
juegos 107/92; total de sets 101/89; juegos ganados por jugador 92/89; aces de jugador 18 (sin
Pinnacle); ganador del 1.er y 2.º set y totales por set. El motor de tenis todavía no lee este
archivo; lo está conectando otra sesión (`tenis/propline-cuotas`).

## Conclusiones

- Para fútbol, PropLine trae Pinnacle en 1X2, totales, hándicap, BTTS, doble oportunidad y
  córners en las diez ligas, y tarjetas con Pinnacle en seis. Tarjetas sin Pinnacle en Primeira,
  Liga MX y Argentina.
- Hueco firme: goles por equipo. Huecos por confirmar: props NBA el día del partido, y
  Champions/Europa League en semana de copa.
- Segunda División, Serie B, Ligue 2 y Superliga danesa siguen sin catálogo (ver
  `docs/propline_compartido_20261023.md`).

Script de medición: un `python -` dentro del worker que abre `index.sqlite` en solo lectura,
recorre `receipts` con estado 200 de `/v1/sports/*/odds` y descomprime los objetos.
