# NBA — descarga de props de jugador históricos (The Odds API, clave dedicada)

Código: `apps/nba/src/nba/props_history.py` (`plan`, `fetch`, `load`). Pruebas: `apps/nba/tests/test_props_history.py`.
Clave propia del plan de 100K (solo NBA), en `apps/nba/.local/odds_api_props.env` (ignorada por git). No es la del fútbol.

## Alcance (decisión del titular, 2026-10-24)
4 mercados (`player_points`, `player_rebounds`, `player_assists`, `player_threes`), región `us`, **una captura por partido**
(30 min antes del salto), temporadas 2024-25 y 2025-26: 2.424 partidos. Fin: entrenar el motor de props de jugador.

## Coste
Listado de eventos del día: 1 crédito × 325 días. Cuotas por partido: 10 × 4 mercados = 40. Peor caso 97.285.
Piloto de 40 partidos: 1.606 créditos (40/partido real), 7 casas, ~14,5 jugadores por partido, 4 mercados con datos.
Descarga completa con `--cap 98000 --reserve 300`. Cada respuesta se guarda en `apps/nba/.local/raw/nba_props_odds_202610`
(`events/`, `odds/`, `manifest.jsonl` con sha256, créditos y saldo): nunca se vuelve a pagar.

## Limitaciones
- Una sola captura, 30-44 min antes del salto: no es cierre. Sirve para entrenar con la línea de salida, no para CLV de cierre.
- Pinnacle no cotiza props: solo casas de EE. UU. Líneas de una cara (solo Over) se descartan al cargar (`one_sided_line`).
- `load` entrega una fila por casa/mercado/jugador/línea; el emparejamiento de nombres de jugador con `player_id` queda por hacer.
- Capturar datos no reentrena ni promueve nada (decisión del 23-oct).

## Descarga y emparejamiento (resultado, 2026-10-24)
Descarga completa: 2.424 partidos, ~97.100 créditos (2.855 de saldo); se reanudó una vez tras un 502 sin cobro. `props_odds.jsonl.gz`: 893.165 filas, 2.421 partidos con precios.

`nba.props_link` (`apps/nba/src/nba/props_link.py`, pruebas `tests/test_props_link.py`) une cada fila con el box score **del mismo partido**: nombre exacto, luego sin sufijo Jr/Sr/II-IV si es único, y 9 alias verificados (Bub Carrington, Nic Claxton, Herbert Jones…). Resultado: 893.101 de 893.165 filas con `player_id` (99,99 %); 9.386 por sufijo; 64 sin pareja (Mohamed Bamba, Yang Hansen, Robert Williams: no están en `players.jsonl.gz`).
- 2.283 filas son de jugadores sin fila de box en ese partido (no jugaron): llevan `player_id` pero `actual`, `participated` y `minutes` en `None`. **Excluirlas del entrenamiento o tratarlas como apuesta anulada**; mantenerlas como ejemplos con resultado sería sesgo de supervivencia inverso.
- `actual` es el resultado realizado (puntos/rebotes/asistencias/triples), no una variable previa al partido.
- Salida: `apps/nba/.local/normalized/nba_props_odds_20261024/props_linked.jsonl.gz`.
