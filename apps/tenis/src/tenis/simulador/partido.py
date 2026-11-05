"""Distribución conjunta EXACTA del marcador del partido (plan G.3), set a set, con el saque propagado entre sets.

Motor común a `distribucion_partido` (un solo par p_A, p_B) y a `mezcla` (nodos de cuadratura): se trabaja con
prefijos de sets aún vivos y un eje «quién saca el set siguiente» (t); al añadir un set con resultado o,
t' = t XOR paridad(o). La suma sobre nodos se hace dentro (einsum / producto de matrices), así que la mezcla
de 81 nodos cuesta casi lo mismo que un solo par. Primer sacador del partido: desconocido ⇒ 50/50
(`firstToServe` está prohibido como predictor); 'A'/'B' solo para verificación.
"""
import numpy as np

from ._comun import validar_lado, validar_p
from .formato import Formato, validar_formato
from .resultado import DistPartido
from .set_ import MAX_JUEGOS_CONTRATO, probs_set

SACA_DESCONOCIDO = "desconocido"


def pesos_primer_sacador(saca_primero: str) -> np.ndarray:
    if saca_primero == SACA_DESCONOCIDO:
        return np.array([0.5, 0.5])
    return np.array([1.0, 0.0]) if validar_lado(saca_primero) else np.array([0.0, 1.0])


def tablas(p_a: np.ndarray, p_b: np.ndarray, formato: Formato, max_juegos: int = MAX_JUEGOS_CONTRATO,
           sigmas: tuple = (0, 1)):
    """Tablas por nodo del set normal y del decisivo (se calculan una vez y sirven para todos los sets)."""
    reg = probs_set(p_a, p_b, "tiebreak_7", sigmas=sigmas)
    dec = reg if formato.decisivo == "tiebreak_7" else probs_set(p_a, p_b, formato.decisivo, max_juegos, sigmas)
    return reg, dec


def conjunta(formato: Formato, reg, dec, w: np.ndarray, c: np.ndarray) -> DistPartido:
    """Masa de cada marcador completo, mezclada sobre nodos (peso w) y primer sacador (peso c).

    a[n, t, P] = masa del prefijo P en el nodo n con t = quien saca el set siguiente. La masa mezclada de cada
    extensión (P, o) es Σ_{n,t} w_n a[n,t,P] T[n,t,o] = producto de matrices; solo los prefijos que siguen vivos
    se expanden por nodo, con t' = t XOR paridad(o). El último set normal y el decisivo van fusionados
    (B[n,t,o,od] = T[n,t,o]·T_dec[n, t XOR paridad(o), od]) para no expandir por nodo el prefijo más grande."""
    (cat_r, t_r, _), (cat_d, t_d, jc_d) = reg, dec
    n, nr, nd, need = t_r.shape[0], len(cat_r), len(cat_d), formato.sets_para_ganar
    tr = t_r.reshape(n * 2, nr)
    a = np.broadcast_to(c[None, :, None], (n, 2, 1)).copy()
    pref = {"cod": np.zeros((1, 0), dtype=int), "sa": np.zeros(1, int), "sb": np.zeros(1, int),
            "jt": np.zeros(1), "dif": np.zeros(1, int), "ntb": np.zeros(1, int), "ps": np.zeros(1, bool)}
    finales = []
    for k in range(formato.mejor_de - 1):
        p = a.shape[2]
        am = (a * w[:, None, None]).reshape(n * 2, p)
        f = am.T @ tr                                                        # (p, nr) masa mezclada
        pi, oi = np.divmod(np.arange(p * nr), nr)
        ext = _extender(pref, pi, oi, cat_r, 0, k == 0)
        fin = (ext["sa"] == need) | (ext["sb"] == need)
        finales.append({nombre: v[fin] for nombre, v in ext.items()} | {"prob": f.reshape(-1)[fin]})
        pref = {nombre: v[~fin] for nombre, v in ext.items()}
        if k < formato.mejor_de - 2:
            pv, ov = pi[~fin], oi[~fin]
            src = np.arange(2)[:, None] ^ cat_r.paridad[ov][None, :]       # (2, k): sacador del set jugado
            a = a[:, src, pv[None, :]] * t_r[:, src, ov[None, :]]
            continue
        sig = np.arange(2)[:, None] ^ cat_r.paridad[None, :]               # sacador del decisivo
        b = t_r[..., None] * t_d[:, sig, :]                                  # (n, 2, nr, nd)
        g = (am.T @ b.reshape(n * 2, nr * nd)).reshape(p * nr, nd)[~fin]
        jcola = np.zeros_like(g)
        if cat_d.cola.any():
            bj = b[..., cat_d.cola] * jc_d[:, sig][..., None]
            jcola[:, cat_d.cola] = (am.T @ bj.reshape(n * 2, -1)).reshape(p * nr, -1)[~fin]
        j, od = np.divmod(np.arange(g.size), nd)
        finales.append(_extender(pref, j, od, cat_d, nr, False) | {"prob": g.reshape(-1), "jcola": jcola.reshape(-1)})
    return DistPartido.desde_finales(formato, cat_r, cat_d, finales)


def _extender(pref: dict, pi: np.ndarray, oi: np.ndarray, cat, desplazamiento: int, primero: bool) -> dict:
    """Prefijo pi + set con resultado oi: actualiza sets, juegos (cola = 0 aquí; su media se suma al final),
    diferencia de juegos (cola ±2), tiebreaks y ganador del 1.er set."""
    gana = cat.gana_a[oi]
    return {"cod": np.concatenate([pref["cod"][pi], (oi + desplazamiento)[:, None]], axis=1),
            "sa": pref["sa"][pi] + gana, "sb": pref["sb"][pi] + ~gana,
            "jt": pref["jt"][pi] + np.where(cat.cola[oi], 0.0, cat.juegos[oi]),
            "dif": pref["dif"][pi] + np.where(cat.cola[oi], np.where(gana, 2, -2), cat.ga[oi] - cat.gb[oi]),
            "ntb": pref["ntb"][pi] + cat.tb[oi], "ps": gana if primero else pref["ps"][pi]}


def distribucion_partido(p_a, p_b, formato: Formato, saca_primero: str = SACA_DESCONOCIDO,
                         max_juegos: int = MAX_JUEGOS_CONTRATO) -> DistPartido:
    """Conjunta exacta para un par (p_A, p_B) SIN incertidumbre (la del pronóstico es `mezcla.distribucion_mezclada`)."""
    formato = validar_formato(formato)
    pa = np.atleast_1d(validar_p(p_a, "p_a"))
    pb = np.atleast_1d(validar_p(p_b, "p_b"))
    if pa.shape != (1,) or pb.shape != (1,):
        raise ValueError("distribucion_partido recibe un solo par (p_a, p_b)")
    reg, dec = tablas(pa, pb, formato, max_juegos)
    return conjunta(formato, reg, dec, np.ones(1), pesos_primer_sacador(saca_primero))


def prob_ganar_nodos(p_a: np.ndarray, p_b: np.ndarray, formato: Formato,
                     max_juegos: int = MAX_JUEGOS_CONTRATO) -> np.ndarray:
    """P(A gana) por nodo con la forma de sets (neutralidad del saque, A31 §3.3): rápido para invertir."""
    (cat_r, t_r, _), (cat_d, t_d, _) = tablas(p_a, p_b, formato, max_juegos, sigmas=(0,))
    s = t_r[:, 0, cat_r.gana_a].sum(axis=1)
    sd = t_d[:, 0, cat_d.gana_a].sum(axis=1)
    if formato.mejor_de == 3:
        return s * s + 2.0 * s * (1.0 - s) * sd
    return s**3 + 3.0 * s**3 * (1.0 - s) + 6.0 * s * s * (1.0 - s) ** 2 * sd
