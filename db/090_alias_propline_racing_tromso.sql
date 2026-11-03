-- 090: dos nombres de PropLine de clubes de nuestras ligas que no emparejaban.
--
-- 'Racing de Santander' (La Liga) y 'Tromsoe' (Eliteserien) llegaban en el feed de cuotas y en el calendario
-- sin alias `propline`: cada hora quedaban sin resolver (78 y 22 veces entre el 25 y el 28-oct-2026) y sus
-- partidos sin cuotas ni cierre. Los demás nombres sin resolver de esos días son clubes de ligas que no
-- cubrimos (las copas no dan de alta equipos; ver CLAUDE.md) o 'Deportivo', que no existe en `teams`: darlo
-- de alta es una decisión de datos aparte. Idempotente.
BEGIN;

INSERT INTO correcciones_identidad (migracion, tabla, clave, campo, antes, despues, motivo)
SELECT '090', 'team_aliases', v.alias || '|propline', 'team_id', NULL, v.tid::text,
       'nombre de PropLine sin alias en cuotas y calendario'
FROM (VALUES ('Racing de Santander', 84889), ('Tromsoe', 85114)) v(alias, tid)
WHERE EXISTS (SELECT 1 FROM teams t WHERE t.team_id = v.tid)
  AND NOT EXISTS (SELECT 1 FROM team_aliases a WHERE a.alias = v.alias AND a.source = 'propline');

INSERT INTO team_aliases (alias, source, team_id)
SELECT v.alias, 'propline', v.tid
FROM (VALUES ('Racing de Santander', 84889), ('Tromsoe', 85114)) v(alias, tid)
WHERE EXISTS (SELECT 1 FROM teams t WHERE t.team_id = v.tid)
ON CONFLICT (alias, source) DO NOTHING;

COMMIT;

-- Reversión: DELETE FROM team_aliases WHERE source = 'propline' AND alias IN ('Racing de Santander', 'Tromsoe');
--            DELETE FROM correcciones_identidad WHERE migracion = '090';
