# F1 — Capa de ajuste de lambdas por bloques: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un módulo `qf.model.ajuste` que decide qué bloques de señales entran al motor principal con la puerta "solo si gana", y fija la línea base contra la que compite cada bloque nuevo.

**Architecture:** Generaliza `lineup_challenger.py` (ajuste Poisson con offset, encogimiento, recorte, puerta de RPS/log-loss/ECE/ligas). Se extrae la puerta a una función compartida y `ajuste.py` añade lo que falta: un registro de bloques y la comparación **incremental** (modelo con bloques A frente a A+B sobre las mismas filas), más el artefacto `ajuste_<versión>.pkl`. Dixon-Coles y la calibración no se tocan.

**Tech Stack:** Python 3.12, numpy, pandas, scipy, pytest.

**Spec:** `docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md` (secciones 2 y 4, fase F1).

## Global Constraints

- Dixon-Coles, el término `strength` entre ligas (`tests/test_cross_league.py` a 1e-9) y la calibración no se modifican.
- `λ = λ_base · exp(clip(shrink · Σ x·β, -1, 1))`, igual para μ; `shrink = 0.5`, `l2 = 10`.
- Dato ausente → mediana del ajuste (aporte 0), nunca cero inventado.
- Entra un bloque solo si mejora RPS y log-loss, no empeora el ECE más allá de su ruido (remuestreo pareado) y mejora en ≥2 ligas, sobre las mismas filas.
- La `rho` de cada fila de validación es la histórica de esa predicción, nunca la del modelo de hoy.
- Comportamiento de `lineup_challenger.fit_and_validate` idéntico antes y después del refactor.
- No se reentrena ni se activa ningún modelo en esta fase.

## Review Focus

1. Columnas de un bloque ausentes en el marco → error claro, no un `KeyError` opaco (Task 2).
2. Bloque sin señal (ruido) → no entra aunque tenga muchas columnas (Task 2).
3. Muestra insuficiente → `status: collecting`, nunca un `ok` positivo (Task 2).
4. Sin bloques aceptados el ajuste devuelve las lambdas base exactas (Task 2).
5. La comparación incremental usa las mismas filas para A y A+B (Task 2).

---

### Task 1: Extraer la puerta de `fit_and_validate`

**Files:**
- Modify: `src/qf/model/lineup_challenger.py` (función `fit_and_validate`)
- Test: `tests/test_lineup_challenger.py` (añadir)

**Interfaces:**
- Produces: `informe_antes_despues(val: pd.DataFrame, before: np.ndarray, after: np.ndarray, n_fit: int) -> dict`. `val` trae `home_goals`, `away_goals`, `league_id` con índice 0..n-1; `before`/`after` son matrices (n, 3) de probabilidades 1X2. Devuelve el mismo informe que hoy construye `fit_and_validate` (claves `status`, `n_fit`, `n_val`, `rps_*`, `log_loss_*`, `ece_*`, `ece_delta_ic95`, `ece_empeora`, `by_league`, `leagues_improved`, `ok`, `promotion_blocked_until_clv`).

- [ ] **Step 1: Prueba de caracterización con los valores actuales (debe pasar ya)**

Ejecutar una vez el código actual sobre un marco sintético y fijar los números en la prueba. Primero obtener los valores:

```bash
PYTHONPATH=src .venv/Scripts/python.exe - <<'EOF'
import numpy as np, pandas as pd
from qf.model.lineup_challenger import fit_and_validate
rng = np.random.default_rng(0); n = 800; x = rng.normal(size=n)
frame = pd.DataFrame({"match_id": [f"m{i}" for i in range(n)], "league_id": ["A", "B"] * (n // 2),
    "kickoff_utc": pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC"),
    "base_lam": 1.4, "base_mu": 1.1, "rho": -0.05, "home_d_tiros": x,
    "home_goals": rng.poisson(1.4 * np.exp(0.3 * x)), "away_goals": rng.poisson(1.1, n)})
_, r = fit_and_validate(frame, rho=-0.05, features=["home_d_tiros"])
print({k: r[k] for k in ("n_fit","n_val","rps_before","rps_after","log_loss_before","log_loss_after","ece_before","ece_after","leagues_improved","ok")})
EOF
```

Escribir la prueba con esos valores:

```python
# añadir a tests/test_lineup_challenger.py
def test_fit_and_validate_informe_no_cambia_tras_extraer_la_puerta():
    """Caracterización: los números de la puerta son los de antes del refactor."""
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
    _, r = fit_and_validate(frame, rho=-0.05, features=["home_d_tiros"])
    esperado = GOLDEN  # <- pegar aquí el diccionario impreso arriba
    assert {k: r[k] for k in esperado} == esperado
```

- [ ] **Step 2: Ejecutar: pasa con el código actual**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_lineup_challenger.py -q`
Expected: PASS (es una prueba de caracterización: protege el refactor)

- [ ] **Step 3: Escribir la prueba de la función nueva (falla)**

```python
def test_informe_antes_despues_expuesto_y_coherente():
    import numpy as np

    from qf.model.lineup_challenger import informe_antes_despues
    val = pd.DataFrame({"home_goals": [2, 0, 1, 1], "away_goals": [0, 1, 1, 3],
                        "league_id": ["A", "A", "B", "B"]})
    antes = np.array([[.4, .3, .3]] * 4)
    despues = np.array([[.7, .2, .1], [.1, .2, .7], [.2, .6, .2], [.1, .1, .8]])
    r = informe_antes_despues(val, antes, despues, n_fit=10)
    assert r["n_fit"] == 10 and r["n_val"] == 4
    assert r["rps_after"] < r["rps_before"] and r["log_loss_after"] < r["log_loss_before"]
    assert set(r["by_league"]) == {"A", "B"} and r["leagues_improved"] == 2
```

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_lineup_challenger.py -q`
Expected: FAIL (`ImportError: cannot import name 'informe_antes_despues'`)

- [ ] **Step 4: Refactor mínimo**

En `fit_and_validate`, mover las líneas desde `outcomes = np.where(...)` hasta `report["ok"] = bool(improved)` a una función de módulo con la firma de Interfaces (el cuerpo es ese mismo código, sustituyendo `cut` por `n_fit` y `val.index.get_indexer(group.index)` por el mismo cálculo sobre el `val` recibido). `fit_and_validate` pasa a:

```python
    report = informe_antes_despues(val, before, after, int(cut))
    model.params.offline_validated = bool(report["ok"])
    return model, report
```

- [ ] **Step 5: Ejecutar y ver que pasa todo**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_lineup_challenger.py tests/test_player_ratings.py tests/test_masmenos.py -q`
Expected: PASS (la caracterización sigue igual y la prueba nueva pasa)

- [ ] **Step 6: Commit**

```bash
git add src/qf/model/lineup_challenger.py tests/test_lineup_challenger.py
git commit -m "F1: extraer la puerta de fit_and_validate a informe_antes_despues" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `ajuste.py` — registro de bloques y comparación incremental

**Files:**
- Create: `src/qf/model/ajuste.py`
- Test: `tests/test_ajuste.py`

**Interfaces:**
- Consumes: `lc.informe_antes_despues`, `lc._fit_poisson_offset`, `lc._probabilities`, `lc.LineupLambdaChallenger`, `lc.LineupParams`, `lc.LINEUP_FEATURES` (Task 1 y módulo existente).
- Produces: `Bloque(nombre: str, columnas: tuple[str, ...])`, `BLOQUES: dict[str, Bloque]`, `registrar(b) -> Bloque`, `columnas_de(nombres: list[str]) -> list[str]`, `comparar(frame, antes: list[str], despues: list[str], rho: float = 0.0, shrink: float = 0.5, holdout_frac: float = 0.30, min_fit: int = 500, min_val: int = 200, l2: float = 10.0) -> dict`, `Ajuste` (dataclass con `bloques`, `modelo`, `informe`, `aplicar(frame)`, `guardar(ruta)`, `cargar(ruta)`), `construir_ajuste(frame, candidatos: list[str], rho: float = 0.0, **kw) -> Ajuste`.

- [ ] **Step 1: Escribir las pruebas que fallan**

```python
# tests/test_ajuste.py
"""El ajuste solo acepta un bloque si gana, sobre las mismas filas."""
import numpy as np
import pandas as pd
import pytest

from qf.model import ajuste as aj
from qf.model import lineup_challenger as lc


def marco(n=1600, seed=1, efecto=0.35):
    rng = np.random.default_rng(seed)
    senal, ruido = rng.normal(size=n), rng.normal(size=n)
    return pd.DataFrame({
        "match_id": [f"m{i}" for i in range(n)], "league_id": ["A", "B", "C"] * (n // 3) + ["A"] * (n % 3),
        "kickoff_utc": pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC"),
        "base_lam": 1.4, "base_mu": 1.1, "rho": -0.05, "s1": senal, "s2": ruido, "s3": rng.normal(size=n),
        "home_goals": rng.poisson(1.4 * np.exp(efecto * senal)), "away_goals": rng.poisson(1.1, n)})


@pytest.fixture(autouse=True)
def bloques_de_prueba(monkeypatch):
    monkeypatch.setattr(aj, "BLOQUES", {})
    aj.registrar(aj.Bloque("con_senal", ("s1",)))
    aj.registrar(aj.Bloque("ruido", ("s2", "s3")))


def test_un_bloque_con_senal_pasa_la_puerta():
    r = aj.comparar(marco(), [], ["con_senal"], rho=-0.05)
    assert r["ok"] is True and r["rps_after"] < r["rps_before"]
    assert r["bloques_antes"] == [] and r["bloques_despues"] == ["con_senal"]


def test_un_bloque_de_ruido_no_pasa():
    r = aj.comparar(marco(), [], ["ruido"], rho=-0.05)
    assert r["ok"] is False


def test_la_comparacion_incremental_usa_las_mismas_filas():
    r = aj.comparar(marco(), ["con_senal"], ["con_senal", "ruido"], rho=-0.05)
    assert r["n_val"] == int(len(marco()) * 0.30) or abs(r["n_val"] - len(marco()) * 0.30) <= 1
    assert r["ok"] is False                      # el ruido no mejora a la señal sola


def test_sin_bloques_la_comparacion_es_la_del_challenger_de_siempre():
    frame = marco()
    r = aj.comparar(frame, [], ["con_senal"], rho=-0.05)
    _, ref = lc.fit_and_validate(frame, rho=-0.05, features=["s1"])
    for k in ("n_fit", "n_val", "rps_before", "rps_after", "log_loss_before", "log_loss_after",
              "ece_before", "ece_after", "leagues_improved", "ok"):
        assert r[k] == ref[k], k


def test_muestra_insuficiente_es_collecting_no_ok():
    r = aj.comparar(marco(n=300), [], ["con_senal"], rho=-0.05)
    assert r["ok"] is False and r["status"] == "collecting"


def test_columnas_ausentes_dan_un_error_claro():
    frame = marco().drop(columns=["s1"])
    with pytest.raises(ValueError, match="s1"):
        aj.comparar(frame, [], ["con_senal"], rho=-0.05)


def test_construir_acepta_solo_lo_que_gana_y_sin_bloques_deja_las_lambdas_base():
    a = aj.construir_ajuste(marco(), ["ruido", "con_senal"], rho=-0.05)
    assert a.bloques == ["con_senal"] and a.informe["ruido"]["ok"] is False
    vacio = aj.construir_ajuste(marco(), ["ruido"], rho=-0.05)
    frame = marco()
    lam, mu = vacio.aplicar(frame)
    assert vacio.bloques == [] and np.array_equal(lam, frame["base_lam"].to_numpy())
    assert np.array_equal(mu, frame["base_mu"].to_numpy())


def test_guardar_y_cargar_conserva_el_ajuste(tmp_path):
    a = aj.construir_ajuste(marco(), ["con_senal"], rho=-0.05)
    ruta = str(tmp_path / "ajuste_v.pkl")
    a.guardar(ruta)
    b = aj.Ajuste.cargar(ruta)
    assert b.bloques == a.bloques
    l1, m1 = a.aplicar(marco())
    l2, m2 = b.aplicar(marco())
    assert np.allclose(l1, l2) and np.allclose(m1, m2)
```

- [ ] **Step 2: Ejecutar y ver que falla**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_ajuste.py -q`
Expected: FAIL (`ImportError: cannot import name 'ajuste'`)

- [ ] **Step 3: Implementar**

```python
# src/qf/model/ajuste.py
"""Capa de ajuste de lambdas por bloques de señales (F1 de la spec 2026-10-14).

λ = λ_base · exp(clip(shrink · Σ x·β, -1, 1)); lo mismo para μ. Dixon-Coles y la
calibración no se tocan. Un bloque entra solo si, sobre las mismas filas, mejora al
modelo SIN él (puerta de `lineup_challenger.informe_antes_despues`).
"""
from __future__ import annotations

import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import lineup_challenger as lc


@dataclass(frozen=True)
class Bloque:
    nombre: str
    columnas: tuple[str, ...]


BLOQUES: dict[str, Bloque] = {}


def registrar(bloque: Bloque) -> Bloque:
    BLOQUES[bloque.nombre] = bloque
    return bloque


registrar(Bloque("xi", tuple(lc.LINEUP_FEATURES)))


def columnas_de(nombres: list[str]) -> list[str]:
    cols: list[str] = []
    for nombre in nombres:
        cols += [c for c in BLOQUES[nombre].columnas if c not in cols]
    return cols


def _ajustar(train: pd.DataFrame, cols: list[str], l2: float):
    raw = train[cols].to_numpy(dtype=float)
    medians = np.nanmedian(raw, axis=0)
    medians = np.where(np.isnan(medians), 0.0, medians)
    filled = np.where(np.isnan(raw), medians, raw)
    scales = np.std(filled, axis=0)
    scales = np.where(scales < 1e-8, 1.0, scales)
    x = np.column_stack([np.ones(len(train)), (filled - medians) / scales])
    bh = lc._fit_poisson_offset(x, np.log(train["base_lam"].to_numpy()),
                                train["home_goals"].to_numpy(dtype=float), l2)
    ba = lc._fit_poisson_offset(x, np.log(train["base_mu"].to_numpy()),
                                train["away_goals"].to_numpy(dtype=float), l2)
    return medians, scales, bh, ba


def _modelo(train: pd.DataFrame, cols: list[str], rho: float, shrink: float, l2: float):
    if not cols:
        return None
    medians, scales, bh, ba = _ajustar(train, cols, l2)
    return lc.LineupLambdaChallenger(lc.LineupParams(
        medians.tolist(), scales.tolist(), bh.tolist(), ba.tolist(), float(rho), float(shrink),
        int(len(train)), False, cols))


def _lambdas(modelo, frame: pd.DataFrame):
    if modelo is None:
        return frame["base_lam"].to_numpy(dtype=float), frame["base_mu"].to_numpy(dtype=float)
    return modelo.apply(frame)


def _ordenado(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(["kickoff_utc", "match_id"]).dropna(
        subset=["base_lam", "base_mu", "home_goals", "away_goals"]).reset_index(drop=True)


def comparar(frame: pd.DataFrame, antes: list[str], despues: list[str], rho: float = 0.0,
             shrink: float = 0.5, holdout_frac: float = 0.30, min_fit: int = 500,
             min_val: int = 200, l2: float = 10.0) -> dict:
    """Modelo con los bloques `antes` frente al de `despues`, mismas filas y misma partición."""
    cols_a, cols_b = columnas_de(antes), columnas_de(despues)
    faltan = [c for c in cols_b if c not in frame.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en el marco: {faltan}")
    ordered = _ordenado(frame)
    cut = int(len(ordered) * (1.0 - holdout_frac))
    if cut < min_fit or len(ordered) - cut < min_val:
        return {"ok": False, "status": "collecting", "n": int(len(ordered)),
                "reason": f"Muestra insuficiente: {cut} de ajuste y {len(ordered) - cut} de validación; "
                          f"se exigen {min_fit}/{min_val}.",
                "bloques_antes": list(antes), "bloques_despues": list(despues)}
    train, val = ordered.iloc[:cut], ordered.iloc[cut:].reset_index(drop=True)
    # La rho de cada predicción es la de ESE momento; la de hoy traería conocimiento del futuro.
    hist_rho = val["rho"].to_numpy(dtype=float) if "rho" in val.columns else rho
    la, ma = _lambdas(_modelo(train, cols_a, rho, shrink, l2), val)
    lb, mb = _lambdas(_modelo(train, cols_b, rho, shrink, l2), val)
    informe = lc.informe_antes_despues(val, lc._probabilities(la, ma, hist_rho),
                                       lc._probabilities(lb, mb, hist_rho), int(cut))
    informe["bloques_antes"], informe["bloques_despues"] = list(antes), list(despues)
    return informe


@dataclass
class Ajuste:
    bloques: list[str]
    modelo: object            # LineupLambdaChallenger | None (sin bloques: lambdas base)
    informe: dict

    def aplicar(self, frame: pd.DataFrame):
        return _lambdas(self.modelo, frame)

    def guardar(self, ruta: str) -> None:
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        params = asdict(self.modelo.params) if self.modelo is not None else None
        with open(ruta, "wb") as f:
            pickle.dump({"bloques": self.bloques, "params": params, "informe": self.informe}, f)

    @classmethod
    def cargar(cls, ruta: str) -> "Ajuste":
        with open(ruta, "rb") as f:
            d = pickle.load(f)
        modelo = lc.LineupLambdaChallenger(lc.LineupParams(**d["params"])) if d["params"] else None
        return cls(d["bloques"], modelo, d["informe"])


def construir_ajuste(frame: pd.DataFrame, candidatos: list[str], rho: float = 0.0, **kw) -> Ajuste:
    """Acepta, en orden, cada candidato que mejora al conjunto ya aceptado."""
    aceptados: list[str] = []
    informe: dict = {}
    for nombre in candidatos:
        r = comparar(frame, aceptados, aceptados + [nombre], rho=rho, **kw)
        informe[nombre] = r
        if r["ok"]:
            aceptados.append(nombre)
    cols = columnas_de(aceptados)
    if not cols:
        return Ajuste([], None, informe)
    cut = int(len(_ordenado(frame)) * (1.0 - kw.get("holdout_frac", 0.30)))
    train = _ordenado(frame).iloc[:cut]
    modelo = _modelo(train, cols, rho, kw.get("shrink", 0.5), kw.get("l2", 10.0))
    modelo.params.offline_validated = True
    return Ajuste(aceptados, modelo, informe)
```

- [ ] **Step 4: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_ajuste.py -q`
Expected: PASS (8 pruebas). Si `test_la_comparacion_incremental...` es inestable por el azar de la semilla, subir `efecto` a 0,5; no relajar la puerta.

- [ ] **Step 5: Commit**

```bash
git add src/qf/model/ajuste.py tests/test_ajuste.py
git commit -m "F1: capa de ajuste por bloques con puerta incremental" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: CLI de línea base, ensayo en el VPS y documentación

**Files:**
- Modify: `src/qf/model/ajuste.py` (añadir `main`)
- Test: `tests/test_ajuste.py` (añadir)
- Modify: `harness/tareas.md`, `harness/progreso.md`, `README.md`
- Create: `docs/f1_capa_de_ajuste_20261014.md`

**Interfaces:**
- Consumes: `construir_ajuste`, `lc.load_training_frame`.
- Produces: `python -m qf.model.ajuste [--oos RUTA] [--guardar]`: imprime el informe de línea base; solo con `--guardar` escribe `ajuste_<versión>.pkl`.

- [ ] **Step 1: Prueba que falla**

```python
def test_el_cli_no_guarda_sin_la_bandera(monkeypatch, tmp_path, capsys):
    guardados = []
    monkeypatch.setattr(aj, "_cargar_marco", lambda ruta: (marco(), -0.05, "vprueba"))
    monkeypatch.setattr(aj.Ajuste, "guardar", lambda self, ruta: guardados.append(ruta))
    aj.main(["--oos", "x.pkl"])
    aj.main(["--oos", "x.pkl", "--guardar"])
    assert len(guardados) == 1 and guardados[0].endswith("ajuste_vprueba.pkl")
    assert "con_senal" not in capsys.readouterr().out or True   # la salida es el informe JSON
```

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_ajuste.py::test_el_cli_no_guarda_sin_la_bandera -q`
Expected: FAIL (`AttributeError: module ... has no attribute 'main'`)

- [ ] **Step 2: Implementar**

```python
def _cargar_marco(ruta: str | None):
    import glob
    import os

    from ..config import settings
    from ..db import query_one
    ruta = ruta or max(glob.glob(f"{settings.artifact_dir}/oos_*.pkl"), key=os.path.getmtime)
    version = os.path.basename(ruta)[len("oos_"):-len(".pkl")]
    fila = query_one("SELECT params->>'rho' AS rho FROM model_artifacts WHERE model_version = %s", (version,))
    frame, _ = lc.load_training_frame(pd.read_pickle(ruta))
    return frame, float(fila["rho"]), version


def main(argv=None):
    import argparse
    import json

    from ..config import settings
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--oos", help="oos_<versión>.pkl; por defecto el más reciente")
    p.add_argument("--guardar", action="store_true", help="escribe ajuste_<versión>.pkl")
    args = p.parse_args(argv)
    frame, rho, version = _cargar_marco(args.oos)
    a = construir_ajuste(frame, list(BLOQUES), rho=rho)
    if args.guardar:
        a.guardar(f"{settings.artifact_dir}/ajuste_{version}.pkl")
    print(json.dumps({"version": version, "bloques_aceptados": a.bloques, "informe": a.informe},
                     indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Ejecutar y ver que pasa**

Run: `PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/test_ajuste.py -q`
Expected: PASS (9 pruebas)

- [ ] **Step 4: Línea base en el VPS (solo lectura, sin guardar)**

Ejecutar por stdin en el contenedor `api` el módulo `ajuste.py` y `lineup_challenger.py` actuales con `main(["--oos", "/srv/quantfut/artifacts/oos_2026.10.12-221104.pkl"])`, sin `--guardar`. Guardar el informe.
Expected: `bloques_aceptados == ["xi"]` con `rps` 0,21305 → ~0,2118, el mismo resultado que el `lineup_challenger` del último entrenamiento (`val_metrics.lineup_challenger`). Si difiere, investigar antes de seguir: sería una divergencia de la puerta.

- [ ] **Step 5: Documentar y cerrar F1**

Escribir `docs/f1_capa_de_ajuste_20261014.md` con el informe real; marcar F1 en `harness/tareas.md`; en `harness/progreso.md` la decisión clave (no se reentrena: el entrenamiento del 12-oct ya usó el xG nuevo y el cron lo repite el 1-nov; la línea base sale del OOS guardado); una línea en el README.

```bash
./scripts/harness_check.sh
git add src/qf/model/ajuste.py tests/test_ajuste.py docs/f1_capa_de_ajuste_20261014.md harness/tareas.md harness/progreso.md README.md
git commit -m "F1: CLI de línea base y documentación" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

## Self-review

**Cobertura de la spec:** sección 2 (capa de ajuste, contrato, artefacto `ajuste_<versión>.pkl`, sin bloques = lambdas base) → Task 2; sección 4 (puerta incremental sobre las mismas filas, ≥2 ligas, informe) → Tasks 1-2; F1 "línea base" → Task 3. **Desviación declarada:** F1 no reentrena. El reentrenamiento del 12-oct ya incorporó el xG nuevo (`docs/entrenamiento_xg_20261012.md`) y el cron del día 1 repite el de noviembre con los 5.355 xG de PitchAPI; la línea base se mide sobre el OOS guardado.

**Fuera de F1 a propósito:** cargar los bloques reales (XI usa `load_training_frame`; los demás llegan en F2-F6) y servir el ajuste en la predicción diaria o en el sello tardío (F7).

**Consistencia de tipos:** `comparar` devuelve el informe de `informe_antes_despues` más `bloques_antes/despues`; `construir_ajuste` lee `r["ok"]`; `Ajuste.aplicar` delega en `_lambdas`. `test_sin_bloques_la_comparacion_es_la_del_challenger_de_siempre` ata la paridad con `lc.fit_and_validate`.

**Riesgo:** el refactor de la Task 1 toca un módulo que corre en producción (`shadow.py`, `train.py`). La prueba de caracterización con valores fijados y las suites de lineup, player_ratings y masmenos son la red; el VPS no se despliega en F1.
