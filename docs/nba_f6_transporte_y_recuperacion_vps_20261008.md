# NBA-RUN-056 — transporte, recuperación fuera del equipo y preparación F7

La conexión reutilizable de SSH y HTTPS consiguió acuses de Telegram en **0,421309 y 0,484205 segundos** desde el sellado local. Se restauró el respaldo del ledger/outbox de ensayo en PostgreSQL16.15 del VPS, con datos idénticos, roles reconstruidos, permisos e inmutabilidad comprobados y reinicio preservado. La copia permanece fuera del equipo. **F6 sigue pendiente y F7 no se inició**: faltan contratos/cuotas, disponibilidad y rol previos, alcance de prórroga, anclaje independiente y observación continua.

| Control | Resultado acreditado |
| --- | --- |
| Suite NBA final, incluyendo Postgres real | 356 aprobadas; cero omisiones |
| Incremento frente a RUN055 | 26 pruebas |
| Arnés general inicial y final | 768 aprobadas, diez omisiones |
| Alertas técnicas nuevas | Cinco aceptadas, IDs7–11; mismo chat operativo autorizado |
| Duplicados al invocar nuevamente cada ID | Cero envíos adicionales |
| Credenciales copiadas localmente | Ninguna |
| Respaldo restaurado fuera del equipo | 39 eventos y19 mensajes, igualdad exacta |
| Controles de mutación rechazados en el VPS | Seis, incluyendo trabajador y propietario |
| Recuperación tras reinicio del contenedor | Igualdad exacta conservada |
| APIs deportivas/cuotas pagadas y compras nuevas | Cero |
| Cuotas/contratos reales nuevos aceptados | Cero |
| Promoción de gates o despliegue comercial | Ninguno |

## Demora y relojes

El recorrido anterior de RUN055 tardó14,625006s en una observación. Reutilizar solo SSH dio tres acuses de10,753647/10,492760/7,752906s. Los tiempos dentro del programa remoto fueron10,389050/10,198358/7,449882s, por lo que quitar el arranque SSH no resolvió toda la demora.

Un diagnóstico gratuito, sin token ni POST, midió DNS0,016712s y dos peticiones HTTPS públicas de0,261566/0,016085s. Se preparó un transporte que abre y reutiliza una conexión HTTPS con validación de certificado; no cambia las credenciales o servicios de fútbol. Los dos POST técnicos siguientes tuvieron duración remota0,159274/0,166598s y sellado local→acuse local0,421309/0,484205s. Mediana0,452757s y p95 descriptivo0,481060s. El arranque separado de SSH+HTTPS tardó4,312s y se excluye de esas dos mediciones calientes.

Estas muestras no establecen un p95 poblacional ni una comparación causal controlada entre implementaciones. Tampoco miden recepción/cálculo de cuotas, disponibilidad en la casa o recepción en el teléfono. Cada salida tenía un ID sellado y reclamado antes del transporte; caducidad revalidada en ambos equipos y ausencia de reintentos automáticos. Una respuesta incierta inutiliza la sesión. El programa sigue limitado a mensajes de prueba técnica.

Tres ecos de solo lectura acotan relojVPS−relojlocal entre−0,901752 y−0,724567s, bajo el supuesto de relojes estables durante la muestra. El VPS informa NTP sincronizado; no se ajustó ningún reloj. Las métricas de sellado→acuse usan exclusivamente relojes locales y el intento también conserva duración monótona. **No se restan tiempos UTC entre equipos como si estuvieran sincronizados**; falta validar la política operativa de relojes/caducidad cerca del límite.

## Respaldo recuperado y conservado

Se usó exclusivamente el archivo congelado RUN055 del ledger/outbox de ensayo, SHA256`38c454e69985e5de706aefb650b368244e167a15f947f7398cfd46fa5c568036`. El contenedor nuevo del VPS usa imagen fijada por digest, red`none`, sin puertos publicados y límites de memoria/CPU. Los roles NBA se reconstruyen sin contraseñas anteriores; el trabajador de recuperación es`NOLOGIN`, usado mediante cambio de rol para comprobar permisos. Esto no acredita autenticación SCRAM del trabajador en el VPS: esa prueba pertenece al clúster local RUN054.

La restauración usa una sola transacción y detención ante error conforme a la [documentación de PostgreSQL16](https://www.postgresql.org/docs/16/app-pgrestore.html). Después se comparan las siete columnas del ledger y los seis campos de la cola contra la exportación congelada. Se verifican lecturas del trabajador, seis mutaciones rechazadas, igualdad tras los controles e igualdad tras reiniciar. Se elimina únicamente el contenedor propio, verificando antes su nombre, etiqueta e imagen; la lista de servicios de fútbol en ejecución permanece igual.

Copia privada conservada:`/home/qf/nba-isolated/backups/run56-20261008/nba_backup.dump`, con recibo y resultado de recuperación. Los archivos tienen permisos600 y la carpeta700. Se conserva esta copia sin borrados ni rotación automática. **No es un respaldo integral del histórico NBA, de secretos o de las últimas alertas de este ensayo**. Falta programar y verificar copias periódicas, retención y recuperación de todo el alcance necesario para una operación continua. El recibo del VPS propio no es una autoridad independiente de tiempo.

## Captura y datos todavía ausentes

El colector conserva cuerpo original por hash, URL pública fijada, solicitud, recepción propia al completar la respuesta, código HTTP y cabeceras permitidas; comprueba integridad, rechaza redirecciones y separa actualización del proveedor de recepción. Las cuotas candidatas tienen controles de vínculo al cuerpo, jurisdicción, reglas y aplicabilidad, pero no se elevan automáticamente a contratos acreditados.

La respuesta NBA diaria fue403 localmente. Dos consultas nuevas desde el VPS —marcador diario y calendario— también dieron403. Se guardaron los tres cuerpos y sus horas reales; cero eventos deportivos nuevos aceptados. Un fallo no reutiliza una cuota antigua ni convierte el archivo histórico en recepción original. Los logs/tickets anteriores siguen ausentes según la respuesta del usuario y no pueden reconstruirse retrofechando descargas.

Preparación operativa y propuesta F7 actualizadas en`operation_readiness.json` y`F7_activation_proposal_updated.json`. Mantienen el candidato histórico y sus hashes, con estos requisitos concretos:

- Fuente funcional de cuotas de las casas/jurisdicciones LATAM, con identidad completa, versiones, precios, estado y reglas aplicables al contrato.
- Universo previo de jugadores, lesiones, disponibilidad y rol capturados antes del corte; los participantes positivos observados después no definen elegibilidad prospectiva.
- Estadísticas por periodo y modelo con alcance de prórroga compatible. Excluir juegos que tuvieron OT después del resultado no es una política previa válida.
- Anclaje independiente y control comprobado de relojes, además de la muestra completa recepción→cálculo→sellado→envío→acuse.
- Operación NBA aislada con salud, credenciales propias, respaldo periódico y retención verificada, una vez que exista una fuente utilizable.
- Congelar universo, configuración, criterios y exclusiones antes de nuevos resultados. El suelo propuesto60días/300partidos/tres bloques no equivale a aprobación automática.

## Trazabilidad

Se preservan55 corridas,20.038 evidencias y116 eventos anteriores. El primer intento RUN056 se detuvo antes de acciones externas:352 pruebas aprobadas y una falló por acceso denegado de Windows al reemplazar un manifiesto temporal existente. Esa prueba pasó en otra carpeta sin modificar su código; el log y el intento se conservan. La versiónv2, en otra base y carpeta temporal, pasó353 pruebas antes de los primeros tres mensajes. La mejora HTTPS añadió tres pruebas, pasando356 en otra base antes de los dos mensajes restantes.

Protocolos117/118, diagnóstico119, mejora120, capturas121 y relojes122 preceden las respectivas acciones. El checkpoint final123 registra la revisión reproducible; el mismo autor hizo la verificación mediante un script separado, sin revisor independiente. Código utilizado en cada versión se conserva en snapshots: la actualización posterior de la sesión no sustituye sus fuentes anteriores. Los clústeres locales quedaron detenidos y el contenedor de recuperación eliminado.

Artefactos principales:`apps/nba/.local/normalized/nba_f6_run56_v2_20261008` y`nba_f6_run56_keepalive_20261008`; primer intento preservado en`nba_f6_run56_20261008`. GatesG0–G9, cuotas históricas estrictas y alcance de producción conservan su estado anterior. Cota ZenRows2232/3200 intacta.
