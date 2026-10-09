# NBA-RUN-050 — minutos de regulación y evaluación F4

Fecha de trabajo: 7 de octubre de 2026, America/Mexico_City. Investigación retrospectiva local, sin promoción a producción ni aprobación de gates. Los sellos UTC pueden corresponder al 8 de octubre.

El candidato reciente mejora modestamente al baseline histórico en tres temporadas y nueve bloques temporales. Su error medio es **4,869 minutos**, frente a **4,965**; la distribución mejora de **3,664 a 3,548 CRPS**. Sin embargo, el intervalo central nominal del 80% solo cubre **70,663%** de los resultados. La mejora permite continuar investigando F4; no acredita calibración suficiente, disponibilidad previa ni una proyección válida de rotaciones de equipo.

## Datos consolidados

Se derivaron **159.075 etiquetas jugador/partido**, correspondientes a **6.150 partidos de temporada regular**, desde los 259.826 tramos de cancha aceptados y los rosters archivados. Cada uno de los 12.300 pares equipo/partido conserva **240 minutos de regulación**. Se suman exclusivamente los periodos 1–4: las prórrogas se validan y conservan como metadatos, pero no se convierten en minutos de regulación ni se reescalan a 48.

| Temporada | Partidos | Etiquetas de roster | Tiempo positivo | Cero regulación | Partidos con prórroga |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2021-22 | 1.230 | 31.029 | 26.035 | 4.994 | 58 |
| 2022-23 | 1.230 | 31.268 | 25.886 | 5.382 | 79 |
| 2023-24 | 1.230 | 32.156 | 26.396 | 5.760 | 59 |
| 2024-25 | 1.230 | 32.504 | 26.302 | 6.202 | 60 |
| 2025-26 | 1.230 | 32.118 | 26.638 | 5.480 | 54 |

Se preservaron las 164.218 filas del boxscore original; las 5.143 de pretemporada quedan fuera de esta etiqueta regular. Cero minutos de regulación no equivale necesariamente a DNP: puede haber participación exclusiva en prórroga. Se conservan por separado minutos, estado y participación del boxscore.

El primer intento se rechazó antes de producir métricas porque **28 filas de 0022400942 carecían de namespace**. El segundo utiliza una capa derivada que exige coincidencia exacta del roster oficial completo, persona, equipo, puntos, rebotes, asistencias y estado con el NBA BoxScoreTraditionalV3 archivado y su hash previamente aceptado. Los archivos originales permanecen intactos. El protocolo rechazado y sus fuentes anteriores se conservan como evidencia; no se presenta como una corrida exitosa.

## Protocolo y alcance de la comparación

Versión `F4-regulation-minutes-exploratory-v2`. Protocolo y hashes registrados localmente en el evento 100 antes de calcular estas métricas; el evento 99 conserva el intento rechazado. Semilla **20261007**, 1.000 réplicas bootstrap por fecha, tres bloques por temporada definidos por las fechas del censo completo.

- Baseline: distribución empírica de las diez apariciones previas con tiempo positivo en regulación.
- Candidato: centro de las últimas cinco apariciones encogido hacia la media de hasta veinte, con peso de cinco pseudoapariciones. La distribución usa los residuos de ese historial de hasta veinte, trasladados al centro y limitados al soporte 0–48.
- Mínimo: diez apariciones positivas previas de la misma temporada. No se incorporan resultados del día objetivo ni de fechas posteriores. Las predicciones y sus resultados se guardan en archivos distintos.
- Métrica primaria: CRPS continuo de minutos; menor es mejor. MAE, RMSE, cobertura y anchura central del 80% son diagnósticos secundarios. El MAE usa la media de cada distribución como estimación central.

El candidato modifica tanto el centro como el tamaño del historial de la distribución. Esta comparación mide su efecto combinado; no atribuye toda la mejora al encogimiento reciente.

La muestra se define **después del evento** por participación positiva observada. No pronostica quién estará disponible. Los datos históricos ya habían sido inspeccionados y este protocolo reutiliza una referencia anterior: es un análisis exploratorio, sin test confirmatorio intacto ni prueba de recepción previa. Los intervalos descriptivos no tienen corrección por comparaciones múltiples ni constituyen garantía de generalización.

## Resultados

| Temporada | Casos | Partidos evaluados | CRPS baseline → candidato | MAE baseline → candidato | Cobertura candidato |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023-24 | 21.035 | 1.086 | 3,650 → 3,540 | 4,953 → 4,872 | 70,630% |
| 2024-25 | 20.928 | 1.085 | 3,685 → 3,574 | 4,990 → 4,897 | 70,566% |
| 2025-26 | 21.192 | 1.085 | 3,657 → 3,529 | 4,954 → 4,840 | 70,791% |
| Total | **63.155** | **3.256** | **3,664 → 3,548** | **4,965 → 4,869** | **70,663%** |

433 fechas evaluadas. Diferencia candidato menos baseline: CRPS **−0,1159**, intervalo exploratorio 95% por fecha **[−0,1235; −0,1080]**; MAE **−0,0959 minutos**, intervalo **[−0,1067; −0,0855]**. RMSE **6,521 → 6,381**. La anchura media del intervalo central crece de **11,450 a 12,973 minutos** y su cobertura mejora de **63,322% a 70,663%**, todavía inferior al 80% nominal.

Los nueve bloques tienen diferencia media favorable en CRPS y MAE. Por historial de minutos, el estrato de 36 o más mejora apenas **0,0035 minutos de MAE**, con intervalo **[−0,0395; +0,0318]**: no se acredita mejora en ese diagnóstico particular. Los estratos describen la media previa, no roles conocidos antes del partido.

En las tres temporadas de evaluación se excluyen explícitamente **16.181** filas por historial positivo insuficiente y **17.442** por cero exposición de regulación; junto con los 63.155 casos suman las **96.778** filas del roster. Estas exclusiones impiden interpretar el resultado como desempeño sobre todos los convocados.

Las métricas no son comparables directamente con corridas anteriores de minutos totales o CRPS de rebotes: cambian el objetivo, las unidades o la población.

## Validación y preservación

La suite NBA pasa **213 pruebas**, incluidas 24 nuevas sobre fugas del día/futuro, identidad, fuente de namespace, intervalos, prórrogas y conservación. El arnés general pasa **768 pruebas con 10 omisiones**, antes y después. Docker no está disponible para esa comprobación. El primer lanzamiento del arnés posterior no se ejecutó porque la revisión automática agotó su límite; se reintentó por la misma revisión tras comprobar que el límite estaba restablecido.

La revisión de los artefactos exige preservar las 49 corridas y 19.744 evidencias previas, el prefijo de 98 eventos, los protocolos 99/100 y todos los archivos NBA existentes protegidos. Reconstruye el historial permitido de los 63.155 pronósticos, coteja sus muestras y calcula los **126.310 CRPS** candidato/baseline mediante una fórmula independiente de distancias por pares. Comprueba los 12.300 totales de equipo y reproduce los resúmenes/bootstrap con la semilla fijada. El resultado de esa revisión y el cierre están en `verification.json` y `checkpoint.json` de la carpeta canónica; solo el checkpoint acredita que el sellado se completó.

No se hicieron llamadas a proveedores, compras ni cambios de contratos/cuotas: cota conservadora ZenRows **2.232/3.200**, 243.132 parejas de cuotas y todos los candidatos anteriores preservados. Sin liquidaciones reales ni pruebas nuevas de recepción histórica original. Revisión propia, sin revisor independiente ni anclaje temporal externo.

## Qué fase sigue

**F4 permanece en curso.** F4.1 avanza con un baseline reproducible y un candidato exploratorio; falta distribución por rol/contexto. F4.2 requiere disponibilidad y titularidad con fuentes conocidas antes del corte, contexto de carga/entrenador y un modelo jerárquico que trate novatos y cambios de equipo. F4.3 requiere escenarios activo/DNP y una distribución conjunta que conserve minutos por equipo, además del tratamiento explícito de prórroga. Los gates G0–G9 permanecen pendientes.

El siguiente trabajo es preparar el protocolo jerárquico y sus variables as-of, distinguir las que tienen procedencia temporal acreditada y validar la coherencia deportiva. La calibración debe ajustarse con train/validación y confirmarse en datos posteriores separados; no se optimizarán parámetros con los resultados de esta comparación. Después se integra esa distribución de minutos en F5 y se completa la validación temporal F6 y la captura prospectiva F7. Props LATAM/REB/AST, reglas pendientes y contratos por ticket continúan como backlog independiente.

## Artefactos

- Carpeta canónica: `apps/nba/.local/normalized/nba_f4_run50_v2_20261007/`.
- Fuentes y protocolo: `prior_verification.json`, `protocol.json`, `protocol_event.json`, `namespace_overlay.json`, `coverage.json`.
- Etiquetas y evaluación: `regulation_labels.jsonl.gz`, `forecasts.jsonl.gz`, `scores.jsonl.gz`, `result.json`.
- Cierre: `verification.json`, `checkpoint.json`, registro `docs/nba_plan_fases_auditoria.json`.
- Código de investigación: `apps/nba/src/nba/minutes_benchmark.py`; no conectado al pronosticador de producción.
- Verificación: `apps/nba/.local/reports/verify_nba_f4_run50_20261007.py`.
