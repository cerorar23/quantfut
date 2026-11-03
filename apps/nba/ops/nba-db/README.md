# nba-db: base `nba_datos` del rediseño NBA

Postgres 16 propio, aislado de la base de fútbol (decisión D1 del 2-nov-2026). Esquema `nba`; ver
[docs/nba_rediseno_plan_tecnico_20261102.md](../../../../docs/nba_rediseno_plan_tecnico_20261102.md).

## Probar en local (sin Docker)

```bash
python apps/nba/ops/cluster_prueba.py start        # clúster temporal en 127.0.0.1:55432
export NBA_TEST_PG_ADMIN_DSN="postgresql://postgres@127.0.0.1:55432/postgres"
apps/nba/.venv/Scripts/python.exe -m pytest apps/nba/tests/v2
python apps/nba/ops/cluster_prueba.py stop
```

## Aplicar migraciones a una base `nba_*`

```bash
NBA_DB_DSN="postgresql://usuario:clave@host:5432/nba_datos" python -m nba.v2.migrar
```

El ejecutor rechaza cualquier base cuyo nombre no empiece por `nba_`, aplica los `apps/nba/db/*.sql` pendientes en
orden (cada uno en su transacción) y falla si un archivo ya aplicado cambió de contenido.

## Despliegue en el VPS (pendiente de confirmación del titular)

Seguir `DEPLOYS.md`: una sesión a la vez, `docker compose -p nba-db ... up -d` con `NBA_DB_PASSWORD` en el entorno,
`docker compose config` antes de arrancar, aplicar migraciones, crear los usuarios de login (migración, colectores,
API) y agregarlos a `nba_escritor` / `nba_lector`, anotar el despliegue y su vuelta atrás
(`docker compose -p nba-db down`; el volumen `nba_db_datos` se conserva).
