# "Marca el local / el visitante" en la línea de alta probabilidad — plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir a la línea de alta probabilidad el mercado "más de 0,5 goles de un equipo" (marca el local / marca el visitante), con su probabilidad derivada del mismo ajuste de goles ya validado y cuota de referencia de las casas de los suscriptores.

**Architecture:** Reglas puras en `publish/alta_prob.py` (`candidatos_equipo`, texto, prioridad); captura de la cuota de referencia en `ingest/af_odds.py` (bets 16/17 de API-Football, misma petición, solo casas blandas y línea 0,5); `publish/alta_prob_datos.py` añade los candidatos y la cuota de referencia; `db/042` amplía el CHECK de mercados de `alta_prob_picks`; etiqueta en la web.

**Tech Stack:** Python 3.12, PostgreSQL 16, JS sin framework.

**Decisión del usuario (2026-10-07):** implementarlo con cuota de referencia. **Prueba histórica** (script de solo lectura con el criterio de `eval/alta_prob_calibracion.py`, firma `d5cbc3151164`, rho −0,0613, 14.216 partidos): local n=4.470 prometido 86,97 % real 88,52 %; visitante n=2.447 86,10 % → 87,45 %; los tres tramos pasan en ambos.

## Global Constraints

- Mercados `team_totals_home` / `team_totals_away`, `selection = 'over'`, `line = 0.5` (ya liquidados por `eval/clv._settle_outcome`).
- Probabilidad = `market_team_total(score_matrix(λ, μ, rho), 0.5, lado)["over"]` del MISMO ajuste que los goles (`ap.ajuste_goles`); sin ajuste (sin línea de goles de Pinnacle o ajuste inválido) no hay candidato. Nunca del modelo propio ni de otra fuente.
- La regla no cambia: el de menor probabilidad en [0,80; 0,95]. Desempate exacto: `h2h` 0 > `totals` 1 > `team_totals_*` 2 > `double_chance` 3.
- Texto: "Marca {equipo}".
- Cuota de referencia: solo de las casas de `settings.soft_books`, línea 0,5, lado `over`, de la MISMA respuesta de API-Football que el 1X2 (`provider_updated_at` igual, `fetched_at <= now`). Con snapshot de The Odds API, sin referencia.
- `af_odds`: cero peticiones extra; de los bets 16 ("Total - Home") y 17 ("Total - Away") solo se guardan casas de `soft_books` y solo la línea 0,5, con pares completos.
- No se tocan el sellado, la puerta de valor ni el orden predecir → seleccionar → sellar → publicar.
- Tests: `PYTHONPATH=src "/c/Users/huye/Documents/apuesta proyec/.venv/Scripts/python.exe" -m pytest -p no:cacheprovider -q <tests>` desde la raíz del worktree; suite completa en verde antes de cada commit. Comentarios en español; commits en español con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Task 1: Captura de "más de 0,5" de cada equipo en `af_odds`

**Files:** Modify `src/qf/ingest/af_odds.py`, `tests/test_af_odds.py`.

**Interfaces:** Produces filas `(match_id, fid, book, "team_totals_home"|"team_totals_away", "over"|"under", price, updated, mins, 0.5)`.

- [ ] **Step 1: Test que falla** (en `tests/test_af_odds.py`, usando la fixture `casas` que fija `settings`):

```python
def _equipo(name, bet_id, lineas):
    vals = []
    for ln, (o, u) in lineas.items():
        vals += [{"value": f"Over {ln}", "odd": o}, {"value": f"Under {ln}", "odd": u}]
    return {"name": name, "bets": [{"id": bet_id, "name": "Total", "values": vals}]}


def test_goles_de_cada_equipo_solo_blandas_y_linea_0_5(casas):
    rows = parse(_resp([
        _equipo("Bet365", 16, {0.5: ("1.14", "5.50"), 1.5: ("1.73", "2.00")}),
        _equipo("Betano", 17, {0.5: ("1.44", "2.67")}),
        _equipo("Pinnacle", 17, {0.5: ("1.42", "2.90")}),
        _equipo("Marathonbet", 16, {0.5: ("1.15", "5.00")}),
    ]), "m1", KO)
    eq = {(r[2], r[3], r[4], r[8]) for r in rows if r[3].startswith("team_totals")}
    assert eq == {("bet365", "team_totals_home", s, 0.5) for s in ("over", "under")} | \
                 {("betano", "team_totals_away", s, 0.5) for s in ("over", "under")}
```

- [ ] **Step 2: Código** — constante tras `LINEAS_BLANDAS`:

```python
# "Total - Home" (16) y "Total - Away" (17): solo para la cuota de referencia
# de "marca el local / el visitante" de la línea de alta probabilidad.
TEAM_TOTALS = {16: "team_totals_home", 17: "team_totals_away"}
```

En `parse`, tras la rama `elif bet.get("id") == GOALS_OU:` (mismo nivel):

```python
                elif bet.get("id") in TEAM_TOTALS and book in settings.soft_books:
                    q = _totales(bet).get(0.5)
                    if q:
                        rows += [(match_id, fid, book, TEAM_TOTALS[bet["id"]], s, p,
                                  updated, mins, 0.5) for s, p in q.items()]
```

Actualizar el docstring de `parse` y del módulo (una frase: bets 16/17, casas blandas, línea 0,5).

- [ ] **Step 3:** tests de `af_odds` y suite completa → PASS. Commit "API-Football: guarda "más de 0,5" de cada equipo de las casas blandas".

---

### Task 2: Reglas, migración, prueba histórica y web

**Files:** Modify `src/qf/publish/alta_prob.py`, `src/qf/eval/alta_prob_calibracion.py`, `frontend/app.js` (+ hashes en `frontend/index.html`); Create `db/042_alta_prob_equipo.sql`; Tests `tests/test_alta_prob_reglas.py`, `tests/test_alta_prob_esquema.py`.

**Interfaces:** Produces `ap.MERCADOS_EQUIPO_HABILITADOS: tuple[str, ...] = ("home", "away")`, `ap.MERCADOS_CON_AJUSTE = ("totals", "team_totals_home", "team_totals_away")`, `ap.candidatos_equipo(ajuste: dict | None, lados: tuple[str, ...] | None = None) -> list[Candidato]`.

- [ ] **Step 1: Tests que fallan** (`tests/test_alta_prob_reglas.py`):

```python
def test_marca_cada_equipo_desde_el_ajuste():
    m = score_matrix(1.6, 0.9, -0.06)
    aj = ap.ajuste_goles(market_1x2(m), 2.5, totals_fair_over(m, 2.5), -0.06)
    c = {x.market: x for x in ap.candidatos_equipo(aj)}
    assert set(c) == {"team_totals_home", "team_totals_away"}
    ma = score_matrix(aj["lambda"], aj["mu"], aj["rho"])
    assert c["team_totals_home"].prob == pytest.approx(1 - float(ma[0, :].sum()), abs=1e-12)
    assert c["team_totals_away"].prob == pytest.approx(1 - float(ma[:, 0].sum()), abs=1e-12)
    assert all(x.selection == "over" and x.line == 0.5 for x in c.values())
    assert ap.candidatos_equipo(None) == [] and ap.candidatos_equipo(aj, ()) == []


def test_desempate_con_goles_de_un_equipo():
    cands = [ap.Candidato("double_chance", "1X", None, 0.85),
             ap.Candidato("team_totals_home", "over", 0.5, 0.85),
             ap.Candidato("totals", "over", 1.5, 0.85)]
    assert ap.elegir(cands).market == "totals"
    assert ap.elegir([cands[0], cands[1]]).market == "team_totals_home"


def test_texto_marca_un_equipo():
    assert ap.texto("team_totals_home", "over", 0.5, "Cruzeiro", "Sao Paulo") == "Marca Cruzeiro"
    assert ap.texto("team_totals_away", "over", 0.5, "Cruzeiro", "Sao Paulo") == "Marca Sao Paulo"
```

y en `tests/test_alta_prob_esquema.py`:

```python
SQL42 = (Path(__file__).resolve().parents[1] / "db" / "042_alta_prob_equipo.sql").read_text(encoding="utf-8")


def test_042_amplia_los_mercados_y_comprueba_que_no_queda_el_check_viejo():
    assert "'team_totals_home'" in SQL42 and "'team_totals_away'" in SQL42
    assert "DROP CONSTRAINT IF EXISTS alta_prob_picks_market_check" in SQL42
    assert "RAISE EXCEPTION" in SQL42
```

- [ ] **Step 2: `alta_prob.py`** — tras `MERCADOS_GOLES_HABILITADOS`:

```python
# "Marca el local / el visitante" (más de 0,5 goles de ese equipo), del mismo
# ajuste que los goles. Prueba histórica 2026-10-07 (firma d5cbc3151164…, rho
# −0,0613, 14.216 partidos, criterio de eval/alta_prob_calibracion.py): local
# n=4.470 86,97→88,52; visitante n=2.447 86,10→87,45; los tres tramos pasan.
MERCADOS_EQUIPO_HABILITADOS: tuple[str, ...] = ("home", "away")
# Mercados que guardan el ajuste de goles en `fit`.
MERCADOS_CON_AJUSTE = ("totals", "team_totals_home", "team_totals_away")
```

`_PRIORIDAD = {"h2h": 0, "totals": 1, "team_totals_home": 2, "team_totals_away": 2, "double_chance": 3}`; comentario del campo `market` de `Candidato` con los nuevos valores; importar `market_team_total` de `..model.pricing`. Tras `candidatos_goles`:

```python
def candidatos_equipo(ajuste: dict | None,
                      lados: tuple[str, ...] | None = None) -> list[Candidato]:
    """Más de 0,5 goles de cada equipo, del mismo ajuste que los goles."""
    lados = MERCADOS_EQUIPO_HABILITADOS if lados is None else lados
    if ajuste is None or not lados:
        return []
    m = score_matrix(ajuste["lambda"], ajuste["mu"], ajuste["rho"])
    return [Candidato(f"team_totals_{lado}", "over", 0.5,
                      market_team_total(m, 0.5, lado)["over"]) for lado in lados]
```

En `texto`, antes del `raise`:

```python
    if market in ("team_totals_home", "team_totals_away"):
        return f"Marca {local if market.endswith('home') else visitante}"
```

- [ ] **Step 3: `db/042_alta_prob_equipo.sql`:**

```sql
-- ============================================================================
-- 042 - "Marca el local / el visitante" en la línea de alta probabilidad
-- (decisión del usuario, 2026-10-07). Amplía el CHECK de mercados de 040.
-- El CHECK de 040 se declaró en la columna: PostgreSQL lo llamó
-- alta_prob_picks_market_check (visto en producción el 2026-10-06). La
-- guardia aborta si queda otro CHECK sobre `market` (p. ej. un nombre
-- distinto): con dos CHECK, los mercados nuevos fallarían al insertar.
-- ============================================================================
BEGIN;

ALTER TABLE alta_prob_picks DROP CONSTRAINT IF EXISTS alta_prob_picks_market_check;
ALTER TABLE alta_prob_picks ADD CONSTRAINT alta_prob_picks_market_check
    CHECK (market IN ('h2h', 'double_chance', 'totals',
                      'team_totals_home', 'team_totals_away'));

DO $$ BEGIN
  IF (SELECT count(*) FROM pg_constraint
      WHERE conrelid = 'alta_prob_picks'::regclass AND contype = 'c'
        AND pg_get_constraintdef(oid) LIKE '%market%') <> 1 THEN
    RAISE EXCEPTION 'alta_prob_picks tiene más de un CHECK sobre market: revisar db/042';
  END IF;
END $$;

COMMIT;
```

- [ ] **Step 4: prueba histórica repetible** — en `src/qf/eval/alta_prob_calibracion.py`, en `filas`, añadir `+ ap.candidatos_equipo(ajuste, ("home", "away"))` a `cands` (todos los lados, como hace con `LINEAS_GOLES`), y una línea en el docstring del módulo. No ejecutar la prueba completa (la ejecuta el controlador).

- [ ] **Step 5: web** — en `frontend/app.js`, `ALTA_MERCADO` añade `team_totals_home: 'Marca el local', team_totals_away: 'Marca el visitante'`; recalcular `?v=` de `app.js` en `index.html` (sha256[:12] del archivo); `npm run check` desde `frontend/`.

- [ ] **Step 6:** tests y suite completa → PASS. Commit "Alta probabilidad: "marca el local / el visitante" (reglas, db/042, web)".

---

### Task 3: La línea elige "marca un equipo" y su cuota de referencia

**Files:** Modify `src/qf/publish/alta_prob_datos.py`, `tests/test_alta_prob_datos.py`.

**Interfaces:** Consumes Task 1 (filas `team_totals_*`) y Task 2 (`candidatos_equipo`, `MERCADOS_EQUIPO_HABILITADOS`, `MERCADOS_CON_AJUSTE`). Produces `_equipos_af(match_id, as_of, now) -> list[dict]` con claves `bookmaker, market, selection, line, price`; `decidir(..., equipo: tuple[str, ...] = ())`; `_ref(snap, totales, c, equipos=())`.

- [ ] **Step 1: Tests que fallan:**
  1. `decidir` con un mercado coherente (1X2 + línea 2,5 de Pinnacle fabricados con `score_matrix`/`market_1x2`/`totals_fair_over`, como los tests de goles existentes) donde "marca el local" quede en [0,80; 0,95] y sea el de menor probabilidad, con `habilitados=()` y `equipo=("home", "away")`: elige `team_totals_home` con `fit["linea"] == 2.5`. Con `equipo=()` (por defecto) el resultado es el de antes (los tests existentes no cambian).
  2. `excluir={"team_totals_home"}` lo descarta y gana el siguiente.
  3. `_ref` para `team_totals_home`: toma la mejor cuota `over` línea 0,5 de `soft_books` del MISMO mercado (con distractores: otro mercado, otra línea, lado `under`, casa fuera de la lista).
  4. `select_and_persist(dry_run=True)` con snapshot de API-Football: `_equipos_af` se consulta con `(match_id, snap.as_of, now)` y la decisión de equipo lleva `ref_book`; con snapshot de The Odds API no se consulta `_equipos_af`.
  5. `_equipos_af` filtra `market IN ('team_totals_home', 'team_totals_away')`, `provider_updated_at = %s` y `fetched_at <= %s`.
  En el helper `_db`, añadir `monkeypatch.setattr(ad, "_equipos_af", lambda match_id, as_of, now: [])`.

- [ ] **Step 2: Código** — junto a `_totales_af`:

```python
def _equipos_af(match_id: str, as_of: datetime, now: datetime) -> list[dict]:
    """
    "Más de 0,5" de cada equipo de las casas blandas, de la MISMA respuesta de
    API-Football que el 1X2. Solo da la cuota de referencia: la probabilidad
    sale del ajuste de goles.
    """
    return query(
        """SELECT bookmaker, market, selection, line, price FROM af_odds_snapshots
           WHERE match_id = %s AND market IN ('team_totals_home', 'team_totals_away')
             AND provider_updated_at = %s AND fetched_at <= %s""",
        (match_id, as_of, now))
```

`decidir` pasa a:

```python
def decidir(snap: pk.Snapshot, totales: list[dict], rho: float | None,
            habilitados: tuple, excluir: set[str],
            equipo: tuple[str, ...] = ()) -> tuple[ap.Candidato, dict | None] | None:
    q = snap.books[settings.sharp_book]
    fair = devig([q[s] for s in SEL], settings.devig_method)
    p = {s: float(fair[i]) for i, s in enumerate(SEL)}
    cands = ap.candidatos_1x2(p) + ap.candidatos_doble(p)
    ajuste = None
    if rho is not None and (habilitados or equipo):
        linea = linea_pinnacle(totales)
        if linea is not None:
            ajuste = ap.ajuste_goles(p, linea[0], linea[1], rho)
    if habilitados and "totals" not in excluir:
        cands += ap.candidatos_goles(ajuste, habilitados)
    cands += ap.candidatos_equipo(ajuste, equipo)    # `elegir` aplica `excluir`
    elegido = ap.elegir(cands, excluir)
    if elegido is None:
        return None
    return elegido, (ajuste if elegido.market in ap.MERCADOS_CON_AJUSTE else None)
```

`_ref` gana `equipos: list[dict] = ()` y una rama antes del `else`:

```python
    elif c.market in ("team_totals_home", "team_totals_away"):
        precios = [(float(r["price"]), pk.canonical_book(r["bookmaker"])) for r in equipos
                   if r["market"] == c.market
                   and pk.canonical_book(r["bookmaker"]) in settings.soft_books
                   and r["selection"] == c.selection and r["line"] is not None
                   and float(r["line"]) == c.line]
```

En `select_and_persist`: `equipos = _equipos_af(m["match_id"], snap.as_of, now)` solo en la rama `api_football` (si no, `[]`); `decidir(snap, totales, rho, habilitados, excluir, ap.MERCADOS_EQUIPO_HABILITADOS)`; `_ref(snap, totales, c, equipos)`.

- [ ] **Step 3:** tests y suite completa → PASS. Commit "Alta probabilidad: elige "marca un equipo" con cuota de referencia de la misma respuesta".

---

### Task 4: Despliegue (controlador, antes del 2026-10-08 07:20 UTC)

- [ ] Integrar en `main` (fast-forward) con suite completa y `npm run check` en verde; README (lista de mercados de la línea).
- [ ] Re-ejecutar `python -m qf.eval.alta_prob_calibracion` (con la caché local) y anotar en `harness/progreso.md` la tabla con los mercados de equipo y la regla completa nueva.
- [ ] Comparar `src/ db/ frontend/` del servidor con lo último desplegado (sin CR); respaldo; `git archive HEAD src frontend db README.md docs/superpowers`; `docker compose build api worker`.
- [ ] En un minuto seguro (sin jobs, sin partidos en 15 min, fuera de :15-:32 y de 07:45-08:35 UTC): aplicar `db/042` con `ON_ERROR_STOP` y, acto seguido, `docker compose up -d api worker`; segunda aplicación idempotente.
- [ ] Comprobar en una transacción con ROLLBACK que `team_totals_home` entra y `btts` se rechaza en `alta_prob_picks`; ejecutar `af_odds` a mano una vez (filas `team_totals_*` de casas blandas); `hashchain verify`; salud; vista previa con la línea encendida solo para ese proceso.
