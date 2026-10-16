BEGIN;
UPDATE mobile_features SET enabled = TRUE, message = '', updated_at = now() WHERE section = 'compras';
SELECT section, enabled, message FROM mobile_features WHERE section = 'compras';
COMMIT;
