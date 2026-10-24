# NBA — correcciones del productor en vivo v1.3 (23-oct-2026)

Corrige los errores 1-6 de `docs/nba_auditoria_motor_20261023.md`. Rama `nba/productor-correcciones` (desde `main`).
**No desplegado.** El modelo, los mercados y la regla de lesiones no cambian; la enmienda es operativa y queda en
`apps/nba/multimarket_v13_live_protocol.json` (`amendment_2026_10_23`, versión `nba-multimarket-live-1.3.1`).
Las cohortes ya selladas no se tocan y conservan la versión 1.3.

## Qué cambia
| Error | Antes | Ahora |
| --- | --- | --- |
| 1. Partidos de tarde | Un solo sellado a las 17:35 ET; 87-97 partidos por temporada nunca se pronosticaban. | Cada partido se sella en la primera pasada (cron cada 10 min) que encuentra su salto a más de 65 y como mucho 90 min. Carpeta `AAAA-MM-DD_HHMM` (hora ET del sellado). |
| 2. Sin lesiones en partidos de 18:00-18:45 ET | El reporte de las 17:30, recibido a las 17:35-17:45, no valía para ellos. | Al sellar 65-90 min antes, el último reporte se recibe antes de salto − 60 y cuenta. |
| 3. Hora del sello | `sealed_at_utc` y la recepción del reporte = inicio de la pasada. | Reloj real: cada página y el reporte se fechan al recibirse; el sello, al escribir el bundle. |
| 4. Caché | El servidor rebajaba toda la temporada en cada sellado y saltaba en silencio los partidos no finales. | El productor usa `--cache` (`/live13/cache`): box scores finales y el calendario del día (se relee cada 2 h). |
| 5. Bloqueo | Cualquier respuesta ≠ 200 se tomaba por «no hay reporte». | 403/404 = franja sin archivo, comprobado una vez con un archivo de control conocido; si el control falla, o llega otro estado, el sellado se detiene con error. |
| 6. Valor de jugadores | Solo box scores hasta 2025-26: novatos y regresos valían 0 y los valores envejecían. | Las filas de jugador de los box scores finales de 2026-27 (ya descargados) se suman a la historia. `completed_games.json` no las repite: cada partido conserva el hash del box score del que salen. |

Además, la página actual de nba.com da los minutos como `PT23M56.00S` y las archivadas como `33:15`; se aceptan los dos.

## Verificación
- Pruebas nuevas en `tests/test_multimarket_v13_live.py` y `tests/test_live_completed_cache.py`: sellado por ventana
  (incluidos un partido de 13:00 ET y uno de 18:30 ET, ambos con reporte aplicado), sin peticiones en una pasada sin
  nada pendiente, relectura del calendario, horas reales de recepción y sello, bloqueo frente a franja vacía, formatos de
  minutos y un novato valorado con sus partidos de 2026-27. Suite NBA: todo verde salvo las 3 pruebas caducadas de
  `test_paper_bundle.py` (error 8, anterior a este cambio).
- Ensayo real contra nba.com (solo lectura, carpeta temporal): 16 partidos finales del 20 al 22-oct, 548 filas de
  jugador (367 jugaron), 34 jugadores sin historia previa que ahora la tienen; segunda pasada con 0 peticiones. Reporte
  del 23-oct capturado con 1 petición y su recepción real; con una franja futura, 403 → control 200 → reporte anterior.
  No se pudo sellar una cohorte real: a esa hora todos los partidos del día ya habían empezado.
- Modelo reajustado (el hash del módulo cambió): `apps/nba/.local/normalized/nba_f6_live13_model_20261023/model.json`
  (sha256 `69e05e6b…`). `fit`, `play_probability`, `observed_share` y temporadas **idénticos** al modelo `…20261021b`.

## Despliegue (NO ejecutado; espera confirmación)
Requisitos: PR fusionado en `main`, una sola sesión desplegando, comparar lo desplegado con `main` (ver `DEPLOYS.md`).
```bash
ssh quantfut
L=$HOME/nba-isolated/live13
crontab -l > $L/crontab.before-20261023
cp -a $L/model $L/model.before-20261023 && cp -a $L/producer.sh $L/producer.sh.before-20261023
mkdir -p $L/cache   # mismos permisos que $L/cohorts (escribible por el usuario 1001 del contenedor)
# contexto desde main con git archive y core.autocrlf=false (como en el despliegue de precios), luego:
docker build -f $L/build-producer/ops/Dockerfile.live13_producer --build-arg NBA_LIVE13_BASE=nba-dashboard-live13:20261021 \
  -t nba-live13-producer:20261023 $L/build-producer
# copiar nba_f6_live13_model_20261023/model.json a $L/model/model.json (comprobar sha256 69e05e6b…)
install -m 755 $L/build-producer/ops/live13_producer.sh $L/producer.sh
```
Comprobar en la primera pasada: el log escribe `schedule/<día>.json` en la caché y no sella hasta 65-90 min antes del
primer salto; la primera cohorte nueva se llama `AAAA-MM-DD_HHMM` y su `created_at_utc` es posterior al inicio de la pasada.

**Vuelta atrás:** restaurar `producer.sh.before-20261023` y `model.before-20261023` (la imagen `nba-live13-producer:20261021`
sigue en el servidor). Las cohortes selladas con 1.3.1 se quedan; el dashboard lee las dos versiones.

## Efecto en la captura de precios (`nba-live13-price`, desplegada el 22-oct, bloqueada hasta el 1-nov)
Con varias cohortes por día, su fase `seal` pedirá un precio por cohorte y el libro (2 peticiones/día) rechazará a partir
de la segunda: la comparación con Pinnacle tendría menos partidos. Como el motor no busca ganarle al mercado, conviene
decidir antes del 1-nov si se retira esa línea de cron (vuelta atrás en `DEPLOYS.md`, entrada del 22-oct).
