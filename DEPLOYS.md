# Registro de despliegues — QuantFut

Una sola regla de fondo: **lo que corre en producción es lo que dice `main`**. Todo cambio en el servidor se
anota aquí en el mismo momento, y solo despliega una sesión a la vez.

## Repositorio
Privado en GitHub: `cerorar23/quantfut` (rama `main`). Cada push ejecuta el arnés en GitHub Actions
(`.github/workflows/pruebas.yml`, con Postgres 16 real). **GitHub no permite proteger ramas en repos privados del
plan gratuito**, así que la regla es por costumbre: rama + pull request + arnés verde antes de fusionar a `main`.
El servidor todavía NO despliega desde aquí (pendiente: clave de despliegue de solo lectura y `git pull` de una etiqueta).

## Estado medido el 2026-10-15 (antes de ordenar; el worker ya quedó en 0 diferencias, ver el registro)
Comparando cada `.py` de `src/` contra `main`:

| Lugar | Archivos | Distintos a `main` | Faltan de `main` |
|---|---|---|---|
| `main` | 130 | — | — |
| Carpeta `~/quantfut/src` del servidor | 90 | 29 | 40 |
| Contenedor worker (cron y reentrenamiento) | 107 | 12 | 23 |
| Contenedor API | 113 | 24 | 17 |

La carpeta `~/quantfut/src` y la API llevan versiones antiguas de `train.py` y `clv.py`. **No reconstruir ninguna
imagen desde esa carpeta sin sincronizarla** con `main`: revertiría código.

## Procedimiento (objetivo)
0. `scripts/deploy.sh estado` antes de empezar: dice qué corre realmente frente a `main`.
1. Árbol limpio, cambio en `main`, arnés en verde (GitHub Actions o `./scripts/harness_check.sh`).
2. Comparar lo desplegado con el commit base anterior: si hay diferencias que no son tuyas, parar y averiguar.
3. Respaldar lo que se va a cambiar (archivos y, si toca la base, la tabla).
4. Construir y desplegar **solo el servicio necesario**; no tocar el worker el día del reentrenamiento.
5. Verificar hashes, salud (API 200) y modelo activo.
6. Anotar la entrada de abajo con la vuelta atrás.

## Registro (lo más reciente arriba)

### 2026-11-03 · NBA: quintetos históricos 2021-26 en `nba.evento` (imagen `nba-captura:rot-e6c49f2`) · SOLO base de datos y archivos, rama `nba/rediseno-s0`
- Archivos locales copiados a `~/nba-isolated/nba-captura/historico/`: `rotaciones.jsonl.gz` (= `nba_pending_rotations_v6`, 6.141 juegos, superconjunto de las rotaciones oficiales) y `games.json` (nba_extended_box). Paso nuevo `rotaciones` de `captura.py historico`, 6 contenedores en paralelo por fragmento `i/6` con `COPY` por partido; probado antes en Postgres desechable.
- Resultado: 183.680 filas `tipo=quinteto` en 6.047 juegos (2021-22: 1.227, 2022-23: 1.222, 2023-24: 1.217, 2024-25: 1.194, 2025-26: 1.187), siempre 5 jugadores por lado, `reloj_s` de 0,1 a 720, `fuente = nba_oficial`, secuencia desde 1.000.001. 94 juegos del archivo no están en el catálogo de cajas y no se cargaron; 0 jugadores sin identidad. `recibido_en` = fecha de adquisición del archivo; tiempos cuantizados, no seguimiento exacto.
- `imagen_actual` NO cambia (crons intactos); la imagen nueva queda en `imagen_rotaciones`.
- **Vuelta atrás:** solo-anexar; deshacer exige restaurar el respaldo diario de `nba_datos`. Es idempotente: relanzar no duplica.

### 2026-11-02 23:10 UTC · NBA: cajas finales y partes oficiales de lesiones 2021-26 en `nba_datos` (imagen `nba-captura:cdecc6c`) · SOLO base de datos y archivos, rama `nba/rediseno-s0`
- Archivos que ya existían en el PC (sin créditos), copiados a `~/nba-isolated/nba-captura/historico/` con hash verificado: `players.jsonl.gz` y `games.json` de nba_extended_box (cajas por jugador y por equipo) y los dos `reports.jsonl.gz` de partes oficiales ya extraídos de los PDF (816 + 1.910 partes). Ensayados antes con la misma carga en un Postgres desechable local.
- Carga única (`captura.py historico`, pasos `juegos,cajas,partes`, contenedor de una vez): 2.696.246 filas de caja final (166.632 jugador-partido, 12.828 equipo-partido; 2021-22 a 2025-26, regular, play-in y playoffs; 1.229 a 1.316 juegos por temporada) con `pit = reconstruido` y `recibido_en` = fecha de adquisición del archivo; 2.726 partes oficiales (150.693 filas nuevas tras descartar repeticiones) con la hora del propio parte como `recibido_en`. A quien no jugó solo se le guarda `jugo = 0`, sin estadísticas en cero.
- Resultado: base de 2,2 GB (disco del VPS al 61 %); 3.868 juegos tienen a la vez cuota de cierre y caja final (insumo del análisis contra el mercado); jugadores canónicos 1.242, **113 marcados ambiguos** (mismo nombre normalizado en varios ids: no se fusionan por duda; queda por mejorar con el equipo como pista).
- La imagen `cdecc6c` es ahora `imagen_actual` (los crons rotowire, espn, parte, nba y propline la usan); mismo código de captura que `9d73ed5` más los cargadores históricos.
- **Vuelta atrás:** los datos son solo-anexar; para deshacer habría que recrear `nba_datos` desde el último respaldo diario (`~/nba-isolated/nba-captura/respaldos`). La imagen anterior sigue en el servidor y basta escribir su etiqueta en `imagen_actual`.

### 2026-11-03 15:35 UTC · NBA: equipo con 100.000 simulaciones en `nba-motor:6b85093` · SOLO imágenes y archivos, rama `nba/rediseno-s0`
- `imagen_motor` = `nba-motor:6b85093`. G-fuga aprobada antes del cambio (100 partidos de equipo, 60 de jugadores, 5.852 distribuciones sin violaciones); tick de las 15:40 sin errores. El número de simulaciones forma parte de `version_modelo` (`n=100000`).
- **Vuelta atrás:** `cp imagen_motor.anterior imagen_motor` (vuelve a `nba-motor:233e372`, 20.000 simulaciones).

### 2026-11-03 04:18 UTC · NBA: contratos Pydantic en las fronteras, `nba-motor:233e372` · SOLO imágenes y archivos, rama `nba/rediseno-s0`
- `imagen_motor` = `nba-motor:233e372` (pydantic 2.14.2). El motor valida antes de sellar; G-fuga con validación aprobada antes del cambio (5.852 distribuciones, 0 violaciones); tick de las 04:20 sin errores; 192 sellos existentes intactos.
- La imagen de la API (`nba-api`) lleva pydantic pero sigue sin desplegarse.
- **Vuelta atrás:** `cp imagen_motor.anterior imagen_motor` (vuelve a `nba-motor:a16b019`).

### 2026-11-03 03:55 UTC · NBA: modelo reentrenado con SofaScore en `nba-motor:a16b019` · SOLO imágenes y archivos, rama `nba/rediseno-s0`
- `imagen_motor` = `nba-motor:a16b019` (props `6323d806ed81`, impacto de 1.083 jugadores, efecto del descanso 2,90, sigmas 13,81/18,43). G-fuga con `nba_oficial` y `sofascore` aprobada antes del cambio; ejecución del cron de las 03:55 sin errores. Los sellos nuevos llevan versiones nuevas en `version_modelo`; los anteriores no se tocan.
- **Vuelta atrás:** `cp imagen_motor.anterior imagen_motor` (vuelve a `nba-motor:b874e9a`); lo sellado se queda.

### 2026-11-03 03:40 UTC · NBA: carga de SofaScore (6 temporadas) a `nba_datos` · SOLO base de datos y archivos, rama `nba/rediseno-s0`
- Respaldo previo `~/nba-isolated/nba-captura/respaldos/nba_datos_20261103T031925Z.dump`. Archivo `historico/sofascore_nba_eventos.jsonl.gz` (4,9 MB, derivado de `SOFASCORE\data\v3` en el PC). Imagen de carga `nba-motor:1df38de` (la del cron no cambia).
- 5.492 partidos, 93 partidos nuevos, 2.409.592 filas nuevas (fuente `sofascore`, prioridad 2, `pit = reconstruido`), 932 jugadores emparejados por huella, 61 por nombre (14 canónicos nuevos). Base 3,05 GB, disco 64 %.
- Motor y colectores siguieron sanos durante la carga (sin errores en las 3 ejecuciones del motor intermedias).
- **Vuelta atrás:** las filas son solo-anexar; para deshacerlo habría que restaurar el respaldo previo. La fuente `sofascore` se puede ignorar sin tocar datos (prioridad menor que `nba_oficial`).

### 2026-11-03 04:00 UTC · NBA: equipo 2.1 con jugadores en `nba-motor:b874e9a` · SOLO imágenes y archivos, rama `nba/rediseno-s0`
- `imagen_motor` = `nba-motor:b874e9a` (impacto `81a0df827045`, datos hasta 2026-04-12; props `df758d36f764`). El cron `*/5` sigue igual; desde el siguiente partido sin sello de equipo se sella `equipo-2.1`. Simulacro sin errores y G-fuga de la mezcla aprobada (60/60 en 2.1, 0 diferencias) antes del cambio.
- Los tres partidos nocturnos del 2-nov quedan con el equipo 2.0 ya sellado (no se duplica).
- **Vuelta atrás:** escribir `nba-motor:06d13f2` (equipo 2.0 + props) o `nba-motor:88f7759` (solo equipo 2.0) en `imagen_motor`; lo sellado se queda.

### 2026-11-03 03:35 UTC · NBA: props de jugador en `nba-motor:06d13f2`, alertas del motor · SOLO base de datos, imágenes y archivos, rama `nba/rediseno-s0`
- `imagen_motor` = `nba-motor:06d13f2` (artefacto de props `df758d36f764`, datos hasta 2026-04-12). El cron `*/5` del motor (activo desde las 01:36 UTC) selló desde las 02:30 los props de 3 partidos nocturnos: 192 pronósticos en total (4 de equipo + 188 de jugador), cadena verificada con `verificar_cadena`.
- `ejecutar_motor.sh` monta `datos/` para el estado de alertas; `motor.env` (modo 600) recibe `NBA_MOTOR_DIR` y las dos variables del canal de alertas copiadas del `.env` principal. No se mandó ningún mensaje de prueba.
- G-fuga con jugadores en solo lectura: 60 partidos, 0 diferencias de repetibilidad y de plantilla frente a la referencia independiente, cobertura 81,5 %.
- **Vuelta atrás:** escribir `nba-motor:88f7759` en `imagen_motor` (vuelve a sellar solo el equipo); quitar la línea del cron detiene todo. Lo sellado es solo-anexar y se queda.

### 2026-11-03 01:35 UTC · NBA: `nba-motor:88f7759` y usuario `nba_motor` (cron NO activado) · SOLO base de datos, imágenes y archivos, rama `nba/rediseno-s0`
- Rol de base `nba_motor` (login; hereda `nba_lector` y `nba_escritor`: lee todo, solo inserta); contraseña generada en el servidor, solo en `~/nba-isolated/nba-captura/motor.env` (modo 600). Imagen `nba-motor:88f7759` (`imagen_motor`) y `ejecutar_motor.sh` con candado.
- Simulacro con datos reales (`--simulacro --ahora 2026-11-03T02:30:00Z`): 3 partidos pronosticados, 0 errores, nada sellado; `nba.pronostico` sigue vacía. El cron no está instalado: `crontab -l | grep motor` devuelve 0.
- **Incidente (mío) 00:10-01:33 UTC:** al cambiar `imagen_actual` escribí `3ca6392` en vez de `nba-captura:3ca6392` y los crons de captura fallaron ≈ 1 h 20 min (23 ejecuciones con `pull access denied`). Corregido a las 01:33; ESPN y partes oficiales recuperaron lo pendiente; las fotos de Rotowire de ese tramo se perdieron. Regla: `imagen_actual` e `imagen_motor` guardan el nombre completo de la imagen.
- **Vuelta atrás:** no activar el cron (o quitar su línea); `DROP ROLE nba_motor` si se quiere borrar el usuario; las imágenes se borran con `docker rmi`.

### 2026-11-03 01:50 UTC · NBA: imágenes `nba-captura:408ea38` y `nba-motor:df8a151` y G-fuga (solo lectura) · SOLO imágenes y archivos, rama `nba/rediseno-s0`
- Construidas dos imágenes en el VPS: `nba-captura:408ea38` (código v2 del Sprint 5; `imagen_actual` sigue en `3ca6392`, los crons no cambian) y `nba-motor:df8a151` (lo del colector más numpy 2.1.3 y scipy 1.14.1). `build/src` del servidor tiene el código del Sprint 5; el anterior en `build/src.antes-3ca6392`.
- G-fuga ejecutada con `nba-motor:df8a151` contra `nba_datos` en una transacción de solo lectura (200 partidos de 2025-26): 0 diferencias, 0 fugas, diferencia máxima con el cálculo independiente 5·10⁻⁵. No se escribió nada en la base ni se selló ningún pronóstico (`nba.pronostico` sigue vacía).
- **Vuelta atrás:** nada que deshacer en datos; las imágenes nuevas se pueden borrar con `docker rmi nba-motor:df8a151 nba-captura:408ea38`.

### 2026-11-03 00:10 UTC · NBA: dato `equipo_del_jugador` (imagen `nba-captura:3ca6392`) · SOLO `nba-db` y colectores, rama `nba/rediseno-s0`
- Migración `0008_equipo_del_jugador` aplicada a `nba_datos` (métrica 60): con qué equipo figura cada jugador en cada partido; antes la caja por jugador no lo guardaba y no se deduce sin ambigüedad.
- Imagen `nba-captura:3ca6392` construida y puesta en `imagen_actual` (los crons usan el cargador de cdn.nba.com que ya escribe el dato); el código anterior queda en `nba-captura/build/src.antes-3ca6392`.
- Cajas históricas recargadas con el mismo cargador (idempotente: 2.862.878 filas leídas, 166.632 nuevas = una por jugador y partido de 6.414 partidos; nada de lo ya cargado se duplicó). Base de datos 2,29 GB, disco 62 %.
- **Vuelta atrás:** datos solo-anexar; volver a la imagen anterior escribiendo `cdecc6c` en `imagen_actual`. La métrica 60 y sus filas se quedan (no estorban a las demás).
- Pendiente de verificar: la primera caja y jugada a jugada reales de cdn.nba.com (los partidos del 2-nov terminan ≈ 02:00-04:30 UTC del 3-nov); hoy solo se pidió el marcador del día (1 crédito de Scrapfly).

### 2026-11-02 22:45 UTC · NBA: cuotas históricas (bet365, The Odds API) y archivo de PropLine desde el 23-oct en `nba_datos` (imagen `nba-captura:9d73ed5`) · SOLO base de datos y archivos, rama `nba/rediseno-s0`
- Archivos que ya existían en el PC (sin créditos nuevos), copiados a `~/nba-isolated/nba-captura/historico/` con hash verificado: catálogo de 6.414 juegos (`games.json` de nba_extended_box), BetsAPI/bet365 (`odds.jsonl.gz`), props de The Odds API ya enlazadas (`props_linked.jsonl.gz`) y 325 instantáneas de moneyline. Cargados con `captura.py historico` (contenedor de una sola vez, 512 MiB, usuario `nba_captura`).
- Resultado: 1.472.382 cuotas de bet365 (3.857 juegos, 2023-24 a 2025-26, trayectoria completa de ganador, hándicap y total de partido, mitad y 1.er cuarto), 1.755.830 de props (8 casas; puntos, rebotes, triples, asistencias) y 5.016 de Pinnacle. `recibido_en` es el instante en que la casa mostró el precio; la adquisición queda en `nba.captura` con fase `historico` y el hash del archivo.
- Archivo de PropLine desde el 23-oct recorrido con el mismo colector (`propline_historico.sh`, 2.110 recibos, 1.044.764 cuotas nuevas, 0 fallos); es idempotente y omite los recibos ya cargados.
- Migración `0007_cuota_margen_por_contrato` aplicada: la vista `nba.cuota_margen` agrupaba por línea y no emparejaba los dos lados de un hándicap (margen −47 %); ahora agrupa por contrato (bet365 h2h 5,4 %, hándicap 6,6 %, total 6,5 %; Pinnacle 2,8 %).
- Error corregido antes de cargar: en los props históricos la línea no formaba parte del contrato y se perdían 340 mil filas de líneas distintas del mismo jugador y foto; ahora forma parte del contrato.
- Estado: 4,30 millones de cuotas, 1,46 GB; disco del VPS al 61 %. Crons activos y sanos (rotowire, espn, parte, nba, propline); créditos de Scrapfly hoy: 1; capturas fallidas: 21 PDF aún no publicados (403 esperado) y 1 error de red de ESPN.
- Pendiente de verificar: el primer box score y jugada a jugada reales llegan esta noche (≈ 02:00-04:30 UTC).
- **Vuelta atrás:** las cuotas son solo-anexar. Para deshacer solo estas cargas habría que recrear la base desde el respaldo diario anterior (`~/nba-isolated/nba-captura/respaldos`, 7 copias); no hay nada más que revertir. La imagen anterior (`9e9dda0`) sigue en el servidor.

### 2026-11-02 21:15 UTC · NBA: cuotas de PropLine hacia `nba.cuota` (imagen `nba-captura:9e9dda0`) · cron del usuario `qf`, rama `nba/rediseno-s0`
- Colector `propline`: lee el archivo compartido de PropLine (volumen `quantfut_artifacts`, carpeta `propline_shared`) montado **en solo lectura**; no hace peticiones al proveedor ni usa créditos. Verifica el hash de cada objeto contra su recibo y carga los recibos NBA con estado 200 desde el último procesado (la primera pasada empezó por el último slot).
- Cron nuevo (respaldo previo en `~/nba-isolated/nba-captura/crontab.before-cuotas-20261102`): `20 * * * *` (el archivo se escribe a :07). Se cargan 4 casas (Pinnacle, DraftKings, FanDuel, BetMGM) y los mercados ganador, hándicap, total, total de equipo, puntos, rebotes, asistencias, triples, robos, tapones, combinados, doble/triple-doble y primer anotador, líneas principales y alternativas (los «milestone» quedan fuera). Solo se guarda una fila cuando cambia el precio o la línea; `fase = cierre` si faltan ≤ 60 min para el salto. Juegos en vivo o a más de 48 h se ignoran.
- Primera pasada: 7 recibos, 19.512 cuotas en 7 s, 15 partidos. Márgenes implícitos de Pinnacle (principales, 2 lados): ganador 2,9 %, hándicap 2,6 %, total 3,1 %, total de equipo 3,8 %, puntos y asistencias de jugador ≈ 7,0 %, en línea con lo medido en la literatura.
- Jugadores: ahora hay 470 canónicos, 12 marcados ambiguos (mismo nombre en distintos ids), 331 unidos entre dos o más fuentes; el id `nba:NNNN` de PropLine es el mismo `personId` de cdn.nba.com.
- Sin tocar: archivo de PropLine (lectura), contenedores previos, base de fútbol.
- **Vuelta atrás:** `crontab ~/nba-isolated/nba-captura/crontab.before-cuotas-20261102`; las cuotas cargadas son solo-anexar.

### 2026-11-02 20:50 UTC · NBA: parte oficial de lesiones (PDF) y final del partido (cdn.nba.com) hacia `nba_datos` (imagen `nba-captura:3b2335c`) · cron del usuario `qf`, rama `nba/rediseno-s0`
- Migración `0006_metricas_parte_oficial_y_final` aplicada con el ejecutor (3 métricas: `motivo_disponibilidad`, `reporte_no_enviado`, `jugo`). Imagen nueva con `pdfplumber==0.11.9`; `imagen_actual` apunta a `3b2335c`.
- Cron nuevo (2 líneas, respaldo previo en `~/nba-isolated/nba-captura/crontab.before-s1b-20261102`): `*/15` `parte` (PDF oficial, directo y gratis desde el VPS; el CDN responde 403 mientras el PDF de esa hora no existe) y `*/15` `nba` (final del partido por Scrapfly con ASP, ≈1 crédito por archivo, **tope 25 créditos por día UTC** en `NBA_SCRAPFLY_TOPE_DIARIO`; como mucho 2 intentos por archivo; marcador del día una vez desde las 10:00 ET; box score de cada final 10 min después de que ESPN lo dé por final; jugada a jugada con lo que quede de presupuesto). `SCRAPFLY_API_KEY` se copió de la configuración del scraper del VPS a `captura.env` (modo 600).
- Créditos gastados hoy: 3 (muestras para escribir el adaptador) + 1 (marcador del día). Saldo de Scrapfly al medir: 672 de 1.000 hasta el 30-nov.
- Primera captura real del parte: 2 PDF (1:30 y 2:30 PM ET), 232 filas. El marcador del día dio los 15 id reales de la NBA; todos se asocian a su juego por fecha y equipos.
- Error corregido durante el despliegue: la primera versión creó 15 partidos canónicos duplicados con el id de la NBA (la regla «una fuente, un alias» chocaba con el id sintético del PDF). La evidencia no se borra: esos 15 registros quedan inertes (sin datos) y la nueva lógica une cada juego por (fecha ET, local, visitante) y siempre usa el canónico más antiguo.
- Sin verificar todavía de extremo a extremo: la captura de un box score y jugada a jugada reales (las pruebas usan muestras reales de cdn, pero el primer final de hoy ocurre esta noche, ≈ 02:00-04:30 UTC).
- Sin tocar: contenedores previos, `run57` (solo lectura), base de fútbol.
- **Vuelta atrás:** `crontab ~/nba-isolated/nba-captura/crontab.before-s1b-20261102` (quita las dos líneas); los datos cargados son solo-anexar.

### 2026-11-02 20:00 UTC · NBA: capturas Rotowire y ESPN hacia `nba_datos` (imagen `nba-captura:8bfe3c6`) · cron del usuario `qf`, rama `nba/rediseno-s0`
- Imagen `nba-captura:8bfe3c6` (Python 3.12 slim, usuario 1001, `--read-only`, sin capacidades, 256 MiB, red `nba-red`) construida en `~/nba-isolated/nba-captura/build` desde el código de la rama; `imagen_actual` apunta a ella. Las tres imágenes de la jornada (`fb397c8`, `71d2ff9`, `8bfe3c6`) siguen en el servidor.
- Usuario de base `nba_captura` (LOGIN, miembro de `nba_escritor`: solo INSERT). Su contraseña y `ZENROWS_API_KEY` (copiada de la configuración del scraper, tope `NBA_ZENROWS_TOPE_DIARIO=30`) están solo en `captura.env` (modo 600).
- Cron nuevo (3 líneas, respaldo previo en `~/nba-isolated/nba-captura/crontab.before-20261102`): `*/30` Rotowire, `*/15` ESPN (lee el ledger de `run57` en solo lectura) y `15 9` respaldo diario con `pg_dump -Fc` (7 conservados). Registro en `~/.local/share/quantfut/nba_captura.log`.
- Carga inicial: 10.177 recibos de `run57` (8-oct a 2-nov) en lotes de 200, 22.493 filas, 156 partidos, 433 jugadores canónicos, 0 ambiguos, 0 conflictos; 1ª captura de Rotowire: 15 partidos, 1.599 filas. Los ciclos de cron de las 19:45 y 20:00 se ejecutaron solos y ESPN tomó el recibo nuevo (seq 10178).
- Hallazgo: Rotowire solo da gratis los minutos proyectados del equipo visitante (los del local devuelven «debes ser suscriptor»); el colector pide solo los visitantes y no rodea la restricción.
- Respaldo probado: `pg_restore` a una base temporal dio los mismos conteos (22.493 / 931 / 3.019); copia fuera del VPS en `Documentsespaldos_nba` del PC del titular con `scripts/respaldo_nba_vps.ps1` (a mano; sin tarea programada).
- Sin tocar: los 8 contenedores previos conservan nombre, id e imagen; `run57` solo se lee. No se escribió ni leyó la base de fútbol.
- **Vuelta atrás:** `crontab ~/nba-isolated/nba-captura/crontab.before-20261102` (quita las líneas NBA); `docker rmi` de las imágenes y borrar `~/nba-isolated/nba-captura` si se quiere deshacer todo. Los datos ya cargados son solo-anexar y se quedan en `nba_datos`.

### 2026-11-02 19:45 UTC · NBA: base propia `nba_datos` (contenedor `nba-db`, vacía) · SOLO host y contenedor nuevo, rama `nba/rediseno-s0` (`e29e746`)
- Contenedor `nba-db` (`postgres:16-alpine`, sin puerto publicado, 512 MiB, `restart: unless-stopped`) en el proyecto Compose `nba-db`, red `nba-red` y volumen `nba_db_datos`; base `nba_datos`, usuario administrador `nba_admin`. Archivos en `~/nba-isolated/nba-db/` (`apps/nba/{ops/nba-db,db,src}` con los mismos hashes que el repositorio; `.env` y `migrar.env` con la contraseña, modo 600, solo en el servidor).
- Migraciones 0001-0005 aplicadas con `python -m nba.v2.migrar` desde un contenedor temporal `python:3.12-slim` en `nba-red`: 7 tablas `nba.*`, 9 fuentes, 34 métricas, `nba.dato_a_las`, roles de grupo `nba_escritor` y `nba_lector`. Verificado en el servidor: `DELETE`/`TRUNCATE ... CASCADE` rechazados por los disparadores, `dato_a_las(now())` devuelve 0 filas, 0 puertos publicados.
- Sin tocar: los 8 contenedores que ya corrían conservan nombre, id e imagen (api, worker, db, cache, caddy, grafana, dashboard NBA, capture, propline). No se leyó ni se escribió la base de fútbol.
- Pendiente: usuarios de login para colectores y API (S1), respaldo diario de `nba_datos` fuera del VPS (la base está vacía; añadirlo antes de cargar datos).
- **Vuelta atrás:** `cd ~/nba-isolated/nba-db/apps/nba/ops/nba-db && docker compose --env-file ~/nba-isolated/nba-db/.env -p nba-db -f compose.yml down` (conserva el volumen); para borrar la base añadir `-v`. No hay nada más que revertir.

### 2026-10-21 · AdMob (ID de editor y bloque) y estado de Meta · SOLO configuración en la base, sin código ni reinicios
- `reward_settings` (vía `qf.api.anuncios.save_config`, auditado como `ssh:claude-titular`): `admob_publisher_id = pub-3902371555866850` y
  `ad_unit_android = ca-app-pub-3902371555866850/4169479093` (bloque Recompensado, SSV con `https://pronosticosdeportivos.pro/rewards/callback/admob`).
  Siguen `ads_enabled = true` y `ad_test_mode = true`: la app muestra bloques de prueba de Google.
- `GET /app-ads.txt` ya responde `google.com, pub-3902371555866850, DIRECT, f08c47fec0942fa0` (antes 404). AdMob tarda hasta 24 h en verificar la app.
- Comprobado por SSH: `META_PIXEL_ID`, `META_DATASET_ID`, `META_CAPI_TOKEN` definidos y `META_CAPI_ENABLED=1`; sin `META_TEST_EVENT_CODE`. El código de Whop y de Meta web
  del contenedor API es el de `main`, salvo `meta_capi.py` (el de la API no trae el extinfo de reserva; el del worker sí, y es el que envía). Cola `meta_events`: 1 `CompleteRegistration` enviado, ninguna compra aún.
- App de Meta (ID `1369265108354712`): plataforma Android con paquete y clase, tres hashes de clave y registro automático de compras apagado; app vinculada al dataset `2253839992227148`.
- Cambio de código aparte: #67 (ID de app de AdMob de Android en el manifiesto). iOS conserva el ID de ejemplo hasta registrar esa app en AdMob.
- **Vuelta atrás:** vaciar `admob_publisher_id` y `ad_unit_android` en `/control/anuncios` (la ruta vuelve a 404).

### 2026-10-21 17:05 UTC · Web: arreglo del arranque (la web quedaba en «Consultando…») · API (imagen nueva), commit `45fdb96`
- Causa: `app.js` llamaba a `render()` antes de declarar `publicAuthKey`/`publicFetch` (zona muerta temporal): ReferenceError en el primer render, el script abortaba y nunca cargaba los datos públicos. Se mueven las declaraciones antes del primer `render()` y `app-order.test.mjs` lo exige.
- Imagen `quantfut-api-web-vip:web-arranque` = `web-renovacion` + `frontend/{app.js,index.html}` (hash de ambos comprobado contra `main` previo antes de sobrescribir). `index.html` lleva el sello nuevo `app.js?v=935045b8a991`: sin re-sellar, Cloudflare sirve el script viejo bajo la URL con el sello anterior. Compose fijado; worker, base y Caddy sin tocar.
- Verificado: `/health` 200, `/` referencia `app.js?v=935045b8a991` (hash servido igual al de `main`), la pestaña Escalera carga retos e historial reales.
- Vuelta atrás: `releases/web-arranque/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` + `docker compose up -d --no-deps --no-build --force-recreate api`.

### 2026-10-21 16:43 UTC · NBA: productor diario de cohortes v1.3 · cron del usuario `qf` (PR #66)
- Imagen `nba-live13-producer:20261021` (`7a77272bba60`), derivada de `nba-dashboard-live13:20261021` + `pdfplumber==0.11.9`; envoltorio `~/nba-isolated/live13/producer.sh` (`flock`, solo un proceso, contenedor de solo lectura salvo `cohorts`, 512 MB, sin credenciales). Datos y modelo en `~/nba-isolated/live13/{data,model}`; cohortes en `~/nba-isolated/live13/cohorts` (el dashboard las monta de solo lectura).
- Cron nuevo: `*/10 * * * * /home/qf/nba-isolated/live13/producer.sh >> ~/.local/share/quantfut/nba_live13.log 2>&1`. Cada pasada recoge los resultados finales (≥3 h tras el salto) y, desde las 17:35 ET, sella una vez por fecha los partidos que no han empezado. Primera ejecución manual 16:43 UTC y primera por cron 16:50 UTC: sin errores, sin sellar (aún antes de las 17:35 ET).
- Cohorte `2026-10-21_ensayo` (11 partidos, 44 pronósticos, sellada 14:39 UTC con el reporte de las 10:30 ET) copiada a mano al servidor; el ensayo en seco del productor (carpeta de pruebas, ya borrada) selló lo mismo con el reporte de las 11:45 ET y aceptó el hash del modelo.
- Sin tocar: API, worker, caddy, db, cache, grafana, capture, paper-pilot, ni el resto del crontab (tenis, firebase).
- **Vuelta atrás:** `crontab ~/nba-isolated/live13/crontab.before-20261021` (copia del crontab anterior) o borrar solo la línea del productor; las cohortes selladas se quedan y el dashboard sigue igual.

### 2026-10-21 15:45 UTC · NBA: pronósticos prospectivos v1.3 en /nba · contenedor del dashboard NBA, `main` (`f99fdaf`, PR #63)
- Imagen `nba-dashboard-live13:20261021` (`8810415bb98e`), derivada de `nba-dashboard-run71:20261009`: solo cambia `src/nba`, `web` y el `CMD` (`nba.multimarket_live_dashboard`); mismo `public-bundle` de RUN071. Nuevo montaje de solo lectura `~/nba-isolated/live13/cohorts` en `/live-cohorts`. Mismos límites y montajes que antes (read-only, usuario 1001, sin capacidades, 256 MB, sin credenciales).
- Ensayo previo con un contenedor temporal (RUN071: 42 + 15 pronósticos; cohorte v1.3: 44). Tras el cambio: `/`, `/nba`, `/nba/app.js` 200, `/nba/.env` 404; la página muestra RUN071 intacto y la cohorte `2026-10-21_ensayo` (11 partidos sellados 14:39 UTC); consola sin errores propios. Los demás contenedores conservan su ID (API, worker, caddy, db, cache, grafana, capture, paper-pilot); Caddy sin cambios (sigue apuntando a `nba-dashboard-run69`).
- **Sin productor aún:** nadie sella cohortes nuevas ni recoge resultados en el servidor; la cohorte se copió a mano. Pendiente decidir dónde corre (el servidor sí llega a nba.com y a los PDF de lesiones, comprobado).
- Respaldo: `~/nba-isolated/dashboard/live13-20261021/backup/` (inspect del contenedor, ID de la imagen, lista de contenedores). El contenedor anterior quedó parado como `nba-dashboard-run71-prev` (restart=no).
- **Vuelta atrás:** `docker rm -f nba-dashboard-run69 && docker rename nba-dashboard-run71-prev nba-dashboard-run69 && docker update --restart unless-stopped nba-dashboard-run69 && docker start nba-dashboard-run69`.

### 2026-10-20 03:55 UTC · Motor de tenis al VPS (servicio nuevo, aislado del fútbol) · imagen `quantfut-tenis:1d2067d` + crontab de `qf`, PR #53 y #54 (`205f62b`)
- Orden del titular («haz lo que queda»): sacar el tenis del PC para que no dependa de que esté encendido. **No toca ningún servicio de fútbol**: ni contenedores, ni compose, ni el crontab del worker, ni la base.
- Imagen propia `quantfut-tenis:1d2067d` construida en el servidor desde `git archive` de `apps/tennis` (`apps/tennis/Dockerfile`, `python:3.12-slim`). El código Python de la imagen es idéntico al de `main` (`205f62b` solo cambia el script del host). Datos en `~/quantfut-tenis/data` (221 MB: base semanal, modelos, parámetros, registros de cuotas y de la entrada automática traídos del PC), claves en `~/quantfut-tenis/secrets` (700/600: `ODDS_API_KEY` y `API_TENNIS_KEY`), imagen activa en `~/quantfut-tenis/IMAGE`.
- Crontab de `qf` (hora del servidor, Europe/Berlin): `30 0,12 * * * ~/quantfut-tenis/vps_run.sh twice-daily` (foto h2h + entrada; una por media jornada UTC, también con horario de invierno) y `0 11 * * 1 ~/quantfut-tenis/vps_run.sh weekly`. Respaldo previo: `~/quantfut-tenis/backup/crontab_qf_antes_20261020.txt`.
- Verificado: entrada en seco dentro del contenedor (34 ya sellados, sin duplicar), `tennis_motor forecast` con foto de cuotas, y la tarea semanal lanzada por el mismo script (0 descargas, 171 reutilizados, base al 20-oct, reentreno y promoción de `motor_config.json`; archivos a nombre de `qf`).
- En el PC, las tareas de Windows «QuantFut tenis cuotas h2h» y «QuantFut tenis datos semanales» quedan **desactivadas** (no borradas) para no duplicar llamadas ni sellos.
- Vuelta atrás: `crontab ~/quantfut-tenis/backup/crontab_qf_antes_20261020.txt` y reactivar las dos tareas de Windows; los datos del PC en `data/tennis/{intake_v1,live_odds_v1,weekly}` se quedaron como estaban a las 03:50 UTC (para volver, copiar antes los del servidor hacia el PC).

### 2026-10-21 13:19 UTC · Web: los planes de Whop se renuevan solos y el texto lo dice antes de pagar · API (imagen nueva), PR #58 (`466a141`)
- El titular confirmó (21-oct) que los planes de Whop se renuevan automáticamente; la web decía lo contrario (preguntas frecuentes: «No… no hay cobros recurrentes»; cuenta: «Sin renovación automática»). Ahora las preguntas frecuentes, la sección de cuenta, el resumen del pedido y la sección de pago informan de que se renueva al terminar cada periodo, al mismo precio, hasta cancelar la renovación desde la cuenta de Whop. El titular confirmó el 21-oct que la renovación se cancela desde Whop; falta solo la revisión legal del texto.
- Imagen `quantfut-api-web-vip:web-renovacion` = `web-copy-pago` + `frontend/{app.js,membership.js,index.html}`; el script de despliegue comprobó el hash de los tres antes de sobrescribir. Verificado: `/health` 200, `/` referencia `app.js?v=d4f8a8a02038` y el `membership.js` versionado trae el texto nuevo.
- Nota: el job «tenis» del CI falló ese día por una prueba de `apps/tennis` que depende de la fecha (ajena a este cambio; marcada como tarea aparte). El arnés principal («arnes») pasó.
- Vuelta atrás: `releases/web-renovacion/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` + `docker compose up -d --no-deps --no-build --force-recreate api`.

### 2026-10-20 04:51 UTC · Web: los textos de pago siguen la configuración del servidor · API (imagen nueva), PR #56 (`375c720`)
- Whop está habilitado en producción (`/app/v1/whop/config` devuelve `enabled: true`, los tres planes tienen `whop_plan_id`), pero la web decía en tres sitios (planes, paquetes, preguntas y cuenta) que el pago en línea todavía no estaba habilitado. Ahora `membership.js` usa `payOn()` (la configuración del servidor) y se vuelve a pintar al cargarla. No se añade ninguna afirmación nueva sobre renovaciones.
- Archivos idénticos a lo esperado antes de sobrescribir (hash comprobado por el propio script de despliegue): `frontend/{app.js,membership.js,index.html}`. Imagen `quantfut-api-web-vip:web-copy-pago` = `a1a8dcd` + esos 3 archivos; compose fijado. Worker, base y Caddy sin tocar.
- Verificado: `/health` 200; `/` referencia `app.js?v=beb802cbd502` y este `membership.js?v=0b23a539278e` (hash del servidor coincide). La URL sin versión de `membership.js` sigue en la caché de Cloudflare, pero la página no la usa.
- Vuelta atrás: `releases/web-copy-pago/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` + `docker compose up -d --no-deps --no-build --force-recreate api`.

### 2026-10-20 03:00 UTC · Artefacto del ajuste del once reajustado con la muestra ampliada · worker (solo un archivo de datos)
- `ajuste_xi_ampliado-2024-01-01_2026-10-19.pkl` (11.920 partidos) en `/srv/quantfut/artifacts`; `calcular` carga el más reciente, así que desde ahora los factores en sombra usan este y quedan marcados con `oos_version = ampliado-...`. Sin cambios de código, sin tocar los lambdas sellados. Vuelta atrás: borrar ese archivo (vuelve al de `2026.10.19-131830`).

### 2026-10-20 01:08 UTC · Captura extra de FotMob a T-30 y sello sin once oficial a T-25 · worker (2 archivos, `docker cp`) + crontab, PR #47 (`9811b7c`)
- Orden del titular (opción 2: captura extra a T-30). Solo ~56 % de los partidos traían el once oficial a T-45 (primer sello real, 19-oct 23:40 UTC: `sin once oficial`). Nueva ventana de captura `tarde` (~T-33 a T-28), que se solapa con `cierre` (cada pasada toma la primera pendiente), y el cron de `previos` pasa de cada 15 a cada 5 min (solo pide a FotMob si hay una ventana pendiente: ~25 % más de peticiones por partido). Sin once oficial, el sello por partido espera hasta T-25 (antes T-38).
- Archivos idénticos a `main` previo antes de copiar: `ingest/fotmob_captura.py`, `publish/sello_tardio.py`. Solo cambió la línea de `previos` del crontab. Sin reinicio: el walk-forward ampliado siguió corriendo (segundo trozo terminado).
- Las pruebas del job diario dejaban de pasar al cambiar la fecha (el corte del sello por partido es 2026-10-20): se fijó el corte en None en esas pruebas y se añadió una que comprueba que con el corte activo el diario no crea picks.
- Vuelta atrás: copiar de vuelta `releases/captura-tarde-t30/backup/*` y cargar `backup/crontab_worker.txt`.

### 2026-10-19 22:06 UTC · El lote de partido lleva el factor del once · worker (2 archivos, `docker cp`) + crontab, PR #44 (`f466d94`)
- Orden del titular («sí, despliega»), antes del primer sello real. `hashchain._collect_partido` ahora incluye `sello_tardio` (disparo, minutos al saque y `ajuste_xi`) en el JSON sellado: así el factor se puede verificar por terceros al revelarse el lote. Aún no había ningún lote de partido, así que no cambia ningún hash existente. `ajuste_xi --avisar` y su cron diario (07:30 UTC) avisan una sola vez al llegar a 150 partidos con efecto.
- Archivos idénticos a `main` previo antes de copiar. Sin reinicio: el walk-forward ampliado siguió corriendo. Verificado: importa, `hashchain verify` OK con 21 lotes, `--medir` responde.
- Vuelta atrás: copiar de vuelta `releases/sello-factor-f466d94/backup/*` y cargar `backup/crontab_worker.txt`. Un lote de partido ya sellado conserva su formato.

### 2026-10-19 19:20 UTC · Ajuste del once en MODO SOMBRA y sello por partido ACTIVO desde el 20-oct · worker (5 archivos, `docker cp`) + API (imagen nueva) + crontab, PR #42 (`a1a8dcd`)
- Orden del titular (confirmó el modo sombra, el corte y el walk-forward ampliado). **`LOTE_POR_PARTIDO_DESDE = 2026-10-20`**: desde el 20-oct 00:00 UTC cada partido con predicción diaria se predice de nuevo (etapa `final`) y se sella solo, con las dos alineaciones capturadas (≤ 90 min) o a T-38 (T-45 menos 7 min de gracia, porque la captura de FotMob de T-45 corre en el mismo minuto). El lote diario de las 09:00 UTC sigue igual.
- **Ajuste del once** (`model/ajuste_xi.py`, bloque `epi_total`): calcula el factor y lo anota en `data_completeness.sello_tardio.ajuste_xi`; **no cambia los lambdas**. Artefacto `ajuste_xi_2026.10.19-131830.pkl` (4.255 partidos). El once sale de la captura oficial de FotMob (`tipo_alineacion='standard'`). Medición hacia adelante: `python -m qf.model.ajuste_xi --medir`.
- Archivos: worker `model/{jugadores,ajuste_xi}.py`, `config.py`, `publish/{sello_tardio,hashchain}.py` (idénticos a `main` previo antes de copiar). API: imagen `quantfut-api-web-vip:a1a8dcd` = `07c12bc` + `api/main.py` (`/chain` añade `batch_kind` y `match_id`), `config.py`, `hashchain.py`, `jugadores.py`, `ajuste_xi.py`, `sello_tardio.py`. Crontab recargado: solo se añade `estado_xi` cada hora (el job de sello ya estaba).
- Verificado: `/health` 200; `/chain` lleva `batch_kind`; `hashchain verify` OK con 21 lotes; `calcular` sobre 6 partidos reales con once oficial; el estado se reconstruye en ~2 min (17.332 jugadores, 495 equipos). El primer sello real será el de un partido del 20-oct.
- Vuelta atrás: poner `LOTE_POR_PARTIDO_DESDE = None` en `hashchain.py` del worker (apaga el sello por partido sin tocar nada más); o restaurar `releases/f7-sombra-a1a8dcd/backup/*` y el compose previo. Los lotes de partido ya sellados quedan en la cadena (inmutable).

### 2026-10-19 UTC · Impacto por jugador (solo medición) · worker (2 archivos, `docker cp`), PR #40 (`3284e6c`)
- `model/jugadores.py` (nuevo) y `model/contexto.py` copiados al worker para poder medir los bloques `epi_*`. No los usa ningún job ni cron: no cambia el modelo, ni lo sellado, ni la API. `contexto.py` era idéntico a `main` previo a #40.
- Verificado: importa junto con `daily`; `hashchain verify` OK con 21 lotes. Vuelta atrás: copiar de vuelta `releases/jugadores-3284e6c/backup/contexto.py` y borrar `jugadores.py`.

### 2026-10-19 13:15 UTC · F7 sello tardío por partido (APAGADO) · migración 084 + worker (8 archivos, `docker cp`) + API (imagen nueva) + crontab, PR #38 (`07c12bc`)
- Orden del titular («hazlo»). **El corte `LOTE_POR_PARTIDO_DESDE` sigue en `None`**: el job `sello_tardio` corre cada 5 min pero responde `apagado`, y el lote diario no cambia. Falta fijar el corte (decisión aparte, tras el reentrenamiento).
- **Migración `db/084`** aplicada a producción (transacción con `lock_timeout 5s`): `predictions.etapa` (387 filas `diaria`), `prediction_batches.batch_kind`/`match_id` (21 lotes `diario`) y sus restricciones. Aditiva: el código anterior la ignora.
- Antes de sobrescribir: los 7 archivos del worker eran idénticos a `main` previo a #38; en la API eran versiones anteriores (se llevan a `main`).
- **Worker:** `model/{lineup_challenger,shadow}.py`, `publish/{alta_prob_datos,daily,escalera_datos,hashchain,parley_datos,sello_tardio}.py`. **API:** imagen `quantfut-api-web-vip:07c12bc` = `8be381b` + esos archivos; compose fijado. **Crontab** recargado por stdin: solo se añadió la línea de `sello_tardio` (el resto igual, solo reordenado).
- Verificado: `/health` 200; `/alta-probabilidad` activa; `hashchain verify` OK con 21 lotes; el lote de las 09:00 UTC de hoy (sellado con el código anterior) lleva `ajuste_altitud` en las 9 predicciones.
- Vuelta atrás: restaurar `releases/f7-sello-07c12bc/backup/docker-compose.before.yml` + `up -d --no-deps --no-build --force-recreate api`; copiar de vuelta `backup/worker_*.py` y cargar `backup/crontab_worker.txt`. La migración se deja (aditiva); esquema previo en `backup/esquema_antes.sql`.

### 2026-10-19 UTC · Motor B medido por partido (control del «fallo grosero») · worker (3 archivos, `docker cp`) + API (imagen nueva), PR #36 (`8be381b`)
- Orden del titular. Sin migración. Los lotes ya sellados no cambian: solo cambia cómo el control de alta probabilidad mide el acierto (varianza por partido, la mayor de las dos) y lo que muestra el historial (`partidos`, `margen_ee` por mercado).
- Antes de sobrescribir: los 3 `publish/alta_prob*.py` del worker eran idénticos a `main` previo a #36; en la API eran una versión anterior (se llevan a `main`), y `frontend/app.js` e `index.html` eran idénticos.
- **Worker:** `alta_prob.py`, `alta_prob_datos.py`, `alta_prob_ext.py` copiados con `docker cp` (se pierden al recrear el worker; ya están en `main`). Sin reinicio ni cambio de cron.
- **API:** imagen `quantfut-api-web-vip:8be381b` = la anterior + esos 3 archivos + `frontend/app.js` + `frontend/index.html`. Ensayo previo en contenedor aparte (importa bien, 118 rutas). Compose fijado en ella.
- Verificado en el dominio real: `/health` 200; `app.js` servido con el hash de `main`; `/alta-probabilidad` devuelve `partidos` y `margen_ee` por mercado.
- Vuelta atrás: `releases/b-por-partido-8be381b/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` + `docker compose up -d --no-deps --no-build --force-recreate api`; para el worker, copiar de vuelta `backup/worker_*.py`.

### 2026-10-19 04:07 UTC · Herramienta de diagnóstico de córners · worker (un archivo nuevo, `docker cp`)
- `eval/corners_diagnostico.py` copiado al worker para ejecutarlo contra la base (solo lectura). No lo importa ningún job ni cron; no
  cambia el modelo ni lo publicado. Vuelta atrás: borrar el archivo del contenedor. Detalle: `docs/corners_diagnostico_20261019.md`.

### 2026-10-19 02:12 UTC · Altitud en el motor A en MODO SOMBRA · worker (4 archivos, `docker cp`), sin reinicio
- Orden del titular: que la información nueva entre a los motores. Se midió cada bloque (docs/contexto_en_el_motor_20261019.md): solo
  la altitud pasa la puerta, con evidencia débil; clima, descanso, bajas y valor del once no mejoran el modelo. La altitud entra en
  **modo sombra**: calcula el factor y lo anota en cada predicción, **sin cambiar los lambdas publicados**.
- Archivos (idénticos a `main` antes de copiar, `daily.py` y `config.py`; los otros dos son nuevos): `publish/daily.py`, `config.py`,
  `model/contexto.py`, `model/ajuste_altitud.py`. Originales de los dos que existían en `releases/contexto-altitud/antes/`.
  Vuelta atrás: copiar de vuelta `daily.py` y `config.py` desde esa carpeta (los dos módulos nuevos quedan sin uso).
- Artefacto `ajuste_altitud_2026.10.12-221104.pkl` en `/srv/quantfut/artifacts`. Sin migración, sin cambios en el cron.
- Modo por `AJUSTE_ALTITUD_MODO` (`off`, `sombra` por defecto, `activo`); el worker en marcha no tiene la variable, así que usa `sombra`.
- Verificado: simulación de solo lectura sobre los 145 partidos modelados de los próximos 8 días (35 con efecto > 0,5 %, lambdas
  intactos en todos). El primer sellado con el código nuevo es el de las 08:00 UTC: comprobarlo mañana (`data_completeness.ajuste_altitud`
  presente y lambdas iguales a los de antes). Modelo activo, API y base sin cambios.

### 2026-10-19 01:45 UTC · Web: bloqueados difuminados, un gratis por sección y VIP ve todo · API (7 archivos), PR #31 (`5f21e93`)
- Orden del titular («si hazlo»). Sin migración. La app móvil no se toca y sus rutas (`/mobile/v1/*`) no cambian.
- Antes de sobrescribir se comprobó que los 7 archivos eran idénticos a `origin/main` dentro de `quantfut-api-meta-web:db24a88`:
  `frontend/{app,cuenta-api,membership,public-data}.js`, `frontend/{index.html,styles.css}` y `src/qf/api/main.py`.
- **API:** imagen `quantfut-api-web-vip:5f21e93` = la anterior + esos 7 archivos (ensayo en contenedor aparte: 118 rutas en las dos;
  los hashes de la imagen coinciden con los fusionados). Compose fijado en ella. Worker, base de datos y Caddy sin tocar.
- Qué cambia para el usuario: en la web, los pronósticos bloqueados salen difuminados (cuota incluida) con «Acceso VIP» a Suscripciones;
  el visitante ve **un** gratis por sección (alta probabilidad pasa de 4 a 1); una cuenta VIP ve todos (`/alta-probabilidad` y `/escalera`
  usan `member`, como `/parley`); parley bloqueado ya no rompe la vista.
- Verificado en el dominio real: `/health`, `/`, `app.js`, `public-data.js`, `styles.css`, `membership.js` y `cuenta-api.js` responden 200;
  `/alta-probabilidad` lleva `Cache-Control: no-store` y `Vary: Authorization`; con un token falso responde 401 (la web cae a visitante).
  **No se pudo comprobar con datos en vivo** el reparto 1 visible / resto bloqueado ni lo que ve una cuenta VIP: a la 01:45 UTC no hay
  pronósticos abiertos (alta probabilidad 0, escalera sin bloqueados) porque el lote llega a las 08:00 UTC. Repetir la comprobación
  después de ese lote, y probar con una cuenta con suscripción real.
- Vuelta atrás: restaurar `releases/web-vip-5f21e93/backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` y
  `docker compose up -d --no-deps --no-build --force-recreate api` (la imagen anterior sigue en el servidor).
  Respaldo de los 7 archivos previos en `releases/web-vip-5f21e93/backup/archivos-antes.tar`.

### 2026-10-18 · ERA5 automático diario · worker (entorno) + cron
- Orden del titular: conservar el token de Copernicus para la descarga automática. Cron nuevo `20 6 * * *` (06:20 UTC)
  `flock -n /tmp/era5.lock python -m qf.ingest.era5_clima` (incremental; pide solo lo que los archivos guardados no cubren).
- El worker en marcha no tenía `CDS_API_TOKEN` (el entorno de cron sale de `/etc/environment`, que se vuelca del `.env` solo al
  arrancar el contenedor). Se añadió la línea a `/etc/environment` **dentro del contenedor** (parche que se pierde al recrearlo).
  Al recrear el worker el 1-nov no hace falta repetirlo: `docker-compose.yml` usa `env_file: .env`, que ya contiene el token.
- Crontab cargado con `cat scripts/crontab | docker compose exec -T worker crontab -` y comprobado (5 líneas de FotMob, sedes y calendario
  más la de ERA5). Respaldo previo: `~/backups/crontab_pre_era5_20261018`. Vuelta atrás: restaurarlo y recargar.

### 2026-10-18 · Meta CAPI: extinfo de reserva válido · worker (un archivo, `docker cp`), PR #29
- `src/qf/comercial/meta_capi.py` copiado al contenedor worker. Antes de copiar se comprobó que era idéntico a `main`
  (`56864d212f2e`); después `37a5cb600a7f` (el del PR). Respaldo: `~/quantfut/deployments/meta-extinfo-20261018/meta_capi.py.antes`.
  **Es un parche del contenedor, no de la imagen:** se pierde si el worker se recrea hasta que el PR #29 esté en `main` y la imagen se reconstruya.
- Causa: Meta responde 400 (subcódigo 2804043) si `extinfo` no lleva versión del SO válida. Una cuenta sin dispositivo registrado
  habría fallado en su `Purchase`/`Subscribe`.
- **Incidente de la prueba (reconocido):** al validar se enviaron **2 eventos `Purchase` de prueba (4,99 USD, correo `prueba@quantfut.invalid`,
  `event_id` `test:var-1-*` y `test:var-2-*`) que Meta PROCESÓ en el dataset de producción**: el `test_event_code` TEST3656 solo desvía los
  eventos mientras la página «Probar eventos» tiene una sesión activa, y no la tenía. No se pueden borrar desde la API; no coinciden con ningún
  usuario real, así que su efecto en atribución es mínimo. Otros 2 intentos fallaron con 400 y no se registraron.
- Estado del worker tras recrearse (otra sesión, 21:58 UTC): sin `/app/meta.env`; usa el `.env` del servidor. Token verificado (dataset HTTP 200),
  `META_TEST_EVENT_CODE=TEST3656` presente.
- **Vuelta atrás:** `docker cp ~/quantfut/deployments/meta-extinfo-20261018/meta_capi.py.antes quantfut-worker-1:/app/src/qf/comercial/meta_capi.py`.
### 2026-10-18 · Token de Conversions API de Meta (usuario del sistema `quantfut-capi`) · SOLO configuración
- Sin código ni imágenes nuevas. En Business Manager («Simulador Ceneval») se creó el usuario del sistema `quantfut-capi`
  (rol Empleado) con acceso parcial al dataset QuantFut y un token con `ads_management`, sin caducidad.
- Token verificado contra Meta: consulta del dataset `2253839992227148` con HTTP 200. El token anterior del worker (205 caracteres)
  daba «Missing Permission» en esa misma consulta.
- Cambiado en dos sitios: `~/quantfut/.env` (copia previa `~/backups/env.pre-meta-token-20261018`) y `/app/meta.env` del contenedor
  worker (copia previa `/app/meta.env.bak-20261018`, dentro del contenedor; se pierde si el worker se recrea, igual que el propio `meta.env`).
  No se recreó ningún contenedor.
- Una pasada de `qf.comercial.meta_capi` tras el cambio: 0 enviados, 0 fallidos (cola vacía).
- **Pendiente:** `META_TEST_EVENT_CODE` sigue vacío, así que los primeros eventos reales irán al dataset de producción. Poner el código
  de «Probar eventos» antes de la primera compra de prueba si se quiere validar sin contar en producción.
- **Vuelta atrás:** en el worker, `cp /app/meta.env.bak-20261018 /app/meta.env`; en el servidor, restaurar `~/backups/env.pre-meta-token-20261018` sobre `.env`.
### 2026-10-18 22:10 UTC · Worker recreado desde `main` y registro público activado · worker
- Orden del titular. Imagen `quantfut-worker:candidato-d2d2735` (construida desde `main` tras los PR #25 y #27 con `git archive` en `~/quantfut/releases/worker-d2d2735`), `latest` = esa imagen. Antes de recrear: sin procesos en el worker.
- **Ensayo** (`scripts/ensayo_worker.py`, worker actual frente a candidata): 0 módulos con error, 25/25 entradas del cron importables, `verify` OK en 20 lotes, conjunto de entrenamiento idéntico (49.450 filas, 46.208 con cierre, huella `44093369780e2f31`). 8 de los 20 lotes no se regeneran desde la base (ya ocurría; ver 15-oct).
- Lo que traía el contenedor viejo como parche (hashchain, módulos de Meta, `sedes.py`, `era5_clima.py`, crontab cargado a mano) ya está en `main`/imagen o en `.env`: comprobado que las variables `META_*` de `/app/meta.env` coinciden con las del `.env` (`env_file`) y que el crontab cargado tiene 127 líneas, como el archivo montado. Archivos de la API distintos a `main` en el worker viejo: solo código que el worker no ejecuta.
- Compose del servidor (worker): `CHAIN_GIT_REMOTE=git@github.com:cerorar23/quantfut-registro.git`, `GIT_SSH_COMMAND` con la llave de despliegue y montaje de solo lectura de `/home/qf/.config/quantfut/registro` en `/run/secrets/registro`. Respaldo en `~/quantfut/deployments/worker-registro-20261018/`.
- Carpeta de la cadena (volumen `quantfut_chain`): `git init`, remoto, `git reset origin/main` (conserva los archivos), usuario local. `git push --dry-run` OK. **Los JSON de los 19 lotes ya terminados se apartaron a `historico_sin_publicar/`** (decisión conservadora: no se publica el histórico sin que el titular lo decida). Sus recibos sí subirán en el primer sellado; `verify` los cuenta como «solo con compromiso» y la cadena sigue OK. Para publicarlos: mover los JSON de vuelta a `/srv/quantfut/chain/`; el siguiente sellado los revela.
- **Prueba del compromiso (18-oct, ~22:40 UTC):** `_git_comprometer` ejecutado a mano en el worker publicó el commit `c34a04a` en `cerorar23/quantfut-registro` con `LEDGER.md` y los 20 recibos; ningún JSON de lote subió. Queda por ver la revelación.
- Primera prueba real: el sellado de las 08:00 UTC del 19-oct (commit de compromiso en el repositorio público) y, tras el último partido del 18-oct, la revelación de su JSON. Vigilarlo.
- Vuelta atrás: `cp ~/quantfut/deployments/worker-registro-20261018/docker-compose.before.yml ~/quantfut/docker-compose.yml && docker tag quantfut-worker:en-ejecucion-20261018 quantfut-worker:latest && docker compose up -d --no-deps --no-build --force-recreate worker`. Sin `CHAIN_GIT_REMOTE`, `seal()` no toca git.

### 2026-10-18 21:25 UTC · Worker alineado con el envío a Meta · worker (2 módulos + cron), sin reiniciar
- Orden del titular. Parche del contenedor con `docker cp` (como F2c y el comprometer-revelar): `comercial/meta_capi.py` y `comercial/meta_datos.py` (los mismos que corre la API = `main`).
  **Es un parche del contenedor, no de la imagen**: se pierde si el worker se recrea. La alineación del 1-nov, construida desde un `main` que ya los incluye, los traerá en la imagen.
- Las variables de Meta (`META_CAPI_ENABLED`, `META_DATASET_ID`, `META_CAPI_TOKEN`; sin código de prueba) viven en `/app/meta.env` dentro del contenedor (600), porque el entorno del worker se fijó al
  crearlo. Al recrearlo con el `.env` actual llegarán por `env_file` y el cron seguirá valiendo (lee el archivo solo si existe).
- Cron: línea `*/5` con `flock` (sustituye en `scripts/crontab` la de Meta que `main` ya traía, que no cargaba entorno). OJO para la próxima sesión: el contenedor veía una copia ANTIGUA del archivo
  montado (otra sesión lo reemplazó con `sed -i`, cambiando el inodo), así que `crontab /etc/cron.d/quantfut` dentro del contenedor recargaba lo viejo; el cron del worker se cargó con
  `docker compose exec -T worker crontab - < scripts/crontab` (127 líneas, idéntico al archivo del host). Comprobado: el worker ejecutó el envío por sí mismo a las 21:20 UTC (`enviados 0`, sin pendientes).
- Retirada la línea transitoria del cron del HOST (queda solo `firebase_operations.py daily`); copias en `releases/worker-meta-20261018/`.
- Vuelta atrás: `docker compose exec -T worker crontab - < ~/quantfut/releases/worker-meta-20261018/worker-crontab.before` y borrar `/app/meta.env`;
  si hiciera falta volver al envío por el host: `*/5 * * * * cd /home/qf/quantfut && /usr/bin/docker compose exec -T api python -m qf.comercial.meta_capi`.

### 2026-10-18 22:50 UTC · Sede de los partidos nuevos y clima ERA5 incremental · worker (2 archivos) + cron
- Hallazgo: 722 de los 729 partidos de octubre no tenían `stadium_id` (los partidos nuevos llegan de `fixtures` sin sede), así que no
  se les podía vincular altitud ni clima. Nuevo `ingest/sedes.py`: toma el estadio de la página de FotMob ya capturada, reutiliza
  uno existente por nombre o por cercanía (<330 m) y solo da de alta si no hay ninguno; procedencia en `matches_enriquecimiento`.
  Primera corrida: **449 partidos asignados, 2 estadios nuevos** (sin duplicar); quedan sin sede 273 próximos, que la reciben al
  llegar su captura de 24 h. Cron nuevo cada hora a :50.
- `ingest/era5_clima.py` corregido: antes, repetirlo reutilizaba el archivo guardado de cada celda y nunca habría pedido los
  partidos nuevos. Ahora es incremental (une los archivos de la celda y pide solo lo que no cubren, hasta hoy−7 días).
- Parche con `docker cp` de `sedes.py` (nuevo) y `era5_clima.py` (ya existía en el worker). Vuelta atrás: copiar los de `main`.
- **Trampa de despliegue encontrada:** el crontab del worker es un archivo montado (`./scripts/crontab`). Un `sed -i` en el
  servidor lo reemplaza por otro archivo y el contenedor sigue viendo el viejo: las líneas añadidas después no llegan. Se
  resolvió cargando el archivo del servidor con `crontab -` dentro del contenedor y comprobando que lo cargado es idéntico.
  Lección: añadir líneas con `>>` (no `sed -i`) o recargar siempre con `cat scripts/crontab | docker compose exec -T worker crontab -`.
  Respaldo previo: `~/backups/crontab_pre_sedes_20261018`.
- ERA5 incremental lanzado (294 celdas con partidos nuevos; 236 partidos aún sin dato de Copernicus por su retraso de ~7 días).

### 2026-10-18 · Relleno puntual del archivo de FotMob · worker (un archivo) · rama `relleno-fotmob`
- Orden del titular. `ingest/fotmob_captura.py` gana `--dias-atras` y `--maximo` (solo para relleno; los cron no cambian).
  Parche con `docker cp` de ese único archivo, que ya existía en el worker desde `main`; vuelta atrás: copiar el de `main`.
- Se ejecutó con `flock -w 900` (sin chocar con los cron): `referencias --dias-atras 20` (264 nuevas) y
  `posteriores --dias-atras 20 --maximo 400` (255 partidos guardados, 0 descartados, 0 bloqueos de FotMob).
- Resultado: ningún partido terminado desde el 3-oct queda sin su página. Totales: 20.766 partidos, 870.608 jugadores,
  48.198 bajas en `fotmob_*`. Sin gasto de créditos. Modelo, predicciones y picks sin cambios.

### 2026-10-18 21:00 UTC · Meta pasa a eventos REALES · solo configuración (sin código ni migración)
- Orden del titular: quitada `META_TEST_EVENT_CODE` del `.env` y recreada la API (misma imagen `quantfut-api-meta-web:db24a88`). Respaldo previo: `releases/meta-web-db24a88/env.antes-produccion-meta`.
- Desde ahora el cron del host envía a Meta eventos que SÍ cuentan para atribución y optimización: `CompleteRegistration`, `InitiateCheckout`, `Purchase`, `Subscribe` (y los de la app que ya se encolaban). El envío anterior (1 evento) fue de prueba.
- Verificado: API sana, contenedor sin el código de prueba, `META_CAPI_ENABLED=1`, `/app/v1/whop/config` con el Pixel.
- Vuelta atrás: añadir `META_TEST_EVENT_CODE=TEST24843` al `.env` y `docker compose up -d --no-deps --no-build api` (los eventos vuelven a ir solo a «Probar eventos»).

### 2026-10-18 20:45 UTC · Meta web: registro, EMQ con facturación, reembolsos, aviso de medición + envío de CAPI · API (rama `feat/meta-web-registro-reembolsos`, commit `db24a88`, PR #17)
- Orden del titular («resuelve lo que falta… prueba todo»). CI del PR en verde antes de desplegar. **Desplegado antes de fusionar a `main`**.
- Antes de sobrescribir, los 13 archivos que se cambian eran idénticos a `origin/main` en el contenedor `quantfut-api-google-whop:d56577d`. Sin migración nueva.
- **API:** imagen `quantfut-api-meta-web:db24a88` = la anterior + esos 13 archivos (118 rutas). Compose fijado en ella (copia previa: `releases/meta-web-db24a88/docker-compose.before.yml`; archivos
  originales en `antes/`). Worker, base, Caddy y redis sin tocar.
- **`.env`:** añadidos `META_DATASET_ID=2253839992227148`, `META_CAPI_TOKEN` (token de sistema generado SIN activar «Dataset Quality API», que Meta no deja desactivar),
  `META_TEST_EVENT_CODE=TEST24843` y `META_CAPI_ENABLED=1`. Respaldos: `releases/google-whop-d56577d/env.antes-meta` y `releases/meta-web-db24a88/env.antes-despliegue`.
  **Mientras exista `META_TEST_EVENT_CODE` los eventos van SOLO a «Probar eventos»: no cuentan para anuncios.**
- **Envío:** el worker aún no lleva `qf.comercial.meta_capi`, así que el cron del HOST (usuario `qf`) ejecuta `docker compose exec -T api python -m qf.comercial.meta_capi` cada 5 min
  (log `~/.local/share/quantfut/meta_capi.log`; copia previa en `crontab.before`). Quitar esa línea cuando el worker se alinee (no hay doble envío: `SKIP LOCKED` y estado por evento).
- **Whop:** el webhook pasó a 5 eventos (+`refund.created`, `refund.updated`).
- **Verificado en producción:** (1) registro web real (cuenta desechable id 7) → `CompleteRegistration` `website` con `fbp` de la cookie y URL de origen → enviado por la tubería real →
  visible en «Probar eventos» como *Procesado · Servidor*; (2) eventos sintéticos Purchase/Subscribe/InitiateCheckout con 13 claves de cliente (correo, nombre, apellido, ciudad, estado,
  código postal, teléfono, país, ID externo, fbp, fbc, IP, user agent); (3) Pixel `2253839992227148` carga y se registra en el navegador integrado; «Rechazar» guarda `qf_ads_consent=no` y
  no carga nada tras recargar; (4) «Prueba» de Whop → `membership.updated` firmado por Whop → 200 `ignorado` (valida la firma real con nuestro secreto).
- **Cuenta de prueba:** `prueba-meta-1792356322@ejemplo.com` (account_id 7) quedó creada en producción por la prueba; no tiene suscripción.
- **Para pasar a producción real de Meta:** quitar `META_TEST_EVENT_CODE` del `.env` y `docker compose up -d --no-deps --no-build api`. Comprobar antes en Events Manager que EMQ de «Purchase» sube.
- **Vuelta atrás:** `cp -p ~/quantfut/releases/meta-web-db24a88/docker-compose.before.yml ~/quantfut/docker-compose.yml && docker compose up -d --no-deps --no-build api` y `crontab ~/quantfut/releases/meta-web-db24a88/crontab.before`.
- **Nota:** el Chrome del titular tiene un bloqueador de rastreadores que devuelve 503 a `fbevents.js`; allí el Pixel no se ve. Los visitantes sin bloqueador sí lo cargan.

### 2026-10-18 20:20 UTC · Acceso con Google en la web + cobro con Whop + Meta web · API + `db/083` (rama `feat/google-whop-meta`, commit `d56577d`, PR #16)
- Orden del titular («despliega al vps»). CI del PR en verde (2/2) antes de desplegar. **Desplegado antes de fusionar a `main`**: al fusionar el PR, `main` queda igual que la API.
- Antes de sobrescribir se comprobó que los 10 archivos existentes que se cambian eran idénticos a `origin/main` en el contenedor `quantfut-api-cybercore:2d8cfef` (los otros 6 son nuevos).
- **Base de datos:** `db/083_whop_checkout.sql` aplicada en una transacción (solo añade: `plans.whop_plan_id`, `whop_checkouts`, `whop_webhooks`, `whop_payments`, `meta_events.action_source/web_context`). `UPDATE plans SET whop_plan_id` de los 3 planes.
  Respaldo previo de `plans`: `~/quantfut/releases/google-whop-d56577d/plans.antes.sql`.
- **API:** imagen `quantfut-api-google-whop:d56577d` = la `2d8cfef` + solo esos 16 archivos (ensayo: 118 rutas, las 8 nuevas presentes). Compose fijado en la nueva (copia previa: `releases/google-whop-d56577d/docker-compose.before.yml`).
  Worker, base, Caddy y redis sin tocar.
- **`.env`:** añadidas `FIREBASE_WEB_API_KEY/APP_ID/AUTH_DOMAIN`; ya estaban `WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`, `META_PIXEL_ID` (entrada de arriba). Respaldos `env.antes-despliegue` y `env.before` en la misma carpeta. `META_CAPI_ENABLED` NO está activo.
- **Verificado en el dominio real:** `/health` 200; `/app/v1/firebase/web-config` con `projectId`; `/app/v1/whop/config` `{"enabled":true,"pixelId":…}`; `/google-auth.js`, `/meta-pixel.js`, `/whop-checkout.js` 200;
  `web-session` sin cuerpo 422; webhook con firma mala 400 y con firma buena 200 (`ignorado`, fila de idempotencia `despliegue.ping`); logs sin errores.
  Desde el VPS, la clave de Whop crea una `checkout_configuration` (200; dos de prueba sin cobro) y la página de pago muestra «Total a pagar hoy 14,99 US$».
- **Falta:** probar el botón de Google y un cobro real con un usuario; alinear el worker (cron de CAPI con `web_context`) ANTES de activar `META_CAPI_ENABLED`; reembolsos (`refund.created` no suscrito).
- **Vuelta atrás:** `cp -p ~/quantfut/releases/google-whop-d56577d/docker-compose.before.yml ~/quantfut/docker-compose.yml && docker compose up -d --no-deps --no-build api`.
  La migración es aditiva: no hace falta deshacerla (el código anterior no usa las tablas ni columnas nuevas).

### 2026-10-18 · Whop: claves en el `.env` del servidor · SOLO configuración, sin código nuevo ni reinicios
- Por orden del titular («usa el backend para guardar claves»): añadidas `WHOP_API_KEY` y `WHOP_WEBHOOK_SECRET` al final de `~/quantfut/.env` (permisos 600).
  Son inertes: la API actual no las lee; las usará la imagen del plan `docs/despliegue_google_web_20261018.md`.
- Respaldo previo: `~/quantfut/releases/whop-env-20261018/env.before`. Vuelta atrás: `cp -p` ese archivo sobre `.env` (la clave solo se muestra una vez en Whop: habría que regenerarla).
- También `META_PIXEL_ID=2253839992227148` (Pixel de Meta, dato público), por orden del titular.
- En Whop (cuenta `biz_VHqtO4zEcnvvOK`): producto QuantFut con 3 planes renovables, clave «QuantFut Backend» (permisos: leer/crear configuraciones de checkout; solo desde 31.220.72.30)
  y webhook `https://pronosticosdeportivos.pro/webhooks/whop` (`payment.succeeded`, `membership.updated`, `membership.deactivated`). Hasta desplegar, ese endpoint no existe
  y las entregas fallarán y se reintentarán; no hay cobros posibles antes de desplegar (la web no muestra el pago).

### 2026-10-18 18:55 UTC · Captura recurrente de FotMob y clima histórico ERA5 · base de datos + worker (3 módulos) + cron
- Orden del titular: autorizó la captura diaria de FotMob y entregó su token personal de Copernicus CDS. Parche del
  contenedor worker con `docker cp`: `ingest/fotmob_captura.py` y `ingest/era5_clima.py` (nuevos) y `ingest/fotmob_a_motor.py`
  (refactor con la función `insertar`, comportamiento igual). Se pierden si el worker se recrea: construir desde `main`.
- **Base de datos** (solo se añade): `db/081` `fotmob_equipo` (495), `fotmob_referencia` (20.331 del archivo + 503 de liga),
  `fotmob_original`, `fotmob_previo`, `fotmob_jugador_previo`, `fotmob_baja_previa`, `fotmob_captura_log`; `db/082`
  `clima_era5_partido`. Vuelta atrás: `DROP` de cada una; nada existente las lee.
- **Cron** (`~/quantfut/scripts/crontab`, recargado con `crontab /etc/cron.d/quantfut`, sin reiniciar): `referencias` 05:50 UTC,
  `previos` cada 15 min, `posteriores` a :35, los tres con `flock -n /tmp/fotmob_captura.lock`. Respaldo previo:
  `~/backups/crontab_pre_fotmob_20261018`. Vuelta atrás: restaurar ese archivo y recargar.
- **Token de CDS** en `~/quantfut/.env` como `CDS_API_TOKEN` (permisos 600; el worker en marcha no lo ve, se pasa con
  `docker compose exec -e`). Respaldo previo del `.env` en `~/backups/env_pre_cds_20261018` (600). El token se compartió por
  chat: conviene regenerarlo en la cuenta de Copernicus cuando termine la descarga.
- **Descarga ERA5 en segundo plano** (423 celdas, ~5 h, 4 en paralelo): `python -m qf.ingest.era5_clima` dentro del worker, con
  registro en `/var/log/era5_clima.log`; las respuestas quedan en `/srv/quantfut/artifacts/era5`. Reanudable.
- Salvaguardas de FotMob: 0,8 s entre peticiones, un bloqueo HTTP 401/403/429 detiene todo 12 h con alerta. Primeras corridas:
  23 referencias, 8 capturas previas y 60 posteriores sin errores. API-Football y The Odds API: sin gasto.
- Verificado: modelo activo sin cambios, predicciones y picks sin cambios (los módulos no los leen ni escriben).
- Detalle: `docs/datos_al_motor_20261018.md` §6.

### 2026-10-18 17:55 UTC · Orden de identidades y datos de FotMob al motor · base de datos + worker (cinco módulos nuevos) + cron
- Orden del titular («hazlo ya», los cuatro grupos de datos). Sin imagen nueva: **parche del contenedor worker** con
  `docker cp` de cinco archivos NUEVOS (no sobrescribe ninguno): `ingest/fotmob_a_motor.py`, `estadios_altitud.py`,
  `arbitros_equivalencia.py`, `calendario_equipos.py`, `puentes_jugadores.py`. Se pierden si el worker se recrea: la
  alineación del 1-nov debe construirse desde un `main` que ya los incluya. Hashes iguales a la rama `ordenar-identidades`.
- **Datos existentes que cambian** (lo que verá el reentrenamiento del 1-nov):
  - `db/073`: 33 filas de `matches` (Champions/Europa League, 2014 → 2024-12-11) pasan de Arsenal de Sarandí (28402) a
    Arsenal (3). Auditado en `correcciones_identidad`. Respaldo: `~/backups/arsenal_sarandi_matches_pre073_20261018.csv.gz`.
    Vuelta atrás: las dos sentencias `UPDATE` comentadas al final de `db/073_corregir_arsenal_sarandi.sql`.
  - 4 alias nuevos de `odds_api` (Bayern München, Internazionale Milano, LOSC Lille, Young Boys), auditados (migración 074).
    Vuelta atrás: `DELETE` por (alias, fuente).
  - **45 cierres de Pinnacle** (135 cuotas, `source='the_odds_api_hist'`) en `odds_snapshots`. **Irreversible:** la tabla no
    admite DELETE. Cada partido tiene exactamente 3 filas; repetir la carga inserta 0.
- **Tablas y vistas nuevas** (solo se añaden; nada existente las lee): `db/075` `fotmob_partido` (20.331),
  `fotmob_jugador_partido` (852.126), `fotmob_baja` (47.140), `v_fotmob_jugador_partido`; `db/076` `estadio_altitud` (728);
  `db/077` `arbitro_equivalencia` (54) y `v_arbitro_unificado`; `db/078` `calendario_equipo` (60.979) y su log;
  `db/079` `puente_jugador` (7.834); `db/080` `v_descanso_equipo`. Vuelta atrás: `DROP` de cada una.
- **Cron:** una línea nueva en `~/quantfut/scripts/crontab` del servidor (05:40 UTC, calendario de la temporada en curso,
  ~313 llamadas de las 7.500 de API-Football), recargada con `crontab /etc/cron.d/quantfut`; sin reiniciar el worker.
  Respaldo previo: `~/backups/crontab_pre_calendario_20261018`. Vuelta atrás: restaurar ese archivo y recargar.
- Créditos y cuotas: The Odds API, 0 (snapshots ya descargados); API-Football, 1.260 llamadas (quedaba 5.238 al empezar).
- Verificado al terminar: API local 200; modelo activo `2026.09.27-010508`; 378 predicciones, 0 picks, 20 lotes de la cadena
  verificados (`verify` correcto); contenedores sin reinicios. Consultas lentas propias canceladas (la medición de jugadores
  se reescribió con funciones de ventana; las anteriores seguían activas en el servidor tras cancelarse el cliente).
- Detalle y cifras: `docs/datos_al_motor_20261018.md`, `docs/ordenar_identidades_20261018.md`.

### 2026-10-18 19:10 UTC · Comprometer-revelar de la cadena · worker (un archivo), rama `codex/force-update-deployment` (`a1e725d`, PR #11)
- Cambio: `publish/hashchain.py` (al repo público sube solo el compromiso; el JSON se revela al terminar los partidos). **Desplegado antes de fusionar a `main`** por orden del titular; al fusionar el PR, `main` queda igual que el worker.
- Método: `docker cp` de ese único archivo al contenedor worker (como F2c): **parche del contenedor, no de la imagen**; se pierde si el worker se recrea, así que la alineación del 1-nov debe construirse desde un `main` que ya lo incluya.
- Antes de copiar, el `hashchain.py` del worker era idéntico a la base (`912aa8c21708`). Hash final `252693f570e9`, igual al commit.
- Ensayo en el worker: `hashchain verify` OK en 20 lotes (0 sin revelar), importa sin error. `CHAIN_GIT_REMOTE` sigue vacío: `seal()` no ejecuta ninguna rama de git, así que el sellado de las 08:00 UTC se comporta igual. Sin reinicios; modelo, API y base intactos.
- Falta: configurar `CHAIN_GIT_REMOTE` (decisión del titular) y probar `revelables` contra el repo real cuando exista.
- Vuelta atrás: `docker cp ~/quantfut/deployments/hashchain-revelado-20261018/antes/hashchain.py <worker>:/app/src/qf/publish/hashchain.py`.
- Observado de paso: el servidor se reinició a las 19:00 UTC (contenedores con 3 min de actividad al llegar) y la API corre `quantfut-api-cybercore:2d8cfef`, que no figura en este registro (otra sesión): anotarlo quien la desplegó.

### 2026-10-18 02:20 UTC · Rediseño CYBERCORE de la web · API
- PR #12 (`a30c799`) y hotfix de rutas FastAPI PR #13 (`2d8cfef`), con los dos arneses de cada PR aprobados.
- Imagen `quantfut-api-cybercore:2d8cfef` (`8d81ce9c10c6`), derivada de la imagen que ya corría
  `quantfut-api-force-update:b8f74ae`. Solo reemplaza `frontend/` y `src/qf/api/web.py`; no reconstruye
  desde la carpeta desactualizada del servidor ni modifica el resto del código de la API.
- Respaldo previo de frontend, `web.py`, imagen y compose en
  `~/quantfut/releases/cybercore-2d8cfef/backup/`. Worker, base de datos, Caddy y Grafana intactos.
- Ensayo aislado y dominio real: `/`, `/health`, `/future.css`,
  `/vendor/cybercore/cybercore.min.css` y `/app.js` responden 200; contenido y cinco hashes iguales a
  `main`. Comprobación visual correcta y consola del navegador sin errores. Modelo activo
  `2026.09.27-010508`; publicación pausada por la puerta comercial; 19 lotes de la cadena verificados.
- Vuelta atrás: restaurar `backup/docker-compose.before.yml` como `~/quantfut/docker-compose.yml` y
  ejecutar `docker compose up -d --no-deps --no-build --force-recreate api`. La imagen anterior es
  `quantfut-api-force-update:b8f74ae` (`9188e2950838`).

### 2026-10-16 · Force Update desde el panel · API + `db/072`
- PR #10 integrado (`b8f74ae`), arnés del PR y de `main` en verde.
- Imagen `quantfut-api-force-update:b8f74ae`, derivada de `quantfut-api-admob:20261015b` con solo los tres archivos de Force Update. Base previa comprobada y hashes finales verificados.
- Migración aditiva aplicada en transacción; respaldo de esquema y compose en `~/quantfut/releases/force-update-b8f74ae/`.
- Ensayo: 108 rutas, renderizado de panel y configuración correctos. Dominio real: salud 200 y siete campos nuevos en `/mobile/v1/config`; logs sin errores. Modelo `2026.09.27-010508`; mismo contenedor del worker.
- Estado inicial: obligación desactivada, mínimos 0 y versiones/enlaces vacíos. Requiere nueva compilación móvil para que los dispositivos apliquen la política.
- Reversión: restaurar `docker-compose.before.yml` del respaldo y ejecutar `docker compose up -d --no-deps --no-build api`. La tabla añadida puede permanecer.
- Detalle y estado móvil: `docs/despliegue_force_update_20261016.md`.

### 2026-10-15 23:30 UTC · Compras de tienda y Meta (CAPI) · API + `db/071` (rama `feat/meta-compras`, commits `4db6616`, `ca818ce`)
- Orden del titular: desplegar el mismo día (antes se había dejado la API para después del 1-nov). El worker NO se tocó
  (mismo contenedor `28330d835ca9`), así que no interfiere con el reentrenamiento.
- **Base de datos:** `db/071` aplicada en una transacción. Solo añade: columnas de tienda en `plans`, `accounts.store_account_token`,
  `firebase_preferences.ads_measurement` y tablas `store_transactions` (inmutable), `meta_events`, `meta_identities`.
  Respaldo previo: `~/backups/pre_meta_071_20261015.sql.gz` (accounts, plans, firebase_preferences).
- **API:** imagen `quantfut-api-admob:20261015b` = la `20261015a` + SOLO 20 archivos de la rama + `app-store-server-library==3.1.2`.
  Antes de sobrescribir se comprobó que los 12 archivos existentes que se cambian eran idénticos a `main` en el contenedor
  (los otros 8 son nuevos), por lo que las demás diferencias de la API frente a `main` no se tocaron.
  Ensayo en contenedor aparte: 104 rutas = 100 + 4 nuevas. Compose del servidor fijado en `20261015b`
  (copia previa: `~/backups/docker-compose.pre-meta-20261015.yml`).
- **Verificado en el dominio real:** `/health` 200; `/app/v1/plans` con los IDs de tienda; las 3 páginas `/legal/*` muestran
  2026-10-16; `compras/verificar` y `google/rtdn` responden 503 `compras_deshabilitadas`; `meta/dispositivo` sin sesión 401;
  callbacks de recompensas idénticos a la imagen anterior; sin errores en los logs.
- **Apagado:** `STORE_PURCHASES_ENABLED` y `META_CAPI_ENABLED` no están en el `.env` (valen 0). Faltan credenciales del titular.
- **Pendiente en el worker:** la tarea `qf.comercial.meta_capi` del cron y la limpieza de `meta_*` en `firebase_mantenimiento`
  llegan con la próxima alineación del worker (después del 1-nov). Hacerla ANTES de activar `META_CAPI_ENABLED`.
- **Vuelta atrás:** `sed -i 's#20261015b#20261015a#' ~/quantfut/docker-compose.yml && docker compose up -d --no-deps --no-build api`.
  La migración es aditiva: no hace falta deshacerla (las columnas y tablas nuevas no las usa el código anterior).
- **Legal:** las páginas públicas ya describen Meta, las compras en tiendas y la medición activada por defecto (versión 2026-10-16);
  el servidor acepta también la 2026-10-12 de la app publicada. Falta la revisión del profesional habilitado.
### 2026-10-15 16:49 UTC · LanusStats/365Scores · tres parejas xG — base de datos
- Carga explícitamente solicitada: Granada–Albacete 1,58/1,43; Almería–Deportivo 1,89/0,84;
  Zaragoza–Málaga 1,41/0,32. Solo cuatro campos xG de tres partidos vacíos, sin tocar fechas/resultados.
- Tres detalles originales y tres respuestas de estadísticas conservados en el archivo existente,
  con hashes y recepción real del 15-oct-2026. Ensayo revertido y repetición sin escrituras.
- Respaldo selectivo: volumen del worker, `/srv/quantfut/artifacts/imports/lanusstats-xg-20261015/carga/tres_partidos_antes.json.gz`.
  Vuelta atrás: restaurar solo los cuatro campos xG de esos tres registros, comprobando que conservan
  exactamente esta fuente/recepción/valores; conservar el archivo de procedencia. No se deshabilitan triggers.
- Lectura tras commit: 3/3 parejas, 6/6 hashes y API 200; 1.219 huecos restantes. Modelo/flags/sellos
  y demás partidos conservados. Sin despliegue de aplicación, reinicios ni entrenamiento.
- Detalle: `docs/lanusstats_carga_20261015.md`; importador auditado bajo el volumen de archivos,
  sin modificaciones del código en ejecución.

### 2026-10-15 15:52 UTC · Worker alineado con `main` (`495053a`) — recreado
- Imagen `quantfut-worker:candidato-495053a` (`896c5009c1ac`), construida desde `main` con el `requirements.txt` corregido
  (incluye `cryptography` y `firebase-admin`). `latest` = esa imagen. El worker pasó de 12 archivos distintos a **0**.
- **Ensayo previo** (worker actual frente a candidata, solo lectura, `scripts/ensayo_worker.py`): 0 módulos con error, 21/21
  entradas del cron importables, `hashchain verify` OK en 17 lotes y conjunto de entrenamiento idéntico (49.509 filas,
  46.226 con cierre, misma huella).
- Se recreó **solo el worker** justo cuando no había trabajos en curso. El ciclo de cron de las 16:00 corrió limpio
  (cuotas, bajas, alineaciones, marcador, sombra) y no hay errores posteriores al cambio.
- **Vuelta atrás:** `docker tag quantfut-worker:en-ejecucion-20261015 quantfut-worker:latest &&
  docker compose up -d --no-deps --force-recreate worker` (el estado exacto de antes, con el parche F2c).
- Receta usada: `git archive HEAD Dockerfile requirements.txt src frontend` → carpeta `~/quantfut/releases/worker-<commit>` →
  `docker build -t quantfut-worker:candidato-<commit>` → ensayo → `docker tag ... latest` → `docker compose up -d --no-deps
  --force-recreate worker`.
- **Nota sobre lotes sellados:** regenerar desde la base 8 de los 17 lotes ya no reproduce el contenido sellado (también pasaba
  antes del cambio). Causa: 93 ítems de Chile y Brasil B eliminados el 13-oct (autorizado) y 4 predicciones de partidos
  reprogramados. Los archivos sellados siguen intactos y la verificación de la cadena da OK; lo que cambia es que ya no se
  puede reconstruir desde la base. No es un fallo de esta alineación.

### 2026-10-15 · Orden de imágenes del worker — sin reiniciar nada
- `quantfut-worker:latest` (la imagen que se usaría al recrear el contenedor) era **más antigua** que el worker en
  ejecución: 16 archivos distintos, entre ellos `publish/daily.py` y `publish/hashchain.py` (sellado de la cadena).
  Recrear el worker habría retrocedido ese código y roto la verificación de lotes recientes.
- Se fijó el estado en ejecución: `scripts/deploy.sh congelar worker`. Etiquetas: `latest` = `en-ejecucion-20261015`
  (`11cd07f588be`, con el parche F2c); la anterior queda como `latest-previo-20261015` (`2cac1af32eed`).
  El contenedor no se tocó (en ejecución desde 2026-10-14).
- Vuelta atrás de esta operación: `docker tag quantfut-worker:latest-previo-20261015 quantfut-worker:latest`.
- Diferencia worker vs `main` que queda: 12 archivos. Los relevantes son pequeños y de bajo riesgo (`config.py`: un ajuste
  nuevo `APP_DOWNLOAD_URL`; `eval/alta_prob_calibracion.py`: ampliación aditiva de un script de evaluación sin cron;
  `ingest/history_fd.py` y `model/lineup_challenger.py`: trabajo de F1/F2, probado). El resto es código de la API.

### 2026-10-16 · Credenciales de Google Play y RTDN — API
- Estado final autorizado: `STORE_PURCHASES_ENABLED=1`, misma imagen, solo API recreada. Respaldo previo: `deployments/play-credentials-20261016/docker-compose.before-enable.yml`. RTDN validado con 204; consulta real de QuantFut Plus por Publisher API con 200 y tres planes ACTIVE. Compra interna `sandbox` y acceso VIP comprobados. Meta no activado por esta sesión.
- Conservada imagen `quantfut-api-admob:20261015b`; recreada solo API sin build. Worker intacto.
- JSON privado con modo 600 en `/home/qf/.config/quantfut/google-play.json`, montado solo lectura en `/run/secrets/quantfut-play.json`.
- Configuradas variables PLAY de cuenta, paquete y OIDC; instalación inicial con compras apagadas y posterior activación comprobada.
- Respaldo de compose previo: `deployments/play-credentials-20261016/docker-compose.before.yml` en servidor.
- Producción 1.0.0 y ficha enviadas a revisión de Google; todavía no se confirma disponibilidad pública.

### Trampas conocidas (no repetirlas)
- **`requirements.txt` del servidor no tiene `cryptography` ni `firebase-admin`** (el de `main` sí). El worker en ejecución
  los tiene instalados a mano. Reconstruir una imagen desde `~/quantfut` tal cual **perdería `cryptography`**, que descifra
  la clave de PitchAPI guardada en la base.
- **`docker-compose.yml` de `main` fija una imagen antigua de la API** (`quantfut-api-tapjoy:20261012-msg`); el servidor usa
  `quantfut-api-admob:20261015a`. Desplegar con el compose del repo retrocedería la API.
- La API (`api`) y la carpeta `~/quantfut/src` llevan código antiguo (ver tabla de arriba); la API no se ha alineado.

### 2026-10-15 · F2c · filtro del cierre reconstruido — worker
- Commit `976b448`. `docker cp` de `eval/cierre.py`, `eval/clv.py`, `model/train.py`, `model/shadow.py`,
  `publish/shadow_sharp.py` al contenedor worker. Hashes verificados contra `main`.
- Respaldo de lo anterior: servidor `~/quantfut/deployments/f2c-filtro-cierre/antes`.
- **Es un parche del contenedor, no de la imagen**: se pierde si el worker se recrea. Comprobar antes del 1-nov.
- La API no se tocó (sus `train.py` y `clv.py` son antiguos).
- Vuelta atrás: `docker cp` de `antes/` al worker.

### 2026-10-15 · F2b · cierres de Pinnacle de The Odds API — base de datos
- 3.492 filas en `odds_snapshots` (`source='the_odds_api_hist'`); 8.000 créditos; saldo 7.367.
- Respaldo: `~/backups/odds_snapshots_pre_f2b_20261015.sql.gz`. Detalle: `docs/f2_cierres_pinnacle_20261015.md`.

### 2026-10-15 · OddsPapi · cierres reconstruidos — base de datos (otra sesión)
- 2.918 cierres, migración `db/070`. Ver `docs/oddspapi_carga_20261015.md`.

### 2026-10-14 · F0 · archivo FotMob a `matches` y `estadios` — base de datos
- Migración `db/067` y relleno de columnas vacías. Respaldo: `~/backups/matches_pre_f0_20261014.sql.gz`.
  Detalle y reversión: `docs/f0_archivo_a_matches_20261014.md`.

### Antes del 2026-10-14
Ver `harness/progreso.md` (despliegues de la API con imágenes `quantfut-api-admob:*`, AdMob, invitaciones, etc.).
