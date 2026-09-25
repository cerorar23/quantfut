"""
Ponderación óptima entre tu modelo y el mercado.

LA PREGUNTA QUE RESPONDE ESTE MÓDULO
------------------------------------
"¿Cuánto vale realmente mi señal comparada con la del mercado?"

Es la pieza que faltaba del bloque de fusión con el mercado. Ya había de-vig
(`model/devig.py`) y shrinkage del edge (`publish/picks.py`), pero nada
estimaba el peso: `eval.metrics.blend_logit()` existía desde el principio
esperando un `w_model` que ningún código calculaba.

El peso se estima minimizando log-loss sobre predicciones FUERA DE MUESTRA:

    p_mezcla  ∝  p_modelo^w  ·  p_mercado^(1-w)

    w = 1.0  ->  el mercado no aporta nada por encima de tu modelo
    w = 0.0  ->  tu modelo no aporta nada por encima del mercado
    w = 0.2  ->  el mercado manda, pero tu modelo añade algo real

PREPÁRATE PARA UN PESO BAJO
---------------------------
Lo normal en fútbol es w entre 0.05 y 0.25. Eso NO es un fracaso: es la
medición más valiosa que puedes tener, porque un peso bajo bien estimado te
dice exactamente cuánta confianza merece tu discrepancia con el mercado. El
error caro es el contrario: asumir w=1 implícitamente —que es lo que hace un
sistema que publica su probabilidad cruda— y dimensionar apuestas como si tu
modelo supiera tanto como el consenso de todas las casas.

CONSECUENCIA DE NEGOCIO, LÉELA ANTES DE ACTIVARLO
-------------------------------------------------
Mezclar con el mercado acerca tus probabilidades a las suyas, y eso REDUCE el
edge que encuentras. Con w bajo, muchos picks que hoy superan el umbral
dejarán de hacerlo. Ese es el comportamiento correcto —esos edges eran en
buena parte ilusorios— pero cambia de forma visible cuántos picks publicas al
día. Por eso `META_BLEND_ENABLED` viene desactivado y la decisión es tuya, no
del código.

PESOS POR LIGA
--------------
Se estima además un peso por liga, encogido hacia el global (empirical Bayes)
para que una liga con pocos partidos no se quede con una estimación ruidosa.
Es información accionable: si tu modelo aporta en Liga MX pero no en Premier,
eso te dice dónde competir y dónde no molestarte.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import minimize_scalar

from ..eval.metrics import blend_logit, log_loss, rps

log = logging.getLogger(__name__)

# Pseudo-conteo del encogimiento por liga: con este número de partidos, el peso
# de una liga pesa lo mismo que el global. Con menos, manda el global.
LEAGUE_SHRINK_K = 600
# Por debajo de esto ni se intenta estimar un peso propio para la liga.
MIN_LEAGUE_OBS = 250


@dataclass
class MetaParams:
    w_model: float = 1.0
    w_by_league: dict = field(default_factory=dict)
    n_train: int = 0
    fitted_at: str = ""
    validated: bool = False
    val_metrics: dict = field(default_factory=dict)

    @property
    def is_identity(self) -> bool:
        """w=1 significa 'usa el modelo tal cual': no mezclar."""
        return abs(self.w_model - 1.0) < 1e-9 and not self.w_by_league


def _fit_weight(model_p: np.ndarray, market_p: np.ndarray,
                outcomes: np.ndarray) -> float:
    """Peso que minimiza log-loss. Búsqueda 1-D acotada en [0, 1]."""
    def objective(w: float) -> float:
        return log_loss(blend_logit(model_p, market_p, float(w)), outcomes)

    res = minimize_scalar(objective, bounds=(0.0, 1.0), method="bounded",
                          options={"xatol": 1e-4})
    return float(np.clip(res.x, 0.0, 1.0))


class MetaBlender:
    """
    Mezcla modelo y mercado con el peso estimado.

    Sin ajustar se comporta como la identidad (w=1, devuelve el modelo tal
    cual), de modo que el pipeline funciona igual antes de tener datos.
    """

    def __init__(self, params: MetaParams | None = None):
        self.params = params or MetaParams()

    @property
    def is_active(self) -> bool:
        return self.params.validated and not self.params.is_identity

    def weight_for(self, league_id: str | None = None) -> float:
        if league_id and league_id in self.params.w_by_league:
            return float(self.params.w_by_league[league_id])
        return float(self.params.w_model)

    def blend(self, model_p, market_p, league_id: str | None = None):
        """
        model_p, market_p: arrays alineados (n, k) o listas de k elementos.
        Funciona con cualquier k: 3 para 1X2, 2 para over/under.
        """
        w = self.weight_for(league_id)
        m = np.atleast_2d(np.asarray(model_p, dtype=float))
        k = np.atleast_2d(np.asarray(market_p, dtype=float))
        # Renormalizar por si llega un mercado de 2 vías ya des-margenado con
        # redondeos, o un 1X2 que no suma exactamente 1.
        m = m / np.clip(m.sum(axis=1, keepdims=True), 1e-12, None)
        k = k / np.clip(k.sum(axis=1, keepdims=True), 1e-12, None)
        out = blend_logit(m, k, w)
        return out[0] if np.ndim(model_p) == 1 else out

    def fit(self, model_p: np.ndarray, market_p: np.ndarray,
            outcomes: np.ndarray, leagues: np.ndarray | None = None) -> "MetaBlender":
        model_p = np.asarray(model_p, dtype=float)
        market_p = np.asarray(market_p, dtype=float)
        outcomes = np.asarray(outcomes, dtype=int)
        if len(model_p) < 300:
            raise ValueError(
                f"Muestra insuficiente para estimar el peso: {len(model_p)}. "
                "Por debajo de ~300 partidos el peso es ruido."
            )

        w_global = _fit_weight(model_p, market_p, outcomes)

        by_league: dict[str, float] = {}
        if leagues is not None:
            leagues = np.asarray(leagues)
            for lg in np.unique(leagues[leagues != None]):  # noqa: E711
                mask = leagues == lg
                n = int(mask.sum())
                if n < MIN_LEAGUE_OBS:
                    continue
                w_raw = _fit_weight(model_p[mask], market_p[mask], outcomes[mask])
                # Empirical Bayes: encoger hacia el peso global según muestra.
                w_shrunk = (n * w_raw + LEAGUE_SHRINK_K * w_global) / (n + LEAGUE_SHRINK_K)
                by_league[str(lg)] = float(w_shrunk)
                log.info("Peso %s: crudo %.3f -> encogido %.3f (n=%d)",
                         lg, w_raw, w_shrunk, n)

        self.params = MetaParams(
            w_model=w_global, w_by_league=by_league, n_train=int(len(model_p)),
            fitted_at=datetime.now(timezone.utc).isoformat(),
        )
        return self

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(asdict(self.params), f)

    @classmethod
    def load(cls, path: str) -> "MetaBlender":
        with open(path, "rb") as f:
            return cls(MetaParams(**pickle.load(f)))

    @classmethod
    def identity(cls) -> "MetaBlender":
        return cls(MetaParams())


def fit_and_validate(oos, holdout_frac: float = 0.3) -> tuple[MetaBlender, dict]:
    """
    Estima el peso en la parte antigua y lo valida en la reciente.

    El informe incluye a propósito las TRES referencias —modelo solo, mercado
    solo y mezcla— porque la comparación interesante no es "¿mejoró la
    mezcla?" sino "¿aporta mi modelo algo que el mercado no tenga ya?". Si el
    mercado solo bate a la mezcla, tienes la respuesta.

    `oos`: DataFrame de `eval.backtest.walk_forward_oos`, ordenado por fecha.
    """
    oos = oos.sort_values("kickoff_utc")
    usable = oos.dropna(subset=["mk_home", "mk_draw", "mk_away"]).reset_index(drop=True)

    n = len(usable)
    cut = int(n * (1.0 - holdout_frac))
    if cut < 300 or n - cut < 150:
        return MetaBlender.identity(), {
            "ok": False,
            "reason": (f"Datos insuficientes: {cut} para estimar y {n - cut} para "
                       f"validar (hacen falta >=300 y >=150). Se necesita "
                       "histórico CON cuotas de cierre."),
        }

    mp = usable[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
    kp = usable[["mk_home", "mk_draw", "mk_away"]].to_numpy(dtype=float)
    oc = usable["outcome"].to_numpy(dtype=int)
    lg = usable["league_id"].to_numpy() if "league_id" in usable.columns else None

    mb = MetaBlender().fit(mp[:cut], kp[:cut], oc[:cut],
                           lg[:cut] if lg is not None else None)

    # Validación sobre datos que la estimación nunca vio.
    v_mp, v_kp, v_oc = mp[cut:], kp[cut:], oc[cut:]
    v_lg = lg[cut:] if lg is not None else None
    if v_lg is None:
        v_blend = blend_logit(v_mp, v_kp, mb.params.w_model)
    else:
        v_blend = np.vstack([
            mb.blend(v_mp[i], v_kp[i], v_lg[i]) for i in range(len(v_mp))
        ])

    report = {
        "n_fit": int(cut),
        "n_val": int(n - cut),
        "w_model": round(mb.params.w_model, 4),
        "w_by_league": {k: round(v, 4) for k, v in mb.params.w_by_league.items()},
        "log_loss_modelo": round(log_loss(v_mp, v_oc), 5),
        "log_loss_mercado": round(log_loss(v_kp, v_oc), 5),
        "log_loss_mezcla": round(log_loss(v_blend, v_oc), 5),
        "rps_modelo": round(rps(v_mp, v_oc), 5),
        "rps_mercado": round(rps(v_kp, v_oc), 5),
        "rps_mezcla": round(rps(v_blend, v_oc), 5),
    }
    report["mejora_sobre_modelo"] = round(
        report["log_loss_modelo"] - report["log_loss_mezcla"], 5)
    report["bate_al_mercado"] = bool(
        report["log_loss_mezcla"] < report["log_loss_mercado"])
    report["ok"] = bool(report["log_loss_mezcla"] < report["log_loss_modelo"])

    # Lectura en lenguaje claro: es el número que hay que entender, no el que
    # hay que celebrar.
    w = report["w_model"]
    if w < 0.10:
        report["lectura"] = (
            f"Peso {w:.2f}: el mercado ya incorpora prácticamente todo lo que "
            "sabe tu modelo. No significa que el modelo esté mal; significa "
            "que tu edge sobre el consenso es muy pequeño y que dimensionar "
            "apuestas con la probabilidad cruda te haría apostar de más."
        )
    elif w < 0.30:
        report["lectura"] = (
            f"Peso {w:.2f}: rango normal de un modelo que funciona. El mercado "
            "manda, pero tu modelo aporta señal propia medible."
        )
    else:
        report["lectura"] = (
            f"Peso {w:.2f}: inusualmente alto. Antes de creértelo, corre "
            "check_leakage() y verifica que las cuotas usadas son de CIERRE y "
            "no de apertura. Un peso así suele ser una fuga, no un hallazgo."
        )

    if not report["ok"]:
        report["reason"] = (
            "La mezcla no mejora sobre el modelo solo fuera de muestra "
            f"({report['log_loss_modelo']} -> {report['log_loss_mezcla']}). "
            "Se deja sin mezclar."
        )
        log.warning(report["reason"])
        return MetaBlender.identity(), report

    mb.params.validated = True
    mb.params.val_metrics = {k: report[k] for k in
                             ("log_loss_modelo", "log_loss_mercado",
                              "log_loss_mezcla", "rps_mezcla", "n_val")}
    log.info("Peso modelo/mercado estimado: %.4f. %s", w, report["lectura"])
    return mb, report
