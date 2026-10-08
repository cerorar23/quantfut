"""Reto escalera: regla de elección, cuentas del saldo, lote sellado y ruta pública."""
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from qf.publish import escalera as es
from qf.publish import hashchain
from qf.publish.alta_prob import Candidato


def _o(prob, price, market="h2h", match="m1"):
    return es.Opcion(match, Candidato(market, "home", None, prob), price, "betano")


# --- Elección ------------------------------------------------------------------

def test_entra_lo_que_esta_en_rango_aunque_el_margen_vaya_en_contra():
    assert es.elegir([_o(0.75, 1.30)]).price == 1.30       # 0,975: con la regla nueva entra
    assert es.elegir([_o(0.80, 1.20)]) is None            # fuera de rango por abajo
    assert es.elegir([_o(0.70, 1.45)]) is None            # fuera de rango por arriba
    # El filtro de valor sigue disponible si se vuelve a poner EV_MIN.
    assert es.elegir([_o(0.75, 1.30)], ev_min=0.0) is None
    assert es.elegir([_o(0.75, 1.34)], ev_min=0.0).price == 1.34


def test_elige_el_mas_probable_y_desempata_por_valor():
    a, b, c = _o(0.74, 1.36, match="a"), _o(0.77, 1.32, match="b"), _o(0.76, 1.34, match="c")
    assert es.elegir([a, b, c]).match_id == "b"
    d, e = _o(0.77, 1.30, match="d"), _o(0.77, 1.33, match="e")    # misma probabilidad
    assert es.elegir([d, e]).match_id == "e"


def test_doble_oportunidad_no_entra_porque_no_hay_cuota_que_tomar():
    assert es.elegir([_o(0.80, 1.30, market="double_chance")]) is None


# --- Cuentas del saldo ---------------------------------------------------------

def _pasos(*items):
    return [es.Paso(i + 1, price, outcome) for i, (price, outcome) in enumerate(items)]


def test_escalera_completa_con_freeroll_a_2_5x():
    st = es.estado(Decimal("10"), 6, 2.5, _pasos(*[(1.30, "win")] * 6))
    # 13,00 → 16,90 → 21,97 → 28,56 (se retiran 10: 18,56) → 24,13 → 31,37
    assert st["estado"] == "completado"
    assert st["retirado"] == Decimal("10.00") and st["saldo"] == Decimal("31.37")
    assert st["ganancia"] == Decimal("31.37")


def test_fallar_despues_del_freeroll_no_pierde_la_inversion():
    st = es.estado(Decimal("10"), 6, 2.5, _pasos(*[(1.30, "win")] * 4, (1.30, "loss")))
    assert st["estado"] == "fallido" and st["ganancia"] == Decimal("0.00")
    st = es.estado(Decimal("10"), 6, 2.5, _pasos((1.30, "win"), (1.30, "loss")))
    assert st["ganancia"] == Decimal("-10.00")


def test_sin_freeroll_todo_sigue_en_juego():
    st = es.estado(Decimal("10"), 6, None, _pasos(*[(1.30, "win")] * 6))
    assert st["retirado"] == Decimal("0.00") and st["ganancia"] == Decimal("38.27")


def test_aplazado_no_cuenta_ni_mueve_el_saldo():
    st = es.estado(Decimal("10"), 2, None, _pasos((1.30, "win"), (1.40, "void"), (1.30, "win")))
    assert st["estado"] == "completado" and st["ganados"] == 2 and st["saldo"] == Decimal("16.90")


def test_escalon_pendiente_deja_el_reto_esperando_con_lo_apostado():
    st = es.estado(Decimal("10"), 6, 2.5, _pasos((1.30, "win"), (1.35, None)))
    assert st["estado"] == "esperando" and st["en_juego"] == Decimal("13.00")
    assert es.estado(Decimal("10"), 6, 2.5, [])["estado"] == "en_curso"


def test_resumen_cuenta_tambien_los_fallidos():
    retos = [{"estado": "completado", "stake_inicial": "10", "ganancia": "31.37"},
             {"estado": "fallido", "stake_inicial": "10", "ganancia": "-10.00"},
             {"estado": "fallido", "stake_inicial": "10", "ganancia": "0.00"},
             {"estado": "en_curso", "stake_inicial": "10", "ganancia": None}]
    r = es.resumen(retos)
    assert (r["cerrados"], r["completados"], r["tasa_completados"]) == (3, 1, 33.3)
    assert r["ganancia"] == "21.37" and r["roi"] == 71.2


# --- Lote sellado y API --------------------------------------------------------

def test_el_lote_solo_lleva_la_escalera_desde_su_fecha(monkeypatch):
    llamadas = []
    monkeypatch.setattr(hashchain, "query", lambda sql, params=(): llamadas.append(sql) or [])
    monkeypatch.setattr(hashchain, "LOTE_ESCALERA_DESDE", None)
    assert "escalera" not in hashchain._collect(date(2026, 10, 9))
    assert not any("escalera_pasos" in s for s in llamadas)
    monkeypatch.setattr(hashchain, "LOTE_ESCALERA_DESDE", date(2026, 10, 9))
    assert "escalera" not in hashchain._collect(date(2026, 10, 8))
    payload = hashchain._collect(date(2026, 10, 9))
    assert payload["escalera"] == {"retos": [], "pasos": []}


def test_ruta_publica_de_la_escalera(monkeypatch):
    from qf.api import main
    from qf.publish import escalera_datos

    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *_a: False)
    monkeypatch.setattr(escalera_datos, "informe_publico", lambda: {"actual": None, "historial": []})
    r = TestClient(main.app).get("/escalera")
    assert r.status_code == 200 and r.json() == {"actual": None, "historial": []}


def test_apagada_no_elige_nada(monkeypatch):
    from dataclasses import replace
    from qf.publish import escalera_datos

    monkeypatch.setattr(escalera_datos, "settings",
                        replace(escalera_datos.settings, escalera_enabled=False))
    monkeypatch.setattr(escalera_datos, "_retos",
                        lambda: pytest.fail("apagada no debe ni leer retos"))
    assert escalera_datos.select_and_persist()["estado"] == "desactivado"


# --- Retos de 3 a 6, varios a la vez ------------------------------------------

def test_longitud_del_reto_nuevo():
    assert es.longitud_nuevo([], 0) == 3
    assert es.longitud_nuevo([3], 0) == 6
    assert es.longitud_nuevo([3], es.MAX_SEIS_MES) == 4      # tope de 6 en el mes
    assert es.longitud_nuevo([3, 6], 0) == 4
    assert es.longitud_nuevo([3, 6, 4], 0) == 5
    assert es.longitud_nuevo([3, 4, 5, 6], 0) is None         # uno de cada longitud
    assert es.longitud_nuevo([6, 4], 0) == 3                  # el de 3 vuelve primero


def test_plan_sirve_primero_a_los_retos_abiertos_y_no_repite_partido():
    ops = [_o(0.76, 1.34, match="a"), _o(0.75, 1.36, match="b"), _o(0.80, 1.26, match="c"),
           _o(0.77, 1.35, match="a"),                         # otro mercado del mismo partido
           _o(0.70, 1.30, match="d"), _o(0.90, 1.10, match="e")]   # e: fuera de rango
    plan = es.planificar(en_curso=[(7, 1), (9, 3)], abiertos=[3, 6], seis_en_mes=1,
                         opciones=ops, ocupados={"c"})
    # El más avanzado (reto 9) recibe la opción más probable; c está ocupado por
    # un escalón pendiente; lo que sobra abre un reto de 4.
    assert [(r, n, o.match_id) for r, n, o in plan] == [(9, None, "a"), (7, None, "b"),
                                                         (None, 4, "d")]
    assert plan[0][2].cand.prob == 0.77


def test_plan_abre_retos_nuevos_con_lo_que_sobra():
    ops = [_o(0.76, 1.34, match=m) for m in "abcdef"]
    plan = es.planificar(en_curso=[], abiertos=[], seis_en_mes=es.MAX_SEIS_MES, opciones=ops)
    assert [n for _, n, _ in plan] == [3, 4, 5]               # sin hueco para otro de 6
    plan = es.planificar(en_curso=[], abiertos=[], seis_en_mes=0, opciones=ops)
    assert [n for _, n, _ in plan] == [3, 6, 4, 5]


def test_push_del_handicap_no_cuenta_ni_mueve_el_saldo():
    st = es.estado(Decimal("10"), 3, None, _pasos((1.30, "win"), (1.33, "push"), (1.30, "win")))
    assert st["estado"] == "en_curso" and st["ganados"] == 2 and st["saldo"] == Decimal("16.90")


def test_handicap_exacto_desde_el_1x2():
    p = {"home": 0.60, "draw": 0.25, "away": 0.15}
    assert es.prob_handicap(p, None, "home", 0.0) == pytest.approx(0.60 / 0.75)
    assert es.prob_handicap(p, None, "away", 0.5) == pytest.approx(0.40)
    assert es.prob_handicap(p, None, "home", -0.5) == pytest.approx(0.60)
    assert es.prob_handicap(p, None, "away", 1.5) is None       # necesita el ajuste de goles


def test_handicap_desde_la_matriz_es_coherente():
    from qf.model.pricing import score_matrix
    m = score_matrix(1.8, 0.9, -0.06)
    visit_15 = es.prob_handicap({"home": 0, "draw": 0, "away": 0}, m, "away", 1.5)
    local_m15 = es.prob_handicap({"home": 0, "draw": 0, "away": 0}, m, "home", -1.5)
    assert visit_15 == pytest.approx(1 - local_m15)           # las dos caras de la misma línea
    assert es.texto_handicap("away", 1.5, "Dortmund", "Werder") == "Werder +1,5 (hándicap asiático)"
    assert es.texto_handicap("home", 0.0, "Dortmund", "Werder") == "Dortmund gana (empate devuelve)"


def test_textos_de_los_mercados_nuevos():
    assert es.texto_total("corners", "over", 8.5) == "Más de 8,5 córners"
    assert es.texto_total("cards", "under", 6.5) == "Menos de 6,5 tarjetas"
    assert es.texto_btts("yes") == "Ambos equipos marcan"
