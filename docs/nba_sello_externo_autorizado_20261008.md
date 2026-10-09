# NBA-RUN-059 — sello externo autorizado

El usuario autorizó expresamente el envío de la huella del manifiesto preparado en RUN058. DigiCert emitió una respuesta RFC3161 con estado Granted y hora firmada **8 de octubre de 2026, 19:24:17 UTC**. Se transmitieron únicamente la huella SHA256 y un nonce; no se enviaron documentos ni datos de jugadores. Se hizo una solicitud de sello y una descarga del certificado intermedio, sin reintentos.

Manifiesto original, preservado sin cambios: `apps/nba/.local/normalized/nba_f6_run58_20261008/closure_manifest.json`.

SHA256: `d2bc63fcf6a0bbcf130a2116c4688f2f4fe80f6afc4017a199449b0291ffa57e`.

La verificación con OpenSSL confirmó la firma y cadena frente al conjunto de autoridades de confianza existente, la huella de los bytes exactos del manifiesto y el nonce de la solicitud. Una copia alterada del manifiesto y una solicitud con otro nonce fueron rechazadas. No se realizaron nuevas comprobaciones OCSP/CRL de revocación.

El sello acredita que ese manifiesto existía a más tardar en la hora firmada, bajo la confianza en la autoridad. El manifiesto relaciona hashes de capturas públicas nuevas, contexto oficial, código congelado y resultados retrospectivos de la referencia de rebotes con prórroga. Esos archivos se volvieron a verificar contra sus hashes. La prueba no acredita recepción original histórica, exactitud del proveedor ni una predicción previa a los partidos del conjunto retrospectivo. Tampoco sella el checkpoint posterior ni todo el registro de auditoría.

La prueba y los controles están en `apps/nba/.local/normalized/nba_f6_run59_20261008/timestamp_proof/` y `negative_controls.json`. Se conserva íntegra la evidencia RUN058 donde figuraba la solicitud bloqueada: el resultado autorizado posterior queda registrado por separado, sin reescribir el pasado.

No se modificaron modelos, servicios, credenciales o programación de copias. Cero llamadas nuevas a APIs deportivas pagadas, mensajes, apuestas o copias periódicas. F6 continúa abierta y F7 no se inicia: siguen pendientes contratos completos de props, disponibilidad/rol y universo previo, criterios finales y validación operativa suficiente.

El arnés general antes y después pasó 768 pruebas con diez omisiones preexistentes. No se repitió la suite NBA completa: los módulos y modelos no cambiaron respecto de las 435 pruebas de RUN058; aquí se ejecutaron las verificaciones criptográficas reales. La revisión separada fue realizada por la misma autoría, sin revisor independiente. Las 58 corridas, 20.535 evidencias y los 145 eventos anteriores se preservan; protocolo 146 y checkpoint 147 registran esta autorización y prueba.
