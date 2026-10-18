-- 080: descanso y carga de cada equipo antes de cada partido (F12), desde calendario_equipo.
--
-- Solo cuenta partidos ya terminados (FT, AET, PEN) con fecha anterior al saque menos una hora. Incluye todas las
-- competiciones y amistosos de clubes; el que consuma decide si filtra por `liga_nombre`. Calidad de la fuente:
-- el calendario viene de API-Football tal como está HOY (un partido aplazado figura en su fecha final), así que
-- para evaluar hacia atrás es una aproximación; para producción, el calendario se refresca cada día.
-- Equipos nacionales y fechas FIFA no están: un jugador cedido a su selección no se refleja aquí.
BEGIN;

CREATE OR REPLACE VIEW v_descanso_equipo AS
SELECT m.match_id, x.team_id, x.lado, m.kickoff_utc,
       prev.fecha            AS ultimo_partido,
       prev.liga_nombre      AS ultima_competicion,
       round((extract(epoch FROM m.kickoff_utc - prev.fecha) / 86400)::numeric, 2) AS dias_descanso,
       (SELECT count(*) FROM calendario_equipo c
         WHERE c.team_id = x.team_id AND c.estado IN ('FT', 'AET', 'PEN')
           AND c.fecha < m.kickoff_utc - interval '1 hour'
           AND c.fecha >= m.kickoff_utc - interval '14 days') AS partidos_14d,
       (SELECT count(*) FROM calendario_equipo c
         WHERE c.team_id = x.team_id AND c.estado IN ('FT', 'AET', 'PEN')
           AND c.fecha < m.kickoff_utc - interval '1 hour'
           AND c.fecha >= m.kickoff_utc - interval '30 days') AS partidos_30d
FROM matches m
CROSS JOIN LATERAL (VALUES (m.home_team_id, 'home'), (m.away_team_id, 'away')) AS x(team_id, lado)
LEFT JOIN LATERAL (
    SELECT c.fecha, c.liga_nombre FROM calendario_equipo c
    WHERE c.team_id = x.team_id AND c.estado IN ('FT', 'AET', 'PEN')
      AND c.fecha < m.kickoff_utc - interval '1 hour'
    ORDER BY c.fecha DESC LIMIT 1) prev ON true;

COMMIT;
