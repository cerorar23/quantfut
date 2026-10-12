"""Scoped private commercial backups and bounded Firebase jobs on the VPS.

Install this script in the reviewed release; cron runs as the existing qf user.
Partial commercial backups are restored against the matching full database;
they deliberately omit sports histories and the separately operated NBA service.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

REPO = Path("/home/qf/quantfut")
BACKUPS = Path("/home/qf/.local/share/quantfut/commercial-backups")
TABLES = ("accounts", "sessions", "session_retired_tokens", "email_tokens", "plans",
          "subscriptions", "admin_audit", "reward_wallets", "reward_ledger",
          "reward_referrals", "reward_unlocks", "reward_provider_events",
          "reward_providers", "reward_settings", "firebase_identities",
          "account_consents", "firebase_preferences", "push_devices",
          "account_notifications", "notification_outbox")


def run(args, **kwargs):
    return subprocess.run(args, cwd=REPO, check=True, **kwargs)


def backup() -> dict:
    os.umask(0o077)
    BACKUPS.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(BACKUPS, 0o700)
    name = datetime.now(timezone.utc).strftime("commercial-%Y%m%dT%H%M%SZ.dump")
    target = BACKUPS / name
    partial = target.with_suffix(".partial")
    args = ["docker", "compose", "exec", "-T", "db", "pg_dump", "-U", "qf", "-d", "quantfut", "-Fc"]
    for table in TABLES:
        args.extend(("--table", f"public.{table}"))
    try:
        with partial.open("xb") as stream:
            run(args, stdout=stream)
        assert partial.stat().st_size > 0
        # Read the complete archive locally in the database container; no SQL writes.
        with partial.open("rb") as stream:
            run(["docker", "compose", "exec", "-T", "db", "pg_restore", "--list"],
                stdin=stream, stdout=subprocess.DEVNULL)
        partial.rename(target)
    finally:
        partial.unlink(missing_ok=True)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = target.with_suffix(".json")
    manifest.write_text(json.dumps({"file": name, "sha256": digest,
                                   "retention_days": 30, "tables": TABLES,
                                   "scope": "commercial-only; matching full database required"}), encoding="utf-8")
    cutoff = time.time() - 30 * 86400
    # Only our own regular files in this exact private directory are rotated.
    for file in BACKUPS.glob("commercial-*"):
        if not file.is_symlink() and file.is_file() and file.suffix in (".dump", ".json"):
            if file.stat().st_mtime < cutoff:
                file.unlink()
    return {"backup": name, "bytes": target.stat().st_size, "sha256": digest}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("daily", "deliver"))
    mode = parser.parse_args().mode
    if mode == "daily":
        # Expire disposable identifiers before copying the commercial data.
        run(["docker", "exec", "quantfut-api-1", "python", "-m", "qf.comercial.firebase_mantenimiento"])
        print(json.dumps(backup()))
    else:
        run(["docker", "exec", "quantfut-api-1", "python", "-m", "qf.comercial.firebase_notificaciones", "--limit", "30"])


if __name__ == "__main__":
    main()
