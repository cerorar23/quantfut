# NBA — ganador con Elo ponderado por la plantilla actual (rechazado, 26-oct-2026)

Encargo del titular: medir una corrección del ganador para equipos con traspasos grandes, con protocolo congelado y sin tocar el
productor hasta comparar. Motivo: la cohorte sellada `2026-10-26_1830` dio a Milwaukee un 69 % en casa contra Indiana mientras el
mercado le daba un 41 %. Giannis Antetokounmpo juega ahora en Miami y la rotación de Milwaukee son sobre todo jugadores que la
temporada pasada estaban en otros equipos, pero el Elo de margen arrastra el 75 % del rating de Milwaukee de 2025-26.

Protocolo congelado antes de calcular ningún número: `apps/nba/nba_roster_elo_protocol.json` (sha256 `7e72884b…`, en
`apps/nba/.local/normalized/nba_roster_elo_20261026/protocol_frozen.json`). Código: `nba.roster_elo` y `nba.roster_elo_check`.
Mismos datos que el productor 1.5.0 (`players` `e5326b7f…`, `games` `c2c13b36…`, reportes `03c24054…`).

## La corrección
- **Rotación** de un equipo en la fecha d: jugadores con minutos en sus últimos 5 partidos de la temporada (antes de d) cuya última
  aparición fue con ese equipo; minutos esperados = media en esos partidos.
- **Rating que arrastra cada jugador**: media, ponderada por minutos, del Elo actual de los equipos con los que jugó sus últimas
  30 apariciones. Quien jugó todo con el equipo arrastra exactamente su Elo, así que un equipo sin fichajes no cambia.
- **Elo efectivo** = (1 − α) · Elo del equipo + α · media de la rotación, con pesos por minutos o por minutos × producción por
  minuto (puntos + rebotes + asistencias + robos + tapones − pérdidas). Sustituye a `elo_gap_mov` en entrenamiento y prueba; las
  actualizaciones del Elo no cambian.
- Rejilla {minutos, producción} × α {0,5; 1}, elegida en 2024-25 (modelo ajustado en 2022-23 y 2023-24) y aplicada sin tocar a
  2025-26. El primer partido de cada temporada no tiene rotación y no se corrige.

## Resultado

Ajuste en 2024-25 (diferencia de Brier frente al modelo desplegado; positivo = peor): las cuatro configuraciones empeoran.

| Configuración | 2024-25 | 2025-26 (IC 95 %) | Partidos movidos ≥ 25 Elo en 2025-26 |
| --- | --- | --- | --- |
| producción, α 0,5 (**elegida**) | +0,000026 | +0,00038 [−0,00005; +0,00082] | 31: +0,0051 |
| minutos, α 0,5 | +0,000050 | +0,00037 [−0,00008; +0,00081] | 35: +0,0056 |
| producción, α 1 | +0,000145 | +0,00094 [+0,00007; +0,00184] | 157: +0,0065 |
| minutos, α 1 | +0,000204 | +0,00094 [+0,00004; +0,00184] | 160: +0,0065 |

- Modelo desplegado en 2025-26 (1.206 partidos): Brier 0,2005, log loss 0,585, pendiente 1,04. Con la corrección elegida: Brier
  0,2009 y log loss 0,586. Los primeros 30 días también empeoran (+0,0010, 219 partidos).
- **No entra**: la cota superior del IC es positiva. Con α 1 el empeoramiento es significativo. Donde más mueve el Elo (≥ 25
  puntos), más empeora.

**Por qué no funciona (explicación, no medida).** El rating que arrastra un jugador es el de su equipo anterior, no lo que vale él: un titular de un buen
equipo que llega a uno malo no lo convierte en bueno, y uno que sale de un equipo malo hunde a su nuevo equipo aunque sea bueno.
Ponderar por producción da más peso a las estrellas, pero sigue repartiendo ratings de equipo, no de jugador.

## Consecuencias
- **El productor no cambia.** El ganador de 1.5.0 sigue como está.
- El fallo de IND @ MIL del 26-oct sigue sin arreglo en el modelo: con traspasos grandes en verano, el ganador del modelo es poco
  fiable en las primeras semanas. Para valorar traspasos haría falta un rating propio de cada jugador (más-menos ajustado o un
  valor por posesión), que es un modelo nuevo, no un ajuste del Elo. No se probó aquí.
- Tampoco se probó una regresión de temporada más fuerte (hoy 0,25): sería otro protocolo.

## Límites
- Retrospectivo sobre una temporada de prueba; 2025-26 ya se había mirado para otras preguntas (líneas de bet365, `nba_live15`
  para puntos y total), nunca para el ganador con corrección de plantilla.
- El registro prospectivo es la prueba real.
