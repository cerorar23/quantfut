"""Escritura de la carga TML en la base: por lotes, ON CONFLICT DO NOTHING, sin UPDATE ni DELETE (evidencia).

Los ids se resuelven con SELECT por lote, nunca por fila. `jugador` no tiene clave natural: se inserta en orden y
se asocian los ids devueltos en orden ascendente (la identidad se asigna en el orden del SELECT con ORDER BY).
"""
from psycopg.types.json import Jsonb


def recibo(cur, r: dict) -> int:
    cur.execute(
        "INSERT INTO recibo (fuente, recurso, parametros, recibido_en, estado_http, sha256, ruta_objeto, bytes, "
        "lote, retro) VALUES (%(fuente)s, %(recurso)s, %(parametros)s, %(recibido_en)s, NULL, %(sha256)s, "
        "%(ruta_objeto)s, %(bytes)s, %(lote)s, true) ON CONFLICT (fuente, recurso, sha256, recibido_en) DO NOTHING",
        {**r, "parametros": Jsonb({})})
    cur.execute("SELECT recibo_id FROM recibo WHERE fuente = %s AND recurso = %s AND sha256 = %s AND recibido_en = %s",
                (r["fuente"], r["recurso"], r["sha256"], r["recibido_en"]))
    return cur.fetchone()[0]


def jugadores_existentes(cur) -> dict:
    cur.execute("SELECT a.id_fuente, j.circuito, a.jugador_id FROM jugador_alias a "
                "JOIN jugador j ON j.jugador_id = a.jugador_id WHERE a.fuente = 'tml'")
    return {(circ, idt): jid for (idt, circ, jid) in cur.fetchall()}


def alias(cur, id_fuente: str, jugador_id: int, recibo_id: int, recibido_en) -> None:
    """Alias de una equivalencia manual: el id de TML apunta a un jugador ya existente (no crea jugador)."""
    cur.execute("INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
                "VALUES ('tml', %s, %s, 'manual', %s, %s) ON CONFLICT DO NOTHING",
                (id_fuente, jugador_id, recibo_id, recibido_en))


def crear_jugadores(cur, filas: list[tuple], recibo_id: int, recibido_en) -> list[int]:
    """filas: [(circuito, id_tml, nombre_alias)]. Devuelve el jugador_id de cada fila, en el mismo orden."""
    if not filas:
        return []
    circs = [f[0] for f in filas]
    cur.execute(
        "WITH ins AS (INSERT INTO jugador (circuito, recibo_id, recibido_en) "
        "SELECT c, %s, %s FROM unnest(%s::text[]) WITH ORDINALITY AS u(c, ord) ORDER BY ord "
        "RETURNING jugador_id) SELECT jugador_id FROM ins ORDER BY jugador_id",
        (recibo_id, recibido_en, circs))
    ids = [r[0] for r in cur.fetchall()]
    cur.executemany(
        "INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
        "VALUES ('tml', %s, %s, 'id_exacto', %s, %s) ON CONFLICT DO NOTHING",
        [(f[1], jid, recibo_id, recibido_en) for f, jid in zip(filas, ids)])
    return ids


def asercion(cur, filas: list[tuple], recibo_id: int, recibido_en) -> None:
    """filas: [(jugador_id, campo, valor)]."""
    cur.executemany(
        "INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
        "VALUES (%s, %s, %s, 'tml', %s, %s) ON CONFLICT DO NOTHING",
        [(j, c, v, recibo_id, recibido_en) for (j, c, v) in filas])


def torneos_existentes(cur) -> dict:
    cur.execute("SELECT torneo_id, circuito, clave FROM torneo")
    return {(c, k): t for (t, c, k) in cur.fetchall()}


def insertar_torneos(cur, filas: list[dict]) -> dict:
    if not filas:
        return {}
    cur.executemany(
        "INSERT INTO torneo (circuito, clave, nombre, categoria, fuente, recibo_id, recibido_en) "
        "VALUES (%(circuito)s, %(clave)s, %(nombre)s, %(categoria)s, 'tml', %(recibo_id)s, %(recibido_en)s) "
        "ON CONFLICT (circuito, clave) DO NOTHING", filas)
    cur.execute("SELECT t.torneo_id, t.circuito, t.clave FROM torneo t JOIN unnest(%s::text[], %s::text[]) "
                "AS k(c, cl) ON t.circuito = k.c AND t.clave = k.cl",
                ([f["circuito"] for f in filas], [f["clave"] for f in filas]))
    return {(c, k): t for (t, c, k) in cur.fetchall()}


def ediciones_existentes(cur) -> dict:
    cur.execute("SELECT edicion_id, torneo_id, temporada FROM edicion WHERE fuente = 'tml'")
    return {(t, a): e for (e, t, a) in cur.fetchall()}


def insertar_ediciones(cur, filas: list[dict]) -> dict:
    if not filas:
        return {}
    cur.executemany(
        "INSERT INTO edicion (torneo_id, temporada, lunes_semana, fecha_fin, superficie, indoor, por_equipos, "
        "fuente, recibo_id, recibido_en, visible_desde) VALUES (%(torneo_id)s, %(temporada)s, %(lunes_semana)s, "
        "%(fecha_fin)s, %(superficie)s, %(indoor)s, %(por_equipos)s, 'tml', %(recibo_id)s, %(recibido_en)s, "
        "%(visible_desde)s) ON CONFLICT (torneo_id, temporada, fuente, recibido_en) DO NOTHING", filas)
    cur.execute("SELECT e.edicion_id, e.torneo_id, e.temporada FROM edicion e JOIN unnest(%s::bigint[], "
                "%s::int[]) AS k(t, a) ON e.torneo_id = k.t AND e.temporada = k.a WHERE e.fuente = 'tml'",
                ([f["torneo_id"] for f in filas], [f["temporada"] for f in filas]))
    return {(t, a): e for (e, t, a) in cur.fetchall()}


def partidos(cur, filas: list[dict]) -> dict:
    """Inserta (ON CONFLICT DO NOTHING) y devuelve {(edicion, ronda, j1, j2): partido_id} de esas ediciones."""
    if not filas:
        return {}
    cur.executemany(
        "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, entrada_1, entrada_2, fuente, "
        "recibo_id, recibido_en, visible_desde) VALUES (%(edicion_id)s, %(ronda)s, %(jugador_1)s, %(jugador_2)s, "
        "%(mejor_de)s, %(entrada_1)s, %(entrada_2)s, 'tml', %(recibo_id)s, %(recibido_en)s, %(visible_desde)s) "
        "ON CONFLICT (edicion_id, ronda, jugador_1, jugador_2) DO NOTHING", filas)
    cur.execute("SELECT partido_id, edicion_id, ronda, jugador_1, jugador_2 FROM partido WHERE edicion_id = ANY(%s)",
                ([f["edicion_id"] for f in filas],))
    return {(e, r, a, b): p for (p, e, r, a, b) in cur.fetchall()}


def resultados(cur, filas: list[dict]) -> None:
    for f in filas:
        if f["sets"] is not None:
            f["sets"] = Jsonb(f["sets"])
    cur.executemany(
        "INSERT INTO resultado (partido_id, estado, ganador, retira, sets, sets_completos, duracion_min, fuente, "
        "recibo_id, recibido_en, visible_desde) VALUES (%(partido_id)s, %(estado)s, %(ganador)s, %(retira)s, "
        "%(sets)s, %(sets_completos)s, %(duracion_min)s, 'tml', %(recibo_id)s, %(recibido_en)s, %(visible_desde)s) "
        "ON CONFLICT (partido_id, fuente, recibido_en) DO NOTHING", filas)


def estadisticas(cur, filas: list[dict]) -> None:
    cur.executemany(
        "INSERT INTO estadistica (partido_id, lado, aces, dobles_faltas, puntos_saque, primeros_dentro, "
        "primeros_ganados, segundos_ganados, juegos_saque, bp_salvados, bp_afrontados, fuente, recibo_id, "
        "recibido_en, visible_desde) VALUES (%(partido_id)s, %(lado)s, %(aces)s, %(dobles_faltas)s, "
        "%(puntos_saque)s, %(primeros_dentro)s, %(primeros_ganados)s, %(segundos_ganados)s, %(juegos_saque)s, "
        "%(bp_salvados)s, %(bp_afrontados)s, 'tml', %(recibo_id)s, %(recibido_en)s, %(visible_desde)s) "
        "ON CONFLICT (partido_id, lado, fuente, recibido_en) DO NOTHING", filas)


def ranking(cur, filas: list[dict]) -> None:
    cur.executemany(
        "INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, puntos, origen, fuente, recibo_id, "
        "recibido_en, visible_desde) VALUES (%(circuito)s, %(fecha_publicacion)s, %(jugador_id)s, %(posicion)s, "
        "%(puntos)s, 'tml_por_partido', 'tml', %(recibo_id)s, %(recibido_en)s, %(visible_desde)s) "
        "ON CONFLICT (circuito, fecha_publicacion, jugador_id, fuente, recibido_en) DO NOTHING", filas)


def contar(cur, tabla: str) -> int:
    cur.execute(f"SELECT count(*) FROM {tabla}")  # tabla fija del código, nunca entrada del usuario
    return cur.fetchone()[0]
