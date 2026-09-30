# Fuerza por jugador — Fase B1: valores y comparación offline. Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Calcular el valor de cada jugador sin mirar el futuro, convertirlo en la señal "cuánto valor pierde el XI de hoy frente al habitual" y comparar fuera de muestra los brazos "XI con valor" y "XI con nota" contra el XI simple.

**Architecture:** `model/player_ratings.py` mantiene acumuladores con decaimiento temporal por jugador y por posición (lectura antes del partido, escritura después: punto en el tiempo por construcción) y construye las señales. El challenger de XI (`model/lineup_challenger.py`) se generaliza para aceptar cualquier lista de señales. `model/player_value.py` arma el conjunto (base walk-forward guardada por el entrenamiento + XI + estadísticas), entrena los tres brazos sobre las MISMAS filas y exige que "XI con valor" gane al XI simple. Se integra en `train.py` y tiene CLI para evaluar sin reentrenar. La sombra en vivo es la Fase B2, con plan propio, solo si B1 se valida.

**Tech Stack:** Python 3.12, pandas, numpy, scipy (`minimize` ya usado por el challenger), PostgreSQL, pytest.

**Spec:** `docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md`
**Ejecutar DESPUÉS** de la revisión del reentreno del 1-oct-2026 (decisión del usuario).

## Global Constraints

- Mensajes al usuario y comentarios nuevos en español.
- Punto en el tiempo: para un partido con inicio T solo cuentan estadísticas y alineaciones de partidos con inicio < T. Partidos con el mismo inicio no se ven entre sí.
- Vida media del decaimiento: `settings.decay_halflife_days` (180).
- Encogimiento: la media de la posición pesa como 450 minutos (5 partidos completos).
- Pesos de las estadísticas: estimados SOLO con el 70 % antiguo (los estima el propio ajuste de Poisson del challenger en su tramo de ajuste); el 30 % reciente nunca los toca.
- El once se toma de las alineaciones (`lineups` / `lineups_historicas`), NUNCA del campo `titular` de `estadisticas_jugador` (el proveedor marca hasta 16 titulares por lado).
- "XI con valor" solo se marca validado si pasa las exigencias de siempre (RPS, log-loss, ECE, ≥2 ligas) Y mejora RPS y log-loss del XI simple sobre las mismas filas.
- Más de 3 titulares sin historial en un lado → ese partido no tiene señal de valor.
- `lineups_historicas` sigue sin poder leerse desde `model/shadow.py`, `publish/daily.py`, `ingest/lineups.py` ni `publish/shadow_sharp.py` (test existente).
- Commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests -q`.

## Archivos

- Create: `src/qf/model/player_ratings.py` — acumulador y señales.
- Modify: `src/qf/model/lineup_challenger.py` — lista de señales configurable.
- Create: `src/qf/model/player_value.py` — conjunto, comparación, artefactos, CLI.
- Modify: `src/qf/model/train.py` — llamar a la comparación.
- Create: `tests/test_player_ratings.py`, `tests/test_player_value.py`.
- Modify: `harness/tareas.md`, `harness/progreso.md`, `README.md` (fila Fase 4).

---

### Task 1: Acumulador de valores por jugador

**Files:**
- Create: `src/qf/model/player_ratings.py`
- Test: `tests/test_player_ratings.py`

**Interfaces:**
- Produces: `OFENSIVAS`, `DEFENSIVAS`, `ESTADISTICAS` (tuplas de nombres de columna de `estadisticas_jugador`); `MINUTOS_PREVIA = 450.0`; `class Acumulador(vida_media_dias: float)` con `avanzar(t: pd.Timestamp) -> None`, `anadir(fila: dict) -> None` (claves `player_id, posicion, minutos, nota_proveedor` + `ESTADISTICAS`), `tasas(player_id: int, posicion: str | None) -> np.ndarray` (por 90, orden de `ESTADISTICAS`), `nota(player_id, posicion) -> float` (nan si no hay nada), `conocido(player_id) -> bool`.

- [ ] **Step 1: Test (falla)**

```python
"""
Valor por jugador (fuerza por jugador, Fase B1).

Lo que fijan: el decaimiento hace pesar más lo reciente; un jugador con pocos
minutos queda cerca de la media de su posición; el acumulador no ve lo que
todavía no se le ha añadido (punto en el tiempo).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model.player_ratings import ESTADISTICAS, MINUTOS_PREVIA, Acumulador

T0 = pd.Timestamp("2026-01-01", tz="UTC")


def _fila(pid, pos="F", minutos=90, tiros=0, nota=7.0):
    f = {e: 0 for e in ESTADISTICAS}
    f.update(player_id=pid, posicion=pos, minutos=minutos, tiros=tiros,
             nota_proveedor=nota)
    return f


def _i(nombre):
    return ESTADISTICAS.index(nombre)


def test_pocos_minutos_se_quedan_cerca_de_la_media_de_su_posicion():
    acc = Acumulador(180)
    acc.avanzar(T0)
    for pid in range(10):                        # delanteros "medios": 2 tiros/90
        acc.anadir(_fila(pid, tiros=2))
    acc.anadir(_fila(99, minutos=10, tiros=3))   # 3 tiros en 10 min = 27/90
    tasa = acc.tasas(99, "F")[_i("tiros")]      # misma hora: sin decaimiento
    esperado = (3 + MINUTOS_PREVIA * (23 / 910)) / (10 + MINUTOS_PREVIA) * 90
    assert abs(tasa - esperado) < 1e-6
    assert tasa < 3.0, "10 minutos no bastan para parecer un goleador"


def test_lo_reciente_pesa_mas():
    acc = Acumulador(180)
    acc.avanzar(T0)
    acc.anadir(_fila(1, tiros=0))
    acc.avanzar(T0 + pd.Timedelta(days=360))     # dos vidas medias
    acc.anadir(_fila(1, tiros=4))
    acc.avanzar(T0 + pd.Timedelta(days=361))
    # Sin decaimiento serían 4 tiros en 180 min = 2,0/90. Con el partido viejo
    # pesando 0,25: 4 / (90 + 22,5) · 90 ≈ 3,2.
    assert acc.tasas(1, "F")[_i("tiros")] > 2.5


def test_sin_historial_devuelve_la_media_de_su_posicion():
    acc = Acumulador(180)
    acc.avanzar(T0)
    acc.anadir(_fila(1, pos="G", tiros=0))
    acc.anadir(_fila(2, pos="F", tiros=2))
    acc.avanzar(T0 + pd.Timedelta(days=1))
    assert not acc.conocido(3)
    assert abs(acc.tasas(3, "F")[_i("tiros")] - 2.0) < 1e-9
    assert np.isnan(Acumulador(180).nota(5, "F"))


def test_no_ve_lo_que_no_se_le_ha_anadido():
    acc = Acumulador(180)
    acc.avanzar(T0)
    antes = acc.tasas(1, "F").copy()
    acc.avanzar(T0 + pd.Timedelta(days=7))
    assert np.array_equal(np.nan_to_num(antes), np.nan_to_num(acc.tasas(1, "F")))
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_player_ratings.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'qf.model.player_ratings'`

- [ ] **Step 3: Implementar**

```python
"""
Valor por jugador (fuerza por jugador, Fase B1).

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Tasas por 90 minutos de cada estadística, con decaimiento temporal y
encogidas hacia la media de la posición del jugador. Punto en el tiempo por
construcción: el llamador AVANZA el reloj al inicio de un partido, LEE los
valores y solo después AÑADE las estadísticas de ese partido.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

OFENSIVAS = ("tiros", "tiros_puerta", "pases_clave", "goles", "asistencias")
DEFENSIVAS = ("entradas", "intercepciones", "duelos_ganados", "paradas")
ESTADISTICAS = OFENSIVAS + DEFENSIVAS
MINUTOS_PREVIA = 450.0      # la media de la posición pesa como 5 partidos
POSICIONES = ("G", "D", "M", "F")
_N = len(ESTADISTICAS)
# Vector: [minutos, estadísticas..., minutos_con_nota, nota·minutos]


class Acumulador:
    def __init__(self, vida_media_dias: float = 180.0):
        self.h = float(vida_media_dias)
        self.t: pd.Timestamp | None = None
        self._jug: dict[int, tuple[pd.Timestamp, np.ndarray]] = {}
        self._pos = {p: np.zeros(_N + 3) for p in POSICIONES}
        self.posicion: dict[int, str] = {}

    def _factor(self, desde: pd.Timestamp) -> float:
        dias = (self.t - desde).total_seconds() / 86400.0
        return 0.5 ** (dias / self.h)

    def avanzar(self, t: pd.Timestamp) -> None:
        if self.t is not None and t > self.t:
            f = 0.5 ** ((t - self.t).total_seconds() / 86400.0 / self.h)
            for p in POSICIONES:
                self._pos[p] *= f
        if self.t is None or t > self.t:
            self.t = t

    def _vector(self, player_id: int) -> np.ndarray:
        if player_id not in self._jug:
            return np.zeros(_N + 3)
        desde, v = self._jug[player_id]
        return v * self._factor(desde)

    def anadir(self, fila: dict) -> None:
        pid = int(fila["player_id"])
        pos = fila.get("posicion") if fila.get("posicion") in POSICIONES else None
        pos = pos or self.posicion.get(pid) or "M"
        self.posicion[pid] = pos
        minutos = float(fila["minutos"] or 0)
        if minutos <= 0:
            return
        nota = fila.get("nota_proveedor")
        add = np.zeros(_N + 3)
        add[0] = minutos
        add[1:_N + 1] = [float(fila.get(e) or 0) for e in ESTADISTICAS]
        if nota is not None and not pd.isna(nota):
            add[_N + 1] = minutos
            add[_N + 2] = float(nota) * minutos
        self._jug[pid] = (self.t, self._vector(pid) + add)
        self._pos[pos] += add

    def conocido(self, player_id: int) -> bool:
        return self._vector(player_id)[0] > 0

    def _pos_de(self, player_id: int, posicion: str | None) -> str:
        if posicion in POSICIONES:
            return posicion
        return self.posicion.get(player_id, "M")

    def tasas(self, player_id: int, posicion: str | None) -> np.ndarray:
        """Por 90 minutos, en el orden de ESTADISTICAS."""
        v = self._vector(player_id)
        p = self._pos[self._pos_de(player_id, posicion)]
        previa = p[1:_N + 1] / p[0] if p[0] > 0 else np.zeros(_N)
        return (v[1:_N + 1] + MINUTOS_PREVIA * previa) / (v[0] + MINUTOS_PREVIA) * 90.0

    def nota(self, player_id: int, posicion: str | None) -> float:
        v = self._vector(player_id)
        p = self._pos[self._pos_de(player_id, posicion)]
        if p[_N + 1] <= 0 and v[_N + 1] <= 0:
            return float("nan")
        previa = p[_N + 2] / p[_N + 1] if p[_N + 1] > 0 else v[_N + 2] / v[_N + 1]
        return float((v[_N + 2] + MINUTOS_PREVIA * previa) / (v[_N + 1] + MINUTOS_PREVIA))
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_player_ratings.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/qf/model/player_ratings.py tests/test_player_ratings.py
git commit -m "Fuerza por jugador (B1.1): acumulador de valores por jugador" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Señales "XI de hoy contra XI habitual"

**Files:**
- Modify: `src/qf/model/player_ratings.py`
- Test: `tests/test_player_ratings.py`

**Interfaces:**
- Consumes: `Acumulador`, `ESTADISTICAS` (Task 1).
- Produces: `VALOR_FEATURES: list[str]` = `[f"{lado}_d_{e}" for lado in ("home","away") for e in ESTADISTICAS]`; `NOTA_FEATURES = ["home_d_nota", "away_d_nota"]`; `build_value_features(matches: pd.DataFrame, lineups: pd.DataFrame, stats: pd.DataFrame, vida_media_dias: float = 180.0, lookback: int = 5, max_desconocidos: int = 3) -> pd.DataFrame` con columnas `match_id` + `VALOR_FEATURES` + `NOTA_FEATURES`. `matches`: `match_id, kickoff_utc, home_team_id, away_team_id`; `lineups`: `match_id, side, starters` (lista de `{player_id, pos}`); `stats`: filas de `estadisticas_jugador`.

- [ ] **Step 1: Test (falla)**

Añadir a `tests/test_player_ratings.py`:

```python
from qf.model.player_ratings import NOTA_FEATURES, VALOR_FEATURES, build_value_features

XI = [{"player_id": i, "pos": "G" if i == 1 else "D" if i < 6 else "M" if i < 10 else "F"}
      for i in range(1, 12)]
RIVAL = [{"player_id": 100 + p["player_id"], "pos": p["pos"]} for p in XI]


def _temporada(n, ultimo_xi=None):
    """n partidos del equipo 1 (local) contra el 2; el 11 es el goleador."""
    matches, lineups, stats = [], [], []
    for k in range(n):
        mid, ko = f"m{k}", T0 + pd.Timedelta(days=7 * k)
        matches.append({"match_id": mid, "kickoff_utc": ko, "home_team_id": 1,
                        "away_team_id": 2})
        xi = ultimo_xi if (ultimo_xi is not None and k == n - 1) else XI
        lineups += [{"match_id": mid, "side": "home", "starters": xi},
                    {"match_id": mid, "side": "away", "starters": RIVAL}]
        for p in XI + RIVAL:
            f = _fila(p["player_id"], p["pos"], tiros=5 if p["player_id"] == 11 else 0)
            f["match_id"] = mid
            stats.append(f)
    return pd.DataFrame(matches), pd.DataFrame(lineups), pd.DataFrame(stats)


def test_con_el_xi_habitual_la_senal_es_cero():
    m, l, s = _temporada(6)
    f = build_value_features(m, l, s).set_index("match_id")
    assert set(f.index) == {"m3", "m4", "m5"}, "hacen falta 3 XI previos"
    assert np.allclose(f.loc["m5", VALOR_FEATURES].to_numpy(float), 0.0)


def test_sin_el_goleador_se_pierde_valor_ofensivo():
    sin_goleador = XI[:-1] + [{"player_id": 50, "pos": "F"}]
    m, l, s = _temporada(6, ultimo_xi=sin_goleador)
    f = build_value_features(m, l, s).set_index("match_id")
    assert f.loc["m5", "home_d_tiros"] < -1.0
    assert abs(f.loc["m5", "away_d_tiros"]) < 1e-9


def test_mas_de_3_desconocidos_no_da_senal():
    extranos = XI[:7] + [{"player_id": 900 + i, "pos": "F"} for i in range(4)]
    m, l, s = _temporada(6, ultimo_xi=extranos)
    assert "m5" not in set(build_value_features(m, l, s)["match_id"])


def test_partidos_posteriores_no_cambian_el_pasado():
    m, l, s = _temporada(5)
    corto = build_value_features(m, l, s).set_index("match_id")
    m2, l2, s2 = _temporada(8)
    largo = build_value_features(m2, l2, s2).set_index("match_id")
    cols = VALOR_FEATURES + NOTA_FEATURES
    pd.testing.assert_frame_equal(corto[cols], largo.loc[corto.index, cols])
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_player_ratings.py -q`
Expected: FAIL `ImportError: cannot import name 'NOTA_FEATURES'`

- [ ] **Step 3: Implementar**

Añadir al final de `src/qf/model/player_ratings.py`:

```python
from collections import defaultdict, deque

LADOS = ("home", "away")
VALOR_FEATURES = [f"{lado}_d_{e}" for lado in LADOS for e in ESTADISTICAS]
NOTA_FEATURES = ["home_d_nota", "away_d_nota"]


def _xi(starters) -> dict[int, str | None]:
    out = {}
    for p in starters or []:
        if p.get("player_id"):
            out[int(p["player_id"])] = (str(p.get("pos") or "").upper()[:1] or None)
    return out


def _habitual(historia: deque) -> dict[int, str | None]:
    """Los 11 más frecuentes en los últimos XI; a igualdad, el más reciente."""
    cuenta: dict[int, int] = defaultdict(int)
    ultimo: dict[int, int] = {}
    pos: dict[int, str | None] = {}
    for i, xi in enumerate(historia):
        for pid, p in xi.items():
            cuenta[pid] += 1
            ultimo[pid] = i
            pos[pid] = p or pos.get(pid)
    orden = sorted(cuenta, key=lambda pid: (-cuenta[pid], -ultimo[pid]))[:11]
    return {pid: pos[pid] for pid in orden}


def _suma(acc: Acumulador, xi: dict[int, str | None]) -> tuple[np.ndarray, float]:
    tasas = [acc.tasas(pid, pos) for pid, pos in xi.items()]
    notas = [acc.nota(pid, pos) for pid, pos in xi.items()]
    notas = [n for n in notas if not np.isnan(n)]
    return (np.sum(tasas, axis=0) if tasas else np.zeros(len(ESTADISTICAS)),
            float(np.mean(notas)) if notas else float("nan"))


def build_value_features(matches: pd.DataFrame, lineups: pd.DataFrame,
                         stats: pd.DataFrame, vida_media_dias: float = 180.0,
                         lookback: int = 5, max_desconocidos: int = 3) -> pd.DataFrame:
    """
    Por partido y lado: valor del XI de hoy menos el del XI habitual, por
    estadística, más la diferencia de nota media. Recorre el calendario en
    orden: LEE a la hora de inicio y AÑADE el partido después, así un
    partido nunca ve estadísticas ni alineaciones suyas ni posteriores.
    """
    cols = ["match_id", *VALOR_FEATURES, *NOTA_FEATURES]
    if matches.empty or lineups.empty:
        return pd.DataFrame(columns=cols)
    ms = matches.copy()
    ms["kickoff_utc"] = pd.to_datetime(ms["kickoff_utc"], utc=True)
    xi_de = {(r["match_id"], r["side"]): _xi(r["starters"]) for _, r in lineups.iterrows()}
    stats_de = ({mid: g.to_dict("records") for mid, g in stats.groupby("match_id")}
                if not stats.empty else {})
    historias: dict[object, deque] = defaultdict(lambda: deque(maxlen=lookback))
    acc = Acumulador(vida_media_dias)
    filas = []
    for ko, grupo in ms.sort_values(["kickoff_utc", "match_id"]).groupby("kickoff_utc", sort=True):
        acc.avanzar(ko)
        pendientes = []
        for _, m in grupo.iterrows():
            valores, completo = {"match_id": m["match_id"]}, True
            for lado in LADOS:
                hoy = xi_de.get((m["match_id"], lado))
                equipo = m[f"{lado}_team_id"]
                if not hoy:
                    completo = False
                    continue
                pendientes.append((equipo, hoy))
                historia = historias[equipo]
                if len(historia) < 3:
                    completo = False
                    continue
                if sum(not acc.conocido(pid) for pid in hoy) > max_desconocidos:
                    completo = False
                    continue
                t_hoy, n_hoy = _suma(acc, hoy)
                t_hab, n_hab = _suma(acc, _habitual(historia))
                for e, d in zip(ESTADISTICAS, t_hoy - t_hab):
                    valores[f"{lado}_d_{e}"] = float(d)
                valores[f"{lado}_d_nota"] = n_hoy - n_hab
            if completo:
                filas.append(valores)
        for equipo, hoy in pendientes:
            historias[equipo].append(hoy)
        for _, m in grupo.iterrows():
            for fila in stats_de.get(m["match_id"], []):
                acc.anadir(fila)
    return pd.DataFrame(filas, columns=cols)
```

Mover `from collections import defaultdict, deque` junto a las importaciones del principio del archivo.

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_player_ratings.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/qf/model/player_ratings.py tests/test_player_ratings.py
git commit -m "Fuerza por jugador (B1.2): señal XI de hoy contra XI habitual" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Challenger con lista de señales configurable

**Files:**
- Modify: `src/qf/model/lineup_challenger.py`
- Test: `tests/test_lineup_challenger.py`

**Interfaces:**
- Produces: `LineupParams.features: list[str]` (por defecto `LINEUP_FEATURES`); `fit_and_validate(frame, rho=0.0, shrink=0.5, holdout_frac=0.30, min_fit=500, min_val=200, l2=10.0, features: list[str] | None = None)`. Artefactos antiguos (sin `features`) siguen cargando con `LINEUP_FEATURES`.

- [ ] **Step 1: Test (falla)**

Añadir a `tests/test_lineup_challenger.py`:

```python
def test_un_artefacto_antiguo_carga_con_las_senales_de_siempre(tmp_path):
    import pickle

    from qf.model.lineup_challenger import LINEUP_FEATURES, LineupLambdaChallenger
    antiguo = {"medians": [0.0] * 14, "scales": [1.0] * 14, "beta_home": [0.0] * 15,
               "beta_away": [0.0] * 15, "rho": -0.05, "shrink": 0.5, "n_fit": 700,
               "offline_validated": True}
    ruta = tmp_path / "lineup_viejo.pkl"
    ruta.write_bytes(pickle.dumps(antiguo))
    assert LineupLambdaChallenger.load(str(ruta)).params.features == LINEUP_FEATURES


def test_fit_and_validate_usa_las_senales_que_se_le_pasan():
    import numpy as np

    from qf.model.lineup_challenger import fit_and_validate
    rng = np.random.default_rng(0)
    n = 800
    x = rng.normal(size=n)
    frame = pd.DataFrame({
        "match_id": [f"m{i}" for i in range(n)], "league_id": ["A", "B"] * (n // 2),
        "kickoff_utc": pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC"),
        "base_lam": 1.4, "base_mu": 1.1, "rho": -0.05, "home_d_tiros": x,
        "home_goals": rng.poisson(1.4 * np.exp(0.3 * x)), "away_goals": rng.poisson(1.1, n)})
    modelo, informe = fit_and_validate(frame, rho=-0.05, features=["home_d_tiros"])
    assert modelo.params.features == ["home_d_tiros"]
    assert modelo.params.beta_home[1] > 0
    assert informe["n_fit"] == 560
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_lineup_challenger.py -q`
Expected: FAIL (`AttributeError: 'LineupParams' object has no attribute 'features'` y `TypeError: fit_and_validate() got an unexpected keyword argument 'features'`)

- [ ] **Step 3: Implementar**

En `src/qf/model/lineup_challenger.py`:

1. Importación: `from dataclasses import dataclass, asdict, field`.
2. `LineupParams`: añadir como ÚLTIMO campo
```python
    features: list[str] = field(default_factory=lambda: list(LINEUP_FEATURES))
```
3. `_matrix`: `x = frame[self.params.features].to_numpy(dtype=float)`.
4. `fit_and_validate`: añadir el parámetro final `features: list[str] | None = None`; primera línea del cuerpo `features = list(features or LINEUP_FEATURES)`; sustituir `train[LINEUP_FEATURES]` por `train[features]`; construir los parámetros con `features=features`:
```python
    model = LineupLambdaChallenger(LineupParams(
        medians.tolist(), scales.tolist(), bh.tolist(), ba.tolist(), float(rho),
        float(shrink), int(cut), False, features))
```

- [ ] **Step 4: Ejecutar toda la suite**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests -q`
Expected: sin FAIL.

- [ ] **Step 5: Commit**

```bash
git add src/qf/model/lineup_challenger.py tests/test_lineup_challenger.py
git commit -m "Fuerza por jugador (B1.3): el challenger de XI acepta cualquier lista de señales" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Comparación de brazos y artefactos

**Files:**
- Create: `src/qf/model/player_value.py`
- Test: `tests/test_player_value.py`

**Interfaces:**
- Consumes: `build_value_features`, `VALOR_FEATURES`, `NOTA_FEATURES` (Task 2); `fit_and_validate(..., features=)` (Task 3); `lineup_challenger.load_training_frame(oos)` y `lineup_challenger._historical_lineups()` (existentes).
- Produces: `comparar(frame: pd.DataFrame, rho: float) -> tuple[dict, dict]` (informe, `{"simple"|"valor"|"nota": LineupLambdaChallenger | None}`); `evaluar(oos: pd.DataFrame, rho: float, version: str, carpeta: str | None = None) -> dict`.

- [ ] **Step 1: Test (falla)**

```python
"""
Comparación de brazos del XI (fuerza por jugador, Fase B1).

Lo que fijan: los tres brazos se ajustan y validan sobre las MISMAS filas, y
"XI con valor" solo queda validado si además gana al XI simple.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model.lineup_challenger import LINEUP_FEATURES
from qf.model.player_ratings import NOTA_FEATURES, VALOR_FEATURES


def _frame(senal_valor: float, n: int = 1000):
    rng = np.random.default_rng(1)
    d = pd.DataFrame({
        "match_id": [f"m{i}" for i in range(n)], "league_id": ["A", "B"] * (n // 2),
        "kickoff_utc": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
        "base_lam": 1.4, "base_mu": 1.1, "rho": -0.05})
    for c in LINEUP_FEATURES + VALOR_FEATURES + NOTA_FEATURES:
        d[c] = rng.normal(size=n)
    d["home_goals"] = rng.poisson(1.4 * np.exp(senal_valor * d["home_d_tiros"]))
    d["away_goals"] = rng.poisson(1.1, n)
    return d


def test_con_senal_real_el_valor_gana_y_queda_validado():
    from qf.model.player_value import comparar
    informe, modelos = comparar(_frame(0.4), rho=-0.05)
    assert informe["n_filas"] == 1000
    assert informe["valor"]["gana_al_simple"] is True
    assert modelos["valor"].params.offline_validated is True


def test_sin_senal_no_se_valida():
    from qf.model.player_value import comparar
    informe, modelos = comparar(_frame(0.0), rho=-0.05)
    assert informe["valor"]["gana_al_simple"] is False or not informe["valor"]["ok"]
    assert modelos["valor"] is None or modelos["valor"].params.offline_validated is False


def test_filas_incompletas_quedan_fuera_de_los_tres():
    from qf.model.player_value import comparar
    d = _frame(0.4)
    d.loc[:9, "home_d_tiros"] = np.nan
    informe, _ = comparar(d, rho=-0.05)
    assert informe["n_filas"] == 990
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_player_value.py -q`
Expected: FAIL `ModuleNotFoundError: No module named 'qf.model.player_value'`

- [ ] **Step 3: Implementar**

```python
"""
Fuerza por jugador, Fase B1: comparación offline de brazos del XI.

Diseño: docs/superpowers/specs/2026-09-29-fuerza-por-jugador-design.md.
Tres brazos sobre las MISMAS filas y la misma base (walk-forward guardado
por `train.py`): XI simple, XI con valor y XI con nota. "XI con valor" solo
se valida si pasa las exigencias de siempre Y mejora RPS y log-loss del XI
simple. La sombra en vivo es la Fase B2, con su propio plan.
"""
from __future__ import annotations

import glob
import json
import logging
import os

import pandas as pd

from ..config import settings
from ..db import query
from . import lineup_challenger as lc
from .player_ratings import NOTA_FEATURES, VALOR_FEATURES, build_value_features

log = logging.getLogger(__name__)


def comparar(frame: pd.DataFrame, rho: float) -> tuple[dict, dict]:
    comun = frame.dropna(subset=["base_lam", "base_mu", "home_goals", "away_goals",
                                 *lc.LINEUP_FEATURES, *VALOR_FEATURES]).copy()
    comun[NOTA_FEATURES] = comun[NOTA_FEATURES].astype(float)
    informe, modelos = {"n_filas": int(len(comun))}, {}
    for nombre, senales in (("simple", lc.LINEUP_FEATURES), ("valor", VALOR_FEATURES),
                            ("nota", NOTA_FEATURES)):
        modelo, rep = lc.fit_and_validate(comun, rho=rho, features=senales)
        informe[nombre], modelos[nombre] = rep, modelo
    s, v = informe["simple"], informe["valor"]
    gana = bool(v.get("ok") and "rps_after" in s
                and v["rps_after"] < s["rps_after"]
                and v["log_loss_after"] < s["log_loss_after"])
    informe["valor"]["gana_al_simple"] = gana
    if modelos["valor"] is not None:
        modelos["valor"].params.offline_validated = gana
    if modelos["nota"] is not None:
        # La nota del proveedor es solo comparación: nunca se valida.
        modelos["nota"].params.offline_validated = False
    return informe, modelos


def _conjunto(oos: pd.DataFrame) -> pd.DataFrame:
    base, _ = lc.load_training_frame(oos)
    if base.empty:
        return base
    matches = pd.DataFrame(query(
        """SELECT m.match_id, m.kickoff_utc, m.home_team_id, m.away_team_id
           FROM matches m JOIN leagues l USING (league_id)
           WHERE l.model_enabled AND m.status = 'finished'
             AND m.kickoff_utc > now() - interval '500 days'"""))
    vivos = pd.DataFrame(query(
        """SELECT DISTINCT ON (l.match_id, l.side) l.match_id, l.side, l.starters
           FROM lineups l JOIN matches m USING (match_id)
           WHERE l.captured_at <= m.kickoff_utc
           ORDER BY l.match_id, l.side, l.captured_at DESC"""))
    historicas = lc._historical_lineups()
    lineups = pd.concat([x for x in (vivos, historicas) if not x.empty], ignore_index=True)
    lineups = lineups.drop_duplicates(subset=["match_id", "side"], keep="first")
    stats = pd.DataFrame(query(
        "SELECT * FROM estadisticas_jugador WHERE minutos > 0"))
    valor = build_value_features(matches, lineups[["match_id", "side", "starters"]], stats,
                                 vida_media_dias=settings.decay_halflife_days)
    return base.merge(valor, on="match_id", how="inner")


def evaluar(oos: pd.DataFrame, rho: float, version: str,
            carpeta: str | None = None) -> dict:
    frame = _conjunto(oos)
    if frame.empty:
        return {"ok": False, "status": "collecting", "reason": "Sin filas con XI y valor"}
    informe, modelos = comparar(frame, rho)
    carpeta = carpeta or settings.artifact_dir
    for nombre, prefijo in (("valor", "lineup_valor"), ("nota", "lineup_nota")):
        if modelos.get(nombre) is not None:
            modelos[nombre].save(f"{carpeta}/{prefijo}_{version}.pkl")
    return informe


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ruta = max(glob.glob(f"{settings.artifact_dir}/oos_*.pkl"), key=os.path.getmtime)
    version = os.path.basename(ruta)[len("oos_"):-len(".pkl")]
    oos = pd.read_pickle(ruta)
    rho = float(oos["rho"].median())
    print(json.dumps(evaluar(oos, rho, version), indent=2, ensure_ascii=False, default=str))
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_player_value.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/qf/model/player_value.py tests/test_player_value.py
git commit -m "Fuerza por jugador (B1.4): comparación de brazos del XI y artefactos" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Integración en el entrenamiento mensual

**Files:**
- Modify: `src/qf/model/train.py` (tras el bloque `val["lineup_challenger"] = lineup_report`)
- Test: `tests/test_player_value.py`

**Interfaces:**
- Consumes: `evaluar(oos, rho, version)` (Task 4).
- Produces: `val["player_value"]` en el informe de validación del modelo.

- [ ] **Step 1: Test (falla)**

```python
def test_train_llama_a_la_comparacion_y_no_se_cae_si_falla():
    from pathlib import Path
    fuente = (Path(__file__).resolve().parents[1] / "src/qf/model/train.py").read_text(encoding="utf-8")
    assert 'val["player_value"]' in fuente
    bloque = fuente[fuente.index('val["player_value"]') - 600:fuente.index('val["player_value"]')]
    assert "player_value_evaluar(oos" in bloque and "except Exception" in bloque
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_player_value.py -q -k train`
Expected: FAIL `ValueError: substring not found`

- [ ] **Step 3: Implementar**

En `src/qf/model/train.py`, importación con las demás del modelo:

```python
from .player_value import evaluar as player_value_evaluar
```

y justo después de `val["lineup_challenger"] = lineup_report`:

```python
    # Fuerza por jugador (Fase B1): XI con valor y XI con nota contra el XI
    # simple, sobre las mismas filas. Solo informe y artefactos; nunca bloquea
    # el despliegue del modelo.
    try:
        player_value_report = player_value_evaluar(oos, float(model.params.rho), version)
    except Exception as exc:  # noqa: BLE001
        player_value_report = {"ok": False, "status": "error", "reason": str(exc)}
    val["player_value"] = player_value_report
```

- [ ] **Step 4: Ejecutar toda la suite**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests -q`
Expected: sin FAIL.

- [ ] **Step 5: Commit**

```bash
git add src/qf/model/train.py tests/test_player_value.py
git commit -m "Fuerza por jugador (B1.5): la comparación entra en el entrenamiento mensual" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Desplegar, evaluar con el walk-forward guardado y registrar

**Files:**
- Modify: `harness/tareas.md`, `harness/progreso.md`, `README.md`

- [ ] **Step 1: Harness local**

Run: `./scripts/harness_check.sh`
Expected: `OK. El repo está en buen estado.`

- [ ] **Step 2: Comprobar el servidor, respaldar y desplegar**

```bash
for f in src/qf/model/lineup_challenger.py src/qf/model/train.py; do l=$(git show HEAD~5:$f | tr -d '\r' | sha256sum | cut -c1-12); r=$(ssh quantfut "tr -d '\r' < ~/quantfut/$f | sha256sum" | cut -c1-12); echo "$f git=$l server=$r"; done
ssh quantfut 'set -e; cd ~/quantfut; B=~/respaldo_$(date +%Y%m%d)_b1; mkdir -p $B; tar czf $B/codigo.tar.gz src/qf/model/lineup_challenger.py src/qf/model/train.py'
scp -q src/qf/model/player_ratings.py src/qf/model/player_value.py src/qf/model/lineup_challenger.py src/qf/model/train.py quantfut:quantfut/src/qf/model/
scp -q tests/test_player_ratings.py tests/test_player_value.py tests/test_lineup_challenger.py quantfut:quantfut/tests/
ssh quantfut 'cd ~/quantfut && timeout 600 docker compose up -d --build api worker && docker compose exec -T worker ls /srv/quantfut/artifacts | grep oos_'
```
Expected: hashes iguales en la primera línea de cada archivo; al final, al menos un `oos_<version>.pkl` (lo guarda el reentreno del 1-oct).

- [ ] **Step 3: Evaluar en segundo plano**

```bash
ssh quantfut 'cd ~/quantfut && nohup sh -c "timeout 7200 docker compose exec -T worker sh -c \"cd /app && PYTHONPATH=/app/src python -m qf.model.player_value\" > /tmp/player_value.log 2>&1; echo FIN >> /tmp/player_value.log" > /dev/null 2>&1 < /dev/null & echo lanzado'
```
Al terminar: `ssh quantfut 'grep -v httpx /tmp/player_value.log | tail -80'`.
Expected: JSON con `n_filas` (≥ 700), y para `simple`, `valor` y `nota`: `rps_before/after`, `log_loss_before/after`, `ece_before/after`, `leagues_improved`, y `valor.gana_al_simple`.

- [ ] **Step 4: Registrar el resultado**

- `harness/progreso.md` (entrada fechada): números de los tres brazos, si "XI con valor" gana al simple y la decisión siguiente (si gana: escribir el plan B2 de sombra en vivo; si no: el valor por jugador, así medido, no aporta sobre el XI simple y no se sigue).
- `harness/tareas.md`: marcar la Fase B1 y dejar la B2 pendiente o descartada según el resultado.
- `README.md`: añadir a la fila de la Fase 4 una línea con el resultado.
- Commit (con la técnica de índice si `harness/progreso.md` tiene cambios de otras sesiones sin commitear):

```bash
git add harness/tareas.md README.md
git commit -m "Harness: resultado de la fuerza por jugador (Fase B1)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
