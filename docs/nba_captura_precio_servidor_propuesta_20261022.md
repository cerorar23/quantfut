# NBA — captura diaria del precio de Pinnacle en el servidor (22-oct-2026)

**Estado: APROBADA (opción A) e IMPLEMENTADA en código; NO DESPLEGADA.** El titular aprobó la opción A con tope de 2 peticiones por día y 70 créditos al mes, capturando también la fase `close`, y ordenó copiar la clave del piloto sin leerla y preparar todo sin desplegar. Contexto: `docs/nba_mercado_prospectivo_20261101.md` (el precio debe tomarse en los 15 min siguientes a sellar cada cohorte).

## Hecho
- **Clave copiada en el servidor sin leerla:** `~/nba-isolated/live13/private/odds_key` (carpeta `drwx------`, archivo `-rw-------`, `qf:qf`, 32 bytes), copiada con `cp -p` desde `paper-pilot/.../private/odds_key`; comprobado con `cmp` que es idéntica y que ningún contenedor en marcha la referencia. Creadas también las carpetas vacías `live13/price` y `live13/ledger`. No está montada en nada.
- **Código** (`apps/nba/src/nba/live_market.py`, 24 pruebas):
  - `read_key`: acepta la clave sola (formato del servidor) o `ODDS_API_KEY=…`; si el archivo no contiene exactamente una clave, falla sin imprimir su contenido.
  - `--market-root`: los precios van a `price/<cohorte>/`; **la cohorte sellada no se escribe nunca** (prueba: el árbol de la cohorte es idéntico antes y después), así que se monta en solo lectura.
  - Libro de presupuesto (`--ledger`), fuera de las cohortes: 2 peticiones por día UTC, 70 créditos por mes UTC, reserva sobre el último saldo conocido, y archivo `halt` ante cualquier error HTTP, coste distinto de 1 o respuesta rara; `halt` bloquea todo hasta que una persona lo borre. Un fallo de red cuenta como una petición, no deja `halt` y no se reintenta.
  - `capture-pending`: paso idempotente para cron. Fase `seal` si la cohorte se selló hace ≤15 min y no tiene precio; fase `close` entre 30 y 10 min antes del primer salto. Sin nada pendiente no hace ninguna petición. Antes del 2026-11-01 devuelve «bloqueado» **sin leer la clave** ni tocar el disco.
- **Piezas de despliegue** (`apps/nba/ops/`): `Dockerfile.live13_price` (deriva de `nba-live13-producer:20261021`, sin secretos) y `live13_price.sh` (envoltorio con su propio `flock`).

## Decisión de diseño al leer `main`
`main` ya trae el productor (PR #66) y su envoltorio usa `exec docker run`, por lo que añadir el paso de precios dentro de `producer.sh` obligaría a editar algo que está en producción. En su lugar el paso de precios es **una línea de cron propia cada 5 minutos** con su propio contenedor: el productor no se toca y el precio se toma <5 min después de sellar (el protocolo admite 15). Cada contenedor de precios dura segundos.

## Presupuesto
Máximo 2 peticiones/día (sello + cierre) → ≤ 62 créditos en un mes de 31 días; tope duro 70. Con la cuenta de fútbol (20.000/mes) es el 0,3 %.

## Runbook de despliegue (NO ejecutado; espera confirmación)
Requisitos: la rama fusionada en `main` con el arnés en verde (hoy `nba/v13-disponibilidad` va por detrás de `main`; fusionar tiene conflictos previsibles en `market_compare.py` y su prueba —`main` trae una primera versión— y en `harness/*.md`); `scripts/deploy.sh estado` y una sola sesión desplegando.
```bash
ssh quantfut
L=$HOME/nba-isolated/live13
# 1) respaldo del cron
crontab -l > $L/crontab.before-price-$(date +%Y%m%d)
# 2) contexto de construcción (desde main) en $L/build-price/ con src/nba y ops/Dockerfile.live13_price, y la imagen
docker build -f $L/build-price/ops/Dockerfile.live13_price --build-arg NBA_LIVE13_BASE=nba-live13-producer:20261021 \
  -t nba-live13-price:20261022 $L/build-price
# 3) red propia
docker network create nba-price
# 4) envoltorio
install -m 755 $L/build-price/ops/live13_price.sh $L/price.sh
# 5) prueba sin clave y sin red: debe imprimir blocked_until y no crear nada
docker run --rm --network none --user 1001:1001 --read-only --cap-drop ALL nba-live13-price:20261022 \
  python -m nba.live_market capture-pending --cohorts /nonexistent --market-root /tmp/p --ledger /tmp/l --key-file /nonexistent
# 6) cron (una línea nueva; el resto del crontab no se toca)
( crontab -l; echo '*/5 * * * * /home/qf/nba-isolated/live13/price.sh >> /home/qf/.local/share/quantfut/nba_live13_price.log 2>&1' ) | crontab -
```
Verificación antes del 1-nov: el registro de `nba_live13_price.log` muestra `blocked_until` en cada pasada, `ledger/` y `price/` siguen vacíos y los demás contenedores conservan su ID. **El 1-nov o después,** tras el primer sellado (17:35 ET): `price/<cohorte>/seal.json` con `credits: 1`, `ledger/requests.jsonl` con una línea, y `seal_raw.json` cuyo sha256 coincide con el recibo; luego el cierre ~30-10 min antes del primer salto.

**Vuelta atrás:** restaurar `crontab.before-price-…` (o borrar solo esa línea), `rm $L/price.sh`, `docker network rm nba-price`, `docker rmi nba-live13-price:20261022`, y `rm $L/private/odds_key` si se quiere retirar la copia de la clave. Lo guardado en `price/` y `ledger/` queda en disco sin efecto.

**Si aparece `ledger/halt`:** leerlo (motivo, cohorte, fase), mirar `nba_live13_price.log` y `price/<cohorte>/attempts.jsonl`, y borrarlo solo cuando se sepa la causa.

**Informe:** `python -m nba.live_market report --cohorts <copia de cohorts> --market-root <copia de price> --protocol nba_vs_market_live_protocol.json --output .local/normalized/nba_f6_live13_market`, sobre una copia bajada del servidor (solo lectura).

## Plantilla de entrada para `DEPLOYS.md` (se rellena al desplegar)
`### AAAA-MM-DD hh:mm UTC · NBA: captura del precio de Pinnacle al sellar (cron propio) · contenedor nba-live13-price` — imagen y hash, cron, red `nba-price`, montajes (`cohorts` ro, `price`, `ledger`, `odds_key` ro), topes 2/día y 70/mes, bloqueo hasta 2026-11-01, respaldos y vuelta atrás.

## Rectificaciones
- Dije que el productor y el panel `live13` no estaban en `DEPLOYS.md`: **era falso**. `main` los registra (entradas del 21-oct 15:45 y 16:43 UTC); mi rama iba por detrás y no los veía.
- Dije que desplegar la captura exigía reajustar el modelo del productor: **no**. Con un contenedor aparte, el productor y su `model.json` no cambian; el módulo local `multimarket_v13_live.py` (con la caché de `completed()`) solo se desplegaría cuando se decida actualizar el productor, y entonces sí haría falta `nba_f6_live13_model_20261021b`.

## Límites
La clave es la de la cuenta compartida con fútbol; el contenedor solo debe salir a `api.the-odds-api.com:443`, pero Docker no filtra por dominio (el control es que el código conoce una única URL fija y el contenedor vive segundos). Un filtro de salida a nivel de host queda como endurecimiento opcional.
