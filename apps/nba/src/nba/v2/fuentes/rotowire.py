"""Rotowire: quinteto esperado, probabilidad de jugar, árbitros y minutos proyectados (solo hacia adelante).

`capturar` recibe `obtener(url) -> (http_status, cuerpo)`; el HTTP real vive en `obtener_http`.
La página no trae hora de actualización: `recibido_en` es el instante en que NOSOTROS la recibimos.
"""
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
import html
import json
from pathlib import Path
import re

from .. import carga, equipos, identidad
from ..carga import DatoNuevo

URL_LINEUPS = "https://www.rotowire.com/basketball/nba-lineups.php"
URL_MINUTOS = "https://www.rotowire.com/basketball/ajax/get-projected-minutes.php?team="
FUENTE = "rotowire"


@dataclass(frozen=True)
class JugadorRW:
    id_rw: str
    nombre: str
    posicion: str
    prob_jugar: float
    estado: str | None


@dataclass(frozen=True)
class EquipoRW:
    estado: str                     # "expected" | "confirmed"
    titulares: list[JugadorRW] = field(default_factory=list)
    ausentes: list[JugadorRW] = field(default_factory=list)


@dataclass(frozen=True)
class PartidoRW:
    visitante: str
    local: str
    hora_et: str
    arbitros: list[tuple[str, str]]
    equipos: dict[str, EquipoRW]


@dataclass(frozen=True)
class PaginaRW:
    fecha: date
    partidos: list[PartidoRW]


@dataclass(frozen=True)
class MinutosRW:
    id_rw: str
    nombre: str
    equipo: str
    proy: float | None
    promedio: float | None
    minimo: float | None
    maximo: float | None
    desviacion: float | None
    lineup: str
    estado: str


def _jugador(clase: str, contenido: str) -> JugadorRW:
    pct = re.search(r"is-pct-play-(\d+)", clase)
    nombre = re.search(r'<a title="([^"]*)" href="/basketball/player/[^"]*-(\d+)"', contenido)
    pos = re.search(r'lineup__pos"[^>]*>([^<]*)<', contenido)
    estado = re.search(r'lineup__inj">([^<]+)<', contenido)
    return JugadorRW(id_rw=nombre.group(2), nombre=html.unescape(nombre.group(1)),
                     posicion=pos.group(1).strip() if pos else "",
                     prob_jugar=int(pct.group(1)) / 100 if pct else 1.0,
                     estado=estado.group(1).strip() if estado else None)


def _equipo(lista: str) -> EquipoRW:
    estado, titulares, ausentes, tras_titulo = "expected", [], [], False
    for clase, contenido in re.findall(r'<li class="([^"]*)"[^>]*>(.*?)</li>', lista, re.S):
        if "lineup__status" in clase:
            estado = "confirmed" if "is-confirmed" in clase else "expected"
        elif "lineup__title" in clase:
            tras_titulo = True
        elif "lineup__player" in clase:
            (ausentes if tras_titulo else titulares).append(_jugador(clase, contenido))
    return EquipoRW(estado, titulares, ausentes)


def parsear_lineups(texto: str) -> PaginaRW:
    fecha = re.search(r'data-gamedate="(\d{4}-\d{2}-\d{2})"', texto)
    if not fecha:
        raise ValueError("la página de Rotowire no trae data-gamedate")
    partidos = []
    for bloque in texto.split('<div class="lineup is-nba"')[1:]:
        abreviaturas = re.findall(r'class="lineup__abbr">([A-Z]+)<', bloque)
        if len(abreviaturas) < 2:
            continue
        visitante, local = (equipos.canonico(FUENTE, a) for a in abreviaturas[:2])
        listas = dict(re.findall(r'<ul class="lineup__list is-(visit|home)">(.*?)</ul>', bloque, re.S))
        hora = re.search(r'class="lineup__time">([^<]+)<', bloque)
        arbitros = [(i, html.unescape(n.strip())) for i, n in
                    re.findall(r'<a href="/basketball/ref\.php\?id=(\d+)">([^<]+)</a>', bloque)]
        partidos.append(PartidoRW(visitante=visitante, local=local, hora_et=hora.group(1).strip() if hora else "",
                                  arbitros=arbitros,
                                  equipos={visitante: _equipo(listas.get("visit", "")),
                                           local: _equipo(listas.get("home", ""))}))
    return PaginaRW(date.fromisoformat(fecha.group(1)), partidos)


def parsear_minutos(texto_json: str) -> list[MinutosRW]:
    return [MinutosRW(id_rw=str(x["id"]), nombre=x["name"], equipo=x["team"], proy=x["proj"], promedio=x["avg"],
                      minimo=x["min"], maximo=x["max"], desviacion=x["stdev"], lineup=x["lineup"], estado=x["inj"])
            for x in json.loads(texto_json)]


def a_filas_lineups(db, pagina: PaginaRW, partido: PartidoRW, recibido_en: datetime, captura_id: int) -> list[DatoNuevo]:
    local, visitante = identidad.equipo(db, partido.local), identidad.equipo(db, partido.visitante)
    partido_id = identidad.partido(db, FUENTE, f"{pagina.fecha.isoformat()}:{partido.visitante}@{partido.local}",
                                   pagina.fecha, local, visitante, identidad.temporada(pagina.fecha))
    base = dict(partido_id=partido_id, fase="pre", fuente=FUENTE, recibido_en=recibido_en, captura_id=captura_id)
    filas = []
    for tricode, equipo in partido.equipos.items():
        for j in equipo.titulares + equipo.ausentes:
            jugador = identidad.jugador(db, FUENTE, j.id_rw, j.nombre)
            filas.append(DatoNuevo(entidad_id=jugador, metrica="estado_disponibilidad", valor=j.prob_jugar,
                                   etiqueta=j.estado, **base))
        for j in equipo.titulares:
            filas.append(DatoNuevo(entidad_id=identidad.jugador(db, FUENTE, j.id_rw, j.nombre),
                                   metrica="titular_esperado", valor=1.0, etiqueta=equipo.estado, **base))
    for id_rw, nombre in partido.arbitros:
        filas.append(DatoNuevo(entidad_id=identidad.arbitro(db, FUENTE, id_rw, nombre), metrica="arbitro_asignado",
                               valor=1.0, **base))
    return filas


def a_filas_minutos(db, partido_id: int, minutos: list[MinutosRW], recibido_en: datetime,
                    captura_id: int) -> list[DatoNuevo]:
    base = dict(partido_id=partido_id, fase="pre", fuente=FUENTE, recibido_en=recibido_en, captura_id=captura_id)
    filas = []
    for m in minutos:
        jugador = identidad.jugador(db, FUENTE, m.id_rw, m.nombre)
        for metrica, valor in (("minutos_proyectados", m.proy), ("minutos_promedio_reciente", m.promedio),
                               ("minutos_proyectados_min", m.minimo), ("minutos_proyectados_max", m.maximo),
                               ("minutos_proyectados_desv", m.desviacion)):
            if valor is not None:  # sin partidos recientes la fuente trae null: no se imputa
                filas.append(DatoNuevo(entidad_id=jugador, metrica=metrica, valor=float(valor), **base))
    return filas


def capturar(db, obtener: Callable[[str], tuple[int, bytes]], raiz: Path, ahora: datetime) -> dict:
    """Pide la página y los minutos de los equipos que juegan; nunca imputa lo que la fuente no entrega."""

    def pedir(url: str, fase: str = "pre"):
        try:
            estado, cuerpo = obtener(url)
        except Exception as e:  # red caída, tiempo agotado...
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase=fase, solicitado_en=ahora, ok=False,
                                    error=f"{type(e).__name__}: {e}")
            return None
        if estado != 200:
            carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase=fase, solicitado_en=ahora, ok=False,
                                    http_status=estado, recibido_en=ahora)
            return None
        ruta, huella = carga.guardar_original(raiz, FUENTE, cuerpo, ahora)
        captura = carga.registrar_captura(db, fuente=FUENTE, objetivo=url, fase=fase, solicitado_en=ahora, ok=True,
                                          recibido_en=ahora, http_status=200, sha256=huella, bytes_=len(cuerpo),
                                          ruta=ruta)
        return captura, cuerpo.decode("utf-8")

    respuesta = pedir(URL_LINEUPS)
    if respuesta is None:
        return {"ok": False, "partidos": 0, "datos": 0}
    captura, texto = respuesta
    try:
        pagina = parsear_lineups(texto)
    except ValueError as e:
        carga.registrar_captura(db, fuente=FUENTE, objetivo=URL_LINEUPS, fase="pre", solicitado_en=ahora, ok=False,
                                error=str(e))
        return {"ok": False, "partidos": 0, "datos": 0}
    datos = 0
    for partido in pagina.partidos:
        filas = a_filas_lineups(db, pagina, partido, ahora, captura)
        partido_id = filas[0].partido_id
        for tricode in (partido.visitante, partido.local):
            r = pedir(URL_MINUTOS + tricode)
            if r is not None:
                filas += a_filas_minutos(db, partido_id, parsear_minutos(r[1]), ahora, r[0])
        datos += carga.guardar_datos(db, filas, solo_cambios=True)
    return {"ok": True, "partidos": len(pagina.partidos), "datos": datos}


def obtener_http(url: str) -> tuple[int, bytes]:
    """Petición real (httpx) con cabeceras de navegador; el endpoint de minutos exige X-Requested-With."""
    import httpx
    cabeceras = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                 "Referer": URL_LINEUPS}
    if "/ajax/" in url:
        cabeceras["X-Requested-With"] = "XMLHttpRequest"
    r = httpx.get(url, headers=cabeceras, timeout=20, follow_redirects=True)
    return r.status_code, r.content
