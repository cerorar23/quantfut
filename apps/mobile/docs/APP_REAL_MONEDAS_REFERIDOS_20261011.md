# App real, monedas y referidos — 11 de octubre de 2026

La entrada de producción de Flutter ya consume `https://pronosticosdeportivos.pro`.
El prototipo visual anterior queda como referencia histórica. No se usan sus
partidos, balances, cuotas, porcentajes ni compras simuladas en la navegación actual.
Cuando falta información, la pantalla lo indica; una sección desactivada muestra
la leyenda configurada en el panel.

## Contenido y acceso

- Inicio: calendario, fecha, hora local del dispositivo, búsqueda, ventana de
  próximos partidos, escudos disponibles y probabilidades 1X2 del modelo existente.
- Predicciones: publicaciones selladas de Alta Probabilidad dentro de **75–90 %**.
  Se libera el **10 %**, redondeado hacia arriba cuando hay una fracción de pick;
  los gratuitos son los de mayor cuota real de publicación entre los elegibles.
  La asignación se guarda por lote y no rota al actualizar la app ni al empezar
  partidos. El filtrado de la app no rebaja las puertas originales del publicador.
- Escalera: **un único escalón pendiente gratuito entre todos los retos activos**,
  elegido por la probabilidad exacta más alta. Los demás requieren VIP o un canje.
  Los escalones liquidados conservan su resultado, incluidos los fallos.
- Los picks bloqueados entregan únicamente metadatos del partido y una clave
  de canje. El servidor oculta selección, mercado, línea, cuota y probabilidad.
  La protección también cubre las rutas públicas web de ambos productos.
- Detalle: pestañas Pronósticos, Estadísticas y H2H & Táctica. Se muestran picks
  autorizados, probabilidades existentes, histórico, H2H, alineaciones y bajas
  disponibles. Las distribuciones Poisson, marcadores más probables y otras
  métricas que la API aún no entrega quedan identificadas como pendientes.
  Diseño estadístico actualizado según las nuevas capturas: resumen 1X2,
  forma, radar morado/verde, comparaciones, clasificación y cara a cara. Ver
  [Estadísticas del pick](ESTADISTICAS_PICK_20261011.md).
- Mercados: acierto observado y tamaño de muestra del historial publicado real;
  no se mezclan porcentajes ilustrativos ni se atribuye certeza a una predicción.
- Coins: la cuarta pestaña abre directamente saldo, asistencia, ofertas y
  referidos; se eliminó el menú intermedio por indicación posterior del usuario.
  Perfil: registro, acceso, recuperación de contraseña,
  verificación de correo y consulta de suscripción mediante `/app/v1`.
- VIP: catálogo y precios del servidor, rendimiento publicado y comparación
  Gratis/VIP. No se simula un cobro; el proveedor de pagos sigue pendiente.

Las respuestas privadas y las públicas que dependen del reparto son `no-store`.
Los permisos VIP se comprueban en el servidor. Los tokens de cliente se mantienen
en memoria; el guardado seguro de sesión entre reinicios queda pendiente.

## Monedas: operaciones reales

La base PostgreSQL registra saldo, movimientos, asistencia, invitaciones, eventos
de proveedores y permisos de lectura por pick. No hay un saldo inicial inventado.
Las monedas sirven para acceder a contenido; no representan dinero retirable.

Valores iniciales, modificables desde el panel:

| Regla | Valor inicial |
| --- | --- |
| Desbloquear un pick pendiente | 100 monedas |
| Asistencia de días 1–7 | 30, 35, 35, 40, 40, 45, 50 |
| Premio al invitador | 200 monedas |
| Premio al invitado | 100 monedas |
| Ofertas confirmadas para calificar un referido | 100 monedas |

La asistencia requiere correo verificado, una solicitud por día UTC y reinicia
la racha al omitir un día. El canje es atómico: comprueba saldo, partido aún no
iniciado y permiso; una repetición no vuelve a descontar. Un pick público o
incluido en una suscripción no cobra monedas.

El código de referido puede registrarse una sola vez en los primeros siete días
de la cuenta. No permite auto-invitación y exige un invitador verificado anterior.

**Cómo llega el código al invitado (2026-10-14).** En Coins, «Compartir mi código» envía un texto
con el código y el enlace `https://pronosticosdeportivos.pro/i/CODIGO`. Esa página del servidor
(`src/qf/api/invitacion.py`, en es, en, pt, fr, it y de según el navegador, sin base de datos) muestra
el código, un botón de copiar y los pasos. El invitado instala la app, crea la cuenta, verifica el
correo y en Coins escribe o pega el código («Pegar código» acepta el código suelto o el enlace entero).
No hay lectura automática al instalar: eso exigiría el referrer de Google Play (solo Android y solo
con instalación desde la tienda) y la app aún se distribuye como APK. Si `APP_DOWNLOAD_URL` está
definida, la página añade el botón «Descargar la app».
La recompensa llega después de completar el mínimo de ofertas confirmadas.
Las anulaciones revierten monedas y, si corresponde, el premio del referido;
una deuda impide seguir gastando. Los eventos repetidos no duplican el saldo.
No se premian valoraciones de cinco estrellas ni reseñas de la tienda.

## Panel y contratos

- `/control/configuracion-app`: interruptores de cada sección y leyenda editable.
- `/control/recompensas`: activación general, asistencia, referidos, coste del canje,
  siete premios diarios, mínimos, proveedores, movimientos y registro de referidos.
- `GET /mobile/v1/config`, `GET /mobile/v1/home`, `GET /mobile/v1/matches/{id}`.
- `GET /mobile/v1/rewards`, `POST /mobile/v1/rewards/attendance`,
  `POST /mobile/v1/rewards/referrals`, `POST /mobile/v1/rewards/unlock`,
  `POST /mobile/v1/rewards/offers/{provider}`.
- Callbacks públicos validados: `GET /rewards/callback/revu` y
  `GET /rewards/callback/bitlabs`.

Los formularios administrativos mantienen la autenticación del panel, CSRF,
verificación de origen y auditoría. Los importes nunca se aceptan del cliente.
Las claves privadas se configuran solo en el servidor.

## Proveedores: elección y estado

**El usuario confirmó que todavía no tiene cuentas de editor.** Los seis
proveedores permanecen desactivados, sin ofertas de muestra. Se prepararon los
adaptadores de RevU y BitLabs; los otros cuatro requieren una integración posterior.

| Proveedor | Evaluación para este proyecto | Estado |
| --- | --- | --- |
| RevU | Primera opción para un piloto por las reseñas consultadas y la integración web/S2S. Confirmar aprobación, países y condiciones comerciales. | Adaptador preparado; falta cuenta aprobada |
| BitLabs | Complemento para encuestas/ofertas con callbacks firmados y condiciones de pago documentadas. | Adaptador preparado; falta cuenta aprobada |
| Tapjoy / Unity Offerwall | SDK oficial Flutter y moneda gestionada por servidor; candidato posterior según audiencia y aprobación. | Integración pendiente |
| ayeT-Studios | Documenta Flutter y callbacks firmados, pero no ofrece evidencia suficiente para preferirlo al piloto elegido. | Integración pendiente |
| adjoe Playtime | Adecuado para recompensas por juegos; exige acuerdo y wrapper específico. Confirmar elegibilidad de la app. | Integración pendiente |
| Torox | Alternativa web/SDK/API; su perfil de reseñas consultado no permitía una comparación fiable. | Integración pendiente |

La elección es una evaluación para el piloto, no una garantía de pago. RevU
mostraba 4,2/5 con 1.821 reseñas en la consulta; también hay reclamaciones por
ofertas no acreditadas. Las reseñas no verifican el cobro comercial del editor.
Fuentes: [reseñas de RevU](https://www.trustpilot.com/review/revu.co) y
[perfil de Torox](https://www.trustpilot.com/review/torox.io).

Separar el crédito de monedas al usuario del pago de ingresos al editor.
BitLabs documenta NET30 después del cierre mensual y un mínimo de USD 100
después de conciliación; por tanto no debe anunciarse cobro inmediato del editor.
Fuente: [Payments & Billing de BitLabs](https://developer.bitlabs.ai/docs/payments-billing).

Documentación oficial de integración consultada:

- [RevU: Offerwall Integration](https://revu.co/docs/offerwall-integration).
- [BitLabs: Flutter SDK](https://developer.bitlabs.ai/docs/flutter-sdk-v2),
  [callbacks](https://developer.bitlabs.ai/docs/callbacks),
  [firma](https://developer.bitlabs.ai/docs/securing-callbacks-through-hashing) y
  [eventos y anulaciones](https://developer.bitlabs.ai/docs/offer-callbacks).
- [Unity: Flutter y moneda virtual](https://docs.unity.com/en-us/grow/offerwall/flutter/placements/virtual-currency-overview).
- [ayeT: documentación del editor](https://www.ayetstudios.com/openapi/publisher-doc) y
  [wrapper Flutter](https://docs.ayetstudios.com/v/product-docs/offerwall/sdk-wrappers-v2/flutter-wrapper-v2).
- [adjoe: integración](https://docs.adjoe.io/adjoe-sdk/integration) y
  [Flutter oficial](https://github.com/adjoeio/adjoe-flutter-sdk).
- [Torox: monetización](https://torox.io/faq-monetise/).
- [Google Play: valoraciones y reseñas](https://support.google.com/googleplay/android-developer/answer/9898684?hl=en).

### Activar RevU cuando llegue la aprobación

Configurar el Wall ID público en el panel y solicitar a RevU las IP oficiales
de sus callbacks. No usar las IP del usuario que realizó la oferta.
Configurar `QF_REWARDS_TRUSTED_PROXY_CIDRS` con los proxies reales que pueden
conectarse al servicio. Solo desde ellos se acepta `CF-Connecting-IP`; la red
del proxy debe impedir acceso directo de terceros que puedan falsificar esa cabecera.

Postback a registrar en el panel de RevU:

```text
https://pronosticosdeportivos.pro/rewards/callback/revu?uid=$uid$&actionid=$actionid$&currency=$currency$&status=$status$
```

El lanzamiento usa un UID aleatorio estable, no el correo, y abre el navegador
externo Android. No hay una firma HMAC inventada para RevU: el adaptador valida
la lista oficial de origen y deduplica transacciones. Probar crédito, duplicado
y reversión desde el panel del proveedor antes de habilitar ofertas a usuarios.

### Activar BitLabs cuando llegue la aprobación

Configurar el token público en el panel y `QF_BITLABS_SECRET` en el servidor.
`QF_REWARDS_PUBLIC_ORIGIN` debe coincidir con el origen público exacto de los
callbacks. No guardar App Secret en Flutter ni en una captura.

Usar callbacks de oferta con estado: uno de finalización y otro de conciliación,
manteniendo el mismo TX. Registrar las siguientes URLs, sin añadir `hash`
manualmente; BitLabs lo añade al firmar:

```text
https://pronosticosdeportivos.pro/rewards/callback/bitlabs?uid=[%USER:UID%]&tx=[%TX%]&amount=[%VALUE:CURRENCY%]&state=COMPLETED
https://pronosticosdeportivos.pro/rewards/callback/bitlabs?uid=[%USER:UID%]&tx=[%TX%]&amount=[%VALUE:CURRENCY%]&state=RECONCILED
```

La firma HMAC-SHA1 cubre la URL original exacta previa a `&hash=`. No se reconstruye
con parámetros reordenados ni codificados de nuevo. El importe se convierte a
monedas enteras hacia abajo. El modo legado de conciliación negativa solo debe
usarse con la referencia al TX original correctamente configurada.

## Validación y operación

- Backend: 124 pruebas aprobadas; cinco pruebas PostgreSQL locales condicionadas
  se omiten si no se activa su entorno. Además se aprobaron ocho comprobaciones
  reales en PostgreSQL dentro de una transacción que siempre se revierte,
  incluidos los formularios de configuración del panel.
- Flutter: 18 pruebas aprobadas, análisis sin incidencias y APK de depuración
  compilado. Las imágenes de pruebas usan fixtures exclusivamente en `test/`.
- API pública comprobada con datos reales: configuración, calendario, detalle,
  Alta Probabilidad, Escalera y estado de recompensas; sin contenido VIP filtrado.
  Las cuentas y el correo transaccional están configurados en el servidor;
  no se envió correo a usuarios durante estas comprobaciones.
  En la comprobación de fecha 11/10 y zona UTC−6: 99 enfrentamientos, dos picks
  gratuitos pendientes, quince VIP y un escalón gratuito. Estos conteos varían
  con el calendario y la liquidación; no se fijan como cifras promocionales.
- Despliegue de API limitado a estos módulos sobre la imagen anterior; se
  conservaron los workers y se guardó la configuración anterior de compose.
  La imagen activa es `quantfut-api-mobile-rewards:20261011`.
- Evidencia: `docs/validation/mobile_rewards_release_20261011/` desde la raíz
  del proyecto y capturas Android en `apps/mobile/docs/validation/real_mobile_20261011/`.

No se han realizado ofertas comerciales ni verificado pagos de proveedores:
faltan las cuentas aprobadas. Las pruebas de saldo y reversión no crean bonos
ni usuarios de prueba permanentes en producción.

## Pendientes concretos

1. Cuentas aprobadas, IDs y secretos de RevU/BitLabs; configuración de origen,
   callbacks de prueba y primer piloto con tareas confirmadas y anuladas.
2. Firebase: identidad compartida con el backend, FCM, bandeja y preferencias;
   guardado seguro de sesión, identificadores definitivos y protección de dispositivo.
3. Selector de idioma inicial y localización completa de las seis lenguas,
   incluyendo textos del modelo y errores backend. Ya anotado en el backlog.
4. Pagos y restauración reales; conservar el catálogo del servidor y comprobar
   permisos de cuenta antes de activar la contratación en la app.
5. Entregar las métricas Poisson, marcadores probables y árbitro desde fuentes
   existentes; favoritos y notificaciones reales de picks, sin datos inventados.
6. Firma de distribución Android e integración/pruebas iOS para ofertas externas.
