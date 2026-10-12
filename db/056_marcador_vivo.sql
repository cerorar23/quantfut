-- Marcador en juego, solo para mostrar en la app. No toca home_goals/away_goals
-- (los escribe results.py al cerrar el partido, con result_recorded_at) ni
-- matches.status, que usa el pipeline de picks.
BEGIN;
ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS live_home_goals SMALLINT,
    ADD COLUMN IF NOT EXISTS live_away_goals SMALLINT,
    ADD COLUMN IF NOT EXISTS live_minute     SMALLINT,
    ADD COLUMN IF NOT EXISTS live_status     TEXT,
    ADD COLUMN IF NOT EXISTS live_updated_at TIMESTAMPTZ;
COMMIT;
