# Plan: sustituir Apify sin pagar (31-oct-2026)

Decisión del titular (31-oct-2026): no se vuelve a pagar Apify. Este plan se basa en consultas reales hechas el
31-oct a la base de producción, al índice del recolector y a cada API gratuita con las claves del titular.

## 0. Estado de partida: Apify ya está cortado

- Desde las **19:40 UTC del 31-oct** cada corrida devuelve `403 platform-feature-disabled: Monthly usage hard limit
  exceeded`. La cuenta tiene ahora un tope de 5 USD (plan gratuito) con 18,04 USD gastados en el ciclo 24-oct → 23-nov.
- Los crons del host siguen corriendo (`capture` 07:40 y `lineups` cada 10 min) y solo archivan ese 403.
- Desde el 24-nov el plan gratuito vuelve a dar 5 USD al mes. No entra en este plan, pero existe como reserva.

## 1. Qué hacía Apify y quién lo usaba de verdad

Inventario de consumidores en `main`, en el worker y en los motores del VPS (`~/quantfut-tenis`, `~/nba-isolated/live13`,
`~/quantfut-public-sports`):

| Deporte | Qué capturaba Apify | Quién lo lee en producción | Qué se pierde sin Apify |
|---|---|---|---|
| Fútbol | Detalle de terminados (xG, estadísticas) | `sofascore_partidos` | Nada: desde el 28-oct el 100 % del xG de `matches` viene de FotMob; el 30-31 oct aplicó 13 de 248 detalles |
| Fútbol | Once previsto/oficial y bajas | `sofascore_alineaciones` → `lineups`, `lineups_previstas`, `injuries` (`source='sofascore'`) | Ver abajo |
| NBA | Listados y box score (scrapesage) | **Nadie** | Nada. El motor NBA usa PropLine, ESPN, stats.nba.com (ZenRows) y The Odds API |
| Tenis | Torneos y estadísticas (scrapesage, rl1987) | **Nadie** | Nada de Apify. Pero el motor y la web dependen de **API-Tennis**, cuyo plan vence: ver fase T |

Lo único que hay que sustituir es el **once y las bajas de fútbol**. Lo leen:

- `sello_tardio`: ya acepta el once oficial de FotMob (`GREATEST` con `fotmob_previo.tipo_alineacion = 'standard'`) y
  sin once sella igual a T-25. **Sellar no se bloquea.**
- `odds_worker`: usa `lineups` (lados y hora) para las ventanas de cuotas tras el once.
- `api/fichas.py`: muestra once y bajas en la web y la app.
- `health.check_sofascore_lineups` (07:00 UTC): alertará por Telegram cuando la cobertura baje del 50 %.
- `lineups.availability`: compara contra historia de la misma fuente (`src` en cada titular).

## 2. Cobertura medida (25-oct → 31-oct, 173 partidos de ligas activas)

| | SofaScore (Apify) | FotMob (ya en producción) | Cualquiera de los dos |
|---|---|---|---|
| Once oficial capturado antes del saque | 148 (86 %) | 140 (81 %) | 161 (93 %) |
| Solo esa fuente lo tenía | 21 | 13 | |
| Partidos con bajas | 151 (6,6 por partido) | 167 (8,1 por partido) | |

FotMob trae el once oficial a una mediana de 45 min antes del saque (p10: 30 min). Los 21 que solo tenía SofaScore
están repartidos (Premier 4, Eredivisie 3, 2. Bundesliga 3, Serie A 3, LaLiga 2, Argentina 2…).

## 3. Fuentes gratuitas probadas el 31-oct

| Fuente | Cuota gratis | Qué sirve (probado) | Límite que importa |
|---|---|---|---|
| **FotMob** (`fotmob_captura`) | Sin cuota; ZenRows de respaldo | Once previsto/oficial, bajas, xG, estadísticas | 429 = pausa de 12 h; ZenRows 3.895/5.000 hasta el 6-nov (compartido con stats.nba.com) |
| **SportsAPIPro** | 100/día para todos los deportes | SofaScore sin transformar, **mismos ids**. Calendario del día (1 petición, 50 torneos de más prioridad: 69 partidos nuestros el 31-oct). Once con `confirmed` y `missingPlayers` (Milan–Inter a T-50: confirmado, 5 bajas por lado). Estadísticas con xG. Tenis con estadísticas | Torneos fuera del top 50: `/api/tournament/{id}/scheduled-events/{date}` |
| **SportsAPI365** | 100/día, 10/min, últimos 7 días | Fútbol: estadísticas con xG, mapa de tiros, once confirmado. Tenis: estadísticas. NBA: estadísticas y alineación | Listado paginado de 10 ligas por página |
| **API-Football** (clave del `.env`) | 100/día, 10/min | `fixtures?id=` trae eventos, alineaciones, estadísticas con xG y jugadores en **1 petición**, de cualquier fecha. Lesiones por fecha | Por fecha solo ayer, hoy y mañana; temporada en curso bloqueada; sin `ids=`. El `.env` dice 7.500/300: hay que bajarlo |
| **Highlightly** | Fútbol 100/día; NBA 100/día aparte | xG y alineaciones de fútbol; box score y alineaciones NBA | Sin lesiones ni cuotas |
| **Scraper local** (`~/sofascore-scraper`) | Sin cuota | Partido de fútbol: 13 solicitudes, ~11 s; tenis: 5, ~6 s; pico ~1,16 GB | Arranca con 403 y pasa por navegador; sin calendario por fecha; solo desde el 31-oct |

Descartadas: Live Tennis API (los terminados cuestan 9,99 USD/mes), TheSportsDB gratis (3 partidos por día, 5 filas de
estadísticas), ESPN (no aporta sobre PropLine ni trae ids de SofaScore).

## 4. Plan por fases

### Fase 0 — Hoy: dejar de depender de Apify sin peticiones nuevas
1. Quitar del crontab del host las dos líneas de `sofascore-apify` (respaldo del crontab y entrada en `DEPLOYS.md`).
   Los datos archivados se conservan.
2. **Puente FotMob → tablas de alineaciones** (nuevo `src/qf/ingest/fotmob_alineaciones.py`, cron cada 5 min tras
   `fotmob_captura previos`):
   - `lineups`: el último once `standard` con los dos lados, titulares con `src = 'fotmob'`.
   - `lineups_previstas`: cada captura previa, `source = 'fotmob'`, `confirmed = (tipo_alineacion = 'standard')`.
   - `injuries`: `fotmob_baja_previa`, `source = 'fotmob'`.
   - `lineups._fuente` reconoce `fotmob`, para que `availability` compare con historia de FotMob.
3. `health.check_sofascore_lineups` pasa a contar cualquier fuente, y el aviso deja de nombrar Apify.
4. En el worker, `sofascore_partidos` y `sofascore_alineaciones` quedan comentados con «RETIRADO» (ya no reciben datos).

Resultado esperado: once oficial en ~81 % de los partidos y bajas en ~97 %, sin coste.

### Fase 1 — Rellenar los huecos de FotMob con SportsAPIPro (10–20 peticiones/día)
1. Guardar la clave en `SPORTSAPIPRO_KEY` (`.env` local y del VPS, nunca en el repo).
2. A las 06:00 UTC, 1 petición al calendario del día. Se emparejan los ids de SofaScore con nuestros partidos usando las
   reglas de `sofascore_alineaciones` (misma competición, ±36 h, nombres parecidos, candidato único).
3. Un partido sin once `standard` de FotMob a T-35 se pide a SportsAPIPro a T-30 y, si sigue sin confirmar, a T-22. Son
   dos intentos como máximo, unos 3–6 partidos al día.
4. Se escribe en las mismas tablas con `source = 'sofascore'`: son los mismos ids que daba Apify, y la historia de
   `availability` sigue valiendo.
5. Tope propio de 40 peticiones al día. El resto de la cuota queda para la fase 2.

Resultado esperado: volver al ~93 % de once oficial que daban las dos fuentes juntas.

### Fase 2 — Respaldo de xG y estadísticas (solo si FotMob falla)
- Si a las 36 h un partido terminado sigue sin xG, se pide la estadística a SportsAPIPro (SofaScore, que coincide con
  FotMob en el 99 % de los casos) con un tope de 20 al día.
- Segundo respaldo: API-Football `fixtures?id=` (1 petición con todo incluido), con el listado de "ayer" para el id.
  Reintroducirlo es reabrir la decisión de fuentes únicas del 25-oct: lo decide el titular. Antes de usarlo, bajar
  `API_FOOTBALL_DAILY` a 100 y `API_FOOTBALL_RPM` a 10.

### Fase T — Tenis: sustituir API-Tennis antes de que venza su plan
El plan de API-Tennis vence pronto y no se renueva (el titular, 31-oct). **Falta la fecha exacta de vencimiento.**

Uso medido el 31-oct:

| Quién | Qué pide a API-Tennis | Cuánto |
|---|---|---|
| Motor (`tennis_intake_v1`, cron :25 de cada hora) | `get_fixtures` ATP/WTA de ayer a +2 días: calendario, resultados por set, ganador y `player_key` | Tope 26/día (2 corridas amplias + refrescos de resultados) |
| Web (`publicar_tenis_estadisticas.py`, cada 2 h) | `get_standings`, `get_players`, `get_H2H` con caché | 121 llamadas el 31-oct |
| Liquidación de picks de tenis | Resultados (PropLine califica mal el ganador en ~1 de 10 partidos a 3 sets) | Dentro de lo anterior |

Sustituto probado: **SportsAPIPro tenis** (datos de SofaScore):
- **Calendario y resultados:** `/v2/tennis/schedule/{fecha}`, 1 petición por fecha (225 partidos el 31-oct; terminados: 32 ATP y 24 WTA). Cada partido trae sets (`period1…`), `winnerCode`, estado, ronda, superficie (`groundType`), y ranking y país de cada jugador.
- **Rankings:** `/api/rankings` (ATP, 500 filas en 1 petición) y `/api/rankings/wta`.
- **Perfil:** `/api/teams/{id}` (mano, altura, edad) y `/api/teams/{id}/events/last/0`.
- **H2H:** no tiene endpoint para tenis. Se calcula del archivo propio de resultados, sin peticiones.

**Equivalencia de ids (lo crítico).** El motor y su historia usan el `player_key` de API-Tennis, y SofaScore tiene sus propios ids. Prueba del 30-oct:
- 15 de 16 partidos ATP/WTA se emparejan por nombre corto exacto (`K. Rakhimova` = `shortName` de SofaScore). El 16º (`J-L. Struff` / `J. Struff`) sale con apellido + inicial.
- 30 jugadores con un único id de SofaScore.
- El ganador coincide en los 8 terminados emparejados.

Pasos:
1. **T1, ya y mientras API-Tennis responda:** capturar SportsAPIPro en paralelo (3 fechas al día, 3 peticiones) y construir la tabla `player_key` ↔ id de SofaScore partido a partido. Los no emparejados se revisan a mano. Cada día antes del vencimiento suma jugadores cubiertos.
2. **T2:** adaptador del motor. `get_fixtures` pasa a leer SportsAPIPro con el mismo formato interno, usando la tabla. Un jugador nuevo sin equivalencia entra con su id de SofaScore, con prefijo para no chocar.
3. **T3:** web de estadísticas. Rankings 2/día, perfiles con caché de 7 días (ranking y país ya vienen en el partido) y H2H del archivo propio. Unas 10–15 peticiones al día en vez de 121.
4. **T4:** liquidación de picks con `winnerCode` y sets de SportsAPIPro.
5. **Desborde:** si un día falta cuota, los refrescos de resultados pasan a SportsAPI365, que tiene cuota propia de 100/día, tenis por fecha y estadísticas. Sus ids no son los de SofaScore, así que se empareja por nombre, como en T1.

Presupuesto de tenis en SportsAPIPro:
- Calendario de ayer y mañana: 2 al día.
- Refresco del día cada 3 h: 8.
- Rankings: 2.
- Perfiles: 5–10.

Total: **unas 17–22 al día**.

### Fase 3 — NBA (opcional)
Para producción no hay nada que sustituir. Solo si un modelo futuro pide box score de SofaScore: Highlightly NBA, con cuota propia, 1 petición de calendario y unas 8–15 de box score.

### Fase 1b — Scraper SofaScore local: archivo diario completo desde el 31-oct
Decisión del titular: el scraper (`~/sofascore-scraper`) cubre solo desde el 31-oct; el historial lo descarga y sube el
titular aparte, en el mismo formato (`data/v3`). Su papel:
1. **Archivo diario** (05:30 UTC, una sola ejecución con `flock` y `nice`):
   - Descarga los partidos terminados de ayer de las 17 competiciones activas con todos sus bloques: estadísticas, once,
     incidencias, mapa de tiros, momento, posiciones medias y mejores jugadores.
   - Los ids salen del calendario de SportsAPIPro de la fase 1, sin peticiones extra, o de `ssc sync --tournament`.
   - Sirve para modelos futuros: la historia del titular y el día a día quedan en el mismo formato, y
     `sofascore_local.py` ya los normaliza.
   - Coste medido: ~45 partidos × 13 solicitudes ≈ 600 al día, unos 8–10 min (~20 min un sábado), pico de ~1,2 GB.
   - Tenis ATP/WTA y NBA se pueden añadir cuando un modelo lo pida: 5 solicitudes por partido de tenis.
   - No escribe en la base de producción hasta que se decida cargarlo.
2. **Reserva de emergencia del once:** si FotMob está en pausa por un 429 y SportsAPIPro agotó su cuota, se lanza a mano
   `ssc fetch event <ids>` de los partidos por sellar.
3. **No se usa para el once en vivo cada 5–10 min.** Cada ejecución arranca un navegador (~14 s y ~1,2 GB) para pasar
   Cloudflare, y repetirlo tantas veces al día arriesga el bloqueo de la IP del VPS.

### Fase 4 — Limpieza
- La cuenta Apify queda en el plan gratuito. Su archivo `~/sofascore-apify/data` se conserva por la historia.

## 5. Presupuesto diario

| Fuente | Uso | Peticiones/día | Cuota | Margen |
|---|---|---|---|---|
| FotMob | Ya corre: previos, posteriores, resultados | sin cambio | — | — |
| SportsAPIPro | Fútbol: calendario + huecos de once (+ xG si falla FotMob). Tenis: calendario, resultados, rankings y perfiles (fase T) | 15–40 + 17–22 = 32–62 | 100 | 38–68 |
| SportsAPI365 | Desborde de los resultados de tenis | 0–10 | 100 | 90+ |
| API-Tennis | Hasta que venza: solo para la tabla de equivalencias (T1) | ≤26 + 121 (hoy) | Plan de pago que vence | — |
| API-Football | Solo si el titular lo aprueba | 0–20 | 100 | 80+ |
| Highlightly NBA | Opcional | 0–17 | 100 | 83+ |
| Scraper local | Archivo diario 05:30 UTC + reserva del once | ~600 (≈1.000 en sábado) | ritmo 1/s | sin cuota; riesgo de bloqueo de IP |

Coste mensual: **0 USD** (Apify Starter costaba 19 USD/mes y el ritmo real del ciclo iba a ~45 USD/mes).

## 6. Riesgos

- **FotMob pasa a ser la fuente principal.** Un 429 pausa 12 h, y en ese caso SportsAPIPro cubre el once de los partidos
  que se sellan. Con 100 al día no da para todos en una jornada grande. El scraper local es el último recurso.
- **ZenRows** está en prueba con 3.895/5.000 créditos hasta el 6-nov y lo comparten FotMob (respaldo) y stats.nba.com
  (motor NBA). Hay que revisar qué pasa el 6-nov.
- **SportsAPIPro y SportsAPI365 son revendedores no oficiales de SofaScore.** Sus cuotas gratis pueden cambiar.
- **Ids de jugador de FotMob distintos a los de SofaScore.** `availability` empieza sin historia de FotMob en `lineups`
  salvo que se rellene desde `fotmob_jugador_partido`.
- **Las claves pegadas en el chat** van al `.env`, no a documentos.

## 7. Cómo se mide el éxito (7 días después de cada fase)

- Once oficial antes del saque ≥ 90 % (hoy, con las dos fuentes: 93 %; con solo FotMob: 81 %).
- Bajas en ≥ 95 % de los partidos.
- xG en `matches` ≥ 98 % a las 36 h.
- Ninguna alerta de `health` por alineaciones y ninguna petición a Apify.
