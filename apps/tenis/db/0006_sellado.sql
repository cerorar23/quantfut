-- 0006: sellado de pronósticos con cadena de hashes (plan técnico tenis, §H.3).
-- Solo-anexar, como el resto de la evidencia. `tenis.sellar_pronostico` es la única vía de escritura del motor.

CREATE TABLE IF NOT EXISTS tenis.artefacto (
    artefacto_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sha256             TEXT NOT NULL UNIQUE CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    tipo               TEXT NOT NULL CHECK (length(tipo) > 0),
    version_modelo     TEXT NOT NULL CHECK (length(version_modelo) > 0),
    informe_compuertas JSONB NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(informe_compuertas) = 'object'),
    registrado_en      TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- Activación de un artefacto. La vuelta atrás es OTRA fila que apunta al anterior (plan §H.4).
CREATE TABLE IF NOT EXISTS tenis.artefacto_activo (
    activo_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sha256           TEXT NOT NULL REFERENCES tenis.artefacto (sha256),
    activado_en      TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    aprobado_en_chat TEXT NOT NULL CHECK (length(trim(aprobado_en_chat)) > 0),
    imagen           TEXT NOT NULL CHECK (imagen ~ '^tenis-motor:[A-Za-z0-9._-]+$')
);

-- Sello. `hash_previo` enlaza con el último sello (génesis = 64 ceros). UNIQUE(hash_previo) impide bifurcaciones.
-- Un partido se sella con una sola fila por versión y corte; `corte <= sellado_en` (nunca datos del futuro).
CREATE TABLE IF NOT EXISTS tenis.pronostico (
    pronostico_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    partido_id         BIGINT NOT NULL REFERENCES tenis.partido (partido_id),
    version_modelo     TEXT NOT NULL CHECK (length(version_modelo) > 0),
    version_datos      TEXT NOT NULL CHECK (length(version_datos) > 0),
    corte              TIMESTAMPTZ NOT NULL,
    sellado_en         TIMESTAMPTZ NOT NULL,
    entradas           JSONB NOT NULL CHECK (jsonb_typeof(entradas) = 'object'),
    distribucion       JSONB NOT NULL CHECK (jsonb_typeof(distribucion) = 'object'),
    referencia_mercado JSONB NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(referencia_mercado) = 'object'),
    hash_previo        TEXT NOT NULL UNIQUE CHECK (hash_previo ~ '^[0-9a-f]{64}$'),
    hash               TEXT NOT NULL UNIQUE CHECK (hash ~ '^[0-9a-f]{64}$'),
    UNIQUE (partido_id, version_modelo, corte),
    CHECK (corte <= sellado_en)
);

SELECT tenis.marcar_inmutable('artefacto');
SELECT tenis.marcar_inmutable('artefacto_activo');
SELECT tenis.marcar_inmutable('pronostico');

-- Serialización canónica (base de la huella): JSON compacto, claves de objeto ordenadas por código
-- (COLLATE "C"), arrays en su orden, escalares tal como los escribe jsonb (texto). Los decimales de las
-- probabilidades deben llegar ya redondeados a 6 cifras (lo exige el contrato Python, no esta función).
CREATE OR REPLACE FUNCTION tenis.json_canonico(j JSONB) RETURNS TEXT
LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
    CASE jsonb_typeof(j)
        WHEN 'object' THEN
            RETURN '{' || coalesce((SELECT string_agg(to_json(e.k)::text || ':' || tenis.json_canonico(e.v), ','
                                                      ORDER BY e.k COLLATE "C")
                                    FROM jsonb_each(j) AS e(k, v)), '') || '}';
        WHEN 'array' THEN
            RETURN '[' || coalesce((SELECT string_agg(tenis.json_canonico(a.v), ',' ORDER BY a.ord)
                                    FROM jsonb_array_elements(j) WITH ORDINALITY AS a(v, ord)), '') || ']';
        ELSE
            RETURN j::text;
    END CASE;
END $$;

-- Sella un pronóstico. Orden: candado asesor de la cadena -> reloj de la base -> comprobaciones -> inserción.
-- Huella = sha256(UTF-8) de json_canonico([partido_id, version_modelo, version_datos, corte, sellado_en,
--          entradas, distribucion, referencia_mercado, hash_previo]); corte y sellado_en en UTC con 6 decimales
--          y sufijo Z, p. ej. 2099-01-01T00:00:00.000000Z.
-- Rechaza: corte posterior al sellado; partido sin inicio programado conocido o con horas no fijas
-- (inicio NULL); sellado a partir del inicio más temprano conocido (G-tiempo).
CREATE OR REPLACE FUNCTION tenis.sellar_pronostico(
    p_partido_id       BIGINT,
    p_version_modelo   TEXT,
    p_version_datos    TEXT,
    p_corte            TIMESTAMPTZ,
    p_entradas         JSONB,
    p_distribucion     JSONB,
    p_referencia       JSONB DEFAULT '{}'::jsonb
) RETURNS TEXT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = tenis, pg_temp AS $$
DECLARE
    v_inicio      TIMESTAMPTZ;
    v_sin_inicio  BIGINT;
    v_previo      TEXT;
    v_sellado     TIMESTAMPTZ;
    v_canon       TEXT;
    v_hash        TEXT;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('tenis.pronostico'));
    v_sellado := clock_timestamp();

    IF p_corte > v_sellado THEN
        RAISE EXCEPTION 'corte posterior al sellado: no se sella con datos del futuro';
    END IF;

    SELECT min(inicio_programado_utc), count(*) FILTER (WHERE inicio_programado_utc IS NULL)
    INTO v_inicio, v_sin_inicio
    FROM tenis.programa WHERE partido_id = p_partido_id;

    IF v_inicio IS NULL OR v_sin_inicio > 0 THEN
        RAISE EXCEPTION 'partido % sin inicio programado conocido: no se sella', p_partido_id;
    END IF;
    IF v_sellado >= v_inicio THEN
        RAISE EXCEPTION 'sellado tardio del partido %: el inicio programado ya llego', p_partido_id;
    END IF;

    SELECT hash INTO v_previo FROM tenis.pronostico ORDER BY pronostico_id DESC LIMIT 1;
    v_previo := coalesce(v_previo, repeat('0', 64));

    v_canon := tenis.json_canonico(jsonb_build_array(
        p_partido_id, p_version_modelo, p_version_datos,
        to_char(p_corte AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
        to_char(v_sellado AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
        p_entradas, p_distribucion, p_referencia, v_previo));
    v_hash := encode(sha256(convert_to(v_canon, 'UTF8')), 'hex');

    INSERT INTO tenis.pronostico (partido_id, version_modelo, version_datos, corte, sellado_en,
                                  entradas, distribucion, referencia_mercado, hash_previo, hash)
    VALUES (p_partido_id, p_version_modelo, p_version_datos, p_corte, v_sellado,
            p_entradas, p_distribucion, p_referencia, v_previo, v_hash);
    RETURN v_hash;
END $$;

-- Permisos: el motor solo ejecuta el sellado; la API y la lectura ven los sellos.
REVOKE ALL ON FUNCTION tenis.sellar_pronostico(BIGINT, TEXT, TEXT, TIMESTAMPTZ, JSONB, JSONB, JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION tenis.json_canonico(JSONB) FROM PUBLIC;

DO $$
BEGIN
    IF (SELECT count(*) FROM pg_roles
        WHERE rolname IN ('tenis_captura', 'tenis_motor', 'tenis_api', 'tenis_lectura')) = 4 THEN
        GRANT EXECUTE ON FUNCTION tenis.sellar_pronostico(BIGINT, TEXT, TEXT, TIMESTAMPTZ, JSONB, JSONB, JSONB)
            TO tenis_motor;
        GRANT SELECT ON tenis.artefacto, tenis.artefacto_activo, tenis.pronostico TO tenis_api, tenis_lectura;
        GRANT SELECT ON tenis.artefacto, tenis.artefacto_activo, tenis.pronostico TO tenis_motor;
    ELSE
        RAISE NOTICE 'roles tenis_* ausentes: se omiten los GRANT de 0006';
    END IF;
END $$;
