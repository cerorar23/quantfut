from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from nba.v2 import identidad
from nba.v2.fuentes import historico_cuotas as hc

FIX = Path(__file__).parent / "fixtures"


def cuotas(db, **filtros):
    cond = " AND ".join(f"{k} = %s" for k in filtros) or "true"
    return db.execute(f"SELECT casa, mercado, periodo, lado, linea, cuota, fase, recibido_en, contrato_id, entidad_id "
                      f"FROM nba.cuota WHERE {cond} ORDER BY recibido_en, cuota_id", tuple(filtros.values())).fetchall()


def test_ids_de_equipo_de_la_nba():
    from nba.v2 import equipos
    assert len(equipos.NBA_IDS) == 30 and set(equipos.NBA_IDS.values()) == set(equipos.TRICODES)
    assert equipos.NBA_IDS[1610612765] == "DET" and equipos.NBA_IDS[1610612739] == "CLE" and equipos.NBA_IDS[1610612760] == "OKC"


def test_catalogo_de_juegos(base_migrada):
    db = base_migrada
    r = hc.cargar_juegos(db, FIX / "historico_juegos.json")
    assert r["juegos"] == 2
    ids = {x[0] for x in db.execute("SELECT id_en_fuente FROM nba.entidad WHERE tipo = 'partido' AND fuente = 'nba_oficial'")}
    assert ids == {"0022300061", "0022300062"}
    assert hc.cargar_juegos(db, FIX / "historico_juegos.json")["juegos"] == 2
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido'").fetchone()[0] == 2


def test_betsapi_trayectoria_orientacion_y_fases(base_migrada):
    db = base_migrada
    r = hc.cargar_betsapi(db, FIX / "historico_betsapi.jsonl")
    assert r["ok"] and r["nuevas"] == r["leidas"] > 100
    assert {c[0] for c in cuotas(db)} == {"bet365"} and {c[1] for c in cuotas(db)} == {"h2h", "spreads", "totals"}
    assert {c[2] for c in cuotas(db)} == {0, 101, 1}
    tip = datetime(2023, 10, 24, 23, 30, tzinfo=UTC)
    ml = [c for c in cuotas(db, mercado="h2h", periodo=0) if "0022300061" and c[8].endswith(":ml_game")]
    apertura = [c for c in ml if c[7] == tip - timedelta(seconds=6339691)]
    assert {(c[3], c[5]) for c in apertura} == {("local", Decimal("1.476")), ("visit", Decimal("2.750"))}
    sp = [c for c in cuotas(db, mercado="spreads", periodo=0) if c[7] == tip - timedelta(seconds=6339691)]
    assert {(c[3], c[4]) for c in sp} == {("local", Decimal("-5.00")), ("visit", Decimal("5.00"))}
    tot = [c for c in cuotas(db, mercado="totals", periodo=0) if c[7] == tip - timedelta(seconds=736)]
    assert {(c[3], c[4], c[5]) for c in tot} == {("over", Decimal("228.50"), Decimal("1.869")),
                                                 ("under", Decimal("228.50"), Decimal("1.869"))}
    assert {c[6] for c in tot} == {"cierre"} and {c[6] for c in apertura} == {"pre"}


def test_betsapi_une_el_juego_por_id_de_la_nba_y_es_idempotente(base_migrada):
    db = base_migrada
    hc.cargar_juegos(db, FIX / "historico_juegos.json")
    antes = db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido' AND canonica_id = entidad_id").fetchone()[0]
    hc.cargar_betsapi(db, FIX / "historico_betsapi.jsonl")
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido' AND canonica_id = entidad_id").fetchone()[0] == antes
    n = db.execute("SELECT count(*) FROM nba.cuota").fetchone()[0]
    assert hc.cargar_betsapi(db, FIX / "historico_betsapi.jsonl")["nuevas"] == 0
    assert db.execute("SELECT count(*) FROM nba.cuota").fetchone()[0] == n
    cap = db.execute("SELECT fase, sha256, fuente FROM nba.captura WHERE objetivo LIKE 'betsapi:%'").fetchall()
    assert cap == [("historico", hashlib.sha256((FIX / "historico_betsapi.jsonl").read_bytes()).hexdigest(), "betsapi")]


def test_props_de_the_odds_api_con_id_de_jugador(base_migrada):
    db = base_migrada
    local, visitante = identidad.equipo(db, "BOS"), identidad.equipo(db, "NYK")
    identidad.partido(db, "nba_oficial", "0022400061", date(2024, 10, 22), local, visitante, "2024-25")
    r = hc.cargar_props(db, FIX / "historico_props_odds.jsonl")
    assert r["nuevas"] == r["leidas"] > 50
    filas = cuotas(db)
    assert {c[0] for c in filas} <= {"draftkings", "fanduel", "bovada"} and {c[3] for c in filas} == {"over", "under"}
    assert all(c[9] is not None for c in filas)
    primera = json.loads((FIX / "historico_props_odds.jsonl").read_text().splitlines()[0])
    assert any(c[7] == datetime.fromisoformat(primera["snapshot_utc"]) and c[4] == Decimal(str(primera["line"])).quantize(Decimal("0.01"))
               for c in filas)
    id_nba = db.execute("SELECT id_en_fuente FROM nba.entidad WHERE entidad_id = %s", (filas[0][9],)).fetchone()[0]
    assert id_nba.isdigit()


def test_props_de_un_juego_sin_partido_se_omiten(base_migrada):
    r = hc.cargar_props(base_migrada, FIX / "historico_props_odds.jsonl")
    assert r["leidas"] == 0 and base_migrada.execute("SELECT count(*) FROM nba.cuota").fetchone()[0] == 0


def test_moneyline_de_the_odds_api(base_migrada, tmp_path):
    db = base_migrada
    carpeta = tmp_path / "h2h"
    carpeta.mkdir()
    (carpeta / "20241101T2225Z.json").write_text((FIX / "historico_h2h_oddsapi.json").read_text())
    r = hc.cargar_h2h(db, carpeta)
    assert r["archivos"] == 1 and r["nuevas"] == 4
    filas = cuotas(db)
    assert {(c[0], c[1], c[3]) for c in filas} == {("pinnacle", "h2h", "local"), ("pinnacle", "h2h", "visit")}
    assert {c[6] for c in filas} == {"cierre"}                                  # faltaban 44 min
    assert hc.cargar_h2h(db, carpeta)["nuevas"] == 0
    assert db.execute("SELECT count(*) FROM nba.entidad WHERE tipo = 'partido' AND canonica_id = entidad_id").fetchone()[0] == 2


def test_props_con_precio_no_valido_se_omiten(base_migrada, tmp_path):
    db = base_migrada
    identidad.partido(db, "nba_oficial", "0022400061", date(2024, 10, 22), identidad.equipo(db, "BOS"), identidad.equipo(db, "NYK"),
                      "2024-25")
    fila = json.loads((FIX / "historico_props_odds.jsonl").read_text().splitlines()[0])
    malo = dict(fila, under=1.0)
    archivo = tmp_path / "p.jsonl"
    archivo.write_text("\n".join([json.dumps(malo), json.dumps(fila)]) + "\n")
    r = hc.cargar_props(db, archivo)
    assert r["leidas"] == 2                                                    # solo la fila válida (over y under)


def test_varias_lineas_del_mismo_jugador_y_casa_en_una_foto_no_se_pisan(base_migrada, tmp_path):
    db = base_migrada
    identidad.partido(db, "nba_oficial", "0022400061", date(2024, 10, 22), identidad.equipo(db, "BOS"), identidad.equipo(db, "NYK"),
                      "2024-25")
    fila = json.loads((FIX / "historico_props_odds.jsonl").read_text().splitlines()[0])
    otra = dict(fila, line=fila["line"] + 2, over=2.4, under=1.55)
    archivo = tmp_path / "p.jsonl"
    archivo.write_text("\n".join([json.dumps(fila), json.dumps(otra)]) + "\n")
    r = hc.cargar_props(db, archivo)
    assert r["leidas"] == 4 and r["nuevas"] == 4
