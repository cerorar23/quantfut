"""Inferencia del motor: reproduce el filtro con Ψ congelado desde la evidencia de la base (plan §H.1, §H.2).

El motor nunca ajusta Ψ. Para pronosticar un partido futuro:
1. lee la evidencia COMPLETA en una transacción de solo lectura (`datos.lectura.leer_todo`);
2. la convierte en el mismo conjunto punto-en-el-tiempo que se usó para entrenar y evaluar (`exportar_pit.construir`),
   pasado por Parquet en memoria para que los tipos sean idénticos a los del walk-forward;
3. corre el MISMO filtro (R) y la pieza P que `ops/evaluar_wf.py` y toma, para cada partido pedido, π, Var(ρ) y Ŝ.

No hay valores por omisión: si el partido no se puede pronosticar (jugador sin historia ni ranking, superficie o formato
desconocido, fuera de la exportación...), se devuelve el motivo y el motor no sella (plan D.6: nunca un promedio silencioso).
El corte de cada partido es el de la exportación (inicio programado − 60 min), que es también el del sellado en vivo.
"""
from __future__ import annotations

import io
import math
from datetime import date
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from tenis.datos import exportar_pit as xp
from tenis.datos.lectura import leer_todo
from tenis.modelo import datos as dm
from tenis.modelo import tabla
from tenis.modelo.parametros import Psi
from tenis.modelo.puntos import PsiP, filtrar_p, observaciones
from tenis.modelo.rating import filtrar
from tenis.modelo.rating_completo import filtrar_completo

# Ventana de la exportación con la que se ajustó y evaluó el modelo (`exportar_pit_cli.py --desde 2005-01-01`). El filtro
# parte de 2005; con más historia las probabilidades cambiarían (medido: hasta 0,045), así que se usa la misma ventana.
DESDE_EXPORTACION = date(2005, 1, 1)

COLUMNAS_SALIDA = ["partido_key", "partido_id_tml", "partido_id_sofascore", "jugador_1", "jugador_2", "fmt", "pi", "var_rho",
                   "s_hat", "motivo", "prior_ranking", "historia_corta", "fatiga_desconocida"]


def _por_parquet(df: pd.DataFrame) -> pd.DataFrame:
    """Mismos tipos que al leer los ficheros de la exportación (la ruta validada)."""
    buf = io.BytesIO()
    pq.write_table(xp._tabla_arrow(df), buf)
    buf.seek(0)
    return pd.read_parquet(buf)


def _flotante(serie: pd.Series):
    """Ids con posibles nulos → float con NaN (las comparaciones con un id entero nunca dan NA)."""
    return pd.to_numeric(serie, errors="coerce").astype("Float64").to_numpy(dtype="float64", na_value=float("nan"))


def conjunto_desde_db(db: Any) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(partidos, eventos_resultado, estadisticas_saque) del estado actual de la base, solo lectura."""
    with db.transaction():
        db.execute("SET TRANSACTION READ ONLY")
        db.execute("SET LOCAL TIME ZONE 'UTC'")
        tablas = leer_todo(db)
        tablas["sin_resolver_conteo"] = {f"{f}:{m}": n for f, m, n in db.execute(
            "SELECT fuente, motivo, count(*) FROM sin_resolver GROUP BY 1, 2 ORDER BY 1, 2").fetchall()}
    salidas = xp.construir(tablas, DESDE_EXPORTACION)
    return tuple(_por_parquet(salidas[k]) for k in ("partidos", "eventos_resultado", "estadisticas_saque"))


def pronosticar_circuito(p: pd.DataFrame, e: pd.DataFrame, stats: pd.DataFrame, cfg: dict, circuito: str) -> pd.DataFrame:
    """Filtro R + pieza P con Ψ congelado sobre TODO el conjunto del circuito. Una fila por partido (orden de la exportación)."""
    d = dm.preparar(p, e, circuito, 9999)
    if d.p.empty:
        return pd.DataFrame(columns=COLUMNAS_SALIDA)
    psi = Psi.desde_dict(cfg["psi_r"])
    tabs = tabla.construir_todas(tuple(cfg["lbar"]), psi.sigma_eps, psi.rho_eps)
    fil = filtrar_completo if cfg.get("filtro") == "covarianza_completa" else filtrar
    sal = fil(d, psi, tabs)
    psip = PsiP(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in cfg["psi_p"].items()})
    _, s_hat, _ = filtrar_p(d, observaciones(d, stats), psip)
    q = d.p
    return pd.DataFrame({
        "partido_key": q.partido_key.to_numpy(), "partido_id_tml": _flotante(q.partido_id_tml),
        "partido_id_sofascore": _flotante(q.partido_id_sofascore), "jugador_1": q.jugador_1.to_numpy(),
        "jugador_2": q.jugador_2.to_numpy(), "fmt": q.fmt.to_numpy(), "pi": sal.pi, "var_rho": sal.var_rho,
        "s_hat": s_hat, "motivo": sal.motivo, "prior_ranking": sal.prior1 | sal.prior2,
        "historia_corta": (q.n_prev_1.fillna(0) < 20).to_numpy() | (q.n_prev_2.fillna(0) < 20).to_numpy(),
        "fatiga_desconocida": sal.fat_desc})


def _fila(pron: pd.DataFrame, partido_id: int):
    for col in ("partido_id_sofascore", "partido_id_tml"):
        sel = pron[pron[col] == partido_id]
        if len(sel):
            return sel.iloc[0]
    return None


def resolver(pron: pd.DataFrame, partido: dict) -> dict:
    """Resultado para UN partido de la base (orientado como `partido.jugador_1`), o el motivo por el que no se puede."""
    fila = _fila(pron, partido["partido_id"])
    if fila is None:
        return {"ok": False, "motivo": "fuera_de_la_exportacion"}
    if fila.motivo:
        return {"ok": False, "motivo": str(fila.motivo)}
    if {int(fila.jugador_1), int(fila.jugador_2)} != {int(partido["jugador_1"]), int(partido["jugador_2"])}:
        return {"ok": False, "motivo": "jugadores_no_coinciden"}
    if not (math.isfinite(fila.pi) and math.isfinite(fila.var_rho)):
        return {"ok": False, "motivo": "pi_no_finito"}
    if not math.isfinite(fila.s_hat):
        return {"ok": False, "motivo": "sin_s_hat"}
    pi = float(fila.pi) if int(fila.jugador_1) == int(partido["jugador_1"]) else 1.0 - float(fila.pi)   # la exportación orienta los lados al azar
    return {"ok": True, "motivo": None, "pi_lado1": pi, "var_rho": float(fila.var_rho), "s_hat": float(fila.s_hat),
            "fmt": int(fila.fmt), "prior_ranking": bool(fila.prior_ranking), "historia_corta": bool(fila.historia_corta),
            "fatiga_desconocida": bool(fila.fatiga_desconocida), "partido_key": str(fila.partido_key)}


def inferir(db: Any, parametros: dict, partidos: list[dict]) -> dict[int, dict]:
    """partido_id → resultado de `resolver`. Una sola lectura de la base y un filtro por circuito presente."""
    if not partidos:
        return {}
    p, e, stats = conjunto_desde_db(db)
    out: dict[int, dict] = {}
    for circ in sorted({x["circuito"].lower() for x in partidos}):
        grupo = [x for x in partidos if x["circuito"].lower() == circ]
        cfg = (parametros.get("circuitos") or {}).get(circ)
        if not cfg or "psi_r" not in cfg or "psi_p" not in cfg or "lbar" not in cfg:
            out.update({x["partido_id"]: {"ok": False, "motivo": "sin_parametros_del_circuito"} for x in grupo})
            continue
        pron = pronosticar_circuito(p, e, stats, cfg, circ)
        out.update({x["partido_id"]: resolver(pron, x) for x in grupo})
    return out
