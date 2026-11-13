-- Definición de pantallas por bloques (Fase 4 del menú «Web y App», 13-nov-2026).
-- El orden, la visibilidad y los avisos de las pantallas `deporte` y `partido` dejan de vivir solo en el código de
-- los clientes. `pantalla_borradores` es editable (una fila por clave); `pantalla_publicaciones` solo admite
-- inserciones (como admin_audit y acceso_reglas): publicar = fila nueva con `version` siguiente; volver atrás =
-- publicar de nuevo el contenido de una versión anterior. Sin ninguna fila publicada, cada cliente usa su orden de hoy.
-- Ver harness/tareas.md, «Especificación de la Fase 4», parte C. La validación del contenido vive en
-- src/qf/comercial/pantallas.py (la base solo guarda la forma de la clave y que haya nota).
BEGIN;

CREATE TABLE IF NOT EXISTS pantalla_borradores (
    pantalla   TEXT NOT NULL CHECK (pantalla IN ('deporte', 'partido')),
    deporte    TEXT NOT NULL CHECK (deporte ~ '^(\*|[a-z][a-z0-9_]{1,23})$'),
    cliente    TEXT NOT NULL CHECK (cliente IN ('web', 'app')),
    bloques    JSONB NOT NULL CHECK (jsonb_typeof(bloques) = 'array'),
    updated_by TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (pantalla, deporte, cliente)
);

CREATE TABLE IF NOT EXISTS pantalla_publicaciones (
    pantalla      TEXT NOT NULL CHECK (pantalla IN ('deporte', 'partido')),
    deporte       TEXT NOT NULL CHECK (deporte ~ '^(\*|[a-z][a-z0-9_]{1,23})$'),
    cliente       TEXT NOT NULL CHECK (cliente IN ('web', 'app')),
    version       INTEGER NOT NULL CHECK (version >= 1),
    bloques       JSONB NOT NULL CHECK (jsonb_typeof(bloques) = 'array'),
    publicado_por TEXT NOT NULL,
    publicado_en  TIMESTAMPTZ NOT NULL DEFAULT now(),
    nota          TEXT NOT NULL CHECK (btrim(nota) <> ''),
    PRIMARY KEY (pantalla, deporte, cliente, version)
);

DROP TRIGGER IF EXISTS trg_pantalla_publicaciones_inmutable ON pantalla_publicaciones;
CREATE TRIGGER trg_pantalla_publicaciones_inmutable BEFORE UPDATE OR DELETE ON pantalla_publicaciones
    FOR EACH ROW EXECUTE FUNCTION deny_mutation();

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
        GRANT SELECT (pantalla, deporte, cliente, version, bloques, publicado_en)
            ON pantalla_publicaciones TO qf_readonly;
    END IF;
END $$;

COMMIT;
