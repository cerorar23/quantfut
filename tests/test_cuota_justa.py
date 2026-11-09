"""F4.2: `/calculadora-cuota-justa/`. Sin base ni red.

Lo importante: el cálculo existe en TRES sitios (este módulo de referencia, el JavaScript de la página y el de-vig del motor) y deben
decir lo mismo. Los vectores de `datos_cuota_justa.json` los comparten esta prueba y `frontend/cuota-justa.test.mjs`.
"""
import json
import math
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from qf.api import cuota_justa, main, ratelimit

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
DATOS = json.loads((Path(__file__).with_name("datos_cuota_justa.json")).read_text(encoding="utf-8"))
TOL = 1e-9


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


def casi(a, b, tol=TOL):
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


# --- el cálculo ----------------------------------------------------------------------------------

@pytest.mark.parametrize("caso", DATOS["metodos"], ids=lambda c: "-".join(str(x) for x in c["cuotas"]))
def test_vectores_compartidos_al_dia(caso):
    """Si cambia el algoritmo, hay que regenerar `datos_cuota_justa.json`: lo que comprueba el JavaScript es esto."""
    assert abs(cuota_justa.sobreredondeo(caso["cuotas"]) - caso["sobreredondeo"]) <= TOL
    for m in ("proporcional", "shin", "potencia"):
        p = cuota_justa.sin_margen(caso["cuotas"], m)
        assert casi(p, caso[m]), m
        assert abs(sum(p) - 1.0) <= 1e-9, m
        assert all(0.0 < x < 1.0 for x in p)


@pytest.mark.parametrize("caso", DATOS["metodos"], ids=lambda c: "-".join(str(x) for x in c["cuotas"]))
def test_coincide_con_el_devig_del_motor(caso):
    """La calculadora no puede enseñar al lector algo distinto de lo que hace el motor."""
    pytest.importorskip("scipy")
    import numpy as np
    from qf.model import devig
    cuotas = caso["cuotas"]
    assert abs(devig.overround(np.asarray(cuotas)) - caso["sobreredondeo"]) <= 1e-9
    for ours, theirs in (("proporcional", "multiplicative"), ("shin", "shin"), ("potencia", "power")):
        assert casi(cuota_justa.sin_margen(cuotas, ours), list(devig.devig(cuotas, theirs)), 1e-7), ours


def test_sin_margen_no_cambia_nada():
    for m in ("proporcional", "shin", "potencia"):
        assert casi(cuota_justa.sin_margen([2.0, 2.0], m), [0.5, 0.5])
        assert casi(cuota_justa.sin_margen([3.0, 3.0, 3.0], m), [1 / 3] * 3)


def test_shin_quita_menos_al_favorito_que_el_proporcional_al_reves():
    """El sesgo favorito-longshot: con margen, Shin da MÁS probabilidad al favorito y menos al muy improbable que el reparto proporcional."""
    c = [1.20, 6.0, 15.0]
    prop, sh = cuota_justa.proporcional(c), cuota_justa.shin(c)
    assert sh[0] > prop[0] and sh[2] < prop[2]


def test_cuota_justa_es_el_inverso():
    assert cuota_justa.cuota_justa(0.5) == 2.0
    assert cuota_justa.cuota_justa(0.25) == 4.0
    assert cuota_justa.cuota_justa(0) == math.inf


@pytest.mark.parametrize("malas", [[1.0, 2.0], [0.5, 3.0], [2.0], [], [float("nan"), 2.0], [float("inf"), 2.0], [-2.0, 2.0]])
def test_cuotas_invalidas_se_rechazan(malas):
    with pytest.raises(ValueError):
        cuota_justa.shin(malas)


def test_ejemplo_resuelto_sale_del_calculo():
    ej = cuota_justa.ejemplo()
    d = ej["datos"]
    assert d["cuotas"] == [c for _, c in cuota_justa.EJEMPLO]
    assert casi(d["sin_margen"], cuota_justa.shin(d["cuotas"]))
    for f, p in zip(ej["filas"], d["sin_margen"]):
        assert f["sin_margen"] == cuota_justa.pct(p)
        assert f["justa"] == cuota_justa.n2(1 / p)
    assert ej["margen"] == cuota_justa.pct(d["total"] - 1)


# --- la página ------------------------------------------------------------------------------------

def test_pagina_200_con_su_politica_y_su_cabeza(client):
    r = client.get("/calculadora-cuota-justa/", headers=HTML)
    assert r.status_code == 200
    csp = r.headers["content-security-policy"]
    assert "default-src 'none'" in csp and "script-src 'self'" in csp
    script = next(d for d in csp.split("; ") if d.startswith("script-src"))
    assert "unsafe-inline" not in script and "unsafe-eval" not in script and "http" not in script
    assert "connect-src" not in csp                      # la calculadora no envía nada a ningún sitio
    assert "content-security-policy-report-only" not in r.headers
    assert "x-robots-tag" not in r.headers
    t = r.text
    assert f'<link rel="canonical" href="{BASE}/calculadora-cuota-justa/">' in t
    assert 'name="robots" content="index, follow' in t
    assert "<title>Calculadora de cuota justa" in t
    assert '"@type": "BreadcrumbList"' in t or '"@type":"BreadcrumbList"' in t


def test_solo_un_script_propio_y_ninguno_en_linea(client):
    t = client.get("/calculadora-cuota-justa/", headers=HTML).text
    etiquetas = re.findall(r"<script\b([^>]*)>", t)
    propios = [e for e in etiquetas if "application/ld+json" not in e]
    assert len(propios) == 1
    assert 'type="module"' in propios[0]
    assert re.search(r'src="/static/cuota-justa\.js\?v=[0-9a-f]{10}"', propios[0])
    assert "onclick" not in t and "onchange" not in t and "oninput" not in t and "javascript:" not in t
    assert "fbevents" not in t


def test_el_script_se_sirve_como_javascript(client):
    r = client.get("/static/cuota-justa.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    assert "export function shin" in r.text


def test_ejemplo_sin_javascript_trae_las_cifras_del_calculo(client):
    t = client.get("/calculadora-cuota-justa/", headers=HTML).text
    ej = cuota_justa.ejemplo()
    for f in ej["filas"]:
        assert f"<tr><th scope=\"row\">{f['nombre']}</th><td>{f['cuota']}</td><td>{f['implicita']}</td><td>{f['sin_margen']}</td><td>{f['justa']}</td></tr>" in t
    assert ej["suma"] in t and ej["margen"] in t
    assert "<noscript>" in t


def test_accesible_y_sin_promesas(client):
    t = client.get("/calculadora-cuota-justa/", headers=HTML).text
    for ident in ("cj-formato", "cj-cuota", "cj-prob", "cj-n", "cj-metodo", "cj-o0", "cj-o1", "cj-o2"):
        assert re.search(rf'<label for="{ident}"', t), ident            # todo campo tiene su etiqueta
    assert t.count('aria-live="polite"') >= 3
    assert "Herramienta educativa" in t and "/juego-responsable/" in t
    minus = t.lower()
    for prohibido in ("kelly", "bankroll", "stake", "apuesta segura", "pick seguro", "ganancia asegurada", "dinero fácil"):
        assert prohibido not in minus, prohibido


def test_enlazada_y_en_el_mapa(client):
    mapa = client.get("/sitemap-paginas.xml").text
    assert f"<loc>{BASE}/calculadora-cuota-justa/</loc>" in mapa
    assert "<lastmod>2026-11-09</lastmod>" in mapa[mapa.index("calculadora-cuota-justa"):][:200]
    assert 'href="/calculadora-cuota-justa/"' in client.get("/metodologia/", headers=HTML).text
    assert 'href="/calculadora-cuota-justa/"' in client.get("/calibracion/", headers=HTML).text or client.get("/calibracion/", headers=HTML).status_code == 503


def test_sin_barra_redirige_y_head_responde(client):
    r = client.get("/calculadora-cuota-justa?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}/calculadora-cuota-justa/?x=1"
    assert client.head("/calculadora-cuota-justa/").status_code == 200
