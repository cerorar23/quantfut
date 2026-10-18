from qf.ingest.calendario_equipos import filas_de


def _item(fid, local_id, visita_id, liga=45, season=2025, estado="FT", gl=2, gv=1, fecha="2025-08-30T14:00:00+00:00"):
    return {"fixture": {"id": fid, "date": fecha, "status": {"short": estado}},
            "league": {"id": liga, "name": "FA Cup", "country": "England", "season": season, "round": "Round 3"},
            "teams": {"home": {"id": local_id, "name": "A"}, "away": {"id": visita_id, "name": "B"}},
            "goals": {"home": gl, "away": gv}}


def test_orienta_goles_y_rival_segun_el_lado():
    local = filas_de([_item(1, 42, 489)], 42, 3)[0]
    assert (local["local"], local["rival_af_id"], local["goles_favor"], local["goles_contra"]) == (True, 489, 2, 1)
    visita = filas_de([_item(1, 489, 42)], 42, 3)[0]
    assert (visita["local"], visita["rival_af_id"], visita["goles_favor"], visita["goles_contra"]) == (False, 489, 1, 2)
    assert local["team_id"] == 3 and local["liga_nombre"] == "FA Cup" and local["ronda"] == "Round 3"


def test_partido_sin_jugar_deja_el_marcador_en_none_no_en_cero():
    f = filas_de([_item(2, 42, 489, estado="NS", gl=None, gv=None)], 42, 3)[0]
    assert f["goles_favor"] is None and f["goles_contra"] is None and f["estado"] == "NS"


def test_ignora_registros_invalidos_o_de_otros_equipos():
    malos = [_item(3, 10, 11), _item(4, 42, 489, fecha="no es fecha"), _item(5, 42, 489, fecha="2025-08-30T14:00:00"),
             _item(6, 42, 489, season=None)]
    assert filas_de(malos, 42, 3) == []
    assert len(filas_de([_item(7, 42, 489), _item(8, 489, 42)], 42, None)) == 2
