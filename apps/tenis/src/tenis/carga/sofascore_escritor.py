"""Escritura de la carga de SofaScore: por lotes (executemany), ON CONFLICT DO NOTHING, sin UPDATE ni DELETE.

Los ids se leen con SELECT por lote, nunca por fila (mismo patrón que tml_escritor).
"""
from psycopg.types.json import Jsonb


def recibo(cur, r: dict) -> int:
    cur.execute(
        "INSERT INTO recibo (fuente, recurso, parametros, recibido_en, estado_http, sha256, ruta_objeto, bytes, "
        "lote, retro) VALUES (%(fuente)s, %(recurso)s, '{}'::jsonb, %(recibido_en)s, NULL, %(sha256)s, "
        "%(ruta_objeto)s, %(bytes)s, %(lote)s, true) ON CONFLICT (fuente, recurso, sha256, recibido_en) DO NOTHING",
        r)
    cur.execute("SELECT recibo_id FROM recibo WHERE fuente = %s AND recurso = %s AND sha256 = %s AND recibido_en = %s",
                (r["fuente"], r["recurso"], r["sha256"], r["recibido_en"]))
    return cur.fetchone()[0]


def torneos(cur, filas: list[dict]) -> dict:
    """{(circuito, clave): torneo_id}. Los existentes no se tocan (identidad estable)."""
    if not filas:
        return {}
    cur.executemany(
        "INSERT INTO torneo (circuito, clave, nombre, categoria, fuente, recibo_id, recibido_en) "
        "VALUES (%(circuito)s, %(clave)s, %(nombre)s, %(categoria)s, 'sofascore', %(recibo_id)s, %(recibido_en)s) "
        "ON CONFLICT (circuito, clave) DO NOTHING", filas)
    cur.execute("SELECT t.torneo_id, t.circuito, t.clave FROM torneo t JOIN unnest(%s::text[], %s::text[]) "
                "AS k(c, cl) ON t.circuito = k.c AND t.clave = k.cl",
                ([f["circuito"] for f in filas], [f["clave"] for f in filas]))
    return {(c, k): t for (t, c, k) in cur.fetchall()}


def ediciones(cur, filas: list[dict]) -> dict:
    """{(torneo_id, temporada): edicion_id} de las ediciones de SofaScore."""
    if not filas:
        return {}
    cur.executemany(
        "INSERT INTO edicion (torneo_id, temporada, lunes_semana, fecha_fin, superficie, indoor, por_equipos, "
        "fuente, recibo_id, recibido_en, visible_desde) VALUES (%(torneo_id)s, %(temporada)s, %(lunes_semana)s, "
        "%(fecha_fin)s, %(superficie)s, %(indoor)s, %(por_equipos)s, 'sofascore', %(recibo_id)s, %(recibido_en)s, "
        "%(visible_desde)s) ON CONFLICT (torneo_id, temporada, fuente, recibido_en) DO NOTHING", filas)
    cur.execute("SELECT e.edicion_id, e.torneo_id, e.temporada FROM edicion e JOIN unnest(%s::bigint[], "
                "%s::int[]) AS k(t, a) ON e.torneo_id = k.t AND e.temporada = k.a WHERE e.fuente = 'sofascore'",
                ([f["torneo_id"] for f in filas], [f["temporada"] for f in filas]))
    return {(t, a): e for (e, t, a) in cur.fetchall()}


def ediciones_existentes(cur) -> dict:
    cur.execute("SELECT edicion_id, torneo_id, temporada FROM edicion WHERE fuente = 'sofascore'")
    return {(t, a): e for (e, t, a) in cur.fetchall()}


def partidos_existentes(cur, edicion_ids: list[int]) -> dict:
    if not edicion_ids:
        return {}
    cur.execute("SELECT partido_id, edicion_id, ronda, jugador_1, jugador_2 FROM partido "
                "WHERE edicion_id = ANY(%s)", (edicion_ids,))
    return {(e, r, a, b): p for (p, e, r, a, b) in cur.fetchall()}


def partidos(cur, filas: list[dict]) -> dict:
    """Inserta los partidos nuevos y devuelve {(edicion, ronda, j1, j2): partido_id} de esas filas."""
    if not filas:
        return {}
    cur.executemany(
        "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, recibo_id, recibido_en, "
        "visible_desde) VALUES (%(edicion_id)s, %(ronda)s, %(jugador_1)s, %(jugador_2)s, %(mejor_de)s, 'sofascore', "
        "%(recibo_id)s, %(recibido_en)s, %(visible_desde)s) ON CONFLICT (edicion_id, ronda, jugador_1, jugador_2) "
        "DO NOTHING", filas)
    return partidos_existentes(cur, list({f["edicion_id"] for f in filas}))


def programas(cur, filas: list[dict]) -> None:
    cur.executemany(
        "INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, pista, estado, fuente, recibo_id, "
        "recibido_en, visible_desde) VALUES (%(partido_id)s, %(inicio)s, 'fija', NULL, 'programado', 'sofascore', "
        "%(recibo_id)s, %(recibido_en)s, %(visible_desde)s) ON CONFLICT (partido_id, fuente, recibido_en) DO NOTHING",
        filas)


def resultados(cur, filas: list[dict]) -> None:
    for f in filas:
        f["sets"] = Jsonb(f["sets"]) if f["sets"] is not None else None
    cur.executemany(
        "INSERT INTO resultado (partido_id, estado, ganador, retira, sets, sets_completos, duracion_min, fuente, "
        "recibo_id, recibido_en, visible_desde) VALUES (%(partido_id)s, %(estado)s, %(ganador)s, %(retira)s, "
        "%(sets)s, %(sets_completos)s, %(duracion_min)s, 'sofascore', %(recibo_id)s, %(recibido_en)s, "
        "%(visible_desde)s) ON CONFLICT (partido_id, fuente, recibido_en) DO NOTHING", filas)


def estadisticas(cur, filas: list[dict]) -> None:
    cur.executemany(
        "INSERT INTO estadistica (partido_id, lado, aces, dobles_faltas, puntos_saque, primeros_dentro, "
        "primeros_ganados, segundos_ganados, juegos_saque, bp_salvados, bp_afrontados, fuente, recibo_id, "
        "recibido_en, visible_desde) VALUES (%(partido_id)s, %(lado)s, %(aces)s, %(dobles_faltas)s, "
        "%(puntos_saque)s, %(primeros_dentro)s, %(primeros_ganados)s, %(segundos_ganados)s, %(juegos_saque)s, "
        "%(bp_salvados)s, %(bp_afrontados)s, 'sofascore', %(recibo_id)s, %(recibido_en)s, %(visible_desde)s) "
        "ON CONFLICT (partido_id, lado, fuente, recibido_en) DO NOTHING", filas)


def pbp(cur, filas: list[dict]) -> None:
    cur.executemany(
        "INSERT INTO juego_pbp (partido_id, set_n, juego_n, sacador, puntos, es_tiebreak, fuente, recibo_id, "
        "recibido_en, visible_desde) VALUES (%(partido_id)s, %(set_n)s, %(juego_n)s, %(sacador)s, %(puntos)s, "
        "%(es_tiebreak)s, 'sofascore', %(recibo_id)s, %(recibido_en)s, %(visible_desde)s) "
        "ON CONFLICT (partido_id, fuente, recibido_en, set_n, juego_n) DO NOTHING", filas)
