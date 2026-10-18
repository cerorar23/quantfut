"""Cobro web con Whop: crea el checkout (con sesión) y recibe los webhooks (con firma)."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import cuentas as api, ratelimit
from ..comercial import whop

router = APIRouter(prefix="/app/v1/whop", tags=["whop"], dependencies=[Depends(api.require_enabled)])
webhooks = APIRouter(tags=["whop"], include_in_schema=False)


@router.get("/config")
def config():
    """Lo único que el navegador necesita saber: si hay pago en línea y qué Pixel de Meta cargar (público)."""
    return {"enabled": whop.enabled(), "pixelId": os.getenv("META_PIXEL_ID") or None}


class CheckoutIn(BaseModel):
    plan_code: str = Field(min_length=1, max_length=40)
    fbp: str | None = Field(default=None, max_length=200)
    fbc: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None, max_length=1000)


@router.post("/checkout")
def checkout(body: CheckoutIn, request: Request, account: dict = Depends(api.current_account)):
    api._limit(request, "whop_checkout", 20, 300)
    try:
        return whop.create_checkout(
            account, body.plan_code, fbp=body.fbp or request.cookies.get('_fbp'),
            fbc=body.fbc or request.cookies.get('_fbc'),
            client_ip=ratelimit.client_ip(request), user_agent=request.headers.get("user-agent"),
            source_url=body.source_url)
    except whop.WhopError as error:
        status = {"pagos_deshabilitados": 503, "whop_no_disponible": 502}.get(error.code, 409)
        raise HTTPException(status, {"code": error.code, "message": error.message}) from None


@webhooks.post("/webhooks/whop")
async def receive(request: Request):
    secret = os.getenv("WHOP_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(503, {"code": "pagos_deshabilitados", "message": "Webhook no configurado"})
    body = await request.body()
    try:
        whop.verify_signature(secret, {k.lower(): v for k, v in request.headers.items()}, body)
        event = whop.parse(body)
    except whop.WhopError as error:
        raise HTTPException(400, {"code": error.code, "message": error.message}) from None
    # Un fallo aquí devuelve 500 y Whop reintenta (el webhook-id solo se registra si todo salió bien).
    result = whop.handle_event(request.headers["webhook-id"], event)
    return {"ok": True, **{k: v for k, v in result.items() if k == "estado"}}
