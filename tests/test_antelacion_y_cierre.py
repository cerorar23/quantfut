"""
Mejoras de la auditoría del 3-oct-2026 (decisión del usuario):

1. Ninguna oferta ni pick se DECIDE a menos de MIN_LEAD del inicio. La
   guarda solo miraba la hora del precio: con un precio de T-55 y la
   decisión a T-5, la oferta contaba aunque nadie pudiera apostarla y aunque
   el cierre se capturase antes de decidirla. La publicación real
   (`find_candidates`) no tenía ninguna guarda. Una sola constante para las
   dos: la puerta certifica "lo que se habría publicado".
2. El cierre tiene una segunda oportunidad. Su ventana (3-12 min) caía en una
   sola pasada del cron */10; una pasada de rescate desfasada 5 min y SOLO
   para `close` deja dos intentos sin mover la vara (sigue siendo el último
   precio a 3-12 min) y sin gastar créditos si el primero funcionó.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from qf.ingest import odds_worker
from qf.publish import picks as pk
from qf.publish import shadow_sharp as ss

T0 = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)
SNAP = pk.Snapshot("the_odds_api", T0 - timedelta(minutes=55), {
    "pinnacle": {"home": 2.0, "draw": 3.5, "away": 4.0},
    "coolbet": {"home": 2.4, "draw": 3.4, "away": 3.6},
    "unibet_se": {"home": 2.0, "draw": 3.4, "away": 3.9},
    "leovegas_se": {"home": 2.0, "draw": 3.4, "away": 3.9}})


def test_una_sola_constante_para_sombra_y_publicacion():
    assert ss.MIN_LEAD is pk.MIN_LEAD


def _sombra(monkeypatch, ko):
    insertadas = []
    monkeypatch.setattr(ss, "query", lambda *a, **k: [
        {"match_id": "m1", "league_id": "us.mls", "kickoff_utc": ko}])
    monkeypatch.setattr(ss.pk, "_af_snapshot", lambda *a: None)
    monkeypatch.setattr(ss.pk, "persistencias", lambda: dict(pk.PERSISTENCE))
    monkeypatch.setattr(ss.pk, "_odds_api_snapshot", lambda *a: SNAP)
    monkeypatch.setattr(ss, "executemany",
                        lambda sql, rows: insertadas.extend(rows) or len(rows))
    return ss.capture(T0), insertadas


def test_sombra_no_decide_a_menos_de_15_min_aunque_el_precio_sea_viejo(monkeypatch):
    r, insertadas = _sombra(monkeypatch, T0 + timedelta(minutes=5))
    assert r["snapshots"] == 0 and insertadas == []


def test_sombra_si_decide_con_tiempo(monkeypatch):
    r, insertadas = _sombra(monkeypatch, T0 + timedelta(minutes=20))
    assert r["snapshots"] == 1 and insertadas


def _publicacion(monkeypatch, ko, as_of=None):
    snap = SNAP if as_of is None else pk.Snapshot(SNAP.source, as_of, SNAP.books)
    monkeypatch.setattr(pk, "_af_snapshot", lambda *a: None)
    monkeypatch.setattr(pk, "_odds_api_snapshot", lambda *a: snap)
    monkeypatch.setattr(pk, "persistencias", lambda: dict(pk.PERSISTENCE))
    return pk.find_candidates({"match_id": "m1", "kickoff_utc": ko,
                               "league_id": "us.mls"}, T0)


def test_publicacion_no_decide_a_menos_de_15_min(monkeypatch):
    assert _publicacion(monkeypatch, T0 + timedelta(minutes=5)) == []


def test_publicacion_no_usa_el_snapshot_de_cierre(monkeypatch):
    ko = T0 + timedelta(minutes=20)
    assert _publicacion(monkeypatch, ko, as_of=ko - timedelta(minutes=8)) == []


def test_publicacion_con_tiempo_si_da_candidatos(monkeypatch):
    assert _publicacion(monkeypatch, T0 + timedelta(minutes=20))


def _filas(mins_por_partido):
    return [{"match_id": m, "odds_api_key": "sport", "mins": mins,
             "lineup_sides": 0, "lineup_as_of": None}
            for m, mins in mins_por_partido.items()]


def test_la_pasada_de_rescate_solo_mira_el_cierre(monkeypatch):
    filas = _filas({"cierre": 6, "t1": 55, "t24": 1400})
    monkeypatch.setattr(odds_worker, "query",
                        lambda sql: [] if "odds_capture_log" in sql else filas)
    assert odds_worker._pending_windows(T0, solo=("close",)) == {
        "sport": [("cierre", "close")]}
    normal = odds_worker._pending_windows(T0)
    assert sorted(t for _, t in normal["sport"]) == ["close", "t1", "t24"]


def test_el_rescate_no_repite_un_cierre_ya_capturado(monkeypatch):
    filas = _filas({"cierre": 6})
    monkeypatch.setattr(odds_worker, "query", lambda sql: (
        [{"match_id": "cierre", "window_tag": "close"}]
        if "odds_capture_log" in sql else filas))
    assert odds_worker._pending_windows(T0, solo=("close",)) == {}


def test_el_cron_tiene_la_pasada_de_rescate_desfasada():
    crontab = (Path(__file__).resolve().parents[1] / "scripts" / "crontab").read_text(
        encoding="utf-8")
    assert "*/10 * * * * cd /app && python -m qf.ingest.odds_worker >>" in crontab
    assert "5-59/10 * * * * cd /app && python -m qf.ingest.odds_worker --solo-cierre" in crontab
