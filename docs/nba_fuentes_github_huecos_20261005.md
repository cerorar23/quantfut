# NBA: archivos para cubrir huecos de datos — 2026-10-05

Estado: descargas y auditoría de candidatos realizadas. Los nuevos archivos
todavía no alimentan el modelo. Este documento complementa
[el inventario anterior](nba_fuentes_github.md); no aprueba puertas del plan.

## Resultado por necesidad

| Necesidad | Fuente descargada | Resultado comprobado localmente | Pendiente |
|---|---|---|---|
| Históricos individuales | [SportsDataverse: player box scores](https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/nba_stats_player_boxscores) | 30 Parquet, temporadas 1996-97 a 2025-26; 1.041.847 filas, incluidas no participaciones; 17.878.574 bytes | Unir fechas, separar competiciones, reconciliar discrepancias y cuarentena de minutos |
| Lesiones reportadas históricamente | [Professor-Pete](https://github.com/Professor-Pete/2024-2025-injury_analysis) | 107.337 filas en 1.165 snapshots declarados, del 21-oct-2024 al 22-jun-2025 | Validar PDF original, zona horaria, IDs y corte anterior al inicio |
| Plantillas actuales | [Transcripción de profundidad](https://github.com/tobeyhirsch/nba-draft-pick-grader/blob/main/src/real_rosters_202627.py) | 30 equipos, 527 nombres; declara sincronización 1-sep-2026 | No acredita membresía vigente de todos los equipos al 5-oct; falta fuente actual con IDs |
| Cuotas históricas de props | [sports-odds-datasets](https://github.com/JacobiusMakes/sports-odds-datasets) y dos muestras adicionales | Archivos reales descargados; cobertura y contratos insuficientes | No existe en esta búsqueda un histórico completo validado para ROI/CLV |

Los archivos originales se conservan bajo `apps/nba/.local/raw/github/`.
Los manifiestos registran bytes, SHA256 y primera recepción local UTC.
Los archivos de repositorios se fijaron por commit y Git blob SHA1; los
assets de release se fijaron por ID y digest SHA256 publicado por GitHub.
Una URL de release puede cambiar: preservar el archivo recibido es necesario.

## Históricos: cobertura de partidos y cobertura de jugadores son distintas

SportsDataverse publica box scores derivados de endpoints NBA. Se descargó
el archivo Parquet de cada año final 1997–2026, sin instalar paquetes ni
ejecutar código del tercero. La fuente distingue tipos de temporada: no
mezclar regular, playoffs, play-in o final de copa.

Auditoría detallada reciente:

| Temporada | Filas de todos los tipos | Partidos regulares | Partidos regulares con ambos equipos conciliados en PTS/REB/AST* | Filas con minutos no vacíos inválidos, todos los tipos |
|---|---:|---:|---:|---:|
| 2021-22 | 33.848 | 1.230 | 1.230 | 64 |
| 2022-23 | 34.024 | 1.230 | 1.229 | 65 |
| 2023-24 | 34.843 | 1.230 | 1.222 | 72 |
| 2024-25 | 35.114 | 1.230 | 1.228 | 57 |
| 2025-26 | 34.786 | 1.230 | 1.219 | 81 |

\* Se sumaron estadísticas individuales por partido/equipo y se compararon
con los archivos de equipo llimllib ya recibidos. Ambos derivan de NBA:
la concordancia comprueba consistencia, no independencia de fuentes.
Los Parquet nuevos carecen de fecha de partido; se debe unir por ID con
una referencia auditada. Se encontró `MM:60`: conservar raw y aplicar la
cuarentena vigente, sin convertirlo silenciosamente a otro minuto. Minutos
vacíos y comentarios requieren contrato de participación; no equivalen a
jugador sano. No se revisó conciliación de equipos de todas las 30 temporadas.

También se descargó [maezellemillan](https://github.com/maezellemillan/nba-data-collection-2023-2025):
22.295 filas/422 jugadores en 2023-24 y 24.965/532 en 2024-25. Cada archivo
incluye los 1.230 partidos, pero solo 93 y 435 partidos, respectivamente,
conciliaron ambos equipos en PTS/REB/AST. No usar como censo completo de
jugadores. Sus minutos son enteros; en 2024-25 los IDs perdieron ceros
iniciales, cuya restauración fue explícita solo para esta auditoría.

[NocturneBear/NBA-Data-2010-2024](https://github.com/NocturneBear/NBA-Data-2010-2024)
también tiene CSV reales de box scores: inventario verificado, descarga no
realizada porque el release anterior ofrece un candidato más amplio.

## Lesiones: preservar el momento y también lo desconocido

El CSV de Professor-Pete contiene estado, motivo, jugador, equipo, partido
y fecha/hora nominal del reporte. Hay 7.769 filas `NOT YET SUBMITTED` sin
jugador: conservarlas para distinguir informe pendiente de ausencia de
designaciones. Una fila es una designación repetible en distintos horarios,
no una lesión independiente. No se detectaron claves duplicadas dentro del
mismo snapshot/partido/equipo/jugador.

Antes de usarlo como feature:

1. Verificar muestras contra los PDFs originales. En esta descarga se obtuvo
   el CSV y se leyó el parser; los PDFs no se recibieron ni validaron.
2. Verificar ET y convertir con `America/New_York`, incluyendo horario de
   verano. `game_time` perdió AM/PM: `07:30` no debe interpretarse como 07:30
   de la mañana; unir el inicio desde calendario verificado.
3. Seleccionar únicamente reportes nominalmente anteriores al corte de
   predicción, registrando precisión y evidencia de publicación. La primera
   recepción local ocurrió ahora, no en 2024; no inventar recepción histórica.
4. Resolver jugador/equipo/partido con IDs y vigencia de plantilla; registrar
   nombres sin resolver. No inferir lesión de falta de aparición en box score.
5. Mantener la participación observada y los derivados de `crossref.py` como
   resultados posteriores, nunca como noticias conocidas antes del partido.

[mrees002/nba-injury-database](https://github.com/mrees002/nba-injury-database)
aporta herramientas/metodología; no se verificó un archivo público equivalente
de todos los PDFs históricos dentro de su árbol. No se ejecutó su scraper.

## Props: las muestras no demuestran un histórico apostable

Auditoría de `prop_closing_lines_sample_50k.csv` de JacobiusMakes:

- 50.000 filas multideporte; 2.505 etiquetadas `basketball_nba`.
- 1.415 snapshots al inicio o después; 730 sin tiempos interpretables;
  360 nominalmente anteriores al inicio.
- De esas 360, 293 tienen otras claves de mercado y 14 fallan el filtro
  básico de línea/precios bilaterales. Quedan 53 candidatos preliminares.
- Esos 53 incluyen 3 filas PrizePicks y etiquetas que contradicen la clave,
  como combinaciones PRA. No son 53 contratos aprobados. Ninguna fila ha
  sido aprobada para medir ROI/CLV.
- En las 2.505 filas hay 2.809 probabilidades por lado inválidas o ausentes
  y 1.280 inconsistencias con el precio americano. Recalcular desde precio
  válido y margen; no reutilizar las probabilidades almacenadas.
- Las fechas etiquetadas NBA abarcan abril–agosto 2026. Validar competición
  y evento; no asumir temporada regular por la etiqueta NBA.

No consta aquí regla de liquidación, prórroga/periodo, actualización de la
casa ni trazabilidad completa. Que el archivo se llame «closing» no acredita
un cierre anterior al inicio. La licencia declarada del sample es CC BY 4.0;
guardar la atribución, sin extrapolarla a los otros repositorios.

Otras descargas:

| Repositorio | Archivo | Auditoría | Uso permitido por la evidencia |
|---|---|---|---|
| [DhirenShivdasani](https://github.com/DhirenShivdasani/NBA-player-prop-analysis) | `historical_prop_data.csv` | 1.390 filas, todas fechadas 31-ene-2024; sin precios/casa/hora | Ejemplo de líneas; no EV/ROI/CLV |
| El mismo | `historical_injury_data.csv` | 173 filas, 29–31 ene-2024; fechas/actualizaciones sin hora precisa | Investigación de estructura; no disponibilidad intradía comprobada |
| [sharp-lines](https://github.com/nirvikkasula/sharp-lines) | `historical_props.csv` | 962 filas, un solo timestamp; sin partido, rival o inicio | Muestra de precios; no enlace prepartido comprobado |

## Correcciones a los repositorios sugeridos

- [nba_api](https://github.com/swar/nba_api) es un cliente no oficial de
  endpoints públicos NBA. No almacena por sí solo toda la data ni garantiza
  acceso a todos los endpoints. En el inventario revisado no apareció un
  endpoint de archivo histórico de injury reports. [CommonTeamRoster](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/commonteamroster.md)
  sirve para plantillas cuando el servidor sea accesible.
- [pbpstats](https://github.com/dblackrun/pbpstats) y
  [nba-on-court](https://github.com/shufinskiy/nba-on-court) reconstruyen
  posesiones/quintetos. «Exactamente cinco en cada evento» exige controles:
  errores de eventos, sustituciones y starters pueden requerir correcciones.
- [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data) ya fue descargado
  en el trabajo previo. No resuelve por sí solo lesiones previas o cuotas.
- [hoopR](https://github.com/sportsdataverse/hoopR) es una herramienta R;
  los Parquet de SportsDataverse se pueden leer en Python. No hace falta
  cambiar el lenguaje del modelo.
- El release `nba_stats_rosters` revisado llega al año final 2026, sin asset
  2027. El README de `damionrashford/nba-predict` menciona datos de rosters,
  pero el archivo anunciado no está en el árbol público inspeccionado.

## Decisión de integración

Priorizar SportsDataverse para ampliar históricos, manteniendo la política
de cuarentena. El archivo de lesiones es candidato para E7/E18 después de
validar tiempos y enlazar IDs. Las muestras de cuotas quedan en investigación
de contratos; falta una captura prospectiva utilizable. Las plantillas
actuales requieren verificación de todos los equipos. Ningún candidato
modifica todavía las métricas ni habilita picks o Telegram.

Auditoría numérica y hashes: `apps/nba/.local/reports/gap_sources_20261005.json`.
Registro de ejecución: `NBA-RUN-004` en `nba_plan_fases_auditoria.json`.
