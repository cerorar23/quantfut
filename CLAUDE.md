# QuantFut — contexto para el agente

Sistema cuantitativo de predicción de fútbol (Dixon-Coles + de-vig de mercado
+ cadena de hashes para picks). Python 3.12, Postgres, Redis, Docker Compose,
FastAPI. Ver [README.md](README.md) para la arquitectura completa; este
archivo es el arnés operativo, no repite esa documentación.

Decisión del usuario (2026-10-23): PropLine es la fuente fija de **cuotas** para
los motores y consultas nuevas. Un recolector compartido captura cada hora;
los motores leen el archivo y no hacen peticiones duplicadas. Conservar las
observaciones originales para reentrenamiento posterior, con recepción real,
fuente e identidad del contrato; no reentrenar ni promover por capturar datos.
Ver `docs/propline_compartido_20261023.md`. The Odds API queda para históricos
ya autorizados/reproducción; no es fallback automático de las cuotas en vivo.
Esto no sustituye estadísticas, lesiones o resultados oficiales.

Actualización (2026-09-23): un único FastAPI sirve también la web demo en
`/` y el panel interno en `/control`; el BFF separado que figura en
decisiones históricas fue descartado. No exponer tokens de servicio o
administración en JavaScript ni en la app Flutter.

Fase comercial desbloqueada (2026-10-07, decisión del usuario): cuentas en
`/app/v1` (`api/cuentas.py`, web + Flutter), lógica en `src/qf/comercial/`,
panel de administración en `/control` (`api/panel.py`, Tabler). `db/043`:
`subscriptions` solo se revoca, `admin_audit` es inmutable. Correo: Proton
Mail por SMTP (`comercial/correo.py`, `db/044`). Falta elegir procesador de
pago (ver `harness/tareas.md`).

## Protocolo de inicio (obligatorio antes de tocar código)

1. Ejecuta `./scripts/harness_check.sh`. Si falla, tu única tarea es arreglar
   eso antes de continuar con cualquier otra cosa.
2. Lee [PENDIENTES.md](PENDIENTES.md) (lista única: qué falta, quién y cuándo) y
   [harness/tareas.md](harness/tareas.md) — backlog priorizado con el detalle técnico.
3. Lee [harness/progreso.md](harness/progreso.md) — decisiones y estado de
   sesiones anteriores, para no repetir trabajo ni deshacer decisiones ya
   tomadas.

## Despliegues (desde 2026-10-15)

Antes de tocar el servidor lee [DEPLOYS.md](DEPLOYS.md). Lo que corre en producción debe ser lo que dice `main`;
solo despliega una sesión a la vez, se compara lo desplegado con `main` antes de sobrescribir, y cada despliegue
se anota en DEPLOYS.md con su vuelta atrás. No reconstruyas imágenes desde `~/quantfut/src` del servidor:
está desactualizada.

## Alcance del negocio (decisión del usuario, 2026-09-21)

El usuario **no usa Telegram**. Vende picks solo desde su propia web, que
consume esta API. `src/qf/publish/telegram.py` sigue en el repo y sigue
siendo llamado desde `daily.py`, pero es best-effort/no-op sin
`TG_BOT_TOKEN` — **nunca** lo trates como la fuente de verdad de nada
(el tier free/paid de un pick lo decide `picks.assign_tiers()`, no
Telegram). No desarrolles el bot receptor de Telegram ni auth por Telegram
a menos que el usuario lo pida explícitamente. Auth de suscriptor
(no-Telegram) ya existe (`/app/v1`); los cobros esperan a que el usuario
elija procesador — ver `harness/tareas.md`.

Excepción (2026-10-02, decisión del usuario): Telegram SÍ es el canal de
**alertas operativas** (`telegram.alert()` → chat privado `TG_ALERT_CHAT`).
Los canales de picks (`TG_CHANNEL_FREE/PAID`) siguen vacíos a propósito. Cada
pasada del chequeo diario queda además en `health_runs` (db/037).

## Dónde vive cada cosa (no lo derives, ya está aquí)

- `src/qf/ingest/` — captura de datos (cuotas, calendario, resultados, xG).
  Desde el 12-oct-2026, por decisión del usuario, API-Football SÍ alimenta el
  xG del modelo mediante `xg_api_football.py`: primera pareja válida congelada,
  recepción real en `xg_recorded_at` y uso solo desde esa fecha. El cliente
  `api_football.py` conserva su control de cuota.
- `src/qf/api/anuncios*.py` — videos con recompensa de AdMob (SSV); el servidor acredita, configurable en
  `/control/anuncios`. Apagado y en modo prueba por defecto; ver `docs/admob_recompensas_20261014.md`.
- `src/qf/model/` — Dixon-Coles, de-vig, pricing, entrenamiento, calibración
  (`calibration.py`), peso modelo/mercado (`meta.py`), GBM de residuo
  (`residual.py`) y ratings dinámicos (`kalman.py`). Todos existen.
- `src/qf/publish/` — orden estricto predecir → seleccionar → sellar →
  publicar (`daily.py`). No reordenes ese pipeline sin que te lo pidan
  explícitamente: es la garantía anti-fraude del negocio.
- `src/qf/eval/` — métricas, backtest, CLV. `check_leakage()` en
  `backtest.py` se corre SIEMPRE antes de confiar en un resultado de backtest.
- `db/*.sql` — el esquema tiene triggers de inmutabilidad (rechaza UPDATE/
  DELETE en `predictions`, `picks`, `odds_snapshots`) y un trigger
  point-in-time en `features_pit`. No los deshabilites para "hacer una
  corrección rápida": ese es exactamente el escenario que bloquean.
- `harness/archivo/` — código retirado pero conservado (no hay git): goles y
  hándicap probados sin valor, y la instantánea de la versión inicial. No se
  despliega nada de ahí. (La antigua carpeta `pyton/` se borró el 2026-09-25
  con confirmación del usuario.)

## Roles según la fase de la tarea

- **Arquitecto:** para tareas grandes o ambiguas, primero escribe o actualiza
  el plan en `harness/tareas.md` antes de escribir código.
- **Implementador:** cambios pequeños y granulares, alineados con la
  estructura de módulos existente (`ingest` / `model` / `publish` / `eval`).
- **Revisor:** después de implementar, corre `./scripts/harness_check.sh` de
  nuevo. Si hay tests relevantes, córrelos. Actualiza
  `harness/progreso.md` con la decisión clave, no con un resumen de diff.

## Competición y liga no son lo mismo (desde 2026-09-22)

Con Champions y Europa League dentro, `matches.league_id` es la COMPETICIÓN y
`teams.league_id` es la liga DOMÉSTICA del equipo. En las 11 ligas coinciden; en
las 2 copas no.

Consecuencias que hay que respetar:

- Cualquier consulta que le dé equipos al modelo tiene que traer
  `th.league_id AS home_league` y `ta.league_id AS away_league`, y pasarlos a
  `lambdas()` / `predict()` / `knows()`. Sin eso, un partido de copa no
  encuentra a sus equipos y se predice con ataque y defensa 0.
- **Nunca** des de alta equipos bajo `eu.ucl` o `eu.uel`. Duplicaría clubes que
  ya existen y partiría su historial en dos sin dar ningún error. Si no se
  resuelve, se descarta el partido y se registra en `unresolved_names`.
- En competiciones `cross_league`, el emparejamiento de nombres solo acepta
  coincidencia EXACTA. El difuso busca en las 11 ligas a la vez y puede colocar
  un club europeo encima de uno latinoamericano de nombre parecido.
- El término `strength` de `dixon_coles.py` se cancela exactamente en los
  partidos domésticos. Si tocas esa fórmula, `tests/test_cross_league.py` lo
  comprueba a 1e-9: no lo relajes, es lo que garantiza que añadir las copas no
  movió nada de lo ya medido en las ocho ligas.

## Reglas estrictas

- **Traducciones de la app (decisión del usuario, 2026-10-12):** cualquier texto visible que se añada o cambie en `apps/mobile` (o mensaje del servidor que la app muestre) se traduce a los 6 idiomas (es, en, pt, fr, it, de) en el MISMO cambio. Sin cadenas fijas en los widgets: `context.l10n` + `python apps/mobile/tool/l10n_add.py`; mensajes de API en `src/qf/api/mensajes.py`. Ver `apps/mobile/docs/TRADUCCIONES.md`; las pruebas `test/l10n_test.dart` y `tests/test_mensajes.py` lo exigen.
- No inventes que existe un archivo o módulo sin verificarlo (`ls`, `grep`).
  Este repo mezcla partes completas (Fase 0-1) con partes que no existen
  todavía (Fase 4-5) — confundir eso rompe el plan.
- No relajes ni quites triggers de la base de datos, validaciones de
  point-in-time, ni el orden `predecir → sellar → publicar` sin pedir
  confirmación explícita: son las garantías que hacen creíble el producto.
- No añadas manejo de errores o fallback para escenarios de proveedor que el
  README ya descarta. La antigua exclusión del xG de API-Football fue revocada
  por el usuario el 12-oct-2026; el histórico previo no acredita su recepción original.
- Sé directo, sin explicar código que ya es legible por sí mismo.
- Al terminar una tarea: márcala en `harness/tareas.md` y añade la decisión
  clave (el porqué, no el qué) a `harness/progreso.md`.
