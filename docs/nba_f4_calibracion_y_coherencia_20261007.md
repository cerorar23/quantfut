# NBA-RUN-051 — corrección de cobertura y escenarios de equipo

Trabajo autorizado el 7 de octubre de 2026, America/Mexico_City; sellos UTC del 8 de octubre. Investigación retrospectiva local. El cierre se acredita mediante `checkpoint.json` de la carpeta canónica, no mediante este documento por sí solo.

Se corrigieron dos problemas técnicos de F4: la cobertura central nominal del 80% pasa de **70,663% a 80,537%** en las temporadas posteriores al ajuste, y se implementaron escenarios que conservan **240 minutos por equipo**, máximo **48 por jugador**, cero para DNP y límites individuales explícitos. Podemos continuar investigando F5 con estas herramientas y con la referencia anterior preservada.

El ajuste de amplitud tiene un coste: **CRPS 3,5479 → 3,5782** y **MAE 4,8694 → 4,8873 minutos** frente al candidato RUN-050. Como CRPS es la métrica primaria, **se conserva la referencia sin ampliar de RUN-050**. El ajuste queda como diagnóstico de cobertura; no se promueve por mejorar una métrica secundaria. No se ha completado F4 ni aprobado G4.

## Ajuste separado de las temporadas de evaluación

Protocolo `F4-width-team-exploratory-v1`, fijado localmente en el evento **102** antes del ajuste. Calibrador congelado en el evento **103** antes de evaluar sus distribuciones ampliadas en validación y temporadas posteriores. El replay sin ampliar reproduce exactamente los 63.155 pronósticos anteriores mediante hash de su contenido lógico.

| Bloque | Temporada | Casos | Uso |
| --- | --- | ---: | --- |
| Entrenamiento | 2021-22 | 20.630 | Elegir amplitud dentro de una rejilla fija |
| Validación | 2022-23 | 20.847 | Revisar cobertura, sin reajuste |
| Evaluación exploratoria | 2023-24–2025-26 | 63.155 | Medir comportamiento posterior, sin reajuste |

Rejilla de amplitud 1,00–2,00 en pasos de 0,05. Se elige el primer valor que alcanza 80% de cobertura en entrenamiento por banda de media histórica previa; con menos de 1.000 casos se usa el ajuste global. Se expande cada muestra alrededor de su mediana y se conserva el soporte 0–48. El ajuste elegido es **1,30** para historial menor de doce minutos y **1,25** para las demás bandas; la banda de 36 o más tiene 727 casos y utiliza el ajuste global.

Última etiqueta de entrenamiento: **2022-04-10**. El corte lógico de disponibilidad del calibrador es **2022-07-01**, dentro de este replay; no implica que se entrenara o recibiera originalmente en 2022. Las temporadas históricas ya habían sido inspeccionadas: no constituyen un test confirmatorio intacto. El mínimo sigue siendo diez apariciones positivas de la misma temporada, excluyendo toda la fecha objetivo.

La ventana diagnóstica de validación **78%–82%** fue fijada antes del ajuste. La cobertura de validación es **80,534%**, dentro de esa ventana; no se vuelve a entrenar tras verla. Cumplir esa ventana no aprueba un gate ni demuestra calibración completa de toda la distribución.

## Resultado posterior

Misma población de 63.155 casos positivos, 3.256 partidos y 433 fechas que RUN-050. La referencia de esta tabla es el candidato reciente sin ampliar, no la distribución histórica de diez apariciones.

| Diagnóstico | Referencia RUN-050 | Ajuste de amplitud |
| --- | ---: | ---: |
| CRPS, menor es mejor | 3,5479 | 3,5782 |
| MAE, minutos | 4,8694 | 4,8873 |
| RMSE, minutos | 6,3809 | 6,3697 |
| Cobertura central nominal 80% | 70,663% | 80,537% |
| Anchura media central, minutos | 12,9728 | 16,2283 |

Diferencia de CRPS **+0,03030**, intervalo exploratorio 95% por fecha **[+0,02488; +0,03526]**. Diferencia de MAE **+0,01787 minutos**, intervalo **[+0,01390; +0,02157]**. Son diagnósticos bootstrap pareados de 1.000 réplicas, semilla 20261007; sin corrección por comparaciones múltiples ni confirmación prospectiva. La mayor cobertura viene acompañada de intervalos más amplios y deterioro de la métrica primaria.

## Escenarios coherentes

El nuevo motor recibe un escenario explícito de jugadores activos/DNP y límites de minutos. Genera propuestas desde las distribuciones individuales y las proyecta al conjunto de minutos admisibles: suma 240, soporte individual 0–48 y DNP cero. Rechaza identidades duplicadas, namespaces mezclados, equipos distintos, menos de cinco activos o una capacidad de minutos insuficiente; no rellena un escenario imposible.

En la prueba histórica se usan los jugadores con tiempo positivo **observados después del partido** para construir el escenario. Esto es un diagnóstico con disponibilidad conocida a posteriori; no es una predicción prepartido. No se ofrece como comparación de precisión con ventaja predictiva ni como modelo de disponibilidad.

De **7.380 pares equipo/partido** de las tres temporadas de evaluación:

- **3.246** tienen historial previo suficiente para todos sus jugadores positivos y se simulan con 128 realizaciones cada uno.
- **4.134** se excluyen porque falta ese historial completo. No se crean pronósticos de jugadores nuevos usando resultados actuales.
- Las **415.488 realizaciones** conservan 240 minutos, el soporte individual y los ceros de DNP. El cambio absoluto medio de la proyección es **2,039 minutos** por celda de roster, incluidos ceros.

La proyección introduce dependencia por la suma del equipo, pero no ajusta dependencia real de quintetos ni reconstruye rotaciones futuras. La disponibilidad previa, titularidad, lesiones, restricciones médicas y escenarios competitivo/paliza/faltas continúan pendientes. El motor solo acepta disponibilidad `hypothetical` y rechaza presentarla como verificada as-of.

## Verificación y preservación

**234 pruebas NBA**, incluidas 21 nuevas para contaminación de entrenamiento, cortes, soporte, proyección, reproducibilidad, DNP, restricciones e inviabilidad. Arnés general **768 pruebas y 10 omisiones**, antes y después. Docker no disponible para su comprobación; no se modificaron los servicios de fútbol/web.

Revisión propia de las 50 corridas y 19.786 evidencias anteriores. Se reproduce el ajuste con sus 20.630 casos de entrenamiento; se revisan los **84.002** pronósticos ampliados y se calculan **168.004 CRPS** mediante una fórmula independiente. Se verifican todos los resúmenes, la elegibilidad de equipos y las restricciones registradas; se regeneran nueve ejemplos de escenarios, distribuidos entre las tres temporadas, comprobando hashes exactos de sus matrices de muestras. Las unidades prueban también escenarios inviables y restricciones distintas de las históricas.

Fuentes, protocolo, calibrador, datos, pruebas y código quedan ligados por hashes y cadena local. Sin revisor independiente ni anclaje externo. Cero llamadas a proveedores, compras, cuotas o liquidaciones nuevas; cota ZenRows **2.232/3.200** preservada. No se crean pruebas de recepción original ni contratos históricos.

## Continuación preparada

`F5_research_handoff.json` deja fijadas las rutas y hashes del conjunto de etiquetas, los boxscores, la capa de namespace, los pronósticos de referencia, el calibrador y el motor de escenarios. Su estado es **listo para investigación F5**, con producción deshabilitada y gate F4 pendiente.

El siguiente paso es el baseline de productividad por minuto de F5, conservando RUN-050 como referencia primaria y comparando el diagnóstico ampliado por separado. Se fijarán protocolo, entrenamiento, validación y evaluación antes de ajustar tasas. Para un objetivo inicial de regulación deben **excluirse partidos con prórroga mientras no haya etiquetas estadísticas verificadas por periodo**: los puntos/rebotes/asistencias del boxscore completo incluyen prórroga y no deben dividirse por minutos de regulación como si fueran el mismo objetivo.

F4.2 y la parte predictiva de F4.3 todavía necesitan datos previos de disponibilidad/rol y validación posterior independiente. El histórico ausente de recepción original no se puede reconstruir con certeza desde resultados finales. Ese límite impide certificar producción, pero permite seguir evaluando modelos retrospectivos con alcance explícito. G0–G9 permanecen pendientes; props LATAM/REB/AST, reglas y contratos por ticket siguen en el backlog.

## Artefactos

- Carpeta canónica: `apps/nba/.local/normalized/nba_f4_run51_20261007/`.
- Configuración: `protocol.json`, `protocol_event.json`, `calibrator.json`, `calibrator_event.json`.
- Evaluación: `raw_forecasts.jsonl.gz`, `raw_scores.jsonl.gz`, `calibrated_forecasts.jsonl.gz`, `calibrated_scores.jsonl.gz`, `result.json`.
- Escenarios: `team_scenarios.jsonl.gz`.
- Continuación: `F5_research_handoff.json`, `F5_handoff_verification.json`.
- Validación y cierre: `verification.json`, `checkpoint.json`.
- Motor: `apps/nba/src/nba/minutes_repair.py`; referencia y artefactos RUN-050 preservados.
