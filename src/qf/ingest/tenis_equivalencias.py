"""Equivalencia de jugadores de tenis: `player_key` de API-Tennis <-> id de SofaScore (SportsAPIPro).

API-Tennis vence y no se renueva (31-oct-2026). El motor de tenis y su historia usan su `player_key`;
SportsAPIPro devuelve SofaScore con otros ids. Mientras API-Tennis siga respondiendo se archiva el
calendario de SportsAPIPro (ayer, hoy y mañana: 3 peticiones) y se empareja cada partido ATP/WTA
individual con los ya archivados de API-Tennis para llenar la tabla `equivalencias`.

Solo biblioteca estándar; corre en el host. Los originales se archivan con la hora real de recepción.
Un partido solo empareja si es el único candidato (misma pareja de jugadores, +-36 h).

    capture   archiva el calendario de SportsAPIPro (3 fechas)
    match     empareja con los originales de API-Tennis y actualiza `equivalencias`
    status    cobertura de la tabla
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.sportsapipro.com/v2/tennis/schedule/%s"
UTC = timezone.utc
VENTANA = timedelta(hours=36)
CIRCUITOS = {"ATP", "WTA"}


def now():
    return datetime.now(UTC)


def read_key(path):
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("SPORTSAPIPRO_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise ValueError("SPORTSAPIPRO_KEY ausente")


HEADERS = {"User-Agent": "Mozilla/5.0 qf-tenis"}  # con el de urllib Cloudflare responde 403 (error 1010)


def http(url, key, timeout=60):
    req = urllib.request.Request(url, headers={**HEADERS, "x-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def connect(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "index.sqlite", timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
      CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, fecha TEXT NOT NULL, status INTEGER NOT NULL,
        sha256 TEXT NOT NULL, body_path TEXT NOT NULL, eventos INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS equivalencias (
        player_key INTEGER NOT NULL, sofascore_id INTEGER NOT NULL, nombre_at TEXT, nombre_ss TEXT,
        partidos INTEGER NOT NULL, primera TEXT NOT NULL, ultima TEXT NOT NULL,
        PRIMARY KEY (player_key, sofascore_id));
      CREATE TABLE IF NOT EXISTS partidos_emparejados (
        event_key INTEGER PRIMARY KEY, sofascore_event INTEGER NOT NULL, at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS torneos (
        tournament_key INTEGER NOT NULL, utid INTEGER NOT NULL, nombre_at TEXT, nombre_ss TEXT,
        partidos INTEGER NOT NULL, PRIMARY KEY (tournament_key, utid));
      CREATE TRIGGER IF NOT EXISTS inmutable_receipts_u BEFORE UPDATE ON receipts
        BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
      CREATE TRIGGER IF NOT EXISTS inmutable_receipts_d BEFORE DELETE ON receipts
        BEGIN SELECT RAISE(ABORT,'immutable receipt'); END;
    """)
    cols = {r[1] for r in db.execute("PRAGMA table_info(partidos_emparejados)")}
    for col, tipo in (("first_key", "INTEGER"), ("second_key", "INTEGER"), ("directo", "INTEGER"),
                      ("tournament_key", "INTEGER"), ("utid", "INTEGER")):
        if col not in cols:
            db.execute("ALTER TABLE partidos_emparejados ADD COLUMN %s %s" % (col, tipo))
    db.commit()
    return db


def put_object(root, body):
    sha = hashlib.sha256(body).hexdigest()
    rel = Path("objects") / sha[:2] / (sha + ".json.gz")
    path = Path(root) / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(body, mtime=0))
    return sha, rel.as_posix()


def capture(root, key, call=http, clock=now):
    """Archiva el calendario de ayer, hoy y mañana (SportsAPIPro agrupa por día de Nueva York)."""
    db = connect(root)
    hoy = clock().date()
    hechos = []
    for delta in (-1, 0, 1):
        fecha = (hoy + timedelta(days=delta)).isoformat()
        status, body = call(API % fecha, key)
        recibido = clock()
        sha, rel = put_object(root, body)
        try:
            eventos = len(json.loads(body).get("events") or []) if status == 200 else 0
        except ValueError:
            eventos = 0
        with db:
            db.execute("INSERT INTO receipts(received_at,fecha,status,sha256,body_path,eventos) VALUES(?,?,?,?,?,?)",
                       (recibido.isoformat(), fecha, status, sha, rel, eventos))
        hechos.append((fecha, status, eventos))
    return hechos


def norm(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", t.replace("-", " "))).strip()


def inicial_apellido(nombre):
    """«J-L. Struff» y «J. Struff» -> ('j', 'struff'). Sin inicial reconocible devuelve None."""
    partes = norm(nombre).split()
    if len(partes) < 2:
        return None
    return partes[0][0], partes[-1]


def mismo_jugador(a, b):
    na, nb = norm(a), norm(b)
    if na and na == nb:
        return True
    ia, ib = inicial_apellido(a), inicial_apellido(b)
    return ia is not None and ia == ib


def eventos_sofascore(root, db):
    """Partidos individuales ATP/WTA de todos los calendarios archivados, sin repetir el id."""
    out = {}
    for r in db.execute("SELECT body_path FROM receipts WHERE status=200 ORDER BY id"):
        for e in json.loads(gzip.decompress((Path(root) / r["body_path"]).read_bytes())).get("events") or []:
            cat = ((e.get("tournament") or {}).get("category") or {}).get("name")
            if cat in CIRCUITOS and "Doubles" not in (e["tournament"].get("name") or ""):
                out[e["id"]] = e
    return list(out.values())


def eventos_api_tennis(carpeta):
    """Originales de API-Tennis (`*/response.json`): partidos individuales; de cada `event_key` manda la versión MÁS
    RECIENTE recibida (`receipt.json`), no la de la carpeta que toque por orden alfabético (ids aleatorios)."""
    archivos = []
    for f in Path(carpeta).glob("*/response.json"):
        try:
            recibido = json.loads((f.parent / "receipt.json").read_text(encoding="utf-8")).get("received_at") or ""
        except (OSError, ValueError):
            recibido = ""
        archivos.append((str(recibido), f.parent.name, f))
    out = {}
    for _, _, f in sorted(archivos):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for e in (data.get("result") if isinstance(data, dict) else None) or []:
            if "Singles" in (e.get("event_type_type") or "") and e.get("first_player_key") and e.get("second_player_key"):
                out[e["event_key"]] = e
    return list(out.values())


def emparejar(at, ss):
    """Devuelve [(evento_at, evento_ss)] solo cuando hay un único candidato."""
    por_apellido = defaultdict(list)
    for e in ss:
        for lado in ("homeTeam", "awayTeam"):
            ia = inicial_apellido((e.get(lado) or {}).get("shortName") or e[lado].get("name"))
            if ia:
                por_apellido[ia[1]].append(e)
    pares = []
    for x in at:
        a1, a2 = x["event_first_player"], x["event_second_player"]
        ia = inicial_apellido(a1)
        if not ia:
            continue
        try:
            t = datetime.fromisoformat(x["event_date"] + "T" + (x.get("event_time") or "12:00")).replace(tzinfo=UTC)
        except ValueError:
            continue
        cand = {}
        for e in por_apellido.get(ia[1], []):
            h, v = e["homeTeam"], e["awayTeam"]
            nh, nv = h.get("shortName") or h["name"], v.get("shortName") or v["name"]
            directo = mismo_jugador(a1, nh) and mismo_jugador(a2, nv)
            cruzado = mismo_jugador(a1, nv) and mismo_jugador(a2, nh)
            inicio = datetime.fromtimestamp(e["startTimestamp"], UTC)
            if (directo or cruzado) and abs(inicio - t) <= VENTANA:
                cand[e["id"]] = (e, directo)
        if len(cand) == 1:
            pares.append((x, *next(iter(cand.values()))))
    return pares


def match(root, carpeta_api_tennis, clock=now):
    db = connect(root)
    ss = eventos_sofascore(root, db)
    ahora = clock().isoformat()
    nuevos = 0
    conocidos = {r[0] for r in db.execute("SELECT event_key FROM partidos_emparejados")}
    completos = {r[0] for r in db.execute("SELECT event_key FROM partidos_emparejados WHERE first_key IS NOT NULL")}
    at = [x for x in eventos_api_tennis(carpeta_api_tennis) if x["event_key"] not in completos]
    with db:
        for x, e, directo in emparejar(at, ss):
            h, v = e["homeTeam"], e["awayTeam"]
            p1, p2 = (h, v) if directo else (v, h)
            if x["event_key"] not in conocidos:
                for key, nombre, jugador in ((x["first_player_key"], x["event_first_player"], p1),
                                             (x["second_player_key"], x["event_second_player"], p2)):
                    db.execute(
                        "INSERT INTO equivalencias(player_key,sofascore_id,nombre_at,nombre_ss,partidos,primera,ultima)"
                        " VALUES(?,?,?,?,1,?,?) ON CONFLICT(player_key,sofascore_id) DO UPDATE SET"
                        " partidos=partidos+1, ultima=excluded.ultima",
                        (int(key), int(jugador["id"]), nombre, jugador.get("shortName") or jugador["name"], ahora, ahora))
                nuevos += 1
            utid = ((e.get("tournament") or {}).get("uniqueTournament") or {}).get("id")
            tk = x.get("tournament_key")
            if tk and utid:
                db.execute(
                    "INSERT INTO torneos(tournament_key,utid,nombre_at,nombre_ss,partidos) VALUES(?,?,?,?,1)"
                    " ON CONFLICT(tournament_key,utid) DO UPDATE SET partidos=partidos+1",
                    (int(tk), int(utid), x.get("tournament_name"), e["tournament"].get("name")))
            db.execute(
                "INSERT INTO partidos_emparejados(event_key,sofascore_event,at,first_key,second_key,directo,tournament_key,utid)"
                " VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(event_key) DO UPDATE SET first_key=excluded.first_key,"
                " second_key=excluded.second_key, directo=excluded.directo, tournament_key=excluded.tournament_key,"
                " utid=excluded.utid",
                (x["event_key"], e["id"], ahora, int(x["first_player_key"]), int(x["second_player_key"]), int(directo),
                 int(tk) if tk else None, utid))
    return {"api_tennis": len(at), "sofascore": len(ss), "emparejados_nuevos": nuevos}


def status(root):
    db = connect(root)
    jugadores = db.execute("SELECT count(DISTINCT player_key) FROM equivalencias").fetchone()[0]
    conflictos = db.execute("SELECT count(*) FROM (SELECT player_key FROM equivalencias GROUP BY 1 HAVING count(*) > 1)"
                            ).fetchone()[0]
    inversos = db.execute("SELECT count(*) FROM (SELECT sofascore_id FROM equivalencias GROUP BY 1 HAVING count(*) > 1)"
                          ).fetchone()[0]
    return {"jugadores": jugadores, "partidos_emparejados": db.execute("SELECT count(*) FROM partidos_emparejados").fetchone()[0],
            "player_key_con_varios_ids": conflictos, "ids_sofascore_con_varias_keys": inversos,
            "torneos": db.execute("SELECT count(DISTINCT tournament_key) FROM torneos").fetchone()[0],
            "calendarios": db.execute("SELECT count(*) FROM receipts WHERE status=200").fetchone()[0]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["capture", "match", "status"])
    ap.add_argument("--root", required=True)
    ap.add_argument("--key-file")
    ap.add_argument("--api-tennis-dir")
    a = ap.parse_args(argv)
    if a.command == "capture":
        out = capture(a.root, read_key(a.key_file))
        ok = all(s == 200 for _, s, _ in out)
    elif a.command == "match":
        out, ok = match(a.root, a.api_tennis_dir), True
    else:
        out, ok = status(a.root), True
    print(json.dumps({"at": now().isoformat(), "result": out}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
