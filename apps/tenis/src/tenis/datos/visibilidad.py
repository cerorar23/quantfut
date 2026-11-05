"""Reimplementación POR CONJUNTO (pandas) de la puerta oficial `*_a_las` de `db/0004_lectura_pit.sql`.

Cada fila de evidencia recibe un instante `vis` con la semántica «visible en el corte c ⇔ c > vis»:
  - dato en vivo (recibo.retro = false): visible si recibido_en <= c  ⇒  vis = recibido_en − 1 µs (la base guarda µs);
  - dato retro con visible_desde: visible si c > visible_desde       ⇒  vis = visible_desde;
  - dato retro sin visible_desde: regla por semana con el `lunes_semana` de la edición VIGENTE en c
    (`lunes_por_partido_a_las`): visible si la edición vigente existe y c > lunes + 7 días (00:00 UTC). Como la edición
    vigente puede cambiar con c, se calcula el conjunto de cortes visibles como unión de intervalos; si no es un único
    intervalo hasta el infinito, la fila queda marcada `no_monotona` (no se exporta; se cuenta).
La selección entre versiones de una misma clave (DISTINCT ON) es: prioridad de la fuente, `recibido_en` más reciente,
id mayor; `vigente_en` la aplica en un corte concreto (la usan las pruebas de equivalencia).
"""
import numpy as np
import pandas as pd

UN_MICRO = pd.Timedelta(microseconds=1)
SIETE_DIAS = pd.Timedelta(days=7)
NUNCA = pd.NaT


def _utc(fecha: pd.Series) -> pd.Series:
    """Fecha (naive, 00:00) → instante UTC."""
    return pd.to_datetime(fecha).dt.tz_localize("UTC")


def vis_propia(df: pd.DataFrame, lunes: pd.Series | None = None) -> pd.Series:
    """Instante de visibilidad de filas que NO dependen de la edición (o con `lunes` ya resuelto por fila).

    `lunes` (fecha) se usa solo para filas retro sin visible_desde: vis = lunes + 7 días."""
    vis = pd.Series(NUNCA, index=df.index, dtype="datetime64[ns, UTC]")
    retro = df["retro"].fillna(False).astype(bool)
    vivo = ~retro
    vis[vivo] = df.loc[vivo, "recibido_en"] - UN_MICRO
    con_vd = retro & df["visible_desde"].notna()
    vis[con_vd] = df.loc[con_vd, "visible_desde"]
    sin_vd = retro & df["visible_desde"].isna()
    if lunes is not None and sin_vd.any():
        vis[sin_vd] = _utc(lunes[sin_vd]) + SIETE_DIAS
    return vis


def vis_edicion(ed: pd.DataFrame) -> pd.Series:
    """Visibilidad de la propia edición (`edicion_a_las`): regla por semana con SU lunes si no trae visible_desde."""
    return vis_propia(ed, ed["lunes_semana"])


def _union_intervalos(intervalos: list[tuple]) -> tuple[object, bool]:
    """Intervalos (desde_excl, hasta_incl) con hasta=None = infinito. Devuelve (desde, monótono): la unión es
    (desde, ∞) ⇒ (desde, True); vacía ⇒ (NaT, True); cualquier otra forma ⇒ (NaT, False)."""
    iv = sorted((a, b) for a, b in intervalos if b is None or a < b)
    if not iv:
        return NUNCA, True
    inicio, fin = iv[0]
    for a, b in iv[1:]:
        if fin is None:
            break
        if a > fin:
            return NUNCA, False
        fin = None if b is None else max(fin, b)
    return (inicio, True) if fin is None else (NUNCA, False)


def limite_por_grupo(ed: pd.DataFrame) -> pd.DataFrame:
    """Por (torneo_id, temporada): instante desde el que un dato retro SIN visible_desde de un partido de ese grupo es
    visible (`lim`), y si esa visibilidad es monótona. Reproduce `edicion_a_las` + `lunes_por_partido_a_las`."""
    e = ed.assign(vis=vis_edicion(ed))
    e = e[e["vis"].notna()]
    n = e.groupby(["torneo_id", "temporada"])["edicion_id"].transform("size")
    unico = e[n == 1]
    salida = [pd.DataFrame({
        "torneo_id": unico["torneo_id"].values, "temporada": unico["temporada"].values,
        "lim": np.maximum(unico["vis"].values, (_utc(unico["lunes_semana"]) + SIETE_DIAS).values),
        "monotono": True, "n_ediciones": 1})]
    filas = []
    for (t, temp), g in e[n > 1].groupby(["torneo_id", "temporada"]):
        g = g.sort_values("vis")
        instantes = list(dict.fromkeys(g["vis"]))
        intervalos = []
        for k, desde in enumerate(instantes):
            visibles = g[g["vis"] <= desde]
            mejor = visibles.sort_values(["prio", "recibido_en", "edicion_id"],
                                         ascending=[True, False, False]).iloc[0]
            hasta = instantes[k + 1] if k + 1 < len(instantes) else None
            intervalos.append((max(desde, pd.Timestamp(mejor["lunes_semana"]).tz_localize("UTC") + SIETE_DIAS), hasta))
        lim, mono = _union_intervalos(intervalos)
        filas.append({"torneo_id": t, "temporada": temp, "lim": lim, "monotono": mono, "n_ediciones": len(g)})
    if filas:
        salida.append(pd.DataFrame(filas))
    out = pd.concat(salida, ignore_index=True)
    out["lim"] = pd.to_datetime(out["lim"], utc=True)
    return out


def limite_por_partido(partido: pd.DataFrame, ed: pd.DataFrame) -> pd.DataFrame:
    """partido_id → (lim, monotono) del grupo (torneo, temporada) de SU edición. Sin edición visible nunca: lim NaT."""
    grupos = limite_por_grupo(ed)
    m = partido[["partido_id", "edicion_id"]].merge(ed[["edicion_id", "torneo_id", "temporada"]], on="edicion_id",
                                                     how="left")
    m = m.merge(grupos, on=["torneo_id", "temporada"], how="left")
    m["monotono"] = m["monotono"].fillna(True).astype(bool)
    return m[["partido_id", "lim", "monotono"]]


def vis_por_partido(df: pd.DataFrame, limites: pd.DataFrame) -> pd.DataFrame:
    """Añade `vis` y `no_monotona` a filas de partido/programa/resultado/estadística (clave partido_id)."""
    m = df.merge(limites, on="partido_id", how="left")
    vis = vis_propia(m)
    retro = m["retro"].fillna(False).astype(bool)
    sin_vd = retro & m["visible_desde"].isna()
    vis[sin_vd] = m.loc[sin_vd, "lim"]
    m["vis"] = vis
    m["no_monotona"] = sin_vd & ~m["monotono"].fillna(True).astype(bool)
    return m.drop(columns=["lim", "monotono"])


def vis_asercion(df: pd.DataFrame) -> pd.Series:
    """`jugador_asercion_a_las`: retro vale para cualquier corte (vis = −∞); en vivo, recibido_en <= corte."""
    vis = pd.Series(pd.Timestamp.min.tz_localize("UTC"), index=df.index, dtype="datetime64[ns, UTC]")
    vivo = ~df["retro"].fillna(False).astype(bool)
    vis[vivo] = df.loc[vivo, "recibido_en"] - UN_MICRO
    return vis


def vigente_en(df: pd.DataFrame, corte, claves: list[str], id_col: str) -> pd.DataFrame:
    """Filas vigentes en `corte` (DISTINCT ON claves: prioridad, recibido_en desc, id desc) entre las visibles."""
    v = df[df["vis"] < corte]
    v = v.sort_values(claves + ["prio", "recibido_en", id_col], ascending=[True] * len(claves) + [True, False, False])
    return v.drop_duplicates(claves, keep="first")
