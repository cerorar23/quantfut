-- ============================================================================
-- 119 - Parley v2: ámbitos que faltaban en `parley_v2_lotes`
-- (auditoría del 19-nov-2026, docs/parley_auditoria_20261119.md)
--
-- * `nba_dia`: el revisor NBA (parley_nba_revisor.ejecutar_multipartido) sella el lote de varios
--   partidos con este ámbito desde el 6-nov, pero el CHECK de db/098 solo admitía 'diario' y
--   'partido': cada intento acababa en CheckViolation y la NBA nunca entró en los objetivos.
-- * `sombra` y `sombra_nba`: el rediseño por probabilidad mínima (publish/parley_prob.py) corre
--   en sombra con su propia estrategia; se liquida igual que el v2 y NO se publica
--   (informe_publico_v2 filtra por estrategia).
--
-- Solo amplía la lista: ninguna fila existente cambia y los triggers de inmutabilidad siguen.
-- Vuelta atrás (solo si no hay filas con los ámbitos nuevos):
--   ALTER TABLE parley_v2_lotes DROP CONSTRAINT parley_v2_lotes_ambito_check;
--   ALTER TABLE parley_v2_lotes ADD CONSTRAINT parley_v2_lotes_ambito_check CHECK (ambito IN ('diario', 'partido'));
-- ============================================================================
BEGIN;

ALTER TABLE parley_v2_lotes DROP CONSTRAINT IF EXISTS parley_v2_lotes_ambito_check;
ALTER TABLE parley_v2_lotes ADD CONSTRAINT parley_v2_lotes_ambito_check
    CHECK (ambito IN ('diario', 'partido', 'nba_dia', 'sombra', 'sombra_nba'));

COMMIT;
