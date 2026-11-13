"""Adaptador de tenis del contrato `/deportes/v1/tenis/…` (Fase 3 parte B de «Web y App»).

Fuente: lo que ya publica el servidor, `tenis_publico.public_data()` (el JSON público del exportador, con caducidad). No
lee nada nuevo ni calcula: traduce cada evento a `Evento`/`Mercado`, campo a campo, con la misma normalización que hacen la
web (`tennisEvents`, `frontend/sports-data.js`) y la app (`tennisEvents`, `sports_feed.dart`).

Decisiones:
* `status`: el exportador emite `scheduled`, `awaiting_result`, `no_result`, `finished` y `cancelled` (`tenis_publico.projection`).
  `scheduled`, `awaiting_result`, `finished` y `cancelled` pasan tal cual; `no_result` (36 h pasadas sin resultado oficial) no existe en el enumerado
  cerrado del contrato y se publica como `awaiting_result`, que es lo que es: sigue sin resultado. `live` no lo emite nadie
  hoy. Un valor que no esté en esta tabla lanza `ValueError` (→ 503): no se adivina ni se esconde el evento.
* `eligible = sealed_at < start`. Sin `sealed_at` válido no es elegible. Un mercado no elegible no lleva `outcome` (un sello
  posterior al inicio no es pronóstico previo ni cuenta como acierto); el exportador ya descarta esos sellos, así que en
  la práctica coincide con la web.
* `seal` solo si es sha256 en minúsculas de 64 hex; si no, `None`. `bloqueados = 0` (tenis no tiene mercados de pago).
* `imagenes = None`: el feed público no trae ids de jugador y las fotos de tenis se resuelven en el cliente por nombre
  (`/web/imagenes/tenis/<archivo>`); el servidor aún no las expone por evento.
* `price`/`reference` tal cual los publica la fuente (hoy `price` siempre es `None`: no se inventa ninguna cuota).
* `line`, `player`, `player_id` quedan en `None`: la fuente solo trae la línea dentro del texto de `selection`.
* `market` es el tipo del contrato, derivado del id público (`games_total-3` → `games_total`; `winner` → `winner`).
* Si la fuente no está `ok`/`partial` (caducada o no disponible) se lanza `RuntimeError`: el router la convierte en 503,
  nunca una cartelera vacía.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from . import tenis_publico
from .deportes_v1 import ADAPTADORES, Evento, Mercado

ESTADOS = {'scheduled': 'scheduled', 'awaiting_result': 'awaiting_result', 'no_result': 'awaiting_result',
           'finished': 'finished', 'cancelled': 'cancelled', 'live': 'live'}

# Clave del motor (`Mercado.market`) -> familia del catálogo de tenis (`catalogo_semilla`). `winner` no es una familia del
# catálogo de tenis: el router la manda a `otros`.
FAMILIAS = {'games_total': 'games_total', 'games_handicap': 'games_handicap', 'set_winner': 'set_winner',
            'sets_handicap': 'sets_handicap', 'sets_total': 'sets_total', 'tiebreak': 'tiebreak', 'winner': 'winner'}

_RE_SELLO = re.compile(r'^[0-9a-f]{64}$')
_RE_ID_MERCADO = re.compile(r'^(.+)-\d+$')


def _instante(valor) -> datetime | None:
    if not isinstance(valor, str):
        return None
    try:
        d = datetime.fromisoformat(valor.replace('Z', '+00:00'))
    except ValueError:
        return None
    return d.astimezone(timezone.utc) if d.tzinfo else None


def _tipo(id_mercado: str) -> str:
    m = _RE_ID_MERCADO.match(id_mercado)
    return m.group(1) if m else id_mercado


def _numero(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _mercado(m: dict, inicio: datetime, sellado: datetime | None) -> Mercado:
    elegible = sellado is not None and sellado < inicio
    tipo = _tipo(str(m['id']))
    return Mercado(
        id=str(m['id']), label=str(m['label']), selection=str(m['selection']), probability=m['probability'],
        sealed_at=sellado, eligible=elegible, market=tipo, family=familia(tipo),
        price=_numero(m.get('price')), reference=m['reference'] if isinstance(m.get('reference'), str) else None,
        outcome=m.get('outcome') if elegible else None, push_probability=_numero(m.get('push_probability')))


def familia(market: str) -> str:
    return FAMILIAS.get(market, market)


def _evento(e: dict, inicio: datetime, *, solo_destacado: bool) -> Evento:
    estado = e.get('status') or 'scheduled'
    if estado not in ESTADOS:
        raise ValueError(f'estado de tenis desconocido: {estado!r}')
    sellado = _instante(e.get('sealed_at'))
    destacado = e.get('destacado')
    destacado_id = str(destacado['id']) if isinstance(destacado, dict) and destacado.get('id') is not None else None
    mercados = [_mercado(m, inicio, sellado) for m in e['markets']
                if not solo_destacado or str(m['id']) == destacado_id]
    seal = e.get('seal')
    return Evento(
        id=str(e['id']), sport='tenis', home=e['home'], away=e['away'], league=str(e.get('league') or ''), start=inicio,
        status=ESTADOS[estado], seal=seal if isinstance(seal, str) and _RE_SELLO.match(seal) else None,
        sealed_at=sellado, score=e['score'] if isinstance(e.get('score'), str) else None,
        surface=e['surface'] if isinstance(e.get('surface'), str) else None, bloqueados=0,
        imagenes=None, markets=mercados, destacado=destacado_id)


def _eventos() -> list[dict]:
    datos = tenis_publico.public_data()
    if datos.get('state') not in ('ok', 'partial') or not isinstance(datos.get('events'), list):
        raise RuntimeError(f"fuente de tenis no disponible (state={datos.get('state')})")
    return datos['events']


class AdaptadorTenis:
    def cartelera(self, inicio: datetime, fin: datetime) -> list[Evento]:
        salida = []
        for e in _eventos():
            comienzo = _instante(e.get('start'))
            if comienzo is None or not inicio <= comienzo < fin:
                continue
            salida.append(_evento(e, comienzo, solo_destacado=True))
        return salida

    def partido(self, id: str) -> Evento | None:
        for e in _eventos():
            if str(e.get('id')) == id:
                comienzo = _instante(e.get('start'))
                return None if comienzo is None else _evento(e, comienzo, solo_destacado=False)
        return None

    def familia_de(self, market: str) -> str:
        return familia(market)


ADAPTADORES['tenis'] = AdaptadorTenis()
