"""
Quién ve cada parley (decisión del usuario, 2026-10-12): UNO gratis al día, el de MENOR
escalón (normalmente el 1, el más probable), y el resto VIP. Mismo criterio que la Escalera
(un solo pendiente gratuito). Con VIP se ve todo. Si el día trae un único parley, no hay
ninguno gratis (decisión del usuario, 2026-10-13): con uno solo no habría "resto" que vender.

Un parley YA LIQUIDADO se ve siempre, con sus patas: es la prueba de que se eligió antes de
los partidos y el historial verificable, como en alta probabilidad y Escalera.

Un parley bloqueado sale SOLO con su escalón y el rango de cuota de ese escalón (público en
las reglas): sin patas, cuota ni probabilidad exactas, ni número de patas.
"""
from __future__ import annotations


def aplicar_acceso(informe: dict, plus: bool) -> dict:
    rangos = {int(e["escalon"]): (e["cuota_min"], e["cuota_max"])
              for e in (informe.get("reglas") or {}).get("escalones", [])}
    dias = []
    for dia in informe.get("dias", []):
        tickets = dia.get("tickets", [])
        gratis = min((int(t["escalon"]) for t in tickets), default=None) if len(tickets) > 1 else None
        salida = []
        for t in tickets:
            escalon = int(t["escalon"])
            if plus or escalon == gratis or t.get("outcome") is not None:
                salida.append({**t, "locked": False, "gratis": escalon == gratis})
            else:
                lo, hi = rangos.get(escalon, (None, None))
                salida.append({"escalon": escalon, "locked": True,
                               "cuota_min": lo, "cuota_max": hi})
        dias.append({**dia, "tickets": salida})
    return {**informe, "dias": dias,
            "acceso": {"plus": bool(plus),
                       "regla": "uno gratis al día (el de menor escalón); el resto, VIP"}}
