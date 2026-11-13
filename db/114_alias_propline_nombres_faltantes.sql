-- 114: nombres de PropLine de clubes del catálogo que no emparejaban (13-nov-2026).
--
-- Auditoría del archivo horario de PropLine contra `team_aliases` (alias exacto `propline` u `odds_api`, o nombre canónico): de 499 nombres de
-- equipo, 49 no se resolvían. Cada partido con uno de ellos se descartaba en `propline_ingest` (`match_events`) y se quedaba sin cuotas, así
-- que no podía tener pronóstico. Estos 19 son del mismo club y misma liga que ya están en el catálogo: ALIAS, nunca equipo nuevo.
-- Los ids se comprobaron a mano contra `teams` y contra los partidos de los últimos 40 días (Pisa y Sampdoria están en `it.serie_a`
-- como liga doméstica del equipo, pero sus partidos recientes son de `it.serie_b`: es el mismo registro).
--
-- Quedan sin alias, a propósito, los clubes de ligas fuera del catálogo que juegan Champions y Europa League (Club Brugge, AEK Athens,
-- Celtic, Olympiacos…): sus partidos se descartan por diseño y no se dan de alta equipos bajo `eu.ucl` ni `eu.uel`. El emparejamiento
-- difuso los confundiría con otros clubes (Sparta Praha → Sparta Rotterdam, Celtic → Celta): no se acepta.
-- Idempotente.
BEGIN;

INSERT INTO correcciones_identidad (migracion, tabla, clave, campo, antes, despues, motivo)
SELECT '114', 'team_aliases', v.alias || '|propline', 'team_id', NULL, v.tid::text,
       'nombre de PropLine sin alias: el partido se descartaba sin cuotas'
FROM (VALUES ('Athletico Paranaense-PR', 39922), ('CR Vasco da Gama RJ', 40692), ('SV 07 Elversberg', 68786),
             ('Cologne', 61446), ('FSV Mainz', 61457), ('Atlético de Madrid', 2984), ('Deportivo', 2968),
             ('Celta De Vigo B', 84898), ('ESTAC Troyes', 69628), ('Racing Club de Lens', 68869), ('Stade Brest', 72662),
             ('Nottingham', 4), ('AC Pisa 1909', 20458), ('Sampdoria Genoa', 12098), ('Carrarese Calcio 1908', 84907),
             ('LR Vicenza Virtus', 84914), ('Cambuur Leeuwarden', 21207), ('CD Nacional Madeira', 77428),
             ('Casa Pia Lisbon', 82325)) v(alias, tid)
WHERE EXISTS (SELECT 1 FROM teams t WHERE t.team_id = v.tid)
  AND NOT EXISTS (SELECT 1 FROM team_aliases a WHERE a.alias = v.alias AND a.source = 'propline');

INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'propline', v.tid
FROM (VALUES ('Athletico Paranaense-PR', 39922), ('CR Vasco da Gama RJ', 40692), ('SV 07 Elversberg', 68786),
             ('Cologne', 61446), ('FSV Mainz', 61457), ('Atlético de Madrid', 2984), ('Deportivo', 2968),
             ('Celta De Vigo B', 84898), ('ESTAC Troyes', 69628), ('Racing Club de Lens', 68869), ('Stade Brest', 72662),
             ('Nottingham', 4), ('AC Pisa 1909', 20458), ('Sampdoria Genoa', 12098), ('Carrarese Calcio 1908', 84907),
             ('LR Vicenza Virtus', 84914), ('Cambuur Leeuwarden', 21207), ('CD Nacional Madeira', 77428),
             ('Casa Pia Lisbon', 82325)) v(alias, tid)
WHERE EXISTS (SELECT 1 FROM teams t WHERE t.team_id = v.tid)
ON CONFLICT (alias, source) DO NOTHING;

COMMIT;

-- Reversión: DELETE FROM team_aliases WHERE source = 'propline' AND alias IN ('Athletico Paranaense-PR', 'CR Vasco da Gama RJ',
--              'SV 07 Elversberg', 'Cologne', 'FSV Mainz', 'Atlético de Madrid', 'Deportivo', 'Celta De Vigo B', 'ESTAC Troyes',
--              'Racing Club de Lens', 'Stade Brest', 'Nottingham', 'AC Pisa 1909', 'Sampdoria Genoa', 'Carrarese Calcio 1908',
--              'LR Vicenza Virtus', 'Cambuur Leeuwarden', 'CD Nacional Madeira', 'Casa Pia Lisbon');
--            DELETE FROM correcciones_identidad WHERE migracion = '114';  -- solo si la tabla lo permite (ver db/073)
