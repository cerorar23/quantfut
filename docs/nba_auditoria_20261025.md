# NBA — tercera auditoría: motor, props, datos en vivo, cierres y créditos (25-oct-2026)

Pedido del titular: auditar a fondo el motor NBA y las props de jugador, las fases, si la data llega en vivo y al cierre
y completa, si todo está conectado al motor, si las cuotas se capturan bien y si los créditos de las API se gastan sin
desperdicio; **corregir y desplegar lo que salga, sin dejarlo pendiente**. Medido en el servidor entre 21:00 y 22:30 UTC.
Auditorías anteriores: `docs/nba_auditoria_motor_20261021.md` y `docs/nba_auditoria_motor_20261023.md` (sus errores
1-8 ya se corrigieron en 1.3.1, PR #91).

## Resumen

| # | Gravedad | Hallazgo | Estado |
|---|---|---|---|
| 1 | alta | **Despliegue 1.4b a medias**: el panel corría `20261025b` desde las ~02:00 UTC, pero el productor seguía con los datos y el modelo 1.4.0; `main` (#114) dice que el vivo usa RUN071 + columnas y pérdidas. Sin entrada en `DEPLOYS.md` | Completado 21:34 UTC tras ensayo |
| 2 | alta | La petición principal de PropLine para NBA (ganador/hándicap/total con todos los periodos, ~120 partidos y 64.000 cuotas) da **504 en 9 de 47 horas**, casi siempre entre 19 y 01 UTC, justo cuando se sella. La cohorte `2026-10-25_1530` (Lakers–Jazz) se selló **sin hándicap ni total** (`game_lines.lines = {}`): las variables de entorno de los jugadores entraron como 0 | Reintento con solo partido completo |
| 3 | alta | **La reserva de 500 peticiones de PropLine corta la pasada de las 23:07 UTC**: hoy quedaban 594 tras la de las 21:07 y cada pasada gasta ~93-122. Sin la captura de las 23:07, los partidos de 00:35-01:35 UTC (los de las 20:00-20:30 ET desde el cambio de hora del 1-nov) se sellan sin líneas de jugador (el protocolo exige un archivo de ≤ 65 min) | Ahorro de ~150 peticiones/día |
| 4 | media | Peticiones de PropLine sin ningún dato: el Mundial (y otras sin partidos) pide sus 3-4 lotes de mercados aunque la petición principal ya dijo 0 partidos (63-103 llamadas/día); los marcadores de las competiciones sin motor se pedían cada 3 h (252 llamadas de marcadores de fútbol el 25-oct) aunque nada los liquida | Corregido |
| 5 | media | **El panel deja en «validation_hold» para siempre un partido cuyo salto se movió más tarde**: Rockets–Spurs (0022600009, 23-oct) se selló para las 01:30 UTC y la página final dice 02:30. Sus 4 pronósticos no se puntuaban | Corregido (un salto adelantado sí se retiene) |
| 6 | media | La captura de precios con The Odds API (`price.sh`, cron cada 5 min) empezaría a gastar créditos de fútbol el 1-nov, contradice la decisión del 23-oct (PropLine es la fuente fija de cuotas en vivo) y su libro de 2 peticiones/día rechazaría casi todas las cohortes por partido. Pinnacle ya llega por PropLine (h2h, hándicap, total y puntos de jugador) | Cron retirado |
| 7 | media | El productor 1.4b pica ~573 MB de memoria con un límite de 512 MB (1.4.0: ~499 MB): sobrevivía usando swap; con más partidos o más historia lo mataría el límite y ese día no se sellaría nada | Límite a 1 GB |
| 8 | baja | `apps/nba/ops/live13_producer.sh` del repo seguía con la imagen `20261023` (el servidor usaba `20261025`) | Alineado |

Sin cambio, documentado: el mercado de **pérdidas** (1.4b) no produce pronósticos en vivo porque en PropLine solo lo
cotizan PrizePicks y Dabble (DFS, excluidas por el protocolo, que pide ≥ 2 casas); dos cierres NBA de PropLine
(Bulls–Raptors 21-oct y Nuggets–Thunder 22-oct, fechas ET) devolvieron 504 dos veces y quedan con un tercer intento automático.

## 1. ¿Llega la data en vivo? (productor)

| Día (ET) | Partidos | Sellados | Faltan | Motivo |
|---|---|---|---|---|
| 20-oct | 3 | 0 | 3 | antes de que existiera el productor |
| 21-oct | 11 | 11 | — | |
| 22-oct | 2 | 2 | — | |
| 23-oct | 12 | 11 | 1 (partido de las 16:00 ET) | sellado único de las 17:35 ET (error 1 de la auditoría del 23-oct, ya corregido en 1.3.1) |
| 24-oct | 8 | 5 | 3 | caída por el minutaje `10:60` (ya corregida en 1.3.2, ver `DEPLOYS.md`) |
| 25-oct | 7 | 5 a las 21:35 | — | los 2 restantes se sellan a las 22:00 y 23:30 UTC |

- Cada partido se sella 65-90 min antes de su salto con el reporte oficial de lesiones más reciente que cuenta
  (≥ 60 min antes): 25-oct 15:30, 16:30 y 17:30 ET aplicados.
- Resultados oficiales: los 29 partidos sellados del 21 al 24-oct tienen su recibo de nba.com; los del 25-oct se
  capturan 3 h después del salto.
- Pronósticos por partido: 4 de equipo + 59-127 de jugador según las líneas disponibles (25-oct: 91, 94, 111, 112 y 127).
- Calidad hasta hoy (440 evaluados, muestra pequeña): ganador Brier 0,197 (n=28), puntos de equipo 0,214, total
  0,241, jugadores 0,225-0,277 (n=41-55 por mercado). Ningún mercado tiene muestra para concluir; se sigue midiendo.

## 2. ¿Llega el cierre y está completa la data? (PropLine, archivo común)

- Capturas horarias NBA: 8 peticiones por hora (principal + puntos, rebotes, asistencias por separado + 4 lotes),
  ~176-185 al día, **6 % del total**; las props llegan para todos los partidos del día siguiente.
- Liquidación (cierre `/odds/closing`, resultados `/results`, box score `/stats`) de cada partido NBA terminado del 21
  al 24-oct (ET): 31 de 33 con cierre (~28.000-33.000 cuotas por partido, props incluidas), 33 de 33 con resultados y box.
- El cierre de PropLine se archiva pero el motor no lo usa: por decisión del titular (23-oct) el motor NBA se mide
  contra el resultado real, no contra el mercado.

## 3. ¿Está toda la data conectada al motor?

| Dato | Entra en el motor | Cómo |
|---|---|---|
| Box scores históricos (RUN071) + tiros, pérdidas, rebote ofensivo y posesiones | sí (desde 1.4b) | `data/` del productor; ritmo, defensa rival y tendencia de uso ya pesan |
| Box scores de 2026-27 (nba.com) | sí | caché `completed()`, se suman a la historia de jugadores |
| Reportes oficiales de lesiones (antiguos + T-60) | sí | ajuste y sellado |
| Hándicap y total de bet365 (BetsAPI) | sí, en el ajuste | variables de entorno del jugador |
| Líneas de jugador y de partido de PropLine | sí, al sellar | umbral de cada prop y entorno |
| Cierres, resultados, box y lesiones de PropLine | no | archivo para reentrenar; el motor usa nba.com |
| SofaScore NBA (scrapesage) | no | 36 partidos listados, 0,06 USD; nba.com es la fuente oficial |
| Props históricos (The Odds API, plan 100K) | no en vivo | estudios `props_residual`/`props_vs_market` |

## 4. Créditos de las API

| Proveedor | Consumo medido | Desperdicio encontrado | Acción |
|---|---|---|---|
| PropLine (5.000/día, reserva 500) | 3.762 (24-oct) y 3.839 (25-oct); NBA ~180, fútbol ~3.400 | 504 que cuentan como gastados; lotes tras una principal vacía (63-103/día); marcadores de ligas sin motor cada 3 h (~80-120/día) | reintento barato, salto de lotes vacíos y marcadores al ritmo de sus cuotas |
| The Odds API fútbol (20.000/mes) | — | `price.sh` NBA gastaría desde el 1-nov | cron retirado |
| The Odds API NBA (100.000/mes) | 97.145 usados, **2.855 restantes**; la descarga de props terminó, nada lo sigue usando | — | — |
| Apify (SofaScore) | NBA 0,06 USD desde el 20-oct | — | — |
| BetsAPI | plan caducado el 25-oct 05:15; cron quitado | — | — |
| nba.com | gratis; caché de partidos finales | — | — |

## 5. Fases del plan NBA (`docs/nba_plan_fases_auditable.md`)

F0-F3 (alcance, aislamiento, fuentes e ingesta point-in-time) y F4-F5 (minutos y distribución calibrada) están hechas
y en producción; F6 (sellado, cohortes, recibos) corre en el VPS; **F7 (validación prospectiva) está en curso** desde
el 21-oct con 9 cohortes; F8 (lesiones y rol) entra por los reportes T-60; F9 (operación evaluada) es el panel `/nba`.
La línea de `PENDIENTES.md` «fases F0 a F9 sin empezar» estaba desactualizada.

## 6. Qué se cambió (detalle en `DEPLOYS.md`)

- Productor: datos y modelo 1.4b (`model.json` `5314c9ef…`), imagen `nba-live13-producer:20261025b`, memoria 1 GB.
  Ensayo previo con la hora real sobre los 3 partidos de las 23:00 UTC: mismos 362 pronósticos que el 1.4.0 real.
- Panel: un salto movido más tarde ya no retiene el resultado.
- Recolector de PropLine: reintento sin periodos cuando la principal falla, salto de lotes tras una principal vacía y
  marcadores de competiciones sin motor cada 6 h.
- Cron: retirada la captura de precios con The Odds API.
