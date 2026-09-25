#!/usr/bin/env bash
# Lleva al servidor la base de datos local (volcado de pg_dump -Fc).
#
#   ./scripts/restore_db.sh ~/quantfut.dump          # base vacía
#   ./scripts/restore_db.sh ~/quantfut.dump --force  # PISA una base con datos
#
# Por qué restaurar y no rehacer el backfill: la base local ya tiene 50.252
# partidos, 164.289 cuotas y los alias revisados a mano; rehacerlo son horas y
# la revisión de alias no se automatiza.
set -euo pipefail
cd "$(dirname "$0")/.."
DUMP=${1:?uso: scripts/restore_db.sh ruta/quantfut.dump [--force]}
FORCE=${2:-}
PSQL="docker compose exec -T db psql -v ON_ERROR_STOP=1 -U qf -d quantfut"

# Se lee del .env con grep y no con `source`: un valor con '$' (el hash de la
# consola) se expandiría y rompería el script.
GRAFANA_DB_PASSWORD=$(grep -E '^GRAFANA_DB_PASSWORD=' .env | cut -d= -f2-)
[ -n "$GRAFANA_DB_PASSWORD" ] || { echo "Falta GRAFANA_DB_PASSWORD en .env"; exit 1; }

echo "==> Arrancando Postgres"
docker compose up -d db
until docker compose exec -T db pg_isready -U qf -d quantfut >/dev/null 2>&1; do sleep 2; done
# El primer arranque ejecuta db/*.sql (docker-entrypoint-initdb.d); se espera
# a que termine antes de tocar nada.
sleep 5

n=$($PSQL -tAc "SELECT CASE WHEN to_regclass('public.matches') IS NULL THEN 0
                            ELSE (SELECT count(*) FROM matches) END")
if [ "$n" -gt 0 ] && [ "$FORCE" != "--force" ]; then
    echo "La base del servidor ya tiene $n partidos. No se pisa sin --force."
    exit 1
fi

echo "==> Vaciando el esquema creado por el primer arranque"
$PSQL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "==> Restaurando $DUMP"
docker compose cp "$DUMP" db:/tmp/quantfut.dump
docker compose exec -T db pg_restore -U qf -d quantfut --no-owner --no-privileges \
    --exit-on-error /tmp/quantfut.dump
docker compose exec -T db rm -f /tmp/quantfut.dump

echo "==> Migraciones que la base local no tenía (idempotentes)"
for f in 014_injuries.sql 015_ev_cierre.sql 016_af_odds.sql \
         017_picks_precio_justo.sql 018_sombra_sharp.sql 019_clv_daily_ev.sql \
         020_alias_odds_api_coventry.sql; do
    $PSQL -f "/docker-entrypoint-initdb.d/$f"
done

echo "==> Permisos del usuario de solo lectura de Grafana"
# El rol lo crea db/004 en el primer arranque, con una contraseña por defecto
# que no coincide con la que usa Grafana. Los GRANT se perdieron al vaciar el
# esquema.
$PSQL <<SQL
ALTER ROLE qf_readonly PASSWORD '${GRAFANA_DB_PASSWORD}';
GRANT USAGE ON SCHEMA public TO qf_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO qf_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO qf_readonly;
SQL

echo "==> Comprobación"
$PSQL -c "SELECT (SELECT count(*) FROM matches) AS partidos,
                 (SELECT count(*) FROM odds_snapshots) AS cuotas,
                 (SELECT count(*) FROM teams) AS equipos,
                 (SELECT count(*) FROM leagues WHERE active) AS competiciones"
echo "Listo. Siguiente: docker compose up -d"
