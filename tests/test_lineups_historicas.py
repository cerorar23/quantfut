"""
Alineaciones históricas (db/034): solo para entrenar el ajuste por XI.

Lo que fijan: un fixture solo se empareja con UN partido de los mismos dos
equipos en ±36 h; lo no resuelto o ambiguo se descarta; y la sombra y la
predicción diaria no leen la tabla.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from qf.ingest.lineups_historicas import emparejar

KO = datetime(2026, 3, 1, 18, tzinfo=timezone.utc)


def _fx(fid, local, visita, ko=KO, estado="FT"):
    return {"fixture": {"id": fid, "date": ko.isoformat(), "status": {"short": estado}},
            "teams": {"home": {"name": local, "id": None}, "away": {"name": visita, "id": None}}}


EQUIPOS = {"Alfa": 1, "Beta": 2, "Gamma": 3}
equipo_de = lambda nombre, af_id: EQUIPOS.get(nombre)  # noqa: E731


def test_empareja_por_equipos_y_fecha():
    partidos = [{"match_id": "a", "home_team_id": 1, "away_team_id": 2,
                 "kickoff_utc": KO + timedelta(hours=20)},
                {"match_id": "b", "home_team_id": 2, "away_team_id": 1,
                 "kickoff_utc": KO + timedelta(days=90)}]
    assert emparejar([_fx(10, "Alfa", "Beta"), _fx(11, "Beta", "Alfa")],
                     equipo_de, partidos) == [("a", 10)]


def test_no_adivina():
    partidos = [{"match_id": "a", "home_team_id": 1, "away_team_id": 2, "kickoff_utc": KO},
                {"match_id": "a2", "home_team_id": 1, "away_team_id": 2,
                 "kickoff_utc": KO + timedelta(hours=30)}]
    assert emparejar([_fx(10, "Alfa", "Beta")], equipo_de, partidos) == [], "dos candidatos"
    assert emparejar([_fx(10, "Alfa", "Desconocido")], equipo_de, partidos) == []
    assert emparejar([_fx(10, "Alfa", "Beta", estado="PST")], equipo_de, partidos) == []


def test_ni_la_sombra_ni_la_prediccion_leen_la_tabla():
    raiz = Path(__file__).resolve().parents[1] / "src" / "qf"
    for modulo in ("model/shadow.py", "publish/daily.py", "ingest/lineups.py",
                   "publish/shadow_sharp.py"):
        assert "lineups_historicas" not in (raiz / modulo).read_text(encoding="utf-8"), modulo


def test_para_en_la_reserva_de_cuota_aunque_llegue_como_texto(monkeypatch):
    from qf.ingest import lineups_historicas as lh
    llamadas, insertados = [], []
    xi = {"formation": "4-4-2", "startXI": [{"player": {"id": i, "pos": "M"}} for i in range(11)]}

    def get(endpoint, params):
        llamadas.append(params["fixture"])
        return [xi, xi], {"quota_remaining": "2400"}

    monkeypatch.setattr(lh.af, "get", get)
    monkeypatch.setattr(lh, "execute", lambda sql, params: insertados.append(params))
    r = lh.descargar([("a", 1), ("b", 2), ("c", 3)], reserva=2500)
    assert llamadas == [1] and r == {"con_xi": 1, "sin_xi": 0}
    assert len(insertados) == 2
