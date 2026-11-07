# Carga del archivo local de SofaScore (tenis ATP/WTA, retro): Sprint 2b, parte A

Fecha: 2026-11-05. Rama `tenis/rediseno-f1`, worktree `qf-tenis-rediseno`. Sin commit, sin red, sin VPS, sin APIs de pago.
Base: esquema `tenis` (Sprint 1). Plan: `docs/tenis_plan_tecnico_20261105.md` §A, §B y C.5.

## 1. Qué se entrega

| Fichero | Contenido |
|---|---|
| `apps/tenis/src/tenis/carga/sofascore_reglas.py` | Reglas puras: ronda, categoría, superficie, estado, sets, duración, fin estimado, estadística (ALL) y punto a punto. |
| `apps/tenis/src/tenis/carga/sofascore_parseo.py` | Decide por evento: aceptar, rechazar (motivo) o excluir. No toca la base. |
| `apps/tenis/src/tenis/carga/sofascore_resolutor.py` | Protocolo `ResolutorJugador` (firma pedida) y `ResolutorPorId` (jugador por `team.id`, alias exacto y aserciones que cambian). |
| `apps/tenis/src/tenis/carga/sofascore_escritor.py` | SQL por lotes (`executemany`), `ON CONFLICT DO NOTHING`, sin UPDATE ni DELETE. |
| `apps/tenis/src/tenis/carga/sofascore_carga.py` | Dos pasadas: agregados de torneo y edición; escritura por lotes de 250 eventos, una transacción por lote. |
| `apps/tenis/src/tenis/carga/sofascore_cli.py` | CLI `python -m tenis.carga.sofascore_cli --indice … --raiz … --dsn … --esquema … --almacen … --rechazos …`. |
| `apps/tenis/ops/conciliar_sofascore.py` | Carga el archivo completo en un esquema aislado, compara con la auditoría y borra el esquema. |
| `apps/tenis/tests/test_carga_sofascore_parseo.py` | 80 pruebas (con parametrización) de reglas y análisis con eventos sintéticos, datos absurdos incluidos. |
| `apps/tenis/tests/test_carga_sofascore_db.py` | 12 pruebas contra Postgres aislado: recibos, orientación, idempotencia, duplicados, rechazos, conflictos, PIT, campos prohibidos. |
| `apps/tenis/tests/test_carga_sofascore_independiente.py` | Muestra real de 300 eventos (semilla 20261105), recuentos y ganador/juegos de 100 partidos frente al JSON original. |

No se tocaron migraciones, `LEEME.md`, `harness/`, `apps/tennis/`, `src/tenis/identidad/` ni `src/tenis/captura/`. `almacen.py` no cambió: `guardar_objeto` ya admite la extensión `.json.gz` (la que usa `recibo.ruta_objeto`).

## 2. Conciliación con la auditoría (archivo completo, 21.974 filas del índice)

Ejecución: `apps/tenis/ops/conciliar_sofascore.py`, salida `data/tennis/rediseno_20261104/conciliacion_sofascore_20261105.json`. Rechazos y avisos con fichero y motivo: `data/tennis/rediseno_20261104/rechazos_sofascore_20261105.csv` (30.377 filas, incluidos conflictos y avisos).

| Concepto | Auditoría | Índice (medido) | Diferencia y causa |
|---|---:|---:|---|
| Partidos de tenis (filas) | 21.974 | 21.974 | Ninguna. |
| `finished` | 21.913 | 21.913 | Ninguna. |
| `canceled` | 61 | 61 | Los 61 no tienen `event.json`: excluidos (`sin_event_json`). No se cargan como `cancelado`. |
| ATP | 11.186 | 11.186 | Cargados 9.678 (ver §3). |
| WTA | 10.788 | 10.788 | Cargados 9.283. |
| Mejor de 3 / de 5 | 19.881 / 2.032 | 19.881 / 2.032 | Cargados 16.932 / 2.029. |
| Punto a punto **y** estadística | 20.816 | 20.816 (ambos ficheros) | El índice cuenta «al menos uno» (20.855) = 20.816 + 38 solo estadística + 1 solo punto a punto. |
| Ronda vacía | 459 y 458 | 917 | 917 = 459 + 458: las dos cifras de la auditoría suman el total del índice; no pude separar la causa de cada cifra. Todas quedan como `ronda_desconocida`. |
| Rango de fechas | 2022-12-30 → 2026-11-03 | igual | Ninguna. |

## 3. Recuentos de la carga

Leídos 21.974 = cargados 18.961 + rechazados 1.730 + excluidos 1.283 (cuadra; no hubo dobles ni duplicados en el archivo).

| Categoría | Eventos | Causa medida |
|---|---:|---|
| Cargados (partido nuevo) | 18.961 | completado 18.362; retirada 500; walkover 95; descalificado 4. ATP 9.678, WTA 9.283. |
| Excluidos `sin_event_json` | 1.283 | 1.222 `finished` que solo aparecen en el calendario (`round_*.json.gz`) y no tienen `event.json`; 61 `canceled` (ver §2). |
| Rechazo `ronda_desconocida` | 1.669 | 917 sin ronda en el dato; 738 «Qualification Final»; 14 «Qualifications». Ninguna se mapea: «Qualification Final» no tiene un código seguro (QF son cuartos). |
| Rechazo `set_invalido` | 27 | Sets con puntos de tie-break en un set que no es de tie-break (ejemplo: 6-2 con `period2TieBreak` 2-4). Dato absurdo. |
| Rechazo `completado_incoherente` | 8 | Ganador que no tiene la mayoría de sets, o menos de 2 sets. |
| Rechazo `ganador_ausente` | 13 | 12 `Ended` con `winnerCode` 3 (valor no previsto); 1 `Retired` sin `winnerCode`. |
| Rechazo `walkover_con_marcador` | 4 | Walkover con sets. |
| Rechazo `tiebreak_incompleto` | 9 | Tie-break con un solo lado informado. |
| Aviso `set_parcial_excluido` | 459 | Set en curso en una retirada: se excluye ese set, el partido se carga. |
| Aviso `tiebreak_sin_puntos` | 211 | 7-6 sin puntos de tie-break: se guarda NULL (ver §6.5). |
| Aviso `duracion_ausente` | 72 | Falta una duración de set, o queda fuera de 1–600 min: NULL. |
| Aviso `walkover_sin_ganador_en_base` / `descalificado_sin_ganador_en_base` | 95 / 4 | El CHECK de `resultado` exige ganador NULL en estos estados. |
| Aviso `pbp_no_derivable` | 1.036 | Ver §5. El partido se carga sin punto a punto. |
| Aviso `estadistica_<lado>:<motivo>` | 49 + 49 | Negativa 26/20; incoherente 9/14; definición incoherente 8/10; cero imposible 4/3; sin datos 2/2. Ese lado queda sin fila. |

Recibos: 55.679 (un original por fichero cargado: evento, estadística y punto a punto). Jugadores 1.347, torneos 65, ediciones 226.

**Tiempo:** carga completa 319 s (≈5,3 min) con la base y el disco en caliente; la primera ejecución, con el disco frío, tardó 610 s. Objetivo < 20 min cumplido.

## 4. Mapeo de estados (medido)

| `status.code` / tipo | Estado de la base | Resultado en el archivo |
|---|---|---|
| 100 `Ended` (`finished`) | `completado` | 18.362 cargados. `winnerCode` 1 o 2 y sets coherentes. |
| 92 `Retired` | `retirada` | 500. `ganador` = `winnerCode`, `retira` = el otro. Sets = solo los completos. |
| 91 `Walkover` | `walkover` | 95. Sin sets. `ganador` NULL: lo exige el CHECK, aunque el original trae `winnerCode`. |
| 97 y 98 `Defaulted` | `descalificado` | 4. `ganador` NULL (CHECK). |
| `canceled` (tipo) | `cancelado` | Ninguno cargado: los 61 no tienen `event.json`. |

Regla de coherencia de `completado`: el ganador tiene exactamente `mejor_de // 2 + 1` sets y el perdedor menos. Cada set pasa `valida_set` (6-0…6-4, 7-5, 7-6 con tie-break ≥ 7 y ventaja de 2, súper tie-break 1-0 en el último set, y ventaja (k+2)-k con k ≥ 6 solo en el último set).

## 5. Estadística y punto a punto

**Estadística (periodo `ALL`; los periodos 1ST, 2ND… se ignoran):**

| Columna de `estadistica` | Origen en SofaScore | Comprobación |
|---|---|---|
| `aces` | `aces` (valor) | — |
| `dobles_faltas` | `doubleFaults` (valor) | — |
| `puntos_saque` | `firstServeAccuracy`, total | = primeros + segundos (`secondServeAccuracy` total). |
| `primeros_dentro` | `firstServeAccuracy`, valor | ≤ `puntos_saque`. |
| `primeros_ganados` | `firstServePointsAccuracy`, valor | total = `primeros_dentro`; ≤ `primeros_dentro`. |
| `segundos_ganados` | `secondServePointsAccuracy`, valor | total = `puntos_saque − primeros_dentro`. |
| `juegos_saque` | `serviceGamesTotal` (valor) | — |
| `bp_salvados` / `bp_afrontados` | `breakPointsSaved`, valor / total | `bp_salvados` ≤ `bp_afrontados`. |

Salen las 9 columnas. No se rellena ninguna por inferencia: si una definición no cuadra o el dato es negativo, el lado entero se deja sin fila (§3).

**Punto a punto (`juego_pbp`).** Se escribe solo si todo cuadra; si no, el partido se carga sin punto a punto y el motivo queda como aviso. Hallazgos medidos:

- Los juegos regulares **no listan su último punto**: el listado llega hasta el punto de 40-x (o ventaja) y el punto que cierra el juego no aparece. Medido: 7.169 de 7.175 juegos regulares de 300 partidos cumplen que el último estado listado es previo a un cierre para el ganador que indica `score.scoring`. El punto que falta se **deduce** del ganador del juego, y solo si el estado final es terminal.
- El tie-break **sí** lista todos sus puntos (110 de 110 terminan con el ganador indicado).
- El campo `serving` del tie-break **no es fiable**: coincide con el sacador del juego anterior en el 56 % de los casos. Se ignora. El primer sacador del tie-break se deduce: saca quien no sacó el último juego regular. Medido indirectamente: tras un set con tie-break, el primer saque del set siguiente coincide con el último juego regular en 187 de 187 casos, y sin tie-break el saque alterna (1.875 de 2.007 casos; el resto son anomalías del listado).
- Causas de `pbp_no_derivable` (1.036): transición de marcador inválida 364; juegos que no cuadran con el marcador de set 340; saque que no alterna 140; juegos no consecutivos 51; número de sets distinto del marcador 43; punto final no deducible 30; tie-break que no cierra 22; punto no visible 16; tie-break sin transición válida 15; ganador del tie-break no cuadra 11; resto 4.

## 6. Decisiones y supuestos (conservadores)

1. **Recibo.** `recurso` = ruta relativa del fichero; `sha256` = del contenido **descomprimido** (coincide con `sha256_event_json` del índice; verificado en la muestra); `recibido_en` = `observed_at_utc` del índice para los tres ficheros; `lote` = `sofascore_AAAAMMDD`; `retro = true`.
2. **Campos prohibidos.** No se leen `firstToServe`, `ranking`, `currentRanking`, `prizeCurrent`, `userCount`, `homeScore.point`, `changes`, `h2h` ni `team_streaks`. Lo comprueban una prueba de reglas y una de base de datos.
3. **Orden de primera aparición.** Por `(startTimestamp, event_id)`. Torneo y edición toman el primer valor; cada valor distinto queda como conflicto (`edicion_conflicto:<campo>`). **Limitación medida:** hay 12.680 conflictos de `inicio_torneo` y otros tantos de `fin_torneo`, porque el clasificatorio tiene su propio objeto de torneo con el mismo `uniqueTournament`. Como la regla pide el primero, la fecha de fin de la edición puede ser la del clasificatorio y quedar antes que la del cuadro principal. No se cambió porque la regla lo fija; ver §8.
4. **7-6 sin puntos de tie-break:** NULL con aviso `tiebreak_sin_puntos`, igual que TML tras la decisión del 5-nov. Los 7-6 incoherentes siguen rechazados.
5. **Desempate de la visibilidad del resultado.** `visible_desde` del resultado, estadística y punto a punto = fin estimado conservador: `max(inicio + Σ duraciones, inicio del periodo actual + última duración) + 30 min`; sin duraciones completas, `inicio + 6 h`.
6. **Ronda.** Solo códigos seguros. «Qualification Final» y «Qualifications» se rechazan (ver §3).
7. **Categoría.** Equipos y finales por nombre; JJOO por nombre; resto por `tennisPoints` (2000 GS, 1000 M1000/WTA1000, 500, 250). Sin ningún caso neutro en este archivo (`categoria_neutra` = 0).
8. **Superficie.** Los seis valores de `groundType` del archivo tienen mapeo (`Hardcourt`/`Red clay`/`Green clay`/`Grass`/`Carpet`). Sin avisos de superficie desconocida.
9. **Partido visible desde `inicio − 12 h`; programa igual;** edición desde `inicio del torneo − 7 días`.
10. **Resolutor.** `ResolutorPorId` crea `jugador` por `(circuito, team.id)` con alias `id_exacto`. Las aserciones (nombre, fecha, mano, altura, país) se escriben solo cuando cambian. El cargador lo recibe por parámetro; no importa nada de `identidad/`.
11. **Mano y altura.** `plays` «right-handed»/«left-handed» → D/Z; otro valor → no se escribe. Altura = `height × 100` redondeada, si está en 1,0–2,5 m.
12. **Excluidos** (no rechazos): dobles (`/`, `subTeams`, tipo ≠ 1), deporte distinto de tenis y filas sin `event.json` u observación.

## 7. Pruebas y verificación

- `correr_pytest_tenis.ps1 apps/tenis/tests -k sofascore`: todas aprobadas (ninguna fallida).
- Suite completa `apps/tenis/tests`: **1.022 aprobadas, 9 omitidas, 0 fallidas**. Las 9 omitidas son 6 de `test_captura_colector.py` (exigen bash y flock: Linux) y 3 de `test_db_roles.py` (el usuario de prueba no puede crear roles). El recuento sale de la barra de progreso; el resumen de pytest no llegó a la salida.
- PIT: corte a `inicio − 11 h` ve el partido y no el resultado; corte posterior al fin estimado ve el resultado; corte de 2023 ve un partido de 2023 cargado en 2026 (retro).
- Idempotencia: repetir la carga sobre el mismo esquema no añade filas (sintético y muestra real de 300 eventos).
- Muestra real (300 eventos): recuentos por estado, formato y circuito coinciden con el cálculo aparte; ganador y juegos de cada lado coinciden con el JSON original en 100 partidos al azar.

## 8. Lo que no se cumplió o queda pendiente (decisión del titular)

1. **1.222 partidos terminados sin `event.json`** (solo en el calendario). No se cargan porque no tienen detalle. Cargarlos con datos mínimos del calendario exige decidir qué campos bastan.
2. **Fecha de fin de la edición con clasificatorio.** Pendiente: usar el fin máximo y el inicio mínimo, o el objeto de torneo del cuadro principal. Cambia `lunes_semana` en las ediciones afectadas; no se midió cuántas quedan con fin anterior al último partido.
3. **«Qualification Final» (738) y «Qualifications» (14).** Hace falta el mapeo que decida el titular.
4. **Tie-break sin serving fiable** (§5): la regla estándar se verificó solo de forma indirecta.
5. **Recibos y mapeo de estados.** Walkover y descalificado pierden `winnerCode`, porque el CHECK lo prohíbe; si se quiere conservar, hace falta ampliar el esquema (migración, fuera de este encargo).
6. **Partidos con `programa.estado = 'programado'` aunque ya se hayan jugado**: es lo que pide el encargo. Los estados reales (`suspendido`, `aplazado`) no se leen de SofaScore en esta parte.
7. **Jugadores multifuente.** `ResolutorPorId` solo une con SofaScore; la unión con TML es del resolutor de `identidad/`.
8. Sin commit, como se pidió.
