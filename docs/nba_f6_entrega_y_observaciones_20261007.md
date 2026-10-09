# NBA-RUN-053 — ensayos locales de entrega y observación

F6 avanzó con controles de reinicio, caducidad y recepción de versiones de cuotas. Pasaron 291 pruebas NBA, incluidas 26 nuevas; el arnés principal pasó 768 pruebas con diez omisiones. Se revisaron por separado 60 cortes y cinco estados persistidos. Son ensayos sintéticos locales: no se enviaron mensajes externos ni se recuperaron cuotas nuevas. F6 y G6 permanecen pendientes.

La fase F6 del plan maestro incluye alertas de pruebas y disponibilidad observada. La auditoría temporal mencionada en el traspaso RUN-052 es un control transversal; no sustituye la entrega durable en Postgres, el ensayo del canal ni las observaciones de operadores. F7 corresponde a confirmación prospectiva y todavía no comenzó.

Se preservaron las 52 corridas, las 19.873 evidencias y los 109 eventos anteriores. El protocolo se registró como evento 110 antes del ensayo; el checkpoint añade el evento 111. Los archivos usan la fecha local de trabajo 2026-10-07; los registros del ensayo son del 2026-10-08 en UTC. Los fixtures tienen relojes artificiales y se identifican como sintéticos.

El outbox local conserva la reclamación del mensaje antes del transporte. Un reinicio no reenvía estados `sent`, `rejected`, `unknown` o `sending`. Una reclamación interrumpida solo puede pasar de `sending` a `unknown` cuando vence su vigencia; no vuelve a la cola. No se recuperan reclamaciones frescas que podrían pertenecer a otro trabajador. Se verificaron también dos trabajadores concurrentes, fallo de auditoría posterior a reclamar el mensaje y expiración entre reclamación e intento de transporte. Ninguno provocó un envío duplicado en las pruebas.

El intento registra la hora del reloj de ejecución separada del `as_of` solicitado. Se comprueba de nuevo la vigencia antes de invocar el remitente. La respuesta registra su hora y conserva `subscriber_receipt_verified=false`. Los ensayos usan funciones inyectadas en memoria; no construyen un remitente Telegram.

| Ensayo de entrega | Estado conservado | Resultado tras reinicio |
| --- | --- | --- |
| Acuse del remitente simulado | sent | Una llamada; sin reenvío |
| Rechazo simulado 429 | rejected | Una llamada; sin reintento automático |
| Timeout simulado | unknown | Una llamada; sin reintento ciego |
| Interrupción de trabajador | sending; unknown tras vencer | Sin reenvío |
| Caducidad posterior a reclamar | rejected | Cero llamadas al remitente |

Las demoras se evalúan en 0, 15, 30, 60, 120 y 300 segundos para diez fixtures: línea nueva, deterioro de precio, suspensión, error del proveedor, datos caducados, publicación antigua recibida tarde, otro operador, ausencia de captura inicial, duplicado y revisión de reglas. Se utiliza la última recepción del mismo evento/jugador/operador/mercado/periodo/fuente que no exceda el corte. Un error o suspensión sustituye la observación anterior; otra casa no sustituye el contrato original. Se rechazan integridad alterada, versiones contradictorias con idéntico reloj, tiempos sin zona y datos retrospectivos sin recepción original.

En el fixture de cambio de línea recibido a los 60 segundos, los cortes 0/15/30 usan la captura original y los cortes posteriores detectan el contrato distinto. Una actualización del proveedor fechada antes del corte, pero recibida después, tampoco se incorpora anticipadamente. Una única captura original deja de ser utilizable cuando supera el máximo de antigüedad. El resultado `acceptable_observation` significa únicamente que la última captura conocida cumple los controles; no demuestra disponibilidad exacta al corte, continuidad, aceptación de apuesta o llegada al dispositivo.

Dos capturas distintas separadas por 60 segundos producen un intervalo entre observaciones, no una duración exacta de cuota. No se atribuye el cambio al operador antes de observarlo ni se reconstruye el primer momento externo de cambio. La disponibilidad comercial y el liderazgo de un feed siguen sin medición real.

El resumen incluye número de intentos, estados, p50/p95 de duración local y de sellado a acuse, y anomalías de orden temporal. El remitente de éxito simulado produjo un único acuse local, aproximadamente 0,03246 segundos después del sellado. Esa muestra no prueba el objetivo técnico p95 <2 segundos de un canal real. La duración del intento incluye escritura de auditoría; no representa tiempo puro de red. Las pruebas con relojes artificiales antiguos no se incorporan a las latencias de acuse. El acuse de servicio, cuando exista, tampoco acreditará recepción en un dispositivo.

La inspección de configuración registró exclusivamente presencia/ausencia: no hay token ni destino NBA, y tampoco los dos campos del puente autorizado del bot operativo existente. No se copiaron ni registraron valores privados. `psql`, `postgres` y `docker` no están disponibles en PATH; esto no demuestra ausencia de un servidor remoto. No se probó conexión NBA a Postgres ni se modificó la base de fútbol. Los SQLite de los ensayos son evidencia local de investigación; sus transacciones separadas no satisfacen por sí solas F6.1.

Se dejó una propuesta de activación F7 con referencias y hashes del candidato RUN-052. Está en estado `draft_not_started`, sin fecha de inicio. Propone el piso del plan de 300 partidos, 60 días y tres bloques, y criterios de CRPS/calibración sujetos a revisión antes de activar el protocolo definitivo. Hace falta definir el objetivo con prórroga, disponibilidad e identidad previas, universo de exclusiones, captura real con recepción UTC y anclaje externo. La población histórica de participantes positivos en partidos sin OT no constituye una regla prepartido: se conoce después del resultado. No puede iniciarse una validación operativa fingiendo que esa selección estaba disponible antes.

Para cerrar F6 se requieren outbox/ledger NBA durable en Postgres con ensayo real de transacciones y reinicios, configuración privada del canal elegido, acuses medidos y capturas reales del mismo contrato y jurisdicción con reglas versionadas. La disponibilidad, los contratos/recibos históricos, los props LATAM/REB/AST pendientes, OT y contexto conservan sus limitaciones anteriores. No se liquidaron apuestas ni se calcularon beneficios reales. Las puertas G0–G9 no cambiaron; el candidato deportivo sigue en investigación.

El ensayo consumió cero APIs y cero compras. La cota conservadora previa ZenRows 2.232/3.200 y las cuotas históricas anteriores se conservaron sin nuevas consultas. La revisión se realizó con un script separado por el mismo autor, no con un revisor humano independiente. Los artefactos, protocolos, snapshots de código, cinco outboxes y verificaciones están en `apps/nba/.local/normalized/nba_f6_run53_20261007`; el registro central es `docs/nba_plan_fases_auditoria.json`.
