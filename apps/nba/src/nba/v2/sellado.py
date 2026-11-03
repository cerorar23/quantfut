"""Sellado en cadena de pronósticos (predecir → sellar → publicar): cada fila encadena el hash de la anterior.

* El sellado exige `objetivo_en <= ahora` (la hora de corte de los datos ya pasó) y fija `sellado_en` con el reloj de la base.
* La cadena se serializa con un candado de aviso de Postgres; `nba.pronostico` rechaza UPDATE/DELETE/TRUNCATE por disparador.
* `verificar_cadena` recalcula todos los hashes y los enlaces; lanza `ValueError` ante la primera ruptura.
"""
from dataclasses import dataclass
from datetime import datetime, UTC
import hashlib
import json

GENESIS = "0" * 64
CANDADO = "nba.pronostico"


@dataclass(frozen=True)
class PronosticoNuevo:
    partido_id: int
    mercado: str
    version_modelo: str
    version_datos: str
    objetivo_en: datetime
    escenarios: dict
    distribucion: dict
    periodo: int = 0
    entidad_id: int | None = None


def _canonico(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def calcular_hash(partido_id, mercado, periodo, entidad_id, version_modelo, version_datos, objetivo_en: datetime,
                  sellado_en: datetime, escenarios: dict, distribucion: dict, hash_previo: str) -> str:
    cuerpo = _canonico([partido_id, mercado, periodo, entidad_id, version_modelo, version_datos,
                        objetivo_en.astimezone(UTC).isoformat(timespec="microseconds"),
                        sellado_en.astimezone(UTC).isoformat(timespec="microseconds"), escenarios, distribucion, hash_previo])
    return hashlib.sha256(cuerpo.encode()).hexdigest()


def sellar(db, p: PronosticoNuevo) -> str:
    """Inserta el pronóstico encadenado y devuelve su hash; si ya estaba sellado (misma clave única) devuelve el hash existente."""
    if p.objetivo_en.tzinfo is None:
        raise ValueError("objetivo_en necesita zona horaria")
    with db.transaction():
        db.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (CANDADO,))
        ahora = db.execute("SELECT clock_timestamp()").fetchone()[0]
        if p.objetivo_en > ahora:
            raise ValueError("objetivo_en es posterior al sellado: no se sella un pronóstico con datos del futuro")
        existente = db.execute("SELECT hash FROM nba.pronostico WHERE partido_id = %s AND mercado = %s AND periodo = %s "
                               "AND entidad_id IS NOT DISTINCT FROM %s AND version_modelo = %s AND objetivo_en = %s",
                               (p.partido_id, p.mercado, p.periodo, p.entidad_id, p.version_modelo, p.objetivo_en)).fetchone()
        if existente:
            return existente[0]
        previo = db.execute("SELECT hash FROM nba.pronostico ORDER BY pronostico_id DESC LIMIT 1").fetchone()
        hash_previo = previo[0] if previo else GENESIS
        h = calcular_hash(p.partido_id, p.mercado, p.periodo, p.entidad_id, p.version_modelo, p.version_datos, p.objetivo_en,
                          ahora, p.escenarios, p.distribucion, hash_previo)
        db.execute("INSERT INTO nba.pronostico (partido_id, mercado, periodo, entidad_id, version_modelo, version_datos, objetivo_en, "
                   "sellado_en, escenarios, distribucion, hash_previo, hash) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)",
                   (p.partido_id, p.mercado, p.periodo, p.entidad_id, p.version_modelo, p.version_datos, p.objetivo_en, ahora,
                    _canonico(p.escenarios), _canonico(p.distribucion), hash_previo, h))
        return h


def verificar_cadena(db) -> int:
    """Recalcula la cadena completa; devuelve el número de filas verificadas o lanza ValueError con la primera ruptura."""
    previo, n = GENESIS, 0
    for fila in db.execute("SELECT pronostico_id, partido_id, mercado, periodo, entidad_id, version_modelo, version_datos, objetivo_en, "
                           "sellado_en, escenarios, distribucion, hash_previo, hash FROM nba.pronostico ORDER BY pronostico_id").fetchall():
        (pid, partido, mercado, periodo, entidad, vm, vd, objetivo, sellado, esc, dist, hp, h) = fila
        if hp != previo:
            raise ValueError(f"cadena rota en el pronóstico {pid}: hash_previo no coincide con la fila anterior")
        if calcular_hash(partido, mercado, periodo, entidad, vm, vd, objetivo, sellado, esc, dist, hp) != h:
            raise ValueError(f"pronóstico {pid} alterado: su hash no coincide con su contenido")
        if objetivo > sellado:
            raise ValueError(f"pronóstico {pid} sellado antes de su hora de corte")
        previo, n = h, n + 1
    return n
