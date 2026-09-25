"""
Modelo de residuo: dónde se equivoca el modelo RESPECTO AL MERCADO.

LA IDEA
-------
Dixon-Coles sabe de fuerza de equipos y poco más. El mercado sabe de todo lo
demás (lesiones, rotación, motivación, clima, arbitraje). La diferencia entre
ambos no es ruido puro: tiene estructura que depende de cosas observables
—descanso entre partidos, densidad de calendario, si el equipo es local tras
viajar, el momento de la temporada—. Un GBM sobre esa diferencia aprende la
estructura que queda.

Se modela el residuo EN ESPACIO LOGIT y sobre la probabilidad de local:

    z_modelo  = logit(p_modelo_local)
    z_mercado = logit(p_mercado_local)
    objetivo  = z_real_ajustado - z_modelo      (ver `_target`)

y la predicción final mezcla:  z_final = z_modelo + shrink * f(features)

POR QUÉ NO SUSTITUYE AL MODELO
------------------------------
El GBM corrige, no predice desde cero. Si le dejas predecir el resultado
directamente, con unos miles de partidos por liga memoriza equipos y colapsa
en cuanto cambia una plantilla. Corrigiendo un residuo pequeño, el daño que
puede hacer está acotado por construcción.

TRES PROTECCIONES, TODAS NECESARIAS
-----------------------------------
1. ENTRENAMIENTO FUERA DE MUESTRA. Las features de modelo y mercado vienen de
   `walk_forward_oos`. Entrenar sobre predicciones dentro de muestra enseña al
   GBM a corregir un error que en producción no existe.
2. ENCOGIMIENTO (`shrink`). La corrección se aplica al 50% por defecto. Un GBM
   sobre pocos miles de filas está sobreajustado aunque la validación diga que
   no; encoger es más barato que descubrirlo con dinero.
3. PUERTA DE VALIDACIÓN TEMPORAL. Si no mejora el log-loss en la parte final
   que nunca vio, se descarta entero y el sistema sigue sin él.

Esto es la Fase 4 del README ("GBM sobre el residuo del mercado"). Requiere
que existan cuotas de cierre en el histórico: sin mercado no hay residuo que
modelar.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from ..eval.metrics import log_loss

log = logging.getLogger(__name__)

EPS = 1e-9
FEATURES = [
    "p_model_home", "p_market_home", "logit_gap",
    "home_rest_days", "away_rest_days", "rest_diff",
    "home_matches_14d", "away_matches_14d",
    "month", "both_known",
]


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1.0 - p))


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def build_features(oos: pd.DataFrame) -> pd.DataFrame:
    """
    Construye las features a partir del DataFrame de `walk_forward_oos`.

    Todas las features son estrictamente PREVIAS al kickoff: descanso y
    densidad de calendario se calculan mirando solo partidos anteriores. Meter
    aquí cualquier cosa posterior al pitido inicial es la fuga clásica que
    convierte un backtest en ficción.
    """
    df = oos.sort_values("kickoff_utc").reset_index(drop=True).copy()
    df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)

    pit_cols = {"home_rest_days", "away_rest_days", "rest_diff",
                "home_matches_14d", "away_matches_14d"}
    if not pit_cols.issubset(df.columns):
        # Compatibilidad con llamadas antiguas y tests unitarios. El pipeline
        # real entrega estas columnas desde model.features, calculadas usando
        # TODO el historial previo y IDs de equipo, no solo la ventana OOS.
        last_seen: dict[str, pd.Timestamp] = {}
        recent: dict[str, list] = {}
        home_rest, away_rest, home_14, away_14 = [], [], [], []

        for _, r in df.iterrows():
            ko = r["kickoff_utc"]
            for side, rest_acc, cnt_acc in (("home_team", home_rest, home_14),
                                            ("away_team", away_rest, away_14)):
                team = r[side]
                prev = last_seen.get(team)
                rest_acc.append((ko - prev).days if prev is not None else np.nan)
                hist = recent.get(team, [])
                cnt_acc.append(sum(1 for t in hist if (ko - t).days <= 14))
            # Actualizar DESPUÉS de calcular: el partido actual no cuenta como
            # historia de sí mismo.
            for side in ("home_team", "away_team"):
                team = r[side]
                last_seen[team] = ko
                recent.setdefault(team, []).append(ko)

        df["home_rest_days"] = np.clip(home_rest, 0, 60)
        df["away_rest_days"] = np.clip(away_rest, 0, 60)
        df["rest_diff"] = df["home_rest_days"] - df["away_rest_days"]
        df["home_matches_14d"] = home_14
        df["away_matches_14d"] = away_14
    df["month"] = df["kickoff_utc"].dt.month
    df["both_known"] = df["both_known"].astype(float)
    df["p_model_home"] = df["p_home"]
    df["p_market_home"] = df["mk_home"]
    df["logit_gap"] = _logit(df["p_home"]) - _logit(df["mk_home"])
    return df


def _target(df: pd.DataFrame) -> np.ndarray:
    """
    Objetivo: cuánto habría que mover el logit del modelo hacia el resultado.

    Se usa el resultado real (1 si ganó el local, 0 si no) suavizado hacia el
    mercado. Sin suavizar, el objetivo es 0/1 puro y el GBM aprende varianza en
    vez de señal; el mercado es el ancla razonable de hacia dónde mover.
    """
    y = (df["outcome"].to_numpy() == 0).astype(float)
    z_market = _logit(df["mk_home"].to_numpy())
    z_model = _logit(df["p_home"].to_numpy())
    # Objetivo suavizado: 80% resultado, 20% mercado.
    z_target = _logit(0.8 * y + 0.2 * _sigmoid(z_market))
    return z_target - z_model


@dataclass
class ResidualParams:
    shrink: float = 0.5
    n_train: int = 0
    fitted_at: str = ""
    validated: bool = False
    val_metrics: dict = field(default_factory=dict)


class ResidualModel:
    """
    Corrección GBM sobre el residuo modelo-mercado, solo para el 1X2.

    IMPORTANTE: a diferencia del calibrador, esto NO mantiene coherentes los
    ~150 mercados —corrige la probabilidad de local y renormaliza el 1X2—. Por
    eso se aplica únicamente al mercado h2h, que es donde está el volumen, y no
    se propaga al resto del paquete de pricing.
    """

    def __init__(self, model=None, params: ResidualParams | None = None):
        self.model = model
        self.params = params or ResidualParams()

    @property
    def is_active(self) -> bool:
        return self.model is not None and self.params.validated

    def fit(self, feats: pd.DataFrame, shrink: float = 0.5) -> "ResidualModel":
        usable = feats.dropna(subset=["mk_home", "p_home"])
        if len(usable) < 800:
            raise ValueError(
                f"Muestra insuficiente para el modelo de residuo: {len(usable)} "
                "filas con mercado. Hacen falta >=800; por debajo de eso el GBM "
                "memoriza en vez de generalizar."
            )
        x = usable[FEATURES].to_numpy(dtype=float)
        y = _target(usable)

        gbm = HistGradientBoostingRegressor(
            max_depth=3,               # poco profundo a propósito: corrige, no predice
            max_iter=200,
            learning_rate=0.05,
            min_samples_leaf=40,
            l2_regularization=1.0,
            early_stopping=True,
            validation_fraction=0.15,
            random_state=0,
        )
        gbm.fit(x, y)
        self.model = gbm
        self.params = ResidualParams(
            shrink=float(shrink), n_train=int(len(usable)),
            fitted_at=datetime.now(timezone.utc).isoformat(),
        )
        return self

    def adjust(self, feats: pd.DataFrame, probs: np.ndarray) -> np.ndarray:
        """
        Aplica la corrección al 1X2. `probs` en orden [home, draw, away].

        El empate y la visita absorben proporcionalmente el cambio del local,
        de modo que la suma sigue siendo 1.
        """
        if self.model is None:
            return probs
        x = feats[FEATURES].to_numpy(dtype=float)
        delta = self.model.predict(x) * self.params.shrink

        p = np.array(probs, dtype=float).copy()
        p_home_new = _sigmoid(_logit(p[:, 0]) + delta)
        resto = np.clip(1.0 - p_home_new, EPS, None)
        resto_viejo = np.clip(p[:, 1] + p[:, 2], EPS, None)
        p[:, 1] = p[:, 1] / resto_viejo * resto
        p[:, 2] = p[:, 2] / resto_viejo * resto
        p[:, 0] = p_home_new
        return p / p.sum(axis=1, keepdims=True)

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "params": asdict(self.params)}, f)

    @classmethod
    def load(cls, path: str) -> "ResidualModel":
        with open(path, "rb") as f:
            d = pickle.load(f)
        return cls(d["model"], ResidualParams(**d["params"]))

    @classmethod
    def disabled(cls) -> "ResidualModel":
        return cls(None, ResidualParams())


def fit_and_validate(oos: pd.DataFrame, shrink: float = 0.5,
                     holdout_frac: float = 0.3) -> tuple[ResidualModel, dict]:
    """
    Ajusta en la parte antigua, valida en la reciente. Solo se activa si mejora
    el log-loss del 1X2 en datos que el GBM nunca vio.

    Devuelve (modelo, informe). Si no pasa la puerta, el modelo devuelto está
    desactivado y `adjust()` es la identidad.
    """
    feats = build_features(oos)
    usable = feats.dropna(subset=["mk_home", "p_home"]).reset_index(drop=True)

    n = len(usable)
    cut = int(n * (1.0 - holdout_frac))
    if cut < 800 or n - cut < 300:
        return ResidualModel.disabled(), {
            "ok": False,
            "reason": (f"Datos insuficientes: {cut} de ajuste y {n - cut} de "
                       "validación (hacen falta >=800 y >=300). El modelo de "
                       "residuo necesita histórico con cuotas de cierre."),
        }

    rm = ResidualModel().fit(usable.iloc[:cut], shrink=shrink)

    val = usable.iloc[cut:].reset_index(drop=True)
    p_antes = val[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
    p_antes = p_antes / p_antes.sum(axis=1, keepdims=True)
    p_despues = rm.adjust(val, p_antes)
    oc = val["outcome"].to_numpy(dtype=int)

    report = {
        "n_fit": int(cut),
        "n_val": int(n - cut),
        "shrink": float(shrink),
        "log_loss_before": round(log_loss(p_antes, oc), 5),
        "log_loss_after": round(log_loss(p_despues, oc), 5),
    }
    report["ok"] = bool(report["log_loss_after"] < report["log_loss_before"])

    if not report["ok"]:
        report["reason"] = (
            "El modelo de residuo no mejora fuera de muestra "
            f"({report['log_loss_before']} -> {report['log_loss_after']}). "
            "Se descarta. Es el resultado esperado si el mercado ya incorpora "
            "todo lo que estas features pueden ver."
        )
        log.warning(report["reason"])
        return ResidualModel.disabled(), report

    rm.params.validated = True
    rm.params.val_metrics = {k: report[k] for k in
                             ("log_loss_before", "log_loss_after", "n_val")}
    log.info("Modelo de residuo validado: log-loss %.5f -> %.5f",
             report["log_loss_before"], report["log_loss_after"])
    return rm, report
