"""Contrato común por deporte: `GET /deportes/v1/{deporte}/…` (`contrato: 1`, Fase 3 parte A de «Web y App»).

Especificación: `harness/tareas.md`, «Especificación de la Fase 3». Este módulo es SOLO la base: el router, los
modelos, el registro de adaptadores y las reglas comunes. No conoce ningún deporte; los datos los pone un adaptador.

Endpoints (públicos, anónimos, cacheables; no miran `Authorization` ni cookies):

    GET /deportes/v1/{deporte}/cartelera?cliente=web|app&desde=AAAA-MM-DD&dias=1..7&tz=-720..840&contrato=1
        -> {contrato, deporte, desde, dias, eventos: [Evento]}      Cache-Control: public, max-age=30
        Ventana [desde 00:00, desde+dias 00:00) en la zona de `tz` (`fichas.ventana`); sin `desde`, hoy en esa zona.
        Orden por `start` y luego `id`. En la cartelera cada evento lleva solo el mercado destacado (o ninguno).
    GET /deportes/v1/{deporte}/partido/{id}?cliente=…
        -> {contrato, deporte, evento: Evento, bloques: []}         Cache-Control: public, max-age=60
        `bloques` está reservado y siempre vacío (lo rellena la Fase 4).
    GET /deportes/v1/{deporte}/partido/{id}/mercados?cliente=…
        -> {contrato, deporte, evento_id, familias: [{id, mercados: [Mercado]}]}      max-age=60
        Familias en el orden del catálogo (`deporte_mercados`), solo las visibles para ese cliente y con mercados; lo
        que `familia_de` no resuelve a una familia del catálogo va a una familia final `otros`. Los mercados de una
        familia que el catálogo oculta a ese cliente no salen en este endpoint.

`deporte` es el `deporte_id` del catálogo. `cliente` es obligatorio y aplica su estado: `off` o inexistente -> 404;
`preview` -> igual de accesible (todo este JSON sale ya con `X-Robots-Tag: noindex`). `contrato` distinto de 1 -> 422.
Todas las respuestas llevan `ETag` débil del JSON canónico (304 con `If-None-Match`) y `X-Robots-Tag: noindex`.

Fallos: partido inexistente o de otro deporte -> 404. Un adaptador que lanza, o que devuelve algo que no cumple los
modelos, -> 503 `{"detail": ...}` (nunca un 200 con lista vacía que parezca «sin partidos»). Deporte encendido sin
adaptador registrado -> 503 «adaptador no disponible».

── Cómo añadir un adaptador (tenis, NBA, fútbol, …) ─────────────────────────────────────────────────────────────

1. Escribe una clase con estos tres métodos (la interfaz es `Adaptador`; basta con cumplirla, no hay que heredar):

       def cartelera(self, inicio: datetime, fin: datetime) -> list[Evento]
           Eventos con `inicio <= start < fin` (ambos datetimes UTC con zona). Cada `Evento` con `markets` vacío o con el
           destacado; el router recorta el resto, ordena y descarta lo que caiga fuera de la ventana.
       def partido(self, id: str) -> Evento | None
           El evento con TODOS sus mercados públicos, o `None` si no existe. Nada de lo que depende del usuario
           (VIP, desbloqueos, Escalera, parley): solo `bloqueados` como recuento.
       def familia_de(self, market: str) -> str
           Id de familia del catálogo para la clave del motor (`Mercado.market`). Si no sabes, devuelve cualquier cosa que
           no sea una familia del catálogo: el router la manda a `otros`.

   Construye `Evento` y `Mercado` campo a campo desde la fuente (nunca `**fila`): los modelos son `extra='forbid'`.
   `Mercado.eligible` lo calcula el adaptador (`False` si el sello es posterior al inicio). Si la fuente falla, deja
   subir la excepción: el router la convierte en 503. No captures errores para devolver una lista vacía.
2. Regístralo: `ADAPTADORES['<clave>'] = MiAdaptador()`, donde `<clave>` es el campo `adaptador` del deporte en el
   catálogo (hoy `futbol`, `nba` o `tenis`, ver `catalogo.ADAPTADORES`). Hazlo en el módulo del adaptador y impórtalo
   desde `main.py` (o añade la línea aquí cuando exista), no dentro de este archivo de base.
3. Pasa la suite de contrato: en `tests/test_deportes_v1.py`, añade un `Caso` a `CASOS` (un `pytest.param`). Un `Caso` dice cómo
   instalar el adaptador con datos fijos (`instalar(monkeypatch)`), cómo hacer que su fuente falle (`romper`), la fecha
   donde hay datos (`desde`), un `partido_id` con varios mercados y los `centinelas` (valores privados de la fuente que
   no pueden aparecer en ninguna respuesta). Toda la suite corre sola para ese caso. Después añade tu prueba de
   paridad (mismos datos de entrada que `nbaV2Events`/`tennisEvents`/`football()` -> mismos `id`, `home`, `away`, `start`,
   `probability`) en un archivo propio o al final del de contrato.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, Protocol, runtime_checkable

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, field_validator

from ..comercial import catalogo
from . import fichas
from .cliente_config import Cliente, _coincide, _etag

log = logging.getLogger(__name__)
router = APIRouter(tags=['deportes'])

CONTRATO = 1
FAMILIA_OTROS = 'otros'
_RE_RUTA_RELATIVA = r'^/[^/]'      # ruta del propio servidor: empieza por «/» y no es «//host»

Estado = Literal['scheduled', 'live', 'awaiting_result', 'finished', 'cancelled']
Resultado = Literal['win', 'loss', 'push', 'void']


# ── modelos ──────────────────────────────────────────────────────────────────

class _Modelo(BaseModel):
    model_config = ConfigDict(extra='forbid')


def _utc(v: datetime | None) -> datetime | None:
    return v.astimezone(timezone.utc) if v is not None else None


class Mercado(_Modelo):
    id: str
    label: str
    selection: str
    probability: float = Field(gt=0, lt=1)
    sealed_at: AwareDatetime | None = None
    eligible: bool
    market: str
    family: str
    line: float | None = None
    player: str | None = None
    player_id: str | None = None
    price: float | None = None
    reference: str | None = None
    outcome: Resultado | None = None
    push_probability: float | None = Field(default=None, ge=0, le=1)

    _a_utc = field_validator('sealed_at')(_utc)


class Imagenes(_Modelo):
    home: str | None = Field(default=None, pattern=_RE_RUTA_RELATIVA)
    away: str | None = Field(default=None, pattern=_RE_RUTA_RELATIVA)


class Evento(_Modelo):
    id: str
    sport: str
    home: str
    away: str
    league: str
    start: AwareDatetime
    status: Estado
    seal: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    sealed_at: AwareDatetime | None = None
    planned_seal: AwareDatetime | None = None
    score: str | None = None
    surface: str | None = None
    bloqueados: int = Field(default=0, ge=0)
    imagenes: Imagenes | None = None
    markets: list[Mercado] = Field(default_factory=list)
    destacado: str | None = None

    _a_utc = field_validator('start', 'sealed_at', 'planned_seal')(_utc)


class Cartelera(_Modelo):
    contrato: Literal[1] = 1
    deporte: str
    desde: str
    dias: int
    eventos: list[Evento]


class Partido(_Modelo):
    contrato: Literal[1] = 1
    deporte: str
    evento: Evento
    bloques: list[dict] = Field(default_factory=list)   # reservado para la Fase 4


class FamiliaMercados(_Modelo):
    id: str
    mercados: list[Mercado]


class Mercados(_Modelo):
    contrato: Literal[1] = 1
    deporte: str
    evento_id: str
    familias: list[FamiliaMercados]


# ── adaptadores ──────────────────────────────────────────────────────────────

@runtime_checkable
class Adaptador(Protocol):
    def cartelera(self, inicio: datetime, fin: datetime) -> list[Evento]: ...
    def partido(self, id: str) -> Evento | None: ...
    def familia_de(self, market: str) -> str: ...


# Clave = campo `adaptador` del catálogo. Vacío en la base; cada adaptador se registra al importarse.
ADAPTADORES: dict[str, Adaptador] = {}


# ── resolución común ─────────────────────────────────────────────────────────

class _Ctx:
    def __init__(self, deporte: str, cliente: Cliente):
        fila = next((d for d in catalogo.todos() if d['deporte_id'] == deporte), None)
        if fila is None or fila[f'estado_{cliente.value}'] == 'off':
            raise HTTPException(404, 'No encontrado')
        self.id = deporte
        self.cliente = cliente.value
        self.familias = [f['familia_id'] for f in fila['familias'] if f[f'visible_{cliente.value}']]
        self.ocultas = {f['familia_id'] for f in fila['familias'] if not f[f'visible_{cliente.value}']}
        adaptador = ADAPTADORES.get(fila['adaptador'] or '')
        if adaptador is None:
            raise HTTPException(503, 'Adaptador no disponible')
        self.adaptador = adaptador


def _fallo(deporte: str, error: Exception) -> HTTPException:
    log.warning('deportes/v1 %s: la fuente falló (%s: %s)', deporte, type(error).__name__, error)
    return HTTPException(503, 'Fuente no disponible')


def _llamar(ctx: _Ctx, fn, *args):
    """Ejecuta el adaptador: cualquier excepción o dato fuera de contrato es un 503, no un 200 vacío."""
    try:
        return fn(*args)
    except HTTPException:
        raise
    except (Exception, ValidationError) as e:
        raise _fallo(ctx.id, e)


def _evento(ctx: _Ctx, bruto: Any) -> Evento:
    try:
        ev = bruto if isinstance(bruto, Evento) else Evento.model_validate(bruto)
        ev = Evento.model_validate(ev.model_dump())      # revalida lo construido con model_construct o mutado
    except ValidationError as e:
        raise _fallo(ctx.id, e)
    return ev


def _responder(request: Request, modelo: BaseModel, max_age: int) -> Response:
    cuerpo = modelo.model_dump(mode='json')
    etag = _etag(cuerpo)
    cabeceras = {'ETag': etag, 'Cache-Control': f'public, max-age={max_age}', 'X-Robots-Tag': 'noindex'}
    if _coincide(request.headers.get('if-none-match'), etag):
        return Response(status_code=304, headers=cabeceras)
    return Response(json.dumps(cuerpo, ensure_ascii=False, separators=(',', ':')).encode('utf-8'),
                    media_type='application/json', headers=cabeceras)


_PATH_DEPORTE = Path(..., min_length=1, max_length=40)
_PATH_ID = Path(..., min_length=1, max_length=120)


# ── endpoints ────────────────────────────────────────────────────────────────

@router.get('/deportes/v1/{deporte}/cartelera', response_model=Cartelera)
def cartelera(request: Request, deporte: str = _PATH_DEPORTE, cliente: Cliente = Query(...),
              desde: str | None = Query(None, pattern=r'^\d{4}-\d{2}-\d{2}$'),
              dias: int = Query(1, ge=1, le=7), tz: int = Query(0, ge=-720, le=840),
              contrato: int = Query(CONTRATO, ge=1, le=1)):
    if desde:
        try:
            date.fromisoformat(desde)
        except ValueError:
            raise HTTPException(422, 'desde no es una fecha válida')
    ctx = _Ctx(deporte, cliente)
    inicio, fin = fichas.ventana(desde, tz, dias)
    eventos = [_evento(ctx, e) for e in _llamar(ctx, ctx.adaptador.cartelera, inicio, fin)]
    salida: list[Evento] = []
    for ev in eventos:
        if ev.sport != deporte:
            raise _fallo(deporte, ValueError(f'evento {ev.id} es de {ev.sport}'))
        if not inicio <= ev.start < fin:
            continue
        ev.markets = [m for m in ev.markets if m.id == ev.destacado]     # cartelera: solo el destacado
        salida.append(ev)
    salida.sort(key=lambda e: (e.start, e.id))
    cuerpo = Cartelera(deporte=deporte, desde=(inicio + timedelta(minutes=tz)).strftime('%Y-%m-%d'), dias=dias,
                       eventos=salida)
    return _responder(request, cuerpo, 30)


def _partido(ctx: _Ctx, id: str) -> Evento:
    bruto = _llamar(ctx, ctx.adaptador.partido, id)
    if bruto is None:
        raise HTTPException(404, 'No encontrado')
    ev = _evento(ctx, bruto)
    if ev.sport != ctx.id or ev.id != id:
        raise HTTPException(404, 'No encontrado')
    return ev


@router.get('/deportes/v1/{deporte}/partido/{id}', response_model=Partido)
def partido(request: Request, deporte: str = _PATH_DEPORTE, id: str = _PATH_ID, cliente: Cliente = Query(...),
            contrato: int = Query(CONTRATO, ge=1, le=1)):
    ctx = _Ctx(deporte, cliente)
    return _responder(request, Partido(deporte=deporte, evento=_partido(ctx, id)), 60)


@router.get('/deportes/v1/{deporte}/partido/{id}/mercados', response_model=Mercados)
def mercados(request: Request, deporte: str = _PATH_DEPORTE, id: str = _PATH_ID, cliente: Cliente = Query(...),
             contrato: int = Query(CONTRATO, ge=1, le=1)):
    ctx = _Ctx(deporte, cliente)
    ev = _partido(ctx, id)
    grupos: dict[str, list[Mercado]] = {f: [] for f in ctx.familias}
    grupos[FAMILIA_OTROS] = []
    for m in ev.markets:
        fam = _llamar(ctx, ctx.adaptador.familia_de, m.market)
        if fam in ctx.ocultas:
            continue
        grupos[fam if fam in grupos and fam != FAMILIA_OTROS else FAMILIA_OTROS].append(m)
    familias = [FamiliaMercados(id=f, mercados=ms) for f, ms in grupos.items() if ms]
    return _responder(request, Mercados(deporte=deporte, evento_id=ev.id, familias=familias), 60)
