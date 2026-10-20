# Tenis: verificación de los repositorios y fuentes propuestos

Fecha: 16 de octubre de 2026. Revisión de documentación, código y muestras reales descargadas. No se ejecutaron modelos ni scrapers de terceros, ni se contrataron servicios.

Actualización posterior a esta revisión: el usuario autorizó la extracción completa y la primera implementación propia; ver [resultados del motor local](tenis_primera_version_y_resultados_20261016.md).

## Resultado

**TennisMyLife es el candidato más prometedor encontrado para ampliar el historial de saque/resto.** La fuente aparece en el actualizador de gmalbert y permite descargar CSV directamente. Ya se inspeccionaron archivos de ATP, Challenger y WTA de 2026 y tres archivos de torneos en curso. Esto acredita acceso y presencia de campos, no cobertura completa ni precisión del motor.

The Odds API continúa como fuente elegida de precios. El calendario futuro y el enlace temporal/identitario entre fuentes siguen pendientes de una prueba real.

| Recurso | Comprobación | Uso propuesto |
|---|---|---|
| gmalbert/tennis-predictions | Repositorio existente, commit del 16-oct-2026; ingesta, Elo, entrenamiento y Streamlit | Referencia de componentes y comparación; adaptar tras revisar cada parte |
| panaC/tennis-dataset | Repositorio existente; último commit 10-nov-2018; JavaScript/Puppeteer | Referencia histórica, no dependencia operativa comprobada |
| Live Tennis API | Servicio y documentación existentes; SDK oficial enlazado en GitLab | Candidato a agenda futura; detalles e historial dependen del producto/plan |
| Actores de Flashscore en Apify | Existen varios, con entradas, precios y alcances diferentes | Candidatos para una prueba acotada, sin asumir funcionamiento por su descripción |
| TennisMyLife directo | Se descargaron seis CSV actuales e inspeccionaron sus conteos | Candidato principal para ampliación del historial |

## gmalbert/tennis-predictions

Versión revisada: `3d132eec7adc2a075ceb9f895e368b0630f3e053`, 16-oct-2026 09:24:47 UTC. La fecha de actualización indicada por el usuario queda confirmada. [Repositorio](https://github.com/gmalbert/tennis-predictions).

Se revisaron README, licencia, features.py, train.py, predict.py, el actualizador TML y los scrapers de Flashscore/Tennis Abstract, además de dos muestras CSV de 2026. No se cargaron archivos pickle ni se instalaron sus dependencias.

Hallazgos relevantes:

1. `train.py` entrena clasificadores de ganador, como árboles, Random Forest y XGBoost. En estos módulos no se implementa la capa de saque/resto bayesiana y distribución conjunta de juegos/sets requerida por nuestro diseño. [Entrenamiento revisado](https://github.com/gmalbert/tennis-predictions/blob/3d132eec7adc2a075ceb9f895e368b0630f3e053/train.py).
2. El modelo guardado se elige por accuracy del conjunto denominado test. Ese conjunto pasa a intervenir en la selección; necesitamos validación y una prueba final reservada. La referencia Elo de ese entrenamiento usa predicciones 0/1 para Brier/log-loss; la comparación probabilística debe usar la probabilidad Elo. Esto no prueba que todos sus resultados estén mal, pero impide adoptarlos como evidencia suficiente.
3. En `features.py`, la métrica denominada segundo saque ganado divide `2ndWon` por `svpt`. Para la proporción condicional del segundo saque, el denominador es `svpt − 1stIn`. Las variables de saque calculadas tampoco figuran en la lista central `FEATURE_COLS` inspeccionada. [Variables revisadas](https://github.com/gmalbert/tennis-predictions/blob/3d132eec7adc2a075ceb9f895e368b0630f3e053/features.py).
4. `scraper_flashscore.py` produce resultados, pero asigna `None` a aces, dobles faltas, puntos de servicio y puntos ganados al primero/segundo. Su presencia no acredita extracción de las estadísticas que necesitamos. [Scraper revisado](https://github.com/gmalbert/tennis-predictions/blob/3d132eec7adc2a075ceb9f895e368b0630f3e053/scraper_flashscore.py).
5. El README llama permisivo al código, mientras que el archivo LICENSE y el metadato de GitHub indican GPL-3.0. No se ha incorporado código a la aplicación. La licencia del código y la procedencia de los datos deben tratarse por separado. [LICENSE](https://github.com/gmalbert/tennis-predictions/blob/3d132eec7adc2a075ceb9f895e368b0630f3e053/LICENSE).

La reutilización más inmediata es estudiar su descubrimiento de fuentes, caché, normalización y organización. El motor matemático y la evaluación temporal necesitan implementación propia o adaptación comprobada.

## TennisMyLife: prueba real de datos

El actualizador de gmalbert apunta a `https://stats.tennismylife.org/data`. Se comprobó directamente esa fuente. Los dos archivos ATP/Challenger anuales de 2026 fueron idénticos por contenido a las copias del commit revisado.

| Archivo | Filas | Filas con conteos de saque dentro de límites básicos | Filas tras apartar también todas las claves repetidas dentro del archivo |
|---|---:|---:|---:|
| 2026.csv, ATP | 2.481 | 2.433 | 2.432 |
| 2026_challenger.csv | 6.255 | 6.234 | 6.172 |
| 2026_wta.csv | 2.319 | 2.300 | 2.300 |
| ongoing_tourneys.csv | 92 | 91 | 91 |
| challenger_ongoing_tourneys.csv | 165 | 165 | 165 |
| wta_ongoing_tourneys.csv | 52 | 52 | 52 |

Son **11.364 filas descargadas**. La última columna solo aplica controles preliminares dentro de cada archivo: no es una base canónica y no se sumará al corpus MCP como si fueran partidos nuevos sin reconciliar identidades y duplicación entre fuentes.

Los controles requieren los ocho campos de saque de ambos jugadores, números de puntos positivos, primer saque dentro del total, ganados al primero dentro de primeros dentro y ganados al segundo dentro de los restantes. Se encontraron claves `tourney_id, match_num` repetidas: deben investigarse por participante, cuadro y ronda antes de decidir si son duplicados o identidades incompletas.

La documentación primaria define `tourney_date` como la semana del torneo; no sustituye la hora real del partido. Los archivos de torneos en curso contienen filas con ganador/perdedor y resultado, no acreditan una agenda futura. La página publica una declaración MIT para la base y advierte que la fiabilidad de los archivos WTA aún está en revisión. [Base y diccionario oficiales](https://stats.tennismylife.org/tennis-match-database).

El catálogo público permite descubrir archivos y sus fechas de modificación. La ruta Challenger en curso enlazada inicialmente devolvió 404; se utilizó la ruta vigente indicada por ese catálogo, `challenger_ongoing_tourneys.csv`. No se necesitó proxy.

Pendiente: descargar temporadas anteriores con un plan de ingesta, separar cuadros y categorías, resolver IDs, comprobar retiros y cronología, consolidar histórico/anual/en curso y medir cobertura contra calendarios independientes. La primera recepción local es de octubre de 2026; no acredita que cada dato estuviera disponible en su fecha histórica.

## panaC/tennis-dataset

Versión consultada: `7b7e9b8744deac11b0ded1a6766c0a53ac13d709`, último commit 10-nov-2018. El código revisado utiliza Node.js, Puppeteer 1.7 y Sequelize; extrae mediante selectores HTML de aquella versión de Flashscore. La descripción del usuario como Python puro no corresponde a este repositorio.

El package.json del componente Flashscore declara ISC, pero el metadato de licencia del repositorio completo es nulo. No se ha acreditado una licencia uniforme de todos los componentes ni compatibilidad con la web actual. [Código y README](https://github.com/panaC/tennis-dataset).

## Live Tennis API

La documentación oficial enlaza el SDK Python en **GitLab**, no en la URL de GitHub propuesta, que devolvió 404. No se comprobó la existencia del método `client.list_upcoming_matches()` en una versión del SDK. La ruta REST documentada es `/matches?status=upcoming`; también existe `/fixtures`.

Planes publicados al revisar:

- FREE: calendario/estado actual, 100 solicitudes al día y 30 por minuto.
- BASIC: historial y secuencias históricas, 9,99 USD/mes.
- ULTRA: el endpoint `/matches/{matchId}/statistics` de estadísticas detalladas figura en este nivel, publicado a 99,99 USD/mes.

La documentación también menciona una muestra limitada de consultas históricas para claves gratuitas. No equivale a un historial gratuito ilimitado. Los planes Historical tienen otro desglose; antes de contratar hay que confirmar qué campos y grado de reconstrucción entregan. No se solicitó clave ni se hicieron llamadas autenticadas. [Precios](https://livetennisapi.com/pricing), [referencia](https://docs.livetennisapi.com/reference.html), [clientes oficiales](https://docs.livetennisapi.com/llms.txt).

Los datos reconstruidos o derivados del marcador necesitan etiquetas distintas de los puntos observados; nunca se usarán probabilidades producidas por el proveedor como si fueran resultados deportivos observados para entrenar nuestro propio modelo.

## Apify y Flashscore

Se verificaron las páginas de `parsebird/flashscore-tennis-scraper`, `webdata_labs/flashscore-tennis-scraper` y `omkar-cloud/flashscore-tennis-scraper`. Sus alcances difieren: uno enumera marcador/partidos, otros anuncian detalles con un coste adicional. Una entrada de fechas para ±7 días no acredita recuperación masiva de temporadas anteriores ni los últimos cinco partidos de cualquier jugador.

Las afirmaciones de velocidad, calidad y coste total son comerciales, no resultados medidos en este proyecto. No se ejecutaron actores ni se abrió una cuenta. La prueba que falta debe exigir numeradores/denominadores, conservar la respuesta original y comparar un pequeño conjunto de partidos finalizados con su ficha de origen. [Parsebird](https://apify.com/parsebird/flashscore-tennis-scraper), [Webdata Labs y entradas](https://apify.com/webdata_labs/flashscore-tennis-scraper/input-schema), [Omkar](https://apify.com/omkar-cloud/flashscore-tennis-scraper).

## Decisión de arquitectura tras esta revisión

1. **Historial:** priorizar la auditoría y normalización de TennisMyLife directo, manteniendo MCP como fuente de detalle para investigación según sus permisos.
2. **Calendario próximo:** probar una fuente con IDs y hora; Live Tennis API FREE es candidato documentado. The Odds API también aporta los eventos de los torneos que cubre, pero no debe asumirse agenda completa del circuito.
3. **Precios:** mantener The Odds API; conocer plan, casas y límite compartido antes de gastar créditos.
4. **Cálculo deportivo:** desarrollar la capa bayesiana de saque/resto y Markov descrita en el diseño inicial. Los últimos cinco partidos pueden ser una variable; el historial de entrenamiento debe ser mayor y regularizarse.
5. **Validación:** comparar con Elo probabilístico y mercado del mismo momento, con selección en validación y prueba final reservada. No incorporar código ni modelos externos como si ya superaran esas comprobaciones.

Evidencia local: `.local/tennis_sources_20261016/` conserva las fichas GitHub, código leído, muestras originales, catálogo TML y `tennismylife_sample_audit.json` con hashes y conteos. Se verificaron los blobs Git de las dos muestras de gmalbert contra su árbol publicado. La revisión no altera los motores existentes.
