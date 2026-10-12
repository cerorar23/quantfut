-- Secret key de cada proveedor de ofertas, editable desde /control/recompensas.
-- Se guarda CIFRADA (AES-256-GCM, src/qf/comercial/cifrado.py); la clave maestra
-- esta solo en el entorno del servidor (QF_SECRETS_KEY), nunca en la BD.
-- Solo escritura desde el panel: nunca se devuelve en pantalla ni en la API.
-- Las variables QF_BITLABS_SECRET / QF_TAPJOY_SECRET siguen valiendo de respaldo.
BEGIN;
ALTER TABLE reward_providers ADD COLUMN IF NOT EXISTS secret_enc TEXT NOT NULL DEFAULT '';
-- Version anterior de esta migracion guardaba texto plano: se elimina.
ALTER TABLE reward_providers DROP COLUMN IF EXISTS secret;
COMMIT;
