# Meta (App Events + Conversions API) y suscripciones en la app — diseño

Fecha: 2026-10-15. Aprobado por el usuario en el chat, sección a sección, en este orden:

1. Cobro en la app: **suscripción renovable** de Google Play Billing y StoreKit, **sin prueba gratis**.
   Esto convierte a Google Play y a App Store en el procesador de pago **de la app** (la web sigue pendiente).
2. Seguimiento (Analytics, diagnóstico y Meta): **encendido por defecto en todo el mundo**, desactivable
   en Perfil. El usuario asume el riesgo RGPD en la UE (Meta exige consentimiento previo en la UE según su
   propia guía de mejores prácticas); queda registrado en `harness/progreso.md`.
3. Arquitectura **A: el servidor es la única fuente de los eventos de valor**. El SDK solo registra lo que
   únicamente conoce la app.
4. Mapa de eventos estándar de la sección 3 de este documento.

Fuera de alcance: Google Sign-In (ya implementado y activo desde el 12-oct; solo falta la prueba con
cuenta real), cobro web, RevenueCat, App Events API `/{app-id}/activities` (Meta: «ya no la recomendamos
para integraciones nuevas»), deduplicación SDK↔servidor (no se necesita porque ningún evento sale de los
dos lados).

## Objetivo y éxito

- Vender Plus dentro de la app con acceso decidido **solo** por el servidor tras verificar con la tienda.
- Mandar a Meta instalaciones, registro, embudo y compras con el importe real, con la mayor calidad de
  coincidencia posible usando solo datos que ya tenemos.

Éxito: (a) compra, renovación, cancelación y reembolso en el sandbox de Play reflejados en
`subscriptions` sin duplicados; (b) los eventos aparecen en «Probar eventos» de Events Manager con
`em`, `external_id`, `madid` (si hay), `anon_id`, IP y user agent; (c) un usuario que lo desactiva deja
de generar eventos en la app y en el servidor. El EMQ lo calcula Meta: no se promete un 10/10.

## 1. Compras de suscripción

### Productos

| Plan interno (`plans`) | Google Play | App Store |
|---|---|---|
| `plus_1m` (30 d) | suscripción `quantfut_plus`, plan base `plus-1m` (mensual) | grupo «QuantFut Plus», producto `quantfut_plus_1m` |
| `plus_3m` (90 d) | plan base `plus-3m` (trimestral) | `quantfut_plus_3m` |
| `plus_6m` (180 d) | plan base `plus-6m` (semestral) | `quantfut_plus_6m` |

`plans` gana columnas `play_product_id`, `play_base_plan_id`, `apple_product_id` (migración `db/071`).
El precio mostrado y cobrado es el de la tienda (moneda local); `price_cents` sigue siendo la referencia
interna en USD. `club` (de por vida) no se vende en tiendas.

### Vínculo compra ↔ cuenta

La API asigna a cada cuenta un UUID estable (`accounts.store_account_token`, `db/071`). La app lo pasa como
`applicationUserName` de `in_app_purchase`; en Play debe llegar como `obfuscatedExternalAccountId` y en
StoreKit 2 como `appAccountToken`. **Verificar en el código fuente del plugin al escribir el plan** (la
documentación del plugin no lo dice; en Apple el valor debe ser un UUID RFC 4122). Al verificar, el
servidor exige que el identificador devuelto por la tienda sea el de la cuenta autenticada; si no
coincide, responde `compra_de_otra_cuenta` y no concede nada.

### Flujo en la app (`in_app_purchase` ^3.3.1)

1. Escuchar `purchaseStream` desde el arranque (requisito del plugin).
2. Pantalla VIP (`live_vip.dart`): `queryProductDetails` → precios de la tienda. Botón por plan →
   `buyNonConsumable(GooglePlayPurchaseParam/PurchaseParam con applicationUserName)`.
3. Compra en `purchased`/`restored` → `POST /app/v1/compras/verificar` con
   `{store, product_id, purchase_token | jws}`. Estado visible «verificando».
4. Respuesta `concedido` → `completePurchase()` y refresco de permisos. Error transitorio → reintento
   al siguiente arranque (Play reembolsa si no se reconoce en 3 días; iOS re-entrega la transacción).
5. `pending` → pantalla «pendiente». «Restaurar compras» → `restorePurchases()` y el mismo camino.
6. La app nunca escribe `isPremium`, vigencia ni plan.

### Verificación en el servidor (`src/qf/comercial/tiendas/`)

- `google_play.py`: `GET .../purchases/subscriptionsv2/tokens/{token}` con cuenta de servicio
  (`https://www.googleapis.com/auth/androidpublisher`). Usa `subscriptionState`, `latestOrderId`,
  `lineItems[].expiryTime`, `offerDetails.basePlanId`, `externalAccountIdentifiers`,
  `linkedPurchaseToken`, `testPurchase`, `regionCode`. Reconoce (`:acknowledge`) tras conceder.
- `app_store.py`: verificar el JWS de la transacción (cadena `x5c` hasta la raíz de Apple) con la
  App Store Server Library oficial para Python; `Get Transaction Info` como respaldo. JWT ES256 con la
  clave `.p8`. Entornos sandbox/producción separados.
- `compras.py`: lógica común e idempotente.

### Datos (`db/071`, aditiva)

- `store_transactions` (solo inserción; trigger que rechaza UPDATE/DELETE): `store`, `order_id`
  (orderId de Play o transactionId de Apple, **UNIQUE** por tienda), `original_id` (purchaseToken
  inicial / originalTransactionId), `account_id`, `product_id`, `base_plan_id`, `period_start`,
  `period_end`, `price_micros`, `currency`, `region_code`, `environment` (`sandbox`/`production`),
  `subscription_id` (FK a la fila concedida), `verified_payload` JSONB, `created_at`.
- Cada cobro verificado nuevo (compra inicial o renovación) → `suscripciones.grant(source='payment',
  price_cents, currency)` con el periodo real de la tienda + fila en `store_transactions` en la misma
  transacción. `order_id` repetido → se devuelve lo ya concedido, sin conceder otra vez.
- Reembolso/revocación de la tienda → `suscripciones.revoke()` de esa fila con el motivo de la tienda.
- Cancelación de la renovación → nada: el acceso dura hasta el fin del periodo pagado.
- No se tocan los triggers de `subscriptions` (`db/043`).

### Notificaciones de la tienda

- Play RTDN: Pub/Sub push → `POST /app/v1/compras/google/rtdn`, autenticado con el token OIDC de
  Pub/Sub (audiencia y cuenta de servicio fijadas en `.env`).
- Apple: App Store Server Notifications V2 → `POST /app/v1/compras/apple/notificaciones`, firma verificada.
- La notificación solo despierta: el servidor **vuelve a consultar a la tienda** y aplica lo verificado.
  Repetidas o desordenadas no cambian el resultado (idempotencia por `order_id`).

### Interruptor

`STORE_PURCHASES_ENABLED` (por defecto 0: falla cerrado, como `ACCOUNTS_ENABLED`). Apagado, los endpoints
responden 503 y la app enseña «compras no disponibles» (lo que hoy muestra `vipPurchasesPending`).

## 2. Meta: SDK y Conversions API

### SDK (`facebook_app_events` ^0.31.0, publicador oddbit.id)

- Android: `facebook_app_id`, `facebook_client_token` en `strings.xml`; `meta-data`
  `com.facebook.sdk.ApplicationId`, `com.facebook.sdk.ClientToken`, `com.facebook.sdk.AutoInitEnabled=false`,
  `com.facebook.sdk.AutoLogAppEventsEnabled=false`. Se conserva el permiso `AD_ID` (ya lo trae AdMob).
- iOS: `FacebookAppID`, `FacebookClientToken`, `FacebookDisplayName`, `CFBundleURLSchemes` `fb{APP_ID}`,
  `FacebookAutoInitEnabled=false`, `FacebookAutoLogAppEventsEnabled=false`, `NSUserTrackingUsageDescription`
  (6 idiomas vía `InfoPlist.strings`). ATT con `app_tracking_transparency` ^2.0.7 tras la primera pantalla.
- Arranque: Dart lee la preferencia (por defecto encendida). Si está encendida: `initializeSdk()`,
  `setAdvertiserTracking(enabled: <ATT en iOS / true en Android>)`, `setAutoLogAppEventsEnabled(true)`,
  `setAdvertiserIdCollectionEnabled(true)`, `activateApp()`. Si está apagada: no se inicializa.
- Tras iniciar sesión: `setUserID(external_id)` y `setUserData(email: ...)`. Al cerrar sesión:
  `clearUserID()` y `clearUserData()`.
- El client token va en la app (diseñado para ello). El token de CAPI **solo** en el `.env` del servidor.
- Panel de Meta (titular): apagar el registro automático de compras («Basic > Settings», tarjeta Android
  y equivalente iOS). Si no, las compras se contarían por el SDK y por el servidor.

### Datos del dispositivo

`POST /app/v1/meta/dispositivo` (autenticado) tras el login y en cada arranque si cambió algo:
`anon_id` (`getAnonymousId()`), `madid` (Android: canal nativo mínimo sobre `AdvertisingIdClient` de
play-services-ads-identifier, ya presente por AdMob; vacío si el usuario limitó/borró el ID. iOS: IDFA
solo con ATT autorizado), `advertiser_tracking_enabled`, `extinfo` (16 posiciones en el orden de Meta,
cadenas vacías donde falte). El servidor añade IP y user agent de la propia petición.
Se guarda en `meta_identities` (operativa, mutable, una fila por cuenta+`anon_id`; `db/071`) y entra en la
limpieza programada de datos operativos (`docs/legal/OPERACION_PRIVACIDAD.md`).

### Conversions API (`src/qf/comercial/meta_capi.py`)

- `POST https://graph.facebook.com/v24.0/{META_DATASET_ID}/events`, `action_source=app`,
  `app_data{advertiser_tracking_enabled, application_tracking_enabled, extinfo}`. La app debe estar
  vinculada al dataset en Events Manager.
- Cola `meta_events` (`event_id` UNIQUE, `payload` JSONB, `status`, `attempts`, `last_error`,
  `sent_at`; `db/071`). Encolar es parte de la misma transacción que el hecho (cuenta creada, cobro
  verificado, desbloqueo). Un trabajo periódico envía en lotes, con reintento exponencial; tres fallos
  seguidos → `telegram.alert()` (canal operativo).
- Si la cuenta tiene la medición desactivada, **no se encola**.
- Variables: `META_CAPI_ENABLED` (0 por defecto), `META_DATASET_ID`, `META_CAPI_TOKEN`,
  `META_TEST_EVENT_CODE` (opcional, para «Probar eventos»).

### `user_data` (normalización de la página «Customer information parameters»)

| Campo | Cifrado | Origen y normalización |
|---|---|---|
| `em` | SHA-256 | correo de la cuenta; recortar espacios, minúsculas |
| `external_id` | SHA-256 | `qf:{account_id}`; el mismo valor que recibe `setUserID` (la app lo obtiene ya cifrado de la API) |
| `fn`, `ln` | SHA-256 | `accounts.display_name` partido por el primer espacio (con una sola palabra, solo `fn`); minúsculas, sin puntuación, UTF-8 |
| `country` | SHA-256 | `regionCode` de la tienda o país de la cuenta; ISO 3166-1 alfa-2 en minúsculas |
| `madid` | no | `meta_identities` |
| `anon_id` | no | `meta_identities` |
| `client_ip_address`, `client_user_agent` | no | última petición de la app guardada en `meta_identities` |

El teléfono no se recoge: no se envía `ph`.

## 3. Mapa de eventos

Criterio: estándar siempre que exista; si el servidor conoce el hecho, sale del servidor; si solo lo sabe
la app, del SDK; nunca de los dos. Límites de la FAQ: 25 parámetros por evento, nombres de 2–40
caracteres, valores ≤100 caracteres, 1.000 nombres de evento por app.

| Acción | Evento | Origen | `event_id` / parámetros |
|---|---|---|---|
| Instalar / abrir | App Install / Activate App | SDK automático | — |
| Crear cuenta | `CompleteRegistration` | servidor | `reg:{account_id}`; `fb_registration_method` = `google`/`email` |
| Terminar la guía (`live_guide`) | `CompleteTutorial` | SDK | `fb_success`=1, `fb_content_id` = tema |
| Abrir análisis de partido o pick | `ViewContent` | SDK | `fb_content_type`=`product`, `fb_content_id`=`match:{id}` |
| Abrir pantalla VIP | `ViewContent` | SDK | `fb_content_type`=`product_group`, `fb_content_id`=`vip` |
| Buscar en la agenda (`home_agenda`) | `Search` | SDK | `fb_search_string` (≤100), `fb_success` |
| Pulsar «Suscribirme» | `InitiateCheckout` | SDK | `fb_content_id` = plan, `fb_currency`, `_valueToSum` = precio tienda, `fb_num_items`=1 |
| Primer cobro verificado | `Subscribe` | servidor | `sub:{order_id}`; `fb_order_id`, `fb_currency`, `_valueToSum` = importe real |
| Cada cobro verificado (incl. el primero y renovaciones) | `Purchase` | servidor | `pur:{order_id}`; `fb_content_id` = plan, `fb_currency`, `_valueToSum`, `fb_num_items`=1 |
| Desbloquear pick con monedas | `SpentCredits` | servidor (libro de monedas) | `spend:{ledger_id}`; `fb_content_id` = pick, `_valueToSum` = monedas |
| Ver video con recompensa | `AdImpression` | SDK | `fb_ad_type`=`rewarded_video` |
| Compartir código de referido | `Invite` (personalizado) | SDK | — |

Descartados por no corresponder a nada de la app: AddToCart, AddToWishlist, AddPaymentInfo, StartTrial,
AchieveLevel, UnlockAchievement, Rate, Contact, Schedule, Donate, FindLocation, SubmitApplication,
CustomizeProduct. Optimización de campañas recomendada: `Subscribe` (conversión) o `Purchase` (valor).

## 4. Privacidad, ajustes y traducciones

- Analytics, diagnóstico (Crashlytics, Performance, Sentry) y Meta: encendidos por defecto en todo el
  mundo; un interruptor por categoría en Perfil → Preferencias (nuevo: «Medición de anuncios (Meta)»,
  que en California funciona como «No compartir»).
- **Una negativa explícita previa se conserva.** Solo se encienden quienes nunca eligieron.
- Límites de plataforma respetados: ATT denegado → sin IDFA y `advertiser_tracking_enabled=0`
  (los eventos siguen sin IDFA); ID de publicidad borrado/limitado en Android → sin `madid`.
- Política y términos (`docs/legal/`, `legal_pages/`): Meta Platforms como proveedor (datos, finalidad,
  transferencia, desactivación); Analytics y diagnóstico pasan a «activo, desactivable»; Google Play y
  Apple como procesadores de pago; matiz CCPA/CPRA sobre «compartir». Versión nueva y
  `CONSENT_VERSION` nueva en servidor y app; el servidor acepta **la anterior y la nueva** durante la
  transición; las cuentas existentes ven un aviso de cambios al abrir la app.
- Traducciones en los 6 idiomas en el mismo cambio (`l10n_add.py`, `mensajes.py`, `InfoPlist.strings`):
  interruptor, aviso de cambios, estados de compra, errores de compra.
- Declaraciones de tienda (titular, con guía): seguridad de los datos y declaración del ID de publicidad
  en Play; etiquetas de privacidad y manifiesto en Apple cuando haya cuenta.

## 5. Pruebas y despliegue

- Python: normalización y hash con los ejemplos de Meta (`(650) 555-1212` → `16505551212`); `extinfo`;
  cola (único, reintentos, sin encolar si desactivado); verificación Play/Apple con respuestas grabadas
  (válida, otra cuenta, prueba, cancelada, reembolsada); RTDN/notificaciones repetidas o desordenadas;
  `grant`/`revoke` con triggers; `db/071` sobre PostgreSQL en esquema aislado.
- Flutter: SDK no arranca con el ajuste apagado; el valor por defecto no pisa un «no»; no hay
  `completePurchase` sin confirmación del servidor; `l10n_test.dart`.
- `harness_check.sh`, `flutter analyze`, `flutter test`, APK release.
- Reales: «Probar eventos» con `META_TEST_EVENT_CODE`; compra sandbox en pista de pruebas internas de
  Play con licencias de prueba. iOS preparado sin probar (sin Mac ni Apple Developer).
- Despliegue: todo apagado (`STORE_PURCHASES_ENABLED=0`, `META_CAPI_ENABLED=0`); a producción **después
  del 1-nov** en un único despliegue de API + versión nueva de la app (consentimiento coordinado),
  siguiendo `DEPLOYS.md`.

## 6. Dependencias del titular

1. Meta: App ID, client token, dataset vinculado a la app, token de CAPI de usuario del sistema (solo al
   `.env` del servidor), apagar el registro automático de compras.
2. Google Play Console: app en pruebas internas, suscripción `quantfut_plus` con 3 planes base y precios,
   cuenta de servicio con acceso a la Play Developer API (JSON al servidor), tema Pub/Sub para RTDN,
   licencias de prueba.
3. Apple (cuando exista la cuenta): clave `.p8`, issuer ID, key ID, productos y URL de notificaciones V2.
4. Políticas: autorización de Meta para anuncios relacionados con apuestas si aplica; revisión legal de
   la política nueva.

## Fuentes consultadas (2026-10-15)

- Meta: getting started Android/iOS, Android SDK getting started, App Events reference, best practices,
  FAQ (límites), Customer information parameters, deduplicación, App Events API (obsoleta para nuevas
  integraciones), Conversions API for App Events.
- pub.dev: `facebook_app_events` 0.31.0, `in_app_purchase` 3.3.1, `app_tracking_transparency` 2.0.7,
  `google_sign_in` 7.2.0.
- Google: `purchases.products.get`, `purchases.subscriptionsv2.get`. Apple: App Store Server API.
