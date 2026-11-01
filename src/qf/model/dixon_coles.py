"""
Dixon-Coles con decaimiento temporal, objetivo mezclado goles/xG y efectos
jerárquicos por liga.

Diferencias frente al Dixon-Coles de libro (1997), todas orientadas a
eficiencia de muestra:

1. Decaimiento exponencial en lugar de ventana fija: un partido de hace
   6 meses pesa la mitad que uno de hoy (media vida configurable).
2. Objetivo mezclado goles/xG. El xG tiene menos ruido que los goles, así que
   la fuerza estimada converge con menos partidos. Se usa cuasi-verosimilitud
   de Poisson, que admite objetivos continuos.
3. EFECTOS POR LIGA CON POOLING PARCIAL. Cada liga tiene su propia ventaja de
   local y su propio nivel de goles, pero ambos se encogen hacia la media
   global con una penalización. Una liga con 12 años de datos se queda
   básicamente con su estimación propia; una liga recién añadida hereda la
   media global hasta que acumula partidos. Es el equivalente MAP (máximo a
   posteriori) de un modelo jerárquico bayesiano con priores gaussianos: te da
   el encogimiento sin el coste de muestrear una posterior.
4. Encogimiento hacia la media de liga (ridge) para equipos con pocos partidos,
   que es el problema real de los recién ascendidos.

5. FUERZA RELATIVA ENTRE LIGAS (`strength`), para competiciones donde se
   enfrentan equipos de ligas distintas (Champions, Europa League).

POR QUÉ POR LIGA Y NO UN AJUSTE GLOBAL: la ventaja de local no es universal
(en las ligas latinoamericanas es sistemáticamente mayor que en las europeas
por viaje, altitud y ambiente) y el nivel de goles tampoco. Con un solo `ha`
y un solo nivel compartidos, el modelo importa el sesgo de las ligas con más
partidos a las que tienen menos, que es justo donde menos margen de error hay.

Los equipos se indexan por (liga, nombre), no solo por nombre: dos ligas
distintas pueden tener un equipo con el mismo nombre canónico y fusionarlos
parte el historial de ambos sin dar ningún error.

COMPETICIÓN Y LIGA NO SON LO MISMO
-----------------------------------
Desde que existen las copas europeas hay que distinguir dos cosas que antes
coincidían:

  - la COMPETICIÓN del partido (`league_id`), que es lo que determina la
    ventaja de local y el nivel de goles;
  - la LIGA DOMÉSTICA de cada equipo (`home_league` / `away_league`), que es
    lo que identifica al equipo y a la que se aplica la suma cero.

El Real Madrid es el MISMO equipo en LaLiga y en Champions. Indexarlo por la
competición lo partiría en dos, y la versión de Champions tendría una docena
de partidos y ningún rival en común.

EL TÉRMINO `strength` Y POR QUÉ HACE FALTA
-------------------------------------------
La suma cero es POR LIGA, así que un ataque de 0,3 en Eredivisie y uno de 0,3
en LaLiga no están en la misma escala: dentro de los datos domésticos no hay
absolutamente nada que las conecte. Se añade un desplazamiento por liga que
entra con signo opuesto en las dos intensidades:

    log lam = base[comp] + ha[comp] + (atk[h] + str[lg_h]) - (dfn[a] + str[lg_a])
    log mu  = base[comp]            + (atk[a] + str[lg_a]) - (dfn[h] + str[lg_h])

En un partido doméstico lg_h == lg_a y `str` se cancela exactamente en las
dos, así que no compite con `base[comp]` ni cambia nada de lo que ya estaba
medido. En un cruce europeo no se cancela, y esa diferencia es lo ÚNICO que
identifica cuánto mejor es una liga que otra. Sin partidos entre ligas la
penalización de pooling lo deja plano y el modelo se comporta como antes.

NOTA: el siguiente upgrade natural es la versión bayesiana completa
(PyMC/numpyro) con pooling también entre temporadas, que además te da
incertidumbre por equipo. Es lo único de este stack que justifica GPU.
"""
from __future__ import annotations

import json
import logging
import math
import pickle
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import minimize

from ..config import settings
from .pricing import price_all_markets

log = logging.getLogger(__name__)

# Peso de las penalizaciones de pooling parcial. Cuanto mayor, más se parecen
# las ligas entre sí. Calibrados para que una liga con ~2.000 partidos quede
# dominada por sus propios datos y una con ~200 herede casi toda la media.
POOL_HOME_ADV = 25.0
POOL_BASE = 25.0
# La fuerza relativa entre ligas se apoya en MUY pocos partidos (los cruces
# europeos con los dos equipos en el catálogo son unos cientos frente a decenas
# de miles domésticos), así que se encoge bastante más fuerte que el resto.
# Sin cruces la penalización lo deja plano y el término desaparece solo.
POOL_STRENGTH = 300.0
# Restricción de identificación: suma cero de ataque y defensa DENTRO de cada
# liga. Sin esto, el nivel de una liga y las fuerzas de sus equipos son
# intercambiables (se puede sumar c a todos los ataques y a todas las defensas
# de una liga sin cambiar ninguna predicción).
#
# La media es PONDERADA por la muestra efectiva (auditoría 2026-10-21). Con la
# media simple, los equipos sin datos recientes (91 en el modelo de producción)
# no aportan nada a la verosimilitud y el optimizador los usaba de holgura para
# cumplir la restricción: acababan con ataques de hasta ±2,4, y un club que
# volvía a la liga (Hull, Coventry, Cambuur) heredaba ese valor. Ponderando, la
# restricción la fijan los equipos que juegan y los que no, se quedan donde los
# deja el ridge.
SUM_ZERO = 1000.0
# Tolerancias del optimizador. Con el gradiente analítico L-BFGS-B converge en
# unos cientos de iteraciones; antes, con diferencias finitas sobre ~800
# parámetros, agotaba el tope de evaluaciones sin converger (23 min).
MAXITER = 5000


@dataclass
class DCParams:
    teams: list[str]                 # claves "liga||equipo"
    attack: list[float]
    defence: list[float]
    leagues: list[str]
    home_adv: list[float]            # uno por liga, mismo orden que `leagues`
    base: list[float]                # nivel de goles por liga
    rho: float
    halflife_days: float
    xg_blend: float
    ridge: float
    fitted_at: str
    n_matches: int
    n_matches_by_league: dict = field(default_factory=dict)
    # Desplazamiento de fuerza de cada liga, mismo orden que `leagues`. Va con
    # default para que los artefactos entrenados antes de las copas europeas
    # sigan cargando: sin él, DCParams(**pickle_viejo) revienta.
    strength: list[float] = field(default_factory=list)
    # Liga doméstica de cada equipo, mismo orden que `teams`. Antes se derivaba
    # del prefijo de la clave; ahora la clave YA es la liga del equipo, pero se
    # guarda explícito porque es lo que consulta `lambdas()` cuando le llega un
    # partido de copa sin saber de dónde es cada equipo.
    team_leagues: list[str] = field(default_factory=list)
    # Muestra EFECTIVA de cada equipo: suma de los pesos de decaimiento de sus
    # partidos, mismo orden que `teams`. No es el número de partidos: un equipo
    # que dejó de jugar hace ocho años tiene cientos de partidos en la base y
    # una muestra efectiva de 0,0000, porque con media vida de 180 días sus
    # pesos son 2^-16. Sus `attack` y `defence` no los deciden los datos, los
    # decide el ridge y el centrado de la liga, y quedan en un valor extremo
    # del que el modelo está seguro. Es lo que hay que poder mirar antes de
    # apostar. Con default para que los artefactos anteriores sigan cargando.
    effective_n: list[float] = field(default_factory=list)
    # Error estándar de `attack` y `defence` de cada equipo, mismo orden que
    # `teams`. Es lo que convierte "mi ventaja es del 6%" en "mi ventaja es del
    # 6% ± 4%", que es la diferencia entre apostar y no. Ver `model/uncertainty.py`.
    # Con default: los artefactos anteriores no lo traen.
    se_attack: list[float] = field(default_factory=list)
    se_defence: list[float] = field(default_factory=list)
    # Fuerza del ridge en PARTIDOS RECIENTES EQUIVALENTES (None en artefactos
    # anteriores, que usaban `ridge` a secas) y si el optimizador convergió.
    ridge_partidos: float | None = None
    converged: bool | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @property
    def home_adv_mean(self) -> float:
        return float(np.mean(self.home_adv)) if self.home_adv else 0.25

    @property
    def base_mean(self) -> float:
        return float(np.mean(self.base)) if self.base else 0.0


def team_key(league_id: str | None, team: str) -> str:
    return f"{league_id or '_'}||{team}"


class DixonColes:
    """
    `ridge` es la penalización en la escala de la verosimilitud normalizada
    (la de los artefactos anteriores). `ridge_partidos` la expresa en PARTIDOS
    RECIENTES EQUIVALENTES y es la que se usa: la verosimilitud se pondera con
    pesos divididos por su media, así que un partido de hoy pesa 1/media (~17
    con 12 años y media vida de 180 días) y un ridge de 0,02 equivalía a una
    milésima de partido, es decir, a no encoger nada. Las dos se suman.
    """

    def __init__(self, halflife_days: float = 270.0, xg_blend: float = 0.65,
                 ridge: float = 0.0, max_goals: int = 12,
                 ridge_partidos: float | None = None):
        self.halflife = halflife_days
        self.xg_blend = xg_blend
        self.ridge = ridge
        self.max_goals = max_goals
        self.ridge_partidos = (settings.ridge_partidos if ridge_partidos is None
                               else ridge_partidos)
        self.params: DCParams | None = None
        self._idx: dict[str, int] = {}
        self._lidx: dict[str, int] = {}

    # ---------------- entrenamiento ----------------

    def _weights(self, kickoffs: np.ndarray, as_of: datetime) -> np.ndarray:
        days = np.array([(as_of - k).total_seconds() / 86400.0 for k in kickoffs])
        xi = math.log(2.0) / self.halflife
        return np.exp(-xi * np.clip(days, 0, None))

    def fit(self, df, as_of: datetime | None = None):
        """
        df: DataFrame con columnas
            kickoff_utc, home_team, away_team, home_goals, away_goals,
            home_xg, away_xg  (xG puede ser NaN; entonces cae a goles)
            league_id         (opcional; la COMPETICIÓN del partido)
            home_league, away_league  (opcionales; la liga DOMÉSTICA de cada
                                       equipo. Si faltan se asume que coinciden
                                       con la competición, que es el caso de
                                       cualquier liga normal.)
        """
        as_of = as_of or datetime.now(timezone.utc)
        df = df.dropna(subset=["home_goals", "away_goals"]).copy()
        if len(df) < 100:
            raise ValueError(f"Muestra insuficiente para ajustar: {len(df)} partidos")

        if "league_id" in df.columns:
            comp_col = df["league_id"].fillna("_").astype(str).tolist()
        else:
            comp_col = ["_"] * len(df)

        def _team_league_col(col: str) -> list[str]:
            if col not in df.columns:
                return list(comp_col)
            s = df[col].astype("object")
            return [comp if (v is None or v != v or not str(v).strip())
                    else str(v)
                    for v, comp in zip(s.tolist(), comp_col)]

        hlg_col = _team_league_col("home_league")
        alg_col = _team_league_col("away_league")

        # Un único índice para competiciones y ligas domésticas: las 8 ligas
        # son ambas cosas, y las dos copas solo lo primero. Las entradas que no
        # aplican quedan fijadas por su propia penalización de pooling y no
        # afectan a ninguna predicción.
        leagues = sorted(set(comp_col) | set(hlg_col) | set(alg_col))
        self._lidx = {lg: i for i, lg in enumerate(leagues)}
        n_lg = len(leagues)
        ci = np.array([self._lidx[lg] for lg in comp_col])
        lh = np.array([self._lidx[lg] for lg in hlg_col])
        la = np.array([self._lidx[lg] for lg in alg_col])

        hkeys = [team_key(lg, t) for lg, t in zip(hlg_col, df["home_team"])]
        akeys = [team_key(lg, t) for lg, t in zip(alg_col, df["away_team"])]
        teams = sorted(set(hkeys) | set(akeys))
        self._idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        hi = np.array([self._idx[k] for k in hkeys])
        ai = np.array([self._idx[k] for k in akeys])
        hg = df["home_goals"].to_numpy(dtype=float)
        ag = df["away_goals"].to_numpy(dtype=float)

        # Liga a la que pertenece cada equipo, para la restricción de suma cero
        team_league = np.zeros(n, dtype=int)
        for k, i in self._idx.items():
            team_league[i] = self._lidx[k.split("||", 1)[0]]
        league_masks = [team_league == j for j in range(n_lg)]
        team_league_names = [leagues[j] for j in team_league]

        # Objetivo mezclado. Si falta xG, se usa el gol.
        from .xg import xg_at_cutoff
        hx, ax = xg_at_cutoff(df, as_of)
        b = self.xg_blend
        y_h = np.where(np.isnan(hx), hg, (1 - b) * hg + b * hx)
        y_a = np.where(np.isnan(ax), ag, (1 - b) * ag + b * ax)

        w_raw = self._weights(df["kickoff_utc"].to_numpy(), as_of)

        # Muestra efectiva por equipo con los pesos CRUDOS, antes de normalizar.
        # La unidad importa: un peso crudo vale 1 para un partido de hoy y 0,5
        # a una media vida, así que la suma se lee como "partidos recientes
        # equivalentes" y el umbral significa lo mismo siempre. Con los pesos
        # normalizados por su media la escala dependería del tamaño y la
        # antigüedad del dataset: cargar más histórico viejo baja la media y
        # multiplica todos los valores, de modo que el mismo umbral iría
        # dejando pasar equipos peor medidos según creciera la base.
        eff = np.zeros(n)
        np.add.at(eff, hi, w_raw)
        np.add.at(eff, ai, w_raw)

        w = w_raw / w_raw.mean()
        # Ridge efectivo en la escala de `w`: `ridge_partidos` partidos
        # recientes equivalentes más el `ridge` heredado.
        ridge = self.ridge + self.ridge_partidos / float(w_raw.mean())

        # Pesos de la suma cero: muestra efectiva normalizada dentro de cada
        # liga (ver SUM_ZERO). El 1e-9 solo evita dividir por cero en una liga
        # sin ningún partido reciente.
        pz = eff + 1e-9
        for m_ in league_masks:
            if m_.any():
                pz[m_] = pz[m_] / pz[m_].sum()

        m00 = (hg == 0) & (ag == 0)
        m01 = (hg == 0) & (ag == 1)
        m10 = (hg == 1) & (ag == 0)
        m11 = (hg == 1) & (ag == 1)
        base0 = math.log(max(float(np.mean([y_h.mean(), y_a.mean()])), 0.2))
        log_min, log_max = math.log(1e-6), math.log(25.0)

        def unpack(p: np.ndarray):
            atk = p[:n]
            dfn = p[n:2 * n]
            ha = p[2 * n:2 * n + n_lg]
            base = p[2 * n + n_lg:2 * n + 2 * n_lg]
            stg = p[2 * n + 2 * n_lg:2 * n + 3 * n_lg]
            rho = np.clip(p[-1], -0.25, 0.25)
            return atk, dfn, ha, base, stg, rho

        def nll(p: np.ndarray) -> tuple[float, np.ndarray]:
            """Objetivo y su gradiente EXACTO (L-BFGS-B con `jac=True`)."""
            atk, dfn, ha, base, stg, rho = unpack(p)

            # `stg` entra con signo opuesto en las dos intensidades, así que en
            # un partido doméstico (lh == la) se cancela exactamente.
            eta_h = np.clip(base[ci] + ha[ci] + (atk[hi] + stg[lh]) - (dfn[ai] + stg[la]),
                            log_min, log_max)
            eta_a = np.clip(base[ci] + (atk[ai] + stg[la]) - (dfn[hi] + stg[lh]),
                            log_min, log_max)
            lam, mu = np.exp(eta_h), np.exp(eta_a)

            # Corrección tau sobre los goles REALES (enteros) y sus derivadas
            # respecto a lam, mu y rho.
            tau = np.ones_like(lam)
            d_lam = np.zeros_like(lam)
            d_mu = np.zeros_like(lam)
            d_rho = np.zeros_like(lam)
            tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
            d_lam[m00], d_mu[m00], d_rho[m00] = -mu[m00] * rho, -lam[m00] * rho, -lam[m00] * mu[m00]
            tau[m01] = 1.0 + lam[m01] * rho
            d_lam[m01], d_rho[m01] = rho, lam[m01]
            tau[m10] = 1.0 + mu[m10] * rho
            d_mu[m10], d_rho[m10] = rho, mu[m10]
            tau[m11] = 1.0 - rho
            d_rho[m11] = -1.0
            tau = np.clip(tau, 1e-9, None)

            # Cuasi-verosimilitud de Poisson (válida con objetivo continuo;
            # equivale a Poisson salvo constante cuando y es entero)
            ll = y_h * eta_h - lam + y_a * eta_a - mu + np.log(tau)
            # Derivada del objetivo respecto a cada predictor lineal.
            g_h = -w * (y_h - lam + lam * d_lam / tau)
            g_a = -w * (y_a - mu + mu * d_mu / tau)

            grad = np.zeros_like(p)
            g_atk, g_dfn = grad[:n], grad[n:2 * n]
            np.add.at(g_atk, hi, g_h)
            np.add.at(g_dfn, ai, -g_h)
            np.add.at(g_atk, ai, g_a)
            np.add.at(g_dfn, hi, -g_a)
            g_ha, g_base, g_stg = np.zeros(n_lg), np.zeros(n_lg), np.zeros(n_lg)
            np.add.at(g_ha, ci, g_h)
            np.add.at(g_base, ci, g_h + g_a)
            np.add.at(g_stg, lh, g_h - g_a)
            np.add.at(g_stg, la, g_a - g_h)
            grad[2 * n:2 * n + n_lg] = g_ha
            grad[2 * n + n_lg:2 * n + 2 * n_lg] = g_base
            grad[2 * n + 2 * n_lg:2 * n + 3 * n_lg] = g_stg
            grad[-1] = -float(np.sum(w * d_rho / tau))

            penalty = ridge * (np.sum(atk ** 2) + np.sum(dfn ** 2))
            g_atk += 2.0 * ridge * atk
            g_dfn += 2.0 * ridge * dfn
            # Identificación: suma cero por liga (no global), ponderada.
            for m_ in league_masks:
                if m_.any():
                    ma = float(np.sum(pz[m_] * atk[m_]))
                    md = float(np.sum(pz[m_] * dfn[m_]))
                    penalty += SUM_ZERO * (ma ** 2 + md ** 2)
                    g_atk[m_] += 2.0 * SUM_ZERO * ma * pz[m_]
                    g_dfn[m_] += 2.0 * SUM_ZERO * md * pz[m_]
            # Pooling parcial: cada liga hacia la media de las ligas.
            if n_lg > 1:
                # Un desplazamiento común a todas las ligas se cancela en TODOS
                # los partidos, así que solo las diferencias de `stg` están
                # identificadas: hay que anclar la media o el optimizador
                # deriva libremente por una dirección plana.
                for off, peso, x in ((2 * n, POOL_HOME_ADV, ha),
                                     (2 * n + n_lg, POOL_BASE, base),
                                     (2 * n + 2 * n_lg, POOL_STRENGTH, stg)):
                    penalty += peso * float(np.sum((x - x.mean()) ** 2))
                    grad[off:off + n_lg] += 2.0 * peso * (x - x.mean())
            return float(-np.sum(w * ll) + penalty), grad

        self._objetivo = nll
        x0 = np.concatenate([
            np.zeros(n), np.zeros(n),
            np.full(n_lg, 0.25), np.full(n_lg, base0), np.zeros(n_lg), [-0.03],
        ])
        bounds = ([(-2.5, 2.5)] * (2 * n)
                  + [(-0.5, 1.0)] * n_lg
                  + [(-1.5, 1.8)] * n_lg
                  + [(-1.0, 1.0)] * n_lg
                  + [(-0.25, 0.25)])
        res = minimize(nll, x0, jac=True, method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": MAXITER, "maxfun": 10 * MAXITER,
                                "ftol": 1e-12, "gtol": 1e-6})
        if not res.success:
            log.warning("Dixon-Coles NO convergió (%s) tras %d iteraciones",
                        res.message, res.nit)

        atk, dfn, ha, base, stg, rho = unpack(res.x)
        counts = {lg: int((ci == j).sum()) for lg, j in self._lidx.items()}
        # --------------------------------------------------------------
        # Incertidumbre de los parámetros.
        #
        # Se llegó aquí por descarte, y los dos intentos fallidos explican la
        # forma final mejor que la fórmula.
        #
        # 1) La curvatura del objetivo a secas NO vale: los pesos se normalizan
        #    por su media antes de entrar en la verosimilitud, así que un
        #    dataset de 12 años con media vida de 180 días se comporta como si
        #    sus 48.000 partidos contaran enteros, y los errores estándar salen
        #    unas cuatro veces demasiado pequeños.
        #
        # 2) El estimador sándwich H^-1·V·H^-1 arregla eso —es invariante a la
        #    escala de los pesos— pero falla justo donde más importa. Medido el
        #    2026-09-22: los seis equipos con el error estándar MÁS PEQUEÑO del
        #    modelo eran los seis con muestra efectiva 0,0000 (Chivas USA, QPR,
        #    Córdoba...). Y es correcto en su propio marco: sin muestra no hay
        #    variabilidad muestral. Pero ese parámetro no lo fijan los datos, lo
        #    fija el ridge, y un prior no es conocimiento. Un número que dice
        #    "de este equipo estoy segurísimo" sobre un equipo del que no se
        #    sabe nada es peor que no tener número.
        #
        # 3) Tampoco vale corregir el sándwich con la muestra efectiva
        #    (sum w·λ)²/(sum w²·λ). Esa expresión es invariante a la ESCALA de
        #    los pesos, que es justo lo que aquí no se puede ignorar: 24
        #    partidos de hace ocho años, todos con el mismo peso minúsculo,
        #    "cuentan" como 24 observaciones. Mide cuántas observaciones
        #    contribuyen, no cuánto pesan.
        #
        # Lo que se usa es la precisión POSTERIOR con pesos CRUDOS:
        #
        #     I_datos = sum w·λ              información de Fisher; se lee como
        #                                    "goles efectivos observados"
        #     I_prior = 2·ridge·media(w)     el ridge, en esas mismas unidades
        #     se = 1 / sqrt(I_datos + I_prior)
        #
        # Con muchos datos domina el primer término y el error estándar sale
        # como debe. Sin datos, I_datos -> 0, el error estándar se va al del
        # prior —que es enorme— y el modelo declara que no sabe, que es la
        # verdad. Las dos son el mismo número, no dos reglas pegadas.
        #
        # Se ignoran los términos fuera de la diagonal. Hay que tenerlo presente
        # al leer el número: ataque del local y defensa del visitante entran los
        # dos en la misma intensidad, así que su covarianza importa, y tratarlos
        # como independientes da una incertidumbre aproximada, no exacta. Para
        # decidir una abstención sobra; para publicar un intervalo de confianza,
        # no llega.
        # --------------------------------------------------------------
        lam_f = np.exp(base[ci] + ha[ci] + (atk[hi] + stg[lh]) - (dfn[ai] + stg[la]))
        mu_f = np.exp(base[ci] + (atk[ai] + stg[la]) - (dfn[hi] + stg[lh]))
        lam_f = np.clip(lam_f, 1e-6, 25.0)
        mu_f = np.clip(mu_f, 1e-6, 25.0)

        # Todo con pesos CRUDOS: así `I_prior` y `I_datos` hablan de lo mismo.
        I_prior = 2.0 * ridge * float(w_raw.mean())
        I_atk, I_dfn = np.full(n, I_prior), np.full(n, I_prior)
        # El ataque de un equipo mueve la intensidad que PRODUCE; su defensa,
        # la que CONCEDE, que es la del rival.
        np.add.at(I_atk, hi, w_raw * lam_f);   np.add.at(I_atk, ai, w_raw * mu_f)
        np.add.at(I_dfn, hi, w_raw * mu_f);    np.add.at(I_dfn, ai, w_raw * lam_f)
        se_atk = 1.0 / np.sqrt(I_atk)
        se_dfn = 1.0 / np.sqrt(I_dfn)

        self.params = DCParams(
            teams=teams,
            attack=atk.tolist(),
            defence=dfn.tolist(),
            leagues=leagues,
            home_adv=ha.tolist(),
            base=base.tolist(),
            strength=stg.tolist(),
            team_leagues=team_league_names,
            effective_n=eff.tolist(),
            se_attack=se_atk.tolist(),
            se_defence=se_dfn.tolist(),
            rho=float(rho),
            halflife_days=self.halflife,
            xg_blend=self.xg_blend,
            ridge=self.ridge,
            fitted_at=as_of.isoformat(),
            n_matches=int(len(df)),
            n_matches_by_league=counts,
            ridge_partidos=self.ridge_partidos,
            converged=bool(res.success),
        )
        return self

    # ---------------- inferencia ----------------

    def _strength(self, league: str | None) -> float:
        """
        Desplazamiento de fuerza de una liga. 0 para artefactos antiguos (sin
        el término) y para ligas que el modelo no vio.
        """
        p = self.params
        if not p.strength:
            return 0.0
        j = self._lidx.get(str(league)) if league is not None else None
        return p.strength[j] if j is not None and j < len(p.strength) else 0.0

    def lambdas(self, home_team: str, away_team: str,
                league_id: str | None = None,
                home_league: str | None = None,
                away_league: str | None = None) -> tuple[float, float]:
        """
        `league_id` es la COMPETICIÓN; `home_league`/`away_league`, la liga
        doméstica de cada equipo. En una liga normal coinciden y se pueden
        omitir; en Champions y Europa League hay que pasarlas o el equipo no se
        encuentra en el índice.
        """
        if self.params is None:
            raise RuntimeError("Modelo no entrenado")
        p = self.params
        hlg = home_league if home_league is not None else league_id
        alg = away_league if away_league is not None else league_id

        # Liga desconocida: cae a la media de las ligas conocidas.
        lj = self._lidx.get(str(league_id) if league_id is not None else "_")
        ha = p.home_adv[lj] if lj is not None else p.home_adv_mean
        base = p.base[lj] if lj is not None else p.base_mean

        # Equipo desconocido (recién ascendido, sin historia): cae a la media
        # de SU liga, que por construcción es 0 en ataque y defensa.
        hi = self._idx.get(team_key(hlg, home_team))
        ai = self._idx.get(team_key(alg, away_team))
        atk_h = p.attack[hi] if hi is not None else 0.0
        dfn_h = p.defence[hi] if hi is not None else 0.0
        atk_a = p.attack[ai] if ai is not None else 0.0
        dfn_a = p.defence[ai] if ai is not None else 0.0

        sh, sa = self._strength(hlg), self._strength(alg)
        lam = math.exp(base + ha + (atk_h + sh) - (dfn_a + sa))
        mu = math.exp(base + (atk_a + sa) - (dfn_h + sh))
        return min(lam, 6.0), min(mu, 6.0)

    def effective_n(self, team: str, league: str | None) -> float:
        """
        Muestra efectiva del equipo: suma de pesos de decaimiento de sus
        partidos. Un equipo que NO está en el índice devuelve 0.0, que es
        correcto y además es el caso seguro: `lambdas()` lo trata como la media
        de su liga. El caso peligroso es el contrario —estar en el índice con
        muestra efectiva ~0— porque entonces no cae a la media: carga el valor
        extremo que le dejaron el ridge y el centrado.

        Los artefactos anteriores a este campo devuelven `inf`: sin el dato no
        se puede afirmar que la muestra sea insuficiente, y hacerlos fallar
        cerrado dejaría al sistema sin publicar nada tras cargar un modelo
        viejo. Queda avisado en `_meta`.
        """
        p = self.params
        if p is None:
            raise RuntimeError("Modelo no entrenado")
        if not p.effective_n:
            return float("inf")
        i = self._idx.get(team_key(league, team))
        return float(p.effective_n[i]) if i is not None else 0.0

    def knows(self, home_team: str, away_team: str,
              league_id: str | None = None,
              home_league: str | None = None,
              away_league: str | None = None,
              min_effective: float | None = None) -> bool:
        """
        ¿Sabe lo suficiente de ambos equipos para que su precio signifique algo?

        No basta con que estén en el índice. Un equipo que jugó su última
        temporada hace años sigue en el índice y el modelo le asigna una fuerza
        extrema con total confianza: en la demostración del 2026-09-22, Hull
        (muestra efectiva 0,0000) salió a 0,9061 de probabilidad contra un
        mercado que decía 0,4659, y el motor le asignó el stake máximo.
        """
        hlg = home_league if home_league is not None else league_id
        alg = away_league if away_league is not None else league_id
        if (team_key(hlg, home_team) not in self._idx
                or team_key(alg, away_team) not in self._idx):
            return False
        umbral = (settings.min_effective_matches if min_effective is None
                  else min_effective)
        return (self.effective_n(home_team, hlg) >= umbral
                and self.effective_n(away_team, alg) >= umbral)

    def predict(self, home_team: str, away_team: str,
                league_id: str | None = None,
                home_league: str | None = None,
                away_league: str | None = None) -> dict:
        lam, mu = self.lambdas(home_team, away_team, league_id,
                               home_league, away_league)
        markets = price_all_markets(lam, mu, self.params.rho, self.max_goals)
        known = self.knows(home_team, away_team, league_id,
                           home_league, away_league)
        hlg = home_league if home_league is not None else league_id
        alg = away_league if away_league is not None else league_id
        markets["_meta"] = {
            "home_lambda": lam, "away_lambda": mu,
            "rho": self.params.rho,
            "both_teams_known": known,
            "home_effective_n": self.effective_n(home_team, hlg),
            "away_effective_n": self.effective_n(away_team, alg),
            "league_known": str(league_id) in self._lidx if league_id else False,
        }
        return markets

    def league_report(self) -> list[dict]:
        """Qué aprendió el modelo de cada liga. Va al model-card público."""
        if self.params is None:
            raise RuntimeError("Modelo no entrenado")
        p = self.params
        n_equipos = {}
        for lg in p.team_leagues:
            n_equipos[lg] = n_equipos.get(lg, 0) + 1
        return [
            {
                "league_id": lg,
                "home_advantage": round(p.home_adv[i], 4),
                "goal_base": round(p.base[i], 4),
                "expected_home_goals_avg": round(math.exp(p.base[i] + p.home_adv[i]), 3),
                "expected_away_goals_avg": round(math.exp(p.base[i]), 3),
                # Fuerza relativa frente a la media de las ligas. Solo tiene
                # sentido si hay partidos entre ligas que la identifiquen; sin
                # ellos queda en 0 para todas.
                "relative_strength": (round(p.strength[i], 4)
                                      if i < len(p.strength) else None),
                "n_matches": p.n_matches_by_league.get(lg, 0),
                "n_teams": n_equipos.get(lg, 0),
            }
            for i, lg in enumerate(p.leagues)
        ]

    # ---------------- persistencia ----------------

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({"params": asdict(self.params), "idx": self._idx,
                         "lidx": self._lidx,
                         "halflife": self.halflife, "xg_blend": self.xg_blend,
                         "ridge": self.ridge, "max_goals": self.max_goals,
                         "ridge_partidos": self.ridge_partidos}, f)

    @classmethod
    def load(cls, path: str) -> "DixonColes":
        with open(path, "rb") as f:
            d = pickle.load(f)
        # Los artefactos anteriores no traen `ridge_partidos`: se cargan con 0
        # para que conserven exactamente su objetivo original.
        m = cls(d["halflife"], d["xg_blend"], d["ridge"], d["max_goals"],
                ridge_partidos=d.get("ridge_partidos", 0.0))
        m.params = DCParams(**d["params"])
        m._idx = d["idx"]
        m._lidx = d["lidx"]
        return m
