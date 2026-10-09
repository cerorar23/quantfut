# NBA — descarga de austin-pesina/nba_scrapes, 2026-10-05

Se descargaron **los seis archivos completos de la rama principal**, 15,023 bytes, fijados al commit `d6d06b273d7a8818be3936f43425979db1ab92a3`. Cada archivo coincide en tamaño, Git blob SHA-1 y SHA-256. El árbol no está truncado y solo existe la rama `main`.

**El repositorio no publica ningún CSV, Parquet o base de datos descargable.** Se comprobaron releases: cero. La API pública de GitHub Actions también devolvió cero artefactos disponibles. La última ejecución consultada terminó correctamente el 2026-06-30. No se atribuye la ausencia a una causa comprobada: los artefactos pueden caducar, pero no se verificó la política específica de este repositorio. [Retención de artefactos en GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

Los archivos recibidos son:

- `player_stats_reg_season.py` y `player_stats_playoffs.py`.
- `.github/workflows/main.yml`.
- `README.md`, `pipeline.md` y `requirements.txt`.

El código extrae plantillas y game logs individuales de Basketball Reference, configura el año final `2026` y escribe resultados en Snowflake antes de exportar CSV/Parquet locales. El workflow intenta publicar un Parquet como artefacto. Los archivos de resultados no están presentes en GitHub en la revisión realizada; los archivos `.py` no son datasets.

Ese año final corresponde a **2025–26**, no selecciona automáticamente 2026–27. Los IDs son de Basketball Reference y no sustituyen nuestros IDs NBA. Los scripts no descargan lesiones previas al partido ni cuotas históricas de props; por tanto, esta fuente no sustituye el histórico de The Odds API que se está preparando.

Se revisó el código como texto/AST, **sin ejecutarlo**, cargar su `.env`, instalar dependencias o conectar con Snowflake. No existe una licencia declarada en el árbol revisado. Para generar nuevos datos desde esa lógica habría que construir un capturador independiente, con límites de peticiones, archivos locales, prevención de duplicados por traspasos y mapeo de identidades verificado. No se incorporó código de terceros al modelo.

Ubicación de la descarga:

`apps/nba/.local/raw/github/austin-pesina__nba_scrapes/d6d06b273d7a8818be3936f43425979db1ab92a3/`

El manifiesto es `manifest.json` dentro de esa carpeta. Informe de integridad y cobertura:

`apps/nba/.local/reports/austin_pesina_repository_audit_20261005.json`

**Créditos de The Odds API consumidos: cero. Filas NBA nuevas importadas: cero**, porque el repositorio ofrece herramientas de captura y no sus resultados. El modelo y sus puertas de validación permanecen sin cambios.
