"""
Picks de ligas "solo sharp" (db/023): sin predicción del modelo.

Antes cada pick exigía una predicción (`picks.prediction_id` NOT NULL) y el
job diario solo buscaba picks entre los partidos predichos. LaLiga 2 y Serie B
no se predicen a propósito (el modelo no conoce a sus equipos y lo sellado es
inmutable), así que aunque su sombra pasara la puerta nunca habrían podido
publicarse. El criterio de precio no necesita el modelo: `db/025` permite
`prediction_id` y `model_prob` vacíos, y el job diario añade esos partidos a
la selección sin predecirlos ni sellar predicción alguna para ellos.

Lo que fijan estos tests:
  - un pick sin predicción lleva prediction_id y model_prob vacíos, nunca un
    0 que se leería como "el modelo da 0%";
  - el job diario selecciona también entre partidos solo sharp, y sigue sin
    predecirlos;
  - con la publicación cerrada no cambia nada: ni selección ni picks;
  - el aviso de Telegram no revienta con model_prob vacío.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from qf.config import settings
from qf.publish import daily
from qf.publish import picks as pk
from qf.publish import telegram as tg

NOW = datetime(2026, 9, 26, 8, 0, tzinfo=timezone.utc)
PIN = {"home": 2.00, "draw": 3.40, "away": 4.00}
NORMAL = {"home": 1.95, "draw": 3.30, "away": 3.90}


def _snap():
    return pk.Snapshot("api_football", NOW - timedelta(hours=1), {
        "pinnacle": PIN, "marathonbet": NORMAL, "betvictor": NORMAL,
        "1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7}})


def _solo_sharp():
    return {"prediction_id": None, "match_id": "es.laliga2:m9", "markets": {},
            "kickoff_utc": NOW + timedelta(hours=20), "league_id": "es.laliga2",
            "teams": ("Leganes", "Albacete")}


def test_un_pick_sin_prediccion_no_inventa_datos_del_modelo(monkeypatch):
    monkeypatch.setattr(pk, "_af_snapshot", lambda m, now: _snap())
    monkeypatch.setattr(pk, "_odds_api_snapshot", lambda m, now: None)
    monkeypatch.setattr(pk, "persistencias", lambda: dict(pk.PERSISTENCE))
    (c,) = pk.find_candidates(_solo_sharp(), NOW)
    assert c.prediction_id is None
    assert c.model_prob is None, "0 se leería como 'el modelo da 0%'"
    assert c.best_book == "1xbet" and c.min_price is not None


def test_con_prediccion_todo_sigue_igual(monkeypatch):
    monkeypatch.setattr(pk, "_af_snapshot", lambda m, now: _snap())
    monkeypatch.setattr(pk, "_odds_api_snapshot", lambda m, now: None)
    monkeypatch.setattr(pk, "persistencias", lambda: dict(pk.PERSISTENCE))
    pred = {"prediction_id": "p1", "match_id": "m1", "league_id": "es.laliga",
            "kickoff_utc": NOW + timedelta(hours=20),
            "markets": {"1x2": {"home": 0.61, "draw": 0.22, "away": 0.17}}}
    (c,) = pk.find_candidates(pred, NOW)
    assert c.prediction_id == "p1" and c.model_prob == 0.61


def test_la_consulta_de_partidos_solo_sharp(monkeypatch):
    sql = []
    monkeypatch.setattr(daily, "query", lambda s, p=None: sql.append(s) or [])
    assert daily._sharp_only_upcoming() == []
    assert "NOT lg.model_enabled" in sql[0] and "'scheduled'" in sql[0]


@pytest.fixture(autouse=True)
def _sin_sello_por_partido(monkeypatch):
    """El corte del sello por partido depende de la fecha de hoy: estas pruebas miran el job diario sin él."""
    from qf.publish import hashchain
    monkeypatch.setattr(hashchain, "LOTE_POR_PARTIDO_DESDE", None)


@pytest.fixture
def job(monkeypatch):
    estado = {"seleccion": None, "persistidos": None, "sellados": 0, "alertas": []}
    monkeypatch.setattr(daily, "settings", replace(settings, publish_picks_enabled=True))
    monkeypatch.setattr(daily, "_shadow_gate_allows_publication", lambda: (True, []))
    monkeypatch.setattr(daily, "_sharp_only_upcoming", lambda hours=36: [_solo_sharp()])
    monkeypatch.setattr(daily, "seal", lambda: estado.__setitem__(
        "sellados", estado["sellados"] + 1) or {"chain_sha256": "ab" * 32})
    monkeypatch.setattr(daily.pk, "select_daily",
                        lambda preds: estado.__setitem__("seleccion", preds) or [])
    monkeypatch.setattr(daily.pk, "persist",
                        lambda tiered: estado.__setitem__("persistidos", tiered) or 0)
    monkeypatch.setattr(daily.tg, "publish_batch", lambda *a, **k: {})
    monkeypatch.setattr(daily.tg, "alert", lambda msg: estado["alertas"].append(msg))
    return estado


def test_el_job_diario_elige_tambien_entre_partidos_solo_sharp(monkeypatch, job):
    monkeypatch.setattr(daily, "generate_predictions",
                        lambda: [{"prediction_id": "p1", "match_id": "es.laliga:m1",
                                  "teams": ("A", "B")}])
    daily.run()
    assert [p["match_id"] for p in job["seleccion"]] == ["es.laliga:m1", "es.laliga2:m9"]
    assert job["sellados"] == 1


def test_sin_predicciones_del_modelo_las_ligas_sharp_siguen_teniendo_pick(monkeypatch, job):
    monkeypatch.setattr(daily, "generate_predictions", lambda: [])
    daily.run()
    assert [p["match_id"] for p in job["seleccion"]] == ["es.laliga2:m9"]
    assert job["alertas"], "que no haya predicciones sigue avisando"


def test_con_la_publicacion_cerrada_no_se_elige_nada(monkeypatch, job):
    monkeypatch.setattr(daily, "settings", replace(settings, publish_picks_enabled=False))
    monkeypatch.setattr(daily, "generate_predictions", lambda: [])
    out = daily.run()
    assert job["seleccion"] is None and job["persistidos"] is None
    assert job["sellados"] == 0, "sin predicciones ni picks no hay nada que sellar"
    assert out["picks"] == 0


def test_el_aviso_no_revienta_sin_probabilidad_del_modelo():
    c = pk.Candidate(match_id="m9", prediction_id=None, market="h2h", selection="home",
                     line=None, model_prob=None, best_price=2.2, best_book="1xbet",
                     market_prob=0.48, raw_edge=5.6, shrunk_edge=4.0, stake_units=0.5,
                     kickoff_utc=NOW, label="h2h home")
    texto = tg.format_pick(c, ("Leganes", "Albacete"), show_stake=True)
    assert "Prob. modelo: —" in texto
