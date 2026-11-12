"""Reglas de acceso de «alta probabilidad», versionadas por fecha de lote (db/111).

A un lote le aplica la fila de mayor (vigente_desde, regla_id) con vigente_desde <= batch_date.
Una regla nueva solo puede valer desde mañana (UTC): nunca alcanza un lote ya repartido.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from psycopg.errors import UndefinedTable

from ..db import conn, query, query_one
from .auditoria import audit

STREAM = 'alta_probabilidad'
PROB_MIN_ABS, PROB_MAX_ABS = Decimal('0.62'), Decimal('0.95')
DIAS_AGENDA_DEFECTO = 7
_TTL = 60.0
_TTL_AJUSTES = 10.0

# Rango SQL: a cada pronóstico (alias `a`) con su lote (alias `b`) le toca la regla del día del lote.
# Los dos %s son el rango de reserva si ninguna regla aplica (nunca ocurre con la fila sembrada).
RANGO_SQL = '''LEFT JOIN LATERAL (SELECT r.prob_min, r.prob_max FROM acceso_reglas r
        WHERE r.stream = 'alta_probabilidad' AND r.vigente_desde <= b.batch_date
        ORDER BY r.vigente_desde DESC, r.regla_id DESC LIMIT 1) rg ON TRUE'''
RANGO_WHERE = 'a.prob BETWEEN COALESCE(rg.prob_min, %s) AND COALESCE(rg.prob_max, %s)'


@dataclass(frozen=True)
class Regla:
    regla_id: int
    vigente_desde: date
    prob_min: float
    prob_max: float
    free_fraction: float
    creado_por: str = 'codigo'
    creado_en: datetime | None = None
    nota: str = ''


# Los valores de hoy: lo que rige si la tabla aún no existe.
HOY = Regla(0, date(2000, 1, 1), .73, .95, .10, 'codigo', None, 'Valores de código')

_lock = threading.Lock()
_cache: dict = {}


def hoy_utc() -> date:
    return datetime.now(timezone.utc).date()


def _regla(row: dict) -> Regla:
    return Regla(int(row['regla_id']), row['vigente_desde'], float(row['prob_min']),
                 float(row['prob_max']), float(row['free_fraction']), row['creado_por'],
                 row['creado_en'], row['nota'])


def _cargar() -> list[Regla]:
    try:
        rows = query('SELECT regla_id, vigente_desde, prob_min, prob_max, free_fraction, creado_por, '
                     'creado_en, nota FROM acceso_reglas WHERE stream=%s '
                     'ORDER BY vigente_desde, regla_id', (STREAM,))
    except UndefinedTable:
        return [HOY]
    return [_regla(r) for r in rows] or [HOY]


def _cargar_dias() -> int:
    try:
        row = query_one('SELECT dias_agenda FROM cliente_ajustes WHERE id=1')
    except UndefinedTable:
        return DIAS_AGENDA_DEFECTO
    return int(row['dias_agenda']) if row else DIAS_AGENDA_DEFECTO


def _con_cache(clave: str, ttl: float, cargar):
    ahora = time.monotonic()
    with _lock:
        hit = _cache.get(clave)
        if hit and ahora - hit[0] < ttl:
            return hit[1]
    valor = cargar()
    with _lock:
        _cache[clave] = (ahora, valor)
    return valor


def invalidar_cache() -> None:
    with _lock:
        _cache.clear()


def todas() -> list[Regla]:
    """Todas las reglas, de la más antigua a la más reciente (orden de vigencia)."""
    return list(_con_cache('reglas', _TTL, lambda: _cargar()))


def _como_fecha(batch_date) -> date:
    if batch_date is None:
        return hoy_utc()
    if isinstance(batch_date, datetime):
        return batch_date.date()
    if isinstance(batch_date, date):
        return batch_date
    return date.fromisoformat(str(batch_date)[:10])


def vigente(batch_date=None) -> Regla:
    """La regla que rige para un lote (sin fecha: el día UTC de hoy)."""
    dia = _como_fecha(batch_date)
    aplicables = [r for r in todas() if r.vigente_desde <= dia]
    # Ya vienen ordenadas por (vigente_desde, regla_id): la última manda.
    return aplicables[-1] if aplicables else todas()[0]


def dias_agenda() -> int:
    return int(_con_cache('dias', _TTL_AJUSTES, lambda: _cargar_dias()))


def validar(prob_min, prob_max, free_fraction, vigente_desde: date, nota: str) -> tuple:
    try:
        lo, hi = Decimal(str(prob_min)), Decimal(str(prob_max))
        fr = Decimal(str(free_fraction))
    except Exception:
        raise ValueError('Rango o porcentaje no válidos.') from None
    for v in (lo, hi, fr):
        if v != v.quantize(Decimal('0.01')):
            raise ValueError('Usa como máximo dos decimales (0,01 = 1 %).')
    if not (PROB_MIN_ABS <= lo < hi <= PROB_MAX_ABS):
        raise ValueError('El rango debe cumplir 62 % ≤ mínimo < máximo ≤ 95 %: fuera de ahí no se sella nada.')
    if not (Decimal(0) <= fr <= Decimal(1)):
        raise ValueError('El porcentaje gratis debe estar entre 0 y 100 %.')
    if vigente_desde <= hoy_utc():
        raise ValueError('La regla debe empezar mañana (UTC) o después: nunca toca lotes ya repartidos.')
    if not (nota or '').strip():
        raise ValueError('La nota es obligatoria.')
    return lo, hi, fr


def crear(prob_min, prob_max, free_fraction, vigente_desde: date, nota: str, actor: str) -> int:
    lo, hi, fr = validar(prob_min, prob_max, free_fraction, vigente_desde, nota)
    with conn() as c:
        regla_id = c.execute(
            'INSERT INTO acceso_reglas (stream, vigente_desde, prob_min, prob_max, free_fraction, '
            'creado_por, nota) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING regla_id',
            (STREAM, vigente_desde, lo, hi, fr, actor, nota.strip())).fetchone()['regla_id']
        audit(c, actor, 'acceso:regla', detail={
            'regla_id': regla_id, 'vigente_desde': vigente_desde.isoformat(), 'prob_min': float(lo),
            'prob_max': float(hi), 'free_fraction': float(fr), 'nota': nota.strip()})
    invalidar_cache()
    return regla_id


def guardar_dias_agenda(dias: int, actor: str) -> None:
    if not 1 <= dias <= 14:
        raise ValueError('Los días de agenda deben estar entre 1 y 14.')
    with conn() as c:
        c.execute('INSERT INTO cliente_ajustes (id, dias_agenda, updated_by) VALUES (1,%s,%s) '
                  'ON CONFLICT (id) DO UPDATE SET dias_agenda=EXCLUDED.dias_agenda, '
                  'updated_by=EXCLUDED.updated_by, updated_at=now()', (dias, actor))
        audit(c, actor, 'acceso:dias_agenda', detail={'dias_agenda': dias})
    invalidar_cache()


def manana_utc() -> date:
    return hoy_utc() + timedelta(days=1)
