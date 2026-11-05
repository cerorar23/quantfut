"""Exportación PIT sobre un esquema aislado con un mundo SINTÉTICO de casos absurdos (TML + SofaScore construidos con
las mismas reglas de visibilidad que los cargadores), equivalencia con la puerta oficial, fuga y determinismo."""
import json
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import psycopg
import pytest
from psycopg.types.json import Jsonb

from db_util import insertar, nuevo_recibo, ts
from tenis.carga import tml_reglas as tr
from tenis.datos import equivalencia, exportar_pit

UTC = timezone.utc


class Mundo:
    """Inserta evidencia retro como lo harían los cargadores (visible_desde con las reglas de TML y SofaScore)."""

    def __init__(self, db):
        self.db = db
        self.r_tml = nuevo_recibo(db, "tml", "2026-11-02", retro=True)
        self.r_sofa = nuevo_recibo(db, "sofascore", "2026-11-04", retro=True)
        self.n = 0

    def jugador(self, circuito="atp") -> int:
        return insertar(self.db, "INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES (%s, %s, %s) "
                                 "RETURNING jugador_id", (circuito, self.r_tml, ts("2026-11-02")))

    def nacimiento(self, j, fecha):
        self.db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
                        "VALUES (%s, 'fecha_nacimiento', %s, 'sofascore', %s, %s)", (j, fecha, self.r_sofa, ts("2026-11-04")))

    def torneo(self, fuente, nombre, categoria, circuito="atp") -> int:
        self.n += 1
        r = self.r_tml if fuente == "tml" else self.r_sofa
        return insertar(self.db, "INSERT INTO torneo (circuito, clave, nombre, categoria, fuente, recibo_id, recibido_en) "
                                 "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING torneo_id",
                        (circuito, f"t{self.n}", nombre, categoria, fuente, r, ts("2026-11-02")))

    def sede(self, huso) -> int:
        self.n += 1
        return insertar(self.db, "INSERT INTO sede (clave, ciudad, pais, huso_iana, fuente, recibo_id, recibido_en) "
                                 "VALUES (%s, 'X', 'AUS', %s, 'sofascore', %s, %s) RETURNING sede_id",
                        (f"s{self.n}", huso, self.r_sofa, ts("2026-11-04")))

    def edicion_tml(self, torneo, L: date, dias=7, rondas=(), superficie="hard", indoor=False, vd=None) -> dict:
        eid = insertar(self.db, "INSERT INTO edicion (torneo_id, temporada, lunes_semana, fecha_fin, superficie, indoor, "
                                "fuente, recibo_id, recibido_en, visible_desde) VALUES (%s, %s, %s, %s, %s, %s, 'tml', "
                                "%s, %s, %s) RETURNING edicion_id",
                       (torneo, L.year, tr.lunes_semana_fin(L, dias), tr.fecha_fin(L, dias), superficie, indoor,
                        self.r_tml, ts("2026-11-02"), vd or tr.inicio_visible(L)))
        return {"id": eid, "L": L, "dias": dias, "rondas": set(rondas)}

    def partido_tml(self, e, ronda, j1, j2, estado="completado", ganador=1, duracion=None, mejor_de=3,
                    sin_visible=False, puntos_saque=None) -> int:
        a, b = sorted((j1, j2))
        vp = None if sin_visible else tr.visible_desde_partido(ronda, e["L"], e["dias"], e["rondas"])
        vr = None if sin_visible else tr.visible_desde_ronda(ronda, e["L"], e["dias"])
        pid = insertar(self.db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, "
                                "recibido_en, visible_desde) VALUES (%s, %s, %s, %s, %s, 'tml', %s, %s, %s) "
                                "RETURNING partido_id", (e["id"], ronda, a, b, mejor_de, self.r_tml, ts("2026-11-02"), vp))
        self._resultado(pid, estado, ganador, duracion, "tml", self.r_tml, ts("2026-11-02"), vr, mejor_de)
        if puntos_saque is not None:
            for lado in (1, 2):
                self._est(pid, lado, puntos_saque, "tml", self.r_tml, ts("2026-11-02"), vr)
        return pid

    def _resultado(self, pid, estado, ganador, duracion, fuente, r, rec, vd, mejor_de=3):
        sets = None
        if estado == "completado":
            n = mejor_de // 2 + 1
            sets = [[6, 3, None, None] if ganador == 1 else [3, 6, None, None] for _ in range(n)]
        self.db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, duracion_min, fuente, "
                        "recibo_id, recibido_en, visible_desde) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (pid, estado, ganador if estado == "completado" else None, Jsonb(sets) if sets else None,
                         len(sets) if sets else None, duracion, fuente, r, rec, vd))

    def _est(self, pid, lado, puntos, fuente, r, rec, vd):
        self.db.execute("INSERT INTO estadistica (partido_id, lado, puntos_saque, primeros_dentro, primeros_ganados, "
                        "segundos_ganados, fuente, recibo_id, recibido_en, visible_desde) VALUES (%s, %s, %s, %s, %s, "
                        "%s, %s, %s, %s, %s)", (pid, lado, puntos, puntos // 2, puntos // 3, puntos // 5, fuente, r,
                                                rec, vd))

    def edicion_sofa(self, torneo, inicio: datetime, fin: date, superficie="hard", indoor=False, sede=None,
                     vd=None) -> int:
        return insertar(self.db, "INSERT INTO edicion (torneo_id, temporada, lunes_semana, fecha_fin, superficie, indoor, "
                                 "sede_id, fuente, recibo_id, recibido_en, visible_desde) VALUES (%s, %s, %s, %s, %s, %s, "
                                 "%s, 'sofascore', %s, %s, %s) RETURNING edicion_id",
                        (torneo, inicio.year, tr.lunes_de(fin), fin, superficie, indoor, sede, self.r_sofa,
                         ts("2026-11-04"), vd or inicio - timedelta(days=7)))

    def partido_sofa(self, ed, ronda, j1, j2, inicio: datetime, estado="completado", ganador=1, duracion=90,
                     mejor_de=3, puntos_saque=None) -> int:
        a, b = sorted((j1, j2))
        vp = inicio - timedelta(hours=12)
        pid = insertar(self.db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, "
                                "recibido_en, visible_desde) VALUES (%s, %s, %s, %s, %s, 'sofascore', %s, %s, %s) "
                                "RETURNING partido_id", (ed, ronda, a, b, mejor_de, self.r_sofa, ts("2026-11-04"), vp))
        self.db.execute("INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, estado, fuente, recibo_id, "
                        "recibido_en, visible_desde) VALUES (%s, %s, 'fija', 'programado', 'sofascore', %s, %s, %s)",
                        (pid, inicio, self.r_sofa, ts("2026-11-04"), vp))
        fin = inicio + (timedelta(minutes=duracion + 30) if duracion else timedelta(hours=6))
        self._resultado(pid, estado, ganador, duracion, "sofascore", self.r_sofa, ts("2026-11-04"), fin, mejor_de)
        if puntos_saque is not None:
            for lado in (1, 2):
                self._est(pid, lado, puntos_saque, "sofascore", self.r_sofa, ts("2026-11-04"), fin)
        return pid

    def ranking(self, j, lunes: date, pos, fuente="tml", origen="tml_por_partido", recibido=None, retro=True):
        r = self.r_tml if retro else nuevo_recibo(self.db, fuente, recibido, retro=False)
        self.db.execute("INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, puntos, origen, fuente, "
                        "recibo_id, recibido_en, visible_desde) VALUES ('atp', %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (lunes, j, pos, 1000 - pos, origen, fuente, r,
                         ts(recibido) if recibido else ts("2026-11-02"), tr.inicio_visible(lunes) if retro else None))


def dt(texto):
    return datetime.fromisoformat(texto).replace(tzinfo=UTC)


@pytest.fixture
def mundo(esquema):
    db = esquema.conectar()
    m = Mundo(db)
    J = {k: m.jugador() for k in "abcdefghijklmnz"}
    m.nacimiento(J["a"], "2000-03-05")
    w = {"J": J}
    # A y B: semanas consecutivas del mismo 250 en las dos fuentes; la pareja (a,b) juega R32 en ambas.
    ta, sa = m.torneo("tml", "Lyon", "250"), m.torneo("sofascore", "Lyon", "250")
    eA = m.edicion_tml(ta, date(2024, 3, 4), rondas={"R32", "R16"})
    eB = m.edicion_tml(m.torneo("tml", "Marsella", "250"), date(2024, 3, 11), rondas={"R32"})
    sA = m.edicion_sofa(sa, dt("2024-03-04T00:00:00"), date(2024, 3, 10))
    sB = m.edicion_sofa(m.torneo("sofascore", "Marsella", "250"), dt("2024-03-11T00:00:00"), date(2024, 3, 17))
    w["tA_ab"] = m.partido_tml(eA, "R32", J["a"], J["b"], duracion=None, puntos_saque=60)
    w["sA_ab"] = m.partido_sofa(sA, "R32", J["a"], J["b"], dt("2024-03-05T12:00:00"), puntos_saque=70)
    w["tA_ac"] = m.partido_tml(eA, "R16", J["a"], J["c"], ganador=2)
    w["sA_ac"] = m.partido_sofa(sA, "R16", J["a"], J["c"], dt("2024-03-07T12:00:00"), ganador=2, duracion=None)
    w["tA_cd"] = m.partido_tml(eA, "R32", J["c"], J["d"])                   # solo TML en A
    w["tB_ab"] = m.partido_tml(eB, "R32", J["a"], J["b"])
    w["sB_ab"] = m.partido_sofa(sB, "R32", J["a"], J["b"], dt("2024-03-12T12:00:00"))
    w["sB_cd"] = m.partido_sofa(sB, "R32", J["c"], J["d"], dt("2024-03-12T14:00:00"))  # sin TML en B: no va con tA_cd
    w["sB_an"] = m.partido_sofa(sB, "R32", J["a"], J["n"], dt("2024-03-11T08:00:00"))  # antes de recibir el oficial
    w["tA_bd_wo"] = m.partido_tml(eA, "R16", J["b"], J["d"], estado="walkover")
    # C: edición desalineada (TML fechada en la semana del clasificatorio).
    eC = m.edicion_tml(m.torneo("tml", "Estoril", "250"), date(2024, 4, 1), rondas={"Q1", "R32", "F"},
                       superficie="clay", indoor=None)
    sC = m.edicion_sofa(m.torneo("sofascore", "Estoril", "250"), dt("2024-04-01T00:00:00"), date(2024, 4, 14),
                        superficie="clay", indoor=False)
    w["tC_q1"] = m.partido_tml(eC, "Q1", J["e"], J["f"])
    w["sC_q1"] = m.partido_sofa(sC, "Q1", J["e"], J["f"], dt("2024-04-02T10:00:00"))
    w["tC_r32"] = m.partido_tml(eC, "R32", J["e"], J["g"])
    w["sC_r32"] = m.partido_sofa(sC, "R32", J["e"], J["g"], dt("2024-04-09T10:00:00"))
    w["tC_f"] = m.partido_tml(eC, "F", J["e"], J["h"])
    w["sC_f"] = m.partido_sofa(sC, "F", J["e"], J["h"], dt("2024-04-14T10:00:00"))
    # D: Grand Slam de dos semanas con solo la primera semana en TML.
    eD = m.edicion_tml(m.torneo("tml", "Roland Garros", "GS"), date(2024, 5, 26), dias=14, rondas={"R128", "R64"},
                       superficie="clay")
    sD = m.edicion_sofa(m.torneo("sofascore", "Roland Garros", "GS"), dt("2024-05-20T00:00:00"), date(2024, 6, 9),
                        superficie="clay")
    w["tD_128"] = m.partido_tml(eD, "R128", J["i"], J["j"], mejor_de=5)
    w["sD_128"] = m.partido_sofa(sD, "R128", J["i"], J["j"], dt("2024-05-26T10:00:00"), mejor_de=5, duracion=200)
    w["tD_64"] = m.partido_tml(eD, "R64", J["i"], J["k"], mejor_de=5)
    w["sD_64"] = m.partido_sofa(sD, "R64", J["i"], J["k"], dt("2024-05-28T10:00:00"), mejor_de=5)
    w["sD_16"] = m.partido_sofa(sD, "R16", J["i"], J["l"], dt("2024-06-02T10:00:00"), mejor_de=5)
    w["sD_qf"] = m.partido_sofa(sD, "QF", J["i"], J["m"], dt("2024-06-04T10:00:00"), mejor_de=5)
    # E: partido cuya edición no es visible hasta 2030 (retro sin visible_desde): pareja y resultado a la vez.
    eE = m.edicion_tml(m.torneo("tml", "Fantasma", "250"), date(2024, 6, 3), vd=dt("2030-01-01T00:00:00"))
    w["tE"] = m.partido_tml(eE, "R32", J["a"], J["z"], sin_visible=True)
    # F: SofaScore cuya edición se ve DESPUÉS del corte (atributos de edición no disponibles) y sede en Melbourne.
    sF = m.edicion_sofa(m.torneo("sofascore", "Melbourne Raro", "250"), dt("2024-01-10T00:00:00"), date(2024, 1, 20),
                        sede=m.sede("Australia/Melbourne"), vd=dt("2024-01-14T23:00:00"))
    w["sF"] = m.partido_sofa(sF, "R32", J["a"], J["z"], dt("2024-01-14T23:30:00"))
    # Ranking de a: semanal de TML y un oficial capturado EN VIVO el lunes 11-mar a las 10:00.
    for lunes, pos in ((date(2024, 1, 8), 12), (date(2024, 1, 15), 11), (date(2024, 2, 26), 10),
                       (date(2024, 3, 4), 8), (date(2024, 3, 11), 5)):
        m.ranking(J["a"], lunes, pos)
    m.ranking(J["a"], date(2024, 3, 11), 6, fuente="sportsapipro", origen="oficial_capturado",
              recibido="2024-03-11T10:00:00Z", retro=False)
    for k in "bcdefghijklmn":
        m.ranking(J[k], date(2024, 1, 1), 50)
    w["esquema"] = esquema
    return w


@pytest.fixture
def exportado(mundo, tmp_path):
    e = mundo["esquema"]
    man = exportar_pit.exportar(e.dsn, e.nombre, tmp_path / "exp")
    p = pd.read_parquet(tmp_path / "exp" / "partidos.parquet")
    return mundo, man, p, tmp_path / "exp"


def _fila(p, tml=None, sofa=None):
    m = pd.Series(True, index=p.index)
    m &= p["partido_id_tml"].eq(tml) if tml else p["partido_id_tml"].isna()
    m &= p["partido_id_sofascore"].eq(sofa) if sofa else p["partido_id_sofascore"].isna()
    assert m.sum() == 1, (tml, sofa)
    return p[m].iloc[0]


def test_duracion_cero_imposible(esquema):
    db = esquema.conectar()
    m = Mundo(db)
    a, b = sorted((m.jugador(), m.jugador()))
    e = m.edicion_tml(m.torneo("tml", "X", "250"), date(2024, 3, 4), rondas={"R32"})
    with pytest.raises(psycopg.errors.CheckViolation):
        m.partido_tml(e, "R32", a, b, duracion=0)


def test_absurdos(exportado):
    w, man, p, d = exportado
    ev = pd.read_parquet(d / "eventos_resultado.parquet")
    # Fusión: cada semana con la suya; (c,d) de B solo en SofaScore no se pega al (c,d) de A.
    assert _fila(p, w["tA_ab"], w["sA_ab"])["fusion_metodo"] == "estricta"
    assert _fila(p, w["tB_ab"], w["sB_ab"])["fusion_metodo"] == "estricta"
    _fila(p, w["tA_cd"], None)
    _fila(p, None, w["sB_cd"])
    # Edición desalineada: Q1 estricta, el cuadro por edición enlazada; superficie de SofaScore (indoor conocido).
    assert _fila(p, w["tC_q1"], w["sC_q1"])["fusion_metodo"] == "estricta"
    r32 = _fila(p, w["tC_r32"], w["sC_r32"])
    assert r32["fusion_metodo"] == "edicion_enlazada" and r32["superficie"] == "Clay" and r32["indoor"] == False  # noqa: E712
    assert _fila(p, w["tC_f"], w["sC_f"])["fusion_metodo"] == "edicion_enlazada"
    # GS de dos semanas con media TML: la segunda semana queda solo en SofaScore, sin fusiones erróneas.
    gs = _fila(p, None, w["sD_qf"])
    assert gs["formato_decisivo"] == "tiebreak_10" and gs["mejor_de"] == 5 and gs["fuente_tiempo"] == "sofascore"
    _fila(p, None, w["sD_16"])
    assert _fila(p, w["tD_128"], w["sD_128"])["fusion_metodo"] == "estricta"
    # Orden de lados: pseudoaleatorio por partido (no el de ids ni el del ganador); las etiquetas lo siguen.
    assert ((p["jugador_1"] > p["jugador_2"]) == p["partido_key"].map(exportar_pit.invertir_lado)).all()
    assert set(p["y_ganador"].dropna()) == {1, 2}
    fa = _fila(p, w["tA_ab"], w["sA_ab"])                  # en la base gana a (lado 1 canónico)
    assert fa[f"jugador_{int(fa['y_ganador'])}"] == w["J"]["a"]
    assert json.loads(fa["y_sets"])[0][int(fa["y_ganador"]) - 1] == 6
    # Corte con hora real: inicio − 60 min; sin hora: pareja + 1 s.
    f = _fila(p, w["tA_ab"], w["sA_ab"])
    assert f["corte_utc"] == pd.Timestamp("2024-03-05T11:00:00Z")
    solo = _fila(p, w["tA_cd"], None)
    assert solo["fuente_tiempo"] == "tml" and solo["corte_utc"] == pd.Timestamp("2024-03-04T00:00:01Z")
    assert pd.isna(solo["inicio_utc"])
    # Walkover: evento sin ganador, no actualiza rating, sin minutos (no 0) y sin estadísticas.
    wo = ev[ev["partido_id_tml"] == w["tA_bd_wo"]].iloc[0]
    assert wo["estado"] == "walkover" and pd.isna(wo["ganador"]) and not wo["actualiza_rating"]
    assert pd.isna(wo["minutos_1"])
    # Duración faltante: NULL y sin estimar (nunca 0).
    sin_dur = ev[ev["partido_id_sofascore"] == w["sA_ac"]].iloc[0]
    assert pd.isna(sin_dur["minutos_1"]) and pd.isna(sin_dur["minutos_estimados"])
    assert (ev["minutos_1"].dropna() > 0).all()
    # Edición nunca visible a tiempo: pareja y resultado a la vez → excluido.
    assert _fila(p, w["tE"], None)["excluir_motivo"] == "resultado_visible_en_su_corte"
    # Edición de SofaScore no visible en el corte: sin superficie, marcado; fecha local de Melbourne (15-ene).
    fF = _fila(p, None, w["sF"])
    assert pd.isna(fF["superficie"]) and "edicion_no_visible_en_corte" in fF["marcas"]
    assert fF["fecha_partido"] == pd.Timestamp("2024-01-15") and fF["fecha_partido_regla"] == "local_sede"
    # ... y aun así el ranking del lunes 15 (visible desde 15-ene 00:00 UTC) NO está: el corte es 14-ene 22:30 UTC.
    j_a = w["J"]["a"]
    lado_a = 1 if fF["jugador_1"] == j_a else 2
    assert fF[f"rank_{lado_a}"] == 12
    # Jugador sin ranking: NULL y marca.
    lado_z = 3 - lado_a
    assert pd.isna(fF[f"rank_{lado_z}"]) and f"sin_ranking_{lado_z}" in fF["marcas"]
    # Ranking: oficial capturado en vivo gana a TML solo cuando ya se había recibido.
    b12 = _fila(p, w["tB_ab"], w["sB_ab"])
    assert b12["rank_1" if b12["jugador_1"] == j_a else "rank_2"] == 6
    an = _fila(p, None, w["sB_an"])
    assert an["rank_1" if an["jugador_1"] == j_a else "rank_2"] == 5
    # TML sin hora: ranking con fecha <= inicio L de la edición.
    assert solo["rank_fecha_1"] <= pd.Timestamp("2024-03-04")
    # Edad desde la fecha de nacimiento (solo a la tiene).
    assert abs(f["edad_1" if f["jugador_1"] == j_a else "edad_2"] - 24.0) < 0.01
    # Etiquetas separadas y declaradas.
    assert "y_ganador" in man["columnas_etiqueta"] and "visible_resultado_utc" in man["columnas_etiqueta"]
    assert not set(man["columnas_etiqueta"]) & set(man["columnas_entrada"])
    # Estadísticas de saque: solo completados, de la fuente del tiempo (SofaScore 70) en el fusionado.
    es = pd.read_parquet(d / "estadisticas_saque.parquet")
    k = f["partido_key"]
    assert set(es.loc[es["partido_key"] == k, "puntos_saque"]) == {70}
    assert (es["puntos_saque"] > 0).all()


def test_fuga_y_orden_de_eventos(exportado):
    w, man, p, d = exportado
    ev = pd.read_parquet(d / "eventos_resultado.parquet")
    assert ev["visible_resultado_utc"].is_monotonic_increasing
    con_corte = p[p["corte_utc"].notna() & p["excluir_motivo"].isna()]
    vis = dict(zip(ev["partido_key"], ev["visible_resultado_utc"]))
    for _, f in con_corte.iterrows():
        assert not vis.get(f["partido_key"], pd.Timestamp.max.tz_localize("UTC")) < f["corte_utc"]
    hora = p[p["fuente_tiempo"] == "sofascore"]
    assert (hora["visible_resultado_utc"] > hora["corte_utc"]).all()


def test_equivalencia_con_la_puerta_sintetica(exportado):
    w, man, p, d = exportado
    e = w["esquema"]
    res = equivalencia.verificar(e.dsn, e.nombre, d, n=len(p), hilos=2)
    assert res["identico"], json.dumps(res, default=str)
    assert res["partidos_muestra"] == p["corte_utc"].notna().sum()


def test_determinismo(exportado, tmp_path):
    w, man, p, d = exportado
    e = w["esquema"]
    otro = exportar_pit.exportar(e.dsn, e.nombre, tmp_path / "exp2")
    assert otro["sha256_export"] == man["sha256_export"]
    assert {k: v["sha256_contenido"] for k, v in otro["ficheros"].items()} == \
           {k: v["sha256_contenido"] for k, v in man["ficheros"].items()}
