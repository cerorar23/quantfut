"""Endpoints públicos de cuota de referencia (NBA y tenis): forma, no-store, nunca 500 y caché de 60 s."""
import json
import shutil
import threading
import time
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import cuotas_nba as cn
from qf.api import cuotas_tenis as ct
from qf.api import cuotas_web as cw
from qf.api import tenis_publico as tp
from qf.api import web

import test_cuotas_nba as tn
import test_cuotas_tenis as tt

NOW = tn.NOW
app = FastAPI()
app.include_router(web.router)
client = TestClient(app)
NBA, TENIS = "/web/deportes/nba/cuotas", "/web/deportes/tenis/cuotas"


class Reloj:
    def __init__(self):
        self.t = NOW

    def __call__(self):
        return self.t


@pytest.fixture(autouse=True)
def entorno(monkeypatch, tmp_path):
    ct.clear_cache()
    cn.clear_cache()
    cw.clear_cache()
    reloj = Reloj()
    monkeypatch.setattr(cw, "_ahora", reloj)
    cfg = SimpleNamespace(propline_archive=str(tmp_path / "arch"), nba_cohorts_dir=str(tmp_path / "cohorts"),
                          tennis_sealed_dir=str(tmp_path / "sellos"))
    monkeypatch.setattr(cw, "settings", cfg)
    yield reloj
    ct.clear_cache()
    cn.clear_cache()
    cw.clear_cache()


def monta_nba(tmp_path):
    prop = tn.archivo(tmp_path / "arch")
    raiz = tmp_path / "cohorts"
    bundle = {k: v for k, v in tn.cohorte(prop).items() if k != "cohort"}
    sha = tn._escribe(raiz / "20261030-a" / "bundle.json", bundle)
    tn._escribe(raiz / "20261030-a" / "bundle.seal.json", dict(sha256=sha))
    return prop


def monta_tenis(tmp_path, monkeypatch):
    r = tt.archivo(tmp_path / "arch")
    (tmp_path / "sellos").mkdir(exist_ok=True)
    tt.sellado(tmp_path / "sellos", tt.pronostico(r))
    feed = tp.projection(tmp_path / "sellos", tt.NOW + timedelta(hours=1))
    monkeypatch.setattr(tp, "public_data", lambda: feed)
    return r


def test_nba_forma_exacta_y_no_store(tmp_path):
    monta_nba(tmp_path)
    r = client.get(NBA)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert set(body) == {"state", "generated_at", "source", "events"}
    assert body["state"] == "ok" and body["source"] == "PropLine" and body["generated_at"] == NOW.isoformat()
    assert body["events"]["0022600100"]["quotes"]["winner||"]["home"]["price"] == 1.62


def test_tenis_forma_exacta_y_no_store(tmp_path, monkeypatch):
    monta_tenis(tmp_path, monkeypatch)
    r = client.get(TENIS)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert set(body) == {"state", "generated_at", "source", "events"}
    assert body["state"] == "ok" and body["source"] == "PropLine"
    assert body["events"]["1"]["winner"]["price"] == 1.83


@pytest.mark.parametrize("ruta", [NBA, TENIS])
def test_ajustes_sin_definir_no_disponible(ruta, monkeypatch):
    monkeypatch.setattr(cw, "settings", SimpleNamespace(propline_archive=None, nba_cohorts_dir=None,
                                                        tennis_sealed_dir=None))
    r = client.get(ruta)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json()["state"] == "unavailable" and r.json()["events"] == {} and r.json()["source"] == "PropLine"


def test_archivo_ausente_no_disponible(tmp_path, monkeypatch):
    monta_tenis(tmp_path, monkeypatch)
    (tmp_path / "cohorts").mkdir()
    shutil.rmtree(tmp_path / "arch")
    for ruta in (NBA, TENIS):
        r = client.get(ruta)
        assert r.status_code == 200 and r.json()["state"] == "unavailable"


def test_recibo_corrupto_es_parcial(tmp_path):
    monta_nba(tmp_path)
    for p in (tmp_path / "arch").rglob("*"):  # estropea los recibos, no el índice
        if p.is_file() and "sqlite" not in p.name:
            p.write_bytes(b"basura")
    r = client.get(NBA)
    assert r.status_code == 200 and r.json()["state"] == "partial"


def test_sello_corrupto_de_tenis_no_tumba_el_resto(tmp_path, monkeypatch):
    monta_tenis(tmp_path, monkeypatch)
    (tmp_path / "sellos" / "predictions" / "basura.json").write_text("{no json", encoding="utf-8")
    r = client.get(TENIS)
    assert r.status_code == 200 and r.json()["state"] == "ok"
    assert r.json()["events"]["1"]["winner"]["price"] == 1.83


def test_excepcion_inesperada_no_disponible_y_no_se_cachea(tmp_path, monkeypatch):
    monta_nba(tmp_path)
    llamadas = []
    real = cn.nba_overlay

    def falla(*a, **k):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise RuntimeError("boom")
        return real(*a, **k)

    monkeypatch.setattr(cw, "nba_overlay", falla)
    r = client.get(NBA)
    assert r.status_code == 200 and r.json()["state"] == "unavailable" and r.headers["cache-control"] == "no-store"
    assert client.get(NBA).json()["state"] == "ok"  # el fallo no envenenó la caché
    assert len(llamadas) == 2


def test_cache_de_60_segundos(tmp_path, monkeypatch, entorno):
    monta_nba(tmp_path)
    n = []
    real = cn.nba_overlay
    monkeypatch.setattr(cw, "nba_overlay", lambda *a, **k: (n.append(1), real(*a, **k))[1])
    a = client.get(NBA).json()
    entorno.t = NOW + timedelta(seconds=59)
    b = client.get(NBA).json()
    assert a == b and len(n) == 1
    entorno.t = NOW + timedelta(seconds=61)
    c = client.get(NBA).json()
    assert len(n) == 2 and c["generated_at"] == (NOW + timedelta(seconds=61)).isoformat()


def test_peticiones_simultaneas_calculan_una_vez(tmp_path, monkeypatch):
    monta_nba(tmp_path)
    n = []
    real = cn.nba_overlay

    def lento(*a, **k):
        n.append(1)
        time.sleep(.2)
        return real(*a, **k)

    monkeypatch.setattr(cw, "nba_overlay", lento)
    out = []
    hilos = [threading.Thread(target=lambda: out.append(client.get(NBA).status_code)) for _ in range(5)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert out == [200] * 5 and len(n) == 1


def test_sin_datos_de_cuenta(tmp_path, monkeypatch):
    monta_nba(tmp_path)
    monta_tenis(tmp_path, monkeypatch)
    for ruta in (NBA, TENIS):
        r = client.get(ruta, headers={"Authorization": "Bearer x", "Cookie": "s=1"})
        texto = json.dumps(r.json()).lower()
        for prohibido in ("token", "email", "user", "account", "password", "cuenta"):
            assert prohibido not in texto
        assert "set-cookie" not in r.headers


def test_cargador_de_sellos_ignora_ids_con_ruta_y_archivos_malos(tmp_path):
    (tmp_path / "predictions").mkdir()
    (tmp_path / "predictions" / "1.json").write_text('{"a": 1}', encoding="utf-8")
    (tmp_path / "predictions" / "2.json").write_text("{no", encoding="utf-8")
    (tmp_path / "secreto.json").write_text('{"x": 1}', encoding="utf-8")
    assert ct.load_sealed(tmp_path, ["1", "2", "3", "../secreto", "a/b"]) == {"1": {"a": 1}}
    assert set(ct.load_sealed(tmp_path)) == {"1"} and ct.load_sealed(None) == {}
