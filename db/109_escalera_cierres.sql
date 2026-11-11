BEGIN;

CREATE TABLE IF NOT EXISTS escalera_cierres (
    reto_id   BIGINT PRIMARY KEY REFERENCES escalera_retos(reto_id),
    motivo    TEXT NOT NULL,
    closed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_escalera_cierres_immutable ON escalera_cierres;
CREATE TRIGGER trg_escalera_cierres_immutable
    BEFORE UPDATE OR DELETE ON escalera_cierres
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
        GRANT SELECT ON escalera_cierres TO qf_readonly;
    END IF;
END $$;

INSERT INTO escalera_cierres (reto_id, motivo)
SELECT 21, 'Cierre manual por cambio a regla vigente (cuota 1.25-2.10)'
WHERE EXISTS (SELECT 1 FROM escalera_retos WHERE reto_id = 21)
ON CONFLICT (reto_id) DO NOTHING;

COMMIT;
