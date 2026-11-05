"""Física del marcador (plan G.6): qué sets y qué partidos existen. Sin efectos, sin modelo.

Regla del set decisivo = último set posible del partido (3.º en mejor de 3, 5.º en mejor de 5).
Los sets anteriores son siempre con tiebreak a 7 en 6-6.
"""
from typing import Literal

from pydantic import Field, model_validator

from .base import Contrato

Regla = Literal["tiebreak_7", "tiebreak_10", "ventaja"]
MejorDe = Literal[3, 5]


def validar_regla(mejor_de: int, regla: str) -> None:
    permitidas = {3: ("tiebreak_7", "tiebreak_10", "ventaja"), 5: ("tiebreak_10", "ventaja")}
    if regla not in permitidas[mejor_de]:
        raise ValueError(f"regla decisiva «{regla}» no existe en mejor de {mejor_de}")


class SetMarcador(Contrato):
    juegos_a: int = Field(ge=0, le=50)
    juegos_b: int = Field(ge=0, le=50)
    tiebreak: bool = False


def set_valido(s: SetMarcador, regla: str | None) -> bool:
    """regla None = set no decisivo (siempre tiebreak a 7 en 6-6)."""
    hi, lo = max(s.juegos_a, s.juegos_b), min(s.juegos_a, s.juegos_b)
    if hi == lo:
        return False
    if s.tiebreak:
        return (hi, lo) == (7, 6) and regla != "ventaja"
    if hi == 6:
        return lo <= 4
    if hi == 7:
        return lo == 5
    return regla == "ventaja" and hi >= 8 and hi - lo == 2


def sets_necesarios(mejor_de: int) -> int:
    return (mejor_de + 1) // 2


def indice_decisivo(mejor_de: int) -> int:
    return 2 * sets_necesarios(mejor_de) - 2


def validar_totales(mejor_de: int, n_sets: int, total_juegos: int) -> None:
    if mejor_de == 3:
        ok = 12 <= total_juegos <= 39 and (n_sets < 3 or total_juegos >= 18)
    else:
        ok = 18 <= total_juegos <= 65 and (n_sets != 4 or total_juegos >= 24) and (n_sets != 5 or total_juegos >= 30)
    if not ok:
        raise ValueError(f"total de juegos {total_juegos} imposible con {n_sets} sets en mejor de {mejor_de}")


def validar_marcador(sets: list[SetMarcador], mejor_de: int, regla: str) -> None:
    need = sets_necesarios(mejor_de)
    decisivo = indice_decisivo(mejor_de)
    ganados = [0, 0]
    for i, s in enumerate(sets):
        if not set_valido(s, regla if i == decisivo else None):
            raise ValueError(f"set {i + 1} «{s.juegos_a}-{s.juegos_b}» no existe en este formato")
        ganados[0 if s.juegos_a > s.juegos_b else 1] += 1
        if max(ganados) == need and i != len(sets) - 1:
            raise ValueError("hay sets después de terminar el partido")
    if max(ganados) != need:
        raise ValueError("el partido no termina: falta un jugador por llegar a los sets necesarios")
    validar_totales(mejor_de, len(sets), sum(s.juegos_a + s.juegos_b for s in sets))


class FormatoPartido(Contrato):
    """Mezcla de campos comunes para contratos que describen un partido."""
    mejor_de: MejorDe
    regla_decisivo: Regla

    @model_validator(mode="after")
    def _regla_del_formato(self):
        validar_regla(self.mejor_de, self.regla_decisivo)
        return self
