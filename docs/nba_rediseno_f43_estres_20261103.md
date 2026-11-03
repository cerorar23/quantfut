# NBA v2 — Fase 4, F4.3: estrés (2026-11-03)

Regla probada: **nunca se sella un dato faltante imputado como 0, ni un pronóstico con ratings viejos o minutos corruptos; lo que no se puede pronosticar se omite y se informa.** Todo corre contra bases desechables con un mini-torneo de 30 equipos y 9 jugadores por equipo (`tests/v2/test_estres.py`, `test_propiedades.py`, `test_concurrencia.py`; 14 pruebas nuevas, 235 en total).

## Escenarios

| Escenario | Qué se simula | Resultado |
|---|---|---|
| Día normal | 15 partidos con hora, 20 días de historia | 15 de equipo + 15 de props sellados (240 filas de jugador-estadística por partido), todas las distribuciones cumplen el contrato, la cadena se verifica |
| Fuentes caídas | 5 de los 15 partidos sin hora de salto + a 2 equipos les faltan los últimos 12 días de resultados | Los 5 sin hora quedan en `sin_hora`; los partidos de los 2 equipos atrasados se omiten con `equipo_sin_resultados_recientes`; solo se sellan los que se pueden pronosticar y de los omitidos no llega nada a la base, ni siquiera props |
| Estadística ausente | A un jugador le falta el dato de puntos en sus 3 últimos partidos | **Antes del arreglo** se contaba como 0 puntos (hueco real: la tasa caía ≈ 8–10 %). Ahora ese partido sale de la tasa de puntos y su pronóstico queda a menos de un 5 % del de jugadores equivalentes |
| Minutos corruptos | Un jugador con 150 minutos en su último partido | **Antes** el pronóstico se descuadraba; ahora el partido con minutos fuera de (0, 60] no cuenta y sus minutos esperados coinciden con los de jugadores equivalentes |
| Sin historia | Solo existe el día objetivo | 0 sellos, 0 errores: todos `historia_atrasada` |
| Base vacía | Ningún partido | El motor termina sin errores y sin sellos |
| Concurrencia | 8 procesos sellando a la vez, 25 sellos cada uno y claves repetidas a propósito | Una fila por clave, `verificar_cadena` íntegra, cada eslabón apunta a uno distinto, y quien repitió una clave recibió el mismo hash |

Propiedades con entradas aleatorias (semilla fija, `test_propiedades.py`): la pmf de conteo es válida y su probabilidad decrece con la línea (150 casos); `quitar_margen` suma 1 y no da 0 ni 1 en los tres métodos (200 casos); la simulación y los mercados son coherentes para cualquier media y desviación (hándicap monótono, ganador = hándicap 0, tramos suman 1; 40 casos); los 199 cuantiles sellados siempre cumplen el contrato; los minutos esperados suman 240; las muestras de minutos quedan en [1, 60]; la probabilidad recalibrada nunca es 0 ni 1; el hash cambia con cualquier campo sellado.
Las dos pruebas de datos faltantes y minutos corruptos fallan sin los arreglos y pasan con ellos (comprobado).

## Arreglos que salieron del estrés

1. **Datos faltantes ya no valen 0** (`props.tasa_por_minuto`, `plantilla_pit`): una estadística ausente es desconocida; ese partido no cuenta ni en el numerador ni en los minutos de esa estadística.
2. **Minutos corruptos fuera**: un partido con minutos fuera de (0, 60] no entra en la plantilla.
3. **Equipos sin resultados recientes** (`motor.equipo_atrasado`): hasta ahora solo se comprobaba que la historia global estuviera fresca; si la captura fallaba solo para un equipo, se sellaba con sus ratings viejos. Ahora se omite (y se alerta) cuando a un equipo le faltan más de 10 días de resultados dentro de la temporada, o no tiene ninguno pasadas tres semanas de temporada. Comprobado contra datos reales: **0 omisiones por la regla en 212 fechas de 2025-26** y 0 en los 14 partidos ya conocidos del 4-nov.

## Datos reales

La base real está limpia: de 143.188 filas jugador-partido ninguna carece de puntos, rebotes, asistencias ni triples y ninguna tiene minutos fuera de rango. Los arreglos protegen el futuro (otra fuente, otra descarga); no cambian los pronósticos de hoy: G-fuga con el código nuevo (VPS, solo lectura, 100 partidos de equipo y 60 de jugadores) da exactamente los mismos números (0 diferencias, 0 violaciones en 5.852 distribuciones, cobertura 82,8 %).

## Observaciones operativas

- El 3-nov no hubo partidos de NBA (día de elecciones en EE. UU.): el siguiente es el 4-nov (14 partidos, sin hora todavía; ESPN publica la hora el mismo día).
- La captura de cdn.nba.com agotó ayer su tope de 25 créditos diarios de Scrapfly con los partidos del 2-nov (25 archivos, 2 fallidos); con 15 partidos al día alcanzan la caja de cada uno y poco más: la jugada a jugada se captura con lo que sobre.

## Estado

Imagen verificada: `nba-motor:d73c7c5` (no desplegada; ver la nota sobre S3c en `DEPLOYS.md`: producción corre `nba-motor:6b85093`, que incluye el impacto S3c pendiente de aprobación). Los arreglos se activarán con la próxima imagen que se ponga en el cron.
