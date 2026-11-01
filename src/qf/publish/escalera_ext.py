"""
Escalones de NBA y tenis para el reto escalera (decisión del usuario,
2026-10-28: «conéctalos»), leídos del archivo PropLine compartido, sin
peticiones nuevas (CLAUDE.md: PropLine es la fuente fija de cuotas y el
recolector horario sirve a todos).

- Mercado: ganador del partido (h2h), lo único medido en
  `eval/escalera_multideporte.py`.
- Probabilidad: Pinnacle sin margen (`settings.sharp_book`, Shin a dos
  lados). Sin Pinnacle en la observación, el partido no entra: no se cambia de
  referencia en silencio.
- Cuota: la mejor de las casas de la lista (`settings.soft_books`) en la misma
  observación, con menos de `escalera.MAX_EDAD_PRECIO` si la casa dice cuándo
  la cambió.
- Liquidación: la calificación de PropLine para la casa del escalón (cada casa
  aplica su regla de retiradas en tenis); sin ella, la de Pinnacle; si pasan
  `MARGEN_SIN_RESULTADO` sin calificar, nulo.

Solo lee el archivo; las filas inmutables las escribe `escalera_datos`.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from ..config import settings
from ..ingest import propline_shared as ps
from ..model.devig import two_way_devig
from . import escalera as es
from . import picks as pk
from . import ventana
from .alta_prob import Candidato

# Deporte de la escalera → deporte del archivo PropLine.
DEPORTES = {"nba": "basketball_nba", "tenis": "tennis"}
MARGEN_SIN_RESULTADO = timedelta(hours=72)
RESOLUCION = {"won": "win", "win": "win", "lost": "loss", "loss": "loss",
              "push": "push", "void": "void", "cancelled": "void", "refund": "void"}


def es_externo(match_id: str | None) -> bool:
    return bool(match_id) and match_id.split(":", 1)[0] in DEPORTES


def _h2h(book: dict, local: str, visitante: str) -> dict[str, dict] | None:
    """{'home': salida, 'away': salida} del ganador de una casa, o None si no trae los dos."""
    for m in book.get("markets", []):
        if m.get("key") != "h2h":
            continue
        lados = {}
        for o in m.get("outcomes", []):
            lado = "home" if o.get("name") == local else "away" if o.get("name") == visitante else None
            if lado:
                lados[lado] = o
        if len(lados) == 2:
            return lados
    return None


def _fresca(o: dict, recibida: datetime, now: datetime) -> bool:
    cambio = o.get("last_update")
    cuando = ps.parse_time(cambio) if cambio else recibida
    return now - cuando <= es.MAX_EDAD_PRECIO


def opciones(now: datetime, root=None) -> list[es.Opcion]:
    """Candidatos de NBA y tenis en el horizonte de la escalera, ya recibidos en `now`."""
    root = root or settings.propline_archive
    sharp = pk.canonical_book(settings.sharp_book)
    blandas = {pk.canonical_book(b) for b in settings.soft_books}
    fin = ventana.fin_ventana(now, es.HORIZONTE)
    out: list[es.Opcion] = []
    for deporte, sport in DEPORTES.items():
        eventos, recibo = ps.read_two_way(root, sport, now)
        if recibo is None:
            continue
        recibida = ps.parse_time(recibo["received_at"])
        for e in eventos:
            inicio = ps.parse_time(e["commence_time"])
            if not now + pk.MIN_LEAD <= inicio <= fin:
                continue
            local, visitante = e["home_team"], e["away_team"]
            casas = {pk.canonical_book(b["key"]): _h2h(b, local, visitante) for b in e["bookmakers"]}
            ref = casas.get(sharp)
            if ref is None:
                continue
            p_local, p_visit = two_way_devig(float(ref["home"]["price"]), float(ref["away"]["price"]),
                                             settings.devig_method)
            evento = (str(e["id"]), e.get("sport_key") or sport, inicio, local, visitante)
            for lado, prob in (("home", p_local), ("away", p_visit)):
                precios = [(float(h[lado]["price"]), casa) for casa, h in casas.items()
                           if h and casa in blandas and _fresca(h[lado], recibida, now)]
                if not precios:
                    continue
                precio, casa = max(precios)
                out.append(es.Opcion(f"{deporte}:{e['id']}", Candidato("h2h", lado, None, float(prob)),
                                     precio, casa, "propline", recibida, deporte, evento))
    return out


def resultado(paso: dict, now: datetime, root=None) -> tuple | None:
    """(outcome, None, None, None) del escalón externo, o None si aún no se puede liquidar."""
    root = root or settings.propline_archive
    sport = DEPORTES[paso["deporte"]]
    nombre = paso["evento_local"] if paso["selection"] == "home" else paso["evento_visitante"]
    filas, recibo = ps.read_results(root, sport, paso["evento_id"], now)
    por_casa = {}
    for f in filas or []:
        if (f["market"] == "h2h" and f["period"] is None and f["team"] is None
                and f["name"] == nombre and f["resolution"] is not None):
            por_casa.setdefault(pk.canonical_book(f["bookmaker"]), RESOLUCION.get(str(f["resolution"]).lower()))
    for casa in (pk.canonical_book(paso["book"]), pk.canonical_book(settings.sharp_book)):
        if por_casa.get(casa):
            return (por_casa[casa], None, None, None)
    if paso["evento_inicio"] < now - MARGEN_SIN_RESULTADO:
        return ("void", None, None, None)
    return None
