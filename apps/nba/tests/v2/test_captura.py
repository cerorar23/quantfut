from datetime import UTC, datetime
import json
from pathlib import Path

from nba.v2 import captura
from nba.v2.fuentes import rotowire

from test_espn import INJ, LESIONES, SB, SCOREBOARD, T, ledger

FIX = Path(__file__).parent / "fixtures"
HTML = (FIX / "rotowire_lineups.html").read_bytes()
AHORA = datetime(2026, 11, 2, 22, 0, tzinfo=UTC)


def contar(dsn, tabla):
    import psycopg
    with psycopg.connect(dsn) as db:
        return db.execute(f"SELECT count(*) FROM nba.{tabla}").fetchone()[0]


def test_ejecutar_rotowire_carga_y_confirma(base_migrada_dsn, tmp_path):
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path)}
    r = captura.ejecutar("rotowire", env, AHORA, obtener=lambda url: (200, HTML) if url == rotowire.URL_LINEUPS else (404, b""))
    assert r["ok"] and r["partidos"] == 2 and contar(base_migrada_dsn, "dato") > 0
    assert (tmp_path / "originales" / "rotowire").is_dir()


def test_ejecutar_espn_avanza_el_estado_solo_tras_confirmar(base_migrada_dsn, tmp_path):
    (tmp_path / "run57").mkdir()
    ruta, blobs = ledger(tmp_path / "run57", [(SB, 200, SCOREBOARD, T), (INJ, 200, LESIONES, T)])
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path / "datos"), "NBA_RUN57_DIR": str(ruta.parent)}
    r = captura.ejecutar("espn", env, AHORA)
    assert r["ok"] and r["ultimo_seq"] == 2
    assert json.loads((tmp_path / "datos" / "estado_espn.json").read_text()) == {"seq": 2}
    datos = contar(base_migrada_dsn, "dato")
    r2 = captura.ejecutar("espn", env, AHORA)                       # sin recibos nuevos
    assert r2["ultimo_seq"] == 2 and contar(base_migrada_dsn, "dato") == datos


def test_principal_sin_dsn_o_con_fuente_mala_devuelve_2(tmp_path):
    assert captura.principal(["rotowire"], {}) == 2
    assert captura.principal(["otra"], {"NBA_DB_DSN": "x"}) == 2
    assert captura.principal([], {}) == 2


def test_principal_rechaza_la_base_de_futbol(tmp_path, capsys):
    env = {"NBA_DB_DSN": "dbname=quantfut", "NBA_CAPTURA_DIR": str(tmp_path)}
    assert captura.principal(["rotowire"], env) == 1
    assert "ValueError" in capsys.readouterr().out
