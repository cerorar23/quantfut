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
from ..normalize import (
    _record_unresolved,
    clasificar_historial,
    clear_cache,
    match_team,
    register_alias,
    resolve_team,
    slugify,
)
from .estadisticas import arbitro

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
    """
    UTF-8 si el archivo lo es y latin-1 si no. Los CSV antiguos son latin-1,
    pero algunos recientes vienen en UTF-8 y leídos como latin-1 daban
    'PreuÃ\x9fen MÃ¼nster' como nombre de equipo nuevo (ensayo del 2026-10-11).
    Ningún alias guardado tenía ese texto roto: el cambio no afecta a lo cargado.
    """
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as c:
            r = c.get(url)
            r.raise_for_status()
        try:
            return pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")),
                               on_bad_lines="skip")
        except UnicodeDecodeError:
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


PINNACLE_CIERRE = ("PSCH", "PSCD", "PSCA")


def ternas_pinnacle(df: pd.DataFrame, cols: dict, desde: datetime) -> list[dict]:
    """Filas del CSV con la terna de cierre de Pinnacle completa y válida, desde `desde`."""
    import math

    if not set(PINNACLE_CIERRE) <= set(df.columns):
        return []
    out = []
    for _, row in df.iterrows():
        home, away = row.get(cols["home"]), row.get(cols["away"])
        ko = _parse_date(row)
        if ko is None or ko < desde or not isinstance(home, str) or not isinstance(away, str):
            continue
        try:
            precios = [float(row[c]) for c in PINNACLE_CIERRE]
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(p) and p > 1.0 for p in precios):
            continue
        out.append({"home": home, "away": away, "ko": ko,
                    "price": dict(zip(("home", "draw", "away"), precios))})
    return out


def insertar_cierre(c, match_id: str, kickoff, precios: dict, captured_at=None,
                    book_updated_at=None, source: str = "football_data") -> int:
    """
    Inserta la terna 1X2 de cierre de Pinnacle de un partido, salvo que ya tenga un cierre de
    Pinnacle de cualquier fuente: la comprobación va DENTRO del INSERT porque `odds_snapshots`
    no admite DELETE y dos ejecuciones no deben pisarse. Devuelve las filas insertadas (0 o 3).
    """
    captured_at = captured_at or kickoff
    mins = max(0, int((kickoff - captured_at).total_seconds() // 60))
    return c.execute(
        """INSERT INTO odds_snapshots (match_id, bookmaker, market, selection, line, price, captured_at,
                                       mins_to_kickoff, window_tag, source, book_updated_at)
           SELECT %s, 'pinnacle', 'h2h', v.sel, NULL, v.price, %s, %s, 'close', %s, %s
           FROM (VALUES ('home', %s::real), ('draw', %s::real), ('away', %s::real)) AS v(sel, price)
           WHERE NOT EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.match_id = %s
                             AND o.bookmaker = 'pinnacle' AND o.market = 'h2h' AND o.window_tag = 'close')""",
        (match_id, captured_at, mins, source, book_updated_at, precios["home"], precios["draw"],
         precios["away"], match_id)).rowcount


def cargar_ternas(c, league_id: str, ternas: list[dict], resolver, aplicar: bool) -> dict:
    """
    Adjunta el cierre de Pinnacle a partidos que YA existen. `resolver` devuelve el team_id (un club
    ascendido o descendido tiene su fila en otra división, así que no se exige la liga del equipo).
    No da de alta equipos ni partidos. `odds_snapshots` no admite DELETE: la comprobación de que no hay ya un cierre
    de Pinnacle va dentro del propio INSERT, para que dos ejecuciones no se pisen.
    """
    r = {"filas": len(ternas), "sin_resolver": 0, "sin_partido": 0, "ya_tenia_cierre": 0,
         "a_insertar": 0, "insertadas": 0}
    for t in ternas:
        hn, an = resolver(t["home"], league_id), resolver(t["away"], league_id)
        if hn is None or an is None:
            r["sin_resolver"] += 1
            continue
        m = c.execute(
            """SELECT m.match_id, m.kickoff_utc,
                      EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.match_id = m.match_id
                              AND o.bookmaker = 'pinnacle' AND o.market = 'h2h'
                              AND o.window_tag = 'close') AS tiene
               FROM matches m
               WHERE m.league_id = %s AND m.home_team_id = %s AND m.away_team_id = %s
                 AND m.status = 'finished' AND m.kickoff_utc BETWEEN %s AND %s
               ORDER BY abs(extract(epoch FROM (m.kickoff_utc - %s::timestamptz))) LIMIT 1""",
            (league_id, hn, an, t["ko"] - timedelta(hours=36), t["ko"] + timedelta(hours=36),
             t["ko"])).fetchone()
        if m is None:
            r["sin_partido"] += 1
        elif m["tiene"]:
            r["ya_tenia_cierre"] += 1
        else:
            r["a_insertar"] += 1
            if aplicar:
                r["insertadas"] += insertar_cierre(c, m["match_id"], m["kickoff_utc"], t["price"])
    return r


def _resolver_lectura(nombre: str, league_id: str) -> int | None:
    """team_id por coincidencia EXACTA y sin escribir nada (ni alias ni pendientes)."""
    tid, _, score = match_team(nombre, "football_data", league_id)
    return tid if tid and score >= 100.0 else None


def _ligas_con_csv(ligas: list[str] | None) -> list[dict]:
    from ..db import query
    filas = query("SELECT league_id, fd_code, fd_extra FROM leagues WHERE fd_code IS NOT NULL AND active")
    return [f for f in filas if not ligas or f["league_id"] in ligas]


def completar_cierres(ligas: list[str] | None = None, seasons: list[str] | None = None,
                      desde: str = "2024-01-01", aplicar: bool = False) -> dict:
    """
    Cierre de Pinnacle de football-data para partidos YA cargados que no lo tienen. Por defecto
    es un ensayo. Solo se aceptan PSCH/PSCD/PSCA. La presencia de esas columnas
    en un CSV no garantiza cobertura reciente: la descarga del 14-oct-2026
    tampoco encontró cierres nuevos en México, Argentina, Brasil ni MLS.
    """
    from ..db import conn

    desde_dt = datetime.fromisoformat(desde).replace(tzinfo=timezone.utc)
    seasons = seasons or default_seasons()[-3:]
    out = {}
    for lg in _ligas_con_csv(ligas):
        ternas = []
        if lg["fd_extra"]:
            df = _fetch_csv(BASE_EXTRA.format(code=lg["fd_code"]))
            if df is not None and not df.empty:
                ternas += ternas_pinnacle(df, COLS_EXTRA, desde_dt)
        else:
            for s in seasons:
                df = _fetch_csv(BASE_MAIN.format(season=s, code=lg["fd_code"]))
                if df is not None and not df.empty:
                    ternas += ternas_pinnacle(df, COLS_MAIN, desde_dt)
        with conn() as c:
            out[lg["league_id"]] = cargar_ternas(
                c, lg["league_id"], ternas,
                _resolver_lectura, aplicar)
    return out


# Los dos formatos de football-data.co.uk NO comparten nombres de columna.
# Leer el "extra" con los nombres del principal devuelve None en cada fila y la
# liga entera se carga vacía sin dar ningún error.
COLS_MAIN = {"home": "HomeTeam", "away": "AwayTeam", "hg": "FTHG", "ag": "FTAG",
             "hg_ht": "HTHG", "ag_ht": "HTAG", "hs": "HS", "as": "AS",
             "hst": "HST", "ast": "AST", "hc": "HC", "ac": "AC",
             "hy": "HY", "ay": "AY", "hr": "HR", "ar": "AR", "referee": "Referee"}
# El extra solo trae resultado y cuotas: ni tiros, ni córners, ni descanso.
COLS_EXTRA = {"home": "Home", "away": "Away", "hg": "HG", "ag": "AG",
              "hg_ht": None, "ag_ht": None, "hs": None, "as": None,
              "hst": None, "ast": None, "hc": None, "ac": None,
              "hy": None, "ay": None, "hr": None, "ar": None, "referee": None}


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
    equipo nuevo legítimo y se da de alta. Pero "no lo reconoce" se decide en
    TODO el país, no solo en la liga que se carga (2026-10-11): al cargar
    Segunda, el Racing o el Leeds ya existen en Primera y crearlos otra vez
    partiría su historial. Un parecido dudoso no se crea: queda pendiente en
    `unresolved_names` y el partido se salta (ver `normalize.clasificar_historial`).

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
    raw = raw_name.strip()
    c = clasificar_historial(raw, "football_data", league_id)
    if c["decision"] == "existe":
        if c["via"] != "alias":
            register_alias(raw, "football_data", c["team_id"])
        return c["team_id"]
    if c["decision"] == "dudoso":
        _record_unresolved(raw, "football_data", league_id, c["candidato"], c["score"])
        return None

    execute(
        """INSERT INTO teams (league_id, canonical_name) VALUES (%s, %s)
           ON CONFLICT (league_id, canonical_name) DO NOTHING""",
        (league_id, raw),
    )
    row = query_one(
        "SELECT team_id FROM teams WHERE league_id = %s AND canonical_name = %s",
        (league_id, raw),
    )
    if not row:
        return None
    clear_cache()
    register_alias(raw, "football_data", row["team_id"])
    return row["team_id"]


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
        referee = arbitro(row.get(cols["referee"])) if cols.get("referee") else None

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
                  home_yellow, away_yellow, home_red, away_red, referee, result_recorded_at)
               VALUES (%s,%s,%s,%s,%s,%s,'finished',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id) DO NOTHING""",
            (match_id, league_id, season, ko, hid, aid,
             _n("hg"), _n("ag"), _n("hg_ht"), _n("ag_ht"),
             _n("hs"), _n("as"), _n("hst"), _n("ast"),
             _n("hc"), _n("ac"), _n("hy"), _n("ay"), _n("hr"), _n("ar"), referee, ko),
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


def completar_tarjetas(seasons: list[str] | None = None) -> dict:
    """
    Rellena amarillas, árbitro y córners de partidos YA cargados, desde los
    CSV principales (gratis; los extra no traen ni tarjetas ni árbitro). Solo
    toca columnas vacías: lo que trajo API-Football no se pisa. Mismo
    emparejamiento que la carga (equipos y ±36 h), sin dar de alta equipos.
    """
    from ..db import query

    seasons = seasons or default_seasons()
    leagues = query("SELECT league_id, fd_code FROM leagues "
                    "WHERE fd_code IS NOT NULL AND NOT fd_extra AND active")
    out = {}
    for lg in leagues:
        n = 0
        for season in seasons:
            df = _fetch_csv(BASE_MAIN.format(season=season, code=lg["fd_code"]))
            if df is None or df.empty or not {"HY", "AY"} <= set(df.columns):
                continue
            for _, row in df.iterrows():
                ko = _parse_date(row)
                home, away = row.get("HomeTeam"), row.get("AwayTeam")
                if ko is None or not isinstance(home, str) or not isinstance(away, str):
                    continue
                hn = resolve_team(home, "football_data", league_id=lg["league_id"])
                an = resolve_team(away, "football_data", league_id=lg["league_id"])
                if hn is None or an is None:
                    continue
                vals = []
                for col in ("HY", "AY", "HR", "AR", "HC", "AC"):
                    v = row.get(col)
                    vals.append(int(v) if pd.notna(v) else None)
                n += execute(
                    """UPDATE matches m SET
                         home_yellow = COALESCE(m.home_yellow, %s),
                         away_yellow = COALESCE(m.away_yellow, %s),
                         home_red = COALESCE(m.home_red, %s),
                         away_red = COALESCE(m.away_red, %s),
                         home_corners = COALESCE(m.home_corners, %s),
                         away_corners = COALESCE(m.away_corners, %s),
                         referee = COALESCE(m.referee, %s)
                       FROM teams th, teams ta
                       WHERE m.league_id = %s AND th.team_id = m.home_team_id
                         AND ta.team_id = m.away_team_id
                         AND th.league_id = %s AND th.canonical_name = %s
                         AND ta.league_id = %s AND ta.canonical_name = %s
                         AND m.kickoff_utc BETWEEN %s AND %s
                         AND m.status = 'finished'
                         AND (m.home_yellow IS NULL OR m.referee IS NULL
                              OR m.home_corners IS NULL)""",
                    (*vals, arbitro(row.get("Referee")), lg["league_id"],
                     lg["league_id"], hn, lg["league_id"], an,
                     ko - timedelta(hours=36), ko + timedelta(hours=36))) or 0
        out[lg["league_id"]] = n
        log.info("Tarjetas %s: %d partidos completados", lg["league_id"], n)
    return out


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


def csv_ajeno(df: pd.DataFrame, lg: dict) -> str | None:
    """
    Motivo si el CSV descargado NO es de esa liga, o None.

    football-data responde 200 a un código inexistente redirigiendo a OTRO
    archivo: `new/CHL.csv` sirve la Superliga china (`CHN.csv`). Sin esta
    comprobación la Primera chilena se habría cargado con 44 clubes chinos,
    sin un solo error. El extra trae la columna Country (con el BOM pegado al
    nombre al leerlo en latin-1) y el principal la columna Div.
    """
    pais = next((c for c in df.columns if str(c).endswith("Country")), None)
    if pais is not None:
        vistos = set(df[pais].dropna().astype(str).str.strip())
        if vistos and vistos != {lg["country"]}:
            return f"Country={sorted(vistos)[:3]} y la liga es de {lg['country']}"
    if "Div" in df.columns:
        vistos = set(df["Div"].dropna().astype(str).str.strip())
        if vistos and vistos != {lg["fd_code"]}:
            return f"Div={sorted(vistos)[:3]} y el código es {lg['fd_code']}"
    return None


def _ligas(league_ids: list[str]) -> list[dict]:
    from ..db import query

    rows = query("SELECT league_id, fd_code, fd_extra, country FROM leagues "
                 "WHERE league_id = ANY(%s) AND fd_code IS NOT NULL", (league_ids,))
    faltan = set(league_ids) - {r["league_id"] for r in rows}
    if faltan:
        raise ValueError(f"Sin fd_code en el catálogo: {sorted(faltan)}")
    return rows


def _temporadas_csv(lg: dict, seasons: list[str]):
    """(temporada, DataFrame, columnas) de cada temporada con datos."""
    if lg["fd_extra"]:
        df = _fetch_csv(BASE_EXTRA.format(code=lg["fd_code"]))
        if df is None or df.empty or "Season" not in df.columns:
            return
        motivo = csv_ajeno(df, lg)
        if motivo:
            raise ValueError(f"{lg['league_id']}: el CSV {lg['fd_code']} es de otra liga ({motivo})")
        etiquetas = df["Season"].astype(str)
        for s in seasons:
            sub = df[etiquetas.isin(season_labels_extra(s))]
            if not sub.empty:
                yield s, sub, COLS_EXTRA
    else:
        for s in seasons:
            df = _fetch_csv(BASE_MAIN.format(season=s, code=lg["fd_code"]))
            if df is None or df.empty:
                continue
            motivo = csv_ajeno(df, lg)
            if motivo:
                raise ValueError(f"{lg['league_id']} {s}: el CSV es de otra liga ({motivo})")
            yield s, df, COLS_MAIN


def ensayo(league_ids: list[str], seasons: list[str] | None = None) -> dict:
    """
    Qué haría `cargar()` con cada nombre de equipo, SIN escribir nada: cuáles
    se reutilizan (y de qué liga son hoy), cuáles se crearían y cuáles quedan
    dudosos. Se corre en el servidor ANTES de cargar; los dudosos se resuelven
    a mano como alias y el ensayo se repite hasta que no quede ninguno.
    """
    from ..db import query

    seasons = seasons or default_seasons()
    nombres_equipo = {r["team_id"]: (r["canonical_name"], r["league_id"])
                      for r in query("SELECT team_id, canonical_name, league_id FROM teams")}
    out = {}
    for lg in _ligas(league_ids):
        vistos: dict[str, list[str]] = {}
        filas = 0
        for s, df, cols in _temporadas_csv(lg, seasons):
            for _, row in df.iterrows():
                h, a = row.get(cols["home"]), row.get(cols["away"])
                if not isinstance(h, str) or not isinstance(a, str):
                    continue
                filas += 1
                for n in (h.strip(), a.strip()):
                    vistos.setdefault(n, [])
                    if s not in vistos[n]:
                        vistos[n].append(s)
        res = {"filas": filas, "existe": [], "nuevo": [], "dudoso": []}
        for n, temps in sorted(vistos.items()):
            c = clasificar_historial(n, "football_data", lg["league_id"])
            item = {"nombre": n, "temporadas": f"{temps[0]}-{temps[-1]}", "n_temp": len(temps)}
            if c["decision"] == "existe":
                item["equipo"], item["liga"] = nombres_equipo.get(c["team_id"], ("?", "?"))
                item["via"] = c["via"]
            elif c["decision"] == "dudoso":
                item["parecido"] = [nombres_equipo.get(t, ("?", "?")) for t in c["candidatos"]]
                item["score"] = c["score"]
            res[c["decision"]].append(item)
        out[lg["league_id"]] = res
    return out


def cargar(league_ids: list[str], seasons: list[str] | None = None) -> dict:
    """Carga el histórico de las ligas dadas (las demás no se tocan)."""
    seasons = seasons or default_seasons()
    out = {}
    for lg in _ligas(league_ids):
        n = sum(_ingest_rows(lg["league_id"], s, df, cols)
                for s, df, cols in _temporadas_csv(lg, seasons))
        log.info("%s: %d partidos", lg["league_id"], n)
        out[lg["league_id"]] = n
    return out


if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(level=logging.INFO)
    # `tarjetas`: solo rellena amarillas, árbitro y córners de lo ya cargado.
    # `ensayo <ligas>`: qué se reutiliza, crea o queda dudoso, sin escribir.
    # `cargar <ligas>`: carga solo esas ligas.
    # `cierres [--aplicar] [ligas]`: cierre de Pinnacle de partidos ya cargados (ensayo sin --aplicar).
    if sys.argv[1:] == ["tarjetas"]:
        print(completar_tarjetas())
    elif sys.argv[1:2] == ["cierres"]:
        args = sys.argv[2:]
        print(json.dumps(completar_cierres([a for a in args if a != "--aplicar"],
                                           aplicar="--aplicar" in args), ensure_ascii=False, indent=1))
    elif sys.argv[1:2] == ["ensayo"]:
        print(json.dumps(ensayo(sys.argv[2:]), ensure_ascii=False, indent=1))
    elif sys.argv[1:2] == ["cargar"]:
        print(cargar(sys.argv[2:]))
    else:
        print(backfill())
