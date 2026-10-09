# NBA-RUN-067: seguimiento en VPS

El piloto se ejecuta en el VPS con los mismos 15 casos y sellos originales.
La captura funciona con Windows y Codex apagados. Se retiró el ejecutor local;
su comando rechaza el diario cedido para evitar una segunda consulta de cierre.

## Pruebas reales

- Tres páginas NBA respondieron HTTP200 desde el VPS, con ID/equipos/hora exactos.
- Primer ciclo sin tareas futuras debidas: cero consultas de pago.
- Segundo ejecutor bloqueado antes de consultar.
- Reinicio con estado idéntico; siete servicios previos conservaron sus IDs.
- NTP sincronizado; retrocesos/cambios bruscos del reloj detienen el trabajador.
- Archivos y recibos verificados; rutas Windows interpretadas en Linux sin
  reescribir los documentos sellados.

Servicio `nba-paper-pilot-run67`, carpeta
`/home/qf/nba-isolated/paper-pilot/run67-v3-20261008`. Red propia, sin puertos,
archivos de sólo lectura, recursos limitados y diario persistente. Se usó la
clave ya existente en el VPS y se verificó la misma cuenta; no se devolvió
localmente ni se modificó fútbol. La [política de reinicio de Docker](https://docs.docker.com/engine/containers/start-containers-automatically/)
recupera el proceso; las reclamaciones persistentes impiden repetir consultas.
El estado terminal bloquea nueva captura. El observador detiene únicamente
este contenedor al completar/agotar el plazo y conserva sus datos.

## Calendario y límites

Partidos del 20/10/2026 a las 13:00, 17:00 y 19:30 de Ciudad de México.
Revisión NBA en los dos minutos previos; resultados en ventanas +4/+6/+12/+24h.
Plazo final: 22/10 a las 12:00 UTC. Sólo las dos entradas Sportsbet originales
pueden consumir **dos créditos totales** para un cierre del mismo contrato.
Tres consultas deportivas nuevas, públicas y gratuitas; cero créditos actuales.
Sin apuestas, publicaciones, nuevas copias periódicas ni reintentos.

La automatización del chat ahora sólo observa el VPS y recupera evidencia
nueva. Su aviso necesita Codex local; la captura del servidor funciona sin él.
Una caída del VPS o bloqueo de la fuente puede causar faltantes: se registran
y nunca se reconstruye retroactivamente una recepción perdida.

## Pendientes por alcance

| Alcance | Estado y condición de cierre |
|---|---|
| Enlace, ejecución, reinicio, exclusión y presupuesto del piloto | Resueltos y probados. |
| Disponibilidad previa, cierre y resultados | Esperan los partidos; recogida y evaluación preparadas. `Active` y ausencia de estado siguen desconocidos; distinta línea no es CLV comparable. |
| Diseño científico | Candidato/configuración/criterios/calendario propuesto congelados; revisión, evidencia F6 y presupuesto previos a activación. |
| Resultado científico | Requiere muestra prospectiva nueva. Tres partidos no la sustituyen. |
| Liquidación comercial | Necesita cuenta/jurisdicción, ticket aceptado y versión contractual aplicable; una regla pública no acredita ese contrato. |
| Recepción histórica original | No conservada por el usuario. Descargar hoy no acredita cuándo recibió el sistema los datos anteriores. |
| Copias periódicas nuevas | Excluidas por el usuario. |

`confirmation_design.json` prepara rebotes fullgame con prórroga, candidato
Gamma-Poisson causal y baseline Poisson reciente. Ventana propuesta 1/11/2026–
31/03/2027, tres bloques y lectura 2/04/2027: efecto mínimo 0,05 CRPS, alfa
unilateral 0,025, potencia objetivo 80%, mínimo 112 días NBA/300 partidos.
Bootstrap por bloques de días; calibración con tolerancia cinco puntos
porcentuales frente a la masa real del intervalo discreto. La potencia es
una estimación de planificación, sin garantía futura. F7 confirmatoria no se
activa y G7 no se promueve por preparar este diseño.

`account_evidence_template.json` especifica datos obtenibles del historial,
exportación y confirmaciones de una cuenta. Está vacía; no es evidencia real.
No necesita contraseñas ni acceso completo. No se contactó con operadores.

Se conservan dos intentos fallidos (referencia de imagen/rutas Windows), ambos
anteriores a consultas de cuotas. El tercero pasó. Artefactos:
`apps/nba/.local/normalized/nba_f6_run67_20261008/`. Diario y salud vivos quedan
fuera de hashes fijos; sólo se registran instantáneas y resultados cerrados.
