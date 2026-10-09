# Menú Fútbol/NBA e histórico guardado — 2026-10-09

La página https://pronosticosdeportivos.pro/ incluye en la cabecera el selector **Fútbol | NBA**. NBA abre https://pronosticosdeportivos.pro/nba; el enlace Fútbol de NBA permite regresar. Son enlaces normales, accesibles por teclado, y el deporte activo está identificado. El selector está fuera del menú de secciones que se oculta en móvil; la cabecera móvil puede envolver sus controles para mantenerlo visible.

El histórico local verificado tiene **164.218 filas jugador-partido y 6.313 identificadores de partido**, entre **2021-10-19 y 2026-06-13**. Su archivo es `apps/nba/.local/normalized/nba_subsecond_20261006/player_games.jsonl.gz`, evidencia registrada `NBA-EV-2204`, SHA256 `722b9f2133465d7a8ccca6108a3996df70d8118e5c7791a50015c75e40003152`. Corresponde a la versión aceptada del censo de investigación descrito en `docs/nba_segundos_y_rotaciones_20261006.md`; no acredita toda la historia NBA ni cobertura uniforme de todas las competiciones. Se verificó la huella antes de contar las filas, fechas e IDs, sin modificar datos.

Estos son **datos retrospectivos de partidos y jugadores**, útiles para investigación y entrenamiento. No son un historial de pronósticos emitidos previamente ni prueba de aciertos retrospectivos. La página NBA sigue mostrando los **15 pronósticos únicos sellados del piloto**, de cinco jugadores y tres eventos, con cero resultados oficiales evaluados el 9 de octubre. El historial evaluado se formará con los resultados futuros que el piloto original reciba y valide. No se fabricaron pronósticos históricos ni se añadieron estadísticas antiguas como resultados del piloto.

## Publicación y controles

Solo cambiaron `frontend/app.js`, `frontend/styles.css` e `frontend/index.html`; las referencias de JavaScript/CSS incorporan sus nuevas huellas para evitar recursos antiguos en caché. La imagen desplegada `quantfut-api-menu70:20261009` deriva de la imagen exacta que ya estaba ejecutando fútbol y añade una capa con esos tres archivos públicos. Las capas de código y dependencias originales se conservaron; no se copiaron secretos ni otros cambios locales de backend.

Se actualizó la imagen de la API en la configuración persistente y se recreó exclusivamente la API. El trabajador, base de datos, proxy y contenedores NBA conservaron sus identidades. La modificación de imágenes y fuentes permite futuras recreaciones; no depende del equipo local. El piloto NBA conservó sus 15 registros y cero resultados. `/control` y `/admin` conservaron Cloudflare Access. No se modificaron credenciales, puertas científicas ni copias periódicas.

El primer intento encontró `ConnectionResetError` al consultar salud durante el arranque, revirtió archivos/configuración y restauró la imagen anterior. Se conservaron ese informe y la captura previa. La recuperación tolera únicamente los errores temporales de conexión al consultar la salud propia; exige una respuesta real 200 antes de comprobar rutas y archivos. Pasó con tres lecturas transitorias sin conexión y después 200. Los recursos públicos coinciden con los candidatos y la navegación Fútbol → NBA → Fútbol se comprobó realmente en navegador.

Verificación: 24 pruebas de frontend pasaron; sintaxis JavaScript válida; arnés antes y después con 800 pruebas pasadas y 16 omitidas. Navegación superior visible, enlace activo correcto, ausencia de desbordamiento horizontal a 1280×720 y sin errores de consola. Captura guardada en `apps/nba/.local/normalized/nba_f6_run70_20261009/menu_futbol_nba.jpg`.

El navegador ignoró otra vez la solicitud de tamaño 390×844 y mantuvo 1280×720, incluso en una pestaña nueva. Se implementaron reglas móviles, pero **la revisión visual móvil continúa pendiente**. No se declara como probada. La limitación anterior de RUN069 se conserva.

Evidencia y protocolos: `apps/nba/.local/normalized/nba_f6_run70_20261009/`; despliegue recuperado en `/home/qf/quantfut/deployments/menu70-v2-20261009`. La publicación no llamó directamente a proveedores de cuotas NBA ni ejecutó apuestas. Se conservan los registros RUN001–RUN069 y los mismos requisitos científicos y comerciales.
