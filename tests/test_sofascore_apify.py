import gzip
import json
from datetime import datetime, timezone

from qf.ingest import sofascore_apify as sa

T0 = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def ev(i, rnd, status, ts=1792800000):
    return {"kind": "event", "id": i, "round": rnd, "startTimestamp": ts, "statusType": status}


class Fake:
    """Apify simulado: cada corrida suma 0,02 USD al gasto mensual."""
    def __init__(self, round_rows, detail_ids=None):
        self.usd, self.calls, self.round_rows = 1.0, [], round_rows

    def __call__(self, method, url, token, payload=None, timeout=0):
        if url.endswith("/users/me/limits"):
            return 200, json.dumps({"data": {"current": {"monthlyUsageUsd": self.usd}}}).encode()
        self.calls.append(payload)
        self.usd += 0.02
        if payload.get("eventsSpan") == "next":
            rows = [ev(9, 3, "notstarted", 1793000000)]
        elif payload["mode"] == "event_detail":
            rows = [{"id": int(i), "statistics": []} for i in payload["eventIds"]]
        elif payload["mode"] == "scheduled":
            rows = [dict(ev(50, 1, "finished"), category="ATP", uniqueTournamentId=2428, uniqueTournament="Vienna"),
                    dict(ev(51, 1, "finished"), category="ATP", uniqueTournamentId=2471, uniqueTournament="Vienna, Doubles"),
                    dict(ev(52, 1, "finished"), category="ITF Men", uniqueTournamentId=9, uniqueTournament="ITF M15")]
        else:
            rows = self.round_rows
        return 200, json.dumps(rows).encode()


CFG = {"monthly_cap_usd": 15, "run_cap_usd": 1, "max_details_per_run": 50,
       "targets": {"es.laliga": {"utid": 8}}}


def collector(tmp_path, rows):
    f = Fake(rows)
    return sa.Collector(tmp_path, "tok", CFG, call=f, clock=lambda: T0), f


def test_captura_terminados_una_sola_vez_con_recepcion_real(tmp_path):
    c, f = collector(tmp_path, [ev(1, 3, "finished"), ev(2, 3, "notstarted", 1793000000)])
    assert c.capture() == "ok"
    kinds = [r["kind"] for r in c.db.execute("SELECT kind FROM receipts ORDER BY id")]
    assert kinds == ["rounds", "list", "detail"]
    assert c.db.execute("SELECT captured_receipt FROM events WHERE id=1").fetchone()[0]
    assert c.db.execute("SELECT captured_receipt FROM events WHERE id=2").fetchone()[0] is None
    got = c.db.execute("SELECT received_at,body_path FROM receipts WHERE kind='detail'").fetchone()
    assert got["received_at"] == T0.isoformat()
    assert gzip.decompress((tmp_path / got["body_path"]).read_bytes())
    n = len(f.calls)
    assert c.capture() == "ok"  # no hay nada vencido: cero gasto nuevo
    assert len(f.calls) == n


def test_jornada_terminada_avanza_y_recibo_es_inmutable(tmp_path):
    c, _ = collector(tmp_path, [ev(1, 3, "finished"), ev(2, 3, "finished")])
    c.capture()
    assert c.db.execute("SELECT round FROM rounds").fetchone()[0] == 4
    try:
        c.db.execute("DELETE FROM receipts")
        assert False
    except Exception as exc:
        assert "immutable" in str(exc)


def test_tope_de_presupuesto_detiene(tmp_path):
    c, f = collector(tmp_path, [ev(1, 3, "finished")])
    c.cfg = {**CFG, "monthly_cap_usd": 1.05}
    assert c.capture() == "presupuesto agotado"


def test_tenis_descubre_semanal_solo_atp_wta_individual(tmp_path):
    f = Fake([])
    cfg = {**CFG, "targets": {}, "tennis": {}}
    c = sa.Collector(tmp_path, "tok", cfg, call=f, clock=lambda: T0)
    assert c.capture() == "ok"
    assert [r[0] for r in c.db.execute("SELECT utid FROM tournaments")] == [2428]
    assert c.db.execute("SELECT captured_receipt FROM events WHERE id=50").fetchone()[0]
    assert c.db.execute("SELECT count(*) FROM events WHERE id IN (51,52)").fetchone()[0] == 0
    n = len([p for p in f.calls if p["mode"] == "scheduled"])
    c.capture()  # misma semana: no vuelve a barrer el calendario
    assert len([p for p in f.calls if p["mode"] == "scheduled"]) == n


def test_detalles_futbol_reciente_primero_y_sin_jornadas_viejas(tmp_path):
    c, f = collector(tmp_path, [])
    c.cfg = {**CFG, "max_details_per_run": 2}
    hora = int(T0.timestamp())
    with c.db:
        c.db.executemany("INSERT INTO events(id,target,round,start_ts,status) VALUES(?,?,?,?,?)", [
            (1, "es.laliga", 1, hora - 200 * 86400, "finished"),     # jornada de abril: fuera
            (2, "es.laliga", 9, hora - 2 * 86400, "finished"),
            (3, "es.laliga", 10, hora - 86400, "finished"),
            (4, "tennis.2428", None, hora - 3600, "finished")])
    c.details()
    pedidos = [p["eventIds"] for p in f.calls if p.get("mode") == "event_detail"]
    assert pedidos == [["3", "2"]]
