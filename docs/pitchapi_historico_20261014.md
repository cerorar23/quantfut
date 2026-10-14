# Fútbol: histórico de PitchAPI y xG importado

Descarga e importación del 14-oct-2026 (UTC). Fuente: <https://pitchapi.dev/>,
API `https://api.pitchapi.dev/v1`, cabecera `X-API-KEY`. La clave (`pk_test_`)
está en `.env` como `PITCHAPI_KEY`, fuera de Git y no enviada al VPS.

## Qué se descargó

- `/v1/leagues/{id}/matches?season=...&status=played` para las 23 competiciones
  de QuantFut y todas las temporadas que publica PitchAPI: 121 listas,
  33.180 partidos terminados, sin fallos.
- `/v1/matches/{id}/stats` de los 5.399 partidos que cruzan (misma liga, fecha
  ±1 día y marcador) con un partido canónico sin xG: 5.399 respuestas 200.
  El xG sale de `expected_goals` del periodo `All`.
- Originales con SHA-256 y hora de recepción real en
  `.local/pitchapi_20261014/raw/` (`lists`, `stats`, `catalog`). Los fallos
  también se guardan y no se repiten solos. Cloudflare rechaza el User-Agent
  por defecto de Python (error 1010); el cliente se identifica como
  `QuantFut-historico/1.0`. Sin límites publicados ni 429 a ~1 petición/s.

## Identidad y carga

Los clubes no se emparejan por nombre. Un equipo de PitchAPI se asocia a un
club canónico si al menos 3 partidos con misma fecha UTC y marcador, con
candidato único, apuntan a él con dominancia del 90 % y ningún otro equipo
lo reclama (496 equipos). Un partido solo se empareja si ambos clubes, marcador
y fecha (±1 día) coinciden con un único partido canónico. Con xG ya presente
(25.732) no se toca; 305 sin partido canónico, 1.754 con equipo sin identificar.

Se importaron **5.355** xG con `xg_source='pitchapi'` y `xg_recorded_at` igual
a la recepción real (04:09–04:32 UTC del 14-oct), de modo que `xg_at_cutoff`
no los usa antes de esa fecha. Solo se rellenan partidos terminados con ambos
xG vacíos. Ensayo en transacción revertida (mismos conteos y cero residuo),
carga real y repetición con cero escrituras. Copia previa de las filas:
`.local/pitchapi_20261014/backup_matches_antes.csv` (todas vacías).

Coherencia: xG medio 1,22–1,46 frente a goles medios 1,26–1,59 y correlación
0,54–0,64 por liga. Arnés 1.049 aprobadas/24 omitidas; modelo, ligas, lotes
sellados y API sin cambios.

| Competición | xG importados |
| --- | ---: |
| Championship | 1.408 |
| Bundesliga 2 | 765 |
| Allsvenskan | 655 |
| Eliteserien | 646 |
| Superligaen | 491 |
| Süper Lig | 485 |
| Super League suiza | 467 |
| Eredivisie | 305 |
| Resto (Liga MX 42, Primeira 32, Ligue 1 13, Serie A 11, LaLiga 10, LaLiga 2 10, Ligue 2 8, Argentina 4, otras 3) | 133 |

## Lo que PitchAPI no resuelve

Serie B, LaLiga 2 y Ligue 2 solo tienen la temporada 2025/26 y Argentina desde
2023; sus huecos desde 2024 siguen casi intactos. Huecos xG desde 2024:
1.262 → **1.220** (Serie B 588, LaLiga 2 236, Argentina 208, Ligue 2 144).
Desde 2021-07: 5.261. Los xG de PitchAPI no demuestran mejora retroactiva del
backtest ni se han usado para entrenar.

Código: `src/qf/ingest/pitchapi_history.py` (descarga) y `pitchapi_pairing.py`
(emparejamiento y SQL), con `tests/test_pitchapi_*.py`.
