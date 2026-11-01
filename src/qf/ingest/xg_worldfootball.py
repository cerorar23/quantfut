"""
xG desde los datasets precompilados de worldfootballR_data. Gratis y sin
pelear contra Cloudflare.

POR QUÉ NO RASPAR FBREF
-----------------------
FBref está detrás de Cloudflare y devuelve 403 ("Just a moment...") incluso
cuando `soccerdata` intenta evadirlo con un navegador automatizado. El módulo
que lo hacía (`xg_fbref.py`) se borró el 2026-09-24: como fuente operativa no
era fiable y su dependencia rompía `pip install`.

El repositorio público `JaseZiv/worldfootballR_data` publica los mismos datos
de FBref ya raspados, como ficheros adjuntos a sus releases de GitHub. Se
descargan por HTTPS normal, en segundos, sin bloqueos y sin clave.

QUÉ APORTA QUE NO TENÍAS
------------------------
El README da por perdido el xG de Liga MX, Brasileirão y Argentina ("no
tienen xG en las fuentes gratuitas"). Para Liga MX y Brasileirão eso ya NO es
cierto por esta vía: el dataset de tiros trae xG con cobertura casi total.
Argentina sigue fuera (solo existe en formato .rds, ver abajo).

FORMATO Y SUS LÍMITES
---------------------
Se usa el release `fb_match_shooting`, que trae un CSV por país con datos
TIRO A TIRO. El xG del partido se obtiene sumando el xG de los tiros de cada
equipo, que es exactamente como se construye el xG de equipo.

Lo que NO hay, por si alguien lo busca:
  - No hay Parquet. Los formatos publicados son .rds y .csv.
  - Los datasets se actualizan por lotes, así que la última fecha disponible
    va por detrás del presente. Sirven para ENTRENAR con histórico, no para
    cerrar el xG del partido de anoche.

ARGENTINA: SEGUNDA VÍA, CON MENOS DETALLE
------------------------------------------
Argentina no tiene fichero de tiros, así que durante un tiempo se dio por
perdida. Sí está en el release `match_results`, que da el xG YA AGREGADO por
partido (sin remates, sin PSxG, sin distancia), y solo en .rds. Antes eso
implicaba añadir `pyreadr` por una sola liga y no compensaba; desde que las
copas europeas obligan a esa dependencia de todos modos
(`ingest/uefa_cups.py`), el coste ya está pagado y la liga entra gratis.

Es la razón de que haya DOS rutas en este módulo: `ASSETS` (tiro a tiro, todo
el detalle) y `RDS_ASSETS` (solo el xG del partido). Lo que se pierde por esa
vía es real: sin remates no hay estado del partido (`ingest/game_state.py`) ni
PSxG, así que Argentina seguirá siendo la liga con menos features.

Es complementario, no sustituto: para el xG reciente hace falta otra vía.
"""
from __future__ import annotations

import io
import logging

import httpx
import pandas as pd

from ..db import execute, query
from ..normalize import match_team
from .salud import record_health

log = logging.getLogger(__name__)

BASE = ("https://github.com/JaseZiv/worldfootballR_data/releases/download/"
        "fb_match_shooting/{asset}")

RDS_BASE = ("https://github.com/JaseZiv/worldfootballR_data/releases/download/"
            "match_results/{asset}")

# Mapeo a los ficheros del release. Se mantiene aquí y no en la base porque es
# el nombre de un fichero de un proyecto externo, no un dato del negocio.
# ar.primera no aparece: no existe en CSV en ese repositorio (ver RDS_ASSETS).
ASSETS = {
    "gb.premier_league": "ENG_M_1st_match_shooting.csv",
    "es.laliga": "ESP_M_1st_match_shooting.csv",
    "it.serie_a": "ITA_M_1st_match_shooting.csv",
    "nl.eredivisie": "NED_M_1st_match_shooting.csv",
    "mx.liga_mx": "MEX_M_1st_match_shooting.csv",
    "br.serie_a": "BRA_M_1st_match_shooting.csv",
    "us.mls": "USA_M_1st_match_shooting.csv",
    "de.bundesliga": "GER_M_1st_match_shooting.csv",
    "fr.ligue_1": "FRA_M_1st_match_shooting.csv",
    "pt.primeira": "POR_M_1st_match_shooting.csv",
}

# Ligas sin fichero de tiros, que solo tienen el xG agregado del partido.
# Se intentan DESPUÉS de ASSETS y solo para las que no están ahí: cuando hay
# tiros, los tiros mandan (dan además remates, PSxG y distancia).
RDS_ASSETS = {
    "ar.primera": "ARG_match_results.rds",
}


def _download(asset: str) -> pd.DataFrame | None:
    url = BASE.format(asset=asset)
    try:
        with httpx.Client(timeout=300, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
        return pd.read_csv(io.BytesIO(r.content), low_memory=False)
    except Exception as exc:  # noqa: BLE001
        log.error("No se pudo descargar %s: %s", url, exc)
        return None


# Un remate cuenta como "a puerta" si entró o si lo paró el portero. FBref
# distingue 'Saved off Target' (parado pero iba fuera), que NO es a puerta, y
# 'Woodwork', que tampoco lo es según su propia definición de SoT.
ON_TARGET = {"Goal", "Saved"}

# Columnas que se derivan por equipo y partido, en el orden en que se escriben.
STATS = ["xg", "shots", "shots_target", "psxg", "shot_distance"]


def match_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega los datos tiro a tiro a estadísticas por partido y lado.

    Se agrupa por MatchURL, que es el identificador del partido en la fuente:
    agrupar por fecha y equipo fallaría en las dobles jornadas y en los
    aplazados que acaban jugándose el mismo día que otro del mismo equipo.

    Devuelve xG, remates, remates a puerta, PSxG y distancia media.
    """
    faltan = {"MatchURL", "Date", "Squad", "Home_Away", "xG"} - set(df.columns)
    if faltan:
        raise ValueError(f"El dataset no trae las columnas esperadas: {faltan}")

    d = df.copy()
    for col in ("xG", "PSxG", "Distance"):
        d[col] = pd.to_numeric(d[col], errors="coerce") if col in d.columns else pd.NA
    # Una fila sin xG no es un remate utilizable: se descarta antes de contar,
    # o el recuento de remates saldría inflado respecto al xG agregado.
    d = d[d["xG"].notna()]
    if d.empty:
        return pd.DataFrame(columns=["MatchURL", "Date", "home_team", "away_team"])

    d["_on_target"] = d["Outcome"].isin(ON_TARGET) if "Outcome" in d.columns else False

    agg = d.groupby(["MatchURL", "Date", "Squad", "Home_Away"], as_index=False).agg(
        xg=("xG", "sum"),
        shots=("xG", "size"),
        shots_target=("_on_target", "sum"),
        psxg=("PSxG", "sum"),
        shot_distance=("Distance", "mean"),
    )

    lados = []
    for lado, prefijo in (("Home", "home"), ("Away", "away")):
        sub = agg[agg["Home_Away"] == lado].rename(
            columns={"Squad": f"{prefijo}_team",
                     **{s: f"{prefijo}_{s}" for s in STATS}})
        cols = ["MatchURL", f"{prefijo}_team"] + [f"{prefijo}_{s}" for s in STATS]
        if lado == "Home":
            cols.insert(1, "Date")
        lados.append(sub[cols])

    out = lados[0].merge(lados[1], on="MatchURL", how="inner")
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    return out.dropna(subset=["Date"])


def ingest_league(league_id: str, asset: str | None = None) -> dict:
    asset = asset or ASSETS.get(league_id)
    if not asset:
        return {"league": league_id, "skipped": "sin dataset en worldfootballR_data"}

    raw = _download(asset)
    if raw is None or raw.empty:
        return {"league": league_id, "error": "descarga vacía"}

    try:
        partidos = match_stats(raw)
    except ValueError as exc:
        return {"league": league_id, "error": str(exc)}

    actualizados = sin_emparejar = sin_partido = 0
    nombres_sueltos: set[str] = set()

    def _num(v):
        """NaN -> None, para que Postgres reciba NULL y no un NaN."""
        return None if v is None or v != v else float(v)

    for _, r in partidos.iterrows():
        hid, _, hs = match_team(str(r["home_team"]), "fbref", league_id)
        aid, _, as_ = match_team(str(r["away_team"]), "fbref", league_id)
        if not hid or not aid:
            sin_emparejar += 1
            if not hid:
                nombres_sueltos.add(str(r["home_team"]))
            if not aid:
                nombres_sueltos.add(str(r["away_team"]))
            continue

        # Ventana de +-1 día: la fuente guarda la fecha local del partido y
        # nuestro kickoff está en UTC, así que un partido nocturno puede caer
        # en el día anterior o posterior.
        #
        # COALESCE en tiros y córners: en las ligas del formato principal esas
        # columnas ya vienen de football-data y son el dato oficial; aquí solo
        # se rellenan donde estaban vacías (las tres latinoamericanas). El xG y
        # el PSxG sí se escriben siempre porque esta es su única fuente.
        n = execute(
            """UPDATE matches
               SET home_xg = %s, away_xg = %s,
                   home_psxg = %s, away_psxg = %s,
                   home_shot_distance = %s, away_shot_distance = %s,
                   home_shots = COALESCE(home_shots, %s),
                   away_shots = COALESCE(away_shots, %s),
                   home_shots_target = COALESCE(home_shots_target, %s),
                   away_shots_target = COALESCE(away_shots_target, %s),
                   xg_recorded_at = now()
               WHERE league_id = %s
                 AND home_team_id = %s AND away_team_id = %s
                 AND kickoff_utc::date BETWEEN %s::date - 1 AND %s::date + 1
                 AND home_xg IS NULL""",
            (_num(r["home_xg"]), _num(r["away_xg"]),
             _num(r["home_psxg"]), _num(r["away_psxg"]),
             _num(r["home_shot_distance"]), _num(r["away_shot_distance"]),
             int(r["home_shots"]), int(r["away_shots"]),
             int(r["home_shots_target"]), int(r["away_shots_target"]),
             league_id, hid, aid, r["Date"].date(), r["Date"].date()),
        )
        actualizados += n
        if n == 0:
            sin_partido += 1

    return {
        "league": league_id,
        "partidos_en_fuente": int(len(partidos)),
        "actualizados": actualizados,
        "sin_emparejar": sin_emparejar,
        "sin_partido_en_bd": sin_partido,
        # Se devuelven los nombres para poder darlos de alta como alias, que es
        # la diferencia entre "no hay datos" y "no supe emparejarlos".
        "nombres_sin_alias": sorted(nombres_sueltos)[:25],
    }


def ingest_league_rds(league_id: str, asset: str | None = None) -> dict:
    """
    xG por partido desde el release `match_results` (.rds).

    Solo escribe `home_xg`/`away_xg`: esa fuente no trae remates ni PSxG, así
    que no toca ninguna otra columna. Comparte con la vía de tiros la ventana
    de ±1 día y el `AND home_xg IS NULL`, de forma que si algún día apareciera
    el fichero de tiros de esa liga, se podrían correr las dos sin que esta
    pisara el dato más rico.
    """
    from .uefa_cups import fetch_rds

    asset = asset or RDS_ASSETS.get(league_id)
    if not asset:
        return {"league": league_id, "skipped": "sin dataset .rds"}

    raw = fetch_rds(RDS_BASE.format(asset=asset), asset)
    if raw is None or raw.empty:
        return {"league": league_id, "error": "descarga vacía"}

    df = raw.dropna(subset=["Home_xG", "Away_xG"])
    df = df[df["HomeGoals"].notna()]
    actualizados = sin_emparejar = sin_partido = 0
    nombres_sueltos: set[str] = set()

    for _, r in df.iterrows():
        fecha = pd.to_datetime(r["Date"], errors="coerce")
        if pd.isna(fecha):
            continue
        hid, _, _ = match_team(str(r["Home"]), "fbref", league_id)
        aid, _, _ = match_team(str(r["Away"]), "fbref", league_id)
        if not hid or not aid:
            sin_emparejar += 1
            if not hid:
                nombres_sueltos.add(str(r["Home"]))
            if not aid:
                nombres_sueltos.add(str(r["Away"]))
            continue

        n = execute(
            """UPDATE matches
               SET home_xg = %s, away_xg = %s, xg_recorded_at = now()
               WHERE league_id = %s
                 AND home_team_id = %s AND away_team_id = %s
                 AND kickoff_utc::date BETWEEN %s::date - 1 AND %s::date + 1
                 AND home_xg IS NULL""",
            (float(r["Home_xG"]), float(r["Away_xG"]),
             league_id, hid, aid, fecha.date(), fecha.date()),
        )
        actualizados += n
        if n == 0:
            sin_partido += 1

    return {"league": league_id, "fuente": "match_results.rds",
            "partidos_en_fuente": int(len(df)),
            "actualizados": actualizados,
            "sin_emparejar": sin_emparejar,
            "sin_partido_en_bd": sin_partido,
            "nombres_sin_alias": sorted(nombres_sueltos)[:25]}


def run() -> dict:
    ligas = query("SELECT league_id FROM leagues WHERE active AND model_enabled "
                  "ORDER BY league_id")
    resultados, total = [], 0
    for lg in ligas:
        lid = lg["league_id"]
        r = ingest_league(lid) if lid in ASSETS else ingest_league_rds(lid)
        resultados.append(r)
        total += r.get("actualizados", 0)

    cobertura = query(
        """SELECT league_id,
                  count(*) AS partidos,
                  count(home_xg) AS con_xg,
                  round(100.0 * count(home_xg) / NULLIF(count(*), 0), 1) AS pct
           FROM matches WHERE status = 'finished'
           GROUP BY league_id ORDER BY pct DESC NULLS LAST"""
    )
    record_health("worldfootballr_xg", total, True, {"results": resultados})
    log.info("xG worldfootballR: %d filas actualizadas", total)
    return {"total_actualizados": total, "por_liga": resultados,
            "cobertura": cobertura}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    res = run()
    print(f"\nActualizadas: {res['total_actualizados']} filas\n")
    print(f"{'liga':24s} {'partidos':>9s} {'con xG':>8s} {'%':>7s}")
    for c in res["cobertura"]:
        pct = c["pct"] if c["pct"] is not None else 0
        print(f"{c['league_id']:24s} {c['partidos']:9d} {c['con_xg']:8d} {pct:6.1f}%")
    sin_alias = {r["league"]: r.get("nombres_sin_alias")
                 for r in res["por_liga"] if r.get("nombres_sin_alias")}
    if sin_alias:
        print("\nNombres sin emparejar (dalos de alta como alias de 'fbref'):")
        for liga, nombres in sin_alias.items():
            print(f"  {liga}: {', '.join(nombres[:12])}")
