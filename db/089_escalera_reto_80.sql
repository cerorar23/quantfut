-- ============================================================================
-- 089 - Reto escalera al 80 % (decisión del usuario, 2026-10-28)
--
-- El reto ENTERO debe completarse al menos con `prob_objetivo` de
-- probabilidad: cada escalón exige p ≥ (prob_objetivo / ∏ p ganados)^(1/faltan)
-- (`publish/escalera.py`). NULL = reto creado con la regla anterior (rango de
-- cuota y el más probable), que termina con esa regla.
--
-- `dias_max`: el reto queda «expirado» a los `dias_max` días de crearse si no
-- se completó y no tiene escalón pendiente (regla de 7 días, misma fecha).
-- NULL = sin plazo (regla anterior).
--
-- Añadir una columna NULL no dispara el trigger de inmutabilidad (es de filas).
-- ============================================================================
BEGIN;

ALTER TABLE escalera_retos ADD COLUMN IF NOT EXISTS prob_objetivo REAL
    CHECK (prob_objetivo IS NULL OR (prob_objetivo > 0 AND prob_objetivo < 1));
COMMENT ON COLUMN escalera_retos.prob_objetivo IS
    'Probabilidad mínima de completar el reto entero; NULL = regla anterior (2026-10-08)';
ALTER TABLE escalera_retos ADD COLUMN IF NOT EXISTS dias_max SMALLINT
    CHECK (dias_max IS NULL OR dias_max > 0);
COMMENT ON COLUMN escalera_retos.dias_max IS
    'Días que puede seguir abierto desde que se crea; luego expira. NULL = sin plazo';

-- NBA y tenis (escalera_ext.py, archivo PropLine): el escalón no está en
-- `matches`; guarda el evento de PropLine tal como se eligió. Añadir columnas
-- con valor por defecto constante y CHECK no reescribe filas: los triggers de
-- inmutabilidad siguen intactos.
ALTER TABLE escalera_pasos ALTER COLUMN match_id DROP NOT NULL;
ALTER TABLE escalera_pasos ADD COLUMN IF NOT EXISTS deporte TEXT NOT NULL DEFAULT 'futbol'
    CHECK (deporte IN ('futbol', 'nba', 'tenis'));
ALTER TABLE escalera_pasos ADD COLUMN IF NOT EXISTS evento_id TEXT;
ALTER TABLE escalera_pasos ADD COLUMN IF NOT EXISTS evento_sport TEXT;
ALTER TABLE escalera_pasos ADD COLUMN IF NOT EXISTS evento_inicio TIMESTAMPTZ;
ALTER TABLE escalera_pasos ADD COLUMN IF NOT EXISTS evento_local TEXT;
ALTER TABLE escalera_pasos ADD COLUMN IF NOT EXISTS evento_visitante TEXT;
ALTER TABLE escalera_pasos DROP CONSTRAINT IF EXISTS escalera_pasos_evento_check;
ALTER TABLE escalera_pasos ADD CONSTRAINT escalera_pasos_evento_check CHECK (
    (deporte = 'futbol' AND match_id IS NOT NULL AND evento_id IS NULL)
    OR (deporte <> 'futbol' AND match_id IS NULL AND evento_id IS NOT NULL
        AND evento_sport IS NOT NULL AND evento_inicio IS NOT NULL
        AND evento_local IS NOT NULL AND evento_visitante IS NOT NULL));

-- Liquidación: en fútbol sigue el marcador (nulo ⇔ sin goles). En NBA y tenis la
-- da la calificación de PropLine de la casa del escalón, sin marcador.
ALTER TABLE escalera_resultados ADD COLUMN IF NOT EXISTS fuente TEXT NOT NULL DEFAULT 'partido'
    CHECK (fuente IN ('partido', 'propline'));
DO $$
DECLARE c TEXT;
BEGIN
    FOR c IN SELECT conname FROM pg_constraint
             WHERE conrelid = 'escalera_resultados'::regclass AND contype = 'c'
               AND pg_get_constraintdef(oid) LIKE '%home_goals IS NULL%'
               AND conname <> 'escalera_resultados_goles_check'
    LOOP
        EXECUTE format('ALTER TABLE escalera_resultados DROP CONSTRAINT %I', c);
    END LOOP;
END $$;
ALTER TABLE escalera_resultados DROP CONSTRAINT IF EXISTS escalera_resultados_goles_check;
ALTER TABLE escalera_resultados ADD CONSTRAINT escalera_resultados_goles_check CHECK (
    (fuente = 'partido' AND (outcome = 'void') = (home_goals IS NULL))
    OR (fuente = 'propline' AND home_goals IS NULL AND away_goals IS NULL));

COMMIT;
