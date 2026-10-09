"""Provider-native coverage; ESPN IDs are not NBA IDs."""
from collections import Counter
import json
from pathlib import Path

import pyarrow.parquet as pq

from .audit import digest


def audit_hoopr(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if manifest["source"] != "sportsdataverse/hoopR-data":
        raise ValueError("expected hoopR data manifest")
    result = []
    for entry in manifest["files"]:
        if "sha256" not in entry or not entry["name"].endswith(".parquet"):
            continue
        file = manifest_path.parent / entry["name"]
        if digest(file) != entry["sha256"]:
            raise ValueError("raw integrity mismatch")
        metadata = pq.read_schema(file)
        # Avoid materializing unused timestamps and picture URLs.
        columns = [c for c in ("game_id", "game_date", "season", "season_type", "athlete_id", "team_id") if c in metadata.names]
        rows = pq.read_table(file, columns=columns).to_pylist()
        dates = sorted({str(r["game_date"])[:10] for r in rows if r.get("game_date")})
        keys = [(r.get("game_id"), r.get("athlete_id"), r.get("team_id")) for r in rows]
        result.append(dict(file=entry["name"], rows=len(rows), unique_games=len({r.get("game_id") for r in rows}),
                           first_date=dates[0] if dates else None, last_date=dates[-1] if dates else None,
                           season_types=dict(Counter(str(r.get("season_type")) for r in rows)),
                           duplicate_entity_keys=len(keys) - len(set(keys)), sha256=entry["sha256"]))
    return dict(source=manifest["source"], source_commit=manifest["commit"], id_namespace="espn",
                files=result, normalized_into_nba_dataset=False, completeness_verified=False,
                warning="Cross-provider mapping, schedule coverage and statistical reconciliation pending")
