# Actualizaciones desde el panel

1. Aplicar `db/072_mobile_updates.sql` al publicar la API.
2. Publicar una nueva compilación de Flutter que incluya esta comprobación. Las aplicaciones anteriores a esta integración no pueden recibir el bloqueo.
3. En `/control/configuracion-app`, registrar la última versión `X.Y.Z+BUILD` y la ficha real de cada tienda. No usar los enlaces de la imagen de referencia.
4. Mantener el mínimo en `0` para avisos opcionales. Subirlo para bloquear solo builds anteriores al mínimo. El interruptor exige la última versión disponible en ambas plataformas; los mínimos se aplican independientemente del interruptor.
5. Activar la obligación solo cuando la actualización esté disponible para los usuarios afectados, considerando despliegues graduales y países.

La app consulta `/mobile/v1/config` al arrancar y al reanudar. Una consulta fallida permite continuar al inicio; si ya estaba mostrando una obligación, la conserva. Al volver de la tienda sin actualizar, el aviso obligatorio sigue abierto. El aviso opcional aparece una sola vez por sesión y puede cerrarse con «Más tarde» o retroceso. La apertura de tienda no cierra el aviso obligatorio.

La versión instalada se obtiene del paquete nativo, incluyendo las opciones de build de CI que pueden sobreescribir `pubspec.yaml`. Los builds deben ser enteros crecientes por plataforma. Los mensajes se traducen a los seis idiomas de la aplicación.

La configuración inicial está desactivada, sin versiones ni enlaces inventados. Antes de aplicar la migración, la API devuelve esa configuración inicial. Los cambios del panel requieren autenticación, comprobación CSRF y quedan auditados.
