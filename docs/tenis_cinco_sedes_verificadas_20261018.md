# Cinco sedes prioritarias: coordenadas y cobertura reconstruida

18 de octubre de 2026. Se verificaron referencias geográficas de Hua Hin, Yucatán, Seúl, Abu Dabi y Martín Carpena. Se reconstruyó un conjunto nuevo, conservando los archivos y experimentos anteriores. Esto mejora la disponibilidad de datos, sin demostrar una mejora predictiva ni activar una corrección.

## Resultado medido

| Indicador | Antes | Después |
|---|---:|---:|
| Partidos con identidad de sede | 11.240 | 11.240 |
| Partidos con coordenadas de destino | 10.510 | 10.774 |
| Variables espaciales completas para ambos jugadores | 6.126 | 6.651 |
| Cohorte apta tras filtros y particiones | 5.798 | 6.244 |
| Aptos excluyendo referencias de más de 1 km de tolerancia | 5.569 | 5.943 |
| Entradas de sede sin coordenadas | 88 | 83 |

Se recuperaron los 264 destinos previstos y 446 partidos adicionales quedaron aptos para análisis espacial. Son cantidades distintas: conocer la sede también permite completar algunos antecedentes de jugadores en torneos posteriores. No se convirtió toda sede nueva en transición válida automáticamente.

La cobertura de destino es 95,85 % de los 11.240 objetivos. La cohorte espacial apta representa el 55,55 %. Contiene 3.226 partidos de desarrollo 2024 (ATP 1.273, WTA 1.953) y 3.018 exploratorios de 2025 (ATP 1.281, WTA 1.737). Las particiones originales permanecen intactas: 5.661 de desarrollo, 5.378 exploratorios y 201 en cuarentena de frontera.

## Referencias verificadas

Los valores siguientes son WGS84. La tolerancia expresa representatividad del recinto para el análisis, no exactitud de un levantamiento topográfico. Las elevaciones son terreno Copernicus GLO-90 consultado mediante Open-Meteo, no alturas medidas de las pistas.

| Recinto | Latitud | Longitud | Terreno, m | Tolerancia, m | Destinos recuperados |
|---|---:|---:|---:|---:|---:|
| Arena Hua Hin | 12,537582 | 99,958213 | 5 | 500 | 62 |
| Yucatán Country Club, referencia del complejo | 21,120522 | −89,600111 | 6 | 1.800 | 58 |
| Olympic Park Tennis Centre, Seúl | 37,515428 | 127,128402 | 23 | 500 | 54 |
| International Tennis Centre, Abu Dabi | 24,413640 | 54,459255 | 6 | 500 | 54 |
| Martín Carpena, Málaga | 36,682387 | −4,460400 | 20 | 400 | 36 |

**Hua Hin.** Se utilizó el punto de lugar del mapa insertado por el [propietario del recinto](https://arenahuahin.com/en/contact-us/), contrastado con el complejo de tenis OSM `way/1068701726`, que enlaza al mismo propietario. Las referencias difieren unos 71 m. Se conservan los enlaces históricos independientes de las dos ediciones de 2024; no se asigna una edición de 2026 hacia atrás.

**Yucatán.** El [propietario](https://www.inmobilia.mx/yucatancountry) enlaza un punto del complejo. No se aceptó el resultado inicial de geocodificación que identificaba una localidad homónima. La zona de tenis OSM `way/1359255118` está a aproximadamente 1.102 m del punto publicado por el propietario. Por ello se utiliza una referencia del complejo con tolerancia de 1.800 m, no una posición exacta de las pistas históricas. Esa referencia queda marcada como amplia y se excluye de la sensibilidad de más de 1 km. La posición actual de las pistas no se proyecta como si acreditara dónde estaban instaladas en cada edición de 2024/2025.

**Seúl.** Se obtuvo un punto representativo de la geometría del estadio de tenis OSM `relation/8679966`: centro de la caja envolvente de su anillo exterior. La dirección coincide con la del [operador](https://www.ksponco.or.kr/sports/menu.es?mid=a70404000000). La coordenada estructurada del recinto Q7451681 está a unos 61 m y sirve de corroboración. No se utiliza un punto genérico del parque olímpico ni el centro de otro estadio del parque.

**Abu Dabi.** Se aceptó el objeto de estadio de tenis OSM `way/93051899`, identificado como Abu Dhabi International Tennis Centre. La [descripción del operador](https://www.zsc.ae/en/sport/tennis) identifica el recinto y su uso en el torneo. La corroboración es de identidad y ubicación del objeto nombrado; no se presenta como una segunda medición independiente de coordenadas. Se descarta la posición del estadio de fútbol próximo.

**Málaga.** La [Junta de Andalucía](https://www.juntadeandalucia.es/cultura/agendaculturaldeandalucia/espacios/palacio-de-deportes-jose-maria-martin-carpena) publica GeoCoordinates del recinto. El estadio OSM `way/1235193701` queda a unos 18 m. La parada de taxis llamada Martín Carpena no se acepta como recinto. Se conservan los enlaces históricos de Davis y BJK 2024 por eliminatoria o edición ya revisados.

## Protección de datos y modelos

El registro nuevo solo modifica las cinco entradas geográficas previstas y añade sus fuentes; no cambia enlaces de ediciones, enlaces por partido ni zonas horarias. Contiene 240 entradas de sede, incluidas equivalencias físicas, de las que 157 tienen coordenadas; no se interpretan como 240 instalaciones físicas distintas. Hay 294 fuentes verificadas por huella, catorce más que en la versión anterior.

La reconstrucción mantiene antecedentes desconocidos sin saltarlos, ambigüedades de periodos, diferencias de huso con DST y la separación por competición completa. Las fuentes nuevas conservan su adquisición real de octubre de 2026. El estudio sigue siendo retrospectivo, sin disponibilidad histórica simulada. No se imputan horas de llegada, finalización, descanso ni vuelos.

La auditoría comprobó que los 5.798 partidos previamente aptos continúan aptos y conservan exactamente sus seis variables espaciales por jugador. También verificó los archivos anteriores con los recibos de sus auditorías, la fuente canónica, los CSV originales y los doce artefactos congelados. Ninguno fue sobrescrito.

Las métricas ya calculadas de la fase espacial y de carga siguen referidas a sus muestras originales. No se vuelven a presentar como si hubieran evaluado los 6.244 partidos nuevos. No se ajustaron modelos ni se modificaron probabilidades. La mejora de cobertura no demuestra rentabilidad, CLV o superioridad predictiva.

## Archivos entregados y verificación

Resultado versionado: `data/tennis/historical_geography_top5_20261018/`. Contiene originales y recibos, registro previo a elevación y registro final, revisión de coordenadas, conjunto reconstruido, cohorte apta, los 446 partidos recién aptos, catálogo, particiones, pendientes y auditoría.

Los scripts `build_top5_geography.py` y `audit_top5_geography.py` están entregados en el directorio `scripts` del motor aislado. El constructor utiliza únicamente los archivos ya archivados, valida identidades concretas de los objetos geográficos y se niega a sobrescribir un registro terminado. El auditor reproduce los controles de cobertura y procedencia; puede ejecutarse desde la raíz del proyecto sin red. Los recibos de adquisición se conservan, incluidas consultas vacías o fallidas que no se aceptan como evidencia.

Pasaron las 194 pruebas existentes de tenis. No se introdujeron cambios en las fórmulas del motor. La auditoría desde la entrega aislada y la revisión de formato pasaron. Se realizó una sola consulta pública adicional de elevación para cinco puntos y ninguna consulta a The Odds API o API-Tennis: cero créditos deportivos.

El arnés general inicial y final aprobó 1.315 pruebas, omitió 94 y emitió dos avisos; el final tardó 123,15 segundos. Docker no estaba disponible para esa comprobación. Los dos scripts entregados coinciden por huella con los utilizados en la reconstrucción y auditoría.

## Pendientes que permanecen

Quedan 83 entradas sin coordenadas, que afectan a 466 destinos. La cola actualizada `geography_priority_queue.json` comienza con SDAT Tennis Stadium (31 partidos), Country Time Club (31), King Saud University Sports Arena (30), Hengqin International Tennis Center (15) y Shenzhen Bay Sports Centre Arena (14). Esas cinco suman 121 destinos pendientes.

Los antecedentes sin sede, la falta de cobertura completa de dobles y las horas sin acreditar siguen limitando viajes y ventanas de carga de 3/7 días. No se intentó resolverlos con supuestos horarios en esta fase. La siguiente ampliación geográfica puede seguir esa cola, mientras las variantes predictivas permanecen experimentales hasta una validación temporal suficiente.
