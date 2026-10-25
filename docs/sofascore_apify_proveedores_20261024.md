# SofaScore vía Apify: proveedor por deporte (decisión del titular, 2026-10-24)

## Decisión

| Deporte | Actor Apify | Motivo |
|---|---|---|
| NBA | `scrapesage/sofascore-scraper` | Estadísticas de equipo, jugadores, goles/incidentes; histórico por `seasonIds` |
| Tenis | `scrapesage/sofascore-scraper` | Saque y resto (aces, dobles faltas, puntos de break, tiebreaks) |
| Fútbol | `rl1987/sofascore-api-scraper` | Alineaciones con ~127 métricas por jugador (xG, xA, sprints, km), estadísticas por periodo (total/1T/2T), árbitro, bajas con motivo |

`azzouzana/sofascore-scraper-pro` queda **descartado**: está publicado y se ejecuta, pero todas las URLs
devuelven `NO ND script found` (comprobado en consola Apify el 24-oct, 4 ejecuciones, build 0.0.14).

## Evidencia (prueba del 24-oct, 2–3 partidos por deporte; no es una auditoría)

- `scrapesage`, fútbol (Premier): xG, posesión, tiros, jugadores con valoración y xG, goles/tarjetas.
  Histórico Premier 24/25 (`seasonIds=[61627]`): 2 partidos de mayo 2025 con xG completo.
- `scrapesage`, NBA (`tournamentIds=[132]`): rebotes, asistencias, triples, robos, pérdidas, jugadores.
- `scrapesage`, tenis (París Masters ATP, id **2404**): aces, dobles faltas, % primer saque, break points.
- `rl1987`, fútbol: `statistics` por periodo y `lineups` por jugador; el más profundo.
- `rl1987`, NBA: en esta prueba (modo `tournament`) solo devolvió 1 partido, con incidentes y sin estadísticas;
  la prueba del 23-oct con `event_detail` sí traía box score. Por eso NBA va a `scrapesage`.
- `rl1987`, tenis: 3 partidos con estadísticas; empate con `scrapesage`.

## Límites y trampas

- Ids de torneo: Premier 17, NBA 132, ATP París **2404** (el 1415 de la URL no es el id: ambos actores devuelven vacío).
- `scrapesage` informó 3 partidos en tenis y el recuento del dataset mostró 1: no se resolvió si fue retraso del
  contador. Verificar `itemCount` y filas antes de confiar en un lote.
- xG solo donde SofaScore lo publica; en ligas menores/latinoamericanas puede venir vacío.
- Ninguno trae hora de captura fiable: para point-in-time hay que registrar nuestra propia recepción (`fetched_at`).
- `rl1987` exige `maxTotalChargeUsd` ≥ 0,10 USD por corrida; limitar el gasto con `maxItems`.
- Precios (nivel Bronze): `scrapesage` 0,00174 USD/partido; `rl1987` 0,003 USD/fila + 0,0015 por enriquecimiento
  (plan gratis: 0,0048 / 0,0024). El gasto real de la prueba no se midió: mirar el saldo en la consola.
- Cuenta Apify: plan de pago (aclaración del titular, 24-oct); el saldo de 0,36 USD que cité era del plan gratis y ya no aplica.

## Pendiente

- Probar histórico de NBA y tenis por temporada con `scrapesage` en un lote pequeño.
- Probar histórico de fútbol con `rl1987` (`seasonId`).
- Normalizar a nuestro esquema y registrar recepción real; no entrena ni promueve nada por capturar.
- Recolector del VPS adaptado y desplegado el 24-oct (ver DEPLOYS.md); no conectado a motores.
