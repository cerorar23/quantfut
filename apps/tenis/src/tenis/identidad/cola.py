"""Cola `sin_resolver`: lo que la resolución de identidad no decide. Se cuenta y se revisa; nunca se descarta en silencio.

`sin_resolver` no tiene clave única: la idempotencia se fuerza aquí (misma fuente, id, motivo y recepción = una fila).
"""
import json

MOTIVOS = ("ambiguo", "sin_candidato", "edad_contradictoria", "edad_dudosa", "sin_edad", "sin_pais",
           "confirmado_distinto", "manual_sin_principal", "contexto_ambiguo")


def registrar(cur, *, fuente: str, id_fuente: str, nombre: str, motivo: str, contexto: dict | None,
              recibo_id: int, recibido_en) -> bool:
    """Anota una fila de la cola. Devuelve True si la fila es nueva; repetirla no añade nada."""
    if motivo not in MOTIVOS:
        raise ValueError(f"motivo de cola desconocido: {motivo}")
    cur.execute(
        "INSERT INTO sin_resolver (fuente, id_fuente, nombre_fuente, motivo, contexto, recibo_id, recibido_en) "
        "SELECT %s, %s, %s, %s, %s::jsonb, %s, %s WHERE NOT EXISTS ("
        "SELECT 1 FROM sin_resolver WHERE fuente = %s AND id_fuente = %s AND motivo = %s AND recibido_en = %s)",
        (fuente, id_fuente, nombre, motivo, json.dumps(contexto or {}), recibo_id, recibido_en,
         fuente, id_fuente, motivo, recibido_en))
    return cur.rowcount == 1


def leer(cur, *, motivo: str | None = None) -> list[dict]:
    """Filas de la cola, en orden de anotación. Filtro opcional por motivo."""
    sql = ("SELECT sin_id, fuente, id_fuente, nombre_fuente, motivo, contexto, recibido_en "
           "FROM sin_resolver {} ORDER BY sin_id")
    if motivo is None:
        cur.execute(sql.format(""))
    else:
        cur.execute(sql.format("WHERE motivo = %s"), (motivo,))
    columnas = ("sin_id", "fuente", "id_fuente", "nombre_fuente", "motivo", "contexto", "recibido_en")
    return [dict(zip(columnas, fila)) for fila in cur.fetchall()]
