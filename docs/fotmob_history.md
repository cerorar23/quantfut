# Histórico FotMob: 2024 a 3-oct-2026

Descarga puntual solicitada por el usuario para las 23 ligas de QuantFut,
Champions League y Europa League. Los datos nuevos vendrán de otra API.
Este proceso escribe archivos locales, sin modificar Postgres ni el cron.

## Archivos

Directorio: `.local/fotmob-history/2024-01-01_2026-10-03/`.

- `manifest.json`: inventario por competición/temporada y lista de partidos.
- `matches.csv`: una fila por partido, xG y estadísticas numéricas. Incluye
  pendientes y errores con `download_status`; solo `with_xg` tiene ambos xG.
- `coverage.csv` y `coverage.json`: avance y cobertura de las 25 competiciones.
- `raw/leagues/*.json.gz`: calendarios originales.
- `raw/matches/*.json.gz`: detalle original completo, incluidas alineaciones,
  jugadores, tiros y eventos cuando FotMob los publica.
- `*.meta.json`: URL, hora real de descarga y SHA-256 de cada respuesta original.
- `rows/*.json`: puntos de reanudación de la extracción.
- `access-denied.json`: motivo si el servidor deniega el acceso o aplica un límite.
- `process.json`, `download.log` y `download-errors.log`: proceso y salida de la
  descarga reanudada en segundo plano en Windows.

El inventario inicial descubrió 22.461 partidos terminados en 96 temporadas o
torneos, sin errores de calendario. Esto no equivale a 22.461 partidos con xG.
La cobertura definitiva está en `coverage.json`: `download_complete` solo es
verdadero cuando termina todo el inventario sin pendientes ni errores. Los
partidos terminados sin xG son resultados válidos, identificados como `missing_xg`.

## Reanudar

Desde la raíz del proyecto, con Python 3.12 y `PYTHONPATH=src`:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location).Path 'src'
python -m qf.ingest.fotmob_history --start 2024-01-01 --end 2026-10-03 --output '.local/fotmob-history/2024-01-01_2026-10-03'
```

El módulo usa solo la biblioteca estándar. `--inventory-only` descarga únicamente
los calendarios. Por defecto emplea cuatro trabajadores y una separación global
de 0,5 segundos entre solicitudes. Las respuestas guardadas se reutilizan y los
errores de partidos se vuelven a intentar al reanudar. No ejecutar dos descargas
simultáneas contra la misma carpeta.

## Criterios

- Fechas del 1-ene-2024 al 3-oct-2026, inclusive, en America/Mexico_City.
- Incluye la parte de 2023/24 jugada en 2024, Apertura/Clausura y playoffs que
  forman parte de los calendarios de las competiciones seleccionadas.
- Excluye encuentros sin finalizar, cancelados y resultados administrativos.
- Deduplica por ID de FotMob y valida ID, competición, equipos y fecha del detalle.
  Las ediciones con ID de torneo propio deben declarar la liga seleccionada
  en `parentLeagueId`.
- Usa las estadísticas del periodo `All` y los valores numéricos `rawStats`.
  Un xG de cero se conserva; un dato ausente queda vacío, nunca se convierte a cero.
- Guarda la hora real de captura. Descargar un histórico hoy no demuestra que
  ese valor revisado estuviera disponible en la fecha del partido.
- Se detiene ante HTTP 401, 403 o 429 y no evita controles de acceso.

Referencia de rutas y cliente: [Public-FotMob-API](https://github.com/pseudo-r/Public-FotMob-API).
La documentación del repositorio y su licencia no conceden derechos sobre los
datos de FotMob; su [solicitud de retirada](https://github.com/pseudo-r/Public-FotMob-API/issues/1)
sigue abierta.
