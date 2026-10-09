# Fuentes gratuitas NBA: inventario verificado

Fecha de trabajo del cliente: 2026-10-04. Archivos NBA locales exclusivamente
en `apps/nba/.local`; fútbol no recibe estos datos. Se consultaron README,
diccionarios y archivos reales de GitHub, sin ejecutar scripts externos.

## Selección y diferencias de cobertura

| Fuente | Aporte | Verificación realizada | Límite para este proyecto |
|---|---|---|---|
| [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data) | Jugadas, tiros; otros feeds y matchups disponibles | Inventario completo de 529 archivos; descarga de una representación PBP v3 y tiros, regular/playoffs, para 30 temporadas disponibles | Conteos por partido deben contrastarse contra calendario; datos retrospectivos |
| [llimllib/nba_data](https://github.com/llimllib/nba_data) | Box scores individuales/equipos y estadísticas avanzadas | Descargados 10 Parquet, README y metadata, años de finalización 2022–2026 | 2022–2024 individuales tienen solo 15 partidos/año, con duplicados; no histórico individual completo |
| [sportsdataverse/hoopR-data](https://github.com/sportsdataverse/hoopR-data) | Box scores ESPN y calendarios | Descargados 66 Parquet: 22 por familia, años 2002–2023 | IDs ESPN distintos de NBA; últimos box scores disponibles terminan 2-abr-2023 |
| [swar/nba_api](https://github.com/swar/nba_api) | Cliente/documentación de endpoints oficiales | Documentación examinada; acceso oficial probado desde este host | No es un archivo de datos; CDN devolvió 403 y stats agotó timeout |
| [dblackrun/pbpstats](https://github.com/dblackrun/pbpstats) | Parser de posesiones y correcciones PBP | Documentación de [quickstart](https://github.com/dblackrun/pbpstats/blob/main/docs/quickstart.rst) examinada | No elimina la necesidad de datos ni de corregir eventos/rotaciones |

En shufinskiy el número representa el **inicio** de temporada: 2025 equivale
a 2025-26. En llimllib representa el **final**: 2026 equivale a 2025-26.
Confundir ambas convenciones desplaza una temporada entera.

Commits capturados:

- shufinskiy: `e829d4678be1e075f99e5d41a1c5f97089be446b`.
- llimllib: `9252ea665d8ea68ad20aa3209a6546381066fd98`.
- hoopR: `24a404292a6dc1b853e89ecd7c040fb11ea28446`.

El árbol global de hoopR aparece truncado en la API de GitHub. Se resolvieron
por separado sus directorios `nba/player_box/parquet`, `nba/team_box/parquet`
y `nba/schedules/parquet`, conservando los inventarios. No se usa un árbol
truncado como prueba de que una temporada no existe en todo el proyecto.

## Descarga realizada y reglas de integridad

De shufinskiy se seleccionaron 124 archivos: 120 datasets comprimidos y cuatro
documentos. Total esperado/verificado en descarga: **325.722.778 bytes**.
La lectura de los 120 datasets contabilizó **24.606.063 filas** de jugadas y
tiros; ambos representan los mismos encuentros en tablas distintas, por lo
que no son 24 millones de observaciones independientes. En 2025-26 aparecen
1.230 IDs regulares y 85 de playoffs tanto en PBP como en tiros. El PBP de
2012-13 contiene 1.213 IDs: revisar el calendario antes de considerarlo completo.

No se descargaron todas las representaciones redundantes del mismo partido
ni WNBA. Jugadas v3 y tiros cubren archivos de 1996-97 a 2025-26; eso describe
el rango de archivos disponibles, no certifica aún ausencia de huecos.

De hoopR se descargaron **20.488.994 bytes**, 66 archivos. Auditoría de tablas:
739.524 filas individuales, 56.136 filas de equipos y 28.222 de calendario.
No se han unido a NBA. En 2022-23 hay 1.176 partidos en box scores mientras
el calendario contiene 1.232 IDs; el calendario también requiere depurar
estados/cancelaciones antes de usarlo como denominador de partidos jugados.

Cada captura conserva commit, ruta original, primera recepción UTC y SHA256.
Las descargas nuevas también verifican tamaño y SHA1 del blob Git. Una
reanudación conserva la hora original; una discrepancia detiene el proceso.
Un 403/429 detiene la fuente sin evasión ni reintento ciego. Los tar se leen
sin ejecutar código ni extraer rutas arbitrarias.

## Auditoría de box scores recientes

La normalización actual exige dos equipos, identidad estable por ID,
deduplicación, suma de minutos compatible con duración del encuentro y
reconciliación de puntos/rebotes/asistencias por equipo. No convierte DNP
en una aparición de cero minutos. Un conflicto pone el partido en cuarentena.

En llimllib hay valores como `30:60` en minutos y duraciones de equipo
inferiores a 48. Se conservan raw y se rechazan bajo el contrato inicial;
no se reparan silenciosamente. Para recuperarlos hace falta contrastar otra
fuente y registrar la transformación. La cuarentena puede sesgar la muestra.

El primer dataset normalizado contiene 67.066 filas. En temporada regular
2024-25: 1.179 partidos reconciliados de 1.230 de referencia. En 2025-26:
1.151 de 1.224 referencias válidas. El raw original de equipos tiene 1.230
IDs regulares de 2025-26; excluir duraciones inválidas reduce el denominador.
Sobre los 1.230 IDs raw, la cobertura reconciliada de 2025-26 es **93,58%**.
No interpretar 94,04% sobre referencias válidas como cobertura del total NBA.

## Fuentes examinadas que no resuelven la descarga

[nickth3man/basketball-data-index](https://github.com/nickth3man/basketball-data-index)
describe CSV grandes, cuotas y PBP, pero el árbol público examinado solo
incluye 88 archivos y no incluye los grandes datasets anunciados. Es un
índice/código, no se selecciona como archivo descargable comprobado.

[kineticloom/plydb-fun-nba-analyst](https://github.com/kineticloom/plydb-fun-nba-analyst)
documenta acceso al dataset de [Eoin A. Moore en Kaggle](https://www.kaggle.com/datasets/eoinamoore/historical-nba-data-and-player-box-scores).
Es otra opción para box scores antiguos, pero no se descargó ni auditó aquí.
No confundir scripts para descargar datos externos con datasets incluidos.

La licencia Apache-2.0 está presente en shufinskiy; la API de GitHub no
identificó licencia en llimllib/hoopR-data. Esto inventaría los repositorios,
sin afirmar que los derechos de toda fuente subyacente permitan redistribución
comercial. No se publica ni revende raw en esta etapa de investigación local.

## Lo que todavía falta para pronósticos de 2026-27

1. Comparar IDs, fechas y finales de PBP/tiros contra calendarios por régimen.
2. Resolver ID ESPN→NBA con tabla verificable; nunca unir por número o nombre
   sin evidencia. Usar otra fuente para cubrir box scores 2023-24 incompletos.
3. Capturar rosters, calendario y disponibilidad actuales con recepción real.
   Un comentario de lesión en un box score posterior no es noticia prepartido.
4. Obtener líneas, precios, reglas de liquidación y cierre comparables. Ninguno
   de los archivos descargados aporta un histórico completo de props/cuotas
   con timestamps prepartido, noticias o tracking privado de toda la NBA.

Los informes ejecutables viven en `apps/nba/.local/normalized/coverage.json`,
`apps/nba/.local/reports/hoopr_coverage.json` y
`apps/nba/.local/reports/pbp_coverage.json`. El registro maestro enlaza evidencia
con sus hashes; las puertas completas siguen sujetas a revisión.
