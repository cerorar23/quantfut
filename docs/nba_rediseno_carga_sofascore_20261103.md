# NBA v2 — Carga de SofaScore (todas las temporadas) a `nba_datos` (2026-11-03)

Fuente: el archivo del titular en `SOFASCORE\data\v3` (torneo 132 = NBA; temporadas 2021-22 a 2025-26 completas y 2026-27 hasta el 2-nov). Convertido en local a un archivo compacto (`ops/sofascore_a_jsonl.py`: 5.492 partidos terminados con alineaciones, 117.459 filas jugador-partido, 4,9 MB) y cargado con `fuentes/sofascore.py`. `nba_datos` sigue siendo la base principal; `sofascore` entra con prioridad 2, detrás de `nba_oficial`.

## Qué se cargó

- **Por partido**: estado final, puntos del equipo (total y por cuarto), y por jugador: minutos, puntos, rebotes, asistencias, robos, tapones, pérdidas, faltas, más/menos, tiros de campo, triples y tiros libres (intentados y anotados), rebotes ofensivos y defensivos, **titular** (nuevo: antes no teníamos titulares) y equipo del jugador. 2.409.592 filas nuevas, todas `pit = reconstruido` con la hora real de observación.
- **No cargado a propósito**: canastas (`incidents`), ausentes por partido (`missingPlayers`, observados después del partido, no sirven como dato de ese instante), árbitros, forma previa y rachas. Las prórrogas solo entran en el total (SofaScore no separa las prórrogas por período).
- **2021-22**: SofaScore trae los marcadores de todos los partidos pero las alineaciones solo de 123 (los playoffs); el resto de la temporada regular de ese año sigue sin titulares.

## Identidad de jugadores

En los partidos que ya tenían caja oficial, el jugador de SofaScore se empareja por la **huella de la caja** (mismos minutos, puntos, rebotes y asistencias en el mismo equipo), no por el nombre: 932 jugadores emparejados así, sin un solo caso de votos en conflicto. 61 jugadores sin ningún partido en común se resolvieron por nombre normalizado: solo 14 canónicos nuevos (2 ambiguos); el resto cayó sobre jugadores que ya existían. Un caso con dos jugadores de la misma línea de caja en el mismo equipo no se empareja por huella (prueba).

## Cobertura resultante (partidos con marcador y caja por jugador)

| Temporada | Antes | Ahora |
|---|---|---|
| 2021-22 | 1.229 | 1.322 |
| 2022-23 | 1.316 | 1.320 |
| 2023-24 | 1.305 | 1.318 |
| 2024-25 | 1.286 | 1.320 |
| 2025-26 | 1.278 | 1.321 |
| 2026-27 | 1 con caja | 91 con caja (137 con marcador) |

Titulares: 100 % desde 2022-23 (1.318–1.320 por temporada). Solo 93 partidos eran realmente nuevos: el resto de los 187 que no tenían marcador existían como calendario (partes y cuotas) y SofaScore los completó sin duplicarlos. Los 15 juegos canónicos duplicados de siempre siguen siendo los mismos 15.

## Auditoría cruzada: SofaScore frente a la caja oficial (111.358 jugador-partido comparables)

Coinciden en más del 99 % de los datos: triples anotados 0 diferencias; tiros de campo 2; faltas 9; tiros libres 11; puntos 13 de 121.788; asistencias 71; tapones 75; pérdidas 83; robos 191; rebotes 202 (0,18 %); minutos 273 (0,25 %); más/menos 857 (0,77 %). Son correcciones de estadística entre fuentes, no problemas de identidad. Donde difieren manda `nba_oficial`. Sirve como verificación cruzada de las dos fuentes: la caja que entrenaba el modelo era sólida.

## Lo que cambia y lo que falta

- **La base ya es otra**: más partidos, titulares y la temporada en curso. El motor en producción no cambia de código; sus datos de entrada sí (las historias de equipo y jugador ahora incluyen estos partidos), y `version_datos` lo refleja en cada sello.
- **Falta reexportar y reentrenar**: las exportaciones de entrenamiento usaban solo `nba_oficial`; hay que leerlas con prioridad (`nba_oficial` > `sofascore`) y repetir las evaluaciones y los artefactos (props, impacto) con los datos nuevos. La comprobación independiente de G-fuga también debe leer ambas fuentes.
- Respaldo previo a la carga: `respaldos/nba_datos_20261103T031925Z.dump`. Base: 3,05 GB (antes 2,29), disco al 64 %.

## Reentrenamiento con la base nueva (2026-11-03, tarde)

- **Exportación con prioridad de fuentes** (`ops/exportar_entrenamiento.sql` y `ops/preparar_datos_entrenamiento.py`): 6.738 partidos con marcador y 142.942 filas jugador-partido resueltas con nba_oficial > sofascore, con ids canónicos.
- **Evaluaciones repetidas** (equipo, jugadores y props) con la misma metodología: las conclusiones no cambian. Error del margen del equipo en 2025-26: 14,49 (antes 14,49); mezcla equipo + jugadores 14,33 (14,32); Brier del ganador 0,206 / 0,2035 (0,206 / 0,2038); cobertura 80 % de los props 80,4–81,0 % (80,5–81,3 %). Con un 1,5 % más de datos y otra fuente, los resultados son los mismos: señal de que no dependían de un detalle de la caja anterior.
- **Parámetros del equipo**: igual eta, arrastre y tasa de liga; efecto de jugar en la noche siguiente 2,78 → 2,90 puntos por equipo; sigma del margen 13,80 → 13,81 y del total 18,46 → 18,43.
- **Artefactos reentrenados**: props con 112.666 filas (108.744 antes), sobredispersión puntos 0,227 / rebotes 0,014 / asistencias 0,051 / triples 0,074; impacto con 1.083 jugadores (1.028) y mezcla del margen con sigma 14,06; en validación el error del margen pasa de 14,20 (equipo) a 14,06 (mezcla), el total no mejora (18,24 → 18,29), así que sigue sin tocarse.
- **G-fuga con ambas fuentes** (VPS, solo lectura, 100 partidos de equipo y 60 de jugadores): 0 diferencias de repetibilidad, 0 fugas, mezcla 2.1 en los 60 partidos con diferencia máxima de 3·10⁻⁴ frente al cálculo independiente, plantillas idénticas a la reconstrucción independiente, cobertura de los puntos reales 82,8 % (n = 1.168). El Brier del ganador de estos 100 partidos fue 0,230: es una muestra distinta de la anterior (cambió el paso del muestreo al haber más partidos) y con 100 partidos el error típico ronda 0,02; no es una medida del modelo.
- **Desplegado**: `imagen_motor` = `nba-motor:a16b019` desde las 03:52 UTC; ejecución del cron de las 03:55 sin errores. La imagen anterior queda en `imagen_motor.anterior` (`nba-motor:b874e9a`).
