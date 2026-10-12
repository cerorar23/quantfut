# QuantFut móvil: bienvenida, inicio y acceso VIP

**Estado actualizado:** ver [App real, monedas y referidos](APP_REAL_MONEDAS_REFERIDOS_20261011.md).
Las pantallas de muestra descritas a continuación pertenecen a la fase visual
anterior. Inicio, picks, cuenta y recompensas ya consumen el servidor real.

Fecha: 11 de octubre de 2026. Referencias: las diez capturas facilitadas por el usuario. Entrega: prototipo navegable dentro de la app Flutter; pendiente de conectar datos, identidad y compras.

## Pantallas implementadas

- Arranque oscuro con la marca QuantFut.
- Cinco bienvenidas en español: fútbol/NBA, contexto del partido, mercados, historial y lectura de probabilidades. Botones Saltar/Siguiente/Empezar e indicadores que permiten cambiar de página.
- Ilustraciones vectoriales originales animadas, dibujadas en Flutter: no necesitan Internet ni paquetes adicionales. Solo se anima la página activa; se detienen en segundo plano y respetan la preferencia de reducir movimiento.
- Barra inferior: Inicio, Predicciones, En vivo, La Grada y Perfil.
- Inicio: selector fútbol/NBA, indicadores pendientes de historial verificado, accesos a secciones, propuesta de simulador y tarjetas de ejemplo.
- Predicciones: búsqueda por equipo/liga, filtro VIP, días relativos y selector de deporte. Anillos de probabilidad y tabla de goles como muestras visuales. Combinada y Spor Toto tienen estados explicativos pendientes de integración.
- Ficha VIP: metadatos públicos del encuentro, formas de relleno difuminadas, candado y botón Hazte VIP.
- Planes VIP: selección semanal/mensual/anual propuesta, beneficios y navegación de compra. Precios por definir; el botón explica que no se ha efectuado ningún cargo.
- En vivo, La Grada y Perfil: propuestas navegables con estados pendientes, sin simular marcadores reales, usuarios, acceso autenticado ni notificaciones.

## Diferencias deliberadas respecto a las referencias

No se presentan como reales el 81 % de acierto, los 29 partidos en vivo, los 15.338 miembros, el descuento, los precios o las recompensas de invitación. Los indicadores reales aparecen con guiones hasta conectarlos a una fuente verificada; las tarjetas numéricas están identificadas como ejemplos.

Los planes de la referencia son una propuesta visual. El catálogo actual del backend incluye duraciones de uno, tres y seis meses: acordar un catálogo común para web y app antes de activar compras. El diseño no concede suscripciones ni verifica pagos.

La bienvenida no promete detectar goles antes de que sucedan, recompensas por escribir o días VIP por invitación. Esas funciones necesitan datos/reglas y una fase propia. El arranque conserva por ahora la espera de cuatro segundos y muestra la bienvenida en cada lanzamiento; al integrar sesión se sustituirá por inicialización real y una bienvenida persistida por versión.

## Regla de acceso VIP

El difuminado es una presentación visual, no un control de acceso. Las fichas de ejemplo bloqueadas solo contienen nombre del encuentro, liga, deporte y día; no contienen selección, porcentajes o contenido premium bajo el desenfoque.

La integración debe mantener esta regla: la API comprueba identidad y suscripción, devuelve únicamente metadatos públicos a quien no tiene acceso y entrega el análisis autorizado a quien sí lo tiene. No descargar un pronóstico privado y ocultarlo después. La compra debe activar acceso únicamente tras confirmación verificada por el backend.

## Fases para concretar tras las próximas ideas de pantallas

| Fase | Entrega | Criterio de aceptación |
|---|---|---|
| 0 · Diseño | Estas pantallas y siguientes propuestas; catálogo y contenido acordados | Navegación revisada, funciones identificadas como existentes o futuras y diseño adaptable |
| 1 · Base | Entornos, configuración Firebase y servicios Flutter | Desarrollo separado de producción; inicialización y errores controlados |
| 2 · Cuenta | Inicio/registro/recuperación y vínculo con cuentas del backend | Sesión verificada, transición segura de cuentas existentes y permisos del servidor |
| 3 · Contenido | API fútbol/NBA, historial y tarjetas gratuitas/VIP | Datos reales; carga/error/vacío; contenido privado ausente sin autorización |
| 4 · Avisos | Preferencias, tokens FCM, envío y enlaces a pantallas | Avisos autorizados, deduplicados y dirigidos al contenido correcto |
| 5 · Medición | Analytics, Crashlytics, Performance y control del producto | Eventos sin datos personales; filtros de entorno; métricas útiles y errores visibles |
| 6 · Compras | Catálogo común, proveedor, restauración y validación del acceso | Confirmación verificada, idempotencia y estados pendiente/cancelado/expirado |
| 7 · Nuevos módulos | Comunidad, radar, simulación e invitaciones según prioridad | Datos y reglas definidos, moderación y permisos antes de publicarlos |
| 8 · Lanzamiento | Identidad definitiva, accesibilidad y revisión Android/iOS | Configuración y compilaciones de distribución verificadas |

Medición propuesta: `onboarding_view`, `onboarding_skip`, `onboarding_complete`, `tab_view`, `prediction_filter`, `vip_locked_view`, `vip_cta`, `plan_selected` y eventos de compra confirmados por el servidor. No se envía telemetría en este prototipo. Evitar contar de nuevo una vista por cada reconstrucción del widget.

## Archivos y validación

- `lib/onbonding_screen/second_screen.dart`: bienvenidas.
- `lib/product/welcome_art.dart`: animaciones.
- `lib/bottombar.dart` → `lib/product/product_shell.dart`: navegación, tarjetas y planes.
- `test/app_smoke_test.dart`, `test/product_navigation_test.dart`: recorrido desde arranque, las cinco pestañas, filtros, acceso a planes, retorno, compra inactiva y adaptación a 320 × 568 con texto al 160 %.
- `docs/validation/pantallas_20261011/`: capturas generadas desde las vistas Flutter, sin modificar las referencias del usuario.

Las nueve pruebas anteriores más cuatro pruebas nuevas pasan (13 en total). Análisis Flutter sin incidencias; compilación Android debug validada. Esto no valida Firebase, la API ni pagos porque todavía no están conectados. El nombre del paquete nativo sigue siendo el de la plantilla; se definirá junto con la configuración Firebase antes del lanzamiento.

Referencia de arquitectura: `FIREBASE_INTEGRACION_CON_BACKEND_20261011.md`.

Actualización del usuario: las pantallas de mercados se adaptan a resultados
del proyecto y la tercera pestaña pasa a Mercados; ver
`MERCADOS_MODELO_APP_20261011.md`. Registrado además selector de idioma antes
de bienvenida y traducción completa app/backend/Firebase como pendiente en
`IDIOMAS_APP_BACKEND_FIREBASE_20261011.md`.


## Actualización: detalle y VIP

La tarjeta bloqueada sustituye el difuminado por el diseño verde/dorado con resumen público de ejemplo. La selección premium sigue ausente del objeto bloqueado. Añadidas ventana de pronóstico, Estadísticas y H2H/táctica; panel de rendimiento publicado, comparación Básico/VIP y compra fija en los planes. Alcance y contratos pendientes en `DETALLE_PRONOSTICO_Y_VIP_20261011.md`.
