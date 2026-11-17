import gzip
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from qf.ingest import cuotas_respaldo as cr
from qf.ingest import cuotas_respaldo_futbol as rf
from qf.ingest import cuotas_sharpapi as sh
from qf.ingest import odds_worker


NOW = datetime(2026, 11, 16, 23, 50, tzinfo=timezone.utc)
START = NOW + timedelta(minutes=20)
TAKEN = NOW - timedelta(minutes=10)


def fila(mercado, seleccion, linea=None, *, market_segment="full_game", **extras):
    return dict(sportsbook="draftkings", market_type=mercado, market_segment=market_segment,
                selection=seleccion, line=linea, odds_decimal=2, **extras)


def guardar(root, filas, *, deporte=None, evento="partido", tomado=TAKEN, liga="england_-_premier_league",
            local="Local", visita="Visita"):
    carpeta = root / START.date().isoformat() / evento
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / tomado.strftime("%Y%m%dT%H%M%SZ.jsonl.gz")
    cabecera = dict(evento=evento, liga=liga, local=local, visita=visita, capturado=tomado.isoformat(),
                    inicio=START.isoformat(), filas=len(filas))
    if deporte:
        cabecera["sport"] = deporte
    with gzip.open(ruta, "wt", encoding="utf-8") as archivo:
        for registro in (cabecera, *filas):
            archivo.write(json.dumps(registro) + "\n")


def sin_red(*args, **kwargs):
    pytest.fail("El respaldo local hizo una petición")


def test_futbol_carga_archivo_legacy_y_respeta_precedencia_y_privacidad(tmp_path, monkeypatch):
    guardar(tmp_path, [fila("moneyline", lado, market_segment=None) for lado in ("Local", "Draw", "Visita")]
            + [fila("total_goals", "Over", 2.5), fila("total_goals", "Under", 2.5),
               fila("total_goals", "Over", 3.5, is_stale_pregame_price=True),
               fila("team_total_goals", "Local Over", 1.5, selection_type="home_over"),
               fila("double_chance", "Visita And Draw", selection_type="away_draw")])
    meta = {"qf": {"home": "Local", "away": "Visita"}}
    monkeypatch.setattr(odds_worker, "match_meta", lambda ids: meta)
    monkeypatch.setattr(cr, "_transporte", lambda key: sin_red)
    ruta = tmp_path / "cache.json"
    partidos = [dict(match_id="qf", odds_api_key="soccer_epl", kickoff_utc=START)]
    result = rf.correr(ejecutar=True, now=NOW, key="", sp_key="", rd_key="", cache_path=ruta,
                       sharpapi_raiz=tmp_path, lista_huecos=partidos, resolutor=lambda a, b: a == b)
    assert result["sharpapi"] == 1 and result["gastado"] == 0
    entries = rf.leer_cache(rf.ruta_cache(ruta))
    assert entries["qf|sharpapi"]["odds_event"] == "partido"
    assert not rf.cuotas_de_cache(entries, "qf", NOW, (), str)
    entries["qf|rd"] = dict(fuente="therundown", captured_at=NOW.isoformat(),
                            rows=[dict(bookmaker="fanduel", market="totals", selection="over", line=2.5, price=1.9)])
    monkeypatch.setattr(rf.crd, "mostrar", lambda: True)
    cuotas = rf.cuotas_de_cache(entries, "qf", NOW, (), str, incluir_sharpapi=True)
    assert cuotas["totals:over:2.5"] == (1.9, "fanduel", NOW)
    assert cuotas["totals:under:2.5"] == (2, "draftkings", TAKEN)
    assert "totals:over:3.5" not in cuotas
    assert cuotas["h2h:draw:None"] == (2, "draftkings", TAKEN)
    assert cuotas["team_totals_home:over:1.5"] == (2, "draftkings", TAKEN)
    assert cuotas["double_chance:X2:None"] == (2, "draftkings", TAKEN)


def test_nba_prop_y_tenis_invertido_con_datos_locales(tmp_path, monkeypatch):
    guardar(tmp_path, [fila("player_points", lado, 20.5, player_name="Alex Smith") for lado in ("Over", "Under")]
            + [fila("player_points", "Over", 21.5, player_name="Alex Smith")],
            deporte="basketball", liga="nba", evento="nba")
    guardar(tmp_path, [fila("game_spread", "Visita", 2.5), fila("game_spread", "Local", -2.5)],
            deporte="tennis", liga="atp", evento="tenis", local="Visita", visita="Local")
    nba = cr.Hueco("nba", "1", None, "Local", "Visita", START, NOW - timedelta(minutes=12),
                   [dict(key="player_points|p1|20.5", market="player_points", odds_market="player_points",
                         line=20.5, player_name="Alex Smith")])
    tenis = cr.Hueco("tenis", "2", None, "Local", "Visita", START, NOW,
                     [dict(key="handicap", market="games_handicap", odds_market="spreads", line=-2.5, selection="A")])
    entries = {}
    assert cr.nivel5_sharpapi(sh.Archivo(tmp_path, NOW), [nba, tenis], entries) == 2
    monkeypatch.setattr(cr, "_ahora", lambda: NOW)
    nba_quotes = {"over": 123, "under": None}
    overlay = {"events": {"1": {"quotes": {"player_points|p1|20.5": nba_quotes}}}}
    cr.aplica_nba(overlay, entries)
    assert nba_quotes["under"] is None
    cr.aplica_nba(overlay, entries, incluir_sharpapi=True)
    assert nba_quotes["over"] == 123
    assert nba_quotes["under"]["src"] == "sharpapi" and nba_quotes["under"]["post_sello"]
    overlay = {"events": {"2": {"handicap": None}}}
    cuota = cr.aplica_tenis(overlay, entries, incluir_sharpapi=True)["events"]["2"]["handicap"]
    assert cuota["side"] == "A" and cuota["price"] == 2 and not cuota["post_sello"]


def test_rechaza_capturas_vencidas_o_futuras_y_eventos_ambiguos(tmp_path):
    ruta = tmp_path
    rows = [fila("total_goals", "Over", 2.5)]
    for evento, tomado in (("viejo", NOW - timedelta(hours=7)), ("futuro", NOW + timedelta(minutes=1))):
        guardar(ruta, rows, evento=evento, tomado=tomado)
    args = ("futbol", "Local", "Visita", START)
    assert sh.Archivo(ruta, NOW).buscar(*args, liga="soccer_epl") is None
    guardar(ruta, rows, evento="uno")
    assert sh.Archivo(ruta, NOW).buscar(*args, liga="soccer_epl")[0] == "uno"
    assert sh.Archivo(ruta, NOW).buscar(*args, liga="soccer_mexico_ligamx") is None
    guardar(ruta, rows, evento="dos")
    assert sh.Archivo(ruta, NOW).buscar(*args, liga="soccer_epl") is None


def test_comando_solo_sharpapi_desactiva_proveedores_remotos(tmp_path, monkeypatch):
    monkeypatch.setenv("CUOTAS_SHARPAPI_ARCHIVO", str(tmp_path))
    monkeypatch.setattr(cr, "settings", SimpleNamespace(cuotas_respaldo_cache=str(tmp_path / "cache.json")))
    pasadas = []
    monkeypatch.setattr(cr, "correr", lambda **kw: pasadas.append(kw))
    monkeypatch.setattr(rf, "correr", lambda **kw: pasadas.append(kw))
    assert cr.main(["--solo-sharpapi", "--ejecutar"]) == 0
    opciones = dict(ejecutar=True, max_creditos=0, key="", sp_key="", rd_key="")
    assert pasadas == [dict(deporte="todos", **opciones), opciones]


def test_mercados_adicionales_se_leen_solo_en_sharpapi(tmp_path):
    guardar(tmp_path, [fila("1st_set_moneyline", "Local", market_segment="1st_set"),
                       fila("1st_set_moneyline", "Visita", market_segment="1st_set"),
                       fila("total_tiebreaks", "Over", 0.5), fila("total_tiebreaks", "Under", 0.5)],
            deporte="tennis", liga="atp")
    items = [dict(key="set1", market="set_winner", odds_market=None, line=None, selection="A", set_number=1),
             dict(key="set2", market="set_winner", odds_market=None, line=None, selection="A", set_number=2),
             dict(key="tb", market="tiebreak", odds_market=None, line=None, selection="yes")]
    h = cr.Hueco("tenis", "t", None, "Local", "Visita", START, NOW, items)
    entries = {}
    assert cr._sin_resolver([h], entries) == []
    assert cr.nivel5_sharpapi(sh.Archivo(tmp_path, NOW), [h], entries) == 2
    assert set(entries) == {"t|set1|sharpapi", "t|tb|sharpapi"}


def test_nba_total_del_equipo_no_mezcla_local_y_visitante(tmp_path):
    guardar(tmp_path, [fila("team_total", "Over", 110.5, selection_type="home_over"),
                       fila("team_total", "Under", 110.5, selection_type="home_under"),
                       fila("team_total", "Over", 112.5, selection_type="away_over")],
            deporte="basketball", liga="nba")
    local = dict(key="local", market="team_points", odds_market=None, line=110.5, team_side="home")
    visita = dict(key="visita", market="team_points", odds_market=None, line=110.5, team_side="away")
    h = cr.Hueco("nba", "n", None, "Local", "Visita", START, NOW, [local, visita])
    entries = {}
    assert cr.nivel5_sharpapi(sh.Archivo(tmp_path, NOW), [h], entries) == 1
    assert set(entries) == {"n|local|sharpapi"}
