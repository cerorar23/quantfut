# Pendientes de QuantFut — lista única

Actualizada el **2026-10-25** (limpieza a fondo: solo queda lo que sigue abierto). El detalle técnico vive en
`harness/tareas.md` (índice «Pendientes vivos» al principio) y en `docs/`; cuando algo se cierre, se marca aquí y allí.

**Regla del titular (25-oct):** un error que aparece al desplegar o al probar se arregla en esa misma sesión, no se apunta.
Aquí solo entra lo que depende de ti (decisión, credencial, pago) o de algo que todavía no ha ocurrido (una fecha, una muestra).
Fuentes de fútbol: **SofaScore** (Apify), **PropLine** y **FotMob**; API-Football está fuera desde el 22-oct.
Responsable: **Tú** = titular; **Claude** = trabajo en el repo o el servidor (con ensayo y registro en `DEPLOYS.md`).

## Calendario
| Fecha | Qué ocurre |
|---|---|
| 26-oct, 01:30 UTC | Migración 088 (retiro de Serie B, LaLiga 2, Allsvenskan y Super League suiza), programada en el cron del host |
| ~26-oct | Termina la prueba Business de Sentry: confirmar la retención del plan (**Tú**) |
| **1-nov, 03:00 UTC** | Reentrenamiento automático (~5 h) y renovación de los 20.000 créditos de The Odds API. Mientras corre (03:00-08:00 UTC) no se recrea el worker: lo mataría |
| **2-nov, 9:00 (hora local)** | Revisión automática de solo lectura (tarea programada `revisar-reentrenamiento-1-nov`) |
| Cuando llegue la muestra | **Puerta de CLV.** Cifra oficial: `publish.shadow_sharp.report()`. Medido el 25-oct, 17:30 UTC: 235 ofertas publicables con cierre justo (290 publicables), `ev_close` **+2,68 %**. Falta n ≥ 300 y al menos 3 ligas con 30 (la mayor, Champions, tiene 21). Los cierres vuelven a entrar desde el 25-oct (PropLine, #127), así que la muestra vuelve a crecer |

## 1. Depende de ti
**Decisiones**
- Encender `PUBLISH_PICKS_ENABLED` cuando se cumpla la puerta de CLV.
- ¿Publicar el JSON de los 19 lotes históricos de la cadena? Hoy están apartados en `historico_sin_publicar/` (`docs/registro_publico_activacion_20261018.md`).
- Comprar, tras la renovación del 1-nov, los cierres históricos que faltan: 590 snapshots (~5.900 créditos) con `python -m qf.ingest.cierres_odds_api fetch --presupuesto 5900`. Los partidos nuevos ya traen su cierre de PropLine.
- `SOFT_BOOKS` frente a las casas de PropLine: solo 1xbet coincide, así que la sombra sharp ve 0 ofertas de casas blandas.
- Licencia de BetsAPI, fuente del calendario de copas y tope mensual de Apify (el ritmo del 24-25 oct supera los 15 USD/mes).
- NBA: lesiones de ESPN, retirar o no la captura `nba-live13-price` (sin créditos hasta el 1-nov), desplegar el productor y el paquete de The Odds API para props (plan 5M, 119 USD).
- Tenis: cuotas de cierre y apagar la automatización de Codex «continuidad-de-validaci-n-predictiva-de-tenis» (solo desde Codex).
- Aviso push al sellar.

**Credenciales, cuentas y trámites**
- Meta: compra de prueba en la web con `META_TEST_EVENT_CODE`, build de Play con `QF_META_ENABLED=true` y app de iOS (`apps/mobile/docs/META_COMPRAS_TITULAR.md`).
- Cuentas de editor RevU/BitLabs; evaluar Tapjoy/Unity, ayeT, adjoe y Torox tras el piloto.
- iOS: Mac y Apple Developer (APNs y firma); registrar `*.lproj/InfoPlist.strings` en Xcode.
- Validar el acceso con Google y la entrega FCM con un usuario real (`FIREBASE_AUTH_ENABLED` ya está en 1 en el servidor).
- Compilar y publicar la app.
- Sentry: retención y ajustes de la organización (IPs, Data Scrubber, 2FA).
- Copia de seguridad fuera del servidor: elegir destino.
- DPA de Contabo y Proton, avisos legales en la web y atender el buzón de contacto.
- Riesgos aceptados el 18-oct, no se vuelven a pedir: 2FA de GitHub, rotar la clave de The Odds API y restringir la clave de Firebase.

## 2. Claude: esperan una fecha o una muestra
- **1-nov:** vigilar que el reentrenamiento corra limpio y reejecutar `python -m qf.model.ajuste` sobre el OOS nuevo.
- **Enero de 2027:** pasar Liga MX a `11620` (Clausura) en `scripts/sofascore_apify_config.json` y en el VPS.
- Puertas que esperan muestra: calibración, residuo, cuatro brazos, `ajuste_xi`, alineación en F7, altitud, tarjetas y córners del parley,
  1xBet y la ampliada 73-95 % (acierta 78,0 % frente a 81,4 % prometido, n=223).
- Historia de onces de SofaScore para `availability`, y que las bajas de SofaScore alimenten al modelo (F3).
- Antes de encender los picks: alinear `select_daily` (13 ligas con modelo) con la sombra (22).
- Referidos, cuando la app esté en Play.

## 3. Motor: fases siguientes (Claude)
Fases de `docs/superpowers/specs/2026-10-14-senales-motor-principal-design.md` y `docs/superpowers/specs/2026-10-15-mejoras-tres-motores-plan.md`.
Una señal solo entra si gana fuera de muestra. Orden: F9 con F8 en paralelo → F12 (descanso y calendario) → F3, F6, F5, F4 → activar F8 y F10.

| Fase | Estado |
|---|---|
| F0 archivo a tablas principales | Hecha (en producción) |
| F1 capa de ajuste y línea base | Hecha: el XI simple pasa la puerta (ΔRPS −0,0013; 9 de 12 ligas). Se reejecuta el 1-nov |
| F2 cierres de Pinnacle | A medias: faltan 2.103 históricos (697 en ligas modeladas); compra en la sección 1 |
| F7 sello tardío | **En producción** (`qf.publish.sello_tardio`, cada 5 min) |
| F9 evaluación de probabilidades y selección a volumen constante | Sin empezar; la prueba decisiva es contra B actualizado al mismo momento |
| F8 conectar el modelo propio con los picks | Se evalúa en paralelo con F9 sin tocar picks vendidos; se activa al final |
| F12 descanso y calendario; ida/vuelta, entrenador, estilos | Sin empezar. El calendario de otras competiciones (`calendario_equipo`) venía de API-Football y está parado desde el 22-oct: hay que llenarlo desde FotMob antes de medir el bloque. El motor en producción no lo usa (su descanso sale de `matches`) |
| F3 bajas como minutos perdidos | Sin empezar; bajas de SofaScore (`injuries`) y FotMob ya se capturan |
| F6 clima y sede | ERA5 histórico completo y cron diario (06:20 UTC); falta medir el bloque. Revisar antes los 182 grupos de estadios duplicados por coordenadas |
| F5 árbitro | Sin empezar; usar el nombre de árbitro de FotMob como llave |
| F4 XI con valor de jugador | Sin empezar; las variantes con valor hoy no pasan la puerta |
| F10 selección y exposición entre productos | Tras F8 |
| F11 app: fuente de cada cifra e indicador de calidad (6 idiomas) | No toca el motor; espera tu visto bueno |
| Bloque `mercado` (movimiento de cuotas) | Cuando haya muestra propia |

## 4. Servidor (Claude, mejoras)
- Que el servidor despliegue desde GitHub (clave de despliegue de solo lectura y `git pull` de una etiqueta).
- Ampliar `scripts/deploy.sh` con `construir`, `ensayo` y `desplegar` (hoy tiene `estado` y `congelar`).
- Quitar rutas internas de `/model-card` y añadir `Content-Security-Policy` (prioridad baja).

## 5. NBA y tenis (otras sesiones; detalle en `harness/tareas.md`)
- NBA: doble-doble, Q3/Q4 y margen por rangos (faltan en el archivo normalizado), recalibración de totales por la deriva de
  anotación y postemporada 2021-22 sin fecha (`docs/nba_productor_14b_20261025.md`).
- Tenis (motor en el VPS desde el 20-oct, checkout `quantfut-tenis`): evidencia prospectiva por mercado con mínimos fijados antes
  de los resultados; identidades WTA/ATP con varios IDs; cobertura externa de seis claves; Palm Hills septiembre de 2025; viajes y
  descanso con historial completo; techo y muestra para el clima. Sin ROI demostrado ni picks de tenis
  (`docs/tenis_mercados_integrados_20261019.md`, `docs/tenis_resultados_y_evidencia_20261019.md`).
