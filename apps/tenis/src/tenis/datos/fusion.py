"""Fusión TML–SofaScore: el mismo partido real cargado por las dos fuentes (filas distintas, MISMOS ids de jugador).

Regla (escrita, en el manifiesto):
  1. Estricta: misma pareja canónica (jugador_1, jugador_2), misma ronda y el inicio real de SofaScore dentro de la
     ventana de la edición de TML [inicio L 00:00 UTC, fecha_fin + 1 día 00:00 UTC). Ronda: igualdad exacta, salvo
     «QL» de SofaScore (última ronda del clasificatorio), que equivale a la ronda Q más alta de esa edición de TML.
  2. Por edición enlazada: si TODAS las fusiones estrictas de una edición de TML van a una única edición de SofaScore y
     viceversa, las dos ediciones quedan enlazadas; las filas aún sin fusionar de ambas se emparejan por pareja y ronda
     sin ventana (corrige las ediciones de TML con `tourney_date` en la semana del clasificatorio: «desalineadas»).
  3. Pareja única en ediciones enlazadas: lo que quede, por pareja sin mirar la ronda, si la pareja aparece UNA sola vez
     en cada edición y no es RR (SofaScore etiqueta algunas rondas del clasificatorio como «Round of 16/32»).
  En los dos pasos una fila solo se fusiona si tiene UN candidato y su candidato la tiene a ella como único: cualquier
  ambigüedad se deja sin fusionar y se cuenta. La fusión no mira resultados (solo identidad, ronda y fechas).
"""
from collections import Counter

import pandas as pd

UN_DIA = pd.Timedelta(days=1)


def _clave_ronda_tml(tml: pd.DataFrame) -> pd.DataFrame:
    """Filas de TML (columna de edición `ed_tml`) con su(s) clave(s) de ronda: la propia y «QL» para la ronda Q más
    alta de su edición."""
    q = tml[tml["ronda"].str.fullmatch(r"Q[1-9]")]
    maxq = q.groupby("ed_tml")["ronda"].max().rename("maxq")
    t = tml.merge(maxq, on="ed_tml", how="left")
    base = t.assign(ronda_k=t["ronda"])
    ql = t[t["ronda"] == t["maxq"]].assign(ronda_k="QL")
    return pd.concat([base, ql], ignore_index=True).drop(columns=["maxq"])


def _unicos(pares: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Pares (tml, sofa) en los que cada lado tiene un único candidato. Devuelve (pares, ambiguos descartados)."""
    pares = pares.drop_duplicates(["pid_tml", "pid_sofa"])
    n_t = pares.groupby("pid_tml")["pid_sofa"].transform("size")
    n_s = pares.groupby("pid_sofa")["pid_tml"].transform("size")
    ok = (n_t == 1) & (n_s == 1)
    ambiguos = pares.loc[~ok, "pid_sofa"].nunique() + pares.loc[~ok, "pid_tml"].nunique()
    return pares[ok], int(ambiguos)


def fusionar(tml: pd.DataFrame, sofa: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """`tml`: partido_id, edicion_id, ronda, jugador_1, jugador_2, ventana_ini, ventana_fin (UTC).
    `sofa`: partido_id, edicion_id, ronda, jugador_1, jugador_2, inicio (UTC).
    Devuelve (pares con columnas pid_tml, pid_sofa, metodo) y recuentos."""
    cont: Counter = Counter()
    t = _clave_ronda_tml(tml.rename(columns={"partido_id": "pid_tml", "edicion_id": "ed_tml"}))
    s = sofa.rename(columns={"partido_id": "pid_sofa", "edicion_id": "ed_sofa"})
    cand = s.merge(t, left_on=["jugador_1", "jugador_2", "ronda"], right_on=["jugador_1", "jugador_2", "ronda_k"],
                   suffixes=("_s", "_t"))
    estricta = cand[(cand["inicio"] >= cand["ventana_ini"]) & (cand["inicio"] < cand["ventana_fin"])]
    p1, amb1 = _unicos(estricta[["pid_tml", "pid_sofa", "ed_tml", "ed_sofa"]])
    cont["fusion_estricta"] = len(p1)
    cont["ambiguos_estricta"] = amb1
    cont["candidatos_fuera_de_ventana"] = int(cand.loc[~cand.index.isin(estricta.index), "pid_sofa"].nunique())

    # Enlace de ediciones: biyectivo en las fusiones estrictas.
    enl = p1.groupby("ed_tml")["ed_sofa"].nunique()
    enl_s = p1.groupby("ed_sofa")["ed_tml"].nunique()
    pares_ed = p1[["ed_tml", "ed_sofa"]].drop_duplicates()
    pares_ed = pares_ed[pares_ed["ed_tml"].map(enl).eq(1) & pares_ed["ed_sofa"].map(enl_s).eq(1)]
    cont["ediciones_enlazadas"] = len(pares_ed)
    cont["ediciones_tml_sin_enlace_por_conflicto"] = int((enl > 1).sum())
    libres = cand[~cand["pid_tml"].isin(p1["pid_tml"]) & ~cand["pid_sofa"].isin(p1["pid_sofa"])]
    enlazada = libres.merge(pares_ed, on=["ed_tml", "ed_sofa"])
    p2, amb2 = _unicos(enlazada[["pid_tml", "pid_sofa", "ed_tml", "ed_sofa"]])
    cont["fusion_edicion_enlazada"] = len(p2)
    cont["ambiguos_edicion_enlazada"] = amb2

    # 3. Pareja única en ediciones enlazadas, sin mirar la ronda: SofaScore etiqueta a veces rondas del clasificatorio
    # como «Round of 16/32». Dos jugadores no se cruzan dos veces en un mismo cuadro eliminatorio; si la pareja aparece
    # más de una vez en la edición de cualquiera de las dos fuentes (perdedor afortunado, RR), no se fusiona.
    usados_t = set(p1["pid_tml"]) | set(p2["pid_tml"])
    usados_s = set(p1["pid_sofa"]) | set(p2["pid_sofa"])
    tb = tml.rename(columns={"partido_id": "pid_tml", "edicion_id": "ed_tml"})
    tb = tb[tb.groupby(["ed_tml", "jugador_1", "jugador_2"])["pid_tml"].transform("size").eq(1)
            & tb["ronda"].ne("RR") & ~tb["pid_tml"].isin(usados_t)]
    sb = s[s.groupby(["ed_sofa", "jugador_1", "jugador_2"])["pid_sofa"].transform("size").eq(1)
           & s["ronda"].ne("RR") & ~s["pid_sofa"].isin(usados_s)]
    c3 = sb.merge(pares_ed, on="ed_sofa").merge(tb, on=["ed_tml", "jugador_1", "jugador_2"], suffixes=("_s", "_t"))
    p3, amb3 = _unicos(c3[["pid_tml", "pid_sofa", "ed_tml", "ed_sofa"]])
    cont["fusion_pareja_en_edicion_enlazada"] = len(p3)
    cont["ambiguos_pareja_en_edicion_enlazada"] = amb3
    pares = pd.concat([p1.assign(metodo="estricta"), p2.assign(metodo="edicion_enlazada"),
                       p3.assign(metodo="pareja_en_edicion_enlazada")], ignore_index=True)
    return pares[["pid_tml", "pid_sofa", "metodo"]].sort_values(["pid_tml", "pid_sofa"]).reset_index(drop=True), dict(cont)


def posibles_duplicados(tml_solo: pd.DataFrame, sofa_solo: pd.DataFrame, dias: int = 7) -> int:
    """Filas de SofaScore sin fusionar con una fila de TML sin fusionar de la MISMA pareja (cualquier ronda) cuyo inicio
    cae en la ventana de esa edición de TML ampliada `dias` por cada lado: posibles partidos reales duplicados que la
    regla no fusionó (cuenta informativa: el filtro de rating los vería dos veces)."""
    c = sofa_solo.merge(tml_solo, on=["jugador_1", "jugador_2"], suffixes=("_s", "_t"))
    margen = pd.Timedelta(days=dias)
    cerca = (c["inicio"] >= c["ventana_ini"] - margen) & (c["inicio"] < c["ventana_fin"] + margen)
    return int(c.loc[cerca, "partido_id_s"].nunique())
