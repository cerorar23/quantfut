"""IndexNow (F2.4 de docs/plan_seo_redes_web_20261108.md): avisar a Bing y a los demás buscadores que lo usan de las URLs
nuevas o cambiadas, en vez de esperar a que las rastreen. **Google NO usa IndexNow** (su ayuda es el sitemap y Search Console);
esto no sustituye al sitemap, lo acompaña.

Dos piezas:

1. La ruta `/<clave>.txt`: el protocolo exige que el sitio demuestre que es suyo sirviendo la clave en un archivo con su nombre.
   La clave no es un secreto (es pública por diseño); vive en `<INDEXNOW_DIR>/clave.txt` (por defecto
   `/srv/quantfut/artifacts/indexnow`), no en una variable de entorno, porque el contenedor no se puede recrear para cambiarla.
2. El envío (`python -m qf.api.indexnow --enviar`): lee el sitemap que ven los buscadores, lo compara con lo ya enviado
   (`estado.json` en el mismo directorio) y manda por lotes SOLO lo nuevo o lo que cambió. Sin `--enviar` solo simula.
   Se lanza desde el cron del host: `docker exec quantfut-api-1 python -m qf.api.indexnow --enviar`.

Qué cuenta como «cambió»: la URL es nueva; su `lastmod` del sitemap cambió (un partido deja de llevarlo al terminar: pasa de la
previa al resultado); o es un pilar (`/nba/`, `/futbol/`, `/tenis/`) y han pasado 6 horas desde el último aviso. Lo que ya se
envió y no cambió no se vuelve a enviar (IndexNow lo desaconseja). Un envío fallido no se da por hecho y se reintenta.

Solo se envían URLs del propio sitio y del sitemap público; nunca nada con sesión, VIP ni API.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

log = logging.getLogger("qf.indexnow")
router = APIRouter(include_in_schema=False)

ENDPOINT = "https://api.indexnow.org/IndexNow"
CLAVE_RE = re.compile(r"^[A-Za-z0-9-]{8,128}$")        # el protocolo admite 8-128 caracteres alfanuméricos y guiones
PILARES = ("/nba/", "/futbol/", "/tenis/")
REENVIO_PILARES = timedelta(hours=6)
LOTE = 500
OLVIDAR_TRAS = timedelta(days=30)
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def directorio() -> Path:
    return Path(os.environ.get("INDEXNOW_DIR", "/srv/quantfut/artifacts/indexnow"))


def host() -> str:
    return os.environ.get("DOMAIN", "pronosticosdeportivos.pro").strip().lower()


def leer_clave() -> str | None:
    try:
        clave = (directorio() / "clave.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return clave if CLAVE_RE.match(clave) else None


# --- la ruta de la clave ---------------------------------------------------------------------------

@router.get("/{nombre}.txt", name="indexnow_clave")
def clave_txt(nombre: str):
    """Sirve la clave solo en `/<clave>.txt`; cualquier otro `.txt` que no exista es 404 (robots.txt va antes en el orden)."""
    clave = leer_clave()
    if not clave or nombre != clave:
        raise HTTPException(404)
    return PlainTextResponse(clave, headers={"Cache-Control": "public, max-age=3600", "X-Robots-Tag": "noindex"})


# --- qué enviar ----------------------------------------------------------------------------------

def leer_sitemap(xml: str) -> dict[str, str | None]:
    """{url: lastmod o None} del sitemap público."""
    salida = {}
    for u in ET.fromstring(xml).findall("s:url", NS):
        loc = u.find("s:loc", NS)
        mod = u.find("s:lastmod", NS)
        if loc is not None and loc.text:
            salida[loc.text.strip()] = mod.text.strip() if mod is not None and mod.text else None
    return salida


def _es_pilar(url: str, dominio: str) -> bool:
    return any(url == f"https://{dominio}{p}" for p in PILARES)


def planificar(previo: dict[str, dict], actual: dict[str, str | None], ahora: datetime, dominio: str) -> list[str]:
    """URLs que hay que avisar ahora. Solo del propio dominio y con https."""
    nuevas = []
    for url, lastmod in actual.items():
        if not url.startswith(f"https://{dominio}/"):
            continue
        antes = previo.get(url)
        if antes is None or antes.get("lastmod") != lastmod:
            nuevas.append(url)
        elif _es_pilar(url, dominio):
            try:
                ultimo = datetime.fromisoformat(antes["enviada"])
            except (KeyError, ValueError):
                ultimo = None
            if ultimo is None or ahora - ultimo >= REENVIO_PILARES:
                nuevas.append(url)
    return nuevas


def _fecha(entrada: dict, defecto: datetime) -> datetime:
    try:
        return datetime.fromisoformat(entrada["enviada"])
    except (KeyError, ValueError, TypeError):
        return defecto


def cargar_estado() -> dict[str, dict]:
    try:
        datos = json.loads((directorio() / "estado.json").read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_estado(estado: dict[str, dict]) -> None:
    d = directorio()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f".estado.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(estado, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    for intento in range(4):
        try:
            os.replace(tmp, d / "estado.json")
            return
        except PermissionError:          # Windows: un antivirus puede tener el archivo abierto un instante
            if intento == 3:
                raise
            time.sleep(0.2)


# --- red ------------------------------------------------------------------------------------------

def _get(url: str, cabeceras: dict[str, str]) -> str:
    req = urllib.request.Request(url, headers=cabeceras)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8")


def _post(url: str, cuerpo: dict) -> int:
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "QuantFut-IndexNow/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def enviar_lote(urls: list[str], dominio: str, clave: str, post=_post) -> int:
    return post(ENDPOINT, {"host": dominio, "key": clave, "keyLocation": f"https://{dominio}/{clave}.txt", "urlList": urls})


# --- ejecución ------------------------------------------------------------------------------------

def ejecutar(enviar: bool = False, ahora: datetime | None = None, leer=None, post=_post, dominio: str | None = None) -> dict:
    """Un pase: lee el sitemap, decide qué avisar y (solo con `enviar`) lo manda por lotes. Devuelve un resumen."""
    ahora = ahora or datetime.now(timezone.utc)
    dominio = dominio or host()
    clave = leer_clave()
    resumen = {"clave": bool(clave), "sitemap": 0, "pendientes": 0, "enviadas": 0, "fallidas": 0, "simulado": not enviar, "lotes": []}
    if not clave:
        resumen["error"] = "sin clave en clave.txt: no se envía nada"
        return resumen
    if leer is None:
        base = os.environ.get("INDEXNOW_SITEMAP", "http://127.0.0.1:8000/sitemap-paginas.xml")
        leer = lambda: _get(base, {"Host": dominio, "User-Agent": "QuantFut-IndexNow/1"})   # noqa: E731
    try:
        actual = leer_sitemap(leer())
    except (OSError, ET.ParseError, ValueError) as e:
        resumen["error"] = f"sitemap no disponible: {e}"
        return resumen
    estado = cargar_estado()
    pendientes = planificar(estado, actual, ahora, dominio)
    resumen.update(sitemap=len(actual), pendientes=len(pendientes))
    if not enviar:
        resumen["muestra"] = pendientes[:10]
        return resumen
    for i in range(0, len(pendientes), LOTE):
        lote = pendientes[i:i + LOTE]
        codigo = enviar_lote(lote, dominio, clave, post)
        resumen["lotes"].append(codigo)
        if codigo in (200, 202):
            resumen["enviadas"] += len(lote)
            for url in lote:
                estado[url] = {"lastmod": actual[url], "enviada": ahora.isoformat()}
        else:
            resumen["fallidas"] += len(lote)
            if codigo == 429:               # demasiadas peticiones: se para y se reintenta en el siguiente pase
                break
    for url in [u for u, v in estado.items() if u not in actual and ahora - _fecha(v, ahora) > OLVIDAR_TRAS]:
        estado.pop(url)
    guardar_estado(estado)
    return resumen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Avisa a IndexNow (Bing y otros) de las URLs nuevas o cambiadas del sitemap.")
    ap.add_argument("--enviar", action="store_true", help="envía de verdad; sin esto solo simula y no escribe nada")
    args = ap.parse_args(argv)
    res = ejecutar(enviar=args.enviar)
    print(json.dumps(res, ensure_ascii=False))
    return 1 if res.get("error") or res.get("fallidas") else 0


if __name__ == "__main__":
    sys.exit(main())
