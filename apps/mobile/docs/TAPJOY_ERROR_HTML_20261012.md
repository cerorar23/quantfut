# Tapjoy: respuesta HTML mostrada como error (2026-10-12)

La captura del usuario corresponde al flujo Coins → Tapjoy / Unity Offerwall.
El puente Android enviaba `TJError.message` directamente como error del canal y
Flutter mostraba `PlatformException.toString()` en un SnackBar sin límite de
contenido. Una respuesta HTML del SDK podía cubrir la pantalla con código.
Esto explica el texto visible; no acredita el motivo de rechazo de la solicitud
por Tapjoy, que requiere su código de respuesta y una prueba real del proveedor.

El puente ahora transmite códigos estables y, cuando existe, el código numérico
del SDK; no transmite cuerpos HTML, mensajes originales ni URLs. Flutter los
convierte en avisos breves en es/en/pt/fr/it/de. Se distingue falta de ofertas,
configuración incompleta, fallo de carga y espera agotada. Los errores API de
cuenta conservan su mensaje traducido.

Solo se permite una apertura pendiente. Android devuelve el resultado en el
hilo principal, espera `onContentShow` para confirmar apertura, limita la espera
a 45 segundos y evita mostrar contenido que llegue después de ese límite.
`connect` recibe la Activity. La acreditación sigue dependiendo del callback
verificado del servidor.

SDK Android actualizado de 14.4.0 a 14.8.0. Unity documenta mejoras de estabilidad
del contenido web y de interfaz en esa versión, pero no identifica específicamente
este fallo: [changelog oficial](https://docs.unity.com/en-us/grow/offerwall/android/introduction/changelog).

Verificación: 16 pruebas Flutter aprobadas (10 del flujo de ofertas y 6 de
traducciones), análisis del código modificado sin incidencias. Las pruebas
simulan el HTML dentro de un PlatformException, también para un puente antiguo,
en los seis idiomas; comprueban mensajes específicos, reintento y exclusión de
solicitudes duplicadas. El SDK real no se simula como validación comercial.

La caché de Pub estaba incompleta (Sentry y plugins asociados): se restauró con
`flutter pub get`. El primer build iniciado antes de restaurarla falló por
plugins ausentes. No se cambiaron versiones de esas dependencias.

En la primera comprobación, la conexión de logs de BlueStacks agotó el tiempo
de espera y la interacción concurrente impidió reproducirlo sin interferir
con el usuario. Posteriormente se confirmó la apertura de pruebas, como se
detalla en el seguimiento de esta nota. Sigue pendiente acreditar una oferta
real y completar la aprobación comercial.

APK release compilado correctamente (74,1 MB); firma v2 verificada y huella SHA-256 del certificado coincidente con la clave de distribución vigente: `e03c66cadb0bc0caca43138dc399844790a6893a885c2a47aa00c86fd38b1f34`. SDK 14.8.0 y códigos seguros presentes en el APK. Artefacto: `.local/artifacts/QuantFut-ofertas-corregidas-20261012.apk`; SHA-256 del archivo: `60b685b2758b7ade705042fcb7eb81ba72886378549c98e9a7264518964d5f82`. No instalado en BlueStacks ni probado como apertura real.

## Seguimiento: apertura real de pruebas verificada

La nueva captura del usuario ya muestra el aviso breve, pero persistía el fallo de apertura. Los registros del dispositivo (vía `adb shell logcat`, no el comando logcat directo) identificaron `no_currency` a las 22:07:05. En Unity se comprobó que Monedas está Active, self-managed, tasa 1000, que Coins la selecciona y está enlazada a `coins_offerwall`, y que la clave SDK del servidor coincide exactamente con la del dashboard (comparación local sin divulgarla). La cuenta está en revisión y la aplicación No activa, sin ID de Play Store. No había dispositivos de prueba.

Con aprobación explícita del usuario se registró **BlueStacks QuantFut** mediante su ID publicitario. El panel confirmó una fila y, al pulsar Ir en la sesión existente, el SDK abrió Earn Rewards con **Tapjoy Test CPA, 7 monedas**, más la introducción en español. Se confirma que la apertura de pruebas funciona. No se completó la oferta ni se acreditaron monedas; la entrega comercial continúa sujeta a aprobación de Unity y publicación/configuración de tienda. No se volvió a recompilar ni se cambiaron claves, moneda o tarjeta. Captura del registro: `.local/artifacts/tapjoy-dispositivo-prueba-20261012.png`; diagnóstico sin identificadores privados: `.local/artifacts/tapjoy-diagnostico-20261012.json`.

Evidencia visual de apertura del SDK y oferta de prueba: `.local/artifacts/tapjoy-ofertas-abiertas-20261012.jpg`.

## Verificación antes del commit (13-oct-2026)

16 pruebas de ofertas y traducciones aprobadas; `:app:compileReleaseKotlin`
correcto. La caché local había perdido `jni_flutter` y faltaba una dependencia
Maven de `share_plus`: se restauraron con `flutter pub get --enforce-lockfile`
y la compilación con red. No cambiaron `pubspec.yaml` ni `pubspec.lock`.
Se excluyen entornos virtuales y carpetas generadas; el informe automático de
Gradle deja de versionarse, conservado en disco. No se generó ni instaló un
nuevo APK durante esta comprobación.
