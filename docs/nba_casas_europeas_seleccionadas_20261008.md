# NBA: casas europeas seleccionadas — 2026-10-08

La petición del usuario incorpora estas cuatro versiones al proyecto:

| Casa solicitada | Identificador The Odds API | Región del proveedor | País identificado |
|---|---|---|---|
| 1xBet Europa | `onexbet` | `eu` | No determinado por el catálogo |
| Betsson Europa | `betsson` | `eu` | No determinado por el catálogo |
| Codere Italia | `codere_it` | `eu` | Italia |
| Betano Reino Unido | `betano_uk` | `uk` | Reino Unido |

Identificadores contrastados con el [catálogo oficial](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html).
La selección está en `apps/nba/src/nba/odds_sources.json`, distribuida con el
paquete. `python -m nba odds-source-plan` permite revisarla sin red ni claves;
con un ID de evento genera las solicitudes concretas. La prueba de consola
usó un ID ficticio de 32 letras `a`; no representa un partido recuperado.

`BoundedOddsCapture.request_selected` aplica el filtro
`bookmakers=onexbet,betsson,codere_it,betano_uk` a solicitudes por evento.
Conserva el presupuesto explícito de cada captura, reserva antes de consultar,
verifica cuota de cuenta, detiene fallos y guarda parámetros sin secretos.
No se activó captura periódica ni se realizaron nuevas consultas The Odds API.

Según la [documentación de la API](https://the-odds-api.com/liveapi/guides/v4/),
hasta diez casas explícitas cuentan como una región equivalente. Para la
selección actual, descubrir mercados reserva un crédito; consultar hasta tres
mercados reserva hasta tres créditos por evento actual o treinta por corte
histórico. El endpoint de descubrimiento contiene claves recientes, no precios
ni un inventario completo de cobertura. La captura real requerirá un lote y
presupuesto explícitos; el piloto anterior ya concluido no se reinició.

La [documentación NBA](https://the-odds-api.com/sports-odds-data/nba-odds.html)
anuncia props individuales para casas estadounidenses y australianas. La
presencia de las cuatro casas seleccionadas en el catálogo no acredita props
NBA disponibles, cobertura histórica, contratos mexicanos ni reglas de
liquidación aplicables. Las consultas de puntos/rebotes/asistencias siguen
siendo investigación de cobertura desconocida. Ningún precio o jugador se
admite para operar por esta incorporación.

Validación: 33 pruebas pertinentes pasaron, con transporte simulado para
verificar filtro, recibos y límites de créditos; el plan de consola se ejecutó
offline. Los resultados del arnés y la preservación están en el checkpoint
NBA-RUN-062. Revisión por el mismo autor; no es aprobación independiente.
F6 permanece abierta y F7 sin iniciar. La exclusión de nuevas copias periódicas
sigue vigente.
