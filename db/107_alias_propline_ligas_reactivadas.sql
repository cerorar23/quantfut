-- 107: nombres de PropLine de clubes de las ligas publicadas el 9-nov-2026 que no emparejaban.
--
-- Tras reactivar LaLiga 2 y Allsvenskan (db/105) y publicar con modelo Turquía, LaLiga 2, Serie B y Allsvenskan (db/106), la
-- primera pasada del calendario dejó sin resolver: 'Malmö' (Allsvenskan), 'Orgryte' (Allsvenskan), 'Goztepe SK' y
-- 'Fenerbahce Istanbul' (Süper Lig) y 'Valladolid' (LaLiga 2; el club baja de La Liga y sigue registrado en `es.laliga`).
-- Sin alias `propline` sus partidos no se insertan y no tendrían pronóstico. Idempotente.
-- Los demás nombres sin resolver son clubes de competiciones que no cubrimos (copas: no dan de alta equipos) y
-- 'Swansea'/'QPR' (Championship, sin modelo): decisión aparte.
BEGIN;

INSERT INTO correcciones_identidad (migracion, tabla, clave, campo, antes, despues, motivo)
SELECT '107', 'team_aliases', v.alias || '|propline', 'team_id', NULL, v.tid::text,
       'nombre de PropLine sin alias en el calendario de ligas reactivadas'
FROM (VALUES ('Malmö', 85128), ('Orgryte', 85130), ('Goztepe SK', 85069),
             ('Fenerbahce Istanbul', 85065), ('Valladolid', 6008)) v(alias, tid)
WHERE EXISTS (SELECT 1 FROM teams t WHERE t.team_id = v.tid)
  AND NOT EXISTS (SELECT 1 FROM team_aliases a WHERE a.alias = v.alias AND a.source = 'propline');

INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'propline', v.tid
FROM (VALUES ('Malmö', 85128), ('Orgryte', 85130), ('Goztepe SK', 85069),
             ('Fenerbahce Istanbul', 85065), ('Valladolid', 6008)) v(alias, tid)
WHERE EXISTS (SELECT 1 FROM teams t WHERE t.team_id = v.tid)
ON CONFLICT (alias, source) DO NOTHING;

COMMIT;

-- Reversión: DELETE FROM team_aliases WHERE source = 'propline' AND alias IN ('Malmö', 'Orgryte', 'Goztepe SK', 'Fenerbahce Istanbul', 'Valladolid');
--            DELETE FROM correcciones_identidad WHERE migracion = '107';
