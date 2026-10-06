"""E/S de la línea de alta probabilidad, con la base de datos simulada."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from qf.config import settings
from qf.publish import alta_prob as ap
from qf.publish import alta_prob_datos as ad
from qf.publish import picks as pk

NOW = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)


def _snap(pin, otros=None, source="the_odds_api", edad=timedelta(hours=1)):
    books = {"pinnacle": dict(zip(("home", "draw", "away"), pin))}
    books.update(otros or {})
    return pk.Snapshot(source, NOW - edad, books)


def test_linea_pinnacle_prefiere_medio_gol():
    rows = [{"bookmaker": "pinnacle", "selection": s, "line": l, "price": p}
            for l, s, p in [(2.75, "over", 1.9), (2.75, "under", 1.95),
                            (3.5, "over", 2.6), (3.5, "under", 1.5)]]
    linea, p_over = ad.linea_pinnacle(rows)
    assert linea == 3.5 and 0.3 < p_over < 0.45


def test_linea_pinnacle_acepta_cuarto_si_no_hay_otra():
    rows = [{"bookmaker": "pinnacle", "selection": "over", "line": 2.75, "price": 1.9},
            {"bookmaker": "pinnacle", "selection": "under", "line": 2.75, "price": 1.95},
            {"bookmaker": "bet365", "selection": "over", "line": 2.5, "price": 1.8}]
    assert ad.linea_pinnacle(rows)[0] == 2.75
    assert ad.linea_pinnacle([]) is None


def test_decidir_favorito_claro():
    # Pinnacle 1,18 / 7,5 / 15 (Shin): local 0,826, 12 0,880, 1X 0,946 → el 1X2.
    out = ad.decidir(_snap((1.18, 7.5, 15.0)), [], None, (), set())
    assert out is not None
    c, ajuste = out
    assert (c.market, c.selection) == ("h2h", "home") and 0.80 <= c.prob <= 0.95
    assert ajuste is None


def test_decidir_partido_igualado_no_da_nada():
    assert ad.decidir(_snap((2.6, 3.2, 2.9)), [], None, (), set()) is None


def test_decidir_respeta_bloqueo():
    c, _ = ad.decidir(_snap((1.18, 7.5, 15.0)), [], None, (), {"h2h"})
    assert (c.market, c.selection) == ("double_chance", "12")


def _db(monkeypatch, partidos, snap, batch_sellado=False, rho=-0.06):
    inserts = []
    # soft_books fijas: el .env local puede redefinir SOFT_BOOKS.
    monkeypatch.setattr(ad, "settings", replace(
        settings, alta_prob_enabled=True,
        soft_books=("bet365", "william_hill", "1xbet", "betano")))
    monkeypatch.setattr(ad, "_liquidados", lambda *a, **k: [])
    monkeypatch.setattr(ad, "_rho_activo", lambda: rho)
    monkeypatch.setattr(ad, "_lote_sellado", lambda dia: batch_sellado)
    monkeypatch.setattr(ad, "_partidos", lambda now: partidos)
    monkeypatch.setattr(ad, "_totales", lambda match_id, as_of: [])
    monkeypatch.setattr(ad.pk, "_odds_api_snapshot", lambda m, now: snap)
    monkeypatch.setattr(ad.pk, "_af_snapshot", lambda m, now: None)
    monkeypatch.setattr(ad, "execute", lambda sql, params=(): inserts.append(params) or 1)
    return inserts


def test_guarda_uno_con_su_cuota_de_referencia(monkeypatch):
    snap = _snap((1.18, 7.5, 15.0), {"bet365": {"home": 1.15, "draw": 7.0, "away": 13.0},
                                     "william_hill": {"home": 1.16, "draw": 7.0, "away": 12.0}})
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}], snap)
    out = ad.select_and_persist(NOW)
    assert out["elegidos"] == 1 and len(inserts) == 1
    p = inserts[0]
    assert p[0] == "m1" and p[1] == "h2h" and p[2] == "home"
    assert p[6] == 1.16 and p[7] == "william_hill"      # mejor de SOFT_BOOKS
    assert p[8] == "the_odds_api"


def test_dry_run_no_guarda(monkeypatch):
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}],
                  _snap((1.18, 7.5, 15.0)))
    out = ad.select_and_persist(NOW, dry_run=True)
    assert inserts == [] and out["decisiones"][0]["market"] == "h2h"


def test_precio_viejo_o_tardio_no_cuenta(monkeypatch):
    viejo = _snap((1.18, 7.5, 15.0), edad=timedelta(hours=7))
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}], viejo)
    assert ad.select_and_persist(NOW)["sin_precio"] == 1 and inserts == []
    tardio = _snap((1.18, 7.5, 15.0), edad=timedelta(minutes=1))
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(minutes=10)}], tardio)
    assert ad.select_and_persist(NOW)["sin_precio"] == 1 and inserts == []


def test_lote_ya_sellado_no_elige(monkeypatch):
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}],
                  _snap((1.18, 7.5, 15.0)), batch_sellado=True)
    out = ad.select_and_persist(NOW)
    assert out["elegidos"] == 0 and inserts == []


def test_apagada_no_hace_nada(monkeypatch):
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}],
                  _snap((1.18, 7.5, 15.0)))
    monkeypatch.setattr(ad, "settings", replace(settings, alta_prob_enabled=False))
    assert ad.select_and_persist(NOW)["estado"] == "desactivada" and inserts == []


def test_liquidacion(monkeypatch):
    monkeypatch.setattr(ad, "query", lambda sql, params=(): [
        {"alta_id": "a1", "market": "double_chance", "selection": "1X", "line": None,
         "home_goals": 1, "away_goals": 1},
        {"alta_id": "a2", "market": "totals", "selection": "over", "line": 1.5,
         "home_goals": 1, "away_goals": 0}])
    escritos = []
    monkeypatch.setattr(ad, "execute", lambda sql, params=(): escritos.append(params) or 1)
    assert ad.settle_pending() == {"settled": 2}
    assert [e[1] for e in escritos] == ["win", "loss"]


def test_informe_solo_sellados_y_con_texto(monkeypatch):
    sqls = []

    def q(sql, params=()):
        sqls.append(sql)
        if "m.kickoff_utc > now()" in sql:
            return [{"match_id": "m1", "league_id": "br.serie_a", "kickoff_utc": NOW,
                     "local": "Cruzeiro", "visitante": "Sao Paulo", "market": "double_chance",
                     "selection": "1X", "line": None, "prob": 0.87, "fair_price": 1.149,
                     "ref_price": None, "ref_book": None, "batch_date": "2026-10-06",
                     "chain_sha256": "ab" * 32}]
        return []
    monkeypatch.setattr(ad, "query", q)
    monkeypatch.setattr(ad, "settings", replace(settings, alta_prob_enabled=True))
    out = ad.informe_publico()
    assert out["estado"] == "activa"
    assert out["proximos"][0]["texto"] == "Cruzeiro o empate"
    assert all("a.decided_at <= b.created_at" in s for s in sqls if "alta_prob_picks a" in s)
