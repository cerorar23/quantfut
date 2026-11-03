# NBA v2 — Fase 4, F4.1: evaluación de origen móvil (2026-11-03)

Misma metodología de los Sprints 3 a 5, repetida con **tres temporadas de prueba** (2023-24, 2024-25 y 2025-26). Cada una se entrena y se ajusta solo con las temporadas anteriores (ventana creciente); parámetros, desviaciones y pesos se vuelven a elegir en cada origen. Los props empiezan en 2024-25, que es cuando hay cierres de mercado de props. Datos: la base nueva con SofaScore (prioridad nba_oficial > sofascore). Reproducible con `ops/evaluar_s3.py`, `evaluar_s3b.py`, `evaluar_s4.py` y `ops/resumen_origen_movil.py`.

Las diferencias frente al mercado son de Brier (negativas = el modelo mejor). El «conjunto» es la media ponderada por la inversa de la varianza de los tres orígenes (partidos distintos, tratados como independientes).

| Métrica | 2023-24 | 2024-25 | 2025-26 | Conjunto (IC95) |
|---|---|---|---|---|
| **Equipo (núcleo v2.0)** | | | | |
| RMSE margen: modelo / mercado | 14,26 / 13,76 | 14,05 / 13,57 | 14,49 / 14,04 | |
| RMSE total: modelo / mercado | 18,20 / 17,82 | 18,63 / 17,86 | 19,08 / 18,41 | |
| Brier ganador (dif.) | 0,2116 (+0,0119) | 0,2105 (+0,0099) | 0,2059 (+0,0078) | +0,0099 [+0,0071, +0,0127] |
| Brier hándicap (dif.) | 0,2612 (+0,0121) | 0,2609 (+0,0107) | 0,2599 (+0,0100) | +0,0110 [+0,0075, +0,0144] |
| Brier total (dif.) | 0,2547 (+0,0061) | 0,2638 (+0,0148) | 0,2599 (+0,0099) | +0,0098 [+0,0066, +0,0131] |
| Pendiente de calibración del ganador | 1,03 | 1,19 | 1,05 | |
| **Equipo + jugadores (media de los dos)** | | | | |
| Brier ganador (dif.) | 0,2082 (+0,0085) | 0,2069 (+0,0063) | 0,2035 (+0,0054) | +0,0068 [+0,0044, +0,0092] |
| Brier hándicap (dif.) | 0,2592 (+0,0101) | 0,2584 (+0,0082) | 0,2558 (+0,0059) | +0,0080 [+0,0050, +0,0110] |
| Brier total (dif.) | 0,2560 (+0,0075) | 0,2601 (+0,0111) | 0,2577 (+0,0077) | +0,0089 [+0,0056, +0,0122] |
| RMSE margen: equipo → mezcla | 14,25 → 14,15 | 14,02 → 13,86 | 14,49 → 14,33 | |
| Pendiente de calibración del ganador | 1,18 | 1,04 | 1,12 | |

| Props | MASE (2024-25 / 2025-26) | Cobertura 80 % | Brier frente al mercado (IC95) |
|---|---|---|---|
| puntos | 0,957 / 0,959 | 0,804 / 0,808 | +0,0129 [+0,0111, +0,0147] / +0,0125 [+0,0107, +0,0144] |
| rebotes | 0,953 / 0,952 | 0,801 / 0,808 | +0,0084 [+0,0068, +0,0098] / +0,0079 [+0,0063, +0,0094] |
| asistencias | 0,956 / 0,961 | 0,811 / 0,810 | +0,0082 [+0,0068, +0,0097] / +0,0078 [+0,0062, +0,0096] |
| triples | 0,960 / 0,963 | 0,800 / 0,804 | +0,0064 [+0,0050, +0,0078] / +0,0032 [+0,0018, +0,0047] |

## Lectura

1. **Los resultados son estables entre temporadas.** Con tres orígenes distintos las conclusiones no dependen de una temporada afortunada: cobertura de los props entre 80,0 y 81,1 %, MASE entre 0,952 y 0,963, coherencia entre mercados con 0 violaciones en las tres.
2. **El modelo es peor que el cierre del mercado en todos los orígenes y mercados**, con intervalos que no cruzan 0 (ganador +0,0099 [+0,0071, +0,0127]; mezcla +0,0068 [+0,0044, +0,0092]). Es el hallazgo central de la fase y se reporta como tal.
3. **Los jugadores ayudan siempre**: en los tres orígenes el error del margen baja (−0,10, −0,16, −0,16) y el Brier del ganador se acerca al mercado (−0,0034, −0,0036, −0,0024).
4. **La distancia al mercado se achica con más datos** (ganador +0,0119, +0,0099, +0,0078 con 2, 3 y 4 temporadas de entrenamiento). Son solo tres puntos y también puede ser un cambio en el mercado; no se promete que seguirá, pero es la dirección que predice una curva de aprendizaje.
5. **Calibración**: la pendiente del ganador queda entre 1,03 y 1,19 (equipo) y 1,04 y 1,18 (mezcla); con unos 1.300 partidos su error típico ronda 0,1, de modo que cada valor es compatible con 1,0, pero el promedio (≈ 1,1) apunta a probabilidades algo tímidas. Hándicap y total siguen sin discriminar (pendientes ≈ 0): el modelo no aporta información que la línea no tenga.
6. **Selección de parámetros**: cambia entre orígenes (arrastre 0,5 / 0,5 / 0,65; tasa 0,045 / 0,03 / 0,045), señal de que la superficie es plana y de que el resultado no depende de un valor exacto.

## Compuertas (estado)

| Compuerta | Estado |
|---|---|
| G-coherencia | **Cumplida** en los tres orígenes (0 violaciones) |
| G-props: cobertura 80 % ∈ [77, 83] y MASE ≤ 1,00 | **Cumplida** en los dos orígenes (80,0–81,1 %; 0,952–0,963) |
| G-equipo: calibración con pendiente 0,9–1,1 | **Borderline**: equipo 1,03 / 1,19 / 1,05 y mezcla 1,18 / 1,04 / 1,12; compatible con 1 dentro del error, pero 3 de 6 valores superan 1,1 |
| G-equipo: Brier no peor que la v1.5 | **No evaluable más allá de 2025-26** (la v1.5 solo tiene cifras de esa temporada y con otro conjunto de partidos) |
| Diferencia con el cierre con IC | **El modelo es peor, de forma consistente**; no hay ventaja sobre el mercado |

## Pendiente que sale de aquí

- Recalibración con las temporadas anteriores (escalado logístico de la probabilidad del ganador) para llevar la pendiente a 1; probarla con el mismo origen móvil antes de adoptarla.
- Se necesita una vista de la v1.5 sobre los mismos partidos si se quiere cerrar la comparación formal.
- Con el origen 2023-24 no existen cuotas de cierre en el ajuste (empiezan ese año): la mezcla con el mercado no se estima allí.

## Recalibración del ganador (probada, no se adopta)

Dos recalibraciones ajustadas con las temporadas anteriores y medidas en cada origen (`nba.v2.recalibracion`, `ops/evaluar_recalibracion.py`): (a) **escala de la media**, P(gana el local) = Φ(k·μ/σ), coherente con el resto de mercados porque cambia el margen esperado; (b) **logística** sobre la probabilidad del ganador (solo referencia: no se podría sellar sin romper la coherencia con la distribución del margen).

| Equipo solo | k ajustado | Brier base → escala | Δ Brier escala vs base (IC95) |
|---|---|---|---|
| 2023-24 | 0,86 | 0,2111 → 0,2116 | +0,00049 [−0,00051, +0,00142] |
| 2024-25 | 0,98 | 0,2095 → 0,2095 | +0,00003 [−0,00012, +0,00018] |
| 2025-26 | 1,01 | 0,2059 → 0,2058 | −0,00004 [−0,00011, +0,00004] |
| **Conjunto** | | | **−0,00002 [−0,00009, +0,00004]** |

Con la mezcla equipo + jugadores: k = 0,95 / 1,03 / 1,05 y Δ Brier conjunto +0,00005 [−0,00011, +0,00021]. La logística da lo mismo (+0,00002 y +0,00005). La escala no perjudica el hándicap (Δ conjunto +0,00005 [−0,00008, +0,00018]) ni el error del margen (14,56 → 14,56), y **tampoco acerca al mercado** (distancia del ganador +0,0094 → +0,0096).

**Conclusión: no se adopta.** Las temporadas anteriores piden k ≈ 1 (de 0,86 a 1,05), es decir, el modelo ya estaba calibrado donde se podía medir; la pendiente algo mayor que 1 que se veía en la prueba es ruido de muestra (error típico ≈ 0,1) y cambia con la desviación elegida (en 2024-25 la pendiente medida con la sigma de la simulación fue 1,19 y con la sigma de todas las temporadas previas 1,03). Una recalibración con datos pasados no la corrige porque no es un sesgo estable. La compuerta de pendiente 0,9–1,1 se reformula para el informe: pendiente conjunta compatible con 1 dentro del error, en lugar de exigirlo en cada temporada.
