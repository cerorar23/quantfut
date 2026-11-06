from datetime import date, datetime, timedelta, timezone

import pytest

from qf.publish import parley_nba as nba
from qf.publish import parley_nba_revisor as rv
from qf.publish import parley_v2 as v2
from qf.publish import parley_v2_datos as base
from qf.publish.alta_prob import Candidato
from qf.publish.parley_ext import OpcionExterna

INICIO = datetime(2026, 11, 7, 1, 0, tzinfo=timezone.utc)
AHORA = INICIO - timedelta(minutes=55)


def cartelera(*juegos):
    return {"partidos": [{"id": i, "local": {"nombre": l}, "visitante": {"nombre": v}, "inicio_utc": ini.isoformat(),
                          "pronostico": {"sellado_en": sello.isoformat()} if sello else None} for i, l, v, ini, sello in juegos]}


def evento_pl(eid, local, visita, inicio):
    return {"id": eid, "home_team": local, "away_team": visita, "commence_time": inicio.isoformat()}


def ops_de(evento_id, n=3, precios=(1.45, 1.5, 1.6)):
    return [OpcionExterna(match_id=f"nba:{evento_id}", cand=Candidato("h2h" if i == 0 else "totals", "home" if i == 0 else "over",
            None if i == 0 else 200.5 + i, .7), price=precios[i], book="b", odds_source="t", odds_as_of=AHORA, deporte="nba",
            evento=(evento_id, "basketball_nba", INICIO, "L", "V")) for i in range(n)]


def test_empareja_por_equipos_y_hora_y_solo_si_es_unico():
    j = rv.juegos_de_cartelera(cartelera((1, "Atlanta Hawks", "Washington Wizards", INICIO, None)))
    ok = rv.emparejar(j, [evento_pl("p1", "Atlanta Hawks", "Washington Wizards", INICIO + timedelta(minutes=5))])
    assert ok == {1: "p1"}
    assert rv.emparejar(j, [evento_pl("p1", "Atlanta Hawks", "Washington Wizards", INICIO + timedelta(hours=3))]) == {}
    dup = [evento_pl("a", "Atlanta Hawks", "Washington Wizards", INICIO), evento_pl("b", "Atlanta Hawks", "Washington Wizards", INICIO)]
    assert rv.emparejar(j, dup) == {}


def test_elegible_solo_con_sello_y_dentro_de_ventana():
    sello = INICIO - timedelta(hours=3)
    j = rv.juegos_de_cartelera(cartelera((1, "A", "B", INICIO, sello), (2, "C", "D", INICIO, None), (3, "E", "F", INICIO + timedelta(hours=5), sello)))
    assert [x.id for x in rv.elegibles(AHORA, j)] == [1]


def test_multipartido_toca_con_tres_o_en_el_ultimo_momento():
    mk = lambda i, ini: rv.Juego(i, "L", "V", ini, INICIO - timedelta(hours=3))
    assert not rv.toca_multipartido(AHORA, [mk(1, INICIO)])
    assert not rv.toca_multipartido(AHORA, [mk(1, INICIO), mk(2, INICIO)])
    assert rv.toca_multipartido(AHORA, [mk(1, INICIO), mk(2, INICIO), mk(3, INICIO)])
    assert rv.toca_multipartido(INICIO - timedelta(minutes=31), [mk(1, INICIO), mk(2, INICIO)])


@pytest.fixture
def entorno(monkeypatch):
    guardados = []
    monkeypatch.setenv("PARLEY_V2_ENABLED", "1")
    monkeypatch.setattr(base, "_existe", lambda clave: False)
    monkeypatch.setattr(base, "_prev", lambda: "0" * 64)
    monkeypatch.setattr(base, "_guardar", lambda lote: guardados.append(lote) or True)
    return guardados


def contexto(now, ev):
    return nba.Contexto(inicio=INICIO, estado_jugadores={}, cuotas={v2._clave(o): o.price for o in ops_de(ev)})


def test_revisa_sella_por_partido_y_un_multipartido_por_dia(entorno):
    sello = INICIO - timedelta(hours=3)
    juegos = [(i, f"L{i}", f"V{i}", INICIO, sello) for i in (1, 2, 3)]
    r = rv.revisar(AHORA, lambda d: cartelera(*juegos) if d == AHORA.date() else {"partidos": []},
                   lambda: [evento_pl(f"p{i}", f"L{i}", f"V{i}", INICIO) for i in (1, 2, 3)],
                   lambda n, ids: [o for e in ids for o in ops_de(e)], contexto)
    assert r["elegibles"] == [1, 2, 3] and [p["estado"] for p in r["partidos"]] == ["elegido"] * 3
    assert r["multi"]["estado"] == "elegido" and r["multi"]["partidos"] == 3
    claves = [l["clave"] for l in entorno]
    assert "parley_objetivo|v2.1|nba_dia|2026-11-07" in claves and len(claves) == 4
    multi = next(l for l in entorno if l["ambito"] == "nba_dia")
    legs = [p for t in multi["payload"]["tickets"] for p in t["patas"]]
    assert len({p["evento_id"] for p in legs}) >= 2


def test_sin_sello_no_hay_parley_y_la_revalidacion_saca_patas_malas(entorno):
    r = rv.revisar(AHORA, lambda d: cartelera((1, "L1", "V1", INICIO, None)), lambda: [evento_pl("p1", "L1", "V1", INICIO)],
                   lambda n, ids: [], contexto)
    assert r["elegibles"] == [] and r["multi"] is None and not entorno
    sello = INICIO - timedelta(hours=3)
    malo = lambda now, ev: nba.Contexto(inicio=INICIO + timedelta(minutes=30), estado_jugadores={}, cuotas={})
    m = rv.ejecutar_multipartido(AHORA, date(2026, 11, 7), ["p1", "p2"], lambda n, ids: [o for e in ids for o in ops_de(e)], malo)
    assert m["estado"] in ("abstencion",) and not entorno
