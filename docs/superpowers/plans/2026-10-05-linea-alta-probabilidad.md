# Línea de alta probabilidad — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar en la web, sellados en la cadena de hashes, pronósticos de fútbol con probabilidad real (Pinnacle sin margen) entre 80 % y 95 %, uno por partido, con historial público de acierto prometido frente a real y pausa automática si se promete de más.

**Architecture:** Reglas puras en `src/qf/publish/alta_prob.py` (candidatos 1X2 / doble oportunidad / goles, elección, texto, control, historial) y E/S en `src/qf/publish/alta_prob_datos.py`. El job diario (`daily.py`) elige y guarda **antes** de `seal()`; `hashchain._collect` mete el bloque en el lote del día; la liquidación se encadena a `clv.settle_pending`. Endpoint público `GET /alta-probabilidad`, tarjeta en `/control` y sección nueva en la web estática.

**Tech Stack:** Python 3.12, PostgreSQL 16 (triggers `deny_mutation`), FastAPI, numpy/pandas/scipy, JavaScript sin framework (`frontend/app.js`), `node --test`.

**Diseño:** `docs/superpowers/specs/2026-10-05-linea-alta-probabilidad-design.md` (incluye "Ajustes al escribir el plan").

## Global Constraints

- Probabilidad SIEMPRE de Pinnacle sin margen (`settings.devig_method`, Shin); nunca del modelo Dixon-Coles propio.
- Rango publicable: `PROB_MIN = 0.80`, `PROB_MAX = 0.95` (ambos incluidos). Se publica el candidato de MENOR probabilidad dentro del rango; desempate 1X2 > goles > doble oportunidad.
- Un pronóstico por partido para siempre (`UNIQUE(match_id)`).
- Snapshot de Pinnacle con antigüedad ≤ 6 h y ≥ 15 min antes del kickoff (`picks.MIN_LEAD`); horizonte 36 h.
- Ajuste de goles: error absoluto máximo ≤ 0,01; sin línea de Pinnacle o sin ajuste válido, no hay goles para ese partido (sin relleno con el modelo).
- Tablas nuevas inmutables con `deny_mutation()`. No se tocan `picks`, `v_track_record`, la puerta de CLV ni `PUBLISH_PICKS_ENABLED`. No se reordena predecir → seleccionar → sellar → publicar.
- La API solo muestra pronósticos sellados: lote de su fecha existe y `decided_at <= prediction_batches.created_at`.
- `ALTA_PROB_ENABLED` por defecto `0`. Control: con n ≥ 50 liquidados y el IC95 (remuestreo por semanas, `soft_vs_sharp._weekly_ci`) de `acertado − prob` entero bajo cero → se bloquea (todo o ese mercado). Sin IC (menos de 8 semanas) no bloquea. `ALTA_PROB_CONTROL_DESDE` (fecha) reinicia la ventana.
- Navegador: solo endpoints públicos, sin tokens; todo texto del servidor pasa por `esc()`; sin scroll horizontal a 375 px; hashes `?v=` = primeros 12 hex del sha256 del archivo.
- Comentarios y textos en español, al estilo del repo. Al terminar cada tarea: `./scripts/harness_check.sh` en verde.
- Ejecutar tests: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q <archivos>` (desde la raíz del repo). Frontend: `cd frontend && npm run check`.
- Despliegue: el servidor (`ssh quantfut`, repo en `~/quantfut`) va por detrás de HEAD. Nada se despliega sin la Tarea 0 y sin visto bueno explícito del usuario a la lista de cambios. **Nunca** lanzar `python -m qf.publish.daily` a mano (sellaría o duplicaría predicciones).

---

### Task 0: Sincronizar el servidor con HEAD (paso previo, con aprobación del usuario)

Es una tarea de operación, sin TDD. No se avanza a la Tarea 10 sin haberla cerrado.

**Files:**
- Ninguno en el repo (salvo commit de trabajo pendiente, con permiso).

- [ ] **Step 1: Preguntar al usuario por el trabajo sin commitear de esta sesión**

`git status --short` muestra cambios de esta sesión ya desplegados a mano (`src/qf/api/console.py`, `src/qf/publish/shadow_sharp.py`, `frontend/*`, `tests/test_web_console.py`, `tests/test_sombra_sharp.py`, `README.md`) y cambios previos ajenos en `harness/*.md`. Si se sincroniza sin commitearlos, `git archive HEAD` **revertiría en producción** la tabla de `/control` y la probabilidad real de la web. Pedir al usuario permiso para commitearlos (solo esos archivos; `apps/` y `docs/nba_*` sin trackear se quedan fuera):

```bash
git add src/qf/api/console.py src/qf/publish/shadow_sharp.py frontend/app.js frontend/index.html frontend/public-data.js frontend/public-data.test.mjs frontend/styles.css frontend/console.css tests/test_web_console.py tests/test_sombra_sharp.py README.md harness/progreso.md harness/tareas.md
git commit -m "Panel /control con picks de la sombra y probabilidad real en la web

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 2: Calcular la lista exacta de archivos que cambiarían en producción**

```bash
git ls-files src frontend db scripts Dockerfile requirements.txt docker-compose.yml Caddyfile grafana | while read f; do echo "$(git show HEAD:"$f" | md5sum | cut -c1-32)  $f"; done | sort -k2 > /tmp/head.md5
ssh quantfut 'cd ~/quantfut && find src frontend db scripts grafana Dockerfile requirements.txt docker-compose.yml Caddyfile -type f ! -path "*__pycache__*" -exec md5sum {} +' | sort -k2 > /tmp/srv.md5
join -1 2 -2 2 -a 1 -e AUSENTE -o 0,1.1,2.1 /tmp/head.md5 /tmp/srv.md5 | awk '$2 != $3 {print $1, ($3=="AUSENTE" ? "(nuevo)" : "(modificado)")}' > /tmp/cambios.txt
while read f estado; do echo "$f $estado — $(git log -1 --format='%h %s' -- "$f")"; done < /tmp/cambios.txt
```

Expected: lista de archivos con el último commit que los tocó (incluye al menos `src/qf/model/promotion.py`, `src/qf/eval/clv.py`, `src/qf/model/dixon_coles.py`, `src/qf/ingest/api_football.py`).

- [ ] **Step 3: Enseñar la lista al usuario y esperar un "sí" explícito**

Resumir en español qué cambia en producción por grupos (puerta comercial, modelo, ingesta, web) y señalar los de riesgo (`promotion.py` decide la puerta; `dixon_coles.py` afecta a las predicciones del día siguiente; cualquier `db/*.sql` nuevo sin aplicar). Si hay `db/*.sql` en la lista, comprobar si sus objetos existen en producción antes de seguir:

```bash
ssh quantfut 'docker exec -i quantfut-db-1 sh -c "psql -U \$POSTGRES_USER -d \$POSTGRES_DB -At -c \"\\dt\""' | sort
```

No continuar sin el visto bueno.

- [ ] **Step 4: Respaldo y sincronización (fuera de :20-:30 y de 07:50-08:30 UTC, por el cron)**

```bash
ssh quantfut 'cat ~/quantfut/scripts/crontab | grep -v "^#" | grep -v "^$"'
ssh quantfut 'cd ~ && tar --exclude=quantfut/.git -czf respaldo_$(date +%Y%m%d)_presync.tgz quantfut'
git archive --format=tar HEAD src frontend db scripts grafana Dockerfile requirements.txt docker-compose.yml Caddyfile README.md CLAUDE.md harness | ssh quantfut 'cd ~/quantfut && tar -xf -'
ssh quantfut 'cd ~/quantfut && docker compose build api worker && docker compose up -d api worker'
```

Expected: build sin errores y `api`/`worker` en estado `Up`.

- [ ] **Step 5: Verificar**

```bash
ssh quantfut 'cd ~/quantfut && docker compose ps --format "{{.Service}} {{.Status}}"'
ssh quantfut 'cd ~/quantfut && docker compose exec -T worker python -m qf.publish.hashchain verify'
ssh quantfut 'cd ~/quantfut && docker compose exec -T worker python -c "from qf.ingest.health import run; import json; print(json.dumps(run(alert_on_fail=False), ensure_ascii=False, default=str)[:1500])"'
ssh quantfut 'cd ~/quantfut && docker compose exec -T api python -c "import urllib.request as u, json; d=json.load(u.urlopen(\"http://localhost:8000/model-card\")); print(d[\"puerta_comercial\"][\"publicacion_de_picks\"]); print(u.urlopen(\"http://localhost:8000/\").status)"'
```

Expected: `verify` OK, chequeo de salud sin fallos nuevos, `pausada: …` y `200`. Comprobar además en el navegador `https://api.pronosticosdeportivos.pro/#picks` (la probabilidad real sigue visible) y que `/control` responde 401 sin credenciales.

- [ ] **Step 6: Anotar en `harness/progreso.md`** la decisión (qué se desplegó y por qué ahora) y commitear.

---

### Task 1: Probabilidad justa de totales con push y ajuste de goles con cualquier línea

**Files:**
- Modify: `src/qf/model/pricing.py` (añadir `totals_fair_over` tras `market_totals`, ~línea 81)
- Modify: `src/qf/model/market_anchor.py:43` (import) y `:69-84` (`_targets`)
- Test: `tests/test_totales_justos.py` (nuevo)

**Interfaces:**
- Produces: `pricing.totals_fair_over(m: np.ndarray, line: float) -> float` — 1/cuota justa del over en una línea de medio gol, gol entero o cuarto de gol. `market_anchor.market_lambdas(..., totals={line: p_over_justa})` acepta cualquiera de esas líneas.

- [ ] **Step 1: Escribir los tests que fallan**

```python
"""
La cuota justa de un over con push no es 1/P(over). En gol entero el push
devuelve la apuesta; en cuarto de gol la apuesta se reparte entre las dos
líneas vecinas. Pinnacle cotiza así dos de cada tres partidos.
"""
import pytest

from qf.model.market_anchor import market_lambdas
from qf.model.pricing import market_1x2, market_totals, score_matrix, totals_fair_over

M = score_matrix(1.6, 1.1, -0.06)


def _p_total(k):
    n = M.shape[0]
    return float(sum(M[i, k - i] for i in range(max(0, k - n + 1), min(k, n - 1) + 1)))


def test_medio_gol_es_p_over():
    assert totals_fair_over(M, 2.5) == pytest.approx(market_totals(M, 2.5)["over"], abs=1e-12)


def test_gol_entero_excluye_el_push():
    t = market_totals(M, 3.0)
    assert totals_fair_over(M, 3.0) == pytest.approx(t["over"] / (t["over"] + t["under"]), abs=1e-12)


def test_cuarto_de_gol_reparte_entre_vecinas():
    p3 = _p_total(3)
    p4_mas = market_totals(M, 3.5)["over"]
    assert totals_fair_over(M, 2.75) == pytest.approx((p4_mas + 0.5 * p3) / (1 - 0.5 * p3), abs=1e-12)
    assert totals_fair_over(M, 3.25) == pytest.approx(p4_mas / (1 - 0.5 * p3), abs=1e-12)


@pytest.mark.parametrize("line", [2.25, 2.75, 3.0, 3.25])
def test_a_cuota_justa_el_valor_esperado_es_cero(line):
    cuota = 1 / totals_fair_over(M, line)
    partes = (line - 0.25, line + 0.25) if round(line * 4) % 2 else (line, line)
    n = M.shape[0]
    ev = 0.0
    for i in range(n):
        for j in range(n):
            tot = i + j
            retorno = sum(0.5 * (cuota if tot > c else 1.0 if tot == c else 0.0) for c in partes)
            ev += M[i, j] * retorno
    assert ev == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize("line", [2.5, 2.75, 3.0])
def test_el_ajuste_recupera_las_lambdas_con_cualquier_linea(line):
    p = market_1x2(M)
    fit = market_lambdas(p["home"], p["draw"], p["away"], rho=-0.06,
                         totals={line: totals_fair_over(M, line)})
    assert fit.lam == pytest.approx(1.6, abs=2e-3)
    assert fit.mu == pytest.approx(1.1, abs=2e-3)
    assert fit.residual < 1e-3
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_totales_justos.py`
Expected: FAIL con `ImportError: cannot import name 'totals_fair_over'`.

- [ ] **Step 3: Implementar `totals_fair_over` en `src/qf/model/pricing.py`** (justo después de `market_totals`)

```python
def totals_fair_over(m: np.ndarray, line: float) -> float:
    """
    Probabilidad del over tal como la da un mercado de dos vías sin margen:
    1 / cuota justa. En medio gol es P(over). En gol entero el push devuelve
    la apuesta y en cuarto de gol (2,75 = mitad a 2,5 y mitad a 3) se reparte
    entre las dos líneas vecinas; resolviendo EV = 0 queda
    E[gana] / (1 − E[push]).
    """
    n = m.shape[0]
    hg, ag = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    tot = hg + ag
    partes = (line - 0.25, line + 0.25) if round(line * 4) % 2 else (line, line)
    gana = np.mean([float(m[tot > c].sum()) for c in partes])
    push = np.mean([float(m[tot == c].sum()) for c in partes])
    return float(gana / (1.0 - push))
```

- [ ] **Step 4: Usarla en `market_anchor._targets`**

En `src/qf/model/market_anchor.py`, cambiar el import:

```python
from .pricing import market_1x2, score_matrix, totals_fair_over
```

y el bucle de totales de `_targets`:

```python
    # Los totales sobre-identifican el sistema: con 1X2 solo hay exactamente
    # dos ecuaciones libres para dos incógnitas, así que el over/under no
    # cambia la solución cuando el mercado es coherente, pero cuando NO lo es
    # el residuo lo delata en vez de esconderlo. `p_over` es la del mercado
    # de dos vías sin margen: en gol entero y cuarto de gol lleva el push
    # descontado, por eso se compara con `totals_fair_over` y no con P(over).
    for line, p_over in (totals or {}).items():
        out.append((lambda m, ln=float(line): totals_fair_over(m, ln),
                    float(p_over), 0.5))
```

- [ ] **Step 5: Ejecutar los tests nuevos y los de `market_anchor`**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_totales_justos.py tests/test_market_anchor.py`
Expected: todos PASS (los de `market_anchor` usan líneas de medio gol, donde la fórmula no cambia).

- [ ] **Step 6: Commit**

```bash
git add src/qf/model/pricing.py src/qf/model/market_anchor.py tests/test_totales_justos.py
git commit -m "Totales: probabilidad justa con push para líneas enteras y de cuarto

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Reglas puras de la línea (`publish/alta_prob.py`)

**Files:**
- Create: `src/qf/publish/alta_prob.py`
- Test: `tests/test_alta_prob_reglas.py` (nuevo)

**Interfaces:**
- Consumes: `market_anchor.market_lambdas`, `pricing.score_matrix`, `pricing.market_totals` (Task 1).
- Produces:
  - constantes `PROB_MIN=0.80`, `PROB_MAX=0.95`, `MAX_EDAD_PRECIO=timedelta(hours=6)`, `HORIZONTE=timedelta(hours=36)`, `MAX_RESIDUO_AJUSTE=0.01`, `LINEAS_GOLES=(("over",1.5),("under",3.5),("under",4.5))`, `MERCADOS_GOLES_HABILITADOS: tuple[tuple[str, float], ...] = ()`, `MIN_N_CONTROL=50`.
  - `@dataclass(frozen=True) Candidato(market: str, selection: str, line: float | None, prob: float)`.
  - `candidatos_1x2(p: dict[str, float]) -> list[Candidato]`, `candidatos_doble(p) -> list[Candidato]`.
  - `ajuste_goles(p: dict[str, float], linea: float, p_over: float, rho: float) -> dict | None` → `{"lambda","mu","rho","linea","residuo"}`.
  - `candidatos_goles(ajuste: dict | None, habilitados: tuple | None = None) -> list[Candidato]`.
  - `elegir(cands: list[Candidato], excluir: set[str] = frozenset()) -> Candidato | None`.
  - `texto(market: str, selection: str, line: float | None, local: str, visitante: str) -> str`.

- [ ] **Step 1: Escribir los tests que fallan** (`tests/test_alta_prob_reglas.py`)

```python
"""Reglas de la línea de alta probabilidad, sin base de datos."""
import pytest

from qf.model.pricing import market_1x2, score_matrix, totals_fair_over
from qf.publish import alta_prob as ap

P = {"home": 0.62, "draw": 0.24, "away": 0.14}


def test_doble_oportunidad_es_la_suma_exacta():
    d = {c.selection: c.prob for c in ap.candidatos_doble(P)}
    assert d == pytest.approx({"1X": 0.86, "X2": 0.38, "12": 0.76})
    assert all(c.market == "double_chance" for c in ap.candidatos_doble(P))


def test_elige_el_de_menor_probabilidad_dentro_del_rango():
    cands = [ap.Candidato("h2h", "home", None, 0.82),
             ap.Candidato("double_chance", "1X", None, 0.93),
             ap.Candidato("totals", "under", 4.5, 0.97)]
    assert ap.elegir(cands) == cands[0]


def test_nada_si_ninguno_entra():
    assert ap.elegir([ap.Candidato("h2h", "home", None, 0.79),
                      ap.Candidato("double_chance", "1X", None, 0.951)]) is None


def test_limites_incluidos():
    assert ap.elegir([ap.Candidato("h2h", "home", None, 0.80)]).prob == 0.80
    assert ap.elegir([ap.Candidato("double_chance", "1X", None, 0.95)]).prob == 0.95


def test_desempate_1x2_goles_doble():
    cands = [ap.Candidato("double_chance", "1X", None, 0.85),
             ap.Candidato("totals", "under", 3.5, 0.85),
             ap.Candidato("h2h", "home", None, 0.85)]
    assert ap.elegir(cands).market == "h2h"
    assert ap.elegir(cands[:2]).market == "totals"


def test_excluir_un_mercado_bloqueado():
    cands = [ap.Candidato("h2h", "home", None, 0.82),
             ap.Candidato("double_chance", "1X", None, 0.93)]
    assert ap.elegir(cands, excluir={"h2h"}).market == "double_chance"


def test_goles_desde_un_ajuste_al_mercado():
    m = score_matrix(1.7, 0.9, -0.06)
    p = market_1x2(m)
    ajuste = ap.ajuste_goles(p, 2.75, totals_fair_over(m, 2.75), -0.06)
    assert ajuste is not None and ajuste["linea"] == 2.75
    goles = {(c.selection, c.line): c.prob
             for c in ap.candidatos_goles(ajuste, ap.LINEAS_GOLES)}
    m_ajuste = score_matrix(ajuste["lambda"], ajuste["mu"], -0.06)
    assert goles[("over", 1.5)] == pytest.approx(float(m_ajuste.sum() - m_ajuste[0, 0] - m_ajuste[1, 0] - m_ajuste[0, 1]), abs=1e-9)


def test_sin_mercados_habilitados_no_hay_goles():
    m = score_matrix(1.7, 0.9, -0.06)
    ajuste = ap.ajuste_goles(market_1x2(m), 2.5, totals_fair_over(m, 2.5), -0.06)
    assert ap.candidatos_goles(ajuste, ()) == []
    assert ap.candidatos_goles(None, ap.LINEAS_GOLES) == []


def test_ajuste_incoherente_se_rechaza():
    # 1X2 equilibrado con un over 2,5 al 97 %: ninguna pareja de lambdas
    # reproduce las dos cosas a menos de 0,01.
    assert ap.ajuste_goles({"home": 0.4, "draw": 0.3, "away": 0.3}, 2.5, 0.97, -0.06) is None


@pytest.mark.parametrize("market,sel,line,esperado", [
    ("h2h", "home", None, "Gana Cruzeiro"),
    ("h2h", "away", None, "Gana Sao Paulo"),
    ("double_chance", "1X", None, "Cruzeiro o empate"),
    ("double_chance", "X2", None, "Sao Paulo o empate"),
    ("double_chance", "12", None, "Cruzeiro o Sao Paulo (sin empate)"),
    ("totals", "over", 1.5, "Más de 1,5 goles"),
    ("totals", "under", 4.5, "Menos de 4,5 goles"),
])
def test_texto(market, sel, line, esperado):
    assert ap.texto(market, sel, line, "Cruzeiro", "Sao Paulo") == esperado
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_reglas.py`
Expected: FAIL con `ImportError: cannot import name 'alta_prob'`.

- [ ] **Step 3: Implementar `src/qf/publish/alta_prob.py`**

```python
"""
Línea de alta probabilidad: un pronóstico por partido con probabilidad real
entre el 80 % y el 95 %.

Es una línea de ACIERTO, no de valor (decisión del usuario, 2026-10-05; diseño
en docs/superpowers/specs/2026-10-05-linea-alta-probabilidad-design.md). Con
las casas de los suscriptores estos resultados no tienen valor esperado
positivo: football-data 2019-2025, favorito ≥ 80 %, ROI −2,4 % y EV al cierre
−2,6 %. Lo que sí se cumple es lo prometido: Pinnacle sin margen está
calibrado (84,6 % previsto, 84,8 % real; doble oportunidad 87,2 / 87,8).

POR QUÉ PINNACLE Y NO EL MODELO
-------------------------------
El modelo no bate al cierre sin margen (README, model-card). Aquí la promesa
es un porcentaje: tiene que salir de la referencia mejor calibrada.

LA REGLA
--------
Candidatos de 1X2, doble oportunidad (suma exacta del 1X2) y goles (desde
los goles esperados que reproducen el 1X2 y la línea de Pinnacle,
`market_anchor.market_lambdas`). Se publica el de MENOR probabilidad dentro
de [PROB_MIN, PROB_MAX]: el más informativo sin bajar del 80 %. El tope evita
obviedades ("menos de 5,5 goles" al 98 %).

Este módulo es la parte pura. La base de datos está en `alta_prob_datos.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from ..model.market_anchor import market_lambdas
from ..model.pricing import market_totals, score_matrix

PROB_MIN = 0.80
PROB_MAX = 0.95
MAX_EDAD_PRECIO = timedelta(hours=6)
HORIZONTE = timedelta(hours=36)
# Error absoluto máximo del ajuste de goles sobre las probabilidades de
# entrada. Por encima, el 1X2 y la línea de goles de Pinnacle no caben en la
# misma pareja de lambdas y los goles derivados no serían de fiar.
MAX_RESIDUO_AJUSTE = 0.01
# Las líneas que se calculan. Solo se publican las de
# MERCADOS_GOLES_HABILITADOS, que pasaron la prueba histórica
# (eval/alta_prob_calibracion.py). Cambiar esa lista exige repetir la prueba.
LINEAS_GOLES: tuple[tuple[str, float], ...] = (("over", 1.5), ("under", 3.5), ("under", 4.5))
MERCADOS_GOLES_HABILITADOS: tuple[tuple[str, float], ...] = ()
# Liquidados mínimos antes de que el control pueda pausar la línea.
MIN_N_CONTROL = 50
# Desempate exacto entre candidatos de la misma probabilidad.
_PRIORIDAD = {"h2h": 0, "totals": 1, "double_chance": 2}
_SEL = ("home", "draw", "away")


@dataclass(frozen=True)
class Candidato:
    market: str              # 'h2h' | 'double_chance' | 'totals' (los de clv._settle_outcome)
    selection: str           # home/draw/away · 1X/X2/12 · over/under
    line: float | None
    prob: float


def candidatos_1x2(p: dict[str, float]) -> list[Candidato]:
    return [Candidato("h2h", s, None, float(p[s])) for s in _SEL]


def candidatos_doble(p: dict[str, float]) -> list[Candidato]:
    return [Candidato("double_chance", "1X", None, float(p["home"] + p["draw"])),
            Candidato("double_chance", "X2", None, float(p["draw"] + p["away"])),
            Candidato("double_chance", "12", None, float(p["home"] + p["away"]))]


def ajuste_goles(p: dict[str, float], linea: float, p_over: float,
                 rho: float) -> dict | None:
    """Goles esperados de mercado, o None si el ajuste no reproduce la entrada."""
    try:
        fit = market_lambdas(p["home"], p["draw"], p["away"], rho=rho,
                             totals={linea: p_over})
    except ValueError:
        return None
    if not fit.converged or fit.residual > MAX_RESIDUO_AJUSTE:
        return None
    return {"lambda": fit.lam, "mu": fit.mu, "rho": rho,
            "linea": linea, "residuo": fit.residual}


def candidatos_goles(ajuste: dict | None,
                     habilitados: tuple[tuple[str, float], ...] | None = None
                     ) -> list[Candidato]:
    habilitados = MERCADOS_GOLES_HABILITADOS if habilitados is None else habilitados
    if ajuste is None or not habilitados:
        return []
    m = score_matrix(ajuste["lambda"], ajuste["mu"], ajuste["rho"])
    return [Candidato("totals", sel, linea, market_totals(m, linea)[sel])
            for sel, linea in habilitados]


def elegir(cands: list[Candidato], excluir: set[str] | frozenset = frozenset()
           ) -> Candidato | None:
    dentro = [c for c in cands
              if c.market not in excluir and PROB_MIN <= c.prob <= PROB_MAX]
    if not dentro:
        return None
    return min(dentro, key=lambda c: (c.prob, _PRIORIDAD[c.market]))


def _goles(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def texto(market: str, selection: str, line: float | None,
          local: str, visitante: str) -> str:
    """El pronóstico en palabras, como se enseña en la web."""
    if market == "h2h":
        return {"home": f"Gana {local}", "away": f"Gana {visitante}",
                "draw": "Empate"}[selection]
    if market == "double_chance":
        return {"1X": f"{local} o empate", "X2": f"{visitante} o empate",
                "12": f"{local} o {visitante} (sin empate)"}[selection]
    if market == "totals":
        return f"{'Más' if selection == 'over' else 'Menos'} de {_goles(line)} goles"
    raise ValueError(f"Mercado desconocido: {market}")
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_reglas.py`
Expected: PASS (medido: el caso incoherente deja un residuo de 0,113, muy por encima de 0,01).

- [ ] **Step 5: Commit**

```bash
git add src/qf/publish/alta_prob.py tests/test_alta_prob_reglas.py
git commit -m "Alta probabilidad: reglas puras de candidatos, elección y texto

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Prueba histórica de calibración y lista de goles habilitados

**Files:**
- Create: `src/qf/eval/alta_prob_calibracion.py`
- Modify: `src/qf/publish/alta_prob.py` (`MERCADOS_GOLES_HABILITADOS`, solo según el resultado)
- Test: `tests/test_alta_prob_calibracion.py` (nuevo)

**Interfaces:**
- Consumes: `alta_prob.candidatos_1x2/candidatos_doble/ajuste_goles/candidatos_goles/elegir/LINEAS_GOLES/PROB_MIN/PROB_MAX` (Task 2); `soft_vs_sharp.load_csvs/_prepare/DEFAULT_SEASONS`; `clv._settle_outcome`.
- Produces: `evaluar(f: pd.DataFrame) -> dict[str, dict]` con `{"n","prometido","real","diferencia_pts","tramos","pasa"}` por mercado; `run(rho: float, cache_dir: Path) -> dict`.

- [ ] **Step 1: Escribir los tests del criterio** (`tests/test_alta_prob_calibracion.py`)

```python
"""El criterio de la prueba histórica, fijado antes de ver los resultados."""
import numpy as np
import pandas as pd

from qf.eval import alta_prob_calibracion as cal


def _f(mercado, prob, aciertos, n):
    won = np.zeros(n, dtype=bool)
    won[:aciertos] = True
    return pd.DataFrame({"mercado": mercado, "prob": prob, "won": won,
                         "elegido": True, "week": "2024-01-01/2024-01-07"})


def test_pasa_si_cumple_lo_prometido():
    r = cal.evaluar(_f("totals over 1.5", 0.86, 172, 200))
    assert r["totals over 1.5"]["pasa"] is True


def test_no_pasa_si_un_tramo_queda_dos_errores_por_debajo():
    # Prometido 86 %, real 76 %: SE = sqrt(.86*.14/200) = 2,45 pts.
    r = cal.evaluar(_f("totals under 3.5", 0.86, 152, 200))
    assert r["totals under 3.5"]["pasa"] is False


def test_tramo_pequeno_no_decide_pero_el_conjunto_si():
    # n = 60 < 100: el tramo no decide; el déficit total (−5 pts) sí.
    r = cal.evaluar(_f("h2h", 0.85, 48, 60))
    assert r["h2h"]["tramos"][0]["decide"] is False
    assert r["h2h"]["pasa"] is False


def test_deficit_de_un_punto_es_el_limite():
    r = cal.evaluar(_f("double_chance", 0.87, 860, 1000))   # −1,0 pts exacto
    assert r["double_chance"]["diferencia_pts"] == -1.0
    assert r["double_chance"]["pasa"] is True
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_calibracion.py`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementar `src/qf/eval/alta_prob_calibracion.py`**

```python
"""
Prueba histórica de la línea de alta probabilidad (diseño 2026-10-05, §4.1).

Repite la selección sobre football-data con el 1X2 (PSH/PSD/PSA) y el 2,5
(P>2.5 / P<2.5) de Pinnacle PRE-CIERRE (de uno a tres días antes) y compara la
probabilidad prometida con lo ocurrido, por mercado y tramo.

CRITERIO, fijado ANTES de ver los resultados: un mercado pasa si
  (a) en cada tramo con n ≥ MIN_N_TRAMO, real ≥ prometido − 2·SE, y
  (b) en conjunto, real − prometido ≥ −MAX_DEFICIT_PTS puntos.
Solo los mercados de goles que pasan entran en
`alta_prob.MERCADOS_GOLES_HABILITADOS`. El 1X2 y la doble oportunidad se
miden igual para dejar constancia.

LÍMITE: football-data solo trae la línea 2,5. Las de cuarto y gol entero que
Pinnacle cotiza en vivo no se pueden validar aquí; las cubre el control en
vivo por mercado (`alta_prob.control`).

FUGAS: la selección solo lee cuotas pre-cierre; el resultado solo se usa al
evaluar.

Uso: python -m qf.eval.alta_prob_calibracion [--rho -0.0613]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig, two_way_devig
from ..publish import alta_prob as ap
from . import soft_vs_sharp as sv
from .clv import _settle_outcome

# Las 7 ligas de formato principal (leagues.fd_code con fd_extra = FALSE).
LIGAS = {"de.bundesliga": "D1", "es.laliga": "SP1", "fr.ligue_1": "F1",
         "gb.premier_league": "E0", "it.serie_a": "I1", "nl.eredivisie": "N1",
         "pt.primeira": "P1"}
COLS = ["PSH", "PSD", "PSA", "P>2.5", "P<2.5"]
TRAMOS = ((0.80, 0.85), (0.85, 0.90), (0.90, 0.95 + 1e-9))
MIN_N_TRAMO = 100
MAX_DEFICIT_PTS = 1.0
# rho del modelo activo el 2026-10-05 (2026.09.27-010508, /model-card).
RHO_POR_DEFECTO = -0.0613


def _nombre(c: ap.Candidato) -> str:
    return c.market if c.market != "totals" else f"totals {c.selection} {c.line:g}"


def filas(raw: pd.DataFrame, rho: float) -> pd.DataFrame:
    """Una fila por candidato dentro del rango, con si acertó y si era el elegido."""
    df = sv._prepare(raw)
    if not set(COLS) <= set(df.columns):
        return pd.DataFrame()
    df[COLS] = df[COLS].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=COLS)
    df = df[(df[COLS] > 1.0).all(axis=1)]
    out = []
    for r in df.to_dict("records"):
        p1x2 = devig([r["PSH"], r["PSD"], r["PSA"]], settings.devig_method)
        p = {"home": float(p1x2[0]), "draw": float(p1x2[1]), "away": float(p1x2[2])}
        p_over, _ = two_way_devig(r["P>2.5"], r["P<2.5"], settings.devig_method)
        ajuste = ap.ajuste_goles(p, 2.5, p_over, rho)
        cands = (ap.candidatos_1x2(p) + ap.candidatos_doble(p)
                 + ap.candidatos_goles(ajuste, ap.LINEAS_GOLES))
        elegido = ap.elegir(cands)
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        for c in cands:
            if not ap.PROB_MIN <= c.prob <= ap.PROB_MAX:
                continue
            out.append({"mercado": _nombre(c), "prob": c.prob,
                        "won": _settle_outcome(c.market, c.selection, c.line, hg, ag)[0] == "win",
                        "elegido": c == elegido, "week": r["week"]})
    return pd.DataFrame(out)


def evaluar(f: pd.DataFrame) -> dict[str, dict]:
    res = {}
    for nombre, g in f.groupby("mercado"):
        tramos, ok = [], True
        for lo, hi in TRAMOS:
            t = g[(g["prob"] >= lo) & (g["prob"] < hi)]
            if t.empty:
                continue
            prom, real = float(t["prob"].mean()), float(t["won"].mean())
            se = float(np.sqrt(prom * (1 - prom) / len(t)))
            decide = len(t) >= MIN_N_TRAMO
            pasa = (not decide) or real >= prom - 2 * se
            ok = ok and pasa
            tramos.append({"tramo": f"{lo:.2f}-{min(hi, 0.95):.2f}", "n": int(len(t)),
                           "prometido": round(prom * 100, 2), "real": round(real * 100, 2),
                           "se_pts": round(se * 100, 2), "decide": decide, "pasa": pasa})
        dif = round((float(g["won"].mean()) - float(g["prob"].mean())) * 100, 2)
        ok = ok and dif >= -MAX_DEFICIT_PTS
        res[str(nombre)] = {"n": int(len(g)), "prometido": round(float(g["prob"].mean()) * 100, 2),
                            "real": round(float(g["won"].mean()) * 100, 2),
                            "diferencia_pts": dif, "tramos": tramos, "pasa": bool(ok)}
    return res


def run(rho: float = RHO_POR_DEFECTO, cache_dir: Path = Path(".local/fd_cache")) -> dict:
    raw, dataset = sv.load_csvs(LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    f = filas(raw, rho)
    elegidos = f[f["elegido"]].assign(mercado="regla completa")
    return {"dataset_sha256": dataset["sha256"], "partidos": dataset["rows"], "rho": rho,
            "por_mercado": evaluar(f),
            "regla_completa": evaluar(elegidos).get("regla completa"),
            "goles_que_pasan": sorted(k for k, v in evaluar(f).items()
                                      if k.startswith("totals") and v["pasa"])}


if __name__ == "__main__":
    ap_ = argparse.ArgumentParser(description="Prueba histórica de la línea de alta probabilidad")
    ap_.add_argument("--rho", type=float, default=RHO_POR_DEFECTO)
    ap_.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    a = ap_.parse_args()
    print(json.dumps(run(a.rho, a.cache), indent=2, ensure_ascii=False))
```

- [ ] **Step 4: Ejecutar los tests del criterio**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_calibracion.py`
Expected: PASS.

- [ ] **Step 5: Correr la prueba real** (usa la caché local `.local/fd_cache`, 42 CSV; sin red)

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m qf.eval.alta_prob_calibracion > .local/alta_prob_calibracion.json; tail -c 1500 .local/alta_prob_calibracion.json`
Expected: JSON con `dataset_sha256` empezando por `d5cbc3151164`, `h2h` y `double_chance` con `pasa: true` (ya medido: 84,6/84,8 y 87,2/87,8), y la lista `goles_que_pasan`.

Si `h2h` o `double_chance` NO pasan, parar y avisar al usuario: contradice la medición del diseño y algo está mal en el script.

- [ ] **Step 6: Fijar `MERCADOS_GOLES_HABILITADOS` con el resultado**

En `src/qf/publish/alta_prob.py`, sustituir la tupla vacía por las entradas de `LINEAS_GOLES` cuyo nombre (`"totals over 1.5"`, `"totals under 3.5"`, `"totals under 4.5"`) esté en `goles_que_pasan`, con un comentario con la firma y la fecha. Por ejemplo, si pasan las tres:

```python
# Pasaron la prueba histórica el 2026-10-0X (eval/alta_prob_calibracion.py,
# firma d5cbc3151164…, rho −0,0613): ver harness/progreso.md.
MERCADOS_GOLES_HABILITADOS: tuple[tuple[str, float], ...] = (
    ("over", 1.5), ("under", 3.5), ("under", 4.5))
```

Si no pasa ninguna, dejar `()` y el comentario con el resultado. Anotar en `harness/progreso.md` la tabla por mercado (n, prometido, real, diferencia) y la firma.

- [ ] **Step 7: Ejecutar todos los tests de la línea y commit**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_reglas.py tests/test_alta_prob_calibracion.py`
Expected: PASS.

```bash
git add src/qf/eval/alta_prob_calibracion.py src/qf/publish/alta_prob.py tests/test_alta_prob_calibracion.py harness/progreso.md
git commit -m "Alta probabilidad: prueba histórica de calibración y goles habilitados

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Migración `db/040` y configuración

**Files:**
- Create: `db/040_alta_probabilidad.sql`
- Modify: `src/qf/config.py` (tras `publish_picks_enabled`, ~línea 83)
- Modify: `.env.example` si existe (añadir las dos variables comentadas)
- Test: `tests/test_alta_prob_esquema.py` (nuevo)

**Interfaces:**
- Produces: tablas `alta_prob_picks` y `alta_prob_results` (columnas exactas abajo); `settings.alta_prob_enabled: bool` (defecto `False`); `settings.alta_prob_control_desde: str` (defecto `""`).

- [ ] **Step 1: Escribir los tests que fallan**

```python
"""Esquema y configuración de la línea de alta probabilidad."""
from pathlib import Path

from qf.config import settings

SQL = (Path(__file__).resolve().parents[1] / "db" / "040_alta_probabilidad.sql").read_text(encoding="utf-8")


def test_tablas_inmutables():
    assert SQL.count("EXECUTE FUNCTION deny_mutation()") == 2
    assert "BEFORE UPDATE OR DELETE ON alta_prob_picks" in SQL
    assert "BEFORE UPDATE OR DELETE ON alta_prob_results" in SQL


def test_un_pronostico_por_partido_y_rango_en_la_base():
    assert "match_id     TEXT NOT NULL UNIQUE REFERENCES matches(match_id)" in SQL
    assert "CHECK (prob >= 0.80 AND prob <= 0.95)" in SQL
    assert "CHECK (market IN ('h2h', 'double_chance', 'totals'))" in SQL


def test_apagada_por_defecto():
    assert settings.alta_prob_enabled is False
    assert settings.alta_prob_control_desde == ""
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_esquema.py`
Expected: FAIL con `FileNotFoundError` (no existe `db/040`).

- [ ] **Step 3: Crear `db/040_alta_probabilidad.sql`**

```sql
-- ============================================================================
-- 040 - Línea de alta probabilidad (decisión del usuario, 2026-10-05)
--
-- Pronósticos con probabilidad real (Pinnacle sin margen) entre el 80 y el
-- 95 %, uno por partido, aparte de los picks de valor: ni `picks` ni su puerta
-- comercial se tocan. Diseño:
-- docs/superpowers/specs/2026-10-05-linea-alta-probabilidad-design.md
--
-- Inmutables como `picks`: un pronóstico fallado no se borra ni se corrige.
-- `prob` en DOUBLE PRECISION: con REAL, el redondeo podía dejar un 0,80
-- justo por debajo del CHECK.
-- ============================================================================
BEGIN;

CREATE TABLE IF NOT EXISTS alta_prob_picks (
    alta_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id     TEXT NOT NULL UNIQUE REFERENCES matches(match_id),
    market       TEXT NOT NULL CHECK (market IN ('h2h', 'double_chance', 'totals')),
    selection    TEXT NOT NULL,
    line         REAL,                        -- solo goles (1,5 / 3,5 / 4,5)
    prob         DOUBLE PRECISION NOT NULL CHECK (prob >= 0.80 AND prob <= 0.95),
    fair_price   REAL NOT NULL,               -- 1 / prob
    ref_price    REAL,                        -- mejor cuota de SOFT_BOOKS en el mismo snapshot
    ref_book     TEXT,
    odds_source  TEXT NOT NULL,               -- 'the_odds_api' | 'api_football'
    odds_as_of   TIMESTAMPTZ NOT NULL,        -- hora del precio de Pinnacle
    fit          JSONB,                       -- goles: lambdas, rho, línea y residuo del ajuste
    decided_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_alta_prob_decided ON alta_prob_picks(decided_at);

DROP TRIGGER IF EXISTS trg_alta_prob_immutable ON alta_prob_picks;
CREATE TRIGGER trg_alta_prob_immutable
    BEFORE UPDATE OR DELETE ON alta_prob_picks
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

CREATE TABLE IF NOT EXISTS alta_prob_results (
    alta_id     UUID PRIMARY KEY REFERENCES alta_prob_picks(alta_id),
    outcome     TEXT NOT NULL CHECK (outcome IN ('win', 'loss')),
    home_goals  SMALLINT NOT NULL,
    away_goals  SMALLINT NOT NULL,
    settled_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_alta_prob_results_immutable ON alta_prob_results;
CREATE TRIGGER trg_alta_prob_results_immutable
    BEFORE UPDATE OR DELETE ON alta_prob_results
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

COMMIT;
```

- [ ] **Step 4: Añadir la configuración en `src/qf/config.py`** (justo después de `publish_picks_enabled`)

```python
    # --- Línea de alta probabilidad (publish/alta_prob.py, 2026-10-05) ---
    # Pronósticos ≥ 80 % de Pinnacle sin margen, aparte de los picks de valor.
    # Apagada hasta desplegar y verificar el primer lote sellado.
    alta_prob_enabled: bool = os.getenv("ALTA_PROB_ENABLED", "0") in ("1", "true", "True")
    # Fecha (AAAA-MM-DD) desde la que el control de calidad mide. Reanudar
    # tras una pausa es decisión del usuario: se mueve esta fecha.
    alta_prob_control_desde: str = os.getenv("ALTA_PROB_CONTROL_DESDE", "")
```

Si existe `.env.example`, añadir:

```
# Línea de alta probabilidad (0 = apagada)
ALTA_PROB_ENABLED=0
# ALTA_PROB_CONTROL_DESDE=2026-10-06
```

- [ ] **Step 5: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_esquema.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add db/040_alta_probabilidad.sql src/qf/config.py tests/test_alta_prob_esquema.py
git add .env.example 2>/dev/null || true
git commit -m "Alta probabilidad: tablas inmutables (db/040) e interruptor

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Control de calidad e historial (puros)

**Files:**
- Modify: `src/qf/publish/alta_prob.py` (añadir al final)
- Test: `tests/test_alta_prob_control.py` (nuevo)

**Interfaces:**
- Consumes: `soft_vs_sharp._weekly_ci(values, weeks) -> list[float] | None`, `soft_vs_sharp.MIN_WEEKS`.
- Produces:
  - `control(liquidados: list[dict], min_n: int = MIN_N_CONTROL) -> {"bloqueados": list[str], "motivos": list[str]}`; filas `{"market","prob","outcome","kickoff_utc"}`; `"todo"` en `bloqueados` = toda la línea.
  - `historial(liquidados: list[dict]) -> dict` con `n, aciertos, acierto_prometido, acierto_real` (en %), `diferencia_ic95` (puntos, `[lo, hi]` o `None`), `por_mercado`, `por_mes`, `rendimiento_ref {"n","roi"}`; filas además con `ref_price`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
"""Control de calidad e historial de la línea de alta probabilidad."""
from datetime import datetime, timedelta, timezone

import pytest

from qf.publish import alta_prob as ap

T0 = datetime(2026, 1, 5, 20, 0, tzinfo=timezone.utc)


def _filas(n, prob, tasa, market="double_chance", semanas=10, ref=None):
    aciertos = round(n * tasa)
    return [{"market": market, "prob": prob, "ref_price": ref,
             "outcome": "win" if i < aciertos else "loss",
             "kickoff_utc": T0 + timedelta(weeks=i % semanas)}
            for i in range(n)]


def test_sin_muestra_no_bloquea():
    assert ap.control([])["bloqueados"] == []
    assert ap.control(_filas(40, 0.87, 0.5))["bloqueados"] == []


def test_promete_de_mas_bloquea_todo_y_su_mercado():
    out = ap.control(_filas(120, 0.87, 0.60))
    assert "todo" in out["bloqueados"] and "double_chance" in out["bloqueados"]


def test_cumpliendo_no_bloquea():
    assert ap.control(_filas(300, 0.87, 0.87))["bloqueados"] == []


def test_solo_el_mercado_que_falla():
    # Medido: conjunto IC95 [−0,6; +1,2] pts (no bloquea), goles [−36; −26].
    filas = _filas(400, 0.87, 0.92) + _filas(60, 0.86, 0.55, market="totals")
    out = ap.control(filas)
    assert out["bloqueados"] == ["totals"]


def test_sin_ocho_semanas_no_hay_intervalo_ni_bloqueo():
    out = ap.control(_filas(120, 0.87, 0.40, semanas=3))
    assert out["bloqueados"] == []
    assert any("semanas" in m for m in out["motivos"])


def test_historial():
    filas = _filas(20, 0.85, 0.90, ref=1.20) + _filas(10, 0.90, 0.80, market="h2h")
    h = ap.historial(filas)
    assert h["n"] == 30 and h["aciertos"] == 26
    assert h["acierto_prometido"] == pytest.approx(86.7, abs=0.05)
    assert h["acierto_real"] == pytest.approx(86.7, abs=0.05)
    assert h["por_mercado"]["h2h"]["n"] == 10
    assert h["rendimiento_ref"]["n"] == 20
    assert h["rendimiento_ref"]["roi"] == pytest.approx((18 * 0.2 - 2) / 20 * 100)
    assert h["diferencia_ic95"] is not None


def test_historial_vacio():
    h = ap.historial([])
    assert h["n"] == 0 and h["acierto_real"] is None and h["por_mercado"] == {}
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_control.py`
Expected: FAIL con `AttributeError: module 'qf.publish.alta_prob' has no attribute 'control'`.

- [ ] **Step 3: Implementar al final de `src/qf/publish/alta_prob.py`**

Añadir a los imports del módulo:

```python
import numpy as np
import pandas as pd

from ..eval.soft_vs_sharp import MIN_WEEKS, _weekly_ci
```

y al final:

```python
# --------------------------------------------------------------------------
# Control de calidad e historial
# --------------------------------------------------------------------------

def _marco(liquidados: list[dict]) -> pd.DataFrame:
    f = pd.DataFrame(liquidados)
    f["prob"] = f["prob"].astype(float)
    f["won"] = f["outcome"] == "win"
    f["diff"] = f["won"].astype(float) - f["prob"]
    ko = pd.to_datetime(f["kickoff_utc"], utc=True).dt.tz_convert(None)
    f["week"] = ko.dt.to_period("W").astype(str)
    f["mes"] = ko.dt.strftime("%Y-%m")
    return f


def control(liquidados: list[dict], min_n: int = MIN_N_CONTROL) -> dict:
    """
    ¿Promete de más? En conjunto ("todo") y por mercado: con n ≥ min_n y el
    IC95 de (acertado − prob) entero bajo cero, se bloquea. El IC remuestrea
    semanas enteras, como la puerta de valor; sin MIN_WEEKS semanas no hay IC
    y no se bloquea (se informa).
    """
    if not liquidados:
        return {"bloqueados": [], "motivos": ["Sin pronósticos liquidados todavía"]}
    f = _marco(liquidados)
    bloqueados, motivos = [], []
    for nombre, g in [("todo", f), *f.groupby("market")]:
        if len(g) < min_n:
            motivos.append(f"{nombre}: muestra insuficiente ({len(g)} < {min_n})")
            continue
        ic = _weekly_ci(g["diff"].to_numpy(float), g["week"].to_numpy())
        if ic is None:
            motivos.append(f"{nombre}: muestra insuficiente (menos de {MIN_WEEKS} semanas)")
            continue
        if ic[1] < 0:
            bloqueados.append(str(nombre))
            motivos.append(f"{nombre}: acierto real por debajo del prometido "
                           f"(IC95 {ic[0] * 100:+.1f} a {ic[1] * 100:+.1f} puntos)")
    return {"bloqueados": bloqueados, "motivos": motivos}


def _bloque(g: pd.DataFrame) -> dict:
    return {"n": int(len(g)), "aciertos": int(g["won"].sum()),
            "acierto_prometido": round(float(g["prob"].mean()) * 100, 1),
            "acierto_real": round(float(g["won"].mean()) * 100, 1)}


def historial(liquidados: list[dict]) -> dict:
    """Lo prometido frente a lo ocurrido, entero y sin filtrar. En %."""
    if not liquidados:
        return {"n": 0, "aciertos": 0, "acierto_prometido": None, "acierto_real": None,
                "diferencia_ic95": None, "por_mercado": {}, "por_mes": [],
                "rendimiento_ref": {"n": 0, "roi": None}}
    f = _marco(liquidados)
    ic = _weekly_ci(f["diff"].to_numpy(float), f["week"].to_numpy())
    con_ref = f[f["ref_price"].notna()] if "ref_price" in f else f.iloc[0:0]
    roi = (np.where(con_ref["won"], con_ref["ref_price"].astype(float) - 1.0, -1.0).mean() * 100
           if len(con_ref) else None)
    return {**_bloque(f),
            "diferencia_ic95": None if ic is None else [round(ic[0] * 100, 1), round(ic[1] * 100, 1)],
            "por_mercado": {str(k): _bloque(g) for k, g in f.groupby("market")},
            "por_mes": [{"mes": k, **_bloque(g)}
                        for k, g in sorted(f.groupby("mes"), key=lambda kg: kg[0], reverse=True)],
            "rendimiento_ref": {"n": int(len(con_ref)),
                                "roi": None if roi is None else round(float(roi), 2)}}
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_control.py tests/test_alta_prob_reglas.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/qf/publish/alta_prob.py tests/test_alta_prob_control.py
git commit -m "Alta probabilidad: control de calidad e historial prometido/real

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: E/S de la línea (`publish/alta_prob_datos.py`)

**Files:**
- Create: `src/qf/publish/alta_prob_datos.py`
- Test: `tests/test_alta_prob_datos.py` (nuevo)

**Interfaces:**
- Consumes: Tasks 2 y 5 (`alta_prob`), `picks.Snapshot/_odds_api_snapshot/_af_snapshot/canonical_book/MIN_LEAD`, `devig`, `two_way_devig`, `clv._settle_outcome`, tablas de Task 4.
- Produces:
  - `linea_pinnacle(rows: list[dict]) -> tuple[float, float] | None` — `(línea, p_over justa)`; medio gol primero, si no la más cercana a 2,5.
  - `decidir(snap: picks.Snapshot, totales: list[dict], rho: float | None, habilitados: tuple, excluir: set[str]) -> tuple[alta_prob.Candidato, dict | None] | None`.
  - `estado() -> {"estado": "activa"|"pausada"|"desactivada", "bloqueados": list[str], "motivos": list[str]}`.
  - `select_and_persist(now: datetime | None = None, dry_run: bool = False) -> dict` → `{"elegidos": int, "sin_precio": int, "sin_candidato": int, "estado": str, "motivos": list[str], "decisiones": list[dict]}` (`decisiones` solo con `dry_run`).
  - `settle_pending() -> {"settled": int}`.
  - `informe_publico() -> {"estado","motivos","proximos","historial"}`.
  - CLI: `python -m qf.publish.alta_prob_datos preview|settle|informe`.

- [ ] **Step 1: Escribir los tests que fallan** (`tests/test_alta_prob_datos.py`)

```python
"""E/S de la línea de alta probabilidad, con la base de datos simulada."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from qf.config import settings
from qf.publish import alta_prob as ap
from qf.publish import alta_prob_datos as ad
from qf.publish import picks as pk

NOW = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)


def _snap(pin, otros=None, source="the_odds_api", edad=timedelta(hours=1)):
    books = {"pinnacle": dict(zip(("home", "draw", "away"), pin))}
    books.update(otros or {})
    return pk.Snapshot(source, NOW - edad, books)


def test_linea_pinnacle_prefiere_medio_gol():
    rows = [{"bookmaker": "pinnacle", "selection": s, "line": l, "price": p}
            for l, s, p in [(2.75, "over", 1.9), (2.75, "under", 1.95),
                            (3.5, "over", 2.6), (3.5, "under", 1.5)]]
    linea, p_over = ad.linea_pinnacle(rows)
    assert linea == 3.5 and 0.3 < p_over < 0.45


def test_linea_pinnacle_acepta_cuarto_si_no_hay_otra():
    rows = [{"bookmaker": "pinnacle", "selection": "over", "line": 2.75, "price": 1.9},
            {"bookmaker": "pinnacle", "selection": "under", "line": 2.75, "price": 1.95},
            {"bookmaker": "bet365", "selection": "over", "line": 2.5, "price": 1.8}]
    assert ad.linea_pinnacle(rows)[0] == 2.75
    assert ad.linea_pinnacle([]) is None


def test_decidir_favorito_claro():
    # Pinnacle 1,18 / 7,5 / 15 (Shin): local 0,826, 12 0,880, 1X 0,946 → el 1X2.
    out = ad.decidir(_snap((1.18, 7.5, 15.0)), [], None, (), set())
    assert out is not None
    c, ajuste = out
    assert (c.market, c.selection) == ("h2h", "home") and 0.80 <= c.prob <= 0.95
    assert ajuste is None


def test_decidir_partido_igualado_no_da_nada():
    assert ad.decidir(_snap((2.6, 3.2, 2.9)), [], None, (), set()) is None


def test_decidir_respeta_bloqueo():
    c, _ = ad.decidir(_snap((1.18, 7.5, 15.0)), [], None, (), {"h2h"})
    assert (c.market, c.selection) == ("double_chance", "12")


def _db(monkeypatch, partidos, snap, batch_sellado=False, rho=-0.06):
    inserts = []
    monkeypatch.setattr(ad, "settings", replace(settings, alta_prob_enabled=True))
    monkeypatch.setattr(ad, "_liquidados", lambda *a, **k: [])
    monkeypatch.setattr(ad, "_rho_activo", lambda: rho)
    monkeypatch.setattr(ad, "_lote_sellado", lambda dia: batch_sellado)
    monkeypatch.setattr(ad, "_partidos", lambda now: partidos)
    monkeypatch.setattr(ad, "_totales", lambda match_id, as_of: [])
    monkeypatch.setattr(ad.pk, "_odds_api_snapshot", lambda m, now: snap)
    monkeypatch.setattr(ad.pk, "_af_snapshot", lambda m, now: None)
    monkeypatch.setattr(ad, "execute", lambda sql, params=(): inserts.append(params) or 1)
    return inserts


def test_guarda_uno_con_su_cuota_de_referencia(monkeypatch):
    snap = _snap((1.18, 7.5, 15.0), {"bet365": {"home": 1.15, "draw": 7.0, "away": 13.0},
                                     "william_hill": {"home": 1.16, "draw": 7.0, "away": 12.0}})
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}], snap)
    out = ad.select_and_persist(NOW)
    assert out["elegidos"] == 1 and len(inserts) == 1
    p = inserts[0]
    assert p[0] == "m1" and p[1] == "h2h" and p[2] == "home"
    assert p[6] == 1.16 and p[7] == "william_hill"      # mejor de SOFT_BOOKS
    assert p[8] == "the_odds_api"


def test_dry_run_no_guarda(monkeypatch):
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}],
                  _snap((1.18, 7.5, 15.0)))
    out = ad.select_and_persist(NOW, dry_run=True)
    assert inserts == [] and out["decisiones"][0]["market"] == "h2h"


def test_precio_viejo_o_tardio_no_cuenta(monkeypatch):
    viejo = _snap((1.18, 7.5, 15.0), edad=timedelta(hours=7))
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}], viejo)
    assert ad.select_and_persist(NOW)["sin_precio"] == 1 and inserts == []
    tardio = _snap((1.18, 7.5, 15.0), edad=timedelta(minutes=1))
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(minutes=10)}], tardio)
    assert ad.select_and_persist(NOW)["sin_precio"] == 1 and inserts == []


def test_lote_ya_sellado_no_elige(monkeypatch):
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}],
                  _snap((1.18, 7.5, 15.0)), batch_sellado=True)
    out = ad.select_and_persist(NOW)
    assert out["elegidos"] == 0 and inserts == []


def test_apagada_no_hace_nada(monkeypatch):
    inserts = _db(monkeypatch, [{"match_id": "m1", "kickoff_utc": NOW + timedelta(hours=10)}],
                  _snap((1.18, 7.5, 15.0)))
    monkeypatch.setattr(ad, "settings", replace(settings, alta_prob_enabled=False))
    assert ad.select_and_persist(NOW)["estado"] == "desactivada" and inserts == []


def test_liquidacion(monkeypatch):
    monkeypatch.setattr(ad, "query", lambda sql, params=(): [
        {"alta_id": "a1", "market": "double_chance", "selection": "1X", "line": None,
         "home_goals": 1, "away_goals": 1},
        {"alta_id": "a2", "market": "totals", "selection": "over", "line": 1.5,
         "home_goals": 1, "away_goals": 0}])
    escritos = []
    monkeypatch.setattr(ad, "execute", lambda sql, params=(): escritos.append(params) or 1)
    assert ad.settle_pending() == {"settled": 2}
    assert [e[1] for e in escritos] == ["win", "loss"]


def test_informe_solo_sellados_y_con_texto(monkeypatch):
    sqls = []

    def q(sql, params=()):
        sqls.append(sql)
        if "m.kickoff_utc > now()" in sql:
            return [{"match_id": "m1", "league_id": "br.serie_a", "kickoff_utc": NOW,
                     "local": "Cruzeiro", "visitante": "Sao Paulo", "market": "double_chance",
                     "selection": "1X", "line": None, "prob": 0.87, "fair_price": 1.149,
                     "ref_price": None, "ref_book": None, "batch_date": "2026-10-06",
                     "chain_sha256": "ab" * 32}]
        return []
    monkeypatch.setattr(ad, "query", q)
    monkeypatch.setattr(ad, "settings", replace(settings, alta_prob_enabled=True))
    out = ad.informe_publico()
    assert out["estado"] == "activa"
    assert out["proximos"][0]["texto"] == "Cruzeiro o empate"
    assert all("a.decided_at <= b.created_at" in s for s in sqls if "alta_prob_picks a" in s)
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_datos.py`
Expected: FAIL con `ImportError`.

- [ ] **Step 3: Implementar `src/qf/publish/alta_prob_datos.py`**

```python
"""
Base de datos de la línea de alta probabilidad: elegir y guardar, liquidar e
informar. Las reglas están en `alta_prob.py`.

ORDEN: `daily.run()` llama a `select_and_persist()` justo ANTES de `seal()`, y
`hashchain._collect` mete las filas del día en el lote. Un pronóstico solo se
enseña si su lote existe y se selló DESPUÉS de decidirlo
(`decided_at <= created_at`): lo que no está en un lote sellado no existe.
Por eso, si el lote del día ya está sellado (job relanzado a mano), no se
elige nada: quedaría fuera de la cadena para siempre.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timezone

from ..config import settings
from ..db import execute, query, query_one
from ..eval.clv import _settle_outcome
from ..model.devig import devig, two_way_devig
from . import alta_prob as ap
from . import picks as pk

log = logging.getLogger(__name__)

SEL = ("home", "draw", "away")
_MEDIO_GOL = (2.5, 3.5)

_SQL_SELLADO = """JOIN prediction_batches b
             ON b.batch_date = (a.decided_at AT TIME ZONE 'UTC')::date
            AND a.decided_at <= b.created_at"""


# --------------------------------------------------------------------------
# Lecturas
# --------------------------------------------------------------------------

def _rho_activo() -> float | None:
    row = query_one("SELECT (params->>'rho')::float AS rho FROM model_artifacts "
                    "WHERE is_active LIMIT 1")
    return None if not row or row["rho"] is None else float(row["rho"])


def _lote_sellado(dia: date) -> bool:
    return query_one("SELECT 1 AS x FROM prediction_batches WHERE batch_date = %s",
                     (dia,)) is not None


def _partidos(now: datetime) -> list[dict]:
    return query(
        """SELECT m.match_id, m.kickoff_utc
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           LEFT JOIN alta_prob_picks a ON a.match_id = m.match_id
           WHERE m.status = 'scheduled' AND l.active AND a.match_id IS NULL
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (now + pk.MIN_LEAD, now + ap.HORIZONTE))


def _totales(match_id: str, as_of: datetime) -> list[dict]:
    """Totales de la MISMA respuesta de The Odds API que el 1X2."""
    return query(
        """SELECT bookmaker, selection, line, price FROM odds_snapshots
           WHERE match_id = %s AND market = 'totals' AND source = 'the_odds_api'
             AND captured_at = %s""",
        (match_id, as_of))


def _liquidados(desde: str | None = "control") -> list[dict]:
    """
    Liquidados y sellados. Por defecto, desde ALTA_PROB_CONTROL_DESDE (lo que
    mide el control); con `None`, todos (el historial público nunca se recorta).
    """
    if desde == "control":
        desde = settings.alta_prob_control_desde or None
    return query(
        f"""SELECT a.market, a.prob, a.ref_price, r.outcome, m.kickoff_utc
            FROM alta_prob_picks a
            JOIN alta_prob_results r ON r.alta_id = a.alta_id
            JOIN matches m ON m.match_id = a.match_id
            {_SQL_SELLADO}
            WHERE %s::date IS NULL OR a.decided_at >= %s::date""",
        (desde, desde))


# --------------------------------------------------------------------------
# Decisión
# --------------------------------------------------------------------------

def _snapshot(match_id: str, kickoff: datetime, now: datetime) -> pk.Snapshot | None:
    """Vigente y con el 1X2 de Pinnacle completo; The Odds API primero (trae goles)."""
    for snap in (pk._odds_api_snapshot(match_id, now), pk._af_snapshot(match_id, now)):
        if snap is None:
            continue
        if now - snap.as_of > ap.MAX_EDAD_PRECIO or kickoff - snap.as_of < pk.MIN_LEAD:
            continue
        q = snap.books.get(settings.sharp_book, {})
        if set(q) == set(SEL) and min(q.values()) > 1.0:
            return snap
    return None


def linea_pinnacle(rows: list[dict]) -> tuple[float, float] | None:
    por_linea: dict[float, dict[str, float]] = {}
    for r in rows:
        if r["line"] is None or pk.canonical_book(r["bookmaker"]) != settings.sharp_book:
            continue
        por_linea.setdefault(float(r["line"]), {})[r["selection"]] = float(r["price"])
    completas = {ln: q for ln, q in por_linea.items()
                 if set(q) == {"over", "under"} and min(q.values()) > 1.0}
    if not completas:
        return None
    ln = min(completas, key=lambda x: (x not in _MEDIO_GOL, abs(x - 2.5)))
    p_over, _ = two_way_devig(completas[ln]["over"], completas[ln]["under"],
                              settings.devig_method)
    return ln, p_over


def decidir(snap: pk.Snapshot, totales: list[dict], rho: float | None,
            habilitados: tuple, excluir: set[str]) -> tuple[ap.Candidato, dict | None] | None:
    q = snap.books[settings.sharp_book]
    fair = devig([q[s] for s in SEL], settings.devig_method)
    p = {s: float(fair[i]) for i, s in enumerate(SEL)}
    cands = ap.candidatos_1x2(p) + ap.candidatos_doble(p)
    ajuste = None
    if rho is not None and habilitados and "totals" not in excluir:
        linea = linea_pinnacle(totales)
        if linea is not None:
            ajuste = ap.ajuste_goles(p, linea[0], linea[1], rho)
            cands += ap.candidatos_goles(ajuste, habilitados)
    elegido = ap.elegir(cands, excluir)
    if elegido is None:
        return None
    return elegido, (ajuste if elegido.market == "totals" else None)


def _ref(snap: pk.Snapshot, totales: list[dict], c: ap.Candidato) -> tuple[float | None, str | None]:
    """Mejor cuota de las casas de los suscriptores en el mismo snapshot."""
    if c.market == "h2h":
        precios = [(q[c.selection], b) for b, q in snap.books.items()
                   if b in settings.soft_books and c.selection in q]
    elif c.market == "totals":
        precios = [(float(r["price"]), pk.canonical_book(r["bookmaker"])) for r in totales
                   if pk.canonical_book(r["bookmaker"]) in settings.soft_books
                   and r["selection"] == c.selection and r["line"] is not None
                   and float(r["line"]) == c.line]
    else:   # doble oportunidad: ningún proveedor capturado la cotiza
        precios = []
    return max(precios) if precios else (None, None)


# --------------------------------------------------------------------------
# Estado, elección, liquidación, informe
# --------------------------------------------------------------------------

def estado() -> dict:
    if not settings.alta_prob_enabled:
        return {"estado": "desactivada", "bloqueados": [], "motivos": ["Línea todavía no activada"]}
    ctl = ap.control(_liquidados())
    return {"estado": "pausada" if "todo" in ctl["bloqueados"] else "activa", **ctl}


def select_and_persist(now: datetime | None = None, dry_run: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    est = estado()
    out = {"elegidos": 0, "sin_precio": 0, "sin_candidato": 0,
           "estado": est["estado"], "motivos": est["motivos"], "decisiones": []}
    if est["estado"] != "activa":
        return out
    if not dry_run and _lote_sellado(now.date()):
        out["motivos"] = [*out["motivos"], "Lote del día ya sellado: no se elige nada"]
        return out
    excluir = set(est["bloqueados"])
    habilitados = ap.MERCADOS_GOLES_HABILITADOS
    rho = _rho_activo()
    for m in _partidos(now):
        snap = _snapshot(m["match_id"], m["kickoff_utc"], now)
        if snap is None:
            out["sin_precio"] += 1
            continue
        totales = _totales(m["match_id"], snap.as_of) if snap.source == "the_odds_api" else []
        res = decidir(snap, totales, rho, habilitados, excluir)
        if res is None:
            out["sin_candidato"] += 1
            continue
        c, ajuste = res
        ref_price, ref_book = _ref(snap, totales, c)
        fila = (m["match_id"], c.market, c.selection, c.line, round(c.prob, 6),
                round(1.0 / c.prob, 4), ref_price, ref_book, snap.source, snap.as_of,
                json.dumps(ajuste) if ajuste else None)
        if dry_run:
            out["decisiones"].append({"match_id": m["match_id"], "market": c.market,
                                      "selection": c.selection, "line": c.line,
                                      "prob": round(c.prob, 4), "ref_price": ref_price,
                                      "ref_book": ref_book, "odds_source": snap.source})
            continue
        out["elegidos"] += execute(
            """INSERT INTO alta_prob_picks
                 (match_id, market, selection, line, prob, fair_price,
                  ref_price, ref_book, odds_source, odds_as_of, fit)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id) DO NOTHING""", fila) or 0
    log.info("Alta probabilidad: %s", {k: v for k, v in out.items() if k != "decisiones"})
    return out


def settle_pending() -> dict:
    rows = query(
        """SELECT a.alta_id, a.market, a.selection, a.line, m.home_goals, m.away_goals
           FROM alta_prob_picks a
           JOIN matches m ON m.match_id = a.match_id
           LEFT JOIN alta_prob_results r ON r.alta_id = a.alta_id
           WHERE r.alta_id IS NULL AND m.status = 'finished'
             AND m.home_goals IS NOT NULL""")
    for r in rows:
        outcome, _, _ = _settle_outcome(r["market"], r["selection"], r["line"],
                                        int(r["home_goals"]), int(r["away_goals"]))
        execute(
            """INSERT INTO alta_prob_results (alta_id, outcome, home_goals, away_goals)
               VALUES (%s,%s,%s,%s) ON CONFLICT (alta_id) DO NOTHING""",
            (r["alta_id"], outcome, int(r["home_goals"]), int(r["away_goals"])))
    return {"settled": len(rows)}


def informe_publico() -> dict:
    est = estado()
    proximos = query(
        f"""SELECT a.match_id, m.league_id, m.kickoff_utc,
                   th.canonical_name AS local, ta.canonical_name AS visitante,
                   a.market, a.selection, a.line, a.prob, a.fair_price,
                   a.ref_price, a.ref_book, b.batch_date, b.chain_sha256
            FROM alta_prob_picks a
            JOIN matches m ON m.match_id = a.match_id
            JOIN teams th ON th.team_id = m.home_team_id
            JOIN teams ta ON ta.team_id = m.away_team_id
            {_SQL_SELLADO}
            WHERE m.kickoff_utc > now()
            ORDER BY m.kickoff_utc""")
    for p in proximos:
        p["texto"] = ap.texto(p["market"], p["selection"], p["line"], p["local"], p["visitante"])
    return {"estado": est["estado"], "motivos": est["motivos"],
            "proximos": proximos, "historial": ap.historial(_liquidados(None))}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Línea de alta probabilidad")
    a.add_argument("accion", choices=["preview", "settle", "informe"])
    accion = a.parse_args().accion
    out = {"preview": lambda: select_and_persist(dry_run=True),
           "settle": settle_pending, "informe": informe_publico}[accion]()
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_datos.py tests/test_alta_prob_control.py tests/test_alta_prob_reglas.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/qf/publish/alta_prob_datos.py tests/test_alta_prob_datos.py
git commit -m "Alta probabilidad: elegir y guardar, liquidar e informe público

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Sellado, job diario y liquidación encadenada

**Files:**
- Modify: `src/qf/publish/hashchain.py:59` (constante) y `_collect` (`:62-106`), `seal` (recibo, `:131-139`)
- Modify: `src/qf/publish/daily.py` (import, helper `_alta`, `run()` `:495-560`)
- Modify: `src/qf/eval/clv.py:232-250` (encadenar liquidación)
- Test: `tests/test_alta_prob_sellado.py` (nuevo)

**Interfaces:**
- Consumes: `alta_prob_datos.select_and_persist() -> dict`, `alta_prob_datos.settle_pending() -> dict` (Task 6).
- Produces: `hashchain.LOTE_ALTA_PROB_DESDE: date | None` (None = bloque desactivado); payload con `alta_probabilidad` y `n_alta_prob`; `daily.run()` devuelve además `"alta_prob": dict`; `clv.settle_pending()` devuelve además `"alta_prob": dict`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
"""La línea de alta probabilidad entra en el lote sellado y nunca rompe el job."""
from dataclasses import replace
from datetime import date

import pytest

from qf.config import settings
from qf.publish import daily, hashchain


def _collect(monkeypatch, dia, desde):
    sqls = []
    monkeypatch.setattr(hashchain, "LOTE_ALTA_PROB_DESDE", desde)
    monkeypatch.setattr(hashchain, "query",
                        lambda sql, params=None: sqls.append(sql) or
                        ([{"alta_id": "a1"}] if "alta_prob_picks" in sql else []))
    return hashchain._collect(dia), sqls


def test_sin_fecha_de_corte_no_hay_bloque(monkeypatch):
    payload, sqls = _collect(monkeypatch, date(2026, 10, 7), None)
    assert "alta_probabilidad" not in payload
    assert not any("alta_prob_picks" in s for s in sqls)


def test_lotes_anteriores_al_corte_no_cambian(monkeypatch):
    payload, _ = _collect(monkeypatch, date(2026, 10, 6), date(2026, 10, 7))
    assert "alta_probabilidad" not in payload


def test_desde_el_corte_va_el_bloque(monkeypatch):
    payload, sqls = _collect(monkeypatch, date(2026, 10, 7), date(2026, 10, 7))
    assert payload["alta_probabilidad"] == [{"alta_id": "a1"}]
    assert payload["n_alta_prob"] == 1


@pytest.fixture
def job(monkeypatch):
    orden = []
    monkeypatch.setattr(daily, "generate_predictions",
                        lambda: [{"match_id": "m1", "confidence_tier": "high", "teams": ("A", "B")}])
    monkeypatch.setattr(daily, "_sharp_only_upcoming", lambda hours=36: [])
    monkeypatch.setattr(daily, "seal", lambda: orden.append("seal") or {"chain_sha256": "ab" * 32})
    monkeypatch.setattr(daily.alta_prob_datos, "select_and_persist",
                        lambda: orden.append("alta") or {"elegidos": 2, "estado": "activa", "motivos": []})
    alerts = []
    monkeypatch.setattr(daily.tg, "alert", alerts.append)
    return orden, alerts


def test_alta_se_elige_antes_de_sellar(monkeypatch, job):
    orden, _ = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=True))
    out = daily.run()
    assert orden == ["alta", "seal"]
    assert out["alta_prob"]["elegidos"] == 2


def test_apagada_no_se_llama(monkeypatch, job):
    orden, _ = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=False))
    daily.run()
    assert orden == ["seal"]


def test_un_fallo_de_la_linea_no_impide_sellar(monkeypatch, job):
    orden, alerts = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=True))

    def roto():
        raise RuntimeError("snapshot corrupto")
    monkeypatch.setattr(daily.alta_prob_datos, "select_and_persist", roto)
    out = daily.run()
    assert orden == ["seal"] and out["sealed"] is True
    assert any("alta probabilidad" in a.lower() for a in alerts)


def test_elegidos_sin_sellar_avisan(monkeypatch, job):
    orden, alerts = job
    monkeypatch.setattr(daily, "settings", replace(settings, alta_prob_enabled=True))
    monkeypatch.setattr(daily, "seal", lambda: orden.append("seal") or {})
    daily.run()
    assert any("SIN SELLAR" in a for a in alerts)
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_sellado.py`
Expected: FAIL (`LOTE_ALTA_PROB_DESDE` no existe / `daily.alta_prob_datos` no existe).

- [ ] **Step 3: `hashchain.py`**

Tras `LOTE_SIN_CONSENSO_DESDE = date(2026, 10, 3)`:

```python
# Desde esta fecha el lote lleva la línea de alta probabilidad
# (publish/alta_prob.py). None = todavía no desplegada: los lotes no cambian.
# Se fija a la fecha del despliegue en ese mismo commit; los lotes anteriores
# se regeneran igual que se sellaron.
LOTE_ALTA_PROB_DESDE: date | None = None
```

En `_collect`, antes del `return`:

```python
    con_alta = LOTE_ALTA_PROB_DESDE is not None and batch_date >= LOTE_ALTA_PROB_DESDE
    alta = query(
        """SELECT alta_id, match_id, market, selection, line, prob, fair_price,
                  ref_price, ref_book, odds_source, odds_as_of, fit, decided_at
           FROM alta_prob_picks
           WHERE (decided_at AT TIME ZONE 'UTC')::date = %s
           ORDER BY decided_at, alta_id""",
        (batch_date,),
    ) if con_alta else []
```

y sustituir el `return {...}` por:

```python
    payload = {
        "batch_date": batch_date.isoformat(),
        "model_version": settings.model_version,
        "fs_version": settings.fs_version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_predictions": len(preds),
        "n_picks": len(picks),
        "predictions": preds,
        "picks": picks,
    }
    if con_alta:
        payload["n_alta_prob"] = len(alta)
        payload["alta_probabilidad"] = alta
    return payload
```

En `seal`, añadir al `receipt` (tras `"n_picks"`): `**({"n_alta_prob": payload["n_alta_prob"]} if "n_alta_prob" in payload else {}),`.

- [ ] **Step 4: `daily.py`**

Import junto a los demás de `publish`:

```python
from . import alta_prob_datos
```

Helper antes de `run()`:

```python
def _alta() -> dict:
    """
    Línea de alta probabilidad: se elige y guarda ANTES de sellar, para que el
    lote del día la incluya. Nunca rompe el job: un fallo aquí no puede dejar
    sin sellar las predicciones.
    """
    if not settings.alta_prob_enabled:
        return {"elegidos": 0, "estado": "desactivada"}
    try:
        out = alta_prob_datos.select_and_persist()
    except Exception as exc:  # noqa: BLE001
        log.exception("Fallo en la línea de alta probabilidad")
        tg.alert(f"Fallo en la línea de alta probabilidad: {exc}")
        return {"elegidos": 0, "error": str(exc)}
    if out.get("estado") == "pausada" or any("por debajo" in m for m in out.get("motivos", [])):
        tg.alert("ALTA PROBABILIDAD: " + "; ".join(out.get("motivos", [])))
    return out


def _alerta_sin_sellar(alta: dict, receipt: dict) -> None:
    if not receipt and alta.get("elegidos"):
        tg.alert(f"{alta['elegidos']} pronósticos de alta probabilidad SIN SELLAR: "
                 "no se mostrarán nunca.")
```

En `run()`, en la rama `if not gate_ok:` sustituir `receipt = seal()` por:

```python
        alta = _alta()
        receipt = seal()
        _alerta_sin_sellar(alta, receipt)
```

y añadir `"alta_prob": alta,` al dict `result` de esa rama. En la rama de publicación (tras `pk.persist(tiered)`), sustituir `receipt = seal()` por las mismas tres líneas; en el `return` de fallo de sellado añadir `"alta_prob": alta` y en el `result` final `"alta_prob": alta`.

- [ ] **Step 5: `clv.py`** — tras el bloque `sharp = settle_sharp()`:

```python
    try:
        from ..publish.alta_prob_datos import settle_pending as settle_alta
        alta = settle_alta()
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo liquidar la línea de alta probabilidad: %s", exc)
        alta = {"settled": 0, "error": str(exc)}
```

y añadir `"alta_prob": alta` al `result`.

- [ ] **Step 6: Ejecutar los tests nuevos y los afectados**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_sellado.py tests/test_publicacion_bloqueada.py tests/test_fugas_del_criterio.py tests/test_ligas_solo_sharp.py tests/test_picks_sin_prediccion.py`
Expected: PASS (los existentes no cambian: con `ALTA_PROB_ENABLED=0` `_alta()` no toca la base, y `_collect` no consulta `alta_prob_picks` con `LOTE_ALTA_PROB_DESDE=None`).

- [ ] **Step 7: Commit**

```bash
git add src/qf/publish/hashchain.py src/qf/publish/daily.py src/qf/eval/clv.py tests/test_alta_prob_sellado.py
git commit -m "Alta probabilidad: se elige antes de sellar y entra en el lote del día

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Endpoint público y tarjeta en `/control`

**Files:**
- Modify: `src/qf/api/main.py` (nuevo endpoint tras `/track-record`, ~línea 212)
- Modify: `src/qf/api/console.py` (`_snapshot`, nueva tarjeta)
- Test: `tests/test_alta_prob_api.py` (nuevo)

**Interfaces:**
- Consumes: `alta_prob_datos.informe_publico() -> dict` (Task 6).
- Produces: `GET /alta-probabilidad` (público, sin token) con `{"estado","motivos","proximos","historial"}`; `console._alta_card() -> dict` (sin `proximos`).

- [ ] **Step 1: Escribir los tests que fallan**

```python
"""/alta-probabilidad es público y no expone nada privado."""
from fastapi.testclient import TestClient

INFORME = {"estado": "activa", "motivos": [], "historial": {"n": 0},
           "proximos": [{"match_id": "m1", "texto": "Cruzeiro o empate", "prob": 0.87}]}


def _client(monkeypatch):
    from qf.api import main
    from qf.publish import alta_prob_datos
    monkeypatch.setattr(main.ratelimit, "rate_limited", lambda *_a: False)
    monkeypatch.setattr(alta_prob_datos, "informe_publico", lambda: INFORME)
    return TestClient(main.app)


def test_publico_sin_token(monkeypatch):
    r = _client(monkeypatch).get("/alta-probabilidad")
    assert r.status_code == 200
    assert r.json()["proximos"][0]["texto"] == "Cruzeiro o empate"


def test_tarjeta_del_panel_sin_lista(monkeypatch):
    from qf.api import console
    from qf.publish import alta_prob_datos
    monkeypatch.setattr(alta_prob_datos, "informe_publico", lambda: INFORME)
    card = console._alta_card()
    assert card["estado"] == "activa" and "proximos" not in card
    assert card["proximos_sellados"] == 1
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_api.py`
Expected: FAIL (404 en la ruta / `_alta_card` no existe).

- [ ] **Step 3: Endpoint en `src/qf/api/main.py`** (tras `track_record`)

```python
@publico.get("/alta-probabilidad")
def alta_probabilidad():
    """
    Línea de alta probabilidad: pronósticos sellados con probabilidad real
    (Pinnacle sin margen) entre el 80 y el 95 %, y su historial de acierto
    prometido frente a real, entero. Es una línea de acierto, no de valor.
    """
    from ..publish import alta_prob_datos
    return alta_prob_datos.informe_publico()
```

- [ ] **Step 4: Tarjeta en `src/qf/api/console.py`**

Función nueva (junto a `_commercial_gate`):

```python
def _alta_card() -> dict:
    """Estado de la línea de alta probabilidad: lo mismo que ve la web, sin la lista."""
    from ..publish import alta_prob_datos

    informe = alta_prob_datos.informe_publico()
    return {"estado": informe["estado"], "motivos": informe["motivos"],
            "proximos_sellados": len(informe["proximos"]),
            "historial": informe["historial"]}
```

y en `_snapshot()`, tras la tarjeta de la puerta comercial:

```python
        "Línea de alta probabilidad": _read(_alta_card),
```

- [ ] **Step 5: Ejecutar y ver que pasa, con los del panel**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_alta_prob_api.py tests/test_web_console.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/qf/api/main.py src/qf/api/console.py tests/test_alta_prob_api.py
git commit -m "Alta probabilidad: endpoint público y estado en /control

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Sección "Alta probabilidad" en la web

**Files:**
- Modify: `frontend/public-data.js` (`SOURCES`)
- Modify: `frontend/public-data.test.mjs` (`responses`, test nuevo)
- Modify: `frontend/app.js` (`nav`, `routeTitle`, `views`, helper `realTime`, función `altaView`)
- Modify: `frontend/styles.css` (al final)
- Modify: `frontend/index.html` y import de `app.js` (hashes `?v=`)

**Interfaces:**
- Consumes: `GET /alta-probabilidad` (Task 8); `probabilityLabel(p)` (ya en `public-data.js`).
- Produces: `publicData.alta = {status: 'ready'|'error', data}`; ruta `#alta`.

- [ ] **Step 1: Test que falla en `frontend/public-data.test.mjs`**

Añadir a `responses`:

```js
  '/alta-probabilidad': { estado: 'desactivada', motivos: ['Línea todavía no activada'], proximos: [], historial: { n: 0 } },
```

y al final:

```js
test('la línea de alta probabilidad se carga de su ruta pública', async () => {
  const data = await loadPublicData(async path => ({ ok: true, json: async () => responses[path] }));
  assert.equal(data.alta.status, 'ready');
  assert.equal(data.alta.data.estado, 'desactivada');
  const roto = await loadPublicData(async path => ({ ok: true, json: async () => (path === '/alta-probabilidad' ? { proximos: 'x' } : responses[path]) }));
  assert.equal(roto.alta.status, 'error');
});
```

Run: `cd frontend && node --test public-data.test.mjs`
Expected: FAIL (`data.alta` undefined y el primer test falla porque la ruta no se llama).

- [ ] **Step 2: Fuente en `frontend/public-data.js`** (dentro de `SOURCES`)

```js
  alta: ['/alta-probabilidad', value => value && Array.isArray(value.proximos) && typeof value.historial === 'object' && typeof value.estado === 'string'],
```

Run: `cd frontend && node --test public-data.test.mjs`
Expected: PASS.

- [ ] **Step 3: Ruta y vista en `frontend/app.js`**

En `nav`, tras la entrada de `picks`:

```js
  { route: 'alta', label: 'Alta probabilidad', short: 'Alta prob.', icon: '◎', group: 'EXPLORAR' },
```

En `routeTitle` añadir `alta: 'Alta probabilidad',`. En `views` (dentro de `render`) añadir `alta: altaView,`.

Tras la definición de `realDate`:

```js
const realTime = value => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : timeLabel(date);
};
```

Tras `picksView()`:

```js
// Línea de alta probabilidad (diseño 2026-10-05). Solo datos reales de
// /alta-probabilidad: es una línea de acierto, no de valor, y se dice.
const ALTA_MERCADO = { h2h: 'Ganador (1X2)', double_chance: 'Doble oportunidad', totals: 'Goles' };
function altaView() {
  const head = `<div class="view-title"><div><p class="eyebrow">PRONÓSTICOS / ALTA PROBABILIDAD</p><h1>Alta probabilidad</h1><p class="lead">Un pronóstico por partido, solo si su probabilidad real (Pinnacle sin margen) está entre el 80% y el 95%. Cada uno se sella en la cadena antes del partido.</p></div>${badge('Datos del servidor', 'accent')}</div>`;
  const source = publicData?.alta;
  if (!source) return `${head}<section class="live-panel"><p>Consultando pronósticos de alta probabilidad…</p></section>`;
  if (source.status !== 'ready') return `${head}<section class="live-panel"><p>No se pudieron consultar los pronósticos. Inténtalo de nuevo más tarde.</p><button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>`;
  const { estado, motivos, proximos, historial: h } = source.data;
  const ic = Array.isArray(h.diferencia_ic95) ? h.diferencia_ic95 : null;
  const record = h.n ? `<div class="live-facts"><div><span>PROMETIDO</span><strong>${realNumber(h.acierto_prometido, 1)}%</strong><small>media de las probabilidades</small></div><div><span>REAL</span><strong>${realNumber(h.acierto_real, 1)}%</strong><small>${realNumber(h.aciertos)} de ${realNumber(h.n)} acertados</small></div><div><span>DIFERENCIA · IC95</span><strong>${ic ? `${realNumber(ic[0], 1)} a ${realNumber(ic[1], 1)}` : '—'}</strong><small>${ic ? 'puntos, real − prometido' : 'Sin intervalo todavía'}</small></div></div>` : '<p>Todavía no hay pronósticos liquidados.</p>';
  const byMarket = Object.entries(h.por_mercado ?? {});
  const marketTable = byMarket.length ? `<div class="table-wrap" tabindex="0" role="region" aria-label="Acierto por mercado"><table><thead><tr><th>Mercado</th><th>Pronósticos</th><th>Prometido</th><th>Real</th></tr></thead><tbody>${byMarket.map(([market, row]) => `<tr><td>${esc(ALTA_MERCADO[market] ?? market)}</td><td>${realNumber(row.n)}</td><td>${realNumber(row.acierto_prometido, 1)}%</td><td>${realNumber(row.acierto_real, 1)}%</td></tr>`).join('')}</tbody></table></div>` : '';
  const roi = h.rendimiento_ref?.n ? `<p class="live-reason">A la cuota de referencia de tu casa (${realNumber(h.rendimiento_ref.n)} pronósticos con cuota): rendimiento ${realPercent(h.rendimiento_ref.roi, 2)}.</p>` : '';
  const note = '<p class="live-reason">Es una línea de acierto, no de valor: por un resultado al 85% la casa paga tan poco que, a la larga, suele dejar poco o nada. Por eso se publican las dos cosas.</p>';
  const paused = estado !== 'activa' ? `<p class="live-reason">Línea ${estado === 'pausada' ? 'pausada' : 'desactivada'}: ${esc((motivos ?? []).join(' · ') || 'sin motivo informado')}</p>` : '';
  const cards = proximos.length ? `<div class="live-pick-list">${proximos.map(p => `<article class="live-pick alta-pick"><div><span>${esc(p.league_id ?? 'Liga')} · ${realDate(p.kickoff_utc)} ${esc(realTime(p.kickoff_utc))}</span><h3>${esc(p.texto ?? 'Pronóstico')}</h3><p>${esc(p.local ?? 'Local')} <small>vs</small> ${esc(p.visitante ?? 'Visitante')}</p><small class="live-prob">Probabilidad real: ${esc(probabilityLabel(p.prob)?.text ?? 'sin dato')}</small></div><div><span>Cuota justa</span><strong>${realNumber(p.fair_price, 2)}</strong><small>${p.ref_price ? `${esc(p.ref_book ?? 'Casa')} ${realNumber(p.ref_price, 2)}` : 'Sin cuota de referencia'}</small><small>Lote ${esc(p.batch_date ?? '—')} · ${esc(String(p.chain_sha256 ?? '').slice(0, 12))}</small></div></article>`).join('')}</div>` : '<p>No hay pronósticos de alta probabilidad para los próximos partidos. Si ningún resultado llega al 80%, no se fuerza uno.</p>';
  const badgeText = estado === 'activa' ? 'Activa' : estado === 'pausada' ? 'Pausada' : 'Desactivada';
  return `${head}
    <section class="live-panel" aria-label="Historial de alta probabilidad"><div class="live-head"><div><p class="eyebrow">HISTORIAL PÚBLICO · /ALTA-PROBABILIDAD</p><h2>Prometido frente a real</h2></div>${badge(badgeText, estado === 'activa' ? 'good' : 'muted')}</div>${record}${marketTable}${roi}${note}</section>
    <section class="live-panel" aria-label="Próximos pronósticos de alta probabilidad"><div class="live-head"><div><p class="eyebrow">PRÓXIMOS PARTIDOS</p><h2>Pronósticos sellados</h2></div></div>${paused}${cards}<button type="button" class="text-link" data-action="refresh-public">Actualizar ↻</button></section>`;
}
```

- [ ] **Step 4: Estilos al final de `frontend/styles.css`**

```css
.live-panel+.live-panel{margin-top:16px}
.live-pick.alta-pick h3{font-size:19px;letter-spacing:-.02em}
.live-pick.alta-pick>div:last-child small+small{margin-top:4px}
```

- [ ] **Step 5: Hashes de caché**

```bash
cd frontend
OLD_PD=$(grep -o "public-data.js?v=[0-9a-f]*" app.js | cut -d= -f2); NEW_PD=$(sha256sum public-data.js | cut -c1-12)
sed -i "s/public-data.js?v=$OLD_PD/public-data.js?v=$NEW_PD/" app.js
OLD_APP=$(grep -o "app.js?v=[0-9a-f]*" index.html | cut -d= -f2); NEW_APP=$(sha256sum app.js | cut -c1-12)
OLD_CSS=$(grep -o "styles.css?v=[0-9a-f]*" index.html | cut -d= -f2); NEW_CSS=$(sha256sum styles.css | cut -c1-12)
sed -i "s/app.js?v=$OLD_APP/app.js?v=$NEW_APP/; s/styles.css?v=$OLD_CSS/styles.css?v=$NEW_CSS/" index.html
grep -n "?v=" app.js index.html
npm run check
```

Expected: hashes nuevos impresos y `# fail 0`.

- [ ] **Step 6: Verificación en el navegador** (servidor `frontend-demo` de `.claude/launch.json`, puerto 5173)

1. `preview_start` con `name: "frontend-demo"`, abrir `#alta`: debe salir "No se pudieron consultar…" (el servidor de la demo no tiene la API; es lo esperado).
2. Simular el servidor con `javascript_tool` y pulsar "Actualizar":

```js
const fake = {
  '/model-card': { puerta_comercial: { autorizada: false, sombra_criterio_sharp: { autorizada: false }, publicacion_de_picks: 'pausada' } },
  '/picks/free?limit=20': [], '/track-record': { mensual: [], ultimos_30d: { n: 0 } },
  '/calibration': { runs: [] }, '/chain?limit=20': { lotes: [] },
  '/alta-probabilidad': { estado: 'activa', motivos: [], proximos: [
    { match_id: 'm1', league_id: 'br.serie_a', kickoff_utc: '2026-10-08T00:30:00Z', local: 'Cruzeiro', visitante: '<b>Sao Paulo</b>', market: 'double_chance', selection: '1X', line: null, texto: 'Cruzeiro o empate', prob: 0.87, fair_price: 1.149, ref_price: null, ref_book: null, batch_date: '2026-10-07', chain_sha256: 'ab'.repeat(32) }],
    historial: { n: 120, aciertos: 105, acierto_prometido: 86.9, acierto_real: 87.5, diferencia_ic95: [-4.1, 5.3], por_mercado: { double_chance: { n: 100, aciertos: 88, acierto_prometido: 87.2, acierto_real: 88.0 }, h2h: { n: 20, aciertos: 17, acierto_prometido: 84.0, acierto_real: 85.0 } }, por_mes: [], rendimiento_ref: { n: 20, roi: -2.1 } } },
};
window.fetch = async path => ({ ok: true, json: async () => fake[path] });
document.querySelector('[data-action="refresh-public"]').click();
await new Promise(r => setTimeout(r, 500));
document.querySelector('main').innerText
```

Expected: "Prometido 86,9% / Real 87,5%", tabla por mercado, tarjeta "Cruzeiro o empate · Probabilidad real: 87% · sale 9 de cada 10", y el nombre `<b>Sao Paulo</b>` escrito como texto.
3. `resize_window` preset `mobile`: `document.documentElement.scrollWidth <= window.innerWidth` debe ser `true`; captura de pantalla; volver a `desktop`.
4. `read_console_messages` con `onlyErrors`: solo los 404 de la API ausente en la demo.
5. `preview_stop`.

- [ ] **Step 7: Commit**

```bash
git add frontend/public-data.js frontend/public-data.test.mjs frontend/app.js frontend/styles.css frontend/index.html
git commit -m "Web: sección Alta probabilidad con historial prometido/real

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Despliegue, verificación, activación y documentación

Requiere la Tarea 0 cerrada. Cada paso que cambia producción se anuncia al usuario antes.

**Files:**
- Modify: `src/qf/publish/hashchain.py` (`LOTE_ALTA_PROB_DESDE`)
- Modify: `README.md`, `harness/tareas.md`, `harness/progreso.md`

- [ ] **Step 1: Suite completa y arnés**

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m pytest -p no:cacheprovider -q tests
cd frontend && npm run check && cd ..
./scripts/harness_check.sh
```

Expected: todo en verde.

- [ ] **Step 2: Fijar la fecha de corte del sellado = fecha UTC del primer job diario tras el despliegue**

Si se despliega antes de las 07:50 UTC, es hoy; si no, mañana. En `src/qf/publish/hashchain.py`:

```python
LOTE_ALTA_PROB_DESDE: date | None = date(2026, 10, DD)   # primer lote tras desplegar
```

Ajustar el test `test_sin_fecha_de_corte_no_hay_bloque` (sigue usando `monkeypatch` con `None`, no cambia) y commitear:

```bash
git add src/qf/publish/hashchain.py
git commit -m "Alta probabilidad: el lote lleva el bloque desde el primer día desplegado

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 3: Desplegar con la línea apagada** (fuera de :20-:30 y de 07:50-08:30 UTC)

```bash
ssh quantfut 'cd ~ && tar --exclude=quantfut/.git -czf respaldo_$(date +%Y%m%d)_alta_prob.tgz quantfut'
git archive --format=tar HEAD src frontend db scripts README.md harness | ssh quantfut 'cd ~/quantfut && tar -xf -'
ssh quantfut 'cd ~/quantfut && grep -q "^ALTA_PROB_ENABLED=" .env || echo "ALTA_PROB_ENABLED=0" >> .env'
ssh quantfut 'cd ~/quantfut && docker compose exec -T db sh -c "psql -v ON_ERROR_STOP=1 -U \$POSTGRES_USER -d \$POSTGRES_DB -f /docker-entrypoint-initdb.d/040_alta_probabilidad.sql"'
ssh quantfut 'cd ~/quantfut && docker compose build api worker && docker compose up -d api worker'
```

Expected: `CREATE TABLE`, `CREATE TRIGGER` ×2, `COMMIT`; contenedores `Up`.

- [ ] **Step 4: Comprobar el esquema en producción (transacción que se deshace; decisión del usuario 2026-10-06)**

Los tests de `db/040` solo miran el texto del SQL; la comprobación real es esta. Volver a aplicar la migración (debe ser idempotente) y, en una transacción que termina en `ROLLBACK`, probar bordes, unicidad e inmutabilidad. Cada caso usa un `SAVEPOINT` para que un error esperado no aborte el resto:

```bash
ssh quantfut 'cd ~/quantfut && docker compose exec -T db sh -c "psql -v ON_ERROR_STOP=1 -U \$POSTGRES_USER -d \$POSTGRES_DB -f /docker-entrypoint-initdb.d/040_alta_probabilidad.sql"'
ssh quantfut 'cd ~/quantfut && docker compose exec -T db sh -c "psql -U \$POSTGRES_USER -d \$POSTGRES_DB"' <<'SQL'
BEGIN;
CREATE TEMP TABLE m2 AS SELECT match_id FROM matches WHERE status = 'scheduled' ORDER BY match_id LIMIT 4;
-- 0,80 y 0,95 entran
INSERT INTO alta_prob_picks (match_id, market, selection, prob, fair_price, odds_source, odds_as_of)
  SELECT match_id, 'h2h', 'home', 0.80, 1.25, 'the_odds_api', now() FROM m2 ORDER BY match_id LIMIT 1;
INSERT INTO alta_prob_picks (match_id, market, selection, prob, fair_price, odds_source, odds_as_of)
  SELECT match_id, 'double_chance', '1X', 0.95, 1.053, 'the_odds_api', now() FROM m2 ORDER BY match_id OFFSET 1 LIMIT 1;
-- 0,79 y 0,96 se rechazan (CHECK)
SAVEPOINT a; INSERT INTO alta_prob_picks (match_id, market, selection, prob, fair_price, odds_source, odds_as_of)
  SELECT match_id, 'h2h', 'home', 0.79, 1.27, 'the_odds_api', now() FROM m2 ORDER BY match_id OFFSET 2 LIMIT 1; ROLLBACK TO a;
SAVEPOINT b; INSERT INTO alta_prob_picks (match_id, market, selection, prob, fair_price, odds_source, odds_as_of)
  SELECT match_id, 'h2h', 'home', 0.96, 1.04, 'the_odds_api', now() FROM m2 ORDER BY match_id OFFSET 3 LIMIT 1; ROLLBACK TO b;
-- mercado desconocido se rechaza
SAVEPOINT c; INSERT INTO alta_prob_picks (match_id, market, selection, prob, fair_price, odds_source, odds_as_of)
  SELECT match_id, 'btts', 'no', 0.85, 1.18, 'the_odds_api', now() FROM m2 ORDER BY match_id OFFSET 3 LIMIT 1; ROLLBACK TO c;
-- segundo pronóstico del mismo partido se rechaza (UNIQUE)
SAVEPOINT d; INSERT INTO alta_prob_picks (match_id, market, selection, prob, fair_price, odds_source, odds_as_of)
  SELECT match_id, 'double_chance', '1X', 0.90, 1.11, 'the_odds_api', now() FROM m2 ORDER BY match_id LIMIT 1; ROLLBACK TO d;
-- UPDATE y DELETE fallan en las dos tablas
SAVEPOINT e; UPDATE alta_prob_picks SET prob = 0.9; ROLLBACK TO e;
SAVEPOINT f; DELETE FROM alta_prob_picks; ROLLBACK TO f;
INSERT INTO alta_prob_results (alta_id, outcome, home_goals, away_goals) SELECT alta_id, 'win', 1, 0 FROM alta_prob_picks LIMIT 1;
SAVEPOINT g; UPDATE alta_prob_results SET outcome = 'loss'; ROLLBACK TO g;
SAVEPOINT h; DELETE FROM alta_prob_results; ROLLBACK TO h;
SELECT count(*) AS deben_ser_2 FROM alta_prob_picks;
ROLLBACK;
SELECT count(*) AS deben_ser_0 FROM alta_prob_picks;
SQL
```

Expected: la segunda aplicación solo da NOTICEs (`already exists, skipping`) y `COMMIT`; los dos primeros INSERT dan `INSERT 0 1`; los savepoints `a`, `b`, `c` fallan por CHECK, `d` por UNIQUE, `e`-`h` con `REGISTRO INMUTABLE`; `deben_ser_2` = 2 y, tras el ROLLBACK, `deben_ser_0` = 0.

- [ ] **Step 5: Vista previa sin guardar (con la línea encendida solo para este proceso)**

```bash
ssh quantfut 'cd ~/quantfut && docker compose exec -T -e ALTA_PROB_ENABLED=1 worker python -m qf.publish.alta_prob_datos preview' | head -60
```

Expected: `estado: activa`, contadores `sin_precio`/`sin_candidato` y una lista `decisiones` coherente (probabilidades entre 0,80 y 0,95; mayoría `double_chance`). Enseñar al usuario 5-10 decisiones con los nombres de los partidos (`informe` aún vacío) y pedir su visto bueno para activar.

- [ ] **Step 6: Esperar al job de las 08:00 UTC con la línea apagada y verificar el lote**

```bash
ssh quantfut 'cd ~/quantfut && docker compose exec -T worker tail -5 /var/log/daily.log'
ssh quantfut 'cd ~/quantfut && docker compose exec -T worker python -m qf.publish.hashchain verify'
ssh quantfut 'cd ~/quantfut && docker compose exec -T worker sh -c "ls -t \$(python -c \"from qf.config import settings; print(settings.chain_dir)\")/*.receipt.json | head -1 | xargs cat"'
```

Expected: el job selló (`sealed: true`), `verify` OK, y si la fecha es ≥ `LOTE_ALTA_PROB_DESDE`, el recibo lleva `"n_alta_prob":0`.

- [ ] **Step 7: Activar** (con el visto bueno del paso 5)

```bash
ssh quantfut 'cd ~/quantfut && sed -i "s/^ALTA_PROB_ENABLED=0$/ALTA_PROB_ENABLED=1/" .env && grep ^ALTA_PROB_ENABLED .env && docker compose up -d api worker'
```

Al día siguiente, tras las 08:00 UTC: repetir el paso 6 (ahora `n_alta_prob > 0`), comprobar `GET /alta-probabilidad` (lista sellada con `chain_sha256` igual al del recibo) y la web `https://api.pronosticosdeportivos.pro/#alta` en escritorio y móvil.

- [ ] **Step 8: Documentación**

- `README.md`: sección "Línea de alta probabilidad" (qué es, que es de acierto y no de valor con las cifras del diseño, fuente Pinnacle sin margen, regla del 80-95 % y el de menor probabilidad, sellado, control y su reanudación con `ALTA_PROB_CONTROL_DESDE`, endpoint `/alta-probabilidad`).
- `harness/tareas.md`: marcar las casillas de "Línea de alta probabilidad".
- `harness/progreso.md`: decisión clave (por qué Pinnacle y no el modelo; por qué el de menor probabilidad; por qué el ajuste con push; resultado de la prueba de goles y la firma; fecha de activación).

```bash
git add README.md harness/tareas.md harness/progreso.md
git commit -m "Alta probabilidad: activada y documentada

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
