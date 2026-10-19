"""Impacto por jugador del once frente al habitual: puntual en el tiempo y con el signo correcto."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from qf.model import jugadores as jg

T0 = datetime(2026, 1, 1, 20, tzinfo=timezone.utc)


def _aparicion(mid, dia, side, equipo, jugador, titular, pos, valor, rating):
    return {"match_id": mid, "kickoff_utc": T0 + timedelta(days=dia), "side": side, "equipo_id": equipo,
            "jugador_id": jugador, "titular": titular, "posicion_id": pos, "valor_mercado": valor, "rating": rating}


def _partido(mid, dia, equipo, once, estrella_ausente=False, rating_estrella=8.5):
    """Equipo 1 de local contra un rival fijo. `once`: ids 1..11; el 11 es la estrella (delantero)."""
    filas = []
    for j in range(1, 12):
        if j == 11 and estrella_ausente:
            j = 99                                       # suplente flojo en su lugar
        pos = 11 if j == 1 else (34 if j <= 5 else (64 if j <= 8 else 104))
        rating = rating_estrella if j == 11 else 6.5
        filas.append(_aparicion(mid, dia, "home", equipo, j, True, pos, 50.0 if j == 11 else 5.0,
                                6.0 if j == 99 else rating))
    for j in range(201, 212):                            # rival
        filas.append(_aparicion(mid, dia, "away", 2, j, True, 64, 5.0, 6.5))
    return filas


def _historia(extra_final):
    filas = []
    for i in range(5):
        filas += _partido(f"m{i}", i, 1, None)
    filas += extra_final
    return pd.DataFrame(filas)


def test_la_ausencia_de_la_estrella_baja_el_delta_y_su_presencia_lo_deja_en_cero():
    con = jg.features_xi(_historia(_partido("m5", 5, 1, None)))
    sin = jg.features_xi(_historia(_partido("m5", 5, 1, None, estrella_ausente=True)))
    f_con = con.set_index("match_id").loc["m5"]
    f_sin = sin.set_index("match_id").loc["m5"]
    assert abs(f_con["epi_total_local"]) < 1e-9                  # mismo once que el habitual
    assert f_sin["epi_total_local"] < -0.3                       # falta la estrella (fuerza alta) y entra un suplente flojo
    assert f_sin["epi_ata_local"] < 0 and abs(f_sin["epi_def_local"]) < 1e-9
    assert f_sin["xiv_delta_local"] < 0 and abs(f_con["xiv_delta_local"]) < 1e-9


def test_el_partido_no_ve_su_propia_calificacion():
    base = jg.features_xi(_historia(_partido("m5", 5, 1, None, rating_estrella=8.5)))
    otra = jg.features_xi(_historia(_partido("m5", 5, 1, None, rating_estrella=3.0)))
    a, b = base.set_index("match_id").loc["m5"], otra.set_index("match_id").loc["m5"]
    assert np.allclose(a.filter(like="epi_").astype(float), b.filter(like="epi_").astype(float), equal_nan=True)


def test_sin_historial_suficiente_queda_nan():
    f = jg.features_xi(pd.DataFrame(_partido("m0", 0, 1, None) + _partido("m1", 1, 1, None)))
    assert f["epi_total_local"].isna().all() and f["xiv_delta_local"].isna().all()


def test_grupos_de_posicion():
    assert jg.grupo_posicion(11) == "def" and jg.grupo_posicion(34) == "def" and jg.grupo_posicion(52) == "def"
    assert jg.grupo_posicion(66) == "med" and jg.grupo_posicion(104) == "ata" and jg.grupo_posicion(115) == "ata"
    assert jg.grupo_posicion(None) is None and jg.grupo_posicion(3) is None
