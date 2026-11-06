from qf.publish.regla_publicacion import Regla, elegir, publicables_tenis, regla_desde_entorno


def c(id, fam, prob, precio, key=None):
    return {"id": id, "familia": fam, "prob": prob, "precio": precio, "linea_key": key or id}


def test_exige_cuota_valida_y_banda():
    r = Regla()
    cand = [c("a", "game_total", .80, 1.25), c("sin", "game_total", .90, None), c("barata", "team_points", .90, 1.05),
            c("baja", "handicap", .70, 1.5), c("lejana", "handicap", .99, 1.5), c("nan", "handicap", float("nan"), 1.5)]
    assert elegir(cand, r) == {"a"}


def test_props_de_jugador_fuera():
    assert elegir([c("p", "player_points", .85, 1.5)], Regla()) == set()
    assert elegir([c("p", "player_points", .85, 1.5)], Regla(excluidas=frozenset())) == {"p"}


def test_un_lado_por_linea_y_uno_por_familia():
    cand = [c("o", "game_total", .79, 1.3, key=220.5), c("u", "game_total", .81, 1.3, key=220.5),
            c("otra", "game_total", .90, 1.3, key=230.5), c("h", "handicap", .80, 1.4, key=3.5)]
    assert elegir(cand, Regla()) == {"otra", "h"}          # un total (el de mayor probabilidad) y un hándicap
    assert elegir(cand, Regla(por_familia=2)) == {"otra", "u", "h"}


def test_desempate_reproducible():
    cand = [c("b", "game_total", .8, 1.3, key=1), c("a", "game_total", .8, 1.3, key=2)]
    assert elegir(cand, Regla()) == {"a"}


def test_entorno(monkeypatch):
    monkeypatch.setenv("QF_PUB_PRICE_MIN", "1.35")
    monkeypatch.setenv("QF_PUB_PROB_MIN", "x")
    monkeypatch.setenv("QF_PUB_EXCLUDE", "")
    r = regla_desde_entorno()
    assert r.precio_min == 1.35 and r.prob_min == .78 and r.excluidas == frozenset()


def test_tenis_usa_la_cuota_del_overlay():
    feed = {"events": [{"id": "1", "markets": [
        {"id": "winner", "probability": .82}, {"id": "games_total-2", "probability": .85},
        {"id": "games_total-3", "probability": .80}, {"id": "sets_total-1", "probability": .90}]},
        {"id": "2", "markets": "roto"}]}
    cuotas = {"1": {"winner": {"price": 1.25}, "games_total-2": {"price": 1.1}, "games_total-3": {"price": 1.3}}}
    assert publicables_tenis(feed, cuotas, Regla()) == {"1": ["games_total-3", "winner"]}
