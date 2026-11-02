"""Captura de SharpAPI (plan Free): selección de partidos, momentos pendientes, páginas y archivo de salida."""
import gzip
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _cargar():
    ruta = Path(__file__).resolve().parents[1] / "scripts" / "sharpapi_captura.py"
    spec = importlib.util.spec_from_file_location("sharpapi_captura", ruta)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


C = _cargar()
AHORA = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def _evento(id_, horas, books=("draftkings", "fanduel"), local="Newcastle", visita="Everton"):
    return {"id": id_, "league": "england_-_premier_league", "home_team": local, "away_team": visita, "books": list(books),
            "start_time": (AHORA + timedelta(hours=horas)).strftime("%Y-%m-%dT%H:%M:%SZ")}


def test_elige_solo_partidos_reales_con_casa_admitida_dentro_del_horizonte():
    eventos = [_evento("a", 3), _evento("b", 30), _evento("c", -1), _evento("d", 5, books=("bet365",)),
               _evento("e", 5, local=""), _evento("f", 1, books=("fanduel",)), {"id": "g", "home_team": "x", "away_team": "y"}]
    assert [e["id"] for e, _ in C.elegir_eventos(eventos, AHORA)] == ["f", "a"]  # ordenados por inicio


def test_momentos_pendientes_se_capturan_una_vez_y_los_anteriores_quedan_hechos():
    inicio = AHORA + timedelta(minutes=100)
    pend = C.momentos_pendientes(inicio, AHORA, [])
    assert pend == [1440, 360, 120]                                               # a 100 min ya pasaron los tres momentos
    assert C.marcar_hechos([], pend) == [1440, 360, 120]                          # una sola captura los deja hechos
    assert C.momentos_pendientes(inicio + timedelta(hours=30), AHORA, []) == []   # fuera de todos los momentos
    assert C.momentos_pendientes(AHORA + timedelta(minutes=55), AHORA, [1440, 360, 120]) == [60]
    assert C.momentos_pendientes(AHORA + timedelta(minutes=10), AHORA, [1440, 360, 120, 60]) == [15]
    assert C.momentos_pendientes(AHORA + timedelta(minutes=10), AHORA, [1440, 360, 120, 60, 15]) == []
    assert C.momentos_pendientes(AHORA + timedelta(hours=5), AHORA, []) == [1440, 360]
    assert C.marcar_hechos([], [1440, 360]) == [1440, 360]                        # a 5 h solo quedan hechos 24 h y 6 h
    assert C.momentos_pendientes(AHORA + timedelta(hours=5), AHORA, [1440, 360]) == []


def test_compactar_quita_lo_pesado_y_conserva_la_cuota():
    fila = {"sportsbook": "draftkings", "market_type": "anytime_goal_scorer", "selection": "Dan Burn", "odds_decimal": 18,
            "line": None, "timestamp": "2026-11-02T02:43:02Z", "player_name": "Dan Burn", "deep_link": "https://x", "home": {"id": 1},
            "odds_american": 1700, "is_main_line": True}
    c = C.compactar(fila)
    assert c == {"sportsbook": "draftkings", "market_type": "anytime_goal_scorer", "selection": "Dan Burn", "odds_decimal": 18,
                 "timestamp": "2026-11-02T02:43:02Z", "player_name": "Dan Burn", "is_main_line": True}


class ApiFalsa:
    def __init__(self, paginas):
        self.paginas, self.llamadas = paginas, []

    def get(self, ruta, **q):
        self.llamadas.append((ruta, q))
        i = 0 if "cursor" not in q else int(q["cursor"])
        if i >= len(self.paginas) or self.paginas[i] is None:
            return None
        return {"data": self.paginas[i], "pagination": {"has_more": i + 1 < len(self.paginas), "next_cursor": str(i + 1)}}


def test_capturar_evento_recorre_las_paginas_y_pide_solo_prepartido_de_las_dos_casas():
    api = ApiFalsa([[{"sportsbook": "draftkings", "odds_decimal": 2.0, "deep_link": "x"}], [{"sportsbook": "fanduel", "odds_decimal": 1.5}]])
    filas, paginas = C.capturar_evento(api, {"id": "ev1"})
    assert paginas == 2 and [f["odds_decimal"] for f in filas] == [2.0, 1.5] and "deep_link" not in filas[0]
    ruta, q = api.llamadas[0]
    assert ruta == "/odds" and q["event_id"] == "ev1" and q["sportsbook"] == "draftkings,fanduel" and q["is_live"] == "false"
    assert api.llamadas[1][1]["cursor"] == "1"
    assert C.capturar_evento(ApiFalsa([[{"a": 1}], None]), {"id": "ev2"}) is None   # una página caída: no se guarda nada a medias


def test_escribir_captura_deja_cabecera_y_filas_con_nombre_seguro(tmp_path):
    ev = _evento("liga_a/b:c", 2)
    f = C.escribir_captura(tmp_path, ev, AHORA + timedelta(hours=2), AHORA, [120], [{"market_type": "m", "odds_decimal": 2.0}], 1)
    assert f.parent.name == "liga_a_b_c" and f.parent.parent.name == "2026-11-02" and f.suffix == ".gz" and not list(tmp_path.rglob("*.tmp"))
    lineas = gzip.open(f, "rt", encoding="utf-8").read().splitlines()
    cab = json.loads(lineas[0])
    assert cab["mins_al_saque"] == 120 and cab["momentos"] == [120] and cab["filas"] == 1 and cab["casas"] == ["draftkings", "fanduel"]
    assert json.loads(lineas[1]) == {"market_type": "m", "odds_decimal": 2.0}


def test_estado_olvida_partidos_viejos(tmp_path):
    ruta = tmp_path / "estado.json"
    estado = {"eventos": {"viejo": {"inicio": (AHORA - timedelta(days=5)).isoformat(), "hechos": [15]},
                          "nuevo": {"inicio": (AHORA + timedelta(hours=1)).isoformat(), "hechos": [120]}}}
    C.guardar_estado(ruta, estado, AHORA)
    assert list(C.cargar_estado(ruta)["eventos"]) == ["nuevo"]
    assert C.cargar_estado(tmp_path / "no_existe.json") == {"eventos": {}}


def test_la_clave_se_lee_del_archivo_y_falta_da_error(tmp_path):
    env = tmp_path / ".env"; env.write_text("OTRA=1\nSHARPAPI_KEY=sk_test_123\n", encoding="utf-8")
    assert C.leer_clave(env) == "sk_test_123"
    env.write_text("OTRA=1\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        C.leer_clave(env)
