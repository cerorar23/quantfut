# NBA: ejecución de scrapers y recuperación histórica — 6 de octubre de 2026

Se ejecutaron los componentes indicados en la tabla y se conservan los bloqueos reales. **Se añaden 53 boxscores de pretemporada y 325 partidos de rotaciones**, en versiones separadas que preservan todos los datos previamente aceptados. Java y el toolkit/MCP solicitado de ZenRows están instalados localmente. No se declara ejecutado cada repositorio ni completado todo el histórico.

## Incremento aceptado

| Datos | Antes | Después | Pendiente |
|---|---:|---:|---:|
| Filas individuales | 159,643 | 161,546 | — |
| Boxscores regulares, cinco temporadas | 6,055 / 6,150 | 6,055 / 6,150 | 95 |
| Boxscores de pretemporada 2025–26 | 14 / 71 | 67 / 71 | 4 |
| Rotaciones regulares cronológicas | 5,168 | 5,493 | 562 entre los 6,055 boxscores aceptados |
| Tramos cronológicos por equipo | 217,619 | 231,075 | — |
| Nuevas fechas médicas | — | 0 | 330; además 13 nombres sin ID |
| Props históricos de rebotes | 20 juegos / 40 snapshots | 20 juegos / 40 snapshots | Otros mercados y temporadas |

Los 95 regulares sin boxscore aceptado tampoco quedan cubiertos por el censo de rotaciones aceptadas. No interpretar 562 pendientes como cobertura completa de los 6,150 partidos de calendario.

## Ejecución por repositorio

| Repositorio | Estado real | Componente / límite |
|---|---|---|
| [swar/nba_api](https://github.com/swar/nba_api) | executed | GitHub Live BoxScore plus published stats 1.11.4 BoxScoreTraditionalV3 |
| [dblackrun/pbpstats](https://github.com/dblackrun/pbpstats) | executed | native EnhancedPbp stats_nba file loader, version 1.3.11 |
| [ramirobentes/nba_pbp_data](https://github.com/ramirobentes/nba_pbp_data) | dataset_executed | pinned CSV lineups independently replayed for candidate acceptance |
| [shufinskiy/nba-on-court](https://github.com/shufinskiy/nba-on-court) | executed | players_on_court with retry=0 and network blocked |
| [mrees002/nba-injury-database](https://github.com/mrees002/nba-injury-database) | executed | parse_report_pdf, CDXReportDiscovery, NBAReportClient |
| [mxufc29/nbainjuries](https://github.com/mxufc29/nbainjuries) | executed | injury.get_reportdata(local=True), Java/tabula |
| [Professor-Pete/2024-2025-injury_analysis](https://github.com/Professor-Pete/2024-2025-injury_analysis) | executed | upstream PDF parse |
| [jaebradley/basketball_reference_web_scraper](https://github.com/jaebradley/basketball_reference_web_scraper) | executed_blocked | player_box_scores public upstream call |
| [sportsdataverse/oddsapiR](https://github.com/sportsdataverse/oddsapiR) | reviewed_not_executed | Rscript unavailable; The Odds API historical acquisition previously executed using project Python adapter |
| [nickth3man/basketball-data-index](https://github.com/nickth3man/basketball-data-index) | reviewed_not_executed | Index not demonstrated as a downloadable complete historical archive; prior fixed tree audit preserved |
| [neeljshah/court-vision](https://github.com/neeljshah/court-vision) | reviewed_not_executed | Forecasting project excluded from dataset reconstruction; prior fixed tree/license review preserved |
| [ANickFlower/nba-props-app](https://github.com/ANickFlower/nba-props-app) | reviewed_not_executed | README describes current props via The Odds API and locally generated reports, not a demonstrated full historical backfill |

Las siete adquisiciones de código de este lote tienen commits, originales y manifiestos: 104 archivos verifican tamaño, Git blob SHA-1 y SHA256. pbpstats 1.3.11 ya estaba aislado mediante wheel verificado. Para NBA Stats se ejecutó la versión publicada nba_api 1.11.4; la prueba del cliente Live procede del código GitHub fijado. No se atribuye identidad byte a byte entre ambos paquetes.

La propuesta de la imagen necesita correcciones: BoxScoreTraditionalV3 no garantiza minutos válidos, segundos exactos de tracking o convocatoria completa en todos los juegos. Se recibieron los 152 pendientes, pero solo 53 pasan el contrato actual; ejemplos reales conservados: 0022300089, Desmond Bane: `33:60`; 0022300835, Jordan Clarkson: `26:60`; 0022300938, Duop Reath: `12:60`. No se convierte `:60` al minuto siguiente. Un roster source se conserva completo; la ausencia de un jugador de ese roster no prueba DNP. Las funciones ESPN de hoopR tampoco comparten IDs/esquema automáticamente con NBA Stats.

La aplicación [ANickFlower/nba-props-app](https://github.com/ANickFlower/nba-props-app) documenta cuotas actuales mediante The Odds API y reportes locales; eso no acredita cuotas históricas gratuitas de todas las casas. El [índice basketball-data-index](https://github.com/nickth3man/basketball-data-index) anuncia datasets en README, cuya presencia debe verificarse en archivos descargables. La revisión anterior y su árbol fijado se conservan. [court-vision](https://github.com/neeljshah/court-vision) describe un sistema de pronósticos; no se ejecutaron sus modelos para esta recuperación.

## Contrato de aceptación y límites

Los boxscores nuevos conservan IDs, comentarios DNP/DND/NWT, minutos MM:SS y recepción UTC. Se contrastan fecha/localía con calendario, dos equipos, identidad única, descomposición de puntos/rebotes, conteos de tiro, sumas individuales/equipo y PRA de la referencia. No se fuerza ninguna reconciliación; permanecen los originales y diagnósticos de rechazo. La tolerancia previa de minutos por equipo sigue siendo 0.15 minutos.

El [archivo público de pbpstats](https://pbpstats.s3.amazonaws.com/data.zip) contiene 174,840 miembros, 709,011,107 bytes y última modificación 11-abr-2023. Mediante rangos HTTP/ETag se conservaron 2,033 miembros relevantes y 30,817,610 bytes de bloques, con hashes y CRC de ZIP; contiene 405 PBP de los candidatos. Su antigüedad impide completar temporadas recientes.

V2 identifica explícitamente jugador saliente y entrante. Se traducen esos IDs a la interfaz del reconstructor, sin resolver entradas por coincidencia difusa. La aceptación exige cinco titulares demostrados por equipo/período desde eventos raw, actores en cancha, orden temporal, sustituciones, marcador y minutos individuales con el presupuesto previo de un segundo por intervalo continuo del jugador. Luego exige acuerdo con Ramiro y el loader nativo EnhancedPbp de pbpstats. No se rellenan titulares con quintetos de Ramiro. La copia de trabajo de pbpstats está separada del raw; en los aceptados no hubo reordenamientos persistidos. Los seis ensayos nba-on-court coinciden sin diferencia de reloj. Estos métodos pueden compartir origen NBA, por lo que no son tres procedencias independientes.

Java Temurin JRE 17.0.20.1 se conserva dentro de `apps/nba/.local/tools/github_scrapers_20261006/java/`, sin instalar globalmente. El parser nbainjuries usa dependencias aisladas compatibles, incluido JPype 1.5.2; el wheel JPype 1.7.1 descargado inicialmente no es el runtime efectivo de esa prueba. Los tres parsers coinciden en jugador/estado para seis PDFs y 398 filas nominales, 18 comparaciones. Son PDFs ya disponibles: no añaden fechas. CDX devolvió 503 y el PDF médico pendiente 403; ambos se conservaron y detuvieron la fuente. Basketball Reference y NBA Live también devolvieron 403.

Rscript no está disponible: oddsapiR se revisó y descargó, no se ejecutó. El histórico de cuotas existente proviene del adaptador Python y mantiene 420 créditos de su límite previo 500. Este lote consume cero créditos nuevos; no amplía mercados de props o contratos de liquidación. Las cuotas deportivas no se recuperan retroactivamente solo instalando un wrapper o guardando reportes diarios nuevos.

## ZenRows solicitado

Toolkit CLI 1.3.1 instalado con ocho skills; MCP 2.4.0 registrado mediante Claude Code con alcance del proyecto. La configuración usa `npx -y @zenrows/mcp@2.4.0`. La prueba stdio `initialize` y `tools/list` pasó y devolvió 44 herramientas. No se llamó scrape/browser/account_usage: cero llamadas a la API, sin prueba de validez de clave/cuota. La credencial queda en los archivos locales excluidos de Git `.zenrows/secrets.json` y `.mcp.json`; no se incorpora a evidencias.

Para cargar el servidor, abrir una nueva sesión de Claude Code desde este proyecto. Si Claude presenta su revisión de MCP del proyecto, habilitar el servidor ZenRows. El registro en Claude no lo agrega automáticamente a las herramientas disponibles de esta sesión de Codex. Esta ejecución no usó rotación de IP para reintentar proveedores bloqueados.

## Verificación y reproducción

Se verificaron todas las filas previas sin cambios, 53 rosters completos del source, 1,490 minutos originales de participantes, 231,075 quintetos, 44,402 segmentos equipo/período y 117,237 reconciliaciones individuales. Once controles adversariales rechazan corrupción de jugador, partido, localía, reloj, rebotes, entrada de sustitución y marcador. Se verificaron 2,033 miembros raw, 39 archivos propios NBA congelados y las 225 evidencias previas.

Harness: 693 pruebas antes y 693 después; NBA: 172 pruebas. Docker no disponible. Se conservan intentos fallidos por acceso restringido a ejecutables, temporales de pytest sin directorio padre y serialización de NaN en el primer output nba-on-court; corregidos en la ejecución final, sin alterar quintetos, relojes ni umbrales.

Outputs finales:

- `apps/nba/.local/normalized/github_scrapers_boxes_20261006/player_games.jsonl.gz`: 161,546 filas.
- `apps/nba/.local/normalized/github_scrapers_boxes_20261006/new_player_games.jsonl.gz`: incremento de 1,903 filas.
- `apps/nba/.local/normalized/github_scrapers_rotations_20261006/combined_games.jsonl.gz`: 5,493 juegos / 231,075 tramos.
- `apps/nba/.local/normalized/github_scrapers_rotations_20261006/new_games.jsonl.gz`: 325 incrementos.
- `apps/nba/.local/normalized/github_scrapers_execution_20261006/report.json`: ejecución, métricas y límites por repositorio.
- `apps/nba/.local/normalized/github_scrapers_verification_20261006.json`: controles completos y preservación.

Los scripts y manifests se sellan en NBA-RUN-037, mediante el ledger local y hashes; no hay anclaje externo ni revisión independiente. Para reproducir auditorías se utilizan los scripts archivados con una carpeta de salida nueva: los scripts rechazan sobrescribir una salida existente. No se cambiaron modelo, puertas, entrenamiento o publicación de picks.
