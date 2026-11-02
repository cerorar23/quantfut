-- 0001: esquema `nba` de la base aislada `nba_datos` (rediseño NBA, plan técnico sección 2).
-- Siete tablas de datos: fuente/metrica (catálogos), entidad, captura, dato, cuota, evento, pronostico.
-- Todo hecho lleva `recibido_en` real; los originales viven como archivos con hash (captura.sha256).
CREATE SCHEMA IF NOT EXISTS nba;

CREATE TABLE nba.fuente (
    fuente      TEXT PRIMARY KEY,
    prioridad   SMALLINT NOT NULL UNIQUE,
    descripcion TEXT NOT NULL
);

-- Catálogo de métricas. `resolucion` decide cómo lo lee nba.dato_a_las:
--   prioridad  = un hecho único; gana la fuente de mejor prioridad (box score).
--   por_fuente = cambia con el tiempo y no se pisa entre fuentes (disponibilidad, proyecciones).
CREATE TABLE nba.metrica (
    metrica_id      SMALLINT PRIMARY KEY,
    nombre          TEXT NOT NULL UNIQUE,
    nivel           TEXT NOT NULL CHECK (nivel IN ('partido','equipo','jugador','arbitro','equipo_jugador')),
    unidad          TEXT,
    definicion      TEXT NOT NULL,
    nombres_nativos JSONB NOT NULL DEFAULT '{}',
    es_proyeccion   BOOLEAN NOT NULL DEFAULT false,
    resolucion      TEXT NOT NULL DEFAULT 'prioridad' CHECK (resolucion IN ('prioridad','por_fuente'))
);

-- Identidad: una fila canónica (canonica_id = entidad_id) y una por alias de fuente.
CREATE TABLE nba.entidad (
    entidad_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo           TEXT NOT NULL CHECK (tipo IN ('partido','equipo','jugador','arbitro','pabellon')),
    canonica_id    BIGINT NOT NULL REFERENCES nba.entidad (entidad_id),
    fuente         TEXT NOT NULL REFERENCES nba.fuente (fuente),
    id_en_fuente   TEXT NOT NULL,
    nombre         TEXT NOT NULL,
    fecha_juego_et DATE,          -- solo tipo 'partido': fecha en hora del Este
    temporada      TEXT,          -- solo tipo 'partido'
    atributos      JSONB NOT NULL DEFAULT '{}',
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fuente, id_en_fuente, tipo)
);
CREATE INDEX nba_entidad_canonica ON nba.entidad (canonica_id);

CREATE FUNCTION nba.completar_canonica() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.canonica_id IS NULL THEN NEW.canonica_id := NEW.entidad_id; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER entidad_canonica BEFORE INSERT ON nba.entidad
    FOR EACH ROW EXECUTE FUNCTION nba.completar_canonica();

-- Registro de cada petición; el original vive como archivo (ruta + sha256).
CREATE TABLE nba.captura (
    captura_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fuente        TEXT NOT NULL REFERENCES nba.fuente (fuente),
    objetivo      TEXT NOT NULL,
    fase          TEXT CHECK (fase IN ('pre','cierre','final','historico')),
    partido_id    BIGINT REFERENCES nba.entidad (entidad_id),
    solicitado_en TIMESTAMPTZ NOT NULL,
    recibido_en   TIMESTAMPTZ,
    http_status   INTEGER,
    ok            BOOLEAN NOT NULL,
    sha256        TEXT,
    bytes         INTEGER,
    ruta          TEXT,
    error         TEXT,
    creditos      NUMERIC(6,2) NOT NULL DEFAULT 0
);
CREATE INDEX nba_captura_partido ON nba.captura (partido_id, fase);

-- UNA tabla en formato largo para todo lo que no es cuota ni jugada.
-- periodo: 0 partido, 1-4 cuartos, 5+ prórrogas, 101/102 = 1.ª/2.ª mitad.
CREATE TABLE nba.dato (
    dato_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partido_id  BIGINT NOT NULL REFERENCES nba.entidad (entidad_id),
    entidad_id  BIGINT NOT NULL REFERENCES nba.entidad (entidad_id),
    periodo     SMALLINT NOT NULL DEFAULT 0,
    metrica_id  SMALLINT NOT NULL REFERENCES nba.metrica (metrica_id),
    valor       DOUBLE PRECISION,
    etiqueta    TEXT,
    fase        TEXT NOT NULL CHECK (fase IN ('pre','cierre','final')),
    fuente      TEXT NOT NULL REFERENCES nba.fuente (fuente),
    captura_id  BIGINT REFERENCES nba.captura (captura_id),
    recibido_en TIMESTAMPTZ NOT NULL,
    pit         TEXT NOT NULL DEFAULT 'posterior' CHECK (pit IN ('posterior','reconstruido','no_acreditado')),
    conflicto   BOOLEAN NOT NULL DEFAULT false,
    CHECK (valor IS NOT NULL OR etiqueta IS NOT NULL),
    UNIQUE NULLS NOT DISTINCT (partido_id, entidad_id, periodo, metrica_id, fase, fuente, captura_id, recibido_en)
);
CREATE INDEX nba_dato_lectura ON nba.dato (partido_id, metrica_id, recibido_en DESC);
CREATE INDEX nba_dato_entidad ON nba.dato (entidad_id, metrica_id, recibido_en DESC);

-- Un precio de un contrato en un instante. El margen NO se guarda (vista nba.cuota_margen).
CREATE TABLE nba.cuota (
    cuota_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partido_id  BIGINT NOT NULL REFERENCES nba.entidad (entidad_id),
    fuente      TEXT NOT NULL REFERENCES nba.fuente (fuente),
    casa        TEXT NOT NULL,
    mercado     TEXT NOT NULL,
    periodo     SMALLINT NOT NULL DEFAULT 0,
    entidad_id  BIGINT REFERENCES nba.entidad (entidad_id),
    linea       NUMERIC(6,2),
    lado        TEXT NOT NULL,
    cuota       NUMERIC(8,3) NOT NULL CHECK (cuota > 1),
    contrato_id TEXT NOT NULL,
    fase        TEXT NOT NULL CHECK (fase IN ('pre','cierre')),
    captura_id  BIGINT REFERENCES nba.captura (captura_id),
    recibido_en TIMESTAMPTZ NOT NULL,
    UNIQUE (fuente, casa, contrato_id, lado, recibido_en)
);
CREATE INDEX nba_cuota_partido ON nba.cuota (partido_id, fase, recibido_en DESC);

-- Jugada a jugada con coordenadas y quinteto en pista.
CREATE TABLE nba.evento (
    partido_id      BIGINT NOT NULL REFERENCES nba.entidad (entidad_id),
    fuente          TEXT NOT NULL REFERENCES nba.fuente (fuente),
    secuencia       INTEGER NOT NULL,
    periodo         SMALLINT NOT NULL,
    reloj_s         REAL NOT NULL,
    equipo_id       BIGINT REFERENCES nba.entidad (entidad_id),
    jugador_id      BIGINT REFERENCES nba.entidad (entidad_id),
    tipo            TEXT NOT NULL,
    subtipo         TEXT,
    x               REAL,
    y               REAL,
    acierto         BOOLEAN,
    puntos          SMALLINT,
    marcador_local  SMALLINT,
    marcador_visit  SMALLINT,
    en_pista_local  BIGINT[],
    en_pista_visit  BIGINT[],
    captura_id      BIGINT REFERENCES nba.captura (captura_id),
    recibido_en     TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (partido_id, fuente, secuencia)
);

-- Salida sellada del motor. La cadena de hashes se valida en el sellado (Sprint 5).
CREATE TABLE nba.pronostico (
    pronostico_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partido_id     BIGINT NOT NULL REFERENCES nba.entidad (entidad_id),
    mercado        TEXT NOT NULL,
    periodo        SMALLINT NOT NULL DEFAULT 0,
    entidad_id     BIGINT REFERENCES nba.entidad (entidad_id),
    version_modelo TEXT NOT NULL,
    version_datos  TEXT NOT NULL,
    objetivo_en    TIMESTAMPTZ NOT NULL,
    sellado_en     TIMESTAMPTZ NOT NULL,
    escenarios     JSONB NOT NULL,
    distribucion   JSONB NOT NULL,
    hash_previo    TEXT NOT NULL,
    hash           TEXT NOT NULL UNIQUE,
    UNIQUE NULLS NOT DISTINCT (partido_id, mercado, periodo, entidad_id, version_modelo, objetivo_en)
);
