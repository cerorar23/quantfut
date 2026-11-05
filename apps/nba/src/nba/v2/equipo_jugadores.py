"""El impacto solo entra con aprobación temporal para regulación; en otro caso se usa el núcleo validado."""
from . import minutos, motor_equipo, nucleo, estado_equipo
from . import plantilla as modelo
from .motor_equipo import NIVELES, N_SIM
from .pit import Instantanea
from .salida_equipo import serializar
from datetime import date, datetime
import numpy as np
from scipy.special import expit

MIN_CANDIDATOS_POR_EQUIPO = 8


def version(imp) -> str:
    if not imp.aprobado_regulacion:
        return motor_equipo.version()
    _, huella = estado_equipo.artefacto()
    return f'equipo-2.2;posesiones;regulacion-mas-ot;ratings-local;equipo={huella[:12]};impacto={imp.version};pmf-exacta'


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
    if not imp.aprobado_regulacion:
        esc, dist = motor_equipo.pronosticar(inst)
        esc['impacto_bloqueado'] = 'sin_aprobacion_temporal_para_regulacion'
        return motor_equipo.version(), esc, dist
    if imp.objetivo != 'margen_regulacion' or not imp.ot or imp.posesiones_referencia <= 0:
        raise ValueError('impacto incompatible con regulación/OT')
    if date.fromisoformat(imp.datos_hasta) >= inst.fecha:
        raise ValueError('impacto contiene el día objetivo o el futuro')
    if imp.conocido_en_utc is not None:
        conocido = datetime.fromisoformat(imp.conocido_en_utc)
        if conocido.tzinfo is None or conocido > inst.corte:
            raise ValueError('impacto posterior al corte')
    esperados = minutos_esperados_plantilla(pl, par_props)
    if min(len(esperados["local"]), len(esperados["visitante"])) < MIN_CANDIDATOS_POR_EQUIPO:
        esc, dist = motor_equipo.pronosticar(inst)
        return motor_equipo.version(), esc, dist
    e = estado_equipo.estimar(inst)
    dl, dv = e.descanso_local, e.descanso_visitante
    mu_l, mu_v = e.mu_local, e.mu_visitante
    descanso = (1.0 if dv == 1 else 0.0) - (1.0 if dl == 1 else 0.0)
    margen_equipo = mu_l - mu_v
    margen_jugadores = imp.impacto.margen(esperados["local"], esperados["visitante"], descanso)
    margen = (margen_equipo + margen_jugadores) / 2
    total = mu_l + mu_v
    mu_l, mu_v = (total + margen) / 2, (total - margen) / 2
    p_ot = float(expit(imp.ot['intercepto'] + imp.ot['abs_margen'] * abs(margen)))
    sigma_margen = imp.sigma_margen * float(np.sqrt(e.posesiones / imp.posesiones_referencia))
    m = nucleo.simular_con_ot(mu_l, mu_v, sigma_margen, e.sigma_total, e.posesiones,
                             p_ot, n=N_SIM, semilla=inst.partido_id)
    distribucion = serializar(m, *map(float, m.muestras.mean(axis=0)), NIVELES)
    distribucion['tratamiento_ot'] = 'regulacion_mas_prorroga'
    escenarios = {"descanso_dias": {"local": dl, "visitante": dv}, "partidos_en_historia": len(inst.historia),
                  'mu_regulacion': [mu_l, mu_v],
                  "margen_equipo": round(margen_equipo, 3), "margen_jugadores": round(margen_jugadores, 3),
                  "jugadores": {"local": len(esperados["local"]), "visitante": len(esperados["visitante"])}, "impacto": imp.version,
                  'posesiones_regulacion': e.posesiones, 'p_ot': p_ot, 'artefacto_equipo': e.version,
                  'corte_entrenamiento': e.corte_entrenamiento}
    return version(imp), escenarios, distribucion
