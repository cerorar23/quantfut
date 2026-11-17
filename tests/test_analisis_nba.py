"""Casillas por receta y bloque `analisis` del destacado de NBA (sin red ni base)."""
import pytest

from qf.api import analisis_nba as an


@pytest.fixture(autouse=True)
def _sin_ia_ni_base(monkeypatch):
    """Por defecto el resumen ni toca la base ni llama a la IA; la prueba que lo necesita lo sustituye."""
    monkeypatch.setattr(an.ia, "resumen_para", lambda *a: None)

EVENTO = {"id": 18712, "local": {"codigo": "CLE", "nombre": "Cleveland Cavaliers"},
          "visitante": {"codigo": "CHI", "nombre": "Chicago Bulls"},
          "pronostico": {"p_local": 0.75, "mu": [121.9, 112.4],
                         "escenarios": {"descanso_dias": {"local": 2, "visitante": 1}, "posesiones_regulacion": 101.28}}}


def equipo(nombre, pf=117.5, pc=115.9, games=14, won=4, lost=2):
    return {"name": nombre, "scoring": {"games": games, "points_for": pf, "points_against": pc},
            "last6": {"won": won, "lost": lost, "games": 6}}


EST = {"teams": [equipo("Cleveland Cavaliers"), equipo("Chicago Bulls", 110.6, 118.0, 14, 3, 3)],
       "h2h": {"home_wins": 3, "away_wins": 2, "average_total": 226.8, "matches": [{}, {}, {}, {}]}}
DIS = {"estado": "reporte_aplicado",
       "local": {"jugadores": [{"estado": "Out"}, {"estado": "Available"}, {"estado": "Out"}]},
       "visitante": {"jugadores": [{"estado": "Out"}]}}


def mercado(market, **kw):
    base = {"id": f"{market}-x", "market": market, "side": "over", "team": None, "line": 230.5, "probability": 0.62}
    base.update(kw)
    return base


def ids(out):
    return [c["id"] for c in out["casillas"]]


def test_ganador_usa_margen_forma_y_diferencial():
    out = an.construir(EVENTO, mercado("winner", team="Cleveland Cavaliers", line=None), EST, DIS)
    assert out["receta"] == "ganador" and ids(out) == ["proy_margen", "forma", "dif"]
    assert out["casillas"][0]["margen"] == 9.5 and out["casillas"][1]["a_w"] == 4
    assert out["casillas"][2]["a"] == 1.6 and out["casillas"][2]["b"] == -7.4


def test_total_usa_total_proyectado_ritmo_y_cara_a_cara():
    out = an.construir(EVENTO, mercado("game_total"), EST, DIS)
    assert out["receta"] == "total" and ids(out) == ["proy_total", "ritmo", "h2h_total"]
    assert out["casillas"][0]["total"] == 234.3 and out["casillas"][0]["linea"] == 230.5
    assert out["casillas"][1]["pos"] == 101.3 and out["casillas"][2] == {"id": "h2h_total", "avg": 226.8, "n": 4}


def test_equipo_toma_los_puntos_del_equipo_del_mercado():
    out = an.construir(EVENTO, mercado("team_points", team="Chicago Bulls", line=112.5, side="under"), EST, DIS)
    assert out["receta"] == "equipo" and ids(out)[:2] == ["proy_equipo", "ataque_defensa"]
    assert out["casillas"][0] == {"id": "proy_equipo", "a": 112.4, "equipo": "b", "linea": 112.5}
    assert out["casillas"][1] == {"id": "ataque_defensa", "a": 110.6, "b": 115.9, "equipo": "b"}


def test_sin_estadisticas_sube_lo_que_si_hay_y_no_deja_huecos():
    out = an.construir(EVENTO, mercado("game_total"), None, DIS)
    assert ids(out) == ["proy_total", "ritmo", "descanso"]
    assert out["casillas"][2] == {"id": "descanso", "a": 2, "b": 1}
    out = an.construir(EVENTO, mercado("winner", team="Cleveland Cavaliers", line=None), None, DIS)
    assert ids(out) == ["proy_margen", "descanso", "bajas"]
    assert out["casillas"][2] == {"id": "bajas", "a": 2, "b": 1}


def test_bajas_solo_con_el_reporte_aplicado():
    sin = {**DIS, "estado": "esperando"}
    assert "bajas" not in ids(an.construir(EVENTO, mercado("winner", team="Cleveland Cavaliers", line=None), None, sin))


def test_pocos_partidos_no_dan_promedios():
    est = {"teams": [equipo("Cleveland Cavaliers", games=3), equipo("Chicago Bulls", games=3)], "h2h": {}}
    assert "dif" not in ids(an.construir(EVENTO, mercado("winner", team="Cleveland Cavaliers", line=None), est, None))


def test_sin_sello_o_sin_receta_no_hay_analisis():
    assert an.construir({**EVENTO, "pronostico": None}, mercado("game_total"), EST, DIS) is None
    assert an.construir(EVENTO, mercado("player_points"), EST, DIS) is None


def test_significado_sin_ambiguedad():
    assert an.significado(mercado("winner", team="Cleveland Cavaliers", line=None)) == "Cleveland Cavaliers wins the game"
    assert an.significado(mercado("game_total", side="under")) == "Fewer than 230.5 total points in the game"
    assert an.significado(mercado("team_points", team="Chicago Bulls", line=112.5)) == "Chicago Bulls scores more than 112.5 points"
    assert "+9.5" in an.significado(mercado("handicap", team="Chicago Bulls", line=9.5))
    assert an.significado(mercado("player_points", team="X")) is None


def test_el_resumen_se_pide_con_los_hechos_y_el_deporte(monkeypatch):
    pedidos = []
    monkeypatch.setattr(an.ia, "resumen_para", lambda *a: pedidos.append(a) or {"es": "texto"})
    out = an.construir(EVENTO, mercado("game_total"), EST, DIS)
    assert out["resumen"] == {"es": "texto"}
    hechos = pedidos[0][2]
    assert hechos["significado"] == "More than 230.5 total points in the game" and hechos["probabilidad_pct"] == 62
    assert pedidos[0][3] == "basketball (NBA)" and pedidos[0][1] == "nba|game_total-x"
    assert an.ia.cifras_validas("Se proyectan 234,3 puntos, con línea de 230,5 y 62 % de probabilidad.", hechos)
    assert not an.ia.cifras_validas("Se proyectan 250 puntos.", hechos)


def test_para_partido_busca_el_evento_y_usa_el_destacado(monkeypatch):
    from datetime import date
    monkeypatch.setattr(an.nba_datos, "hoy_et", lambda: date(2026, 11, 16))
    monkeypatch.setattr(an.nba_datos, "cartelera_ventana", lambda d, h: {date(2026, 11, 16): [EVENTO]})
    monkeypatch.setattr(an.nba_datos, "mercados", lambda pid, f: {"destacado": mercado("game_total")})
    monkeypatch.setattr(an.nba_datos, "estadisticas", lambda pid, f: EST)
    monkeypatch.setattr(an.nba_datos, "disponibilidad", lambda pid: DIS)
    monkeypatch.setattr(an.ia, "resumen_para", lambda *a: None)
    out = an.para_partido("18712")
    assert out["mercado_id"] == "game_total-x" and out["receta"] == "total"
    assert an.para_partido("999") is None
    monkeypatch.setattr(an.nba_datos, "mercados", lambda pid, f: {"destacado": None})
    assert an.para_partido("18712") is None
    monkeypatch.setattr(an.nba_datos, "cartelera_ventana", lambda d, h: (_ for _ in ()).throw(an.nba_datos.NbaNoDisponible("x")))
    assert an.para_partido("18712") is None


def test_ruta_del_analisis_devuelve_404_sin_datos_y_200_con_ellos(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from qf.api import web
    app = FastAPI()
    app.include_router(web.router)
    cliente = TestClient(app)
    monkeypatch.setattr(an, "para_partido", lambda pid: {"receta": "total", "casillas": [{"id": "ritmo"}],
                                                         "resumen": None, "mercado_id": "m"} if pid == "18712" else None)
    ok = cliente.get("/web/deportes/nba/analisis/18712")
    assert ok.status_code == 200 and ok.json()["mercado_id"] == "m" and ok.headers["cache-control"] == "no-store"
    assert cliente.get("/web/deportes/nba/analisis/999").status_code == 404           # sin análisis
    assert cliente.get("/web/deportes/nba/analisis/abc").status_code == 404           # id no numérico
    assert cliente.get("/web/deportes/nba/analisis/1234567890").status_code == 404    # demasiado largo
