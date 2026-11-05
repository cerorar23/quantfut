# Rediseño del motor de tenis ATP/WTA — Fase 2: plan técnico (5-nov-2026)

Estado: **plan, sin código del motor**. Rama `tenis/rediseno-f1` (worktree `C:\Users\huye\Documents\qf-tenis-rediseno`). Este documento es el único archivo creado en la fase; no se llamó a ninguna API ni al VPS; no se gastó nada.

Entradas: auditoría de la Fase 1 ([tenis_auditoria_20261104.md](tenis_auditoria_20261104.md)) con sus inventarios de [datos](tenis_auditoria_inventario_datos_20261104.md) y [cuotas](tenis_auditoria_inventario_cuotas_20261104.md) y las tablas `docs/tenis_auditoria_tablas/*.csv`; literatura de 76 estudios ([tenis_literatura_20261104.md](tenis_literatura_20261104.md)); `CLAUDE.md`, `PENDIENTES.md`, `harness/tareas.md`, `harness/progreso.md`, `DEPLOYS.md` (secciones de tenis, NBA y PropLine); el motor actual `apps/tennis/` (solo para saber qué existe); los principios de `apps/nba` (`db/0001`–`0009`, `src/nba/v2/sellado.py`, `src/nba/contratos/base.py`, `ops/g_fuga.py`) y `src/qf/ingest/propline_shared.py`.

## 0. Convenciones de este documento

- **Dato** = cifra medida, con su fuente entre paréntesis: «(aud. §6.2)» = auditoría, sección 6.2; «(inv. datos §3)» y «(inv. cuotas §4)» = inventarios; «(lit. C.ii, A02)» = documento de literatura, sección y estudio; «(CSV `nombre`)» = tabla de `docs/tenis_auditoria_tablas/`. Las etiquetas de verificación de la literatura ([VT], [VF], [J]) se conservan cuando importan.
- **Propuesta** = decisión de diseño mía, sujeta a tu aprobación cuando cambia algo de producción o del alcance. Va marcada «Propuesta:».
- **No medido** = no hay cifra; no se rellena con supuestos.
- **Comprobado aquí** = cálculo pequeño que hice en la consola para verificar una fórmula (sin crear archivos de código).
- Las cifras de la literatura marcadas como inciertas en la §E de ese documento no se usan como umbrales.

## 1. Arquitectura elegida (resumen)

1. **Evidencia en Postgres propio de tenis** (esquema `tenis`, contenedor aislado como el de NBA): tablas solo-anexar con `recibido_en` real y fuente, disparadores por sentencia contra UPDATE/DELETE/TRUNCATE, originales como archivos con SHA-256 y lectura punto en el tiempo por funciones SQL. Nada de tenis vive hoy en Postgres (inv. datos §10).
2. **Identidad propia**: jugador canónico con alias por fuente (id del proveedor > nombre + fecha de nacimiento > contexto del partido), torneo y **edición** (sede, huso, superficie, indoor, formato por edición). Dobles fuera. Lo no resuelto no se predice y se cuenta.
3. **Modelo en dos piezas que se juntan por inversión exacta** (estrategia suma/diferencia de A26 y B03): la **diferencia** de probabilidad de punto sale de un rating dinámico ajustado con resultados (con superficie como multiplicador y desviación jerárquica, y fatiga como penalizador con signo forzado); la **suma** sale de un modelo jerárquico de puntos al saque/resto. Se resuelve δ para que el modelo completo reproduzca la probabilidad de ganador calibrada.
4. **Simulador analítico** (juego, tiebreak a 7 y a 10, set con alternancia de saque, partido a 3 y a 5) que produce **una sola distribución conjunta** de marcadores por set; primer sacador 50/50; incertidumbre de parámetros y «forma del día» integradas por cuadratura determinista (Monte Carlo con semilla fija solo donde no haya forma gaussiana).
5. **IID condicionado + efecto aleatorio del partido** como opción por defecto; sin «factor clutch» por jugador; el margen de error conocido en totales se declara y se mide; una prueba preregistrada decide si se añade presión más adelante.
6. **Entrena solo el PC**: el VPS solo filtra (actualiza estados con hiperparámetros congelados) e infiere con artefactos JSON/Parquet con huella de contenido; nada se reentrena dentro del contenedor.
7. **El mercado nunca entra en el modelo**: PropLine (archivo compartido, sin peticiones propias) y Tennis-Data (solo historia del ganador, clase b) son referencia de evaluación; los resultados salen de fuentes de resultados propias, nunca de la calificación de PropLine.
8. **Compuertas definidas antes de medir** (coherencia y física del marcador con propiedades aleatorias, calibración conjunta, log-loss/Brier frente a línea base y cierre con IC por bootstrap por partido, cobertura, reproducibilidad Windows/Linux, G-fuga contra una implementación independiente, operación) y producto beta honesto: si no gana al cierre, se publica que no gana.

## 2. Hechos nuevos que encontré al preparar el plan (afectan al diseño)

| # | Hecho | Fuente | Consecuencia |
|---|---|---|---|
| 1 | **El plan de API-Tennis venció el 1-nov-2026 y no se renueva**; el motor actual pasó a `--source auto` (API-Tennis primero y, si falla, SportsAPIPro con el mismo formato). SportsAPIPro tiene 100 peticiones/día compartidas. | `DEPLOYS.md`, entradas del 31-oct (noche) «Tenis: el motor pasa a `--source auto`» y «Equivalencia de jugadores… (T1)» | La premisa «resultados de API-Tennis» necesita confirmación: hoy el calendario y los resultados en vivo llegan por SportsAPIPro. El pipeline (§C) se diseña con una interfaz de calendario/resultados independiente del proveedor y una **decisión tuya** (§M, D3). |
| 2 | Existe un recolector SofaScore en el VPS vía Apify (`~/sofascore-apify`, cron `40 7 * * *`) que **incluye tenis ATP/WTA individual** (torneos localizados cada 6 días, ~0,6 USD por barrido; tope 15 USD/mes de la cuenta). La auditoría midió `~/sofascore-scraper` (0 tenis) pero **no** este árbol. | `DEPLOYS.md`, 24-oct «Recolector SofaScore (Apify, actor rl1987)» y «pasan a scrapesage» | Cuánto tenis hay en `~/sofascore-apify/data`: **no medido**. Puede dar duraciones (minutos) de partidos recientes para la fatiga; es de pago (presupuesto ya aprobado para fútbol/NBA, no para un uso nuevo). |
| 3 | SportsAPIPro sirve el ranking oficial actual (ATP `/rankings/type/5`, WTA `/rankings/wta`); el exportador de estadísticas ya lo usa con tope propio de 6 peticiones/día. | `DEPLOYS.md`, 31-oct «Tenis T3» | Candidato a la captura semanal del ranking **hacia adelante** con recepción real (§C.4). |
| 4 | TML se revisa a posteriori: `2024.csv` local y del VPS tienen el mismo número de líneas y distinto hash. | inv. datos §10 | Los resultados y estadísticas de TML se guardan como **aserciones con recepción**, no como una tabla que se sobrescribe (§A). |
| 5 | Añadir superficie al Elo mejoró ATP (+0,039 → +0,036 frente al cierre) y **empeoró** WTA (+0,036 → +0,038). | CSV `linea_base_dif_vs_cierre_combinada` | La compuerta de superficie (§I) puede fallar en un circuito y no en el otro: los parámetros de superficie van **por circuito**. |

## A. Modelo de datos propio de tenis

### A.1 Dónde vive (decisión justificada)

Propuesta: **Postgres, esquema `tenis`, en un contenedor aislado `tenis-db`** (mismo patrón que `nba-db`), con roles separados. Alternativas descartadas:

| Opción | A favor | En contra | Veredicto |
|---|---|---|---|
| Archivos + SQLite (lo de hoy) | Ya existe; sin servidor | SQLite no tiene roles ni disparadores por sentencia contra TRUNCATE; un escritor a la vez; las copias del VPS llevan rutas Windows en `receipts.source_path` (aud. §10); 21 paquetes y protocolos congelados (aud. §6.5) | Descartada para la evidencia y los sellos |
| Esquema `tenis` en la base `quantfut` de fútbol | Un servidor menos | Un despliegue de fútbol (migraciones, restauraciones) arrastra al tenis; mezcla roles y respaldos | Descartada |
| **Contenedor `tenis-db` propio** | Aislamiento de fallos, respaldo propio cada 6 h, roles mínimos, funciones PIT en SQL, candado de aviso para la cadena, igual que NBA v2 (probado en producción) | Memoria del VPS (no medida para un tercer Postgres) | **Elegida** (decisión tuya D1 porque añade un contenedor) |

Lo que **no** va a Postgres: los originales (archivos `objetos/aa/<sha256>.json.gz` o `.csv.gz` en un árbol direccionado por contenido, escritura atómica como `propline_shared.put_object`) y el archivo horario de PropLine, que se **lee** en su sitio (`propline_shared.newest/read_two_way/read_closing`) y se carga a una tabla derivada (A.3). Los conjuntos de entrenamiento son Parquet con huella, generados en el PC desde la copia restaurada (§H).

Roles (propuesta): `tenis_captura` (INSERT en evidencia, nada más), `tenis_motor` (SELECT en evidencia + INSERT en `pronostico` y `artefacto_activo`), `tenis_api` (SELECT en vistas públicas), `tenis_lectura` (solo lectura para G-fuga y copias). Nadie tiene UPDATE/DELETE en evidencia; además los disparadores lo rechazan para el dueño.

### A.2 Qué es evidencia y qué es derivado

- **Evidencia (solo-anexar, disparadores por sentencia, con `recibido_en` y `fuente`)**: recibos de originales, aserciones de identidad, ediciones de torneo, partidos, orden de juego, resultados, estadísticas, secuencias punto a punto, ranking, precios de mercado observados, artefactos activados, pronósticos sellados. Una corrección es **otra fila** con `recibido_en` posterior (y, si procede, `corrige_a`); la lectura PIT elige.
- **Derivado (regenerable, sin valor de prueba)**: vistas y funciones de lectura, tablas de estado del filtro (ratings) que se pueden recalcular por reproducción, exportaciones Parquet, informes de compuertas. Si un derivado se pierde se reconstruye desde la evidencia; si se pierde evidencia, no.
- **Estado operativo (mutable, fuera de la prueba)**: cursores de cada colector (`tenis_op.cursor`), presupuesto diario por proveedor (`tenis_op.presupuesto`), deduplicación de alertas. Viven en otro esquema (`tenis_op`) para que nadie confunda estado con evidencia.

### A.3 Tablas (propuesta; tipos abreviados)

Claves: identificadores sustitutos `BIGINT IDENTITY`; claves naturales `UNIQUE` para la idempotencia. Todas las tablas de evidencia llevan `recibido_en TIMESTAMPTZ NOT NULL`, `fuente TEXT NOT NULL REFERENCES tenis.fuente` y, salvo los catálogos semilla, `recibo_id` (el original del que salen).

| Tabla | Grano | Columnas clave (resumen) | Notas tenis-específicas |
|---|---|---|---|
| `fuente` (catálogo) | proveedor | `fuente`, `prioridad_resultado`, `prioridad_calendario`, `licencia`, `uso_permitido` | TML, SofaScore, MCP (CC BY-NC-SA, solo local y con atribución), Tennis-Data, API-Tennis, SportsAPIPro, PropLine |
| `recibo` | original | `recibo_id`, `fuente`, `recurso`, `parametros` (sin clave), `recibido_en`, `estado_http`, `sha256`, `ruta_objeto`, `bytes`, `lote` ; `UNIQUE(fuente, recurso, sha256)` | El mismo contenido recibido dos veces = dos recepciones del mismo `sha256` (se guarda la recepción, no se duplica el objeto) |
| `jugador` | persona | `jugador_id`, `circuito` (atp/wta), `creado_en` | Sin nombre aquí: los nombres son aserciones |
| `jugador_asercion` | dato de un jugador según una fuente | `jugador_id`, `campo` (nombre, fecha_nacimiento, mano, altura, pais), `valor`, `recibido_en`, `fuente` | La fecha de nacimiento decide homónimos (§B) |
| `jugador_alias` | id de una fuente → jugador | `fuente`, `id_fuente`, `jugador_id`, `metodo` (id_exacto, nombre_fecha_nac, contexto_partido, manual), `recibido_en`, `anula_a` | Un alias erróneo se anula con otra fila; nunca se borra |
| `sin_resolver` | cola | `fuente`, `id_fuente`, `nombre_fuente`, `motivo`, `contexto` (jsonb), `recibido_en` | Lo que no se resuelve se cuenta y alerta (§B.3) |
| `torneo` | torneo estable | `torneo_id`, `circuito`, `nombre`, `categoria` | Categorías: GS, M1000/WTA1000, 500, 250, Finales, Challenger, ITF, equipos (Davis, BJK, United Cup), JJOO, exhibición |
| `edicion` | torneo × temporada | `edicion_id`, `torneo_id`, `temporada`, `lunes_semana`, `fecha_fin`, `sede_id`, `superficie` (clay/grass/hard/carpet), `indoor` (bool o NULL = desconocido), `formato` (jsonb: mejor_de, tiebreak por set, set decisivo), `por_equipos`, `recibido_en` | La superficie va por **edición**, no por torneo; una corrección es otra fila |
| `sede` | recinto | `sede_id`, `ciudad`, `pais`, `huso_iana`, `lat`, `lon`, `altitud_m` (NULL si no se conoce) | Reutiliza como **dato** el registro de sedes verificado del motor actual (`config/historical_venues_20261018`), no su diseño |
| `partido` | partido individual | `partido_id`, `edicion_id`, `ronda`, `jugador_1`, `jugador_2` (**orden canónico por `jugador_id`, nunca ganador primero**), `mejor_de`, `formato` (si difiere de la edición), `entrada_1/2` (Q, LL, WC, PR, SE, NULL), `recibido_en` | TML viene como ganador/perdedor: guardarlo así filtraría el resultado en cualquier rasgo posicional |
| `programa` | aserción de horario | `partido_id`, `inicio_programado_utc`, `tipo_hora` (fija, no_antes_de, a_continuacion, desconocida), `pista`, `estado` (programado, en_juego, suspendido, aplazado), `recibido_en`, `fuente` | De aquí sale el **corte** (§C.6) |
| `resultado` | aserción de desenlace | `partido_id`, `estado` (completado, retirada, walkover, descalificado, cancelado), `ganador` (1/2/NULL), `retira` (1/2/NULL), `sets` (jsonb: `[[g1,g2,tb1,tb2],…]`), `sets_completos`, `duracion_min` (NULL si falta, nunca 0), `recibido_en`, `fuente` | Retirada/walkover/cancelado = nulo para la mayoría de mercados (§I.9). PropLine **no** escribe aquí |
| `estadistica` | jugador × partido × fuente | `partido_id`, `lado` (1/2), `aces`, `dobles_faltas`, `puntos_saque`, `primeros_dentro`, `primeros_ganados`, `segundos_ganados`, `juegos_saque`, `bp_salvados`, `bp_afrontados`, `recibido_en`, `fuente` | Comprobaciones: `primeros_ganados ≤ primeros_dentro ≤ puntos_saque`, `bp_salvados ≤ bp_afrontados`; NULL ≠ 0 |
| `juego_pbp` | juego de un partido | `partido_id`, `set_n`, `juego_n`, `sacador` (1/2), `puntos` (texto `S`/`R` en orden), `es_tiebreak`, `recibido_en`, `fuente` | SofaScore (20.816 partidos con punto a punto, aud. §1) y MCP (~11.800, solo local). Permite inferir el primer sacador histórico y las pruebas de presión (§E) |
| `ranking` | jugador × lunes de publicación | `circuito`, `fecha_publicacion` (lunes), `jugador_id`, `posicion`, `puntos`, `origen` (oficial_capturado, tml_por_partido, serie_publica), `recibido_en`, `fuente` | Unión estrictamente `fecha_publicacion <= fecha_local_partido` y `recibido_en <= corte` (§C.4) |
| `precio_mercado` (derivado de originales, pero solo-anexar) | lado de un contrato observado | `recibo_ref` (id del recibo de PropLine o del fichero de Tennis-Data), `sha256_objeto`, `recibido_en`, `evento_fuente`, `partido_id` (NULL hasta enlazar), `casa`, `mercado`, `periodo`, `linea`, `lado`, `cuota_decimal`, `clase_cierre` (a/b/c), `marcas` (en_juego, caducada, dfs, bolsa, suspendida) | Tennis-Data entra con `clase_cierre='b'` y sin hora. Es referencia: el motor no lo lee para predecir |
| `enlace_evento` | evento de una fuente de cuotas → partido | `fuente`, `evento_fuente`, `partido_id`, `metodo`, `recibido_en` | Sin enlace único no hay comparación (§B.4) |
| `artefacto` | artefacto de modelo registrado | `sha256`, `tipo`, `version_modelo`, `informe_compuertas` (jsonb), `registrado_en` | Solo-anexar |
| `artefacto_activo` | activación | `sha256`, `activado_en`, `aprobado_en_chat` (texto de referencia), `imagen` | La vuelta atrás es otra fila (§H) |
| `pronostico` | sello | `pronostico_id`, `partido_id`, `version_modelo`, `version_datos`, `corte`, `sellado_en`, `entradas` (jsonb: estados y rasgos usados), `distribucion` (jsonb: marcador conjunto comprimido + mercados), `referencia_mercado` (jsonb: id del recibo de PropLine visto, sin entrar en el modelo), `hash_previo`, `hash` ; `UNIQUE(partido_id, version_modelo, corte)` | Cadena de hashes con candado de aviso (§H.3) |

Volumen esperado (dato para dimensionar): TML 492.251 partidos (aud. §3) → ~0,5 M filas en `partido` y `resultado`, ~0,5 M en `estadistica` (249.938 partidos aptos × 2 lados); punto a punto ~21 mil partidos de SofaScore. Tamaño total en disco: **no medido**; por órdenes de magnitud cabe en unos pocos GB.

### A.4 Inmutabilidad y lectura punto en el tiempo

- Disparadores `BEFORE UPDATE OR DELETE` y `BEFORE TRUNCATE` **por sentencia** en todas las tablas de evidencia (fallan aunque no haya filas afectadas, como `nba.rechazar_cambio`). Prueba obligatoria: `DELETE … WHERE false` y `TRUNCATE … CASCADE` fallan también para el dueño.
- **Única puerta de lectura del motor**: funciones `tenis.*_a_las(corte timestamptz)` que devuelven, por clave lógica, la aserción vigente con `recibido_en <= corte` (empate: prioridad de la fuente, luego la más reciente, luego el id mayor). El motor no tiene SELECT directo sobre las tablas de evidencia (permiso del rol), solo sobre esas funciones.
- **Historia retrospectiva** (TML, Tennis-Data, MCP, SofaScore descargado en nov-2026): su `recibido_en` es la fecha de adquisición, no la del partido. Igual que NBA (`pit.py`, progreso 2-nov), se acepta por **fecha del partido** con la marca `retro=true` en el recibo, y la regla escrita: un dato retro de un partido solo es visible para cortes **posteriores al final de la semana del partido** (TML no tiene hora: aud. §3). Un dato retro nunca puede alimentar un sello en vivo de un partido cuya fecha sea igual o anterior a su recepción.
- Rasgos prohibidos por construcción (aud. §5.1): ranking «de hoy» de SofaScore, `firstToServe`, `time.periodN` y `point` del propio partido, `h2h` y `team_streaks` capturados después. Los cargadores **no** los copian a la evidencia de rasgos (se quedan en el original), así que ningún módulo puede leerlos por error.

### A.5 Contratos tipados en las fronteras

Base común (principio de NBA, `contratos/base.py`): Pydantic `strict=True, extra="forbid", frozen=True, allow_inf_nan=False`; instantes con zona; probabilidades en [0, 1]; probabilidad de punto en **(0, 1) abierto**; hashes de 64 hex. Fronteras (propuesta):

| Contrato | Cruza | Reglas tenis-específicas |
|---|---|---|
| `PartidoPrevio` | lectura PIT → modelo | dos jugadores distintos y resueltos; formato conocido (mejor_de ∈ {3,5}, regla del set decisivo); superficie e indoor de la edición; corte < inicio programado más temprano |
| `EstadoJugador` | filtro → modelo | media y varianza finitas, varianza > 0; `n_partidos_previos` ≥ 0; `minutos_96h` NULL solo si se declara `fatiga_desconocida` |
| `ParametrosPunto` | modelo → simulador | `p1, p2 ∈ [0,02; 0,98]` (fuera de ese rango se rechaza y alerta: ni el saque más dominante medido llega ahí); matriz de covarianza simétrica definida positiva |
| `DistribucionPartido` | simulador → sellado/API | suma de probabilidades = 1 ± 1e-9; soporte físico (§G.6); mercados derivados coherentes con la conjunta (recalculados y comparados antes de sellar) |
| `PronosticoSellado` | base → API | mismo esquema que lo sellado; si no cumple, la API responde **502** y alerta (lección NBA) |

## B. Identidad de jugadores y torneos

### B.1 Jugadores

Datos de partida: 94 nombres normalizados con más de un id y 41 ids con más de un nombre en el crudo TML; 47 de 2.299 partidos WTA de 2026 todavía con id alterno `3xxxxx` tras el puente v3; el puente v3 fusionó 5 alias por fecha de nacimiento y confirmó 14 distintos; homónimos e ids alternos ATP **no medidos** (inv. datos §7; CSV `identidad_puente_resumen`). El «54 % excluido» de la auditoría del 19-oct son partidos aún en descarga: se vuelve a medir cuando termine (premisa 5).

Orden de resolución (propuesta), de más a menos fiable; cada paso escribe un `jugador_alias` con su `metodo`:

1. **Id exacto del proveedor ya conocido** (TML/Sackmann `player_id`, SofaScore `team.id`, API-Tennis `player_key`, SportsAPIPro id). Dos ids del mismo proveedor que apuntan a la misma persona (caso WTA `3xxxxx`) se fusionan solo con prueba: misma fecha de nacimiento **y** mismo nombre normalizado, o una equivalencia manual firmada.
2. **Nombre normalizado + fecha de nacimiento** (sin tildes, minúsculas, apellidos compuestos unidos, orden nombre/apellido indiferente). Si el nombre coincide y la fecha difiere → personas distintas (se registra como «confirmado distinto»).
3. **Contexto del partido** solo para fuentes sin id ni fecha de nacimiento (Tennis-Data «Apellido I.», PropLine y nombres de casas): se acepta si **los dos** jugadores del partido resuelven a la vez, en el mismo circuito, con fecha ±1 día y torneo compatible, y la pareja es única. Nunca difuso entre circuitos (lección de fútbol `cross_league`: solo coincidencia exacta cuando hay varias bolsas).
4. **Manual** (fichero de equivalencias versionado en el repo, con autor y fecha); se usa para los casos de la cola.

Lo que no resuelve ningún paso va a `sin_resolver` y **no se predice**.

### B.2 Torneos, ediciones, sedes y superficie

- **Torneo** estable a lo largo de los años (clave por el código del proveedor: la parte fija del `tourney_id` de TML, el `uniqueTournament.id` de SofaScore, el `tournament_key` de API-Tennis); las equivalencias se guardan como alias de torneo, igual que los jugadores.
- **Edición** = torneo × temporada, con `lunes_semana` (TML trae el inicio de semana como fecha: aud. §3), `fecha_fin`, sede, huso IANA, superficie, indoor y formato. Superficie por edición (un torneo puede cambiarla); fuentes en orden: SofaScore `groundType` (distingue «Hardcourt indoor» y «Red clay indoor»: CSV `sofascore_local_resumen_circuito_nivel_superficie`) > Tennis-Data columna `Court` (Indoor/Outdoor; su cobertura en nuestros 47 ficheros: **no medida**) > TML `surface` (sin indoor; «Carpet» se trata como indoor salvo prueba en contra) > registro de sedes del motor actual.
- **Categorías de superficie del modelo** (propuesta): `Clay`, `Grass`, `Hard` (exterior), `Indoor` (dura o moqueta bajo techo). La tierra bajo techo (p. ej. «Red clay indoor», 334 partidos WTA en SofaScore 2023-26) queda en `Clay` con una covariable `indoor` encogida a cero (§D.3). Indoor desconocido → la edición no se puede sellar hasta resolverlo (y se alerta); en el entrenamiento histórico, indoor desconocido usa la categoría de la superficie con `indoor=NULL` como nivel propio encogido.
- **Huso horario**: de la sede. Las fechas locales del partido se calculan con él (el ejemplo de Indian Wells difiere entre UTC y hora local: aud. §5.1).

### B.3 Dobles y partidos sin resolver

- **Dobles excluidos** en la carga: nombres con «/», `team.type` de pareja en SofaScore, eventos de PropLine con dos nombres por lado. Hoy hay 0 dobles en TML, SofaScore y MCP (aud. §3); la exclusión es defensiva para PropLine y las fuentes vivas.
- **Partidos sin resolver**: se guardan en `sin_resolver` con motivo; no entran en el entrenamiento ni se sellan. **Se miden siempre**: tasa semanal por circuito y nivel. Alerta por Telegram si en ATP/WTA principal la tasa supera el 2 % de los partidos de la semana a las 48 h (propuesta; el 2 % es la cifra residual medida en WTA 2026 tras el puente v3, inv. datos §7).
- **Riesgo de sesgo**: excluir partidos sin resolver no es neutral (suelen ser jugadores nuevos, que son justo donde el modelo falla más: <20 partidos previos +0,056 ATP y +0,066 WTA frente al cierre, aud. §6.2). Por eso la tasa entra en la compuerta G-identidad (§I) y en el informe de cada evaluación.

### B.4 Enlace con las fuentes de cuotas

- PropLine: `event.id` + nombres + `commence_time` + `tour` (inv. cuotas §7). Se enlaza con el paso 3 de B.1 (los dos jugadores, mismo circuito, fecha ±1 día). En el piloto solo 55 de 173 eventos eran ATP/WTA principal (31,8 %); el resto (ITF, Challenger, UTR) **no se enlaza** en la beta (sin resultados propios en vivo).
- Tennis-Data: sin id (inv. cuotas §7); paso 3 de B.1. El emparejamiento previo del motor actual (`odds_matched`, 45,1 % de filas, criterio sin documentar) **no se reutiliza**; la tasa nueva se mide y se publica en el informe de evaluación (gate de cobertura del cruce en §I).

## C. Pipeline de captura

### C.1 Fuentes, papel y cadencia (propuesta)

| Fuente | Papel | Cuándo | Dónde corre | Coste |
|---|---|---|---|---|
| TML (originales CSV) | Historia 1967→hoy: partidos, resultados, estadísticas de saque, ranking por partido | Carga histórica una vez; refresco semanal los lunes (TML publica por semanas; el motor actual lo baja lunes 11:00 Berlín, inv. datos §11) | Colector del VPS (solo descarga y carga, no entrena) | 0 |
| SofaScore local (`SOFASCORE/data/v3`) | 2023→hoy ATP/WTA: hora real de inicio, duración por set (fatiga), punto a punto, indoor | Carga histórica cuando termine la descarga en curso (premisa 5); subida de originales al árbol del VPS con el script idempotente de 6 conexiones (memoria «Subidas al VPS en paralelo») | PC → VPS | 0 |
| SofaScore VPS vía Apify (`~/sofascore-apify`) | Duraciones y punto a punto de partidos recientes | Lo que ya captura (cada 6 días); **uso para tenis pendiente de medir y de tu OK** (es de pago) | VPS | Dentro del tope existente; uso nuevo = decisión D4 |
| Calendario/resultados en vivo (API-Tennis hasta el 1-nov; hoy `--source auto` con SportsAPIPro) | Orden de juego, estado, marcador por sets, retiradas | Cada hora (`:25`), con el tope de SportsAPIPro (100/día compartidas) | VPS | 0 nuevo si se reutilizan los recibos del colector actual; decisión D3 |
| PropLine (archivo compartido) | Precios de referencia (todos los mercados), `commence_time`, estado | **No se pide nada**: se lee el archivo del recolector horario (`read_two_way`, `read_closing`, `newest`) | VPS | 0 (decisión del 23-oct) |
| Tennis-Data (47 xls) | Historia del ganador, clase b, para evaluación retrospectiva | Carga única + ficheros nuevos manuales | PC | 0 |
| MCP | Diagnósticos (IID, suma de p, presión) | Carga única, **solo en la copia local** (CC BY-NC-SA, sesgado a partidos destacados) | PC | 0 |
| Ranking oficial semanal | Prior de jugadores con poca historia | Lunes (y martes de reintento) | VPS | 2 peticiones/semana de SportsAPIPro (decisión D2) |

Regla de oro: **un colector por fuente**, cada uno con su `flock -n /var/lock/tenis-<fuente>.lock`; si el candado está tomado, la pasada termina sin error y lo anota. Ninguna fuente sustituye a otra en silencio (sin fallback automático de cuotas; para resultados, prioridad explícita por fuente en `tenis.fuente` y conflictos marcados).

### C.2 Idempotencia y avance del estado

1. Descargar → escribir el objeto por contenido (`sha256`) de forma atómica → insertar `recibo` (`UNIQUE(fuente, recurso, sha256)`; un mismo contenido recibido otra vez solo añade la recepción).
2. Analizar el original → filas de evidencia con `recibo_id` en **una transacción** junto con el avance del cursor (`tenis_op.cursor`). Si algo falla, se revierte todo y la próxima pasada repite el mismo lote sin duplicar (claves naturales `UNIQUE` por `(partido, fuente, recibo)`).
3. El cursor **solo avanza tras confirmar el lote**. Un 403/404 de un recurso aún no publicado (ranking del lunes, CSV semanal) es normal: se registra como «no publicado» y no alerta hasta pasado un umbral (propuesta: 36 h tras la hora esperada).
4. Presupuesto: cada proveedor con cupo tiene su libro diario en **UTC** (`tenis_op.presupuesto`), con tope propio por debajo del del proveedor y orden de prioridad: resultados > estado/orden de juego > ranking > estadísticas. Al tocar el tope, se para el tipo de petición de menos prioridad; 401/403/429 detienen la fuente ese día y alertan.

### C.3 Histórico y diario

- **Histórico (S2)**: TML completo (snapshot del VPS del 2-nov, más nuevo que el local: 2026.csv 2.658 frente a 2.482 líneas, inv. datos §10; decisión D5 para copiarlo al PC), Tennis-Data, SofaScore local, MCP (solo local). Cada fichero con su recibo `retro=true`.
- **Diario (S2 y S6)**: calendario y orden de juego (cada hora), resultados (cada hora hasta 3 días después), TML (lunes), ranking (lunes), PropLine (lectura del archivo cuando el motor sella y cuando el evaluador liquida).

### C.4 Ranking semanal: fuente y unión punto en el tiempo

No hay serie semanal (aud. §5.2; inv. datos §8). Propuesta en tres capas, por orden de uso:

1. **Hacia adelante (desde S2)**: captura del ranking oficial cada lunes (SportsAPIPro, como el exportador de estadísticas) con `recibido_en` real y `fecha_publicacion` = lunes de la clasificación. Es la única serie con PIT verdadero.
2. **Historia reconstruida de TML** (sin coste): cada fila de TML trae el ranking y los puntos de **ambos** jugadores (2025: ganador 99,7 %, perdedor 98,2 % rellenos; aud. §3). Se convierte en observaciones `(jugador, lunes_semana_del_torneo, posición, puntos, origen='tml_por_partido')`. Se usa como función escalón: última observación con `fecha_publicacion <= fecha del partido`. Limitación declarada: qué lunes usa TML para cada fila **no está verificado**; se verifica en S2 comparando con la capa 1 en las semanas que se solapen (desde el primer lunes capturado) y con la capa 3 si se aprueba.
3. **Serie pública histórica** (opcional, decisión D2): ficheros semanales de ranking de los repositorios públicos de Jeff Sackmann (`atp_rankings_*`, `wta_rankings_*`). Licencia CC BY-NC-SA (uso sin lucro con atribución, como el MCP); cobertura de 2025-26: **no medida**.

Unión (regla escrita en el módulo PIT): `fecha_publicacion <= fecha_local_inicio_partido` **y** `recibido_en <= corte`. La publicación es los lunes; un torneo que empieza el domingo (cuadro principal de un Grand Slam) usa el ranking del lunes anterior. El ranking solo entra en el **prior** de jugadores con poca historia (§D.6) y como covariable diagnóstica; la fuerza viene del rating.

### C.5 Qué se reconstruye para la fatiga

- Con hora y duración reales: SofaScore (`startTimestamp`, `time.periodN` de partidos **anteriores**: aud. §5.1). Cubre 2023→hoy ATP/WTA principal.
- Sin hora (TML): solo semana y ronda. El tiempo entre partidos se aproxima por la **secuencia de rondas** dentro de la edición (R1 < R2 < … < F) y por un calendario tipo de cada categoría; la aproximación se valida en S3 contra SofaScore 2023-26 (donde están las dos cosas) y se publica su error.
- Minutos faltantes: TML tiene minutos nulos en 260.099 de 492.251 partidos (aud. §5.2). Un minuto faltante **no es 0**: se estima con los juegos jugados (regresión minutos ~ juegos × circuito × superficie ajustada en el PC) y se marca `minutos_estimados`; si de un partido previo del cuadro no hay ni marcador (el jugador tuvo que jugarlo para llegar a esta ronda), la fatiga es **desconocida** y el partido no se sella (alerta).

### C.6 Corte del pronóstico (fijo, antes del primer servicio)

- **Corte** (propuesta): `corte = T_ref − 60 min`, con `T_ref` = la hora **más temprana posible** de inicio: la hora fija si la hay; si el partido va «a continuación» o «no antes de», la hora de inicio de la sesión de esa pista (un partido anterior puede acabar por walkover). Se usa el último `programa` con `recibido_en <= corte`.
- **Sello permitido** solo si: `ahora ≥ corte`; existe una observación de estado de ≤ 65 min que dice «no empezado»; y la inserción comprueba `clock_timestamp() < T_ref` en la misma sentencia (como NBA `sellado.py`). Si el partido aparece empezado o el estado está caducado, **no se sella** y se registra como `no_sellado_tarde` (cuenta para la compuerta de cobertura operativa).
- Un cron atrasado usa el mismo corte (mismos datos) y G-fuga sigue valiendo (lección NBA, progreso 3-nov). Nunca se sella después del primer servicio.
- Hora reprogramada después del sello (lluvia, retraso): el sello sigue valiendo para ese corte; si el partido se aplaza a otro día, se permite un sello nuevo con su corte nuevo (otra fila; la clave única incluye `corte`).

## D. Modelo jerárquico: saque/resto, rating de resultados, superficie y fatiga

### D.1 Por qué dos piezas (lo que dicen los datos)

- Un modelo **solo por puntos** pierde frente a Elo en el ganador (A01 IID 0,63-0,68 frente a Elo 0,59; A06 0,592 frente a 0,586; A12 0,6537 frente a 0,6474: lit. C.i) y nuestro Markov del motor actual queda +0,061 (ATP) y +0,095 (WTA) peor que la media de casas y sobreconfiado (pendiente 0,54 y 0,43: aud. §6.3).
- Al inicio del partido la probabilidad de ganar depende casi solo de **p_A − p_B**; la **suma** gobierna duración y totales (A26 [VF], O'Malley citado en A29/A30 [VT]: lit. C.i). A26 propone estimar la diferencia con resultados y la suma con puntos.
- Propuesta: **R** = rating dinámico ajustado con resultados (da la diferencia y el ganador); **P** = modelo jerárquico de puntos al saque/resto (da la suma); **C** = inversión exacta que los une. El ganador publicado es el de R (calibrado); todos los demás mercados salen de la misma distribución conjunta construida con (suma de P, diferencia que reproduce R).

Notación: partido m entre A = `jugador_1` y B = `jugador_2`; circuito c ∈ {ATP, WTA} (**parámetros separados por circuito**, código común: lit. F17); superficie s ∈ {Clay, Grass, Hard, Indoor} (§B.2); formato f (mejor de 3/5, regla del set decisivo); t = instante del corte; logit(x) = ln(x/(1−x)), expit su inversa.

### D.2 Pieza P: probabilidad de punto al saque/resto (la suma)

Para el saque de A contra el resto de B (simétrico para B):

    logit p_{A,m} = μ_{c,s}(t) + κ^P_{c,s} · (α_A(t) − β_B(t)) + (a_{A,s}(t) − b_{B,s}(t)) + ε_{A,m}
    logit p_{B,m} = μ_{c,s}(t) + κ^P_{c,s} · (α_B(t) − β_A(t)) + (a_{B,s}(t) − b_{A,s}(t)) + ε_{B,m}

- μ_{c,s}(t): nivel del saque en el circuito y la superficie, con paseo aleatorio lento (el dominio del saque cambia con los años: A25, B04, T26; lit. C.v.6).
- α_i, β_i: habilidad de saque y de resto, con paseo aleatorio gaussiano en el tiempo, α_i(t') = α_i(t) + N(0, τ_α²·(t' − t)).
- **Superficie, siempre presente**: μ_{c,s} (nivel), κ^P_{c,s} (multiplicador de la diferencia de habilidades: en hierba manda el sacador, en dura y tierra el restador pesa tanto como él: T17 [VF]), y desviaciones por jugador a_{i,·}, b_{i,·} ~ N₄(0, Σ_a), con Σ_a = diag(σ_s)·Ω·diag(σ_s) y Ω (correlaciones entre las 4 superficies) aprendida con un prior LKJ(2). La literatura coincide en que tierra–hierba es el par más alejado (lit. C.iii); por eso Ω no se fija.
- Efecto del partido («forma del día»): (ε_A, ε_B) ~ N₂(0, Σ_ε) con desviación σ_ε y correlación ρ_ε. Valores de partida de A26 [VF]: DE 0,051 (H) / 0,040 (M) en probabilidad y correlación −0,45 / −0,64; en logit, a p ≈ 0,64, σ_ε ≈ 0,051/(0,64·0,36) ≈ 0,22 (H). Se re-estiman con nuestros datos (sobredispersión de los puntos de saque entre partidos en ~250 mil partidos de TML y en SofaScore).
- Verosimilitud: puntos de saque ganados W_A ~ Binomial(N_A, p_{A,m}) con W = primeros ganados + segundos ganados y N = puntos de saque (TML, SofaScore). Solo partidos completados; retiradas fuera.
- Valores de partida de las escalas (ATP, A06 [VT parcial/VF], solo como inicialización del ajuste, no como valores fijos): σ_α0 0,154; σ_β0 0,124; superficie 0,067; paseo bimestral 0,039 (saque) y 0,027 (resto).

Lo que P entrega al resto del motor: **Ŝ_m = E[p_{A,m} + p_{B,m}]** (y su varianza). La fatiga **no** entra en P por defecto: un penalizador simétrico sobre el saque y el resto del jugador cansado mueve la diferencia, no la suma. Un efecto de la fatiga sobre la suma (partidos más cortos o más largos) se prueba como coeficiente aparte φ^S, sin signo forzado y encogido a 0, dentro de la compuerta de totales.

### D.3 Pieza R: rating de resultados con superficie como multiplicador y fatiga como penalizador

    ρ_m = κ^R_{c,s} · (1 + Σ_k γ_k z_{k,m}) · (θ_A(t) − θ_B(t))          ← superficie (multiplicador) y contextos
          + (d_{A,s}(t) − d_{B,s}(t)) + ζ_c · ι_m · (d^ι_A − d^ι_B)      ← desviación de superficie por jugador (y tierra bajo techo)
          − Σ_{j=1,2} φ_j · (g_j(F_A) − g_j(F_B))                         ← fatiga, φ_j ≥ 0

    P_R(A gana) = M̄_f( expit(ℓ̄_{c,s} + ρ_m), expit(ℓ̄_{c,s} − ρ_m) ; Σ_m )

- θ_i(t): fuerza global del jugador; paseo aleatorio con varianza τ_θ²·Δt más un aumento por inactividad (> 60 días; Glicko/A05, T10 [VF]).
- **κ^R_{c,s} es el multiplicador principal de la superficie**: escala la diferencia de fuerza según la superficie. Identificación: κ^R_{c,Hard} ≡ 1; los demás con prior log κ ~ N(0, s_κ²). d_{i,s} ~ N₄(0, Σ_d) con la misma estructura que Σ_a: el **encogimiento jerárquico** hace que el peso de la historia propia de un jugador en una superficie sea, en la aproximación normal, w_{i,s} = n_{i,s} / (n_{i,s} + σ²_ruido/σ²_{d,s}); con pocos partidos en hierba, d_{i,Grass} ≈ 0 y manda θ_i (lit. C.iii: la superficie es real pero su parámetro está mal identificado; T17 encoge más en hierba).
- **Fatiga acumulada** (§C.5): F_{i,m} = Σ_{k ∈ K_i(m)} w(Δ_k)·minutos_k, con K_i(m) = partidos de i (cualquier torneo, previas incluidas) terminados en las **96 h** anteriores a T_ref(m), Δ_k en días, y w(Δ) = λ^Δ con λ = 0,75 como valor inicial (descuento de A07 [VT]; se ajusta en {0,5; 0,75; 0,9}, rejilla preregistrada). Dos bases: g_1(F) = F/60 (horas ponderadas) y g_2(F) = max(0, F − F₉₀)/60 (bisagra en el percentil 90 de F en el entrenamiento, congelado en cada origen), porque el único efecto con evidencia está en el extremo (A16: 5 sets frente a 3, Δw = −0,049, logit −0,184 (EE 0,039) [VT]). **φ_j ≥ 0 por construcción** (parametrización φ_j = softplus(u_j)) con prior semi-normal de escala s_φ estimada por máxima verosimilitud predictiva: si los datos no tienen señal, s_φ → 0 y la fatiga queda ≈ 0. Días de descanso **no** entran (A16: p = 0,533, n.s.).
- **Contextos** z_k (§F): semana previa a un Grand Slam, competición por equipos, JJOO. Modifican el multiplicador (el favorito domina menos o más), con γ_k ~ N(0, 0,1²) encogido a 0.
- **Enlace exacto del formato**: M̄_f es la probabilidad de ganar el partido del simulador (§G) en el formato f, integrada sobre Σ_m (forma del día + incertidumbre de parámetros), con ℓ̄_{c,s} = logit de la probabilidad media de punto al saque del circuito y la superficie (de P). Así el rating vive en la escala del punto y la diferencia entre mejor de 3 y mejor de 5 (o el tiebreak a 10 del set decisivo) sale exacta de la fórmula, sin la conversión aproximada K = √1,4 ≈ 1,183 (B03 [VT]), que queda como **diagnóstico** (comprobado aquí: con p 0,60/0,55 el cociente logit(m5)/logit(m3) es 1,263; K es un promedio sobre jugadores, no una identidad).
- Margen en juegos (WElo, T27 y A04 [VT]): término opcional de verosimilitud con peso ω ∈ [0, 1] sobre la proporción de juegos ganados; ω = 0 es «solo resultados». Se decide con la compuerta (los modelos que usan juegos salen mal calibrados si no se recalibran: lit. B.2.12).
- **Actualización** tras cada resultado: un paso de Newton/Laplace sobre la verosimilitud (B03: Glicko es un paso de Newton desde el prior [VF]): con estado x = (θ_A, θ_B, d_{A,s}, d_{B,s}) ~ N(m, V), V⁺ = (V⁻¹ + H)⁻¹ y m⁺ = m + V⁺·∇ℓ(m), con ∇ℓ y H calculados por diferencias exactas a través de M̄_f. Orden: por semana, edición y ronda (R1 < R2 < … < F; previas antes del cuadro). Walkovers y retiradas **no actualizan** el rating (contaminan: lit. C.ix), pero sus minutos sí cuentan para la fatiga del que jugó.

### D.4 Pieza C: unión por inversión exacta

1. Recalibración opcional: π_m = Cal(P_R(A)). Por defecto **identidad**; una capa de Platt ajustada con temporadas previas solo se activa si pasa su compuerta (§I.3). La línea base dice que casi no mejora (0,001–0,002: aud. §6.2), así que lo esperado es dejarla apagada.
2. Suma: Ŝ_m de P.
3. Diferencia: δ*_m único tal que

       M̄_f( Ŝ_m/2 + δ*, Ŝ_m/2 − δ* ; Σ_m ) = π_m

   M̄_f es estrictamente creciente en δ con la suma fija (teorema de invertibilidad de B03 [VF]; con la mezcla sigue siéndolo porque cada componente lo es). Se resuelve por bisección a tolerancia 1e-10. Si π_m está fuera del rango alcanzable con p ∈ [0,02; 0,98], el contrato rechaza el partido (alerta; no se sella).
4. Probabilidades de punto finales: p_A = Ŝ_m/2 + δ*, p_B = Ŝ_m/2 − δ*. **El ganador de la distribución conjunta coincide con π_m por construcción**; las demás probabilidades heredan la suma de P y la forma del día.

Comprobado aquí (consola, sin archivos): con Ŝ = 1,25, π = 0,70, mejor de 3, σ_ε = 0,22 y ρ_ε = −0,45, la bisección da δ* = 0,0311 (p_A = 0,6561, p_B = 0,5939) y la mezcla recalculada devuelve 0,700000. La forma del día pesa mucho: para p 0,66/0,60 la probabilidad de ganar a 3 sets pasa de 0,775 (sin efecto del partido) a 0,694 (con él). Es exactamente la sobreconfianza que mostraba el Markov crudo del motor actual.

### D.5 Cómo queda la superficie y la fatiga «obligatorias» sin forzar un efecto falso

- **Estructurales**: los términos κ_{c,s}, μ_{c,s}, d_{i,s}, a_{i,s}, b_{i,s}, φ_j existen siempre en la fórmula y en el código; ninguna configuración los quita.
- **Magnitud estimada con datos**: sus escalas (s_κ, σ_{d,s}, σ_{a,s}, s_φ) son hiperparámetros ajustados en el PC por máxima verosimilitud predictiva un paso adelante (la misma métrica del walk-forward). Si no hay señal, las escalas tienden a 0 y los efectos también: el modelo **no** puede inventar un efecto que los datos no sostienen.
- **Medidos con su propia compuerta** (G-superficie y G-fatiga, §I.7): comparación con el mismo modelo con esos términos anulados. Si no mejoran fuera de muestra, se **publica** que no mejoran y se dejan con sus escalas estimadas (cerca de 0). Nunca se sube un coeficiente a mano.
- Dato que obliga a la prudencia: la superficie ayudó en ATP y perjudicó en WTA en nuestra línea base (+0,039 → +0,036 frente a +0,036 → +0,038; CSV `linea_base_dif_vs_cierre_combinada`); nadie validó minutos acumulados fuera de muestra (lit. C.vi).

### D.6 Jugador sin historia (omitir y alertar; nunca un promedio silencioso)

n_prev = partidos con resultado del jugador en TML (gira, Challenger y previas) antes del corte.

| Caso | Qué hace el motor | Marca en el sello |
|---|---|---|
| n_prev = 0 y sin ranking PIT | **No se pronostica**; alerta `jugador_sin_historia` | — |
| n_prev = 0 con ranking PIT | Prior explícito θ₀ = r(puntos de ranking), con varianza grande, ajustado en el PC con la primera aparición de cada jugador histórico; d_{i,s} = 0 con su varianza a priori | `historia_corta`, `prior=ranking` |
| 0 < n_prev < 20 | Estado del filtro (que empezó en ese prior) | `historia_corta` |
| n_prev ≥ 20 | Estado del filtro | — |

Los partidos con `historia_corta` son ~20 % de la muestra ATP de la línea base (3.406 de ~16.700) y es el segmento que más falla (+0,056 ATP y +0,066 WTA frente al cierre: CSV `linea_base_segmentos`). Se evalúan aparte; si su compuerta de calibración falla, **no se publican** (se sellan para medir). El umbral 20 viene de la segmentación de la línea base; la ganancia del filtro se estabiliza tras ~20 partidos en T08 [J] (no citable sin el PDF).

### D.7 Incertidumbre de parámetros

Las varianzas del filtro (θ, d) y de P (α, β, μ) se propagan a (logit p_A, logit p_B) con el método delta: Σ_m = Σ_ε + J·V·Jᵀ. Esa misma Σ_m se usa en el enlace de R, en la inversión de C y en el simulador, para que el ganador y la conjunta integren la misma incertidumbre. Los intervalos publicados (p. ej. del total de juegos) salen de la conjunta, que ya la incluye.

### D.8 Qué se ajusta en el PC (y qué no se ajusta nunca en el VPS)

Hiperparámetros Ψ por circuito = {τ_θ, τ_d, τ_α, τ_β, aumento por inactividad, Σ_a, Σ_b, Σ_d (escalas y Ω), κ^P, κ^R, μ_{c,s} inicial, φ_j, λ, F₉₀, γ_k, ζ, ω, Σ_ε, prior por ranking r(·), recalibración}. Se ajustan maximizando la log-verosimilitud predictiva un paso adelante sobre las temporadas de entrenamiento de cada origen (L-BFGS con reproducción del filtro). El VPS solo **reproduce el filtro** con Ψ congelado (eso es inferencia, no entrenamiento) y simula.

## E. Presión («factor clutch»): recomendación y prueba preregistrada

### E.1 Evidencia

| Estudio | Qué mide | Cifra | Peso |
|---|---|---|---|
| A02 (Wimbledon 1992-95, 86.298 puntos) | Desviación del IID por punto | Punto anterior ±0,3–0,7 pp; 30-40 a 5-5 del set decisivo −4,6 (H) / −4,8 (M) pp; **fuera de muestra el no-iid no mejora al iid** (RMSE 0,4778 en ambos) [VT] | El mejor diseño del corpus (lit. B.2.3) |
| T31 (Sackmann 2010-24) | Sesgo del IID en el total de juegos | +0,792 (EE 0,035) ATP y +0,892 (EE 0,029) WTA, concentrado en partidos igualados; **en muestra y con p realizadas**, no pronosticadas [VT] | Única cifra del corpus para totales |
| B16 (190 partidos GS 2024) | Sets independientes con un p por partido | 3-0: 64 observados frente a 52,9; 3-2: 23 frente a 36,4 [VF] | Diagnóstico: falta varianza entre partidos; confunde heterogeneidad con dependencia |
| A26 | Heterogeneidad entre partidos | DE de la forma del día 0,051 (H) / 0,040 (M) [VF] | Explica parte de lo anterior sin dependencia |
| T19 | «Momentum» | χ² = 111,5, pero cuenta el fin del juego como fin de racha y no controla al sacador [VF] | **Descartado** (lit. tabla A) |
| A33 | «Clutch average» | Discrimina al ganador **dentro** del partido; persistencia entre partidos: no consta [VF] | Descartado como pre-partido |
| T39 | Puntos de break | 62,6 % frente a 65,0 % del sacador, n.s. (238 puntos) [J] | Débil |

Hándicaps de juegos y de sets: el corpus **no aporta** cifra del error del IID (lit. C.ii).

### E.2 Recomendación

**IID condicionado al sacador y a la calidad de ambos jugadores + efecto aleatorio del partido**, sin multiplicador de presión por jugador. Motivos: (1) el único estudio con validación fuera de muestra (A02) no gana nada con el no-iid; (2) ningún estudio del corpus valida un «clutch» persistente por jugador; (3) las desviaciones medidas están en la **forma** de las distribuciones (totales, sets) y la heterogeneidad entre partidos las produce también (lit. C.ii).

**Margen de error que se declara** (en la página de cada mercado afectado y en la documentación del modelo):
- Totales de juegos: referencia de la literatura +0,79 (ATP) / +0,89 (WTA) juegos de infraestimación del IID **con p realizadas**; nuestro sesgo con p pronosticadas: **no medido** hasta S4, se mide en el walk-forward y se publica con su IC.
- Hándicap de juegos, hándicap de sets, resultado exacto en sets, tiebreak: sin cifra en el corpus; **no medido**; se mide en S4 y se publica.

### E.3 Corrección (dentro del modelo generativo; nunca un retoque marginal)

Un ajuste aplicado solo al mercado de totales rompería la coherencia con el hándicap y los sets. Por eso las correcciones son **parámetros del modelo conjunto**:
1. Efecto aleatorio del partido Σ_ε (ya en D.2): ensancha sets y totales (diagnóstico de B16).
2. Efecto aleatorio **por set** ε_{i,m,k} ~ N(0, σ_set²) opcional: variación de p entre sets del mismo partido; σ_set se estima con punto a punto (SofaScore, MCP) y por defecto es 0.
3. «Recalibración de totales» = ajustar σ_ε y σ_set (y, si pasa E.4, γ_I) para que el PIT aleatorizado del total de juegos sea uniforme en las temporadas de entrenamiento. Se adopta solo si mejora el RPS de totales fuera de muestra (§I).

### E.4 Prueba preregistrada que decidiría añadir presión

Fijada ahora, antes de mirar los datos:

- **Paso 0 (persistencia, barato y con mucha muestra).** Con TML (bp_salvados y bp_afrontados en ~250 mil partidos): residuo por jugador y partido r_{i,m} = bp_salvados − bp_afrontados·p̃_{i,m}, con p̃ = proporción de puntos de saque ganados **fuera** de los break points, (W − bp_salvados)/(N − bp_afrontados). Media estandarizada por jugador y temporada (jugadores con ≥ 50 break points afrontados en cada una). **Criterio**: correlación de Spearman entre temporadas consecutivas; si r < 0,10 o su IC95 (bootstrap por jugador) incluye 0, **no hay clutch por jugador** y P2 se descarta sin más pruebas.
- **Modelos**: P0 = IID + efecto del partido (+ efecto por set si pasó E.3); P1 = P0 + un parámetro global por circuito γ_I: logit p_punto = logit p − γ_I·I(punto), con I la importancia del punto (Morris, calculable con el propio simulador); P2 = P1 + desviación por jugador c_i ~ N(0, σ_c²) sobre γ_I.
- **Datos**: ajuste con punto a punto de SofaScore 2023-2025 (y el MCP solo como diagnóstico, por su sesgo); prueba en SofaScore 2026 y en el walk-forward con marcadores por set de TML 2019-2026 (§J).
- **Métricas**: RPS del total de juegos (multiclase), log-loss del resultado exacto en sets, Brier de tiebreak sí/no, log-loss del hándicap de juegos en las líneas ±1,5…±5,5; control: log-loss del ganador.
- **Regla de adopción**: P1 entra si ΔRPS(totales) < 0 con IC95 (bootstrap por partido, 2.000 réplicas) que excluye 0 **en ese circuito**, ningún otro mercado empeora más allá de su IC y el ganador no empeora más de 0,001 de log-loss. P2 entra solo si pasó el paso 0 y bate a P1 con la misma regla. Muestra mínima de prueba: 2.000 partidos por circuito con marcador completo.
- Si nada pasa: se queda P0 y se publica el margen medido. Repetir la prueba solo con una temporada nueva completa, no antes.

## F. Contextos especiales y formatos

### F.1 Semana previa a un Grand Slam

Sin evidencia en el corpus (lit. C.x). Se mide con nuestros datos:
- **Identificación por calendario**: ediciones de nivel de gira cuyo `lunes_semana` es el lunes inmediatamente anterior al inicio del cuadro principal de un Grand Slam (fecha de la edición del GS en `edicion`). Variable z_preGS = 1 para sus partidos. Variante preregistrada: z_preGS × «el favorito por θ está en el cuadro del GS» (protegerse antes del GS sería cosa de los favoritos).
- **Tratamiento**: se entrena con todos los partidos; γ_preGS modifica el multiplicador de fuerza (§D.3) y está encogido a 0. Se mide además la tasa de walkovers y retiradas esas semanas frente al resto (afecta a la liquidación, no al modelo).
- **Medición**: posterior de γ_preGS con IC y Δlog-loss del segmento. Tamaño del segmento por año y circuito: **no medido** (se cuenta en S3 con TML).

### F.2 Competiciones por equipos y JJOO

- **Identificación**: categoría de la edición (§B.2). En TML, los niveles `D` (ATP 14.320, WTA 8.732 partidos) y `O` (ATP 621, WTA 572) parecen Copa Davis/BJK y JJOO, pero **el significado de los códigos no está verificado** (CSV `canon_circuito_nivel`); se verifica en S2 contra los nombres de torneo. United Cup/ATP Cup: código **no medido**. Laver Cup y exhibiciones: fuera (no oficiales).
- **Tratamiento**: (1) partidos «muertos» (eliminatoria ya decidida) fuera del entrenamiento y del rating; si la estructura de la eliminatoria no se puede reconstruir, **todos** los partidos por equipos quedan fuera del rating y se miden aparte; (2) el resto entra con su z_k (equipos, JJOO) encogido a 0; (3) **no se publican** en la beta.

### F.3 Formatos que el simulador soporta (el formato va por edición; desconocido = no se sella)

| Formato | Regla | Fuente de la fórmula |
|---|---|---|
| Mejor de 3, tiebreak a 7 en 6-6 en todos los sets | Gira regular | A31, T32 |
| Mejor de 5, tiebreak a 10 en 6-6 del set decisivo | Grand Slam masculino desde 2022 (T32 [VF]) | T32 Prop. 3.4 y Teor. 4.1 |
| Mejor de 3 con tiebreak a 10 en 6-6 del set decisivo | Grand Slam femenino desde 2022 (misma regla) | T32 |
| Set decisivo con ventaja (sin tiebreak) | Historia (formatos anteriores de algunos GS y Copa Davis); desde 6-6 gana quien saca dos juegos de diferencia: P = g_A(1−g_B) / (g_A(1−g_B) + (1−g_A)g_B) con alternancia | Derivación propia con la misma lógica que el «desde iguales» de A07 |
| Juego con punto decisivo (sin ventaja) | g* = p⁴(−20p³ + 70p² − 84p + 35) | A26 [VF], comprobado en lit. (0,8002 a p = 0,65) |
| Supertiebreak en lugar del 3.er set, sets a 4, Fast4, NextGen | — | **No soportado**: no se sella; fuera del entrenamiento |

El calendario exacto de cambios de reglas por torneo y año (p. ej. cuándo adoptó cada GS su tiebreak decisivo) se carga **por edición** en S2 desde las fuentes, no desde memoria; lo que no se pueda verificar queda como formato desconocido.

### F.4 Indoor y otros

- Indoor: categoría de superficie propia (§B.2).
- Altitud y calor: sin evidencia en el corpus para el ganador (lit. C.x; S04 solo sobre el saque, efecto pequeño). La altitud de la sede se guarda (NULL si no se conoce) y **no entra** en el modelo v1; queda como medición exploratoria posterior.

## G. Simulador: distribución conjunta y mercados

### G.1 Principio

Dentro del partido todo es **analítico** (programación dinámica exacta bajo IID condicionado): Monte Carlo sobra ahí (A26 calcula exacto; T32 difiere ≤ 0,004 de 50.000 simulaciones: lit. C.i). La incertidumbre (forma del día + parámetros) se integra **fuera**, por cuadratura gaussiana determinista; Monte Carlo con semilla fija solo para componentes no gaussianas (G.5). Todos los mercados salen de **una sola** distribución conjunta.

### G.2 Piezas cerradas (q = 1 − p)

- Juego al saque (A31 ec. 5 [VT]):

      g(p) = p⁴(1 + 4q + 10q²) + 20 p³q³ · p² / (1 − 2pq)

  Formas equivalentes de A26 y T31 (lit. C.i). Comprobado aquí: g(0,5) = 0,5000 y g(0,65) = 0,8296 (A26 imprime 0,830).
- Juego con punto decisivo: g*(p) = p⁴(−20p³ + 70p² − 84p + 35) (A26 [VF]).
- Tiebreak a K puntos (K = 7 o 10) con alternancia ABBA: programación dinámica sobre el marcador de puntos hasta (K−1, K−1) y, desde la igualdad, Q = p_A q_B / (p_A q_B + q_A p_B) (A31, B03, T32 [VF]). Denominador p_A q_B + q_A p_B > 0 siempre que p ∈ (0, 1); con p_A = p_B = 1 sería 0 (el tiebreak no termina): por eso el contrato exige p ∈ [0,02; 0,98] (§A.5) y la prueba absurda lo verifica.
- Set con primer sacador σ ∈ {A, B}: programación dinámica sobre el marcador de juegos (x, y), sacando σ los juegos impares; en 6-6, tiebreak que empieza sacando σ. Salida: tabla T_σ(x, y) con x–y ∈ {6-0…6-4, 7-5, 7-6} y simétricos (y, en formatos de ventaja, x ≥ 6 con |x − y| = 2, truncando la cola en 1e-12 y declarando la masa truncada).
- **Sacador del set siguiente**: el que no sacó el último juego; con tiebreak (juego 13, que empieza σ), saca primero el otro. Es decir, σ' = σ si x + y es par y σ' = ¬σ si es impar (contando el tiebreak como juego). Así el primer sacador se propaga por **paridad** entre sets (A31, T31).

### G.3 Distribución conjunta del partido

Estado de la programación dinámica entre sets: (s_A, s_B, G_A, G_B, n_TB, σ_siguiente), con s = sets ganados, G = juegos acumulados y n_TB = tiebreaks jugados; además se guarda aparte la tabla del 1.er set. Transición con T_σ. Para cada (p_A, p_B) y primer sacador σ₁:

    P(s_A, s_B, G_A, G_B, n_TB | p_A, p_B, σ₁)

Primer sacador desconocido (sorteo 5 min antes; `firstToServe` de SofaScore **prohibido**: aud. §5.1): mezcla 50/50 en el inicio, y la integración de la incertidumbre por cuadratura de Gauss–Hermite 2D sobre (u_A, u_B) ~ N₂(0, Σ_m) en escala logit:

    P(·) = ½ Σ_{σ₁∈{A,B}} Σ_{k,l=1..Q} w_k w_l · P(· | expit(logit p_A + u_A^{(k,l)}), expit(logit p_B + u_B^{(k,l)}), σ₁)

con (u_A, u_B)^{(k,l)} = L·(x_k, x_l), L·Lᵀ = Σ_m, y (x, w) los nodos y pesos de Hermite probabilista. Con el teorema de neutralidad (A31 [VT]) el ganador del set y del partido no depende de σ₁; los marcadores exactos y los totales sí (T32: A gana 6-1 con 0,0947 si saca primero y 0,0485 si no [VT]), de ahí la mezcla.

Comprobado aquí: con p_A = 0,60 y p_B = 0,55, la programación dinámica reproduce T32 (set 0,6695; 6-1 0,0947 / 0,0485; 6-3 0,2042 / 0,1046; partido a 5 sets 0,7943 con 3-0 0,3001, 3-1 0,2975, 3-2 0,1967; P(6-6) = 0,1383 frente a 0,138) y A31 (p 0,6 frente a 0,5: 0,9513 a 5 sets y 0,9078 a 3, frente a 0,9079 impreso). Cuadratura: P(ganar) con Σ de D.4 da 0,693873 (Q = 5), 0,693789 (Q = 7), 0,693792 (Q = 9) y 0,693793 (Q = 15). Propuesta: **Q = 9** por eje (81 nodos), con verificación de Q = 9 frente a Q = 21 en la compuerta.

### G.4 Mercados derivados (todos de la misma conjunta)

Con N_s = s_A + s_B, T = G_A + G_B, H = G_A − G_B:

| Mercado | Probabilidad |
|---|---|
| Ganador | P(s_A > s_B) (= π_m por construcción, §D.4) |
| 1.er set | Σ de la tabla del 1.er set con x > y (mezcla en σ₁ y cuadratura) |
| Hándicap de sets h (p. ej. −1,5) | P(s_A − s_B + h > 0) |
| Total de sets L | P(N_s > L) |
| Resultado exacto en sets | P(s_A = i, s_B = j) para cada (i, j) final |
| Hándicap de juegos h | P(H + h > 0); con h entero, P(H + h = 0) es «push» y se excluye de la puntuación (§I.9) |
| Total de juegos L | P(T > L); con L entero, P(T = L) es push |
| Tiebreak sí/no | P(n_TB ≥ 1) |
| Total de juegos del 1.er set, ganador del set k | de las tablas por set con σ propagado |
| Break en el 1.er set (S7, no publicable) | programación dinámica del 1.er set con un indicador de «hubo break» por jugador |
| Aces y dobles faltas (S7, no publicables) | recuento sobre el número de puntos de saque de cada jugador, cuya distribución sale de la misma programación dinámica (número de puntos por juego), con tasas por punto de saque jerárquicas (§K, S7) |

La conjunta se sella comprimida (probabilidades de (s_A, s_B, G_A, G_B, n_TB) por encima de 1e-9, más la tabla del 1.er set) para que la API calcule cualquier línea sin volver a simular (lección NBA: 199 cuantiles; aquí el soporte es discreto y pequeño).

### G.5 Monte Carlo (solo donde no hay forma cerrada) y su error

Se usa Monte Carlo únicamente si la incertidumbre de algún parámetro no es gaussiana (p. ej. propagar la incertidumbre de los hiperparámetros Ψ con B ajustes bootstrap). Entonces p̂_N = (1/N) Σ_n h(Ψ_n), donde h es la probabilidad **exacta** del mercado dado Ψ_n (la parte interna sigue siendo analítica). Error:

    EE(p̂_N) = s_h / √N,    s_h² = Var_Ψ[h(Ψ)]

Meta: el **1 % peor** de los errores absolutos sobre todos los (partido, mercado, línea) de un conjunto de 500 partidos < 0,5 pp. Como cada error tiene percentil 99 ≈ 2,576·EE, basta EE ≤ 0,005/2,576 en cada mercado: N ≥ (2,576·s_h/0,005)². Comprobado aquí: s_h = 0,5 (peor caso de una Bernoulli, si la parte interna también se simulara) → N = 66.358; s_h = 0,1 → 2.655; s_h = 0,05 → 664. Propuesta: N = 8.192 (Sobol aleatorizado, **semilla fija** registrada en `version_modelo`), que da EE ≤ 0,0011 si s_h ≤ 0,1; se **mide** con R = 20 aleatorizaciones independientes (EE empírico = DE entre réplicas) y con una referencia de N_ref = 16·N; si el percentil 99 supera 0,5 pp, se duplica N. La cuadratura determinista (G.3) se mide igual: |P_{Q=9} − P_{Q=21}| máximo < 1e-4.

### G.6 Física del marcador (comprobaciones del contrato y propiedades aleatorias)

- Sets válidos: 6-0…6-4, 7-5, 7-6 (y simétricos); tiebreak a 7 con ganador ≥ 7 y diferencia ≥ 2 (a 10, ≥ 10); sets de ventaja con x ≥ 6 y |x − y| = 2.
- Mejor de 3: N_s ∈ {2, 3}; T ∈ [12, 39]; si N_s = 3, **T ≥ 18** (6-0, 0-6, 6-0). Mejor de 5: N_s ∈ {3, 4, 5}; T ∈ [18, 65]; N_s = 4 ⇒ T ≥ 24; N_s = 5 ⇒ T ≥ 30. n_TB ≤ N_s. Toda probabilidad fuera del soporte debe ser **exactamente 0**.
- Propiedades (pruebas con `hypothesis` sobre p_A, p_B ∈ [0,02; 0,98], formatos y Σ aleatorios): suma = 1 ± 1e-12; ganador = suma de resultados exactos con s_A > s_B; P(ganar) creciente en p_A y decreciente en p_B; simetría al intercambiar jugadores; neutralidad del set respecto a σ₁ (1e-12) y las cinco invariantes de A31 (P(6-0), P(6-1)+P(6-2), P(6-3)+P(6-4), P(7-5), P(6-6)); P(T > L) no creciente en L; P(H + h > 0) monótona en h; P(hándicap de sets −1,5) ≤ P(ganar); si p_A > p_B, P_mejor de 5(A) ≥ P_mejor de 3(A); coherencia entre el ganador del 1.er set y la tabla de sets.
- Reproducción de cifras publicadas como pruebas fijas: las de G.3 (T32, A31) con tolerancia 2e-4 (redondeo de los autores), g(0,65) = 0,830 y g*(0,65) = 0,800 (A26).

### G.7 Sensibilidad

Para cada mercado publicado se guardan ∂P/∂p_A y ∂P/∂p_B por diferencias centrales (h = 1e-4) en el punto medio (cuánto se mueve la probabilidad por 1 pp de saque). Sirve para dos cosas: explicar el pronóstico y comprobar que la propagación por el método delta de D.7 coincide con la cuadratura (diferencia máxima < 0,2 pp en la compuerta de coherencia).

## H. Qué se entrena en el PC y qué infiere el VPS

### H.1 Reparto

| Paso | Dónde | Qué |
|---|---|---|
| Restaurar la copia diaria de `tenis-db` en un Postgres local | PC | Mismo esquema; la base de producción no se toca |
| Exportar el conjunto PIT (Parquet) | PC | Desde las funciones `*_a_las`; huella = SHA-256 del Parquet canónico → `version_datos` |
| Ajustar Ψ por circuito y origen, evaluar walk-forward, compuertas | PC | §D.8, §I, §J |
| Producir artefactos y su informe | PC | H.2 |
| Registrar y activar un artefacto | VPS, **con tu OK en el chat** | Fila en `artefacto` y en `artefacto_activo` |
| Reproducir el filtro con Ψ congelado, simular, sellar, servir | VPS | Inferencia; nunca ajusta Ψ |

El reentrenamiento semanal dentro del contenedor del motor actual (`tennis_refresh_v1`, lunes 11:00: inv. datos §11) **no** se replica. El refresco de los datos de TML del lunes sí (es captura).

### H.2 Artefactos

- `tenis_parametros_<circuito>.json`: Ψ, rejillas preregistradas, semillas, versión del simulador, reglas de formato. JSON canónico (claves ordenadas, separadores fijos, LF, números con repr exacta); **huella** = SHA-256 de esos bytes; `version_modelo = "tenis-2.<menor>+<sha12>"`.
- `tenis_estado_<circuito>_<fecha>.parquet` (opcional, acelera el arranque): estado del filtro en una fecha; su huella va en el informe. El VPS puede reconstruirlo reproduciendo el filtro desde la evidencia, y G-fuga lo comprueba.
- `informe_compuertas.json`: resultados de §I con la huella de los datos y del artefacto.
- Sin `pickle` (seguridad y reproducibilidad). Los artefactos viajan en la imagen del motor (como los parámetros de props de NBA, progreso 3-nov) y su huella se recalcula al arrancar: si no coincide con la registrada, el motor no sella y alerta.

### H.3 Sellado (predecir → sellar → publicar)

- Cadena de hashes: `hash = SHA-256(JSON canónico de [partido_id, version_modelo, version_datos, corte, sellado_en, entradas, distribucion, referencia_mercado, hash_previo])`, génesis `0×64`, serializada con `pg_advisory_xact_lock(hashtext('tenis.pronostico'))`, `sellado_en = clock_timestamp()` de la base, y la condición `clock_timestamp() < T_ref` en la misma sentencia de inserción (patrón de `nba/v2/sellado.py`). `verificar_cadena` recalcula todo y falla en la primera ruptura.
- Probabilidades redondeadas a 6 decimales **antes** de serializar: el hash es idéntico en Windows y en Linux (compuerta de reproducibilidad).
- El contrato `DistribucionPartido` se valida antes de sellar; el `PronosticoSellado` se valida antes de servir (502 si no cumple).
- Un partido se sella **todo o nada** (todos sus mercados en una transacción; lección NBA de los props).

### H.4 Respaldo, restauración y vuelta atrás

- `pg_dump` de `tenis-db` y del árbol de originales **cada 6 h, conservando 24** (≈ 6 días), y **copia diaria al PC** por tarea programada (mismo esquema que NBA desde el 3-nov: `DEPLOYS.md`).
- **Restauración ensayada** en S1 y repetida antes de activar el motor (S6): restaurar en una base temporal, `verificar_cadena`, recuentos por tabla iguales, una lectura PIT idéntica a la de producción.
- **Vuelta atrás de la imagen**: un solo fichero `imagen_actual` con el **nombre completo** `tenis-motor:<tag>` (nunca solo la etiqueta: el 3-nov eso rompió los crons de NBA 1 h 20 min, progreso 3-nov) y `imagen_actual.anterior`. Tras cambiarlo, **ejecutar a mano un colector y una pasada del motor en modo ensayo** y comprobar salida 0. La activación de un artefacto se revierte con otra fila en `artefacto_activo` que apunta al anterior.
- **Antes de activar una imagen**: `git log --oneline <commit_de_main_desplegado>..<commit_de_la_imagen>` y el inverso, para ver qué commits ajenos lleva y cuáles le faltan; si lleva commits que no están en `main`, no se activa (producción = `main`, `DEPLOYS.md`).
- **Alertas por Telegram** (canal operativo `TG_ALERT_CHAT`, decisión del 2-oct): colector parado o con 401/403/429, cupo agotado, `sin_resolver` > 2 %, jugador sin historia, contrato incumplido, cadena rota, sello tardío, respaldo fallido. Una alerta por tipo, partido y día; el estado de deduplicación se siembra al activar para no mandar una avalancha (lección NBA).

## I. Compuertas (definidas antes de medir)

### I.0 Reglas comunes

- **Protocolo de medida** = el de la línea base (aud. §6.2): walk-forward por temporadas (§J), presentación A/B con semilla fija, IC95 por **bootstrap por partido** (2.000 réplicas), orígenes combinados por **inversa de la varianza**. Las líneas de un mismo partido están correlacionadas: el bootstrap remuestrea partidos, no líneas.
- Referencia de mercado del ganador: probabilidad sin margen **proporcional** (lección NBA: Shin y potencia solo ganan diezmilésimas, progreso 2-nov; el método queda escrito en el informe). PS de Tennis-Data hasta ene-2026; desde feb-2026, media de casas (Avg) y Bet365, marcadas clase (b).
- Toda compuerta se evalúa por **circuito** (ATP y WTA por separado). Una compuerta no pasada en un circuito bloquea solo ese circuito.
- Cifras de calibración y puntuación: nunca por una sola temporada (error típico de la pendiente ≈ 0,05 con ~2.500 partidos y ≈ 0,1 con ~1.300; IC de 2025 ATP del Elo recalibrado [0,83; 1,03]: CSV `linea_base_metricas_por_origen`).

### I.1 Tabla de compuertas

| Compuerta | Métrica | Umbral | Muestra mínima | Si falla |
|---|---|---|---|---|
| **G-coherencia** | Violaciones de G.6 (física y propiedades) en pruebas `hypothesis` (≥ 10.000 casos por formato) y en todos los partidos evaluados | **0 violaciones**; método delta frente a cuadratura < 0,2 pp; Q = 9 frente a Q = 21 < 1e-4 | 10.000 casos aleatorios + todo el walk-forward | No se avanza; causa raíz y prueba de regresión |
| **G-reproducibilidad** | Hash de la distribución sellada y del informe de evaluación | Idéntico en dos ejecuciones y entre Windows y Linux (redondeo a 6 decimales antes de serializar) | 300 partidos | No se avanza |
| **G-calibración (ganador)** | Pendiente e intercepto de la regresión logística del resultado sobre logit(p̂), conjunta de todos los orígenes | IC95 de la pendiente contiene 1 **y** \|b − 1\| ≤ 0,10; IC95 del intercepto contiene 0 | ≥ 10.000 partidos por circuito (2019-2026 da ~16.700 ATP y ~15.400 WTA) | No se publica el ganador de ese circuito; se revisa el modelo (no se «arregla» con una capa sin pasar su compuerta) |
| **G-recalibración** | Δ log-loss (Platt con temporadas previas − sin capa) | Se activa la capa solo si IC95 < 0 | Igual que arriba | Capa apagada (resultado esperado: la línea base ganó 0,001–0,002, aud. §6.2) |
| **G-línea base (ganador)** | Δ log-loss y Δ Brier (nuevo − Elo recalibrado de la línea base), mismos partidos | Límite superior del IC95 ≤ +0,002 (no peor); objetivo: estimación < 0 | Igual que arriba | No se publica; si es peor que Elo, el motor nuevo no aporta nada en el ganador y se dice |
| **G-cierre (ganador, retrospectivo, clase b)** | Δ log-loss (nuevo − cierre sin margen) | Se **informa siempre**; compuerta: Δ ≤ Δ(Elo recalibrado − cierre) + 0,002 (hoy +0,038 ATP y +0,036 WTA: aud. §6.2) | Igual | Se publica la brecha tal cual; si es mayor que la de Elo, no se publica el ganador |
| **G-resultados (otros mercados)** | RPS (totales, sets, resultado exacto), log-loss (hándicaps en líneas fijas, tiebreak, 1.er set) frente a: (a) frecuencias por circuito × superficie × formato; (b) estructura sin pieza P ni efecto del partido (suma media constante, IID) | Mejor que (a) con IC95 que excluye 0; no peor que (b) en más de 0,002 | ≥ 2.000 partidos por circuito y mercado (completados) | Ese mercado no se publica en la beta |
| **G-calibración (otros mercados)** | Pendiente conjunta por mercado binarizado (línea principal: la más cercana al 50 %); PIT aleatorizado del total de juegos | IC95 de la pendiente contiene 1 y \|b − 1\| ≤ 0,15; PIT: ninguna decila fuera de [0,08; 0,12] | ≥ 2.000 por circuito | No se publica |
| **G-cobertura** | Cobertura empírica de los intervalos centrales del 50 % y 80 % del total de juegos y del hándicap de juegos | Dentro de ±3 pp del nominal (≈ 3,4 errores típicos con n = 2.000) | ≥ 2.000 por circuito | No se publican intervalos; revisar Σ_ε/σ_set |
| **G-superficie** | Ablación: modelo completo frente al mismo con κ ≡ 1, d ≡ 0, a ≡ b ≡ 0, μ común | Se **informa** Δ log-loss (ganador) y Δ RPS (totales), global y por superficie | Todo el walk-forward; hierba ≥ 1.000 | Nunca se quitan los términos; si empeoran con IC95 > +0,001, se fija una escala a priori menor, se reajusta y se informa |
| **G-fatiga** | Ablación φ ≡ 0; segmento F > F₉₀ | Igual que G-superficie, en el segmento | ≥ 1.000 partidos en el segmento por circuito | Igual; además se publica que el efecto no está validado |
| **G-contextos** | Posterior de γ_preGS, γ_equipos | Se informa IC; ningún umbral de publicación | Lo que haya (no medido) | — |
| **G-presión** | §E.4 | Regla preregistrada | 2.000 por circuito | P0 se queda |
| **G-micro (S7)** | Aces, dobles faltas, break en el 1.er set: calibración y RPS frente a frecuencias por jugador | Las de G-calibración y G-resultados | ≥ 2.000 por circuito | **No publicables** (por defecto no lo son) |
| **G-fuga** | I.2 | **0 diferencias** fuera de tolerancia | 300 partidos | No se avanza |
| **G-cordura** | Brier del ganador en cualquier evaluación con n ≥ 500 | Brier ATP o WTA **< 0,18 ⇒ sospecha de fuga** (el cierre de Pinnacle mide 0,197–0,209 por temporada en ATP: CSV `linea_base_metricas_por_origen`) | 500 | Se para todo hasta encontrar la causa |
| **G-identidad** | Tasa de `sin_resolver` en ATP/WTA principal; tasa de cruce con Tennis-Data por circuito y año | ≤ 2 % sin resolver; cruce ≥ 90 % (el motor actual cruzaba 86,8–95,1 %: aud. §6.3) y Δ de log-loss del Elo entre cruzados y no cruzados con IC que incluye 0 | Cada semana / cada año | Se informa; si el cruce es selectivo, la comparación con el cierre se marca como sesgada |
| **G-tiempo** | Sellos con `sellado_en ≥ T_ref` o `corte > sellado_en` | **0** | Todos | Se detiene el motor y se alerta |
| **G-operación** | Restauración, vuelta atrás, alertas, candados | Restauración ensayada con cadena verificada y recuentos iguales; cambio de `imagen_actual` y vuelta atrás con un colector ejecutado a mano y salida 0; alerta de prueba recibida una sola vez; dos ejecuciones simultáneas de un colector → una sale sin hacer nada; respaldo de ≤ 6 h presente | Un ensayo completo antes de S6 y otro antes de activar | No se activa |
| **G-mercado (prospectivo, PropLine)** | Δ log-loss frente al cierre sin margen de PropLine por mercado (una línea por partido: la principal) | Se informa mensualmente; ninguna afirmación pública con n < 300 partidos por mercado | 300 | Se publica la brecha tal cual, sea cual sea |

### I.2 G-fuga en detalle

Sobre la **base real en solo lectura** (rol `tenis_lectura`, transacción `READ ONLY`), 300 partidos pasados estratificados por circuito, superficie, formato y ronda, con su corte `T_ref − 60 min`:

1. **Sin fuga en las entradas**: ninguna fila usada con `recibido_en > corte`; ningún dato retro de la semana del partido o posterior; ninguna estadística ni duración del propio partido; ranking con `fecha_publicacion ≤ fecha local`; ningún campo prohibido (§A.4). Tolerancia: 0.
2. **Implementación de referencia independiente del rating**: consulta SQL distinta (sin las funciones `*_a_las` ni `DISTINCT ON`) y una reproducción del filtro escrita aparte (bucle simple, sin el código vectorizado del motor), jugando los partidos por semana, edición y ronda, con la predicción de cada partido **antes** de actualizar con él. Tolerancias: |Δθ| ≤ 1e-9; |Δπ| ≤ 1e-9.
3. **Simulador de referencia**: (a) una segunda programación dinámica escrita de otro modo (recursión sobre los puntos del set completo, sin la fórmula cerrada del juego): tolerancia 1e-9 en cada probabilidad de la conjunta; (b) simulación punto a punto por fuerza bruta con N = 10⁶ en 50 de los partidos: |Δ| ≤ max(4·EE, 0,002) por mercado.
4. **Repetibilidad**: dos ejecuciones dan el mismo hash.
5. La muestra cambia cuando cambia el número de partidos: el Brier de G-fuga **no** es una métrica del modelo (lección NBA), solo la alarma de G-cordura.

Lección NBA que justifica el punto 2: la referencia independiente encontró un error real (arrastre de temporada omitido) y una ventana de historia distinta a la validada que la reproducibilidad sola no veía (progreso 2-nov y 3-nov).

### I.3 Liquidación: qué entra en el Brier/log-loss

Regla de la casa de referencia (premisa 2), aplicada con **resultados propios** (nunca con la calificación de PropLine, que califica mal el ganador por juegos totales en ~1 de cada 10 partidos a 3 sets):

| Desenlace | Ganador | 1.er set | Hándicaps, totales, sets exactos, tiebreak |
|---|---|---|---|
| Completado | Liquida | Liquida | Liquida (línea entera con empate = push, fuera) |
| Walkover | Nulo (fuera) | Nulo | Nulo |
| Retirada con ≥ 1 set completo | Liquida (gana quien avanza) | Liquida si el 1.er set terminó | **Nulo** |
| Retirada antes de completar un set | Nulo | Nulo | Nulo |
| Cancelado / descalificado | Nulo | Nulo | Nulo |

Los nulos y pushes se cuentan y se publican con cada evaluación; nunca se puntúan. El modelo predice **condicionado a que el partido se liquide** (supuesto S-3 de §M.2); la calidad en las retiradas que liquidan se mide aparte (en la línea base, ATP +0,042 y WTA −0,022 [−0,050; 0,005]: aud. §6.2).

## J. Walk-forward con origen móvil

- **Nunca validación cruzada aleatoria** (las cifras altas de la literatura vienen de particiones aleatorias o fugas: lit. C.v.4).
- **Orígenes**: 1 de enero de 2019, 2020, …, 2026 (los mismos de la línea base, para comparar sobre los **mismos partidos**: intersección por identidad, con la cobertura publicada). En cada origen: Ψ se ajusta con las temporadas anteriores; dentro del año de prueba el filtro se actualiza partido a partido (inferencia, como en producción) con Ψ congelado.
- **Ventana de ajuste de Ψ** (propuesta preregistrada): las 8 temporadas anteriores al origen; el filtro arranca desde el primer año disponible (calentamiento) para que los estados tengan historia. Sensibilidad informativa con 5 y 12 temporadas (no se elige sobre la prueba). Motivo: el saque y el juego cambian por épocas (deriva: T26 [J], A25, B04).
- **Embargo**: 7 días entre el último dato del ajuste de Ψ y el origen. TML fecha por semana sin hora (aud. §3): una semana de torneo nunca queda partida entre ajuste y prueba. Dentro de la prueba, el orden semana → edición → ronda evita usar un resultado de una ronda posterior (riesgo de T13: lit. D, fuga 1).
- **Reserva final**: las decisiones de diseño (rejillas, ventana, variantes de E y F) se toman con los orígenes 2019-2024; 2025 y 2026 se abren **una vez** al final de S4 para la decisión de promoción. (La línea base ya miró 2025; para el modelo nuevo se trata como reserva igualmente.)
- **2026**: Pinnacle no existe en Tennis-Data desde feb-2026 (aud. §1, punto 3); la referencia de 2026 es la **media de casas** (y Bet365 como contraste), marcada clase (b), en una fila aparte y combinada con las demás por inversa de la varianza solo si el informe lo dice explícitamente (la media de casas mide +0,0007 ATP y +0,0008 WTA frente a Pinnacle en 2019-2026: CSV `linea_base_dif_vs_cierre_combinada`, fila `m_avg`).
- **Orígenes para punto a punto** (presión, break en el 1.er set): SofaScore empieza en 2023, así que los orígenes útiles son 2024, 2025 y 2026.
- **Prospectivo**: desde la activación, cada sello es una predicción fuera de muestra real; la evaluación prospectiva con PropLine (§I.1, G-mercado) se acumula sin tocar el modelo (nada se reentrena ni promueve por capturar datos: decisión del 23-oct).

## K. Riesgos, orden de sprints y criterios de «terminado»

### K.1 Riesgos y mitigación

| Tipo | Riesgo | Mitigación |
|---|---|---|
| Datos | El calendario/resultados en vivo dependía de API-Tennis, que venció el 1-nov; SportsAPIPro tiene 100 peticiones/día compartidas | Interfaz de proveedor única con prioridad explícita; reutilizar los recibos del colector actual; decisión D3; alerta si un día no hay resultados |
| Datos | Minutos faltantes (53 % en TML: 260.099 de 492.251) y sin hora en TML | Minutos estimados marcados; tiempo entre partidos por rondas, validado con SofaScore 2023-26 (§C.5); fatiga desconocida ⇒ no se sella |
| Datos | SofaScore local en descarga (cifras cambiarán; el «54 %» aún no medido) | Volver a medir al terminar, antes de entrenar (S2, criterio de salida) |
| Datos | Superficie/indoor/formato por edición incompletos | Formato o indoor desconocido ⇒ no se sella; en entrenamiento, nivel propio encogido |
| Fuga | TML como ganador/perdedor, estadísticas del propio partido, ranking «de hoy», `firstToServe`, `h2h` posteriores | Orden canónico de jugadores; cargadores que no copian campos prohibidos; lectura solo por funciones PIT; G-fuga con referencia independiente |
| Fuga | Tennis-Data quizá de apertura y no de cierre (lit. §0.2) | Clase (b) declarada; la brecha cambia de tamaño, no de sentido; prospectivo con PropLine (con instante) |
| Fuga | El mercado como entrada (lo que hace el motor actual) | Prohibido en el diseño: la referencia se guarda en el sello pero no entra en el cálculo |
| Modelo | La inversión C reproduce un ganador mal calibrado en todos los mercados | El ganador pasa su compuerta antes; los demás mercados tienen la suya propia |
| Modelo | Superficie y fatiga sin señal (o con señal en un circuito y no en otro) | Escalas estimadas y encogimiento; ablación publicada; parámetros por circuito |
| Modelo | Sesgo del IID en totales y hándicaps | Efecto del partido y por set; margen declarado; prueba preregistrada (§E) |
| Modelo | Jugadores con poca historia (20 % de la muestra, el peor segmento) | Prior explícito por ranking marcado; compuerta por segmento; no publicar si falla |
| Proveedor | PropLine: archivo en un volumen sin permiso de lectura para `qf` (aud., inv. cuotas §3.2); mezcla ITF/UTR; calificación defectuosa | Lectura dentro del contenedor del motor con el volumen montado en solo lectura (como el worker); enlace solo ATP/WTA; resultados propios |
| Proveedor | Cuotas de pago o créditos nuevos | Presupuesto 0 por defecto; libro diario en UTC con tope y prioridad; Apify/SportsAPIPro nuevos usos solo con tu OK |
| Operación | Imagen con commits ajenos o `imagen_actual` mal escrito | `git log` en los dos sentidos antes de activar; nombre completo; colector a mano tras el cambio |
| Operación | Sello erróneo para siempre (solo-anexar) | Simulacro antes de activar el cron; el cron no se activa solo (lección NBA, progreso 3-nov) |
| Operación | Memoria del VPS con un tercer Postgres | Medir antes (no medido); decisión D1 |
| Honestidad | Que el producto sugiera ventaja | Sin Kelly/stakes/ROI/«ventaja»; aviso beta con la brecha medida frente al cierre; publicar también lo que no pasa |
| Honestidad | Licencias (MCP CC BY-NC-SA; series de ranking públicas) | Solo uso sin lucro con atribución; MCP solo local para diagnóstico |
| Proceso | Conflictos en DEPLOYS.md, progreso.md, tareas.md al fusionar | Conservar ambas partes; nunca resolver borrando la otra sesión |
| Proceso | Confundir falla de entorno con falla de código (en la Fase 1 Python no podía escribir en el worktree) | Diagnóstico de entorno antes de tocar código; anotar en el informe |

### K.2 Sprints

Ajuste respecto a la propuesta del encargo: el rating R usa como enlace la probabilidad exacta de ganar el partido (§D.3), así que el **núcleo analítico** del simulador (juego → tiebreak → set → partido → mezcla) entra al principio de S3; S4 completa la conjunta, los mercados, la inversión y la evaluación. Código nuevo en un paquete propio `apps/tenis/` (el motor actual `apps/tennis/` no se toca ni se hereda). Guía: módulos de ~50 líneas, una responsabilidad cada uno. Todas las pruebas con Postgres local en esquema aislado (memoria «Entorno local de pruebas») y en CI.

**Regla de pruebas de todos los sprints**: (1) datos **absurdos** que deben rechazarse o comportarse en el límite; (2) comparación con un cálculo **independiente** sobre **datos reales** (otro código, otro camino), porque los errores reales de NBA solo aparecieron así.

#### S0 — Cierre de la Fase 1 (administrativo)

- Objetivo: dejar la Fase 1 y este plan en git. Entregables: `./scripts/test_local_windows.ps1 -Suite all` en verde (o diagnóstico de entorno si falla), commit en `tenis/rediseno-f1`, PR solo de documentos y scripts de medición.
- Decide el titular: las decisiones de §M (al menos D1-D5) y el «Sí» al plan. Subagente: ninguno.

#### S1 — Base de datos y contratos

- Objetivo: el esquema `tenis` con inmutabilidad, lectura PIT, roles, sellado y contratos, sin datos de producción.
- Archivos: `apps/tenis/db/0001_catalogos.sql` (fuente, jugador, alias, torneo, edición, sede), `0002_evidencia.sql` (recibo, partido, programa, resultado, estadística, juego_pbp, ranking, precio_mercado, enlace_evento, sin_resolver), `0003_inmutabilidad.sql`, `0004_lectura_pit.sql` (funciones `*_a_las`), `0005_roles.sql`, `0006_sellado.sql` (pronóstico, artefacto, artefacto_activo), `0007_semillas.sql` (fuentes, formatos); `apps/tenis/src/tenis/contratos/{base,entrada,salida,validar}.py`; `apps/tenis/src/tenis/recibo.py` (objeto por contenido + recibo); `apps/tenis/ops/tenis-db/{compose.yml,respaldar.sh,restaurar_ensayo.sh}`.
- Pruebas: `DELETE … WHERE false`, `UPDATE`, `TRUNCATE … CASCADE` fallan en todas las tablas de evidencia, también como dueño; una fila con `recibido_en` posterior al corte es invisible; un dato retro no es visible en la semana de su partido; contratos con p = 0, p = 1, NaN, ±inf, instante sin zona, campo de más, jugador_1 = jugador_2, mejor_de = 4, set 8-6 con tiebreak, duración 0 → rechazo; objeto escrito dos veces = un objeto y dos recepciones; proceso matado a mitad de escritura no deja objeto truncado. Independiente: cargar 1.000 filas reales de TML en un esquema de prueba y comparar recuentos y sumas con un cálculo `pandas` aparte.
- Compuerta de salida: todo verde local y en CI; ensayo de restauración con recuentos iguales.
- Depende de: S0, D1. Subagente: **haiku** (SQL e I/O repetitivo), revisión mía.

#### S2 — Ingesta e identidad (histórico + captura diaria)

- Objetivo: toda la historia cargada como evidencia retro, identidad resuelta y colectores diarios idempotentes listos (ejecutados en local; en el VPS solo con tu OK).
- Archivos: `src/tenis/captura/{tml,sofascore,tennis_data,mcp,calendario,ranking}.py` (uno por fuente; `calendario.py` con la interfaz de proveedor de D3); `src/tenis/carga/{ediciones,partidos,resultados,estadisticas,pbp,ranking_tml}.py`; `src/tenis/identidad/{normalizar,resolver,cola}.py`; `ops/colector.sh` (`flock -n` por fuente); `ops/medir_identidad.py`; equivalencias manuales en `apps/tenis/config/equivalencias.csv`.
- Pruebas absurdas: partido «completado» de 1 juego → rechazado; retirada en el 2.º set (6-3 2-1 ret.) → `retirada`, `sets_completos = 1`; walkover con marcador → rechazo; duración 0, negativa o > 7 h → NULL con marca; `primeros_ganados > primeros_dentro` → rechazo; nombre con «/» → excluido; la misma fila de TML revisada → nueva aserción y la lectura PIT elige según el corte; ranking publicado el lunes no es visible para un partido del domingo anterior. Independiente sobre datos reales: reconstruir con la base cargada los recuentos de la auditoría (492.251 partidos, 469.527 completados, 449.335 / 42.916 por formato, superficies; SofaScore 21.974 actualizado al terminar la descarga) por otro camino (los scripts de inventario de la Fase 1); medir de nuevo la exclusión WTA 2026 (el «54 %»); comparar el cruce TML–SofaScore por id con el aproximado por apellido (~60 %).
- Compuerta de salida: G-identidad (≤ 2 % sin resolver en ATP/WTA principal); recuentos conciliados o diferencias explicadas; cada cargador ejecutado dos veces deja las mismas filas; prueba de `flock`; significado de los niveles `D`, `O` de TML verificado; ranking TML frente al oficial capturado comparado en las semanas de solape (si D2 lo permite).
- Depende de: S1; D2, D3, D4, D5. Decide el titular: copiar el snapshot del VPS (D5), fuente de ranking (D2), proveedor de resultados (D3), Apify (D4); y, si quiere que la serie PIT empiece pronto, desplegar ya el colector de ranking (2 peticiones/semana). Subagente: **haiku**.

#### S3 — Núcleo analítico, pieza P (suma) y pieza R (rating)

- Objetivo: probabilidades de punto por jugador con incertidumbre, superficie y fatiga estructurales, y ganador calibrado al menos igual que Elo.
- Archivos: `src/tenis/simulador/{juego,tiebreak,set_,partido,mezcla}.py`; `src/tenis/modelo/{fatiga,superficie,puntos,rating,prior_ranking,recalibracion,hiperparametros}.py`; `src/tenis/datos/exportar_pit.py`; `ops/{entrenar,evaluar_wf}.py`; `ops/referencia_rating.py` (independiente, escrito por otro subagente solo con la especificación de §D).
- Pruebas absurdas: p = 0 y p = 1 rechazados; saque del 95 % en ambos → sin NaN, P(tiebreak) alta y total cerca del máximo; diferencia de θ enorme → π ∈ (0, 1) sin desbordar; F = 0 → fatiga sin efecto; φ negativo imposible; jugador sin historia ni ranking → omitido con alerta; 3 años de inactividad → varianza mayor; walkover → sin actualización. Independiente sobre datos reales: reproducir con el nuevo flujo de datos el Elo de la línea base (+0,039 ATP / +0,036 WTA frente al cierre) en los mismos partidos; si no sale, se para (es una diferencia del camino de datos); reproducción del filtro por `referencia_rating.py`; cifras de T32/A31/A26.
- Compuerta de salida (orígenes 2019-2024): G-línea base (ganador), G-calibración (ganador), G-recalibración, G-cordura; informes de G-superficie y G-fatiga.
- Depende de: S2. Subagente: **opus** (lógica cuantitativa).

#### S4 — Conjunta, mercados derivados, inversión y evaluación completa

- Objetivo: una sola distribución por partido, todos los mercados coherentes, evaluación contra resultados y decisión de promoción con la reserva 2025-26.
- Archivos: `src/tenis/simulador/{conjunta,mercados,sensibilidad,montecarlo}.py`; `src/tenis/modelo/union.py` (inversión de §D.4); `ops/{referencia_dp,referencia_mc_puntos,evaluar_mercados,prueba_presion}.py`.
- Pruebas: propiedades G.6 con `hypothesis`; absurdas: mejor de 5 con tiebreak a 10, set decisivo de ventaja con p = 0,98 en ambos (cola truncada y declarada), retirada en el 2.º set (liquida 1.er set y ganador, anula totales). Independiente: segunda programación dinámica y fuerza bruta punto a punto (§I.2.3) sobre partidos reales.
- Compuerta de salida: G-coherencia, G-resultados, G-calibración (otros mercados), G-cobertura, G-presión (paso 0 y regla de E.4); después, apertura única de 2025-26 y decisión de qué mercados son candidatos a la beta.
- Depende de: S3. Subagente: **opus**.

#### S5 — Cuotas y referencia de mercado (PropLine, Tennis-Data)

- Objetivo: precios de referencia cargados con su recepción real, enlazados y sin entrar en el modelo; evaluación retrospectiva (ganador, clase b) y prospectiva (todos los mercados).
- Archivos: `src/tenis/mercado/{propline,enlace,devig,liquidacion,tennis_data_hist}.py` (`propline.py` solo envuelve `propline_shared.newest/read_two_way/read_closing`, sin red); `ops/{cargar_precios,evaluar_prospectivo}.py`.
- Pruebas absurdas: cuota ≤ 1 o americana con |x| < 100 → rechazo; mercado de un solo lado → sin probabilidad sin margen; cotización en juego, suspendida, DFS o de bolsa → excluida; pareja repetida en la misma observación → sin mercado (decisión del 24-oct); la liquidación solo lee `tenis.resultado` (prueba que falla si alguien lee la calificación de PropLine). Independiente: reproducir el margen mediano de Pinnacle 2,46 % en Tennis-Data y 4,74 % (n = 76) en el piloto de PropLine (inv. cuotas §4) desde la base cargada.
- Compuerta de salida: G-identidad (cruce con Tennis-Data ≥ 90 % y sin sesgo), G-cierre (retrospectivo) calculada e informada; evaluación prospectiva corriendo en local con el archivo.
- Depende de: S2 (puede ir en paralelo con S3-S4); acceso de lectura al volumen de PropLine (D9). Subagente: **haiku**.

#### S6 — Sellado, motor programado, API y web beta

- Objetivo: sellar en producción con corte fijo, servir una ruta pública beta y operar con respaldo, vuelta atrás y alertas.
- Archivos: `src/tenis/{sellado,motor,alertas,salud}.py`; ruta en el FastAPI único `src/qf/api/tenis_v2.py` (`/tenis/v2/cartelera`, `/tenis/v2/partido/{id}`, `/tenis/v2/metodologia`; solo códigos de error, la web traduce); página web beta; textos nuevos en **es, en, pt, fr, it, de** (y en la app, con `l10n_add.py`, si se toca); `ops/{Dockerfile.tenis-motor,imagen_actual,g_fuga.py,ensayo_operativo.sh,ensayo_vuelta_atras.sh}`; líneas de cron con `flock`.
- Pruebas absurdas: sello con `ahora ≥ T_ref` → rechazado; corte futuro → rechazado; partido que empieza durante el sellado → no se inserta; fila alterada → `verificar_cadena` falla; contrato roto → 502; paridad de claves de traducción (`tests/test_mensajes.py`, `test/l10n_test.dart`). Independiente: G-fuga completa sobre la copia real.
- Compuerta de salida: G-fuga, G-tiempo, G-reproducibilidad, G-operación; **simulacro de 7 días** sellando en una base de ensayo; luego tu OK para activar el cron. Despliegue por rama + PR + CI en verde + fusión a `main`; producción = `main`; entrada en `DEPLOYS.md` con vuelta atrás.
- Depende de: S4 (mercados que pasaron), S5 (referencia), D6-D8. Subagente: **haiku** para I/O, API y web; la referencia de G-fuga la escribe **otro** subagente (opus) sin ver el código del motor, para que sea independiente de verdad.

#### S7 — Micro-eventos (solo si los datos lo permiten)

- Objetivo: aces, dobles faltas y break en el 1.er set **evaluados, no publicados**.
- Archivos: `src/tenis/micro/{aces,dobles_faltas,break_set1}.py`; `ops/evaluar_micro.py`.
- Datos: recuentos de TML (~250 mil partidos ATP/WTA principales) y punto a punto de SofaScore 2023-26 (break). El corpus no tiene un modelo de recuento validado (lit. D).
- Pruebas absurdas: 0 puntos de saque → 0 aces; tasa de aces 0 o 1 → rechazo; partido retirado → nulo. Independiente: frecuencias por jugador calculadas por otro camino.
- Compuerta: G-micro; aunque pase, publicar exige tu decisión. Subagente: **opus**.

### K.3 Criterio de «terminado» de todo el rediseño (beta)

1. G-fuga, G-tiempo, G-coherencia, G-reproducibilidad y G-operación en verde.
2. Ganador por circuito con G-línea base y G-calibración en verde (si no, ese circuito no se publica).
3. Cada mercado publicado con G-resultados, G-calibración y G-cobertura en verde.
4. Aviso beta visible con la brecha medida frente al cierre (retrospectiva y, cuando haya n ≥ 300, prospectiva).
5. `harness/tareas.md` marcado y la decisión clave en `harness/progreso.md`.

## L. Lecciones de NBA aplicadas desde el día 1

| Lección (fuente) | Dónde se aplica en este plan |
|---|---|
| La ventaja esperada suele no aparecer: el núcleo de equipo quedó calibrado pero sin información sobre el cierre (progreso 2-nov, Sprint 3) | Producto honesto: sin ventaja, Kelly ni ROI; brecha frente al cierre publicada (§I, G-cierre y G-mercado; §K.3) |
| Los errores reales se encuentran con una referencia **independiente** sobre datos reales: arrastre de temporada omitido; ventana de historia distinta de la validada (progreso 2-nov y 3-nov) | G-fuga con referencia escrita por otro subagente sin ver el motor (§I.2, S6); cada sprint compara con un cálculo independiente sobre datos reales (§K.2) |
| Faltante ≠ 0; duraciones imposibles se rechazan | Minutos NULL nunca 0; duración 0/negativa/> 7 h rechazada; fatiga desconocida ⇒ no se sella (§C.5, S2) |
| Coherencia entre mercados por construcción y con propiedades aleatorias (progreso 2-nov) | Una sola conjunta; `hypothesis` sobre la física del marcador (§G.6) |
| Contratos Pydantic antes de sellar y antes de servir; 502 si no cumplen; las pruebas con datos absurdos encontraron un hueco real (progreso 3-nov, F4.0) | §A.5; pruebas absurdas en cada sprint |
| Presupuesto de pago con tope diario y orden de prioridad; día de créditos en UTC | §C.2.4; presupuesto 0 salvo tu OK (D10) |
| Un proceso por fuente (`flock`), colectores idempotentes | §C.1-C.2 |
| 403/404 de ficheros aún no publicados son normales | §C.2.3 (umbral de 36 h antes de alertar) |
| Corte = salto − 60 min fijo; un cron atrasado usa los mismos datos; nunca sellar tras el inicio (progreso 3-nov) | §C.6 (con `T_ref` = inicio más temprano posible, por los partidos «a continuación») |
| El cron no se activa solo: un sello es para siempre | Simulacro de 7 días y tu OK (S6) |
| `imagen_actual` con nombre completo; probar un colector a mano tras cambiarla (incidente 3-nov) | §H.4 |
| Revisar con `git log` qué commits lleva una imagen antes de activarla; producción = `main` | §H.4 |
| Despliegue por rama + PR + CI en verde + fusión a `main`, registrado en `DEPLOYS.md` con vuelta atrás | S6 |
| `DEPLOYS.md`, `progreso.md`, `tareas.md` darán conflictos al fusionar: conservar ambas partes | §K.1 |
| Distinguir falla de entorno de falla de código | §K.1; S0 |
| Respaldo cada 6 h (24 copias) y copia diaria al PC (3-nov) | §H.4 |
| El servidor no entrena; parámetros como artefacto JSON con huella normalizada por finales de línea (3-nov) | §H.1-H.2 |
| El método de quitar margen va escrito en la versión, no en la cuota; proporcional (2-nov) | §I.0 |
| La muestra de G-fuga no es una métrica del modelo (error típico ≈ 0,02 con 100 partidos) | §I.2.5 |
| Sellos de un partido todo o nada (props, 3-nov) | §H.3 |
| Alertas una vez por tipo, partido y día; sembrar el estado al activar | §H.4 |

## M. Decisiones y supuestos

### M.1 Decisiones que necesito del titular

Solo las que cambian el diseño o requieren aprobación. Mi recomendación va primero.

| # | Decisión | Recomendación | Alternativa |
|---|---|---|---|
| D1 | Dónde vive la evidencia de tenis | **Contenedor Postgres propio `tenis-db`** en el VPS (como `nba-db`), tras medir que la memoria alcanza | Esquema `tenis` dentro de la base `quantfut` de fútbol |
| D2 | Fuente del ranking semanal | **Captura oficial cada lunes** desde SportsAPIPro (2 peticiones/semana del cupo compartido) + **historia reconstruida de TML** (sin coste); la serie pública de Sackmann solo si se confirma licencia y cobertura | Solo el ranking por partido de TML, con su fecha sin verificar |
| D3 | Calendario y resultados en vivo tras el vencimiento de API-Tennis (1-nov) | **Reutilizar los recibos del colector actual** (`--source auto`, SportsAPIPro) sin peticiones nuevas; SofaScore como segunda fuente de resultados y duraciones | Renovar API-Tennis (pago) |
| D4 | Tenis del recolector Apify (de pago, tope 15 USD/mes) para duraciones y punto a punto recientes | **Primero medir** (solo lectura) qué tenis hay en `~/sofascore-apify/data`; ningún gasto nuevo hasta ver el resultado | Usarlo ya |
| D5 | Copias de datos | **Sí** a copiar el snapshot TML del VPS (2-nov) al PC en solo lectura para entrenar en local; **sí** a subir los originales de tenis de SofaScore al árbol del VPS cuando termine la descarga (script idempotente de 6 conexiones) | Entrenar con el TML local del 16-oct |
| D6 | Alcance de circuitos | **Publicar solo ATP/WTA principal**; Challenger y previas (TML) solo alimentan los ratings; ITF/UTR fuera | Incluir Challenger en la publicación (sin resultados en vivo ni cuotas fiables) |
| D7 | Mercados candidatos de la beta | **Ganador, 1.er set, sets (hándicap, total, exacto), juegos (hándicap, total) y tiebreak**, cada uno solo si pasa sus compuertas; aces, dobles faltas y break en el 1.er set **evaluados, no publicados** | Lista más corta (solo ganador y totales) |
| D8 | Motor actual | **No tocarlo ni retirarlo** durante el rediseño; sus 350 sellos no se reescriben; retirarlo solo cuando la beta nueva esté activa y con tu OK | Apagarlo antes |
| D9 | Lectura del archivo de PropLine (volumen sin permiso para `qf`) | **Montarlo en solo lectura** en el contenedor del motor de tenis, como el worker | Copia periódica a otra carpeta |
| D10 | Presupuesto de pago | **Mantener 0**; ningún crédito nuevo (Apify, SportsAPIPro por encima del uso actual, API-Tennis) sin tu OK explícito | — |
| D11 | Semana previa a GS y competiciones por equipos/JJOO | **Medirlos** como contextos encogidos a 0, dentro del entrenamiento; partidos muertos fuera; equipos y JJOO **no publicados** | Excluirlos del todo |
| D12 | Ruta pública | **`/tenis/v2` nueva, beta, sin cuentas ni cobro**, en paralelo a la página actual; cambiar la página pública de tenis solo tras el simulacro y con tu OK | Sustituir la página actual directamente |

### M.2 Supuestos que asumo para no bloquear el plan

- **S-1** Las columnas PS/B365 de Tennis-Data se tratan como cierre declarado sin hora (clase b); si fueran de apertura, la brecha cambia de tamaño, no de sentido (lit. §0.2).
- **S-2** El ranking de TML por partido es el de la semana del torneo; se verifica en S2 (§C.4).
- **S-3** El modelo predice condicionado a que el partido se liquide y la retirada es independiente de los rasgos previos; se mide aparte (§I.3).
- **S-4** El primer sacador no se conoce antes del corte: mezcla 50/50.
- **S-5** Formatos por edición cargados desde las fuentes; el tiebreak a 10 en el set decisivo de los Grand Slam desde 2022 (T32 [VF]); lo no verificable queda «desconocido» y no se sella.
- **S-6** Reglas de liquidación de la casa de referencia: las del encargo (walkover nulo; retirada con ≥ 1 set completo liquida el ganador; hándicaps y totales nulos si no termina). Las de A29 son de 2013: se verifican las vigentes de la casa de referencia antes de S5.
- **S-7** ATP y WTA con parámetros separados y código común.
- **S-8** Para ATP, Challenger y previas entran en el conjunto del rating; para WTA, qué niveles inferiores hay en TML depende de códigos aún no verificados (`I`, `T1`-`T5`).
- **S-9** El VPS tiene memoria para un tercer Postgres (no medido; se mide antes de D1).
- **S-10** La descarga de SofaScore terminará; las cifras cambiarán y se vuelven a medir antes de entrenar.
- **S-11** El recolector compartido de PropLine sigue capturando cada hora (no depende de este plan).
- **S-12** La historia retro usa `recibido_en` = fecha de adquisición con la marca `retro` y la regla de visibilidad de §A.4.
- **S-13** El efecto aleatorio del partido parte de A26 (σ ≈ 0,22 en logit para hombres) y se re-estima; no se publica nada con el valor de partida.

## N. Formato de entrega de parches y código (fases siguientes)

- Cada bloque de código en Markdown empieza con una **primera línea que es la ruta exacta** del archivo (p. ej. `apps/tenis/src/tenis/simulador/juego.py`).
- **Protocolo anti-ruptura** para cualquier corrección:
  1. **Causa raíz** escrita antes del parche (qué dato o qué línea, por qué, desde cuándo), distinguiendo falla de entorno y falla de código.
  2. **Parche atómico**: un cambio por causa, mostrado con **3 líneas de contexto antes y después** de cada fragmento modificado.
  3. **Prueba de regresión `pytest`** que falla sin el parche y pasa con él, añadida en el mismo cambio.
  4. Arnés completo (`./scripts/test_local_windows.ps1 -Suite all` o `./scripts/harness_check.sh`) antes de commit; si toca producción, rama + PR + CI + fusión y registro en `DEPLOYS.md` con vuelta atrás.
- Textos visibles nuevos: en los 6 idiomas en el mismo cambio (regla de `CLAUDE.md`).

## Anexo. Comprobaciones hechas en la consola para este plan

Sin crear archivos; Python 3.12 local con `-I`. Programación dinámica de juego → tiebreak → set → partido con alternancia de saque:

| Comprobación | Resultado | Referencia |
|---|---|---|
| g(0,5), g(0,65) | 0,5000; 0,8296 | A26: 0,830 |
| Set con p 0,60 / 0,55, sacando A o B primero | 0,6695 en los dos casos (neutralidad) | T32: 0,669; A31 teorema |
| 6-1 y 6-3 según quien saca primero | 0,0947 / 0,0485 y 0,2042 / 0,1046 | T32 tabla 7 [VT] |
| Partido a 5 sets, 3-0 / 3-1 / 3-2 | 0,7943; 0,3001 / 0,2975 / 0,1967 | T32: 0,795; 0,300 / 0,298 / 0,197 |
| P(6-6) con p 0,60 / 0,55 | 0,1383 | T32: 0,138 |
| p 0,6 frente a 0,5, a 5 y a 3 sets | 0,9513; 0,9078 | A31: 0,9513 / 0,9079 [VF] |
| √1,4 y logit(m5)/logit(m3) con p 0,60/0,55 | 1,1832; 1,2632 | B03: K = 1,183 (promedio, no identidad) |
| Inversión δ* (Ŝ = 1,25, π = 0,70, mejor de 3, σ_ε = 0,22, ρ_ε = −0,45) | δ* = 0,0311; comprobación 0,700000 | §D.4 |
| Ganar a 3 sets con p 0,66/0,60, sin y con forma del día | 0,775 → 0,694; cuadratura Q = 5/7/9/15: 0,693873 / 0,693789 / 0,693792 / 0,693793 | §G.3 |
| N de Monte Carlo para percentil 99 < 0,5 pp | s_h 0,5 → 66.358; 0,1 → 2.655; 0,05 → 664 | §G.5 |











