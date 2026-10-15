#!/usr/bin/env bash
# Despliegue ordenado de QuantFut (ver DEPLOYS.md).
#
#   scripts/deploy.sh estado            compara main con lo que corre en worker y API, y con la etiqueta `latest`
#   scripts/deploy.sh congelar worker   fija el estado EN EJECUCIÓN del worker en una imagen (no reinicia nada)
#
# Solo lee, salvo `congelar`, que crea etiquetas de imagen. No construye ni recrea contenedores: eso se hace
# después de un ensayo y con el visto bueno del usuario, y se anota en DEPLOYS.md.
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
PYEOF
}

estado() {
  [ -z "$(git status --porcelain)" ] || echo "AVISO: el árbol local tiene cambios sin comitear; se compara contra el último commit."
  echo "main (HEAD) = $(git rev-parse --short HEAD) $(git log -1 --format=%s | cut -c1-60)"
  tmp=$(mktemp -d); hashes_repo > "$tmp/repo"
  echo "== código ejecutándose ahora vs main"
  for s in worker api; do hashes_contenedor "$s" > "$tmp/$s"; comparar "contenedor $s" "$tmp/repo" "$tmp/$s"; done
  echo "== imagen con la etiqueta latest del worker (la que usaría un recreate) vs lo que corre"
  hashes_imagen quantfut-worker:latest > "$tmp/latest"; comparar "imagen quantfut-worker:latest" "$tmp/worker" "$tmp/latest"
  echo "== contenedor worker usa: $("${SSH[@]}" "docker inspect quantfut-worker-1 --format '{{.Image}}' | cut -c8-19") | latest = $("${SSH[@]}" "docker images quantfut-worker:latest --format '{{.ID}}'")"
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

case "${1:-estado}" in
  estado) estado ;;
  congelar) congelar "${2:-}" ;;
  *) sed -n '2,8p' "$0"; exit 2 ;;
esac
