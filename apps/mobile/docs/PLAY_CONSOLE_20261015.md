# Google Play — avance por navegador, actualizado el 16 de octubre de 2026

## Identidad y versión

- Cuenta de desarrollador: **Saptain Ldt**, `6518952823410038427`, sesión `ceo@saptain.ru`.
- App: **QuantFut**, `com.saptain.quantfut`, ID de consola `4974486848092741748`.
- Idioma predeterminado: español latinoamericano (`es-419`); descarga gratuita.
- El titular confirmó en el chat las declaraciones de políticas y exportación antes de crearla.
- AAB release generado con la firma configurada: `apps/mobile/build/app/outputs/bundle/release/app-release.aab`.
- Tamaño: 83.865.895 bytes. SHA-256: `e329fe81b28686adbfb99a0d9b327d65090f3d37a279f1091b3b886b5ef3406d`.
- Google aceptó la versión **1 (1.0.0)**, Android API 26+, destino 37, con mapping y símbolos nativos.
- Publicada en **pruebas internas**, segmento `4701408945873506474`. La consola confirmó «Activo» y «Disponible para verificadores internos».
- Enlace de incorporación: https://play.google.com/apps/internaltest/4701408945873506474
- Nombre temporal de Google: `com.saptain.quantfut (unreviewed)` hasta completar ficha y revisión.
- **No publicada en producción**.

## Verificadores y compras de prueba

- Lista propia `QuantFut - Pruebas internas`, con `ceo@saptain.ru`, seleccionada en el segmento interno.
- La misma lista quedó añadida a pruebas de licencia, conservando la lista previa `prueba` y `RESPOND_NORMALLY`.
- El titular autorizó explícitamente el alcance de las pruebas de licencia a todas las apps de la cuenta. Confirmado «Se guardaron los cambios».

## Suscripciones

El titular indicó: **USD 15 / 1 mes, USD 40 / 3 meses, USD 70 / 6 meses, todos los países**.

Producto `quantfut_plus`, nombre **QuantFut Plus**:

| Plan básico | Renovación | Estado | Regiones | Precio en EE. UU. |
|---|---|---|---|---|
| `plus-1m` | mensual automática | Activo | 175 | USD 15,00 |
| `plus-3m` | cada 3 meses automática | Activo | 175 | USD 40,00 |
| `plus-6m` | cada 6 meses automática | Activo | 175 | USD 70,00 |

Sin ofertas ni pruebas gratis. Google calculó las conversiones regionales y los impuestos; redondeó inicialmente EE. UU. a 14,99 / 39,99 / 69,99, que se corrigieron por celda a los importes exactos indicados. Los precios de otras regiones conservan la conversión/redondeo de Google.

Un borrador auxiliar `monthly` quedó **inactivo** al investigar un problema de sincronización del formulario; no es un ID de integración y no debe activarse. La consola asignó a ese borrador la marca de retrocompatibilidad, que habrá que revisar si algún cliente antiguo la necesita.

Beneficio: «Acceso a pronósticos y contenido Plus». Descripción: acceso durante vigencia, renovación automática, sin prueba gratis.

Los precios internos de `db/043_cuentas.sql` siguen siendo 1499 / 3399 / 5399 centavos USD. Esta sesión configuró precios de tienda, sin cambiar la base de datos del servidor.

## Contenido de Play guardado

- Política de privacidad: https://pronosticosdeportivos.pro/legal/privacidad
- Declaraciones guardadas: **contiene anuncios**, **no es gubernamental** y **ninguna función de salud**. El titular confirmó expresamente la declaración de salud.
- Funciones financieras: se declaró únicamente el sistema de recompensas/puntos de la app; no se declararon pagos, cripto, apuestas ni mercados de predicción.
- ID de publicidad: el manifiesto contiene `AD_ID`; se declararon los usos **estadísticas** y **publicidad o marketing**.
- Ficha principal guardada como borrador con descripción corta y completa en español, icono de 512 px y gráfico destacado de 1024×500.
- La ficha sigue incompleta porque Google exige al menos dos capturas actuales. Las imágenes antiguas de GoBet, NBA, inglés y versiones de demostración no representan QuantFut y no deben subirse.

## Seguridad de datos

El formulario quedó completo y guardado como borrador, basado en el código y la política publicada. Declara cifrado en tránsito, OAuth, eliminación total o parcial mediante
`https://pronosticosdeportivos.pro/legal/eliminar-cuenta`, y los datos usados por la cuenta, compras, analítica, estabilidad, publicidad y recompensas. La vista previa muestra como compartidos el ID de usuario, ubicación aproximada, interacciones e identificadores de dispositivo. El guardado final permanece bloqueado hasta terminar «Público objetivo».

## Bloqueos actuales de Play Console

- **Acceso a la app:** Google exige credenciales en inglés para una cuenta de revisión reutilizable y con acceso completo a Plus. Los revisores no pueden crear su propia cuenta, usar una cuenta personal ni depender de una prueba gratuita. Falta crear/proporcionar una cuenta dedicada de prueba; no debe usarse la contraseña personal del titular.
- **Clasificación IARC:** correo `admin@pronosticosdeportivos.pro` y categoría general preparados. Falta aceptar las Condiciones de Uso de IARC antes de continuar el cuestionario.
- **Público objetivo:** pendiente; después permitirá el guardado final de Seguridad de datos.
- **Capturas:** faltan al menos dos capturas actuales de la app.

## Google Cloud y RTDN

- Proyecto autorizado por el titular: `pronosticos-deportivos-85ffa`.
- Cuenta de servicio creada sin roles generales de proyecto: `quantfut-play@pronosticos-deportivos-85ffa.iam.gserviceaccount.com` (ID `115177367541083973915`).
- Play Console le concedió, solo para QuantFut y sin vencimiento, lectura de la app/calidad, vista financiera y administración de pedidos y suscripciones, incluidos reembolsos y cancelaciones. El titular autorizó expresamente ese alcance.
- Google creó la clave JSON `4b20923c544ec09b45a46fcbded7cb7a9a939509` con nombre `pronosticos-deportivos-85ffa-4b20923c544e.json`, pero la descarga no devolvió una ruta y el archivo no aparece en Descargas. La clave existe en Google Cloud y no debe dejarse perdida: falta autorización inmediata para revocarla y generar una sustituta cuya descarga pueda verificarse.
- Tema creado: `projects/pronosticos-deportivos-85ffa/topics/quantfut-play-rtdn`.
- Está preparado, sin guardar, el rol **Publicador de Pub/Sub** para `google-play-developer-notifications@system.gserviceaccount.com`, limitado al tema anterior. Falta confirmación inmediata porque amplía acceso persistente.
- Falta crear la suscripción push autenticada hacia `https://pronosticosdeportivos.pro/app/v1/compras/google/rtdn`, con la misma URL como audiencia, y autorizar la emisión de tokens OIDC como la cuenta de servicio únicamente para ese destino.
- La Google Play Android Developer API sigue deshabilitada. Habilitarla acepta las Condiciones de Servicio de Google APIs y de Google Play Android Developer API, por lo que falta confirmación inmediata del titular.
- No se activaron las compras ni Meta en el servidor. Se requieren RTDN, clave disponible y una compra real de prueba antes de `STORE_PURCHASES_ENABLED=1`.
- Faltan huellas finales de Play en Firebase y el recorrido de instalación/referidos descrito en `harness/tareas.md`.

## Evidencia local

En `documentos/`:

- `quantfut-play-prueba-interna-20261015.jpg`
- `quantfut-play-suscripciones-20261015.jpg`
- `quantfut-play-licencias-20261015.jpg`
- `quantfut-play-privacidad-20261015.jpg`
- `quantfut-play-servicio-activo-20261015.jpg`
- `quantfut-play-clave-creada-20261015.jpg`
- `quantfut-play-ficha-borrador-20261016.jpg`
- `quantfut-play-seguridad-datos-borrador-20261016.jpg`
- `quantfut-iarc-terminos-pendientes-20261016.jpg`
- `quantfut-pubsub-publicador-pendiente-20261016.jpg`
- `quantfut-api-android-publisher-pendiente-20261016.jpg`

### Seguimiento posterior del 16 de octubre

**Producción enviada:** con autorización «hazlo», creada versión de producción en segmento `4697257023945966248`, reutilizando AAB código 1, versión 1.0.0, probado internamente. Países ya seleccionados: 177 + resto del mundo. Notas en es-419 añadidas. Play indicó «Contenido listo para el lanzamiento». Guardados y enviados los 11 cambios, incluida ficha con imágenes y declaraciones. Estado verificado: «Cambios en la etapa de revisión», verificaciones rápidas en curso (hasta 14 min indicados); se remite a revisión al completarlas. Publicación administrada desactivada: el lanzamiento completo queda solicitado, sujeto a aprobación de Google. No afirmar aún disponibilidad pública. Evidencia: `documentos/quantfut-produccion-enviada-revision-20261016.jpg`.

**Capturas subidas y ficha guardada:** con autorización «todo bien subelas», cargadas `01-inicio-ia.png` y `02-pronostico-ia.png` como capturas de teléfono en es-419 (941×1672, aceptadas como 9:16). Se etiquetaron ambas específicamente como creadas/editadas con IA. Play confirmó «Se guardó el cambio. Envíalo a revisión en Descripción general de la publicación». No enviadas aún a revisión ni publicadas en producción. Evidencia: `documentos/quantfut-capturas-subidas-20261016.jpg`. El mínimo obligatorio de dos capturas está satisfecho; la recomendación promocional de cuatro imágenes con lados de al menos 1080 px sigue siendo opcional.

**Recursos de tienda obtenidos:** cuatro capturas actuales reales de BlueStacks (720×1280) y dos composiciones promocionales mediante imagegen en `apps/mobile/docs/play_store/20261016/`. Inicio, detalle, Reto Escalera y Alta Probabilidad; sin datos personales ni anuncios del emulador en el archivo capturado. Propuestas guardadas y revisadas, aún no subidas en esta sesión. Ver README de esa carpeta.

**Compra interna confirmada:** el titular completó el flujo en Pixel 6. Verificación de solo lectura en servidor: transacciones `google_play`, plan `plus_1m`, entorno `sandbox`; registro más reciente 2026-10-16 18:43:31 UTC con suscripción VIP activa al comprobar. Se observan registros anteriores de prueba y periodos cortos de renovación. No se imprimieron identificadores de cuenta, órdenes ni tokens. Flujo instalación Play → Google Sign-In → compra de prueba → verificación servidor → acceso VIP comprobado. Pendientes de publicación: cuenta dedicada/instrucciones de revisión, Público objetivo, cierre de Seguridad de datos y capturas actuales.

**Pantalla VIP desbloqueada:** tras completar el acceso Google, el titular mostró «Compras en preparación». Se verificó `mobile_features.compras.enabled=false`, separado del flag de API. Activado a true y mensaje vacío, verificado en la misma transacción; los tres IDs de planes coinciden con Play. No requiere nueva compilación ni reinicio. Falta cerrar/reabrir la app y comprobar carga de productos y compra de prueba. Reversión: desactivar `mobile_features` para `section='compras'` y restaurar mensaje «Compras en preparación».

**Inicio de sesión de la instalación de Play:** el titular logró instalar en Pixel 6 pero Google Sign-In falló. Se compararon certificados: Firebase tenía solo huellas de desarrollo/carga, faltaban las de distribución de Play. Se agregaron y verificaron las tres SHA-1 y tres SHA-256 devueltas por «Copiar todas las huellas digitales del certificado» de Play, conservando las anteriores. SHA-1: `F4:03:6D:9E:FA:5F:69:FB:68:79:4D:C7:54:27:59:9B:CE:14:0D:2F`, `B2:41:ED:9E:B2:5B:06:65:FA:9A:C9:74:54:87:DC:A4:8A:47:49:BC`, `3D:4B:62:E9:54:9B:6B:A6:28:4C:A9:4F:16:66:54:E1:97:03:07:93`. La configuración incluida en la app ya contiene cliente OAuth web tipo 3. Pendiente reintento real del titular tras propagación. Evidencia: `documentos/quantfut-firebase-firmas-play-20261016.jpg`.

**Integración activada y validada tras «hazlo» del titular:** `STORE_PURCHASES_ENABLED=1`, solo API recreada sin build y con la misma imagen. Respaldo previo a activación: `deployments/play-credentials-20261016/docker-compose.before-enable.yml` en servidor. RTDN autenticado recibido con HTTP **204** (dos mensajes), validando OIDC y endpoint. Consulta real de `quantfut_plus` por Android Publisher API: **200**; `plus-1m`, `plus-3m`, `plus-6m` ACTIVE y `monthly` DRAFT. Aún no se realizó una compra dentro de la app: el titular debe confirmar esa transacción desde Play en su teléfono. Meta no fue activado en esta sesión. Evidencia: `documentos/quantfut-rtdn-validado-20261016.jpg`.

**RTDN configurado:** autorizado y guardado `roles/iam.serviceAccountTokenCreator` para `service-68225142184@gcp-sa-pubsub.iam.gserviceaccount.com` sobre la cuenta de servicio QuantFut Google Play exclusivamente. Creada `quantfut-play-rtdn-push`, entrega push autenticada, cuenta `quantfut-play@pronosticos-deportivos-85ffa.iam.gserviceaccount.com`, endpoint y audiencia `https://pronosticosdeportivos.pro/app/v1/compras/google/rtdn`, retención 7 días y sin vencimiento. Play tiene RTDN habilitado para el tema, solo suscripciones y compras anuladas. Consola confirmó guardado y envío de notificación de prueba.

**API:** montada la clave `/home/qf/.config/quantfut/google-play.json` en `/run/secrets/quantfut-play.json:ro`; configurados `PLAY_SERVICE_ACCOUNT_FILE`, `PLAY_PACKAGE_NAME`, `PLAY_RTDN_AUDIENCE` y `PLAY_RTDN_SERVICE_ACCOUNT`. Recreada solo API con la misma imagen `quantfut-api-admob:20261015b`, sin rebuild ni cambio del worker. Respaldo compose: `/home/qf/quantfut/deployments/play-credentials-20261016/docker-compose.before.yml`. `STORE_PURCHASES_ENABLED=0` explícito. Credencial carga correctamente; consulta exploratoria devolvió 404 (no prueba autorización de compras). RTDN llegó por HTTP al endpoint, pero respondió 503 por `require_store`; autenticación OIDC aún NO validada, porque la dependencia bloquea antes. Pendiente habilitación controlada y compra de prueba. Evidencias: `documentos/quantfut-rtdn-play-configurado-20261016.jpg`, `documentos/quantfut-rtdn-push-creado-20261016.jpg`.

**Pub/Sub desbloqueado con autorización del titular:** se aplicó temporalmente «Permitir todo» solo al proyecto, se guardó `roles/pubsub.publisher` para `google-play-developer-notifications@system.gserviceaccount.com` únicamente en `quantfut-play-rtdn`, y se restauró la herencia original. Verificación final: `Heredar política del elemento superior`, valores permitidos `C03vu1ssf`. La consola confirmó la política IAM del tema actualizada y muestra Publicador de Pub/Sub (1). Evidencias: `documentos/quantfut-dominio-restaurado-20261016.jpg` y `documentos/quantfut-publicador-guardado-20261016.jpg`. Aún falta la suscripción push autenticada, configuración RTDN en Play y pruebas.

**Instalación de credencial:** JSON transferido por SSH al servidor propio, `/home/qf/.config/quantfut/google-play.json`, 2404 bytes, modo `600`. Aún no montado en API ni activadas compras. API actual `quantfut-api-admob:20261015b`; no usar el compose local antiguo. Se preservó el contenedor en ejecución. La política heredada permite solo `C03vu1ssf`; su editor antiguo no admite una excepción por correo. Está preparada SIN APLICAR una anulación temporal solo del proyecto con «Permitir todo», para otorgar el publicador exacto y restaurar inmediatamente la herencia. Requiere confirmación por reducción temporal de protección. Evidencia: `documentos/quantfut-excepcion-dominio-pendiente-20261016.jpg`.

**Credencial recuperada correctamente:** el titular eliminó la clave anterior y creó/descargó una nueva desde su navegador. Se encontró `C:\Users\huye\Downloads\pronosticos-deportivos-85ffa-6b928ede5ec5.json` (2404 bytes). Se verificaron solo metadatos: tipo `service_account`, proyecto correcto, correo `quantfut-play@pronosticos-deportivos-85ffa.iam.gserviceaccount.com`, ID `6b928ede5ec5c78d65ff4f7fc579eca8e703e750` y presencia de clave privada. No se imprimió el secreto ni se copió al repositorio. Pendiente instalarla en servidor mediante `PLAY_SERVICE_ACCOUNT_FILE`, resolver Pub/Sub y probar antes de activar compras.

Actualización tras confirmación explícita del titular: se creó la clave sustituta `424f9e592f9060d591da366a5adcfd70b38d0048`, estado Active, 16-oct-2026. La captura del evento de descarga no devolvió ruta; tampoco aparece el JSON en Descargas (búsqueda por nombre de proyecto/clave). No se generaron más claves. Falta localizar la descarga del navegador antes de instalarla en el servidor. Evidencia: `documentos/quantfut-clave-sustituta-creada-20261016.jpg`.

- IARC guardado: contenido en línea y compras digitales, sin artículos aleatorios. Clasificaciones generadas: Brasil 14+, ESRB Todos, PEGI 3 y resto 3+. Pendiente envío a revisión junto con los demás cambios.
- La activación de Android Publisher API fue solicitada y navegó a métricas; falta comprobar su estado final tras la interrupción.
- Pub/Sub rechazó al publicador de Google Play por `constraints/iam.allowedPolicyMemberDomains`. No se modificó esa protección. RTDN continúa bloqueado.
- La clave perdida `4b20923c544ec09b45a46fcbded7cb7a9a939509` fue revocada. Se verificó que no hay claves activas. La sustituta no se creó: revisión automática exige confirmación explícita en el momento de generar/descargar la nueva credencial. Evidencia: `documentos/quantfut-clave-sustituta-pendiente-20261016.jpg`.
- Se confirmó que Público objetivo exige completar primero Detalles de acceso; por tanto la cuenta dedicada de revisión bloquea también el cierre de Seguridad de datos.
- Ficha conservada como borrador; Google confirmó «Se guardaron los cambios». Continúan faltando las capturas actuales.

La publicación y todos los cambios de consola se realizaron mediante el navegador. La compilación local fue el requisito previo para obtener el AAB; no se modificó código de la app.
