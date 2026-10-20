# Tenis: Open-Meteo gratuito y altitudes verificables

## Alcance confirmado por el usuario

El 17 de octubre de 2026 (México), el titular aclara que este proyecto de tenis no está monetizado. Para este trabajo se usa el endpoint público gratuito de Open-Meteo sin clave; no se requiere Standard ni una nueva suscripción. La documentación anterior sobre el producto de fútbol no determina el alcance de esta investigación de tenis. No se modifican las condiciones de otros proyectos ni el plan de pago de The Odds API y sus 2.000 créditos mensuales reservados para tenis.

La documentación de elevación confirma que `apikey` solo es necesario para el acceso comercial reservado. La consulta pública acepta hasta 100 coordenadas a la vez. Se realizó una solicitud exitosa con los ocho puntos ya revisados, sin credenciales ni consultas deportivas adicionales.

Fuentes: [Elevation API](https://open-meteo.com/en/docs/elevation-api), [documentación meteorológica](https://open-meteo.com/en/docs), [condiciones del acceso gratuito](https://open-meteo.com/en/terms).

## Resultado de la consulta

| Recinto | Elevación estimada, metros |
|---|---:|
| Almaty Arena | 756 |
| LDLC Arena, Décines-Charpieu | 194 |
| Bruselas, ING Arena / Palais 12 | 73 |
| Bruselas, Palais 5 | 83 |
| Shanghai, Qizhong | 20 |
| Wuhan, Optics Valley | 48 |
| Ningbo, Yinzhou | 9 |
| Osaka, Utsubo | 5 |

Son valores del modelo de elevación **Copernicus DEM 2021 GLO-90**, con resolución horizontal de 90 metros. No son cotas medidas de la pista, alturas de edificios ni altitudes de un centro urbano. La resolución de 90 m tampoco representa un error vertical de ±90 m. La incertidumbre de las coordenadas originales se conserva por recinto.

Atribución: **Open-Meteo; Copernicus DEM (ESA)**, [DOI 10.5270/ESA-c5d3d65](https://doi.org/10.5270/ESA-c5d3d65). La atribución de las geometrías OpenStreetMap permanece vigente.

## Integración y trazabilidad

Carpeta `data/tennis/venues_20261017/`:

- `originals/open_meteo_elevation/response.json`: respuesta original exitosa, SHA-256 `4eb5d756a4fcd2eecc8d685fc329b1b6164236ff67a6e3c9022f9c56a66e3f85`.
- `originals/open_meteo_elevation/receipt.json`: parámetros, orden de coordenadas/recintos, recepción UTC, dataset, resolución y alcance.
- `registry_seed_open_meteo_v2.json`: revisión reproducible con 25 fuentes y elevación por campo; conserva los quince enlaces de torneo originales.
- `venues.sqlite`: añade las ocho revisiones sin sobrescribir las versiones previas.
- `calendar_report_v3_open_meteo.json`: los mismos 228 encuentros archivados; 102 resueltos con coordenadas y elevación (44,74 %), incluyendo 102/102 ATP/WTA de la muestra. No se presenta como cobertura de todo el circuito.

La respuesta fue recibida el **18-oct-2026 a las 02:59:53 UTC** (17-oct en México). La revisión del registro es posterior a la recepción. Consultar una decisión previa sigue devolviendo elevación desconocida: no se retrodata conocimiento ni se modifica la semilla original. Los informes v1/v2 siguen conservados. Los valores se incorporaron como metadatos; no modifican las probabilidades del modelo ni prueban un efecto predictivo.

Comprobaciones de integración: hash de respuesta; longitud y orden de valores; igualdad exacta de coordenadas solicitadas con los recintos; elevaciones numéricas finitas; revisión posterior a recepción; integridad de la semilla original; cobertura del calendario idéntica; versiones anteriores con elevación desconocida.

## Qué sigue pendiente

Los **126 encuentros** sin sede y las **48 discrepancias** entre temporada del proveedor y año de la fecha siguen pendientes. Una API de elevación requiere coordenadas previamente identificadas; no acredita la sede ni corrige el año de edición.

Open-Meteo también puede proporcionar pronósticos. Su captura, almacenamiento y conexión al ajuste climático siguen pendientes: esta consulta solo descargó elevación. Debe guardarse la recepción previa a cada decisión y distinguirse de la fecha de emisión del modelo, que no se deduce de `generationtime_ms`. El tiempo observado o reanalizado después de un partido no acredita lo que se pronosticaba antes. La exposición meteorológica en recintos cubiertos requiere tratar el techo y sus datos ausentes.

Validación: 116 pruebas de tenis aprobadas; arnés general con 1.300 aprobadas, 88 omitidas y dos avisos. No hubo cambios de código.

Actualización 18-oct: se cerró la identificación de sedes y revisión de las 48 temporadas; véase [informe de cierre](tenis_sedes_temporadas_completadas_20261018.md). La elevación de los 27 recintos nuevos requiere verificar sus coordenadas.
