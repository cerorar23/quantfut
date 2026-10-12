BEGIN;
CREATE TABLE IF NOT EXISTS mobile_features (
    section TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    message TEXT NOT NULL DEFAULT 'Modelo en entrenamiento',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO mobile_features(section, enabled, message) VALUES
 ('agenda', true, 'Agenda temporalmente no disponible'),
 ('alta_probabilidad', true, 'Modelo en entrenamiento'),
 ('escalera', true, 'Modelo en entrenamiento'),
 ('estadisticas', true, 'Estadísticas temporalmente no disponibles'),
 ('h2h', true, 'Datos del partido temporalmente no disponibles'),
 ('vip', true, 'Acceso VIP temporalmente no disponible'),
 ('nba', false, 'Modelo NBA en entrenamiento'),
 ('comunidad', false, 'Comunidad en preparación'),
 ('notificaciones', false, 'Notificaciones en preparación'),
 ('balance', false, 'Seguimiento en preparación'),
 ('medicion', false, 'Medición en preparación'),
 ('idiomas', false, 'Traducciones en preparación'),
 ('compras', false, 'Compras en preparación')
ON CONFLICT(section) DO NOTHING;
CREATE TABLE IF NOT EXISTS mobile_free_allocations (
    stream TEXT NOT NULL CHECK(stream IN ('alta_probabilidad', 'escalera')),
    batch_date DATE NOT NULL,
    pick_key TEXT NOT NULL,
    allocated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(stream, batch_date, pick_key)
);
CREATE TABLE IF NOT EXISTS mobile_allocation_batches (
    stream TEXT NOT NULL CHECK(stream IN ('alta_probabilidad', 'escalera')),
    batch_date DATE NOT NULL,
    candidate_count INTEGER NOT NULL CHECK(candidate_count >= 0),
    free_count INTEGER NOT NULL CHECK(free_count >= 0 AND free_count <= candidate_count),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(stream, batch_date)
);
COMMIT;
