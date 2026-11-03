-- Bajas y once desde SofaScore (recolector Apify, actor rl1987), cargados por `qf.ingest.sofascore_alineaciones`.
-- Sustituye a /injuries y /fixtures/lineups de API-Football (plan gratuito desde el 22-oct-2026) y a las capturas
-- de FotMob (retiradas del cron el 25-oct). Todo aditivo: no cambia lo ya guardado.

-- Origen de cada baja y fecha estimada de regreso (SofaScore la da; API-Football no).
ALTER TABLE injuries ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'api_football';
ALTER TABLE injuries ADD COLUMN IF NOT EXISTS expected_return DATE;

-- Once previsto (confirmed = false, días u horas antes) y oficial (confirmed = true). `captured_at` es la
-- recepción real del recolector. Solo el oficial se copia a `lineups`, que es lo que lee `sello_tardio`
-- y significa «alineación confirmada»: mezclar previstos ahí falsearía esa señal.
CREATE TABLE IF NOT EXISTS lineups_previstas (
    match_id    TEXT NOT NULL REFERENCES matches(match_id),
    side        TEXT NOT NULL,              -- 'home' | 'away'
    formation   TEXT,
    starters    JSONB NOT NULL,             -- [{player_id, name, pos, number, src}]
    confirmed   BOOLEAN NOT NULL,
    source      TEXT NOT NULL DEFAULT 'sofascore',
    receipt_id  INTEGER,
    captured_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (match_id, side, captured_at)
);
CREATE INDEX IF NOT EXISTS idx_lineups_previstas_match ON lineups_previstas(match_id, captured_at DESC);
