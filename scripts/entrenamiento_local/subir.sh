#!/usr/bin/env bash
# Paso 5: sube los artefactos del candidato al volumen del servidor y lo registra con `registrar.py` dentro del worker.
#   scripts/entrenamiento_local/subir.sh .local/entreno_AAAAMMDD <versión>            ensayo (no escribe en la base)
#   scripts/entrenamiento_local/subir.sh .local/entreno_AAAAMMDD <versión> --activar  registra y activa
# Nunca pisa un artefacto existente. Anotar el despliegue en DEPLOYS.md con su vuelta atrás.
set -euo pipefail
D=${1:?carpeta}; V=${2:?versión}; MODO=${3:-}
SSH=${QF_SSH:-quantfut}
AQUI=$(dirname "$0")
test -f "$D/subida_$V.json" || { echo "falta $D/subida_$V.json: corre exportar.py"; exit 1; }
ya=$(ssh "$SSH" "docker exec quantfut-worker-1 sh -c 'ls /srv/quantfut/artifacts/*_$V.pkl 2>/dev/null | wc -l'")
if [ "$ya" != "0" ] && [ "$MODO" != "--activar" ]; then echo "AVISO: ya hay $ya artefactos de $V en el servidor"; fi
ssh "$SSH" "rm -rf /tmp/subida_$V && mkdir -p /tmp/subida_$V"
scp -q "$D"/artifacts/*_"$V".pkl "$D/subida_$V.json" "$AQUI/registrar.py" "$SSH":/tmp/subida_"$V"/
ssh "$SSH" "set -e; cd /tmp/subida_$V
  for f in *_$V.pkl; do
    docker exec quantfut-worker-1 test -e /srv/quantfut/artifacts/\$f || docker cp \$f quantfut-worker-1:/srv/quantfut/artifacts/\$f
  done
  docker cp subida_$V.json quantfut-worker-1:/tmp/; docker cp registrar.py quantfut-worker-1:/tmp/
  docker exec quantfut-worker-1 sh -c 'cd /app && PYTHONPATH=/app/src python /tmp/registrar.py /tmp/subida_$V.json $MODO'"
