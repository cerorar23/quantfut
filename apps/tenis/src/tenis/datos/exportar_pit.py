"""Exportación PUNTO EN EL TIEMPO del histórico de tenis para entrenar y evaluar en walk-forward (plan §A.4, §C.5, K.2 S3).

Salida (directorio por parámetro):
  partidos.parquet            una fila por partido del mundo real (TML y SofaScore fusionados), con su corte y entradas
                              «as of»; las etiquetas llevan prefijo `y_` (lista `columnas_etiqueta` del manifiesto)
  eventos_resultado.parquet   resultados como eventos ordenados por `visible_resultado_utc` (orden de consumo del filtro)
  ranking_asof.parquet        ranking y puntos de cada lado con la regla estricta de la puerta oficial
  estadisticas_saque.parquet  puntos de saque y ganados por lado (solo completados) con su `visible_desde`
  visibilidad_filas.parquet   auditoría: instante de visibilidad de cada fila fuente (lo que se compara con la puerta)
  calidad.json, manifiesto.json

Semántica de todos los instantes: un dato con instante v es visible en el corte c si y solo si c > v (como la base).
"""
import hashlib
import io
import json
import platform
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from . import reglas
from .fusion import fusionar, posibles_duplicados
from .visibilidad import (UN_MICRO, limite_por_partido, vis_asercion, vis_edicion, vis_por_partido, vis_propia,
                          vigente_en)

VERSION = "tenis-export-pit-1.0.0"
SALIDA_POR_OMISION = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\export_pit")
ESTADOS_JUGADOS = ("completado", "retirada")
MOTIVOS_DUROS = ("sin_hora_ni_calendario", "pareja_no_visible_en_su_corte", "resultado_visible_en_su_corte",
                 "visibilidad_no_monotona", "multiversion", "fuente_no_soportada")


# ------------------------------------------------------------------------------------------------ ayudas
def _sets_json(texto) -> str | None:
    if texto is None or texto != texto:
        return None
    return json.dumps(json.loads(texto), separators=(",", ":"))


def _juegos(texto) -> tuple:
    if texto is None or texto != texto:
        return (pd.NA, pd.NA)
    sets = json.loads(texto)
    return (sum(s[0] for s in sets), sum(s[1] for s in sets))


def _fecha_local(instantes: pd.Series, husos: pd.Series) -> pd.Series:
    """Fecha local del instante en el huso IANA de la sede; sin sede, UTC (documentado)."""
    out = instantes.dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize().copy()
    con_huso = husos.notna() & instantes.notna()
    for huso in husos[con_huso].unique():
        m = con_huso & (husos == huso)
        out[m] = instantes[m].dt.tz_convert(ZoneInfo(huso)).dt.tz_localize(None).dt.normalize()
    return out


def _clave(pt, ps) -> str:
    return ("" if pd.isna(pt) else f"T{int(pt)}") + ("" if pd.isna(ps) else f"S{int(ps)}")


# ------------------------------------------------------------------------------------------------ construcción
def _ediciones(t: dict) -> pd.DataFrame:
    ed = t["edicion"].merge(t["torneo"].drop(columns=["fuente"]), on="torneo_id", how="left")
    ed = ed.merge(t["sede"], on="sede_id", how="left") if len(t["sede"]) else ed.assign(huso_iana=pd.NA)
    ed["vis_ed"] = vis_edicion(ed)
    ed["n_grupo"] = ed.groupby(["torneo_id", "temporada"])["edicion_id"].transform("size")
    return ed


def _edicion_en_corte(filas: pd.DataFrame, ed: pd.DataFrame, col_ed: str, col_corte: str) -> pd.DataFrame:
    """Para cada fila (edicion_id de su partido, corte): la edición VIGENTE en el corte de su grupo (torneo,
    temporada), o nada si ninguna es visible. Devuelve edicion_id vigente (o <NA>) alineado con `filas`."""
    base = filas[[col_ed, col_corte]].merge(ed[["edicion_id", "torneo_id", "temporada", "n_grupo", "vis_ed"]],
                                            left_on=col_ed, right_on="edicion_id", how="left")
    base.index = filas.index
    out = pd.Series(pd.NA, index=filas.index, dtype="Int64")
    unico = base["n_grupo"].eq(1) & (base[col_corte] > base["vis_ed"])
    out[unico] = base.loc[unico, "edicion_id"]
    multi = base["n_grupo"].gt(1) & base[col_corte].notna()
    if multi.any():
        e = ed.rename(columns={"vis_ed": "vis"})
        for i, fila in base[multi].iterrows():
            g = e[(e["torneo_id"] == fila["torneo_id"]) & (e["temporada"] == fila["temporada"])]
            v = vigente_en(g, fila[col_corte], ["torneo_id", "temporada"], "edicion_id")
            if len(v):
                out[i] = v["edicion_id"].iloc[0]
    return out


def _ranking_asof(q: pd.DataFrame, rk: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Ranking vigente por consulta (circuito, jugador_id, corte, fecha_rk), con la regla de `ranking_a_las(corte,
    fecha)`: por fecha de publicación, la mejor fila VISIBLE (c > vis); se toma la publicación más reciente con
    fecha_publicacion <= fecha_rk que tenga alguna fila visible. Devuelve (filas elegidas por consulta, consultas por
    el camino lento)."""
    cols = ["ranking_id", "fecha_publicacion", "posicion", "puntos", "origen", "fuente", "vis"]
    vacio = pd.DataFrame(index=q.index, columns=cols)
    if q.empty or rk.empty:
        return vacio, 0
    g = rk.groupby(["circuito", "jugador_id", "fecha_publicacion"]).agg(gvis=("vis", "min"), n=("ranking_id", "size"),
                                                                       primero=("ranking_id", "first")).reset_index()
    qq = q.reset_index().rename(columns={"index": "_q"})
    qq = qq[qq["corte"].notna() & qq["fecha_rk"].notna() & qq["jugador_id"].notna()]
    qq["jugador_id"] = qq["jugador_id"].astype("int64")
    g["jugador_id"] = g["jugador_id"].astype("int64")
    qq["fecha_rk"] = pd.to_datetime(qq["fecha_rk"]).dt.tz_localize(None).astype("datetime64[ns]")
    g["fecha_publicacion"] = pd.to_datetime(g["fecha_publicacion"]).dt.tz_localize(None).astype("datetime64[ns]")
    qq = qq.sort_values("fecha_rk")
    g = g.sort_values("fecha_publicacion")
    m = pd.merge_asof(qq, g, left_on="fecha_rk", right_on="fecha_publicacion", by=["circuito", "jugador_id"],
                      direction="backward")
    rapido = m["fecha_publicacion"].notna() & (m["corte"] > m["gvis"]) & m["n"].eq(1)
    lento = m["fecha_publicacion"].notna() & ~rapido
    por_id = rk.set_index("ranking_id")
    out = vacio.copy()
    sel = m.loc[rapido, ["_q", "primero"]]
    out.loc[sel["_q"].values, cols] = por_id.loc[sel["primero"].values].reset_index()[cols].values
    if lento.any():
        grupos = {k: v.sort_values(["fecha_publicacion", "prio", "recibido_en", "ranking_id"],
                                   ascending=[False, True, False, False])
                  for k, v in rk[rk.set_index(["circuito", "jugador_id"]).index.isin(
                      list(zip(m.loc[lento, "circuito"], m.loc[lento, "jugador_id"])))].groupby(["circuito", "jugador_id"])}
        for _, f in m[lento].iterrows():
            v = grupos[(f["circuito"], f["jugador_id"])]
            v = v[(v["fecha_publicacion"] <= f["fecha_rk"]) & (f["corte"] > v["vis"])]
            if len(v):
                out.loc[f["_q"], cols] = v.iloc[0][cols].values
    return out, int(lento.sum())


def _nacimiento(nac: pd.DataFrame) -> pd.DataFrame:
    """Fecha de nacimiento por jugador (aserción vigente; las retro valen para cualquier corte). Si hubiera aserciones
    en vivo se aplicaría su `recibido_en`: aquí se exige que todas sean retro y, si no, se cuentan y no se usan."""
    if nac.empty:
        return pd.DataFrame(columns=["jugador_id", "nacimiento"])
    n = nac.assign(vis=vis_asercion(nac))
    retro = n[n["retro"].fillna(False).astype(bool)]
    sel = retro.sort_values(["jugador_id", "prio", "recibido_en", "asercion_id"], ascending=[True, True, False, False])
    sel = sel.drop_duplicates("jugador_id")
    return pd.DataFrame({"jugador_id": sel["jugador_id"].values,
                         "nacimiento": pd.to_datetime(sel["valor"], format="%Y-%m-%d", errors="coerce").values})


def construir(t: dict, desde: date | None = None) -> dict:
    """Construye todas las tablas de la exportación a partir de las tablas leídas (`lectura.leer_todo`)."""
    cal: Counter = Counter()
    ed = _ediciones(t)
    lim = limite_por_partido(t["partido"], t["edicion"])
    P = vis_por_partido(t["partido"], lim)
    G = vis_por_partido(t["programa"], lim)
    R = vis_por_partido(t["resultado"], lim)
    E = vis_por_partido(t["estadistica"], lim)

    multi = set(R.loc[R.duplicated("partido_id", keep=False), "partido_id"])
    multi |= set(E.loc[E.duplicated(["partido_id", "lado"], keep=False), "partido_id"])
    cal["multiversion_resultado_o_estadistica"] = len(multi)
    no_mono = set(P.loc[P["no_monotona"], "partido_id"]) | set(R.loc[R["no_monotona"], "partido_id"])
    cal["visibilidad_no_monotona"] = len(no_mono)

    # ---- filas por fuente
    soportadas = {"tml", "sofascore"}
    otras = P[~P["fuente"].isin(soportadas)]
    cal["partidos_fuente_no_soportada"] = len(otras)
    ed_cols = ed[["edicion_id", "visible_desde", "fecha_fin", "lunes_semana"]].rename(
        columns={"visible_desde": "ed_vd"})
    Pt = P[P["fuente"] == "tml"].merge(ed_cols, on="edicion_id", how="left")
    Pt["ventana_ini"] = Pt["ed_vd"].fillna(
        pd.to_datetime(Pt["lunes_semana"]).dt.tz_localize("UTC") - pd.Timedelta(days=7))
    fin = Pt["fecha_fin"].fillna(Pt["lunes_semana"] + pd.Timedelta(days=6))
    Pt["ventana_fin"] = pd.to_datetime(fin).dt.tz_localize("UTC") + pd.Timedelta(days=1)
    Ps = P[P["fuente"] == "sofascore"].copy()
    prog_s = G[G["fuente"] == "sofascore"].groupby("partido_id").agg(
        inicio=("inicio_programado_utc", "min"), n_prog=("programa_id", "size")).reset_index()
    cal["multiversion_programa"] = int((prog_s["n_prog"] > 1).sum())
    Ps = Ps.merge(prog_s, on="partido_id", how="left")
    cal["sofascore_sin_hora"] = int(Ps["inicio"].isna().sum())

    pares, cont_f = fusionar(
        Pt[["partido_id", "edicion_id", "ronda", "jugador_1", "jugador_2", "ventana_ini", "ventana_fin"]],
        Ps.loc[Ps["inicio"].notna(), ["partido_id", "edicion_id", "ronda", "jugador_1", "jugador_2", "inicio"]])
    cal.update({f"fusion:{k}": v for k, v in cont_f.items()})

    K = pd.concat([
        pares,
        pd.DataFrame({"pid_tml": Pt.loc[~Pt["partido_id"].isin(pares["pid_tml"]), "partido_id"].values}),
        pd.DataFrame({"pid_sofa": Ps.loc[~Ps["partido_id"].isin(pares["pid_sofa"]), "partido_id"].values}),
    ], ignore_index=True)
    K["pid_tml"] = K["pid_tml"].astype("Int64")
    K["pid_sofa"] = K["pid_sofa"].astype("Int64")
    cal["posibles_duplicados_no_fusionados"] = posibles_duplicados(
        Pt[~Pt["partido_id"].isin(pares["pid_tml"])],
        Ps[Ps["inicio"].notna() & ~Ps["partido_id"].isin(pares["pid_sofa"])])

    cols_p = ["partido_id", "edicion_id", "ronda", "jugador_1", "jugador_2", "mejor_de", "entrada_1", "entrada_2", "vis"]
    K = K.merge(Pt[cols_p + ["ventana_ini"]].add_suffix("_t"), left_on="pid_tml", right_on="partido_id_t", how="left")
    K = K.merge(Ps[cols_p + ["inicio"]].add_suffix("_s"), left_on="pid_sofa", right_on="partido_id_s", how="left")
    K["partido_key"] = [_clave(a, b) for a, b in zip(K["pid_tml"], K["pid_sofa"])]
    K["jugador_1"] = K["jugador_1_s"].fillna(K["jugador_1_t"]).astype("Int64")
    K["jugador_2"] = K["jugador_2_s"].fillna(K["jugador_2_t"]).astype("Int64")
    con_hora = K["pid_sofa"].notna() & K["inicio_s"].notna()
    K["fuente_tiempo"] = np.where(con_hora, "sofascore", "tml")
    K["inicio_utc"] = K["inicio_s"].where(con_hora)
    K["corte_utc"] = (K["inicio_s"] - reglas.MARGEN_CORTE).where(con_hora, K["vis_t"] + reglas.PASO_RETRO)
    K["pid_tiempo"] = K["pid_sofa"].where(con_hora, K["pid_tml"]).astype("Int64")

    # ---- resultado de la fuente del tiempo (evento) y etiquetas
    Rk = R.drop_duplicates("partido_id")
    rcols = ["resultado_id", "estado", "ganador", "retira", "sets", "sets_completos", "duracion_min", "fuente", "vis"]
    K = K.merge(Rk[["partido_id"] + rcols].rename(columns={"partido_id": "pid_tiempo"}).add_prefix("r_")
                .rename(columns={"r_pid_tiempo": "pid_tiempo"}), on="pid_tiempo", how="left")
    # conflicto de ganador entre fuentes en los fusionados (control de calidad)
    otro = Rk[["partido_id", "ganador", "estado"]]
    chk = K[K["pid_tml"].notna() & K["pid_sofa"].notna()][["pid_tml", "pid_sofa"]]
    chk = chk.merge(otro.add_suffix("_t"), left_on="pid_tml", right_on="partido_id_t").merge(
        otro.add_suffix("_s"), left_on="pid_sofa", right_on="partido_id_s")
    cal["fusion:conflicto_ganador"] = int((chk["ganador_t"].notna() & chk["ganador_s"].notna()
                                           & (chk["ganador_t"] != chk["ganador_s"])).sum())
    cal["fusion:conflicto_estado"] = int((chk["estado_t"] != chk["estado_s"]).sum())

    # ---- motivos duros
    motivo = pd.Series(pd.NA, index=K.index, dtype="string")

    def marcar(mask, texto):
        nonlocal motivo
        motivo = motivo.where(~(mask & motivo.isna()), texto)

    marcar(K["corte_utc"].isna(), "sin_hora_ni_calendario")
    vis_par_tiempo = K["vis_s"].where(con_hora, K["vis_t"])
    marcar(~(K["corte_utc"] > vis_par_tiempo), "pareja_no_visible_en_su_corte")
    marcar(K["r_vis"].notna() & (K["r_vis"] < K["corte_utc"]), "resultado_visible_en_su_corte")
    marcar(K["pid_tml"].isin(no_mono) | K["pid_sofa"].isin(no_mono), "visibilidad_no_monotona")
    marcar(K["pid_tml"].isin(multi) | K["pid_sofa"].isin(multi), "multiversion")

    # ---- atributos «as of»: solo de filas fuente visibles en el corte (prioridad de calendario: SofaScore > TML)
    vis_s_ok = K["corte_utc"] > K["vis_s"]
    vis_t_ok = K["corte_utc"] > K["vis_t"]
    for c in ("mejor_de", "entrada_1", "entrada_2"):
        K[c] = K[f"{c}_s"].where(vis_s_ok).combine_first(K[f"{c}_t"].where(vis_t_ok))
    # La ronda es identidad del partido (como el torneo): la de TML si está fusionado (numeración canónica de las
    # previas; SofaScore etiqueta algunas previas como R16/R32), si no la de su fuente.
    K["ronda"] = K["ronda_t"].where(K["pid_tml"].notna(), K["ronda_s"])
    K["ed_s"] = _edicion_en_corte(K, ed, "edicion_id_s", "corte_utc").where(vis_s_ok)
    K["ed_t"] = _edicion_en_corte(K, ed, "edicion_id_t", "corte_utc").where(vis_t_ok)
    K["ed_attr"] = K["ed_s"].combine_first(K["ed_t"]).astype("Int64")
    ecols = ["edicion_id", "torneo_id", "temporada", "circuito", "nombre", "categoria", "superficie", "indoor",
             "por_equipos", "huso_iana"]
    K = K.merge(ed[ecols].add_prefix("e_"), left_on="ed_attr", right_on="e_edicion_id", how="left")
    # identidad del torneo (no es dato con visible_desde): de la edición de la fuente del tiempo
    K["ed_ident"] = K["edicion_id_s"].where(con_hora, K["edicion_id_t"]).astype("Int64")
    K = K.merge(ed[["edicion_id", "torneo_id", "temporada", "circuito", "nombre", "categoria", "por_equipos",
                    "huso_iana"]].add_prefix("i_"), left_on="ed_ident", right_on="i_edicion_id", how="left")
    K["ronda_ident"] = K["ronda"]

    sup = [reglas.superficie_modelo(None if pd.isna(s) else s, None if pd.isna(i) else bool(i))
           for s, i in zip(K["e_superficie"].astype(object), K["e_indoor"].astype(object))]
    K["superficie"] = [s[0] for s in sup]
    K["indoor"] = pd.array([s[1] for s in sup], dtype="boolean")
    K["superficie_motivo"] = [s[2] for s in sup]
    K.loc[K["ed_attr"].isna(), "superficie_motivo"] = "edicion_no_visible_en_corte"
    fmt = [reglas.formato_decisivo(c if isinstance(c, str) else None, nm if isinstance(nm, str) else None,
                                   int(tp) if pd.notna(tp) else 0, r if isinstance(r, str) else "")
           for c, nm, tp, r in zip(K["i_categoria"], K["i_nombre"], K["i_temporada"], K["ronda_ident"])]
    K["formato_decisivo"] = [f[0] for f in fmt]
    K["formato_regla"] = [f[1] for f in fmt]

    # ---- fecha del partido (para ranking y edad): con hora, fecha local de la sede (sin sede, UTC); sin hora,
    # el primer día de la edición de TML (L): nunca después del partido real, así no entra un ranking publicado
    # durante el torneo (que ya incluiría sus puntos).
    huso = K["i_huso_iana"]   # el huso de la sede es identidad del lugar (no revela nada del partido)
    fecha_hora = _fecha_local(K["inicio_utc"], huso.astype(object).where(huso.notna(), None))
    fecha_tml = K["ventana_ini_t"].dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    K["fecha_partido"] = fecha_hora.where(con_hora, fecha_tml)
    K["fecha_partido_regla"] = np.where(con_hora, np.where(huso.notna(), "local_sede", "utc_sin_sede"),
                                        "inicio_edicion_tml")

    # ---- contextos (§F)
    K = K.merge(_contextos(K, ed), on="partido_key", how="left")
    cat_nom = list(zip(K["i_categoria"].astype(object).where(K["i_categoria"].notna(), None),
                       K["i_nombre"].astype(object).where(K["i_nombre"].notna(), None)))
    K["por_equipos"] = K["i_por_equipos"].fillna(False).astype(bool) | pd.Series(
        [reglas.es_equipos(c, n) for c, n in cat_nom], index=K.index)
    K["jjoo"] = pd.Series([reglas.es_jjoo(c, n) for c, n in cat_nom], index=K.index)

    # ---- edades
    nac = _nacimiento(t["nacimiento"])
    for lado in (1, 2):
        K = K.merge(nac.rename(columns={"jugador_id": f"jugador_{lado}", "nacimiento": f"nac_{lado}"}),
                    on=f"jugador_{lado}", how="left")
        K[f"edad_{lado}"] = ((K["fecha_partido"] - K[f"nac_{lado}"]).dt.days / 365.25).round(3)

    # ---- ranking «as of»
    rk = t["ranking"].assign(vis=lambda d: vis_propia(d, d["fecha_publicacion"]))
    q = pd.concat([pd.DataFrame({"partido_key": K["partido_key"], "lado": lado, "circuito": K["i_circuito"],
                                 "jugador_id": K[f"jugador_{lado}"], "corte": K["corte_utc"],
                                 "fecha_rk": K["fecha_partido"]}) for lado in (1, 2)], ignore_index=True)
    elegido, lentas = _ranking_asof(q, rk)
    cal["ranking:consultas_camino_lento"] = lentas
    rasof = pd.concat([q[["partido_key", "lado", "jugador_id", "fecha_rk", "corte"]], elegido], axis=1)
    rasof = rasof.rename(columns={"fecha_rk": "fecha_partido", "corte": "corte_utc", "vis": "visible_desde"})
    for lado in (1, 2):
        x = rasof[rasof["lado"] == lado].set_index("partido_key")
        K[f"rank_{lado}"] = K["partido_key"].map(x["posicion"]).astype("Int64")
        K[f"puntos_{lado}"] = K["partido_key"].map(x["puntos"]).astype("Int64")
        K[f"rank_origen_{lado}"] = K["partido_key"].map(x["origen"]).astype("string")
        K[f"rank_fecha_{lado}"] = pd.to_datetime(K["partido_key"].map(x["fecha_publicacion"]))

    # ---- eventos (resultado de la fuente del tiempo)
    ev = K[K["r_resultado_id"].notna() & ~motivo.isin(["visibilidad_no_monotona", "multiversion"])].copy()
    juegos = [_juegos(s) for s in ev["r_sets"]]
    ev["juegos_1"] = pd.array([j[0] for j in juegos], dtype="Int64")
    ev["juegos_2"] = pd.array([j[1] for j in juegos], dtype="Int64")
    ev = ev[ev["r_vis"].notna()]

    # ---- historia previa (n_prev, plan §D.6) con TODOS los eventos jugados visibles antes del corte
    jug = ev[ev["r_estado"].isin(ESTADOS_JUGADOS)]
    largo = pd.concat([pd.DataFrame({"jugador_id": jug[f"jugador_{l}"].astype("int64"), "t": jug["r_vis"]})
                       for l in (1, 2)], ignore_index=True)
    largo["t"] = pd.to_datetime(largo["t"], utc=True).astype("datetime64[ns, UTC]")
    largo = largo.sort_values(["t", "jugador_id"], kind="mergesort")
    largo["n"] = largo.groupby("jugador_id").cumcount() + 1
    for lado in (1, 2):
        qq = K[["partido_key", f"jugador_{lado}", "corte_utc"]].dropna().rename(
            columns={f"jugador_{lado}": "jugador_id"})
        qq["jugador_id"] = qq["jugador_id"].astype("int64")
        qq["corte_utc"] = pd.to_datetime(qq["corte_utc"], utc=True).astype("datetime64[ns, UTC]")
        qq = qq.sort_values("corte_utc")
        mm = pd.merge_asof(qq, largo, left_on="corte_utc", right_on="t", by="jugador_id", direction="backward",
                           allow_exact_matches=False)
        K[f"n_prev_{lado}"] = K["partido_key"].map(mm.set_index("partido_key")["n"].fillna(0)).astype("Int64")

    # ---- marcas blandas (no descartan)
    marcas = []
    for i in range(len(K)):
        m = []
        if isinstance(K["superficie_motivo"].iat[i], str):
            m.append(K["superficie_motivo"].iat[i])
        if K["formato_decisivo"].iat[i] == "desconocido":
            m.append("formato_desconocido")
        for lado in (1, 2):
            n = K[f"n_prev_{lado}"].iat[i]
            if pd.notna(n) and n < reglas.HISTORIA_CORTA:
                m.append(f"historia_corta_{lado}")
            if pd.isna(K[f"rank_{lado}"].iat[i]):
                m.append(f"sin_ranking_{lado}")
        marcas.append(";".join(m) if m else None)
    K["marcas"] = pd.array(marcas, dtype="string")
    K["excluir_motivo"] = motivo

    return _salidas(K, ev, E, rasof, P, G, R, desde, cal, t)


def _contextos(K: pd.DataFrame, ed: pd.DataFrame) -> pd.DataFrame:
    """semana_previa_gs por partido: inicio de su edición (TML: L; SofaScore: primer partido) entre 3 y 9 días antes
    del inicio del cuadro principal de un GS del mismo circuito (SofaScore: primer partido de cuadro; si no, L de TML)."""
    b = K[["partido_key", "ed_ident", "fuente_tiempo", "inicio_utc", "ventana_ini_t", "ronda_ident", "i_circuito",
           "i_categoria", "i_nombre", "i_temporada"]].copy()
    b["dia"] = b["inicio_utc"].where(b["fuente_tiempo"] == "sofascore", b["ventana_ini_t"])
    b["dia"] = b["dia"].dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    inicio_ed = b.groupby("ed_ident")["dia"].min()
    cuadro = b[~b["ronda_ident"].fillna("").str.startswith("Q")]
    gs = cuadro[cuadro["i_categoria"].eq("GS") | cuadro["i_categoria"].isna()].copy()
    gs["gs"] = gs["i_nombre"].map(lambda n: reglas.grand_slam(n) if isinstance(n, str) else None)
    gs = gs[gs["gs"].notna()]
    b["gs_propio"] = b["i_nombre"].map(lambda n: reglas.grand_slam(n) if isinstance(n, str) else None).notna()
    ini_gs = gs.groupby(["i_circuito", "i_temporada", "gs", "fuente_tiempo"])["dia"].min().reset_index()
    ini_gs["pref"] = ini_gs["fuente_tiempo"].map({"sofascore": 0, "tml": 1})
    ini_gs = ini_gs.sort_values(["i_circuito", "i_temporada", "gs", "pref"]).drop_duplicates(
        ["i_circuito", "i_temporada", "gs"])
    starts = {c: np.sort(g["dia"].values) for c, g in ini_gs.groupby("i_circuito")}
    b["inicio_ed"] = b["ed_ident"].map(inicio_ed)
    a, z = reglas.PREVIA_GS_DIAS
    previa = []
    for circ, cat, nom, gs_propio, d in zip(b["i_circuito"], b["i_categoria"], b["i_nombre"], b["gs_propio"],
                                            b["inicio_ed"]):
        cat = cat if isinstance(cat, str) else None
        nom = nom if isinstance(nom, str) else None
        if pd.isna(d):
            previa.append(None)
            continue
        if (cat in reglas.CATEGORIAS_SIN_PREVIA or gs_propio or reglas.es_jjoo(cat, nom)
                or reglas.es_equipos(cat, nom) or circ not in starts):
            previa.append(False)
            continue
        dif = (starts[circ] - np.datetime64(d)) / np.timedelta64(1, "D")
        previa.append(bool(((dif >= a) & (dif <= z)).any()))
    return pd.DataFrame({"partido_key": b["partido_key"], "semana_previa_gs": pd.array(previa, dtype="boolean")})


# ------------------------------------------------------------------------------------------------ salidas
COLUMNAS_ETIQUETA = ["visible_resultado_utc", "y_estado", "y_ganador", "y_retira", "y_sets", "y_sets_completos",
                     "y_juegos_1", "y_juegos_2", "y_duracion_min", "y_duracion_origen", "y_fuente_resultado",
                     "y_resultado_id"]


def _salidas(K, ev, E, rasof, P, G, R, desde, cal, t) -> dict:
    K = K.copy()
    K["temporada"] = K["i_temporada"].astype("Int64")
    if desde is not None:
        dentro = K["fecha_partido"] >= pd.Timestamp(desde)
        cal["fuera_de_rango_desde"] = int((~dentro).sum())
        K = K[dentro]
    claves = set(K["partido_key"])
    juegos = [_juegos(s) for s in K["r_sets"]]
    part = pd.DataFrame({
        "partido_key": K["partido_key"].astype("string"),
        "partido_id_tml": K["pid_tml"].astype("Int64"), "partido_id_sofascore": K["pid_sofa"].astype("Int64"),
        "fusion_metodo": K["metodo"].astype("string"),
        "circuito": K["i_circuito"].astype("string"), "temporada": K["temporada"],
        "torneo_id": K["i_torneo_id"].astype("Int64"), "torneo_nombre": K["i_nombre"].astype("string"),
        "categoria": K["i_categoria"].astype("string"),
        "superficie": K["superficie"].astype("string"), "indoor": K["indoor"].astype("boolean"),
        "superficie_base": K["e_superficie"].astype("string"),
        "mejor_de": K["mejor_de"].astype("Int64"),
        "formato_decisivo": K["formato_decisivo"].astype("string"), "formato_regla": K["formato_regla"].astype("string"),
        "ronda": K["ronda"].astype("string"),
        "entrada_1": K["entrada_1"].astype("string"), "entrada_2": K["entrada_2"].astype("string"),
        "semana_previa_gs": K["semana_previa_gs"].astype("boolean"),
        "por_equipos": K["por_equipos"].astype("boolean"), "jjoo": K["jjoo"].astype("boolean"),
        "jugador_1": K["jugador_1"].astype("Int64"), "jugador_2": K["jugador_2"].astype("Int64"),
        "edad_1": K["edad_1"].astype("Float64"), "edad_2": K["edad_2"].astype("Float64"),
        "rank_1": K["rank_1"], "puntos_1": K["puntos_1"], "rank_origen_1": K["rank_origen_1"],
        "rank_fecha_1": K["rank_fecha_1"],
        "rank_2": K["rank_2"], "puntos_2": K["puntos_2"], "rank_origen_2": K["rank_origen_2"],
        "rank_fecha_2": K["rank_fecha_2"],
        "n_prev_1": K["n_prev_1"], "n_prev_2": K["n_prev_2"],
        "fecha_partido": K["fecha_partido"], "fecha_partido_regla": K["fecha_partido_regla"].astype("string"),
        "inicio_utc": K["inicio_utc"], "corte_utc": K["corte_utc"],
        "fuente_tiempo": K["fuente_tiempo"].astype("string"),
        "excluir_motivo": K["excluir_motivo"].astype("string"), "marcas": K["marcas"].astype("string"),
        # etiquetas (resultado del propio partido): NUNCA entradas
        "visible_resultado_utc": K["r_vis"],
        "y_estado": K["r_estado"].astype("string"), "y_ganador": K["r_ganador"].astype("Int64"),
        "y_retira": K["r_retira"].astype("Int64"),
        "y_sets": pd.array([_sets_json(s) for s in K["r_sets"]], dtype="string"),
        "y_sets_completos": K["r_sets_completos"].astype("Int64"),
        "y_juegos_1": pd.array([j[0] for j in juegos], dtype="Int64"),
        "y_juegos_2": pd.array([j[1] for j in juegos], dtype="Int64"),
        "y_duracion_min": K["r_duracion_min"].astype("Int64"),
        "y_duracion_origen": K["r_fuente"].where(K["r_duracion_min"].notna()).astype("string"),
        "y_fuente_resultado": K["r_fuente"].astype("string"),
        "y_resultado_id": K["r_resultado_id"].astype("Int64"),
    }).sort_values("partido_key").reset_index(drop=True)

    ev = ev[ev["partido_key"].isin(claves)]
    ev = ev.merge(part[["partido_key", "superficie", "indoor", "formato_decisivo", "temporada", "circuito"]],
                  on="partido_key", how="left", suffixes=("_k", ""))
    dur = ev["r_duracion_min"].astype("Int64")
    eventos = pd.DataFrame({
        "partido_key": ev["partido_key"].astype("string"),
        "partido_id_tml": ev["pid_tml"].astype("Int64"), "partido_id_sofascore": ev["pid_sofa"].astype("Int64"),
        "circuito": ev["circuito"].astype("string"), "temporada": ev["temporada"].astype("Int64"),
        "jugador_1": ev["jugador_1"].astype("Int64"), "jugador_2": ev["jugador_2"].astype("Int64"),
        "ronda": ev["ronda"].astype("string"), "superficie": ev["superficie"].astype("string"),
        "indoor": ev["indoor"].astype("boolean"), "mejor_de": ev["mejor_de"].astype("Int64"),
        "formato_decisivo": ev["formato_decisivo"].astype("string"),
        "estado": ev["r_estado"].astype("string"), "ganador": ev["r_ganador"].astype("Int64"),
        "retira": ev["r_retira"].astype("Int64"),
        "sets": pd.array([_sets_json(s) for s in ev["r_sets"]], dtype="string"),
        "sets_completos": ev["r_sets_completos"].astype("Int64"),
        "juegos_1": ev["juegos_1"], "juegos_2": ev["juegos_2"],
        "minutos_1": dur, "minutos_2": dur,
        "minutos_origen": ev["r_fuente"].where(dur.notna()).astype("string"),
        # Un minuto faltante NO es 0. No hay regresión documentada de minutos ~ juegos: no se estima nada.
        "minutos_estimados": pd.array([False if pd.notna(d) else None for d in dur], dtype="boolean"),
        "actualiza_rating": ev["r_estado"].eq("completado").astype("boolean"),
        "inicio_utc": ev["inicio_utc"], "corte_utc": ev["corte_utc"],
        "visible_resultado_utc": ev["r_vis"],
        "fuente_tiempo": ev["fuente_tiempo"].astype("string"), "fuente_resultado": ev["r_fuente"].astype("string"),
        "resultado_id": ev["r_resultado_id"].astype("Int64"),
    }).sort_values(["visible_resultado_utc", "partido_key"]).reset_index(drop=True)
    eventos.insert(0, "orden", pd.array(np.arange(1, len(eventos) + 1), dtype="Int64"))

    # ---- estadísticas de saque (solo completados): fila de la fuente del tiempo; si falta y el partido está
    # fusionado, la de la otra fuente, visible desde max(su instante, el del evento).
    comp = eventos[eventos["estado"] == "completado"][["partido_key", "partido_id_tml", "partido_id_sofascore",
                                                       "fuente_tiempo", "visible_resultado_utc", "jugador_1",
                                                       "jugador_2"]]
    Ek = E.drop_duplicates(["partido_id", "lado"])
    filas = []
    for fuente_col in ("partido_id_sofascore", "partido_id_tml"):
        x = comp.merge(Ek, left_on=fuente_col, right_on="partido_id")
        x["prio_sel"] = np.where(x["fuente_tiempo"].eq("sofascore") == (fuente_col == "partido_id_sofascore"), 0, 1)
        filas.append(x)
    est = pd.concat(filas, ignore_index=True).sort_values(["partido_key", "lado", "prio_sel"])
    est = est.drop_duplicates(["partido_key", "lado"])
    cal["estadistica:ceros_imposibles_descartados"] = int((est["puntos_saque"] == 0).sum())
    est = est[~(est["puntos_saque"] == 0)]
    ganados = est["primeros_ganados"].astype("Int64") + est["segundos_ganados"].astype("Int64")
    est_out = pd.DataFrame({
        "partido_key": est["partido_key"].astype("string"), "lado": est["lado"].astype("Int64"),
        "jugador_id": np.where(est["lado"] == 1, est["jugador_1"], est["jugador_2"]).astype("int64"),
        "puntos_saque": est["puntos_saque"].astype("Int64"), "puntos_saque_ganados": ganados,
        "aces": est["aces"].astype("Int64"), "dobles_faltas": est["dobles_faltas"].astype("Int64"),
        "primeros_dentro": est["primeros_dentro"].astype("Int64"),
        "primeros_ganados": est["primeros_ganados"].astype("Int64"),
        "segundos_ganados": est["segundos_ganados"].astype("Int64"),
        "juegos_saque": est["juegos_saque"].astype("Int64"), "bp_salvados": est["bp_salvados"].astype("Int64"),
        "bp_afrontados": est["bp_afrontados"].astype("Int64"),
        "fuente": est["fuente"].astype("string"), "estadistica_id": est["estadistica_id"].astype("Int64"),
        "visible_desde": est[["vis", "visible_resultado_utc"]].max(axis=1),
    }).sort_values(["partido_key", "lado"]).reset_index(drop=True)

    rasof = rasof[rasof["partido_key"].isin(claves)]
    rk_out = pd.DataFrame({
        "partido_key": rasof["partido_key"].astype("string"), "lado": rasof["lado"].astype("Int64"),
        "jugador_id": rasof["jugador_id"].astype("Int64"), "fecha_partido": pd.to_datetime(rasof["fecha_partido"]),
        "corte_utc": rasof["corte_utc"],
        "fecha_publicacion": pd.to_datetime(rasof["fecha_publicacion"]),
        "posicion": rasof["posicion"].astype("Int64"), "puntos": rasof["puntos"].astype("Int64"),
        "origen": rasof["origen"].astype("string"), "fuente": rasof["fuente"].astype("string"),
        "ranking_id": rasof["ranking_id"].astype("Int64"),
        "visible_desde": pd.to_datetime(rasof["visible_desde"], utc=True),
    }).sort_values(["partido_key", "lado"]).reset_index(drop=True)

    def _vf(tabla, df, id_col, con_lado=False, con_prio=True):
        n = len(df)
        return pd.DataFrame({
            "tabla": pd.array([tabla] * n, dtype="string"), "partido_id": df["partido_id"].astype("Int64").values,
            "lado": df["lado"].astype("Int64").values if con_lado else pd.array([pd.NA] * n, dtype="Int64"),
            "fila_id": df[id_col].astype("Int64").values, "fuente": df["fuente"].astype("string").values,
            "prio": df["prio"].astype("Int64").values if con_prio else pd.array([pd.NA] * n, dtype="Int64"),
            "recibido_en": df["recibido_en"].values, "vis": df["vis"].values,
            "no_monotona": df["no_monotona"].astype("boolean").values})

    vf = pd.concat([_vf("partido", P, "partido_id", con_prio=False), _vf("programa", G, "programa_id"),
                    _vf("resultado", R, "resultado_id"), _vf("estadistica", E, "estadistica_id", con_lado=True)],
                   ignore_index=True)
    vf["recibido_en"] = pd.to_datetime(vf["recibido_en"], utc=True)
    vf["vis"] = pd.to_datetime(vf["vis"], utc=True)
    vf = vf.sort_values(["tabla", "partido_id", "lado", "fila_id"]).reset_index(drop=True)
    cal["orden_lados:p_gana_id_menor"] = round(float((part["y_ganador"] == 1).sum()
                                                      / max(part["y_ganador"].notna().sum(), 1)), 6)
    part, eventos, est_out, rk_out = _orientar(part, eventos, est_out, rk_out)
    cal["orden_lados:p_gana_lado_1"] = round(float((part["y_ganador"] == 1).sum()
                                                    / max(part["y_ganador"].notna().sum(), 1)), 6)
    calidad = _calidad(part, eventos, est_out, rk_out, cal, t)
    return {"partidos": part, "eventos_resultado": eventos, "ranking_asof": rk_out,
            "estadisticas_saque": est_out, "visibilidad_filas": vf, "calidad": calidad}


def invertir_lado(partido_key: str) -> bool:
    """Orden de los lados en la exportación: pseudoaleatorio por partido (bit del sha256 de su clave), determinista e
    independiente del resultado y de la historia. NO se usa el orden de ids de la base: el id de un jugador sale del
    orden de carga (TML carga primero la gira principal de todos los años, después WTA, challengers y previas, y dentro
    de cada fila crea antes al GANADOR), así que el id menor gana el 55 % de los partidos y, cuando los dos debutan
    juntos, el id menor es el ganador de ESE partido. Ese orden revelaría el resultado (regla 2)."""
    return hashlib.sha256(partido_key.encode()).digest()[0] & 1 == 1


def _sets_invertidos(texto):
    if texto is None or texto is pd.NA or texto != texto:
        return texto
    return json.dumps([[s[1], s[0], s[3], s[2]] for s in json.loads(texto)], separators=(",", ":"))


def _cambiar(df: pd.DataFrame, inv: pd.Series, pares: list[tuple[str, str]], lados: list[str],
             sets: list[str]) -> pd.DataFrame:
    df = df.copy()
    for a, b in pares:
        va, vb = df[a].copy(), df[b].copy()
        df.loc[inv, a] = vb[inv]
        df.loc[inv, b] = va[inv]
    for c in lados:
        df.loc[inv, c] = 3 - df.loc[inv, c]
    for c in sets:
        df.loc[inv, c] = [_sets_invertidos(s) for s in df.loc[inv, c]]
    return df


def _orientar(part, eventos, est, rk):
    """Aplica `invertir_lado` a todas las tablas (columnas por lado, ganador, retira, sets, juegos y `lado`)."""
    inv_p = part["partido_key"].map(invertir_lado).astype(bool)
    pares_p = [("jugador_1", "jugador_2"), ("edad_1", "edad_2"), ("rank_1", "rank_2"), ("puntos_1", "puntos_2"),
               ("rank_origen_1", "rank_origen_2"), ("rank_fecha_1", "rank_fecha_2"), ("n_prev_1", "n_prev_2"),
               ("entrada_1", "entrada_2"), ("y_juegos_1", "y_juegos_2")]
    part = _cambiar(part, inv_p, pares_p, ["y_ganador", "y_retira"], ["y_sets"])
    m = part["marcas"].fillna("")
    for a, b in (("historia_corta_1", "historia_corta_2"), ("sin_ranking_1", "sin_ranking_2")):
        m = m.where(~inv_p, m.str.replace(a, "\0", regex=False).str.replace(b, a, regex=False)
                    .str.replace("\0", b, regex=False))
    part["marcas"] = pd.array([None if (x == "" or pd.isna(x)) else ";".join(sorted(x.split(";")))
                               for x in m], dtype="string")
    inv_e = eventos["partido_key"].map(invertir_lado).astype(bool)
    eventos = _cambiar(eventos, inv_e, [("jugador_1", "jugador_2"), ("juegos_1", "juegos_2")],
                       ["ganador", "retira"], ["sets"])
    est = est.copy()
    est.loc[est["partido_key"].map(invertir_lado).astype(bool), "lado"] = \
        3 - est.loc[est["partido_key"].map(invertir_lado).astype(bool), "lado"]
    rk = rk.copy()
    inv_r = rk["partido_key"].map(invertir_lado).astype(bool)
    rk.loc[inv_r, "lado"] = 3 - rk.loc[inv_r, "lado"]
    return (part, eventos, est.sort_values(["partido_key", "lado"]).reset_index(drop=True),
            rk.sort_values(["partido_key", "lado"]).reset_index(drop=True))


def _calidad(part, eventos, est, rk, cal, t) -> dict:
    p = part.assign(anio=part["fecha_partido"].dt.year)
    por = p.groupby(["circuito", "anio", "fuente_tiempo"], dropna=False).size()
    sin_res = t.get("sin_resolver_conteo", {})
    fus = part["fusion_metodo"].notna().sum()
    sofa = part["partido_id_sofascore"].notna().sum()
    marcas = Counter(m for s in part["marcas"].dropna() for m in s.split(";"))
    return {
        "partidos": int(len(part)), "eventos": int(len(eventos)), "estadisticas_saque_filas": int(len(est)),
        "ranking_asof_filas": int(len(rk)), "ranking_asof_nulos": int(rk["ranking_id"].isna().sum()),
        "por_circuito_anio_fuente_tiempo": [{"circuito": c, "anio": int(a) if pd.notna(a) else None, "fuente_tiempo": f,
                                             "partidos": int(n)} for (c, a, f), n in por.items()],
        "por_fuente_tiempo": {k: int(v) for k, v in part["fuente_tiempo"].value_counts().sort_index().items()},
        "fusion": {"fusionados": int(fus), "con_sofascore": int(sofa),
                   "tasa_sobre_sofascore": round(float(fus / sofa), 6) if sofa else None,
                   "por_metodo": {k: int(v) for k, v in part["fusion_metodo"].value_counts().sort_index().items()},
                   **{k.split(":", 1)[1]: v for k, v in sorted(cal.items()) if k.startswith("fusion:")}},
        "excluidos_por_motivo": {k: int(v) for k, v in part["excluir_motivo"].value_counts().sort_index().items()},
        "marcas": dict(sorted(marcas.items())),
        "formato_decisivo": {k: int(v) for k, v in part["formato_decisivo"].value_counts().sort_index().items()},
        "superficie": {str(k): int(v) for k, v in part["superficie"].value_counts(dropna=False).sort_index().items()},
        "sin_resolver_en_la_base": sin_res,
        "contadores": {k: v for k, v in sorted(cal.items()) if not k.startswith("fusion:")},
        "limitaciones_calendario": [
            "TML no trae hora: sin SofaScore el corte es la visibilidad conservadora de la pareja + 1 s (tml_reglas), "
            "que cae tras el inicio real en ~55 % de los partidos comparados (integración S2b).",
            "Fuga residual del calendario de TML medida contra SofaScore: 0,97 % (125 de 12.924); 3 ediciones de ~100 "
            "con tourney_date en la semana del clasificatorio. Con hora real se usan SIEMPRE los tiempos de SofaScore.",
            "Fuera de 2023-2026 el calendario de TML no es verificable hacia atrás.",
            "Sin sedes cargadas: la fecha local del partido usa UTC (huso de la sede cuando exista).",
            "Edades solo con fecha de nacimiento en la base (SofaScore); TML no persiste edades.",
        ],
    }


# ------------------------------------------------------------------------------------------------ escritura
def _tabla_arrow(df: pd.DataFrame) -> pa.Table:
    return pa.Table.from_pandas(df, preserve_index=False).replace_schema_metadata(None).combine_chunks()


def sha_contenido(tabla: pa.Table) -> str:
    """sha256 del contenido: flujo IPC de Arrow de la tabla (sin metadatos de pandas), determinista."""
    buf = io.BytesIO()
    with pa.ipc.new_stream(buf, tabla.schema) as w:
        w.write_table(tabla)
    return hashlib.sha256(buf.getvalue()).hexdigest()


def _sha_fichero(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _sha_codigo() -> str:
    h = hashlib.sha256()
    for p in sorted(Path(__file__).parent.glob("*.py")):
        h.update(p.name.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


REGLAS = {
    "visibilidad": "Un dato es visible en el corte c si y solo si c > vis. vis: en vivo recibido_en − 1 µs; retro con "
                   "visible_desde: visible_desde; retro sin él: lunes_semana de la edición vigente en c + 7 días "
                   "(reimplementa visible_a_las/retro_visible/lunes_por_partido_a_las de db/0004).",
    "corte": "Con hora real de SofaScore: inicio − 60 min. Sin ella (solo TML): visible_desde de la pareja (fin "
             "conservador de la ronda anterior o inicio de la edición) + 1 s.",
    "visible_resultado": "Instante de visibilidad de la fila de resultado de la fuente del tiempo (SofaScore si hay hora "
                         "real; el calendario de TML no se usa para esos partidos).",
    "fusion": "Ver tenis/datos/fusion.py: (1) estricta por (jugador_1, jugador_2, ronda, inicio SofaScore en [L, "
              "fin+1)); (2) por edición enlazada biyectiva sin ventana; (3) pareja única en ediciones enlazadas sin "
              "mirar la ronda (no RR). QL ↔ ronda Q más alta de la edición TML; ambiguos sin fusionar y contados.",
    "orden_lados": "jugador_1/jugador_2 en orden pseudoaleatorio por partido (bit del sha256 de partido_key), NO por "
                   "id: el orden de ids de la base viene del orden de carga y el id menor gana el 55 % (ver calidad).",
    "atributos_as_of": "mejor_de, entradas y atributos de edición (superficie, indoor) solo de filas fuente cuya fila "
                       "de partido y edición son visibles en el corte; SofaScore antes que TML.",
    "superficie": "Clay, Grass, Hard, Indoor; tierra bajo techo = Clay con indoor=True; moqueta = Indoor salvo "
                  "indoor=False; indoor desconocido = superficie de su base con indoor NULL (marca).",
    "formato_decisivo": "tenis/datos/reglas.py:formato_decisivo (Grand Slams por año, gira tiebreak a 7, Laver "
                        "supertiebreak, resto desconocido).",
    "ranking": "ranking_a_las(corte, fecha_partido): por fecha de publicación la mejor fila visible (prioridad, "
               "recibido_en desc, id desc); la publicación más reciente con fecha_publicacion <= fecha_partido. "
               "fecha_partido: con hora, fecha local de la sede (sin sede, UTC); sin hora, inicio L de la edición TML.",
    "edad": "(fecha_partido − fecha de nacimiento vigente) / 365,25; sin fecha de nacimiento → NULL.",
    "n_prev": "Eventos completados o retirada del jugador con visible_resultado_utc < corte (toda la historia de la "
              "base, también anterior a `desde`). < 20 → marca historia_corta (no se descarta).",
    "minutos": "Duración del partido para ambos lados; faltante = NULL (no 0); sin regresión documentada no se estima "
               "(minutos_estimados NULL). Walkover: sin minutos (no se jugó).",
    "estadisticas_saque": "Solo completados; fila de la fuente del tiempo, si no la de la otra fuente fusionada, "
                          "visible desde max(su instante, visible_resultado_utc); puntos_saque = 0 se descarta.",
    "semana_previa_gs": "Inicio de la edición entre 3 y 9 días antes del inicio del cuadro principal de un GS del "
                        "mismo circuito.",
}
EXCEPCIONES = {
    "semana_previa_gs": "Usa la fecha de inicio del Grand Slam, cuya edición retro es visible en la base más tarde que "
                        "el corte de los partidos de la semana previa. Es calendario publicado con meses de antelación "
                        "y no contiene ningún resultado; se declara aquí como excepción a la regla 1.",
    "identidad_torneo": "circuito, torneo, temporada y categoría son identidad del torneo (catálogo sin visible_desde).",
    "identidad_partido": "ronda (la de TML si está fusionado) y huso de la sede (para la fecha local) son identidad del "
                         "partido y del lugar; se usan aunque la fila de TML o la edición aún no sean visibles.",
}
ADVERTENCIAS = [
    "jugador_id es una CLAVE, no un rasgo: su magnitud refleja el orden de carga (gira principal de todos los años "
    "antes que challengers y previas; el ganador se crea antes en su fila) y correlaciona con el resultado. Nunca usar "
    "ids ni su orden como entrada numérica.",
    "n_prev cuenta toda la historia de la base (también anterior a `desde`).",
    "visible_resultado_utc es etiqueta: codifica la duración del partido.",
    "Partidos excluidos (excluir_motivo) se conservan en el fichero; filtrar por excluir_motivo IS NULL.",
]


def escribir(salidas: dict, directorio: Path, meta: dict) -> dict:
    directorio.mkdir(parents=True, exist_ok=True)
    ficheros = {}
    for nombre in ("partidos", "eventos_resultado", "ranking_asof", "estadisticas_saque", "visibilidad_filas"):
        tabla = _tabla_arrow(salidas[nombre])
        ruta = directorio / f"{nombre}.parquet"
        pq.write_table(tabla, ruta, compression="zstd", write_statistics=False)
        ficheros[nombre] = {"fichero": ruta.name, "filas": tabla.num_rows, "sha256_contenido": sha_contenido(tabla),
                            "sha256_fichero": _sha_fichero(ruta)}
    (directorio / "calidad.json").write_text(json.dumps(salidas["calidad"], indent=1, ensure_ascii=False,
                                                        default=str), encoding="utf-8")
    huella = hashlib.sha256("".join(ficheros[k]["sha256_contenido"] for k in sorted(ficheros)).encode()).hexdigest()
    entrada = [c for c in salidas["partidos"].columns
               if c not in COLUMNAS_ETIQUETA and not c.startswith("y_")]
    manifiesto = {
        "version_exportacion": VERSION, "sha256_codigo": _sha_codigo(), "sha256_export": huella,
        "generado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0], "pandas": pd.__version__, "pyarrow": pa.__version__,
        "plataforma": platform.platform(), **meta, "ficheros": ficheros,
        "columnas_etiqueta": COLUMNAS_ETIQUETA, "columnas_entrada": entrada,
        "reglas": REGLAS, "excepciones_regla_1": EXCEPCIONES, "advertencias": ADVERTENCIAS,
        "recuentos": {k: salidas["calidad"][k] for k in ("partidos", "eventos", "estadisticas_saque_filas",
                                                         "ranking_asof_filas")},
    }
    (directorio / "manifiesto.json").write_text(json.dumps(manifiesto, indent=1, ensure_ascii=False, default=str),
                                                encoding="utf-8")
    return manifiesto


def exportar(dsn: str, esquema: str, directorio: Path = SALIDA_POR_OMISION, desde: date | None = None) -> dict:
    """Lee el esquema (solo lectura), construye y escribe la exportación. Devuelve el manifiesto."""
    from .lectura import conexion_lectura, leer_todo, max_recibido
    with conexion_lectura(dsn, esquema) as conn:
        tablas = leer_todo(conn)
        corte_datos = max_recibido(conn)
        tablas["sin_resolver_conteo"] = {f"{f}:{m}": n for f, m, n in conn.execute(
            "SELECT fuente, motivo, count(*) FROM sin_resolver GROUP BY 1, 2 ORDER BY 1, 2").fetchall()}
    salidas = construir(tablas, desde)
    meta = {"esquema": esquema, "desde": desde.isoformat() if desde else None, "fecha_corte_datos": corte_datos}
    return escribir(salidas, Path(directorio), meta)
