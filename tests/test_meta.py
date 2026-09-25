"""
Verificación del estimador de peso modelo/mercado.

Los tests construyen escenarios donde la respuesta correcta se conoce de
antemano:

  - Si el "modelo" es el que genera los resultados y el mercado es ruido,
    el peso debe irse hacia 1.
  - Si el mercado es el que genera los resultados y el modelo es ruido,
    el peso debe irse hacia 0.
  - Si ambos aportan, debe quedarse en medio.

Un estimador que no distinga estos tres casos no sirve para nada, por muy
limpio que sea el código.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.eval.metrics import log_loss
from qf.model.meta import (
    MIN_LEAGUE_OBS,
    MetaBlender,
    fit_and_validate,
)

START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _norm(x: np.ndarray) -> np.ndarray:
    return x / x.sum(axis=1, keepdims=True)


def make_probs(n: int, rng: np.random.Generator) -> np.ndarray:
    raw = rng.dirichlet([6.0, 4.0, 5.0], size=n)
    return _norm(np.clip(raw, 0.02, 0.96))


def sample_outcomes(p: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    u = rng.random(len(p))
    return (u[:, None] > np.cumsum(p, axis=1)).sum(axis=1).clip(0, 2)


def make_oos(n: int, verdad: str, seed: int = 0,
             leagues: list[str] | None = None) -> pd.DataFrame:
    """
    `verdad` decide quién genera los resultados: 'modelo', 'mercado' o 'ambos'.
    El otro lado se construye como una versión ruidosa, de modo que ambos son
    probabilidades plausibles pero solo uno tiene la información.
    """
    rng = np.random.default_rng(seed)
    p_true = make_probs(n, rng)
    ruido = _norm(np.clip(p_true + rng.normal(0, 0.12, p_true.shape), 0.02, 0.96))

    if verdad == "modelo":
        p_model, p_market = p_true, ruido
    elif verdad == "mercado":
        p_model, p_market = ruido, p_true
    else:
        # Los dos son versiones ruidosas independientes: la mezcla debe ganar
        # a cualquiera de los dos por separado.
        p_model = _norm(np.clip(p_true + rng.normal(0, 0.10, p_true.shape), 0.02, 0.96))
        p_market = _norm(np.clip(p_true + rng.normal(0, 0.10, p_true.shape), 0.02, 0.96))

    outcomes = sample_outcomes(p_true, rng)
    lg = (rng.choice(leagues, n) if leagues else ["L1"] * n)

    return pd.DataFrame({
        "kickoff_utc": [START + timedelta(hours=6 * i) for i in range(n)],
        "league_id": lg,
        "p_home": p_model[:, 0], "p_draw": p_model[:, 1], "p_away": p_model[:, 2],
        "mk_home": p_market[:, 0], "mk_draw": p_market[:, 1], "mk_away": p_market[:, 2],
        "outcome": outcomes,
    })


# ---------------------------------------------------------------------------
# Recuperación del peso
# ---------------------------------------------------------------------------

def test_peso_alto_cuando_el_modelo_tiene_la_informacion():
    oos = make_oos(4000, "modelo", seed=1)
    mb, report = fit_and_validate(oos)
    assert report["w_model"] > 0.7, f"Peso demasiado bajo: {report['w_model']}"


def test_peso_bajo_cuando_el_mercado_tiene_la_informacion():
    """El caso realista en fútbol, y el que el sistema debe saber reconocer."""
    oos = make_oos(4000, "mercado", seed=2)
    mb, report = fit_and_validate(oos)
    assert report["w_model"] < 0.3, f"Peso demasiado alto: {report['w_model']}"


def test_peso_intermedio_cuando_ambos_aportan():
    oos = make_oos(5000, "ambos", seed=3)
    mb, report = fit_and_validate(oos)
    assert 0.2 < report["w_model"] < 0.8, (
        f"No detectó que ambos aportan: w={report['w_model']}"
    )
    # Y la mezcla debe batir a cada uno por separado.
    assert report["log_loss_mezcla"] < report["log_loss_modelo"]
    assert report["log_loss_mezcla"] < report["log_loss_mercado"]


def test_el_informe_compara_contra_el_mercado_solo():
    """
    La comparación que importa no es modelo vs mezcla, sino si aportas algo
    sobre el mercado. El informe debe permitir responder eso.
    """
    oos = make_oos(4000, "mercado", seed=4)
    _, report = fit_and_validate(oos)
    for k in ("log_loss_modelo", "log_loss_mercado", "log_loss_mezcla",
              "rps_modelo", "rps_mercado", "rps_mezcla", "bate_al_mercado"):
        assert k in report, f"Falta {k} en el informe"


def test_lectura_en_lenguaje_claro_segun_el_peso():
    _, bajo = fit_and_validate(make_oos(4000, "mercado", seed=5))
    assert "lectura" in bajo
    _, alto = fit_and_validate(make_oos(4000, "modelo", seed=6))
    assert "fuga" in alto["lectura"].lower(), (
        "Un peso alto debe advertir de posible fuga, no celebrarse"
    )


# ---------------------------------------------------------------------------
# Mezcla
# ---------------------------------------------------------------------------

def test_identidad_devuelve_el_modelo_sin_tocar():
    mb = MetaBlender.identity()
    assert mb.params.is_identity
    p = np.array([0.5, 0.3, 0.2])
    out = mb.blend(p, np.array([0.2, 0.3, 0.5]))
    assert np.allclose(out, p, atol=1e-9)


def test_peso_cero_devuelve_el_mercado():
    mb = MetaBlender()
    mb.params.w_model = 0.0
    mercado = np.array([0.25, 0.30, 0.45])
    out = mb.blend(np.array([0.7, 0.2, 0.1]), mercado)
    assert np.allclose(out, mercado, atol=1e-9)


def test_la_mezcla_queda_entre_ambos():
    mb = MetaBlender()
    mb.params.w_model = 0.5
    modelo = np.array([0.60, 0.25, 0.15])
    mercado = np.array([0.30, 0.30, 0.40])
    out = mb.blend(modelo, mercado)
    assert modelo[0] > out[0] > mercado[0]
    assert out.sum() == pytest.approx(1.0)


def test_funciona_con_mercados_de_dos_vias():
    """Over/under: la misma mezcla debe valer para k=2, no solo para 1X2."""
    mb = MetaBlender()
    mb.params.w_model = 0.3
    out = mb.blend(np.array([0.62, 0.38]), np.array([0.50, 0.50]))
    assert len(out) == 2
    assert out.sum() == pytest.approx(1.0)
    assert 0.50 < out[0] < 0.62


def test_mezcla_vectorizada_coincide_con_la_fila_a_fila():
    mb = MetaBlender()
    mb.params.w_model = 0.4
    rng = np.random.default_rng(10)
    m = make_probs(50, rng)
    k = make_probs(50, rng)
    lote = mb.blend(m, k)
    for i in range(50):
        assert np.allclose(lote[i], mb.blend(m[i], k[i]), atol=1e-12)


# ---------------------------------------------------------------------------
# Pesos por liga
# ---------------------------------------------------------------------------

def test_estima_pesos_por_liga_con_muestra_suficiente():
    oos = make_oos(6000, "ambos", seed=7, leagues=["mx", "eng", "bra"])
    mb, report = fit_and_validate(oos)
    assert report["w_by_league"], "No estimó ningún peso por liga"
    for lg, w in report["w_by_league"].items():
        assert 0.0 <= w <= 1.0


def test_liga_con_pocos_datos_no_recibe_peso_propio():
    oos = make_oos(3000, "ambos", seed=8, leagues=["grande"])
    # Una liga diminuta añadida a mano, por debajo del mínimo.
    pequena = make_oos(MIN_LEAGUE_OBS - 50, "ambos", seed=9, leagues=["pequena"])
    mixto = pd.concat([oos, pequena], ignore_index=True).sort_values("kickoff_utc")
    mb, report = fit_and_validate(mixto)
    assert "pequena" not in report["w_by_league"]


def test_weight_for_cae_al_global_si_la_liga_no_tiene_peso():
    mb = MetaBlender()
    mb.params.w_model = 0.22
    mb.params.w_by_league = {"mx": 0.4}
    assert mb.weight_for("mx") == pytest.approx(0.4)
    assert mb.weight_for("liga_desconocida") == pytest.approx(0.22)
    assert mb.weight_for(None) == pytest.approx(0.22)


# ---------------------------------------------------------------------------
# Puerta de validación y persistencia
# ---------------------------------------------------------------------------

def test_datos_insuficientes_devuelve_identidad():
    mb, report = fit_and_validate(make_oos(200, "ambos", seed=11))
    assert not report["ok"]
    assert mb.params.is_identity
    assert "insuficientes" in report["reason"]


def test_sin_cuotas_no_se_puede_estimar():
    oos = make_oos(3000, "ambos", seed=12)
    oos[["mk_home", "mk_draw", "mk_away"]] = np.nan
    mb, report = fit_and_validate(oos)
    assert not report["ok"]
    assert mb.params.is_identity


def test_muestra_insuficiente_en_fit_es_error_explicito():
    rng = np.random.default_rng(13)
    with pytest.raises(ValueError, match="insuficiente"):
        MetaBlender().fit(make_probs(100, rng), make_probs(100, rng),
                          np.zeros(100, dtype=int))


def test_persistencia_conserva_pesos(tmp_path):
    oos = make_oos(5000, "ambos", seed=14, leagues=["mx", "eng"])
    mb, _ = fit_and_validate(oos)
    path = str(tmp_path / "meta.pkl")
    mb.save(path)
    otro = MetaBlender.load(path)
    assert otro.params.w_model == pytest.approx(mb.params.w_model)
    assert otro.params.w_by_league == mb.params.w_by_league


def test_la_mezcla_reduce_el_edge_frente_al_mercado():
    """
    Consecuencia de negocio que hay que poder demostrar: mezclar acerca al
    mercado, luego el edge aparente BAJA. Si no bajara, la mezcla no estaría
    haciendo nada.
    """
    mb = MetaBlender()
    mb.params.w_model = 0.2
    modelo = np.array([0.60, 0.25, 0.15])
    mercado = np.array([0.45, 0.28, 0.27])
    cuota = 1.0 / mercado[0]

    edge_antes = modelo[0] * cuota - 1.0
    edge_despues = mb.blend(modelo, mercado)[0] * cuota - 1.0
    assert 0 < edge_despues < edge_antes
