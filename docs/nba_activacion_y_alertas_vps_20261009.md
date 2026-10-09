# NBA — activación operativa en VPS, RUN068

Comprobación del 9 de octubre de 2026. La captura pública, el piloto prospectivo y las alertas operativas funcionan en el VPS. Las alertas y el cierre del trabajador ya no dependen de Codex abierto. Investigación activa no equivale a validación científica ni operación con dinero.

| Componente | Estado comprobado | Alcance |
|---|---|---|
| Captura pública | `nba-research-capture-run68-v2`, activo | ESPN NBA: calendario, lesiones y plantillas; cada 15 minutos, lesiones/plantillas cada hora. Recibos originales y diario conservados. |
| Piloto prospectivo | `nba-paper-pilot-run67`, activo, esperando eventos | Los mismos 15 casos sellados, tres partidos del 20 de octubre; observación previa, cierre comparable y evaluación oficial en ventanas prefijadas. |
| Alertas operativas | `nba-operations-run68.service`, activo y habilitado al arrancar el VPS | Canal operativo ya autorizado de fútbol. Un aviso real confirmado por Telegram; conservación del estado y exclusión concurrente comprobadas. |
| Fin del piloto | Supervisor activo | Detiene únicamente `nba-paper-pilot-run67` al completarse, agotarse su plazo o aparecer un bloqueo de validación/reloj. Comprueba la etiqueta de propiedad antes de actuar. |
| Caliente | En cuarentena, sin recuperación acreditada | El HTTP 403 y su cuerpo original siguen disponibles. Se detienen consultas repetitivas inútiles. Su ausencia no contamina la salud de ESPN ni se presenta como cobertura de props mexicanos. |
| Copias periódicas | Desactivadas | No se generan ni eliminan archivos de copia anteriores. Capturar respuestas nuevas y escribir el diario son operaciones del recolector. |
| Confirmación científica | Diseño disponible en VPS; sin abrir | Conserva requisitos de entrada y calendario propuesto noviembre–marzo. Faltan revisión y validación del universo prospectivo; después harán falta observaciones futuras. |
| Liquidación comercial | Preparación disponible, operación desactivada | Plantilla de evidencia por cuenta disponible en el servidor. Cero tickets reales aportados; no se inventan reglas aplicables, disponibilidad ni resultados de apuestas. |

El recolector usa la misma carpeta de datos de RUN057. Se comprobó que el prefijo completo del diario anterior permanece idéntico, que los cuerpos de las fuentes en cuarentena mantienen su hash y que las copias existentes no cambian. El recolector anterior queda detenido y conservado; sólo hay un ejecutor activo sobre ese diario. Los contenedores de fútbol y el estado del piloto conservaron su identidad y contenido, respectivamente.

Las alertas registran una reclamación inmutable antes del envío, con diario verificable y máximo 20 intentos por día UTC. Un envío incierto no se reintenta automáticamente. No se envían picks a clientes. El token y el destino se extraen exclusivamente en el VPS de la configuración autorizada; el servicio sólo recibe esos dos campos en un archivo privado, sin exportarlos a este equipo. La respuesta de Telegram acredita aceptación y destino, no lectura por cada persona.

El primer despliegue detectó una carrera de arranque: `systemd` consideraba activo al proceso antes de que adquiriera su bloqueo. Se revirtió automáticamente y se conservó su informe. La recuperación usa `Type=notify`: el arranque termina después de adquirir el bloqueo y completar el primer ciclo durable. Se comprobó la exclusión real de un segundo proceso y un reinicio posterior sin nuevo mensaje. El aviso confirmado antes de la reversión conserva su reclamación y resultado originales.

Esta ejecución realizó dos GET públicos y un envío operativo confirmado. No consultó cuotas pagadas. El piloto mantiene el máximo original de dos créditos futuros para el cierre; no se amplía ningún presupuesto ni se abre captura pagada recurrente.

Los resultados y la disponibilidad de los tres partidos futuros se recogerán en las ventanas ya fijadas. Si las fuentes fallan o no aportan el dato, se registrará el faltante. El diseño científico y la plantilla por cuenta se copiaron una vez al VPS; eso no inicia F7 confirmatoria, no aprueba G7 y no habilita apuestas reales. La recepción histórica original tampoco puede reconstruirse a partir de una descarga actual.

Evidencia: `apps/nba/.local/normalized/nba_f6_run68_20261009/deployment_result.json` conserva el primer intento y `deployment_result_v2.json` contiene la recuperación validada. `verification.json`, `checkpoint.json` y los informes de pruebas completan el cierre auditado. La preparación previa y los sellos RUN065–067 conservan sus bytes.
