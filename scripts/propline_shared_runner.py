#!/usr/bin/env python3
"""Host cron runner: one isolated reader, archive on the existing shared volume.

runtime.json is written by deployment: immutable image id, key file and volume.
Run this file under flock. No API credentials are passed on command lines.
"""
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone


def main():
    release = Path(__file__).resolve().parent
    runtime = json.loads((release / "runtime.json").read_text())
    image = runtime["image"]
    if not image.startswith("sha256:") or len(image) != 71:
        raise ValueError("deployment must pin the container image digest")
    key = Path(runtime["key_file"]).resolve()
    if not key.is_file():
        raise ValueError("private key file missing")
    user = str(runtime["user"])
    if not re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", user):
        raise ValueError("runtime user must be a numeric non-root uid:gid")
    cmd = ["docker", "run", "--rm", "--name", "propline-shared-capture", "--read-only",
           "--user", user, "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=64",
           "--memory=1536m", "--cpus=1", "--tmpfs", "/tmp:rw,nosuid,noexec,size=32m",
           "--network", runtime["network"], "-v", runtime["volume"] + ":/archive",
           "-v", str(key) + ":/run/secrets/propline:ro",
           "-v", str(release / "propline_shared.py") + ":/collector.py:ro",
           "-v", str(release / "propline_shared_config.json") + ":/config.json:ro",
           "--entrypoint", "python", image, "/collector.py", "capture", "--root",
           "/archive/propline_shared", "--key-file", "/run/secrets/propline", "--config", "/config.json"]
    logs = release.parent.parent / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / (datetime.now(timezone.utc).strftime("%Y-%m") + ".log")).open("a", buffering=1) as output:
        output.write(json.dumps({"runner_started_at": datetime.now(timezone.utc).isoformat(),
                                 "release": release.name}) + "\n")
        result = subprocess.run(cmd, stdout=output, stderr=subprocess.STDOUT)
        output.write(json.dumps({"runner_finished_at": datetime.now(timezone.utc).isoformat(),
                                 "exit_code": result.returncode}) + "\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
