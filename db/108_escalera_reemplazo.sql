-- ============================================================================
-- 108 - Reto escalera: reemplazo intradia tras 6 h por nulo o aplazado
--
-- 1. `escalera_pasos.kickoff_utc`: captura la hora original de inicio al elegir
--    el escalon de futbol para detectar aplazamientos o reprogramaciones > 6 h
--    incluso si fixtures sobrescribe `matches.kickoff_utc`.
-- 2. `escalera_pasos.reemplaza_paso_id`: enlace 1 a 1 con el escalon 'void'
--    al que sustituye (indice unico parcial: un nulo no se reemplaza dos veces).
-- 3. `prediction_batches`: admite `batch_kind = 'escalera'` con `match_id` =
--    `paso_id::text` para sellar al instante el escalon de reemplazo intradia
--    sin esperar al lote diario del dia siguiente ni romper la cadena.
-- ============================================================================
BEGIN;

ALTER TABLE escalera_pasos ADD COLUMN IF NOT EXISTS kickoff_utc TIMESTAMPTZ;
COMMENT ON COLUMN escalera_pasos.kickoff_utc IS
    'Hora de inicio del partido de futbol en el momento de elegir el escalon.';

ALTER TABLE escalera_pasos ADD COLUMN IF NOT EXISTS reemplaza_paso_id UUID
    REFERENCES escalera_pasos(paso_id);
COMMENT ON COLUMN escalera_pasos.reemplaza_paso_id IS
    'Escalon nulo sustituido por este reemplazo; NULL en escalones ordinarios.';
CREATE UNIQUE INDEX IF NOT EXISTS uq_escalera_reemplazo_paso
    ON escalera_pasos(reemplaza_paso_id)
    WHERE reemplaza_paso_id IS NOT NULL;

ALTER TABLE prediction_batches DROP CONSTRAINT IF EXISTS prediction_batches_kind_chk;
ALTER TABLE prediction_batches ADD CONSTRAINT prediction_batches_kind_chk CHECK (
    (batch_kind = 'diario' AND match_id IS NULL)
    OR (batch_kind = 'partido' AND match_id IS NOT NULL)
    OR (batch_kind = 'escalera' AND match_id IS NOT NULL));
CREATE UNIQUE INDEX IF NOT EXISTS uq_batch_escalera
    ON prediction_batches(match_id)
    WHERE batch_kind = 'escalera';

COMMIT;
