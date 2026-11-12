# Pendientes de QuantFut — lista única

Actualizada el **2026-11-11**. Antes tenía 105 líneas con calendario y estados de octubre; el original está en
`harness/archivo/PENDIENTES_hasta_20261110.md`. El detalle técnico vive en `harness/tareas.md` (búscalo con `grep -n '^## '`, no lo leas entero).

**Reglas del titular:** un error al desplegar o probar se arregla en esa misma sesión, no se apunta. Aquí solo entra lo que depende de ti
(decisión, credencial, pago) o de algo que aún no ha ocurrido (fecha, muestra). Responsable: **Tú** = titular; **Claude** = repo o servidor
(con ensayo y registro en `DEPLOYS.md`). Fuentes vivas de fútbol: ver `CLAUDE.md` y la memoria del proyecto.

## 0. Orden del repositorio (10-nov-2026) — hecho, con un resto
- [x] Rescate fusionado (PR #341, #342, #343, #344): `main` = producción. API desplegada desde `main` con la imagen `quantfut-api:015f78c1`; entradas del 8-nov y del 10-nov pasadas a `DEPLOYS.md`.
- [x] 279 ramas y 81 worktrees acumulados reducidos a `main` y la rama de trabajo; el resto está en `C:/Users/huye/Documents/qf-respaldo-carpeta-20261110/todo_pendiente_20261110.bundle` (45 MB, 25 referencias) y en las listas `ramas_borradas.txt` y `worktrees_quitados.txt` de esa carpeta. Copia el `.bundle` fuera de este disco si quieres una segunda copia.
- [x] 7 worktrees viejos limpiados tras confirmación del titular (11-nov-2026: quitadas las carpetas y junctions `.venv` residuales en `.claude/worktrees/{escalera-7dias,escalera-horas,fallos,futbol-base-unica}`, `qf-app-nba-tenis` y `~/.codex/worktrees/{datos-motor-fotmob,web-real-forecasts}` sin tocar el `.venv` raíz; el respaldo se conserva en `rescate/wt-*` y `todo_pendiente_20261110.bundle`).
- **Trabajo archivado que no está en `main`** (recuperable con `git fetch <bundle> <rama>`; todo parte de octubre o principios de noviembre y chocaría con lo nuevo): radar de seis familias NBA en la app (`app/mercados-nba-seis`, `nba_markets.dart`); cuota de casa de tenis como referencia (`web/tenis-cuota-referencia`, `tenis_cuotas.py`); scripts de backtest de escalera (`feature/escalera-redesign-2026`: `backtest_profesional_escalera.py`, `backtest_maestro_mercados_totales.py`, `escalera_targets_backtest.py`); cargadores FotMob de contexto y calendario (foto `wt-datos-motor-fotmob`). Si alguno interesa, se rehace sobre `main` en su propia rama.
- Idiomas: textos aprobados por el titular (11-nov-2026). Inglés sigue en `preview` y portugués en `off` hasta confirmar si `en` pasa a `on` ya o tras `/legal/privacidad` y el nuevo menú `/control/configuracion`. (F7 `fr`/`it`/`de` bloqueado hasta revisión legal: `docs/revision_legal_f7_20261110.md`.)
- `README.md` auditado el 10-nov-2026 frente al sistema en marcha (`CLAUDE.md`, `scripts/crontab`, `docker-compose.yml`, `Caddyfile`, `db/001..109` y `DEPLOYS.md`); las secciones históricas conservan su fecha. (`Caddyfile` del repo también alineado con F2.1 de producción: sin `302` en `/nba/*` y con `X-Robots-Tag: noindex` en `@nba_v2`.)

## 1. Depende de ti
**Decisiones**
- Encender `PUBLISH_PICKS_ENABLED` cuando se cumpla la puerta de CLV.
- [x] Decisión cerrada (11-nov-2026): los 19 lotes históricos de la cadena se quedan apartados en `historico_sin_publicar/` (`docs/registro_publico_activacion_20261018.md`), sin subirse al registro público.
- [x] Nuevo módulo en `/control/configuracion` (11-nov-2026): implementado y desplegado (`quantfut-api:f73f7df2`, `db/110_web_config.sql`, PR `#356`) para editar páginas principales del frontend, ajustes web, redes sociales, idiomas y traducción via APIMart; **pendiente del titular:** rotar la clave de APIMart compartida en chat, cargarla en `/control/configuracion` (o `APIMART_API_KEY`) y revisar los textos antes de pasar `en`/`pt` a `on`.
- Menú «Web y App» en `/control`: Fases 1 y 2 (A–E) desplegadas el 12-nov-2026 (reglas de acceso en `/control/acceso`, `/cliente/v1/config` con contrato 1 y catálogo de deportes en `/control/deportes`). Te toca: abrir `/control/acceso` y `/control/deportes` y comprobar que ves la regla en vigor (73–95 %, 10 %) y fútbol, NBA y tenis, y mirar la portada `/` con calma (no pude verla: mis comprobaciones activaron el límite de peticiones). Para la parte F (la app lee el catálogo): decir cuándo se publica la versión de la app.
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
