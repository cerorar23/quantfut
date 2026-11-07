"""Adaptador offline de cuotas PropLine para tenis (plan tcnico, B.4, I.1, S5).

Solo lectura local sin red. Envuelve qf.ingest.propline_shared (newest, read_two_way, read_closing).
Aplica filtros estrictos de calidad:
  - Excluye cotizaciones en juego, suspendidas, congeladas, invlidas.
  - Excluye casas DFS y exchanges (EXCHANGE_OR_DFS).
  - Pareja de jugadores repetida en la misma observacin -> sin mercado (decisin del 24-oct).
  - Des-margina proporcionalmente las lneas con dos resultados.
"""
from __future__ import annotations

import gzip
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

from qf.ingest import propline_shared as ps

from .devig import devig_dos_vias

EXCHANGE_OR_DFS = frozenset({
    "kalshi", "polymarket", "polymarket_us", "matchbook", "smarkets", "novig", "prophetx", "sx_bet",
    "betfair_exchange", "betfair_ex", "betfair_ex_eu", "betfair_ex_au", "betfair", "betfair_ex_uk",
    "prizepicks", "underdog", "sleeper", "dabble", "parlayplay", "draftkings_pick6", "thrillzz", "courtside"
}) | set(ps.DFS_BOOKS) | set(ps.EXCHANGES)

BANDERAS_EXCLUSION = frozenset({
    "invalid_price",
    "in_play_or_started",
    "suspended",
    "frozen_pregame_book",
    "dfs_not_single_bet",
    "exchange_contract_requires_rules",
    "redacted",
    "restricted_side",
})


def es_cotizacion_valida(q: dict, *, excluir_en_juego: bool = True) -> bool:
    """Verifica si una cotizacin es utilizable como referencia pre-partido."""
    if q.get("price_decimal") is None or q.get("price_decimal") <= 1.0:
        return False
    if q.get("bookmaker") in EXCHANGE_OR_DFS:
        return False
    flags = set(q.get("flags") or [])
    banderas = BANDERAS_EXCLUSION if excluir_en_juego else (BANDERAS_EXCLUSION - {"in_play_or_started"})
    if flags & banderas:
        return False
    return True


def leer_dos_vias_tenis(root: Path, as_of: datetime, max_age_seconds: int = 3900) -> tuple[list[dict] | None, dict | None]:
    """Lectura sin red y punto en el tiempo para tennis: envuelve ps.read_two_way."""
    return ps.read_two_way(root, "tennis", as_of, max_age_seconds=max_age_seconds)


def leer_cierre_evento(root: Path, event_id: str, as_of: datetime) -> tuple[list[dict] | None, dict | None]:
    """Lectura sin red del cierre de un evento de tenis: envuelve ps.read_closing."""
    return ps.read_closing(root, "tennis", event_id, as_of)


def extraer_mercados_dos_vias(quotes: Iterable[dict], *, excluir_en_juego: bool = False) -> list[dict]:
    """Agrupa cotizaciones en mercados de dos lados, descarta parejas repetidas y des-margina.

    Si una misma observacin contiene la pareja repetida con inconsistencias o ambigedades,
    se descarta (decisin 24-oct: 'sin mercado').
    """
    validas = [q for q in quotes if es_cotizacion_valida(q, excluir_en_juego=excluir_en_juego)]

    # Agrupar por contrato: (event_id, bookmaker, market, period, line_type, point, description)
    grupos = defaultdict(list)
    for q in validas:
        clave = (
            q["event_id"],
            q["bookmaker"],
            q.get("market"),
            q.get("period") or "-",
            q.get("line_type") or "-",
            abs(float(q["point"])) if q.get("point") is not None else None,
            q.get("description") or "",
        )
        grupos[clave].append(q)

    mercados = []
    for clave, items in grupos.items():
        ev_id, book, market, period, line_type, point_abs, desc = clave
        nombres = [x.get("name") for x in items]
        if len(items) != 2 or len(set(nombres)) != 2:
            # Si no son exactamente 2 cotizaciones con nombres distintos -> descartar (pareja repetida, un solo lado, etc.)
            continue

        q1, q2 = items[0], items[1]
        p1, p2, margen = devig_dos_vias(q1["price_decimal"], q2["price_decimal"])
        if p1 is None or p2 is None or margen is None:
            continue

        mercados.append({
            "event_id": ev_id,
            "bookmaker": book,
            "market": market,
            "period": period,
            "line_type": line_type,
            "point": q1.get("point"),
            "name_1": q1.get("name"),
            "odds_1": q1.get("price_decimal"),
            "prob_1": p1,
            "name_2": q2.get("name"),
            "odds_2": q2.get("price_decimal"),
            "prob_2": p2,
            "margen": margen,
            "received_at": q1.get("received_at"),
            "commence_time": q1.get("commence_time"),
        })

    return mercados


def cargar_ganadores_piloto(root_piloto: Path, *, excluir_en_juego: bool = False) -> list[dict]:
    """Carga todas las cotizaciones de ganador (h2h main) del archivo piloto local."""
    db_path = root_piloto / "index.sqlite"
    if not db_path.exists():
        raise FileNotFoundError(f"No existe index.sqlite en {root_piloto}")

    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    recibos = [dict(r) for r in db.execute(
        "SELECT q.path, p.request_id, p.received_at, p.status, p.body_path "
        "FROM receipts p JOIN requests q ON q.id = p.request_id "
        "WHERE q.path LIKE '%/tennis/odds' AND p.status = 200 "
        "ORDER BY p.received_at"
    )]
    db.close()

    todas_cuotas = []
    for r in recibos:
        cuerpo_path = root_piloto / r["body_path"]
        if not cuerpo_path.exists():
            continue
        with gzip.open(cuerpo_path, "rt", encoding="utf-8") as f:
            eventos = json.load(f)
        todas_cuotas.extend(ps.quotes(eventos, r["received_at"]))

    ganador_quotes = [
        q for q in todas_cuotas
        if q.get("market") == "h2h" and q.get("period") is None and q.get("line_type") == "main"
    ]
    return extraer_mercados_dos_vias(ganador_quotes, excluir_en_juego=excluir_en_juego)
