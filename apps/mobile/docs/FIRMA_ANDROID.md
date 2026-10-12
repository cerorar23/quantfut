# Firma Android de distribución

Estado verificado el 2026-10-12: `flutter build apk --release` produce un APK
firmado con el certificado de **QuantFut** (CN=QuantFut, O=Saptain LTD, C=SC), no
con el de depuración. `apksigner verify` lo confirma (esquema v2).

## Cómo funciona

- `android/key.properties` (ignorado por git) apunta al almacén y da alias y
  contraseñas. `android/app/build.gradle` lo lee; **si falta, cualquier compilación
  release se detiene** con un mensaje que remite a este documento.
- El almacén está en `.local/android-release/quantfut-release.jks` (carpeta ignorada
  por git). Alias: `quantfut-release`.
- Huellas del certificado (públicas, no son secretas):
  - SHA-1: `2b507566245504d00f5fadd6d18200248348c00a`
  - SHA-256: `7e089dad09d51ee553f70224593ac97d9f4ef4846739f5515447e75fc4ef8618`
- La huella SHA-1 de release **ya está registrada** en Firebase (`google-services.json`),
  necesaria para Google Sign-In y App Check con Play Integrity.

## Riesgos y obligaciones

- **La copia única del almacén vive solo en este ordenador.** Si se pierde junto con
  las contraseñas, no se podrán publicar actualizaciones con la misma firma.
  Guardar una copia cifrada del `.jks` y de `key.properties` fuera del equipo
  (gestor de contraseñas o disco cifrado). Nunca subirlos a git.
- Al subir a Google Play, activar **Play App Signing**: Google custodia la clave de
  firma final y la clave local pasa a ser la de *subida*, que se puede restablecer.
  Tras activarlo, registrar también en Firebase la huella SHA-256/SHA-1 que Play
  muestre en «Integridad de la aplicación».

## Compilar

```
cd apps/mobile
flutter pub get
flutter build apk --release
```

R8 reduce el código: las reglas del SDK de Tapjoy están en `android/app/proguard-rules.pro`
(sin ellas el release falla con clases `appset` ausentes).
