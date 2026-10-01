"""
Valor por jugador (fuerza por jugador, Fase B1).

Lo que fijan: el decaimiento hace pesar más lo reciente; un jugador con pocos
minutos queda cerca de la media de su posición; el acumulador no ve lo que
todavía no se le ha añadido (punto en el tiempo).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model.player_ratings import (ESTADISTICAS, MINUTOS_PREVIA, NOTA_FEATURES,
                                     VALOR_FEATURES, Acumulador, build_value_features)

T0 = pd.Timestamp("2026-01-01", tz="UTC")


def _fila(pid, pos="F", minutos=90, tiros=0, nota=7.0):
    f = {e: 0 for e in ESTADISTICAS}
    f.update(player_id=pid, posicion=pos, minutos=minutos, tiros=tiros,
             nota_proveedor=nota)
    return f


def _i(nombre):
    return ESTADISTICAS.index(nombre)


def test_pocos_minutos_se_quedan_cerca_de_la_media_de_su_posicion():
    acc = Acumulador(180)
    acc.avanzar(T0)
    for pid in range(10):                        # delanteros "medios": 2 tiros/90
        acc.anadir(_fila(pid, tiros=2))
    acc.anadir(_fila(99, minutos=10, tiros=3))   # 3 tiros en 10 min = 27/90
    tasa = acc.tasas(99, "F")[_i("tiros")]      # misma hora: sin decaimiento
    esperado = (3 + MINUTOS_PREVIA * (23 / 910)) / (10 + MINUTOS_PREVIA) * 90
    assert abs(tasa - esperado) < 1e-6
    assert tasa < 3.0, "10 minutos no bastan para parecer un goleador"


def test_lo_reciente_pesa_mas():
    acc = Acumulador(180)
    acc.avanzar(T0)
    acc.anadir(_fila(1, tiros=0))
    acc.avanzar(T0 + pd.Timedelta(days=360))     # dos vidas medias
    acc.anadir(_fila(1, tiros=4))
    acc.avanzar(T0 + pd.Timedelta(days=361))
    # Sin decaimiento serían 4 tiros en 180 min = 2,0/90. Con el partido viejo
    # pesando 0,25: 4 / (90 + 22,5) · 90 ≈ 3,2.
    assert acc.tasas(1, "F")[_i("tiros")] > 2.5


def test_sin_historial_devuelve_la_media_de_su_posicion():
    acc = Acumulador(180)
    acc.avanzar(T0)
    acc.anadir(_fila(1, pos="G", tiros=0))
    acc.anadir(_fila(2, pos="F", tiros=2))
    acc.avanzar(T0 + pd.Timedelta(days=1))
    assert not acc.conocido(3)
    assert abs(acc.tasas(3, "F")[_i("tiros")] - 2.0) < 1e-9
    assert np.isnan(Acumulador(180).nota(5, "F"))


def test_no_ve_lo_que_no_se_le_ha_anadido():
    acc = Acumulador(180)
    acc.avanzar(T0)
    antes = acc.tasas(1, "F").copy()
    acc.avanzar(T0 + pd.Timedelta(days=7))
    assert np.array_equal(np.nan_to_num(antes), np.nan_to_num(acc.tasas(1, "F")))


XI = [{"player_id": i, "pos": "G" if i == 1 else "D" if i < 6 else "M" if i < 10 else "F"}
      for i in range(1, 12)]
RIVAL = [{"player_id": 100 + p["player_id"], "pos": p["pos"]} for p in XI]


def _temporada(n, ultimo_xi=None):
    """n partidos del equipo 1 (local) contra el 2; el 11 es el goleador."""
    matches, lineups, stats = [], [], []
    for k in range(n):
        mid, ko = f"m{k}", T0 + pd.Timedelta(days=7 * k)
        matches.append({"match_id": mid, "kickoff_utc": ko, "home_team_id": 1,
                        "away_team_id": 2})
        xi = ultimo_xi if (ultimo_xi is not None and k == n - 1) else XI
        lineups += [{"match_id": mid, "side": "home", "starters": xi},
                    {"match_id": mid, "side": "away", "starters": RIVAL}]
        for p in XI + RIVAL:
            f = _fila(p["player_id"], p["pos"], tiros=5 if p["player_id"] == 11 else 0)
            f["match_id"] = mid
            stats.append(f)
    return pd.DataFrame(matches), pd.DataFrame(lineups), pd.DataFrame(stats)


def test_con_el_xi_habitual_la_senal_es_cero():
    m, l, s = _temporada(6)
    f = build_value_features(m, l, s).set_index("match_id")
    assert set(f.index) == {"m3", "m4", "m5"}, "hacen falta 3 XI previos"
    assert np.allclose(f.loc["m5", VALOR_FEATURES].to_numpy(float), 0.0)


def test_sin_el_goleador_se_pierde_valor_ofensivo():
    sin_goleador = XI[:-1] + [{"player_id": 50, "pos": "F"}]
    m, l, s = _temporada(6, ultimo_xi=sin_goleador)
    f = build_value_features(m, l, s).set_index("match_id")
    assert f.loc["m5", "home_d_tiros"] < -1.0
    assert abs(f.loc["m5", "away_d_tiros"]) < 1e-9


def test_mas_de_3_desconocidos_no_da_senal():
    extranos = XI[:7] + [{"player_id": 900 + i, "pos": "F"} for i in range(4)]
    m, l, s = _temporada(6, ultimo_xi=extranos)
    assert "m5" not in set(build_value_features(m, l, s)["match_id"])


def test_partidos_posteriores_no_cambian_el_pasado():
    m, l, s = _temporada(5)
    corto = build_value_features(m, l, s).set_index("match_id")
    m2, l2, s2 = _temporada(8)
    largo = build_value_features(m2, l2, s2).set_index("match_id")
    cols = VALOR_FEATURES + NOTA_FEATURES
    pd.testing.assert_frame_equal(corto[cols], largo.loc[corto.index, cols])
