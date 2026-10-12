# Firebase: instalación base en Flutter

12 de octubre de 2026. Firebase Core instalado, configurado y comprobado en
Android. El usuario eligió el proyecto `pronosticos-deportivos-85ffa`, completó
el acceso de Google y cambió la identidad de la app a QuantFut.

## Identidad definitiva

| Plataforma | Nombre en Firebase | Identificador | Firebase App ID |
| --- | --- | --- | --- |
| Android | QuantFut (Android) | `com.saptain.quantfut` | `1:68225142184:android:c4cf6e1ff70dbbb2e0619d` |
| iOS | QuantFut (iOS) | `com.saptain.quantfut` | `1:68225142184:ios:27b4ad1feef18adfe0619d` |

Se eliminaron de Firebase, por petición del usuario, los registros anteriores
`gobet (android)` y `gobet (ios)`, ambos con `com.example.gobet`. La lista remota
solo contiene las dos apps QuantFut activas. La configuración Android oficial
se descargó nuevamente y contiene únicamente `com.saptain.quantfut`.

## Instalado y conectado

- Firebase CLI 15.33.0 en `.local/firebase-tools` de la raíz del repositorio.
- FlutterFire CLI 1.4.1 en `.local/flutterfire-pub-cache` de la raíz.
- `firebase_core` 4.15.0, con versiones resueltas en `pubspec.lock`.
- `lib/firebase_options.dart` generado para las dos apps reales del proyecto.
- Android: `google-services.json`, plugin Google Services 4.4.4, aplicación,
  namespace y paquete de MainActivity actualizados.
- iOS: bundle ID y nombre actualizados; `Google-Service-Info.plist` descargado
  y añadido a los recursos de Runner en Xcode.
- `lib/core/firebase_startup.dart` inicializa Firebase antes de abrir la app,
  muestra espera y permite reintentar si falla. Firebase está activo por defecto.

`--dart-define=QF_FIREBASE_ENABLED=false` permite omitir la inicialización en
desarrollo. Las pruebas de navegación instancian la app sin llamar al SDK
nativo; las pruebas del arranque comprueban espera, fallo y reintento.

FastAPI/Postgres siguen siendo la autoridad de permisos, suscripciones, saldo
y pronósticos. Esta fase instala Core; quedan pendientes Google Auth, FCM,
Analytics, Crashlytics, Performance y Remote Config. El acceso actual de la
app conserva su implementación existente.

## Configurar desde PowerShell

Desde `apps/mobile`:

```powershell
.\tool\configure_firebase.ps1 -Login
.\tool\configure_firebase.ps1 -ProjectId pronosticos-deportivos-85ffa -Platforms android,ios
& C:\flutter\bin\flutter.bat run
```

El primer comando solo es necesario si no hay una sesión de Firebase CLI.
El script prepara PATH/PUB_CACHE temporalmente, fija los identificadores
elegidos y genera la configuración oficial. En Windows descarga también el
plist nativo de iOS, que FlutterFire no genera allí. Se puede repetir para
actualizarlo. Este proyecto tiene Android/iOS; la web actual es FastAPI.

Comprobación posterior:

```powershell
& C:\flutter\bin\flutter.bat analyze
& C:\flutter\bin\flutter.bat test
& C:\flutter\bin\flutter.bat build apk --debug
```

iOS requiere Mac/Xcode y CocoaPods. Los identificadores públicos generados
pueden versionarse; claves privadas del Admin SDK, tokens de acceso y cuentas
de servicio deben permanecer fuera del repositorio y de la app.

## Reinstalar las herramientas locales

Desde la raíz del repositorio, con Node y Flutter instalados:

```powershell
npm.cmd install --prefix .local/firebase-tools firebase-tools@15.33.0
$env:PUB_CACHE = Join-Path (Get-Location) '.local\flutterfire-pub-cache'
& C:\flutter\bin\dart.bat pub global activate flutterfire_cli 1.4.1
```

`.local` está excluida de Git. No se requiere instalar globalmente estas CLI.

## Validación

- Análisis Flutter sin incidencias; 35 pruebas aprobadas (32 existentes y
  tres del arranque de Firebase).
- Android debug compilado e instalado como `com.saptain.quantfut` en
  `emulator-5556`. Registro nativo: `FirebaseApp initialization successful`.
  La app superó el arranque y abrió el calendario con datos reales.
- APK: `build/app/outputs/flutter-apk/app-debug.apk`.
- Configuración Android e iOS comprobada: proyecto, identificador y Firebase
  App ID coinciden con las apps QuantFut.
- Arnés del repositorio: 911 pruebas aprobadas, 21 omitidas y una advertencia.
  Docker no disponible en este entorno para las comprobaciones que lo requieren.
- La configuración iOS está preparada; su compilación y ejecución siguen
  pendientes en Mac. La firma de distribución Android sigue pendiente.

Fuente: [Agregar Firebase a Flutter](https://firebase.google.com/docs/flutter/setup?hl=es-419).
Arquitectura y siguientes fases: [plan de integración](FIREBASE_INTEGRACION_CON_BACKEND_20261011.md).
