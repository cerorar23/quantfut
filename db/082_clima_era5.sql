-- 082: clima histórico de cada partido desde ERA5 (Copernicus Climate Data Store), para F6.
--
-- Reanálisis ERA5 horario, rejilla de 0,25 grados, conjunto `reanalysis-era5-single-levels-timeseries`
-- (licencia Copernicus, CC-BY, uso comercial permitido con atribución: «Contains modified Copernicus Climate Change
-- Service information»). Es clima OBSERVADO (reanálisis), no el pronóstico que se habría tenido antes del partido:
-- sirve para medir el efecto del clima; el pronóstico previo se acumula desde el 18-oct en fotmob_previo.
-- Ventana del partido: la hora del saque y las dos siguientes (UTC). Precipitación: suma de las tres horas acumuladas
-- que terminan en la hora siguiente al saque, +1 h, +2 h y +3 h. Un dato incompleto deja la fila fuera.
BEGIN;

CREATE TABLE IF NOT EXISTS clima_era5_partido (
    match_id        TEXT PRIMARY KEY REFERENCES matches(match_id),
    stadium_id      BIGINT REFERENCES estadios(stadium_id),
    celda_lat       REAL NOT NULL,
    celda_lon       REAL NOT NULL,
    temperatura_c   REAL NOT NULL,
    humedad_pct     REAL NOT NULL,            -- de temperatura y punto de rocío (Magnus)
    viento_ms       REAL NOT NULL,
    precipitacion_mm REAL NOT NULL,           -- 0 es un dato real: no llovió
    nubosidad_pct   REAL NOT NULL,
    fuente          TEXT NOT NULL DEFAULT 'ERA5 timeseries (CDS)',
    calculado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
