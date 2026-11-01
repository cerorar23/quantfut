"""
API interna. NO es un producto que vendas a terceros.

Actualización 2026-10-07 (fase comercial desbloqueada por el usuario): las
cuentas de clientes viven en `/app/v1` (`cuentas.py`, web y app Flutter, sin
secretos en el cliente) y la administración en `/control` (`panel.py`). Lo
que sigue sobre "sin cuentas" describe `/v1`, que no cambia.

Actualización 2026-09-23: este mismo proceso sirve la web demo pública en
`/` y el panel de lectura `/control`. El BFF separado descrito en la decisión
histórica de abajo queda sustituido por módulos de un FastAPI único; cuentas,
pagos y autorización de suscriptores aún NO están implementados. Ningún
token de servicio o administración llega al JavaScript del navegador.

Decisión de arquitectura (2026-09-22): esta API no tiene cuentas de
suscriptor, ni cobros, ni login de usuario final. Los pronósticos se sirven
a UN SOLO cliente de confianza — el backend de tu propio frontend (BFF) —
que es quien maneja cuentas, pagos y arma los prompts del LLM para tus
usuarios finales. Ni el navegador ni la futura app Flutter le hablan a esta
API directamente: le hablan a tu backend, y solo tu backend le habla a esta
API. Esto importa porque un secreto embebido en un cliente que corre en el
dispositivo del usuario (JS de navegador, binario de app) SIEMPRE se puede
extraer; un secreto que vive solo en tu servidor, no.

Dos niveles de acceso, nada más:

  PÚBLICO      Sin auth. Track record, calibración, cadena de hashes y los
               picks gratuitos. Es tu escaparate: un comprador escéptico tiene
               que poder auditarte sin registrarse. Si le pides email para ver
               tu historial, asume que no vuelve. Tu propio frontend también
               puede leer esto sin credencial.

  SERVICIO     Un único secreto (`SERVICE_TOKEN`) que solo conoce tu backend
               de frontend, enviado en `X-Service-Token`. Da acceso a TODOS
               los picks y probabilidades sin recorte de tier — el recorte
               free/paid para usuarios finales lo decide tu frontend con su
               propia base de suscriptores, no esta API.

  ADMIN        Token único en .env, solo tú. Operación del sistema.
               Rutas separadas para poder cerrarlas por IP en el proxy.

Todo se sirve desde Redis, precalculado. La API nunca ejecuta el modelo en la
ruta de la petición: latencia de milisegundos y un pico de tráfico no tumba
el VPS.

Seguridad de plataforma (no solo de negocio): rate limiting por IP en TODAS
las rutas, cabeceras de seguridad, y `SERVICE_TOKEN`/`ADMIN_TOKEN`
obligatorios en el arranque — no hay fallback silencioso a un secreto vacío
o generado en caliente.
"""
from __future__ import annotations

import hmac
import json
import os

import redis
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import ratelimit
from .cuenta_web import router as cuenta_web_router
from .invitacion import router as invitacion_router
from .cuentas import openapi_router as cuentas_openapi_router
from .cuentas import public_router as cuentas_public_router
from .cuentas import router as cuentas_router
from .fichas import router as fichas_router
from .panel import router as panel_router
from .web import router as web_router
from .mobile import member, router as mobile_router
from . import mensajes
from .rewards import router as rewards_router
from .anuncios import router as anuncios_router
from .respaldo import router as respaldo_router
from .firebase import router as firebase_router
from .whop import router as whop_router, webhooks as whop_webhooks
from .legal import router as legal_router
from .meta import router as meta_router
from .compras import router as compras_router, store_router as compras_store_router
from ..comercial.entrega import picks_for_tiers
from ..config import settings
from ..db import query, query_one
from ..eval.clv import clv_report, summary
from ..model.devig import consensus_devig
from ..model.market_anchor import anchor_from_consensus
from ..model.promotion import evaluate_clv_gate

SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
DOMAIN = os.getenv("DOMAIN", "localhost")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(
    title="QuantFut",
    version=settings.model_version,
    description="Probabilidades calibradas de fútbol. No es asesoría financiera.",
    docs_url=None, redoc_url=None,   # sin docs públicas: es una API interna
    # Tampoco el esquema: listaba las rutas de /admin y /v1, que responden 404
    # precisamente para no confirmar que existen (auditoría 2026-10-03).
    openapi_url=None,
)

_cors_origins = [f"https://{DOMAIN}", f"https://www.{DOMAIN}"]
if settings.app_env == "development":
    _cors_origins.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-QF-Identity", "X-Firebase-AppCheck"],
)

r = redis.from_url(settings.redis_url, decode_responses=True)

publico = APIRouter(tags=["público"])
privado = APIRouter(prefix="/v1", tags=["servicio"])
admin = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Rate limiting global (todas las rutas) + cabeceras de seguridad
# ---------------------------------------------------------------------------

_client_key = ratelimit.client_key


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # /control lleva contador propio: con el global compartido, su tope se
    # comparaba contra las visitas a la web y a sus estáticos del mismo
    # minuto, y el panel devolvía 429 al operador. Desde 2026-10-07 el panel
    # tiene varias páginas y carga sus librerías de /static: el tope de 10
    # que bastaba para una sola página cortaba la navegación normal.
    if request.url.path.startswith(("/control", "/static")):
        scope, limit = "control", settings.rate_limit_default_per_minute * 2
    elif request.url.path.startswith(("/web/escudos/", "/web/imagenes/")):
        # Una sola pantalla de la app pide ~80 escudos (uno por equipo) y agotaba los 60/min por IP:
        # el resto de la app (p. ej. Coins) recibía 429 (2026-10-15). Son PNG estáticos y de solo lectura.
        # Los logos NBA y las fotos de tenis (/web/imagenes/) son igual de estáticos.
        scope, limit = "escudos", settings.rate_limit_default_per_minute * 10
    else:
        scope, limit = "ip", settings.rate_limit_default_per_minute
    if ratelimit.rate_limited(r, f"{scope}:{_client_key(request)}", limit):
        return JSONResponse({"detail": "Demasiadas solicitudes, intenta más tarde"},
                            status_code=429)

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    if request.url.path.startswith(("/v1", "/admin", "/control")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Igual que el manejador por defecto de FastAPI, pero traduce los mensajes
    conocidos al idioma de `Accept-Language` (ver `mensajes.py`)."""
    lang = mensajes.idioma(request.headers.get("accept-language"))
    return JSONResponse({"detail": mensajes.traducir_detalle(exc.detail, lang)},
                        status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Nunca devolver el traceback ni el mensaje de la excepción original al
    # cliente: puede filtrar rutas de archivo, queries SQL o versiones de
    # librería. El detalle real queda en el log del proceso.
    import logging
    logging.getLogger(__name__).exception("Error no manejado en %s", request.url.path)
    return JSONResponse({"detail": "Error interno"}, status_code=500)


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

def require_service(x_service_token: str = Header(default="")) -> bool:
    """Único secreto de servidor a servidor: solo tu backend de frontend lo
    conoce. No hay noción de "usuario" aquí — quien lo presenta obtiene TODOS
    los picks, y es tu backend el que decide qué le muestra a cada usuario
    final según su propia base de suscriptores."""
    if not SERVICE_TOKEN or not hmac.compare_digest(x_service_token, SERVICE_TOKEN):
        raise HTTPException(404)   # 404, no 401: no confirmes que la ruta existe
    return True


def require_admin(x_admin_token: str = Header(default="")) -> bool:
    if not ADMIN_TOKEN or not hmac.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(404)   # 404, no 401: no confirmes que la ruta existe
    return True


# ---------------------------------------------------------------------------
# PÚBLICO — el escaparate. Sin auth, a propósito.
# ---------------------------------------------------------------------------

@publico.get("/health")
def health():
    return {"status": "ok", "model_version": settings.model_version}


@publico.get("/track-record")
def track_record():
    """
    Se publica entero, incluidos los meses en pérdida. Ocultar las rachas malas
    es lo que hace que nadie crea a nadie en este sector.
    """
    return {
        "mensual": query("SELECT * FROM v_track_record"),
        "ultimos_7d": summary(7),
        "ultimos_30d": summary(30),
        "ultimo_ano": summary(365),
        "nota": ("Nuestra métrica principal es avg_ev_close: el valor esperado "
                 "de la cuota que aconsejamos, valorada al cierre de Pinnacle "
                 "sin margen. avg_clv compara contra la cuota de cierre con "
                 "margen y sale más alta por ese margen; se publica por "
                 "transparencia. El ROI a pocos cientos de picks es ruido "
                 "estadístico, por eso publicamos su intervalo de confianza "
                 "al lado."),
    }


@publico.get("/escalera")
def escalera(response: Response, plus: bool = Depends(member)):
    """
    Reto escalera: el reto en curso con sus escalones sellados, el historial
    de retos cerrados (también los fallidos) y la ganancia acumulada.
    """
    from .mobile import ladder
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Vary'] = 'Authorization'
    data = ladder(plus=plus)
    if plus:
        return data      # la cuenta VIP ve todos los escalones, también en la web
    # Igual que /alta-probabilidad: la web difumina la cuota de lo bloqueado (decisión del titular, 2026-10-18), así que
    # esta ruta pública no la envía. La app lee /mobile/v1/home y no cambia.
    for reto in data.get('actuales', []):
        reto['vip'] = [{k: v for k, v in item.items() if k != 'cuota'} for item in reto.get('vip', [])]
    return data


WEB_PUBLICO_GRATIS_ALTA = 1   # pronósticos de alta probabilidad gratis visibles al público de la web


@publico.get("/alta-probabilidad")
def alta_probabilidad(response: Response, plus: bool = Depends(member)):
    """
    Línea de alta probabilidad: pronósticos sellados con probabilidad real
    (Pinnacle sin margen) filtrados al 75–90 %, 10 % gratuito por lote.
    El historial de acierto se conserva entero. Las puertas de publicación
    y su rango original se mantienen en el pipeline.
    """
    from .mobile import high_probability, metadata
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Vary'] = 'Authorization'
    informe = high_probability(plus=plus)
    if plus:
        return informe   # la cuenta VIP ve todos los pronósticos, también en la web
    # Al público de la web solo se le deja VER uno gratis en esta sección (decisión del titular, 2026-10-18: «uno por
    # sección»); queda el de mayor probabilidad y el resto pasa a bloqueado. La app no usa esta ruta: sus 4 gratis no cambian.
    libres = sorted(informe.get('proximos', []), key=lambda p: -float(p.get('prob') or 0))
    if len(libres) > WEB_PUBLICO_GRATIS_ALTA:
        informe['proximos'] = libres[:WEB_PUBLICO_GRATIS_ALTA]
        informe['vip'] = [*informe.get('vip', []), *[metadata(p) for p in libres[WEB_PUBLICO_GRATIS_ALTA:]]]
    # La web difumina la cuota de lo bloqueado (decisión del titular, 2026-10-18). Difuminar un dato que sigue en la
    # respuesta no protege nada, así que esta ruta pública no lo envía. La app NO usa esta ruta (lee /mobile/v1/home
    # con `mobile.metadata`, que no se toca).
    informe['vip'] = [{k: v for k, v in item.items() if k != 'cuota'} for item in informe.get('vip', [])]
    return informe

@publico.get("/parley")
def parley(response: Response, plus: bool = Depends(member)):
    """
    Parley del día: 1 a 5 parlays sellados de cuota 1,90-5,00, el más probable
    de cada escalón, y su historial prometido frente a real. Se elige por
    probabilidad, no por valor. Uno gratis al día (el de menor escalón); el resto
    es VIP y los ya liquidados se ven siempre (`parley_acceso`).
    """
    from ..publish import parley_datos
    from .parley_acceso import aplicar_acceso
    response.headers['Cache-Control'] = 'no-store'
    return aplicar_acceso(parley_datos.informe_publico(), plus)


@publico.get("/calibration")
def calibration():
    return {"runs": query(
        """SELECT model_version, window_start, window_end, n_obs,
                  rps, rps_market, log_loss, brier, bins, created_at
           FROM calibration_runs ORDER BY created_at DESC LIMIT 12"""
    )}


@publico.get("/chain")
def chain(limit: int = Query(90, le=365)):
    return {
        "lotes": query(
            """SELECT batch_date, batch_kind, match_id, n_predictions, n_picks, payload_sha256,
                      prev_sha256, chain_sha256, created_at, published_ref
               FROM prediction_batches ORDER BY seq DESC LIMIT %s""",
            (limit,),
        ),
        "como_verificar": [
            "1. Descarga el JSON del lote del repo público (los lotes de tipo 'partido' están en partido/AAAA-MM-DD/).",
            "2. Calcula su SHA-256 y compáralo con payload_sha256.",
            "3. Comprueba que sha256(prev_sha256 || payload_sha256) == chain_sha256.",
            "Si cambiáramos una sola predicción pasada, todos los hashes "
            "posteriores dejarían de cuadrar.",
        ],
    }


@publico.get("/model-card")
def model_card():
    art = query_one("SELECT model_version, trained_at, params, val_metrics "
                    "FROM model_artifacts WHERE is_active LIMIT 1")
    params = (art or {}).get("params") or {}
    val = (art or {}).get("val_metrics") or {}
    cal = val.get("calibration") or {}
    meta = val.get("meta") or {}
    benchmarks = val.get("benchmarks") or {}

    # La puerta comercial, en la cara pública y con su motivo. Desde el
    # 2026-09-22 no se decide por batir al cierre en RPS —que es lo que casi
    # nadie consigue y además no es lo que se cobra— sino por CLV con
    # intervalo de confianza y en varias ligas. Publicar que TODAVÍA no está
    # autorizada es parte del producto: un sistema que solo enseña sus
    # métricas cuando salen bien no es auditable.
    try:
        clv_gate = clv_report(days=180)
        autorizado, motivos = evaluate_clv_gate(clv_gate)
    except Exception:  # noqa: BLE001
        clv_gate, autorizado, motivos = None, False, ["CLV no disponible"]

    # Con la publicación pausada, la muestra que puede autorizar reactivarla
    # es la de la sombra del criterio sharp. Se publica igual que la puerta.
    try:
        from ..publish.shadow_sharp import report as sharp_shadow_report
        sombra = sharp_shadow_report()
        sombra = {"autorizada": sombra["gate"]["authorized"],
                  "motivos": sombra["gate"]["reasons"],
                  "publicables": {k: v for k, v in sombra["publishable"].items()
                                  if k != "by_league"},
                  "ofertas_registradas": sombra["n_offers"]}
    except Exception:  # noqa: BLE001
        sombra = {"autorizada": False, "motivos": ["Sombra no disponible"]}

    return {
        "model_version": (art or {}).get("model_version", settings.model_version),
        "artefacto": art,
        "puerta_comercial": {
            "autorizada": autorizado,
            "criterio": ("Valor esperado de la cuota tomada, valorada al "
                         "cierre de Pinnacle SIN margen, con intervalo de "
                         "confianza del 95% por encima de cero, mínimo 300 "
                         "apuestas liquidadas y al menos 3 ligas con muestra "
                         "propia. El CLV contra la cuota con margen se "
                         "publica pero no decide: el margen lo infla."),
            "motivos": motivos,
            "clv": clv_gate,
            "sombra_criterio_sharp": sombra,
            "publicacion_de_picks": (
                "activa" if settings.publish_picks_enabled and sombra["autorizada"] else
                "pausada: el criterio de precio sharp corre en sombra "
                "(sombra_criterio_sharp) y la publicación se reanuda solo "
                "cuando esa muestra supere esta misma puerta"),
        },
        "metodo": ("Dixon-Coles con decaimiento temporal, objetivo mezclado "
                   "goles/xG, efectos por liga con pooling parcial y fuerza "
                   "relativa entre ligas estimada con los cruces europeos"),
        "eliminacion_de_margen": settings.devig_method,
        # Un bloque por liga: ventaja de local y nivel de goles estimados por
        # separado. Se publica porque es auditable y porque explica por qué las
        # predicciones de Liga MX no salen de la misma plantilla que las de
        # Premier League.
        "parametros_por_liga": params.get("leagues", []),
        # Champions y Europa League son los únicos partidos que enfrentan
        # equipos de ligas distintas, y por tanto lo único que permite situar
        # a las ocho ligas en una escala común. Se publica la lectura para que
        # se entienda por qué el mismo equipo no vale lo mismo en cada
        # competición.
        "fuerza_relativa_entre_ligas": {
            "valores": {lg["league_id"]: lg.get("relative_strength")
                        for lg in params.get("leagues", [])
                        if lg.get("relative_strength") is not None},
            "nota": ("Desplazamiento en escala logarítmica frente a la media "
                     "de las competiciones. Se identifica SOLO con los cruces "
                     "europeos: dentro de una liga la suma cero lo borra. Con "
                     "pocos cruces está muy encogido hacia cero a propósito."),
        },
        "calibracion": {
            "aplicada": bool(cal.get("ok")),
            "log_loss_antes": cal.get("log_loss_before"),
            "log_loss_despues": cal.get("log_loss_after"),
            "nota": ("La calibración se ajusta sobre predicciones fuera de "
                     "muestra y solo se aplica si mejora. Cuando no aparece "
                     "aplicada es porque el modelo ya estaba calibrado, no "
                     "porque no se haya intentado."),
        },
        # El peso modelo/mercado se publica aunque la mezcla esté desactivada:
        # es la medida honesta de cuánto aporta el modelo sobre el consenso, y
        # publicarlo es más creíble que afirmar que se le gana al mercado.
        "peso_modelo_vs_mercado": {
            "w_model": meta.get("w_model"),
            "por_liga": meta.get("w_by_league", {}),
            "log_loss_modelo": meta.get("log_loss_modelo"),
            "log_loss_mercado": meta.get("log_loss_mercado"),
            "log_loss_mezcla": meta.get("log_loss_mezcla"),
            "mezcla_aplicada_en_produccion": settings.meta_blend_enabled,
            "lectura": meta.get("lectura"),
        },
        "comparacion_mismas_observaciones": {
            "n": benchmarks.get("n_obs"),
            "firma_muestra": benchmarks.get("match_ids_sha256"),
            "dixon_coles": (benchmarks.get("models") or {}).get("dixon_coles"),
            "elo": (benchmarks.get("models") or {}).get("elo"),
            "pinnacle_sin_margen": (benchmarks.get("models") or {}).get("market"),
            "nota": ("Los tres se evalúan sobre la misma intersección de "
                     "partidos; Elo es un baseline, no una afirmación de edge."),
        },
        "challengers": {
            "residual": val.get("residual"),
            "multinomial": val.get("multinomial"),
            "ablaciones": val.get("ablations"),
            "alineaciones": val.get("lineup_challenger"),
            "promocion": val.get("promotion"),
            "nota": ("Un resultado offline favorable sigue en sombra hasta "
                     "reunir CLV real suficiente; no modifica picks publicados."),
        },
        "limitaciones_conocidas": [
            "El xG solo existe desde ~2017-18; los partidos anteriores del "
            "histórico se modelan solo con goles, que tienen más ruido.",
            "Argentina tiene xG por partido pero no datos de remates, así que "
            "es la única liga sin PSxG ni ajuste por estado del partido.",
            "Champions y Europa League entran como datos de ENTRENAMIENTO, no "
            "como mercado. No existe histórico gratuito de cuotas de esas "
            "competiciones, así que no se pueden evaluar ni calibrar contra el "
            "mercado hasta acumular cierres propios.",
            "De los cruces europeos solo se aprovechan los partidos con los "
            "dos equipos en el catálogo: 1.111 de 3.308. El resto involucra "
            "ligas que no están dadas de alta (Bélgica, Rusia, Ucrania, "
            "Turquía y Grecia son las que más pesan).",
            "Equipos con menos de 15 partidos de historia se marcan como "
            "confianza baja en la predicción. Desde el 2026-09-23 eso ya no "
            "decide los picks, que no salen del modelo.",
            "Las alineaciones confirmadas se capturan a T-60 pero todavía no "
            "ajustan la predicción: hace falta acumular histórico primero.",
            "En la última validación sobre 28.128 partidos, el modelo NO batió "
            "al cierre sin margen de Pinnacle en ninguna de las 7 ligas que "
            "había entonces (ni en la MLS al ampliar el catálogo) "
            "(RPS 0.20327 frente a 0.19674). El peso óptimo del modelo frente "
            "al consenso de mercado se estimó en 0.0001. Se publica porque "
            "ocultarlo sería exactamente lo que hace increíble a este sector.",
            "Los picks no salen del modelo, cuyo edge resultó ser una "
            "anti-señal (correlación −0,123 con el acierto). Salen de casas "
            "que pagan más que el precio justo de Pinnacle en ese momento. "
            "El edge publicado es el ESPERADO AL CIERRE: el edge frente al "
            "precio justo multiplicado por la fracción que, medida en el "
            "histórico, sobrevive hasta el cierre en esa casa (1xBet 0,72; "
            "Bet365 0,13; William Hill 0; casas sin medir 0,42).",
            "El valor medido en el histórico con las casas que usan nuestros "
            "suscriptores sale casi entero de una sola casa (1xBet) y sobre "
            "todo de la MLS. Si esa casa limita las cuentas, desaparece.",
            "Bet365 y Betano no tienen histórico de cuotas en ninguna fuente "
            "accesible: su valor se está midiendo desde el 2026-09-23.",
        ],
    }


@publico.get("/picks/free")
def picks_gratis(limit: int = Query(20, le=100), offset: int = Query(0, ge=0)):
    """Los picks del escaparate gratuito. Es lo que se muestra sin login en la web."""
    return picks_for_tiers(("free",), limit=limit, offset=offset)


@publico.get("/leagues")
def leagues():
    """Catálogo de ligas activas, para el selector/filtro de la web."""
    return query(
        """SELECT league_id, country, name, tier
           FROM leagues WHERE active ORDER BY tier, country, name"""
    )


@publico.get("/teams")
def teams(league: str | None = None,
           limit: int = Query(100, le=500), offset: int = Query(0, ge=0)):
    """Catálogo de equipos, opcionalmente filtrado por liga."""
    return query(
        """SELECT team_id, league_id, canonical_name
           FROM teams
           WHERE %s::text IS NULL OR league_id = %s::text
           ORDER BY canonical_name
           LIMIT %s OFFSET %s""",
        (league, league, limit, offset),
    )


@publico.get("/matches/{match_id}")
def match_public(match_id: str):
    """
    Ficha pública de un partido: datos del partido + la predicción recortada
    al tier gratuito (mismo recorte de mercados que ve un suscriptor free).
    Pensada para páginas de partido indexables, sin necesitar login.
    """
    m = query_one(
        """SELECT m.match_id, m.league_id, m.season, m.kickoff_utc, m.status,
                  m.home_goals, m.away_goals,
                  th.canonical_name AS local, ta.canonical_name AS visitante
           FROM matches m
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.match_id = %s""",
        (match_id,),
    )
    if not m:
        raise HTTPException(404, "Partido no encontrado")

    # Sin `market_consensus` (auditoría 2026-10-03): es el precio justo sin
    # margen, y con él se reconstruye el criterio de picks, igual que con
    # `/fair-price` antes de pasar a `/v1`. Sigue en `/v1/.../predictions`.
    pred = query_one(
        """SELECT prediction_id, model_version, generated_at, markets,
                  confidence_tier, data_completeness
           FROM predictions WHERE match_id = %s
           ORDER BY generated_at DESC LIMIT 1""",
        (match_id,),
    )
    if pred:
        pred["markets"] = {
            "1x2": pred["markets"].get("1x2"),
            "totals": {"2.5": pred["markets"].get("totals", {}).get("2.5")},
        }

    pick = query_one(
        """SELECT pick_id, market, selection, line, advised_price, bookmaker,
                  edge_pct, min_price, odds_as_of, published_at
           FROM picks WHERE match_id = %s AND tier = 'free'
           ORDER BY published_at DESC LIMIT 1""",
        (match_id,),
    )

    return {"match": m, "prediction": pred, "pick": pick}


@privado.get("/fair-price/{match_id}", dependencies=[Depends(require_service)])
def fair_price(match_id: str):
    """
    Precio JUSTO derivado del mercado sharp, y dónde las casas se apartan de él.

    PRIVADO desde 2026-09-28 (antes era público en `/fair-price`): `best_price`
    y `gap_pct` dicen qué casa paga por encima del justo en cada partido, que
    es el criterio de picks entero. Con `SERVICE_TOKEN`, como `/v1/picks`.

    Es una salida distinta de `/matches/{id}`, y la diferencia es el producto
    entero. Esa devuelve lo que opina el modelo. Esta devuelve:

      1. el consenso sharp (Pinnacle y Betfair pesados) SIN margen;
      2. las intensidades implícitas en ese precio (`model/market_anchor.py`),
         que permiten derivar cualquier mercado a partir del precio sharp en
         vez de a partir de la fuerza estimada de los equipos;
      3. la mejor cuota disponible por selección y su distancia al precio justo.

    El motivo de que exista está medido: `w_model = 0.0001`. El modelo no le
    gana al mercado en nivel, así que vender "nuestra probabilidad" es vender
    lo que peor hacemos. Lo que sí se puede sostener es esto: el mercado sharp
    ya fijó un precio y hay casas que todavía no han convergido.

    `anchor` puede venir a null: la familia Dixon-Coles no representa cualquier
    terna 1X2, y cuando no llega se dice en vez de devolver un ajuste forzado.
    """
    m = query_one(
        """SELECT m.match_id, m.league_id, m.kickoff_utc, m.status,
                  th.canonical_name AS local, ta.canonical_name AS visitante
           FROM matches m
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.match_id = %s""",
        (match_id,),
    )
    if not m:
        raise HTTPException(404, "Partido no encontrado")

    filas = query(
        """SELECT DISTINCT ON (bookmaker, selection)
                  bookmaker, selection, price, captured_at
           FROM odds_snapshots
           WHERE match_id = %s AND market = 'h2h'
           ORDER BY bookmaker, selection, captured_at DESC""",
        (match_id,),
    )
    por_casa: dict[str, dict[str, float]] = {}
    for f in filas:
        por_casa.setdefault(f["bookmaker"], {})[f["selection"]] = float(f["price"])
    completas = {b: q for b, q in por_casa.items()
                 if {"home", "draw", "away"} <= set(q)}
    if not completas:
        raise HTTPException(404, "Sin cuotas 1X2 para este partido")

    cons = consensus_devig(completas, method=settings.devig_method,
                           sharp_book=settings.sharp_book)
    ajuste = anchor_from_consensus(cons)

    salida = {}
    for sel in ("home", "draw", "away"):
        p = cons[sel]
        mejor, casa = max((q[sel], b) for b, q in completas.items())
        salida[sel] = {
            "fair_prob": round(p, 5),
            "fair_price": round(1.0 / p, 4) if p > 0 else None,
            "best_price": mejor,
            "best_book": casa,
            # Cuánto paga la mejor casa por encima del precio justo. Positivo
            # = todavía no ha convergido al sharp.
            "gap_pct": round((p * mejor - 1.0) * 100.0, 3),
        }

    return {
        "match": m,
        "sharp_book": settings.sharp_book,
        "devig_method": settings.devig_method,
        "books_used": len(completas),
        "selections": salida,
        "anchor": ajuste.as_dict() if ajuste is not None else None,
    }


# ---------------------------------------------------------------------------
# SERVICIO — solo tu backend de frontend. Sin recorte de tier: eso lo decide
# tu backend con su propia base de usuarios, no esta API.
# ---------------------------------------------------------------------------

@privado.get("/picks", dependencies=[Depends(require_service)])
def picks(limit: int = Query(20, le=100), offset: int = Query(0, ge=0)):
    return picks_for_tiers(("free", "paid"), limit=limit, offset=offset)


@privado.get("/matches/{match_id}/predictions", dependencies=[Depends(require_service)])
def predictions(match_id: str):
    cached = r.get(f"pred:{match_id}:full")
    if cached:
        return json.loads(cached)

    row = query_one(
        """SELECT prediction_id, match_id, model_version, generated_at,
                  home_lambda, away_lambda, markets, market_consensus,
                  confidence_tier, data_completeness
           FROM predictions WHERE match_id = %s
           ORDER BY generated_at DESC LIMIT 1""",
        (match_id,),
    )
    if not row:
        raise HTTPException(404, "Todavía no hay predicción para ese partido")

    r.setex(f"pred:{match_id}:full", 600, json.dumps(row, default=str))
    return row


@privado.get("/fixtures", dependencies=[Depends(require_service)])
def fixtures(league: str | None = None, hours: int = Query(72, le=240)):
    return query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc,
                  th.canonical_name AS local, ta.canonical_name AS visitante,
                  EXISTS(SELECT 1 FROM predictions p
                         WHERE p.match_id = m.match_id) AS tiene_prediccion
           FROM matches m
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.status = 'scheduled'
             AND (%s::text IS NULL OR m.league_id = %s::text)
             AND m.kickoff_utc BETWEEN now() AND now() + make_interval(hours => %s)
           ORDER BY m.kickoff_utc""",
        (league, league, hours),
    )


# ---------------------------------------------------------------------------
# ADMIN — operación. Ciérralo por IP en el proxy además del token.
# ---------------------------------------------------------------------------

@admin.get("/health", dependencies=[Depends(require_admin)])
def admin_health():
    from ..ingest.health import run as health_run
    return health_run(alert_on_fail=False)


@admin.get("/unresolved", dependencies=[Depends(require_admin)])
def unresolved():
    from ..normalize import pending_report
    return pending_report()


@admin.post("/alias", dependencies=[Depends(require_admin)])
def add_alias(payload: dict):
    from ..normalize import register_alias
    t = query_one(
        "SELECT team_id FROM teams WHERE league_id=%s AND canonical_name=%s",
        (payload["league_id"], payload["canonical_name"]),
    )
    if not t:
        raise HTTPException(404, "Ese equipo no existe en esa liga")
    register_alias(payload["raw_name"], payload["source"], t["team_id"])
    return {"ok": True}


@admin.post("/run/{job}", dependencies=[Depends(require_admin)])
def run_job(job: str):
    """Disparo manual de los jobs. Útil para depurar sin entrar por SSH."""
    jobs = {
        "fixtures": ("..ingest.fixtures", "run"),
        "results": ("..ingest.results", "close_recent"),
        "odds": ("..ingest.odds_worker", "run_once"),
        "xg": ("..ingest.xg_worldfootball", "run"),
        "uefa_cups": ("..ingest.uefa_cups", "run"),
        "lineups": ("..ingest.lineups", "run"),
        "daily": ("..publish.daily", "run"),
        "settle": ("..eval.clv", "settle_pending"),
    }
    if job not in jobs:
        raise HTTPException(404, f"Jobs disponibles: {', '.join(jobs)}")
    import importlib
    mod = importlib.import_module(jobs[job][0], package=__package__)
    return getattr(mod, jobs[job][1])()


@admin.get("/picks/pending", dependencies=[Depends(require_admin)])
def pending_settlement():
    return query(
        """SELECT p.pick_id, p.match_id, p.market, p.selection, p.advised_price,
                  m.kickoff_utc, m.status
           FROM picks p JOIN matches m USING (match_id)
           LEFT JOIN pick_results res USING (pick_id)
           WHERE res.pick_id IS NULL AND m.kickoff_utc < now()
           ORDER BY m.kickoff_utc"""
    )


@admin.get("/shadow-audit", dependencies=[Depends(require_admin)])
def shadow_audit():
    """Embudo operativo por liga; nunca cambia ofertas ni abre la venta."""
    from ..publish.shadow_sharp import audit
    return audit()


@admin.get("/challengers", dependencies=[Depends(require_admin)])
def admin_challengers():
    """Estado operativo de experimentos y CLV en sombra."""
    art = query_one("SELECT model_version, val_metrics FROM model_artifacts "
                    "WHERE is_active LIMIT 1") or {}
    val = art.get("val_metrics") or {}
    try:
        from ..model.shadow import summary as shadow_summary
        shadow = shadow_summary()
        baseline_shadow = shadow_summary("baseline_t60")
    except Exception as exc:  # noqa: BLE001
        shadow = {"n": 0, "error": str(exc)}
        baseline_shadow = {"n": 0, "error": str(exc)}
    from ..model.promotion import evaluate_shadow_promotion
    lineup_report = val.get("lineup_challenger") or {}
    lineup_gate = (evaluate_shadow_promotion(lineup_report, shadow,
                                             baseline_shadow).as_dict()
                   if lineup_report.get("status") == "shadow_only" else None)
    return {
        "model_version": art.get("model_version"),
        "benchmarks": val.get("benchmarks"),
        "multinomial": val.get("multinomial"),
        "ablations": val.get("ablations"),
        "lineup_challenger": val.get("lineup_challenger"),
        "lineup_promotion_gate": lineup_gate,
        "promotion": val.get("promotion"),
        "shadow_clv": shadow,
        "baseline_t60_clv": baseline_shadow,
    }


app.include_router(publico)
app.include_router(privado)
app.include_router(admin)
app.include_router(panel_router)
app.include_router(cuentas_router)
app.include_router(cuentas_openapi_router)
app.include_router(cuentas_public_router)
app.include_router(cuenta_web_router)
app.include_router(invitacion_router)
app.include_router(web_router)
app.include_router(fichas_router)
app.include_router(mobile_router)
# anuncios va ANTES: su `/rewards/callback/admob` es más específico que
# `/rewards/callback/{provider}` de ofertas, que si no lo capturaría.
app.include_router(anuncios_router)
app.include_router(rewards_router)
app.include_router(respaldo_router)
app.include_router(firebase_router)
app.include_router(whop_router)
app.include_router(whop_webhooks)
app.include_router(meta_router)
app.include_router(compras_router)
app.include_router(compras_store_router)
app.include_router(legal_router)

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
