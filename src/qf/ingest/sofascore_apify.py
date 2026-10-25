"""Recolector diario SofaScore vía Apify.

Actor por deporte (decisión del titular, 2026-10-24): fútbol con
rl1987/sofascore-api-scraper; NBA y tenis con scrapesage/sofascore-scraper.
El actor de cada objetivo se fija con "provider" en la configuración.

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
ACTORS = {"rl1987": "rl1987~sofascore-api-scraper",
          "scrapesage": "scrapesage~sofascore-scraper"}
DEFAULT_PROVIDER = "rl1987"
UTC = timezone.utc
FINAL = {"finished", "canceled", "cancelled", "postponed", "abandoned"}
ENRICH = {"includeStatistics": True, "includeLineups": True, "includeIncidents": True}
DETAIL = {"mode": "event_detail", **ENRICH}
DETAIL_SCRAPESAGE = {"mode": "event", **ENRICH}
LIST_MAX = 100
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


def normalize_scrapesage(r):
    """Fila de scrapesage al formato común del índice (id = matchId)."""
    return {"kind": "event", "id": r["matchId"], "round": r.get("round"),
            "startTimestamp": r.get("startTimestamp"), "statusType": r.get("statusType")}


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

    def provider(self, target):
        if target.startswith("tennis."):
            return (self.cfg.get("tennis") or {}).get("provider", DEFAULT_PROVIDER)
        return (self.cfg["targets"].get(target) or {}).get("provider", DEFAULT_PROVIDER)

    def run(self, kind, params, cap, provider=DEFAULT_PROVIDER):
        """Una corrida del actor; archiva el original y devuelve las filas.

        Las filas de scrapesage vuelven normalizadas (kind/id/round/startTimestamp/
        statusType); el cuerpo original se archiva tal cual y el recibo anota el actor.
        """
        before = month_usd(self.token, self.call)
        url = "%s/acts/%s/run-sync-get-dataset-items?timeout=300&maxTotalChargeUsd=%.2f" % (
            API, ACTORS[provider], max(cap, 0.10))
        status, body = self.call("POST", url, self.token, params)
        received = self.clock()
        sha, rel = put_object(self.root, body)
        rows = json.loads(body) if status in (200, 201) else []
        if not isinstance(rows, list):
            rows = []
        if provider == "scrapesage":
            rows = [normalize_scrapesage(r) for r in rows if r.get("matchId")]
        usd = max(month_usd(self.token, self.call) - before, 0.0)
        with self.db:
            cur = self.db.execute(
                "INSERT INTO receipts(received_at,kind,params,status,sha256,body_path,rows,usd)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (received.isoformat(), kind,
                 json.dumps({**params, "_actor": provider}, sort_keys=True),
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
        if spec and (spec.get("rounds") is False or spec.get("provider") == "scrapesage"):
            # sin jornadas: una vez cada ~20 h
            last = self.db.execute(
                "SELECT max(received_at) FROM receipts WHERE kind='list' AND"
                " (params LIKE ? OR params LIKE ?)",
                ('%%"uniqueTournamentId": %d}' % spec["utid"],
                 '%%"tournamentIds": [%d]}' % spec["utid"])).fetchone()[0]
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
        if spec.get("provider") == "scrapesage":
            # NBA y tenis: terminados recientes de la temporada en curso, sin jornadas.
            params = {"mode": "tournament", "tournamentIds": [spec["utid"]],
                      "onlyFinished": True,
                      "maxResults": self.cfg.get("list_max", LIST_MAX)}
            _, rows = self.run("list", params, min(cap, 0.50), "scrapesage")
            self.upsert(target, rows)
            return
        if spec.get("rounds") is False:  # competición sin jornadas
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
        # Fútbol primero y lo más reciente primero: su xG alimenta el modelo desde el 24-oct
        # (API-Football en plan gratuito). Con 40 detalles al día, empezar por la jornada 1
        # tardaba semanas en llegar a los partidos de ayer.
        since = int((self.clock() - timedelta(days=self.cfg.get("detail_days", 14))).timestamp())
        by_provider = {}
        for eid, target in self.db.execute(
                "SELECT id, target FROM events WHERE captured_receipt IS NULL AND"
                " status='finished' AND start_ts>=?"
                " ORDER BY (target LIKE 'tennis.%' OR target = 'nba'), start_ts DESC LIMIT ?",
                (since, self.cfg["max_details_per_run"])).fetchall():
            by_provider.setdefault(self.provider(target), []).append(eid)
        for provider, ids in by_provider.items():
            base = DETAIL_SCRAPESAGE if provider == "scrapesage" else DETAIL
            for i in range(0, len(ids), BATCH):
                chunk = ids[i:i + BATCH]
                cap = self.budget_left()
                if cap < 0.10:
                    raise Stop("presupuesto agotado")
                send = [int(x) for x in chunk] if provider == "scrapesage" else [str(x) for x in chunk]
                rid, rows = self.run("detail", {**base, "eventIds": send},
                                     min(cap, 0.01 * len(chunk) + 0.10), provider)
                got = {e["id"] for e in rows if e.get("id")}
                with self.db:
                    for x in chunk:
                        if x in got:
                            self.db.execute("UPDATE events SET captured_receipt=? WHERE id=?",
                                            (rid, x))

    def discover_tennis(self):
        """Cada semana localiza los torneos ATP/WTA (individuales) en juego.

        SofaScore no lista torneos activos: se barre un día de calendario y se
        filtra por categoría. Solo rl1987 tiene modo por fecha (scrapesage no),
        así que el descubrimiento sigue con rl1987 aunque los datos vengan de
        scrapesage. Los partidos hallados se registran de paso.
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
                                        "dateTo": day, "maxItems": cfg.get("max_items", 220)},
                           cap, "rl1987")
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
        prov = cfg.get("provider", DEFAULT_PROVIDER)
        return {"tennis.%d" % r[0]: {"utid": r[0], "rounds": False, "provider": prov}
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
