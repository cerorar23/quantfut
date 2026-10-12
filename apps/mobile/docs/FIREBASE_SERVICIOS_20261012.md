# Firebase en QuantFut — estado del 12 de octubre de 2026

Proyecto: `pronosticos-deportivos-85ffa`. Apps activas: QuantFut Android e iOS,
ambas con identificador `com.saptain.quantfut`. Los registros de ejemplo se
eliminaron por petición del usuario. FastAPI/Postgres conserva la autoridad
sobre cuentas, VIP, monedas, referidos y contenido deportivo.

## Instalado y configurado

| Servicio | Implementación | Estado operativo |
| --- | --- | --- |
| Authentication / Google | Proveedor Google habilitado, clientes OAuth, huellas Android de desarrollo, acceso inicial, restauración y vinculación explícita con cuenta anterior | Preparado; acceso en app y API cerrado hasta publicar documentos legales |
| Cloud Messaging | Preferencias, permiso del dispositivo, renovación/desvinculación de token, recepción, apertura interna y bandeja autenticada; cola y emisor de servidor | Preparado; entrega real pendiente de prueba tras habilitar acceso; campañas y tarea periódica sin activar |
| Analytics | Pantallas visibles y eventos, consentimiento separado, publicidad personalizada desactivada | Integrado; recopilación desactivada por defecto |
| Crashlytics | Fallos Flutter/nativos, recursos Android y archivo de configuración para símbolos iOS | Integrado; recopilación desactivada por defecto; fallo controlado pendiente en dispositivo de prueba |
| Performance | Plugin nativo y trazas de peticiones de API sin identificadores sensibles en el nombre | Integrado; recopilación desactivada por defecto |
| Remote Config | Valores locales, descarga con tiempo límite, banners y presentación de mantenimiento | Publicado; Google y URLs legales desactivados/vacíos; versión mínima reservada sin bloqueo obligatorio |
| App Check | Play Integrity para distribución Android, proveedor de depuración registrado para emulator-5556, App Attest/DeviceCheck previsto en iOS | Observación; no se exige todavía en producción |

Los paquetes exactos quedan fijados en `pubspec.lock`. El servidor usa
`firebase-admin==7.7.0`. Firestore, Storage, Functions y experimentos de la fase
P2 son opcionales en el plan revisado; no se activaron ni se cambió la facturación.
Las dependencias de Firestore/Storage incluidas por el Admin SDK no crean bases
de datos ni buckets.

## Identidad y controles de acceso

El ID token Firebase se envía con `X-QF-Identity: firebase`, se verifica contra
el proyecto y se comprueba su revocación. Un token Firebase inválido no se
interpreta como una sesión anterior. Las cuentas anteriores conservan su ID,
permisos, saldo e historial: compartir correo no basta para vincularlas; se
exige demostrar el acceso a la cuenta existente. Google no recibe ni sustituye
su contraseña anterior en el backend.

La aceptación de documentos se guarda con versión. No se registran borradores
como documentos vigentes. Las preferencias de medición, diagnóstico y avisos
son independientes y comienzan desactivadas. El selector admite seis idiomas
en el acceso y conserva la preferencia; la traducción completa del resto de la
app sigue pendiente.

Las notificaciones usan textos genéricos y un identificador de partido validado.
No transportan selecciones VIP, credenciales ni URLs arbitrarias. Al abrirlas,
el servidor vuelve a comprobar los permisos del contenido. La cola comprueba
propietario, preferencias y caducidad; la entrega puede repetirse tras un fallo
de confirmación y utiliza un identificador estable. No promete entrega exacta.

## Despliegue del servidor

El usuario autorizó expresamente crear la cuenta de servicio y su clave privada,
y después desplegar la integración con respaldo y reversión. Cuenta:
`quantfut-backend@pronosticos-deportivos-85ffa.iam.gserviceaccount.com`.
Roles: lectura de Authentication y envío de Cloud Messaging.

Se instaló el SDK y se aplicó `db/058_firebase.sql`, con seis tablas de
identidad, consentimientos, preferencias, dispositivos, bandeja y cola. El
despliegue recreó únicamente la API; el resto de las secciones de Compose se
conservó. El paquete se preparó sobre la imagen y módulos reales del servidor,
sin incluir cambios deportivos de otras sesiones.

La clave queda fuera del repositorio en
`/home/qf/.config/quantfut/firebase-backend.json`, con permisos privados, y se
monta en la API como solo lectura en `/run/secrets/quantfut-firebase.json`.
No se distribuye con Flutter ni con el paquete de código. Los archivos locales
de credenciales y operaciones están ignorados por Git.

Respaldo y paquete: `/home/qf/quantfut/releases/firebase-backend-20261012`.
Se guardaron Compose, esquema anterior de cuentas e imagen previa. El script
revierte Compose e imagen si falla el arranque. La migración es aditiva y permite
contraseñas nulas para futuras cuentas Google; no se habilitaron altas nuevas.
Una retirada completa de tablas requeriría comprobar primero si contienen datos.

El checkout del VPS es anterior a algunos módulos ya presentes en la imagen
activa, entre ellos contenido móvil y recompensas. La comprobación para guardar
fuentes allí se detuvo antes de escribir. El paquete conserva las ocho fuentes
exactas y la migración. Para futuras actualizaciones, partir de la imagen vigente
o reconciliar antes todo el código desplegado; reconstruir directamente desde
ese checkout antiguo perdería funciones que ya estaban instaladas antes de Firebase.

Configuración efectiva:

```text
FIREBASE_PROJECT_ID=pronosticos-deportivos-85ffa
FIREBASE_AUTH_ENABLED=0
FIREBASE_APPCHECK_ENFORCE=0
qf_google_auth_enabled=false
qf_terms_url=""
qf_privacy_url=""
```

## Validación realizada

- Análisis Flutter limpio; 38 pruebas aprobadas.
- APK Android compilado e instalado en emulator-5556. Firebase se inicializa;
  calendario real con 43 enfrentamientos; navegación y preferencias comprobadas.
- Medición, diagnóstico y notificaciones desactivados al entrar en preferencias.
- Tras registrar el emulador, arranque sin fallo de intercambio de App Check,
  excepción Android fatal ni excepción Flutter sin manejar en la observación.
- 11 pruebas específicas Firebase aprobadas. Arnés completo: 924 aprobadas,
  21 omitidas y dos advertencias; Docker no disponible localmente.
- Ocho escenarios de vínculo ejecutados sobre PostgreSQL real, en esquema
  aislado y con reversión: consentimiento, alta/restauración, protección de cuenta
  anterior, vinculación conservando contraseña, conflictos, suspensión y ausencia
  de duplicados. No modificaron filas comerciales de producción.
- SDK/credencial del servidor comprobados mediante lectura de una identidad
  inexistente, sin descargar cuentas reales. Seis tablas presentes; dependencias
  compatibles. Configuración y calendario HTTPS responden 200; preferencias y
  avisos anónimos responden 401; alta Google cerrada responde 503.

Evidencia sin secretos: [validación](validation/firebase_services_20261012/).
No se ha probado todavía el acceso Google de una persona ni la entrega de un
aviso real. No se ha compilado ni ejecutado iOS.

## Lo siguiente

1. Finalizar y publicar términos/privacidad, comprobar las URLs y alinear la
   versión de consentimiento del cliente/servidor con los documentos vigentes.
2. Habilitar Google de forma coordinada en servidor y Remote Config; comprobar
   alta, cancelación, reapertura, vínculo con cuenta existente y cierre de sesión.
3. Probar avisos reales con una cuenta/dispositivo de prueba y preferencias
   elegidas explícitamente; después conectar eventos y tarea de envío.
4. Preparar firma Android de distribución y registrar sus huellas. Validar
   Play Integrity antes de exigir App Check.
5. En Mac, instalar Pods, compilar iOS, firmar, configurar equipo Apple y cargar
   clave APNs. El usuario confirmó que aún no dispone de Apple Developer/APNs.

Fuentes de implementación: [Flutter](https://firebase.google.com/docs/flutter/setup?hl=es-419),
[Admin SDK](https://firebase.google.com/docs/admin/setup?hl=es-419),
[App Check para backend propio](https://firebase.google.com/docs/app-check/custom-resource-backend?hl=es-419).
