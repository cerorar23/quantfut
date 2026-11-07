# Base de datos de tenis (Sprint 1, parte A)

Esquemas `tenis` (evidencia, solo-anexar) y `tenis_op` (estado operativo mutable). Plan: `docs/tenis_plan_tecnico_20261105.md` §A, §H.3, §H.4 y K.2 S1.

## Orden de migraciones

| Fichero | Contenido |
|---|---|
| `0001_catalogos.sql` | Esquemas; `fuente`, `jugador`, `jugador_asercion`, `jugador_alias`, `torneo`, `sede`, `edicion`; `tenis_op.cursor`, `tenis_op.presupuesto` |
| `0002_evidencia.sql` | `recibo`; claves foráneas de `recibo` en los catálogos; `partido`, `programa`, `resultado`, `estadistica`, `juego_pbp`, `ranking`, `precio_mercado`, `enlace_evento`, `sin_resolver` |
| `0003_inmutabilidad.sql` | `rechazar_cambio()`, `marcar_inmutable()` y disparadores por sentencia en toda la evidencia |
| `0004_lectura_pit.sql` | Funciones `*_a_las(corte)` y `retro_visible()` |
| `0005_roles.sql` | Roles `tenis_captura`, `tenis_motor`, `tenis_api`, `tenis_lectura`; permisos (solo si los roles existen) |
| `0006_sellado.sql` | `artefacto`, `artefacto_activo`, `pronostico`; `json_canonico()`, `sellar_pronostico()` |
| `0007_semillas.sql` | Catálogo de fuentes (idempotente) |

Se aplican en ese orden. Las migraciones no son idempotentes del todo: `0002` añade claves foráneas con `ALTER TABLE ... ADD CONSTRAINT`, que fallaría en una segunda pasada. El resto usa `IF NOT EXISTS`, `OR REPLACE` o `ON CONFLICT`.

## Supuestos (lo más conservador que se pudo)

1. **`recibo` y la unicidad.** El plan dice `UNIQUE(fuente, recurso, sha256)` y a la vez que el mismo contenido recibido dos veces son dos recepciones. Se resuelve con `UNIQUE(fuente, recurso, sha256, recibido_en)`: una fila por recepción, el objeto no se duplica.
2. **Catálogos sin corrección por fila.** `torneo` y `sede` son identidades estables (clave natural única). Una categoría o un nombre distintos exigen clave nueva y migración explícita. `edicion`, en cambio, sí admite correcciones (`UNIQUE(torneo, temporada, fuente, recibido_en)`).
3. **Prioridades de fuente provisionales.** Se usan dos columnas. `prioridad_calendario` decide `jugador_asercion`, `edicion` y `programa`; `prioridad_resultado` decide `resultado`, `estadistica` y `ranking`. Los valores de `0007` son provisionales (1 = mejor) y deben fijarse con la auditoría de cada fuente.
4. **Licencias.** Solo MCP tiene licencia anotada (CC BY-NC-SA, plan §A.3). Las demás están como «pendiente de verificar». Ningún dato de esas fuentes debe usarse en producción hasta revisar su licencia.
5. **Regla RETRO.** `lunes_semana` de la edición es el lunes de la semana en que **termina** la edición (no la de inicio). Un recibo con `retro = true` solo es visible para cortes **estrictamente posteriores** a `lunes_semana + 7 días` a las 00:00 UTC. Se aplica a `edicion`, `partido`, `programa`, `resultado`, `estadistica` y `ranking` (en el ranking, con `fecha_publicacion` como lunes). No se aplica a `jugador_asercion` ni a `jugador_alias`: no tienen partido al que atarse; su fecha de nacimiento y su alias son estables. **Actualizado el 5-nov:** la regla por semana es solo el valor por omisión; `visible_desde` la sustituye cuando el cargador lo conoce (ver «Limitaciones conocidas»).
6. **Desempates.** Prioridad de fuente, luego `recibido_en` más reciente, luego id mayor. En `jugador_alias` no hay prioridad: gana el alias más reciente no anulado.
7. **Anulación de alias.** Una fila con `anula_a` deja fuera el alias anulado desde su `recibido_en`. La propia fila que anula puede ser el alias correcto. No se comprueba en SQL que anule un alias de la misma fuente e id; eso queda para el cargador.
8. **Resultados.** `completado` exige ganador, `sets` y al menos 2 sets. `retirada` exige ganador y quien retira, distintos. `walkover`, `cancelado` y `descalificado` no tienen ganador (plan §I.9 y §M: nulo para liquidar). `walkover` y `cancelado` tampoco tienen sets.
9. **Orden canónico.** `partido` exige `jugador_1 < jugador_2` por id de jugador, nunca el ganador primero. La clave natural es `UNIQUE(edicion_id, ronda, jugador_1, jugador_2)`.
10. **Sellado.** Cadena global (no por partido), con `hash_previo` único, de modo que no caben bifurcaciones. Serialización: `json_canonico` sobre `[partido_id, version_modelo, version_datos, corte, sellado_en, entradas, distribucion, referencia_mercado, hash_previo]`, con claves ordenadas por código (`COLLATE "C"`) y timestamps UTC con 6 decimales y sufijo `Z`. El génesis es 64 ceros.
11. **G-tiempo.** El inicio de referencia es el `MIN(inicio_programado_utc)` de **todas** las filas de `programa` del partido, sin filtrar por el corte. Si alguna fila no tiene hora fija, o no hay filas, no se sella.
12. **Redondeo de probabilidades.** El plan pide redondear a 6 decimales antes de serializar. La función SQL **no** lo verifica: lo debe garantizar el contrato Python del Sprint 2. **No cumplido en este sprint.**
13. **Sellado con el reloj de la base.** `sellado_en = clock_timestamp()` tomado tras el candado asesor. Hay una comprobación previa en PL/pgSQL, no una sola sentencia con la condición en el `INSERT`.
14. **Permisos.** Las funciones de lectura y `sellar_pronostico` son `SECURITY DEFINER` con `search_path` fijado. El motor no tiene `SELECT` sobre las tablas de evidencia; solo ejecuta funciones.
15. **Cobertura PIT.** Hay funciones `*_a_las` para `jugador_asercion`, `jugador_alias`, `edicion`, `partido`, `programa`, `resultado`, `estadistica` y `ranking`. No hay para `juego_pbp`, `precio_mercado`, `enlace_evento` ni `sin_resolver`; no se pidieron en este sprint.

## Limitaciones conocidas

- **Rendimiento de la lectura PIT: MEDIDO Y CORREGIDO (revisión del 5-nov).** La primera versión llamaba por fila a `lunes_partido_a_las()` (que recorre las ediciones). Medido con `ops/medir_pit.py` sobre datos sintéticos: 2.000 partidos 1,94 s, 4.000 partidos 4,57 s, 8.000 partidos 13,74 s (crecimiento mayor que lineal). Ahora `partido_a_las`, `programa_a_las`, `resultado_a_las` y `estadistica_a_las` usan `lunes_por_partido_a_las(corte)` en una sola pasada (LEFT JOIN, misma semántica: edición no visible ⇒ dato retro oculto): 8.000 partidos 0,03 s y 50.000 partidos 0,46 s (≈ lineal; extrapolación a ~0,5 M: unos segundos, **no medido** a ese tamaño). La regresión `tests/test_db_pit_escala.py` compara el resultado con la fórmula antigua por fila en 6 cortes (con edición corregida y datos retro y no retro) y vigila el tiempo (< 5 s con 20.000 partidos). `lunes_partido_a_las()` se conserva como referencia escalar. `ranking_a_las` no usa esta función y no se midió aparte.
- **`lunes_semana` coherente con `fecha_fin` (revisión del 5-nov).** Con fecha de fin conocida, la base rechaza una edición cuyo `lunes_semana` no sea el lunes de esa semana (`edicion_lunes_coincide_con_fin`). Sin `fecha_fin` (NULL) la regla RETRO confía en el cargador: **el cargador del Sprint 2 debe calcular `fecha_fin` de las ediciones retro**, o una edición de dos semanas con el lunes de inicio dejaría ver resultados antes de jugarse.
- **REGLA RETRO CON `visible_desde` (implementada el 5-nov, aprobada por el titular).** El plan (§A.4) ocultaba los datos retro de un partido hasta pasada la semana en que termina su edición, y eso impedía que la fatiga intratorneo (§C.5, §D.3) y el rating ronda a ronda vieran las rondas anteriores del mismo torneo. Ahora las tablas `edicion`, `partido`, `programa`, `resultado`, `estadistica`, `juego_pbp` y `ranking` tienen `visible_desde TIMESTAMPTZ` (solo cuenta si el recibo es retro). Lo calcula el cargador con el mejor instante CONOCIDO y CONSERVADOR de cuándo el dato era conocible (hora real de fin del partido en SofaScore; en TML, que no trae hora, el final estimado de la ronda; para la edición, el inicio de su semana; para el ranking, el lunes de publicación). Con `visible_desde`: visible para cortes **estrictamente posteriores**. Sin él: la regla por semana (`lunes_semana + 7 días`). Un dato retro nunca se puede ver antes de `visible_desde`: **el cargador debe ser conservador** (si duda, un instante más tarde, nunca más temprano).
- **DEFECTO CORREGIDO (5-nov): el filtro `recibido_en <= corte` ocultaba toda la historia retro.** Un dato retro tiene `recibido_en` = fecha de descarga (2026), así que ningún corte anterior (un walk-forward sobre 2023) lo veía. Lo destapó la prueba de `visible_desde` (las pruebas anteriores solo usaban cortes posteriores a la descarga). Ahora `visible_a_las(corte, recibido_en, retro, lunes, visible_desde)`: dato en vivo ⇒ `recibido_en <= corte`; dato retro ⇒ solo manda `retro_visible`. Entre dos versiones retro de la misma clave gana la más reciente (limitación declarada: una corrección retro posterior vale para todos los cortes). `jugador_asercion` y `jugador_alias` retro valen para cualquier corte (datos de identidad estables). Pruebas: `test_db_visible_desde.py` y la regresión de `test_db_pit_escala.py`.
- **Migraciones no idempotentes del todo** (ver arriba).
- **Sin tabla de alias de torneo** (el plan §B.2 dice que las equivalencias de torneo se guardan «como alias de torneo, igual que los jugadores»): falta para el Sprint 2.
- **Roles sin probar**: el usuario de la base local no puede crear roles; las 3 pruebas de `test_db_roles.py` se omiten. Hay que ejecutarlas con un usuario que pueda crear roles (p. ej. el contenedor `tenis-db` en el ensayo de S6).

## Lo que no se ha probado

- **Roles (`0005` y la parte de `0006` que concede permisos).** El usuario de la prueba local no puede crear roles, así que las tres pruebas de `test_db_roles.py` se omiten. Las sentencias `GRANT` están dentro de bloques `IF` que no se ejecutaron. **Sin verificar en este sprint.** Hay que ejecutar `apps/tenis/tests/test_db_roles.py` con un usuario que pueda crear roles, o revisar a mano en la base de pruebas.
- **Contenedor `tenis-db` y scripts de operación** (`ops/tenis-db/`): no se han desplegado, no se han ejecutado contra Docker real y no hay Docker en esta sesión. Solo se ha comprobado la sintaxis con `bash -n`. `compose.yml` no se ha validado con `docker compose config`.

## Pruebas

Se ejecutan con `correr_pytest_tenis.ps1 apps/tenis/tests -k db` y `QF_TEST_PG_DSN`. Cada prueba crea un esquema `tenis_t_<hex>` (y su `_op`) y lo borra al terminar. La prueba cruzada usa una muestra de 1.000 partidos reales de TML (semilla 20261104) con un cargador mínimo escrito en el propio test.

## Cargador TML (Sprint 2a, retro)

Código: `apps/tenis/src/tenis/carga/` (`tml_reglas`, `tml_score`, `tml_campos`, `tml_parseo`, `tml_orientar`, `tml_agregado`, `tml_escritor`, `tml_carga`, `tml_cli`). Uso: `python -m tenis.carga.tml_cli --snapshot <carpeta tml/originals> --dsn <dsn> --esquema tenis`. Conciliación con la auditoría: `apps/tenis/ops/conciliar_tml.py` y `docs/tenis_carga_tml_conciliacion_20261105.md`.

### Ficheros y recibos

- Se cargan `YYYY.csv`, `YYYY_wta.csv`, `YYYY_challenger.csv` y `atp_quali/YYYY_atp_quali.csv`. No se cargan `ATP_Database.csv` (repite los anuales), `atp_matches_amateur.csv` (amateur) ni los `*ongoing*` (partidos en curso); quedan listados con su número de filas.
- Cada fichero se verifica por tamaño y sha256 contra el manifiesto. Si no coincide o no está en él, se rechaza entero y se registra (`fichero_sha_no_coincide`).
- Recibo: `recibido_en` = `received_at` del manifiesto; `lote` = `tml_` + fecha de `snapshot_created_at`; `retro = true`; original en `objetos/aa/<sha>.csv.gz`. Para ello `almacen.guardar_objeto` y `recibo.nuevo_recibo` admiten `extension` (por defecto `.json.gz`, sin cambio de comportamiento).
- Circuito: `_wta` → wta; el resto (incluidos challengers y previas) → atp.

### Torneos, ediciones y categorías

- Clave de torneo: el `tourney_id` sin el año inicial, en minúsculas. Los torneos de equipos (`W-FC-AAAA-…`) no empiezan por año: la clave es el id completo y el año es el primer grupo de cuatro dígitos.
- Temporada `< 1968` se rechaza (`temporada_anterior_al_esquema`): el CHECK de `edicion.temporada` no admite 1967.
- Edición = torneo × temporada, creada una vez con el recibo de su primera aparición (orden: ATP, WTA, challengers, previas). Fecha = mínimo de las filas; superficie e `indoor` = primer valor no vacío. Cada valor distinto queda como conflicto.
- Categoría por nivel, con significado verificado por nombres de torneo:
  - ATP: `G` GS; `M` M1000 (Miami, Indian Wells, Rome…); `500`, `250`; `F` Finales (Masters, Tour Finals); `O` JJOO; `D` equipos (Davis Cup); `C` Challenger.
  - WTA: `G` GS; `1000` y `PM` WTA1000 (Indian Wells, Miami, Madrid, Beijing); `500`; `250`; `I` 250 (Auckland, Hobart, Acapulco, Linz); `D` equipos (BJK/Fed Cup); `O` JJOO; `F` y `YEC` Finales.
  - `T1` WTA1000, `T2` 500, `T3`/`T4`/`T5` 250: son las categorías históricas de la WTA; la lista de nombres es coherente con ese orden, pero el nivel exacto no está verificado para `T4` y `T5`.
- Niveles **no verificados**, con categoría neutra 250 y aviso `nivel_no_verificado`: ATP `A` (mezcla de Cincinnati, Queen's, Rome… de los años 90) y `P` (torneos pro de 1968-1970); WTA `P` (Premier de 2009-2020, entre 250 y 500), `P5` (asignado a 500; incluye Rome y Cincinnati), `W` (mezcla de Virginia Slims Championships y eventos normales), `A` (Prague Open, United Cup), `T4` y `T5`. Un nivel vacío (solo en algunas previas) deja la categoría vacía si el torneo no tiene otro nivel.
- Si un mismo torneo trae categorías distintas en años distintos, la categoría queda vacía y se registra `categoria_conflicto` (la base no permite corregirla por fila).
- Equipos por nombre (Davis, Billie Jean King/BJK, Fed Cup, United Cup, Laver Cup, Hopman): categoría `equipos` y `por_equipos = true`, también si el nivel no es `D`.

### Duración y visibilidad (regla fijada, con una desviación justificada)

- `L` = `tourney_date` tal cual, sin ajustarla al lunes (la fecha del snapshot no es siempre lunes; ver medición abajo). `fecha_fin = L + duración − 1`; `lunes_semana` = lunes de `fecha_fin` (cumple el CHECK).
- **Desviación:** la duración es de 14 días para los niveles `G`, `M`, `1000`, `PM`, `P5`, `T1`, `F`, `YEC`, `O` y `W`, y 7 para el resto. La regla escrita decía solo «G o M». Con 7 días, la final de un WTA1000 (dos semanas) quedaría visible antes de jugarse, lo que incumple «nunca más temprano que el fin real». Elegir el desfase largo es la opción conservadora.
- `visible_desde` de partido, resultado y estadísticas = tabla fijada (`tml_reglas.DESFASE_7` y `DESFASE_14`), contando desde `L` a las 00:00 UTC. Ronda fuera de la tabla → NULL (regla por semana). La edición lleva `visible_desde = L`.
- Ranking: `fecha_publicacion` = lunes ISO de `tourney_date` (en un domingo, el lunes anterior: nunca adelanta una publicación); `visible_desde` = ese lunes.
- Pruebas de la tabla: la cadena R128→F es monótona y ninguna ronda supera `fecha_fin + 1 d`. Las rondas Q1–Q3 no se encadenan con R128 (en 7 días, Q1 = L+3 y R128 = L+2): la tabla lo fija así y no se corrige.

### Marcador, sets y estado

- TML escribe el marcador desde el ganador. Cada set se guarda como `[g_a, g_b, tb_a, tb_b]` desde el ganador y se reorienta a `jugador_1`/`jugador_2` según el id canónico.
- Tie-break: los puntos entre paréntesis son los del que perdió el set; el ganador del set tiene `max(7, t+2)`. Un super tie-break final `[x-y]` es un set 1-0 con tb `x`/`y` (gana el mayor) y cuenta en `aviso:super_tiebreak_final`.
- Un «completado» exige: sets válidos, al menos 2 sets, el ganador de TML gana la mayoría (`(mejor_de // 2) + 1`) y el perdedor no. Una super-tiebreak que contradice el resultado (`7-6(5) 5-7 [3-10]`) se rechaza (`completado_incoherente`).
- `RET`/`ret.` → retirada (ganador = el de TML; `retira` = el otro). `sets_completos` no cuenta el último set si no es un set terminado (`6-3 2-1 RET` → 1).
- `DEF` → descalificado sin ganador. `W/O` → walkover sin sets; `W/O` con marcador → rechazo. Vacío, `ABD`, `Unfinished`, `Played and abandoned`, `&nbsp;` → cancelado. `WEA` o `RET+H64` con sets, o cualquier token no reconocido → rechazo.
- `duracion_min`: solo 1–600. Vacío, 0 o mayor de 600 → NULL con aviso (nunca 0).

### Jugadores, entradas y estadísticas

- Un `jugador` por (circuito, id de TML), con alias `id_exacto`. Filas con id vacío o con el mismo id en ambos lados → rechazo (`id_jugador_vacio`, `mismo_jugador`). Nombres con «/» → dobles, excluidos.
- Asercion de nombre, altura, país y mano: solo cuando cambia el valor respecto a la última escrita en la carga. Mano: `R`→`D`, `L`→`Z`, `U`→`U`; `A` (ambidiestro) no existe en el CHECK y no se escribe. Altura: 2–3 dígitos (`0` y fechas no). País: tres letras.
- `equivalencias.csv` existe solo con cabecera: no hay equivalencias manuales. Si llegan, el alias apunta al jugador principal (`metodo = manual`).
- Entradas: solo `Q`, `LL`, `WC`, `PR`, `SE`. Variantes en minúsculas (`Wc`, `Ll`, `wc`) y otras (`SR`, `ALT`, `A`, `IP`, `ITF`, `CO`, `NG`, `UP`) → NULL. Cuenta como `aviso:entrada_no_mapeada`, sin rechazo.
- Estadísticas: un lado sin ningún dato no se escribe (no es 0). Si un lado viola un CHECK (`primeros_ganados > primeros_dentro`, `primeros_dentro > puntos_saque`, `bp_salvados > bp_afrontados`) se rechaza la estadística de ese partido; el partido se carga igual.

### Duplicados y ranking

- Clave del partido: (edición, ronda, par de jugadores). La primera aparición se carga; las demás cuentan como `duplicado` y van al CSV de rechazos. Las estadísticas, resultados y ranking solo se escriben para la primera aparición.
- Ranking: una observación por (circuito, lunes, jugador), tomada de las filas aceptadas (también de las duplicadas, sin escribir partido). Si el mismo lunes llega con otro valor, se conserva el primero y se cuenta `conflicto_ranking`.

### Recuentos y garantías

- Leídas = cargadas + rechazadas + duplicadas + dobles (cada fila cae en una sola categoría; los avisos son informativos). El informe lo verifica (`cuadra`).
- Cada fichero es una transacción; la clave natural y `ON CONFLICT DO NOTHING` hacen que repetir la carga no añada filas (prueba `test_carga_tml_idempotencia`).
- Ningún `UPDATE` ni `DELETE` sobre la evidencia. Los ids se resuelven por lote, no por fila.

### Medición del snapshot A (16-oct)

- Día de la semana de `tourney_date` en las 495.960 filas: 312.332 lunes, 128.179 domingos, 17.954 viernes, 12.344 sábados, 10.369 martes, 9.133 miércoles, 5.649 jueves. Se usa `L` literal: en un torneo que empieza en domingo, `L+2` cae en martes y el desfase se cuenta desde el primer día del torneo, como pide la regla. Es una consecuencia de no ajustar la fecha; no se ha medido si alguna ronda de esos torneos se juega después de su visibilidad.
- Resultado de la carga completa (snapshot A, reglas finales del 5-nov): 495.960 filas leídas, 493.867 cargadas, 2.007 rechazadas, 86 duplicadas, 400–430 s; segunda carga: 0 filas nuevas. Recuentos frente a la auditoría y verificación independiente: `docs/tenis_carga_tml_conciliacion_20261105.md`.
- **Decisión tomada en la revisión (5-nov): se aceptan los 7-6 sin puntos de tie-break y los sets de ventaja.** TML antiguo (1968–1990) no registra los puntos del tie-break (faltante = NULL, no inválido) y hubo sets de ventaja sin tie-break; rechazarlos dejaba fuera ≈39.000 partidos reales. Siguen rechazados los sets imposibles (7-4, 9-6, 6-6, 7-7, 8-5, 10-3…). Reversible: es una línea en `tml_score._set_normal`. **Ceros imposibles:** un lado con 0 puntos de saque en un partido terminado es un faltante codificado como 0 (65 partidos medidos); queda sin estadística (NULL) y con aviso `estadistica_cero_imposible`.

## S2b: SofaScore, identidad entre fuentes y captura (5-nov)

Informes por módulo: `docs/tenis_carga_sofascore_20261105.md`, `docs/tenis_identidad_20261105.md`, `docs/tenis_captura_ranking_20261105.md`; integración real y validación del calendario: `docs/tenis_integracion_s2b_20261105.md`.

- **Orden de carga obligatorio:** TML primero y SofaScore después con el resolutor multifuente (`fabrica_resolutor` de `sofascore_cli.ejecutar`); si se carga SofaScore antes, duplica a los jugadores.
- **Códigos de país:** se normalizan a ISO alpha-3 (`identidad/paises.py`) porque TML usa los del COI (sin esto, el 15 % de los jugadores se separaba como homónimo).
- **Calendario retro de TML calibrado con horas reales de SofaScore** (ver `tml_reglas.py`): tablas por ronda = percentil 99,9 del fin real + 1 día. Fuga residual 0,97 % (125 de 12.924). Edición desalineada (3 %): limitación declarada. **Para partidos con hora real, el PIT debe usar los tiempos de SofaScore, no el calendario de TML.**
- **Equivalencia con el principal en un fichero posterior:** el cargador de TML crea el principal al ver el alias (antes era un error).
- **Edición de SofaScore:** inicio = mínimo y fin = máximo de las fechas de torneo de sus eventos (el clasificatorio y el cuadro traen fechas distintas), nunca antes del último partido + 1 día.
- **Ronda QL:** «Qualification Final» (última ronda del clasificatorio), distinta de QF (cuartos).
- **Pendiente:** captura del ranking de SportsAPIPro no probada contra respuesta real; colector con flock solo ejercitado en CI Linux; el resolutor requiere un proveedor de edades de TML (`enlazar.edades_para_resolutor`), porque las edades no se persisten.
