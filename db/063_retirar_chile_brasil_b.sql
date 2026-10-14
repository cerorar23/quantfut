-- Retiro del titular, 13-oct-2026. Borrado protegido autorizado por separado.
-- El mantenimiento respaldado elimina los datos existentes; esta migración
-- impide que una importación o semilla vieja vuelva a introducir las ligas.
BEGIN;
UPDATE leagues SET active=FALSE,model_enabled=FALSE,captura_completa=FALSE
 WHERE league_id IN ('cl.primera','br.serie_b');

CREATE TABLE IF NOT EXISTS retired_leagues (
 league_id TEXT PRIMARY KEY,
 retired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 reason TEXT NOT NULL
);
INSERT INTO retired_leagues(league_id,reason) VALUES
 ('cl.primera','Eliminación completa autorizada por el titular el 13-oct-2026'),
 ('br.serie_b','Eliminación completa autorizada por el titular el 13-oct-2026')
 ON CONFLICT(league_id) DO NOTHING;

CREATE OR REPLACE FUNCTION deny_retired_league() RETURNS TRIGGER AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM retired_leagues WHERE league_id=NEW.league_id) THEN
  RAISE EXCEPTION 'retired_league: %',NEW.league_id;
 END IF;
 RETURN NEW;
END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_leagues_retired ON leagues;
CREATE TRIGGER trg_leagues_retired BEFORE INSERT OR UPDATE ON leagues
 FOR EACH ROW EXECUTE FUNCTION deny_retired_league();
DROP TRIGGER IF EXISTS trg_matches_retired ON matches;
CREATE TRIGGER trg_matches_retired BEFORE INSERT OR UPDATE ON matches
 FOR EACH ROW EXECUTE FUNCTION deny_retired_league();

-- En una instalación nueva no hay historial protegido que requiera purga.
DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM matches WHERE league_id IN ('cl.primera','br.serie_b'))
 AND NOT EXISTS(SELECT 1 FROM historical_football_matches WHERE league_id IN ('cl.primera','br.serie_b')) THEN
  DELETE FROM standings WHERE league_id IN ('cl.primera','br.serie_b');
  DELETE FROM unresolved_names WHERE league_id IN ('cl.primera','br.serie_b');
  DELETE FROM team_aliases WHERE team_id IN
   (SELECT team_id FROM teams WHERE league_id IN ('cl.primera','br.serie_b'));
  DELETE FROM teams WHERE league_id IN ('cl.primera','br.serie_b');
  DELETE FROM leagues WHERE league_id IN ('cl.primera','br.serie_b');
 END IF;
END $$;
COMMIT;
