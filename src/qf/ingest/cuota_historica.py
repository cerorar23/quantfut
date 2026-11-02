"""
Cuotas HISTÓRICAS de fútbol (archivo de BetsAPI/bet365 y respaldo de API-Football) listas para `futbol.cuota_historica`.

No se escriben en `odds_snapshots` (ver `odds_history.py`): esa tabla es inmutable y alimenta el entrenamiento, el CLV y
la API sin filtrar por fuente en varias lecturas; meter ahí cuotas retroactivas cambiaría resultados ya medidos. La tabla
nueva guarda solo lo necesario para medir y reentrenar, no cada cambio de precio:

  BetsAPI (bet365, retroactiva): por partido y mercado, el primer precio prepartido (`apertura`), el último con ≥ 60 min
  de antelación (`t60`), el último antes del saque (`cierre`) y, en córners, la última lectura entre el minuto 65 y 70
  (`vivo_65_70`, con minuto, marcador y marcador de córners). Los cambios intermedios quedan en el archivo original del VPS.
  API-Football (10 casas, recepción real): primer snapshot (`apertura`), último con ≥ 60 min (`t60`) y último (`ultimo`).

Nombres de mercado como en `odds_snapshots` (h2h, spreads, totals, corners…); los de la 1.ª parte llevan sufijo `_1t`.
En el hándicap la línea es la de la propia selección (local h, visitante −h). Una línea de cuarto («9.5,10») se guarda
como su media (9,75) y el texto original en `linea_texto`.

    python -m qf.ingest.cuota_historica --raiz .local/betsapi_futbol --salida .local/betsapi_futbol/cuota_historica.csv.gz
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNAS = ["match_id", "fuente", "casa", "mercado", "seleccion", "linea", "linea_texto", "cuota", "momento", "precio_en",
            "recibido_en", "retroactiva", "minutos_al_saque", "minuto_juego", "marcador", "corners_vivo", "id_en_fuente"]

# mercado de BetsAPI → (mercado, columnas de cuota, selecciones)
MERCADOS_BETSAPI = {
    "1x2": ("h2h", ("home_od", "draw_od", "away_od"), ("home", "draw", "away")),
    "ah": ("spreads", ("home_od", "away_od"), ("home", "away")),
    "goles": ("totals", ("over_od", "under_od"), ("over", "under")),
    "corners": ("corners", ("over_od", "under_od"), ("over", "under")),
    "descanso": ("h2h_1t", ("home_od", "draw_od", "away_od"), ("home", "draw", "away")),
    "ah_1t": ("spreads_1t", ("home_od", "away_od"), ("home", "away")),
    "goles_1t": ("totals_1t", ("over_od", "under_od"), ("over", "under")),
    "corners_1t": ("corners_1t", ("over_od", "under_od"), ("over", "under")),
}
COLUMNAS_LEER = ["bid", "mercado", "t", "minuto", "marcador", "corners_vivo", "linea", "home_od", "draw_od", "away_od",
                 "over_od", "under_od"]


def linea_media(texto) -> float | None:
    """«9.5» → 9.5; «9.5,10» → 9.75; vacío o ilegible → None."""
    if texto is None or (isinstance(texto, float) and np.isnan(texto)) or str(texto).strip() == "":
        return None
    try:
        partes = [float(x) for x in str(texto).split(",")]
    except ValueError:
        return None
    return float(np.mean(partes))


def momentos_betsapi(ticks: pd.DataFrame, kickoff: pd.Series) -> pd.DataFrame:
    """Ticks elegidos con su `momento`; `kickoff` es bid → segundos unix. Un tick puede salir con dos momentos."""
    t = ticks.merge(kickoff.rename("kickoff"), left_on="bid", right_index=True)
    pre = t[t["minuto"].isna() & t["t"].notna() & (t["t"] < t["kickoff"])].sort_values(["bid", "mercado", "t"])
    g = pre.groupby(["bid", "mercado"])
    partes = [g.head(1).assign(momento="apertura"), g.tail(1).assign(momento="cierre"),
              pre[pre["t"] <= pre["kickoff"] - 3600].groupby(["bid", "mercado"]).tail(1).assign(momento="t60")]
    vivo = t[t["mercado"].eq("corners") & t["minuto"].between(65, 70)].sort_values(["bid", "t"])
    partes.append(vivo.groupby("bid").tail(1).assign(momento="vivo_65_70"))
    return pd.concat(partes, ignore_index=True)


def filas_betsapi(ticks: pd.DataFrame, kickoff: pd.Series, puente: pd.DataFrame) -> pd.DataFrame:
    """Una fila por selección de cada tick elegido, con las columnas de `COLUMNAS`."""
    m = momentos_betsapi(ticks, kickoff).merge(puente[["bid", "match_id"]], on="bid")
    salida = []
    for clave, (mercado, columnas, selecciones) in MERCADOS_BETSAPI.items():
        x = m[m["mercado"].eq(clave)]
        if x.empty:
            continue
        for col, sel in zip(columnas, selecciones):
            y = x[x[col].gt(1)]
            media = y["linea"].map(linea_media)
            if sel == "away" and mercado.startswith("spreads"):
                media = media.map(lambda v: None if v is None else -v)  # línea propia: visitante −h
            salida.append(pd.DataFrame({
                "match_id": y["match_id"].to_numpy(), "fuente": "betsapi", "casa": "bet365", "mercado": mercado, "seleccion": sel,
                "linea": media.to_numpy(), "linea_texto": y["linea"].astype("string").to_numpy() if clave not in ("1x2", "descanso") else None,
                "cuota": y[col].to_numpy(), "momento": y["momento"].to_numpy(),
                "precio_en": pd.to_datetime(y["t"], unit="s", utc=True).to_numpy(), "recibido_en": pd.NaT, "retroactiva": True,
                "minutos_al_saque": ((y["kickoff"] - y["t"]) / 60).round().astype("Int64").to_numpy(),
                "minuto_juego": y["minuto"].to_numpy(), "marcador": y["marcador"].to_numpy(),
                "corners_vivo": y["corners_vivo"].to_numpy(), "id_en_fuente": y["bid"].astype(str).to_numpy()}))
    f = pd.concat(salida, ignore_index=True)
    # las líneas de cuarto del hándicap/ totales guardan texto, y el 1X2 no tiene línea
    f.loc[f["mercado"].isin(["h2h", "h2h_1t"]), ["linea", "linea_texto"]] = None
    return f[COLUMNAS]


def filas_api_football(af: pd.DataFrame) -> pd.DataFrame:
    """Respaldo de API-Football (`af_odds.csv.gz`): primer snapshot, último con ≥ 60 min y último, por casa y opción."""
    a = af[af["price"].gt(1)].copy()
    a["linea_clave"] = a["line"].fillna(-999)
    a = a.sort_values(["match_id", "bookmaker", "market", "selection", "linea_clave", "fetched_at"])
    clave = ["match_id", "bookmaker", "market", "selection", "linea_clave"]
    g = a.groupby(clave)
    partes = [g.head(1).assign(momento="apertura"), g.tail(1).assign(momento="ultimo"),
              a[a["mins_to_kickoff"] >= 60].groupby(clave).tail(1).assign(momento="t60")]
    x = pd.concat(partes, ignore_index=True)
    return pd.DataFrame({
        "match_id": x["match_id"], "fuente": "api_football", "casa": x["bookmaker"], "mercado": x["market"],
        "seleccion": x["selection"], "linea": x["line"], "linea_texto": None, "cuota": x["price"], "momento": x["momento"],
        "precio_en": pd.to_datetime(x["provider_updated_at"], utc=True, errors="coerce"),
        "recibido_en": pd.to_datetime(x["fetched_at"], utc=True, errors="coerce"), "retroactiva": False,
        "minutos_al_saque": x["mins_to_kickoff"].astype("Int64"), "minuto_juego": np.nan, "marcador": None,
        "corners_vivo": None, "id_en_fuente": x["snapshot_id"].astype(str)})[COLUMNAS]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=".local/betsapi_futbol")
    ap.add_argument("--salida", default=".local/betsapi_futbol/cuota_historica.csv.gz")
    a = ap.parse_args()
    raiz = Path(a.raiz)
    ev = pd.read_csv(raiz / "eventos.csv.gz")
    puente = pd.read_csv(raiz / "puente.csv.gz")
    ticks = pd.read_csv(raiz / "ticks.csv.gz", usecols=COLUMNAS_LEER, low_memory=False)
    kickoff = ev.drop_duplicates("bid").set_index("bid")["kickoff"]
    bet = filas_betsapi(ticks, kickoff, puente)
    del ticks
    af = pd.read_csv(raiz / "af_odds.csv.gz", low_memory=False)
    afi = filas_api_football(af)
    todo = pd.concat([bet, afi], ignore_index=True)
    # varias lecturas con el mismo valor de la clave única de la tabla: se queda la primera
    todo["_lc"] = todo["linea"].fillna(-999)
    todo = todo.drop_duplicates(["fuente", "casa", "match_id", "mercado", "seleccion", "_lc", "momento"]).drop(columns="_lc")
    for c in ("precio_en", "recibido_en"):
        todo[c] = pd.to_datetime(todo[c], utc=True, errors="coerce")
    todo["minuto_juego"] = pd.to_numeric(todo["minuto_juego"], errors="coerce").astype("Int64")
    todo["minutos_al_saque"] = pd.to_numeric(todo["minutos_al_saque"], errors="coerce").astype("Int64")
    todo.to_csv(a.salida, index=False, date_format="%Y-%m-%d %H:%M:%S%z")
    print(f"BetsAPI {len(bet):,} filas, API-Football {len(afi):,}; tras quitar repetidas {len(todo):,}")
    print(todo.groupby(["fuente", "momento"]).size().to_string())
    print(todo.groupby(["fuente", "mercado"]).size().to_string())


if __name__ == "__main__":
    main()
