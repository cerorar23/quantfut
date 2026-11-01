-- 100: retira dos tablas de origen sin lectores (R3 del rediseño, 1-nov-2026).
--
--  * af_odds_snapshots: cuotas de API-Football; la fuente se retiró y los lectores se borraron en la fase 2c.
--  * sofascore_detalles: detalles de SofaScore de db/085 (212 filas), sustituidos por `futbol.dato`.
-- Ambas eran inmutables por trigger. Antes de borrarlas se exportaron comprimidas con recuento y sha256
-- (`~/backups/retiro_*_20261101.sql.gz`, copia local en Documents/respaldos_quantfut_20261101). Sin CASCADE: si algo
-- dependiera de ellas, la migración falla en vez de arrastrarlo.
BEGIN;
DROP TABLE IF EXISTS af_odds_snapshots;
DROP TABLE IF EXISTS sofascore_detalles;
COMMIT;
