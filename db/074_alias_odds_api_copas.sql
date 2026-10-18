-- 074: nombres del histórico de The Odds API para clubes de nuestras ligas que juegan Champions y Europa League.
--
-- El endpoint histórico usa 'Bayern München', 'Internazionale Milano', 'LOSC Lille' y 'Young Boys'; los alias de
-- `odds_api` tenían las otras variantes, así que esos partidos no emparejaban y quedaban sin cierre de Pinnacle.
-- Los otros 30 nombres sin alias de esos snapshots son clubes de ligas que no cubrimos y no se registran
-- (las copas no dan de alta equipos; ver CLAUDE.md). Idempotente.
BEGIN;

INSERT INTO correcciones_identidad (migracion, tabla, clave, campo, antes, despues, motivo)
SELECT '074', 'team_aliases', v.alias || '|odds_api', 'team_id', NULL, v.tid::text,
       'nombre del histórico de The Odds API en Champions/Europa League'
FROM (VALUES ('Bayern München', 61440), ('Internazionale Milano', 12102),
             ('LOSC Lille', 68864), ('Young Boys', 85077)) v(alias, tid)
WHERE NOT EXISTS (SELECT 1 FROM team_aliases a WHERE a.alias = v.alias AND a.source = 'odds_api');

INSERT INTO team_aliases (alias, source, team_id) VALUES
    ('Bayern München', 'odds_api', 61440), ('Internazionale Milano', 'odds_api', 12102),
    ('LOSC Lille', 'odds_api', 68864), ('Young Boys', 'odds_api', 85077)
ON CONFLICT (alias, source) DO NOTHING;

COMMIT;

-- Reversión: DELETE FROM team_aliases WHERE source = 'odds_api'
--              AND alias IN ('Bayern München', 'Internazionale Milano', 'LOSC Lille', 'Young Boys');
--            DELETE FROM correcciones_identidad WHERE migracion = '074';
