# QuantFut: análisis y adaptación de TennisPredictions

Fecha: 7 de octubre de 2026. Primera implementación local, sin despliegue.

## Qué aporta la referencia

La [portada pública de TennisPredictions](https://tennispredictions.ai/) combina
un titular editorial, un resumen del día, calendario, filtros, búsqueda y filas
de partidos agrupadas por competición. Los enlaces a la ficha y al historial
reducen los pasos entre explorar un partido y revisar su resultado. El diseño
es útil para QuantFut porque su proyecto ya tiene agenda, fichas, precios y
evidencia pública.

El alcance de esta revisión es el contenido público accesible. Los porcentajes
y explicaciones de su modelo son afirmaciones del sitio, no una validación
independiente de su rentabilidad ni un método reproducible para QuantFut.

## Adaptación implementada

| Patrón de la referencia | Adaptación a QuantFut |
| --- | --- |
| Titular editorial y resumen | «Lee el partido. Entiende la cuota.» con conteos de agenda demo, sin cifras comerciales inventadas |
| Calendario semanal | Siete fechas con estado activo, también visibles en móvil |
| Filtros y búsqueda | Equipo/liga, próximos/cerrados, competición y orden por hora o diferencia de precio |
| Agrupación por torneo | Filas por liga con ficha accesible desde equipo y flecha |
| Pick, cuota y confianza | Probabilidad 1X2 del modelo separada de precio justo, cuota/casa y estado del criterio |
| Pick del día y Bet Builder | Accesos a las vistas existentes de Pick del día y Combinadas |
| Progress | Acceso al historial verificable y al estado real de publicación |
| Fondo azul/violeta | Paleta del usuario: azul noche y pizarra, con esmeralda y azul para datos |

La paleta sigue la segunda imagen aportada: `#0b132b`, `#1c2541`, `#3a506b`,
`#f8fafc`, `#94a3b8`, `#10b981`, `#059669`, `#38bdf8` y token de riesgo
`#ef4444`. Se migraron las superficies verdes del resto de las vistas al mismo
sistema para evitar una portada que parezca un producto distinto.

## SingleFile y la copia local

Se utilizó el ejecutable oficial de
[SingleFile CLI](https://github.com/gildas-lormeau/single-file-cli), versión
2.18.0, para guardar la portada pública con manifiesto:

- `.local/design-reference/tennispredictions.html`
- `.local/design-reference/tennispredictions.html.manifest.json`

La captura permite conservar la referencia visual y sus recursos en un HTML.
No reproduce su backend, modelo, cuentas ni contenido de suscripción. No se
incorporó SingleFile como dependencia de QuantFut; la web adaptada sigue usando
HTML, CSS y JavaScript del proyecto. El archivo de referencia y la herramienta
permanecen en la carpeta local ignorada por Git.

## Propuesta para la siguiente fase

1. **Llevar la agenda real al nuevo tablero.** Reutilizar `/web/partidos` y sus
   estados de carga/vacío/error. Las filas deben usar resultados confirmados y
   escudos disponibles. El tablero implementado aquí sigue siendo demo; la
   agenda real conserva su sección independiente y sus fichas.
2. **Una ficha que explique la elección.** Priorizar cuota registrada, mínimo,
   fecha de cálculo, contexto y criterio del servidor. La forma, el cara a cara
   y las alineaciones ya existen en la vista de Partidos; conviene conectarlos
   al producto publicado sin inventar una puntuación de confianza.
3. **Dar más protagonismo a la evidencia.** Exponer muestra, periodo, ROI con
   intervalo y EV al cierre comparable cuando los endpoints tengan datos. Un
   porcentaje de aciertos aislado no basta para describir el rendimiento.
4. **Ampliación NBA como producto separado.** La navegación por deporte puede
   diseñarse después de disponer de endpoints propios. La implementación de
   esta fase mantiene el aislamiento actual de NBA y fútbol.

Las cuentas, pagos, notificaciones y publicación comercial conservan sus
condiciones previas. El rediseño no activa ninguna puerta del servidor.

## Verificación

- `npm run check`: sintaxis y 9 pruebas existentes de integración pública.
- Suite Python del proyecto: 732 pruebas aprobadas antes de los cambios de
  presentación; una advertencia de dependencia. El script shell del arnés no
  encontró sus utilidades dentro del entorno restringido, por lo que no se
  consideró su mensaje «OK» una verificación válida y se ejecutó Python con
  el entorno del proyecto.
- Navegador: búsqueda, filtros, fechas con/sin partidos, acceso a fichas y
  accesos rápidos; revisión de escritorio y móvil. El servidor Node de vista
  previa no tiene API: sus errores de datos reales se muestran como tales.

Abrir la versión local con `npm run dev` desde `frontend/`, en
`http://127.0.0.1:5173`. No se ha publicado en producción.

## Ampliación de acceso y suscripciones

La segunda fase solicitada ya incluye paquetes, login/registro/recuperación
de ejemplo, Mi cuenta y planes de 1/3/6 meses más Club con resumen de pedido.
El modelo y la verificación actual están en
[modelo_paquetes_suscripciones_20261007.md](modelo_paquetes_suscripciones_20261007.md).
Autenticación, cobro y autorización reales siguen pendientes de integración.
