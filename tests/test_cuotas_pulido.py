"""Alertas de Telegram del respaldo de cuotas y hándicap asiático de SportsAPIPro en fútbol (respuesta real del 9-nov)."""
from datetime import datetime, timedelta, timezone

import pytest
import test_cuotas_nba as base  # noqa: F401
from test_cuotas_respaldo import NOW, Red, entorno  # noqa: F401  (fixture `entorno`)
from test_cuotas_cascada import (KO, RedFutbol, SP, calendario_nba, cuerpo_nba, futbol, futuro, mercado,  # noqa: F401
                                 pasada as pasada_sp)
from test_cuotas_therundown import RD, pasada as pasada_rd, sin_pausa  # noqa: F401

from qf.ingest import cuotas_respaldo as cr
from qf.ingest import cuotas_respaldo_futbol as rf
from qf.ingest import cuotas_sportsapipro as csp
from qf.ingest import cuotas_therundown as crd

UTC = timezone.utc


@pytest.fixture
def alertas(monkeypatch):
    enviadas = []
    monkeypatch.setattr(cr, "_enviar_alerta", enviadas.append)
    return enviadas


# --- alertas --------------------------------------------------------------------------------------------------

def test_avisa_una_vez_cada_6_horas(tmp_path, alertas):
    cache = tmp_path / "cuotas_respaldo.json"
    ahora = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
    assert cr.avisa("therundown", "uno", ahora, cache) is True
    assert cr.avisa("therundown", "dos", ahora + timedelta(hours=5, minutes=59), cache) is False
    assert cr.avisa("sportsapipro", "otra fuente", ahora + timedelta(minutes=1), cache) is True   # clave distinta
    assert cr.avisa("therundown", "tres", ahora + timedelta(hours=6, minutes=1), cache) is True
    assert alertas == ["uno", "otra fuente", "tres"]


def test_avisa_nunca_lanza(tmp_path, monkeypatch):
    def rota(_):
        raise RuntimeError("telegram caído")
    monkeypatch.setattr(cr, "_enviar_alerta", rota)
    assert cr.avisa("x", "t", datetime(2026, 11, 9, tzinfo=UTC), tmp_path / "c.json") is False


def test_avisa_sin_ruta_de_estado_envia_igual(alertas, monkeypatch):
    monkeypatch.setattr(cr, "settings", type("S", (), {"cuotas_respaldo_cache": None})())
    assert cr.avisa("x", "sin estado", datetime(2026, 11, 9, tzinfo=UTC)) is True and alertas == ["sin estado"]


def test_alerta_si_sportsapipro_se_queda_sin_cupo(entorno, alertas):
    archive, cs, cache = entorno
    futuro(cs)

    def sp(url):
        return 429, b"{}"
    cr.settings.cuotas_respaldo_cache = str(cache)
    pasada_sp(cache, Red(eventos=[]), sp)
    assert len(alertas) == 1 and "SportsAPIPro se detuvo" in alertas[0] and "429" in alertas[0]
    pasada_sp(cache, Red(eventos=[]), sp, now=NOW + timedelta(hours=2))       # dentro de 6 h: no se repite
    assert len(alertas) == 1


def test_alerta_si_therundown_rechaza_la_clave_o_se_agota(entorno, alertas):
    archive, cs, cache = entorno
    futuro(cs)
    cr.settings.cuotas_respaldo_cache = str(cache)
    pasada_rd(cache, RD(status=401))
    assert len(alertas) == 1 and "TheRundown se detuvo" in alertas[0] and "HTTP 401" in alertas[0]


def test_alerta_therundown_por_reserva_de_puntos(entorno, alertas):
    archive, cs, cache = entorno
    futuro(cs)
    cr.settings.cuotas_respaldo_cache = str(cache)
    # Dos fechas distintas obligan a una segunda petición con el saldo ya bajo la reserva.
    cs[0]["games"].append(dict(cs[0]["games"][0], event_id="otro"))
    rd = RD({}, restante=1500)
    cli = crd.Cliente("k", call=rd, sleep=sin_pausa)
    cli.eventos(4, "2026-10-31")
    with pytest.raises(crd.SinCupo) as e:
        cli.eventos(4, "2026-11-01")
    assert "reserva" in str(e.value)


def test_futbol_alerta_cuando_therundown_se_detiene(futbol, monkeypatch, alertas):
    from qf.ingest import odds_worker as ow
    h, eventos, spa, tmp = futbol
    h["odds_api_key"] = "soccer_epl"
    eventos[0]["bookmakers"][0]["key"] = "leovegas_se"
    monkeypatch.setattr(ow, "match_meta", lambda ids: {"M1": dict(match_id="M1", kickoff_utc=KO, league_id="eu.epl",
                                                                   home="Arsenal", away="Chelsea")})
    monkeypatch.setattr(spa, "event_id", lambda db, hh: None)
    monkeypatch.setattr(cr, "settings", type("S", (), {"cuotas_respaldo_cache": str(tmp / "c.json")})())
    rf.correr(ejecutar=True, get=RedFutbol(eventos), now=KO - timedelta(hours=5), lista_huecos=[h], sp_call=SP(),
              rd_key="rd", rd_call=RD(status=429), rd_sleep=sin_pausa, resolutor=lambda a, b: False, salida=lambda x: None)
    assert any("TheRundown se detuvo" in a and "429" in a for a in alertas)


# --- hándicap asiático de SportsAPIPro en fútbol -----------------------------------------------------------------

def test_opcion_handicap():
    assert csp.opcion_handicap("(-0.5) Plymouth Parkway") == (-0.5, "Plymouth Parkway")
    assert csp.opcion_handicap("(0.5) Berkhamsted Town") == (0.5, "Berkhamsted Town")
    assert csp.opcion_handicap("(+1.5) Aston Villa") == (1.5, "Aston Villa")
    assert csp.opcion_handicap("(-0.25) Real Madrid CF") == (-0.25, "Real Madrid CF")
    assert csp.opcion_handicap("Over") is None and csp.opcion_handicap("") is None and csp.opcion_handicap(None) is None


def hc_real():
    """Mercado REAL «Asian handicap» de FA Cup (partido 17364669, 9-nov-2026), periodo «Full-time»."""
    return csp.mercados({"data": {"markets": [mercado(17, "Asian handicap", [
        ("(-0.5) Plymouth Parkway", "33/40"), ("(0.5) Berkhamsted Town", "41/40")], grupo="Asian Handicap",
        periodo="Full-time")]}})


def test_handicap_asiatico_real_de_fa_cup():
    filas = csp.filas_futbol(hc_real(), "Plymouth Parkway", "Berkhamsted Town")
    sp = {(f["selection"], f["line"]): f["price"] for f in filas if f["market"] == "spreads"}
    assert sp == {("home", -0.5): pytest.approx(1.825), ("away", 0.5): pytest.approx(2.025)}
    # Equipos invertidos o desconocidos: no se adivina el signo.
    assert {(f["selection"], f["line"]) for f in csp.filas_futbol(hc_real(), "Berkhamsted Town", "Plymouth Parkway")} \
        == {("away", -0.5), ("home", 0.5)}
    assert csp.filas_futbol(hc_real()) == []
    assert csp.filas_futbol(hc_real(), "Otro FC", "Berkhamsted Town") == [dict(bookmaker="sofascore", market="spreads",
                                                                                selection="away", line=0.5, price=pytest.approx(2.025))]


def test_handicap_con_resolutor_de_nombres():
    igual = lambda proveedor, propio: crd.norm(proveedor).replace("fc ", "") == crd.norm(propio).replace(" fc", "")  # noqa: E731
    ms = csp.mercados({"data": {"markets": [mercado(17, "Asian handicap", [
        ("(-1.5) FC Barcelona", "2/1"), ("(1.5) Real Madrid", "2/5")], periodo="Full-time")]}})
    filas = csp.filas_futbol(ms, "Barcelona FC", "Real Madrid", igual)
    assert {(f["selection"], f["line"]) for f in filas} == {("home", -1.5), ("away", 1.5)}


def test_futbol_nivel3_traduce_el_handicap_con_los_nombres(futbol, monkeypatch):
    from qf.ingest import odds_worker as ow
    h, eventos, spa, tmp = futbol
    eventos[0]["bookmakers"][0]["key"] = "leovegas_se"                 # PropLine/Odds API no la cubren a suscriptores
    monkeypatch.setattr(ow, "match_meta", lambda ids: {"M1": dict(match_id="M1", kickoff_utc=KO, league_id="eu.epl",
                                                                   home="Plymouth Parkway", away="Berkhamsted Town")})
    monkeypatch.setattr(spa, "event_id", lambda db, hh: 555)
    cuerpo = {"data": {"markets": [
        mercado(1, "Full time", [("1", "79/100"), ("X", "14/5"), ("2", "31/10")], grupo="1X2", periodo="Full-time"),
        mercado(17, "Asian handicap", [("(-0.5) Plymouth Parkway", "33/40"), ("(0.5) Berkhamsted Town", "41/40")],
                grupo="Asian Handicap", periodo="Full-time")]}}
    rf.correr(ejecutar=True, get=RedFutbol(eventos), now=KO - timedelta(hours=5), lista_huecos=[h], sp_call=SP(cuerpo=cuerpo),
              resolutor=lambda a, b: crd.norm(a) == crd.norm(b), salida=lambda x: None)
    ent = rf.leer_cache(tmp / "cuotas_respaldo_futbol.json")
    filas = ent["M1|sp"]["rows"]
    assert {(f["market"], f["selection"], f["line"]) for f in filas} >= {("spreads", "home", -0.5), ("spreads", "away", 0.5)}
