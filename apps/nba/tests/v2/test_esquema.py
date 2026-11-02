import psycopg
import pytest

from ayudas import nueva_entidad, nuevo_dato

TABLAS_EVIDENCIA = ["entidad", "captura", "dato", "cuota", "evento", "pronostico"]
SIETE = ["entidad", "dato", "cuota", "captura", "evento", "pronostico", "metrica"]


def test_tablas_y_claves_existen(base_migrada):
    presentes = {r[0] for r in base_migrada.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'nba'")}
    assert set(SIETE) <= presentes
    claves = {r[0] for r in base_migrada.execute(
        "SELECT conrelid::regclass::text FROM pg_constraint WHERE contype = 'p' AND connamespace = 'nba'::regnamespace")}
    assert {f"nba.{t}" for t in SIETE} <= claves


def test_cuota_rechaza_valor_menor_o_igual_a_uno(base_migrada):
    partido = nueva_entidad(base_migrada, "partido", "g1")
    with pytest.raises(psycopg.errors.CheckViolation):
        base_migrada.execute(
            "INSERT INTO nba.cuota (partido_id, fuente, casa, mercado, lado, cuota, contrato_id, fase, recibido_en) "
            "VALUES (%s,'propline','x','ganador','local',1.0,'c1','cierre', now())", (partido,))


def test_dato_exige_valor_o_etiqueta(base_migrada):
    p = nueva_entidad(base_migrada, "partido", "g1")
    j = nueva_entidad(base_migrada, "jugador", "p1")
    with pytest.raises(psycopg.errors.CheckViolation):
        nuevo_dato(base_migrada, p, j, valor=None, etiqueta=None)


def test_dato_clave_unica_evita_duplicados(base_migrada):
    p = nueva_entidad(base_migrada, "partido", "g1")
    j = nueva_entidad(base_migrada, "jugador", "p1")
    nuevo_dato(base_migrada, p, j)
    with pytest.raises(psycopg.errors.UniqueViolation):
        nuevo_dato(base_migrada, p, j, valor=11.0)


COLUMNA_EDITABLE = {"entidad": "nombre", "captura": "objetivo", "dato": "fase", "cuota": "casa",
                    "evento": "tipo", "pronostico": "mercado"}


@pytest.mark.parametrize("tabla", TABLAS_EVIDENCIA)
@pytest.mark.parametrize("instruccion", [
    "UPDATE nba.{t} SET {c} = {c} WHERE false",
    "DELETE FROM nba.{t} WHERE false",
    "TRUNCATE nba.{t} CASCADE",
])
def test_cambios_rechazados_en_tablas_de_evidencia(base_migrada, tabla, instruccion):
    texto = instruccion.format(t=tabla, c=COLUMNA_EDITABLE[tabla])
    with pytest.raises(psycopg.errors.RaiseException, match="inmutable"):
        base_migrada.execute(texto)


@pytest.mark.parametrize("tabla", TABLAS_EVIDENCIA)
def test_truncate_simple_tambien_falla(base_migrada, tabla):
    # Las tablas referenciadas fallan antes por llave foránea; las demás, por el disparador.
    with pytest.raises((psycopg.errors.RaiseException, psycopg.errors.FeatureNotSupported)):
        base_migrada.execute(f"TRUNCATE nba.{tabla}")


def test_entidad_canonica_apunta_a_si_misma(base_migrada):
    e = nueva_entidad(base_migrada, "jugador", "p1")
    assert base_migrada.execute("SELECT canonica_id FROM nba.entidad WHERE entidad_id = %s", (e,)).fetchone()[0] == e


def test_alias_apunta_a_la_canonica(base_migrada):
    canonica = nueva_entidad(base_migrada, "jugador", "p1")
    alias = nueva_entidad(base_migrada, "jugador", "9001", fuente="sofascore", canonica_id=canonica)
    fila = base_migrada.execute("SELECT canonica_id FROM nba.entidad WHERE entidad_id = %s", (alias,)).fetchone()
    assert fila[0] == canonica and alias != canonica
    with pytest.raises(psycopg.errors.UniqueViolation):
        nueva_entidad(base_migrada, "jugador", "9001", fuente="sofascore")


def test_semillas_fuentes_prioridad_unica(base_migrada):
    filas = base_migrada.execute("SELECT fuente, prioridad FROM nba.fuente ORDER BY prioridad").fetchall()
    assert [f for f, _ in filas] == ["nba_oficial", "sofascore", "espn", "basketball_reference", "rotowire",
                                     "propline", "the_odds_api", "sharpapi", "betsapi"]
    assert [p for _, p in filas] == list(range(1, 10))


def test_semillas_metricas_nombres_unicos_y_nivel_valido(base_migrada):
    filas = base_migrada.execute("SELECT nombre, nivel, resolucion, es_proyeccion FROM nba.metrica").fetchall()
    nombres = [f[0] for f in filas]
    assert len(nombres) == len(set(nombres)) >= 30
    requeridas = {"inicio_programado_utc", "estado_partido", "equipo_local", "equipo_visitante", "arbitro_asignado",
                  "puntos", "minutos", "rebotes", "asistencias", "triples_anotados", "robos", "tapones",
                  "estado_disponibilidad", "titular_esperado", "minutos_proyectados"}
    assert requeridas <= set(nombres)
    por_nombre = {f[0]: f for f in filas}
    assert por_nombre["estado_disponibilidad"][2] == "por_fuente"
    assert por_nombre["minutos_proyectados"][3] is True and por_nombre["minutos_proyectados"][2] == "por_fuente"
    assert por_nombre["puntos"][2] == "prioridad" and por_nombre["puntos"][1] == "equipo_jugador"
    with pytest.raises(psycopg.errors.CheckViolation):
        base_migrada.execute("INSERT INTO nba.metrica (metrica_id, nombre, nivel, definicion) "
                             "VALUES (9999, 'x', 'otro', 'x')")


def test_pronostico_unico_con_entidad_nula(base_migrada):
    p = nueva_entidad(base_migrada, "partido", "g1")
    insertar = ("INSERT INTO nba.pronostico (partido_id, mercado, version_modelo, version_datos, objetivo_en, "
                "sellado_en, escenarios, distribucion, hash_previo, hash) "
                "VALUES (%s,'ganador','v2.0','d1','2026-11-01T22:00Z','2026-11-01T22:05Z','[]','{}','0',%s)")
    base_migrada.execute(insertar, (p, "h1"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        base_migrada.execute(insertar, (p, "h2"))
