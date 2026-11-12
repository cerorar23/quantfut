-- Reglas de acceso «alta probabilidad» versionadas por fecha de lote (12-nov-2026).
-- Rango mostrado y fracción gratis dejan de ser constantes de código: cada regla vale
-- desde un día UTC FUTURO, así que ninguna alcanza un lote ya repartido ni un
-- pronóstico ya sellado. Solo se añaden filas (como admin_audit). Ver harness/tareas.md,
-- «Especificación de la Fase 1», parte A.
BEGIN;

CREATE TABLE IF NOT EXISTS acceso_reglas (
    regla_id      BIGSERIAL PRIMARY KEY,
    stream        TEXT NOT NULL CHECK (stream = 'alta_probabilidad'),
    vigente_desde DATE NOT NULL,
    prob_min      NUMERIC(3,2) NOT NULL,
    prob_max      NUMERIC(3,2) NOT NULL,
    free_fraction NUMERIC(3,2) NOT NULL CHECK (free_fraction >= 0 AND free_fraction <= 1),
    creado_por    TEXT NOT NULL,
    creado_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    nota          TEXT NOT NULL CHECK (btrim(nota) <> ''),
    -- publish/alta_prob_ext sella desde 0,62 y alta_prob hasta 0,95: fuera no hay filas que mostrar.
    CONSTRAINT acceso_reglas_rango CHECK (prob_min >= 0.62 AND prob_min < prob_max AND prob_max <= 0.95)
);
CREATE INDEX IF NOT EXISTS idx_acceso_reglas_vigencia
    ON acceso_reglas (stream, vigente_desde DESC, regla_id DESC);

-- Siembra ANTES del trigger (el trigger rechaza fechas pasadas): los valores de hoy.
INSERT INTO acceso_reglas (stream, vigente_desde, prob_min, prob_max, free_fraction, creado_por, nota)
SELECT 'alta_probabilidad', DATE '2000-01-01', 0.73, 0.95, 0.10, 'migracion',
       'Valores vigentes al crear la tabla (decisiones de 12 y 27-oct-2026)'
WHERE NOT EXISTS (SELECT 1 FROM acceso_reglas);

CREATE OR REPLACE FUNCTION acceso_reglas_solo_futuro() RETURNS trigger AS $$
BEGIN
    IF NEW.vigente_desde <= (now() AT TIME ZONE 'UTC')::date THEN
        RAISE EXCEPTION 'acceso_reglas: vigente_desde debe ser posterior al día UTC de hoy (%)',
            (now() AT TIME ZONE 'UTC')::date;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_acceso_reglas_inmutable ON acceso_reglas;
CREATE TRIGGER trg_acceso_reglas_inmutable BEFORE UPDATE OR DELETE ON acceso_reglas
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

DROP TRIGGER IF EXISTS trg_acceso_reglas_futuro ON acceso_reglas;
CREATE TRIGGER trg_acceso_reglas_futuro BEFORE INSERT ON acceso_reglas
    FOR EACH ROW EXECUTE FUNCTION acceso_reglas_solo_futuro();

-- Ajustes del cliente que no afectan a nada sellado (efecto inmediato).
CREATE TABLE IF NOT EXISTS cliente_ajustes (
    id          SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    dias_agenda SMALLINT NOT NULL DEFAULT 7 CHECK (dias_agenda BETWEEN 1 AND 14),
    updated_by  TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO cliente_ajustes (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

COMMIT;
