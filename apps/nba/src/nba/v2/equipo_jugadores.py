"""Pronóstico de equipo versión 2.1: el MARGEN es la media del rating de equipo y del modelo de jugadores (Sprint 3b).

El total se queda con el núcleo de equipo: en la validación (2023-25) la mezcla no lo mejora (18,33 frente a 18,28) y en la prueba de
2025-26 sí (19,03 frente a 19,12), así que solo se usa lo que mejora en los dos periodos; el margen sí mejora en ambos
(14,19 → 14,05 y 14,49 → 14,32). Sin plantilla suficiente en alguno de los equipos vuelve al núcleo 2.0 y lo dice en la versión.
"""
from . import mercados, minutos, motor_equipo, nucleo
from . import plantilla as modelo
from .motor_equipo import NIVELES, N_SIM, PARAMETROS, SIGMA_TOTAL, VERSION_MODELO
from .pit import Instantanea

MIN_CANDIDATOS_POR_EQUIPO = 8


def version(imp) -> str:
    return (f"equipo-2.1;eta={PARAMETROS.eta};arrastre={PARAMETROS.arrastre};liga={PARAMETROS.eta_liga};b2b={PARAMETROS.efecto_b2b};"
            f"sigma={imp.sigma_margen}/{SIGMA_TOTAL};n={N_SIM};margen=media(equipo,jugadores);impacto={imp.version}")


def minutos_esperados_plantilla(pl, par_props) -> dict:
    """{lado: {jugador: minutos esperados}} sumando 240 por equipo: probabilidad de jugar (parte o rol) × minutos si juega."""
    salida = {}
    for lado, jugadores in pl.lados.items():
        cand = {}
        for j in jugadores:
            mp = minutos.punto(list(j.minutos))
            if mp is None:
                continue
            p = par_props.p_estado.get(j.estado) if j.estado is not None else None
            cand[j.id] = (mp, p if p is not None else par_props.p_sin_parte.get(minutos.tramo(mp), 0.84))
        salida[lado] = modelo.minutos_esperados(cand)
    return salida


def pronosticar(inst: Instantanea, pl, imp, par_props) -> tuple[str, dict, dict]:
    """(version_modelo, escenarios, distribucion) listos para sellar."""
    esperados = minutos_esperados_plantilla(pl, par_props)
    if min(len(esperados["local"]), len(esperados["visitante"])) < MIN_CANDIDATOS_POR_EQUIPO:
        esc, dist = motor_equipo.pronosticar(inst)
        return VERSION_MODELO, esc, dist
    r, ultimo = motor_equipo._ratings(inst)
    dl = (inst.fecha - ultimo[inst.local]).days if inst.local in ultimo else 7
    dv = (inst.fecha - ultimo[inst.visitante]).days if inst.visitante in ultimo else 7
    mu_l, mu_v = r.esperado(inst.local, inst.visitante, nucleo.ajuste_descanso(dl, dv, PARAMETROS))
    descanso = (1.0 if dv == 1 else 0.0) - (1.0 if dl == 1 else 0.0)
    margen_equipo = mu_l - mu_v
    margen_jugadores = imp.impacto.margen(esperados["local"], esperados["visitante"], descanso)
    margen = (margen_equipo + margen_jugadores) / 2
    total = mu_l + mu_v
    mu_l, mu_v = (total + margen) / 2, (total - margen) / 2
    m = nucleo.simular(mu_l, mu_v, imp.sigma_margen, SIGMA_TOTAL, n=N_SIM, semilla=inst.partido_id)
    mg, tt = m.margen(), m.total()
    distribucion = {"p_local": round(mercados.ganador(m), 6), "mu": [round(mu_l, 4), round(mu_v, 4)], "paso_cuantil": 0.005,
                    "margen": [float(mg.cuantil(q)) for q in NIVELES], "total": [float(tt.cuantil(q)) for q in NIVELES],
                    "puntos_local": [float(m.puntos("local").cuantil(q)) for q in NIVELES],
                    "puntos_visitante": [float(m.puntos("visit").cuantil(q)) for q in NIVELES]}
    escenarios = {"descanso_dias": {"local": dl, "visitante": dv}, "partidos_en_historia": len(inst.historia),
                  "margen_equipo": round(margen_equipo, 3), "margen_jugadores": round(margen_jugadores, 3),
                  "jugadores": {"local": len(esperados["local"]), "visitante": len(esperados["visitante"])}, "impacto": imp.version}
    return version(imp), escenarios, distribucion
