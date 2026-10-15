"""Compras de suscripción en Google Play y App Store (db/071).

La app manda el token (Play) o el JWS (Apple); el servidor verifica con la tienda y
concede. Las notificaciones de la tienda solo despiertan: se vuelve a consultar a la
tienda antes de actuar. Apagado por defecto (STORE_PURCHASES_ENABLED=1 para abrir).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from . import cuentas as api
from ..comercial import suscripciones
from ..comercial.tiendas import TiendaError, app_store, compras, google_play

log = logging.getLogger(__name__)
_REVOCADA = 12  # SUBSCRIPTION_REVOKED en RTDN


def require_store() -> None:
    if os.getenv("STORE_PURCHASES_ENABLED", "0") != "1":
        raise HTTPException(503, {"code": "compras_deshabilitadas",
                                  "message": "Las compras todavía no están disponibles"})


router = APIRouter(prefix="/app/v1/compras", tags=["app"],
                   dependencies=[Depends(api.require_enabled), Depends(require_store)])
# Llamadas de las tiendas: sin sesión de cuenta, autenticadas por firma/OIDC.
store_router = APIRouter(prefix="/app/v1/compras", include_in_schema=False,
                         dependencies=[Depends(require_store)])


class VerificarIn(BaseModel):
    store: Literal["google_play", "app_store"]
    product_id: str = Field(min_length=1, max_length=100)
    purchase_token: str | None = Field(default=None, max_length=4096)
    jws: str | None = Field(default=None, max_length=16384)


class VerificarOut(BaseModel):
    estado: Literal["concedido", "pendiente", "sin_acceso"]
    plus: bool
    ends_at: datetime | None


def _tienda_error(e: TiendaError):
    status = 503 if e.code == "tienda_no_configurada" else 409
    raise HTTPException(status, {"code": e.code, "message": e.message})


def _no_disponible(exc: Exception):
    log.warning("tienda no disponible: %s", type(exc).__name__)
    raise HTTPException(503, {"code": "tienda_no_disponible",
                              "message": "La tienda no está disponible. Inténtalo de nuevo"})


@router.post("/verificar", response_model=VerificarOut)
def verificar(body: VerificarIn, request: Request, acc: dict = Depends(api.current_account)):
    api._limit(request, "compras_verificar", 30, 300)
    try:
        if body.store == "google_play":
            if not body.purchase_token:
                raise HTTPException(422, "Falta el token de compra")
            data = google_play.fetch(body.purchase_token)
            cobro = google_play.parse(body.purchase_token, data)
        else:
            if not body.jws:
                raise HTTPException(422, "Falta la transacción firmada")
            cobro = app_store.verify_transaction(body.jws)
        result = compras.aplicar(cobro, acc["account_id"])
        if (body.store == "google_play" and result["estado"] == "concedido"
                and cobro.payload.get("acknowledgementState") != "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"):
            google_play.acknowledge(cobro.product_id, body.purchase_token)
    except TiendaError as e:
        _tienda_error(e)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — red o tienda caída: la app reintentará
        _no_disponible(exc)
    plus = suscripciones.active_subscription(acc["account_id"]) is not None
    return VerificarOut(estado=result["estado"], plus=plus, ends_at=result["ends_at"])


@store_router.post("/google/rtdn", status_code=204)
def google_rtdn(envelope: dict, request: Request):
    # Síncrona a propósito: consulta a Play y a la BD con llamadas bloqueantes; FastAPI la
    # ejecuta en su grupo de hilos sin bloquear el bucle de eventos.
    try:
        google_play.verify_push(request.headers.get("authorization"))
    except TiendaError:
        raise HTTPException(401, "No autenticado") from None
    try:
        note = json.loads(base64.b64decode(envelope["message"]["data"]))
    except (KeyError, ValueError, TypeError):
        return Response(status_code=204)          # mensaje mal formado: no reintentar
    try:
        if voided := note.get("voidedPurchaseNotification"):
            compras.revocar_orden("google_play", voided["orderId"], "Reembolso o anulación en Google Play")
        elif sub := note.get("subscriptionNotification"):
            token = sub["purchaseToken"]
            if sub.get("notificationType") == _REVOCADA:
                compras.revocar_original("google_play", token, "Suscripción revocada en Google Play")
            else:
                data = google_play.fetch(token)
                cobro = google_play.parse(token, data)
                result = compras.aplicar(cobro, None)
                if (result["estado"] == "concedido" and
                        data.get("acknowledgementState") != "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"):
                    google_play.acknowledge(cobro.product_id, token)
    except TiendaError as e:
        log.warning("RTDN descartada: %s", e.code)   # cuenta o producto desconocido: no reintentar
    except Exception as exc:  # noqa: BLE001 — Pub/Sub reintenta ante 5xx
        _no_disponible(exc)
    return Response(status_code=204)


class AppleIn(BaseModel):
    signedPayload: str = Field(min_length=1, max_length=65536)


@store_router.post("/apple/notificaciones", status_code=204)
def apple_notificaciones(body: AppleIn):
    try:
        kind, cobro, transaction_id = app_store.verify_notification(body.signedPayload)
        if cobro is not None:
            compras.aplicar(cobro, None)
        elif kind in ("REFUND", "REVOKE") and transaction_id:
            compras.revocar_orden("app_store", transaction_id, f"{kind} en App Store")
    except TiendaError as e:
        if e.code == "compra_no_valida":
            raise HTTPException(401, "Firma no válida") from None
        log.warning("Notificación de Apple descartada: %s", e.code)
    except Exception as exc:  # noqa: BLE001
        _no_disponible(exc)
    return Response(status_code=204)
