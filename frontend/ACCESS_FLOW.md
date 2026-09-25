# Fase 3 · contrato de acceso y cobro

El recorrido de `Planes` y `Mi espacio` es una demostración: no solicita correo,
contraseña ni tarjeta; no crea usuarios, órdenes, sesiones de servidor o derechos
Plus. El botón de checkout enseña por qué está bloqueado y no envía ninguna
petición de pago. La muestra del criterio sharp debe aprobar su puerta antes
de vender pronósticos.

## Recorrido previsto cuando exista evidencia

1. La persona solicita acceso con su correo. El servidor envía un enlace de
   un solo uso y corta el intento con límite por IP/correo; el navegador nunca
   recibe `SERVICE_TOKEN` ni `ADMIN_TOKEN`.
2. Tras verificar el enlace, el servidor crea una sesión con cookie `HttpOnly`,
   `Secure` y `SameSite=Lax`; el correo no es por sí mismo un derecho Plus.
3. El servidor vuelve a calcular la puerta de CLV y comprueba que la
   publicación sigue activa antes de crear una sesión de checkout. Si falla
   alguna condición, no crea una orden ni ofrece un precio cobrable.
4. El procesador notifica el pago mediante un webhook firmado. El servidor
   verifica la firma sobre el cuerpo original, la identidad del evento, el
   importe, la moneda, el plan y la orden; guarda el evento de forma idempotente
   y solo entonces actualiza la suscripción. El retorno del navegador del
   checkout **nunca** concede acceso.
5. Cada petición de picks Plus requiere sesión vigente, suscripción activa y
   puerta comercial aprobada. La consulta que entrega el pick ocurre después
   de autorizar; el HTML público no contiene picks Plus ocultos por CSS.
6. Cancelación, impago, reembolso y expiración revocan el derecho. El historial
   y la evidencia siguen siendo públicos. No se aceptan ni colocan apuestas.

## Estado de implementación

- Hecho: vistas de demo, puerta de publicación, `SERVICE_TOKEN` exclusivo de
  servidor, `/v1/picks` protegido para el futuro backend web, y auditoría
  interna por liga en `/control` y `/admin/shadow-audit`.
- Pendiente de elección de proveedor y validación: envío de correo, sesiones
  reales, tablas de usuarios/suscripciones/órdenes, checkout y webhook.
- Regla de despliegue: ninguna ruta de alta o cobro real se habilita mientras
  la puerta comercial no apruebe; no se simula una compra exitosa en público.

## Casos de aceptación antes de cualquier lanzamiento

- Invitado, sesión expirada, pago pendiente/reembolsado y puerta cerrada no
  reciben ni metadatos privados ni contenido Plus.
- Un webhook duplicado no extiende dos veces la suscripción; un webhook con
  firma, importe, moneda, orden o plan incorrectos no produce cambios.
- El retorno de checkout sin webhook confirmado no concede acceso.
- Una caída de la base de datos o de la puerta falla cerrada.
- Las rutas públicas y los archivos JS no incluyen tokens, datos de pago ni
  picks Plus; se comprueba también desde otro navegador sin sesión.
