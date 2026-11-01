#!/bin/sh
# Pasada diaria ligera de la tabla única `futbol.dato` (db/094-096). Un solo proceso a la vez (flock en el cron) y con nice.
#  1. Identidad: enlaza jugadores nuevos con el id canónico (SofaScore) y registra los ids sin ficha.
#  2. FotMob: lo recibido en los últimos 3 días (prioridad 1). Su carga conserva lo que otra fuente completó en
#     sus filas, así que ya no hace falta recargar SofaScore a la fuerza.
#  3. SofaScore: lo asentado en los últimos 4 días (los partidos tardan 72 h en dejar de ser provisionales), liga por
#     liga. Si el original no cambió no hace nada; si es nuevo o cambió, carga o completa las columnas vacías.
#  4. Clima (ERA5, FotMob de respaldo) y estadio/altitud (OpenTopoData).
# API-Football ya no entrega datos nuevos (31-oct-2026): no forma parte de la pasada diaria.
set -u
D=${FUTBOL_DIR:-$HOME/futbol_base_unica}
SINCE=$(date -u -d '4 days ago' +%F)
echo "== $(date -u +%FT%TZ) inicio desde $SINCE"
MODULO=qf.ingest.futbol_identidad nice -n 10 "$D/futbol_correr.sh" "" --aplicar 2>&1 | tail -1 | cut -c1-300
docker exec -i quantfut-db-1 psql -U qf -d quantfut -X -At -F ' | '   -c "select 'fotmob', * from futbol.cargar_fotmob(now() - interval '3 days')"
for LIGA in it.serie_a gb.premier_league es.laliga fr.ligue_1 de.bundesliga nl.eredivisie pt.primeira br.serie_a mx.liga_mx ar.primera; do
  nice -n 10 "$D/futbol_correr.sh" $LIGA --since "$SINCE" --aplicar 2>&1 | tail -1 | cut -c1-400
done
docker exec -i quantfut-db-1 psql -U qf -d quantfut -X -At -F ' | '   -c "select 'clima', futbol.cargar_clima()" -c "select 'estadio', futbol.cargar_estadio()"
docker exec -i quantfut-db-1 psql -U qf -d quantfut -X -At -F ' | '   -c "select 'previo', * from futbol.cargar_previo(now() - interval '2 days')" -c "select 'derbi', * from futbol.cargar_derbis()"
echo "== $(date -u +%FT%TZ) fin"
