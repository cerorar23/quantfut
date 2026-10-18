-- 077: equivalencia de árbitros entre API-Football ("A Taylor") y FotMob ("Anthony Taylor").
--
-- Se deduce de los partidos que tienen ambos nombres y solo se acepta un par si los dos lados coinciden de forma
-- casi exclusiva (ver qf.ingest.arbitros_equivalencia). No se modifica matches.referee: el motor de tarjetas
-- sigue leyendo lo mismo hasta que F5 decida cambiarlo. La vista da el nombre en formato API-Football cuando solo
-- hay árbitro de FotMob y su equivalencia está probada.
BEGIN;

CREATE TABLE IF NOT EXISTS arbitro_equivalencia (
    arbitro_af      TEXT NOT NULL,
    arbitro_fotmob  TEXT NOT NULL,
    partidos        INTEGER NOT NULL,
    cuota_af        REAL NOT NULL,        -- partidos del par / partidos de ese nombre API-Football
    cuota_fotmob    REAL NOT NULL,
    regla_nombre    BOOLEAN NOT NULL,     -- ¿encaja inicial + apellido?
    calculada_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (arbitro_af, arbitro_fotmob)
);

CREATE OR REPLACE VIEW v_arbitro_unificado AS
SELECT m.match_id,
       COALESCE(m.referee, e.arbitro_af) AS arbitro,
       CASE WHEN m.referee IS NOT NULL THEN 'api_football'
            WHEN e.arbitro_af IS NOT NULL THEN 'fotmob_equivalente'
            ELSE NULL END AS origen
FROM matches m
LEFT JOIN arbitro_equivalencia e
       ON e.arbitro_fotmob = m.referee_fotmob AND e.regla_nombre
WHERE m.referee IS NOT NULL OR m.referee_fotmob IS NOT NULL;

COMMIT;
