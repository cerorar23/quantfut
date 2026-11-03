"""
Clasificación calculada con nuestros resultados (`ingest/standings.py`).

Lo que fijan: puntos, partidos y goles salen de los partidos cerrados; el orden
es puntos, diferencia y goles a favor; los grupos (MLS, Argentina) se respetan
sin mezclar dos "primeros"; las eliminatorias no suman (tope de la fase
regular); las sanciones se aplican; la forma va del más reciente al más viejo;
los torneos cortos solo cuentan el semestre en curso.
"""
from __future__ import annotations

from datetime import datetime, timezone

from qf.ingest.standings import calcular, desde, season_label


def _p(h, a, hg, ag):
    return {"home_team_id": h, "away_team_id": a, "home_goals": hg, "away_goals": ag}


def _por_equipo(filas):
    return {f["team_id"]: f for f in filas}


def test_puntos_partidos_y_goles():
    t = _por_equipo(calcular([_p(1, 2, 2, 0), _p(2, 3, 1, 1), _p(3, 1, 0, 3)], {}))
    assert (t[1]["puntos"], t[1]["jugados"], t[1]["ganados"]) == (6, 2, 2)
    assert (t[1]["goles_favor"], t[1]["goles_contra"]) == (5, 0)
    assert (t[2]["puntos"], t[2]["empatados"], t[2]["perdidos"]) == (1, 1, 1)
    assert [f["team_id"] for f in sorted(t.values(), key=lambda f: f["posicion"])] == [1, 2, 3]


def test_desempate_por_diferencia_y_goles_a_favor():
    # 1 y 2 empatan a 3 puntos y diferencia +1; 2 marcó más.
    filas = calcular([_p(1, 3, 1, 0), _p(2, 4, 3, 2)], {})
    assert [f["team_id"] for f in sorted(filas, key=lambda f: f["posicion"])][:2] == [2, 1]


def test_la_mls_separa_conferencias():
    filas = calcular([_p(1, 2, 1, 0), _p(3, 4, 2, 0)],
                     {1: "Eastern Conference", 2: "Eastern Conference",
                      3: "Western Conference", 4: "Western Conference"})
    assert {(f["grupo"], f["posicion"], f["team_id"]) for f in filas if f["posicion"] == 1} == {
        ("Eastern Conference", 1, 1), ("Western Conference", 1, 3)}


def test_las_eliminatorias_no_suman():
    # Fase regular de 2 partidos por equipo; el tercero de 1 y 2 es eliminatoria.
    partidos = [_p(1, 2, 1, 0), _p(3, 4, 0, 0), _p(1, 3, 2, 2), _p(2, 4, 1, 0), _p(1, 2, 5, 0)]
    t = _por_equipo(calcular(partidos, {}, tope=2))
    assert t[1]["jugados"] == 2 and t[1]["goles_favor"] == 3
    assert t[2]["jugados"] == 2


def test_tope_por_defecto_es_ida_y_vuelta():
    partidos = [_p(1, 2, 1, 0), _p(2, 1, 1, 0), _p(1, 2, 3, 0)]
    assert _por_equipo(calcular(partidos, {}))[1]["jugados"] == 2


def test_sancion_de_puntos():
    t = _por_equipo(calcular([_p(1, 2, 1, 0)], {}, sanciones={1: -4}))
    assert t[1]["puntos"] == -1 and t[1]["posicion"] == 2


def test_forma_del_mas_reciente_al_mas_viejo():
    partidos = [_p(1, 2, 1, 0), _p(1, 3, 0, 0), _p(4, 1, 1, 0)]
    assert _por_equipo(calcular(partidos, {}, tope=10))[1]["forma"] == "LDW"


def test_torneo_corto_cuenta_el_semestre():
    mx = {"league_id": "mx.liga_mx", "season_style": "apertura_clausura"}
    assert desde(mx, datetime(2026, 10, 25, tzinfo=timezone.utc)) == datetime(
        2026, 7, 1, tzinfo=timezone.utc)
    assert desde(mx, datetime(2027, 2, 3, tzinfo=timezone.utc)) == datetime(
        2027, 1, 1, tzinfo=timezone.utc)
    ar = {"league_id": "ar.primera", "season_style": "calendar"}
    assert desde(ar, datetime(2026, 10, 25, tzinfo=timezone.utc)).month == 7
    assert desde({"league_id": "es.laliga", "season_style": "european"},
                 datetime(2026, 10, 25, tzinfo=timezone.utc)) is None


def test_respuesta_vacia():
    assert calcular([], {}) == []


def test_etiqueta_de_temporada_igual_que_el_resto():
    assert season_label(2026) == "2627"


def test_escudos_se_bajan_una_vez_y_solo_si_son_png(monkeypatch, tmp_path):
    from qf.ingest import standings

    (tmp_path / "1.png").write_bytes(b"ya estaba")
    pedidos = []

    class Resp:
        def __init__(self, contenido):
            self.content = contenido

        def raise_for_status(self):
            pass

    class Cliente:
        def __init__(self, **_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def get(self, url):
            pedidos.append(url)
            return Resp(b"\x89PNG..." if url.endswith("/20.png") else b"<html>")

    monkeypatch.setattr(standings.httpx, "Client", Cliente)
    monkeypatch.setattr(standings, "query", lambda sql: [
        {"team_id": 1, "af_team_id": 10}, {"team_id": 2, "af_team_id": 20},
        {"team_id": 3, "af_team_id": 30}])
    assert standings.descargar_escudos(str(tmp_path)) == 1
    assert pedidos == [standings.ESCUDO_URL.format(20), standings.ESCUDO_URL.format(30)]
    assert (tmp_path / "2.png").read_bytes().startswith(b"\x89PNG")
    assert not (tmp_path / "3.png").exists()
