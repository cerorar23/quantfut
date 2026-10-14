# Auditoría de datos y motor de pronóstico — 14 de octubre de 2026

Corte de cobertura: 2026-10-14T05:52:55.780406+00:00. Corte operativo: 13-10-2026 23:57:44 (Ciudad de México). Consultas a producción con transacciones de solo lectura. Ningún cambio al motor, entrenamiento, banderas de ligas ni datos de producción.

La base contiene 92.327 partidos terminados de todas las fechas. El análisis detallado usa los 20.854 terminados desde el 1 de enero de 2024 en las 23 competiciones actuales; también compara los 13.203 desde 2025. Los conteos describen los partidos registrados, no certifican por sí solos que todos los calendarios externos estén completos. Los faltantes se superponen: no se deben sumar como partidos únicos.

## Qué alimenta hoy el pronóstico

| Componente | Uso actual | Pendiente |
| --- | --- | --- |
| Probabilidades del modelo principal | Goles y xG históricos, fuerza de ataque/defensa, localía, competición, ponderación temporal y calibración | Reentrenar y evaluar después de las importaciones; guardar más datos no cambia el artefacto activo |
| Selección de picks de valor | Comparación de casas disponibles con Pinnacle sin margen, cuotas simultáneas, consenso, antigüedad y persistencia de la ventaja | Cobertura y calidad de precios antes del partido y al cierre |
| Alta probabilidad / parlays / parte de escalera | Probabilidades de mercado y reglas/calibración del producto | No reciben directamente clima, lesiones o XI |
| Alineaciones y valor de jugadores | Captura, evaluación histórica y predicciones experimentales en paralelo | Integrar los archivos FotMob con identidades compatibles y validar antes de cambiar el modelo principal |
| Lesiones, sanciones y dudas | Captura de bajas y comprobantes de consulta | Transformar disponibilidad e importancia del reemplazo en variables validadas |
| Córners y tarjetas | Motor específico con históricos, recencia y factor arbitral para tarjetas | Completar campos consultables y árbitro de cada partido |
| Clima / estadio / desplazamientos | No son entradas directas del modelo activo | Normalizar originales y capturar condiciones/ubicación con hora de recepción |

Modelo principal activo: `2026.09.27-010508`, ajustado el 2026-09-27 06:21:39.596498+00:00, con 49.257 partidos. Activo en 13 competiciones; 10 están configuradas para operar sin este modelo y sin captura completa de XI/bajas. Mezcla modelo/mercado y residuo desactivados; calibración activa. Hay 106 predicciones experimentales de alineaciones, pero eso no implica promoción al modelo principal. De las parejas xG actuales, 7.689 de las 13 ligas modeladas tienen recepción posterior al ajuste: el artefacto congelado no incorpora estas nuevas recepciones. No se estima aquí su impacto predictivo.

## Totales de cobertura

| Dato faltante / no acreditado | Desde 2024 | Desde 2025 |
| --- | --- | --- |
| Marcador final | 0 | 0 |
| xG de ambos equipos | 1.222 | 239 |
| Tiros de ambos equipos | 247 | 26 |
| Tiros a puerta de ambos equipos | 245 | 24 |
| Córners de ambos equipos | 250 | 24 |
| Amarillas de ambos equipos, tabla principal | 8.412 | 5.495 |
| Árbitro, tabla principal | 18.280 | 11.537 |
| Marcador al descanso | 7.325 | 4.408 |
| PSxG, tabla principal | 17.137 | 12.901 |
| XI completo de ambos equipos, cualquier archivo | 336 | 108 |
| XI completo en tablas leídas por los módulos actuales | 16.176 | 8.525 |
| XI completo capturado antes del inicio | 20.713 | 13.062 |
| Jugadores: al menos 11 con minutos por lado, cualquier archivo | 349 | 81 |
| Jugadores con minutos en tablas leídas por los módulos actuales | 15.822 | 8.171 |
| Sin comprobante de consulta de bajas anterior al inicio | 20.681 | 13.030 |
| Sin 1X2 de cierre completo de Pinnacle almacenado | 6.185 | 5.995 |

Un XI completo exige 11 titulares con identificadores distintos en ambos lados de un mismo proveedor. La cobertura de jugadores exige al menos 11 jugadores distintos con minutos positivos por lado; no certifica que todas las métricas individuales estén presentes. Un archivo descargado después de un partido sirve como antecedente para futuros partidos, pero no acredita que ese XI o esa baja se conocieran antes de ese mismo partido. Las cuotas contadas al cierre aquí son existencia almacenada, sin auditoría adicional de simultaneidad o elegibilidad temporal.

Bajas: solo 173 partidos terminados tienen comprobante de consulta antes del inicio; 102 tienen alguna baja capturada antes. Hay declaraciones de ausencias en archivos históricos de 14.331 partidos. Una respuesta vacía es una consulta realizada, no una garantía médica de ausencia de lesiones. La tabla actual reporta los tipos «Missing Fixture» y «Questionable»; no demuestra un histórico completo de sanciones, motivos y fechas de retorno.

## Las 23 competiciones: huecos de xG, alineaciones y jugadores

Columnas de XI/jugadores: datos ausentes en todos los archivos revisados, no solamente en las tablas actuales. «Modelo» indica la configuración del motor principal.

### Desde 2024-01-01

| Competición | Modelo | Terminados | Sin xG | Sin XI completo | Sin jugadores/minutos completos |
| --- | --- | --- | --- | --- | --- |
| Liga Profesional | Sí | 1.525 | 208 | 218 | 203 |
| Brasileirão Série A | Sí | 1.059 | 2 | 4 | 4 |
| Super League (Suiza) | No | 638 | 2 | 4 | 3 |
| Bundesliga | Sí | 820 | 0 | 1 | 1 |
| 2. Bundesliga | No | 828 | 0 | 0 | 0 |
| Superliga (Dinamarca) | No | 537 | 0 | 1 | 1 |
| LaLiga | Sí | 1.038 | 0 | 0 | 1 |
| LaLiga 2 | No | 1.272 | 236 | 11 | 10 |
| UEFA Champions League | Sí | 312 | 14 | 22 | 8 |
| UEFA Europa League | Sí | 208 | 12 | 12 | 13 |
| Ligue 1 | Sí | 819 | 0 | 2 | 0 |
| Ligue 2 | No | 872 | 144 | 9 | 4 |
| Championship | No | 1.484 | 0 | 11 | 11 |
| Premier League | Sí | 1.004 | 0 | 0 | 0 |
| Serie A | Sí | 1.020 | 0 | 0 | 0 |
| Serie B | No | 1.039 | 588 | 6 | 63 |
| Liga MX | Sí | 943 | 8 | 14 | 9 |
| Eredivisie | Sí | 855 | 0 | 1 | 0 |
| Eliteserien | No | 658 | 3 | 6 | 6 |
| Primeira Liga | Sí | 854 | 0 | 0 | 0 |
| Allsvenskan | No | 666 | 4 | 7 | 6 |
| Süper Lig | No | 921 | 1 | 6 | 5 |
| Major League Soccer | Sí | 1.482 | 0 | 1 | 1 |

### Desde 2025-01-01

| Competición | Modelo | Terminados | Sin xG | Sin XI completo | Sin jugadores/minutos completos |
| --- | --- | --- | --- | --- | --- |
| Liga Profesional | Sí | 944 | 5 | 15 | 0 |
| Brasileirão Série A | Sí | 679 | 2 | 4 | 4 |
| Super League (Suiza) | No | 408 | 0 | 2 | 1 |
| Bundesliga | Sí | 522 | 0 | 0 | 0 |
| 2. Bundesliga | No | 522 | 0 | 0 | 0 |
| Superliga (Dinamarca) | No | 344 | 0 | 1 | 1 |
| LaLiga | Sí | 657 | 0 | 0 | 0 |
| LaLiga 2 | No | 806 | 7 | 11 | 10 |
| UEFA Champions League | Sí | 222 | 14 | 14 | 0 |
| UEFA Europa League | Sí | 136 | 12 | 11 | 12 |
| Ligue 1 | Sí | 530 | 0 | 2 | 0 |
| Ligue 2 | No | 539 | 2 | 9 | 4 |
| Championship | No | 943 | 0 | 11 | 11 |
| Premier League | Sí | 632 | 0 | 0 | 0 |
| Serie A | Sí | 642 | 0 | 0 | 0 |
| Serie B | No | 639 | 188 | 5 | 22 |
| Liga MX | Sí | 603 | 5 | 8 | 3 |
| Eredivisie | Sí | 538 | 0 | 1 | 0 |
| Eliteserien | No | 416 | 1 | 4 | 4 |
| Primeira Liga | Sí | 539 | 0 | 0 | 0 |
| Allsvenskan | No | 424 | 2 | 5 | 4 |
| Süper Lig | No | 558 | 1 | 5 | 5 |
| Major League Soccer | Sí | 960 | 0 | 0 | 0 |

## Cobertura detallada consultable por el motor desde 2024

| Competición | Sin XI compatible | Sin jugadores compatibles | Sin amarillas | Sin árbitro | Sin córners | Sin cierre 1X2 |
| --- | --- | --- | --- | --- | --- | --- |
| Liga Profesional | 938 | 926 | 1.510 | 1.510 | 208 | 451 |
| Brasileirão Série A | 579 | 581 | 1.045 | 1.045 | 2 | 321 |
| Super League (Suiza) | 638 | 638 | 632 | 632 | 2 | 223 |
| Bundesliga | 478 | 478 | 1 | 811 | 1 | 193 |
| 2. Bundesliga | 828 | 828 | 54 | 819 | 0 | 270 |
| Superliga (Dinamarca) | 537 | 537 | 531 | 531 | 0 | 170 |
| LaLiga | 598 | 598 | 0 | 1.029 | 0 | 261 |
| LaLiga 2 | 1.272 | 1.272 | 106 | 1.261 | 0 | 350 |
| UEFA Champions League | 305 | 90 | 305 | 305 | 8 | 305 |
| UEFA Europa League | 208 | 84 | 208 | 208 | 11 | 208 |
| Ligue 1 | 480 | 478 | 0 | 810 | 0 | 198 |
| Ligue 2 | 872 | 872 | 63 | 863 | 0 | 269 |
| Championship | 1.484 | 1.484 | 108 | 108 | 0 | 389 |
| Premier League | 583 | 583 | 0 | 0 | 0 | 220 |
| Serie A | 589 | 589 | 0 | 1.010 | 0 | 232 |
| Serie B | 1.039 | 1.039 | 79 | 1.029 | 0 | 369 |
| Liga MX | 568 | 564 | 934 | 934 | 11 | 282 |
| Eredivisie | 503 | 502 | 9 | 846 | 0 | 236 |
| Eliteserien | 658 | 658 | 650 | 650 | 3 | 202 |
| Primeira Liga | 501 | 501 | 0 | 845 | 0 | 216 |
| Allsvenskan | 666 | 666 | 655 | 655 | 2 | 192 |
| Süper Lig | 921 | 921 | 55 | 912 | 1 | 225 |
| Major League Soccer | 931 | 933 | 1.467 | 1.467 | 1 | 403 |

## Datos que ya existen, pero requieren integración

Los originales/archivos contienen parejas de amarillas para 8.118 de los 8.412 partidos con hueco en la tabla principal. Es posible recuperar esos campos sin volver a buscar todos los partidos; todavía habría 294 sin pareja encontrada con este criterio. También contienen xGOT en 14.717 partidos sin PSxG canónico. xGOT y PSxG no deben intercambiarse automáticamente: requieren definición, escala y procedencia coherentes.

Existen 873.898 registros archivados de jugadores y 156.660 en la tabla actual. Son observaciones, no jugadores únicos. El puente de identificadores FotMob/API-Football y la normalización de métricas son trabajo pendiente; la presencia de un archivo no convierte esos datos en variables del modelo.

Métricas individuales en la tabla actual, desde 2024 (no nulos; cero cuenta como dato):

| Métrica | Registros con valor | Universo de registros |
| --- | --- | --- |
| Minutos positivos | 156.660 | 156.660 |
| Goles | 156.660 | 156.660 |
| Asistencias | 156.660 | 156.660 |
| Tiros | 156.660 | 156.660 |
| Tiros a puerta | 156.660 | 156.660 |
| Pases clave | 156.660 | 156.660 |
| Entradas | 156.660 | 156.660 |
| Intercepciones | 156.660 | 156.660 |
| Duelos ganados | 156.660 | 156.660 |
| Paradas | 156.660 | 156.660 |
| Nota del proveedor | 154.039 | 156.660 |

Limitación de calidad: el importador actual convierte varios valores ausentes del proveedor en cero (`estadisticas_jugador._n`). Por tanto, estos conteos de no nulos no certifican cobertura real: un cero puede significar “no hizo tiros” o “el proveedor no dio el dato”. Hace falta conservar la distinción antes de confiar en ratings individuales. Estas métricas describen partidos pasados; para pronosticar se necesitan promedios ajustados por minutos, posición, rival, recencia y tamaño de muestra. No se usa el rendimiento final del partido que se intenta predecir. Los originales tienen otras métricas individuales, cuya normalización y calidad no se certifican solo por encontrar una clave JSON.

## Clima, estadio y árbitro en los originales

Se leyeron 20.331 originales FotMob vinculados a partidos terminados desde 2024, sin errores de lectura. 8.623 contienen un campo de temperatura, 20.331 un bloque de estadio y 20.140 un bloque de árbitro. Son campos encontrados, pendientes de validar unidades, precisión, identidad y fecha de observación. No existe una tabla/columna dedicada de clima, sede o coordenadas en el esquema consultado, y el motor no consume estos bloques.

| Competición | Originales | Temperatura | Estadio | Árbitro |
| --- | --- | --- | --- | --- |
| ar.primera | 1.291 | 590 | 1.291 | 1.267 |
| br.serie_a | 1.036 | 474 | 1.036 | 901 |
| ch.super_league | 630 | 257 | 630 | 630 |
| de.bundesliga | 810 | 342 | 810 | 810 |
| de.bundesliga2 | 819 | 344 | 819 | 819 |
| dk.superliga | 531 | 226 | 531 | 531 |
| es.laliga | 1.029 | 449 | 1.029 | 1.029 |
| es.laliga2 | 1.252 | 547 | 1.252 | 1.252 |
| eu.ucl | 283 | 144 | 283 | 283 |
| eu.uel | 195 | 83 | 195 | 195 |
| fr.ligue_1 | 810 | 351 | 810 | 810 |
| fr.ligue_2 | 862 | 360 | 862 | 862 |
| gb.championship | 1.461 | 639 | 1.461 | 1.461 |
| gb.premier_league | 994 | 430 | 994 | 994 |
| it.serie_a | 1.010 | 430 | 1.010 | 1.010 |
| it.serie_b | 1.028 | 396 | 1.028 | 1.028 |
| mx.liga_mx | 923 | 384 | 923 | 891 |
| nl.eredivisie | 846 | 363 | 846 | 846 |
| no.eliteserien | 647 | 268 | 647 | 647 |
| pt.primeira | 845 | 362 | 845 | 845 |
| se.allsvenskan | 653 | 263 | 653 | 653 |
| tr.super_lig | 911 | 355 | 911 | 911 |
| us.mls | 1.465 | 566 | 1.465 | 1.465 |

En el bloque de clima revisado se encontraron campos de humedad en 8.623 originales, viento en 8.623 y lluvia/precipitación en 8.623. Quedan 12.231 partidos sin temperatura encontrada por este criterio. Se inspeccionan claves del bloque `content.weather`: presencia no equivale a unidades ni calidad verificadas; un icono meteorológico tampoco equivale a medir milímetros de lluvia. Para condiciones completas se necesita validar estos campos, una fuente meteorológica previa al encuentro y la ubicación real del estadio.

El clima puede afectar el esfuerzo físico, pero no demuestra automáticamente una mejora de la predicción de ganador o goles. Un estudio de 1.530 partidos de Bundesliga encontró cambios en distancia y esfuerzos de sprint relacionados con temperatura y adaptación de jugadores: [Chmura et al., PLOS ONE, 2021](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0247771). Conviene probar temperatura, humedad, viento, lluvia y condiciones del campo con interacciones por equipo/sede, sin inventar ajustes fijos. Para simular pronósticos pasados se necesitan los pronósticos meteorológicos disponibles en ese momento; el tiempo observado después no prueba disponibilidad previa.

## Próximos siete días

Hay 227 partidos programados: 140 en competiciones modeladas y 87 en competiciones sin ese modelo. Todos tienen identificadores de partido y clubes de API-Football. Los 140 modelados tienen una consulta de bajas en las últimas 24 horas; 89 en las últimas 4 horas. Los otros 87 no están incluidos en la captura de bajas por configuración. De los 140 modelados, el modelo reconoce con su criterio de muestra efectiva a ambos equipos en 129; quedan 11 que merecen revisión de muestra/clubes.

No había ningún partido en la ventana de captura de XI (20–90 minutos antes del inicio). Por eso la ausencia de XI confirmados para los siguientes días no se marca como fallo. En 49 de los 227 hay las tres selecciones 1X2 de Pinnacle capturadas en las últimas 24 horas: es una medida de cobertura, no certificación de que el snapshot sea simultáneo, vigente o apto para publicar.

| Competición | Próximos | Bajas revisadas ≤24h | XI pendientes en ventana | 1X2 Pinnacle ≤24h |
| --- | --- | --- | --- | --- |
| Liga Profesional | 16 | 16 | 0 | 3 |
| Brasileirão Série A | 10 | 10 | 0 | 1 |
| Super League (Suiza) | 0 | 0 | 0 | 0 |
| Bundesliga | 9 | 9 | 0 | 1 |
| 2. Bundesliga | 9 | 0 | 0 | 2 |
| Superliga (Dinamarca) | 6 | 0 | 0 | 1 |
| LaLiga | 10 | 10 | 0 | 1 |
| LaLiga 2 | 11 | 0 | 0 | 1 |
| UEFA Champions League | 11 | 11 | 0 | 6 |
| UEFA Europa League | 3 | 3 | 0 | 0 |
| Ligue 1 | 9 | 9 | 0 | 1 |
| Ligue 2 | 9 | 0 | 0 | 5 |
| Championship | 17 | 0 | 0 | 4 |
| Premier League | 10 | 10 | 0 | 0 |
| Serie A | 10 | 10 | 0 | 1 |
| Serie B | 10 | 0 | 0 | 1 |
| Liga MX | 13 | 13 | 0 | 3 |
| Eredivisie | 9 | 9 | 0 | 1 |
| Eliteserien | 8 | 0 | 0 | 0 |
| Primeira Liga | 0 | 0 | 0 | 0 |
| Allsvenskan | 8 | 0 | 0 | 1 |
| Süper Lig | 9 | 0 | 0 | 1 |
| Major League Soccer | 30 | 30 | 0 | 15 |

## Otros datos del partido para evaluar una mejora

| Prioridad propuesta | Datos concretos | Estado / propósito |
| --- | --- | --- |
| 1 | XI confirmado, suplentes, posición, minutos esperados, titulares ausentes y calidad del reemplazo | Hay archivos e integración experimental; conectar identidades y evaluar contribución de ataque/defensa/portero |
| 1 | Lesión, sanción, duda, causa de baja, inicio, retorno esperado y momento de publicación | Captura parcial; transformar ausencia en pérdida de minutos/valor, sin confundir duda con baja segura |
| 1 | Cuotas de apertura, antes/después del XI y cierre; casas, margen, liquidez cuando disponible y hora exacta | Es entrada operativa clave del selector actual; medir movimientos sin usar cuotas futuras |
| 1 | Rendimiento reciente: xG a favor/en contra, sin penaltis, tiros, ocasiones, portero y balón parado | Completar huecos y armonizar fuentes; ajustar por rival, localía y expulsiones |
| 2 | Horas/días de descanso, partidos 7/14/30 días, minutos por jugador y tiempo extra previo | Descanso/congestión parcialmente derivables del calendario; probar carga individual y rotación |
| 2 | Viaje, distancia, husos horarios, altitud, cancha neutral, césped y estadio real | No integrados; necesitan ubicación real y no asumir siempre el estadio del club local |
| 2 | Entrenador vigente, fecha del cambio, formación, estilo y continuidad de plantilla | No son entradas directas actuales; capturar cambios con fecha y probar con suficiente muestra |
| 2 | Fase de competición, ida/vuelta, marcador global, prórroga posible, clasificación y calendario próximo | Definir escenarios objetivos; no asignar un número subjetivo de “motivación” |
| 3 | Temperatura, humedad, viento/ráfagas, lluvia, estado del campo y hora del pronóstico del tiempo | Temperatura aparece en originales; faltan integración y pronósticos previos auditables |
| 3 | Árbitro confirmado, tarjetas, faltas, penaltis y expulsiones por encuentro | Ya existe uso específico en tarjetas; recuperar identificadores y comprobar sesgo de asignación |

La prioridad es una propuesta de trabajo, no una promesa de mejora. Cada bloque debe demostrar valor añadido frente al motor actual en partidos posteriores al entrenamiento, con cortes por liga y mercado, calibración, log loss/Brier y comparación con el mercado; si afecta picks, también valor frente al cierre y estabilidad. No basta subir el porcentaje de aciertos ni añadir variables. Registrar la recepción real y usar solo información disponible antes de cada decisión.

## Orden de trabajo recomendado

1. Integrar los datos ya conservados (XI, jugadores, amarillas, árbitro y sede) con identidades y trazabilidad; completar los 1.222 huecos xG con fuentes comprobables.
2. Evaluar un nuevo entrenamiento con los xG recibidos después del ajuste actual, conservando el modelo activo hasta superar las pruebas.
3. Validar XI/valor del jugador/bajas y carga de minutos en paralelo, usando el historial completo ya recuperado y observaciones antes del inicio.
4. Incorporar descanso, contexto y sede; después probar clima y otros bloques por separado.
5. Mantener una matriz por liga con tres estados: disponible, integrado y acreditado antes de la decisión.

## Verificación y límites

Se contrastó el código desplegado con los archivos locales relevantes (hashes coincidentes), el artefacto y los interruptores activos, las predicciones recientes y las tablas de datos. Se verificaron las sumas de 23 ligas por periodo y coherencia entre cobertura archivada, compatible y anterior al inicio. Arnés inicial: 1.084 pruebas aprobadas, 24 omitidas; Docker no disponible localmente. Este trabajo no modifica código de ejecución; los recuentos están guardados en `.local/model_data_audit_20261013/{schema,coverage,operational,raw_quality}.json`. No se realizó un nuevo entrenamiento ni se certificó la precisión de las variables nuevas. Los conteos son una fotografía de una base que sigue recibiendo partidos.
