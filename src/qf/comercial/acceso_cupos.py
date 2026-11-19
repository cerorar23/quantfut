"""Cupos de pronósticos gratis por deporte y cliente (db/116, menú `/control/cupos`).

Dos números por (deporte, cliente 'web'|'app'); `None` = sin límite (todo gratis):

    destacados_gratis_dia     en cuántos partidos del día el destacado se ve sin VIP (los de mayor probabilidad)
    mercados_gratis_partido   cuántos mercados de cada partido se ven sin VIP (los de mayor probabilidad)

Lo demás publicado queda VIP. Es presentación: no toca nada sellado ni el reparto gratis de «alta
probabilidad» (`acceso_reglas`). Un partido de un día ya cerrado se ve entero, con o sin VIP
(`ventana.dia_cerrado`): los cupos solo rigen lo que aún no se ha jugado.

Sin tabla, o para un deporte sin fila, valen los de `DEFECTO` (el comportamiento anterior a db/116).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from psycopg.errors import UndefinedTable

from ..db import conn, query
from .auditoria import audit

CLIENTES = ('web', 'app')
MAXIMO = 999
_TTL = 30.0


@dataclass(frozen=True)
class Cupo:
    destacados_gratis_dia: int | None = None
    mercados_gratis_partido: int | None = None


LIBRE = Cupo()
DEFECTO: dict[tuple[str, str], Cupo] = {
    ('futbol', 'web'): Cupo(None, 3),      # GRATIS_WEB (titular, 28-oct-2026)
    ('futbol', 'app'): Cupo(None, 0),      # la app solo abre sus pronósticos gratis de alta probabilidad
}
# Celdas que no existen en el producto: la app de fútbol no enseña destacado por partido.
NO_APLICA = frozenset({('futbol', 'app', 'destacados_gratis_dia')})

_lock = threading.Lock()
_cache: tuple[float, dict[tuple[str, str], Cupo]] | None = None


def _cargar() -> dict[tuple[str, str], Cupo]:
    try:
        filas = query('SELECT deporte_id, cliente, destacados_gratis_dia, mercados_gratis_partido FROM acceso_cupos')
    except UndefinedTable:
        return {}
    return {(f['deporte_id'], f['cliente']): Cupo(f['destacados_gratis_dia'], f['mercados_gratis_partido'])
            for f in filas}


def _todos() -> dict[tuple[str, str], Cupo]:
    global _cache
    ahora = time.monotonic()
    with _lock:
        if _cache and ahora - _cache[0] < _TTL:
            return _cache[1]
    valor = {**DEFECTO, **_cargar()}
    with _lock:
        _cache = (ahora, valor)
    return valor


def invalidar_cache() -> None:
    global _cache
    with _lock:
        _cache = None


def cupo(deporte: str, cliente: str) -> Cupo:
    return _todos().get((deporte, cliente), LIBRE)


def para_cliente(cliente: str, deportes: list[str]) -> dict[str, Cupo]:
    """Cupos de `cliente` para cada deporte pedido (los que no tienen fila van sin límite)."""
    return {d: cupo(d, cliente) for d in deportes}


def _numero(valor) -> int | None:
    """Campo del formulario: vacío = sin límite; si no, un entero de 0 a `MAXIMO`."""
    if valor is None or str(valor).strip() == '':
        return None
    try:
        n = int(str(valor).strip())
    except ValueError:
        raise ValueError('Usa un número entero, o deja la casilla vacía para «sin límite».') from None
    if not 0 <= n <= MAXIMO:
        raise ValueError(f'El número debe estar entre 0 y {MAXIMO}.')
    return n


def guardar(deporte: str, cliente: str, destacados, mercados, actor: str) -> Cupo:
    if cliente not in CLIENTES:
        raise ValueError('Cliente no válido.')
    nuevo = Cupo(_numero(destacados), _numero(mercados))
    if (deporte, cliente, 'destacados_gratis_dia') in NO_APLICA:
        nuevo = Cupo(None, nuevo.mercados_gratis_partido)
    antes = cupo(deporte, cliente)
    with conn() as c:
        c.execute('''INSERT INTO acceso_cupos (deporte_id, cliente, destacados_gratis_dia, mercados_gratis_partido, updated_by)
                     VALUES (%s,%s,%s,%s,%s)
                     ON CONFLICT (deporte_id, cliente) DO UPDATE SET
                       destacados_gratis_dia=EXCLUDED.destacados_gratis_dia,
                       mercados_gratis_partido=EXCLUDED.mercados_gratis_partido,
                       updated_by=EXCLUDED.updated_by, updated_at=now()''',
                  (deporte, cliente, nuevo.destacados_gratis_dia, nuevo.mercados_gratis_partido, actor))
        audit(c, actor, 'acceso:cupo', detail={
            'deporte': deporte, 'cliente': cliente,
            'antes': {'destacados_gratis_dia': antes.destacados_gratis_dia,
                      'mercados_gratis_partido': antes.mercados_gratis_partido},
            'despues': {'destacados_gratis_dia': nuevo.destacados_gratis_dia,
                        'mercados_gratis_partido': nuevo.mercados_gratis_partido}})
    invalidar_cache()
    return nuevo


def abiertos_del_dia(candidatos: list[tuple[str, float]], limite: int | None) -> set[str] | None:
    """Ids de partido cuyo destacado va abierto. `candidatos` = (id, probabilidad del destacado) de los
    partidos del día. `None` = todos (sin límite). Ganan los de mayor probabilidad; empates por id."""
    if limite is None:
        return None
    orden = sorted(candidatos, key=lambda c: (-float(c[1]), str(c[0])))
    return {str(i) for i, _ in orden[:limite]}
