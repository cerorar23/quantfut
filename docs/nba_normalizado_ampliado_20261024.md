# NBA — normalizado ampliado: tiros, pérdidas, rebotes, posesiones, play-in y playoffs (24-oct-2026)

Código: `apps/nba/src/nba/extended_box.py` (`freeze`, `build`). Pruebas: `apps/nba/tests/test_extended_box.py`.
Protocolo congelado antes de construir: `apps/nba/nba_extended_box_protocol.json` (hash en
`apps/nba/.local/normalized/nba_extended_box_20261024/protocol_frozen.json`; `build` se niega a correr si cambia).
Salida: esa misma carpeta (`players.jsonl.gz`, `games.json`, `coverage.json`). Solo datos: no entrena ni promueve nada.

## Qué añade
- **Jugador:** `fgm`, `fga`, `fg3a`, `ftm`, `fta`, `oreb`, `dreb`, `tov`, `pf`, `plus_minus` (más los seis de antes).
- **Equipo** (`games.json`): los mismos conteos y, donde existe el box oficial, `tov` oficial, `team_turnovers`
  (pérdidas de equipo no atribuidas a jugadores), `possessions`, `pace` y `minutes`. En todos los partidos,
  `possessions_estimate` = FGA − OREB + TOV de jugadores + 0,44·FTA (la misma definición en todos los niveles).
- **Tipos de partido:** `season_type` ∈ regular, play_in, playoffs; `count_source` dice de dónde salen los conteos.

## Resultado
| Temporada | Regular | Play-in | Playoffs |
| --- | --- | --- | --- |
| 2021-22 | 1.229 | — | — (sin fuente de fecha) |
| 2022-23 | 1.226 | 6 | 84 |
| 2023-24 | 1.217 | 6 | 82 |
| 2024-25 | 1.196 | 6 | 84 |
| 2025-26 | 1.187 | 6 | 85 |

6.414 partidos y 166.632 filas. **No regresión comprobada:** cada fila regular conservada es idéntica a la de
RUN071 en todos sus campos; 53 partidos regulares (0,87 % de 6.108) salen por las comprobaciones nuevas (tope 2 %).
En todo el nivel aceptado quedan en cuarentena 95 partidos (incluye los que RUN071 ya excluía): 108 filas sin una
única versión de los conteos, 57 partidos incompletos, 37 con totales de equipo que no cuadran, 9 sin local claro,
1 con pérdidas de equipo negativas y 1 con un no participante con conteos. Los playoffs 2022-23..2024-25 casan 1 a 1 con API-Sports (fecha, local y marcador final) sin ningún
descarte.

Posesiones: la estimación queda +1,1 por encima de la oficial de media (DE 2,1) en temporada regular y +1,3 en playoffs.

## Niveles de confianza (`count_source`)
- `accepted_base`: regular de las cinco temporadas y postemporada 2025-26. Conteos con una sola versión entre dos
  fuentes crudas, cuadrados contra el box oficial del equipo; minutos oficiales a sub-segundo.
- `sportsdataverse_only`: postemporada 2022-23..2024-25. Una sola fuente de conteos; se exigen las identidades
  internas (puntos = 2·TC + triples + TL, rebotes = ofensivos + defensivos, anotados ≤ intentados) y el marcador final
  de API-Sports. Minutos con precisión de segundo; sin pérdidas de equipo, posesiones oficiales ni ritmo.

## Límites
- Para 2021-22 a 2024-25 la temporada regular tiene los conteos nuevos de una sola fuente de jugador
  (sportsdataverse); el registro original solo está completo en 2025-26. El cruce con el box oficial del equipo es la
  segunda fuente.
- Excluidos: pretemporada, final de la Copa NBA, All-Star y la postemporada 2021-22.
- Los modelos existentes (v1.1-v1.5, vivo) siguen leyendo RUN071. Quien use este conjunto debe filtrar `season_type`.
- Sin hora de salto en postemporada todavía (la fecha es la del Este).
