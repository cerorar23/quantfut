# Correcciones del motor de fútbol — 3-nov-2026

Rama: `codex/correcciones-futbol-20261103`. Origen: auditoría del mismo día. Los cambios corrigen medición, integridad y registro; ningún resultado de investigación activa automáticamente un modelo.

## Cambios implementados

| Hallazgo | Corrección |
|---|---|
| H01 historial retrospectivo | El destacado se guarda antes del inicio dentro de `predictions.data_completeness.web_destacado`; entra en el payload sellado. La API liquida esa fila congelada y conserva su probabilidad. Un partido sin registro previo no genera un acierto retrospectivo. El análisis estadístico de un partido pasado usa un acumulador limitado a su corte. |
| H02 xG desigual | A0 y el banco común aplican la misma admisión de xG por recepción que DC. Los derivados de tiros requieren su propio reloj; sin él no se hacen pasar por información disponible. Reconstrucción y recepción son protocolos separados y explícitos. |
| H03 simultáneos | Las medias de liga, equipo y árbitro incorporan resultados después de su disponibilidad, con empates temporales agrupados. El orden de IDs no permite conocer un resultado simultáneo. La reconstrucción histórica de conteos usa fin reconstruido +3 h y está etiquetada como tal. |
| H04 atraso canónico | La migración 102 propaga en la misma transacción las inserciones de `injuries`, `fotmob_baja_previa`, `fotmob_jugador_previo` y `lineups_previstas`. Conserva el reloj original, recupera dos días pendientes y distingue capturas de una misma fuente recibidas en el mismo minuto. |
| H05 A4 | Nuevo segmentador por cambios y rojas, con ridge por exposición. Los eventos ambiguos se apartan. Se corrigió la documentación que confundía la suma de tasas del once con plus-minus por tramos. Sigue siendo un candidato, sin validación de acierto a T-60. |
| H06 estimación prematura | Antes del fin de estimación A0 usa su prior de calentamiento; el ajuste definitivo espera al corte declarado. Al llegar xG tardío se reproduce el estado con la información permitida al corte. |
| H07 convergencia | NB y A0 rechazan fallos, coeficientes no finitos y objetivos no finitos. NB utiliza gradiente analítico verificado mediante diferencias numéricas. Los cortes fallidos se registran y no producen predicciones utilizables. |
| H08 sanciones | La inferencia de que Liga MX no tiene acumulación pasa a `pendiente`. Una vista de consumo solo acepta reglas verificadas, de reglamento y con temporada definida. No se inventó una regla vigente para 2026/27. |
| H09 tiros | Cuarentena con copia íntegra del registro antes de excluir la pareja incoherente. Los triggers cubren nuevos registros. Las evaluaciones de equipo/jugador también excluyen las parejas inconsistentes sin modificar los CSV originales. |
| H10 cuotas | Se rechazan duplicados ambiguos y ternas sin reloj o separadas más de 15 minutos. Desaparece la media automática entre precios distintos. |
| H11 integración | Los lectores canónicos existentes se conservan disponibles, con su interruptor y estado separados. No se encienden sin comparación de paridad. Los módulos de investigación no sustituyen al modelo de producción por existir en el repositorio. |
| H12 evaluación | Los resultados nuevos identifican 26/27 como seguimiento ya observado. Se evita además que los priors usados para entrenar el calibrador de props incorporen el futuro interno de su temporada de entrenamiento. El once reconstruido se etiqueta como condicionado a ese once, no como captura prospectiva. |

Los lotes antiguos mantienen su forma: el campo nuevo del destacado se omite cuando no existía. No se relajan triggers ni se cambia el orden predecir → seleccionar → sellar → publicar.

## Mediciones repetidas

Se conservaron las exportaciones y métricas anteriores. Los resultados nuevos están en carpetas nuevas bajo `.local/correcciones-20261103-*`; los resúmenes y hashes acompañan esta entrega.

### A0 y Dixon-Coles, misma política de recepción del xG

Walk-forward semanal; 5.541 partidos comunes en selección y 475 en seguimiento 26/27 ya observado. No se ha recalibrado sobre el seguimiento ni se presenta como prueba nueva intacta.

| Periodo | Mercado | DC | A0-xG |
|---|---:|---:|---:|
| Selección, log-loss | 0,963922 | 0,982760 | 0,981514 |
| Seguimiento ya observado, log-loss | 0,976560 | 0,991350 | 0,991654 |

Delta A0−DC en selección: **−0,001246**, IC95 **[−0,003201; +0,000708]**. Seguimiento: **+0,000304**, IC95 **[−0,012386; +0,012993]**. No hay mejora confirmada para promover A0. Cero ajustes omitidos por fallo de convergencia en esta repetición.

Esta comparación aplica recepción al xG con fuente conocida y mantiene el tratamiento legado del xG sin recepción acreditada que utiliza el DC existente. No convierte ese histórico legado ni las cuotas de cierre en evidencia prospectiva.

### Conteos sin resultados simultáneos

Reconstrucción histórica explícita; no se denomina simulación de recepción original. Comparación por filas comunes de cada objetivo.

| Objetivo / periodo | n | Media de liga | Variante con covariables |
|---|---:|---:|---:|
| Córners, selección | 5.538 | 2,644870 | 2,620194 (NB variable inspirada en Yip) |
| Córners, seguimiento | 475 | 2,704737 | 2,682905 |
| Amarillas, selección | 5.535 | 2,157836 | 2,118914 (rasgos inspirados en Dawson) |
| Amarillas, seguimiento | 475 | 2,110768 | 2,055033 |

Cero ajustes omitidos en la repetición final. Un intento previo detectó una terminación anormal del optimizador de NB; se corrigió la derivada numérica sustituyéndola por un gradiente analítico, y se repitió. No se aceptaron sus coeficientes fallidos.

### Nuevo A4 por tramos

Se construyeron **49.933 tramos de 7.138 partidos**, con **8.512 jugadores** en el ajuste ridge. Se apartaron 31.277 registros de partido del universo exportado: 28.923 sin jugadores o incidencias, 1.623 con cambios incompatibles con el once, 573 con gol/cambio en el mismo minuto sin orden acreditado, 156 con once incompleto, uno sin identidad y uno con marcador no monótono.

Es cobertura y ajuste del candidato, **no una mejora predictiva demostrada**. No incluye tracking, secuencias de posesión ni prior de edad. Falta la evaluación prospectiva del once disponible y cualquier promoción posterior.

## Migración y operación

`db/102_futbol_integridad_y_capturas.sql` debe aplicarse antes del nuevo worker. Fue ensayada en PostgreSQL 16 temporal, sin red, sin puertos ni volúmenes de producción, con datos ficticios y `ROLLBACK`. El ensayo comprueba cuarentena, las cuatro tablas de captura, idempotencia y colisiones dentro de un mismo minuto.

La migración conserva la procedencia y cambia a NULL únicamente parejas de tiros incoherentes; el valor correcto se recupera contrastando el original, no adivinándolo. La cuarentena conserva el registro para esa revisión. La captura intradía se resuelve con triggers, sin añadir cron ni llamadas a proveedores.

Al desplegar, los partidos anteriores sin destacado congelado dejarán de contarse como pronósticos registrados. El historial nuevo empieza con decisiones previas selladas. Esto corrige el origen del historial; no reconstruye una publicación que nunca quedó registrada.

La activación del lector canónico, nuevas reglas de sanción verificadas y una promoción de A0/A4 requieren sus datos y comprobaciones correspondientes. No se marcan como logradas por tener código o pruebas sintéticas.

## Verificación

Pruebas de regresión nuevas: independencia de resultados futuros/simultáneos, prior de calibración sin futuro, coherencia de ternas, convergencia y gradiente, intervalo real de estimación, destacado congelado, payload compatible y segmentación de jugadores. Suite completa del checkout corregido: **1.756 aprobadas, 122 omitidas, cero fallos**. Pyflakes de los módulos nuevos/modificados y comprobación de espacios correctos. Ensayo SQL aislado con `ROLLBACK`: aprobado.
