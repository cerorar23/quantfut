-- 0007: catálogo de fuentes (plan técnico tenis, §A.3). Idempotente: ON CONFLICT no modifica filas existentes.
-- Las prioridades son PROVISIONALES (1 = mejor): se fijan con la auditoría de cada fuente (ver LEEME, supuestos).
-- Las licencias marcadas «pendiente» no están verificadas: no se usa ningún dato de esa fuente en producción
-- hasta que se revise su licencia.
INSERT INTO tenis.fuente (fuente, prioridad_calendario, prioridad_resultado, licencia, uso_permitido, descripcion) VALUES
    ('sofascore',    1, 1, 'pendiente de verificar', 'pendiente de verificar',
     'Marcador, orden de juego y punto a punto (scraper del VPS); fuente principal en vivo'),
    ('sportsapipro', 2, 2, 'pendiente de verificar', 'pendiente de verificar',
     'Calendario y resultados en vivo; cupo compartido diario'),
    ('api_tennis',   2, 2, 'pendiente de verificar', 'pendiente de verificar',
     'Calendario y resultados hasta el 1-nov-2026; sustituida por sportsapipro'),
    ('tml',          3, 3, 'pendiente de verificar', 'pendiente de verificar',
     'Histórico ATP/WTA por partido: ganador y perdedor, sin hora (retro)'),
    ('tennis_data',  4, 5, 'pendiente de verificar', 'pendiente de verificar',
     'Cierres de cuotas de referencia, sin hora; solo referencia, no entra en el motor'),
    ('mcp',          5, 4, 'CC BY-NC-SA', 'solo local, sin lucro, con atribución',
     'Punto a punto de partidos destacados; carga única en la copia local, nunca en producción'),
    ('propline',     9, 9, 'pendiente de verificar', 'pendiente de verificar',
     'Cuotas de referencia; no aporta identidad ni desenlace')
ON CONFLICT (fuente) DO NOTHING;
