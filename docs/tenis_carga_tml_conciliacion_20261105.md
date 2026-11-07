# Conciliación de la carga TML (snapshot 16-oct) con la auditoría del 5-nov — versión final del S2a

Cargador: `apps/tenis/src/tenis/carga/tml_*.py`. Cifras de dos scripts: `ops/conciliar_tml.py` (recuentos) y `ops/verificar_tml.py` (comprobaciones **independientes**: leen los CSV originales con código propio, sin el parseo del cargador). Carga completa en un esquema aislado, borrado al terminar. Rechazos con motivo: `data/tennis/rediseno_20261104/tmp/conciliacion_tml/rechazos_tml_full_20261016.csv`.

## Decisiones tomadas durante la revisión (5-nov)

1. **Los sets 7-6 sin puntos de tie-break y los sets de ventaja son datos históricos válidos.** La primera versión los rechazaba (regla escrita por el revisor) y dejaba fuera ≈39.000 partidos de 1968–1990. El tie-break queda **NULL** (faltante, no 0) y el set de ventaja vale como se jugó. Los sets imposibles (7-4, 9-6, 6-6, 7-7, 8-5, 10-3…) siguen rechazándose, con pruebas. Reversible.
2. **Un lado con 0 puntos de saque en un partido terminado es un faltante codificado como 0 en el origen** (65 partidos medidos en los CSV, p. ej. un 6-2 6-2 con todo el saque del perdedor a 0). Ese lado queda sin estadística (no se escribe fila) y se avisa (`estadistica_cero_imposible`, 47 avisos). En retiradas muy tempranas (`1-0 RET`) el 0 es posible y se conserva (24 filas con 0 en la base).

## Resultado de la carga

- Leídas **495.960** filas de 166 ficheros. Cuadra: **493.867 cargadas + 2.007 rechazadas + 86 duplicadas + 0 dobles = 495.960**.
- Tiempo de la carga completa: **400–430 s** (< 15 min). Segunda carga idéntica: **0 filas nuevas en las 10 tablas** (idempotente), 304 s.
- Ningún fichero rechazado por sha256 (los 171 del manifiesto coinciden en tamaño y huella). No cargados, con motivo: `ATP_Database.csv`, `atp_matches_amateur.csv` y los `*ongoing*`.

## Recuentos frente a la auditoría (mismo snapshot)

| Concepto | Carga | Auditoría 5-nov | Diferencia |
|---|---:|---:|---:|
| Partidos cargados | 493.867 | 492.251 | +1.616 |
| ATP (gira, challenger y previas) | 396.168 | 394.592 | +1.576 |
| WTA | 97.699 | 97.659 | +40 |
| Completados | 478.661 | 469.527 | +9.134 |
| Mejor de 3 | 450.409 | 449.335 | +1.074 |
| Mejor de 5 | 43.458 | 42.916 | +542 |
| Superficie Hard / Clay / Grass / Carpet | 221.872 / 193.875 / 41.408 / 33.567 | 222.518 / 194.048 / 41.812 / 33.873 | −646 / −173 / −404 / −306 |
| Filas rechazadas | 2.007 | 3.923 | −1.916 |
| Elegibles para el modelo | sin dato | 249.938 | (definición no reproducida) |

Otros recuentos de la base: 20.013 ediciones, 3.707 torneos, 16.101 jugadores (y alias), 517.320 filas de estadística, 462.109 observaciones de ranking, 166 recibos.

**Qué explica y qué no.** La carga ya no queda por debajo de la auditoría (+0,3 %): el hueco de −37.900 de la primera versión era casi todo la regla de sets que se revirtió. Las diferencias restantes **no están explicadas por una causa medida**: la auditoría usó otras reglas de elegibilidad y de «completado» (la nuestra incluye partidos con marcador legible y estado completado; +9.134), y los 3.709 filas de diferencia en origen (492.251 frente a 495.960) no se reproducen con ninguna exclusión probada. Rechazos que sí tienen causa medida: temporada 1967 (363; el CHECK de `edicion.temporada` empieza en 1968), `set_invalido` 1.035, `completado_incoherente` 186, formato no válido 170, ronda no válida 118, id de jugador vacío 95, marcador ilegible 27.

## Verificación independiente (`ops/verificar_tml.py`, 40.000 partidos al azar con semilla fija)

| Comprobación | Resultado |
|---|---|
| Ganador de la base frente al `winner_id` del CSV | **0 mal orientados** (de 38.085 localizados en el CSV) |
| Juegos del ganador y del perdedor frente al marcador del CSV | **0 mal orientados** (37.122 comparados) |
| Idempotencia (segunda carga) | 0 filas nuevas |
| `visible_desde` posterior al fin de la edición + 1 día | **0** partidos |
| `visible_desde` de un partido anterior al de su edición | **0** partidos |
| Estadística con `puntos_saque` = 0 | 24 (retiradas tempranas); NULL en lugar de 0 para los 47 casos imposibles |

Límite: 1.915 de los 40.000 partidos de la muestra (4,8 %) no se encontraron en el CSV por la clave (torneo, ronda, pareja) y no se compararon; no cuentan como aciertos ni como fallos.

## Lo que sigue sin verificar

- **Calendario de `visible_desde` por ronda**: es conservador por construcción (más tarde que el fin real) pero **no está validado con horas reales**; se mide contra SofaScore 2023–2026 en S2b/S3 (porcentaje de partidos cuyo `visible_desde` cae antes del fin real: debe ser ≈ 0).
- Niveles de torneo con significado no verificado (ATP `A` 67.984 filas, WTA `T4`, `T5`, `P`, `P5`, `W`): van a la categoría neutra «250» con aviso.
- 7.372 conflictos de ranking (valor distinto el mismo lunes dentro de TML): se conserva el primero.
- El CLI no se ha ejecutado contra la base `tenis` real (solo esquemas aislados) y la ruta de equivalencias manuales no tiene pruebas (el CSV solo trae la cabecera).
