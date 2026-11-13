# Probar un deporte nuevo contra un servidor local (Fase 4 · 4.5)

La app NO necesita producción para ver la pantalla genérica de un deporte del catálogo: se compila apuntando a un
servidor simulado que sirve la configuración con un deporte `golf` y las tres rutas del contrato.

## Cómo apunta la app a otra URL base

`QuantFutApi` lee la URL base de `--dart-define=QF_API_BASE_URL=<url>` (por omisión `https://pronosticosdeportivos.pro`,
`lib/product/live_api.dart`). Sin Firebase hace falta además `--dart-define=QF_FIREBASE_ENABLED=false`: la app salta
el acceso por cuenta y la bienvenida lleva directo a la pantalla principal con el cliente sin sesión.

Desde el emulador de Android, `10.0.2.2` es el equipo anfitrión, pero en la prueba del 13-nov-2026 las conexiones de la app a
`10.0.2.2` se quedaron en `SYN_SENT` aunque `nc` desde `adb shell` sí llegaba. Lo que funcionó: `adb reverse tcp:18765 tcp:18765` y
la app compilada con `QF_API_BASE_URL=http://127.0.0.1:18765`. HTTP en claro funciona en el release sin tocar el manifiesto
(`dart:io` no pasa por la política de tráfico en claro de Android).

## Pasos

```bash
# 1) servidor simulado (escucha en 0.0.0.0:18765; registra las peticiones en $QF_SIM_LOG o en el temporal del sistema)
python tool/servidor_contrato_simulado.py 18765

# 2) opcional: definición de pantallas. Un archivo `tool/pantallas.json` (no lo confirmes) se añade como `pantallas`:
#    {"deporte": {"golf": [{"id":"a","tipo":"aviso","visible":true,"params":{"texto":{"es":"Hola"}}}, {"id":"s","tipo":"seccion","seccion":"partidos","visible":true,"params":{}}]}}

# 3) compilar (release firmado con una llave de prueba propia en android/key.properties, que Git ignora) e instalar
C:\flutter\bin\flutter.bat build apk --release --dart-define=QF_FIREBASE_ENABLED=false --dart-define=QF_API_BASE_URL=http://127.0.0.1:18765
adb -s <emulador> install -r build/app/outputs/flutter-apk/app-release.apk
adb -s <emulador> reverse tcp:18765 tcp:18765   # tras cada reinicio del emulador
```

La llave de prueba NO es la de publicación: `keytool -genkeypair -keystore prueba.jks -alias prueba -keyalg RSA -keysize 2048 -validity 30`
y un `android/key.properties` con `keyAlias`, `keyPassword`, `storeFile`, `storePassword`. No lo confirmes.
El servidor registra `build=<compilación>` en la petición de `/cliente/v1/config`.
