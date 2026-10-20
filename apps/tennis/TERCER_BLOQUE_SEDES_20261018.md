# Tercer bloque de sedes y evaluación espacial — 18 de octubre de 2026

Se añadieron referencias geográficas de Taipei, BolognaFiere, Manchester, Vilna y Biel, conservando los enlaces de las ediciones históricas. El resultado amplía la cobertura; la corrección espacial sigue experimental y sin evidencia clara de mejora.

## Cobertura

| Indicador | Antes | Después |
|---|---:|---:|
| Partidos objetivo | 11.240 | 11.240 |
| Con coordenadas de destino | 10.895 | 10.954 |
| Con variables completas de ambos jugadores | 6.845 | 6.874 |
| Aptos para comparación probabilística | 6.414 | 6.442 |
| Aptos sin referencias de más de 1 km | 6.107 | 6.135 |
| Entradas pendientes del registro | 78 | 73 |
| Destinos sin coordenadas | 345 | 286 |

Los 59 destinos recuperados no equivalen a 59 partidos aptos: la procedencia observada, los solapamientos de periodos y la integridad del resultado siguen condicionando la elegibilidad. Se incorporan 28 aptos: 16 de desarrollo 2024 y 12 exploratorios 2025, todos ATP. Ahora hay 3.322 de desarrollo y 3.120 de evaluación; los 201 objetivos en cuarentena permanecen intactos. Los 6.414 aptos anteriores conservan sus variables numéricas.

## Cinco referencias revisadas

| Recinto | Latitud WGS84 | Longitud WGS84 | Tolerancia | Terreno DEM | Destinos |
|---|---:|---:|---:|---:|---:|
| Taipei Tennis Center | 25,0667241 | 121,5966552 | 500 m | 17 m | 14 |
| SuperTennis Arena, pabellón 37 de BolognaFiere | 44,5099879 | 11,36697855 | 500 m | 40 m | 14 |
| AO Arena, Manchester | 53,4880867 | -2,2441724 | 500 m | 35 m | 12 |
| SEB Arena, Vilna | 54,7069912 | 25,2347764 | 500 m | 176 m | 10 |
| Swiss Tennis Arena, referencia del complejo de Biel | 47,1587958 | 7,2780037 | 600 m | 445 m | 9 |

Las tolerancias son márgenes de representatividad, no precisión topográfica medida. Una única consulta pública a Open-Meteo obtiene elevación Copernicus GLO-90 del terreno del punto; no altura medida de la cancha o de una plataforma interior. Se completan los husos IANA `Asia/Taipei`, `Europe/Vilnius` y `Europe/Zurich`; Bolonia y Manchester conservan los existentes.

- **Taipei:** geometría OSM 189781451, centro de tenis en Minquan East Road, sección 6, número 208. La [página del operador](https://www.tsc.taipei/) confirma la dirección mediante un extracto archivado del buscador; los accesos directos fallaron y no cuentan como HTML recibido. Se rechazó una estación YouBike con el mismo nombre. El punto representa el complejo.
- **Bolonia:** geometría OSM 41260142, identificada como Virtus Arena/Padiglione 37. La [federación](https://www.supertennis.tv/News/World-Tennis/coppa-davis-bologna-primi-allenamenti) y la [autoridad regional](https://www.regione.emilia-romagna.it/notizie/2025/novembre/sport-la-coppa-davis-torna-in-emilia-romagna-dal-18-al-23-novembre-alla-super-tennis-arena-di-bologna-fiere) acreditan la instalación de las finales 2025. No se reutiliza Unipol Arena, sede de la fase de grupos anterior, ni un pabellón nuevo de 2026.
- **Manchester:** objeto OSM 354135390, estadio AO Arena, con web y código postal coincidentes con el [operador](https://www.ao-arena.com/plan-your-visit/how-to-find-us). No se usa el centroide de la estación ferroviaria.
- **Vilna:** [Go Vilnius](https://www.govilnius.lt/meet-in-vilnius/venue-finder/seb-arena) publica el punto del recinto y la dirección Azuolyno 7; [el operador](https://www.sebarena.lt/) confirma la sede y OSM 199382037 corrobora el complejo de tenis. Se conserva el punto municipal: el complejo también contiene hotel. No se confunde con Arena Vilnius ni con las canchas de Bernardinu.
- **Biel:** [Swiss Tennis](https://www.swisstennis.ch/de/verband/nlz/) sitúa su arena de eventos dentro del centro nacional de Roger-Federer-Allee 1; su [página de la arena](https://www.swisstennis.ch/de/verband/nlz/arena/) confirma la instalación. Se utiliza la geometría del centro de tenis OSM 213588055 como **referencia del complejo**, con 600 m de tolerancia. No se acredita una huella separada exacta de la arena; se rechazan la parada de autobús homónima y Tissot Arena. El plano de acceso consultado tampoco resuelve esa huella, por lo que no se usa para afirmar coordenadas precisas de la cancha.

La evidencia ITF de cada edición 2024/2025 se conserva. Las fuentes geográficas actuales no sustituyen esas acreditaciones históricas. Registro: 324 fuentes verificadas por SHA256, 240 entradas, 167 georreferenciadas; las entradas pueden incluir alias ya existentes.

## Evaluación fija

Se reutilizan las 11.240 predicciones base archivadas. El protocolo se escribió antes del ajuste: ridge 1, RMS calculado en desarrollo 2024, tres diferencias espaciales, 1.000 remuestreos por competición y semilla 20261018. Se mantienen el embargo del modelo base y las exclusiones por solapamiento del dataset. No hay búsqueda de parámetros sobre 2025.

| Comparación 2025 | Desarrollo | Evaluación | Log-Loss base | Log-Loss espacial | Brier base | Brier espacial |
|---|---:|---:|---:|---:|---:|---:|
| Principal | 3.322 | 3.120 | 0,635817 | 0,635835 | 0,223157 | 0,223170 |
| Sin referencias >1 km | 3.179 | 2.956 | 0,632257 | 0,632243 | 0,221961 | 0,221958 |

Cobertura principal: 58,01 % de los 5.378 objetivos exploratorios. ECE10: base 0,022689; espacial 0,022560. La diferencia de Log-Loss espacial menos base es +0,0000178, intervalo descriptivo del 95 % [-0,0001329; +0,0001531]. La sensibilidad obtiene -0,0000139, intervalo [-0,0001128; +0,0000707]. Ambos incluyen cero. Los bloques no capturan toda la dependencia entre jugadores presentes en competiciones distintas.

También se conserva exactamente la muestra del bloque anterior, con 3.108 IDs, variables y base idénticos: Log-Loss base 0,635571; ajuste del bloque 2, 0,635581; ajuste del bloque 3, 0,635585. Sobre los 2.833 IDs originales: base 0,638733; primer ajuste 0,638682; ajuste actual 0,638774. No se acredita mejora; no se comparan pérdidas de muestras distintas como si midieran solamente la calidad del modelo.

2025 es exploratorio y ya fue inspeccionado. No se activa ni se selecciona la corrección. Una nueva variante requiere evaluación futura intacta; el periodo reservado para el candidato ya congelado permanece protegido. No hay ROI sin cuotas contemporáneas ejecutables.

## Entrega y pendientes

Versión: `data/tennis/historical_geography_batch3_20261018/`. Incluye registro, originales y recibos, revisión de coordenadas, dataset, 28 nuevos aptos, particiones y cola. `comparison/` contiene protocolo, coeficientes, predicciones, métricas, calibración en diez intervalos y las dos comparaciones de muestra común.

Scripts preparados para el motor aislado: `build_batch3_geography.py`, `collect_batch3_elevation.py`, `compare_batch3_geography.py`, `audit_batch3_geography.py`; ejecución desde la carpeta principal de datos. La construcción y el experimento rechazan sobrescribir versiones; el recolector reutiliza su recibo. La auditoría comprueba fuentes, identidades, etiquetas, particiones, ausencia de horas imputadas, conservación de datasets y experimentos anteriores, seis modelos base y 12 artefactos congelados. El ajuste y las métricas se reproducen de forma independiente.

Entrega completada: los cuatro scripts coinciden por SHA256 y la auditoría se ejecutó satisfactoriamente desde el motor aislado. Código y pruebas coinciden en 50 archivos con la preparación local. Las 194 pruebas de tenis aprobaron en 37,71 segundos; comprobación general inicial 1.315 aprobadas/95 omitidas/dos avisos en 137,18 segundos, final con los mismos recuentos en 130,60 segundos. Docker no está instalado y su comprobación se omitió. Verificación de sintaxis, integridad final de archivos y revisión de espacios aprobadas.

Quedan 73 entradas y 286 destinos pendientes. Próxima prioridad: Eric Bell National Tennis Centre, Kingston (8); El Gezira, El Cairo (7); Groenkloof, Pretoria (7); Domain Tennis Centre, Hobart (6); Radomskie Centrum Sportu, Radom (6). Son 34 destinos potenciales; su recuperación no garantiza igual número de partidos aptos.

Las ventanas diarias y el descanso exacto siguen separados: no se inventan horas ni se interpreta la distancia entre sedes como itinerario real. Cero consultas a The Odds API/API-Tennis y cero créditos deportivos en este bloque.
