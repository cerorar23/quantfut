-- 115: avisos push por deporte (15-nov-2026, F7c del rediseño CyberCore).
--
-- `push_sports` = deportes de los que la cuenta quiere recibir avisos push. NULL = todos (cuentas
-- existentes y apps antiguas, que no lo envían: nada cambia para ellas). Lista vacía = ninguno.
-- `account_notifications.sport` = deporte del aviso; NULL = aviso general, que no se filtra.
ALTER TABLE firebase_preferences ADD COLUMN IF NOT EXISTS push_sports TEXT[];
ALTER TABLE firebase_preferences DROP CONSTRAINT IF EXISTS firebase_preferences_push_sports_check;
ALTER TABLE firebase_preferences ADD CONSTRAINT firebase_preferences_push_sports_check
    CHECK (push_sports IS NULL OR push_sports <@ ARRAY['futbol','nba','tenis']::TEXT[]);
ALTER TABLE account_notifications ADD COLUMN IF NOT EXISTS sport TEXT
    CHECK (sport IS NULL OR sport IN ('futbol','nba','tenis'));
