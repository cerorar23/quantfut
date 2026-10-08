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

def test_solo_entra_lo_que_esta_en_rango_y_paga_al_menos_el_justo():
    assert es.elegir([_o(0.75, 1.30)]) is None            # 0,975: margen en contra
    assert es.elegir([_o(0.80, 1.20)]) is None            # fuera de rango por abajo
    assert es.elegir([_o(0.70, 1.45)]) is None            # fuera de rango por arriba
    assert es.elegir([_o(0.75, 1.34)]).price == 1.34      # 1,005
    assert es.elegir([_o(0.80, 1.25)]).price == 1.25      # justo exacto vale


def test_elige_el_de_mas_valor_y_desempata_por_probabilidad():
    a, b, c = _o(0.74, 1.36, match="a"), _o(0.77, 1.32, match="b"), _o(0.76, 1.34, match="c")
    # a: 0,74 × 1,36 = 1,0064 · b: 0,77 × 1,32 = 1,0164 · c: 0,76 × 1,34 = 1,0184
    assert es.elegir([a, b, c]).match_id == "c"
    assert es.elegir([a, b]).match_id == "b"
    d, e = _o(0.75, 1.36, match="d"), _o(0.80, 1.275, match="e")   # mismo EV: 1,02
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
    monkeypatch.setattr(escalera_datos, "_ultimo_reto",
                        lambda: pytest.fail("apagada no debe ni leer retos"))
    assert escalera_datos.select_and_persist()["estado"] == "desactivado"
