-- ============================================================================
-- 025 - Picks sin predicción del modelo (ligas "solo sharp", db/023)
--
-- LaLiga 2 y Serie B no se predicen a propósito: el modelo no conoce a sus
-- equipos y la predicción diaria se sella de forma pública e inmutable. El
-- criterio de picks (casa blanda contra el precio justo de Pinnacle) no
-- necesita la predicción, pero `picks.prediction_id` y `picks.model_prob`
-- eran obligatorios: sin esto esas ligas nunca podrían publicar un pick.
--
-- Vacío quiere decir "sin modelo", nunca "el modelo da 0%": por eso no se
-- rellena con 0. El pick se sigue sellando en la cadena igual que los demás.
--
-- `picks` es inmutable (trigger deny_mutation sobre UPDATE/DELETE de filas):
-- quitar un NOT NULL es DDL, no toca ninguna fila y no lo dispara.
-- ============================================================================
BEGIN;
ALTER TABLE picks ALTER COLUMN prediction_id DROP NOT NULL;
ALTER TABLE picks ALTER COLUMN model_prob DROP NOT NULL;
COMMENT ON COLUMN picks.prediction_id IS
  'NULL solo en ligas con leagues.model_enabled = FALSE (db/023): el pick '
  'sale del criterio de precio sin predicción del modelo.';
COMMIT;
