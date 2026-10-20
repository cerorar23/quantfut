# Tenis: coordenadas completadas y modulo de viajes entre torneos

Revision del 18 de octubre de 2026. Trabajo local de investigacion, sin modificar probabilidades ni publicar apuestas.

## Resultado espacial

Los 27 recintos pendientes tienen pares WGS84 revisados, fuentes archivadas y una tolerancia espacial explicita. Se contrastaron nombres, direcciones, complejos y geometria; no se aceptaron centros de ciudad, paradas de autobus, calles homonimas ni coordenadas de encuadre de mapas. En China se utilizaron geometrías OSM WGS84, evitando importar posiciones GCJ02 sin verificar.

Se incorporaron 46 fuentes, cuatro de ellas extracciones de hechos publicos observados en el navegador, etiquetadas expresamente como tales; no son respuestas HTTP archivadas. No se guardaron datos de cuenta ni historial del navegador. Las posiciones representan el recinto o el complejo, no acreditan la pista de cada encuentro. Las tolerancias de 150 a 1.100 metros son margenes conservadores de representatividad espacial, no errores topograficos medidos ni intervalos estadisticos. Cali representa un club amplio; Nana, Skanes y Forte Village representan complejos hoteleros/deportivos.

Una consulta gratuita y sin clave a Open-Meteo devolvio 27 elevaciones, verificando cantidad, orden y coordenadas contra el manifiesto. Son estimaciones del terreno Copernicus DEM 2021 GLO-90 (resolucion horizontal 90 m), no mediciones de la altura de las pistas. Su utilidad depende tambien de la precision de la ubicacion. Fuentes: [documentacion de elevacion](https://open-meteo.com/en/docs/elevation-api), Open-Meteo y programa Copernicus, DOI 10.5270/ESA-c5d3d65. Geometria: OpenStreetMap contributors, ODbL, [atribucion y licencia](https://www.openstreetmap.org/copyright).

El registro conserva 35 recintos, 52 enlaces de edicion y 89 revisiones espaciales/altimetricas, con 112 fuentes en total. La muestra archivada pasa de 102/228 a **228/228 con coordenadas y elevacion**. Mantiene las 48 correcciones de temporada ya revisadas. La instantanea original sigue siendo la recibida el 17-oct a las 21:12:56 UTC; este enriquecimiento no es un calendario actualizado ni verifica horarios o participantes.

La consulta real inmediatamente anterior al registro de las coordenadas nuevas conserva 102/228 con coordenadas y altitud: ninguna disponibilidad se retrodata. Los doce hashes de artefactos prospectivos congelados siguen intactos. Cero consultas deportivas, cero creditos de The Odds API y ninguna llamada a servicios de rutas/vuelos durante esta fase.

Artefactos en `data/tennis/coordinates_20261018/`:

- `coordinate_manifest.json`: 27 selecciones explicitas, IDs de objetos, fuentes, alcance y tolerancia espacial; tambien candidatos rechazados.
- `coordinate_sources.json` y `originals/`: recibos, originales y hashes. Las extracciones de navegador estan separadas de HTTP/XML/JSON.
- `registry_seed_coordinates_v2.json` y `registry_seed_elevation.json`: semillas reproducibles; esta ultima contiene las revisiones completas.
- `calendar_georeferenced.json` e `integration_audit.json`: cobertura y comprobacion temporal.
- `travel_input_readiness.json`: auditoria de lo que realmente permite el historial disponible.

## Calculo de viajes implementado

`tennis_engine/travel.py` en el checkout aislado incorpora `InterTournamentTravelExtractor`, `TournamentTransition`, `Evidence` y `TransportPolicy`.

- Solo admite transiciones revisadas entre ediciones. Un cambio de pista dentro de la misma edicion no crea un viaje nuevo. Dos torneos semanales distintos en el mismo recinto pueden tener distancia cero.
- Exige procedencia integra y recibida antes de la decision; sedes y versiones deben estar disponibles en ese momento. Las marcas de cierre iguales o posteriores a la decision se rechazan.
- Antes de calcular exposiciones exige verificar consecutividad, debut y cierre de participacion, incluyendo otras disciplinas cuando correspondan. La ausencia de un evento en una respuesta no acredita estos hechos.
- Devuelve distancia geodesica y margen espacial; diferencia horaria firmada con zonas IANA y horario de verano, evaluando ambas zonas al mismo instante; direccion geografica; altitud de destino y cambio de altitud.
- Identifica candidatos de cruce de linea de fecha, incluidas desviaciones politicas donde el salto de reloj supera 12 horas. El salto de calendario no se interpreta como magnitud fisiologica de jet lag.
- Transporte candidato configurable: avion para separaciones de al menos 1.000 km; carretera para mas de cero y hasta 200 km solo si se ha confirmado conexion por carretera; los restantes casos quedan desconocidos. Son reglas operativas experimentales, no itinerarios observados ni umbrales fisiologicos.
- Tiempo entre salida previa y debut **programado**, con cotas cuando existe un intervalo verificado. No acepta horarios programados previos o intervalos de sondeo como si fueran horas reales de cierre. Sin llegada observada, descanso real y dias de adaptacion permanecen desconocidos.

Se corrigio tambien el contexto anterior: ya no convierte automaticamente dos partidos consecutivos en un viaje. La carga y el cambio de superficie siguen disponibles segun sus propios contratos.

## Limite de los datos y siguiente fase

La base local contiene 879 eventos observados, incluidos 579 finalizados y 35 retirados. Hay historial candidato para 183 de las 456 filas jugador-encuentro de la muestra, ordenado solo por fecha programada del proveedor. Ese orden no verifica la secuencia real de viajes. No hay horas reales de cierre acreditadas; tampoco se ha probado, para esas filas, el debut, la cobertura de otros torneos/dobles y el cierre completo de participacion. Por ello la auditoria devuelve **cero transiciones completamente verificadas**, sin fabricar valores.

El siguiente paso es construir revisiones de participacion por jugador y edicion, cubrir individuales/dobles/clasificacion y registrar evidencias de debut y cierre. Donde no sea posible recuperar una hora real, conservar desconocidos o intervalos solo cuando esten respaldados. El registro por cambios de estado describe observaciones del proveedor, no el instante exacto del evento en pista. Despues se evaluaran variables separadas y regularizadas mediante comparaciones temporales en muestra comun; ningun indice de fatiga manual se incorpora a las probabilidades.

## Validacion

143 pruebas de tenis aprobadas sobre el codigo entregado, incluidas 17 nuevas: China-Paris, horario de verano, linea de fecha, dobles pendientes, traslados dentro del torneo, isla-carretera, marcas futuras, originales alterados, intervalos y disponibilidad temporal de sedes. El primer intento de pruebas en el directorio temporal predeterminado fallo por permisos del entorno; la suite completa paso usando un directorio temporal permitido en el workspace.

No hay mejoras de rendimiento predictivo ni rentabilidad demostradas por esta fase: se completo la infraestructura espacial y el calculo experimental sujeto a evidencia.

## Recintos nuevos: posiciones representativas y terreno

| Recinto | Latitud | Longitud | Margen espacial (m) | Elevacion DEM (m) |
|---|---:|---:|---:|---:|
| Match Ball Firenze Country Club | 43.767243 | 11.329415 | 300 | 59 |
| Bayard H. Friedman Tennis Center | 32.704854 | -97.371129 | 300 | 198 |
| Club Campestre Farallones | 3.326096 | -76.540532 | 1100 | 1033 |
| Nansha International Tennis Center | 22.784648 | 113.508998 | 450 | 6 |
| Club Internacional de Foot-ball (CIF) | 38.714664 | -9.210283 | 450 | 99 |
| Tennis School Monte Ka Tira | 37.562563 | 15.100979 | 250 | 316 |
| Jinan Olympic Sports Center Tennis Venue | 36.654756 | 117.119948 | 650 | 128 |
| TK Zlatni rat | 43.262414 | 16.639771 | 400 | 38 |
| Lyttos Beach Sportscenter | 35.333534 | 25.353267 | 300 | 12 |
| NANA Tennis & Sports Club | 35.303410 | 25.420869 | 650 | 13 |
| Magic Hotel Skanes Family Monastir | 35.763985 | 10.745720 | 500 | 5 |
| Soho Square Tennis Complex | 27.961882 | 34.392296 | 300 | 36 |
| HNTA | 48.275366 | 22.043198 | 300 | 103 |
| Academia de Tenis Kikuxi Villas Club | -9.000392 | 13.338344 | 200 | 138 |
| Qiandaohu Tennis Park | 29.635885 | 119.041964 | 300 | 108 |
| MSLTA Tennis Centre, District Sports Complex | 17.654371 | 75.920568 | 350 | 482 |
| Complexo Municipal de Tenis da Maia | 41.234220 | -8.615813 | 250 | 84 |
| Polideportivo Municipal de Magaluf | 39.511598 | 2.531372 | 350 | 7 |
| Tennis Club Terranova | 40.928883 | 9.497352 | 250 | 3 |
| Halle Andre Vacheresse | 46.031185 | 4.051548 | 150 | 284 |
| PalaBaldresca / Circolo Tennis Rovereto | 45.879980 | 11.029473 | 300 | 184 |
| National Tennis Center, Bacioi | 46.951303 | 28.904472 | 350 | 115 |
| GuangMing QunZhong Sports Center | 22.751039 | 113.943611 | 450 | 40 |
| Sun Oaks Club | 40.557195 | -122.306828 | 250 | 176 |
| Club Avantage / Academie Aliassime | 46.830372 | -71.284951 | 250 | 19 |
| ASD Fortevillage | 38.936824 | 8.930935 | 650 | 20 |
| Tennis Club Avgusta Trayana | 42.432885 | 25.612451 | 250 | 302 |

Verificacion general final: 1.300 pruebas aprobadas, 88 omitidas y dos avisos en 138,58 segundos; comprobacion correcta. Docker no disponible en este entorno. Diffcheck del checkout de tenis correcto. Los modulos y pruebas entregados coinciden por hash con los validados.

