"""Parley del día: migración, base de datos, liquidación e informe."""
import re
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from qf.publish import escalera as es
from qf.publish import hashchain
from qf.publish import parley as pl
from qf.publish import parley_datos as pd_
from qf.publish.alta_prob import Candidato
from qf.publish.escalera import Opcion

SQL = Path(__file__).resolve().parents[1] / "db" / "053_parley.sql"


def test_migracion_inmutable_y_con_los_mercados_de_la_escalera():
    t = SQL.read_text(encoding="utf-8")
    for tabla in ("parley_tickets", "parley_patas", "parley_resultados_pata", "parley_resultados"):
        assert f"CREATE TABLE IF NOT EXISTS {tabla}" in t
        assert re.search(rf"BEFORE UPDATE OR DELETE ON {tabla}\s+FOR EACH ROW EXECUTE FUNCTION deny_mutation\(\)", t)
    for m in es.MERCADOS:
        assert f"'{m}'" in t
    assert "double_chance" not in t
    assert "UNIQUE (dia, escalon)" in t and "UNIQUE (ticket_id, match_id)" in t


AHORA = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)


def _o(match, prob=0.7, price=1.4):
    return Opcion(match, Candidato("totals", "over", 1.5, prob), price, "betano", "the_odds_api", AHORA)


@pytest.fixture(autouse=True)
def _sin_bloqueos(monkeypatch):
    """Por defecto ningún mercado bloqueado (no se consulta el control de alta probabilidad)."""
    monkeypatch.setattr(pd_, "mercados_bloqueados", lambda: [])


@pytest.fixture
def encendido(monkeypatch):
    monkeypatch.setattr(pd_, "settings", replace(pd_.settings, parley_enabled=True))
    monkeypatch.setattr(hashchain, "LOTE_PARLEY_DESDE", date(2026, 10, 12))
    monkeypatch.setattr(pd_.ad, "_lote_sellado", lambda dia: False)
    monkeypatch.setattr(pd_, "_liquidados", lambda: [])


def test_apagado_no_elige_nada(monkeypatch):
    monkeypatch.setattr(pd_, "settings", replace(pd_.settings, parley_enabled=False))
    monkeypatch.setattr(pd_, "candidatas", lambda now: pytest.fail("apagado no lee partidos"))
    assert pd_.select_and_persist(AHORA)["estado"] == "desactivado"


def test_sin_corte_de_lote_no_elige(monkeypatch, encendido):
    monkeypatch.setattr(hashchain, "LOTE_PARLEY_DESDE", None)
    assert pd_.select_and_persist(AHORA)["estado"] == "sin_corte"


def test_no_elige_dos_veces_el_mismo_dia(monkeypatch, encendido):
    monkeypatch.setattr(pd_, "query_one", lambda sql, params=(): {"x": 1})
    monkeypatch.setattr(pd_, "candidatas", lambda now: pytest.fail("ya elegido: no se vuelve a buscar"))
    assert pd_.select_and_persist(AHORA)["estado"] == "ya_elegido"


def test_sin_partidos_no_rompe(monkeypatch, encendido):
    monkeypatch.setattr(pd_, "query_one", lambda sql, params=(): None)
    monkeypatch.setattr(pd_, "candidatas", lambda now: ([], 0))
    out = pd_.select_and_persist(AHORA)
    assert out["estado"] == "sin_combinacion" and out["tickets"] == []


class _Cursor:
    def __init__(self, log, ya):
        self.log, self.ya, self._ultimo = log, ya, None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=()):
        self.log.append((sql, params))
        self._ultimo = sql

    def fetchone(self):
        if "FROM parley_tickets WHERE dia" in self._ultimo:
            return {"x": 1} if self.ya else None
        if "INSERT INTO parley_tickets" in self._ultimo:
            return {"ticket_id": f"t{sum('INSERT INTO parley_tickets' in s for s, _ in self.log)}"}
        return None


def _conn_falsa(monkeypatch, ya=False):
    from contextlib import contextmanager
    log, usos = [], []

    @contextmanager
    def conn():
        usos.append(1)
        yield type("C", (), {"cursor": lambda self: _Cursor(log, ya)})()
    monkeypatch.setattr(pd_, "conn", conn)
    return log, usos


def test_elige_y_guarda_todo_en_una_transaccion_con_candado(monkeypatch, encendido):
    monkeypatch.setattr(pd_, "query_one", lambda sql, params=(): None)
    log, usos = _conn_falsa(monkeypatch)
    # a, b: 1,40² = 1,96 (escalón 1) · c, d: 1,60² = 2,56 (escalón 2)
    monkeypatch.setattr(pd_, "candidatas", lambda now: ([_o("a"), _o("b"), _o("c", 0.6, 1.6),
                                                         _o("d", 0.6, 1.6)], 0))
    out = pd_.select_and_persist(AHORA)
    assert out["estado"] == "elegido" and [t["escalon"] for t in out["tickets"]] == [1, 2]
    assert len(usos) == 1                                    # una sola conexión = una transacción
    assert "pg_advisory_xact_lock" in log[0][0]
    assert "FROM parley_tickets WHERE dia" in log[1][0]      # se vuelve a mirar DENTRO del candado
    tickets = [p for s, p in log if "INSERT INTO parley_tickets" in s]
    assert tickets[0][0] == date(2026, 10, 12) and tickets[0][1] == 1
    patas = [(s, p) for s, p in log if "INSERT INTO parley_patas" in s]
    assert len(patas) == 4 and all("kickoff_utc" in s for s, _ in patas)


def test_dos_ejecuciones_a_la_vez_no_duplican(monkeypatch, encendido):
    monkeypatch.setattr(pd_, "query_one", lambda sql, params=(): None)   # la primera mirada no ve nada
    log, _ = _conn_falsa(monkeypatch, ya=True)                          # dentro del candado, ya hay
    monkeypatch.setattr(pd_, "candidatas", lambda now: ([_o("a"), _o("b")], 0))
    assert pd_.select_and_persist(AHORA)["estado"] == "ya_elegido"
    assert not any("INSERT" in s for s, _ in log)


def test_ensayo_no_escribe(monkeypatch):
    monkeypatch.setattr(pd_, "_liquidados", lambda: [])
    monkeypatch.setattr(pd_, "candidatas", lambda now: ([_o("a"), _o("b")], 1))
    monkeypatch.setattr(pd_, "execute", lambda *a: pytest.fail("el ensayo no escribe"))
    monkeypatch.setattr(pd_, "query_one", lambda *a: pytest.fail("el ensayo no escribe"))
    out = pd_.select_and_persist(AHORA, dry_run=True)
    assert out["estado"] == "elegido" and out["sin_precio"] == 1


def _fila_pata(outcome_partido="finished", ko=AHORA, hg=2, ag=1, original=AHORA):
    return {"pata_id": "p1", "market": "totals", "selection": "over", "line": 1.5,
            "status": outcome_partido, "kickoff_utc": ko, "kickoff_original": original,
            "home_goals": hg, "away_goals": ag,
            "home_corners": None, "away_corners": None, "home_yellow": None,
            "away_yellow": None, "home_red": None, "away_red": None}


def test_partido_reprogramado_deja_la_pata_nula_a_las_48_h_de_su_hora_original():
    ahora = AHORA + timedelta(days=3)
    otra_fecha = AHORA + timedelta(days=10)
    assert pd_._resultado_pata(_fila_pata("scheduled", otra_fecha, None, None), ahora)[0] == "void"
    # Jugado días después de su hora original: tampoco cuenta.
    assert pd_._resultado_pata(_fila_pata("finished", AHORA + timedelta(days=5)), AHORA + timedelta(days=6))[0] == "void"
    # Aún dentro del margen y sin jugar: se espera.
    assert pd_._resultado_pata(_fila_pata("scheduled", otra_fecha, None, None), AHORA + timedelta(hours=10)) is None
    # Jugado a su hora: se liquida normal.
    assert pd_._resultado_pata(_fila_pata("finished"), AHORA + timedelta(hours=3))[0] == "win"


def test_aplazado_deja_la_pata_nula_y_liquida_el_ticket(monkeypatch):
    ahora = AHORA + timedelta(days=3)
    escritos = []
    def query(sql, params=()):
        if "r.pata_id IS NULL" in sql:
            return [_fila_pata("postponed", AHORA, None, None)]
        return [{"ticket_id": "t1", "price": 1.4, "prob": 0.7, "outcome": "void"},
                {"ticket_id": "t1", "price": 1.5, "prob": 0.6, "outcome": "win"}]
    monkeypatch.setattr(pd_, "query", query)
    monkeypatch.setattr(pd_, "execute", lambda sql, params=(): escritos.append((sql, params)) or 1)
    out = pd_.settle_pending(ahora)
    assert out == {"patas": 1, "tickets": 1}
    assert escritos[0][1][1] == "void"
    ticket = escritos[1][1]
    assert ticket[0] == "t1" and ticket[1] == "ganado" and abs(ticket[2] - 1.5) < 1e-6


def test_ticket_con_pata_pendiente_no_se_liquida(monkeypatch):
    escritos = []
    monkeypatch.setattr(pd_, "query", lambda sql, params=(): [] if "r.pata_id IS NULL" in sql else
                        [{"ticket_id": "t1", "price": 1.4, "prob": 0.7, "outcome": "win"},
                         {"ticket_id": "t1", "price": 1.5, "prob": 0.6, "outcome": None}])
    monkeypatch.setattr(pd_, "execute", lambda sql, params=(): escritos.append(sql) or 1)
    assert pd_.settle_pending(AHORA) == {"patas": 0, "tickets": 0} and escritos == []


def test_informe_agrupa_por_dia_y_solo_sellados(monkeypatch):
    t = {"ticket_id": "t1", "dia": date(2026, 10, 12), "escalon": 1, "cuota_total": 1.96,
         "prob_total": 0.49, "n_patas": 2, "decided_at": AHORA, "chain_sha256": "abc",
         "outcome": None, "factor_pago": None, "prob_efectiva": None}
    pata = {"ticket_id": "t1", "match_id": "m1", "market": "totals", "selection": "over",
            "line": 1.5, "prob": 0.7, "price": 1.4, "book": "betano", "kickoff_utc": AHORA,
            "league_id": "mx.liga_mx", "local": "Pachuca", "visitante": "Necaxa",
            "outcome": None, "home_goals": None, "away_goals": None, "valor": None}
    sqls = []
    def query(sql, params=()):
        sqls.append(sql)
        return [t] if "FROM parley_tickets t" in sql and "parley_patas p" not in sql else [pata]
    monkeypatch.setattr(pd_, "query", query)
    monkeypatch.setattr(pd_, "_liquidados", lambda: [])
    monkeypatch.setattr(hashchain, "LOTE_PARLEY_DESDE", date(2026, 10, 12))
    inf = pd_.informe_publico()
    assert inf["dias"][0]["dia"] == date(2026, 10, 12) and inf["dias"][0]["chain_sha256"] == "abc"
    leg = inf["dias"][0]["tickets"][0]["patas"][0]
    assert leg["texto"] == "Más de 1,5 goles"
    # La app traduce la pata desde estos campos; sin ellos salía siempre en español.
    assert (leg["market"], leg["selection"], leg["line"]) == ("totals", "over", 1.5)
    assert all("prediction_batches" in s for s in sqls)
    assert any("COALESCE(th.display_name" in s for s in sqls)   # el mismo nombre que en el resto


def test_informe_sin_corte_no_enseña_nada(monkeypatch):
    sqls = []
    monkeypatch.setattr(pd_, "query", lambda sql, params=(): sqls.append(sql) or [])
    monkeypatch.setattr(pd_, "_liquidados", lambda: [])
    monkeypatch.setattr(hashchain, "LOTE_PARLEY_DESDE", None)
    assert pd_.informe_publico()["dias"] == []
    assert all("AND FALSE" in s for s in sqls)


# --- Enganches: lote, job diario, liquidación --------------------------------

def test_el_lote_solo_lleva_el_parley_desde_su_fecha(monkeypatch):
    llamadas = []
    monkeypatch.setattr(hashchain, "query", lambda sql, params=(): llamadas.append(sql) or [])
    monkeypatch.setattr(hashchain, "LOTE_PARLEY_DESDE", None)
    assert "parley" not in hashchain._collect(date(2026, 10, 12))
    assert not any("parley_tickets" in s for s in llamadas)
    monkeypatch.setattr(hashchain, "LOTE_PARLEY_DESDE", date(2026, 10, 12))
    assert "parley" not in hashchain._collect(date(2026, 10, 11))
    assert hashchain._collect(date(2026, 10, 12))["parley"] == {"tickets": [], "patas": []}


def test_job_diario_elige_parley_antes_de_sellar(monkeypatch):
    from qf.publish import daily
    orden = []
    monkeypatch.setattr(daily, "generate_predictions", lambda: [{"match_id": "m"}])
    monkeypatch.setattr(daily, "_sharp_only_upcoming", lambda: [])
    monkeypatch.setattr(daily, "settings", replace(daily.settings, publish_picks_enabled=False,
                                                    parley_enabled=True))
    monkeypatch.setattr(daily, "_alta", lambda: orden.append("alta") or {})
    monkeypatch.setattr(daily, "_escalera", lambda: orden.append("escalera") or {})
    monkeypatch.setattr(daily.parley_datos, "select_and_persist",
                        lambda: orden.append("parley") or {"tickets": [{}]})
    monkeypatch.setattr(daily, "seal", lambda: orden.append("seal") or {"chain_sha256": "x" * 64})
    out = daily.run()
    assert orden == ["alta", "escalera", "parley", "seal"] and "parley" in out


def test_fallo_del_parley_no_rompe_el_job(monkeypatch):
    from qf.publish import daily
    alertas = []
    monkeypatch.setattr(daily, "settings", replace(daily.settings, parley_enabled=True))
    monkeypatch.setattr(daily.parley_datos, "select_and_persist",
                        lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(daily.tg, "alert", alertas.append)
    assert daily._parley()["estado"] == "error" and "boom" in alertas[0]


def test_parley_sin_sellar_avisa(monkeypatch):
    from qf.publish import daily
    alertas = []
    monkeypatch.setattr(daily.tg, "alert", alertas.append)
    daily._alerta_sin_sellar({}, {}, None, {"tickets": [{}, {}]})
    assert any("parlays SIN SELLAR" in a for a in alertas)


def test_liquidacion_general_llama_al_parley(monkeypatch):
    from qf.eval import clv
    from qf.model import shadow
    from qf.publish import alta_prob_datos, escalera_datos, shadow_sharp
    monkeypatch.setattr(clv, "query", lambda *a, **k: [])
    for mod in (shadow, shadow_sharp, alta_prob_datos, escalera_datos):
        monkeypatch.setattr(mod, "settle_pending", lambda *a, **k: {"settled": 0})
    monkeypatch.setattr(pd_, "settle_pending", lambda: {"patas": 0, "tickets": 0})
    assert clv.settle_pending()["parley"] == {"patas": 0, "tickets": 0}


def test_ruta_publica_del_parley(monkeypatch):
    from fastapi.testclient import TestClient
    from qf.api import main

    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *_a: False)
    monkeypatch.setattr(pd_, "informe_publico", lambda: {"dias": [], "activo": False})
    r = TestClient(main.app).get("/parley")
    assert r.status_code == 200
    body = r.json()
    assert body["dias"] == [] and body["activo"] is False
    assert body["acceso"]["plus"] is False


def _de(mercado, match="m", prob=0.7, price=1.4):
    return Opcion(match, Candidato(mercado, "over", 1.5, prob), price, "betano", "the_odds_api", AHORA)


def test_las_patas_de_un_mercado_bloqueado_no_entran():
    patas = [_de("totals", "a"), _de("corners", "b"), _de("spreads", "c"), _de("double_chance", "d")]
    assert [o.cand.market for o in pl.sin_bloqueados(patas, ["totals"])] == ["corners", "spreads", "double_chance"]
    assert pl.sin_bloqueados(patas, []) == patas


def test_el_bloqueo_se_compara_por_grupo_y_todo_no_pausa_el_parley():
    patas = [_de("team_totals_home", "a"), _de("team_totals_away", "b"), _de("totals", "c")]
    # «marca el local» y «marca el visitante» se vigilan como un solo grupo
    assert [o.cand.market for o in pl.sin_bloqueados(patas, ["team_totals"])] == ["totals"]
    assert pl.sin_bloqueados(patas, ["todo"]) == patas


def test_el_parley_no_usa_goles_si_el_control_los_bloquea(monkeypatch, encendido):
    monkeypatch.setattr(pd_, "query_one", lambda sql, params=(): None)
    monkeypatch.setattr(pd_, "mercados_bloqueados", lambda: ["totals"])
    monkeypatch.setattr(pd_, "candidatas", lambda now: ([_de("totals", "a"), _de("totals", "b"),
                                                         _de("corners", "c"), _de("corners", "d")], 0))
    out = pd_.select_and_persist(AHORA, dry_run=True)
    usadas = {p["market"] for t in out["tickets"] for p in t["patas"]}
    assert out["mercados_bloqueados"] == ["totals"] and usadas == {"corners"}
    assert {p["match_id"] for t in out["tickets"] for p in t["patas"]} == {"c", "d"}


def test_mercados_bloqueados_une_principal_y_ampliada_sin_todo(monkeypatch):
    from qf.publish import alta_prob_ext as ae
    monkeypatch.undo()                  # la función real, no la del fixture automático
    monkeypatch.setattr(pd_.ad, "estado", lambda: {"bloqueados": ["corners", "todo"]})
    monkeypatch.setattr(ae, "estado", lambda: {"bloqueados": ["totals", "corners"]})
    assert pd_.mercados_bloqueados() == ["corners", "totals"]
