"""db/098 (umbrales de sanción y derbis) y db/099 (lo previo al partido en `futbol.dato`)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from test_futbol_sofascore import STUBS, pg_connection

KICKOFF = datetime(2026, 10, 25, 18, 0, tzinfo=timezone.utc)
EXTRA = """
ALTER TABLE matches ADD COLUMN league_id TEXT, ADD COLUMN season TEXT;
CREATE TABLE teams (team_id BIGINT PRIMARY KEY, league_id TEXT, canonical_name TEXT);
CREATE TABLE fotmob_baja_previa (match_id TEXT, capturado_en TIMESTAMPTZ, side TEXT, jugador_id BIGINT, nombre TEXT,
    valor_mercado BIGINT, tipo TEXT, lesion_id INTEGER, regreso_texto TEXT, regreso_fecha TIMESTAMPTZ);
CREATE TABLE fotmob_jugador_previo (match_id TEXT, capturado_en TIMESTAMPTZ, side TEXT, jugador_id BIGINT, nombre TEXT,
    titular BOOLEAN, posicion_id INTEGER, valor_mercado BIGINT);
CREATE TABLE injuries (match_id TEXT, side TEXT, player_id BIGINT, player_name TEXT, status_type TEXT, reason TEXT,
    captured_at TIMESTAMPTZ, source TEXT, expected_return DATE);
CREATE TABLE lineups_previstas (match_id TEXT, side TEXT, formation TEXT, starters JSONB, confirmed BOOLEAN,
    source TEXT, receipt_id INTEGER, captured_at TIMESTAMPTZ);
"""
STARTERS = ('[{"pos":"G","src":"sofascore","name":"Portiere","number":1,"player_id":901},'
            '{"pos":"D","src":"sofascore","name":"Difensore","number":2,"player_id":902}]')


def with_schema(connection):
    connection.execute(STUBS)
    connection.execute(EXTRA)
    root = Path(__file__).resolve().parents[1]
    for name in ('094_futbol_dato_unico.sql', '096_futbol_dato_ampliado.sql', '097_futbol_dato_mitades.sql',
                 '098_futbol_reglas_sancion_y_derbis.sql', '099_futbol_dato_previo.sql'):
        sql = (root / 'db' / name).read_text(encoding='utf-8')
        connection.execute(sql.replace('BEGIN;', '').replace('COMMIT;', ''))


def test_las_reglas_de_sancion_quedan_sin_verificar_hasta_confirmarlas():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            reglas = {r[0]: r[1:] for r in connection.execute(
                "SELECT liga, tipo, amarillas, fuente, verificada FROM futbol.regla_sancion").fetchall()}
            assert reglas['it.serie_a'] == ('fijo', 5, 'observado', False)
            assert reglas['br.serie_a'][:2] == ('fijo', 3)
            assert reglas['gb.premier_league'][0] == 'por_jornada' and reglas['gb.premier_league'][1] is None
            assert reglas['mx.liga_mx'][0] == 'sin_acumulacion'
            assert 'fr.ligue_1' not in reglas   # la medición no la decide: sin fila hasta confirmarla
            assert not any(r[-1] for r in reglas.values())
        finally:
            connection.rollback()


def test_amarillas_acumuladas_cuentan_solo_la_liga_la_temporada_y_lo_anterior():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            casos = [('it.serie_a', '2526', 0), ('it.serie_a', '2526', 7), ('it.serie_a', '2425', 14),
                     ('eu.ucl', '2526', 21), ('it.serie_a', '2526', 28)]
            for i, (liga, temp, dias) in enumerate(casos):
                mid = f'p{i}'
                connection.execute("INSERT INTO matches (match_id, league_id, season, kickoff_utc) VALUES (%s,%s,%s,%s)",
                                   (mid, liga, temp, KICKOFF + timedelta(days=dias)))
                connection.execute("INSERT INTO futbol.dato (match_id, tipo, evento, jugador_id, fuente, recibido_en, subtipo, clase) "
                                   "VALUES (%s,'incidencia',1,7,'sofascore',now(),'card','yellow')", (mid,))
            n = connection.execute("SELECT futbol.amarillas_acumuladas(7, 'it.serie_a', '2526', %s)",
                                   (KICKOFF + timedelta(days=28),)).fetchone()[0]
            assert n == 2   # la de 2425 y la de la Champions no cuentan, ni la del propio partido
        finally:
            connection.rollback()


def test_derbis_misma_ciudad_y_lista_manual_sin_ambiguedad():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            equipos = [(1, 'it.serie_a', 'Milan'), (2, 'it.serie_a', 'Inter'), (3, 'it.serie_a', 'Roma'),
                       (4, 'it.serie_a', 'Juventus'), (5, 'es.laliga', 'Barcelona'), (6, 'es.laliga', 'Real Madrid'),
                       (7, 'es.laliga', 'Real Madrid B'), (8, 'it.serie_a', 'Lazio'),
                       (9, 'it.serie_a', 'Torino'), (10, 'it.serie_a', 'Torino B')]
            connection.cursor().executemany("INSERT INTO teams VALUES (%s,%s,%s)", equipos)
            ciudad = {1: 'Milano', 2: 'Milano', 3: 'Roma', 4: 'Torino', 5: 'Barcelona', 6: 'Madrid', 7: 'Madrid',
                      8: 'Roma', 9: 'Torino', 10: 'Torino'}
            liga = {e[0]: e[1] for e in equipos}
            for team, city in ciudad.items():
                mid = f'm{team}'
                connection.execute("INSERT INTO matches (match_id, league_id, home_team_id) VALUES (%s,%s,%s)",
                                   (mid, liga[team], team))
                connection.execute("INSERT INTO futbol.dato (match_id, tipo, fuente, recibido_en, estadio_ciudad) "
                                   "VALUES (%s,'estadio','opentopodata',now(),%s)", (mid, city))
            res = dict(connection.execute("SELECT * FROM futbol.cargar_derbis()").fetchall())
            assert res['ciudad'] == 3          # Milan-Inter, Roma-Lazio y Real Madrid-Real Madrid B (ciudad con dos clubes)
            pares = {(r[0], r[1]): r[2] for r in connection.execute(
                "SELECT equipo_a, equipo_b, origen FROM futbol.derbi").fetchall()}
            assert pares[(1, 2)] == 'ciudad'
            assert not any(a in (9, 10) or b in (9, 10) for a, b in pares)   # Turin tiene tres clubes de la liga: sin regla de ciudad
            assert pares[(2, 4)] == 'manual'      # Derby d'Italia: distinta ciudad
            assert (1, 4) in pares                # Juventus-Milan, manual
            assert pares[(5, 6)] == 'manual'      # El Clasico: patron anclado, "Real Madrid B" no lo confunde
            # un patron suelto que casa con dos equipos no se resuelve a ninguno
            assert connection.execute("SELECT futbol.equipo_por_nombre('es.laliga', 'Real Madrid')").fetchone() == (None,)
            assert connection.execute("SELECT futbol.equipo_por_nombre('es.laliga', '^Real Madrid$')").fetchone() == (6,)
            assert connection.execute("SELECT futbol.es_derbi(2, 1), futbol.es_derbi(1, 3)").fetchone() == (True, False)
            assert dict(connection.execute("SELECT * FROM futbol.cargar_derbis()").fetchall())['ciudad'] == 0  # idempotente
        finally:
            connection.rollback()


def test_lo_previo_entra_con_la_hora_real_el_pit_y_sin_duplicar():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            connection.execute("INSERT INTO matches (match_id, league_id, season, kickoff_utc) VALUES ('x','it.serie_a','2526',%s)", (KICKOFF,))
            antes, despues = KICKOFF - timedelta(hours=3), KICKOFF + timedelta(minutes=5)
            connection.cursor().executemany("INSERT INTO fotmob_baja_previa VALUES ('x',%s,'home',%s,%s,1000,'injury',1,'Semana 2',NULL)",
                                   [(antes, 501, 'Rossi'), (despues, 501, 'Rossi')])
            connection.execute("INSERT INTO fotmob_jugador_previo VALUES ('x',%s,'home',601,'Bianchi',true,3,500)", (antes,))
            connection.execute("INSERT INTO injuries VALUES ('x','away',801,'Verdi','Questionable','Knock',%s,'api_football',NULL)", (antes,))
            connection.execute("INSERT INTO lineups_previstas VALUES ('x','home','4-3-3', %s::jsonb, false, 'sofascore', 1, %s)",
                               (STARTERS, antes))
            primera = {r[0]: r[1] for r in connection.execute("SELECT * FROM futbol.cargar_previo()").fetchall()}
            assert primera == {'baja_previa fotmob': 2, 'baja_previa injuries': 1, 'once_previo fotmob': 1,
                               'alineacion_previa': 1, 'once_previo previsto': 2}
            pits = connection.execute("SELECT recibido_en, pit FROM futbol.dato WHERE tipo='baja_previa' AND fuente='fotmob' "
                                      "ORDER BY recibido_en").fetchall()
            assert pits == [(antes, 'previo'), (despues, 'posterior')]   # la de despues del saque no sirve para predecir
            assert connection.execute("SELECT estado FROM futbol.dato WHERE fuente='api_football'").fetchone() == ('doubtful',)
            assert connection.execute("SELECT formacion, confirmada, pit FROM futbol.dato WHERE tipo='alineacion_previa'").fetchone() == ('4-3-3', False, 'previo')
            assert connection.execute("SELECT count(*) FROM futbol.dato WHERE tipo='once_previo' AND titular").fetchone()[0] == 3
            assert connection.execute("SELECT count(*) FROM futbol.v_baja_a_t").fetchone()[0] == 2   # solo las previas al saque
            segunda = [r[1] for r in connection.execute("SELECT * FROM futbol.cargar_previo()").fetchall()]
            assert segunda == [0, 0, 0, 0, 0]                          # recargar no duplica nada
        finally:
            connection.rollback()
