"""
Banco de pruebas del motor C (fase F4): córners y amarillas por lado con binomial negativa (`model/conteos.py`).

Todos los rasgos son PREVIOS al partido: medias exponenciales de cada equipo y de cada árbitro calculadas solo con
partidos anteriores (desplazadas una posición) y encogidas hacia la media de la liga; el 1X2 sin margen del cierre
(sabido antes del saque) da la supremacía y la igualdad q(1−q). Reajuste cada `paso_dias`; ventana de 4 años.
"""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd

from ..model.conteos import RegresionNB, pmf_suma
from .metrics import diebold_mariano, murphy

MAXIMO = {"corners": 25, "yellow": 14}
LINEAS = {"corners": (8.5, 9.5, 10.5), "yellow": (3.5, 4.5, 5.5)}


def clave_arbitro(nombre) -> str | None:
    """Nombre y último apellido sin acentos: une «Manuel Oliveira» con «Manuel António Rodrigues Oliveira»."""
    if not isinstance(nombre, str) or not nombre.strip():
        return None
    s = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower().split()
    return f"{s[0]} {s[-1]}" if len(s) > 1 else s[0]


def _ewm_previa(serie: pd.Series, grupos: pd.Series, vida: float) -> pd.Series:
    """Media exponencial de los valores ANTERIORES de cada grupo (el propio partido no cuenta)."""
    return serie.groupby(grupos).transform(lambda s: s.ewm(halflife=vida, ignore_na=True).mean().shift(1))


def _previos(serie: pd.Series, grupos: pd.Series) -> pd.Series:
    return serie.notna().astype(int).groupby(grupos).cumsum() - serie.notna().astype(int)


def rasgos(df: pd.DataFrame, contexto: pd.DataFrame, derbis: pd.DataFrame, equipo: pd.DataFrame,
           objetivo: str, vida: float = 10.0, k: float = 6.0) -> pd.DataFrame:
    """Una fila por partido y lado con la respuesta `y` y los rasgos previos."""
    c = f"{objetivo}"
    base = df.merge(contexto[["match_id", "arbitro"]], on="match_id", how="left")
    faltas = equipo[equipo["periodo"] == 0].pivot_table(index="match_id", columns="side", values="faltas")
    base = base.merge(faltas.add_suffix("_faltas"), left_on="match_id", right_index=True, how="left")
    filas = []
    for side, opp in (("home", "away"), ("away", "home")):
        filas.append(pd.DataFrame({
            "match_id": base["match_id"], "kickoff_utc": base["kickoff_utc"], "semana": base["semana"],
            "league_id": base["league_id"], "local": int(side == "home"),
            "equipo": base[f"{side}_team"], "rival": base[f"{opp}_team"],
            "y": base[f"{side}_{c}"], "y_rival": base[f"{opp}_{c}"],
            "goles": base[f"{side}_goals"], "goles_rival": base[f"{opp}_goals"],
            "faltas": base.get(f"{side}_faltas"),
            "p_gana": base[f"mk_{side}"], "p_pierde": base[f"mk_{opp}"], "p_local": base["mk_home"],
            "arbitro": (base["arbitro"].fillna(base["arbitro_matches"])).map(clave_arbitro),
            "total": base[f"home_{c}"] + base[f"away_{c}"]}))
    L = pd.concat(filas, ignore_index=True).sort_values(["kickoff_utc", "match_id", "local"]).reset_index(drop=True)
    # medias de la liga por lado, solo con partidos anteriores
    ls = L["league_id"] + L["local"].astype(str)
    liga_y = L.groupby(ls)["y"].transform(lambda s: s.expanding().mean().shift(1))
    liga_g = L.groupby(ls)["goles"].transform(lambda s: s.expanding().mean().shift(1))
    liga_f = L.groupby(ls)["faltas"].transform(lambda s: s.expanding().mean().shift(1))

    def encoger(media, n, prior):
        return (media.fillna(prior) * n + prior * k) / (n + k)

    for col, prior in (("y", liga_y), ("y_rival", liga_y), ("goles", liga_g), ("goles_rival", liga_g),
                       ("faltas", liga_f)):
        L[f"m_{col}"] = encoger(_ewm_previa(L[col], L["equipo"], vida), _previos(L[col], L["equipo"]), prior)
    # lo que concede el rival: su media de `y_rival` (lo que le hacen a él)
    por_equipo = L.set_index(["match_id", "equipo"])
    rival = por_equipo.loc[list(zip(L["match_id"], L["rival"])), ["m_y_rival", "m_goles_rival", "m_faltas"]]
    L["rival_concede"] = rival["m_y_rival"].to_numpy()
    L["rival_encaja_goles"] = rival["m_goles_rival"].to_numpy()
    L["rival_faltas"] = rival["m_faltas"].to_numpy()
    # árbitro: media del TOTAL del partido en sus partidos anteriores, encogida a la de la liga (k = 10 partidos)
    porp = L[L["local"] == 1][["match_id", "kickoff_utc", "league_id", "arbitro", "total"]].copy()
    liga_t = porp.groupby("league_id")["total"].transform(lambda s: s.expanding().mean().shift(1))
    con_arb = porp["arbitro"].notna()
    m_arb = _ewm_previa(porp["total"].where(con_arb), porp["arbitro"].fillna("_"), 30.0)
    n_arb = _previos(porp["total"].where(con_arb), porp["arbitro"].fillna("_"))
    porp["arbitro_rel"] = np.log((m_arb.fillna(liga_t) * n_arb + liga_t * 10) / (n_arb + 10) / liga_t)
    porp.loc[~con_arb, "arbitro_rel"] = 0.0
    L = L.merge(porp[["match_id", "arbitro_rel"]], on="match_id", how="left")
    d = set(map(tuple, derbis[["equipo_a", "equipo_b"]].astype(str).to_numpy()))
    L["derbi"] = [int((a, b) in d or (b, a) in d) for a, b in zip(L["equipo"], L["rival"])]
    L["supremacia"] = L["p_gana"] - L["p_pierde"]
    L["igualdad"] = L["p_local"] * (1 - L["p_local"])
    L["log_liga"] = np.log(liga_y)
    return L


VARIANTES = {
    # nombre: (columnas de log μ, columnas de log κ)
    "c0_liga": (["log_liga", "local"], []),
    "c1_equipos": (["log_liga", "local", "l_m_y", "l_rival_concede"], []),
    "c2_yip": (["log_liga", "local", "l_m_y", "l_rival_concede", "l_goles_esp", "supremacia"], ["abs_sup"]),
    "t1_equipos": (["log_liga", "local", "l_m_y", "l_rival_concede"], []),
    "t2_arbitro": (["log_liga", "local", "l_m_y", "l_rival_concede", "arbitro_rel"], []),
    "t3_dawson": (["log_liga", "local", "l_m_y", "l_rival_concede", "arbitro_rel", "derbi", "igualdad",
                   "supremacia", "l_faltas", "l_rival_faltas"], []),
}


def matriz(L: pd.DataFrame) -> pd.DataFrame:
    X = L.copy()
    X["l_m_y"] = np.log(X["m_y"] / np.exp(X["log_liga"]))
    X["l_rival_concede"] = np.log(X["rival_concede"] / np.exp(X["log_liga"]))
    X["l_goles_esp"] = np.log((X["m_goles"] + X["rival_encaja_goles"]) / 2)
    X["l_faltas"] = np.log(X["m_faltas"]); X["l_rival_faltas"] = np.log(X["rival_faltas"])
    X["abs_sup"] = X["supremacia"].abs()
    return X


def walk_forward(L: pd.DataFrame, objetivo: str, variantes: list[str], desde, paso_dias: int = 28,
                 anios: float = 4.0, por_lado: bool = False) -> pd.DataFrame:
    """Distribución del total por partido y variante (fuera de muestra); columnas p0..pMAX."""
    X = matriz(L)
    corte = pd.Timestamp(desde, tz="UTC"); fin = X["kickoff_utc"].max() + pd.Timedelta(seconds=1)
    mx = MAXIMO[objetivo]
    salida = []
    while corte < fin:
        sig = corte + pd.Timedelta(days=paso_dias)
        ent = X[(X["kickoff_utc"] < corte) & (X["kickoff_utc"] >= corte - pd.Timedelta(days=365 * anios))]
        pru = X[(X["kickoff_utc"] >= corte) & (X["kickoff_utc"] < sig)]
        for v in variantes:
            cx, cz = VARIANTES[v]
            # una sola fila con log(0) deja la verosimilitud en NaN y el ajuste se queda en el punto inicial
            e = ent[np.isfinite(ent[cx + cz + ["y"]].to_numpy(float)).all(1)]
            p = pru[np.isfinite(pru[cx + cz].to_numpy(float)).all(1)]
            if len(e) < 1000 or p.empty:
                continue
            m = RegresionNB().fit(e[cx].to_numpy(), e["y"].to_numpy(), e[cz].to_numpy() if cz else None)
            pm = m.pmf(p[cx].to_numpy(), mx, p[cz].to_numpy() if cz else None)
            lado = pd.DataFrame(pm).assign(match_id=p["match_id"].to_numpy(), local=p["local"].to_numpy())
            h = lado[lado["local"] == 1].set_index("match_id").drop(columns="local")
            a = lado[lado["local"] == 0].set_index("match_id").drop(columns="local")
            comunes = h.index.intersection(a.index)
            tot = pmf_suma(h.loc[comunes].to_numpy(), a.loc[comunes].to_numpy())
            fila = pd.DataFrame(tot, index=comunes).add_prefix("p")
            if por_lado:  # para hándicaps (local − visita) hace falta la distribución de cada equipo
                fila = fila.join(h.loc[comunes].add_prefix("h")).join(a.loc[comunes].add_prefix("a"))
            salida.append(fila.assign(variante=v).reset_index())
        corte = sig
    return pd.concat(salida, ignore_index=True)


def evaluar(pred: pd.DataFrame, L: pd.DataFrame, objetivo: str, desde, hasta=None,
            ref: str = "c0_liga") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Log score del total, Brier y Murphy en las líneas de más/menos, PIT; sobre las filas comunes."""
    reales = L[L["local"] == 1].set_index("match_id")[["kickoff_utc", "semana", "total"]].dropna()
    reales = reales[reales["kickoff_utc"] >= pd.Timestamp(desde, tz="UTC")]
    if hasta:
        reales = reales[reales["kickoff_utc"] < pd.Timestamp(hasta, tz="UTC")]
    ancho = {v: g.set_index("match_id").drop(columns="variante") for v, g in pred.groupby("variante")}
    comunes = reales.index
    for a in ancho.values():
        comunes = comunes.intersection(a.index)
    r = reales.loc[comunes]
    y = r["total"].to_numpy(int)
    filas, perd = [], {}
    for v, a in ancho.items():
        P = a.loc[comunes].to_numpy(float)
        yy = np.clip(y, 0, P.shape[1] - 1)
        ls = -np.log(np.clip(P[np.arange(len(yy)), yy], 1e-15, 1))
        perd[v] = ls
        cdf = np.cumsum(P, 1)
        pit = cdf[np.arange(len(yy)), yy] - P[np.arange(len(yy)), yy] / 2  # PIT aleatorizado en su punto medio
        fila = {"variante": v, "n": len(y), "log": ls.mean(), "media_pred": (P * np.arange(P.shape[1])).sum(1).mean(),
                "media_real": y.mean(), "pit_chi2": float(((np.histogram(pit, bins=10, range=(0, 1))[0]
                                                         - len(y) / 10) ** 2 / (len(y) / 10)).sum())}
        for linea in LINEAS[objetivo]:
            p_mas = P[:, int(linea) + 1:].sum(1)
            d = murphy(p_mas, (y > linea).astype(float))
            fila[f"brier_{linea}"], fila[f"mcb_{linea}"], fila[f"dsc_{linea}"] = d["score"], d["mcb"], d["dsc"]
        filas.append(fila)
    res = pd.DataFrame(filas).sort_values("log").reset_index(drop=True)
    comp = [dict(variante=v, frente_a=ref, **{k: x for k, x in diebold_mariano(perd[v], perd[ref],
                                                                               r["semana"].to_numpy()).items()
                                              if k in ("delta", "t")}) for v in perd if v != ref]
    return res, pd.DataFrame(comp)
