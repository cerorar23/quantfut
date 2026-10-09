# NBA — revisión de player-performance-forecaster, 2026-10-05

**Sí sirve como referencia para descargar estadísticas históricas NBA desde la API; no contiene un histórico completo listo para importar.** Se revisó el commit `7a0c22f6e26e8ec6854742dd88abf755d10733f4` de [EdgarParra565/player-performance-forecaster](https://github.com/EdgarParra565/player-performance-forecaster). Se inventariaron los 365 archivos de main y se descargaron 14 archivos relevantes con tamaño, Git blob SHA-1 y SHA-256 verificados, sin ejecutar el proyecto.

## Descargador aprovechable

[`nba_results_ingestion.py`](https://github.com/EdgarParra565/player-performance-forecaster/blob/7a0c22f6e26e8ec6854742dd88abf755d10733f4/nba_model/data/nba_results_ingestion.py) utiliza `nba_api`: `LeagueGameFinder` obtiene filas equipo/partido y `PlayerGameLogs` obtiene registros individuales de toda la liga por temporada. Estos incluyen minutos, puntos, rebotes, asistencias, tiros, robos, bloqueos, pérdidas y IDs NBA. Permite especificar temporadas; los valores predeterminados son 2023–24, 2024–25 y 2025–26. Guarda resultados en una base SQLite local.

La descarga masiva por liga/temporada es una idea útil para completar los huecos de nuestro histórico. No usa The Odds API para esas estadísticas y, por tanto, ese módulo no consume sus créditos. La disponibilidad real de los endpoints debe comprobarse: el propio workflow diario comenta que stats.nba.com devuelve timeouts desde GitHub Actions. En esta revisión no se hicieron consultas NBA ni se acreditó una descarga exitosa del módulo.

## Datos realmente publicados

El único CSV en el árbol, `nba_model/data/player_game_logs.csv`, tiene **cero bytes**. No hay SQLite, Parquet u otro exporte tabular de partidos en ese árbol. `.gitignore` excluye CSV, bases SQLite y `data/raw/`.

`data/DATABASE_INVENTORY.txt` declara 91,654 registros individuales y 8,390 filas equipo/partido, pero es un informe del autor generado el 2026-06-04, no la base de datos. No se verificó su contenido con los registros originales. Su desglose incluye equipos de exhibición y All-Star; la cifra agregada no acredita una cobertura homogénea de temporada regular. El inventario declara cuotas de solo 2026-03-14/15 y un único instante de snapshots, no una serie multitemporada de props.

Releases: cero. La API de Actions devuelve 90 artefactos, todos denominados `etl-artifacts-*`, de hasta 2,330 bytes. El workflow publica reportes/logs y no incluye la ruta de la base de datos. No se descargaron los ZIP ni se verificó su contenido; esos metadatos no acreditan un dataset histórico descargable.

## Cambios necesarios antes de usar la lógica

- **Temporada y competición explícitas:** `DEFAULT_SEASON_TYPES` está definido pero no se usa en las consultas. La consulta individual no fija `season_type_nullable`; el README anuncia regular más playoffs sin que el código lo garantice explícitamente. Consultar cada tipo por separado y contrastar IDs/censo contra calendario; aislar pretemporada, play-in y All-Star.
- **Caché por temporada:** `data_loader.py` busca base/caché antes de aplicar el argumento de temporada y usa un archivo identificado solo por jugador. Además, su wrapper `load_player_logs` descarta ese argumento. No es el camino adecuado para garantizar una descarga multitemporada.
- **Minutos:** el conversor legado devuelve cero ante una cadena numérica sin `:`; exige auditoría de unidades/tipos para no convertir minutos válidos en ceros.
- **Datos auditables:** preservar respuestas originales, recepción UTC, configuración, checksums, estados incompletos y revisiones. `INSERT OR REPLACE/IGNORE` no constituye un archivo histórico de disponibilidad previa al partido.
- **Cuotas reales:** [`historical_odds_backfill.py`](https://github.com/EdgarParra565/player-performance-forecaster/blob/7a0c22f6e26e8ec6854742dd88abf755d10733f4/nba_model/data/historical_odds_backfill.py) toma props ya capturados, selecciona la última línea por día observado y asigna `-110` a ambos lados. La fecha de observación se utiliza como fecha de partido. Eso no reconstruye precios reales previos al partido ni reglas de liquidación, y no se admite en nuestro backtest de valor esperado.

El benchmark publicado revisado para LeBron James declara 30 partidos y **cero apuestas**. El propio README señala benchmarks sintéticos y ausencia de validación para apostar dinero real. Ninguno de esos resultados certifica ventaja predictiva del modelo.

## Decisión para nuestro proyecto

Usar el patrón de descarga masiva `nba_api` como referencia para completar partidos faltantes, conservando nuestro pipeline NBA aislado y cruzando contra los 154,058 registros individuales ya aceptados de las cinco temporadas recientes. No importar duplicados ni sustituir el modelo por este proyecto. El módulo inspeccionado no resuelve lesiones históricas conocidas antes del partido, quintetos cronológicos o cuotas históricas auténticas; requieren sus fuentes y validaciones respectivas. El presupuesto de cuotas continúa bajo The Odds API y separado del backfill estadístico gratuito.

Archivos de referencia: `apps/nba/.local/raw/github/EdgarParra565__player-performance-forecaster/7a0c22f6e26e8ec6854742dd88abf755d10733f4/`. Inventario y metadatos: `apps/nba/.local/source_inventory/edgar_parra_20261005/`. Informe: `apps/nba/.local/reports/edgar_parra_repository_audit_20261005.json`.

**Esta revisión añadió cero registros de partidos y gastó cero créditos de The Odds API.** No se ejecutó código externo, no se instalaron dependencias ni skills del repositorio y no se modificaron código, parámetros o puertas de validación propios. No aparece una licencia declarada en el árbol consultado.
