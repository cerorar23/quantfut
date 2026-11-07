"""Inventario de cuotas de tenis (auditoria 1.2): solo lectura.

Uso (Python 3.12, con -I al leer ficheros descargados):
  python -I apps/tennis/ops/inventario_cuotas.py --repo "C:/Users/huye/Documents/apuesta proyec" \
      --vps-dir <carpeta con copias de solo lectura del VPS> --out docs/tenis_auditoria_tablas

Cada cifra sale de una funcion de este fichero. Las copias del VPS se generan con los comandos
que figuran en docs/tenis_auditoria_inventario_cuotas_20261104.md (solo ls/head/zcat/find/ssh de lectura).
Escribe solo en --out, prefijo cuotas_. No llama a ninguna API.
"""
import argparse
import csv
import gzip
import importlib.util
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

import pyarrow.parquet as pq

HERE = Path(__file__).resolve()
WORKTREE = HERE.parents[3]
DEFAULT_REPO = Path("C:/Users/huye/Documents/apuesta proyec")
EXCHANGE_OR_DFS = {"kalshi", "polymarket", "polymarket_us", "matchbook", "smarkets", "novig", "prophetx", "sx_bet",
                   "betfair_exchange", "betfair_ex", "betfair_ex_eu", "betfair_ex_au", "betfair", "betfair_ex_uk",
                   "prizepicks", "underdog", "sleeper", "dabble", "parlayplay", "draftkings_pick6", "thrillzz", "courtside"}
TENNISDATA_BOOKS = {"PS": ("PSW", "PSL", "Pinnacle"), "B365": ("B365W", "B365L", "Bet365"), "Max": ("MaxW", "MaxL", "Mejor cuota (Max)"),
                    "Avg": ("AvgW", "AvgL", "Media (Avg)"), "BFE": ("BFEW", "BFEL", "Betfair Exchange"),
                    "EX": ("EXW", "EXL", "Betfair Exch. (EX)"), "LB": ("LBW", "LBL", "Ladbrokes"), "UB": ("UBW", "UBL", "Unibet"),
                    "SJ": ("SJW", "SJL", "Stan James"), "CB": ("CBW", "CBL", "Centrebet"), "GB": ("GBW", "GBL", "Gamebookers"),
                    "IW": ("IWW", "IWL", "Interwetten"), "SB": ("SBW", "SBL", "Sportingbet"), "B&W": ("B&WW", "B&WL", "Bet&Win")}
ROWS = []  # filas de todas las tablas (se escriben a CSV al final)
# Clasificacion por fuente y mercado (criterio del informe: (a) cierre verificable, (b) cierre declarado sin instante,
# (c) foto de algun instante). Solo (a) y (b) sirven de referencia de calibracion.
FUENTES = [
    dict(fuente="Tennis-Data (local, odds_raw.parquet)", mercado="ganador", casas="PS, B365, Max, Avg, BFE, EX, LB, UB, SJ, CB, GB, IW, SB, B&W",
         instante_recepcion="NO (solo fecha dia, sin hora)", instante_casa="NO", inicio="NO (solo fecha)",
         clase_cierre="(b) cierre declarado por convencion de columnas, sin instante", referencia_calibracion="si (a nivel partido, sin hora)",
         cobertura="ATP/WTA principal; 2000-2026 (cuotas segun anio y casa)", fuente_medida="cuotas_tennisdata_cobertura_anual.csv"),
    dict(fuente="Tennis-Data margen agregado Max/Avg", mercado="ganador", casas="Max y Avg (agregados, no casas)",
         instante_recepcion="NO", instante_casa="NO", inicio="NO", clase_cierre="(b) sin instante; no es una casa",
         referencia_calibracion="no (agregado)", cobertura="igual que Tennis-Data", fuente_medida="cuotas_margen_ganador_casa.csv"),
    dict(fuente="PropLine piloto (.local/propline_shared_pilot_20261023)", mercado="ganador, totales, hándicaps, sets, juegos, aces, puntos de break, tiebreaks",
         casas="ver casas_distintas en el resumen (incluye exchanges y DFS, marcados)", instante_recepcion="SI (received_at por recibo, hora UTC)",
         instante_casa="SI en algunos contratos (book_updated_at); last_seen_at siempre", inicio="SI (commence_time)",
         clase_cierre="(c) foto de un instante (recibo 22:21-22:24 UTC del 23-oct); sin endpoint de cierre en el piloto",
         referencia_calibracion="no", cobertura="3 recibos de tenis con 200 y 1 con 400; 173 eventos; 30.966 cotizaciones",
         fuente_medida="cuotas_propline_piloto_*.csv"),
    dict(fuente="PropLine produccion (VPS, endpoint /odds/closing)", mercado="cierre de todos los mercados del evento (cotizaciones por evento)",
         casas="no desglosado en logs", instante_recepcion="SI por recibo en el archivo del VPS (NO accesible desde qf: permiso denegado)",
         instante_casa="NO medido", inicio="SI (commence_time en archivo; no leido en el log)",
         clase_cierre="(b) cierre declarado por PropLine; el log solo tiene la hora de la pasada, no por evento",
         referencia_calibracion="si, a nivel de conteo; falta verificar el instante por evento",
         cobertura="ver cuotas_propline_produccion_runs_tenis.csv (270 pasadas)", fuente_medida="cuotas_propline_produccion_runs_tenis.csv"),
    dict(fuente="PropLine produccion (VPS, /tennis/odds horario)", mercado="todas las cotizaciones de tenis por hora",
         casas="no desglosado en logs", instante_recepcion="SI en archivo (no accesible)", instante_casa="NO medido",
         inicio="SI en archivo (no accesible)", clase_cierre="(c) foto horaria", referencia_calibracion="no",
         cobertura="562 peticiones y 13,1 M cotizaciones en logs", fuente_medida="cuotas_propline_produccion_runs_tenis.csv"),
    dict(fuente="PropLine precursor (VPS ~/propline_data/tennis, 23-oct)", mercado="cierre por evento",
         casas="depende del evento", instante_recepcion="SI (captured_at)", instante_casa="NO", inicio="SI (commence_time)",
         clase_cierre="(b) cierre declarado, con captured_at", referencia_calibracion="pendiente (muchos cierres vacios)",
         cobertura="ver cuotas_apitennis_propline_precursor.csv", fuente_medida="cuotas_apitennis_propline_precursor.csv"),
    dict(fuente="The Odds API (local live_odds_v1: slots/credits/run)", mercado="ganador (h2h), region eu",
         casas="no en local (sin respuestas guardadas localmente)", instante_recepcion="SI (received_at en receipt)",
         instante_casa="SI (last_update por casa)", inicio="SI (commence_time)", clase_cierre="(c) foto (2 por dia, AM/PM)",
         referencia_calibracion="no", cobertura="1 ejecucion local (2026-10-20 AM, 9 eventos, 1 credito)", fuente_medida="cuotas_theoddsapi_vps_snapshots.csv"),
    dict(fuente="The Odds API (VPS live_odds_v1, WTA Ningbo)", mercado="ganador (h2h)", casas="ver casas_distintas en el resumen",
         instante_recepcion="SI", instante_casa="SI (last_update)", inicio="SI", clase_cierre="(c) foto; 5 instantes de tenis",
         referencia_calibracion="no", cobertura="5 instantes, 32 eventos", fuente_medida="cuotas_margen_ganador_theoddsapi.csv"),
    dict(fuente="BetsAPI (VPS prematch/odds/upcoming/list)", mercado="bet365 prematch: to_win_match, 1st_set_winner, ...; en directo 13_1",
         casas="bet365 (unica)", instante_recepcion="SI en upcoming (epoca en el nombre); en odds (add_time); NO en prematch",
         instante_casa="SI (updated_at en prematch/odds)", inicio="SI (time)",
         clase_cierre="(c) foto en upcoming; prematch sin instante de captura", referencia_calibracion="no",
         cobertura="ver cuotas_betsapi_vps_resumen.csv", fuente_medida="cuotas_betsapi_vps_resumen.csv"),
    dict(fuente="API-Tennis (VPS intake)", mercado="ninguno (solo fixtures y resultados)", casas="no", instante_recepcion="SI (receipt)",
         instante_casa="no aplica", inicio="SI (event_date/event_time)", clase_cierre="no aplica (no es cuota)",
         referencia_calibracion="resultados (no cuotas)", cobertura="147 registros get_fixtures", fuente_medida="cuotas_apitennis_propline_precursor.csv"),
]


def pct(values, q):
    """Percentil lineal (q en 0..100)."""
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * q / 100
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def resumen(values):
    if not values:
        return dict(n=0, media=None, mediana=None, p5=None, p25=None, p75=None, p95=None)
    return dict(n=len(values), media=round(mean(values), 5), mediana=round(median(values), 5),
                p5=round(pct(values, 5), 5), p25=round(pct(values, 25), 5), p75=round(pct(values, 75), 5),
                p95=round(pct(values, 95), 5))


def fnum(x):
    try:
        v = float(x)
        return v if math.isfinite(v) and v > 0 else None
    except (TypeError, ValueError):
        return None


def load_propline_shared(repo):
    path = repo / "src" / "qf" / "ingest" / "propline_shared.py"
    spec = importlib.util.spec_from_file_location("propline_shared", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 1. Tennis-Data (cuotas de cierre de ganador, fichero procesado a partir de tennis-data.co.uk)
def seccion_tennis_data(repo, out):
    tbl = pq.read_table(repo / "data/tennis/tennis_data_manual_processed/odds_raw.parquet").to_pylist()
    matched = pq.read_table(repo / "data/tennis/tennis_data_manual_processed/odds_matched.parquet").to_pylist()
    matched_keys = Counter((r["circuit"], r["file_year"]) for r in matched)
    raw_keys = Counter((r["circuit"], r["file_year"]) for r in tbl)
    resumen_anual = []
    for (circ, year) in sorted(raw_keys):
        rows = [r for r in tbl if r["circuit"] == circ and r["file_year"] == year]
        fechas = [r["Date"] for r in rows if r["Date"] is not None]
        row = dict(fuente="Tennis-Data (odds_raw.parquet)", circuito=circ, anio=year, partidos=len(rows),
                   fecha_min=min(fechas).date().isoformat() if fechas else None,
                   fecha_max=max(fechas).date().isoformat() if fechas else None,
                   partidos_en_odds_matched=matched_keys.get((circ, year), 0))
        for casa, (cw, cl, _) in TENNISDATA_BOOKS.items():
            row[f"con_cuota_{casa}"] = sum(1 for r in rows if fnum(r.get(cw)) and fnum(r.get(cl)))
        resumen_anual.append(row)
    write_csv(out / "cuotas_tennisdata_cobertura_anual.csv", resumen_anual)
    ROWS.append(("tennisdata_cobertura", resumen_anual))

    series = Counter((r["circuit"], r.get("Series"), r.get("Tier")) for r in tbl)
    write_csv(out / "cuotas_tennisdata_series.csv",
              [dict(circuito=c, series=s, tier=t, partidos=n) for (c, s, t), n in sorted(series.items(), key=lambda x: -x[1])])

    margenes = []
    margen_por_casa = {}
    for casa, (cw, cl, nombre) in TENNISDATA_BOOKS.items():
        vals = []
        por_circ = defaultdict(list)
        for r in tbl:
            w, l = fnum(r.get(cw)), fnum(r.get(cl))
            if w is None or l is None or w <= 1 or l <= 1:
                continue
            m = 1 / w + 1 / l - 1  # margen de dos resultados, por partido
            vals.append(m)
            por_circ[r["circuit"]].append(m)
        margen_por_casa[casa] = vals
        flag = "exchange" if casa in ("BFE", "EX") else "agregado (no es una casa)" if casa in ("Max", "Avg") else "casa"
        for circ in sorted(por_circ) + ["TODOS"]:
            v = vals if circ == "TODOS" else por_circ[circ]
            margenes.append(dict(fuente="Tennis-Data", casa=casa, nombre=nombre, tipo=flag, circuito=circ,
                                 mercado="ganador (moneyline)", linea="", **resumen(v)))
    write_csv(out / "cuotas_margen_ganador_casa.csv", margenes)
    ROWS.append(("tennisdata_margen", margenes))

    # Cierre: la cabecera del fichero no trae instante; solo la convención de columnas (PS/B365/...).
    sin_instante = dict(fuente="Tennis-Data", campos_de_instante="ninguno (solo Date, sin hora)",
                        clasificacion_cierre="(b) cierre declarado por la fuente sin instante", uso_calibracion="si, a nivel partido")
    return dict(total_filas=len(tbl), anios=len(resumen_anual), matched=len(matched), margen_resumen=margenes,
                cierre=sin_instante, series=series)


EMIT = {"activo": False, "archivos": {}}


def write_csv(path, rows):
    """Escribe el CSV. Con --emit no toca disco: guarda el texto para que el shell lo escriba (ver docstring)."""
    rows = list(rows)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)
    texto = buf.getvalue()
    if EMIT["activo"]:
        EMIT["archivos"][path.name] = texto
    else:
        path.write_text(texto, encoding="utf-8", newline="")


# 2. PropLine: archivo piloto local (.local/propline_shared_pilot_20261023), solo tenis
def seccion_propline_piloto(repo, out, ps):
    root = repo / ".local/propline_shared_pilot_20261023"
    db = sqlite3.connect(f"file:{root.as_posix()}/index.sqlite?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    recibos = [dict(r) for r in db.execute(
        "select q.path, p.request_id, p.received_at, p.status, p.error, p.events, p.outcomes, p.body_path, p.sha256 "
        "from receipts p join requests q on q.id = p.request_id order by p.received_at")]
    tenis = [r for r in recibos if "/tennis" in r["path"]]
    tenis_odds = [r for r in tenis if r["path"].endswith("/tennis/odds")]
    resumen_recibos = []
    for r in tenis:
        resumen_recibos.append(dict(fuente="PropLine piloto", ruta=r["path"], request_id=r["request_id"],
                                    recibido_en=r["received_at"], http=r["status"], eventos=r["events"],
                                    cotizaciones=r["outcomes"], sha256=r["sha256"][:12]))
    write_csv(out / "cuotas_propline_piloto_recibos_tenis.csv", resumen_recibos)

    eventos_por_recibo = {}
    flags = Counter()
    mercados = Counter()
    mercados_casas = defaultdict(set)
    mercados_eventos = defaultdict(set)
    tours = Counter()
    minutos_antes = []
    cotiz_total = 0
    ev_tenis = {}
    for r in tenis_odds:
        if r["status"] != 200:
            continue
        body = json.loads(gzip.open(root / r["body_path"]).read())
        eventos_por_recibo[r["request_id"]] = len(body)
        for e in body:
            ev_tenis[e["id"]] = e
            tours[e.get("tour")] += 1
            try:
                t_ini = e["commence_time"]
            except KeyError:
                continue
            minutos_antes.append((ps.parse_time(t_ini) - ps.parse_time(r["received_at"])).total_seconds() / 60)
            for b in e.get("bookmakers", []):
                for m in b.get("markets", []):
                    key = (m["key"], m.get("period") or "-", m.get("line_type") or "-")
                    mercados[key] += 1
                    mercados_casas[key].add(b["key"])
                    mercados_eventos[key].add(e["id"])
                    for o in m.get("outcomes", []):
                        cotiz_total += 1
    ps_quotes = []
    for r in tenis_odds:
        if r["status"] != 200:
            continue
        body = json.loads(gzip.open(root / r["body_path"]).read())
        for q in ps.quotes(body, r["received_at"]):
            ps_quotes.append(q)
            for f in q["flags"]:
                flags[f] += 1

    fila_mercado = []
    for key, n in sorted(mercados.items(), key=lambda x: -x[1]):
        fila_mercado.append(dict(fuente="PropLine piloto", mercado=key[0], periodo=key[1], tipo_linea=key[2], cotizaciones_tipo_ev=n,
                                 casas=len(mercados_casas[key]), eventos=len(mercados_eventos[key]),
                                 circuitos="mezcla de tours (distribucion por tour en el resumen del script)"))
    write_csv(out / "cuotas_propline_piloto_mercados.csv", fila_mercado)

    # margen por contrato: (evento, casa, mercado, periodo, linea, descripcion) con dos resultados
    grupos = defaultdict(list)
    for q in ps_quotes:
        if q["price_decimal"] is None or q["bookmaker"] in EXCHANGE_OR_DFS:
            continue
        clave = (q["event_id"], q["bookmaker"], q["market"], q["period"] or "-", q["line_type"] or "-",
                 abs(q["point"]) if q["point"] is not None else None, q["description"] or "")
        grupos[clave].append(q)
    margen_contrato = defaultdict(list)
    for clave, qs in grupos.items():
        if len({x["name"] for x in qs}) != 2 or len(qs) != 2:
            continue
        if any(x["market"] == "h2h_lay" for x in qs):
            continue
        marg = sum(1 / x["price_decimal"] for x in qs) - 1
        mkey = (qs[0]["market"], qs[0]["period"] or "-", qs[0]["line_type"] or "-")
        linea = "" if qs[0]["point"] is None else str(abs(qs[0]["point"]))
        margen_contrato[(mkey, linea, qs[0]["bookmaker"])].append(marg)

    filas_margen = []
    for (mkey, linea, casa), vals in sorted(margen_contrato.items()):
        filas_margen.append(dict(fuente="PropLine piloto", mercado=mkey[0], periodo=mkey[1], tipo_linea=mkey[2],
                                 linea_abs=linea, casa=casa, **resumen(vals)))
    write_csv(out / "cuotas_margen_linea_propline_piloto.csv", filas_margen)

    ganador = [x for x in ps_quotes if x["market"] == "h2h" and x["period"] is None and x["line_type"] == "main"
               and x["price_decimal"] is not None]
    ganador_casas = defaultdict(list)
    grupos_w = defaultdict(list)
    for q in ganador:
        if q["bookmaker"] in EXCHANGE_OR_DFS:
            continue
        grupos_w[(q["event_id"], q["bookmaker"])].append(q)
    for (ev, casa), qs in grupos_w.items():
        if len(qs) == 2 and len({x["name"] for x in qs}) == 2:
            ganador_casas[casa].append(sum(1 / x["price_decimal"] for x in qs) - 1)
    filas_ganador = [dict(fuente="PropLine piloto", casa=c, nombre="", tipo="casa", circuito="todos",
                          mercado="ganador (h2h main)", linea="", **resumen(v)) for c, v in sorted(ganador_casas.items())]
    write_csv(out / "cuotas_margen_ganador_propline_piloto.csv", filas_ganador)

    ev_tours = Counter(e.get("tour") for e in ev_tenis.values())
    casas_distintas = {b for k in mercados_casas for b in mercados_casas[k]}
    return dict(casas_distintas=len(casas_distintas), casas_distintas_sin_exchange_dfs=len(casas_distintas - EXCHANGE_OR_DFS),
                recibos_tenis=len(tenis), recibos_200=sum(1 for r in tenis if r["status"] == 200),
                recibos_400=sum(1 for r in tenis if r["status"] != 200), eventos_unicos=len(ev_tenis),
                cotizaciones_tenis=cotiz_total, tours=dict(ev_tours), flags=dict(flags),
                minutos_antes_min=round(min(minutos_antes), 1) if minutos_antes else None,
                minutos_antes_mediana=round(median(minutos_antes), 1) if minutos_antes else None,
                eventos_ventana_0_10_min_antes=sum(1 for m in minutos_antes if 0 <= m <= 10),
                eventos_con_inicio_antes_de_recepcion=sum(1 for m in minutos_antes if m < 0),
                ganador_filas_margen=filas_ganador)


# 3. PropLine produccion: registros del VPS (logs JSON por linea, copia de solo lectura)
def seccion_propline_logs(vps_dir, out):
    runs = []
    pendientes = []
    for name in ("propline_log_2026-10.jsonl", "propline_log_2026-11.jsonl"):
        for line in (vps_dir / name).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if "path" in obj:
                pendientes.append(obj)
            elif "settlement" in obj:
                runs.append(dict(obj, _lineas=pendientes))
                pendientes = []
    filas = []
    tot = Counter()
    tot_salidas = Counter()
    for run in runs:
        ten = run["settlement"].get("tennis", {})
        lineas = run["_lineas"]
        t_odds = [x for x in lineas if x["path"].endswith("/tennis/odds")]
        t_close = [x for x in lineas if "/tennis/events/" in x["path"] and x["path"].endswith("/odds/closing")]
        t_res = [x for x in lineas if "/tennis/events/" in x["path"] and x["path"].endswith("/results")]
        t_stats = [x for x in lineas if "/tennis/events/" in x["path"] and x["path"].endswith("/stats")]
        close_ok = [x for x in t_close if x["status"] == 200 and x["outcomes"] > 0]
        fila = dict(inicio_run=run["started_at"], fin_run=run["finished_at"],
                    tenis_odds_peticiones=len(t_odds), tenis_odds_eventos=sum(x["events"] for x in t_odds),
                    tenis_odds_cotizaciones=sum(x["outcomes"] for x in t_odds),
                    tenis_cierre_peticiones=len(t_close), tenis_cierre_con_cotizaciones=len(close_ok),
                    tenis_cierre_cotizaciones=sum(x["outcomes"] for x in t_close),
                    tenis_resultados_peticiones=len(t_res), tenis_resultados_con_datos=sum(1 for x in t_res if x["outcomes"] > 0),
                    tenis_stats_peticiones=len(t_stats),
                    settlement_tenis_cierre=ten.get("closing"), settlement_tenis_resultados=ten.get("results"),
                    fallos_run=run.get("failures"), peticiones_run=run.get("requests"), cuota_diaria_usada=(run.get("quota") or {}).get("x-daily-used"))
        filas.append(fila)
        tot["cierre_peticiones"] += len(t_close)
        tot["cierre_con_cotiz"] += len(close_ok)
        tot["cierre_cotiz"] += sum(x["outcomes"] for x in t_close)
        tot["resultados_con_datos"] += sum(1 for x in t_res if x["outcomes"] > 0)
        tot["odds_peticiones"] += len(t_odds)
        tot["odds_cotiz"] += sum(x["outcomes"] for x in t_odds)
        tot["fallos"] += run.get("failures") or 0
    write_csv(out / "cuotas_propline_produccion_runs_tenis.csv", filas)
    return dict(runs=len(runs), **tot, outcomes_por_cierre_mediana=median([x["outcomes"] for r in runs for x in r["_lineas"]
                                                                              if "/tennis/events/" in x["path"] and x["path"].endswith("/odds/closing") and x["outcomes"] > 0] or [0]))


# 4. The Odds API (h2h, WTA Ningbo) capturas en VPS y local
def seccion_odds_api(vps_dir, repo, out):
    txt = (vps_dir / "live_odds_vps.txt").read_text(encoding="utf-8")
    partes = re.split(r"^@@FILE (\S+)\n", txt, flags=re.M)
    snaps = {}
    for i in range(1, len(partes), 2):
        name, body = partes[i], partes[i + 1]
        m = re.search(r"snapshots/([0-9a-f]+)/(receipt|response)\.json", name)
        if m:
            snaps.setdefault(m.group(1), {})[m.group(2)] = json.loads(body)
    filas = []
    margen_h2h = defaultdict(list)
    lag_book = []
    minutos = []
    for sid, par in sorted(snaps.items()):
        rec = par.get("receipt", {})
        if "tennis" not in rec.get("path", ""):
            continue
        resp = par.get("response", [])
        rcv = rec["received_at"]
        for ev in resp:
            minutos.append((_pt(ev["commence_time"]) - _pt(rcv)).total_seconds() / 60)
            for b in ev["bookmakers"]:
                if b.get("last_update"):
                    lag_book.append((_pt(rcv) - _pt(b["last_update"])).total_seconds() / 60)
                for m in b["markets"]:
                    if m["key"] != "h2h" or b["key"] in EXCHANGE_OR_DFS:
                        continue
                    pr = [fnum(o["price"]) for o in m["outcomes"]]
                    if len(pr) == 2 and all(pr):
                        margen_h2h[b["key"]].append(sum(1 / p for p in pr) - 1)
        filas.append(dict(fuente="The Odds API (VPS)", snapshot=sid[:8], ruta=rec["path"], recibido_en=rcv,
                          eventos=len(resp), creditos=rec.get("reserved_credits"),
                          remaining=(rec.get("headers") or {}).get("x-requests-remaining")))
    write_csv(out / "cuotas_theoddsapi_vps_snapshots.csv", filas)
    filas_m = []
    for casa, vals in sorted(margen_h2h.items(), key=lambda x: -len(x[1])):
        filas_m.append(dict(fuente="The Odds API (VPS, h2h)", casa=casa, tipo="casa", circuito="WTA Ningbo",
                            mercado="ganador (h2h)", linea="", **resumen(vals)))
    write_csv(out / "cuotas_margen_ganador_theoddsapi.csv", filas_m)

    # Instante de publicacion de la casa: last_update de cada casa frente a received_at
    casas_oa = {b for sid, par in snaps.items() if "tennis" in par.get("receipt", {}).get("path", "")
                for ev in par.get("response", []) for b in (x["key"] for x in ev["bookmakers"])}
    return dict(casas_distintas=len(casas_oa), snapshots_tenis=len([f for f in filas]), eventos=sum(f["eventos"] for f in filas),
                eventos_ventana_0_10_min_antes=sum(1 for m in minutos if 0 <= m <= 10),
                eventos_empezados_antes_de_recepcion=sum(1 for m in minutos if m < 0),
                minutos_inicio_menos_recepcion_min=round(min(minutos), 1) if minutos else None,
                minutos_inicio_menos_recepcion_max=round(max(minutos), 1) if minutos else None,
                minutos_recepcion_menos_ultima_actualizacion_casa_mediana=round(median(lag_book), 2) if lag_book else None,
                margen=filas_m)


def seccion_betsapi_y_apitennis(vps_dir, out):
    """Muestras (no censo completo) de BetsAPI y registros de API-Tennis en el VPS."""
    txt = (vps_dir / "betsapi_sample.txt").read_text(encoding="utf-8", errors="replace")
    partes = re.split(r"^@@FILE (\S+)\n", txt, flags=re.M)
    cont = Counter()
    mercados_pm = Counter()
    pm_eventos = 0
    pm_act = []
    od_filas = 0
    od_pre = 0
    od_post = 0
    od_eventos = 0
    od_status = Counter()
    up_mercados = Counter()
    up_archivos = 0
    for i in range(1, len(partes), 2):
        nombre, cuerpo = partes[i], partes[i + 1]
        carpeta = nombre.split("/")[0]
        cont[carpeta] += 1
        if carpeta == "prematch":
            pm_eventos += 1
            for k in re.findall(r'"([a-z0-9_]+)":\{"id":"\d+","name":"[^"]*","odds":\[', cuerpo):
                mercados_pm[k] += 1
            ev_t = re.search(r'"event":\{"id":"\d+","sport_id":"13","time":"(\d+)"', cuerpo)
            upd = [int(x) for x in re.findall(r'"updated_at":"(\d+)"', cuerpo)]
            if ev_t and upd:
                pm_act.append((int(ev_t.group(1)) - max(upd)) / 3600)
        elif carpeta == "odds":
            od_eventos += 1
            ev_t = re.search(r'"event":\{"id":"\d+","sport_id":"13","time":"(\d+)"', cuerpo)
            ts = re.findall(r'"add_time":"(\d+)"', cuerpo)
            for s in re.findall(r'"time_status":"(\d+)"', cuerpo)[:1]:
                od_status[s] += 1
            if ev_t:
                t0 = int(ev_t.group(1))
                for x in ts:
                    od_filas += 1
                    if int(x) < t0:
                        od_pre += 1
                    else:
                        od_post += 1
        elif carpeta == "upcoming":
            up_archivos += 1
            for k in re.findall(r'"([a-z0-9_]+)":\{"id":"\d+","name":"[^"]*","odds":\[', cuerpo):
                up_mercados[k] += 1
    epocas = []
    for linea in (vps_dir / "betsapi_meta.txt").read_text(encoding="utf-8").splitlines():
        if re.match(r"^\d+/\d{10}\.json\.gz$", linea.strip()):
            epocas.append(int(linea.split("/")[1].split(".")[0]))
    from datetime import datetime, timezone
    ini = datetime.fromtimestamp(min(epocas), timezone.utc).isoformat() if epocas else None
    fin = datetime.fromtimestamp(max(epocas), timezone.utc).isoformat() if epocas else None
    filas = [
        dict(fuente="BetsAPI (VPS) prematch", medida="muestra de archivos", n=cont["prematch"],
             mercados_con_cuotas_en_muestra=json.dumps(mercados_pm.most_common(12), ensure_ascii=False),
             instante_captura="NO (solo updated_at de la casa; mtime del VPS = 2026-10-24 por copia)",
             nota="archivos totales en VPS: 2.569; sin instante de captura por archivo"),
        dict(fuente="BetsAPI (VPS) odds (in-play)", medida="muestra de archivos", n=cont["odds"],
             mercados_con_cuotas_en_muestra="13_1 (ganador en directo; patron de claves)",
             instante_captura="SI por fila (add_time) pero cuota en directo",
             nota=f"filas de cotizacion en muestra={od_filas}; antes del inicio={od_pre}; despues={od_post}; time_status={dict(od_status)}; archivos totales en VPS: 31.136"),
        dict(fuente="BetsAPI (VPS) upcoming", medida="censo de nombres de archivo", n=len(epocas),
             mercados_con_cuotas_en_muestra=json.dumps(up_mercados.most_common(8), ensure_ascii=False),
             instante_captura="SI: nombre de archivo = epoca de captura",
             nota=f"237 eventos; rango de capturas {ini} a {fin}; muestra de contenido n={up_archivos}"),
    ]
    write_csv(out / "cuotas_betsapi_vps_resumen.csv", filas)
    act = [round(x, 2) for x in pm_act]
    return dict(prematch_muestra=pm_eventos, prematch_horas_inicio_menos_ultima_actualizacion_mediana=round(median(act), 2) if act else None,
                odds_muestra_eventos=od_eventos, odds_filas_antes_inicio=od_pre, odds_filas_despues_inicio=od_post,
                upcoming_rango=(ini, fin), upcoming_archivos=len(epocas))


def seccion_apitennis_y_pt(vps_dir, out):
    rec = (vps_dir / "api_tennis_receipts_head.txt").read_text(encoding="utf-8")
    metodos = Counter(re.findall(r'"method": "([a-z_]+)"', rec))
    estados = Counter(re.findall(r'"http_status": (\d+)', rec))
    txt = (vps_dir / "api_tennis_head.txt").read_text(encoding="utf-8", errors="replace")
    partes = re.split(r"^@@FILE (\S+)\n", txt, flags=re.M)
    con_odds = sum(1 for i in range(2, len(partes), 2) if '"odds' in partes[i])
    # PropLine precursor 2026-10-23 (101 archivos): cierre con cotizaciones o vacio
    pre = (vps_dir / "propline_data_tennis.txt").read_text(encoding="utf-8", errors="replace")
    bloques = re.split(r"^@@FILE (\S+)\n", pre, flags=re.M)
    cerr_vacio = cerr_con = 0
    capt = []
    for i in range(2, len(bloques), 2):
        cuerpo = bloques[i]
        m = re.search(r'"captured_at":"([^"]+)"', cuerpo)
        if m:
            capt.append(m.group(1))
        c = re.search(r'"closing":\{.*?"bookmakers":(\[\]|\[\{)', cuerpo, flags=re.S)
        if c:
            if c.group(1) == "[]":
                cerr_vacio += 1
            else:
                cerr_con += 1
    filas = [
        dict(fuente="API-Tennis (VPS intake)", medida="receipts", metodos=json.dumps(dict(metodos)), http=json.dumps(dict(estados)),
             archivos_respuesta_con_clave_odds_en_cabecera=con_odds,
             nota="los 147 registros son get_fixtures; no hay llamada de cuotas"),
        dict(fuente="PropLine precursor (VPS propline_data/tennis)", medida="archivos de cierre", metodos="",
             http="", archivos_respuesta_con_clave_odds_en_cabecera="",
             nota=f"archivos muestreados={len(bloques)//2}; cierre con cotizaciones={cerr_con}; cierre vacio={cerr_vacio}; captured_at min/max={min(capt) if capt else None}/{max(capt) if capt else None}"),
    ]
    write_csv(out / "cuotas_apitennis_propline_precursor.csv", filas)
    return dict(apitennis_metodos=dict(metodos), apitennis_estados=dict(estados), apitennis_odds_claves=con_odds,
                precursor_archivos=len(bloques) // 2, precursor_cierre_con=cerr_con, precursor_cierre_vacio=cerr_vacio,
                precursor_captured_at=(min(capt), max(capt)) if capt else None)


def _pt(value):
    from datetime import datetime, timezone
    v = value.replace("Z", "+00:00")
    t = datetime.fromisoformat(v)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def fnum_safe(x):
    return fnum(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--vps-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=WORKTREE / "docs/tenis_auditoria_tablas")
    ap.add_argument("--emit", action="store_true",
                    help="No escribe CSV: imprime bloques '@@ARCHIVO nombre' para que el shell los guarde "
                         "(en Windows, python.exe puede estar bloqueado por Controlled Folder Access).")
    args = ap.parse_args()
    EMIT["activo"] = args.emit
    args.out.mkdir(parents=True, exist_ok=True)
    ps = load_propline_shared(args.repo)
    resultados = {}
    resultados["tennisdata"] = seccion_tennis_data(args.repo, args.out)
    resultados["propline_piloto"] = seccion_propline_piloto(args.repo, args.out, ps)
    resultados["propline_produccion"] = seccion_propline_logs(args.vps_dir, args.out)
    resultados["theoddsapi"] = seccion_odds_api(args.vps_dir, args.repo, args.out)
    resultados["betsapi"] = seccion_betsapi_y_apitennis(args.vps_dir, args.out)
    resultados["apitennis_precursor"] = seccion_apitennis_y_pt(args.vps_dir, args.out)
    write_csv(args.out / "cuotas_fuentes_clasificacion.csv", FUENTES)
    resumen_json = {}
    for k, v in resultados.items():
        resumen_json[k] = {kk: vv for kk, vv in v.items() if kk not in ("margen_resumen", "series", "ganador_filas_margen", "margen")} \
            if isinstance(v, dict) else v
    if args.emit:
        for nombre, texto in EMIT["archivos"].items():
            print(f"@@ARCHIVO {nombre}")
            print(texto, end="")
            print("@@FIN")
    import sys
    print(json.dumps(resumen_json, ensure_ascii=False, indent=1, default=str), file=sys.stderr)


if __name__ == "__main__":
    main()
