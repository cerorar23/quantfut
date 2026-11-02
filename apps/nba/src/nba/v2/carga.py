"""Núcleo de carga a `nba.*`: idempotente, con conflicto marcado y originales con hash."""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
from pathlib import Path

# Diferencia máxima entre fuentes antes de marcar `conflicto` (0 por omisión).
TOLERANCIA = {"minutos": 0.5}


@dataclass(frozen=True)
class DatoNuevo:
    partido_id: int
    entidad_id: int
    metrica: str
    fase: str
    fuente: str
    recibido_en: datetime
    periodo: int = 0
    valor: float | None = None
    etiqueta: str | None = None
    captura_id: int | None = None
    pit: str = "posterior"


@dataclass(frozen=True)
class CuotaNueva:
    partido_id: int
    fuente: str
    casa: str
    mercado: str
    lado: str
    cuota: Decimal
    contrato_id: str
    fase: str
    recibido_en: datetime
    periodo: int = 0
    entidad_id: int | None = None
    linea: Decimal | None = None
    captura_id: int | None = None


def guardar_datos(db, filas: Iterable[DatoNuevo], solo_cambios: bool = False) -> int:
    """Con `solo_cambios`, omite la fila si el último valor visible de la misma fuente y clave es idéntico:
    `nba.dato_a_las` ya devuelve ese valor mientras no cambie, así que repetirlo solo ocuparía espacio."""
    filas = list(filas)
    metricas = {nombre: (mid, res) for mid, nombre, res in db.execute(
        "SELECT metrica_id, nombre, resolucion FROM nba.metrica")}
    for f in filas:
        if f.metrica not in metricas:
            raise KeyError(f.metrica)
    insertadas = 0
    for f in filas:
        metrica_id, resolucion = metricas[f.metrica]
        if solo_cambios and db.execute(
                "SELECT (valor IS NOT DISTINCT FROM %s AND etiqueta IS NOT DISTINCT FROM %s) FROM nba.dato "
                "WHERE partido_id = %s AND entidad_id = %s AND periodo = %s AND metrica_id = %s AND fase = %s "
                "AND fuente = %s AND recibido_en <= %s ORDER BY recibido_en DESC, dato_id DESC LIMIT 1",
                (f.valor, f.etiqueta, f.partido_id, f.entidad_id, f.periodo, metrica_id, f.fase, f.fuente,
                 f.recibido_en)).fetchone() in [(True,)]:
            continue
        conflicto = False
        if resolucion == "prioridad" and f.valor is not None:
            conflicto = db.execute(
                "SELECT EXISTS (SELECT 1 FROM nba.dato WHERE partido_id = %s AND entidad_id = %s AND periodo = %s "
                "AND metrica_id = %s AND fase = %s AND fuente <> %s AND valor IS NOT NULL "
                "AND abs(valor - %s) > %s)",
                (f.partido_id, f.entidad_id, f.periodo, metrica_id, f.fase, f.fuente, f.valor,
                 TOLERANCIA.get(f.metrica, 0))).fetchone()[0]
        cursor = db.execute(
            "INSERT INTO nba.dato (partido_id, entidad_id, periodo, metrica_id, valor, etiqueta, fase, fuente, "
            "captura_id, recibido_en, pit, conflicto) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING",
            (f.partido_id, f.entidad_id, f.periodo, metrica_id, f.valor, f.etiqueta, f.fase, f.fuente,
             f.captura_id, f.recibido_en, f.pit, conflicto))
        insertadas += cursor.rowcount
    return insertadas


def guardar_cuotas(db, filas: Iterable[CuotaNueva]) -> int:
    insertadas = 0
    for c in filas:
        cursor = db.execute(
            "INSERT INTO nba.cuota (partido_id, fuente, casa, mercado, periodo, entidad_id, linea, lado, cuota, "
            "contrato_id, fase, captura_id, recibido_en) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT DO NOTHING",
            (c.partido_id, c.fuente, c.casa, c.mercado, c.periodo, c.entidad_id, c.linea, c.lado, c.cuota,
             c.contrato_id, c.fase, c.captura_id, c.recibido_en))
        insertadas += cursor.rowcount
    return insertadas


def guardar_original(raiz: Path, fuente: str, cuerpo: bytes, recibido_en: datetime) -> tuple[str, str]:
    huella = hashlib.sha256(cuerpo).hexdigest()
    relativa = f"{fuente}/{recibido_en.date().isoformat()}/{huella}"
    destino = raiz / relativa
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = destino.with_name(destino.name + ".tmp")
        temporal.write_bytes(cuerpo)
        temporal.replace(destino)
    return relativa, huella


def registrar_captura(db, *, fuente: str, objetivo: str, fase: str, solicitado_en: datetime, ok: bool,
                      recibido_en: datetime | None = None, http_status: int | None = None,
                      sha256: str | None = None, bytes_: int | None = None, ruta: str | None = None,
                      error: str | None = None, creditos: float = 0, partido_id: int | None = None) -> int:
    return db.execute(
        "INSERT INTO nba.captura (fuente, objetivo, fase, partido_id, solicitado_en, recibido_en, http_status, ok, "
        "sha256, bytes, ruta, error, creditos) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING captura_id",
        (fuente, objetivo, fase, partido_id, solicitado_en, recibido_en, http_status, ok, sha256, bytes_, ruta,
         error, creditos)).fetchone()[0]
