"""Carga TML sobre datos reales (2025, ATP y WTA del snapshot A) contra un cálculo pandas aparte.

El cálculo pandas es otro camino de código: vectorizado, sin los módulos del cargador. Repite las mismas reglas
(validez del marcador, dobles, duplicados, estadísticas, ranking) para comprobar recuentos y sumas.
Se omite si falta el snapshot o QF_TEST_PG_DSN.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")

from tenis.carga.tml_cli import ejecutar  # noqa: E402

ORIGINALES = Path("C:/Users/huye/Documents/apuesta proyec/data/tennis/full_20261016/tml/originals")
try:
    MANIFIESTO = ORIGINALES.parents[1] / "download_manifest.json"
except IndexError:
    MANIFIESTO = ORIGINALES / "download_manifest.json"
FICHEROS = ["2025.csv", "2025_wta.csv"]


@pytest.fixture(scope="module")
def datos_reales(tmp_path_factory):
    if not (ORIGINALES / FICHEROS[0]).exists() or not MANIFIESTO.exists():
        pytest.skip("snapshot A no disponible")
    base = tmp_path_factory.mktemp("real")
    original = base / "tml" / "originals"
    original.mkdir(parents=True)
    man = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    entradas = [f for f in man["files"] if f.get("source") == "tml" and f["name"] in FICHEROS]
    for nombre in FICHEROS:
        shutil.copy(ORIGINALES / nombre, original / nombre)
    (base / "download_manifest.json").write_text(json.dumps({**man, "files": entradas}), encoding="utf-8")
    return original, base / "download_manifest.json", base


def _pandas_tabla():
    partes = []
    for nombre in FICHEROS:
        d = pd.read_csv(ORIGINALES / nombre, dtype=str, keep_default_na=False)
        d["circuito"] = "wta" if "_wta" in nombre else "atp"
        d["orden"] = range(len(d))
        d["fichero"] = nombre
        partes.append(d)
    d = pd.concat(partes, ignore_index=True)
    n = len(d)
    doble = d.winner_name.str.contains("/") | d.loser_name.str.contains("/")
    ids_ok = (d.winner_id != "") & (d.loser_id != "") & (d.winner_id != d.loser_id)
    fecha_ok = pd.to_datetime(d.tourney_date, format="%Y%m%d", errors="coerce").notna()
    ronda_ok = d["round"].str.match(r"^[A-Z]{1,2}[0-9]*$")
    bo = pd.to_numeric(d.best_of, errors="coerce")
    bo_ok = bo.isin([3, 5])
    s = d.score.str.strip()
    wo = s.str.lower().isin(["w/o", "wo", "walkover"])
    ret = s.str.contains(r"(?: RET| ret\.)$")
    dfl = s.str.endswith(" DEF")
    core = s.mask(wo, "").str.replace(r" (?:RET|ret\.|DEF)$", "", regex=True)
    toks = core.str.split().explode().dropna()
    toks = toks[toks != ""]
    pos = toks.groupby(level=0).cumcount()
    tot = toks.groupby(level=0).transform("size")
    ultimo = pos == tot - 1
    norm = toks.str.extract(r"^(\d+)-(\d+)(?:\((\d+)\))?$").astype(float)
    sup = toks.str.extract(r"^\[(\d+)-(\d+)\]$").astype(float)
    es_norm, es_sup = norm[0].notna(), sup[0].notna()
    a = norm[0].fillna(sup[0])
    b = norm[1].fillna(sup[1])
    t = norm[2]
    hi, lo = np.maximum(a, b), np.minimum(a, b)
    # Regla (5-nov): sin tie-break entre paréntesis vale 6-x (x≤4), 7-5, 7-6 (puntos de tie-break desconocidos) y los
    # sets de ventaja (hi ≥ 8 con diferencia 2); con tie-break solo 7-6.
    valido_norm = np.where(t.isna(), ((hi == 6) & (lo <= 4)) | ((hi == 7) & ((lo == 5) | (lo == 6)))
                           | ((hi >= 8) & ((hi - lo) == 2)), (hi == 7) & (lo == 6))
    valido_sup = (hi >= 10) & ((a - b).abs() >= 2)
    valido = np.where(es_sup, valido_sup, valido_norm) & (es_norm | es_sup)
    gana = a > b
    tok = pd.DataFrame({"row": toks.index, "valido": valido, "ultimo": ultimo.values, "gana": gana,
                        "reconocido": es_norm | es_sup}).groupby("row")
    res = pd.DataFrame({"n": tok.size(), "validos": tok.valido.sum(), "reconocidos": tok.reconocido.sum(),
                        "gana": tok.gana.sum(), "ultimo_invalido": tok.apply(lambda g: (~g.valido & g.ultimo).any())})
    d = d.join(res, how="left").fillna({"n": 0, "validos": 0, "reconocidos": 0, "gana": 0,
                                        "ultimo_invalido": False})
    d["n"], d["validos"], d["reconocidos"], d["gana"] = (d.n.astype(int), d.validos.astype(int),
                                                       d.reconocidos.astype(int), d.gana.astype(int))
    todos_ok = (d.n == d.validos) & (d.n == d.reconocidos)
    need = bo // 2 + 1
    completado = ~wo & ~ret & ~dfl & (s != "") & todos_ok & (d.n >= 2) & (d.n <= bo) & (d.gana == need) & \
        (d.n - d.gana < need)
    solo_ultimo_mal = (d.validos == d.n) | ((d.validos == d.n - 1) & d.ultimo_invalido.astype(bool))
    retirada = ret & (d.reconocidos == d.n) & solo_ultimo_mal & (d.n <= bo)
    walkover = wo & (d.n == 0)
    cancelado = (s == "") & (d.n == 0)
    desc = dfl & (d.reconocidos == d.n) & solo_ultimo_mal & (d.n <= bo)
    estado = np.select([walkover, cancelado, completado, retirada, desc],
                       ["walkover", "cancelado", "completado", "retirada", "descalificado"], "rechazo")
    ok = ~doble & ids_ok & fecha_ok & ronda_ok & bo_ok & (estado != "rechazo")
    d["estado"] = estado
    d["ok"] = ok
    clave = d.tourney_id + "|" + d["round"] + "|" + [
        "|".join(sorted([x, y])) for x, y in zip(d.winner_id, d.loser_id)]
    primero = ~clave.duplicated(keep="first")
    cargado = ok & primero
    d["cargado"] = cargado
    # superficie de la edición: primera no vacía por torneo y año (orden de carga)
    d["anio"] = d.tourney_id.str.extract(r"(\d{4})")[0]
    sup_ed = d[d.surface != ""].groupby(["circuito", "tourney_id", "anio"]).surface.first()
    d = d.join(sup_ed.rename("sup_ed"), on=["circuito", "tourney_id", "anio"])
    d["sup_ed"] = d.sup_ed.fillna("").str.lower()
    # estadísticas: lados con algún dato, y violaciones por fila
    cols = ["w_svpt", "w_1stIn", "w_1stWon", "w_bpSaved", "w_bpFaced"]
    num = lambda c: pd.to_numeric(d[c], errors="coerce")
    v_w = (num("w_1stWon") > num("w_1stIn")) | (num("w_1stIn") > num("w_svpt")) | \
        (num("w_bpSaved") > num("w_bpFaced"))
    v_l = (num("l_1stWon") > num("l_1stIn")) | (num("l_1stIn") > num("l_svpt")) | \
        (num("l_bpSaved") > num("l_bpFaced"))
    con_stats = d.estado.isin(["completado", "retirada"]) & cargado  # solo la primera aparición se escribe
    stat_ok = con_stats & ~(v_w.fillna(False) | v_l.fillna(False))
    lados_datos = (d[[c for c in d.columns if c.startswith("w_") and c[2:] in
                      ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced")]]
                   != "").any(axis=1)
    lados_l = (d[[c for c in d.columns if c.startswith("l_") and c[2:] in
                  ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced")]]
               != "").any(axis=1)
    est_filas = int((stat_ok & lados_datos).sum() + (stat_ok & lados_l).sum())
    # ranking: lunes ISO de la fecha, una observación por (circuito, lunes, jugador), la primera gana
    fecha = pd.to_datetime(d.tourney_date, format="%Y%m%d", errors="coerce")
    lunes = fecha - pd.to_timedelta(fecha.dt.weekday, unit="D")
    obs = []
    for lado, col_id, col_r in (("w", "winner_id", "winner_rank"), ("l", "loser_id", "loser_rank")):
        r = pd.to_numeric(d[col_r], errors="coerce")
        m = ok & r.notna() & (r >= 1)
        obs.append(pd.DataFrame({"circ": d.circuito[m], "lunes": lunes[m], "jug": d[col_id][m]}))
    obs = pd.concat(obs, ignore_index=True)
    ranking_obs = int(len(obs.drop_duplicates(["circ", "lunes", "jug"], keep="first")))
    return d, est_filas, ranking_obs


def _pandas_esperado() -> dict:
    d, est_filas, ranking_obs = _pandas_tabla()
    n, ok, cargado = len(d), d.ok, d.cargado
    doble = d.winner_name.str.contains("/") | d.loser_name.str.contains("/")
    return {"n": n, "doble": int(doble.sum()), "ok": int(ok.sum()), "cargado": int(cargado.sum()),
            "duplicado": int((ok & ~cargado).sum()), "rechazo": int(n - doble.sum() - ok.sum()),
            "por_estado": d[cargado].estado.value_counts().to_dict(),
            "por_circuito": d[cargado].circuito.value_counts().to_dict(),
            "por_bo": d[cargado].best_of.value_counts().to_dict(),
            "por_superficie": d[cargado].sup_ed.value_counts().to_dict(),
            "sets_ganador": int(d[cargado & d.estado.isin(["completado", "retirada"])].gana.sum()),
            "estadisticas": est_filas, "ranking": ranking_obs}


def test_carga_tml_real_2025_recuentos_igual_que_pandas(datos_reales, esquema):
    original, manifiesto, base = datos_reales
    res = ejecutar(original, esquema.dsn, esquema.nombre, manifiesto, base / "almacen", base / "rechazos.csv",
                   equivalencias=base / "no_existe.csv")
    esp = _pandas_esperado()
    db = esquema.conectar()
    assert res["leidas"] == esp["n"] and res["cuadra"] is True
    assert res["contadores"]["cargado"] == esp["cargado"]
    assert res["contadores"]["doble"] == esp["doble"]
    assert res["contadores"]["duplicado"] == esp["duplicado"]
    rechazos = sum(v for k, v in res["contadores"].items() if k.startswith("rechazo:"))
    assert rechazos == esp["rechazo"]
    assert dict(db.execute("SELECT r.estado, count(*) FROM resultado r GROUP BY 1").fetchall()) == esp["por_estado"]
    assert dict(db.execute("SELECT t.circuito, count(*) FROM partido p JOIN edicion e USING (edicion_id) "
                           "JOIN torneo t USING (torneo_id) GROUP BY 1").fetchall()) == esp["por_circuito"]
    assert dict(db.execute("SELECT mejor_de, count(*) FROM partido GROUP BY 1").fetchall()) == \
        {int(k): v for k, v in esp["por_bo"].items()}
    assert dict(db.execute("SELECT coalesce(e.superficie, ''), count(*) FROM partido p JOIN edicion e USING "
                           "(edicion_id) GROUP BY 1").fetchall()) == \
        {k: v for k, v in esp["por_superficie"].items()}
    sets_db = 0
    for ganador, sets in db.execute("SELECT ganador, sets FROM resultado WHERE estado IN ('completado', 'retirada')"):
        for g1, g2, _, _ in sets:
            sets_db += (g1 > g2) if ganador == 1 else (g2 > g1)
    assert sets_db == esp["sets_ganador"]
    assert db.execute("SELECT count(*) FROM estadistica").fetchone()[0] == esp["estadisticas"]
    assert db.execute("SELECT count(*) FROM ranking").fetchone()[0] == esp["ranking"]
