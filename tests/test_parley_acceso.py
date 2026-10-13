"""Reparto gratis/VIP de los parlays: uno gratis al día, los liquidados siempre abiertos."""
from qf.api.parley_acceso import aplicar_acceso

REGLAS = {"escalones": [{"escalon": e, "cuota_min": lo, "cuota_max": hi} for e, lo, hi in
                        ((1, 1.9, 2.2), (2, 2.2, 2.7), (3, 2.7, 3.4), (4, 3.4, 4.3), (5, 4.3, 5.0))]}


def _t(escalon, outcome=None):
    return {"escalon": escalon, "cuota_total": 2.01 + escalon, "prob_total": .5 / escalon, "n_patas": 2,
            "outcome": outcome, "factor_pago": None,
            "patas": [{"match_id": f"m{escalon}", "texto": "Más de 1,5 goles", "price": 1.4, "prob": .8}]}


def informe(*dias):
    return {"activo": True, "reglas": REGLAS, "resumen": {"total": {"n": 3}}, "control": {"pausados": []},
            "dias": [{"dia": d, "chain_sha256": "abc", "tickets": ts} for d, ts in dias]}


def test_sin_vip_solo_el_escalon_1_abierto_y_el_resto_sin_nada():
    out = aplicar_acceso(informe(("2026-10-13", [_t(1), _t(2), _t(5)])), plus=False)
    t1, t2, t5 = out["dias"][0]["tickets"]
    assert t1["locked"] is False and t1["gratis"] is True and t1["patas"]
    for t, rango in ((t2, (2.2, 2.7)), (t5, (4.3, 5.0))):
        assert t == {"escalon": t["escalon"], "locked": True, "cuota_min": rango[0], "cuota_max": rango[1]}


def test_si_no_hay_escalon_1_el_gratis_es_el_de_menor_escalon():
    out = aplicar_acceso(informe(("2026-10-13", [_t(3), _t(4)])), plus=False)
    t3, t4 = out["dias"][0]["tickets"]
    assert t3["locked"] is False and t3["gratis"] and t4["locked"] is True


def test_un_unico_parley_en_el_dia_no_es_gratis():
    out = aplicar_acceso(informe(("2026-10-13", [_t(1)])), plus=False)
    assert out["dias"][0]["tickets"] == [{"escalon": 1, "locked": True, "cuota_min": 1.9, "cuota_max": 2.2}]
    vip = aplicar_acceso(informe(("2026-10-13", [_t(1)])), plus=True)["dias"][0]["tickets"][0]
    assert not vip["locked"] and vip["gratis"] is False


def test_vip_ve_todo_y_solo_uno_figura_como_gratis():
    out = aplicar_acceso(informe(("2026-10-13", [_t(1), _t(2)])), plus=True)
    t1, t2 = out["dias"][0]["tickets"]
    assert not t1["locked"] and not t2["locked"] and t1["gratis"] and not t2["gratis"]
    assert out["acceso"]["plus"] is True


def test_los_liquidados_se_ven_siempre_aunque_fueran_vip():
    out = aplicar_acceso(informe(("2026-10-12", [_t(1, "ganado"), _t(2, "perdido"), _t(3, "nulo")])), plus=False)
    assert all(not t["locked"] and t["patas"] for t in out["dias"][0]["tickets"])


def test_lo_pendiente_de_hoy_sigue_cerrado_y_el_historial_abierto():
    out = aplicar_acceso(informe(("2026-10-13", [_t(1), _t(2)]), ("2026-10-12", [_t(1, "ganado"), _t(2, "perdido")])),
                         plus=False)
    hoy, ayer = out["dias"]
    assert [t["locked"] for t in hoy["tickets"]] == [False, True]
    assert [t["locked"] for t in ayer["tickets"]] == [False, False]


def test_el_resto_del_informe_no_se_toca_y_un_ticket_bloqueado_no_filtra_nada():
    base = informe(("2026-10-13", [_t(1), _t(4)]))
    out = aplicar_acceso(base, plus=False)
    assert out["reglas"] == REGLAS and out["resumen"] == base["resumen"] and out["control"] == base["control"]
    bloqueado = out["dias"][0]["tickets"][1]
    assert set(bloqueado) == {"escalon", "locked", "cuota_min", "cuota_max"}
    assert aplicar_acceso({"activo": False, "reglas": REGLAS, "dias": []}, False)["dias"] == []
