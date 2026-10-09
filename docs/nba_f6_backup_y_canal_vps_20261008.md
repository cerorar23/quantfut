# NBA-RUN-055 — restauración y prueba real del canal del VPS

Se restauró un backup Postgres y Telegram aceptó un mensaje técnico NBA en el chat de alertas de fútbol del VPS, según la autorización directa del usuario. El acuse confirmó `message_id=6` y coincidencia con el destino configurado. El contenido fue la prueba operativa NBA, sin pick ni recomendación. No se copiaron credenciales al equipo local ni se desplegó un servicio permanente.

Pasaron 330 pruebas NBA, incluidas 21 nuevas, y 768 pruebas generales con diez omisiones. La cola bloqueó la segunda invocación del mensaje ya enviado. La base fuente quedó idéntica a RUN-054 y el servidor de ensayo terminó detenido. F6/G6 permanecen pendientes de latencia suficiente, observaciones de cuotas/contratos y del resto de controles operativos; F7 no comenzó.

El usuario indicó que las credenciales están en el VPS y que se usen las de fútbol. Se resolvió el alias SSH existente `quantfut` y se comprobó únicamente la presencia de `TG_BOT_TOKEN` y `TG_ALERT_CHAT` en `/home/qf/quantfut/.env`. El programa remoto lee esos dos campos y envía al destino existente. Los valores no se retornan, registran o almacenan localmente. No se modificó el `.env`, la base de fútbol, el servicio de fútbol o su programación.

Se utilizó `pg_dump -Fc` sobre `nba_delivery_run54` y `pg_restore --single-transaction --exit-on-error` en una base nueva, `nba_delivery_restore_run55_v2`. Antes de ejecutar tests, las 39 entradas del ledger y los 19 mensajes coincidían exactamente con la fuente y con las exportaciones RUN-054; se verificaron sus hashes y cadena. Los mecanismos corresponden a las herramientas oficiales [pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html) y [pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html). No se deshabilitaron los triggers de la fuente ni se sobrescribió otra base.

La restauración se probó en el mismo clúster local con roles ya existentes. El backup de una base no incluye los roles globales y sus credenciales; no se ha probado reconstrucción integral en otro servidor. Tampoco se configuraron backups programados, retención remota o recuperación ante pérdida del equipo. El archivo de backup incluye el esquema y los mensajes técnicos de ensayo; se conserva localmente sin credenciales.

Las pruebas NBA usan la base restaurada y vuelven a comprobar restricciones, deduplicación, concurrencia, rollback y estados inciertos. La fuente permaneció con sus 39 eventos/19 mensajes; la base restaurada terminó con 75 eventos/36 mensajes después de los tests y la notificación real. Se añadió un lector de métricas que exige un ledger completo y válido, excluye tiempos de acuse incoherentes, conserva acuses ausentes como desconocidos y distingue duración local de recepción en el dispositivo. Hay pruebas de hashes alterados, ledger parcial, duración inválida y ausencia de acuse.

El primer protocolo, evento 114, preservó una restauración correcta y 329 pruebas NBA, pero el intento remoto quedó `unknown`. Un diagnóstico sin HTTP confirmó que el VPS usa Python 3.10.12 y fallaba al importar `datetime.UTC`, antes de leer las credenciales o construir una petición. Se conservan el código congelado, resultados, estado incierto y diagnóstico original. Se cambió únicamente la compatibilidad del programa remoto a `timezone.utc`, se verificó su ejecución de solo lectura y se añadió una prueba para ese entorno. El protocolo canónico v2 se fijó en el evento 115 antes de repetir el ensayo en otra base restaurada. No hubo un reintento ciego ni dos POST de envío: el primer programa falló en el import y la versión compatible realizó un único `sendMessage`.

El mensaje canónico fue sellado y reclamado en la cola local antes del comando SSH. El VPS revalidó su caducidad antes del POST. La respuesta se filtró a campos de resultado y comprobó el destino; no se imprimen URL con token, contenidos del entorno o errores que puedan contenerlos. Telegram devuelve un objeto de mensaje cuando acepta el envío, conforme a su [API oficial](https://core.telegram.org/bots/api#sendmessage). Este acuse no acredita recepción o lectura en el dispositivo.

| Medición del ensayo canónico | Resultado |
| --- | --- |
| Mensajes técnicos aceptados por Telegram | 1 |
| ID del mensaje aceptado | 6 |
| Destino coincide con el chat autorizado | Sí |
| Reenvío al volver a invocar el mismo ID | Bloqueado |
| Duración local del intento, incluyendo SSH | 14,360 segundos |
| Sellado local a recepción del acuse de servicio | 14,625006 segundos |
| Acuse de recepción en dispositivo | Desconocido |
| Errores de orden temporal en este ensayo | 0 |

El transporte se midió desde el equipo local, pasando por SSH y el VPS. No se aisló el tiempo exclusivo de Telegram. Una observación no establece un p95 operativo; este recorrido excede el objetivo técnico propuesto de dos segundos. Los percentiles numéricos de una muestra no se presentan como cumplimiento del objetivo. El lector genérico conserva `real_channel_latency_demonstrated=false`; el acuse real se acredita separadamente con el evento del envío y la respuesta verificada. Los resultados simulados de tests se mantienen separados de esa observación.

Se conservaron las 54 corridas, las 19.962 evidencias y los 113 eventos anteriores. Los protocolos 114/115 y el checkpoint 116 añaden trazabilidad. La revisión la realizó el mismo autor mediante un script separado; no hay revisor humano independiente ni promoción de gates. Los artefactos canónicos están en `apps/nba/.local/normalized/nba_f6_run55_v2_20261008`; el primer intento permanece en `nba_f6_run55_20261008`.

El siguiente paso es preparar una entrega NBA aislada desde el VPS que reduzca el coste del recorrido SSH y medir una muestra suficiente de acuses. También hacen falta capturas reales de contratos con identidad, reglas, revisiones y tiempos de recepción, además del protocolo prospectivo y disponibilidad/prórroga adecuados antes de F7. Reutilizar el bot operativo no activa publicación comercial ni sustituye esas evidencias.

Cero APIs de datos deportivas/cuotas pagadas y cero compras. Hubo un envío real autorizado a Telegram; las consultas de documentación y diagnósticos SSH se conservan como acciones técnicas. La cota previa ZenRows 2.232/3.200 permanece intacta.
