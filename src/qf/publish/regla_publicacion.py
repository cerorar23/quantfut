"""Regla de publicación de NBA y tenis: qué pronósticos entran en Mercados y en Alta probabilidad.

La decide el SERVIDOR (no la app): así se cambia un umbral sin publicar otra versión en Play. Solo elige entre
pronósticos ya sellados; no calcula probabilidades ni toca el sello (orden predecir → sellar → publicar intacto).

Medida del 5-nov-2026 (docs/regla_publicacion_20261105.md): con probabilidad ≥ 78 % y cuota de referencia ≥ 1,20
acierta ~81 % (límite inferior del IC95 ~77 %); sin exigir cuota, ~92 %, pero eso son líneas de cuota ~1,05 sin valor.
Las props de jugador de NBA se ocultan: el modelo dice ~67 % y acierta 49–61 %.

Umbrales por entorno (cambian al reiniciar el servicio): QF_PUB_PROB_MIN, QF_PUB_PROB_MAX, QF_PUB_PRICE_MIN,
QF_PUB_EXCLUDE (familias separadas por coma), QF_PUB_PER_FAMILY.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

PROPS_NBA = ("player_points", "player_rebounds", "player_assists", "player_threes")


@dataclass(frozen=True)
class Regla:
    prob_min: float = .78
    prob_max: float = .95
    precio_min: float = 1.20
    excluidas: frozenset = frozenset(PROPS_NBA)
    por_familia: int = 1


def _numero(nombre: str, defecto: float) -> float:
    try:
        v = float(os.environ.get(nombre, ""))
    except ValueError:
        return defecto
    return v if math.isfinite(v) else defecto


def regla_desde_entorno() -> Regla:
    base = Regla()
    excl = os.environ.get("QF_PUB_EXCLUDE")
    return Regla(
        prob_min=_numero("QF_PUB_PROB_MIN", base.prob_min),
        prob_max=_numero("QF_PUB_PROB_MAX", base.prob_max),
        precio_min=_numero("QF_PUB_PRICE_MIN", base.precio_min),
        excluidas=base.excluidas if excl is None else frozenset(x.strip() for x in excl.split(",") if x.strip()),
        por_familia=max(1, int(_numero("QF_PUB_PER_FAMILY", base.por_familia))),
    )


def _finito(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def elegir(candidatos, regla: Regla) -> set[str]:
    """Ids publicables de UN partido. Cada candidato: dict(id, familia, prob, precio, linea_key).

    1. Fuera las familias excluidas, lo que no tiene cuota válida ≥ `precio_min` y lo que cae fuera de la banda.
    2. Un solo lado por línea (`linea_key` junta los dos lados): el de mayor probabilidad.
    3. Por familia, los `por_familia` mejores (probabilidad y luego cuota; empate por id: reproducible).
    """
    por_linea: dict[tuple, dict] = {}
    for c in candidatos:
        prob, precio = _finito(c.get("prob")), _finito(c.get("precio"))
        if c["familia"] in regla.excluidas or prob is None or precio is None:
            continue
        if precio < regla.precio_min or not regla.prob_min <= prob <= regla.prob_max:
            continue
        clave = (c["familia"], c.get("linea_key"))
        previo = por_linea.get(clave)
        if previo is None or (prob, str(c["id"])) > (previo["prob"], str(previo["id"])):
            por_linea[clave] = {**c, "prob": prob, "precio": precio}
    por_familia: dict[str, list[dict]] = {}
    for c in por_linea.values():
        por_familia.setdefault(c["familia"], []).append(c)
    out: set[str] = set()
    for lista in por_familia.values():
        lista.sort(key=lambda c: (-c["prob"], -c["precio"], str(c["id"])))
        out.update(str(c["id"]) for c in lista[: regla.por_familia])
    return out


def _precio_publicable(q) -> float | None:
    """Una cuota del tercer nivel del respaldo (SportsAPIPro) es de DESPUÉS del sello: se muestra, pero no decide
    qué se publica (no se puede probar que existiera cuando se selló el pronóstico)."""
    if not isinstance(q, dict) or q.get("post_sello"):
        return None
    return q.get("price")


def publicables_tenis(feed: dict, eventos_cuota: dict, regla: Regla | None = None) -> dict[str, list[str]]:
    """{event_id: [market_id]} publicables del feed público de tenis. La cuota sale del overlay de PropLine
    (`eventos_cuota`: event_id -> market_id -> {price, ...}); un mercado sin cuota no es publicable."""
    regla = regla or regla_desde_entorno()
    out: dict[str, list[str]] = {}
    for event in feed.get("events", []) if isinstance(feed, dict) else []:
        try:
            eid = str(event["id"])
            cuotas = eventos_cuota.get(eid) or {}
            candidatos = [
                {"id": m["id"], "familia": str(m["id"]).split("-")[0], "prob": m.get("probability"),
                 "precio": _precio_publicable(cuotas.get(m["id"])), "linea_key": m["id"]}
                for m in event["markets"]]
        except (KeyError, TypeError, AttributeError):
            continue
        elegidos = elegir(candidatos, regla)
        if elegidos:
            out[eid] = sorted(elegidos)
    return out
