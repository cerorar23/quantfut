# NBA-RUN-058 — partido completo, plantillas actuales y controles

Fecha: 8 de octubre de 2026. F6 sigue abierta; F7 permanece `draft_not_started`. Trabajo de nuevas copias periódicas excluido por petición del usuario. No se habilitaron apuestas, publicación comercial, compras de datos ni mensajes externos.

## Resultado verificado

| Área | Avance | Límite que permanece |
|---|---|---|
| Plantillas oficiales actuales | Doce perfiles NBA 2026-27; 249 jugadores listados; 245 de 247 identidades ESPN corroboradas con equipo y nacimiento | Una lista de pretemporada no acredita contrato activo, convocatoria ni disponibilidad final |
| Contexto de los seis partidos | 34 observaciones de lesiones asociadas al evento; un cruce oficial de IDs NBA/ESPN | Cero disponibilidades finales o roles por partido acreditados |
| Rebotes de partido completo | Referencia nueva incluye prórrogas, sin excluir partidos por su resultado OT | Evaluación retrospectiva condicionada a participación positiva; falta universo previo y probabilidad de no participación |
| Contratos y reglas | Dos páginas actuales de Caliente; revalidación fija también fuente de liquidación y horario | Diez selecciones de equipo; cero props individuales o contratos completos |
| Caducidad entre equipos | Intervalo de desfase medido; transporte rechaza medición ausente o antigua y adelanta conservadoramente el vencimiento remoto | Sin nueva prueba real de envío cercano al vencimiento ni muestra operativa suficiente para p95 |
| Guardado en Windows | Escritura temporal única y completa; reemplazo tolera bloqueos transitorios sin repetir llamadas externas | No acredita recuperación integral ante fallo del equipo |

## Fuentes y procedencia

Se hicieron 35 intentos públicos gratuitos: 23 para contexto, páginas de plantilla, mercados y reglas, y doce perfiles oficiales de equipo. Los cuerpos y recibos originales están conservados con hashes y orden en su propio ledger. Los perfiles NBA respondieron 200 y contienen temporada 2026-27; la comprobación usa equipo, fecha de nacimiento y nombre, con excepción registrada únicamente para sufijos generacionales inequívocos. No se empleó coincidencia difusa. Fuente primaria de ejemplo: [perfil oficial Lakers](https://www.nba.com/team/1610612747/los-angeles-lakers).

Tres identidades adicionales se resolvieron por sufijo con fecha y equipo exactos: William Kyle III, Bobby Portis y Labaron Philon Jr. Cinco IDs NBA nuevos quedaron corroborados respecto al cruce previo. **Maliq Brown y Steve Settle III permanecen sin correspondencia actual segura**; no se inventó un ID ni se sustituyó una fecha.

El partido BOS–CLE se cruzó por equipos, condición local/visitante, tipo de competición y `gameTimeUTC`: NBA `0012600011`, ESPN `401898392`, inicio 23:00 UTC. Su página oficial aún no contenía lista de jugadores activos o inactivos. La hora denominada `gameEt` no se interpretó como UTC. [Partido oficial NBA](https://www.nba.com/game/bos-vs-cle-0012600011).

Las seis respuestas ESPN previas al inicio contienen 34 observaciones de lesión. Estar mencionado en el contexto de un partido no acredita la designación final; una fecha prevista de regreso, el estado genérico Active o la ausencia de una lesión no prueban aptitud. La ruta candidata del reporte NBA 2026-27 respondió 404; eso no demuestra que ninguna otra ruta exista. Una ruta de plantilla Lakers redirigió y se detuvo conforme a la política de captura; los perfiles oficiales alternativos sí fueron recuperados.

Los recibos se obtuvieron hoy. No acreditan recepción histórica previa a partidos de años anteriores; siguen faltando logs o tickets originales del usuario.

## Modelo de rebotes con prórroga

Se conservaron **159.075 etiquetas oficiales de 6.150 partidos**, incluyendo **310 partidos con prórroga**. Las etiquetas usan minutos y rebotes reales de partido completo sin escalarlos a 48 minutos. El cruce NBA está respaldado por la prueba de namespace ya archivada.

La referencia fijada antes de evaluar combina una tasa Gamma–Poisson con una mezcla de minutos observados en las veinte participaciones positivas previas del mismo jugador y temporada. Incluye minutos históricos de prórroga; 1.068 muestras superan 48 minutos. Exige diez antecedentes. Todas las previsiones de una fecha se construyen antes de incorporar sus resultados, excluyendo filtración del mismo día. La familia y el prior heredado de 30 minutos a 0,18 rebotes/minuto quedaron fijados antes de consultar estas métricas.

Se reconstruyeron 104.645 casos con antecedentes suficientes. La evaluación en 2022-23 a 2025-26 contiene **84.015 observaciones de jugadores en 4.343 partidos**, de las cuales **3.842 observaciones pertenecen a partidos con prórroga**. Estas cifras de OT no son número de partidos. Las exclusiones son 27.804 participaciones observadas no positivas y 26.626 casos sin historia suficiente; ninguna exclusión depende de que el partido objetivo termine en OT.

| Medida | Referencia Poisson reciente | Nueva referencia de partido completo |
|---|---:|---:|
| CRPS, menor es mejor | 1,390279 | 1,361001 |
| Pérdida logarítmica | 2,377864 | 2,206793 |
| Error absoluto medio | 1,961465 | 1,944971 |
| Cobertura menos masa del intervalo discreto | −9,13 puntos porcentuales | −2,46 puntos porcentuales |

Diferencia CRPS candidato menos referencia: **−0,029277**, intervalo bootstrap del 95 % por fechas **[−0,032610; −0,026288]**. La diferencia favorece al candidato en las cuatro temporadas. La masa máxima omitida de las distribuciones es aproximadamente 2,03×10⁻²⁰. No se seleccionó otra familia ni se ajustaron parámetros a partir de estas métricas.

Es un resultado **exploratorio**: las temporadas ya habían sido inspeccionadas, y el universo sigue definido por participación positiva observada después del partido. No es confirmación prospectiva, no estima probabilidad de DNP/anulación, ni modela explícitamente duración de prórroga y rotaciones o conservación conjunta de minutos por equipo. No produjo EV, CLV, ROI, picks ni apuestas. Los artefactos anteriores RUN052 se preservan como referencia histórica; la propuesta F7 incorpora la nueva referencia sin promoverla automáticamente.

## Contratos y operación

El evento público de Caliente produjo diez precios de mercados de equipo en esta captura, frente a catorce en la captura anterior. No hubo ninguna prop individual. Las reglas actuales describen liquidación por resultado oficial con tiempo extra salvo excepción en la descripción, participación efectiva para rendimiento del jugador, empate/anulación y condiciones de abandono. No identifican por sí solas el contrato ni las excepciones de una prop concreta, ni su vigencia histórica. [Reglas de basquetbol](https://www.caliente.mx/mas/ayuda/reglas-de-apuestas/basquetbol/), [reglas generales](https://www.caliente.mx/mas/ayuda/reglas-de-apuestas/apuestas-generales/).

La revalidación ahora rechaza cambios en fuente de liquidación o inicio del partido, además de reglas DNP, empate, tipo de pago y los campos anteriores. Los desconocidos sobre salida temprana, reloj del proveedor, aplicabilidad temporal y aceptación efectiva impiden admitir contratos para operar.

Tres consultas de reloj al VPS delimitaron en ese momento `remoto − local` entre **−0,010387 y +2,711583 segundos**. Son una observación fechada, no sincronización certificada ni medición permanentemente vigente. La admisión exige límites recientes y consistentes; convierte el vencimiento al reloj remoto usando el extremo inferior menos un segundo. Las pruebas confirman rechazo antes de SSH o escritura del mensaje cuando falta la medición o está antigua. No se enviaron mensajes para medir estos cambios; los acuses de RUN056 siguen siendo una muestra pequeña.

La comprobación de solo lectura del VPS a las 19:15 UTC confirma el colector de investigación activo, misma imagen y cero reinicios, con 38 recibos acumulados y servicios existentes preservados. La salud sigue `source_degraded`: ESPN funciona y Caliente sigue bloqueado desde el VPS. Los módulos nuevos no se desplegaron en ese colector. No se cambiaron redes, credenciales, servicios de fútbol ni programación de copias.

## Verificación y pendientes

La suite final pasó **435 pruebas NBA sin omisiones**, usando PostgreSQL NBA nuevo y explícito. Los 39 eventos y 19 mensajes de la base fuente se preservaron, y el clúster de pruebas quedó detenido. El arnés general pasó antes y después: **768 pruebas y 10 omisiones preexistentes**.

El primer intento de suite conservó un fallo transitorio de permisos Windows al reemplazar un manifiesto. La corrección usa archivos temporales únicos, cierre y sincronización antes del reemplazo, y hasta seis intentos acotados únicamente de renombrado para errores Windows 5/32. No repite envíos externos; en fallo terminal conserva el destino previo y el temporal completo. Se preservaron también el fallo inicial del cruce NO/NOP, la importación inicial del extractor y dos lanzamientos sin dependencia PostgreSQL que se detuvieron antes de ejecutar pruebas o contactar la base.

La revisión ejecutada por separado reconstruye etiquetas, antecedentes, identidades, recibos, probabilidades de una muestra determinista, CRPS de todos los casos e intervalo por fechas. Es revisión de la misma autoría, no un revisor independiente. Las 57 corridas, 20.328 evidencias y los 134 eventos anteriores deben conservar sus hashes al sellar.

El manifiesto nuevo está preparado localmente. **No tiene nuevo sello externo**: la revisión automática rechazó transmitir su huella a DigiCert sin autorización explícita del contenido/destino. No se hizo la solicitud ni se reintentó. Los dos sellos RFC3161 anteriores RUN057 siguen válidos para sus propios archivos; no cubren este modelo o las nuevas capturas. El sello propuesto transmitiría solamente SHA256 y nonce, no documentos, y probaría existencia nueva, sin retrofechar recepción histórica.

Permanecen abiertos: fuente real de props LATAM con contratos completos; convocatoria/disponibilidad/rol final y dos identidades actuales; universo y elección del modelo congelados antes de confirmación; prueba de caducidad real y muestra operativa suficiente; revisión independiente. Nuevas copias periódicas quedan excluidas de esta ejecución y no se dan por resueltas. G0–G9, alcance y estado comercial no se promueven.

Evidencias principales: `apps/nba/.local/normalized/nba_f6_run58_20261008/`; protocolo/resultado del modelo en `fullgame/`; propuesta `F7_activation_proposal_updated.json`; controles `transport_atomic_protocol.json`; cierre `verification.json` y `checkpoint.json`.
