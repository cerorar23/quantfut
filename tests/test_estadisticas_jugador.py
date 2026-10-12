"""
Estadísticas por jugador (db/035, fuerza por jugador Fase A).

Lo que fijan: el lado se asigna por el id de equipo de API-Football, no por
el orden; los suplentes que no jugaron no se guardan; los recuentos nulos son
0 y la nota del proveedor, que llega como texto, se convierte a número.
"""
from __future__ import annotations

from qf.ingest.estadisticas_jugador import parse_jugadores


def _jugador(pid, minutos, pos="M", suplente=False, rating="7.1", **stats):
    s = {"games": {"minutes": minutos, "position": pos, "rating": rating,
                   "substitute": suplente},
         "shots": {"total": stats.get("tiros"), "on": stats.get("puerta")},
         "goals": {"total": stats.get("goles"), "assists": stats.get("asist"),
                   "saves": stats.get("paradas")},
         "passes": {"key": stats.get("clave")},
         "tackles": {"total": stats.get("entradas"), "interceptions": None},
         "duels": {"won": stats.get("duelos")},
         "dribbles": {"success": None}}
    return {"player": {"id": pid, "name": f"J{pid}"}, "statistics": [s]}


def _resp(primero_visitante=False):
    local = {"team": {"id": 538}, "players": [
        _jugador(1, 90, "F", tiros=4, puerta=2, goles=1, clave=1),
        _jugador(2, 25, "M", suplente=True, rating=None),
        _jugador(3, None, "D", suplente=True, rating=None)]}
    visita = {"team": {"id": 542}, "players": [_jugador(9, 90, "G", paradas=3)]}
    return [visita, local] if primero_visitante else [local, visita]


def test_el_lado_sale_del_id_de_equipo_no_del_orden():
    filas = parse_jugadores(_resp(primero_visitante=True), 538, 542)
    assert {f["player_id"]: f["side"] for f in filas} == {1: "home", 2: "home", 9: "away"}


def test_suplente_sin_minutos_no_se_guarda_y_nulos_son_cero():
    filas = {f["player_id"]: f for f in parse_jugadores(_resp(), 538, 542)}
    assert 3 not in filas
    delantero = filas[1]
    assert (delantero["tiros"], delantero["tiros_puerta"], delantero["goles"],
            delantero["pases_clave"], delantero["asistencias"]) == (4, 2, 1, 1, 0)
    assert delantero["titular"] is True and delantero["nota_proveedor"] == 7.1
    assert filas[2]["titular"] is False and filas[2]["nota_proveedor"] is None
    assert filas[9]["paradas"] == 3 and filas[9]["posicion"] == "G"


def test_sin_ids_de_equipo_usa_el_orden_del_proveedor():
    filas = parse_jugadores(_resp(), None, None)
    assert {f["player_id"]: f["side"] for f in filas}[9] == "away"


def test_respuesta_vacia():
    assert parse_jugadores([], 538, 542) == []


def test_capturar_guarda_filas_y_registra_el_intento(monkeypatch):
    from qf.ingest import estadisticas_jugador as ej
    llamadas, sqls = [], []
    monkeypatch.setattr(ej.af, "get", lambda ep, p: (llamadas.append((ep, p)) or
                                                      (_resp(), {"quota_remaining": "5000"})))
    monkeypatch.setattr(ej, "executemany", lambda sql, filas: sqls.append(("many", len(filas))))
    monkeypatch.setattr(ej, "execute", lambda sql, params: sqls.append(("log", params)))
    n, meta = ej.capturar("m1", 777, 538, 542)
    assert llamadas == [("fixtures/players", {"fixture": 777})]
    assert n == 3 and ("many", 3) in sqls and ("log", ("m1", 3)) in sqls


def test_sin_datos_se_registra_para_no_repetir(monkeypatch):
    from qf.ingest import estadisticas_jugador as ej
    sqls = []
    monkeypatch.setattr(ej.af, "get", lambda ep, p: ([], {"quota_remaining": "5000"}))
    monkeypatch.setattr(ej, "executemany", lambda sql, filas: sqls.append("many"))
    monkeypatch.setattr(ej, "execute", lambda sql, params: sqls.append(params))
    assert ej.capturar("m1", 777, 538, 542)[0] == 0
    assert sqls == [("m1", 0)]


def test_el_historico_para_en_la_reserva(monkeypatch):
    from qf.ingest import estadisticas_jugador as ej
    pendientes = [{"match_id": f"m{i}", "af_fixture_id": i, "home_af": 538,
                   "away_af": 542} for i in range(5)]
    monkeypatch.setattr(ej, "query", lambda sql, params=(): pendientes)
    hechos = []

    def capturar(match_id, fixture, h, a):
        hechos.append(match_id)
        return 20, {"quota_remaining": "2400" if match_id == "m1" else "3000"}
    monkeypatch.setattr(ej, "capturar", capturar)
    monkeypatch.setattr(ej.af, "record_health", lambda *a, **k: None)
    r = ej.run_historico(reserva=2500)
    assert hechos == ["m0", "m1"] and r["partidos"] == 2 and r["pendientes"] == 5


def test_al_cerrar_se_capturan_solo_ligas_con_modelo(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from qf.ingest import results
    ko = datetime.now(timezone.utc) - timedelta(hours=3)
    pendientes = [
        {"match_id": "con", "league_id": "es.laliga", "kickoff_utc": ko, "af_id": "10",
         "captura_jugadores": True, "home_af": 538, "away_af": 542},
        {"match_id": "sin", "league_id": "cl.primera", "kickoff_utc": ko, "af_id": "11",
         "captura_jugadores": False, "home_af": 1, "away_af": 2}]

    def fx(fid):
        return {"fixture": {"id": fid, "status": {"short": "FT"}},
                "goals": {"home": 1, "away": 0}, "score": {"halftime": {}},
                "teams": {"home": {"id": 538}, "away": {"id": 542}}}

    monkeypatch.setattr(results, "query", lambda sql, params=(): pendientes)
    monkeypatch.setattr(results, "execute", lambda sql, params=(): 1)
    monkeypatch.setattr(results.af, "get", lambda ep, p: ([fx(10), fx(11)], {})
                        if ep == "fixtures" else ([], {}))
    monkeypatch.setattr(results.af, "check_quota", lambda meta: None)
    monkeypatch.setattr(results.af, "record_health", lambda *a, **k: None)
    capturados = []
    monkeypatch.setattr(results, "capturar_jugadores",
                        lambda m, f, h, a: capturados.append((m, f, h, a)) or (11, {}))
    import qf.eval.clv as clv
    monkeypatch.setattr(clv, "settle_pending", lambda: {})
    r = results.close_recent(with_stats=False)
    assert capturados == [("con", 10, 538, 542)]
    assert r["closed"] == 2 and r["jugadores"] == 1
