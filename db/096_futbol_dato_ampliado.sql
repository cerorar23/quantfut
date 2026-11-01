-- 096: `futbol.dato` cubre el partido COMPLETO del scraper de SofaScore (db/094 guardaba lo esencial).
--
-- Medido el 1-nov-2026 con Fulham-Bournemouth (12 bloques): de 82 estadísticas por jugador se guardaban 34, de 46
-- de equipo 28 y solo el periodo completo, faltaban campos de tiros e incidencias, la asistencia y tres bloques
-- enteros (momentum, posiciones medias). Esta migración añade las columnas y los dos tipos que faltan:
--   * jugador: xG/xGOT del jugador, pases clave, conducciones y progresión, distancias de carrera, errores,
--     penaltis, regates, pases por mitad del campo, estadísticas de portero y los índices de valor normalizados;
--   * equipo: las 12 claves que faltaban; por periodo (evento 0 = partido, 1 = 1.ª parte, 2 = 2.ª parte);
--   * tiro: coordenadas del bloqueo, tipo de gol, portero, tiempo añadido y segundos del periodo;
--   * incidencia: lesión, duración del descuento, anulada, texto y la red de pases del gol (JSONB);
--   * tipo `momentum` (presión por minuto) y tipo `posicion` (posición media de cada jugador).
-- Los bloques `h2h`, `pregame_form` y `team_streaks` siguen fuera a propósito: no son verificables como previos al
-- partido (point-in-time). `best_players` y `player_ranking` los calcula el propio descargador a partir de lo ya
-- guardado. Los originales completos siguen como archivos.
--
-- Cuando un partido ya lo posee otra fuente de mejor prioridad (p. ej. FotMob), SofaScore COMPLETA solo las
-- columnas que esa fila tiene vacías y deja constancia en `fuente_extra`; nunca pisa lo que la fuente dueña dio.
BEGIN;

ALTER TABLE futbol.dato DROP CONSTRAINT IF EXISTS dato_tipo_check;
ALTER TABLE futbol.dato ADD CONSTRAINT dato_tipo_check CHECK (tipo IN
    ('jugador','equipo','baja','alineacion','entrenador','contexto','tiro','incidencia','clima','estadio',
     'momentum','posicion'));

ALTER TABLE futbol.dato ADD COLUMN IF NOT EXISTS fuente_extra TEXT REFERENCES futbol.fuente(fuente);

-- jugador (y, donde mide lo mismo, equipo)
ALTER TABLE futbol.dato
    ADD COLUMN IF NOT EXISTS pases_clave SMALLINT,
    ADD COLUMN IF NOT EXISTS tiros_totales SMALLINT,
    ADD COLUMN IF NOT EXISTS conducciones SMALLINT,
    ADD COLUMN IF NOT EXISTS conducciones_progresivas SMALLINT,
    ADD COLUMN IF NOT EXISTS distancia_conduccion REAL,
    ADD COLUMN IF NOT EXISTS mejor_conduccion REAL,
    ADD COLUMN IF NOT EXISTS progresion_total REAL,
    ADD COLUMN IF NOT EXISTS distancia_progresiva REAL,
    ADD COLUMN IF NOT EXISTS km_alta_velocidad REAL,
    ADD COLUMN IF NOT EXISTS km_carrera REAL,
    ADD COLUMN IF NOT EXISTS km_esprint REAL,
    ADD COLUMN IF NOT EXISTS error_gol SMALLINT,
    ADD COLUMN IF NOT EXISTS error_tiro SMALLINT,
    ADD COLUMN IF NOT EXISTS penaltis_ganados SMALLINT,
    ADD COLUMN IF NOT EXISTS penaltis_cometidos SMALLINT,
    ADD COLUMN IF NOT EXISTS penaltis_parados SMALLINT,
    ADD COLUMN IF NOT EXISTS penaltis_enfrentados SMALLINT,
    ADD COLUMN IF NOT EXISTS goles_propia SMALLINT,
    ADD COLUMN IF NOT EXISTS palos SMALLINT,
    ADD COLUMN IF NOT EXISTS despejes_linea SMALLINT,
    ADD COLUMN IF NOT EXISTS ultimo_hombre SMALLINT,
    ADD COLUMN IF NOT EXISTS bloqueos SMALLINT,
    ADD COLUMN IF NOT EXISTS regates_intentados SMALLINT,
    ADD COLUMN IF NOT EXISTS regates_ganados SMALLINT,
    ADD COLUMN IF NOT EXISTS regates_perdidos SMALLINT,
    ADD COLUMN IF NOT EXISTS perdidas_balon SMALLINT,
    ADD COLUMN IF NOT EXISTS toques_fallidos SMALLINT,
    ADD COLUMN IF NOT EXISTS pases_propio_campo SMALLINT,
    ADD COLUMN IF NOT EXISTS pases_propio_campo_acertados SMALLINT,
    ADD COLUMN IF NOT EXISTS pases_campo_rival SMALLINT,
    ADD COLUMN IF NOT EXISTS pases_campo_rival_acertados SMALLINT,
    ADD COLUMN IF NOT EXISTS salidas_portero SMALLINT,
    ADD COLUMN IF NOT EXISTS salidas_portero_acertadas SMALLINT,
    ADD COLUMN IF NOT EXISTS paradas_dentro_area SMALLINT,
    ADD COLUMN IF NOT EXISTS centros_no_atrapados SMALLINT,
    ADD COLUMN IF NOT EXISTS atrapadas_altas SMALLINT,
    ADD COLUMN IF NOT EXISTS punos SMALLINT,
    ADD COLUMN IF NOT EXISTS valor_parada REAL,
    ADD COLUMN IF NOT EXISTS valor_defensivo REAL,
    ADD COLUMN IF NOT EXISTS valor_regate REAL,
    ADD COLUMN IF NOT EXISTS valor_porteria REAL,
    ADD COLUMN IF NOT EXISTS valor_pase REAL,
    ADD COLUMN IF NOT EXISTS valor_tiro REAL,
    ADD COLUMN IF NOT EXISTS nota_alternativa REAL;

-- equipo (las 12 claves que faltaban; `palos` y `atrapadas_altas` comparten columna con jugador)
ALTER TABLE futbol.dato
    ADD COLUMN IF NOT EXISTS pases_filtrados SMALLINT,
    ADD COLUMN IF NOT EXISTS pct_duelos_aereos REAL,
    ADD COLUMN IF NOT EXISTS paradas_estiradas SMALLINT,
    ADD COLUMN IF NOT EXISTS pct_regates REAL,
    ADD COLUMN IF NOT EXISTS pct_duelos REAL,
    ADD COLUMN IF NOT EXISTS errores_tiro SMALLINT,
    ADD COLUMN IF NOT EXISTS fase_ultimo_tercio SMALLINT,
    ADD COLUMN IF NOT EXISTS faltas_ultimo_tercio SMALLINT,
    ADD COLUMN IF NOT EXISTS pct_duelos_suelo REAL,
    ADD COLUMN IF NOT EXISTS pct_entradas REAL;

-- tiro
ALTER TABLE futbol.dato
    ADD COLUMN IF NOT EXISTS bloqueo_x REAL,
    ADD COLUMN IF NOT EXISTS bloqueo_y REAL,
    ADD COLUMN IF NOT EXISTS bloqueo_z REAL,
    ADD COLUMN IF NOT EXISTS tipo_gol TEXT,
    ADD COLUMN IF NOT EXISTS portero_id BIGINT,
    ADD COLUMN IF NOT EXISTS portero TEXT,
    ADD COLUMN IF NOT EXISTS segundos_periodo INTEGER;

-- incidencia
ALTER TABLE futbol.dato
    ADD COLUMN IF NOT EXISTS lesion BOOLEAN,
    ADD COLUMN IF NOT EXISTS duracion SMALLINT,
    ADD COLUMN IF NOT EXISTS anulada BOOLEAN,
    ADD COLUMN IF NOT EXISTS texto TEXT,
    ADD COLUMN IF NOT EXISTS red_pases JSONB;       -- pases que llevaron al gol: [jugador, tipo, min, x, y, x_fin, y_fin]

-- momentum y posicion
ALTER TABLE futbol.dato
    ADD COLUMN IF NOT EXISTS minuto_decimal REAL,
    ADD COLUMN IF NOT EXISTS momentum REAL,
    ADD COLUMN IF NOT EXISTS pos_x REAL,
    ADD COLUMN IF NOT EXISTS pos_y REAL,
    ADD COLUMN IF NOT EXISTS puntos INTEGER;

-- `dispossessed` es el mismo dato en jugador y en equipo: una sola columna (`perdidas_balon`). `perdidas` queda
-- para `possessionLostCtrl` del jugador.
UPDATE futbol.dato SET perdidas_balon = perdidas, perdidas = NULL WHERE tipo = 'equipo' AND perdidas IS NOT NULL;

INSERT INTO futbol.prioridad_entidad (entidad, fuente, prioridad) VALUES
    ('momentum', 'sofascore', 1), ('posicion', 'sofascore', 1)
ON CONFLICT (entidad, fuente) DO NOTHING;

COMMIT;
