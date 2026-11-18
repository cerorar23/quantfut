"""Fechas de nacimiento estimadas desde las edades de TML: estimación, descartes, idempotencia y uso por la exportación."""
from datetime import date

import pandas as pd
import pytest

from tenis.carga import nacimientos_tml as nt

NAC = date(1995, 3, 14)


def edad(nac: date, dia: date) -> float:
    return round((dia - nac).days / 365.25, 3)


def csv(ruta, filas):
    pd.DataFrame(filas, columns=["tourney_date", "winner_id", "winner_age", "loser_id", "loser_age"]).to_csv(ruta, index=False)


def test_estimacion_exacta_con_edades_de_tres_decimales(tmp_path):
    dias = [date(2018, 1, 8), date(2019, 6, 3), date(2021, 11, 15), date(2023, 2, 20)]
    csv(tmp_path / "2023.csv", [[d.strftime("%Y%m%d"), "AA11", edad(NAC, d), f"R{i}", 30.0] for i, d in enumerate(dias)])
    (tmp_path / "ATP_Database.csv").write_text("id,player,birthdate\nAA11,X,19800101\n")      # sin columnas de edad: se ignora
    est, _ = nt.estimar(nt.leer_edades(tmp_path))
    fila = est[est["id"] == "AA11"].iloc[0]
    assert abs((fila["nacimiento"] - NAC).days) <= 1 and fila["n"] == 4 and fila["dispersion_dias"] < 3


def test_se_descartan_edades_inconsistentes_y_fuera_de_rango(tmp_path):
    base = [date(2018, 1, 8), date(2019, 6, 3), date(2020, 9, 7)]
    filas = [[d.strftime("%Y%m%d"), "MALO", edad(NAC, d) + (3.0 if i == 2 else 0), "R", 30.0] for i, d in enumerate(base)]
    filas += [["20200101", "NINO", 7.0, "R", 30.0], ["20200101", "VIEJO", 70.0, "R", 30.0]]
    csv(tmp_path / "2020.csv", filas)
    est, cont = nt.estimar(nt.leer_edades(tmp_path))
    assert "MALO" not in set(est["id"]) and cont["descartado_edades_inconsistentes"] >= 1
    assert not {"NINO", "VIEJO"} & set(est["id"])


psycopg = pytest.importorskip("psycopg")
from db_util import insertar, nuevo_recibo as recibo_prueba, ts  # noqa: E402
from tenis import inferencia as inf  # noqa: E402


def jugador(db, tml_id, circuito="atp", nacimiento=None):
    r = recibo_prueba(db, "tml", "2025-12-01", retro=True)
    j = insertar(db, "INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES (%s, %s, %s) RETURNING jugador_id",
                 (circuito, r, ts("2025-12-01")))
    db.execute("INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
               "VALUES ('tml', %s, %s, 'id_exacto', %s, %s)", (tml_id, j, r, ts("2025-12-01")))
    if nacimiento:
        db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
                   "VALUES (%s, 'fecha_nacimiento', %s, 'sofascore', %s, %s)", (j, nacimiento, r, ts("2025-12-01")))
    return j


def estimaciones(**ids):
    return pd.DataFrame([{"id": k, "nacimiento": v, "n": 5, "dispersion_dias": 0.5} for k, v in ids.items()])


def test_carga_idempotente_sin_pisar_fechas_existentes(esquema, tmp_path):
    with esquema.conectar() as db:
        nuevo = jugador(db, "NUEVO")
        exacto = jugador(db, "EXACTO", nacimiento="1990-05-05")
        ambiguo = jugador(db, "AMBIGUO")
        r = recibo_prueba(db, "tml", "2025-12-01", retro=True)
        otro = insertar(db, "INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES ('atp', %s, %s) RETURNING jugador_id",
                        (r, ts("2025-12-01")))
        db.execute("INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
                   "VALUES ('tml', 'AMBIGUO', %s, 'manual', %s, %s)", (otro, r, ts("2025-12-01")))
        est = estimaciones(NUEVO=date(1999, 2, 3), EXACTO=date(1990, 5, 9), AMBIGUO=date(1980, 1, 1), FANTASMA=date(1985, 1, 1))
        ensayo = nt.cargar(db, est, tmp_path, ensayo=True)
        assert ensayo["a_escribir"] == 1 and ensayo["escritas"] == 0
        assert db.execute("SELECT count(*) FROM jugador_asercion WHERE fuente = 'tml' AND campo = 'fecha_nacimiento'").fetchone()[0] == 0
        c = nt.cargar(db, est, tmp_path, ahora=ts("2026-11-17T23:00:00Z"))
        assert (c["escritas"], c["ya_tenia_fecha"], c["id_ambiguo"], c["sin_jugador_en_la_base"]) == (1, 1, 1, 1)
        valor, retro, fuente = db.execute(
            "SELECT a.valor, r.retro, a.fuente FROM jugador_asercion a JOIN recibo r ON r.recibo_id = a.recibo_id "
            "WHERE a.jugador_id = %s AND a.campo = 'fecha_nacimiento'", (nuevo,)).fetchone()
        assert (valor, retro, fuente) == ("1999-02-03", True, "tml")
        assert db.execute("SELECT valor FROM jugador_asercion WHERE jugador_id = %s AND campo = 'fecha_nacimiento'",
                          (exacto,)).fetchone()[0] == "1990-05-05"
        assert nt.cargar(db, est, tmp_path)["escritas"] == 0


def test_la_exportacion_usa_la_edad_estimada_y_sofascore_manda(esquema, tmp_path):
    from inferencia_util import ranking
    from test_captura_propline_calendario import AHORA, doc, ev, mundo
    from tenis.captura import propline_calendario as pc
    from tenis.identidad.resolver import ResolutorMultifuente
    with esquema.conectar() as db:
        db.execute(f"SET search_path TO {esquema.nombre}, {esquema.nombre_op}, public")
        _, ids = mundo(db)
        a, b = ids["Carlos Test"][0], ids["Daniil Prueba"][0]
        ranking(db, a, 120), ranking(db, b, 45)
        r = recibo_prueba(db, "tml", "2025-12-01", retro=True)
        rs = recibo_prueba(db, "sofascore", "2025-12-01", retro=True)
        db.execute("INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
                   "VALUES ('tml', 'CT', %s, 'id_exacto', %s, %s), ('tml', 'DP', %s, 'id_exacto', %s, %s)",
                   (a, r, ts("2025-12-01"), b, r, ts("2025-12-01")))
        db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
                   "VALUES (%s, 'fecha_nacimiento', '2003-07-01', 'sofascore', %s, %s)", (b, rs, ts("2025-12-01")))
        c = nt.cargar(db, estimaciones(CT=date(1996, 4, 10), DP=date(1990, 1, 1)), tmp_path, ahora=ts("2026-01-05"))
        assert (c["escritas"], c["ya_tenia_fecha"]) == (1, 1)                       # DP ya tenía la exacta de SofaScore
        pc.capturar(db, doc([ev("1", "Carlos Test", "Daniil Prueba")]), tmp_path, ResolutorMultifuente(db), AHORA)
        p, _, _ = inf.conjunto_desde_db(db)
        f = p[p.partido_id_sofascore.notna()].iloc[0]
        edades = {int(f.jugador_1): f.edad_1, int(f.jugador_2): f.edad_2}
        assert edades[a] == round((date(2026, 11, 18) - date(1996, 4, 10)).days / 365.25, 3)    # la estimada de TML
        assert edades[b] == round((date(2026, 11, 18) - date(2003, 7, 1)).days / 365.25, 3)     # la exacta de SofaScore
