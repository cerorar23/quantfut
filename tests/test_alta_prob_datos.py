"""E/S de la línea de alta probabilidad, con la base de datos simulada."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest

from qf.config import settings
from qf.model.pricing import (market_1x2, market_team_total, market_totals, score_matrix,
                              totals_fair_over)
from qf.publish import alta_prob as ap
from qf.publish import alta_prob_datos as ad
from qf.publish import picks as pk

NOW = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _solo_mercados_de_pinnacle(monkeypatch):
    """
    Las pruebas de E/S de antes de la ampliación (2026-10-09) simulan solo las
    consultas de Pinnacle. Hándicap y córners leen otras tablas: se apagan
    aquí y se prueban aparte, con sus propias consultas simuladas.
    """
    monkeypatch.setattr(ap, "HANDICAP_HABILITADOS", ())
    monkeypatch.setattr(ap, "CORNERS_HABILITADOS", ())
    monkeypatch.setattr(ap, "BTTS_HABILITADOS", ())


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


# --- Rama de goles de la capa de datos ----------------------------------------
#
# Pinnacle da casi siempre una línea de CUARTO de gol (2,75): es la que ajusta
# las lambdas. Lo publicado es inmutable, así que la rama se ejercita entera
# antes de activar: precios de Pinnacle fabricados sin margen desde un partido
# con lambdas conocidas, y el ajuste tiene que recuperarlas.

RHO = -0.06
GOLES = (("over", 1.5), ("under", 3.5), ("under", 4.5))


def _mercado_pinnacle(lam, mu, linea=2.75):
    """(snapshot, filas de totales) de Pinnacle SIN margen para un partido (lam, mu)."""
    m = score_matrix(lam, mu, RHO)
    p = market_1x2(m)
    p_over = totals_fair_over(m, linea)
    snap = _snap((1 / p["home"], 1 / p["draw"], 1 / p["away"]))
    filas = [{"bookmaker": "pinnacle", "selection": "over", "line": linea, "price": 1 / p_over},
             {"bookmaker": "pinnacle", "selection": "under", "line": linea, "price": 1 / (1 - p_over)}]
    return m, snap, filas


@pytest.mark.parametrize("lam, mu, esperado", [
    (1.25, 1.0, ("under", 3.5)),     # partido igualado: solo los goles llegan al 80 %
    (2.0, 1.5, ("over", 1.5)),       # partido abierto: idem, y por el otro lado
])
def test_decidir_elige_un_mercado_de_goles_con_el_ajuste_de_la_linea_2_75(lam, mu, esperado):
    m, snap, filas = _mercado_pinnacle(lam, mu)
    # Sin la rama de goles este partido no tiene pronóstico (ni 1X2 ni doble llegan a 0,80).
    assert ad.decidir(snap, [], RHO, GOLES, set()) is None
    assert ad.decidir(snap, filas, RHO, (), set()) is None
    out = ad.decidir(snap, filas, RHO, GOLES, set())
    assert out is not None
    c, fit = out
    assert (c.market, c.selection, c.line) == ("totals", *esperado)
    verdad = market_totals(m, c.line)[c.selection]
    assert 0.80 <= c.prob <= 0.95 and c.prob == pytest.approx(verdad, abs=0.003)
    # El ajuste que se guarda en `fit` es el de la línea de cuarto de gol.
    assert fit["linea"] == 2.75 and fit["rho"] == RHO
    assert fit["lambda"] == pytest.approx(lam, abs=0.05) and fit["mu"] == pytest.approx(mu, abs=0.05)
    assert fit["residuo"] < ap.MAX_RESIDUO_AJUSTE


def test_decidir_goles_respeta_el_bloqueo_y_los_mercados_habilitados():
    _, snap, filas = _mercado_pinnacle(1.25, 1.0)
    assert ad.decidir(snap, filas, RHO, GOLES, {"totals"}) is None
    # Solo una línea habilitada: se elige esa (0,92), no la de 3,5.
    c, fit = ad.decidir(snap, filas, RHO, (("under", 4.5),), set())
    assert (c.market, c.selection, c.line) == ("totals", "under", 4.5) and fit["linea"] == 2.75
    # Sin rho del artefacto no hay ajuste: el partido se queda sin pronóstico.
    assert ad.decidir(snap, filas, None, GOLES, set()) is None


def test_decidir_no_mete_goles_de_otras_casas():
    _, snap, filas = _mercado_pinnacle(1.25, 1.0)
    de_bet365 = [{**f, "bookmaker": "bet365"} for f in filas]
    assert ad.decidir(snap, de_bet365, RHO, GOLES, set()) is None


# --- "Marca el local / el visitante" --------------------------------------------
#
# Con lambdas 1,8 / 0,6 (línea 2,5 de Pinnacle) los candidatos dentro de
# [0,80, 0,95] son "marca el local" (0,835) y la doble oportunidad 1X (0,888):
# el de menor probabilidad es el del local. "Marca el visitante" (0,45) y el
# resto quedan fuera.

EQUIPO = ("home", "away")


def test_decidir_elige_marca_el_local_con_el_ajuste_de_la_linea_2_5():
    m, snap, filas = _mercado_pinnacle(1.8, 0.6, linea=2.5)
    out = ad.decidir(snap, filas, RHO, (), set(), EQUIPO)
    assert out is not None
    c, fit = out
    assert (c.market, c.selection, c.line) == ("team_totals_home", "over", 0.5)
    verdad = market_team_total(m, 0.5, "home")["over"]
    assert 0.80 <= c.prob <= 0.95 and c.prob == pytest.approx(verdad, abs=0.003)
    # El ajuste que se guarda en `fit` es el de la línea de Pinnacle.
    assert fit["linea"] == 2.5 and fit["rho"] == RHO
    assert fit["lambda"] == pytest.approx(1.8, abs=0.05) and fit["mu"] == pytest.approx(0.6, abs=0.05)
    assert fit["residuo"] < ap.MAX_RESIDUO_AJUSTE


def test_decidir_sin_equipo_es_el_de_antes():
    _, snap, filas = _mercado_pinnacle(1.8, 0.6, linea=2.5)
    # Por defecto (y con `equipo=()`) la rama no existe: gana la doble 1X, sin ajuste.
    for out in (ad.decidir(snap, filas, RHO, (), set()),
                ad.decidir(snap, filas, RHO, (), set(), ())):
        c, fit = out
        assert (c.market, c.selection) == ("double_chance", "1X") and fit is None
    # Solo el visitante habilitado: su probabilidad (0,45) no entra en el rango.
    c, fit = ad.decidir(snap, filas, RHO, (), set(), ("away",))
    assert (c.market, c.selection) == ("double_chance", "1X") and fit is None
    # Sin rho del artefacto, sin línea de Pinnacle o con totales de otra casa: no hay ajuste.
    for rho, totales in ((None, filas), (RHO, []),
                         (RHO, [{**f, "bookmaker": "bet365"} for f in filas])):
        c, fit = ad.decidir(snap, totales, rho, (), set(), EQUIPO)
        assert (c.market, c.selection) == ("double_chance", "1X") and fit is None


def test_decidir_marca_un_equipo_respeta_el_bloqueo():
    _, snap, filas = _mercado_pinnacle(1.8, 0.6, linea=2.5)
    # Bloqueado "marca el local": gana el siguiente (la doble 1X) y no lleva ajuste.
    c, fit = ad.decidir(snap, filas, RHO, (), {"team_totals_home"}, EQUIPO)
    assert (c.market, c.selection) == ("double_chance", "1X") and fit is None
    # Bloqueados los dos: no queda nada dentro del rango.
    assert ad.decidir(snap, filas, RHO, (), {"team_totals_home", "double_chance"}, EQUIPO) is None
    # El bloqueo de los goles de partido no toca a "marca un equipo".
    c, fit = ad.decidir(snap, filas, RHO, (), {"totals"}, EQUIPO)
    assert c.market == "team_totals_home" and fit["linea"] == 2.5


def test_decidir_con_el_grupo_de_control_team_totals_excluye_los_dos_lados():
    # `control` devuelve el grupo "team_totals" (no cada lado): bloquearlo deja
    # fuera "marca el local" y "marca el visitante".
    _, snap, filas = _mercado_pinnacle(1.8, 0.6, linea=2.5)
    c, fit = ad.decidir(snap, filas, RHO, (), {"team_totals"}, EQUIPO)
    assert (c.market, c.selection) == ("double_chance", "1X") and fit is None
    assert ad.decidir(snap, filas, RHO, (), {"team_totals", "double_chance"}, EQUIPO) is None


def test_decidir_convive_con_los_goles_y_guarda_el_ajuste_solo_si_gana_un_mercado_con_ajuste():
    # Lambdas 1,25 / 1,0: "marca el local" (0,71) no llega; sigue ganando "menos de 3,5".
    _, snap, filas = _mercado_pinnacle(1.25, 1.0)
    c, fit = ad.decidir(snap, filas, RHO, GOLES, set(), EQUIPO)
    assert (c.market, c.selection, c.line) == ("totals", "under", 3.5) and fit["linea"] == 2.75


def _filas_ref(*filas):
    return [{"bookmaker": b, "selection": sel, "line": ln, "price": pr} for b, sel, ln, pr in filas]


def _filas_equipo(*filas):
    return [{"bookmaker": b, "market": mk, "selection": sel, "line": ln, "price": pr}
            for b, mk, sel, ln, pr in filas]


def test_ref_de_goles_toma_la_mejor_cuota_de_soft_books_de_la_misma_linea_y_lado(monkeypatch):
    monkeypatch.setattr(ad, "settings", replace(
        settings, soft_books=("bet365", "william_hill", "1xbet", "betano")))
    totales = _filas_ref(
        ("bet365", "under", 3.5, 1.22), ("1xbet", "under", 3.5, 1.25),
        ("william_hill", "under", 3.5, 1.20),
        ("betano", "under", 4.5, 1.40),       # otra línea
        ("bet365", "over", 3.5, 3.10),        # otro lado
        ("pinnacle", "under", 3.5, 1.30),     # no es de la lista de suscriptores
        ("unibet", "under", 3.5, 1.45),       # tampoco
        ("1xbet", "under", None, 9.0))        # fila sin línea
    snap = _snap((1.18, 7.5, 15.0))
    c = ap.Candidato("totals", "under", 3.5, 0.83)
    assert ad._ref(snap, totales, c) == (1.25, "1xbet")
    assert ad._ref(snap, totales, ap.Candidato("totals", "over", 3.5, 0.2)) == (3.10, "bet365")
    # Sin cuota de ninguna casa de la lista para esa selección: nada.
    assert ad._ref(snap, totales, ap.Candidato("totals", "over", 1.5, 0.84)) == (None, None)
    # Los alias de casa se normalizan antes de compararlos.
    alias = _filas_ref(("WilliamHill", "under", 3.5, 1.30), ("onexbet", "under", 3.5, 1.28))
    assert ad._ref(snap, alias, c) == (1.30, "william_hill")


def test_ref_de_doble_oportunidad_es_vacia():
    assert ad._ref(_snap((1.18, 7.5, 15.0)), [], ap.Candidato("double_chance", "1X", None, 0.9)) == (None, None)


def test_ref_de_marca_un_equipo_toma_la_mejor_over_0_5_de_soft_books_del_mismo_mercado(monkeypatch):
    monkeypatch.setattr(ad, "settings", replace(
        settings, soft_books=("bet365", "william_hill", "1xbet", "betano")))
    equipos = _filas_equipo(
        ("bet365", "team_totals_home", "over", 0.5, 1.18),
        ("1xbet", "team_totals_home", "over", 0.5, 1.22),
        ("william_hill", "team_totals_home", "over", 0.5, 1.20),
        ("betano", "team_totals_away", "over", 0.5, 1.80),     # otro mercado (el visitante)
        ("betano", "team_totals_home", "over", 1.5, 2.60),     # otra línea
        ("bet365", "team_totals_home", "under", 0.5, 4.00),    # otro lado
        ("pinnacle", "team_totals_home", "over", 0.5, 1.30),   # no es de la lista de suscriptores
        ("unibet", "team_totals_home", "over", 0.5, 1.45),     # tampoco
        ("1xbet", "team_totals_home", "over", None, 9.0))      # fila sin línea
    snap = _snap((1.18, 7.5, 15.0))
    local = ap.Candidato("team_totals_home", "over", 0.5, 0.84)
    assert ad._ref(snap, [], local, equipos) == (1.22, "1xbet")
    visitante = ap.Candidato("team_totals_away", "over", 0.5, 0.84)
    assert ad._ref(snap, [], visitante, equipos) == (1.80, "betano")
    # Sin filas de equipo (The Odds API o fuente desconocida): sin referencia.
    assert ad._ref(snap, [], local) == (None, None)
    assert ad._ref(snap, [], local, []) == (None, None)
    # Las filas de totales de partido no se cuelan en la referencia de un equipo...
    totales = _filas_ref(("bet365", "over", 0.5, 1.05))
    assert ad._ref(snap, totales, local, []) == (None, None)
    # ...ni las de equipo en la de los goles de partido, aunque coincidan la línea y el lado.
    assert ad._ref(snap, [], ap.Candidato("totals", "over", 0.5, 0.9), equipos) == (None, None)
    # Los alias de casa se normalizan antes de compararlos.
    alias = _filas_equipo(("WilliamHill", "team_totals_home", "over", 0.5, 1.30),
                          ("onexbet", "team_totals_home", "over", 0.5, 1.28))
    assert ad._ref(snap, [], local, alias) == (1.30, "william_hill")


def _db(monkeypatch, partidos, snap, batch_sellado=False, rho=-0.06):
    inserts = []
    # El lote de hoy lleva el bloque de alta probabilidad: sin corte, la línea
    # no elige nada (ver test_sin_corte_no_elige_pero_la_vista_previa_si).
    monkeypatch.setattr(ad.hashchain, "LOTE_ALTA_PROB_DESDE", NOW.date())
    # soft_books fijas: el .env local puede redefinir SOFT_BOOKS.
    monkeypatch.setattr(ad, "settings", replace(
        settings, alta_prob_enabled=True,
        soft_books=("bet365", "william_hill", "1xbet", "betano")))
    monkeypatch.setattr(ad, "_liquidados", lambda *a, **k: [])
    monkeypatch.setattr(ad, "_rho_activo", lambda: rho)
    monkeypatch.setattr(ad, "_lote_sellado", lambda dia: batch_sellado)
    monkeypatch.setattr(ad, "_partidos", lambda now: partidos)
    monkeypatch.setattr(ad, "_totales", lambda match_id, as_of: [])
    monkeypatch.setattr(ad, "_totales_af", lambda match_id, as_of, now: [])
    monkeypatch.setattr(ad, "_equipos_af", lambda match_id, as_of, now: [])
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


def test_goles_de_api_football_salen_de_la_misma_respuesta_que_el_1x2(monkeypatch):
    # A las 08:00 UTC el snapshot vigente suele ser de API-Football: sus totales
    # (misma marca `update`) sustituyen a los de The Odds API, que no se consulta.
    m, snap_pin, filas_pin = _mercado_pinnacle(1.25, 1.0, linea=2.5)
    books = {**snap_pin.books, "bet365": {"home": 2.2, "draw": 3.4, "away": 3.6}}
    snap = pk.Snapshot("api_football", snap_pin.as_of, books)
    filas = filas_pin + _filas_ref(
        ("bet365", "over", 1.5, 1.28), ("bet365", "under", 1.5, 3.40),
        ("bet365", "over", 3.5, 3.60), ("bet365", "under", 3.5, 1.27),
        ("bet365", "over", 4.5, 8.00), ("bet365", "under", 4.5, 1.08))
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}], None)
    consultas = []

    def totales_af(match_id, as_of, now):
        consultas.append((match_id, as_of, now))
        return filas

    def totales_the_odds(match_id, as_of):
        raise AssertionError("un snapshot de API-Football no mezcla totales de The Odds API")

    monkeypatch.setattr(ad.ap, "MERCADOS_GOLES_HABILITADOS", GOLES)
    monkeypatch.setattr(ad.pk, "_odds_api_snapshot", lambda m, now: None)
    monkeypatch.setattr(ad.pk, "_af_snapshot", lambda m, now: snap)
    monkeypatch.setattr(ad, "_totales_af", totales_af)
    monkeypatch.setattr(ad, "_totales", totales_the_odds)
    out = ad.select_and_persist(NOW, dry_run=True)
    assert consultas == [("m1", snap.as_of, NOW)] and inserts == []
    d = out["decisiones"][0]
    assert (d["market"], d["selection"], d["line"]) == ("totals", "under", 3.5)
    assert d["odds_source"] == "api_football"
    # La referencia es la cuota de bet365 de la misma línea y lado, no otra.
    assert (d["ref_book"], d["ref_price"]) == ("bet365", 1.27)
    assert out["resumen"]["por_fuente"] == {"api_football": 1}
    # Y al guardar, la fila lleva el ajuste de la línea de Pinnacle y la fuente.
    out = ad.select_and_persist(NOW)
    assert out["elegidos"] == 1 and len(inserts) == 1
    f = inserts[0]
    assert f[1:4] == ("totals", "under", 3.5) and f[6:9] == (1.27, "bet365", "api_football")
    assert f[9] == snap.as_of and '"linea": 2.5' in f[10]


def test_snapshot_de_the_odds_api_no_consulta_los_totales_de_api_football(monkeypatch):
    def totales_af(match_id, as_of, now):
        raise AssertionError("un snapshot de The Odds API no mezcla totales de API-Football")

    _, snap, filas = _mercado_pinnacle(1.25, 1.0)
    _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}], snap)
    monkeypatch.setattr(ad, "_totales_af", totales_af)
    monkeypatch.setattr(ad, "_totales", lambda match_id, as_of: filas)
    d = ad.select_and_persist(NOW, dry_run=True)["decisiones"][0]
    assert (d["market"], d["selection"], d["line"]) == ("totals", "under", 3.5)
    assert d["odds_source"] == "the_odds_api"


def test_totales_af_lee_la_misma_respuesta_por_su_marca_de_proveedor(monkeypatch):
    llamadas = []
    filas = [{"bookmaker": "pinnacle", "selection": "over", "line": 2.5, "price": 1.9}]

    def q(sql, params=()):
        llamadas.append((" ".join(sql.split()), params))
        return filas
    monkeypatch.setattr(ad, "query", q)
    as_of = NOW - timedelta(hours=1)
    assert ad._totales_af("m1", as_of, NOW) == filas
    sql, params = llamadas[0]
    assert "FROM af_odds_snapshots" in sql and "market = 'totals'" in sql
    assert "provider_updated_at = %s" in sql
    # Misma regla que `picks._af_snapshot`: solo lo que ya TENÍAMOS en `now`.
    assert "fetched_at <= %s" in sql
    assert params == ("m1", as_of, NOW)


def test_marca_un_equipo_de_api_football_toma_su_referencia_de_la_misma_respuesta(monkeypatch):
    # El 1X2 y la línea 2,5 de Pinnacle dan "marca el local" (0,835); su cuota
    # de referencia sale de las filas `team_totals_home` de la MISMA respuesta
    # (misma marca `update`) de API-Football.
    _, snap_pin, filas_pin = _mercado_pinnacle(1.8, 0.6, linea=2.5)
    snap = pk.Snapshot("api_football", snap_pin.as_of, snap_pin.books)
    equipos = _filas_equipo(
        ("bet365", "team_totals_home", "over", 0.5, 1.17),
        ("william_hill", "team_totals_home", "over", 0.5, 1.19),
        ("bet365", "team_totals_home", "under", 0.5, 4.50),     # otro lado
        ("betano", "team_totals_away", "over", 0.5, 1.60))      # otro mercado
    inserts = _db(monkeypatch, [PARTIDO], None)
    consultas = []

    def equipos_af(match_id, as_of, now):
        consultas.append((match_id, as_of, now))
        return equipos

    def totales_the_odds(match_id, as_of):
        raise AssertionError("un snapshot de API-Football no mezcla totales de The Odds API")

    monkeypatch.setattr(ad.pk, "_odds_api_snapshot", lambda m, now: None)
    monkeypatch.setattr(ad.pk, "_af_snapshot", lambda m, now: snap)
    monkeypatch.setattr(ad, "_totales_af", lambda match_id, as_of, now: filas_pin)
    monkeypatch.setattr(ad, "_totales", totales_the_odds)
    monkeypatch.setattr(ad, "_equipos_af", equipos_af)
    out = ad.select_and_persist(NOW, dry_run=True)
    assert consultas == [("m1", snap.as_of, NOW)] and inserts == []
    d = out["decisiones"][0]
    assert (d["market"], d["selection"], d["line"]) == ("team_totals_home", "over", 0.5)
    assert d["odds_source"] == "api_football"
    assert (d["ref_book"], d["ref_price"]) == ("william_hill", 1.19)
    assert out["resumen"]["por_mercado"] == {"team_totals_home": 1}
    # Y al guardar, la fila lleva la referencia, la fuente y el ajuste de la línea de Pinnacle.
    out = ad.select_and_persist(NOW)
    assert out["elegidos"] == 1 and len(inserts) == 1
    f = inserts[0]
    assert f[1:4] == ("team_totals_home", "over", 0.5)
    assert f[6:9] == (1.19, "william_hill", "api_football")
    assert f[9] == snap.as_of and '"linea": 2.5' in f[10]


def test_marca_un_equipo_de_the_odds_api_no_consulta_las_cuotas_de_api_football(monkeypatch):
    def equipos_af(match_id, as_of, now):
        raise AssertionError("un snapshot de The Odds API no mezcla cuotas de API-Football")

    _, snap, filas = _mercado_pinnacle(1.8, 0.6, linea=2.5)
    _db(monkeypatch, [PARTIDO], snap)
    monkeypatch.setattr(ad, "_equipos_af", equipos_af)
    monkeypatch.setattr(ad, "_totales", lambda match_id, as_of: filas)
    d = ad.select_and_persist(NOW, dry_run=True)["decisiones"][0]
    assert (d["market"], d["selection"], d["line"]) == ("team_totals_home", "over", 0.5)
    # Se elige igual, pero sin cuota de referencia (The Odds API no cotiza este mercado).
    assert d["odds_source"] == "the_odds_api" and (d["ref_price"], d["ref_book"]) == (None, None)


def test_equipos_af_lee_la_misma_respuesta_por_su_marca_de_proveedor(monkeypatch):
    llamadas = []
    filas = [{"bookmaker": "bet365", "market": "team_totals_home", "selection": "over",
              "line": 0.5, "price": 1.2}]

    def q(sql, params=()):
        llamadas.append((" ".join(sql.split()), params))
        return filas
    monkeypatch.setattr(ad, "query", q)
    as_of = NOW - timedelta(hours=1)
    assert ad._equipos_af("m1", as_of, NOW) == filas
    sql, params = llamadas[0]
    assert "FROM af_odds_snapshots" in sql
    assert "market IN ('team_totals_home', 'team_totals_away')" in sql
    assert "provider_updated_at = %s" in sql
    # Misma regla que `_totales_af`: solo lo que ya TENÍAMOS en `now`.
    assert "fetched_at <= %s" in sql
    assert params == ("m1", as_of, NOW)


def test_fuente_desconocida_no_consulta_ningun_total(monkeypatch):
    # Solo hay dos fuentes conocidas: cualquier otra no mezcla totales de nadie.
    def ninguna(*a, **k):
        raise AssertionError("una fuente desconocida no consulta totales")

    snap = pk.Snapshot("otra_fuente", NOW - timedelta(hours=1), _snap((1.18, 7.5, 15.0)).books)
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}], snap)
    monkeypatch.setattr(ad, "_totales", ninguna)
    monkeypatch.setattr(ad, "_totales_af", ninguna)
    monkeypatch.setattr(ad, "_equipos_af", ninguna)
    monkeypatch.setattr(ad.ap, "MERCADOS_GOLES_HABILITADOS", GOLES)
    out = ad.select_and_persist(NOW, dry_run=True)
    assert inserts == []
    d = out["decisiones"][0]
    assert (d["market"], d["odds_source"]) == ("h2h", "otra_fuente")


def test_dry_run_no_guarda(monkeypatch):
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}],
                  _snap((1.18, 7.5, 15.0)))
    out = ad.select_and_persist(NOW, dry_run=True)
    assert inserts == [] and out["decisiones"][0]["market"] == "h2h"


def test_vista_previa_resume_por_fuente_y_mercado(monkeypatch):
    # Con el límite de 6 h, a las 08:00 muchos partidos europeos de la tarde solo
    # tienen precio de API-Football: la vista previa cuenta cuántas decisiones
    # salen de cada fuente (aquí sin líneas de goles: `_totales_af` vacío).
    partidos = [{"match_id": f"m{i}", "kickoff_utc": NOW + timedelta(hours=8 + i)}
                for i in range(1, 7)]
    inserts = _db(monkeypatch, partidos, None)
    _, snap_goles, filas_goles = _mercado_pinnacle(1.25, 1.0)
    the_odds = {"m1": _snap((1.18, 7.5, 15.0)),            # 1X2: gana el local
                "m2": snap_goles,                          # goles (línea 2,75)
                "m6": _snap((2.6, 3.2, 2.9))}              # igualado: sin candidato
    api_football = {"m3": _snap((1.30, 5.5, 10.0), source="api_football"),   # doble oportunidad
                    "m4": _snap((1.18, 7.5, 15.0), source="api_football")}   # 1X2
    monkeypatch.setattr(ad.pk, "_odds_api_snapshot", lambda m, now: the_odds.get(m))
    monkeypatch.setattr(ad.pk, "_af_snapshot", lambda m, now: api_football.get(m))
    monkeypatch.setattr(ad, "_totales", lambda m, as_of: filas_goles if m == "m2" else [])
    out = ad.select_and_persist(NOW, dry_run=True)
    assert inserts == []
    assert out["sin_precio"] == 1 and out["sin_candidato"] == 1 and len(out["decisiones"]) == 4
    assert out["resumen"] == {"por_fuente": {"the_odds_api": 2, "api_football": 2},
                              "por_mercado": {"h2h": 2, "totals": 1, "double_chance": 1}}
    # Solo la vista previa lleva el resumen: lo que se guarda no cambia.
    assert "resumen" not in ad.select_and_persist(NOW)


def test_vista_previa_sin_decisiones_lleva_el_resumen_vacio(monkeypatch):
    _db(monkeypatch, [], None)
    out = ad.select_and_persist(NOW, dry_run=True)
    assert out["resumen"] == {"por_fuente": {}, "por_mercado": {}}


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
    out = ad.select_and_persist(NOW)
    assert out["estado"] == "desactivada" and inserts == []
    # El motivo vale antes y después de activar (el servidor no sabe en qué momento está).
    assert out["motivos"] == ["Línea desactivada"]


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


# --- Fecha de corte del lote: una sola fuente de verdad (hashchain) ---------

PARTIDO = {"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}


@pytest.mark.parametrize("corte", [None, NOW.date() + timedelta(days=1)])
def test_sin_corte_no_elige_pero_la_vista_previa_si(monkeypatch, corte):
    inserts = _db(monkeypatch, [PARTIDO], _snap((1.18, 7.5, 15.0)))
    monkeypatch.setattr(ad.hashchain, "LOTE_ALTA_PROB_DESDE", corte)
    out = ad.select_and_persist(NOW)
    assert inserts == []
    assert out["estado"] == "sin_corte" and out["elegidos"] == 0
    assert "LOTE_ALTA_PROB_DESDE" in " ".join(out["motivos"])
    vista = ad.select_and_persist(NOW, dry_run=True)
    assert inserts == [] and vista["decisiones"][0]["market"] == "h2h"


def test_el_corte_se_mide_en_utc(monkeypatch):
    # 22:00 en UTC-5 del 6 de octubre = 03:00 UTC del 7: el lote ya lleva el bloque.
    ahora = datetime(2026, 10, 6, 22, 0, tzinfo=timezone(timedelta(hours=-5)))
    snap = pk.Snapshot("the_odds_api", ahora - timedelta(hours=1),
                       {"pinnacle": dict(zip(("home", "draw", "away"), (1.18, 7.5, 15.0)))})
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": ahora + timedelta(hours=10)}], snap)
    monkeypatch.setattr(ad.hashchain, "LOTE_ALTA_PROB_DESDE", date(2026, 10, 7))
    assert ad.select_and_persist(ahora)["elegidos"] == 1 and len(inserts) == 1
    monkeypatch.setattr(ad.hashchain, "LOTE_ALTA_PROB_DESDE", date(2026, 10, 8))
    assert ad.select_and_persist(ahora)["estado"] == "sin_corte"


def _q_solo_si_cubierto(sqls):
    """Devuelve filas solo si la SQL deja pasar al lector (no lleva `AND FALSE`)."""
    def q(sql, params=()):
        sqls.append(sql)
        if "AND FALSE" in sql:
            return []
        if "m.kickoff_utc > now()" in sql:
            return [{"match_id": "m1", "league_id": "br.serie_a", "kickoff_utc": NOW,
                     "local": "Cruzeiro", "visitante": "Sao Paulo", "market": "double_chance",
                     "selection": "1X", "line": None, "prob": 0.87, "fair_price": 1.149,
                     "ref_price": None, "ref_book": None, "batch_date": "2026-10-06",
                     "chain_sha256": "ab" * 32}]
        if "alta_prob_results" in sql:
            return [{"market": "double_chance", "prob": 0.87, "ref_price": None,
                     "outcome": "win", "kickoff_utc": NOW}]
        return []
    return q


def test_lector_sin_corte_no_ensena_nada(monkeypatch):
    sqls = []
    monkeypatch.setattr(ad, "query", _q_solo_si_cubierto(sqls))
    monkeypatch.setattr(ad, "settings", replace(settings, alta_prob_enabled=True))
    monkeypatch.setattr(ad.hashchain, "LOTE_ALTA_PROB_DESDE", None)
    out = ad.informe_publico()
    assert out["proximos"] == []
    assert ad._liquidados(None) == []
    assert all("AND FALSE" in s for s in sqls if "alta_prob_picks a" in s)


def test_lector_con_corte_solo_cuenta_lotes_desde_esa_fecha(monkeypatch):
    sqls = []
    monkeypatch.setattr(ad, "query", _q_solo_si_cubierto(sqls))
    monkeypatch.setattr(ad, "settings", replace(settings, alta_prob_enabled=True))
    monkeypatch.setattr(ad.hashchain, "LOTE_ALTA_PROB_DESDE", date(2026, 10, 6))
    out = ad.informe_publico()
    assert out["proximos"][0]["texto"] == "Cruzeiro o empate"
    assert len(ad._liquidados(None)) == 1
    filas = [s for s in sqls if "alta_prob_picks a" in s]
    assert filas and all("b.batch_date >= DATE '2026-10-06'" in s for s in filas)
    assert not any("AND FALSE" in s for s in filas)


# --- Ampliación 2026-10-09: ambos marcan, hándicap y córners -----------------

def test_decidir_ambos_marcan_y_handicap_salen_del_mismo_ajuste():
    m, snap, filas = _mercado_pinnacle(1.25, 1.0)
    out = ad.decidir(snap, filas, RHO, (), set(), btts=("yes", "no"), handicap=(1.0, 1.5, 2.0))
    assert out is not None
    c, fit = out
    assert c.market in ("btts", "spreads") and fit is not None   # el ajuste se guarda
    assert ap.PROB_MIN <= c.prob <= ap.PROB_MAX
    # Sin ajuste de goles (sin rho) no hay ni ambos marcan ni hándicap.
    assert ad.decidir(snap, filas, None, (), set(), btts=("yes", "no"),
                      handicap=(1.0, 1.5, 2.0)) is None
    # Bloqueado por el control: no se elige.
    assert ad.decidir(snap, filas, RHO, (), {"btts", "spreads"}, btts=("yes", "no"),
                      handicap=(1.0, 1.5, 2.0)) is None


def test_decidir_acepta_corners_ya_recortados():
    snap = _snap((2.6, 3.2, 2.9))                       # nada de Pinnacle en rango
    corner = ap.Candidato("corners", "over", 7.5, 0.83)
    c, fit = ad.decidir(snap, [], None, (), set(), extra=[corner])
    assert c == corner and fit is None
    assert ad.decidir(snap, [], None, (), {"corners"}, extra=[corner]) is None


def _fila_res(market, selection, line, hg=2, ag=1, hc=6, ac=4, horas=3):
    return {"market": market, "selection": selection, "line": line,
            "home_goals": hg, "away_goals": ag, "home_corners": hc, "away_corners": ac,
            "kickoff_utc": NOW - timedelta(hours=horas)}


def test_resultado_de_los_mercados_nuevos():
    assert ad.resultado(_fila_res("corners", "over", 8.5), NOW) == ("win", 10)
    assert ad.resultado(_fila_res("corners", "under", 9.5), NOW) == ("loss", 10)
    assert ad.resultado(_fila_res("btts", "yes", None), NOW) == ("win", None)
    assert ad.resultado(_fila_res("spreads", "away", 1.0), NOW) == ("push", None)   # 2-1
    assert ad.resultado(_fila_res("spreads", "away", 1.5), NOW) == ("win", None)


def test_corners_sin_estadistica_esperan_y_luego_son_nulos():
    assert ad.resultado(_fila_res("corners", "over", 8.5, hc=None), NOW) is None
    assert ad.resultado(_fila_res("corners", "over", 8.5, hc=None, horas=80), NOW) == ("void", None)


def test_textos_nuevos():
    assert ap.texto("btts", "no", None, "A", "B") == "No marcan los dos"
    assert ap.texto("spreads", "away", 1.5, "A", "B") == "B +1,5 (hándicap asiático)"
    assert ap.texto("spreads", "home", 0.0, "A", "B") == "A gana (empate devuelve)"
    assert ap.texto("corners", "under", 10.5, "A", "B") == "Menos de 10,5 córners"


class _Acc:
    def __init__(self, media):
        self.media = media

    def lambdas(self, now, local, visitante, arbitro=None):
        return (self.media / 2, self.media / 2)


class _Modelos:
    def __init__(self, media):
        self.acc = _Acc(media)

    def de(self, liga, mercado):
        return self.acc


def test_corners_se_recortan_al_mercado_y_guardan_modelo_y_mercado(monkeypatch):
    monkeypatch.setattr(ap, "CORNERS_HABILITADOS", (("corners", "under", 12.5),))
    m = {"league_id": "es.laliga", "home_team_id": "a", "away_team_id": "b"}
    filas = [{"bookmaker": "betano", "market": "corners", "selection": s, "line": 12.5,
              "price": p, "provider_updated_at": NOW} for s, p in (("under", 1.30), ("over", 3.30))]
    cands, fits = ad._corners(m, NOW, _Modelos(8.0), filas)
    assert len(cands) == 1
    c = cands[0]
    fit = fits[("corners", "under", 12.5)]
    assert fit["modelo"] > fit["mercado"]                  # el modelo es más optimista…
    assert c.prob == pytest.approx(fit["mercado"], abs=1e-6)   # …y manda la casa
    # Sin los dos lados cotizados, no entra.
    assert ad._corners(m, NOW, _Modelos(8.0), filas[:1]) == ([], {})


def test_corners_de_un_equipo_usan_su_lambda_y_se_liquidan_con_sus_corners(monkeypatch):
    monkeypatch.setattr(ap, "CORNERS_HABILITADOS", (("corners_home", "over", 2.5),))
    m = {"league_id": "es.laliga", "home_team_id": "a", "away_team_id": "b"}
    filas = [{"bookmaker": "betano", "market": "corners_home", "selection": s, "line": 2.5,
              "price": p, "provider_updated_at": NOW} for s, p in (("over", 1.20), ("under", 4.20))]
    cands, fits = ad._corners(m, NOW, _Modelos(12.0), filas)
    assert [c.market for c in cands] == ["corners_home"]
    assert fits[("corners_home", "over", 2.5)]["lambdas"] == [6.0, 6.0]
    assert ad.resultado(_fila_res("corners_home", "over", 2.5, hc=6, ac=None), NOW) == ("win", 6)
    assert ad.resultado(_fila_res("corners_away", "over", 2.5, hc=6, ac=None), NOW) is None
    assert ap.texto("corners_home", "over", 3.5, "Real Madrid", "B") == "Más de 3,5 córners de Real Madrid"


@pytest.mark.parametrize("market", ["corners", "corners_home", "corners_away"])
def test_cuota_de_referencia_de_todos_los_corners(market):
    filas = [{"bookmaker": "betano", "market": market, "selection": "under", "line": 7.5,
              "price": 1.08, "provider_updated_at": NOW}]
    c = ap.Candidato(market, "under", 7.5, 0.80)
    assert ad._ref_nuevos(c, "m1", _snap((2.0, 3.4, 3.8)), filas) == (1.08, "betano")
