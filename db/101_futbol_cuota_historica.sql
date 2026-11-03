-- 101: cuotas históricas de fútbol (1-nov-2026). Autorizado por el titular en el chat.
--
-- Guarda el archivo de BetsAPI (bet365, retroactivo) y el respaldo de API-Football (10 casas, recepción real) que
-- estaban solo como archivos en el VPS y en `~/backups`. NO van a `odds_snapshots`: esa tabla es inmutable y
-- varias lecturas (CLV, API, `daily.py`, `train.py`) no filtran por fuente, así que cuotas retroactivas cambiarían
-- resultados ya medidos (misma razón que `ingest/odds_history.py`). Esta tabla las guarda aparte y nada del
-- pipeline predecir → sellar → publicar la lee.
--
-- Solo lo necesario para medir y reentrenar (apertura, T-60, cierre/último y, en córners, la lectura del minuto
-- 65-70), no cada cambio de precio: los cambios intermedios siguen en el archivo original (`~/betsapi/data`).
-- Inmutable como el resto de las cuotas (deny_mutation). La clave única hace la carga idempotente.
--
-- `retroactiva`: BetsAPI se descargó después de los partidos; `precio_en` es cuándo cambió el precio en la casa, no
-- cuándo lo recibimos, y `recibido_en` queda vacío. Con API-Football `recibido_en` es la recepción real. Para
-- entrenamiento punto en el tiempo solo valen las filas con `retroactiva = false` o con `precio_en` anterior al saque.
BEGIN;

CREATE SCHEMA IF NOT EXISTS futbol;

CREATE TABLE IF NOT EXISTS futbol.cuota_historica (
    cuota_id         BIGSERIAL PRIMARY KEY,
    match_id         TEXT        NOT NULL REFERENCES matches(match_id),
    fuente           TEXT        NOT NULL CHECK (fuente IN ('betsapi', 'api_football')),
    casa             TEXT        NOT NULL,
    mercado          TEXT        NOT NULL,           -- como odds_snapshots (h2h, spreads, totals, corners…); _1t = 1.ª parte
    seleccion        TEXT        NOT NULL,
    linea            REAL,                           -- la de la propia selección; cuartos = media (9.75)
    linea_texto      TEXT,                           -- línea original de la fuente («9.5,10»)
    cuota            REAL        NOT NULL CHECK (cuota > 1),
    momento          TEXT        NOT NULL CHECK (momento IN ('apertura', 't60', 'cierre', 'ultimo', 'vivo_65_70')),
    precio_en        TIMESTAMPTZ,                    -- instante del precio según la casa o la fuente
    recibido_en      TIMESTAMPTZ,                    -- recepción por nosotros (solo API-Football)
    retroactiva      BOOLEAN     NOT NULL,
    minutos_al_saque INTEGER,                        -- negativo si es en vivo
    minuto_juego     SMALLINT,                       -- solo vivo_65_70
    marcador         TEXT,                           -- solo vivo_65_70 («0-1»)
    corners_vivo     TEXT,                           -- solo vivo_65_70, local-visita
    id_en_fuente     TEXT,
    cargado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un solo índice (la clave única empieza por el partido y sirve también para buscar por partido): la tabla pesa
-- unos 350 MB con 1,03 M filas.
CREATE UNIQUE INDEX IF NOT EXISTS cuota_historica_uq
    ON futbol.cuota_historica (match_id, mercado, momento, fuente, casa, seleccion, COALESCE(linea, -999));

DROP TRIGGER IF EXISTS trg_cuota_historica_immutable ON futbol.cuota_historica;
CREATE TRIGGER trg_cuota_historica_immutable BEFORE UPDATE OR DELETE ON futbol.cuota_historica
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

COMMENT ON TABLE futbol.cuota_historica IS
    'Cuotas históricas de BetsAPI (bet365, retroactivas) y API-Football (recepción real). Fuera de odds_snapshots a propósito (db/101).';
COMMIT;
