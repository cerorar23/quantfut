-- 0001: esquemas y catálogos del motor de tenis (plan técnico tenis, §A.2–A.3).
-- `tenis` es evidencia solo-anexar (la inmutabilidad se añade en 0003). `tenis_op` es estado operativo
-- mutable (cursores y presupuestos), a propósito fuera de la evidencia.
-- Una corrección de un dato es OTRA fila con `recibido_en` posterior; la lectura PIT (0004) elige.
-- Los catálogos llevan `recibo_id`; su clave foránea se añade en 0002, cuando existe `recibo`.
CREATE SCHEMA IF NOT EXISTS tenis;
CREATE SCHEMA IF NOT EXISTS tenis_op;

-- Proveedores. Prioridad: 1 = mejor. Se usan dos porque la identidad (calendario, jugadores, ediciones)
-- y el desenlace (resultados, estadísticas, ranking) no tienen por qué venir del mismo proveedor.
CREATE TABLE IF NOT EXISTS tenis.fuente (
    fuente               TEXT PRIMARY KEY CHECK (fuente ~ '^[a-z][a-z0-9_]*$'),
    prioridad_calendario SMALLINT NOT NULL CHECK (prioridad_calendario >= 1),
    prioridad_resultado  SMALLINT NOT NULL CHECK (prioridad_resultado >= 1),
    licencia             TEXT NOT NULL CHECK (length(licencia) > 0),
    uso_permitido        TEXT NOT NULL CHECK (length(uso_permitido) > 0),
    descripcion          TEXT NOT NULL CHECK (length(descripcion) > 0)
);

-- Persona. Sin nombre: los nombres son aserciones de `jugador_asercion`.
CREATE TABLE IF NOT EXISTS tenis.jugador (
    jugador_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circuito    TEXT NOT NULL CHECK (circuito IN ('atp', 'wta')),
    recibo_id   BIGINT NOT NULL,
    recibido_en TIMESTAMPTZ NOT NULL
);

-- Dato de un jugador según una fuente. La fecha de nacimiento decide homónimos (plan §B).
CREATE TABLE IF NOT EXISTS tenis.jugador_asercion (
    asercion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    jugador_id  BIGINT NOT NULL REFERENCES tenis.jugador (jugador_id),
    campo       TEXT NOT NULL CHECK (campo IN ('nombre', 'fecha_nacimiento', 'mano', 'altura_cm', 'pais')),
    valor       TEXT NOT NULL CHECK (length(valor) > 0),
    fuente      TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id   BIGINT NOT NULL,
    recibido_en TIMESTAMPTZ NOT NULL,
    CHECK (campo <> 'fecha_nacimiento' OR valor ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'),
    CHECK (campo <> 'mano' OR valor IN ('D', 'Z', 'U')),
    CHECK (campo <> 'altura_cm' OR valor ~ '^[0-9]{2,3}$'),
    UNIQUE (jugador_id, campo, fuente, valor, recibido_en)
);

-- Id de una fuente → jugador. Un alias erróneo se anula con OTRA fila (`anula_a`); nunca se borra.
CREATE TABLE IF NOT EXISTS tenis.jugador_alias (
    alias_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fuente      TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    id_fuente   TEXT NOT NULL CHECK (length(id_fuente) > 0),
    jugador_id  BIGINT NOT NULL REFERENCES tenis.jugador (jugador_id),
    metodo      TEXT NOT NULL CHECK (metodo IN ('id_exacto', 'nombre_fecha_nac', 'contexto_partido', 'manual')),
    anula_a     BIGINT REFERENCES tenis.jugador_alias (alias_id),
    recibo_id   BIGINT NOT NULL,
    recibido_en TIMESTAMPTZ NOT NULL,
    CHECK (anula_a IS NULL OR anula_a <> alias_id),
    UNIQUE (fuente, id_fuente, jugador_id, metodo, recibido_en)
);

-- Torneo: identidad estable (circuito + clave). Sus atributos no se corrigen por fila nueva:
-- una categoría distinta exige clave nueva y migración explícita (ver LEEME, supuestos).
CREATE TABLE IF NOT EXISTS tenis.torneo (
    torneo_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    circuito    TEXT NOT NULL CHECK (circuito IN ('atp', 'wta')),
    clave       TEXT NOT NULL CHECK (clave ~ '^[a-z0-9][a-z0-9-]*$'),
    nombre      TEXT NOT NULL CHECK (length(nombre) > 0),
    categoria   TEXT CHECK (categoria IN ('GS', 'M1000', 'WTA1000', '500', '250', 'Finales',
                                          'Challenger', 'ITF', 'equipos', 'JJOO', 'exhibicion')),
    fuente      TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id   BIGINT NOT NULL,
    recibido_en TIMESTAMPTZ NOT NULL,
    UNIQUE (circuito, clave)
);

-- Recinto. Identidad estable, como torneo. La altitud es NULL si no se conoce (nunca 0 por defecto).
CREATE TABLE IF NOT EXISTS tenis.sede (
    sede_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    clave       TEXT NOT NULL UNIQUE CHECK (length(clave) > 0),
    ciudad      TEXT NOT NULL CHECK (length(ciudad) > 0),
    pais        TEXT NOT NULL CHECK (length(pais) > 0),
    huso_iana   TEXT NOT NULL CHECK (length(huso_iana) > 0),
    lat         NUMERIC(9, 6) CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
    lon         NUMERIC(9, 6) CHECK (lon IS NULL OR lon BETWEEN -180 AND 180),
    altitud_m   NUMERIC(7, 1),
    fuente      TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id   BIGINT NOT NULL,
    recibido_en TIMESTAMPTZ NOT NULL
);

-- Torneo × temporada. `superficie` vive aquí, no en el torneo. `lunes_semana` es el lunes de la semana
-- en que TERMINA la edición (ver LEEME: regla RETRO). NULL en superficie/indoor = desconocido.
CREATE TABLE IF NOT EXISTS tenis.edicion (
    edicion_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    torneo_id    BIGINT NOT NULL REFERENCES tenis.torneo (torneo_id),
    temporada    INTEGER NOT NULL CHECK (temporada BETWEEN 1968 AND 2100),
    lunes_semana DATE NOT NULL CHECK (EXTRACT(ISODOW FROM lunes_semana) = 1),
    fecha_fin    DATE,
    -- Con fecha de fin conocida, `lunes_semana` ES el lunes de esa semana. Así un cargador no puede poner el lunes de
    -- INICIO en un torneo de dos semanas y hacer visibles (regla RETRO) resultados que aún no se habían jugado.
    CONSTRAINT edicion_lunes_coincide_con_fin
        CHECK (fecha_fin IS NULL OR lunes_semana = fecha_fin - (EXTRACT(ISODOW FROM fecha_fin)::int - 1)),
    sede_id      BIGINT REFERENCES tenis.sede (sede_id),
    superficie   TEXT CHECK (superficie IN ('clay', 'grass', 'hard', 'carpet')),
    indoor       BOOLEAN,
    formato      JSONB NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(formato) = 'object'),
    por_equipos  BOOLEAN NOT NULL DEFAULT false,
    fuente       TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recibo_id    BIGINT NOT NULL,
    recibido_en  TIMESTAMPTZ NOT NULL,
    UNIQUE (torneo_id, temporada, fuente, recibido_en)
);

-- Estado operativo MUTABLE (no es evidencia; sin disparadores de inmutabilidad).
-- cursor: último punto leído de cada recurso de cada colector.
CREATE TABLE IF NOT EXISTS tenis_op.cursor (
    fuente         TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    recurso        TEXT NOT NULL CHECK (length(recurso) > 0),
    valor          TEXT,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fuente, recurso)
);

-- presupuesto: peticiones usadas por proveedor y día. tope NULL = sin tope conocido (no es 0).
CREATE TABLE IF NOT EXISTS tenis_op.presupuesto (
    fuente  TEXT NOT NULL REFERENCES tenis.fuente (fuente),
    dia     DATE NOT NULL,
    tope    INTEGER CHECK (tope IS NULL OR tope >= 0),
    usadas  INTEGER NOT NULL DEFAULT 0 CHECK (usadas >= 0),
    PRIMARY KEY (fuente, dia)
);
