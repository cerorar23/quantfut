"""Calendario de tenis desde el archivo compartido de PropLine hacia `tenis.partido` y `tenis.programa` (17-nov-2026).

Sin esto el motor v2 no tiene partidos que pronosticar: `tenis-db` solo recibía TML (semanal, sin calendario futuro).

Fuente: los eventos de tenis que el recolector horario compartido ya archivó (`/v1/sports/tennis/odds`); no hace peticiones a
PropLine. Un script del servidor los extrae del archivo y los entrega a este módulo (`--stdin`).

Qué se carga y qué NO (nunca se inventa nada; lo que no se puede resolver va a `sin_resolver` con su motivo):
- Solo individuales de ATP, WTA y Challenger. ITF, UTR, dobles, Grand Slams (la ronda no viene y decide el formato), Next Gen,
  Copa Davis y demás quedan fuera.
- Torneo y superficie: PropLine no da superficie. El torneo se identifica por su ciudad entre los torneos que TML ya conoce
  del mismo circuito, en una semana parecida a la de años anteriores, y la superficie/indoor se copian de su edición más
  reciente. Torneo desconocido o ambiguo ⇒ `sin_resolver`.
- Jugadores: solo coincidencia EXACTA de nombre dentro del circuito y única. Nunca se crea un jugador.
- Ronda: PropLine no la trae; se guarda `R` (desconocida). Mejor de 3.
- Provenance: cada captura es un `recibo` (retro = false) con `recibido_en` = recepción real del archivo, de modo que el
  dato es visible solo desde entonces (regla en vivo de la exportación PIT).
- Idempotente: el cursor guarda el sha256 del archivo ya procesado; un partido/horario/enlace/sin_resolver no se repite.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from psycopg.types.json import Jsonb

from ..identidad.normalizar import tokens
from ..recibo import Recibo, nuevo_recibo
from .cursor import ejecutar_lote, leer as leer_cursor

FUENTE = "propline"
RECURSO = "/v1/sports/tennis/odds#calendario"
CURSOR = "calendario_tenis"
HORIZONTE = timedelta(hours=72)
MARGEN_INICIO = timedelta(minutes=5)     # un partido a punto de empezar ya no se puede sellar a tiempo
VENTANA_TORNEOS = timedelta(days=1100)   # ediciones consideradas para reconocer un torneo (≈ 3 años)
MAX_DISTANCIA_DIAS = 10                  # semana del evento frente a la de las ediciones anteriores del torneo
RONDA = "R"
TOURS = {"ATP": ("atp", False), "WTA": ("wta", False), "CHALLENGER": ("atp", True)}
NO_SOPORTADOS = re.compile(r"\b(itf|utr|davis|united cup|billie|laver|exhibition|olympic|next ?gen|qualif\w*|"
                           r"australian open|roland garros|french open|wimbledon|us open|u s open)\b", re.I)


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


@dataclass(frozen=True)
class Candidato:
    evento_id: str
    inicio: datetime
    local: str
    visitante: str
    torneo: str
    circuito: str
    challenger: bool


@dataclass
class Resultado:
    estado: str                                   # 'sin_cambios' | 'escrito' | 'vacio'
    partidos_nuevos: int = 0
    programas_nuevos: int = 0
    sin_resolver: int = 0
    descartes: dict = field(default_factory=dict)
    recibo_id: int | None = None


# ----------------------------------------------------------------------------------------------------------- análisis
def parse_instante(texto) -> datetime | None:
    if not isinstance(texto, str):
        return None
    try:
        d = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)


def analizar(eventos: list[dict], ahora: datetime) -> tuple[list[Candidato], Counter]:
    """Filtra los eventos del archivo a los candidatos que el modelo cubre. Puro, sin base ni red."""
    candidatos: list[Candidato] = []
    descartes: Counter = Counter()
    vistos: set[str] = set()
    for e in eventos:
        eid = str(e.get("id") or "")
        local, visitante = (e.get("home_team") or "").strip(), (e.get("away_team") or "").strip()
        torneo = (e.get("tournament") or "").strip()
        inicio = parse_instante(e.get("commence_time"))
        if not eid or not local or not visitante or inicio is None:
            descartes["evento_incompleto"] += 1
        elif eid in vistos:
            descartes["evento_repetido"] += 1
        elif e.get("is_outright"):
            descartes["outright"] += 1
        elif e.get("live"):
            descartes["en_vivo"] += 1
        elif inicio <= ahora + MARGEN_INICIO:
            descartes["ya_empezado"] += 1
        elif inicio > ahora + HORIZONTE:
            descartes["fuera_de_horizonte"] += 1
        elif str(e.get("tour") or "").upper() not in TOURS:
            descartes["tour_no_cubierto"] += 1
        elif "/" in local or "/" in visitante or "double" in torneo.lower():
            descartes["dobles"] += 1
        elif not torneo or NO_SOPORTADOS.search(torneo):
            descartes["torneo_no_soportado"] += 1
        else:
            circuito, challenger = TOURS[str(e["tour"]).upper()]
            vistos.add(eid)
            candidatos.append(Candidato(eid, inicio, local, visitante, torneo, circuito, challenger))
    return candidatos, descartes


# ------------------------------------------------------------------------------------------------- torneo y superficie
def lunes_de(dia: date) -> date:
    return dia - timedelta(days=dia.isoweekday() - 1)


def _distancia_anual(a: date, b: date) -> int:
    d = abs(a.timetuple().tm_yday - b.timetuple().tm_yday)
    return min(d, 365 - d)


def indice_torneos(db, hoy: date) -> dict[str, list[dict]]:
    """{circuito: [torneo con sus ediciones recientes con superficie]}. Solo lectura."""
    filas = db.execute(
        "SELECT t.torneo_id, t.circuito, t.nombre, t.categoria, e.lunes_semana, e.superficie, e.indoor "
        "FROM torneo t JOIN edicion e ON e.torneo_id = t.torneo_id "
        "WHERE e.superficie IS NOT NULL AND NOT e.por_equipos AND e.lunes_semana >= %s "
        "AND COALESCE(t.categoria, '') NOT IN ('equipos', 'JJOO', 'exhibicion', 'ITF')",
        (hoy - VENTANA_TORNEOS,)).fetchall()
    por_torneo: dict[int, dict] = {}
    for tid, circ, nombre, categoria, lunes, sup, indoor in filas:
        t = por_torneo.setdefault(tid, {"torneo_id": tid, "circuito": circ, "nombre": nombre, "categoria": categoria,
                                        "base": tuple(tokens(nombre)), "ediciones": []})
        t["ediciones"].append((lunes, sup, indoor))
    indice: dict[str, list[dict]] = defaultdict(list)
    for t in por_torneo.values():
        t["ediciones"].sort(reverse=True)
        indice[t["circuito"]].append(t)
    return indice


def _contiene(tokens_evento: list[str], base: tuple) -> bool:
    n = len(base)
    return n > 0 and any(tuple(tokens_evento[i:i + n]) == base for i in range(len(tokens_evento) - n + 1))


def resolver_torneo(indice: dict, c: Candidato) -> tuple[dict | None, str | None]:
    """(torneo con 'superficie' e 'indoor' de su edición más reciente, None) o (None, motivo)."""
    toks = tokens(c.torneo)
    torneos = indice.get(c.circuito, [])
    if "finals" in toks and not c.challenger:
        cand = [t for t in torneos if t["categoria"] == "Finales"]
        elegido = cand if len(cand) == 1 else []
        motivo_vacio = "torneo_sin_historial" if not cand else "torneo_ambiguo"
        if not elegido:
            return None, motivo_vacio
        t = elegido[0]
        return {**t, "superficie": t["ediciones"][0][1], "indoor": t["ediciones"][0][2]}, None
    # TML deja la categoría vacía cuando el nivel del torneo cambió entre años (p. ej. Montevideo): vale para ambos niveles.
    cand = [t for t in torneos if _contiene(toks, t["base"])
            and (t["categoria"] in ("Challenger", None) if c.challenger else t["categoria"] != "Challenger")]
    if not cand:
        return None, "torneo_sin_historial"
    largo = max(len(t["base"]) for t in cand)
    cand = [t for t in cand if len(t["base"]) == largo]
    dia = c.inicio.date()
    puntuados = sorted(
        ((min(_distancia_anual(dia, lunes + timedelta(days=3)) for lunes, _, _ in t["ediciones"]), t["torneo_id"], t)
         for t in cand), key=lambda x: (x[0], x[1]))
    mejor = puntuados[0]
    if mejor[0] > MAX_DISTANCIA_DIAS:
        return None, "torneo_fuera_de_calendario"
    sup_mejor = mejor[2]["ediciones"][0][1:]
    if any(d <= mejor[0] + 3 and t["ediciones"][0][1:] != sup_mejor for d, _, t in puntuados[1:]):
        return None, "torneo_ambiguo"
    t = mejor[2]
    return {**t, "superficie": sup_mejor[0], "indoor": sup_mejor[1]}, None


# ---------------------------------------------------------------------------------------------------------- escritura
def _insertar_recibo(db, r: Recibo, lote: str) -> int:
    fila = db.execute(
        "INSERT INTO recibo (fuente, recurso, parametros, recibido_en, estado_http, sha256, ruta_objeto, bytes, lote, "
        "retro) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, false) "
        "ON CONFLICT (fuente, recurso, sha256, recibido_en) DO NOTHING RETURNING recibo_id",
        (r.fuente, r.recurso, Jsonb(r.parametros), r.recibido_en, r.estado_http, r.sha256, r.ruta_objeto, r.bytes,
         lote)).fetchone()
    if fila:
        return fila[0]
    return db.execute("SELECT recibo_id FROM recibo WHERE fuente = %s AND recurso = %s AND sha256 = %s AND recibido_en = %s",
                      (r.fuente, r.recurso, r.sha256, r.recibido_en)).fetchone()[0]


def _a_sin_resolver(db, c: Candidato, motivo: str, rid: int, recibido: datetime) -> bool:
    if db.execute("SELECT 1 FROM sin_resolver WHERE fuente = %s AND id_fuente = %s AND motivo = %s",
                  (FUENTE, c.evento_id, motivo)).fetchone():
        return False
    db.execute("INSERT INTO sin_resolver (fuente, id_fuente, nombre_fuente, motivo, contexto, recibo_id, recibido_en) "
               "VALUES (%s, %s, %s, %s, %s, %s, %s)",
               (FUENTE, c.evento_id, f"{c.local} vs {c.visitante}", motivo,
                Jsonb({"torneo": c.torneo, "circuito": c.circuito, "inicio": c.inicio.isoformat()}), rid, recibido))
    return True


def _edicion(db, torneo: dict, c: Candidato, rid: int, recibido: datetime) -> int:
    lunes = lunes_de(c.inicio.date())
    previa = db.execute("SELECT edicion_id, lunes_semana FROM edicion WHERE torneo_id = %s AND temporada = %s AND fuente = %s "
                        "ORDER BY recibido_en DESC LIMIT 1", (torneo["torneo_id"], lunes.year, FUENTE)).fetchone()
    if previa and abs((previa[1] - lunes).days) <= 7:      # torneo de dos semanas: la misma edición
        return previa[0]
    return db.execute(
        "INSERT INTO edicion (torneo_id, temporada, lunes_semana, fecha_fin, superficie, indoor, por_equipos, fuente, "
        "recibo_id, recibido_en) VALUES (%s, %s, %s, NULL, %s, %s, false, %s, %s, %s) RETURNING edicion_id",
        (torneo["torneo_id"], lunes.year, lunes, torneo["superficie"], torneo["indoor"], FUENTE, rid, recibido)).fetchone()[0]


def _partido(db, edicion_id: int, j1: int, j2: int, rid: int, recibido: datetime) -> tuple[int, bool]:
    fila = db.execute(
        "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en) "
        "VALUES (%s, %s, %s, %s, 3, %s, %s, %s) ON CONFLICT (edicion_id, ronda, jugador_1, jugador_2) DO NOTHING "
        "RETURNING partido_id", (edicion_id, RONDA, j1, j2, FUENTE, rid, recibido)).fetchone()
    if fila:
        return fila[0], True
    return db.execute("SELECT partido_id FROM partido WHERE edicion_id = %s AND ronda = %s AND jugador_1 = %s AND jugador_2 = %s",
                      (edicion_id, RONDA, j1, j2)).fetchone()[0], False


def _programa(db, partido_id: int, inicio: datetime, rid: int, recibido: datetime) -> bool:
    ultimo = db.execute("SELECT inicio_programado_utc FROM programa WHERE partido_id = %s AND fuente = %s "
                        "ORDER BY recibido_en DESC, programa_id DESC LIMIT 1", (partido_id, FUENTE)).fetchone()
    if ultimo and ultimo[0] == inicio:
        return False
    db.execute("INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, pista, estado, fuente, recibo_id, "
               "recibido_en) VALUES (%s, %s, 'fija', NULL, 'programado', %s, %s, %s) ON CONFLICT DO NOTHING",
               (partido_id, inicio, FUENTE, rid, recibido))
    return True


def _enlace(db, evento_id: str, partido_id: int, rid: int, recibido: datetime) -> None:
    if not db.execute("SELECT 1 FROM enlace_evento WHERE fuente = %s AND evento_fuente = %s AND partido_id = %s",
                      (FUENTE, evento_id, partido_id)).fetchone():
        db.execute("INSERT INTO enlace_evento (fuente, evento_fuente, partido_id, metodo, recibo_id, recibido_en) "
                   "VALUES (%s, %s, %s, 'nombre_fecha', %s, %s)", (FUENTE, evento_id, partido_id, rid, recibido))


def capturar(db, doc: dict, raiz, resolutor, ahora: datetime | None = None) -> Resultado:
    """Procesa un documento del archivo: {'recibido_en': iso, 'sha256': hex, 'eventos': [...]}.

    `resolutor` tiene `buscar_exacto(circuito, nombre) -> set[int]` (ResolutorMultifuente). Todo en una transacción."""
    recibido = parse_instante(doc.get("recibido_en"))
    sha = doc.get("sha256")
    if recibido is None or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("documento del archivo sin recibido_en o sha256 válidos")
    ahora = ahora or datetime.now(timezone.utc)
    if leer_cursor(db, FUENTE, CURSOR) == sha:
        return Resultado("sin_cambios")
    candidatos, descartes = analizar(doc.get("eventos", []), ahora)
    res = Resultado("vacio" if not candidatos else "escrito", descartes=dict(descartes))
    cuerpo = json.dumps({"archivo": {"recibido_en": recibido.isoformat(), "sha256": sha},
                         "eventos": [{"id": c.evento_id, "commence_time": c.inicio.isoformat(), "home_team": c.local,
                                      "away_team": c.visitante, "tournament": c.torneo, "circuito": c.circuito,
                                      "challenger": c.challenger} for c in candidatos]},
                        sort_keys=True, ensure_ascii=False).encode("utf-8")
    lote = f"calendario_propline_{recibido.strftime('%Y%m%dT%H%M%SZ')}"

    def lote_fn(conn, _previo):
        objeto = nuevo_recibo(raiz, fuente=FUENTE, recurso=RECURSO, retro=False, recibido_en=recibido, cuerpo=cuerpo,
                              parametros={"deporte": "tennis", "archivo_sha256": sha,
                                          "archivo_recibido_en": recibido.isoformat()})
        rid = _insertar_recibo(conn, objeto, lote)
        res.recibo_id = rid
        indice = indice_torneos(conn, recibido.date())
        for c in candidatos:
            torneo, motivo = resolver_torneo(indice, c)
            if torneo is None:
                res.sin_resolver += _a_sin_resolver(conn, c, motivo, rid, recibido)
                continue
            ids = []
            for nombre in (c.local, c.visitante):
                encontrados = resolutor.buscar_exacto(c.circuito, nombre)
                ids.append(next(iter(encontrados)) if len(encontrados) == 1 else None)
                if len(encontrados) != 1:
                    res.sin_resolver += _a_sin_resolver(
                        conn, c, "jugador_ambiguo" if encontrados else "jugador_sin_resolver", rid, recibido)
                    break
            if len(ids) != 2 or None in ids or ids[0] == ids[1]:
                continue
            j1, j2 = sorted(ids)
            partido_id, nuevo = _partido(conn, _edicion(conn, torneo, c, rid, recibido), j1, j2, rid, recibido)
            res.partidos_nuevos += nuevo
            res.programas_nuevos += _programa(conn, partido_id, c.inicio, rid, recibido)
            _enlace(conn, c.evento_id, partido_id, rid, recibido)
        return sha

    ejecutar_lote(db, FUENTE, CURSOR, lote_fn)
    return res


# -------------------------------------------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    import psycopg
    from ..identidad.resolver import ResolutorMultifuente
    ap = argparse.ArgumentParser(description="Calendario de tenis desde el archivo de PropLine (documento JSON por stdin)")
    ap.add_argument("--stdin", action="store_true", required=True)
    ap.add_argument("--almacen", type=Path, required=True)
    ap.add_argument("--dsn", default=os.environ.get("PG_DSN"))
    ap.add_argument("--esquema", default="tenis")
    a = ap.parse_args(argv)
    if not a.dsn or not re.fullmatch(r"[a-z_][a-z0-9_]*", a.esquema):
        print("falta --dsn o PG_DSN, o esquema no válido", file=sys.stderr)
        return 1
    try:
        doc = json.loads(sys.stdin.read())
        with psycopg.connect(a.dsn, autocommit=True) as db:
            db.execute(f"SET search_path TO {a.esquema}, {a.esquema}_op, public")      # el cursor vive en tenis_op
            res = capturar(db, doc, a.almacen, ResolutorMultifuente(db))
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 1
    print(json.dumps({"estado": res.estado, "partidos_nuevos": res.partidos_nuevos, "programas_nuevos": res.programas_nuevos,
                      "sin_resolver": res.sin_resolver, "descartes": res.descartes}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
