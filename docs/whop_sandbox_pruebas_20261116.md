# Probar el cobro con el sandbox de Whop (16-nov-2026)

Guía oficial: <https://docs.whop.com/developer/guides/sandbox>. El sandbox no cobra dinero real y **no comparte
nada con producción** (ni cuentas, ni claves, ni productos, ni webhooks). Por eso se prueba en una instancia
aparte: **nunca** apuntes la API de producción al sandbox; sus `plans.whop_plan_id` son los reales.

## Qué hace el código

- `WHOP_API_BASE=https://sandbox-api.whop.com/api/v1` pone al servidor en modo sandbox (`whop.environment()`).
- `GET /app/v1/whop/config` devuelve `environment: "sandbox" | "production"`; el navegador crea
  `WhopElements({ environment: 'sandbox' })` solo cuando es sandbox y muestra «Modo de prueba: no se cobra
  dinero real». En producción nada cambia.
- El acceso lo concede el **webhook** (`/webhooks/whop`), no el navegador: sin webhook configurado el pago se
  completa pero no se activa el acceso. Es lo que más importa probar.

## Pasos (los tres primeros los hace el titular: cuenta y claves son suyas)

1. Crear la cuenta en <https://sandbox.whop.com> y su empresa (`biz_…`).
2. En `https://sandbox.whop.com/dashboard/developer`: crear una **API key** (empresa) y apuntar el `biz_…`.
3. Crear un producto con tres planes recurrentes en USD: 19,90 / 30 días, 33,99 / 90 días y 53,99 / 180 días.
   Apuntar sus `plan_…`.
4. Instancia de prueba (local o de ensayo) con **su propia base de datos** y estas variables:

   ```
   WHOP_API_BASE=https://sandbox-api.whop.com/api/v1
   WHOP_API_KEY=<clave del sandbox>
   WHOP_ACCOUNT_ID=<biz_… del sandbox>
   WHOP_WEBHOOK_SECRET=<ws_… del paso 5>
   ```

   Y en esa base de prueba (no en producción): `UPDATE plans SET whop_plan_id = '<plan_… sandbox>' WHERE plan_code = 'plus_1m'`
   (igual para `plus_3m` y `plus_6m`).
5. Webhook en el sandbox hacia `https://<dirección pública>/webhooks/whop` (en local, un túnel) con los eventos
   `payment.succeeded`, `refund.created`, `refund.updated`, `membership.updated` y `membership.deactivated`.
   Copiar el secreto `ws_…` a `WHOP_WEBHOOK_SECRET`.
6. Abrir la web de la instancia de prueba, crear una cuenta, elegir plan y pagar.

## Casos a recorrer

Tarjetas (cualquier fecha futura, CVC de 3 dígitos, cualquier dirección):

| Tarjeta | Qué comprueba | Resultado esperado |
|---|---|---|
| `4242 4242 4242 4242` | Pago aprobado | Webhook `payment.succeeded` → acceso Plus activo y una fila en `subscriptions` |
| `4000 0000 0000 0002` | Pago rechazado | Mensaje de error, sin acceso, sin suscripción |
| `5385 3083 6013 5181` | 3D Secure (clave `Checkout1!`) | Vuelta a `/?checkout=1&status=succeeded#checkout` y acceso activo |
| `4000 0000 0000 0341` | Se guarda, la renovación falla | Primer cobro concede; la renovación fallida no extiende el acceso |

Además: reembolso desde el panel del sandbox (`refund.*` → se revoca el periodo) y cancelar la membresía
(`membership.*` → se revoca). No funcionan en sandbox: Apple Pay, Google Pay, pagos (payouts) y los trabajos
programados.

## Qué no cubre

El sandbox no prueba el formulario de producción ni la cuenta real de Whop. Tras estas pruebas, una compra real
mínima en producción confirma el de ida y vuelta (decisión del titular: puede costar dinero real).
