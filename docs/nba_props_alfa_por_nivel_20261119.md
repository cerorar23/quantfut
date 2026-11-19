# Props NBA: sobredispersión de puntos por nivel de rol (2026-11-19)

**Origen.** La fase 0 del parley de un solo partido (`docs/nba_sgp_f0_correlaciones_20261119.md`, PR #521) encontró que, en jugadores
con ≥ 20 minutos esperados, el prop de puntos supera su cuantil 25 % pronosticado el 79–82 % de las veces, no el 75 %.

## Causa

El conteo es una binomial negativa con **una sola** sobredispersión `alfa` por estadística, estimada con todos los jugadores. Medida
por nivel de rol (los mismos niveles del prior: < 10, 10–16, 16–22, 22–28, 28–34 y ≥ 34 minutos esperados), en puntos va de ≈ 0,70
(suplentes) a ≈ 0,07 (estrellas). Con la global de 0,22 los titulares salen demasiado anchos en las dos colas y los suplentes
demasiado estrechos. **No es un problema de minutos:** el patrón se repite al usar los minutos reales.

## Medición hacia adelante (`apps/nba/ops/f51_alfa_por_nivel.py`)

Con los (k, decaimiento) de producción (30; 0,97) y todo ajustado con temporadas anteriores. Log-verosimilitud media por fila,
por nivel menos global, con IC 95 % por bootstrap de días:

| Estadística | 2024-25 | 2025-26 | 2026-27 |
|---|---|---|---|
| **Puntos** | **+0,0263 [+0,0238; +0,0288]** | **+0,0293 [+0,0269; +0,0320]** | **+0,0204 [+0,0117; +0,0283]** |
| Rebotes | −0,0002 | −0,0003 | −0,0002 |
| Asistencias | +0,0006 | +0,0005 | +0,0006 (IC incluye el 0) |
| Triples | −0,0002 | +0,0003 | −0,0001 |

Solo cambia la de puntos. En las otras tres la ganancia es nula y la alfa por nivel es inestable (asistencias: 0,001 en un nivel y 0,2 en el contiguo).

Colas del PIT de puntos, jugadores con ≥ 20 minutos esperados (calibrado: 0,10 / 0,25 / 0,25 / 0,10; cobertura 0,80):

| Temporada | Variante | < 0,10 | < 0,25 | > 0,75 | > 0,90 | Cobertura 80 % |
|---|---|---|---|---|---|---|
| 2024-25 | global | 0,076 | 0,192 | 0,246 | 0,068 | 0,856 |
| 2024-25 | por nivel | 0,108 | 0,243 | 0,268 | 0,099 | 0,793 |
| 2025-26 | global | 0,073 | 0,180 | 0,242 | 0,066 | 0,861 |
| 2025-26 | por nivel | 0,101 | 0,225 | 0,263 | 0,093 | 0,805 |
| 2026-27 | global | 0,095 | 0,216 | 0,204 | 0,056 | 0,849 |
| 2026-27 | por nivel | 0,128 | 0,263 | 0,224 | 0,079 | 0,793 |

Queda pendiente: con ≥ 34 minutos la cola alta sigue algo estrecha (> 0,90: 0,06–0,08). Los suplentes (< 20 minutos) siguen estrechos
(cobertura 0,74–0,77): su incertidumbre es de minutos, no de conteo, y casi no tienen línea en las casas.

## Cambio

- `props.estimar_alfa_por_nivel` y `props.alfa_para`. El motor (`motor_jugadores`) usa la alfa del nivel de cada jugador.
- El artefacto pasa a `formato: 2` con `alfa_por_nivel` **solo para puntos**. El resto del archivo no cambia: es el del 2-nov.
  Los seis valores salen de `entrenar_props.py` con datos hasta el 2026-11-02 (exportación del 19-nov; 296 filas más que el
  entrenamiento original, por datos que llegaron después). `cargar_props` sigue leyendo el formato 1.
- `VERSION_PROPS` pasa a `props-2.2`. La huella del artefacto pasa de `6323d806ed81` a `c5da73f48db2`. Los sellos anteriores no se tocan.

Para que llegue a producción hay que desplegar la imagen del motor NBA con este artefacto, con autorización del titular y anotándolo en `DEPLOYS.md`.
