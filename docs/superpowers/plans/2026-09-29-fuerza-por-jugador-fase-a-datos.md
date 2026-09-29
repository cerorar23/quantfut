# Fuerza por jugador — Fase A: datos. Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guardar las estadísticas por jugador y partido de API-Football (`/fixtures/players`) para los 4.555 partidos históricos con XI y, en adelante, para cada partido que se cierre en ligas con modelo.

**Architecture:** Tabla `estadisticas_jugador` + registro `estadisticas_jugador_log` (db/035). Módulo `ingest/estadisticas_jugador.py` con un parser puro, una función de captura por partido y un recorrido histórico reanudable con reserva de cuota (mismo patrón que `ingest/lineups_historicas.py`). `ingest/results.py` llama a la captura al cerrar partidos de ligas con modelo. La Fase B (valores por jugador y brazos del challenger) tendrá su propio plan después del reentreno del 1-oct-2026.

**Tech Stack:** Python 3.12, PostgreSQL 16, psycopg (`qf.db.query/execute/executemany`), pytest, cliente `qf.ingest.api_football`.

**Spec:** `docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md`

## Global Constraints

- Todo mensaje al usuario y todo comentario nuevo en español.
- Solo ligas con `leagues.model_enabled = TRUE`.
- Para un partido del día D solo cuentan estadísticas de partidos anteriores a D (se aplica en la Fase B; aquí solo se guardan con su partido).
- Reserva de cuota de API-Football: 2.500 peticiones (`RESERVA_CUOTA` de `ingest/lineups_historicas.py`); la cuota restante llega como TEXTO en la cabecera.
- `nota_proveedor` es solo comparación; se guarda `fetched_at`.
- Nunca se modifica `lineups`, `predictions` ni nada sellado.
- Commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests -q` desde la raíz del repo.

## Formato real de `/fixtures/players` (comprobado 2026-09-29)

`response` = lista de 2 bloques `{"team": {"id": <af_team_id>}, "players": [...]}`. Cada jugador:
`{"player": {"id", "name"}, "statistics": [{"games": {"minutes", "position", "rating": "5.9" | null, "substitute"}, "shots": {"total", "on"}, "goals": {"total", "conceded", "assists", "saves"}, "passes": {"key"}, "tackles": {"total", "interceptions"}, "duels": {"won"}, "dribbles": {"success"}}]}`.
Recuentos a `null` significan 0. Suplentes no utilizados vienen con `minutes: null`.

## Archivos

- Create: `db/035_estadisticas_jugador.sql` — tablas.
- Create: `src/qf/ingest/estadisticas_jugador.py` — parser, captura, histórico.
- Modify: `src/qf/ingest/results.py` — captura al cerrar.
- Create: `tests/test_estadisticas_jugador.py`.
- Modify: `harness/tareas.md`, `harness/progreso.md`.

---

### Task 1: Migración y parser puro

**Files:**
- Create: `db/035_estadisticas_jugador.sql`
- Create: `src/qf/ingest/estadisticas_jugador.py`
- Test: `tests/test_estadisticas_jugador.py`

**Interfaces:**
- Produces: `parse_jugadores(resp: list[dict], home_af: int | None, away_af: int | None) -> list[dict]`, cada dict con claves `side, player_id, nombre, posicion, minutos, titular, goles, asistencias, tiros, tiros_puerta, pases_clave, regates, entradas, intercepciones, duelos_ganados, paradas, nota_proveedor`.

- [ ] **Step 1: Escribir la migración**

```sql
-- ============================================================================
-- 035 - Estadísticas por jugador y partido (fuerza por jugador, Fase A)
--
-- Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
-- Fuente: /fixtures/players de API-Football, 1 petición por partido. Datos de
-- partidos YA jugados: la Fase B solo usará, para un partido del día D, filas
-- de partidos anteriores a D. `nota_proveedor` puede revisarse días después:
-- solo comparación, con `fetched_at`.
-- `estadisticas_jugador_log` registra cada intento, también los vacíos, para
-- no gastar dos veces la petición de un partido sin datos.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS estadisticas_jugador (
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    side            TEXT NOT NULL CHECK (side IN ('home', 'away')),
    player_id       BIGINT NOT NULL,
    nombre          TEXT,
    posicion        TEXT,
    minutos         SMALLINT NOT NULL,
    titular         BOOLEAN NOT NULL,
    goles           SMALLINT NOT NULL,
    asistencias     SMALLINT NOT NULL,
    tiros           SMALLINT NOT NULL,
    tiros_puerta    SMALLINT NOT NULL,
    pases_clave     SMALLINT NOT NULL,
    regates         SMALLINT NOT NULL,
    entradas        SMALLINT NOT NULL,
    intercepciones  SMALLINT NOT NULL,
    duelos_ganados  SMALLINT NOT NULL,
    paradas         SMALLINT NOT NULL,
    nota_proveedor  REAL,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, player_id)
);
CREATE INDEX IF NOT EXISTS idx_estad_jugador_player ON estadisticas_jugador (player_id);

CREATE TABLE IF NOT EXISTS estadisticas_jugador_log (
    match_id     TEXT PRIMARY KEY REFERENCES matches(match_id),
    n_jugadores  INTEGER NOT NULL,
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
    GRANT SELECT ON estadisticas_jugador, estadisticas_jugador_log TO qf_readonly;
  END IF;
END $$;

COMMIT;
```

- [ ] **Step 2: Escribir el test del parser (falla)**

```python
"""
Estadísticas por jugador (db/035, fuerza por jugador Fase A).

Lo que fijan: el lado se asigna por el id de equipo de API-Football, no por
el orden; los suplentes que no jugaron no se guardan; los recuentos nulos son
0 y la nota del proveedor, que llega como texto, se convierte a número.
"""
from __future__ import annotations

from qf.ingest.estadisticas_jugador import parse_jugadores


def _jugador(pid, minutos, pos="M", suplente=False, rating="7.1", **stats):
    s = {"games": {"minutes": minutos, "position": pos, "rating": rating,
                   "substitute": suplente},
         "shots": {"total": stats.get("tiros"), "on": stats.get("puerta")},
         "goals": {"total": stats.get("goles"), "assists": stats.get("asist"),
                   "saves": stats.get("paradas")},
         "passes": {"key": stats.get("clave")},
         "tackles": {"total": stats.get("entradas"), "interceptions": None},
         "duels": {"won": stats.get("duelos")},
         "dribbles": {"success": None}}
    return {"player": {"id": pid, "name": f"J{pid}"}, "statistics": [s]}


def _resp(primero_visitante=False):
    local = {"team": {"id": 538}, "players": [
        _jugador(1, 90, "F", tiros=4, puerta=2, goles=1, clave=1),
        _jugador(2, 25, "M", suplente=True, rating=None),
        _jugador(3, None, "D", suplente=True, rating=None)]}
    visita = {"team": {"id": 542}, "players": [_jugador(9, 90, "G", paradas=3)]}
    return [visita, local] if primero_visitante else [local, visita]


def test_el_lado_sale_del_id_de_equipo_no_del_orden():
    filas = parse_jugadores(_resp(primero_visitante=True), 538, 542)
    assert {f["player_id"]: f["side"] for f in filas} == {1: "home", 2: "home", 9: "away"}


def test_suplente_sin_minutos_no_se_guarda_y_nulos_son_cero():
    filas = {f["player_id"]: f for f in parse_jugadores(_resp(), 538, 542)}
    assert 3 not in filas
    delantero = filas[1]
    assert (delantero["tiros"], delantero["tiros_puerta"], delantero["goles"],
            delantero["pases_clave"], delantero["asistencias"]) == (4, 2, 1, 1, 0)
    assert delantero["titular"] is True and delantero["nota_proveedor"] == 7.1
    assert filas[2]["titular"] is False and filas[2]["nota_proveedor"] is None
    assert filas[9]["paradas"] == 3 and filas[9]["posicion"] == "G"


def test_sin_ids_de_equipo_usa_el_orden_del_proveedor():
    filas = parse_jugadores(_resp(), None, None)
    assert {f["player_id"]: f["side"] for f in filas}[9] == "away"


def test_respuesta_vacia():
    assert parse_jugadores([], 538, 542) == []
```

- [ ] **Step 3: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_estadisticas_jugador.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'qf.ingest.estadisticas_jugador'`

- [ ] **Step 4: Implementar el parser**

Crear `src/qf/ingest/estadisticas_jugador.py`:

```python
"""
Estadísticas por jugador y partido (fuerza por jugador, Fase A).

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Fuente: /fixtures/players de API-Football (1 petición por partido). Solo se
guardan jugadores que jugaron; la Fase B calcula su valor usando, para un
partido del día D, únicamente partidos anteriores a D.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def _n(valor) -> int:
    """Recuento del proveedor: null significa 0."""
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _nota(valor) -> float | None:
    try:
        return float(valor) if valor is not None else None
    except (TypeError, ValueError):
        return None


def parse_jugadores(resp: list[dict], home_af: int | None,
                    away_af: int | None) -> list[dict]:
    """
    Filas para `estadisticas_jugador`. El lado se decide por el id de equipo
    de API-Football; si no se conocen los ids, por el orden del proveedor
    (local primero, el mismo contrato que usa `ingest/lineups.py`).
    """
    filas = []
    for i, bloque in enumerate(resp[:2]):
        tid = (bloque.get("team") or {}).get("id")
        if home_af is not None and tid == home_af:
            side = "home"
        elif away_af is not None and tid == away_af:
            side = "away"
        else:
            side = ("home", "away")[i]
        for j in bloque.get("players") or []:
            s = (j.get("statistics") or [{}])[0]
            juego = s.get("games") or {}
            minutos = _n(juego.get("minutes"))
            if minutos <= 0:
                continue
            goles = s.get("goals") or {}
            tiros = s.get("shots") or {}
            entradas = s.get("tackles") or {}
            filas.append({
                "side": side,
                "player_id": int(j["player"]["id"]),
                "nombre": j["player"].get("name"),
                "posicion": (juego.get("position") or "")[:1] or None,
                "minutos": minutos,
                "titular": not bool(juego.get("substitute")),
                "goles": _n(goles.get("total")),
                "asistencias": _n(goles.get("assists")),
                "tiros": _n(tiros.get("total")),
                "tiros_puerta": _n(tiros.get("on")),
                "pases_clave": _n((s.get("passes") or {}).get("key")),
                "regates": _n((s.get("dribbles") or {}).get("success")),
                "entradas": _n(entradas.get("total")),
                "intercepciones": _n(entradas.get("interceptions")),
                "duelos_ganados": _n((s.get("duels") or {}).get("won")),
                "paradas": _n(goles.get("saves")),
                "nota_proveedor": _nota(juego.get("rating")),
            })
    return filas
```

- [ ] **Step 5: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_estadisticas_jugador.py -q`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add db/035_estadisticas_jugador.sql src/qf/ingest/estadisticas_jugador.py tests/test_estadisticas_jugador.py
git commit -m "Fuerza por jugador (A1): tabla y parser de estadísticas por jugador" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Captura por partido y recorrido histórico reanudable

**Files:**
- Modify: `src/qf/ingest/estadisticas_jugador.py`
- Test: `tests/test_estadisticas_jugador.py`

**Interfaces:**
- Consumes: `parse_jugadores` (Task 1); `qf.ingest.lineups_historicas._cuota(meta) -> int | None` y `RESERVA_CUOTA`.
- Produces: `capturar(match_id: str, af_fixture: int, home_af: int | None, away_af: int | None) -> tuple[int, dict]` (n guardados, meta del proveedor); `run_historico(reserva: int = RESERVA_CUOTA) -> dict`.

- [ ] **Step 1: Escribir los tests (fallan)**

Añadir a `tests/test_estadisticas_jugador.py`:

```python
def test_capturar_guarda_filas_y_registra_el_intento(monkeypatch):
    from qf.ingest import estadisticas_jugador as ej
    llamadas, sqls = [], []
    monkeypatch.setattr(ej.af, "get", lambda ep, p: (llamadas.append((ep, p)) or
                                                      (_resp(), {"quota_remaining": "5000"})))
    monkeypatch.setattr(ej, "executemany", lambda sql, filas: sqls.append(("many", len(filas))))
    monkeypatch.setattr(ej, "execute", lambda sql, params: sqls.append(("log", params)))
    n, meta = ej.capturar("m1", 777, 538, 542)
    assert llamadas == [("fixtures/players", {"fixture": 777})]
    assert n == 3 and ("many", 3) in sqls and ("log", ("m1", 3)) in sqls


def test_sin_datos_se_registra_para_no_repetir(monkeypatch):
    from qf.ingest import estadisticas_jugador as ej
    sqls = []
    monkeypatch.setattr(ej.af, "get", lambda ep, p: ([], {"quota_remaining": "5000"}))
    monkeypatch.setattr(ej, "executemany", lambda sql, filas: sqls.append("many"))
    monkeypatch.setattr(ej, "execute", lambda sql, params: sqls.append(params))
    assert ej.capturar("m1", 777, 538, 542)[0] == 0
    assert sqls == [("m1", 0)]


def test_el_historico_para_en_la_reserva(monkeypatch):
    from qf.ingest import estadisticas_jugador as ej
    pendientes = [{"match_id": f"m{i}", "af_fixture_id": i, "home_af": 538,
                   "away_af": 542} for i in range(5)]
    monkeypatch.setattr(ej, "query", lambda sql, params=(): pendientes)
    hechos = []

    def capturar(match_id, fixture, h, a):
        hechos.append(match_id)
        return 20, {"quota_remaining": "2400" if match_id == "m1" else "3000"}
    monkeypatch.setattr(ej, "capturar", capturar)
    monkeypatch.setattr(ej.af, "record_health", lambda *a, **k: None)
    r = ej.run_historico(reserva=2500)
    assert hechos == ["m0", "m1"] and r["partidos"] == 2 and r["pendientes"] == 5
```

- [ ] **Step 2: Ejecutar y ver que fallan**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_estadisticas_jugador.py -q`
Expected: FAIL con `AttributeError: module 'qf.ingest.estadisticas_jugador' has no attribute 'capturar'`

- [ ] **Step 3: Implementar**

En `src/qf/ingest/estadisticas_jugador.py`, sustituir las importaciones del principio por:

```python
from __future__ import annotations

import logging

from ..db import execute, executemany, query
from . import api_football as af
from .lineups_historicas import RESERVA_CUOTA, _cuota

log = logging.getLogger(__name__)

COLUMNAS = ("side", "player_id", "nombre", "posicion", "minutos", "titular",
            "goles", "asistencias", "tiros", "tiros_puerta", "pases_clave",
            "regates", "entradas", "intercepciones", "duelos_ganados",
            "paradas", "nota_proveedor")
```

y añadir al final del archivo:

```python
def capturar(match_id: str, af_fixture: int, home_af: int | None,
             away_af: int | None) -> tuple[int, dict]:
    """Descarga y guarda un partido. Registra el intento aunque venga vacío."""
    resp, meta = af.get("fixtures/players", {"fixture": af_fixture})
    filas = parse_jugadores(resp, home_af, away_af)
    if filas:
        executemany(
            f"""INSERT INTO estadisticas_jugador (match_id, {", ".join(COLUMNAS)})
                VALUES (%s, {", ".join(["%s"] * len(COLUMNAS))})
                ON CONFLICT (match_id, player_id) DO NOTHING""",
            [(match_id, *(f[c] for c in COLUMNAS)) for f in filas],
        )
    execute(
        """INSERT INTO estadisticas_jugador_log (match_id, n_jugadores)
           VALUES (%s, %s) ON CONFLICT (match_id) DO NOTHING""",
        (match_id, len(filas)),
    )
    return len(filas), meta


def run_historico(reserva: int = RESERVA_CUOTA) -> dict:
    """
    Partidos con XI histórico (db/034) aún sin intento registrado.
    Reanudable: se detiene al llegar a la reserva de cuota y sigue otro día.
    """
    pendientes = query(
        """SELECT DISTINCT h.match_id, h.af_fixture_id,
                  th.af_team_id AS home_af, ta.af_team_id AS away_af
           FROM lineups_historicas h
           JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           LEFT JOIN estadisticas_jugador_log g USING (match_id)
           WHERE g.match_id IS NULL
           ORDER BY h.match_id""")
    partidos = jugadores = 0
    for p in pendientes:
        n, meta = capturar(p["match_id"], p["af_fixture_id"], p["home_af"], p["away_af"])
        partidos += 1
        jugadores += n
        restante = _cuota(meta)
        if restante is not None and restante < reserva:
            log.warning("Reserva de cuota alcanzada (%s): se sigue otro día", restante)
            break
    resultado = {"pendientes": len(pendientes), "partidos": partidos,
                 "jugadores": jugadores}
    af.record_health("estadisticas_jugador", jugadores, True, resultado)
    log.info("Estadísticas por jugador (histórico): %s", resultado)
    return resultado


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run_historico())
```

- [ ] **Step 4: Ejecutar y ver que pasan**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_estadisticas_jugador.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add src/qf/ingest/estadisticas_jugador.py tests/test_estadisticas_jugador.py
git commit -m "Fuerza por jugador (A2): captura por partido e histórico reanudable" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Captura diaria al cerrar partidos

**Files:**
- Modify: `src/qf/ingest/results.py` (función `close_recent`)
- Test: `tests/test_estadisticas_jugador.py`

**Interfaces:**
- Consumes: `capturar` (Task 2).
- Produces: `close_recent(...)` devuelve además la clave `"jugadores"` (partidos con estadísticas capturadas).

- [ ] **Step 1: Escribir el test (falla)**

Añadir a `tests/test_estadisticas_jugador.py`:

```python
def test_al_cerrar_se_capturan_solo_ligas_con_modelo(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from qf.ingest import results
    ko = datetime.now(timezone.utc) - timedelta(hours=3)
    pendientes = [
        {"match_id": "con", "league_id": "es.laliga", "kickoff_utc": ko, "af_id": "10",
         "model_enabled": True, "home_af": 538, "away_af": 542},
        {"match_id": "sin", "league_id": "cl.primera", "kickoff_utc": ko, "af_id": "11",
         "model_enabled": False, "home_af": 1, "away_af": 2}]

    def fx(fid):
        return {"fixture": {"id": fid, "status": {"short": "FT"}},
                "goals": {"home": 1, "away": 0}, "score": {"halftime": {}},
                "teams": {"home": {"id": 538}, "away": {"id": 542}}}

    monkeypatch.setattr(results, "query", lambda sql, params=(): pendientes)
    monkeypatch.setattr(results, "execute", lambda sql, params=(): 1)
    monkeypatch.setattr(results.af, "get", lambda ep, p: ([fx(10), fx(11)], {})
                        if ep == "fixtures" else ([], {}))
    monkeypatch.setattr(results.af, "check_quota", lambda meta: None)
    monkeypatch.setattr(results.af, "record_health", lambda *a, **k: None)
    capturados = []
    monkeypatch.setattr(results, "capturar_jugadores",
                        lambda m, f, h, a: capturados.append((m, f, h, a)) or (11, {}))
    import qf.eval.clv as clv
    monkeypatch.setattr(clv, "settle_pending", lambda: {})
    r = results.close_recent(with_stats=False)
    assert capturados == [("con", 10, 538, 542)]
    assert r["closed"] == 2 and r["jugadores"] == 1
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_estadisticas_jugador.py -q -k cerrar`
Expected: FAIL con `AttributeError: <module 'qf.ingest.results'> does not have the attribute 'capturar_jugadores'`

- [ ] **Step 3: Implementar**

En `src/qf/ingest/results.py`:

1. Añadir la importación junto a las demás:

```python
from .estadisticas_jugador import capturar as capturar_jugadores
```

2. En `close_recent`, sustituir la consulta de pendientes por esta (añade liga con modelo y los ids de equipo de API-Football):

```python
    pending = query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc,
                  m.external_ids ->> 'api_football' AS af_id,
                  l.model_enabled,
                  th.af_team_id AS home_af, ta.af_team_id AS away_af
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.status IN ('scheduled', 'live', 'postponed')
             AND m.kickoff_utc < now() - interval '105 minutes'
             AND m.kickoff_utc > %s
             AND m.external_ids ? 'api_football'
             AND (%s::text[] IS NULL OR m.league_id = ANY(%s))""",
        (since, leagues, leagues),
    )
```

3. Inicializar el contador junto a los demás: sustituir `closed = voided = still_open = 0` por:

```python
    closed = voided = still_open = jugadores = 0
```

4. Justo después de `closed += 1` (dentro del bucle, tras el `UPDATE matches`), añadir:

```python
            # Fuerza por jugador (db/035): una petición más, solo en ligas con
            # modelo. Un fallo aquí no debe dejar el partido sin cerrar.
            if row["model_enabled"]:
                try:
                    capturar_jugadores(row["match_id"], int(af_id),
                                       row["home_af"], row["away_af"])
                    jugadores += 1
                except Exception as exc:  # noqa: BLE001
                    log.warning("Estadísticas por jugador de %s: %s",
                                row["match_id"], exc)
```

5. Añadir `"jugadores": jugadores` al diccionario `result` final:

```python
    result = {"closed": closed, "voided": voided, "still_open": still_open,
              "jugadores": jugadores, "settled": settled}
```

- [ ] **Step 4: Ejecutar toda la suite**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests -q`
Expected: todo en verde (`488 + 8 passed` aprox.; ningún FAIL).

- [ ] **Step 5: Commit**

```bash
git add src/qf/ingest/results.py tests/test_estadisticas_jugador.py
git commit -m "Fuerza por jugador (A3): capturar estadísticas al cerrar partidos con modelo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Despliegue, descarga histórica y verificación

**Files:**
- Modify: `harness/tareas.md`, `harness/progreso.md`

- [ ] **Step 1: Harness local**

Run: `./scripts/harness_check.sh`
Expected: `OK. El repo está en buen estado.`

- [ ] **Step 2: Comprobar que el servidor coincide con git en los archivos a tocar**

```bash
for f in src/qf/ingest/results.py; do l=$(git show HEAD~3:$f | tr -d '\r' | sha256sum | cut -c1-12); r=$(ssh quantfut "tr -d '\r' < ~/quantfut/$f | sha256sum" | cut -c1-12); echo "$f git=$l server=$r"; done
```
Expected: los dos hashes iguales (si no, parar e investigar).

- [ ] **Step 3: Respaldo, copia, migración y reconstrucción**

```bash
ssh quantfut 'set -e; cd ~/quantfut; B=~/respaldo_$(date +%Y%m%d)_jugadores; mkdir -p $B; docker compose exec -T db sh -c "pg_dump -U \"\$POSTGRES_USER\" -Fc \"\$POSTGRES_DB\"" > $B/quantfut.dump; cp src/qf/ingest/results.py $B/'
scp -q db/035_estadisticas_jugador.sql quantfut:quantfut/db/
scp -q src/qf/ingest/estadisticas_jugador.py src/qf/ingest/results.py quantfut:quantfut/src/qf/ingest/
scp -q tests/test_estadisticas_jugador.py quantfut:quantfut/tests/
ssh quantfut 'cd ~/quantfut && docker compose exec -T db sh -c "psql -v ON_ERROR_STOP=1 -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\"" < db/035_estadisticas_jugador.sql && timeout 600 docker compose up -d --build api worker && docker compose exec -T worker grep -c capturar_jugadores /app/src/qf/ingest/results.py'
```
Expected: `COMMIT` de la migración y un número ≥ 1 en el último grep.

- [ ] **Step 4: Consultar cuota y lanzar el histórico en segundo plano**

```bash
ssh quantfut 'cd ~/quantfut && nohup sh -c "timeout 14400 docker compose exec -T worker sh -c \"cd /app && PYTHONPATH=/app/src python -m qf.ingest.estadisticas_jugador\" > /tmp/jugadores.log 2>&1; echo FIN >> /tmp/jugadores.log" > /dev/null 2>&1 < /dev/null & echo lanzado'
```

- [ ] **Step 5: Verificar al terminar**

```bash
ssh quantfut 'grep -v httpx /tmp/jugadores.log | tail -3; cd ~/quantfut && docker compose exec -T db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"SELECT count(*) partidos, count(*) FILTER (WHERE n_jugadores = 0) vacios FROM estadisticas_jugador_log\" -c \"SELECT posicion, count(*), round(avg(minutos)) min_medios, round(avg(tiros)::numeric, 2) tiros FROM estadisticas_jugador GROUP BY 1 ORDER BY 1\""'
```
Expected: ~4.555 partidos registrados (o menos si paró en la reserva: relanzar el Step 4 otro día), pocos vacíos, 4 posiciones G/D/M/F con minutos medios coherentes (titulares ~70-90).

- [ ] **Step 6: Harness y commit**

Marcar en `harness/tareas.md` la Fase A como hecha y apuntar en `harness/progreso.md` (entrada fechada) el resultado de la descarga y cualquier sorpresa del proveedor. Commit:

```bash
git add harness/tareas.md harness/progreso.md
git commit -m "Harness: fuerza por jugador, Fase A desplegada y descargada" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
