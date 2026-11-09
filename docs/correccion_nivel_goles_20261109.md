# Corrección del nivel de goles del Dixon-Coles — 9-nov-2026

## Problema (medido en el backtest de las ligas nuevas)
El Dixon-Coles crudo predice menos goles de los reales en 16 de 21 competiciones (−0,10 a −0,29 goles por partido en 11 de ellas).
Dos causas, medidas en `pit_oos.csv`:
1. **Deriva reciente**: el sesgo es casi nulo hasta abril de 2026 (−0,01 a −0,08) y salta a −0,20/−0,27 desde agosto, cuando los goles reales
   pasan de ≈ 2,75 a ≈ 3,05 por partido. La semivida de 270 días reacciona tarde.
2. **Pooling del nivel hacia la media de todas las ligas** (`POOL_BASE`): las ligas de muchos goles salen bajas (Noruega −0,26, Suiza −0,25,
   Eredivisie −0,22, MLS −0,17) y las de pocos salen altas (2. Bundesliga +0,10, Premier +0,08, Ligue 1 +0,08).

## Corrección propuesta
`DixonColes._nivel_reciente`: tras el ajuste, `base` de cada competición += log r, con
`r = (Σ w·goles + K) / (Σ w·(λ+μ) + K)` sobre los partidos de entrenamiento con pesos de semivida corta, tope [0,85; 1,20].
Cambia solo parámetros (`params.base`): el worker lo aplica sin cambios de código. Apagada por defecto (`DC_NIVEL_HALFLIFE_DAYS = 0`).

**Hiperparámetros fijados ANTES de medir** (no se eligen con el tramo de prueba): semivida 90 días, prior K = 60 goles ponderados.
Se informará también la sensibilidad (45 y 180 días), que NO decide.

## Criterios de aceptación (fijados el 9-nov-2026 antes de ejecutar; no se mueven después)
Comparación `nivel` contra `pit` (mismas filas, walk-forward desde 2025-07-01):
- **N1 nivel**: sesgo de goles totales agrupado en todo el tramo |predicho − real| ≤ 0,05; en ago-nov 2026 ≤ 0,10; y ≥ 75 % de las
  21 competiciones con |sesgo| ≤ 0,15.
- **N2 sin daño al 1X2**: log-loss 1X2 agrupado con la corrección menos sin ella ≤ +0,001, y ninguna competición con diferencia > +0,005
  y IC95 (errores por semana) entero por encima de 0.
- **N3 mercados de goles**: Brier medio agrupado de {over 1,5, over 2,5, over 3,5, ambos marcan, local más de 1,5, visitante más de 1,5}
  no empeora (diferencia ≤ 0) y ningún mercado empeora más de 0,002.
- **N4 alta probabilidad**: en el backtest de mercados (`backtest_mercados`), la familia goles de las 4 ligas aprobadas sigue «CUMPLE» en todas
  las franjas y la lista de mercados fuera (A2) no crece.
- **N5 no añade ruido en periodos estables**: en 2025-07 a 2026-04 el |sesgo| agrupado no empeora más de 0,03 respecto a `pit`.
Si se cumplen N1-N5 se propone activar `DC_NIVEL_HALFLIFE_DAYS = 90`; si falla alguno, no se activa y se documenta por qué.

## Resultado del candidato A (en muestra, semivida 90 días, prior 60): NO cumple N1
| Criterio | Antes | Con A | Resultado |
|---|---:|---:|---|
| N1 sesgo total (límite 0,05) | −0,085 | −0,062 | **falla** |
| N1 sesgo ago-nov 2026 (límite 0,10) | −0,219 | −0,169 | **falla** |
| N1 competiciones con \|sesgo\| ≤ 0,15 (límite 75 %) | 15 de 21 | 19 de 21 | cumple |
| N2 log-loss 1X2 (límite +0,001) | — | −0,00002, ninguna liga peor | cumple |
| N3 Brier de mercados de goles | — | −0,00018 (los 6 mejoran, IC95 [−0,00038, +0,00003]) | cumple |
| N5 periodo estable (límite +0,03) | −0,037 | −0,026 | cumple |

Sensibilidad (solo informa): 45 días deja el sesgo total en −0,054 y el reciente en −0,152; 180 días, −0,073 y −0,198. Ninguna cumple N1.
**Por qué se queda corto**: compara los goles reales con las lambdas del propio ajuste, y estas ya se adaptaron en parte a los partidos recientes
(se entrenaron con ellos), así que subestiman el sesgo que verá el partido siguiente. No daña nada, pero corrige solo ≈ 25-30 % del hueco.
No se activa. No se retocan los hiperparámetros con el tramo de prueba.

## Candidato B (fuera de muestra, fijado ANTES de evaluarlo)
Medir el sesgo con predicciones realmente fuera de muestra: en cada corte mensual, por competición,
`r = (Σ w·goles + K) / (Σ w·(λ+μ) + K)` sobre las filas del walk-forward con kickoff anterior al corte, w con semivida 60 días y K = 60,
tope [0,85; 1,20]; el factor multiplica λ y μ de los partidos del mes siguiente y se recalculan el 1X2 y los mercados. En producción equivale a
calcularlo en el reentreno mensual sobre las predicciones OOS ya registradas y fijarlo en `params.base` del artefacto (sin cambiar código del worker).
Se evalúa sobre la serie OOS que arranca en 2024-07-01 y se mide desde 2025-07-01, con los mismos N1-N5. Hiperparámetros fijos (60 días, K = 60);
la sensibilidad (30 y 120 días) solo informa. **Aviso**: B se diseñó después de ver el resultado de A y la deriva de ago-nov 2026 en el tramo de
prueba; el criterio es el mismo y los hiperparámetros no se ajustan con él, pero esa exposición queda declarada.

## Resultado del candidato B (fuera de muestra, 60 días, K = 60): tampoco cumple
Serie OOS desde 2024-07-01 (28 pasos), medida desde 2025-07-01; base = la misma serie sin corregir.
| Criterio | Antes | Con B | Resultado |
|---|---:|---:|---|
| N1 sesgo total (límite 0,05) | −0,085 | −0,046 | cumple |
| N1 sesgo ago-nov 2026 (límite 0,10) | −0,221 | −0,135 | **falla** |
| N1 competiciones con \|sesgo\| ≤ 0,15 (límite 75 %) | 14 de 21 | 19 de 21 | cumple |
| N2 log-loss 1X2 agrupado (límite +0,001) | — | +0,00001 | cumple |
| N2 ninguna competición peor en más de +0,005 con IC95 entero > 0 | — | **Europa League +0,0063, IC95 [+0,0002, +0,0124] (96 partidos)** | **falla** |
| N3 Brier de mercados de goles | — | −0,00004 (IC95 [−0,00044, +0,00035]; over 1,5 y 2,5 y visitante más de 1,5 suben ≤ 0,0001) | cumple |
| N5 periodo estable (límite +0,03) | −0,039 | −0,019 | cumple |
N4 no se evaluó porque N1 y N2 ya fallan.

## Conclusión: no se activa ninguna de las dos
- **A** (en muestra) corrige ≈ 25-30 % del hueco reciente y no daña nada, pero no cumple N1. **B** (fuera de muestra) corrige más (sesgo total −0,046;
  19 de 21 competiciones dentro de ±0,15), pero el sesgo de ago-nov sigue en −0,135 y empeora la Europa League, con solo 96 partidos.
- **El beneficio en probabilidad es ≈ 0 en ambas**: la mejora del Brier de los mercados de goles es de 0,0002 como mucho y su intervalo incluye el 0. Un
  sesgo de 0,2 goles por partido mueve «más de 2,5» unos 3-9 puntos en la ficha, pero ese error pesa poco en el Brier porque la mayoría de los partidos
  están lejos de esa línea.
- **Lo dominante es un cambio de régimen**, no un sesgo estructural: hasta abril de 2026 el sesgo es de −0,01 a −0,08 goles y salta a −0,20/−0,27 con
  el arranque de 2026/27 (los goles pasan de ≈ 2,75 a ≈ 3,05). Una corrección retrospectiva no puede anticipar un cambio así; ambas se quedan cortas
  precisamente donde más se necesita, y quitar el resto exigiría reaccionar más rápido a costa de más ruido (los prior y semividas más cortos no se probaron para no ajustar con el tramo de prueba).
- **El pooling de `base` hacia la media de ligas** sí es estructural (ligas de muchos goles bajas, de pocos altas) y las dos correcciones lo reducen
  (competiciones dentro de ±0,15: de 14-15 a 19 de 21).
- **Qué queda hecho**: `DixonColes._nivel_reciente` (apagada: `DC_NIVEL_HALFLIFE_DAYS = 0`) y el comparador `qf.eval.nivel_goles`, con pruebas. Si más adelante se
  quiere el efecto parcial de A (sin daño medido), basta entrenar en local con `DC_NIVEL_HALFLIFE_DAYS=90` y subir el artefacto: cambia solo `params.base`.
- **Recomendación**: dejar apagada, vigilar el sesgo de goles por liga cada semana (si el tramo ago-nov se normaliza, el problema desaparece solo) y seguir
  presentando más/menos y ambos marcan como probabilidad, no como señal (su skill sobre la base de la liga es ≈ 0, ver el informe de mercados).
