-- 079: puente entre el identificador de jugador de API-Football y el de FotMob (F4).
--
-- Se deduce de los partidos que tienen jugadores en las dos fuentes (mismo partido y lado). Un par solo se acepta
-- si cada identificador apunta casi siempre al otro (ver qf.ingest.puentes_jugadores). 1 a 1 en las dos direcciones,
-- por eso hay clave única en ambos lados. Los jugadores con pocos partidos entran con confianza 'baja'.
BEGIN;

CREATE TABLE IF NOT EXISTS puente_jugador (
    af_player_id     BIGINT PRIMARY KEY,
    fotmob_jugador_id BIGINT NOT NULL UNIQUE,
    partidos         INTEGER NOT NULL,
    cuota_af         REAL NOT NULL,       -- partidos del par / partidos de ese id de API-Football
    cuota_fotmob     REAL NOT NULL,
    confianza        TEXT NOT NULL CHECK (confianza IN ('alta', 'baja')),
    pasada_nombre    INTEGER NOT NULL,    -- 1 = nombre completo exacto, 2 = inicial + apellido
    calculado_en     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
