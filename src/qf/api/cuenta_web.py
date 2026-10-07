"""Páginas a las que llevan los enlaces de los correos (`/cuenta/*`).

Sirven igual si la persona usa la web o la app Flutter: el enlace se abre en
el navegador. Abrir el enlace (GET) nunca consume el token; solo el botón
(POST). Así los filtros de correo que visitan los enlaces para analizarlos
no gastan ni la verificación ni el restablecimiento.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse

from . import ratelimit
from .cuentas import redis_client, require_enabled
from .panel import CSP, ENV
from ..comercial import cuentas
from ..comercial.cuentas import CuentaError

router = APIRouter(prefix="/cuenta", include_in_schema=False, dependencies=[Depends(require_enabled)])


def _page(template: str, status: int = 200, **ctx) -> HTMLResponse:
    return HTMLResponse(ENV.get_template(template).render(**ctx), status_code=status,
                        headers={"Cache-Control": "no-store", "Content-Security-Policy": CSP})


def _limited(request: Request) -> bool:
    return ratelimit.rate_limited(redis_client(), f"cuenta_web:{ratelimit.client_key(request)}", 20, 60)


@router.get("/verificar")
def verificar_form(token: str = Query("", max_length=200)):
    if not cuentas.email_token_valid(token, "verify"):
        return _page("cuenta/mensaje.html", 400, titulo="Enlace no válido",
                     texto="El enlace ha caducado o ya se usó. Pide uno nuevo desde la app o la web.")
    return _page("cuenta/verificar.html", token=token)


@router.post("/verificar")
def verificar(request: Request, token: str = Form("", max_length=200)):
    if _limited(request) or not cuentas.confirm_email(token):
        return _page("cuenta/mensaje.html", 400, titulo="Enlace no válido",
                     texto="El enlace ha caducado o ya se usó. Pide uno nuevo desde la app o la web.")
    return _page("cuenta/mensaje.html", titulo="Correo confirmado",
                 texto="Listo: tu correo queda verificado. Ya puedes volver a la app.", ok=True)


@router.get("/restablecer")
def restablecer_form(token: str = Query("", max_length=200)):
    if not cuentas.email_token_valid(token, "reset"):
        return _page("cuenta/mensaje.html", 400, titulo="Enlace no válido",
                     texto="El enlace ha caducado o ya se usó. Pide otro desde «¿Olvidaste tu contraseña?».")
    return _page("cuenta/restablecer.html", token=token, minimo=cuentas.PASSWORD_MIN)


@router.post("/restablecer")
def restablecer(request: Request, token: str = Form("", max_length=200),
                password: str = Form("", max_length=cuentas.PASSWORD_MAX),
                password2: str = Form("", max_length=cuentas.PASSWORD_MAX)):
    if _limited(request):
        return _page("cuenta/mensaje.html", 429, titulo="Demasiados intentos",
                     texto="Espera un minuto y vuelve a intentarlo.")
    if password != password2:
        return _page("cuenta/restablecer.html", 422, token=token, minimo=cuentas.PASSWORD_MIN,
                     error="Las dos contraseñas no coinciden.")
    try:
        ok = cuentas.reset_password(token, password)
    except CuentaError as e:
        return _page("cuenta/restablecer.html", 422, token=token, minimo=cuentas.PASSWORD_MIN,
                     error=e.message)
    if not ok:
        return _page("cuenta/mensaje.html", 400, titulo="Enlace no válido",
                     texto="El enlace ha caducado o ya se usó. Pide otro desde «¿Olvidaste tu contraseña?».")
    return _page("cuenta/mensaje.html", titulo="Contraseña cambiada",
                 texto="Tu contraseña es nueva y se cerraron tus sesiones. Inicia sesión otra vez.", ok=True)
