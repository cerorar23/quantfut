"""Servidor LOCAL simulado para probar la pantalla genérica de la app en el emulador (no es producción).

Uso: python tool/servidor_contrato_simulado.py 18765   (ver docs/PRUEBA_LOCAL_CONTRATO.md)

Sirve /cliente/v1/config con un deporte `golf` y las tres rutas del contrato /deportes/v1/golf/*.
Si existe `pantallas.json` junto a este archivo, se añade como campo `pantallas` de la configuración.
Registra cada petición en `$QF_SIM_LOG` (por omisión, el temporal del sistema). Todo lo demás responde 404.
"""
import json, os, re, sys, tempfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

AQUI = os.path.dirname(os.path.abspath(__file__))
LOG = os.environ.get('QF_SIM_LOG', os.path.join(tempfile.gettempdir(), 'peticiones_simuladas.log'))


def ahora():
    return datetime.now(timezone.utc)


def iso(d):
    return d.strftime('%Y-%m-%dT%H:%M:%SZ')


def config():
    cuerpo = {
        'contrato': 1,
        'deportes': [
            {'id': 'futbol', 'orden': 1, 'estado': 'on', 'nombre': {l: 'Fútbol' for l in ('es', 'en', 'pt', 'fr', 'it', 'de')},
             'slug': {'es': 'futbol'}, 'icono': 'futbol', 'color': '#00d58b', 'secciones': ['high', 'ladder', 'parley'], 'familias': []},
            {'id': 'golf', 'orden': 2, 'estado': 'on',
             'nombre': {'es': 'Golf', 'en': 'Golf', 'pt': 'Golfe', 'fr': 'Golf', 'it': 'Golf', 'de': 'Golf'},
             'slug': {'es': 'golf'}, 'icono': 'golf', 'color': '#2e9e4f', 'secciones': ['high'],
             'familias': [
                 {'id': 'demo_resultado', 'orden': 1, 'nombre': {'es': 'Resultado', 'en': 'Result', 'pt': 'Resultado', 'fr': 'Résultat', 'it': 'Risultato', 'de': 'Ergebnis'}, 'subtitulo': {}},
                 {'id': 'demo_totales', 'orden': 2, 'nombre': {'es': 'Totales', 'en': 'Totals', 'pt': 'Totais', 'fr': 'Totaux', 'it': 'Totali', 'de': 'Gesamt'}, 'subtitulo': {}},
             ]},
        ],
    }
    ruta = os.path.join(AQUI, 'pantallas.json')
    if os.path.exists(ruta):
        cuerpo['pantallas'] = json.load(open(ruta, encoding='utf-8'))
    return cuerpo


MERCADOS = (
    ('demo_ganador_a', 'demo_resultado', 'Demo · Gana Equipo A', 'a', 0.45, 'win'),
    ('demo_ganador_b', 'demo_resultado', 'Demo · Gana Equipo B', 'b', 0.35, 'loss'),
    ('demo_total_mas', 'demo_totales', 'Demo · Más de 2.5', 'over', 0.62, 'win'),
    ('demo_total_menos', 'demo_totales', 'Demo · Menos de 2.5', 'under', 0.38, 'loss'),
    ('demo_ambos_si', 'demo_especiales', 'Demo · Ambos anotan', 'yes', 0.60, 'win'),
)
EVENTOS = (('demo-1', -150, 'finished', '2-1'), ('demo-2', -60, 'finished', '0-3'),
           ('demo-3', 90, 'scheduled', None), ('demo-4', 20 * 60, 'scheduled', None))


def evento(fila, completo):
    id, minutos, estado, marcador = fila
    fin = estado == 'finished'
    ms = [{'id': f'{id}:{c}', 'label': et, 'selection': sel, 'probability': p, 'sealed_at': iso(ahora() - timedelta(hours=30)),
           'eligible': True, 'market': c, 'family': fam, 'line': None, 'player': None, 'player_id': None, 'price': None,
           'reference': None, 'outcome': res if fin else None, 'push_probability': None, 'principal': c == 'demo_ganador_a'}
          for c, fam, et, sel, p, res in MERCADOS]
    if not completo:
        ms = [m for m in ms if m['principal'] or m['id'] == f'{id}:demo_total_mas']
    return {'id': id, 'sport': 'golf', 'home': 'Equipo A', 'away': 'Equipo B', 'league': 'Demostración (servidor local)',
            'start': iso(ahora() + timedelta(minutes=minutos)), 'status': estado, 'seal': 'a1b2c3d4e5f60718293a4b5c6d7e8f90',
            'sealed_at': iso(ahora() - timedelta(hours=30)), 'planned_seal': None, 'score': marcador, 'surface': None,
            'bloqueados': 0, 'imagenes': None, 'markets': ms, 'destacado': f'{id}:demo_total_mas', 'team_projection': None}


TEXTOS = {
    'es': ('Tabla demo', 'Barras demo', 'Pares demo', 'Nota demo', 'Equipo', 'Valor', 'Racha', 'Líder'),
    'en': ('Demo table', 'Demo bars', 'Demo pairs', 'Demo note', 'Team', 'Value', 'Streak', 'Leader'),
    'pt': ('Tabela demo', 'Barras demo', 'Pares demo', 'Nota demo', 'Equipe', 'Valor', 'Sequência', 'Líder'),
}


def bloques(lang):
    t = TEXTOS.get(lang, TEXTOS['es'])
    return [
        {'id': 'demo_tabla', 'tipo': 'tabla', 'titulo': t[0], 'columnas': [t[4], t[5]], 'filas': [['Equipo A', 12], ['Equipo B', 9.5]]},
        {'id': 'demo_barras', 'tipo': 'barras', 'titulo': t[1], 'items': [{'etiqueta': 'A', 'valor': 0.6}, {'etiqueta': 'B', 'valor': 0.3, 'nota': 'nota'}]},
        {'id': 'demo_pares', 'tipo': 'pares', 'titulo': t[2], 'items': [{'etiqueta': t[6], 'valor': 7}, {'etiqueta': t[7], 'valor': 'Equipo B'}]},
        {'id': 'demo_texto', 'tipo': 'texto', 'titulo': t[3], 'cuerpo': f'{t[3]}: <b>texto plano</b> & sin HTML.'},
        {'id': 'demo_futuro', 'tipo': 'mapa', 'titulo': 'Tipo desconocido', 'puntos': []},
    ]


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def responder(self, cuerpo, estado=200):
        data = json.dumps(cuerpo).encode()
        self.send_response(estado)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(f'{datetime.now():%H:%M:%S} GET {self.path}\n')
        if u.path == '/cliente/v1/config':
            return self.responder(config())
        m = re.fullmatch(r'/deportes/v1/golf/cartelera', u.path)
        if m:
            return self.responder({'contrato': 1, 'deporte': 'golf', 'desde': q.get('desde'), 'dias': 7,
                                   'eventos': [evento(f, False) for f in EVENTOS]})
        m = re.fullmatch(r'/deportes/v1/golf/partido/([\w-]+)', u.path)
        if m:
            fila = next((f for f in EVENTOS if f[0] == m.group(1)), None)
            if not fila:
                return self.responder({'detail': 'no'}, 404)
            return self.responder({'contrato': 1, 'deporte': 'golf', 'evento': evento(fila, True), 'bloques': bloques(q.get('lang', 'es'))})
        m = re.fullmatch(r'/deportes/v1/golf/partido/([\w-]+)/mercados', u.path)
        if m:
            fila = next((f for f in EVENTOS if f[0] == m.group(1)), None)
            if not fila:
                return self.responder({'detail': 'no'}, 404)
            ev = evento(fila, True)
            grupos = {}
            for mk in ev['markets']:
                grupos.setdefault(mk['family'], []).append(mk)
            return self.responder({'contrato': 1, 'deporte': 'golf', 'evento_id': fila[0],
                                   'familias': [{'id': k, 'mercados': v} for k, v in grupos.items() if k != 'demo_especiales']})
        self.responder({'detail': 'no encontrado'}, 404)


if __name__ == '__main__':
    open(LOG, 'w').close()
    ThreadingHTTPServer(('0.0.0.0', int(sys.argv[1]) if len(sys.argv) > 1 else 8765), H).serve_forever()
