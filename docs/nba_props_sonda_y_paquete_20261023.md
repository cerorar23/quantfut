# NBA — sonda de props de jugador y paquete de The Odds API a comprar (23-oct-2026)

Resultado de lanzar una sonda real sobre el histórico de props de The Odds API, con una llamada por temporada, y de calcular qué plan hace falta. Complementa `docs/nba_props_jugadores_viabilidad_20261023.md`. Coste de la sonda: **110 créditos** (saldo 294 → 175, el resto es consumo normal de fútbol). Respuestas guardadas con hash en `apps/nba/.local/raw/nba_props_probe_20261023/` (no se versionan).

## Qué se sondó
Un partido por temporada, a 60 min del salto, región `us`, seis mercados de jugador (se cobran solo los que devuelven datos):
- 2024-25: Suns @ Hawks (14-ene-2025). **Seis mercados devueltos: 60 créditos.**
- 2025-26: Mavericks @ Suns (10-feb-2026). **Cinco mercados devueltos: 50 créditos** (no vino `player_steals`).

## Cobertura observada
Comparada con quién jugó de verdad según nuestros box scores (jugadores con ≥ 20 min: 13 y 14).

| Mercado | Casas (24-25 / 25-26) | Jugadores con ≥ 20 min con línea (24-25 / 25-26) | Minutos cubiertos (24-25 / 25-26) |
| --- | --- | --- | --- |
| Puntos | 7 / 8 | 100 % / 86 % | 93 % / 80 % |
| Rebotes | 7 / 8 | 100 % / 86 % | 93 % / 80 % |
| Asistencias | 7 / 8 | 92 % / 86 % | 87 % / 80 % |
| Triples | 7 / 8 | 92 % / 71 % | 83 % / 63 % |
| Tapones | 4 / **1** | 92 % / 57 % | 86 % / 57 % |
| Robos | 4 / **0** | 92 % / — | 86 % / — |

- **Emparejado de nombres:** 100 % (ningún jugador sin emparejar en ninguno de los dos partidos).
- **Acuerdo entre casas:** el rango de líneas entre casas tiene mediana 0,0 y máximo 1,0 punto: hay un consenso claro. Las líneas de puntos y rebotes las cotizan entre 5 y 8 casas según el jugador (no se calculó la mediana por mercado).
- **Lo que falta:** unos 15 jugadores por mercado y partido, es decir, los titulares y la rotación principal; los suplentes de poco rodaje no tienen línea. Robos y tapones son demasiado escasos (en 2025-26 solo BetMGM cotiza tapones y no hay robos): **no entran en el análisis principal**. Triples cae a 71 % de los jugadores de ≥ 20 min en 2025-26.
- **Coste:** se confirma 10 créditos por mercado devuelto y por llamada; con los cuatro mercados principales (puntos, rebotes, asistencias y triples) son **40 créditos por partido y snapshot**.
- Límites de la sonda: solo 2 partidos; indica la forma, no la tasa exacta de cobertura de toda la temporada.

## Escenarios (partidos: 2024-25 = 1.218; 2025-26 = 1.206; 2023-24 = 1.225)
Más un mes normal de fútbol (~15.000) y la captura en vivo NBA (~3.000).

| Escenario | Créditos | Total del mes | Plan mínimo |
| --- | ---: | ---: | --- |
| A. Piloto: 100 partidos × puntos y rebotes | 2.000 | 20.000 | 20K ($30) |
| B. Muestra: 400 partidos × 4 mercados, 1 snapshot | 16.000 | 34.000 | 100K ($59) |
| C. Dos temporadas × 4 mercados, 1 snapshot (T-60) | 96.960 | 114.960 | **5M ($119)** |
| D. C con 2 snapshots (T-60 y cierre) | 193.920 | 211.920 | 5M |
| E. D + `team_totals` (2 snapshots) + `totals` y `spreads` de Pinnacle | 249.225 | 267.225 | 5M |
| F. Dos temporadas × 6 mercados, 2 snapshots | 266.640 | 284.640 | 5M |
| G. E + 2023-24 (4 mercados, 2 snapshots) | 347.225 | 365.225 | 5M |

- Con el plan 100K, tras la parte de fútbol y la captura en vivo, quedan ~82.000 créditos: alcanzan para ~85 % de las dos temporadas en un solo snapshot, no para el escenario C completo. Dos meses de 100K ($118) cuestan lo mismo que un mes de 5M ($119) y dan menos.
- Escenario E ≈ 5 % de la bolsa del plan 5M. Líneas jugador-mercado esperables en C: ~145.000.
- Descarga de una pasada: ~2.400 llamadas, ~55 minutos y ~140 MB.

## Recomendación
**Comprar un mes del plan 5M ($119) coincidiendo con la renovación del 1-nov** y hacer en la primera semana el escenario E (props principales con 2 snapshots, `team_totals` y `totals`/`spreads` de Pinnacle), con protocolo congelado antes de gastar. Ventajas: es el único plan que cubre las dos temporadas completas; sobra más del 90 % de la bolsa, así que fútbol no vuelve a quedarse sin créditos ese mes; y el coste extra frente a 100K es de solo $60. En diciembre se vuelve al plan normal.
Orden dentro del mes: (1) piloto A el primer día para validar el flujo; (2) C; (3) el cierre y `team_totals`; (4) opcionalmente 2023-24 (escenario G).

Si se quiere gastar menos: el plan 100K ($59) alcanza para la muestra B (400 partidos), suficiente para una primera cifra pero con barras de error más anchas.

## Lo que sigue sin saberse
- Cobertura en toda la temporada (solo 2 partidos sondados) y en 2023-24.
- Si el mercado de The Odds API tiene Pinnacle para props: no (casas de EE. UU.). La referencia sería un consenso sin margen de 5-8 casas.
- Facturación de The Odds API al cambiar de plan (prorrateo, vencimiento de créditos no usados): confirmar en el panel antes de pagar.
