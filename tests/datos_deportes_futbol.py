"""Datos fijos y parches de fuentes del adaptador de fútbol del contrato `/deportes/v1/futbol`.

Los usan `test_deportes_v1.py` (suite de contrato), `test_deportes_futbol.py` y `test_deportes_futbol_paridad.py`.
Reproducen la FORMA real de cada fuente (`fichas._agenda`, `mobile.high_probability`,
`partido_mercados.destacados_resueltos`, `mobile.mercados_partido`), con valores de otra época (2031) para que ningún
estado dependa del reloj, y con centinelas en todo lo que NO puede salir por el contrato.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone

from qf.api import deportes_futbol, fichas, mobile, partido_mercados
from qf.api import deportes_v1 as dv

SELLO = 'b' * 64
DESDE = '2031-03-14'
CENTINELAS = ('CENTINELA_FIT', 'CENTINELA_XG', 'CENTINELA_VIP', 'CENTINELA_NOLIBRE', 'CENTINELA_BLOQUEADO',
              'CENTINELA_NOTA', 'CENTINELA_RACHA', 'CENTINELA_ERROR')


def utc(t: str) -> datetime:
    return datetime.fromisoformat(t.replace('Z', '+00:00'))


def _equipo(id_, nombre, *, escudo=True):
    return {'id': id_, 'nombre': nombre, 'escudo': f'/web/escudos/{id_}.png' if escudo else None,
            'posicion': 3, 'racha': 'CENTINELA_RACHA'}


def _partido(match_id, inicio, estado, liga, local, visitante, marcador=None):
    return {'match_id': match_id, 'kickoff_utc': utc(inicio), 'estado': estado, 'liga': liga,
            'marcador': marcador, 'local': local, 'visitante': visitante}


CHAMPIONS = {'id': 'eu.ucl', 'nombre': 'UEFA Champions League', 'pais': 'Europa'}
LALIGA = {'id': 'es.laliga', 'nombre': 'LaLiga', 'pais': 'España'}
LIGA_MX = {'id': 'mx.ligamx', 'nombre': 'Liga MX', 'pais': 'México'}

# m1 y m2 empiezan a la misma hora (desempate por id); m3 está terminado; m4 cae al día siguiente; m5 queda fuera de la
# ventana de dos días y está aplazado. m1 es un partido de Champions de un equipo de LaLiga: `league` debe ser la competición.
AGENDA = [
    _partido('eu.ucl:m1', f'{DESDE}T18:00:00Z', 'scheduled', CHAMPIONS, _equipo(1, 'Real Madrid'), _equipo(2, 'Manchester City')),
    _partido('es.laliga:m2', f'{DESDE}T18:00:00Z', 'scheduled', LALIGA, _equipo(3, 'Sevilla'), _equipo(4, 'Betis', escudo=False)),
    _partido('es.laliga:m3', f'{DESDE}T20:00:00Z', 'finished', LALIGA, _equipo(5, 'Girona', escudo=False),
             _equipo(6, 'Getafe', escudo=False), marcador=[2, 1]),
    _partido('mx.ligamx:m4', '2031-03-15T02:00:00Z', 'scheduled', LIGA_MX, _equipo(7, 'Tigres'), _equipo(8, 'Pumas')),
    _partido('mx.ligamx:m5', '2031-03-30T02:00:00Z', 'postponed', LIGA_MX, _equipo(9, 'León'), _equipo(10, 'Toluca')),
]


def _pick(match_id, key, market, selection, line, prob, texto, *, batch='2031-03-14', ref_price=1.4, book='pinnacle',
          local='Real Madrid', visitante='Manchester City', outcome=None, **extra):
    return {'match_id': match_id, 'league_id': match_id.split(':')[0], 'kickoff_utc': utc(f'{DESDE}T18:00:00Z'),
            'local': local, 'visitante': visitante, 'market': market, 'selection': selection, 'line': line,
            'prob': prob, 'ref_price': ref_price, 'ref_book': book, 'odds_as_of': utc(f'{DESDE}T10:00:00Z'),
            'batch_date': date.fromisoformat(batch), 'chain_sha256': SELLO, 'outcome': outcome,
            'home_goals': None, 'away_goals': None, 'texto': texto, 'local_escudo': '/web/escudos/1.png',
            'visitante_escudo': '/web/escudos/2.png', 'locked': False, 'free': True, 'pick_key': key,
            'started': False, 'xg': {'total': 'CENTINELA_XG'}, 'fair_price': 1.25, 'fit': 'CENTINELA_FIT', **extra}


PROXIMOS = [
    _pick('eu.ucl:m1', 'pk1', 'totals', 'over', 2.5, .8, 'Más de 2,5 goles'),
    # sellado DESPUÉS del inicio: eligible=False
    _pick('eu.ucl:m1', 'pk2', 'corners', 'over', 8.5, .76, 'Más de 8,5 córners', batch='2031-03-15', ref_price=None),
    # una fila que NO es gratis jamás sale, aunque venga en la lista
    _pick('eu.ucl:m1', 'CENTINELA_NOLIBRE', 'cards', 'over', 3.5, .9, 'CENTINELA_NOLIBRE', free=False),
    # sello que no es un sha256: la web (`publicForecasts`) tampoco la enseña
    _pick('es.laliga:m2', 'pk-sin-sello', 'btts', 'yes', None, .78, 'Marcan los dos', chain_sha256='no-es-un-hash'),
]
VIP = [{'match_id': 'eu.ucl:m1', 'league_id': 'eu.ucl', 'kickoff_utc': utc(f'{DESDE}T18:00:00Z'), 'local': 'Real Madrid',
        'visitante': 'Manchester City', 'batch_date': '2031-03-14', 'market': 'spreads', 'locked': True,
        'pick_key': f'CENTINELA_VIP_{i}', 'cuota': 1.9} for i in range(2)]
VIP += [{'match_id': 'mx.ligamx:m4', 'league_id': 'mx.ligamx', 'kickoff_utc': utc('2031-03-15T02:00:00Z'), 'local': 'Tigres',
         'visitante': 'Pumas', 'batch_date': '2031-03-14', 'market': 'totals', 'locked': True,
         'pick_key': 'CENTINELA_VIP_9', 'cuota': 1.7}]

RESUELTOS = [{'match_id': 'es.laliga:m3', 'league_id': 'es.laliga', 'kickoff_utc': utc(f'{DESDE}T20:00:00Z'), 'local': 'Girona',
              'visitante': 'Getafe', 'market': 'totals', 'selection': 'over', 'line': 1.5, 'texto': 'Más de 1,5 goles',
              'prob': .81, 'outcome': 'win', 'ref_price': 1.3, 'ref_book': 'Pinnacle', 'home_goals': 2, 'away_goals': 1,
              'local_escudo': None, 'visitante_escudo': None}]


def _fila(market, selection, line, prob, titulo, texto, *, cuota_tipo='justa', cuota=None, casa=None, **extra):
    return {'id': partido_mercados.clave(market, selection, line), 'grupo': 'X', 'titulo': titulo, 'market': market,
            'selection': selection, 'line': line, 'seleccion': texto, 'prob': prob, 'nivel': 'alta',
            'cuota': cuota or round(1 / prob, 2), 'cuota_tipo': cuota_tipo, 'casa': casa, 'nota': 'CENTINELA_NOTA',
            'oportunidad': True, 'locked': False, **extra}


MERCADOS_M1 = {'filas': [
    _fila('h2h', 'home', None, .55, 'Ganador del partido', 'Gana Real Madrid', cuota_tipo='casa', cuota=1.8, casa='bet365'),
    _fila('totals', 'over', 2.5, .8, 'Goles totales', 'Más de 2,5 goles'),      # = pk1: no se repite
    _fila('double_chance', '1X', None, .78, 'Doble oportunidad', 'Real Madrid o empate'),
    _fila('btts', 'yes', None, .6, 'Ambos marcan', 'Marcan los dos'),
    {'id': 'CENTINELA_BLOQUEADO', 'grupo': 'GOLES', 'locked': True},
], 'marcadores': None, 'destacado': None, 'rango': [1.2, None], 'abiertas': 4, 'total': 5}


class Fuentes:
    """Instala las fuentes falsas. `llamadas` registra lo que el adaptador les pide."""

    def __init__(self, mp):
        self.mp, self.llamadas = mp, {'alta': [], 'mercados': [], 'agenda': []}
        self.roto = False
        self.agenda = copy.deepcopy(AGENDA)
        self.proximos = copy.deepcopy(PROXIMOS)
        self.vip = copy.deepcopy(VIP)
        self.resueltos = copy.deepcopy(RESUELTOS)
        self.mercados = {'eu.ucl:m1': copy.deepcopy(MERCADOS_M1)}
        mp.setattr(fichas, '_agenda', self._agenda)
        mp.setattr(mobile, 'high_probability', self._alta)
        mp.setattr(mobile, 'mercados_partido', self._mercados)
        mp.setattr(partido_mercados, 'destacados_resueltos', self._resueltos)
        mp.setattr(deportes_futbol, 'query_one', self._query_one)

    def _falla(self):
        if self.roto:
            raise RuntimeError('fuente caída: CENTINELA_ERROR')

    def _agenda(self, inicio, fin, liga):
        self._falla()
        self.llamadas['agenda'].append((inicio, fin, liga))
        return copy.deepcopy([a for a in self.agenda if inicio <= a['kickoff_utc'] < fin])

    def _query_one(self, sql, params=()):
        self._falla()
        return next(({'kickoff_utc': a['kickoff_utc']} for a in self.agenda if a['match_id'] == params[0]), None)

    def _alta(self, plus=False, unlocks=None, started=False):
        self._falla()
        self.llamadas['alta'].append({'plus': plus, 'unlocks': unlocks, 'started': started})
        return {'estado': 'activa', 'motivos': [], 'historial': {'n': 0},
                'proximos': copy.deepcopy(self.proximos), 'vip': copy.deepcopy(self.vip)}

    def _mercados(self, match_id, ficha, picks, plus, web=False):
        self.llamadas['mercados'].append({'match_id': match_id, 'plus': plus, 'web': web, 'picks': [p['pick_key'] for p in picks],
                                          'ficha': ficha})
        return copy.deepcopy(self.mercados.get(match_id))

    def _resueltos(self, desde: date):
        self._falla()
        return copy.deepcopy(self.resueltos)


class ConFamiliasDelCatalogoDePrueba:
    """El catálogo de `test_deportes_v1.fijar_catalogo` usa familias de prueba (`fam_a`, `fam_b`, `fam_oculta`): este
    envoltorio solo traduce la familia del adaptador real a esas, para recorrer en la suite de contrato los mismos
    caminos (familia visible, oculta a la web y `otros`). La traducción real a las familias del catálogo de fútbol
    se prueba en `test_deportes_futbol.py` contra `catalogo_semilla`."""

    TRADUCCION = {'goals': 'fam_a', 'winner': 'fam_b', 'double_chance': 'fam_oculta'}

    def __init__(self, real):
        self._real = real

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)

    def familia_de(self, market):
        return self.TRADUCCION.get(self._real.familia_de(market), 'otros')


def instalar_para_suite(mp) -> Fuentes:
    fuentes = Fuentes(mp)
    mp.setitem(dv.ADAPTADORES, 'futbol', ConFamiliasDelCatalogoDePrueba(deportes_futbol.AdaptadorFutbol()))
    return fuentes


def instalar_real(mp) -> Fuentes:
    fuentes = Fuentes(mp)
    mp.setitem(dv.ADAPTADORES, 'futbol', deportes_futbol.AdaptadorFutbol())
    return fuentes
