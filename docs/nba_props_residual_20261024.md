# NBA — modelo de props anclado en el mercado: resultado (24-oct-2026)

Código: `apps/nba/src/nba/props_residual.py`. Pruebas: `apps/nba/tests/test_props_residual.py` (10).
Protocolo congelado antes de calcular: `apps/nba/nba_props_residual_protocol.json` (hash en
`apps/nba/.local/normalized/nba_props_residual_20261024/protocol_frozen.json`). Informe completo y coeficientes en esa carpeta.
Investigación: no genera apuestas, no promueve nada, no reentrena el motor vivo.

## Pregunta
¿Un modelo que parte del consenso sin margen de las 8 casas de EE. UU. y lo corrige con el v1 de jugador, la disponibilidad (reportes T-60),
el entorno del partido (total y hándicap de bet365 «as-of» el momento del precio, ritmo, defensa rival, descanso, localía, minutos) añade
información calibrada, en puntos, rebotes, asistencias y triples? Entrena con 2024-25 y se evalúa sin reajustar en 2025-26.

## Universo y controles
294.688 unidades con precio y modelo v1. Se descartan 4.859 de partidos fuera de los datos extendidos, **1.566 cuyo precio es más de 60 min antes del salto**
(un reporte T-60 podría contener información que el precio aún no tenía) y 237 sin cuota de bet365 anterior al precio. Prueba de
reproducción superada: la diferencia v1-contra-mercado publicada se reprodujo a 1e-9 en los ocho casos mercado/temporada.
Unidades de prueba 2025-26: puntos 95.566, rebotes 36.275, asistencias 26.394, triples 20.719.

## Resultado (Brier, diferencia contra el consenso crudo; negativo = mejor; entre corchetes el intervalo del 98,75 %, remuestreo por fechas)
| Mercado | Brier del mercado | Solo recalibrar (A) | Modelo completo (E) | E contra A | Walk-forward mensual (E) | Placebo | Veredicto del protocolo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Puntos | 0,23497 | −0,00007 [−0,00013; 0,00000] | −0,00010 [−0,00024; +0,00002] | −0,00003 [−0,00016; +0,00009] | −0,00009 [−0,00023; +0,00003] | −0,00008 | sin evidencia |
| Rebotes | 0,23732 | −0,00035 [−0,00061; −0,00004] | −0,00030 [−0,00050; −0,00008] | +0,00005 [−0,00012; +0,00021] | −0,00039 [−0,00059; −0,00018] | −0,00033 [−0,00055; −0,00012] | solo calibración; **control del placebo falla** |
| Asistencias | 0,23967 | −0,00003 [−0,00009; +0,00003] | −0,00020 [−0,00042; +0,00001] | −0,00017 [−0,00041; +0,00004] | −0,00021 [−0,00042; −0,00002] | +0,00016 (peor) | sin evidencia (cota superior +0,00001) |
| Triples | 0,23635 | −0,00032 [−0,00049; −0,00013] | −0,00032 [−0,00050; −0,00014] | 0,00000 [−0,00018; +0,00020] | −0,00040 [−0,00062; −0,00020] | −0,00025 [−0,00035; −0,00014] | solo calibración; **control del placebo falla** |

## Lectura
- **El mercado es muy difícil de superar con estas variables.** La mejora máxima es de 0,0004 de Brier (0,17 %), en el orden de la incertidumbre.
  Ninguno de los cuatro mercados cumple «añade información».
- **Rebotes y triples: la mejora es solo recalibración.** Recalibrar el consenso (a, b) ya da el mismo resultado que el modelo completo
  (E contra A ≈ 0). Coincide con el sesgo conocido del consenso: sobrevalora el Over entre 1,2 y 2,1 puntos de probabilidad
  (puntos 1,2; rebotes 1,8; asistencias 0,8; triples 2,1), y el desplazamiento aprendido en 2024-25 (a entre −0,01 y −0,04 en logit) sigue mejorando en 2025-26.
- **Asistencias es el único indicio de algo más** (entorno: descanso, defensa rival y minutos; −0,0002, cota superior +0,00001) y el placebo empeora
  (+0,00016), así que no parece fuga. No alcanza la regla; queda como hipótesis para la prueba hacia adelante con PropLine, no como hallazgo.
- Los coeficientes del modelo completo son pequeños (|θ| ≤ 0,03 en logit estandarizado) y la regularización elige el máximo de la rejilla (0,1) en
  casi todos los casos: los datos piden contraer las variables hacia cero.

## Control del placebo: defecto del protocolo (importante)
El protocolo exigía que el placebo (variables barajadas dentro de fecha y mercado) no mejorara al mercado crudo, «de lo contrario hay fuga y la
corrida es nula». Pero el placebo conserva la recalibración (a, b) y el v1, que por sí solos ya mejoran al mercado crudo en rebotes y triples.
Es decir, el control confundía recalibración con fuga. **Por la letra del protocolo congelado, rebotes y triples quedan como corrida nula**: no se
afirma nada de ellos. No cambia la conclusión (el veredicto ya era «solo calibración», no «añade información») ni hay indicio de fuga: en puntos y
asistencias el placebo sale limpio, y la reproducción exacta del v1 y la regla «precio después de T-60» limitan la fuente de fuga más probable.
Si se quiere repetir, el control correcto es **placebo contra la recalibración (A)**, no contra el mercado crudo; eso exige un protocolo v1.1
declarado antes de volver a correr y marcado como posterior a ver estos números.

## Qué significa para el motor
- Con precio de mercado disponible, la mejor probabilidad de props no es el modelo v1 sino **el consenso recalibrado** (restar entre 0,01 y 0,04 en logit al
  Over); las variables propias no añaden mucho encima.
- Donde **no hay precio** (robos, tapones, pérdidas, combinados, dobles-dobles), este resultado no aplica: el motor depende de su propio modelo y se
  evalúa contra el resultado real. Ahí sí conviene probar las variables de entorno y disponibilidad, midiendo calibración y cobertura, no contra una cuota.
- Siguiente prueba limpia: puntuar el modelo ajustado, sin tocarlo, sobre el archivo de PropLine a medida que se acumule (consenso de las 6 casas presentes en
  ambos lados; Pinnacle como serie aparte), con asistencias como mercado prioritario.

## Límites
Una sola captura 30-45 min antes del salto (no es cierre), casas de EE. UU., cuatro mercados, dos temporadas. Los cuatro mercados se corrigieron con Bonferroni
(98,75 %). Sin pruebas de rentabilidad, límites de apuesta ni líneas alternativas.
