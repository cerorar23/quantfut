"""
Entrenamiento mensual y registro de artefactos.

Dos protecciones importantes:

1. NO SE DESPLIEGA UN MODELO QUE EMPEORA. El nuevo artefacto solo se marca
   activo si su RPS en validación es igual o mejor que el del activo actual.
   Sin esto, un reentrenamiento con datos corruptos te degrada en silencio.

2. HASH DEL DATASET. Cada artefacto guarda el SHA-256 del dataset con el que
   se entrenó. Es lo que te permite reproducir y hacer rollback.

Este es también el único punto del stack que justifica GPU: si migras a un
modelo jerárquico bayesiano (numpyro/JAX), el muestreo NUTS pasa de horas en
CPU a minutos en GPU. Mide primero en el VPS antes de pagar Colab.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from ..config import settings
from ..db import execute, query, query_one
from ..eval.backtest import check_leakage, metrics_from_oos, walk_forward_oos
from ..eval.comparison import compare_elo_dc_market
from .calibration import fit_and_validate
from .dixon_coles import DixonColes
from .elo import sequential_elo
from .features import build_pit_features, merge_pit_features
from .lineup_challenger import (
    fit_and_validate as lineup_fit_and_validate,
    load_training_frame as load_lineup_training_frame,
)
from .meta import fit_and_validate as meta_fit_and_validate
from .multinomial import fit_and_validate as multinomial_fit_and_validate
from .player_value import evaluar as player_value_evaluar
from .multinomial import run_ablations
from ..eval.clv import clv_report
from .promotion import MARKET_MAX_AGE_DAYS, evaluate_base_promotion
from .residual import fit_and_validate as residual_fit_and_validate
from .structure import evaluate as structure_evaluate

log = logging.getLogger(__name__)



def guardar_oos(oos: pd.DataFrame, version: str, carpeta: str | None = None) -> str:
    """
    Guarda las predicciones fuera de muestra del walk-forward. La Fase B de
    la fuerza por jugador compara brazos del XI sobre ellas sin repetir un
    entrenamiento (docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md).
    """
    ruta = f"{carpeta or settings.artifact_dir}/oos_{version}.pkl"
    oos.to_pickle(ruta)
    return ruta

def load_training_data(league_id: str | None = None,
                       years: int = 12,
                       incluir: tuple[str, ...] | list[str] = ()) -> pd.DataFrame:
    """
    `incluir`: ligas que entran aunque tengan `model_enabled = FALSE`. Sirve
    para entrenar el modelo que va a activarlas ANTES de encender el
    interruptor (2026-10-11): con el interruptor encendido y el modelo viejo
    activo, el job diario sellaría predicciones de equipos que no conoce.
    """
    since = datetime.now(timezone.utc) - timedelta(days=365 * years)
    incluir = list(incluir)
    rows = query(
        """WITH sharp_close AS (
               SELECT DISTINCT ON (match_id, selection)
                      match_id, selection, price
               FROM odds_snapshots
               WHERE bookmaker=%s AND market='h2h' AND window_tag='close'
               ORDER BY match_id, selection, captured_at DESC
           )
           SELECT m.match_id, m.league_id, m.kickoff_utc,
                  m.home_team_id, m.away_team_id,
                  th.canonical_name AS home_team, ta.canonical_name AS away_team,
                  -- La liga DOMÉSTICA de cada equipo, que en las copas
                  -- europeas no es la competición del partido. Es lo que
                  -- identifica al equipo en el modelo de fuerza.
                  th.league_id AS home_league, ta.league_id AS away_league,
                  m.home_goals, m.away_goals, m.home_xg, m.away_xg,
                  m.xg_source, m.xg_recorded_at,
                  m.home_shots, m.away_shots,
                  m.home_shots_target, m.away_shots_target,
                  m.home_psxg, m.away_psxg,
                  oh.price AS odds_home, od.price AS odds_draw, oa.price AS odds_away
           FROM matches m
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           -- Ligas "solo sharp" (db/023): fuera del modelo. También sus
           -- equipos cuando juegan una copa (2026-09-28: al añadir ligas solo
           -- sharp, `uefa_cups` empezaría a cargar sus partidos europeos).
           -- Comprobado al introducirlo: no excluía ningún partido.
           JOIN leagues lg ON lg.league_id = m.league_id
                AND (lg.model_enabled OR lg.league_id = ANY(%s::text[]))
           JOIN leagues lh ON lh.league_id = th.league_id
                AND (lh.model_enabled OR lh.league_id = ANY(%s::text[]))
           JOIN leagues la ON la.league_id = ta.league_id
                AND (la.model_enabled OR la.league_id = ANY(%s::text[]))
           LEFT JOIN sharp_close oh ON oh.match_id = m.match_id
                AND oh.selection='home'
           LEFT JOIN sharp_close od ON od.match_id = m.match_id
                AND od.selection='draw'
           LEFT JOIN sharp_close oa ON oa.match_id = m.match_id
                AND oa.selection='away'
           WHERE m.status='finished' AND m.home_goals IS NOT NULL
             AND m.kickoff_utc > %s
             -- Los casts son obligatorios: sin ellos Postgres no puede
             -- inferir el tipo del parámetro suelto de la comparación IS NULL
             -- y aborta con IndeterminateDatatype en TODAS las llamadas.
             AND (%s::text IS NULL OR m.league_id = %s::text)
           ORDER BY m.kickoff_utc""",
        (settings.sharp_book, incluir, incluir, incluir, since, league_id, league_id),
    )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
    return df


def dataset_hash(df: pd.DataFrame, config: dict | None = None) -> str:
    """
    Hash de TODAS las entradas de entrenamiento y de la configuración.

    Antes solo incluía ID y goles: cambiar xG, tiros, cuotas o cualquier
    feature dejaba el mismo hash y hacía imposible reproducir el artefacto.
    """
    ordered = df.copy()
    sort_cols = [c for c in ("kickoff_utc", "match_id") if c in ordered]
    if sort_cols:
        ordered = ordered.sort_values(sort_cols)
    ordered = ordered.reindex(sorted(ordered.columns), axis=1)

    def canonical(value):
        if value is None or (not isinstance(value, (dict, list, tuple))
                             and pd.isna(value)):
            return None
        if isinstance(value, (datetime, pd.Timestamp)):
            return pd.Timestamp(value).isoformat()
        if isinstance(value, float):
            return format(value, ".17g")
        if isinstance(value, (dict, list, tuple)):
            return json.loads(json.dumps(value, sort_keys=True, default=str))
        return value.item() if hasattr(value, "item") else value

    payload = {
        "columns": list(ordered.columns),
        "rows": [[canonical(v) for v in row]
                 for row in ordered.itertuples(index=False, name=None)],
        "config": config or {},
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def source_hash() -> str:
    """Huella del código que construye las predicciones y sus features."""
    root = Path(__file__).parent
    files = ("train.py", "dixon_coles.py", "pricing.py", "elo.py",
             "features.py", "multinomial.py", "lineup_challenger.py", "xg.py",
             "masmenos.py", "player_value.py")
    digest = hashlib.sha256()
    for name in files:
        digest.update(name.encode())
        digest.update((root / name).read_bytes())
    return digest.hexdigest()


def train_and_register(new_version: str | None = None,
                       validation_days: int = 365,
                       incluir: tuple[str, ...] | list[str] = ()) -> dict:
    df = load_training_data(incluir=incluir)
    if df.empty:
        raise RuntimeError("Sin datos de entrenamiento. Ejecuta la ingesta histórica.")

    version = new_version or datetime.now(timezone.utc).strftime("%Y.%m.%d-%H%M%S")
    hash_config = {
        "halflife": settings.decay_halflife_days,
        "xg_blend": settings.xg_blend,
        "devig": settings.devig_method,
        "sharp_book": settings.sharp_book,
        "fs_version": settings.fs_version,
        "source_sha256": source_hash(),
    }
    if incluir:
        hash_config["incluir"] = sorted(incluir)
    ds_hash = dataset_hash(df, hash_config)
    leakage_diagnostics = check_leakage(df)

    # Validación walk-forward sobre el último año antes de desplegar nada.
    # Se guardan las predicciones fuera de muestra: son la materia prima del
    # calibrador y del modelo de residuo, y repetir el walk-forward para cada
    # uno costaría el triple de tiempo sobre los mismos datos.
    val_start = df["kickoff_utc"].max() - timedelta(days=validation_days)
    oos = walk_forward_oos(df, val_start,
                           halflife=settings.decay_halflife_days,
                           xg_blend=settings.xg_blend)
    val = metrics_from_oos(oos, {"halflife": settings.decay_halflife_days,
                                 "xg_blend": settings.xg_blend,
                                 "devig": settings.devig_method})
    val["leakage_diagnostics"] = leakage_diagnostics

    # Baseline Elo y mercado sobre EXACTAMENTE los mismos partidos. Elo recorre
    # también la historia anterior a la validación para que sus ratings en el
    # primer partido OOS no empiecen de cero.
    elo_all = sequential_elo(df)
    elo_oos = elo_all[elo_all["match_id"].isin(set(oos["match_id"]))]
    try:
        comparison = compare_elo_dc_market(oos, elo_oos)
        market_end = pd.Timestamp(comparison["last_kickoff_utc"])
        comparison["market_age_days"] = int(
            (df["kickoff_utc"].max() - market_end).days)
        val["benchmarks"] = comparison
        val["validation_signature"] = comparison["match_ids_sha256"]
        val["validation_comparable"] = comparison["models"]["dixon_coles"]
    except ValueError as exc:
        comparison = None
        val["benchmarks"] = {"available": False, "reason": str(exc)}
        val["validation_signature"] = None
        val["validation_comparable"] = None

    # Una sola construcción point-in-time alimenta residuo, logística y
    # ablaciones. Así todos prueban las mismas definiciones y no cada uno su
    # propia versión de "forma" o "descanso".
    pit = build_pit_features(df, elo_all)
    oos_enriched = merge_pit_features(oos, pit)
    log.info("Validación: RPS=%.5f (mercado %.5f) n=%d",
             val["rps"], val.get("rps_market", float("nan")), val["n_obs"])

    # Ajuste final sobre TODO el histórico
    model = DixonColes(halflife_days=settings.decay_halflife_days,
                       xg_blend=settings.xg_blend)
    model.fit(df)

    Path(settings.artifact_dir).mkdir(parents=True, exist_ok=True)
    path = f"{settings.artifact_dir}/dc_{version}.pkl"
    model.save(path)
    guardar_oos(oos, version)

    # Calibración: se ajusta sobre las predicciones FUERA DE MUESTRA y solo se
    # guarda si supera su propia puerta de validación. Si no la supera, el
    # calibrador guardado es la identidad y el sistema publica sin calibrar,
    # que es el resultado correcto cuando el modelo ya estaba bien calibrado.
    cal, cal_report = fit_and_validate(
        oos["lam"].to_numpy(), oos["mu"].to_numpy(),
        oos["outcome"].to_numpy(), rho=model.params.rho,
    )
    cal_path = f"{settings.artifact_dir}/cal_{version}.pkl"
    cal.save(cal_path)
    val["calibration"] = cal_report
    log.info("Calibración: %s", "aplicada" if cal_report.get("ok") else "descartada")

    # Peso óptimo modelo/mercado. Se estima SIEMPRE, incluso con la mezcla
    # desactivada en producción: el peso es en sí mismo el diagnóstico más
    # importante del sistema —cuánto aporta tu señal sobre el consenso— y se
    # publica en el model-card.
    meta_path = f"{settings.artifact_dir}/meta_{version}.pkl"
    try:
        mb, meta_report = meta_fit_and_validate(oos)
        mb.save(meta_path)
    except Exception as exc:  # noqa: BLE001
        meta_report = {"ok": False, "reason": f"No se pudo estimar: {exc}"}
        log.warning("Peso modelo/mercado: %s", meta_report["reason"])
    val["meta"] = meta_report
    if meta_report.get("lectura"):
        log.info("%s", meta_report["lectura"])

    # Fase 2.D: otras formas de la matriz de marcadores sobre las mismas medias.
    # Solo informe; ninguna se usa para predecir.
    try:
        val["structure"] = structure_evaluate(oos)
        log.info("Estructura: %s", val["structure"].get("lectura"))
    except Exception as exc:  # noqa: BLE001
        val["structure"] = {"ok": False, "reason": f"No se pudo evaluar: {exc}"}

    # Modelo de residuo. Se entrena SIEMPRE (para poder medir si aportaría),
    # pero solo se aplica en producción si RESIDUAL_ENABLED está activo y
    # además superó su puerta de validación. Entrenarlo sin usarlo es barato y
    # te dice cuánto estás dejando sobre la mesa.
    res_path = f"{settings.artifact_dir}/res_{version}.pkl"
    try:
        rm, res_report = residual_fit_and_validate(
            oos_enriched, shrink=settings.residual_shrink)
        rm.save(res_path)
    except Exception as exc:  # noqa: BLE001
        res_report = {"ok": False, "reason": f"No se pudo entrenar: {exc}"}
        log.warning("Modelo de residuo: %s", res_report["reason"])
    val["residual"] = res_report
    log.info("Modelo de residuo: %s",
             "validado" if res_report.get("ok") else "descartado")

    # Regresión logística multinomial: dos preguntas distintas. La deportiva
    # mide señal sin cuotas; la anclada pregunta si añade algo sobre Pinnacle.
    multinomial_reports = {}
    multinomial_uris = {}
    for name, anchored in (("sport", False), ("market", True)):
        try:
            challenger, report = multinomial_fit_and_validate(
                oos_enriched, anchored=anchored, penalty="l1")
            multinomial_reports[name] = report
            if challenger is not None:
                uri = f"{settings.artifact_dir}/multinomial_{name}_{version}.pkl"
                challenger.save(uri)
                multinomial_uris[name] = uri
        except Exception as exc:  # noqa: BLE001
            multinomial_reports[name] = {"ok": False,
                                         "reason": f"No se pudo entrenar: {exc}"}
    val["multinomial"] = multinomial_reports

    try:
        val["ablations"] = run_ablations(oos_enriched)
    except Exception as exc:  # noqa: BLE001
        val["ablations"] = {"ok": False,
                            "reason": f"No se pudieron ejecutar: {exc}"}

    # El challenger de XI se entrena con predicciones generadas antes del
    # kickoff (selladas, o fuera de muestra en este mismo walk-forward) y XI
    # capturados a tiempo o, con autorización del usuario (2026-09-29),
    # descargados después del partido (`lineups_historicas`). Si aún no hay
    # muestra, el informe dice "collecting" y no se crea artefacto.
    lineup_uri = None
    try:
        lineup_frame, lineup_readiness = load_lineup_training_frame(oos)
        if lineup_frame.empty:
            lineup_report = {"ok": False, "status": "collecting",
                             "reason": "Aún no hay predicciones y XI históricos unidos"}
        else:
            lineup_model, lineup_report = lineup_fit_and_validate(
                lineup_frame, rho=float(model.params.rho))
            if lineup_model is not None:
                lineup_uri = f"{settings.artifact_dir}/lineup_{version}.pkl"
                lineup_model.save(lineup_uri)
        lineup_report["readiness"] = lineup_readiness
    except Exception as exc:  # noqa: BLE001
        lineup_report = {"ok": False, "status": "collecting",
                         "reason": f"No se pudo preparar: {exc}"}
    val["lineup_challenger"] = lineup_report

    # Fuerza por jugador (Fase B1): XI con valor y XI con nota contra el XI
    # simple, sobre las mismas filas. Solo informe y artefactos; nunca bloquea
    # el despliegue del modelo.
    try:
        player_value_report = player_value_evaluar(oos, float(model.params.rho), version)
    except Exception as exc:  # noqa: BLE001
        player_value_report = {"ok": False, "status": "error", "reason": str(exc)}
    val["player_value"] = player_value_report

    # Puerta final. Las métricas antiguas solo se comparan si su firma de
    # observaciones coincide; comparar ventanas diferentes sería falsa
    # precisión. Vencer a Elo es obligatorio para activación interna. Vencer al
    # mercado y reunir CLV se reportan aparte como puerta comercial.
    active = query_one("SELECT model_version, val_metrics FROM model_artifacts "
                       "WHERE is_active LIMIT 1")
    active_metrics = (json.loads(json.dumps(active["val_metrics"], default=str))
                      if active else None)
    candidate_common = {**(val["validation_comparable"] or {}),
                        "validation_signature": val["validation_signature"]}
    champion_common = None
    if active_metrics and active_metrics.get("validation_comparable"):
        champion_common = {
            **active_metrics["validation_comparable"],
            "validation_signature": active_metrics.get("validation_signature"),
        }
    # El CLV real entra en la puerta. Antes el parámetro existía y no se
    # pasaba nunca, así que `ready_for_commercial_picks` era falso por
    # construcción y no por medición: parecía una puerta y era un tapón.
    try:
        clv_real = clv_report(days=180)
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo leer el CLV para la puerta: %s", exc)
        clv_real = None
    val["clv_report"] = clv_real
    decision = evaluate_base_promotion(candidate_common, champion_common,
                                       comparison, clv_real)
    val["promotion"] = decision.as_dict()
    activate = bool(decision.promote)

    if activate:
        execute("UPDATE model_artifacts SET is_active = FALSE WHERE is_active")
    execute(
        """INSERT INTO model_artifacts
             (model_version, trained_at, dataset_sha256, params, val_metrics,
              artifact_uri, is_active, notes)
           VALUES (%s, now(), %s, %s, %s, %s, %s, %s)
           ON CONFLICT (model_version) DO UPDATE
             SET trained_at = now(), dataset_sha256 = EXCLUDED.dataset_sha256,
                 params = EXCLUDED.params, val_metrics = EXCLUDED.val_metrics,
                 artifact_uri = EXCLUDED.artifact_uri,
                 is_active = EXCLUDED.is_active, notes = EXCLUDED.notes""",
        (version, ds_hash,
         json.dumps({"halflife": settings.decay_halflife_days,
                     "xg_blend": settings.xg_blend,
                     "rho": model.params.rho,
                     "n_teams": len(model.params.teams),
                     # Un valor por liga, no uno global: es lo que permite
                     # auditar si el modelo aprendió algo distinto en Liga MX
                     # que en Premier, que es justo lo que debe pasar.
                     "leagues": model.league_report(),
                     "calibrator_uri": cal_path,
                     "meta_uri": meta_path,
                     "residual_uri": res_path,
                     "multinomial_uris": multinomial_uris,
                     "lineup_uri": lineup_uri,
                     "hash_config": hash_config}),
         json.dumps(val), path, activate, json.dumps(decision.as_dict())),
    )

    # Registro de calibración para el dashboard público
    if activate:
        execute(
            """INSERT INTO calibration_runs
                 (model_version, window_start, window_end, market, n_obs,
                  rps, log_loss, brier, rps_market, bins)
               VALUES (%s, %s, %s, '1x2', %s, %s, %s, %s, %s, %s)""",
            (version, val_start.date(), df["kickoff_utc"].max().date(),
             val["n_obs"], val["rps"], val["log_loss"], val["brier"],
             val.get("rps_market"), json.dumps(val["bins"])),
        )

    log.info("Modelo %s %s (%d partidos, %d ligas)", version,
             "activado" if activate else "guardado como candidato",
             len(df), len(model.params.leagues))
    return {"version": version, "activated": activate, "n_matches": len(df),
            "leagues": model.league_report(),
            "calibrated": bool(cal_report.get("ok")),
            "dataset_sha256": ds_hash, "promotion": decision.as_dict(),
            "val": val}


def bootstrap_status() -> tuple[bool, str]:
    """
    ¿Merece la pena entrenar ahora para salir de "sin modelo activo"?

    Un entrenamiento cuesta ~3,5 h en el servidor y, sin modelo activo, el job
    diario no sella nada. Esto NO ablanda la puerta: solo evita gastar un
    entrenamiento que la frescura del mercado ya condena de antemano. Replica
    `market_age_days` de `train_and_register` con una consulta barata.
    """
    if query_one("SELECT 1 AS x FROM model_artifacts WHERE is_active LIMIT 1"):
        return False, "Ya hay un modelo activo; el reentrenamiento es el mensual"
    row = query_one(
        """WITH close3 AS (
               SELECT match_id FROM odds_snapshots
               WHERE bookmaker=%s AND market='h2h' AND window_tag='close'
               GROUP BY match_id HAVING count(DISTINCT selection) = 3
           )
           SELECT max(m.kickoff_utc) AS last_match,
                  max(m.kickoff_utc) FILTER (WHERE c.match_id IS NOT NULL)
                      AS last_market
           FROM matches m LEFT JOIN close3 c USING (match_id)
           -- Lo mismo que ve `load_training_data`: un cierre de una liga
           -- "solo sharp" no hace fresco un mercado que el modelo no usa.
           JOIN leagues lg ON lg.league_id = m.league_id AND lg.model_enabled
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           JOIN leagues lh ON lh.league_id = th.league_id AND lh.model_enabled
           JOIN leagues la ON la.league_id = ta.league_id AND la.model_enabled
           WHERE m.status='finished' AND m.home_goals IS NOT NULL""",
        (settings.sharp_book,),
    )
    if not row or not row["last_market"]:
        return False, "Ningún partido terminado con cierre sharp completo"
    age = (row["last_match"] - row["last_market"]).days
    if age > MARKET_MAX_AGE_DAYS:
        return False, (f"Mercado sharp de hace {age} días "
                       f"(> {MARKET_MAX_AGE_DAYS}): la puerta lo rechazaría")
    return True, f"Sin modelo activo y mercado sharp de hace {age} días"


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true",
                        help="entrenar solo si no hay modelo activo y el "
                             "mercado sharp ya es lo bastante reciente")
    parser.add_argument("--incluir", nargs="*", default=[],
                        help="ligas con model_enabled = FALSE que entran en "
                             "este entrenamiento (para activarlas después)")
    args = parser.parse_args()
    if args.bootstrap:
        go, why = bootstrap_status()
        log.info("Bootstrap: %s", why)
        if not go:
            print(json.dumps({"trained": False, "reason": why}))
            raise SystemExit(0)
    print(json.dumps(train_and_register(incluir=args.incluir), indent=2, default=str))
