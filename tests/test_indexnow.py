"""F2.4 del plan SEO: IndexNow. La ruta de la clave y el envío por lotes, sin red: HTTP y sitemap se simulan."""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from qf.api import indexnow, main, ratelimit

BASE = "https://pronosticosdeportivos.pro"
DOM = "pronosticosdeportivos.pro"
CLAVE = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
AHORA = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def carpeta(monkeypatch, tmp_path):
    monkeypatch.setenv("INDEXNOW_DIR", str(tmp_path))
    monkeypatch.setenv("DOMAIN", DOM)
    return tmp_path


@pytest.fixture
def client(monkeypatch, carpeta):
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


def sitemap(*filas):
    cuerpo = "".join(f"<url><loc>{u}</loc>{f'<lastmod>{m}</lastmod>' if m else ''}</url>" for u, m in filas)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{cuerpo}</urlset>'


class Red:
    """Sustituye al POST de IndexNow y guarda lo que se habría enviado."""
    def __init__(self, codigos=(200,)):
        self.codigos, self.peticiones = list(codigos), []

    def __call__(self, url, cuerpo):
        self.peticiones.append((url, cuerpo))
        return self.codigos.pop(0) if len(self.codigos) > 1 else self.codigos[0]


# --- la ruta de la clave --------------------------------------------------------------------------

def test_la_clave_se_sirve_solo_en_su_propio_archivo(client, carpeta):
    (carpeta / "clave.txt").write_text(CLAVE + "\n", encoding="utf-8")
    r = client.get(f"/{CLAVE}.txt")
    assert r.status_code == 200 and r.text == CLAVE and r.headers["content-type"].startswith("text/plain")
    assert r.headers["x-robots-tag"] == "noindex"
    for otra in ("/otra-clave.txt", "/ads.txt", "/a1b2c3d4e5f60718293a4b5c6d7e8f9.txt", f"/{CLAVE.upper()}.txt"):
        assert client.get(otra).status_code == 404, otra


def test_sin_clave_instalada_ningun_txt_responde(client):
    assert client.get(f"/{CLAVE}.txt").status_code == 404


def test_una_clave_mal_formada_no_se_sirve(client, carpeta):
    for mala in ("corta", "con espacios no vale aunque sea larga", "x" * 200, "clave/con/barras-largas-1234"):
        (carpeta / "clave.txt").write_text(mala, encoding="utf-8")
        assert indexnow.leer_clave() is None, mala
        assert client.get(f"/{mala}.txt").status_code in (404, 405, 422), mala


def test_no_tapa_a_robots_ni_al_resto_de_rutas(client, carpeta):
    (carpeta / "clave.txt").write_text(CLAVE, encoding="utf-8")
    robots = client.get("/robots.txt")
    assert robots.status_code == 200 and "User-agent" in robots.text and CLAVE not in robots.text
    assert client.get("/sitemap.xml").status_code == 200
    assert client.get("/health").status_code in (200, 503)


def test_la_ruta_va_la_ultima_del_orden():
    rutas = [getattr(r, "path", "") for r in main.app.routes]
    assert rutas.index("/{nombre}.txt") > rutas.index("/robots.txt")
    assert rutas.index("/{nombre}.txt") > rutas.index("/sitemap.xml")


# --- qué se envía ---------------------------------------------------------------------------------

def test_leer_el_sitemap():
    xml = sitemap((f"{BASE}/", None), (f"{BASE}/nba/", None), (f"{BASE}/nba/a-vs-b-2026-11-09/", "2026-11-09"))
    assert indexnow.leer_sitemap(xml) == {f"{BASE}/": None, f"{BASE}/nba/": None, f"{BASE}/nba/a-vs-b-2026-11-09/": "2026-11-09"}


def test_planificar_nuevas_cambiadas_y_sin_cambios():
    previo = {f"{BASE}/nba/ya-enviado/": {"lastmod": None, "enviada": AHORA.isoformat()},
              f"{BASE}/nba/previa/": {"lastmod": "2026-11-08", "enviada": AHORA.isoformat()}}
    actual = {f"{BASE}/nba/ya-enviado/": None,                  # igual: no se vuelve a enviar
              f"{BASE}/nba/previa/": None,                      # terminó (deja de llevar lastmod): cambió
              f"{BASE}/nba/nuevo/": "2026-11-09"}               # nuevo
    assert indexnow.planificar(previo, actual, AHORA, DOM) == [f"{BASE}/nba/previa/", f"{BASE}/nba/nuevo/"]


def test_los_pilares_se_reenvian_cada_6_horas_y_no_antes():
    antes = (AHORA - timedelta(hours=5)).isoformat()
    previo = {f"{BASE}/futbol/": {"lastmod": None, "enviada": antes}, f"{BASE}/nba/": {"lastmod": None, "enviada": (AHORA - timedelta(hours=7)).isoformat()}}
    actual = {f"{BASE}/futbol/": None, f"{BASE}/nba/": None}
    assert indexnow.planificar(previo, actual, AHORA, DOM) == [f"{BASE}/nba/"]


def test_solo_se_avisa_de_urls_del_propio_sitio_y_con_https():
    actual = {f"{BASE}/nba/": None, "https://otro-sitio.com/nba/": None, f"http://{DOM}/nba/x/": None, f"https://www.{DOM}/nba/y/": None}
    assert indexnow.planificar({}, actual, AHORA, DOM) == [f"{BASE}/nba/"]


# --- envío ----------------------------------------------------------------------------------------

def test_sin_enviar_solo_simula_y_no_escribe_nada(carpeta):
    (carpeta / "clave.txt").write_text(CLAVE, encoding="utf-8")
    red = Red()
    res = indexnow.ejecutar(enviar=False, ahora=AHORA, leer=lambda: sitemap((f"{BASE}/nba/", None), (f"{BASE}/nba/x-vs-y-2026-11-09/", "2026-11-09")), post=red)
    assert res["simulado"] and res["pendientes"] == 2 and res["enviadas"] == 0 and not red.peticiones
    assert not (carpeta / "estado.json").exists() and len(res["muestra"]) == 2


def test_el_envio_lleva_lo_que_pide_el_protocolo(carpeta):
    (carpeta / "clave.txt").write_text(CLAVE, encoding="utf-8")
    red = Red()
    urls = [(f"{BASE}/nba/x-vs-y-2026-11-09/", "2026-11-09"), (f"{BASE}/futbol/", None)]
    res = indexnow.ejecutar(enviar=True, ahora=AHORA, leer=lambda: sitemap(*urls), post=red)
    assert res["enviadas"] == 2 and res["fallidas"] == 0 and res["lotes"] == [200]
    (destino, cuerpo), = red.peticiones
    assert destino == "https://api.indexnow.org/IndexNow"
    assert cuerpo == {"host": DOM, "key": CLAVE, "keyLocation": f"{BASE}/{CLAVE}.txt", "urlList": [u for u, _ in urls]}
    estado = json.loads((carpeta / "estado.json").read_text(encoding="utf-8"))
    assert set(estado) == {u for u, _ in urls} and estado[urls[0][0]]["lastmod"] == "2026-11-09"
    # segundo pase sin cambios: no se envía nada
    red2 = Red()
    res2 = indexnow.ejecutar(enviar=True, ahora=AHORA + timedelta(minutes=30), leer=lambda: sitemap(*urls), post=red2)
    assert res2["pendientes"] == 0 and not red2.peticiones


def test_un_envio_fallido_no_se_da_por_hecho_y_se_reintenta(carpeta):
    (carpeta / "clave.txt").write_text(CLAVE, encoding="utf-8")
    u = [(f"{BASE}/nba/x-vs-y-2026-11-09/", "2026-11-09")]
    res = indexnow.ejecutar(enviar=True, ahora=AHORA, leer=lambda: sitemap(*u), post=Red([403]))
    assert res["fallidas"] == 1 and res["enviadas"] == 0
    assert json.loads((carpeta / "estado.json").read_text(encoding="utf-8")) == {}
    ok = indexnow.ejecutar(enviar=True, ahora=AHORA + timedelta(minutes=30), leer=lambda: sitemap(*u), post=Red([202]))
    assert ok["enviadas"] == 1 and ok["fallidas"] == 0                       # 202 también vale


def test_se_envia_por_lotes_y_se_para_si_hay_demasiadas_peticiones(carpeta, monkeypatch):
    (carpeta / "clave.txt").write_text(CLAVE, encoding="utf-8")
    monkeypatch.setattr(indexnow, "LOTE", 3)
    filas = [(f"{BASE}/nba/p{i}-vs-q{i}-2026-11-09/", "2026-11-09") for i in range(8)]
    red = Red([200])
    res = indexnow.ejecutar(enviar=True, ahora=AHORA, leer=lambda: sitemap(*filas), post=red)
    assert [len(c["urlList"]) for _, c in red.peticiones] == [3, 3, 2] and res["enviadas"] == 8
    otra = carpeta / "otra"
    monkeypatch.setenv("INDEXNOW_DIR", str(otra))
    (otra).mkdir(); (otra / "clave.txt").write_text(CLAVE, encoding="utf-8")
    red429 = Red([200, 429])
    res = indexnow.ejecutar(enviar=True, ahora=AHORA, leer=lambda: sitemap(*filas), post=red429)
    assert res["lotes"] == [200, 429] and res["enviadas"] == 3 and res["fallidas"] == 3            # se para tras el 429
    assert len(json.loads((otra / "estado.json").read_text(encoding="utf-8"))) == 3


def test_sin_clave_o_sin_sitemap_no_se_envia_nada(carpeta):
    red = Red()
    assert "sin clave" in indexnow.ejecutar(enviar=True, ahora=AHORA, leer=lambda: sitemap((f"{BASE}/nba/", None)), post=red)["error"]
    (carpeta / "clave.txt").write_text(CLAVE, encoding="utf-8")

    def roto():
        raise OSError("sin red")
    assert "sitemap no disponible" in indexnow.ejecutar(enviar=True, ahora=AHORA, leer=roto, post=red)["error"]
    assert "sitemap no disponible" in indexnow.ejecutar(enviar=True, ahora=AHORA, leer=lambda: "<no es xml", post=red)["error"]
    assert not red.peticiones and indexnow.main([]) in (0, 1)


def test_el_estado_corrupto_no_rompe_el_pase_y_se_olvidan_las_urls_viejas(carpeta):
    (carpeta / "clave.txt").write_text(CLAVE, encoding="utf-8")
    (carpeta / "estado.json").write_text("{esto no es json", encoding="utf-8")
    assert indexnow.ejecutar(enviar=True, ahora=AHORA, leer=lambda: sitemap((f"{BASE}/nba/", None)), post=Red())["enviadas"] == 1
    viejo = (AHORA - timedelta(days=31)).isoformat()
    (carpeta / "estado.json").write_text(json.dumps({f"{BASE}/nba/ya-no-esta/": {"lastmod": None, "enviada": viejo},
                                                     f"{BASE}/nba/reciente/": {"lastmod": None, "enviada": AHORA.isoformat()}}), encoding="utf-8")
    indexnow.ejecutar(enviar=True, ahora=AHORA, leer=lambda: sitemap((f"{BASE}/nba/", None)), post=Red())
    estado = json.loads((carpeta / "estado.json").read_text(encoding="utf-8"))
    assert f"{BASE}/nba/ya-no-esta/" not in estado and f"{BASE}/nba/reciente/" in estado


def test_el_modulo_solo_usa_la_biblioteca_estandar_para_hablar_con_la_red():
    import ast
    from pathlib import Path
    arbol = ast.parse(Path(indexnow.__file__).read_text(encoding="utf-8"))
    importados = {n.module.split(".")[0] if isinstance(n, ast.ImportFrom) else a.name.split(".")[0]
                  for n in ast.walk(arbol) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in (n.names if isinstance(n, ast.Import) else [n])}
    assert not importados & {"requests", "httpx", "aiohttp"}
