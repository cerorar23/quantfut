# Pendiente: selección de idioma desde el arranque

Fecha: 11 de octubre de 2026. Petición del usuario: tomar en cuenta la pantalla adjunta y anotar traducción, backend y funciones relacionadas junto con Firebase. **Requisito registrado para implementar por fases; todavía no hay selector ni traducción completa en la app.**

## Experiencia acordada como requisito

- Actualización posterior, solo planificar: el registro/acceso será la primera
  pantalla, según la nueva captura del usuario. Incluir allí un botón de idioma
  en la esquina superior, disponible antes de autenticar y de las cinco
  bienvenidas. El selector puede abrir las tarjetas de idiomas de la referencia
  anterior; no anteponerlo como pantalla obligatoria. No implementar todavía.
- Opciones iniciales: Español, English, Português, Français, Italiano y Deutsch. Identificadores estables `es`, `en`, `pt`, `fr`, `it`, `de`; especificar variantes regionales al preparar las traducciones.
- Detectar idioma del dispositivo como sugerencia; permitir elegir sin registro. Guardar la selección localmente y usar español como alternativa cuando no haya traducción disponible.
- Siguientes inicios: conservar la elección. Mantener acceso para cambiarla desde bienvenida/entrada y desde Perfil → Idioma, sin obligar a repetir el selector.
- La selección cambia todos los textos de interfaz: bienvenida, cinco pestañas, mercados, estados de carga/error/vacío, cuenta, VIP, avisos, soporte y accesibilidad.
- El idioma no cambia el deporte favorito, ligas, probabilidades, permisos VIP, moneda de cobro o zona horaria. Los nombres de ligas de la referencia son indicativos; los favoritos se configuran aparte.

## Construcción Flutter

Separar los textos de los widgets en catálogos localizados (propuesta: ARB y generación de localizaciones Flutter). Identificadores de ruta, mercado, evento de Analytics y campos JSON permanecen estables. No traducir nombres de variables o claves de negocio.

Soportar parámetros y plurales: conteo de partidos/resultados, porcentajes, duración del plan y estados de compra. Formatear fechas, horas y números conforme a la preferencia, conservando la zona horaria elegida y la moneda real de cada plan. Reservar espacio para textos largos y comprobar caracteres acentuados en la tipografía. No depender de imágenes que lleven textos incrustados; las ilustraciones actuales de bienvenida necesitan también textos localizables.

Guardar una versión de bienvenida completada y el idioma por separado. Elegir idioma no autoriza medición, notificaciones o una compra.

## Backend y cuenta compartida

- Añadir preferencia de idioma a la cuenta mediante migración compatible, sin reescribir registros o migraciones auditadas. Permitir sincronizarla desde app/web una vez autenticadas.
- Visitante: preferencia local. Cuenta: definir precedencia y sincronización; sugerencia, conservar la elección explícita más reciente y aplicarla en la cuenta sin perder la preferencia al iniciar sesión.
- API con idioma aceptado de una lista cerrada, alternativa española y códigos de error estables; traducir la presentación, no los datos del modelo. Separar valores numéricos/unidades de frases ya formateadas.
- Mercado/selección/línea y resultado se almacenan una sola vez. Construir su descripción en el idioma elegido a partir de esos campos. No crear seis copias independientes de un pronóstico o de su historial.
- Correos de cuenta, recuperación, avisos de suscripción, soporte y textos de la web deben seguir la preferencia correspondiente. Mantener coherentes los permisos y el contenido en todos los idiomas.

## Integración Firebase y otras funciones

- Registrar idioma preferido por cuenta/instalación al integrar FCM. Plantillas traducidas con alternativa definida; links y destinatarios mantienen el mismo control de autorización.
- Un cambio de idioma no genera seis avisos ni cambia la idempotencia del evento. Resolver qué idioma utiliza cada instalación si una cuenta tiene varios dispositivos.
- Configurar el idioma de acciones de Authentication (verificación/recuperación) y localización de errores visibles; los códigos técnicos no cambian.
- Analytics: eventos estables, idioma como atributo permitido sin datos personales; `language_selected` tras elección efectiva y `language_changed` tras guardar el cambio. Las vistas no se duplican por una reconstrucción para traducir.
- Panel: ver/modificar preferencia con autorización y auditar cambios administrativos cuando corresponda. La localización no altera roles, suscripciones, precios o fórmulas deportivas.

## Fases y aceptación

1. **Diseño/base:** selector y catálogo de textos, navegación inicial, idioma local persistido y cambio desde Perfil. Esta parte puede funcionar sin Firebase.
2. **Cuenta/API:** migración, contratos, sincronización app/web y mensajes del backend.
3. **Firebase/avisos:** Auth, FCM, correos, bandeja y medición en el idioma elegido.
4. **Calidad/lanzamiento:** revisión humana de las seis traducciones y pruebas de todos los recorridos. Idioma no soportado, sin conexión, cierre/reapertura, cambio con sesión activa y textos al 160 %; no mezclar español residual, no cambiar probabilidades/importes y no duplicar avisos.

Relacionado: `FIREBASE_INTEGRACION_CON_BACKEND_20261011.md`, `PANTALLAS_BIENVENIDA_INICIO_VIP_20261011.md` y `harness/tareas.md`.
