from nba.api.publicacion import publicar


def fila(id, market, side, prob, price, line=None, team="A", player_id=None):
    return {"id": id, "market": market, "side": side, "probability": prob, "price": price, "line": line,
            "team": team, "player_id": player_id}


def test_marca_publicables_sin_quitar_ninguno():
    salida = {"markets": [
        fila("w", "winner", "local", .80, 1.3),
        fila("t-o", "game_total", "over", .30, 3.0, 220.5), fila("t-u", "game_total", "under", .85, 1.25, 220.5),
        fila("h-l", "handicap", "local", .40, 2.0, -3.5), fila("h-v", "handicap", "visit", .80, 1.3, 3.5),
        fila("p", "player_points", "over", .90, 1.5, 20.5, player_id=1),
        fila("barata", "team_points", "over", .90, 1.05, 110.5)]}
    publicar(salida)
    flags = {m["id"]: m["publicable"] for m in salida["markets"]}
    assert flags == {"w": True, "t-o": False, "t-u": True, "h-l": False, "h-v": True, "p": False, "barata": False}
