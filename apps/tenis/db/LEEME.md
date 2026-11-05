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
