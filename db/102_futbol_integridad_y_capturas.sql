-- Auditoría 3-nov: copia intradía con reloj original y cuarentena de conteos incoherentes.
-- No modifica originales, predicciones, picks ni cuotas. Se aplica antes del nuevo worker.
BEGIN;

CREATE TABLE IF NOT EXISTS futbol.cuarentena (
    tabla TEXT NOT NULL, clave TEXT NOT NULL, motivo TEXT NOT NULL,
    original JSONB NOT NULL, registrado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    huella TEXT GENERATED ALWAYS AS (md5(original::text)) STORED,
    PRIMARY KEY (tabla, clave, motivo, huella)
);

CREATE OR REPLACE FUNCTION futbol.validar_tiros() RETURNS trigger LANGUAGE plpgsql AS $f$
DECLARE lado TEXT; total INTEGER; puerta INTEGER; j JSONB;
BEGIN
    j := to_jsonb(NEW);
    IF TG_TABLE_NAME = 'matches' THEN
        FOREACH lado IN ARRAY ARRAY['home', 'away'] LOOP
            total := (j->>(lado||'_shots'))::integer;
            puerta := (j->>(lado||'_shots_target'))::integer;
            IF total < 0 OR puerta < 0 OR puerta > total THEN
                INSERT INTO futbol.cuarentena(tabla,clave,motivo,original)
                VALUES(TG_TABLE_NAME,NEW.match_id,lado||': tiros incoherentes',j) ON CONFLICT DO NOTHING;
                IF lado='home' THEN NEW.home_shots:=NULL; NEW.home_shots_target:=NULL;
                ELSE NEW.away_shots:=NULL; NEW.away_shots_target:=NULL; END IF;
            END IF;
        END LOOP;
    ELSE
        IF NEW.tiros_totales < 0 OR NEW.tiros_puerta < 0 OR NEW.tiros_puerta > NEW.tiros_totales THEN
            INSERT INTO futbol.cuarentena(tabla,clave,motivo,original)
            VALUES('futbol.dato', concat_ws('|',NEW.match_id,NEW.tipo,NEW.side,NEW.jugador_id,NEW.evento),
                   'tiros incoherentes',j) ON CONFLICT DO NOTHING;
            NEW.tiros_totales:=NULL; NEW.tiros_puerta:=NULL;
        END IF;
    END IF;
    RETURN NEW;
END $f$;
CREATE TRIGGER futbol_validar_tiros BEFORE INSERT OR UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION futbol.validar_tiros();
CREATE TRIGGER futbol_validar_tiros BEFORE INSERT OR UPDATE ON futbol.dato
    FOR EACH ROW EXECUTE FUNCTION futbol.validar_tiros();
-- Dispara la misma cuarentena en los cuatro casos ya existentes; no se inventa un valor correcto.
UPDATE matches SET home_shots=home_shots WHERE home_shots_target>home_shots OR away_shots_target>away_shots;
UPDATE futbol.dato SET tiros_totales=tiros_totales WHERE tiros_puerta>tiros_totales;

CREATE OR REPLACE FUNCTION futbol.copiar_captura_previa(
    p_match TEXT, p_tipo TEXT, p_fuente TEXT, p_hora TIMESTAMPTZ,
    p_side TEXT, p_id BIGINT, p JSONB) RETURNS VOID LANGUAGE plpgsql AS $f$
DECLARE ko TIMESTAMPTZ; canon BIGINT; ev INTEGER;
BEGIN
    IF p_side NOT IN ('home','away') OR p_hora IS NULL OR p_id IS NULL THEN RETURN; END IF;
    SELECT kickoff_utc INTO STRICT ko FROM matches WHERE match_id=p_match;
    canon := CASE WHEN p_id=0 THEN 0 ELSE futbol.jugador_canonico(p_fuente,p_id,p->>'nombre') END;
    ev := futbol.evento_captura(p_hora,p_fuente);
    LOOP
    IF EXISTS(SELECT FROM futbol.dato WHERE match_id=p_match AND tipo=p_tipo AND side=p_side
        AND jugador_id=canon AND fuente=p_fuente AND recibido_en=p_hora) THEN RETURN; END IF;
    INSERT INTO futbol.dato(match_id,tipo,side,jugador_id,evento,fuente,recibido_en,pit,
        id_en_fuente,nombre,estado,descripcion,regreso_fecha,titular,posicion_id,valor_mercado,
        formacion,confirmada,posicion,camiseta)
    VALUES(p_match,p_tipo,p_side,canon,ev,p_fuente,p_hora,
        CASE WHEN p_hora<ko THEN 'previo' ELSE 'posterior' END,
        nullif(p_id,0),p->>'nombre',CASE p->>'estado' WHEN 'Missing Fixture' THEN 'missing'
            WHEN 'Questionable' THEN 'doubtful' ELSE p->>'estado' END,p->>'descripcion',(p->>'regreso_fecha')::timestamptz,
        (p->>'titular')::boolean,(p->>'posicion_id')::integer,(p->>'valor_mercado')::bigint,
        p->>'formacion',(p->>'confirmada')::boolean,p->>'posicion',p->>'camiseta')
    ON CONFLICT(match_id,tipo,side,jugador_id,evento) DO NOTHING;
    IF FOUND THEN RETURN; END IF;
    -- Dos capturas de la misma fuente en el mismo minuto siguen siendo dos observaciones.
    ev := ev+10;
    END LOOP;
END $f$;

CREATE OR REPLACE FUNCTION futbol.propagar_previo() RETURNS trigger LANGUAGE plpgsql AS $f$
DECLARE j JSONB := to_jsonb(NEW); p JSONB; jugador JSONB; at TIMESTAMPTZ; fuente TEXT;
BEGIN
    IF TG_TABLE_NAME='injuries' THEN
        p:=jsonb_build_object('nombre',NEW.player_name,'estado',NEW.status_type,'descripcion',NEW.reason,
                             'regreso_fecha',NEW.expected_return);
        PERFORM futbol.copiar_captura_previa(NEW.match_id,'baja_previa',NEW.source,NEW.captured_at,NEW.side,NEW.player_id,p);
    ELSIF TG_TABLE_NAME='fotmob_baja_previa' THEN
        p:=j||jsonb_build_object('estado',j->>'tipo','descripcion',j->>'regreso_texto');
        PERFORM futbol.copiar_captura_previa(NEW.match_id,'baja_previa','fotmob',NEW.capturado_en,NEW.side,NEW.jugador_id,p);
    ELSIF TG_TABLE_NAME='fotmob_jugador_previo' THEN
        PERFORM futbol.copiar_captura_previa(NEW.match_id,'once_previo','fotmob',NEW.capturado_en,NEW.side,NEW.jugador_id,j);
    ELSIF TG_TABLE_NAME='lineups_previstas' THEN
        fuente:=NEW.source; at:=NEW.captured_at;
        p:=jsonb_build_object('formacion',NEW.formation,'confirmada',NEW.confirmed);
        PERFORM futbol.copiar_captura_previa(NEW.match_id,'alineacion_previa',fuente,at,NEW.side,0,p);
        FOR jugador IN SELECT value FROM jsonb_array_elements(NEW.starters) LOOP
            IF (jugador->>'player_id') ~ '^[0-9]+$' THEN
                p:=jsonb_build_object('nombre',jugador->>'name','titular',true,'posicion',jugador->>'pos',
                                     'camiseta',jugador->>'number');
                PERFORM futbol.copiar_captura_previa(NEW.match_id,'once_previo',fuente,at,NEW.side,
                                                   (jugador->>'player_id')::bigint,p);
            END IF;
        END LOOP;
    END IF;
    RETURN NEW;
END $f$;
CREATE TRIGGER futbol_propagar_previo AFTER INSERT ON injuries FOR EACH ROW EXECUTE FUNCTION futbol.propagar_previo();
CREATE TRIGGER futbol_propagar_previo AFTER INSERT ON fotmob_baja_previa FOR EACH ROW EXECUTE FUNCTION futbol.propagar_previo();
CREATE TRIGGER futbol_propagar_previo AFTER INSERT ON fotmob_jugador_previo FOR EACH ROW EXECUTE FUNCTION futbol.propagar_previo();
CREATE TRIGGER futbol_propagar_previo AFTER INSERT ON lineups_previstas FOR EACH ROW EXECUTE FUNCTION futbol.propagar_previo();
-- Recupera el atraso medido; se conserva la recepción original y no se generan capturas nuevas.
SELECT * FROM futbol.cargar_previo(now()-interval '2 days');

ALTER TABLE futbol.regla_sancion DROP CONSTRAINT regla_sancion_tipo_check;
ALTER TABLE futbol.regla_sancion ADD CONSTRAINT regla_sancion_tipo_check
    CHECK(tipo IN ('fijo','por_jornada','sin_acumulacion','pendiente'));
UPDATE futbol.regla_sancion SET tipo='pendiente', amarillas=NULL,
    detalle='La ausencia de acumulación inferida no es válida: FMF 2025/26 art.15 sí contempla acumulación. Falta verificar vigencia y reinicios por fase.',
    verificada=false WHERE liga='mx.liga_mx' AND fuente='observado' AND NOT verificada;
CREATE OR REPLACE VIEW futbol.reglas_sancion_verificadas AS
    SELECT * FROM futbol.regla_sancion WHERE verificada AND fuente='reglamento' AND desde<>'0000';

COMMIT;
