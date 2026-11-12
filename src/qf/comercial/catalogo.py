"""Catálogo de deportes y mercados que gobierna web y app (db/112, Fase 2 de «Web y App»).

Es presentación (nombre, orden, color, visibilidad), no datos sellados ni evidencia. Sin tabla o con la tabla
vacía, todo se sirve desde la semilla del código (`catalogo_semilla.SEMILLA`): nunca una lista vacía.

Interfaz pública (la usan el endpoint `/cliente/v1/config`, las páginas SSR y el panel):

    deportes_para(cliente: 'web'|'app') -> list[dict]
        (`deportes_para_semilla(cliente)` hace lo mismo sobre la semilla del código, para el asset de la app.)
        La lista `deportes` del contrato 1, ya filtrada: sin deportes `off`, sin familias con `visible_<cliente>`
        falso, por `orden`. Cada deporte: {id, orden, estado, nombre, slug, icono, color, secciones, familias},
        `estado` es el del cliente pedido; `nombre` lleva es,en,pt para web y los 6 idiomas para app; cada familia:
        {id, orden, nombre, subtitulo}. Sin `adaptador`, `updated_by`, `updated_at` ni el estado del otro cliente.
    todos() -> list[dict]
        Catálogo completo para el panel (con `adaptador`, ambos estados, `visible_*`, `updated_*`), por `orden`.
    web_estado(deporte_id: str) -> 'off'|'preview'|'on'     ('off' si el deporte no existe)
    exigir_web(deporte_id: str) -> dependencia de FastAPI
        `dependencies=[Depends(exigir_web('nba'))]`: 404 si el estado web es `off`; si es `preview` deja pasar y
        añade `X-Robots-Tag: noindex` a la respuesta.
    guardar_deporte(deporte_id: str, datos: dict, actor: str) -> None
        Crea o edita un deporte (edición parcial). `datos` admite: nombre, slug, icono, color, secciones, orden,
        estado_web, estado_app, adaptador. `deporte_id` es inmutable. ValueError con mensaje en español si algo falla.
    guardar_familia(deporte_id: str, familia_id: str, datos: dict, actor: str) -> None
        Crea o edita una familia. `datos` admite: nombre, subtitulo, orden, visible_web, visible_app.
    ensure_seeded() -> bool      (True si cargó la semilla; False si ya había deportes o no existe la tabla)
    invalidar_cache() -> None
    ADAPTADORES, IDIOMAS_APP, IDIOMAS_WEB, SECCIONES, ESTADOS

Cada guardado escribe `audit()` con el antes y el después en la misma transacción e invalida la caché (30 s).
Nunca se borra: un deporte o una familia se apaga.
"""
from __future__ import annotations

import copy
import re
import threading
import time

from fastapi import HTTPException, Response
from psycopg.errors import UndefinedTable
from psycopg.types.json import Jsonb

from ..db import conn, query
from .auditoria import audit
from .catalogo_semilla import SEMILLA

ADAPTADORES = ('futbol', 'nba', 'tenis')
IDIOMAS_APP = ('es', 'en', 'pt', 'fr', 'it', 'de')
IDIOMAS_WEB = ('es', 'en', 'pt')
SECCIONES = ('high', 'ladder', 'parley')
ESTADOS = ('off', 'preview', 'on')
CLIENTES = ('web', 'app')
NOMBRE_MAX = 40
SUBTITULO_MAX = 120

_RE_DEPORTE = re.compile(r'^[a-z][a-z0-9_]{1,23}$')
_RE_FAMILIA = re.compile(r'^[a-z][a-z0-9_]{1,31}$')
_RE_SLUG = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
_RE_COLOR = re.compile(r'^#[0-9a-f]{6}$')
_RE_ICONO = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
_TTL = 30.0

_lock = threading.Lock()
_cache: dict = {}


# ── lectura ──────────────────────────────────────────────────────────────────

def _de_semilla() -> list[dict]:
    out = []
    for d in SEMILLA:
        d = copy.deepcopy(d)
        d.setdefault('updated_by', 'codigo')
        d.setdefault('updated_at', None)
        for f in d['familias']:
            f.setdefault('updated_by', 'codigo')
            f.setdefault('updated_at', None)
        out.append(d)
    return _ordenar(out)


def _ordenar(lista: list[dict]) -> list[dict]:
    lista.sort(key=lambda d: (d['orden'], d['deporte_id']))
    for d in lista:
        d['familias'].sort(key=lambda f: (f['orden'], f['familia_id']))
    return lista


def _cargar_real() -> list[dict]:
    try:
        deps = query('SELECT deporte_id, adaptador, orden, icono, color, secciones, nombre, slug, estado_web, '
                     'estado_app, updated_by, updated_at FROM deportes')
        fams = query('SELECT deporte_id, familia_id, orden, nombre, subtitulo, visible_web, visible_app, '
                     'updated_by, updated_at FROM deporte_mercados')
    except UndefinedTable:
        return _de_semilla()
    if not deps:
        return _de_semilla()
    por_dep = {d['deporte_id']: {**d, 'secciones': list(d['secciones']), 'familias': []} for d in deps}
    for f in fams:
        if f['deporte_id'] in por_dep:
            por_dep[f['deporte_id']]['familias'].append(dict(f))
    return _ordenar(list(por_dep.values()))


_cargar = _cargar_real   # las pruebas sustituyen `_cargar`; `_cargar_real` queda para las de Postgres


def _con_cache():
    ahora = time.monotonic()
    with _lock:
        hit = _cache.get('catalogo')
        if hit and ahora - hit[0] < _TTL:
            return hit[1]
    valor = _cargar()
    with _lock:
        _cache['catalogo'] = (ahora, valor)
    return valor


def invalidar_cache() -> None:
    with _lock:
        _cache.clear()


def todos() -> list[dict]:
    """Catálogo completo (copia) para el panel."""
    return copy.deepcopy(_con_cache())


def deportes_para(cliente: str) -> list[dict]:
    """La lista `deportes` del contrato 1 para `cliente` ('web' o 'app')."""
    return _proyectar(cliente, _con_cache())


def deportes_para_semilla(cliente: str) -> list[dict]:
    """Lo mismo, aplicado a la semilla del código (copia de fábrica de la app; ver scripts/generar_catalogo_defecto.py)."""
    return _proyectar(cliente, _de_semilla())


def _proyectar(cliente: str, catalogo: list[dict]) -> list[dict]:
    if cliente not in CLIENTES:
        raise ValueError("cliente debe ser 'web' o 'app'.")
    idiomas = IDIOMAS_WEB if cliente == 'web' else IDIOMAS_APP

    def pick(d: dict) -> dict:
        return {k: v for k, v in d.items() if k in idiomas and v}

    out = []
    for d in catalogo:
        estado = d[f'estado_{cliente}']
        if estado == 'off':
            continue
        out.append({
            'id': d['deporte_id'], 'orden': d['orden'], 'estado': estado,
            'nombre': pick(d['nombre']), 'slug': {k: d['slug'][k] for k in IDIOMAS_WEB if k in d['slug']},
            'icono': d['icono'], 'color': d['color'], 'secciones': list(d['secciones']),
            'familias': [{'id': f['familia_id'], 'orden': f['orden'], 'nombre': pick(f['nombre']),
                          'subtitulo': pick(f['subtitulo'] or {})}
                         for f in d['familias'] if f[f'visible_{cliente}']],
        })
    return out


def web_estado(deporte_id: str) -> str:
    for d in _con_cache():
        if d['deporte_id'] == deporte_id:
            return d['estado_web']
    return 'off'


def exigir_web(deporte_id: str):
    """Dependencia de FastAPI: 404 con el deporte apagado en la web; `noindex` con él en `preview`."""
    def dependencia(response: Response) -> None:
        estado = web_estado(deporte_id)
        if estado == 'off':
            raise HTTPException(status_code=404, detail='No encontrado')
        if estado == 'preview':
            response.headers['X-Robots-Tag'] = 'noindex'
    return dependencia


# ── validación ───────────────────────────────────────────────────────────────

def _nombres(valor, idiomas, etiqueta: str, *, obligatorio: bool, maximo: int) -> dict:
    if not isinstance(valor, dict):
        raise ValueError(f'{etiqueta}: se esperaba un texto por idioma.')
    extra = set(valor) - set(IDIOMAS_APP)
    if extra:
        raise ValueError(f'{etiqueta}: idioma desconocido ({", ".join(sorted(extra))}).')
    out = {}
    for lg in idiomas:
        t = valor.get(lg)
        t = t.strip() if isinstance(t, str) else ''
        if not t:
            if obligatorio:
                raise ValueError(f'{etiqueta}: falta el texto en «{lg}».')
            continue
        if len(t) > maximo:
            raise ValueError(f'{etiqueta} «{lg}»: máximo {maximo} caracteres.')
        out[lg] = t
    return out


def validar_deporte(d: dict) -> dict:
    """Valida un deporte completo; devuelve la versión normalizada."""
    if not isinstance(d.get('deporte_id'), str) or not _RE_DEPORTE.match(d['deporte_id']):
        raise ValueError('El id del deporte debe ser minúsculas, dígitos o «_» (2 a 24, empieza por letra).')
    ad = d.get('adaptador')
    if ad is not None and ad not in ADAPTADORES:
        raise ValueError(f'Adaptador desconocido: {ad}.')
    for k in ('estado_web', 'estado_app'):
        if d.get(k) not in ESTADOS:
            raise ValueError(f'{k} debe ser off, preview u on.')
    if ad is None and (d['estado_web'] != 'off' or d['estado_app'] != 'off'):
        raise ValueError('Un deporte sin adaptador solo admite el estado «off».')
    if not isinstance(d.get('orden'), int) or isinstance(d['orden'], bool) or not -32768 <= d['orden'] <= 32767:
        raise ValueError('El orden debe ser un entero.')
    if not isinstance(d.get('color'), str) or not _RE_COLOR.match(d['color']):
        raise ValueError('El color debe ser #rrggbb en minúscula.')
    icono = d.get('icono') or 'generico'
    if not isinstance(icono, str) or not _RE_ICONO.match(icono):
        raise ValueError('Icono no válido.')
    secc = d.get('secciones')
    if not isinstance(secc, (list, tuple)) or any(s not in SECCIONES for s in secc):
        raise ValueError('Las secciones deben ser high, ladder o parley.')
    slug = d.get('slug')
    if not isinstance(slug, dict) or set(slug) != set(IDIOMAS_WEB):
        raise ValueError('Hacen falta los 3 slugs: es, en y pt.')
    for lg in IDIOMAS_WEB:
        if not isinstance(slug[lg], str) or not _RE_SLUG.match(slug[lg]):
            raise ValueError(f'Slug «{lg}» no válido: minúsculas, dígitos y guiones.')
    return {**d, 'adaptador': ad, 'icono': icono, 'secciones': list(dict.fromkeys(secc)), 'slug': dict(slug),
            'nombre': _nombres(d.get('nombre'), IDIOMAS_APP, 'Nombre', obligatorio=True, maximo=NOMBRE_MAX)}


def validar_familia(f: dict) -> dict:
    if not isinstance(f.get('familia_id'), str) or not _RE_FAMILIA.match(f['familia_id']):
        raise ValueError('El id de la familia debe ser minúsculas, dígitos o «_» (2 a 32, empieza por letra).')
    if not isinstance(f.get('orden'), int) or isinstance(f['orden'], bool) or not -32768 <= f['orden'] <= 32767:
        raise ValueError('El orden debe ser un entero.')
    for k in ('visible_web', 'visible_app'):
        if not isinstance(f.get(k), bool):
            raise ValueError(f'{k} debe ser verdadero o falso.')
    return {**f, 'nombre': _nombres(f.get('nombre'), IDIOMAS_APP, 'Nombre', obligatorio=True, maximo=NOMBRE_MAX),
            'subtitulo': _nombres(f.get('subtitulo') or {}, IDIOMAS_APP, 'Subtítulo', obligatorio=False,
                                  maximo=SUBTITULO_MAX)}


def _validar_conjunto(deportes: list[dict]) -> None:
    """Guarda de servidor: ningún cliente se queda sin un deporte `on`."""
    for cliente in CLIENTES:
        if not any(d[f'estado_{cliente}'] == 'on' for d in deportes):
            nombre = 'la web' if cliente == 'web' else 'la app'
            raise ValueError(f'No se puede dejar {nombre} sin ningún deporte en «on».')


# ── escritura ────────────────────────────────────────────────────────────────

_CAMPOS_DEPORTE = {'nombre', 'slug', 'icono', 'color', 'secciones', 'orden', 'estado_web', 'estado_app', 'adaptador'}
_CAMPOS_FAMILIA = {'nombre', 'subtitulo', 'orden', 'visible_web', 'visible_app'}
_PUBLICOS_DEP = ('adaptador', 'orden', 'icono', 'color', 'secciones', 'nombre', 'slug', 'estado_web', 'estado_app')
_PUBLICOS_FAM = ('orden', 'nombre', 'subtitulo', 'visible_web', 'visible_app')


def ensure_seeded() -> bool:
    """Carga la semilla solo si `deportes` está vacía. Sin tabla, no hace nada."""
    try:
        with conn() as c:
            if c.execute('SELECT 1 FROM deportes LIMIT 1').fetchone():
                return False
            c.execute('LOCK TABLE deportes, deporte_mercados IN SHARE ROW EXCLUSIVE MODE')
            if c.execute('SELECT 1 FROM deportes LIMIT 1').fetchone():
                return False
            for d in SEMILLA:
                d = validar_deporte(d)
                c.execute('INSERT INTO deportes (deporte_id, adaptador, orden, icono, color, secciones, nombre, '
                          'slug, estado_web, estado_app, updated_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                          (d['deporte_id'], d['adaptador'], d['orden'], d['icono'], d['color'], d['secciones'],
                           Jsonb(d['nombre']), Jsonb(d['slug']), d['estado_web'], d['estado_app'], 'semilla'))
                for f in d['familias']:
                    f = validar_familia(f)
                    c.execute('INSERT INTO deporte_mercados (deporte_id, familia_id, orden, nombre, subtitulo, '
                              'visible_web, visible_app, updated_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',
                              (d['deporte_id'], f['familia_id'], f['orden'], Jsonb(f['nombre']),
                               Jsonb(f['subtitulo']), f['visible_web'], f['visible_app'], 'semilla'))
            audit(c, 'sistema', 'catalogo:semilla', detail={'deportes': [d['deporte_id'] for d in SEMILLA]})
    except UndefinedTable:
        return False
    invalidar_cache()
    return True


def _publico(d: dict | None, campos) -> dict | None:
    return None if d is None else {k: d[k] for k in campos}


def guardar_deporte(deporte_id: str, datos: dict, actor: str) -> None:
    """Crea o edita (parcialmente) un deporte. `deporte_id` no cambia nunca."""
    if 'deporte_id' in datos and datos['deporte_id'] != deporte_id:
        raise ValueError('El id del deporte no se puede cambiar.')
    extra = set(datos) - _CAMPOS_DEPORTE - {'deporte_id'}
    if extra:
        raise ValueError(f'Campos no editables: {", ".join(sorted(extra))}.')
    ensure_seeded()
    with conn() as c:
        filas = c.execute('SELECT deporte_id, adaptador, orden, icono, color, secciones, nombre, slug, estado_web, '
                          'estado_app FROM deportes FOR UPDATE').fetchall()
        actuales = {r['deporte_id']: {**r, 'secciones': list(r['secciones'])} for r in filas}
        antes = actuales.get(deporte_id)
        base = antes or {'deporte_id': deporte_id, 'adaptador': None, 'icono': 'generico', 'secciones': [],
                         'estado_web': 'off', 'estado_app': 'off',
                         'orden': 1 + max((r['orden'] for r in actuales.values()), default=0)}
        nuevo = validar_deporte({**base, **{k: v for k, v in datos.items() if k != 'deporte_id'}})
        actuales[deporte_id] = nuevo
        _validar_conjunto(list(actuales.values()))
        vals = (nuevo['adaptador'], nuevo['orden'], nuevo['icono'], nuevo['color'], nuevo['secciones'],
                Jsonb(nuevo['nombre']), Jsonb(nuevo['slug']), nuevo['estado_web'], nuevo['estado_app'], actor)
        if antes is None:
            c.execute('INSERT INTO deportes (adaptador, orden, icono, color, secciones, nombre, slug, estado_web, '
                      'estado_app, updated_by, deporte_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                      vals + (deporte_id,))
        else:
            c.execute('UPDATE deportes SET adaptador=%s, orden=%s, icono=%s, color=%s, secciones=%s, nombre=%s, '
                      'slug=%s, estado_web=%s, estado_app=%s, updated_by=%s, updated_at=now() WHERE deporte_id=%s',
                      vals + (deporte_id,))
        audit(c, actor, 'catalogo:deporte', detail={
            'deporte_id': deporte_id, 'antes': _publico(antes, _PUBLICOS_DEP),
            'despues': _publico(nuevo, _PUBLICOS_DEP)})
    invalidar_cache()


def guardar_familia(deporte_id: str, familia_id: str, datos: dict, actor: str) -> None:
    """Crea o edita (parcialmente) una familia de mercados de un deporte existente."""
    if 'familia_id' in datos and datos['familia_id'] != familia_id:
        raise ValueError('El id de la familia no se puede cambiar.')
    extra = set(datos) - _CAMPOS_FAMILIA - {'familia_id', 'deporte_id'}
    if extra:
        raise ValueError(f'Campos no editables: {", ".join(sorted(extra))}.')
    if 'deporte_id' in datos and datos['deporte_id'] != deporte_id:
        raise ValueError('El deporte de la familia no se puede cambiar.')
    ensure_seeded()
    with conn() as c:
        if not c.execute('SELECT 1 FROM deportes WHERE deporte_id=%s', (deporte_id,)).fetchone():
            raise ValueError('El deporte no existe.')
        antes = c.execute('SELECT orden, nombre, subtitulo, visible_web, visible_app FROM deporte_mercados '
                          'WHERE deporte_id=%s AND familia_id=%s FOR UPDATE', (deporte_id, familia_id)).fetchone()
        if antes is None:
            maximo = c.execute('SELECT COALESCE(MAX(orden), 0) AS m FROM deporte_mercados WHERE deporte_id=%s',
                               (deporte_id,)).fetchone()['m']
            base = {'orden': maximo + 1, 'subtitulo': {}, 'visible_web': True, 'visible_app': True}
        else:
            base = dict(antes)
        nuevo = validar_familia({**base, 'familia_id': familia_id,
                                 **{k: v for k, v in datos.items() if k in _CAMPOS_FAMILIA}})
        vals = (nuevo['orden'], Jsonb(nuevo['nombre']), Jsonb(nuevo['subtitulo']), nuevo['visible_web'],
                nuevo['visible_app'], actor, deporte_id, familia_id)
        if antes is None:
            c.execute('INSERT INTO deporte_mercados (orden, nombre, subtitulo, visible_web, visible_app, '
                      'updated_by, deporte_id, familia_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', vals)
        else:
            c.execute('UPDATE deporte_mercados SET orden=%s, nombre=%s, subtitulo=%s, visible_web=%s, '
                      'visible_app=%s, updated_by=%s, updated_at=now() WHERE deporte_id=%s AND familia_id=%s', vals)
        audit(c, actor, 'catalogo:familia', detail={
            'deporte_id': deporte_id, 'familia_id': familia_id,
            'antes': _publico(antes, _PUBLICOS_FAM), 'despues': _publico(nuevo, _PUBLICOS_FAM)})
    invalidar_cache()
