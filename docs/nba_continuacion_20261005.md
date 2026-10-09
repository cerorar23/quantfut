# NBA: continuación auditada de F2–F6 — 5 de octubre de 2026

Se implementaron componentes y se ejecutaron capturas, diagnósticos y pruebas
locales. El modelo sigue en investigación: no se publicaron picks, no se
apostó y ninguna puerta G0–G9 fue aprobada por este incremento.

## Estado comprobado

| Fase | Resultado de esta ejecución | Condición que sigue pendiente |
|---|---|---|
| F2: identidades y contratos | 596 identidades ESPN→NBA verificadas y equipos concordantes; esquema de cuotas y reglas estricto | Diez identidades sin resolver; operadores, reglas y props actuales utilizables |
| F3: captura y tiempos | Respuestas públicas conservadas con SHA256 y recepción UTC; calendario separado por competición | Estado médico por partido y publicación original verificados |
| F4: minutos | 436 escenarios condicionales de arranque unidos a equipo actual; detector de cambio de equipo; proyección acotada a 240 minutos para escenarios explícitos | Rol, entrenador, participación y redistribución por lesión validados |
| F5: calibración | Replay de 8,264 observaciones comprobado contra resultados y distribuciones selladas; PIT y masa discreta | Confirmación prospectiva, tolerancias y revisión independiente |
| F6: avisos | Outbox NBA, prueba local, deduplicación, expiración, manejo de fallo ambiguo y enlace al bot/chat de fútbol | Credenciales activas disponibles localmente, envío real y latencia hasta suscriptores |

La cobertura se refiere a los insumos recibidos, no al universo completo de
partidos, jugadores o mercados. NBA.com ofreció 619 jugadores; ESPN, 606.
Los cuatro conflictos de fecha de nacimiento y los seis nombres sin coincidencia
exacta permanecen separados. El reporte identifica 23 IDs de la página NBA
sin cruce ESPN verificado. Los rookies sin historial suficiente se abstienen.

Se descargaron 165 fichas públicas NBA adicionales: 51,340,337 bytes, sin
fallos en esa captura. Las referencias históricas de identidad nunca se usan
para inferir el equipo actual. La recepción de hoy tampoco se retrofecha para
simular conocimiento previo de temporadas pasadas.

El calendario recibido identifica cinco partidos de pretemporada del 5 de
octubre; la fecha UTC de uno puede ser 6 de octubre. Los IDs ESPN de partido
y equipo conservan su namespace. El modelo de arranque evalúa temporada regular
y no traslada automáticamente sus minutos a la pretemporada.

## Qué significa el diagnóstico estadístico

| Distribución | Cobertura observada del intervalo central nominal 80% | Masa discreta esperada del intervalo | Diferencia observada menos esperada, IC 95% por partido |
|---|---:|---:|---:|
| Candidato de arranque | 87.9356% | 88.5199% | −0.5843 puntos porcentuales [−1.2808, +0.1703] |
| Media móvil + Poisson | 78.5697% | 88.7992% | −10.2295 puntos porcentuales [−11.0933, −9.3269] |

Un intervalo de conteos enteros puede contener más masa que el 80% nominal.
Por eso 87.94% de cobertura no significa 87.94% de acierto en apuestas, ni
demuestra por sí solo una distribución demasiado ancha. El candidato queda
más cerca de su masa esperada en este diagnóstico. El PIT y la fiabilidad
por líneas contienen información adicional; ninguna métrica aislada aprueba
el modelo. No se ajustaron parámetros ni se eligieron mercados por este resultado.

Se comprobaron resultados de cada jugador/partido y reproducción de CRPS,
NLL y minutos del replay original. El bootstrap usa 500 remuestreos por
partido, semilla 20261005; no resuelve toda la dependencia entre fechas y
jugadores. Las temporadas ya habían sido inspeccionadas: son evidencia
exploratoria, condicionada a jugadores que participaron, sin ventaja comercial
ni riesgo de DNP acreditados.

## Disponibilidad y precios: abstenciones deliberadas

El listado de lesiones ESPN recibido contiene 81 entradas en 26 equipos:
15 Out y 66 Day-To-Day. Los IDs se recuperan únicamente de enlaces de atleta
no ambiguos. La fecha declarada de una lesión y el timestamp del feed no se
tratan como publicación médica del partido. No aparecer en el listado no
equivale a estar disponible. La API interna solo acepta como disponibilidad
verificada un registro con partido, identidad, estado, publicación, recepción,
frescura y fuente comprobables; futuras, caducadas o contradictorias se abstienen.

Los dos enlaces probados para el informe oficial 2026–27 devolvieron 404.
Esto documenta esas consultas; no demuestra que la NBA carezca de informes
ni permite sustituirlos por noticias antiguas.

La página pública ESPN del partido Memphis–Atlanta ofreció «Game Props / Team
Total Points», no props individuales en esa captura. El resumen también tiene
líneas del partido, pero faltan las reglas y tiempos necesarios para contratos
accionables. La muestra se rechazó; cero props actuales quedaron validadas.
No se generaliza esa ausencia a todos los partidos o proveedores.

Se investigó una alternativa gratuita: [PropLine](https://prop-line.com/)
declara 1,000 solicitudes diarias y props NBA en su plan gratuito. Requiere
clave; no se creó cuenta, contrató plan ni verificó su cobertura con llamadas
autenticadas. Su [documentación de tiempos](https://prop-line.com/docs) distingue
observación del proveedor y publicación de la casa; la última puede faltar.
Es una candidata a prueba, no una fuente ya aceptada.

## Bot compartido, pipeline NBA separado

El usuario autorizó usar el bot de fútbol y el mismo chat de alertas. El
enlace privado NBA solo referencia la configuración; no duplica el token ni
modifica los valores de fútbol. La cola, el ledger y los mensajes siguen en NBA.
Las credenciales activas no están en el entorno ni en los archivos locales
comprobados; una plantilla de ejemplo nunca se toma como configuración operativa.

La prueba local produjo un mensaje identificado como «PRUEBA TÉCNICA NBA —
sin pick ni recomendación de apuesta». No se hizo una llamada real a Telegram.
El adaptador utiliza [sendMessage de Telegram](https://core.telegram.org/bots/api#sendmessage).
Un timeout ambiguo queda sin repetición automática: no se promete entrega
exactamente una vez. Un proceso que cae tras reclamar el mensaje deja estado
`sending` para revisión; no lo reenvía a ciegas. Una confirmación API no prueba
que el usuario haya visto el mensaje o tomado una cuota.

Para una prueba real: disponer del `TG_BOT_TOKEN` y `TG_ALERT_CHAT` activos en
el entorno/ruta autorizados o configurar localmente las variables NBA, y ejecutar
`python -m nba telegram-test --as-of ISO_UTC --send` desde el entorno NBA.
No pegar claves en el chat. El comando sigue limitado a la prueba técnica;
la publicación comercial no está habilitada.

El filtro de picks sella el pronóstico antes de seleccionarlo y rechaza el
modelo no promovido, disponibilidad/rol desconocidos, contrato incompleto y
puertas pendientes. El validador también contempla push, DNP, abandono y
prórroga; la revalidación rechaza cambios de línea, reglas o cuota mínima.
El modelo de rebotes no se presenta como modelo ya validado de puntos,
asistencias, cuartos o mitades.

## Evidencia, reproducción y siguiente condición de avance

Los reportes están en `apps/nba/.local/reports/`; el registro JSON del plan
añade evidencia y ejecuciones, conserva las anteriores y mantiene las puertas
pendientes. El ledger local sigue sin anclaje externo. La copia de código de
este incremento es independiente de la congelación anterior.

Validación final: **79 pruebas NBA y 606 pruebas de fútbol aprobadas**. El
chequeo Docker se omitió porque no está disponible en este entorno. Las pruebas
incluyen identidad/DOB, conservación de minutos, fugas temporales, verdad del
replay, contratos caducados, cambio de línea y precio, sellado, deduplicación,
reclamación concurrente, timeout ambiguo y expiración con reloj real.

La siguiente condición para probar señales reales es obtener disponibilidad
por partido y precios de props con contrato y frescura comprobados, junto con
la configuración activa del bot. Después corresponde medir supervivencia de
cuota y latencia de extremo a extremo y completar el protocolo prospectivo.
Compartir bot exige coordinar el presupuesto de mensajes de ambos emisores;
todavía no hay servicio conjunto desplegado ni rendimiento comercial demostrado.
