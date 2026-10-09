# NBA — acceso histórico confirmado, 2026-10-05

El usuario confirma que su API es de pago. Además, **la prueba real con la clave existente confirma acceso a eventos históricos y props históricos de rebotes NBA**. Este documento actualiza el estado de la revisión anterior, que se conserva como evidencia de lo conocido entonces.

Se solicitó el estado del 2025-10-21 a las 23:00 UTC. El servicio devolvió un snapshot de las 22:55:40 UTC y el evento Houston Rockets–Oklahoma City Thunder, cuyo inicio programado figura a las 23:35 UTC. Se recibieron **242 cuotas, 17 nombres de jugadores y ocho casas**, agrupadas en 121 pares jugador/casa/línea con Over y Under. Solo se probó `player_rebounds`, una región y un partido; no acredita cobertura completa de todas las temporadas o mercados.

La prueba consumió **11 créditos**: uno para localizar eventos y diez para el mercado histórico. La cabecera final reportó **19,638 restantes** a las 21:44:31 UTC del 2026-10-05. Entre la revisión anterior y esta, el contador global aumentó tres créditos adicionales a los consumidos por esta prueba; su origen no se atribuye a NBA. La cuenta y su presupuesto siguen compartidos con fútbol. No se guardó la clave, no se cambió el plan ni se habilitaron descargas masivas.

Hay una discrepancia que se conserva para auditoría: tres mercados tienen actualizaciones de 7, 13 y 26 segundos posteriores al timestamp del snapshot. Todos siguen siendo anteriores a las 23:00 UTC solicitadas. Para un replay que decida exactamente a las 22:55:40, esos tres mercados se excluyen: quedan cinco casas y 154 cuotas compatibles con ese corte. No se corrigen ni se ocultan sus relojes. La captura recibida en 2026 tampoco se presenta como una recepción propia en 2025.

Esta fuente permite preparar el conjunto histórico de precios del experimento de rebotes. Antes de evaluar rentabilidad faltan el enlace verificado de evento/jugador con NBA, reglas de liquidación, tratamiento de DNP/void/prórroga y el protocolo de selección temporal. No se recalibró el modelo ni se promovió ningún contrato a pick. Los históricos publicados tienen resolución de cinco minutos; no reproducen movimientos de segundos. [Guía oficial V4](https://the-odds-api.com/liveapi/guides/v4/#get-historical-event-odds).

Evidencia:

- `apps/nba/.local/raw/the_odds_api/historical_entitlement_20261005T214429/manifest.json` y sus dos respuestas verificadas con SHA-256.
- `apps/nba/.local/reports/historical_odds_entitlement_20261005.json`: contraste de relojes y consumo.
- Registro de fases NBA y ledger independiente: acceso confirmado, puertas de validación pendientes.
