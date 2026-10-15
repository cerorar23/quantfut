"""Google Play Developer API: purchases.subscriptionsv2 y reconocimiento de compras.
Cuenta de servicio en PLAY_SERVICE_ACCOUNT_FILE (solo en el servidor)."""
from __future__ import annotations

import os
from datetime import datetime

from . import Cobro, TiendaError

SCOPE = "https://www.googleapis.com/auth/androidpublisher"
BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
_ACTIVA = {"SUBSCRIPTION_STATE_ACTIVE", "SUBSCRIPTION_STATE_CANCELED", "SUBSCRIPTION_STATE_IN_GRACE_PERIOD"}
_PENDIENTE = {"SUBSCRIPTION_STATE_PENDING"}


def package() -> str:
    return os.getenv("PLAY_PACKAGE_NAME", "com.saptain.quantfut")


def _session():
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account
    path = os.getenv("PLAY_SERVICE_ACCOUNT_FILE", "")
    if not path:
        raise TiendaError("tienda_no_configurada", "Las compras todavía no están disponibles")
    creds = service_account.Credentials.from_service_account_file(path, scopes=[SCOPE])
    return AuthorizedSession(creds)


def fetch(token: str, session=None) -> dict:
    s = session or _session()
    r = s.get(f"{BASE}/{package()}/purchases/subscriptionsv2/tokens/{token}", timeout=20)
    if r.status_code in (400, 404, 410):
        raise TiendaError("compra_no_valida", "La tienda no reconoce esta compra")
    r.raise_for_status()
    return r.json()


def acknowledge(product_id: str, token: str, session=None) -> None:
    s = session or _session()
    r = s.post(f"{BASE}/{package()}/purchases/subscriptions/{product_id}/tokens/{token}:acknowledge",
               json={}, timeout=20)
    r.raise_for_status()


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse(token: str, data: dict) -> Cobro:
    item = (data.get("lineItems") or [{}])[0]
    state = data.get("subscriptionState", "")
    price = (item.get("autoRenewingPlan") or {}).get("recurringPrice") or {}
    micros = (int(price["units"]) * 1_000_000 + int(price.get("nanos", 0)) // 1000) if "units" in price else None
    order = item.get("latestSuccessfulOrderId") or data.get("latestOrderId")
    if not order or not item.get("expiryTime"):
        raise TiendaError("compra_no_valida", "La tienda no reconoce esta compra")
    return Cobro(
        store="google_play", order_id=order, original_id=token,
        account_token=(data.get("externalAccountIdentifiers") or {}).get("obfuscatedExternalAccountId"),
        product_id=item.get("productId", ""),
        base_plan_id=(item.get("offerDetails") or {}).get("basePlanId"),
        period_start=_time(data["startTime"]), period_end=_time(item["expiryTime"]),
        price_micros=micros, currency=price.get("currencyCode"), region_code=data.get("regionCode"),
        environment="sandbox" if "testPurchase" in data else "production",
        state="activa" if state in _ACTIVA else "pendiente" if state in _PENDIENTE else "sin_acceso",
        payload=data)


def verify_push(authorization: str | None) -> None:
    """Pub/Sub firma cada push con un token OIDC de la cuenta de servicio configurada."""
    if not authorization or not authorization.startswith("Bearer "):
        raise TiendaError("rtdn_no_autenticado", "Notificación sin autenticar")
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token
    try:
        claims = id_token.verify_oauth2_token(authorization[7:], Request(),
                                              audience=os.environ["PLAY_RTDN_AUDIENCE"])
    except Exception:  # noqa: BLE001
        raise TiendaError("rtdn_no_autenticado", "Notificación sin autenticar") from None
    if not claims.get("email_verified") or claims.get("email") != os.getenv("PLAY_RTDN_SERVICE_ACCOUNT"):
        raise TiendaError("rtdn_no_autenticado", "Notificación sin autenticar")
