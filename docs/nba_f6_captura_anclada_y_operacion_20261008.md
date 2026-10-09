# NBA-RUN-057 — fuentes recuperadas, sellos externos y captura continua

La recuperación NBA volvió a producir datos utilizables para investigación: **seis partidos de pretemporada, doce plantillas con 247 jugadores, 240 identidades NBA estables, 101 observaciones de lesiones y 14 precios públicos de Caliente México**. El VPS conserva respuestas originales y recibos nuevos cada 15 minutos, con respaldo diario y retención de siete archivos generados. Dos manifiestos tienen firma temporal independiente verificada. **F6 continúa en progreso y F7 permanece sin iniciar**: todavía faltan props individuales con contratos completos, disponibilidad por partido y un modelo compatible con prórroga.

| Resultado | Alcance comprobado |
| --- | --- |
| Validación NBA | 390pruebas aprobadas, incluidas transacciones reales en una base PostgreSQL nueva; cero omisiones |
| Arnés general inicial y final | 768 pruebas aprobadas, diez omisiones y una advertencia |
| Nuevos controles | 34casos sobre contexto, precios, respaldo y operación; respuestas inválidas nunca activan pronósticos |
| Datos locales normalizados | Seis eventos futuros,247jugadores,101lesiones y14selecciones de precios |
| Identidad | 240IDs NBA corroborados por nombre/fecha de nacimiento contra cruce previo; siete sin acreditar |
| Sellos externos | Dos respuestas RFC3161 de DigiCert; nonce, contenido y cadena verificados |
| Captura VPS inicial | 15recibos:14ESPN200 y un Caliente403; seis eventos NBA |
| Respaldo/restauración | Archivo del VPS verificado y restaurado localmente con15eventos y cuerpos idénticos; pruebas temporales verificadas de nuevo |
| Operación | Contenedor propio, reinicio preservado, ningún puerto publicado; los seis servicios existentes conservan identidad y ejecución |
| APIs deportivas pagadas y mensajes nuevos | Cero; cota ZenRows2232/3200 conservada |
| Contratos individuales acreditados, apuestas o inicio F7 | Cero |

## Contexto y precios realmente recuperados

Los seis partidos vienen del marcador público de [ESPNNBA](https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20261008), temporada2027 y tipo1, pretemporada. Se mantienen los IDs en su espacio ESPN. No se atribuyen IDs de partidos oficiales NBA sin un cruce acreditado. Las doce plantillas se obtuvieron de ESPN para esa temporada; el cruce previo de nombres y fechas de nacimiento acredita identidad estable, **no pertenencia actual oficial al equipo**. La consulta nueva de jugadores NBA devuelve403.

La [fuente ESPN de lesiones](https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries?limit=1000) entregó101observaciones. Algunos registros omiten `athlete.id`, pero sus enlaces públicos permiten obtener un ID ESPN único. Se rechazan IDs contradictorios y se conserva como desconocido lo que carece de enlace válido. Estado genérico y fecha reportada no acreditan disponibilidad para un partido concreto. La etiqueta `Active` del roster tampoco constituye parte médico ni garantiza participación.

La página pública de [Boston–Cleveland en Caliente México](https://sports.caliente.mx/es_MX/e/33506702/Boston-Celtics-%40-Cleveland-Cavaliers) permitió recuperar14selecciones del evento. Se filtran anuncios, navegación y otros deportes, y se lee expresamente el precio decimal. El mismo ID de selección puede aparecer con etiqueta corta y completa; se conservan ambas si el resto coincide. Un precio contradictorio para ese ID se rechaza.

Las selecciones son mercados de partido/equipo, **no props individuales de rebotes, puntos o asistencias**. No hay hora de actualización del proveedor acreditada, versión aplicable de reglas ni contrato completo. El horario visible del sitio y el horario UTC de ESPN tienen una discrepancia de una hora cuya semántica de zona no está resuelta. El campo opaco `data-msg_stamp` no se convierte en fecha. Estos precios siguen sin ser accionables.

Las páginas públicas NBA de calendario y quintetos respondieron200, pero los datos incrustados examinados no contenían calendario ni quintetos actuales. Se distingue una página accesible de un feed funcional. Codere redirigió y la captura quedó detenida por el control de URL. BetPlay permitió leer su página y un recurso público; una ruta candidata del catálogo Kambi produjo `URLError`, sin respuesta HTTP ni datos. No se utilizó autenticación ni se atribuye cobertura a esa ruta. Los fallos permanecen archivados.

## Anclaje externo con alcance preciso

Se implementó RFC3161 mediante el [servidor oficial DigiCert](https://knowledge.digicert.com/general-information/rfc3161-compliant-time-stamp-authority-server) y las comprobaciones de [OpenSSLts](https://docs.openssl.org/3.0/man1/openssl-ts/). Se transmitieron únicamente hash SHA256 y nonce. Se conservaron solicitud, respuesta firmada, certificados, paquete de confianza, texto del sello y resultado de verificación. Se comprobó tanto correspondencia de solicitud/nonce como hash de los bytes del manifiesto. Dos controles negativos reales rechazaron contenido alterado y un nonce distinto.

El manifiesto local enlaza25recibos originales nuevos, sus cuerpos y los datos derivados, además del prefijo de auditoría hasta el evento130. El tiempo firmado es **2026-10-08 17:39:29UTC**; SHA256 del manifiesto `cb48fd3ce50516996ac39edaacb6289c74501a06a655181e37b223945e2d0053`. El primer manifiesto del VPS tiene tiempo firmado **17:52:14UTC** y SHA256 `30d38e18bb02dbe3e7350d8b3e6739d5c6466151cc40ba10c38e49d9476660b6`. La prueba del VPS volvió a verificarse después de copiarla al equipo local.

Estos sellos acreditan existencia de esos bytes antes del tiempo firmado, bajo la confianza de la autoridad y su cadena. No prueban exactitud deportiva, legitimidad contractual, la recepción original de archivos históricos ni sincronización entre los relojes del equipo y VPS. No se probó revocación OCSP/CRL. La consulta BetPlay posterior al primer manifiesto queda fuera de ese sello; no se considera anclada. Tampoco se presenta el checkpoint final como sellado externamente.

## Captura autónoma y recuperación

El contenedor `nba-research-capture` corre en `/home/qf/nba-isolated/research-capture/run57-20261008`, con imagen construida desde digest fijado. Usa un usuario sin privilegios, raíz de solo lectura, capacidades eliminadas, prohibición de nuevos privilegios, red propia,0,25CPU,128MiB y64procesos. No monta secretos ni directorios de fútbol. No envía alertas o picks y no coloca apuestas. Se comprobó que un reinicio conserva ledger, recibos y salud.

La captura de calendario y página de Caliente se intenta cada15minutos; lesiones y plantillas se consultan como máximo una vez por hora. El sello se solicita como máximo una vez por24horas; un fallo queda registrado sin reintento automático inmediato. El primer ciclo acreditó14respuestas ESPN válidas y un403 de Caliente desde el VPS. La salud se mantiene **`source_degraded`**; esa etiqueta no oculta los datos ESPN válidos ni considera resuelto el acceso continuo a precios mexicanos.

El primer intento de activación exigía todas las fuentes200 y se detuvo al detectar ese403. Se conservaron su informe, código e imagen. Un segundo protocolo activó exactamente el mismo colector con la degradación explícita, comprobando la única fuente bloqueada. No hubo otra consulta deportiva o solicitud temporal para ese segundo paso.

Los respaldos diarios usan la copia consistente de SQLite y reúnen los cuerpos referenciados por el ledger. Cada miembro y su hash se verifican; rutas inseguras y cuerpos corruptos impiden aceptar el archivo. La retención elimina exclusivamente archivos generados válidos dentro de su carpeta y mantiene siete. Los cuerpos originales nunca se eliminan. Se pausa la captura si alcanza16GiB de datos propios o quedan menos de10GiB libres en el host. Estos límites no garantizan retención indefinida.

El primer archivo se copió fuera del VPS y se restauraron explícitamente15eventos y sus cuerpos, con igualdad de hashes y cadena. Se copiaron también12archivos entre respaldo, manifiesto, pruebas temporales, salud, estado y logs de construcción. **La copia fuera del VPS fue puntual**: no hay sincronización periódica fuera del host. Los archivos diarios actuales contienen ledger/cuerpos, sin incluir las pruebas temporales; estas siguen separadas en su directorio. Falta automatizar un respaldo integral que incluya también sellos, modelos y cola de alertas. La copia diaria empieza con el primer ciclo del día, de modo que las capturas siguientes esperan al archivo del día siguiente.

## Verificación, fallos y pendientes

Se preservaron las56corridas,20.143evidencias y123eventos anteriores. La normalización inicial falló por IDs de lesiones ausentes; la segunda, por etiquetas distintas para una selección idéntica. Se conservaron ambas y sus versiones antes de corregirlas. Tres pruebas de respaldo fallaron porque los contextos SQLite no cerraban los handles en Windows; el cierre explícito corrigió el defecto. Las31pruebas de fuentes/respaldos y las tres pruebas de operación pasaron después; la suite final completa aprobó390casos. La base de ensayo anterior conserva sus39eventos y19mensajes; el clúster local quedó detenido.

La confirmación F7 conserva el candidato y criterios propuestos anteriores, sin inicio ni resultados nuevos atribuidos a confirmación. La recepción prospectiva y la prueba externa ya tienen una ruta funcional. Permanecen estos requisitos:

- Props individuales de casas/jurisdicciones objetivo con vínculo completo a partido, jugador, línea, período, reglas y versión aplicable.
- Universo previo acreditado, disponibilidad y rol por partido; pertenencia actual oficial y controles de identidad pendientes.
- Modelo de minutos/conteos que incluya prórroga cuando el contrato la incluya. Se mantiene el rechazo de alcance incompatible; no se excluyen juegos después de conocer que tuvieron OT.
- Muestra continua del recorrido completo recepción→cálculo→sellado→envío→acuse, política de caducidad entre relojes y p95 operativo. El colector de investigación no prueba ese recorrido.
- Respaldo integral y copia periódica fuera del host, con recuperación automática del alcance necesario.
- Congelación de universo, exclusiones, umbrales y evaluación independiente antes de abrir F7. Los seis eventos de pretemporada no sustituyen la muestra regular requerida.

Los tickets/logs históricos originales siguen ausentes según la respuesta del usuario. Nuevas descargas y sellos no reconstruyen aquellos recibos. G0–G9 permanecen en su estado anterior y no se declara producción comercial lista.
