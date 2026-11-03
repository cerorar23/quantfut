"""Motor v2.0 de equipo sobre una `Instantanea`: reproduce los ratings jugando la historia visible y simula el partido.

Determinista: la semilla es el id del partido; mismos datos → misma distribución (G-fuga). No usa jugadores todavía: ese refinamiento
(plantilla, Sprint 3b) necesita las alineaciones y los minutos esperados dentro de la instantánea.
"""
from . import identidad, mercados, nucleo
from .nucleo import Parametros, Ratings
from .pit import Instantanea

PARAMETROS = Parametros(eta=0.045, arrastre=0.65, eta_liga=0.01, efecto_b2b=2.90)
SIGMA_MARGEN, SIGMA_TOTAL = 13.81, 18.43
N_SIM = 100_000                                       # error típico de una probabilidad ≤ 0,16 pp (con 20.000 era 0,35 pp); 6 ms por partido
NIVELES = tuple(i / 200 for i in range(1, 200))                     # cuantiles 0,5 % … 99,5 % en pasos de 0,5 % (199 valores)
VERSION_MODELO = (f"equipo-2.0;eta={PARAMETROS.eta};arrastre={PARAMETROS.arrastre};liga={PARAMETROS.eta_liga};"
                  f"b2b={PARAMETROS.efecto_b2b};sigma={SIGMA_MARGEN}/{SIGMA_TOTAL};n={N_SIM};margen=proporcional")


def _ratings(inst: Instantanea) -> tuple[Ratings, dict]:
    """Juega la historia visible; si el partido pronosticado abre una temporada nueva, también aplica el arrastre antes de él."""
    r, ultimo, temporada = Ratings(), {}, None
    for fecha, _, local, visit, pl, pv in inst.historia:
        t = identidad.temporada(fecha)
        if t != temporada:
            if temporada is not None:
                nucleo.nueva_temporada(r, PARAMETROS)
            temporada = t
        dl = (fecha - ultimo[local]).days if local in ultimo else 7
        dv = (fecha - ultimo[visit]).days if visit in ultimo else 7
        nucleo.actualizar(r, local, visit, pl, pv, PARAMETROS, nucleo.ajuste_descanso(dl, dv, PARAMETROS))
        ultimo[local] = ultimo[visit] = fecha
    if temporada is not None and identidad.temporada(inst.fecha) != temporada:
        nucleo.nueva_temporada(r, PARAMETROS)
    return r, ultimo


def pronosticar(inst: Instantanea) -> tuple[dict, dict]:
    """(escenarios, distribucion) listos para sellar; con la historia vacía se niega en lugar de inventar ratings."""
    if not inst.historia:
        raise ValueError("sin historia visible: no se pronostica")
    r, ultimo = _ratings(inst)
    dl = (inst.fecha - ultimo[inst.local]).days if inst.local in ultimo else 7
    dv = (inst.fecha - ultimo[inst.visitante]).days if inst.visitante in ultimo else 7
    mu_l, mu_v = r.esperado(inst.local, inst.visitante, nucleo.ajuste_descanso(dl, dv, PARAMETROS))
    m = nucleo.simular(mu_l, mu_v, SIGMA_MARGEN, SIGMA_TOTAL, n=N_SIM, semilla=inst.partido_id)
    margen, total = m.margen(), m.total()
    distribucion = {"p_local": round(mercados.ganador(m), 6), "mu": [round(mu_l, 4), round(mu_v, 4)],
                    "paso_cuantil": 0.005,
                    "margen": [float(margen.cuantil(q)) for q in NIVELES],
                    "total": [float(total.cuantil(q)) for q in NIVELES],
                    "puntos_local": [float(m.puntos("local").cuantil(q)) for q in NIVELES],
                    "puntos_visitante": [float(m.puntos("visit").cuantil(q)) for q in NIVELES]}
    escenarios = {"descanso_dias": {"local": dl, "visitante": dv}, "partidos_en_historia": len(inst.historia)}
    return escenarios, distribucion
