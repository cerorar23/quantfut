# Medición del límite del ajuste de goles (`MAX_RESIDUO_AJUSTE`) — protocolo

Fijado el 2026-11-18, **antes de calcular ningún resultado** (este archivo se confirma y se sube antes de ejecutar la medición;
los números de la sección «Resultados» se añaden después, sin tocar el protocolo).

## Pregunta

`alta_prob.MAX_RESIDUO_AJUSTE = 0,01` (desde el 2026-10-05, sin medición documentada) descarta el ajuste de goles cuando el 1X2 y la
línea de goles de Pinnacle «no caben» en una misma pareja de lambdas. Sin ajuste desaparecen de golpe los candidatos que dependen de él:
totales, «marca el local/visitante», ambos marcan y los hándicaps de línea no entera cero. El 13-nov-2026 se midió en producción que el
**36 % de los partidos con cuotas** (86 de 242) supera ese límite (mediana del residuo 0,0080; p90 0,0154; p95 0,0174; máx. 0,0508).

**¿Se puede subir el límite sin empeorar la calibración de lo que se publica?** Candidatas: 0,015, 0,02 y 0,03.

## Qué se sabía antes de fijar el protocolo (para que se vea el sesgo posible)

- Comparación provisional en producción, partidos del 1 al 12-nov, candidatos de goles de 62-95 % con cuota: residuo ≤ 0,01 → acierto
  79,8 % frente a 77,7 % prometido (n = 1.220 candidatos); residuo 0,01-0,02 → 76,7 % frente a 77,6 % (n = 691); > 0,02 → 88,5 % frente a
  78,5 % (n = 52). Son candidatos muy correlacionados dentro de cada partido y solo 12 días: **no concluye**.
- La prueba histórica original (`eval/alta_prob_calibracion.py`, 14.216 partidos de football-data) aplicó **este mismo límite** al decidir
  qué mercados de goles entraban: validó los mercados de goles solo en los partidos donde el ajuste encajaba (residuo ≤ 0,01). Es la razón
  de esta medición: lo que se aprobó vale para ese subconjunto, no para el resto.

## Datos

- football-data.co.uk, 7 ligas (`alta_prob_calibracion.LIGAS`), temporadas 1920 a 2425 (`soft_vs_sharp.DEFAULT_SEASONS`): Pinnacle PRE-CIERRE
  (PSH/PSD/PSA) y línea 2,5 (P>2,5 / P<2,5). Misma fuente y mismas columnas que la prueba original. Se registra el sha256 del conjunto.
- `rho` = −0,0347 (el modelo activo en producción el 13-nov). Sensibilidad: −0,0613 (el de la prueba original).
- Devig = `settings.devig_method`, igual que producción.
- Limitación conocida: football-data solo trae la línea 2,5; producción ajusta a la línea principal de Pinnacle de cada partido (puede ser
  2,25, 2,75…). Se compara la distribución del residuo de football-data con la de producción (arriba) para ver si el residuo se parece.

## Unidad y definiciones

- **Residuo**: `fit.residual` de `market_lambdas` con el 1X2 sin margen y la línea 2,5 sin margen. Se calcula SIN límite; los partidos que
  no convergen se cuentan aparte y quedan fuera.
- **Candidatos dependientes del ajuste**: los que produciría la línea ampliada (`alta_prob_ext.candidatos`, sin córners) con ajuste y que NO
  existen sin él: `totals` (`GOLES_EXT`), `team_totals_home/away` over 0,5, `btts yes` (`BTTS_EXT`) y `spreads` de línea ≠ 0 (el 0 sale del 1X2 y
  no depende del ajuste). Solo los de probabilidad entre 0,62 y 0,95. Un candidato con devolución (hándicap entero) no cuenta.
- **Grupos por residuo**: A ≤ 0,010 (base, lo vigente) · B (0,010-0,015] · C (0,015-0,020] · D (0,020-0,030] · E > 0,030.
- **Incremento de un límite X**: `I_X` = candidatos de los partidos con residuo en (0,010, X].
- **Brecha** = acierto real − probabilidad prometida media, en puntos porcentuales.
- **Clúster**: el partido (los candidatos de un mismo partido no son independientes). Todo error estándar y todo intervalo usa remuestreo o
  varianza por partido, no por candidato.

## Criterio de decisión (fijado ahora)

Para cada límite candidato X ∈ {0,015; 0,02; 0,03}, el incremento `I_X` debe cumplir las TRES:

1. **Brecha conjunta ≥ −1,0 punto** (el mismo `MAX_DEFICIT_PTS` de la prueba original), sobre todos los candidatos de `I_X`.
2. **Prueba por tramo de la prueba original**, con error estándar por partido: para cada mercado y tramo (`TRAMOS_AMPLIOS`) de `I_X` con
   n ≥ 100 candidatos, real ≥ prometido − 2·SE_clúster. Todos los mercados evaluables deben pasar.
3. **No peor que lo vigente**: brecha(`I_X`) − brecha(A) ≥ −2,0 puntos (estimación puntual; el intervalo del 95 % por remuestreo de partidos
   se informa, no decide).

Además: `I_X` debe tener al menos **300 partidos**; con menos, el resultado es «no concluyente» y el límite no se sube.
**Decisión**: se propone el mayor X que cumple las tres condiciones; si ninguno, se mantiene 0,010. La decisión final de reglas del motor
es del titular; esta medición propone, no cambia nada.

## Análisis informativos (no deciden)

- Brecha por grupo (A-E), por mercado y por liga; distribución del residuo; por tramo de probabilidad (0,62-0,80 línea ampliada, 0,80-0,95 línea normal).
- Sensibilidad a `rho` = −0,0613.
- Picks ganados: por cada X, número de partidos con al menos un candidato en cada línea (80 % y ampliada) frente al límite vigente.
- Producción (1-nov a la fecha de la medición): los mismos grupos con partidos reales y cuotas PropLine, como confirmación fuera de muestra.

## Reproducibilidad

`python -m qf.eval.alta_prob_residuo --cache <carpeta de football-data> --json salida.json` (módulo nuevo, con pruebas en `tests/test_alta_prob_residuo.py`).
