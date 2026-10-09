# NBA: continuación auditable de históricos — 2026-10-05

Esta ejecución amplía las fuentes locales y sus conciliaciones. **La data todavía no está completa y no se promovió ningún modelo ni pick.** Los resultados son de investigación retrospectiva, separados del fútbol.

## Resultado por componente

| Componente | Resultado verificado de esta ejecución | Pendiente / límite |
|---|---|---|
| Boxscores regulares | 3 adicionales; 6,055 de 6,150 en el censo de cinco temporadas (98.46%) | 95 partidos |
| Pretemporada | 13 adicionales de los 71 pendientes de 2025-26 | 58 boxscores; no es un censo de todas las pretemporadas históricas |
| Dataset estadístico | 515 filas nuevas; 159,603 filas finales | Las 159,088 filas anteriores se conservaron sin cambios |
| Rotaciones cronológicas | 5,161 partidos / 217,334 tramos con cinco jugadores | 891 partidos en cuarentena entre los 6,052 regulares de la base usada; los 3 nuevos regulares aún no forman parte de este lote |
| Lesiones | 486 PDFs oficiales / 43,924 registros, de los que 36,300 son nominales | 330 fechas no capturadas con éxito del universo de 816 fechas regulares; un corte diario, no todas las versiones intradía |
| Enlace de lesiones | 43,675 filas con partido NBA; 36,063 filas con jugador NBA; 14,569 con horario contrastado | 237 filas nominales / 13 nombres sin ID único; 82 discrepancias del reloj impreso; originales preservados |
| Lesiones a T−60 | 1,213 regulares 2025-26 con reporte etiquetado antes del corte; 974 con ambos equipos declarados como enviados | El horario proviene del calendario ESPN. Se desconoce la recepción histórica real; no es una certificación operativa point-in-time |
| Props históricos | 20 partidos / 40 snapshots / 2,961 pares Over/Under (5,922 precios), rebotes | Solo dos cortes por partido y un mercado; no es el histórico completo de props |
| Coste | 420 créditos The Odds API, límite local 500; estadísticas/PDF/PBP sin créditos de cuotas | No hubo nuevas ejecuciones Apify ni recargas; la cuota de la cuenta es compartida con fútbol |

## Boxscores: descarga y aceptación son distintas

Se capturaron resúmenes públicos completos de ESPN para 166 de los 169 candidatos, junto con 80 calendarios diarios. Tres partidos de pretemporada no tuvieron un cruce único por fecha y equipos. Los resúmenes se cruzaron con el Flashscore y los calendarios NBA ya conservados.

Solo se aceptaron partidos con identidad canónica única, pertenencia al mismo encuentro, P/R/A concordantes, participación explícita, minutos compatibles y conciliación estricta de los dos equipos. La tabla ESPN muestra minutos enteros: **no se fabricaron segundos añadiendo `:00`**. Los segundos de Flashscore siguen siendo una reconstrucción condicionada al redondeo decimal declarado; no se capturó el reloj MM:SS original de esa fuente.

Cuando existía un reloj NBA válido se exigió concordancia individual exacta. Las diferencias de uno o dos segundos, cambios de P/R/A y jugadores ambiguos siguen rechazados. Para los nuevos partidos se registraron las correcciones respaldadas por calendario sin sobrescribir las referencias históricas previas. Los DNP explícitos observados se conservan; la lista de DNP no certifica una plantilla completa ni lesiones conocidas antes del encuentro.

La recuperación final de este lote es `apps/nba/.local/normalized/remaining_espn_flashscore_20261005/`. Su SHA256 de dataset es `41c5a4f82d3638138a6a4d9b5bb7fb21033eecbae5e3fa07de99dc074d67ef68`.

Se descubrieron enlaces oficiales para algunas identidades pendientes, pero el primer intento de obtener un perfil NBA devolvió HTTP403. Se conservó la respuesta y se detuvo ese lote. Los enlaces de búsqueda permanecen como candidatos, sin usarlos para forzar la aceptación de jugadores. Los 153 pendientes están enumerados en `recovery.json`, con errores de primera validación; un partido puede tener más de un problema.

## Rotaciones: intervalos reales del PBP, con incertidumbre explícita

Se procesaron los archivos V3 2021–2025 del commit previamente fijado de `shufinskiy/nba_data`, sin descargar nuevamente el histórico. Se reconstruyeron sustituciones en orden de fuente y se probaron cinco titulares por equipo en cada período mediante su primera intervención en cancha o su primera salida anterior a una entrada. No se trasladó automáticamente el quinteto del cuarto anterior.

Los nombres de sustitución se vinculan solo a IDs observados en el PBP o nombres canónicos del mismo boxscore. Se rechazan candidatos múltiples, actores fuera de cancha, sustituciones contradictorias, relojes desordenados y marcadores finales discrepantes. Los IDs de equipo en rebotes de equipo no se confundieron con jugadores.

Se comprobaron continuidad por equipo/período, cinco jugadores distintos, tiempo reglamentario y prórrogas, y minutos por jugador. El presupuesto de cuantización es de un segundo por **intervalo continuo del propio jugador dentro del período**, no por cada cambio de quinteto causado por compañeros. No se escalaron los relojes para hacerlos cuadrar.

La versión final es `chronological_stints_v4_20261005`. Las versiones previas v1/v2/v3 conservan diagnósticos y resultados exploratorios; no son la versión final. Entre los 891 rechazos: 390 etiquetas de entrada ambiguas/no observadas, 414 etiquetas de salida discrepantes, 78 aperturas de período sin cinco titulares demostrados, 4 marcadores discrepantes, 3 conciliaciones de minutos fallidas y 2 contradicciones de cancha/sustitución.

Estos tramos se infieren retrospectivamente del PBP completo. No son seguimiento físico exacto ni información disponible antes del partido.

## Reportes médicos: publicación, recepción y desconocidos

La captura predefinió una consulta por fecha regular: archivo antiguo `_01PM` con cabecera 13:30 ET y, desde el cambio de formato de diciembre de 2025, `_01_00PM` con cabecera 13:00 ET. El timestamp aceptado procede de la cabecera, convertido desde `America/New_York`, no del nombre del archivo.

Se recibieron 486 PDFs válidos y después un HTTP403 para 2023-10-24. Se conservó el cuerpo y hash de esa respuesta y se detuvieron las solicitudes; no se usaron proxies, cuadrículas de horas ni reintentos para sortearla. Las fechas más antiguas siguen pendientes. El recibo fue durante esta ejecución en 2026, y **no se reconstruye como si se hubiese recibido en 2023–2026 antes de apostar**.

El parser inicial separó 198 documentos por motivos de lesión cortados entre páginas. Una revisión visual confirmó el formato: última fila nominal de una página, primer fragmento de la siguiente con solo texto en la columna de motivo. El adaptador de investigación une únicamente ese caso, conserva ambos textos y números de página, y rechaza fragmentos huérfanos o con nombre/estado nuevo. No se modificó el parser de producción.

La comprobación con un segundo motor PDF (`pypdf`) verificó los 486 documentos: cabeceras, páginas, nombres en la página original, conteos de estados en su columna, equipos `NOT YET SUBMITTED` y 272 continuaciones. La columna es importante: la palabra `Available` puede aparecer también dentro del motivo.

El enlace canónico usa fecha, matchup, equipo y nombre completo único; no infiere disponibilidad por ausencia del jugador. El horario solo pudo contrastarse con el archivo local ESPN2025-26. Los 974 partidos con ambos reportes enviados a T−60 siguen siendo una reconstrucción retrospectiva de etiquetas, no prueba de recepción ni de actualización intradía. Jugador ausente, ID ambiguo y equipo no enviado significan **desconocido**, nunca `Available`.

La versión final enlazada es `injury_daily_joined_remaining_v2_20261005`. El lote anterior de parseo v1 y el enlace inicial incompleto se conservan como diagnósticos. La fuente oficial aporta disponibilidad, incluidas asignaciones G League; los 36,300 registros nominales no equivalen a 36,300 lesiones distintas.

## Cuotas: lote acotado y controles temporales

Se eligieron los primeros 20 regulares aceptados de 2025-26 por fecha/ID con cruce único entre calendario NBA y ESPN. Se solicitaron `player_rebounds`, región US, cortes T−60 y T−15 respecto del calendario ESPN. La selección y límite de 500 créditos quedaron registrados antes de solicitar cuotas. Se usó el límite conservador anunciado mientras seguía pendiente la respuesta a la pregunta opcional de presupuesto.

Coste observado: 20 consultas históricas de descubrimiento de evento a un crédito y 40 consultas de mercado a diez créditos = **420**. Se sumaron las cabeceras de estas solicitudes; no se atribuyó a NBA la variación total de una cuenta compartida. La última cabecera mostró 19,194 créditos restantes, como lectura puntual, no garantía de saldo actual.

Se conservaron 60 originales y se reprodujeron los 40 snapshots. Se rechazaron 88 combinaciones casa/mercado por actualización posterior al timestamp envolvente y 73 entidades sin nombre canónico único en el mismo partido. Las 161 son entidades rechazadas, no 161 partidos ni necesariamente 161 jugadores distintos.

Los 2,961 pares aceptados corresponden a ocho operadores y 232 jugadores canónicos, incluidos diferentes líneas y cortes; no son 2,961 apuestas independientes. Se verificaron pares Over/Under únicos, precios decimales, líneas enteras/medias, ID/evento/localía y secuencia temporal. Dos snapshots mostraron cambios del inicio programado del proveedor; se conservaron las dos versiones y el corte debía preceder todos los horarios comparados.

La identidad usa boxscores posteriores exclusivamente como referencia nominal. No se incorpora su resultado ni pertenencia a variables predictivas previas. Siguen sin verificarse las reglas particulares de DNP, prórroga, anulaciones y liquidación. **No se calculó ROI realizado ni se envió ninguna señal.** La resolución histórica del proveedor es de aproximadamente cinco minutos, no un registro de alta frecuencia recibido en su momento. [Documentación oficial de The Odds API](https://the-odds-api.com/liveapi/guides/v4/#get-historical-event-odds).

La versión final es `historical_rebounds_remaining_v2_20261005`.

## Auditoría y siguiente trabajo

Se preservaron y verificaron las 152 evidencias anteriores; los 39 archivos NBA congelados y modelo/configuración permanecieron sin cambios. El arnés completo aprobó 609 pruebas antes y después, con una advertencia; Docker no estaba disponible. La verificación de este lote añade 19 controles de corrupción/temporalidad, barrido completo de invariantes de rotaciones, seis reproducciones del PBP raw —una por temporada y una de prórroga—, todos los pares de cuotas y todos los PDFs mediante segundo motor. Es auto-revisión con hashes locales, sin revisor independiente ni anclaje externo.

Los originales y scripts se fijan en manifests nuevos, con snapshots de los scripts. Registro de ejecución: **NBA-RUN-033**, conservando G0–G9 pendientes. No se modificó fútbol, no se entrenó el modelo y no se publicaron picks/avisos.

El siguiente trabajo se concentra en:

1. Resolver 95 regulares y 58 pretemporadas por identidad, relojes originales y referencias verificables. Los conflictos de estadística/reloj deben corroborarse mediante una fuente independiente; descargar otra copia de la misma fuente no los resuelve.
2. Completar 330 fechas médicas mediante acceso normal autorizado o archivo independiente con PDFs originales verificables; ampliar cortes intradía y resolver los 13 nombres pendientes. Mantener separados timestamp de publicación y recibo.
3. Auditar los 891 rechazos de rotaciones y procesar los 3 regulares recién recuperados cuando exista cobertura PBP validada.
4. Definir el siguiente presupuesto de props; cubrir puntos/asistencias y más temporadas, verificar reglas de liquidación y congelar protocolo de validación temporal antes de cualquier backtest o promoción.

No se da por completada una fase por haber descargado candidatos: cuenta únicamente la cobertura conciliada y verificable.
