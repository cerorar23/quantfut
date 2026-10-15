# Meta y compras: lo que hace el titular en las consolas

Diseño: `docs/superpowers/specs/2026-10-15-meta-compras-design.md`. El código ya está; sin estos pasos
todo queda apagado (`STORE_PURCHASES_ENABLED=0`, `META_CAPI_ENABLED=0`, `QF_META_ENABLED` sin definir).

## Meta (developers.facebook.com y Events Manager)
1. Crear la app de Meta (tipo «Empresa») y añadir la plataforma Android: paquete
   `com.saptain.quantfut`, clase `com.saptain.quantfut.MainActivity`, hashes de la clave de
   firma (debug y la de Play App Signing; ver `FIRMA_ANDROID.md`).
2. Copiar App ID y Client Token a `apps/mobile/android/meta.properties` (plantilla
   `meta.properties.example`) y a `ios/Flutter/Meta.xcconfig`. Compilar con
   `--dart-define=QF_META_ENABLED=true`.
3. Configuración básica → tarjeta Android (y luego iOS): **desactivar el registro automático de
   compras en la aplicación**. Las compras las manda el servidor.
4. Events Manager: crear o elegir un dataset y **vincular la app** (Configuración → Fuentes de datos).
5. Business Manager → Usuarios del sistema: crear uno, darle el dataset y generar un token con
   permiso `ads_management`. Ponerlo SOLO en el `.env` del servidor como `META_CAPI_TOKEN`, con
   `META_DATASET_ID`. No pegarlo en el chat.
6. Probar: Events Manager → Probar eventos → copiar el código a `META_TEST_EVENT_CODE`, activar
   `META_CAPI_ENABLED=1` y comprobar `CompleteRegistration`, `Purchase`, `Subscribe` y `SpentCredits`,
   y la calidad de coincidencia de cada uno. Vaciar el código después.
7. Revisar si los anuncios necesitan autorización de Meta por estar relacionados con apuestas.

## Google Play Console
1. Subir un AAB a **Pruebas internas** y añadir tu cuenta como tester y como **tester de licencias**
   (Configuración → Pruebas de licencias): así las compras no se cobran.
2. Monetizar → Suscripciones: crear `quantfut_plus` con planes base `plus-1m` (mensual), `plus-3m`
   (cada 3 meses) y `plus-6m` (cada 6 meses), renovación automática, sin prueba gratis, con precios.
3. Google Cloud (mismo proyecto que Play): crear una cuenta de servicio, descargar su JSON y en
   Play Console → Usuarios y permisos invitarla con «Ver datos financieros» y «Gestionar pedidos y
   suscripciones». El JSON va al servidor (`PLAY_SERVICE_ACCOUNT_FILE`), nunca al repo.
4. Pub/Sub: crear el tema, dar permiso de publicación a
   `google-play-developer-notifications@system.gserviceaccount.com`, crear una suscripción push a
   `https://pronosticosdeportivos.pro/app/v1/compras/google/rtdn` con autenticación (cuenta de servicio =
   `PLAY_RTDN_SERVICE_ACCOUNT`, audiencia = `PLAY_RTDN_AUDIENCE`), y en Play Console → Monetización →
   configurar el tema en «Notificaciones en tiempo real».
5. Contenido de la app → Seguridad de los datos: declarar correo, nombre, ID de usuario, ID de
   dispositivo/publicidad, historial de compras, interacciones en la app y diagnósticos; compartidos con
   Meta para publicidad/analítica; cifrados en tránsito; borrables a petición. Declaración del ID de
   publicidad: sí, para analítica y publicidad.
6. Activar en el servidor: `STORE_PURCHASES_ENABLED=1` (y recrear solo el contenedor de la API).

## Apple (cuando exista la cuenta)
1. App Store Connect → grupo de suscripción «QuantFut Plus» con `quantfut_plus_1m`, `_3m`, `_6m`.
2. Claves → Compras dentro de la app: generar la `.p8`, anotar Key ID e Issuer ID.
3. App Store Server Notifications V2 → URL `https://pronosticosdeportivos.pro/app/v1/compras/apple/notificaciones`.
4. Descargar `AppleRootCA-G3.cer` de apple.com/certificateauthority a `APPLE_ROOT_CERTS_DIR`.
5. En Xcode (Mac): registrar las carpetas `*.lproj/InfoPlist.strings`, compilar y probar ATT.
6. Etiquetas de privacidad equivalentes a la sección de Play.
