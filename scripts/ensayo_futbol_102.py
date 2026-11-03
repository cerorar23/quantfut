"""Genera un ensayo SQL autónomo para un PostgreSQL AISLADO. Siempre termina en ROLLBACK."""
import ast
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]

def literal(archivo, nombre):
    tree=ast.parse((root/archivo).read_text(encoding='utf-8'))
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id==nombre for t in n.targets))

sql=['\\set ON_ERROR_STOP on','BEGIN;',literal('tests/test_futbol_sofascore.py','STUBS'),
     literal('tests/test_futbol_previo_reglas.py','EXTRA'),
     'ALTER TABLE matches ADD COLUMN home_shots SMALLINT, ADD COLUMN away_shots SMALLINT, '
     'ADD COLUMN home_shots_target SMALLINT, ADD COLUMN away_shots_target SMALLINT;']
for name in ('094_futbol_dato_unico.sql','096_futbol_dato_ampliado.sql','097_futbol_dato_mitades.sql',
             '098_futbol_reglas_sancion_y_derbis.sql','099_futbol_dato_previo.sql'):
    sql.append((root/'db'/name).read_text(encoding='utf-8').replace('BEGIN;','').replace('COMMIT;',''))
sql.append("""
INSERT INTO matches(match_id,kickoff_utc,home_shots,home_shots_target) VALUES('m','2026-11-04T18:00Z',2,7);
SELECT futbol.jugador_canonico('fotmob',10,'Jugador');
INSERT INTO futbol.dato(match_id,tipo,side,jugador_id,fuente,recibido_en,tiros_totales,tiros_puerta)
 VALUES('m','jugador','home',-10,'fotmob',now(),0,1);
""")
sql.append((root/'db/102_futbol_integridad_y_capturas.sql').read_text(encoding='utf-8').replace('BEGIN;','').replace('COMMIT;',''))
sql.append("""
INSERT INTO injuries(match_id,side,player_id,player_name,status_type,captured_at,source)
 VALUES('m','home',10,'Jugador','missing','2026-11-03T12:22:33Z','fotmob');
INSERT INTO injuries(match_id,side,player_id,player_name,status_type,captured_at,source)
 VALUES('m','home',10,'Jugador','doubtful','2026-11-03T12:22:44Z','fotmob');
INSERT INTO fotmob_jugador_previo(match_id,side,jugador_id,nombre,titular,capturado_en)
 VALUES('m','home',10,'Jugador',true,'2026-11-03T12:23:33Z');
INSERT INTO fotmob_baja_previa(match_id,side,jugador_id,nombre,tipo,capturado_en)
 VALUES('m','away',11,'Otro','doubtful','2026-11-03T12:24:33Z');
INSERT INTO lineups_previstas(match_id,side,formation,starters,confirmed,captured_at,source)
 VALUES('m','home','4-4-2','[{"player_id":10,"name":"Jugador","pos":"D","number":3}]',true,'2026-11-03T12:25:33Z','fotmob');
INSERT INTO injuries(match_id,side,player_id,player_name,status_type,captured_at,source)
 VALUES('m','home',10,'Jugador','missing','2026-11-03T12:22:33Z','fotmob');
DO $test$
BEGIN
 IF (SELECT count(*) FROM futbol.cuarentena)<>2 THEN RAISE EXCEPTION 'Cuarentena incompleta'; END IF;
 IF (SELECT home_shots FROM matches WHERE match_id='m') IS NOT NULL THEN RAISE EXCEPTION 'Dato inválido conservado'; END IF;
 IF (SELECT count(*) FROM futbol.dato WHERE tipo='baja_previa' AND side='home')<>2 THEN RAISE EXCEPTION 'Captura duplicada o colisión de minuto'; END IF;
 IF NOT EXISTS(SELECT FROM futbol.dato WHERE tipo='baja_previa' AND side='home' AND recibido_en='2026-11-03T12:22:33Z' AND pit='previo') THEN RAISE EXCEPTION 'Reloj cambiado'; END IF;
 IF (SELECT count(*) FROM futbol.dato WHERE tipo='once_previo')<>2 THEN RAISE EXCEPTION 'Once sin propagar'; END IF;
 IF (SELECT count(*) FROM futbol.dato WHERE tipo='alineacion_previa')<>1 THEN RAISE EXCEPTION 'Alineación sin propagar'; END IF;
 IF EXISTS(SELECT FROM futbol.reglas_sancion_verificadas) THEN RAISE EXCEPTION 'Regla no verificada admitida'; END IF;
 IF NOT EXISTS(SELECT FROM futbol.regla_sancion WHERE liga='mx.liga_mx' AND tipo='pendiente') THEN RAISE EXCEPTION 'Regla MX falsa'; END IF;
END $test$;
SELECT 'PASS: migración, cuarentena, recepción original, cuatro tablas de captura, colisión de minuto e idempotencia';
ROLLBACK;
""")
Path(sys.argv[1]).write_text('\n'.join(sql),encoding='utf-8')
