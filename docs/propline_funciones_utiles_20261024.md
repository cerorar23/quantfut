# PropLine: funciones útiles para fútbol, NBA, tenis y props de jugador — 24 de octubre de 2026

Lectura completa de `https://prop-line.com/llms-full.txt` (actualizado el 24-oct-2026), contrastada
con `api.prop-line.com/openapi.json` y con lo que ya usa el repositorio. Ninguna función se ha
probado todavía, salvo `/odds`, `/scores` e `/ids`, que ya captura el recolector.

**Plan actual de la clave: Hobby** (cabecera `x-daily-limit: 5000`; 9 USD/mes). El recolector se
limita a 4.500 peticiones al día y reserva 500. El 24-oct a las 04:17 UTC llevaba 695.

| Plan | Precio | Peticiones/día | Qué añade |
|---|---|---|---|
| Free | 0 | 1.000 | Cuotas, marcadores, estadísticas, lesiones; histórico y liquidación ocultos |
| **Hobby (actual)** | 9 USD | 5.000 | Histórico de líneas (30 días), liquidación de props, +EV, CLV, `/projections`, `/trends` |
| Pro | 19 USD | 25.000 | Exportaciones CSV (resolved-props con apertura y cierre, 90 días), histórico de 90 días |
| Streaming Lite | 39 USD | 250.000 | Webhooks de movimiento de línea y de liquidación |

Ojo: la tabla de precios pone la liquidación (`/results`) en Hobby, pero la sección del endpoint
dice «Pro full, Free redacted». Hay que confirmarlo con una petición real antes de depender de ello.

## Reglas de la API que afectan a nuestro código

- Pasar siempre `markets=`; sin él solo llega `h2h`. Más de 50 claves da error 400. Si una clave no
  existe en la respuesta, llega la cabecera `X-PropLine-Missing-Markets`.
- **Goles por equipo y totales alternativos van en `totals`**: el campo `team` distingue el total del
  equipo (`team: null` = partido). Agrupar siempre por `(key, period, team)` y filtrar `line_type`
  (`main` / `alternate` / `milestone`).
- **Los IDs de partido cambian**: PropLine fusiona duplicados. Un ID viejo devuelve el evento canónico
  con otro `id`; `merged_from_event_ids` lista los absorbidos y un 404 persistente significa
  «redescubrir el evento». El archivo ya guarda `merged_from_event_ids`.
- `home_team`/`away_team` son nombres para mostrar; las claves estables son `home_team_key` y
  `home_team_id` (ID de la liga: `nba:`, `espn.soccer:`). En tenis no hay clave de jugador estable.
- `last_change_at` es la hora en que PropLine vio cambiar el precio, para todas las casas;
  `book_updated_at` solo lo publica Bovada. Ninguna de las dos es nuestra hora de recepción.
- Precios DFS (PrizePicks, Sleeper, Dabble, ParlayPlay, Pick6) no son cuotas de dos lados; Underdog
  solo con `payout_multiplier == 1.0`. El productor NBA ya los excluye.
- Límites: 20 peticiones simultáneas, ráfaga de 20 y 10 por segundo en Hobby. Respetar `Retry-After`.

## Fútbol

| Función | Plan | Para qué nos sirve |
|---|---|---|
| `GET /v1/sports/{liga}/odds` (ya en uso) | Free | Cuotas de todas las casas, Pinnacle incluida: 1X2, totales y goles por equipo (`totals`+`team`), hándicap asiático y europeo, BTTS, doble oportunidad, sin empate, córners (totales, por equipo, hándicap), tarjetas (totales y por equipo), resultado exacto, combinados, primera parte con `period=h1` |
| `GET .../events/{id}/odds/closing` | Free* | Apertura y cierre por casa y mercado en una petición, con `closing_at` e `is_stale`. Es el **cierre real** para la puerta CLV, en lugar de la última captura horaria |
| `GET .../events/{id}/results` | Hobby/Pro | Liquida 1X2, totales, goles por equipo y periodos con el marcador real; props de jugador (goleador, tiros) contra el acta |
| `GET .../events/{id}/stats` | Free | Acta por jugador: goles, asistencias, tiros, tiros a puerta, tarjetas, faltas, fueras de juego, paradas; córners por equipo; marcadores por parte. Sirve para liquidar córners y tarjetas sin otra fuente |
| `GET /v1/sports/{liga}/scores` (ya en uso) | Free | Marcadores de los últimos 3-30 días, con estado (`final`, `postponed`, `cancelled`) |
| `GET /v1/sports/{liga}/ids` (ya en uso) | Free | `espn_event_id` e IDs de cada casa por partido; une PropLine con otras fuentes sin emparejar nombres |
| `GET .../events/{id}/movement` | Hobby | Apertura contra última línea y `steam[]` (varias casas moviéndose a la vez). Diagnóstico, no entrada del modelo |
| `GET .../events/{id}/ev` | Hobby | +EV contra el precio sin margen de Pinnacle (o consenso). Referencia, no sustituye al de-vig propio |

\* `/odds/closing` no dice plan en su sección; `scripts/propline_captura.py` ya lo usaba con esta clave.

Ligas sin catálogo: Segunda División, Serie B, Ligue 2 y Superliga danesa.

## NBA y props de jugador

| Función | Plan | Para qué nos sirve |
|---|---|---|
| `GET /v1/sports/basketball_nba/odds` (ya en uso) | Free | Líneas del partido y props: puntos, rebotes, asistencias, triples, robos, tapones, pérdidas, combinados (PRA, P+R, P+A, R+A, robos+tapones), doble-doble, triple-doble, primer enceste; cuartos y mitades con `period` |
| `GET /v1/sports/basketball_nba/injuries` | Free | Lesiones de ESPN cada 10 min: `status_code` (out, doubtful, questionable, probable, game_time_decision…), `player_id`, `status_since`, `expected_return`. **Complemento, no sustituto** del PDF oficial que usa v1.3 |
| `GET .../injuries/history?days=` | Free | Cada cambio de estado con `changed_at` (desde el 18-oct-2026). Da tiempos point-in-time de un cambio de estado |
| `GET .../events/{id}/stats` | Free | Box score por jugador: puntos, rebotes, asistencias, triples, robos, tapones, pérdidas, combinados y `minutes`. En vivo cada ~90 s, oficial al pasar a `final` |
| `GET /v1/sports/basketball_nba/players/{id}/games` | Free | Registro de partidos del jugador con todas sus estadísticas, filtrable por temporada, tipo y rival; incluye partidos sin línea publicada |
| `GET .../players?search=` | Free | `player_id` estable (`nba:<personId>`, el ID de la NBA) y todas las grafías que usan las casas. Resuelve nombres abreviados tipo «J. Vandromme» que hoy no emparejan |
| `GET .../events/{id}/results` | Hobby/Pro | Cada línea de prop liquidada (`won`/`lost`/`push`/`void`) con el valor real |
| `GET .../events/{id}/odds/closing` | Free* | Línea de cierre de cada prop para medir el pronóstico contra el cierre |
| `GET .../events/{id}/projections` | Hobby | Valor que implica el mercado (donde P(over) sin margen = 50 %), mediana entre casas. Solo referencia: el motor NBA no usa cuotas como entrada |
| `GET .../players/{id}/trends` | Hobby | Rachas de over/under en 5/10/20/50 partidos contra la línea principal |
| `GET /v1/books/accuracy` | Free | Brier de cada casa en props contra el consenso: qué casa es la mejor referencia |

El archivo de box scores de NBA empieza con la temporada 2026-27: no hay histórico anterior.

## Tenis

| Función | Plan | Para qué nos sirve |
|---|---|---|
| `GET /v1/sports/tennis/odds` (ya en uso) | Free | Ganador, hándicap de juegos, total de juegos, total de sets, hándicap de sets, por set (`period=s1…s5`); props: aces, dobles faltas, juegos ganados, break points ganados, total de aces |
| Campos `tour`, `tier`, `qualifying`, `doubles` | Free | Filtrar ATP/WTA principal frente a Challenger, ITF, UTR, exhibición y dobles. `tier` y `qualifying` solo vienen en `/events` |
| `GET /v1/sports/tennis/scores` | Free | Estados `retired` y `walkover`: anulan hándicap, totales y props y dejan el ganador sin liquidar |
| `GET .../events/{id}/stats` | Free | Juegos totales, sets ganados y juegos por set; en una parte de los partidos, aces, dobles faltas, break points y tie-breaks. Archivo desde abril de 2026 |
| `GET .../events/{id}/results` | Hobby/Pro | Props de tenis liquidados desde el 14-ago-2026 (solo individuales) |

En tenis `player_id` es siempre `null`: el emparejamiento de jugadores sigue siendo nuestro.

## Funciones generales

- `GET /v1/sports/{deporte}/events/{id}/markets` (Free): qué claves tiene un partido antes de pedirlas.
- `GET /v1/freshness` (sin clave): antigüedad por casa, separada entre líneas y props.
- `GET /v1/coverage/history?sport=` (Free): desde cuándo hay histórico de cada casa; necesario antes
  de cualquier backtest.
- `POST /v1/clv/grade` (Hobby): CLV y liquidación de hasta 500 apuestas por llamada contra el cierre
  sin margen (Pinnacle primero).
- `GET /v1/exports/resolved-props` (Pro): CSV con apertura, cierre y resultado de cada línea; 90 días.
- Webhooks `line_movement` y `resolution` (Streaming Lite).

## Prioridad propuesta

1. **Cierre real con `/odds/closing`** para fútbol y NBA. Ya probado con esta clave; cuesta una
   petición por partido y mercado, poco frente al tope de 4.500.
2. **`/players?search=` y `player_id` en NBA**, para emparejar los props que hoy caen por nombres
   abreviados (pendiente anotado en `PENDIENTES.md`).
3. **`/stats` de fútbol** para liquidar córners y tarjetas, y de NBA como segunda fuente del box score.
4. **`/injuries` NBA** archivado cada hora como segunda señal con `status_since`, sin sustituir al PDF
   oficial en el protocolo sellado.
5. Confirmar con una petición si `/results` entra en Hobby; si exige Pro, decidir si compensa subir a
   19 USD/mes (también daría `resolved-props`).

Nada de esto toca modelos ni protocolos sellados: son fuentes nuevas que habría que añadir al
recolector compartido, con su hora de recepción, igual que `/odds`.
