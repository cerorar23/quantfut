"""Paridad del adaptador de fútbol con `football()` de la web (`frontend/ergonomic-views.js`).

Con los MISMOS datos de entrada, los eventos del contrato coinciden con los que construye `football()`: mismos `id`,
`home`, `away`, `start`, `league`, `bloqueados` (= `locked_count`), `probability` de cada mercado y `outcome` de los
destacados resueltos. `football()` es una función interna de `createHubViews`: el script de Node extrae su texto del
archivo real (sin tocar `frontend/`) y la ejecuta con el `publicForecasts` real de `fichas-data.js`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

import datos_deportes_futbol as datos
from qf.api.deportes_futbol import AdaptadorFutbol

RAIZ = Path(__file__).resolve().parents[1]
FRONT = RAIZ / 'frontend'

SCRIPT = """
import fs from 'node:fs';
import { publicForecasts } from '%(fichas)s';
const src = fs.readFileSync('%(vistas)s', 'utf8');
const ini = src.indexOf('function football(entry)');
let prof = 0, fin = -1;
for (let k = src.indexOf('{', ini); k < src.length; k++) {
  if (src[k] === '{') prof++;
  else if (src[k] === '}' && --prof === 0) { fin = k + 1; break; }
}
const football = new Function('publicForecasts', 'results', src.slice(ini, fin) + '; return football;');
const entrada = JSON.parse(fs.readFileSync(0, 'utf8'));
const f = football(publicForecasts, () => ({ featured: entrada.featured }));
process.stdout.write(JSON.stringify(f({ status: 'ready', data: entrada.home })));
"""


def _json(o):
    return json.loads(json.dumps(o, default=lambda v: v.isoformat() if hasattr(v, 'isoformat') else str(v)))


def _football(fuentes, tmp_path) -> list[dict]:
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node no está instalado: la paridad con football() se comprueba en CI (job frontend/arnes)')
    script = tmp_path / 'football.mjs'
    script.write_text(SCRIPT % {'fichas': (FRONT / 'fichas-data.js').as_uri(),
                                'vistas': (FRONT / 'ergonomic-views.js').as_posix()}, encoding='utf-8')
    entrada = _json({'home': {'agenda': fuentes.agenda, 'alta_probabilidad': {'proximos': fuentes.proximos, 'vip': fuentes.vip}},
                     'featured': fuentes.resueltos})
    salida = subprocess.run([node, str(script)], input=json.dumps(entrada), capture_output=True, text=True,
                            encoding='utf-8', cwd=str(RAIZ), timeout=60)
    assert salida.returncode == 0, salida.stderr
    return json.loads(salida.stdout)


def _t(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace('Z', '+00:00')).astimezone(timezone.utc)


@pytest.fixture
def fuentes(monkeypatch):
    f = datos.instalar_real(monkeypatch)
    # Filas que la fuente real nunca emite en `proximos` con plus=False (no gratis, o sin sha256 válido): el adaptador las
    # descarta por seguridad y `football()` las enseñaría. La paridad se mide con lo que la fuente SÍ puede entregar.
    f.proximos = [r for r in f.proximos if r['free'] and len(r['chain_sha256']) == 64]
    return f


def test_los_eventos_del_contrato_coinciden_con_football(fuentes, tmp_path):
    web = {e['id']: e for e in _football(fuentes, tmp_path)}
    ini = datetime.fromisoformat(datos.DESDE + 'T00:00:00+00:00')
    fin = ini.replace(day=31)
    contrato = {e.id: e for e in AdaptadorFutbol().cartelera(ini, fin)}
    assert set(web) == {'eu.ucl:m1', 'es.laliga:m3', 'mx.ligamx:m4'}, 'football() crea un evento por pick, destacado y candado'
    assert set(web) <= set(contrato)            # el contrato trae además los partidos de la agenda sin pronóstico público
    for id_, w in web.items():
        c = contrato[id_]
        assert (c.home, c.away, c.league) == (w['home'], w['away'], w['league']), id_
        assert c.start == _t(w['start']), id_
        assert c.bloqueados == w['locked_count'], id_
        assert c.sport == w['sport'] == 'futbol'


def test_probabilidades_y_resultados_de_los_mercados_coinciden(fuentes, tmp_path):
    web = {e['id']: e for e in _football(fuentes, tmp_path)}
    for id_, w in web.items():
        detalle = {m.id: m for m in AdaptadorFutbol().partido(id_).markets}
        assert w['markets'] or id_ == 'mx.ligamx:m4'          # m4 solo tiene candado
        for m in w['markets']:
            mercado = detalle[m['id']]                         # mismo id: pick_key, o `destacado:<partido>`
            assert mercado.probability == m['probability'], m['id']
            assert mercado.selection == m['selection'], m['id']
            assert mercado.outcome == m.get('outcome'), m['id']
            assert mercado.price == m.get('price') or m.get('model') or m.get('price') is None
    # el destacado resuelto: mismo id, probabilidad, selección y resultado que la tarjeta de la web
    resuelto = next(m for m in web['es.laliga:m3']['markets'] if m['featured'])
    ev = AdaptadorFutbol().partido('es.laliga:m3')
    assert ev.destacado == resuelto['id'] and ev.score == web['es.laliga:m3']['score']
    assert next(m for m in ev.markets if m.id == ev.destacado).outcome == resuelto['outcome'] == 'win'


def test_la_cartelera_trae_los_mismos_picks_publicos_que_football(fuentes, tmp_path):
    web = {e['id']: e for e in _football(fuentes, tmp_path)}
    ids_web = {m['id'] for m in web['eu.ucl:m1']['markets']}
    assert ids_web == {'pk1', 'pk2'}
    ev = AdaptadorFutbol().partido('eu.ucl:m1')
    assert {m.id for m in ev.markets if m.id.startswith('pk')} == ids_web
