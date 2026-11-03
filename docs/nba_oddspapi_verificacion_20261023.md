# NBA — verificación de OddsPapi como fuente de props de jugador (23-oct-2026)

Qué se hizo: leer la documentación de `oddspapi.io` y probar con una clave real facilitada por el titular (no se guarda en ningún archivo). Pruebas mínimas: 19 peticiones facturables de las 250 mensuales de la cuenta (quedan 198) y varias llamadas gratuitas al histórico. Los archivos grandes descargados se borraron. Complementa `docs/nba_props_jugadores_viabilidad_20261023.md`.

## Veredicto
OddsPapi **no sirve para el backtest de dos temporadas** (2024-25 y 2025-26), pero sí para algo que The Odds API no da: **Pinnacle con props de jugador, con cada cambio de precio con su hora y el cierre real, de forma gratuita**. Es la mejor fuente para la prueba hacia delante y para una muestra retrospectiva de abril-octubre de 2026.

## Qué se verificó
| Pregunta | Resultado |
| --- | --- |
| ¿Funciona la clave? | Sí. Cuenta: 250 peticiones facturables al mes, 348 casas, sin precio, sin renovación automática, activa desde el 23-sep-2026. |
| ¿Cuesta el histórico? | **No**: `GET /v4/historical-odds` no mueve el contador (comprobado). Fixtures, mercados, jugadores, deportes y torneos cuestan 1 cada uno (también las respuestas 4xx). Espera de 5 s por llamada al histórico y 2 s en fixtures. |
| ¿Hasta cuándo hacia atrás? | La documentación dice «desde enero de 2026»; **en la práctica no**: con datos el 12-abr, 18-abr, 25-abr y 10-may-2026 (liga y playoffs) y el 20 y 21-oct-2026; **404** el 15-mar, 11-feb y 20-ene-2026 y el 18-nov-2025 (también con DraftKings, FanDuel y bet365). Entre el 15-mar y el 12-abr no se probó. No cubre las dos temporadas pedidas. |
| ¿Pinnacle cotiza props de jugador? | **Sí.** En Orlando–Atlanta (21-oct-2026): 28 mercados de jugador y 11 jugadores: puntos, rebotes, asistencias, triples y puntos+rebotes+asistencias. Sin robos ni tapones. Primer registro un día antes del partido y último en el inicio (cierre real). |
| ¿Y las casas de EE. UU.? | DraftKings ≈224 mercados de jugador, FanDuel ≈211, BetMGM ≈59, con robos y tapones. |
| ¿Qué trae cada registro? | `createdAt` (µs, UTC), `price`, `limit` (apuesta máxima) y `active`, por casa, mercado, resultado y jugador. Es historial tick a tick. |
| ¿Tamaño? | Pinnacle: ~8 MB y 73.000 registros por partido; DraftKings solo: >100 MB; tres casas de EE. UU.: 161 MB. Los registros posteriores al inicio son precios en juego: hay que cortar por `createdAt` < inicio. |
| ¿Cómo se emparejan jugadores? | `GET /v4/players?sportId=11` devuelve toda la base de baloncesto en una petición (~1 MB) con «Apellido, Nombre». Tres de tres IDs de los props se resolvieron (Wagner, Suggs, Daniels). El parámetro `participantId` se ignora. |
| Identificadores | Baloncesto `sportId` 11; NBA `tournamentId` 132; Pinnacle `pinnacle`; máximo 3 casas por petición. |

## Qué permite y qué no
- **Retrospectivo de dos temporadas:** no. Sigue dependiendo de The Odds API (un mes de 5M, $119) con consenso de casas de EE. UU. en lugar de Pinnacle.
- **Muestra retrospectiva gratuita:** los playoffs de 2026 (~85 partidos) con Pinnacle, algo de la última semana de liga y 2026-27: unas 2.500+ líneas de jugador, en un régimen distinto (playoffs). Coste: ~60 peticiones de fixtures (ventanas de menos de 48 h) + 1 de jugadores; el histórico es gratis.
- **Hacia delante (2026-27):** captura diaria de Pinnacle por partido terminado: 1 petición de fixtures al día (~30 al mes, cabe en 250) + histórico gratis (~10 partidos × 8 MB = ~80 MB por noche). Da apertura, cierre real y CLV de props frente a Pinnacle.

## Riesgos y lo que no se sabe
- Cuenta sin precio ni renovación automática: no se sabe si seguirá activa en noviembre; la página de precios no publica planes ni condiciones (solo una calculadora).
- No se leyeron los términos de uso; la propia web dice que cubrir todas las cuotas «no siempre está garantizado». Datos de terceros, solo para uso propio.
- La retención parece limitada y no se sabe si se borra con el tiempo: conviene archivar pronto.
- Los jugadores no traen equipo en `/v4/players`; el equipo sale del partido y de nuestro historial.
- Pinnacle no cubre robos ni tapones; para esos hace falta The Odds API o las casas de EE. UU.

## Siguiente paso propuesto
1. Colector con caché y topes (fixtures + histórico de Pinnacle) que archive los playoffs de 2026 disponibles y el goteo diario de 2026-27.
2. Comparador modelo-Pinnacle de props con protocolo congelado antes de mirar resultados, reutilizando la distribución del modelo de jugadores para la probabilidad de «más de» a cada línea.
3. Decidir si se compra además el mes de 5M para el retrospectivo de dos temporadas, o si basta con esto y la captura hacia delante.
