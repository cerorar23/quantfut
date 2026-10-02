-- ============================================================================
-- 036 - lineups_historicas también da la HISTORIA de la sombra
--
-- Decisión del usuario (2026-10-02), ampliando la de db/034. `availability()`
-- exige 3 XI anteriores de cada equipo; solo con `lineups` (en vivo desde el
-- 26-sep) las ligas europeas no tendrían historia hasta finales de octubre y
-- el brazo de XI de la sombra no mediría nada.
--   * La historia (XI de partidos ya JUGADOS antes del de hoy) puede salir de
--     esta tabla: ese XI era público antes del partido que se predice.
--   * El XI de HOY sigue saliendo solo de `lineups`, capturado antes del
--     inicio. La predicción diaria y lo sellado no la leen.
-- Solo cambia la documentación de la tabla; ningún dato.
-- ============================================================================
BEGIN;

COMMENT ON TABLE lineups_historicas IS
  'XI descargados después del partido. Entrenan/validan el challenger de XI '
  'y dan la historia de cada equipo a lineups.availability() (db/036). '
  'Nunca el XI del partido que se predice ni la predicción diaria.';

COMMIT;
