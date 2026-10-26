# Entorno común del trabajo local sobre la copia de producción (esquema `entreno`). Se carga con `source`.
# Requiere D = carpeta de trabajo (.local/entreno_AAAAMMDD) y el directorio actual en la raíz del repo.
BASE=$(grep "^PG_DSN=" .env | cut -d= -f2-)
export PG_DSN="${BASE}?options=-csearch_path%3Dentreno%2Cpublic"
export ARTIFACT_DIR="$D/artifacts"
# Mismos valores que el worker de producción (`printenv` en quantfut-worker-1, 26-oct-2026). El .env local tenía
# DECAY_HALFLIFE_DAYS=180: sin fijarlos aquí se entrenaría otro modelo.
export DECAY_HALFLIFE_DAYS=270 XG_BLEND=0.65 DEVIG_METHOD=shin SHARP_BOOK=pinnacle META_BLEND_ENABLED=0 RESULTS_PROVIDER=propline
export TG_BOT_TOKEN= TG_ALERT_CHAT= SENTRY_DSN=
export PYTHONPATH=src PYTHONUNBUFFERED=1
PY=${PYTHON:-"/c/Users/huye/Documents/apuesta proyec/.venv/Scripts/python.exe"}
mkdir -p "$ARTIFACT_DIR"
