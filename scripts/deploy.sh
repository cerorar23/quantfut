#!/usr/bin/env bash
# Despliegue ordenado de QuantFut (ver DEPLOYS.md).
#
#   scripts/deploy.sh estado            compara main con lo que corre en worker y API, y con la etiqueta `latest`
#   scripts/deploy.sh congelar worker   fija el estado EN EJECUCIÓN del worker en una imagen (no reinicia nada)
#   scripts/deploy.sh construir <api|worker>   construye en el servidor la imagen del commit actual (`git archive`
#                                       por SSH: no hace falta clave de despliegue ni `git pull` en el servidor)
#   scripts/deploy.sh ensayo <api|worker> <imagen>   solo lectura: módulos importables y, en el worker, entradas del cron
#   scripts/deploy.sh desplegar <api|worker> <imagen>   respalda el compose, cambia SOLO la etiqueta de ese servicio
#                                       y recrea SOLO ese servicio. Exige CONFIRMO=si
#
# `estado`, `ensayo` solo leen; `congelar` y `construir` crean imágenes/etiquetas; solo `desplegar` toca contenedores,
# y siempre después de un ensayo, con el visto bueno del usuario y anotado en DEPLOYS.md. `construir` y `desplegar`
# exigen árbol limpio y HEAD == origin/main (lo que corre en producción es lo que dice `main`).
set -euo pipefail
cd "$(dirname "$0")/.."
SSH=(ssh -i "${QF_SSH_KEY:-$HOME/.ssh/quantfut_vps}" -o BatchMode=yes "${QF_SSH_HOST:-qf@31.220.72.30}")
PY=${PYTHON:-python}

hashes_repo() {
  git ls-files 'src/*.py' | sort | while read -r f; do echo "$(git show "HEAD:$f" | tr -d '\r' | sha256sum | cut -c1-12) $f"; done
}
hashes_contenedor() {  # $1 = servicio
  "${SSH[@]}" "cd ~/quantfut && docker compose exec -T $1 sh -c 'cd /app && find src -name \"*.py\" | sort | while read f; do echo \"\$(tr -d \"\\r\" < \$f | sha256sum | cut -c1-12) \$f\"; done'"
}
hashes_imagen() {  # $1 = imagen
  "${SSH[@]}" "docker run --rm --entrypoint sh $1 -c 'cd /app && find src -name \"*.py\" | sort | while read f; do echo \"\$(tr -d \"\\r\" < \$f | sha256sum | cut -c1-12) \$f\"; done'"
}
comparar() {  # $1 = nombre, $2 = archivo A (referencia), $3 = archivo B
  "$PY" - "$1" "$2" "$3" <<'PYEOF'
import sys
def carga(p):
    d = {}
    for l in open(p, encoding="utf-8", errors="ignore"):
        l = l.strip()
        if l:
            h, f = l.split(" ", 1)
            d[f] = h
    return d
nombre, a, b = sys.argv[1], carga(sys.argv[2]), carga(sys.argv[3])
dif = sorted(f for f in a if f in b and a[f] != b[f])
falta = sorted(f for f in a if f not in b)
corto = lambda xs: ", ".join(x.replace("src/qf/", "") for x in xs[:8]) + (" ..." if len(xs) > 8 else "")
print(f"  {nombre}: {len(b)} archivos | distintos a main: {len(dif)} | faltan de main: {len(falta)}")
if dif: print(f"     distintos: {corto(dif)}")
if falta: print(f"     faltan: {corto(falta)}")
PYEOF
}

estado() {
  [ -z "$(git status --porcelain)" ] || echo "AVISO: el árbol local tiene cambios sin comitear; se compara contra el último commit."
  echo "main (HEAD) = $(git rev-parse --short HEAD) $(git log -1 --format=%s | cut -c1-60)"
  tmp=$(mktemp -d); hashes_repo > "$tmp/repo"
  echo "== código ejecutándose ahora vs main"
  for s in worker api; do hashes_contenedor "$s" > "$tmp/$s"; comparar "contenedor $s" "$tmp/repo" "$tmp/$s"; done
  echo "== imagen fijada en el compose del repo vs la que corre (un recreate usa la del compose)"
  for s in api worker; do
    corre=$("${SSH[@]}" "docker inspect quantfut-$s-1 --format '{{.Config.Image}}'")
    fijada=$(awk -v s="$s:" '/^  [a-z_-]+:$/ {cur=$1} cur==s && /^    image:/ {print $2; exit}' docker-compose.yml)
    if [ "$corre" = "$fijada" ]; then echo "  $s: $corre (coincide)"; else echo "  $s: corre $corre | compose del repo $fijada  <-- ACTUALIZAR docker-compose.yml"; fi
  done
  rm -rf "$tmp"
}

congelar() {
  [ "${1:-}" = worker ] || { echo "solo se implementa 'worker'"; exit 2; }
  fecha=$(date +%Y%m%d)
  "${SSH[@]}" "set -e; docker tag quantfut-worker:latest quantfut-worker:latest-previo-$fecha
    docker commit --pause=false -m 'Estado en ejecución del worker' quantfut-worker-1 quantfut-worker:en-ejecucion-$fecha >/dev/null
    docker tag quantfut-worker:en-ejecucion-$fecha quantfut-worker:latest
    docker images quantfut-worker --format '{{.Tag}} {{.ID}}' | grep -E '^(latest|latest-previo-$fecha|en-ejecucion-$fecha) '"
}

exigir_main_limpio() {
  [ -z "$(git status --porcelain)" ] || { echo "ERROR: árbol con cambios sin comitear"; exit 1; }
  git fetch -q origin main
  [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || { echo "ERROR: HEAD no es origin/main"; exit 1; }
}
servicio_valido() { case "${1:-}" in api|worker) ;; *) echo "servicio: api o worker"; exit 2 ;; esac; }

construir() {  # $1 = servicio. Imagen: quantfut-<servicio>:<commit>. No toca ningún contenedor.
  servicio_valido "${1:-}"; exigir_main_limpio
  sha=$(git rev-parse --short HEAD); dir="releases/$1-$sha"
  git archive HEAD Dockerfile requirements.txt src frontend | "${SSH[@]}" "mkdir -p ~/quantfut/$dir && tar -x -C ~/quantfut/$dir"
  "${SSH[@]}" "cd ~/quantfut/$dir && docker build -q -t quantfut-$1:$sha ." && echo "imagen quantfut-$1:$sha lista (ensayo y luego desplegar)"
}

ensayo() {  # $1 = servicio, $2 = imagen. Solo lectura, en un contenedor aparte sin red ni volúmenes.
  servicio_valido "${1:-}"; img=${2:?imagen}
  "${SSH[@]}" "docker run --rm --network none --entrypoint python $img -c \"
import importlib, pkgutil, qf
fallos = []
for m in pkgutil.walk_packages(qf.__path__, 'qf.'):
    try: importlib.import_module(m.name)
    except Exception as e: fallos.append(m.name + ': ' + type(e).__name__)
print('modulos con error:', fallos or 'ninguno'); raise SystemExit(1 if fallos else 0)\""
  if [ "$1" = api ]; then
    "${SSH[@]}" "docker run --rm --network none --entrypoint python $img -c 'from qf.api.main import app; print(\"rutas:\", len(app.routes))'"
  else
    "${SSH[@]}" "docker run --rm -i --network none --entrypoint sh $img -c 'cat > /tmp/e.py; PYTHONPATH=/app/src python -c \"import py_compile;py_compile.compile(\\\"/tmp/e.py\\\",doraise=True)\"'" < scripts/ensayo_worker.py       && echo "ensayo_worker.py compila; el ensayo completo (cron + cadena) corre dentro del worker: ver DEPLOYS.md 2026-10-15"
  fi
}

desplegar() {  # $1 = servicio, $2 = imagen. Cambia solo la etiqueta de ese servicio y recrea solo ese servicio.
  servicio_valido "${1:-}"; img=${2:?imagen}; exigir_main_limpio
  [ "${CONFIRMO:-}" = si ] || { echo "ERROR: falta CONFIRMO=si (visto bueno del usuario)"; exit 2; }
  "${SSH[@]}" "docker image inspect $img >/dev/null" || { echo "ERROR: la imagen $img no existe en el servidor"; exit 1; }
  copia="releases/compose-antes-$(date +%Y%m%d-%H%M%S).yml"
  "${SSH[@]}" "cd ~/quantfut && cp -p docker-compose.yml $copia && awk -v s='$1:' -v t='$img' '/^  [a-z_-]+:\$/ {cur=\$1} cur==s && /^    image:/ {print \"    image: \" t; next} {print}' $copia > docker-compose.yml.nuevo && mv docker-compose.yml.nuevo docker-compose.yml && docker compose up -d --no-deps --no-build --force-recreate $1"
  echo "respaldo del compose: ~/quantfut/$copia"
  if [ "$1" = api ]; then
    for i in 1 2 3 4 5 6; do sleep 5; code=$("${SSH[@]}" "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health") && [ "$code" = 200 ] && { echo "salud API: 200"; break; }; done
    [ "$code" = 200 ] || { echo "ERROR: salud API $code. Vuelta atrás: restaurar $copia y recrear"; exit 1; }
  fi
  echo "Falta: actualizar docker-compose.yml del repo con $img y anotar DEPLOYS.md (con la vuelta atrás: $copia)."
}

case "${1:-estado}" in
  estado) estado ;;
  congelar) congelar "${2:-}" ;;
  construir) construir "${2:-}" ;;
  ensayo) ensayo "${2:-}" "${3:-}" ;;
  desplegar) desplegar "${2:-}" "${3:-}" ;;
  *) sed -n '2,15p' "$0"; exit 2 ;;
esac
