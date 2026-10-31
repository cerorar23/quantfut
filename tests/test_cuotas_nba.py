"""Overlay de cuotas de NBA: archivo PropLine sintético con el escritor real, sin red."""
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from qf.api import cuotas_nba as cn
from qf.ingest import propline_shared as pl

UTC = timezone.utc
NOW = datetime(2026, 10, 31, 1, 5, tzinfo=UTC)
SEALED = NOW + timedelta(minutes=10)
PATH = "/v1/sports/basketball_nba/odds"
LAL, GSW, BOS, NYK = 1610612747, 1610612744, 1610612738, 1610612752
LEBRON, CURRY, REAVES = 2544, 201939, 1630559


def o(name, price, point=None, side=None, player=None, **extra):
    return dict(name=name, price_decimal=price, point=point, side=side, player_id=player, **extra)


def m(key, outcomes, team=None, line_type="main", period=None):
    return dict(key=key, period=period, team=team, line_type=line_type, outcomes=outcomes)


def ou(point, over, under, player=None, **extra):
    return [o("Over", over, point, player=player, **extra), o("Under", under, point, player=player, **extra)]


def ev_lakers(bump=0.0):
    p = lambda x: round(x + bump, 2)
    return dict(id="E1", sport_key="basketball_nba", commence_time="2026-10-31T02:40:00Z",
                home_team="Los Angeles Lakers", away_team="Golden State Warriors",
                home_team_id=f"nba:{LAL}", away_team_id=f"nba:{GSW}", bookmakers=[
        dict(key="pinnacle", markets=[
            m("h2h", [o("Los Angeles Lakers", p(1.60), side="home"), o("Golden State Warriors", 2.40, side="away")]),
            m("totals", ou(221.5, 1.91, 1.91)),
            # Ganador alternativo: no es el mercado publicado.
            m("h2h", [o("Los Angeles Lakers", 9.0, side="home"), o("Golden State Warriors", 9.0, side="away")],
              line_type="alternate"),
            m("player_points", ou(24.5, 1.87, 1.95, f"nba:{LEBRON}") + ou(28.5, 1.80, 2.00, f"nba:{CURRY}")),
        ]),
        dict(key="bet365", markets=[
            m("h2h", [o("Los Angeles Lakers", 1.62, side="home"), o("Golden State Warriors", 2.35, side="away")]),
            m("totals", ou(221.5, 1.90, 1.90)),
            m("totals", ou(112.5, 1.85, 1.95), team="Los Angeles Lakers"),
            m("totals", ou(108.5, 1.88, 1.92), team="Golden State Warriors"),
            m("player_points", ou(24.5, 1.90, 1.90, f"nba:{LEBRON}")),
            m("player_rebounds", ou(6.5, 1.85, 1.95, f"nba:{CURRY}")),
            # Jugador sin identificador NBA: nunca se une por nombre.
            m("player_assists", ou(4.5, 1.85, 1.95, None, description="Austin Reaves")),
        ]),
        # Escalera alternativa del total: 220,5 solo aquí.
        dict(key="fanduel", markets=[m("totals", ou(220.5, 1.83, 1.99), line_type="alternate")]),
        # Robos solo en casas DFS (lista o campos DFS).
        dict(key="prizepicks", markets=[m("player_steals", ou(1.5, 1.80, 1.80, f"nba:{LEBRON}"))]),
        dict(key="betr_picks", markets=[m("player_steals", ou(1.5, 1.80, 1.80, f"nba:{LEBRON}", dfs_odds_type="standard"))]),
    ])


def ev_celtics():
    return dict(id="E2", sport_key="basketball_nba", commence_time="2026-10-31T00:10:00Z",
                home_team="Boston Celtics", away_team="New York Knicks",
                home_team_id=f"nba:{BOS}", away_team_id=f"nba:{NYK}", bookmakers=[
        dict(key="pinnacle", markets=[m("h2h", [o("Boston Celtics", 1.50, side="home"),
                                                 o("New York Knicks", 2.70, side="away")])])])


def archivo(root, clock=NOW, events=None, lotes=None):
    """Una observación horaria en dos lotes (como el recolector) y su identidad sellada, como prop_lines.lines()."""
    events = events or [ev_lakers()]
    juego = [dict(e, bookmakers=[dict(b, markets=[x for x in b["markets"] if x["key"] in ("h2h", "totals")])
                                 for b in e["bookmakers"]]) for e in events]
    jugadores = [dict(e, bookmakers=[dict(b, markets=[x for x in b["markets"] if x["key"].startswith("player_")])
                                     for b in e["bookmakers"]]) for e in events]
    cuerpos = {"h2h,totals": juego, "player_points": jugadores}
    c = pl.Collector(root, "k", get=lambda path, params, key: (200, {}, json.dumps(cuerpos[params["markets"]]).encode()),
                     clock=lambda: clock)
    for markets in lotes or cuerpos:
        c.capture(PATH, {"markets": markets})
    c.db.close()
    _, receipt = pl.newest(root, PATH, clock + timedelta(minutes=1))
    return dict(state="archivo_aplicado", received_at_utc=receipt["received_at"], slot=receipt["slot"],
                sha256=receipt["sha256"], component_requests=receipt["component_receipts"], events_matched=1)


def fila(market, player_id, line, team_id=None, sealed=SEALED, gid="0022600100"):
    return dict(event_id=gid, nba_game_id=gid, market=market, player_id=player_id, line=line, team_id=team_id,
                sealed_at_utc=pl.stamp(sealed), probability_over=.6, probability_under=.4, actionable=False)


def cohorte(prop, sealed=SEALED, created=None, forecasts=None):
    game = dict(event_id="0022600100", nba_game_id="0022600100", tipoff_utc="2026-10-31T02:30:00+00:00",
                home_team="Los Angeles Lakers", away_team="Golden State Warriors",
                home_nba_team_id=LAL, away_nba_team_id=GSW)
    rows = forecasts if forecasts is not None else [
        fila("winner", "winner", .5, LAL, sealed),
        fila("team_points", LAL, 112.5, LAL, sealed),
        fila("team_points", GSW, 108.5, GSW, sealed),
        fila("game_total", "total", 220.5, None, sealed),
        fila("player_points", LEBRON, 24.5, LAL, sealed),
        fila("player_rebounds", CURRY, 5.5, GSW, sealed),     # umbral estadístico: el recibo solo tiene 6,5
        fila("player_steals", LEBRON, 1.5, LAL, sealed),      # solo DFS
        fila("player_assists", REAVES, 4.5, LAL, sealed),     # sin nba:<id> en el recibo
    ]
    return dict(version="nba-multimarket-live-1.3", cohort="20261030-a", created_at_utc=pl.stamp(created or sealed),
                games=[game], forecasts=rows, prop_lines=prop, actionable=False)


def cohorte_celtics(prop):
    game = dict(event_id="0022600099", nba_game_id="0022600099", tipoff_utc="2026-10-31T00:00:00+00:00",
                home_team="Boston Celtics", away_team="New York Knicks", home_nba_team_id=BOS, away_nba_team_id=NYK)
    return dict(cohort="20261030-b", created_at_utc=pl.stamp(SEALED), games=[game], prop_lines=prop,
                forecasts=[fila("winner", "winner", .5, BOS, gid="0022600099")])


def q(price, book, prop, side, books):
    return dict(price=price, book=book, as_of=prop["received_at_utc"], books=books, side=side)


@pytest.fixture(autouse=True)
def limpia():
    cn.clear_cache()
    yield
    cn.clear_cache()


def test_ganador_con_los_dos_lados(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_quotes(cohorte(prop), tmp_path / "arch")["0022600100"]
    assert out["winner||"] == dict(home=q(1.62, "bet365", prop, "home", 2), away=q(2.40, "pinnacle", prop, "away", 2))


def test_puntos_de_jugador_con_linea_propline(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_quotes(cohorte(prop), tmp_path / "arch")["0022600100"]
    assert out[f"player_points|{LEBRON}|24.5"] == dict(over=q(1.90, "bet365", prop, "over", 2),
                                                       under=q(1.95, "pinnacle", prop, "under", 2))


def test_total_alternativo_exacto_y_puntos_por_equipo(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_quotes(cohorte(prop), tmp_path / "arch")["0022600100"]
    assert out["game_total||220.5"] == dict(over=q(1.83, "fanduel", prop, "over", 1), under=q(1.99, "fanduel", prop, "under", 1))
    assert out[f"team_points|{LAL}|112.5"]["over"] == q(1.85, "bet365", prop, "over", 1)
    assert out[f"team_points|{GSW}|108.5"]["under"] == q(1.92, "bet365", prop, "under", 1)


def test_sin_la_linea_publicada_ni_la_mas_cercana(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_quotes(cohorte(prop), tmp_path / "arch")["0022600100"]
    assert out[f"player_rebounds|{CURRY}|5.5"] == dict(over=None, under=None)
    rows = [fila("game_total", "total", 221.0, None)]  # hay 220,5 y 221,5: ninguna vale
    out = cn.nba_quotes(cohorte(prop, forecasts=rows), tmp_path / "arch")["0022600100"]
    assert out["game_total||221"] == dict(over=None, under=None)  # entera: "221", no "221.0"


def test_dfs_y_jugador_sin_id_nba_sin_precio(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_quotes(cohorte(prop), tmp_path / "arch")["0022600100"]
    assert out[f"player_steals|{LEBRON}|1.5"] == dict(over=None, under=None)
    assert out[f"player_assists|{REAVES}|4.5"] == dict(over=None, under=None)


def test_overlay_ok(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_overlay(tmp_path / "arch", [cohorte(prop)], now=NOW)
    assert out["state"] == "ok" and out["source"] == "PropLine" and out["generated_at"] == NOW.isoformat()
    assert out["events"]["0022600100"]["quotes"]["winner||"]["home"]["price"] == 1.62


def test_cohorte_sin_archivo_reciente_todo_null_y_parcial(tmp_path):
    archivo(tmp_path / "arch")
    out = cn.nba_overlay(tmp_path / "arch", [cohorte(dict(state="sin_archivo_reciente"))], now=NOW)
    assert out["state"] == "partial"
    filas = out["events"]["0022600100"]["quotes"]
    assert len(filas) == 8 and all(v is None for lados in filas.values() for v in lados.values())


def test_el_recibo_se_lee_una_sola_vez(tmp_path, monkeypatch):
    prop = archivo(tmp_path / "arch")
    lecturas = []
    real = pl.load_object
    monkeypatch.setattr(pl, "load_object", lambda root, rec: lecturas.append(rec["request_id"]) or real(root, rec))
    a = cn.nba_overlay(tmp_path / "arch", [cohorte(prop)], now=NOW)
    b = cn.nba_overlay(tmp_path / "arch", [cohorte(prop), cohorte(prop)], now=NOW)
    assert a == b and a["state"] == "ok"
    assert sorted(lecturas) == sorted(prop["component_requests"])


def test_recalculo_posterior_sustituye_al_anterior(tmp_path):
    prop = archivo(tmp_path / "arch")
    original = cohorte(prop)
    nueva = dict(original, recalculated_at_utc=pl.stamp(SEALED + timedelta(minutes=20)),
                 forecasts=[fila("player_points", LEBRON, 24.5, LAL, SEALED + timedelta(minutes=20))])
    for orden in ([original, nueva], [nueva, original]):
        out = cn.nba_overlay(tmp_path / "arch", orden, now=NOW)
        assert list(out["events"]["0022600100"]["quotes"]) == [f"player_points|{LEBRON}|24.5"]


def test_recibo_posterior_al_sello_se_rechaza(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_quotes(cohorte(prop, sealed=NOW - timedelta(minutes=1)), tmp_path / "arch")["0022600100"]
    assert all(v is None for lados in out.values() for v in lados.values())


def test_identidad_distinta_del_sello_no_se_usa(tmp_path):
    prop = archivo(tmp_path / "arch")
    for cambio in (dict(sha256="0" * 64), dict(component_requests=prop["component_requests"][:1]),
                   dict(slot="2026-10-31T00:00:00+00:00")):
        out = cn.nba_overlay(tmp_path / "arch", [cohorte(dict(prop, **cambio))], now=NOW)
        assert out["state"] == "partial"
        assert all(v is None for lados in out["events"]["0022600100"]["quotes"].values() for v in lados.values())


def test_recibo_corrupto_solo_afecta_a_su_cohorte(tmp_path):
    root = tmp_path / "arch"
    lakers = archivo(root)
    celtics = archivo(root, clock=NOW - timedelta(hours=2), events=[ev_celtics()])
    db = sqlite3.connect(root / "index.sqlite")
    rutas = [r for (r,) in db.execute("SELECT body_path FROM receipts WHERE request_id IN (?,?)",
                                      lakers["component_requests"])]
    db.close()
    for ruta in rutas:
        (root / ruta).write_bytes(b"no es gzip")
    out = cn.nba_overlay(root, [cohorte(lakers), cohorte_celtics(celtics)], now=NOW)
    assert out["state"] == "partial"
    assert all(v is None for lados in out["events"]["0022600100"]["quotes"].values() for v in lados.values())
    assert out["events"]["0022600099"]["quotes"]["winner||"]["away"] == q(2.70, "pinnacle", celtics, "away", 1)


def test_archivo_ausente_no_disponible(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_overlay(tmp_path / "nada", [cohorte(prop)], now=NOW)
    assert out["state"] == "unavailable" and out["events"] == {}


def test_datos_malos_no_lanzan(tmp_path):
    prop = archivo(tmp_path / "arch")
    out = cn.nba_overlay(tmp_path / "arch", [None, {}, {"games": "x"}, cohorte(prop)], now=NOW)
    assert out["state"] == "partial" and out["events"]["0022600100"]["quotes"]["winner||"]["home"]["price"] == 1.62
    c = cohorte(prop)
    c["forecasts"] = [None, dict(market="player_points"), *c["forecasts"]]
    assert cn.nba_quotes(c, tmp_path / "arch")["0022600100"]["winner||"]["home"]["price"] == 1.62
    naive = cohorte(prop)
    for f in naive["forecasts"]:
        f["sealed_at_utc"] = SEALED.replace(tzinfo=None).isoformat()
    out = cn.nba_quotes(naive, tmp_path / "arch")["0022600100"]
    assert all(v is None for lados in out.values() for v in lados.values())


def test_sqlite_bloqueado_no_se_cachea(tmp_path, monkeypatch):
    prop = archivo(tmp_path / "arch")
    real, fallos = pl.newest, [sqlite3.OperationalError("database is locked")]

    def newest(*a, **k):
        if fallos:
            raise fallos.pop()
        return real(*a, **k)
    monkeypatch.setattr(pl, "newest", newest)
    assert cn.nba_overlay(tmp_path / "arch", [cohorte(prop)], now=NOW)["state"] == "partial"
    assert cn.nba_overlay(tmp_path / "arch", [cohorte(prop)], now=NOW)["state"] == "ok"


def test_partido_sin_evento_propline_queda_parcial(tmp_path):
    prop = archivo(tmp_path / "arch")
    c = cohorte(prop)
    c["games"][0]["tipoff_utc"] = "2026-10-31T07:00:00+00:00"  # más de 3 h del commence_time
    out = cn.nba_overlay(tmp_path / "arch", [c], now=NOW)
    assert out["state"] == "partial"
    assert all(v is None for lados in out["events"]["0022600100"]["quotes"].values() for v in lados.values())


def _escribe(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value).encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_cargador_lee_cohortes_y_su_ultimo_recalculo(tmp_path):
    prop = archivo(tmp_path / "arch")
    raiz = tmp_path / "cohorts"
    bundle = {k: v for k, v in cohorte(prop).items() if k != "cohort"}
    sha = _escribe(raiz / "20261030-a" / "bundle.json", bundle)
    _escribe(raiz / "20261030-a" / "bundle.seal.json", dict(sha256=sha))
    nuevas = [fila("player_points", LEBRON, 24.5, LAL, SEALED + timedelta(minutes=20))]
    for tag, rows in (("20261031T000000Z", bundle["forecasts"]), ("20261031T010000Z", nuevas)):
        rev = dict(format="nba-probability-revision-1", original_bundle_sha256=sha, forecasts=rows,
                   recalculated_at_utc=pl.stamp(SEALED + timedelta(minutes=20)))
        _escribe(raiz / "20261030-a" / "updates" / tag / "revision.seal.json",
                 dict(sha256=_escribe(raiz / "20261030-a" / "updates" / tag / "revision.json", rev)))
    _escribe(raiz / "20261030-a" / "updates" / "20261031T020000Z.partial" / "revision.seal.json", dict(sha256="x"))
    # Cohorte alterada: no se usa, y el overlay lo marca como parcial.
    _escribe(raiz / "20261030-z" / "bundle.json", bundle)
    _escribe(raiz / "20261030-z" / "bundle.seal.json", dict(sha256="0" * 64))
    cohorts = cn.load_cohorts(raiz, now=NOW)
    assert [c.get("cohort") for c in cohorts] == ["20261030-a", "20261030-z"]
    assert cohorts[0]["forecasts"] == nuevas and cohorts[0]["prop_lines"] == prop
    assert "games" not in cohorts[1]
    out = cn.nba_overlay(tmp_path / "arch", cohorts, now=NOW)
    assert out["state"] == "partial" and list(out["events"]["0022600100"]["quotes"]) == [f"player_points|{LEBRON}|24.5"]
    # Fuera de la ventana de 3 días se omite; la alterada sigue marcada.
    assert [c["cohort"] for c in cn.load_cohorts(raiz, now=NOW + timedelta(days=4))] == ["20261030-z"]
    assert len(cn.load_cohorts(raiz, dias=None, now=NOW + timedelta(days=4))) == 2
    assert cn.load_cohorts(None) == [] and cn.load_cohorts(tmp_path / "no-existe") == []


def test_ajuste_de_carpeta_de_cohortes(monkeypatch):
    from qf.config import Settings
    monkeypatch.delenv("NBA_COHORTS_DIR", raising=False)
    assert Settings().nba_cohorts_dir is None


def test_mas_cohortes_que_recibos_en_cache_no_relee(tmp_path, monkeypatch):
    root = tmp_path / "arch"
    cohorts = []
    for i in range(cn.MAX_RECEIPTS + 3):
        prop = archivo(root, clock=NOW - timedelta(hours=i), events=[ev_lakers(bump=i / 100)])
        cohorts.append(dict(cohorte(prop, created=SEALED - timedelta(hours=i)), cohort=f"c{i}"))
    primera = cn.nba_overlay(root, cohorts, now=NOW)
    cuotas = [cn.nba_quotes(c, root) for c in cohorts]  # cada recibo leído una vez; solo 4 índices en caché
    lecturas = []
    real = pl.load_object
    monkeypatch.setattr(pl, "load_object", lambda r, rec: lecturas.append(rec["request_id"]) or real(r, rec))
    for _ in range(2):
        assert cn.nba_overlay(root, cohorts, now=NOW) == primera
        assert [cn.nba_quotes(c, root) for c in cohorts] == cuotas
    assert lecturas == [] and primera["state"] == "ok" and primera["events"]["0022600100"]["cohort"] == "c0"


def test_copia_parcial_del_archivo_no_se_cachea(tmp_path):
    prop = archivo(tmp_path / "completo")
    parcial = tmp_path / "parcial"
    archivo(parcial, lotes=["h2h,totals"])  # solo el primer lote de la hora
    out = cn.nba_overlay(parcial, [cohorte(prop)], now=NOW)
    assert out["state"] == "partial" and out["events"]["0022600100"]["quotes"]["winner||"]["home"] is None
    archivo(parcial, lotes=["player_points"])  # llega el lote que faltaba
    out = cn.nba_overlay(parcial, [cohorte(prop)], now=NOW)
    assert out["state"] == "ok" and out["events"]["0022600100"]["quotes"]["winner||"]["home"]["price"] == 1.62


def test_cohorte_nueva_que_el_cliente_descarta_no_gana(tmp_path):
    vieja_prop = archivo(tmp_path / "arch", clock=NOW - timedelta(hours=1))
    nueva_prop = archivo(tmp_path / "arch", events=[ev_lakers(bump=.10)])
    vieja = dict(cohorte(vieja_prop, created=SEALED - timedelta(hours=1)), cohort="vieja")
    for cambio in ("hold_evento", "hold_fila", "probabilidad", "sello"):
        nueva = dict(cohorte(nueva_prop, created=SEALED), cohort="nueva")
        if cambio == "hold_evento":
            nueva["games"][0]["status"] = "validation_hold"
        for f in nueva["forecasts"]:
            if cambio == "hold_fila":
                f["result"] = dict(status="validation_hold")
            elif cambio == "probabilidad":
                f["probability_over"] = 1.0
            elif cambio == "sello":
                f["sealed_at_utc"] = "no es fecha"
        entry = cn.nba_overlay(tmp_path / "arch", [vieja, nueva], now=NOW)["events"]["0022600100"]
        assert entry["cohort"] == "vieja" and entry["sealed_at"] == vieja["created_at_utc"], cambio
        assert entry["quotes"]["winner||"]["home"] == q(1.62, "bet365", vieja_prop, "home", 2), cambio
    nueva = dict(cohorte(nueva_prop, created=SEALED), cohort="nueva")
    entry = cn.nba_overlay(tmp_path / "arch", [vieja, nueva], now=NOW)["events"]["0022600100"]
    assert entry["cohort"] == "nueva" and entry["recalculated_at"] is None
    assert entry["quotes"]["winner||"]["home"] == q(1.70, "pinnacle", nueva_prop, "home", 2)


def test_cohorte_sin_hora_cuenta_como_la_mas_antigua(tmp_path):
    prop = archivo(tmp_path / "arch")
    sin_hora = {k: v for k, v in dict(cohorte(prop), cohort="sin").items() if k != "created_at_utc"}
    con_hora = dict(cohorte(prop), cohort="con")
    for orden in ([sin_hora, con_hora], [con_hora, sin_hora]):
        assert cn.nba_overlay(tmp_path / "arch", orden, now=NOW)["events"]["0022600100"]["cohort"] == "con"


def test_alias_de_elegible():
    from qf.ingest import cuotas_referencia as cr
    assert cr._elegible is cr.elegible


def test_peticiones_simultaneas_analizan_el_recibo_una_vez(tmp_path, monkeypatch):
    import threading
    import time
    prop = archivo(tmp_path / "arch")
    real, llamadas = pl.newest, []

    def lento(*a, **k):
        llamadas.append(1)
        time.sleep(.2)
        return real(*a, **k)
    monkeypatch.setattr(pl, "newest", lento)
    hilos = [threading.Thread(target=cn.nba_quotes, args=(cohorte(prop), tmp_path / "arch")) for _ in range(4)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert len(llamadas) == 1
