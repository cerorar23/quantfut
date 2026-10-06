# Goles de Pinnacle desde API-Football — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la línea de alta probabilidad tenga pronósticos de goles también cuando el precio reciente de Pinnacle viene de API-Football (hoy, casi siempre a las 08:00 UTC), guardando las líneas de goles que esa misma petición ya trae.

**Architecture:** `ingest/af_odds.py` deja de filtrar `bet=1`: con la misma petición por partido guarda además "Goals Over/Under" (bet 5) — todas las líneas de Pinnacle y, de las casas de `SOFT_BOOKS`, las líneas 1,5 / 2,5 / 3,5 / 4,5 — en `af_odds_snapshots` con una columna nueva `line` (`db/041`). `publish/alta_prob_datos.py` lee esos totales cuando el snapshot elegido es de API-Football (misma marca `update` que el 1X2) y los pasa al ajuste de goles ya validado, sin cambiar el método ni la regla.

**Tech Stack:** Python 3.12, PostgreSQL 16 (índice único `NULLS NOT DISTINCT`), API-Football `/odds`.

**Contexto medido (2026-10-06, `harness/progreso.md`):** prueba de solo lectura con 22 partidos de las próximas 72 h: 22/22 con 1X2 + O/U de Pinnacle en API-Football; pronóstico de goles en 15/22 (hoy 0); línea directa de Pinnacle frente al ajuste Dixon-Coles con su 2,5: media −0,03 pts, máx. 1,55 pts. Coste en peticiones: cero (una por partido, igual que hoy).

## Global Constraints

- Cero peticiones extra a API-Football: sigue siendo una petición `/odds` por partido; solo se quita el filtro `bet`.
- Se guarda bet 5 ("Goals Over/Under") solo con pares completos over/under y cuotas > 1: de `settings.sharp_book` (Pinnacle) todas las líneas; de las casas de `settings.soft_books` solo `LINEAS_BLANDAS = (1.5, 2.5, 3.5, 4.5)`; del resto de casas, nada.
- `market = 'totals'`, `selection` en `'over'`/`'under'`, `line` numérica; el 1X2 sigue con `market = 'h2h'` y `line` NULL.
- Los lectores existentes de `af_odds_snapshots` (`picks._af_snapshot`, `eval/quote_coverage`) filtran `market = 'h2h'`: no cambian.
- El método de goles de la línea de alta probabilidad NO cambia (ajuste `market_lambdas` con la línea de Pinnacle elegida por `linea_pinnacle`, medio gol primero). Solo cambia de dónde salen los totales cuando el snapshot es de API-Football: de la MISMA respuesta (`provider_updated_at` igual que el del 1X2). Nunca se mezclan fuentes.
- Tablas inmutables: no se tocan los triggers; `ADD COLUMN` e índices nuevos no chocan con ellos.
- Tests: `PYTHONPATH=src "/c/Users/huye/Documents/apuesta proyec/.venv/Scripts/python.exe" -m pytest -p no:cacheprovider -q <tests>` desde la raíz del worktree; suite completa en verde antes de cada commit. Comentarios en español; commits en español con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Task 1: Migración `db/041` y captura de goles en `af_odds`

**Files:**
- Create: `db/041_af_odds_totales.sql`
- Modify: `src/qf/ingest/af_odds.py` (docstring, constantes, `parse`, `run_once`)
- Modify: `tests/test_af_odds.py`

**Interfaces:**
- Produces: filas de `parse()` con 9 campos `(match_id, af_fixture_id, bookmaker, market, selection, price, provider_updated_at, mins_to_kickoff, line)`; columna `af_odds_snapshots.line REAL`; índice único `af_odds_snapshots_uq_linea (match_id, bookmaker, market, selection, line, provider_updated_at) NULLS NOT DISTINCT`.

- [ ] **Step 1: Tests que fallan** — en `tests/test_af_odds.py`:

Cambiar el desempaquetado de `test_la_hora_es_la_del_proveedor_y_los_minutos_salen_de_ella` a 9 campos y afirmar que el 1X2 no lleva línea:

```python
def test_la_hora_es_la_del_proveedor_y_los_minutos_salen_de_ella():
    rows = parse(_resp([_bk("Bet365")]), "m1", KO)
    assert len(rows) == 3
    _, fid, book, market, _, _, updated, mins, line = rows[0]
    assert (fid, book, market, line) == (1550966, "bet365", "h2h", None)
    assert updated == datetime(2026, 9, 23, 20, tzinfo=timezone.utc)
    assert mins == 53 * 60
```

Y añadir al final:

```python
def _ou(name, lineas):
    """bet 5 con {línea: (over, under)}."""
    vals = []
    for ln, (o, u) in lineas.items():
        vals += [{"value": f"Over {ln}", "odd": o}, {"value": f"Under {ln}", "odd": u}]
    return {"name": name, "bets": [{"id": 5, "name": "Goals Over/Under", "values": vals}]}


def test_goles_de_pinnacle_todas_las_lineas_y_de_blandas_solo_las_de_la_linea():
    rows = parse(_resp([
        _ou("Pinnacle", {1.5: ("1.24", "4.11"), 2.75: ("1.96", "1.89"), 5.5: ("15.0", "1.01")}),
        _ou("Bet365", {1.5: ("1.22", "4.00"), 2.25: ("1.60", "2.30"), 4.5: ("5.00", "1.15")}),
        _ou("Marathonbet", {1.5: ("1.25", "4.20")}),
    ]), "m1", KO)
    tot = {(r[2], r[4], r[8]) for r in rows if r[3] == "totals"}
    assert tot == {("pinnacle", s, ln) for ln in (1.5, 2.75, 5.5) for s in ("over", "under")} | \
                  {("bet365", s, ln) for ln in (1.5, 4.5) for s in ("over", "under")}


def test_goles_solo_pares_completos_y_cuotas_validas():
    bk = {"name": "Pinnacle", "bets": [{"id": 5, "values": [
        {"value": "Over 2.5", "odd": "1.90"},                       # sin under
        {"value": "Over 3.5", "odd": "2.90"}, {"value": "Under 3.5", "odd": "1.00"},
        {"value": "Over 1.5", "odd": "1.25"}, {"value": "Under 1.5", "odd": "4.10"},
        {"value": "Más de 0.5", "odd": "1.05"},                     # formato raro
    ]}]}
    tot = [(r[4], r[8]) for r in parse(_resp([bk]), "m1", KO) if r[3] == "totals"]
    assert sorted(tot) == [("over", 1.5), ("under", 1.5)]
```

Run: `PYTHONPATH=src "/c/Users/huye/Documents/apuesta proyec/.venv/Scripts/python.exe" -m pytest -p no:cacheprovider -q tests/test_af_odds.py` → FAIL (filas de 8 campos, sin totales).

- [ ] **Step 2: Migración** — crear `db/041_af_odds_totales.sql`:

```sql
-- ============================================================================
-- 041 - Líneas de goles en af_odds_snapshots (2026-10-06)
--
-- La misma petición /odds de API-Football trae, además del 1X2, "Goals
-- Over/Under" de Pinnacle y de las casas blandas. La línea de alta
-- probabilidad los necesita: a las 08:00 UTC el precio reciente de Pinnacle
-- casi siempre es de API-Football (ver harness/progreso.md, 2026-10-06).
--
-- `line` NULL en el 1X2. El UNIQUE de 016 no lleva la línea: dos líneas del
-- mismo lado chocarían. Se sustituye por un índice único con la línea y
-- NULLS NOT DISTINCT (PostgreSQL 15+) para que el 1X2, con línea NULL, siga
-- sin duplicarse. ADD COLUMN e índices no chocan con el trigger de
-- inmutabilidad (bloquea UPDATE/DELETE de filas, no DDL).
-- ============================================================================
BEGIN;

ALTER TABLE af_odds_snapshots ADD COLUMN IF NOT EXISTS line REAL;
COMMENT ON COLUMN af_odds_snapshots.line IS
  'Línea de goles en market = totals (1.5, 2.75...). NULL en h2h.';

CREATE UNIQUE INDEX IF NOT EXISTS af_odds_snapshots_uq_linea
    ON af_odds_snapshots (match_id, bookmaker, market, selection, line, provider_updated_at)
    NULLS NOT DISTINCT;

ALTER TABLE af_odds_snapshots
    DROP CONSTRAINT IF EXISTS af_odds_snapshots_match_id_bookmaker_market_selection_provi_key;

COMMIT;
```

- [ ] **Step 3: Código** — en `src/qf/ingest/af_odds.py`:

En el docstring del módulo, primera línea: "Captura de cuotas 1X2 y de goles de API-Football: ..." y un párrafo nuevo antes de "Se guarda en `af_odds_snapshots`":

```
GOLES (2026-10-06): la misma petición trae "Goals Over/Under" (bet 5). Se
guardan todas las líneas de Pinnacle (el ajuste de goles de la línea de alta
probabilidad elige la que haya) y, de las casas de SOFT_BOOKS, solo
LINEAS_BLANDAS (cuota de referencia de los pronósticos de goles). Sin coste
extra: sigue siendo una petición por partido.
```

Imports: añadir `from ..config import settings`.

Constantes (tras `SELECTIONS`):

```python
GOALS_OU = 5
# De las casas blandas solo se guardan las líneas de la línea de alta
# probabilidad y la 2,5; de Pinnacle, todas.
LINEAS_BLANDAS = (1.5, 2.5, 3.5, 4.5)
```

Sustituir `parse` por:

```python
def _precio(v: dict) -> float | None:
    try:
        p = float(v.get("odd"))
    except (TypeError, ValueError):
        return None
    return p if p > 1.0 else None


def _totales(bet: dict) -> dict[float, dict[str, float]]:
    """{línea: {'over': cuota, 'under': cuota}}, solo pares completos y válidos."""
    out: dict[float, dict[str, float]] = {}
    for v in bet.get("values", []):
        partes = str(v.get("value", "")).split()
        if len(partes) != 2 or partes[0] not in ("Over", "Under"):
            continue
        try:
            linea = float(partes[1])
        except ValueError:
            continue
        p = _precio(v)
        if p is not None:
            out.setdefault(linea, {})[partes[0].lower()] = p
    return {ln: q for ln, q in out.items() if set(q) == {"over", "under"}}


def parse(response: list[dict], match_id: str, kickoff: datetime) -> list[tuple]:
    """
    Filas para `af_odds_snapshots`. 1X2: solo casas con el grupo completo y
    cuotas válidas (un grupo incompleto no se puede de-vigar ni comparar).
    Goles: pares over/under completos, todas las líneas de Pinnacle y
    LINEAS_BLANDAS de las casas de SOFT_BOOKS.
    """
    rows = []
    for item in response:
        updated = datetime.fromisoformat(item["update"])
        mins = int((kickoff - updated).total_seconds() // 60)
        fid = int(item["fixture"]["id"])
        for bk in item.get("bookmakers", []):
            if not bk.get("name"):
                continue
            book = bookmaker_key(bk["name"])
            for bet in bk.get("bets", []):
                if bet.get("id") == MATCH_WINNER:
                    q = {}
                    for v in bet.get("values", []):
                        sel, p = SELECTIONS.get(v.get("value")), _precio(v)
                        if sel and p is not None:
                            q[sel] = p
                    if set(q) == set(SELECTIONS.values()):
                        rows += [(match_id, fid, book, "h2h", s, p, updated, mins, None)
                                 for s, p in q.items()]
                elif bet.get("id") == GOALS_OU:
                    if book == settings.sharp_book:
                        lineas = None                    # todas
                    elif book in settings.soft_books:
                        lineas = LINEAS_BLANDAS
                    else:
                        continue
                    for ln, q in _totales(bet).items():
                        if lineas is None or ln in lineas:
                            rows += [(match_id, fid, book, "totals", s, p, updated, mins, ln)
                                     for s, p in q.items()]
    return rows
```

En `run_once`: la petición pasa a `af.get("odds", {"fixture": m["fixture_id"]})` (sin `bet`, misma petición), y el INSERT a:

```python
        rows_new += executemany(
            """INSERT INTO af_odds_snapshots
                 (match_id, af_fixture_id, bookmaker, market, selection, price,
                  provider_updated_at, mins_to_kickoff, line)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id, bookmaker, market, selection, line,
                            provider_updated_at) DO NOTHING""",
            rows,
        )
```

- [ ] **Step 4:** Run `tests/test_af_odds.py tests/test_ligas_solo_sharp.py` → PASS; suite completa → PASS.
- [ ] **Step 5: Commit** — `git add db/041_af_odds_totales.sql src/qf/ingest/af_odds.py tests/test_af_odds.py && git commit -m "API-Football: guarda las líneas de goles de la misma petición (db/041)"` (con el trailer).

---

### Task 2: La línea de alta probabilidad lee los totales de API-Football

**Files:**
- Modify: `src/qf/publish/alta_prob_datos.py` (`_totales_af` nueva, `select_and_persist`, docstrings que digan que los totales solo vienen de The Odds API)
- Modify: `tests/test_alta_prob_datos.py`

**Interfaces:**
- Consumes: filas `af_odds_snapshots` con `market = 'totals'` y `line` (Task 1).
- Produces: `_totales_af(match_id: str, as_of: datetime) -> list[dict]` con claves `bookmaker, selection, line, price` (mismo formato que `_totales`).

- [ ] **Step 1: Tests que fallan** — en `tests/test_alta_prob_datos.py`:
  1. En el helper `_db`, añadir `monkeypatch.setattr(ad, "_totales_af", lambda match_id, as_of: [])` (los tests existentes siguen sin base).
  2. Test nuevo: un partido cuyo único snapshot vigente es de API-Football (`ad.pk._odds_api_snapshot` → `None`, `ad.pk._af_snapshot` → `pk.Snapshot("api_football", NOW - 1h, {"pinnacle": 1X2 sin margen coherente, "bet365": {...}})`), con `_totales_af` devolviendo la línea 2,5 de Pinnacle coherente con el 1X2 (fabricada con `score_matrix`, `market_1x2` y `totals_fair_over`, cuotas sin margen `1/p`) más líneas de bet365 en 1,5 / 3,5 / 4,5, y `MERCADOS_GOLES_HABILITADOS` con las tres líneas: `select_and_persist(NOW, dry_run=True)` elige un mercado `totals` con `odds_source == "api_football"` y `ref_book == "bet365"` en la misma línea y lado; y `_totales` (The Odds API) no se llama (monkeypatch que lance `AssertionError`). Elegir lambdas de forma que gane un mercado de goles (p. ej. las del test de goles existente de la Tarea E: 1,25/1,0 → under 3,5).
  3. Test: `_totales_af` consulta `af_odds_snapshots` con `market = 'totals'` y `provider_updated_at = %s` (query simulada que capture SQL y parámetros).

- [ ] **Step 2: Código** — en `alta_prob_datos.py`, junto a `_totales`:

```python
def _totales_af(match_id: str, as_of: datetime) -> list[dict]:
    """Totales de la MISMA respuesta de API-Football que el 1X2 (misma marca `update`)."""
    return query(
        """SELECT bookmaker, selection, line, price FROM af_odds_snapshots
           WHERE match_id = %s AND market = 'totals' AND provider_updated_at = %s""",
        (match_id, as_of))
```

y en `select_and_persist`, sustituir la línea de `totales` por:

```python
        totales = (_totales(m["match_id"], snap.as_of) if snap.source == "the_odds_api"
                   else _totales_af(m["match_id"], snap.as_of))
```

Actualizar los comentarios/docstrings que afirmen que los goles solo existen con The Odds API.

- [ ] **Step 3:** Run `tests/test_alta_prob_datos.py tests/test_alta_prob_sellado.py` → PASS; suite completa → PASS.
- [ ] **Step 4: Commit** — `git commit -m "Alta probabilidad: goles también desde API-Football (misma respuesta que el 1X2)"` (con el trailer).

---

### Task 3: Despliegue (controlador, antes del 2026-10-07 07:45 UTC)

- [ ] Integrar en `main` (rama aparte, fast-forward) con la suite completa en verde; actualizar en `README.md` la "Limitación conocida" de la línea de alta probabilidad.
- [ ] Respaldo de `~/quantfut`; `git archive HEAD src frontend db scripts README.md docs/superpowers | ssh quantfut 'cd ~/quantfut && tar -xf -'`; `docker compose build api worker`.
- [ ] En un minuto sin crons y lejos de `:20` (cron de `af_odds`), de `:25` y de 07:45-08:35 UTC: aplicar `db/041` (`psql -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/041_af_odds_totales.sql`) y, acto seguido, `docker compose up -d api worker`. La migración quita el UNIQUE viejo: el código viejo no debe correr un `af_odds` entre ambos pasos.
- [ ] Verificar: `\d af_odds_snapshots` (columna `line`, índice `af_odds_snapshots_uq_linea`, sin el UNIQUE viejo); que la segunda aplicación de `db/041` es idempotente; tras la siguiente pasada de `af_odds` (minuto :20), filas `market = 'totals'` de `pinnacle` y de casas blandas, y que el 1X2 sigue entrando; `picks._af_snapshot` de un partido sigue dando el 1X2 completo; `hashchain verify`; salud.
- [ ] Vista previa: `docker compose exec -T -e ALTA_PROB_ENABLED=1 worker python -m qf.publish.alta_prob_datos preview` → ahora con decisiones `totals` de `api_football`; enseñar el resumen al usuario.
- [ ] Anotar en `harness/progreso.md` y marcar en `harness/tareas.md` (sin commitear el arnés: tiene notas de otra sesión).
