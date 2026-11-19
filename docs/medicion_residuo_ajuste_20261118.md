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

---

# Resultados (añadidos el 2026-11-18, después de ejecutar; el protocolo de arriba no se modificó)

Conjunto: football-data, 14.216 partidos de 7 ligas (2019-2025), el mismo de la prueba original (sha256 `d5cbc3151164…`, 14.305 filas). Los 14.216
ajustes convergen (0 sin convergencia, 0 con error). Datos: `medicion_residuo_ajuste_20261118_rho0347.json` (principal) y `…_rho0613.json`.

## El residuo en football-data se parece al de producción

| | mediana | p90 | p95 | partidos con residuo > 0,01 |
|---|---|---|---|---|
| football-data, rho −0,0347 | 0,0072 | 0,0166 | 0,0199 | 33,9 % |
| producción (13-nov, 242 partidos) | 0,0080 | 0,0154 | 0,0174 | 36 % |

La limitación de usar solo la línea 2,5 no cambia el orden de magnitud del residuo, así que la medición es trasladable.

## Calibración por calidad del ajuste (candidatos de goles de 62-95 %, rho −0,0347)

| Grupo (residuo) | candidatos | partidos | prometido | real | brecha ± SE (por partido) |
|---|---|---|---|---|---|
| A ≤ 0,010 (vigente) | 70.185 | 9.392 | 79,49 | 80,33 | +0,84 ± 0,17 |
| B 0,010-0,015 | 25.424 | 2.792 | 79,87 | 81,03 | +1,15 ± 0,29 |
| C 0,015-0,020 | 12.609 | 1.336 | 79,98 | 81,22 | +1,24 ± 0,43 |
| D 0,020-0,030 | 6.005 | 634 | 79,97 | 80,82 | +0,85 ± 0,62 |
| E > 0,030 | 572 | 62 | 80,43 | 80,59 | +0,17 ± 1,99 |

**Todos los grupos aciertan algo MÁS de lo prometido**, y los de peor ajuste no son peores que el vigente. El déficit que temía el límite no aparece.

## Criterio del protocolo, aplicado sin cambios

| Límite | incremento (partidos) | brecha del incremento | vs. base (IC 95 %) | cond. 1 | cond. 2 | cond. 3 | ≥ 300 partidos | resultado |
|---|---|---|---|---|---|---|---|---|
| 0,015 | 2.792 | +1,15 ± 0,29 | +0,31 [−0,34; +0,94] | sí | sí | sí | sí | **acepta** |
| 0,020 | 4.128 | +1,18 ± 0,24 | +0,34 [−0,26; +0,94] | sí | sí | sí | sí | **acepta** |
| 0,030 | 4.762 | +1,14 ± 0,22 | +0,29 [−0,27; +0,81] | sí | **no** | sí | sí | rechaza |

El 0,03 se rechaza por una sola celda: «más de 1,5 goles» en el tramo 0,67-0,72 (n = 1.061, brecha −3,38, SE 1,45). Con tantos mercados y tramos
comparados, una celda aislada puede ser azar; pero el protocolo ya decía que todas las evaluables debían pasar, y no se reinterpreta a
posteriori. **Límite propuesto por el criterio: 0,020.**

## Sensibilidad a rho (−0,0613, el de la prueba original)

Con ese rho el residuo es menor (mediana 0,0045; solo el 15,7 % supera 0,01) y los tres límites pasan (propuesto 0,03). Coincide en que subir a 0,020
cumple en ambos; el criterio principal (rho activo) es el que decide.

## Desgloses informativos (no deciden)

- Por banda: en 0,62-0,80 las brechas de B, C y D son +1,16, +1,66 y +0,77; en 0,80-0,95, +1,14, +0,83 y +0,93. Ningún grupo con déficit en ninguna banda.
- Incremento (0,01-0,02] por mercado: de −0,38 (más de 2,5, n = 349, SE 2,5) a +1,98 (visitante marca); ningún mercado con déficit mayor que su error.
- Incremento (0,01-0,02] por liga: todas positivas, de +0,22 (Premier) a +2,31 (Serie A).
- Partidos con candidato elegible por probabilidad (sin exigir cuota) en la línea del 80 %: 70,9 % con 0,01; 87,2 % con 0,015; **95,6 % con 0,02**;
  99,6 % con 0,03. En la línea ampliada ya es 100 % (siempre hay 1X2 o doble oportunidad en rango; en producción la limita la cuota).

## Confirmación fuera de muestra con producción (informativa)

Partidos de producción jugados del 1 al 17-nov, con las cuotas de PropLine de la decisión de las 09:00 y la línea principal de Pinnacle de cada
partido (258 con ajuste; 56 sin captura de Pinnacle):

| Grupo | candidatos | partidos | brecha ± SE |
|---|---|---|---|
| A | 1.363 | 165 | +1,45 ± 1,29 |
| B | 609 | 63 | −1,99 ± 2,27 |
| C | 195 | 20 | +0,94 ± 4,19 |
| D | 68 | 7 | +6,65 ± 4,37 |

Incrementos de 63 a 90 partidos: por debajo del mínimo de 300 del protocolo, **no concluyen**. El grupo B queda 2 puntos por debajo de lo prometido, pero con
un error de ±2,3, y entre 3 semanas de partidos con candidatos muy correlacionados. La diferencia con football-data (+1,15) es de unas 1,4 desviaciones: es
compatible con azar. Hay que repetirlo cuando haya 300 partidos de incremento (a este ritmo, unos 2 meses).

## Lo que esta medición no cubre

- football-data solo trae la línea 2,5 y 7 ligas (2019-2025); producción usa la línea principal de cada partido y además MLS, Liga MX, Brasileirão, etc.
- Mide calibración de la probabilidad, no el valor frente a la cuota ni el CLV.
- No mide córners (no dependen del ajuste de goles).
- Los candidatos de un mismo partido están correlacionados: por eso el error estándar es por partido; aun así, seis temporadas de ligas no son independientes del
  régimen de goles de cada temporada.

## Recomendación (la decisión de reglas del motor es del titular)

1. Subir `MAX_RESIDUO_AJUSTE` de 0,010 a **0,020** es lo que el criterio fijado de antemano permite: unos 4.100 partidos (el 29 % de los 14.216) que hoy pierden sus candidatos de goles de 62-95 %,
   sin deterioro de calibración medible. Es una constante en `alta_prob.py`; solo afecta a las selecciones futuras (lo sellado no se toca).
2. Mantener la vigilancia en vivo por mercado (`alta_prob.control`), que ya pausa un mercado si su acierto real cae por debajo de lo prometido.
3. Repetir la confirmación con producción cuando el incremento llegue a 300 partidos.
