# Auditoría de consumo de APIs — 28-oct-2026

Alcance: cuotas, calendario, resultados, estadísticas y alineaciones de fútbol, NBA y tenis, para la app y la web.
Todo medido en producción el 28-oct (logs del host y del worker, SQLite de los recolectores, Postgres) salvo donde se dice.
Código de referencia: `main` en `3cbc63e`; producción corre `4907a0d` (está en `main`).

## 1. Qué consume cada proveedor

| Proveedor | Quién lo llama | Consumo medido | Límite | Estado |
|---|---|---|---|---|
| **PropLine** (cuotas, calendario, resultados, cierres, box score, bajas NBA) | `~/propline-shared` (host, cron `:07` cada hora) | 26-oct 2.756 · 27-oct 2.742 · 28-oct (17 corridas) 1.930 llamadas | 5.000/día, tope local 4.500, reserva 500 | Sano: 0 paradas por reserva desde el 26-oct |
| **Apify / SofaScore** (once, bajas, detalle de partidos, NBA y tenis) | `~/sofascore-apify` (host) | 1,0-1,1 USD/día (24-oct: 3,0; 25-oct: 2,4) | 15 USD «cuenta Apify» (límite duro de la cuenta: 19) | **Error corregido** (ver 2.1) |
| **API-Tennis** (estadísticas de jugadores para la web, calendario del estudio) | `publicar_tenis_estadisticas.py` (host) | 57-68 llamadas/día | tope diario propio | Sano |
| **FotMob** (marcador en vivo, cierre al pitido, `completar`) | worker: `live` cada 5 min, `fotmob_captura` | 1 petición por pasada de `live`; 0 errores en 10.631 líneas de log | enfriamiento de 12 h ante 401/403/429 | Sano |
| **ZenRows** (stats NBA oficiales) | `apps/nba` / contenedor de estadísticas NBA | `nba-stats` cada 30 min, 49 eventos, sin errores | créditos de la cuenta | Sano |
| **The Odds API** | `rafagas` y `odds_worker` | **0**: con `ODDS_PROVIDER=propline` ambos salen sin llamar | 20.000 créditos/mes | Solo históricos autorizados |
| **API-Football** | ningún cron | 0 (plan gratuito, jobs retirados el 22-oct) | — | Los errores de `results`, `fixtures`, `standings` y `live` en los logs son del 24-25-oct, antes del cambio |

### PropLine por tipo de llamada (27-oct, un día completo)

| Llamadas | Para qué |
|---|---|
| 1.909 | `soccer_*/odds` (33 competiciones; 17 cada hora, el resto cada 6 h) |
| 212 | `soccer_*/scores` |
| 192 | `basketball_nba/odds` (8 lotes por hora) |
| 48 | `tennis/odds` |
| 79 + 79 | cierre y resultados de tenis |
| 36 + 36 + 35 | `ids`, `futures`, `markets` de fútbol |
| 24 | `injuries` NBA · 24 `/v1/sports` |
| ~50 | cierre, resultados y box score de NBA y fútbol |

Fútbol son 1.909 de 2.742 (70 %). De sus 4 lotes por liga y hora, el primero (`h2h/spreads/totals`) trae lo que leen los motores; los otros tres (córners, tarjetas, jugadores) traen 2.500-13.500 selecciones por llamada y solo importan cerca del partido.

## 2. Errores encontrados y corregidos

### 2.1 Recolector SofaScore: los detalles de partidos no se pedían desde el 26-oct (CORREGIDO)
- Síntoma: `presupuesto agotado` los días 26, 27 y 28 en `cron.log`; 433 partidos terminados de los últimos 14 días sin estadísticas ni xG (NBA 56, MLS 53, tenis 39 por torneo…). Detalles pedidos: 6 el 25-oct, 1 el 26, 0 el 27 y 28.
- Causa: `capture()` listaba todos los objetivos primero y `budget_left()` restaba el gasto de las listas (~1 USD/día) del tope de la corrida (1,20 USD); al llegar a `details()` quedaba menos de 0,10 USD y lanzaba `Stop`.
- Corrección (`src/qf/ingest/sofascore_apify.py`): (a) las listas reservan el 50 % del tope de la corrida para los detalles (`detail_reserve`); (b) los detalles se piden aunque las listas se corten; (c) el gasto de la corrida se reparte: tope mensual restante entre los días que quedan del ciclo de Apify (`monthlyUsageCycle.endAt`); (d) 1,0 USD del tope mensual queda reservado para las alineaciones (`lineups_reserve_usd`), que lee `sello_tardio`. Pruebas nuevas: 3.
- **Pendiente de decisión del titular (gasto):** el ciclo de Apify empezó el 24-oct y la cuenta lleva 13,20 USD de 15; el colector solo registra 8,59 USD en sus recibos, así que unos 4,6 USD vienen de otros usos de la cuenta. Con el tope en 15 el ritmo diario permitido es ~0,03 USD y las listas y detalles no se ejecutan hasta el 24-nov; las alineaciones siguen (reserva). Subir `monthly_cap_usd` hasta el límite de la cuenta (19) da ~0,2 USD/día.

### 2.2 Alias de PropLine sin registrar (CORREGIDO, `db/090`)
- `Racing de Santander` (La Liga) y `Tromsoe` (Eliteserien) quedaban sin resolver cada hora (78 y 22 veces entre el 25 y 28-oct): sus partidos sin cuotas ni cierre. Alias `propline` añadidos y registrados en `correcciones_identidad`.
- No se registran: los clubes de Champions y Europa League de ligas que no cubrimos (AEK, Slavia, Sparta, Lech…; las copas no dan de alta equipos, ver CLAUDE.md) ni `Deportivo`, que no existe en `teams` (darlo de alta es una decisión de datos aparte).

### 2.3 Sin error: lo que parecía un fallo
- Logs de `results`, `fixtures`, `standings`, `live`, `rafagas`: los errores son del 24-25-oct (API-Football en plan gratuito). Desde entonces las pasadas de hoy salen sin error.
- Partidos huérfanos (programados o en vivo, >6 h, últimos 14 días, ligas activas): **0**. Terminados sin goles: **0** de 435.
- `alta_prob` del job diario: el `AttributeError: estadisticas_mercado.disponible` es del 24-oct; el job de hoy selló 22 selecciones sin error.
- Seguridad (ya anotado en `PENDIENTES.md`): `rafagas.log` del 24-oct contiene la clave de The Odds API dentro de una URL; ya no se escribe ahí, pero sigue pendiente rotarla.

## 3. Ahorro de llamadas aplicado

`scripts/propline_shared_config.json` + `propline_shared.py`:
- `extended_horizon_hours: 48` y `extended_far_every_hours: 6`: córners, tarjetas y jugadores solo se piden cada hora en ligas con un partido en las próximas 48 h (o ya empezado); sin partido cercano, cada 6 h. La primera petición (cuotas principales) sigue cada hora y es la que leen los motores. Estimación: 40-60 % de las ~1.430 llamadas de los lotes ampliados de fútbol (~600-850 al día).
- `futures_daily: false`: 36 llamadas al día que ningún código lee.
- Prueba nueva: `test_extended_markets_wait_for_the_horizon_and_then_follow_a_slow_cadence`.

## 4. Plan de eficiencia (lo que falta, por orden de valor)

1. **Verificar el ahorro** (28-29-oct): comparar llamadas/día de `soccer_*/odds` tras el despliegue con las 1.909 de base; criterio de cierre: ≤1.300 y cero huecos en la primera petición de cada liga.
2. **Scores de fútbol** (212/día): solo las competiciones prioritarias los necesitan para liquidar; si el ahorro del punto 1 no basta, pasar las demás a la cadencia de sus cuotas (ya ocurre con `other_sports_every_hours`).
3. **Lotes de fútbol de 13 mercados** (`soccer_markets_per_request`): los dos últimos devuelven 2.500-3.400 selecciones de media. PropLine admite 50 claves por petición, pero la NBA dio 504 con lotes grandes (23-25-oct): probar 20 en una sola liga con medición antes de generalizar.
4. **Apify**: decidir el tope mensual (2.1). Con el reparto diario, el coste del colector baja de ~1 USD/día a lo que permita el tope; el detalle de NBA y tenis cuesta lo mismo en la lista que aparte (scrapesage cobra por partido), así que a futuro conviene pedir estadísticas ya en la lista de esos dos deportes.
5. **Vigilancia**: `account_reserve` de 500 y la cuota diaria ya se registran por corrida; añadir alerta si `soccer_*/odds` supera 1.600 llamadas/día o si el Apify de un día no pide detalles habiendo terminados pendientes.
