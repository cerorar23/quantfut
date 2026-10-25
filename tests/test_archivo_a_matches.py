"""El extractor no fabrica datos: ausente o inválido es None, nunca 0."""
import math

from qf.ingest.archivo_a_matches import extraer

STATS = {"yellow_cards": [2.0, 1.0], "red_cards": [0.0, 1.0], "corners": [7.0, 5.0],
         "total_shots": [22.0, 21.0], "ShotsOnTarget": [5.0, 6.0],
         "expected_goals_on_target": [1.05, 2.68]}


def payload(**extra):
    base = {"content": {"matchFacts": {
        "infoBox": {"Referee": {"text": " José Luis Munuera Montero "},
                    "Stadium": {"name": "Estadio de Mestalla", "city": "Valencia", "country": "Spain",
                                "lat": 39.4746, "long": -0.3582, "capacity": 49430, "surface": "grass"}},
        "events": {"events": [{"type": "Half", "halfStrShort": "HT", "homeScore": 1, "awayScore": 2}]}}}}
    base.update(extra)
    return base


def test_caso_completo():
    r = extraer(payload(), STATS, 2, 3)
    assert (r["home_yellow"], r["away_yellow"]) == (2, 1)
    assert (r["home_red"], r["away_red"]) == (0, 1)
    assert (r["home_corners"], r["away_corners"]) == (7, 5)
    assert (r["home_shots"], r["away_shots"], r["home_shots_target"], r["away_shots_target"]) == (22, 21, 5, 6)
    assert (r["home_xgot"], r["away_xgot"]) == (1.05, 2.68)
    assert (r["home_goals_ht"], r["away_goals_ht"]) == (1, 2)
    assert r["referee_fotmob"] == "José Luis Munuera Montero"
    assert r["estadio"] == {"name": "Estadio de Mestalla", "city": "Valencia", "country": "Spain",
                            "lat": 39.4746, "lon": -0.3582, "capacity": 49430, "surface": "grass"}


def test_ausente_es_none_no_cero():
    r = extraer({}, {}, 0, 0)
    assert all(v is None for v in r.values())


def test_valores_invalidos_son_none():
    malos = {"yellow_cards": [-1.0, 1.0], "red_cards": [float("nan"), 0.0],
             "corners": [math.inf, 3.0], "total_shots": [True, 3.0],
             "ShotsOnTarget": [2.5, 1.0], "expected_goals_on_target": [1.0]}
    r = extraer(payload(), malos, 2, 3)
    for campo in ("home_yellow", "away_yellow", "home_red", "away_red", "home_corners", "away_corners",
                  "home_shots", "away_shots", "home_shots_target", "away_shots_target",
                  "home_xgot", "away_xgot"):
        assert r[campo] is None, campo


def test_descanso_mayor_que_el_final_es_none():
    p = payload()
    p["content"]["matchFacts"]["events"]["events"][0].update(homeScore=3, awayScore=0)
    r = extraer(p, STATS, 2, 3)
    assert r["home_goals_ht"] is None and r["away_goals_ht"] is None


def test_estadio_con_coordenadas_fuera_de_rango_no_se_guarda_con_ellas():
    p = payload()
    p["content"]["matchFacts"]["infoBox"]["Stadium"]["lat"] = 123.0
    r = extraer(p, STATS, 2, 3)
    assert r["estadio"]["name"] == "Estadio de Mestalla"
    assert r["estadio"]["lat"] is None and r["estadio"]["lon"] is None


def tarjeta(local: bool, tipo: str, tecnico: bool = False) -> dict:
    return {"type": "Card", "isHome": local, "card": tipo,
            "cardDescription": {"localizedKey": "coach", "defaultText": "Coach"} if tecnico else None}


def con_tarjetas(*tarjetas):
    p = payload()
    p["content"]["matchFacts"]["events"]["events"] += list(tarjetas)
    return p


CERO = {**STATS, "yellow_cards": [0.0, 0.0], "red_cards": [0.0, 0.0]}


def test_bloque_a_cero_manda_la_cronologia_sin_el_cuerpo_tecnico():
    # Argentina, Brasil y parte de México en 2026: FotMob deja [0, 0] aunque hubo tarjetas.
    p = con_tarjetas(tarjeta(True, "Yellow"), tarjeta(True, "Yellow"), tarjeta(False, "Yellow"),
                     tarjeta(False, "YellowRed"), tarjeta(True, "Red"), tarjeta(False, "Yellow", tecnico=True))
    r = extraer(p, CERO, 2, 3)
    assert (r["home_yellow"], r["away_yellow"]) == (2, 1)
    assert (r["home_red"], r["away_red"]) == (1, 1)


def test_bloque_a_cero_y_cronologia_sin_tarjetas_es_cero():
    r = extraer(payload(), CERO, 2, 3)
    assert (r["home_yellow"], r["away_yellow"], r["home_red"], r["away_red"]) == (0, 0, 0, 0)


def test_bloque_a_cero_sin_cronologia_completa_es_none():
    p = con_tarjetas(tarjeta(True, "Yellow"))
    p["content"]["matchFacts"]["events"]["events"] = p["content"]["matchFacts"]["events"]["events"][1:]
    r = extraer(p, CERO, 2, 3)
    assert all(r[k] is None for k in ("home_yellow", "away_yellow", "home_red", "away_red"))


def test_bloque_a_cero_con_tarjeta_desconocida_es_none():
    r = extraer(con_tarjetas(tarjeta(True, "Blue")), CERO, 2, 3)
    assert all(r[k] is None for k in ("home_yellow", "away_yellow", "home_red", "away_red"))


def test_bloque_con_tarjetas_se_respeta():
    r = extraer(con_tarjetas(tarjeta(True, "Yellow")), STATS, 2, 3)
    assert (r["home_yellow"], r["away_yellow"], r["home_red"], r["away_red"]) == (2, 1, 0, 1)


def test_arbitro_vacio_es_none():
    p = payload()
    p["content"]["matchFacts"]["infoBox"]["Referee"] = {"text": "   "}
    assert extraer(p, STATS, 2, 3)["referee_fotmob"] is None


def test_el_cli_por_defecto_es_ensayo(monkeypatch, capsys):
    from qf.ingest import archivo_a_matches as mod

    llamadas = []

    class FalsaConexion:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("qf.db.conn", lambda: FalsaConexion())
    monkeypatch.setattr(mod, "aplicar", lambda c, desde, rollback: llamadas.append(rollback) or {"ok": 1})
    mod.main(["--desde", "2024-01-01"])
    mod.main(["--desde", "2024-01-01", "--aplicar"])
    assert llamadas == [True, False]
    assert '"ok": 1' in capsys.readouterr().out


def test_huecos_xg_consulta_solo_lectura():
    from qf.ingest.archivo_a_matches import huecos_xg

    class Cursor:
        def __init__(self):
            self.sql = None

        def execute(self, sql, params=()):
            self.sql = sql
            return self

        def fetchall(self):
            return [{"league_id": "it.serie_b", "terminados": 639, "sin_xg": 188}]

    c = Cursor()
    filas = huecos_xg(c, "2025-01-01")
    assert filas[0]["sin_xg"] == 188
    assert "UPDATE" not in c.sql.upper() and "INSERT" not in c.sql.upper()
