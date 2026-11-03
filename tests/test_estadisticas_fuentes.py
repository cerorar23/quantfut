"""`matches.stats` con las claves de la web desde SofaScore y FotMob (sustitutos de API-Football)."""
from qf.ingest.estadisticas import desde_fotmob, desde_sofascore


def _item(key, h, a, **kw):
    return dict(key=key, homeValue=h, awayValue=a, **kw)


def test_sofascore_partido_completo_con_centros_y_tarjetas_a_cero():
    stats = [dict(period="ALL", groups=[
                 dict(statisticsItems=[_item("fouls", 17, 13), _item("passes", 339, 387),
                                       _item("accuratePasses", 229, 279), _item("goalkeeperSaves", 3, 4),
                                       _item("accurateCross", 8, 3, homeTotal=29, awayTotal=21)]),
                 dict(statisticsItems=[_item("goalkeeperSaves", 3, 4)])]),
             dict(period="1ST", groups=[dict(statisticsItems=[_item("fouls", 9, 5)])])]
    s = desde_sofascore(stats)
    assert s["home"]["faltas"] == 17 and s["away"]["faltas"] == 13       # el 1.er tiempo no pisa el total
    assert s["home"]["centros"] == 29 and s["home"]["centros_precisos"] == 8
    assert s["home"]["paradas"] == 3 and s["home"]["pct_pases"] == 68
    assert s["home"]["amarillas"] == 0 and s["away"]["rojas"] == 0


def test_sofascore_repeticion_discrepante_se_descarta_y_vacio_es_none():
    stats = [dict(period="ALL", groups=[dict(statisticsItems=[_item("fouls", 17, 13), _item("fouls", 18, 13)])])]
    assert desde_sofascore(stats) is None
    assert desde_sofascore([]) is None


def test_fotmob_mismas_claves():
    s = desde_fotmob({"fouls": [10.0, 12.0], "corners": [6.0, 3.0], "expected_goals": [1.87, 0.36],
                      "accurate_crosses": [7.0, 2.0], "shots": [None, None], "yellow_cards": [2.0, 0.0]})
    assert s["home"] == {"faltas": 10, "corners": 6, "xg": 1.87, "centros_precisos": 7, "amarillas": 2, "rojas": 0}
    assert desde_fotmob({"shots": [None, None]}) is None
