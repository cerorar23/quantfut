"""Transporte de `TennisStateCapture` que contesta `get_fixtures` con SportsAPIPro (SofaScore) en el formato de API-Tennis.

`TennisStateCapture(root, key, daily_limit, transport=...)` llama `transport(url, params=..., timeout=..., allow_redirects=False)`
y lee `.content` y `.status_code`. Este objeto ignora la URL de API-Tennis y sirve el mismo cuerpo desde los calendarios
de SportsAPIPro (`/v2/tennis/schedule/{fecha}`), convertidos con `tenis_formato_api_tennis` y las equivalencias de jugador,
torneo y partido de `tenis_equivalencias`. Cualquier otro método devuelve 501.

SportsAPIPro agrupa por día de Nueva York: para cubrir fechas UTC [d0, d1] hacen falta las fechas NY d0-1..d1 (un partido de
la 01:00 UTC es del día anterior en Nueva York). El refresco de resultados (rango de 2 días) pide solo d0..d1: lo anterior
ya lo cubrió la captura ancha de las 00 y 12 UTC. Un día ya pedido en esta ejecución no se repite (los dos circuitos lo
comparten). Con el User-Agent de urllib Cloudflare responde 403 (error 1010).

Solo biblioteca estándar. En el contenedor de tenis vive junto a `tenis_formato_api_tennis.py` en `tennis_engine/`.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, timedelta

from .tenis_formato_api_tennis import indice, respuesta

API = "https://api.sportsapipro.com/v2/tennis/schedule/%s"
HEADERS = {"User-Agent": "Mozilla/5.0 qf-tenis"}


class Respuesta:
    def __init__(self, status_code: int, content: bytes):
        self.status_code, self.content = status_code, content


class _Fallo(Exception):
    def __init__(self, status, body):
        super().__init__(status)
        self.status, self.body = status, body


def http(url, key, timeout=60):
    req = urllib.request.Request(url, headers={**HEADERS, "x-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class TransporteSportsApiPro:
    def __init__(self, key: str, raiz_equivalencias, call=http):
        self.key, self.call, self.dias = key, call, {}
        self.ix = indice(raiz_equivalencias)
        self.peticiones = 0

    def fechas(self, d0: date, d1: date) -> list[date]:
        ini = d0 if (d1 - d0).days <= 1 else d0 - timedelta(days=1)       # refresco: sin la fecha anterior
        return [ini + timedelta(days=i) for i in range((d1 - ini).days + 1)]

    def dia(self, fecha: date):
        if fecha not in self.dias:
            status, body = self.call(API % fecha.isoformat(), self.key)
            self.peticiones += 1
            if status != 200:
                raise _Fallo(status, body)
            self.dias[fecha] = json.loads(body).get("events") or []
        return self.dias[fecha]

    def __call__(self, url, params=None, timeout=None, allow_redirects=False):
        params = params or {}
        if params.get("method") != "get_fixtures":
            return Respuesta(501, b'{"success": 0, "error": "metodo no soportado por el sustituto"}')
        d0, d1 = date.fromisoformat(params["date_start"]), date.fromisoformat(params["date_stop"])
        try:
            eventos = [e for f in self.fechas(d0, d1) for e in self.dia(f)]
        except _Fallo as exc:
            return Respuesta(exc.status, exc.body)
        return Respuesta(200, respuesta(eventos, self.ix, params["event_type_key"], d0.isoformat(), d1.isoformat()))


class TransporteConRespaldo:
    """API-Tennis primero; si falla (excepción, HTTP distinto de 200 o `success != 1`) responde SportsAPIPro.

    Mientras API-Tennis siga activo la tabla de equivalencias sigue creciendo con sus originales; cuando venza, el
    corte es automático. `fuentes` cuenta qué proveedor contestó cada llamada.
    """

    def __init__(self, primario, respaldo):
        self.primario, self.respaldo, self.fuentes = primario, respaldo, {"api-tennis": 0, "sportsapipro": 0}

    @property
    def peticiones(self):
        return self.respaldo.peticiones

    def __call__(self, url, params=None, timeout=None, allow_redirects=False):
        try:
            r = self.primario(url, params=params, timeout=timeout, allow_redirects=allow_redirects)
            data = json.loads(r.content)
            if r.status_code == 200 and data.get("success") == 1 and isinstance(data.get("result"), list):
                self.fuentes["api-tennis"] += 1
                return r
        except Exception:
            pass
        self.fuentes["sportsapipro"] += 1
        return self.respaldo(url, params=params, timeout=timeout, allow_redirects=allow_redirects)
