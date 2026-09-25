"""
Verificación del parseo de alineaciones.

Solo se prueba la parte pura (transformar la respuesta del proveedor al
formato del esquema). La parte de I/O necesita base de datos y clave de API;
lo que se puede romper en silencio sin que nadie lo note es el parseo, porque
API-Football devuelve HTTP 200 con estructuras vacías o incompletas.
"""
from __future__ import annotations

from qf.ingest import lineups
from qf.ingest.lineups import WINDOW_MAX_BEFORE, WINDOW_MIN_BEFORE, _parse_side


def test_parsea_once_inicial_completo():
    entry = {
        "formation": "4-3-3",
        "coach": {"id": 9, "name": "Entrenador X"},
        "startXI": [
            {"player": {"id": 1, "name": "Portero", "pos": "G", "number": 1}},
            {"player": {"id": 2, "name": "Lateral", "pos": "D", "number": 2}},
            {"player": {"id": 3, "name": "Delantero", "pos": "F", "number": 9}},
        ],
    }
    out = _parse_side(entry)
    assert out["formation"] == "4-3-3"
    assert out["coach"] == "Entrenador X"
    assert len(out["starters"]) == 3
    assert out["starters"][0] == {"player_id": 1, "name": "Portero",
                                  "pos": "G", "number": 1}


def test_xi_vacio_no_revienta():
    """El caso normal antes de que se publique la alineación."""
    out = _parse_side({"formation": None, "startXI": []})
    assert out["starters"] == []
    assert out["formation"] is None


def test_falta_startxi_por_completo():
    """API-Football devuelve 200 con el bloque incompleto más a menudo de lo esperable."""
    out = _parse_side({})
    assert out["starters"] == []
    assert out["coach"] is None


def test_jugador_sin_campos_no_rompe_el_parseo():
    out = _parse_side({"startXI": [{"player": {}}, {}]})
    assert len(out["starters"]) == 2
    assert all(p["player_id"] is None for p in out["starters"])


def test_ventana_de_captura_es_coherente():
    """T-90 a T-20: antes casi nunca hay XI, después el mercado ya ajustó."""
    assert WINDOW_MIN_BEFORE > WINDOW_MAX_BEFORE > 0


def test_si_solo_hay_xi_local_reintenta_el_visitante(monkeypatch):
    entry = {"startXI": [{"player": {"id": 7, "name": "J", "pos": "M"}}]}
    monkeypatch.setattr(lineups.af, "get", lambda *_: ([entry, entry],
                                                        {"empty": False}))
    monkeypatch.setattr(lineups.af, "check_quota", lambda *_: None)
    inserted = []
    monkeypatch.setattr(lineups, "execute", lambda sql, params: inserted.append(
        params) or 1)

    def lookup(sql, params):
        if "count(DISTINCT side)" in sql:
            return {"n": 2}
        return {"exists": 1} if params[1] == "home" else None

    monkeypatch.setattr(lineups, "query_one", lookup)
    result = lineups.ingest_match({"match_id": "m", "af_id": "123",
                                   "mins_to_ko": 60})
    assert result == {"match_id": "m", "stored": 1, "pending": False}
    assert len(inserted) == 1
    assert inserted[0][1] == "away"
