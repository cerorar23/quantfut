"""
Latencia de las casas blandas (idea 3, db/038).

Lo que fijan: se guarda cuándo cambió cada precio, las ráfagas respetan su
tope de créditos y no tocan `odds_snapshots`, y la lectura reconstruye bien
la duración de una oferta y la reacción de una casa.
"""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from qf.eval import latencia as lt
from qf.ingest import odds_worker, rafagas

T0 = pd.Timestamp("2026-10-10 12:00", tz="UTC")
RAIZ = Path(__file__).resolve().parents[1]


def _ev():
    return {"home_team": "A", "away_team": "B", "bookmakers": [
        {"key": "betsson", "last_update": "2026-10-10T11:00:00Z", "markets": [
            {"key": "h2h", "last_update": "2026-10-10T10:58:00Z", "outcomes": [
                {"name": "A", "price": 2.1}, {"name": "Draw", "price": 3.4},
                {"name": "B", "price": 3.6}]}]}]}


def test_el_worker_guarda_cuando_cambio_cada_precio():
    now = datetime(2026, 10, 10, 11, 5, tzinfo=timezone.utc)
    filas = odds_worker._parse_event(_ev(), "m1", "t1", now, now)
    assert len(filas) == 3
    assert {f[-1] for f in filas} == {datetime(2026, 10, 10, 10, 58, tzinfo=timezone.utc)}


def test_sin_last_update_queda_vacio():
    assert odds_worker.last_update({}, {}) is None
    assert odds_worker.last_update({}, {"last_update": "roto"}) is None


def test_las_rafagas_fechan_cada_fila_con_su_cambio():
    now = datetime(2026, 10, 10, 11, 5, tzinfo=timezone.utc)
    filas = rafagas.filas(_ev(), "m1", now)
    assert sorted(f[2] for f in filas) == ["away", "draw", "home"]
    assert all(f[4].minute == 58 and f[5] == now for f in filas)


def test_las_rafagas_se_detienen_en_el_tope(monkeypatch):
    llamadas = []
    monkeypatch.setattr(rafagas, "_objetivos", lambda now: {"x": ["m1"], "y": ["m2"]})
    monkeypatch.setattr(rafagas, "creditos_del_mes", lambda now: 2999)
    monkeypatch.setattr(rafagas, "_fetch", lambda k: llamadas.append(k) or ([], 1))
    monkeypatch.setattr(rafagas, "execute", lambda *a, **k: None)
    monkeypatch.setattr(rafagas, "executemany", lambda *a, **k: 0)
    monkeypatch.setattr(rafagas, "match_meta", lambda ids: {})
    r = rafagas.run_once(datetime(2026, 10, 10, tzinfo=timezone.utc))
    assert llamadas == ["x"] and r["creditos_mes"] == 3000


def test_coste_de_diez_casas_es_un_credito():
    assert len(rafagas.settings.rafagas_casas) <= 10
    assert rafagas.coste_previsto() == 1


def test_las_rafagas_nunca_escriben_en_odds_snapshots():
    fuente = (RAIZ / "src/qf/ingest/rafagas.py").read_text(encoding="utf-8")
    cadenas = [n.value for n in ast.walk(ast.parse(fuente))
               if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any("odds_snapshots" in c and "INSERT" in c.upper() for c in cadenas)
    assert "odds_rafagas" in fuente


def test_crontab_lanza_las_rafagas_cada_5_min():
    crontab = (RAIZ / "scripts/crontab").read_text(encoding="utf-8")
    assert "*/5 * * * * cd /app && python -m qf.ingest.rafagas >>" in crontab


def _filas(pin: list[tuple], blanda: list[tuple]) -> pd.DataFrame:
    """pin: (minuto, local, empate, visitante); blanda: (minuto, cuota local)."""
    out = []
    for m, h, d, a in pin:
        for sel, p in zip(lt.SEL, (h, d, a)):
            out.append(("pinnacle", sel, p, T0 + pd.Timedelta(minutes=m)))
    for m, p in blanda:
        out.append(("betsson", "home", p, T0 + pd.Timedelta(minutes=m)))
    return pd.DataFrame(out, columns=["bookmaker", "selection", "price", "book_updated_at"])


def test_oferta_que_dura_hasta_que_la_casa_reacciona():
    # Pinnacle acorta al local en el minuto 30; Betsson tarda 45 min en seguirle.
    rows = _filas(pin=[(-10, 2.00, 3.60, 4.00), (30, 1.80, 3.80, 4.80)],
                  blanda=[(-10, 2.00), (75, 1.80)])
    of = lt.ofertas(rows, T0, T0 + pd.Timedelta(hours=3))
    assert len(of) == 1
    o = of.iloc[0]
    assert o["inicio"] == T0 + pd.Timedelta(minutes=30) and o["minutos"] == 45
    assert not o["censurada"]
    re = lt.reacciones(rows, T0, T0 + pd.Timedelta(hours=3))
    assert re["minutos"].tolist() == [45.0] and not re["censurada"].any()


def test_oferta_abierta_al_final_queda_censurada():
    rows = _filas(pin=[(-10, 2.00, 3.60, 4.00), (30, 1.80, 3.80, 4.80)],
                  blanda=[(-10, 2.00)])
    of = lt.ofertas(rows, T0, T0 + pd.Timedelta(minutes=50))
    assert bool(of.iloc[0]["censurada"]) and of.iloc[0]["minutos"] == 20


def test_el_resumen_excluye_censuradas_cortas_y_espera_muestra():
    of = pd.DataFrame({"bookmaker": ["a", "a", "b"], "minutos": [90.0, 20.0, 10.0],
                       "censurada": [True, True, False]})
    r = lt.resumen(of, pd.DataFrame(columns=["bookmaker", "minutos", "censurada"]))
    assert r["ofertas_clasificables"] == 2 and r["censuradas_cortas_excluidas"] == 1
    assert r["pct_largas"] == 50.0
    assert r["lectura"].startswith("muestra insuficiente")
