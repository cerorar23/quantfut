"""Casillas por receta, perfiles de saque/resto y bloque `analisis` del destacado de tenis (sin base ni red)."""
from qf.api import analisis_tenis as at


def fila(lado=1, ganador=1, sup="hard", js=10, bpa=4, bps=2, o_js=10, o_bpa=6, o_bps=3, sets=None, mejor_de=3):
    return {"partido_id": 1, "mejor_de": mejor_de, "superficie": sup, "lunes_semana": None, "lado": lado,
            "ganador": ganador, "sets": sets if sets is not None else [[6, 4, None, None], [6, 3, None, None]],
            "juegos_saque": js, "bp_afrontados": bpa, "bp_salvados": bps,
            "o_js": o_js, "o_bpa": o_bpa, "o_bps": o_bps}


def test_hold_y_break_salen_de_los_puntos_de_quiebre_no_salvados():
    # cede 2 de 10 juegos de saque (hold 80 %) y rompe 3 de 10 del rival (break 30 %)
    perfil = at.perfil_de_filas([fila() for _ in range(20)], "hard")
    assert round(perfil["hold"]) == 80 and round(perfil["brk"]) == 30
    assert perfil["n_saque"] == 20 and perfil["n_s"] == 20 and perfil["victorias_s"] == 20


def test_sin_estadistica_de_saque_no_hay_hold():
    perfil = at.perfil_de_filas([fila(js=None, bpa=None, bps=None, o_js=None, o_bpa=None, o_bps=None)] * 20, "hard")
    assert perfil["hold"] is None and perfil["brk"] is None and perfil["n_saque"] == 0


def test_tres_sets_solo_cuenta_partidos_al_mejor_de_tres():
    tres = [[6, 4, None, None], [3, 6, None, None], [7, 5, None, None]]
    filas = [fila(sets=tres)] * 4 + [fila()] * 6 + [fila(mejor_de=5, sets=tres)] * 3
    perfil = at.perfil_de_filas(filas, None)
    assert perfil["n_bo3"] == 10 and perfil["tres"] == 4


def ctx(**kw):
    filas = [fila() for _ in range(20)]
    base = {"pa": at.perfil_de_filas(filas, "hard"), "pb": at.perfil_de_filas(filas, "hard"), "superficie": "hard",
            "rank_a": 1, "rank_b": 3, "h2h": (6, 4)}
    base.update(kw)
    return base


def test_ganador_prioriza_saque_ranking_y_cara_a_cara():
    tarjetas = at.casillas("ganador", ctx())
    assert [c["id"] for c in tarjetas] == ["saque", "rank", "h2h"]
    assert tarjetas[0]["sup"] == "hard" and tarjetas[0]["a"] == 80


def test_duracion_usa_tres_sets_y_salta_lo_que_no_tiene_dato():
    tres = [[6, 4, None, None], [3, 6, None, None], [7, 5, None, None]]
    filas = [fila(sets=tres)] * 3 + [fila()] * 9
    c = ctx(pa=at.perfil_de_filas(filas, "hard"), pb=at.perfil_de_filas(filas, "hard"))
    assert [t["id"] for t in at.casillas("duracion", c)][:2] == ["saque", "tres_sets"]
    sin_bo3 = ctx(pa=at.perfil_de_filas([fila(mejor_de=5)] * 20, "hard"))
    assert "tres_sets" not in [t["id"] for t in at.casillas("duracion", sin_bo3)]


def test_pocos_partidos_en_la_superficie_usa_todas_las_superficies():
    filas = [fila(sup="clay") for _ in range(20)] + [fila() for _ in range(3)]
    c = ctx(pa=at.perfil_de_filas(filas, "hard"), pb=at.perfil_de_filas(filas, "hard"))
    assert at.casillas("ganador", c)[0]["sup"] == "todas"


def test_h2h_con_un_solo_cruce_no_se_muestra():
    assert "h2h" not in [c["id"] for c in at.casillas("ganador", ctx(h2h=(1, 0)))]


def test_receta_y_circuito():
    assert at.receta_de("winner") == at.receta_de("games_handicap") == "ganador"
    assert at.receta_de("games_total") == at.receta_de("tiebreak") == "duracion"
    assert at.circuito_de("ATP · Stockholm") == "atp" and at.circuito_de("WTA 500 · Linz") == "wta"
    assert at.circuito_de("Challenger") is None and at.superficie_de("Hard") == "hard" and at.superficie_de("Carpet") is None


def test_significado_sin_ambiguedad():
    assert at.significado("winner", "Alex Michelsen") == "Alex Michelsen wins the match"
    assert at.significado("games_total", "Más de 22.5") == "More than 22.5 total games in the match"
    assert at.significado("sets_total", "Menos de 2.5") == "Fewer than 2.5 total sets in the match"
    assert at.significado("tiebreak", "Sí") == "At least one tie-break is played"
    assert "-5.5" in at.significado("games_handicap", "Alex Michelsen -5.5")
    assert at.significado("set_winner", "algo") is None


def test_construir_no_adivina_jugadores_ambiguos_ni_sin_circuito(monkeypatch):
    mercado = {"id": "winner", "label": "Ganador del partido", "selection": "A", "probability": 0.7}
    assert at.construir("1", "A", "B", "Challenger", "Hard", mercado) is None
    monkeypatch.setattr(at, "jugador_id", lambda n, c: None if n == "A" else 7)
    assert at.construir("1", "A", "B", "ATP · X", "Hard", mercado) is None


def test_construir_completo_y_resumen_pedido_una_vez(monkeypatch):
    pedidos = []
    monkeypatch.setattr(at, "jugador_id", lambda n, c: 1 if n == "A" else 2)
    monkeypatch.setattr(at, "_perfil", lambda j, s: at.perfil_de_filas([fila() for _ in range(20)], s))
    monkeypatch.setattr(at, "_ranking_pareja", lambda a, b, c: (1, 3))
    monkeypatch.setattr(at, "_h2h", lambda a, b: (6, 4))
    monkeypatch.setattr(at.ia, "resumen_para", lambda *a: pedidos.append(a) or {"es": "texto"})
    mercado = {"id": "winner", "label": "Ganador del partido", "selection": "A", "probability": 0.75}
    out = at.construir("9", "A", "B", "ATP · Stockholm", "Hard", mercado)
    assert out["receta"] == "ganador" and out["resumen"] == {"es": "texto"}
    assert [c["id"] for c in out["casillas"]] == ["saque", "rank", "h2h"]
    hechos = pedidos[0][2]
    assert hechos["significado"] == "A wins the match" and hechos["probabilidad_pct"] == 75
    assert pedidos[0][3] == "tennis"


def test_perfil_y_h2h_con_la_consulta_simulada(monkeypatch):
    at._cache.clear()
    llamadas = []

    def falsa(sql, params=()):
        llamadas.append(sql)
        if "CASE WHEN r.ganador" in sql:
            return [{"gana": 1}, {"gana": 1}, {"gana": 2}]
        return [fila() for _ in range(20)]
    monkeypatch.setattr(at, "_consultar", falsa)
    assert at._perfil(1, "hard")["n"] == 20 and at._h2h(1, 2) == (2, 1)
    at._perfil(1, "hard"), at._h2h(1, 2)
    assert len(llamadas) == 2        # la segunda vuelta sale de la caché
    at._cache.clear()


def test_ranking_se_compara_en_la_misma_semana_y_caduca(monkeypatch):
    from datetime import date, timedelta
    hoy = date.today()
    at._cache.clear()
    # a: 2.º la semana pasada y 1.º hace dos; b solo tiene la de hace dos (3.º). Se comparan en la semana de b.
    filas = [{"jugador_id": 1, "fecha_publicacion": hoy - timedelta(days=7), "posicion": 2},
             {"jugador_id": 1, "fecha_publicacion": hoy - timedelta(days=14), "posicion": 1},
             {"jugador_id": 2, "fecha_publicacion": hoy - timedelta(days=14), "posicion": 3}]
    monkeypatch.setattr(at, "_consultar", lambda sql, params=(): filas)
    assert at._ranking_pareja(1, 2, "atp") == (1, 3)     # misma semana, no la última de cada uno
    at._cache.clear()
    viejas = [{**f, "fecha_publicacion": f["fecha_publicacion"] - timedelta(days=60)} for f in filas]
    monkeypatch.setattr(at, "_consultar", lambda sql, params=(): viejas)
    assert at._ranking_pareja(1, 2, "atp") == (None, None)
    monkeypatch.setattr(at, "_consultar", lambda sql, params=(): filas[:2])
    at._cache.clear()
    assert at._ranking_pareja(1, 2, "atp") == (None, None)  # falta uno de los dos
    at._cache.clear()


EVENTO = {"id": "9017489489", "home": "A", "away": "B", "league": "ATP · Stockholm", "surface": "Hard",
          "status": "scheduled", "destacado": {"id": "winner"},
          "markets": [{"id": "winner", "label": "Ganador del partido", "selection": "A", "probability": 0.75},
                      {"id": "tiebreak-1", "label": "Tie-break", "selection": "Sí", "probability": 0.3}]}


def test_para_evento_usa_el_mercado_destacado_y_lo_identifica(monkeypatch):
    vistos = []
    monkeypatch.setattr(at, "construir", lambda *a: vistos.append(a) or {"receta": "ganador", "casillas": [], "resumen": None})
    out = at.para_evento(EVENTO)
    assert out["mercado_id"] == "winner" and vistos[0][5]["id"] == "winner"
    assert at.para_evento({**EVENTO, "status": "cancelled"}) is None
    assert at.para_evento({**EVENTO, "destacado": None}) is None
    monkeypatch.setattr(at, "construir", lambda *a: None)
    assert at.para_evento(EVENTO) is None


def test_ruta_del_analisis_devuelve_404_sin_datos_y_200_con_ellos(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from qf.api import tenis_publico, web
    app = FastAPI()
    app.include_router(web.router)
    cliente = TestClient(app)
    monkeypatch.setattr(tenis_publico, "public_data", lambda: {"events": [EVENTO]})
    monkeypatch.setattr(at, "construir", lambda *a: {"receta": "ganador", "casillas": [{"id": "h2h"}], "resumen": None})
    ok = cliente.get("/web/deportes/tenis/analisis/9017489489")
    assert ok.status_code == 200 and ok.json()["mercado_id"] == "winner" and ok.headers["cache-control"] == "no-store"
    assert cliente.get("/web/deportes/tenis/analisis/123").status_code == 404          # evento que no existe
    assert cliente.get("/web/deportes/tenis/analisis/abc").status_code == 404          # id no numérico
    monkeypatch.setattr(at, "construir", lambda *a: None)
    assert cliente.get("/web/deportes/tenis/analisis/9017489489").status_code == 404   # sin datos fiables
