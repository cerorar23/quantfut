"""Respaldo interno a partir de capturas SharpAPI locales. Este lector no tiene cliente HTTP."""
from __future__ import annotations

import gzip
import json
import math
import os
import zlib
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from qf.ingest import propline_shared as pl
from qf.ingest.cuotas_therundown import norm

FUENTE = "sharpapi"
SUFIJO = "|sharpapi"
EDAD_MAX = timedelta(hours=6)
TOLERANCIA = timedelta(minutes=30)
CASAS = {"draftkings", "fanduel"}
LIGAS_FUTBOL = {
    "soccer_epl": "england_-_premier_league",
    "soccer_spain_la_liga": "spain_-_la_liga",
    "soccer_italy_serie_a": "italy_-_serie_a",
    "soccer_germany_bundesliga": "germany_-_bundesliga",
    "soccer_france_ligue_one": "france_-_ligue_1",
    "soccer_netherlands_eredivisie": "netherlands_-_eredivisie",
    "soccer_portugal_primeira_liga": "portugal_-_primeira_liga",
    "soccer_brazil_campeonato": "brazil_-_serie_a",
    "soccer_mexico_ligamx": "mexico_-_liga_mx",
}
MERCADOS_FUTBOL = {
    "moneyline_3way": "h2h", "moneyline_3-way": "h2h", "moneyline": "h2h", "total_goals": "totals",
    "asian_handicap": "spreads", "both_teams_to_score": "btts", "total_corners": "corners",
    "total_cards": "cards", "double_chance": "double_chance", "team_total_goals": "team_totals",
    "team_total_corners": "team_corners", "1st_half_both_teams_to_score": "ht_btts",
    "1st_half_total_goals": "ht_goal", "team_to_win_to_nil": "win_to_nil",
    "draw_no_bet": "draw_no_bet",
}
DOBLE_OPORTUNIDAD = {"home draw": "1X", "away draw": "X2", "home away": "12"}
MERCADOS = {
    "nba": {"winner": ("moneyline",), "game_total": ("total_points",), "team_points": ("team_total",),
            "player_points": ("player_points",), "player_rebounds": ("player_rebounds",),
            "player_assists": ("player_assists",), "player_threes": ("player_made_threes", "player_threes"),
            "player_steals": ("player_steals",), "player_blocks": ("player_blocks",),
            "player_turnovers": ("player_turnovers",), "player_blocks_steals": ("player_steals_+_blocks",),
            "player_points_rebounds": ("player_points_+_rebounds",),
            "player_points_assists": ("player_points_+_assists",),
            "player_rebounds_assists": ("player_rebounds_+_assists",),
            "player_points_rebounds_assists": ("player_points_+_rebounds_+_assists",)},
    "tenis": {"winner": ("moneyline",), "games_total": ("total_games",), "games_handicap": ("game_spread",),
              "sets_total": ("total_sets",), "sets_handicap": ("set_spread", "set_handicap"),
              "tiebreak": ("total_tiebreaks",), "set_winner": ("moneyline",)},
}


def raiz(configurada=None) -> Path | None:
    ruta = configurada if configurada is not None else os.getenv("CUOTAS_SHARPAPI_ARCHIVO")
    return Path(ruta) if ruta else None


def _deporte(cabecera):
    deporte = str(cabecera.get("deporte") or cabecera.get("sport") or "").lower()
    if deporte in ("futbol", "soccer") or (not deporte and cabecera.get("liga") in LIGAS_FUTBOL.values()):
        return "futbol"
    if deporte in ("nba", "basketball") and cabecera.get("liga") in ("nba", "basketball_nba"):
        return "nba"
    if deporte in ("tenis", "tennis"):
        return "tenis"
    return None


def _igual(a, b):
    return bool(norm(a)) and norm(a) == norm(b)


class Archivo:
    def __init__(self, ruta: Path, now: datetime):
        self.ruta = ruta
        self.now = now
        self._dias = {}

    def _capturas(self, dia):
        if dia not in self._dias:
            capturas = {}
            for ruta in (self.ruta / dia.isoformat()).glob("*/*.jsonl.gz"):
                try:
                    marca = datetime.strptime(ruta.name, "%Y%m%dT%H%M%SZ.jsonl.gz").replace(tzinfo=timezone.utc)
                    if not self.now - EDAD_MAX - timedelta(seconds=1) <= marca <= self.now:
                        continue
                    with gzip.open(ruta, "rt", encoding="utf-8") as archivo:
                        cabecera = json.loads(next(archivo))
                    recibido = pl.parse_time(cabecera["capturado"])
                    inicio = pl.parse_time(cabecera["inicio"])
                    evento = cabecera["evento"]
                    deporte = _deporte(cabecera)
                    if not deporte or not isinstance(evento, str) or not self.now - EDAD_MAX <= recibido <= self.now < inicio:
                        continue
                    clave = (deporte, evento)
                    anterior = capturas.get(clave)
                    if anterior is None or recibido > anterior[0]:
                        capturas[clave] = (recibido, inicio, cabecera, ruta)
                except (OSError, EOFError, StopIteration, ValueError, TypeError, KeyError, AttributeError, zlib.error):
                    continue
            self._dias[dia] = capturas
        return self._dias[dia]

    def buscar(self, deporte, local, visita, inicio, *, liga=None, igual=_igual):
        if inicio <= self.now:
            return None
        liga_esperada = LIGAS_FUTBOL.get(liga) if deporte == "futbol" else None
        dia = inicio.astimezone(timezone.utc).date()
        candidatos = {}
        comparar = lru_cache(maxsize=None)(igual)
        for d in (dia - timedelta(days=1), dia, dia + timedelta(days=1)):
            for (tipo, evento), captura in self._capturas(d).items():
                recibido, comienzo, cabecera, _ = captura
                if tipo != deporte or abs(comienzo - inicio) > TOLERANCIA or recibido >= inicio:
                    continue
                if liga_esperada and cabecera.get("liga") != liga_esperada:
                    continue
                a, b = cabecera.get("local"), cabecera.get("visita")
                if not all(isinstance(n, str) and n for n in (a, b)):
                    continue
                directo = comparar(a, local) and comparar(b, visita)
                inverso = deporte == "tenis" and comparar(a, visita) and comparar(b, local)
                if directo == inverso:
                    continue
                anterior = candidatos.get(evento)
                if anterior is None or recibido > anterior[0][0]:
                    candidatos[evento] = (captura, inverso)
        if len(candidatos) != 1:
            return None
        evento, ((recibido, _, cabecera, ruta), inverso) = next(iter(candidatos.items()))
        try:
            with gzip.open(ruta, "rt", encoding="utf-8") as archivo:
                next(archivo)
                filas = [json.loads(linea) for linea in archivo]
            if cabecera.get("filas") != len(filas):
                return None
        except (OSError, EOFError, StopIteration, ValueError, TypeError, zlib.error):
            return None
        return evento, recibido, cabecera, inverso, filas


def _numero(valor):
    if isinstance(valor, bool):
        return None
    try:
        n = float(valor)
        return (n + 0.0) if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def filas_validas(captura):
    _, recibido, cabecera, inverso, filas = captura
    for fila in filas:
        if (not isinstance(fila, dict) or not isinstance(fila.get("sportsbook"), str)
                or not isinstance(fila.get("market_type"), str) or fila["sportsbook"] not in CASAS or fila.get("is_live")
                or fila.get("is_active") is False or fila.get("is_stale_pregame_price")):
            continue
        precio, linea = _numero(fila.get("odds_decimal")), _numero(fila.get("line"))
        if precio is None or precio <= 1 or (fila.get("line") is not None and linea is None):
            continue
        if fila.get("timestamp"):
            try:
                if not recibido - EDAD_MAX <= pl.parse_time(fila["timestamp"]) <= recibido:
                    continue
            except (TypeError, ValueError, AttributeError):
                continue
        seleccion = norm(fila.get("selection"))
        lado = fila.get("team_side")
        if lado not in ("home", "away", "draw"):
            lado = next((k for k, n in (("home", cabecera["local"]), ("away", cabecera["visita"]))
                         if seleccion and seleccion == norm(n)), None)
        if inverso:
            lado = {"home": "away", "away": "home"}.get(lado, lado)
        tipo = norm(fila.get("selection_type"))
        yield fila, precio, linea, lado, tipo, seleccion


def filas_futbol(captura):
    """Traduce los mercados de fútbol con equivalencia explícita en las fichas."""
    out, ganadores = [], {}
    for f, precio, linea, lado, tipo, seleccion in filas_validas(captura):
        mercado = MERCADOS_FUTBOL.get(f.get("market_type"))
        segmento = f.get("market_segment")
        if mercado in ("ht_btts", "ht_goal"):
            if segmento not in (None, "1st_half"):
                continue
        elif segmento not in (None, "full_game"):
            continue
        if mercado == "h2h":
            seleccion = lado or ("draw" if tipo == "draw" or seleccion in ("draw", "tie", "empate") else None)
            linea = None
        elif mercado == "spreads":
            seleccion = lado if linea is not None and lado in ("home", "away") else None
        elif mercado == "draw_no_bet":
            mercado, seleccion, linea = "spreads", lado if lado in ("home", "away") else None, 0.0
        elif mercado in ("totals", "corners", "cards"):
            seleccion = next((s for s in (tipo, seleccion) if s in ("over", "under")), None) if linea is not None else None
        elif mercado in ("team_totals", "team_corners"):
            equipo, _, direccion = tipo.partition(" ")
            if linea is None or equipo not in ("home", "away") or direccion not in ("over", "under"):
                continue
            prefijo = "team_totals" if mercado == "team_totals" else "corners"
            mercado, seleccion = f"{prefijo}_{equipo}", direccion
        elif mercado == "double_chance":
            seleccion, linea = DOBLE_OPORTUNIDAD.get(tipo), None
        elif mercado in ("btts", "ht_btts"):
            seleccion = next((s for s in (tipo, seleccion) if s in ("yes", "no")), None)
            linea = None
        elif mercado == "ht_goal":
            direccion = next((s for s in (tipo, seleccion) if s in ("over", "under")), None)
            seleccion = {"over": "yes", "under": "no"}.get(direccion) if linea == 0.5 else None
            linea = None
        elif mercado == "win_to_nil":
            equipo, _, resultado = tipo.partition(" ")
            if equipo not in ("home", "away") or resultado not in ("", "yes") or (lado and lado != equipo):
                continue
            seleccion = equipo
            linea = None
        else:
            continue
        if seleccion:
            fila = dict(bookmaker=f["sportsbook"], market=mercado, selection=seleccion, line=linea, price=precio)
            if mercado == "h2h":
                ganadores.setdefault((f["sportsbook"], f["market_type"]), []).append(fila)
            else:
                out.append(fila)
    # Un moneyline de dos lados en fútbol puede liquidar el empate como nulo.
    for filas in ganadores.values():
        if {f["selection"] for f in filas} == {"home", "draw", "away"}:
            out.extend(filas)
    return out


def filas_item(deporte, item, filas):
    mercado = item["market"]
    origen = MERCADOS[deporte].get(mercado, ())
    segmentos = (None, "full_game")
    if mercado == "set_winner":
        numero = item.get("set_number")
        if type(numero) is not int or not 1 <= numero <= 5:
            return []
        sufijo = {1: "st", 2: "nd", 3: "rd"}.get(numero, "th")
        segmento = f"{numero}{sufijo}_set"
        origen = (f"{segmento}_moneyline",)
        segmentos = (None, segmento)
    out = []
    for f, precio, linea, lado, tipo, seleccion in filas:
        if f.get("market_type") not in origen or f.get("market_segment") not in segmentos:
            continue
        if mercado.startswith("player_") and not _igual(f.get("player_name"), item.get("player_name")):
            continue
        if mercado in ("winner", "games_handicap", "sets_handicap", "set_winner"):
            if lado not in ("home", "away"):
                continue
            if deporte == "tenis":
                lado = {"home": "A", "away": "B"}[lado]
            nombre = lado
            if mercado in ("winner", "set_winner"):
                linea = None
        else:
            if mercado == "team_points":
                equipo, _, tipo = tipo.partition(" ") if tipo.startswith(("home ", "away ")) else (lado, "", tipo)
                if equipo is None or equipo != item.get("team_side"):
                    continue
            nombre = next((s for s in (tipo, seleccion) if s in ("over", "under")), None)
            if mercado == "tiebreak" and linea == 0.5:
                nombre, linea = {"over": "yes", "under": "no"}.get(nombre), None
            if nombre is None or linea != item.get("line"):
                continue
            lado = None
        out.append(dict(bookmaker=f["sportsbook"], name=nombre, side=lado, point=linea, price_decimal=precio))
    return out
