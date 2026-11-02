from datetime import date

import pytest

from nba.v2 import equipos, identidad


def canonica(db, entidad_id):
    return db.execute("SELECT canonica_id FROM nba.entidad WHERE entidad_id = %s", (entidad_id,)).fetchone()[0]


def test_treinta_equipos_y_canonico_de_alias():
    assert len(equipos.TRICODES) == 30
    for espn, oficial in {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}.items():
        assert equipos.canonico("espn", espn) == oficial
    assert equipos.canonico("espn", "BOS") == "BOS" and equipos.canonico("rotowire", "GSW") == "GSW"
    with pytest.raises(KeyError):
        equipos.canonico("espn", "XXX")


def test_equipo_es_idempotente(base_migrada):
    a = identidad.equipo(base_migrada, "BOS")
    assert identidad.equipo(base_migrada, "BOS") == a
    assert base_migrada.execute("SELECT nombre FROM nba.entidad WHERE entidad_id = %s", (a,)).fetchone()[0] == \
        "Boston Celtics"


def test_jugador_alias_por_nombre_normalizado(base_migrada):
    db = base_migrada
    a = identidad.jugador(db, "espn", "3112335", "Nikola Jokić")
    b = identidad.jugador(db, "rotowire", "4387", "Nikola Jokic")
    c = identidad.jugador(db, "nba_oficial", "203999", "Nikola Jokic Jr.")
    assert a == b == c
    assert identidad.jugador(db, "rotowire", "4387", "otro nombre") == a
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE canonica_id = %s", (a,)).fetchone()[0] == 3


def test_nombre_ambiguo_no_se_fusiona(base_migrada):
    db = base_migrada
    a = identidad.jugador(db, "espn", "1", "John Smith")
    b = identidad.jugador(db, "espn", "2", "John Smith")           # otro id de la misma fuente: otra persona
    c = identidad.jugador(db, "rotowire", "9", "John Smith")       # dos candidatos: no se fusiona
    assert len({a, b, c}) == 3
    ambiguo = db.execute("SELECT atributos->>'ambiguo' FROM nba.entidad WHERE entidad_id = %s", (c,)).fetchone()[0]
    assert ambiguo == "true"


def test_dos_jugadores_mismo_nombre_distinto_id_misma_fuente_no_se_fusionan(base_migrada):
    db = base_migrada
    assert identidad.jugador(db, "espn", "10", "Jalen Williams") != identidad.jugador(db, "espn", "11", "Jalen Williams")


def test_partido_de_otra_fuente_es_alias(base_migrada):
    db = base_migrada
    loc, vis = identidad.equipo(db, "CLE"), identidad.equipo(db, "OKC")
    p1 = identidad.partido(db, "espn", "401909907", date(2026, 11, 2), loc, vis, "2026-27")
    p2 = identidad.partido(db, "nba_oficial", "0022600123", date(2026, 11, 2), loc, vis, "2026-27")
    assert p1 == p2 == canonica(db, p2)
    assert identidad.partido(db, "espn", "401909907", date(2026, 11, 2), loc, vis, "2026-27") == p1


def test_partido_de_otra_fecha_no_es_alias(base_migrada):
    db = base_migrada
    loc, vis = identidad.equipo(db, "CLE"), identidad.equipo(db, "OKC")
    p1 = identidad.partido(db, "espn", "1", date(2026, 11, 2), loc, vis, "2026-27")
    p2 = identidad.partido(db, "nba_oficial", "2", date(2026, 11, 4), loc, vis, "2026-27")
    assert p1 != p2


def test_temporada_de_una_fecha():
    assert identidad.temporada(date(2026, 11, 2)) == "2026-27"
    assert identidad.temporada(date(2027, 4, 12)) == "2026-27"
    assert identidad.temporada(date(2099, 10, 1)) == "2099-00"
