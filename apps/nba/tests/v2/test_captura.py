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


def test_espn_por_lotes_da_lo_mismo_que_de_golpe(base_nueva, monkeypatch, tmp_path):
    from nba.v2 import migrar
    migrar.aplicar(base_nueva)
    (tmp_path / "run57").mkdir()
    ruta, _ = ledger(tmp_path / "run57", [(SB, 200, SCOREBOARD, T), (INJ, 200, LESIONES, T), (INJ, 200, LESIONES, T)])
    env = {"NBA_DB_DSN": base_nueva, "NBA_CAPTURA_DIR": str(tmp_path / "datos"), "NBA_RUN57_DIR": str(ruta.parent)}
    monkeypatch.setattr(captura, "LOTE_ESPN", 1)
    r = captura.ejecutar("espn", env, AHORA)
    assert r["ultimo_seq"] == 3 and r["calendario"] == 1 and r["lesiones"] == 2
    assert json.loads((tmp_path / "datos" / "estado_espn.json").read_text()) == {"seq": 3}
    assert contar(base_nueva, "dato") > 0


def test_ejecutar_parte_oficial_con_pdf_real(base_migrada_dsn, tmp_path):
    from nba.v2.fuentes import parte_oficial as po
    pdf = (FIX / "parte_oficial_2025-10-21_06PM.pdf").read_bytes()
    url = po.BASE + "Injury-Report_2025-10-21_06PM.pdf"
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path)}
    r = captura.ejecutar("parte", env, datetime(2025, 10, 21, 23, 0, tzinfo=UTC),
                         obtener=lambda u: (200, pdf) if u == url else (403, b""))
    assert r["ok"] and r["partes_nuevos"] == 1 and contar(base_migrada_dsn, "dato") > 100


def test_nba_sin_clave_de_scrapfly_devuelve_2(base_migrada_dsn, tmp_path):
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path)}
    assert captura.principal(["nba"], env) == 2


def test_ejecutar_propline_desde_un_archivo(base_migrada_dsn, tmp_path):
    from test_propline import LOTES, archivo
    raiz = archivo(tmp_path, LOTES)
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path / "datos"), "NBA_PROPLINE_DIR": str(raiz),
           "NBA_PROPLINE_DESDE": "0"}
    r = captura.ejecutar("propline", env, AHORA)
    assert r["ok"] and r["lotes"] == 3 and contar(base_migrada_dsn, "cuota") > 0
    assert captura.principal(["propline"], {"NBA_DB_DSN": base_migrada_dsn}) == 2          # falta NBA_PROPLINE_DIR


def test_ejecutar_historico_desde_una_carpeta(base_migrada_dsn, tmp_path):
    import shutil
    fix = Path(__file__).parent / "fixtures"
    shutil.copy(fix / "historico_juegos.json", tmp_path / "games.json")
    shutil.copy(fix / "historico_betsapi.jsonl", tmp_path / "betsapi_odds.jsonl.gz.tmp")
    import gzip
    with gzip.open(tmp_path / "betsapi_odds.jsonl.gz", "wt", encoding="utf8") as f:
        f.write((fix / "historico_betsapi.jsonl").read_text(encoding="utf8"))
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path / "datos"), "NBA_HISTORICO_DIR": str(tmp_path)}
    r = captura.ejecutar("historico", env, AHORA)
    assert r["ok"] and r["juegos"]["juegos"] == 2 and r["betsapi"]["nuevas"] > 100 and "props" not in r
    r2 = captura.ejecutar("historico", env, AHORA)
    assert r2["betsapi"]["nuevas"] == 0


# El fixture está recortado; las respuestas reales de ESPN traen la liga, que el colector exige.
SCOREBOARD_NBA = json.dumps({"leagues": [{"slug": "nba"}], **json.loads(SCOREBOARD)}).encode()


def _espn_en_vivo(solicitadas, malo=None):
    def obtener(url):
        solicitadas.append(url)
        if malo and malo in url:
            return 200, b'{"otra": "cosa"}'
        return (200, SCOREBOARD_NBA) if "/scoreboard" in url else (200, LESIONES)
    return obtener


def test_espn_directo_carga_sin_ledger_y_lesiones_como_mucho_cada_hora(base_migrada_dsn, tmp_path):
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path)}
    pedidas = []
    r = captura.ejecutar("espn_directo", env, AHORA, obtener=_espn_en_vivo(pedidas))
    assert r["ok"] and r["calendario"] == 3 and r["lesiones"] == 1 and contar(base_migrada_dsn, "dato") > 0
    assert sum("/scoreboard?dates=" in u for u in pedidas) == 3 and sum("/injuries" in u for u in pedidas) == 1
    assert (tmp_path / "originales" / "espn").is_dir()
    datos = contar(base_migrada_dsn, "dato")
    pedidas.clear()
    r2 = captura.ejecutar("espn_directo", env, AHORA, obtener=_espn_en_vivo(pedidas))
    assert r2["ok"] and r2["lesiones"] == 0 and not any("/injuries" in u for u in pedidas)
    assert contar(base_migrada_dsn, "dato") == datos          # mismos cuerpos: nada nuevo


def test_espn_directo_rechaza_respuestas_que_no_son_de_la_nba(base_migrada_dsn, tmp_path):
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path)}
    r = captura.ejecutar("espn_directo", env, AHORA, obtener=_espn_en_vivo([], malo="/injuries"))
    assert not r["ok"] and r["fallidos"] == 1 and r["lesiones"] == 0 and r["calendario"] == 3
    r = captura.ejecutar("espn_directo", env, AHORA, obtener=lambda url: (403, b""))
    assert not r["ok"] and r["fallidos"] >= 3


def test_espn_directo_un_fallo_de_red_no_tumba_la_pasada(base_migrada_dsn, tmp_path):
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path)}
    def obtener(url):
        if "/injuries" in url:
            raise TimeoutError("sin respuesta")
        return 200, SCOREBOARD_NBA
    r = captura.ejecutar("espn_directo", env, AHORA, obtener=obtener)
    assert not r["ok"] and r["calendario"] == 3 and r["fallidos"] == 1
