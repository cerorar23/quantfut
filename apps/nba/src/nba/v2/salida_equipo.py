"""Una única ley discreta por mercado conserva masas, cuantiles y semántica del partido completo."""
import numpy as np
from . import mercados


def serializar(marcador, mu_local: float, mu_visitante: float, niveles) -> dict:
    leyes = {"margen": marcador.margen(), "total": marcador.total(),
             "puntos_local": marcador.puntos("local"), "puntos_visitante": marcador.puntos("visit")}
    resultado = {"p_local": round(mercados.ganador(marcador), 6), "mu": [round(mu_local, 4), round(mu_visitante, 4)],
                 "paso_cuantil": .005, "masas": {}, "objetivo": "partido_completo_con_prorroga",
                 "tratamiento_ot": "final_historico_implicito"}
    for nombre, ley in leyes.items():
        soporte, indices = np.unique(ley.valores, return_index=True)
        pmf = np.add.reduceat(ley.pesos, indices)
        pmf /= pmf.sum()
        # Una sola CDF autoritativa: la acumulación de 100.000 pesos repetidos puede
        # cruzar un nivel exacto de cuantil de forma distinta de la PMF agregada.
        idx = np.searchsorted(np.cumsum(pmf), np.maximum(np.asarray(niveles) - 1e-12, 0))
        resultado[nombre] = list(map(float, soporte[np.minimum(idx, len(soporte) - 1)]))
        resultado["masas"][nombre] = {"soporte": list(map(int, soporte)), "pmf": list(map(float, pmf))}
    return resultado
