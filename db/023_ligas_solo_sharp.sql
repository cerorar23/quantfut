-- ============================================================================
-- 023 - LaLiga 2 y Serie B en modo "solo sharp"
--
-- Entran por el criterio "casa blanda contra precio sharp", que no necesita el
-- modelo: backtest 2021/22-2024/25, 1X2, mejor de Bet365/William Hill/1xBet a
-- umbral 2%, valor al cierre de Pinnacle sin margen:
--     LaLiga 2  1,64 picks/semana  +3,91%  IC95 [2,5, 5,3]
--     Serie B   1,43 picks/semana  +5,06%  IC95 [3,3, 7,1]
-- Pinnacle en The Odds API comprobado el 2026-09-25: 11/12 y 10/10 partidos.
--
-- `model_enabled = FALSE` las deja FUERA de todo lo que alimenta al modelo o a
-- la cadena sellada: predicción diaria (se sellaría una predicción sin base
-- para equipos que el modelo no conoce), entrenamiento, alineaciones, bajas y
-- xG. DENTRO: calendario, resultados, cuotas de API-Football, sombra del
-- criterio y cierre de Pinnacle de The Odds API (solo 1X2).
--
-- `fd_code` va a NULL a propósito: `history_fd.backfill` carga toda liga con
-- código, y el histórico de football-data escribe los nombres a su manera. En
-- una liga que no alimenta al modelo no aporta nada y mezclaría dos fuentes
-- de nombres en equipos recién creados. Los backtests pasan SP2/I2 a mano.
-- ============================================================================
BEGIN;

ALTER TABLE leagues ADD COLUMN IF NOT EXISTS model_enabled BOOLEAN NOT NULL DEFAULT TRUE;
COMMENT ON COLUMN leagues.model_enabled IS
  'FALSE: la liga solo alimenta el criterio sharp (calendario, resultados, '
  'cuotas, sombra). Nunca entra en el entrenamiento ni en la predicción '
  'diaria sellada.';

INSERT INTO leagues (league_id, country, name, tier, fd_code, fd_extra, odds_api_key,
                     cross_league, active, api_football_id, season_style, model_enabled)
VALUES
  ('es.laliga2', 'Spain', 'LaLiga 2', 2, NULL, FALSE, 'soccer_spain_segunda_division',
   FALSE, TRUE, 141, 'european', FALSE),
  ('it.serie_b', 'Italy', 'Serie B',  2, NULL, FALSE, 'soccer_italy_serie_b',
   FALSE, TRUE, 136, 'european', FALSE)
ON CONFLICT (league_id) DO NOTHING;

COMMIT;
