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


def test_excepcion_inesperada_no_disponible_y_no_se_cachea(tmp_path, monkeypatch, entorno):
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
    entorno.t = NOW + timedelta(seconds=6)  # pasado el reposo tras el fallo
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


# ---- tamaño, gzip, tope y respuesta rancia ----------------------------------------------------------------------
def test_se_omiten_las_entradas_sin_precio(tmp_path, monkeypatch):
    monta_nba(tmp_path)
    body = client.get(NBA, headers={"Accept-Encoding": "identity"}).json()
    quotes = body["events"]["0022600100"]["quotes"]
    assert quotes and all(any(v is not None for v in row.values()) for row in quotes.values())
    # tenis: sin mercados con precio, el evento no aparece
    monta_tenis(tmp_path, monkeypatch)
    t = client.get(TENIS).json()
    assert all(q is not None for mk in t["events"].values() for q in mk.values())
    assert "tiebreak" not in t["events"]["1"]


def test_json_compacto_y_sin_gzip_sin_cabecera(tmp_path):
    monta_nba(tmp_path)
    r = client.get(NBA, headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in r.headers and r.headers["vary"] == "Accept-Encoding"
    assert r.content == json.dumps(r.json(), separators=(",", ":"), ensure_ascii=False).encode()
    assert r.headers["content-type"].startswith("application/json")


def test_gzip_si_el_cliente_lo_acepta(tmp_path):
    import gzip
    monta_nba(tmp_path)
    plano = client.get(NBA, headers={"Accept-Encoding": "identity"}).content
    r = client.get(NBA, headers={"Accept-Encoding": "gzip"})
    assert r.headers["content-encoding"] == "gzip" and r.headers["vary"] == "Accept-Encoding"
    assert r.headers["cache-control"] == "no-store" and r.content == plano  # httpx descomprime
    con_q0 = client.get(NBA, headers={"Accept-Encoding": "gzip;q=0"})
    assert "content-encoding" not in con_q0.headers
    assert gzip.decompress(cw._obtener("nba", lambda: None).gz) == plano


def test_tope_de_tamano_descarta_las_cohortes_mas_antiguas(monkeypatch):
    def evento(cohorte, sellado):
        return dict(cohort=cohorte, sealed_at=sellado, recalculated_at=None,
                    quotes={f"player_points|{i}|24.5": dict(over=dict(price=1.9, book="x", as_of="t", books=2,
                                                                      side="over"), under=None) for i in range(20)})

    falso = dict(state="ok", generated_at="g", source="PropLine", events={
        "viejo": evento("20261028-a", "2026-10-28T00:00:00Z"), "medio": evento("20261029-a", "2026-10-29T00:00:00Z"),
        "nuevo": evento("20261030-a", "2026-10-30T00:00:00Z")})
    un_evento = len(cw._json(falso["events"]["viejo"])) + 10
    monkeypatch.setattr(cw, "MAX_BYTES", un_evento * 2 + 300)
    monkeypatch.setattr(cw, "nba_overlay", lambda *a, **k: falso)
    body = client.get(NBA, headers={"Accept-Encoding": "identity"}).json()
    assert body["truncated"] is True and body["state"] == "partial"
    assert list(body["events"]) == ["medio", "nuevo"] or list(body["events"]) == ["nuevo"]
    assert "viejo" not in body["events"] and "nuevo" in body["events"]
    assert len(client.get(NBA, headers={"Accept-Encoding": "identity"}).content) <= cw.MAX_BYTES


def test_dentro_del_tope_no_hay_marca_truncated(tmp_path):
    monta_nba(tmp_path)
    assert "truncated" not in client.get(NBA).json()


def test_tamano_en_la_fixture_multicohorte(tmp_path, capsys):
    prop = tn.archivo(tmp_path / "arch")
    raiz = tmp_path / "cohorts"
    for i in range(3):
        c = tn.cohorte(prop)
        c["games"][0] = dict(c["games"][0], event_id=f"00226001{i:02d}", nba_game_id=f"00226001{i:02d}")
        for f in c["forecasts"]:
            f["event_id"] = f["nba_game_id"] = f"00226001{i:02d}"
        c["created_at_utc"] = tn.pl.stamp(tn.SEALED + timedelta(minutes=i))
        bundle = {k: v for k, v in c.items() if k != "cohort"}
        sha = tn._escribe(raiz / f"20261030-{i}" / "bundle.json", bundle)
        tn._escribe(raiz / f"20261030-{i}" / "bundle.seal.json", dict(sha256=sha, created_at_utc=c["created_at_utc"]))
    plano = client.get(NBA, headers={"Accept-Encoding": "identity"})
    body = plano.json()
    filas = sum(len(e["quotes"]) for e in body["events"].values())
    gz = client.get(NBA, headers={"Accept-Encoding": "gzip"}).headers.get("content-length")
    print(f"MEDIDA cohortes=3 eventos={len(body['events'])} filas_con_precio={filas} bytes={len(plano.content)} gz={gz}")
    assert len(body["events"]) == 3 and filas > 0 and len(plano.content) < 20_000


def _espera(cond, seg=5):
    fin = time.time() + seg
    while time.time() < fin:
        if cond():
            return True
        time.sleep(.01)
    return False


def _bloqueable(monkeypatch):
    """nba_overlay controlado: `libera` lo suelta; `llamadas` cuenta ejecuciones."""
    libera, llamadas, real = threading.Event(), [], cn.nba_overlay

    def lento(*a, **k):
        llamadas.append(1)
        libera.wait(10)
        return real(*a, **k)

    monkeypatch.setattr(cw, "nba_overlay", lento)
    return libera, llamadas


def test_calculo_lento_sin_resultado_previo_no_cuelga(tmp_path, monkeypatch):
    monta_nba(tmp_path)
    monkeypatch.setattr(cw, "ESPERA_MAX", .2)
    libera, llamadas = _bloqueable(monkeypatch)
    t0 = time.time()
    r = client.get(NBA)
    assert time.time() - t0 < 2 and r.status_code == 200 and r.json()["state"] == "unavailable"
    r2 = client.get(NBA)  # el cálculo sigue en curso: no se lanza otro
    assert r2.status_code == 200 and r2.json()["state"] == "unavailable" and len(llamadas) == 1
    libera.set()
    assert _espera(lambda: client.get(NBA).json()["state"] == "ok")


def test_en_frio_solo_espera_quien_lanza_el_calculo(tmp_path, monkeypatch):
    monta_nba(tmp_path)
    monkeypatch.setattr(cw, "ESPERA_MAX", 5)
    libera, llamadas = _bloqueable(monkeypatch)
    primero = threading.Thread(target=lambda: client.get(NBA), daemon=True)
    primero.start()
    assert _espera(lambda: len(llamadas) == 1)
    t0 = time.time()
    r = client.get(NBA)  # no ocupa un hilo esperando: responde al instante
    assert time.time() - t0 < 1 and r.json()["state"] == "unavailable" and len(llamadas) == 1
    libera.set()
    primero.join(5)


def test_se_sirve_la_ultima_buena_mientras_recalcula(tmp_path, monkeypatch, entorno):
    monta_nba(tmp_path)
    buena = client.get(NBA).json()
    entorno.t = NOW + timedelta(seconds=90)  # caducada, pero dentro de STALE_MAX
    monkeypatch.setattr(cw, "ESPERA_MAX", .2)
    libera, llamadas = _bloqueable(monkeypatch)
    r = client.get(NBA)  # arranca el recálculo y, al agotarse la espera, sirve la rancia
    assert r.json() == buena
    t0 = time.time()
    assert client.get(NBA).json() == buena and time.time() - t0 < .15 and len(llamadas) == 1
    libera.set()
    assert _espera(lambda: client.get(NBA).json()["generated_at"] == (NOW + timedelta(seconds=90)).isoformat())


def test_la_rancia_mas_vieja_que_stale_max_no_se_sirve(tmp_path, monkeypatch, entorno):
    monta_nba(tmp_path)
    client.get(NBA)
    entorno.t = NOW + timedelta(seconds=901)
    monkeypatch.setattr(cw, "ESPERA_MAX", .2)
    libera, _ = _bloqueable(monkeypatch)
    r = client.get(NBA)
    assert r.status_code == 200 and r.json()["state"] == "unavailable"
    libera.set()


def test_tras_un_fallo_solo_un_reintento_pasado_el_reposo(tmp_path, monkeypatch, entorno):
    monta_nba(tmp_path)
    n = []

    def falla(*a, **k):
        n.append(1)
        time.sleep(.2)
        raise RuntimeError("boom")

    monkeypatch.setattr(cw, "nba_overlay", falla)
    out = []
    hilos = [threading.Thread(target=lambda: out.append(client.get(NBA).json()["state"])) for _ in range(6)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert out == ["unavailable"] * 6 and len(n) == 1
    assert client.get(NBA).json()["state"] == "unavailable" and len(n) == 1  # dentro del reposo de 5 s
    entorno.t = NOW + timedelta(seconds=6)
    client.get(NBA)
    assert len(n) == 2


def test_feed_publico_de_tenis_que_falla_es_no_disponible(tmp_path, monkeypatch):
    def rompe():
        raise FileNotFoundError("tennis.json")

    monkeypatch.setattr(tp, "public_data", rompe)
    (tmp_path / "sellos").mkdir()
    (tmp_path / "arch").mkdir()
    r = client.get(TENIS)
    assert r.status_code == 200 and r.json()["state"] == "unavailable" and r.headers["cache-control"] == "no-store"
