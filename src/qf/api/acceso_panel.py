"""`/control/acceso`: reglas de «alta probabilidad» (rango y fracción gratis) y días de agenda.

Las reglas solo valen desde mañana (UTC) y nunca se editan: corregir una que aún no
entró en vigor es añadir otra con la misma fecha (gana la última). Ver db/111.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from psycopg import errors as pgerr

from . import console, panel
from ..comercial import acceso_reglas

router = APIRouter(prefix="/control", include_in_schema=False)


def _error(texto: str) -> RedirectResponse:
    query = urlencode({"m": "acceso_error", "err": (texto or "Datos no válidos.")[:240]})
    return RedirectResponse(f"/control/acceso?{query}", status_code=303)


def _fraccion(texto: str) -> str:
    """El formulario habla en porcentajes; la base guarda fracciones (73 -> 0.73)."""
    return str(round(float(texto.replace(",", ".")) / 100, 4))


@router.get("/acceso", response_class=HTMLResponse)
def acceso_page(request: Request, user: str = Depends(console.require_console)):
    acceso_reglas.invalidar_cache()
    hoy = acceso_reglas.hoy_utc()
    reglas = acceso_reglas.todas()
    en_vigor = acceso_reglas.vigente(hoy)
    return panel._render(
        request, "acceso.html", user, "acceso", en_vigor=en_vigor,
        futuras=[r for r in reglas if r.vigente_desde > hoy],
        historial=[r for r in reversed(reglas) if r.vigente_desde <= hoy],
        manana=acceso_reglas.manana_utc().isoformat(), dias_agenda=acceso_reglas.dias_agenda(),
        err=request.query_params.get("err", ""))


@router.post("/acceso/regla")
def acceso_regla(request: Request, csrf: str = Form(""), prob_min: str = Form("", max_length=8),
                 prob_max: str = Form("", max_length=8), free_pct: str = Form("", max_length=8),
                 vigente_desde: str = Form("", max_length=10), nota: str = Form("", max_length=500),
                 user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    try:
        acceso_reglas.crear(_fraccion(prob_min), _fraccion(prob_max), _fraccion(free_pct),
                            date.fromisoformat(vigente_desde), nota, panel._actor(request, user))
    except (ValueError, pgerr.CheckViolation, pgerr.RaiseException) as exc:
        return _error(str(exc))
    return panel._back("/control/acceso", "acceso_guardado")


@router.post("/acceso/agenda")
def acceso_agenda(request: Request, csrf: str = Form(""), dias: int = Form(7),
                  user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    try:
        acceso_reglas.guardar_dias_agenda(dias, panel._actor(request, user))
    except ValueError as exc:
        return _error(str(exc))
    return panel._back("/control/acceso", "acceso_agenda_guardada")
