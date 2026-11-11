BEGIN;

CREATE TABLE IF NOT EXISTS web_site_settings (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    brand_name TEXT NOT NULL DEFAULT 'QuantFut',
    legal_name TEXT NOT NULL DEFAULT 'Saptain LTD',
    hero_badge TEXT NOT NULL DEFAULT 'SPORTS INTELLIGENCE',
    support_email TEXT NOT NULL DEFAULT 'admin@pronosticosdeportivos.pro',
    disclaimer_text TEXT NOT NULL DEFAULT 'QuantFut es un servicio de información estadística, no una casa de apuestas. Los pronósticos tienen fines exclusivamente informativos y de entretenimiento: una probabilidad estimada no garantiza un resultado.',
    maintenance_banner TEXT NOT NULL DEFAULT '',
    social_x TEXT NOT NULL DEFAULT '',
    social_instagram TEXT NOT NULL DEFAULT '',
    social_telegram TEXT NOT NULL DEFAULT '',
    social_facebook TEXT NOT NULL DEFAULT '',
    social_youtube TEXT NOT NULL DEFAULT '',
    social_tiktok TEXT NOT NULL DEFAULT '',
    default_robots TEXT NOT NULL DEFAULT 'index,follow',
    content_signal TEXT NOT NULL DEFAULT 'search=yes, ai-input=yes, ai-train=no',
    public_cache_seconds INTEGER NOT NULL DEFAULT 300 CHECK (public_cache_seconds >= 0 AND public_cache_seconds <= 86400),
    indexnow_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lang_selector_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lang_states JSONB NOT NULL DEFAULT '{"en": "off", "pt": "off"}'::jsonb,
    apimart_base_url TEXT NOT NULL DEFAULT 'https://api.apimart.ai/v1',
    apimart_model TEXT NOT NULL DEFAULT 'gpt-4o-mini',
    apimart_key_enc TEXT NOT NULL DEFAULT '',
    translation_target_langs JSONB NOT NULL DEFAULT '["en", "pt"]'::jsonb,
    updated_by TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO web_site_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS web_page_contents (
    page_key TEXT NOT NULL,
    lang TEXT NOT NULL CHECK (lang IN ('es', 'en', 'pt')),
    kind TEXT NOT NULL CHECK (kind IN ('spa', 'pagina', 'legal', 'tool', 'sport', 'ui')),
    route_path TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    h1 TEXT NOT NULL DEFAULT '',
    migas TEXT NOT NULL DEFAULT '',
    body_html TEXT NOT NULL DEFAULT '',
    revision_date TEXT NOT NULL DEFAULT '',
    is_auto_translated BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed BOOLEAN NOT NULL DEFAULT TRUE,
    source_sha256 TEXT NOT NULL DEFAULT '',
    translation_model TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (page_key, lang)
);

CREATE INDEX IF NOT EXISTS idx_web_page_contents_lang ON web_page_contents (lang, kind);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qf_readonly') THEN
        GRANT SELECT (
            id, brand_name, legal_name, hero_badge, support_email,
            disclaimer_text, maintenance_banner,
            social_x, social_instagram, social_telegram,
            social_facebook, social_youtube, social_tiktok,
            default_robots, content_signal, public_cache_seconds,
            indexnow_enabled, lang_selector_enabled, lang_states,
            apimart_base_url, apimart_model, translation_target_langs,
            updated_by, updated_at
        ) ON web_site_settings TO qf_readonly;
        GRANT SELECT ON web_page_contents TO qf_readonly;
    END IF;
END $$;

COMMIT;
