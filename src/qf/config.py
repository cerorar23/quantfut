"""Configuración central. Todo por variables de entorno, nada hardcodeado."""
from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _f(key: str, default: float) -> float:
    return float(os.getenv(key, default))


def _i(key: str, default: int) -> int:
    return int(os.getenv(key, default))


def _odds_provider() -> str:
    selected = os.getenv("ODDS_PROVIDER")
    policy = Path(os.getenv("PROPLINE_ARCHIVE", "/srv/quantfut/artifacts/propline_shared")) / "provider.json"
    if selected is None and policy.is_file():
        selected = json.loads(policy.read_text(encoding="utf8"))["provider"]
    selected = selected or "the_odds_api"
    if selected not in ("the_odds_api", "propline"):
        raise ValueError("unknown odds provider")
    return selected


@dataclass(frozen=True)
class Settings:
    # --- Infraestructura ---
    pg_dsn: str = os.getenv("PG_DSN", "postgresql://qf:qf@localhost:5432/quantfut")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # --- APIs ---
    odds_api_key: str = os.getenv("ODDS_API_KEY", "")
    odds_api_base: str = "https://api.the-odds-api.com/v4"
    # PropLine is captured once hourly outside the prediction worker. Consumers
    # read its archive; the key belongs only to the collector. Legacy remains
    # selectable for reproducing older research, not as a silent fallback.
    odds_provider: str = _odds_provider()
    propline_archive: str = os.getenv("PROPLINE_ARCHIVE", "/srv/quantfut/artifacts/propline_shared")
    # Casas que no son la sharp: solo partidos a menos de estas horas y una
    # observación de cada tantas (diez casas cada hora a 8 días eran ~100 MB/día
    # de `odds_snapshots`, medido el 24-oct). La cuota de referencia admite 6 h.
    propline_soft_horizon_hours: int = _i("PROPLINE_SOFT_HORIZON_HOURS", 48)
    propline_soft_every_hours: int = _i("PROPLINE_SOFT_EVERY_HOURS", 3)
    # Resultados y calendario. API-Football pasó al plan gratuito el 22-oct-2026
    # y el titular decidió sustituirlo por el archivo de PropLine (24-oct).
    # Archivo del recolector SofaScore vía Apify (host), montado en solo lectura.
    sofascore_archive: str = os.getenv("SOFASCORE_ARCHIVE", "/srv/quantfut/sofascore")
    # `eu` trae Pinnacle y Betfair Exchange, la referencia sharp. `us` solo
    # añade casas de EE. UU. y duplica el coste en créditos.
    odds_api_regions: str = os.getenv("ODDS_API_REGIONS", "eu")
    odds_api_markets: str = os.getenv("ODDS_API_MARKETS", "h2h,totals,spreads")
    api_football_key: str = os.getenv("API_FOOTBALL_KEY", "")
    # Peticiones por minuto del plan de API-Football. El plan Free son 10 y
    # devuelve 429 al superarlo; los de pago suben mucho. Es el valor del que
    # el cliente deriva su intervalo entre llamadas.
    api_football_rpm: int = _i("API_FOOTBALL_RPM", 10)
    # Cuota DIARIA del plan. Free = 100. Se usa para presupuestar el calendario
    # de ingesta, no solo para avisar cuando ya se agotó.
    api_football_daily: int = _i("API_FOOTBALL_DAILY", 100)

    # --- Telegram ---
    tg_bot_token: str = os.getenv("TG_BOT_TOKEN", "")
    tg_channel_free: str = os.getenv("TG_CHANNEL_FREE", "")
    tg_channel_paid: str = os.getenv("TG_CHANNEL_PAID", "")
    tg_alert_chat: str = os.getenv("TG_ALERT_CHAT", "")  # alertas de fallos

    # --- Publicación de la cadena de hashes ---
    chain_dir: str = os.getenv("CHAIN_DIR", "/srv/quantfut/chain")
    chain_git_remote: str = os.getenv("CHAIN_GIT_REMOTE", "")

    # --- Modelo ---
    model_version: str = os.getenv("MODEL_VERSION", "0.1.0")
    fs_version: str = os.getenv("FS_VERSION", "fs-0.1.0")
    artifact_dir: str = os.getenv("ARTIFACT_DIR", "/srv/quantfut/artifacts")
    # Escudos descargados una vez de API-Football (ingest/standings.py) y
    # servidos desde el propio dominio: la web no enlaza al proveedor.
    escudos_dir: str = os.getenv("ESCUDOS_DIR", "/srv/quantfut/escudos")
    # Cohortes NBA v1.3 del productor (live13/cohorts) montadas en solo lectura para la
    # cuota de referencia (api/cuotas_nba.py). Sin valor: no hay cuotas de NBA.
    nba_cohorts_dir: str | None = os.getenv("NBA_COHORTS_DIR") or None
    # Sellos de tenis del motor (`<raíz>/predictions/<event_key>.json`) montados en solo lectura para la
    # cuota de referencia (api/cuotas_tenis.py). Sin valor: no hay cuotas de tenis.
    tennis_sealed_dir: str | None = os.getenv("TENNIS_SEALED_DIR") or None
    # Respaldo de cuotas NBA/tenis con The Odds API histórico (ingest/cuotas_respaldo.py). La clave es la del plan
    # dedicado a NBA: solo la usa el comando por lotes, nunca la API web. La caché es un JSON que el overlay solo lee.
    odds_api_respaldo_key: str | None = os.getenv("ODDS_API_RESPALDO_KEY") or None
    cuotas_respaldo_cache: str | None = os.getenv("CUOTAS_RESPALDO_CACHE") or None
    # Pasada automática (`cuotas_respaldo --auto`, cron): apagada por defecto. Topes en créditos.
    cuotas_respaldo_auto: bool = os.getenv("CUOTAS_RESPALDO_AUTO", "0") == "1"
    cuotas_respaldo_auto_max: int = int(os.getenv("CUOTAS_RESPALDO_AUTO_MAX", "100"))
    cuotas_respaldo_diario: int = int(os.getenv("CUOTAS_RESPALDO_DIARIO", "300"))

    # Media vida del decaimiento temporal, en días: un partido de hace 270 días
    # pesa la mitad que uno de hoy. Elegida por walk-forward en la auditoría del
    # 2026-10-21 (120/180/220/270/365 sobre 11.920 partidos; 180, el valor
    # anterior, nunca se había medido). Ley et al. (2019) dan 360-480 con goles.
    decay_halflife_days: float = _f("DECAY_HALFLIFE_DAYS", 270.0)
    # Fuerza del ridge de ataque/defensa en PARTIDOS RECIENTES EQUIVALENTES
    # (ver `DixonColes`). 0,5 = un equipo con dos partidos queda a medio camino
    # de la media de su liga. Medido en la misma auditoría (0,5-1 lo mejor).
    ridge_partidos: float = _f("RIDGE_PARTIDOS", 0.5)
    # Mezcla goles/xG para el objetivo del modelo de fuerza. 0 = solo goles, 1 = solo xG.
    xg_blend: float = _f("XG_BLEND", 0.65)
    max_goals_matrix: int = _i("MAX_GOALS_MATRIX", 12)
    # Muestra EFECTIVA mínima por equipo para precificar un partido, medida en
    # PARTIDOS RECIENTES EQUIVALENTES: un partido de hoy suma 1 y uno de hace
    # una media vida suma 0,5. Por debajo, la fuerza
    # del equipo no la deciden sus datos sino el ridge y el centrado de la
    # liga, y el modelo produce una probabilidad extrema con total confianza.
    # Es el caso del club que vuelve a primera tras años fuera: sigue en el
    # índice con un parámetro rancio, así que NO cae a la media de su liga.
    min_effective_matches: float = _f("MIN_EFFECTIVE_MATCHES", 5.0)

    # --- Publicación de picks ---
    # APAGADO hasta que el criterio "casa blanda contra precio sharp"
    # (publish/picks.py) supere la puerta de CLV con la muestra de su sombra
    # (publish/shadow_sharp.py, visible en /model-card). Un pick sellado en la
    # cadena queda en el historial público para siempre: se enciende con
    # evidencia, no antes. Con esto apagado el job diario sigue prediciendo y
    # sellando las predicciones; solo se salta seleccionar, guardar y
    # difundir picks.
    publish_picks_enabled: bool = os.getenv("PUBLISH_PICKS_ENABLED", "0") in ("1", "true", "True")

    # --- Línea de alta probabilidad (publish/alta_prob.py, 2026-10-05) ---
    # Pronósticos ≥ 80 % de Pinnacle sin margen, aparte de los picks de valor.
    # Apagada hasta desplegar y verificar el primer lote sellado.
    alta_prob_enabled: bool = os.getenv("ALTA_PROB_ENABLED", "0") in ("1", "true", "True")
    # Fecha (AAAA-MM-DD) desde la que el control de calidad mide. Reanudar
    # tras una pausa es decisión del usuario: se mueve esta fecha.
    alta_prob_control_desde: str = os.getenv("ALTA_PROB_CONTROL_DESDE", "")
    # Ampliación 62-95 % (tabla alta_prob_ext, 2026-10-11). Apagada hasta aplicar
    # db/057 y desplegar con LOTE_ALTA_EXT_DESDE fijado.
    alta_prob_ext_enabled: bool = os.getenv("ALTA_PROB_EXT_ENABLED", "0") in ("1", "true", "True")

    # Seguimiento sin publicar de tarjetas (tabla tarjetas_seg, 2026-10-14). ENCENDIDO por
    # defecto: no publica nada y activarlo por entorno exigiría recrear el worker.
    tarjetas_seg_enabled: bool = os.getenv("TARJETAS_SEG_ENABLED", "1") in ("1", "true", "True")

    # Dónde descargar la app, que enseña la página de invitación `/i/CODIGO`. Vacío = sin botón
    # (la app aún no está en una tienda).
    app_download_url: str = os.getenv("APP_DOWNLOAD_URL", "")

    # --- Reto escalera (publish/escalera.py, 2026-10-08) ---
    # Apagado hasta desplegar con LOTE_ESCALERA_DESDE fijado: sin bloque en el
    # lote, un escalón no quedaría sellado.
    escalera_enabled: bool = os.getenv("ESCALERA_ENABLED", "0") in ("1", "true", "True")

    # --- Parley del día (publish/parley.py, 2026-10-11) ---
    # Apagado hasta desplegar con LOTE_PARLEY_DESDE fijado y el visto bueno
    # del usuario tras el ensayo en seco.
    parley_enabled: bool = os.getenv("PARLEY_ENABLED", "0") in ("1", "true", "True")

    # --- Criterio "casa blanda contra precio sharp" (publish/picks.py) ---
    # Casas donde apuestan los suscriptores (decisión del usuario 2026-09-23),
    # con los nombres canónicos de picks.canonical_book. Betway y 888sport no
    # los da hoy ninguna fuente capturada, pero forman parte de la lista.
    # 2026-09-28: + Betsson y Coolbet, confirmadas por el usuario (sus
    # clientes apuestan ahí). LeoVegas y Unibet NO: la sombra las mide igual
    # (todas las casas del snapshot), pero no cuentan para la puerta.
    # 2026-10-24: PropLine solo trae 1xbet de esas; el titular añadió las de
    # México (Codere MX, Strendus), España (Codere, Marca Apuestas, Sportium) y
    # las internacionales que aceptan clientes de Latinoamérica.
    soft_books: tuple[str, ...] = tuple(
        b.strip() for b in os.getenv(
            "SOFT_BOOKS", "bet365,betano,1xbet,william_hill,888sport,betway,"
            "betsson,coolbet,coderemx,strendus,codere,marcaapuestas,sportium,"
            "bovada,betonlineag,bookmaker_eu,heritage,jazzsports"
        ).split(",") if b.strip())
    # Edge BRUTO mínimo contra el precio justo de Pinnacle. 2% es el umbral
    # validado en los dos backtests (eval/soft_vs_sharp, ingest/odds_history).
    soft_min_edge_pct: float = _f("SOFT_MIN_EDGE_PCT", 2.0)
    # Antigüedad máxima del snapshot al decidir. API-Football llega a tener
    # precios de 19 h: un pick con un precio que ya no existe engaña al
    # suscriptor y hace trampa en el track record.
    soft_quote_max_age_hours: float = _f("SOFT_QUOTE_MAX_AGE_HOURS", 6.0)

    # --- Ráfagas para medir la latencia de las casas blandas (db/038) ---
    # Tope de créditos de The Odds API al mes (decisión del usuario,
    # 2026-10-03: 3.000 de 20.000). 0 las desactiva.
    rafagas_max_creditos_mes: int = int(_f("RAFAGAS_MAX_CREDITOS_MES", 3000))
    # ≤10 casas: así cada consulta cuesta 1 crédito. Pinnacle y Betfair como
    # referencia; Betsson, Coolbet, William Hill y 1xBet son de los clientes.
    rafagas_casas: tuple[str, ...] = tuple(
        b.strip() for b in os.getenv(
            "RAFAGAS_CASAS", "pinnacle,betfair_ex_eu,betsson,coolbet,williamhill,"
            "onexbet,marathonbet,unibet_se,leovegas_se,nordicbet"
        ).split(",") if b.strip())
    # Pocas ligas a propósito: cada liga con partidos cuesta ~1 crédito cada
    # 5 min durante todo su día de partidos.
    rafagas_ligas: tuple[str, ...] = tuple(
        b.strip() for b in os.getenv(
            "RAFAGAS_LIGAS", "gb.premier_league,es.laliga,mx.liga_mx"
        ).split(",") if b.strip())

    # --- Gestión de riesgo ---
    # El edge estimado está sesgado al alza por selección adversa:
    # solo apuestas donde el modelo discrepa, que es donde suele equivocarse.
    edge_shrinkage: float = _f("EDGE_SHRINKAGE", 0.55)
    # Parámetros de `model/uncertainty.py`, que se conserva como herramienta de
    # medición. Ya no participa en la selección de picks: el edge sale del
    # precio sharp, no del modelo.
    # Desviaciones tipicas de prudencia. 1.0 = se exige que el edge siga siendo
    # positivo una desviacion por debajo de su media.
    #
    # SIN CALIBRAR, y a proposito. Se intento el 2026-09-22 contra histórico
    # real point-in-time (12.183 filas, 4.061 partidos, tres cortes) y NO HAY
    # SEÑAL QUE CALIBRAR: la razon media/sd no separa apuestas buenas de malas
    # (correlacion con el acierto -0,047, quintiles no monotonos). El motivo
    # esta un nivel mas abajo: el edge CRUDO del modelo correlaciona -0,123 con
    # el acierto, o sea que es una ANTI-señal, y filtrar mas fuerte sobre una
    # señal negativa no puede mejorar nada.
    #
    # La rejilla de Z parecia subir el ROI de -8,5% a +2,5%, pero desde Z=0,4
    # todos los intervalos incluyen cero. Elegir 0,9 "porque la tabla sube" es
    # justo el error que ese experimento existia para evitar. Ver progreso.md.
    uncertainty_z: float = _f("UNCERTAINTY_Z", 1.0)
    # Muestras de Monte Carlo por seleccion candidata.
    uncertainty_draws: int = _i("UNCERTAINTY_DRAWS", 256)
    min_edge_pct: float = _f("MIN_EDGE_PCT", 3.0)       # tras shrinkage
    kelly_fraction: float = _f("KELLY_FRACTION", 0.20)
    max_stake_units: float = _f("MAX_STAKE_UNITS", 2.0)  # tope duro por apuesta
    max_picks_per_day: int = _i("MAX_PICKS_PER_DAY", 12)
    # De los picks seleccionados cada día, los de mayor edge van al tier 'free'
    # (el escaparate público en la web); el resto queda en 'paid'.
    free_picks_per_day: int = _i("FREE_PICKS_PER_DAY", 2)
    # Exposición bruta máxima del día (suma de stakes).
    max_daily_exposure: float = _f("MAX_DAILY_EXPOSURE", 10.0)
    # Riesgo máximo del portafolio: desviación típica del retorno conjunto del
    # lote, YA con correlación entre picks. Es el tope que de verdad protege;
    # la suma bruta trata 12 apuestas correlacionadas como si fueran
    # independientes. Ver publish/picks.py::apply_portfolio_limits.
    max_portfolio_risk: float = _f("MAX_PORTFOLIO_RISK", 4.0)

    # --- Fusión con el mercado (ponderación óptima) ---
    # DESACTIVADO por defecto porque cambia el producto, no solo el código:
    # mezclar con el mercado acerca tus probabilidades a las suyas y REDUCE el
    # edge que encuentras, así que publicarás menos picks al día. Es el
    # comportamiento correcto (esos edges eran en parte ilusorios), pero la
    # decisión de asumir ese cambio es de negocio. El peso se estima y se
    # reporta SIEMPRE en `/model-card` aunque esto esté apagado.
    meta_blend_enabled: bool = os.getenv("META_BLEND_ENABLED", "0") in ("1", "true", "True")

    # --- Ajuste de lambdas por altitud (qf.model.ajuste_altitud, 2026-10-19) ---
    # off     no calcula nada.
    # sombra  calcula el ajuste y lo anota en cada predicción (data_completeness.ajuste_altitud) SIN alterar los lambdas
    #         publicados: la evidencia es débil y lo sellado es público e inmutable. Es el valor por defecto.
    # activo  aplica el ajuste a los lambdas antes de calcular todos los mercados.
    ajuste_altitud_modo: str = os.getenv("AJUSTE_ALTITUD_MODO", "sombra").lower()

    # Ajuste por el once confirmado (impacto por jugador), solo en la predicción FINAL del sello por partido:
    #   off     no lo calcula.
    #   sombra  calcula el factor y lo anota en data_completeness.sello_tardio.ajuste_xi sin tocar los lambdas (por defecto).
    # (`activo` aún no existe: hace falta medirlo hacia adelante con `python -m qf.model.ajuste_xi --medir`.)
    ajuste_xi_modo: str = os.getenv("AJUSTE_XI_MODO", "sombra").lower()

    # --- Modelo de residuo (GBM sobre la diferencia modelo-mercado) ---
    # DESACTIVADO por defecto a propósito: corrige solo el 1X2, así que
    # mientras esté activo ese mercado deja de ser perfectamente coherente con
    # el resto del paquete de pricing. Enciéndelo cuando tengas histórico con
    # cuotas de cierre y su puerta de validación lo apruebe.
    residual_enabled: bool = os.getenv("RESIDUAL_ENABLED", "0") in ("1", "true", "True")
    # Cuánto se aplica de la corrección del GBM. 1.0 = completa. Se queda corto
    # a propósito: un GBM sobre unos miles de filas está sobreajustado aunque
    # la validación diga que no.
    residual_shrink: float = _f("RESIDUAL_SHRINK", 0.5)

    # Casa de referencia para el precio "justo" y para el CLV.
    sharp_book: str = os.getenv("SHARP_BOOK", "pinnacle")
    # Método de eliminación de margen: shin | power | additive | multiplicative
    devig_method: str = os.getenv("DEVIG_METHOD", "shin")

    # --- Rate limiting (Redis, ventana fija por IP) ---
    rate_limit_default_per_minute: int = _i("RATE_LIMIT_DEFAULT_PER_MINUTE", 60)

    # "development" habilita el origen CORS de Vite en localhost; cualquier
    # otro valor (el default, para producción) lo deja fuera.
    app_env: str = os.getenv("APP_ENV", "production")

    # --- Captura de cuotas ---
    # Ventanas objetivo en minutos antes del kickoff. Solo se llama a la API
    # cuando un partido entra en una ventana aún no capturada (ahorro de cuota).
    odds_windows: tuple = field(default=(
        ("t72", 4320, 4200),
        ("t24", 1440, 1380),
        ("t6",   360,  330),
        ("t1",    60,   50),
        ("post_xi", 45, 15),
        ("close", 12,    3),
    ))


settings = Settings()
