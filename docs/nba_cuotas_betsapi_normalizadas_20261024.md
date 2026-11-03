# NBA — cuotas históricas de BetsAPI/bet365 normalizadas (24-oct-2026)

Código: `apps/nba/src/nba/betsapi_odds.py` (`freeze`, `build`). Pruebas: `apps/nba/tests/test_betsapi_odds.py`.
Protocolo: `apps/nba/nba_betsapi_odds_protocol.json` (v1.1, congelado antes de reconstruir; el hash vigente y el reemplazado están en
`apps/nba/.local/normalized/nba_betsapi_odds_20261024/protocol_frozen.json`; `build` se niega a correr si cambia).
Entrada: copia de `~/betsapi/data/nba` del VPS tomada el 24-oct 19:48 UTC (3.996 eventos, 203 MB), cada archivo con su sha256 en `inputs_manifest.json`.
Salida (esa carpeta): `odds.jsonl.gz`, `coverage.json`, `inputs_manifest.json`. Solo datos: no entrena ni promueve nada.

## Qué hay
Una fila por (partido, mercado) con apertura, cierre previo al salto y la trayectoria completa de la línea, unida a `game_id` y liquidada
con el resultado oficial. 34.713 filas, 3.867 partidos de 2023-24, 2024-25 y 2025-26 (3.598 de temporada regular, 251 de playoffs y 18 de play-in).

| Mercado | Filas | Cierre ≤ 60 min | Cierre mediano antes del salto | Empates (push) |
| --- | --- | --- | --- | --- |
| `ml_game`, `spread_game`, `total_game` | 3.867 c/u | 99,7-99,8 % | 2,3 min | 0 / 7 / 11 |
| `ml_h1`, `spread_h1`, `total_h1` | 3.852 c/u | 99,9 % | 1,5 min | 122 / 6 / 5 |
| `ml_q1`, `spread_q1`, `total_q1` | 3.852 c/u | 99,9 % | 1,5 min | 185 / 9 / 5 |

Cada fila trae `open`/`close` (`line`, `p1`, `p2` en el orden local/visitante o over/under, `p1_novig`, `overround`, segundos antes del salto),
`path` (todas las fotos válidas como `[segundos_antes, línea, p1, p2]`), `y_open`/`y_close` (1 = gana el local, cubre el local o over; 0 = lo
contrario; `null` = push) y los puntos del periodo. `ml_h1` tiene 6 partidos sin liquidar porque el marcador de la mitad no suma Q1+Q2.

## Lo que se descubrió al construirlo
- **BetsAPI lista primero al visitante como «home».** En los 3.867 partidos emparejados (100 %) el equipo «home» del archivo es el visitante
  oficial, y sus precios y su hándicap le pertenecen. La primera pasada con el protocolo v1.0 no emparejó ninguno y no escribió filas;
  una sonda de orientación (equipos, fecha y marcador contra la referencia, sin cuotas ni métricas) lo mostró y el protocolo pasó a v1.1:
  la clave es la pareja de equipos sin orden y cada fila se reorienta al local oficial (precios intercambiados, línea del hándicap con
  el signo cambiado, totales intactos). La regla de aceptación del 99 % sobre todos los eventos estaba mal planteada, porque la referencia
  excluye partidos propios; ahora cuenta el acuerdo de marcador entre los eventos que sí tienen partido de referencia.
- **Chequeos de integridad tras construir** (no son métricas de modelo): victoria local 55,1 % frente a 55,5 % implícito en el cierre;
  margen local + línea local = +0,05 en el partido, +0,01 en la mitad y +0,13 en Q1 (≈ 0, así que la orientación es correcta);
  ninguna foto es posterior al salto y todas las trayectorias están ordenadas.

## Reglas de las fotos previas (resumen; completas en el protocolo)
Solo `add_time` estrictamente anterior al inicio programado; se aceptan filas sin estado en vivo o con el estado previo al salto
(`0:0`, `1 - 12:00`); se descartan precios suspendidos (`-`), `+999` y sobreoverround fuera de [−0,02; 0,25]. Cuando varias líneas comparten
instante, la principal es la de precios más equilibrados.

## Cobertura y límites
- Emparejamiento: 3.867 de 3.869 eventos con partido de referencia (99,95 %); 2 por marcador distinto. Fuera: 93 sin partido en la referencia
  (sin verificar caso a caso; la referencia deja fuera partidos en cuarentena y no trae la pretemporada), 23 de 2026-27 y 11 aplazados. La referencia tiene 2.547 partidos sin cuotas (2021-22 y 2022-23, que BetsAPI no trae).
- Una sola casa (bet365): sin Pinnacle ni consenso. Sin totales por equipo, sin Q2-Q4 ni segunda mitad, sin props de jugador.
- Es una descarga histórica: `add_time` es la marca del proveedor y nuestra recepción original es desconocida. «Cierre» es el último precio
  con marca anterior al inicio programado, no una línea de cierre verificada, y no prueba que un cliente hubiera podido tomarlo.
- El cierre de bet365 es un baseline duro (margen mediano 7 %); sirve para calibrar y medir, no para afirmar valor.
