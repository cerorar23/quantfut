# Cuotas históricas de tenis, NBA y fútbol: BetsAPI y PropLine (2026-10-23/24)

Estudio sin fines de lucro del motor de tenis y mejora de NBA/fútbol. Los datos viven solo en el VPS (`qf@31.220.72.30`); no hay copia ni van al repo. Las claves están en `~/quantfut-tenis/secrets/.env.betsapi`, `.env.propline2` y copias en `~/betsapi/` (permisos 600); no se guardan aquí.

## BetsAPI (plan «Everything» de un día, comprado el 23-oct; 1.800 peticiones/hora)
- Descargador reanudable `scripts/betsapi_descarga.py` (respuestas crudas en gzip; lo existente no se vuelve a pedir). Cola en `~/betsapi/cadena2.sh`, registro `~/betsapi/descarga.log`, datos `~/betsapi/data/{nba,tennis,football}/{list,odds}`.
- Medido: tenis solo `13_1` (ganador) y `13_4` (ganador del set en curso, deducido) para ATP/WTA/Challenger/ITF, con movimiento; histórico desde 2022 como mínimo. NBA: 9 mercados de equipo (`18_1`..`18_9`) desde 2021. Fútbol: `1_1`..`1_8`. NBA league_id = 2274.
- Props de jugadores NBA: solo partidos futuros (`/v4/bet365/prematch`); partidos terminados devuelven vacío. No hay histórico de props.
- Ids de fútbol usados (verificados): ver `~/betsapi/ligas.json` (23 competiciones; faltan La Liga/Serie B alternativas duplicadas descartadas: Eredivisie 24792 y Süper Lig 215 devuelven 0).
- Lo que ya había en la base: ganador (1X2) de 89.746 partidos desde 2012 (football-data). Totales y hándicap solo en 439 partidos recientes. BetsAPI aporta esos mercados con movimiento.
- Licencia: términos de uso de BetsAPI **no leídos**; el uso es el de estudio propio.

## PropLine (plan Hobby: 5.000 peticiones/día, histórico visible de 30 días)
- Captura `scripts/propline_captura.py`: cron del usuario `qf` cada 2 h (`40 */2 * * *`), cierre de Pinnacle/Bovada/Matchbook/Kalshi (+DraftKings/FanDuel) de tenis ATP/WTA/Challenger, NBA (con props) y 14 ligas de fútbol; datos en `~/propline_data`, tope propio 4.000/día.
- Archivo desde abril de 2026 (Pinnacle: tenis desde 12-jul, props de tenis desde 1-oct; NBA partidos desde 19-abr, props desde 20-oct). No hay temporadas anteriores.

## The Odds API: props NBA históricos
- Probado con un partido de 2024-03-15 (`player_points`, región `us`): devuelve líneas y cuotas de 4 casas; 10 créditos por mercado y región + 1 por consulta de calendario. Una temporada con 4 mercados serían ~49.000 créditos. Saldo real al probar: 160.

## Otras fuentes revisadas (sin comprar)
Apify `sports-odds-lab/tennis-odds-results` (tenis desde 2009, totales/hándicap/marcador de sets, sin Pinnacle, ~5 USD por 1.000 partidos), ParlayAPI, SportsData.io, odds-api.io, SportsGameOdds, TheRundown: sin confirmar histórico de props.
