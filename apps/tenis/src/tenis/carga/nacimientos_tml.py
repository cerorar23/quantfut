"""Fechas de nacimiento estimadas desde las edades de los CSV de TML (17-nov-2026).

TML no trae fechas de nacimiento, pero cada partido trae `winner_age` y `loser_age`: la edad decimal (3 decimales, unos 0,4
días) en la fecha de inicio del torneo (`tourney_date`). Con eso, `nacimiento = tourney_date - edad * 365,25 días`, y la
mediana por jugador deja un error de décimas de día. Medido contra las 1.135 fechas exactas de SofaScore que TML y SofaScore
comparten: error absoluto mediano 0,0 días, p99 0,4 días, máximo 9 días (jugadores con 2 partidos).

Reglas (nada se inventa; lo dudoso se descarta y se cuenta):
- Solo edades entre 12 y 60 años. Un jugador con edades inconsistentes (p90 - p10 de sus estimaciones > 30 días: id reutilizado
  o error de captura) se descarta.
- No se toca ningún jugador que ya tenga una `fecha_nacimiento` de cualquier fuente (SofaScore es exacta y tiene prioridad).
- Un id de TML con más de un jugador no anulado es ambiguo: se descarta.
- Se guarda como aserción `fecha_nacimiento` de fuente `tml` con un `recibo` retro (la fecha de nacimiento es un hecho válido en
  cualquier corte; la exportación PIT solo usa aserciones retro) cuyo original es la lista de estimaciones con su n y dispersión.
- Idempotente: lo ya cubierto no se repite. Pensado para correr tras cada carga semanal de TML (jugadores nuevos).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from psycopg.types.json import Jsonb

from ..recibo import nuevo_recibo

FUENTE = "tml"
RECURSO = "nacimientos_estimados_de_edad"
COLUMNAS = ("tourney_date", "winner_id", "winner_age", "loser_id", "loser_age")
EDAD_MIN, EDAD_MAX = 12.0, 60.0
MAX_DISPERSION_DIAS = 30.0
_ORIGEN = pd.Timestamp("1900-01-01")


def leer_edades(carpeta: Path) -> pd.DataFrame:
    """Observaciones (id, fecha, edad) de todos los CSV de partidos de la carpeta (los que traen las columnas de edad)."""
    partes = []
    for ruta in sorted(Path(carpeta).glob("*.csv")):
        try:
            d = pd.read_csv(ruta, dtype=str, low_memory=False)
        except (OSError, ValueError, pd.errors.ParserError):
            continue
        if not set(COLUMNAS) <= set(d.columns):
            continue                                              # ATP_Database.csv, torneos en curso, etc.
        for lado in ("winner", "loser"):
            x = d[["tourney_date", f"{lado}_id", f"{lado}_age"]].dropna()
            x.columns = ["fecha", "id", "edad"]
            partes.append(x)
    if not partes:
        return pd.DataFrame({"id": pd.Series(dtype=str), "fecha": pd.Series(dtype="datetime64[ns]"),
                             "edad": pd.Series(dtype=float)})
    t = pd.concat(partes, ignore_index=True)
    t["fecha"] = pd.to_datetime(t["fecha"], format="%Y%m%d", errors="coerce")
    t["edad"] = pd.to_numeric(t["edad"], errors="coerce")
    t = t.dropna()
    return t[(t["edad"] > EDAD_MIN) & (t["edad"] < EDAD_MAX)].reset_index(drop=True)


def estimar(obs: pd.DataFrame) -> tuple[pd.DataFrame, Counter]:
    """DataFrame (id, nacimiento: date, n, dispersion_dias) y contadores de descartes."""
    cont: Counter = Counter()
    if obs.empty:
        return pd.DataFrame(columns=["id", "nacimiento", "n", "dispersion_dias"]), cont
    dias = (obs["fecha"] - pd.to_timedelta(obs["edad"] * 365.25, unit="D") - _ORIGEN).dt.total_seconds() / 86400
    g = pd.DataFrame({"id": obs["id"], "dias": dias}).groupby("id")["dias"]
    est = pd.DataFrame({"n": g.size(), "mediana": g.median(), "p10": g.quantile(0.10), "p90": g.quantile(0.90)})
    est["dispersion_dias"] = est["p90"] - est["p10"]
    ok = est["dispersion_dias"] <= MAX_DISPERSION_DIAS
    cont["descartado_edades_inconsistentes"] = int((~ok).sum())
    est = est[ok].reset_index()
    est["nacimiento"] = [(_ORIGEN + timedelta(days=round(float(m)))).date() for m in est["mediana"]]
    cont["estimados"] = len(est)
    return est[["id", "nacimiento", "n", "dispersion_dias"]], cont


def cargar(db, estimaciones: pd.DataFrame, raiz, ahora: datetime | None = None, ensayo: bool = False,
           etiqueta: str = "") -> Counter:
    """Escribe las aserciones que faltan en una transacción. `ensayo` calcula todo y no escribe."""
    ahora = ahora or datetime.now(timezone.utc)
    cont: Counter = Counter()
    alias: dict[str, set[int]] = {}
    for idt, jid in db.execute(
            "SELECT a.id_fuente, a.jugador_id FROM jugador_alias a WHERE a.fuente = %s "
            "AND NOT EXISTS (SELECT 1 FROM jugador_alias z WHERE z.anula_a = a.alias_id)", (FUENTE,)).fetchall():
        alias.setdefault(idt, set()).add(jid)
    con_fecha = {r[0] for r in db.execute(
        "SELECT DISTINCT jugador_id FROM jugador_asercion WHERE campo = 'fecha_nacimiento'").fetchall()}
    nuevas: list[tuple[int, date, int, float, str]] = []
    vistos: set[int] = set()
    for fila in estimaciones.itertuples(index=False):
        ids = alias.get(str(fila.id))
        if not ids:
            cont["sin_jugador_en_la_base"] += 1
        elif len(ids) > 1:
            cont["id_ambiguo"] += 1
        else:
            jid = next(iter(ids))
            if jid in con_fecha or jid in vistos:
                cont["ya_tenia_fecha"] += 1
            else:
                vistos.add(jid)
                nuevas.append((jid, fila.nacimiento, int(fila.n), float(fila.dispersion_dias), str(fila.id)))
    cont["a_escribir"] = len(nuevas)
    cont["escritas"] = 0
    if not nuevas or ensayo:
        return cont
    cuerpo = json.dumps(
        {"fuente": "edades de los CSV de TML", "regla": "tourney_date - edad*365.25 d, mediana por jugador",
         "estimaciones": [{"id_tml": i, "nacimiento": n.isoformat(), "partidos": c, "dispersion_dias": round(d, 2)}
                          for _, n, c, d, i in nuevas]}, sort_keys=True, ensure_ascii=False).encode("utf-8")
    with db.transaction():
        r = nuevo_recibo(raiz, fuente=FUENTE, recurso=RECURSO, retro=True, recibido_en=ahora, cuerpo=cuerpo,
                         parametros={"origen": etiqueta or "snapshot_tml", "jugadores": len(nuevas)})
        fila = db.execute(
            "INSERT INTO recibo (fuente, recurso, parametros, recibido_en, estado_http, sha256, ruta_objeto, bytes, lote, "
            "retro) VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s, true) "
            "ON CONFLICT (fuente, recurso, sha256, recibido_en) DO NOTHING RETURNING recibo_id",
            (r.fuente, r.recurso, Jsonb(r.parametros), r.recibido_en, r.sha256, r.ruta_objeto, r.bytes,
             f"nacimientos_tml_{ahora.strftime('%Y%m%dT%H%M%SZ')}")).fetchone()
        rid = fila[0] if fila else db.execute(
            "SELECT recibo_id FROM recibo WHERE fuente = %s AND recurso = %s AND sha256 = %s AND recibido_en = %s",
            (r.fuente, r.recurso, r.sha256, r.recibido_en)).fetchone()[0]
        db.cursor().executemany(
            "INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
            "VALUES (%s, 'fecha_nacimiento', %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            [(jid, nac.isoformat(), FUENTE, rid, ahora) for jid, nac, *_ in nuevas])
    cont["escritas"] = len(nuevas)
    return cont


def main(argv=None) -> int:
    import psycopg
    ap = argparse.ArgumentParser(description="Fechas de nacimiento estimadas desde las edades de TML")
    ap.add_argument("--snapshot", type=Path, required=True, help="carpeta con los CSV de TML (.../tml/originals)")
    ap.add_argument("--almacen", type=Path, required=True)
    ap.add_argument("--dsn", default=os.environ.get("PG_DSN"))
    ap.add_argument("--esquema", default="tenis")
    ap.add_argument("--ensayo", action="store_true", help="calcula y cuenta, sin escribir")
    a = ap.parse_args(argv)
    if not a.dsn or not re.fullmatch(r"[a-z_][a-z0-9_]*", a.esquema):
        print("falta --dsn o PG_DSN, o esquema no válido", file=sys.stderr)
        return 1
    try:
        est, desc = estimar(leer_edades(a.snapshot))
        with psycopg.connect(a.dsn, autocommit=True) as db:
            db.execute(f"SET search_path TO {a.esquema}, public")
            res = cargar(db, est, a.almacen, ensayo=a.ensayo, etiqueta=a.snapshot.parent.parent.name)
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1
    print(json.dumps({"ensayo": a.ensayo, **dict(desc), **dict(res)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
