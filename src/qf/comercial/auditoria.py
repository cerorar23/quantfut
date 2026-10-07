"""Rastro de las acciones del panel. `admin_audit` es inmutable (db/043)."""
from __future__ import annotations

from psycopg.types.json import Jsonb


def audit(c, actor: str, action: str, account_id: int | None = None,
          detail: dict | None = None) -> None:
    """Se escribe con la conexión de la acción: misma transacción, o ninguna de las dos."""
    c.execute("INSERT INTO admin_audit (actor, action, account_id, detail) VALUES (%s, %s, %s, %s)",
              (actor, action, account_id, Jsonb(detail or {})))
