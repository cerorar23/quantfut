# Datos al motor: lo ejecutado el 18-oct-2026

Seguimiento del plan `docs/superpowers/specs/2026-10-15-mejoras-tres-motores-plan.md` (§5). El titular autorizó
ejecutar los cuatro grupos. Todo lo de abajo está en producción, con ensayo antes y registro en `DEPLOYS.md`.
**El modelo, las predicciones, los picks y la cadena de hashes no se tocaron.** Los únicos datos que cambian lo que
ve el reentrenamiento del 1-nov son los de la sección 1 (Arsenal) y la 2 (45 cierres).

## 1. Orden de identidades (grupo 4)

| Qué | Resultado | Cómo |
|---|---|---|
| Arsenal figuraba como Arsenal de Sarandí | **33 partidos de copa corregidos** (2014 → 2024-12-11); 23 con xG. Arsenal pasa a 75 partidos de copa | `db/073` con auditoría en `correcciones_identidad` y reversión escrita |
| 4 alias de The Odds API (Bayern München, Internazionale Milano, LOSC Lille, Young Boys) | Registrados | `team_aliases`, auditados |
| Cierres de Pinnacle de copas | **+45 cierres** (135 cuotas): 39 de los alias más 6 de Arsenal, que ya empareja. Sin cierre en copas: 103 → **58** | `cierres_odds_api cargar --aplicar` con snapshots ya pagados; repetir inserta 0 |
| Árbitros API-Football ↔ FotMob | **54 equivalencias** (todas cumplen la regla inicial + apellido) → +125 partidos con árbitro en formato API-Football | `db/077`, `arbitro_equivalencia`, vista `v_arbitro_unificado` |
| Jugadores API-Football ↔ FotMob | **7.834 puentes** (6.676 de confianza alta, 1.158 baja) de 8.301 jugadores con estadísticas (94 %) | `db/079`, `puente_jugador`; muestra de 16 revisada a mano: 16 correctas |
| 379 «identidades» de copas | Cerrado como no resoluble por diseño: 110 equipos, ningún partido con sus dos equipos probados | ver `docs/ordenar_identidades_20261018.md` |

Referencia sobre árbitros: FotMob da árbitro en 19.183 partidos desde 2024 y API-Football en 2.799; casi no se
solapan, así que el cruce solo suma 125. La salida real para F5 es usar el **nombre de FotMob como llave**.

## 2. Lo que ya teníamos, ahora en tablas del motor (grupo 1)

Tablas nuevas con clave `match_id` (`db/075`, cargador `qf.ingest.fotmob_a_motor`). No se mezclan con
`lineups_historicas` ni `estadisticas_jugador`: esas llevan identificadores de API-Football.

| Tabla | Filas | Contenido |
|---|---|---|
| `fotmob_partido` | 20.331 | ronda, ida/vuelta, árbitro, asistencia, estadio, formaciones, valor y edad del once, entrenadores, clima |
| `fotmob_jugador_partido` | 852.126 (22.199 jugadores; 70 % con valor de mercado) | titulares y suplentes con posición, camiseta, edad, valor, rating |
| `fotmob_baja` | 47.140 (6.537 jugadores; 73 % con valor) | no disponibles: lesión (43.237) o sanción (2.971), regreso esperado |
| `v_fotmob_jugador_partido` | vista | une los minutos y estadísticas ya archivadas |

Cobertura por partido: entrenador 100 %, ronda 93 %, asistencia 93 %, árbitro 94 %, valor del once 73 %,
**clima medido en el partido 40 %** (80-93 % en Premier, LaLiga, Liga MX, MLS, Argentina y Brasil desde jul-2025;
muy bajo antes), marcador global de eliminatoria 1,7 %.

Comprobado contra `matches`: el árbitro coincide en 19.183 de 19.183 partidos con los dos y el estadio en 20.331 de 20.331;
ninguna fila se recibió antes del saque.

Advertencias que el consumidor debe respetar:
- Todo se guardó **después** del partido (`recibido_en`). Las bajas son la reconstrucción de quién faltó, no lo que se
  sabía antes del saque: sirven para entrenar y medir, no como entrada anticipada sin su propia regla de PIT.
- El clima de FotMob es el valor al guardarse la página. Solo `clima_en_partido = true` (entre 1 h antes y 3 h después
  del saque) es el clima del partido; el resto es de otro día y no se debe usar.

## 3. Capturas (grupo 2)

| Captura | Estado |
|---|---|
| Calendario de cada equipo, temporada en curso | **Hecho:** cron diario 05:40 UTC (`calendario_equipos --temporadas 2026 --refrescar`, ~313 llamadas de 7.500) |
| No disponibles de FotMob antes del partido y archivo de FotMob a diario | **Hecho (autorizado por el titular el 18-oct):** `qf.ingest.fotmob_captura`, `db/081`. Ver §6 |
| Pronóstico de clima a la hora de publicar | **Hecho con la misma captura:** la página previa de FotMob trae el pronóstico (`apiUsed: forecast`, con probabilidad de lluvia y hora de actualización). Open-Meteo no se usa, ver §6 |

## 4. Descargas (grupo 3)

| Dato | Estado |
|---|---|
| Calendario de copas, continentales y amistosos desde 2023 | **Hecho:** `calendario_equipo`, 60.979 partidos, 315 equipos × 4 temporadas, 1.255 llamadas a API-Football |
| Altitud de los estadios | **Hecho:** `estadio_altitud`, 728 de 728 con coordenadas (99,3 % de los partidos desde 2024). Toluca 2.682 m, Ciudad de México ~2.281 m |
| Clima histórico ERA5 | **En curso:** token recibido y probado; 423 celdas de 0,25° (~5 h), `clima_era5_partido`. Ver §6 |
| Minutos con la selección nacional | **No hecho:** pesado, segunda etapa de F12 |

Descanso y carga ya se pueden calcular: la vista `v_descanso_equipo` (`db/080`) da días de descanso, partidos en 14
y 30 días y última competición. Frente a `matches` solo, el calendario revela un partido intermedio que no se veía
en el **17,6 %** de los equipo-partidos desde 2024 (4.243 de 24.102), y en 2.204 el descanso real fue de menos de 4 días.

## 5. Pendiente que descubrí

- **Estadios duplicados:** 182 grupos con las mismas coordenadas (384 estadios), p. ej. el Azteca y el Banorte, o dos
  «Olímpico Universitario». No afecta a la altitud, sí a cualquier característica por sede o viaje (F6).
- **Reentrenamiento y Arsenal:** la corrección entra sola al del 1-nov. Su efecto no está medido.
- **Pruebas:** la suite completa tiene 9 fallos que no son de estos cambios (ver `harness/progreso.md`).

## 6. Captura de FotMob, pronóstico y clima histórico (autorizado el 18-oct, tarde)

**Captura de FotMob** (`db/081`, `qf.ingest.fotmob_captura`, tres cron con `flock`):
- `referencias` (05:50 UTC): qué id de FotMob es cada partido nuestro. 503 nuevas; **todos** los partidos próximos de
  las 13 ligas modeladas ya tienen referencia. 495 equipos de FotMob identificados con partidos de liga.
- `previos` (cada 15 min): instantáneas de un partido futuro en cuatro ventanas, a ~24 h, ~4 h, ~70 min y ~40 min del
  saque: alineación probable o confirmada (`predicted` / `lastStarting11` / la oficial), no disponibles con tipo y
  regreso esperado, entrenadores, valor del once y **pronóstico de clima**. Cada fila lleva su hora real de captura.
  Primera corrida: 8 partidos, 46 jugadores y 3 a 11 bajas por partido.
- `posteriores` (cada hora): la página del partido terminado a las tablas de la §2. Primera corrida: 60 partidos.
- Se conserva el original comprimido de cada captura (`fotmob_original`, ~27 kB; ~3 MB al día).
- **Salvaguardas:** una petición cada 0,8 s en serie; HTTP 401, 403 o 429 detienen todo y dejan 12 h de enfriamiento
  con alerta a Telegram; un id de respuesta distinto del pedido, o un partido ya empezado, se descarta. Sin evasión de
  controles de acceso. Probado: un 404 no cuenta como bloqueo; los tres códigos de bloqueo no se reintentan.

**Open-Meteo no se usa.** Se pidió usar el plan gratuito por ser un proyecto «sin fines comerciales», pero QuantFut
vende suscripciones y el plan gratuito es solo no comercial; además el titular había contratado el plan de pago
Standard, cuya clave nunca se entregó. Como el pronóstico de FotMob ya se guarda point-in-time, no hace falta. Si más
adelante se quiere una segunda fuente, hay que cargar la clave del plan de pago.

**Clima histórico ERA5** (`db/082`, `qf.ingest.era5_clima`): conjunto `reanalysis-era5-single-levels-timeseries` de
Copernicus, una petición por celda de 0,25° con seis variables horarias, guardada en disco antes de tocar la base.
Token en el `.env` del servidor (permisos 600); no está en el repositorio. Resultado por partido: temperatura, humedad
(de punto de rocío), viento, lluvia acumulada en la ventana de 3 h y nubosidad. **Validación:** contra el clima que
midió FotMob en 184 partidos comunes, temperatura con correlación 0,98 y error medio de 1,2 °C; humedad 0,90; viento
0,64; nubosidad 0,58. Es clima observado (reanálisis), no pronóstico: sirve para medir el efecto del clima.
Atribución obligatoria de la licencia: «Contains modified Copernicus Climate Change Service information».
