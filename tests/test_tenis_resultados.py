"""Pruebas del respaldo de resultados de tenis con SportsAPIPro (`/v2/tennis/schedule/{fecha}`)."""
import gzip
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qf.ingest import tenis_resultados as tr

INICIO = datetime(2026, 11, 11, 16, 0, tzinfo=timezone.utc)
NOW = INICIO + timedelta(hours=3)


def _evento(eid=101, local="Matteo Martineau", visita="Hugo Gaston", inicio=INICIO, *,
            tipo="finished", desc="Ended", winner=1, home_score=None, away_score=None,
            torneo="Lyon, France"):
    return {
        "id": eid,
        "startTimestamp": int(inicio.timestamp()),
        "tournament": {"name": torneo, "category": {"name": "Challenger"}},
        "homeTeam": {"name": local},
        "awayTeam": {"name": visita},
        "status": {"type": tipo, "description": desc},
        "winnerCode": winner,
        "homeScore": home_score if home_score is not None else {
            "current": 2, "period1": 6, "period2": 6, "period3": 6,
            "period2TieBreak": 4,
        },
        "awayScore": away_score if away_score is not None else {
            "current": 1, "period1": 3, "period2": 7, "period3": 2,
            "period2TieBreak": 7,
        },
    }


def _crear_equivalencias(raiz: Path, fecha: str, received_at: datetime, events: list[dict]):
    raiz.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(raiz / "index.sqlite")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, fecha TEXT NOT NULL,
            status INTEGER NOT NULL, sha256 TEXT NOT NULL, body_path TEXT NOT NULL, eventos INTEGER NOT NULL);
    """)
    body = json.dumps({"events": events}).encode()
    sha = hashlib.sha256(body).hexdigest()
    rel = Path("objects") / sha[:2] / f"{sha}.json.gz"
    (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
    (raiz / rel).write_bytes(gzip.compress(body, mtime=0))
    with db:
        db.execute("INSERT INTO receipts(received_at,fecha,status,sha256,body_path,eventos) VALUES(?,?,?,?,?,?)",
                   (received_at.isoformat(), fecha, 200, sha, rel.as_posix(), len(events)))
    db.close()


def test_califica_h2h_totales_y_handicap_incluyendo_nombres_invertidos_e_iniciales():
    ev = _evento()  # local: 6+6+6 = 18 juegos; visita: 3+7+2 = 12 juegos; total = 30; diff = +6
    # El punto del tiebreak (4 / 7) NO entra en la suma de juegos.
    assert tr.calificar_evento(ev, False, "h2h", "home") == "win"
    assert tr.calificar_evento(ev, False, "h2h", "away") == "loss"
    assert tr.calificar_evento(ev, False, "total_games", "over", 29.5) == "win"
    assert tr.calificar_evento(ev, False, "total_games", "under", 29.5) == "loss"
    assert tr.calificar_evento(ev, False, "totals", "over", 30.0) == "push"
    assert tr.calificar_evento(ev, False, "handicap_games", "home", -3.5) == "win"
    assert tr.calificar_evento(ev, False, "handicap_games", "away", 3.5) == "loss"
    assert tr.calificar_evento(ev, False, "spreads", "home", -6.0) == "push"

    # Cuando SofaScore trae local/visitante invertidos respecto a PropLine, se invierten ganador y juegos.
    assert tr.calificar_evento(ev, True, "h2h", "away") == "win"
    assert tr.calificar_evento(ev, True, "h2h", "home") == "loss"
    assert tr.calificar_evento(ev, True, "handicap_games", "away", -3.5) == "win"
    assert tr.calificar_evento(ev, True, "handicap_games", "home", 3.5) == "loss"

    hallado = tr.buscar_evento({1: (NOW, "2026-11-11", _evento(local="Hugo Gaston", visita="Matteo Martineau"))},
                               "M. Martineau", "H. Gaston", INICIO + timedelta(hours=3))
    assert hallado is not None and hallado[1] is True


def test_supertiebreak_retirada_walkover_cancelado_y_dobles():
    walk = _evento(desc="Walkover", winner=1, home_score={}, away_score={})
    canc = _evento(tipo="canceled", desc="Canceled", winner=None, home_score={}, away_score={})
    ret = _evento(desc="Retired", winner=1, home_score={"current": 1, "period1": 6},
                  away_score={"current": 0, "period1": 2})
    live = _evento(tipo="inprogress", desc="2nd set", winner=None)
    for ev in (walk, canc):
        assert tr.calificar_evento(ev, False, "h2h", "home") == "void"
        assert tr.calificar_evento(ev, False, "total_games", "over", 21.5) == "void"
    assert tr.calificar_evento(ret, False, "h2h", "home") is None
    assert tr.calificar_evento(live, False, "h2h", "home") is None

    # 3er set supertiebreak (>= 10 puntos): h2h sigue siendo válido, juegos no se adivina.
    super_tb = _evento(home_score={"current": 2, "period1": 6, "period2": 3, "period3": 10},
                       away_score={"current": 1, "period1": 3, "period2": 6, "period3": 7})
    assert tr.calificar_evento(super_tb, False, "h2h", "home") == "win"
    assert tr.calificar_evento(super_tb, False, "total_games", "over", 21.5) is None
    assert tr.calificar_evento(super_tb, False, "handicap_games", "home", -1.5) is None

    # Dobles y partidos duplicados ambiguos nunca emparejan.
    doble = _evento(local="A. Uno / B. Dos", visita="C. Tres / D. Cuatro", torneo="Lyon, Doubles")
    assert tr.buscar_evento({1: (NOW, "2026-11-11", doble)}, "A. Uno", "C. Tres", INICIO) is None
    dup = {1: (NOW, "2026-11-11", _evento(eid=1)), 2: (NOW, "2026-11-11", _evento(eid=2))}
    assert tr.buscar_evento(dup, "Matteo Martineau", "Hugo Gaston", INICIO) is None


def test_consulta_bajo_demanda_espera_min_edad_respeta_cache_y_archiva_en_sqlite(tmp_path):
    calls = []
    eq_dir = tmp_path / "eq"
    res_dir = tmp_path / "res"
    _crear_equivalencias(eq_dir, "2026-11-11", INICIO - timedelta(hours=1),
                         [_evento(tipo="notstarted", desc="Not started", winner=None)])

    def fake_http(url, key):
        calls.append(url)
        return 200, json.dumps({"events": [_evento(winner=1)]}).encode()

    # Antes de MIN_EDAD (2h30): 0 peticiones, devuelve None porque en eq aún estaba notstarted.
    with tr.RespaldoTenis("CLAVE", raiz=res_dir, eq_raiz=eq_dir, call=fake_http,
                          clock=lambda: INICIO + timedelta(hours=2)) as r:
        assert r.resolver("Matteo Martineau", "Hugo Gaston", INICIO, "h2h", "away",
                          now=INICIO + timedelta(hours=2)) is None
        assert calls == []

    # Pasada MIN_EDAD: 1 única petición para la fecha NY del partido, resuelve y archiva en SQLite.
    with tr.RespaldoTenis("CLAVE", raiz=res_dir, eq_raiz=eq_dir, call=fake_http, clock=lambda: NOW) as r:
        assert r.resolver("Matteo Martineau", "Hugo Gaston", INICIO, "h2h", "away", now=NOW) == "loss"
        assert r.resolver("Matteo Martineau", "Hugo Gaston", INICIO, "total_games", "over", 25.5, now=NOW) == "win"
        assert calls == ["https://api.sportsapipro.com/v2/tennis/schedule/2026-11-11"]
        assert r.hits_api == 1 and r.hits_archivo == 1

    # Segunda corrida (incluso una instancia nueva): 0 peticiones porque ya está archivado terminado.
    calls.clear()
    with tr.RespaldoTenis("CLAVE", raiz=res_dir, eq_raiz=eq_dir, call=fake_http,
                          clock=lambda: NOW + timedelta(minutes=10)) as r2:
        assert r2.resolver("Matteo Martineau", "Hugo Gaston", INICIO, "h2h", "home",
                           now=NOW + timedelta(minutes=10)) == "win"
        assert calls == [] and r2.hits_archivo == 1


def test_respeta_cooldown_tope_diario_429_y_carpeta_solo_lectura(tmp_path):
    calls = []

    def inprogress_http(url, key):
        calls.append(url)
        return 200, json.dumps({"events": [_evento(tipo="inprogress", desc="2nd set", winner=None)]}).encode()

    res_dir = tmp_path / "res"
    with tr.RespaldoTenis("CLAVE", raiz=res_dir, eq_raiz=tmp_path / "no_eq",
                          call=inprogress_http, clock=lambda: NOW) as r:
        assert r.resolver("Matteo Martineau", "Hugo Gaston", INICIO, "h2h", "home", now=NOW) is None
        assert len(calls) == 1  # lo halló en d0 en juego; no gasta llamadas en d0±1
    # 20 min después: cooldown (45 min) evita repetir la misma fecha.
    with tr.RespaldoTenis("CLAVE", raiz=res_dir, eq_raiz=tmp_path / "no_eq",
                          call=inprogress_http, clock=lambda: NOW + timedelta(minutes=20)) as r:
        assert r.resolver("Matteo Martineau", "Hugo Gaston", INICIO, "h2h", "home",
                          now=NOW + timedelta(minutes=20)) is None
        assert len(calls) == 1
    # Pasado el cooldown: sí refresca.
    tarde = NOW + timedelta(minutes=50)
    with tr.RespaldoTenis("CLAVE", raiz=res_dir, eq_raiz=tmp_path / "no_eq",
                          call=lambda u, k: (200, json.dumps({"events": [_evento(winner=1)]}).encode()),
                          clock=lambda: tarde) as r:
        assert r.resolver("Matteo Martineau", "Hugo Gaston", INICIO, "h2h", "home", now=tarde) == "win"

    # Ante 429 detiene la corrida inmediatamente y nunca vuelve a pedir.
    llamadas_429 = []
    with tr.RespaldoTenis("CLAVE", raiz=tmp_path / "res429", eq_raiz=tmp_path / "no_eq",
                          call=lambda u, k: llamadas_429.append(u) or (429, b"{}"),
                          clock=lambda: NOW) as r:
        assert r.resolver("Jugador A", "Jugador B", INICIO, "h2h", "home", now=NOW) is None
        assert r.agotado is True and len(llamadas_429) == 1
        assert r.resolver("Otro A", "Otro B", INICIO, "h2h", "home", now=NOW) is None
        assert len(llamadas_429) == 1

    # Si `raiz` es un archivo (impide mkdir/SQLite escribible), resuelve igual sin caerse.
    archivo_bloqueo = tmp_path / "es_archivo"
    archivo_bloqueo.write_text("ro")
    with tr.RespaldoTenis("CLAVE", raiz=archivo_bloqueo, eq_raiz=tmp_path / "no_eq",
                          call=lambda u, k: (200, json.dumps({"events": [_evento(winner=1)]}).encode()),
                          clock=lambda: NOW) as r:
        assert r.resolver("Matteo Martineau", "Hugo Gaston", INICIO, "h2h", "home", now=NOW) == "win"
