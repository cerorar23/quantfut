"""/alta-probabilidad es público y no expone nada privado."""
from fastapi.testclient import TestClient

INFORME = {"estado": "activa", "motivos": [], "historial": {"n": 0},
           "proximos": [{"match_id": "m1", "texto": "Cruzeiro o empate", "prob": 0.87}]}


def _client(monkeypatch):
    from qf.api import main
    from qf.publish import alta_prob_datos
    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *_a: False)
    monkeypatch.setattr(alta_prob_datos, "informe_publico", lambda: INFORME)
    from qf.api import mobile
    from datetime import datetime, timedelta, timezone
    monkeypatch.setattr(mobile, 'features', lambda: {key: {'enabled': True} for key in mobile.SECTIONS})
    monkeypatch.setattr(mobile, 'high_rows', lambda: [{**INFORME['proximos'][0], 'kickoff_utc': datetime.now(timezone.utc)+timedelta(days=1), 'ref_price':1.4, 'batch_date':'2026-10-11'}])
    monkeypatch.setattr(mobile, 'allocations', lambda rows, stream: {'m1'})
    return TestClient(main.app)


def test_publico_sin_token(monkeypatch):
    r = _client(monkeypatch).get("/alta-probabilidad")
    assert r.status_code == 200
    assert r.json()["proximos"][0]["texto"] == "Cruzeiro o empate"


def test_tarjeta_del_panel_sin_lista(monkeypatch):
    from qf.api import console
    from qf.publish import alta_prob_datos
    monkeypatch.setattr(alta_prob_datos, "informe_publico", lambda: INFORME)
    card = console._alta_card()
    assert card["estado"] == "activa" and "proximos" not in card
    assert card["proximos_sellados"] == 1


def test_la_ruta_publica_no_envia_la_cuota_de_lo_bloqueado_pero_la_app_si(monkeypatch):
    """La web la difumina, así que no viaja; el bloque que lee la app (mobile.high_probability) no cambia."""
    from datetime import datetime, timedelta, timezone
    from qf.api import mobile
    c = _client(monkeypatch)
    soon = datetime.now(timezone.utc) + timedelta(days=1)
    filas = [{"match_id": f"m{i}", "market": "totals", "texto": "x", "prob": 0.87, "ref_price": 1.15 + i / 100,
              "kickoff_utc": soon, "league_id": "gb.premier_league", "local": "A", "visitante": "B"} for i in (1, 2)]
    monkeypatch.setattr(mobile, "high_rows", lambda: filas)
    monkeypatch.setattr(mobile, "allocations", lambda rows, stream: {"m1"})   # m2 queda bloqueado
    web = c.get("/alta-probabilidad").json()
    assert [v["match_id"] for v in web["vip"]] == ["m2"]
    assert "cuota" not in web["vip"][0]
    assert not {"selection", "line", "prob", "ref_price", "fit", "texto"} & web["vip"][0].keys()
    app = mobile.high_probability()
    assert app["vip"][0]["cuota"] == 1.17            # lo que ve la app no cambia


def test_escalera_publica_no_envia_la_cuota_de_lo_bloqueado(monkeypatch):
    from qf.api import mobile
    c = _client(monkeypatch)
    falso = {"activo": True, "actuales": [{"reto_id": 1, "pasos": [{"paso": 1}],
             "vip": [{"match_id": "m2", "locked": True, "pick_key": "1:2", "cuota": 1.3}]}]}
    monkeypatch.setattr(mobile, "ladder", lambda *a, **k: falso)
    web = c.get("/escalera").json()
    assert web["actuales"][0]["vip"] == [{"match_id": "m2", "locked": True, "pick_key": "1:2"}]
    assert web["actuales"][0]["pasos"] == [{"paso": 1}]


def test_el_publico_de_la_web_ve_un_solo_gratis_y_la_app_conserva_sus_cuatro(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from qf.api import mobile
    c = _client(monkeypatch)
    soon = datetime.now(timezone.utc) + timedelta(days=1)
    probs = {"m1": 0.80, "m2": 0.91, "m3": 0.85, "m4": 0.78}
    filas = [{"match_id": k, "market": "totals", "texto": f"t{k}", "selection": "over", "line": 2.5, "prob": p, "ref_price": 1.2,
              "kickoff_utc": soon, "league_id": "gb.premier_league", "local": "A", "visitante": "B"} for k, p in probs.items()]
    monkeypatch.setattr(mobile, "high_rows", lambda: filas)
    monkeypatch.setattr(mobile, "allocations", lambda rows, stream: set(probs))      # los cuatro son gratis
    web = c.get("/alta-probabilidad").json()
    assert [p["match_id"] for p in web["proximos"]] == ["m2"]                         # queda el de mayor probabilidad
    assert sorted(v["match_id"] for v in web["vip"]) == ["m1", "m3", "m4"]
    for v in web["vip"]:
        assert v["locked"] is True
        assert not {"cuota", "texto", "selection", "line", "prob", "ref_price", "fit"} & v.keys()
    assert len(mobile.high_probability()["proximos"]) == 4                            # la app no cambia


def _como_vip(monkeypatch):
    from qf.api import main
    c = _client(monkeypatch)
    main.app.dependency_overrides[main.member] = lambda: True
    return c, main


def test_la_cuenta_vip_ve_todos_los_pronosticos_en_la_web(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from qf.api import mobile
    c, main = _como_vip(monkeypatch)
    try:
        soon = datetime.now(timezone.utc) + timedelta(days=1)
        probs = {"m1": 0.80, "m2": 0.91, "m3": 0.85, "m4": 0.78}
        filas = [{"match_id": k, "market": "totals", "texto": f"t{k}", "selection": "over", "line": 2.5, "prob": p, "ref_price": 1.2,
                  "kickoff_utc": soon, "league_id": "gb.premier_league", "local": "A", "visitante": "B"} for k, p in probs.items()]
        monkeypatch.setattr(mobile, "high_rows", lambda: filas)
        monkeypatch.setattr(mobile, "allocations", lambda rows, stream: {"m1"})     # solo uno gratis; los otros tres, VIP
        r = c.get("/alta-probabilidad")
        vip = r.json()
        assert sorted(p["match_id"] for p in vip["proximos"]) == ["m1", "m2", "m3", "m4"]      # todos desbloqueados
        assert vip["vip"] == [] and all(p["locked"] is False for p in vip["proximos"])
        assert r.headers["cache-control"] == "no-store" and "Authorization" in r.headers["vary"]
    finally:
        main.app.dependency_overrides.clear()
    # y sin sesión sigue viéndose uno solo: lo de arriba no abrió nada al público
    publico = c.get("/alta-probabilidad").json()
    assert len(publico["proximos"]) == 1 and len(publico["vip"]) == 3


def test_la_cuenta_vip_ve_toda_la_escalera_y_el_visitante_no_la_cuota(monkeypatch):
    from qf.api import mobile
    c, main = _como_vip(monkeypatch)
    llamadas = []

    def falso(plus=False, unlocks=None):
        llamadas.append(plus)
        return {"activo": True, "actuales": [{"reto_id": 1, "pasos": [{"paso": 1}, {"paso": 2}] if plus else [{"paso": 1}],
                "vip": [] if plus else [{"match_id": "m2", "locked": True, "cuota": 1.3}]}]}
    monkeypatch.setattr(mobile, "ladder", falso)
    try:
        assert [p["paso"] for p in c.get("/escalera").json()["actuales"][0]["pasos"]] == [1, 2]
    finally:
        main.app.dependency_overrides.clear()
    assert c.get("/escalera").json()["actuales"][0]["vip"] == [{"match_id": "m2", "locked": True}]
    assert llamadas == [True, False]
