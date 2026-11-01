#!/usr/bin/env bash
# Arranque ordenado de la fase 1. El orden importa: cada paso depende del anterior.
set -euo pipefail
cd "$(dirname "$0")/.."
D="docker compose exec -T worker"

echo "==> 1/7  Esquema de base de datos"
docker compose up -d db cache
sleep 8
# 006 y 007 son ALTER TABLE y seed: van aqui. Los ficheros de ALIAS (005, 008,
# 009) NO: necesitan que los equipos existan y se aplican tras el backfill.
for f in db/001_schema.sql db/002_seed_leagues.sql db/003_api_football.sql \
         db/004_grafana_readonly.sql db/006_shot_stats.sql \
         db/007_competiciones.sql db/010_ligas_europeas.sql \
         db/012_shadow_challengers.sql db/014_injuries.sql \
         db/015_ev_cierre.sql db/016_af_odds.sql \
         db/017_picks_precio_justo.sql db/018_sombra_sharp.sql; do
  docker compose exec -T db psql -U qf -d quantfut -f "/docker-entrypoint-initdb.d/$(basename "$f")" \
    || echo "    (ya aplicado, se omite)"
done

echo "==> 3/7  Backfill historico (football-data.co.uk, ~10 min)"
$D python -m qf.ingest.history_fd

echo "==> 4/7  Emparejamiento de nombres entre fuentes"
$D python scripts/bootstrap_aliases.py
echo
echo "    DETENTE AQUI si quedaron nombres pendientes."
echo "    Corrige aliases_pendientes.csv y aplica:"
echo "      docker compose exec -T worker python scripts/bootstrap_aliases.py --fix aliases_pendientes.csv"
read -rp "    Pulsa Enter cuando la lista este vacia..."

# Los alias de FBref se aplican DESPUES del backfill: necesitan que los
# equipos ya existan en la tabla teams o no se registra ninguno. Cada fichero
# avisa por RAISE WARNING si su liga esta vacia.
echo "==> 4b/7  Alias de FBref (revisados a mano)"
for f in 005_fbref_aliases.sql 008_mls_aliases.sql 009_argentina_aliases.sql \
         011_aliases_europa.sql 013_aliases_api_football.sql; do
  docker compose exec -T db psql -U qf -d quantfut \
    -f "/docker-entrypoint-initdb.d/$f" || true
done

echo "==> 5/7  Calendario y xG"
$D python -m qf.ingest.fixtures
$D python -m qf.ingest.xg_worldfootball

# Las copas van DESPUES del xG y del backfill: uefa_cups nunca crea equipos, asi
# que si los clubes de LaLiga o Premier no existen todavia descarta todos los
# partidos en silencio.
echo "==> 6/7  Historico de Champions y Europa League"
$D python -m qf.ingest.uefa_cups

echo "==> 7/7  Entrenar el primer modelo y chequear salud"
$D python -m qf.model.train
$D python -m qf.ingest.health

echo
echo "Fase 1 completa. Arranca los workers:  docker compose up -d"
