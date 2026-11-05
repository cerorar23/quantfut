"""Árbol `data/v3` del scraper de SofaScore (VPS) → `nba.dato`, solo los partidos recientes y sin pisar nada."""
from datetime import UTC, datetime, timedelta
import gzip
import json
from pathlib import Path

from nba.v2 import captura
from nba.v2.fuentes import sofascore, sofascore_arbol

FIX = Path(__file__).parent / "fixtures" / "sofascore_eventos.jsonl"
BASE = [json.loads(x) for x in FIX.read_text(encoding="utf-8").splitlines()]
AHORA = datetime(2026, 11, 5, 8, 0, tzinfo=UTC)
OBSERVADO = "2026-11-05T06:40:00+00:00"


def _gz(ruta: Path, obj):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(ruta, "wt", encoding="utf8") as f:
        json.dump(obj, f)


def _evento_crudo(e, estado="finished", inicio=None):
    """Un partido de `fixtures/sofascore_eventos.jsonl` escrito como lo guarda el scraper (calendario)."""
    def marcador(m):
        return dict({"current": m["total"]}, **{f"period{i}": p for i, p in enumerate(m["periodos"], 1)})
    return {"id": e["id"], "status": {"type": estado}, "startTimestamp": int(inicio.timestamp()),
            "homeTeam": {"id": e["local"]["id"], "nameCode": e["local"]["codigo"], "name": e["local"]["nombre"]},
            "awayTeam": {"id": e["visitante"]["id"], "nameCode": e["visitante"]["codigo"], "name": e["visitante"]["nombre"]},
            "homeScore": marcador(e["marcador"]["local"]), "awayScore": marcador(e["marcador"]["visitante"])}


def arbol(raiz: Path, partidos):
    """`partidos`: [(evento base, estado, inicio UTC, con_alineaciones)]. Devuelve la raíz `v3` creada."""
    v3 = raiz / "v3"
    crudos = []
    for e, estado, inicio, con_alineaciones in partidos:
        crudos.append(_evento_crudo(e, estado, inicio))
        if not con_alineaciones:
            continue
        i = str(e["id"])
        carpeta = v3 / "events" / i[:2] / i[2:5] / i
        lados = {"home": [], "away": []}
        for j in e["jugadores"]:
            lados["home" if j["equipo"] == "local" else "away"].append(
                {"player": {"id": j["id"], "name": j["nombre"]}, "substitute": not j["titular"], "statistics": j["stats"]})
        _gz(carpeta / "lineups.json.gz", {"home": {"players": lados["home"]}, "away": {"players": lados["away"]}})
        (carpeta / "manifest.json").write_text(json.dumps({"observation": {"observed_at_utc": OBSERVADO}}), encoding="utf-8")
    _gz(v3 / "tournaments" / "132" / "seasons" / "100772" / "schedule" / "last_0.json.gz", {"events": crudos})
    return v3


def _lineas(ruta: Path):
    with gzip.open(ruta, "rt", encoding="utf8") as f:
        return [json.loads(x) for x in f]


def test_convierte_solo_terminados_con_alineaciones_y_desde_la_fecha(tmp_path):
    ayer = AHORA - timedelta(hours=30)
    extra = dict(BASE[0], id=99)
    v3 = arbol(tmp_path, [(BASE[0], "finished", ayer, True), (BASE[1], "finished", AHORA - timedelta(days=9), True),
                          (dict(extra, id=98), "inprogress", ayer, False), (dict(extra, id=97), "finished", ayer, False)])
    salida = tmp_path / "salida.jsonl.gz"
    cuenta = sofascore_arbol.convertir(v3, salida, AHORA - timedelta(days=4))
    lineas = _lineas(salida)
    assert [x["id"] for x in lineas] == [BASE[0]["id"]]
    assert cuenta["partidos"] == 1 and cuenta["viejos"] == 1 and cuenta["no_terminado"] == 1 and cuenta["sin_alineaciones"] == 1
    e = lineas[0]
    assert e["temporada"] == "2026-27" and e["observado_utc"] == OBSERVADO
    assert e["local"]["codigo"] == BASE[0]["local"]["codigo"] and e["marcador"]["local"]["total"] == BASE[0]["marcador"]["local"]["total"]
    assert len(e["jugadores"]) == len(BASE[0]["jugadores"])
    assert all(isinstance(j["stats"].get("secondsPlayed", 0), int) for j in e["jugadores"])


def test_carga_los_recientes_con_la_hora_real_y_es_idempotente(base_migrada, tmp_path):
    db = base_migrada
    v3 = arbol(tmp_path, [(BASE[0], "finished", AHORA - timedelta(hours=30), True)])
    r = sofascore_arbol.cargar_recientes(db, v3, tmp_path / "sf", AHORA, dias=4)
    assert r["eventos"] == 1 and r["filas_nuevas"] > 100
    asist = db.execute("SELECT d.valor, d.recibido_en, d.fuente, d.fase FROM nba.dato d JOIN nba.metrica m USING (metrica_id) "
                       "WHERE m.nombre = 'asistencias' AND d.valor IS NOT NULL ORDER BY d.valor DESC LIMIT 1").fetchone()
    assert asist[0] == max(j["stats"].get("assists", 0) for j in BASE[0]["jugadores"])
    assert asist[1] == datetime.fromisoformat(OBSERVADO) and asist[2] == "sofascore" and asist[3] == "final"
    r2 = sofascore_arbol.cargar_recientes(db, v3, tmp_path / "sf", AHORA + timedelta(minutes=30), dias=4)
    assert r2["filas_nuevas"] == 0
    assert db.execute("SELECT count(*) FROM nba.dato WHERE fuente <> 'sofascore'").fetchone()[0] == 0   # no toca otras fuentes


def test_sin_partidos_recientes_no_carga_nada(base_migrada, tmp_path):
    v3 = arbol(tmp_path, [(BASE[1], "finished", AHORA - timedelta(days=9), True)])
    r = sofascore_arbol.cargar_recientes(base_migrada, v3, tmp_path / "sf", AHORA, dias=4)
    assert r["ok"] and r["eventos"] == 0 and r["filas_nuevas"] == 0


def test_la_fuente_sofascore_del_colector_carga_el_arbol(base_migrada_dsn, tmp_path):
    v3 = arbol(tmp_path, [(BASE[0], "finished", AHORA - timedelta(hours=30), True)])
    env = {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path / "datos"), "NBA_SOFASCORE_DIR": str(v3)}
    r = captura.ejecutar("sofascore", env, AHORA)
    assert r["ok"] and r["eventos"] == 1 and r["filas_nuevas"] > 100
    assert captura.principal(["sofascore"], {"NBA_DB_DSN": base_migrada_dsn, "NBA_CAPTURA_DIR": str(tmp_path / "d2")}) == 2   # sin la carpeta
