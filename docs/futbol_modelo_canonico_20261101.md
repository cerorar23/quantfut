# Fútbol: una sola tabla para el motor — `futbol.dato` (1-nov-2026)

Idea del titular: todo lo que se capture de fútbol —APIs, servicios, scrapers— se junta en **una sola tabla**, con nombres de campo unificados, y esa tabla es la única que alimenta al motor. Cada fuente tiene su forma de capturar y sus nombres; un adaptador por fuente los traduce a los de esta tabla.

## 1. La tabla

`futbol.dato` (db/094): una fila por hecho (`tipo`), columnas tipadas y esparcidas (cada tipo usa las suyas y deja el resto en NULL; en Postgres un NULL cuesta un bit, así que es compacta). Dos tipos que miden lo mismo comparten columna (`tiros_fuera` vale para un jugador y para un equipo).

| `tipo` | Una fila por… | Clave dentro del partido | Qué trae |
|---|---|---|---|
| `jugador` | jugador y partido | `side` + `jugador_id` | las 82 estadísticas del scraper: minutos, nota (y alternativa), goles, asistencias, xG, xGOT, xA, pases clave, tiros, pases por mitad del campo, conducciones y progresión, duelos, entradas, errores, penaltis, portero, carrera (km a alta velocidad y esprint), índices de valor normalizados, edad, valor de mercado… |
| `equipo` | lado, partido y periodo | `side` + `evento` (0 = partido, 1 = 1.ª parte, 2 = 2.ª) | las 46 claves del scraper menos las que ya viven en `matches` (córners, xG, tarjetas, tiros totales y a puerta) |
| `baja` | jugador ausente | `side` + `jugador_id` | estado (missing/doubtful), motivo, fecha de regreso |
| `alineacion` | lado | `side` | formación, confirmada, completa |
| `entrenador` | lado | `side` | id y nombre |
| `contexto` | partido | — | trayectoria del árbitro, ronda, descuentos, goles al descanso, asistencia |
| `tiro` | tiro | `evento` = id del tiro | minuto, tiempo añadido, resultado, situación, parte del cuerpo, x/y, portería, coordenadas del bloqueo, tipo de gol, portero, xG, xGOT |
| `incidencia` | tarjeta, cambio, gol, VAR, descuento… | `evento` = orden | subtipo, clase, minuto, jugador, segundo jugador, marcador, lesión, duración del descuento, anulada, confirmada y la red de pases del gol (JSONB) |
| `clima` | partido | — | temperatura, humedad, viento, precipitación, nubosidad |
| `estadio` | partido | — | estadio, ciudad, capacidad, coordenadas, altitud |
| `momentum` | punto del gráfico | `evento` = minuto × 2 | presión por minuto (también medios minutos) |
| `posicion` | jugador y partido | `side` + `jugador_id` | posición media (x, y) y número de puntos |

Cobertura del scraper de SofaScore, medida con el partido Fulham–Bournemouth (12 bloques): `event`, `statistics` (3 periodos), `lineups`, `incidents`, `shotmap`, `momentum`, `average_positions` y `managers` entran enteros. Quedan fuera solo `h2h`, `pregame_form` y `team_streaks` (no verificables como previos al partido) y `best_players`/`player_ranking` (los calcula el propio descargador de lo ya guardado); siguen disponibles en los archivos originales.

Clave primaria `(match_id, tipo, side, jugador_id, evento)`: **una fila por hecho, sin repetidos posibles**. Cada fila lleva `fuente`, `recibido_en` y `pit` (posterior / reconstruido / no_acreditado).

Reglas:
- **Una fuente por tipo y partido** (y SofaScore completa lo que falta): la de mejor prioridad en `futbol.prioridad_entidad` (jugadores, bajas, alineación y entrenador: FotMob > SofaScore > API-Football; clima: ERA5 > FotMob; altitud: OpenTopoData). Cargar una mejor reemplaza las filas de la peor en la misma transacción; una peor nunca pisa a una mejor; un tipo sin filas no se adueña del partido. Donde manda FotMob, SofaScore no pisa la fila: **completa solo las columnas vacías** (xG del jugador, pases clave, penaltis, conducciones…) y lo anota en `fuente_extra`; `nota`, `valor_mercado` y `posicion_id` no se completan nunca porque son entradas del motor con el sentido de cada fuente.
- **Identidad única de jugador**: `jugador_id` es el id de SofaScore; el jugador que no tiene pareja recibe un id negativo y determinista (`futbol.id_sintetico`) y `futbol.vincular_jugador` lo pasa al de SofaScore cuando aparece la pareja. Los enlaces salen de evidencia (mismo partido, mismo lado, mismo nombre, repetido en 2 o más partidos).
- **Los originales no se copian**: viven como archivos (`~/sofascore-scraper/data/v3`) y la base solo guarda su índice (`futbol.original`).
- Tablas de apoyo (no son datos para el motor): `fuente`, `prioridad_entidad`, `jugador`, `jugador_fuente_id`, `partido_fuente`, `original`.

## 2. Lo que sigue fuera de la tabla, y por qué

- **`matches`**: es el registro del partido (su identidad y resultado) y 36 tablas lo referencian.
- **`odds_snapshots`**: ya es UNA tabla de cuotas con columna de fuente (PropLine, The Odds API, football-data.org, OddsPapi), pero es **inmutable por trigger** y de ella depende la cadena de hashes de los picks. Meterla en `futbol.dato` exige quitar esas garantías; solo se hace con confirmación explícita del titular.
- **Lo conocido antes del partido** (once previsto de SportsAPIPro/FotMob, bajas previas): segunda fase. Necesita su propio `pit` y la hora de cada captura, porque el motor usa lo último conocido a T-60.

## 3. Cobertura por servicio (1-nov-2026)

| Servicio | Entra por | Estado |
|---|---|---|
| Scraper SofaScore del VPS (2 pasadas al día) | `qf.ingest.futbol_sofascore` (tipos jugador, equipo, baja, alineacion, entrenador, contexto, tiro, incidencia) | **Hecho** |
| FotMob (ZenRows solo es su transporte de respaldo) | `futbol.cargar_fotmob()` (jugador, baja, alineacion, entrenador) y `cargar_clima()` | **Hecho** |
| API-Football | solo historia: 652 filas de jugador; sin captura nueva desde el 25-oct | Congelado |
| SportsAPIPro | sus ids son los canónicos; su salida previa (`lineups_previstas`, `injuries`) es de la fase 2 | Pendiente (fase 2) |
| Copernicus ERA5 | `futbol.cargar_clima()` | **Hecho** |
| OpenTopoData (altitud) | `futbol.cargar_estadio()` | **Hecho** |
| PropLine, The Odds API, football-data.org | `odds_snapshots` | Ya era una tabla; inmutable (ver arriba) |

## 4. Estado en producción (1-nov-2026)

db/094 y db/095 aplicadas con respaldo previo (`~/backups/futbol_pre_094_20261101.sql.gz`) y un ensayo con `ROLLBACK` sobre los datos reales. La 095 absorbió las nueve tablas por tipo que existían, comprobó que cada tipo cuadrara fila por fila (si no cuadra, se deshace entera) y las retiró.

- **1.604.058 filas** en 22.504 partidos; 591 MB (la base completa, 4,26 GB; disco con 43 GB libres).
- 0 filas repetidas, 0 tipos con dos fuentes en un partido, 0 ids de jugador sin ficha.
- 477.902 de las 885.899 apariciones de FotMob tienen el id de SofaScore (las demás son de ligas o temporadas que el archivo de SofaScore aún no cubre y llevan id negativo).

## 5. Lo que falta para que el motor lea solo de aquí

1. **Lectores del motor**: `FUTBOL_LECTURA=canonica` hace que `jugadores.cargar_filas` lea `futbol.dato` y que `ajuste_xi.once_confirmado` traduzca el once previo al id canónico. Por defecto está apagado. Antes de activarlo hay que comparar el modelo con las dos lecturas y regenerar el estado guardado. `contexto.py` (bajas y valor del once, de `fotmob_baja` y `fotmob_partido`) y `player_value.py` (que lee `estadisticas_jugador`, tabla de API-Football congelada) se evalúan aparte.
2. **Capturas diarias**: `scripts/futbol_diario.sh` rellena la tabla (SofaScore reciente, puente de identidad, FotMob de los últimos 3 días, clima y estadio). Falta instalar su cron (08:15) con autorización del titular.
3. **Fase 2**: lo conocido antes del partido.
4. **Retirar lo redundante** de las tablas de origen (por ejemplo el JSONB de `historical_football_player_stats`) con respaldo y confirmación.
