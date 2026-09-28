-- Id de API-Football de cada equipo, para bajar su escudo una sola vez.
--
-- Lo escribe `ingest/standings.py` junto a `display_name` y con la misma
-- regla: solo si el equipo se resolvió por coincidencia EXACTA. Es
-- presentación; ningún emparejamiento lo lee.
BEGIN;

ALTER TABLE teams ADD COLUMN IF NOT EXISTS af_team_id INTEGER;
COMMENT ON COLUMN teams.af_team_id IS
  'Id del equipo en API-Football (vía standings). Solo para el escudo de la web.';

COMMIT;
