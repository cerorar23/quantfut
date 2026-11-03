# Respaldo football-data.org para el motor de fútbol — diseño

Fecha: 2026-11-01. Estado: borrador para aprobación del titular. Sin código escrito.

## Intención

El motor de fútbol depende de pocas fuentes vivas para saber **qué partidos hay y cómo
terminaron**: PropLine (calendario, resultados, cuotas) y FotMob (resultados al pitido,
árbitro, xG). Si una de ellas se retrasa o se equivoca, el síntoma llega tarde: un
partido que no entra a `matches` no se predice, un resultado ausente o erróneo liquida mal
un pick y rompe el historial verificable. El titular entregó una clave de
football-data.org (v4) para tener un **tercer testigo independiente** de calendario y
resultados. Es un respaldo y un verificador, no una fuente nueva de verdad.

## Hechos verificados (1-nov-2026, con la clave real)

- Base `https://api.football-data.org/v4/`, cabecera `X-Auth-Token`. Plan gratuito.
- 13 competiciones visibles; 10 solapan con el motor: PL, ELC, PD, SA, BL1, FL1, DED, PPL,
  BSA y CL. Fuera de cobertura: MLS, Liga MX, Argentina, Turquía, Bundesliga 2, Suiza,
  Dinamarca, Noruega, Suecia, Europa League, LaLiga 2, Serie B y Ligue 2.
- Límite: 10 peticiones por minuto (`x-requests-available-minute`).
- `GET /v4/matches?competitions=PL,ELC,...&dateFrom=&dateTo=` devuelve todas las ligas de
  una vez: 170 partidos en una sola petición para el 24-oct a 2-nov.
- Un partido trae: `id`, `utcDate`, `status` (FINISHED, TIMED, ...), `matchday`, `stage`,
  `homeTeam`/`awayTeam` (`id`, `name`, `tla`), `score.fullTime`, `score.halfTime`,
  `score.duration`, `referees`, `lastUpdated`. El bloque `odds` viene apagado.
- No trae once, bajas, xG ni tiros.
- **No verificado:** si el plan gratuito retrasa marcadores recientes; los términos de uso
  del plan gratuito para este proyecto (ver «Preguntas del titular»).

## Metas

1. Detectar y avisar cuando el calendario o los resultados de la base difieren de
   football-data.org en las 10 ligas solapadas.
2. Conservar cada respuesta recibida como original con hash y recepción real, para
   auditoría y reentrenamiento posterior (regla del titular del 23-oct).
3. Funcionar sin supervisión, sin consumir más de unas pocas peticiones al día.
4. No poder tumbar el cron ni tocar nada inmutable aunque la API falle o devuelva basura.

## No metas

- No es fuente de cuotas, once, bajas, xG, tiros ni jugadores.
- No cubre las ligas fuera de las 10 solapadas; ahí no hay respaldo y se dice.
- v1 no corrige ni escribe en `matches`. Rellenar resultados queda como fase 2, solo con
  decisión del titular.
- v1 no añade panel en `/control`.

## Anti-metas (fallaría aunque «funcione»)

- Sobrescribir un valor ya capturado, o crear equipos o partidos. Los clubes de CL ya
  existen bajo su liga doméstica: nunca dar de alta equipos bajo `eu.ucl`.
- Emparejar clubes por nombre difuso.
- Escribir en `predictions`, `picks` u `odds_snapshots`, o cambiar el orden
  predecir → sellar → publicar.
- Provocar reentrenamiento o promoción de modelos por capturar datos.
- Alertar a diario por la misma diferencia o por falsas alarmas de prórroga y penales.

## Diseño

### Dónde encaja

Es un job hermano de `qf.ingest.pitchapi_respaldo`, con el mismo contrato: desactivado o
sin clave no hace nada y no falla; una clave rechazada (401) detiene la pasada y avisa una
vez; ninguna discrepancia se corrige sola. Va **por detrás** de las fuentes vivas y de
`results.py` / `fixtures.py` / `fotmob_*`: lee `matches`, no compite con quien la escribe.

```
PropLine / FotMob / results ──► matches ◄── compara ── fdorg_respaldo ◄── football-data.org
                                                │
                                                ├─► fdorg_discrepancies (+ aviso Telegram de alertas)
                                                ├─► fdorg_originals (respuesta cruda, hash, recepción)
                                                └─► ingest_health (fuente 'fdorg')
```

### Módulo

`src/qf/ingest/fdorg_respaldo.py`, cliente HTTP mínimo con `httpx` (ya en el proyecto).

- Clave: `FOOTBALL_DATA_ORG_KEY` del entorno (ya en `.env` local y `.env.example`).
- Peticiones por pasada: 2.
  - `/v4/matches?competitions=<10 códigos>&dateFrom=hoy-7&dateTo=hoy+2` (resultados
    recientes).
  - `/v4/matches?competitions=<10 códigos>&dateFrom=hoy&dateTo=hoy+9` (calendario
    próximo).
  La ventana de cada petición no pasa de 10 días. Un 429 o un 5xx termina la pasada con
  aviso en `last_detail`; no hay reintentos en bucle.
- Normalización a la forma que ya entiende `pitchapi_respaldo.compare()` y
  `promote()`: se importan y se reutilizan sin modificarlas (código ya desplegado).
  Adaptador puro `to_common(match)` con `status` en `finished`/`scheduled`, `score_home`,
  `score_away`, `time_utc`, `league.id` = código de competición, equipos con `id` y
  `name`.
- Solo se comparan marcadores con `score.duration == 'REGULAR'`. Prórroga y penales se
  omiten (la convención de goles de la base y la de football-data.org pueden diferir y
  daría falsas alarmas); queda contado en `last_detail`.
- Estados `POSTPONED`, `SUSPENDED`, `CANCELLED`, `AWARDED`: no se comparan.
- Equivalencia de equipos: tablas `fdorg_teams` y `fdorg_team_votes`, mismo mecanismo de
  votos de PitchAPI (misma fecha UTC y marcador, candidato único, ≥3 votos, 90 % de
  dominancia, nunca por nombre). Un club sin equivalencia no genera discrepancias.
- `compare()` solo trata partidos terminados: `score`, `result_pending` y `missing_in_db`
  de terminados salen de ella. Los programados (`missing_in_db` a futuro y
  `kickoff_shift`) requieren una función pura nueva `compare_calendar()` en el módulo, con
  la misma regla de «si hay más de un candidato no se afirma nada».
- Tipos de discrepancia: `score`, `result_pending` (kickoff + 6 h sin cerrar en la base),
  `missing_in_db` (finalizado o programado a ≤ 7 días que la base no tiene) y
  `kickoff_shift` (programado con hora distinta en > 90 min; una reprogramación mal
  recogida descuadra las ventanas de captura de cuotas y el CLV, como advierte
  `fixtures.py`).
- Aviso al chat de alertas (`telegram.alert`): `score`, `result_pending`, `kickoff_shift`
  y `missing_in_db` de partidos a ≤ 72 h. Máximo 5 líneas por aviso; una diferencia
  abierta no se vuelve a avisar.
- Cierre de cada pasada: `last_run_at`, `last_ok`, `last_detail` en `fdorg_settings` y
  `af.record_health('fdorg', ...)` en `ingest_health`, igual que PitchAPI.
- Bloqueo asesor `pg_try_advisory_lock` para que no corran dos pasadas a la vez.

### Datos (migración nueva, solo aditiva)

Número: el siguiente libre en `main` al empezar. En esta fecha `main` llega a `084` y la
rama `futbol/base-unica` ya tiene `085`–`086` (y se menciona `088`); verificar antes de
numerar para no chocar.

- `leagues.fdorg_code TEXT`, con PL→`gb.premier_league`, ELC→`gb.championship`,
  PD→`es.laliga`, SA→`it.serie_a`, BL1→`de.bundesliga`, FL1→`fr.ligue_1`,
  DED→`nl.eredivisie`, PPL→`pt.primeira`, BSA→`br.serie_a`, CL→`eu.ucl`. (No reutiliza
  `fd_code`, que es de football-data.co.uk.)
- `fdorg_settings` (fila única: `enabled` falso por defecto, `last_run_at`, `last_ok`,
  `last_detail`).
- `fdorg_teams`, `fdorg_team_votes`, `fdorg_discrepancies` (índice único parcial sobre las
  abiertas, como PitchAPI), `fdorg_originals` (una fila por respuesta: ventana, `sha256`,
  `received_at`, `payload_gzip`). Unos 15 KB comprimidos por respuesta.
- Ninguna tabla existente cambia salvo la columna nueva de `leagues`.

### Programación

Entrada en `scripts/crontab`: dos pasadas diarias, 13:10 y 01:10 UTC (cuatro peticiones al
día). Se activa desde la fila de `fdorg_settings`, no desde el código.

### Fallos

| Caso | Comportamiento |
| --- | --- |
| Desactivado o sin clave | no hace nada, `skipped` |
| 401 | detiene, `last_ok` falso, un aviso |
| 429, 5xx, red | termina la pasada, `last_ok` falso; `last_detail` lleva un contador de fallos seguidos y avisa al llegar a 3 |
| JSON inesperado | se guarda el original, la pasada falla, nada se compara |
| Dos coincidencias posibles | no se afirma nada |

## Pruebas

- Puras (sin base): adaptador `to_common`, omisión de prórroga y penales, ventanas de
  fechas, `kickoff_shift`.
- Con Postgres aislado (patrón de `tests/test_history_fd_cierres_pg.py`): una pasada con
  respuesta grabada devuelve las discrepancias esperadas, no duplica una diferencia
  abierta y no escribe en `matches`.
- Muestra real recortada (unos 6 partidos de la respuesta del 1-nov) como fixture.
- Antes de empezar, el protocolo del proyecto: `harness_check.sh` o
  `test_local_windows.ps1 -Suite all` debe pasar.

## Despliegue

Desde un worktree de `main` (la rama actual va 101 commits atrás). Seguir `DEPLOYS.md`:
comparar con `main`, una sesión a la vez, copia previa y vuelta atrás anotadas. Añadir la
clave al `.env` del VPS, comprobar que el contenedor del worker la ve, aplicar la
migración, activar `enabled` y vigilar la primera pasada. Anotar en `harness/progreso.md`
y `harness/tareas.md`, y una fila de fuente en el README.

## Mis decisiones (a revisar)

1. Reutilizar `compare()` y `promote()` de `pitchapi_respaldo` mediante un adaptador, en vez
   de extraer una librería común. Menos riesgo sobre código ya en producción.
2. Tablas propias `fdorg_*` en vez de generalizar las de PitchAPI.
3. Clave solo por entorno en v1, sin cifrado en base ni formulario en `/control`.
4. Umbrales: 6 h para `result_pending`, 90 min para `kickoff_shift`, 72 h para avisar por
   calendario, ventana de 7 días atrás y 9 adelante.
5. Horarios 13:10 y 01:10 UTC.
6. Omitir prórroga y penales en la comparación de marcadores.

## Preguntas del titular

1. **¿Fase 2: que el respaldo rellene resultados?** v1 solo avisa. Rellenar es lo que
   convierte el respaldo en «respaldo» de verdad, pero toca la liquidación de picks y la
   cadena de hashes (`result_recorded_at` debe ser la recepción real). Si la respuesta es
   sí, se diseña aparte con plazo de gracia y sin sobrescribir.
2. **Términos del plan gratuito.** No los leí. Los datos solo se comparan y se guardan como
   original, no se republican; si el titular quiere uso estrictamente dentro de los
   términos, hay que revisarlos antes de activar.
3. **¿Panel?** ¿Quieres una sección de football-data.org en `/control/respaldo` (ver y
   marcar discrepancias como revisadas), o basta con las alertas de Telegram?
