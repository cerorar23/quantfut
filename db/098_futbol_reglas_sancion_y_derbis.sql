-- 098: dos tablas pequeñas que piden los estudios del rediseño de tarjetas y rotación y que no vienen de ninguna API.
--
--  * `futbol.regla_sancion`: con cuántas amarillas acumuladas se suspende a un jugador en cada liga (Kruse-Maennig:
--    un jugador a una amarilla del umbral cambia su conducta y su probabilidad de ser baja; A5 del rediseño).
--  * `futbol.derbi`: pares de equipos de una liga que son derbi (+0,20 amarillas por equipo en Kruse-Maennig).
--
-- Los umbrales se MIDEN con los datos propios (moda de las amarillas acumuladas de los jugadores sancionados) y se
-- contrastan con lo que se sabe del reglamento; `verificada` queda en falso hasta confirmarla contra el reglamento
-- oficial de cada liga. Los derbis salen de una regla automática (misma ciudad del estadio) más una lista manual de
-- rivalidades que la distancia no capta.
BEGIN;

CREATE TABLE IF NOT EXISTS futbol.regla_sancion (
    liga        TEXT NOT NULL,
    desde       TEXT NOT NULL DEFAULT '0000',      -- temporada AABB desde la que rige
    tipo        TEXT NOT NULL CHECK (tipo IN ('fijo', 'por_jornada', 'sin_acumulacion')),
    amarillas   SMALLINT,                          -- umbral (tipo fijo); se repite en cada ciclo
    detalle     TEXT,                              -- tipo por_jornada: «5 hasta la jornada 19, 10 hasta la 32, 15 hasta la 37»
    fuente      TEXT NOT NULL CHECK (fuente IN ('observado', 'reglamento')),
    muestra     INTEGER,                           -- sanciones observadas que respaldan el valor
    verificada  BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (liga, desde)
);

-- Medido el 1-nov-2026: amarillas acumuladas en la liga y temporada antes de cada baja por sanción.
-- Solo se anotan las ligas donde la moda domina; las demás (Ligue 1: 4 y 5 empatadas; Argentina) quedan sin fila
-- hasta confirmarlas con el reglamento, y la Liga MX no suspende por acumulación.
INSERT INTO futbol.regla_sancion (liga, tipo, amarillas, detalle, fuente, muestra, verificada) VALUES
    ('it.serie_a',    'fijo', 5, NULL, 'observado', 204, false),   -- 49 % de las sanciones a la 5.ª; el resto, rojas y el 2.º ciclo
    ('de.bundesliga', 'fijo', 5, NULL, 'observado',  93, false),   -- 51 %
    ('es.laliga',     'fijo', 5, NULL, 'observado', 259, false),   -- 30 %; el ciclo se repite (el 10 aparece en el 6 %)
    ('nl.eredivisie', 'fijo', 5, NULL, 'observado',  82, false),   -- 43 %
    ('pt.primeira',   'fijo', 5, NULL, 'observado', 138, false),   -- 44 %
    ('br.serie_a',    'fijo', 3, NULL, 'observado', 224, false),   -- 51 %; coincide con el reglamento de la CBF
    ('gb.premier_league', 'por_jornada', NULL,
        '5 amarillas antes de la jornada 19, 10 antes de la 32 y 15 antes de la 37 (1, 2 y 3 partidos)',
        'reglamento', 297, false),   -- la medición no lo delata: solo el 19 % está en 5 y el 4 % en 10
    ('mx.liga_mx',    'sin_acumulacion', NULL, '72 % de las sanciones ocurren con 0 amarillas: son rojas', 'observado', 94, false)
ON CONFLICT (liga, desde) DO NOTHING;

-- Amarillas acumuladas de un jugador en la liga y temporada antes de un instante (para A5 y tarjetas).
CREATE OR REPLACE FUNCTION futbol.amarillas_acumuladas(p_jugador BIGINT, p_liga TEXT, p_temporada TEXT, p_antes TIMESTAMPTZ)
RETURNS INTEGER LANGUAGE sql STABLE AS $f$
    SELECT count(*)::integer
      FROM futbol.dato d JOIN matches m USING (match_id)
     WHERE d.tipo = 'incidencia' AND d.subtipo = 'card' AND d.clase = 'yellow' AND d.jugador_id = p_jugador
       AND m.league_id = p_liga AND m.season = p_temporada AND m.kickoff_utc < p_antes
$f$;

-- ── Derbis ───────────────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS futbol.derbi (
    liga     TEXT NOT NULL,                          -- liga doméstica (teams.league_id)
    equipo_a BIGINT NOT NULL,
    equipo_b BIGINT NOT NULL CHECK (equipo_a < equipo_b),
    origen   TEXT NOT NULL CHECK (origen IN ('ciudad', 'manual')),
    nombre   TEXT,
    PRIMARY KEY (liga, equipo_a, equipo_b)
);

-- Equipo de una liga cuyo nombre canónico case con el patrón; NULL si no hay exactamente uno.
CREATE OR REPLACE FUNCTION futbol.equipo_por_nombre(p_liga TEXT, p_patron TEXT) RETURNS BIGINT
LANGUAGE sql STABLE AS $f$
    SELECT CASE WHEN count(*) = 1 THEN min(team_id) END FROM teams WHERE league_id = p_liga AND canonical_name ~* p_patron
$f$;

CREATE OR REPLACE FUNCTION futbol.cargar_derbis() RETURNS TABLE (origen TEXT, pares BIGINT)
LANGUAGE plpgsql AS $f$
#variable_conflict use_column
BEGIN
    -- Regla automática: dos equipos de la misma liga cuyo estadio de local está en la misma ciudad.
    INSERT INTO futbol.derbi (liga, equipo_a, equipo_b, origen, nombre)
    WITH sede AS (
        SELECT DISTINCT ON (t.team_id) t.team_id, t.league_id, e.estadio_ciudad AS ciudad
          FROM teams t
          JOIN matches m ON m.home_team_id = t.team_id
          JOIN futbol.dato e ON e.match_id = m.match_id AND e.tipo = 'estadio' AND e.estadio_ciudad IS NOT NULL
         WHERE m.league_id = t.league_id          -- solo partidos de su liga doméstica
         GROUP BY t.team_id, t.league_id, e.estadio_ciudad
         ORDER BY t.team_id, count(*) DESC
    )
    SELECT a.league_id, a.team_id, b.team_id, 'ciudad', a.ciudad
      FROM sede a JOIN sede b ON a.league_id = b.league_id AND a.ciudad = b.ciudad AND a.team_id < b.team_id
     -- solo si la ciudad tiene exactamente dos clubes de la liga: con más (Londres, Buenos Aires, Estambul) casi
     -- todos los pares dejarían de ser derbis, y esos casos van en la lista manual
     WHERE (SELECT count(*) FROM sede c WHERE c.league_id = a.league_id AND c.ciudad = a.ciudad) = 2
    ON CONFLICT (liga, equipo_a, equipo_b) DO NOTHING;
    GET DIAGNOSTICS pares = ROW_COUNT; origen := 'ciudad'; RETURN NEXT;

    -- Rivalidades que la ciudad no capta. Cada fila se resuelve por nombre y se omite si no es único.
    INSERT INTO futbol.derbi (liga, equipo_a, equipo_b, origen, nombre)
    SELECT l, least(a, b), greatest(a, b), 'manual', n
      FROM (SELECT v.l, v.n, futbol.equipo_por_nombre(v.l, v.pa) AS a, futbol.equipo_por_nombre(v.l, v.pb) AS b
              FROM (VALUES
                ('es.laliga',         '^Barcelona$',                    '^Real Madrid$',        'El Clásico'),
                ('gb.premier_league', '^(Man(chester)? )?(Utd|United)$', '^Liverpool$',          'Manchester United–Liverpool'),
                ('it.serie_a',        '^Inter$',                        '^Juventus$',           'Derby d''Italia'),
                ('it.serie_a',        '^Milan$',                        '^Juventus$',           'Juventus–Milan'),
                ('de.bundesliga',     '^Bayern',                        '^Dortmund$',           'Der Klassiker'),
                ('de.bundesliga',     '^Dortmund$',                     '^Schalke',             'Revierderby'),
                ('de.bundesliga',     'Gladbach|Monchengladbach',       '^FC Koln$',            'Rheinderby'),
                ('fr.ligue_1',        '^Paris SG$',                     '^Marseille$',          'Le Classique'),
                ('fr.ligue_1',        '^Lyon$',                         '^St Etienne$',         'Derby rhodanien'),
                ('pt.primeira',       '^Benfica$',                      '^Porto$',              'O Clássico'),
                ('pt.primeira',       '^Porto$',                        '^Sp Lisbon$',          'Porto–Sporting'),
                ('nl.eredivisie',     '^Ajax$',                         '^Feyenoord$',          'De Klassieker'),
                ('nl.eredivisie',     '^Ajax$',                         '^PSV',                 'Ajax–PSV'),
                ('mx.liga_mx',        '^Club America$',                 '^Guadalajara',         'Clásico Nacional'),
                ('mx.liga_mx',        '^Club America$',                 '^UNAM Pumas$',         'Clásico Capitalino'),
                ('mx.liga_mx',        '^Club America$',                 '^Cruz Azul$',          'Clásico Joven'),
                -- ciudades con más de dos clubes de la liga
                ('es.laliga',         '^Real Madrid$',                  '^Ath Madrid$',         'Derbi madrileño'),
                ('gb.premier_league', '^Arsenal$',                      '^Tottenham$',          'Derbi del norte de Londres'),
                ('gb.premier_league', '^Arsenal$',                      '^Chelsea$',            'Arsenal–Chelsea'),
                ('gb.premier_league', '^Chelsea$',                      '^Tottenham$',          'Chelsea–Tottenham'),
                ('br.serie_a',        '^Flamengo',                      '^Fluminense$',         'Fla-Flu'),
                ('br.serie_a',        '^Flamengo',                      '^Vasco$',              'Clássico dos Milhões'),
                ('br.serie_a',        '^Corinthians$',                  '^Palmeiras$',          'Derby Paulista'),
                ('br.serie_a',        '^Corinthians$',                  '^Sao Paulo$',          'Majestoso'),
                ('br.serie_a',        '^Palmeiras$',                    '^Sao Paulo$',          'Choque-Rei'),
                ('ar.primera',        '^Boca Juniors$',                 '^River Plate$',        'Superclásico')
              ) AS v(l, pa, pb, n)) s
     WHERE a IS NOT NULL AND b IS NOT NULL AND a <> b
    ON CONFLICT (liga, equipo_a, equipo_b) DO UPDATE SET origen = 'manual', nombre = EXCLUDED.nombre;
    GET DIAGNOSTICS pares = ROW_COUNT; origen := 'manual'; RETURN NEXT;
END
$f$;

-- ¿Es derbi el partido? (por los dos equipos y la liga doméstica de cada uno)
CREATE OR REPLACE FUNCTION futbol.es_derbi(p_local BIGINT, p_visita BIGINT) RETURNS BOOLEAN
LANGUAGE sql STABLE AS $f$
    SELECT EXISTS (SELECT 1 FROM futbol.derbi WHERE equipo_a = least(p_local, p_visita) AND equipo_b = greatest(p_local, p_visita))
$f$;

COMMIT;
