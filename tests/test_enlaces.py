"""F3.3 del plan SEO: enlaces reales entre deportes. Reutiliza los datos simulados de las pruebas de og (NBA, fútbol y tenis)."""
import re
from pathlib import Path

import test_futbol_paginas as tf
import test_nba_paginas as tn
import test_tenis_paginas as tt
from test_og import client  # noqa: F401  (fixture con los tres deportes simulados)
from test_paginas import Doc

HTML = {"accept": "text/html,application/xhtml+xml"}
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
PILARES = {"/nba/", "/futbol/", "/tenis/"}


def test_cada_pilar_y_cada_partido_enlazan_a_los_otros_dos_deportes(client):  # noqa: F811
    for ruta, propio in (("/nba/", "/nba/"), ("/futbol/", "/futbol/"), ("/tenis/", "/tenis/"),
                         (f"/nba/{tn.SLUG_FINAL}/", "/nba/"), (tf.URL_FINAL, "/futbol/"), (tt.U_ACIERTO, "/tenis/")):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 200, ruta
        hrefs = set(Doc(r.text).hrefs)
        assert (PILARES - {propio}) <= hrefs, (ruta, PILARES - {propio} - hrefs)


def test_las_secciones_y_la_portada_enlazan_a_los_tres_pilares(client):  # noqa: F811
    for ruta in ("/", "/historial/", "/planes/", "/metodologia/"):
        assert PILARES <= set(Doc(client.get(ruta, headers=HTML).text).hrefs), ruta


def test_el_selector_de_deporte_de_la_app_lleva_enlaces_reales():
    """Antes apuntaba a `#picks` para los tres deportes: Google no podía seguirlos. El clic sigue interceptado (preventDefault)."""
    app = (FRONTEND / "app.js").read_text(encoding="utf-8")
    nav = re.search(r'<nav class="sport-nav".*?</nav>`', app, re.S).group(0)
    assert 'href="/${slug}/" data-sport="${id}"' in nav and 'href="#picks"' not in nav
    assert "button?.matches('a[data-sport]'))event.preventDefault()" in app


def test_el_pie_de_la_app_enlaza_a_los_pilares():
    app = (FRONTEND / "app.js").read_text(encoding="utf-8")
    pie = re.search(r"function siteFooter\(\) \{(.*?)\n\}\n", app, re.S).group(1)
    assert {h for h in re.findall(r'<a href="([^"]+)"', pie)} >= PILARES
