"""Candidatos de tenis y NBA para el parley v2 (ganador, hándicap y totales del partido).

Sigue el mismo criterio que la escalera para NBA y tenis (decisión del usuario,
2026-10-28) y lee el archivo PropLine compartido sin peticiones nuevas:

* Probabilidad: consenso de las casas que cotizan ese contrato (mercado y línea)
  completo, cada una sin margen (``referencia.probabilidades``). Pinnacle NO es
  obligatorio (decisión del usuario, 2026-11-06): si cotiza, conserva el peso que
  ya tenía; si no, pesan igual. Hacen falta al menos ``referencia.MIN_CASAS``
  casas; con una sola, el contrato no entra.
* Cuota: una oferta por casa de la lista (``settings.soft_books``) en el mismo
  contrato exacto; ``parley_v2.consolidar`` elige la mejor con su guarda contra
  cuotas atípicas. Se exige que la cuota sea reciente (``MAX_EDAD_PRECIO``).
* Solo líneas .5 en hándicap y totales: una línea entera puede devolverse y la
  medición (docs/parley_topes_medicion_20261106.md) no las incluye.
* Ventana: el evento empieza al menos ``MIN_ANTELACION`` después de la decisión
  y antes de ``HORIZONTE``.

Props de jugador de NBA (puntos, rebotes, asistencias y triples, Over/Under): salen
del mismo archivo (``props_feed`` sobre ``propline_shared.quotes``), con los mismos
filtros que ``two_way_feed`` (sin marcas de restricción, suspensión, DFS ni en juego), ambos
lados en la misma casa y línea .5. Un prop cuyo jugador no juega se devuelve: la pata se
anula y el ticket cambia de cuota, así que antes de publicar hay que confirmar
disponibilidad (lesiones, titulares, minutos); mientras no exista esa confirmación el
ticket sigue en ``solo_referencia``. Solo cuenta una pata por partido: un parley de varias
patas del mismo partido es same-game.

Mercados de tenis → familia del selector: ganador (``h2h``), hándicap de juegos
(``handicap_games``) y juegos totales (``total_games``); en NBA ``h2h``,
``spreads`` y ``totals``. Los demás mercados de tenis (sets, ganador del set,
tie-break) no tienen cuota en el archivo: no entran.

El módulo es puro: recibe los eventos ya leídos (``propline_shared.read_two_way``)
y no toca la base de datos ni el sellado. Guardar patas de tenis o NBA en
``parley_patas`` requiere una migración y es parte del lote propio del parley
(harness/tareas.md, fase 3).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..config import settings
from . import parley_v2 as v2
from . import picks as pk
from . import referencia as rf
from .alta_prob import Candidato
from .escalera import Opcion

# Deporte del parley → deporte del archivo PropLine.
DEPORTES = {"tenis": "tennis", "nba": "basketball_nba"}
MIN_ANTELACION = timedelta(minutes=30)
HORIZONTE = timedelta(hours=24)
MAX_EDAD_PRECIO = timedelta(hours=6)

_MERCADO = {
    "tenis": {"h2h": "h2h", "spreads": "handicap_games", "totals": "total_games"},
    "nba": {"h2h": "h2h", "spreads": "spreads", "totals": "totals"},
}
# Props de jugador medidos (docs/parley_topes_medicion_20261106.md): 2 temporadas, 7-8 casas.
PROPS = ("player_points", "player_rebounds", "player_assists", "player_threes")


@dataclass(frozen=True)
class OpcionExterna(Opcion):
    """Pata de otro deporte: guarda el evento para mostrarla y liquidarla después."""
    deporte: str = ""
    evento: tuple = ()          # (id, sport_key, inicio, local, visitante)
    n_casas_ref: int = 0        # casas que sustentan la probabilidad
    referencia: str = ""        # "preferida" (Pinnacle con peso) o "consenso"
    jugador: tuple = ()         # (player_id, nombre) en los props de jugador


def _tiempo(valor) -> datetime:
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(valor).replace("Z", "+00:00")).astimezone(timezone.utc)


def _media_linea(x) -> bool:
    return x is not None and math.isfinite(float(x)) and math.isclose(abs(float(x)) % 1, 0.5)


def _contratos(book: dict, local: str, visitante: str) -> dict[tuple, dict]:
    """{contrato: {lado: salida}} de una casa.

    Contrato = (mercado, jugador, línea): ganador (``h2h``, None, None), total (``totals``, None, línea),
    hándicap (``spreads``, None, línea del local) y prop (``player_*``, player_id, línea).
    """
    out: dict[tuple, dict] = {}
    for m in book.get("markets", []):
        key, salidas = m.get("key"), m.get("outcomes", [])
        lados: dict[str, dict] = {}
        if key == "totals" or key in PROPS:
            for o in salidas:
                if o.get("name") in ("Over", "Under"):
                    lados["over" if o["name"] == "Over" else "under"] = o
            ident = lados.get("over", {}).get("player_id") if key in PROPS else None
            if (len(lados) == 2 and lados["over"].get("point") == lados["under"].get("point")
                    and _media_linea(lados["over"].get("point"))
                    and (key not in PROPS or (ident is not None and ident == lados["under"].get("player_id")))):
                out[(key, ident, float(lados["over"]["point"]))] = lados
        elif key in ("h2h", "spreads"):
            for o in salidas:
                if o.get("name") == local:
                    lados["home"] = o
                elif o.get("name") == visitante:
                    lados["away"] = o
            if len(lados) != 2:
                continue
            if key == "h2h":
                out[("h2h", None, None)] = lados
            else:
                ph, pa = lados["home"].get("point"), lados["away"].get("point")
                if _media_linea(ph) and pa is not None and math.isclose(float(ph), -float(pa)):
                    out[("spreads", None, float(ph))] = lados
    return out


def props_feed(events: list[dict], received_at) -> list[dict]:
    """Props de jugador (``PROPS``) de NBA con la forma de The Odds API que lee ``opciones``.

    Mismo criterio que ``propline_shared.two_way_feed``: se descarta toda cotización con marca
    (restringida, suspendida, DFS, exchange, en juego, precio o línea inválidos). Cada (casa,
    mercado, jugador, línea) forma un mercado con sus dos lados; con uno solo no se puede quitar el margen.
    """
    from ..ingest import propline_shared as ps
    agrupado: dict[tuple, dict] = {}
    for q in ps.quotes(events, received_at):
        if (q["flags"] or q["market"] not in PROPS or q["player_id"] is None
                or q["period"] is not None or q["name"] not in ("Over", "Under")
                or q["point"] is None or q["price_decimal"] is None):
            continue
        k = (q["event_id"], q["bookmaker"], q["market"], q["player_id"], float(q["point"]))
        salida = dict(name=q["name"], price=q["price_decimal"], point=q["point"], player_id=q["player_id"],
                      description=q["description"])
        if q["book_updated_at"]:
            salida["last_update"] = q["book_updated_at"]
        agrupado.setdefault(k, {"key": q["market"], "outcomes": []})["outcomes"].append(salida)
    por_evento: dict[str, dict[str, list]] = {}
    for (eid, casa, _, _, _), mercado in agrupado.items():
        if len(mercado["outcomes"]) == 2 and {o["name"] for o in mercado["outcomes"]} == {"Over", "Under"}:
            por_evento.setdefault(eid, {}).setdefault(casa, []).append(mercado)
    return [dict(e, bookmakers=[dict(key=c, markets=ms) for c, ms in por_evento[str(e["id"])].items()],
                 _received_at=received_at)
            for e in events if str(e["id"]) in por_evento]


def _fresca(salida: dict, recibida: datetime, now: datetime) -> bool:
    cambio = salida.get("last_update")
    cuando = _tiempo(cambio) if cambio else recibida
    return now - cuando <= MAX_EDAD_PRECIO


def opciones(eventos: dict[str, list[dict]], now: datetime) -> list[Opcion]:
    """Una oferta por (contrato, lado, casa) con la probabilidad de consenso; sin consolidar.

    ``eventos``: {"tenis": [...], "nba": [...], "nba_props": [...]} con la forma de The Odds API que
    entrega ``propline_shared.read_two_way`` (cada evento lleva ``_received_at``).
    """
    sharp = pk.canonical_book(settings.sharp_book)
    blandas = {pk.canonical_book(b) for b in settings.soft_books}
    fin = now + HORIZONTE
    out: list[Opcion] = []
    for clave, lista in eventos.items():
        deporte = clave.split("_")[0]                  # "nba_props" → "nba"
        nombres = _MERCADO[deporte]
        for e in lista:
            if not e.get("_received_at"):
                continue                      # sin recepción real no hay procedencia
            recibida = _tiempo(e["_received_at"])
            if recibida > now:
                continue
            inicio = _tiempo(e["commence_time"])
            if not now + MIN_ANTELACION <= inicio < fin:
                continue
            local, visitante = e["home_team"], e["away_team"]
            casas = {pk.canonical_book(b["key"]): _contratos(b, local, visitante) for b in e["bookmakers"]}
            evento = (str(e["id"]), e.get("sport_key") or DEPORTES[deporte], inicio, local, visitante)
            for contrato in sorted({c for cs in casas.values() for c in cs}, key=str):
                a, b = ("over", "under") if contrato[0] == "totals" or contrato[0] in PROPS else ("home", "away")
                cotizaciones = {casa: {a: cs[contrato][a].get("price"), b: cs[contrato][b].get("price")}
                                for casa, cs in casas.items() if contrato in cs}
                ref = rf.probabilidades(cotizaciones, (a, b), preferida=sharp)
                if ref is None:
                    continue
                probs, meta = ref
                for lado in (a, b):
                    for casa, contratos in casas.items():
                        if casa not in blandas or contrato not in contratos:
                            continue
                        salida = contratos[contrato][lado]
                        try:
                            precio = float(salida["price"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        if not (precio > 1 and math.isfinite(precio)) or not _fresca(salida, recibida, now):
                            continue
                        mercado, linea = nombres.get(contrato[0], contrato[0]), contrato[2]
                        if contrato[0] == "spreads":
                            linea = float(salida["point"])
                        jugador = ((str(contrato[1]), salida.get("description") or "")
                                   if contrato[1] is not None else ())
                        out.append(OpcionExterna(
                            match_id=f"{deporte}:{e['id']}", cand=Candidato(mercado, lado, linea, float(probs[lado])),
                            price=precio, book=casa, odds_source="propline", odds_as_of=recibida,
                            deporte=deporte, evento=evento, n_casas_ref=meta["casas"],
                            referencia=meta["referencia"], jugador=jugador))
    return out


def candidatos(eventos: dict[str, list[dict]], now: datetime) -> list[Opcion]:
    """Ofertas consolidadas: la mejor cuota por contrato exacto entre casas, con la guarda del selector."""
    return v2.consolidar(opciones(eventos, now))


def cargar(now: datetime, root=None) -> dict[str, list[dict]]:
    """Lee el archivo PropLine sin red: {"tenis", "nba", "nba_props"}. Solo en una base que traiga `read_two_way`."""
    from ..ingest import propline_shared as ps
    if not hasattr(ps, "read_two_way"):
        raise RuntimeError("propline_shared de esta base no trae read_two_way (NBA y tenis)")
    root = root or settings.propline_archive
    out: dict[str, list[dict]] = {}
    for deporte, sport in DEPORTES.items():
        eventos, recibo = ps.read_two_way(root, sport, now)
        out[deporte] = eventos or []
    crudos, recibo = ps.newest(root, f"/v1/sports/{DEPORTES['nba']}/odds", now)
    out["nba_props"] = props_feed(crudos or [], recibo["received_at"]) if recibo else []
    return out


def ensayo(now: datetime | None = None, root=None, calibracion: dict | None = None) -> dict:
    """Plan de los cuatro targets solo con tenis y NBA, sin guardar nada (ensayo de lectura)."""
    now = now or datetime.now(timezone.utc)
    ops = candidatos(cargar(now, root), now)
    plan = v2.armar_plan(ops, calibracion=calibracion, ahora=now)
    return {"candidatas": len(ops), "partidos": len({o.match_id for o in ops}),
            "por_deporte": {d: len({o.match_id for o in ops if o.match_id.startswith(d + ":")}) for d in DEPORTES},
            "props": sum(1 for o in ops if o.cand.market in PROPS),
            "tickets": [v2.resumen(t) for t in plan.tickets],
            "abstenciones": [{"target": a.target, "motivo": a.motivo} for a in plan.abstenciones],
            "diagnostico": plan.diagnostico}


if __name__ == "__main__":
    import json
    print(json.dumps(ensayo(), ensure_ascii=False, indent=2, default=str))
