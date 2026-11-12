-- Catálogo de deportes y mercados (12-nov-2026): presentación gobernada desde /control, no datos sellados.
-- Por eso SIN triggers de inmutabilidad: cada cambio queda en admin_audit (db/043). Nunca se borran filas:
-- un deporte o una familia se apaga. La semilla la carga catalogo.ensure_seeded() desde el código, no este SQL.
-- Ver harness/tareas.md, «Especificación de la Fase 2», parte A.
BEGIN;

CREATE TABLE IF NOT EXISTS deportes (
    deporte_id TEXT PRIMARY KEY CHECK (deporte_id ~ '^[a-z][a-z0-9_]{1,23}$'),
    -- Se valida en Python contra catalogo.ADAPTADORES: vive en código, no en SQL.
    adaptador  TEXT,
    orden      SMALLINT NOT NULL,
    icono      TEXT NOT NULL DEFAULT 'generico',
    color      TEXT NOT NULL CHECK (color ~ '^#[0-9a-f]{6}$'),
    secciones  TEXT[] NOT NULL DEFAULT '{}' CHECK (secciones <@ ARRAY['high','ladder','parley']),
    nombre     JSONB NOT NULL,   -- es, en, pt, fr, it, de
    slug       JSONB NOT NULL,   -- es, en, pt
    estado_web TEXT NOT NULL DEFAULT 'off' CHECK (estado_web IN ('off','preview','on')),
    estado_app TEXT NOT NULL DEFAULT 'off' CHECK (estado_app IN ('off','preview','on')),
    updated_by TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Un deporte nuevo no puede encenderse hasta que exista su adaptador.
    CONSTRAINT deportes_sin_adaptador_apagado
        CHECK (adaptador IS NOT NULL OR (estado_web = 'off' AND estado_app = 'off'))
);

CREATE TABLE IF NOT EXISTS deporte_mercados (
    deporte_id  TEXT NOT NULL,
    familia_id  TEXT NOT NULL CHECK (familia_id ~ '^[a-z][a-z0-9_]{1,31}$'),
    orden       SMALLINT NOT NULL,
    nombre      JSONB NOT NULL,                      -- es, en, pt, fr, it, de
    subtitulo   JSONB NOT NULL DEFAULT '{}'::jsonb,
    visible_web BOOLEAN NOT NULL DEFAULT TRUE,
    visible_app BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by  TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (deporte_id, familia_id),
    FOREIGN KEY (deporte_id) REFERENCES deportes (deporte_id) ON DELETE RESTRICT
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
        -- Públicas: todo menos adaptador, updated_by y updated_at.
        GRANT SELECT (deporte_id, orden, icono, color, secciones, nombre, slug, estado_web, estado_app)
            ON deportes TO qf_readonly;
        GRANT SELECT (deporte_id, familia_id, orden, nombre, subtitulo, visible_web, visible_app)
            ON deporte_mercados TO qf_readonly;
    END IF;
END $$;

COMMIT;
