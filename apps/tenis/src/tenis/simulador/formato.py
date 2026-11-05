"""Formato del partido (plan F.3). Va por edición; un formato desconocido es un error explícito, nunca un valor por omisión.

Sets no decisivos: siempre tiebreak a 7 en 6-6. Set decisivo (3.º en mejor de 3, 5.º en mejor de 5):
- 'tiebreak_7'          tiebreak a 7 en 6-6 (gira regular en mejor de 3; US Open a 5 sets hasta 2021)
- 'tiebreak_10'         tiebreak a 10 en 6-6 (Grand Slam desde 2022, T32)
- 'ventaja'             sin tiebreak, gana por dos juegos (formatos históricos, Copa Davis)
- 'super_tiebreak_10'   el 3.er set se sustituye por un tiebreak a 10 (solo mejor de 3; el contrato y el plan F.3
                        aún no lo admiten para sellar: el simulador lo calcula pero `salida.a_contrato` lo rechaza)
"""
from dataclasses import dataclass

DECISIVOS = ("tiebreak_7", "tiebreak_10", "ventaja", "super_tiebreak_10")


@dataclass(frozen=True)
class Formato:
    mejor_de: int
    decisivo: str

    def __post_init__(self):
        if isinstance(self.mejor_de, bool) or self.mejor_de not in (3, 5):
            raise ValueError(f"mejor de {self.mejor_de!r} no soportado (solo 3 o 5 sets; un set suelto, sets a 4, "
                             "Fast4 o NextGen no se simulan)")
        if self.decisivo not in DECISIVOS:
            raise ValueError(f"regla del set decisivo «{self.decisivo}» desconocida: {DECISIVOS}")
        if self.decisivo == "super_tiebreak_10" and self.mejor_de != 3:
            raise ValueError("el súper tiebreak en lugar del set decisivo solo existe en mejor de 3")

    @property
    def sets_para_ganar(self) -> int:
        return (self.mejor_de + 1) // 2


def validar_formato(formato) -> Formato:
    if not isinstance(formato, Formato):
        raise TypeError("formato debe ser un tenis.simulador.Formato explícito (sin valor por omisión)")
    return formato
