-- Resumen del pronóstico destacado redactado con IA (src/qf/api/analisis_futbol.py).
-- Una fila por (partido, mercado, huella de los datos entregados): si los datos cambian, se redacta de nuevo.
-- `textos` guarda el texto en los 6 idiomas; se escribe una sola vez y no se actualiza.
CREATE TABLE IF NOT EXISTS analisis_resumen (
    match_id   TEXT        NOT NULL,
    clave      TEXT        NOT NULL,
    datos_hash TEXT        NOT NULL,
    textos     JSONB       NOT NULL,
    modelo     TEXT        NOT NULL DEFAULT '',
    creado_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, clave, datos_hash)
);
