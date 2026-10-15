"""App Store: transacciones StoreKit 2 y App Store Server Notifications V2, ambas como JWS
que se verifican con la cadena de certificados de Apple (librería oficial). Las raíces
(AppleRootCA-G3.cer…) se descargan de apple.com/certificateauthority y se montan en
APPLE_ROOT_CERTS_DIR."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from . import Cobro, TiendaError

_TIPOS_COBRO = {"SUBSCRIBED", "DID_RENEW"}
_TIPOS_REVOCACION = {"REFUND", "REVOKE"}


def _verifier(environment):
    from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
    folder = os.getenv("APPLE_ROOT_CERTS_DIR", "")
    if not folder:
        raise TiendaError("tienda_no_configurada", "Las compras todavía no están disponibles")
    roots = [p.read_bytes() for p in sorted(Path(folder).glob("*.cer"))]
    app_id = os.getenv("APPLE_APP_ID")
    return SignedDataVerifier(roots, True, environment, os.getenv("APPLE_BUNDLE_ID", "com.saptain.quantfut"),
                              int(app_id) if app_id else None)


def _verify(method: str, signed: str):
    from appstoreserverlibrary.models.Environment import Environment
    from appstoreserverlibrary.signed_data_verifier import VerificationException
    last = None
    for env in (Environment.PRODUCTION, Environment.SANDBOX):
        try:
            return getattr(_verifier(env), method)(signed)
        except VerificationException as exc:
            last = exc
    raise TiendaError("compra_no_valida", "La tienda no reconoce esta compra") from last


def _ms(value: int | None) -> datetime | None:
    return datetime.fromtimestamp(value / 1000, timezone.utc) if value else None


def parse(tx) -> Cobro:
    expires = _ms(tx.expiresDate)
    if expires is None:
        raise TiendaError("compra_no_valida", "La tienda no reconoce esta compra")
    env = getattr(tx.environment, "value", str(tx.environment))
    return Cobro(
        store="app_store", order_id=str(tx.transactionId), original_id=str(tx.originalTransactionId),
        account_token=str(tx.appAccountToken) if tx.appAccountToken else None,
        product_id=tx.productId, base_plan_id=None,
        period_start=_ms(tx.purchaseDate), period_end=expires,
        price_micros=tx.price * 1000 if tx.price is not None else None, currency=tx.currency,
        region_code=None, environment="production" if env == "Production" else "sandbox",
        state="sin_acceso" if tx.revocationDate else "activa",
        payload={"transactionId": str(tx.transactionId), "productId": tx.productId})


def verify_transaction(jws: str) -> Cobro:
    return parse(_verify("verify_and_decode_signed_transaction", jws))


def verify_notification(signed_payload: str) -> tuple[str, Cobro | None, str | None]:
    note = _verify("verify_and_decode_notification", signed_payload)
    kind = getattr(note.notificationType, "value", str(note.notificationType))
    signed_tx = note.data.signedTransactionInfo if note.data else None
    if not signed_tx:
        return kind, None, None
    tx = _verify("verify_and_decode_signed_transaction", signed_tx)
    if kind in _TIPOS_COBRO:
        return kind, parse(tx), str(tx.transactionId)
    if kind in _TIPOS_REVOCACION:
        return kind, None, str(tx.transactionId)
    return kind, None, None
