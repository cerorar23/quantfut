from datetime import datetime, timedelta, timezone

from qf.ingest.cuotas_referencia import Quote, best_quote

SEALED = datetime(2026, 10, 30, 18, 0, tzinfo=timezone.utc)
RECEIVED = SEALED - timedelta(minutes=5)


def row(book, name, price, point=None, side=None, **extra):
    base = dict(bookmaker=book, name=name, side=side, point=point, price_decimal=price,
                period=None, team=None, flags=[], dfs_odds_type=None, payout_multiplier=None)
    return {**base, **extra}


def pair(book, over, under, point=24.5):
    return [row(book, "Over", over, point), row(book, "Under", under, point)]


def best(rows, **kw):
    args = dict(line=24.5, side="over", sealed_at=SEALED, received_at=RECEIVED)
    return best_quote(rows, **{**args, **kw})


def test_best_quote_maximo_entre_casas():
    rows = pair("a", 1.90, 1.90) + pair("b", 2.05, 1.80) + pair("c", 1.95, 1.85)
    assert best(rows) == Quote(price=2.05, book="b", as_of=RECEIVED.isoformat(), books=3)


def test_best_quote_lado_under():
    rows = pair("a", 1.90, 1.70) + pair("b", 2.05, 1.80)
    q = best(rows, side="under")
    assert (q.price, q.book) == (1.80, "b")


def test_best_quote_empate_casa_alfabetica_menor():
    rows = pair("zeta", 2.0, 1.8) + pair("alfa", 2.0, 1.8)
    assert best(rows).book == "alfa"


def test_best_quote_excluye_dfs_intercambio_en_juego_y_periodo():
    rows = (pair("prizepicks", 3.0, 3.0) + pair("kalshi", 3.0, 3.0) + pair("ok", 1.9, 1.9)
            + [row("live", "Over", 4.0, 24.5, flags=["in_play_or_started"]), row("live", "Under", 4.0, 24.5)]
            + [row("q1", "Over", 4.0, 24.5, period="q1"), row("q1", "Under", 4.0, 24.5, period="q1")]
            + [row("pick", "Over", 4.0, 24.5, dfs_odds_type="standard"), row("pick", "Under", 4.0, 24.5)]
            + [row("mult", "Over", 4.0, 24.5, payout_multiplier=1.0), row("mult", "Under", 4.0, 24.5)])
    q = best(rows)
    assert (q.book, q.price, q.books) == ("ok", 1.9, 1)


def test_best_quote_casa_con_un_solo_lado_excluida():
    rows = [row("solo", "Over", 5.0, 24.5)] + pair("ok", 1.9, 1.9)
    q = best(rows)
    assert (q.book, q.books) == ("ok", 1)


def test_best_quote_precio_invalido_excluido():
    rows = (pair("uno", 1.0, 1.9) + pair("nan", float("nan"), 1.9) + pair("inf", float("inf"), 1.9)
            + pair("neg", 0.5, 1.9) + pair("ok", 1.9, 1.9))
    q = best(rows)
    assert (q.book, q.price, q.books) == ("ok", 1.9, 1)


def test_best_quote_otra_linea_es_none():
    assert best(pair("a", 1.9, 1.9, point=25.5)) is None


def test_best_quote_recibo_posterior_al_sello():
    rows = pair("a", 1.9, 1.9)
    assert best(rows, received_at=SEALED + timedelta(seconds=1)) is None
    assert best(rows, received_at=SEALED) is not None


def test_best_quote_vacio():
    assert best([]) is None


def test_best_quote_ganador_home_away_sin_linea():
    rows = [row("a", "X", 1.5, side="home"), row("a", "Y", 2.6, side="away"),
            row("b", "X", 1.6, side="home"), row("b", "Y", 2.5, side="away")]
    q = best(rows, line=None, side="away")
    assert (q.price, q.book) == (2.6, "a")


def test_best_quote_handicap_lado_opuesto_con_linea_inversa():
    rows = [row("a", "X", 1.9, -3.5, side="home"), row("a", "Y", 1.9, 3.5, side="away"),
            row("b", "X", 2.0, -3.5, side="home")]
    q = best(rows, line=-3.5, side="home")
    assert (q.book, q.books) == ("a", 1)


def test_best_quote_sides_a_b_y_yes_no():
    rows = [row("a", "P", 1.4, side="A"), row("a", "Q", 3.0, side="B")]
    assert best(rows, line=None, side="B").price == 3.0
    yn = [row("a", "Yes", 1.8, 0.5), row("a", "No", 2.0, 0.5)]
    assert best(yn, line=0.5, side="no").price == 2.0
