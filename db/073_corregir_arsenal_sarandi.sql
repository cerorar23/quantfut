-- 073: Arsenal (Inglaterra) figuraba como Arsenal de Sarandí en 33 partidos de copa europea.
--
-- Causa: filas históricas cargadas antes de que uefa_cups.py resolviera cada nombre con la liga
-- doméstica de su país: el alias ('Arsenal','fbref') -> 28402 (Arsenal de Sarandí, correcto para
-- Argentina) se aplicaba sin liga y atrapaba al Arsenal inglés. Hoy el cargador ya resuelve bien
-- (los partidos de copa de Arsenal desde 2025-09 usan team_id 3), así que el alias NO se toca.
--
-- Qué hace (una transacción, con auditoría para revertir):
--   1. Registra cada cambio en correcciones_identidad (tabla nueva, solo se inserta).
--   2. matches: 28402 -> 3 en eu.ucl/eu.uel (33 partidos, lado local o visitante).
-- Nota de aplicación (18-oct-2026): la primera versión también intentaba añadir ('Arsenal','fbref')->3;
-- team_aliases es único por (alias, fuente), así que no insertó nada. Esa versión dejó una fila de
-- auditoría de alias falsa, ya borrada; este archivo es el que debe correr una instalación nueva.
-- Reversión: ver el final del archivo.
BEGIN;

CREATE TABLE IF NOT EXISTS correcciones_identidad (
    id          BIGSERIAL PRIMARY KEY,
    aplicada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    migracion   TEXT NOT NULL,
    tabla       TEXT NOT NULL,
    clave       TEXT NOT NULL,
    campo       TEXT NOT NULL,
    antes       TEXT,
    despues     TEXT,
    motivo      TEXT NOT NULL
);

DO $$
DECLARE
    n_local int; n_visita int;
BEGIN
    IF EXISTS (SELECT 1 FROM correcciones_identidad WHERE migracion = '073') THEN
        RAISE NOTICE '073 ya aplicada: no se hace nada';
        RETURN;
    END IF;

    INSERT INTO correcciones_identidad (migracion, tabla, clave, campo, antes, despues, motivo)
    SELECT '073', 'matches', match_id, 'home_team_id', '28402', '3',
           'Arsenal (ENG) registrado como Arsenal de Sarandí por el alias fbref'
    FROM matches WHERE league_id IN ('eu.ucl', 'eu.uel') AND home_team_id = 28402;
    INSERT INTO correcciones_identidad (migracion, tabla, clave, campo, antes, despues, motivo)
    SELECT '073', 'matches', match_id, 'away_team_id', '28402', '3',
           'Arsenal (ENG) registrado como Arsenal de Sarandí por el alias fbref'
    FROM matches WHERE league_id IN ('eu.ucl', 'eu.uel') AND away_team_id = 28402;

    UPDATE matches SET home_team_id = 3
    WHERE league_id IN ('eu.ucl', 'eu.uel') AND home_team_id = 28402;
    GET DIAGNOSTICS n_local = ROW_COUNT;
    UPDATE matches SET away_team_id = 3
    WHERE league_id IN ('eu.ucl', 'eu.uel') AND away_team_id = 28402;
    GET DIAGNOSTICS n_visita = ROW_COUNT;

    -- 0 en una base vacía (CI, instalación nueva); 33 en producción. Cualquier otra cifra es una sorpresa.
    IF n_local + n_visita NOT IN (0, 33) THEN
        RAISE EXCEPTION 'se esperaban 33 partidos y hay % (local %, visita %)',
            n_local + n_visita, n_local, n_visita;
    END IF;
    IF EXISTS (SELECT 1 FROM matches WHERE home_team_id = away_team_id) THEN
        RAISE EXCEPTION 'un partido quedó con el mismo equipo en los dos lados';
    END IF;
END $$;

COMMIT;

-- Reversión (solo si hace falta):
--   UPDATE matches m SET home_team_id = 28402 FROM correcciones_identidad c
--    WHERE c.migracion='073' AND c.tabla='matches' AND c.campo='home_team_id' AND c.clave=m.match_id;
--   UPDATE matches m SET away_team_id = 28402 FROM correcciones_identidad c
--    WHERE c.migracion='073' AND c.tabla='matches' AND c.campo='away_team_id' AND c.clave=m.match_id;
--   DELETE FROM correcciones_identidad WHERE migracion='073';
