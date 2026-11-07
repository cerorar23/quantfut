import math
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from qf.config import settings
from qf.model.devig import consensus_devig, devig
from qf.publish import alta_prob_datos as ad
from qf.publish import escalera_datos as ed
from qf.publish import picks as pk
from qf.publish import referencia as rf

NOW = datetime(2026, 11, 6, 9, 35, tzinfo=timezone.utc)
SEL = ("home", "draw", "away")


def test_consenso_sin_pinnacle_pesa_igual_y_exige_dos_casas():
    q = {"bet365": {"home": 1.50, "draw": 4.2, "away": 6.0}, "betano": {"home": 1.55, "draw": 4.0, "away": 5.5}}
    p, meta = rf.probabilidades(q, SEL, preferida="pinnacle")
    esperado = consensus_devig(q, settings.devig_method)
    assert all(math.isclose(p[s], esperado[s]) for s in SEL) and math.isclose(sum(p.values()), 1.0)
    assert meta == {"casas": 2, "referencia": "consenso"}
    assert rf.probabilidades({"bet365": q["bet365"]}, SEL, preferida="pinnacle") is None


def test_pinnacle_cotizando_conserva_su_peso_y_vale_sola():
    pin = {"home": 1.50, "draw": 4.2, "away": 6.0}
    sola, meta = rf.probabilidades({"pinnacle": pin}, SEL, preferida="pinnacle")
    assert meta["referencia"] == "preferida"
    assert all(math.isclose(sola[s], v) for s, v in zip(SEL, devig([pin[s] for s in SEL], settings.devig_method)))
    con_otra, _ = rf.probabilidades({"pinnacle": pin, "bet365": {"home": 1.7, "draw": 3.8, "away": 5.0}}, SEL,
                                    preferida="pinnacle")
    assert con_otra["home"] != sola["home"]


def test_casas_con_el_mercado_a_medias_o_cuota_invalida_no_cuentan():
    q = {"a": {"home": 1.5, "away": 2.6}, "b": {"home": 1.6}, "c": {"home": 1.5, "away": 1.0},
         "d": {"home": 1.55, "away": 2.5}}
    p, meta = rf.probabilidades(q, ("home", "away"))
    assert meta["casas"] == 2 and math.isclose(sum(p.values()), 1.0)


def _snap(books, minutos=30):
    return pk.Snapshot("the_odds_api", NOW - timedelta(minutes=minutos), books)


SIN_PINNACLE = {"bet365": {"home": 1.50, "draw": 4.2, "away": 6.0},
                "betano": {"home": 1.55, "draw": 4.0, "away": 5.5}}


def test_snapshot_sin_pinnacle_solo_entra_con_consenso(monkeypatch):
    snap = _snap(SIN_PINNACLE)
    monkeypatch.setattr(ad, "_capturas", lambda m, now: [snap])
    kick = NOW + timedelta(hours=5)
    assert ad._snapshot("m", kick, NOW) is None                       # alta probabilidad y escalera: igual que antes
    assert ad._snapshot("m", kick, NOW, consenso=True) is snap
    p = ad.referencia_1x2(snap, consenso=True)
    assert math.isclose(sum(p.values()), 1.0)


def test_referencia_1x2_por_defecto_sigue_siendo_pinnacle():
    pin = {"home": 1.50, "draw": 4.2, "away": 6.0}
    snap = _snap({"pinnacle": pin, "bet365": SIN_PINNACLE["bet365"]})
    p = ad.referencia_1x2(snap)
    esperado = devig([pin[s] for s in SEL], settings.devig_method)
    assert all(math.isclose(p[s], float(v)) for s, v in zip(SEL, esperado))


def test_linea_de_goles_por_consenso_y_por_defecto_solo_pinnacle():
    filas = [dict(bookmaker=b, selection=s, line=2.5, price=pr)
             for b, (o, u) in {"bet365": (1.85, 2.0), "betano": (1.9, 1.95)}.items()
             for s, pr in (("over", o), ("under", u))]
    assert ad.linea_pinnacle(filas) is None
    linea, p_over = ad.linea_pinnacle(filas, consenso=True)
    assert linea == 2.5 and 0.4 < p_over < 0.6


def test_opciones_de_futbol_sin_pinnacle_solo_con_consenso(monkeypatch):
    snap = _snap(SIN_PINNACLE)
    monkeypatch.setattr(ad, "_capturas", lambda m, now: [snap])
    monkeypatch.setattr(ad, "_referencias", lambda m, sn, now: ([], []))
    monkeypatch.setattr(ed, "_cuotas_mercados", lambda m, now: [])
    monkeypatch.setattr(ad, "settings", replace(ad.settings, soft_books=("bet365", "betano")))
    monkeypatch.setattr(ed, "settings", replace(ed.settings, soft_books=("bet365", "betano")))
    m = {"match_id": "m", "kickoff_utc": NOW + timedelta(hours=5)}
    assert ed.opciones(m, NOW, None) is None
    ops = ed.opciones(m, NOW, None, consenso=True)
    h2h = {o.cand.selection: o for o in ops if o.cand.market == "h2h"}
    assert set(h2h) == {"home", "draw", "away"} and h2h["home"].price == 1.55 and h2h["home"].book == "betano"
    assert math.isclose(sum(o.cand.prob for o in h2h.values()), 1.0)
