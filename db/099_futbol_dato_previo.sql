-- 099: fase 2 de `futbol.dato`: lo que se SABÍA antes del partido, con la hora real de cada captura.
--
-- El motor predice con lo último conocido a T-60 (once previsto, bajas y dudas anunciadas), no con el once que acabó
-- jugando ni con las bajas reconstruidas después. Esas capturas ya se hacen (FotMob cada hora, SportsAPIPro/SofaScore
-- para el once previsto, `injuries` de tres fuentes), pero vivían en cuatro tablas de origen sin unificar. Aquí pasan a
-- la tabla única, con tres tipos nuevos y un `pit` propio:
--
--   tipo               una fila por…                         qué trae
--   baja_previa        jugador ausente o dudoso y captura    estado (injury, suspension, missing, doubtful…), motivo, regreso
--   once_previo        jugador del once previsto y captura   titular, posición, camiseta
--   alineacion_previa  lado y captura                        formación y si el club ya confirmó el once
--
--   pit = 'previo'     capturado ANTES del saque inicial con su hora real de recepción (`recibido_en`): es lo único
--                      que puede usarse como «sabido a T-60» sin reconstruir.
--   pit = 'posterior'  capturado después del saque inicial: se conserva pero no sirve para predecir.
--
-- Cada captura es una observación y se conserva entera (no hay «una fuente por tipo»): el motor toma, para cada
-- fuente, la última captura anterior a T-60. `evento` identifica la captura: minutos desde 2020-01-01 UTC × 10 + el
-- número de la fuente (fotmob 1, sofascore 2, api_football 3, sportsapipro 4), así que dos fuentes que capturan en
-- el mismo minuto no chocan. Cargar de nuevo la misma captura no duplica nada.
BEGIN;

ALTER TABLE futbol.dato DROP CONSTRAINT IF EXISTS dato_tipo_check;
ALTER TABLE futbol.dato ADD CONSTRAINT dato_tipo_check CHECK (tipo IN
    ('jugador','equipo','baja','alineacion','entrenador','contexto','tiro','incidencia','clima','estadio',
     'momentum','posicion','baja_previa','once_previo','alineacion_previa'));
ALTER TABLE futbol.dato DROP CONSTRAINT IF EXISTS dato_pit_check;
ALTER TABLE futbol.dato ADD CONSTRAINT dato_pit_check CHECK (pit IN ('posterior','reconstruido','no_acreditado','previo'));

CREATE OR REPLACE FUNCTION futbol.evento_captura(p_captura TIMESTAMPTZ, p_fuente TEXT) RETURNS INTEGER
LANGUAGE sql IMMUTABLE AS $f$
    SELECT (floor(extract(epoch FROM p_captura - timestamptz '2020-01-01 00:00:00+00') / 60)::integer * 10)
           + CASE p_fuente WHEN 'fotmob' THEN 1 WHEN 'sofascore' THEN 2 WHEN 'api_football' THEN 3 WHEN 'sportsapipro' THEN 4 ELSE 9 END
$f$;

DROP FUNCTION IF EXISTS futbol.cargar_previo(TIMESTAMPTZ);
CREATE FUNCTION futbol.cargar_previo(p_desde TIMESTAMPTZ DEFAULT NULL)
RETURNS TABLE (entidad TEXT, filas BIGINT)
LANGUAGE plpgsql AS $f$
#variable_conflict use_column
DECLARE n BIGINT;
BEGIN
    -- bajas previas de FotMob
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, evento, fuente, recibido_en, pit, nombre, id_en_fuente,
                             estado, regreso_texto, regreso_fecha, valor_mercado)
    SELECT b.match_id, 'baja_previa', b.side, futbol.jugador_canonico('fotmob', b.jugador_id, b.nombre),
           futbol.evento_captura(b.capturado_en, 'fotmob'), 'fotmob', b.capturado_en,
           CASE WHEN b.capturado_en < m.kickoff_utc THEN 'previo' ELSE 'posterior' END, b.nombre, b.jugador_id,
           COALESCE(b.tipo, 'missing'), b.regreso_texto, b.regreso_fecha, b.valor_mercado
      FROM fotmob_baja_previa b JOIN matches m USING (match_id)
     WHERE b.side IN ('home', 'away') AND (p_desde IS NULL OR b.capturado_en >= p_desde)
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT; entidad := 'baja_previa fotmob'; filas := n; RETURN NEXT;

    -- bajas previas de `injuries` (API-Football, FotMob, SofaScore)
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, evento, fuente, recibido_en, pit, nombre, id_en_fuente,
                             estado, descripcion, regreso_fecha)
    SELECT i.match_id, 'baja_previa', i.side, futbol.jugador_canonico(i.source, i.player_id, i.player_name),
           futbol.evento_captura(i.captured_at, i.source), i.source, i.captured_at,
           CASE WHEN i.captured_at < m.kickoff_utc THEN 'previo' ELSE 'posterior' END, i.player_name, i.player_id,
           CASE i.status_type WHEN 'Missing Fixture' THEN 'missing' WHEN 'Questionable' THEN 'doubtful'
                              ELSE COALESCE(i.status_type, 'missing') END,
           i.reason, i.expected_return
      FROM injuries i JOIN matches m USING (match_id)
     WHERE i.side IN ('home', 'away') AND i.player_id IS NOT NULL
       AND i.source IN (SELECT fuente FROM futbol.fuente)
       AND (p_desde IS NULL OR i.captured_at >= p_desde)
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT; entidad := 'baja_previa injuries'; filas := n; RETURN NEXT;

    -- once previo de FotMob (titulares y suplentes anunciados)
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, evento, fuente, recibido_en, pit, nombre, id_en_fuente,
                             titular, posicion_id, valor_mercado)
    SELECT j.match_id, 'once_previo', j.side, futbol.jugador_canonico('fotmob', j.jugador_id, j.nombre),
           futbol.evento_captura(j.capturado_en, 'fotmob'), 'fotmob', j.capturado_en,
           CASE WHEN j.capturado_en < m.kickoff_utc THEN 'previo' ELSE 'posterior' END, j.nombre, j.jugador_id,
           j.titular, j.posicion_id, j.valor_mercado
      FROM fotmob_jugador_previo j JOIN matches m USING (match_id)
     WHERE j.side IN ('home', 'away') AND (p_desde IS NULL OR j.capturado_en >= p_desde)
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT; entidad := 'once_previo fotmob'; filas := n; RETURN NEXT;

    -- once previsto de `lineups_previstas` (SofaScore/FotMob): la alineación y cada titular
    INSERT INTO futbol.dato (match_id, tipo, side, evento, fuente, recibido_en, pit, formacion, confirmada)
    SELECT l.match_id, 'alineacion_previa', l.side, futbol.evento_captura(l.captured_at, l.source), l.source, l.captured_at,
           CASE WHEN l.captured_at < m.kickoff_utc THEN 'previo' ELSE 'posterior' END, l.formation, l.confirmed
      FROM lineups_previstas l JOIN matches m USING (match_id)
     WHERE l.side IN ('home', 'away') AND l.source IN (SELECT fuente FROM futbol.fuente)
       AND (p_desde IS NULL OR l.captured_at >= p_desde)
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT; entidad := 'alineacion_previa'; filas := n; RETURN NEXT;

    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, evento, fuente, recibido_en, pit, nombre, id_en_fuente,
                             titular, posicion, camiseta)
    SELECT l.match_id, 'once_previo', l.side, futbol.jugador_canonico(l.source, (p.e ->> 'player_id')::bigint, p.e ->> 'name'),
           futbol.evento_captura(l.captured_at, l.source), l.source, l.captured_at,
           CASE WHEN l.captured_at < m.kickoff_utc THEN 'previo' ELSE 'posterior' END, p.e ->> 'name',
           (p.e ->> 'player_id')::bigint, true, p.e ->> 'pos', p.e ->> 'number'
      FROM lineups_previstas l JOIN matches m USING (match_id)
     CROSS JOIN LATERAL jsonb_array_elements(l.starters) AS p(e)
     WHERE l.side IN ('home', 'away') AND l.source IN (SELECT fuente FROM futbol.fuente)
       AND (p.e ->> 'player_id') ~ '^[0-9]+$' AND (p_desde IS NULL OR l.captured_at >= p_desde)
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT; entidad := 'once_previo previsto'; filas := n; RETURN NEXT;
END
$f$;

-- Capturas de bajas hechas antes del saque, con su antelación. El motor filtra `antelacion >= interval '60 minutes'`
-- y se queda, por fuente y jugador, con la captura más reciente.
CREATE OR REPLACE VIEW futbol.v_baja_a_t AS
SELECT d.*, m.kickoff_utc - d.recibido_en AS antelacion
  FROM futbol.dato d JOIN matches m USING (match_id)
 WHERE d.tipo = 'baja_previa' AND d.pit = 'previo';

COMMIT;
