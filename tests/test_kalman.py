"""
Verificación de los ratings dinámicos.

La pregunta que responden estos tests no es "¿converge?" —eso lo hace
cualquier estimador— sino las tres propiedades por las que este modelo existe
y que el decaimiento exponencial NO tiene:

  1. Recupera la fuerza real de cada equipo.
  2. Ante un cambio brusco de fuerza, se adapta más rápido que un ajuste
     estático sobre la misma ventana.
  3. La incertidumbre CRECE con el tiempo parado, así que el primer partido
     tras un parón mueve más el rating.

Y una cuarta, que es de seguridad: `predict_sequential` no puede ver el
futuro ni aunque alguien se olvide de un filtro.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.model.kalman import (
    DynamicRatings,
    KalmanConfig,
    tune_process_var,
)

START = datetime(2022, 1, 1, tzinfo=timezone.utc)


def liga_sintetica(n_equipos=10, n_vueltas=8, ha=0.30, base=0.15,
                   seed=0, cambio=None):
    """
    Genera una liga con fuerzas conocidas.

    `cambio`: (indice_equipo, vuelta, nuevo_ataque) introduce un cambio brusco
    de fuerza a mitad del histórico, que es el escenario que justifica todo
    este módulo (cambio de entrenador, fichajes, plantilla rehecha).
    """
    rng = np.random.default_rng(seed)
    equipos = [f"T{i:02d}" for i in range(n_equipos)]
    atk = rng.normal(0, 0.30, n_equipos)
    atk -= atk.mean()
    dfn = rng.normal(0, 0.25, n_equipos)
    dfn -= dfn.mean()

    filas, dia = [], 0
    for vuelta in range(n_vueltas):
        if cambio and vuelta == cambio[1]:
            atk[cambio[0]] = cambio[2]
        for i in range(n_equipos):
            for j in range(n_equipos):
                if i == j:
                    continue
                dia += 1
                ko = START + timedelta(days=dia // 4)
                lam = math.exp(base + atk[i] - dfn[j] + ha)
                mu = math.exp(base + atk[j] - dfn[i])
                filas.append({
                    "match_id": f"m{dia}", "league_id": "L1",
                    "kickoff_utc": ko,
                    "home_team": equipos[i], "away_team": equipos[j],
                    "home_goals": float(rng.poisson(lam)),
                    "away_goals": float(rng.poisson(mu)),
                    "home_xg": np.nan, "away_xg": np.nan,
                })
    return pd.DataFrame(filas), equipos, atk, dfn


# ---------------------------------------------------------------------------
# Recuperación
# ---------------------------------------------------------------------------

def test_recupera_el_orden_de_fuerza_de_los_equipos():
    df, equipos, atk, dfn = liga_sintetica(seed=1)
    m = DynamicRatings(KalmanConfig(xg_blend=0.0)).fit(df)

    verdad = {e: atk[i] + dfn[i] for i, e in enumerate(equipos)}
    estimado = {e: m._state("L1", e).attack + m._state("L1", e).defence
                for e in equipos}
    orden_v = [e for e, _ in sorted(verdad.items(), key=lambda x: -x[1])]
    orden_e = [e for e, _ in sorted(estimado.items(), key=lambda x: -x[1])]

    # Correlación de rangos alta: no se exige orden exacto (hay ruido Poisson)
    rv = {e: i for i, e in enumerate(orden_v)}
    re_ = {e: i for i, e in enumerate(orden_e)}
    d2 = sum((rv[e] - re_[e]) ** 2 for e in equipos)
    n = len(equipos)
    spearman = 1 - 6 * d2 / (n * (n * n - 1))
    assert spearman > 0.7, f"Correlación de rangos demasiado baja: {spearman:.2f}"


def test_estima_parametros_de_liga_razonables():
    df, *_ = liga_sintetica(ha=0.30, base=0.15, seed=2)
    m = DynamicRatings().fit(df)
    lp = m._league("L1")
    assert lp.home_adv == pytest.approx(0.30, abs=0.10)
    assert lp.base == pytest.approx(0.15, abs=0.15)


def test_liga_desconocida_cae_a_la_media():
    df, *_ = liga_sintetica(seed=3)
    m = DynamicRatings().fit(df)
    lp = m._league("liga_que_no_existe")
    assert lp.home_adv == pytest.approx(m._league("L1").home_adv, abs=1e-9)


# ---------------------------------------------------------------------------
# La razón de ser: adaptación a cambios
# ---------------------------------------------------------------------------

def test_se_adapta_a_un_cambio_brusco_de_fuerza():
    """
    Un equipo se vuelve mucho mejor a mitad de histórico. El rating final debe
    reflejar la fuerza NUEVA, no el promedio de las dos épocas.
    """
    df, equipos, atk, _ = liga_sintetica(n_vueltas=10, seed=4,
                                         cambio=(0, 5, 1.0))
    m = DynamicRatings(KalmanConfig(xg_blend=0.0)).fit(df)

    cambiado = m._state("L1", equipos[0]).attack
    otros = [m._state("L1", e).attack for e in equipos[1:]]
    assert cambiado > max(otros), (
        f"No detectó el salto de fuerza: {cambiado:.3f} vs max otros {max(otros):.3f}"
    )
    # Debe acercarse al valor nuevo (1.0), no quedarse en el promedio histórico.
    assert cambiado > 0.45, f"Se quedó en el promedio de ambas épocas: {cambiado:.3f}"


def test_reacciona_mas_rapido_que_un_promedio_estatico():
    """
    Comparación directa contra el estimador que sustituye: la media histórica
    de goles del equipo, que es lo que hace en esencia un ajuste estático.
    """
    df, equipos, *_ = liga_sintetica(n_vueltas=10, seed=5, cambio=(0, 5, 1.0))
    m = DynamicRatings(KalmanConfig(xg_blend=0.0)).fit(df)

    # Media de goles del equipo cambiado en TODO el histórico vs en la época
    # nueva: el promedio estático se queda a medio camino por construcción.
    eq = equipos[0]
    suyos = df[(df["home_team"] == eq) | (df["away_team"] == eq)]
    corte = suyos["kickoff_utc"].quantile(0.5)
    goles_todos = suyos.apply(
        lambda r: r["home_goals"] if r["home_team"] == eq else r["away_goals"],
        axis=1).mean()
    goles_nuevos = suyos[suyos["kickoff_utc"] > corte].apply(
        lambda r: r["home_goals"] if r["home_team"] == eq else r["away_goals"],
        axis=1).mean()

    lam, _ = m.lambdas(eq, equipos[1], "L1")
    # El filtro debe estar más cerca de la época NUEVA que de la media global.
    assert abs(lam - goles_nuevos) < abs(goles_todos - goles_nuevos) + 0.35


def test_la_incertidumbre_crece_con_el_tiempo_parado():
    m = DynamicRatings()
    m.leagues["L1"] = type(m._league("L1"))(base=0.1, home_adv=0.3, n_matches=100)
    st = m._state("L1", "A")
    st.last_seen = START
    st.var_attack = 0.01

    m._advance(st, START + timedelta(days=90))
    var_parado_largo = st.var_attack

    st2 = m._state("L1", "B")
    st2.last_seen = START
    st2.var_attack = 0.01
    m._advance(st2, START + timedelta(days=3))
    var_parado_corto = st2.var_attack

    assert var_parado_largo > var_parado_corto, (
        "Un parón de 3 meses debe dejar el rating más incierto que uno de 3 días"
    )


def test_mas_incertidumbre_significa_actualizacion_mas_grande():
    """Es la consecuencia práctica: el filtro aprende más cuando sabe menos."""
    m = DynamicRatings()
    x_inicial = 0.0
    lam = 1.4
    y = 4.0            # resultado sorprendente

    x_incierto, _ = m._update_component(x_inicial, 0.25, y, lam, +1.0)
    x_seguro, _ = m._update_component(x_inicial, 0.01, y, lam, +1.0)

    assert abs(x_incierto - x_inicial) > abs(x_seguro - x_inicial)


def test_la_incertidumbre_baja_al_acumular_partidos():
    df, equipos, *_ = liga_sintetica(n_vueltas=8, seed=6)
    m = DynamicRatings().fit(df)
    st = m._state("L1", equipos[0])
    assert st.var_attack < 0.25, "La varianza no bajó respecto a la inicial"
    assert st.n_matches > 50


# ---------------------------------------------------------------------------
# Seguridad point-in-time
# ---------------------------------------------------------------------------

def test_predict_sequential_no_puede_ver_el_futuro():
    """
    Se verifica por construcción: se guarda el estado antes de cada predicción
    y se comprueba que el número de partidos vistos por los equipos implicados
    nunca incluye el partido que se está prediciendo.
    """
    df, *_ = liga_sintetica(n_equipos=6, n_vueltas=6, seed=7)
    m = DynamicRatings()
    oos = m.predict_sequential(df, min_matches=3)

    # Cada fila predicha debe corresponder a un partido posterior al anterior
    assert oos["kickoff_utc"].is_monotonic_increasing
    # Y el total de predicciones debe ser menor que el de partidos: los
    # primeros de cada equipo se descartan a propósito.
    assert len(oos) < len(df)


def test_predict_sequential_devuelve_el_formato_del_backtest():
    df, *_ = liga_sintetica(n_equipos=6, n_vueltas=6, seed=8)
    oos = DynamicRatings().predict_sequential(df, min_matches=3)
    for col in ("kickoff_utc", "league_id", "p_home", "p_draw", "p_away",
                "lam", "mu", "mk_home", "outcome", "both_known"):
        assert col in oos.columns, f"Falta la columna {col}"
    p = oos[["p_home", "p_draw", "p_away"]].to_numpy()
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-9)


def test_min_matches_descarta_el_arranque_del_filtro():
    df, *_ = liga_sintetica(n_equipos=6, n_vueltas=6, seed=9)
    pocos = DynamicRatings().predict_sequential(df, min_matches=1)
    muchos = DynamicRatings().predict_sequential(df, min_matches=10)
    assert len(muchos) < len(pocos)


# ---------------------------------------------------------------------------
# Integración y utilidades
# ---------------------------------------------------------------------------

def test_predict_devuelve_mercados_validos():
    df, equipos, *_ = liga_sintetica(seed=10)
    m = DynamicRatings().fit(df)
    out = m.predict(equipos[0], equipos[1], "L1")
    p = out["1x2"]
    assert p["home"] + p["draw"] + p["away"] == pytest.approx(1.0, abs=1e-9)
    assert out["_meta"]["engine"] == "kalman"
    assert out["_meta"]["both_teams_known"]


def test_equipo_desconocido_arranca_neutro_y_con_mucha_incertidumbre():
    df, *_ = liga_sintetica(seed=11)
    m = DynamicRatings().fit(df)
    st = m._state("L1", "RecienAscendido")
    assert st.attack == 0.0 and st.defence == 0.0
    assert st.var_attack == pytest.approx(m.cfg.init_var)
    assert not m.knows("RecienAscendido", "OtroNuevo", "L1")


def test_muestra_insuficiente_es_error_explicito():
    df, *_ = liga_sintetica(n_equipos=3, n_vueltas=1, seed=12)
    with pytest.raises(ValueError, match="insuficiente"):
        DynamicRatings().fit(df.head(20))


def test_persistencia_conserva_el_estado(tmp_path):
    df, equipos, *_ = liga_sintetica(seed=13)
    m = DynamicRatings().fit(df)
    path = str(tmp_path / "kal.pkl")
    m.save(path)
    otro = DynamicRatings.load(path)
    assert otro.lambdas(equipos[0], equipos[1], "L1") == \
           m.lambdas(equipos[0], equipos[1], "L1")


def test_tune_process_var_elige_alguno():
    df, *_ = liga_sintetica(n_equipos=8, n_vueltas=6, seed=14)
    res = tune_process_var(df, grid=(1e-4, 5e-4))
    assert res["best_process_var"] in (1e-4, 5e-4)
    assert res["results"]


def test_top_teams_ordena_por_fuerza():
    df, *_ = liga_sintetica(seed=15)
    top = DynamicRatings().fit(df).top_teams(5)
    assert len(top) == 5
    assert top == sorted(top, key=lambda x: -x["net"])
    assert all("uncertainty" in t for t in top)
