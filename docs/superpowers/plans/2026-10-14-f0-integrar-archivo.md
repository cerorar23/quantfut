# F0 — Integrar el archivo FotMob a las tablas principales: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pasar a `matches` (y a una tabla nueva `estadios`) los datos que ya están archivados en `historical_football_*`: tarjetas, descanso, tiros, córners, xGOT, árbitro y sede con coordenadas. Sin inventar valores y sin pisar ninguno existente.

**Architecture:** Un módulo `qf.ingest.archivo_a_matches` con una función pura `extraer()` (original FotMob + estadísticas → campos validados) y una función `aplicar()` que rellena **solo NULL** dentro de una transacción, con ensayo revertible. La procedencia de cada campo rellenado queda en `matches_enriquecimiento`. Mismo patrón que `fotmob_import.apply_import`.

**Tech Stack:** Python 3.12, psycopg3, Postgres 15+, pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md` (fase F0).

## Global Constraints

- Solo se rellenan columnas que están en NULL; nunca se sobrescribe un valor existente (`COALESCE(actual, nuevo)`).
- Un dato ausente o inválido queda NULL. Nunca se convierte en cero.
- Un par local/visita se rellena completo o no se rellena (no hay mitades).
- Solo partidos con `mapping_status IN ('matched','created')`, `status='finished'` y el mismo marcador final en el archivo y en `matches`.
- `matches.referee` NO se toca: el motor de tarjetas lo usa con el formato de API-Football. El árbitro de FotMob va a `referee_fotmob`; F5 resuelve las identidades.
- xGOT de FotMob (`expected_goals_on_target`) va a `home_xgot/away_xgot`. NO se copia a `home_psxg`: no son intercambiables (auditoría 2026-10-14).
- Triggers de inmutabilidad, `features_pit` y la cadena de hashes no se tocan.
- La migración es aditiva y reversible (`IF NOT EXISTS`, una transacción).
- Aplicar en producción exige confirmación del usuario (Task 5).

## Review Focus

1. Estadística ausente en el original → queda NULL, no 0 (Task 2).
2. Valores negativos, NaN, infinitos, booleanos o decimales en un conteo → NULL (Task 2).
3. Descanso mayor que el marcador final → NULL (Task 2).
4. Segunda ejecución: 0 filas cambiadas, y un valor ya existente no cambia (Task 3).
5. Local y visita invertidos: se exige el mismo marcador archivo/partido (Task 3).
6. El motor de tarjetas recibe más historial de amarillas: se mide el antes/después (Task 4).

---

### Task 1: Migración 067 (estadios, procedencia y columnas nuevas)

**Files:**
- Create: `db/067_f0_archivo_a_matches.sql`
- Test: `tests/test_f0_esquema.py`

**Interfaces:**
- Produces: tabla `estadios(stadium_id, name, city, country, lat, lon, capacity, surface, source, first_seen_at)`; columnas `matches.stadium_id`, `matches.home_xgot`, `matches.away_xgot`, `matches.referee_fotmob`; tabla `matches_enriquecimiento(match_id, campo, provider, source_match_id, captured_at, imported_at)` con PK `(match_id, campo)`.

- [ ] **Step 1: Escribir la prueba que falla**

```python
# tests/test_f0_esquema.py
"""Esquema de db/067: aditivo, en una transacción y sin tocar triggers existentes."""
from pathlib import Path

SQL = (Path(__file__).resolve().parents[1] / "db" / "067_f0_archivo_a_matches.sql").read_text(encoding="utf-8")


def test_una_transaccion_y_aditiva():
    assert SQL.lstrip().startswith("--") or SQL.lstrip().startswith("BEGIN")
    assert SQL.count("BEGIN;") == 1 and SQL.count("COMMIT;") == 1
    for peligro in ("DROP TABLE", "DROP TRIGGER", "DISABLE TRIGGER", "DELETE FROM", "UPDATE "):
        assert peligro not in SQL


def test_tabla_estadios_con_coordenadas_validadas():
    assert "CREATE TABLE IF NOT EXISTS estadios" in SQL
    assert "lat BETWEEN -90 AND 90" in SQL.replace("  ", " ")
    assert "lon BETWEEN -180 AND 180" in SQL.replace("  ", " ")
    assert "NULLS NOT DISTINCT" in SQL


def test_columnas_nuevas_en_matches():
    for col in ("stadium_id", "home_xgot", "away_xgot", "referee_fotmob"):
        assert f"ADD COLUMN IF NOT EXISTS {col}" in SQL


def test_procedencia_se_borra_junto_con_el_partido():
    # Las retiradas de ligas (063) borran partidos: la procedencia no puede bloquearlas.
    assert "CREATE TABLE IF NOT EXISTS matches_enriquecimiento" in SQL
    assert "ON DELETE CASCADE" in SQL
    assert "PRIMARY KEY (match_id, campo)" in SQL


def test_no_mezcla_xgot_con_psxg():
    # Los comentarios pueden nombrar home_psxg para advertir; ninguna sentencia lo toca.
    assert "ADD COLUMN IF NOT EXISTS home_psxg" not in SQL
    assert "SET home_psxg" not in SQL
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `python -m pytest tests/test_f0_esquema.py -v`
Expected: FAIL (`FileNotFoundError` de `067_f0_archivo_a_matches.sql`)

- [ ] **Step 3: Escribir la migración**

```sql
-- ============================================================================
-- 067 - F0: lo archivado de FotMob pasa a tablas consultables.
--       Spec docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md
--
-- estadios: sede real con coordenadas (el motor no las usa todavía; F6).
-- matches_enriquecimiento: de dónde y cuándo llegó cada campo rellenado.
-- xGOT no es PSxG: columnas propias, nunca se copia a home_psxg.
-- referee_fotmob: matches.referee conserva el formato de API-Football que lee
-- el motor de tarjetas; F5 unifica identidades.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS estadios (
    stadium_id    BIGSERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    city          TEXT,
    country       TEXT,
    lat           DOUBLE PRECISION,
    lon           DOUBLE PRECISION,
    capacity      INTEGER,
    surface       TEXT,
    source        TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL,
    CHECK (lat BETWEEN -90 AND 90),
    CHECK (lon BETWEEN -180 AND 180),
    CHECK ((lat IS NULL) = (lon IS NULL)),
    CHECK (capacity IS NULL OR capacity > 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS estadios_uq ON estadios (name, city, country) NULLS NOT DISTINCT;

ALTER TABLE matches ADD COLUMN IF NOT EXISTS stadium_id BIGINT REFERENCES estadios(stadium_id);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_xgot REAL;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_xgot REAL;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS referee_fotmob TEXT;
CREATE INDEX IF NOT EXISTS idx_matches_stadium ON matches(stadium_id) WHERE stadium_id IS NOT NULL;

COMMENT ON COLUMN matches.home_xgot IS
    'xG de los remates a puerta (xGOT) del proveedor. NO equivale a home_psxg: otra definición y escala.';
COMMENT ON COLUMN matches.referee_fotmob IS
    'Árbitro tal como lo nombra FotMob. matches.referee conserva el formato de API-Football.';

CREATE TABLE IF NOT EXISTS matches_enriquecimiento (
    match_id        TEXT NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    campo           TEXT NOT NULL,
    provider        TEXT NOT NULL,
    source_match_id TEXT NOT NULL,
    captured_at     TIMESTAMPTZ NOT NULL,
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, campo)
);
COMMENT ON TABLE matches_enriquecimiento IS
    'Procedencia de cada campo de matches rellenado desde el archivo. captured_at = recepción real del original.';

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON estadios, matches_enriquecimiento TO qf_readonly;
  END IF;
END $$;

COMMIT;
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `python -m pytest tests/test_f0_esquema.py -v`
Expected: PASS (5 pruebas)

- [ ] **Step 5: Commit**

```bash
git add db/067_f0_archivo_a_matches.sql tests/test_f0_esquema.py
git commit -m "F0: migración 067 (estadios, procedencia, xGOT y árbitro FotMob)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Extractor puro `extraer()`

**Files:**
- Create: `src/qf/ingest/archivo_a_matches.py`
- Test: `tests/test_archivo_a_matches.py`

**Interfaces:**
- Produces: `CAMPOS_PARES: dict[str, tuple[str, str, str, bool]]` y `extraer(payload: dict, statistics: dict, goles_local: int, goles_visita: int) -> dict`. El dict devuelto tiene SIEMPRE estas claves (valor `None` si no hay dato válido): `home_yellow, away_yellow, home_red, away_red, home_shots, away_shots, home_shots_target, away_shots_target, home_corners, away_corners, home_xgot, away_xgot, home_goals_ht, away_goals_ht, referee_fotmob, estadio`. `estadio` es `None` o un dict `{name, city, country, lat, lon, capacity, surface}`.

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
# tests/test_archivo_a_matches.py
"""El extractor no fabrica datos: ausente o inválido es None, nunca 0."""
import math

from qf.ingest.archivo_a_matches import extraer

STATS = {"yellow_cards": [2.0, 1.0], "red_cards": [0.0, 1.0], "corners": [7.0, 5.0],
         "total_shots": [22.0, 21.0], "ShotsOnTarget": [5.0, 6.0],
         "expected_goals_on_target": [1.05, 2.68]}


def payload(**extra):
    base = {"content": {"matchFacts": {
        "infoBox": {"Referee": {"text": " José Luis Munuera Montero "},
                    "Stadium": {"name": "Estadio de Mestalla", "city": "Valencia", "country": "Spain",
                                "lat": 39.4746, "long": -0.3582, "capacity": 49430, "surface": "grass"}},
        "events": {"events": [{"type": "Half", "halfStrShort": "HT", "homeScore": 1, "awayScore": 2}]}}}}
    base.update(extra)
    return base


def test_caso_completo():
    r = extraer(payload(), STATS, 2, 3)
    assert (r["home_yellow"], r["away_yellow"]) == (2, 1)
    assert (r["home_red"], r["away_red"]) == (0, 1)
    assert (r["home_corners"], r["away_corners"]) == (7, 5)
    assert (r["home_shots"], r["away_shots"], r["home_shots_target"], r["away_shots_target"]) == (22, 21, 5, 6)
    assert (r["home_xgot"], r["away_xgot"]) == (1.05, 2.68)
    assert (r["home_goals_ht"], r["away_goals_ht"]) == (1, 2)
    assert r["referee_fotmob"] == "José Luis Munuera Montero"
    assert r["estadio"] == {"name": "Estadio de Mestalla", "city": "Valencia", "country": "Spain",
                            "lat": 39.4746, "lon": -0.3582, "capacity": 49430, "surface": "grass"}


def test_ausente_es_none_no_cero():
    r = extraer({}, {}, 0, 0)
    assert all(v is None for v in r.values())


def test_valores_invalidos_son_none():
    malos = {"yellow_cards": [-1.0, 1.0], "red_cards": [float("nan"), 0.0],
             "corners": [math.inf, 3.0], "total_shots": [True, 3.0],
             "ShotsOnTarget": [2.5, 1.0], "expected_goals_on_target": [1.0]}
    r = extraer(payload(), malos, 2, 3)
    for campo in ("home_yellow", "away_yellow", "home_red", "away_red", "home_corners", "away_corners",
                  "home_shots", "away_shots", "home_shots_target", "away_shots_target",
                  "home_xgot", "away_xgot"):
        assert r[campo] is None, campo


def test_descanso_mayor_que_el_final_es_none():
    p = payload()
    p["content"]["matchFacts"]["events"]["events"][0].update(homeScore=3, awayScore=0)
    r = extraer(p, STATS, 2, 3)
    assert r["home_goals_ht"] is None and r["away_goals_ht"] is None


def test_estadio_con_coordenadas_fuera_de_rango_no_se_guarda_con_ellas():
    p = payload()
    p["content"]["matchFacts"]["infoBox"]["Stadium"]["lat"] = 123.0
    r = extraer(p, STATS, 2, 3)
    assert r["estadio"]["name"] == "Estadio de Mestalla"
    assert r["estadio"]["lat"] is None and r["estadio"]["lon"] is None


def test_arbitro_vacio_es_none():
    p = payload()
    p["content"]["matchFacts"]["infoBox"]["Referee"] = {"text": "   "}
    assert extraer(p, STATS, 2, 3)["referee_fotmob"] is None
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `python -m pytest tests/test_archivo_a_matches.py -v`
Expected: FAIL (`ModuleNotFoundError: qf.ingest.archivo_a_matches`)

- [ ] **Step 3: Implementar el extractor**

```python
# src/qf/ingest/archivo_a_matches.py
"""Pasa a `matches` lo ya archivado de FotMob (F0 de la spec 2026-10-14).

Solo rellena columnas en NULL, nunca inventa un valor ausente y nunca sobrescribe.
La procedencia de cada campo queda en `matches_enriquecimiento`.
"""
from __future__ import annotations

import math

# columna_local, columna_visita, clave en `statistics`, ¿entero?
CAMPOS_PARES = {
    "amarillas": ("home_yellow", "away_yellow", "yellow_cards", True),
    "rojas": ("home_red", "away_red", "red_cards", True),
    "corners": ("home_corners", "away_corners", "corners", True),
    "tiros": ("home_shots", "away_shots", "total_shots", True),
    "tiros_puerta": ("home_shots_target", "away_shots_target", "ShotsOnTarget", True),
    "xgot": ("home_xgot", "away_xgot", "expected_goals_on_target", False),
}


def _numero(valor) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if not math.isfinite(valor) or valor < 0:
        return None
    return float(valor)


def _par(statistics: dict, clave: str, entero: bool):
    """(local, visita) válidos los dos, o (None, None): nunca una mitad."""
    valor = (statistics or {}).get(clave)
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        return None, None
    a, b = _numero(valor[0]), _numero(valor[1])
    if a is None or b is None:
        return None, None
    if entero:
        if a != int(a) or b != int(b):
            return None, None
        return int(a), int(b)
    return a, b


def _descanso(payload: dict, goles_local: int, goles_visita: int):
    hechos = ((payload.get("content") or {}).get("matchFacts") or {})
    eventos = hechos.get("events")
    eventos = eventos.get("events") if isinstance(eventos, dict) else None
    for e in eventos or []:
        if e.get("type") == "Half" and e.get("halfStrShort") == "HT":
            h, a = e.get("homeScore"), e.get("awayScore")
            validos = all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (h, a))
            if validos and h <= goles_local and a <= goles_visita:
                return h, a
    return None, None


def _info(payload: dict) -> dict:
    return (((payload.get("content") or {}).get("matchFacts") or {}).get("infoBox")) or {}


def _texto(valor) -> str | None:
    if isinstance(valor, str) and valor.strip() and len(valor.strip()) <= 160:
        return valor.strip()
    return None


def _estadio(payload: dict) -> dict | None:
    bruto = _info(payload).get("Stadium")
    nombre = _texto((bruto or {}).get("name")) if isinstance(bruto, dict) else None
    if not nombre:
        return None
    lat, lon = bruto.get("lat"), bruto.get("long")
    en_rango = (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                and not isinstance(lat, bool) and not isinstance(lon, bool)
                and -90 <= lat <= 90 and -180 <= lon <= 180)
    capacidad = bruto.get("capacity")
    return {"name": nombre, "city": _texto(bruto.get("city")), "country": _texto(bruto.get("country")),
            "lat": float(lat) if en_rango else None, "lon": float(lon) if en_rango else None,
            "capacity": int(capacidad) if isinstance(capacidad, int) and not isinstance(capacidad, bool)
            and capacidad > 0 else None,
            "surface": _texto(bruto.get("surface"))}


def extraer(payload: dict, statistics: dict, goles_local: int, goles_visita: int) -> dict:
    """Campos validados de un original FotMob. Dato ausente o inválido: None."""
    out: dict = {}
    for local, visita, clave, entero in CAMPOS_PARES.values():
        out[local], out[visita] = _par(statistics, clave, entero)
    out["home_goals_ht"], out["away_goals_ht"] = _descanso(payload, goles_local, goles_visita)
    arbitro = _info(payload).get("Referee")
    out["referee_fotmob"] = _texto(arbitro.get("text")) if isinstance(arbitro, dict) else None
    out["estadio"] = _estadio(payload)
    return out
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `python -m pytest tests/test_archivo_a_matches.py -v`
Expected: PASS (6 pruebas)

- [ ] **Step 5: Commit**

```bash
git add src/qf/ingest/archivo_a_matches.py tests/test_archivo_a_matches.py
git commit -m "F0: extractor de tarjetas, descanso, xGOT, árbitro y sede del archivo FotMob" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `aplicar()` — rellenar solo NULL con procedencia

**Files:**
- Modify: `src/qf/ingest/archivo_a_matches.py` (añadir al final)
- Test: `tests/test_archivo_a_matches_pg.py`

**Interfaces:**
- Consumes: `extraer()` y `CAMPOS_PARES` (Task 2); tablas de la migración 067.
- Produces: `huecos(c, desde: str) -> dict[str, int]` y `aplicar(c, desde: str = "2024-01-01", rollback: bool = False) -> dict` con claves `visitados`, `rellenados` (campo → n), `estadios_nuevos`, `omitidos` (motivo → n), `antes`, `despues`. `c` es una conexión de `qf.db.conn()`.

- [ ] **Step 1: Escribir la prueba que falla (Postgres real, se omite sin `QF_TEST_PG_DSN`)**

```python
# tests/test_archivo_a_matches_pg.py
"""aplicar() contra un Postgres real con db/*.sql aplicados (ver test_escalera_pg)."""
import gzip
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.ingest.archivo_a_matches import aplicar

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")

STATS = {"yellow_cards": [2.0, 1.0], "red_cards": [0.0, 1.0], "corners": [7.0, 5.0],
         "total_shots": [22.0, 21.0], "ShotsOnTarget": [5.0, 6.0], "expected_goals_on_target": [1.05, 2.68]}
PAYLOAD = {"content": {"matchFacts": {
    "infoBox": {"Referee": {"text": "Árbitro Prueba"},
                "Stadium": {"name": "Estadio Prueba", "city": "Ciudad", "country": "País",
                            "lat": 10.0, "long": 20.0, "capacity": 1000, "surface": "grass"}},
    "events": {"events": [{"type": "Half", "halfStrShort": "HT", "homeScore": 1, "awayScore": 1}]}}}}


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


def _partido(hg=2, ag=3, **columnas):
    s = uuid.uuid4().hex[:8]
    liga = db.query_one("SELECT league_id FROM leagues ORDER BY league_id LIMIT 1")["league_id"]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s,%s) RETURNING team_id",
                        (liga, f"{n}-{s}"))["team_id"] for n in ("Local", "Visita")]
    ko = datetime.now(timezone.utc) - timedelta(days=3)
    mid = f"{liga}:f0:{s}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  VALUES (%s,%s,'t',%s,%s,%s,'finished',%s,%s)""", (mid, liga, ko, *ids, hg, ag))
    for col, val in columnas.items():
        db.execute(f"UPDATE matches SET {col} = %s WHERE match_id = %s", (val, mid))
    db.execute("""INSERT INTO historical_football_matches
        (provider, source_match_id, league_id, season, kickoff_utc, captured_at, raw_sha256, raw_payload_gzip,
         raw_metadata, home_source_team_id, away_source_team_id, home_name, away_name, home_goals, away_goals,
         statistics, match_id, mapping_status)
        VALUES ('fotmob', %s, %s, 't', %s, now(), %s, %s, '{}', '1', '2', 'L', 'V', %s, %s, %s, %s, 'matched')""",
               (s, liga, ko, "0" * 64, gzip.compress(json.dumps(PAYLOAD).encode()), hg, ag,
                json.dumps(STATS), mid))
    return mid


def _fila(mid):
    return db.query_one("SELECT * FROM matches WHERE match_id = %s", (mid,))


def test_rellena_los_null_y_registra_procedencia():
    mid = _partido()
    with db.conn() as c:
        informe = aplicar(c, desde="2000-01-01")
    f = _fila(mid)
    assert (f["home_yellow"], f["away_yellow"]) == (2, 1)
    assert (f["home_goals_ht"], f["away_goals_ht"]) == (1, 1)
    assert f["referee_fotmob"] == "Árbitro Prueba" and f["referee"] is None
    assert f["stadium_id"] is not None and (f["home_xgot"], f["away_xgot"]) == (1.05, 2.68)
    assert f["home_psxg"] is None
    prov = db.query("SELECT campo FROM matches_enriquecimiento WHERE match_id = %s", (mid,))
    assert {"home_yellow", "home_goals_ht", "referee_fotmob", "stadium_id"} <= {p["campo"] for p in prov}
    assert informe["rellenados"]["home_yellow"] >= 1


def test_no_sobrescribe_un_valor_existente():
    mid = _partido(home_yellow=9, away_yellow=9)
    with db.conn() as c:
        aplicar(c, desde="2000-01-01")
    f = _fila(mid)
    assert (f["home_yellow"], f["away_yellow"]) == (9, 9)


def test_segunda_ejecucion_no_cambia_nada():
    _partido()
    with db.conn() as c:
        aplicar(c, desde="2000-01-01")
    with db.conn() as c:
        segunda = aplicar(c, desde="2000-01-01")
    assert sum(segunda["rellenados"].values()) == 0 and segunda["estadios_nuevos"] == 0


def test_marcador_distinto_no_se_toca():
    mid = _partido(hg=2, ag=3)
    db.execute("UPDATE historical_football_matches SET home_goals = 3, away_goals = 2 "
               "WHERE match_id = %s", (mid,))
    with db.conn() as c:
        informe = aplicar(c, desde="2000-01-01")
    assert _fila(mid)["home_yellow"] is None
    assert informe["omitidos"].get("marcador_distinto", 0) >= 1


def test_ensayo_revierte():
    mid = _partido()
    with db.conn() as c:
        aplicar(c, desde="2000-01-01", rollback=True)
    assert _fila(mid)["home_yellow"] is None
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `QF_TEST_PG_DSN=<dsn de un Postgres local con db/*.sql> python -m pytest tests/test_archivo_a_matches_pg.py -v`
Expected: FAIL (`ImportError: cannot import name 'aplicar'`). Sin `QF_TEST_PG_DSN` las pruebas se omiten: en ese caso la validación real es el ensayo de la Task 5.

- [ ] **Step 3: Implementar `huecos()` y `aplicar()`**

```python
# src/qf/ingest/archivo_a_matches.py  (añadir imports arriba: gzip, json, collections.Counter)
import gzip
import json
from collections import Counter

PROVIDER = "fotmob"
COLUMNAS_MATCHES = [c for par in CAMPOS_PARES.values() for c in par[:2]] + [
    "home_goals_ht", "away_goals_ht", "referee_fotmob"]
LOTE = 200


def huecos(c, desde: str) -> dict:
    """Partidos terminados desde `desde` con el dato incompleto."""
    return dict(c.execute("""
        SELECT count(*) FILTER (WHERE home_yellow IS NULL OR away_yellow IS NULL) AS amarillas,
               count(*) FILTER (WHERE home_red IS NULL OR away_red IS NULL) AS rojas,
               count(*) FILTER (WHERE referee IS NULL AND referee_fotmob IS NULL) AS arbitro,
               count(*) FILTER (WHERE home_goals_ht IS NULL OR away_goals_ht IS NULL) AS descanso,
               count(*) FILTER (WHERE home_shots IS NULL OR away_shots IS NULL) AS tiros,
               count(*) FILTER (WHERE home_shots_target IS NULL OR away_shots_target IS NULL) AS tiros_puerta,
               count(*) FILTER (WHERE home_corners IS NULL OR away_corners IS NULL) AS corners,
               count(*) FILTER (WHERE home_xgot IS NULL OR away_xgot IS NULL) AS xgot,
               count(*) FILTER (WHERE stadium_id IS NULL) AS sede
        FROM matches WHERE status = 'finished' AND kickoff_utc >= %s""", (desde,)).fetchone())


def _estadio_id(c, estadio: dict, captured_at) -> tuple[int, bool]:
    fila = c.execute("""INSERT INTO estadios (name, city, country, lat, lon, capacity, surface, source, first_seen_at)
                        VALUES (%(name)s, %(city)s, %(country)s, %(lat)s, %(lon)s, %(capacity)s, %(surface)s,
                                %(source)s, %(visto)s)
                        ON CONFLICT (name, city, country) DO NOTHING RETURNING stadium_id""",
                     {**estadio, "source": PROVIDER, "visto": captured_at}).fetchone()
    if fila:
        return fila["stadium_id"], True
    return c.execute("""SELECT stadium_id FROM estadios WHERE name = %s
                        AND city IS NOT DISTINCT FROM %s AND country IS NOT DISTINCT FROM %s""",
                     (estadio["name"], estadio["city"], estadio["country"])).fetchone()["stadium_id"], False


def aplicar(c, desde: str = "2024-01-01", rollback: bool = False) -> dict:
    """Rellena solo NULL desde el archivo. `rollback=True` es el ensayo: mide y revierte."""
    from psycopg import Rollback

    informe = {"visitados": 0, "rellenados": Counter(), "estadios_nuevos": 0, "omitidos": Counter()}
    with c.transaction():
        informe["antes"] = huecos(c, desde)
        pendientes = c.execute(f"""
            SELECT h.source_match_id FROM historical_football_matches h JOIN matches m USING (match_id)
            WHERE h.provider = %s AND h.mapping_status IN ('matched','created') AND m.status = 'finished'
              AND m.kickoff_utc >= %s
              AND (m.stadium_id IS NULL OR {" OR ".join(f"m.{k} IS NULL" for k in COLUMNAS_MATCHES)})
            ORDER BY m.kickoff_utc""", (PROVIDER, desde)).fetchall()
        ids = [r["source_match_id"] for r in pendientes]
        for i in range(0, len(ids), LOTE):
            filas = c.execute(f"""
                SELECT h.source_match_id, h.captured_at, h.raw_payload_gzip, h.statistics,
                       h.home_goals AS h_hg, h.away_goals AS h_ag, m.match_id, m.home_goals, m.away_goals,
                       m.stadium_id, {", ".join("m." + k for k in COLUMNAS_MATCHES)}
                FROM historical_football_matches h JOIN matches m USING (match_id)
                WHERE h.provider = %s AND h.source_match_id = ANY(%s)""", (PROVIDER, ids[i:i + LOTE])).fetchall()
            for f in filas:
                informe["visitados"] += 1
                if (f["h_hg"], f["h_ag"]) != (f["home_goals"], f["away_goals"]):
                    informe["omitidos"]["marcador_distinto"] += 1
                    continue
                try:
                    payload = json.loads(gzip.decompress(bytes(f["raw_payload_gzip"])))
                except (OSError, ValueError):
                    informe["omitidos"]["original_ilegible"] += 1
                    continue
                datos = extraer(payload, f["statistics"], f["home_goals"], f["away_goals"])
                nuevos = {k: datos[k] for k in COLUMNAS_MATCHES if f[k] is None and datos[k] is not None}
                if f["stadium_id"] is None and datos["estadio"]:
                    sid, creado = _estadio_id(c, datos["estadio"], f["captured_at"])
                    nuevos["stadium_id"] = sid
                    informe["estadios_nuevos"] += creado
                if not nuevos:
                    continue
                sets = ", ".join(f"{k} = COALESCE({k}, %({k})s)" for k in nuevos)
                c.execute(f"UPDATE matches SET {sets} WHERE match_id = %(match_id)s",
                          {**nuevos, "match_id": f["match_id"]})
                for campo in nuevos:
                    informe["rellenados"][campo] += 1
                    c.execute("""INSERT INTO matches_enriquecimiento
                                 (match_id, campo, provider, source_match_id, captured_at)
                                 VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                              (f["match_id"], campo, PROVIDER, f["source_match_id"], f["captured_at"]))
        informe["despues"] = huecos(c, desde)
        if rollback:
            raise Rollback()
    informe["rellenados"] = dict(informe["rellenados"])
    informe["omitidos"] = dict(informe["omitidos"])
    return informe
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `QF_TEST_PG_DSN=<dsn> python -m pytest tests/test_archivo_a_matches_pg.py tests/test_archivo_a_matches.py -v`
Expected: PASS. Si no hay Postgres local, `python -m pytest tests/test_archivo_a_matches.py -v` pasa y las `_pg` se omiten.

- [ ] **Step 5: Commit**

```bash
git add src/qf/ingest/archivo_a_matches.py tests/test_archivo_a_matches_pg.py
git commit -m "F0: aplicar() rellena solo NULL con procedencia y ensayo revertible" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: CLI y medición del efecto sobre el motor de tarjetas

**Files:**
- Modify: `src/qf/ingest/archivo_a_matches.py` (añadir `main()`)
- Test: `tests/test_archivo_a_matches.py` (añadir)

**Interfaces:**
- Consumes: `aplicar()` (Task 3).
- Produces: `python -m qf.ingest.archivo_a_matches [--desde YYYY-MM-DD] [--aplicar]`; sin `--aplicar` es ensayo revertido. Imprime el informe JSON.

- [ ] **Step 1: Escribir la prueba que falla**

```python
# añadir a tests/test_archivo_a_matches.py
import pytest
from qf.ingest import archivo_a_matches as mod


def test_el_cli_por_defecto_es_ensayo(monkeypatch, capsys):
    llamadas = []

    class FalsaConexion:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr("qf.db.conn", lambda: FalsaConexion())
    monkeypatch.setattr(mod, "aplicar", lambda c, desde, rollback: llamadas.append(rollback) or {"ok": 1})
    mod.main(["--desde", "2024-01-01"])
    mod.main(["--desde", "2024-01-01", "--aplicar"])
    assert llamadas == [True, False]
    assert '"ok": 1' in capsys.readouterr().out
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `python -m pytest tests/test_archivo_a_matches.py::test_el_cli_por_defecto_es_ensayo -v`
Expected: FAIL (`AttributeError: module ... has no attribute 'main'`)

- [ ] **Step 3: Implementar**

```python
# al final de src/qf/ingest/archivo_a_matches.py
def main(argv=None):
    import argparse

    from ..db import conn
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--desde", default="2024-01-01")
    p.add_argument("--aplicar", action="store_true", help="sin esto es un ensayo que se revierte")
    args = p.parse_args(argv)
    with conn() as c:
        informe = aplicar(c, desde=args.desde, rollback=not args.aplicar)
    print(json.dumps(informe, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `python -m pytest tests/test_archivo_a_matches.py -v`
Expected: PASS (7 pruebas)

- [ ] **Step 5: Commit**

```bash
git add src/qf/ingest/archivo_a_matches.py tests/test_archivo_a_matches.py
git commit -m "F0: CLI con ensayo revertido por defecto" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Ensayo en producción y despliegue (PUNTO DE CONFIRMACIÓN CON EL USUARIO)

**Files:**
- Modify: `harness/tareas.md`, `harness/progreso.md`, `README.md`
- Create: `docs/f0_archivo_a_matches_20261014.md`

**Interfaces:**
- Consumes: CLI de la Task 4 y migración de la Task 1.

Esta tarea toca producción (esquema y datos). **No se ejecuta sin que el usuario lo autorice en el chat.** Se pide la confirmación con el informe del ensayo delante.

- [ ] **Step 1: Arnés y suite completa en local**

Run: `./scripts/harness_check.sh`
Expected: `OK. El repo está en buen estado.` (≥1.084 pruebas aprobadas + las nuevas)

- [ ] **Step 2: Ensayo en el VPS que aplica la migración y lo revierte todo**

Copiar migración y módulo a una carpeta temporal del servidor y ejecutar, dentro de una sola transacción, `\i 067_...sql` seguido de `aplicar(rollback=True)`. Al final se hace `ROLLBACK`: el esquema real no cambia. Guardar el informe.
Expected: `antes.amarillas` ≈ 8.412 y `despues.amarillas` ≈ 294 (desde 2024-01-01); `omitidos` explicado; cero cambios persistentes (`\d matches` sigue sin `stadium_id`).

- [ ] **Step 3: Medir el efecto sobre el motor de tarjetas**

Con el mismo ensayo, comparar antes/después la tasa media de amarillas por liga y el número de partidos de historial por equipo que lee `publish/escalera_datos.py` (líneas ~110-125). Reportar cuánto cambia. Más historial es esperable y deseable; un salto grande en la tasa de una liga se investiga antes de aplicar.

- [ ] **Step 4: Pedir confirmación al usuario**

Mostrar el informe del ensayo (huecos antes/después, omitidos, efecto en tarjetas) y preguntar si se aplica la migración 067 y `--aplicar` en producción.

- [ ] **Step 5: Aplicar (solo con el sí del usuario)**

Aplicar `db/067_f0_archivo_a_matches.sql`, copiar el módulo al contenedor `api` y ejecutar `python -m qf.ingest.archivo_a_matches --desde 2024-01-01 --aplicar`. Repetir una vez: debe rellenar 0 filas. Verificar API y web con 200 y que el modelo activo sigue `2026.09.27-010508`.

- [ ] **Step 6: Documentar y cerrar**

Escribir `docs/f0_archivo_a_matches_20261014.md` con los números reales; marcar F0 en `harness/tareas.md`; añadir a `harness/progreso.md` la decisión clave (rellenar solo NULL, xGOT separado de PSxG, árbitro en columna aparte) y, en el README, una línea con el estado.

```bash
git add docs/f0_archivo_a_matches_20261014.md harness/tareas.md harness/progreso.md README.md
git commit -m "F0: archivo FotMob integrado a matches y estadios (ensayo y aplicación)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Informe de huecos de xG tras F0 (solo lectura)

**Files:**
- Modify: `src/qf/ingest/archivo_a_matches.py` (añadir `huecos_xg()`)
- Test: `tests/test_archivo_a_matches.py` (añadir)

**Interfaces:**
- Produces: `huecos_xg(c, desde: str) -> list[dict]` con `league_id`, `terminados`, `sin_xg`, ordenado por `sin_xg` descendente. No escribe nada y no busca fuentes: decidir una fuente nueva (créditos de ZenRows, PitchAPI) es del usuario.

- [ ] **Step 1: Escribir la prueba que falla**

```python
# añadir a tests/test_archivo_a_matches.py
def test_huecos_xg_consulta_solo_lectura():
    from qf.ingest.archivo_a_matches import huecos_xg

    class Cursor:
        def __init__(self): self.sql = None
        def execute(self, sql, params=()):
            self.sql = sql
            return self
        def fetchall(self):
            return [{"league_id": "it.serie_b", "terminados": 639, "sin_xg": 188}]

    c = Cursor()
    filas = huecos_xg(c, "2025-01-01")
    assert filas[0]["sin_xg"] == 188
    assert "UPDATE" not in c.sql.upper() and "INSERT" not in c.sql.upper()
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `python -m pytest tests/test_archivo_a_matches.py::test_huecos_xg_consulta_solo_lectura -v`
Expected: FAIL (`ImportError: cannot import name 'huecos_xg'`)

- [ ] **Step 3: Implementar**

```python
def huecos_xg(c, desde: str) -> list[dict]:
    """Partidos terminados sin la pareja de xG, por competición. Solo lectura."""
    return c.execute("""
        SELECT league_id, count(*) AS terminados,
               count(*) FILTER (WHERE home_xg IS NULL OR away_xg IS NULL) AS sin_xg
        FROM matches WHERE status = 'finished' AND kickoff_utc >= %s
        GROUP BY league_id HAVING count(*) FILTER (WHERE home_xg IS NULL OR away_xg IS NULL) > 0
        ORDER BY sin_xg DESC""", (desde,)).fetchall()
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `python -m pytest tests/test_archivo_a_matches.py -v`
Expected: PASS (8 pruebas)

- [ ] **Step 5: Commit**

```bash
git add src/qf/ingest/archivo_a_matches.py tests/test_archivo_a_matches.py
git commit -m "F0: informe de huecos de xG por competición (solo lectura)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Self-review

**Cobertura de la spec (F0):** amarillas, árbitro, tiros y PSxG → Tasks 2-3 (PSxG queda como xGOT por separado, decisión explícita); tabla `estadios` con coordenadas → Tasks 1-3; huecos de xG → Task 6 (informe; la fuente nueva la decide el usuario, no se inventa dato); trazabilidad → `matches_enriquecimiento`.

**Fuera de F0 a propósito:** que el motor use estas columnas (F1-F6), la unificación de identidades de árbitro (F5) y el estadio de un partido futuro (F6, el archivo solo cubre partidos jugados).

**Consistencia de tipos:** `extraer()` devuelve las 16 claves que `aplicar()` lee (`COLUMNAS_MATCHES` + `estadio`); `CAMPOS_PARES` es la única fuente de nombres de columnas de pares; `huecos()` y `aplicar()` comparten `desde` como cadena ISO.

**Riesgo conocido:** el SQL de `aplicar()` solo se prueba contra Postgres real (`_pg`, omitido sin DSN y sin Docker local). Por eso la Task 5 exige un ensayo revertido en el VPS antes de aplicar.
