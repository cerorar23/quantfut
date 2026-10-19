"""Ajuste de lambdas por el once confirmado (impacto por jugador), en MODO SOMBRA (19-oct-2026).

Medido con `qf.model.contexto` (bloque `epi_total`): ΔRPS −0,0005 sobre el modelo de nivel, favorable en las 4 particiones de
validación, significativo en 3, placebo limpio (docs/impacto_jugador_20261019.md). Es pequeño frente a la brecha con el mercado,
así que no se aplica: calcula el factor y lo anota en la predicción FINAL de cada partido (`data_completeness.ajuste_xi`) sin
tocar los lambdas sellados. Con ~150 partidos medidos hacia adelante (`python -m qf.model.ajuste_xi --medir`) se decide si pasa
a `activo`.

Variable: `epi_total_local` y `epi_total_visita` (cuánto mejor o peor que el habitual es el once de cada lado). Sin intercepto:
con el once habitual la variable es 0 y el factor es exactamente 1. Un dato ausente se toma como 0. Cualquier fallo devuelve
`None`: nunca puede impedir el sellado.

Fuente del once en producción: la última captura de FotMob con alineación OFICIAL (`tipo_alineacion = 'standard'`) en
`fotmob_jugador_previo`; el estado (fuerza de cada jugador, once habitual) se recorre desde `fotmob_jugador_partido`.
"""
from __future__ import annotations

import glob
import logging
import os
import pickle
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import ajuste, jugadores

log = logging.getLogger(__name__)

COLUMNAS = jugadores.COLUMNAS["epi_total"]
PREFIJO = "ajuste_xi_"
ESTADO_ARCHIVO = "estado_xi.pkl"
ESTADO_MAX_EDAD_S = 6 * 3600


@dataclass
class AjusteXI:
    escalas: list[float]
    beta_local: list[float]     # sin intercepto, una por columna (local, visita)
    beta_visita: list[float]
    shrink: float
    n_ajuste: int
    oos_version: str

    def factores(self, delta_local, delta_visita) -> tuple[float, float]:
        """(factor del λ del local, factor del μ del visitante). Dato ausente o no finito = 0 = once habitual."""
        x = np.array([delta_local, delta_visita], dtype=float)
        x = np.where(np.isfinite(x), x, 0.0)
        z = x / np.array(self.escalas)
        fl = float(np.exp(np.clip(self.shrink * float(np.dot(self.beta_local, z)), -1.0, 1.0)))
        fv = float(np.exp(np.clip(self.shrink * float(np.dot(self.beta_visita, z)), -1.0, 1.0)))
        return fl, fv

    def guardar(self, ruta: str) -> None:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "wb") as f:
            pickle.dump(self.__dict__, f)

    @classmethod
    def cargar(cls, ruta: str) -> "AjusteXI":
        with open(ruta, "rb") as f:
            return cls(**pickle.load(f))


def ajustar(frame: pd.DataFrame, oos_version: str, shrink: float = 0.5, l2: float = 10.0) -> AjusteXI:
    """Ajusta con todas las filas del walk-forward. La variable no se centra en la mediana: 0 es «el once habitual»."""
    ordenado = ajuste._ordenado(frame)
    cols = list(COLUMNAS)
    raw = ordenado[cols].to_numpy(dtype=float)
    llena = np.where(np.isfinite(raw), raw, 0.0)
    escalas = np.std(llena, axis=0)
    escalas = np.where(escalas < 1e-8, 1.0, escalas)
    from . import lineup_challenger as lc
    x = np.column_stack([np.ones(len(ordenado)), llena / escalas])
    bh = lc._fit_poisson_offset(x, np.log(ordenado["base_lam"].to_numpy()), ordenado["home_goals"].to_numpy(dtype=float), l2)
    ba = lc._fit_poisson_offset(x, np.log(ordenado["base_mu"].to_numpy()), ordenado["away_goals"].to_numpy(dtype=float), l2)
    return AjusteXI([float(v) for v in escalas], [float(v) for v in bh[1:]], [float(v) for v in ba[1:]], float(shrink),
                    int(len(ordenado)), oos_version)


def cargar_ultimo(carpeta: str) -> AjusteXI | None:
    archivos = glob.glob(f"{carpeta}/{PREFIJO}*.pkl")
    return AjusteXI.cargar(max(archivos, key=os.path.getmtime)) if archivos else None


# --------------------------------------------------------------------------------------------- producción
def estado_xi(carpeta: str, max_edad_s: int = ESTADO_MAX_EDAD_S) -> jugadores.EstadoXI:
    """Estado de fuerzas y onces hasta ahora. Se guarda en disco: recorrer 870.000 apariciones tarda minutos."""
    ruta = f"{carpeta}/{ESTADO_ARCHIVO}"
    if os.path.exists(ruta) and time.time() - os.path.getmtime(ruta) < max_edad_s:
        with open(ruta, "rb") as f:
            return pickle.load(f)
    estado = jugadores.EstadoXI.desde_historial(jugadores.cargar_filas())
    tmp = ruta + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(estado, f)
    os.replace(tmp, ruta)
    return estado


def once_confirmado(match_id: str) -> tuple[pd.DataFrame, object, float] | None:
    """(apariciones con equipo, momento de la captura, minutos al saque) de la última captura OFICIAL con los dos lados."""
    from ..db import query
    filas = query(
        """SELECT jp.side, jp.jugador_id, jp.titular, jp.posicion_id, jp.valor_mercado, jp.capturado_en,
                  fp.mins_to_kickoff,
                  CASE WHEN jp.side = 'home' THEN m.home_team_id ELSE m.away_team_id END AS equipo_id
           FROM fotmob_jugador_previo jp
           JOIN fotmob_previo fp ON fp.match_id = jp.match_id AND fp.capturado_en = jp.capturado_en
           JOIN matches m ON m.match_id = jp.match_id
           WHERE jp.match_id = %s AND fp.tipo_alineacion = 'standard'
             AND jp.capturado_en = (SELECT max(f2.capturado_en) FROM fotmob_previo f2
                                    WHERE f2.match_id = jp.match_id AND f2.tipo_alineacion = 'standard')""", (match_id,))
    if not filas:
        return None
    d = pd.DataFrame(filas)
    if d.loc[d["titular"].astype(bool), "side"].nunique() < 2:
        return None
    d["rating"] = np.nan
    return d, d["capturado_en"].iloc[0], float(d["mins_to_kickoff"].iloc[0])


def calcular(match_id: str, carpeta: str) -> dict | None:
    """Constancia para `data_completeness.ajuste_xi`, o None si no hay ajuste o ante cualquier error."""
    try:
        aj = cargar_ultimo(carpeta)
        if aj is None:
            return None
        once = once_confirmado(match_id)
        if once is None:
            return {"disponible": False, "motivo": "sin once oficial de FotMob", "oos_version": aj.oos_version}
        d, capturado, mins = once
        estado = estado_xi(carpeta)
        delta = {}
        for side, sufijo in (("home", "local"), ("away", "visita")):
            p = d[d["side"] == side]
            tit = p[p["titular"].astype(bool)]
            delta[sufijo] = estado.delta(p["equipo_id"].iloc[0], tit) if len(p) else None
        el, ev = (delta["local"] or {}).get("epi_total", np.nan), (delta["visita"] or {}).get("epi_total", np.nan)
        fl, fv = aj.factores(el, ev)
        if not (np.isfinite(fl) and np.isfinite(fv)):
            return None
        return {"disponible": True, "oos_version": aj.oos_version, "shrink": aj.shrink,
                "capturado_en": capturado.isoformat(), "mins_al_saque": round(mins, 1),
                "epi_total_local": None if not np.isfinite(el) else round(float(el), 4),
                "epi_total_visita": None if not np.isfinite(ev) else round(float(ev), 4),
                "factor_local": round(fl, 4), "factor_visita": round(fv, 4)}
    except Exception:  # noqa: BLE001 — un ajuste opcional no puede romper el sellado
        log.exception("Ajuste del once fallido para %s", match_id)
        return None


# --------------------------------------------------------------------------------------------- medición hacia adelante
def medir() -> dict:
    """Partidos terminados con predicción final y factor calculado: RPS con y sin el factor, sobre los mismos partidos."""
    from ..db import query
    from . import lineup_challenger as lc
    filas = query(
        """SELECT p.home_lambda, p.away_lambda, p.rho, m.home_goals, m.away_goals,
                  p.data_completeness -> 'sello_tardio' -> 'ajuste_xi' AS xi
           FROM predictions p JOIN matches m USING (match_id)
           WHERE p.etapa = 'final' AND m.status = 'finished' AND m.home_goals IS NOT NULL
             AND p.data_completeness -> 'sello_tardio' -> 'ajuste_xi' ->> 'disponible' = 'true'""")
    if len(filas) < 10:
        return {"n": len(filas), "estado": "muestra insuficiente"}
    d = pd.DataFrame(filas)
    fl = np.array([float(x["factor_local"]) for x in d["xi"]])
    fv = np.array([float(x["factor_visita"]) for x in d["xi"]])
    lam, mu, rho = (d[c].to_numpy(float) for c in ("home_lambda", "away_lambda", "rho"))
    res = np.where(d["home_goals"] > d["away_goals"], 0, np.where(d["home_goals"] == d["away_goals"], 1, 2))
    p0, p1 = lc._probabilities(lam, mu, rho), lc._probabilities(lam * fl, mu * fv, rho)
    delta, p95 = ajuste._delta_rps(p0, p1, res)
    movidos = int(np.sum((np.abs(np.log(fl)) > 0.005) | (np.abs(np.log(fv)) > 0.005)))
    return {"n": len(d), "con_efecto_mayor_0.5pct": movidos, "rps_sin": round(float(ajuste._rps_por_partido(p0, res).mean()), 5),
            "rps_con": round(float(ajuste._rps_por_partido(p1, res).mean()), 5), "delta_rps": delta, "p95": p95,
            "listo_para_decidir": movidos >= 150}


def main(argv=None) -> None:
    import argparse
    import json

    from ..config import settings
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--oos", nargs="*", help="oos_*.pkl (se unen); por defecto el más reciente")
    ap.add_argument("--guardar", action="store_true", help="escribe ajuste_xi_<versión>.pkl")
    ap.add_argument("--medir", action="store_true", help="mide hacia adelante con las predicciones finales ya jugadas")
    ap.add_argument("--estado", action="store_true", help="reconstruye el estado de fuerzas y onces (cron cada hora)")
    ap.add_argument("--avisar", action="store_true", help="con --medir: avisa por Telegram una sola vez al llegar a 150 partidos")
    a = ap.parse_args(argv)
    if a.estado:
        e = estado_xi(settings.artifact_dir, max_edad_s=0)
        print(json.dumps({"jugadores": len(e.n), "equipos": len(e.historial), "hasta": str(e.hasta)}))
        return
    if a.medir:
        r = medir()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        marca = f"{settings.artifact_dir}/ajuste_xi_150_avisado"
        if a.avisar and r.get("listo_para_decidir") and not os.path.exists(marca):
            from ..publish import telegram as tg
            tg.alert(f"Ajuste del once: {r['con_efecto_mayor_0.5pct']} partidos con efecto medidos hacia adelante "
                     f"(ΔRPS {r['delta_rps']}, p95 {r['p95']}). Toca decidir si pasa a activo.")
            open(marca, "w").close()
        return
    from . import contexto
    rutas = a.oos or [max(glob.glob(f"{settings.artifact_dir}/oos_2*.pkl"), key=os.path.getmtime)]
    oos = pd.concat([pd.read_pickle(r) for r in rutas]).drop_duplicates("match_id")
    version = "+".join(os.path.basename(r)[len("oos_"):-len(".pkl")] for r in rutas)
    frame = contexto.marco_contexto(oos)
    aj_ = ajustar(frame, version)
    print(json.dumps({"oos": rutas, "filas": int(len(frame)), "n_ajuste": aj_.n_ajuste, "escalas": aj_.escalas,
                      "beta_local": aj_.beta_local, "beta_visita": aj_.beta_visita,
                      "ejemplo_once_mucho_peor (-2 sd local)": aj_.factores(-2 * aj_.escalas[0], 0.0),
                      "ejemplo_once_habitual": aj_.factores(0.0, 0.0)}, indent=2, ensure_ascii=False))
    if a.guardar:
        destino = f"{settings.artifact_dir}/{PREFIJO}{version}.pkl"
        aj_.guardar(destino)
        print("guardado:", destino)


if __name__ == "__main__":
    main()
