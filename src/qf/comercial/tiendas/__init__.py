"""Cobros verificados con Google Play y App Store. El acceso se decide aquí, en el
servidor, con lo que devuelve la tienda: la app solo transporta el token o el JWS."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class TiendaError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


@dataclass(frozen=True)
class Cobro:
    store: str                 # 'google_play' | 'app_store'
    order_id: str              # orderId (Play) / transactionId (Apple): un cobro
    original_id: str           # purchaseToken (Play) / originalTransactionId (Apple): la suscripción
    account_token: str | None  # obfuscatedExternalAccountId / appAccountToken
    product_id: str
    base_plan_id: str | None
    period_start: datetime
    period_end: datetime
    price_micros: int | None
    currency: str | None
    region_code: str | None
    environment: str           # 'production' | 'sandbox'
    state: str                 # 'activa' | 'pendiente' | 'sin_acceso'
    payload: dict
