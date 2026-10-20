# Impacto por jugador del once real: primer bloque de contexto con evidencia (19-oct-2026)

Propuesta recibida el 19-oct (bloque de alineaciones) revisada contra lo ya medido. Lo que ya existía (valor del once, bajas,
descanso, clima) no mejoraba el modelo. Lo que no se había probado: medir el **apartamiento del once real respecto al habitual**,
ponderando cada jugador por su rendimiento histórico (`qf.model.jugadores`), en lugar del valor de mercado absoluto.

## Construcción (todo point-in-time: se recorre cronológicamente y cada partido se calcula antes de actualizar el estado)
- Fuerza del jugador: calificación de FotMob relativa a la media de su equipo en ese partido, acumulada y encogida a 0 (K = 8).
- Once habitual: los 11 con más titularidades en los últimos 5 partidos del equipo.
- `epi_total_*`: suma de fuerzas del once real menos la del habitual (positivo = hoy juega mejor once que de costumbre).
  `epi_grupos_*`: lo mismo por defensa (con portero), medios y delanteros. `xi_habitual_valor`: log del valor del once real / habitual.
- Datos: 871.401 apariciones de FotMob desde 2024. Cobertura del 99,2 % de los 4.255 partidos fuera de muestra.

## Resultado (walk-forward del candidato 2026.10.19-131830, 4.255 partidos; puerta de `ajuste.py`)

| Bloque | ΔRPS (30 % final) | p95 | Ligas que mejoran | ¿Pasa? |
|---|---|---|---|---|
| `epi_total` | −0,00053 | −0,00014 | 9/13 | Sí |
| `epi_grupos` | −0,00063 | −0,00013 | 10/13 | Sí |
| `xi_habitual_valor` | +0,00048 | +0,00109 | 6/13 | No (empeora) |
| `xi_valor` (anterior) | +0,00016 | +0,00028 | 3/13 | No |
| `bajas` (anterior) | −0,00001 | +0,00016 | 7/13 | No |

Variantes probadas en esta familia: 3 (`epi_total`, `epi_grupos`, `xi_habitual_valor`); las dos que pasan están muy correlacionadas.

### Estabilidad en cuatro particiones de validación (semántica de producción: sin intercepto, contra los lambdas crudos)

| Validación | n | `epi_total` ΔRPS (p95) | `epi_grupos` ΔRPS (p95) |
|---|---|---|---|
| 20 % | 851 | −0,00093 (−0,00049) | −0,00079 (−0,00028) |
| 30 % | 1.277 | −0,00053 (−0,00013) | −0,00064 (−0,00014) |
| 40 % | 1.702 | −0,00033 (+0,00009) | −0,00043 (+0,00008) |
| 50 % | 2.128 | −0,00033 (−0,00001) | −0,00047 (−0,00005) |

Siempre favorable; significativo en 3 de 4 particiones. **Placebo** (misma columna barajada entre partidos, 30 intentos): media
+0,00003, sd 0,00009, mínimo −0,00009. El efecto real queda a 4-10 desviaciones del ruido, y la prueba descarta una fuga de datos.

## Lectura honesta
- Es el primer bloque más fuerte y estable que la altitud (ΔRPS −0,0003 a −0,0009, 3/4 particiones, frente a −0,0002/−0,0003 y 1/4).
- **Es pequeño frente al mercado:** el A pierde ~0,0097 de RPS contra el mercado; el bloque recorta ~0,0005 (≈ 5 %). No va a
  hacer pasar solo la puerta de promoción (que exige batir a Elo y al mercado en las mismas filas). Hace falta sumarlo a otros y comparar
  con el mercado del mismo momento (F9).
- **Necesita el once confirmado (T-60):** no entra a la corrida de las 03:00. Solo puede aplicarse en el sello tardío (F7), que sigue
  apagado. Además la medición usa el once real que FotMob guardó tras el partido; en producción vendría de `lineups` y de
  `puente_jugador`, y habrá pérdidas de mapeo.
- La fuerza usa calificaciones post-partido de partidos anteriores: son conocidas a la hora de predecir, pero FotMob puede
  recalificar; se asume estable.

## Para aplicarlo
1. Función de producción: dado el once confirmado de un partido, calcular `epi_total_local/visita` con el estado de FotMob hasta ahora.
2. Ajuste `ajuste_xi` (como `ajuste_altitud`): una sola variable, sin intercepto, factor exactamente 1 con delta neutro, en MODO SOMBRA
   dentro de la predicción `final` (`data_completeness.ajuste_xi`) sin tocar los lambdas sellados.
3. Eso exige fijar `hashchain.LOTE_POR_PARTIDO_DESDE` (sello por partido en la cadena pública): decisión del titular.
4. Con ≥ 150 partidos medidos hacia adelante, comparar con y sin el factor y pasar a `activo` solo si se confirma.

## Con la muestra ampliada (20-oct-2026): el efecto es real pero más pequeño

Walk-forward ampliado a 2024-01 – 2026-10 con la misma función y parámetros del reentrenamiento: **11.920 partidos** (casi el triple;
9.670 con cierre de Pinnacle), cobertura del bloque 94,4 %. La primera medición (1.277 partidos de validación) sobreestimaba el efecto
(maldición del ganador: se midió justo la variante que mejor salió).

| Validación | n | `epi_total` ΔRPS (p95) | `epi_grupos` ΔRPS (p95) | Pasa la puerta |
|---|---|---|---|---|
| 20 % | 2.384 | −0,00031 (+0,000004) | −0,00027 (+0,00006) | no |
| 30 % | 3.576 | −0,00018 (+0,00008) | −0,00011 (+0,00017) | no |
| 40 % | 4.768 | −0,00023 (−0,00002) | −0,00015 (+0,00011) | no (`epi_total` sí en producción) |
| 50 % | 5.960 | −0,00032 (−0,00014) | −0,00032 (−0,00011) | sí |

Validación **secuencial** (ajusta con todo lo anterior y valida en el tramo siguiente, 5 tramos de 1.788 partidos): `epi_total` mejora
en los **5 tramos** (−0,00002 a −0,00049; p95 < 0 en 3 de 5); `epi_grupos` también en 5 de 5. Placebo (columna barajada, 30 intentos):
media +0,00001, sd 0,00003: el efecto real queda a 6-10 desviaciones del ruido. Sobre las filas con cierre de Pinnacle del 30 % final
(n = 1.428) no se aprecia diferencia (0,20297 → 0,20298; Pinnacle 0,19215): con ese n un efecto de 0,0002 no es detectable.

**Lectura honesta:** la señal es consistente en el tiempo y nunca perjudica, pero vale ~−0,0002 de RPS (≈ 2 % de la brecha con el
mercado) y solo pasa la puerta estricta (p95 < 0) en una de cuatro particiones. No es un bloque para activar: se queda en MODO SOMBRA
y se decide con la medición hacia adelante. Los coeficientes apenas cambian con la muestra triple (propio 0,027 → 0,024; rival
−0,022 → −0,022), lo que apoya que el modelo está bien estimado aunque el efecto sea chico.

El artefacto en sombra se reajustó con la muestra completa: `ajuste_xi_ampliado-2024-01-01_2026-10-19.pkl` (reemplaza al de 4.255 partidos;
con el once local 2 desviaciones peor el factor del visitante pasa de 1,038 a 1,023).
