# Rediseño NBA — Sprint 0: base `nba_datos` y migraciones

> **Para quien ejecute:** `superpowers:executing-plans`. Implementa la sección 2 de [nba_rediseno_plan_tecnico_20261102.md](nba_rediseno_plan_tecnico_20261102.md) (decisiones D1-D6 aprobadas el 2-nov-2026).

**Objetivo:** una base Postgres propia `nba_datos` con las siete tablas `nba.*`, sus triggers de inmutabilidad, el acceso punto-en-el-tiempo y los roles, aplicable de forma repetible con un ejecutor de migraciones y verificada por pruebas contra un Postgres desechable.

**Arquitectura:** migraciones SQL numeradas en `apps/nba/db/`; ejecutor `nba.v2.migrar` (con candado, suma de verificación y registro); pruebas con un clúster Postgres 16 temporal (`initdb`) que nunca toca la base de fútbol. El contenedor `nba-db` se define pero **no se despliega en el VPS en este sprint sin tu confirmación** (`DEPLOYS.md`).

**Tecnología:** Postgres 16, psycopg 3.2.3 (extra `postgres` ya declarado), pytest 8.3.4.

## Restricciones globales
Las del plan técnico (aislamiento `nba_*`, solo-anexar, `recibido_en` real, LF, sin `qf`). Además: ninguna migración puede ejecutarse contra una base cuyo nombre no empiece por `nba_`.

## Refinamientos al esquema (decididos al detallar S0)
1. `nba.metrica.resolucion` (`'prioridad'` | `'por_fuente'`): `dato_a_las` elige por prioridad de fuente las métricas `'prioridad'` (hechos únicos: box score) y devuelve una fila por fuente, la más reciente visible, para las `'por_fuente'` (disponibilidad y proyecciones, que cambian cada hora y no se pisan entre fuentes).
2. `nba.metrica.nivel` admite `'equipo_jugador'` para métricas que valen para ambos (como `tiros_fuera` en fútbol).
3. `nba.migracion(version TEXT PK, sha256 TEXT, aplicada_en TIMESTAMPTZ)` es infraestructura del ejecutor, no una tabla de datos.

## Task 1: Ejecutor de migraciones
**Files:** Create `apps/nba/src/nba/v2/__init__.py`, `apps/nba/src/nba/v2/migrar.py`; Test `apps/nba/tests/v2/test_migrar.py`, `apps/nba/tests/v2/conftest.py`.
**Interfaces — Produces:**
- `conectar(dsn: str) -> psycopg.Connection`: lanza `ValueError` si el `dbname` no empieza por `nba_`.
- `aplicar(dsn: str, directorio: Path | None = None) -> list[str]`: aplica los `*.sql` pendientes en orden, cada uno en su transacción, con `pg_advisory_xact_lock`; devuelve las versiones aplicadas en esta llamada. Si un archivo ya aplicado cambió (sha256 distinto) lanza `RuntimeError`.
- fixture `base_nueva` (conftest): crea `nba_test_<uuid8>` en el clúster de `NBA_TEST_PG_ADMIN_DSN`, devuelve su DSN y la borra al terminar; `pytest.skip` si la variable no está.
- [ ] Pruebas: `test_conectar_rechaza_bases_ajenas` (`dbname=quantfut` y vacío ⇒ `ValueError`), `test_aplicar_es_idempotente` (segunda llamada devuelve `[]`), `test_aplicar_detecta_archivo_modificado`, `test_aplicar_en_orden_y_atomico` (un archivo con error no deja registro ni objetos).
- [ ] Verificar rojo → implementar → verde → commit.

## Task 2: Esquema, inmutabilidad y semillas
**Files:** Create `apps/nba/db/0001_esquema.sql`, `0002_inmutabilidad.sql`, `0003_semillas.sql`; Test `apps/nba/tests/v2/test_esquema.py`.
**Interfaces — Produces:** tablas, claves y checks exactos de la sección 2 del plan técnico; `nba.entidad.canonica_id` se completa con un trigger `BEFORE INSERT` (= `entidad_id` si llega nulo); trigger `nba.rechazar_cambio()` en `UPDATE`/`DELETE`/`TRUNCATE` de `entidad`, `captura`, `dato`, `cuota`, `evento`, `pronostico`; semillas: 9 fuentes (prioridades 1-9 en el orden del plan) y el catálogo inicial de métricas (partido, equipo, jugador, disponibilidad y proyecciones de Rotowire).
- [ ] Pruebas: `test_tablas_y_claves_existen`, `test_cuota_rechaza_valor_menor_o_igual_a_uno`, `test_dato_exige_valor_o_etiqueta`, `test_dato_clave_unica_evita_duplicados`, `test_cambios_rechazados_en_tablas_de_evidencia` (parametrizada: 6 tablas × UPDATE/DELETE/TRUNCATE), `test_entidad_canonica_apunta_a_si_misma`, `test_alias_apunta_a_la_canonica`, `test_semillas_fuentes_prioridad_unica`, `test_semillas_metricas_nombres_unicos_y_nivel_valido`, `test_pronostico_unico_con_entidad_nula` (`NULLS NOT DISTINCT`).
- [ ] Verificar rojo → implementar → verde → commit.

## Task 3: Acceso punto-en-el-tiempo, vistas de cuotas y roles
**Files:** Create `apps/nba/db/0004_lectura.sql`, `0005_roles.sql`; Test `apps/nba/tests/v2/test_lectura.py`.
**Interfaces — Produces:** `nba.dato_a_las(corte timestamptz) RETURNS SETOF nba.dato`; vistas `nba.dato_vigente` (corte = `now()`), `nba.conflicto`, `nba.cuota_cierre`, `nba.cuota_margen(partido_id, casa, mercado, periodo, entidad_id, linea, n_lados, margen)`; roles de grupo `nba_escritor` (INSERT + uso de secuencias, sin UPDATE/DELETE) y `nba_lector` (SELECT) creados solo si no existen.
- [ ] Pruebas: `test_dato_a_las_no_ve_el_futuro` (fila con `recibido_en` posterior al corte no aparece), `test_prioridad_gana_en_metricas_de_prioridad` (oficial sobre SofaScore aunque SofaScore sea más reciente), `test_por_fuente_devuelve_una_fila_por_fuente_la_mas_reciente`, `test_dato_vigente_equivale_a_dato_a_las_ahora`, `test_conflicto_lista_solo_marcadas`, `test_cuota_cierre_toma_la_ultima_del_cierre`, `test_cuota_margen_dos_lados` (1,91/1,91 ⇒ margen ≈ 0,0471), `test_escritor_no_puede_actualizar_ni_borrar`, `test_lector_solo_lee`.
- [ ] Verificar rojo → implementar → verde → commit.

## Task 4: Contenedor `nba-db` y guion del clúster de prueba
**Files:** Create `apps/nba/ops/nba-db/compose.yml`, `apps/nba/ops/nba-db/README.md`, `apps/nba/ops/cluster_prueba.py`.
**Interfaces — Produces:** `compose.yml` con servicio `nba-db` (`postgres:16-alpine`, volumen y red propios, sin puerto publicado, contraseñas por variables `NBA_DB_*` sin valores en el repo, migraciones montadas de solo lectura); `cluster_prueba.py {start|stop}`: crea con `initdb` un clúster temporal en el puerto 55432 y escribe su DSN administrador en la salida.
- [ ] Verificar: `docker compose config` no disponible en este PC ⇒ validar el YAML con `python -c "import yaml"` y revisarlo contra `docs/nba_arquitectura_aislada.md` sección 3; el despliegue en el VPS queda como paso aparte con confirmación del titular y entrada en `DEPLOYS.md`.
- [ ] Commit.

## Revisión final del sprint
- [ ] `pytest apps/nba/tests/v2 -v` en verde con el clúster temporal; `pytest apps/nba/tests` completo sin regresiones (las pruebas viejas que dependen de datos locales quedan como estaban).
- [ ] Anotar S0 en `harness/tareas.md` y `harness/progreso.md` (la decisión clave: por qué `resolucion` por métrica).

## Review Focus de este sprint
1. Fila con `recibido_en` exactamente igual al corte: debe verse (≤).
2. Dos filas de la misma fuente con el mismo `recibido_en`: desempata `dato_id` descendente.
3. `TRUNCATE ... CASCADE` y `DELETE` desde el rol dueño también deben fallar.
4. Migración parcial por error: ni registro ni objetos a medias.
5. DSN de fútbol (`quantfut`) pasado por error al ejecutor: rechazado antes de abrir transacción.
