"""Control de gasto de peticiones sobre `tenis_op.presupuesto` (fuente, dia, tope, usadas).

Reglas:
- `tope` NULL o fila inexistente = sin tope conocido: la reserva se RECHAZA (no es 0 ni infinito).
- `usadas` cuenta lo reservado, incluido lo que está en vuelo (conservador).
- `confirmar` deja constancia de que la respuesta llegó y no cambia `usadas` (ya se contó al reservar).
- `devolver` resta solo cuando la respuesta no consumió cuota (p. ej. HTTP distinto de 200 o cuerpo vacío).
- Además del tope diario, `TOPE_SEMANAL` limita las peticiones de la semana ISO (lunes a domingo, UTC).
  Para SportsAPIPro el tope propio de este uso es 2 por semana; el cupo diario compartido de 100 se gestiona aparte.

Concurrencia: cada reserva y devolución toma un candado de transacción por fuente (`pg_advisory_xact_lock`),
así dos reservas simultáneas no pasan del tope.
"""
from datetime import datetime, timedelta, timezone

# Tope semanal propio de cada fuente (además del diario de la tabla). Fuente sin entrada: no hay tope semanal.
TOPE_SEMANAL = {"sportsapipro": 2}


class PresupuestoError(Exception):
    """Base de los rechazos de presupuesto. Nunca se tragan: quien llama decide qué hacer."""


class SinTopeConocido(PresupuestoError):
    """No hay fila para ese día o el tope es NULL: sin permiso de gasto."""


class TopeDiarioAgotado(PresupuestoError):
    """La reserva superaría el tope diario."""


class TopeSemanalAgotado(PresupuestoError):
    """La reserva superaría el tope semanal de la fuente."""


def _dia(ahora: datetime):
    if ahora.tzinfo is None or ahora.utcoffset() is None:
        raise ValueError("el instante necesita zona horaria")
    return ahora.astimezone(timezone.utc).date()


def _candado(db, fuente: str) -> None:
    db.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"presupuesto:{fuente}",))


def fijar_tope(db, fuente: str, ahora: datetime, tope: int | None) -> None:
    """Fija (o deja sin tope, con None) el tope diario del día UTC de `ahora`. Sin UPDATE de evidencia: es estado."""
    if tope is not None and tope < 0:
        raise ValueError("tope negativo")
    db.execute(
        "INSERT INTO presupuesto (fuente, dia, tope, usadas) VALUES (%s, %s, %s, 0) "
        "ON CONFLICT (fuente, dia) DO UPDATE SET tope = EXCLUDED.tope",
        (fuente, _dia(ahora), tope),
    )


def reservar(db, fuente: str, n: int, ahora: datetime) -> None:
    """Reserva `n` peticiones. Lanza `PresupuestoError` (y no cambia nada) si no caben."""
    if n < 1:
        raise ValueError("n debe ser al menos 1")
    dia = _dia(ahora)
    with db.transaction():
        _candado(db, fuente)
        fila = db.execute(
            "SELECT tope, usadas FROM presupuesto WHERE fuente = %s AND dia = %s FOR UPDATE", (fuente, dia)
        ).fetchone()
        if fila is None or fila[0] is None:
            raise SinTopeConocido(f"sin tope conocido para {fuente} el {dia.isoformat()}")
        tope, usadas = fila
        if usadas + n > tope:
            raise TopeDiarioAgotado(f"{fuente} {dia.isoformat()}: {usadas}+{n} supera el tope {tope}")
        if fuente in TOPE_SEMANAL:
            lunes = dia - timedelta(days=dia.weekday())
            (semana,) = db.execute(
                "SELECT COALESCE(SUM(usadas), 0) FROM presupuesto WHERE fuente = %s AND dia BETWEEN %s AND %s",
                (fuente, lunes, lunes + timedelta(days=6)),
            ).fetchone()
            if semana + n > TOPE_SEMANAL[fuente]:
                raise TopeSemanalAgotado(f"{fuente} semana de {lunes.isoformat()}: {semana}+{n} supera "
                                         f"{TOPE_SEMANAL[fuente]}")
        db.execute("UPDATE presupuesto SET usadas = usadas + %s WHERE fuente = %s AND dia = %s", (n, fuente, dia))


def confirmar(db, fuente: str, n: int, ahora: datetime) -> None:
    """La respuesta llegó y se consumió la cuota reservada. No cambia `usadas` (ya se contó al reservar)."""
    if n < 1:
        raise ValueError("n debe ser al menos 1")
    with db.transaction():
        _candado(db, fuente)
        fila = db.execute("SELECT usadas FROM presupuesto WHERE fuente = %s AND dia = %s",
                          (fuente, _dia(ahora))).fetchone()
        if fila is None or fila[0] < n:
            raise ValueError("confirmar sin reserva previa")


def devolver(db, fuente: str, n: int, ahora: datetime) -> None:
    """Deshace una reserva cuya petición no consumió cuota. No puede dejar `usadas` negativo."""
    if n < 1:
        raise ValueError("n debe ser al menos 1")
    with db.transaction():
        _candado(db, fuente)
        db.execute(
            "UPDATE presupuesto SET usadas = GREATEST(usadas - %s, 0) WHERE fuente = %s AND dia = %s",
            (n, fuente, _dia(ahora)),
        )
