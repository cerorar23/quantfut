-- Retiro del titular, 25-oct-2026: Ligue 2 y Superliga danesa fuera de los motores. PropLine, la única fuente de
-- cuotas desde el 23-oct, no las cotiza (catálogo de 36 competiciones, comprobado el 25-oct), así que el Motor B no
-- tiene precio para ellas y el Motor A nunca las modeló.
-- A diferencia de Chile y Brasil B (db/063) aquí NO se borra nada: sus 26 + 179 pronósticos de alta probabilidad,
-- 3 pasos de escalera, 4 patas de parley y 55 ofertas en sombra están sellados y liquidados, y borrarlos exige una
-- autorización aparte. Tampoco se añaden a `retired_leagues`: su trigger rechazaría cualquier UPDATE sobre los
-- partidos que se conservan. Desactivadas, ningún motor, captura ni producto las lee (todos filtran `l.active`).
BEGIN;
UPDATE leagues SET active = FALSE, model_enabled = FALSE, captura_completa = FALSE
 WHERE league_id IN ('fr.ligue_2', 'dk.superliga');
COMMIT;
