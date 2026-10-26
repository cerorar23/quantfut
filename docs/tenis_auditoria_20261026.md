# Motor de tenis: auditoría del 26-oct-2026 (datos, APIs, mercados y producción)

Estudio sin fines de lucro. Objetivo del titular: el mayor acierto posible en todos los mercados, no batir cuotas. Se auditó
el motor vigente (`tennis_motor` v8 + entrada automática `tennis_intake_v1`) en el VPS contra lo que piden los documentos
del motor (`tenis_recomendaciones_mejora_20261017.md`, `tenis_calidad_predictiva_20261019.md`, `tenis_mercados_integrados_20261019.md`).

## Estado medido antes de corregir (VPS, 26-oct 14:30 UTC)

- 178 pronósticos sellados, 134 con resultado (129 completos, 5 retiros). Ganador: ATP 56,2 % (n=73, log-loss 0,679),
  WTA 72,1 % (n=61, 0,599). Con ±12-16 puntos de margen a esta muestra, ATP no contradice el 67 % esperado, pero se revisó.
- Actualización semanal del lunes: 88 archivos nuevos de TennisMyLife, 492.724 filas, modelos ATP (74.284 partidos) y WTA
  (20.826) reentrenados y promovidos; chequeos superados.
- Cuotas: PropLine (archivo horario compartido) desde el 24-oct; 53 de 68 sellados desde entonces con precio.

## Errores encontrados y corregidos

| Error | Causa | Corrección |
|---|---|---|
| 7 partidos del Challenger de Lyon (20-oct) sellados en **arcilla** | El torneo tomaba la superficie de la última fila con ese nombre (el ATP 250 de mayo) | Superficie de la edición celebrada en la misma época del año (±30 días); sin edición cercana, se excluye en vez de adivinar |
| 15 sellados sin cuota la noche del 25-oct | El cron está en hora de Berlín: tras el cambio de horario la pasada de las 00:30 cayó a las 23:30 UTC, la hora en que el recolector de PropLine ya agotó su cupo diario y no captura | Pasada horaria en el minuto 25; calendario de API-Tennis solo a las 00 y 12 UTC (decidido con `date -u`); sin precio, el sellado espera a la siguiente pasada |
| `math domain error` en el cálculo de inactividad (Birrell–Kasatkina) | Los días de ronda son estimados: un partido ya jugado puede tener día posterior al del pronóstico y el hueco salía negativo | `dynamic_features` en `tennis_motor` recorta el hueco a 0 y cuenta esos partidos en la carga de 14 días (`tennis_dynamic_v2` no se toca: lo congelan los protocolos v7/v8) |
| Jugadores excluidos por nombre: «Xin. Wang», «B. Nakashima» | La inicial solo admitía una letra; dos homónimos activos | Iniciales largas con prefijo del nombre; homónimos separados por el nivel del torneo (gira o Challenger) |
| 46 jugadores activos (8 WTA, 38 ATP; p. ej. Xinran Sun) excluidos con «use a canonical ID» | Sus partidos no traen estadísticas de saque y el modelo de saque no los incluye | `Motor.resolve` acepta el ID canónico: saque de población (como cualquier efecto sin entrenar), Elo, ranking y precio del mercado propios |
| Mercados evaluados solo en líneas fijas (18,5 … 26,5) | Contrario a la recomendación de comparar en la misma línea ofrecida | Ver «Todos los mercados» |

Las 7 predicciones de Lyon en arcilla y las del 25-oct sin cuota quedan selladas tal cual (los sellados no se reescriben).

## Todos los mercados con sus cuotas

El archivo de PropLine trae para tenis, por casa: ganador, ganador del set 1-3, total y hándicap de juegos (línea principal y
alternativas) del partido y del set 1, total y hándicap de sets, juegos por jugador y aces. Cada sellado guarda ahora
`market_board`: todas las líneas soportadas por el motor, con precio sin margen (media de casas con los dos lados de la misma
línea; excluidas bolsas, DFS, suspendidas y en juego) y la probabilidad del motor en esa línea (sin el empate de líneas enteras).
Ensayo real: 41-48 líneas por partido WTA. Aces, dobles faltas, juegos por jugador y puntos de quiebre quedan fuera: el motor
no modela esas variables.

`evaluation_latest.json → offered_markets` compara por familia el motor, el precio al sellar y el **cierre** de PropLine en las
mismas líneas. Primera medida con 27 partidos que ya tenían cierre (modelo recentrado al precio de ganador, log-loss):

| Familia | n líneas | Motor | Cierre |
|---|---|---|---|
| Total de juegos | 385 | **0,547** | 0,584 |
| Hándicap de juegos | 315 | **0,652** | 0,663 |
| Total de juegos del set | 145 | 0,483 | **0,476** |
| Total de sets | 27 | **0,619** | 0,627 |
| Ganador de set | 58 | 0,695 | **0,691** |

En totales el mercado sobrevalora el «más de» (precio medio 0,481, observado 0,413, motor 0,447). Por eso **no** se anclan los
totales del motor al mercado: el ganador sí sigue anclado al precio (evidencia 2025-2026). Muestra pequeña y líneas correlacionadas
dentro de cada partido: es una medida, no una acreditación.

## Datos descargados y entrenamiento

- **Entrenan el motor:** TennisMyLife semanal (ATP, Challenger, WTA) → puentes de identidad v2/v3 → modelo de saque/resto y Elo
  dinámico. Comprobado el 26-oct.
- **Se usan en vivo:** PropLine (precio de ganador como objetivo; todas las líneas para evaluación).
- **Sirven solo para evaluar, no para entrenar:** Tennis-Data (cierres 2025-2026, ya usado para fijar que el precio sin margen
  supera al apilador), BetsAPI (ganador y set en curso, sep-2025→oct-2026), cierres de PropLine. Usarlos para entrenar los mismos
  parámetros que luego se evalúan con ellos sería fuga. Match Charting Project: estructura del Markov (sin cambios).
- **Identidades semanales:** 42 nombres cambiaron de ID entre las instantáneas del 20 y el 26-oct (alias que alternan su ID
  principal). El 20-oct una fila errónea de la fuente fusionó a Juan-Andrés Gómez con Harshana Godamanna; la fuente se corrigió
  y la instantánea del 26-oct ya los separa. Los sellados guardan nombres además de IDs, así que la evaluación no depende de ello.

## Pruebas y despliegue

434 pruebas del motor (5 nuevas). Imagen y crontab: ver `DEPLOYS.md` (26-oct).
