# Detalle de pronósticos y página VIP

**Actualización:** la navegación actual consume datos reales y permisos del
servidor. Ver [App real, monedas y referidos](APP_REAL_MONEDAS_REFERIDOS_20261011.md).
Las descripciones y capturas de ejemplos siguientes documentan el prototipo
anterior; no representan las cifras ni la integración actuales.

Diseño solicitado el 11/10/2026, adaptado a QuantFut y a las fichas de ejemplo existentes.

## Implementado en el prototipo

- Tarjeta VIP con fondo oscuro verde/dorado, equipos, monogramas originales, vista gratuita identificada como ejemplo y botón «Desbloquear pronóstico VIP» que abre los planes.
- «Ver pronóstico» abre una ventana desplazable con cierre, favorito de sesión y copia local del resumen. El listado conserva su posición al volver.
- Pestaña Pronósticos: selección destacada, probabilidad, indicadores disponibles y filtros de mercados. Fútbol y NBA utilizan categorías diferentes.
- Pestaña Estadísticas: probabilidades de resultado, gráfico de radar para dos equipos y distribución de goles. Los indicadores ausentes aparecen con guiones; el radar no dibuja series inventadas. La distribución de goles solo corresponde a fútbol y requiere parámetros del modelo entregados por el servidor.
- Pestaña H2H y táctica: historial, alineaciones, bajas y árbitro con estados pendientes. «Información pendiente» no equivale a «sin bajas».
- Página VIP: panel de resultados publicados con fecha de corte, barras por mercado y tamaño de muestra; comparación Básico/VIP; planes propuestos y botón de compra fijo que muestra que la compra aún no está disponible.

El panel utiliza el historial público guardado: 75/96 resueltos (78,1 %), corte 11/10/2026 a las 21:25 UTC. Las tres familias mostradas son las de mayor muestra publicada: hándicap 14/21; goles 15/21; doble oportunidad 15/20. No es una clasificación por rentabilidad ni una prueba de superioridad. Todas estas muestras por mercado son limitadas. La racha aparece pendiente porque el resumen agregado no contiene la secuencia de resultados.

No se copian cifras de usuarios/reseñas, cuotas, ELO, xG, rachas, precios, garantías de reembolso ni afirmaciones de algoritmo verificado de las referencias. No se prometen ganancias ni acceso ilimitado a servicios no configurados.

## Contratos de backend pendientes para la fase de contenido

1. Identificador estable del partido/pick, deporte, liga, fecha y zona horaria; equipos y URLs de escudos verificadas. Los monogramas actuales no son escudos oficiales.
2. Respuesta pública con metadatos y, cuando exista, un resumen gratuito explícitamente autorizado: mercado y probabilidad. `PublicMatchTeaser` no contiene selecciones privadas ocultas.
3. Respuesta autorizada con selecciones, claves de mercado, líneas, probabilidades por pick, cuotas y fecha/fuente de la cuota; procedencia y versión del modelo. El cliente no asignará valor o confianza IA a partir de un porcentaje histórico.
4. Estadísticas opcionales: distribución 1X2 validada; indicadores normalizados para comparar ambos equipos y sus unidades; xG/ELO cuando estén calculados; distribución de goles o parámetros únicamente si el modelo declara esa distribución. `MatchStatistics` prepara la vista, todavía sin API conectada.
5. H2H con fechas/resultados, alineaciones y su estado confirmado, lesiones/sanciones con estado de disponibilidad y árbitro. Un dato ausente se conserva como ausente.
6. Rendimiento calculado sobre picks sellados y resueltos: muestra, aciertos, fallos, pendientes/anulados, fecha de corte, secuencia para rachas y filtros por deporte/mercado. Separar evaluación retrospectiva de historial publicado.
7. El servidor valida identidad y acceso VIP antes de devolver contenido privado. La compra del prototipo no desbloquea nada. Un pick VIP autorizado se abrirá con la misma ventana de detalle después de la validación real de acceso.
8. Catálogo común de planes web/app, precios y moneda; condiciones de renovación, cancelación, restauración y reembolso según proveedor. La comparación de beneficios es una propuesta, no cuotas operativas activadas.

## Firebase, idiomas y control pendientes

- Firebase Auth y vínculo con la cuenta web; autorización del backend y actualización del acceso tras compra confirmada.
- FCM con enlaces al partido/pick; al abrir un aviso comprobar sesión y acceso antes de cargar el detalle privado.
- Analytics: `prediction_open`, `prediction_tab_view`, `prediction_market_filter`, `vip_locked_view`, `vip_cta`, `vip_plans_view`, `plan_selected`; errores de carga a Crashlytics y tiempos de detalle a Performance. No se envía telemetría en este prototipo.
- Traducir todos los textos de tarjetas, ventanas y comparación mediante los catálogos previstos; selector de idioma antes de bienvenida y preferencia sincronizada con backend/Firebase siguen pendientes.
- Favoritos y exportación/copia: el favorito actual dura la vida de la ventana; definir persistencia por cuenta y permisos de exportación antes de conectarlos.

## Validación

Recorridos de ventana, filtros, cierre, VIP sin contenido privado, planes, compra inactiva y adaptación a 320 × 568 con texto al 160 %. Prueba matemática de la distribución Poisson con cola 3+ y casos límite. Capturas en `docs/validation/detalle_vip_20261011/`.

Referencias de fases: `FIREBASE_INTEGRACION_CON_BACKEND_20261011.md` y `IDIOMAS_APP_BACKEND_FIREBASE_20261011.md`.
