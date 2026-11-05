"""Resultados y partes de lesiones históricos que ya existían en archivos (2021-22 a 2025-26), sin créditos nuevos:

* Cajas por jugador y por equipo (`players.jsonl.gz` y `games.json` de nba_extended_box): estadísticas finales.
* Partes oficiales de lesiones ya extraídos de los PDF (`reports.jsonl.gz`): estado y motivo por jugador y partido.

La caja final no tiene recepción acreditada: `recibido_en` es la fecha de adquisición del archivo y `pit = 'reconstruido'`
La hora publicada del parte permanece en el original; no sustituye la recepción del archivo.
"""
from collections.abc import Iterator
from datetime import UTC, date, datetime
import gzip
import json
from pathlib import Path

from .. import carga, equipos, identidad
from ..carga import DatoNuevo
from ..duracion import prorrogas
from .historico_cuotas import _abrir, _huella
from .parte_oficial import nombre_directo

FUENTE = "nba_oficial"
# métrica canónica → clave de la caja histórica
JUGADOR = {"puntos": "points", "minutos": "minutes", "tiros_campo_anotados": "fgm", "tiros_campo_intentados": "fga",
           "triples_anotados": "threes", "triples_intentados": "fg3a", "tiros_libres_anotados": "ftm",
           "tiros_libres_intentados": "fta", "rebotes_ofensivos": "oreb", "rebotes_defensivos": "dreb",
           "rebotes": "rebounds", "asistencias": "assists", "robos": "steals", "tapones": "blocks", "perdidas": "tov",
           "faltas": "pf", "mas_menos": "plus_minus"}
EQUIPO = {"puntos": "points", "minutos": "minutes", "tiros_campo_anotados": "fgm", "tiros_campo_intentados": "fga",
          "triples_anotados": "threes", "triples_intentados": "fg3a", "tiros_libres_anotados": "ftm",
          "tiros_libres_intentados": "fta", "rebotes_ofensivos": "oreb", "rebotes_defensivos": "dreb", "robos": "steals",
          "tapones": "blocks", "perdidas": "tov", "faltas": "pf", "posesiones": "possessions"}


def _captura(db, ruta: Path, nombre: str, sha256: str | None = None) -> int:
    existente = db.execute("SELECT captura_id FROM nba.captura WHERE fuente = %s AND objetivo = %s AND ok",
                           (FUENTE, nombre)).fetchone()
    if existente:
        return existente[0]
    adquirido = datetime.fromtimestamp(ruta.stat().st_mtime, UTC)
    return carga.registrar_captura(db, fuente=FUENTE, objetivo=nombre, fase="historico", solicitado_en=adquirido, ok=True,
                                   recibido_en=adquirido, sha256=sha256 or _huella(ruta), bytes_=ruta.stat().st_size,
                                   ruta=ruta.name)


def _partido(db, cache: dict, game_id: str, fecha: date, local: str, visitante: str) -> int:
    if game_id not in cache:
        cache[game_id] = identidad.partido(db, FUENTE, game_id, fecha, identidad.equipo(db, local),
                                           identidad.equipo(db, visitante), identidad.temporada(fecha))
    return cache[game_id]


def _guardar(db, filas, solo_cambios: bool, masivo: bool) -> int:
    return carga.guardar_datos_lote(db, filas) if masivo else carga.guardar_datos(db, filas, solo_cambios=solo_cambios)


def _volcar(db, filas: Iterator[DatoNuevo], solo_cambios: bool = False, masivo: bool = False,
            lote: int = 20000) -> dict:
    leidas = nuevas = 0
    buffer: list[DatoNuevo] = []
    for f in filas:
        buffer.append(f)
        if len(buffer) >= lote:
            leidas += len(buffer)
            nuevas += _guardar(db, buffer, solo_cambios, masivo)
            db.commit()
            buffer = []
    if buffer:
        leidas += len(buffer)
        nuevas += _guardar(db, buffer, solo_cambios, masivo)
        db.commit()
    return {"ok": True, "leidas": leidas, "nuevas": nuevas}


def cargar_cajas(db, carpeta: Path) -> dict:
    """`games.json` (equipos) + `players.jsonl.gz` (jugadores) de la caja extendida."""
    ruta_juegos, ruta_jugadores = carpeta / "games.json", carpeta / "players.jsonl.gz"
    if not ruta_jugadores.exists():
        ruta_jugadores = carpeta / "players.jsonl"
    captura_j = _captura(db, ruta_jugadores, f"cajas_jugadores:{ruta_jugadores.name}")
    captura_e = _captura(db, ruta_juegos, f"cajas_equipos:{ruta_juegos.name}")
    recibido = datetime.fromtimestamp(ruta_jugadores.stat().st_mtime, UTC)
    juegos = json.loads(ruta_juegos.read_text(encoding="utf8"))
    juegos = list(juegos.values()) if isinstance(juegos, dict) else juegos
    cache: dict = {}
    jugadores: dict = {}
    equipos_ids: dict = {}

    def generar():
        for g in juegos:
            fecha = date.fromisoformat(g["date"])
            local, visitante = equipos.NBA_IDS[g["home"]["team_id"]], equipos.NBA_IDS[g["away"]["team_id"]]
            partido = _partido(db, cache, g["game_id"], fecha, local, visitante)
            base = dict(partido_id=partido, fase="final", fuente=FUENTE, recibido_en=recibido, captura_id=captura_e,
                        pit="reconstruido")
            yield DatoNuevo(entidad_id=partido, metrica="estado_partido", etiqueta="final", **base)
            ot_l, ot_v = prorrogas(g['home'].get('minutes')), prorrogas(g['away'].get('minutes'))
            if ot_l is not None and ot_v is not None and ot_l == ot_v:
                yield DatoNuevo(entidad_id=partido, metrica='prorrogas', valor=float(ot_l), **base)
            for lado in ("home", "away"):
                e = g[lado]
                equipo = identidad.equipo(db, equipos.NBA_IDS[e["team_id"]])
                for metrica, clave in EQUIPO.items():
                    if e.get(clave) is not None:
                        yield DatoNuevo(entidad_id=equipo, metrica=metrica, valor=float(e[clave]), **base)
        with _abrir(ruta_jugadores) as f:
            for linea in f:
                r = json.loads(linea)
                partido = cache.get(r["game_id"])
                if partido is None:
                    continue  # juego que no está en el catálogo de equipos: no se inventa
                if r["player_id"] not in jugadores:
                    jugadores[r["player_id"]] = identidad.jugador(db, FUENTE, str(r["player_id"]), r["name"])
                base = dict(partido_id=partido, fase="final", fuente=FUENTE, recibido_en=recibido, captura_id=captura_j,
                            pit="reconstruido", entidad_id=jugadores[r["player_id"]])
                if r.get("team_id") in equipos.NBA_IDS:
                    if r["team_id"] not in equipos_ids:
                        equipos_ids[r["team_id"]] = identidad.equipo(db, equipos.NBA_IDS[r["team_id"]])
                    yield DatoNuevo(metrica="equipo_del_jugador", valor=float(equipos_ids[r["team_id"]]), **base)
                yield DatoNuevo(metrica="jugo", valor=1.0 if r["participated"] else 0.0, **base)
                if not r["participated"]:
                    continue  # sin minutos no se imputan estadísticas en cero
                for metrica, clave in JUGADOR.items():
                    if r.get(clave) is not None:
                        yield DatoNuevo(metrica=metrica, valor=float(r[clave]), **base)

    return _volcar(db, generar(), masivo=True)


def cargar_partes(db, rutas: list[Path]) -> dict:
    """Partes oficiales ya extraídos: dedupe por URL, orden cronológico y solo cambios por jugador."""
    informes: dict[str, tuple[dict, Path]] = {}
    for ruta in rutas:
        with _abrir(ruta) as f:
            for linea in f:
                r = json.loads(linea)
                informes.setdefault(r["source_url"], (r, ruta))
    orden = sorted(informes.values(), key=lambda x: x[0]["report_timestamp_utc"])
    cache: dict = {}
    jugadores: dict = {}

    def generar():
        for r, ruta in orden:
            captura = _captura(db, ruta, r["source_url"], sha256=r.get("pdf_sha256"))
            recibido = datetime.fromtimestamp(ruta.stat().st_mtime, UTC)
            for x in r["rows"]:
                visitante, local = (equipos.canonico(FUENTE, c) for c in x["matchup"].split("@"))
                fecha = datetime.strptime(x["game_date"], "%m/%d/%Y").date()
                partido = _partido(db, cache, x["nba_game_id"] or f"{fecha.isoformat()}:{x['matchup']}", fecha, local, visitante)
                base = dict(partido_id=partido, fase="pre", fuente=FUENTE, recibido_en=recibido, captura_id=captura,
                            pit="reconstruido")
                if not x["report_submitted"]:
                    equipo = equipos.NBA_IDS.get(x.get("nba_team_id"))
                    if equipo:
                        yield DatoNuevo(entidad_id=identidad.equipo(db, equipo), metrica="reporte_no_enviado", valor=1.0, **base)
                    continue
                nombre = nombre_directo(x["player_name_raw"])
                clave = x.get("nba_player_id") or ("nombre:" + identidad.normalizar_nombre(nombre))
                if clave not in jugadores:
                    jugadores[clave] = identidad.jugador(db, FUENTE, str(clave), nombre)
                yield DatoNuevo(entidad_id=jugadores[clave], metrica="estado_disponibilidad", etiqueta=x["status_raw"], **base)
                yield DatoNuevo(entidad_id=jugadores[clave], metrica="motivo_disponibilidad", etiqueta=x["reason_raw"][:300], **base)

    resultado = _volcar(db, generar(), solo_cambios=True)
    resultado["partes"] = len(orden)
    return resultado
