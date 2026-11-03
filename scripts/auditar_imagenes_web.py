"""Read-only audit of PUBLIC web images. Run in the API container via stdin.

Prints image coverage, HTTP failures and asset validity; never prints picks,
account data, prediction values, private artifacts or credentials.
"""
import concurrent.futures
import json
import struct
import unicodedata
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path, base=BASE):
    with urllib.request.urlopen(base + path, timeout=30) as response:
        return response.read(), response.headers.get("Content-Type", "")


def document(path, base=BASE):
    return json.loads(get(path, base)[0])


def norm(value):
    return "".join(c for c in unicodedata.normalize("NFD", value)
                   if not unicodedata.combining(c)).lower()


def image_check(path):
    try:
        body, mime = get(path)
        kind = ("png" if body.startswith(b"\x89PNG\r\n\x1a\n") else
                "jpeg" if body.startswith(b"\xff\xd8") else
                "webp" if body[:4] == b"RIFF" and body[8:12] == b"WEBP" else None)
        valid = bool(kind and mime.split(";")[0] == "image/" + kind)
        size = list(struct.unpack(">II", body[16:24])) if kind == "png" and len(body) >= 24 else None
        return {"path": path, "ok": valid, "bytes": len(body), "dimensions": size,
                **({"error": "Invalid image or MIME"} if not valid else {})}
    except Exception as exc:
        return {"path": path, "ok": False, "error": str(exc)}


def run():
    manifest = document("/web/imagenes/manifiesto.json")
    home = document("/mobile/v1/home")
    tennis = document("/web/deportes/tenis")
    agenda = home.get("agenda", [])
    teams = {str(g[side]["id"]): g[side] for g in agenda for side in ("local", "visitante")}
    missing_football = [{"id": key, "name": team.get("nombre")}
                        for key, team in teams.items() if not team.get("escudo")]
    tennis_names = sorted({e[side] for e in tennis.get("events", []) for side in ("home", "away")})
    tennis_missing = [name for name in tennis_names if norm(name) not in manifest.get("tenis", {})]
    paths = {team["escudo"] for team in teams.values() if team.get("escudo")}
    for folder in ("nba", "tenis"):
        paths.update(f"/web/imagenes/{folder}/{entry['f']}" for entry in manifest.get(folder, {}).values())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        assets = list(pool.map(image_check, sorted(paths)))
    result = {
        "version": 1,
        "scope": "Public football agenda, tennis feed and complete published image manifest",
        "football": {"events": len(agenda), "unique_teams": len(teams),
                     "teams_with_crest": len(teams) - len(missing_football), "missing": missing_football},
        "nba": {"manifest_logos": len(manifest.get("nba", {})),
                "portrait_sample": image_check("/web/imagenes/jugadores/nba/2544.png")},
        "tennis": {"events": len(tennis.get("events", [])), "unique_players": len(tennis_names),
                   "manifest_photos": len(manifest.get("tenis", {})),
                   "players_with_photo": len(tennis_names) - len(tennis_missing), "missing": tennis_missing},
        "football_portrait_sample": image_check("/web/imagenes/jugadores/futbol/874.png"),
        "assets": {"total": len(assets), "ok": sum(a["ok"] for a in assets),
                   "failures": [a for a in assets if not a["ok"]], "checks": assets},
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    run()
