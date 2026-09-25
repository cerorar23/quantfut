"""
Verificación del soporte de competiciones entre ligas (Champions, Europa
League) en el modelo de fuerza.

Hay dos propiedades que tienen que cumplirse a la vez y que tiran en
direcciones opuestas:

  1. Un partido de copa NO puede partir al equipo en dos. El Real Madrid de
     Champions y el de LaLiga son el mismo, y si se indexan por la competición
     el de Champions tendría una docena de partidos y ningún rival común.

  2. Un partido doméstico NO puede notar que existe el término de fuerza por
     liga. Si `strength` no se cancelara exactamente cuando los dos equipos
     son de la misma liga, añadir las copas habría cambiado en silencio todo
     lo que ya estaba medido en las ocho ligas.

El tercer test es el que de verdad demuestra que el término sirve para algo:
se simulan dos ligas de nivel MUY distinto, se genera una copa entre ellas y
se comprueba que el modelo recupera la diferencia. Sin partidos de copa esa
diferencia es literalmente inobservable, porque la suma cero es por liga.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.model.dixon_coles import DixonColes, team_key

INICIO = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _liga(league_id: str, n_equipos: int, vueltas: int, nivel: float,
          home_adv: float, base: float, rng) -> pd.DataFrame:
    """
    Genera una liga donde TODOS los equipos comparten un `nivel` común.

    Ese nivel es justo lo que la suma cero por liga borra: dentro de la liga
    no se puede distinguir de un cambio en `base`. Solo reaparece al cruzar.
    """
    equipos = [f"{league_id}_T{i}" for i in range(n_equipos)]
    atk = rng.normal(0, 0.25, n_equipos)
    atk -= atk.mean()
    dfn = rng.normal(0, 0.20, n_equipos)
    dfn -= dfn.mean()

    filas, dia = [], 0
    for _ in range(vueltas):
        for i in range(n_equipos):
            for j in range(n_equipos):
                if i == j:
                    continue
                lam = math.exp(base + (nivel + atk[i]) - (nivel + dfn[j]) + home_adv)
                mu = math.exp(base + (nivel + atk[j]) - (nivel + dfn[i]))
                filas.append({
                    "league_id": league_id,
                    "home_league": league_id, "away_league": league_id,
                    "kickoff_utc": INICIO + timedelta(days=dia % 500),
                    "home_team": equipos[i], "away_team": equipos[j],
                    "home_goals": float(rng.poisson(lam)),
                    "away_goals": float(rng.poisson(mu)),
                    "home_xg": np.nan, "away_xg": np.nan,
                })
                dia += 1
    return pd.DataFrame(filas), equipos, atk, dfn


def _copa(comp: str, a, b, base: float, home_adv: float, rng,
          n: int = 400) -> pd.DataFrame:
    """Cruces entre las dos ligas, alternando quién es local."""
    (lg_a, eq_a, atk_a, dfn_a, niv_a) = a
    (lg_b, eq_b, atk_b, dfn_b, niv_b) = b
    filas = []
    for k in range(n):
        i = rng.integers(len(eq_a))
        j = rng.integers(len(eq_b))
        if k % 2 == 0:
            hl, al = lg_a, lg_b
            ht, at = eq_a[i], eq_b[j]
            ah, dh, nh = atk_a[i], dfn_a[i], niv_a
            aa, da, na = atk_b[j], dfn_b[j], niv_b
        else:
            hl, al = lg_b, lg_a
            ht, at = eq_b[j], eq_a[i]
            ah, dh, nh = atk_b[j], dfn_b[j], niv_b
            aa, da, na = atk_a[i], dfn_a[i], niv_a
        lam = math.exp(base + (nh + ah) - (na + da) + home_adv)
        mu = math.exp(base + (na + aa) - (nh + dh))
        filas.append({
            "league_id": comp, "home_league": hl, "away_league": al,
            "kickoff_utc": INICIO + timedelta(days=int(rng.integers(0, 500))),
            "home_team": ht, "away_team": at,
            "home_goals": float(rng.poisson(lam)),
            "away_goals": float(rng.poisson(mu)),
            "home_xg": np.nan, "away_xg": np.nan,
        })
    return pd.DataFrame(filas)


@pytest.fixture(scope="module")
def ajuste_con_copa():
    """Liga fuerte (nivel +0,20), liga débil (nivel -0,20) y una copa entre ambas."""
    rng = np.random.default_rng(11)
    fuerte, eq_f, atk_f, dfn_f = _liga("lg.fuerte", 10, 4, nivel=0.20,
                                       home_adv=0.30, base=0.15, rng=rng)
    debil, eq_d, atk_d, dfn_d = _liga("lg.debil", 10, 4, nivel=-0.20,
                                      home_adv=0.30, base=0.15, rng=rng)
    copa = _copa("eu.copa",
                 ("lg.fuerte", eq_f, atk_f, dfn_f, 0.20),
                 ("lg.debil", eq_d, atk_d, dfn_d, -0.20),
                 base=0.15, home_adv=0.30, rng=rng)
    df = pd.concat([fuerte, debil, copa], ignore_index=True)
    m = DixonColes(halflife_days=10_000.0, xg_blend=0.0).fit(
        df, as_of=INICIO + timedelta(days=500))
    return m, eq_f, eq_d


# ---------------------------------------------------------------------------
# 1. El equipo no se parte en dos
# ---------------------------------------------------------------------------

def test_un_equipo_de_copa_es_el_mismo_que_el_de_su_liga(ajuste_con_copa):
    m, eq_f, eq_d = ajuste_con_copa
    # Existe indexado por su liga doméstica...
    assert team_key("lg.fuerte", eq_f[0]) in m._idx
    # ...y NO existe una copia bajo la competición.
    assert team_key("eu.copa", eq_f[0]) not in m._idx


def test_la_copa_no_crea_equipos_propios(ajuste_con_copa):
    m, _, _ = ajuste_con_copa
    assert not [t for t in m.params.teams if t.startswith("eu.copa||")]


def test_la_copa_si_tiene_sus_propios_parametros_de_competicion(ajuste_con_copa):
    """Ventaja de local y nivel de goles SÍ son de la competición."""
    m, _, _ = ajuste_con_copa
    assert "eu.copa" in m._lidx
    reporte = {r["league_id"]: r for r in m.league_report()}
    assert reporte["eu.copa"]["n_matches"] > 0
    assert reporte["eu.copa"]["n_teams"] == 0   # ningún equipo le pertenece


# ---------------------------------------------------------------------------
# 2. Los partidos domésticos no se enteran
# ---------------------------------------------------------------------------

def test_en_un_partido_domestico_la_fuerza_de_liga_se_cancela(ajuste_con_copa):
    """
    Es la propiedad que permitió añadir el término sin volver a validar las
    ocho ligas: dentro de una liga, `strength` entra y sale con el mismo signo.
    """
    m, eq_f, _ = ajuste_con_copa
    lam, mu = m.lambdas(eq_f[0], eq_f[1], "lg.fuerte")

    # Se recalcula a mano SIN el término de fuerza.
    p = m.params
    j = m._lidx["lg.fuerte"]
    hi = m._idx[team_key("lg.fuerte", eq_f[0])]
    ai = m._idx[team_key("lg.fuerte", eq_f[1])]
    lam_sin = math.exp(p.base[j] + p.home_adv[j] + p.attack[hi] - p.defence[ai])
    mu_sin = math.exp(p.base[j] + p.attack[ai] - p.defence[hi])

    assert lam == pytest.approx(lam_sin, rel=1e-9)
    assert mu == pytest.approx(mu_sin, rel=1e-9)


def test_sin_partidos_entre_ligas_el_termino_queda_plano():
    """
    Un modelo entrenado solo con ligas domésticas no tiene NADA que identifique
    la fuerza relativa. La penalización tiene que dejarla plana, o el
    optimizador derivaría por una dirección que no cambia la verosimilitud.
    """
    rng = np.random.default_rng(3)
    a, *_ = _liga("lg.a", 10, 3, nivel=0.0, home_adv=0.30, base=0.15, rng=rng)
    b, *_ = _liga("lg.b", 10, 3, nivel=0.0, home_adv=0.30, base=0.15, rng=rng)
    m = DixonColes(halflife_days=10_000.0, xg_blend=0.0).fit(
        pd.concat([a, b], ignore_index=True),
        as_of=INICIO + timedelta(days=500))
    fuerzas = m.params.strength
    assert max(fuerzas) - min(fuerzas) < 0.02


# ---------------------------------------------------------------------------
# 3. Con copa, la diferencia de nivel SÍ se recupera
# ---------------------------------------------------------------------------

def test_la_copa_identifica_que_liga_es_mejor(ajuste_con_copa):
    m, _, _ = ajuste_con_copa
    rep = {r["league_id"]: r for r in m.league_report()}
    fuerte = rep["lg.fuerte"]["relative_strength"]
    debil = rep["lg.debil"]["relative_strength"]
    assert fuerte > debil, (
        f"La liga simulada como mejor salió con menos fuerza "
        f"({fuerte:.4f} vs {debil:.4f})"
    )


def test_un_equipo_de_la_liga_fuerte_es_favorito_fuera_de_casa(ajuste_con_copa):
    """
    La prueba que le importa al negocio: en un cruce, el modelo tiene que
    saber que visitar al de la liga débil no es lo mismo que visitar a uno de
    la suya. Se comparan dos partidos idénticos salvo la liga del rival.
    """
    m, eq_f, eq_d = ajuste_con_copa
    # Mismo local, mismo papel; solo cambia de dónde viene el visitante.
    lam_vs_debil, mu_vs_debil = m.lambdas(
        eq_f[0], eq_d[0], "eu.copa", "lg.fuerte", "lg.debil")
    lam_vs_fuerte, mu_vs_fuerte = m.lambdas(
        eq_f[0], eq_f[1], "eu.copa", "lg.fuerte", "lg.fuerte")
    # Contra un rival de la liga débil se esperan más goles a favor y menos en
    # contra que contra uno de la propia.
    assert (lam_vs_debil / mu_vs_debil) > (lam_vs_fuerte / mu_vs_fuerte)


# ---------------------------------------------------------------------------
# Compatibilidad hacia atrás
# ---------------------------------------------------------------------------

def test_un_dataframe_sin_columnas_de_liga_domestica_sigue_funcionando():
    """
    Todo el histórico anterior se entrena sin `home_league`/`away_league`. Si
    faltan, la liga doméstica ES la competición y el modelo se comporta como
    antes de existir las copas.
    """
    rng = np.random.default_rng(5)
    a, *_ = _liga("lg.a", 10, 3, nivel=0.0, home_adv=0.30, base=0.15, rng=rng)
    sin_cols = a.drop(columns=["home_league", "away_league"])
    m = DixonColes(halflife_days=10_000.0, xg_blend=0.0).fit(
        sin_cols, as_of=INICIO + timedelta(days=500))
    assert m.params.team_leagues
    assert all(lg == "lg.a" for lg in m.params.team_leagues)
    # Y predice sin que haga falta pasar las ligas domésticas.
    lam, mu = m.lambdas(a["home_team"].iloc[0], a["away_team"].iloc[0], "lg.a")
    assert 0.2 < lam < 6.0 and 0.2 < mu < 6.0
