# Segundo bloque de sedes y repetición espacial — 18 de octubre de 2026

Se incorporaron cinco referencias de recinto, sin modificar enlaces históricos de ediciones o partidos. La cobertura mejora, pero la corrección espacial continúa experimental: no hay evidencia clara para activarla en el modelo operativo.

## Cobertura medida

| Indicador | Antes del bloque | Después |
|---|---:|---:|
| Partidos objetivo | 11.240 | 11.240 |
| Con coordenadas de destino | 10.774 | 10.895 |
| Con variables espaciales completas para ambos jugadores | 6.651 | 6.845 |
| Aptos para comparación probabilística | 6.244 | 6.414 |
| Aptos sin referencias de más de 1 km | 5.943 | 6.107 |
| Entradas del registro sin coordenadas | 83 | 78 |
| Partidos con destino pendiente | 466 | 345 |

Los 121 destinos recuperados generan 170 partidos aptos adicionales porque una sede también puede desbloquear la procedencia observada de encuentros posteriores. Los 6.244 aptos anteriores conservan sus variables numéricas. Hay 3.306 partidos de desarrollo 2024, 3.108 exploratorios 2025 y 201 objetivos en cuarentena de frontera. El universo completo mantiene 384 bloques de competición indivisibles.

## Referencias y alcance

| Recinto | Latitud WGS84 | Longitud WGS84 | Tolerancia espacial | Terreno DEM | Destinos recuperados |
|---|---:|---:|---:|---:|---:|
| SDAT Tennis Stadium, Chennai | 13,056551 | 80,2389454 | 500 m | 12 m | 31 |
| Country Time Club, Palermo | 38,18988995 | 13,3191794 | 750 m | 19 m | 31 |
| King Saud University Indoor Arena, Riad | 24,72789230 | 46,6221849 | 500 m | 665 m | 30 |
| Hengqin International Tennis Center, Zhuhai | 22,1281707 | 113,5291769 | 600 m | 1 m | 15 |
| Shenzhen Bay Sports Centre Gymnasium | 22,52084295 | 113,9441016 | 500 m | 24 m | 14 |

Las tolerancias representan incertidumbre del punto de referencia; no son errores instrumentales medidos ni precisión de la pista histórica. Las elevaciones provienen de una sola consulta de cinco puntos a Open-Meteo/Copernicus GLO-90: representan terreno del entorno, especialmente relevante en arenas con plataformas o cubiertas, y no altura topográfica medida de la cancha.

- Chennai: el [enlace de la asociación de Tamil Nadu](https://www.tn-tennis.com/about-us/) identifica el estadio de tenis; se contrasta con el estadio OSM 23186312. Se rechazaron el enlace del estadio de hockey y un homónimo de otra ciudad.
- Palermo: la [dirección del propietario](https://www.countrytimeclub.eu/contatti/) se cruza con el complejo deportivo OSM 262811284, la agrupación de canchas de tenis y Country Discoclub en Viale dell'Olimpo. **Es una inferencia geográfica revisada del complejo**: el polígono no tiene nombre y no se afirma una posición exacta de la pista. Se rechazan el establecimiento costero homónimo y los puntos genéricos de ciudad.
- Riad: la [WTA identifica la arena y enlaza a webook](https://www.wtatennis.com/news/4389831/wta-finals-2025-riyadh-schedule-groups-prize-money-and-everything-you-need-to-know). El lector web mostró en [webook](https://webook.com/en/events/wta-2025) el enlace de mapa con coordenadas; la página del mapa no llegó a cargarse. El punto difiere 208 m del centro de la geometría OSM de la arena cubierta 667480100, dentro de la tolerancia. Se rechaza Al-Awwal Park, el estadio de fútbol cercano.
- Hengqin: el [operador Huafa](https://zhuhai.huafasports.com/en/tennis/) y el objeto OSM 435045112 corroboran el complejo. Se completa explícitamente `Asia/Shanghai`. No se convierten coordenadas GCJ02 en WGS84 por suposición.
- Shenzhen: la [fuente municipal](https://www.sz.gov.cn/szzt2010/szwtt/wtcg/tycg/content/post_11128543.html) confirma el complejo en Binhai Avenue 3001; la geometría 665408865 corresponde al gimnasio cubierto, diferenciada de piscina y estadio de fútbol. La identificación de la edición 2025 conserva la evidencia ITF ya archivada.

Las fuentes históricas de 2024/2025 permanecen intactas; estos contrastes geográficos actuales no sustituyen la prueba de qué edición se jugó en cada sede. Las dos páginas accedidas mediante lector web se identifican como extractos, con su método de recuperación, sin inventar respuesta HTTP exitosa. Las respuestas de desafío y los fallos TLS quedan archivados como intentos, no como evidencia aceptada. El registro valida 309 fuentes con SHA256; hay 162 entradas georreferenciadas de 240, incluidas referencias y alias existentes.

## Comparación con protocolo fijo

Se reutilizan, sin reentrenar, las 11.240 predicciones base del experimento original y sus recibos. El protocolo se guarda antes de ajustar la corrección: ridge 1, escalado RMS exclusivamente en desarrollo 2024, las mismas tres diferencias espaciales, 1.000 remuestreos por bloque con semilla 20261018 y sensibilidad sin referencias de más de 1 km. Se conservan el embargo de 35 días del modelo base y el resguardo por periodos de origen del dataset. No hay búsqueda de parámetros sobre 2025.

| Evaluación 2025 | Entrenamiento | Evaluación | Log-Loss base | Log-Loss espacial | Brier base | Brier espacial |
|---|---:|---:|---:|---:|---:|---:|
| Principal | 3.306 | 3.108 | 0,635571 | 0,635581 | 0,223035 | 0,223044 |
| Sin referencias >1 km | 3.163 | 2.944 | 0,631982 | 0,631955 | 0,221827 | 0,221819 |

La cobertura principal es 3.108/5.378 = 57,79 % de los objetivos exploratorios. ECE de 10 intervalos: base 0,022326, espacial 0,022180. La diferencia de Log-Loss espacial menos base es +0,0000101, con intervalo descriptivo del 95 % [-0,0001250; +0,0001444]. En sensibilidad es -0,0000270, intervalo [-0,0001229; +0,0000637]. Ambos incluyen cero. El remuestreo por competición no captura toda la dependencia entre jugadores que reaparecen en distintos torneos.

Para comparar con el estudio previo se conservan exactamente sus 2.833 partidos de evaluación, etiquetas, predicciones base y variables: Log-Loss base 0,638733; ajuste anterior 0,638682; ajuste con entrenamiento ampliado 0,638764. La ampliación no acredita una mejora en esa muestra común. No debe atribuirse la menor pérdida absoluta de la muestra nueva a una mejora del modelo, porque cambió la composición de partidos.

2025 ya fue inspeccionado y es exploratorio. No se elige una variante ni se activa un modelo con estas cifras. El periodo futuro del candidato previamente congelado no se reutiliza para seleccionar esta corrección. Faltan validación futura intacta y cuotas contemporáneas ejecutables para evaluar rentabilidad.

## Archivos y comprobaciones

Datos versionados en `data/tennis/historical_geography_batch2_20261018/`: registro final, revisión de puntos, recibos y originales, dataset, manifiesto de particiones, 170 nuevos aptos, cola geográfica y auditoría. Subcarpeta `comparison/`: protocolo, predicciones, coeficientes, métricas y diez intervalos de calibración en `calibration_bins.csv`, muestra común original y auditoría.

Scripts entregados al motor aislado: `build_batch2_geography.py`, `audit_batch2_geography.py`, `compare_batch2_geography.py` y `collect_batch2_elevation.py`. Se ejecutan desde la carpeta principal de datos. Los constructores y el experimento rechazan sobrescribir sus versiones publicadas; la auditoría puede reproducirse. El recolector de elevación reutiliza su recibo local.

La auditoría comprueba enlaces, identidades, etiquetas, particiones, coordenadas y elevaciones, conservación de variables anteriores y hashes de fuentes/canónico/CSV. Reproduce ajustes y métricas, conserva estudios previos, verifica los seis modelos base reutilizados y los 12 artefactos congelados. Las 194 pruebas de tenis pasaron. La primera invocación de pruebas no encontró el paquete por la ruta de importación; se corrigió el entorno de ejecución y la suite completa terminó satisfactoriamente. La comprobación general final terminó con 1.315 pruebas aprobadas, 95 omitidas y dos avisos en 126,80 segundos; no se pudo comprobar Docker porque no está instalado. Código y pruebas de tenis coinciden en 50 archivos entre preparación y motor aislado; los cuatro scripts se entregaron y la auditoría final se ejecutó desde el motor aislado.

No se imputaron horas de eliminación, llegada, inicio o fin. Distancia entre torneos observados no equivale al itinerario real, y diferencia de husos no equivale a severidad individual de jet lag. Se consumieron cero créditos de The Odds API y cero consultas a API-Tennis.

## Siguiente trabajo delimitado

Quedan 78 entradas geográficas sin resolver, asociadas a 345 destinos. La siguiente prioridad por cobertura es Taipei Tennis Center (14), SuperTennis Arena de Bolonia (14), AO Arena de Manchester (12), SEB Arena de Vilna (10) y Swiss Tennis Arena de Biel (9): 59 destinos. Mantener tratamiento histórico por edición y revisar la cancha exacta de eventos por equipos. La carga diaria y el descanso exacto siguen separados: las 152 observaciones terminales archivadas no acreditan un límite inferior de finalización suficiente para reconstruir esos relojes.
