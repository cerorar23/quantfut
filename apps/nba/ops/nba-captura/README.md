# nba-captura: colectores hacia `nba_datos`

Imagen `nba-captura:<commit>` (Python 3.12 slim, usuario sin privilegios) que ejecuta **una vez** un colector y termina:
`python -m nba.v2.captura rotowire|espn`. El cron del VPS la lanza con `ejecutar.sh` (un proceso por fuente, `flock`).

| Colector | Frecuencia | Qué hace |
|---|---|---|
| `rotowire` | cada 30 min | Página de quintetos (probabilidad de jugar, árbitros) y, dentro de las 8 h previas al salto y como mucho una vez por hora, los minutos proyectados **del equipo visitante** (los del local son de pago en Rotowire y no se piden). Directo y gratis; ZenRows solo ante un bloqueo (403/429/503) y con tope diario `NBA_ZENROWS_TOPE_DIARIO` |
| `espn` | cada 15 min | Convierte los recibos nuevos del ledger de `run57` (solo lectura) en calendario, marcadores finales y lesiones; avanza `datos/estado_espn.json` tras confirmar cada lote |

Respaldo: `respaldar.sh` (diario 09:15 UTC) deja `pg_dump -Fc` en `respaldos/` y conserva 7. La copia fuera del VPS la trae
`scripts/respaldo_nba_vps.ps1` desde el PC del titular.

## En el servidor (`~/nba-isolated/nba-captura/`)
`captura.env` (modo 600: `NBA_DB_DSN` del usuario `nba_captura`, `ZENROWS_API_KEY`, tope), `imagen_actual`, `datos/originales/` (cuerpos
con hash), `datos/estado_espn.json`, `respaldos/`, `crontab.before-20261102`.

## Actualizar
Copiar `apps/nba/src/nba` a `build/src/`, `docker build -q -f build/ops/nba-captura/Dockerfile -t nba-captura:<commit> build`,
escribir la etiqueta en `imagen_actual`. Registrar el cambio en `DEPLOYS.md`.

## Vuelta atrás
`crontab ~/nba-isolated/nba-captura/crontab.before-20261102` (quita las tres líneas NBA). Los datos ya cargados se quedan
(son solo-anexar). Para volver a una imagen anterior, escribir su etiqueta en `imagen_actual`.
