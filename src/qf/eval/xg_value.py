"""
¿Aporta el xG al modelo de fuerza? Mezcla actual (XG_BLEND) frente a solo goles.

Contexto (2-oct-2026): `worldfootballR_data` dejó de publicar en 2024-25 y hay
que decidir antes del 1-nov si se busca otra fuente. Se mide antes de buscar.

Regla fijada ANTES de ver resultados (harness/tareas.md):
  - Ventana A, cuando el xG existía (jul-2023 → ene-2025): el xG "aporta" si
    el RPS mejora con el IC95 por semanas ENTERO por debajo de cero y en al
    menos la mitad de las ligas. Es lo que recuperaría una fuente nueva.
  - Ventana B, la situación actual (jul-2025 → hoy, xG viejo y goles nuevos):
    informativa. Dice si mantener la mezcla con el xG parado perjudica.

Los dos brazos son el mismo walk-forward (reajuste cada 30 días, cada
predicción solo con partidos anteriores) y solo cambia `xg_blend`. Solo
lectura: no toca producción ni artefactos.
"""
from __future__ import annotations

import argparse
import json
import logging

import numpy as np
import pandas as pd

from ..config import settings
from .backtest import check_leakage, walk_forward_oos
from .comparison import _rps_per_match

log = logging.getLogger(__name__)

MIN_SEMANAS = 8
VENTANA_A = ("2023-07-01", "2025-02-01")
VENTANA_B = ("2025-07-01", None)


def compare(oos_xg: pd.DataFrame, oos_goles: pd.DataFrame,
            iterations: int = 1000) -> dict:
    """Delta de RPS (xG − goles) sobre los partidos de AMBOS brazos."""
    cols = ["match_id", "kickoff_utc", "league_id", "p_home", "p_draw",
            "p_away", "outcome"]
    m = oos_xg[cols].merge(oos_goles[cols], on=["match_id", "kickoff_utc",
                                                 "league_id", "outcome"],
                           suffixes=("_xg", "_goles"))
    oc = m["outcome"].to_numpy(int)
    rps = {}
    for brazo in ("xg", "goles"):
        p = m[[f"p_home_{brazo}", f"p_draw_{brazo}", f"p_away_{brazo}"]].to_numpy(float)
        rps[brazo] = _rps_per_match(p, oc)
    delta = rps["xg"] - rps["goles"]

    semanas = (pd.to_datetime(m["kickoff_utc"], utc=True)
               .dt.tz_convert(None).dt.to_period("W"))
    grupos = list(pd.Series(delta).groupby(semanas.to_numpy()).indices.values())
    ci = None
    if len(grupos) >= MIN_SEMANAS:
        rng = np.random.default_rng(42)
        est = [float(delta[np.concatenate(
                   [grupos[i] for i in rng.integers(0, len(grupos), len(grupos))])].mean())
               for _ in range(iterations)]
        lo, hi = np.percentile(est, [2.5, 97.5])
        ci = [round(float(lo), 6), round(float(hi), 6)]

    por_liga = {str(lg): {"n": int(len(idx)),
                          "rps_delta": round(float(delta[idx].mean()), 6)}
                for lg, idx in pd.Series(delta).groupby(m["league_id"].to_numpy())
                .indices.items()}
    return {
        "n": int(len(m)),
        "semanas": len(grupos),
        "rps_xg": round(float(rps["xg"].mean()), 6),
        "rps_goles": round(float(rps["goles"].mean()), 6),
        "rps_delta": round(float(delta.mean()), 6),
        "rps_delta_ci95": ci,
        "negativo_favorece_xg": True,
        "ligas": len(por_liga),
        "ligas_mejoran": sum(v["rps_delta"] < 0 for v in por_liga.values()),
        "por_liga": por_liga,
    }


def veredicto(resultado: dict) -> str:
    ci = resultado.get("rps_delta_ci95")
    if (ci is not None and ci[1] < 0
            and resultado["ligas_mejoran"] * 2 >= resultado["ligas"]):
        return "xg_aporta"
    return "xg_no_demostrado"


COMUN = {"step_days": 30, "min_train": 500}
BLEND = {"xg": None, "goles": 0.0}       # None = settings.xg_blend (producción)
VENTANAS = {"a": VENTANA_A, "b": VENTANA_B}


def _datos(df: pd.DataFrame, fin: str | None) -> pd.DataFrame:
    return df if fin is None else df[df["kickoff_utc"] < pd.Timestamp(fin, tz="UTC")]


def brazo(df: pd.DataFrame, inicio: str, fin: str | None, nombre: str) -> pd.DataFrame:
    """Un brazo de una ventana. Los dos brazos solo difieren en `xg_blend`."""
    blend = settings.xg_blend if BLEND[nombre] is None else BLEND[nombre]
    return walk_forward_oos(_datos(df, fin), inicio, xg_blend=blend, **COMUN)


def _informe(df: pd.DataFrame, inicio: str, fin: str | None,
             oos_xg: pd.DataFrame, oos_goles: pd.DataFrame) -> dict:
    resultado = compare(oos_xg, oos_goles)
    test = _datos(df, fin)
    test = test[test["kickoff_utc"] >= pd.Timestamp(inicio, tz="UTC")]
    if "home_xg" in test:
        resultado["test_con_xg_pct"] = round(100 * float(test["home_xg"].notna().mean()), 1)
    resultado["ventana"] = [inicio, fin]
    return resultado


def ventana(df: pd.DataFrame, inicio: str, fin: str | None) -> dict:
    """Mismo walk-forward para los dos brazos; solo cambia `xg_blend`."""
    return _informe(df, inicio, fin, brazo(df, inicio, fin, "xg"),
                    brazo(df, inicio, fin, "goles"))


def _cargar() -> pd.DataFrame:
    from ..model.train import load_training_data

    df = load_training_data()
    df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
    return df


def combinar(directorio: str) -> dict:
    """Une los cuatro brazos ya calculados (`--brazo`) en el informe final."""
    df = _cargar()
    out = {"xg_blend_actual": settings.xg_blend, "fugas": check_leakage(df)}
    for clave, etiqueta in (("a", "ventana_a_cuando_existia"),
                            ("b", "ventana_b_situacion_actual")):
        inicio, fin = VENTANAS[clave]
        oos = {n: pd.read_pickle(f"{directorio}/{clave}_{n}.pkl") for n in BLEND}
        informe = _informe(df, inicio, fin, oos["xg"], oos["goles"])
        if clave == "a":
            informe["veredicto"] = veredicto(informe)
        out[etiqueta] = informe
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    # Cada reajuste tarda ~18 min en el VPS y son 68: los cuatro brazos se
    # lanzan como procesos aparte (`--brazo a xg DIR`, ...) y `--combinar DIR`
    # hace el informe.
    ap.add_argument("--brazo", nargs=3, metavar=("VENTANA", "BRAZO", "DIR"))
    ap.add_argument("--combinar", metavar="DIR")
    args = ap.parse_args()
    if args.brazo:
        clave, nombre, directorio = args.brazo
        inicio, fin = VENTANAS[clave]
        brazo(_cargar(), inicio, fin, nombre).to_pickle(
            f"{directorio}/{clave}_{nombre}.pkl")
        print("ok", clave, nombre)
    else:
        print(json.dumps(combinar(args.combinar), ensure_ascii=False, indent=1,
                         default=str))
