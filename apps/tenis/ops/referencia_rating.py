"""Implementación de REFERENCIA independiente del filtro de rating R (plan técnico §D.3, §D.6, §D.7, §J).

Escrita solo desde la especificación del plan, sin mirar `tenis/modelo/` ni el simulador por dentro: la
probabilidad del partido se calcula aquí con código propio (forma cerrada por sets, verificada en las pruebas
contra una programación dinámica punto a punto lenta que sigue al sacador). Prioridad: claridad, no velocidad.

Fórmulas (§D.3), partido m entre A = jugador_1 y B = jugador_2, circuito c, superficie s, formato f:
    ρ_m = κ_s·(1 + Σ_k γ_k z_k)·(θ_A − θ_B) + (d_{A,s} − d_{B,s}) + ζ·ι_m·(d^ι_A − d^ι_B)
          − Σ_j φ_j·(g_j(F_A) − g_j(F_B))
    P(A gana) = M̄_f(expit(ℓ̄_s + ρ), expit(ℓ̄_s − ρ); Σ)
Estado por jugador: x_i = (θ, d_Clay, d_Grass, d_Hard, d_Indoor, d^ι) ~ N(m_i, P_i) (6×6, sin covarianza
entre jugadores). Actualización de Laplace/Newton con V⁺ = (V⁻¹ + H)⁻¹ y m⁺ = m + V⁺∇ℓ(m), H = −∇²ℓ.

Cada decisión que el plan NO fija está en `DECISIONES` (con su valor por omisión) y en el informe
docs/tenis_referencia_rating_20261105.md: son hallazgos de especificación, no verdades.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
import pandas as pd

SUPERFICIES = ("Clay", "Grass", "Hard", "Indoor")
I_THETA, I_IOTA = 0, 5          # índices del vector de estado; d_s está en 1 + SUPERFICIES.index(s)
N_EST = 6
CONTEXTOS = ("semana_previa_gs", "por_equipos", "jjoo")
DECISIVOS = ("tiebreak_7", "tiebreak_10", "ventaja", "supertiebreak_10")

# Decisiones que la especificación deja abiertas (ver informe, sección «Ambigüedades»).
DECISIONES = {
    "orden_eventos": "visible_resultado_utc (columna `orden` de la exportación); predicción en corte c ve vis < c",
    "reloj_estado": "corte_utc del partido (Δt en días; Δt < 0 se trunca a 0)",
    "inactividad": "salto aditivo inact_var en Var(θ) si Δt > inact_umbral_dias (solo θ)",
    "ruido_d": "tau_d²·Δt en cada d_s y en d^ι",
    "covarianza_estado": "6×6 completa por jugador; actualización en el espacio conjunto 12-dim; "
                         "la covarianza entre jugadores se descarta tras cada partido",
    "sigma_en_actualizacion": "Σ_ε (solo forma del día); Σ_m = Σ_ε + J V Jᵀ solo en la predicción",
    "derivadas": "diferencias centrales en ρ con paso h_dif (ℓ' y ℓ''); c = max(−ℓ'', 0)",
    "fatiga_tiempos": "T_ref = inicio_utc si existe, si no corte_utc; fin_k = inicio_k + minutos_k si hay hora "
                      "real, si no visible_resultado_utc_k; cuenta k si vis_k < corte_m y 0 ≤ T_ref − fin_k ≤ 96 h",
    "fatiga_desconocida": "minutos NULL de un partido jugado (no walkover) aportan 0 y marcan fatiga_desconocida",
    "prior": "θ₀ = a + b·ln(1 + puntos); sin puntos: theta_sin_ranking; d = 0 con Σ_d; d^ι = 0 con var_d_iota",
    "inicializacion": "el estado se crea en la PRIMERA ACTUALIZACIÓN (prior con el ranking de ese partido); "
                      "una predicción sin estado usa un prior temporal que no se guarda",
    "sin_historia": "n_prev = 0 y sin puntos de ranking ⇒ sin pronóstico (π = NaN)",
    "no_actualizan": "actualiza_rating False (retiradas, walkovers, descalificados), superficie NULL o "
                     "formato desconocido (M̄_f no definido); sus minutos sí cuentan para la fatiga",
    "cuadratura": "Gauss–Hermite producto de orden q sobre la base propia de Σ (eigh), nodos √2·Q·√Λ·u",
}


# ---------------------------------------------------------------------------------------------------------
# 1. Probabilidad del partido (rápida, vectorizada; forma cerrada por sets)
# ---------------------------------------------------------------------------------------------------------
def p_juego(p):
    """P(el sacador gana el juego) con ventaja: p⁴(1+4q+10q²) + 20p³q³·p²/(1−2pq)."""
    p = np.asarray(p, dtype=float)
    q = 1.0 - p
    return p**4 * (1 + 4 * q + 10 * q**2) + 20 * p**3 * q**3 * p**2 / (1 - 2 * p * q)


def _saca_a_en_tb(k: int) -> bool:
    """Punto k (desde 0) del tiebreak: A saca el primero y luego se alterna cada dos puntos."""
    return k == 0 or ((k - 1) // 2) % 2 == 1


def _diagonales(fin_a, fin_b, n_filas: int, n_diag: int):
    """Máscaras por diagonal (total = a + b) de una cadena de «A suma 1 / B suma 1»: para cada a de la diagonal,
    ¿el paso de A termina la cadena (fin_a(a+1, b)) y el de B (fin_b(a, b+1))?"""
    out = []
    for t in range(n_diag):
        ma = np.zeros(n_filas); mb = np.zeros(n_filas)
        for a in range(n_filas):
            b = t - a
            if b < 0:
                continue
            ma[a] = 1.0 if fin_a(a + 1, b) else 0.0
            mb[a] = 1.0 if fin_b(a, b + 1) else 0.0
        out.append((ma[:, None], mb[:, None]))
    return out


@lru_cache(maxsize=None)
def _mascaras_tb(n: int):
    return _diagonales(lambda a, b: a == n, lambda a, b: b == n, n, 2 * n - 2)


@lru_cache(maxsize=None)
def _mascaras_set():
    return _diagonales(lambda a, b: (a == 6 and b <= 4) or a == 7, lambda a, b: (b == 6 and a <= 4) or b == 7, 7, 12)


def _cadena(M, mascaras, w_por_diag):
    """Avanza la masa M[a, nodo] por las diagonales; devuelve (P(A termina ganando), masa restante)."""
    gana = 0.0
    for t, (ma, mb) in enumerate(mascaras):
        w = w_por_diag(t)
        gana = gana + (M * ma).sum(axis=0) * w
        sigue_a = M * (1 - ma) * w
        sigue_b = M * (1 - mb) * (1 - w)
        M = sigue_b.copy()
        M[1:] += sigue_a[:-1]
    return gana, M


def p_tiebreak(pa, pb, n: int):
    """P(A gana un tiebreak a n por diferencia de 2), A saca primero. En el empate (n−1, n−1) cada pareja de
    puntos tiene un saque de cada uno: P = x/(x+y), x = pa(1−pb), y = (1−pa)pb."""
    forma = np.broadcast(pa, pb).shape
    pa, pb = (np.broadcast_to(np.asarray(v, dtype=float), forma).ravel() for v in (pa, pb))
    M = np.zeros((n, pa.size)); M[0] = 1.0
    gana, M = _cadena(M, _mascaras_tb(n), lambda t: pa if _saca_a_en_tb(t) else 1 - pb)
    x, y = pa * (1 - pb), (1 - pa) * pb
    return (gana + M[n - 1] * x / (x + y)).reshape(forma)      # solo queda masa en (n−1, n−1)


def p_set(pa, pb, regla: str):
    """P(A gana el set), A saca el primer juego. regla: 'tb7', 'tb10' (tiebreak a 7 / a 10 en 6-6) o 'ventaja'."""
    forma = np.broadcast(pa, pb).shape
    pa, pb = (np.broadcast_to(np.asarray(v, dtype=float), forma).ravel() for v in (pa, pb))
    ha, hb = p_juego(pa), p_juego(pb)
    M = np.zeros((7, pa.size)); M[0] = 1.0
    w = lambda t: ha if t % 2 == 0 else 1 - hb    # noqa: E731  (juego t: A saca los pares)
    if regla == "ventaja":
        gana, M = _cadena(M, _mascaras_set()[:10], w)
        x, y = ha * (1 - hb), (1 - ha) * hb       # 5-5, saca A: pareja de juegos hasta romper el empate
        return (gana + M[5] * x / (x + y)).reshape(forma)
    gana, M = _cadena(M, _mascaras_set(), w)
    return (gana + M[6] * p_tiebreak(pa, pb, 10 if regla == "tb10" else 7)).reshape(forma)   # 6-6, saca A


def p_partido(pa, pb, mejor_de: int, decisivo: str):
    """P(A gana el partido). Usa que la probabilidad de un set o de un tiebreak no depende de quién saca primero
    (comprobado contra `p_partido_lento` en las pruebas)."""
    if decisivo not in DECISIVOS:
        raise ValueError(f"formato decisivo no soportado: {decisivo}")
    s = p_set(pa, pb, "tb7")
    sd = {"tiebreak_7": s, "tiebreak_10": p_set(pa, pb, "tb10"), "ventaja": p_set(pa, pb, "ventaja"),
          "supertiebreak_10": p_tiebreak(pa, pb, 10)}[decisivo]
    if mejor_de == 3:
        return s * s + 2 * s * (1 - s) * sd
    if mejor_de == 5:
        return s**3 + 3 * s**3 * (1 - s) + 6 * s**2 * (1 - s) ** 2 * sd
    raise ValueError(f"mejor_de no soportado: {mejor_de}")


# ---------------------------------------------------------------------------------------------------------
# 2. Probabilidad del partido LENTA, punto a punto, siguiendo al sacador (solo para verificar)
# ---------------------------------------------------------------------------------------------------------
def p_partido_lento(pa: float, pb: float, mejor_de: int, decisivo: str) -> float:
    """Recorre el partido punto a punto con el sacador explícito; mezcla 50/50 del primer sacador. Los empates
    infinitos (deuce, tiebreak ≥ (n−1, n−1), set a ventaja ≥ 5-5) se cierran con su serie geométrica."""
    pa, pb = float(pa), float(pb)
    gana_pto = {"A": pa, "B": 1 - pb}             # P(A gana el punto) según quién saca

    @lru_cache(maxsize=None)
    def juego(sacador, i, j):                     # i, j: puntos del sacador y del restador; devuelve P(A gana)
        p = gana_pto[sacador] if sacador == "A" else 1 - gana_pto[sacador]   # P(sacador gana punto)
        if i >= 4 and i - j >= 2:
            return 1.0 if sacador == "A" else 0.0
        if j >= 4 and j - i >= 2:
            return 0.0 if sacador == "A" else 1.0
        if i == j and i >= 3:
            ps = p * p / (p * p + (1 - p) ** 2)   # P(sacador gana desde deuce)
            return ps if sacador == "A" else 1 - ps
        return p * juego(sacador, i + 1, j) + (1 - p) * juego(sacador, i, j + 1)

    def otro(x):
        return "B" if x == "A" else "A"

    @lru_cache(maxsize=None)
    def tiebreak(primero, n, a, b):               # a, b: puntos de A y B; devuelve P(A gana)
        if a >= n and a - b >= 2:
            return 1.0
        if b >= n and b - a >= 2:
            return 0.0
        if a == b and a >= n - 1:
            x, y = pa * (1 - pb), (1 - pa) * pb
            return x / (x + y)
        k = a + b
        sac = primero if (k == 0 or ((k - 1) // 2) % 2 == 1) else otro(primero)
        w = gana_pto[sac]
        return w * tiebreak(primero, n, a + 1, b) + (1 - w) * tiebreak(primero, n, a, b + 1)

    @lru_cache(maxsize=None)
    def resto_set(sacador, regla, a, b):
        """Desde (a, b) con `sacador` al saque del próximo juego: dict {(gana_A, saca_primero_el_set_siguiente): P}."""
        if (a >= 6 and a - b >= 2) or a == 7:
            return {(True, sacador): 1.0}
        if (b >= 6 and b - a >= 2) or b == 7:
            return {(False, sacador): 1.0}
        if a == 6 and b == 6 and regla != "ventaja":
            pt = tiebreak(sacador, 10 if regla == "tb10" else 7, 0, 0)
            sig = otro(sacador)                   # el tiebreak cuenta como un juego sacado por `sacador`
            return {(True, sig): pt, (False, sig): 1 - pt}
        if regla == "ventaja" and a == b and a >= 5:
            # Pareja de juegos: sacador y luego el otro; vuelve al empate con el mismo sacador.
            h1 = juego(sacador, 0, 0)             # P(A gana el juego que saca `sacador`)
            h2 = juego(otro(sacador), 0, 0)
            x, y = h1 * h2, (1 - h1) * (1 - h2)
            pg = x / (x + y)
            return {(True, sacador): pg, (False, sacador): 1 - pg}   # tras número par de juegos saca el mismo
        hg = juego(sacador, 0, 0)
        out: dict = {}
        for k, v in resto_set(otro(sacador), regla, a + 1, b).items():
            out[k] = out.get(k, 0.0) + hg * v
        for k, v in resto_set(otro(sacador), regla, a, b + 1).items():
            out[k] = out.get(k, 0.0) + (1 - hg) * v
        return out

    objetivo = 3 if mejor_de == 5 else 2

    @lru_cache(maxsize=None)
    def partido(sacador, sa, sb):
        if sa == objetivo:
            return 1.0
        if sb == objetivo:
            return 0.0
        es_decisivo = sa == sb == objetivo - 1
        if es_decisivo and decisivo == "supertiebreak_10":
            return tiebreak(sacador, 10, 0, 0)
        regla = "tb7"
        if es_decisivo:
            regla = {"tiebreak_7": "tb7", "tiebreak_10": "tb10", "ventaja": "ventaja"}[decisivo]
        tot = 0.0
        for (gana_a, sig), pr in resto_set(sacador, regla, 0, 0).items():
            tot += pr * partido(sig, sa + 1, sb) if gana_a else pr * partido(sig, sa, sb + 1)
        return tot

    return 0.5 * partido("A", 0, 0) + 0.5 * partido("B", 0, 0)


# ---------------------------------------------------------------------------------------------------------
# 3. M̄_f: integración sobre Σ (logit) por Gauss–Hermite
# ---------------------------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _gh(q: int):
    u, w = np.polynomial.hermite.hermgauss(q)
    U1, U2 = np.meshgrid(u, u, indexing="ij")
    W = np.outer(w, w) / math.pi
    return np.stack([U1.ravel(), U2.ravel()]), W.ravel()


def nodos_sigma(sigma: np.ndarray, q: int):
    """Desplazamientos (2, q²) y pesos para E[f(e)], e ~ N₂(0, Σ). Σ semidefinida (eigh admite σ_ε = 0)."""
    U, W = _gh(q)
    lam, Q = np.linalg.eigh(np.asarray(sigma, dtype=float))
    lam = np.clip(lam, 0.0, None)
    E = Q @ (np.sqrt(2.0 * lam)[:, None] * U)
    return E, W


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def m_barra(ell: float, rhos, sigma: np.ndarray, mejor_de: int, decisivo: str, q: int):
    """M̄_f(expit(ℓ̄+ρ), expit(ℓ̄−ρ); Σ) para un vector de ρ (una sola llamada vectorizada)."""
    rhos = np.atleast_1d(np.asarray(rhos, dtype=float))
    E, W = nodos_sigma(sigma, q)
    la = ell + rhos[:, None] + E[0][None, :]
    lb = ell - rhos[:, None] + E[1][None, :]
    P = p_partido(expit(la), expit(lb), mejor_de, decisivo)
    return P @ W


def sigma_eps(s_eps: float, r_eps: float) -> np.ndarray:
    v = s_eps * s_eps
    return np.array([[v, r_eps * v], [r_eps * v, v]])


# ---------------------------------------------------------------------------------------------------------
# 4. Hiperparámetros (formato canónico de esta referencia, por circuito)
# ---------------------------------------------------------------------------------------------------------
@dataclass
class Hiper:
    ell: dict                     # ℓ̄_{c,s}
    kappa: dict                   # κ^R_{c,s}; Hard ≡ 1
    tau_theta: float              # √(varianza por día) del paseo de θ
    tau_d: float                  # √(varianza por día) del paseo de d
    inact_umbral_dias: float      # 60
    inact_var: float              # salto de Var(θ) por inactividad
    sigma_d: dict                 # escalas de Σ_d por superficie
    omega: list                   # 4×4, orden SUPERFICIES
    zeta: float
    var_d_iota: float
    phi: tuple                    # (φ₁, φ₂) ≥ 0
    lam: float                    # λ del descuento
    F90: float                    # bisagra (minutos ponderados)
    ventana_h: float              # 96
    gamma: dict                   # γ_k por contexto
    s_eps: float
    r_eps: float
    prior_a: float
    prior_b: float
    prior_var: float
    theta_sin_ranking: float
    omega_juegos: float = 0.0
    q: int = 20                   # cuadratura en la actualización (Σ_ε: q = 11 → ~6e-7; q = 20 → ~1e-11)
    q_pred: int = 60              # cuadratura en la predicción (Σ_m con J V Jᵀ: q = 11 se equivoca hasta ~5e-4)
    h_dif: float = 2e-3
    extra: dict = field(default_factory=dict)

    def validar(self):
        if any(f < 0 for f in self.phi):
            raise ValueError("φ_j ≥ 0 por construcción (§D.3)")
        if abs(self.kappa.get("Hard", 1.0) - 1.0) > 1e-12:
            raise ValueError("identificación: κ_Hard ≡ 1")
        if self.omega_juegos != 0.0:
            raise NotImplementedError("ω > 0 (margen en juegos) no está en la referencia")
        return self

    def sigma_d_mat(self) -> np.ndarray:
        s = np.array([self.sigma_d[x] for x in SUPERFICIES], dtype=float)
        return np.diag(s) @ np.asarray(self.omega, dtype=float) @ np.diag(s)

    def prior(self, puntos) -> tuple[np.ndarray, np.ndarray]:
        m = np.zeros(N_EST)
        if puntos is None or (isinstance(puntos, float) and math.isnan(puntos)) or pd.isna(puntos):
            m[I_THETA] = self.theta_sin_ranking
        else:
            m[I_THETA] = self.prior_a + self.prior_b * math.log1p(max(float(puntos), 0.0))
        P = np.zeros((N_EST, N_EST))
        P[I_THETA, I_THETA] = self.prior_var
        P[1:5, 1:5] = self.sigma_d_mat()
        P[I_IOTA, I_IOTA] = self.var_d_iota
        return m, P


def hiper_demo(circuito: str = "atp") -> Hiper:
    """Valores de demostración (NO ajustados) para las pruebas y la prueba de humo sobre datos reales."""
    ell = {"atp": {"Clay": 0.50, "Grass": 0.75, "Hard": 0.62, "Indoor": 0.70},
           "wta": {"Clay": 0.25, "Grass": 0.40, "Hard": 0.32, "Indoor": 0.36}}[circuito]
    om = np.full((4, 4), 0.5); np.fill_diagonal(om, 1.0)
    return Hiper(ell=ell, kappa={"Clay": 0.95, "Grass": 1.05, "Hard": 1.0, "Indoor": 1.0},
                 tau_theta=0.004, tau_d=0.002, inact_umbral_dias=60, inact_var=0.005,
                 sigma_d={s: 0.05 for s in SUPERFICIES}, omega=om.tolist(), zeta=1.0, var_d_iota=0.0025,
                 phi=(0.01, 0.03), lam=0.75, F90=150.0, ventana_h=96.0,
                 gamma={k: 0.0 for k in CONTEXTOS}, s_eps=0.22, r_eps=-0.45,
                 prior_a=-0.35, prior_b=0.06, prior_var=0.04, theta_sin_ranking=-0.35).validar()


# ---------------------------------------------------------------------------------------------------------
# 5. Fatiga
# ---------------------------------------------------------------------------------------------------------
def fatiga(historial: list, corte: float, t_ref: float, hp: Hiper) -> tuple[float, bool]:
    """F = Σ λ^Δ·minutos sobre los partidos terminados en las `ventana_h` horas anteriores a t_ref y visibles
    antes del corte. historial: lista de (vis, fin, minutos|None, jugado) en días. Devuelve (F, desconocida)."""
    F, desconocida = 0.0, False
    for vis, fin, minutos, jugado in historial:
        if not vis < corte:
            continue
        delta = t_ref - fin
        if delta < 0 or delta > hp.ventana_h / 24.0:
            continue
        if minutos is None:
            desconocida = desconocida or jugado
            continue
        F += hp.lam**delta * minutos
    return F, desconocida


def g_fatiga(F: float, hp: Hiper) -> tuple[float, float]:
    return F / 60.0, max(0.0, F - hp.F90) / 60.0


def termino_fatiga(Fa: float, Fb: float, hp: Hiper) -> float:
    ga, gb = g_fatiga(Fa, hp), g_fatiga(Fb, hp)
    return hp.phi[0] * (ga[0] - gb[0]) + hp.phi[1] * (ga[1] - gb[1])


# ---------------------------------------------------------------------------------------------------------
# 6. Filtro
# ---------------------------------------------------------------------------------------------------------
@dataclass
class Partido:
    """Lo que el filtro necesita de un partido (entradas as-of; `ganador` solo para actualizar)."""
    superficie: str | None
    indoor: bool | None
    mejor_de: int
    decisivo: str
    contextos: dict
    corte: float                  # días
    t_ref: float                  # días
    puntos_a: float | None = None
    puntos_b: float | None = None


def vector_g(p: Partido, hp: Hiper) -> np.ndarray:
    """∂ρ/∂(x_A, x_B) (12 componentes): ρ es lineal en el estado."""
    mult = hp.kappa[p.superficie] * (1.0 + sum(hp.gamma.get(k, 0.0) * float(bool(p.contextos.get(k, False)))
                                                 for k in CONTEXTOS))
    iota = 1.0 if (p.superficie == "Clay" and p.indoor is True) else 0.0
    ga = np.zeros(N_EST)
    ga[I_THETA] = mult
    ga[1 + SUPERFICIES.index(p.superficie)] = 1.0
    ga[I_IOTA] = hp.zeta * iota
    return np.concatenate([ga, -ga])


class Filtro:
    def __init__(self, hp: Hiper):
        self.hp = hp.validar()
        self.m: dict = {}
        self.P: dict = {}
        self.t: dict = {}
        self.hist: dict = {}       # jugador -> lista (vis, fin, minutos, jugado)
        self.n_act: dict = {}      # nº de actualizaciones por jugador

    # -- estado ---------------------------------------------------------------------------------------------
    def estado_en(self, j, t: float, puntos) -> tuple[np.ndarray, np.ndarray, bool]:
        """(m, P) del jugador propagado a t, sin modificar el filtro. Tercer valor: ¿viene del prior?"""
        if j not in self.m:
            m, P = self.hp.prior(puntos)
            return m, P, True
        m, P = self.m[j].copy(), self.P[j].copy()
        dt = max(0.0, t - self.t[j])
        P[I_THETA, I_THETA] += self.hp.tau_theta**2 * dt
        if dt > self.hp.inact_umbral_dias:
            P[I_THETA, I_THETA] += self.hp.inact_var
        for k in range(1, N_EST):
            P[k, k] += self.hp.tau_d**2 * dt
        return m, P, False

    def _rho_y_var(self, p: Partido, a, b):
        ma, Pa, pra = self.estado_en(a, p.corte, p.puntos_a)
        mb, Pb, prb = self.estado_en(b, p.corte, p.puntos_b)
        Fa, da = fatiga(self.hist.get(a, []), p.corte, p.t_ref, self.hp)
        Fb, db = fatiga(self.hist.get(b, []), p.corte, p.t_ref, self.hp)
        g = vector_g(p, self.hp)
        m = np.concatenate([ma, mb])
        V = np.zeros((2 * N_EST, 2 * N_EST)); V[:N_EST, :N_EST] = Pa; V[N_EST:, N_EST:] = Pb
        rho = float(g @ m) - termino_fatiga(Fa, Fb, self.hp)
        return dict(g=g, m=m, V=V, rho=rho, prior_a=pra, prior_b=prb, fat_desc=da or db, Fa=Fa, Fb=Fb)

    # -- predicción -----------------------------------------------------------------------------------------
    def predecir(self, p: Partido, a, b) -> dict:
        r = self._rho_y_var(p, a, b)
        v = float(r["g"] @ r["V"] @ r["g"])
        v_pred = v + float(self.hp.extra.get("c_inf", 0.0))
        S = sigma_eps(self.hp.s_eps, self.hp.r_eps) + v_pred * np.array([[1.0, -1.0], [-1.0, 1.0]])
        pi = float(m_barra(self.hp.ell[p.superficie], [r["rho"]], S, p.mejor_de, p.decisivo, self.hp.q_pred)[0])
        return dict(pi=pi, rho=r["rho"], var_rho=v_pred, ell=self.hp.ell[p.superficie], sigma_m=S, prior_a=r["prior_a"], prior_b=r["prior_b"],
                    fatiga_desconocida=r["fat_desc"], F_a=r["Fa"], F_b=r["Fb"])

    # -- actualización --------------------------------------------------------------------------------------
    def actualizar(self, p: Partido, a, b, gana_a: bool):
        r = self._rho_y_var(p, a, b)
        d1, d2 = self.derivadas(p, r["rho"], gana_a)
        c = max(-d2, 0.0)
        g, V, m = r["g"], r["V"], r["m"]
        Vg = V @ g
        Vp = V - c * np.outer(Vg, Vg) / (1.0 + c * float(g @ Vg))     # (V⁻¹ + c g gᵀ)⁻¹ (Sherman–Morrison)
        mp = m + Vp @ g * d1                                           # m + V⁺ ∇ℓ(m)
        for j, sl in ((a, slice(0, N_EST)), (b, slice(N_EST, 2 * N_EST))):
            self.m[j] = mp[sl].copy()
            self.P[j] = Vp[sl, sl].copy()
            self.t[j] = max(p.corte, self.t.get(j, -np.inf))
            self.n_act[j] = self.n_act.get(j, 0) + 1

    def derivadas(self, p: Partido, rho: float, gana_a: bool) -> tuple[float, float]:
        """ℓ'(ρ) y ℓ''(ρ) del log de la verosimilitud del resultado, por diferencias centrales con extrapolación
        de Richardson (pasos h y h/2: error O(h⁴)); M̄ con Σ_ε."""
        h = self.hp.h_dif
        pasos = np.array([-h, -h / 2, 0.0, h / 2, h])
        M = m_barra(self.hp.ell[p.superficie], rho + pasos, sigma_eps(self.hp.s_eps, self.hp.r_eps),
                    p.mejor_de, p.decisivo, self.hp.q)
        L = np.log(M) if gana_a else np.log1p(-M)
        d1_h, d1_h2 = (L[4] - L[0]) / (2 * h), (L[3] - L[1]) / h
        d2_h, d2_h2 = (L[4] - 2 * L[2] + L[0]) / h**2, (L[3] - 2 * L[2] + L[1]) / (h / 2) ** 2
        return (4 * d1_h2 - d1_h) / 3, (4 * d2_h2 - d2_h) / 3

    def registrar_minutos(self, j, vis: float, fin: float, minutos, jugado: bool):
        self.hist.setdefault(j, []).append((vis, fin, minutos, jugado))
        if len(self.hist[j]) > 40:                                      # solo hace falta la ventana reciente
            self.hist[j] = self.hist[j][-40:]


# ---------------------------------------------------------------------------------------------------------
# 7. Ejecución sobre la exportación punto en el tiempo
# ---------------------------------------------------------------------------------------------------------
def _dias(ts) -> float:
    if ts is None or pd.isna(ts):
        return float("nan")
    return pd.Timestamp(ts).value / 86_400e9


def _opt(x):
    return None if x is None or pd.isna(x) else x


def cargar_entrada(dir_export: str) -> pd.DataFrame:
    """Eventos (orden por visible_resultado_utc) unidos a las entradas as-of de partidos que el filtro usa."""
    ev = pd.read_parquet(f"{dir_export}/eventos_resultado.parquet")
    pa = pd.read_parquet(f"{dir_export}/partidos.parquet",
                         columns=["partido_key", "semana_previa_gs", "por_equipos", "jjoo", "puntos_1", "puntos_2",
                                  "rank_1", "rank_2", "n_prev_1", "n_prev_2", "excluir_motivo", "marcas"])
    df = ev.merge(pa, on="partido_key", how="left", validate="one_to_one").sort_values("orden", kind="stable")
    if not df["visible_resultado_utc"].is_monotonic_increasing:
        raise ValueError("`orden` no sigue visible_resultado_utc")
    return df.reset_index(drop=True)


def _partido_de_fila(r) -> Partido:
    corte = _dias(r.corte_utc)
    t_ref = _dias(r.inicio_utc)
    return Partido(superficie=_opt(r.superficie), indoor=_opt(r.indoor), mejor_de=int(r.mejor_de),
                   decisivo=r.formato_decisivo, contextos={k: bool(getattr(r, k)) for k in CONTEXTOS},
                   corte=corte, t_ref=corte if math.isnan(t_ref) else t_ref,
                   puntos_a=_opt(r.puntos_1), puntos_b=_opt(r.puntos_2))


def pronosticable(r) -> str | None:
    """Motivo por el que no se pronostica (None = se pronostica)."""
    if _opt(r.excluir_motivo) is not None:
        return "excluido"
    if _opt(r.superficie) is None:
        return "superficie_desconocida"
    if r.formato_decisivo not in DECISIVOS or int(r.mejor_de) not in (3, 5):
        return "formato_desconocido"
    for lado in (1, 2):
        if int(getattr(r, f"n_prev_{lado}")) == 0 and _opt(getattr(r, f"puntos_{lado}")) is None:
            return "jugador_sin_historia"
    return None


def _ejecutar_circuito(args_tuple):
    d, hp, circ, objetivo, hasta, progreso = args_tuple
    if hasta is not None:
        d = d[d["corte_utc"] < hasta]
    filtro = Filtro(hp)
    obj = d[d["partido_key"].isin(objetivo)].sort_values("corte_utc", kind="stable")
    obj_it = list(obj.itertuples(index=False))
    salida = []
    k = 0
    for n, r in enumerate(d.itertuples(index=False)):
        vis = r.visible_resultado_utc
        while k < len(obj_it) and obj_it[k].corte_utc <= vis:
            salida.append(_pronostico(filtro, obj_it[k], circ)); k += 1
        _consumir(filtro, r)
        if progreso and n % progreso == 0:
            print(f"  {circ} {n}/{len(d)} {vis}", flush=True)
    while k < len(obj_it):
        salida.append(_pronostico(filtro, obj_it[k], circ)); k += 1
    return salida


def ejecutar(df: pd.DataFrame, hp_por_circuito: dict, objetivo: set, hasta=None, progreso: int = 0, paralelo: bool = True) -> pd.DataFrame:
    """Recorre los eventos de cada circuito en orden de visibilidad y pronostica los partidos de `objetivo`
    (partido_key) justo antes de consumir el primer evento con vis ≥ su corte."""
    tareas = [
        (df[df["circuito"] == circ].copy(), hp, circ, objetivo, hasta, progreso)
        for circ, hp in hp_por_circuito.items()
    ]
    if paralelo and len(tareas) > 1:
        from concurrent.futures import ProcessPoolExecutor
        salida = []
        with ProcessPoolExecutor(max_workers=min(2, len(tareas))) as ex:
            for res in ex.map(_ejecutar_circuito, tareas):
                salida.extend(res)
    else:
        salida = []
        for t in tareas:
            salida.extend(_ejecutar_circuito(t))
    return pd.DataFrame(salida)


def _pronostico(filtro: Filtro, r, circ) -> dict:
    base = dict(partido_key=r.partido_key, circuito=circ, corte_utc=r.corte_utc, ganador_real=_opt(r.ganador),
                n_prev_1=int(r.n_prev_1), n_prev_2=int(r.n_prev_2))
    motivo = pronosticable(r)
    if motivo is not None:
        return {**base, "pi_ref": float("nan"), "motivo": motivo}
    out = filtro.predecir(_partido_de_fila(r), r.jugador_1, r.jugador_2)
    pi_q11 = float(m_barra(out["ell"], [out["rho"]], out["sigma_m"], int(r.mejor_de), r.formato_decisivo, 11)[0])
    return {**base, "pi_ref": out["pi"], "pi_ref_q11": pi_q11, "motivo": None, "rho": out["rho"],
            "var_rho": out["var_rho"], "ell": out["ell"], "mejor_de": int(r.mejor_de), "decisivo": r.formato_decisivo,
            "prior_1": out["prior_a"], "prior_2": out["prior_b"], "fatiga_desconocida": out["fatiga_desconocida"],
            "F_1": out["F_a"], "F_2": out["F_b"],
            "historia_corta": int(r.n_prev_1) < 20 or int(r.n_prev_2) < 20}


def _consumir(filtro: Filtro, r):
    p = _partido_de_fila(r)
    vis = _dias(r.visible_resultado_utc)
    jugado = r.estado != "walkover" and r.estado != "cancelado"
    for j, mins in ((r.jugador_1, _opt(r.minutos_1)), (r.jugador_2, _opt(r.minutos_2))):
        if r.estado == "walkover":
            mins = 0.0
        fin = p.t_ref + mins / 1440.0 if (mins is not None and not math.isnan(_dias(r.inicio_utc))) else vis
        if r.estado != "cancelado":
            filtro.registrar_minutos(j, vis, fin, None if mins is None else float(mins), jugado)
    if bool(r.actualiza_rating) and p.superficie is not None and p.decisivo in DECISIVOS and _opt(r.ganador) is not None:
        filtro.actualizar(p, r.jugador_1, r.jugador_2, int(r.ganador) == 1)
