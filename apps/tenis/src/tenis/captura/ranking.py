"""Captura del ranking oficial semanal desde SportsAPIPro (decisión del titular: única fuente de ranking nueva).

Forma usada por el motor viejo (`scripts/publicar_tenis_estadisticas.py`, worktree apify-detalles-huecos):
  ATP oficial: `rankings/type/5`; WTA: `rankings/wta`. Respuesta `{"data": {"rankings": [ {ranking, points,
  previousRanking, team: {id, name, country}, rowName, country} ]}}`. El `team.id` es el id de SofaScore.
  NO VERIFICADO contra respuesta real: no hay muestra guardada en el repositorio, y en este sprint no hay red.
  Tampoco se ha verificado que `points` llegue como entero (el motor viejo lo convierte con str()).
  Campo de fecha de la clasificación: no aparece en la forma conocida. Se busca `rankingDate` o `date` en `data`;
  si no existe, regla conservadora: lunes anterior o igual a la fecha de la captura (nunca adelanta la publicación).

El transporte es inyectable: `obtener(ruta) -> (estado_http, bytes)`. Aquí no hay implementación de red.
Sin resolver de jugadores no se inventa nada: el nombre va a `sin_resolver`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Protocol

from psycopg.types.json import Jsonb

from ..recibo import Recibo, nuevo_recibo
from . import presupuesto
from .cursor import ejecutar_lote

FUENTE = "sportsapipro"
RUTAS = {"atp": "/rankings/type/5", "wta": "/rankings/wta"}
CAMPOS_FECHA = ("rankingDate", "date")

Resolver = Callable[[str, str, str], int | None]


class Transporte(Protocol):
    def __call__(self, ruta: str) -> tuple[int, bytes]: ...


@dataclass(frozen=True)
class FilaRanking:
    id_fuente: str
    nombre: str
    posicion: int
    puntos: int | None  # None = faltante (nunca 0)


@dataclass
class Analisis:
    aceptado: bool
    motivo: str | None = None
    fecha_publicacion: date | None = None
    regla_fecha: str | None = None
    filas: list[FilaRanking] = field(default_factory=list)


def _rechazo(motivo: str) -> Analisis:
    return Analisis(aceptado=False, motivo=motivo)


def _lunes_en_o_antes(dia: date) -> date:
    return dia - timedelta(days=dia.isoweekday() - 1)


def _fecha(data: dict, recibido_en: datetime) -> tuple[date | None, str | None, str | None]:
    """Devuelve (fecha, regla, motivo_rechazo)."""
    for campo in CAMPOS_FECHA:
        if campo in data:
            valor = data[campo]
            try:
                fecha = date.fromisoformat(valor[:10]) if isinstance(valor, str) else None
            except ValueError:
                fecha = None
            if fecha is None:
                return None, None, "fecha_invalida"
            if fecha.isoweekday() != 1:
                return None, None, "fecha_no_lunes"
            return fecha, "campo", None
    recibido_utc = recibido_en.astimezone(timezone.utc)
    return _lunes_en_o_antes(recibido_utc.date()), "lunes_captura", None


def analizar(cuerpo: bytes, circuito: str, recibido_en: datetime) -> Analisis:
    """Valida una respuesta. Solo rechaza la respuesta entera por forma, fecha o duplicados; las filas sueltas
    mal formadas se descartan y se cuentan por motivo. Una respuesta rechazada no escribe observaciones."""
    if circuito not in RUTAS:
        raise ValueError(f"circuito desconocido: {circuito}")
    try:
        doc = json.loads(cuerpo)
    except (ValueError, UnicodeDecodeError):
        return _rechazo("json_invalido")
    data = doc.get("data") if isinstance(doc, dict) else None
    if not isinstance(data, dict):
        return _rechazo("estructura")
    crudas = data.get("rankings")
    if not isinstance(crudas, list) or not crudas:
        return _rechazo("vacia")
    fecha, regla, motivo = _fecha(data, recibido_en)
    if motivo:
        return _rechazo(motivo)

    filas: list[FilaRanking] = []
    ids_vistos: set[str] = set()
    posiciones_vistas: set[int] = set()
    for fila in crudas:
        # Cualquier fila mal formada rechaza la respuesta entera: una clasificación con huecos no se escribe.
        if not isinstance(fila, dict):
            return _rechazo("fila_no_objeto")
        posicion = fila.get("ranking")
        if type(posicion) is not int or posicion < 1:
            return _rechazo("posicion_invalida")
        equipo = fila.get("team")
        id_bruto = equipo.get("id") if isinstance(equipo, dict) else None
        if type(id_bruto) not in (int, str) or str(id_bruto).strip() == "":
            return _rechazo("id_ausente")
        id_fuente = str(id_bruto)
        nombre = (equipo.get("name") or fila.get("rowName") or "").strip()
        if not nombre:
            return _rechazo("nombre_ausente")
        puntos = fila.get("points")
        if puntos is not None and (type(puntos) is not int or puntos < 0):
            return _rechazo("puntos_invalidos")
        if id_fuente in ids_vistos:
            return _rechazo("jugador_duplicado")
        if posicion in posiciones_vistas:
            return _rechazo("posicion_duplicada")
        ids_vistos.add(id_fuente)
        posiciones_vistas.add(posicion)
        filas.append(FilaRanking(id_fuente, nombre, posicion, puntos))
    return Analisis(True, None, fecha, regla, filas)


@dataclass(frozen=True)
class Resultado:
    estado: str  # 'presupuesto' | 'sin_datos' | 'rechazado' | 'escrito'
    motivo: str | None = None
    escritas: int = 0
    sin_resolver: int = 0
    descartes: dict = field(default_factory=dict)
    recibo_id: int | None = None


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _insertar_recibo(db, r: Recibo, lote: str) -> int:
    fila = db.execute(
        "INSERT INTO recibo (fuente, recurso, parametros, recibido_en, estado_http, sha256, ruta_objeto, bytes, lote, "
        "retro) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, false) "
        "ON CONFLICT (fuente, recurso, sha256, recibido_en) DO NOTHING RETURNING recibo_id",
        (r.fuente, r.recurso, Jsonb(r.parametros), r.recibido_en, r.estado_http, r.sha256, r.ruta_objeto, r.bytes,
         lote),
    ).fetchone()
    if fila:
        return fila[0]
    return db.execute(
        "SELECT recibo_id FROM recibo WHERE fuente = %s AND recurso = %s AND sha256 = %s AND recibido_en = %s",
        (r.fuente, r.recurso, r.sha256, r.recibido_en),
    ).fetchone()[0]


def capturar(db, circuito: str, transporte: Transporte, resolver: Resolver, raiz,
             reloj: Callable[[], datetime] = _ahora) -> Resultado:
    """Una captura del ranking de `circuito`. Gasta 1 petición (reservada antes, confirmada o devuelta después)."""
    if circuito not in RUTAS:
        raise ValueError(f"circuito desconocido: {circuito}")
    ruta = RUTAS[circuito]
    try:
        presupuesto.reservar(db, FUENTE, 1, reloj())
    except presupuesto.PresupuestoError as exc:
        return Resultado("presupuesto", type(exc).__name__)

    estado, cuerpo = transporte(ruta)
    recibido = reloj()
    if estado != 200 or not cuerpo:
        presupuesto.devolver(db, FUENTE, 1, recibido)
        return Resultado("sin_datos", f"http_{estado}" if estado != 200 else "cuerpo_vacio")
    presupuesto.confirmar(db, FUENTE, 1, recibido)

    analisis = analizar(cuerpo, circuito, recibido)
    lote_nombre = f"ranking_{circuito}_{recibido.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    conteo = {"escritas": 0, "sin": 0, "rid": None}

    def lote(conn, _previo):
        objeto = nuevo_recibo(raiz, fuente=FUENTE, recurso=ruta, parametros={"circuito": circuito},
                              recibido_en=recibido, cuerpo=cuerpo, retro=False, estado_http=estado)
        rid = _insertar_recibo(conn, objeto, lote_nombre)
        conteo["rid"] = rid
        if not analisis.aceptado:
            return None
        escritas = 0
        sin = 0
        for f in analisis.filas:
            jugador = resolver(f.id_fuente, f.nombre, circuito)
            if jugador is None:
                conn.execute(
                    "INSERT INTO sin_resolver (fuente, id_fuente, nombre_fuente, motivo, contexto, recibo_id, "
                    "recibido_en) VALUES (%s, %s, %s, 'sin_resolver_ranking', %s, %s, %s)",
                    (FUENTE, f.id_fuente, f.nombre,
                     Jsonb({"circuito": circuito, "posicion": f.posicion, "puntos": f.puntos}), rid, recibido),
                )
                sin += 1
                continue
            if conn.execute(
                "INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, puntos, origen, fuente, "
                "recibo_id, recibido_en) VALUES (%s, %s, %s, %s, %s, 'oficial_capturado', %s, %s, %s) "
                "ON CONFLICT DO NOTHING RETURNING ranking_id",
                (circuito, analisis.fecha_publicacion, jugador, f.posicion, f.puntos, FUENTE, rid, recibido),
            ).fetchone():
                escritas += 1
        conteo["escritas"], conteo["sin"] = escritas, sin
        return analisis.fecha_publicacion.isoformat()

    ejecutar_lote(db, FUENTE, f"ranking_{circuito}", lote)
    if not analisis.aceptado:
        return Resultado("rechazado", analisis.motivo, 0, 0, {}, conteo["rid"])
    return Resultado("escrito", None, conteo["escritas"], conteo["sin"], {}, conteo["rid"])
