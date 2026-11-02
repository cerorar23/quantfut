"""Inserciones mínimas para las pruebas de la base `nba_datos`."""

def nueva_entidad(db, tipo, id_en_fuente, nombre="x", fuente="nba_oficial", canonica_id=None):
    return db.execute(
        "INSERT INTO nba.entidad (tipo, canonica_id, fuente, id_en_fuente, nombre) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING entidad_id",
        (tipo, canonica_id, fuente, id_en_fuente, nombre)).fetchone()[0]


def metrica(db, nombre):
    return db.execute("SELECT metrica_id FROM nba.metrica WHERE nombre = %s", (nombre,)).fetchone()[0]


def nuevo_dato(db, partido, entidad, nombre="puntos", valor=10.0, etiqueta=None, fase="final",
               fuente="nba_oficial", captura_id=None, recibido="2026-11-01T12:00:00Z", periodo=0):
    return db.execute(
        "INSERT INTO nba.dato (partido_id, entidad_id, periodo, metrica_id, valor, etiqueta, fase, fuente, "
        "captura_id, recibido_en) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING dato_id",
        (partido, entidad, periodo, metrica(db, nombre), valor, etiqueta, fase, fuente, captura_id, recibido)
    ).fetchone()[0]


def nueva_captura(db, fuente="nba_oficial", fase="final"):
    return db.execute(
        "INSERT INTO nba.captura (fuente, objetivo, fase, solicitado_en, ok) VALUES (%s,'x',%s, now(), true) "
        "RETURNING captura_id", (fuente, fase)).fetchone()[0]


def nueva_cuota(db, partido, valor, lado, fase="cierre", recibido="2026-11-01T21:00:00Z", fuente="propline",
                casa="bet365", mercado="ganador", contrato="c1", linea=None, entidad=None):
    return db.execute(
        "INSERT INTO nba.cuota (partido_id, fuente, casa, mercado, entidad_id, linea, lado, cuota, contrato_id, "
        "fase, recibido_en) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING cuota_id",
        (partido, fuente, casa, mercado, entidad, linea, lado, valor, contrato, fase, recibido)).fetchone()[0]

