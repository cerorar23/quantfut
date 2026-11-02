"""Resolución de identidades en `nba.entidad`: alias de fuente → fila canónica, sin falsas fusiones."""
from datetime import date
import json
import re
import unicodedata

from .equipos import TRICODES

_SUFIJOS = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalizar_nombre(nombre: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    palabras = re.sub(r"[^a-z0-9 ]", "", sin_acentos.casefold().replace("-", " ")).split()
    while len(palabras) > 1 and palabras[-1] in _SUFIJOS:
        palabras.pop()
    return " ".join(palabras)


def _existente(db, tipo: str, fuente: str, id_en_fuente: str) -> int | None:
    fila = db.execute("SELECT canonica_id FROM nba.entidad WHERE tipo = %s AND fuente = %s AND id_en_fuente = %s",
                      (tipo, fuente, id_en_fuente)).fetchone()
    return fila[0] if fila else None


def _insertar(db, tipo, fuente, id_en_fuente, nombre, canonica_id=None, atributos=None, fecha_et=None,
              temporada=None) -> int:
    db.execute(
        "INSERT INTO nba.entidad (tipo, canonica_id, fuente, id_en_fuente, nombre, fecha_juego_et, temporada, atributos) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (fuente, id_en_fuente, tipo) DO NOTHING",
        (tipo, canonica_id, fuente, id_en_fuente, nombre, fecha_et, temporada, json.dumps(atributos or {})))
    return _existente(db, tipo, fuente, id_en_fuente)


def equipo(db, tricode: str) -> int:
    nombre = TRICODES[tricode]
    return _existente(db, "equipo", "nba_oficial", tricode) or _insertar(db, "equipo", "nba_oficial", tricode, nombre)


def _persona(db, tipo: str, fuente: str, id_en_fuente: str, nombre: str) -> int:
    previa = _existente(db, tipo, fuente, id_en_fuente)
    if previa:
        return previa
    norma = normalizar_nombre(nombre)
    # Candidatas: canónicas con el mismo nombre normalizado que aún no tienen fila de esta fuente.
    candidatas = [r[0] for r in db.execute(
        "SELECT c.entidad_id FROM nba.entidad c WHERE c.tipo = %s AND c.canonica_id = c.entidad_id "
        "AND c.atributos->>'nombre_norm' = %s "
        "AND NOT EXISTS (SELECT 1 FROM nba.entidad a WHERE a.canonica_id = c.entidad_id AND a.fuente = %s)",
        (tipo, norma, fuente))]
    colision = bool(candidatas) or db.execute(
        "SELECT EXISTS (SELECT 1 FROM nba.entidad WHERE tipo = %s AND atributos->>'nombre_norm' = %s)",
        (tipo, norma)).fetchone()[0]
    if len(candidatas) == 1:
        return _insertar(db, tipo, fuente, id_en_fuente, nombre, canonica_id=candidatas[0],
                         atributos={"nombre_norm": norma})
    atributos = {"nombre_norm": norma}
    if colision:
        atributos["ambiguo"] = True
    return _insertar(db, tipo, fuente, id_en_fuente, nombre, atributos=atributos)


def jugador(db, fuente: str, id_en_fuente: str, nombre: str) -> int:
    return _persona(db, "jugador", fuente, id_en_fuente, nombre)


def arbitro(db, fuente: str, id_en_fuente: str, nombre: str) -> int:
    return _persona(db, "arbitro", fuente, id_en_fuente, nombre)


def partido(db, fuente: str, id_en_fuente: str, fecha_et: date, local: int, visitante: int, temporada: str) -> int:
    previa = _existente(db, "partido", fuente, id_en_fuente)
    if previa:
        return previa
    atributos = {"local": local, "visitante": visitante}
    fila = db.execute(
        "SELECT c.entidad_id FROM nba.entidad c WHERE c.tipo = 'partido' AND c.canonica_id = c.entidad_id "
        "AND c.fecha_juego_et = %s AND (c.atributos->>'local')::bigint = %s AND (c.atributos->>'visitante')::bigint = %s "
        "AND NOT EXISTS (SELECT 1 FROM nba.entidad a WHERE a.canonica_id = c.entidad_id AND a.fuente = %s)",
        (fecha_et, local, visitante, fuente)).fetchone()
    nombre = f"{fecha_et.isoformat()} #{visitante}@{local}"
    return _insertar(db, "partido", fuente, id_en_fuente, nombre, canonica_id=fila[0] if fila else None,
                     atributos=atributos, fecha_et=fecha_et, temporada=temporada)
