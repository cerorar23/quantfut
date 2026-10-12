# QuantFut

Aplicación Flutter conectada a la API real de QuantFut: calendario, pronósticos públicos/VIP, estadísticas, cuenta, monedas y referidos. Estado de integración y activaciones pendientes en [App real, monedas y referidos](docs/APP_REAL_MONEDAS_REFERIDOS_20261011.md). El prototipo anterior se conserva como referencia, fuera de la navegación de producción.

## Entorno

- Flutter 3.47.7 estable y Dart 3.13.5.
- Android SDK API 37, NDK 30.0.16248370, Gradle 9.6.0, AGP 9.4.1 y Kotlin 2.4.0.
- Java 17 o superior compatible con Gradle. En este equipo Flutter detecta el JDK 25 de Android Studio.
- Android mínimo API 24. iOS mínimo 15.0; compilación iOS en macOS con Xcode.

La actualización y sus límites están documentados en [la auditoría](docs/AUDITORIA_STACK.md).

## Firebase

Firebase Core y los servicios P0/P1 están instalados para Android/iOS en
`pronosticos-deportivos-85ffa`; el arranque lo inicializa por defecto.
El nombre visible es QuantFut y ambos identificadores son
`com.saptain.quantfut`. Instalación, herramientas locales y
pasos de conexión en [Firebase: instalación base](docs/FIREBASE_INSTALACION_20261012.md).
Google, avisos, medición, diagnóstico, rendimiento, Remote Config y App Check
están integrados; la API del servidor también está desplegada. Google permanece
cerrado hasta publicar documentos legales y los servicios opcionales requieren
elección del usuario. Validación y pendientes en
[Firebase: servicios y servidor](docs/FIREBASE_SERVICIOS_20261012.md).

## Ejecutar y comprobar

Desde esta carpeta, con Flutter en PATH:

```sh
flutter pub get
flutter analyze
flutter test
flutter run
```

En este equipo Windows, si Flutter aún no está en PATH, usa `C:\flutter\bin\flutter.bat` en lugar de `flutter`.

```sh
flutter pub outdated
flutter build apk --debug
```

Mantén pubspec.lock para reproducir las versiones resueltas. android/local.properties es específico de cada equipo y no debe compartirse como configuración portable.

## Compilar iOS en Mac

```sh
flutter pub get
cd ios
pod install
cd ..
flutter build ios --release --no-codesign
```

Abre ios/Runner.xcworkspace en Xcode para verificar el simulador, configurar el equipo de desarrollo y firmar. La compilación iOS todavía debe validarse en Mac; no se genera un Podfile.lock ficticio desde Windows.

## Iconos y distribución

```sh
dart run flutter_launcher_icons
```

El generador usa image/batting app icon.png y elimina la transparencia al generar iconos iOS. No se regeneraron los iconos durante esta actualización.

La firma release de Android sigue usando la clave de depuración de la plantilla. Configura una clave privada antes de distribuir. Google Auth está integrado pero su activación espera los documentos legales; los pagos siguen pendientes de elegir proveedor.

## Ver la app en el emulador Android

En Android Studio, abre esta carpeta (la que contiene pubspec.yaml), ve a View > Tool Windows > Device Manager y pulsa el botón de inicio de Medium Phone API 37.0. Selecciona ese dispositivo en la barra superior, abre lib/main.dart y pulsa Run.

También puedes hacerlo desde PowerShell, situado en esta carpeta:

```powershell
& C:\flutter\bin\flutter.bat emulators --launch Medium_Phone_API_37.0
& C:\flutter\bin\flutter.bat run -d emulator-5554
```

El segundo comando debe ejecutarse cuando Android termine de arrancar. flutter run permite recarga de cambios durante el desarrollo. Para el simulador de iPhone necesitas macOS y Xcode.
