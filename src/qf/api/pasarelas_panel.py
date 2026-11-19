"""`/control/pasarelas`: claves de Whop (producción y sandbox), planes de prueba y cuentas autorizadas (db/117).

Las claves se escriben aquí, nunca en el chat ni en el navegador de los clientes: viajan por POST con CSRF, se
cifran en reposo y la página solo muestra los últimos 4 caracteres.
"""
from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import console, panel
from ..comercial import cifrado, pasarelas
from ..db import conn

router = APIRouter(prefix="/control", include_in_schema=False)

MENSAJES = {
    "guardado": ("success", "Claves guardadas."),
    "sin_cambios": ("info", "No escribiste nada: se conservan las claves actuales."),
    "cuenta_ok": ("success", "Cuenta de prueba añadida."),
    "cuenta_baja": ("success", "Cuenta de prueba quitada."),
    "plan_ok": ("success", "Plan de prueba guardado."),
}


def _volver(codigo: str = "", error: str = "") -> RedirectResponse:
    q = urlencode({"e": error} if error else {"m": codigo})
    return RedirectResponse(f"/control/pasarelas?{q}", status_code=303)


@router.get("/pasarelas", response_class=HTMLResponse)
def pasarelas_page(request: Request, user: str = Depends(console.require_console)):
    with conn() as c:
        planes = c.execute("SELECT plan_code, name, whop_plan_id, whop_plan_id_sandbox FROM plans "
                           "ORDER BY price_cents").fetchall()
    host = request.headers.get("host", "")
    msg = MENSAJES.get(request.query_params.get("m", ""))
    return panel._render(
        request, "pasarelas.html", user, "pasarelas",
        modos=[pasarelas.estado("live"), pasarelas.estado("sandbox")], planes=planes,
        cuentas=pasarelas.cuentas_prueba(), clave_maestra=cifrado.disponible(),
        urls={"live": f"https://{host}/webhooks/whop", "sandbox": f"https://{host}/webhooks/whop-sandbox"},
        aviso=msg, error=request.query_params.get("e", "")[:200])


@router.post("/pasarelas/{modo}")
def guardar(request: Request, modo: str, csrf: str = Form(""), api_key: str = Form("", max_length=300),
            webhook_secret: str = Form("", max_length=300), account_id: str = Form("", max_length=60),
            user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    try:
        cambiados = pasarelas.guardar(modo, panel._actor(request, user), api_key=api_key,
                                      webhook_secret=webhook_secret, account_id=account_id)
    except pasarelas.PasarelaError as e:
        return _volver(error=e.message)
    return _volver("guardado" if cambiados else "sin_cambios")


@router.post("/pasarelas-cuentas")
def cuenta_alta(request: Request, csrf: str = Form(""), email: str = Form("", max_length=254),
                user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    try:
        pasarelas.agregar_cuenta_prueba(email, panel._actor(request, user))
    except pasarelas.PasarelaError as e:
        return _volver(error=e.message)
    return _volver("cuenta_ok")


@router.post("/pasarelas-cuentas/{account_id}/quitar")
def cuenta_baja(request: Request, account_id: int, csrf: str = Form(""),
                user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    pasarelas.quitar_cuenta_prueba(account_id, panel._actor(request, user))
    return _volver("cuenta_baja")


@router.post("/pasarelas-planes/{plan_code}")
def plan_sandbox(request: Request, plan_code: str, csrf: str = Form(""),
                 plan_id: str = Form("", max_length=80), user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    try:
        pasarelas.plan_sandbox(plan_code, plan_id, panel._actor(request, user))
    except pasarelas.PasarelaError as e:
        return _volver(error=e.message)
    return _volver("plan_ok")
