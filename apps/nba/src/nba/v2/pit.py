"""Acceso punto en el tiempo del motor (ficha 64): lo que se sabía de un partido en un instante, con la huella de esos datos.

Una `Instantanea` contiene (1) la historia de resultados finales de partidos ANTERIORES (por fecha) y (2) las filas propias del
partido visibles en `corte` (`recibido_en <= corte`, nunca las de fase `final`). `version_datos` es el sha256 de ambas: si dos
instantáneas tienen la misma huella, el motor ve exactamente lo mismo.

También los archivos reconstruidos exigen recepción acreditada anterior al corte; la fecha del evento no acredita recepción.
"""
from dataclasses import dataclass
from datetime import date, datetime, UTC
import hashlib
import json

HISTORIA = """
WITH vis AS (
    SELECT DISTINCT ON (d.partido_id, d.entidad_id) d.partido_id, d.entidad_id, d.valor
    FROM nba.dato d
    JOIN nba.entidad equipo ON equipo.entidad_id = d.entidad_id AND equipo.tipo = 'equipo'
    JOIN nba.entidad juego ON juego.entidad_id = d.partido_id AND juego.tipo = 'partido'
         AND juego.canonica_id = juego.entidad_id AND juego.fecha_juego_et < %(fecha)s
    JOIN nba.fuente f ON f.fuente = d.fuente
    JOIN nba.metrica m ON m.metrica_id = d.metrica_id AND m.nombre = 'puntos'
    WHERE d.periodo = 0 AND d.fase = 'final' AND d.recibido_en <= %(corte)s
      AND NOT EXISTS (SELECT 1 FROM nba.captura c WHERE c.captura_id = d.captura_id AND (c.recibido_en IS NULL OR c.recibido_en > %(corte)s))
    ORDER BY d.partido_id, d.entidad_id, f.prioridad, d.recibido_en DESC, d.dato_id DESC
)
SELECT e.fecha_juego_et, e.entidad_id, tl.id_en_fuente, tv.id_en_fuente, pl.valor, pv.valor
FROM nba.entidad e
JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint
JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint
JOIN vis pl ON pl.partido_id = e.entidad_id AND pl.entidad_id = tl.entidad_id
JOIN vis pv ON pv.partido_id = e.entidad_id AND pv.entidad_id = tv.entidad_id
WHERE e.tipo = 'partido' AND e.canonica_id = e.entidad_id AND e.fecha_juego_et < %(fecha)s
ORDER BY e.fecha_juego_et, e.entidad_id
"""

PROPIAS = """
SELECT d.metrica_id, d.entidad_id, d.periodo, d.fase, d.fuente, d.valor, d.etiqueta, d.recibido_en
FROM nba.dato_a_las(%(corte)s) d
WHERE d.partido_id = %(partido)s AND d.fase <> 'final'
ORDER BY d.metrica_id, d.entidad_id, d.periodo, d.fase, d.fuente, d.recibido_en
"""


@dataclass(frozen=True)
class Instantanea:
    partido_id: int
    corte: datetime
    fecha: date
    local: str
    visitante: str
    historia: tuple          # (fecha, partido_id, local, visitante, pts_local, pts_visitante)
    propias: tuple
    version_datos: str


def _huella(historia, propias) -> str:
    h = hashlib.sha256()
    for fila in historia:
        h.update(json.dumps([fila[0].isoformat(), *fila[1:]], separators=(",", ":")).encode())
    h.update(b"|")
    for fila in propias:
        h.update(json.dumps([*fila[:7], fila[7].astimezone(UTC).isoformat(timespec="microseconds")], separators=(",", ":")).encode())
    return h.hexdigest()


def combinar_huellas(*huellas: str) -> str:
    """Composición con dominio y orden: ninguna entrada se descarta por concatenación/truncamiento."""
    if not huellas or any(len(h) != 64 or any(c not in '0123456789abcdef' for c in h) for h in huellas):
        raise ValueError("se requieren huellas sha256 completas")
    return hashlib.sha256(json.dumps(['nba-inputs-v1', *huellas], separators=(',', ':')).encode()).hexdigest()


def instantanea(db, partido_id: int, corte: datetime) -> Instantanea:
    """Solo lectura: la vista del motor sobre `partido_id` en `corte` (con zona horaria)."""
    if corte.tzinfo is None:
        raise ValueError("el corte necesita zona horaria")
    e = db.execute("SELECT e.fecha_juego_et, tl.id_en_fuente, tv.id_en_fuente FROM nba.entidad e "
                   "JOIN nba.entidad tl ON tl.entidad_id = (e.atributos->>'local')::bigint "
                   "JOIN nba.entidad tv ON tv.entidad_id = (e.atributos->>'visitante')::bigint "
                   "WHERE e.entidad_id = %s AND e.tipo = 'partido' AND e.canonica_id = e.entidad_id", (partido_id,)).fetchone()
    if e is None:
        raise ValueError(f"partido canónico inexistente: {partido_id}")
    historia = tuple((f, int(p), lo, vi, float(a), float(b)) for f, p, lo, vi, a, b in
                     db.execute(HISTORIA, {"corte": corte, "fecha": e[0]}).fetchall())
    propias = tuple(db.execute(PROPIAS, {"corte": corte, "partido": partido_id}).fetchall())
    return Instantanea(partido_id, corte, e[0], e[1], e[2], historia, propias, _huella(historia, propias))
