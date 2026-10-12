# Firma Android de distribución

Estado verificado el 2026-10-12: `flutter build apk --release` produce un APK
firmado con el certificado de **QuantFut** (CN=QuantFut, O=Saptain LTD, C=SC), no
con el de depuración. `apksigner verify` lo confirma (esquema v2).

## Cómo funciona

- `android/key.properties` (ignorado por git) apunta al almacén y da alias y
  contraseñas. `android/app/build.gradle` lo lee; **si falta, cualquier compilación
  release se detiene** con un mensaje que remite a este documento.
- **Clave en uso desde el 2026-10-12 (decisión del titular, opción A):** almacén
  `C:/1. llave/llave.jks` (fuera del repositorio), alias `llave`. Su certificado es
  `CN=ely marine, O=NavalQuiz, L=mexico`: **la misma identidad de firma que otro
  proyecto (NavalQuiz)**. Si esa clave se compromete, afecta a ambas apps.
  - SHA-1: `d4c32b3d1d7e09d3de058373739557a2015abc6f`
  - SHA-256: `e03c66cadb0bc0caca43138dc399844790a6893a885c2a47aa00c86fd38b1f34`
- Clave anterior (`quantfut-release.jks`, en `.local/android-release/`, CN=QuantFut,
  O=Saptain LTD): sus contraseñas se perdieron al sobrescribir `key.properties`.
  - SHA-1: `2b507566245504d00f5fadd6d18200248348c00a`
  - SHA-256: `7e089dad09d51ee553f70224593ac97d9f4ef4846739f5515447e75fc4ef8618`
- Las huellas son públicas, no secretas. **Registradas en Firebase** (app Android
  `1:68225142184:android:c4cf6e1ff70dbbb2e0619d`): SHA-1 y SHA-256 de ambas claves y
  la de depuración, necesarias para Google Sign-In y App Check con Play Integrity.
  `google-services.json` incluye el cliente OAuth de la clave en uso.

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
