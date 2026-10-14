# F2 — Cierres de Pinnacle de football-data para partidos ya existentes: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `history_fd` adjunte la cuota de cierre de Pinnacle a partidos que ya existen (creados por el calendario de API-Football), cargando de paso los ~1.457 cierres de México, Argentina, Brasil y MLS que faltan, sin comprar créditos.

**Architecture:** Función nueva `completar_cierres` en `qf.ingest.history_fd`, con el mismo patrón que `completar_tarjetas`: baja el CSV, resuelve nombres sin dar de alta equipos, empareja por liga, equipos y ±36 h, e inserta las 3 cuotas con un único `INSERT ... WHERE NOT EXISTS` para que sea idempotente. `odds_snapshots` es inmutable, así que el ensayo (por defecto) no escribe nada.

**Tech Stack:** Python 3.12, pandas, psycopg3, Postgres 15+, pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md` (fase F2). Decisión del usuario (14-oct-2026): solo lo gratis; Europa sin cierre histórico, se llena con la captura en vivo.

## Global Constraints

- Solo Pinnacle (`PSCH/PSCD/PSCA`): no se insertan bet365 ni promedios de mercado.
- Nunca se duplica: no se inserta si el partido ya tiene un cierre h2h de Pinnacle de cualquier fuente.
- `captured_at` es el `kickoff_utc` del partido de la base, `mins_to_kickoff = 0`, `window_tag = 'close'`, `source = 'football_data'`.
- No se dan de alta equipos ni partidos; un nombre sin resolver o un partido sin pareja se cuenta y se omite.
- Una cuota que no es un número finito mayor que 1, o una terna incompleta, se descarta entera.
- El ensayo es el modo por defecto y no escribe.

## Review Focus

1. Dos ejecuciones seguidas: la segunda inserta 0 filas (Task 2).
2. Partido que ya tiene cierre de Pinnacle de la API en vivo: no se le añade el de football-data (Task 2).
3. Terna con una cuota ≤ 1, NaN o ausente: no se inserta nada del partido (Task 1).
4. Dos partidos de los mismos equipos en ±36 h: se elige el más cercano (Task 2).

---

### Task 1: Extracción de las ternas de Pinnacle del CSV

**Files:**
- Modify: `src/qf/ingest/history_fd.py`
- Test: `tests/test_history_fd.py` (añadir)

**Interfaces:**
- Produces: `ternas_pinnacle(df: pd.DataFrame, cols: dict, desde: datetime) -> list[dict]` con claves `home`, `away` (nombres crudos), `ko` (datetime UTC), `price` (`{"home": float, "draw": float, "away": float}`). `cols` es `COLS_MAIN` o `COLS_EXTRA`.

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
# añadir a tests/test_history_fd.py
def _csv(**extra):
    import pandas as pd
    base = {"Date": ["20/09/2025"], "Home": ["A"], "Away": ["B"], "PSCH": [2.1], "PSCD": [3.3], "PSCA": [3.6]}
    base.update({k: [v] for k, v in extra.items()})
    return pd.DataFrame(base)


def test_ternas_pinnacle_toma_la_terna_completa():
    from datetime import datetime, timezone

    from qf.ingest.history_fd import COLS_EXTRA, ternas_pinnacle
    t = ternas_pinnacle(_csv(), COLS_EXTRA, datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert len(t) == 1 and t[0]["home"] == "A" and t[0]["away"] == "B"
    assert t[0]["price"] == {"home": 2.1, "draw": 3.3, "away": 3.6}
    assert t[0]["ko"].year == 2025


def test_ternas_pinnacle_descarta_cuotas_invalidas_o_incompletas():
    from datetime import datetime, timezone

    from qf.ingest.history_fd import COLS_EXTRA, ternas_pinnacle
    desde = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for malo in (dict(PSCD=1.0), dict(PSCH=float("nan")), dict(PSCA=float("inf")), dict(PSCH=-3.0)):
        assert ternas_pinnacle(_csv(**malo), COLS_EXTRA, desde) == []
    sin_cols = _csv().drop(columns=["PSCA"])
    assert ternas_pinnacle(sin_cols, COLS_EXTRA, desde) == []


def test_ternas_pinnacle_respeta_el_desde():
    from datetime import datetime, timezone

    from qf.ingest.history_fd import COLS_EXTRA, ternas_pinnacle
    assert ternas_pinnacle(_csv(), COLS_EXTRA, datetime(2026, 1, 1, tzinfo=timezone.utc)) == []
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_history_fd.py -q`
Expected: FAIL (`ImportError: cannot import name 'ternas_pinnacle'`)

- [ ] **Step 3: Implementar**

```python
# en src/qf/ingest/history_fd.py, después de _parse_date
PINNACLE_CIERRE = ("PSCH", "PSCD", "PSCA")


def ternas_pinnacle(df: pd.DataFrame, cols: dict, desde: datetime) -> list[dict]:
    """Filas del CSV con la terna de cierre de Pinnacle completa y válida, desde `desde`."""
    import math

    if not set(PINNACLE_CIERRE) <= set(df.columns):
        return []
    out = []
    for _, row in df.iterrows():
        home, away = row.get(cols["home"]), row.get(cols["away"])
        ko = _parse_date(row)
        if ko is None or ko < desde or not isinstance(home, str) or not isinstance(away, str):
            continue
        try:
            precios = [float(row[c]) for c in PINNACLE_CIERRE]
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(p) and p > 1.0 for p in precios):
            continue
        out.append({"home": home, "away": away, "ko": ko,
                    "price": dict(zip(("home", "draw", "away"), precios))})
    return out
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_history_fd.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/qf/ingest/history_fd.py tests/test_history_fd.py
git commit -m "F2: extraer las ternas de cierre de Pinnacle del CSV de football-data" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `cargar_ternas` — emparejar con partidos existentes e insertar sin duplicar

**Files:**
- Modify: `src/qf/ingest/history_fd.py`
- Test: `tests/test_history_fd_cierres_pg.py`

**Interfaces:**
- Consumes: `ternas_pinnacle` (Task 1).
- Produces: `cargar_ternas(c, league_id: str, ternas: list[dict], resolver, aplicar: bool) -> dict` donde `c` es una conexión de `qf.db.conn()` y `resolver(nombre: str, league_id: str) -> str | None` devuelve el nombre canónico del club. Devuelve `{"filas": n, "sin_resolver": n, "sin_partido": n, "ya_tenia_cierre": n, "a_insertar": n, "insertadas": n}`.

- [ ] **Step 1: Escribir las pruebas que fallan (Postgres real, se omiten sin `QF_TEST_PG_DSN`)**

```python
# tests/test_history_fd_cierres_pg.py
"""cargar_ternas contra un Postgres real con db/*.sql aplicados (ver test_escalera_pg)."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.ingest.history_fd import cargar_ternas

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


def _partido(ko=None, local="Local", visita="Visita"):
    s = uuid.uuid4().hex[:8]
    liga = db.query_one("SELECT league_id FROM leagues ORDER BY league_id LIMIT 1")["league_id"]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s,%s) RETURNING team_id",
                        (liga, f"{n}-{s}"))["team_id"] for n in (local, visita)]
    ko = ko or datetime.now(timezone.utc) - timedelta(days=5)
    mid = f"{liga}:cier:{s}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  VALUES (%s,%s,'t',%s,%s,%s,'finished',1,0)""", (mid, liga, ko, *ids))
    return mid, liga, f"{local}-{s}", f"{visita}-{s}", ko


def _terna(local, visita, ko, p=(2.1, 3.3, 3.6)):
    return {"home": local, "away": visita, "ko": ko, "price": dict(zip(("home", "draw", "away"), p))}


def _resolver(nombre, league_id):
    return nombre


def _cierres(mid):
    return db.query("""SELECT selection, price, bookmaker, window_tag, source, mins_to_kickoff, captured_at
                       FROM odds_snapshots WHERE match_id=%s AND market='h2h' AND window_tag='close'
                       ORDER BY selection""", (mid,))


def test_inserta_la_terna_de_pinnacle_en_el_partido_existente():
    mid, liga, local, visita, ko = _partido()
    with db.conn() as c:
        r = cargar_ternas(c, liga, [_terna(local, visita, ko + timedelta(hours=1))], _resolver, aplicar=True)
    f = _cierres(mid)
    assert r["insertadas"] == 3 and r["a_insertar"] == 1 and len(f) == 3
    assert {x["bookmaker"] for x in f} == {"pinnacle"} and {x["source"] for x in f} == {"football_data"}
    assert all(x["mins_to_kickoff"] == 0 and x["captured_at"] == ko for x in f)
    assert [round(x["price"], 2) for x in f] == [3.6, 3.3, 2.1]      # away, draw, home (orden alfabético)


def test_segunda_ejecucion_no_inserta_nada():
    mid, liga, local, visita, ko = _partido()
    t = [_terna(local, visita, ko)]
    with db.conn() as c:
        cargar_ternas(c, liga, t, _resolver, aplicar=True)
    with db.conn() as c:
        r = cargar_ternas(c, liga, t, _resolver, aplicar=True)
    assert r["insertadas"] == 0 and r["ya_tenia_cierre"] == 1 and len(_cierres(mid)) == 3


def test_si_la_api_en_vivo_ya_trajo_el_cierre_no_se_duplica():
    mid, liga, local, visita, ko = _partido()
    for sel, p in (("home", 2.0), ("draw", 3.2), ("away", 3.5)):
        db.execute("""INSERT INTO odds_snapshots (match_id,bookmaker,market,selection,line,price,captured_at,
                                                  mins_to_kickoff,window_tag,source)
                      VALUES (%s,'pinnacle','h2h',%s,NULL,%s,%s,3,'close','the_odds_api')""",
                   (mid, sel, p, ko - timedelta(minutes=3)))
    with db.conn() as c:
        r = cargar_ternas(c, liga, [_terna(local, visita, ko)], _resolver, aplicar=True)
    assert r["insertadas"] == 0 and r["ya_tenia_cierre"] == 1 and len(_cierres(mid)) == 3


def test_el_ensayo_cuenta_y_no_escribe():
    mid, liga, local, visita, ko = _partido()
    with db.conn() as c:
        r = cargar_ternas(c, liga, [_terna(local, visita, ko)], _resolver, aplicar=False)
    assert r["a_insertar"] == 1 and r["insertadas"] == 0 and _cierres(mid) == []


def test_sin_partido_y_sin_resolver_se_cuentan_y_se_omiten():
    mid, liga, local, visita, ko = _partido()
    sin_pareja = _terna(local, visita, ko + timedelta(days=10))
    desconocido = _terna("Nadie", visita, ko)
    with db.conn() as c:
        r = cargar_ternas(c, liga, [sin_pareja, desconocido], lambda n, l: None if n == "Nadie" else n,
                          aplicar=True)
    assert r["sin_partido"] == 1 and r["sin_resolver"] == 1 and r["insertadas"] == 0


def test_con_dos_partidos_cercanos_elige_el_mas_proximo():
    mid1, liga, local, visita, ko = _partido(ko=datetime.now(timezone.utc) - timedelta(days=9))
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  SELECT %s, league_id, season, %s, home_team_id, away_team_id, 'finished', 2, 2
                  FROM matches WHERE match_id = %s""", (mid1 + "-b", ko + timedelta(hours=30), mid1))
    with db.conn() as c:
        cargar_ternas(c, liga, [_terna(local, visita, ko + timedelta(hours=28))], _resolver, aplicar=True)
    assert len(_cierres(mid1)) == 0 and len(_cierres(mid1 + "-b")) == 3
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `QF_TEST_PG_DSN=<dsn de un Postgres local con db/*.sql> PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_history_fd_cierres_pg.py -q`
Expected: FAIL (`ImportError: cannot import name 'cargar_ternas'`)

- [ ] **Step 3: Implementar**

```python
# en src/qf/ingest/history_fd.py, después de ternas_pinnacle
def cargar_ternas(c, league_id: str, ternas: list[dict], resolver, aplicar: bool) -> dict:
    """
    Adjunta el cierre de Pinnacle a partidos que YA existen. No da de alta equipos ni
    partidos. `odds_snapshots` no admite DELETE: la comprobación de que no hay ya un cierre
    de Pinnacle va dentro del propio INSERT, para que dos ejecuciones no se pisen.
    """
    r = {"filas": len(ternas), "sin_resolver": 0, "sin_partido": 0, "ya_tenia_cierre": 0,
         "a_insertar": 0, "insertadas": 0}
    for t in ternas:
        hn, an = resolver(t["home"], league_id), resolver(t["away"], league_id)
        if hn is None or an is None:
            r["sin_resolver"] += 1
            continue
        m = c.execute(
            """SELECT m.match_id, m.kickoff_utc,
                      EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.match_id = m.match_id
                              AND o.bookmaker = 'pinnacle' AND o.market = 'h2h'
                              AND o.window_tag = 'close') AS tiene
               FROM matches m JOIN teams th ON th.team_id = m.home_team_id
                              JOIN teams ta ON ta.team_id = m.away_team_id
               WHERE m.league_id = %s AND th.league_id = %s AND th.canonical_name = %s
                 AND ta.league_id = %s AND ta.canonical_name = %s AND m.status = 'finished'
                 AND m.kickoff_utc BETWEEN %s AND %s
               ORDER BY abs(extract(epoch FROM (m.kickoff_utc - %s::timestamptz))) LIMIT 1""",
            (league_id, league_id, hn, league_id, an, t["ko"] - timedelta(hours=36),
             t["ko"] + timedelta(hours=36), t["ko"])).fetchone()
        if m is None:
            r["sin_partido"] += 1
        elif m["tiene"]:
            r["ya_tenia_cierre"] += 1
        else:
            r["a_insertar"] += 1
            if aplicar:
                p = t["price"]
                r["insertadas"] += c.execute(
                    """INSERT INTO odds_snapshots (match_id, bookmaker, market, selection, line, price,
                                                   captured_at, mins_to_kickoff, window_tag, source)
                       SELECT %s, 'pinnacle', 'h2h', v.sel, NULL, v.price, %s, 0, 'close', 'football_data'
                       FROM (VALUES ('home', %s::real), ('draw', %s::real), ('away', %s::real)) AS v(sel, price)
                       WHERE NOT EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.match_id = %s
                                         AND o.bookmaker = 'pinnacle' AND o.market = 'h2h'
                                         AND o.window_tag = 'close')""",
                    (m["match_id"], m["kickoff_utc"], p["home"], p["draw"], p["away"],
                     m["match_id"])).rowcount
    return r
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `QF_TEST_PG_DSN=<dsn> PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_history_fd_cierres_pg.py tests/test_history_fd.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/qf/ingest/history_fd.py tests/test_history_fd_cierres_pg.py
git commit -m "F2: adjuntar el cierre de Pinnacle a partidos existentes sin duplicar" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `completar_cierres`, CLI, ensayo y carga en producción

**Files:**
- Modify: `src/qf/ingest/history_fd.py`
- Test: `tests/test_history_fd.py` (añadir)
- Modify: `harness/tareas.md`, `harness/progreso.md`, `README.md`
- Create: `docs/f2_cierres_pinnacle_20261014.md`

**Interfaces:**
- Consumes: `ternas_pinnacle`, `cargar_ternas`, `resolve_team` (ya importado en el módulo), `_fetch_csv`, `BASE_MAIN`, `BASE_EXTRA`, `COLS_MAIN`, `COLS_EXTRA`.
- Produces: `completar_cierres(ligas: list[str] | None = None, seasons: list[str] | None = None, desde: str = "2024-01-01", aplicar: bool = False) -> dict` (clave por liga con el dict de `cargar_ternas`); CLI `python -m qf.ingest.history_fd cierres [--aplicar] [liga ...]`.

- [ ] **Step 1: Prueba que falla (sin red ni base: se inyectan descarga y conexión)**

```python
# añadir a tests/test_history_fd.py
def test_completar_cierres_usa_el_csv_correcto_por_formato_y_es_ensayo_por_defecto(monkeypatch):
    import pandas as pd

    from qf.ingest import history_fd as h

    pedidos, llamadas = [], []
    csv_extra = pd.DataFrame({"Date": ["20/09/2025"], "Home": ["A"], "Away": ["B"],
                              "PSCH": [2.1], "PSCD": [3.3], "PSCA": [3.6]})
    monkeypatch.setattr(h, "_fetch_csv", lambda url: pedidos.append(url) or csv_extra)
    monkeypatch.setattr(h, "_ligas_con_csv", lambda ligas: [
        {"league_id": "mx.liga_mx", "fd_code": "MEX", "fd_extra": True},
        {"league_id": "es.laliga", "fd_code": "SP1", "fd_extra": False}])

    class Con:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr("qf.db.conn", lambda: Con())
    monkeypatch.setattr(h, "cargar_ternas",
                        lambda c, liga, ternas, resolver, aplicar: llamadas.append((liga, len(ternas), aplicar)) or {"ok": 1})
    out = h.completar_cierres(seasons=["2526"])
    assert any(u.endswith("/new/MEX.csv") for u in pedidos)
    assert any(u.endswith("/mmz4281/2526/SP1.csv") for u in pedidos)
    assert out["mx.liga_mx"] == {"ok": 1} and all(a is False for _, _, a in llamadas)
```

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_history_fd.py::test_completar_cierres_usa_el_csv_correcto_por_formato_y_es_ensayo_por_defecto -q`
Expected: FAIL (`AttributeError: ... no attribute '_ligas_con_csv'` o `completar_cierres`)

- [ ] **Step 2: Implementar**

```python
# en src/qf/ingest/history_fd.py
def _ligas_con_csv(ligas: list[str] | None) -> list[dict]:
    from ..db import query
    filas = query("SELECT league_id, fd_code, fd_extra FROM leagues WHERE fd_code IS NOT NULL AND active")
    return [f for f in filas if not ligas or f["league_id"] in ligas]


def completar_cierres(ligas: list[str] | None = None, seasons: list[str] | None = None,
                      desde: str = "2024-01-01", aplicar: bool = False) -> dict:
    """
    Cierre de Pinnacle de football-data para partidos YA cargados que no lo tienen. Por defecto
    es un ensayo. Los CSV de las ligas europeas dejaron de traer Pinnacle hacia enero de 2026; los
    «extra» (México, Argentina, Brasil, MLS) lo siguen trayendo.
    """
    from ..db import conn

    desde_dt = datetime.fromisoformat(desde).replace(tzinfo=timezone.utc)
    seasons = seasons or default_seasons()[-3:]
    out = {}
    for lg in _ligas_con_csv(ligas):
        ternas = []
        if lg["fd_extra"]:
            df = _fetch_csv(BASE_EXTRA.format(code=lg["fd_code"]))
            if df is not None and not df.empty:
                ternas += ternas_pinnacle(df, COLS_EXTRA, desde_dt)
        else:
            for s in seasons:
                df = _fetch_csv(BASE_MAIN.format(season=s, code=lg["fd_code"]))
                if df is not None and not df.empty:
                    ternas += ternas_pinnacle(df, COLS_MAIN, desde_dt)
        with conn() as c:
            out[lg["league_id"]] = cargar_ternas(
                c, lg["league_id"], ternas,
                lambda nombre, liga: resolve_team(nombre, "football_data", league_id=liga), aplicar)
    return out
```

Y en el `__main__`:

```python
    elif sys.argv[1:2] == ["cierres"]:
        args = sys.argv[2:]
        print(json.dumps(completar_cierres([a for a in args if a != "--aplicar"],
                                           aplicar="--aplicar" in args), ensure_ascii=False, indent=1))
```

- [ ] **Step 3: Ejecutar y ver que pasa; suite del módulo y de las pruebas `_pg`**

Run: `QF_TEST_PG_DSN=<dsn> PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_history_fd.py tests/test_history_fd_cierres_pg.py -q`
Expected: PASS

- [ ] **Step 4: Ensayo en el VPS (solo lectura)**

Ejecutar `completar_cierres(aplicar=False)` por stdin en el contenedor `api`. Guardar el informe por liga.
Expected: `a_insertar` ≈ 1.457 sumando México, Argentina, Brasil y MLS; Europa con `a_insertar` bajo o 0 (sus CSV ya no traen Pinnacle). Si algo cae fuera de ese orden, investigar antes de aplicar.

- [ ] **Step 5: Aplicar en producción (solo tras el visto bueno del usuario al informe del ensayo)**

Respaldar `odds_snapshots` de esas ligas, ejecutar con `aplicar=True`, repetir una vez (debe insertar 0), comprobar el conteo de cierres antes/después y que el modelo activo y la API siguen igual.

- [ ] **Step 6: Documentar y cerrar**

`docs/f2_cierres_pinnacle_20261014.md` con los números reales; F2 en `harness/tareas.md`; decisión clave en `harness/progreso.md`; una línea en el README. Correr `./scripts/harness_check.sh`.

```bash
git add src/qf/ingest/history_fd.py tests/test_history_fd.py docs/f2_cierres_pinnacle_20261014.md harness/tareas.md harness/progreso.md README.md
git commit -m "F2: completar_cierres, CLI y documentación" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

## Self-review

**Cobertura:** decisión del usuario (solo lo gratis) → Tasks 1-3; defecto del importador (salta cuotas de partidos existentes) → Task 2; cierres de México, Argentina, Brasil y MLS → Task 3 (ensayo y carga). **Fuera de F2 a propósito:** comprar histórico de Europa (rechazado por el usuario), el proxy de cierre promedio, y el bloque `mercado` de movimiento (se construye cuando haya muestra).

**Consistencia de tipos:** `ternas_pinnacle` produce las claves `home/away/ko/price` que `cargar_ternas` lee; `completar_cierres` pasa `resolve_team(nombre, "football_data", league_id=liga)` como `resolver`, y las pruebas inyectan `lambda n, l: n`.

**Riesgo:** `odds_snapshots` es inmutable: un error de emparejamiento es para siempre. Por eso hay ensayo por defecto, `INSERT ... WHERE NOT EXISTS`, respaldo previo y aplicar solo con visto bueno del usuario sobre el informe real.
