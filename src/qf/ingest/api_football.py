"""
Cliente de API-Football (v3) con control de cuota.

Dos cosas que este proveedor hace y que rompen integraciones ingenuas:

1. Devuelve HTTP 200 con `response: []` cuando una liga no tiene cobertura.
   No es un error, es silencio. Por eso `get()` distingue entre "vacío" y
   "fallo" y lo registra en ingest_health.

2. Los errores de plan y de parámetros vienen dentro del cuerpo, en la clave
   `errors`, también con HTTP 200.

La cuota diaria viene en las cabeceras. Se vigila y se alerta antes de
agotarla, porque cuando se acaba el feed se corta sin aviso.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from ..config import settings

log = logging.getLogger(__name__)

BASE = "https://v3.football.api-sports.io"
_last_call = 0.0

# El límite POR MINUTO depende del plan y no viene en ninguna parte hasta que
# lo incumples: el plan Free son 10 req/min y devuelve 429. Un intervalo fijo
# pensado para los planes de pago (0,35 s) agota ese límite en cuatro llamadas
# y tenacity reintenta encima, así que hay que derivarlo del plan.
MIN_INTERVAL = 60.0 / max(settings.api_football_rpm, 1)


class ApiFootballError(RuntimeError):
    pass


class RateLimited(ApiFootballError):
    """429 o `errors.rateLimit`: es el límite por minuto, no un fallo."""


class PlanError(ApiFootballError):
    """La suscripción no cubre lo pedido (p. ej. temporada fuera del plan).

    Es permanente: reintentarlo no lo arregla y cada reintento consume una
    petición de la cuota diaria, que en el plan Free son 100.
    """


def _retryable(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.HTTPError, ApiFootballError)) and not isinstance(exc, PlanError)


class QuotaWarning(RuntimeError):
    pass


@retry(stop=stop_after_attempt(4),
       wait=wait_exponential(multiplier=2, min=2, max=30),
       retry=retry_if_exception(_retryable))
def get(endpoint: str, params: dict[str, Any] | None = None) -> tuple[list, dict]:
    """Devuelve (response, meta). `response` vacío no es error; meta lo indica."""
    global _last_call

    if not settings.api_football_key:
        raise ApiFootballError("API_FOOTBALL_KEY no configurada")

    delta = time.monotonic() - _last_call
    if delta < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - delta)

    with httpx.Client(timeout=30) as c:
        r = c.get(f"{BASE}/{endpoint.lstrip('/')}",
                  headers={"x-apisports-key": settings.api_football_key},
                  params=params or {})
        _last_call = time.monotonic()
        if r.status_code == 429:
            time.sleep(60)
            raise RateLimited(f"{endpoint}: 429, límite por minuto del plan")
        r.raise_for_status()
        data = r.json()

    errors = data.get("errors")
    if errors and (isinstance(errors, dict) and errors or isinstance(errors, list) and errors):
        # El límite por minuto también llega como HTTP 200 con este cuerpo.
        if isinstance(errors, dict) and "rateLimit" in errors:
            time.sleep(60)
            raise RateLimited(f"{endpoint}: {errors['rateLimit']}")
        if isinstance(errors, dict) and "plan" in errors:
            raise PlanError(f"{endpoint}: {errors['plan']}")
        raise ApiFootballError(f"{endpoint}: {errors}")

    meta = {
        "results": data.get("results", 0),
        "quota_remaining": r.headers.get("x-ratelimit-requests-remaining"),
        "quota_limit": r.headers.get("x-ratelimit-requests-limit"),
        "empty": data.get("results", 0) == 0,
    }
    return data.get("response", []), meta


def check_quota(meta: dict, threshold_pct: float = 15.0) -> None:
    """Alerta cuando queda poca cuota diaria. Se llama tras cada lote."""
    rem, lim = meta.get("quota_remaining"), meta.get("quota_limit")
    if not rem or not lim:
        return
    try:
        pct = int(rem) / int(lim) * 100
    except (ValueError, ZeroDivisionError):
        return
    if pct < threshold_pct:
        from ..publish.telegram import alert
        alert(f"Cuota de API-Football al {pct:.0f}% ({rem}/{lim}). "
              "Cuando llegue a cero el feed se corta sin aviso.")


def record_health(source: str, rows: int, ok: bool, detail: dict | None = None) -> None:
    from ..db import execute
    import json
    execute(
        """INSERT INTO ingest_health (source, rows_written, ok, detail)
           VALUES (%s, %s, %s, %s)""",
        (source, rows, ok, json.dumps(detail or {})),
    )


def verify_league_ids() -> list[dict]:
    """
    Comprueba que los api_football_id del seed siguen apuntando a la liga
    correcta. El proveedor los ha cambiado en el pasado; un ID equivocado te
    llena la base con partidos de otra competición sin dar ningún error.
    """
    from ..db import query

    out = []
    for lg in query("SELECT league_id, name, country, api_football_id, cross_league "
                    "FROM leagues WHERE api_football_id IS NOT NULL"):
        try:
            resp, _ = get("leagues", {"id": lg["api_football_id"]})
        except ApiFootballError as exc:
            out.append({**lg, "ok": False, "detail": str(exc)})
            continue
        if not resp:
            out.append({**lg, "ok": False, "detail": "ID inexistente"})
            continue
        remote = resp[0]["league"]["name"]
        country = resp[0]["country"]["name"]
        # Las competiciones cross_league no tienen país: API-Football las
        # archiva bajo "World" mientras el catálogo local dice "Europe".
        # Comparar países ahí da un falso FALLO, así que se comprueba el tipo
        # y el nombre, que es lo que de verdad identifica la competición.
        if lg["cross_league"]:
            ok = (resp[0]["league"]["type"].lower() == "cup"
                  and remote.lower() == lg["name"].lower())
        else:
            ok = (country.lower() == lg["country"].lower())
        out.append({**lg, "ok": ok, "remote_name": remote, "remote_country": country})
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for r in verify_league_ids():
        mark = "OK  " if r.get("ok") else "FALLO"
        print(f"{mark} {r['league_id']:22s} id={r['api_football_id']} "
              f"-> {r.get('remote_name', r.get('detail'))} "
              f"({r.get('remote_country', '')})")
