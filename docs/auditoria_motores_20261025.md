# Auditoría de los tres motores de fútbol tras el cambio a PropLine y SofaScore (25-oct-2026, 04:50 UTC)

Pregunta del titular: ¿reciben los tres motores los datos actualizados de las dos APIs nuevas (PropLine y SofaScore vía
Apify) y están generando pronósticos? Continúa `docs/auditoria_motores_20261024.md`, ahora con el worker `117feb7`
(despliegues del 25-oct 02:23 y 04:25 UTC). **Solo lectura**: SELECT a la base, registros del worker y del recolector,
y una vista previa sin guardar (`alta_prob_datos.select_and_persist(dry_run=True)`) con `now` = corrida de las 09:00 UTC.

## Resumen

| # | Gravedad | Hallazgo |
|---|---|---|
| 1 | **crítica** | **Motor B y Motor C sin pronósticos desde el 22-oct.** 23-oct: sin precio (The Odds API sin créditos, API-Football en plan gratis). 24-oct: `AttributeError … 'disponible'` (worker con versiones mezcladas). Corregido en `ab82dcb`; la primera corrida real es hoy a las 09:00 UTC |
| 2 | **crítica** | **19 de 63 partidos de la corrida de hoy sin precio** porque los nombres de PropLine no tienen alias (Inter–Fiorentina, Lecce–Juventus, Independiente–Boca, River–Racing, Sparta–Ajax, Angers–Lorient…). PropLine **sí** trae esos partidos a la hora exacta. 84 nombres sin emparejar en ligas activas (Copa UEFA 25, Brasil 24, Argentina 17) |
| 3 | alta | La misma falta de alias deja resultados sin cerrar: 13 `sin_evento` en cada pasada de PropLine y **19 huérfanos** (Serie B 7, LaLiga 2 3, Suiza 3, MLS 3…) |
| 4 | alta | Motor A: el xG llega de SofaScore solo en **25 de 95** partidos cerrados el 25-oct (26 %); antes API-Football lo daba en todos. Afecta al reentrenamiento del 1-nov (mezcla xG 0,65) |
| 5 | alta | Motor C: amarillas en **30 de 95** cerrados (solo los que tienen detalle SofaScore) y árbitro en 65 de 95; la pasada de resultados de las 03:45 cerró 12 partidos con **0 córners** |
| 6 | alta | Sigue sin cargarse ningún cierre de PropLine (`window_tag` de cierre: 0 de 238.150 filas): CLV, sombra y puerta comercial congelados |
| 7 | media | El chequeo diario dice «xG al día» con el 26 % de cobertura |

## 1. ¿Llegan los datos nuevos?

| Fuente | Estado medido |
|---|---|
| **PropLine (recolector compartido)** | Funciona. Última pasada 04:07–04:16 UTC, 162 peticiones, 0 fallos, 1.180 de 5.000 del día. En `odds_snapshots`: 187.973 filas el 24-oct (186 partidos) y 50.177 el 25-oct (151). The Odds API, última fila 23-oct 16:00; `af_odds_snapshots` casi a cero desde el 23-oct |
| **PropLine → worker** | `odds_worker` importa cada pasada horaria (última: 4.238 filas, 81 partidos); las pasadas intermedias dan 0 filas porque no hay archivo nuevo, es lo esperado. `unmatched_events` 192: incluye partidos fuera de ventana y los nombres del hallazgo 2 |
| **PropLine → resultados/calendario** | 95 partidos cerrados el 25-oct (81 con córners). Calendario PropLine: 280 enlazados, 3 altas, 46 sin resolver. La pasada de `fixtures` de las 05:15 UTC será la primera con el worker nuevo (las de ayer aún fallaban contra API-Football) |
| **SofaScore (rl1987)** | 45 detalles cargados en `sofascore_detalles` (25 con xG), 0 conflictos de marcador. Bajas: 293 filas de 54 partidos (`source='sofascore'`). Onces previstos: 110 filas de 55 partidos. Onces oficiales: 0 todavía (ningún partido en T-65..T-20 desde el despliegue) |

## 2. ¿Generan pronósticos?

| Motor | Último producido | Estado |
|---|---|---|
| **A** (Dixon-Coles) | 53 predicciones el 24-oct (lote diario sellado) y 3 `final` el 25-oct por sello tardío. Modelo `2026.10.22-185314` | **Sí** |
| **B** (Pinnacle sin margen) | Alta probabilidad, ampliada, escalera y parley: última fila el **22-oct** | **No desde el 22-oct.** Vista previa de las 09:00 de hoy: 63 partidos, 30 decisiones candidatas, **todas con precio de PropLine** (doble oportunidad 11, hándicap 10, goles 5, goles del local 4), 14 sin candidato, 19 sin precio (hallazgo 2) |
| **C** (córners/tarjetas) | `tarjetas_seg`: última fila el 22-oct; córners dentro de B, igual | **No desde el 22-oct** (depende de la corrida de B) |

La vista previa no estima `elegidos` (no guarda); el número real se verá en `daily.log` a las 09:00 UTC.

## 3. Partidos sin precio (vista previa de las 09:00)

Comprobado uno por uno contra el archivo de PropLine: el evento existe con la misma hora; `resolve_team(…, "odds_api")`
devuelve `None` para al menos uno de los dos nombres:

`ACF Fiorentina`, `US Lecce`, `CA River Plate (Arg)`, `Racing Club Avellaneda`, `Ajax Amsterdam`, `Angers SCO`,
`Nacional da Madeira`, `Molde FK`, `Corum Belediyespor`, `Albacete Balompie`…

La lista completa está en `unresolved_names` (`source='odds_api'`, `last_seen > 2026-10-24`). Varias mejores
conjeturas del difuso son **erróneas** (`Atletico Lanus → atletico san luis`, `Club Brugge → brage`,
`Sporting CP → porto`, `1. FC Cologne → boulogne`): los alias se tienen que revisar a mano, no aceptar la conjetura.

## 4. Después de la auditoría (25-oct, tarde)

- La corrida de las 09:00 UTC funcionó: 41 predicciones del Motor A, **28 de alta probabilidad** y la escalera con
  plan nuevo; 19 partidos sin precio, los mismos que anticipó la vista previa.
- A las 13:36 UTC se dieron de alta 150 alias `odds_api` revisados a mano (ver DEPLOYS.md). Causa de fondo: el
  calendario y los resultados de PropLine aprenden alias con la fuente `propline`, pero el lector de cuotas solo mira
  `odds_api`. En la pasada de las 13:40 entraron cuotas de 48 partidos que antes no emparejaban.

## 5. Siguiente paso propuesto (redactado antes del alta)

Dar de alta los alias de PropLine de las ligas activas (`scripts/bootstrap_aliases.py` o alta manual revisada) antes de
las 09:00 UTC, para que la primera corrida del Motor B tenga precio en los 63 partidos y los huérfanos se liquiden. Es
una escritura en producción: necesita el visto bueno del titular. Sin tocar: cierres de PropLine, cobertura de xG y de
tarjetas (hallazgos 4–6).
