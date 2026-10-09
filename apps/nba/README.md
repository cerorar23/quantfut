# QuantNBA: arranque de investigación

## Recuperación Basketball Reference

El adaptador diario contrasta fecha, local/visitante, equipos, IDs y P/R/A
con el boxscore NBA del mismo partido. Conserva los minutos de la fuente
independiente y aplica la conciliación estricta existente. Las ausencias
en la tabla no se convierten en DNP o lesiones. Cada fila nueva lleva
procedencia; las filas anteriores y su archivo permanecen intactos.
Se registran variantes únicas de sufijos generacionales omitidos y puntos
en iniciales, corroboradas por partido/equipo/P/R/A. No se admiten
generaciones contradictorias, apodos o candidatos múltiples.

```powershell
& apps/nba/.venv/Scripts/python.exe -m nba capture-bref --dates 2021-10-20 2021-10-24
& apps/nba/.venv/Scripts/python.exe -m nba recover-bref `
  --inventory apps/nba/.local/reports/backfill_inventory_20261005.json `
  --release-manifest apps/nba/.local/raw/github/sportsdataverse__sportsdataverse-data/release_97519777/manifest.json `
  --team-manifest apps/nba/.local/raw/github/9252ea665d8ea68ad20aa3209a6546381066fd98/manifest.json `
  --base-report apps/nba/.local/reports/sportsdataverse_import_v2_20261005.json `
  --output-dir apps/nba/.local/normalized/basketball_reference/NUEVA_VERSION
```

Captura: máximo 20 fechas por llamada, caché verificada, seis segundos
entre solicitudes y parada compartida ante fallo/rechazo del proveedor.
No hay reintentos automáticos ni cambio de IP. Se permite reutilizar el
piloto con `--seed-manifest`, conservando su fecha de recepción original.
Recuperación: solo regular, playoffs y play-in; pretemporada y cruces
ambiguos quedan pendientes. El directorio de salida debe ser nuevo.
Ningún comando reentrena el modelo o activa publicación de picks.

Aplicación independiente en `apps/nba`, paquete `nba`, entorno `.venv`,
dependencias y datos `.local` propios. No importa `qf`, no carga el `.env`
de fútbol ni conecta a su base. Solo utiliza configuración `NBA_*`.

Este primer incremento implementa descarga pública con commit/hashes,
auditoría de cobertura, deduplicación y reconciliación de box scores,
comparación retrospectiva de minutos/rebotes y escenarios hipotéticos.
No hay feed actual de lesiones/cuotas, servicio continuo ni envío Telegram.
`NBA_TELEGRAM_ENABLED` y `NBA_ODDS_ENABLED` no activan funciones inexistentes.

Actualización 5-oct: importación separada SportsDataverse y captura finita
de plantillas ESPN disponibles. Las lesiones incluidas en esas plantillas
se conservan raw; su vigencia y disponibilidad médica prepartido no están
validadas. No constituyen todavía un feed utilizable por el modelo.

## Ejecutar desde la raíz del proyecto en PowerShell

```powershell
# Crear el entorno con un Python 3.12 disponible, si aún no existe.
python -m venv apps/nba/.venv
& 'apps/nba/.venv/Scripts/python.exe' -m pip install -e 'apps/nba[test]'
& 'apps/nba/.venv/Scripts/python.exe' -m nba status
& 'apps/nba/.venv/Scripts/python.exe' -m nba capture --years 2022 2023 2024 2025 2026

# Sustituir COMMIT por el que devuelva capture. Se conservan todas las versiones.
& 'apps/nba/.venv/Scripts/python.exe' -m nba import 'apps/nba/.local/raw/github/COMMIT/manifest.json'
& 'apps/nba/.venv/Scripts/python.exe' -m nba backtest
& 'apps/nba/.venv/Scripts/python.exe' -m nba verify-ledger
& 'apps/nba/.venv/Scripts/python.exe' -m pytest apps/nba/tests
```

## Incremento de históricos y contexto actual

```powershell
& 'apps/nba/.venv/Scripts/python.exe' -m nba import-sdv `
  'apps/nba/.local/raw/github/sportsdataverse__sportsdataverse-data/release_97519777/manifest.json' `
  --team-manifest 'apps/nba/.local/raw/github/9252ea665d8ea68ad20aa3209a6546381066fd98/manifest.json'

# El importador devuelve dataset_path. Para un replay, indicar un directorio nuevo.
& 'apps/nba/.venv/Scripts/python.exe' -m nba backtest `
  --dataset 'RUTA_DEVUELTA/player_games.jsonl.gz' --output-dir 'DIRECTORIO_NUEVO'
& 'apps/nba/.venv/Scripts/python.exe' -m nba capture-rosters --season-year 2027
```

`import-sdv` verifica hashes/tamaño de los assets, selecciona los años finales
2022–2026, une fechas por partido/equipo NBA y valida temporada/tipo. Utiliza
las mismas reglas de minutos, deduplicación y conciliación. Guarda datasets
por hash de entradas y versión del adaptador; no reemplaza la referencia
`normalized/player_games.jsonl.gz`. Un snapshot existente alterado se rechaza.
El replay con dataset propio exige salida propia vacía y sella el hash de
datos/protocolo antes de evaluar. No repite una evaluación por un cambio de
adaptador si se demuestra que los bytes de datos son idénticos.

`capture-rosters` hace una captura de las 30 plantillas de ESPN, sin reintentos
ante denegación. Guarda primero cada respuesta con recepción UTC, URL y
hash. Valida temporada y equipo; los IDs permanecen en namespace `espn`,
sin inventar correspondencia NBA. Una afiliación duplicada marca conflicto.
El estado de plantilla «Active» y la ausencia de lesión no significan que
un jugador vaya a participar. La fecha interna de una lesión puede ser
antigua o tener semántica distinta de una actualización; conservarla.
Solo puede conocerse la respuesta desde su recepción local, nunca antes.

## Experimento de arranque de temporada

El modelo original exige diez apariciones en la misma temporada. El módulo
`startup` prueba, por separado, priors del último año para las primeras diez
apariciones observadas en el registro conciliado. `startup_protocol.json`
fija ventanas/pesos antes de la ejecución; no se buscaron parámetros por
rendimiento. Los datos históricos ya se habían inspeccionado: el resultado
es exploratorio y necesita confirmación prospectiva. Los partidos excluidos
pueden desplazar el conteo observado respecto de las diez apariciones reales.

```powershell
& 'apps/nba/.venv/Scripts/python.exe' -m nba startup-backtest `
  --dataset 'RUTA_DEVUELTA/player_games.jsonl.gz' --output-dir 'DIRECTORIO_NUEVO'
& 'apps/nba/.venv/Scripts/python.exe' -m nba startup-scenario `
  --dataset 'RUTA_DEVUELTA/player_games.jsonl.gz' --player-id 203999 `
  --as-of 2026-10-05 --season 2026-27
```

La media móvil de comparación también puede usar el año anterior. El
candidato combina minutos previos/recientes y una tasa Gamma-Poisson con
peso parcial del año anterior. Se excluyen todo el día objetivo, otras
competiciones y temporadas más antiguas. Sin historial suficiente del año
anterior, abstiene; no resuelve rookies. No conoce rol, equipo, lesiones o
rival actuales y supone participación. `startup-scenario` muestra un
escenario de investigación para 2026-27, siempre `actionable=false`, sin
sustituir el modelo original ni habilitar Telegram.

En esta máquina el Python raíz previo no funciona; se creó un entorno
auxiliar `.local/harness-venv` para las verificaciones de fútbol y otro
`apps/nba/.venv` para NBA. No se reemplazó el entorno previo.

## Datos y cobertura

`capture` usa [llimllib/nba_data](https://github.com/llimllib/nba_data).
El número del archivo representa el año de finalización de temporada.
No equivale a cobertura completa: los archivos individuales antiguos
descargados contienen solo el último día de temporada y duplicados.
`coverage.json` informa el resultado comprobado, sin extrapolar el README.

`capture-pbp INVENTARIO --start 1996 --end 2025` usa el inventario público
de [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data) conservado en
`.local/source_inventory/shufinskiy__nba_data.json`. En este repositorio
el año representa el **inicio** de temporada. Selecciona una representación
PBP (v3 si existe) y tiros por temporada, regular y playoffs disponibles.
No mezcla feeds duplicados. Descarga blobs sin ejecutar código de terceros;
verifica tamaño, SHA1 de Git y SHA256. `audit-pbp MANIFEST` lee el CSV
esperado dentro del tar sin extraer rutas arbitrarias.

Los datos adicionales de [hoopR-data](https://github.com/sportsdataverse/hoopR-data)
conservan IDs **ESPN**, distintos de IDs NBA. `audit-hoopr MANIFEST`
documenta sus rangos y conteos; todavía no une identidades entre fuentes.
Descarga no implica permiso de redistribución comercial de todos los datos.
Ver inventario documentado en `docs/nba_fuentes_github.md`.

## Modelo de referencia y límites

`protocol.json` congela parámetros antes de evaluar. Historial de la misma
temporada regular, mínimo 10 apariciones anteriores; se excluye todo el día
objetivo. Minutos recientes encogidos hacia el historial de 20 apariciones;
tasa de rebotes Gamma-Poisson con exposición en minutos y distribución
mezclada sobre minutos históricos centrados. Se compara contra medias
móviles de 10 apariciones y Poisson. No usa los minutos reales del objetivo.

El replay evalúa **jugadores que participaron**; aún no resuelve quién
estaba disponible antes del partido. Los datos descargados hoy pueden
contener correcciones posteriores. Por ello este resultado no acredita
point-in-time prospectivo, calibración comercial ni ventaja ante las casas.
CRPS/NLL menores indican mejora contra la referencia, no una tasa de acierto
de apuestas. Intervalos centrales discretos pueden cubrir más del 80% nominal.
Los intervalos bootstrap agrupan por partido; no resuelven dependencia
temporal entre partidos, jugadores o temporadas.

`scenario --player-id ID --as-of YYYY-MM-DD --season 2025-26 --minutes 30
--line 7.5` calcula un escenario hipotético, siempre `actionable=false`.
No es un pick actual ni incorpora traspasos, disponibilidad o rival actuales.
Push se separa de over/under; void queda desconocido sin reglas del operador.

## Auditoría y siguientes puertas

El ledger SQLite **local de investigación** rechaza UPDATE/DELETE y encadena
hashes. Una cuenta con acceso al archivo puede alterar/eliminarlo; no hay
anclaje temporal externo. No sustituye Postgres/Redis ni recuperación de F1.
Protocolo y resultados se registran con hashes; puertas G0–G9 pendientes
de su evidencia/revisión completa. Los JSON de reportes son salidas derivadas
recalculables, vinculadas a entradas; las capturas raw conservan su primera
hora de recepción.

## Contexto y avisos de investigación (2026-10-05)

`current-context --roster-manifest MANIFEST_ESPN --probe-manifest MANIFEST_PUBLICO
--profile-manifest MANIFEST_FICHAS --dataset DATASET --as-of ISO_UTC
--output-dir CARPETA_NUEVA` une nombres exactos normalizados y fechas de
nacimiento. Comprueba el equipo actual contra NBA.com; conserva conflictos
y exige que todas las capturas existieran al decidir. La plantilla histórica
solo acredita identidad. En la captura revisada: 596/606 identidades, diez
sin resolver, 436 escenarios condicionales de arranque. Tener equipo conocido
no acredita disponibilidad, rol o minutos actuales.

`capture-context --date YYYY-MM-DD --reference-manifest MANIFEST_PUBLICO`
hace tres solicitudes públicas finitas: jugadores NBA, calendario ESPN y
lesiones ESPN. Hereda la referencia de identidad con hash y recepción original.
No reintenta denegaciones. Las designaciones ESPN no se convierten en estado
médico verificado sin publicación y partido comprobados. El informe oficial
2026–27 consultado devuelve 404; NBA.com/players sí respondió.

`calibration-diagnostics --dataset DATASET --predictions REPLAY_JSON
--output-dir CARPETA_NUEVA` comprueba verdad y reproducción del replay sellado,
registra protocolo/código antes de evaluar y calcula PIT aleatorizado,
fiabilidad en líneas fijas y cobertura frente a masa discreta esperada.
No ajusta parámetros ni promueve el modelo. `coherent_minutes` conserva 240
minutos reglamentarios solo en escenarios con elegibilidad explícita;
no adivina disponibilidad ni redistribuye automáticamente una lesión.

`audit-quotes INPUT_JSON --as-of ISO_UTC --output-dir CARPETA_NUEVA`
valida identidad de contrato, tiempos, cuotas bilaterales y reglas.
`price_contract` separa push/void y exige alcance de prórroga compatible para EV;
`revalidate_selection` rechaza una línea distinta o una cuota inferior al mínimo.
No hay fuente de props actual validada ni evidencia de CLV/ROI.

`telegram-test --as-of ISO_UTC` prepara una prueba local sin enviar. `--send`
solo admite el mensaje técnico explícito con configuración activa. La cola NBA
es independiente: sello antes de encolar, expiración con reloj real al enviar,
reclamación persistente, deduplicación y ninguna repetición tras timeout ambiguo.
La confirmación de Telegram no acredita recepción por cada suscriptor.

Decisión del usuario: reutilizar el **bot y chat de alertas de fútbol**.
El enlace explícito `.local/private/telegram_link.json` lee exclusivamente
`TG_BOT_TOKEN`/`TG_ALERT_CHAT` de la ruta autorizada o del entorno; no importa
el paquete de fútbol ni copia secretos. También acepta las variables NBA
privadas. No hay carga automática del `.env` global. En este host las credenciales
activas no están disponibles; no se envió ninguna notificación real.
Compartir bot también comparte sus límites: la coordinación entre emisores
para operación sostenida sigue pendiente. Los picks comerciales se rechazan.

Evidencia y pendientes detallados en `docs/nba_continuacion_20261005.md`.
Falta disponibilidad por partido, rol/minutos validados, contratos y precios
utilizables, confirmación prospectiva y almacenamiento/anclaje de producción.

## Fuentes adicionales auditadas (2026-10-05)

`capture-lineups` guarda una captura pública RotoWire con hash y recepción.
`audit-lineups MANIFEST --context-manifest MANIFEST_ESPN --as-of ISO_UTC
--output-dir CARPETA_NUEVA` distingue alineaciones previstas/confirmadas por
el proveedor, titulares y observaciones médicas. Conserva IDs `rotowire:`;
los cruces con eventos ESPN son candidatos sin validación de reloj/identidad.
La muestra aporta 50 titulares previstos, sin elegibilidad médica acreditada.

`capture-rotations --game-ids ID1 ID2` admite 1–20 IDs NBA por lote público
PBP Stats; detiene denegaciones, 429 y errores 5xx. `audit-rotations MANIFEST
--dataset DATASET --output-dir CARPETA_NUEVA` contrasta quintetos, tiempos,
prórrogas y marcadores con el dataset independiente aceptado. El piloto final
conserva 15 partidos y 745 registros de quintetos por cuarto; seis descargas
fallaron con 503. Son agregados, no secuencias de sustitución, y los rebotes
de equipo no se importan como rebotes individuales. No se reentrenó el modelo.

Los calendarios históricos revisados no tienen horas de inicio. Una muestra
PDF oficial adicional devolvió 403, distinta de la consulta 404 mencionada
arriba; no se recibió ningún PDF. Diez repos se fijaron por commit y se revisó
su código sin ejecutarlo. Detalles y evidencia en
`docs/nba_scrapers_avance_20261005.md`; todas las salidas siguen sin promoción.
# Recuperación gratuita de históricos

`python -m nba backfill-inventory RELEASE_MANIFEST --team-manifest TEAM_MANIFEST --base-report BASE_REPORT --output NUEVO_JSON` crea un censo reproducible de los partidos conocidos pendientes. No modifica datos aceptados ni corrige minutos inválidos. La auditoría del 2026-10-05 identifica 395 pendientes: 320 regulares, 71 de pretemporada, tres de playoffs y uno de play-in. Los calendarios anteriores de playoffs aún requieren cobertura propia.

`python -m nba capture-backfill --kind boxscore --game-ids 0022500003` captura hasta 20 partidos por lote. `--kind rotation` consulta GameRotation. Las respuestas y sus hashes permanecen en `NBA_DATA_DIR/raw/official_backfill`. Cualquier error detiene el lote; una ejecución idéntica reutiliza archivos verificados y no reintenta un lote detenido. La muestra real de ambos endpoints agotó el timeout; no se ha acreditado una recuperación de boxscores o stints nuevos.

`python -m nba capture-injury-reports --urls URL1 URL2` admite hasta diez URL canónicas oficiales por lote, sin claves. Conserva también las respuestas de error y se detiene ante un fallo. Tres PDF históricos del 2025-04-25 sí fueron recibidos y revisados visualmente.

El parser PDF es opcional y se ejecuta con el runtime PDF de escritorio, que dispone de `pdfplumber`; no se instala el proyecto `nbainjuries` ni Java. Con `apps/nba/src` en `PYTHONPATH`, ejecutar:

```text
python -m nba.injury_pdf MANIFEST --name ARCHIVO.pdf --output NUEVO_JSON
```

Usa la hora del encabezado, no el nombre del archivo, y convierte ET con `tzdata==2026.3`. Preserva `NOT YET SUBMITTED`, el contexto entre páginas y IDs desconocidos. El layout de siete columnas se valida como piloto; un layout diferente se rechaza. `select_report` exige recepción anterior al corte por defecto. `retrospective=True` permite una selección de investigación por hora declarada del documento, conservando que la recepción histórica original no está acreditada. No habilita señales médicas o comerciales.

Estas rutas no consumen The Odds API. Las reglas actuales de conciliación, el dataset aceptado y el modelo quedan intactos. Véase `docs/nba_recuperacion_piloto_20261005.md` para resultados, comandos y límites.

## Casas europeas seleccionadas (2026-10-08)

`src/nba/odds_sources.json` incluye las versiones solicitadas: 1xBet Europa
(`onexbet`), Betsson Europa (`betsson`), Codere Italia (`codere_it`) y Betano
Reino Unido (`betano_uk`). Europa es la región del proveedor; para 1xBet y
Betsson no acredita un país contractual. Ninguna selección acredita la versión
mexicana ni el contrato de una apuesta individual.

`python -m nba odds-source-plan` muestra la selección sin red ni credenciales.
Con `--event-id ID_THE_ODDS_API` genera las solicitudes por evento; `--sport
basketball_nba_preseason` distingue pretemporada. Usa el filtro explícito
`bookmakers=onexbet,betsson,codere_it,betano_uk`, sin ampliar a todas las casas
de Europa/Reino Unido. El JSON se incluye en la distribución del paquete.

El cliente `BoundedOddsCapture.request_selected` conecta esa selección a las
reservas y recibos existentes. Requiere un presupuesto explícito y la consulta
inicial de cuota de cuenta; no activa un recolector periódico. Descubrir
mercados actuales cuesta hasta un crédito; consultar los tres mercados de
equipos reserva tres por evento, o treinta para un corte histórico. Las
consultas de puntos/rebotes/asistencias son investigación de cobertura
desconocida: la documentación NBA anuncia props para regiones US/AU, no para
estas cuatro versiones. El catálogo reciente de mercados no contiene precios
ni constituye un inventario completo. No se han consultado nuevas cuotas al
incorporar esta selección; siguen pendientes la captura real, reglas
vinculadas a cada versión/mercado y disponibilidad final del jugador.

## Captura funcional de props individuales (2026-10-08)

La captura de datos está disponible mediante `capture-props`: usa diez casas
US/AU, selecciona hasta ocho eventos futuros y conserva PTS/REB/AST con línea,
precios Over/Under, recepción y reloj de mercado. `props_sources.json` mantiene
esta selección independiente de las cuatro versiones europeas.

```text
python -m nba capture-props --credit-cap 32 --max-events 8 --key-file .env --output-dir CARPETA_NUEVA
```

También acepta `NBA_ODDS_API_KEY`; no importa otras variables de `.env`.
Cada ejecución requiere carpeta nueva y presupuesto explícito, sin reintentos
ni captura periódica. El máximo por evento es cuatro créditos: descubrimiento
y tres mercados. `pairs.json`, `coverage.json`, `result.json` y `raw/manifest.json`
son las salidas reutilizables. Una respuesta vacía significa ausencia en ese
recibo, nunca cotización cero ni ausencia universal.

`--identity-file REFERENCIA_JSON` añade `pairs_identified.json`: exige nombre
completo normalizado único en evidencia oficial. Conserva cuándo se recibió
la identidad; una prueba posterior al precio no se retrofecha. Identidad y
pertenencia al roster no acreditan disponibilidad final.

RUN064 comprobó 36 pares reales (12 por mercado), de FanDuel, Fanatics y
Sportsbet, usando 17 créditos. El archivo histórico de 2617 pares se conserva
con sus límites de recepción original. `data_ready` acredita datos de precio
para investigación; `production_ready` y `actionable` siguen falsos hasta
completar contratos aplicables, disponibilidad y validación prospectiva.

## Seguimiento prospectivo en simulación (2026-10-08)

`paper-run` valida el histórico antes de gastar créditos, captura únicamente
partidos regulares y sella un registro nuevo en una sola operación. Requiere
presupuesto explícito, referencia de identidades oficiales, etiquetas de
minutos de partido completo y boxscores corregidos. Cada salida es nueva;
no sustituye predicciones anteriores ni inicia un servicio periódico.

```text
python -m nba paper-run --credit-cap 4 --max-events 1 --key-file .env --identity-file REFERENCIA_JSON --fullgame-labels ETIQUETAS_JSONL_GZ --boxes BOXSCORES_JSONL_GZ --output-dir CARPETA_NUEVA
```

`--injury-receipt RECIBO_JSON` añade el feed ESPN recibido: los nombres coincidentes
son candidatos sin cruce NBA verificado y bloquean entradas hipotéticas. No
figurar en el feed nunca significa estar disponible. `paper-register` permite
registrar un feed ya recibido con los mismos insumos; sus precios pueden estar
vencidos. La frescura se comprueba nuevamente al sellar, con límite de 60 segundos.

El protocolo incluido (`paper_protocol.json`) fija historia causal de veinte
apariciones positivas, mínimo diez, prior de la temporada anterior para el
inicio, prórroga incluida, distribución Gamma-Poisson y baseline Poisson.
Las tres estadísticas son experimentales; extender rebotes al inicio de otra
temporada y a puntos/asistencias no equivale a validar esos modelos. Todas
las predicciones son condicionadas a participación. Las entradas usan una
unidad y contrato hipotético DNP-void/prórroga/push, sin acreditar reglas de
una cuenta ni habilitar apuestas reales. Se guarda el baseline y la ausencia
de disponibilidad final; no hay ajuste numérico por lesiones.

Cuando termine el partido, la recepción y evaluación son explícitas:

```text
python -m nba paper-capture-result --nba-game-id ID_NBA --game-slug SLUG_OFICIAL_NBA --output-dir RECIBO_NUEVO
python -m nba paper-score --registration REGISTRO --event-id ID_ODDS_API --receipt RECIBO_NUEVO/receipt.json --output-dir EVALUACION_NUEVA
python -m nba paper-summary --evaluations EVALUACION_1 EVALUACION_2 --output-dir RESUMEN_NUEVO
```

Sin `--game-slug`, se consulta el CDN oficial; con él, la página NBA de boxscore
es una vía alternativa comprobada. El slug conserva el mismo ID NBA. HTTP
fallido queda como recibo y no constituye un resultado. La evaluación exige
finalización, ID NBA, equipos, hora exacta, jugador y registro anterior al
inicio; rechaza resultados incompletos o cambios de horario sin reconciliar.
El lector web verifica las sumas de jugadores contra equipos y conserva DNP
e inactivos explícitos. Un ausente del boxscore nunca se inventa como DNP.

Los archivos de registro y evaluación están sellados; el resumen rechaza
modificaciones y duplicados por evento/jugador/mercado. Distintas casas o
versiones del mismo pronóstico no aumentan el tamaño de muestra. CRPS, NLL,
MAE, cobertura y Brier son descriptivos; CLV e intervalos confirmatorios quedan
pendientes. F6/G6 y F7/G7 conservan sus requisitos de promoción. En RUN065 se
congeló `evaluation_cohort.json` antes de resultados: quince unidades únicas,
con seis versiones recientes sustituyendo referencias iniciales únicamente
para la evaluación futura; todos los archivos anteriores se conservan.

### Seguimiento acotado de una cohorte existente

`paper-followup-plan --cohort ARCHIVO --receipts RECIBOS --raw-folder BLOBS
--output-dir PLAN_NUEVO` sella el cruce exacto con las páginas NBA y las
ventanas previas, cierre y resultados. `paper-advance --plan PLAN --state
DIARIO --output-dir EJECUCION_NUEVA --key-file ARCHIVO_LOCAL` ejecuta sólo
tareas debidas. No cambia predicciones ni coloca apuestas. El diario vivo
conserva reclamaciones inmutables antes de cada consulta y debe quedar fuera
de evidencia cuyo hash sea fijo; las carpetas de ejecución son nuevas.

El cierre compara la misma casa, evento, jugador, mercado y línea, con fuente
y recepción frescas antes del inicio. Un precio ausente o distinto queda no
comparable. Las observaciones `Active` o una plantilla sin estado explícito
no se convierten en disponibilidad. El trabajador conserva fallos y ventanas
perdidas, obtiene un final oficial por partido, evita duplicados y produce
resumen de evaluación y cierre por separado. RUN066 programa este seguimiento
local para el 20–21 de octubre: requiere equipo encendido y Codex abierto.
El límite adicional de cierre es dos créditos; no añade copias periódicas.
Consulte `docs/nba_pendientes_resueltos_y_cierre_programado_20261008.md`.


RUN067 traslada la captura del piloto al VPS y retira el ejecutor local.
El comando paper-advance rechaza un diario con state.owner.json retirado.
La automatización de Codex observa únicamente los resultados del servidor;
la captura ya no requiere este equipo encendido. El límite de cierre total
permanece en dos créditos, con los mismos sellos y sin copias periódicas.
Detalles: docs/nba_seguimiento_vps_y_pendientes_por_alcance_20261008.md.

RUN068 activa las alertas operativas y la parada terminal del piloto desde el
propio VPS. El recolector actualizado conserva el diario original, distingue
fallos de fuentes necesarias de Caliente en cuarentena y desactiva nuevas
copias periódicas. Un reinicio conserva las reclamaciones de consultas y
mensajes. La confirmación científica y las cuentas comerciales mantienen sus
requisitos de evidencia; no hay apuestas reales habilitadas. Detalles:
docs/nba_activacion_y_alertas_vps_20261009.md.

RUN069 publica https://pronosticosdeportivos.pro/nba con los 15 pronósticos
registrados del piloto y sus resultados oficiales verificables cuando lleguen.
Filtros por jugador/equipo, mercado, partido y estado; cuotas históricas y
participación condicional explícitas. Servicio aislado en VPS, sin consultas
deportivas desde la web ni credenciales expuestas. La vista lee fuentes
originales para lectura y rechaza resultados que no coincidan con el cuerpo
oficial recibido. Detalles y límites de verificación visual móvil:
docs/nba_pagina_pronosticos_resultados_20261009.md.

RUN071 añade los nueve mercados estadísticos: ganador, puntos de equipo,
total del partido y puntos/rebotes/asistencias/triples/robos/tapones de
jugadores. La extensión de 42 pronósticos mantiene el piloto original de15.
`python -m nba.multimarket` permite recuperar, evaluar y registrar;
`nba.multimarket_dashboard` proyecta la extensión y sus resultados oficiales.
Cuotas fuera del modelo, calibración cronológica de candidato/referencia,
cobertura visible y recepción histórica desconocida explícita. Todo sigue
clasificado como investigación, sin promoción de puertas científicas.
Detalles y resultados: docs/nba_nueve_mercados_estadistica_20261009.md.
