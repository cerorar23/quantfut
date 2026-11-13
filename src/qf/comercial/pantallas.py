"""Definición de pantallas por bloques de «Web y App» (Fase 4, db/113).

Una *definición* dice qué secciones de una pantalla se pintan, en qué orden y qué avisos se intercalan. No trae
datos. Clave: `(pantalla, deporte, cliente)`; `deporte = '*'` vale para todos y el deporte concreto gana sobre `'*'`.
Sin definición publicada, cada cliente usa su orden de hoy (nada cambia hasta que alguien publique).

Interfaz pública:
- `PANTALLAS`, `TIPOS`, `TONOS`, `MAX_BLOQUES`: la lista cerrada (el id de cada sección es el contrato con los clientes).
- `validar(pantalla, bloques) -> list[dict]`: devuelve los bloques normalizados o lanza `ValueError` con un mensaje
  legible; es la ÚNICA fuente de reglas (el panel muestra su mensaje tal cual).
- `validar_clave(pantalla, deporte, cliente)`.
- `guardar_borrador(pantalla, deporte, cliente, bloques, actor)`: valida y guarda el borrador editable.
- `publicar(pantalla, deporte, cliente, nota, actor) -> int`: copia el borrador (revalidado) a una fila NUEVA con la
  `version` siguiente, en la misma transacción que `audit()`. Nunca edita filas publicadas.
- `volver_a(pantalla, deporte, cliente, version, nota, actor) -> int`: publica de nuevo el contenido de una versión
  anterior como versión nueva. No toca el borrador.
- `borrador(...)`, `historial(...)`, `claves()`: lectura para el panel (sin caché).
- `publicadas(cliente) -> {(pantalla, deporte): [bloque]}`: la publicada vigente (mayor `version` de cada clave),
  con caché de 30 s; `invalidar_cache()` la vacía. Sin tabla (`UndefinedTable`) o sin publicación: `{}`.
- `resolver(pantalla, deporte, cliente) -> list | None`: la del deporte si existe; si no, la de `'*'`; si no, `None`.
- `para_entrega(cliente, build=None) -> {pantalla: {deporte: [bloque]}}`: lo que sale en `/cliente/v1/config`;
  con `build` quita los bloques cuyo `build_min_app` es mayor y omite las claves que se quedan sin bloques.
"""
from __future__ import annotations

import copy
import re
import threading
import time

from psycopg.errors import UndefinedTable
from psycopg.types.json import Jsonb

from ..db import conn, query, query_one
from .auditoria import audit

# Pantallas y secciones cerradas: las que ya existen en ambos clientes. Una sección nueva = añadirla aquí + una
# versión de cliente que la pinte (con `build_min_app`). Las tres últimas de `partido` solo existen donde el
# cliente ya tiene esa pieza para el deporte; en un deporte nuevo se ignoran.
PANTALLAS: dict[str, tuple[str, ...]] = {
    'deporte': ('dias', 'resumen', 'destacado', 'partidos'),
    'partido': ('cabecera', 'pronostico', 'mercados', 'contenido', 'sello', 'estadisticas', 'h2h', 'alertas'),
}
TIPOS = ('seccion', 'aviso', 'vip')
TONOS = ('info', 'exito', 'aviso', 'peligro')
CLIENTES = ('web', 'app')
IDIOMAS_APP = ('es', 'en', 'pt', 'fr', 'it', 'de')
IDIOMAS_WEB = ('es', 'en', 'pt')
MAX_BLOQUES = 20
TEXTO_MAX = 300
NOTA_MAX = 500
TODOS = '*'

# Rutas web existentes a las que puede apuntar un aviso (frontend/rutas.js ROUTE_PATH; tests/test_pantallas.py
# comprueba que son rutas reales de rutas_web.SECCIONES). A ellas se suma `/<slug>/` de cada deporte del catálogo.
RUTAS_ENLACE = ('/', '/partidos/', '/pronosticos/', '/historial/', '/pronosticos-alta-probabilidad/',
                '/parley-del-dia/', '/reto-escalera/', '/paquetes/', '/planes/')

_RE_ID = re.compile(r'^[a-z0-9_]{1,40}$')
_RE_DEPORTE = re.compile(r'^[a-z][a-z0-9_]{1,23}$')
_CAMPOS = {'id', 'tipo', 'seccion', 'visible', 'params', 'build_min_app'}
_TTL = 30.0

_lock = threading.Lock()
_cache: dict = {}


# --- validación -----------------------------------------------------------------------------------------

def validar_clave(pantalla: str, deporte: str, cliente: str) -> None:
    if pantalla not in PANTALLAS:
        raise ValueError(f'Pantalla desconocida: {pantalla!r}. Valen: {", ".join(PANTALLAS)}.')
    if deporte != TODOS and not _RE_DEPORTE.match(deporte or ''):
        raise ValueError(f'Deporte no válido: {deporte!r} (usa «*» para todos o el id de un deporte).')
    if cliente not in CLIENTES:
        raise ValueError(f'Cliente desconocido: {cliente!r}. Valen: {", ".join(CLIENTES)}.')


def _rutas_validas() -> set[str]:
    rutas = set(RUTAS_ENLACE)
    try:
        from . import catalogo
        for d in catalogo.todos():
            for slug in (d.get('slug') or {}).values():
                rutas.add(f'/{slug}/')
    except Exception:   # noqa: BLE001 - sin catálogo valen las rutas fijas
        pass
    return rutas


def _validar_aviso(prefijo: str, params) -> dict:
    if not isinstance(params, dict):
        raise ValueError(f'{prefijo}: los parámetros del aviso deben ser un objeto.')
    sobran = set(params) - {'texto', 'tono', 'enlace'}
    if sobran:
        raise ValueError(f'{prefijo}: parámetros no admitidos en un aviso: {", ".join(sorted(sobran))}.')
    texto = params.get('texto')
    if not isinstance(texto, dict) or set(texto) != set(IDIOMAS_APP):
        raise ValueError(f'{prefijo}: el texto del aviso debe estar en los 6 idiomas ({", ".join(IDIOMAS_APP)}).')
    limpio = {}
    for lg in IDIOMAS_APP:
        valor = texto[lg]
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f'{prefijo}: falta el texto del aviso en «{lg}».')
        if len(valor.strip()) > TEXTO_MAX:
            raise ValueError(f'{prefijo}: el texto en «{lg}» supera {TEXTO_MAX} caracteres.')
        limpio[lg] = valor.strip()
    tono = params.get('tono')
    if tono not in TONOS:
        raise ValueError(f'{prefijo}: el tono del aviso debe ser {", ".join(TONOS)}.')
    out = {'texto': limpio, 'tono': tono}
    enlace = params.get('enlace')
    if enlace not in (None, ''):
        if not isinstance(enlace, str) or enlace not in _rutas_validas():
            raise ValueError(f'{prefijo}: el enlace debe ser una ruta relativa existente de la app '
                             f'(por ejemplo {", ".join(RUTAS_ENLACE[:4])}).')
        out['enlace'] = enlace
    return out


def validar(pantalla: str, bloques) -> list[dict]:
    """Normaliza y valida los bloques de una pantalla. `ValueError` con mensaje legible si algo no cumple."""
    if pantalla not in PANTALLAS:
        raise ValueError(f'Pantalla desconocida: {pantalla!r}. Valen: {", ".join(PANTALLAS)}.')
    if not isinstance(bloques, list):
        raise ValueError('Los bloques deben ser una lista.')
    if len(bloques) > MAX_BLOQUES:
        raise ValueError(f'Como mucho {MAX_BLOQUES} bloques por pantalla (hay {len(bloques)}).')
    secciones = PANTALLAS[pantalla]
    vistos: set[str] = set()
    secciones_vistas: set[str] = set()
    salida: list[dict] = []
    visibles = 0
    for n, b in enumerate(bloques, 1):
        if not isinstance(b, dict):
            raise ValueError(f'Bloque {n}: debe ser un objeto.')
        bid = b.get('id')
        pre = f'Bloque {n}' + (f' («{bid}»)' if isinstance(bid, str) and bid else '')
        sobran = set(b) - _CAMPOS
        if sobran:
            raise ValueError(f'{pre}: campos no admitidos: {", ".join(sorted(sobran))}.')
        if not isinstance(bid, str) or not _RE_ID.match(bid):
            raise ValueError(f'{pre}: el id debe cumplir ^[a-z0-9_]{{1,40}}$.')
        if bid in vistos:
            raise ValueError(f'{pre}: el id «{bid}» está repetido en la pantalla.')
        vistos.add(bid)
        tipo = b.get('tipo')
        if tipo not in TIPOS:
            raise ValueError(f'{pre}: tipo no válido; valen {", ".join(TIPOS)}.')
        visible = b.get('visible', True)
        if not isinstance(visible, bool):
            raise ValueError(f'{pre}: «visible» debe ser verdadero o falso.')
        minimo = b.get('build_min_app')
        if minimo is not None and (isinstance(minimo, bool) or not isinstance(minimo, int) or minimo < 0):
            raise ValueError(f'{pre}: build_min_app debe ser un entero ≥ 0 o estar vacío.')
        params = b.get('params', {})
        seccion = b.get('seccion')
        if tipo == 'seccion':
            if seccion not in secciones:
                raise ValueError(f'{pre}: la sección debe ser una de {", ".join(secciones)} '
                                 f'para la pantalla «{pantalla}».')
            if seccion in secciones_vistas:
                raise ValueError(f'{pre}: la sección «{seccion}» ya está en la pantalla.')
            secciones_vistas.add(seccion)
            if params not in ({}, None):
                raise ValueError(f'{pre}: una sección no admite parámetros.')
            params = {}
            if visible:
                visibles += 1
        else:
            if seccion not in (None, ''):
                raise ValueError(f'{pre}: solo los bloques de tipo «seccion» llevan sección.')
            seccion = None
            if tipo == 'aviso':
                params = _validar_aviso(pre, params)
            else:
                if params not in ({}, None):
                    raise ValueError(f'{pre}: la llamada VIP no admite parámetros.')
                params = {}
        salida.append({'id': bid, 'tipo': tipo, 'seccion': seccion, 'visible': visible, 'params': params,
                       'build_min_app': minimo})
    if not visibles:
        raise ValueError('Debe haber al menos una sección visible.')
    return salida


# --- escritura ------------------------------------------------------------------------------------------

def guardar_borrador(pantalla: str, deporte: str, cliente: str, bloques, actor: str) -> list[dict]:
    validar_clave(pantalla, deporte, cliente)
    limpios = validar(pantalla, bloques)
    with conn() as c:
        c.execute('INSERT INTO pantalla_borradores (pantalla, deporte, cliente, bloques, updated_by) '
                  'VALUES (%s,%s,%s,%s,%s) ON CONFLICT (pantalla, deporte, cliente) DO UPDATE SET '
                  'bloques=EXCLUDED.bloques, updated_by=EXCLUDED.updated_by, updated_at=now()',
                  (pantalla, deporte, cliente, Jsonb(limpios), actor))
        audit(c, actor, 'pantallas:borrador', detail={'pantalla': pantalla, 'deporte': deporte,
                                                       'cliente': cliente, 'bloques': len(limpios)})
    return limpios


def _nota(nota: str) -> str:
    nota = (nota or '').strip()
    if not nota:
        raise ValueError('La nota es obligatoria.')
    if len(nota) > NOTA_MAX:
        raise ValueError(f'La nota no puede pasar de {NOTA_MAX} caracteres.')
    return nota


def _insertar_version(c, pantalla, deporte, cliente, limpios, nota, actor, accion, extra=None) -> int:
    clave = f'pantallas:{pantalla}:{deporte}:{cliente}'
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (clave,))   # dos publicaciones a la vez no repiten versión
    version = c.execute(
        'SELECT COALESCE(MAX(version), 0) + 1 AS v FROM pantalla_publicaciones '
        'WHERE pantalla=%s AND deporte=%s AND cliente=%s', (pantalla, deporte, cliente)).fetchone()['v']
    c.execute('INSERT INTO pantalla_publicaciones (pantalla, deporte, cliente, version, bloques, publicado_por, nota) '
              'VALUES (%s,%s,%s,%s,%s,%s,%s)',
              (pantalla, deporte, cliente, version, Jsonb(limpios), actor, nota))
    audit(c, actor, accion, detail={'pantalla': pantalla, 'deporte': deporte, 'cliente': cliente,
                                    'version': version, 'nota': nota, **(extra or {})})
    return version


def publicar(pantalla: str, deporte: str, cliente: str, nota: str, actor: str) -> int:
    validar_clave(pantalla, deporte, cliente)
    nota = _nota(nota)
    fila = query_one('SELECT bloques FROM pantalla_borradores WHERE pantalla=%s AND deporte=%s AND cliente=%s',
                     (pantalla, deporte, cliente))
    if not fila:
        raise ValueError('No hay borrador que publicar para esta clave: guárdalo primero.')
    limpios = validar(pantalla, fila['bloques'])    # el borrador se revalida: las reglas pudieron endurecerse
    with conn() as c:
        version = _insertar_version(c, pantalla, deporte, cliente, limpios, nota, actor, 'pantallas:publicar')
    invalidar_cache()
    return version


def volver_a(pantalla: str, deporte: str, cliente: str, version: int, nota: str, actor: str) -> int:
    validar_clave(pantalla, deporte, cliente)
    nota = _nota(nota)
    fila = query_one('SELECT bloques FROM pantalla_publicaciones WHERE pantalla=%s AND deporte=%s AND cliente=%s '
                     'AND version=%s', (pantalla, deporte, cliente, version))
    if not fila:
        raise ValueError(f'La versión {version} no existe para esta clave.')
    limpios = validar(pantalla, fila['bloques'])
    with conn() as c:
        nueva = _insertar_version(c, pantalla, deporte, cliente, limpios, nota, actor, 'pantallas:volver',
                                  {'copia_de': version})
    invalidar_cache()
    return nueva


# --- lectura para el panel (sin caché) ------------------------------------------------------------------

def borrador(pantalla: str, deporte: str, cliente: str) -> dict | None:
    try:
        return query_one('SELECT bloques, updated_by, updated_at FROM pantalla_borradores '
                         'WHERE pantalla=%s AND deporte=%s AND cliente=%s', (pantalla, deporte, cliente))
    except UndefinedTable:
        return None


def historial(pantalla: str, deporte: str, cliente: str) -> list[dict]:
    """Versiones publicadas de una clave, de la más nueva a la más antigua."""
    try:
        return query('SELECT version, bloques, publicado_por, publicado_en, nota FROM pantalla_publicaciones '
                     'WHERE pantalla=%s AND deporte=%s AND cliente=%s ORDER BY version DESC',
                     (pantalla, deporte, cliente))
    except UndefinedTable:
        return []


def claves() -> list[dict]:
    """Claves con borrador o publicación: versión vigente, y si el borrador difiere de lo publicado."""
    try:
        filas = query(
            'SELECT k.pantalla, k.deporte, k.cliente, p.version, p.publicado_en, b.bloques AS borrador, '
            'p.bloques AS publicado FROM (SELECT pantalla, deporte, cliente FROM pantalla_borradores '
            'UNION SELECT pantalla, deporte, cliente FROM pantalla_publicaciones) k '
            'LEFT JOIN LATERAL (SELECT version, bloques, publicado_en FROM pantalla_publicaciones x '
            'WHERE x.pantalla=k.pantalla AND x.deporte=k.deporte AND x.cliente=k.cliente '
            'ORDER BY version DESC LIMIT 1) p ON TRUE '
            'LEFT JOIN pantalla_borradores b USING (pantalla, deporte, cliente) '
            'ORDER BY k.pantalla, k.deporte, k.cliente')
    except UndefinedTable:
        return []
    return [{'pantalla': f['pantalla'], 'deporte': f['deporte'], 'cliente': f['cliente'], 'version': f['version'],
             'publicado_en': f['publicado_en'], 'tiene_borrador': f['borrador'] is not None,
             'difiere': f['borrador'] is not None and f['borrador'] != f['publicado']} for f in filas]


# --- lectura con caché (entrega) ------------------------------------------------------------------------

def _cargar() -> dict:
    try:
        filas = query('SELECT DISTINCT ON (pantalla, deporte, cliente) pantalla, deporte, cliente, bloques '
                      'FROM pantalla_publicaciones ORDER BY pantalla, deporte, cliente, version DESC')
    except UndefinedTable:
        return {}
    return {(f['pantalla'], f['deporte'], f['cliente']): f['bloques'] for f in filas}


def _todas() -> dict:
    ahora = time.monotonic()
    with _lock:
        hit = _cache.get('pantallas')
        if hit and ahora - hit[0] < _TTL:
            return hit[1]
    valor = _cargar()
    with _lock:
        _cache['pantallas'] = (ahora, valor)
    return valor


def invalidar_cache() -> None:
    with _lock:
        _cache.clear()


def publicadas(cliente: str) -> dict[tuple[str, str], list[dict]]:
    """La publicada vigente de cada `(pantalla, deporte)` del cliente (copia)."""
    return {(p, d): copy.deepcopy(b) for (p, d, c), b in _todas().items() if c == cliente}


def resolver(pantalla: str, deporte: str, cliente: str) -> list[dict] | None:
    """El deporte concreto gana sobre `'*'`; sin ninguna, `None` (el cliente usa su orden de hoy)."""
    todas = publicadas(cliente)
    return todas.get((pantalla, deporte)) or todas.get((pantalla, TODOS))


def para_entrega(cliente: str, build: int | None = None) -> dict[str, dict[str, list[dict]]]:
    """Forma de `/cliente/v1/config`: `{pantalla: {deporte|'*': [bloque]}}`, solo claves con bloques."""
    salida: dict[str, dict[str, list[dict]]] = {}
    for (pantalla, deporte), bloques in sorted(publicadas(cliente).items()):
        if build is not None:
            bloques = [b for b in bloques if b.get('build_min_app') is None or b['build_min_app'] <= build]
        if bloques:
            salida.setdefault(pantalla, {})[deporte] = bloques
    return salida
