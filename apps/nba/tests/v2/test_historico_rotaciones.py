from nba.v2.fuentes.historico_rotaciones import fin_periodo, quintetos


def _tramo(periodo, equipo, ini, fin, jugadores):
    return {"period": periodo, "team_id": equipo, "start_elapsed_seconds": ini, "end_elapsed_seconds": fin,
            "nba_player_ids": jugadores}


def test_fin_de_periodo_con_prorroga():
    assert [fin_periodo(p) for p in (1, 4, 5, 6)] == [720, 2880, 3180, 3480]


def test_un_instante_por_cambio_con_los_dos_quintetos():
    juego = {"chronological_lineups": [
        _tramo(1, 1, 0, 300, [5, 4, 3, 2, 1]), _tramo(1, 1, 300, 720, [6, 4, 3, 2, 1]),
        _tramo(1, 2, 0, 720, [15, 14, 13, 12, 11]), _tramo(2, 1, 720, 1440, [6, 4, 3, 2, 1])]}
    filas = list(quintetos(juego, 1, 2))
    assert filas[0] == (1, 720, [1, 2, 3, 4, 5], [11, 12, 13, 14, 15])
    assert filas[1] == (1, 420, [1, 2, 3, 4, 6], [11, 12, 13, 14, 15])
    assert len(filas) == 2  # periodo 2: el visitante no tiene tramo, se omite
