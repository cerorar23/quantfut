"""Reto escalera contra un Postgres real con db/*.sql aplicados (ver test_cuentas_pg)."""
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.publish import escalera_datos as ed
from qf.publish import hashchain

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


@pytest.fixture(autouse=True)
def _lote(monkeypatch):
    monkeypatch.setattr(hashchain, "LOTE_ESCALERA_DESDE", date(2000, 1, 1))


def _dia() -> datetime:
    """Una fecha distinta en cada ejecución: los lotes no se pueden borrar."""
    return datetime(2001, 1, 1, 9, tzinfo=timezone.utc) + timedelta(days=uuid.uuid4().int % 8000)


def _partido(status="finished", hg=2, ag=0, kickoff=None) -> tuple[str, str, str]:
    sufijo = uuid.uuid4().hex[:8]
    liga = db.query_one("SELECT league_id FROM leagues ORDER BY league_id LIMIT 1")["league_id"]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s, %s) RETURNING team_id",
                        (liga, f"{n}-{sufijo}"))["team_id"] for n in ("Local", "Visita")]
    mid = f"{liga}:test:{sufijo}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  VALUES (%s,%s,'test',%s,%s,%s,%s,%s,%s)""",
               (mid, liga, kickoff or datetime.now(timezone.utc) - timedelta(days=1), *ids, status,
                hg if status == "finished" else None, ag if status == "finished" else None))
    return mid, f"Local-{sufijo}", f"Visita-{sufijo}"


def _reto(objetivo=2) -> int:
    return db.query_one("""INSERT INTO escalera_retos (stake_inicial, pasos_objetivo, cuota_min, cuota_max, ev_min)
                           VALUES (10, %s, 1.25, 1.40, 0) RETURNING reto_id""", (objetivo,))["reto_id"]


def _paso(reto_id, paso, mid, decided, price=1.30) -> None:
    db.execute("""INSERT INTO escalera_pasos (reto_id, paso, match_id, market, selection, prob, fair_price,
                                              price, book, odds_source, odds_as_of, decided_at)
                  VALUES (%s,%s,%s,'h2h','home',0.77,1.2987,%s,'betano','the_odds_api',%s,%s)""",
               (reto_id, paso, mid, price, decided - timedelta(hours=1), decided))


def _sellar(dia: datetime) -> None:
    h = uuid.uuid4().hex
    db.execute("""INSERT INTO prediction_batches (batch_date, n_predictions, n_picks, payload_sha256,
                                                  prev_sha256, chain_sha256, created_at)
                  VALUES (%s, 1, 0, %s, %s, %s, %s)""",
               (dia.date(), h, h, h + "c", dia + timedelta(hours=1)))


def _reto_publico(reto_id):
    inf = ed.informe_publico()
    return next(r for r in [*inf["actuales"], *inf["historial"]] if r["reto_id"] == reto_id)


def test_escalon_sellado_se_liquida_y_mueve_el_saldo():
    dia = _dia()
    reto = _reto(objetivo=2)
    mid, local, _ = _partido(hg=2, ag=0)
    _paso(reto, 1, mid, dia)
    _sellar(dia)
    assert ed.settle_pending()["settled"] >= 1
    r = _reto_publico(reto)
    assert r["estado"] == "en_curso" and r["ganados"] == 1 and r["saldo"] == "13.00"
    (p,) = r["pasos"]
    assert p["texto"] == f"Gana {local}" and p["marcador"] == "2-0" and p["outcome"] == "win"
    assert p["chain_sha256"]


def test_escalon_sin_sellar_no_se_ensena():
    dia = _dia()
    reto = _reto(objetivo=3)
    mid, *_ = _partido()
    _paso(reto, 1, mid, dia)              # sin lote: no existe para el público
    r = _reto_publico(reto)
    assert r["pasos"] == [] and r["estado"] == "en_curso"


def test_aplazado_pasado_el_margen_queda_nulo():
    dia = _dia()
    reto = _reto(objetivo=2)
    mid, *_ = _partido(status="postponed", kickoff=datetime.now(timezone.utc) - timedelta(days=3))
    _paso(reto, 1, mid, dia)
    _sellar(dia)
    ed.settle_pending()
    r = _reto_publico(reto)
    assert r["pasos"][0]["outcome"] == "void" and r["ganados"] == 0 and r["saldo"] == "10.00"


def test_perder_cierra_el_reto_y_las_filas_no_se_pueden_tocar():
    dia = _dia()
    reto = _reto(objetivo=2)
    mid, *_ = _partido(hg=0, ag=1)
    _paso(reto, 1, mid, dia)
    _sellar(dia)
    ed.settle_pending()
    r = _reto_publico(reto)
    assert r["estado"] == "fallido" and r["ganancia"] == "-10.00"
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("UPDATE escalera_pasos SET price = 9 WHERE reto_id = %s", (reto,))
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("DELETE FROM escalera_retos WHERE reto_id = %s", (reto,))


def test_handicap_entero_devuelto_queda_push_con_marcador():
    dia = _dia()
    reto = _reto(objetivo=3)
    mid, *_ = _partido(hg=0, ag=2)          # visitante gana por 2: el local +2 se devuelve
    db.execute("""INSERT INTO escalera_pasos (reto_id, paso, match_id, market, selection, line, prob,
                                              fair_price, price, book, odds_source, odds_as_of, decided_at)
                  VALUES (%s, 1, %s, 'spreads', 'home', 2.0, 0.78, 1.282, 1.30, '1xbet',
                          'the_odds_api', %s, %s)""", (reto, mid, dia - timedelta(hours=1), dia))
    _sellar(dia)
    ed.settle_pending()
    r = _reto_publico(reto)
    (p,) = r["pasos"]
    assert p["outcome"] == "push" and p["marcador"] == "0-2" and r["saldo"] == "10.00"
    assert p["texto"].endswith("+2 (hándicap asiático)")


def test_reto_sin_filtro_de_valor_y_escalon_de_corners_se_liquida_con_el_total():
    dia = _dia()
    reto = db.query_one("""INSERT INTO escalera_retos (stake_inicial, pasos_objetivo, cuota_min,
                                                       cuota_max, ev_min)
                           VALUES (10, 3, 1.25, 1.40, NULL) RETURNING reto_id""")["reto_id"]
    mid, *_ = _partido(hg=1, ag=1)
    db.execute("UPDATE matches SET home_corners = 6, away_corners = 5 WHERE match_id = %s", (mid,))
    db.execute("""INSERT INTO escalera_pasos (reto_id, paso, match_id, market, selection, line, prob,
                                              fair_price, price, book, odds_source, odds_as_of, decided_at)
                  VALUES (%s, 1, %s, 'corners', 'over', 8.5, 0.74, 1.351, 1.33, 'betano',
                          'api_football', %s, %s)""", (reto, mid, dia - timedelta(hours=1), dia))
    _sellar(dia)
    ed.settle_pending()
    r = _reto_publico(reto)
    (p,) = r["pasos"]
    assert (p["outcome"], p["valor"], p["texto"]) == ("win", 11, "Más de 8,5 córners")
    assert r["saldo"] == "13.30"


def test_reto_al_80_se_crea_con_su_objetivo_y_publica_su_probabilidad(monkeypatch):
    from dataclasses import replace
    from qf.publish import alta_prob_datos as ad
    from qf.publish import escalera as es
    from qf.publish.alta_prob import Candidato

    ahora = _dia()
    mid, *_ = _partido(status="scheduled", kickoff=ahora + timedelta(hours=5))
    monkeypatch.setattr(ed, "settings", replace(ed.settings, escalera_enabled=True))
    monkeypatch.setattr(ed, "_retos", lambda: [])
    monkeypatch.setattr(ed, "_partidos", lambda now: [{"match_id": mid}])
    monkeypatch.setattr(ad, "_rho_activo", lambda: None)
    monkeypatch.setattr(ed, "opciones", lambda m, now, rho, modelos: [es.Opcion(
        m["match_id"], Candidato("spreads", "home", 1.5, 0.95), 1.06, "betano", "propline",
        now - timedelta(minutes=5))])
    out = ed.select_and_persist(ahora)
    (plan,) = out["plan"]
    assert plan["nuevo_de"] == 2 and out["en_rango"] == 1
    reto = db.query_one("""SELECT r.* FROM escalera_retos r JOIN escalera_pasos p USING (reto_id)
                           WHERE p.match_id = %s""", (mid,))
    assert reto["prob_objetivo"] == pytest.approx(0.80) and reto["freeroll_x"] is None
    assert reto["dias_max"] == 7
    assert ed.prob_reto(ed._pasos(reto["reto_id"])) == pytest.approx(0.95)
    # El escalón aún no está sellado (decided_at es la hora real): no se enseña.
    r = _reto_publico(reto["reto_id"])
    assert r["prob_objetivo"] == pytest.approx(0.80) and r["prob_reto"] is None
    assert ed.informe_publico()["reglas"]["umbrales"] == {"2": 0.8944}


def test_reto_con_plazo_vencido_pasa_al_historial_como_expirado():
    reto = db.query_one("""INSERT INTO escalera_retos (stake_inicial, pasos_objetivo, cuota_min,
                                                       cuota_max, ev_min, prob_objetivo, dias_max,
                                                       created_at)
                           VALUES (10, 2, 1.03, 1.40, NULL, 0.8, 7, now() - interval '8 days')
                           RETURNING *""")
    assert ed.vencido(reto) and not ed.vencido(reto, reto["created_at"] + timedelta(days=6))
    r = _reto_publico(reto["reto_id"])
    assert r["estado"] == "expirado" and r["ganancia"] == "0.00" and r["dias_max"] == 7


def test_escalon_de_tenis_se_guarda_sin_partido_de_futbol_y_se_liquida_con_propline(monkeypatch):
    from dataclasses import replace
    from qf.publish import alta_prob_datos as ad
    from qf.publish import escalera as es
    from qf.publish import escalera_ext as ext
    from qf.publish.alta_prob import Candidato

    ahora = _dia()
    evento = (uuid.uuid4().hex[:10], "tennis_atp_paris", ahora + timedelta(hours=2),
              "Jannik Sinner", "Qualifier X")
    tenis = es.Opcion(f"tenis:{evento[0]}", Candidato("h2h", "home", None, 0.95), 1.06, "bovada",
                      "propline", ahora - timedelta(minutes=20), "tenis", evento)
    monkeypatch.setattr(ed, "settings", replace(ed.settings, escalera_enabled=True))
    monkeypatch.setattr(ed, "_retos", lambda: [])
    monkeypatch.setattr(ed, "_partidos", lambda now: [])
    monkeypatch.setattr(ad, "_rho_activo", lambda: None)
    monkeypatch.setattr(ext, "opciones", lambda now: [tenis])
    out = ed.select_and_persist(ahora)
    assert out["en_rango_por_deporte"]["tenis"] == 1 and out["plan"][0]["deporte"] == "tenis"
    paso = db.query_one("SELECT * FROM escalera_pasos WHERE evento_id = %s", (evento[0],))
    assert paso["match_id"] is None and paso["deporte"] == "tenis" and paso["evento_local"] == "Jannik Sinner"
    (publico,) = ed._pasos(paso["reto_id"])
    assert publico["match_id"] == f"tenis:{evento[0]}" and publico["league_id"] == "tenis"
    assert ed.texto(publico["market"], publico["selection"], None, publico["local"],
                    publico["visitante"]) == "Gana Jannik Sinner"
    # Un escalón de fútbol sin partido o uno de tenis sin evento no entran.
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("""INSERT INTO escalera_pasos (reto_id, paso, market, selection, prob, fair_price,
                                                  price, book, odds_source, odds_as_of)
                      VALUES (%s, 9, 'h2h', 'home', 0.9, 1.11, 1.05, 'bovada', 'propline', now())""",
                   (paso["reto_id"],))
    monkeypatch.setattr(ext, "resultado", lambda r, now: ("win", None, None, None))
    ed.settle_pending(evento[2] + timedelta(hours=5))
    res = db.query_one("SELECT * FROM escalera_resultados WHERE paso_id = %s", (paso["paso_id"],))
    assert (res["outcome"], res["fuente"], res["home_goals"]) == ("win", "propline", None)
    # Un resultado de fútbol sigue necesitando marcador.
    with pytest.raises(psycopg.errors.CheckViolation):
        mid, *_ = _partido()
        r = _reto()
        _paso(r, 1, mid, ahora)
        pid = db.query_one("SELECT paso_id FROM escalera_pasos WHERE reto_id = %s", (r,))["paso_id"]
        db.execute("INSERT INTO escalera_resultados (paso_id, outcome) VALUES (%s, 'win')", (pid,))
