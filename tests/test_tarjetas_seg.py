"""Seguimiento sin publicar de tarjetas: guardar, sellar, liquidar y no publicar nunca."""
import re
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from qf.config import settings
from qf.eval import calibracion_mercados as cm
from qf.model import estadisticas_mercado as em
from qf.publish import daily, hashchain
from qf.publish import escalera_datos as ed
from qf.publish import tarjetas_seg as ts

ROOT = Path(__file__).resolve().parents[1]
AHORA = datetime(2026, 10, 15, 8, 0, tzinfo=timezone.utc)
PARTIDO = {"match_id": "m1", "kickoff_utc": AHORA + timedelta(hours=10), "league_id": "us.mls",
           "home_team_id": "h", "away_team_id": "a", "referee": "R"}


# --- Esquema ---------------------------------------------------------------------

def test_migracion_inmutable_solo_tarjetas_y_sin_nulos_en_el_resultado():
    sql = (ROOT / "db" / "068_tarjetas_seguimiento.sql").read_text(encoding="utf-8")
    assert "market = 'cards'" in sql and "ref_price    REAL NOT NULL" in sql
    for tabla in ("tarjetas_seg", "tarjetas_seg_results"):
        assert re.search(rf"BEFORE UPDATE OR DELETE ON {tabla}\s+FOR EACH ROW EXECUTE FUNCTION deny_mutation", sql)
    assert "(outcome = 'void') = (home_goals IS NULL)" in sql
    assert "tarjetas_seg_uq UNIQUE (match_id, market, selection, line)" in sql


def test_ninguna_ruta_publica_lee_el_seguimiento():
    """Ni la API ni el panel ni el frontend ni la app mencionan la tabla: no se publica."""
    for carpeta in ("src/qf/api", "frontend", "apps/mobile/lib"):
        for f in (ROOT / carpeta).rglob("*"):
            if f.is_file() and f.suffix in (".py", ".js", ".html", ".dart", ".mjs"):
                assert "tarjetas_seg" not in f.read_text(encoding="utf-8", errors="ignore"), f


# --- Lote sellado ----------------------------------------------------------------

def test_el_lote_lleva_el_bloque_solo_desde_su_fecha(monkeypatch):
    llamadas = []
    monkeypatch.setattr(hashchain, "query", lambda sql, params=(): llamadas.append(sql) or
                        ([{"seg_id": "s1"}] if "tarjetas_seg" in sql else []))
    monkeypatch.setattr(hashchain, "LOTE_TARJETAS_DESDE", None)
    assert "tarjetas_seg" not in hashchain._collect(date(2026, 10, 15))
    assert not any("tarjetas_seg" in s for s in llamadas)
    monkeypatch.setattr(hashchain, "LOTE_TARJETAS_DESDE", date(2026, 10, 15))
    assert "tarjetas_seg" not in hashchain._collect(date(2026, 10, 14))      # lotes anteriores no cambian
    p = hashchain._collect(date(2026, 10, 15))
    assert p["tarjetas_seg"] == [{"seg_id": "s1"}] and p["n_tarjetas_seg"] == 1


def test_el_corte_por_defecto_es_el_primer_lote_sin_sellar():
    assert not hashchain.lote_lleva_tarjetas(date(2026, 10, 14))
    assert hashchain.lote_lleva_tarjetas(date(2026, 10, 15))


# --- Candidatos ------------------------------------------------------------------

class _Acc:
    def lambdas(self, now, home, away, referee=None):
        return (2.3, 2.5)


class _Modelos:
    def __init__(self, acc=_Acc()):
        self.acc = acc

    def de(self, liga, mercado):
        assert mercado == "cards"
        return self.acc


def _filas(*lineas):
    """Cuotas de tarjetas de Pinnacle (referencia, los dos lados) y de Betano (la tomable)."""
    out = []
    for linea, (u_pin, o_pin, u_soft) in lineas:
        for casa, lado, precio in (("pinnacle", "under", u_pin), ("pinnacle", "over", o_pin),
                                   ("betano", "under", u_soft), ("betano", "over", 2.2)):
            out.append({"bookmaker": casa, "market": "cards", "selection": lado, "line": linea,
                        "price": precio, "provider_updated_at": AHORA - timedelta(hours=1)})
    return out


def test_un_candidato_por_linea_con_los_dos_lados_cotizados_y_cuota_de_la_lista():
    filas = _filas((4.5, (3.0, 1.40, 3.2)), (5.5, (1.9, 1.95, 2.0)))
    cands = ts.candidatos(PARTIDO, AHORA, _Modelos(), filas)
    por_linea = {(c["selection"], c["line"]): c for c in cands}
    assert set(por_linea) == {("under", 4.5), ("under", 5.5), ("over", 4.5), ("over", 5.5)}   # 6,5 sin cuotas: no entra
    c = por_linea[("under", 5.5)]
    assert c["ref_book"] == "betano" and c["ref_price"] == 2.0
    assert c["prob"] <= c["fit"]["modelo"] and c["prob"] <= c["fit"]["mercado"]   # la menor de las dos
    assert c["fit"]["lambdas"] == [2.3, 2.5]


def test_se_miden_tambien_las_lineas_de_mas_de_sin_habilitarlas():
    cands = ts.candidatos(PARTIDO, AHORA, _Modelos(), _filas((4.5, (1.9, 1.95, 2.0)), (3.5, (3.0, 1.4, 3.2))))
    assert {(c["selection"], c["line"]) for c in cands} >= {("over", 4.5), ("under", 4.5), ("over", 3.5)}
    assert ("over", 4.5) not in em.LINEAS_HABILITADAS["cards"]        # medir no es habilitar
    assert set(em.LINEAS_HABILITADAS["cards"]) <= set(ts.LINEAS_SEGUIMIENTO)


def test_sin_modelo_o_sin_cuota_de_la_lista_no_hay_candidato():
    assert ts.candidatos(PARTIDO, AHORA, _Modelos(None), _filas((5.5, (1.9, 1.95, 2.0)))) == []
    solo_pinnacle = [f for f in _filas((5.5, (1.9, 1.95, 2.0))) if f["bookmaker"] == "pinnacle"]
    assert ts.candidatos(PARTIDO, AHORA, _Modelos(), solo_pinnacle) == []   # nadie de la lista la da


# --- Guardar ----------------------------------------------------------------------

@pytest.fixture
def encendido(monkeypatch):
    monkeypatch.setattr(ts, "settings", replace(settings, tarjetas_seg_enabled=True))
    monkeypatch.setattr(hashchain, "LOTE_TARJETAS_DESDE", date(2026, 10, 15))
    monkeypatch.setattr(ts.ad, "_lote_sellado", lambda dia: False)
    monkeypatch.setattr(ts, "_partidos", lambda now: [PARTIDO])
    monkeypatch.setattr(ed, "Modelos", lambda now: _Modelos())
    monkeypatch.setattr(ed, "_cuotas_af", lambda mid, now: _filas((5.5, (1.9, 1.95, 2.0))))


def test_apagado_sin_corte_o_lote_sellado_no_guarda_nada(monkeypatch, encendido):
    monkeypatch.setattr(ts, "execute", lambda *a: pytest.fail("no debe escribir"))
    monkeypatch.setattr(ts, "settings", replace(settings, tarjetas_seg_enabled=False))
    assert ts.select_and_persist(AHORA)["estado"] == "desactivado"
    monkeypatch.setattr(ts, "settings", replace(settings, tarjetas_seg_enabled=True))
    monkeypatch.setattr(hashchain, "LOTE_TARJETAS_DESDE", None)
    assert ts.select_and_persist(AHORA)["estado"] == "sin_corte"
    monkeypatch.setattr(hashchain, "LOTE_TARJETAS_DESDE", date(2026, 10, 15))
    monkeypatch.setattr(ts.ad, "_lote_sellado", lambda dia: True)
    assert ts.select_and_persist(AHORA)["estado"] == "lote_sellado"


def test_guarda_cada_candidato_con_su_cuota_y_el_ajuste(monkeypatch, encendido):
    filas = []
    monkeypatch.setattr(ts, "execute", lambda sql, params: filas.append((sql, params)) or 1)
    out = ts.select_and_persist(AHORA)
    assert out["guardados"] == 2 and out["partidos"] == 1                   # menos de y más de 5,5
    sql, p = next(f for f in filas if f[1][2] == "under")
    assert "INSERT INTO tarjetas_seg" in sql and "ON CONFLICT ON CONSTRAINT tarjetas_seg_uq" in sql
    assert p[:4] == ("m1", "cards", "under", 5.5) and p[7] == "betano" and p[8] == "api_football"
    assert p[6] == 2.0 and 0 < p[4] < 1 and abs(p[5] - 1 / p[4]) < 1e-3


def test_el_ensayo_no_escribe(monkeypatch, encendido):
    monkeypatch.setattr(ts, "execute", lambda *a: pytest.fail("el ensayo no escribe"))
    out = ts.select_and_persist(AHORA, dry_run=True)
    assert out["decisiones"][0]["selection"] == "under" and out["guardados"] == 0


# --- Liquidar ----------------------------------------------------------------------

def _fila(total_amarillas, rojas=0, linea=5.5, lado="under", estado="finished"):
    return {"seg_id": "s1", "market": "cards", "selection": lado, "line": linea, "status": estado,
            "kickoff_utc": AHORA - timedelta(hours=5), "home_goals": 1, "away_goals": 0,
            "home_corners": None, "away_corners": None, "home_yellow": total_amarillas,
            "away_yellow": 0, "home_red": rojas, "away_red": 0}


def test_liquida_con_amarillas_mas_rojas(monkeypatch):
    inserts = []
    monkeypatch.setattr(ts, "query", lambda sql, params=(): [_fila(4, rojas=1), _fila(7)])
    monkeypatch.setattr(ts, "execute", lambda sql, params: inserts.append(params) or 1)
    assert ts.settle_pending(AHORA)["settled"] == 2
    assert inserts[0][1:] == ("win", 1, 0, 5)           # 4 + 1 roja = 5 tarjetas, menos de 5,5
    assert inserts[1][1:] == ("loss", 1, 0, 7)


def test_sin_estadisticas_espera_y_pasado_el_margen_queda_nulo(monkeypatch):
    inserts = []
    sin = {**_fila(0), "home_yellow": None, "away_yellow": None}
    monkeypatch.setattr(ts, "execute", lambda sql, params: inserts.append(params) or 1)
    monkeypatch.setattr(ts, "query", lambda sql, params=(): [{**sin, "kickoff_utc": AHORA - timedelta(hours=5)}])
    assert ts.settle_pending(AHORA)["settled"] == 0
    monkeypatch.setattr(ts, "query", lambda sql, params=(): [{**sin, "kickoff_utc": AHORA - timedelta(hours=80)}])
    assert ts.settle_pending(AHORA)["settled"] == 1 and inserts[0][1:] == ("void", None, None, None)


# --- Job diario -------------------------------------------------------------------

def test_el_job_guarda_antes_de_sellar_y_un_fallo_no_lo_rompe(monkeypatch):
    alertas = []
    monkeypatch.setattr(daily.tg, "alert", alertas.append)
    monkeypatch.setattr(daily, "settings", replace(settings, tarjetas_seg_enabled=False))
    assert daily._tarjetas_seg()["estado"] == "desactivado"
    monkeypatch.setattr(daily, "settings", replace(settings, tarjetas_seg_enabled=True))
    monkeypatch.setattr(daily.tarjetas_seg, "select_and_persist", lambda: {"guardados": 3})
    assert daily._tarjetas_seg()["guardados"] == 3

    def falla():
        raise RuntimeError("base caída")
    monkeypatch.setattr(daily.tarjetas_seg, "select_and_persist", falla)
    assert "base caída" in daily._tarjetas_seg()["error"] and "tarjetas" in alertas[0]


def test_en_run_se_llama_antes_de_seal(monkeypatch):
    orden = []
    monkeypatch.setattr(daily, "generate_predictions",
                        lambda: [{"match_id": "m1", "confidence_tier": "high", "teams": ("A", "B")}])
    monkeypatch.setattr(daily, "_sharp_only_upcoming", lambda hours=36: [])
    monkeypatch.setattr(daily, "seal", lambda: orden.append("seal") or {"chain_sha256": "ab" * 32})
    monkeypatch.setattr(daily, "_tarjetas_seg", lambda: orden.append("tarjetas") or {})
    monkeypatch.setattr(daily.tg, "alert", lambda m: None)
    daily.run()
    assert orden == ["tarjetas", "seal"]


# --- Informe de calibración --------------------------------------------------------

def _f(fuente, match, outcome, prob=0.8, market="cards", sel="under", line=5.5):
    return {"fuente": fuente, "match_id": match, "market": market, "selection": sel,
            "line": line, "prob": prob, "outcome": outcome}


def test_wilson_contiene_la_proporcion_y_se_estrecha_con_n():
    lo, hi = cm.wilson(40, 50)
    assert lo < 0.8 < hi and hi - lo < 0.25
    assert cm.wilson(400, 500)[1] - cm.wilson(400, 500)[0] < hi - lo
    assert cm.wilson(0, 0) == (0.0, 1.0)


def test_un_mismo_pronostico_en_varias_fuentes_cuenta_una_vez_y_los_nulos_no():
    filas = [_f("parley", "m1", "win"), _f("tarjetas_seg", "m1", "win"),      # el mismo pronóstico
             _f("tarjetas_seg", "m2", "loss"), _f("tarjetas_seg", "m3", "void"),
             _f("alta_ext", "m4", "push", market="corners")]
    inf = cm.resumir(filas)
    t = inf["mercados"]["cards"]
    assert t["n"] == 2 and t["aciertos"] == 1                                  # m1 una vez, m2; sin el nulo
    assert "corners" not in inf["mercados"]                                    # push no cuenta
    assert t["fuentes"]["parley"]["n"] == 1 and t["fuentes"]["tarjetas_seg"]["n"] == 2   # el desglose no deduplica


def test_el_veredicto_exige_muestra_y_compara_el_prometido_con_el_ic():
    poca = cm.resumir([_f("alta_ext", f"m{i}", "loss") for i in range(10)])
    assert poca["mercados"]["cards"]["veredicto"] == "muestra insuficiente"
    mal = cm.resumir([_f("alta_ext", f"m{i}", "win" if i < 30 else "loss", prob=0.82) for i in range(100)])
    b = mal["mercados"]["cards"]
    assert (b["n"], b["real"], b["prometido"]) == (100, 30.0, 82.0)
    assert b["veredicto"] == "por debajo de lo prometido" and b["diferencia_pts"] == -52.0
    bien = cm.resumir([_f("alta_ext", f"m{i}", "win" if i < 80 else "loss") for i in range(100)])
    assert bien["mercados"]["cards"]["veredicto"] == "dentro de lo prometido"
    mejor = cm.resumir([_f("alta_ext", f"m{i}", "win" if i < 95 else "loss", prob=0.7) for i in range(100)])
    assert mejor["mercados"]["cards"]["veredicto"] == "por encima de lo prometido"


def test_el_informe_lee_solo_filas_selladas_y_liquidadas(monkeypatch):
    sqls = []
    monkeypatch.setattr(cm, "query", lambda sql, params=(): sqls.append(sql) or [])
    assert cm.informe()["mercados"] == {}
    assert len(sqls) == 5
    for sql in sqls:
        assert "JOIN prediction_batches b" in sql and "decided_at <= b.created_at" in sql
        assert "r.outcome IN ('win', 'loss')" in sql
