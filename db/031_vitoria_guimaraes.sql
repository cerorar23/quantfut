-- Guimarães ('Vitória SC' en API-Football desde septiembre de 2026) se
-- resolvía como el Vitória BRASILEÑO: el alias global de API-Football
-- 'Vitoria' (Brasil) y 'Vitória SC' se normalizan igual. Desde este cambio
-- `normalize.match_team` acota los alias al país de la liga.
--
-- Datos corregidos, cada uno solo si sigue en el estado erróneo:
--   * alias propio de API-Football para Guimarães;
--   * el único partido afectado (Benfica–Guimarães, 11-oct): sin
--     predicciones, cuotas ni ofertas en sombra. El match_id conserva
--     'vitoria' en el texto: es un identificador, no un nombre visible;
--   * nombre, id de API-Football y fila de clasificación que la pasada de
--     Portugal escribió sobre el Vitória brasileño.
BEGIN;

INSERT INTO team_aliases (alias, source, team_id)
VALUES ('Vitória SC', 'api_football', 77425)
ON CONFLICT (alias, source) DO NOTHING;

UPDATE matches SET away_team_id = 77425
WHERE match_id = 'pt.primeira:2627:benfica-vitoria:20261011'
  AND away_team_id = 39917;

UPDATE teams SET display_name = NULL, af_team_id = NULL
WHERE team_id = 39917 AND af_team_id = 224;

DELETE FROM standings WHERE league_id = 'pt.primeira' AND team_id = 39917;

COMMIT;
