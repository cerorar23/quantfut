import gzip
import io
import json
import urllib.error
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from qf.ingest import fotmob_captura as fc

KICKOFF = datetime(2026, 10, 19, 19, 0, tzinfo=timezone.utc)


def _previo():
    def equipo(coach, base, bajas):
        return {"formation": "4-2-3-1", "totalStarterMarketValue": 200_000_000, "coach": {"id": 1, "name": coach},
                "starters": [{"id": base + i, "name": f"J{i}", "positionId": 11, "marketValue": 1_000_000}
                             for i in range(11)],
                "unavailable": [{"id": base + 90 + i, "name": f"B{i}", "marketValue": 5_000_000,
                                 "unavailability": {"injuryId": 7, "type": "injury", "expectedReturn": "Doubtful"}}
                                for i in range(bajas)]}
    return {"general": {"matchId": "5795484", "started": False, "finished": False},
            "content": {"lineup": {"lineupType": "predicted", "homeTeam": equipo("De Zerbi", 100, 2),
                                   "awayTeam": equipo("Lampard", 200, 1)},
                        "weather": {"temperature": 12, "windSpeed": 2, "relativeHumidity": 81, "precipChance": 7,
                                    "precipitation": 0, "cloudCover": 88, "apiUsed": "forecast",
                                    "lastUpdated": "2026-10-18T13:00:04Z"}}}


def test_ventanas_de_captura():
    assert fc.ventana_de(1440) == "dia" and fc.ventana_de(1000) == "dia"
    assert fc.ventana_de(200) == "horas"
    assert fc.ventana_de(70) == "final" and fc.ventana_de(50) == "final"
    assert fc.ventana_de(40) == "cierre" and fc.ventana_de(25) == "cierre"
    for fuera in (10, 24.9, 46, 49.9, 76, 149, 301, 899, 1561):
        assert fc.ventana_de(fuera) is None


def test_ventana_tarde_se_solapa_con_cierre_y_se_toma_la_primera_pendiente():
    assert fc.ventanas_de(30) == ["cierre", "tarde"] and fc.ventanas_de(40) == ["cierre"]
    assert fc.ventanas_de(33) == ["cierre", "tarde"] and fc.ventanas_de(24) == []
    assert fc.ventana_de(30) == "cierre"


class _Filas:
    def __init__(self, filas):
        self.filas = filas

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return self.filas[0] if self.filas else None


def test_candidatos_toma_cierre_y_despues_tarde():
    from datetime import datetime, timedelta, timezone
    ahora = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    partido = {"match_id": "m1", "kickoff_utc": ahora + timedelta(minutes=30), "fotmob_match_id": "1", "mins": 30.0}
    hechas = set()

    class C:
        def execute(self, sql, params=None):
            if "FROM matches" in sql:
                return _Filas([partido])
            return _Filas([(1,)] if (params[0], params[1]) in hechas else [])

    assert [x["ventana"] for x in fc.candidatos_previos(C(), ahora)] == ["cierre"]
    hechas.add(("m1", "cierre"))
    assert [x["ventana"] for x in fc.candidatos_previos(C(), ahora)] == ["tarde"]
    hechas.add(("m1", "tarde"))
    assert fc.candidatos_previos(C(), ahora) == []


def test_datos_previo_conserva_pronostico_alineacion_y_bajas():
    d = fc.datos_previo(_previo(), KICKOFF)
    assert d["tipo_alineacion"] == "predicted" and d["clima_api"] == "forecast"
    assert d["clima_prob_precipitacion"] == 7.0 and d["clima_precipitacion"] == 0.0   # 0 es un dato real
    assert d["entrenador_local"] == "De Zerbi" and d["valor_xi_visita"] == 200_000_000
    assert len([j for j in d["jugadores"] if j["titular"]]) == 22
    assert sorted((b["side"], b["jugador_id"]) for b in d["bajas"]) == [("away", 290), ("home", 190), ("home", 191)]
    assert d["clima_actualizado"].isoformat().startswith("2026-10-18T13:00:04")


def test_datos_previo_sin_clima_ni_alineacion_deja_none():
    d = fc.datos_previo({"general": {"matchId": "1"}, "content": {}}, KICKOFF)
    assert d["clima_temperatura_c"] is None and d["clima_prob_precipitacion"] is None
    assert d["tipo_alineacion"] is None and d["jugadores"] == [] and d["bajas"] == []


def test_validar_exige_el_mismo_id():
    assert fc._validar({"general": {"matchId": "5795484"}}, "5795484")
    assert not fc._validar({"general": {"matchId": "999"}}, "5795484")
    assert not fc._validar({}, "5795484")


def _http_error(codigo):
    return urllib.error.HTTPError("https://x", codigo, "err", {}, io.BytesIO(b""))


@pytest.mark.parametrize("codigo", [401, 403, 429])
def test_un_bloqueo_detiene_la_captura_sin_reintentar(codigo):
    cli = fc.Cliente(espera_s=0)
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=_http_error(codigo)) as op:
        with pytest.raises(fc.AccesoDenegado):
            cli.get("matchDetails", {"matchId": 1})
    assert op.call_count == 1          # nada de insistir contra un bloqueo


def test_un_404_no_es_un_bloqueo():
    cli = fc.Cliente(espera_s=0)
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", side_effect=_http_error(404)) as op:
        with pytest.raises(urllib.error.HTTPError):
            cli.get("matchDetails", {"matchId": 1})
    assert op.call_count == 1


class _Resp:
    headers = {"Content-Encoding": "gzip"}

    def __init__(self, cuerpo):
        self.cuerpo = gzip.compress(json.dumps(cuerpo).encode())

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.cuerpo


def test_respuesta_valida_incluye_el_original_para_guardarlo():
    cli = fc.Cliente(espera_s=0)
    with patch("qf.ingest.fotmob_captura.urllib.request.urlopen", return_value=_Resp({"general": {"matchId": "5"}})):
        d = cli.get("matchDetails", {"matchId": 5})
    assert json.loads(d["__raw__"])["general"]["matchId"] == "5"


def test_correr_pasa_las_opciones_de_relleno_y_respeta_el_enfriamiento():
    from unittest.mock import MagicMock, patch

    c = MagicMock()
    with patch.object(fc, "en_enfriamiento", return_value=False), \
            patch.object(fc, "capturar_posteriores", return_value={"guardados": 0}) as f, \
            patch.object(fc, "_log"):
        fc.correr(c, "posteriores", cli=object(), dias_atras=20, maximo=500)
    assert f.call_args.kwargs == {"dias_atras": 20, "maximo": 500}
    with patch.object(fc, "en_enfriamiento", return_value=True), \
            patch.object(fc, "capturar_posteriores") as f:
        assert "omitido" in fc.correr(c, "posteriores", cli=object())
    f.assert_not_called()
