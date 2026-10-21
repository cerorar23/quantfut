# La información nueva en el motor: qué entra y qué no (19-oct-2026)

Pedido del titular: que la información capturada desde el 18-oct (calendario, clima, bajas, valor del once, altitud) **entre a los
motores**. Regla del proyecto, que el titular reforzó en su revisión: una señal entra solo si mejora al modelo **fuera de
muestra**, con significancia y estabilidad. Esta página es la medición de cada bloque y la decisión.

Herramienta: `python -m qf.model.contexto` (mide cada bloque contra el modelo solo de nivel con el walk-forward del 12-oct:
4.192 partidos, 13 ligas, un año; validación en el 30 % final; puerta de `ajuste.py`). Es solo lectura.

## Resultado por bloque (30 % final, 1.258 partidos de validación)

| Bloque | Variables | ΔRPS | ¿Pasa? | Comentario |
|---|---|---|---|---|
| Altitud | altitud de la sede y salto de altura del visitante | −0,00039 | **Sí** | ver abajo: evidencia débil |
| Clima (ERA5, observado) | temperatura, humedad, viento, lluvia, nubosidad | −0,00020 | No | p95 > 0 en las 4 particiones; el signo cambia con 50 % |
| Descanso y carga | días de descanso, partidos en 14 días (calendario completo) | +0,00014 | No | empeora |
| Bajas (FotMob) | valor perdido relativo y número de bajas | +0,00002 | No | sin efecto |
| Valor del once | diferencia de valor y de edad del once real | +0,00013 | No | empeora; además el once real no se conoce a las 03:00 |

Lo que **no** significa: que descanso, bajas o clima no importen en el fútbol. Significa que, con este modelo, un año de datos y
estas variables sencillas, no se les ve efecto fuera de muestra; el mercado ya los descuenta en gran parte. Las bajas y el clima
tienen además un problema de momento: se midieron con datos posteriores al partido (bajas reconstruidas, clima observado), no con
lo que se sabía antes. Los equivalentes previos (`fotmob_previo`) se acumulan desde el 18-oct y harán falta semanas.

## La altitud: por qué solo en sombra

Dos medidas distintas del mismo bloque, porque la primera engañaba:

1. **Con la puerta tal cual** (el modelo con el bloque re-nivela su intercepto; la referencia también): pasa en 3 de 4 particiones.
   Pero parte de la ganancia en ligas sin altura (Eredivisie, copas) era solo ese re-nivelado, y en producción el ajuste **no** lleva
   intercepto.
2. **Con la semántica de producción** (sin intercepto, contra los lambdas sin ajustar), para la variable más defendible, solo el
   **salto de altura** del visitante: ΔRPS −0,0002 a −0,0003, siempre favorable pero **significativo en 1 de 4 particiones** (30 %).
   Gana en México (−0,0006, 104 partidos), España, Brasil y Argentina.

La versión con la altitud de la sede además del salto pasaba mejor, pero bajaba un 6 % el λ del local en América–Pachuca (ambos de
altura): un artefacto de variables correlacionadas, sin sentido físico. Se descartó.

**Decisión:** entra al motor en **modo sombra**. Cada predicción (de las 13 ligas) guarda en `data_completeness.ajuste_altitud` el
factor que se habría aplicado, pero los lambdas publicados no cambian: lo sellado es público e inmutable y la evidencia es débil.
Con los partidos reales de las próximas semanas se mide la ganancia hacia adelante y se decide pasar a `activo`.

## Qué quedó desplegado

- `qf.model.contexto` (medición) y `qf.model.ajuste_altitud` (ajuste con una sola variable, sin intercepto, a prueba de fallos).
- `daily.py` aplica el ajuste tras el calibrador según `AJUSTE_ALTITUD_MODO` (`off`, `sombra` por defecto, `activo`).
- Artefacto `ajuste_altitud_2026.10.12-221104.pkl` ajustado con el walk-forward del 12-oct (ver «Pendiente»).
- Hoy: 145 partidos próximos con registro, 35 con efecto mayor al 0,5 % (Toluca ×1,14 al local frente a un visitante de nivel del
  mar; Madrid ×1,03; América–Pachuca ×1,00), y los lambdas intactos en todos.

## Para pasarlo a activo (una sola variable)

`AJUSTE_ALTITUD_MODO=activo` en el `.env` del servidor y reiniciar el worker (o en `/etc/environment` del contenedor en marcha).
Se recomienda esperar a tener ≥ 150 partidos con salto > 0,5 km medidos hacia adelante y comparar, con `data_completeness`, el RPS
real con y sin el factor.

## Pendiente

- Reajustar el artefacto con el walk-forward de cada reentrenamiento (`python -m qf.model.ajuste_altitud --guardar`): hoy usa el
  del 12-oct, de un modelo no activado, y el activo es el del 27-sep. El efecto relativo de la altitud cambia poco, pero hay que
  automatizarlo al entrar en el reentrenamiento del 1-nov.
- Repetir `python -m qf.model.contexto` cuando haya semanas de `fotmob_previo` (bajas y pronóstico de clima previos) y después de
  cada reentrenamiento. Es la forma de que los bloques que hoy no pasan tengan su oportunidad con datos mejores.
- Esto es solo el motor A. Para que algo llegue a los productos que se venden (alta probabilidad, escalera, parley, que salen del
  mercado: motor B) hace falta F8, la mezcla A + B aprendida, evaluada contra el mercado del mismo momento (F9).
