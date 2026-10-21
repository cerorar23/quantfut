# NBA — pronósticos prospectivos v1.3 (disponibilidad por reporte oficial de lesiones)

Protocolo congelado antes de correr: `apps/nba/multimarket_v13_live_protocol.json`. Código: `nba.multimarket_v13_live` (ajuste, sellado, resultados) y `nba.multimarket_live_dashboard` (página). RUN071 (42 pronósticos v1.1) no se tocó: la página lo sigue mostrando igual y la cohorte nueva aparece en una sección aparte. Todo `actionable=false`, sin cuotas como entrada, 0 créditos de The Odds API.

## Qué hace
- **Mercados:** ganador, puntos de cada equipo y total del partido. Los de jugador quedan fuera: antes del salto no hay lista verificada de quién juega, y la v1.3 solo aporta disponibilidad a quien aparece en el reporte.
- **Ajuste único** (`fit`): el modelo v1.3 (`multimarket_v13`) se ajusta una vez con 2024-25 y 2025-26 y se guarda en `model.json` con los hashes del código y de todos los insumos. El hash del código cambió respecto a RUN071, así que no se reutiliza su `model.json`. Si se edita `multimarket_v13_live.py` hay que volver a ajustar (el sellado lo comprueba).
- **Calendario** (`forecast`): nba.com/games?date=… (tarjetas) y nba.com/game/<slug> (salto, IDs, equipos). Una cohorte = partidos de una fecha del Este que aún no han empezado; un partido se pronostica una sola vez (`--exclude-sealed`). Los partidos ya terminados de 2026-27 alimentan ratings, descanso y forma.
- **Disponibilidad:** el reporte más reciente de `ak-static.cms.nba.com/referee/injury/` (cada 15 min). Cuenta para un partido solo si su sello y nuestra primera recepción son ≥60 min anteriores al salto; si no, el partido se sella como `sin_reporte_valido` (sin información de lesión, no «todos sanos»). Jugador = nombre exacto único entre quienes tienen historial; equipo = el del reporte; sin 5 partidos en 370 días no aporta.
- **Sellado:** `bundle.json` + `bundle.seal.json` (hash), `sealed_at_utc` estrictamente antes del salto, carpeta nueva por cohorte, nunca se sobrescribe. Incluye `model.json`, `schedule.json`, `completed_games.json` y el PDF del reporte usado, todos con hash.
- **Resultados** (`results`): box score oficial de nba.com tras ≥3 h del salto; si no está final se descarta y se reintenta. La página recalcula todo desde el recibo (hash, identidad, hora de salto, marcadores que cuadran) y, si algo no coincide, marca `validation_hold` en vez de mostrarlo. Marcador acumulado: Brier por mercado.
- **Página** (`/nba`): sección «Pronósticos prospectivos · Modelo 1.3 con lesiones» con versión, estado de disponibilidad por partido (reporte usado, jugadores con efecto, puntos esperados perdidos), aviso de investigación y resultados. Una cohorte rota nunca oculta RUN071.

## Cambio colateral
`injury_pdf.records_from_cells`: el PDF vivo parte algunos motivos en una fila propia (solo columna «Reason»); ahora se anexa al motivo de la fila anterior. Antes el analizador estricto rechazaba el reporte de hoy.

## Operación diaria (desde `apps/nba`, `PYTHONPATH=src`, entorno `.venv` con `pip install -e .[pdf]`)
```bash
N=.local/normalized
# una vez (ya hecho: nba_f6_live13_model_20261021); repetir solo si cambia el código
python -m nba.multimarket_v13_live fit --output $N/NUEVO_MODELO --data $N/nba_f6_run71_20261009/data \
  --injuries $N/nba_complete_injury_final_20261006/reports.jsonl.gz --api-dir .local/raw/api_nba_20261006
# cada día, tras el reporte de la tarde (~17:30 ET) y antes del primer partido que quieras cubrir
python -m nba.multimarket_v13_live forecast --model $N/nba_f6_live13_model_20261021 --data $N/nba_f6_run71_20261009/data \
  --date AAAA-MM-DD --first-day 2026-10-20 --exclude-sealed $N/nba_f6_live13_cohorts --output $N/nba_f6_live13_cohorts/AAAA-MM-DD
# cada hora (o al día siguiente): recoge los resultados finales de lo sellado
for c in $N/nba_f6_live13_cohorts/*; do python -m nba.multimarket_v13_live results --cohort $c; done
```
Los partidos tempranos solo tendrán reporte válido si se sella ≥60 min antes de ellos; un segundo sellado más tarde cubre el resto de la fecha.

## Ensayo local (2026-10-21)
Cohorte `nba_f6_live13_cohorts/2026-10-21_ensayo`: 11 partidos reales, 44 pronósticos, sellada a las 14:39 UTC (≥8 h antes del primer salto, 23:00 UTC) con el reporte de las 10:30 ET; los 11 con reporte aplicado. La página local la muestra sin errores de consola (44 tarjetas). Resultados: se recogerán tras los partidos; verificada la captura y lectura sobre un partido real ya terminado (0022600001: 121-113) y por pruebas con recibos sintéticos.

## Límites
- Ratings y forma parten del cierre de 2025-26 más los partidos ya jugados de 2026-27; el calendario nuevo y los traspasos de la agencia libre solo entran vía reporte y ratings. Equipos con pocos partidos jugados dependen del prior.
- Los reportes de última hora (después del último ≥60 min) no cuentan. Jugadores sin historial (novatos) no aportan.
- Exploratorio y descriptivo; una cohorte de 11 partidos no prueba nada. Comparar con Pinnacle sin margen exige las cuotas históricas (desde el 1-nov, ver `docs/nba_cuotas_historicas_plan_20261021.md`).

## Plan de despliegue (NO ejecutado; requiere confirmación del titular)
Precondiciones de DEPLOYS.md: cambio en `main` con arnés verde (PR de `nba/v13-disponibilidad`), `scripts/deploy.sh estado`, una sola sesión, respaldo y anotar la entrada.
1. **Salida a internet del servidor:** desde `ssh quantfut`, comprobar `curl -I` a `https://www.nba.com/games?date=…` y a un PDF de `ak-static.cms.nba.com` (si bloquean IPs de datacenter, sellar desde otra máquina y copiar la cohorte; el sellado es el hash y las horas de recepción).
2. **Imagen de la página:** `apps/nba/ops/Dockerfile.multimarket_live` (igual que la actual, `CMD nba.multimarket_live_dashboard`) → `nba-dashboard-live13:AAAAMMDD` con el mismo contexto que `nba-dashboard-run71:20261009` y `public-bundle` de RUN071. Comprobar dentro de la imagen `python -c "import nba.multimarket_live_dashboard"` (necesita numpy/scipy; si faltan en la base, añadirlos).
3. **Carpeta de cohortes:** `/home/qf/nba-isolated/live13/cohorts` montada solo lectura en `/live-cohorts` (`NBA_LIVE_COHORTS`); sin credenciales montadas, mismas redes y límites que el contenedor actual.
4. **Respaldo:** `docker inspect` y compose del contenedor `nba-dashboard-run71`, copia de los IDs de los otros contenedores (`quantfut-api-1`, worker, caddy, db…).
5. **Cambio:** parar `nba-dashboard-run71`, arrancar el nuevo con el mismo puerto/alias para que Caddy no cambie. Verificar: `/nba` 200, `/nba/api/data` con `extension` (RUN071: 42 pronósticos) y `live_v13`, `/nba/.env` 404, `/` 200, otros contenedores con el mismo ID.
6. **Productor** (después, aparte): tarea programada que ejecuta `forecast` y `results` con las órdenes de arriba (contenedor con `pdfplumber`, o desde esta máquina con `scp` de la carpeta de cohorte). Se decide tras el paso 1.
7. **Vuelta atrás:** parar `nba-dashboard-live13` y arrancar `nba-dashboard-run71:20261009` (imagen conservada); las cohortes sellada quedan en disco sin efecto.
8. Anotar la entrada en DEPLOYS.md con la vuelta atrás.

## Productor diario (preparado, sin activar)
`nba.multimarket_v13_live_producer` (imagen `Dockerfile.live13_producer`, envoltorio `ops/live13_producer.sh`): cada ejecución recoge los resultados finales de todas las cohortes y, pasadas las 17:35 ET, sella los partidos de esa fecha que aún no empezaron (una sola vez por fecha; los ya sellados se excluyen). Decide todo en hora del Este, así que la hora del servidor (Berlín) no importa. Los datos (`players.jsonl.gz`, `games.json`) y `model.json` están en `~/nba-isolated/live13/{data,model}`; las cohortes en `~/nba-isolated/live13/cohorts`, que el dashboard ya monta en solo lectura.

Ensayo en el servidor (2026-10-21 15:49 UTC, carpeta de pruebas ya borrada): 11 partidos, 44 pronósticos, reporte de las 11:45 ET, hash del modelo aceptado.

Activación (pendiente de visto bueno): una línea en el crontab de `qf`:
```
*/10 * * * * /home/qf/nba-isolated/live13/producer.sh >> /home/qf/.local/share/quantfut/nba_live13.log 2>&1
```
Vuelta atrás: quitar esa línea; las cohortes selladas se quedan y el dashboard sigue igual. Límite conocido: cada sellado vuelve a leer los partidos terminados de la temporada (≈8 páginas por día transcurrido); si se vuelve pesado, cachear `completed_games.json`.
