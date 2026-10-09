# Revisión real de The Odds API para NBA — 2026-10-05

**La clave existente de fútbol responde también para NBA y pretemporada.** Se usó exclusivamente para consultas de lectura: no se guardó la clave en reportes o URLs, no se modificó el cliente de fútbol y no se activó polling continuo. El gasto total comprobado fue **cuatro créditos**, quedando **19,652** a las 21:35:53 UTC. El consumo y saldo pertenecen a la misma cuenta que usa fútbol; no se verificó su fecha de reinicio ni el nombre comercial del plan.

## Comprobaciones realizadas

| Consulta | Resultado | Créditos |
|---|---|---:|
| `/v4/sports?all=true` | NBA y NBA Preseason activas | 0 |
| `/v4/sports/basketball_nba/events` | 46 eventos de NBA regular listados | 0 |
| `/v4/sports/basketball_nba_preseason/events` | Ocho eventos de pretemporada listados | 0 |
| Mercados de Memphis @ Atlanta, 2026-10-05 23:00 UTC, región `us` | Mercados de partido/cuarto/mitad y props alternativos | 1 |
| Cuotas de tres props alternativos del mismo evento, región `us` | DraftKings: 22 opciones Over de Jalen Johnson | 3 |

Las 22 opciones se reparten entre `player_points_alternate`, `player_rebounds_alternate` y `player_assists_alternate`. No son 22 jugadores ni 22 mercados independientes. No había los tres mercados estándar en la consulta de descubrimiento; esa lista refleja mercados vistos recientemente y no garantiza disponibilidad exhaustiva. Solo se consultó un partido y una región.

Todos los mercados de props devueltos indicaban `last_update=2026-10-05T21:32:40Z`; la captura terminó a las 21:35:53 UTC: unos **193.6 segundos** de antigüedad. Se conserva este faltante frente al límite local de 60 segundos. La hora de recepción no se sustituye por la de actualización. No hubo opciones Under en la muestra, reglas verificadas de liquidación o IDs oficiales de jugador: **cero contratos promovidos a picks**.

## Encaje en el modelo

La [documentación específica NBA](https://the-odds-api.com/sports/nba-odds.html) y el [catálogo de mercados](https://the-odds-api.com/sports-odds-data/betting-markets.html) confirman puntos, rebotes, asistencias y segmentos. El cliente NBA debe elegir `basketball_nba` para la temporada regular y `basketball_nba_preseason` para esta pretemporada, con métricas separadas. Los props se consultan por evento; el endpoint agregado que utiliza fútbol para `h2h,totals,spreads` no basta por sí solo.

La [guía V4](https://the-odds-api.com/liveapi/guides/v4/) distingue consultas actuales por evento de históricos. Los históricos de props/segmentos comienzan después de 2023-05-03T05:30:00Z, requieren plan de pago y ofrecen snapshots de cinco minutos. No se descargaron históricos ni se probó el permiso histórico concreto de esta cuenta. No se infiere acceso histórico solo del saldo.

El [intervalo publicado](https://the-odds-api.com/sports-odds-data/update-intervals.html) para props y mercados adicionales es de 60 segundos. La muestra demuestra que la antigüedad efectiva puede ser mayor. Es una fuente para investigación y vigilancia de precios; no acredita ventaja al reaccionar en segundos a lesiones. Consultar más rápido no elimina el retraso del dato recibido.

El [listado de operadores](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html) requiere atención a la región: `codere_it` es Italia, no Codere México; Bet365 AU tiene cobertura específica limitada; Caliente no figura en la lista revisada. Las cuotas de DraftKings no acreditan que el usuario pueda tomar esa misma cuota en su operador local. Tampoco se convierten multiplicadores DFS en precios de apuestas convencionales.

## Presupuesto e integración siguiente

Para props actuales, una región y tres mercados devueltos consumen tres créditos por evento/consulta. **Ejemplo calculado:** cinco partidos consultados una vez por minuto durante tres horas consumirían hasta `5 × 180 × 3 = 2,700` créditos en esa jornada, antes de fútbol. No se activó ese patrón. Los históricos cuestan diez veces el componente de mercados/regiones por snapshot; no debe iniciarse una descarga masiva con este saldo compartido.

La integración siguiente requiere un cliente NBA independiente y una reserva coordinada de créditos de la cuenta, con topes de gasto y ventanas de captura. Debe conservar snapshot, recepción, actualización por mercado, identidad del evento/jugador, ambos lados cuando corresponda y reglas de operador. Los props alternativos de un solo lado deben tener su evaluación específica; no se fabrica un Under o un margen de la casa.

Los modelos, normalización y ledger se mantienen NBA. Reutilizar la clave comparte presupuesto y límites del proveedor; no implica usar las tablas o el selector de fútbol. F2/F3 tienen una fuente de cuotas comprobada y F6 sigue sin contratos comerciales validados.

## Evidencia local

Capturas con SHA-256 y ledger NBA:

- `apps/nba/.local/raw/the_odds_api/review_20261005T213349/manifest.json`: deportes, cuota de cuenta y eventos NBA.
- `apps/nba/.local/raw/the_odds_api/preseason_review_20261005T213511/manifest.json`: eventos/mercados de pretemporada.
- `apps/nba/.local/raw/the_odds_api/alternate_props_review_20261005T213553/manifest.json`: cuotas alternativas y gasto final.

Esta revisión no modifica código de aplicación ni parámetros del modelo. El incremento anterior conserva sus 100 pruebas NBA y 606 fútbol. No se envió ningún pick ni se realizó ninguna apuesta.
