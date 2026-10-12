"""
Orquestador diario. Es el único proceso que publica al mundo.

Orden ESTRICTO, no negociable:
  1. Generar predicciones (INSERT inmutable)
  2. Seleccionar picks (INSERT inmutable)
  3. SELLAR la cadena de hashes
  4. Solo entonces publicar en Telegram/web

Si publicas antes de sellar, el hash deja de probar nada. Si el paso 3 falla,
el 4 no se ejecuta: mejor no publicar hoy que publicar sin prueba.

Cron sugerido: 08:00 hora local, antes del primer kickoff europeo.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

import numpy as np

from ..config import settings
from ..db import query, query_one
from ..model.dixon_coles import DixonColes
from ..model.devig import consensus_devig
from . import alta_prob_datos, alta_prob_ext
from . import escalera_datos
from . import parley_datos
from . import picks as pk
from . import telegram as tg
from .hashchain import seal

log = logging.getLogger(__name__)


def _shadow_gate_allows_publication() -> tuple[bool, list[str]]:
    """El interruptor de despliegue no sustituye la evidencia de CLV."""
    try:
        from .shadow_sharp import report
        gate = report()["gate"]
        return gate["authorized"] is True, list(gate.get("reasons") or [])
    except Exception as exc:  # noqa: BLE001
        log.exception("No se pudo comprobar la puerta de la sombra sharp: %s", exc)
        return False, ["Puerta de CLV no disponible"]


def _upcoming(hours: int = 36) -> list[dict]:
    return query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc,
                  m.home_team_id, m.away_team_id,
                  th.canonical_name AS home_team, ta.canonical_name AS away_team,
                  -- Liga doméstica de cada equipo. En un partido de copa
                  -- europea NO coincide con m.league_id, y es la que el modelo
                  -- usa para encontrar al equipo.
                  th.league_id AS home_league, ta.league_id AS away_league,
                  (SELECT count(*) FROM matches x
                   WHERE x.status='finished'
                     AND (x.home_team_id = m.home_team_id OR x.away_team_id = m.home_team_id)
                  ) AS home_history,
                  (SELECT count(*) FROM matches x
                   WHERE x.status='finished'
                     AND (x.home_team_id = m.away_team_id OR x.away_team_id = m.away_team_id)
                  ) AS away_history
           FROM matches m
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           -- Las ligas "solo sharp" (db/023) no se predicen: el modelo no
           -- conoce a sus equipos y lo sellado aquí es público e inmutable.
           JOIN leagues lg ON lg.league_id = m.league_id AND lg.model_enabled
           -- Tampoco un partido de copa con un equipo de esas ligas (un turco
           -- o un suizo en Champions): se sellaría con ataque y defensa 0.
           JOIN leagues lh ON lh.league_id = th.league_id AND lh.model_enabled
           JOIN leagues la ON la.league_id = ta.league_id AND la.model_enabled
           WHERE m.status = 'scheduled'
             AND m.kickoff_utc BETWEEN now() AND now() + make_interval(hours => %s)
           ORDER BY m.kickoff_utc""",
        (hours,),
    )


def _sharp_only_upcoming(hours: int = 36) -> list[dict]:
    """
    Partidos de ligas "solo sharp" (db/023): entran en la selección de picks
    SIN predicción, porque el criterio de precio no la necesita y el modelo no
    conoce a sus equipos. No se predicen ni se sella ninguna predicción suya.
    Misma forma que una predicción para `picks.select_daily`.
    """
    rows = query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc,
                  th.canonical_name AS home_team, ta.canonical_name AS away_team
           FROM matches m
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           JOIN leagues lg ON lg.league_id = m.league_id
                          AND lg.active AND NOT lg.model_enabled
           WHERE m.status = 'scheduled'
             AND m.kickoff_utc BETWEEN now() AND now() + make_interval(hours => %s)
           ORDER BY m.kickoff_utc""",
        (hours,),
    )
    return [{"prediction_id": None, "match_id": r["match_id"], "markets": {},
             "kickoff_utc": r["kickoff_utc"], "league_id": r["league_id"],
             "teams": (r["home_team"], r["away_team"])} for r in rows]


def _confidence(home_hist: int, away_hist: int, has_odds: bool,
                home_eff: float | None = None,
                away_eff: float | None = None) -> str:
    """Comunicar cuándo el modelo sabe poco es señal de seriedad, no de debilidad.

    `home_hist`/`away_hist` cuentan partidos DE TODA LA VIDA, y el modelo pesa
    con media vida de 180 días: son dos magnitudes distintas y usar la primera
    para hablar de la segunda es justo el fallo que esto cierra. Un club que
    vuelve a primera tras años fuera tiene cientos de partidos en la base
    —tier `high` con la regla antigua— y una muestra efectiva de 0,0000. Su
    fuerza no la deciden sus datos, la deciden el ridge y el centrado de la
    liga, así que el modelo le pone una probabilidad extrema y la sostiene con
    total confianza. Medido el 2026-09-22 sobre cuotas reales: Hull, que no
    juega desde 2017, salió a 0,9061 contra un mercado de 0,4659 y se llevó el
    stake máximo.

    Devolver `low` no descarta la predicción: se guarda, se sirve por la API y
    queda auditable. Lo que hace es sacarla del universo de picks en `run()`,
    que ya filtra por este mismo campo.
    """
    if not has_odds:
        return "low"
    if home_eff is not None and away_eff is not None:
        if min(home_eff, away_eff) < settings.min_effective_matches:
            return "low"
    if min(home_hist, away_hist) < 15:
        return "low"
    if min(home_hist, away_hist) < 40:
        return "medium"
    return "high"


def _consensus_totals(match_id: str) -> dict[str, list[float]]:
    """
    Consenso des-margenado de over/under por línea: {"2.5": [p_over, p_under]}.

    Todas las líneas que cotiza el modelo son de media unidad (2.5, 3.5...),
    así que no hay empuje (push) que repartir y el mercado es binario limpio.
    """
    rows = query(
        """SELECT DISTINCT ON (bookmaker, line, selection)
                  bookmaker, line, selection, price
           FROM odds_snapshots
           WHERE match_id = %s AND market = 'totals' AND line IS NOT NULL
           ORDER BY bookmaker, line, selection, captured_at DESC""",
        (match_id,),
    )
    por_linea: dict[float, dict[str, dict[str, float]]] = {}
    for r in rows:
        por_linea.setdefault(float(r["line"]), {}) \
                 .setdefault(r["bookmaker"], {})[r["selection"]] = float(r["price"])

    out: dict[str, list[float]] = {}
    for line, quotes in por_linea.items():
        quotes = {b: q for b, q in quotes.items() if set(q) == {"over", "under"}}
        if not quotes:
            continue
        cons = consensus_devig(quotes, settings.devig_method, settings.sharp_book)
        if cons.get("over") and cons.get("under"):
            out[f"{line}"] = [cons["over"], cons["under"]]
    return out


def _apply_blend(meta, markets: dict, cons: dict, match_id: str,
                 league_id: str | None) -> list[str]:
    """
    Mezcla las probabilidades del modelo con el mercado usando el peso
    estimado. Devuelve la lista de mercados efectivamente mezclados.

    Solo se mezcla donde HAY consenso de mercado: 1X2 y totales. El hándicap
    asiático queda fuera porque sus líneas enteras tienen empuje y la mezcla
    binaria no está bien definida ahí sin tratarlo aparte.

    La mezcla solo cambia las probabilidades guardadas en `predictions`: desde
    el 2026-09-23 la selección de picks no las usa (ver publish/picks.py).
    """
    blended: list[str] = []

    if cons.get("home") and cons.get("draw") and cons.get("away"):
        p = [markets["1x2"]["home"], markets["1x2"]["draw"], markets["1x2"]["away"]]
        k = [cons["home"], cons["draw"], cons["away"]]
        out = meta.blend(np.array(p), np.array(k), league_id)
        markets["1x2"] = {"home": float(out[0]), "draw": float(out[1]),
                          "away": float(out[2])}
        blended.append("h2h")

    tot = _consensus_totals(match_id)
    if tot:
        tocados = 0
        for line, (p_over_mkt, p_under_mkt) in tot.items():
            m = markets.get("totals", {}).get(line)
            if not m:
                continue
            out = meta.blend(np.array([m["over"], m["under"]]),
                             np.array([p_over_mkt, p_under_mkt]), league_id)
            m["over"], m["under"] = float(out[0]), float(out[1])
            tocados += 1
        if tocados:
            blended.append("totals")

    return blended


def _rest_features(match: dict) -> dict:
    """
    Descanso y congestión de calendario de ambos equipos, contando SOLO
    partidos anteriores al kickoff de este.

    Es el punto donde es más fácil colar una fuga: basta con olvidar el filtro
    `kickoff_utc < este_kickoff` para que el modelo "sepa" cuántos partidos
    jugará el equipo después, que en producción es información que no existe.
    """
    out = {}
    for side, team_id in (("home", match["home_team_id"]),
                          ("away", match["away_team_id"])):
        row = query_one(
            """SELECT
                 MAX(x.kickoff_utc) AS last_ko,
                 count(*) FILTER (
                     WHERE x.kickoff_utc >= %s - interval '14 days'
                 ) AS m14
               FROM matches x
               WHERE x.status = 'finished'
                 AND (x.home_team_id = %s OR x.away_team_id = %s)
                 AND x.kickoff_utc < %s""",
            (match["kickoff_utc"], team_id, team_id, match["kickoff_utc"]),
        ) or {}
        last_ko = row.get("last_ko")
        rest = ((match["kickoff_utc"] - last_ko).days
                if last_ko is not None else float("nan"))
        out[f"{side}_rest_days"] = min(max(rest, 0), 60) if rest == rest else float("nan")
        out[f"{side}_matches_14d"] = int(row.get("m14") or 0)
    out["rest_diff"] = out["home_rest_days"] - out["away_rest_days"]
    return out


def _apply_residual(residual, match: dict, p1x2: dict, cons: dict,
                    meta: dict) -> dict | None:
    """
    Aplica la corrección de residuo al 1X2 de un partido.

    Devuelve None (y no corrige nada) si falta cualquier dato de entrada: sin
    consenso de mercado no hay residuo que corregir, y sin descanso conocido
    el GBM extrapolaría fuera del rango en el que se entrenó.
    """
    import pandas as pd

    try:
        feats = _rest_features(match)
    except Exception as exc:  # noqa: BLE001
        log.warning("Sin features de descanso para %s: %s", match["match_id"], exc)
        return None

    row = {
        "p_model_home": p1x2["home"],
        "p_market_home": cons["home"],
        "logit_gap": float(np.log(max(p1x2["home"], 1e-6) / max(1 - p1x2["home"], 1e-6))
                           - np.log(max(cons["home"], 1e-6) / max(1 - cons["home"], 1e-6))),
        "month": match["kickoff_utc"].month,
        "both_known": float(meta["both_teams_known"]),
        **feats,
    }
    df = pd.DataFrame([row])
    probs = np.array([[p1x2["home"], p1x2["draw"], p1x2["away"]]], dtype=float)
    probs = probs / probs.sum()
    out = residual.adjust(df, probs)[0]
    return {"home": float(out[0]), "draw": float(out[1]), "away": float(out[2])}


def _load_meta(version: str):
    """
    Mezcla con el mercado. Opcional y desactivada por defecto: ver la nota de
    consecuencia de negocio en `model/meta.py`.
    """
    from ..model.meta import MetaBlender

    if not settings.meta_blend_enabled:
        return MetaBlender.identity()
    path = f"{settings.artifact_dir}/meta_{version}.pkl"
    try:
        mb = MetaBlender.load(path)
    except FileNotFoundError:
        log.warning("META_BLEND_ENABLED=1 pero no hay artefacto en %s.", path)
        return MetaBlender.identity()
    if not mb.is_active:
        log.warning("El peso modelo/mercado existe pero no superó su validación.")
        return MetaBlender.identity()
    log.info("Mezcla con el mercado activa: w=%.3f", mb.params.w_model)
    return mb


def _load_residual(version: str):
    """
    El modelo de residuo es OPCIONAL y está DESACTIVADO por defecto.

    Dos razones para no encenderlo solo: (1) necesita histórico con cuotas de
    cierre para entrenarse con sentido, y (2) a diferencia del calibrador,
    corrige únicamente el 1X2, así que mientras esté activo ese mercado deja
    de ser perfectamente coherente con el resto del paquete de pricing. Es una
    decisión de producto, no técnica, y por eso la toma una variable de
    entorno (RESIDUAL_ENABLED) y no el código.
    """
    from ..model.residual import ResidualModel

    if not settings.residual_enabled:
        return ResidualModel.disabled()
    path = f"{settings.artifact_dir}/res_{version}.pkl"
    try:
        rm = ResidualModel.load(path)
    except FileNotFoundError:
        log.warning("RESIDUAL_ENABLED=1 pero no hay artefacto en %s.", path)
        return ResidualModel.disabled()
    if not rm.is_active:
        log.warning("El modelo de residuo existe pero no superó su validación.")
        return ResidualModel.disabled()
    log.info("Modelo de residuo activo: %s", path)
    return rm


def _consensus(match_id: str) -> dict:
    rows = query(
        """SELECT DISTINCT ON (bookmaker, selection) bookmaker, selection, price
           FROM odds_snapshots WHERE match_id = %s AND market = 'h2h'
           ORDER BY bookmaker, selection, captured_at DESC""",
        (match_id,),
    )
    q: dict[str, dict[str, float]] = {}
    for r in rows:
        q.setdefault(r["bookmaker"], {})[r["selection"]] = float(r["price"])
    q = {b: v for b, v in q.items() if set(v) == {"home", "draw", "away"}}
    return consensus_devig(q, settings.devig_method, settings.sharp_book)


def _active_artifact() -> tuple[str, str]:
    """
    Ruta del modelo ACTIVO y su versión, desde `model_artifacts`.

    Deliberadamente no se construye la ruta desde `settings.model_version`:
    `train.py` versiona por fecha ("2026.09.21") mientras que MODEL_VERSION es
    una variable de entorno fija, así que el primer reentrenamiento dejaría al
    job diario cargando un artefacto viejo —o ninguno— sin avisar. La tabla es
    la única fuente de verdad de qué modelo está desplegado.
    """
    row = query_one(
        """SELECT model_version, artifact_uri, params FROM model_artifacts
           WHERE is_active LIMIT 1"""
    )
    if not row:
        raise RuntimeError(
            "No hay ningún modelo activo en model_artifacts. "
            "Ejecuta `python -m qf.model.train` antes del job diario."
        )
    return row["artifact_uri"], row["model_version"]


def _load_calibrator(version: str):
    """
    El calibrador es OPCIONAL. Si no existe (todavía no hay datos suficientes,
    o el ajuste no superó su puerta de validación), se usa la identidad y el
    sistema publica sin calibrar. Preferimos no calibrar a calibrar mal.
    """
    from ..model.calibration import LambdaCalibrator

    path = f"{settings.artifact_dir}/cal_{version}.pkl"
    try:
        cal = LambdaCalibrator.load(path)
        log.info("Calibrador cargado: %s", path)
        return cal
    except FileNotFoundError:
        log.warning("Sin calibrador en %s. Se publica sin calibrar.", path)
        return LambdaCalibrator.identity()


def generate_predictions(model_path: str | None = None) -> list[dict]:
    from ..db import conn
    from ..model.pricing import price_all_markets

    if model_path:
        version = settings.model_version
    else:
        model_path, version = _active_artifact()
    model = DixonColes.load(model_path)
    calibrator = _load_calibrator(version)
    meta = _load_meta(version)
    residual = _load_residual(version)

    # Exclusión mutua: los dos fusionan el modelo con el mercado (el residuo
    # usa la diferencia modelo-mercado como feature). Aplicar ambos contaría
    # la información del mercado dos veces y encogería el edge de más.
    if meta.is_active and residual.is_active:
        log.warning(
            "META_BLEND_ENABLED y RESIDUAL_ENABLED están activos a la vez. "
            "Ambos fusionan con el mercado; se usa solo la mezcla ponderada, "
            "que es la más robusta. Desactiva uno de los dos."
        )
        residual = residual.__class__.disabled()

    matches = _upcoming()
    out: list[dict] = []

    for m in matches:
        try:
            # La calibración se aplica sobre las INTENSIDADES y se vuelve a
            # derivar toda la matriz de marcadores. Así el 1X2 calibrado y el
            # over/under calibrado siguen siendo coherentes entre sí; corregir
            # solo el 1X2 los dejaría contradiciéndose.
            lam, mu = model.lambdas(m["home_team"], m["away_team"],
                                    m["league_id"],
                                    m["home_league"], m["away_league"])
            lam_c, mu_c = calibrator.apply(lam, mu)
            markets = price_all_markets(lam_c, mu_c, model.params.rho,
                                        model.max_goals)
            markets["_meta"] = {
                "home_lambda": lam_c, "away_lambda": mu_c,
                "home_lambda_raw": lam, "away_lambda_raw": mu,
                "rho": model.params.rho,
                "calibrated": not calibrator.params.is_identity,
                "both_teams_known": model.knows(m["home_team"], m["away_team"],
                                                m["league_id"],
                                                m["home_league"],
                                                m["away_league"]),
                "home_effective_n": model.effective_n(
                    m["home_team"], m["home_league"] or m["league_id"]),
                "away_effective_n": model.effective_n(
                    m["away_team"], m["away_league"] or m["league_id"]),
            }
        except Exception as exc:  # noqa: BLE001
            log.error("Predicción fallida %s: %s", m["match_id"], exc)
            continue

        meta_pred = markets.pop("_meta")
        cons = _consensus(m["match_id"])
        tier = _confidence(int(m["home_history"]), int(m["away_history"]), bool(cons),
                           meta_pred.get("home_effective_n"),
                           meta_pred.get("away_effective_n"))

        # Fusión con el mercado usando el peso estimado. Va ANTES del residuo
        # y antes de cualquier cálculo de edge: el edge debe calcularse sobre
        # la probabilidad que de verdad creemos, no sobre la cruda.
        blended: list[str] = []
        if meta.is_active:
            blended = _apply_blend(meta, markets, cons, m["match_id"],
                                   m["league_id"])
            if blended:
                meta_info = {"blended": blended,
                             "w_model": meta.weight_for(m["league_id"])}
            else:
                meta_info = None
        else:
            meta_info = None

        # Corrección de residuo (solo 1X2, solo si está habilitada y validada).
        if residual.is_active and cons.get("home"):
            adjusted = _apply_residual(residual, m, markets["1x2"], cons, meta_pred)
            if adjusted is not None:
                markets["1x2"] = adjusted
                meta_pred["residual_applied"] = True

        with conn() as c, c.cursor() as cur:
            cur.execute(
                """INSERT INTO predictions
                     (match_id, model_version, fs_version, home_lambda,
                      away_lambda, rho, markets, market_consensus,
                      confidence_tier, data_completeness)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   RETURNING prediction_id""",
                (m["match_id"], version, settings.fs_version,
                 meta_pred["home_lambda"], meta_pred["away_lambda"],
                 meta_pred["rho"],
                 json.dumps(markets), json.dumps(cons), tier,
                 json.dumps({"home_history": int(m["home_history"]),
                             "away_history": int(m["away_history"]),
                             "both_teams_known": meta_pred["both_teams_known"],
                             "bookmakers_seen": len(cons),
                             "calibrated": meta_pred.get("calibrated", False),
                             "market_blend": meta_info,
                             "residual_applied": meta_pred.get("residual_applied",
                                                               False)})),
            )
            pid = cur.fetchone()["prediction_id"]

        out.append({"prediction_id": pid, "match_id": m["match_id"],
                    "markets": markets, "kickoff_utc": m["kickoff_utc"],
                    "confidence_tier": tier,
                    "league_id": m["league_id"],
                    "teams": (m["home_team"], m["away_team"])})

    log.info("Predicciones generadas: %d", len(out))
    return out


def _alta() -> dict:
    """
    Línea de alta probabilidad: se elige y guarda ANTES de sellar, para que el
    lote del día la incluya. Nunca rompe el job: un fallo aquí no puede dejar
    sin sellar las predicciones.
    """
    if not settings.alta_prob_enabled:
        return {"elegidos": 0, "estado": "desactivada"}
    try:
        out = alta_prob_datos.select_and_persist()
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo en la línea de alta probabilidad")
        tg.alert(f"Fallo en la línea de alta probabilidad: {exc}")
        return {"elegidos": 0, "error": str(exc)}
    if (out.get("estado") in ("pausada", "sin_corte")
            or any("por debajo" in m for m in out.get("motivos", []))):
        tg.alert("ALTA PROBABILIDAD: " + "; ".join(out.get("motivos", [])))
    return out


def _alta_ext() -> dict:
    """Ampliación 62-95 %: se elige y guarda ANTES de sellar. Nunca rompe el job."""
    if not settings.alta_prob_ext_enabled:
        return {"elegidos": 0, "estado": "desactivada"}
    try:
        out = alta_prob_ext.select_and_persist()
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo en la alta probabilidad ampliada")
        tg.alert(f"Fallo en la alta probabilidad ampliada: {exc}")
        return {"elegidos": 0, "error": str(exc)}
    if out.get("estado") in ("pausada", "sin_corte"):
        tg.alert("ALTA PROB. AMPLIADA: " + "; ".join(out.get("motivos", [])))
    return out


def _alerta_sin_sellar(alta: dict, receipt: dict, escalera: dict | None = None,
                       parley: dict | None = None) -> None:
    if not receipt and alta.get("elegidos"):
        tg.alert(f"{alta['elegidos']} pronósticos de alta probabilidad SIN SELLAR: "
                 "no se mostrarán nunca.")
    if not receipt and (escalera or {}).get("paso"):
        tg.alert("Escalón de la escalera SIN SELLAR: no se mostrará nunca y el reto "
                 "seguirá esperando su resultado.")
    if not receipt and (parley or {}).get("tickets"):
        tg.alert(f"{len(parley['tickets'])} parlays SIN SELLAR: no se mostrarán nunca.")


def _escalera() -> dict:
    """Reto escalera: el escalón del día se elige ANTES de sellar. Nunca rompe el job."""
    if not settings.escalera_enabled:
        return {"estado": "desactivado"}
    try:
        return escalera_datos.select_and_persist()
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo en el reto escalera")
        tg.alert(f"Fallo en el reto escalera: {exc}")
        return {"estado": "error", "error": str(exc)}


def _parley() -> dict:
    """Parley del día: se elige ANTES de sellar. Nunca rompe el job."""
    if not settings.parley_enabled:
        return {"estado": "desactivado"}
    try:
        return parley_datos.select_and_persist()
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo en el parley del día")
        tg.alert(f"Fallo en el parley del día: {exc}")
        return {"estado": "error", "error": str(exc)}


def run() -> dict:
    preds = generate_predictions()
    sharp_only = _sharp_only_upcoming()
    if not preds:
        tg.alert("El job diario no generó ninguna predicción. Revisa la ingesta.")
        if not sharp_only:
            return {"predictions": 0}

    gate_ok, gate_reasons = (
        _shadow_gate_allows_publication() if settings.publish_picks_enabled
        else (False, ["PUBLISH_PICKS_ENABLED=0"])
    )
    if not gate_ok and not preds:
        # Solo había partidos "solo sharp" y no se publica: nada que sellar.
        return {"predictions": 0, "picks": 0,
                "picks_publishing": ("gate_blocked" if settings.publish_picks_enabled
                                     else "disabled"),
                "gate_reasons": gate_reasons}
    if not gate_ok:
        # Se sella igual: las predicciones del día quedan probadas aunque no
        # se publique ningún pick. El interruptor por sí solo no abre la
        # puerta: también debe aprobar la muestra en sombra del criterio.
        alta = _alta()
        _alta_ext()
        escalera = _escalera()
        parley = _parley()
        receipt = seal()
        _alerta_sin_sellar(alta, receipt, escalera, parley)
        if not receipt:
            tg.alert("FALLO AL SELLAR LA CADENA (predicciones sin picks).")
        if settings.publish_picks_enabled:
            tg.alert("PUBLICACIÓN BLOQUEADA por la puerta de CLV: "
                     + "; ".join(gate_reasons))
        result = {"predictions": len(preds), "picks": 0,
                  "picks_publishing": ("gate_blocked" if settings.publish_picks_enabled
                                       else "disabled"),
                  "gate_reasons": gate_reasons,
                  "alta_prob": alta,
                  "escalera": escalera,
                  "parley": parley,
                  "sealed": bool(receipt),
                  "chain": receipt["chain_sha256"][:16] if receipt else None}
        log.info("Job diario sin picks: %s", result)
        return result

    # Todas las predicciones son elegibles: la confianza del MODELO ya no
    # decide, el edge sale del precio de Pinnacle. Los partidos "solo sharp"
    # entran sin predicción (db/025): su pick se sella igual, sin referencia
    # a una predicción que no existe.
    selected = pk.select_daily(preds + sharp_only)
    tiered = pk.assign_tiers(selected)
    pk.persist(tiered)

    alta = _alta()
    _alta_ext()
    escalera = _escalera()
    parley = _parley()
    receipt = seal()
    _alerta_sin_sellar(alta, receipt, escalera, parley)
    if not receipt:
        tg.alert("FALLO AL SELLAR LA CADENA. No se publicó nada hoy.")
        return {"predictions": len(preds), "picks": len(selected), "sealed": False,
                "alta_prob": alta, "parley": parley}

    # Telegram es opcional (best-effort): si no hay TG_BOT_TOKEN configurado,
    # _send() lo omite en silencio. La API (picks.tier, ya asignado arriba)
    # es la fuente de verdad para lo que se muestra en la web, no Telegram.
    team_names = {p["match_id"]: p["teams"] for p in preds + sharp_only}
    free = [c for c, t in tiered if t == "free"]
    paid = [c for c, t in tiered if t == "paid"]
    published = tg.publish_batch(free + paid, team_names, receipt["chain_sha256"],
                                  free_count=len(free))

    n_free = sum(1 for _, t in tiered if t == "free")
    result = {"predictions": len(preds),
              "picks": len(selected), "free": n_free, "paid": len(selected) - n_free,
              "chain": receipt["chain_sha256"][:16], "alta_prob": alta, "escalera": escalera,
              "parley": parley,
              **published}
    log.info("Job diario: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run())
