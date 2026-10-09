# NBA: resultado real de las cuatro casas europeas — 2026-10-08

Se ejecutó la consulta autorizada por el usuario («hazlo») en la cuenta
existente de The Odds API. Ocho eventos: cuatro de pretemporada del 8 de
octubre y cuatro regulares del 20–21 de octubre. Filtro exclusivo
`onexbet,betsson,codere_it,betano_uk`; presupuesto nuevo máximo de 56 créditos.

| Versión consultada | Eventos con cuotas de equipos | Cuotas de equipos recibidas | Cuotas individuales PTS/REB/AST |
|---|---:|---:|---:|
| 1xBet Europa | 4 | 24 | 0 |
| Betsson Europa | 8 | 36 | 0 |
| Codere Italia | 0 | 0 | 0 |
| Betano Reino Unido | 3 | 12 | 0 |
| Total | 15 observaciones casa/evento | 72 | 0 |

«Cuota» aquí significa un precio decimal para una selección, no un partido
ni un par individual over/under. Los72precios corresponden a ganador,
hándicap y total de equipos. Se guardaron cuerpos originales, hashes,
recepción, reloj de proveedor y las selecciones recibidas en
`apps/nba/.local/raw/nba_european_books_run63_20261008` y
`apps/nba/.local/normalized/nba_f6_run63_20261008`.

Las ocho consultas directas de puntos, rebotes y asistencias respondieron 200
con lista de casas vacía. El descubrimiento reciente tampoco devolvió esos
mercados para las cuatro versiones. Codere Italia no devolvió mercados ni
precios en esta muestra, aunque su identificador está en el catálogo del
proveedor. No se atribuye el vacío a bloqueo de IP ni a una clave inválida:
hubo respuestas 200 y otras casas proporcionaron cuotas.

Esto verifica la captura de mercados de equipos para tres versiones y la
ausencia de props en la muestra. La [documentación NBA del proveedor](https://the-odds-api.com/sports-odds-data/nba-odds.html)
anuncia props para casas US/AU. Las versiones europeas no quedan acreditadas
como fuente de props individuales por estar incluidas en el catálogo.

Límites: los cuatro eventos de pretemporada tenían el horario de inicio
declarado ya pasado al consultar; los cuatro regulares aún estaban lejos del
inicio. No se demuestra ausencia universal de props, cobertura histórica,
disponibilidad final de jugadores ni equivalencia contractual con México.
No hubo cuotas individuales para admitir ni se retrofecharon recepciones.

Consumo real: 29/56 créditos en 27 solicitudes HTTP, 16 con cargo. Las otras once
fueron tres consultas de catálogo/cuenta y ocho consultas individuales sin
precios. Sin errores, reservas pendientes ni reintentos automáticos. No se
contrató un plan, activó captura periódica, cambió el VPS o publicaron apuestas.
Nuevas copias periódicas siguen excluidas por el usuario.

Verificación offline de 27 recibos y 72 precios; 33 pruebas pertinentes correctas.
Revisión del mismo autor, no aprobación independiente. El checkpoint RUN063
contiene el resultado del arnés y preservación de registros previos.
F6 continúa abierta y F7 sin iniciar. Para conseguir props mediante este proveedor,
el siguiente paso es usar casas US/AU que sí tengan cobertura y mantener sus
contratos separados de los de México; no se inició un nuevo lote adicional.
