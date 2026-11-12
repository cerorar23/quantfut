"""Ruta genérica `/{slug}/` (Fase 2 «Web y App», parte C): un deporte del catálogo SIN página SSR propia se sirve
solo como shell de la SPA (`<html data-deporte=...>`), sin SEO propio hasta que exista una plantilla genérica
(Fase 3 o 4): siempre `noindex, follow` y fuera del `sitemap`.

Es una `Route` cuyo `matches` solo acepta el primer segmento si es el `slug` español de un deporte del catálogo con
estado web distinto de `off`. Así no cambia nada para el resto de las rutas: ni responde a rutas desconocidas
(que siguen dando 404 sin la redirección 307 de barra final que provocaría un `/{slug}/` ordinario), ni pisa
`/en/…`, `/pt/…`, `/legal/…`, la API o los estáticos. Se registra la última, después de todo lo demás, en `main.py`.
Los tres deportes actuales tienen rutas SSR registradas antes, así que esta nunca los alcanza.
"""
from __future__ import annotations

import re

from fastapi import Request
from fastapi.responses import HTMLResponse
from starlette.routing import Match, Route

from ..comercial import catalogo
from . import rutas_web

_RUTA = re.compile(r"^/([^/]+)/$")


def _deporte_de(path: str) -> dict | None:
    m = _RUTA.match(path)
    if not m:
        return None
    for d in catalogo.deportes_para("web"):          # ya sin los `off`
        if d["slug"].get("es") == m.group(1):
            return d
    return None


def _responder(request: Request) -> HTMLResponse:
    d = _deporte_de(request.url.path)
    if d is None:
        from fastapi import HTTPException
        raise HTTPException(404, "No encontrado")
    nombre = d["nombre"]["es"]
    cab = {"Cache-Control": "no-cache, must-revalidate", "X-Robots-Tag": "noindex"}
    cuerpo = rutas_web.render_pagina(
        titulo=nombre, descripcion=f"{nombre}: probabilidades y estadísticas en QuantFut.",
        path=request.url.path, ruta="partidos", jsonld=[],
        principal=f"<h1>{nombre}</h1>", datos={"deporte": d["id"]}, robots="noindex, follow")
    return HTMLResponse(cuerpo, headers=cab)


class RutaDeporteGenerico(Route):
    def matches(self, scope):
        if scope["type"] == "http" and _deporte_de(scope["path"]) is None:
            return Match.NONE, {}
        return super().matches(scope)


def registrar(app) -> None:
    """Añade la ruta al final de la tabla de rutas de `app` (después del montaje de `/static`)."""
    app.router.routes.append(RutaDeporteGenerico("/{slug}/", _responder, methods=["GET", "HEAD"], name="deporte_generico"))
