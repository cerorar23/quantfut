from datetime import datetime, timezone

from qf.ingest.fotmob_a_motor import COLS_JUGADOR, COLS_PARTIDO, extraer

KICKOFF = datetime(2026, 2, 1, 14, 0, tzinfo=timezone.utc)


def _equipo(nombre, coach_id, base):
    return {
        "name": nombre, "formation": "4-3-3", "rating": 7.0, "averageStarterAge": 27.3,
        "totalStarterMarketValue": 302533388,
        "coach": {"id": coach_id, "name": "Unai Emery"},
        "starters": [{"id": base + i, "name": f"J{base + i}", "positionId": 11, "usualPlayingPositionId": 0,
                      "shirtNumber": str(i + 1), "age": 25, "marketValue": 1_000_000 * (i + 1),
                      "performance": {"rating": 6.7}} for i in range(11)],
        "subs": [{"id": base + 50, "name": "Suplente", "positionId": 31, "age": 19, "marketValue": 500_000}],
        "unavailable": [{"id": base + 90, "name": "Lesionado", "age": 28, "positionId": 1000,
                         "marketValue": 40_397_589,
                         "unavailability": {"injuryId": 30, "type": "injury", "expectedReturn": "Doubtful"}},
                        {"id": base + 91, "name": "Sancionado", "unavailability": {
                            "type": "suspension", "expectedReturn": "Mid July 2026",
                            "expectedReturnDate": "2026-07-18T05:00:00Z"}}],
    }


def _original(**cambios):
    p = {
        "general": {"matchRound": "24", "leagueRoundName": "24"},
        "header": {"status": {"whoLostOnAggregated": None}},
        "content": {
            "matchFacts": {"infoBox": {
                "legInfo": None, "Tournament": {"roundName": "24", "round": "24"},
                "Stadium": {"name": "Villa Park"}, "Referee": {"text": "Tim Robinson", "country": "England"},
                "Attendance": 41415}},
            "lineup": {"homeTeam": _equipo("Aston Villa", 96940, 1000), "awayTeam": _equipo("Brighton", 5, 2000)},
            "weather": {"temperature": 8, "windSpeed": 1, "windDirectionCardinal": "ESE", "relativeHumidity": 91,
                        "precipitation": 0.25, "cloudCover": 98, "description": "Showers", "apiUsed": "current",
                        "lastUpdated": "2026-02-01T16:02:34Z"},
        },
    }
    p.update(cambios)
    return p


def test_extrae_contexto_jugadores_y_bajas():
    x = extraer(_original(), KICKOFF)
    p = x["partido"]
    assert set(p) == set(COLS_PARTIDO)
    assert (p["ronda"], p["arbitro"], p["asistencia"], p["estadio"]) == ("24", "Tim Robinson", 41415, "Villa Park")
    assert p["entrenador_local"] == "Unai Emery" and p["entrenador_local_id"] == 96940
    assert p["valor_xi_local"] == 302533388 and p["formacion_visita"] == "4-3-3"
    assert len(x["jugadores"]) == 2 * (11 + 1)
    assert sum(j["titular"] for j in x["jugadores"]) == 22
    assert set(x["jugadores"][0]) == set(COLS_JUGADOR)
    assert [b["tipo"] for b in x["bajas"] if b["side"] == "home"] == ["injury", "suspension"]
    sancion = [b for b in x["bajas"] if b["tipo"] == "suspension"][0]
    assert sancion["regreso_fecha"].year == 2026 and sancion["lesion_id"] is None


def test_clima_se_marca_solo_si_cae_cerca_del_saque():
    assert extraer(_original(), KICKOFF)["partido"]["clima_en_partido"] is True  # +2,04 h
    tarde = _original()
    tarde["content"]["weather"]["lastUpdated"] = "2026-10-13T20:00:00Z"
    p = extraer(tarde, KICKOFF)["partido"]
    assert p["clima_en_partido"] is False and p["clima_desfase_horas"] > 1000
    sin = _original()
    del sin["content"]["weather"]
    p = extraer(sin, KICKOFF)["partido"]
    assert p["clima_en_partido"] is None and p["clima_temperatura_c"] is None


def test_ausente_o_invalido_es_none_nunca_cero():
    mal = _original()
    mal["content"]["matchFacts"]["infoBox"]["Attendance"] = -5
    mal["content"]["lineup"]["homeTeam"]["totalStarterMarketValue"] = float("nan")
    mal["content"]["lineup"]["homeTeam"]["starters"][0]["marketValue"] = "mucho"
    mal["content"]["lineup"]["homeTeam"]["starters"][1]["id"] = None
    mal["content"]["lineup"]["awayTeam"]["coach"] = None
    x = extraer(mal, KICKOFF)
    p = x["partido"]
    assert p["asistencia"] is None and p["valor_xi_local"] is None
    assert p["entrenador_visita"] is None and p["entrenador_visita_id"] is None
    assert len(x["jugadores"]) == 2 * 12 - 1  # el jugador sin id no entra
    assert [j for j in x["jugadores"] if j["jugador_id"] == 1000][0]["valor_mercado"] is None


def test_temperatura_bajo_cero_es_valida():
    frio = _original()
    frio["content"]["weather"]["temperature"] = -7
    assert extraer(frio, KICKOFF)["partido"]["clima_temperatura_c"] == -7.0


def test_original_vacio_no_rompe():
    x = extraer({}, KICKOFF)
    assert x["jugadores"] == [] and x["bajas"] == []
    assert all(v is None for v in x["partido"].values())
