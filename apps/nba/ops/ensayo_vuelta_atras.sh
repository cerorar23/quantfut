#!/bin/sh
# F4.4: ensayo REAL de vuelta atrás de la imagen del motor en el cron. Solo cuando no hay partidos en ventana de sellado.
# 1) cambia imagen_motor a imagen_motor.anterior y comprueba que el motor corre con ella por la misma ruta que el cron (ejecutar_motor.sh);
# 2) comprueba que la imagen más antigua (primer despliegue con props) también corre contra la base de hoy;
# 3) restaura la imagen en uso, aunque algo falle.
cd ~/nba-isolated/nba-captura || exit 1
ACTUAL=$(cat imagen_motor)
ANTERIOR=$(cat imagen_motor.anterior)
trap 'echo "$ACTUAL" > imagen_motor; echo "imagen restaurada: $(cat imagen_motor)"' EXIT
echo "en uso: $ACTUAL; anterior: $ANTERIOR"
echo "$ANTERIOR" > imagen_motor
INICIO=$(date +%s)
./ejecutar_motor.sh | python3 -c "
import sys, json
d = json.loads(sys.stdin.read()); print('vuelta atrás ->', d['version_modelo'][-30:], '| errores', d['errores'], '| sellados', len(d['sellados']))"
echo "vuelta atrás efectiva en $(( $(date +%s) - INICIO )) s con $(cat imagen_motor)"
for IMAGEN in nba-motor:233e372; do
  docker run --rm --network nba-red --user "$(id -u):$(id -g)" --read-only --tmpfs /tmp --cap-drop ALL --memory 1g --env-file motor.env "$IMAGEN" \
    python -m nba.v2.motor --simulacro | python3 -c "
import sys, json
d = json.loads(sys.stdin.read()); print('imagen antigua $IMAGEN ->', d['version_modelo'][:12], '| errores', d['errores'], '| omitidos', len(d['omitidos']))"
done
