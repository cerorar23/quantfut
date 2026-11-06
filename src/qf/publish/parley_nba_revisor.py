"""Revisor del parley NBA (cada 5 minutos): parleys por partido y de varios partidos, con el sello del pronóstico.

Un partido es elegible cuando su pronóstico NBA ya está sellado (``nba-api /nba/v1/cartelera``), ya llegó
``max(inicio − 60 min, sellado)`` y falta más de ``inicio − 30 min``. Con los partidos elegibles:

* por partido: un parley de un solo evento con varios mercados (same-game → ``solo_referencia`` sin cuota de
  paquete y modelo conjunto), ``parley_nba_datos.ejecutar_partido``;
* de varios partidos: los cuatro targets del selector v2 con patas de varios partidos y mercados
  (ganador, hándicap, totales y props), una sola vez por día de la cartelera, cuando hay ``MIN_PARTIDOS``
  elegibles o al llegar al último momento del primer partido (inicio − 31 min).
Antes de sellar se revalidan jugadores, horario y cuota con ``parley_nba.revalidar``; las patas que fallan se
sacan y se recalcula una vez. Las fuentes llegan por parámetro (pruebas) o por ``main`` (producción).
"""
from __future__ import annotations

import json
import logging
import os
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from . import parley_nba as nba
from . import parley_nba_datos as nd
from . import parley_v2 as v2
from . import parley_v2_datos as base

log = logging.getLogger(__name__)
MIN_PARTIDOS = 3
ULTIMO_MOMENTO = timedelta(minutes=31)


@dataclass(frozen=True)
class Juego:
    id: int
    local: str
    visitante: str
    inicio: datetime
    sellado: datetime | None


def _t(v) -> datetime | None:
    return None if not v else datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)


def juegos_de_cartelera(cartelera: dict) -> list[Juego]:
    out = []
    for p in cartelera.get("partidos", []):
        inicio = _t(p.get("inicio_utc"))
        if inicio is None:
            continue
        out.append(Juego(int(p["id"]), p["local"]["nombre"], p["visitante"]["nombre"], inicio,
                         _t((p.get("pronostico") or {}).get("sellado_en"))))
    return out


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if c.isalnum())


def emparejar(juegos: list[Juego], eventos: list[dict], tolerancia: timedelta = timedelta(minutes=15)) -> dict[int, str]:
    """{id NBA → id del evento PropLine} por equipos y hora de inicio. Sin pareja única no se empareja."""
    out: dict[int, str] = {}
    for j in juegos:
        cand = [e for e in eventos
                if _norm(e["home_team"]) == _norm(j.local) and _norm(e["away_team"]) == _norm(j.visitante)
                and abs(_t(e["commence_time"]) - j.inicio) <= tolerancia]
        if len(cand) == 1:
            out[j.id] = str(cand[0]["id"])
    return out


def elegibles(now: datetime, juegos: list[Juego]) -> list[Juego]:
    return [j for j in juegos if nba.puede_ejecutarse(now, j.inicio, j.sellado)[0]]


def toca_multipartido(now: datetime, listos: list[Juego]) -> bool:
    if len(listos) < 2:
        return False
    return len(listos) >= MIN_PARTIDOS or now >= min(j.inicio for j in listos) - ULTIMO_MOMENTO


def ejecutar_multipartido(now: datetime, dia: date, ids_evento: list[str], cargar_ops: Callable,
                          leer_contexto: Callable, dry_run: bool = False, artefacto: dict | None = None) -> dict:
    """Un ticket por target con patas de varios partidos NBA, sellado en el lote ``nba_dia``."""
    if not base.habilitado() and not dry_run:
        return {"estado": "desactivado"}
    clave = f"{v2.ESTRATEGIA}|{v2.VERSION}|nba_dia|{dia.isoformat()}"
    if not dry_run and base._existe(clave):
        return {"estado": "ya_elegido", "dia": dia.isoformat()}
    ops = [o for o in cargar_ops(now, ids_evento)]
    calibracion = None
    if artefacto and artefacto.get("aprobado"):           # abstención por categoría, como el lote diario
        from ..eval.parley_calibracion import Calibrador, filtrar_calibradas
        calibracion = Calibrador(artefacto).para_opciones(ops)
        ops = filtrar_calibradas(ops, calibracion)
    for _ in range(2):                                    # una revalidación y, si hace falta, un recálculo
        plan = v2.armar_plan(ops, calibracion=calibracion, ahora=now)
        malos: set[str] = set()
        for t in plan.tickets:
            for o in t.legs:
                inicio = o.evento[2] if len(getattr(o, "evento", ())) > 2 else None
                ev = o.match_id.split(":", 1)[1]
                veredicto, _ = nba.revalidar([o], inicio, leer_contexto(now, ev)) if inicio else ("anular", [])
                if veredicto != "ok":
                    malos.add(base_clave(o))
        if not malos:
            break
        ops = [o for o in ops if base_clave(o) not in malos]
    else:
        return {"estado": "abstencion", "motivo": "las patas no superaron la revalidación", "dia": dia.isoformat()}
    resumen = {"estado": "elegido" if plan.tickets else "abstencion", "dia": dia.isoformat(), "partidos": len(ids_evento),
               "tickets": [{"target": t.target, "estado": t.estado, "patas": len(t.legs)} for t in plan.tickets]}
    if dry_run or not plan.tickets:
        return resumen
    br = base.Barrera(True, [], ("nba",), completa=True)
    lote = base.construir_lote(plan, now, dia, br, None, base._prev(), ambito="nba_dia", evento_id=None)
    if not base._guardar(lote):
        return {"estado": "ya_elegido", "dia": dia.isoformat()}
    return {**resumen, "chain": lote["chain_sha256"][:16]}


def base_clave(o) -> str:
    return str(v2._clave(o))


def revisar(now: datetime, cartelera: Callable[[date], dict], eventos_propline: Callable[[], list[dict]],
            cargar_ops: Callable, leer_contexto: Callable, dry_run: bool = False, artefacto: dict | None = None) -> dict:
    """Una pasada: partidos elegibles, un parley por partido y el de varios partidos si toca."""
    hoy = now.date()
    juegos = [j for d in (hoy - timedelta(days=1), hoy, hoy + timedelta(days=1)) for j in juegos_de_cartelera(cartelera(d))]
    juegos = list({j.id: j for j in juegos}.values())
    mapa = emparejar(juegos, eventos_propline())
    listos = [j for j in elegibles(now, juegos) if j.id in mapa]
    out = {"juegos": len(juegos), "emparejados": len(mapa), "elegibles": [j.id for j in listos], "partidos": [], "multi": None}
    for j in listos:
        out["partidos"].append(nd.ejecutar_partido(
            now, mapa[j.id], j.inicio, j.sellado, lambda n, e: cargar_ops(n, [e]), leer_contexto, dry_run=dry_run))
    if toca_multipartido(now, listos):
        dia = min(j.inicio for j in listos).date()
        out["multi"] = ejecutar_multipartido(now, dia, [mapa[j.id] for j in listos], cargar_ops, leer_contexto, dry_run=dry_run,
                                       artefacto=artefacto)
    return out


def main() -> None:                                     # pragma: no cover - cableado de producción
    import urllib.request as ur
    from ..config import settings
    from ..ingest import propline_shared as ps
    from . import parley_ext as ext
    now = datetime.now(timezone.utc)
    url = os.getenv("NBA_API_URL", "http://nba-api:8000")

    def cartelera(d: date) -> dict:
        return json.load(ur.urlopen(f"{url}/nba/v1/cartelera?fecha={d.isoformat()}", timeout=10))

    datos = ext.cargar(now)
    eventos = datos.get("nba", [])

    def cargar(ahora, ids):
        pe = {"nba": [e for e in datos["nba"] if str(e["id"]) in ids], "nba_props": [e for e in datos["nba_props"] if str(e["id"]) in ids]}
        return ext.candidatos(pe, ahora)

    lesiones, _ = ps.read_injuries(settings.propline_archive, "basketball_nba", now)

    def contexto(ahora, ev):
        ops = cargar(ahora, [ev])
        inicio = next((_t(e["commence_time"]) for e in eventos if str(e["id"]) == ev), None)
        fuera = {str(p.get("player_id")): str(p.get("status") or "out").lower() for p in (lesiones or [])}
        activos = {pid: fuera.get(pid, "active") for o in ops if o.jugador for pid in [o.jugador[0]]} if lesiones is not None else {}
        return nba.Contexto(inicio=inicio, estado_jugadores=activos, cuotas={v2._clave(o): o.price for o in ops})

    ruta = os.getenv("PARLEY_V2_ARTEFACTO")
    artefacto = json.loads(open(ruta, encoding="utf-8").read()) if ruta and os.path.isfile(ruta) else None
    print(json.dumps(revisar(now, cartelera, lambda: eventos, cargar, contexto, artefacto=artefacto), ensure_ascii=False, default=str))


if __name__ == "__main__":                              # pragma: no cover
    main()
