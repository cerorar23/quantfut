"""Medición de mercados de NBA y tenis que escalera y parley aún no usan (2026-11-10).

Pregunta: ¿la probabilidad de referencia (consenso de casas sin margen,
``publish/referencia.py``) cumple lo que promete en spreads, totales, periodos y
props de NBA y en juegos, sets y props de tenis, dentro de las bandas en las que
escalera (p ≥ 0,69 y cuota 1,25–2,10) y parley (cuota 1,20–2,50) eligen?

Datos: los documentos ``/events/{id}/results`` del archivo compartido de
PropLine (desde el 24-oct-2026). Cada uno trae, por casa, la cuota y la
calificación (won/lost/push/void) de cada resultado. Límites que hay que leer
junto a cualquier cifra:

* la cuota es la que PropLine guarda con la calificación (la última antes del
  inicio), no la de la hora en que el lote decide: el consenso al cierre es más
  fino que el de la mañana;
* PropLine califica mal el ganador de tenis cuando gana quien hace menos juegos
  (medido el 29-oct): ``h2h`` de tenis NO se mide aquí;
* son pocas semanas; por eso los intervalos remuestrean PARTIDOS, no filas: las
  líneas alternativas de un mismo jugador y los dos lados de un contrato no son
  observaciones independientes.

Dos partes separadas a propósito (no se ajusta nada en el worker):

* ``extraer``: corre en el VPS, solo lee el archivo y escribe un CSV;
* ``medir``: corre en local sobre ese CSV. Bandas de cada producto con su
  intervalo, y un walk-forward purgado (bloques por fecha, embargo de un día, un
  partido nunca a los dos lados) que compara el mercado tal cual con la
  calibración Beta (Kull et al., 2017) y Venn-Abers inductivo (Vovk y Petej, 2014).

Es investigación: no cambia ningún selector ni promueve nada.
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np

CAMPOS = ("deporte", "evento", "fecha", "mercado", "periodo", "sujeto", "linea", "lado",
          "p", "casas", "pinnacle", "cuota", "cuota_todas", "gana")
SPORTS = {"nba": "basketball_nba", "tenis": "tennis"}
SIN_MEDIR = {("tenis", "h2h", "")}          # calificación de PropLine no fiable (ver docstring)
PASO = 0.002                                 # rejilla de probabilidad para ajustar calibradores
BLOQUES, EMBARGO_DIAS, DIAS_MIN_ENTRENO = 5, 1, 5
MIN_EVENTOS, MIN_FILAS = 30, 300
BOOTSTRAP = 500
_EPS = 1e-4


# ---------------------------------------------------------------- extracción (VPS)

def _decimal(american) -> float | None:
    try:
        raw = float(american)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(raw) or abs(raw) < 100:
        return None
    return 1 + (raw / 100 if raw > 0 else 100 / -raw)


def _linea_media(pt: float | None) -> bool:
    """Solo líneas .5 (como los selectores): una entera puede devolverse."""
    return pt is None or abs(abs(pt) % 1 - 0.5) < 1e-9


def contratos(filas: list[dict], excluidas: frozenset[str] | set[str] = frozenset()) -> dict:
    """Agrupa las filas de un evento en contratos de dos lados.

    Clave: (mercado, periodo, equipo, sujeto, primer lado, línea del primer lado).
    Over/Under comparten línea; en un hándicap el segundo lado lleva la línea opuesta.
    """
    grupos: dict[tuple, list[dict]] = defaultdict(list)
    for f in filas:
        if f.get("redacted") or f.get("bookmaker") in excluidas or not f.get("name"):
            continue
        grupos[(f["bookmaker"], f["market"], f.get("period") or "", f.get("team") or "",
                f.get("description") or "")].append(f)
    out: dict[tuple, dict] = {}
    for (casa, mk, per, team, desc), fs in grupos.items():
        nombres = sorted({f["name"] for f in fs})
        ou = set(nombres) <= {"Over", "Under"}
        if not ou and len(nombres) != 2:
            continue
        primero = "Over" if ou else nombres[0]
        for f in fs:
            pt = None if f.get("point") is None else float(f["point"])
            if not _linea_media(pt):
                continue
            lado = "A" if f["name"] == primero else "B"
            linea = pt if (pt is None or ou or lado == "A") else -pt
            c = out.setdefault((mk, per, team, desc, primero, linea),
                               {"casas": defaultdict(dict), "res": {"A": Counter(), "B": Counter()}})
            precio = _decimal(f.get("price_american"))
            if precio:
                c["casas"][casa][lado] = precio
            if f.get("resolution"):
                c["res"][lado][f["resolution"]] += 1
    return out


def _gana(res: dict) -> tuple[int, int] | None:
    """(gana A, gana B) si la calificación es won/lost y coherente; None si se devuelve o no cuadra."""
    lados = []
    for lado in ("A", "B"):
        if not res[lado]:
            return None
        r = res[lado].most_common(1)[0][0]
        if r not in ("won", "lost"):
            return None
        lados.append(1 if r == "won" else 0)
    return (lados[0], lados[1]) if sum(lados) == 1 else None


def registros(filas: list[dict], deporte: str, evento: str, fecha: str, *, soft_books, preferida: str,
              excluidas, probabilidades) -> list[dict]:
    """Una fila por lado de cada contrato con referencia (≥ 2 casas) y calificación limpia."""
    out = []
    for (mk, per, team, desc, primero, linea), c in contratos(filas, excluidas).items():
        mercado = mk + ("_equipo" if team else "")
        if (deporte, mercado, per) in SIN_MEDIR:
            continue
        gana = _gana(c["res"])
        if gana is None:
            continue
        completas = {casa: q for casa, q in c["casas"].items() if len(q) == 2}
        ref = probabilidades(completas, ("A", "B"), preferida=preferida)
        if ref is None:
            continue
        p, _ = ref
        for i, lado in enumerate(("A", "B")):
            todas = [q[lado] for q in c["casas"].values() if lado in q]
            soft = [q[lado] for casa, q in c["casas"].items() if lado in q and casa in soft_books]
            out.append(dict(deporte=deporte, evento=evento, fecha=fecha, mercado=mercado, periodo=per,
                            sujeto=desc or team, linea="" if linea is None else linea,
                            lado=primero if lado == "A" else "otro", p=round(p[lado], 5), casas=len(completas),
                            pinnacle=int(preferida in completas), cuota=max(soft) if soft else "",
                            cuota_todas=max(todas), gana=gana[i]))
    return out


def extraer(salida) -> dict:
    """Recorre el archivo compartido y escribe el CSV (gzip) en ``salida``. Solo lectura."""
    import sqlite3
    from pathlib import Path

    from qf.config import settings
    from qf.ingest import propline_shared as ps
    from qf.publish import referencia

    root = Path(settings.propline_archive)
    db = sqlite3.connect((root / "index.sqlite").resolve().as_uri() + "?mode=ro", uri=True)
    now = datetime.now(timezone.utc)
    excluidas = frozenset(ps.DFS_BOOKS | ps.EXCHANGES)
    soft = frozenset(settings.soft_books)
    cuenta: Counter = Counter()
    with gzip.open(salida, "wt", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, CAMPOS)
        w.writeheader()
        for deporte, sport in SPORTS.items():
            rutas = [r[0] for r in db.execute(
                "SELECT DISTINCT q.path FROM receipts p JOIN requests q ON q.id=p.request_id "
                "WHERE q.path LIKE ? AND p.status=200 AND p.error IS NULL",
                (f"/v1/sports/{sport}/events/%/results",))]
            for ruta in rutas:
                doc, recibo = ps.newest(root, ruta, now, max_age_seconds=ps.SETTLEMENT_MAX_AGE)
                if not doc or doc.get("status") != "final":
                    cuenta[f"{deporte}_no_final"] += 1
                    continue
                filas = [dict(bookmaker=b["key"], market=m["key"], period=m.get("period"), team=m.get("team"),
                              name=o.get("name"), description=o.get("description"), point=o.get("point"),
                              price_american=o.get("price"), resolution=o.get("resolution"),
                              redacted=o.get("redacted"))
                         for b in doc.get("bookmakers", []) for m in b.get("markets", [])
                         for o in m.get("outcomes", [])]
                fecha = (doc.get("commence_time") or recibo["received_at"])[:10]
                regs = registros(filas, deporte, ruta.split("/")[5], fecha, soft_books=soft,
                                 preferida=settings.sharp_book, excluidas=excluidas,
                                 probabilidades=referencia.probabilidades)
                w.writerows(regs)
                cuenta[f"{deporte}_eventos"] += 1
                cuenta[f"{deporte}_filas"] += len(regs)
    return dict(cuenta)


# ---------------------------------------------------------------- calibradores

def _agrupar(p: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(p de la rejilla, aciertos, n): ajustar sobre la rejilla da lo mismo y cuesta mucho menos."""
    k = np.round(np.asarray(p, float) / PASO).astype(int)
    u, inv = np.unique(k, return_inverse=True)
    return np.clip(u * PASO, _EPS, 1 - _EPS), np.bincount(inv, weights=y), np.bincount(inv).astype(float)


def beta_ajustar(p: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Calibración Beta: logit(q) = a·ln p − b·ln(1 − p) + c, con a, b ≥ 0 (Kull et al., 2017)."""
    from sklearn.linear_model import LogisticRegression

    x, s, n = _agrupar(p, y)
    X = np.column_stack([np.log(x), -np.log1p(-x)])
    X2, y2, w2 = np.vstack([X, X]), np.r_[np.ones(len(x)), np.zeros(len(x))], np.r_[s, n - s]
    ok = w2 > 0

    def ajuste(cols):
        m = LogisticRegression(C=1e6, max_iter=2000).fit(X2[ok][:, cols], y2[ok], sample_weight=w2[ok])
        coef = np.zeros(2)
        coef[cols] = m.coef_[0]
        return float(coef[0]), float(coef[1]), float(m.intercept_[0])

    a, b, c = ajuste([0, 1])
    if a < 0:
        a, b, c = ajuste([1])
    elif b < 0:
        a, b, c = ajuste([0])
    return a, b, c


def beta_aplicar(params: tuple[float, float, float], p: np.ndarray) -> np.ndarray:
    a, b, c = params
    x = np.clip(np.asarray(p, float), _EPS, 1 - _EPS)
    return 1 / (1 + np.exp(-(a * np.log(x) - b * np.log1p(-x) + c)))


def venn_abers(p_fit: np.ndarray, y_fit: np.ndarray, p_nuevo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(p0, p1) de Venn-Abers inductivo: la isotónica ajustada con el punto nuevo etiquetado 0 y 1."""
    from sklearn.isotonic import IsotonicRegression

    x, s, n = _agrupar(p_fit, y_fit)
    k = np.round(np.asarray(p_nuevo, float) / PASO).astype(int)
    u, inv = np.unique(k, return_inverse=True)
    p0, p1 = np.empty(len(u)), np.empty(len(u))
    for i, v in enumerate(np.clip(u * PASO, _EPS, 1 - _EPS)):
        for etiqueta, destino in ((0.0, p0), (1.0, p1)):
            iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
            iso.fit(np.r_[x, v], np.r_[s / n, etiqueta], sample_weight=np.r_[n, 1.0])
            destino[i] = float(iso.predict([v])[0])
    return p0[inv], p1[inv]


def venn_abers_punto(p0: np.ndarray, p1: np.ndarray) -> np.ndarray:
    """Probabilidad única a partir del intervalo (la que minimiza la pérdida logarítmica en el peor caso)."""
    return p1 / (1 - p0 + p1)


# ---------------------------------------------------------------- partición y métricas

def bloques(fechas: np.ndarray, n_bloques: int = BLOQUES, embargo_dias: int = EMBARGO_DIAS,
            dias_min_entreno: int = DIAS_MIN_ENTRENO) -> list[tuple[np.ndarray, np.ndarray]]:
    """Walk-forward con ventana creciente: [(máscara de entreno, máscara de prueba)].

    Cada evento tiene una sola fecha, así que nunca cae a los dos lados. El embargo
    deja fuera del entreno los días pegados al inicio de la prueba.
    """
    f = np.asarray(fechas, dtype="datetime64[D]")
    dias = np.unique(f)
    resto = dias[dias_min_entreno + embargo_dias:]
    if len(resto) == 0:
        return []
    out = []
    for trozo in np.array_split(resto, min(n_bloques, len(resto))):
        test = (f >= trozo[0]) & (f <= trozo[-1])
        train = f < trozo[0] - np.timedelta64(embargo_dias, "D")
        if train.any() and test.any():
            out.append((train, test))
    return out


def logloss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    q = np.clip(p, _EPS, 1 - _EPS)
    return -(y * np.log(q) + (1 - y) * np.log(1 - q))


def ece(p: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
    k = np.minimum((p * n_bins).astype(int), n_bins - 1)
    n = np.bincount(k, minlength=n_bins)
    hueco = np.abs(np.bincount(k, weights=y, minlength=n_bins) - np.bincount(k, weights=p, minlength=n_bins))
    return float(hueco.sum() / max(n.sum(), 1))


def ic_por_evento(valores: np.ndarray, eventos: np.ndarray, repeticiones: int = BOOTSTRAP,
                  semilla: int = 7) -> tuple[float, float, float]:
    """(media, IC 2,5 %, IC 97,5 %) remuestreando eventos enteros."""
    cod = np.unique(eventos, return_inverse=True)[1]
    g = int(cod.max()) + 1
    suma, n = np.bincount(cod, weights=valores, minlength=g), np.bincount(cod, minlength=g)
    idx = np.random.default_rng(semilla).integers(0, g, (repeticiones, g))
    medias = suma[idx].sum(1) / n[idx].sum(1)
    return float(suma.sum() / n.sum()), float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))


# ---------------------------------------------------------------- medición (local)

def _bandas(deporte: str) -> list[tuple[str, callable]]:
    from qf.eval.parley_calibracion import BANDAS
    from qf.publish import escalera as es

    p_max = es.PROB_MAX_DEPORTE.get(deporte, es.PROB_MAX)
    out = [("escalera", lambda p, c: (p >= es.PROB_MIN) & (p <= p_max) & (c >= es.CUOTA_MIN) & (c <= es.CUOTA_MAX))]
    for lo, hi, nombre in BANDAS:
        out.append((f"parley {nombre}", lambda p, c, lo=lo, hi=hi: (c >= lo) & (c < hi)))
    return out


def medir_bandas(df) -> list[dict]:
    """Acierto frente a lo prometido en cada banda de producto, por familia de mercado."""
    out = []
    for (deporte, familia), z in df.groupby(["deporte", "familia"], sort=True):
        z = z[z.cuota.notna()]
        p, c, y, ev = z.p.to_numpy(), z.cuota.to_numpy(), z.gana.to_numpy(float), z.evento.to_numpy()
        for nombre, regla in _bandas(deporte):
            m = regla(p, c)
            n_ev = len(np.unique(ev[m]))
            fila = dict(deporte=deporte, familia=familia, banda=nombre, filas=int(m.sum()), eventos=n_ev)
            if n_ev >= MIN_EVENTOS and m.sum() >= MIN_FILAS:
                hueco, lo, hi = ic_por_evento(y[m] - p[m], ev[m])
                roi, rlo, rhi = ic_por_evento(y[m] * c[m] - 1, ev[m])
                fila.update(p_media=float(p[m].mean()), acierto=float(y[m].mean()), hueco=hueco, hueco_ic=(lo, hi),
                            cuota_media=float(c[m].mean()), rendimiento=roi, rendimiento_ic=(rlo, rhi))
            else:
                fila["estado"] = "muestra insuficiente"
            out.append(fila)
    return out


def medir_calibradores(df) -> list[dict]:
    """Walk-forward purgado: pérdida logarítmica fuera de muestra del mercado, Beta y Venn-Abers."""
    out = []
    for (deporte, familia), z in df.groupby(["deporte", "familia"], sort=True):
        p, y, ev = z.p.to_numpy(), z.gana.to_numpy(float), z.evento.to_numpy()
        pred = {m: np.full(len(z), np.nan) for m in ("mercado", "beta", "venn_abers")}
        for train, test in bloques(z.fecha.to_numpy()):
            if len(np.unique(ev[train])) < MIN_EVENTOS:
                continue
            pred["mercado"][test] = p[test]
            pred["beta"][test] = beta_aplicar(beta_ajustar(p[train], y[train]), p[test])
            pred["venn_abers"][test] = venn_abers_punto(*venn_abers(p[train], y[train], p[test]))
        m = ~np.isnan(pred["mercado"])
        fila = dict(deporte=deporte, familia=familia, filas=int(m.sum()), eventos=len(np.unique(ev[m])))
        if fila["eventos"] < MIN_EVENTOS or fila["filas"] < MIN_FILAS:
            fila["estado"] = "muestra insuficiente"
        else:
            base = logloss(pred["mercado"][m], y[m])
            fila.update(logloss_mercado=float(base.mean()), ece_mercado=ece(pred["mercado"][m], y[m]))
            for metodo in ("beta", "venn_abers"):
                d, lo, hi = ic_por_evento(logloss(pred[metodo][m], y[m]) - base, ev[m])
                fila[metodo] = dict(delta_logloss=d, ic=(lo, hi), ece=ece(pred[metodo][m], y[m]))
        out.append(fila)
    return out


def cargar(ruta: str):
    import pandas as pd

    df = pd.read_csv(ruta, dtype={"evento": str, "periodo": str, "sujeto": str}, keep_default_na=False,
                     na_values={"cuota": [""], "linea": [""]})
    df["familia"] = df.mercado + np.where(df.periodo != "", "@" + df.periodo, "")
    return df


def medir(ruta: str) -> dict:
    df = cargar(ruta)
    resumen = df.groupby("deporte").agg(filas=("gana", "size"), eventos=("evento", "nunique"),
                                        desde=("fecha", "min"), hasta=("fecha", "max"),
                                        con_cuota=("cuota", "count")).reset_index().to_dict("records")
    return dict(creado=datetime.now(timezone.utc).isoformat(timespec="seconds"), resumen=resumen,
                parametros=dict(bloques=BLOQUES, embargo_dias=EMBARGO_DIAS, min_eventos=MIN_EVENTOS,
                                min_filas=MIN_FILAS, bootstrap=BOOTSTRAP),
                bandas=medir_bandas(df), calibradores=medir_calibradores(df))


def informe(r: dict) -> str:
    """Tablas en Markdown: solo las filas con muestra; las demás se cuentan."""
    pc = lambda v: f"{100 * v:+.1f}".replace(".", ",")
    out = ["| Deporte | Familia | Banda | Filas | Partidos | p media | Acierto | Hueco pp (IC 95 %) | Rendimiento % (IC 95 %) |",
           "|---|---|---|---:|---:|---:|---:|---|---|"]
    for b in r["bandas"]:
        if "hueco" in b:
            out.append(f"| {b['deporte']} | {b['familia']} | {b['banda']} | {b['filas']} | {b['eventos']} | "
                       f"{b['p_media']:.3f} | {b['acierto']:.3f} | {pc(b['hueco'])} ({pc(b['hueco_ic'][0])} a {pc(b['hueco_ic'][1])}) | "
                       f"{pc(b['rendimiento'])} ({pc(b['rendimiento_ic'][0])} a {pc(b['rendimiento_ic'][1])}) |")
    out += ["", f"Bandas sin muestra: {sum('hueco' not in b for b in r['bandas'])}.", "",
            "| Deporte | Familia | Filas | Partidos | Log-loss mercado | ECE mercado | Δ Beta (IC 95 %) | Δ Venn-Abers (IC 95 %) |",
            "|---|---|---:|---:|---:|---:|---|---|"]
    d = lambda m: f"{m['delta_logloss']:+.4f} ({m['ic'][0]:+.4f} a {m['ic'][1]:+.4f})"
    for c in r["calibradores"]:
        if "beta" in c:
            out.append(f"| {c['deporte']} | {c['familia']} | {c['filas']} | {c['eventos']} | {c['logloss_mercado']:.4f} | "
                       f"{c['ece_mercado']:.4f} | {d(c['beta'])} | {d(c['venn_abers'])} |")
    out += ["", f"Familias sin muestra para el walk-forward: {sum('beta' not in c for c in r['calibradores'])}."]
    return "
".join(out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["extraer"]:
        print(json.dumps(extraer(sys.argv[2])), file=sys.stderr)
    elif sys.argv[1:2] == ["medir"]:
        json.dump(medir(sys.argv[2]), sys.stdout, indent=1, default=float)
    elif sys.argv[1:2] == ["informe"]:
        sys.stdout.reconfigure(encoding="utf-8")
        print(informe(json.load(open(sys.argv[2], encoding="utf-8"))))
    else:
        sys.exit("uso: python -m qf.eval.mercados_nuevos extraer <salida.csv.gz> | medir <entrada.csv.gz> | informe <medicion.json>")
