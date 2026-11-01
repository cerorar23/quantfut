"""
Histórico de Champions League y Europa League desde worldfootballR_data.

POR QUÉ ESTE FORMATO Y NO CSV
------------------------------
Las copas europeas NO están en football-data.co.uk, que solo cubre ligas
domésticas, ni en el release `fb_match_shooting` que usa `xg_worldfootball.py`.
La única fuente gratuita es el release `match_results_cups`, y ahí solo hay
.rds (serialización de R): se comprobó que ese release no publica ni un solo
fichero .csv. Leerlo obliga a `pyreadr`, deuda que hasta ahora se había
rechazado por una liga suelta (Argentina) y que aquí sí se paga: son dos
competiciones y además traen xG por partido.

QUÉ ENTRA Y QUÉ NO
------------------
Entra: resultado, xG de los dos equipos, árbitro, sede, asistencia.
NO entra: ninguna cuota. Ni de apertura ni de cierre, ni de una sola casa.

Esa ausencia decide cómo se usan estos partidos. Sin cuotas de cierre no hay
baseline de mercado, así que no se pueden evaluar (`eval/metrics.py` compara
contra el mercado), ni calibrar, ni medir CLV, ni estimar el peso
modelo/mercado. Son datos de ENTRENAMIENTO. Que la Champions sea apostable
depende de que `odds_worker` acumule cierres propios vía The Odds API
(`soccer_uefa_champs_league`), no de este módulo.

POR QUÉ SÍ VALEN LA PENA AUNQUE NO SE APUESTEN
-----------------------------------------------
Son los ÚNICOS partidos que enfrentan equipos de ligas distintas. El modelo de
fuerza impone suma cero de ataque y defensa dentro de cada liga, así que un
ataque de 0,3 en Eredivisie y uno de 0,3 en LaLiga no están en la misma
escala: no hay nada en los datos domésticos que las conecte. Estos partidos
son la única información que identifica esa diferencia
(`model/dixon_coles.py`, término `strength`).

NUNCA SE CREAN EQUIPOS AQUÍ
----------------------------
Un partido cuyos dos equipos no estén ya en el catálogo se descarta. Dar de
alta equipos bajo `league_id='eu.ucl'` crearía un Real Madrid de Champions
distinto del de LaLiga, con una docena de partidos y ningún rival común: el
modelo no aprendería nada y el término `strength` se quedaría sin identificar,
que es justo lo contrario de para lo que se ingestan.
"""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone

import httpx
import pandas as pd

from ..db import execute, query
from ..normalize import match_team, slugify
from .salud import record_health

log = logging.getLogger(__name__)

BASE = ("https://github.com/JaseZiv/worldfootballR_data/releases/download/"
        "match_results_cups/{asset}")

# Códigos de país de FBref -> liga doméstica del catálogo. Un partido con un
# equipo de un país que no esté aquí se descarta: no es que falte el dato, es
# que esa liga no está dada de alta y no tenemos a sus equipos.
#
# Cada entrada nueva vale partidos de copa, que es lo escaso: `de`, `fr` y
# `pt` se añadieron justo por eso (db/010_ligas_europeas.sql). Los que siguen
# fuera y más pesan: be (264), ru (252), tr (230), ua (235), gr (180).
COUNTRY_LEAGUE = {
    "eng": "gb.premier_league",
    "es": "es.laliga",
    "it": "it.serie_a",
    "nl": "nl.eredivisie",
    "de": "de.bundesliga",
    "fr": "fr.ligue_1",
    "pt": "pt.primeira",
    "us": "us.mls",
}

# FBref pega el país al nombre, y de forma distinta según el lado:
#   local    -> 'Girona es', 'Bayern Munich de'
#   visitante-> 'eng Arsenal', 'sk Slovan Bratislava'
# El código es siempre minúscula, y los nombres van en mayúscula inicial, así
# que exigir minúsculas basta para no morder un trozo del nombre.
_SUFIJO = re.compile(r"^(.*?)\s+([a-z]{2,3})$")
_PREFIJO = re.compile(r"^([a-z]{2,3})\s+(.*)$")


def split_country(raw: str, side: str) -> tuple[str | None, str]:
    """Devuelve (código_país, nombre) de un nombre de FBref con país pegado."""
    s = str(raw).strip()
    m = _SUFIJO.match(s) if side == "home" else _PREFIJO.match(s)
    if not m:
        return None, s
    return (m.group(2), m.group(1)) if side == "home" else (m.group(1), m.group(2))


def season_label(season_end_year: int) -> str:
    """2016 -> '1516', igual que el resto del sistema."""
    y = int(season_end_year)
    return f"{(y - 1) % 100:02d}{y % 100:02d}"


def fetch_rds(url: str, asset: str) -> pd.DataFrame | None:
    """
    Descarga un .rds de worldfootballR_data y lo devuelve como DataFrame.

    Vive aquí y no en `xg_worldfootball` porque este es el módulo que obliga a
    `pyreadr`; el de xG lo reutiliza para Argentina, que es la única liga sin
    fichero de tiros.
    """
    try:
        import pyreadr
    except ImportError as exc:
        log.error("Falta pyreadr (pip install -r requirements.txt): %s", exc)
        return None

    try:
        with httpx.Client(timeout=300, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
        # pyreadr solo lee de disco, no de memoria.
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / asset
            p.write_bytes(r.content)
            data = pyreadr.read_r(str(p))
        return next(iter(data.values()))
    except Exception as exc:  # noqa: BLE001
        log.error("No se pudo leer %s: %s", url, exc)
        return None


def _download(asset: str) -> pd.DataFrame | None:
    return fetch_rds(BASE.format(asset=asset), asset)


def _kickoff(row) -> datetime | None:
    d = pd.to_datetime(row.get("Date"), errors="coerce")
    if pd.isna(d):
        return None
    hh, mm = 19, 0
    t = str(row.get("Time") or "").strip()
    if ":" in t:
        try:
            hh, mm = int(t.split(":")[0]), int(t.split(":")[1][:2])
        except ValueError:
            hh, mm = 19, 0
    # La fuente da la hora local de la sede; se trata como UTC igual que en
    # history_fd. Para el decaimiento temporal y el orden del walk-forward un
    # desfase de 1-2 horas es irrelevante.
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=timezone.utc)


def _num(v):
    return None if v is None or pd.isna(v) else float(v)


def ingest_competition(league_id: str, asset: str,
                       since_season_end: int = 2015) -> dict:
    """Carga una competición. Devuelve el recuento y por qué se descartó cada fila."""
    raw = _download(asset)
    if raw is None or raw.empty:
        return {"competition": league_id, "error": "descarga vacía"}

    faltan = {"Season_End_Year", "Date", "Home", "Away",
              "HomeGoals", "AwayGoals"} - set(raw.columns)
    if faltan:
        return {"competition": league_id, "error": f"faltan columnas: {faltan}"}

    df = raw[raw["Season_End_Year"] >= since_season_end]
    df = df.dropna(subset=["HomeGoals", "AwayGoals"])

    insertados = 0
    fuera_de_catalogo = sin_resolver = sin_fecha = 0
    paises_descartados: dict[str, int] = {}
    nombres_sueltos: set[str] = set()

    for _, r in df.iterrows():
        pais_h, nombre_h = split_country(r["Home"], "home")
        pais_a, nombre_a = split_country(r["Away"], "away")
        liga_h = COUNTRY_LEAGUE.get(pais_h or "")
        liga_a = COUNTRY_LEAGUE.get(pais_a or "")
        if not liga_h or not liga_a:
            fuera_de_catalogo += 1
            for p in (pais_h, pais_a):
                if p and p not in COUNTRY_LEAGUE:
                    paises_descartados[p] = paises_descartados.get(p, 0) + 1
            continue

        # Se restringe la búsqueda a la liga doméstica del equipo. Buscar en
        # todo el catálogo emparejaría 'Barcelona' con el Barcelona ecuatoriano
        # o 'Santos' con el brasileño, y un equipo mal emparejado contamina dos
        # historiales a la vez sin dar ningún error.
        hid, _, _ = match_team(nombre_h, "fbref", liga_h)
        aid, _, _ = match_team(nombre_a, "fbref", liga_a)
        if not hid or not aid:
            sin_resolver += 1
            if not hid:
                nombres_sueltos.add(f"{liga_h}: {nombre_h}")
            if not aid:
                nombres_sueltos.add(f"{liga_a}: {nombre_a}")
            continue

        ko = _kickoff(r)
        if ko is None:
            sin_fecha += 1
            continue

        season = season_label(r["Season_End_Year"])
        match_id = (f"{league_id}:{season}:"
                    f"{slugify(nombre_h)[:12].replace(' ', '')}-"
                    f"{slugify(nombre_a)[:12].replace(' ', '')}:"
                    f"{ko.strftime('%Y%m%d')}")

        hxg, axg = _num(r.get("Home_xG")), _num(r.get("Away_xG"))
        # El sello de xG se decide en Python, no con un CASE en SQL: psycopg no
        # puede inferir el tipo de un parámetro suelto dentro de `IS NULL` y
        # aborta con IndeterminateDatatype (mismo motivo que los casts de
        # model/train.py). Se marca con el kickoff, no con now(): el xG de esta
        # fuente es histórico, y poner now() haría saltar check_leakage.
        n = execute(
            """INSERT INTO matches
                 (match_id, league_id, season, kickoff_utc, home_team_id,
                  away_team_id, status, home_goals, away_goals,
                  home_xg, away_xg, result_recorded_at, xg_recorded_at)
               VALUES (%s,%s,%s,%s,%s,%s,'finished',%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id) DO NOTHING""",
            (match_id, league_id, season, ko, hid, aid,
             int(r["HomeGoals"]), int(r["AwayGoals"]),
             hxg, axg, ko, ko if hxg is not None else None),
        )
        insertados += n

    return {
        "competition": league_id,
        "partidos_en_fuente": int(len(df)),
        "insertados": insertados,
        "descartados_liga_no_dada_de_alta": fuera_de_catalogo,
        "descartados_sin_resolver": sin_resolver,
        "descartados_sin_fecha": sin_fecha,
        # Cuántos partidos se pierden por cada país que no tenemos. Es la
        # cifra que dice si compensa dar de alta la Bundesliga o la Ligue 1.
        "paises_no_dados_de_alta": dict(sorted(paises_descartados.items(),
                                               key=lambda kv: -kv[1])[:12]),
        "nombres_sin_alias": sorted(nombres_sueltos)[:25],
    }


def run(since_season_end: int = 2015) -> dict:
    comps = query("SELECT league_id, rds_asset FROM leagues "
                  "WHERE cross_league AND rds_asset IS NOT NULL AND active "
                  "ORDER BY league_id")
    resultados, total = [], 0
    for c in comps:
        r = ingest_competition(c["league_id"], c["rds_asset"], since_season_end)
        resultados.append(r)
        total += r.get("insertados", 0)
    record_health("uefa_cups", total, True, {"results": resultados})
    return {"total_insertados": total, "por_competicion": resultados}


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    print(json.dumps(run(), indent=2, ensure_ascii=False))
