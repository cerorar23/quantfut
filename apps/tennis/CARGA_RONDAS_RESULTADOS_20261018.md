# Carga observable de rondas anteriores: resultado y siguientes pasos

18 de octubre de 2026. Se implementó y ejecutó una comparación de carga observada dentro del mismo cuadro individual. Las métricas mejoran ligeramente, pero los intervalos siguen incluyendo cero: la corrección permanece experimental y no modifica el motor congelado.

## Resultado sobre los mismos partidos

Se ajustaron las correcciones con 2.130 partidos de desarrollo 2024 y se evaluaron tres variantes sobre exactamente los mismos 1.957 partidos de 2025. La cobertura es 36,39 % de los 5.378 partidos de la partición exploratoria, e incluye 993 ATP y 964 WTA. Se exige que ambos jugadores tengan juego observado en una ronda anterior del mismo cuadro.

| Métrica, menor es mejor | Base | Base + Cobertura | Base + Cobertura + Carga |
|---|---:|---:|---:|
| Log-Loss | 0,615696 | 0,615629 | 0,615221 |
| Brier | 0,213501 | 0,213475 | 0,213225 |
| ECE, diez intervalos iguales | 0,028584 | 0,028569 | 0,026355 |

La diferencia de Log-Loss de carga respecto a base es −0,00047531, con intervalo descriptivo del 95 % [−0,00110306; +0,00015902]. Respecto al control de cobertura, la diferencia es −0,00040859, con intervalo [−0,00109461; +0,00032448]. Ambos incluyen cero. Brier presenta la misma limitación. ECE baja en esta muestra, pero ese cambio no basta para seleccionar modelo ni garantiza calibración futura.

El control de cobertura contiene diferencias entre jugadores de partidos previos observados, walkovers y contadores faltantes. Permite comprobar que la mejora no se atribuya automáticamente a los totales de carga cuando pudiera proceder de diferencias de historial disponible. Tanto el control como la variante con carga se ajustan con datos de entrenamiento, no con resultados de 2025.

## Qué carga se calculó

El nuevo extractor suma exclusivamente los contadores observados de rondas anteriores del mismo cuadro de individuales:

- Puntos jugados: suma de los totales de puntos al saque de ambos jugadores del partido anterior. Incluye los puntos de tie-break que contiene ese registro; no estima puntos a partir de juegos.
- Juegos y sets: conteo directo de marcadores completos convencionales.
- Sets decisivos: indicador de partido que alcanzó el máximo de sets de su formato, agregado sobre partidos anteriores.

La precedencia usa R128, R64, R32, R16, QF, SF y F dentro de la misma edición y fase. No usa `match_num` ni inventa el orden de una fase de grupos. Se excluyen round-robin y competiciones por equipos del experimento de cuadros individuales. El marcador y las estadísticas del partido objetivo y de rondas posteriores no entran en sus variables.

Los contadores ausentes se conservan como ausentes mediante indicadores y subtotales conocidos. Un subtotal de cero con registros faltantes no afirma carga real cero. Los walkovers son avances sin juego; retiros y marcadores incompletos no se convierten artificialmente en juegos o sets completos. Un total al saque utilizable puede conservar puntos observados aunque el marcador no permita completar otros contadores.

La extracción cubre 11.240 objetivos: 10.407 tienen formato de cuadro compatible y 4.378 tienen juego previo observado para ambos jugadores antes de los filtros de resultado y partición. No se acredita con ello un historial completo. Esta carga excluye dobles, qualies, torneos previos y actividad no registrada; tampoco mide minutos, descanso, esfuerzo metabólico o causa fisiológica.

## Sensibilidad con contadores observados completos

Se repitió el ajuste exigiendo que todos los registros previos observados tengan los cuatro contadores disponibles. Esto no prueba que estén registrados todos los partidos que jugó el deportista.

Entrenamiento: 1.882 partidos. Evaluación común: 1.700 (31,61 % de la partición exploratoria).

| Métrica | Base | Base + Cobertura | Base + Cobertura + Carga |
|---|---:|---:|---:|
| Log-Loss | 0,611986 | 0,611969 | 0,611413 |
| Brier | 0,211987 | 0,211960 | 0,211671 |
| ECE | 0,032465 | 0,033151 | 0,027608 |

Carga menos base: −0,00057277 de Log-Loss, intervalo [−0,00133857; +0,00020260]. Carga menos cobertura: −0,00055658, intervalo [−0,00133145; +0,00021039]. No cambia la decisión de mantenerla experimental. Los valores absolutos de esta tabla y de la principal corresponden a muestras diferentes; no deben compararse como si una especificación hubiera vencido a la otra.

Los intervalos utilizan 1.000 remuestreos emparejados por competición, semilla 20261018 y 107 bloques de evaluación. No modelan toda la dependencia de jugadores entre competiciones ni corrigen comparaciones múltiples. Las desagregaciones ATP/WTA están en los informes; sus intervalos de diferencia frente al control también incluyen cero.

## Qué sigue bloqueado: ventanas diarias

Las ventanas L3D/L7D de puntos, juegos y sets y L5D de partidos decisivos siguen sin quedar acreditadas por estas nuevas variables. No se sustituyen días por rondas.

Se revisaron, sin llamadas nuevas, los archivos ya conservados de API-Tennis: 152 observaciones terminales de individuales en sus últimas revisiones. Ninguna tiene un límite inferior finito de finalización acreditado en el normalizador. La recepción de un resultado terminado proporciona un límite superior, mientras que una fecha programada no prueba cuándo se jugó realmente. Por eso no se utilizan horas arbitrarias ni se fuerza su inclusión en ventanas cortas.

Para activar aquellas ventanas hace falta, por partido y con fuente archivada, un intervalo de finalización suficientemente acotado y un registro de disponibilidad anterior a la decisión. Si se pretende validar retrospectivamente con fechas reales, deben acreditarse también la semántica de las fechas y las suspensiones; no basta con un campo llamado `Date`. Los extractores diarios estrictos ya existentes mantienen sus controles y no se modificaron para relajar esta exigencia.

## Diseño, corrección de alcance y validación

La base histórica es la reconstrucción Markov/Elo de la fase anterior, con calibraciones anteriores a cada origen y embargo de 35 días. Se reutilizaron sus 11.240 predicciones con huella verificada, sin volver a ajustar sus parámetros. Las dos nuevas correcciones son offsets logísticos simétricos: diferencias entre jugadores, escala RMS calculada en entrenamiento y ridge fijo de 1. No tienen intercepto ni centran con datos de evaluación. El ajuste comparte coeficientes entre ATP y WTA.

Las competiciones completas conservan su partición temporal. Se excluyen 201 objetivos de frontera y los resultados no convencionales del contrato de puntuación. Las fuentes fueron recibidas en 2026: todo el estudio sigue siendo retrospectivo y 2025 exploratorio, sin disponibilidad histórica simulada. No se seleccionaron hiperparámetros con sus resultados.

La primera ejecución detectó aparentes contradicciones de avance en las finales BJK 2024. Al revisar los originales se comprobó que eran partidos por equipos: una jugadora puede perder su rubber y volver a jugar si avanza la selección. Se corrigió el alcance para excluir todos los eventos por equipos de esta prueba de cuadros individuales. La versión preliminar `draw_load_20261018` quedó retirada mediante `SUPERSEDED.json`; el resultado válido es `draw_load_20261018_v2`. La corrección fue de contrato y no una búsqueda de mejores métricas. Se mantuvieron intactos los originales.

Pasaron 194 pruebas de tenis, doce nuevas. Cubren rondas previas, exclusión del objetivo/futuro, contadores faltantes, walkovers, marcadores incompletos, formatos de equipo/grupos, muestra común, entrenamiento separado, simetría y escala de entrenamiento. La auditoría reproduce la extracción, comprueba los IDs y la precedencia de cada partido usado, vuelve a ajustar los coeficientes y recalcula las métricas. Los 12 artefactos congelados permanecen intactos. No hubo llamadas nuevas a proveedores deportivos ni consumo de créditos de The Odds API.

El arnés general inicial y final aprobó 1.310 pruebas, omitió 88 y emitió dos avisos; el final tardó 324,67 segundos. Docker no estaba disponible. La auditoría se ejecutó también desde la entrega aislada; sus cuatro archivos coinciden por huella con los comprobados y la revisión de formato pasó.

## Entrega y siguiente prioridad

Resultados y auditoría: `data/tennis/draw_load_20261018_v2/`. Incluye protocolo anterior al cálculo, variables por objetivo, predicciones comunes, artefactos de ajuste, métricas, 60 filas de calibración, diagnóstico de ventanas diarias y cola geográfica priorizada. El código entregado al motor aislado es `tennis_engine/draw_load.py`, con `run_draw_load_comparison.py`, `audit_draw_load.py` y sus pruebas. Los scripts se ejecutan desde la raíz del proyecto con los datos locales; el runner exige un directorio nuevo.

La cola `geography_priority_queue.json` ordena las 88 entradas de sede todavía sin coordenadas por partidos de destino afectados. Las primeras cinco concentran 264 de los 730 destinos pendientes:

| Recinto | Partidos afectados |
|---|---:|
| True Arena Hua Hin | 62 |
| Yucatan Country Club | 58 |
| Olympic Park Tennis Centre | 54 |
| Zayed Sports City International Tennis Centre | 54 |
| Martin Carpena Arena | 36 |

Se priorizan para verificación, sin tratarlas aún como coordenadas conocidas. La nueva cola no modifica los registros ni conjuntos históricos ya utilizados.

Recomendación: conservar la base, completar primero estas sedes de mayor impacto y conseguir intervalos temporales verificables. La carga por rondas queda disponible para investigación. Si se estudian otra penalización, nuevas interacciones o parámetros por circuito, deben elegirse en bloques temporales internos de 2024 y congelarse antes de un nuevo periodo futuro intacto. Estos resultados no validan ROI, CLV ni rentabilidad, y el periodo reservado al candidato operativo congelado no se reutiliza para seleccionar esta variante.
