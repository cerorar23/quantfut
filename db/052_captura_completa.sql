-- ============================================================================
-- 052 - `leagues.captura_completa`: separa lo que se PAGA a los proveedores de
-- si la liga está en el modelo (2026-10-11).
--
-- Hasta ahora `model_enabled` decidía las dos cosas: con el modelo encendido,
-- The Odds API pedía 3 mercados (3 créditos por llamada en vez de 1) y
-- API-Football alineaciones, bajas y estadísticas por jugador. Al activar el
-- modelo en las 12 ligas "solo sharp" eso se habría encendido solo, y
-- API-Football ya gasta ~5.400 de 7.500 peticiones al día. El modelo de goles
-- no necesita nada de eso: se entrena con resultados y cierres de Pinnacle.
--
-- FALSE: The Odds API solo `h2h`; sin alineaciones, bajas ni estadísticas por
-- jugador. Encenderla en una liga es una decisión de gasto aparte.
-- ============================================================================
BEGIN;

ALTER TABLE leagues ADD COLUMN IF NOT EXISTS captura_completa BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE leagues SET captura_completa = FALSE WHERE NOT model_enabled;

COMMENT ON COLUMN leagues.captura_completa IS
    'FALSE: The Odds API solo h2h y sin alineaciones/bajas/jugadores de API-Football (db/052). Independiente de model_enabled.';

COMMIT;
