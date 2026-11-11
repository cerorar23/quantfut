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

NUEVO_2 = es.Abierto(None, 0, 2)
# Reto abierto con la regla del 2026-10-08 (prob_objetivo NULL en la base).
ANTERIOR = es.Abierto(5, 1, 3, prob_ganada=0.74, prob_objetivo=None,
                      cuota_min=1.25, cuota_max=1.40)


def test_umbral_reparte_el_presupuesto_entre_los_escalones_que_faltan():
    assert es.umbral(0.80, 1.0, 2) == pytest.approx(0.8944, abs=1e-4)
    assert es.umbral(0.80, 1.0, 3) == pytest.approx(0.9283, abs=1e-4)
    # Un primer escalón muy seguro deja margen al segundo.
    assert es.umbral(0.80, 0.95, 1) == pytest.approx(0.8421, abs=1e-4)
    # Regla del 69% para 2 escalones (prob_reto ≈ 0.4761):
    assert es.umbral(es.PROB_RETO, 1.0, 2) == pytest.approx(0.6900, abs=1e-4)


def test_regla_69_exige_el_umbral_y_elige_el_mas_probable():
    ops = [_o(0.75, 1.35, match="a"),          # pasa
           _o(0.82, 1.25, match="b"),          # pasa, el más probable
           _o(0.67, 1.60, match="c"),          # 67 % < 69 %: no pasa
           _o(0.80, 1.15, match="d"),          # cuota < 1,20: fuera de rango
           _o(0.96, 1.25, match="e")]          # > 95 %: fuera de lo calibrado
    assert es.elegir(ops, NUEVO_2).match_id == "b"
    assert es.elegir(ops, NUEVO_2, usados={"b"}).match_id == "a"
    assert es.elegir([_o(0.82, 1.25, market="mercado_invalido")], NUEVO_2) is None
    assert es.elegir([_o(0.82, 1.25, market="double_chance")], NUEVO_2).cand.market == "double_chance"


def test_el_reto_entero_cumple_prob_minima():
    segundo = es.Abierto(1, 1, 2, prob_ganada=0.75)
    o = es.elegir([_o(0.68, 1.50, match="a"), _o(0.70, 1.40, match="b")], segundo)
    assert o.match_id == "b" and o.cand.prob >= es.PROB_MIN
    # Si no llega al 69 % mínimo, no entra.
    justo = es.Abierto(1, 1, 2, prob_ganada=0.75)
    assert es.elegir([_o(0.67, 1.50)], justo) is None


def test_reto_de_la_regla_anterior_sigue_con_su_rango_y_el_mas_probable():
    ops = [_o(0.74, 1.36, match="a"), _o(0.77, 1.32, match="b"), _o(0.95, 1.06, match="c")]
    assert es.elegir(ops, ANTERIOR).match_id == "b"
    d, e = _o(0.77, 1.30, match="d"), _o(0.77, 1.33, match="e")    # misma probabilidad
    assert es.elegir([d, e], ANTERIOR).match_id == "e"


def test_filtro_de_valor_sigue_disponible():
    assert not es.valida(_o(0.75, 1.30), 1.25, 1.40, ev_min=0.0)
    assert es.valida(_o(0.75, 1.34), 1.25, 1.40, ev_min=0.0)


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


def test_target_ladder_completa_al_alcanzar_meta_multiplicador():
    # Target 2.8: stake 10 -> meta payout 28.00
    pasos2 = _pasos((1.70, "win"), (1.70, "win"))
    st2 = es.estado(Decimal("10"), 6, 2.5, pasos2, target_cuota=2.8)
    assert st2["estado"] == "completado"
    assert st2["ganados"] == 2
    assert st2["retirado"] == Decimal("10.00")


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
    from qf.api import mobile
    monkeypatch.setattr(mobile, 'features', lambda: {key: {'enabled': True} for key in mobile.SECTIONS})
    monkeypatch.setattr(mobile, 'allocations', lambda rows, stream: set())
    monkeypatch.setattr(escalera_datos, "informe_publico", lambda: {"activo": True, "actuales": [], "historial": []})
    r = TestClient(main.app).get("/escalera")
    assert r.status_code == 200 and r.json() == {"activo": True, "actuales": [], "historial": []}
    assert r.headers['cache-control'] == 'no-store'


def test_apagada_no_elige_nada(monkeypatch):
    from dataclasses import replace
    from qf.publish import escalera_datos

    monkeypatch.setattr(escalera_datos, "settings",
                        replace(escalera_datos.settings, escalera_enabled=False))
    monkeypatch.setattr(escalera_datos, "_retos",
                        lambda: pytest.fail("apagada no debe ni leer retos"))
    assert escalera_datos.select_and_persist()["estado"] == "desactivado"


# --- Retos de 2 escalones en 7 días ----------------------------------------------

def _ids(plan):
    return [(r, n, [o.match_id for o in escalones]) for r, n, escalones in plan]


def test_un_reto_de_cada_target_abierto_a_la_vez():
    assert es.target_nuevo([]) == 2.0
    assert es.target_nuevo([2.0]) == 2.8
    assert es.target_nuevo(list(es.TARGETS)) is None


def test_un_escalon_al_dia_regla_dorada():
    # Con POR_DIA = 1 cada reto abierto toma como máximo 1 escalón por día.
    ops = [_o(0.75, 1.30, match="a"), _o(0.72, 1.40, match="b"), _o(0.68, 1.50, match="c")]
    assert _ids(es.planificar([], [], ops)) == [(None, 2.0, ["a"]), (None, 2.8, ["b"])]


def test_plan_sirve_primero_a_los_retos_abiertos_y_no_repite_partido():
    ops = [_o(0.96, 1.25, match="a"), _o(0.85, 1.45, match="b"), _o(0.88, 1.35, match="c"),
           _o(0.90, 1.28, match="a"),                         # otro mercado del mismo partido
           _o(0.76, 1.34, match="d")]
    plan = es.planificar(en_curso=[es.Abierto(9, 1, 2, prob_ganada=0.75), ANTERIOR],
                         abiertos=list(es.TARGETS), opciones=ops, ocupados={"c"})
    # El reto 9 recibe a (0,96 pasa del tope de 95 %: el de 0,90); c está ocupado por un
    # escalón pendiente; el reto anterior, uno solo y en su rango 1,25-1,40 (d: b tiene cuota 1,45).
    assert _ids(plan) == [(9, None, ["a"]), (5, None, ["d"])]
    assert plan[0][2][0].cand.prob == 0.90


def test_si_un_reto_se_queda_sin_escalon_no_se_abre_otro():
    ops = [_o(0.75, 1.30, match=m) for m in "abc"]
    sin = es.Abierto(4, 1, 2, prob_ganada=0.476101)            # necesitaría ~100 %
    assert es.planificar([sin], [], ops) == []


def test_pasado_el_plazo_expira_y_cobra_el_saldo():
    st = es.estado(Decimal("10"), 2, None, _pasos((1.06, "win")), vencido=True)
    assert st["estado"] == "expirado" and st["ganancia"] == Decimal("0.60")
    # Con un escalón pendiente se espera su resultado aunque haya vencido.
    st = es.estado(Decimal("10"), 2, None, _pasos((1.06, "win"), (1.08, None)), vencido=True)
    assert st["estado"] == "esperando"
    st = es.estado(Decimal("10"), 2, None, _pasos((1.06, "win"), (1.08, "win")), vencido=True)
    assert st["estado"] == "completado"
    r = es.resumen([{"estado": "expirado", "stake_inicial": "10", "ganancia": "0.60"},
                    {"estado": "completado", "stake_inicial": "10", "ganancia": "1.45"}])
    assert (r["cerrados"], r["completados"], r["expirados"], r["tasa_completados"]) == (2, 1, 1, 50.0)


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


def test_paso_publico_lleva_seleccion_y_linea_para_traducir_en_la_app():
    from datetime import datetime, timezone
    from qf.publish import escalera_datos as ed
    paso = {"paso": 1, "match_id": "m1", "league_id": "es.laliga",
            "kickoff_utc": datetime(2026, 10, 10, 18, tzinfo=timezone.utc),
            "local": "Lens", "visitante": "Nice", "market": "totals", "selection": "over",
            "line": 1.5, "prob": 0.78123, "price": 1.4, "book": "bet365", "outcome": "win",
            "home_goals": 2, "away_goals": 1, "valor": None}
    out = ed._paso_publico(paso)
    assert (out["market"], out["selection"], out["line"]) == ("totals", "over", 1.5)
    assert out["texto"] == "Más de 1,5 goles"
    assert ed._paso_publico({**paso, "market": "btts", "selection": "no", "line": None})["line"] is None


# --- Rediseño por objetivo de cobro: lo que NO debe romper a los retos abiertos -----------------

def test_reto_del_80_abierto_conserva_su_presupuesto_de_probabilidad():
    # Reto 2 pasos al 80 %: el primer escalón exige sqrt(0,80) = 0,894; 0,80 no basta.
    reto = es.Abierto(21, 0, 2, prob_objetivo=0.80, cuota_min=1.03, cuota_max=1.40)
    flojo = es.Opcion("a:1", es.Candidato("h2h", "home", None, 0.80), 1.10, "bet365")
    firme = es.Opcion("a:2", es.Candidato("h2h", "home", None, 0.93), 1.05, "bet365")
    assert es.elegir([flojo], reto) is None
    assert es.elegir([flojo, firme], reto).match_id == "a:2"


def test_estado_con_objetivo_de_cobro_cierra_al_alcanzar_el_multiplo():
    pasos = [es.Paso(1, 1.50, "win"), es.Paso(2, 1.50, "win")]          # 10 -> 22,50 (>= x2,0)
    st = es.estado(Decimal("10.00"), 6, None, pasos, target_cuota=2.0)
    assert st["estado"] == "completado" and st["ganados"] == 2 and st["ganancia"] == Decimal("12.50")
    # Sin objetivo (regla anterior) el mismo reto de 6 pasos sigue abierto.
    assert es.estado(Decimal("10.00"), 6, None, pasos)["estado"] == "en_curso"


def test_un_paso_repetido_no_cuenta_dos_veces_en_el_informe():
    # El informe público une cada paso con UN lote diario (batch_kind = 'diario').
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src/qf/publish/escalera_datos.py").read_text(encoding="utf-8")
    assert "b.batch_kind = 'diario'" in src


def test_escalera_aplazado_y_reprogramado_anulan_a_las_6_horas_sin_tocar_parley():
    from datetime import datetime, timedelta, timezone
    from qf.publish import escalera_datos as ed

    assert ed.ESCALERA_MARGEN_APLAZADO == timedelta(hours=6)
    # Parley y Tarjetas conservan su propio margen de 48 h intacto.
    assert ed.MARGEN_APLAZADO == timedelta(hours=48)

    ko = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    aplazado = {"status": "postponed", "kickoff_utc": ko, "kickoff_original": ko,
                "home_goals": None, "away_goals": None, "market": "h2h", "selection": "home", "line": None}
    assert ed.resultado(aplazado, ko + timedelta(hours=5)) is None
    assert ed.resultado(aplazado, ko + timedelta(hours=7)) == ("void", None, None, None)

    reprogramado = {**aplazado, "status": "scheduled", "kickoff_utc": ko + timedelta(days=3)}
    assert ed.resultado(reprogramado, ko + timedelta(hours=5)) is None
    assert ed.resultado(reprogramado, ko + timedelta(hours=7)) == ("void", None, None, None)


def test_reemplazar_nulos_cubre_reto_y_oculta_void_en_activos(monkeypatch):
    from dataclasses import replace
    from datetime import datetime, timedelta, timezone
    from qf.publish import escalera_datos as ed, hashchain as hc

    ahora = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(ed, "settings", replace(ed.settings, escalera_enabled=True))
    monkeypatch.setattr(hc, "LOTE_ESCALERA_DESDE", date(2026, 10, 9))
    monkeypatch.setattr(ed, "settle_pending", lambda now=None: {"settled": 1})

    reto = {"reto_id": 21, "stake_inicial": Decimal("10.00"), "pasos_objetivo": 2,
            "target_cuota": None, "cuota_min": 1.03, "cuota_max": 1.40, "freeroll_x": None,
            "prob_objetivo": 0.80, "dias_max": 7, "created_at": ahora - timedelta(days=5)}
    p_void = {"paso_id": "11111111-1111-1111-1111-111111111111", "reto_id": 21, "paso": 1,
              "match_id": "tenis:ev1", "league_id": "tenis", "deporte": "tenis",
              "kickoff_utc": ahora - timedelta(hours=7), "local": "A", "visitante": "B",
              "market": "h2h", "selection": "home", "line": None, "prob": 0.94, "price": 1.28,
              "book": "bovada", "outcome": "void", "home_goals": None, "away_goals": None,
              "valor": None, "batch_date": date(2026, 11, 10), "chain_sha256": "a" * 64}
    reemplazo_op = es.Opcion("tenis:ev2", es.Candidato("h2h", "home", None, 0.93), 1.30, "bovada",
                             "propline", ahora, "tenis", ("ev2", "tennis_atp", ahora + timedelta(hours=3), "C", "D"))

    monkeypatch.setattr(ed, "_retos", lambda: [reto])
    monkeypatch.setattr(ed, "_pasos", lambda rid, solo_sellados=False: [p_void])
    # Si el partido viejo volviera a aparecer reprogramado, `ocupados` impide re-elegirlo.
    mismo = es.Opcion("tenis:ev1", es.Candidato("h2h", "home", None, 0.96), 1.35, "bovada",
                      "propline", ahora, "tenis", ("ev1", "tennis_atp", ahora + timedelta(hours=3), "A", "B"))
    monkeypatch.setattr(ed, "_evaluar_opciones", lambda now: ([mismo, reemplazo_op], 0))
    insertados, sellados = [], []
    monkeypatch.setattr(ed, "_insertar_paso",
                        lambda rid, op, reemplaza_paso_id=None: insertados.append((rid, op.match_id, reemplaza_paso_id))
                        or "22222222-2222-2222-2222-222222222222")
    monkeypatch.setattr(hc, "seal_escalera",
                        lambda pid, git_push=True: sellados.append(pid) or {"chain_sha256": "b" * 64})

    res = ed.reemplazar_nulos(ahora)
    assert res["estado"] == "reemplazado" and res["reemplazados"] == 1
    assert insertados == [(21, "tenis:ev2", "11111111-1111-1111-1111-111111111111")]
    assert sellados == ["22222222-2222-2222-2222-222222222222"]

    # En informe_publico: activo oculta el 'void'; cerrado lo conserva por trazabilidad.
    monkeypatch.setattr(ed, "query", lambda sql, params=(): [reto])
    monkeypatch.setattr(ed, "vencido", lambda r, now=None: False)
    inf_vivo = ed.informe_publico()
    assert inf_vivo["actuales"][0]["pasos"] == []
    assert inf_vivo["actuales"][0]["estado"] == "en_curso"
    monkeypatch.setattr(ed, "vencido", lambda r, now=None: True)
    inf_hist = ed.informe_publico()
    assert len(inf_hist["historial"][0]["pasos"]) == 1 and inf_hist["historial"][0]["pasos"][0]["outcome"] == "void"
