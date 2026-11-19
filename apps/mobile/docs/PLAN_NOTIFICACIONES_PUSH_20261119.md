# Plan de notificaciones push (Android e iOS) — 19-nov-2026

Estado: **aprobado por el titular el 19-nov-2026 (ver §9), sin implementar**. Tope diario cambiado de 3 a 5.

## 1. Qué ya existe (verificado en `main`, 19-nov)

| Pieza | Dónde | Estado |
|---|---|---|
| FCM en la app | `pubspec.yaml` (`firebase_messaging ^16.7.0`), `lib/core/firebase_services.dart` | Pide permiso desde Preferencias, registra el token, `onBackgroundMessage`, `onMessageOpenedApp`, `getInitialMessage`, abre la ficha del partido (`data.route=match`). Auto-init apagado hasta el consentimiento. |
| Android | `AndroidManifest.xml`, `MainActivity.kt` | `POST_NOTIFICATIONS` declarado; **un solo canal** `quantfut_predictions` (IMPORTANCE_DEFAULT) con nombre fijo en español «Avisos de QuantFut»; icono `ic_stat_quantfut`. |
| iOS | `Info.plist`, `Runner.entitlements` | `remote-notification` en background modes, `aps-environment` por variable. Sin probar: falta Mac/Apple Developer (APNs). |
| Servidor | `db/058`, `db/115`, `src/qf/comercial/firebase_notificaciones.py` | `push_devices`, `account_notifications` (bandeja con caducidad), `notification_outbox` con reintentos, filtro por deporte (`push_sports`), baja de tokens `UNREGISTERED`. Envío lo lanza `scripts/firebase_operations.py deliver`. |
| Bandeja en la app | `FirebaseInbox`, filtros por deporte (F3e/F7c) | Hecha. |

**Lo que falta:**

1. **Nadie llama a `enqueue()`**: hoy no se emite ningún aviso (PENDIENTES: «Aviso push al sellar»).
2. El texto es genérico («Nuevo aviso de QuantFut») para todo; no hay tipos de aviso.
3. Un solo canal Android: el usuario no puede silenciar «resultados» sin perder «pick gratis».
4. No hay tope diario, horas de silencio, zona horaria ni agrupación.
5. La app no escucha `onTokenRefresh` y el servidor no limpia tokens viejos de iOS (en iOS no caducan solos).
6. `migración db/115` y API F7c sin desplegar (ver `harness/tareas.md`, F7c).

## 2. Lo que exige la documentación oficial

Fuentes: [FCM Flutter — recibir mensajes](https://firebase.google.com/docs/cloud-messaging/flutter/receive),
[FCM — gestión de tokens](https://firebase.google.com/docs/cloud-messaging/manage-tokens),
[FCM — prioridad Android](https://firebase.google.com/docs/cloud-messaging/android/message-priority),
[FCM — mensajes plegables](https://firebase.google.com/docs/cloud-messaging/customize-messages/collapsible-message-types),
[Android — permiso de notificaciones](https://developer.android.com/develop/ui/views/notifications/notification-permission),
[Android — canales](https://developer.android.com/develop/ui/views/notifications/channels),
[Apple HIG — Notifications](https://developer.apple.com/design/human-interface-guidelines/notifications),
[Apple — payload remoto](https://developer.apple.com/documentation/usernotifications/generating-a-remote-notification),
[App Review Guidelines 4.5.4 y 5.3](https://developer.apple.com/app-store/review/guidelines/),
[Política de Google Play](https://support.google.com/googleplay/android-developer/answer/18258653).

**Permiso**
- Android 13+: las notificaciones vienen **apagadas** al instalar. Pedir el permiso **en contexto** (tras una acción del usuario, p. ej. «Avísame»), no en el primer arranque; mostrar explicación propia antes del diálogo del sistema. En Android 13+ `denied` puede significar «aún no preguntado», así que la app debe **guardar si ya preguntó**.
- iOS: `requestPermission`; existe la autorización **provisional** (llegan en silencio al Centro de notificaciones sin diálogo).
- Apple 4.5.4: las push **no pueden ser obligatorias** para usar la app, ni llevar datos personales o confidenciales; las de **promoción o marketing solo con consentimiento explícito** en la UI y con forma de darse de baja dentro de la app.
- Google Play: las notificaciones del sistema solo para funciones propias de la app; **nada de anuncios** en notificaciones ni imitar alertas del sistema; nada de mensajes no solicitados.

**Android**
- Un **canal por tipo de aviso**. La importancia de un canal **no se puede cambiar** una vez creado (solo nombre y descripción): hay que acertar ahora. Borrar canales queda contado en Ajustes (antispam), así que el canal viejo no se borra a la ligera.
- Ofrecer en Preferencias un acceso a los ajustes del canal (`ACTION_CHANNEL_NOTIFICATION_SETTINGS`).
- Prioridad FCM **alta solo** para avisos visibles y urgentes; si un mensaje alto no acaba en notificación visible, FCM lo degrada.

**iOS**
- Avisos breves, sin el nombre de la app en el texto, sin duplicados del mismo hecho; el **badge solo para no leídos**.
- `thread-id` para agrupar, `interruption-level` (`passive` / `active`; `time-sensitive` solo si el retraso perjudica al usuario y requiere capacidad propia), `relevance-score` para el resumen programado.
- En primer plano no se muestra banner del sistema por defecto: informar dentro de la app sin interrumpir.

**Tokens**
- Guardar token con marca de tiempo, refrescarlo **una vez al mes**, borrar con `UNREGISTERED` / `INVALID_ARGUMENT` (este último solo si el payload era válido), y **limpieza diaria** de dispositivos sin actividad (Android caduca a los 270 días; iOS nunca).

## 3. Principios de QuantFut para los avisos

1. **Solo después del sello.** El aviso se encola al final de `daily.py` (después de predecir → seleccionar → sellar → publicar), sin reordenar nada. Si un aviso sale, el pronóstico ya está en la cadena de hashes. El aviso puede llevar la hora del sello.
2. **Nada protegido en la pantalla de bloqueo.** Los pronósticos VIP nunca aparecen en el texto; solo «ya están sellados». El pick gratis sí puede ir completo (ya es público).
3. **Probabilidad, no presión.** Se muestra la probabilidad del modelo, no frases tipo «banker», «seguro», «confía en el proceso». **Sin cuota en el aviso** (cambia y empuja a apostar). Los resultados se avisan igual si se gana que si se pierde.
4. **Pocos y útiles.** Tope de **5 avisos de contenido al día** por usuario, horas de silencio, y agrupación en vez de ráfagas.
5. **Todo traducido a los 6 idiomas** en el mismo cambio (textos en `src/qf/api/mensajes.py` y nombres de canal en `res/values-*/strings.xml`).

## 4. Catálogo recomendado (7 tipos)

| # | Tipo (`kind`) | Cuándo | Ejemplo (es) | Por defecto | Canal Android (importancia) | iOS | Tope |
|---|---|---|---|---|---|---|---|
| 1 | `pick_gratis` | Tras sellar el pick gratis del día | **⚽ Pick gratis de hoy** · Ecuador – Bolivia: Bolivia +2,5 hándicap · Prob. 71 % · sellado 10:02 | **Sí** | `qf_pick_gratis` (DEFAULT) | `active`, relevancia 0,8 | 1/día |
| 2 | `escalera` | Escalón nuevo sellado **o** resultado del escalón anterior (se fusionan en uno si coinciden) | **🪜 Escalera · escalón 3** · Ya está el siguiente escalón. Escalón 2 acertado. | **Sí** (si sigue la escalera) | `qf_escalera_parley` (DEFAULT) | `active`, `thread-id=escalera` | 1/día |
| 3 | `parley` | Parley del día sellado | **🎯 Parley del día listo** · 3 partidos · prob. conjunta 41 % | **Sí** | `qf_escalera_parley` (DEFAULT) | `active`, `thread-id=parley` | 1/día |
| 4 | `vip_listos` | Solo suscriptores VIP: lote VIP sellado | **👑 Tus 6 pronósticos VIP de hoy están sellados** | **Sí** para VIP | `qf_vip` (DEFAULT) | `active` | 1/día |
| 5 | `resumen_resultados` | Un resumen al día (mañana siguiente) | **Ayer: 3 de 4 acertados** · Pick gratis ✅ · Parley ❌ | No (opcional) | `qf_resultados` (LOW, sin sonido) | `passive`, relevancia 0,3 | 1/día |
| 6 | `inicio_partido` | 30 min antes del inicio de un partido **cuyo pronóstico el usuario desbloqueó** | **Empieza en 30 min** · Flamengo – Athletico-PR | No (opcional) | `qf_partidos` (DEFAULT, prioridad FCM alta) | `active` | 2/día |
| 7 | `recordatorio_monedas` | Asistencia diaria no marcada a las 20:00 locales | **Tu asistencia de hoy sigue pendiente (+N monedas)** | **No** (cuenta como promoción: requiere consentimiento propio, Apple 4.5.4) | `qf_monedas` (LOW) | `passive` | 1/día, nunca si ya la marcó |

Fuera del cálculo del tope (pocos y transaccionales): `cuenta` — suscripción VIP por caducar, pago fallido de la tienda, cuenta verificada. Canal `qf_cuenta` (DEFAULT). Solo bandeja + push, sin marketing.

**No recomendados** (saturan o no encajan): cada gol/marcador en vivo, movimientos de cuota, un aviso por cada pick o por cada resultado, promociones de planes VIP, «racha caliente», avisos de reactivación tipo «te echamos de menos».

## 5. Reglas de envío (servidor)

- **Presupuesto diario**: máximo 5 avisos de contenido (tipos 1-7; `recordatorio_monedas` cuenta) por cuenta y día local. Prioridad si se pasa: `vip_listos` > `pick_gratis` > `escalera` > `parley` > `inicio_partido` > `resumen_resultados` > `recordatorio_monedas`. Lo que no cabe queda **solo en la bandeja**.
- **Horas de silencio**: 22:00–09:00 hora local del dispositivo (configurable por el usuario). Un aviso que cae en silencio se retrasa a las 09:00 si su `expires_at` (inicio del partido) lo permite; si no, solo bandeja.
- **Agrupar**: si en 10 min se sellan varios eventos para la misma cuenta, se envía uno («Pick gratis y parley de hoy listos»).
- **Sin duplicados**: `event_key` estable (ya existe `UNIQUE(account_id,event_key)`); `tag` Android y `apns-collapse-id` = `kind:fecha` para que un reenvío reemplace al anterior.
- **Caducidad**: TTL = hasta el inicio del partido (ya se hace con `expires_at`); un aviso de un partido ya empezado no se envía.
- **Silencio automático**: si una cuenta no abre ninguno de sus últimos 10 avisos, se pasa a solo `resumen_resultados` y se le sugiere en la app revisar sus preferencias (no se apaga nada sin decírselo).
- **Prioridad FCM**: `normal` para todo salvo `inicio_partido` (`high`).
- **Idioma**: el texto lo construye el servidor con el idioma de la cuenta (como hoy), desde `mensajes.py`.

## 6. Experiencia en la app (Flutter)

**Petición del permiso (en contexto, nunca en el primer arranque)**
1. Primer momento natural: al ver el **pick gratis** o al terminar la bienvenida → tarjeta propia «¿Te avisamos cuando se selle el pick gratis de cada día?» con botones *Avísame* / *Ahora no*.
2. Solo con *Avísame* se lanza `requestPermission()`. *Ahora no* → no volver a preguntar en 7 días; tras dos rechazos, solo desde Preferencias.
3. iOS: valorar `provisional: true` en el primer arranque (llegan en silencio al Centro de notificaciones) y pedir la autorización completa en el momento del punto 1.
4. Guardar localmente `push_permiso_preguntado_en` (Android 13+ no distingue «no preguntado» de «denegado»).
5. Botón de campana en la cabecera de la ficha de escalera/parley: «Avisarme de esta escalera» (petición en contexto).

**Preferencias → Avisos** (pantalla F3e ya existe; se amplía)
- Interruptor general + los 7 tipos (con su descripción) + deportes (ya hecho) + horas de silencio.
- `recordatorio_monedas` con texto de consentimiento explícito (Apple 4.5.4).
- Enlace «Ajustes del sistema» a cada canal Android (`ACTION_CHANNEL_NOTIFICATION_SETTINGS`) y a Ajustes de iOS.
- Si el sistema tiene las notificaciones bloqueadas, mostrarlo y ofrecer abrir Ajustes.

**Recepción**
- Primer plano: banner interno discreto (ya existe `foregroundMessage`), sin sonido.
- Toque: ruta según `data.kind` → pick gratis / escalera / parley / VIP / resultados / ficha del partido / monedas. Hoy solo existe `route=match`.
- `onTokenRefresh` → reenviar token al servidor; reenvío mensual del token aunque no cambie.
- Badge iOS = no leídos de la bandeja; ponerlo a 0 al abrir la bandeja.

## 7. Cambios técnicos

**Servidor**
- `db/1xx_push_tipos.sql`: `account_notifications.kind`; `firebase_preferences.push_kinds TEXT[]` (NULL = valores por defecto de la §4), `quiet_start`/`quiet_end`; `push_devices.timezone` (IANA), `last_seen_at`; `notification_outbox.send_after`.
- `firebase_notificaciones.py`: texto por `kind` desde `mensajes.py`; `channel_id`, `tag`, `apns` (`thread-id`, `interruption-level`, `relevance-score`, `apns-collapse-id`) por tipo; presupuesto diario, silencio y agrupación en `enqueue`/`deliver`.
- **Productores** (llamadas a `enqueue`) al final de cada publicación, sin tocar el orden del pipeline y en modo best-effort como `telegram.py`: `publish/alta_prob.py` (pick gratis), `publish/escalera.py`, `publish/parley_v2.py`, lote VIP (`picks.py`), liquidaciones para el resumen, y un cron para `inicio_partido` y `recordatorio_monedas`.
- Limpieza diaria (`firebase_mantenimiento.py`): desactivar dispositivos sin `last_seen_at` en 60 días.
- `/control`: contador de avisos enviados por tipo y tasa de apertura (para medir saturación).

**App**
- `MainActivity.kt`: crear los 7 canales nuevos con nombres desde `strings.xml` en 6 idiomas; conservar `quantfut_predictions` para apps antiguas (no borrarlo hasta que nadie lo use).
- `firebase_services.dart`: `onTokenRefresh`, ruteo por `kind`, timezone en el registro, permiso en contexto.
- Preferencias y tarjeta de petición; textos con `context.l10n` + `tool/l10n_add.py` en 6 idiomas.
- iOS: activar capacidad Push Notifications, clave APNs (.p8) subida a Firebase, `APS_ENVIRONMENT=production` en release. (Bloqueado por Mac + Apple Developer.)

## 8. Fases

| Fase | Contenido | Depende de |
|---|---|---|
| P0 | Desplegar `db/115` + API F7c (pendiente) y validar entrega FCM con un usuario real en Android | Titular |
| P1 | Servidor: `kind`, textos, canales/headers por tipo, presupuesto y silencio, limpieza de tokens, pruebas | P0 |
| P2 | Productores: `pick_gratis`, `escalera`, `parley`, `vip_listos` | P1 |
| P3 | App: 7 canales, permiso en contexto, preferencias por tipo, ruteo, `onTokenRefresh`, 6 idiomas; nueva build | P1 |
| P4 | `resumen_resultados`, `inicio_partido`, `recordatorio_monedas` (con consentimiento) | P2, P3 |
| P5 | iOS real (APNs) | Mac + Apple Developer |
| P6 | Medir 4 semanas: aperturas, bajas de permiso, desactivaciones por tipo; ajustar topes | P3 en tienda |

## 9. Decisiones del titular (19-nov-2026)

1. Catálogo de la §4 (7 tipos, 1-4 activos por defecto): **aprobado**.
2. Tope diario: **5 avisos de contenido al día** (no 3). Silencio 22:00–09:00 hora local: se mantiene (no se objetó).
3. Pick gratis: **completo en el aviso** (partido, mercado, probabilidad y hora del sello).
4. Cuota en el aviso: **no**.
5. `recordatorio_monedas`: **sí**, apagado por defecto y con consentimiento explícito (Apple 4.5.4).
6. iOS: **autorización provisional** en el primer arranque; la completa se pide en contexto.
