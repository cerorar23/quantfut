# Página pública NBA — 2026-10-09

Publicada en **https://pronosticosdeportivos.pro/nba**. Es la vista de investigación del piloto registrado, con 15 pronósticos, cinco jugadores y tres partidos. Muestra puntos, rebotes y asistencias, estimación, rango percentil 10–90, probabilidad respecto de la línea registrada y resultado oficial cuando esté disponible. Permite filtrar por jugador/equipo, mercado, partido y estado.

El 9 de octubre hay cero resultados evaluados. Los tres partidos registrados comienzan el 20 de octubre a las 13:00, 17:00 y 19:30, hora de Ciudad de México. Las fechas corresponden al calendario sellado del piloto; una discrepancia posterior con la fuente oficial exige revisión. El servidor original consulta resultados en sus ventanas finitas a +4/+6/+12/+24 horas. La página actualiza su lectura cada minuto; no ejecuta captura ni modelos. Si no hay un resultado verificable, mantiene pendiente, no disponible o en revisión. No garantiza que una fuente futura responda.

Las probabilidades son condicionales a participación. Los precios visibles son las cuotas recibidas y registradas previamente, con casa y fecha, y no son cotizaciones actuales. Las dos selecciones del piloto están identificadas como simulación, sin apuesta real. No se acredita disponibilidad final, rendimiento científico ni liquidación de una cuenta comercial mediante esta publicación.

## Datos y resultados verificables

La proyección usa exclusivamente la cohorte seleccionada y sellada en RUN065 y su plan RUN066/RUN067, conservando los 15 registros anteriores al partido. Lee los archivos originales montados para lectura. Verifica la cadena del diario del piloto, los sellos, el identificador del plan, la recepción y el cuerpo del boxscore oficial. Reconstruye el resultado desde el cuerpo recibido y contrasta partido, equipos, jugadores y conteos. Un archivo de resultados alterado, incluso con un sello recalculado, no sustituye el cuerpo oficial.

Jugador ausente del boxscore y DNP explícito tienen tratamientos distintos; un jugador que no participó no recibe un cero imputado ni entra como una predicción evaluada. Si los datos no pueden verificarse, la API responde sin publicar resultados dudosos; el navegador borra la respuesta anterior en vez de presentarla como actual.

## Servicio publicado

Servicio aislado `nba-dashboard-run69`, imagen `nba-dashboard-run69:20261009`, carpeta `/home/qf/nba-isolated/dashboard/run69-20261009`. Se reinicia automáticamente salvo detención explícita. La red interna `nba-dashboard-run69` conecta únicamente el servicio NBA y el proxy existente. El proxy conserva su red de fútbol y su configuración de recreación declara ambas redes. La ruta `/nba` no depende de este equipo ni de Codex.

El servicio ejecuta sin privilegios, con sistema de archivos de solo lectura, capacidades retiradas, límites de recursos y sin puertos publicados en el host. Monta el piloto, captura y estado de alertas para lectura; no monta la carpeta privada de credenciales ni la base de fútbol. La salida pública contiene una lista explícita de campos y no publica diarios, cuerpos recibidos, rutas locales, tokens ni claves. Se sirven únicamente cuatro recursos web y `/nba/api/data`; no hay listado de carpetas ni operaciones de apuesta.

La ruta de administración sigue protegida por Cloudflare Access y por el rechazo de solicitudes sin la cabecera de acceso en el origen. `/admin` y `/control` conservaron la pantalla de acceso; `/nba/.env` devuelve 404. La página principal de fútbol y `/health` respondieron 200 y los contenedores preexistentes conservaron sus identidades. No se reiniciaron la API ni el trabajador de fútbol. El proxy tuvo reinicios breves para comprobar que conserva la ruta tras reiniciar.

## Verificación y recuperaciones

La primera publicación detectó un montaje del proxy que aún leía un archivo anterior y revirtió el cambio. La segunda alcanzó HTTPS pero falló al exigir disponibilidad tras solo tres segundos de arranque; una tercera prueba encontró la misma carrera en el arranque inicial. Cada intento quedó conservado con reversión automática. La cuarta espera una respuesta HTTP real tanto inicialmente como después de reiniciar. Pasó; el reinicio del servicio mostró seis respuestas 502 durante su arranque y luego 200, manteniendo los mismos 15 registros y el diario del piloto intacto.

Pruebas NBA: **558 pasaron y dos omitidas**. Pruebas específicas nuevas: 16 pasaron y una omitida por permisos de enlace simbólico de Windows. Cubren resultados oficiales, DNP, manipulación de recepción/cuerpo/resultados/diario, rutas inseguras, aislamiento de campos, caducidad de salud y manejo HTTP. El arnés del proyecto antes y después de cambiar código pasó con **800 pruebas y 16 omitidas**; la comprobación final se registra en `verification.json` de RUN069.

La comprobación HTTPS desde este equipo detectó que el CDN existente añade una etiqueta de analítica a ciertas respuestas HTML. La primera comparación de bytes, que no la contemplaba, falló y se conservó. La segunda admite exclusivamente esa etiqueta de `static.cloudflareinsights.com`, exige igualdad de todos los bytes originales y compara CSS y JavaScript exactamente; pasó. No se modificaron las políticas de Cloudflare ni se amplió la política de scripts para permitir la analítica.

Comprobación real del navegador: página pública, 15 filas, cinco tarjetas de jugador y tres partidos; filtros de mercado, búsqueda de Cade, partido y ausencia de resultados evaluados; detalle de fechas y cuotas históricas; sin errores de consola. Capturas y estado visible conservados. Tras un bloqueo inicial, la apertura del dominio publicado funcionó. La vista local no fue accesible desde el navegador de comprobación. Este navegador mantuvo 700×572 píxeles pese a solicitar 1366×900 y 390×844: **la comprobación visual móvil queda pendiente**. Las reglas adaptativas a 850 y 620 píxeles están implementadas; no se afirma haber visto el tamaño móvil.

Esta publicación no realizó consultas adicionales a proveedores deportivos, consumos de cuotas de pago ni apuestas. No se activaron nuevas copias periódicas. Conserva las alertas operativas autorizadas y las decisiones/puertas científicas anteriores. Las ventanas futuras del piloto y sus límites de crédito siguen siendo los originales.

Evidencia: `apps/nba/.local/normalized/nba_f6_run69_20261009/`, registro `docs/nba_plan_fases_auditoria.json`, ejecución NBA-RUN-069. La recuperación aprobada es `deployment_result_v4.json`; los fallos anteriores se conservaron para revisión.
