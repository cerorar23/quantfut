"""Copia de `qf.publish.regla_publicacion` (el paquete NBA es aislado y no importa `qf`): mantener ambas iguales.

Regla de publicación de NBA y tenis: qué pronósticos entran en Mercados y en Alta probabilidad.

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


def publicar(salida: dict, regla: Regla | None = None) -> None:
    """Marca cada mercado de `/nba/v1/partido/{id}/mercados` con `publicable` (True/False). No quita ninguno: el detalle
    del partido sigue mostrando todo; Mercados y Alta probabilidad de la app solo cuentan los publicables."""
    regla = regla or regla_desde_entorno()
    candidatos = [
        {"id": m["id"], "familia": m["market"], "prob": m["probability"], "precio": m.get("price"),
         "linea_key": None if m["market"] == "winner" else (m.get("player_id") or m.get("team"),
                                                            abs(m["line"]) if m["market"] == "handicap" else m["line"])}
        for m in salida["markets"] if m.get("line") is not None or m["market"] == "winner"]
    elegidos = elegir(candidatos, regla)
    for m in salida["markets"]:
        m["publicable"] = m["id"] in elegidos
