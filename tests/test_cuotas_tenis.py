"""Overlay de cuotas de tenis: archivo PropLine sintético con el escritor real, sin red."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from qf.api import cuotas_tenis as ct
from qf.api import tenis_publico as tp
from qf.ingest import propline_shared as pl

UTC = timezone.utc
NOW = datetime(2026, 10, 30, 10, 5, tzinfo=UTC)
SEALED = NOW + timedelta(minutes=10)
PATH = "/v1/sports/tennis/odds"
# PropLine lista a Alcaraz como local: el jugador A del motor (Sinner) es el visitante.
A, B = "Jannik Sinner", "Carlos Alcaraz"


def o(name, price, point=None, side=None):
    return dict(name=name, price_decimal=price, point=point, side=side)


def m(key, outcomes, period=None, line_type="main"):
    return dict(key=key, period=period, team=None, line_type=line_type, outcomes=outcomes)


def evento():
    return dict(id="T1", sport_key="tennis", commence_time="2026-10-30T14:00:00Z",
                home_team=B, away_team=A, bookmakers=[
        dict(key="pinnacle", markets=[
            m("h2h", [o(A, 1.80, side="away"), o(B, 2.10, side="home")]),
            m("spreads", [o(A, 1.95, -3.5, "away"), o(B, 1.90, 3.5, "home")]),
            m("totals", [o("Over", 1.85, 22.5), o("Under", 2.00, 22.5)]),
            m("h2h", [o(A, 1.70, side="away"), o(B, 2.20, side="home")], period="s1")]),
        dict(key="bet365", markets=[
            m("h2h", [o(A, 1.83, side="away"), o(B, 2.05, side="home")]),
            m("spreads", [o(A, 1.92, -3.5, "away"), o(B, 1.93, 3.5, "home")]),
            m("total_games", [o("Over", 1.88, 22.5), o("Under", 1.95, 22.5)])]),
        # Orientación opuesta: Alcaraz -3,5 / Sinner +3,5. No es el contrato A -3,5.
        dict(key="fanduel", markets=[m("spreads", [o(B, 2.50, -3.5, "home"), o(A, 1.50, 3.5, "away")])]),
        dict(key="prizepicks", markets=[m("h2h", [o(A, 3.0, side="away"), o(B, 3.0, side="home")])]),
    ])


def archivo(root, data=None):
    c = pl.Collector(root, "k", get=lambda *a: (200, {}, json.dumps(data or [evento()]).encode()), clock=lambda: NOW)
    receipt, _ = c.capture(PATH, {"markets": "h2h"})
    c.db.close()
    return dict(receipt)


def mercado(kind, selection, line=None, set_number=None):
    return dict(contract=dict(kind=kind, selection=selection, line=line, set_number=set_number),
                probabilities=dict(win=.55, push=0.))


def pronostico(receipt, p=.6, board=True):
    f = dict(players=[A, B], winner=dict(final_winner=p), markets=[
        mercado("games_total", "over", 22.5),       # 0: presente
        mercado("games_total", "over", 20.5),       # 1: línea ausente
        mercado("games_handicap", "A", -3.5),       # 2: A visitante
        mercado("tiebreak", "yes"),                 # 3: sin cotización
        mercado("set_winner", "A", set_number=1),   # 4: periodo s1
        mercado("games_handicap", "A", 3.5),        # 5: signo
    ])
    if board:
        f["market_board"] = dict(provider="propline", event_id="T1", commence_time="2026-10-30T14:00:00Z",
                                 received_at=receipt["received_at"], snapshot_id=receipt["sha256"], rows=[])
    return f


def sellado(root, forecast, key="1"):
    folder = root / "predictions"
    folder.mkdir(exist_ok=True)
    v = dict(schema="tennis-intake-sealed-v1", event_key=key, circuit="ATP", tournament="Paris",
             rules={"surface": "Hard", "best_of": 3}, provider_start="2026-10-30T14:00:00Z",
             sealed_at=pl.stamp(SEALED), forecast=forecast)
    v["payload_sha256"] = tp._checksum(v)
    (folder / f"{key}.json").write_text(json.dumps(v), encoding="utf-8")
    return v


@pytest.fixture(autouse=True)
def limpia():
    ct.clear_cache()
    yield
    ct.clear_cache()


def test_cada_mercado_toma_la_mejor_casa_de_su_familia(tmp_path):
    r = archivo(tmp_path / "arch")
    q = ct.tennis_quotes(pronostico(r), SEALED, tmp_path / "arch")
    assert q["winner"] == dict(price=1.83, book="bet365", as_of=r["received_at"], books=2, side="A")
    assert q["games_total-0"] == dict(price=1.88, book="bet365", as_of=r["received_at"], books=2, side="over")
    assert q["games_total-1"] is None
    assert q["games_handicap-2"] == dict(price=1.95, book="pinnacle", as_of=r["received_at"], books=2, side="A")
    assert q["tiebreak-3"] is None
    assert q["set_winner-4"] == dict(price=1.70, book="pinnacle", as_of=r["received_at"], books=1, side="A")
    assert q["games_handicap-5"] == dict(price=1.50, book="fanduel", as_of=r["received_at"], books=1, side="A")


def test_favorito_b_recibe_el_precio_de_b(tmp_path):
    r = archivo(tmp_path / "arch")
    q = ct.tennis_quotes(pronostico(r, p=.4), SEALED, tmp_path / "arch")
    assert q["winner"] == dict(price=2.10, book="pinnacle", as_of=r["received_at"], books=2, side="B")


def test_seleccion_b_en_handicap_usa_la_linea_de_b(tmp_path):
    r = archivo(tmp_path / "arch")
    f = pronostico(r)
    f["markets"] = [mercado("games_handicap", "B", 3.5)]
    q = ct.tennis_quotes(f, SEALED, tmp_path / "arch")
    assert q["games_handicap-0"] == dict(price=1.93, book="bet365", as_of=r["received_at"], books=2, side="B")


def test_recibo_posterior_al_sello_o_de_otro_hash_no_se_usa(tmp_path):
    r = archivo(tmp_path / "arch")
    assert set(ct.tennis_quotes(pronostico(r), NOW - timedelta(minutes=1), tmp_path / "arch").values()) == {None}
    f = pronostico(r)
    f["market_board"]["snapshot_id"] = "0" * 64
    assert set(ct.tennis_quotes(f, SEALED, tmp_path / "arch").values()) == {None}


def test_overlay_con_claves_del_feed_publico(tmp_path):
    r = archivo(tmp_path / "arch")
    v = sellado(tmp_path, pronostico(r))
    feed = tp.projection(tmp_path, NOW + timedelta(hours=1))
    out = ct.tennis_overlay(tmp_path / "arch", feed, sealed={"1": v}, now=NOW)
    assert out["state"] == "ok" and out["source"] == "PropLine" and out["generated_at"] == NOW.isoformat()
    ids = [x["id"] for x in feed["events"][0]["markets"]]
    assert list(out["events"]["1"]) == ids
    assert out["events"]["1"]["winner"]["price"] == 1.83


def test_sin_board_o_sin_sello_todo_null_y_parcial(tmp_path):
    r = archivo(tmp_path / "arch")
    v = sellado(tmp_path, pronostico(r, board=False))
    feed = tp.projection(tmp_path, NOW + timedelta(hours=1))
    out = ct.tennis_overlay(tmp_path / "arch", feed, sealed={"1": v}, now=NOW)
    assert out["state"] == "partial" and set(out["events"]["1"].values()) == {None}
    out = ct.tennis_overlay(tmp_path / "arch", feed, sealed={}, now=NOW)
    assert out["state"] == "partial" and set(out["events"]["1"].values()) == {None}


def test_sello_que_no_coincide_con_el_feed_no_se_usa(tmp_path):
    r = archivo(tmp_path / "arch")
    v = sellado(tmp_path, pronostico(r))
    feed = tp.projection(tmp_path, NOW + timedelta(hours=1))
    otro = dict(v, payload_sha256="f" * 64)
    out = ct.tennis_overlay(tmp_path / "arch", feed, sealed={"1": otro}, now=NOW)
    assert out["state"] == "partial" and set(out["events"]["1"].values()) == {None}


def test_recibo_corrupto_todo_null_y_parcial(tmp_path):
    r = archivo(tmp_path / "arch")
    v = sellado(tmp_path, pronostico(r))
    (tmp_path / "arch" / r["body_path"]).write_bytes(b"no es gzip")
    feed = tp.projection(tmp_path, NOW + timedelta(hours=1))
    out = ct.tennis_overlay(tmp_path / "arch", feed, sealed={"1": v}, now=NOW)
    assert out["state"] == "partial" and set(out["events"]["1"].values()) == {None}


def test_archivo_ausente_no_disponible(tmp_path):
    r = archivo(tmp_path / "arch")
    v = sellado(tmp_path, pronostico(r))
    feed = tp.projection(tmp_path, NOW + timedelta(hours=1))
    out = ct.tennis_overlay(tmp_path / "nada", feed, sealed={"1": v}, now=NOW)
    assert out["state"] == "unavailable" and out["events"] == {}


def test_el_recibo_se_lee_una_sola_vez(tmp_path, monkeypatch):
    r = archivo(tmp_path / "arch")
    lecturas = []
    real = pl.load_object
    monkeypatch.setattr(pl, "load_object", lambda root, rec: lecturas.append(rec["sha256"]) or real(root, rec))
    f = pronostico(r)
    a = ct.tennis_quotes(f, SEALED, tmp_path / "arch")
    b = ct.tennis_quotes(f, SEALED, tmp_path / "arch")
    assert a == b and a["winner"] is not None and lecturas == [r["sha256"]]


def test_datos_malos_no_lanzan(tmp_path):
    r = archivo(tmp_path / "arch")
    for f in ({}, {"players": [A]}, dict(pronostico(r), market_board="x")):
        assert all(v is None for v in ct.tennis_quotes(f, SEALED, tmp_path / "arch").values())
    q = ct.tennis_quotes(dict(pronostico(r), markets=[None, 3]), SEALED, tmp_path / "arch")
    assert list(q) == ["winner"] and q["winner"]["price"] == 1.83
    assert ct.tennis_overlay(tmp_path / "arch", {"events": "x"}, sealed={}, now=NOW)["state"] == "partial"
