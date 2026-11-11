#!/usr/bin/env python3
"""Verificador público sin dependencias de la cadena de hashes de QuantFut.

Pensado para terceros que quieran auditar la integridad de los pronósticos
sellados sin instalar el proyecto ni depender de la base de datos: solo usa
la biblioteca estándar de Python 3.

Formas de uso:
  python scripts/verificar_cadena_publica.py
  python scripts/verificar_cadena_publica.py --url https://pronosticosdeportivos.pro/chain?limit=365
  python scripts/verificar_cadena_publica.py --archivo chain.json --desde-genesis
  python scripts/verificar_cadena_publica.py --dir ./ruta/a/cadena-publica
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
URL_POR_DEFECTO = "https://pronosticosdeportivos.pro/chain?limit=365"
_RE_HASH = re.compile(r"^[0-9a-f]{64}$")


def sha256_hex(texto: str) -> str:
    """Calcula SHA-256 UTF-8 en hexadecimal minúsculas, idéntico a qf.publish.hashchain."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _es_hash(valor: Any) -> bool:
    return isinstance(valor, str) and bool(_RE_HASH.match(valor))


def _etiqueta_lote(lote: dict[str, Any], indice: int) -> str:
    fecha = lote.get("batch_date") or "?"
    kind = lote.get("batch_kind") or "diario"
    match_id = lote.get("match_id")
    extra = f" {match_id}" if match_id else ""
    return f"lote #{indice + 1} ({fecha} {kind}{extra})"


def verificar_lotes(
    lotes: list[dict[str, Any]],
    *,
    exigir_genesis: bool = False,
    ya_cronologico: bool = False,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Verifica una lista de lotes procedente de `/chain`.

    `/chain` devuelve los lotes en orden `seq DESC` (el más reciente primero),
    por lo que por defecto se invierte la lista para recorrerla en orden cronológico.
    """
    if not isinstance(lotes, list) or not lotes:
        return False, ["No hay lotes para verificar."], {"total": 0}

    cron = list(lotes) if ya_cronologico else list(reversed(lotes))
    errores: list[str] = []

    for i, lote in enumerate(cron):
        etiqueta = _etiqueta_lote(lote if isinstance(lote, dict) else {}, i)
        if not isinstance(lote, dict):
            errores.append(f"{etiqueta}: formato de lote inválido")
            continue

        payload = lote.get("payload_sha256")
        prev = lote.get("prev_sha256")
        chain = lote.get("chain_sha256")
        if not (_es_hash(payload) and _es_hash(prev) and _es_hash(chain)):
            errores.append(f"{etiqueta}: falta algún hash SHA-256 válido (64 hex)")
            continue

        if i == 0:
            if exigir_genesis and prev != GENESIS:
                errores.append(
                    f"{etiqueta}: se esperaba enlace al génesis ({GENESIS[:16]}…) y llega {prev[:16]}…"
                )
        else:
            anterior = cron[i - 1]
            prev_real = anterior.get("chain_sha256") if isinstance(anterior, dict) else None
            if prev_real and prev != prev_real:
                errores.append(
                    f"{etiqueta}: CADENA ROTA en prev_sha256 "
                    f"(esperado {prev_real[:16]}…, obtenido {prev[:16]}…)"
                )

        esperado = sha256_hex(prev + payload)
        if chain != esperado:
            errores.append(
                f"{etiqueta}: hash de cadena inconsistente "
                f"(esperado {esperado[:16]}…, obtenido {chain[:16]}…)"
            )

    primero = cron[0] if isinstance(cron[0], dict) else {}
    ultimo = cron[-1] if isinstance(cron[-1], dict) else {}
    resumen = {
        "modo": "chain_json",
        "total": len(cron),
        "desde_genesis": primero.get("prev_sha256") == GENESIS,
        "primer_hash": primero.get("chain_sha256"),
        "ultimo_hash": ultimo.get("chain_sha256"),
    }
    return not errores, errores, resumen


def _cargar_recibos_ordenados(directorio: Path) -> list[tuple[Path, dict[str, Any]]]:
    archivos = [
        *sorted(directorio.glob("????-??-??.receipt.json")),
        *sorted(directorio.glob("partido/????-??-??/*.receipt.json")),
        *sorted(directorio.glob("escalera/????-??-??/*.receipt.json")),
    ]
    todos = [(f, json.loads(f.read_text(encoding="utf-8"))) for f in archivos]
    por_prev: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    for f, r in todos:
        if isinstance(r, dict):
            por_prev.setdefault(str(r.get("prev_sha256", "")), []).append((f, r))

    orden: list[tuple[Path, dict[str, Any]]] = []
    prev = GENESIS
    while len(por_prev.get(prev, [])) == 1 and len(orden) < len(todos):
        f, r = por_prev[prev][0]
        orden.append((f, r))
        prev = str(r.get("chain_sha256", ""))
    return orden if len(orden) == len(todos) else todos


def verificar_directorio(directorio: Path) -> tuple[bool, list[str], dict[str, Any]]:
    """Verifica un directorio local de recibos `.receipt.json` y cuerpos `.json` revelados."""
    if not directorio.is_dir():
        return False, [f"No existe el directorio: {directorio}"], {"modo": "directorio", "total": 0}

    try:
        recibos = _cargar_recibos_ordenados(directorio)
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"No se pudieron leer los recibos: {exc}"], {"modo": "directorio", "total": 0}

    if not recibos:
        return False, ["No se encontraron recibos *.receipt.json en el directorio."], {"modo": "directorio", "total": 0}

    prev = GENESIS
    errores: list[str] = []
    sin_revelar = 0

    for rf, r in recibos:
        if not isinstance(r, dict):
            errores.append(f"{rf.name}: el recibo no es un objeto JSON")
            continue
        payload = r.get("payload_sha256")
        prev_r = r.get("prev_sha256")
        chain_r = r.get("chain_sha256")
        if not (_es_hash(payload) and _es_hash(prev_r) and _es_hash(chain_r)):
            errores.append(f"{rf.name}: hashes SHA-256 ausentes o inválidos")
            continue

        nombre = rf.name.removesuffix(".receipt.json")
        body = rf.with_name(f"{nombre}.json")
        if body.exists():
            payload_real = sha256_hex(body.read_text(encoding="utf-8"))
            if payload != payload_real:
                errores.append(
                    f"{body.name}: CONTENIDO ALTERADO "
                    f"(esperado {payload[:16]}…, obtenido {payload_real[:16]}…)"
                )
        else:
            sin_revelar += 1

        if prev_r != prev:
            errores.append(f"{rf.name}: CADENA ROTA en el enlace anterior")
        esperado = sha256_hex(prev + payload)
        if chain_r != esperado:
            errores.append(f"{rf.name}: hash de cadena inconsistente")
        prev = chain_r

    cuerpos = [
        *sorted(directorio.glob("????-??-??.json")),
        *(p for p in sorted(directorio.glob("partido/????-??-??/*.json")) if not p.name.endswith(".receipt.json")),
        *(p for p in sorted(directorio.glob("escalera/????-??-??/*.json")) if not p.name.endswith(".receipt.json")),
    ]
    for body in cuerpos:
        if not body.with_name(f"{body.stem}.receipt.json").exists():
            errores.append(f"{body.name}: falta el recibo")

    resumen = {
        "modo": "directorio",
        "total": len(recibos),
        "revelados": len(recibos) - sin_revelar,
        "solo_compromiso": sin_revelar,
        "ultimo_hash": recibos[-1][1].get("chain_sha256") if isinstance(recibos[-1][1], dict) else None,
    }
    return not errores, errores, resumen


def _cargar_json_url(url: str, timeout: float = 15.0) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "QuantFut-VerificadorCadena/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verifica de forma independiente la cadena pública SHA-256 de QuantFut."
    )
    fuente = parser.add_mutually_exclusive_group()
    fuente.add_argument("--url", default=URL_POR_DEFECTO, help="Endpoint /chain JSON a auditar.")
    fuente.add_argument("--archivo", type=Path, help="Archivo JSON local descargado de /chain.")
    fuente.add_argument("--dir", type=Path, help="Directorio local con recibos .receipt.json y .json.")
    parser.add_argument(
        "--desde-genesis",
        action="store_true",
        help="Exigir que el lote más antiguo de la respuesta arranque en el génesis (64 ceros).",
    )
    parser.add_argument("--json", action="store_true", help="Emitir resultado estructurado en JSON.")
    args = parser.parse_args(argv)

    try:
        if args.dir is not None:
            ok, errores, resumen = verificar_directorio(args.dir)
        else:
            if args.archivo is not None:
                datos = json.loads(args.archivo.read_text(encoding="utf-8"))
            else:
                datos = _cargar_json_url(args.url)
            if isinstance(datos, dict):
                lotes = datos.get("lotes", [])
                ya_cron = datos.get("orden") == "asc"
            elif isinstance(datos, list):
                lotes = datos
                ya_cron = False
            else:
                raise ValueError("El JSON debe ser un objeto con clave 'lotes' o una lista de lotes.")
            ok, errores, resumen = verificar_lotes(
                lotes, exigir_genesis=args.desde_genesis, ya_cronologico=ya_cron
            )
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        if args.json:
            print(json.dumps({"ok": False, "errores": [str(exc)], "resumen": {}}, ensure_ascii=False))
        else:
            print(f"ERROR de lectura: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"ok": ok, "errores": errores, "resumen": resumen}, ensure_ascii=False, indent=2))
    else:
        estado = "OK" if ok else "FALLO"
        print(f"{estado}: {resumen.get('total', 0)} lotes verificados ({resumen.get('modo', 'chain')})")
        for err in errores:
            print(f"  ! {err}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
