from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from nba.v2.fuentes import propline as pl

FIX = Path(__file__).parent / "fixtures"
LOTES = json.loads((FIX / "propline_lotes.json").read_text(encoding="utf-8"))["lotes"]
LINEAS, PROPS_PUNTOS, PROPS_ESPECIALES = LOTES[0], LOTES[1], LOTES[2]
T = datetime.fromisoformat(LINEAS["received_at"])           # 15:07 ET; el juego es a las 00:00Z


def test_decimal_desde_americano():
    assert pl.decimal(-182) == Decimal("1.549") and pl.decimal(140) == Decimal("2.400")
    assert pl.decimal(-110) == Decimal("1.909") and pl.decimal(100) == Decimal("2.000") and pl.decimal(2300) == Decimal("24.000")


def cuotas(db, **filtros):
    cond = " AND ".join(f"{k} = %s" for k in filtros) or "true"
    return db.execute(f"SELECT casa, mercado, lado, linea, cuota, fase, periodo, entidad_id, contrato_id FROM nba.cuota "
                      f"WHERE {cond} ORDER BY cuota_id", tuple(filtros.values())).fetchall()


def cargar(db, lote, recibido=None, captura=None):
    ctx = pl.Contexto(db, {}, {})
    return pl.cargar_lote(db, ctx, lote["events"], recibido or datetime.fromisoformat(lote["received_at"]), captura)


def test_lineas_solo_casas_y_eventos_utiles(base_migrada):
    db = base_migrada
    r = cargar(db, LINEAS)
    assert r["nuevas"] > 20
    assert {c[0] for c in cuotas(db)} <= pl.CASAS and {c[0] for c in cuotas(db)} == {"draftkings", "pinnacle"}
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido'").fetchone()[0] == 1   # ni el vivo ni el lejano
    dk = {(c[1], c[2], c[5]): c for c in cuotas(db, casa="draftkings") if c[1] == "h2h"}
    assert dk[("h2h", "local", "pre")][4] == Decimal("1.559") and dk[("h2h", "visit", "pre")][4] == Decimal("2.500")


def test_handicap_total_y_total_de_equipo(base_migrada):
    db = base_migrada
    cargar(db, LINEAS)
    pin = cuotas(db, casa="pinnacle")
    spread = [c for c in pin if c[1] == "spreads" and "|main|" in c[8]]
    assert {(c[2], c[3]) for c in spread} == {("local", Decimal("-4.0")), ("visit", Decimal("4.0"))}
    total = [c for c in pin if c[1] == "totals" and "|main|" in c[8]]
    assert {(c[2], c[3]) for c in total} == {("over", Decimal("229.0")), ("under", Decimal("229.0"))}
    equipo = [c for c in pin if c[1] == "team_totals" and c[7] is not None and "|main|" in c[8]]
    assert {c[3] for c in equipo} == {Decimal("116.5"), Decimal("112.5")}
    clevel = db.execute("SELECT entidad_id FROM nba.entidad WHERE tipo = 'equipo' AND id_en_fuente = 'CLE'").fetchone()[0]
    assert {c[3] for c in equipo if c[7] == clevel} == {Decimal("116.5")}


def test_alternativas_llevan_la_linea_en_el_contrato_y_las_principales_no(base_migrada):
    db = base_migrada
    cargar(db, LINEAS)
    alt = [c for c in cuotas(db, casa="draftkings") if c[1] == "totals" and "|alternate|" in c[8]]
    assert alt and all(Decimal(c[8].rsplit("|", 1)[1]) == c[3] for c in alt)
    principal = [c for c in cuotas(db, casa="draftkings") if c[1] == "totals" and "|main|" in c[8] and c[7] is None]
    assert principal and all(c[8].endswith("|") for c in principal)


def test_cierre_cuando_faltan_60_minutos_o_menos(base_migrada):
    db = base_migrada
    cargar(db, LINEAS, recibido=datetime(2026, 11, 2, 23, 30, tzinfo=UTC))       # 30 min antes del salto
    assert {c[5] for c in cuotas(db)} == {"cierre"}
    base = db.execute("SELECT count(*) FROM nba.cuota_cierre").fetchone()[0]
    assert base > 0


def test_juego_ya_empezado_o_demasiado_lejano_se_ignora(base_migrada):
    db = base_migrada
    assert cargar(db, LINEAS, recibido=datetime(2026, 11, 3, 0, 5, tzinfo=UTC))["leidas"] == 0       # ya empezó
    assert cargar(db, LINEAS, recibido=datetime(2026, 10, 30, 0, 0, tzinfo=UTC))["leidas"] == 0      # faltan > 48 h


def test_solo_cambios_y_cambio_de_precio(base_migrada):
    db = base_migrada
    r1 = cargar(db, LINEAS)
    r2 = cargar(db, LINEAS, recibido=T + timedelta(hours=1))
    assert r1["nuevas"] > 0 and r2["nuevas"] == 0 and r2["leidas"] == r1["leidas"]
    movido = json.loads(json.dumps(LINEAS))
    for b in movido["events"][0]["bookmakers"]:
        if b["key"] == "draftkings":
            for m in b["markets"]:
                if m["key"] == "h2h":
                    m["outcomes"][0]["price"] = -190
    r3 = cargar(db, movido, recibido=T + timedelta(hours=2))
    assert r3["nuevas"] == 1
    ultimo = db.execute("SELECT cuota FROM nba.cuota WHERE casa = 'draftkings' AND mercado = 'h2h' AND lado = 'local' "
                        "ORDER BY recibido_en DESC LIMIT 1").fetchone()[0]
    assert ultimo == Decimal("1.526")


def test_props_de_jugador_con_id_de_la_nba(base_migrada):
    db = base_migrada
    cargar(db, LINEAS)
    cargar(db, PROPS_PUNTOS)
    cargar(db, PROPS_ESPECIALES)
    pts = cuotas(db, mercado="player_points")
    assert pts and {c[2] for c in pts} == {"over", "under"} and all(c[7] is not None for c in pts)
    assert not any("milestone" in c[8] for c in pts)                                    # los milestone no se cargan
    nombre, fuente, id_fuente = db.execute(
        "SELECT nombre, fuente, id_en_fuente FROM nba.entidad WHERE entidad_id = %s", (pts[0][7],)).fetchone()
    assert fuente == "nba_oficial" and id_fuente.isdigit()                               # nba:1642349 → 1642349
    esp = {(c[1], c[2]) for c in cuotas(db) if c[1] in pl.ESPECIALES}
    assert esp <= {("player_double_double", "si"), ("player_triple_double", "si"), ("player_first_basket", "primero")}
    assert esp


def archivo(tmp_path, lotes, corromper=False):
    """Mini archivo con el mismo formato del recolector compartido."""
    raiz = tmp_path / "archivo"
    (raiz / "objects").mkdir(parents=True)
    con = sqlite3.connect(raiz / "index.sqlite")
    con.execute("CREATE TABLE requests (id INTEGER PRIMARY KEY, slot TEXT NOT NULL, path TEXT NOT NULL, params TEXT NOT NULL, "
                "started_at TEXT NOT NULL, state TEXT NOT NULL)")
    con.execute("CREATE TABLE receipts (request_id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, status INTEGER NOT NULL, "
                "sha256 TEXT NOT NULL, body_path TEXT NOT NULL, headers TEXT NOT NULL, error TEXT, events INTEGER NOT NULL, "
                "outcomes INTEGER NOT NULL)")
    for lote in lotes:
        cuerpo = json.dumps(lote["events"]).encode()
        huella = hashlib.sha256(cuerpo).hexdigest()
        ruta = f"objects/{huella[:2]}/{huella}.json.gz"
        (raiz / ruta).parent.mkdir(parents=True, exist_ok=True)
        (raiz / ruta).write_bytes(gzip.compress(b"{}" if corromper else cuerpo))
        con.execute("INSERT INTO requests VALUES (?,?,?,?,?,?)", (lote["request_id"], "2026-11-02T20:00:00+00:00",
                                                                  pl.RUTA_NBA, "{}", lote["received_at"], "done"))
        con.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?,?)", (lote["request_id"], lote["received_at"], 200, huella,
                                                                       ruta, "{}", None, len(lote["events"]), 0))
    con.commit()
    con.close()
    return raiz


def test_capturar_lee_el_archivo_y_avanza(base_migrada, tmp_path):
    db = base_migrada
    raiz = archivo(tmp_path, LOTES)
    r = pl.capturar(db, raiz, T)
    assert r["ok"] and r["lotes"] == 3 and r["nuevas"] > 0 and r["ultimo_id"] == LOTES[-1]["request_id"]
    assert db.execute("SELECT count(*) FROM nba.captura WHERE ok AND objetivo LIKE 'propline:%'").fetchone()[0] == 3
    cuentas = db.execute("SELECT count(*) FROM nba.cuota").fetchone()[0]
    r2 = pl.capturar(db, raiz, T)
    assert r2["lotes"] == 0 and db.execute("SELECT count(*) FROM nba.cuota").fetchone()[0] == cuentas


def test_primera_pasada_sin_historia_empieza_por_el_ultimo_slot(base_migrada, tmp_path):
    db = base_migrada
    raiz = archivo(tmp_path, LOTES)
    r = pl.capturar(db, raiz, T, desde_id=None)
    assert r["lotes"] == 3                                                # todos pertenecen al mismo slot


def test_objeto_corrupto_queda_como_captura_fallida_sin_cuotas(base_migrada, tmp_path):
    db = base_migrada
    raiz = archivo(tmp_path, LOTES[:1], corromper=True)
    r = pl.capturar(db, raiz, T)
    assert not r["ok"] and r["fallidos"] == 1
    assert db.execute("SELECT count(*) FROM nba.cuota").fetchone()[0] == 0
    assert "hash" in db.execute("SELECT error FROM nba.captura WHERE NOT ok").fetchone()[0]
