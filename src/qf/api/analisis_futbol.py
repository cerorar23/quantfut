"""Análisis del destacado de fútbol: casillas según el mercado y resumen redactado con APIMart.

Decisión del titular (2026-11-17): la tarjeta del pronóstico destacado muestra los datos que de verdad ayudan a
ese mercado, no siempre los mismos. Cada mercado pertenece a una RECETA con una lista de prioridad; se toman las
tres primeras casillas con dato (la proyección va primero) y una casilla nunca se rellena con «—».

El resumen lo redacta APIMart en los 6 idiomas, pero las cifras salen solo de la ficha: si el texto contiene un
número que no está en los datos entregados se descarta y la app usa su plantilla fija. Se genera una sola vez por
(partido, mercado, datos) y fuera de la petición: el primer visitante no espera a la IA.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ..db import execute, query_one
from . import apimart

log = logging.getLogger(__name__)

IDIOMAS = ("es", "en", "pt", "fr", "it", "de")
NOMBRE_IDIOMA = {"es": "Spanish", "en": "English", "pt": "Brazilian Portuguese", "fr": "French",
                 "it": "Italian", "de": "German"}
CASILLAS = 3                 # casillas 2, 3 y 4 (la 1 es siempre la probabilidad)
MIN_PARTIDOS = 3             # por debajo, un porcentaje de casa/fuera engaña
MAX_TEXTO = 420

RECETAS = {"h2h": "resultado", "double_chance": "resultado", "spreads": "resultado",
           "totals": "goles", "btts": "goles",
           "team_totals_home": "equipo", "team_totals_away": "equipo"}
PRIORIDAD = {"resultado": ("xg", "empate", "forma", "xgd", "locvis"),
             "goles": ("xg", "tendencia", "ambos", "goles_partido", "locvis", "forma"),
             "equipo": ("xg_equipo", "marca", "concede", "forma", "locvis"),
             "general": ("locvis", "forma", "xgd")}


def receta_de(market: str | None) -> str:
    return RECETAS.get(market or "", "general")


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _bloque(ficha: dict, lado: str, tipo: str) -> dict:
    return ((ficha.get(lado) or {}).get("promedios") or {}).get(tipo) or {}


def _par(ficha: dict, tipo_a: str, tipo_b: str, campo: str, minimo: int = MIN_PARTIDOS):
    """(valor local, valor visitante, n local, n visitante) o None si falta dato o hay pocos partidos."""
    a, b = _bloque(ficha, "local", tipo_a), _bloque(ficha, "visitante", tipo_b)
    va, vb = _num(a.get(campo)), _num(b.get(campo))
    if va is None or vb is None or (a.get("n") or 0) < minimo or (b.get("n") or 0) < minimo:
        return None
    return va, vb, int(a["n"]), int(b["n"])


def _casilla(id_: str, ctx: dict) -> dict | None:
    ficha, lam_mu, market, line = ctx["ficha"], ctx["lam_mu"], ctx["market"], ctx["line"]
    if id_ == "xg":
        if not lam_mu:
            return None
        return {"id": "xg", "total": round(lam_mu[0] + lam_mu[1], 2), "a": round(lam_mu[0], 2),
                "b": round(lam_mu[1], 2)}
    if id_ == "xg_equipo":
        if not lam_mu:
            return None
        lado = "a" if market == "team_totals_home" else "b"
        return {"id": "xg_equipo", "a": round(lam_mu[0 if lado == "a" else 1], 2), "equipo": lado}
    if id_ == "empate":
        par = _par(ficha, "casa", "fuera", "pct_empates")
        if not par:
            return None
        liga = _num(((ficha.get("partido") or {}).get("liga") or {}).get("pct_empates"))
        out = {"id": "empate", "a": round(par[0]), "b": round(par[1]), "n_a": par[2], "n_b": par[3]}
        if liga is not None:
            out["liga"] = round(liga)
        return out
    if id_ == "forma":
        ra = ((ficha.get("local") or {}).get("forma") or {}).get("resumen") or {}
        rb = ((ficha.get("visitante") or {}).get("forma") or {}).get("resumen") or {}
        if (ra.get("n") or 0) < MIN_PARTIDOS or (rb.get("n") or 0) < MIN_PARTIDOS:
            return None
        return {"id": "forma", "a": ra["puntos"], "b": rb["puntos"], "n_a": ra["n"], "n_b": rb["n"]}
    if id_ == "xgd":
        out = {"id": "xgd"}
        for lado, clave in (("local", "a"), ("visitante", "b")):
            blq = _bloque(ficha, lado, "todos")
            f, c = _num(blq.get("xg_favor")), _num(blq.get("xg_contra"))
            if f is None or c is None or (blq.get("n") or 0) < MIN_PARTIDOS * 2:
                return None
            out[clave] = round(f - c, 2)
            out["n_" + clave] = int(blq["n"])
        return out
    if id_ == "tendencia":
        if market != "totals" or line != 2.5:
            return None
        par = _par(ficha, "todos", "todos", "pct_mas_2_5", MIN_PARTIDOS * 2)
        return {"id": "tendencia", "a": round(par[0]), "b": round(par[1]), "n_a": par[2], "n_b": par[3]} if par else None
    if id_ == "ambos":
        par = _par(ficha, "todos", "todos", "pct_ambos_marcan", MIN_PARTIDOS * 2)
        return {"id": "ambos", "a": round(par[0]), "b": round(par[1]), "n_a": par[2], "n_b": par[3]} if par else None
    if id_ == "goles_partido":
        a, b = _bloque(ficha, "local", "todos"), _bloque(ficha, "visitante", "todos")
        v = [_num(a.get("goles_favor")), _num(a.get("goles_contra")), _num(b.get("goles_favor")),
             _num(b.get("goles_contra"))]
        if None in v or (a.get("n") or 0) < MIN_PARTIDOS * 2 or (b.get("n") or 0) < MIN_PARTIDOS * 2:
            return None
        return {"id": "goles_partido", "a": round(v[0] + v[1], 1), "b": round(v[2] + v[3], 1),
                "n_a": int(a["n"]), "n_b": int(b["n"])}
    if id_ == "locvis":
        par = _par(ficha, "casa", "fuera", "pct_victorias")
        return {"id": "locvis", "a": round(par[0]), "b": round(par[1]), "n_a": par[2], "n_b": par[3]} if par else None
    if id_ in ("marca", "concede"):
        propio, rival = ("local", "visitante") if market == "team_totals_home" else ("visitante", "local")
        blq = _bloque(ficha, propio if id_ == "marca" else rival, "todos")
        v = _num(blq.get("pct_marca" if id_ == "marca" else "goles_contra"))
        if v is None or (blq.get("n") or 0) < MIN_PARTIDOS * 2:
            return None
        return {"id": id_, "a": round(v) if id_ == "marca" else round(v, 1), "n_a": int(blq["n"]),
                "equipo": "a" if propio == "local" else "b"}
    return None


def casillas(pick: dict, ficha: dict, lam_mu: tuple | None) -> tuple[str, list[dict]]:
    """(receta, hasta 3 casillas). La receta fija el orden de prioridad; lo que no tiene dato se salta."""
    market = pick.get("market")
    receta = receta_de(market)
    ctx = {"ficha": ficha, "lam_mu": lam_mu, "market": market, "line": _num(pick.get("line"))}
    out, vistos = [], set()
    for id_ in PRIORIDAD[receta] + PRIORIDAD["general"]:
        if id_ in vistos:
            continue
        vistos.add(id_)
        c = _casilla(id_, ctx)
        if c:
            out.append(c)
        if len(out) == CASILLAS:
            break
    return receta, out


# --- resumen redactado -----------------------------------------------------------------------------------

_NUM = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?![\w])")


def _numeros(obj: Any, acc: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)) and math.isfinite(obj):
        acc.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numeros(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numeros(v, acc)


def cifras_validas(texto: str, hechos: dict) -> bool:
    """Todo número del texto debe estar en los hechos (con la tolerancia de un redondeo a 1 decimal)."""
    permitidos: set[float] = set()
    _numeros(hechos, permitidos)
    permitidos |= {0.0, 1.0, 100.0}
    for crudo in _NUM.findall(texto):
        valor = float(crudo.replace(",", "."))
        if not any(abs(valor - p) <= 0.051 or abs(valor - round(p)) < 1e-9 for p in permitidos):
            return False
    return True


def hechos_de(pick: dict, ficha: dict, receta: str, tarjetas: list[dict]) -> dict:
    prob = _num(pick.get("prob"))
    justa = round(1 / prob, 2) if prob else None
    publicada = _num(pick.get("ref_price"))
    return {"partido": f"{(ficha.get('local') or {}).get('nombre')} vs {(ficha.get('visitante') or {}).get('nombre')}",
            "pronostico": pick.get("texto"), "mercado": receta,
            "probabilidad_pct": round(prob * 100) if prob else None, "cuota_justa": justa,
            "cuota_publicada": publicada,
            "precio": None if not (justa and publicada) else ("por encima de la justa" if publicada >= justa
                                                              else "por debajo de la justa"),
            "datos": tarjetas}


PROMPT = (
    "You write the short 'forecast summary' shown on a football betting-analytics card. "
    "Write in these languages: {idiomas}. For each language write 2 or 3 sentences, at most {max} characters. "
    "Open with the strong conclusion (a hook a reader would want to keep reading), then justify it with the figures. "
    "Use ONLY numbers that appear in the data; never invent, derive or round to a new number. "
    "If 'precio' says the published odds are below the fair odds, close by saying the appeal is in the probability, "
    "not the price; if above, say the price also supports it. Never promise or guarantee a result. "
    "In each 'datos' item a/b are the home/away team values (a/b = home/away; n_a/n_b are matches counted). "
    "Return ONLY a JSON object with the language codes as keys.\nDATA:\n{datos}"
)


def redactar(hechos: dict) -> dict[str, str] | None:
    cfg = _config()
    if not cfg:
        return None
    prompt = PROMPT.format(idiomas=", ".join(f"{k} ({NOMBRE_IDIOMA[k]})" for k in IDIOMAS), max=MAX_TEXTO,
                           datos=json.dumps(hechos, ensure_ascii=False))
    res = apimart._chat_completion(api_key=cfg["api_key"], base_url=cfg["base_url"], model=cfg["model"],
                                   messages=[{"role": "user", "content": prompt}], expect_json=True,
                                   max_tokens=1200, timeout=60.0)
    data = apimart._extract_json_object(res["content"])
    textos = {}
    for k in IDIOMAS:
        t = str(data.get(k) or "").strip()
        if not t or len(t) > MAX_TEXTO + 80 or not cifras_validas(t, hechos):
            log.warning("resumen %s descartado (vacío, largo o con cifras ajenas)", k)
            return None
        textos[k] = t
    return textos


def _config() -> dict | None:
    from . import web_config
    try:
        cfg = web_config.get_apimart_runtime_config()
    except Exception:  # noqa: BLE001 - sin configuración no hay resumen, la app usa su plantilla
        return None
    return cfg if cfg.get("api_key") else None


# --- caché en base + generación fuera de la petición --------------------------------------------------------

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analisis")
_en_curso: set[str] = set()
_fallos: dict[str, float] = {}
_LOCK = threading.Lock()
REINTENTO_S = 3600.0


def _clave(match_id: str, pick: dict) -> str:
    return f"{pick.get('market')}|{pick.get('selection')}|{pick.get('line')}"


def _hash(hechos: dict) -> str:
    return hashlib.sha256(json.dumps(hechos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:32]


def _leer(match_id: str, clave: str, h: str) -> dict | None:
    row = query_one("SELECT textos FROM analisis_resumen WHERE match_id = %s AND clave = %s AND datos_hash = %s",
                    (match_id, clave, h))
    return row["textos"] if row else None


def _generar(match_id: str, clave: str, h: str, hechos: dict) -> None:
    k = f"{match_id}|{clave}|{h}"
    try:
        textos = redactar(hechos)
        if textos:
            execute("INSERT INTO analisis_resumen (match_id, clave, datos_hash, textos, modelo) "
                    "VALUES (%s, %s, %s, %s::jsonb, %s) ON CONFLICT DO NOTHING",
                    (match_id, clave, h, json.dumps(textos, ensure_ascii=False),
                     (_config() or {}).get("model") or ""))
        else:
            _fallos[k] = time.monotonic()
    except Exception as exc:  # noqa: BLE001 - la IA es un extra
        log.warning("resumen de %s no generado: %s", match_id, apimart.redact_secrets(str(exc)))
        _fallos[k] = time.monotonic()
    finally:
        with _LOCK:
            _en_curso.discard(k)


def construir(match_id: str, pick: dict, ficha: dict, lam_mu: tuple | None) -> dict | None:
    """Bloque `analisis` del destacado: receta, casillas y, si ya está generado, el resumen por idioma."""
    receta, tarjetas = casillas(pick, ficha, lam_mu)
    if not tarjetas:
        return None
    out: dict[str, Any] = {"receta": receta, "casillas": tarjetas, "resumen": None}
    try:
        hechos = hechos_de(pick, ficha, receta, tarjetas)
        clave, h = _clave(match_id, pick), _hash(hechos)
        out["resumen"] = _leer(match_id, clave, h)
        k = f"{match_id}|{clave}|{h}"
        if out["resumen"] is None and _config():
            with _LOCK:
                reciente = time.monotonic() - _fallos.get(k, -REINTENTO_S) < REINTENTO_S
                if k not in _en_curso and not reciente:
                    _en_curso.add(k)
                    _POOL.submit(_generar, match_id, clave, h, hechos)
    except Exception:  # noqa: BLE001 - sin resumen la app sigue con las casillas y su plantilla
        log.exception("resumen del partido %s", match_id)
    return out
