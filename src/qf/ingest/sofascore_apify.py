"""Recolector diario SofaScore vía Apify (actor rl1987/sofascore-api-scraper).

Solo biblioteca estándar; corre en el host por cron. Las respuestas originales
se archivan sin tocar (gzip por hash) con la hora REAL de recepción: SofaScore
no entrega la hora de captura y el uso point-in-time depende de ella.
Gasto acotado: tope mensual (cuenta Apify), tope diario y tope por corrida.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.apify.com/v2"
ACTOR = "rl1987~sofascore-api-scraper"
UTC = timezone.utc
FINAL = {"finished", "canceled", "cancelled", "postponed", "abandoned"}
DETAIL = {"mode": "event_detail", "includeStatistics": True,
          "includeLineups": True, "includeIncidents": True}
BATCH = 20
# Margen tras el inicio antes de esperar un partido terminado.
GRACE = timedelta(hours=3)


class Stop(Exception):
    pass


def now():
    return datetime.now(UTC)


def read_token(path):
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("APIFY_TOKEN="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise ValueError("APIFY_TOKEN ausente")


def connect(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "index.sqlite", timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
      CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, kind TEXT NOT NULL,
        params TEXT NOT NULL, status INTEGER NOT NULL, sha256 TEXT NOT NULL,
        body_path TEXT NOT NULL, rows INTEGER NOT NULL, usd REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY, target TEXT NOT NULL, round INTEGER,
        start_ts INTEGER NOT NULL, status TEXT NOT NULL, captured_receipt INTEGER);
      CREATE TABLE IF NOT EXISTS tournaments (
        utid INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
        last_seen TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS rounds (
        target TEXT PRIMARY KEY, round INTEGER NOT NULL);
      CREATE TRIGGER IF NOT EXISTS immutable_receipts_u BEFORE UPDATE ON receipts
        BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
      CREATE TRIGGER IF NOT EXISTS immutable_receipts_d BEFORE DELETE ON receipts
        BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
    """)
    return db


def put_object(root, body):
    sha = hashlib.sha256(body).hexdigest()
    rel = Path("objects") / sha[:2] / (sha + ".json.gz")
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(gzip.compress(body, mtime=0))
        tmp.replace(path)
    return sha, rel.as_posix()


def http(method, url, token, payload=None, timeout=330):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json",
        "User-Agent": "QuantFut-Sofascore/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def month_usd(token, call=http):
    status, body = call("GET", API + "/users/me/limits", token, timeout=60)
    if status != 200:
        raise Stop("no se pudo leer el gasto Apify: HTTP %d" % status)
    return float(json.loads(body)["data"]["current"]["monthlyUsageUsd"])


class Collector:
    def __init__(self, root, token, cfg, call=http, clock=now):
        self.root, self.token, self.cfg = Path(root), token, cfg
        self.call, self.clock = call, clock
        self.db = connect(root)
        self.start_usd = month_usd(token, call)
        self.spent = 0.0

    def budget_left(self):
        used = month_usd(self.token, self.call)
        self.spent = used - self.start_usd
        return min(self.cfg["monthly_cap_usd"] - used,
                   self.cfg["run_cap_usd"] - self.spent)

    def run(self, kind, params, cap):
        """Una corrida del actor; archiva el original y devuelve las filas."""
        before = month_usd(self.token, self.call)
        url = "%s/acts/%s/run-sync-get-dataset-items?timeout=300&maxTotalChargeUsd=%.2f" % (
            API, ACTOR, max(cap, 0.10))
        status, body = self.call("POST", url, self.token, params)
        received = self.clock()
        sha, rel = put_object(self.root, body)
        rows = json.loads(body) if status in (200, 201) else []
        if not isinstance(rows, list):
            rows = []
        usd = max(month_usd(self.token, self.call) - before, 0.0)
        with self.db:
            cur = self.db.execute(
                "INSERT INTO receipts(received_at,kind,params,status,sha256,body_path,rows,usd)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (received.isoformat(), kind, json.dumps(params, sort_keys=True),
                 status, sha, rel, len(rows), usd))
        return cur.lastrowid, rows

    def upsert(self, target, rows):
        with self.db:
            for e in rows:
                if e.get("kind") != "event":
                    continue
                self.db.execute(
                    "INSERT INTO events(id,target,round,start_ts,status) VALUES(?,?,?,?,?)"
                    " ON CONFLICT(id) DO UPDATE SET status=excluded.status,"
                    " start_ts=excluded.start_ts, round=excluded.round",
                    (e["id"], target, e.get("round"), e["startTimestamp"], e["statusType"]))

    def due(self, target, spec=None):
        """¿Hay que volver a listar? Solo si algo pudo terminar o no hay datos."""
        if spec and spec.get("rounds") is False:  # sin jornadas: una vez cada ~20 h
            last = self.db.execute(
                "SELECT max(received_at) FROM receipts WHERE kind='list' AND params LIKE ?",
                ('%%"uniqueTournamentId": %d}' % spec["utid"],)).fetchone()[0]
            return last is None or self.clock() - datetime.fromisoformat(last) > timedelta(hours=20)
        row = self.db.execute("SELECT round FROM rounds WHERE target=?", (target,)).fetchone()
        if row is None:
            return True
        limit = int((self.clock() - GRACE).timestamp())
        pending = self.db.execute(
            "SELECT 1 FROM events WHERE target=? AND round=? AND status NOT IN (%s)"
            " AND start_ts<? LIMIT 1" % ",".join("?" * len(FINAL)),
            (target, row["round"], *sorted(FINAL), limit)).fetchone()
        known = self.db.execute("SELECT 1 FROM events WHERE target=? AND round=? LIMIT 1",
                                (target, row["round"])).fetchone()
        return bool(pending) or not known

    def refresh(self, target, spec):
        cap = self.budget_left()
        if cap < 0.10:
            raise Stop("presupuesto agotado")
        if spec.get("rounds") is False:  # competición sin jornadas (NBA)
            params = {"mode": "tournament", "uniqueTournamentId": spec["utid"],
                      "eventsSpan": "last"}
        else:
            row = self.db.execute("SELECT round FROM rounds WHERE target=?", (target,)).fetchone()
            if row is None:
                # listRounds cuesta ~0,12 USD por liga; el próximo partido da la jornada.
                _, nxt = self.run("rounds", {"mode": "tournament",
                                             "uniqueTournamentId": spec["utid"],
                                             "eventsSpan": "next", "maxItems": 1},
                                  min(cap, 0.10))
                cur = [r["round"] for r in nxt if r.get("kind") == "event" and r.get("round")]
                if not cur:
                    return
                with self.db:
                    self.db.execute("INSERT INTO rounds VALUES(?,?)", (target, cur[0]))
                rnd = cur[0]
            else:
                rnd = row["round"]
            params = {"mode": "tournament", "uniqueTournamentId": spec["utid"],
                      "eventsSpan": "last", "tournamentRound": str(rnd)}
        _, rows = self.run("list", params, min(self.budget_left(), 0.20))
        self.upsert(target, rows)
        self.advance(target)

    def advance(self, target):
        row = self.db.execute("SELECT round FROM rounds WHERE target=?", (target,)).fetchone()
        if row is None:
            return
        left = self.db.execute(
            "SELECT count(*) FROM events WHERE target=? AND round=? AND status NOT IN (%s)"
            % ",".join("?" * len(FINAL)), (target, row["round"], *sorted(FINAL))).fetchone()[0]
        total = self.db.execute("SELECT count(*) FROM events WHERE target=? AND round=?",
                                (target, row["round"])).fetchone()[0]
        if total and not left:
            with self.db:
                self.db.execute("UPDATE rounds SET round=round+1 WHERE target=?", (target,))

    def details(self):
        ids = [r[0] for r in self.db.execute(
            "SELECT id FROM events WHERE captured_receipt IS NULL AND status='finished'"
            " ORDER BY start_ts LIMIT ?", (self.cfg["max_details_per_run"],))]
        for i in range(0, len(ids), BATCH):
            chunk = ids[i:i + BATCH]
            cap = self.budget_left()
            if cap < 0.10:
                raise Stop("presupuesto agotado")
            rid, rows = self.run("detail", {**DETAIL, "eventIds": [str(x) for x in chunk]},
                                 min(cap, 0.01 * len(chunk) + 0.10))
            got = {e["id"] for e in rows if e.get("id")}
            with self.db:
                for x in chunk:
                    if x in got:
                        self.db.execute("UPDATE events SET captured_receipt=? WHERE id=?",
                                        (rid, x))

    def discover_tennis(self):
        """Cada semana localiza los torneos ATP/WTA (individuales) en juego.

        SofaScore no lista torneos activos: se barre un día de calendario y se
        filtra por categoría. Los partidos hallados se registran de paso.
        """
        cfg = self.cfg.get("tennis")
        if cfg is None:
            return
        last = self.db.execute("SELECT max(received_at) FROM receipts WHERE kind='discover'").fetchone()[0]
        if last and self.clock() - datetime.fromisoformat(last) < timedelta(days=cfg.get("every_days", 6)):
            return
        cap = min(self.budget_left(), cfg.get("discovery_cap_usd", 0.9))
        if cap < 0.10:
            raise Stop("presupuesto agotado")
        day = self.clock().date().isoformat()
        _, rows = self.run("discover", {"mode": "scheduled", "sport": "tennis", "dateFrom": day,
                                        "dateTo": day, "maxItems": cfg.get("max_items", 220)}, cap)
        keep = [e for e in rows if e.get("kind") == "event"
                and e.get("category") in cfg.get("categories", ["ATP", "WTA"])
                and not any(x in (e.get("uniqueTournament") or "") for x in cfg.get("exclude", ["Doubles"]))]
        seen = self.clock().isoformat()
        with self.db:
            for e in keep:
                self.db.execute(
                    "INSERT INTO tournaments VALUES(?,?,?,?) ON CONFLICT(utid) DO UPDATE SET last_seen=excluded.last_seen",
                    (e["uniqueTournamentId"], e["uniqueTournament"], e["category"], seen))
        for e in keep:
            self.upsert("tennis.%d" % e["uniqueTournamentId"], [e])

    def active_tennis(self):
        cfg = self.cfg.get("tennis") or {}
        limit = (self.clock() - timedelta(days=cfg.get("active_days", 10))).isoformat()
        return {"tennis.%d" % r[0]: {"utid": r[0], "rounds": False}
                for r in self.db.execute("SELECT utid FROM tournaments WHERE last_seen>=?", (limit,))}

    def capture(self):
        try:
            self.discover_tennis()
            targets = {**self.cfg["targets"], **self.active_tennis()}
            for target, spec in targets.items():
                if self.due(target, spec):
                    self.refresh(target, spec)
            self.details()
        except Stop as exc:
            return str(exc)
        return "ok"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["capture"])
    ap.add_argument("--root", required=True)
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--config", required=True)
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.config).read_text(encoding="utf8"))
    c = Collector(a.root, read_token(a.key_file), cfg)
    result = c.capture()
    c.budget_left()
    print(json.dumps({"at": now().isoformat(), "result": result,
                      "spent_usd": round(c.spent, 4)}))
    return 0 if result == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
