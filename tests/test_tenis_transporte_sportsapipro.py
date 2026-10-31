"""Transporte SportsAPIPro para el motor de tenis: fechas NY, caché por ejecución, errores y formato."""
import json
from datetime import datetime, timezone

from qf.ingest import tenis_equivalencias as te, tenis_transporte_sportsapipro as tt

TS = int(datetime(2026, 10, 30, 14, 30, tzinfo=timezone.utc).timestamp())


def evento(i, categoria="ATP"):
    return {"id": i, "startTimestamp": TS, "status": {"type": "finished", "description": "Ended"}, "winnerCode": 1,
            "homeTeam": {"id": 10 + i, "name": "A%d" % i, "shortName": "A. A%d" % i},
            "awayTeam": {"id": 50 + i, "name": "B%d" % i, "shortName": "B. B%d" % i},
            "homeScore": {"current": 2, "period1": 6, "period2": 6}, "awayScore": {"current": 0, "period1": 1, "period2": 2},
            "tournament": {"name": "Basel", "category": {"name": categoria}, "uniqueTournament": {"id": 2400}}}


class Fake:
    def __init__(self, status=200):
        self.urls, self.status = [], status

    def __call__(self, url, key, timeout=60):
        self.urls.append(url.rsplit("/", 1)[1])
        return self.status, json.dumps({"events": [evento(1), evento(2, "WTA")]}).encode()


def transporte(tmp_path, fake):
    te.connect(tmp_path / "eq").close()
    return tt.TransporteSportsApiPro("k", tmp_path / "eq", call=fake)


def pide(t, d0, d1, tour="265"):
    return t("https://api.api-tennis.com/tennis/", params={"method": "get_fixtures", "date_start": d0, "date_stop": d1,
                                                           "event_type_key": tour, "timezone": "UTC"}, timeout=(15, 60),
             allow_redirects=False)


def test_captura_ancha_pide_un_dia_ny_antes_y_los_dos_circuitos_comparten_peticiones(tmp_path):
    f = Fake()
    t = transporte(tmp_path, f)
    atp = pide(t, "2026-10-30", "2026-11-02", "265")
    wta = pide(t, "2026-10-30", "2026-11-02", "266")
    assert f.urls == ["2026-10-29", "2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"] and t.peticiones == 5
    assert atp.status_code == 200 and [r["event_type_type"] for r in json.loads(atp.content)["result"]] == ["Atp Singles"]
    assert [r["event_type_type"] for r in json.loads(wta.content)["result"]] == ["Wta Singles"]


def test_refresco_de_resultados_solo_pide_ayer_y_hoy(tmp_path):
    f = Fake()
    pide(transporte(tmp_path, f), "2026-10-30", "2026-10-31")
    assert f.urls == ["2026-10-30", "2026-10-31"]


def test_error_de_http_se_devuelve_como_respuesta_no_exitosa(tmp_path):
    assert pide(transporte(tmp_path, Fake(status=429)), "2026-10-30", "2026-10-31").status_code == 429


def test_otros_metodos_no_se_soportan(tmp_path):
    assert transporte(tmp_path, Fake())("u", params={"method": "get_H2H"}).status_code == 501


def test_el_cuerpo_cumple_lo_que_exige_el_almacen_de_estados(tmp_path):
    """`StateStore.ingest`: success == 1, result lista, event_key sin repetir y dos jugadores distintos por partido."""
    cuerpo = json.loads(pide(transporte(tmp_path, Fake()), "2026-10-30", "2026-10-31").content)
    assert cuerpo["success"] == 1 and isinstance(cuerpo["result"], list) and cuerpo["result"]
    claves = [r["event_key"] for r in cuerpo["result"]]
    assert len(claves) == len(set(claves))
    assert all(r["first_player_key"] != r["second_player_key"] for r in cuerpo["result"])


class Primario:
    def __init__(self, status=200, cuerpo=None, error=None):
        self.status, self.cuerpo, self.error, self.llamadas = status, cuerpo, error, 0

    def __call__(self, url, params=None, timeout=None, allow_redirects=False):
        self.llamadas += 1
        if self.error:
            raise self.error
        return tt.Respuesta(self.status, json.dumps(self.cuerpo if self.cuerpo is not None else {"success": 1, "result": []}).encode())


def con_respaldo(tmp_path, primario):
    return tt.TransporteConRespaldo(primario, transporte(tmp_path, Fake()))


def test_con_respaldo_usa_api_tennis_mientras_responda_bien(tmp_path):
    t = con_respaldo(tmp_path, Primario())
    assert pide(t, "2026-10-30", "2026-10-31").status_code == 200
    assert t.fuentes == {"api-tennis": 1, "sportsapipro": 0} and t.peticiones == 0


def test_con_respaldo_cambia_solo_si_api_tennis_falla(tmp_path):
    for primario in (Primario(status=403), Primario(cuerpo={"success": 0, "result": "plan vencido"}), Primario(error=OSError("red")),
                     Primario(cuerpo={"success": 1, "result": None})):
        t = con_respaldo(tmp_path, primario)
        r = pide(t, "2026-10-30", "2026-10-31")
        assert t.fuentes == {"api-tennis": 0, "sportsapipro": 1} and json.loads(r.content)["result"]
