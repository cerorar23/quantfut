# NBA — productor vivo 1.5.0: recalibración de equipo (rechazada) y umbral estadístico para jugadores (26-oct-2026)

Encargo del titular: recalibración móvil de total y puntos de equipo con prior de pretemporada, mejorar el protocolo en vivo
corrigiendo los errores que aparezcan, y dejarlo en producción. Protocolo congelado antes de mirar 2025-26:
`apps/nba/nba_live15_protocol.json` (sha256 `86eb3c7b…`, en `apps/nba/.local/normalized/nba_live15_recal_20261026/protocol_frozen.json`).

## Errores del vivo encontrados en el servidor (registro y cohortes del 21 al 26-oct)
1. **La cohorte 2026-10-25 19:30 ET se selló sin ningún pronóstico de jugadores.** El recolector compartido de PropLine paró a las
   22:13 UTC por la reserva de la cuota diaria (4.501 de 5.000 usadas; otro consumidor de la misma cuenta gasta ~300-500 por hora a
   media tarde) y se saltó la captura de las 23:00 UTC. Al sellar a las 23:30 el archivo más reciente tenía 83 min y el límite es
   65 (`prop_lines.MAX_AGE`), así que el productor selló solo ganador, puntos de equipo y total. El 24-oct pasó lo mismo a las 23:07.
   La versión del recolector desplegada el 25-oct a las 23:19 (otra sesión) bajó el consumo (~80-100 por hora), pero el motor seguía
   dependiendo de una sola captura.
2. **Nunca se selló un pronóstico de pérdidas.** El modelo 1.4.0 tiene `player_turnovers` ajustado, pero PropLine casi no lo cotiza
   (62 filas de mercado en la captura de las 14:00 UTC del 26-oct, frente a 5.324 de puntos) y con el mínimo de 2 casas no pasa ninguno. Robos y tapones salen solo para
   unos pocos jugadores por partido por la misma razón.
3. El fallo `invalid box score minutes '10:60'` del 24-oct (9 trazas) ya estaba corregido en el código desplegado (`:60` = minuto siguiente).

## Corrección en vivo (L1): umbral estadístico para jugadores sin línea
Cada jugador de rotación de los dos equipos (media de minutos ≥ 12 en su historial elegible, al menos 10 partidos, último equipo en
este partido, no listado «Out») recibe, en cada mercado en el que PropLine no le da línea (o si no hay archivo reciente), un
pronóstico sobre el umbral `floor(media de los últimos 10) + 0,5`. Es el desplazamiento 0 de la rejilla sobre la que ya está
ajustada la calibración de jugadores, así que la probabilidad sale del mismo modelo, sin reajustar nada. Las filas llevan
`line_source = 'statistical'`, `books = 0` y la referencia «Umbral estadístico (media de los últimos 10); sin línea de PropLine».
Las líneas de PropLine siguen teniendo prioridad (`line_source = 'propline'`). Resultado: ninguna cohorte vuelve a quedarse sin
jugadores y entran pérdidas, robos y tapones de toda la rotación.

**Enmienda tras el ensayo (no cambia el protocolo congelado, que no puntúa L1):** el umbral estadístico exige además que el último
partido del jugador sea de esta temporada (desde el 20-oct). En el ensayo con los 9 partidos del 26-oct salían jugadores cuyo último
equipo era el de la temporada pasada y que ya no están en la plantilla (p. ej. Kevin Love o Santi Aldama en Jazz–Grizzlies). Un
jugador con línea de una casa no lo necesita: la casa ya dice que está en la plantilla.

## Recalibración de equipo: validación congelada (`nba.live15_check`)
Diseño mirado solo en 2023-24 y 2024-25 (cada una con el modelo ajustado para ella): en las líneas del vivo el sesgo del total
cambia de signo (−0,041 y +0,034; puntos de equipo −0,028 y +0,015), la pendiente del total es baja (0,70 y 0,84) y octubre es lo
que más falla. El ajuste de equipo del módulo reproduce exactamente el modelo desplegado (`fit` y tabla de participación idénticos).

Prueba en 2025-26 (3.618 unidades, bootstrap por fechas, 400 réplicas, semilla 20261031):

| Candidato | Elegido en 2024-25 | Δ Brier conjunto (IC 95 %) | Puntos de equipo | Total | Decisión |
| --- | --- | --- | --- | --- | --- |
| P: prior de arranque (forma de la temporada anterior regresada a la media de la liga) | ρ = 0,25, sin quitar abril | −0,00007 [−0,00046; +0,00023] | +0,00004 | −0,00029 | no entra |
| R1: recalibración logística por temporada (ajustada en la anterior) | a, b de 2024-25 | +0,00089 [−0,00032; +0,00199] | +0,00036 | +0,00196 | no entra |
| R2: R1 + intercepto dentro de la temporada | τ = 0,2 | +0,00226 [+0,00075; +0,00387] | +0,00209 (IC 97,5 % excluye 0) | +0,00260 | no entra (peor) |

- **En 2025-26 el modelo de equipo ya está calibrado en sus propias líneas** (pendiente 1,10 en puntos y 1,05 en total; intercepto
  +0,06 y −0,02). La recalibración de 2024-25 lo vuelve infraconfiado (pendiente 1,21-1,25): el sesgo de ±0,04 no se traslada de una
  temporada a otra. El «±0,04» de la auditoría del 23-oct se medía en otras líneas (bet365), con otra pregunta.
- R2 aprende el intercepto de partidos pasados predichos **sin** disponibilidad (el productor no guarda reportes de partidos ajenos a
  sus cohortes) y lo aplica a probabilidades **con** disponibilidad: ese desajuste da interceptos negativos (−0,19 y −0,36 al final de
  2025-26) y empeora el resultado. Una versión que aprenda de las propias cohortes selladas solo puede probarse con el registro prospectivo.
- El prior de arranque mejora un poco los primeros 30 días (−0,00034, 657 unidades) sin evidencia. No es un prior de plantilla
  (traspasos y novatos sin valorar).

**El modelo de equipo no cambia.** El reajuste 1.5.0 usa los mismos datos y opciones que 1.4.0: equipo, tabla de participación y los
12 mercados de jugador salen idénticos (`compare` sin `--retrain`); solo cambian el código del módulo y la versión.

## Límites
- Retrospectivo sobre una temporada de prueba; la prueba real es el registro prospectivo.
- Los umbrales estadísticos se eligen por la media de los últimos 10, no por el interés del público; la calibración en ese umbral
  está medida dentro de la rejilla de 1.4b (desplazamiento 0), no por separado.
- **Traspasos de verano.** El equipo de un jugador es el de su último partido en el historial (incluye los de esta temporada). Un traspasado que aún no ha jugado en temporada regular se descarta (`last_team_not_in_game`) aunque PropLine lo cotice: el archivo de PropLine no trae el equipo del jugador (`team` va vacío en las cotizaciones de jugador), así que no hay forma de verificar el lado. Es pérdida de cobertura, no un pronóstico mal asignado; solo se asignaría mal el caso, muy raro, de un traspasado al rival de su antiguo equipo. Medido en la primera cohorte real (`2026-10-26_1730`): 0 descartados de 28 cotizados, ningún pronosticado sin partidos esta temporada, sin discrepancias con el informe oficial de lesiones. Se cierra solo a medida que los jugadores debutan; arreglarlo de verdad exigiría una fuente de plantillas, que hoy no compensa el ciclo de reajuste y despliegue.
- Sigue fuera: modelo único del marcador, distribución de puntos 2P/3P/TL, doble-doble, cuartos 3-4 y márgenes por rangos.
