# Córners: el modelo está calibrado; lo que parecía un sesgo era ruido de picks correlacionados (19-oct-2026)

Punto de partida (mío, y estaba mal planteado): el 19-oct dije que los «menos de» de córners publicados se quedaban ~5 puntos cortos
(prometido 72,6 %, real 67,6 %, 349 picks) y que convenía recalibrar por lado. Medido a fondo, **no hay que recalibrar nada**.

## Qué se midió (`python -m qf.eval.corners_diagnostico`, solo lectura)

1. **El modelo solo, en walk-forward sobre todo el historial** (41.815 partidos, 23 ligas, desde 2019, mismos parámetros que producción):
   las cinco líneas publicadas (más de 6,5 y 8,5, menos de 10,5, 11,5 y 12,5), cuando el modelo da 62-95 %, quedan a **menos de 0,6
   puntos** de lo prometido. También en las ligas «otras» (Argentina, Brasil, México, MLS, nórdicas) y desde julio de 2025. El nivel
   medio por liga es correcto (sesgo menor de 0,15 córners por partido; solo la Champions +0,39) y la pendiente de calibración es 0,977.
2. **Lo publicado es lo mismo que el walk-forward:** la probabilidad guardada del modelo coincide con la reconstruida (correlación
   0,999) y los resultados guardados coinciden al 100 % con los córners finales de `matches`. No hay error de liquidación ni de datos.
3. **El déficit viene del tamaño de muestra, no del modelo:** 601 picks de córners totales eran **170 partidos** (hasta 4 picks por
   partido, muy correlacionados). Con el error estándar por partido, el déficit de los «menos de» es **−5,0 puntos con ±3,6**
   (z = −1,4; contando cada pick como independiente habría salido z = −2,0). Los «más de»: +2,6 con ±3,0 (z = +0,9). Dos semanas de datos.
4. **¿Alguna variable nueva mejora la predicción del total?** Se probó clima, altitud, descanso, desbalance de equipos (valor del once),
   goles esperados del modelo A y bajas, ajustando en lo anterior y validando en el 30 % final: **todas empeoran** el error cuadrático.

## Qué se concluye

- No se toca el modelo de córners ni se recalibra por liga o por lado: se empeoraría un modelo calibrado con dos semanas de datos.
- La alta probabilidad de córners pierde ~10 % a cuota de referencia (664 picks con cuota) por el **margen de las casas**, no por el
  modelo: acierta lo que promete. Es una línea de acierto (decisión del 5-oct), no de valor.
- Regla que se queda: **un déficit medido sobre picks del mismo partido se mide por partido** (`error_estandar_por_partido`). Las tablas
  «por mercado» de `/alta-probabilidad` cuentan picks, no partidos: leerlas con ese margen. Mejora pendiente y barata: añadir a esas tablas
  el número de partidos distintos.

## Para repetir

`python -m qf.eval.corners_diagnostico` (necesita la base; tarda unos minutos). Volver a correrlo tras cualquier cambio del modelo de
córners y cuando haya meses de datos nuevos.
