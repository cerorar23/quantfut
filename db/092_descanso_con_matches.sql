-- 092: el descanso y la carga de cada equipo vuelven a calcularse con lo jugado DESPUÉS de la última carga de
-- calendario_equipo. La fuente de ese calendario (API-Football) se retiró y la tabla no se refresca desde el 22-oct-2026:
-- sin esto, v_descanso_equipo no veía ningún partido posterior y sobrestimaba el descanso (+8,2 días de media el 1-nov).
--
-- Hasta la última carga (max(recibido_en)) manda calendario_equipo, que trae todas las competiciones y amistosos de clubes;
-- después, los partidos terminados de `matches` (ligas, Champions y Europa League). Copas domésticas y selecciones jugadas
-- después de esa fecha NO están: el descanso es una cota superior para esos equipos. Para el histórico anterior el
-- resultado es idéntico al de la vista 080. `ultima_competicion` mezcla nombres de liga (calendario) e ids (matches).
BEGIN;

CREATE OR REPLACE VIEW v_partidos_jugados_equipo AS
SELECT c.team_id, c.fecha, c.liga_nombre AS competicion
FROM calendario_equipo c
WHERE c.team_id IS NOT NULL AND c.estado IN ('FT', 'AET', 'PEN')
  AND c.fecha <= (SELECT coalesce(max(recibido_en), '-infinity'::timestamptz) FROM calendario_equipo)
UNION ALL
SELECT m.home_team_id, m.kickoff_utc, m.league_id
FROM matches m
WHERE m.status = 'finished'
  AND m.kickoff_utc > (SELECT coalesce(max(recibido_en), '-infinity'::timestamptz) FROM calendario_equipo)
UNION ALL
SELECT m.away_team_id, m.kickoff_utc, m.league_id
FROM matches m
WHERE m.status = 'finished'
  AND m.kickoff_utc > (SELECT coalesce(max(recibido_en), '-infinity'::timestamptz) FROM calendario_equipo);

CREATE OR REPLACE VIEW v_descanso_equipo AS
SELECT m.match_id, x.team_id, x.lado, m.kickoff_utc,
       prev.fecha            AS ultimo_partido,
       prev.competicion      AS ultima_competicion,
       round((extract(epoch FROM m.kickoff_utc - prev.fecha) / 86400)::numeric, 2) AS dias_descanso,
       (SELECT count(*) FROM v_partidos_jugados_equipo c
         WHERE c.team_id = x.team_id
           AND c.fecha < m.kickoff_utc - interval '1 hour'
           AND c.fecha >= m.kickoff_utc - interval '14 days') AS partidos_14d,
       (SELECT count(*) FROM v_partidos_jugados_equipo c
         WHERE c.team_id = x.team_id
           AND c.fecha < m.kickoff_utc - interval '1 hour'
           AND c.fecha >= m.kickoff_utc - interval '30 days') AS partidos_30d
FROM matches m
CROSS JOIN LATERAL (VALUES (m.home_team_id, 'home'), (m.away_team_id, 'away')) AS x(team_id, lado)
LEFT JOIN LATERAL (
    SELECT c.fecha, c.competicion FROM v_partidos_jugados_equipo c
    WHERE c.team_id = x.team_id AND c.fecha < m.kickoff_utc - interval '1 hour'
    ORDER BY c.fecha DESC LIMIT 1) prev ON true;

COMMIT;
