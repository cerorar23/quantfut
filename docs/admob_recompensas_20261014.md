# Monedas por videos con recompensa (AdMob) — 2026-10-14

Decisión del usuario: 10 monedas por video, máximo 5 al día, pausa de 3 minutos, día UTC
(reinicio a las 00:00 UTC). Todo se configura en `/control/anuncios`; la app lo lee del servidor.

## Cómo funciona

1. La persona toca «Ver video · +10 monedas» (el botón es el aviso previo de la acción y la recompensa).
2. La app pide `POST /mobile/v1/rewards/ads/ticket`. El servidor comprueba cuenta verificada, anuncios
   activos, ID de bloque para esa plataforma, un único ticket abierto, tope del día UTC y pausa desde el
   último crédito. Devuelve `user_id` (uid del monedero), `nonce` y `unit_id`.
3. La app carga el anuncio y lo muestra con `userId` y `customData=nonce` (verificación del lado del servidor).
4. Google llama a `GET /rewards/callback/admob` con la visualización firmada (ECDSA P-256). El servidor
   verifica la firma con las claves públicas de Google (caché ≤ 24 h), exige un ticket válido de esa
   cuenta y acredita `reward_settings.ad_coins` en `reward_ledger` (`kind='ad'`, `event_key='ad:<tx>'`).
5. La app sondea el saldo hasta 10 s y celebra por la **diferencia** de saldo. Nunca acredita.

## Garantías

- El importe lo decide el servidor; `reward_amount` de Google se ignora.
- Idempotente por `transaction_id`. Un rechazo posterior a una firma válida responde `200` con
  `coins=0` (Google no reintenta); una firma inválida responde `403`; sin claves, `503` (Google reintenta).
- El día de un crédito es el día UTC de emisión del ticket (un ticket de las 23:59 acreditado a las
  00:01 cuenta en su día).
- Un callback ya emitido se acepta aunque el administrador apague los anuncios después.
- Las monedas de anuncios **no** cuentan para validar referidos (no pasan por `reward_provider_events`).
- `reward_ad_events` es inmutable (trigger `deny_mutation`, `db/069`).
- Apagado y en modo prueba por defecto. El modo prueba entrega los bloques de prueba oficiales de Google.

## Archivos

- Backend: `src/qf/api/anuncios.py`, `src/qf/api/anuncios_ssv.py`, `src/qf/api/templates/anuncios.html`,
  `db/069_admob_recompensas.sql`; mensajes traducidos en `src/qf/api/mensajes.py`.
- App: `apps/mobile/lib/product/live_ads.dart` (flujo, pasarela AdMob y tarjeta), integrado en
  `live_rewards.dart`; textos `ads*` y `ledgerAd` en los 6 ARB.
- Pruebas: `tests/test_anuncios*.py` (las marcadas `pg` exigen `QF_TEST_POSTGRES=1` y `db/069` aplicada),
  `apps/mobile/test/rewards_ads_*_test.dart`.

## Para activar anuncios reales (pasos del titular)

1. Crear la app y un bloque «Con recompensa» en AdMob; activar la verificación del lado del servidor del
   bloque con `https://pronosticosdeportivos.pro/rewards/callback/admob`.
2. Aplicar `db/069` en el servidor y desplegar el backend (solo con visto bueno explícito).
3. En `/control/anuncios`: modo prueba **encendido**, activar, IDs de bloque e ID de editor.
4. Probar con la herramienta de prueba de SSV de AdMob y en un teléfono con bloques de prueba.
5. Sustituir el ID de APP de ejemplo de Google por el real en `AndroidManifest.xml` y `Info.plist`.
6. Apagar el modo prueba. **Nunca pulsar anuncios reales propios.**

## Pendiente antes de anuncios reales (sin resolver)

- **Política de apuestas de AdMob / Google Play.** No se pudo confirmar cómo se trata una app de
  pronósticos con cuotas. Preguntar por escrito al soporte de AdMob. Bloquear la categoría de apuestas
  en los controles de AdMob y no enlazar ni afiliar casas de apuestas.
- **Política de privacidad.** El texto publicado dice que la publicidad personalizada no está
  habilitada (`docs/legal/PRIVACIDAD_QUANTFUT.md`). Con AdMob deja de ser cierto: hay que redactar el
  cambio (AdMob, identificador de publicidad, formulario de consentimiento) y publicarlo antes. Es un
  texto legal: lo decide el titular.
- Declaración de ID de publicidad y formulario de seguridad de datos en Play Console.
- Si los bloques de **prueba** disparan el callback SSV y qué trae `ad_unit` (solo número o ID completo;
  el código acepta ambos).
- Los IDs de bloque y de app de prueba de Google se tomaron de su documentación pública; confirmarlos
  al configurar.
- La mediación (Unity Ads, AppLovin) se evaluó y se pospone: primero medir con AdMob solo.

## Lo que se verificó y lo que no

Verificado: pruebas unitarias y de base de datos reales (Postgres local, esquema aislado) del
backend; pruebas de Flutter (233) y `flutter analyze` limpios.
No verificado: panel visto en un navegador (solo prueba de renderizado), anuncios mostrados en un
dispositivo, callback real de Google, despliegue.
