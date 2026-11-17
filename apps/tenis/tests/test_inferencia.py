"""Inferencia del motor: el mismo filtro que el walk-forward, orientación de lados y motivos de omisión."""
import numpy as np
import pandas as pd
import pytest

from tenis import inferencia as inf
from tenis.modelo import datos as dm
from tenis.modelo.rating import filtrar
from tenis.modelo.sintetico import mundo, tablas_prueba, psi_prueba

from inferencia_util import params_prueba

STATS_VACIAS = pd.DataFrame({"partido_key": pd.Series(dtype="object"), "lado": pd.Series(dtype="int64"),
                             "puntos_saque": pd.Series(dtype="float64"), "puntos_saque_ganados": pd.Series(dtype="float64"),
                             "visible_desde": pd.Series(dtype="datetime64[ns, UTC]")})


def _mundo():
    p, e = mundo(semilla=71, n_semanas=30)
    p["partido_id_tml"] = pd.array([pd.NA] * len(p), dtype="Int64")
    p["partido_id_sofascore"] = pd.array(np.arange(1, len(p) + 1), dtype="Int64")
    return p, e


def test_pronosticar_circuito_es_el_filtro_de_la_evaluacion():
    p, e = _mundo()
    cfg = params_prueba()["circuitos"]["atp"]
    pron = inf.pronosticar_circuito(p, e, STATS_VACIAS, cfg, "atp")
    d = dm.preparar(p, e, "atp", 9999)
    esperado = filtrar(d, psi_prueba(c_inf=0.02), tablas_prueba()).pi
    np.testing.assert_allclose(pron.pi.to_numpy(), esperado, rtol=0, atol=1e-12, equal_nan=True)
    assert list(pron.partido_key) == list(d.p.partido_key)
    assert np.isfinite(pron.pi).sum() > 100 and np.isfinite(pron.s_hat).all()


def _partido_db(pron, i, invertir=False):
    f = pron.iloc[i]
    a, b = int(f.jugador_1), int(f.jugador_2)
    return {"partido_id": int(f.partido_id_sofascore), "jugador_1": b if invertir else a, "jugador_2": a if invertir else b}


def test_resolver_orienta_segun_el_partido_de_la_base():
    p, e = _mundo()
    pron = inf.pronosticar_circuito(p, e, STATS_VACIAS, params_prueba()["circuitos"]["atp"], "atp")
    i = int(np.flatnonzero(np.isfinite(pron.pi.to_numpy()) & (pron.motivo.isna()).to_numpy())[-1])
    a = inf.resolver(pron, _partido_db(pron, i))
    b = inf.resolver(pron, _partido_db(pron, i, invertir=True))      # mismo partido con los lados cambiados
    assert a["ok"] and b["ok"]
    assert a["pi_lado1"] + b["pi_lado1"] == pytest.approx(1.0, abs=1e-12)
    assert a["s_hat"] == b["s_hat"] and a["var_rho"] == b["var_rho"]


def test_resolver_motivos():
    p, e = _mundo()
    pron = inf.pronosticar_circuito(p, e, STATS_VACIAS, params_prueba()["circuitos"]["atp"], "atp")
    assert inf.resolver(pron, {"partido_id": 10**9, "jugador_1": 1, "jugador_2": 2}) == {"ok": False, "motivo": "fuera_de_la_exportacion"}
    ok = _partido_db(pron, 40)
    assert inf.resolver(pron, ok | {"jugador_2": 987654})["motivo"] == "jugadores_no_coinciden"
    malo = pron.copy(); malo.loc[malo.index[40], "motivo"] = "sin_historia_ni_ranking"
    assert inf.resolver(malo, ok) == {"ok": False, "motivo": "sin_historia_ni_ranking"}
    malo.loc[malo.index[40], "motivo"] = None
    malo.loc[malo.index[40], "s_hat"] = np.nan
    assert inf.resolver(malo, ok)["motivo"] == "sin_s_hat"


def test_sin_parametros_del_circuito_no_pronostica():
    class _Sin:                                   # `inferir` solo toca la base si hay algo que pronosticar con parámetros
        pass
    assert inf.inferir(_Sin(), {}, []) == {}


psycopg = pytest.importorskip("psycopg")
from db_util import cargar_minimo  # noqa: E402
from inferencia_util import partido_futuro, ranking  # noqa: E402


def test_inferir_desde_la_base_con_ranking_como_prior(esquema):
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        a, b, c, _ = m["jugadores"]
        # a ya trae el puesto 5 del mundo mínimo. La base exige jugador_1 < jugador_2 (orden canónico por id):
        ranking(db, b, 80)
        ranking(db, c, 3)                                            # c (id mayor) es el mejor del cuadro
        d = m["jugadores"][3]                                        # d sin ranking ni historia
        p_ab = partido_futuro(db, m, a, b, "SF")                     # favorito = lado 1
        p_bc = partido_futuro(db, m, b, c, "QF")                     # favorito = lado 2
        p_ad = partido_futuro(db, m, a, d, "R16")
        base = {"circuito": "atp", "inicio_programado_utc": None, "mejor_de": 3, "superficie": "clay"}
        pend = [base | {"partido_id": p_ab, "jugador_1": a, "jugador_2": b},
                base | {"partido_id": p_bc, "jugador_1": b, "jugador_2": c},
                base | {"partido_id": p_ad, "jugador_1": a, "jugador_2": d}]
        res = inf.inferir(db, params_prueba(), pend)
        assert res[p_ab]["ok"] and res[p_bc]["ok"]
        assert res[p_ab]["pi_lado1"] > 0.5                           # puesto 5 contra 80
        assert res[p_bc]["pi_lado1"] < 0.5                           # puesto 80 contra 3: la orientación aleatoria de la exportación se deshace
        assert res[p_ab]["prior_ranking"] is True
        assert res[p_ad] == {"ok": False, "motivo": "sin_historia_ni_ranking"}
        assert inf.inferir(db, {"circuitos": {}}, pend[:1])[p_ab]["motivo"] == "sin_parametros_del_circuito"


def test_pasada_del_motor_infiere_una_vez_y_omite_sin_historia(esquema, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from tenis import motor
    with esquema.conectar() as db:
        m = cargar_minimo(db)
        a, b, _, d = m["jugadores"]
        ranking(db, b, 80)
        p_ok = partido_futuro(db, m, a, b, "SF")
        p_sin = partido_futuro(db, m, a, d, "R16")                    # d: sin ranking ni historia
        llamadas = []
        real = inf.inferir
        monkeypatch.setattr(motor, "inferir", lambda *args: llamadas.append(args[2]) or real(*args))
        monkeypatch.setattr(motor, "cargar_artefacto_activo",
                            lambda *_: {"version_modelo": "vx", "sha256": "0" * 64, "parametros": params_prueba()})
        monkeypatch.setattr(motor, "enviar_alerta", lambda *a_, **k: {})
        forzado = datetime.now(timezone.utc) - timedelta(hours=1)
        r = motor.ejecutar_pasada_motor(db, forzar_corte=forzado, dry_run=True)
        por_id = {x["partido_id"]: x for x in r["resultados"]}
        assert por_id[p_ok]["estado"] == "dry_run_ok"
        assert por_id[p_sin] == {"estado": "omitido_sin_modelo", "partido_id": p_sin, "motivo": "sin_historia_ni_ranking"}
        assert len(llamadas) == 1                                      # una sola inferencia para toda la pasada
        # Sin forzar corte, ningún partido de 2099 está en ventana: no se infiere nada ni se sella
        llamadas.clear()
        r2 = motor.ejecutar_pasada_motor(db, dry_run=True)
        assert all(x["estado"] == "pendiente_ventana" for x in r2["resultados"])
        assert llamadas == [[]]
