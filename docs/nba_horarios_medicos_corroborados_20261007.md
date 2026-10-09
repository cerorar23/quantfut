# NBA: horarios médicos corroborados — 7 de octubre de 2026

**Se añadieron 20 selecciones médicas retrospectivas: 6.149 de 6.150 partidos regulares del censo 2021–22 a 2025–26.** Queda Celtics–Knicks del 25 de octubre de 2023 (`0022300065`), cuyo contexto no figura en los diez PDFs oficiales revisados de ese día. La ausencia permanece desconocida; no acredita equipos sanos, reportes enviados ni disponibilidad de jugadores.

| Cobertura | Antes | NBA-RUN-044 |
|---|---:|---:|
| Selecciones médicas retrospectivas T−60 | 6.129 | 6.149 |
| Partidos sin selección médica | 21 | 1 |
| Reportes médicos con dos parsers e identidad | 4.625 | 4.628 |
| Filas médicas | 555.536 | 555,703 |
| Boxscores y rotaciones regulares | 6.150/6.150 | 6.150/6.150 |
| Pares de cuotas con cronología completa | 233.430 | 233.430 |

## Criterio de las veinte selecciones nuevas

Las veinte páginas de [Basketball Reference](https://www.basketball-reference.com/boxscores/202210260DEN.html) se capturaron mediante ZenRows, con recibo actual y hash. Se exige título con fecha y local/visitante exactos, metadatos con una única hora y concordancia literal con el reloj del PDF oficial de NBA. El marcador ET procede del PDF; la metadata capturada de Basketball Reference corrobora la hora y AM/PM, pero no declara por sí misma la zona horaria.

Se conservan ambos relojes: ESPN está entre 12 y 50 minutos más tarde. No se atribuye esa diferencia definitivamente a un retraso ni se afirma la hora del salto inicial. El corte conservador se calcula **60 minutos antes del más temprano de ambos relojes**. La versión elegida debe tener encabezado anterior o igual al corte, fecha, matchup, equipo y reloj literal concordantes. Los 6.129 registros anteriores se preservan exactamente; los 20 nuevos conservan la discrepancia y su prueba independiente.

Hay 6,056 selecciones con ambos equipos enviados, 93 con algún equipo ausente y 0 con un `NOT YET SUBMITTED` explícito. Existencia de un reporte y disponibilidad nominal completa son medidas diferentes. Los datos siguen siendo investigación retrospectiva: `original_historical_receipt_known=False`, `pregame_availability_verified=False`, `actionable=False`.

## Partido que no figura

Se inspeccionó texto de todos los folios de diez versiones de [los reportes oficiales de NBA](https://ak-static.cms.nba.com/referee/injury/Injury-Report_2023-10-25_05PM.pdf). Ninguna contiene el matchup BOS@NYK, Boston Celtics o New York Knicks. Se renderizaron e inspeccionaron las cuatro páginas del reporte con encabezado 17:30 ET. Tres versiones adicionales —08:30, 12:30 y 15:30— se recuperaron con tres solicitudes directas separadas por un segundo, sin coste pagado. Se aceptaron con el parser por coordenadas y el parser independiente de mrees002: 167 filas y 155 filas nominales, todas con ID NBA. Se preservan las diferencias literales de motivos y las restricciones históricas.

No se inventa una fila vacía para cerrar el 6.150/6.150 ni se usa un boxscore posterior para inferir disponibilidad previa. Queda acreditada la ausencia en estas diez versiones, no en todas las publicaciones posibles.

## Presupuesto y validación

ZenRows procesó 22 tareas: 20 páginas corroboradas y dos consultas fallidas al JSON CDN oficial. Coste confirmado **200 créditos**; las dos fallidas costaron cero y no aportaron relojes. Riesgo acumulado conservador **1.982/3.200**. La última lectura de cuenta conservada observa 1.674/5.000 utilizados; su fecha es 2026-10-07 21:58 UTC y no representa un saldo en tiempo real. No hubo compras ni cambios de plan. Odds API conserva 500 créditos locales agotados y cero llamadas nuevas; los 720 adicionales propuestos siguen sin autorización.

Se verificaron las 18.952 evidencias, 43 corridas y 92 eventos anteriores, la preservación exacta de los datos y seis controles de fecha/equipos/reloj/corte/ausencia. El arnés pasó 753 pruebas antes y 764 después. Producción NBA, modelos y gates permanecen iguales; se preserva el trabajo concurrente de web/fútbol. La versión inicial del auxiliar atribuía a Basketball Reference una declaración de zona que no estaba en la metadata capturada: se corrigió en v2, que es la versión canónica. Los fallos auxiliares y la versión inicial se conservan como evidencia de trabajo, no como resultados adoptados. Auto revisión local; sin revisor independiente ni anclaje externo.

## Datos y siguientes pendientes

- Conjunto médico: `apps/nba/.local/normalized/nba_pending44_medical_v2_20261007/reports.jsonl.gz`.
- Selección canónica: `apps/nba/.local/normalized/nba_pending44_medical_v2_20261007/retrospective_T60_selection.json`.
- Pruebas de ausencia: `apps/nba/.local/normalized/nba_pending44_absence_20261007/proofs.json`.
- Auditoría: `apps/nba/.local/normalized/nba_pending44_validation_20261007/`.

Restan ese contexto médico ausente, versiones intradía adicionales, props históricos de rebotes/asistencias y cortes T−60/T−15, relojes separados de los 27.151 candidatos aislados, recepción histórica original y reglas de liquidación. No se amplió el censo a toda la historia NBA ni se habilitaron picks por esta recuperación.
