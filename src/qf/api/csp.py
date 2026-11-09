"""CSP en MODO INFORME (F5 de docs/plan_seo_redes_web_20261108.md §10): el navegador avisa de lo que bloquearía una política de
seguridad de contenido, pero no bloquea nada. Sirve para aprender qué carga de verdad la web (Pixel de Meta, Cloudflare Insights,
Firebase/Google, Whop…) antes de aplicarla: una CSP aplicada a ciegas rompería el pago o el acceso con Google.

- Cabecera `Content-Security-Policy-Report-Only` en las páginas HTML públicas (no en JSON, imágenes, panel ni páginas que ya llevan
  su propia CSP). `Reporting-Endpoints` + `report-uri` apuntan a `/csp-report`.
- `POST /csp-report`: recibe los dos formatos (`application/csp-report` de `report-uri` y `application/reports+json` de `report-to`),
  guarda solo lo necesario —fecha, directiva, HOST bloqueado, ruta del documento SIN consulta, tipo de disposición— en
  `<CSP_DIR>/informes.jsonl` y devuelve 204. No guarda IP, `User-Agent`, cuerpo completo ni URLs completas (pueden llevar tokens).
  Está acotado: cuerpo ≤ 8 KB, ≤ 400 líneas por hora y proceso, archivo ≤ 5 MB. Cualquiera puede enviarle basura: por eso no confía en nada.
- Resumen para decidir: `python -m qf.api.csp` (cuenta por directiva y host).

La política se endurecerá y se APLICARÁ en una fase posterior, con los informes de una semana real a la vista.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, Response

router = APIRouter(include_in_schema=False)

RUTA_INFORMES = "/csp-report"
MAX_CUERPO = 8 * 1024
MAX_POR_HORA = 400
MAX_ARCHIVO = 5 * 1024 * 1024
EXCLUIDAS = ("/control", "/admin", "/static", "/vendor", "/web/", "/app/", "/mobile/", "/nba/v", "/tenis/v2", "/v1", "/csp-report",
             "/rewards", "/webhooks", "/i/")

POLITICA = "; ".join([
    "default-src 'self'",
    # Scripts: la propia web (módulos ES), el Pixel de Meta, el beacon de Cloudflare Insights, el SDK de Firebase (acceso con Google) y Whop.
    "script-src 'self' https://connect.facebook.net https://static.cloudflareinsights.com https://www.gstatic.com https://cdn.whop.com https://apis.google.com",
    "style-src 'self' 'unsafe-inline' https://cdn.whop.com",     # la app pinta `style=` en línea y el HTML inicial lleva <style>
    "img-src 'self' data: blob: https://www.facebook.com https://*.whop.com https://lh3.googleusercontent.com",
    "font-src 'self' data: https://cdn.whop.com",
    "connect-src 'self' https://www.facebook.com https://connect.facebook.net https://cloudflareinsights.com https://*.googleapis.com https://*.whop.com",
    "frame-src https://accounts.google.com https://*.firebaseapp.com https://*.whop.com https://whop.com",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    f"report-uri {RUTA_INFORMES}",
    "report-to csp",
])


def aplica(request: Request, response: Response) -> bool:
    """¿Lleva esta respuesta la política en modo informe? Solo HTML público que aún no trae su propia CSP."""
    if request.method not in ("GET", "HEAD") or response.status_code >= 500:
        return False
    if any(request.url.path.startswith(p) for p in EXCLUIDAS):
        return False
    if "text/html" not in response.headers.get("content-type", "").lower():
        return False
    return not any(h in response.headers for h in ("content-security-policy", "content-security-policy-report-only"))


def aplicar_cabeceras(request: Request, response: Response) -> None:
    if aplica(request, response):
        response.headers["Content-Security-Policy-Report-Only"] = POLITICA
        response.headers["Reporting-Endpoints"] = f'csp="{RUTA_INFORMES}"'


# --- receptor -------------------------------------------------------------------------------------

_ventana = {"inicio": 0.0, "n": 0}


def directorio() -> Path:
    for base in (os.environ.get("CSP_DIR", "/srv/quantfut/artifacts/csp"), str(Path(tempfile.gettempdir()) / "qf_csp")):
        p = Path(base)
        try:
            p.mkdir(parents=True, exist_ok=True)
            if os.access(p, os.W_OK):
                return p
        except OSError:
            continue
    raise OSError("sin directorio de escritura para los informes CSP")


def _host(uri: object) -> str:
    """Solo el host (o la palabra clave: inline, eval, data, blob, self…); nunca la URL completa."""
    texto = str(uri or "")[:300]
    if not texto:
        return "(vacío)"
    esquema = texto.split(":", 1)[0].lower()
    if esquema in ("blob", "data", "filesystem", "about", "mediastream"):
        return esquema                         # `blob:https://x.com/uuid` no es un host: es un blob
    if "://" not in texto:
        return texto.split(":")[0][:30] or "(vacío)"
    return (urlsplit(texto).hostname or "(sin host)")[:80]


def _ruta(uri: object) -> str:
    try:
        return (urlsplit(str(uri or "")[:300]).path or "/")[:120]
    except ValueError:
        return "/"


def normalizar(cuerpo: object) -> list[dict]:
    """Extrae informes de los dos formatos. Devuelve filas ya saneadas; lo que no se entiende se descarta."""
    crudos: list[dict] = []
    if isinstance(cuerpo, dict) and isinstance(cuerpo.get("csp-report"), dict):
        crudos.append(cuerpo["csp-report"])
    elif isinstance(cuerpo, list):
        crudos += [x.get("body") for x in cuerpo if isinstance(x, dict) and x.get("type") == "csp-violation" and isinstance(x.get("body"), dict)]
    filas = []
    for c in crudos[:20]:
        directiva = str(c.get("effective-directive") or c.get("effectiveDirective") or c.get("violated-directive") or c.get("violatedDirective") or "")[:60]
        if not directiva:
            continue
        filas.append({
            "t": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "directiva": directiva.split(" ")[0],
            "bloqueado": _host(c.get("blocked-uri") or c.get("blockedURL") or c.get("blockedUri")),
            "ruta": _ruta(c.get("document-uri") or c.get("documentURL") or c.get("documentUri")),
            "disposicion": str(c.get("disposition") or "report")[:10],
        })
    return filas


def _cabe_en_la_hora(n: int) -> bool:
    ahora = time.monotonic()
    if ahora - _ventana["inicio"] > 3600:
        _ventana.update(inicio=ahora, n=0)
    if _ventana["n"] + n > MAX_POR_HORA:
        return False
    _ventana["n"] += n
    return True


def guardar(filas: list[dict]) -> int:
    if not filas or not _cabe_en_la_hora(len(filas)):
        return 0
    try:
        archivo = directorio() / "informes.jsonl"
        if archivo.exists() and archivo.stat().st_size > MAX_ARCHIVO:
            return 0
        with archivo.open("a", encoding="utf-8") as f:
            for fila in filas:
                f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    except OSError:
        return 0
    return len(filas)


@router.post(RUTA_INFORMES, name="csp_informes")
async def recibir(request: Request):
    declarado = request.headers.get("content-length")
    if declarado and declarado.isdigit() and int(declarado) > MAX_CUERPO:
        return Response(status_code=413)
    crudo = await request.body()
    if len(crudo) > MAX_CUERPO:
        return Response(status_code=413)
    try:
        cuerpo = json.loads(crudo.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return Response(status_code=204)      # basura: se descarta sin ruido
    guardar(normalizar(cuerpo))
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


# --- resumen --------------------------------------------------------------------------------------

def resumen(archivo: Path | None = None, tope: int = 40) -> list[tuple[int, str, str, str]]:
    """[(veces, directiva, host bloqueado, ruta más frecuente)] de mayor a menor."""
    archivo = archivo or directorio() / "informes.jsonl"
    cuentas: Counter = Counter()
    rutas: dict[tuple, Counter] = {}
    try:
        lineas = archivo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for linea in lineas:
        try:
            f = json.loads(linea)
        except ValueError:
            continue
        clave = (f.get("directiva", "?"), f.get("bloqueado", "?"))
        cuentas[clave] += 1
        rutas.setdefault(clave, Counter())[f.get("ruta", "/")] += 1
    return [(n, d, b, rutas[(d, b)].most_common(1)[0][0]) for (d, b), n in cuentas.most_common(tope)]


def main() -> int:
    filas = resumen()
    if not filas:
        print("sin informes")
        return 0
    for n, directiva, bloqueado, ruta in filas:
        print(f"{n:6d}  {directiva:<16} {bloqueado:<40} p. ej. {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
