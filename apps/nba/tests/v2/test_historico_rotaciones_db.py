import gzip
import json
from datetime import UTC, date
from pathlib import Path

from nba.v2.fuentes import historico_partidos, historico_rotaciones



def _escribir(ruta, filas):
    with gzip.open(ruta, "wt", encoding="utf8") as f:
        for fila in filas:
            f.write(json.dumps(fila) + "\n")


def test_carga_por_fragmentos_y_es_idempotente(base_migrada, tmp_path):
    db = base_migrada
    juegos = {"0022100001": {"game_id": "0022100001", "date": "2021-10-19", "home": {"team_id": 1610612749, "minutes": 240},
                             "away": {"team_id": 1610612751, "minutes": 240}}}
    (tmp_path / "games.json").write_text(json.dumps(juegos))
    _escribir(tmp_path / "players.jsonl.gz", [
        {"game_id": "0022100001", "player_id": 100 + i, "name": f"J{i}", "team_id": 1610612749 if i < 5 else 1610612751,
         "participated": False} for i in range(10)])
    historico_partidos.cargar_cajas(db, tmp_path)
    tramos = [{"period": 1, "team_id": 1610612749, "start_elapsed_seconds": 0, "end_elapsed_seconds": 720,
               "nba_player_ids": [100 + i for i in range(5)]},
              {"period": 1, "team_id": 1610612751, "start_elapsed_seconds": 0, "end_elapsed_seconds": 720,
               "nba_player_ids": [105 + i for i in range(5)]}]
    _escribir(tmp_path / "rotaciones.jsonl.gz", [{"game_id": "0022100001", "chronological_lineups": tramos}])
    r0 = historico_rotaciones.cargar_rotaciones(db, tmp_path, (0, 2))
    r1 = historico_rotaciones.cargar_rotaciones(db, tmp_path, (1, 2))
    assert (r0["filas"], r0["juegos"], r1["juegos"]) == (1, 1, 0)
    assert historico_rotaciones.cargar_rotaciones(db, tmp_path, (0, 2))["ya_cargados"] == 1
    fila = db.execute("SELECT periodo, reloj_s, tipo, en_pista_local, en_pista_visit FROM nba.evento").fetchall()
    assert len(fila) == 1 and fila[0][:3] == (1, 720.0, "quinteto") and len(fila[0][3]) == 5 and len(fila[0][4]) == 5
