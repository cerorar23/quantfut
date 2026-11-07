"""Cursor de cada colector en `tenis_op.cursor` (fuente, recurso, valor).

Regla: el cursor avanza SOLO después de confirmar el lote. `ejecutar_lote` ejecuta el lote y el avance en la
misma transacción: si el lote lanza una excepción, la evidencia escrita y el cursor vuelven a su estado previo.
"""
from typing import Callable

# Lote: recibe (db, valor_previo) y escribe evidencia. Devuelve el nuevo valor del cursor, o None si el lote
# no debe avanzar el cursor (p. ej. respuesta rechazada): en ese caso solo se conserva lo que el lote haya escrito.
Lote = Callable[[object, str | None], str | None]


def leer(db, fuente: str, recurso: str) -> str | None:
    fila = db.execute('SELECT valor FROM "cursor" WHERE fuente = %s AND recurso = %s', (fuente, recurso)).fetchone()
    return fila[0] if fila else None


def ejecutar_lote(db, fuente: str, recurso: str, lote: Lote) -> str | None:
    """Ejecuta `lote` y avanza el cursor en una sola transacción. Devuelve el valor final del cursor."""
    with db.transaction():
        previo = leer(db, fuente, recurso)
        nuevo = lote(db, previo)
        if nuevo is None:
            return previo
        if not isinstance(nuevo, str) or not nuevo:
            raise ValueError("el valor del cursor debe ser una cadena no vacía")
        db.execute(
            'INSERT INTO "cursor" (fuente, recurso, valor, actualizado_en) VALUES (%s, %s, %s, now()) '
            "ON CONFLICT (fuente, recurso) DO UPDATE SET valor = EXCLUDED.valor, actualizado_en = EXCLUDED.actualizado_en",
            (fuente, recurso, nuevo),
        )
        return nuevo
