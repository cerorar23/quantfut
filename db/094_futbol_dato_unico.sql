-- 094: UNA sola tabla de fútbol para el motor: `futbol.dato`.
--
-- Idea del titular (1-nov-2026): todo lo que capturen las APIs, los servicios y los scrapers de fútbol
-- (FotMob, scraper de SofaScore, SportsAPIPro, ERA5, OpenTopoData, API-Football en su historia...) se junta en
-- UNA tabla con nombres de campo unificados, y esa tabla es la única que alimenta al motor. Cada fuente tiene un
-- adaptador que traduce sus nombres y formatos a los de esta tabla.
--
-- Forma: una fila por hecho (`tipo`) con columnas ESPARCIDAS y tipadas: cada tipo usa las suyas y deja el resto
-- NULL (en Postgres un NULL solo cuesta un bit del mapa de nulos, así que la tabla es compacta). Los nombres de
-- columna son los del motor; dos tipos que miden lo mismo comparten columna (`tiros_fuera` vale para un
-- jugador y para un equipo).
--
--   tipo         una fila por...                       clave dentro del partido
--   jugador      jugador y partido                     side + jugador_id
--   equipo       lado y partido (estadística)          side
--   baja         jugador ausente                       side + jugador_id
--   alineacion   lado                                  side
--   entrenador   lado                                  side
--   contexto     partido (árbitro, ronda, asistencia)  —
--   tiro         tiro                                  evento = id del tiro
--   incidencia   tarjeta, cambio, gol...               evento = orden en la fuente
--   clima        partido                               —
--   estadio      partido (estadio y altitud)           —
--
-- Sin repetidos: la clave primaria (partido, tipo, lado, jugador, evento) admite UNA fila por hecho. Una fuente
-- por tipo y partido (la de mejor prioridad en `futbol.prioridad_entidad`): cargar una mejor reemplaza las filas
-- de la peor en la misma transacción y una peor nunca pisa a una mejor. Cada fila lleva `fuente`,
-- `recibido_en` y `pit` (posterior / reconstruido / no_acreditado).
--
-- Fuera de esta tabla, a propósito: `matches` (el registro del partido y su resultado, 36 tablas lo referencian)
-- y `odds_snapshots` (cuotas de PropLine, The Odds API y football-data.org: ya es UNA tabla con columna de fuente,
-- pero es inmutable por trigger y de ella depende la cadena de hashes de los picks; moverla exigiría quitar esas
-- garantías, algo que solo se hace con confirmación explícita del titular).
-- Lo conocido ANTES del partido (once previsto, bajas previas) entra en una segunda fase con su propio `pit`.
--
-- Idempotente: se puede aplicar sobre la base de producción, donde ya existían las tablas por tipo de las
-- migraciones 085-090 de la rama de trabajo (las absorbe db/095).
BEGIN;

CREATE SCHEMA IF NOT EXISTS futbol;

CREATE TABLE IF NOT EXISTS futbol.fuente (
    fuente      TEXT PRIMARY KEY,
    prioridad   SMALLINT NOT NULL UNIQUE,
    descripcion TEXT NOT NULL
);
INSERT INTO futbol.fuente (fuente, prioridad, descripcion) VALUES
    ('fotmob',        1, 'FotMob: captura diaria y archivo; fuente de los motores'),
    ('sofascore',     2, 'Scraper/archivo de SofaScore (dos pasadas al día); aporta lo que FotMob no tiene'),
    ('api_football',  3, 'API-Football: solo historia (sin captura nueva desde el 25-oct-2026)'),
    ('sportsapipro',  4, 'SportsAPIPro: once previsto y bajas previas con ids de SofaScore'),
    ('pitchapi',      5, 'PitchAPI: retirada'),
    ('football_data', 6, 'football-data.org: resultados y cuotas históricas'),
    ('era5',          7, 'Copernicus ERA5: clima por celda y hora'),
    ('opentopodata',  8, 'OpenTopoData: altitud de estadios'),
    ('the_odds_api',  9, 'The Odds API: cuotas en vivo e históricas'),
    ('propline',     10, 'PropLine: cuotas horarias compartidas')
ON CONFLICT (fuente) DO NOTHING;

-- Prioridad por tipo de dato (no es lo mismo quién gana en jugadores que en clima).
CREATE TABLE IF NOT EXISTS futbol.prioridad_entidad (
    entidad   TEXT NOT NULL,                 -- un `tipo` de futbol.dato
    fuente    TEXT NOT NULL REFERENCES futbol.fuente(fuente),
    prioridad SMALLINT NOT NULL,
    PRIMARY KEY (entidad, fuente)
);
INSERT INTO futbol.prioridad_entidad (entidad, fuente, prioridad) VALUES
    ('jugador','fotmob',1), ('jugador','sofascore',2), ('jugador','api_football',3),
    ('baja','fotmob',1),    ('baja','sofascore',2),    ('baja','api_football',3),
    ('alineacion','fotmob',1), ('alineacion','sofascore',2), ('alineacion','api_football',3),
    ('entrenador','fotmob',1), ('entrenador','sofascore',2),
    ('contexto','sofascore',1), ('contexto','fotmob',2),
    ('tiro','sofascore',1), ('incidencia','sofascore',1), ('equipo','sofascore',1),
    ('clima','era5',1), ('clima','fotmob',2),
    ('estadio','opentopodata',1)
ON CONFLICT (entidad, fuente) DO NOTHING;

-- Enlace de cada partido de una fuente con nuestro partido (un id de fuente apunta a UN solo partido).
CREATE TABLE IF NOT EXISTS futbol.partido_fuente (
    match_id        TEXT NOT NULL REFERENCES matches(match_id),
    fuente          TEXT NOT NULL REFERENCES futbol.fuente(fuente),
    source_match_id TEXT NOT NULL,
    raw_sha256      TEXT,
    recibido_en     TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (match_id, fuente),
    UNIQUE (fuente, source_match_id)
);

-- Índice de los originales (los bytes viven como archivos, no aquí).
CREATE TABLE IF NOT EXISTS futbol.original (
    fuente          TEXT NOT NULL REFERENCES futbol.fuente(fuente),
    source_match_id TEXT NOT NULL,
    bloque          TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    bytes           INTEGER,
    recibido_en     TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (fuente, source_match_id, bloque)
);

-- Identidad única de jugador: id canónico = id de SofaScore (negativo y determinista si no hay pareja).
CREATE TABLE IF NOT EXISTS futbol.jugador (
    jugador_id BIGINT PRIMARY KEY,
    nombre     TEXT NOT NULL,
    creado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS futbol.jugador_fuente_id (
    fuente       TEXT NOT NULL REFERENCES futbol.fuente(fuente),
    id_en_fuente BIGINT NOT NULL,
    jugador_id   BIGINT NOT NULL REFERENCES futbol.jugador(jugador_id),
    evidencia    TEXT NOT NULL CHECK (evidencia IN
                 ('id_canonico','nombre_en_partido','puente_api_football','solo_en_fuente','manual')),
    partidos     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (fuente, id_en_fuente)
);
CREATE INDEX IF NOT EXISTS futbol_jugador_fuente_id_jugador ON futbol.jugador_fuente_id (jugador_id);

-- ── LA tabla ─────────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS futbol.dato (
    match_id    TEXT NOT NULL REFERENCES matches(match_id),
    tipo        TEXT NOT NULL CHECK (tipo IN ('jugador','equipo','baja','alineacion','entrenador','contexto',
                                              'tiro','incidencia','clima','estadio')),
    side        TEXT NOT NULL DEFAULT '' CHECK (side IN ('', 'home', 'away')),
    jugador_id  BIGINT NOT NULL DEFAULT 0,        -- id canónico; 0 = el tipo no es de un jugador
    evento      INTEGER NOT NULL DEFAULT 0,       -- id del tiro / orden de la incidencia; 0 si no aplica
    fuente      TEXT NOT NULL REFERENCES futbol.fuente(fuente),
    recibido_en TIMESTAMPTZ NOT NULL,
    pit         TEXT NOT NULL DEFAULT 'posterior' CHECK (pit IN ('posterior','reconstruido','no_acreditado')),
    -- quién es
    nombre          TEXT,
    id_en_fuente    BIGINT,                       -- id del jugador/entrenador en la fuente dueña
    jugador2_id     BIGINT,                       -- asistente, o quien entra en un cambio
    jugador2        TEXT,
    posicion        TEXT,
    posicion_id     INTEGER,                      -- id numérico de FotMob
    camiseta        TEXT,
    titular         BOOLEAN,
    edad            SMALLINT,
    valor_mercado   BIGINT,
    -- rendimiento (jugador y equipo comparten nombre cuando miden lo mismo)
    minutos         REAL,
    nota            REAL,
    goles           SMALLINT,
    asistencias     SMALLINT,
    xa              REAL,
    xg              REAL,
    xgot            REAL,
    tiros_puerta    SMALLINT,
    tiros_fuera     SMALLINT,
    tiros_bloq      SMALLINT,
    tiros_dentro_area SMALLINT,
    tiros_fuera_area  SMALLINT,
    grandes_ocasiones_creadas  SMALLINT,
    grandes_ocasiones_falladas SMALLINT,
    pases           SMALLINT,
    pases_acertados SMALLINT,
    balones_largos  SMALLINT,
    balones_largos_acertados SMALLINT,
    centros         SMALLINT,
    centros_acertados SMALLINT,
    duelos_ganados  SMALLINT,
    duelos_perdidos SMALLINT,
    aereos_ganados  SMALLINT,
    aereos_perdidos SMALLINT,
    entradas        SMALLINT,
    entradas_ganadas SMALLINT,
    intercepciones  SMALLINT,
    despejes        SMALLINT,
    recuperaciones  SMALLINT,
    perdidas        SMALLINT,
    faltas          SMALLINT,
    faltas_recibidas SMALLINT,
    fuera_juego     SMALLINT,
    toques          SMALLINT,
    paradas         SMALLINT,
    goles_evitados  REAL,
    tiros_libres    SMALLINT,
    toques_area_rival SMALLINT,
    entradas_ultimo_tercio SMALLINT,
    saques_banda    SMALLINT,
    saques_puerta   SMALLINT,
    posesion        REAL,
    km              REAL,
    sprints         SMALLINT,
    vel_max         REAL,
    -- baja
    estado          TEXT,                         -- missing | doubtful
    motivo_codigo   INTEGER,
    descripcion     TEXT,
    regreso_texto   TEXT,
    regreso_fecha   TIMESTAMPTZ,
    -- alineación
    formacion       TEXT,
    confirmada      BOOLEAN,
    completa        BOOLEAN,
    -- contexto del partido
    arbitro_partidos       INTEGER,
    arbitro_amarillas      INTEGER,
    arbitro_rojas          INTEGER,
    arbitro_doble_amarilla INTEGER,
    arbitro_pais    TEXT,
    ronda           INTEGER,
    descuento_1t    SMALLINT,
    descuento_2t    SMALLINT,
    goles_local_1t  SMALLINT,
    goles_visita_1t SMALLINT,
    asistencia      INTEGER,
    -- tiro / incidencia
    minuto          SMALLINT,
    anadido         SMALLINT,
    segundo         INTEGER,
    resultado       TEXT,                         -- tiro: goal | save | miss | block | post
    situacion       TEXT,
    parte_cuerpo    TEXT,
    x               REAL,
    y               REAL,
    boca            TEXT,
    boca_x          REAL,
    boca_y          REAL,
    boca_z          REAL,
    subtipo         TEXT,                         -- incidencia: card | substitution | goal | varDecision ...
    clase           TEXT,                         -- yellow | red | regular | injury | penalty ...
    razon           TEXT,
    marcador_local  SMALLINT,
    marcador_visita SMALLINT,
    -- clima
    temperatura_c   REAL,
    humedad_pct     REAL,
    viento_ms       REAL,
    precipitacion_mm REAL,
    nubosidad_pct   REAL,
    -- estadio
    estadio_ciudad  TEXT,
    estadio_capacidad INTEGER,
    estadio_lat     DOUBLE PRECISION,
    estadio_lon     DOUBLE PRECISION,
    altitud_m       REAL,
    PRIMARY KEY (match_id, tipo, side, jugador_id, evento)
);
CREATE INDEX IF NOT EXISTS futbol_dato_jugador ON futbol.dato (jugador_id, fuente) WHERE tipo = 'jugador';
CREATE INDEX IF NOT EXISTS futbol_dato_tipo_fuente ON futbol.dato (tipo, fuente);

-- ── Funciones: identidad ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION futbol.id_sintetico(p_fuente TEXT, p_id BIGINT) RETURNS BIGINT
LANGUAGE sql IMMUTABLE AS $f$
    SELECT CASE WHEN p_fuente IN ('sofascore', 'sportsapipro') THEN p_id
                WHEN p_fuente = 'fotmob' THEN -p_id
                WHEN p_fuente = 'api_football' THEN -(1000000000 + p_id)
                ELSE -(2000000000 + p_id) END
$f$;

CREATE OR REPLACE FUNCTION futbol.jugador_canonico(p_fuente TEXT, p_id BIGINT, p_nombre TEXT) RETURNS BIGINT
LANGUAGE plpgsql AS $f$
DECLARE canon BIGINT;
BEGIN
    SELECT jugador_id INTO canon FROM futbol.jugador_fuente_id WHERE fuente = p_fuente AND id_en_fuente = p_id;
    IF canon IS NOT NULL THEN RETURN canon; END IF;
    canon := futbol.id_sintetico(p_fuente, p_id);
    INSERT INTO futbol.jugador (jugador_id, nombre) VALUES (canon, COALESCE(NULLIF(p_nombre, ''), '?'))
        ON CONFLICT (jugador_id) DO NOTHING;
    INSERT INTO futbol.jugador_fuente_id (fuente, id_en_fuente, jugador_id, evidencia)
        VALUES (p_fuente, p_id, canon,
                CASE WHEN p_fuente IN ('sofascore', 'sportsapipro') THEN 'id_canonico' ELSE 'solo_en_fuente' END)
        ON CONFLICT (fuente, id_en_fuente) DO NOTHING;
    RETURN canon;
END
$f$;

-- Enlaza el id de una fuente con otro jugador canónico y pasa a él todas sus filas de `futbol.dato`.
CREATE OR REPLACE FUNCTION futbol.vincular_jugador(p_fuente TEXT, p_id BIGINT, p_canonico BIGINT,
                                                   p_evidencia TEXT, p_partidos INTEGER) RETURNS BIGINT
LANGUAGE plpgsql AS $f$
DECLARE anterior BIGINT; movidas BIGINT := 0; n BIGINT;
BEGIN
    SELECT jugador_id INTO anterior FROM futbol.jugador_fuente_id WHERE fuente = p_fuente AND id_en_fuente = p_id;
    IF anterior IS NOT NULL AND anterior <> p_canonico THEN
        -- si el jugador ya tiene fila en ese partido y lado con el id nuevo, la del id viejo sobra
        DELETE FROM futbol.dato o WHERE o.jugador_id = anterior AND o.tipo IN ('jugador', 'baja') AND EXISTS (
            SELECT 1 FROM futbol.dato d WHERE d.match_id = o.match_id AND d.tipo = o.tipo AND d.side = o.side
               AND d.jugador_id = p_canonico AND d.evento = o.evento);
        UPDATE futbol.dato SET jugador_id = p_canonico WHERE jugador_id = anterior;
        GET DIAGNOSTICS n = ROW_COUNT; movidas := n;
        UPDATE futbol.dato SET jugador2_id = p_canonico WHERE jugador2_id = anterior;
    END IF;
    INSERT INTO futbol.jugador_fuente_id (fuente, id_en_fuente, jugador_id, evidencia, partidos)
        VALUES (p_fuente, p_id, p_canonico, p_evidencia, p_partidos)
        ON CONFLICT (fuente, id_en_fuente) DO UPDATE SET jugador_id = EXCLUDED.jugador_id,
            evidencia = EXCLUDED.evidencia, partidos = EXCLUDED.partidos;
    IF anterior IS NOT NULL AND anterior <> p_canonico
       AND NOT EXISTS (SELECT 1 FROM futbol.jugador_fuente_id WHERE jugador_id = anterior) THEN
        DELETE FROM futbol.jugador WHERE jugador_id = anterior;
    END IF;
    RETURN movidas;
END
$f$;

-- ── Utilidades para leer las estadísticas anidadas de FotMob ─────────────────────────────────────
CREATE OR REPLACE FUNCTION futbol.fm_aplanar(p_stats JSONB) RETURNS JSONB
LANGUAGE sql IMMUTABLE AS $f$
    SELECT COALESCE(jsonb_object_agg(s.value ->> 'key', s.value -> 'stat'), '{}'::jsonb)
      FROM jsonb_array_elements(CASE WHEN jsonb_typeof(p_stats) = 'array' THEN p_stats ELSE '[]'::jsonb END) g,
           jsonb_each(CASE WHEN jsonb_typeof(g -> 'stats') = 'object' THEN g -> 'stats' ELSE '{}'::jsonb END) s
     WHERE s.value ->> 'key' IS NOT NULL
$f$;
CREATE OR REPLACE FUNCTION futbol.fm_num(p_st JSONB, p_clave TEXT, p_campo TEXT DEFAULT 'value') RETURNS REAL
LANGUAGE sql IMMUTABLE AS $f$
    SELECT CASE WHEN jsonb_typeof(p_st -> p_clave -> p_campo) = 'number' THEN (p_st -> p_clave ->> p_campo)::real END
$f$;
CREATE OR REPLACE FUNCTION futbol.a_smallint(p_x REAL) RETURNS SMALLINT
LANGUAGE sql IMMUTABLE AS $f$
    SELECT CASE WHEN p_x IS NOT NULL AND abs(p_x) <= 32767 THEN round(p_x)::smallint END
$f$;

-- ── Adaptador FotMob -> futbol.dato ──────────────────────────────────────────────────────────────
-- Traduce `fotmob_*` (y las estadísticas de historical_football_player_stats, vía v_fotmob_jugador_partido).
-- FotMob es la fuente 1: reemplaza lo que hubiera de otra fuente en esos partidos. Idempotente.
DROP FUNCTION IF EXISTS futbol.cargar_fotmob(TIMESTAMPTZ);
CREATE FUNCTION futbol.cargar_fotmob(p_desde TIMESTAMPTZ DEFAULT NULL)
RETURNS TABLE (entidad TEXT, partidos BIGINT, filas BIGINT)
LANGUAGE plpgsql AS $f$
#variable_conflict use_column
DECLARE n BIGINT; p BIGINT;
BEGIN
    CREATE TEMP TABLE IF NOT EXISTS tmp_fm_partidos (match_id TEXT PRIMARY KEY) ON COMMIT DROP;
    TRUNCATE tmp_fm_partidos;
    INSERT INTO tmp_fm_partidos
        SELECT DISTINCT j.match_id FROM fotmob_jugador_partido j
         WHERE p_desde IS NULL OR EXISTS (SELECT 1 FROM fotmob_partido fp
                                           WHERE fp.match_id = j.match_id AND fp.recibido_en >= p_desde);

    INSERT INTO futbol.jugador (jugador_id, nombre)
        SELECT -j.jugador_id, COALESCE(max(NULLIF(j.nombre, '')), '?')
          FROM fotmob_jugador_partido j JOIN tmp_fm_partidos t USING (match_id)
         WHERE NOT EXISTS (SELECT 1 FROM futbol.jugador_fuente_id m WHERE m.fuente = 'fotmob' AND m.id_en_fuente = j.jugador_id)
         GROUP BY j.jugador_id
        ON CONFLICT (jugador_id) DO NOTHING;
    INSERT INTO futbol.jugador_fuente_id (fuente, id_en_fuente, jugador_id, evidencia)
        SELECT DISTINCT 'fotmob', j.jugador_id, -j.jugador_id, 'solo_en_fuente'
          FROM fotmob_jugador_partido j JOIN tmp_fm_partidos t USING (match_id)
         WHERE NOT EXISTS (SELECT 1 FROM futbol.jugador_fuente_id m WHERE m.fuente = 'fotmob' AND m.id_en_fuente = j.jugador_id)
        ON CONFLICT (fuente, id_en_fuente) DO NOTHING;

    -- jugador: se prepara y se hace UPSERT. Lo que otra fuente (SofaScore) completó en la fila de FotMob se conserva;
    -- las entradas del motor `nota`, `valor_mercado` y `posicion_id` quedan EXACTAMENTE como las da FotMob.
    CREATE TEMP TABLE IF NOT EXISTS tmp_fm_jug (LIKE futbol.dato INCLUDING DEFAULTS) ON COMMIT DROP;
    TRUNCATE tmp_fm_jug;
    INSERT INTO tmp_fm_jug (match_id, tipo, side, jugador_id, fuente, recibido_en, nombre, posicion, titular, camiseta,
        minutos, nota, goles, asistencias, xa, tiros_puerta, tiros_fuera, tiros_bloq, grandes_ocasiones_creadas,
        grandes_ocasiones_falladas, pases, pases_acertados, balones_largos, balones_largos_acertados, centros,
        centros_acertados, duelos_ganados, duelos_perdidos, aereos_ganados, entradas, intercepciones, despejes,
        recuperaciones, perdidas, faltas, faltas_recibidas, fuera_juego, toques, paradas,
        edad, valor_mercado, posicion_id, id_en_fuente)
    SELECT DISTINCT ON (v.match_id, v.side, m.jugador_id)
           v.match_id, 'jugador', v.side, m.jugador_id, 'fotmob', COALESCE(fp.recibido_en, now()), v.nombre, NULL,
           v.titular, v.camiseta, v.minutos,
           COALESCE(v.rating, futbol.fm_num(a.st, 'rating_title')),
           futbol.a_smallint(futbol.fm_num(a.st, 'goals')), futbol.a_smallint(futbol.fm_num(a.st, 'assists')),
           futbol.fm_num(a.st, 'expected_assists'),
           futbol.a_smallint(futbol.fm_num(a.st, 'ShotsOnTarget')), futbol.a_smallint(futbol.fm_num(a.st, 'ShotsOffTarget')),
           futbol.a_smallint(futbol.fm_num(a.st, 'blocked_shots')),
           futbol.a_smallint(futbol.fm_num(a.st, 'big_chance_created_team_title')),
           futbol.a_smallint(futbol.fm_num(a.st, 'big_chance_missed_title')),
           futbol.a_smallint(futbol.fm_num(a.st, 'accurate_passes', 'total')),
           futbol.a_smallint(futbol.fm_num(a.st, 'accurate_passes')),
           futbol.a_smallint(futbol.fm_num(a.st, 'long_balls_accurate', 'total')),
           futbol.a_smallint(futbol.fm_num(a.st, 'long_balls_accurate')),
           futbol.a_smallint(futbol.fm_num(a.st, 'accurate_crosses', 'total')),
           futbol.a_smallint(futbol.fm_num(a.st, 'accurate_crosses')),
           futbol.a_smallint(futbol.fm_num(a.st, 'duel_won')), futbol.a_smallint(futbol.fm_num(a.st, 'duel_lost')),
           futbol.a_smallint(futbol.fm_num(a.st, 'aerials_won')),
           futbol.a_smallint(futbol.fm_num(a.st, 'matchstats.headers.tackles')),
           futbol.a_smallint(futbol.fm_num(a.st, 'interceptions')), futbol.a_smallint(futbol.fm_num(a.st, 'clearances')),
           futbol.a_smallint(futbol.fm_num(a.st, 'recoveries')), futbol.a_smallint(futbol.fm_num(a.st, 'dispossessed')),
           futbol.a_smallint(futbol.fm_num(a.st, 'fouls')), futbol.a_smallint(futbol.fm_num(a.st, 'was_fouled')),
           futbol.a_smallint(futbol.fm_num(a.st, 'Offsides')), futbol.a_smallint(futbol.fm_num(a.st, 'touches')),
           futbol.a_smallint(futbol.fm_num(a.st, 'saves')),
           NULLIF(j.edad, 0)::smallint, j.valor_mercado, j.posicion_id, v.jugador_id
      FROM v_fotmob_jugador_partido v
      JOIN tmp_fm_partidos t ON t.match_id = v.match_id
      JOIN fotmob_partido fp ON fp.match_id = v.match_id
      JOIN fotmob_jugador_partido j ON j.match_id = v.match_id AND j.side = v.side AND j.jugador_id = v.jugador_id
      JOIN futbol.jugador_fuente_id m ON m.fuente = 'fotmob' AND m.id_en_fuente = v.jugador_id
      CROSS JOIN LATERAL (SELECT futbol.fm_aplanar(v.estadisticas) AS st) a
     ORDER BY v.match_id, v.side, m.jugador_id;
    GET DIAGNOSTICS n = ROW_COUNT;
    DELETE FROM futbol.dato d USING tmp_fm_partidos t
     WHERE d.match_id = t.match_id AND d.tipo = 'jugador'
       AND NOT EXISTS (SELECT 1 FROM tmp_fm_jug j WHERE j.match_id = d.match_id AND j.side = d.side AND j.jugador_id = d.jugador_id);
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, fuente, recibido_en, nombre, posicion, titular, camiseta,
        minutos, nota, goles, asistencias, xa, tiros_puerta, tiros_fuera, tiros_bloq, grandes_ocasiones_creadas,
        grandes_ocasiones_falladas, pases, pases_acertados, balones_largos, balones_largos_acertados, centros,
        centros_acertados, duelos_ganados, duelos_perdidos, aereos_ganados, entradas, intercepciones, despejes,
        recuperaciones, perdidas, faltas, faltas_recibidas, fuera_juego, toques, paradas,
        edad, valor_mercado, posicion_id, id_en_fuente)
    SELECT match_id, tipo, side, jugador_id, fuente, recibido_en, nombre, posicion, titular, camiseta,
        minutos, nota, goles, asistencias, xa, tiros_puerta, tiros_fuera, tiros_bloq, grandes_ocasiones_creadas,
        grandes_ocasiones_falladas, pases, pases_acertados, balones_largos, balones_largos_acertados, centros,
        centros_acertados, duelos_ganados, duelos_perdidos, aereos_ganados, entradas, intercepciones, despejes,
        recuperaciones, perdidas, faltas, faltas_recibidas, fuera_juego, toques, paradas,
        edad, valor_mercado, posicion_id, id_en_fuente
      FROM tmp_fm_jug
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO UPDATE SET
        fuente_extra = CASE WHEN futbol.dato.fuente <> 'fotmob' THEN futbol.dato.fuente ELSE futbol.dato.fuente_extra END,
        fuente = 'fotmob', recibido_en = EXCLUDED.recibido_en,
        nota = EXCLUDED.nota, valor_mercado = EXCLUDED.valor_mercado, posicion_id = EXCLUDED.posicion_id,
        nombre = COALESCE(EXCLUDED.nombre, futbol.dato.nombre), posicion = COALESCE(EXCLUDED.posicion, futbol.dato.posicion),
        titular = COALESCE(EXCLUDED.titular, futbol.dato.titular), camiseta = COALESCE(EXCLUDED.camiseta, futbol.dato.camiseta),
        minutos = COALESCE(EXCLUDED.minutos, futbol.dato.minutos), goles = COALESCE(EXCLUDED.goles, futbol.dato.goles),
        asistencias = COALESCE(EXCLUDED.asistencias, futbol.dato.asistencias), xa = COALESCE(EXCLUDED.xa, futbol.dato.xa),
        tiros_puerta = COALESCE(EXCLUDED.tiros_puerta, futbol.dato.tiros_puerta),
        tiros_fuera = COALESCE(EXCLUDED.tiros_fuera, futbol.dato.tiros_fuera),
        tiros_bloq = COALESCE(EXCLUDED.tiros_bloq, futbol.dato.tiros_bloq),
        grandes_ocasiones_creadas = COALESCE(EXCLUDED.grandes_ocasiones_creadas, futbol.dato.grandes_ocasiones_creadas),
        grandes_ocasiones_falladas = COALESCE(EXCLUDED.grandes_ocasiones_falladas, futbol.dato.grandes_ocasiones_falladas),
        pases = COALESCE(EXCLUDED.pases, futbol.dato.pases), pases_acertados = COALESCE(EXCLUDED.pases_acertados, futbol.dato.pases_acertados),
        balones_largos = COALESCE(EXCLUDED.balones_largos, futbol.dato.balones_largos),
        balones_largos_acertados = COALESCE(EXCLUDED.balones_largos_acertados, futbol.dato.balones_largos_acertados),
        centros = COALESCE(EXCLUDED.centros, futbol.dato.centros), centros_acertados = COALESCE(EXCLUDED.centros_acertados, futbol.dato.centros_acertados),
        duelos_ganados = COALESCE(EXCLUDED.duelos_ganados, futbol.dato.duelos_ganados),
        duelos_perdidos = COALESCE(EXCLUDED.duelos_perdidos, futbol.dato.duelos_perdidos),
        aereos_ganados = COALESCE(EXCLUDED.aereos_ganados, futbol.dato.aereos_ganados),
        entradas = COALESCE(EXCLUDED.entradas, futbol.dato.entradas), intercepciones = COALESCE(EXCLUDED.intercepciones, futbol.dato.intercepciones),
        despejes = COALESCE(EXCLUDED.despejes, futbol.dato.despejes), recuperaciones = COALESCE(EXCLUDED.recuperaciones, futbol.dato.recuperaciones),
        perdidas = COALESCE(EXCLUDED.perdidas, futbol.dato.perdidas), faltas = COALESCE(EXCLUDED.faltas, futbol.dato.faltas),
        faltas_recibidas = COALESCE(EXCLUDED.faltas_recibidas, futbol.dato.faltas_recibidas),
        fuera_juego = COALESCE(EXCLUDED.fuera_juego, futbol.dato.fuera_juego), toques = COALESCE(EXCLUDED.toques, futbol.dato.toques),
        paradas = COALESCE(EXCLUDED.paradas, futbol.dato.paradas), edad = COALESCE(EXCLUDED.edad, futbol.dato.edad),
        id_en_fuente = COALESCE(EXCLUDED.id_en_fuente, futbol.dato.id_en_fuente);
    SELECT count(DISTINCT d.match_id) INTO p FROM futbol.dato d JOIN tmp_fm_partidos t USING (match_id)
     WHERE d.tipo = 'jugador' AND d.fuente = 'fotmob';
    entidad := 'jugador'; partidos := p; filas := n; RETURN NEXT;

    -- baja: UPSERT. `motivo_codigo` y `descripcion` (que FotMob no trae) se conservan si SofaScore los completó; si
    -- FotMob no informa bajas de un partido, siguen las de otra fuente.
    CREATE TEMP TABLE IF NOT EXISTS tmp_fm_baja (LIKE futbol.dato INCLUDING DEFAULTS) ON COMMIT DROP;
    TRUNCATE tmp_fm_baja;
    INSERT INTO tmp_fm_baja (match_id, tipo, side, jugador_id, fuente, recibido_en, pit, nombre, estado, id_en_fuente,
                             regreso_texto, regreso_fecha, valor_mercado, edad, posicion_id)
    SELECT DISTINCT ON (b.match_id, b.side, m.jugador_id) b.match_id, 'baja', b.side, m.jugador_id, 'fotmob',
           COALESCE(fp.recibido_en, now()), 'reconstruido', b.nombre, COALESCE(b.tipo, 'missing'), b.jugador_id,
           b.regreso_texto, b.regreso_fecha, b.valor_mercado, b.edad, b.posicion_id
      FROM fotmob_baja b
      JOIN tmp_fm_partidos t ON t.match_id = b.match_id
      LEFT JOIN fotmob_partido fp ON fp.match_id = b.match_id
      CROSS JOIN LATERAL (SELECT futbol.jugador_canonico('fotmob', b.jugador_id, b.nombre) AS jugador_id) m
     ORDER BY b.match_id, b.side, m.jugador_id;
    GET DIAGNOSTICS n = ROW_COUNT;
    DELETE FROM futbol.dato d USING tmp_fm_partidos t
     WHERE d.match_id = t.match_id AND d.tipo = 'baja'
       AND NOT EXISTS (SELECT 1 FROM tmp_fm_baja j WHERE j.match_id = d.match_id AND j.side = d.side AND j.jugador_id = d.jugador_id)
       AND (d.fuente = 'fotmob' OR EXISTS (SELECT 1 FROM tmp_fm_baja j WHERE j.match_id = d.match_id));
    INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, fuente, recibido_en, pit, nombre, estado, id_en_fuente,
                             regreso_texto, regreso_fecha, valor_mercado, edad, posicion_id)
    SELECT match_id, tipo, side, jugador_id, fuente, recibido_en, pit, nombre, estado, id_en_fuente,
           regreso_texto, regreso_fecha, valor_mercado, edad, posicion_id
      FROM tmp_fm_baja
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO UPDATE SET
        fuente_extra = CASE WHEN futbol.dato.fuente <> 'fotmob' THEN futbol.dato.fuente ELSE futbol.dato.fuente_extra END,
        fuente = 'fotmob', recibido_en = EXCLUDED.recibido_en, pit = EXCLUDED.pit, nombre = COALESCE(EXCLUDED.nombre, futbol.dato.nombre),
        estado = EXCLUDED.estado, id_en_fuente = COALESCE(EXCLUDED.id_en_fuente, futbol.dato.id_en_fuente),
        regreso_texto = COALESCE(EXCLUDED.regreso_texto, futbol.dato.regreso_texto),
        regreso_fecha = COALESCE(EXCLUDED.regreso_fecha, futbol.dato.regreso_fecha),
        valor_mercado = EXCLUDED.valor_mercado, edad = COALESCE(EXCLUDED.edad, futbol.dato.edad),
        posicion_id = EXCLUDED.posicion_id;
    SELECT count(DISTINCT d.match_id) INTO p FROM futbol.dato d JOIN tmp_fm_partidos t USING (match_id)
     WHERE d.tipo = 'baja' AND d.fuente = 'fotmob';
    entidad := 'baja'; partidos := p; filas := n; RETURN NEXT;

    -- alineacion
    DELETE FROM futbol.dato d USING tmp_fm_partidos t WHERE d.match_id = t.match_id AND d.tipo = 'alineacion';
    INSERT INTO futbol.dato (match_id, tipo, side, fuente, recibido_en, formacion, confirmada, completa)
    SELECT p2.match_id, 'alineacion', s.side, 'fotmob', COALESCE(p2.recibido_en, now()),
           CASE s.side WHEN 'home' THEN p2.formacion_local ELSE p2.formacion_visita END, TRUE,
           (SELECT count(*) FROM fotmob_jugador_partido j
             WHERE j.match_id = p2.match_id AND j.side = s.side AND j.titular) = 11
      FROM fotmob_partido p2 JOIN tmp_fm_partidos t ON t.match_id = p2.match_id
      CROSS JOIN (VALUES ('home'), ('away')) s(side)
     WHERE (CASE s.side WHEN 'home' THEN p2.formacion_local ELSE p2.formacion_visita END) IS NOT NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    entidad := 'alineacion'; partidos := n / 2; filas := n; RETURN NEXT;

    -- entrenador
    DELETE FROM futbol.dato d USING tmp_fm_partidos t WHERE d.match_id = t.match_id AND d.tipo = 'entrenador';
    INSERT INTO futbol.dato (match_id, tipo, side, fuente, recibido_en, id_en_fuente, nombre)
    SELECT p2.match_id, 'entrenador', s.side, 'fotmob', COALESCE(p2.recibido_en, now()),
           CASE s.side WHEN 'home' THEN p2.entrenador_local_id ELSE p2.entrenador_visita_id END,
           CASE s.side WHEN 'home' THEN p2.entrenador_local ELSE p2.entrenador_visita END
      FROM fotmob_partido p2 JOIN tmp_fm_partidos t ON t.match_id = p2.match_id
      CROSS JOIN (VALUES ('home'), ('away')) s(side)
     WHERE (CASE s.side WHEN 'home' THEN p2.entrenador_local_id ELSE p2.entrenador_visita_id END) IS NOT NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    entidad := 'entrenador'; partidos := n / 2; filas := n; RETURN NEXT;
END
$f$;

-- ── Adaptador clima: ERA5 (medido por celda y hora) primero; FotMob solo donde ERA5 no llega ─────
-- Los m/s del viento de FotMob no están verificados: en sus filas `viento_ms` va vacío.
CREATE OR REPLACE FUNCTION futbol.cargar_clima() RETURNS BIGINT
LANGUAGE plpgsql AS $f$
DECLARE n BIGINT := 0; k BIGINT;
BEGIN
    INSERT INTO futbol.dato (match_id, tipo, fuente, recibido_en, temperatura_c, humedad_pct, viento_ms,
                             precipitacion_mm, nubosidad_pct)
    SELECT c.match_id, 'clima', 'era5', COALESCE(c.calculado_en, now()), c.temperatura_c, c.humedad_pct, c.viento_ms,
           c.precipitacion_mm, c.nubosidad_pct
      FROM clima_era5_partido c
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO UPDATE SET fuente = 'era5',
        recibido_en = EXCLUDED.recibido_en, temperatura_c = EXCLUDED.temperatura_c, humedad_pct = EXCLUDED.humedad_pct,
        viento_ms = EXCLUDED.viento_ms, precipitacion_mm = EXCLUDED.precipitacion_mm,
        nubosidad_pct = EXCLUDED.nubosidad_pct;
    GET DIAGNOSTICS k = ROW_COUNT; n := n + k;
    INSERT INTO futbol.dato (match_id, tipo, fuente, recibido_en, temperatura_c, humedad_pct, precipitacion_mm, nubosidad_pct)
    SELECT p.match_id, 'clima', 'fotmob', COALESCE(p.recibido_en, now()), p.clima_temperatura_c, p.clima_humedad,
           p.clima_precipitacion, p.clima_nubosidad
      FROM fotmob_partido p
     WHERE p.clima_temperatura_c IS NOT NULL
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO NOTHING;   -- no pisa a ERA5
    GET DIAGNOSTICS k = ROW_COUNT; n := n + k;
    RETURN n;
END
$f$;

-- ── Adaptador estadio y altitud (OpenTopoData) ───────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION futbol.cargar_estadio() RETURNS BIGINT
LANGUAGE plpgsql AS $f$
DECLARE n BIGINT;
BEGIN
    INSERT INTO futbol.dato (match_id, tipo, fuente, recibido_en, nombre, estadio_ciudad, estadio_capacidad,
                             estadio_lat, estadio_lon, altitud_m)
    SELECT m.match_id, 'estadio', 'opentopodata', COALESCE(a.recibido_en, now()), e.name, e.city, e.capacity,
           e.lat, e.lon, a.altitud_m
      FROM matches m JOIN estadios e ON e.stadium_id = m.stadium_id
      JOIN estadio_altitud a ON a.stadium_id = e.stadium_id
    ON CONFLICT (match_id, tipo, side, jugador_id, evento) DO UPDATE SET recibido_en = EXCLUDED.recibido_en,
        nombre = EXCLUDED.nombre, estadio_ciudad = EXCLUDED.estadio_ciudad,
        estadio_capacidad = EXCLUDED.estadio_capacidad, estadio_lat = EXCLUDED.estadio_lat,
        estadio_lon = EXCLUDED.estadio_lon, altitud_m = EXCLUDED.altitud_m;
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END
$f$;

COMMIT;
