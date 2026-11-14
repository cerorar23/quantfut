"""Informe de cobertura de cuotas por fuente (solo lectura): `python medir_cobertura_cuotas.py [propline|oddsapi|therundown|sportsapipro|todo]`.

Se ejecuta DENTRO de un contenedor con las claves (p. ej. `releases/cuotas-cascada-20261109/run.sh python - <parte> < este_archivo`).
`todo` NO incluye sportsapipro: gasta ~60 de las 100 peticiones diarias del plan gratis (compartidas con el once de fútbol);
pídelo expresamente. The Odds API cuesta ~160 créditos por pasada. PropLine y TheRundown no gastan cupo relevante."""
import collections
import gzip
import json
import os
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8")
PARTE = sys.argv[1] if len(sys.argv) > 1 else "todo"
NOW = datetime.now(timezone.utc)
HASTA = NOW + timedelta(days=7)


def J(d):
    return json.loads(d) if isinstance(d, (str, bytes)) else d


def fam(k):
    k = k.lower()
    for a, b in (("h2h_3_way", "1x2"), ("h2h", "1x2/ganador"), ("alternate_spread", "alt_spread"), ("alternate_total", "alt_total"),
                 ("team_total", "team_totals"), ("spread", "hándicap"), ("total", "totales"), ("btts", "ambos_marcan"),
                 ("both_teams", "ambos_marcan"), ("double_chance", "doble_op"), ("draw_no_bet", "dnb"), ("corner", "córners"),
                 ("card", "tarjetas"), ("player_", "props_jugador"), ("batter", "props_jugador")):
        if a in k:
            return b
    return k


# ---------------------------------------------------------------- PropLine (archivo horario del VPS)
def propline():
    base = "/srv/quantfut/artifacts/propline_shared/"
    c = sqlite3.connect("file:" + base + "index.sqlite?mode=ro", uri=True)
    rows = c.execute("select r.path,x.received_at,x.body_path from requests r join receipts x on x.request_id=r.id "
                     "where x.status=200 and r.path like '/v1/sports/%/odds' order by x.received_at desc limit 900").fetchall()
    ultimo = {}
    for p, ra, bp in rows:
        ultimo.setdefault(p, ra[:13])
    por = collections.defaultdict(lambda: collections.defaultdict(set))
    evs = collections.defaultdict(set)
    for p, ra, bp in rows:
        if ra[:13] != ultimo[p]:
            continue
        sport = p.split("/")[3]
        try:
            b = open(base + bp, "rb").read()
            try:
                b = gzip.decompress(b)
            except Exception:
                pass
            d = json.loads(b)
        except Exception:
            continue
        d = d if isinstance(d, list) else d.get("events", [])
        for e in d:
            try:
                ct = datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00"))
            except Exception:
                continue
            if not (NOW <= ct <= HASTA):
                continue
            evs[sport].add(e["id"])
            for bk in e.get("bookmakers", []):
                for m in bk.get("markets", []):
                    if m.get("outcomes"):
                        por[sport][fam(m["key"])].add(e["id"])
    print("== PROPLINE (próximos 7 días, archivo de la última hora)")
    for s in sorted(evs):
        if s.startswith(("soccer", "basketball_nba", "tennis")):
            print(f"{s}: {len(evs[s])} eventos | " + ", ".join(f"{k}:{len(v)}" for k, v in sorted(por[s].items(), key=lambda x: -len(x[1]))))


# ---------------------------------------------------------------- The Odds API
def oddsapi():
    key = os.environ["ODDS_API_RESPALDO_KEY"]
    H = "https://api.the-odds-api.com/v4"

    def get(path, **q):
        q["apiKey"] = key
        url = f"{H}{path}?" + "&".join(f"{k}={v}" for k, v in q.items())
        try:
            r = urllib.request.urlopen(url, timeout=30)
            return r.status, json.load(r), r.headers
        except urllib.error.HTTPError as e:
            return e.code, None, e.headers
    ligas = [
        "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a", "soccer_germany_bundesliga", "soccer_germany_bundesliga2",
        "soccer_france_ligue_one", "soccer_netherlands_eredivisie", "soccer_portugal_primeira_liga", "soccer_turkey_super_league",
        "soccer_mexico_ligamx", "soccer_argentina_primera_division", "soccer_usa_mls", "soccer_spain_segunda_division",
        "soccer_italy_serie_b", "soccer_sweden_allsvenskan", "soccer_denmark_superliga", "soccer_switzerland_superleague",
        "soccer_norway_eliteserien", "soccer_uefa_champs_league", "soccer_uefa_europa_league"]
    print("== THE ODDS API (región eu; h2h,totals,spreads por liga + 1 partido con mercados adicionales)")
    gastado = 0
    for lg in ligas:
        st, d, h = get(f"/sports/{lg}/odds", regions="eu", markets="h2h,totals,spreads", oddsFormat="decimal")
        if st != 200 or d is None:
            print(f"{lg}: status {st}")
            continue
        gastado += int(h.get("x-requests-last", 0) or 0)
        ev = [e for e in d if NOW <= datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) <= HASTA]
        mk = collections.defaultdict(set)
        casas = 0
        for e in ev:
            casas = max(casas, len(e["bookmakers"]))
            for b in e["bookmakers"]:
                for m in b["markets"]:
                    mk[m["key"]].add(e["id"])
        print(f"{lg}: {len(ev)} eventos, máx {casas} casas | " + ", ".join(f"{k}:{len(v)}" for k, v in sorted(mk.items(), key=lambda x: -len(x[1]))))
        if ev:
            ad = collections.defaultdict(set)
            for m in ("btts", "draw_no_bet", "double_chance", "h2h_h1", "team_totals", "alternate_totals", "alternate_spreads"):
                st2, d2, h2 = get(f"/sports/{lg}/events/{ev[0]['id']}/odds", regions="eu", markets=m, oddsFormat="decimal")
                gastado += int((h2 or {}).get("x-requests-last", 0) or 0)
                if st2 == 200 and d2:
                    for b in d2.get("bookmakers", []):
                        for mm in b["markets"]:
                            ad[mm["key"]].add(b["key"])
            print("   adicionales (1 partido, casas): " + (", ".join(f"{k}:{len(v)}" for k, v in ad.items()) or "ninguno"))
    # NBA
    st, d, h = get("/sports/basketball_nba/odds", regions="us", markets="h2h,spreads,totals", oddsFormat="decimal")
    gastado += int((h or {}).get("x-requests-last", 0) or 0)
    ev = [e for e in (d or []) if NOW <= datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) <= HASTA]
    mk = collections.defaultdict(set)
    for e in ev:
        for b in e["bookmakers"]:
            for m in b["markets"]:
                mk[m["key"]].add(e["id"])
    print(f"basketball_nba: {len(ev)} eventos | " + ", ".join(f"{k}:{len(v)}" for k, v in mk.items()))
    if ev:
        PROPS = "player_points,player_rebounds,player_assists,player_threes,player_blocks,player_steals,player_points_rebounds_assists,player_double_double,player_turnovers"
        st, d, h = get(f"/sports/basketball_nba/events/{ev[0]['id']}/odds", regions="us", markets=PROPS, oddsFormat="decimal")
        gastado += int((h or {}).get("x-requests-last", 0) or 0)
        mk = collections.defaultdict(set)
        for b in (d or {}).get("bookmakers", []):
            for m in b["markets"]:
                mk[m["key"]].add(b["key"])
        print("NBA props (1 partido):", ", ".join(f"{k}:{len(v)} casas" for k, v in mk.items()) or "ninguna")
    # tenis
    st, d, h = get("/sports")
    act = [s["key"] for s in (d or []) if s["key"].startswith("tennis_") and s.get("active")]
    print("tenis activos:", act)
    for t in act:
        st, d, h = get(f"/sports/{t}/odds", regions="eu", markets="h2h,spreads,totals", oddsFormat="decimal")
        gastado += int((h or {}).get("x-requests-last", 0) or 0)
        ev = [e for e in (d or []) if NOW <= datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")) <= HASTA]
        mk = collections.defaultdict(set)
        for e in ev:
            for b in e["bookmakers"]:
                for m in b["markets"]:
                    mk[m["key"]].add(e["id"])
        print(f"{t}: {len(ev)} eventos | " + ", ".join(f"{k}:{len(v)}" for k, v in mk.items()))
    print("créditos gastados:", gastado, "| saldo:", h.get("x-requests-remaining") if h else "?")


# ---------------------------------------------------------------- SportsAPIPro
def sportsapipro():
    from qf.ingest import cuotas_sportsapipro as csp
    get = csp._transporte(os.environ["SPORTSAPIPRO_KEY"])
    A = csp.API
    peticiones = 0
    print("== SPORTSAPIPRO (calendario próximos 7 días; cuotas: muestra de partidos por torneo)")
    torneos = collections.defaultdict(list)
    for deporte, dias in (("football", 8), ("basketball", 3), ("tennis", 3)):
        for i in range(dias):
            f = (NOW + timedelta(days=i)).date().isoformat()
            st, doc = get(f"{A}/{deporte}/schedule/{f}")
            peticiones += 1
            for e in csp._eventos_de(J(doc)) if st == 200 else []:
                t = e.get("tournament") or {}
                n = (t.get("uniqueTournament") or {}).get("name") or t.get("name") or ""
                cat = (t.get("category") or {}).get("name") or ""
                try:
                    if datetime.fromtimestamp(int(e["startTimestamp"]), timezone.utc) < NOW:
                        continue
                except Exception:
                    continue
                torneos[(deporte, cat, n)].append(e)
    objetivo = {"football": {"England", "Spain", "Italy", "Germany", "France", "Netherlands", "Portugal", "Turkey", "Mexico", "Argentina",
                             "USA", "Sweden", "Denmark", "Switzerland", "Norway", "Europe", "International"},
                "basketball": {"USA"}, "tennis": None}
    muestra = []
    for (dep, cat, n), evs in sorted(torneos.items()):
        if dep == "football" and cat not in objetivo["football"]:
            continue
        if dep == "basketball" and n != "NBA":
            continue
        if dep == "tennis" and not any(x in n for x in ("ATP", "WTA")):
            continue
        muestra.append((dep, cat, n, evs))
    print(f"torneos en el alcance: {len(muestra)}")
    usados = 0
    for dep, cat, n, evs in muestra:
        res = []
        for e in evs[:2]:
            if usados >= 26:
                break
            st, doc = get(f"{A}/{dep}/api/match/{e['id']}/odds/pre-match")
            usados += 1
            ms = csp.mercados(J(doc)) if st == 200 else []
            res.append(sorted({m["nombre"] for m in ms}))
        peticiones += len(res)
        con = [r for r in res if r]
        print(f"{dep} | {cat} | {n}: {len(evs)} partidos | cuotas {len(con)}/{len(res)} probados | "
              + ("; ".join(con[0]) if con else "ninguna"))
    print("peticiones usadas:", peticiones)


# ---------------------------------------------------------------- TheRundown
def therundown():
    from qf.ingest import cuotas_therundown as crd
    cli = crd.Cliente(os.environ["THERUNDOWN_API_KEY"])
    print("== THERUNDOWN (Free; 3 casas; market_ids 1,2,3; main_line)")
    deportes = {10: "MLS", 11: "EPL", 12: "Ligue 1", 13: "Bundesliga", 14: "LaLiga", 15: "Serie A", 16: "Champions", 33: "Europa League",
                34: "Liga MX", 4: "NBA", 38: "ATP", 39: "WTA"}
    for sid, nombre in deportes.items():
        total, mk = 0, collections.Counter()
        for i in range(7):
            f = (NOW + timedelta(days=i)).date().isoformat()
            try:
                evs = cli.eventos(sid, f)
            except Exception as e:  # noqa: BLE001
                print(f"{nombre}: error {type(e).__name__} {e}")
                break
            for e in evs:
                ini = crd._inicio(e)
                if not ini or ini < NOW:
                    continue
                total += 1
                for mid, nom in ((1, "ganador"), (2, "hándicap"), (3, "totales")):
                    if crd.lineas(e, mid):
                        mk[nom] += 1
        print(f"{nombre}: {total} eventos | " + ", ".join(f"{k}:{v}" for k, v in mk.items()))
    print("puntos usados:", cli.puntos, "| restante:", cli.restante)


if PARTE in ("todo", "propline"):
    propline()
if PARTE in ("todo", "oddsapi"):
    oddsapi()
if PARTE == "sportsapipro":
    sportsapipro()
if PARTE in ("todo", "therundown"):
    therundown()
