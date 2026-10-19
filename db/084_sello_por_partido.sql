-- F7: sello tardío por partido (docs/superpowers/plans/2026-10-18-f7-sello-tardio.md).
-- Un lote de partido sella, minutos antes del saque, la predicción final y sus picks de valor. Convive con el lote diario
-- en la misma cadena (la cadena avanza por seq). Nada de lo ya sellado cambia: todo lo existente es 'diaria' / 'diario'.

ALTER TABLE predictions ADD COLUMN IF NOT EXISTS etapa TEXT NOT NULL DEFAULT 'diaria';
ALTER TABLE predictions DROP CONSTRAINT IF EXISTS predictions_etapa_chk;
ALTER TABLE predictions ADD CONSTRAINT predictions_etapa_chk CHECK (etapa IN ('diaria', 'final'));
-- Una sola predicción final por partido: el sello por partido es idempotente en la base, no solo en memoria.
CREATE UNIQUE INDEX IF NOT EXISTS uq_pred_final_por_partido ON predictions(match_id) WHERE etapa = 'final';

ALTER TABLE prediction_batches ADD COLUMN IF NOT EXISTS batch_kind TEXT NOT NULL DEFAULT 'diario';
ALTER TABLE prediction_batches ADD COLUMN IF NOT EXISTS match_id TEXT;
ALTER TABLE prediction_batches DROP CONSTRAINT IF EXISTS prediction_batches_kind_chk;
ALTER TABLE prediction_batches ADD CONSTRAINT prediction_batches_kind_chk CHECK (
    (batch_kind = 'diario' AND match_id IS NULL) OR (batch_kind = 'partido' AND match_id IS NOT NULL));
CREATE UNIQUE INDEX IF NOT EXISTS uq_batch_por_partido ON prediction_batches(match_id) WHERE batch_kind = 'partido';
