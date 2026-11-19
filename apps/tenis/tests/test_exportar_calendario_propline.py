"""El extractor del servidor: forma del documento, huella determinista y ausencia de lote."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ruta = Path(__file__).resolve().parents[1] / "ops" / "exportar_calendario_propline.py"
spec = importlib.util.spec_from_file_location("exportar_calendario_propline", ruta)
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)
AHORA = datetime(2026, 11, 17, 22, 30, tzinfo=timezone.utc)
EVENTOS = [{"id": 2, "commence_time": "2026-11-18T10:00:00Z", "home_team": "A", "away_team": "B", "tournament": "T", "tour": "ATP",
            "live": False, "is_outright": False, "bookmakers": [{"key": "x"}] * 50, "home_team_id": 9},
           {"id": 1, "commence_time": "2026-11-18T11:00:00Z", "home_team": "C", "away_team": "D", "tournament": "T", "tour": "ATP"}]


def test_documento_minimo_ordenado_y_con_huella_estable():
    llamadas = []

    def newest(raiz, ruta_, ahora, max_age_seconds):
        llamadas.append((ruta_, max_age_seconds))
        return list(EVENTOS), {"received_at": "2026-11-17T22:07:57+00:00"}

    d1 = ex.extraer(newest, AHORA)
    d2 = ex.extraer(lambda *a, **k: (list(reversed(EVENTOS)), {"received_at": "2026-11-17T22:07:57+00:00"}), AHORA)
    assert llamadas == [("/v1/sports/tennis/odds", 7200)]
    assert [e["id"] for e in d1["eventos"]] == [1, 2] and set(d1["eventos"][0]) == set(ex.CAMPOS)   # sin cuotas ni ids ajenos
    assert d1["recibido_en"] == "2026-11-17T22:07:57+00:00" and len(d1["sha256"]) == 64
    assert d1 == d2                                                                                     # el orden del archivo no cambia la huella
    d3 = ex.extraer(lambda *a, **k: (list(EVENTOS), {"received_at": "2026-11-17T23:07:57+00:00"}), AHORA)
    assert d3["sha256"] != d1["sha256"]                                                                 # otra hora = otro documento
    json.dumps(d1)


def test_sin_lote_reciente_no_inventa_nada():
    assert ex.extraer(lambda *a, **k: (None, None), AHORA) is None
