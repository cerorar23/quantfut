# NBA — productor en vivo v1.3.1: errores corregidos y mercados de jugador (23/24-oct-2026)

Corrige los errores 1-8 de `docs/nba_auditoria_motor_20261023.md` y añade, por decisión del titular, los mercados de
jugador **puntos, rebotes y asistencias** con las líneas de PropLine. Rama `nba/productor-correcciones` (desde `main`).
**No desplegado.** El modelo de equipo y la regla de lesiones no cambian. Enmienda en
`apps/nba/multimarket_v13_live_protocol.json` (versión `nba-multimarket-live-1.3.1`: `amendment_2026_10_23`,
`player_markets`, `game_types`). Las cohortes ya selladas no se tocan y conservan la versión 1.3.

## Errores corregidos
| Error | Antes | Ahora |
| --- | --- | --- |
| 1. Partidos de tarde | Un solo sellado a las 17:35 ET; 87-97 partidos por temporada nunca se pronosticaban. | Cada partido se sella en la primera pasada (cron cada 10 min) que encuentra su salto a más de 65 y como mucho 90 min. Carpeta `AAAA-MM-DD_HHMM` (hora ET del sellado). |
| 2. Sin lesiones en partidos de 18:00-18:45 ET | El reporte de las 17:30, recibido a las 17:35-17:45, no valía para ellos. | Al sellar 65-90 min antes, el último reporte se recibe antes de salto − 60 y cuenta. |
| 3. Hora del sello | `sealed_at_utc` y la recepción del reporte = inicio de la pasada. | Reloj real: cada página y el reporte se fechan al recibirse; el sello, al escribir el bundle. |
| 4. Caché | El servidor rebajaba toda la temporada en cada sellado y saltaba en silencio los partidos no finales. | `--cache` (`/live13/cache`): box scores finales y el calendario del día (se relee cada 2 h). Una entrada con otro formato es error, no se usa. |
| 5. Bloqueo | Cualquier respuesta ≠ 200 se tomaba por «no hay reporte». | 403/404 = franja sin archivo, comprobado una vez con un archivo de control; si el control falla, o llega otro estado, el sellado se detiene con error. |
| 6. Valor de jugadores | Solo box scores hasta 2025-26. | Se suman las filas de jugador (minutos, puntos, rebotes, asistencias) de los box scores finales de 2026-27. Minutos en los dos formatos de nba.com (`PT23M56.00S` actual, `33:15` archivado). |
| 7. Play-in y playoffs | Solo identificadores `002`. | `002` regular, `005` play-in, `004` playoffs y `006` final de la Copa: se sellan, se recogen sus resultados y alimentan Elo, descanso y forma. Pretemporada y All-Star nunca. |
| 8. Pruebas caducadas | 3 pruebas de `test_paper_bundle.py` fallaban desde el 22-oct. | La fecha límite del piloto RUN071 es la constante `paper_bundle.DEADLINE_UTC` (mismo valor); las pruebas usan su propio reloj. |

## Mercados de jugador: puntos, rebotes y asistencias
- **Fuente de líneas:** el archivo horario común de PropLine (`qf.ingest.propline_shared`, el único lector de red;
  documentación https://api.prop-line.com/docs). El NBA solo lo lee, sin red, con la observación más reciente ≤ 65 min
  al sellar. La unión es directa por IDs oficiales (`nba:<equipo>`, `nba:<jugador>`).
- **Qué jugador y qué línea:** jugadores con línea principal Over/Under de partido completo en medio punto en al menos
  2 casas de apuestas. No cuentan sitios DFS (incluido `pick6`, que el archivo no marcaba), casas de intercambio,
  cuotas en juego, suspendidas o marcadas. La línea es la más repetida (empate: la más cercana a la mediana, luego la
  menor). Las cuotas no entran en el modelo: la línea solo es el umbral del pronóstico.
- **Modelo:** el de jugador de v1.3 (binomial negativa + 25 % empírico sobre los últimos 20 partidos, mínimo 10, 370 días;
  recalibración con el estado propio del reporte y los minutos esperados que faltan en el equipo), ajustado una vez con
  2024-25 y 2025-26. Se excluye al jugador «Out» y al que su último equipo no juega ese partido.
- **Condicionado a jugar**, como anulan las casas: si no juega, el resultado es «No participó» y no puntúa.
- **Cambio frente a v1.3 retrospectivo, medido:** la recalibración se ajusta sobre una rejilla de umbrales (media de
  10 + 0,5 + {−4, −2, −1, 0, +1, +2, +4}) y no solo en ese umbral sintético, porque la línea de una casa puede caer en
  cualquier sitio. Fuera de muestra (entrenado 2023-25, evaluado 2025-26, con las variables de lesiones):

| Mercado | Brier umbral único → rejilla | Sesgo a 4 líneas por debajo / por encima (único → rejilla) |
| --- | --- | --- |
| Puntos | 0,2233 → 0,2222 | −0,080 → −0,031 / +0,075 → +0,030 |
| Rebotes | 0,1721 → 0,1693 | −0,079 → −0,015 / +0,068 → +0,010 |
| Asistencias | 0,1494 → 0,1482 | −0,057 → −0,013 / +0,029 → −0,004 |

  En el umbral sintético exacto el único es ~0,001 mejor (es donde se ajustó); en el resto gana la rejilla.
- **Página y resultados:** el panel puntúa los tres mercados desde el box score oficial y la página muestra la línea
  («Línea principal de PropLine, la más repetida en N casas»), el estado del reporte y la probabilidad de jugar.

## Verificación
- Pruebas: `tests/test_live_players.py` (12: consenso, filtros de casas, partido y hora, archivo ausente, pronóstico con
  línea/historia/reporte, peso del estado, «Out» y otro equipo, modelo sin `player_fit`, resultados con «No participó»,
  identificadores 004/005/006, rejilla de recalibración y caché antigua) más las del productor y la caché. Suite NBA
  completa en verde (incluidas las 3 de `test_paper_bundle.py`).
- Ensayo real (solo lectura): el archivo de PropLine del servidor leído desde un contenedor con el volumen montado
  `readonly` (63 eventos, captura 03:08 UTC del 24-oct): las líneas se emparejan con los 8 partidos del 24-oct y salen
  17 pronósticos de jugador con las líneas publicadas a esa hora (se publican más durante el día). Box scores reales del
  20-22-oct: 548 filas de jugador; reporte del 23-oct y control de bloqueo comprobados contra nba.com.
- Modelo: `apps/nba/.local/normalized/nba_f6_live13_model_20261023/model.json` (sha256 `ded93f16…`). Equipo
  (`fit`, `play_probability`, `observed_share`, temporadas) **idéntico** al `…20261021b`; `player_fit` nuevo
  (337.546 / 309.341 / 272.268 muestras de rejilla).

## Límites
- La recalibración se aprendió con umbrales estadísticos, no con líneas históricas de casas (no se compraron). Lo que
  mide de verdad su certeza es el registro prospectivo que empieza al desplegar.
- El rango 80 % de jugador sale de la distribución sin recalibrar (la auditoría midió que en puntos cubre ~73 %).
- Si el archivo de PropLine falta o tiene más de 65 min, la cohorte sale solo con mercados de equipo (`prop_lines.state`).

## Despliegue (NO ejecutado; espera confirmación)
Requisitos: PR fusionado en `main`, una sola sesión desplegando, comparar lo desplegado con `main` (`DEPLOYS.md`).
```bash
ssh quantfut
L=$HOME/nba-isolated/live13
crontab -l > $L/crontab.before-20261023
cp -a $L/model $L/model.before-20261023 && cp -a $L/producer.sh $L/producer.sh.before-20261023
mkdir -p $L/cache   # mismos permisos que $L/cohorts (escribible por el usuario 1001 del contenedor)
# contexto desde main con git archive y core.autocrlf=false (como en el despliegue de precios) en $L/build-producer,
# más el lector común en la raíz del contexto:
cp <checkout de main>/src/qf/ingest/propline_shared.py $L/build-producer/propline_shared.py
docker build -f $L/build-producer/ops/Dockerfile.live13_producer --build-arg NBA_LIVE13_BASE=nba-dashboard-live13:20261021 \
  -t nba-live13-producer:20261023 $L/build-producer
# copiar nba_f6_live13_model_20261023/model.json a $L/model/model.json (comprobar sha256 ded93f16…)
install -m 755 $L/build-producer/ops/live13_producer.sh $L/producer.sh
```
**Montaje del archivo de PropLine:** está en el volumen Docker `quantfut_artifacts`, subcarpeta `propline_shared` (no en
una ruta del host). `producer.sh` lo monta con `--mount type=volume,src=quantfut_artifacts,dst=/live13/propline,
volume-subpath=propline_shared,readonly` (Docker 29.8; comprobado el 24-oct: un contenedor con ese montaje leyó el índice
WAL sin escribir).

**Panel:** reconstruir `nba-dashboard-live13` con el `src/nba` y `web/` de esta rama (puntúa y muestra los mercados de
jugador); mismo procedimiento que la entrada del 21-oct de `DEPLOYS.md`.

Comprobar en la primera pasada: `schedule/<día>.json` en la caché, ningún sellado hasta 65-90 min antes del primer salto,
cohorte `AAAA-MM-DD_HHMM` con `created_at_utc` posterior al inicio de la pasada, `prop_lines.state = archivo_aplicado` y
pronósticos `player_points/rebounds/assists`.

**Vuelta atrás:** restaurar `producer.sh.before-20261023` y `model.before-20261023` (la imagen
`nba-live13-producer:20261021` sigue en el servidor) y el contenedor anterior del panel. Las cohortes 1.3.1 se quedan.

## Efecto en la captura de precios (`nba-live13-price`, desplegada el 22-oct, bloqueada hasta el 1-nov)
Con varias cohortes por día, su fase `seal` pedirá un precio por cohorte y el libro (2 peticiones/día) rechazará a partir
de la segunda. Como el motor no busca ganarle al mercado y PropLine es la fuente fija de cuotas, conviene decidir antes
del 1-nov si se retira esa línea de cron (vuelta atrás en `DEPLOYS.md`, entrada del 22-oct).
