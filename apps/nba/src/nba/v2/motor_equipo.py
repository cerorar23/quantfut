"""Inferencia determinista con posesiones, estado local congelado y prórroga explícita."""
from . import identidad, mercados, nucleo, estado_equipo
from .nucleo import Parametros, Ratings
from .pit import Instantanea
from .salida_equipo import serializar

PARAMETROS = Parametros(eta=0.045, arrastre=0.65, eta_liga=0.01, efecto_b2b=2.90)
SIGMA_MARGEN, SIGMA_TOTAL = 13.81, 18.43
N_SIM = 100_000                                       # error típico de una probabilidad ≤ 0,16 pp (con 20.000 era 0,35 pp); 6 ms por partido
NIVELES = tuple(i / 200 for i in range(1, 200))                     # cuantiles 0,5 % … 99,5 % en pasos de 0,5 % (199 valores)
VERSION_MODELO = 'equipo-2.2;posesiones;regulacion-mas-ot;ratings-local;pmf-exacta'


def version() -> str:
    return VERSION_MODELO + ';equipo=' + estado_equipo.artefacto()[1][:12]


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
    e = estado_equipo.estimar(inst)
    m = nucleo.simular_con_ot(e.mu_local, e.mu_visitante, e.sigma_margen, e.sigma_total,
                             e.posesiones, e.p_ot, n=N_SIM, semilla=inst.partido_id)
    distribucion = serializar(m, *map(float, m.muestras.mean(axis=0)), NIVELES)
    distribucion['tratamiento_ot'] = 'regulacion_mas_prorroga'
    escenarios = {"descanso_dias": {"local": e.descanso_local, "visitante": e.descanso_visitante},
                  "partidos_en_historia": len(inst.historia), 'posesiones_regulacion': e.posesiones, 'p_ot': e.p_ot,
                  'artefacto_equipo': e.version, 'corte_entrenamiento': e.corte_entrenamiento}
    return escenarios, distribucion
