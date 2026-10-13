-- Primera observación de xG de API-Football para el modelo. No se altera
-- el xG histórico ni se atribuye una fecha de disponibilidad retrospectiva.
BEGIN;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS xg_source TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS xg_api_checked_at TIMESTAMPTZ;
COMMENT ON COLUMN matches.xg_source IS
  'api_football: primera pareja válida, congelada en xg_recorded_at. NULL: histórico previo sin recepción original acreditada.';
COMMENT ON COLUMN matches.xg_api_checked_at IS
  'Última consulta de xG API-Football; limita reintentos de partidos ya terminados.';
COMMIT;
