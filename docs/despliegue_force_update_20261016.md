# Force Update — despliegue del 16 de octubre de 2026

PR #10 integrado en `main`, commit `b8f74aeac6dd89397ead5d150a89c1c3ebef7908`. Ambos arneses del PR y el arnés de `main` terminaron correctamente.

## Servidor

- Imagen anterior: `quantfut-api-admob:20261015b`.
- Imagen nueva: `quantfut-api-force-update:b8f74ae`, derivada de la anterior y con solo tres archivos: `api/mobile.py`, `api/templates/mobile_config.html` y `comercial/mobile_updates.py`.
- Antes del cambio, los dos archivos existentes eran idénticos a la base del PR. Se conservaron las demás diferencias de producción y la configuración de compras.
- Migración `db/072_mobile_updates.sql` aplicada en una transacción. La tabla no existía previamente; se guardó el esquema anterior.
- Respaldo y manifiesto: `/home/qf/quantfut/releases/force-update-b8f74ae/` (`schema.before.sql`, `docker-compose.before.yml`, `manifest.json`).
- Ensayo de imagen candidata con la configuración real: importación de 108 rutas, nueva ruta de guardado y renderizado del panel correctos.
- API recreada y etiqueta persistida en el compose del servidor. Hashes de los tres archivos verificados contra el commit integrado.
- Worker conserva el contenedor `28330d835ca99f851f037b9b7df9e2494a7f6d77b5c0746161371d433c6f72ba`.
- Modelo activo: `2026.09.27-010508`.
- Verificación pública: `/health` HTTP 200; `/mobile/v1/config` HTTP 200 con los siete campos de actualizaciones. Logs de arranque y solicitudes sin errores.
- Valores iniciales: versiones y enlaces vacíos, mínimos 0, `force_update_app=false`. El titular puede configurarlos en `/control/configuracion-app` cuando la nueva versión esté disponible.

## Reversión

En el servidor, restaurar el compose respaldado y recrear únicamente la API:

```sh
cp /home/qf/quantfut/releases/force-update-b8f74ae/docker-compose.before.yml /home/qf/quantfut/docker-compose.yml
cd /home/qf/quantfut
docker compose up -d --no-deps --no-build api
```

La tabla añadida puede permanecer: la imagen anterior no la utiliza.

## Aplicaciones

Android: compilación firmada `1.0.1+2` terminada y firma verificada. AAB: `apps/mobile/build/app/outputs/bundle/release/app-release.aab`, SHA-256 `276f2dab132018ce48234277cc4197bc0d977eae3b56da3af99f3fc9724ed6b6`.

Comando reproducible: `flutter build appbundle --release --no-pub --build-name=1.0.1 --build-number=2`.

Google Play registra previamente el build 1 en canales interno y producción. El titular autorizó explícitamente la subida y publicación de `com.saptain.quantfut` en los canales interno y producción.

Resultado del intento por API: creación de edit 200, subida del bundle 200 (build y SHA-256 comprobados), preparación de canales interno y producción 200, validación final 403 `The caller does not have permission`. No se ejecutó commit: la versión 2 no está publicada en ninguno de los dos canales. Evidencia operativa: `play-publish-result.txt` en la carpeta de la release del servidor.

Alternativa por navegador: se accedió con la sesión existente de Saptain Ldt. La app muestra revisión en curso de la publicación anterior. Se creó un borrador nuevo de producción (`releases/2/prepare`), pero el selector de archivos no genera el evento necesario para subir el AAB desde la automatización. La biblioteca del borrador no ofrece el paquete nuevo. El borrador permanece abierto para continuar; no se canceló la revisión previa ni se ampliaron permisos.

Pendiente: completar la carga/publicación desde Play Console con la cuenta del titular, o conceder a la cuenta de servicio los permisos adecuados para publicar y reintentar. Esa ampliación de permisos no se realizó.

iOS: el código está integrado, pero este entorno es Windows; no se puede generar ni firmar un IPA sin macOS/Xcode y las credenciales de distribución correspondientes.
