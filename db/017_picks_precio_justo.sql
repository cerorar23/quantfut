-- Datos del criterio "casa blanda contra precio sharp" que tiene que llevar
-- cada pick publicado. ADD COLUMN no choca con el trigger de inmutabilidad
-- (bloquea UPDATE y DELETE de filas, no el DDL). Los picks anteriores quedan
-- con NULL: se eligieron con el criterio del modelo y no tienen precio justo.
--
--   fair_prob    probabilidad sin margen de Pinnacle en el snapshot usado
--   min_price    cuota mínima a la que el pick sigue superando el umbral:
--                por debajo, el suscriptor no debe apostar
--   odds_source  'api_football' | 'the_odds_api'
--   odds_as_of   cuándo existía ese precio en la casa (hora del proveedor)

ALTER TABLE picks
    ADD COLUMN IF NOT EXISTS fair_prob   REAL,
    ADD COLUMN IF NOT EXISTS min_price   REAL,
    ADD COLUMN IF NOT EXISTS odds_source TEXT,
    ADD COLUMN IF NOT EXISTS odds_as_of  TIMESTAMPTZ;
