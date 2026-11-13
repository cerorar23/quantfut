"""Adaptador de fútbol del contrato `/deportes/v1/futbol/…` (Fase 3 parte D de «Web y App»).

Reúne, sin cambiar su comportamiento, las fuentes que hoy usan la web (`football()` de `ergonomic-views.js`) y la
app (`sports_feed.dart`): la agenda (`fichas._agenda`), las filas públicas de alta probabilidad
(`mobile.high_probability(plus=False)`), los destacados resueltos (`partido_mercados.destacados_resueltos`) y los
mercados abiertos del partido (`mobile.mercados_partido(..., plus=False, web=True)`). Solo lee; no extrae ni modifica
ninguna función de esas fuentes. Es público y anónimo: nada depende de la sesión (VIP, desbloqueos, Escalera, parley).

Mapeo (decisiones de la parte D; el porqué está en `harness/progreso.md`):

* `Evento.id` = `match_id`. `league` = NOMBRE de la COMPETICIÓN (`liga.nombre` de la agenda, que sale de
  `matches.league_id`), nunca la liga doméstica del equipo (`teams.league_id`).
* `status` (la fuente solo distingue `matches.status`; el marcador en vivo vive en otra columna y la agenda no lo trae,
  así que NO se inventa `live`): `finished` -> `finished`; `postponed` -> `cancelled` (el enumerado cerrado no tiene
  «aplazado»: el cliente lo trata como no jugado); `live` (si algún día la columna lo trae) -> `live`; `scheduled` ->
  `scheduled`, salvo que hayan pasado `ESPERA_RESULTADO` desde el inicio sin resultado: entonces `awaiting_result`.
* `score` = «g – g» solo si la agenda trae marcador (partido terminado con goles).
* `seal` = `chain_sha256` de la fila pública del partido, solo si es un sha256 válido de 64 hex. `sealed_at` = la fecha
  de su lote (`batch_date`, a las 00:00 UTC): la fila no trae una marca mejor. `planned_seal` = cuándo se calcula el
  pronóstico (`mobile.pronostico_desde`), mientras no haya pronóstico sellado y el partido no haya empezado.
* `bloqueados` = SOLO el número de filas de pago (`alta_probabilidad.vip`) del partido.
* Mercados públicos: (1) las filas gratis de alta probabilidad (sellan `sealed_at` y `eligible = sealed_at < start`);
  (2) el destacado resuelto de un partido terminado (registrado y sellado antes del inicio -> `eligible=True`, sin
  `sealed_at` porque la fuente no lo trae); (3) solo en `partido(id)`, los demás mercados abiertos que ya publica
  `mercados_partido` para la web sin sesión: son ANÁLISIS no sellado -> `eligible=False`, `sealed_at=None`.
* `destacado`: el destacado resuelto si el partido terminado lo tiene; si no, la fila gratis de mayor probabilidad. La
  cartelera no calcula el destacado de la web (`construir` consulta la base por partido); lo único que tiene a mano es
  eso, y `partido(id)` usa la MISMA regla para que ambas respuestas coincidan.
* `price` solo es una cuota que paga una casa (o la publicada al sellar); la «cuota justa» 1 ÷ probabilidad no se
  inventa: el cliente la calcula de `probability`.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from . import fichas, mobile, partido_mercados
from ..db import query_one
from .deportes_v1 import ADAPTADORES, FAMILIA_OTROS, Evento, Imagenes, Mercado

DEPORTE = 'futbol'
ESPERA_RESULTADO = timedelta(hours=3)      # un partido (con prórroga y penaltis) no pasa de ahí sin resultado
_RE_SHA256 = re.compile(r'^[0-9a-f]{64}$')
_RESULTADOS = {'win', 'loss', 'push', 'void'}
_CUOTA_REAL = partido_mercados.CUOTA_REAL

# Clave del motor -> familia del catálogo de fútbol (`catalogo_semilla`; la misma tabla que la app:
# `familyMarkets` en `live_markets.dart`). Lo que no esté aquí (btts, 1ª mitad, gana a cero…) va a `otros`.
_FAMILIAS = {
    'totals': 'goals',
    'team_totals_home': 'team_goals', 'team_totals_away': 'team_goals',
    'home_to_score': 'team_goals', 'away_to_score': 'team_goals',
    'corners': 'corners',
    'corners_home': 'corners_team', 'corners_away': 'corners_team',
    'spreads': 'handicap',
    'double_chance': 'double_chance',
    'h2h': 'winner',
    'cards': 'cards',
}


def _estado(crudo: Any, start: datetime, ahora: datetime) -> str:
    if crudo == 'finished':
        return 'finished'
    if crudo == 'postponed':
        return 'cancelled'
    if crudo == 'live':
        return 'live'
    return 'awaiting_result' if start + ESPERA_RESULTADO <= ahora else 'scheduled'


def _probabilidad(v: Any) -> float | None:
    try:
        p = float(v)
    except (TypeError, ValueError):
        return None
    return p if math.isfinite(p) and 0 < p < 1 else None


def _cuota(v: Any) -> float | None:
    try:
        p = float(v)
    except (TypeError, ValueError):
        return None
    return round(p, 2) if math.isfinite(p) and p > 1 else None


def _resultado(v: Any) -> str | None:
    return v if v in _RESULTADOS else None


def _linea(v: Any) -> float | None:
    return None if v is None else float(v)


def _lote_a_utc(v: Any) -> datetime | None:
    """`batch_date` (fecha del lote sellado) como instante UTC a las 00:00."""
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            v = date.fromisoformat(v[:10])
        except ValueError:
            return None
    if isinstance(v, date):
        return datetime.combine(v, time.min, tzinfo=timezone.utc)
    return None


def _sha(v: Any) -> str | None:
    return v.lower() if isinstance(v, str) and _RE_SHA256.match(v.lower()) else None


def _imagenes(a: dict) -> Imagenes | None:
    casa, fuera = ((a.get(lado) or {}).get('escudo') for lado in ('local', 'visitante'))
    return Imagenes(home=casa, away=fuera) if casa or fuera else None


class AdaptadorFutbol:
    """Cumple `deportes_v1.Adaptador`; se registra como `ADAPTADORES['futbol']` al importarse."""

    # ── interfaz ─────────────────────────────────────────────────────────────

    def cartelera(self, inicio: datetime, fin: datetime) -> list[Evento]:
        agenda = fichas._agenda(inicio, fin, None)
        if not agenda:
            return []
        alta = mobile.high_probability(plus=False)
        resueltos = self._resueltos(agenda, inicio.date())
        return [self._evento(a, alta, resueltos.get(a['match_id']), todos=False) for a in agenda]

    def partido(self, id: str) -> Evento | None:
        fila = query_one('SELECT kickoff_utc FROM matches WHERE match_id = %s', (id,))
        if not fila:
            return None
        ko = fila['kickoff_utc']
        agenda = [a for a in fichas._agenda(ko, ko + timedelta(seconds=1), None) if a['match_id'] == id]
        if not agenda:
            return None            # liga inactiva o partido fuera de la agenda pública
        a = agenda[0]
        # `started=True`: el detalle de la app/web también enseña lo gratis de un partido ya empezado o terminado.
        alta = mobile.high_probability(plus=False, started=True)
        resuelto = self._resueltos(agenda, ko.date()).get(id)
        return self._evento(a, alta, resuelto, todos=True)

    def familia_de(self, market: str) -> str:
        return _FAMILIAS.get(market, FAMILIA_OTROS)

    # ── construcción ─────────────────────────────────────────────────────────

    @staticmethod
    def _resueltos(agenda: list[dict], desde: date) -> dict[str, dict]:
        if not any(a.get('estado') == 'finished' for a in agenda):
            return {}
        ids = {a['match_id'] for a in agenda}
        return {r['match_id']: r for r in partido_mercados.destacados_resueltos(desde) if r['match_id'] in ids}

    def _evento(self, a: dict, alta: dict, resuelto: dict | None, *, todos: bool) -> Evento:
        id_ = a['match_id']
        start = a['kickoff_utc']
        ahora = datetime.now(timezone.utc)
        filas = sorted((r for r in alta.get('proximos', []) if r.get('match_id') == id_ and self._publica(r)),
                       key=lambda r: (-float(r['prob']), str(r['pick_key'])))
        mercados = [self._mercado_pick(r, start) for r in filas]
        claves = {partido_mercados.clave(r['market'], r['selection'], r.get('line')): m
                  for r, m in zip(filas, mercados)}
        destacado = mercados[0].id if mercados else None
        if resuelto is not None and (m := self._mercado_resuelto(resuelto)) is not None:
            previo = claves.get(partido_mercados.clave(resuelto['market'], resuelto['selection'], resuelto.get('line')))
            if previo is None:
                mercados.insert(0, m)
                destacado = m.id
            else:
                previo.outcome = previo.outcome or m.outcome
                destacado = previo.id
        if todos:
            existentes = {m.id for m in mercados} | set(claves)
            if resuelto is not None:
                existentes.add(partido_mercados.clave(resuelto['market'], resuelto['selection'], resuelto.get('line')))
            mercados += self._mercados_abiertos(a, filas, existentes)
        sello = filas[0] if filas else None          # `_publica` ya garantiza un sha256 válido
        sellado = _lote_a_utc(sello.get('batch_date')) if sello else None
        estado = _estado(a.get('estado'), start, ahora)
        planificado = None
        if sello is None and estado == 'scheduled':
            planificado = self._planificado(start)
        marcador = a.get('marcador')
        return Evento(
            id=id_, sport=DEPORTE, home=a['local']['nombre'], away=a['visitante']['nombre'],
            league=a['liga']['nombre'], start=start, status=estado,
            seal=_sha(sello.get('chain_sha256')) if sello else None, sealed_at=sellado, planned_seal=planificado,
            score=f'{marcador[0]} – {marcador[1]}' if marcador and None not in marcador else None,
            bloqueados=sum(1 for v in alta.get('vip', []) if v.get('match_id') == id_),
            imagenes=_imagenes(a), markets=mercados, destacado=destacado)

    @staticmethod
    def _publica(r: dict) -> bool:
        """Misma condición que `publicForecasts` (web) más `free`: nunca una fila de pago o abierta por desbloqueo."""
        return (r.get('locked') is not True and r.get('free') is True and _probabilidad(r.get('prob')) is not None
                and bool(r.get('pick_key')) and _sha(r.get('chain_sha256')) is not None)

    def _mercado_pick(self, r: dict, start: datetime) -> Mercado:
        sellado = _lote_a_utc(r.get('batch_date'))
        precio = _cuota(r.get('ref_price'))
        return Mercado(
            id=str(r['pick_key']), label='Pronóstico publicado', selection=str(r.get('texto') or ''),
            probability=float(r['prob']), sealed_at=sellado, eligible=sellado is not None and sellado < start,
            market=str(r['market']), family=self.familia_de(r['market']), line=_linea(r.get('line')),
            price=precio, reference=partido_mercados.nombre_casa(r.get('ref_book')) if precio else None,
            outcome=_resultado(r.get('outcome')))

    def _mercado_resuelto(self, r: dict) -> Mercado | None:
        p = _probabilidad(r.get('prob'))
        if p is None:
            return None
        precio = _cuota(r.get('ref_price'))
        return Mercado(
            id=f"destacado:{r['match_id']}", label='Pronóstico destacado', selection=str(r.get('texto') or ''),
            probability=p, sealed_at=None, eligible=True,      # la fuente solo liquida el registrado y sellado antes del inicio
            market=str(r['market']), family=self.familia_de(r['market']), line=_linea(r.get('line')),
            price=precio, reference=(r.get('ref_book') or 'Casa registrada') if precio else None,
            outcome=_resultado(r.get('outcome')))

    def _mercados_abiertos(self, a: dict, picks: list[dict], existentes: set[str]) -> list[Mercado]:
        """Mercados que `mercados_partido` deja abiertos a la web sin sesión (análisis, no sellados)."""
        ficha = {'local': {'nombre': a['local']['nombre']}, 'visitante': {'nombre': a['visitante']['nombre']}}
        lista = mobile.mercados_partido(a['match_id'], ficha, picks, False, True)
        salida: list[Mercado] = []
        for f in (lista or {}).get('filas', []):
            p = _probabilidad(f.get('prob'))
            if f.get('locked') or p is None or not f.get('market') or str(f.get('id')) in existentes:
                continue
            real = f.get('cuota_tipo') in _CUOTA_REAL
            precio = _cuota(f.get('cuota')) if real else None
            existentes.add(str(f['id']))
            salida.append(Mercado(
                id=str(f['id']), label=str(f.get('titulo') or ''), selection=str(f.get('seleccion') or ''),
                probability=p, sealed_at=None, eligible=False, market=str(f['market']),
                family=self.familia_de(f['market']), line=_linea(f.get('line')),
                price=precio, reference=f.get('casa') if precio else None, outcome=_resultado(f.get('resultado'))))
        return salida

    @staticmethod
    def _planificado(start: datetime) -> datetime | None:
        texto = mobile.pronostico_desde(start)
        return datetime.fromisoformat(texto) if texto else None


ADAPTADORES[DEPORTE] = AdaptadorFutbol()
