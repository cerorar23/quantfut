#!/bin/sh
# Ejecuta un módulo de la capa de fútbol (`futbol.dato`) en un contenedor desechable con la imagen del worker,
# sin tocar el worker. El DSN se pasa por entorno (`-e PG_DSN` sin valor) para que no aparezca en `ps`.
# Uso:  futbol_correr.sh LIGA [--since AAAA-MM-DD] [--aplicar]                  (cargador de SofaScore)
#       MODULO=qf.ingest.futbol_identidad futbol_correr.sh "" [--aplicar]       (puente de identidad)
# Requiere en ~/futbol_base_unica/src las copias de los módulos que se montan encima de la imagen.
LIGA=${1:-}; [ $# -gt 0 ] && shift
D=${FUTBOL_DIR:-$HOME/futbol_base_unica}
IMAGEN=${FUTBOL_IMAGEN:-$(docker inspect quantfut-worker-1 --format '{{.Config.Image}}')}
PG_DSN=$(docker exec quantfut-worker-1 printenv PG_DSN); export PG_DSN
MONTAJES=""
for f in futbol_sofascore futbol_identidad sofascore_local sofascore_history fotmob_import; do
  [ -f "$D/src/$f.py" ] && MONTAJES="$MONTAJES -v $D/src/$f.py:/app/src/qf/ingest/$f.py:ro"
done
exec docker run --rm --network quantfut_default --entrypoint python -e PG_DSN \
  -v "$HOME/sofascore-scraper/data/v3:/archive:ro" -v "$D/work:/work" $MONTAJES \
  "$IMAGEN" -m "${MODULO:-qf.ingest.futbol_sofascore}" --archive /archive \
  ${LIGA:+--league $LIGA --workdir /work/$LIGA} "$@"
