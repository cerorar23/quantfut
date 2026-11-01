# Serie A como base del rediseño: datos nuevos de SofaScore y recomendaciones (31-oct-2026)

Estado: **análisis y recomendaciones; ningún motor nuevo construido ni desplegado.** Continúa el borrador
`docs/superpowers/specs/2026-10-30-modelo-probabilistico-futbol-design.md` (pronósticos probabilísticos
calibrados) y la descripción de los tres motores en `docs/MOTOR_Y_PICKS_AL_DETALLE_20261015.md`.

**La sección 0 (1-nov) prevalece sobre el resto donde se contradigan.** Las secciones 1–7 se escribieron el 31-oct,
antes de la tabla única `futbol.dato`, y se conservan como registro de lo medido y leído.

## 0. Cambios del 1-nov-2026: tabla única, ligas con más datos y retiro de lo redundante

### 0.1 De dónde lee el motor

Desde el 1-nov todo lo de fútbol que alimenta al motor está en **una sola tabla, `futbol.dato`** (db/094–096, diseño
en `docs/futbol_modelo_canonico_20261101.md`): una fila por hecho (`tipo` = jugador, equipo, baja, alineacion,
entrenador, contexto, tiro, incidencia, clima, estadio, momentum, posicion), nombres de campo unificados, una fuente
por tipo y partido, `fuente`, `recibido_en` y `pit` en cada fila. Fuera de ella, a propósito, solo quedan `matches`
(identidad y resultado del partido) y `odds_snapshots` (cuotas, inmutable).

Consecuencias para este rediseño:
- La fase **F1 queda hecha** por otra vía: el «esquema `futbol` del borrador» (tiro, jugador_partido, alineación,
  baja, incidencia, contexto) es hoy `futbol.dato`. Ningún motor nuevo lee tablas de origen (`fotmob_*`,
  `historical_football_*`, `estadisticas_jugador`, archivos SofaScore): solo `futbol.dato` + `matches` + `odds_snapshots`.
- Identidad de jugador única (`jugador_id` = id de SofaScore; negativo determinista si aún no tiene pareja). A4
  (plus-minus) y A5 (rotación) se construyen sobre ese id, no sobre el de FotMob.
- El motor actual sigue leyendo las tablas de origen (`FUTBOL_LECTURA=origen`, por defecto). Pasar a `canonica`
  exige comparar el modelo con las dos lecturas sobre las mismas filas (pendiente 4 del traspaso).

### 0.2 Ligas que usa el motor por ahora: las que tienen más datos

Medido el 1-nov en producción (partidos terminados de `matches` frente a filas de `futbol.dato`). El titular está
descargando en local el historial completo del resto de ligas; mientras tanto el rediseño se construye y se mide
**solo con las ligas del nivel 1**.

| Nivel | Ligas | Temporadas completas | Qué tienen | Uso en el rediseño |
|---|---|---|---|---|
| **1 — núcleo (6)** | Serie A, Bundesliga, Ligue 1, Eredivisie, Primeira, Brasileirão | 23/24 → 26/27 (4) | tiros con coordenadas y xG en ≥ 99,6 % de los tiros, estadísticas de equipo por mitad, incidencias con minuto, once, entrenador, jugadores | todas las fases F2–F5; Serie A sigue como liga para construir y depurar primero |
| **1b — núcleo sin 23/24 (2)** | Premier, LaLiga | 24/25 → 26/27 (3); 23/24 solo FotMob desde enero (184 y 200 de 380) | igual que el nivel 1 | entran en F2–F5 desde 24/25; 23/24 de calentamiento cuando se descargue |
| **2 — parcial (2)** | Liga MX, Argentina | Liga MX 4 temporadas de bloques, pero **0 % de xG por tiro en 23/24 y 24/25**; Argentina 24/25 con tiros en 163 de 581 partidos y xG por tiro en ~50 % de 25/26–26/27 | todo menos xG por tiro completo | Liga MX: A0, A4, motor C (córners/tarjetas). Argentina: fuera hasta completar la descarga |
| **3 — solo FotMob (13)** | Championship, LaLiga2, Serie B, 2. Bundesliga, Ligue 2, Süper Lig, Superliga danesa, Eliteserien, Allsvenskan, Super League suiza, MLS, Champions, Europa League | 3–4 | jugadores (minutos, titular, nota), once, bajas; **sin tiros, sin incidencias, sin estadísticas de equipo por mitad** | solo el motor A actual; nada de F3–F5 hasta descargarlas de SofaScore (la Champions y la Europa League solo como historia de los clubes del núcleo, ver 0.3) |

Regla de activación (sustituye a F6): una variante se activa si mejora en las **8 ligas del núcleo** (niveles 1 y 1b)
con el mismo protocolo (walk-forward, `check_leakage()`, log score, Diebold-Mariano agrupando ligas). Cuando el
titular termine de descargar una liga, se añade a las listas de `futbol_diario.sh`/`recarga_ampliada.sh`, se mide su
cobertura con esta misma tabla y, si llega al nivel 1, entra en la siguiente evaluación.

### 0.3 ¿Tenemos los datos que piden los estudios? (revisión columna por columna, 1-nov)

Cruce de lo que necesita cada componente respaldado en las secciones 4 y 4b con lo que hay en `futbol.dato`,
`matches` y `odds_snapshots`. Cifras de las ligas del núcleo salvo que se diga otra cosa.

| Componente (estudio) | Datos que exige | Dónde está | Estado |
|---|---|---|---|
| A0 *score-driven* (Koopman-Lit) | goles por partido en orden temporal | `matches` | ✔ todas las ligas, desde 14/15 |
| Referencia pi-ratings (Constantinou) | goles o xG por partido | `matches` | ✔ |
| Referencia de mercado (Kaunitz, Štrumbelj) | cierres de varias casas sin margen | `odds_snapshots` (football-data: Pinnacle/bet365; PropLine desde 23-oct) | ✔ 1X2 y goles 2,5 históricos; ✗ córners y tarjetas antes del 23-oct |
| A1 xG sin penaltis por tiro | xG por tiro y situación | `tiro.xg`, `tiro.situacion = 'penalty'` | ✔ núcleo (≥ 99,6 %); ✗ Liga MX 23/24–24/25 |
| A2 estado del partido | minuto de goles, rojas y tiros; marcador | `incidencia` (goal, card red/yellowRed, minuto, marcador), `tiro.minuto` | ✔ núcleo |
| A3 definición y portero | xGOT por tiro, portero del tiro, goles evitados | `tiro.xgot`, `tiro.portero_id`, `jugador.goles_evitados` | ✔ núcleo |
| A4 plus-minus por tramos (Pantuso-Hvattum, Bajons-Hornik) | once, cambios y rojas con minuto, goles y xG por tramo, edad, liga | `alineacion`, `jugador.titular/minutos/edad`, `incidencia` (substitution 97.191, red 1.815, yellowRed 919), `tiro` | ✔ núcleo; ✗ nivel 3 (sin incidencias de cambio: FotMob las trae en el original pero no se cargan) |
| A5 rotación y carga de 30 días (Page et al.) | minutos de cada jugador en **todas** las competiciones, incluidas copas | `jugador.minutos` en ligas + Champions/Europa League (FotMob) | **parcial**: faltan las copas nacionales. `calendario_equipo` (API-Football) tiene fechas de copas pero no minutos y está congelada desde el 22-oct |
| A5 suspensiones (Kruse-Maennig) | amarillas por jugador con fecha, umbral de sanción de cada liga, rival siguiente | `incidencia` card con `jugador_id` (≥ 95 % de partidos), `matches`, `futbol.regla_sancion`, `futbol.amarillas_acumuladas()` | ✔ en las 6 ligas con umbral 5 o 3 medido (Serie A, Bundesliga, LaLiga, Eredivisie, Primeira, Brasileirão); **pendiente verificar contra el reglamento**; ✗ Ligue 1 (4 y 5 empatadas), Premier (por jornada) y Argentina sin umbral fijo |
| A6 bajas | ausentes con motivo | `baja` | **parcial**: 23/24 de Eredivisie (141/309), Primeira (133/306), Brasileirão (157/380) y Liga MX (144/340) incompleto |
| A7 entrenador | entrenador por partido | `entrenador` | ✔ 100 % |
| A5 en vivo (T-60) | once previsto y bajas previas con hora de captura | `baja_previa`, `once_previo`, `alineacion_previa` con `pit = 'previo'` (db/099) | ✔ **desde el 18-oct** (FotMob) y el 25-oct (once previsto) en adelante; el histórico anterior es reconstrucción (`pit = 'reconstruido'`) |
| C córners (Yip) | córners por equipo, goles esperados, supremacía, medias de centros, toques en el área, entradas al último tercio | `matches.home/away_corners`, `equipo` (`centros_acertados`, `toques_area_rival`, `entradas_ultimo_tercio`) | ✔ núcleo |
| C tarjetas (Dawson 2007/2008, Kruse-Maennig) | tarjetas local/visita, **identidad del árbitro**, faltas por equipo, entrenador, temporada, derbi, llenado del estadio | `matches` (tarjetas, `referee_fotmob`), `equipo.faltas`, `contexto.asistencia`, `estadio.estadio_capacidad` | **parcial**: árbitro vacío en la primera mitad de 23/24 (Serie A 200/380, Bundesliga, Ligue 1, Eredivisie y Primeira ~50 %, Brasileirão 0), que db/097 y la recarga llenan; asistencia escasa en Eredivisie (7), Primeira (58), Liga MX (4) y Brasileirão (145); derbis en `futbol.derbi` (db/098) |
| C3 mercados por mitad | córners, tarjetas, tiros y xG por mitad | `equipo` evento 1/2 | ✗ **córners, tiros, xG y tarjetas por mitad se descartaban al cargar** (corregido el 1-nov, ver abajo); faltas por mitad solo en ~1/3 de los partidos |
| C5 props de jugador | minutos, tiros, a puerta, tarjetas por jugador | `jugador` | ✔ |
| Auditoría de fugas (Frontiers 2026) | saber qué es previo | `pit` por fila | ✔ columna; la **trayectoria del árbitro** de SofaScore (`arbitro_partidos`, `arbitro_amarillas`…) se contó al descargar y es **posterior**: no usarla, recalcular con `matches` |

**Corregido el 1-nov (rama `futbol/dato-unico`, sin desplegar):**
1. `futbol_sofascore.py` guardaba de las estadísticas por mitad todo **menos** córners, tiros totales y a puerta, xG y
   tarjetas, porque «ya viven en `matches`»; pero `matches` solo tiene el partido completo. Ahora se guardan en las
   filas de equipo de evento 1 y 2 (db/097 añade `corners`, `amarillas`, `rojas`); el partido completo sigue sin
   repetirse.
2. Del árbitro se guardaba la trayectoria pero no **quién es**. Ahora la fila `contexto` lleva `nombre` e
   `id_en_fuente` del árbitro de SofaScore, que rellena los árbitros que faltan en 23/24.
3. Ambos necesitan aplicar db/097 y recargar las 10 ligas de SofaScore con `--forzar` (idempotente).

**Hecho también el 1-nov (db/098 y db/099, sin aplicar en producción):**
1. **Umbrales de sanción** (`futbol.regla_sancion`): medidos con los propios datos (moda de las amarillas acumuladas de
   los sancionados) y marcados `verificada = false` hasta contrastarlos con el reglamento. Serie A 5 (49 %),
   Bundesliga 5 (51 %), LaLiga 5 (30 %), Eredivisie 5 (43 %), Primeira 5 (44 %) y Brasileirão 3 (51 %). La Premier va
   por jornada (5, 10 y 15 amarillas: la medición no lo delata), la Liga MX no suspende por acumulación (72 % de
   sanciones con 0 amarillas) y Ligue 1 (4 y 5 empatadas) y Argentina quedan sin fila. `futbol.amarillas_acumuladas()`
   da las del jugador en la liga y temporada antes de un instante.
2. **Derbis** (`futbol.derbi`, `futbol.cargar_derbis()`): regla automática (dos clubes de la liga en la misma ciudad;
   con más de dos —Londres, Buenos Aires, Estambul— no vale) más una lista manual de 26 rivalidades. Comprobado en
   solo lectura con producción: los 14 nombres de la lista original resuelven a un equipo único (Porto–Sporting
   necesitó `Sp Lisbon`). Sin el tope de dos clubes la regla daba 17 «derbis» en la Premier (Londres) y 28 en Argentina;
   con el tope ya no los da. Los derbis de las ligas de nivel 3 con ciudades grandes (Estambul) no se completan a mano.
3. **Fase 2** (`futbol.cargar_previo()`): `baja_previa`, `once_previo` y `alineacion_previa` con la hora real de cada
   captura y `pit = 'previo'` si fue antes del saque. Cargan las cuatro tablas de captura (`fotmob_baja_previa`,
   `fotmob_jugador_previo`, `lineups_previstas`, `injuries`) sin tocar su captura. Se conservan todas las capturas
   (sin «una fuente por tipo»): el motor toma, por fuente y jugador, la última anterior a T-60. La vista
   `futbol.v_baja_a_t` da las bajas previas con su antelación. Del orden de 140.000 filas al cargar lo
   existente (`injuries` desde el 2-oct, FotMob desde el 18-oct, once previsto desde el 25-oct).

**Lo que sigue sin resolverse con código:** copas nacionales (minutos de jugador), verificar los umbrales de sanción
con el reglamento de cada liga, histórico de cuotas de córners y tarjetas (solo hacia delante, PropLine) y las
descargas pendientes del titular (Premier y LaLiga 23/24, Argentina, nivel 3). Ninguno impide empezar: F2–F4
(referencias, A0–A3, córners) se pueden hacer ya con el núcleo; A5 y las tarjetas completas esperan a las copas y a
la verificación de umbrales. Bajas incompletas de 23/24 en 4 ligas: se aceptan (temporada de calentamiento; contar
bajas no aportó en los estudios).

### 0.4 Retiro de las tablas de origen redundantes

Base de producción: 4,96 GB (`futbol.dato` 1,24 GB). Se retira solo lo que **ya está en `futbol.dato` o se puede
regenerar desde un original conservado**, y nada que lea un motor en producción. Revisado código (`src/`, `scripts/`),
vistas, funciones y claves foráneas.

| Tabla | Tamaño | Qué es | Quién la usa | Propuesta |
|---|---|---|---|---|
| `historical_football_player_stats` | 1.102 MB (845 MB de JSON) | derivada del original FotMob (`historical_football_matches.raw_payload_gzip`) | `v_fotmob_jugador_partido` → `futbol.cargar_fotmob` (pasada diaria) | **R1:** antes, que `cargar_fotmob` no pise con NULL un partido sin estadísticas; después, borrar las filas de partidos ya cargados en `futbol.dato` y de más de 14 días, y `VACUUM FULL`. Regenerable desde el original. ≈ 1 GB |
| `historical_football_lineups` | 134 MB | derivada del mismo original | nadie | **R2:** mismas reglas que R1. ≈ 130 MB |
| `historical_football_absences` | 11 MB | derivada; idéntica a `fotmob_baja` (0 diferencias en 47.140 filas) | nadie | **R2** |
| `af_odds_snapshots` | 476 MB | cuotas de API-Football (fuente retirada; lectores borrados en la fase 2c) | nadie | **R3:** exportar a archivo comprimido (VPS y copia local), comprobar recuento y hash, y `DROP`. Es **inmutable por trigger**: exige confirmación explícita del titular |
| `sofascore_detalles` | 7,5 MB | detalles SofaScore de db/085 (212 filas), sustituidos por `futbol.dato` | nadie | **R3**, igual que la anterior (también inmutable) |
| `fotmob_jugador_partido`, `fotmob_baja`, `fotmob_partido` | 220 + 13 + 9 MB | entrada tipada de FotMob | motor actual (`jugadores`, `ajuste_xi`, `contexto`) y `cargar_fotmob` | **R4**, más adelante: tras activar `FUTBOL_LECTURA=canonica` y comparar el modelo |
| `estadisticas_jugador` | 37 MB | API-Football, congelada desde el 22-oct | `model/player_value.py` | **R4**, tras pasar `player_value` a `futbol.dato` |
| `historical_football_matches` | 629 MB | **original** FotMob | importador, `fotmob_a_motor` | **Se queda** (regla de conservar las observaciones originales) |
| `odds_snapshots` | 719 MB | cuotas, inmutable | picks y cadena de hashes | **Se queda** |

R1 + R2 + R3 liberan ≈ 1,6 GB (un tercio de la base). Cada paso: `pg_dump` previo, ensayo con `BEGIN … ROLLBACK`
sobre los datos reales y anotación en `DEPLOYS.md` con su vuelta atrás.

## 1. Qué trae la descarga nueva (medido hoy, archivo local)

Ubicación: `C:\Users\huye\Documents\SOFASCORE\data\v3`. Serie A = torneo 23; temporadas 23/24 (52760),
24/25 (63515), 25/26 (76457) y 26/27 (95836, en curso). Calendario en `tournaments\23\seasons\<id>\schedule`,
cada partido en `events\<2 díg.>\<3 díg.>\<id>\` (13 archivos `.json.gz` + `manifest.json` con sha256).

| Bloque | 23/24 | 24/25 | 25/26 | 26/27 | Nota |
|---|---|---|---|---|---|
| Partidos terminados con carpeta | 380 | 380 | 380 | 90 | 1.230; 0 errores de descarga |
| Mapa de tiros con coordenadas | 380 (9.702 tiros) | 380 (9.250) | 380 (9.381) | 90 (2.649) | ~25 tiros/partido; parte del cuerpo, situación, portero, coordenadas de bloqueo y de portería |
| xGOT en el mapa de tiros | 379 | 380 | 380 | 90 | |
| xG en **todos** los tiros del partido | 358 | 343 | 361 | 83 | en el resto faltan algunos tiros sin xG |
| Estadísticas de equipo por mitad (1T/2T) | 380 | 380 | 380 | 90 | 51 métricas: xG, xGOT, ocasiones claras, entradas al último tercio, toques en el área, km, sprints, goalsPrevented… |
| Once confirmado y formación | 380 | 380 | 380 | 90 | titulares y suplentes |
| Métricas por jugador | ✔ | ✔ | ✔ | ✔ | 83 claves: minutos, nota (con versiones), xG, xA, pases clave, conducciones progresivas, duelos, valores normalizados de pase/regate/defensa/portero, velocidad máxima, distancias a alta intensidad |
| Bajas (`missingPlayers`) | 378 | 378 | 380 | 90 | 8.816 registros: 7.153 «missing» con código de motivo, 1.663 «doubtful» |
| Incidencias con minuto | ✔ | ✔ | ✔ | ✔ | 4.920 amarillas, 176 rojas, 100 dobles amarillas, 939 cambios por lesión, decisiones VAR (40 tarjetas mejoradas, 216 penaltis revisados) |
| Árbitro / estadio / descuento | 380 / 380 / 379 | 380 | 380 | 90 | 53 árbitros distintos |
| Entrenadores por partido | 380 | 380 | 380 | 90 | |
| Posiciones medias / momentum | 380 / 377 | 380 / 375 | 380 / 380 | 90 / 90 | descriptivos |
| Mapas de calor por jugador | **no descargados** | | | | el origen los ofrece en los 1.230 (`hasEventPlayerHeatMap`) |

**Tiempo de los datos.** Todo se observó en octubre de 2026 (`manifest.json → observation`). Para el
pasado es una reconstrucción. Consecuencias:
- Resultado, tiros, estadísticas, once real, incidencias y árbitro describen el partido: sirven como
  **historia** para estimar fuerzas, nunca como predictor de ese mismo partido.
- Las bajas se pueden usar como «sabido a T-60» marcado como reconstrucción (igual que las de FotMob).
- `h2h`, `pregame_form` y `team_streaks` **no se usan tal cual**: no se puede acreditar que sean de antes del
  partido. Se recalculan con nuestra historia.

**Árbitros: primera señal (cruda).** Media de 4,22 tarjetas por partido (varianza 4,61, algo de sobredispersión).
Entre árbitros con ≥ 40 partidos, la media cruda va de 3,02 (Zufferli) a 5,31 (Colombo). Una parte de esa
diferencia es ruido de muestra y otra depende de qué partidos se les asignan: hay que **encogerla** (modelo
jerárquico) y controlar por equipos, derbi y estado del marcador antes de usarla.

## 2. Qué hay hoy en producción para Serie A (consulta de solo lectura, 31-oct)

| Temporadas | Partidos | Goles, tiros, córners, amarillas | xG (fuente) | xGOT | Árbitro |
|---|---|---|---|---|---|
| 14/15 → 16/17 | 1.140 | 100 % | — | — | — |
| 17/18 → 20/21 | 1.520 | 100 % | 99,8 % (sin fuente acreditada) | — | — |
| 21/22 → 22/23 | 760 | 100 % | 100 % (PitchAPI) | — | — |
| 23/24 | 380 | 100 % | 100 % (FotMob) | 192 | 200 |
| 24/25 → 25/26 | 760 | 100 % | 100 % (FotMob) | 100 % | 100 % |
| 26/27 | 90 | 100 % | 100 % (API-Football / FotMob / SofaScore) | 100 % | 100 % |

Además: 1.050 originales FotMob de Serie A (enero-2024 en adelante) y 30 originales SofaScore. Al motor solo
llegan los agregados por partido de esta tabla; tiros, jugadores y bajas no llegan a ningún motor.

## 3. Comparación vieja contra nueva y respuesta: ¿se borra la vieja?

**Qué añade la nueva.** Completa 23/24 (los 188 partidos sin xGOT y 180 sin árbitro). Sobre todo, añade el nivel
de **tiro, jugador, once, bajas e incidencias con minuto**, que en producción no existe para ninguna temporada.
De 24/25 en adelante se solapa con FotMob. Probablemente ambos vienen del mismo proveedor de origen, así que
sirve para verificar, no como segunda opinión independiente.

**Pendiente:** la conciliación partido a partido (goles, xG, córners, tarjetas SofaScore contra producción) no se
hizo: la exportación por partido desde el servidor quedó bloqueada por permisos en esta sesión. Es la fase F0 de
la sección 6.

**Recomendación: no borrar la historia anterior.** Conservarla por niveles, como ya proponía el borrador del
30-oct, y que cada modelo elija con un filtro:

| Nivel | Contenido | Para qué |
|---|---|---|
| **Oro** | 23/24 → hoy, SofaScore completo (y FotMob) | fuerzas por tiros, jugadores, once, bajas, árbitros, motor C ampliado |
| **Plata** | 17/18 → 22/23, goles + xG agregado + córners + tarjetas | parámetros de liga, priors de córners/tarjetas, calibración |
| **Bronce** | 14/15 → 16/17, goles, tiros, córners, amarillas, cuotas | ventaja de local, ρ, dispersión de conteos, pruebas de estabilidad |

Motivos:
1. **No hay coste.** La fuerza de los equipos ya usa una vida media de 180 días: un partido de hace 4 años pesa
   ≈ 0,4 % de uno de hoy. «Analizar con las últimas 4 temporadas» ya ocurre en la práctica para la fuerza.
2. **Sí aporta.** La ventaja de local, la base de goles, ρ y la dispersión de córners y tarjetas son parámetros de
   liga que se estiman mejor con más partidos. 1.520 partidos por liga son pocos para calibrar mercados de
   probabilidad extrema.
3. **No se puede borrar limpiamente.** `matches` está referenciada por `odds_snapshots`, `predictions` y `picks`,
   que tienen triggers de inmutabilidad. Esos triggers no se desactivan.
4. **La ventana es un hiperparámetro.** Se prueba 4 contra 6 contra 12 temporadas en walk-forward y gana la que
   mida mejor. No se decide de antemano.

## 4. Lo que dice la literatura (verificado hoy salvo que se indique)

- **xG mejor que goles para la fuerza.** Varios trabajos coinciden en que el xG es más estable y predictivo que los
  goles. Con tres temporadas de Bundesliga (22/23–24/25), el xG previo dio RPS 0,199 y el valor de posesión
  esperado 0,194 ([Frontiers 2025, doi 10.3389/fspor.2025.1713852](https://doi.org/10.3389/fspor.2025.1713852); cifras tomadas
  del resumen, sin leer el texto completo).
  Lectura: con mapa de tiros se gana estabilidad; métricas más ricas pueden añadir algo, pero no mucho.
- **xG jerárquico bayesiano con efecto de jugador/posición** ([Scholtes-Karakuş, arXiv:2311.13707](https://arxiv.org/html/2311.13707v1);
  contrafactual, [arXiv:2511.23072](https://arxiv.org/abs/2511.23072v1); efectos mixtos interpretables,
  [Frontiers 2025](https://www.frontiersin.org/articles/10.3389/fspor.2025.1504362/full)). Ninguno predice el
  resultado del partido; esa unión es hipótesis nuestra.
- **Fuerza a partir del once (plus-minus regularizado).** RAPM con secuencias de posesión
  ([Bajons-Hornik 2024, arXiv:2407.17832](https://arxiv.org/html/2407.17832v1)). En la EURO 2020, el plus-minus de
  los titulares añadió información a un Elo de equipo ([arXiv:2106.05799](https://arxiv.org/pdf/2106.05799)).
  Gelade-Hvattum ([JSA](https://himolde.brage.unit.no/himolde-xmlui/handle/11250/3031232)) hallan que las
  estadísticas de evento explican 22–38 % del plus-minus y lo mejoran poco. Lectura: el aporte principal es
  **quién juega y cuántos minutos**, no la nota del jugador.
- **Calendario congestionado.** El metaanálisis de Sports Medicine 2020
  ([s40279-020-01359-9](https://link.springer.com/article/10.1007/s40279-020-01359-9)) no encontró efecto en la
  distancia total ni en lo técnico; la evidencia táctica es escasa. Un trabajo antiguo de LaLiga tampoco halló
  efecto de jugar Champions entre semana. Lectura: el efecto de «jugar con suplentes por la Champions» llega por la
  **rotación**, que el once captura, no por el cansancio en sí. No conviene poner un bono fijo por «Champions la
  semana que viene».
- **Árbitro y tarjetas.** Dawson et al. (JRSS-A 2007,
  [UEA](https://research-portal.uea.ac.uk/en/publications/are-football-referees-really-biased-and-inconsistent-evidence-on-))
  rechazan que los árbitros sean consistentes entre sí y hallan un sesgo de tarjetas a favor del local, con
  binomial negativa bivariante. Kruse-Maennig: árbitro, local, derbi y quién gana determinan las amarillas.
  Philipson (NESSIS 23, [pdf](https://www.nessis.org/nessis23/Pete-Philipson-approved.pdf)): Poisson
  infraestima la incertidumbre; usar binomial negativa.
- **Córners.** Poisson compuesta y geométrica-Poisson bayesiana para el número de córners, con información de
  otros mercados ([Yip et al., arXiv:2112.13001](https://arxiv.org/abs/2112.13001v3)).
- **Ya citados en el borrador del 30-oct:** Egidi-Pauli-Torelli 2018 (mercado como prior), Wheatcroft 2021 (log
  score como métrica principal), Fischer-Heuer 2024 y el Soccer Prediction Challenge (los modelos de ML no ganan
  con claridad; llevar siempre una referencia CatBoost + pi-ratings).

No encontré un estudio de 2025–2026 que demuestre una arquitectura claramente superior para 1X2 con este tipo de
datos. Lo de la sección 5 son **hipótesis a medir**, no resultados. La sección 4b, leída sobre textos completos, corrige parte de esta.

## 4b. Estudios 2025–2026 leídos completos: qué se sostiene (31-oct, segunda y tercera pasada)

La primera versión de esta sección se basaba en resúmenes. Esta se basa en **leer los textos completos** donde
se pudo. Varias conclusiones cambiaron.

**Tesis doctorales.** No encontré ninguna de 2025–2026 que prediga resultados con datos de tiros y jugadores.
La más cercana en método es la de Rutger Lit (Tinbergen 2016), base del artículo de Koopman-Lit que se resume abajo.

### Qué dicen de verdad los textos completos

| Trabajo | Leído | Lo que muestran sus tablas | Veredicto para nosotros |
|---|---|---|---|
| **Koopman-Lit, modelos *score-driven*** ([Tinbergen DP 17-062](https://papers.tinbergen.nl/17062.pdf); IJF 2019) | completo | 6 ligas **incluida Serie A**, 7 temporadas fuera de muestra (2009–16, ≈15.000 pronósticos), RPS + Diebold-Mariano (tabla abajo). Una variante *score-driven* (fuerzas actualizadas tras cada jornada) es la mejor en las 6 ligas. Frente a la ponderación temporal, la diferencia es significativa en 4 de 6; no lo es en Ligue 1 ni Eredivisie. La binomial negativa no mejoró (los goles casi no tienen sobredispersión). Estima en < 10 s, frente a 1 h del espacio de estados | **La evidencia más sólida y la más aplicable.** Nuestro motor A usa justo la variante que pierde: ponderación temporal de Dixon-Coles con vida media fija |
| Macrì-Demartino, Egidi, Torelli 2025 ([arXiv:2508.05891](https://arxiv.org/abs/2508.05891)) | completo | Preprint sin revisión. Solo goles; compara con otros dos modelos dinámicos, sin modelo estático ni *score-driven*. Mejoras pequeñas y **no uniformes**: en Bundesliga empeora el Brier en 3 de 6 distribuciones (p. ej. 0,718 frente a 0,702), aunque el texto dice «superior de forma consistente» | Bajar de prioridad. Opcional, después de Koopman-Lit |
| ~~Glicko-2 adaptativo~~ ([arXiv:2607.01722](https://arxiv.org/abs/2607.01722)) | — | **Retirado por los autores** el 27-jul-2026 («the content is not enough») | **Fuera** |
| Forcher et al. 2025, EPV frente a xG ([Frontiers](https://www.frontiersin.org/articles/10.3389/fspor.2025.1713852/full)) | completo | Bundesliga 22/23–24/25, eventos + tracking (DFL/TRACAB). Antes del partido: EPV RPS 0,194, xG 0,199, Elo 0,202. Prueba con ≈100 partidos, partición 80/20 por partido **no cronológica**, sin prueba de significancia; los propios autores señalan incoherencias de tabla | Evidencia débil. El EPV exige tracking, que no tenemos. Los valores normalizados de SofaScore quedan como experimento menor |
| Bajons-Hornik 2024, RAPM ([arXiv:2407.17832](https://arxiv.org/html/2407.17832v1)) | completo | LaLiga 17/18. La fuerza por jugadores (ridge/group lasso) gana a Elo y a la referencia: Brier 0,566–0,577 frente a 0,638 de Elo. Significativo al 5 % con logit ordenado y solo al 10 % con Poisson bivariante. Prueba de 100 partidos. La parte de «implicación» necesita la secuencia de posesión; la parte «en el campo» (±1 por jugador presente) solo necesita once y minutos | La idea vale con nuestra data, pero solo la parte «en el campo» |
| Groll, Hvattum et al. 2021, EURO ([arXiv:2106.05799](https://arxiv.org/pdf/2106.05799)) | completo (§1–5) | El plus-minus de Pantuso-Hvattum se calcula **solo con once, cambios, rojas y goles por tramo**, con regresión ridge, ajuste por edad y liga, y pesos por antigüedad, duración del tramo y marcador. Es la 4.ª variable más importante del modelo. El indicador «jugadores importantes ausentes» aportó ≈0. Las casas siguen ganando (RPS 0,203 frente a 0,210 del mejor modelo) | **Confirma A4 con exactamente los datos que tenemos.** Ojo: las bajas sumadas como conteo no aportaron |
| Yip et al., córners ([arXiv:2112.13001](https://arxiv.org/html/2112.13001v3)) | completo | 20.190 partidos (HKJC, 2016–21). Ranking: geométrica-Poisson ≈ BN con dispersión variable (diferencias dentro de 1–2 errores estándar), luego BN, y Poisson claramente peor. La covariable clave es el **total de goles esperado**: +16,7 % de córners por gol esperado. Sobredispersión 1,19. Beneficio en apuestas 3,7–5,8 % en un solo periodo de 5 meses y **negativo en Premier y Champions**. Margen de la casa 7,6 % | Motor C: BN con dispersión que depende de lo desigual del partido y los goles esperados del motor A como covariable. No esperar beneficio en ligas grandes |
| Allen et al. 2025, conformes ([arXiv:2503.03841](https://arxiv.org/abs/2503.03841v1)) | completo (texto extraído) | Simulación (Y|X ~ Gamma con incertidumbre que depende de X; n = 2.000, prueba 5.000): el LSPM cubre bien **en promedio** pero no condicionalmente (sobrecubre con poca incertidumbre y subcubre con mucha); el binning y el IDR conformal sí. Aplicaciones en estancias en UCI y temperatura europea, **ambas con resultados continuos, ningún conteo**. Garantías bajo **intercambiabilidad**, que una serie temporal de partidos no cumple del todo. Pensado para variables continuas, sin experimentos de conteo. La banda contiene una distribución calibrada, pero elegir una concreta es heurístico | Capa tardía y opcional; antes, una recalibración isotónica simple |
| xG bayesiano: contrafactual 2025 ([arXiv:2511.23072](https://arxiv.org/abs/2511.23072v1)) y efectos mixtos ([Frontiers 2025](https://www.frontiersin.org/articles/10.3389/fspor.2025.1504362/full)) | completo | El contrafactual no tiene evaluación con reglas de puntuación propias, usa una temporada y su variable más importante son los defensores en el triángulo de tiro (exige foto fija). El de efectos mixtos queda **por debajo del xG del proveedor**: AUC 0,781 frente a 0,801 de StatsBomb | **No construir xG propio.** Usar el xG/xGOT de SofaScore |
| HIGFormer ([arXiv:2507.10626](https://arxiv.org/html/2507.10626v1)), ScoutGPT ([arXiv:2603.15212](https://arxiv.org/html/2603.15212v1)) | completo | HIGFormer: eventos Wyscout con cada pase, 389 partidos de prueba, solo exactitud (52 %, empates 24,5 %), sin comparar con casas ni con Poisson. ScoutGPT: K League, no predice el resultado del partido; CatBoost lo iguala o lo supera en probabilidad de gol | **Fuera:** no aplica a nuestra data y la evaluación es débil |
| Dawson & Dobson 2008, árbitros en copas UEFA ([IASE WP 08-09](https://hcapps.holycross.edu/hcs/RePEc/spe/DawsonDobson_Referees.pdf)) | completo, con tablas (pp. 21–27) | Tablas: correlación local–visitante ρ = 0,241 (EE 0,025). Faltas propias +0,086 (local) y +0,080 (visitante), muy significativas; tiros a puerta y posesión no. Llenado del estadio +0,232 al visitante. **Pseudo-R² = 0,013**: todo junto explica muy poco de las tarjetas. Es un estudio distinto del Dawson et al. 2007 de JRSS-A (leído más abajo). Champions y Copa UEFA 2002–07, 1.720 partidos, probit ordenado bivariante sobre «puntos disciplinarios» (amarilla 1, roja 2). El local recibe menos tarjetas. Con estadio más lleno en proporción, el visitante recibe más; con pista de atletismo, el local recibe más. Las ecuaciones de local y visitante están correlacionadas (prueba LR significativa). Rojas y amarillas van juntas. **Las faltas son significativas; posesión y tiros a puerta no.** La nacionalidad del árbitro importa | Motor C: modelo bivariante (local/visitante correlacionados) con faltas esperadas y llenado del estadio. La asistencia es dato posterior; como predictor, solo la media histórica de cada estadio |
| Boshnakov, Kharrat, McHale 2017, Weibull bivariante ([preprint](https://blogs.salford.ac.uk/business-school/wp-content/uploads/sites/7/2016/09/paper.pdf); IJF) | completo | Premier 2006–16, ventanas de 4,5 temporadas, 1.140 partidos fuera de muestra. Dentro de muestra mejora el AIC (6628 frente a 6650 de Poisson independiente); la cópula aporta más que la Weibull (12–14 puntos frente a 7–8). Fuera de muestra **no da RPS ni log score**: solo curvas de calibración y rentabilidad con Kelly (1X2 +20,3 % frente a +12,2 % de Poisson). Que Poisson también «gane» +12 % sugiere que la comparación se hizo contra cuotas medias blandas, no contra el cierre afilado. Forma final c ≈ 1,05 / 0,98, es decir, casi Poisson | Baja prioridad. Nuestra corrección ρ de DC ya recoge la dependencia negativa (τ de Kendall −0,05). Probar Weibull solo como variante barata y medirla con log score |
| Ievoli, Gardini, Palazzo 2023, redes de pases ([AStA](https://link.springer.com/content/pdf/10.1007/s10182-021-00411-x.pdf)) | completo | **No es un modelo anidado tiros → a puerta → goles ni trata props de jugador.** Champions 2016–17: 125 partidos, entrena con 96 y prueba con 29. Explica goles con estadísticas **del mismo partido**: tiros a puerta (β 0,304), córners (negativo), intensidad de pases. Es explicativo, no un pronóstico previo. CC_out 0,79 sobre 29 partidos | No sirve tal cual como predictor previo. En la conclusión (p. 173) los autores proponen el paso que sí podemos dar: usar **resúmenes de partidos anteriores** (medias o medianas de cada covariable) en ligas nacionales para pronosticar sin datos del propio partido. Con SofaScore eso significa medias recientes de tiros a puerta, posesión y córners, encogidas y calculadas solo con partidos previos. También respalda usar los tiros a puerta como exposición (*offset*), que dejan como trabajo futuro. No hay redes de pases en SofaScore (solo totales de pases), y los tiros anidados siguen siendo hipótesis nuestra |
| Deb & Das 2023, once óptimo ([arXiv:2303.12385](https://arxiv.org/pdf/2303.12385.pdf)) | completo | **No trata actualización en vivo ni momentum.** Premier 2008–16, 10 equipos, atributos del videojuego FIFA (Kaggle). Logit multinomial con LASSO **por equipo**: 600 efectos fijos de jugador y 2.171 de parejas sobre ≈270 partidos por equipo. La comparación predictiva está solo en el suplemento | Riesgo alto de sobreajuste. No usar efectos de parejas. Confirma que el once importa, pero el método útil es el plus-minus regularizado |
| Page, Field, Langley, Harper, Julian 2023, congestión y lesiones ([Sports Med 53:667](https://link.springer.com/content/pdf/10.1007/s40279-022-01799-5.pdf)) | completo (§1–3 y tabla de estudios) | Revisión sistemática **sin metaanálisis**: 8 estudios, la mayoría de un solo club francés. En 5 de 8, la congestión (≤ 4 días entre partidos) sube la incidencia de lesiones en partido, aunque las bajas resultantes son más cortas. El mayor estudio (Bengtsson, UEFA Elite Club Injury Study, 2.672 jugadores y 68.477 observaciones) mide la carga como **horas de partido en los 30 días previos**: baja ≤ 4,5 h, media 4,5–7,5 h, alta > 7,5 h. **No mide resultados de equipo** | Respalda modelar la congestión **por jugador** (riesgo de baja y de rotación), no como bono de equipo. La carga de 30 días se calcula con los minutos de SofaScore |
| Dawson, Dobson, Goddard, Wilson 2007, árbitros en Premier ([JRSS-A 170:231](http://www2.stat-athens.aueb.gr/~jpan/Dawson-RSS(A)2007(231-250).pdf)) | completo | Premier 1996–2003, 2.660 partidos. Puntos disciplinarios (amarilla 1, roja 2): media 1,47 local y 2,05 visitante. Con covariables gana la **Poisson bivariante con cópula de Frank e inflación de ceros**; la binomial negativa deja de hacer falta porque las covariables explican la sobredispersión. Correlación local–visitante de 0,28. La igualdad del partido q(1−q) sube las tarjetas de ambos: +5,02 local y +3,02 visitante. Los árbitros **difieren de forma significativa** (χ²(56) = 171,3): de 2,53 a 4,54 puntos por partido entre 28 árbitros con ≥ 30 partidos. El sesgo al local no se explica por la ventaja de local (−0,29 puntos con partido igualado). El entrenador como efecto fijo también es significativo. Un cambio de reglamento movió la media una temporada | **Especificación concreta para tarjetas (motor C):** Poisson bivariante con dependencia y covariables. Lleva (1) probabilidad de victoria del motor A y su término cuadrático de igualdad, (2) efecto de árbitro encogido (nuestros 53 árbitros), (3) entrenador, (4) temporada, (5) partido con algo en juego. La binomial negativa solo si las covariables no bastan |
| Julian, Page, Harper 2021, congestión y rendimiento ([Sports Med 51:255](https://link.springer.com/content/pdf/10.1007/s40279-020-01359-9.pdf)) | completo (métodos, resultados, discusión) | 527 registros → 16 artículos, 5 en el metaanálisis (836 observaciones de jugador en congestión y 820 sin ella; 10.565 ± 991 m frente a 10.475 ± 880 m). Al corregir un estudio faltante (*trim and fill*) sale significativo (p = 0,045) pero trivial (SMD 0,16; IC 0,00–0,32). Metaanálisis de 5 de 16 estudios: **la congestión no cambia la distancia total** (Hedges G 0,12; IC −0,04 a 0,28; p = 0,134). Lo técnico no cambia y lo táctico solo tiene 1 estudio. En un club de Ligue 1, solo el 25–40 % de los jugadores juega todos los partidos de una semana con 2–3 partidos | Confirma lo anterior: **no hay término de «cansancio» para el equipo**. Lo que cambia es **quién juega** (rotación), y eso entra por A4/A5 |
| Constantinou & Fenton 2013, pi-ratings ([JQAS 9:37](http://www.constantinou.info/downloads/papers/pi-ratings.pdf)) | completo | Ratings de local y visitante por equipo, actualizados con el error de diferencia de goles: ψ(e) = 3·log₁₀(1+e), λ = 0,035 (aprendizaje), γ = 0,7 (traspaso local↔visitante). Diferencia esperada = 10^(\|R\|/3) − 1. Premier 2007–12: ganan a dos Elo y obtienen +£57,62 en 1.887 apuestas (+3 %) contra la mejor cuota de Betbrain, con 2 de 5 temporadas en pérdida. **Sin log score ni RPS**; la probabilidad sale de agrupar diferencias de rating | **Referencia de comparación lista para programar** con fórmulas exactas. Se calcula con goles **o con xG** de SofaScore, que es una variante nueva y barata. Entra al banco de pruebas como referencia (pi-ratings + CatBoost) |
| Constantinou 2019, Dolores ([Mach Learn 108:49](https://link.springer.com/content/pdf/10.1007/s10994-018-5703-7.pdf)) | completo (texto extraído) | Extiende los pi-ratings con una capa de «forma» (umbral, impacto y decaimiento). Tasas óptimas λ = 0,054 y γ = 0,79: RPS 0,211208 sin forma y 0,211198 con ella, o sea la forma mejora **0,00001**. RPS del concurso 0,208256 frente a 0,206307 del ganador; Serie A 0,200186 (7.º de 52, dentro de muestra). 216.743 partidos de 52 ligas, **solo goles**. Pi-ratings + red bayesiana híbrida. 2.º en el desafío (206 partidos de prueba; error 0,94 % mayor que el ganador). Rentabilidad en 21 ligas y 7 temporadas: **+1,09 % en primeras divisiones y −1,57 % en segundas**. En Premier +20 %, pero sin repetirse en ninguna otra liga: **Serie A −9 %**. El autor advierte que los estudios que solo miran la Premier engañan | Confirma la regla de evaluar con varias ligas y temporadas antes de activar nada (fase F6). El propio autor dice que faltan jugadores, bajas, entrenador y competiciones europeas, justo lo que trae SofaScore |
| Constantinou, Fenton, Neil 2012, pi-football ([KBS 36:322](http://constantinou.info/downloads/papers/pi-model11.pdf)) | leído hasta el inicio de la conclusión (pp. 1–17); sin leer el resto de la conclusión ni los apéndices | Priors con 6.244 partidos de Premier 1993/94–2009/10 y **equipos anónimos** (14 niveles de puntos de temporada). Cuatro componentes: fuerza, forma, psicología y **fatiga** (dureza del partido anterior, días de descanso, titulares descansados, partidos con selección). Las componentes 2–4 son juicio experto. Premier 2010/11, 380 partidos: el pronóstico objetivo es **peor que las casas** (p = 0,0023) y con lo subjetivo queda a la par (p = 0,1319). Apuestas con discrepancia ≥ 5 %: +8,40 % (169 apuestas) contra la mejor cuota, +2,87 % (109) contra la media y +9,48 % (123) contra William Hill; sin lo subjetivo, −13,98 %, −19,92 % y −12,84 %. La fatiga fue la componente con mayor aporte aislado (+£15,25), con muestras de 13 a 79 casos y los autores advierten que es peligroso concluir por componente | Sus entradas subjetivas (opinión experta) no son reproducibles ni acreditables en el tiempo. Lo aprovechable es la **publicación previa sellada**, que ya hacemos con la cadena de hashes |
| Kruse & Maennig 2019, amarillas y suspensión buscada ([HCED 64](https://www.hced.uni-hamburg.de/WorkingPapers/HCED-064.pdf)) | completo (pp. 1–18) | Bundesliga 2013/14–2017/18: 3.060 observaciones equipo-partido, 33 árbitros, MCO con efectos aleatorios. Amarillas por equipo: local −0,26, derbi +0,20, media de 3 años del árbitro +0,16 por cada tarjeta de su media (mejor que la media de la temporada o que una variable 0/1), rival ligeramente mejor en puntos (≤ 5) +0,12; la posición en la tabla no es significativa. «Ganar» resta 0,14, pero **es el resultado del propio partido**: una fuga si se usara para pronosticar. **5.ª amarilla:** el árbitro no influye; la probabilidad sube con las amarillas del partido, con la jornada y cuando **el siguiente rival es mejor** (equipos de arriba OR 1,17 por puesto; los de abajo 1,03 por puesto y, además, miran el rival de después) | **Tarjetas:** media del árbitro sobre 3 años encogida, derbi (falta una tabla de derbis de Serie A), local y la **probabilidad previa de victoria** del motor A en lugar de «ganar». **Nuevo cálculo para A5 (rotación):** con las incidencias de SofaScore se cuentan las amarillas acumuladas por jugador; un jugador a una del umbral de sanción de la liga (por verificar en el reglamento de Serie A) tiene más riesgo de ser baja en el partido siguiente, sobre todo antes de jugar contra un rival mejor |
| Tesis doctoral de Rutger Lit (VU/Tinbergen 2016, «Time-Varying Parameter Models for Discrete Valued Time Series») | sin PDF localizado | Registrada en el portal de la VU; no encontré enlace público | **No hace falta:** sus capítulos de fútbol son Koopman-Lit 2015 (JRSS-A) y el DP 17-062, que ya está leído completo |

**Koopman-Lit, RPS medio fuera de muestra** (2009–16; menor es mejor; DM > 1,96 = significativamente peor que
el mejor modelo de su liga):

| Liga | Estático | Ponderado en el tiempo (como nuestro DC) | *Score-driven* (mejor) |
|---|---|---|---|
| **Serie A** | 0,2042 | 0,2025 (DM 2,78) | **0,2005** |
| Premier | 0,2062 | 0,2014 (DM 4,15) | 0,1981 |
| Bundesliga | 0,2165 | 0,2127 (DM 3,35) | 0,2089 |
| LaLiga | 0,1980 | 0,1942 (DM 4,28) | 0,1915 |
| Ligue 1 | 0,2109 | 0,2070 (DM 1,28) | 0,2059 |
| Eredivisie | 0,1974 | 0,1939 (DM 0,58) | 0,1934 |

En Serie A, pasar de la ponderación temporal a la actualización *score-driven* bajó el RPS en 0,002. (Corrección tras
verificar el texto: la mejor variante en Serie A es la **Skellam dinámica sobre la diferencia de goles**, 0,2005; la
Poisson bivariante dinámica da 0,2019 y el probit ordenado de espacio de estados 0,2007.) Es del mismo
orden que la distancia que separa hoy a nuestro motor A del mercado (0,1991 frente a 0,1935, sección 3.3 de
`MOTOR_Y_PICKS_AL_DETALLE`). No la cierra sola, pero es la mejora individual mejor documentada que encontré. Salvedad:
se midió con goles de 2009–16; nuestro DC ya mezcla xG, y eso puede reducir la ganancia.

### Cuarta pasada: siete textos más, cruzados con la data que tenemos

| Trabajo | Leído | Lo que muestran | Con nuestra data (SofaScore + producción + PropLine) |
|---|---|---|---|
| Decroos et al., VAEP (KDD 2019, [arXiv:1802.07127](https://arxiv.org/pdf/1802.07127.pdf)) | completo | Valora **cada acción con balón** (unas 1.250 por partido: pases, regates, despejes…) por cuánto cambia la probabilidad de marcar o encajar en las 10 acciones siguientes. Usa Wyscout, 11.565 partidos y CatBoost (Brier 0,0138 / AUC 0,769 al marcar). Salida: valoración de jugadores por 90 min. **No trata apuestas ni props** | **No se puede calcular:** SofaScore solo da los tiros con coordenadas, no la secuencia de acciones. Lo más cercano son `passValueNormalized`, `dribbleValueNormalized` y `defensiveValueNormalized` por jugador, propietarios y sin documentar. Pueden entrar como **prior débil** de la fuerza del jugador (A4), no como VAEP |
| Kaunitz, Zhong, Kreiner 2017, «Beating the bookies» ([arXiv:1710.02824](https://arxiv.org/pdf/1710.02824.pdf)) | completo | Cierres de 32 casas, 479.440 partidos (2005–15). El **consenso de casas está casi perfectamente calibrado**: pendientes 1,003 / 1,081 / 1,012 e interceptos −0,034 / −0,057 / −0,037 (el margen). Apostando cuando la mejor cuota supera 1/(p_consenso − 0,05): +3,5 % con cierres (56.435 apuestas) y +9,9 % con cuotas de 1–5 h antes (6.994). Con dinero real, +6,2 % en 672 apuestas, **p = 0,089 (no significativo)**. El 30 % de las cuotas ya había cambiado al ir a apostar, y las casas **limitaron las cuentas** a los pocos meses | El «modelo» es el mercado. PropLine trae varias casas por mercado, así que el **consenso sin margen** de PropLine es la referencia a batir en calibración, también en córners y tarjetas. Lo que gana dinero ahí es comparar casas, no predecir mejor, y no es la meta del 30-oct |
| ~~Constantinou, pi-football~~ ([arXiv:1809.04369](https://arxiv.org/pdf/1809.04369.pdf)) | — | **El enlace está mal:** ese arXiv es «Thick points of random walk and the Gaussian free field» (Jego, matemática pura), no Constantinou. El pi-football real (Constantinou, Fenton, Neil 2012, [core.ac.uk](https://core.ac.uk/download/77039393.pdf)) y Dolores se leyeron después con los enlaces del titular: ver las filas de pi-ratings, Dolores y pi-football en la tercera pasada | Lo verificable: Dolores (pi-ratings + red bayesiana, **solo resultados de 52 ligas**) quedó 2.º en el desafío de Machine Learning, y el ganador también usaba pi-ratings. Encaja con la referencia CatBoost + pi-ratings que ya teníamos. Ninguno usa tiros ni jugadores |
| Dixon & Coles 1997 ([enlace math.ku.dk](http://www.math.ku.dk/~rolf/teaching/thesis/DixonColes.pdf)) | **no accesible** | ku.dk rechaza la conexión, Wiley da 403 y el repositorio de Lancaster no tiene el texto. El enlace de Scribd (17 páginas) solo entrega portada y descripción sin el texto del documento: hay que descargarlo con sesión iniciada | Es lo que ya corre: el motor A **es** Dixon-Coles (`model/dixon_coles.py`, ρ = −0,0613, vida media de 180 días). Su ponderación temporal fija es justo lo que Koopman-Lit superan en Serie A (tabla de arriba) |
| Halawi et al. 2024, LLM que pronostica ([arXiv:2402.18563](https://arxiv.org/abs/2402.18563)) | completo | Recuperación de noticias + GPT-4 afinado: Brier 0,179 frente a 0,149 de la multitud; **en deportes, 0,175 frente a 0,171 (peor)**. Solo gana cuando la multitud duda (0,238 frente a 0,240), y la media sistema+multitud es lo mejor (0,146). Tiende a probabilidades moderadas y falla en lo seguro | No como predictor. Como mucho, como **lector de noticias** para A5 (bajas y rotaciones anunciadas antes del once), con hora de recepción registrada. Su lección de fuga temporal (preguntas posteriores al corte del modelo) es la misma que nuestro sellado |
| Reevaluación con control de fugas, baloncesto juvenil ([Frontiers in Physiology 2026](https://www.frontiersin.org/journals/physiology/articles/10.3389/fphys.2026.1912035/full)) | completo | Dataset de Kaggle con 1.000 filas de origen no verificable. Los modelos «perfectos» (AUC 1,000) eran **fuga por construcción del objetivo**: la etiqueta se calculaba con las propias variables de entrada. Sin ellas, AUC 0,622 y sensibilidad al riesgo alto 0 | **Aplica directo a SofaScore.** Variables «construidas» con el mismo partido o con información posterior: `pregame_form`, `h2h` y `team_streaks` (descargados en oct-2026); la **nota** del jugador y los valores normalizados (calculados con el partido); las estadísticas del partido como explicación (el error de Ievoli). Regla: auditar cómo se construye cada variable antes de usarla, reservar un periodo bloqueado y medir la calibración aparte |
| Galekwa et al. 2024, revisión sistemática ([arXiv:2410.21484](https://arxiv.org/abs/2410.21484)) | texto completo extraído, consultado por secciones (3, 4.1 y 8) | Revisión **cualitativa** de 219 estudios. Su cifra «69,86 % más de rendimiento» para calibración frente a acierto es en realidad una **diferencia de puntos porcentuales** (34,69 − (−35,17))., sin metaanálisis. Reproduce sin crítica exactitudes de hasta el 99 %. La «regla de calibración» **no es suya**: cita a Walsh & Joshi (2024, [arXiv:2303.06021](https://arxiv.org/abs/2303.06021)), que en **NBA** eligen modelos por calibración en vez de exactitud: +34,69 % frente a −35,17 % de rendimiento medio en una temporada. Leído completo: entrenan con 2014/15–2017/18, apuestan solo en 2018/19 con cierres de una casa (Westgate) y comparan **un único modelo final por rama** (SVM con ECE por clase de 3,23 % frente a SVM con 66,55 % de acierto). Con apuesta fija, +32,45 % frente a +5,56 %. Es una sola temporada sin prueba de significancia (hay corrigendum de mar-2025 sin revisar). **Versión de la revista (main.pdf, MLwA 16:100539):** los «promedios» +34,69 % y −35,17 % son la media de **solo dos simulaciones** (apuesta fija: +32,45 % frente a +5,56 %; octavo de Kelly: +36,93 % frente a −75,9 %). Ambos SVM apostaron en 87,55 % y 89,89 % de los partidos con acierto 64,27 % y 64,62 %, y acertaron casi las mismas apuestas en la segunda mitad de la temporada; la diferencia se decidió en la primera mitad. Es un único SVM por rama. Lo de simular goles y córners y compararlo con la cuota tampoco aparece en el texto leído | La idea de fondo (elegir por calibración) ya es nuestro criterio: log score como métrica principal y calibración aparte. Lo que pide el titular se formula abajo con nuestra data |

### Quinta pasada: cinco textos de cuotas, ML híbrido, Kelly y calibración (31-oct, con prueba en Serie A)

Textos leídos con extracción de texto. Lo que dicen las tablas difiere en dos casos de la descripción que acompañaba al enlace.

| Texto | Qué demuestra de verdad | ¿Se integra con nuestra data? |
|---|---|---|
| Štrumbelj, «On determining probability forecasts from betting odds» (IJF 2014; el PDF local y el de Scribd son el mismo) | **No es una demostración analítica del sesgo favorito–longshot** (esa expresión solo aparece en la bibliografía): es una comparación empírica de cuatro métodos con 48.126 partidos de 5 deportes, 4 temporadas (2008/09–2011/12) y 12 casas más Betfair. Shin tiene el mejor RPS en todos los deportes salvo la mediana del hockey. **En fútbol, 162 pares casa-liga: Shin 0,2014 frente a 0,2016 de la normalización simple, una diferencia de 0,0002**, significativa por Friedman/Nemenyi pero minúscula. La regresión es peor que ambas. La mejora de Shin viene de la **resolución**; en fútbol su fiabilidad no es la mejor, y el autor admite que no sabe si Shin describe cómo las casas fijan los márgenes. Cambia la comparación entre casas y Betfair: con Shin, Betfair deja de ser significativamente la mejor | **Ya está integrado:** `model/devig.py` implementa Shin, multiplicativo, aditivo y potencia, con Shin por defecto. No hay nada que construir. La data de SofaScore **no trae cuotas**, así que la prueba con cuotas debe hacerse con PropLine/Pinnacle |
| Groll, Ley, Schauberger, Van Eetvelde 2018, [arXiv:1806.03208](https://arxiv.org/pdf/1806.03208) | **Selecciones nacionales**, Mundiales 2002–14, 250 partidos con cuotas. Un bosque aleatorio con las habilidades de un ranking Poisson bivariante (vida media óptima de 3 años: RPS 0,17366) añadidas como covariable baja su RPS de 0,192 a 0,187 (casas 0,190). **El ranking solo ya tenía 0,188**: el bosque híbrido mejora al ranking en 0,001, sin prueba de significancia. No predice α y β del modelo: usa las habilidades como entrada | Es la idea que ya tenía `model/residual.py` (apagado). La data nueva ofrece muchas covariables por partido (xG, tiros, once), pero **la ganancia publicada sobre el ranking es mínima**. Prioridad baja, tras A0/A4. Falta además scikit-learn en este entorno |
| Chu, Wu, Swartz, «Modified Kelly Criteria» ([SFU](https://www.sfu.ca/~tswartz/papers/kelly.pdf)) | **No usa la varianza del modelo.** Supone un sistema con x aciertos en n apuestas históricas y una prior Beta(a, b): la probabilidad se sustituye por la media posterior p̂ = (x+a)/(n+a+b) y se aplica el Kelly clásico, f = (p̂·o − 1)/(o − 1) si p̂ > 1/o. Ejemplos: con 100 aciertos de 180 a cuota 1,909 y a = b = 50, Kelly pasa de 0,067 a 0,025; con a = b = 100, a 0,005. Con funciones de pérdida alternativas la fracción cambia mucho (de 0,018 a 0,039). Las fracciones son siempre menores que el Kelly original | **Poco aplicable ahora:** los picks de valor están apagados y el producto publica probabilidades, no apuestas. Si se reactivan, `uncertainty.py` ya mide el edge con la incertidumbre de los parámetros (suelo = media − Z·desviación) y `picks.kelly` usa una fracción fija, que es la misma idea con otra mecánica. Se podría añadir una prior Beta sobre la tasa de acierto de cada familia de mercado |
| Pohle 2020, «The Murphy decomposition and the calibration-resolution principle» ([arXiv:2005.01835](https://arxiv.org/pdf/2005.01835)) | Teoría general: **pérdida esperada = incertidumbre + descalibración − resolución**, para cualquier regla de puntuación consistente (Brier, log, pinball…), con recalibración isotónica. Sus aplicaciones son macroeconómicas (PIB, inflación); **no trata apuestas**. La idea de que un pronóstico calibrado pero sin resolución no sirve es su «principio calibración-resolución» | **Sí, y es barato.** Hoy `eval/metrics.py` tiene Brier, RPS, curva de fiabilidad y ECE, pero **no descomposición**. Funciona con las 4 temporadas (ver la prueba de abajo) |

#### Prueba hecha: descomposición de Murphy sobre Serie A

Script `prueba_integracion.py` (en la carpeta temporal de la sesión, solo lectura). Ajusta un Poisson de ataque y defensa con vida media de 180 días y ridge, **refitando cada 10 partidos con solo el pasado**. 23/24 es calentamiento y se evalúan 850 partidos (24/25, 25/26 y 90 de 26/27). Se comparan goles frente a la mezcla 65 % xG + 35 % goles que usa hoy el motor A. UNC/MCB/DSC calculados con PAV sobre los propios datos (algo optimista con 850 puntos).

| Modelo | RPS 1X2 | Log loss | Local: MCB / DSC | Más de 2,5: MCB / DSC | Ambos marcan: MCB / DSC |
|---|---|---|---|---|---|
| Climatología | 0,2333 | 1,0907 | — | — | — |
| Goles | **0,1968** | 0,9817 | 0,0043 / 0,0395 | 0,0080 / **0,0030** | 0,0058 / **0,0033** |
| xG 65 % + goles | 0,1969 | 0,9831 | 0,0087 / 0,0439 | 0,0055 / 0,0051 | 0,0052 / 0,0048 |

- **El arnés funciona con la data nueva:** los 1.230 partidos, goles y xG se cargaron sin huecos y el RPS (0,1968) cae en el rango del motor A en producción (0,1991).
- **La mezcla con xG no mejora aquí:** ΔRPS = +0,00009 (IC95 [−0,0023, +0,0026]) y Δlog loss = +0,0014 (IC95 [−0,0060, +0,0091]), con bootstrap por bloques de 10 partidos. Con 850 partidos no se distingue de cero. Es una advertencia contra asumir que «más xG» ya mejora el modelo; hay que medirlo con las 7 ligas.
- **Más de 2,5 y ambos marcan casi no tienen resolución:** DSC de 0,003–0,005 sobre una incertidumbre de 0,25 (1–2 %). Con este modelo esas probabilidades son prácticamente climatología, aunque estén calibradas. Es justo lo que Pohle describe y que ECE y Brier no muestran: **calibrado no equivale a informativo**. Para estos mercados hace falta más información (tiros, once, árbitro), no más recalibración.
- El 1X2 sí discrimina: DSC 0,040–0,044 sobre 0,240 (16–18 %).
- Calibración del conteo: goles totales observados 2,564 frente a 2,532 esperados.

#### Prueba con las cuotas del servidor (31-oct, solo lectura)

Cierres 1X2 de Serie A exportados de `odds_snapshots` (fuente `football_data`, `mins_to_kickoff = 0`): 1.190 partidos, todos emparejados con SofaScore por equipos, marcador y hora (25 de 25 equipos mapeados). Pinnacle 958 partidos (sobreronda media 2,95 %), bet365 232 (5,68 %). Mismo modelo walk-forward de arriba, **sin calibrador ni corrección ρ**; se evalúan 578 partidos con Pinnacle (24/25 y primera parte de 25/26) y 232 con bet365 (resto de 25/26 y 26/27). Intervalos por bootstrap en bloques de 10 partidos.

**1. Shin frente a otros métodos de quitar el margen (958 partidos Pinnacle)**

| Método | RPS | Log loss |
|---|---|---|
| Multiplicativo (simple) | 0,18602 | 0,96446 |
| **Shin** | 0,18583 | 0,96369 |
| Potencia | 0,18579 | 0,96377 |
| Aditivo | 0,18577 | 0,96343 |

- Simple − Shin: ΔRPS +0,00019 (IC95 [−0,00000, +0,00037]) y Δlog loss +0,00077 ([+0,00003, +0,00148]): Shin es algo mejor, **en la cuarta cifra decimal**, lo mismo que midió Štrumbelj en 162 pares casa-liga (0,0002).
- Potencia y aditivo empatan con Shin (ΔRPS −0,00004 y −0,00006, con intervalos que incluyen cero). **No hay base para cambiar el método por defecto del repo.**
- Shin mueve la probabilidad hacia el favorito en +0,0043 y la baja en −0,0028 en el resultado menos probable: es el ajuste favorito–longshot, de tamaño pequeño en 1X2.
- Con bet365 (232 partidos) el orden es el mismo con diferencias aún menores y sin significancia.
- La diferencia entre métodos es unas **40 veces menor** que la que separa al modelo del mercado (abajo).

**2. Modelo frente a mercado (Pinnacle, 578 partidos)**

| Fuente | RPS | Log loss | Local MCB / DSC | Empate MCB / DSC | Visita MCB / DSC |
|---|---|---|---|---|---|
| Climatología | 0,2290 | 1,0940 | — | — | — |
| Modelo goles | 0,1962 | 0,9968 | 0,0057 / 0,0361 | 0,0050 / 0,0061 | 0,0075 / 0,0406 |
| Modelo xG 65 % | 0,1942 | 0,9927 | 0,0109 / 0,0436 | 0,0038 / 0,0048 | 0,0141 / 0,0490 |
| **Mercado Pinnacle (Shin)** | **0,1871** | **0,9640** | 0,0074 / 0,0462 | 0,0049 / 0,0084 | 0,0076 / 0,0505 |

- **El mercado gana con claridad:** goles − mercado, ΔRPS +0,0091 (IC95 [+0,0043, +0,0139]); xG65 − mercado, ΔRPS +0,0071 ([+0,0032, +0,0111]). El log loss confirma (+0,033 y +0,029).
- **Mezcla log-lineal con el mercado:** el log loss **solo empeora** al darle peso al modelo (w = 0,1: 0,9652; w = 0,5: 0,9745; w = 1: 0,9968). Coincide con `w_model ≈ 0,0001` medido en producción.
- **Resolución (DSC):** el modelo xG alcanza casi la del mercado en local (0,0436 frente a 0,0462) y visita (0,0490 frente a 0,0505); el de goles queda más lejos. **La descalibración (MCB) del modelo xG es mayor** (0,0109 y 0,0141 frente a 0,0074 y 0,0076). Lectura: en este ensayo una parte de la distancia al mercado parece ser **calibración** y no información, y mi modelo no lleva el calibrador afín del motor A. Es una hipótesis a comprobar, no un resultado.
- **El empate no tiene resolución en ninguna fuente:** DSC de 0,005–0,008 sobre una incertidumbre de 0,205 (2–4 %), también en el mercado. Ningún modelo de goles va a «predecir empates».
- **Con bet365 (232 partidos)** el modelo de goles queda cerca del mercado: ΔRPS +0,0028 (IC95 [−0,0037, +0,0098]) y una mezcla con w = 0,2 baja el log loss de 0,9500 a 0,9493. Es una diferencia de milésimas con 232 partidos, no una señal. Esa casa tiene un margen de 5,7 %, casi el doble que Pinnacle.
- **xG frente a goles es inconsistente entre muestras:** en los 578 partidos de Pinnacle el xG baja el RPS en 0,0020; en los 850 de la prueba anterior no cambia; en los 232 de bet365 lo empeora en 0,0045. No hay evidencia de que la mezcla con xG ayude con esta data.

**Límites:** la recalibración PAV con 578 puntos es optimista (afecta igual a todas las fuentes, así que la comparación entre ellas sí es válida); es una sola liga; el modelo es el más simple posible; los cierres de bet365 y Pinnacle no son comparables entre sí; las cuotas de totales y de córners/tarjetas no se pudieron usar (no hay histórico).

#### Repetición con el calibrador y la corrección ρ del motor A (31-oct)

Se añadieron al modelo de prueba la corrección τ de Dixon-Coles con ρ = −0,0613 y un calibrador afín en log-λ de cuatro parámetros (`model/calibration.py`), **ajustado en cada paso solo con predicciones fuera de muestra anteriores** (historia desde el partido 150; sin fugas). Variantes: goles y xG 65 %, cada una cruda, con ρ y con ρ + calibrador. Total de comparaciones: 12 frente al mercado y 10 pareadas entre variantes, así que los intervalos del 95 % no se pueden leer sueltos.

| Pinnacle, 578 partidos | RPS | Log loss | Local MCB / DSC | Visita MCB / DSC | ΔRPS frente al mercado (IC95) |
|---|---|---|---|---|---|
| Goles | 0,1962 | 0,9968 | 0,0057 / 0,0361 | 0,0075 / 0,0406 | +0,0091 [+0,0043, +0,0139] |
| Goles + ρ | 0,1960 | 0,9940 | 0,0054 / 0,0361 | 0,0076 / 0,0409 | +0,0089 [+0,0041, +0,0135] |
| Goles + ρ + calibrador | 0,1967 | 0,9948 | 0,0057 / 0,0356 | 0,0077 / 0,0402 | +0,0096 [+0,0045, +0,0148] |
| xG 65 % | 0,1942 | 0,9927 | 0,0109 / 0,0436 | 0,0141 / 0,0490 | +0,0071 [+0,0030, +0,0112] |
| xG 65 % + ρ | 0,1940 | 0,9898 | 0,0105 / 0,0435 | 0,0140 / 0,0490 | +0,0069 [+0,0027, +0,0109] |
| **xG 65 % + ρ + calibrador** | **0,1918** | **0,9802** | 0,0084 / 0,0426 | **0,0077** / 0,0458 | **+0,0047 [+0,0008, +0,0089]** |
| Mercado Shin | 0,1871 | 0,9640 | 0,0074 / 0,0462 | 0,0076 / 0,0505 | — |

- **La hipótesis se cumple a medias.** El calibrador baja la descalibración del modelo xG en visita (MCB 0,0141 → 0,0077, igual que el mercado) y en local (0,0109 → 0,0084), y recorta la distancia con el mercado de +0,0071 a +0,0047 de RPS. Pero esa mejora, comparada de forma pareada con xG sin calibrar, **no es significativa** (ΔRPS −0,0024, IC95 [−0,0051, +0,0005]), y con goles el calibrador no aporta nada. **El mercado sigue siendo mejor** (el intervalo no incluye cero).
- **xG con calibrador mejora a goles con calibrador:** ΔRPS −0,0049 (IC95 [−0,0075, −0,0022]) y Δlog loss −0,0145 (IC95 [−0,0235, −0,0058]) en la muestra de Pinnacle.
- **Mezcla con el mercado:** el mejor peso del modelo sigue siendo **≈ 0** (xG + calibrador: w = 0 da 0,9640 y w = 0,1 da 0,9639; con goles solo empeora). El modelo no aporta información que el mercado no tenga.
- **ρ:** baja el log loss en unos 0,003 (IC95 [−0,0059, +0,0004]), un efecto pequeño y al límite de la significancia.
- **El calibrador sube la confianza en vez de bajarla:** a₁ ≈ 1,14 (goles) y ≈ 1,36–1,77 (xG), frente a 0,88 del artefacto de producción. Mi modelo regulariza demasiado (ridge 2,0), y el calibrador compensa esa compresión. **No es un resultado trasladable al motor A**, que ya tiene su propia regularización; sí indica que en el diseño nuevo el grado de regularización y la calibración hay que ajustarlos juntos.
- **La muestra de bet365 (232 partidos) no confirma nada:** el calibrador no mejora (ΔRPS −0,0004 pareado, IC95 [−0,0047, +0,0038]), xG sin calibrar es peor que goles (ΔRPS +0,0045, IC95 [+0,0004, +0,0085]) y ρ empeora el log loss en 0,003. Los signos se invierten respecto a Pinnacle. Como Pinnacle cubre 24/25 y la primera mitad de 25/26 y bet365 la segunda mitad de 25/26 y 26/27, **no se puede separar el efecto de la casa del del periodo**.
- **Conclusión:** con esta data, el modelo se acerca al mercado en la mejor variante (xG + ρ + calibrador, +0,0047 de RPS) pero no lo alcanza ni le añade información, y la ventaja del xG sobre los goles depende del periodo. Por la regla del borrador del 30-oct, un componente entra solo si mejora sobre las mismas filas **en varias ligas y periodos**: ninguna de estas variantes lo demuestra todavía.

#### Qué entra al plan
1. **Añadir la descomposición de Murphy a `eval/metrics.py`** (UNC, MCB, DSC por PAV, con CORP ya citado en el borrador del 30-oct) y reportarla por familia de mercado y por liga. Criterio nuevo: una variante solo avanza si sube la **resolución** sin empeorar la descalibración, medida frente al mercado en los mismos partidos.
2. Para Shin: **ya medido** con las cuotas del servidor (arriba); no cambia nada. Siguiente paso con cuotas: añadir el **calibrador del motor A** al modelo de prueba y repetir la comparación de MCB/DSC contra Pinnacle, para saber cuánto de la distancia al mercado es calibración.
3. ML híbrido y Kelly modificado: quedan como ideas de baja prioridad.

### La regla de calibración aplicada a nuestra data

Lo que se pide: no predecir «quién gana», sino cuántos goles, córners o tarjetas debieron ocurrir según la
simulación, y compararlo con la cuota. Con lo que tenemos:

1. **Simular la distribución completa de cada partido**, no un ganador:
   - goles con la matriz de marcadores del motor A (A0 *score-driven* + A4 del once);
   - córners y tarjetas con el motor C (BN con goles esperados; tarjetas bivariantes con árbitro y faltas);
   - por mitad, porque las estadísticas 1T/2T están al 100 %.
   - Salida por partido: media esperada y P(más de la línea) para cada línea publicada.
2. **Elegir modelos y variantes por calibración, no por acierto:**
   - log score como métrica principal;
   - diagrama de fiabilidad (CORP) por familia de mercado;
   - para conteos, el histograma PIT: si sale plano, la dispersión está bien.
3. **Comparar con la cuota en el mismo instante** como diagnóstico. Δ = p_modelo − p_consenso sin margen
   (Shin para 1X2, multiplicativo para totales, como hacen Yip y Kaunitz).
4. **Medir si Δ tiene información**, agrupando por partido:
   - ¿el resultado se acerca más a p_modelo que a p_consenso cuando |Δ| es grande?
   - ¿la línea de cierre de PropLine se mueve hacia el modelo (CLV)?

**Qué cuotas hay para hacerlo:**

| Mercado | Histórico (backtest) | Hacia delante |
|---|---|---|
| 1X2 y goles 2,5 | Cierre Pinnacle en producción desde 2014 (football-data) | PropLine cada hora desde el 23-oct |
| Córners, tarjetas, por mitad, por equipo | **No tenemos histórico** | Solo PropLine desde el 23-oct (≈ 1 semana) |

Para córners y tarjetas, la comparación con la cuota solo se puede medir **hacia delante**. En 4 temporadas de
SofaScore sí se mide la calibración contra el resultado real; contra el mercado, unas semanas de captura.

**Límites que dicen los propios textos:**
- El consenso de casas está casi perfectamente calibrado (Kaunitz). Batirlo en 1X2 es improbable; Yip tampoco lo
  logró en Premier ni Champions con córners.
- Donde hay margen (córners y tarjetas, 7–15 %), el beneficio medido viene de pocos meses y desaparece cuando las
  casas limitan la cuenta.
- Usar Δ para **elegir** qué se publica reabre la decisión del 30-oct («no competir en precio»). Como diagnóstico
  de calidad es compatible con ella; como criterio de selección es decisión del titular.

### Cambios a las recomendaciones tras la lectura

1. **Nueva prioridad 1 (A0):** fuerzas *score-driven* (Koopman-Lit) sobre Poisson bivariante, con goles y xG, en
   lugar de la vida media fija de 180 días. Es barata (segundos), solo necesita lo que ya hay en producción y
   tiene evidencia en Serie A. Antes de construir nada, revisar qué hace hoy `model/kalman.py`, que solo se usa en
   evaluación.
2. **A4 se concreta (Pantuso-Hvattum):** plus-minus ridge por tramos entre cambios, rojas y goles.
   - **Nuevo cálculo con nuestra data:** usar como respuesta la **diferencia de xG por tramo** en vez de la de
     goles. Los minutos de cada tiro permiten repartir el xG entre tramos, y el xG es mucho menos escaso que el gol.
   - Pesos por antigüedad, duración del tramo y marcador al inicio del tramo.
3. **A6 (bajas) se rebaja:** contar ausencias no aportó en el único estudio que lo midió. Las bajas entran solo a
   través de A4 (quién juega), no como variable aparte.
4. **No construir xG propio** (A3 se limita a encoger el xGOT − xG por portero, a prioridad baja).
5. **Motor C, córners:** BN con dispersión variable y los goles esperados del motor A como covariable. Poisson queda
   descartado.
6. **Fuera:** Glicko-2 adaptativo (retirado), transformers y grafos, xG propio y LLM como predictor.
7. **Tarjetas (tras leer Dawson & Dobson 2008 y Dawson et al. 2007):** Poisson bivariante local/visitante con
   dependencia (cópula de Frank o equivalente) e inflación de ceros; binomial negativa solo si sobra
   sobredispersión. Además de lo que sigue, lleva igualdad del partido q(1−q) desde el motor A, entrenador y
   temporada. Lleva:
   - faltas esperadas de cada equipo (la única estadística de juego significativa);
   - efecto de árbitro encogido (nuestra dispersión, sección 1);
   - sesgo al local;
   - llenado medio histórico del estadio (la asistencia del día es posterior al saque).
   Rojas y amarillas se modelan juntas, no por separado.
8. **Rotación y congestión (tras leer Page et al.):**
   - **Nuevo cálculo por jugador:** horas de partido en los 30 días previos (≤ 4,5 / 4,5–7,5 / > 7,5 h), días desde
     el último partido y si viene otro en ≤ 4 días;
   - amarillas acumuladas del jugador frente al umbral de sanción y fuerza del rival siguiente (Kruse & Maennig);
   - alimentan la probabilidad de que cada jugador sea titular o baja en A5 → A4;
   - no hay evidencia de un efecto directo sobre el resultado, así que no se suma un término de «cansancio» a λ.
9. **Siguen como hipótesis:** tiros anidados (Ievoli no lo respalda) y Weibull (sin log score fuera de muestra,
   forma ≈ Poisson).
10. **Auditoría de construcción de variables (control de fugas, Frontiers 2026)** antes de la fase F1:
    - cada columna SofaScore se marca *previa*, *del partido* o *posterior*;
    - solo las previas pueden ser predictoras del propio partido;
    - nota, valores normalizados, forma, cara a cara y rachas quedan fuera como predictores directos.
11. **Referencias en el banco de pruebas:**
    - consenso de casas sin margen (Kaunitz), además de Pinnacle;
    - pi-ratings + CatBoost (Constantinou);
    - para conteos, la línea de PropLine.
12. **Salida = distribución simulada de conteos**; selección de variantes por calibración (Walsh & Joshi). La
    comparación con la cuota es diagnóstico (Δ, CLV) salvo que el titular decida usarla para elegir.

**Orden revisado de pruebas en Serie A**

| Orden | Variante | Respaldo |
|---|---|---|
| 0 | Auditoría de variables + referencias (consenso sin margen, pi-ratings) | Frontiers 2026, Kaunitz, Constantinou |
| 1 | A0 *score-driven* | Koopman-Lit, Serie A incluida |
| 2 | A4 plus-minus con xG por tramo | Pantuso-Hvattum, Bajons-Hornik |
| 3 | C, córners BN con goles esperados | Yip et al. |
| 4 | C, tarjetas bivariantes con árbitro y faltas esperadas | Dawson & Dobson 2008 + nuestra medición |
| 5 | A5, rotación por carga de 30 días | Page et al. 2023 (lesiones); el efecto sobre el resultado no está probado |
| 6 | Tiros anidados | hipótesis |
| 7 | Weibull/CMP | Boshnakov sin log score; BN no ayudó en Koopman-Lit |
| 8 | Conformes | capa tardía |

Cada variante pasa la misma puerta (walk-forward, `check_leakage()`, log score, Diebold-Mariano, registro del
número de variantes probadas).

### Fórmulas que quedan en pie

- **A0, *score-driven*** (Koopman-Lit, ec. 14–18):
  - f_{t+1} = ω + B·f_t + A·s_t, con f = (ataques, defensas) de todos los equipos;
  - s_t = ∂ log p_BP(x, y; λ₁, λ₂, λ₃) / ∂f_t, sin escalar;
  - A = diag(a₁·I, a₂·I) y B = diag(b₁·I, b₂·I);
  - λ₁ = exp(δ + α_i − β_j), λ₂ = exp(α_j − β_i);
  - parámetros fijos (a₁, a₂, b₁, b₂, λ₃, δ) por máxima verosimilitud;
  - arranque con el ajuste estático de la primera temporada;
  - un equipo ascendido entra con valores tales que la media de la liga no cambie.
- **A4, plus-minus por tramos:**
  - Δxg_s = Σ_k β_k·x_{sk} + h + ε_s, con x_{sk} = +1 (local en el campo), −1 (visitante en el campo), 0 (fuera);
  - ridge con peso w_s = (duración del tramo) × 2^(−antigüedad/vida media);
  - la fuerza del once que juega es la media de las β de los once, ajustada por minutos esperados.
- **C, córners** (Yip): Córners ~ BN(μ, κ), con:
  - log μ = c + β₁·log(goles esperados) + β₂·log(|supremacía| + 0,01) + medias recientes de córners;
  - log κ = α₀ + α₁·log(|supremacía| + 0,01).

## 5. Rediseño recomendado de los tres motores

### Motor A → motor probabilístico (fuerza de equipo y de plantilla)

| # | Cambio | Dato nuevo que usa | Por qué |
|---|---|---|---|
| A1 | Fuerza desde el **xG sin penaltis por tiro** (volumen de tiros × calidad por tiro) en lugar del xG agregado mezclado 0,65 con goles; los penaltis por separado | mapa de tiros | menos ruido; separa equipos que tiran mucho de los que tiran bien |
| A2 | **Corrección por estado del partido**: descontar el xG generado con un jugador de más o con ±2 goles en el marcador | incidencias con minuto | el que va ganando se repliega; con diez el partido cambia |
| A3 | **Definición y portero** como efectos encogidos (xGOT − xG, `goalsPrevented`) | xGOT, portero por tiro | la regresión a la media es fuerte; solo entra lo que aguante fuera de muestra |
| A4 | **Fuerza del once**: aporte de cada jugador (plus-minus regularizado por tramos entre cambios + prior por estadísticas y posición) × minutos esperados | once, cambios con minuto, minutos, métricas | captura rotaciones, suplentes y bajas en una sola cuenta |
| A5 | **Rotación antes del once**: probabilidad de que juegue cada jugador según días de descanso, partido siguiente (Champions/Europa/Copa) y su historial de rotaciones; mezcla sobre onces probables; al confirmarse el once, versión T-60 (F7) | once histórico, calendario de otras competiciones | es el caso «juega con suplentes porque tiene Champions», medido en vez de supuesto |
| A6 | **Bajas** ponderadas por el peso del jugador en el once habitual, sin contarlas dos veces (si ya no jugaba, ya está en la fuerza) | `missingPlayers` | evita el doble conteo con la fuerza |
| A7 | **Entrenador** como punto de cambio en la dinámica (Kalman con colas pesadas), sin bono automático por técnico nuevo | entrenadores por partido | regresión a la media tras el cambio |

La salida sigue siendo una única matriz de marcadores (`price_all_markets`). Así los ~150 mercados son coherentes
entre sí.

### Motor B (mercado): sin cambio de fondo
PropLine sigue como fuente fija de cuotas. El mercado sin margen queda como **referencia de evaluación** y, en una
variante aparte, como prior (Egidi). Se publica la versión que mida mejor.

### Motor C → conteos de partido completos

| # | Cambio | Dato nuevo |
|---|---|---|
| C1 | **Tarjetas**: binomial negativa bivariante (local/visita) con efecto de árbitro jerárquico, faltas del equipo y del rival, derbi, diferencia de fuerza esperada (partido igualado) y sesgo al local | árbitro 100 %, tarjetas con minuto, faltas, VAR |
| C2 | **Córners**: Poisson compuesta / binomial negativa con centros, entradas al último tercio, toques en el área y estado esperado del partido (el que pierde saca más córners) | 51 métricas por mitad |
| C3 | **Mercados por mitad** (goles, córners, tarjetas 1T/2T) | estadísticas por mitad 100 % |
| C4 | **Nuevos conteos de equipo**: tiros, tiros a puerta, faltas, fueras de juego | estadísticas de equipo |
| C5 | **Jugador** (después): minutos esperados × tasa por 90 encogida a la posición (tiros, a puerta, tarjetas), repartida para que cuadre con el total del equipo | métricas por jugador |

### Lo que **no** recomiendo usar todavía
- `h2h`, `pregame_form`, `team_streaks` del proveedor (no son de antes del partido; se recalculan).
- La **nota** de SofaScore como predictor principal: es propietaria y cambia de versión (`ratingVersions`).
  Como mucho, prior débil.
- **Mapas de calor**: no están descargados. Sirven para estilo y rol, con poco valor esperado para el resultado.
  Se descargan solo si A4/C2 muestran que falta información de posición. Las posiciones medias ya cubren parte.
- **Momentum**: descriptivo.

## 6. Plan y protocolo de prueba (Serie A como laboratorio)

| Fase | Trabajo | Salida |
|---|---|---|
| F0 | Conciliar SofaScore contra producción partido a partido (goles, xG, xGOT, córners, tarjetas, árbitro), emparejando por hora de inicio y equipos | **Hecha el 31-oct** (solo lectura, resultados abajo) |
| F1 | **Hecha el 1-nov** con la tabla única `futbol.dato` (sección 0.1), 10 ligas cargadas; sustituye al esquema por tipos del diseño del 31-oct | `futbol.dato`; originales como archivos |
| F2 | Referencias en Serie A: DC actual; DC con xG agregado; CatBoost + pi-ratings; mercado sin margen | línea base |
| F3 | A1–A3, una a una (ablación) | ΔLog score / ΔRPS por capa |
| F4 | C1 (tarjetas con árbitro) y C2 (córners) | log score y calibración por línea |
| F5 | A4–A6 (once, rotación, bajas) | el mayor cambio esperado, el más caro |
| F6 | Puerta de activación con las **8 ligas del núcleo** (sección 0.2); las demás entran al completar su descarga | puerta con varias ligas |

### F0 hecha: conciliación SofaScore contra producción (Serie A, 31-oct)

Se exportó `matches` de Serie A desde agosto de 2023 (1.231 partidos, solo lectura) y se emparejó con el archivo por equipos, marcador y hora (diferencia mediana 0 min, máxima 165 min; 25 de 25 equipos mapeados). **Emparejados 1.230 de 1.231**; falta en SofaScore el Bologna–Monza de 26/27 (2–1).

| Campo | Valores comparables | Iguales | Diferencia media | Comentario |
|---|---|---|---|---|
| Goles | 2.460 | **100 %** | 0 | |
| Córners | 2.460 | 99,5 % | 0,007 | unas pocas diferencias de 1 a 3 córners |
| xGOT | 2.084 | 97,9 % | 0,004 | producción no tiene 354 valores (el 23/24 incompleto) |
| Tiros a puerta | 2.460 | 97,8 % | 0,026 | |
| Tiros totales | 2.460 | 95,4 % | 0,069 | 24/25 solo 91,3 %; en 66 valores distintos, 42 son menores en producción |
| Amarillas | 2.394 | 96,7 % | 0,040 | 7 partidos de 24/25 tienen 0 en producción y 3–4 en SofaScore |
| xG | 2.460 | **62,4 %** | 0,021 | ver abajo |
| Árbitro | 1.050 | 99,7 % por apellido | — | producción vacío en 180 partidos de 23/24 |

- **Definición de tiros:** `home_shots` de producción coincide con `totalShotsOnGoal` de SofaScore (tiros a puerta + fuera + bloqueados: 95,9–98,6 % según temporada). Tiros a puerta + fuera sin bloqueados no coincide (4–6 %).
- **El xG explica casi todo el desacuerdo, y depende de la fuente registrada en producción:**

| Temporada y fuente en producción | Valores | xG igual al de SofaScore | Correlación |
|---|---|---|---|
| 23/24, sin fuente registrada | 758 | 26,8 % | 0,992 |
| 24/25, sin fuente registrada | 454 | 28,6 % | 0,996 |
| 24/25, FotMob | 306 | 99,0 % | 0,999 |
| 25/26, FotMob | 760 | 99,2 % | 1,000 |
| 26/27, FotMob | 116 | 98,3 % | 1,000 |
| 26/27, API-Football | 40 | 27,5 % | 0,983 |
| 26/27, SofaScore | 24 | 79,2 % | 0,998 |

  **Lectura:** el xG de SofaScore es **el mismo** que el de FotMob (99 % idéntico con tres decimales, coherente con un proveedor común aguas arriba), y es el xG del «histórico sin fuente» de 23/24 y 24/25 (más de mil valores) lo que difiere: promedio +0,015 y hasta 1,16 en un partido (Juventus–Cagliari: 3,51 frente a 2,35). Con correlación 0,99, es un cambio de versión del modelo de xG o de proveedor, no un error de captura. El xG de API-Football también difiere.
- **Árbitro:** en producción casi todo está en `referee_fotmob` (1.010 de 1.230); `referee` solo tiene 40. SofaScore trae los 380 de 23/24, que producción no tiene (180 vacíos). En 3 partidos de 1.050 el árbitro es distinto, por revisar.

**Qué significa para el plan**
1. **SofaScore es consistente con producción** en goles, córners y tiros a puerta y sirve como fuente verificada; el 3–9 % de diferencias en tiros totales y amarillas está en 24/25 y es de producción (valores en cero o más bajos).
2. **El xG de 23/24–24/25 sin fuente en producción tiene una versión alternativa de SofaScore/FotMob, y el A/B de abajo muestra que no mejora el pronóstico.** La regla del proyecto (xG usable solo desde su recepción real acreditada) impide sustituirla de forma automática: las filas sin fuente no tienen recepción acreditada, y los de SofaScore se recibieron el 30-oct-2026. Es una decisión del titular si el xG de esos 1.212 valores se reemplaza para entrenar.
3. Los 180 árbitros que faltan en 23/24 se pueden llenar desde SofaScore con la misma regla de procedencia y fecha de recepción.
4. No se modificó nada en el servidor.

### A/B del xG en Serie A: producción frente a SofaScore (31-oct, Serie A solamente)

Criterio fijado antes de mirar: «gana» SofaScore si el cambio de log loss (SofaScore − producción) tiene IC95 < 0. Mismo walk-forward, mismas filas, modelo con xG 65 % + goles 35 %; solo cambia de dónde sale el xG (473 de 1.230 partidos lo tienen distinto; 451 de ellos son de las filas sin fuente). Se evaluaron 850 partidos y se probaron **dos variantes** (primaria con ρ y calibrador, secundaria cruda). Intervalos con bootstrap en bloques de 10 partidos.

| Variante | RPS producción | RPS SofaScore | ΔRPS (IC95) | Δ log loss (IC95) |
|---|---|---|---|---|
| **Primaria** (xG + ρ + calibrador) | 0,19481 | 0,19499 | +0,00017 [−0,00004, +0,00038] | +0,00063 [−0,00018, +0,00146] |
| Secundaria (xG crudo) | 0,19677 | 0,19688 | +0,00011 [−0,00001, +0,00022] | +0,00024 [−0,00011, +0,00064] |

- **SofaScore no gana:** el intervalo del log loss incluye cero y apunta al lado contrario (ligeramente peor). Por temporada: 24/25 Δ log loss +0,0013, 25/26 −0,0002, 26/27 +0,0012.
- **Por qué casi no hay efecto:** al cambiar el xG de entrenamiento, la probabilidad de un partido cambia en media 0,0053 (p95 0,022, máximo 0,076). Las dos versiones del xG tienen correlación 0,99.
- **Decisión:** el xG de producción se queda; no hay razón predictiva para sustituirlo. Queda registrado en `harness/tareas.md` (paso 1 hecho). La carga del archivo SofaScore sigue teniendo sentido para lo que producción no tiene (tiros con coordenadas, jugadores, once, bajas, incidencias y los árbitros de 23/24).
- **Alcance:** solo Serie A, con las 4 temporadas descargadas completas. Las otras ligas se repiten cuando el titular termine de descargarlas.

Protocolo: walk-forward por jornada (entrenar hasta la jornada j, predecir j+1). 23/24 queda como calentamiento,
24/25 y 25/26 para elegir variantes, y 26/27 se reserva y solo se mira al final. `check_leakage()` antes de leer
un resultado. Principal: log score; secundarios: RPS, Brier y calibración. Diebold-Mariano agrupando ligas.

**Advertencia de potencia:** una temporada de Serie A son 380 partidos. Mejoras de milésimas de RPS no se
distinguen con una sola liga. Serie A sirve para construir y depurar; la decisión de activar se toma con las
siete ligas descargadas. Entrenar en local y subir el artefacto, nunca en el worker.

## 7. Decisiones del titular

1. ¿Conservar la historia anterior por niveles (recomendado) o recortar las consultas del motor a 4 temporadas?
2. Orden: ¿motor C primero (tarjetas/córners, más rápido y con más margen de mejora) o motor A primero
   (once/rotación, más valioso y más caro)?
3. ¿Descargar el calendario de Coppa Italia y otras copas (necesario para A5) desde la misma herramienta?
4. ¿Mapas de calor: no por ahora (recomendado)?
5. ~~Permiso de lectura en el servidor para F0~~ (F0 hecha el 31-oct).
6. (1-nov) ¿Aplicar db/097–099 y recargar las 10 ligas de SofaScore (mitades, árbitro, umbrales, derbis y fase 2, sección 0.3)?
7. (1-nov) ¿Retirar R1–R3 (≈ 1,6 GB, sección 0.4)? R3 borra dos tablas inmutables tras exportarlas a archivo.
8. (1-nov) ¿Descargar las copas nacionales para la carga de 30 días (A5)? Es la misma pregunta 3, ahora con el
   hueco medido.
