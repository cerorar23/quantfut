"""
Archivo de BetsAPI (bet365) de fútbol: lectura, emparejamiento con `matches` y liquidación de líneas asiáticas.

Cada archivo `odds/<id>.json.gz` trae el evento (marcador, estadísticas finales, córners) y, por mercado `1_1`..`1_8`,
la serie de cambios de cuota con `add_time`; una fila lleva la línea principal de ese instante (no la escalera
entera). Antes del saque `time_str` es nulo; durante el partido trae el minuto, el marcador (`ss`) y el de córners
(`ss2`, local-visita).

    1_1 1X2   1_2 hándicap asiático   1_3 goles   1_4 córners   1_5 hándicap 1.ª parte
    1_6 goles 1.ª parte   1_7 córners 1.ª parte   1_8 resultado al descanso

Solo lectura de archivos locales; no toca la base.
"""
from __future__ import annotations

import gzip
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

LIGAS = {"gb_premier_league": "gb.premier_league", "es_laliga": "es.laliga", "it_serie_a": "it.serie_a",
         "de_bundesliga": "de.bundesliga", "fr_ligue1": "fr.ligue_1", "nl_eredivisie": "nl.eredivisie",
         "pt_primeira": "pt.primeira", "br_serie_a": "br.serie_a", "mx_liga_mx": "mx.liga_mx"}
MERCADOS = {"1_1": "1x2", "1_2": "ah", "1_3": "goles", "1_4": "corners", "1_5": "ah_1t", "1_6": "goles_1t",
            "1_7": "corners_1t", "1_8": "descanso"}
COLUMNAS_CUOTA = ["home_od", "draw_od", "away_od", "over_od", "under_od"]


def numero(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def lineas(texto) -> list[float]:
    """«9.5» → [9.5]; «9.5,10» → [9.5, 10.0] (línea de cuarto = dos medias apuestas)."""
    if texto is None or texto == "":
        return []
    try:
        return sorted(float(t) for t in str(texto).split(","))
    except ValueError:
        return []


def liquidar_total(valor, ls: list[float], direccion: str) -> str:
    """'gana' solo si ganan todas las partes, 'pierde' solo si pierden todas, el resto 'devuelve' (incluye medias)."""
    if not ls or pd.isna(valor):
        return ""
    if direccion == "mas":
        return "gana" if valor > max(ls) else "pierde" if valor < min(ls) else "devuelve"
    return "gana" if valor < min(ls) else "pierde" if valor > max(ls) else "devuelve"


def liquidar_handicap(dif_local, ls: list[float], lado: str) -> str:
    """`ls` es el hándicap del LOCAL; el visitante tiene el opuesto. dif_local = goles local − goles visita."""
    if not ls or pd.isna(dif_local):
        return ""
    d = dif_local if lado == "home" else -dif_local
    h = ls if lado == "home" else [-x for x in ls]
    return "gana" if all(d + x > 0 for x in h) else "pierde" if all(d + x < 0 for x in h) else "devuelve"


def p_total(pmf: np.ndarray, ls: list[float], direccion: str) -> float:
    """P(gana todas las partes) de una variable entera con distribución `pmf` (índice = valor)."""
    s = np.arange(len(pmf))
    if direccion == "mas":
        return float(pmf[s > max(ls)].sum())
    return float(pmf[s < min(ls)].sum())


def p_handicap(dif_pmf: np.ndarray, soporte: np.ndarray, ls: list[float], lado: str) -> float:
    """P(gana todas las partes) del hándicap; `dif_pmf` es la distribución de local − visita."""
    d = soporte if lado == "home" else -soporte
    h = ls if lado == "home" else [-x for x in ls]
    ok = np.ones(len(d), bool)
    for x in h:
        ok &= (d + x) > 0
    return float(dif_pmf[ok].sum())


def normalizar(nombre: str) -> str:
    n = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\b(fc|cf|ac|as|sc|cd|club|de|ud|sd|rc|afc|ssc|us|sv|vfl|vfb|tsg|fsv|1)\b", " ", n)
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", n).split())


def similitud(a: str, b: str) -> float:
    a, b = normalizar(a), normalizar(b)
    if not a or not b:
        return 0.0
    ta, tb = set(a.split()), set(b.split())
    base = SequenceMatcher(None, a, b).ratio()
    if a in b or b in a or (ta & tb):
        base = max(base, 0.75)
    return base


def leer_evento(ruta: Path) -> tuple[dict, list[dict]] | None:
    try:
        j = json.load(gzip.open(ruta))
    except (OSError, ValueError):
        return None
    ev = j.get("event") or {}
    if not ev.get("time"):
        return None
    st = ev.get("stats") or {}
    sc = ev.get("scores") or {}
    ft, ht = sc.get("2") or {}, sc.get("1") or {}
    cor = st.get("corner_f") or st.get("corners") or [None, None]
    cor1 = st.get("corner_h") or [None, None]
    ss = str(ev.get("ss") or "")
    gl = ss.split("-") if "-" in ss else [None, None]
    fila = {"bid": int(ev["id"]), "kickoff": int(ev["time"]), "estado": ev.get("time_status"),
            "home": (ev.get("home") or {}).get("name"), "away": (ev.get("away") or {}).get("name"),
            "gl_h": numero(gl[0]), "gl_a": numero(gl[1]),
            "ht_h": numero(ht.get("home")), "ht_a": numero(ht.get("away")),
            "cor_h": numero(cor[0]), "cor_a": numero(cor[1]),
            "cor1t_h": numero(cor1[0]), "cor1t_a": numero(cor1[1])}
    ticks = []
    for clave, serie in ((j.get("odds") or {}).get("odds") or {}).items():
        if clave not in MERCADOS:
            continue
        for t in serie or []:
            ticks.append({"bid": fila["bid"], "mercado": MERCADOS[clave], "t": numero(t.get("add_time")),
                          "minuto": numero(t.get("time_str")), "marcador": t.get("ss"), "corners_vivo": t.get("ss2"),
                          "linea": t.get("handicap"), **{c: numero(t.get(c)) for c in COLUMNAS_CUOTA}})
    return fila, ticks


def emparejar(eventos: pd.DataFrame, partidos: pd.DataFrame, ventana_h: float = 3.0) -> pd.DataFrame:
    """bid → match_id por liga, hora (±ventana), marcador final y parecido de nombres."""
    p = partidos.copy()
    p["t"] = pd.to_datetime(p["kickoff_utc"], utc=True).astype("int64") // 10 ** 9
    filas = []
    for liga, g in eventos.groupby("liga"):
        pl = p[p["league_id"] == LIGAS[liga]]
        tt = pl["t"].to_numpy()
        for e in g.itertuples(index=False):
            cand = pl[np.abs(tt - e.kickoff) <= ventana_h * 3600]
            if cand.empty:
                continue
            igual = cand[(cand["home_goals"] == e.gl_h) & (cand["away_goals"] == e.gl_a)]
            usar = igual if len(igual) else cand
            sim = np.array([(similitud(e.home, h) + similitud(e.away, a)) / 2
                            for h, a in zip(usar["home_name"], usar["away_name"])])
            k = int(sim.argmax())
            ok = sim[k] >= 0.45 or (len(igual) == 1 and abs(usar.iloc[0]["t"] - e.kickoff) <= 1800)
            if ok:
                filas.append({"bid": e.bid, "match_id": usar.iloc[k]["match_id"], "similitud": float(sim[k]),
                              "con_marcador": bool(len(igual))})
    return pd.DataFrame(filas)


def instantaneas(ticks: pd.DataFrame, kickoff: pd.Series, antes_s: float) -> pd.DataFrame:
    """Último tick PREPARTIDO de cada (partido, mercado) con al menos `antes_s` segundos de antelación."""
    t = ticks.merge(kickoff.rename("kickoff"), left_on="bid", right_index=True)
    t = t[t["minuto"].isna() & (t["t"] <= t["kickoff"] - antes_s)]
    return t.sort_values("t").groupby(["bid", "mercado"], as_index=False).tail(1)


def llegada_carrera(vivo: pd.DataFrame, x: int) -> str | None:
    """
    Quién llegó antes a `x` córners según la serie en vivo (`corners_vivo` local-visita con el minuto).
    'home'/'away', o None si ninguno llegó o los dos cruzaron entre dos lecturas (empate de lecturas).
    """
    v = vivo.dropna(subset=["minuto"]).copy()
    c = v["corners_vivo"].astype(str).str.split("-", expand=True)
    if c.shape[1] < 2:
        return None
    v["h"], v["a"] = pd.to_numeric(c[0], errors="coerce"), pd.to_numeric(c[1], errors="coerce")
    v = v.dropna(subset=["h", "a"]).sort_values(["t"])
    for h, a in zip(v["h"], v["a"]):
        if h >= x or a >= x:
            if h >= x and a >= x:
                return None
            return "home" if h >= x else "away"
    return None
