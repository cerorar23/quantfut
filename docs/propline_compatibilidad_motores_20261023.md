# PropLine frente a los motores de fútbol, NBA y tenis

23-oct-2026. Fuentes: `https://prop-line.com/llms-full.txt` (actualizado 24-oct), `https://api.prop-line.com/openapi.json`
(46 rutas) y el archivo piloto real `.local/propline_shared_pilot_20261023` (436.731 cotizaciones, todas con precio;
59 % con `player_id`). La clave demo pública ya había agotado su cuota diaria (HTTP 429), así que no se hicieron
consultas nuevas: todo lo "observado" sale del piloto.

## Veredicto por motor

| Motor | ¿Compatible para cuotas? | ¿Sustituye sus datos estadísticos? |
|---|---|---|
| Fútbol | Sí, en 1X2, totales, hándicap, BTTS, doble oportunidad, córners, tarjetas, totales por equipo. | No. Box score sin xG, sin alineaciones previas, sin lesiones (las lesiones solo existen para ligas de EE. UU.). |
| NBA | Sí, y es la fuente más rica: 25 claves por partido, props por cuarto, 16-21 casas por prop. | Parcialmente: `/injuries` (ESPN, cada 10 min, historial desde 18-oct) y `/stats` con minutos; el archivo de box score NBA empieza en la temporada 2026-27. |
| Tenis | Sí para ganador, ganador de set, juegos (total/hándicap), sets; con un adaptador de nombres de claves. | No. Estadísticas de saque solo "en una porción reducida" de partidos; `player_id` es nulo siempre en tenis. |

## Fútbol

**Ligas.** PropLine tiene 31 competiciones de fútbol. Del catálogo del motor faltan en PropLine: LaLiga 2, Serie B,
Ligue 2, Brasil Serie B, Chile y Dinamarca.

Los alias de la Championship (`soccer_efl_champ`), Noruega, Suecia y Suiza ya están en `main` (PR #86 y #90); la copia
local que revisé primero estaba desactualizada.

**Mercados vistos en un partido de la EPL (34 claves):**

| Ya entra a `odds_snapshots` | Solo se archiva (falta adaptador) | No están en la doc ni en la configuración |
|---|---|---|
| `h2h`, `spreads`, `totals` (y total por equipo), `both_teams_to_score`, `double_chance`, `total_corners`, `team_corners`, `total_cards` | `draw_no_bet`, `european_handicap`, `correct_score`, `team_cards`, `corners_spread`, `corners_european_handicap`, `first_team_to_score`, `half_time_full_time`, combinados (`result_total_goals`, `result_btts`…), goleadores, asistencias, tarjetas por jugador, y todo `period=h1/h2` | `player_shots` (999 cotizaciones), `player_shots_on_target` (649), `goalie_saves` (40), `2plus_goals` (275), `3plus_goals`, `winning_margin`, `h2h_early_payout` |

Las siete claves de la última columna no están en `markets_by_family.soccer_`; llegan una vez al día por el
descubrimiento por partido (`2plus_goals` y `3plus_goals` solo desde esta rama, antes se descartaban).

Lo que más le sirve al modelo Dixon-Coles: `correct_score` (14 casas, compara directamente la matriz de goles),
`european_handicap` (Pinnacle en todos los partidos), mitades `h1/h2` (25 casas para el total de 1.ª mitad), y
`draw_no_bet`. Todos se pueden derivar de la matriz de goles que el modelo ya produce.

**Datos (no cuotas):** `/events/{id}/stats` da goles, asistencias, tiros, tiros a puerta, tarjetas, faltas, fueras de
juego, paradas y córners del equipo, por jugador y con marcador por mitad. El archivo empieza en abril de 2026. No hay xG.

## NBA

El motor usa hoy `player_points/rebounds/assists/threes/steals/blocks` y `h2h/spreads/totals`. PropLine trae además,
con precio real en el piloto:

- Combinados: `player_points_rebounds_assists` (45.436 cotizaciones, 16 casas), `points_rebounds`, `points_assists`,
  `rebounds_assists`, `blocks_steals`.
- `player_double_double`, `player_triple_double`, `player_turnovers` (solo DFS), primer anotador
  (`player_first_basket`, `team_first_basket_scorer`…).
- Escalones FanDuel no documentados: `player_points_10plus`, `player_points_15plus`.
- Por periodos: totales y hándicap de `q1…q4` y `h1/h2`; props de jugador en `q1` (puntos, rebotes, asistencias).

La configuración NBA ya pide todas esas claves salvo los dos escalones `10plus/15plus`.

**Datos útiles:** `/v1/sports/basketball_nba/injuries` y `/injuries/history` (ESPN, cada 10 min, desde 18-oct-2026)
encajan con el v1.3 de disponibilidad como segunda fuente fechada; `/players/{id}/games` es el registro de partidos con
minutos; `/projections` da la línea implícita del mercado por jugador (Hobby+).

Límite práctico ya medido: pedir líneas y props NBA juntos da 504; hay que mantener lotes pequeños.

## Tenis

Lo que se vio en el piloto (171 partidos con `h2h`):

| Clave PropLine | Equivalente en `tennis_markets_v2` | Casas |
|---|---|---|
| `h2h` | `h2h` | 44 |
| `h2h` + `period=s1` / `s2` | `h2h_s1` / `h2h_s2` | 18 / 11 |
| `totals`, `spreads` (líneas `alternate` con `line_type`) | `totals`/`alternate_totals`, `spreads`/`alternate_spreads` | 39 / 35 |
| `totals`/`spreads` + `period=s1` | `totals_s1`, `spreads_s1` | 6 / 5 |
| `total_sets` | `alternate_set_totals` | 16 |
| `set_spread` | `alternate_set_spreads` | 1 (Fanatics) |
| `player_games_won` | ninguno; se puede derivar de la distribución Markov | 13 |
| `player_aces`, `player_break_points_won`, `total_tiebreaks`, `total_games` | ninguno; casi solo DFS | 2-5 |

Así que PropLine cubre las diez familias del motor salvo "marcador por sets". La diferencia es de **nombres**: The
Odds API usa sufijos (`h2h_s1`), PropLine usa `period=s1`, y "alternativa" llega como `line_type`, no como otra
clave. Hace falta un adaptador de traducción; los cálculos del motor no cambian.

Avisos: los totales de juegos/sets/tiebreaks de DFS se liquidan sobre **todo el partido** aunque el jugador aparezca en
`description`. Los precios DFS no son apuestas de dos lados. En tenis `player_id` siempre es nulo, así que la
identidad tiene que seguir pasando por `tennis_identity_v3`.

La familia horaria de tenis no incluía `player_aces`, `player_double_faults`, `player_games_won`,
`player_break_points_won` ni `total_aces`. El piloto sí los capturó en un lote aparte.

## Endpoints útiles que no usa nadie todavía

La cuenta es de pago: las cabeceras guardadas en el piloto dicen `x-daily-limit: 5000`, que es el plan **Hobby**
(9 USD/mes). Incluye historial de 30 días, cierres, liquidación de props, +EV, proyecciones y mejor línea. No incluye
las exportaciones CSV (Pro) ni los webhooks (Streaming Lite). El recolector solo acepta rutas `/odds`, `/scores`,
`/ids`, `/futures` y `/markets`, así que hoy no pide nada de lo que añade el plan de pago.

| Endpoint | Plan | Para qué |
|---|---|---|
| `/events/{id}/odds/closing` | Free devuelve estructura; precios desde Hobby | Cierre real y apertura para CLV, sin depender de nuestra hora de captura. |
| `/events/{id}/odds/history` | Hobby (30 días) / Pro (90) | Movimiento de línea para reentrenar sin haberlo capturado nosotros. |
| `/events/{id}/results` y `/exports/resolved-props` | Pro | Props liquidados con valor real: etiqueta para entrenar props NBA y tenis. |
| `/v1/sports/{s}/ids` | Free | IDs de ESPN/casas por partido: evita emparejar por nombre. |
| `/v1/books/accuracy` | Free | Brier por casa: elegir qué casas usar como referencia de mercado. |
| `/v1/coverage/history` | Free | Desde cuándo hay histórico por casa, antes de diseñar un backtest. |

Todo el histórico de PropLine empieza en abril de 2026, y su hora (`recorded_at`) es la de PropLine, no nuestra
recepción. Para point-in-time sigue valiendo solo lo que capturamos nosotros.

## Apify / SofaScore

- La configuración MCP pegada apunta a `azzouzana/sofascore-scraper-pro`, que el 23-oct devolvía "NO ND script found"
  en todas las URLs. El actor que funcionó es `rl1987/sofascore-api-scraper`.
- Saldo de la cuenta Apify: 4,64 de 5 USD usados en el ciclo que termina el 5-nov (quedan ~0,36 USD, unas 75 filas
  de `rl1987`). No se ejecutó ningún actor.
- SofaScore aporta justo lo que le falta a PropLine: xG y alineaciones en fútbol, saque/resto por set en tenis.
  El token no se guardó en ningún archivo; si se usa, debe ir en `.env` (fuera de git), nunca en el repositorio.

## Cambios propuestos

Estado al 24-oct (rama `propline/cierres-liquidaciones`, sin desplegar):

1. Alias: ya resueltos en `main`.
2. Claves: tenis y NBA añadidas a la familia horaria (+24 peticiones/día). Las 6 de fútbol se dejan al descubrimiento
   diario por partido, porque en la familia horaria costarían un lote más por competición (+744/día). El
   descubrimiento ya no descarta las claves que empiezan por dígito (`2plus_goals`, `3plus_goals`).
3. Adaptador de tenis PropLine → claves de `tennis_markets_v2` (periodo y `line_type`): pendiente.
4. Adaptadores de fútbol para `correct_score`, `european_handicap`, `draw_no_bet` y mitades, comparándolos con la
   matriz de Dixon-Coles: pendiente. Solo evaluación al principio; nada pasa a picks sin validación separada.
5. Cierres y liquidaciones diarios: implementados, ver `docs/propline_compartido_20261023.md`.
