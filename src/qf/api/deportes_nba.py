"""Adaptador de NBA del contrato `/deportes/v1/nba` (Fase 3 parte C de «Web y App»; base en `deportes_v1.py`).

Fuente: `nba_datos` (lee `nba-api` con su propia caché). Aquí no se calcula nada: se normaliza lo que la web ya normaliza
en `nbaGames` / `nbaPickMarkets` / `nbaV2Events` (`frontend/sports-data.js`) y `loadNbaMarkets`.

Zona horaria: la cartelera de `nba-api` es por fecha del Este (ET), no por UTC. Para una ventana UTC [inicio, fin) se piden
los días ET que la cubren con un día de margen por lado (como la web), se unen sin duplicar por `id` y se filtra por `start`.
Un día que falla hace fallar la petición (el router lo vuelve 503): no se devuelve una lista parcial como si fuera completa.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

from . import nba_datos
from .destacado_valor import cumple_filtro
from .deportes_v1 import ADAPTADORES, Evento, Mercado

SEASON_START = date(2026, 10, 20)      # la API trae también la pretemporada; la web (NBA_SEASON_START) muestra desde el estreno
MARGEN_DIAS = 1
BUSCAR_ATRAS, BUSCAR_ADELANTE = 4, 4   # días ET donde se busca un partido por id (los que navega la web)
ESPERA_RESULTADO = timedelta(hours=4)
FAMILIAS = ('winner', 'handicap', 'game_total', 'team_points', 'player_points', 'player_rebounds', 'player_assists',
            'player_threes')
REFERENCIA_MODELO = 'Probabilidad estadística'
_ETIQUETAS = {'winner': 'Ganador del partido', 'handicap': 'Hándicap', 'game_total': 'Total del partido',
              'team_points': 'Puntos del equipo', 'player_points': 'Puntos del jugador',
              'player_rebounds': 'Rebotes del jugador', 'player_assists': 'Asistencias del jugador',
              'player_threes': 'Triples del jugador'}
_UNIDADES = {'game_total': 'puntos', 'team_points': 'puntos', 'player_points': 'puntos', 'player_rebounds': 'rebotes',
             'player_assists': 'asistencias', 'player_threes': 'triples'}
_RE_SELLO = re.compile(r'^[0-9a-f]{64}$')
_RESULTADOS = ('win', 'loss', 'push', 'void')


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _fecha(v) -> datetime | None:
    if not isinstance(v, str):
        return None
    try:
        d = datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _prob(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v < 1 else None


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float('inf') else None


def _pts(v) -> str:
    """Puntos como los muestra la web (JS imprime 101, no 101.0)."""
    return str(int(v)) if float(v).is_integer() else str(v)


def dias_et(inicio: datetime, fin: datetime) -> list[date]:
    """Días ET que cubren [inicio, fin) con un día de margen por lado, desde el estreno de la temporada."""
    primero = inicio.astimezone(nba_datos.ET).date() - timedelta(days=MARGEN_DIAS)
    ultimo = (fin - timedelta(microseconds=1)).astimezone(nba_datos.ET).date() + timedelta(days=MARGEN_DIAS)
    primero = max(primero, SEASON_START)
    return [primero + timedelta(days=i) for i in range((ultimo - primero).days + 1)]


def _partido_valido(p) -> bool:
    return (isinstance(p, dict) and isinstance(p.get('id'), int) and not isinstance(p.get('id'), bool)
            and isinstance(p.get('local'), dict) and p['local'].get('nombre')
            and isinstance(p.get('visitante'), dict) and p['visitante'].get('nombre')
            and _fecha(p.get('inicio_utc')) is not None)


def _final(p: dict) -> tuple[int | float, int | float] | None:
    r = p.get('resultado')
    if isinstance(r, dict) and _num(r.get('local')) is not None and _num(r.get('visitante')) is not None:
        return r['local'], r['visitante']
    return None


def _mercado_ganador(p: dict, inicio: datetime, final) -> Mercado | None:
    pron = p.get('pronostico')
    if not isinstance(pron, dict):
        return None
    prob, sello = _prob(pron.get('p_local')), _fecha(pron.get('sellado_en'))
    if prob is None or sello is None:
        return None
    local = prob >= .5
    elegible = sello < inicio
    resultado = None
    if elegible and final:
        resultado = 'win' if (final[0] > final[1]) == local else 'loss'
    return Mercado(id=f'winner-{p["id"]}', label=_ETIQUETAS['winner'], market='winner', family='winner',
                   selection=p['local']['nombre'] if local else p['visitante']['nombre'],
                   probability=prob if local else 1 - prob, sealed_at=sello, eligible=elegible,
                   reference=REFERENCIA_MODELO, outcome=resultado, principal=True)


def _destacado_cartelera(ganador: Mercado | None) -> str | None:
    """Destacado de la cartelera: la misma regla que aplica la web (`featuredSportMarket` sobre el ganador del modelo, sin cuota
    de casa): no revisado, probabilidad >= 75 % y cuota de referencia 1 ÷ probabilidad >= 1,20 (franja 75 %–83,3 %)."""
    if ganador is None or not ganador.eligible:
        return None
    return ganador.id if cumple_filtro(ganador.probability, 1 / ganador.probability) else None


def _proyeccion(pron: dict) -> list[float] | None:
    """`[mu_local, mu_visitante]` como la lee la web (`nbaV2Events`): exactamente dos números finitos."""
    mu = pron.get('mu')
    if isinstance(mu, list) and len(mu) == 2 and all(_num(x) is not None for x in mu):
        return [float(x) for x in mu]
    return None


def _evento(p: dict, ahora: datetime) -> Evento:
    inicio = _fecha(p['inicio_utc'])
    final = _final(p)
    pron = p.get('pronostico') if isinstance(p.get('pronostico'), dict) else {}
    hash_ = pron.get('hash')
    ganador = _mercado_ganador(p, inicio, final)
    estado = ('finished' if final else 'awaiting_result' if inicio + ESPERA_RESULTADO < ahora else 'scheduled')
    return Evento(id=str(p['id']), sport='nba', home=p['local']['nombre'], away=p['visitante']['nombre'], league='NBA',
                  start=inicio, status=estado, seal=hash_ if isinstance(hash_, str) and _RE_SELLO.match(hash_) else None,
                  sealed_at=_fecha(pron.get('sellado_en')), planned_seal=_fecha(p.get('sello_previsto')),
                  score=f'{_pts(final[0])} – {_pts(final[1])}' if final else None, markets=[ganador] if ganador else [],
                  destacado=ganador.id if ganador and ganador.eligible else None, team_projection=_proyeccion(pron))


def _mercado_publico(m: dict, p: dict, inicio: datetime, final) -> Mercado | None:
    """Un mercado de `/nba/v1/partido/{id}/mercados`; los que la fuente publica fuera de rango se descartan."""
    familia = m.get('market')
    prob, sello = _prob(m.get('probability')), _fecha(m.get('sealed_at'))
    if familia not in FAMILIAS or familia == 'winner' or prob is None or sello is None or not isinstance(m.get('id'), str):
        return None
    linea, equipo, jugador, lado = _num(m.get('line')), m.get('team'), m.get('player'), m.get('side')
    if linea is None:
        return None
    if familia == 'handicap':
        seleccion = f'{equipo} {"+" if linea > 0 else ""}{linea:g}'
    else:
        seleccion = f'{"Más de" if lado == "over" else "Menos de"} {linea:g} {_UNIDADES[familia]}'
    if jugador:
        etiqueta = f'{_ETIQUETAS[familia].replace(" del jugador", "")} de {jugador}'
    elif familia == 'team_points':
        etiqueta = f'Puntos de {equipo}'
    else:
        etiqueta = _ETIQUETAS[familia]
    elegible = sello < inicio
    precio = _num(m.get('price'))
    precio = precio if precio is not None and precio > 1 else None
    casa = m.get('book') if isinstance(m.get('book'), str) and m['book'].strip() else None
    pid = m.get('player_id')
    push = _num(m.get('push_probability'))
    return Mercado(id=m['id'], label=etiqueta, selection=seleccion, probability=prob, sealed_at=sello, eligible=elegible,
                   market=familia, family=familia, line=linea, player=jugador if isinstance(jugador, str) else None,
                   player_id=str(pid) if isinstance(pid, int) and not isinstance(pid, bool) else None,
                   price=precio, reference=casa if precio is not None and casa else REFERENCIA_MODELO,
                   outcome=m.get('outcome') if elegible and m.get('outcome') in _RESULTADOS else None,
                   push_probability=push if push is not None and 0 <= push <= 1 else None)


class AdaptadorNba:
    def cartelera(self, inicio: datetime, fin: datetime) -> list[Evento]:
        dias = dias_et(inicio, fin)
        if not dias:
            return []
        hoy = nba_datos.hoy_et()
        with ThreadPoolExecutor(max_workers=min(6, len(dias))) as pool:
            por_dia = list(pool.map(lambda d: nba_datos.cartelera(d, hoy), dias))     # un día que falla lanza
        vistos: dict[int, dict] = {}
        for partidos in por_dia:
            for p in partidos:
                if _partido_valido(p):
                    vistos.setdefault(p['id'], p)
        ahora = _ahora()
        eventos = [_evento(p, ahora) for p in vistos.values()]
        for e in eventos:       # en la cartelera el destacado sigue la regla de la web; el detalle conserva el suyo
            e.destacado = _destacado_cartelera(e.markets[0] if e.markets else None)
        return [e for e in eventos if inicio <= e.start < fin]

    def _buscar(self, id: str) -> dict | None:
        if not id.isdecimal() or len(id) > 12:
            return None
        hoy = nba_datos.hoy_et()
        orden = sorted(range(-BUSCAR_ATRAS, BUSCAR_ADELANTE + 1), key=lambda i: (abs(i), i))
        for i in orden:
            dia = hoy + timedelta(days=i)
            if dia < SEASON_START:
                continue
            for p in nba_datos.cartelera(dia, hoy):
                if _partido_valido(p) and p['id'] == int(id):
                    return p
        return None

    def partido(self, id: str) -> Evento | None:
        p = self._buscar(id)
        if p is None:
            return None
        ev = _evento(p, _ahora())
        inicio = ev.start
        fecha = date.fromisoformat(p['fecha']) if isinstance(p.get('fecha'), str) else inicio.astimezone(nba_datos.ET).date()
        datos = nba_datos.mercados(p['id'], fecha)
        final = _final(p)
        propios = [x for x in (_mercado_publico(m, p, inicio, final) for m in datos['markets'] if isinstance(m, dict)) if x]
        ev.markets = [*ev.markets, *propios]
        dest = datos.get('destacado')
        dest = dest.get('id') if isinstance(dest, dict) else None
        if isinstance(dest, str) and dest in {m.id for m in propios}:
            ev.destacado = dest
        return ev

    def familia_de(self, market: str) -> str:
        return market if market in FAMILIAS else 'otros'


ADAPTADORES['nba'] = AdaptadorNba()
