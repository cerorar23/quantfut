"""Download selected public GitHub data blobs, never execute repository code."""
import csv
import codecs
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import tarfile
import time

import httpx

from .audit import digest, write_json


def select_shufinskiy(inventory, start=1996, end=2025):
    files = inventory["files"]
    by_name = {Path(f["path"]).name: f for f in files}
    selected = [f for f in files if f["path"] in ("README.md", "LICENSE", "description_fields.md", "list_data.txt")]
    for year in range(start, end + 1):
        for period in ("", "po_"):
            # One canonical PBP representation per season/period; no duplicate feed union.
            for family in ("nbastatsv3", "nbastats"):
                f = by_name.get(f"{family}_{period}{year}.tar.xz")
                if f:
                    selected.append(f)
                    break
            f = by_name.get(f"shotdetail_{period}{year}.tar.xz")
            if f:
                selected.append(f)
    return selected


def download_inventory(inventory, selected, root, progress=print):
    repo, commit = inventory["repository"], inventory["commit"]
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repo) or not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("invalid repository identity")
    root = Path(root) / repo.replace("/", "__") / commit
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        "source": repo, "commit": commit, "mode": "retrospective_archive", "files": []}
    entries = {e["name"]: e for e in manifest["files"]}
    with httpx.Client(timeout=60, follow_redirects=True, headers={"User-Agent": "QuantNBAResearch/0.1"}) as client:
        for item in selected:
            name = item["path"]
            if ".." in Path(name).parts or Path(name).is_absolute() or "\\" in name:
                raise ValueError("unsafe data path")
            path = root / name
            prior = entries.get(name)
            if path.exists():
                if not prior or digest(path) != prior.get("sha256"):
                    raise ValueError("untracked or changed raw file")
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            url = f"https://raw.githubusercontent.com/{repo}/{commit}/{name}"
            temporary = path.with_suffix(path.suffix + ".part")
            expected = item["size"]
            if expected > 100_000_000:
                raise ValueError("blob exceeds per-file research cap")
            hashed = hashlib.sha256()
            git_hash = hashlib.sha1(f"blob {expected}\0".encode())
            size = 0
            try:
                with client.stream("GET", url) as response:
                    response.raise_for_status()  # Stop on 403/429; no bypass/retry loop.
                    with temporary.open("wb") as file:
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > expected:
                                raise ValueError("blob size changed")
                            file.write(chunk)
                            hashed.update(chunk)
                            git_hash.update(chunk)
                if size != expected or git_hash.hexdigest() != item["sha"]:
                    raise ValueError("Git blob integrity mismatch")
                temporary.replace(path)
                entries[name] = dict(name=name, url=url, bytes=size, git_blob_sha1=item["sha"],
                                     sha256=hashed.hexdigest(), first_received_at_utc=datetime.now(UTC).isoformat())
            except Exception as exc:
                entries[name] = dict(name=name, url=url, error=type(exc).__name__, attempted_at_utc=datetime.now(UTC).isoformat())
                manifest["files"] = list(entries.values())
                write_json(manifest_path, manifest)
                raise
            manifest["files"] = list(entries.values())
            write_json(manifest_path, manifest)
            progress(f"{repo}: {name} ({size} bytes)")
            time.sleep(0.3)
    return manifest_path


def audit_tar_csv(path):
    """Read only the single expected CSV member; never extract arbitrary tar paths."""
    path = Path(path)
    expected = path.name.removesuffix(".tar.xz") + ".csv"
    with tarfile.open(path, mode="r|xz") as tar:
        member = tar.next()
        if member is None or member.name != expected or not member.isfile():
            raise ValueError("unexpected archive members")
        if member.size > 1_000_000_000:
            raise ValueError("CSV exceeds research size cap")
        with tar.extractfile(member) as stream:
            reader = csv.DictReader(codecs.getreader("utf-8-sig")(stream))
            columns = reader.fieldnames
            key = next((c for c in columns if c.lower().replace("_", "") in ("gameid", "gid")), None)
            games, rows = set(), 0
            for row in reader:
                rows += 1
                if key:
                    games.add(row[key])
        if tar.next() is not None:
            raise ValueError("unexpected archive members")
    return dict(file=path.name, rows=rows, game_id_column=key, unique_games=len(games),
                columns=columns, sha256=digest(path), validated_against_schedule=False)
