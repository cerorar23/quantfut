"""Datos fijos de NBA para la suite de contrato `/deportes/v1` y las pruebas del adaptador (sin red ni base).

Instala una `nba-api` falsa en `nba_datos._pedir`: cartelera por fecha ET y `/partido/{id}/mercados`.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from qf.api import deportes_nba, nba_datos

AHORA = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)      # 07:00 ET del 13-nov
HOY_ET = date(2026, 11, 13)
SELLO_A, SELLO_B, SELLO_C = 'a' * 64, 'b' * 64, 'c' * 64
PARTIDO_ID = '103'


def partido(pid, local, visit, fecha, inicio, p_local=0.62, resultado=None, sellado='antes', hash_=SELLO_A,
            sello_previsto=None):
    """`sellado`: 'antes' (una hora antes del inicio), 'despues' (una hora tras el inicio) o None (sin pronóstico)."""
    pron = None
    if sellado:
        ini = datetime.fromisoformat(inicio)
        delta = -3600 if sellado == 'antes' else 3600
        pron = {'hash': hash_, 'p_local': p_local, 'sellado_en': datetime.fromtimestamp(ini.timestamp() + delta, timezone.utc).isoformat(),
                'mu': [111.7, 116.4], 'escenarios': {'privado': 'CENTINELA_FIT'}}
    return {'id': pid, 'fecha': fecha, 'local': {'codigo': local[:3].upper(), 'nombre': local},
            'visitante': {'codigo': visit[:3].upper(), 'nombre': visit}, 'inicio_utc': inicio,
            'sello_previsto': sello_previsto, 'resultado': resultado, 'pronostico': pron}


# Claves = fecha ET. El 100 y el 101 empiezan a la misma hora (desempate por id); el 99 es del día ET anterior al pedido.
DIAS = {
    '2026-11-11': [partido(99, 'Miami Heat', 'New York Knicks', '2026-11-11', '2026-11-12T01:00:00+00:00',
                           resultado={'local': 101.0, 'visitante': 99.0}, hash_=SELLO_C)],
    '2026-11-12': [
        partido(101, 'Boston Celtics', 'Los Angeles Lakers', '2026-11-12', '2026-11-13T00:00:00+00:00',
                p_local=0.30, resultado={'local': 99.0, 'visitante': 104.0}, hash_=SELLO_B),
        partido(100, 'Denver Nuggets', 'Utah Jazz', '2026-11-12', '2026-11-13T00:00:00+00:00', p_local=0.62),
    ],
    '2026-11-13': [partido(102, 'Chicago Bulls', 'Philadelphia 76ers', '2026-11-13', '2026-11-14T01:00:00+00:00',
                           sellado=None, sello_previsto='2026-11-14T00:30:00+00:00')],
    '2026-11-14': [partido(103, 'Phoenix Suns', 'Golden State Warriors', '2026-11-14', '2026-11-15T00:30:00+00:00',
                           p_local=0.58, sellado='despues')],
}


def mercado(id, market, side, sellado, prob=0.55, line=None, team=None, player=None, player_id=None, price=None,
            book=None, outcome=None):
    return {'id': id, 'market': market, 'side': side, 'team': team, 'line': line, 'probability': prob,
            'push_probability': 0.0, 'conditional': player is not None, 'player': player, 'player_id': player_id,
            'sealed_at': sellado, 'seal': SELLO_A, 'estimate': 24.2, 'price': price, 'book': book,
            'odds_at': None, 'outcome': outcome, 'photo_id': 'CENTINELA_MERCADO'}


MERCADOS_103 = {
    'partido_id': 103,
    'markets': [
        mercado('winner-103-local', 'winner', 'local', '2026-11-15T01:30:00+00:00', 0.58, team='Phoenix Suns'),
        mercado('spreads-1-5.5-local', 'handicap', 'local', '2026-11-14T23:30:00+00:00', 0.52, line=-5.5,
                team='Phoenix Suns', price=1.91, book='pinnacle'),
        mercado('totals-None-228.5-over', 'game_total', 'over', '2026-11-14T23:30:00+00:00', 0.57, line=228.5,
                price=1.95, book='fanduel'),
        mercado('player_points-77-24.5-over', 'player_points', 'over', '2026-11-14T23:30:00+00:00', 0.61, line=24.5,
                team='Phoenix Suns', player='Devin Booker', player_id=77),
        mercado('player_blocks-77-1.5-over', 'player_blocks', 'over', '2026-11-14T23:30:00+00:00', 0.5, line=1.5,
                player='Devin Booker', player_id=77),
    ],
    'projections': [{'player_id': 77, 'player': 'Devin Booker', 'market': 'puntos', 'estimate': 'CENTINELA_FIT'}],
    'destacado': {'id': 'totals-None-228.5-over'},
}


class NbaApiFalsa:
    def __init__(self, dias=None, mercados=None):
        self.dias = DIAS if dias is None else dias
        self.mercados = {103: MERCADOS_103} if mercados is None else mercados
        self.llamadas: list[tuple[str, dict | None]] = []

    def __call__(self, ruta, params=None):
        self.llamadas.append((ruta, params))
        if ruta == '/nba/v1/cartelera':
            return {'partidos': list(self.dias.get(params['fecha'], []))}
        if ruta.startswith('/nba/v1/partido/') and ruta.endswith('/mercados'):
            pid = int(ruta.split('/')[4])
            if pid in self.mercados:
                return self.mercados[pid]
            return {'partido_id': pid, 'markets': [], 'projections': [], 'destacado': None}
        raise nba_datos.NbaNoDisponible(f'ruta inesperada {ruta}')

    @property
    def dias_pedidos(self) -> list[str]:
        return [p['fecha'] for r, p in self.llamadas if r == '/nba/v1/cartelera']


def instalar(mp, falsa: NbaApiFalsa | None = None) -> NbaApiFalsa:
    falsa = falsa or NbaApiFalsa()
    nba_datos.vaciar_cache()
    mp.setattr(nba_datos, '_pedir', falsa)
    mp.setattr(nba_datos, 'hoy_et', lambda ahora=None: HOY_ET)
    mp.setattr(deportes_nba, '_ahora', lambda: AHORA)
    return falsa


def romper(mp):
    def caida(ruta, params=None):
        raise nba_datos.NbaNoDisponible('CENTINELA_ERROR')
    nba_datos.vaciar_cache()
    mp.setattr(nba_datos, '_pedir', caida)
