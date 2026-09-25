"""
Ingesta del histórico de football-data.co.uk (gratis, ~25 años).

Es la base estadística sobre la que se entrena el modelo de fuerza. Incluye
resultados, tiros, córners, tarjetas y cuotas de varias casas por partido.

Dos familias de archivos:
  - Principales (E0, SP1, I1, D1, F1, N1, P1, T1, G1, SC0...): columnas ricas,
    incluidas cuotas de cierre de varias casas.
  - "Extra" (MEX, ARG, BRA, USA...): menos columnas, sin datos de tiros.
    Liga MX vive aquí. Ténlo en cuenta: para esas ligas el modelo trabaja con
    goles, no con xG ni tiros, y debe ponderarse peor en el meta-learner.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd

from ..db import execute, query_one
from ..normalize import register_alias, resolve_team, slugify

log = logging.getLogger(__name__)

BASE_MAIN = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
BASE_EXTRA = "https://www.football-data.co.uk/new/{code}.csv"

# Cuotas de cierre por casa: prioridad para el baseline de mercado
CLOSING_COLS = [
    ("PSCH", "PSCD", "PSCA", "pinnacle"),
    ("B365CH", "B365CD", "B365CA", "bet365"),
    ("MaxCH", "MaxCD", "MaxCA", "market_max"),
    ("AvgCH", "AvgCD", "AvgCA", "market_avg"),
    ("PSH", "PSD", "PSA", "pinnacle"),
    ("B365H", "B365D", "B365A", "bet365"),
    ("AvgH", "AvgD", "AvgA", "market_avg"),
]


def _fetch_csv(url: str) -> pd.DataFrame | None:
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
        return pd.read_csv(io.BytesIO(r.content), encoding="latin-1",
                           on_bad_lines="skip")
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo descargar %s: %s", url, exc)
        return None


def _parse_date(row) -> datetime | None:
    d = str(row.get("Date", "")).strip()
    t = str(row.get("Time", "")).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(d, fmt)
            break
        except ValueError:
            continue
    else:
        return None
    if t and ":" in t:
        try:
            hh, mm = t.split(":")[:2]
            dt = dt.replace(hour=int(hh), minute=int(mm))
        except ValueError:
            dt = dt.replace(hour=19)
    else:
        # Sin hora: se marca a las 19:00 UTC. El backtest debe saber que el
        # orden intra-jornada es arbitrario (ver check_leakage).
        dt = dt.replace(hour=19)
    return dt.replace(tzinfo=timezone.utc)


# Los dos formatos de football-data.co.uk NO comparten nombres de columna.
# Leer el "extra" con los nombres del principal devuelve None en cada fila y la
# liga entera se carga vacía sin dar ningún error.
COLS_MAIN = {"home": "HomeTeam", "away": "AwayTeam", "hg": "FTHG", "ag": "FTAG",
             "hg_ht": "HTHG", "ag_ht": "HTAG", "hs": "HS", "as": "AS",
             "hst": "HST", "ast": "AST", "hc": "HC", "ac": "AC"}
# El extra solo trae resultado y cuotas: ni tiros, ni córners, ni descanso.
COLS_EXTRA = {"home": "Home", "away": "Away", "hg": "HG", "ag": "AG",
              "hg_ht": None, "ag_ht": None, "hs": None, "as": None,
              "hst": None, "ast": None, "hc": None, "ac": None}


def season_labels_extra(season: str) -> tuple[str, str]:
    """
    Etiquetas posibles de la columna Season del formato extra para '2526'.

    No hay un solo formato: las ligas de temporada europea lo escriben
    '2025/2026' y las de año natural (Brasil siempre; Argentina desde que
    cambió de formato) lo escriben '2025' a secas. El propio ARG.csv contiene
    LAS DOS formas en el mismo fichero según el año, así que hay que aceptar
    ambas o se pierden temporadas enteras en silencio.
    """
    return (f"20{season[:2]}/20{season[2:]}", f"20{season[:2]}")


def _ensure_team(league_id: str, raw_name: str) -> int | None:
    """
    football-data.co.uk es la fuente CANÓNICA: un nombre que no reconoce es un
    equipo nuevo legítimo y se da de alta.

    El alta se cierra con `register_alias` y no con un INSERT a mano. Da lo
    mismo para la tabla de alias, pero no para `unresolved_names`: cada nombre
    nuevo pasa antes por `resolve_team`, que lo registra ahí como pendiente, y
    solo `register_alias` lo marca resuelto. Con el INSERT directo esas filas
    se quedaban pendientes PARA SIEMPRE aunque el equipo existiera ya y todo
    hubiera funcionado. El chequeo de salud acababa reportando 362 nombres sin
    emparejar —todos fantasmas, casi todos de la MLS— y recomendando
    `bootstrap_aliases.py`, que ni siquiera toca la fuente football_data.
    Una alarma permanentemente en rojo es una alarma que nadie lee.
    """
    canonical = resolve_team(raw_name, "football_data")
    if canonical is None:
        canonical = raw_name.strip()
        execute(
            """INSERT INTO teams (league_id, canonical_name) VALUES (%s, %s)
               ON CONFLICT (league_id, canonical_name) DO NOTHING""",
            (league_id, canonical),
        )
    row = query_one(
        "SELECT team_id FROM teams WHERE league_id = %s AND canonical_name = %s",
        (league_id, canonical),
    )
    if row:
        register_alias(raw_name.strip(), "football_data", row["team_id"])
    return row["team_id"] if row else None


def _ingest_rows(league_id: str, season: str, df, cols: dict) -> int:
    """Inserta las filas de un DataFrame ya filtrado a una temporada."""
    inserted = 0
    for _, row in df.iterrows():
        home_raw, away_raw = row.get(cols["home"]), row.get(cols["away"])
        if not isinstance(home_raw, str) or not isinstance(away_raw, str):
            continue
        ko = _parse_date(row)
        if ko is None:
            continue

        hid = _ensure_team(league_id, home_raw)
        aid = _ensure_team(league_id, away_raw)
        if not hid or not aid:
            continue

        match_id = (f"{league_id}:{season}:"
                    f"{slugify(home_raw)[:12].replace(' ', '')}-"
                    f"{slugify(away_raw)[:12].replace(' ', '')}:"
                    f"{ko.strftime('%Y%m%d')}")

        def _n(key, cast=int):
            col = cols.get(key)
            if col is None:
                return None
            v = row.get(col)
            try:
                return cast(v) if pd.notna(v) else None
            except (ValueError, TypeError):
                return None

        if _n("hg") is None or _n("ag") is None:
            continue    # partido futuro o sin resultado en el CSV

        # ¿Ya existe este partido? Cubre dos casos con la misma consulta:
        #  - lo creó el calendario de API-Football, con otra etiqueta de
        #    temporada ('2026A', '2026') y otros nombres, así que el match_id
        #    no coincide y el ON CONFLICT no lo frena;
        #  - es una recarga del propio histórico.
        # En ambos hay que saltar la fila ENTERA: las cuotas de cierre de abajo
        # no tienen clave única y odds_snapshots no admite DELETE, un duplicado
        # ahí es para siempre. ±36 h porque el CSV da hora del Reino Unido (o
        # ninguna) y API-Football da UTC.
        if query_one(
            """SELECT 1 AS x FROM matches
               WHERE league_id = %s AND home_team_id = %s AND away_team_id = %s
                 AND kickoff_utc BETWEEN %s AND %s""",
            (league_id, hid, aid, ko - timedelta(hours=36), ko + timedelta(hours=36)),
        ):
            continue

        execute(
            """INSERT INTO matches
                 (match_id, league_id, season, kickoff_utc, home_team_id,
                  away_team_id, status, home_goals, away_goals,
                  home_goals_ht, away_goals_ht, home_shots, away_shots,
                  home_shots_target, away_shots_target, home_corners, away_corners,
                  result_recorded_at)
               VALUES (%s,%s,%s,%s,%s,%s,'finished',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id) DO NOTHING""",
            (match_id, league_id, season, ko, hid, aid,
             _n("hg"), _n("ag"), _n("hg_ht"), _n("ag_ht"),
             _n("hs"), _n("as"), _n("hst"), _n("ast"),
             _n("hc"), _n("ac"), ko),
        )

        # Cuotas históricas -> snapshots marcados como cierre
        for ch, cd, ca, book in CLOSING_COLS:
            if all(c in row and pd.notna(row[c]) for c in (ch, cd, ca)):
                for sel, col in (("home", ch), ("draw", cd), ("away", ca)):
                    try:
                        price = float(row[col])
                    except (ValueError, TypeError):
                        continue
                    if price <= 1.0:
                        continue
                    execute(
                        """INSERT INTO odds_snapshots
                             (match_id, bookmaker, market, selection, line, price,
                              captured_at, mins_to_kickoff, window_tag, source)
                           VALUES (%s,%s,'h2h',%s,NULL,%s,%s,0,'close','football_data')""",
                        (match_id, book, sel, price, ko),
                    )
                break  # solo la primera familia de columnas disponible

        inserted += 1

    return inserted


def ingest_season(league_id: str, fd_code: str, season: str) -> int:
    """Una temporada del formato PRINCIPAL (un CSV por liga y temporada)."""
    df = _fetch_csv(BASE_MAIN.format(season=season, code=fd_code))
    if df is None or df.empty:
        return 0
    n = _ingest_rows(league_id, season, df, COLS_MAIN)
    log.info("%s %s: %d partidos", league_id, season, n)
    return n


def ingest_extra(league_id: str, fd_code: str, seasons: list[str]) -> int:
    """
    Formato EXTRA (Liga MX, Argentina, Brasil): un único CSV con TODO el
    histórico, columnas distintas y temporada escrita como '2025/2026'.

    Se descarga una sola vez y se recorren todas las temporadas pedidas. Antes
    esto cargaba una sola temporada, buscaba '2526' dentro de '2025/2026' —que
    no casa nunca— y encima leía nombres de columna del otro formato, así que
    las tres ligas latinoamericanas se quedaban a cero sin dar ningún error.
    """
    df = _fetch_csv(BASE_EXTRA.format(code=fd_code))
    if df is None or df.empty:
        return 0
    if "Season" not in df.columns:
        log.warning("%s: el CSV extra no trae columna Season", league_id)
        return 0

    etiquetas = df["Season"].astype(str)
    total = 0
    for s in seasons:
        sub = df[etiquetas.isin(season_labels_extra(s))]
        if sub.empty:
            continue
        n = _ingest_rows(league_id, s, sub, COLS_EXTRA)
        log.info("%s %s: %d partidos", league_id, s, n)
        total += n
    if total == 0:
        log.warning("%s: 0 partidos de %d temporadas. Etiquetas disponibles: %s",
                    league_id, len(seasons), sorted(etiquetas.unique())[-5:])
    return total


def default_seasons(now: datetime | None = None) -> list[str]:
    """
    De 2014/15 hasta la temporada que empieza en el año en curso, incluida.

    Antes era un rango fijo que acababa en 2025/26: la temporada en curso no se
    cargaba nunca y, como `fixtures` solo crea partidos futuros, lo jugado antes
    del primer calendario no existía en siete ligas. Se llega hasta el año en
    curso y no hasta la temporada europea en curso porque Brasil y Argentina
    etiquetan '2026' la que ya juegan en mayo, y eso solo casa con '2627'. En
    enero-junio el CSV principal de esa temporada aún no existe: 404 avisado y
    0 partidos, sin más.
    """
    now = now or datetime.now(timezone.utc)
    return [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(2014, now.year + 1)]


def backfill(seasons: list[str] | None = None) -> dict:
    """Carga inicial. Ejecutar una vez al montar el sistema."""
    from ..db import query

    seasons = seasons or default_seasons()
    leagues = query("SELECT league_id, fd_code, fd_extra FROM leagues "
                    "WHERE fd_code IS NOT NULL AND active")
    total = {}
    for lg in leagues:
        if lg["fd_extra"]:
            n = ingest_extra(lg["league_id"], lg["fd_code"], seasons)
        else:
            n = sum(ingest_season(lg["league_id"], lg["fd_code"], s)
                    for s in seasons)
        total[lg["league_id"]] = n
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(backfill())
