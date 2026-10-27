# Web ergonómica: fútbol, NBA y tenis — 27-oct-2026

El titular pidió reorganizar la web siguiendo sus ideas de lectura y venta, e incluir los tres deportes de forma ergonómica. Se aplica la jerarquía portada → pronósticos → resultados → planes con una sola navegación y filtros por deporte, fecha y estado. CYBERCORE CSS 0.3.0 sigue siendo la biblioteca instalada y servida; `ergonomia.css` mejora jerarquía, legibilidad, contraste y adaptación móvil. Se mantienen las cuentas y el checkout real.

## Contenido y acceso

- Fútbol conserva `/mobile/v1/home` y `/mobile/v1/matches/{id}`, incluida la autorización gratis/Plus del servidor. Los mercados reservados se indican sin copiar sus selecciones, cuotas ni probabilidades.
- NBA consume únicamente su fuente pública `/nba/api/data`. Conserva estados de validación y etiqueta las revisiones posteriores al inicio; estas se excluyen de los resultados de pronósticos previos. Las líneas estadísticas no se presentan como cuotas de una casa. El detalle agrupa partido y jugadores.
- Tenis obtiene una proyección explícita de sus predicciones selladas y los resultados de API-Tennis archivados. El exportador comprueba el hash de cada publicación, su fecha previa al inicio y los recibos originales antes de tomar resultados. No importa el motor ni hace predicciones o llamadas a proveedores.
- La API **solo lee el JSON público** en `/srv/quantfut/artifacts/public-sports/tennis.json`, dentro de un volumen ya existente. No monta originales privados ni recibe modelos, coeficientes, credenciales o configuraciones del motor. Aplica otra lista de campos permitidos y rechaza una salida de más de dos horas. La revisión automática rechazó el primer planteamiento de montar originales en la API; se sustituyó por esta proyección pública limitada.
- La salida pública se actualiza mediante `scripts/publicar_tenis_web.py`, ejecutado en el host. Lee el proyector revisado, genera exclusivamente campos públicos y sustituye atómicamente ese único JSON mediante `docker exec`. No cambia el entrenamiento ni el sellado, ni modifica el cron del motor.
- Los resultados conservan aciertos y fallos por fecha, sin seleccionar solo aciertos ni inventar rentabilidad. Los precios y periodos proceden de `/app/v1/plans`; el destacado comercial no se anuncia como «más vendido».

## Interacción

Cuatro accesos principales: pronósticos, resultados, planes y herramientas. El menú adicional conserva las funciones anteriores. En móvil, barra inferior con Hoy, Resultados, Planes, Cuenta y Más; controles de al menos 44 px donde se requiere interacción principal. Las siete fechas siguen accesibles, con búsqueda por equipo, jugador o torneo. La lista empieza por próximos; si una fecha no tiene NBA, ofrece la última jornada publicada con su fecha explícita. Fallos de una fuente no sustituyen ni impiden ver las demás.

## Comprobación

- 51 pruebas frontend: contratos, fuentes separadas, bloqueo, revisión NBA, fallos, escapes, precios y arranque.
- 58 pruebas iniciales de API, entrega y publicación; tras cambiar al lector de JSON público, sus siete pruebas pasan (incluidas descarte de campos privados y caducidad).
- Lectura real de tenis: 155 eventos recientes, 131 con resultado, cero problemas de sellos. Los números son una observación de la prueba, no cifras fijas en la web.
- Navegación real probada: tres deportes, acceso a la jornada NBA del 26-oct, análisis por partido/jugadores y vista móvil de 390 px sin desplazamiento horizontal.
- El arnés local se intentó con el entorno virtual del proyecto: la suite completa requiere Postgres de pruebas; una prueba previa al rediseño intentó conectar a una base inexistente (`test_antelacion_y_cierre`). La comprobación completa con Postgres corresponde a GitHub Actions antes de integrar y publicar; no se modifica esa prueba ni se evita la puerta de publicación.

Publicación y reversión se registran en `DEPLOYS.md` tras comprobar la versión base, ensayar la imagen y respaldar. Solo se cambia la API y se añade la actualización del JSON público; los productores y sus datos originales permanecen intactos.
