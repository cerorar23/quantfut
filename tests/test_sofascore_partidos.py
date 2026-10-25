"""Carga de SofaScore a partidos: emparejamiento por marcador, integridad del archivo y xG point-in-time."""
import gzip
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from qf.ingest import sofascore_partidos as sp

KO = datetime(2026, 10, 24, 20, 0, tzinfo=timezone.utc)


def stats(xg=(1.4, 0.6), amarillas=(2, 3), rojas=None):
    items = [dict(key="totalShotsOnGoal", homeValue=12, awayValue=7),
             dict(key="shotsOnGoal", homeValue=5, awayValue=2),
             dict(key="cornerKicks", homeValue=6, awayValue=4),
             dict(key="yellowCards", homeValue=amarillas[0], awayValue=amarillas[1])]
    if xg:
        items.append(dict(key="expectedGoals", homeValue=xg[0], awayValue=xg[1]))
    if rojas:
        items.append(dict(key="redCards", homeValue=rojas[0], awayValue=rojas[1]))
    return [dict(period="ALL", groups=[dict(statisticsItems=items)])]


def fila(**kw):
    base = dict(kind="event_detail", sport="football", id=15269947, uniqueTournamentId=155,
                startTimestamp=int(KO.timestamp()), statusType="finished", statusCode=100,
                homeTeam="Club Atlético Belgrano", awayTeam="Aldosivi", homeTeamId=3203, awayTeamId=3204,
                homeScore=1, awayScore=0, referee="Daniel Zamora", statistics=stats(),
                lineups=dict(confirmed=True, home=dict(players=[]), away=dict(players=[])))
    base.update(kw)
    return base


def candidatos(monkeypatch, partidos, nombres):
    monkeypatch.setattr(sp, "query", lambda q, p=(): partidos)
    monkeypatch.setattr(sp, "_nombres", lambda ids: {i: {n} for i, n in nombres.items()})


def test_empareja_con_nombre_largo_y_mismo_marcador(monkeypatch):
    p = dict(match_id="ar:1", status="finished", home_team_id=1, away_team_id=2, home_goals=1, away_goals=0)
    candidatos(monkeypatch, [p], {1: "belgrano", 2: "aldosivi"})
    assert sp.emparejar(fila()) == ("ar:1", "ok")


def test_marcador_distinto_es_conflicto_y_no_se_aplica(monkeypatch):
    p = dict(match_id="ar:1", status="finished", home_team_id=1, away_team_id=2, home_goals=2, away_goals=0)
    candidatos(monkeypatch, [p], {1: "belgrano", 2: "aldosivi"})
    assert sp.emparejar(fila()) == (None, "conflicto_marcador")


def test_partido_sin_resultado_espera(monkeypatch):
    p = dict(match_id="ar:1", status="scheduled", home_team_id=1, away_team_id=2, home_goals=None, away_goals=None)
    candidatos(monkeypatch, [p], {1: "belgrano", 2: "aldosivi"})
    assert sp.emparejar(fila()) == (None, "pendiente_de_resultado")


def test_nombres_que_no_se_parecen_no_emparejan(monkeypatch):
    p = dict(match_id="ar:1", status="finished", home_team_id=1, away_team_id=2, home_goals=1, away_goals=0)
    candidatos(monkeypatch, [p], {1: "river plate", 2: "boca juniors"})
    assert sp.emparejar(fila()) == (None, "sin_partido")


def test_prorroga_y_competicion_ajena_se_descartan(monkeypatch):
    candidatos(monkeypatch, [], {})
    assert sp.emparejar(fila(statusCode=110))[1] == "no_terminado_en_tiempo_reglamentario"
    assert sp.emparejar(fila(uniqueTournamentId=999999))[1] == "competicion_fuera_de_catalogo"


class FakeConn:
    def __init__(self, inserta=True):
        self.sql, self.inserta = [], inserta

    def execute(self, q, p=()):
        self.sql.append((" ".join(q.split()), p))
        ret = {"match_id": "ar:1"} if q.strip().startswith("INSERT") and self.inserta else None
        return type("R", (), {"fetchone": lambda s: ret})()


RECIBO = dict(id=77, received_at="2026-10-24T22:09:53+00:00", sha256="a" * 64)


def test_aplicar_escribe_xg_con_hora_de_recepcion_y_tarjetas_en_cero():
    c = FakeConn()
    assert sp.aplicar(c, RECIBO, fila(), "ar:1")
    upd = [p for q, p in c.sql if q.startswith("UPDATE matches SET home_shots")][0]
    assert upd == (12, 7, 5, 2, 6, 4, 2, 3, 0, 0, "D Zamora", "ar:1")
    xg = [p for q, p in c.sql if "xg_source = 'sofascore'" in q][0]
    assert xg == (1.4, 0.6, RECIBO["received_at"], "ar:1")


def test_sin_xg_no_toca_el_xg_y_repetido_no_reescribe():
    c = FakeConn()
    sp.aplicar(c, RECIBO, fila(statistics=stats(xg=None)), "ar:1")
    assert not any("xg_source" in q for q, p in c.sql)
    c = FakeConn(inserta=False)
    assert not sp.aplicar(c, RECIBO, fila(), "ar:1")
    assert len(c.sql) == 1


def test_detalles_verifica_hash_y_filtra_futbol(tmp_path):
    db = sqlite3.connect(tmp_path / "index.sqlite")
    db.execute("CREATE TABLE receipts (id INTEGER PRIMARY KEY, received_at TEXT, kind TEXT, params TEXT,"
               " status INTEGER, sha256 TEXT, body_path TEXT, rows INTEGER, usd REAL)")
    def guardar(rid, filas, sha=None):
        body = json.dumps(filas).encode()
        (tmp_path / f"{rid}.gz").write_bytes(gzip.compress(body))
        db.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?,?)",
                   (rid, KO.isoformat(), "detail", "{}", 200, sha or hashlib.sha256(body).hexdigest(),
                    f"{rid}.gz", len(filas), 0.01))
    guardar(1, [fila(), dict(kind="event_detail", sport="basketball", id=5), dict(type="match", sport="tennis")])
    guardar(2, [fila(id=2)], sha="0" * 64)
    db.commit(); db.close()
    out = sp.detalles(tmp_path, KO - timedelta(days=1))
    assert [f["id"] for r, f in out] == [15269947]
    assert sp.detalles(tmp_path, KO + timedelta(days=1)) == []
