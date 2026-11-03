# NBA — productor vivo 1.4: reentrenado y calibrado con la data nueva (24/25-oct-2026)

Decisión del titular: el motor vivo debe quedar entrenado y calibrado con toda la data nueva y desplegado. Para no meter nada «porque existe»,
cada pieza se validó contra la anterior con un protocolo congelado antes de correr (`apps/nba/nba_live14_protocol.json`; hash en
`apps/nba/.local/normalized/nba_live14_20261024/protocol_frozen.json`). Validación: `nba.live14_check`, que ajusta cada brazo con el mismo
`fit_model` del productor como si el objetivo fuera 2025-26 (entrena 2023-24 y 2024-25) y compara en 2025-26 sobre **las mismas unidades**
(mismo jugador, partido y línea), cada brazo con su propio historial. Informe: `live14_report.json` en esa carpeta.

## Resultado por pieza (diferencia de Brier contra la configuración aceptada hasta ese paso; negativo = mejor)
| Pieza | Diferencia conjunta (IC 95 %) | Detalle | Decisión |
| --- | --- | --- | --- |
| C1 Reportes T-60 en el ajuste | −0,0018 [−0,0022; −0,0015] | los 7 mercados de jugador mejoran (puntos −0,0020, P+R+A −0,0027) | **entra** |
| C2 Dataset ampliado (play-in, playoffs, columnas nuevas) | +0,0004 [+0,0002; +0,0007] | peor en rebotes, asistencias, R+A y P+R+A; equipo sin cambio | **no entra** |
| C3 Entorno del partido en la calibración de jugador | −0,0003 [−0,0004; −0,0002] | los 7 mejoran | **entra** |
| C4 Ajuste del nivel de anotación en la temporada | +0,0010 [+0,0000; +0,0018] en puntos/total | n0 = 400 elegido en 2024-25 | **no entra** |
| C5 Mercados nuevos | triples −0,0007, robos −0,0004, tapones −0,0002, robos+tapones −0,0007 contra la ley cruda; pendiente 0,99-1,00 | pérdidas sin datos (RUN071 no trae pérdidas) | **entran 4** |

Lecturas:
- Lo que más aporta son los **reportes de lesiones T-60**: el modelo vivo se había ajustado con reportes de las 13:30/17:30 y servía reportes de una hora antes del salto.
- **Añadir play-in y playoffs al historial empeora** los mercados de jugador: el rol y los minutos de postemporada no son los de la temporada regular. Se conserva RUN071.
- Con RUN071 no hay posesiones ni tiros intentados: **ritmo, defensa rival y tendencia de uso valen 0 en el entrenamiento** y su peso queda en 0. La mejora de C3 viene
  del total y el hándicap previos al partido, la localía, el descanso y los minutos recientes.
- El ajuste del nivel de anotación dentro de la temporada empeora los puntos de equipo: la deriva de 2025-26 no se corrige así.

## Configuración 1.4.0 (la que se despliega)
- Datos: RUN071 (los mismos del servidor). Reportes del ajuste: antiguos + T-60 (`nba_reports_old_t60_20261024/reports.jsonl.gz`, 2.726 reportes).
- Calibración de jugador: `logit p`, sesgo, estado propio, minutos perdidos de compañeros + `total_c`, `own_spread`, `abs_spread`, `home`, `back_to_back`, `pace_c`, `opp_def_c`, `min10`, `usage_trend`.
  Al sellar, total y hándicap salen del consenso de líneas principales de PropLine (al menos 2 casas; 0 si faltan); en el ajuste, de bet365 45 min antes del salto.
- Mercados de jugador: puntos, rebotes, asistencias, P+R, P+A, R+A, P+R+A, **triples, robos, tapones, robos+tapones** (11).
- Equipo: sin cambios (sin ajuste de nivel de anotación).
- El modelo guarda sus `options`; un modelo sin ellas se lee como 1.3.2.

## Cambios de código
`live_features.py` (nuevo: entorno, rol reciente y ajuste de equipo), `multimarket_v13_live.py` (opciones en el ajuste y al sellar, conteos nuevos del box score,
caché 1.3.x que se vuelve a descargar, `season_shift`, `compare --retrain`), `prop_lines.py` (mercados nuevos y `game_lines`), `multimarket_live_dashboard.py`
(resultados oficiales de los conteos nuevos), web (pestañas Triples, Robos, Tapones, R+T), `live14_check.py` (la validación) y pruebas (`test_live14.py`, 12).

## Despliegue
Igual que 1.3.2: estado del servidor comparado con `main`, contexto con `git -c core.autocrlf=false archive`, **panel primero**, productor después, modelo ajustado con el módulo
de `main` y comprobado con `compare --retrain` contra el desplegado, ensayo del productor con carpetas temporales y el límite de memoria real (512 MB) antes de cambiar el cron.
```bash
python -m nba.multimarket_v13_live fit --output apps/nba/.local/normalized/nba_f6_live13_model_<fecha> \
  --data apps/nba/.local/normalized/nba_f6_run71_20261009/data \
  --injuries apps/nba/.local/normalized/nba_reports_old_t60_20261024/reports.jsonl.gz \
  --api-dir apps/nba/.local/raw/api_nba_20261006 \
  --options apps/nba/.local/normalized/nba_live14_20261024/accepted_options.json \
  --bets apps/nba/.local/normalized/nba_betsapi_odds_20261024/odds.jsonl.gz
python -m nba.multimarket_v13_live compare --retrain --model apps/nba/.local/normalized/nba_f6_live13_model_<fecha> \
  --reference apps/nba/.local/normalized/nba_f6_live13_model_20261024c
```
**Vuelta atrás:** restaurar `producer.sh` y `model` anteriores (1.3.2, imagen `nba-live13-producer:20261024b`); el panel nuevo lee 1.3.x y 1.4.

## Límites
- Las líneas del entorno se entrenan con bet365 y se sirven con el consenso de PropLine: misma magnitud, casas distintas.
- Todo es retrospectivo sobre 2025-26; la prueba real es el registro prospectivo.
- Fuera: pérdidas (sin datos en RUN071), doble-doble, cuartos 3-4, márgenes por rangos y SofaScore (el archivo tiene solo unos cientos de KB y ningún histórico).
