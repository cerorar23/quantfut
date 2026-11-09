# Hipótesis para mejorar los pronósticos de ambos marcan, primera mitad, córners y tarjetas — 9-nov-2026

Origen: hipótesis del titular (texto pegado en el chat) sobre tres puntos. Se contrasta cada uno con datos **antes de cambiar nada**. Código:
`src/qf/eval/hipotesis_mercados.py`. Todo es fuera de muestra y point-in-time: cada modelo secundario se entrena solo con filas anteriores al corte y se evalúa en
los 28 días siguientes (walk-forward).

## Lo que ya se midió antes y condiciona las hipótesis
- La proporción de goles de la 1ª mitad **no cambió**: 44,3 % en 2019-22, 44,5 % en 2022-25 y 44,5 % desde 2025-07 (10.166 partidos). Liga MX tiene el 45,1 %
  (más alto que la media, no más bajo) y solo la Champions está por debajo (41,9 %, 194 partidos). La explicación «el fútbol cambió tras el Mundial 2022» no se sostiene con la
  proporción; el desfase en Liga MX y Champions necesita otra causa.
- El rediseño del 1-nov (`futbol_rediseno_desde_cero_20261101.md`, 8 ligas) midió el motor C (binomial negativa con goles esperados, árbitro, derbi, igualdad y faltas):
  mejora la media por equipos en tarjetas (resolución de Brier ≈ 9 %) y poco en córners (≈ 2 %). No está en producción.

## H1 — «Ambos marcan» con un modelo secundario
Dixon-Coles trata los goles de local y visitante casi como independientes (solo corrige los marcadores 0-0, 1-0, 0-1 y 1-1). Se prueba una regresión logística sobre las
intensidades del modelo base más rasgos previos: tasa de «ambos marcan», de «no marcar» y de portería a cero de cada equipo (media exponencial de 180 días), puntos por partido,
posición en la tabla y fase de la temporada (proxy de «necesidad de puntos»; la necesidad real exige la tabla completa y los objetivos de cada liga y no se midió).
Variantes: `base` (Dixon-Coles), `basica` (solo log λ y log μ: es una recalibración) y `completa` (con los rasgos).
Criterios fijados antes de medir (periodo 2025-07-01 en adelante, 21 competiciones):
- **B1** `completa` mejora el Brier de «ambos marcan» frente a `base` en ≤ −0,001 y el IC95 (errores por semana) de la diferencia queda entero por debajo de 0.
- **B2** `completa` mejora a `basica` en ≤ −0,0005 (si no, el beneficio es recalibración, no información nueva).
- **B3** Ninguna competición empeora más de +0,005 con IC95 entero por encima de 0.
Si B1, B2 y B3 se cumplen, el modelo secundario es candidato (no se activa sin tu visto bueno).

## H2 — Primera mitad por liga
La proporción fija (0,4366 local / 0,4588 visitante) se ajustó con datos de 2019-22. Se prueban dos correcciones sobre las mismas λ y μ:
- `prop_liga`: proporción propia de cada competición con los 24 meses anteriores, encogida hacia la global con un prior de 400 goles.
- `cal_liga`: recalibración logística de «gol en 1T» y «ambos 1T» con intercepto por competición, entrenada con filas anteriores.
Criterios (periodo 2025-07-01 en adelante):
- **T1** En Liga MX y en Champions la promesa menos la realidad en los mercados publicados (gol en 1T: sí; ambos 1T: no; 0,62-0,85) queda dentro de ±0,03, con al menos 100 lados cada una.
- **T2** El Brier agrupado de gol en 1T y ambos 1T no empeora (diferencia ≤ 0) y ninguna competición empeora más de +0,005 con IC95 entero por encima de 0.

## H3 — Córners y tarjetas con contexto
El ejemplo del titular (equipo muy superior que va perdiendo en el minuto 70) es **en juego**; el producto predice **antes** del partido, así que esa parte no se puede medir con estos
datos. Lo que sí se mide es el contexto previo: se apilan sobre el acumulador actual los goles esperados del modelo (supremacía) con una binomial negativa.
Criterio (periodo 2026-01-01 en adelante, entrenando con 2025-07 a cada corte): **K1** Brier medio de las líneas de córners (8,5-10,5) o de tarjetas (3,5-5,5) mejora en ≤ −0,001
frente al acumulador actual y el IC95 (por semana) queda entero por debajo de 0. Se informa por separado córners y tarjetas.

## Reglas
- Ningún criterio se cambia después de ver los resultados. Si una hipótesis falla, se informa como tal.
- Nada se despliega: este documento y el código son solo medición. Pasar un modelo a producción requiere reentrenar, comparar con el activo y tu aprobación.

# Resultados (9-nov-2026)
Reproducción: `ejecutar.sh .local/entreno_20261109 qf.eval.hipotesis_mercados correr` (resultados crudos en `.local/hipotesis_mercados/hipotesis.json`).
Pruebas: `tests/test_hipotesis_mercados.py` (los rasgos no miran al futuro ni al propio partido).

## Resumen
| Hipótesis | Criterios fijados antes | Resultado |
|---|---|---|
| H1 Ambos marcan con modelo secundario | B1 ✓, **B2 ✗**, B3 ✓ | **No es candidato**: lo que mejora es la recalibración, no los rasgos nuevos |
| H2 Primera mitad: proporción por liga | T2 ✗ | **No ayuda**: la proporción no era el problema |
| H2 Primera mitad: recalibración por liga | T1 ✓ (trivial), T2 ✓ | Mejora pequeña y significativa; arregla a medias el desfase de Liga MX y apenas el de Champions |
| H3 Córners con goles esperados apilados | K1 ✗ | Sin mejora |
| H3 Tarjetas con goles esperados apilados | K1 ✗ | Mejora pequeña no significativa; Serie B empeora |

## H1 — Ambos marcan (9.230 partidos, 2025-07 en adelante; frecuencia real 55,8 %)
| Variante | Brier | Log-loss | Mejora sobre la frecuencia (skill) |
|---|---:|---:|---:|
| `base` (Dixon-Coles) | 0,24676 | 0,68674 | −0,03 % |
| `basica` (recalibración con log λ y log μ) | 0,24492 | 0,68290 | +0,71 % |
| `completa` (con estilo de juego, tabla y fase de la temporada) | 0,24499 | 0,68304 | +0,68 % |
- `completa` frente a `base`: −0,00177 de Brier, IC95 [−0,00271, −0,00082], ninguna liga peor → **B1 y B3 cumplen**.
- `completa` frente a `basica`: **+0,00008**, IC95 [−0,00043, +0,00059] → **B2 falla**: los rasgos de estilo y de «necesidad de puntos» (proxy: puntos por partido, posición y tramo final) **no aportan nada** sobre la recalibración.
- Lectura posterior (no fijada de antemano): la recalibración sencilla `basica` mejora −0,00185 de Brier (IC95 [−0,00266, −0,00103], ninguna liga peor). Es pequeña en términos absolutos (el skill sube de 0 a +0,7 %), pero significativa.
  La interpretación del titular («Dixon-Coles trata los goles como independientes») es plausible, pero lo que se corrige con dos parámetros es el mapa de intensidades a «ambos marcan», no hace falta información de estilo.
- No se midió la necesidad de puntos real (exige la tabla con los objetivos de cada liga); el proxy no aporta.

## H2 — Primera mitad (9.204 partidos)
| Variante | Brier gol 1T | Brier ambos 1T | Promesa − realidad, 0,62-0,85 (Liga MX / Champions) | Ídem, franja 0,75-0,85 (Liga MX / Champions) |
|---|---:|---:|---|---|
| `fijo` (producción) | 0,20174 | 0,15957 | +2,1 / +2,2 | **+5,8 / +5,8** |
| `prop_liga` (proporción por competición, 24 meses) | 0,20171 | 0,15967 | +2,0 / +2,5 | +5,9 / +6,0 |
| `cal_liga` (intercepto por competición) | 0,20111 | 0,15939 | +0,9 / +1,0 | **+2,6 / +4,6** |
- `prop_liga` frente a `fijo`: +0,00004 (IC95 [−0,00006, +0,00013]) → **T2 falla**: la proporción por liga no cambia nada. Con los datos medidos antes (44,3 % → 44,5 %) la hipótesis de que
  «la proporción cambió tras 2022» no se sostiene.
- `cal_liga` frente a `fijo`: −0,00041 (IC95 [−0,00068, −0,00013]), ninguna liga peor → **T1 y T2 cumplen**.
- **Defecto de mi criterio T1**: se fijó en el rango publicado completo (0,62-0,85) y la proporción fija ya cumplía (+2,1 y +2,2). El desfase estaba en la franja 0,75-0,85, que se añadió como lectura posterior (columna de la derecha): ahí `cal_liga` reduce Liga MX de +5,8 a +2,6 (dentro de ±3) y
  Champions de +5,8 a +4,6 (con menos lados, 158; sigue por encima).

## H3 — Córners y tarjetas con contexto previo (Brier por línea, 5.698 partidos desde 2026-01 entrenando desde 2025-07)
| | Línea | Acumulador actual | Apilado con goles esperados | Diferencia |
|---|---|---:|---:|---:|
| Córners | 8,5 / 9,5 / 10,5 | 0,22992 / 0,24593 / 0,23645 | 0,22996 / 0,24585 / 0,23636 | +0,00004 / −0,00008 / −0,00009 |
| Tarjetas | 3,5 / 4,5 / 5,5 | 0,22787 / 0,22941 / 0,18522 | 0,22710 / 0,22867 / 0,18542 | −0,00077 / −0,00075 / +0,00019 |
- Córners: diferencia media −0,00004, IC95 [−0,00054, +0,00045] → **K1 falla**.
- Tarjetas: −0,00044, IC95 [−0,00137, +0,00049], **Serie B peor** → **K1 falla**.
- El ejemplo del titular (equipo superior que va perdiendo en el minuto 70) es **en juego** y no se puede medir con un pronóstico previo al partido. Coincide con lo medido el 1-nov: el motor C (binomial negativa con goles esperados, árbitro, derbi, igualdad y faltas)
  mejora tarjetas frente a la media de la liga, pero aporta poco sobre un acumulador por equipos.

## Conclusión y qué sería razonable hacer
1. **Ninguna de las hipótesis, tal como se formularon, cumple sus criterios.** Los rasgos de estilo/necesidad (H1), la proporción por liga (H2) y el contexto apilado (H3) no aportan.
2. **Dos mejoras pequeñas aparecen, ambas de recalibración y no de información nueva**: «ambos marcan» (−0,00185 de Brier) y primera mitad con intercepto por competición (−0,00041). Son ganancias reales pero mínimas.
3. **Si se quiere actuar**: la más justificada es el intercepto por competición de la primera mitad (arregla Liga MX, objetivo concreto) y es barata (una constante por liga); la recalibración de «ambos marcan» exige tocar la salida de la matriz de marcadores y reentrenar, con una mejora de 0,7 % de skill.
   Ninguna se activa sin tu aprobación, y cualquier cambio de producción requiere reentrenar, comparar con el modelo activo y anotarlo en DEPLOYS.md.
