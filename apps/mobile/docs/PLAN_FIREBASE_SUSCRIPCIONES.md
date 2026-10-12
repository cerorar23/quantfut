# GoBet: adaptación a suscripciones de pronósticos deportivos

Fecha: 11 de octubre de 2026. Objetivo confirmado por el usuario: vender suscripciones a pronósticos deportivos. Este documento es una auditoría y una propuesta de implementación; no constituye una integración ya realizada.

## 1. Diagnóstico y alcance

La carpeta activa es `Gobet V1.1`; `maintenance-backup-2026-10-11` es una copia anterior. Se revisaron la estructura de los 62 archivos Dart en `lib`, dependencias, arranque, navegación, acceso, perfil, ajustes, notificaciones, partidos, pronósticos/apuestas de ejemplo, noticias, estadísticas, billetera y configuración Android/iOS. Se contrastaron recomendaciones con documentación oficial de Firebase, tiendas y RevenueCat. La revisión es de código y configuración; no se inspeccionó visualmente cada pantalla en dispositivos.

La aplicación es una plantilla de interfaz. Puede reutilizarse su diseño, tarjetas deportivas, pestañas y gráficos. Todavía faltan datos remotos, identidad real, gestión editorial, venta de suscripciones, permisos premium y medición.

| Área | Evidencia actual | Cambio necesario |
| --- | --- | --- |
| Firebase | `pubspec.yaml` no declara paquetes Firebase; `main.dart:6` ejecuta directamente `runApp` | Configuración por ambiente e inicialización antes de usar servicios |
| Inicio de sesión | `login.dart:196` abre términos sin comprobar email/contraseña | Firebase Auth, validación, estados de carga, errores y sesión |
| Registro | `signup.dart:154` abre Profile directamente | Crear usuario real, verificar correo y completar perfil |
| Contraseñas | No hay `obscureText`, validadores ni controladores de texto en los formularios de acceso | Ocultación funcional, validación y recuperación por enlace seguro |
| Recuperación | `forgot_password.dart:108`, `reset_password.dart:162` y `set_password.dart:134` solo navegan | Enviar y validar la acción de recuperación, confirmar resultado real |
| Rutas | `bottombar.dart:95` crea navegadores por pestaña; onboarding permite entrar sin cuenta | Separar navegación pública, autenticada y premium; resolver enlaces entrantes |
| Perfil | `profile.dart:71` muestra Dylan Dybala y un saldo fijo | Datos reales, plan, vigencia, renovación, preferencias y soporte |
| Notificaciones | `notification.dart:59` abre una lista; no solicita permiso ni obtiene tokens | FCM, preferencias persistentes, bandeja y enlaces al contenido |
| Ajustes | Los switches de `user_profile.dart` solo cambian estado local | Guardar preferencias y conectarlas a funciones reales |
| Tema | `color_notifire.dart:6` cambia un booleano sin `notifyListeners` | Corregir actualización y persistencia del tema |
| Partidos | Equipos, ligas y datos están escritos en widgets | Repositorios de eventos y contenido; API deportiva opcional |
| Apuestas | `match.dart:475–568` muestra importe, pool, premio y botón Bet | Sustituir por detalle de pronóstico y acceso al análisis |
| Estadísticas | `month.dart:441` contiene puntos fijos de gráfica | Agregados calculados desde el historial editorial |
| Billetera | Depósitos/retiros navegan a éxito sin operación remota | Retirar flujo de saldo y crear Mi suscripción e historial de compras |
| Soporte/referidos | Mensajes e invitaciones son demostraciones | Tickets reales; referidos después de validar el producto básico |

Comprobación realizada en esta revisión: `flutter analyze --no-pub` sin incidencias con las reglas actuales; `flutter test --no-pub`, 9 pruebas aprobadas. Cubren arranque, navegación, componentes y temporizador. No prueban compras, autenticación ni protección premium porque esas funciones aún no existen. No se recompiló Android ni se validó iOS en esta revisión; iOS requiere macOS/Xcode.

## 2. Producto recomendado

Primera versión: contenido gratuito de muestra y una membresía premium con dos duraciones, mensual y anual. Ambas duraciones otorgan el mismo acceso. Esto reduce complejidad de permisos y evita confundir niveles de contenido con periodos de cobro. Precios, prueba gratuita y países todavía deben definirse.

Navegación propuesta: Inicio, Pronósticos, Resultados y Mi cuenta. Deportes y ligas funcionan como filtros. Noticias puede convertirse en artículos y análisis complementarios.

| Pantalla actual | Destino propuesto |
| --- | --- |
| Matches / Upcoming / Live / Finished | Agenda y pronósticos próximos, en curso y resueltos |
| Match con botón Bet | Detalle, selección, análisis, autor y bloqueo premium |
| Inplay / My bets / Wins / Loses | Pronósticos guardados y resultados ganados, perdidos o anulados |
| Wallet / Deposit / Withdraw / Add card | Planes, compra, restauración y administración de suscripción |
| Exchange History | Historial de compras, renovaciones y ajustes verificados |
| Statistics | Historial verificable de rendimiento editorial |
| Profile | Cuenta, plan, preferencias, ayuda y eliminación de cuenta |

Cada pronóstico necesita deporte, liga, evento, hora de inicio, autor, título, selección, explicación, nivel de acceso, fecha de publicación y estado. Si el producto utiliza cuotas y unidades, agregar cuota de referencia, fuente, hora de captura y unidades recomendadas. La confianza del analista debe presentarse como evaluación editorial; no como probabilidad calibrada sin evidencia.

Experiencias necesarias: muestras gratuitas, vista previa premium, pantalla de planes, favoritos, filtros, buscador por equipo/competición, historial y ayuda. Mostrar fecha y zona horaria del partido; persistir tiempos UTC. Diferenciar ausencia de contenido, falta de conexión, acceso insuficiente y error de carga.

## 3. Servicios Firebase

| Servicio | Función concreta | Prioridad |
| --- | --- | --- |
| Authentication | Email/contraseña, sesión, verificación, recuperación; Google/Apple cuando se habiliten | Primera versión |
| Cloud Firestore | Perfiles, pronósticos, agenda, preferencias, permisos, resultados y tickets | Primera versión |
| Cloud Functions | Operaciones editoriales, eventos de compra, conciliación, agregados y envío de avisos | Primera versión |
| Cloud Messaging | Nuevos pronósticos, correcciones, recordatorios elegidos por el usuario | Primera versión |
| Analytics | Embudo, consumo, retención, origen y respuesta a campañas | Primera versión |
| Crashlytics | Fallos fatales y errores recuperables, con versión y contexto | Primera versión |
| App Check + Security Rules | Reducir abuso y aplicar acceso por usuario, rol y membresía | Primera versión |
| Cloud Storage | Avatares, portadas y adjuntos necesarios | Según contenido |
| Remote Config | Mensajes, presentación de planes y despliegue gradual de funciones | Después del flujo básico |
| Performance Monitoring | Arranque y trazas de carga de pronósticos y verificación premium | Antes de lanzamiento |
| App Distribution / Emulator Suite | Distribución de pruebas y validación local de reglas/servidor | Desarrollo |
| BigQuery / A/B Testing / In-App Messaging | Cohortes avanzadas, experimentos y mensajes contextuales | Segunda etapa |

Comenzar con Firestore. Realtime Database solo aportaría valor adicional si se incorporan presencia o actualizaciones de muy alta frecuencia. Firebase no suministra marcadores, cuotas ni pronósticos deportivos: se publican desde el panel editorial o se obtienen de un proveedor independiente.

Los paquetes Flutter previstos son `firebase_core`, `firebase_auth`, `cloud_firestore`, `cloud_functions`, `firebase_messaging`, `firebase_analytics`, `firebase_crashlytics` y `firebase_app_check`. Incorporar `firebase_storage`, `firebase_remote_config` y `firebase_performance` según la fase. Resolver versiones compatibles durante la integración; no fijar versiones por memoria. La configuración FlutterFire debe repetirse cuando se agreguen servicios que requieren ajustes nativos. [Configuración oficial para Flutter](https://firebase.google.com/docs/flutter/setup?hl=es-419).

## 4. Identidad y cuenta

**Decisión posterior del usuario (11/10/2026), solo planificar:** registro/acceso
como primera pantalla para personas sin sesión, antes de bienvenida o contenido,
con acceso principal Google, selector de idioma y aceptación de términos y
privacidad según la nueva captura. Sustituye la propuesta de explorar sin cuenta.
No implementar todavía. Requisito y criterios de aceptación en
[el plan de integración actualizado](FIREBASE_INTEGRACION_CON_BACKEND_20261011.md).
Conservar la identidad y los permisos del backend al vincular Firebase.
El resto de los mecanismos previstos (email/contraseña, verificación y
recuperación) se resolverá en la fase de identidad. No guardar contraseñas en
Firestore ni crear un sistema paralelo de tokens Firebase.

Usar un punto central de control de sesión basado en los cambios de Firebase Auth. Al cerrar sesión o cambiar de cuenta: limpiar datos privados en memoria, desvincular tokens de notificación y actualizar la identidad del proveedor de suscripciones. Proteger rutas sensibles y volver a validar permisos al abrir un enlace.

Cuenta debe incluir nombre, foto opcional, deportes favoritos, idioma, zona horaria, permisos de notificación y consentimiento de medición. Añadir cerrar sesión, eliminar cuenta y acceso a soporte. Eliminar una cuenta debe coordinar identidad y datos asociados; aclarar al usuario la administración de su suscripción de tienda, ya que borrar la cuenta no debe asumirse equivalente a cancelarla.

Para el panel administrativo: roles editor, soporte y administrador, permisos mínimos y autenticación reforzada. Los roles se asignan desde servidor. [Firebase Auth para Flutter](https://firebase.google.com/docs/auth/flutter/start?hl=es-419), [claims y permisos](https://firebase.google.com/docs/auth/admin/custom-claims).

## 5. Suscripciones y cobros

Firebase no es un procesador de cobros recurrentes. Para Android/iOS, mi recomendación técnica inicial es evaluar RevenueCat para coordinar compras de las tiendas, restauraciones y eventos de ciclo de vida; Firebase conserva identidad, permisos y contenido. La alternativa es integrar directamente compras nativas y construir verificación y conciliación de Apple/Google en el servidor, con mayor trabajo operativo.

RevenueCat permite sincronizar información de compra con Firestore y enlazar usuarios mediante el UID de Firebase. El proveedor no elimina los requisitos de las tiendas ni sus comisiones. [Integración oficial RevenueCat–Firebase](https://www.revenuecat.com/docs/integrations/third-party-integrations/firebase-integration), [SDK Flutter](https://www.revenuecat.com/docs/getting-started/installation/flutter).

La venta de acceso digital dentro de apps distribuidas por tiendas generalmente utiliza sus mecanismos de compra; existen excepciones y programas por país. Además, el contenido que facilite apuestas puede recibir otra clasificación. Definir países, presentación y alcance antes de fijar el canal de cobro. No asumir que una app de pronósticos queda automáticamente aprobada por cobrar una suscripción. Evitar conservar botones de apostar, gestión de saldos o anuncios/enlaces a casas de apuestas sin revisar su efecto concreto. [Apple: pagos y suscripciones](https://developer.apple.com/app-store/review/guidelines/#in-app-purchase), [Google Play: pagos](https://support.google.com/googleplay/android-developer/answer/9858738?hl=es-419), [Google Play: contenido relacionado con apuestas](https://support.google.com/googleplay/android-developer/answer/9877032).

Si posteriormente existe una web comercial, evaluar un proveedor de cobro web compatible con el negocio y los países. No poner cobro web dentro de la app como supuesto atajo a las políticas de compra digital.

Flujo de acceso: usuario identificado → producto real de tienda → compra → verificación por proveedor/servidor → permiso persistido → contenido premium. El indicador visual de éxito de compra no es autoridad para dar acceso. Nunca permitir que Flutter escriba su propio `isPremium`, vigencia o plan.

Modelar separadamente situación de cobro y permiso de acceso. Estados mínimos: compra pendiente, activa, prueba si existe, cancelación programada, problema de cobro, periodo de gracia, expiración y revocación/reembolso. Cancelación normalmente conserva el acceso hasta el fin del periodo pagado; gracia y reembolsos dependen del estado verificado del proveedor.

Requisitos: restaurar compras, administrar/cancelar desde la tienda correspondiente, detectar doble suscripción, actualizar al volver a la app y resolver compras asociadas a otra cuenta según una política explícita. Usar UID estable y probar cuidadosamente transferencia/restauración para evitar vincular una compra con una cuenta equivocada.

Guardar identificadores del proveedor, producto, ambiente sandbox/producción, periodo, fecha de vencimiento, renovación y última conciliación. Procesar notificaciones del proveedor autenticadas, deduplicadas y tolerantes a eventos fuera de orden. Conciliar periódicamente; un webhook perdido no debe dejar permisos desactualizados indefinidamente. Separar transacciones verificadas del análisis de comportamiento.

Mostrar precio y moneda localizados desde la tienda/proveedor, periodo de facturación, condiciones de renovación, beneficios y administración. Remote Config no es autoridad del precio cobrado ni del derecho premium.

## 6. Protección del contenido premium

Un candado o texto borroso no protege datos descargados. Separar la ficha pública —evento, título y vista previa— del documento privado que contiene selección y análisis cuando esos campos son premium.

Solo usuarios con permiso vigente deben leer documentos privados. Consultar permiso escrito exclusivamente por servidor y comparar la vigencia con tiempo de servidor. Los roles pueden usar claims; para cambios rápidos de membresía conviene verificar estado persistido, porque un claim no se actualiza instantáneamente en tokens ya emitidos. [Condiciones de Firestore](https://firebase.google.com/docs/firestore/security/rules-conditions), [propagación de claims](https://firebase.google.com/docs/auth/admin/custom-claims).

Reglas propuestas: usuario edita únicamente campos permitidos de su perfil y preferencias; guarda favoritos propios; crea tickets limitados. No puede modificar rol, permiso, compras, resultados ni publicaciones. Visitante lee solo fichas públicas publicadas. Editor opera mediante funciones que validan rol, transición de estado y campos. El Admin SDK omite reglas de Firestore: cada función debe verificar autorización y validar entradas por su cuenta.

Los documentos se autorizan completos, por lo que no se deben mezclar campos secretos y públicos esperando que las reglas oculten campos. Las consultas deben ajustarse a las reglas: las reglas no filtran una consulta amplia automáticamente.

Activar App Check con Play Integrity en Android y App Attest/DeviceCheck en Apple según compatibilidad; medir antes de exigirlo en producción y usar proveedor de depuración solo en desarrollo. App Check complementa identidad y permisos, no los reemplaza. [App Check para Flutter](https://firebase.google.com/docs/app-check/flutter/default-providers).

Evitar URLs de descarga públicas permanentes para adjuntos premium. Una vez entregado contenido, no se puede garantizar que el usuario no lo copie o conserve; definir política de caché, desconexión y expiración, limpiar memoria al salir y evitar persistencia premium indiscriminada. No basar autorización en el reloj del teléfono.

## 7. Modelo de datos propuesto

| Colección/ruta | Datos esenciales | Quién escribe |
| --- | --- | --- |
| `users/{uid}` | Perfil, idioma, zona horaria, consentimiento | Usuario con lista limitada de campos; servidor para campos protegidos |
| `users/{uid}/preferences` | Deportes/ligas, categorías de aviso, horario silencioso | Usuario |
| `users/{uid}/devices/{installationId}` | Token FCM, plataforma, permiso, última actividad | Usuario propio mediante validación |
| `users/{uid}/favorites/{predictionId}` | Referencia y fecha | Usuario |
| `users/{uid}/notifications/{id}` | Referencia, tipo, fecha, leído | Servidor; usuario solo estado leído |
| `entitlements/{uid}` | Nivel, vigencia, origen y última verificación | Servidor exclusivamente |
| `subscriptions/{id}` | Estado de compra, producto, tienda, periodo y UID | Servidor exclusivamente |
| `purchaseEvents/{eventId}` | Evento verificado, deduplicación y procesamiento | Servidor exclusivamente |
| `matches/{id}` | Evento, competición, inicio UTC, marcador y fuente | Editor/servidor |
| `predictionCards/{id}` | Título, vista previa, partido, autor, nivel, publicación | Operación editorial validada |
| `predictionContent/{id}` | Selección, análisis y material privado | Operación editorial validada |
| `predictionResults/{id}` | Ganado/perdido/anulado, fuente y cálculo | Servidor/editor autorizado |
| `predictionRevisions/{id}` | Cambio, motivo, autor y fecha | Servidor exclusivamente |
| `performanceSummaries/{id}` | Agregados por periodo/deporte/autor | Servidor |
| `supportTickets/{id}` | UID, asunto, estado, mensajes | Usuario/soporte con permisos |
| `auditLogs/{id}` | Actor, acción, entidad, fecha y correlación | Servidor exclusivamente |

Separar compras, eventos y permisos evita mezclar historia de facturación con acceso actual. No exponer datos de compradores en listados públicos. Crear índices según consultas reales; usar límites y paginación por fecha, deporte, estado y publicación.

## 8. Panel de administración

Hace falta un panel editorial propio. Firebase Console sirve para configurar infraestructura, pero no sustituye el flujo de publicar y controlar pronósticos.

Funciones mínimas: crear borradores, previsualizar, programar publicación, seleccionar nivel gratis/premium, subir portadas, corregir con motivo, resolver resultados y consultar historial. Publicación y programación deben ser idempotentes, con identificador estable y trabajos de recuperación.

Bloquear cambios silenciosos de selección y cuota después del inicio. Conservar versiones y correcciones públicas. No borrar pronósticos fallados del historial. Registrar editor y fecha en cada operación. La programación necesita hora de servidor, no una app abierta.

Soporte debe ver el estado de la suscripción, buscar incidencias y reenviar comprobación de acceso. Un acceso promocional manual, si se permite, debe expirar y dejar auditoría. El rol de soporte no necesita facultad para modificar resultados ni precios.

## 9. Medición del usuario y embudo

Embudo principal: muestra gratuita → registro → pantalla de planes → intento de compra → compra verificada → primer pronóstico premium leído → renovación.

| Evento propuesto | Qué resuelve |
| --- | --- |
| `sign_up`, `login` | Registro y retorno identificados |
| `view_prediction` | Lectura gratuita/premium, autor y deporte |
| `premium_content_locked` | Contenido que provoca intención de compra |
| `paywall_view`, `plan_select` | Exposición de planes y elección |
| `purchase_started`, `purchase_failed`, `purchase_cancelled` | Fricción de compra y abandono voluntario |
| `premium_access_activated`, `first_premium_read` | Activación real y valor recibido |
| `favorite_add` | Interés editorial |
| `notification_permission_result`, `notification_open` | Aceptación y retorno por avisos |
| `support_ticket_created`, `manage_subscription_open` | Problemas y administración |

Estos nombres son un contrato propuesto, no todos son eventos automáticos de Firebase. Preferir eventos recomendados cuando se ajusten a la acción. Registrar vistas explícitamente: los cuatro navegadores de `bottombar.dart` y widgets Offstage no equivalen a cuatro pantallas vistas por el usuario.

Parámetros: deporte, liga, autor, ID de pronóstico, nivel, producto, origen, campaña y versión de presentación. Seleccionar dimensiones útiles; no registrar correos, teléfonos, texto privado premium ni datos de tarjeta. El ID de usuario, si se usa, debe ser interno y sin información personal directa. Respetar consentimiento, plataforma y eliminación.

Fuente de verdad comercial: eventos verificados del proveedor. Analytics puede sufrir duplicación, bloqueo por consentimiento y pérdida de eventos; no usarlo para decidir acceso o conciliar ingresos. Deduplicar compras entre SDK, integración y servidor. [Analytics para Flutter](https://firebase.google.com/docs/analytics/flutter/get-started), [eventos de suscripción en RevenueCat/Firebase](https://www.revenuecat.com/docs/integrations/third-party-integrations/firebase-integration).

Tablero comercial: usuarios activos, conversión por cohorte, suscriptores pagados activos, renovación, cancelación programada, bajas efectivas, reembolsos, ingreso recurrente mensual normalizado y efectivo recibido. MRR no equivale a caja; normalizar anualidades, separar pruebas/accesos gratuitos y acordar moneda y tratamiento de comisiones. Medir retención D1/D7/D30 e interés por autor/deporte. CAC y LTV requieren datos de campañas y cobros además de Firebase.

## 10. Historial y calidad del pronóstico

Es un tablero distinto del tablero comercial. Mostrar muestra total, ganados, perdidos, anulados, pendientes, cuota media y rendimiento por deporte/autor/periodo. Si se muestran unidades y yield, explicar claramente que son resultados teóricos bajo un método publicado, no ganancias reales del usuario.

Para pronósticos simples sin resultados parciales: ganado = unidades × (cuota decimal − 1); perdido = −unidades; anulado = 0. Acierto = ganados / (ganados + perdidos). Yield = resultado neto / unidades arriesgadas de pronósticos liquidados no anulados, aplicando siempre el mismo criterio. Publicar denominador, periodo y tamaño de muestra. Mercados con medias ganancias/pérdidas, combinadas o liquidaciones especiales necesitan reglas adicionales; no aplicarles ciegamente esas fórmulas.

Calcular desde registros de servidor y congelar la selección publicada antes del evento. Guardar fuente del resultado, cuota de referencia y fecha. Una importación deportiva puede proponer resolución, pero necesita validación según las reglas del mercado y posibilidad de corrección auditada. Una tasa de acierto aislada no demuestra rentabilidad.

Para versión inicial, resultados pueden registrarse manualmente desde el panel. La automatización con API deportiva se añade cuando cobertura, licencia de uso, cuotas de consulta y coste estén definidos. Medir retrasos de publicación y de resolución para controlar calidad operativa.

## 11. Notificaciones

Avisos recomendados: nuevo pronóstico en deportes favoritos, cambio relevante, inicio próximo si el usuario lo solicita, resultado disponible y mensajes sobre acceso/cobro verificados. Preferencias separadas para contenido, servicio y promociones, con horarios silenciosos y límites de frecuencia.

Guardar y actualizar tokens por instalación, retirar tokens inválidos y desvincularlos al cambiar de usuario. Solicitar permiso después de explicar su utilidad. En iOS se requiere configuración APNs y capacidades nativas; Android necesita revisar permiso de notificaciones y canales. Manejar primer plano, segundo plano y apertura desde app cerrada. [Configuración FCM Flutter](https://firebase.google.com/docs/cloud-messaging/flutter/get-started?hl=es-419), [recepción de mensajes](https://firebase.google.com/docs/cloud-messaging/flutter/receive-messages).

Enviar referencias de contenido, no la selección premium en el texto de la notificación. Para información privada, seleccionar tokens desde servidor según permiso actual; los temas públicos no son una barrera de acceso. Al abrir el aviso, autenticar y verificar membresía de nuevo.

FCM no sustituye una bandeja persistente ni garantiza entrega inmediata. Usar bandeja dentro de la app como respaldo, deduplicar envíos y registrar publicación, intento de envío y apertura por separado. El servidor usa Admin SDK/HTTP v1; nunca guardar claves privadas de envío dentro de Flutter.

Para compartir pronósticos y abrir enlaces, usar Android App Links y Apple Universal Links sobre dominio propio. Firebase Dynamic Links cerró el 25 de agosto de 2025, por lo que no es una opción para esta integración nueva. [Aviso oficial](https://firebase.google.com/support/dynamic-links-faq).

## 12. Control técnico y operación

Crashlytics debe capturar errores de Flutter y asíncronos, separar fallos fatales de recuperables y añadir versión/flujo sin datos privados. Verificar un fallo de prueba en ambiente de desarrollo. [Guía Flutter](https://firebase.google.com/docs/crashlytics/flutter/get-started).

Performance Monitoring: añadir trazas de carga del feed, apertura del análisis y comprobación de permiso. Flutter no obtiene automáticamente rendimiento de renderizado por cada pantalla; estas mediciones requieren instrumentación concreta. [Guía Performance para Flutter](https://firebase.google.com/docs/perf-mon/flutter/get-started).

Alertas operativas: fallos de compras verificadas, retraso de webhooks, permisos no sincronizados, publicaciones programadas omitidas, envío de avisos fallido y incremento de errores. Logs con IDs de correlación, métricas y procedimientos de conciliación. Respaldos y prueba de restauración de contenido e historial.

Remote Config puede cambiar mensajes, orden de tarjetas, variantes de planes y disponibilidad visual. Un bloqueo de mantenimiento que protege datos o compras necesita aplicarse también en el servidor. No almacenar secretos ni conceder premium con parámetros descargables. [Remote Config Flutter](https://firebase.google.com/docs/remote-config/flutter/get-started).

## 13. Arquitectura Flutter y plataforma

Mantener Provider es viable; no es obligatorio migrar de gestor de estado. Agregar controladores de sesión, feed, compras y preferencias, repositorios y modelos tipados. Separar widgets, acceso a datos y reglas del negocio. Reutilizar tarjetas y extraer componentes comunes; hay pantallas de 500–800 líneas con repetición de datos y diseño.

Organización sugerida: `app`, `core`, `features/auth`, `features/predictions`, `features/subscriptions`, `features/results`, `features/notifications` y `features/profile`. Un enrutador con rutas nombradas y redirecciones hará más fiables enlaces y navegación premium. La protección real permanece en servidor/reglas.

Android: reemplazar `com.example.gobet` por identificador definitivo antes de registrar el proyecto Firebase y los productos; configurar firma release propia. `android/app/build.gradle` todavía usa firma debug para release. El manifiesto principal no declara INTERNET; solo lo declaran debug/profile. Al integrar red, declarar/revisar Internet en release y comprobar permisos aportados por el manifiesto fusionado. Configurar huellas necesarias para proveedores de acceso y App Check.

iOS: reemplazar bundle de ejemplo, configurar equipo y firma, registrar app Firebase y preparar APNs, compras y enlaces universales. Validar plugins añadidos en macOS/Xcode. La configuración actual no demuestra que notificaciones o compras funcionen. Revisar declaraciones de privacidad y datos recogidos por SDKs antes de publicar.

Localización: sustituir textos de plantilla en inglés por recursos traducibles, moneda/precio desde tienda, fechas locales y formatos consistentes. Probar teclado, tamaño de letra, pantallas pequeñas, lector de pantalla y reanudación. Reducir splash fijo y mostrar carga real de sesión/contenido.

## 14. Ambientes, costes y pruebas

Separar Firebase desarrollo, pruebas y producción; compras sandbox y producción también. No conectar pruebas automáticas a datos/cobros reales. Configurar secretos de servidor, región de datos/funciones, accesos mínimos y política de retención antes de crecer.

Presupuestar Firebase, proveedor de suscripciones, tiendas y eventual API deportiva. No dar un precio mensual fijo sin usuarios, sesiones, contenido y tráfico estimados. Storage exige actualmente Blaze, aunque puede haber uso sin coste dentro del plan. [Requisitos de Storage](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024).

Firestore cobra por operaciones y otros componentes según uso. Paginar consultas, limitar suscripciones en tiempo real y mantener agregados precomputados; no descargar todo el historial para cada gráfico. Los navegadores Offstage pueden conservar pantallas montadas: detener listeners innecesarios para evitar lecturas y batería desperdiciadas. [Facturación Firestore](https://firebase.google.com/docs/firestore/pricing).

Crear alertas de presupuesto. Las alertas simples no detienen servicios; la documentación actual contempla topes para ciertos servicios, pero no cubren automáticamente todo el proyecto ni Firestore/Storage. Evaluar qué operaciones se interrumpirían antes de aplicar topes. [Control de facturación](https://firebase.google.com/docs/projects/billing/avoid-surprise-bills).

Pruebas prioritarias: registro/recuperación, reanudación de sesión, visitante y usuario gratuito sin acceso premium, cliente incapaz de cambiar permisos, compra pendiente/fallida/restaurada, renovación, cancelación al fin del periodo, expiración, gracia, reembolso, webhook repetido o fuera de orden, cambio de cuenta, caché/desconexión y notificación que llega cuando ya expiró el acceso. Probar con Emulator Suite y sandboxes de tienda. Verificar publicación única, correcciones auditadas y todos los resultados incluidos en estadísticas.

## 15. Orden de implementación y criterios de salida

| Fase | Entrega | Criterio para avanzar |
| --- | --- | --- |
| 0. Definición | Marca, países, planes, política editorial y canal de distribución | Canal de cobro y alcance compatibles con producto/tiendas |
| 1. Adaptación | Navegación de pronósticos, eliminación de flujos de billetera, modelos y repositorios | App presenta el negocio correcto y maneja carga/error/vacío |
| 2. Cuenta y contenido | Firebase, Auth, perfiles, Firestore, panel editorial mínimo y permisos | Cuenta real; contenido publicado; acceso no manipulable por cliente |
| 3. Venta | Productos de suscripción, verificación, restauración y conciliación | Compras y ciclo completo probados en sandbox; premium depende de estado verificado |
| 4. Seguimiento | FCM, Analytics, Crashlytics, historial de resultados y tablero básico | Eventos coherentes, avisos seguros y resultados reproducibles |
| 5. Lanzamiento | App Check exigido tras pruebas, rendimiento, firma, privacidad y QA de dispositivos | Android/iOS verificados con escenarios de negocio completos |
| 6. Optimización | Cohortes, pruebas A/B, referidos, automatización deportiva y contenido avanzado | Datos suficientes para justificar complejidad adicional |

Primera versión vendible: registro/recuperación, feed gratuito y premium, plan mensual/anual, compra/restauración/administración, control de vigencia, panel de publicación/resultados, notificaciones por preferencias, soporte, medición y monitoreo. El núcleo del producto es vender acceso verificado y entregar contenido con un historial confiable.

Decisiones pendientes para implementar: nombre e identificadores definitivos, países de publicación, cuentas de desarrollador Apple/Google, proyecto Firebase, precios y catálogo, autores y reglas editoriales, alcance de cuotas/unidades, política de acceso al archivo tras vencer y proveedor deportivo si se automatiza. No se necesitan esas respuestas para completar este diagnóstico, pero sí para configurar producción.
