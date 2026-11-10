"""Medición de mercados nuevos de NBA y tenis: contratos, calibradores y partición."""
import numpy as np

from qf.eval import mercados_nuevos as mn
from qf.publish import referencia


def _f(casa, mercado, nombre, precio, res, punto=None, desc="", periodo=None):
    return dict(bookmaker=casa, market=mercado, period=periodo, team=None, name=nombre, description=desc,
                point=punto, price_american=precio, resolution=res)


def _regs(filas, deporte="nba"):
    return mn.registros(filas, deporte, "e1", "2026-11-01", soft_books={"bet365"}, preferida="pinnacle",
                        excluidas={"prizepicks"}, probabilidades=referencia.probabilidades)


def test_el_handicap_empareja_lineas_opuestas_y_descarta_enteras_y_dfs():
    filas = [_f(c, "spreads", "Hawks", -110, "lost", -4.5) for c in ("bet365", "pinnacle", "prizepicks")]
    filas += [_f(c, "spreads", "Pacers", -110, "won", 4.5) for c in ("bet365", "pinnacle", "prizepicks")]
    filas += [_f("bet365", "spreads", "Hawks", -120, "push", -4.0), _f("bet365", "spreads", "Pacers", 100, "push", 4.0)]
    c = mn.contratos(filas, {"prizepicks"})
    assert list(c) == [("spreads", "", "", "", "Hawks", -4.5)]
    assert set(c[("spreads", "", "", "", "Hawks", -4.5)]["casas"]) == {"bet365", "pinnacle"}


def test_registros_dan_los_dos_lados_con_probabilidades_que_suman_uno():
    filas = []
    for casa, over, under in (("bet365", -150, 120), ("pinnacle", -145, 125)):
        filas += [_f(casa, "player_steals", "Over", over, "won", 0.5, "Jugador"),
                  _f(casa, "player_steals", "Under", under, "lost", 0.5, "Jugador")]
    a, b = _regs(filas)
    assert (a["lado"], a["gana"], b["gana"]) == ("Over", 1, 0)
    assert abs(a["p"] + b["p"] - 1) < 1e-4 and a["p"] > 0.5
    assert a["cuota"] == 1 + 100 / 150 and a["cuota_todas"] == 1 + 100 / 145 and a["pinnacle"] == 1


def test_no_entra_lo_devuelto_lo_incoherente_una_sola_casa_ni_el_ganador_de_tenis():
    par = lambda casa, r1, r2, mk="totals": [_f(casa, mk, "Over", -110, r1, 21.5), _f(casa, mk, "Under", -110, r2, 21.5)]
    assert _regs(par("bet365", "void", "void") + par("pinnacle", "void", "void")) == []
    assert _regs(par("bet365", "won", "won") + par("pinnacle", "won", "won")) == []
    assert _regs(par("bet365", "won", "lost")) == []
    h2h = [_f(c, "h2h", n, -110, r) for c in ("bet365", "pinnacle") for n, r in (("Ana", "won"), ("Bea", "lost"))]
    assert _regs(h2h, "tenis") == [] and len(_regs(h2h, "nba")) == 2


def test_beta_corrige_una_distorsion_conocida_y_no_estropea_lo_calibrado():
    rng = np.random.default_rng(3)
    real = rng.uniform(0.1, 0.9, 40_000)
    y = (rng.random(len(real)) < real).astype(float)
    dicho = mn.beta_aplicar((1.6, 1.6, 0.0), real)            # exagera los extremos
    cal = mn.beta_aplicar(mn.beta_ajustar(dicho[:30_000], y[:30_000]), dicho[30_000:])
    assert mn.logloss(cal, y[30_000:]).mean() < mn.logloss(dicho[30_000:], y[30_000:]).mean() - 0.005
    assert np.abs(cal - real[30_000:]).mean() < 0.015
    igual = mn.beta_aplicar(mn.beta_ajustar(real[:30_000], y[:30_000]), real[30_000:])
    assert np.abs(igual - real[30_000:]).mean() < 0.015


def test_venn_abers_da_un_intervalo_ordenado_que_contiene_el_punto():
    rng = np.random.default_rng(5)
    p = rng.uniform(0.2, 0.9, 6_000)
    y = (rng.random(len(p)) < p).astype(float)
    nuevo = np.array([0.3, 0.5, 0.7, 0.85])
    p0, p1 = mn.venn_abers(p, y, nuevo)
    punto = mn.venn_abers_punto(p0, p1)
    assert (p0 <= p1).all() and (p0 <= punto).all() and (punto <= p1).all()
    assert np.abs(punto - nuevo).max() < 0.06 and (np.diff(punto) >= 0).all()


def test_bloques_respetan_el_embargo_y_la_ventana_crece():
    fechas = np.repeat(np.arange("2026-10-24", "2026-11-10", dtype="datetime64[D]"), 4)
    partes = mn.bloques(fechas, n_bloques=4, embargo_dias=1, dias_min_entreno=5)
    assert len(partes) == 4
    previo = 0
    for train, test in partes:
        assert not (train & test).any()
        assert fechas[train].max() < fechas[test].min() - np.timedelta64(1, "D")
        assert train.sum() > previo
        previo = train.sum()
    assert mn.bloques(fechas[:8]) == []


def test_el_intervalo_remuestrea_eventos_no_filas():
    rng = np.random.default_rng(9)
    ev = np.repeat(np.arange(60), 5)
    v = np.repeat(rng.normal(0.02, 0.2, 60), 5)                # dentro de un evento todo es igual
    media, lo, hi = mn.ic_por_evento(v, ev)
    assert lo < media < hi
    _, lo2, hi2 = mn.ic_por_evento(np.tile(v, 3), np.tile(ev, 3))   # triplicar filas no da información
    assert abs((hi2 - lo2) - (hi - lo)) < 1e-9


def test_medir_sobre_un_csv_pequeno(tmp_path):
    import csv, gzip
    rng = np.random.default_rng(1)
    ruta = tmp_path / "m.csv.gz"
    with gzip.open(ruta, "wt", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, mn.CAMPOS)
        w.writeheader()
        for e in range(120):
            fecha = np.datetime64("2026-10-24") + e // 8
            for _ in range(30):
                p = float(rng.uniform(0.55, 0.9))
                w.writerow(dict(deporte="nba", evento=f"e{e}", fecha=str(fecha), mercado="player_steals", periodo="",
                                sujeto="x", linea=0.5, lado="Over", p=round(p, 5), casas=3, pinnacle=1,
                                cuota=round(0.95 / p, 3), cuota_todas=round(0.97 / p, 3), gana=int(rng.random() < p)))
    r = mn.medir(str(ruta))
    esc = next(b for b in r["bandas"] if b["banda"] == "escalera")
    assert esc["eventos"] > 100 and abs(esc["hueco"]) < 0.05 and esc["hueco_ic"][0] < esc["hueco"] < esc["hueco_ic"][1]
    cal = r["calibradores"][0]
    assert cal["familia"] == "player_steals" and abs(cal["beta"]["delta_logloss"]) < 0.02
