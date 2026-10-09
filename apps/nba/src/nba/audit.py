"""Local research ledger. Hash integrity is not an external timestamp anchor."""
import hashlib
import json
import sqlite3
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, allow_nan=False) + "\n"
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    # Windows scanners may briefly hold the destination. Retry only the rename,
    # never a network request, and retain the old file plus completed temp on failure.
    delays = (0, .01, .025, .05, .1, .2)
    for attempt, delay in enumerate(delays):
        if delay:
            time.sleep(delay)
        try:
            temporary.replace(path)
            break
        except PermissionError as error:
            if getattr(error, "winerror", None) not in {5, 32} or attempt == len(delays) - 1:
                raise


class Ledger:
    """Explicit NBA-only SQLite research store, not the production Postgres gate."""

    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with sqlite3.connect(path) as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY, received_at TEXT NOT NULL,
                kind TEXT NOT NULL, payload TEXT NOT NULL,
                previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE
            );
            CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
            BEGIN SELECT RAISE(ABORT, 'immutable NBA audit'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
            BEGIN SELECT RAISE(ABORT, 'immutable NBA audit'); END;
            """)

    def append(self, kind, payload):
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            last = db.execute("SELECT seq,event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            seq, previous = (last[0] + 1, last[1]) if last else (1, "0" * 64)
            event = dict(seq=seq, received_at=datetime.now(UTC).isoformat(),
                         kind=kind, payload=canonical(payload), previous_hash=previous)
            event_hash = hashlib.sha256(canonical(event).encode()).hexdigest()
            db.execute("INSERT INTO events VALUES (?,?,?,?,?,?)",
                       (seq, event['received_at'], kind, event['payload'], previous, event_hash))
            return event_hash

    def verify(self):
        previous = "0" * 64
        count = 0
        with sqlite3.connect(self.path) as db:
            for seq, received_at, kind, payload, prev, hashed in db.execute("SELECT * FROM events ORDER BY seq"):
                count += 1
                event = dict(seq=seq, received_at=received_at, kind=kind, payload=payload, previous_hash=prev)
                if seq != count or prev != previous or hashlib.sha256(canonical(event).encode()).hexdigest() != hashed:
                    raise ValueError("NBA audit chain mismatch")
                previous = hashed
        return dict(events=count, head=previous, external_anchor=False)
