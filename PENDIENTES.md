# Pendientes de QuantFut — lista única

Actualizada el **2026-11-10**. Antes tenía 105 líneas con calendario y estados de octubre; el original está en
`harness/archivo/PENDIENTES_hasta_20261110.md`. El detalle técnico vive en `harness/tareas.md` (búscalo con `grep -n '^## '`, no lo leas entero).

**Reglas del titular:** un error al desplegar o probar se arregla en esa misma sesión, no se apunta. Aquí solo entra lo que depende de ti
(decisión, credencial, pago) o de algo que aún no ha ocurrido (fecha, muestra). Responsable: **Tú** = titular; **Claude** = repo o servidor
(con ensayo y registro en `DEPLOYS.md`). Fuentes vivas de fútbol: ver `CLAUDE.md` y la memoria del proyecto.

## 0. Orden del repositorio (10-nov-2026) — en curso
- [ ] **Tú:** revisar y fusionar el PR de rescate (CLAUDE.md, auditoría VPS, entradas de DEPLOYS del 8-nov, frontend alineado con producción) y el PR de tenis (`tenis/rediseno-f1`, solo medición).
- [ ] **Claude:** pasar a `DEPLOYS.md` las entradas de `docs/rescate_deploys_pendientes_20261110.md` que sigan vigentes.
- [ ] **Claude:** producción sirve `app.js`, `index.html` y `conversion-views.js` que `main` no tenía; tras fusionar el PR de rescate, `main` = producción. `parley_v2_datos.py` de `main` es más nuevo que el del servidor (trae `resumen_publico_v2`): desplegarlo con el flujo de `DEPLOYS.md`.
- [ ] **Claude:** decidir qué hacer con 7 fotos de worktrees viejos (refs `rescate/wt-*`, base 15–31 oct; sus migraciones 085–089 chocan con las de `main`) y con las ramas locales `app/mercados-nba-seis`, `app/version-1-1-0-8`, `web/tenis-cuota-referencia`, `tarjetas-lineas-seguimiento` y `feature/escalera-redesign-2026` (frontend del 7-nov ya desplegado vía el PR de rescate). Respaldo: `qf-respaldo-carpeta-20261110/ramas_pendientes_20261110.bundle` (en Documents).

## 1. Depende de ti
**Decisiones**
- Encender `PUBLISH_PICKS_ENABLED` cuando se cumpla la puerta de CLV.
- ¿Publicar el JSON de los 19 lotes históricos de la cadena? Hoy están apartados en `historico_sin_publicar/` (`docs/registro_publico_activacion_20261018.md`).
- Comprar, tras la renovación del 1-nov, los cierres históricos que faltan: 590 snapshots (~5.900 créditos) con `python -m qf.ingest.cierres_odds_api fetch --presupuesto 5900`. Los partidos nuevos ya traen su cierre de PropLine.
- `SOFT_BOOKS` frente a las casas de PropLine: solo 1xbet coincide, así que la sombra sharp ve 0 ofertas de casas blandas.
- Fuente del calendario de copas y de otras competiciones (descanso).
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
- **Enero de 2027:** pasar Liga MX a `11620` (Clausura) en `LIGA_DE_TORNEO` (`sofascore_carga.py`) y en el scraper del VPS.
- Puertas que esperan muestra: calibración, residuo, cuatro brazos, `ajuste_xi`, alineación en F7, altitud, tarjetas y córners del parley,
  1xBet y la ampliada 73-95 % (acierta 78,0 % frente a 81,4 % prometido, n=223).
- Historia de onces de SofaScore para `availability`, y que las bajas de SofaScore alimenten al modelo (F3).
- Antes de encender los picks: alinear `select_daily` (13 ligas con modelo) con la sombra (22).
- Referidos, cuando la app esté en Play.

## 3. Heredado de octubre (sin verificar desde el 25-oct)
Las secciones de motor (fases F0–F12), servidor y NBA/tenis del `PENDIENTES.md` anterior no se han reconfirmado; el texto íntegro está en el archivo.
Reconfirma cada punto contra `harness/tareas.md` antes de actuar sobre él.
