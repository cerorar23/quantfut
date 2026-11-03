"""Respaldo de cuotas con The Odds API histórico: respuestas grabadas, sin red."""
import json
from types import SimpleNamespace
from datetime import timedelta

import pytest
import test_cuotas_nba as base

from qf.api import cuotas_nba as cn
from qf.ingest import cuotas_respaldo as cr
from qf.ingest import propline_shared as pl

SEALED, NOW = base.SEALED, base.SEALED + timedelta(hours=1)
STAMP = pl.stamp(SEALED)


def fila_total(sealed=SEALED):
    return base.fila("game_total", "total", 215.5, None, sealed, gid="0022600099")


def cohortes(tmp_path):
    prop = base.archivo(tmp_path / "arch", clock=base.NOW - timedelta(hours=2), events=[base.ev_celtics()])
    c = base.cohorte_celtics(prop)
    c["forecasts"].append(fila_total())
    return tmp_path / "arch", [c]


def oevento(**kw):
    e = dict(id="OE1", commence_time="2026-10-31T00:00:00Z", home_team="Boston Celtics", away_team="New York Knicks")
    e.update(kw)
    return e


def libro(key, over=1.90, under=1.90, punto=215.5, h2h=(1.55, 2.60)):
    mk = [dict(key="totals", outcomes=[dict(name="Over", price=over, point=punto),
                                       dict(name="Under", price=under, point=punto)])]
    if h2h:
        mk.append(dict(key="h2h", outcomes=[dict(name="Boston Celtics", price=h2h[0]),
                                            dict(name="New York Knicks", price=h2h[1])]))
    return dict(key=key, markets=mk)


class Red:
    """Doble de The Odds API: registra las peticiones; /v4/sports es gratis."""
    def __init__(self, libros=None, eventos=None, ts=None, saldo=2855):
        self.llamadas, self.saldo = [], saldo
        self.libros = libros if libros is not None else [libro("draftkings", 1.92, 1.88), libro("fanduel", 1.95, 1.85),
                                                          libro("prizepicks", 3.0, 3.0)]
        self.eventos = eventos if eventos is not None else [oevento()]
        self.ts = ts or (SEALED - timedelta(minutes=3))

    def __call__(self, path, params):
        assert "apiKey" not in params
        self.llamadas.append((path, dict(params)))
        if path == "/v4/sports":
            return 200, {"x-requests-remaining": str(self.saldo)}, [{"key": "basketball_nba", "active": True}]
        n = 1 if path.endswith("/events") else 10 * len(params["markets"].split(","))
        self.saldo -= n
        h = {"x-requests-remaining": str(self.saldo), "x-requests-last": str(n)}
        if path.endswith("/events"):
            return 200, h, {"timestamp": pl.stamp(self.ts), "data": self.eventos}
        return 200, h, {"timestamp": pl.stamp(self.ts), "data": oevento(bookmakers=self.libros)}

    def de_pago(self):
        return [c for c in self.llamadas if c[0] != "/v4/sports"]


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    cn.clear_cache()
    archive, cs = cohortes(tmp_path)
    monkeypatch.setattr(cr, "settings", SimpleNamespace(propline_archive=str(archive), nba_cohorts_dir="x",
                                                        tennis_sealed_dir=None, odds_api_respaldo_key=None,
                                                        cuotas_respaldo_cache=None))
    monkeypatch.setattr(cn, "load_cohorts", lambda *a, **k: cs)
    cache = tmp_path / "cache.json"
    yield archive, cs, cache
    cn.clear_cache()


def corre(cache, red, **kw):
    out = []
    cr.correr(key="no-es-una-clave", cache_path=str(cache), get=red, now=NOW, salida=out.append, **kw)
    return out


def overlay(archive, cs, cache):
    return cr.aplica_nba(cn.nba_overlay(archive, cs, now=NOW), cr.leer_cache(cache))["events"]["0022600099"]["quotes"]


def test_seco_no_hace_peticiones(entorno):
    archive, cs, cache = entorno
    red = Red()
    out = corre(cache, red)
    assert red.llamadas == [] and not cache.exists()
    assert any("1 filas" in x and "coste estimado ~11" in x for x in out) and any("seco" in x for x in out)


def test_sin_clave_no_hace_nada(entorno):
    archive, cs, cache = entorno
    red = Red()
    cr.correr(key=None, ejecutar=True, cache_path=str(cache), get=red, salida=lambda x: None)
    assert red.llamadas == [] and not cache.exists()


def test_rellena_hueco_propline_gana_y_dfs_excluido(entorno):
    archive, cs, cache = entorno
    red = Red()
    corre(cache, red, ejecutar=True)
    assert [p for p, _ in red.de_pago()] == ["/v4/historical/sports/basketball_nba/events",
                                              "/v4/historical/sports/basketball_nba/events/OE1/odds"]
    assert red.de_pago()[1][1]["date"] == STAMP and red.de_pago()[1][1]["markets"] == "totals"
    q = overlay(archive, cs, cache)
    assert q["game_total||215.5"]["over"] == dict(price=1.95, book="fanduel", as_of=pl.stamp(red.ts), books=2,
                                                  side="over", src="the-odds-api")
    assert q["game_total||215.5"]["under"]["book"] == "draftkings" and q["game_total||215.5"]["under"]["price"] == 1.88
    # PropLine gana: el ganador ya tenía cuota y no recibe src ni se pide.
    assert q["winner||"]["home"]["book"] == "pinnacle" and "src" not in q["winner||"]["home"]


def test_propline_no_se_sobrescribe_con_cache(entorno):
    archive, cs, cache = entorno
    entrada = dict(sealed_at=STAMP, timestamp=pl.stamp(SEALED - timedelta(minutes=1)),
                   rows=[cr._fila("x", "Boston Celtics", "home", None, 9.0),
                         cr._fila("x", "New York Knicks", "away", None, 9.0)])
    cache.write_text(json.dumps(dict(entries={"0022600099|winner||": entrada})))
    assert overlay(archive, cs, cache)["winner||"]["home"]["price"] == 1.50


def test_snapshot_posterior_al_sello_se_descarta(entorno):
    archive, cs, cache = entorno
    corre(cache, Red(ts=SEALED + timedelta(minutes=1)), ejecutar=True)
    assert not cache.exists()
    # Y una entrada con hora posterior al sello no se aplica en el overlay.
    fila = [cr._fila("a", "Over", None, 215.5, 1.9), cr._fila("a", "Under", None, 215.5, 1.9)]
    cache.write_text(json.dumps(dict(entries={"0022600099|game_total||215.5": dict(
        sealed_at=STAMP, timestamp=pl.stamp(SEALED + timedelta(seconds=1)), rows=fila)})))
    assert overlay(archive, cs, cache)["game_total||215.5"] == dict(over=None, under=None)


def test_linea_distinta_se_descarta(entorno):
    archive, cs, cache = entorno
    corre(cache, Red(libros=[libro("draftkings", punto=216.5, h2h=None)]), ejecutar=True)
    assert overlay(archive, cs, cache)["game_total||215.5"] == dict(over=None, under=None)


def test_presupuesto_y_suelo(entorno):
    archive, cs, cache = entorno
    red = Red()
    out = corre(cache, red, ejecutar=True, max_creditos=5)
    assert len(red.de_pago()) == 1 and any("parado" in x for x in out)  # el listado (1) cabe; el evento (10) no
    assert not cache.exists()
    red = Red(saldo=505)
    corre(cache, red, ejecutar=True)
    assert len(red.de_pago()) == 1  # el listado cabe (504); el evento (10) dejaría 494 < suelo
    assert not cache.exists()


@pytest.mark.parametrize("eventos", [
    [oevento(), oevento(id="OE2")],                                     # dos candidatos: duda
    [oevento(home_team="Boston Celtic")],                               # nombre parecido, no exacto
    [oevento(commence_time="2026-10-31T02:00:00Z")],                    # comienzo lejano
    [],
])
def test_emparejamiento_dudoso_se_descarta(entorno, eventos):
    archive, cs, cache = entorno
    red = Red(eventos=eventos)
    corre(cache, red, ejecutar=True)
    assert len(red.de_pago()) == 1 and not cache.exists()


def test_entradas_ya_en_cache_no_se_vuelven_a_pedir(entorno):
    archive, cs, cache = entorno
    corre(cache, Red(), ejecutar=True)
    red = Red()
    corre(cache, red, ejecutar=True)
    assert red.de_pago() == []


def test_jugador_sin_nombre_no_se_pide(entorno):
    archive, cs, cache = entorno
    cs[0]["forecasts"].append(base.fila("player_points", base.LEBRON, 24.5, base.BOS, gid="0022600099"))
    assert {i["market"] for h in cr.huecos_nba(archive, cs, {}) for i in h.items} == {"game_total"}


def test_tenis_rellena_hueco_con_jugadores_exactos():
    a, b = "Jannik Sinner", "Carlos Alcaraz"
    sello = pl.parse_time("2026-10-30T10:15:00Z")
    h = cr.Hueco("tenis", "1", None, a, b, pl.parse_time("2026-10-30T14:00:00Z"), sello, [
        dict(key="winner", market="winner", odds_market="h2h", line=None, selection="A"),
        dict(key="games_total-0", market="games_total", odds_market="totals", line=22.5, selection="over")])
    data = dict(id="T", commence_time="2026-10-30T14:00:00Z", home_team=b, away_team=a, bookmakers=[
        dict(key="pinnacle", markets=[dict(key="h2h", outcomes=[dict(name=a, price=1.8), dict(name=b, price=2.1)]),
                                      dict(key="totals", outcomes=[dict(name="Over", price=1.85, point=22.5),
                                                                   dict(name="Under", price=2.0, point=22.5)])])])
    ts = sello - timedelta(minutes=2)

    def get(path, params):
        cuerpo = [data] if path.endswith("/events") else data
        return 200, {"x-requests-last": "1"}, {"timestamp": pl.stamp(ts), "data": cuerpo}
    cli = cr.Cliente(get, cr.Presupuesto(300))
    entries = {}
    assert cr._procesa(cli, h, ["tennis_atp_paris"], {}, entries) == 2
    out = cr.aplica_tenis(dict(events={"1": {"winner": None, "games_total-0": None, "tiebreak-3": None}}), entries)
    assert out["events"]["1"]["winner"] == dict(price=1.8, book="pinnacle", as_of=pl.stamp(ts), books=1, side="A",
                                                src="the-odds-api")
    assert out["events"]["1"]["games_total-0"]["side"] == "over" and out["events"]["1"]["tiebreak-3"] is None
    # Jugadores parecidos pero no exactos: sin emparejar.
    h2 = cr.Hueco("tenis", "2", None, "Jannik Sinn", b, h.comienzo, sello, h.items)
    assert cr._procesa(cli, h2, ["tennis_atp_paris"], {}, {}) == 0


def test_cache_atomica_y_poda(tmp_path):
    p = tmp_path / "c.json"
    vieja = dict(sealed_at="2026-10-01T00:00:00Z", timestamp="2026-10-01T00:00:00Z", rows=[])
    cr.escribir_cache(p, {"a|k": vieja, "b|k": dict(vieja, sealed_at=STAMP)}, NOW)
    assert list(cr.leer_cache(p)) == ["b|k"] and not (tmp_path / "c.json.tmp").exists()
    assert cr.leer_cache(tmp_path / "no.json") == {} and cr.leer_cache(None) == {}


# --- pasada automática (auto) ------------------------------------------------------------------------------------

def activa(monkeypatch, cache, **kw):
    s = cr.settings
    s.cuotas_respaldo_auto, s.cuotas_respaldo_auto_max, s.cuotas_respaldo_diario = True, 100, 300
    s.cuotas_respaldo_cache = str(cache)
    for k, v in kw.items():
        setattr(s, k, v)


def llama(cache, red, alertas=None, **kw):
    return cr.auto(key="no-es-una-clave", get=red, now=NOW, alerta=(alertas.append if alertas is not None else None), **kw)


def test_auto_desactivado_no_hace_nada(entorno, monkeypatch):
    archive, cs, cache = entorno
    s = cr.settings
    s.cuotas_respaldo_auto, s.cuotas_respaldo_auto_max, s.cuotas_respaldo_diario = False, 100, 300
    s.cuotas_respaldo_cache = str(cache)
    red = Red()
    assert llama(cache, red)["estado"] == "desactivado"
    assert red.llamadas == [] and not cache.exists()


def test_auto_sin_huecos_no_pide(entorno, monkeypatch):
    archive, cs, cache = entorno
    activa(monkeypatch, cache)
    monkeypatch.setattr(cn, "load_cohorts", lambda *a, **k: [])
    red = Red()
    llama(cache, red)
    assert red.llamadas == []


def test_auto_con_hueco_pide_una_vez(entorno, monkeypatch):
    archive, cs, cache = entorno
    activa(monkeypatch, cache)
    red = Red()
    r = llama(cache, red)
    assert r["estado"] == "ok" and len(red.de_pago()) == 2 and cache.exists()
    n = len(red.llamadas)
    llama(cache, red)  # segunda pasada: el hueco ya está en la caché
    assert len(red.llamadas) == n


def test_auto_tope_diario_entre_pasadas(entorno, monkeypatch):
    archive, cs, cache = entorno
    activa(monkeypatch, cache, cuotas_respaldo_diario=0)
    red = Red()
    assert llama(cache, red)["estado"] == "tope_diario" and red.llamadas == []
    activa(monkeypatch, cache, cuotas_respaldo_diario=15)
    llama(cache, red)  # listado (1) + evento (10) = 11 créditos; el gasto queda persistido
    assert len(red.de_pago()) == 2
    assert cr._gasto_hoy(cache.with_name("cache.json.gasto.json"), NOW) == 11
    activa(monkeypatch, cache, cuotas_respaldo_diario=11)
    otra = Red()
    assert llama(cache, otra)["estado"] == "tope_diario" and otra.llamadas == []


def test_auto_excepcion_no_se_propaga_y_saldo_bajo_alerta(entorno, monkeypatch):
    archive, cs, cache = entorno
    activa(monkeypatch, cache)

    def rota(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(cr, "correr", rota)
    assert llama(cache, Red())["estado"] == "error"


def test_auto_saldo_bajo_el_suelo_alerta(entorno, monkeypatch):
    archive, cs, cache = entorno
    activa(monkeypatch, cache)
    alertas = []
    llama(cache, Red(saldo=505), alertas)
    assert len(alertas) == 1
