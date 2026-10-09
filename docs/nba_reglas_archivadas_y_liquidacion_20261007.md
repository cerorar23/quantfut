# NBA: reglas archivadas y evaluación de liquidación — 7 de octubre de 2026

**Se recuperaron seis capturas históricas verificadas y se añadió Betway México al catálogo.** El evaluador de escenarios supera 38 controles, y la revisión de las 243.132 cuotas mantiene todas como pendientes de liquidación real: faltan tickets, jurisdicción de cuenta y contrato histórico acreditado. El usuario confirmó que no tiene logs originales; no se reconstruyen fechas de recepción por suposición.

## Documentos que ahora tienen historia verificable

| Casa | Capturas reales del archivo web | Resultado |
|---|---|---|
| Caliente México | 23 de octubre de 2025, 16:02:57 UTC | Se recuperó HTML original; la sección de rendimiento del jugador coincide con la captura actual revisada en RUN-045. |
| Betway México | 1 de agosto de 2021; 29 de mayo y 5 de octubre de 2022; 10 de junio de 2023; 14 de abril de 2024 | Cinco HTML originales recuperados. Sus secciones de actuación/comparación de jugadores coinciden con la captura actual. |

Los seis cuerpos coinciden byte por byte con el digest SHA-1 codificado en base32 del índice CDX; se conservan también SHA-256 locales, timestamp del índice y `Memento-Datetime` concordante. No se afirma igualdad de documentos completos ni continuidad de vigencia entre dos capturas. Una captura acredita existencia del texto en una fecha, no el contrato de un ticket ni la recepción del scraper en esa fecha.

Fuentes históricas: [Caliente 2025](https://web.archive.org/web/20251023160257id_/https://www.caliente.mx/mas/ayuda/reglas-de-apuestas/basquetbol/) y [Betway 2024](https://web.archive.org/web/20240414193553id_/https://betway.mx/p/basketball/es-mx/). Los índices capturados contienen las otras cuatro versiones de Betway, con sus URLs completas en el manifiesto local.

Las versiones de Betway declaran actualizaciones de febrero de 2021, diciembre de 2022, marzo de 2024 y octubre de 2025. Son fechas declaradas por el documento; no se sustituyen por intervalos de vigencia probados. Las reglas generales actuales declaran diciembre de 2025 y también requieren revisar su relación con cada ticket.

## Nueva cobertura de reglas mexicanas

Las [reglas oficiales de Betway México](https://betway.mx/p/basketball/es-mx/) explicitan participación del jugador, prórroga de props salvo excepción y push. En simples de dos opciones, el push devuelve la apuesta; no se trata como pérdida. La sección de baloncesto estadounidense excluye prórroga de mitades/cuartos. Betbuilder/SGP tiene un tratamiento conjunto de selecciones anuladas que no se extrapola a cualquier parlay. La fuente también especifica el origen de estadísticas y alternativas ante conflictos.

Se conservan [sus reglas generales](https://betway.mx/p/general-rules/es-mx/) por separado. Sigue sin acreditarse una ventana de corrección de estadísticas, un contrato de bono o un reembolso por lesión temprana para un ticket concreto. El catálogo acumulado contiene cinco perfiles: Caliente MX, Codere MX, Betway MX, Wplay CO y RETAbet PE; los cuatro anteriores permanecen exactamente iguales. Hay ocho documentos de reglas adicionales —seis archivados y dos actuales— y una página oficial de ayuda.

El intento de capturar Codere Argentina fue redirigido a la portada de Codere México. Aunque respondió HTTP200, no aportó reglas argentinas de baloncesto; se conserva en cuarentena y no se amplía cobertura por ese resultado. El índice de Codere México respondió 503; cuatro consultas al API de disponibilidad del archivo web devolvieron 429. No se repitieron esas solicitudes limitadas ni se interpreta el fallo como ausencia de historia.

## Evaluador preparado y límites de aplicación

El auxiliar de investigación recibe identidad de partido/jugador, casa/país, mercado/periodo, lado, línea, importe y cuota. Separa las condiciones de participación, prórroga y empate. Los controles cubren Over/Under, devolución por push/void, participante de menos de un segundo con estadísticas cero, lesión con condición desconocida, estadísticas de otro mercado, identidad discordante, periodo incompleto, correcciones sin resolver, bonos y combinadas no admitidos.

Los resultados positivos son **escenarios sintéticos expresamente etiquetados**, no tickets reales ni un backtest rentable. La aritmética usa decimales y diferencia dinero devuelto de ganancia neta. Si falta una condición relevante, el resultado permanece desconocido. No se presupone que un jugador con `00:00` sea DNP ni que un partido interrumpido permita resolver todos los mercados.

La comprobación de entrada se aplicó a las **243.132 cuotas existentes**: todas carecen de las pruebas necesarias para una liquidación real, y los identificadores de sus casas no se unen al catálogo latinoamericano por inferencia. Los booleanos introducidos en una plantilla tampoco autentican un contrato. Resultado: cero liquidaciones reales verificadas, cero ROI calculado y `actionable=False`. El código permanece como auxiliar local de investigación; no se integró en publicación comercial ni se relajaron los controles de producción.

## Dónde conseguir tickets o logs

La [ayuda oficial de Caliente](https://www.caliente.mx/mas/ayuda/deportes/donde-puedo-ver-la-lista-de-mis-apuestas/) sitúa las apuestas en “Apuestas Abiertas”, con filtros de intervalo y estado para consultar también resueltas o anuladas. Se puede conservar el boleto/exportación original y pedir copias del historial al soporte oficial si no aparece. No se necesitan contraseñas en la plantilla.

Para una revisión, el ticket debe identificar casa/entidad, país/estado de cuenta, ID y hora aceptada con zona, partido/jugador, texto exacto del mercado, periodo, lado, línea, cuota, importe/divisa y tipo de apuesta. Se preparó una plantilla JSON con campos vacíos; no contiene apuestas inventadas. El archivo y su SHA-256 deben conservarse junto a las pruebas de reglas aplicables.

Un historial obtenido hoy puede documentar la aceptación de una apuesta por la casa; no demuestra cuándo el sistema recibió una cuota o lesión antes del partido. Los logs del colector solo se pueden recuperar de registros de aplicación/servidor, backups, versiones históricas de almacenamiento o artefactos originales del productor con procedencia verificable. Un repo público no contiene necesariamente el historial privado de una cuenta.

Se inventariaron 4.978 archivos con nombres relacionados con recibos/tickets en seis raíces locales acotadas. La mayoría son recibos de descargas actuales; también se identifican auxiliares y fixtures sintéticos. Es una búsqueda por nombre, no prueba de que no existan archivos con otros nombres o backups externos. El usuario confirmó que no dispone de logs originales.

El auxiliar de recibos nuevos guarda bytes exactos, SHA-256, URL y la hora UTC actual del registro, con escrituras exclusivas. No admite un timestamp histórico proporcionado por el llamador. Su prueba usa bytes sintéticos. Reloj, autenticidad de origen e integridad externa siguen requiriendo corroboración; por sí solo no convierte un archivo antiguo en recepción histórica acreditada. La precisión del reloj de Windows puede compartir un tick entre llamadas contiguas: el control temporal usa un corte anterior inequívoco.

## Validación y presupuesto

Se verificaron las 19.165 evidencias, 45 corridas y 94 eventos previos. Permanecen 243.132 pares estrictos, 27.151 candidatos separados, 4.628 PDFs médicos, 6.149 selecciones retrospectivas T−60 y 6.150 rotaciones regulares. Los modelos, gates y producción NBA siguen iguales; se preservan los cambios concurrentes.

El arnés pasó 764 pruebas antes y 764 después, con nueve omisiones. El evaluador canónico v3 pasó 38 controles. Se conservan el fallo inicial de dependencias del extractor, el intento restringido de red y el primer fixture temporal ambiguo como evidencia; no son resultados adoptados. Auto revisión local, sin revisor independiente ni anclaje externo propio.

Hubo 28 intentos GET planificados: once restringidos fallidos, once con acceso de red y seis replays. Cero llamadas/créditos nuevos de The Odds API o ZenRows y cero compras. Odds API mantiene 500 créditos locales agotados; los 720 adicionales propuestos no están autorizados. Riesgo conservador ZenRows: 1.982/3.200, sin nueva lectura de cuenta.

## Archivos y pendientes

- Versiones, comparaciones y catálogo: `apps/nba/.local/normalized/nba_pending46_contracts_20261007/`.
- Plantilla: `apps/nba/.local/normalized/nba_pending46_contracts_20261007/ticket_intake_template.json`.
- Evaluación canónica y controles: `apps/nba/.local/normalized/nba_pending46_settlement_v3_20261007/`.
- Auxiliar: `apps/nba/.local/reports/nba_pending46_settlement_engine_20261007.py`.
- Fuentes archivadas: `apps/nba/.local/raw/nba_pending46_replays_20261007/`.
- Verificación y checkpoint: `apps/nba/.local/normalized/nba_pending46_validation_20261007/`.

Quedan tickets/contratos reales por aportar, recepción histórica no reconstruible sin originales, otras casas/países, cuotas LATAM, historia amplia de rebotes/asistencias y cortes, relojes de candidatos y pendientes médicos. La recuperación de versiones y la preparación del evaluador están completadas; la liquidación histórica real continúa pendiente de esas pruebas.
