# Tenis: sedes históricas y dataset espacial 2024–2025

Se ejecutó la primera reconstrucción retrospectiva autorizada. El conjunto contiene 11.240 partidos objetivo y permite iniciar una comparación exploratoria con 2.982 partidos con variables espaciales completas para ambos jugadores. No es una validación histórica de información disponible en tiempo real, ni demuestra todavía una mejora del motor.

## Cobertura comprobada

| Elemento | Resultado |
|---|---:|
| Partidos del historial 2023–2025 utilizados para buscar antecedentes | 38.936 |
| Partidos objetivo, temporadas 2024–2025 | 11.240 |
| Bloques de edición objetivo, incluyendo eliminatorias por equipos | 472 |
| Ediciones enlazadas con evidencia de su propio año | 187 |
| Ediciones con coordenadas verificadas del recinto | 160 |
| Ediciones con sede identificada y coordenadas pendientes | 27 |
| Ediciones sin enlace acreditado | 285 |
| De las anteriores, eventos por equipos o con múltiples sedes | 233 |
| Partidos con sede identificada | 8.742 |
| Partidos con variables espaciales completas para ambos jugadores, antes de filtros finales | 3.155 |
| Partidos aptos tras exigir finalización estándar y separación temporal | 2.982 (26,53% del total objetivo) |
| Recintos físicos distintos enlazados | 95 |
| Recintos con coordenadas y elevación de terreno | 78 |
| Fuentes utilizadas con archivo, fecha real de recepción y SHA-256 | 122 |

La cobertura no es uniforme. No debe interpretarse la muestra completa como representativa de todos los circuitos, superficies o niveles sin presentar sus desgloses. Un encuentro excluido por falta de sede permanece en el archivo principal y en los denominadores.

## Evidencia y cambios históricos

Se archivaron los directorios oficiales ATP 2024 y 2025, notas de edición de WTA e información oficial de los Juegos de París. Las páginas de los directorios y los campos de sede de las notas quedan referenciados en el registro. Se revisaron visualmente las notas cuyo texto no podía extraerse de manera fiable.

Las correcciones de edición incluyen Dallas 2025 en Ford Center, Hangzhou 2024 en lugar de Zhuhai, Belgrado 2024, Atenas 2025 y Bruselas 2025. París conserva Accor Arena en 2024 y Paris La Défense Arena en 2025. Canadá distingue Montreal/Toronto por año y circuito; no se completa una edición faltante por analogía. Las sedes históricas de Lyon y Mallorca no heredan las de 2026.

Un punto del mismo recinto físico puede reutilizarse cuando una fuente independiente de 2024 o 2025 identifica ese recinto. No se trasladan enlaces de edición, fechas ni condiciones de 2026. Las fuentes consultadas el 18-oct-2026 mantienen esa recepción real.

Las coordenadas proceden de objetos específicos de OpenStreetMap revisados por identidad y localidad, mediante Nominatim/Photon. Se rechazaron aparcamientos, paradas, homónimos y localidades equivocadas. Los puntos representan el recinto o complejo, no una pista concreta. El margen espacial documentado es una tolerancia conservadora, no un error topográfico medido. Las alturas proceden del terreno de Copernicus GLO-90 mediante Open-Meteo; no son mediciones del suelo de una pista interior.

## Variables y límites temporales

Cada jugador conserva su última edición observada anterior. No se salta una edición desconocida para encontrar un antecedente más cómodo. Challenger y clasificación permanecen en la búsqueda de antecedentes aunque todavía no tengan sedes enlazadas. Una sede del cuadro principal no acredita automáticamente la de su clasificación.

Se calculan kilómetros geodésicos, elevación de destino menos origen y diferencia UTC de destino menos origen. Esta última compara ambas zonas IANA en los mismos instantes e incluye el horario de verano. Si varía dentro del periodo de referencia, se conserva un rango y falta el valor escalar. No equivale a una medición de jet lag ni determina la dirección real de vuelo.

Los periodos del archivo no acreditan fechas individuales de eliminación, debut o llegada. La primera versión aplica una guarda conservadora de siete días por periodo registrado: los posibles solapamientos se excluyen. Los instantes utilizados para consultar los husos son sondas computacionales, nunca horarios imputados de partidos. No hay descanso exacto, cierre de participación en dobles, itinerario, transporte ni penalización fisiológica inventados.

Las variables de entrada son constantes dentro de una edición para cada jugador. No se introducen desplazamientos locales entre sus rondas. Una distancia entre recintos de torneos sigue siendo una aproximación espacial, no kilómetros realmente recorridos.

## Partición por ediciones completas

| Partición | Todos los partidos | Aptos ATP | Aptos WTA |
|---|---:|---:|---:|
| Desarrollo 2024 | 5.661 | 898 | 528 |
| Exploración 2025 | 5.378 | 1.021 | 535 |
| Cuarentena de frontera anual | 201 | 0 | 0 |

Cada edición conserva un único bloque y partición, incluso cuando sus filas contienen distintos periodos. Las ediciones 2025 ancladas en diciembre de 2024 y los bloques tardíos de diciembre se conservan en cuarentena para esta primera comparación. Esta es una regla de separación operativa, no una fecha de cierre reconstruida. Los IDs exactos quedan en `split_manifest.json`.

2025 ya fue inspeccionado y se etiqueta como exploratorio. Los modelos congelados y su protocolo futuro permanecen intactos. Este conjunto tampoco transforma 2024 en un nuevo holdout independiente.

## Archivos y reproducción

Datos locales: `data/tennis/historical_venues_20261018/`.

- `registry.json`: recintos, enlaces de edición, fuentes, objetos geográficos aceptados y trazabilidad.
- `matches_spatial.parquet`: todos los partidos objetivo, incluidos valores desconocidos y motivos.
- `eligible_spatial_cohort.parquet`: los 2.982 candidatos aptos para la comparación espacial.
- `edition_catalog.json`, `pending_editions.json`: cobertura por edición y motivos pendientes.
- `split_manifest.json`: particiones con IDs exactos.
- `dataset_report.json`: conteos, hashes y límites de interpretación.
- `originals/`: respuestas originales, documentos y recibos. Las respuestas fallidas no constituyen evidencia aceptada.

Código entregado en la carpeta aislada `apps/tennis`: `tennis_engine/historical_dataset.py`, `scripts/prepare_historical_dataset.py`, `scripts/build_historical_registry.py`, configuración revisada y once pruebas específicas. El preparador se ejecuta sin red con `--registry`, `--canonical`, `--raw-root` y `--output`; el constructor de enlaces utiliza `--config` y los originales archivados, desde la raíz del proyecto de datos.

## Siguiente evaluación

Comparar Base y Base + Espaciales en la intersección de sus predicciones válidas, que todavía no se ha calculado. Los 2.982 partidos son candidatos con datos, no una muestra común ya puntuada. Ajustar escalas, imputaciones, regularización y coeficientes exclusivamente en entrenamiento; mantener bloques completos al avanzar por meses. Desglosar ATP/WTA, cobertura y resultados excepcionales.

Reportar Log-Loss, Brier, curva de calibración y ECE de diez intervalos, con incertidumbre que respete la dependencia por edición/jugador. No usar 2025 para elegir y luego presentar la misma muestra como prueba final. La variante horaria experimental sigue pendiente de días individuales acreditados: no se activa con fechas de semana. ROI y CLV siguen pendientes de cuotas históricas utilizables y reglas de liquidación.

Esta fase no ajustó modelos, no modificó probabilidades y no consumió créditos de The Odds API ni consultas de API-Tennis. La captura nueva de elevación fue una única solicitud pública de Open-Meteo para 72 puntos.

Verificación: 165 pruebas del motor de tenis aprobadas en la carpeta entregada, incluidas once nuevas sobre antecedentes desconocidos, solapamientos, separación por edición, husos, integridad de fuentes y ausencia de fechas de 2026. La auditoría real volvió a validar las 122 fuentes y los doce hashes de modelos congelados. Los conteos y archivos de entrega están sellados en `delivery_audit.json`.
