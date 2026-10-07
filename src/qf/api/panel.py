"""Panel de administración `/control`: dashboard, clientes, suscripciones,
planes, auditoría y la vista de sistema.

Detrás de Cloudflare Access (Caddy) y de la autenticación propia de
`console.require_console`. Lo comercial se puede modificar desde aquí,
siempre auditado; el pipeline de predicción NO: el panel no lanza jobs, no
publica picks ni toca modelos.

UI: Tabler + Tabler Icons + Chart.js, servidos desde `/static/vendor`
(ver su README). Sin scripts en línea: la CSP solo admite `'self'`.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from . import console
from ..comercial import correo, cuentas, metricas, suscripciones
from ..comercial.auditoria import audit
from ..comercial.cuentas import CuentaError
from ..config import settings
from ..db import conn

_log = logging.getLogger(__name__)
_DIR = Path(__file__).resolve().parent
router = APIRouter(prefix="/control", include_in_schema=False)

CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")


def _load_icons() -> dict[str, Markup]:
    icons = {}
    for f in (_DIR / "static" / "vendor" / "icons").glob("*.svg"):
        svg = f.read_text(encoding="utf-8")
        icons[f.stem] = Markup(svg.replace("<svg", '<svg aria-hidden="true"', 1))
    return icons


_ICONS = _load_icons()


def _icon(name: str) -> Markup:
    return _ICONS.get(name, Markup(""))


def _fecha(value, fmt: str = "%d-%m-%Y %H:%M") -> str:
    if value is None:
        return "—"
    return value.astimezone(timezone.utc).strftime(fmt) if isinstance(value, datetime) else str(value)


def _dinero(cents, currency: str = "USD") -> str:
    if cents is None:
        return "—"
    return f"{Decimal(cents) / 100:,.2f} {currency}".replace(",", " ").replace(".", ",")


def _detalle(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str) if value else ""


ENV = Environment(loader=FileSystemLoader(_DIR / "templates"),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
ENV.globals.update(icon=_icon)
ENV.filters.update(fecha=_fecha, dinero=_dinero, detalle=_detalle)
ENV.policies["json.dumps_kwargs"] = {"sort_keys": True, "default": str}

# Mensajes tras una acción. Solo códigos conocidos: el texto nunca sale de la URL.
_MENSAJES = {
    "concedida": ("success", "Suscripción concedida."),
    "revocada": ("success", "Suscripción revocada."),
    "suspendida": ("success", "Cuenta suspendida y sesiones cerradas."),
    "reactivada": ("success", "Cuenta reactivada."),
    "verificada": ("success", "Correo marcado como verificado."),
    "sesiones": ("success", "Sesiones cerradas."),
    "plan": ("success", "Plan actualizado."),
    "sin_cambios": ("info", "No había nada que cambiar."),
    "precio_invalido": ("danger", "Precio no válido."),
    "motivo_requerido": ("danger", "Indica el motivo de la revocación."),
    "ya_de_por_vida": ("danger", "La cuenta ya tiene acceso de por vida."),
    "plan_inexistente": ("danger", "Ese plan no existe."),
    "correo_enviado": ("success", "Correo enviado."),
    "correo_fallo": ("danger", "No se pudo enviar el correo; revisa los logs y la configuración SMTP."),
    "correo_no_configurado": ("warning", "El envío de correo no está configurado (SMTP_HOST / SMTP_FROM)."),
    "cuenta_suspendida": ("warning", "La cuenta está suspendida: no se envía enlace de acceso."),
}


def csrf_token(user: str) -> str:
    """Basic auth viaja sola en cada petición del navegador: sin este token,
    otra web podría hacer que el operador enviase un formulario."""
    key = os.getenv("ADMIN_CONSOLE_PASSWORD_HASH", "").encode()
    return hmac.new(key, f"csrf:{user}".encode(), hashlib.sha256).hexdigest()


def _check_post(request: Request, user: str, token: str) -> None:
    site = request.headers.get("sec-fetch-site")
    # Con `Referrer-Policy: no-referrer` (main.py) el navegador manda
    # `Origin: null` en los POST propios: ese valor no prueba nada, el token sí.
    origin = request.headers.get("origin")
    if (site and site != "same-origin") or (
            origin and origin != "null" and urlsplit(origin).netloc != request.headers.get("host")):
        raise HTTPException(403, "Origen no permitido")
    if not hmac.compare_digest(token, csrf_token(user)):
        raise HTTPException(403, "Formulario caducado; recarga la página")


def _render(request: Request, template: str, user: str, active: str, **ctx) -> HTMLResponse:
    flash = _MENSAJES.get(request.query_params.get("m", ""))
    html_ = ENV.get_template(template).render(
        user=user, active=active, csrf=csrf_token(user), flash=flash,
        publicacion_activa=settings.publish_picks_enabled, version=settings.model_version,
        now=datetime.now(timezone.utc), correo_ok=correo.configurado(), **ctx)
    return HTMLResponse(html_, headers={"Cache-Control": "no-store", "Content-Security-Policy": CSP})


def _back(path: str, code: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?{urlencode({'m': code})}", status_code=303)


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001 - una tarjeta caída no tumba el dashboard
        _log.exception("Fallo al cargar dato del panel")
        return default


# --- Páginas -----------------------------------------------------------------

@router.get("")
@router.get("/")
def dashboard(request: Request, user: str = Depends(console.require_console)):
    return _render(request, "dashboard.html", user, "dashboard",
                   cuentas=_safe(metricas.cuentas, {}),
                   subs=_safe(metricas.suscripciones, {}),
                   ingresos=_safe(metricas.ingresos_30d, []),
                   op=_safe(metricas.operacion, {}),
                   serie=_safe(metricas.serie_diaria, []),
                   ultimas=_safe(metricas.ultimas_cuentas, []),
                   acciones=_safe(lambda: metricas.auditoria(limit=8), []))


@router.get("/usuarios")
def usuarios(request: Request, user: str = Depends(console.require_console),
             q: str = Query("", max_length=120), filtro: str = "todas",
             page: int = Query(1, ge=1)):
    return _render(request, "usuarios.html", user, "usuarios",
                   lista=metricas.lista_cuentas(q, filtro, page), q=q, filtro=filtro)


@router.get("/usuarios/{account_id}")
def usuario(request: Request, account_id: int, user: str = Depends(console.require_console)):
    acc = metricas.cuenta(account_id)
    if acc is None:
        raise HTTPException(404, "La cuenta no existe")
    return _render(request, "usuario.html", user, "usuarios", acc=acc,
                   historial=suscripciones.history(account_id),
                   sesiones=metricas.sesiones(account_id),
                   planes=suscripciones.plans(),
                   acciones=metricas.auditoria(account_id=account_id, limit=50))


@router.get("/suscripciones")
def lista_suscripciones(request: Request, user: str = Depends(console.require_console),
                        filtro: str = "vigentes", page: int = Query(1, ge=1)):
    return _render(request, "suscripciones.html", user, "suscripciones",
                   lista=metricas.lista_suscripciones(filtro, page), filtro=filtro)


@router.get("/planes")
def planes(request: Request, user: str = Depends(console.require_console)):
    return _render(request, "planes.html", user, "planes", planes=suscripciones.plans())


@router.get("/auditoria")
def auditoria(request: Request, user: str = Depends(console.require_console)):
    return _render(request, "auditoria.html", user, "auditoria", filas=metricas.auditoria())


@router.get("/sistema")
def sistema(request: Request, user: str = Depends(console.require_console)):
    cards = console.snapshot_cards(console._snapshot())
    sombra = console._shadow_table(console._read(console._shadow_picks))
    return _render(request, "sistema.html", user, "sistema",
                   contenido=Markup(sombra + cards))


# --- Acciones (POST → 303, patrón PRG) --------------------------------------

def _actor(request: Request, user: str) -> str:
    # Con Cloudflare Access delante, el correo verificado identifica mejor
    # que el usuario compartido del panel.
    email = request.headers.get("cf-access-authenticated-user-email")
    return f"panel:{user}" + (f" ({email})" if email else "")


@router.post("/usuarios/{account_id}/suscripcion")
def conceder(request: Request, account_id: int, plan_code: str = Form(...),
             nota: str = Form(""), csrf: str = Form(""),
             user: str = Depends(console.require_console)):
    _check_post(request, user, csrf)
    try:
        suscripciones.grant(account_id, plan_code, _actor(request, user), note=nota)
    except CuentaError as e:
        return _back(f"/control/usuarios/{account_id}", e.code)
    return _back(f"/control/usuarios/{account_id}", "concedida")


@router.post("/suscripciones/{subscription_id}/revocar")
def revocar(request: Request, subscription_id: int, motivo: str = Form(""),
            volver: int = Form(0), csrf: str = Form(""),
            user: str = Depends(console.require_console)):
    _check_post(request, user, csrf)
    destino = f"/control/usuarios/{volver}" if volver else "/control/suscripciones"
    try:
        row = suscripciones.revoke(subscription_id, _actor(request, user), motivo)
    except CuentaError as e:
        return _back(destino, e.code)
    return _back(destino, "revocada" if row else "sin_cambios")


@router.post("/usuarios/{account_id}/estado")
def estado(request: Request, account_id: int, status: str = Form(...), csrf: str = Form(""),
           user: str = Depends(console.require_console)):
    _check_post(request, user, csrf)
    if status not in ("active", "suspended"):
        raise HTTPException(422, "Estado no válido")
    changed = cuentas.set_status(account_id, status, _actor(request, user))
    code = ("suspendida" if status == "suspended" else "reactivada") if changed else "sin_cambios"
    return _back(f"/control/usuarios/{account_id}", code)


@router.post("/usuarios/{account_id}/verificar")
def verificar(request: Request, account_id: int, csrf: str = Form(""),
              user: str = Depends(console.require_console)):
    _check_post(request, user, csrf)
    changed = cuentas.mark_email_verified(account_id, _actor(request, user))
    return _back(f"/control/usuarios/{account_id}", "verificada" if changed else "sin_cambios")


@router.post("/usuarios/{account_id}/cerrar-sesiones")
def cerrar_sesiones(request: Request, account_id: int, csrf: str = Form(""),
                    user: str = Depends(console.require_console)):
    _check_post(request, user, csrf)
    cuentas.revoke_all_sessions(account_id, _actor(request, user))
    return _back(f"/control/usuarios/{account_id}", "sesiones")


@router.post("/usuarios/{account_id}/correo")
def enviar_correo(request: Request, account_id: int, tipo: str = Form(...), csrf: str = Form(""),
                  user: str = Depends(console.require_console)):
    _check_post(request, user, csrf)
    destino = f"/control/usuarios/{account_id}"
    acc = metricas.cuenta(account_id)
    if acc is None or tipo not in ("verificar", "restablecer"):
        raise HTTPException(404, "No existe")
    if not correo.configurado():
        return _back(destino, "correo_no_configurado")
    if tipo == "restablecer" and acc["status"] != "active":
        return _back(destino, "cuenta_suspendida")
    enviar = correo.enviar_verificacion if tipo == "verificar" else correo.enviar_restablecimiento
    ok = enviar(account_id, acc["email"])
    with conn() as c:
        audit(c, _actor(request, user), f"correo.{tipo}", account_id, {"enviado": ok})
    return _back(destino, "correo_enviado" if ok else "correo_fallo")


def parse_price(text: str) -> int:
    """'14,99' o '14.99' → 1499 céntimos, sin pasar por float."""
    try:
        value = Decimal((text or "").strip().replace(",", "."))
    except InvalidOperation:
        raise CuentaError("precio_invalido", "Precio no válido") from None
    if not value.is_finite() or value < 0 or value != value.quantize(Decimal("0.01")):
        raise CuentaError("precio_invalido", "Precio no válido")
    return int(value * 100)


@router.post("/planes/{plan_code}")
def editar_plan(request: Request, plan_code: str, precio: str = Form(...),
                activo: str = Form(""), csrf: str = Form(""),
                user: str = Depends(console.require_console)):
    _check_post(request, user, csrf)
    try:
        cents = parse_price(precio)
    except CuentaError as e:
        return _back("/control/planes", e.code)
    ok = suscripciones.update_plan(plan_code, _actor(request, user),
                                   active=activo == "1", price_cents=cents)
    return _back("/control/planes", "plan" if ok else "plan_inexistente")
