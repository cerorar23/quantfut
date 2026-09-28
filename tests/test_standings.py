"""
Clasificación de API-Football (`/standings`) para las fichas de la web.

Lo que fijan: se leen posición, puntos, partidos y goles; una liga con una
sola tabla no lleva grupo; la MLS (dos conferencias) sí, para no mezclar dos
"primeros"; la forma y la descripción se guardan tal cual.
"""
from __future__ import annotations

from qf.ingest.standings import parse, season_label


def _fila(rank, nombre, pts, group, j=6, g=4, e=1, p=1, gf=12, gc=5, form="WWDLW",
          desc=None):
    return {"rank": rank, "team": {"id": rank * 10, "name": nombre}, "points": pts,
            "group": group, "form": form, "description": desc,
            "all": {"played": j, "win": g, "draw": e, "lose": p,
                    "goals": {"for": gf, "against": gc}}}


def _resp(*tablas):
    return [{"league": {"id": 140, "season": 2026, "standings": list(tablas)}}]


def test_una_tabla_sin_grupo():
    filas = parse(_resp([_fila(1, "Barcelona", 16, "LaLiga", desc="Champions League"),
                         _fila(2, "Real Madrid", 13, "LaLiga")]))
    assert [(f["grupo"], f["posicion"], f["nombre"], f["puntos"]) for f in filas] == [
        ("", 1, "Barcelona", 16), ("", 2, "Real Madrid", 13)]
    f = filas[0]
    assert (f["jugados"], f["ganados"], f["empatados"], f["perdidos"]) == (6, 4, 1, 1)
    assert (f["goles_favor"], f["goles_contra"]) == (12, 5)
    assert f["forma"] == "WWDLW" and f["descripcion"] == "Champions League"


def test_la_mls_separa_conferencias():
    filas = parse(_resp([_fila(1, "Inter Miami", 50, "Eastern Conference")],
                        [_fila(1, "LA Galaxy", 48, "Western Conference")]))
    assert {(f["grupo"], f["posicion"]) for f in filas} == {
        ("Eastern Conference", 1), ("Western Conference", 1)}


def test_respuesta_vacia():
    assert parse([]) == []


def test_etiqueta_de_temporada_igual_que_el_resto():
    assert season_label(2026) == "2627"



def test_argentina_se_queda_con_la_fase_en_juego():
    from qf.ingest.standings import vigentes
    filas = parse(_resp([_fila(1, "River", 30, "Apertura - Group A")],
                        [_fila(1, "Estudiantes", 29, "Apertura - Group B")],
                        [_fila(1, "Boca", 20, "Clausura - Group A")],
                        [_fila(1, "Racing", 19, "Clausura - Group B")]))
    assert [f["grupo"] for f in vigentes(filas)] == ["Clausura - Group A",
                                                     "Clausura - Group B"]


def test_las_conferencias_no_son_fases():
    from qf.ingest.standings import vigentes
    filas = parse(_resp([_fila(1, "Inter Miami", 50, "Eastern Conference")],
                        [_fila(1, "LA Galaxy", 48, "Western Conference")]))
    assert len(vigentes(filas)) == 2


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



def test_un_id_nulo_se_completa_con_teams(monkeypatch):
    from qf.ingest import standings
    pedidos = []

    def get(endpoint, params):
        pedidos.append(endpoint)
        return [{"team": {"id": 2289, "name": "Leon"}},
                {"team": {"id": 2290, "name": "Pachuca"}}], {}

    # 'Club Leon' (clasificación) y 'Leon' (/teams) son el mismo equipo 7.
    ids = {"Club Leon": (7, None, 100.0), "Leon": (7, None, 100.0),
           "Pachuca": (8, None, 100.0)}
    monkeypatch.setattr(standings.af, "get", get)
    monkeypatch.setattr(standings, "match_team", lambda n, s, l: ids.get(n, (None, None, 0.0)))
    filas = [{"nombre": "Club Leon", "af_id": None}, {"nombre": "Pachuca", "af_id": None},
             {"nombre": "America", "af_id": 2287}]
    assert [f["af_id"] for f in standings.completar_ids(filas, 262, 2026, "mx.liga_mx")] == [
        2289, 2290, 2287]
    completas = [{"nombre": "America", "af_id": 2287}]
    assert standings.completar_ids(completas, 262, 2026, "mx.liga_mx") == completas
    assert pedidos == ["teams"]          # solo cuando falta alguno
