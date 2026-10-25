-- Retiro del titular, 25-oct-2026: quedan 15 ligas + 2 copas (Premier, LaLiga, Serie A, Bundesliga, Ligue 1,
-- Eredivisie, Primeira, Brasil, Liga MX, MLS, Championship, 2. Bundesliga, Turquía, Noruega, Argentina, Champions y
-- Europa League). Fuera Serie B, LaLiga 2, Allsvenskan y Super League suiza: huecos de xG que ninguna fuente cierra
-- (LaLiga 2 y Serie B), xG de jugador irregular (Suecia) y sin resultados en PropLine (Suiza). Ver
-- docs/cobertura_ligas_propline_sofascore_20261025.md.
-- Igual que db/086: no se borra nada ni se añaden a `retired_leagues` (su trigger rechazaría cualquier UPDATE sobre
-- los partidos sellados que se conservan). Desactivadas, ningún motor, captura ni producto las lee.
BEGIN;
UPDATE leagues SET active = FALSE, model_enabled = FALSE, captura_completa = FALSE
 WHERE league_id IN ('it.serie_b', 'es.laliga2', 'se.allsvenskan', 'ch.super_league');
COMMIT;
