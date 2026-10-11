# Parley del día — diseño

Fecha: 2026-10-11. Estado: diseño aprobado en conversación por el usuario;
pendiente de revisión de este documento antes del plan de implementación.

## Objetivo

Una pestaña nueva **"Parley"** dentro de Fútbol en la web, con su historial de
seguimiento. Cada día con partidos el sistema arma entre 1 y 5 parlays de
cuota total 1,90–5,00, combinando selecciones de todos los mercados que ya
calcula, y elige en cada nivel de cuota la combinación **más probable**.

Es una línea de **acierto**, no de valor: se elige solo por probabilidad, como
la alta probabilidad. La pestaña lo dice y el historial enseña el resultado
real, incluido el dinero perdido.

## Decisiones del usuario (2026-10-11)

| Pregunta | Decisión |
|---|---|
| Reparto dentro de 1,9–5,0 | **Escalones de cuota**: cada parlay apunta a un nivel distinto y en cada nivel se elige la combinación más probable. |
| ¿Repetir partido entre parlays del día? | **No.** Cada partido aparece como mucho en un parlay del día. |
| Filtro de precio por pata | **Solo la probabilidad.** No se exige que la pata esté cerca de su precio justo. |
| Enfoque de búsqueda | **A**: búsqueda exacta por escalón, del más bajo al más alto. |
| Visibilidad | Pública, como la escalera y la alta probabilidad. |

Consecuencia aceptada de "solo la probabilidad": el margen de la casa se paga
en cada pata, así que a la larga los parlays pierden dinero aunque acierten lo
prometido. No se esconde: el historial publica unidades y ROI.

## Fuera de alcance

- Cobro o tier de pago para los parlays (la puerta de CLV no aplica: no es una
  línea de valor).
- Parlays con varias patas del mismo partido (correlación sin modelar).
- Avisos por Telegram a clientes (Telegram solo es canal operativo).
- Ligas sin cuotas vigentes (Bélgica, Grecia: no están en el sistema).

## Selección

### Escalones

| Escalón | Cuota total |
|---|---|
| ≈2,0 | 1,90 – 2,20 |
| ≈2,5 | 2,20 – 2,70 |
| ≈3,0 | 2,70 – 3,40 |
| ≈4,0 | 3,40 – 4,30 |
| ≈5,0 | 4,30 – 5,00 |

Límites cerrados por abajo y abiertos por arriba (`lo <= cuota < hi`), salvo
el último, cerrado en 5,00.

### Ventana del día

La selección corre en el job diario de las 08:00 UTC (`daily.run`). Entran los
partidos con `kickoff_utc` entre `now + MIN_LEAD` (15 min) y `now + 24 h`, de
ligas activas. Así el "día" va de 08:00 UTC a 08:00 UTC (02:00–02:00 en
México) y cubre la jornada americana completa.

### Patas candidatas

Fuente: `escalera_datos.opciones(m, now, rho, modelos)`, la misma de la
escalera. Da para cada partido: 1X2, goles totales, goles por equipo, ambos
marcan, hándicap asiático, córners totales y por equipo y tarjetas, con:

- probabilidad de Pinnacle sin margen (1X2, goles, ambos marcan, hándicap);
- córners y tarjetas solo en `em.LINEAS_HABILITADAS` (las que pasaron la
  prueba histórica), recortadas a la probabilidad del mercado (`prudente`);
- la mejor cuota de las casas de la lista (`settings.soft_books`) y su hora.

Se añade la doble oportunidad cuando haya cuota de la lista para ella
(`alta_prob.candidatos_doble` + `alta_prob_datos._ref`); si no hay cuota, no
entra. Cuotas de más de 6 h (`MAX_EDAD_PRECIO`) no entran.

Filtros por pata:

1. Cuota ≥ **1,15** (por debajo apenas sube la cuota total y solo resta
   probabilidad).
2. **Cuota errónea fuera**: si `p · cuota − 1 > 0,25` la cuota se descarta como
   error de la casa (caso real: William Hill pagaba a Deportivo a 19,00 con el
   resto del mercado en ~5).
3. Hora de la cuota ≤ hora de decisión (sin fuga).

### Búsqueda (enfoque A)

Por cada escalón, en orden ascendente:

- Problema: elegir como mucho una pata por partido, entre **2 y 6 patas**,
  con `lo <= Π cuota < hi`, maximizando `Π p`.
- Resolución: mochila de elección múltiple sobre `ln(cuota)`. Estado
  `dp[k][b]` = máxima `Σ ln p` con `k` patas y `Σ ln cuota` en el cubo `b`
  (ancho 0,001 en ln, ~1.610 cubos hasta ln 5). Se recorre partido a partido;
  cada partido aporta "ninguna pata" o una de sus patas.
- Reconstrucción: entre los estados con `k ≥ 2` cuyo cubo cae en el rango, se
  toman en orden de probabilidad y se **verifica la cuota exacta**; el primero
  que cumple gana. Así el redondeo del cubo nunca saca un parlay fuera de rango.
- Desempate: mayor probabilidad; luego menos patas; luego `match_id`
  ascendente (determinista).
- Al cerrar el escalón se retiran sus partidos y se pasa al siguiente. Si un
  escalón no tiene combinación válida, **se salta** y se prueba el siguiente
  (un escalón alto puede salir con partidos que no servían para uno bajo).

Probabilidad del parlay = producto de las patas (partidos distintos:
independientes a efectos prácticos).

## Datos

Migración `db/053_parley.sql`:

- `parley_tickets`: `ticket_id uuid`, `dia date`, `escalon smallint (1-5)`,
  `cuota_total real`, `prob_total double precision`, `n_patas smallint`,
  `decided_at timestamptz`. Único `(dia, escalon)`.
- `parley_patas`: `pata_id uuid`, `ticket_id` → tickets, `match_id` →
  matches, `market`, `selection`, `line`, `prob`, `fair_price`, `price`,
  `book`, `odds_source`, `odds_as_of`. Único `(ticket_id, match_id)`. Mismo
  `CHECK` de mercados que `escalera_pasos` más `double_chance`.
- `parley_resultados_pata` y `parley_resultados`: resultado de cada pata
  (`outcome`, fracciones ganada/devuelta) y del ticket (`outcome`,
  `factor_pago`, `settled_at`).
- Triggers `deny_mutation()` en tickets, patas y resultados (inmutables, como
  `alta_prob_picks`).

## Sellado

- Orden en `daily.run`: predecir → picks → alta probabilidad → escalera →
  **`parley_datos.select_and_persist()`** → `seal()`.
- `hashchain._collect` mete en el lote los tickets y patas decididos ese día,
  desde `LOTE_PARLEY_DESDE` (fecha del primer lote sin sellar al desplegar).
- Un ticket solo se muestra si su lote existe y se selló **después** de
  decidirlo (mismo criterio `_sql_sellado` que la escalera).
- Si la selección falla: `log.exception` + `tg.alert`; el job sigue. Si hay
  tickets y el sello falla: alerta "Parley SIN SELLAR".
- Interruptor `PARLEY_ENABLED` (`config.py`), apagado por defecto.

## Liquidación

Enganche en `clv.settle_pending()` (ya se dispara con cada resultado).

- Cada pata se liquida con la lógica existente: `escalera_datos.resultado`
  para córners/tarjetas/goles por equipo y `clv._settle_outcome` para el resto
  (incluye cuartos de hándicap).
- Factor de la pata: ganada = cuota; perdida = 0; nula/devuelta = 1;
  medio ganada = (cuota + 1) / 2; medio perdida = 0,5.
- Partido aplazado más de 48 h desde su hora original: pata nula
  (`MARGEN_APLAZADO`, como la escalera).
- Ticket: se liquida cuando todas sus patas lo están. `factor_pago = Π
  factores`. `outcome`: `ganado` si ninguna pata perdió (ni entera ni media) y
  alguna se ganó; `perdido` si alguna pata perdió entera; `parcial` si solo
  hubo medias pérdidas; `nulo` si todas fueron nulas.
- **Acierto** (para comparar con lo prometido) = `outcome = ganado`.

## API

`GET /parley` en el router público (`api/main.py`), servido por
`parley_datos.informe_publico()`:

- `hoy`: tickets sellados del día con escalón, cuota, probabilidad y patas
  (partido, hora, texto del pronóstico, cuota, casa, estado).
- `historial`: todos los tickets sellados, también perdidos, agrupados por
  día, con el `chain_sha256` del lote.
- `resumen_por_escalon`: liquidados, acertados, % real frente a probabilidad
  media prometida, unidades y ROI a 1 unidad por ticket.
- `control`: estado del control por escalón (ver abajo).
- Textos de pronóstico con las funciones existentes (`escalera_datos.texto`).

## Control prometido frente a real

Mismo patrón que `alta_prob.control`: por escalón, con al menos **50**
liquidados y **10 semanas** distintas, IC del **99 %** (bootstrap por semanas)
de `acierto real − probabilidad prometida`. Si el IC queda entero por debajo
de cero, el escalón se **pausa** (deja de elegirse) y la pestaña lo dice. Por
debajo de la muestra: "muestra insuficiente".

## Web

- Ruta `parley` en el menú de Fútbol (`frontend/app.js`, grupo EXPLORAR),
  junto a Escalera y Alta probabilidad; `public-data.js` consulta `/parley`.
- Arriba: tarjetas de hoy (escalón, cuota total, probabilidad, patas con hora
  en la zona del navegador). Debajo: resumen por escalón y historial por día.
- Reutiliza los estilos de la escalera (`ladder-card`, `live-pick-list`).
- Texto fijo: "Se elige por probabilidad, no por valor: el margen de la casa
  se paga en cada pata. Cada parlay se sella en la cadena antes del partido."

## Pruebas

- Búsqueda: igual al óptimo por fuerza bruta en casos pequeños aleatorios;
  respeta rango de escalón, 2–6 patas, una pata por partido, ningún partido
  repetido en el día, cuota ≥ 1,15, filtro de cuota errónea; desempate
  determinista; escalón sin solución se salta.
- Sin fuga: ninguna pata con `odds_as_of` posterior a `decided_at` ni partido
  empezado.
- Liquidación: ganado, perdido, nulo, aplazado, cuartos de hándicap (medio
  ganado / medio perdido) y factor de pago.
- Triggers: UPDATE y DELETE rechazados en las cuatro tablas.
- Lote: los tickets entran en `_collect` solo desde `LOTE_PARLEY_DESDE`.
- Frontend: render de hoy, historial vacío y error de consulta
  (`*.test.mjs`).

## Despliegue

1. Desplegar con `PARLEY_ENABLED=0` (migración + código).
2. Vista previa en seco (`parley_datos ensayo`) con los partidos del día
   siguiente; el usuario la revisa.
3. Activar con su visto bueno; `LOTE_PARLEY_DESDE` = primer lote sin sellar.

## Riesgos

- **Errores multiplicados**: un sesgo pequeño por pata se multiplica en el
  parlay. Lo vigila el control por escalón; por eso no es opcional.
- **Escalones altos con poca muestra**: el ≈5,0 saldrá menos días; su control
  tardará meses en tener veredicto.
- **Cuotas de una sola casa**: la mejor cuota puede ser de una casa que el
  usuario no tiene; la pestaña muestra la casa de cada pata.
