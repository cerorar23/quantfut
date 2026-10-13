"""
Fichas de partido de la web: forma, promedios y cara a cara.

Son funciones puras sobre filas de `matches`: lo que fijan estos tests es la
aritmética que ve el público. Un error aquí no cambia ningún pick, pero sí lo
que un visitante cree de un equipo, y la web vende credibilidad.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from qf.api import fichas

T0 = datetime(2026, 9, 20, 20, tzinfo=timezone.utc)
A, B, C = 1, 2, 3


def _p(dias, local, visita, gl, gv, **extra):
    fila = {"match_id": f"m{dias}", "kickoff_utc": T0 - timedelta(days=dias),
            "league_id": "es.laliga", "league_name": "LaLiga",
            "home_team_id": local, "away_team_id": visita,
            "home_team": {A: "Alfa", B: "Beta", C: "Gamma"}[local],
            "away_team": {A: "Alfa", B: "Beta", C: "Gamma"}[visita],
            "home_goals": gl, "away_goals": gv}
    fila.update(extra)
    return fila


# Alfa, del más reciente al más antiguo: G 2-0 (casa), E 1-1 (fuera), P 0-3 (casa)
FILAS_A = [
    _p(1, A, B, 2, 0, home_xg=1.8, away_xg=0.4, home_corners=7, away_corners=2),
    _p(8, C, A, 1, 1, home_xg=1.1, away_xg=0.9, home_corners=4, away_corners=5),
    _p(15, A, C, 0, 3, home_xg=0.7, away_xg=2.2, home_corners=3, away_corners=6),
]


def test_la_forma_se_lee_desde_el_equipo_no_desde_el_local():
    f = fichas.forma(A, FILAS_A)
    assert [p["res"] for p in f["partidos"]] == ["G", "E", "P"]
    assert [p["local"] for p in f["partidos"]] == [True, False, True]
    assert [p["rival"] for p in f["partidos"]] == ["Beta", "Gamma", "Gamma"]
    assert f["resumen"] == {"G": 1, "E": 1, "P": 1, "gf": 3, "gc": 4,
                            "puntos": 4, "racha": "GEP", "n": 3}


def test_la_forma_respeta_el_limite_de_partidos():
    assert fichas.forma(A, FILAS_A, n=2)["resumen"]["racha"] == "GE"


def test_promedios_generales_y_por_campo():
    p = fichas.promedios(A, FILAS_A)
    todos, casa, fuera = p["todos"], p["casa"], p["fuera"]
    assert todos["n"] == 3 and casa["n"] == 2 and fuera["n"] == 1
    assert todos["goles_favor"] == pytest.approx(1.0)
    assert todos["goles_contra"] == pytest.approx(4 / 3)
    assert todos["xg_favor"] == pytest.approx((1.8 + 0.9 + 0.7) / 3)
    assert casa["corners_favor"] == pytest.approx(5.0)
    assert fuera["corners_contra"] == pytest.approx(4.0)
    assert todos["pct_ambos_marcan"] == pytest.approx(100 / 3)
    assert todos["pct_mas_2_5"] == pytest.approx(100 / 3), "2-0, 1-1 y 0-3: solo el 0-3"
    assert todos["pct_porteria_cero"] == pytest.approx(100 / 3)


def test_sin_dato_de_xg_no_se_inventa_un_cero():
    p = fichas.promedios(A, [_p(1, A, B, 2, 0)])
    assert p["todos"]["xg_favor"] is None
    assert p["todos"]["goles_favor"] == 2


def test_sin_partidos_no_hay_promedios():
    assert fichas.promedios(A, [])["todos"] == {"n": 0}


def test_cara_a_cara_cuenta_por_equipo_aunque_cambie_la_localia():
    filas = [_p(3, A, B, 2, 1), _p(40, B, A, 0, 0), _p(80, B, A, 3, 1)]
    h = fichas.cara_a_cara(A, B, filas)
    r = h["resumen"]
    assert (r["victorias_local"], r["empates"], r["victorias_visitante"]) == (1, 1, 1), \
        "'local' y 'visitante' son los del partido que se analiza, no los de cada cruce"
    assert r["n"] == 3
    assert r["goles_media"] == pytest.approx(7 / 3)
    assert r["pct_ambos_marcan"] == pytest.approx(200 / 3)
    assert r["pct_mas_2_5"] == pytest.approx(200 / 3)
    assert [p["marcador"] for p in h["partidos"]] == ["2-1", "0-0", "3-1"]


def test_cara_a_cara_vacio():
    assert fichas.cara_a_cara(A, B, [])["resumen"] == {"n": 0}


def test_estadisticas_del_proveedor_se_normalizan():
    crudo = [{"team": {"id": 10}, "statistics": [
                 {"type": "Ball Possession", "value": "58%"},
                 {"type": "Yellow Cards", "value": 2},
                 {"type": "Red Cards", "value": None},
                 {"type": "Fouls", "value": 11}]},
             {"team": {"id": 20}, "statistics": [
                 {"type": "Ball Possession", "value": "42%"},
                 {"type": "Yellow Cards", "value": 4},
                 {"type": "Fouls", "value": 15}]}]
    s = fichas.normalizar_estadisticas(crudo, home_af_id=10, away_af_id=20)
    assert s["home"]["posesion"] == 58 and s["away"]["posesion"] == 42
    assert s["home"]["amarillas"] == 2 and s["home"]["rojas"] == 0
    assert s["away"]["faltas"] == 15


# --------------------------------------------------------------------------
# Endpoints (sin base: se sustituyen las consultas)
# --------------------------------------------------------------------------

def test_la_ventana_es_el_dia_local_del_visitante():
    # 27-sep 03:00 UTC es todavía el 26 en Ciudad de México (UTC-6).
    ahora = datetime(2026, 9, 27, 3, tzinfo=timezone.utc)
    inicio, fin = fichas.ventana(None, -360, 1, ahora)
    assert inicio == datetime(2026, 9, 26, 6, tzinfo=timezone.utc)
    assert fin - inicio == timedelta(days=1)
    inicio, _ = fichas.ventana("2026-09-27", 120, 1)   # Madrid, UTC+2
    assert inicio == datetime(2026, 9, 26, 22, tzinfo=timezone.utc)


def _cliente(monkeypatch, filas_query, fila_one):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    fichas._cache.clear()
    sqls = []

    def q(sql, params=()):
        sqls.append(sql)
        return filas_query(sql)

    monkeypatch.setattr(fichas, "query", q)
    monkeypatch.setattr(fichas, "query_one", lambda sql, params=(): fila_one(sql))
    app = FastAPI()
    app.include_router(fichas.router)
    return TestClient(app), sqls


def test_agenda_une_la_racha_de_cada_lado(monkeypatch):
    partido = {"match_id": "x", "kickoff_utc": T0, "status": "scheduled",
               "league_id": "es.laliga", "liga": "LaLiga", "pais": "España",
               "home_team_id": A, "away_team_id": B, "local": "Alfa",
               "visitante": "Beta", "home_goals": None, "away_goals": None,
               "pos_local": 3, "pos_visitante": None}
    rachas = [{"match_id": "x", "side": "home", "res": r} for r in "GEP"] + [
        {"match_id": "x", "side": "away", "res": "G"}]
    cliente, _ = _cliente(monkeypatch,
                          lambda sql: rachas if "s.side" in sql else [partido],
                          lambda sql: None)
    r = cliente.get("/web/partidos?fecha=2026-09-20&tz=-360")
    assert r.status_code == 200
    p = r.json()["partidos"][0]
    assert (p["local"]["racha"], p["visitante"]["racha"]) == ("GEP", "G")
    assert p["local"]["posicion"] == 3 and p["marcador"] is None


def test_fecha_mal_formada_se_rechaza(monkeypatch):
    cliente, _ = _cliente(monkeypatch, lambda sql: [], lambda sql: None)
    assert cliente.get("/web/partidos?fecha=27-09-2026").status_code == 422


def test_ficha_inexistente_da_404(monkeypatch):
    cliente, _ = _cliente(monkeypatch, lambda sql: [], lambda sql: None)
    assert cliente.get("/web/partidos/no-existe").status_code == 404


def test_la_ficha_no_lleva_cuotas_ni_picks(monkeypatch):
    """Es contenido: nada de precios, probabilidades del modelo ni picks."""
    partido = {**_p(0, A, B, None, None), "status": "scheduled", "season": "2627",
               "home_goals_ht": None, "away_goals_ht": None, "stats": None,
               "home_xg": None, "away_xg": None,
               "pais": "España", "cross_league": False}

    def filas(sql):
        if "injuries_capture_log" in sql:
            return []
        if "FROM standings" in sql or "FROM lineups" in sql:
            return []
        return FILAS_A if "OR m.away_team_id" in sql else []

    cliente, sqls = _cliente(monkeypatch, filas,
                             lambda sql: partido if "l.active" in sql else None)
    r = cliente.get("/web/partidos/m0")
    assert r.status_code == 200
    datos = r.json()
    assert datos["local"]["forma"]["resumen"]["racha"] == "GEP"
    assert datos["bajas"] is None and datos["alineaciones"] == {}
    texto = r.text.lower()
    for prohibido in ("odds", "price", "pick", "prob", "stake", "edge"):
        assert prohibido not in texto
    assert not any("odds_snapshots" in s or "picks" in s or "predictions" in s
                   for s in sqls)


def test_la_forma_no_mira_mas_alla_de_la_ventana(monkeypatch):
    """Un equipo sin temporada anterior en la base no enseña partidos de hace un año."""
    capturado = {}

    def q(sql, params=()):
        capturado["sql"], capturado["params"] = sql, params
        return []

    monkeypatch.setattr(fichas, "query", q)
    fichas._ultimos(A, T0, 10)
    assert capturado["params"][3] == T0 - timedelta(days=fichas.VENTANA_FORMA_DIAS)
    assert "m.kickoff_utc > %s" in capturado["sql"]


def test_el_escudo_solo_se_anuncia_si_existe(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from dataclasses import replace
    monkeypatch.setattr(fichas, "settings", replace(fichas.settings, escudos_dir=str(tmp_path)))
    (tmp_path / "7.png").write_bytes(b"\x89PNG\r\n\x1a\nresto")
    assert fichas.escudo(7) == "/web/escudos/7.png"
    assert fichas.escudo(8) is None
    app = FastAPI()
    app.include_router(fichas.router)
    cliente = TestClient(app)
    r = cliente.get("/web/escudos/7.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert "max-age" in r.headers["cache-control"]
    assert cliente.get("/web/escudos/8.png").status_code == 404
    assert cliente.get("/web/escudos/..%2F..%2Fetc.png").status_code in (404, 422)


def test_ultimo_once_se_formatea_sin_inventar():
    from datetime import datetime, timezone
    from qf.api import fichas

    fila = {"match_id": "m1", "kickoff_utc": datetime(2026, 10, 9, tzinfo=timezone.utc),
            "competicion": "Ligue 1", "rival": "Lyon", "formation": "3-4-2-1",
            "starters": [{"name": "Risser", "pos": "G", "number": 1, "player_id": 9},
                         {"name": "Gradit", "pos": "D", "number": 24},
                         {"pos": "M", "number": 8}]}  # sin nombre: se descarta
    once = fichas._formatear_once(fila)
    assert once["formacion"] == "3-4-2-1" and once["rival"] == "Lyon"
    assert [j["nombre"] for j in once["titulares"]] == ["Risser", "Gradit"]
    assert "player_id" not in once["titulares"][0]
    assert fichas._formatear_once(None) is None
    assert fichas._formatear_once({**fila, "starters": []}) is None
    assert fichas._formatear_once({**fila, "starters": [{"pos": "M"}]}) is None
