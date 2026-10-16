CREATE TABLE IF NOT EXISTS mobile_update_settings (
    id integer PRIMARY KEY CHECK (id = 1),
    app_version_android text NOT NULL DEFAULT '',
    app_version_ios text NOT NULL DEFAULT '',
    min_build_android integer NOT NULL DEFAULT 0 CHECK (min_build_android >= 0),
    min_build_ios integer NOT NULL DEFAULT 0 CHECK (min_build_ios >= 0),
    force_update_app boolean NOT NULL DEFAULT false,
    app_link text NOT NULL DEFAULT '',
    ios_app_link text NOT NULL DEFAULT '',
    updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO mobile_update_settings (id) VALUES (1) ON CONFLICT DO NOTHING;
