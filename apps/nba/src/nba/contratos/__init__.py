"""Contratos de datos entre los pasos del motor (Pydantic estricto). Sin lógica de modelo: solo formas, unidades e invariantes."""
from .paso_a import EstimacionJugador, MinutosSiJuega, SalidaPasoA
from .paso_b import ParametrosConteo, ParametrosMarcador, SalidaPasoB
from .paso_c import DistribucionEquipo, DistribucionJugador, EntradaMonteCarlo, SalidaMonteCarlo

__all__ = ["DistribucionEquipo", "DistribucionJugador", "EntradaMonteCarlo", "EstimacionJugador", "MinutosSiJuega", "ParametrosConteo",
           "ParametrosMarcador", "SalidaMonteCarlo", "SalidaPasoA", "SalidaPasoB"]
