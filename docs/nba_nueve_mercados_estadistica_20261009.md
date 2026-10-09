# NBA — nueve mercados estadísticos (NBA-RUN-071)

Página publicada: https://pronosticosdeportivos.pro/nba. Nueve mercados desarrollados: ganador, puntos de equipo, total del partido, puntos de jugador, rebotes, asistencias, triples, robos y tapones. Hay 42 pronósticos nuevos registrados antes de los tres partidos del 20–21 de octubre. El piloto original conserva sus 15 unidades y registros independientes. Hoy no hay resultados oficiales de esos encuentros.

## Datos y modelos

Se recuperaron seis estadísticas a partir de los originales ya recibidos de llimllib/nba_data y sportsdataverse/sportsdataverse-data, con huellas verificadas. Se cruzaron exclusivamente las identidades NBA y los puntos/rebotes/asistencias aceptados. Una discordancia de las nuevas columnas, fechas, equipos, suma de puntos/triples/robos/tapones o condición local/visitante excluye el partido completo. El histórico nuevo contiene 157.962 filas individuales y 6.108 partidos regulares, 2021-10-19 a 2026-04-12. Los 42 partidos excluidos permanecen identificados, y el histórico anterior de 164.218 filas no cambia.

Los seis mercados individuales usan tasa por minuto con regularización Gamma, variación histórica de minutos y mezcla con la distribución empírica de las últimas 20 participaciones positivas; requieren al menos diez y excluyen apariciones de más de 370 días. No usan los minutos reales del partido objetivo. Son pronósticos condicionados a participación, sin estimación de probabilidad DNP ni disponibilidad final acreditada. La mezcla se aproxima mediante momentos de una binomial negativa; no es el candidato confirmatorio de rebotes de RUN067.

Ganador usa Elo, ventaja local fija y regresión al comienzo de temporada. Puntos de equipo combinan ataque reciente y defensa del oponente; total usa la suma de medias y la covarianza de residuos de ambos equipos, estimada sólo con entrenamiento. Los totales tienen una aproximación normal y rangos continuos; incluyen prórroga en el objetivo. Los mercados se calculan por separado: no constituyen una distribución conjunta de todas las estadísticas de jugadores, de equipos y del ganador. No hay cuotas, dinero ni límites de una casa como variables del modelo.

Todo partido de una fecha se pronostica antes de incorporar cualquier resultado de esa fecha. Entrenamiento: 2021–22; calibración: 2022–23; evaluación exploratoria: 2023–24 a 2025–26. Candidato y referencia reciben la misma calibración logística, período y restricciones. El primer cálculo con referencia sin recalibrar se conserva como preliminar; el protocolo de comparación justa se registró antes de inspeccionar sus métricas. Se vectorizaron cálculos equivalentes; no se cambió el método según los aciertos de evaluación.

Los umbrales son `floor(media de las últimas diez apariciones)+0.5`, o su equivalente de equipo/total. No son líneas ofertadas por una casa. Ganador se evalúa contra el resultado local/visitante. Las métricas de clasificación usan esos objetivos específicos; no hay una clasificación universal comparable con mercados de casas o líneas alternativas.

## Lectura del histórico

Se selecciona el lado con probabilidad calculada ≥70%. Cobertura se refiere a unidades históricas elegibles, condicionadas a participación para jugadores. Las seis estadísticas comparten 74.623 unidades y 3.649 partidos evaluados. Hay 3.649 unidades de ganador/total y 7.298 de puntos de equipo.

| Mercado | Selecciones ≥70% | Acierto observado | Cobertura | Referencia en mismas unidades |
| --- | ---: | ---: | ---: | ---: |
| Ganador | 1.071 | 80,4% | 29,4% | 69,5% |
| Puntos de equipo | 1.721 | 74,3% | 23,6% | 53,3% |
| Total del partido | 583 | 70,5% | 16,0% | 52,1% |
| Puntos de jugador | 83 | 65,1% | 0,1% | 65,1% |
| Rebotes | 2.474 | 65,6% | 3,3% | 65,7% |
| Asistencias | 6.470 | 71,5% | 8,7% | 70,3% |
| Triples | 30.629 | 77,9% | 41,0% | 77,1% |
| Robos | 21.795 | 75,6% | 29,2% | 75,6% |
| Tapones | 45.100 | 80,3% | 60,4% | 80,3% |

Los porcentajes altos de tapones/robos pueden provenir de su baja frecuencia; su clasificación no mejora necesariamente frente a la referencia en las mismas selecciones. En puntos/rebotes individuales, el filtro ≥70% sobreestima el acierto: probabilidades medias 70,9%/72,2% frente a aciertos 65,1%/65,6%. No deben presentarse como selecciones fiables al 70%. Los modelos conservan clasificación experimental y `actionable=false`.

La comparación también contiene Brier, logloss, MAE, bins de calibración, selección ≥80% y diferencias pareadas de Brier con 400 remuestreos por partido, semilla 20261009. Los intervalos describen esta evaluación retrospectiva: no corrigen búsqueda histórica de modelos, dependencia entre fechas, recepción original desconocida o las comparaciones múltiples. Una mejora de Brier no equivale a rentabilidad ni a liquidación real. Ninguna puerta científica cambia.

## Publicación y resultados

El paquete de 42 unidades enlaza las huellas de protocolo, datos, código, modelo y plan original. La web filtra nueve mercados, muestra probabilidades, rango central 80%, fecha de registro, umbral estadístico y tabla de acierto/probabilidad media/cobertura/referencia. Probabilidades de umbral calibradas y rangos de la distribución original se distinguen explícitamente. Se mantienen los 15 pronósticos originales y sus cuotas históricas en una sección separada.

La extensión lee el diario y los cuerpos oficiales recibidos por el seguimiento original del VPS, verificando sellos, recibo, huellas, equipos, fecha y partido final. No consulta proveedores deportivos desde la web. Cada estadística adicional debe reconciliar con el equipo; una columna ausente queda en revisión y un DNP queda separado, sin convertirlo en cero. Puntos finales reconciliados alimentan ganador/equipos/total. Un fallo de la extensión no altera resultados originales.

Se reemplazó exclusivamente el contenedor web NBA, conservando el anterior detenido y recuperable. El nombre de servicio interno continúa `nba-dashboard-run69`, con imagen `nba-dashboard-run71:20261009` y etiqueta de alcance RUN071. Código y paquete sellado viven en `/home/qf/nba-isolated/dashboard/run71-20261009`. Fuentes originales montadas sólo para lectura; ninguna credencial, puerto NBA del host ni nueva copia periódica. Proxy, fútbol, captura, piloto y alertas conservan identidad y estado. Cero llamadas de pago y apuestas.

Verificación: nueve filtros con cantidades exactas, 42 tarjetas nuevas/15 originales, nueve filas de comparación, consola sin errores y sin desbordamiento horizontal a 1280×720. CSS/JS públicos coinciden con las huellas del paquete. Reinicio y HTTPS comprobados; rutas privadas siguen protegidas. Verificación móvil visual de 390 píxeles sigue pendiente por la limitación de tamaño del navegador ya documentada en RUN069–070. Pruebas NBA: 577 pasan y 18 se omiten en esta configuración. El arnés final y la preservación de evidencia quedan registrados en el checkpoint de RUN071.

## Reproducción

Módulo `nba.multimarket`: comandos `recover`, `evaluate`, `forecast`, con `--output`, `--protocol`, `--data`; `forecast` también requiere `--plan`. Usar una carpeta nueva para una cohorte prospectiva: rechaza sobrescribir el paquete sellado, alterar datos/código/modelo o registrar después del inicio. Las entradas concretas de RUN071 se conservan en `apps/nba/.local/normalized/nba_f6_run71_20261009/`, con `evaluation_protocol.json`, `data/coverage.json`, `model.json`, `comparison.json`, `bundle.json` y `bundle.seal.json`.

Es una extensión completa de investigación de los nueve mercados y estos tres partidos; no habilita entrenamiento diario para toda la liga ni una nueva confirmación científica. Sigue pendiente recibir finales y disponibilidad de los partidos futuros, ampliar evaluación prospectiva y acreditar contratos/liquidación de casas para uso comercial. No se recupera la primera recepción histórica desconocida al descargar archivos hoy.
