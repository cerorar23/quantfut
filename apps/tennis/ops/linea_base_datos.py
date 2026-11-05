# apps/tennis/ops/linea_base_datos.py
"""Carga Tennis-Data (ATP/WTA) -> tabla normalizada con liquidación de la casa de referencia.

Solo lectura. Sin red. Un faltante nunca vale 0 (NaN se conserva y el partido se excluye de lo que lo necesite).
Liquidación (regla de la casa de referencia, Pinnacle, tal como la fijó el titular en el encargo):
  - Walkover: sin acción -> excluido.
  - Retirada con >=1 set completado: el ganador del partido liquida; con 0 sets completados: anulado.
"""
from pathlib import Path
import re
import unicodedata
import numpy as np
import pandas as pd

RAIZ = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\tennis_data_manual")
COLS_ODDS = ["B365W", "B365L", "PSW", "PSL", "MaxW", "MaxL", "AvgW", "AvgL"]


def _archivos(circuito: str):
    carpeta = RAIZ / circuito.lower()
    for f in sorted(carpeta.glob("*.xls*")):
        m = re.match(r"(\d{4})", f.name)
        if m:
            yield int(m.group(1)), f


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", "", s.replace("-", "")).strip()


def clave_td(nombre: str):
    """'de Minaur A.' -> ('deminaur', 'a'). Homónimos con misma inicial NO se separan (límite conocido)."""
    partes = str(nombre).strip().split(" ")
    ini = partes[-1].replace(".", "")[:1].lower()
    ape = _norm("".join(partes[:-1]))
    return ape.replace(" ", ""), ini


def cargar(circuito: str, desde: int = 2005) -> pd.DataFrame:
    marcos = []
    for anio, f in _archivos(circuito):
        if anio < desde:
            continue
        d = pd.read_excel(f)
        d["archivo"] = f.name
        d["anio_archivo"] = anio
        marcos.append(d)
    d = pd.concat(marcos, ignore_index=True)
    d["circuito"] = circuito.upper()
    d = d.rename(columns={"Series": "nivel", "Tier": "nivel"})
    if "nivel" not in d:
        d["nivel"] = np.nan
    d["Date"] = pd.to_datetime(d["Date"])
    for c in COLS_ODDS + ["WRank", "LRank", "WPts", "LPts", "Wsets", "Lsets", "Best of"]:
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d else np.nan
    # Datos corruptos de cuota (<=1) se rechazan -> NaN, nunca 0.
    for c in COLS_ODDS:
        d.loc[d[c] <= 1.0, c] = np.nan
    comp = d["Comment"].fillna("").str.lower()
    sets_comp = d["Wsets"].fillna(0) + d["Lsets"].fillna(0)
    d["liquidable"] = ~comp.str.contains("walkover") & ~comp.str.contains("awarded") & (
        ~comp.str.contains("retired") | (sets_comp >= 1)
    )
    d["retirada"] = comp.str.contains("retired")
    d["walkover"] = comp.str.contains("walkover")
    d["indoor"] = d["Court"].fillna("").str.lower().eq("indoor")
    d["kw"] = d["Winner"].map(clave_td)
    d["kl"] = d["Loser"].map(clave_td)
    for i in range(1, 6):
        for p in "WL":
            if f"{p}{i}" in d:
                d[f"{p}{i}"] = pd.to_numeric(d[f"{p}{i}"], errors="coerce")
    d["games_total"] = sum(d[f"W{i}"].fillna(0) + d[f"L{i}"].fillna(0) for i in range(1, 6) if f"W{i}" in d)
    d["games_ok"] = d["liquidable"] & ~d["retirada"] & d["Comment"].fillna("").str.lower().eq("completed")
    d = d.sort_values(["Date", "Tournament", "Round"]).reset_index(drop=True)
    d["mid"] = np.arange(len(d))
    return d


def desvig_proporcional(oa: pd.Series, ob: pd.Series) -> pd.Series:
    """Probabilidad de A sin margen (proporcional). NaN si falta algún lado."""
    ia, ib = 1.0 / oa, 1.0 / ob
    return ia / (ia + ib)


def margen(oa: pd.Series, ob: pd.Series) -> pd.Series:
    return 1.0 / oa + 1.0 / ob - 1.0
