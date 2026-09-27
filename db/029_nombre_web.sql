-- Nombre de cada equipo para la web.
--
-- `canonical_name` sale de football-data ('Ath Madrid', "Nott'm Forest") y es
-- la identidad con la que se emparejan fuentes: no se toca. La web muestra
-- el nombre de API-Football, que escribe `ingest/standings.py` solo cuando el
-- equipo se resolvió por coincidencia EXACTA. Es presentación: ningún
-- emparejamiento, modelo ni pick lo lee.
BEGIN;

ALTER TABLE teams ADD COLUMN IF NOT EXISTS display_name TEXT;
COMMENT ON COLUMN teams.display_name IS
  'Nombre para la web (API-Football, vía standings). Solo presentación; la identidad es canonical_name + team_aliases.';

COMMIT;
