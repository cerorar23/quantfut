# Pendientes de QuantFut — lista única

Actualizada el **2026-10-25** (limpieza a fondo: solo queda lo que sigue abierto). El detalle técnico vive en
`harness/tareas.md` (índice «Pendientes vivos» al principio) y en `docs/`; cuando algo se cierre, se marca aquí y allí.

**Regla del titular (25-oct):** un error que aparece al desplegar o al probar se arregla en esa misma sesión, no se apunta.
Aquí solo entra lo que depende de ti (decisión, credencial, pago) o de algo que todavía no ha ocurrido (una fecha, una muestra).
Fuentes de fútbol: **SofaScore** (Apify), **PropLine** y **FotMob**; API-Football está fuera desde el 22-oct.
Responsable: **Tú** = titular; **Claude** = trabajo en el repo o el servidor (con ensayo y registro en `DEPLOYS.md`).

## Consumo de APIs — 28-oct-2026

- [x] Corregidos: detalles de SofaScore sin pedir desde el 26-oct, alias de Racing de Santander y Tromsoe, y 40-60 % de las llamadas ampliadas de fútbol en PropLine. Ver `docs/auditoria_consumo_apis_20261028.md`.
- [ ] **Tú:** tope mensual de Apify (15 USD, cuenta en 13,2 USD de un límite de 19): hasta decidirlo, listas y detalles de partidos esperan al 24-nov; las alineaciones siguen.
- [ ] Claude: confirmar el ahorro de PropLine tras una jornada completa y decidir si se amplían los lotes de fútbol.

## Calendario
| Fecha | Qué ocurre |
|---|---|
| 26-oct, 01:30 UTC | Migración 088 (retiro de Serie B, LaLiga 2, Allsvenskan y Super League suiza), programada en el cron del host |
| ~26-oct | Termina la prueba Business de Sentry: confirmar la retención del plan (**Tú**) |
| **1-nov** | Reentrenamiento mensual del Motor A **en local** (`scripts/entrenamiento_local/`, ~2 min; el servidor ya no entrena) y renovación de los 20.000 créditos de The Odds API |
| **2-nov, 9:00 (hora local)** | Revisión automática de solo lectura (tarea programada `revisar-reentrenamiento-1-nov`) |
| Cuando llegue la muestra | **Puerta de CLV.** Cifra oficial: `publish.shadow_sharp.report()`. Medido el 25-oct, 17:30 UTC: 235 ofertas publicables con cierre justo (290 publicables), `ev_close` **+2,68 %**. Falta n ≥ 300 y al menos 3 ligas con 30 (la mayor, Champions, tiene 21). Los cierres vuelven a entrar desde el 25-oct (PropLine, #127), así que la muestra vuelve a crecer |

## 1. Depende de ti
**Cuenta de GitHub (26-oct, 21:47 UTC):** el CI no arranca en ningún repositorio: «recent account payments have failed or your spending
limit needs to be increased». Revisar *Billing & plans*. Revisado por el titular a las 21:55 UTC, pero los reintentos de las 21:52-21:56
siguieron fallando. Mientras tanto queda abierto el PR #163 (solo anota en `DEPLOYS.md` la imagen de tenis `7b974ed`, ya activa en el VPS).
Cuando el CI vuelva: relanzarlo y fusionar el #163 (**Claude**).

**Decisiones**
- Encender `PUBLISH_PICKS_ENABLED` cuando se cumpla la puerta de CLV.
- ¿Publicar el JSON de los 19 lotes históricos de la cadena? Hoy están apartados en `historico_sin_publicar/` (`docs/registro_publico_activacion_20261018.md`).
- Comprar, tras la renovación del 1-nov, los cierres históricos que faltan: 590 snapshots (~5.900 créditos) con `python -m qf.ingest.cierres_odds_api fetch --presupuesto 5900`. Los partidos nuevos ya traen su cierre de PropLine.
- `SOFT_BOOKS` frente a las casas de PropLine: solo 1xbet coincide, así que la sombra sharp ve 0 ofertas de casas blandas.
- Licencia de BetsAPI, fuente del calendario de copas y tope mensual de Apify (el ritmo del 24-25 oct supera los 15 USD/mes).
- NBA: decidir si las lesiones de ESPN entran como segunda señal. (Props históricos descargados con el plan de 100K; productor 1.5.0 con umbral estadístico para jugadores: `docs/nba_live15_recalibracion_20261026.md`.)
- Tenis: apagar la automatización de Codex «continuidad-de-validaci-n-predictiva-de-tenis» (solo desde Codex). Las cuotas de cierre ya están: la evaluación las lee del archivo de PropLine desde el 26-oct.
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
- **1-nov:** reentrenar en local y subir (`scripts/entrenamiento_local/`), y reejecutar `python -m qf.model.ajuste` sobre el OOS nuevo.
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
- [x] Despliegue desde `main` sin credenciales nuevas en el servidor y `scripts/deploy.sh construir|ensayo|desplegar` (28-oct; ver DEPLOYS.md). El `docker-compose.yml` del repo ya fija las imágenes que corren.
- Cada sesión despliega desde su propio `git worktree` y anota en DEPLOYS.md lo que despliega; la API corre hoy una imagen (`conversion:002ffcd-v2`) cuyo commit no está en el repositorio remoto: fusionar esa rama.
- Quitar rutas internas de `/model-card` y añadir `Content-Security-Policy` (prioridad baja).

## 5. NBA y tenis (otras sesiones; detalle en `harness/tareas.md`)
- NBA: hecho en 1.7.0 (26-oct): los 86 partidos recuperados y los 9 de cuarentena ya están en el reajuste y los traspasados se cubren con plantillas oficiales (`docs/nba_recalibracion_17_20261026.md`). Las 8 rotaciones sin fuente no las usa el motor.
- NBA: doble-doble, Q3/Q4 y margen por rangos (faltan en el archivo normalizado), modelo único del marcador, prior de
  plantilla y postemporada 2021-22 sin fecha. La recalibración de totales se probó y no entra (`docs/nba_live15_recalibracion_20261026.md`).
- Tenis (motor en el VPS desde el 20-oct, checkout `quantfut-tenis`): evidencia prospectiva por mercado con mínimos fijados antes
  de los resultados; identidades WTA/ATP con varios IDs; cobertura externa de seis claves; Palm Hills septiembre de 2025; viajes y
  descanso con historial completo; techo y muestra para el clima. Sin ROI demostrado ni picks de tenis
  (`docs/tenis_mercados_integrados_20261019.md`, `docs/tenis_resultados_y_evidencia_20261019.md`).
- [ ] Tenis, juegos ganados por jugador (en producción desde el 27-oct, imagen `45f5876`, PR #177): la web y la app no lo muestran
  porque `tenis_publico` solo lee `forecast.markets` y el mercado va en `market_board`. Mostrarlo, con textos en los 6 idiomas, es
  parte de la integración de NBA y tenis en la app (Claude).
- [ ] Tenis: en los «más de» el motor queda por debajo del mercado, en el total de juegos (−0,04 de media en 137 líneas; hándicap
  +0,001) y por tanto en los juegos por jugador. Medirlo fuera de muestra con `offered_markets` por familia antes de corregir nada (Claude).
