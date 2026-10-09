# NBA: props históricos, recepción y reglas para Latinoamérica — 7 de octubre de 2026

**Se recuperaron 9.702 pares adicionales de cuotas de puntos en 145 partidos. El conjunto validado pasa de 233.430 a 243.132 pares.** También se archivaron cinco documentos oficiales en español para cuatro casas de México, Colombia y Perú. La recepción histórica original y la aplicabilidad contractual siguen sin prueba; esta recuperación no habilita picks ni resultados de rentabilidad.

## Cobertura recuperada

| Mercado | Pares anteriores | NBA-RUN-045 |
|---|---:|---:|
| Puntos de jugador | 230.277 | 239.979 |
| Rebotes de jugador | 2.961 | 2.961 |
| Asistencias de jugador | 192 | 192 |
| Total | 233.430 | 243.132 |

Un par contiene Over y Under de la misma casa, jugador, mercado y línea en un snapshot. No equivale a un partido adicional ni a un ticket. Los 27.151 candidatos multimerkado anteriores siguen separados y no están sumados en este total. Los nuevos snapshots tienen horizontes variables; no completan automáticamente cortes T−60/T−15 ni toda la historia de la NBA.

Los 145 eventos proceden del archivo público [NBA-Propositions-Forecasting-App](https://github.com/KamranSHussain/NBA-Propositions-Forecasting-App/tree/a95be8924f3c4fe08b44dcfd940269610ca49501), ya capturado. Antes quedaron rechazados por IDs ausentes o discordantes en el mapa del archivo. Se exige una coincidencia única de fecha y equipos local/visitante con el calendario corroborado NBA/ESPN, más IDs y fecha del boxscore canónico. Por ejemplo, CHI@MIA del 14 de diciembre de 2023 se une a `0022300320`; se conserva la referencia errónea previa `0022300337` y su rechazo, sin modificar el archivo original. Quedan 21 eventos sin resolución.

La revisión independiente volvió a comprobar cada precio Over/Under, línea, jugador, evento, hash del archivo y relojes de casa/mercado anteriores al snapshot, con vecinos ordenados y snapshot anterior a ambos horarios de inicio. En 35 filas se revalidaron alias oficiales para el mismo ID NBA. El boxscore posterior sirve para corroborar identidad, no como información disponible previamente. Los 233.430 pares anteriores se preservan exactamente y no hay claves duplicadas.

Se fijaron además [m4nr44j/nba-betting](https://github.com/m4nr44j/nba-betting/tree/2d831947b8d6f50cc209ae0dce0af6d7b2a769e4) y [mostgood1/NBA-Betting](https://github.com/mostgood1/NBA-Betting/tree/73892a6daba2a9a67d4baf8691a106a2f67a9ca6), con 14 blobs verificados. El árbol revisado del primero no contiene los archivos históricos que anuncia su README; su auxiliar de descarga requiere The Odds API pagada y no se ejecutó. El segundo aporta 78 tarjetas de recomendaciones de tres fechas de 2026, sin acreditar ambos lados y relojes separados de casa/mercado/vecinos. No añaden pares al conjunto estricto ni se adoptan sus probabilidades o beneficios calculados.

## Reglas por casa y país

México tiene prioridad según la indicación del usuario. Se conserva cada fuente, URL final, fecha de captura y hash; los PDFs se extraen completos y se inspeccionan páginas renderizadas. No se presume jurisdicción por el idioma español ni se trasladan reglas de estados de EE. UU.

| Casa / país | Fuente primaria capturada | Contenido corroborado / límites |
|---|---|---|
| Caliente / México | [Básquetbol](https://www.caliente.mx/mas/ayuda/reglas-de-apuestas/basquetbol/) y [generales](https://www.caliente.mx/mas/ayuda/reglas-de-apuestas/apuestas-generales/) | Participación real del jugador; resultado oficial; prórroga por defecto, incluida segunda mitad salvo excepción. Abandono y reprogramación tienen condiciones. La regla general toma el resultado oficial inicial e ignora cambios posteriores salvo excepción deportiva. No se acredita una ventana específica de corrección de estadísticas ni push de props enteros. |
| Codere / México | [Reglas México](https://condiciones.apuestas.codere.es/Mexico/reglas_deporte.html) | Prórroga con exclusiones por modalidad, periodos completos y aplazamiento. Reglas específicas de DNP y push de props no validadas. El país procede de la sección México, no del dominio .es. |
| Wplay / Colombia | [Términos, octubre de 2020](https://www.wplay.co/mas/wp-content/uploads/sites/5/2020/10/D-TEC-054_TyC_23102020PDF.pdf), páginas físicas 1, 49–50, 52 | Segunda mitad excluye prórroga; ganador y hándicap requieren revisar el texto del mercado. Suspensión y cambios de fecha/estadio tienen condiciones de anulación. No se valida una regla de DNP de props NBA. |
| RETAbet / Perú | [Normativa, noviembre de 2024](https://cdn.retabet.es/peru/es/OfficialDocuments/Peru-normativa.pdf), páginas físicas 1, 21, 78–79 | Juego completo incluye prórroga salvo excepción; último cuarto/segunda mitad la excluyen salvo excepción. No participar anula pronósticos específicos del jugador. Catálogo de puntos, rebotes, asistencias y PRA. Push entero y correcciones de estadísticas quedan sin acreditar. |

La fecha impresa identifica una versión documental; no demuestra por sí sola su intervalo de vigencia histórica ni que fuera el contrato de un ticket. Todas las versiones tienen `effective_interval_verified=False`. Los 11 identificadores de casas del conjunto de cuotas no coinciden con estas cuatro casas; tampoco hay país/estado de cuenta acreditado. **Contratos históricos aplicables comprobados: cero.** No se calcula win/loss/push/void automáticamente.

Winpot respondió 403, La Bolita falló en conexión y bet365 respondió 403; idioma español por sí solo tampoco acreditaría su alcance mexicano. Sus fallos quedan archivados y no se adoptan como reglas. Los paquetes estadounidenses se conservan únicamente como referencias fuera del alcance. El folio 47 de RETAbet corresponde a eSports y no se usa para NBA. La cobertura aún no abarca todos los países latinoamericanos de habla española.

## Recepción original

Se auditaron los 243.132 pares y los 4.628 reportes médicos canónicos. Todos contienen recibos locales del 6–7 de octubre de 2026: las cuotas se recibieron después de sus partidos y los PDFs después de sus encabezados históricos. El timestamp del proveedor acredita el reloj que declara el snapshot; no acredita cuándo el sistema lo recibió originalmente ni su disponibilidad para una decisión previa.

En estos conjuntos no se encontró ninguna prueba de recepción histórica original. No se afirma que no existan backups externos: el usuario no aportó una ubicación de logs/tickets originales. Para cerrar el pendiente se necesita un registro original vinculado al SHA-256 del payload, timestamp del colector con zona/precisión antes del corte y pruebas fechadas de integridad/retención. El esquema de evidencias y los controles están guardados; un fixture positivo sintético verifica la estructura del control y nunca se une a datos reales. Incluso una estructura válida exige revisión de autenticidad.

La liquidación requiere además casa/entidad y jurisdicción de cuenta, texto exacto del mercado, periodo, línea y hora del ticket, junto con la versión oficial y su vigencia acreditada. Participación, prórroga, empate entero, abandono, correcciones y condiciones de bono deben resolverse con ese contrato. Descargar hoy una regla o una cuota antigua no sustituye esas pruebas.

## Validación y presupuesto

Se preservaron las 19.062 evidencias, 44 corridas y 93 eventos anteriores; los 4.628 reportes médicos, 6.149 selecciones T−60 y 6.150 rotaciones regulares permanecen iguales. El contexto BOS@NYK del 25 de octubre de 2023 sigue ausente en las diez versiones de PDF revisadas. Se superaron 21 controles de identidad/relojes/precios, recepción y jurisdicción, incluidos dos fixtures positivos identificados como sintéticos. El arnés pasó **764 pruebas antes y 764 después**, con nueve omisiones en ambas ejecuciones. Auto revisión local; sin revisor independiente ni anclaje externo.

Hubo 31 intentos GET directos de fuentes públicas y cero llamadas o créditos pagados nuevos. The Odds API mantiene 500 créditos locales agotados; los 720 adicionales propuestos no están autorizados. ZenRows mantiene el riesgo conservador 1.982/3.200; última observación de cuenta 1.674/5.000 utilizada, del 7 de octubre a las 21:58 UTC, sin nueva consulta ni saldo en tiempo real. No se compraron servicios. Producción NBA, modelo y gates permanecen iguales; se conserva el trabajo concurrente.

## Artefactos y pendientes

- Pares nuevos y conjunto acumulado: `apps/nba/.local/normalized/nba_pending45_props_20261007/`.
- Catálogo, auditoría de recepción y pruebas requeridas: `apps/nba/.local/normalized/nba_pending45_contracts_20261007/`.
- Fuentes oficiales y recibos: `apps/nba/.local/raw/nba_pending45_20261007/latam_rules/`.
- Verificación y checkpoint: `apps/nba/.local/normalized/nba_pending45_validation_20261007/`.

Restan historia amplia de rebotes/asistencias y cortes, relojes completos de candidatos, cotizaciones de las casas latinoamericanas elegidas, recepción original acreditada y vigencia contractual por ticket, otros países/casas, versiones médicas intradía y el contexto médico ausente. El alcance de esta corrida está completado y sellado; esos faltantes siguen registrados como pendientes reales.
