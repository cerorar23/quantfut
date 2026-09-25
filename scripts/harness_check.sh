#!/usr/bin/env bash
# Verificación rápida del arnés antes de que el agente empiece a trabajar.
# No toca datos ni contenedores; solo confirma que el repo está sano.
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0

# El entorno virtual del proyecto va PRIMERO. En Windows `python3` resuelve al
# stub de la Microsoft Store, que arranca, responde a --version y no tiene
# ninguna dependencia instalada: el arnés daba "OK" saltándose todos los tests.
PY=""
for cand in .venv/Scripts/python.exe .venv/bin/python python3 python py; do
    if [ -x "$cand" ] || command -v "$cand" >/dev/null 2>&1; then
        if "$cand" -c "import sys" >/dev/null 2>&1; then
            PY="$cand"
            break
        fi
    fi
done

echo "==> Sintaxis de todos los módulos Python"
if [ -z "$PY" ]; then
    echo "    (no se encontró un intérprete de Python en el PATH, se omite)"
elif ! "$PY" -m py_compile $(find src scripts -name '*.py') 2>&1; then
    echo "    ERROR: hay un error de sintaxis. Corrígelo antes de continuar."
    fail=1
fi

echo "==> Tests"
if [ -z "$PY" ]; then
    echo "    (sin Python en el PATH, se omite)"
elif ! "$PY" -c "import pytest" >/dev/null 2>&1; then
    echo "    ERROR: $PY no tiene pytest. Monta el entorno:"
    echo "           python -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements-dev.txt"
    fail=1
elif ! out=$(PYTHONPATH=src "$PY" -m pytest tests -q 2>&1); then
    echo "$out" | tail -20
    echo "    ERROR: hay tests fallando. Arréglalos antes de seguir."
    fail=1
else
    echo "$out" | tail -2
fi

echo "==> docker-compose.yml es válido"
if command -v docker >/dev/null 2>&1; then
    if ! docker compose config -q 2>&1; then
        echo "    ERROR: docker-compose.yml no valida."
        fail=1
    fi
else
    echo "    (docker no disponible en este entorno, se omite)"
fi

echo "==> .env presente"
if [ ! -f .env ]; then
    echo "    AVISO: no hay .env (solo .env.example). Normal si aún no arrancaste servicios."
fi

echo "==> Estado de git"
if [ -d .git ]; then
    git status -s
else
    echo "    (este directorio no es un repo git todavía)"
fi

if [ "$fail" -ne 0 ]; then
    echo
    echo "El arnés encontró problemas. Arréglalos antes de seguir."
    exit 1
fi

echo
echo "OK. El repo está en buen estado."
exit 0
