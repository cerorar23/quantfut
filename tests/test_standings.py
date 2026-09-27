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
