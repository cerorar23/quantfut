# API-Tennis: prueba real de acceso y cobertura

Observación del 17-oct-2026, 21:12 UTC. Prueba autorizada por el titular. Seis consultas autenticadas; todas devolvieron HTTP 200 y success=1. La clave se configura únicamente en un archivo local ignorado por Git; no se incluye en los originales ni en este informe.

| Consulta | Resultado |
|---|---:|
| Tipos de competición | 27 |
| Catálogo de torneos | 10.360 entradas, no implica torneos activos ni sedes únicas |
| Partidos 16–17 octubre 2026 | 445 |
| Próximos partidos 18–20 octubre 2026 | 228; 40 ATP y 28 WTA individuales |
| Partidos 17 octubre 2025 | 205 |
| Partidos en vivo al consultar | 5 |

En la muestra reciente hay 20 ATP individuales terminados y 25 WTA individuales terminados: los 45 traen estadísticas, marcadores y punto a punto. Los cinco retiros WTA se contabilizan aparte. En todo el conjunto reciente solo 132 de los 393 terminados traen estadísticas: la cobertura de circuitos inferiores es menor. En la fecha histórica, 11 ATP y siete WTA individuales terminados traen estadísticas. Una fecha no demuestra profundidad histórica completa.

Se observaron estados Finished, Retired, Walk Over, Cancelled y Set 1/2/3; en futuros aparece también el valor textual `1` y vacío. No se debe clasificar cualquier estado desconocido como prepartido. Los 878 registros de las tres consultas de fixtures tienen identificadores de ambos jugadores y no hay IDs de evento duplicados dentro de cada respuesta.

Comprobación de estadísticas de los 45 terminados ATP/WTA: 1138 pares numéricos de puntos ganados/totales revisados; 45 partidos con ambos jugadores y cuentas de saque/resto completas. Incidencias: 0; detalle en quality_checks.json. La presencia del campo no acredita por sí sola exactitud frente a fuente independiente.

Las finales del 18-oct coinciden con los horarios oficiales previamente archivados: Davidovich Fokina/Jodar, 08:30 UTC (event_key 12171959), y Chwalinska/Kartal, 10:30 UTC (12171967). Esto es una concordancia de calendario, no validación global de latencia o inicio real. Las identidades nuevas no se vinculan automáticamente al registro interno.

## Utilidad y límites para el motor

- Calendario, resultados y estadísticas: candidato útil, con recepción UTC y originales verificables. No se alteraron modelos, predicciones congeladas ni el evaluador prospectivo.
- Fatiga: en las respuestas revisadas aparecen event_date y event_time, sin inicio/final reales ni duración. No habilitar descanso en horas ni minutos de carga con estos campos. El punto a punto tampoco mostró marcas temporales en sus objetos examinados.
- Viajes: completar sedes, coordenadas y zona local; país del jugador no es sede ni itinerario. El catálogo devuelve superficie con la grafía `tournament_sourface`, que requiere normalización y comprobación.
- Rentabilidad: resultados son un insumo; siguen haciendo falta predicciones previas selladas, precios disponibles, reglas por casa y resultados futuros. Los datos de 2025 recibidos hoy no prueban disponibilidad histórica previa.
- Operación: aún faltan medir cambios, retrasos de actualización, estabilidad de IDs y límites/consumo del plan. Estas seis respuestas no acreditan coste monetario ni cuota restante. No se consultó The Odds API: cero créditos consumidos de esa cuenta.

## Evidencia local

Originales, manifiesto, hashes SHA-256, parámetros sin clave y resumen: `.local/api_tennis_probe/20261017T211250Z/`. Todos los hashes comprobados: True. Apariciones de la clave en artefactos de prueba: 0. Archivo de configuración `.env.api-tennis.local` ignorado por Git.

Documentación de referencia: https://api-tennis.com/documentation . La integración automática de esta fuente con la captura del motor queda pendiente; esta tarea valida acceso y muestra, sin activar trabajos recurrentes.
