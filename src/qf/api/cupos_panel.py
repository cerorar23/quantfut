"""`/control/cupos`: cuántos pronósticos gratis ve quien no tiene VIP, por deporte y por cliente (db/116).

Efecto inmediato (caché de 30 s) y sin tocar nada sellado; ver `comercial/acceso_cupos.py`.
"""
from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import console, panel
from ..comercial import acceso_cupos, catalogo

router = APIRouter(prefix="/control", include_in_schema=False)

CLIENTES = (("web", "Web"), ("app", "App"))


def _deportes() -> list[dict]:
    return [{"id": d["deporte_id"], "nombre": (d.get("nombre") or {}).get("es") or d["deporte_id"]}
            for d in catalogo.todos()]


@router.get("/cupos", response_class=HTMLResponse)
def cupos_page(request: Request, user: str = Depends(console.require_console)):
    acceso_cupos.invalidar_cache()
    filas = [{**d, "clientes": [
        {"id": c, "nombre": nombre, "cupo": acceso_cupos.cupo(d["id"], c),
         "sin_destacado": (d["id"], c, "destacados_gratis_dia") in acceso_cupos.NO_APLICA}
        for c, nombre in CLIENTES]} for d in _deportes()]
    return panel._render(request, "cupos.html", user, "cupos", deportes=filas, maximo=acceso_cupos.MAXIMO,
                         err=request.query_params.get("err", ""))


@router.post("/cupos/{deporte_id}/{cliente}")
def cupos_guardar(request: Request, deporte_id: str, cliente: str, csrf: str = Form(""),
                  destacados: str = Form("", max_length=4), mercados: str = Form("", max_length=4),
                  user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    if deporte_id not in {d["id"] for d in _deportes()}:
        raise HTTPException(404, "Deporte no encontrado")
    try:
        acceso_cupos.guardar(deporte_id, cliente, destacados, mercados, panel._actor(request, user))
    except ValueError as exc:
        query = urlencode({"m": "acceso_error", "err": str(exc)[:240]})
        return RedirectResponse(f"/control/cupos?{query}", status_code=303)
    return panel._back("/control/cupos", "cupos_guardados")
