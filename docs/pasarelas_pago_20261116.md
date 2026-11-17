# Pasarelas de pago en /control (16-nov-2026)

`/control/pasarelas` guarda las claves de Whop y permite probar el cobro con el sandbox de Whop
(<https://docs.whop.com/developer/guides/sandbox>) **sin tocar a los clientes reales**.

## Regla que no se rompe

El sandbox **nunca es global**. Con la tarjeta de prueba `4242 4242 4242 4242` cualquiera obtendría acceso Plus
gratis, y los planes reales no existen en el sandbox. Por eso:

- Todos pagan en **producción**, salvo las cuentas de la lista «Cuentas que pagan en el sandbox».
- Una cuenta de prueba sin claves de sandbox recibe `sandbox_sin_configurar`: **nunca** cae a producción.
- El webhook del sandbox (`/webhooks/whop-sandbox`) usa **su** secreto y solo concede a cuentas de prueba
  (`cuenta_no_autorizada` en otro caso). Un plan de sandbox no vale en el webhook de producción.
- El pago de sandbox da acceso real a la cuenta de prueba (para poder ver el resultado), pero con importe 0, nota
  `whop-sandbox:<pago>`, `whop_payments.modo = 'sandbox'` y **sin** eventos hacia Meta.

## Claves

- Se escriben en la página, por POST con CSRF. Se guardan **cifradas** (AES-GCM, `comercial/cifrado.py`, clave
  maestra `QF_SECRETS_KEY` del servidor), ligadas a proveedor, modo y campo. La página solo muestra los últimos 4
  caracteres; vacío = conservar. Cada cambio queda en `admin_audit` (`pasarela.guardar`, solo nombres de campo).
- Producción sigue funcionando con las variables de entorno (`WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`,
  `WHOP_ACCOUNT_ID`) mientras no se guarden claves aquí; lo guardado en la base tiene prioridad.
- Si una clave guardada no se descifra (clave maestra cambiada), se registra el error y se trata como no guardada.
- No las pegues en el chat ni en el repo: solo en esta pantalla.

## Pasos para probar

1. En <https://sandbox.whop.com> (cuenta y empresa propias): crear una API key de empresa, apuntar el `biz_…` y
   crear un producto con tres planes en USD (19,90 / 30 días, 33,99 / 90 días, 53,99 / 180 días).
2. En el sandbox, añadir un webhook a `https://<dominio>/webhooks/whop-sandbox` con los eventos
   `payment.succeeded`, `refund.created`, `refund.updated`, `membership.updated`, `membership.deactivated`;
   copiar su secreto `ws_…`.
3. En `/control/pasarelas`: pegar API key, secreto y `biz_…` en el bloque **Sandbox**; pegar el `plan_…` de cada plan en
   «Planes del sandbox»; añadir el correo de **tu cuenta de prueba**.
4. Entrar en la web con esa cuenta, elegir plan y pagar con las tarjetas de prueba. Verás «Modo de prueba: no se
   cobra dinero real».
5. Al terminar, **quitar la cuenta** de la lista: vuelve a pagar en producción.

## Tarjetas de prueba

Cualquier fecha futura, CVC de 3 dígitos, cualquier dirección.

| Tarjeta | Qué comprueba | Resultado esperado |
|---|---|---|
| `4242 4242 4242 4242` | Pago aprobado | Webhook → acceso Plus activo y fila en `subscriptions` |
| `4000 0000 0000 0002` | Pago rechazado | Error, sin acceso |
| `5385 3083 6013 5181` | 3D Secure (clave `Checkout1!`) | Vuelta a `/?checkout=1&status=succeeded#checkout` y acceso |
| `4000 0000 0000 0341` | Se guarda y la renovación falla | Primer cobro concede; la renovación fallida no extiende |

También: reembolso desde el panel del sandbox (`refund.*` revoca el periodo) y cancelar la membresía. No funcionan en
sandbox: Apple Pay, Google Pay y payouts.

## Qué no cubre

No se probó contra el sandbox real de Whop (hacen falta las claves del titular): lo automático son pruebas con base
real que simulan sus webhooks. La primera compra de prueba real es el ensayo que falta.
