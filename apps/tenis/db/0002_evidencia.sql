-- 0002: recibos (originales) y evidencia de partidos (plan técnico tenis, §A.3).
-- Cada fila lleva `fuente`, `recibo_id` y `recibido_en` real. Las claves naturales UNIQUE hacen idempotente la carga.
-- La inmutabilidad es de 0003; la lectura punto en el tiempo, de 0004.

-- Original recibido: un contenido (sha256) puede recibirse varias veces; cada recepción es una fila.
-- `retro` marca datos históricos cuya recepción no es la del partido (regla RETRO, plan §A.4).
CREATE TABLE IF NOT EXISTS tenis.recibo (
    recibo_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fuente      TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recurso     TEXT NOT NULL CHECK (length(recurso) > 0),
    parametros  JSONB NOT NULL DEFAULT '{}'
                CHECK (jsonb_typeof(parametros) = 'object'
                       AND parametros::text !~* '(key|token|secret|clave|password|passwd)'),
    recibido_en TIMESTAMPTZ NOT NULL,
    estado_http SMALLINT CHECK (estado_http IS NULL OR estado_http BETWEEN 100 AND 599),
    sha256      TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    ruta_objeto TEXT NOT NULL CHECK (ruta_objeto IN ('objetos/' || substr(sha256, 1, 2) || '/' || sha256 || '.json.gz',
                                                     'objetos/' || substr(sha256, 1, 2) || '/' || sha256 || '.csv.gz')),
    bytes       BIGINT NOT NULL CHECK (bytes >= 0),
    lote        TEXT NOT NULL CHECK (length(lote) > 0),
    retro       BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (fuente, recurso, sha256, recibido_en)
);

-- Las tablas de 0001 llevan recibo_id desde su creación; aquí se fija la clave foránea.
ALTER TABLE tenis.jugador         ADD CONSTRAINT jugador_recibo_fk         FOREIGN KEY (recibo_id) REFERENCES tenis.recibo (recibo_id);
ALTER TABLE tenis.jugador_asercion ADD CONSTRAINT jugador_asercion_recibo_fk FOREIGN KEY (recibo_id) REFERENCES tenis.recibo (recibo_id);
ALTER TABLE tenis.jugador_alias   ADD CONSTRAINT jugador_alias_recibo_fk   FOREIGN KEY (recibo_id) REFERENCES tenis.recibo (recibo_id);
ALTER TABLE tenis.torneo          ADD CONSTRAINT torneo_recibo_fk          FOREIGN KEY (recibo_id) REFERENCES tenis.recibo (recibo_id);
ALTER TABLE tenis.sede            ADD CONSTRAINT sede_recibo_fk            FOREIGN KEY (recibo_id) REFERENCES tenis.recibo (recibo_id);
ALTER TABLE tenis.edicion         ADD CONSTRAINT edicion_recibo_fk         FOREIGN KEY (recibo_id) REFERENCES tenis.recibo (recibo_id);

-- Partido. Orden canónico: jugador_1 < jugador_2 por id, NUNCA el ganador primero (filtraría el resultado).
CREATE TABLE IF NOT EXISTS tenis.partido (
    partido_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    edicion_id  BIGINT NOT NULL REFERENCES tenis.edicion (edicion_id),
    ronda       TEXT NOT NULL CHECK (ronda ~ '^[A-Z]{1,2}[0-9]*$'),
    jugador_1   BIGINT NOT NULL REFERENCES tenis.jugador (jugador_id),
    jugador_2   BIGINT NOT NULL REFERENCES tenis.jugador (jugador_id),
    mejor_de    SMALLINT NOT NULL CHECK (mejor_de IN (3, 5)),
    formato     JSONB CHECK (formato IS NULL OR jsonb_typeof(formato) = 'object'),
    entrada_1   TEXT CHECK (entrada_1 IN ('Q', 'LL', 'WC', 'PR', 'SE')),
    entrada_2   TEXT CHECK (entrada_2 IN ('Q', 'LL', 'WC', 'PR', 'SE')),
    fuente      TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id   BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    recibido_en TIMESTAMPTZ NOT NULL,
    -- Solo datos retro (recibo.retro): instante desde el que el dato era conocible. NULL = regla por semana (0004).
    visible_desde TIMESTAMPTZ,
    CONSTRAINT partido_jugadores_distintos CHECK (jugador_1 <> jugador_2),
    CONSTRAINT partido_orden_canonico CHECK (jugador_1 < jugador_2),
    UNIQUE (edicion_id, ronda, jugador_1, jugador_2)
);

-- Aserción de horario. `inicio_programado_utc` NULL solo si la hora no es fija (a continuación / desconocida).
CREATE TABLE IF NOT EXISTS tenis.programa (
    programa_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partido_id            BIGINT NOT NULL REFERENCES tenis.partido (partido_id),
    inicio_programado_utc TIMESTAMPTZ,
    tipo_hora             TEXT NOT NULL CHECK (tipo_hora IN ('fija', 'no_antes_de', 'a_continuacion', 'desconocida')),
    pista                 TEXT,
    estado                TEXT NOT NULL CHECK (estado IN ('programado', 'en_juego', 'suspendido', 'aplazado')),
    fuente                TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id             BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    recibido_en           TIMESTAMPTZ NOT NULL,
    visible_desde         TIMESTAMPTZ,
    CHECK (inicio_programado_utc IS NOT NULL OR tipo_hora IN ('a_continuacion', 'desconocida')),
    CHECK (tipo_hora NOT IN ('fija', 'no_antes_de') OR inicio_programado_utc IS NOT NULL),
    UNIQUE (partido_id, fuente, recibido_en)
);

-- Desenlace. Walkover, cancelado y descalificado no tienen ganador (nulo para liquidar, plan §I.9).
-- Retirada: ganador y retirado conocidos. NULL en duración = falta; nunca 0.
CREATE TABLE IF NOT EXISTS tenis.resultado (
    resultado_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partido_id     BIGINT NOT NULL REFERENCES tenis.partido (partido_id),
    estado         TEXT NOT NULL CHECK (estado IN ('completado', 'retirada', 'walkover', 'descalificado', 'cancelado')),
    ganador        SMALLINT CHECK (ganador IN (1, 2)),
    retira         SMALLINT CHECK (retira IN (1, 2)),
    sets           JSONB CHECK (sets IS NULL OR jsonb_typeof(sets) = 'array'),
    sets_completos SMALLINT CHECK (sets_completos IS NULL OR sets_completos >= 0),
    duracion_min   SMALLINT CHECK (duracion_min IS NULL OR duracion_min BETWEEN 1 AND 600),
    fuente         TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id      BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    recibido_en    TIMESTAMPTZ NOT NULL,
    visible_desde  TIMESTAMPTZ,
    CHECK (retira IS NULL OR estado = 'retirada'),
    CHECK (estado <> 'completado' OR (ganador IS NOT NULL AND sets IS NOT NULL
                                      AND sets_completos IS NOT NULL AND sets_completos >= 2)),
    CHECK (estado <> 'retirada' OR (ganador IS NOT NULL AND retira IS NOT NULL AND retira <> ganador)),
    CHECK (estado NOT IN ('walkover', 'cancelado') OR (ganador IS NULL AND sets IS NULL AND sets_completos IS NULL)),
    CHECK (estado <> 'descalificado' OR ganador IS NULL),
    UNIQUE (partido_id, fuente, recibido_en)
);

-- Estadística de servicio por lado. NULL = dato no publicado (nunca 0). Orden de comprobaciones del plan §A.3.
CREATE TABLE IF NOT EXISTS tenis.estadistica (
    estadistica_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partido_id       BIGINT NOT NULL REFERENCES tenis.partido (partido_id),
    lado             SMALLINT NOT NULL CHECK (lado IN (1, 2)),
    aces             INTEGER CHECK (aces IS NULL OR aces >= 0),
    dobles_faltas    INTEGER CHECK (dobles_faltas IS NULL OR dobles_faltas >= 0),
    puntos_saque     INTEGER CHECK (puntos_saque IS NULL OR puntos_saque >= 0),
    primeros_dentro  INTEGER CHECK (primeros_dentro IS NULL OR primeros_dentro >= 0),
    primeros_ganados INTEGER CHECK (primeros_ganados IS NULL OR primeros_ganados >= 0),
    segundos_ganados INTEGER CHECK (segundos_ganados IS NULL OR segundos_ganados >= 0),
    juegos_saque     INTEGER CHECK (juegos_saque IS NULL OR juegos_saque >= 0),
    bp_salvados      INTEGER CHECK (bp_salvados IS NULL OR bp_salvados >= 0),
    bp_afrontados    INTEGER CHECK (bp_afrontados IS NULL OR bp_afrontados >= 0),
    fuente           TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id        BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    recibido_en      TIMESTAMPTZ NOT NULL,
    visible_desde    TIMESTAMPTZ,
    CHECK (primeros_dentro IS NULL OR puntos_saque IS NULL OR primeros_dentro <= puntos_saque),
    CHECK (primeros_ganados IS NULL OR primeros_dentro IS NULL OR primeros_ganados <= primeros_dentro),
    CHECK (bp_salvados IS NULL OR bp_afrontados IS NULL OR bp_salvados <= bp_afrontados),
    UNIQUE (partido_id, lado, fuente, recibido_en)
);

-- Punto a punto: un juego, sacador y puntos en orden (S = gana el sacador, R = gana el resto).
CREATE TABLE IF NOT EXISTS tenis.juego_pbp (
    juego_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partido_id   BIGINT NOT NULL REFERENCES tenis.partido (partido_id),
    set_n        SMALLINT NOT NULL CHECK (set_n >= 1),
    juego_n      SMALLINT NOT NULL CHECK (juego_n >= 1),
    sacador      SMALLINT NOT NULL CHECK (sacador IN (1, 2)),
    puntos       TEXT NOT NULL CHECK (puntos ~ '^[SR]+$'),
    es_tiebreak  BOOLEAN NOT NULL,
    fuente       TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id    BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    recibido_en  TIMESTAMPTZ NOT NULL,
    visible_desde TIMESTAMPTZ,
    UNIQUE (partido_id, fuente, recibido_en, set_n, juego_n)
);

-- Ranking publicado un lunes. Solo se lee con fecha_publicacion <= fecha local del partido (plan §C.4).
CREATE TABLE IF NOT EXISTS tenis.ranking (
    ranking_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circuito           TEXT NOT NULL CHECK (circuito IN ('atp', 'wta')),
    fecha_publicacion  DATE NOT NULL CHECK (EXTRACT(ISODOW FROM fecha_publicacion) = 1),
    jugador_id         BIGINT NOT NULL REFERENCES tenis.jugador (jugador_id),
    posicion           INTEGER NOT NULL CHECK (posicion >= 1),
    puntos             INTEGER CHECK (puntos IS NULL OR puntos >= 0),
    origen             TEXT NOT NULL CHECK (origen IN ('oficial_capturado', 'tml_por_partido', 'serie_publica')),
    fuente             TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id          BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    recibido_en        TIMESTAMPTZ NOT NULL,
    visible_desde      TIMESTAMPTZ,
    UNIQUE (circuito, fecha_publicacion, jugador_id, fuente, recibido_en)
);

-- Precio observado de un contrato. Referencia: el motor no lo lee para predecir.
-- Tennis-Data entra con clase_cierre 'b' y sin hora. `linea` NULL = mercado sin línea (índice con NaN).
CREATE TABLE IF NOT EXISTS tenis.precio_mercado (
    precio_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recibo_id      BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    evento_fuente  TEXT NOT NULL CHECK (length(evento_fuente) > 0),
    partido_id     BIGINT REFERENCES tenis.partido (partido_id),
    casa           TEXT NOT NULL CHECK (length(casa) > 0),
    mercado        TEXT NOT NULL CHECK (length(mercado) > 0),
    periodo        TEXT NOT NULL CHECK (length(periodo) > 0),
    linea          NUMERIC(6, 2),
    lado           TEXT NOT NULL CHECK (lado IN ('1', '2', 'over', 'under')),
    cuota_decimal  NUMERIC(8, 3) NOT NULL CHECK (cuota_decimal > 1),
    clase_cierre   TEXT NOT NULL CHECK (clase_cierre IN ('a', 'b', 'c')),
    marcas         JSONB NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(marcas) = 'array'),
    fuente         TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibido_en    TIMESTAMPTZ NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS precio_mercado_natural
    ON tenis.precio_mercado (recibo_id, evento_fuente, casa, mercado, periodo, COALESCE(linea, 'NaN'::numeric), lado);

-- Evento de una fuente de cuotas → partido. Sin enlace único no hay comparación (plan §B.4).
CREATE TABLE IF NOT EXISTS tenis.enlace_evento (
    enlace_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fuente         TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    evento_fuente  TEXT NOT NULL CHECK (length(evento_fuente) > 0),
    partido_id     BIGINT NOT NULL REFERENCES tenis.partido (partido_id),
    metodo         TEXT NOT NULL CHECK (metodo IN ('id_exacto', 'nombre_fecha', 'manual')),
    recibo_id      BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    recibido_en    TIMESTAMPTZ NOT NULL,
    UNIQUE (fuente, evento_fuente, partido_id, recibido_en)
);

-- Cola de lo no resuelto. Se cuenta y alerta; nunca se descarta en silencio (plan §B.3).
CREATE TABLE IF NOT EXISTS tenis.sin_resolver (
    sin_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fuente        TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    id_fuente     TEXT NOT NULL,
    nombre_fuente TEXT NOT NULL,
    motivo        TEXT NOT NULL CHECK (length(motivo) > 0),
    contexto      JSONB NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(contexto) = 'object'),
    recibo_id     BIGINT NOT NULL REFERENCES tenis.recibo (recibo_id),
    recibido_en   TIMESTAMPTZ NOT NULL
);
