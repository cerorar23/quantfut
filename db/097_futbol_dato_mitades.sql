-- 097: córners, tiros, xG y tarjetas POR MITAD en las filas de equipo (evento 1 = 1.ª parte, 2 = 2.ª parte).
--
-- db/096 dejó fuera esas seis claves porque «ya viven en `matches`», pero `matches` solo guarda el partido
-- completo: los mercados de córners y tarjetas por mitad (motor C, fase C3 del rediseño) no tenían de dónde leer.
-- El partido completo (evento 0) sigue sin repetirse aquí. `xg`, `tiros_totales` y `tiros_puerta` ya existían.
-- En la misma recarga, la fila `contexto` pasa a llevar quién arbitra en `nombre` e `id_en_fuente` (columnas que ya
-- existían); la trayectoria `arbitro_*` se contó al descargar y es posterior al partido.
BEGIN;

ALTER TABLE futbol.dato
    ADD COLUMN IF NOT EXISTS corners SMALLINT,
    ADD COLUMN IF NOT EXISTS amarillas SMALLINT,
    ADD COLUMN IF NOT EXISTS rojas SMALLINT;

COMMIT;
