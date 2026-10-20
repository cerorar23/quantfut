# Resultados, evidencia y causa del registro futuro vacío

Comprobación real: **19-oct-2026, 18:35 UTC / 12:35 Ciudad de México**. Los 18 encuentros registrados todavía están programados para el futuro. Primer inicio estimado: **20-oct 04:15 UTC / 19-oct 22:15 Ciudad de México**; faltaban unas 9,7 horas. Esta hora es una estimación, no el inicio físico.

Por tanto, cero resultados futuros es el estado correcto a esa hora. No se puede acreditar el resultado de estos encuentros antes de que se jueguen. Tampoco se puede convertir un partido anterior no pronosticado en un acierto del estudio.

## Trabajo completado ahora

- Incorporador offline `tennis_evidence_v1`: verifica archivos y cruza ID exacto de evento, IDs de ambos jugadores, orientación, circuito y edición con el calendario original del pronóstico.
- Conversión contrastada de marcadores API-Tennis: `6.4`/`7.7` describe 6–7 juegos y tiebreak 4–7; no se trata como número decimal de juegos. Se validan sets contiguos, resultado final y ganador, sin truncar datos dudosos.
- Conservación de conflictos y resultados candidatos sin horas. Los conflictos de marcadores/fuentes no se resuelven escogiendo el más reciente o favorable. Un lote con IDs repetidos se rechaza completo.
- Vinculación de revisiones temporales a campos originales, participantes, fuente archivada, zonas horarias y cronología. No se imputan inicio o fin.
- Ejecución automática de los evaluadores originales de ganador y diez mercados con listas nuevas de resultados admitidos; sus protocolos y modelos siguen intactos.
- Revisión legible del histórico ya existente: **2.788 partidos terminados, 2.207 ATP y 581 WTA, diez familias y 39 grupos exactos** después de unir los marcadores finales como una sola tarea multiclase. No se inflan los partidos contando sus alternativas por separado.
- Auditoría financiera actualizada y continuidad existente ampliada; sin duplicar automatizaciones, gastar créditos o ejecutar apuestas.

Primera reconciliación: 18 pendientes por `scheduled_in_future`, **cero eventos terminales de esos 18**, 59 eventos terminales del proveedor ajenos al registro y cero errores de fuente. Los 59 incluyen estados terminales distintos; no son 59 nuevos aciertos ni todos partidos completados. La comprobación del capturador respondió `capture_not_due`: no se forzó otra descarga ni se consumió una consulta.

## Qué demuestra el histórico

La revisión usa modelos anteriores a enero de 2026 y probabilidades archivadas para 2026, año ya inspeccionado. Es **exploratoria**, no una muestra confirmatoria nueva del candidato actual de octubre. Se conservan los 50 grupos marginales anteriores; al agrupar cada vector de marcador por sets se obtienen 39 tareas/grupos, sin perder alternativas.

Ejemplos del Markov histórico, sin seleccionar partidos por conveniencia:

| Tarea | Muestra | Aciertos de la alternativa más probable | Log-Loss | Brier binario |
|---|---:|---:|---:|---:|
| Ganador ATP, mejor de tres | 1.789 | 62,3% | 0,6610 | 0,2314 |
| Ganador ATP, mejor de cinco | 418 | 69,1% | 0,6224 | 0,2049 |
| Ganador WTA, mejor de tres | 581 | 69,5% | 0,6043 | 0,2074 |
| Total de juegos ATP >22,5, mejor de tres | 1.789 | 51,9% | 0,6995 | 0,2530 |
| Marcador exacto ATP, mejor de tres | 1.789 | 41,3% | 1,3330 | No aplica: multiclase |
| Marcador exacto WTA, mejor de tres | 581 | 46,8% | 1,2597 | No aplica: multiclase |

Son tareas diferentes: no se compara directamente el Log-Loss de cuatro alternativas con el binario. El informe completo muestra todos los grupos, Brier vectorial, ECE de la alternativa más probable con diez intervalos, curvas y estimaciones de incertidumbre por competición. También muestra el balance de clases como diagnóstico posterior, no como benchmark entrenado. Ejemplo: >22,5 juegos en mejor de cinco acierta el 98,8%, pero el resultado mayoritario aparece también el 98,8%; ese porcentaje aislado no acredita capacidad de seleccionar ganadores ni beneficio.

Estas cifras no acreditan superioridad global, calibración de todas las líneas, cobertura universal o certeza individual. Se mantienen las cuarentenas y la muestra común. No se reentrena el candidato ni se escogen nuevos umbrales sobre estos resultados. `historical/` conserva la primera revisión; `historical_v2/` añade el diagnóstico de clases sin modificarla.

## Rentabilidad: impedimentos reales

La auditoría financiera conserva **cero órdenes simuladas válidas y cero liquidaciones**, con ROI/CLV desconocidos. El periodo ni siquiera había empezado en esta comprobación; va del 20-oct-2026 al 1-jul-2027. Además de resultados futuros, necesita cuotas prepartido válidas, órdenes registradas antes de los encuentros, precios de cierre, reglas de liquidación y costes. La exactitud probabilística no permite reconstruir esos precios o ejecuciones.

**La continuidad predictiva activa no genera por sí sola una muestra financiera.** No se afirma que esté acumulando ROI. El financiero permanece limitado a ganador/Pinnacle; las otras familias tienen el estudio probabilístico separado. No se cambió su protocolo para admitir precios obsoletos ni registros retrospectivos.

Los permisos anteriores de The Odds API se consumieron, la reserva compartida de 6.000 sigue vigente y el último saldo observado fue 4.606. Son observaciones históricas de cuenta, no una consulta nueva de saldo. No se aprovecha otra clave para saltar esa reserva. Poner en marcha nuevas capturas financieras requiere disponibilidad y autorización compatibles con esos límites o una fuente alternativa realmente verificada. No se inventó una autorización adicional. Cualquier propuesta de excepción deberá presentar primero alcance y consumo concretos para revisión.

Los criterios de muestra, cobertura, incertidumbre y cierre de periodo permanecen fijados. Obtener el primer resultado solo inicia la evaluación; no acredita de inmediato calidad ni beneficio. El sello DigiCert prueba existencia del protocolo anterior, no resultados de partidos ni ganancias.

## Automatización de resultados

La automatización `continuidad-de-validaci-n-predictiva-de-tenis` sigue en este mismo chat cada dos horas. Se conservan capturas cada cuatro horas, máximo 12 intentos API-Tennis/día UTC y espera de 24 horas ante 401/403/429. El incorporador no hace llamadas de red ni consume créditos.

Comando a ejecutar después de cada pasada de captura/revisión, con el motor aislado como directorio de módulos:

```text
python -m tennis_evidence_v1 reconcile --quality-protocol data/tennis/predictive_quality_v3_20261019_v3/future_quality_protocol.json --market-protocol data/tennis/all_markets_prospective_20261019/protocol.json --capture-root data/tennis/continuous_quality_20261019/state_capture --times-root data/tennis/evidence_resolution_20261019/time_reviews --output-root data/tennis/evidence_resolution_20261019/runs/FECHA_UUID_NUEVA
```

La salida debe ser una carpeta nueva: `accepted_results.json`, `terminal_candidates.json`, `winner_evaluation.json`, `markets_evaluation.json` y `reconciliation.json`. No se sobrescriben listas iniciales, informes o registros sellados. Las fuentes permanecen archivadas; los resultados no verificables siguen pendientes en cobertura. No se confunde la muestra histórica con la futura.

Las revisiones temporales se crean **solo si se acredita una fuente real** en archivos nuevos de `time_reviews/`. La documentación de [API-Tennis](https://api-tennis.com/documentation) enumera marcadores/ganador y ejemplos de `event_date`/`event_time`, pero no acredita que esos horarios sean inicio y fin físicos. Tener esos nombres de campo no basta.

El adaptador inicial de revisión exige JSON original: `event_id`, `semantics="physical_court_start_end"`, `reviewed=true`, `reviewed_by`, `source_url` reconocido, `source_path`, `source_sha256`, `received_at` real, `participants` en orden A/B, `actual_start`/`actual_end` con zona explícita y `field_paths` a los cuatro campos nativos (`actual_start`, `actual_end`, `home_team`, `away_team`). Se comprueba la correspondencia de los valores y participantes contra el documento, además de la cronología. La semántica física debe revisarse con evidencia primaria; la herramienta no puede certificarla por una bandera. Si la fuente usa otro formato, hace falta otro adaptador revisado; no convertir una estimación en un dato físico.

## Archivos de esta entrega

Raíz `data/tennis/evidence_resolution_20261019/`:

- `historical_v2/HISTORICO.md` y `historical_review.json`: evidencia histórica completa y sus límites.
- `reconciliation_initial/`: primera reconciliación y nuevas evaluaciones, conservadas.
- `financial_review.json`: auditoría financiera real, sin órdenes ni rentabilidad acreditada.
- `capture_check.json`: comprobación de captura no vencida, cero llamadas.
- `time_reviews/`: registro explícito actualmente vacío; no contiene pruebas simuladas.

Cuatro módulos y pruebas entregados al motor aislado. Las pruebas comprueban software y no se presentan como precisión deportiva ni como beneficio.
