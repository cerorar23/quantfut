# Integración del S2b sobre datos reales (5-nov-2026): TML + SofaScore + identidad + calendario retro

Script: `apps/tenis/ops/integrar_s2b.py` (esquema aislado, se borra al terminar). Snapshot TML del VPS del 2-nov copiado al PC (D5). Resultados de la corrida final (JSON en `data/tennis/rediseno_20261104/integracion_s2b_D.json`).

## Carga

| | TML | SofaScore |
|---|---:|---:|
| Filas leídas | 496.827 | 21.974 |
| Cargadas | 495.039 | 19.665 |
| Cuadre leídas = cargadas + rechazadas + excluidas | sí | sí |
| Tiempo | 474–582 s | 588–695 s |
| Segunda carga: filas nuevas en las tablas | 0 (S2a) | **0** en las 7 tablas |

SofaScore: 1.283 excluidos (finished solo en el calendario, sin `event.json`), 931 rechazados por ronda desconocida (917 vacías), 41 `completado_incoherente`, 27 sets inválidos, 14 sin ganador, 9 tie-break incompleto, 4 walkover con marcador. Tras cargar ambas fuentes: 16.421 jugadores, 514.704 partidos, 555.285 estadísticas, 426.604 juegos con punto a punto, 19.665 programas.

## Identidad entre fuentes (resolutor multifuente)

Cargando TML primero y SofaScore después con el resolutor: **1.149 de 1.349 jugadores de SofaScore se unen con TML (85,2 %)**, todos por nombre + país + edad (`nombre_fecha_nac`), **0 uniones contradictorias**. No unidos: 156 sin candidato en TML, 21 sin edad, 3 ambiguos, 3 con edad contradictoria, 1 sin país, 16 «confirmado distinto» (homónimos de otro país o edad).

**Defecto hallado y corregido en esta integración:** TML usa los códigos de país del COI y SofaScore los de ISO alpha-3. Sin normalizar, 132 de 860 jugadores con nombre idéntico (15 %) parecían «de otro país» (`GER`/`DEU`, `SUI`/`CHE`, `CRO`/`HRV`, `NED`/`NLD`…) y 200 ids se separaban como homónimos. Con `identidad/paises.py` (COI→ISO) bajan a 16 y la tasa de unión sube de 71,8 % a 85,2 %.

## Validación del calendario retro de TML contra las horas reales de SofaScore

Se cruzan los partidos de las dos fuentes por (jugador_1, jugador_2, misma ronda, fecha dentro de la edición) y se compara cuándo TML hace visible el resultado con el fin real (SofaScore). **Hallazgo: el calendario inicial (días «razonables») dejaba el resultado visible antes del fin real en el 9,1 % de 12.924 partidos.** Una primera versión del cruce sin exigir la misma ronda mezclaba enfrentamientos de torneos consecutivos y daba cifras contaminadas; con la ronda exigida la fuga seguía siendo real.

Recalibración con el percentil 99,9 del fin real por ronda + 1 día (cadena estrictamente creciente): tablas `DESFASE_7` y `DESFASE_14` de `tml_reglas.py`.

| | Comparados | Fuga (resultado visible antes del fin real) |
|---|---:|---:|
| Calendario inicial | 12.924 | 1.182 (9,1 %) |
| **Calendario calibrado (corrida final)** | 12.924 | **125 (0,97 %)**: 7 días 2/3.890 (0,05 %); 14 días 123/9.034 (1,4 %) |
| Fuera de muestra (calibrado con 2023-24, comprobado 2025-26) | 7.146 | 7 días 0,05 %; 14 días ≈ 2 % (casi todo una edición: US Open 2026) |

- **Limitación declarada:** unas 3 ediciones de ~100 (2023-04, 2024-07, 2026-08) tienen en TML `tourney_date` apuntando a la semana del clasificatorio y no a la del cuadro principal: no se detectan sin horas reales y concentran la fuga restante. Para partidos con hora real (SofaScore, 2023→) el PIT debe usar sus tiempos; el calendario de TML es el recurso para lo anterior y **no es verificable hacia atrás**.
- **Coste:** la pareja de TML se hace visible después del inicio real en el 54,6 % de los partidos (el corte retro «pareja + 1 s» cae casi siempre tras el inicio real). No filtra el propio resultado, pero el conjunto de información del corte retro puede incluir resultados de otras parejas de rondas anteriores terminados después del inicio real (efecto de segundo orden en ratings). Además, la final de un torneo se hace visible hasta L+10 (7 días) o L+16 (14 días), de modo que la fatiga entre torneos consecutivos queda degradada en la era solo-TML.

## Qué falta (no medido o pendiente)

- Cargar en la base `tenis` real o en el VPS: requiere tu OK (todo esto fue en esquemas aislados).
- Analizador de ranking de SportsAPIPro sin respuesta real (hace falta una petición aprobada).
- 35 equivalencias de alias de WTA propuestas por el agente de identidad: 18 tienen una sola fila con edad válida (evidencia más débil) y 25 dudosas no entran; sin revisión manual.
- 1.222 partidos de SofaScore `finished` sin `event.json` no se cargan.
