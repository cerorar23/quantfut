# Cobro web con Whop (checkout embebido + webhooks) y Meta con EMQ alto — diseño (2026-10-18)

Decisión del titular (18-oct): procesador de la web = **Whop**, con **checkout embebido + webhooks**; meta: EMQ alto
para campañas de Meta. Docs leídas: Whop (start, checkout element, accept-payments, webhooks, sandbox, quickstart,
pixel, payment/membership objects) y Meta (pixel reference, advanced matching, customer information parameters,
best practices, dedupe).

## Principios
1. **El acceso se concede solo desde el webhook `payment.succeeded`**, nunca desde el navegador (regla de Whop y del repo:
   «el derecho Plus se deriva siempre del servidor»). `onComplete` del checkout solo dispara el Pixel y refresca la sesión.
2. **El servidor crea la `checkout_configuration`** (`POST https://api.whop.com/api/v1/checkout_configurations` con `plan_id`
   y `metadata`), no el navegador: así `qf_account_id` en `metadata` no se puede falsificar. El navegador monta
   `checkoutConfiguration: ch_…` en el elemento `Checkout` de `@whop/elements`.
3. **Idempotencia**: `webhook-id` (entrega al menos una vez) y `payment_id` (un cobro = una concesión).
4. **Dedupe Pixel↔CAPI** por `event_name` + `event_id` (ventana 48 h). `Purchase`: `event_id = pur:<payment_id>`; el navegador
   solo lo conoce tras `onComplete`, así que se usa `purchase:<ch_id>` en ambos lados (el `ch_` existe antes del pago y es
   único por intento).
5. **EMQ**: CAPI web manda `action_source=website`, `event_source_url`, `client_user_agent`, `client_ip_address`, `fbp`, `fbc`,
   `external_id`, `em`, `fn`, `ln` (hasheados salvo ip/ua/fbp/fbc) con los datos capturados al crear el checkout. El Pixel usa
   coincidencia avanzada manual (`fbq('init', id, {em, fn, ln, external_id, country})`, en claro) cuando hay sesión.
6. Respeta `firebase_preferences.ads_measurement` (NULL = activo, decisión del 15-oct) y `META_CAPI_ENABLED`.

## Datos (db/083, aditiva)
- `plans.whop_plan_id` (único parcial).
- `whop_checkouts(checkout_id PK 'ch_…', account_id, plan_code, event_id, fbp, fbc, client_ip, user_agent, source_url, created_at)`.
- `whop_webhooks(webhook_id PK, event_type, received_at)` — idempotencia de entregas.
- `whop_payments(payment_id PK, account_id, plan_code, subscription_id, checkout_id, amount_cents, currency, billing_reason, created_at)`.
- `meta_events.action_source` (`app` por defecto) y `meta_events.web_context JSONB`.

## Piezas
- `src/qf/comercial/whop.py`: firma Standard Webhooks, creación de checkout, aplicación del pago (concede con `grant_store`,
  encola `Purchase`).
- `src/qf/api/whop.py`: `POST /app/v1/whop/checkout` (sesión), `GET /app/v1/whop/config`, `POST /webhooks/whop` (firma).
- `meta_capi.build_event`: soporte web. Endpoint web de Pixel/config.
- Frontend: vista de pedido con `Checkout` embebido; Pixel con `eventID`.

## Fuera de alcance / pendiente de datos del titular
`WHOP_API_KEY`, `WHOP_WEBHOOK_SECRET`, `plan_` de Whop por plan, `META_PIXEL_ID`, `META_DATASET_ID/TOKEN`, aviso de cookies.
El sandbox de Whop **no** está disponible para Elements todavía: la prueba de punta a punta es con dinero real o con el
sandbox de API + webhooks. Reembolsos/cancelaciones: el evento exacto no está documentado en las páginas de eventos leídas
(solo `membership.updated`); se revoca por `membership.updated` con estado `canceled`/`expired` y se confirma con una entrega real.
