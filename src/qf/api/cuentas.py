"""API de clientes: la consumen la web y la app Flutter.

Ninguno de los dos clientes lleva secretos: cada persona se autentica con su
cuenta y el servidor decide qué picks ve. `SERVICE_TOKEN` y `ADMIN_TOKEN` no
sirven aquí ni se aceptan.

Esquema para generar el cliente Dart: `GET /app/v1/openapi.json`.
"""
from __future__ import annotations

import os
from datetime import datetime

import redis
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from . import mensajes, ratelimit
from ..comercial import correo, cuentas, meta_datos, suscripciones
from ..comercial.cuentas import CuentaError
from ..comercial.entrega import picks_for_tiers
from ..config import settings

_redis = None
_bearer = HTTPBearer(auto_error=False)


def redis_client():
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def require_enabled() -> None:
    # Apagado por defecto: un despliegue sin decidirlo no abre altas.
    if os.getenv("ACCOUNTS_ENABLED", "0") not in ("1", "true", "True"):
        raise HTTPException(503, {"code": "cuentas_deshabilitadas",
                                  "message": "Las cuentas todavía no están abiertas"})


router = APIRouter(prefix="/app/v1", tags=["app"], dependencies=[Depends(require_enabled)])


# --- Modelos: también son el contrato del cliente Dart generado.

class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=cuentas.PASSWORD_MAX)
    display_name: str | None = Field(default=None, max_length=80)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=cuentas.PASSWORD_MAX)


class RefreshIn(BaseModel):
    refresh_token: str | None = Field(default=None, max_length=200)


class TokenIn(BaseModel):
    token: str = Field(max_length=200)


class ForgotIn(BaseModel):
    email: str = Field(max_length=254)


class ResetIn(BaseModel):
    token: str = Field(max_length=200)
    password: str = Field(max_length=cuentas.PASSWORD_MAX)


class TokensOut(BaseModel):
    access_token: str
    # None en la web: allí el refresh viaja solo en la cookie HttpOnly.
    refresh_token: str | None
    token_type: str = "bearer"
    expires_in: int


class AccountOut(BaseModel):
    account_id: int
    email: str
    display_name: str | None
    email_verified: bool
    created_at: datetime


class SubscriptionOut(BaseModel):
    plan_code: str
    plan_name: str
    starts_at: datetime
    ends_at: datetime | None


class MeOut(BaseModel):
    account: AccountOut
    plus: bool
    subscription: SubscriptionOut | None
    # Lo pasa la app a la tienda (obfuscatedAccountId / appAccountToken): no es secreto
    # ni dato personal, solo liga la compra a esta cuenta.
    store_account_token: str | None = None
    # SHA-256 de qf:{account_id}: el mismo external_id que manda el servidor a Meta.
    meta_external_id: str


class PlanOut(BaseModel):
    plan_code: str
    name: str
    duration_days: int | None
    price_cents: int
    currency: str
    play_product_id: str | None = None
    play_base_plan_id: str | None = None
    apple_product_id: str | None = None


class PickOut(BaseModel):
    pick_id: str
    match_id: str
    league_id: str
    kickoff_utc: datetime
    local: str
    visitante: str
    market: str
    selection: str
    line: float | None
    advised_price: float | None
    min_price: float | None
    fair_prob: float | None
    bookmaker: str | None
    stake_units: float | None
    tier: str
    published_at: datetime | None


class PicksOut(BaseModel):
    plus: bool
    publicacion_activa: bool
    picks: list[PickOut]


# --- Web: el refresh vive en una cookie HttpOnly que el JavaScript no puede
# leer; el acceso, solo en memoria. La cabecera X-QF-Client obliga a un
# preflight CORS desde otro origen (y no está permitida), así que otra web no
# puede usar la cookie aunque el navegador la mande.
WEB_COOKIE = "qf_refresh"
# Indicador sin secreto y legible por JS: la página solo intenta recuperar la
# sesión si existe, en vez de lanzar un refresh 401 por cada visitante.
WEB_HINT = "qf_hay_sesion"
WEB_GRACE_SECONDS = 20


def _clear_web(response: Response) -> None:
    response.delete_cookie(WEB_COOKIE, path="/app/v1/auth")
    response.delete_cookie(WEB_HINT, path="/")


def _is_web(request: Request) -> bool:
    return request.headers.get("x-qf-client") == "web"


def _deliver(tokens: dict, request: Request, response: Response) -> dict:
    if not _is_web(request):
        return tokens
    if tokens["refresh_token"]:
        response.set_cookie(WEB_COOKIE, tokens["refresh_token"],
                            max_age=cuentas.REFRESH_TTL_DAYS * 86400, path="/app/v1/auth",
                            httponly=True, secure=settings.app_env != "development",
                            samesite="strict")
        response.set_cookie(WEB_HINT, "1", max_age=cuentas.REFRESH_TTL_DAYS * 86400, path="/",
                            secure=settings.app_env != "development", samesite="strict")
    return {**tokens, "refresh_token": None}


def _fail(status: int, err: CuentaError):
    raise HTTPException(status, {"code": err.code, "message": err.message})


def _limit(request: Request, scope: str, limit: int, window: int) -> None:
    if ratelimit.rate_limited(redis_client(), f"{scope}:{ratelimit.client_key(request)}",
                              limit, window):
        raise HTTPException(429, {"code": "demasiados_intentos",
                                  "message": "Demasiados intentos, espera un momento"})


def current_account(creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
                    request: Request = None) -> dict:
    if request is not None and request.headers.get('x-qf-identity') == 'firebase':
        from .firebase import firebase_account
        return firebase_account(creds, request)
    acc = cuentas.account_from_access(redis_client(), creds.credentials if creds else "")
    if acc is None:
        raise HTTPException(401, {"code": "no_autenticado", "message": "Sesión no válida"},
                            headers={"WWW-Authenticate": "Bearer"})
    acc["_token"] = creds.credentials
    return acc


def _lang(request: Request) -> str:
    return mensajes.idioma(request.headers.get("accept-language"))


def _account_out(acc: dict) -> AccountOut:
    return AccountOut(account_id=acc["account_id"], email=acc["email"],
                      display_name=acc["display_name"],
                      email_verified=acc["email_verified_at"] is not None,
                      created_at=acc["created_at"])


@router.post("/auth/register", response_model=TokensOut, status_code=201)
def register(body: RegisterIn, request: Request, response: Response, tasks: BackgroundTasks):
    _limit(request, "registro", 5, 3600)
    try:
        acc = cuentas.create_account(body.email, body.password, body.display_name)
    except CuentaError as e:
        _fail(409 if e.code == "email_en_uso" else 422, e)
    tasks.add_task(correo.enviar_verificacion, acc["account_id"], acc["email"], _lang(request))
    return _deliver(cuentas.open_session(redis_client(), acc["account_id"],
                                         request.headers.get("user-agent"),
                                         ratelimit.client_ip(request)), request, response)


@router.post("/auth/login", response_model=TokensOut)
def login(body: LoginIn, request: Request, response: Response):
    _limit(request, "login", 10, 60)
    # Por correo además de por IP: frena el ataque repartido entre muchas IPs.
    email_key = body.email.strip().lower()[:254]
    if ratelimit.rate_limited(redis_client(), f"login_email:{email_key}", 10, 900):
        raise HTTPException(429, {"code": "demasiados_intentos",
                                  "message": "Demasiados intentos, espera un momento"})
    acc = cuentas.authenticate(body.email, body.password)
    if acc is None:
        raise HTTPException(401, {"code": "credenciales", "message": "Correo o contraseña incorrectos"})
    if acc["status"] != "active":
        raise HTTPException(403, {"code": "cuenta_suspendida", "message": "Cuenta suspendida"})
    return _deliver(cuentas.open_session(redis_client(), acc["account_id"],
                                         request.headers.get("user-agent"),
                                         ratelimit.client_ip(request)), request, response)


@router.post("/auth/refresh", response_model=TokensOut)
def refresh(request: Request, response: Response, body: RefreshIn | None = None):
    _limit(request, "refresh", 30, 60)
    web = _is_web(request)
    token = (body.refresh_token if body else None) or (request.cookies.get(WEB_COOKIE) if web else None)
    try:
        tokens = cuentas.rotate_refresh(redis_client(), token or "",
                                        grace_seconds=WEB_GRACE_SECONDS if web else 0)
    except CuentaError as e:
        # En la web, una cookie que ya no vale se borra: la página deja de
        # intentar restaurar una sesión muerta en cada carga.
        if web:
            out = JSONResponse({"detail": {"code": e.code, "message": e.message}}, status_code=401)
            _clear_web(out)
            return out
        _fail(401, e)
    return _deliver(tokens, request, response)


@router.post("/auth/logout", status_code=204)
def logout(response: Response, acc: dict = Depends(current_account)):
    if acc.get('_identity') != 'firebase':
        cuentas.logout(redis_client(), acc["_token"], acc["session_id"])
    _clear_web(response)


@router.post("/auth/verify/resend", status_code=202)
def verify_resend(request: Request, tasks: BackgroundTasks, acc: dict = Depends(current_account)):
    if acc["email_verified_at"] is not None:
        return {"status": "ya_verificado"}
    if not correo.configurado():
        raise HTTPException(503, {"code": "correo_no_configurado",
                                  "message": "El envío de correo no está disponible"})
    if ratelimit.rate_limited(redis_client(), f"verificar:{acc['account_id']}", 3, 3600):
        raise HTTPException(429, {"code": "demasiados_intentos",
                                  "message": "Ya enviamos varios enlaces; revisa tu correo"})
    tasks.add_task(correo.enviar_verificacion, acc["account_id"], acc["email"], _lang(request))
    return {"status": "enviado"}


@router.post("/auth/verify/confirm", status_code=204)
def verify_confirm(body: TokenIn):
    if not cuentas.confirm_email(body.token):
        _fail(400, CuentaError("token_invalido", "El enlace no es válido o ha caducado"))


@router.post("/auth/password/forgot", status_code=202)
def password_forgot(body: ForgotIn, request: Request, tasks: BackgroundTasks):
    """Siempre 202 y el envío en segundo plano: ni la respuesta ni su
    duración dicen si el correo tiene cuenta."""
    _limit(request, "olvido", 5, 3600)
    email_key = body.email.strip().lower()[:254]
    if not ratelimit.rate_limited(redis_client(), f"olvido_email:{email_key}", 3, 3600):
        acc = cuentas.account_for_reset(body.email)
        if acc is not None:
            tasks.add_task(correo.enviar_restablecimiento, acc["account_id"], acc["email"], _lang(request))
    return {"status": "si_existe_la_cuenta_se_envio_el_enlace"}


@router.post("/auth/password/reset", status_code=204)
def password_reset(body: ResetIn, request: Request):
    _limit(request, "restablecer", 10, 60)
    try:
        ok = cuentas.reset_password(body.token, body.password)
    except CuentaError as e:
        _fail(422, e)
    if not ok:
        _fail(400, CuentaError("token_invalido", "El enlace no es válido o ha caducado"))


@router.get("/me", response_model=MeOut)
def me(acc: dict = Depends(current_account)):
    sub = suscripciones.active_subscription(acc["account_id"])
    return MeOut(account=_account_out(acc), plus=sub is not None,
                 subscription=SubscriptionOut(**sub) if sub else None,
                 store_account_token=acc.get("store_account_token"),
                 meta_external_id=meta_datos.external_id(acc["account_id"]))


@router.get("/picks", response_model=PicksOut)
def picks(acc: dict = Depends(current_account),
          limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
    plus = suscripciones.active_subscription(acc["account_id"]) is not None
    rows = picks_for_tiers(("free", "paid") if plus else ("free",), limit=limit, offset=offset)
    for r in rows:
        r["pick_id"], r["match_id"] = str(r["pick_id"]), str(r["match_id"])
    return PicksOut(plus=plus, publicacion_activa=settings.publish_picks_enabled, picks=rows)


# Catálogo público: los precios se leen aunque las altas estén cerradas. La
# web los toma de aquí, así que un cambio en el panel se ve sin desplegar.
public_router = APIRouter(prefix="/app/v1", tags=["app"])


@public_router.get("/plans", response_model=list[PlanOut])
def plans():
    return suscripciones.plans(only_active=True)


openapi_router = APIRouter(include_in_schema=False)


@openapi_router.get("/app/v1/openapi.json")
def app_openapi():
    """Solo las rutas de clientes: el esquema global sigue apagado."""
    return get_openapi(title="QuantFut App API", version="1.0.0",
                       description="Cuentas, planes y picks para la web y la app.",
                       routes=router.routes + public_router.routes)
