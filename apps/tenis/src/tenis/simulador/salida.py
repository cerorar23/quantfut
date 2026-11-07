"""Paso de la conjunta del simulador al contrato `contratos.salida.DistribucionPartido` (física del marcador y
mercados recalculados por el propio contrato). Lo que el contrato no admite se rechaza aquí con un motivo claro:
súper tiebreak en lugar del 3.er set (plan F.3: no soportado para sellar) y set decisivo de ventaja (el contrato
topa el total de juegos en 39/65, plan G.6, incompatible con ese formato)."""
from tenis.contratos.salida import TOLERANCIA_SUMA, DistribucionPartido

from .resultado import DistPartido


def a_contrato(dist: DistPartido, sets_mas_de=(), juegos_mas_de=(), handicap_sets=()) -> DistribucionPartido:
    if dist.formato.decisivo == "super_tiebreak_10":
        raise ValueError("el contrato no admite el súper tiebreak en lugar del set decisivo (plan F.3): no se sella")
    if dist.formato.decisivo == "ventaja":
        raise ValueError("el contrato no admite hoy el set decisivo de ventaja: `validar_totales` limita el total a "
                         "39 (mejor de 3) y 65 (mejor de 5) juegos, y un set de ventaja lo supera (p. ej. 6-7 7-6 "
                         "14-12); además SetMarcador limita el set a 50 juegos. Pendiente de decidir en el contrato")
    if dist.masa_cola > TOLERANCIA_SUMA / 2:
        raise ValueError(f"masa sin marcador representable {dist.masa_cola:.3e} > tolerancia del contrato")
    entradas = [{"sets": [{"juegos_a": a, "juegos_b": b, "tiebreak": t} for a, b, t in m], "probabilidad": p}
                for m, p in dist.marcadores().items() if p > 0.0]
    filas = ~dist.cola & (dist.prob > 0)

    def p(mask) -> float:
        return float(dist.prob[filas & mask].sum())

    ns, tot, dif = dist.sets_a + dist.sets_b, dist.juegos, dist.sets_a - dist.sets_b
    mercados = {
        "gana_a": p(dist.sets_a > dist.sets_b),
        "primer_set_a": p(dist.primer_set_a),
        "sets_mas_de": {str(x): p(ns > x) for x in sets_mas_de},
        "juegos_mas_de": {str(x): p(tot > x) for x in juegos_mas_de},
        "handicap_sets": {str(x): p(dif + x > 0) for x in handicap_sets},
    }
    return DistribucionPartido.model_validate({"mejor_de": dist.formato.mejor_de,
                                               "regla_decisivo": dist.formato.decisivo,
                                               "entradas": entradas, "mercados": mercados})
