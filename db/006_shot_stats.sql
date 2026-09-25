-- ============================================================================
-- Estadísticas derivadas de los datos tiro a tiro de worldfootballR_data.
--
-- El esquema ya tenía home_shots / home_shots_target, pero solo los rellenaba
-- football-data.co.uk y SOLO en su formato principal. Las tres ligas
-- latinoamericanas (formato "extra") se quedaban con esas columnas a NULL en
-- el 100% de sus partidos. Los datos tiro a tiro permiten derivarlas.
--
-- PSxG (post-shot expected goals) es información NUEVA, no una columna que
-- faltara por rellenar:
--
--   xG    mide la calidad de la ocasión ANTES del disparo (posición, tipo de
--         jugada, parte del cuerpo).
--   PSxG  mide la calidad del disparo YA EJECUTADO, es decir, incorpora dónde
--         fue colocado el balón. Solo existe para remates a puerta.
--
-- SEÑAL VÁLIDA:
--   goles - PSxG  ≈ rendimiento del portero rival. Las dos magnitudes se
--   refieren a la misma población (remates que llegaron a puerta), así que la
--   resta significa algo. Revierte fuertemente a la media, que es lo que la
--   hace útil: un equipo que lleva meses marcando por encima de su PSxG está
--   viviendo de una racha, no de una habilidad.
--
-- CUIDADO, ESTA RESTA NO SIGNIFICA LO QUE PARECE:
--   home_psxg - home_xg   NO es "calidad de definición".
--   `home_psxg` suma solo los remates A PUERTA; `home_xg` suma TODOS los
--   remates, incluidos los que se van fuera y los bloqueados. Son poblaciones
--   distintas, así que la diferencia sale sistemáticamente negativa en todas
--   las ligas (medido: entre -0.006 y -0.084) y eso no dice nada sobre los
--   delanteros. Para medir definición de verdad hace falta el xG restringido
--   a los remates a puerta, que esta tabla no guarda.
-- ============================================================================

ALTER TABLE matches
    ADD COLUMN IF NOT EXISTS home_psxg          REAL,
    ADD COLUMN IF NOT EXISTS away_psxg          REAL,
    -- Distancia media de remate en yardas. Un equipo que dispara de lejos
    -- acumula muchos tiros de bajo valor: distingue volumen de peligro.
    ADD COLUMN IF NOT EXISTS home_shot_distance REAL,
    ADD COLUMN IF NOT EXISTS away_shot_distance REAL;

COMMENT ON COLUMN matches.home_psxg IS
    'Suma de PSxG (xG post-disparo) del local. Solo remates a puerta.';
COMMENT ON COLUMN matches.away_psxg IS
    'Suma de PSxG (xG post-disparo) del visitante. Solo remates a puerta.';
COMMENT ON COLUMN matches.home_shot_distance IS
    'Distancia media de los remates del local, en yardas.';
COMMENT ON COLUMN matches.away_shot_distance IS
    'Distancia media de los remates del visitante, en yardas.';
