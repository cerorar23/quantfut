# NBA v2 — Jugadores dentro del pronóstico de equipo (versión 2.1) (2026-11-03)

## Qué cambia

El margen sellado del partido deja de ser solo el del rating de equipo: es la **media** del margen del rating de equipo (`equipo-2.0`) y del margen del modelo de jugadores del Sprint 3b (impacto por jugador × minutos esperados de la plantilla, con partes y rol). El **total** y la forma de la distribución siguen siendo los del núcleo de equipo; la desviación del margen es la medida hacia adelante de la mezcla (14,05) y la del total la de siempre (18,46).

Por qué solo el margen: la mezcla mejora el error del margen en los dos periodos medidos (validación 2023-25: 14,19 → 14,05; prueba 2025-26: 14,49 → 14,32), pero el del total cambia de signo (validación 18,28 → 18,33; prueba 19,12 → 19,03), así que no se toca. Se usa lo que mejora en ambos.

- **Artefacto** (`parametros/impacto.json`, `ops/entrenar_impacto.py`, entrenado en local con los 6.414 partidos y 1.028 jugadores): ridge λ = 10, vida media 730 días, intercepto y efecto del descanso; su huella va en `version_modelo` (`equipo-2.1;…;margen=media(equipo,jugadores);impacto=<huella>`).
- **Minutos esperados**: probabilidad de jugar (parte oficial o rol) × minutos si juega de cada candidato, reescalados a 240 por equipo (el mismo cálculo del Sprint 3b).
- **Respaldo honesto**: si algún equipo tiene menos de 8 candidatos con historial, el motor sella con el núcleo 2.0 y la versión lo dice; no inventa jugadores.
- **Un solo pronóstico de equipo por partido**: si ya hay uno sellado con ese corte (de cualquier versión de equipo) no se sella otro. Los tres partidos nocturnos del 2-nov quedan con la versión 2.0; los siguientes, con la 2.1.
- **Corrección de un error propio**: al mover el cálculo de la plantilla antes del sello del equipo, los pronósticos de jugador dejaron de sellarse "todo o nada" (cada uno se confirmaba solo). Lo cazó la prueba de fallo a mitad; ahora van dentro de una transacción explícita.

## G-fuga de la mezcla (VPS, solo lectura, 60 partidos de 2025-26)

0 diferencias de repetibilidad (versión, escenarios y distribución idénticos al repetir); en los 60 partidos se usó la versión 2.1 (ninguno cayó al respaldo); la media esperada de la mezcla coincide con la media del margen de equipo calculado de forma independiente y el margen de jugadores en 3·10⁻⁴ puntos (el redondeo del sello); plantillas y props siguen sin diferencias frente a la reconstrucción independiente (cobertura 81,5 % de los puntos reales).

## Límites

- **El impacto es un artefacto estático** ajustado con datos hasta el 12-abr-2026. El Sprint 3b lo reajustaba cada 21 días; sin reajuste se degrada con el tiempo (jugadores nuevos entran con impacto 0 y los traspasos no se reflejan en su beta). Hay que reentrenarlo en local periódicamente (`entrenar_impacto.py`) y publicar una imagen nueva; cada artefacto cambia la versión y se ve en la web como un modelo nuevo.
- **No hay cajas de 2026-27 antes de las que llegan por cdn.nba.com**: el historial de muchos jugadores termina en abril.
- **Los partidos sin hora de salto conocida** (hoy los de mañana hasta que ESPN/cdn publican la hora) no se sellan y no generan alerta: falta una alerta específica cuando un partido del día sigue sin hora a media tarde.
- Un dato de la evaluación, no del motor: ni la mezcla ni el equipo superan el cierre del mercado (Brier del ganador 0,204 frente a 0,198).
