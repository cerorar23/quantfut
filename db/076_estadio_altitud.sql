-- 076: altitud de cada estadio (F6), de un modelo de elevación abierto.
--
-- La altitud es un dato estático del terreno, no una medición meteorológica: no depende de ninguna API de
-- clima. Fuente: OpenTopoData, conjunto `mapzen` (global, ~30 m, mezcla de SRTM y otros modelos abiertos).
-- Error esperado de decenas de metros (Azteca 2.281 m frente a ~2.240 m reales); suficiente para distinguir
-- Ciudad de México, Toluca o Pachuca del resto, que es lo que usa el bloque de sede.
BEGIN;

CREATE TABLE IF NOT EXISTS estadio_altitud (
    stadium_id   BIGINT PRIMARY KEY REFERENCES estadios(stadium_id),
    altitud_m    REAL NOT NULL,
    fuente       TEXT NOT NULL,
    recibido_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
