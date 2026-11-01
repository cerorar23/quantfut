"""Huecos de once con SportsAPIPro: solo en la ventana, 2 intentos, tope diario, sin peticiones si no hay hueco."""
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from qf.ingest import sportsapipro_alineaciones as sp

T0 = datetime(2026, 10, 31, 18, 0, tzinfo=timezone.utc)
KO = T0 + timedelta(minutes=30)


def evento(i, utid=17, ko=KO, local="Chelsea", visita="Wolves"):
    return {"id": i, "startTimestamp": int(ko.timestamp()), "homeTeam": {"name": local}, "awayTeam": {"name": visita},
            "tournament": {"uniqueTournament": {"id": utid}}}


def lado(n=11):
    return {"formation": "4-3-3", "players": [{"substitute": False, "player": {"id": 1000 + i, "name": "J%d" % i}}
                                               for i in range(n)], "missingPlayers": []}


class Fake:
    def __init__(self, eventos=(), status_once=200):
        self.urls, self.eventos, self.status_once = [], list(eventos), status_once

    def __call__(self, url, key, timeout=60):
        self.urls.append(url)
        if "/schedule/" in url:
            return 200, json.dumps({"events": self.eventos}).encode()
        return self.status_once, json.dumps({"data": {"confirmed": True, "home": lado(), "away": lado()}}).encode()


class Conn:
    def execute(self, sql, params=()):
        return SimpleNamespace(fetchone=lambda: {"ok": True})

    @contextmanager
    def transaction(self):
        yield


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    monkeypatch.setenv("SPORTSAPIPRO_KEY", "k")
    monkeypatch.setattr(sp, "carpeta", lambda: tmp_path / "sportsapipro")
    monkeypatch.setattr(sp, "LIGA_DE_TORNEO", {17: "gb.premier_league"})
    monkeypatch.setattr(sp, "conn", lambda: _cm())
    monkeypatch.setattr(sp, "query", lambda sql, params=(): [{"match_id": "m1", "league_id": "gb.premier_league",
                                                              "kickoff_utc": KO}])
    monkeypatch.setattr(sp, "emparejar", lambda fila: ("m1", "ok") if fila["homeTeam"] == "Chelsea" else (None, "sin_partido"))
    aplicados = []
    monkeypatch.setattr(sp, "aplicar", lambda c, rec, fila, mid: aplicados.append((rec, mid)) or {"oficial": True})
    monkeypatch.setattr(sp, "record_health", lambda *a, **k: None)
    return SimpleNamespace(aplicados=aplicados, ruta=tmp_path / "sportsapipro")


@contextmanager
def _cm():
    yield Conn()


def test_un_hueco_pide_calendario_una_vez_y_luego_el_once(mundo):
    f = Fake([evento(555)])
    r = sp.run(call=f, clock=lambda: T0)
    assert [u.rsplit("/", 2)[-2] if "/schedule/" not in u else "cal" for u in f.urls] == ["cal", "cal", "cal", "555"]
    assert r["consultados"] == 1 and r["oficiales"] == 1 and r["peticiones_hoy"] == 4
    assert mundo.aplicados[0][1] == "m1"


def test_sin_hueco_no_hay_ninguna_peticion(mundo, monkeypatch):
    monkeypatch.setattr(sp, "query", lambda sql, params=(): [])
    f = Fake([evento(555)])
    assert sp.run(call=f, clock=lambda: T0)["huecos"] == 0 and f.urls == []


def test_dos_intentos_con_espera_y_luego_para(mundo):
    f = Fake([evento(555)])
    sp.run(call=f, clock=lambda: T0)
    n = len(f.urls)
    sp.run(call=f, clock=lambda: T0 + timedelta(minutes=3))          # antes de 7 min: nada
    assert len(f.urls) == n
    sp.run(call=f, clock=lambda: T0 + timedelta(minutes=8))          # segundo intento (calendario en caché)
    assert f.urls[-1].endswith("/555/lineups") and len(f.urls) == n + 1
    sp.run(call=f, clock=lambda: T0 + timedelta(minutes=16))         # ya van 2: no más
    assert len(f.urls) == n + 1


def test_evento_que_no_empareja_cuenta_sin_evento_y_no_pide_el_once(mundo):
    f = Fake([evento(556, local="Otro")])
    r = sp.run(call=f, clock=lambda: T0)
    assert r["sin_evento"] == 1 and r["consultados"] == 0 and all("/schedule/" in u for u in f.urls)


def test_tope_diario_corta_las_peticiones(mundo, monkeypatch):
    monkeypatch.setattr(sp, "DIARIO", 3)
    f = Fake([evento(555)])
    r = sp.run(call=f, clock=lambda: T0)
    assert len(f.urls) == 3 and r["consultados"] == 0              # el calendario gastó el tope


def test_respuesta_de_error_no_se_carga(mundo):
    f = Fake([evento(555)], status_once=403)
    r = sp.run(call=f, clock=lambda: T0)
    assert r["consultados"] == 1 and mundo.aplicados == []


def test_sin_clave_no_hace_nada(mundo, monkeypatch):
    monkeypatch.delenv("SPORTSAPIPRO_KEY")
    assert sp.run(call=Fake(), clock=lambda: T0)["skipped"] == "sin SPORTSAPIPRO_KEY"


def test_la_peticion_lleva_user_agent_de_navegador(monkeypatch):
    visto = {}

    class R:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    monkeypatch.setattr(sp.urllib.request, "urlopen", lambda req, timeout=0: visto.update(h=dict(req.header_items())) or R())
    sp.http("https://x", "k")
    assert "urllib" not in visto["h"]["User-agent"].lower()


def test_el_calendario_no_se_repite_antes_de_6_horas_y_si_despues(mundo, monkeypatch):
    """Regresión (CI del PR 223): con un calendario ya archivado, `refrescar_calendario` usaba `ahora` sin definir."""
    f = Fake([evento(555)])
    db = sp.abrir(mundo.ruta)
    assert sp.refrescar_calendario(mundo.ruta, db, "k", f, lambda: T0) == 3      # 3 fechas x 1 evento
    assert sp.refrescar_calendario(mundo.ruta, db, "k", f, lambda: T0 + timedelta(hours=5)) == 0
    n = len(f.urls)
    assert sp.refrescar_calendario(mundo.ruta, db, "k", f, lambda: T0 + timedelta(hours=7)) == 3
    assert len(f.urls) == n + 3


def test_hueco_sin_evento_en_cache_refresca_aunque_ya_haya_calendario_archivado(mundo):
    f = Fake([evento(556, local="Otro")])
    sp.run(call=f, clock=lambda: T0)                                   # primer calendario
    f.eventos = [evento(555)]
    n = len(f.urls)
    r = sp.run(call=f, clock=lambda: T0 + timedelta(hours=7))          # evento nuevo, calendario viejo: hay que pedirlo
    assert r["consultados"] == 1 and len(f.urls) > n
