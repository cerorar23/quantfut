-- ============================================================================
-- 014: Bajas/lesiones vía API-Football (/injuries). Fuente decidida
--      2026-09-22: el proveedor ya contratado (plan Pro, usado para
--      calendario y alineaciones) cubre este endpoint sin coste incremental.
--      Ver harness/progreso.md para la decisión completa.
-- ============================================================================

CREATE TABLE IF NOT EXISTS injuries (
    match_id     TEXT NOT NULL REFERENCES matches(match_id),
    side         TEXT NOT NULL,              -- 'home' | 'away'
    player_id    BIGINT NOT NULL,
    player_name  TEXT NOT NULL,
    status_type  TEXT NOT NULL,              -- crudo del proveedor: 'Injured' | 'Missing Fixture' | 'Suspended'...
    reason       TEXT,                       -- descripción cruda del proveedor ('Knock', 'Red Card', ...)
    captured_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, side, player_id, captured_at)
);
CREATE INDEX IF NOT EXISTS idx_injuries_match ON injuries(match_id, captured_at DESC);

-- Registra CADA intento de captura, incluso sin bajas reportadas. Sin esto no
-- se puede distinguir "no se ha comprobado todavía" de "se comprobó y no hay
-- nadie fuera", y el ingest reintentaría el mismo partido en cada pasada para
-- siempre en vez de respetar la cadencia mínima entre comprobaciones.
CREATE TABLE IF NOT EXISTS injuries_capture_log (
    match_id     TEXT NOT NULL REFERENCES matches(match_id),
    captured_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    n_reported   INTEGER NOT NULL,
    PRIMARY KEY (match_id, captured_at)
);
CREATE INDEX IF NOT EXISTS idx_injuries_log_match ON injuries_capture_log(match_id, captured_at DESC);
