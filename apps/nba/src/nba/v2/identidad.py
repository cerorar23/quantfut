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


def alias_jugador(db, fuente: str, id_en_fuente: str, nombre: str, canonica_id: int) -> int:
    """Alias de una fuente apuntando a un canónico YA decidido por otra vía (p. ej. la huella de la caja del mismo partido en otra fuente)."""
    previa = _existente(db, "jugador", fuente, id_en_fuente)
    if previa:
        return previa
    return _insertar(db, "jugador", fuente, id_en_fuente, nombre, canonica_id=canonica_id,
                     atributos={"nombre_norm": normalizar_nombre(nombre), "alias_por_huella": True})


def jugador(db, fuente: str, id_en_fuente: str, nombre: str) -> int:
    return _persona(db, "jugador", fuente, id_en_fuente, nombre)


def arbitro(db, fuente: str, id_en_fuente: str, nombre: str) -> int:
    return _persona(db, "arbitro", fuente, id_en_fuente, nombre)


def _juego_canonico(db, fecha_et: date, local: int, visitante: int) -> int | None:
    """El partido canónico más antiguo de ese día y esos equipos (en la NBA no hay dobles jornadas)."""
    return db.execute(
        "SELECT min(entidad_id) FROM nba.entidad WHERE tipo = 'partido' AND canonica_id = entidad_id "
        "AND fecha_juego_et = %s AND (atributos->>'local')::bigint = %s AND (atributos->>'visitante')::bigint = %s",
        (fecha_et, local, visitante)).fetchone()[0]


def partido(db, fuente: str, id_en_fuente: str, fecha_et: date, local: int, visitante: int, temporada: str) -> int:
    """Un juego es único por (fecha ET, local, visitante): todas las fuentes y todos sus ids caen en el mismo canónico,
    aunque una misma fuente use ids distintos (p. ej. el id sintético del PDF y el id real de cdn.nba.com)."""
    canonico = _juego_canonico(db, fecha_et, local, visitante)
    previa = _existente(db, "partido", fuente, id_en_fuente)
    if canonico is None:
        return previa or _insertar(db, "partido", fuente, id_en_fuente, f"{fecha_et.isoformat()} #{visitante}@{local}",
                                   atributos={"local": local, "visitante": visitante}, fecha_et=fecha_et,
                                   temporada=temporada)
    if previa is None:
        _insertar(db, "partido", fuente, id_en_fuente, f"{fecha_et.isoformat()} #{visitante}@{local}",
                  canonica_id=canonico, atributos={"local": local, "visitante": visitante}, fecha_et=fecha_et,
                  temporada=temporada)
    return canonico


def temporada(fecha_et: date) -> str:
    """Temporada NBA de una fecha ET: de septiembre en adelante empieza la del año en curso."""
    inicio = fecha_et.year if fecha_et.month >= 9 else fecha_et.year - 1
    return f"{inicio}-{(inicio + 1) % 100:02d}"
