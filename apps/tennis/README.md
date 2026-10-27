> Estado consolidado al 18-oct-2026: [cierre integral y límites actuales](CIERRE_INTEGRAL_20261018.md). Revisión completa de las 73 entradas pendientes; 72 referencias acreditadas y una ambigüedad de campus conservada. Los apartados históricos siguientes documentan versiones anteriores.

# Motor local de tenis

Primera implementación de investigación: captura completa, normalización, habilidades de saque/resto regularizadas y puntuación probabilística para varios mercados. No conecta con publicación, apuestas, producción de fútbol o NBA.

La formulación del candidato está en `MATEMATICAS.md` y los resultados realmente medidos en `RESULTADOS.md`.

## Ejecución

Python 3.12 con las dependencias de `requirements.txt`. Desde la raíz de este checkout, en PowerShell:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'apps\tennis')
$dataRoot = 'C:\Users\huye\Documents\apuesta proyec\data\tennis\full_20261016'
python -m tennis_engine download --root $dataRoot --source all
python -m tennis_engine normalize --root $dataRoot --as-of 2026-10-16
python -m tennis_engine evaluate --root $dataRoot --output "$dataRoot\experiments\ATP_2026" --circuit ATP --test-year 2026
python -m tennis_engine evaluate-markets --root $dataRoot --output "$dataRoot\experiments\ATP_2026"
python -m tennis_engine train --root $dataRoot --output "$dataRoot\models\ATP_current" --circuit ATP --cutoff 2026-10-16
python -m tennis_engine predict --model "$dataRoot\models\ATP_current" --player-a 'Jannik Sinner' --player-b 'Carlos Alcaraz' --surface Hard --output "$dataRoot\example_forecast.json"
python -m tennis_engine.manage seed-identities --root $dataRoot --db "$dataRoot\operations\identities.sqlite"
python -m tennis_engine.manage pool --root $dataRoot --output "$dataRoot\improvements\ATP_pool" --circuit ATP
python -m tennis_engine.manage walk-forward --root $dataRoot --output "$dataRoot\improvements\ATP_monthly" --circuit ATP --start 2026-07 --end 2026-09 --pool "$dataRoot\improvements\ATP_pool\pool.json"
python -m tennis_engine.manage shadow --data-root $dataRoot --models-root "$dataRoot\models" --pools-root 'C:\Users\huye\Documents\apuesta proyec\data\tennis\improvements_20261016' --operations-root 'C:\Users\huye\Documents\apuesta proyec\data\tennis\operations_20261016' --identity-db 'C:\Users\huye\Documents\apuesta proyec\data\tennis\operations_20261016\identities.sqlite' --tournament-config apps\tennis\config\tournaments.json --fixture-file apps\tennis\config\fixtures_20261017.json --credit-cap 0 --account-reserve 6200
python -m pytest apps/tennis/tests -q
```

Los mismos comandos aceptan WTA. El ejemplo de jugadores es una consulta hipotética: no afirma que haya un partido programado. El número de muestras de integración se controla con `--samples` (24 por defecto). Para un Grand Slam actual hay que especificar el formato correcto y `--deciding-tiebreak 10`; no se infiere de los nombres.

Los comandos operativos viven en `tennis_engine.manage`. `discover` consulta el catálogo y los eventos sin costo, y solo descarga mercados cuando se fija un límite de créditos y se conserva una reserva de la cuenta compartida. La clave se recibe por variable de entorno y nunca se escribe en recibos. Cada respuesta original queda sellada con hora UTC y SHA-256.

Auditoría completa de alcance y correcciones: `AUDITORIA_20261017.md`. La captura local con hash detecta alteraciones respecto del recibo conservado; no constituye un servicio externo de timestamp ni almacenamiento WORM. La versión de investigación aún tiene pendientes antes de producción.

`shadow` actualiza el calendario por endpoints gratuitos, resuelve identidades, congela la predicción y registra objetivos T−120/T−15 en un archivo nuevo con hash. Por defecto no consulta cuotas. `--capture-odds` solo puede gastar dentro de una ventana de ±7 minutos cuando existe una constancia oficial de estado con menos de 15 minutos, participantes exactos y hora reconciliada. Aun así, la salida queda `executable: false`: este comando no publica ni apuesta. El límite mensual local incluye capturas anteriores del mismo directorio; `--account-reserve` protege el saldo compartido conocido.

Desde la auditoría v2, la constancia de estado requiere también `sport_key`, `participants` (nombres exactos del proveedor), `provider_commence_time`, `source_path` y `source_sha256`. El archivo de fuente debe existir y coincidir con el hash. Solo se admiten hosts oficiales ATP/WTA/ITF en este perfil; otros torneos o proveedores necesitan un adaptador explícito. El texto de las constancias iniciales de `config/fixtures_20261017.json` es histórico y no cumple la evidencia nueva. No se debe cambiar su hora para simular una observación reciente.

Las predicciones se guardan antes de consultar precios. La comprobación de antigüedad usa la hora posterior a la recepción. Un cambio de participantes u hora obliga a reconciliar de nuevo. El registro SQLite impide duplicar una ventana del mismo evento y mantiene la reserva ante fallos; una revisión explícita es necesaria antes de reintentar una ventana reclamada. Los totales de créditos reservados y cobros confirmados se informan por separado. Otros consumidores de la cuenta pueden gastar simultáneamente; la reserva local no coordina esos consumidores.

`markets.compare_offered` conecta `h2h`, `h2h_s1`, `h2h_s2`, `spreads`, `alternate_spreads`, `totals` y `alternate_totals`. Ganador utiliza el híbrido y los derivados utilizan Markov MAP sin calibración propia. Las probabilidades de devolución se conservan y el margen se retira solo de parejas complementarias de la misma línea. `conditional_expected_return` está condicionado a partido completo y no incorpora retiros. Las ofertas lay, líneas no soportadas y mercados sin mapeo quedan pendientes. Las cuotas vencidas nunca se etiquetan como mejor precio fresco.

Auditoría local sin llamadas API:

```powershell
python -m tennis_engine.manage audit --root $dataRoot --operations-root 'C:\Users\huye\Documents\apuesta proyec\data\tennis\operations_20261016' --output 'C:\Users\huye\Documents\apuesta proyec\data\tennis\audit_nueva_version'
python -m tennis_engine normalize --root $dataRoot --as-of 2026-10-16 --output-root 'C:\Users\huye\Documents\apuesta proyec\data\tennis\canonical_nueva_version'
```

Los directorios de auditoría y modelos deben ser nuevos. La nueva normalización conserva contexto y trazabilidad por archivo/fila/recepción; un duplicado combinado toma la recepción más tardía. Una versión distinta de los datos requiere modelos nuevos, sin cambiar los recibos originales del candidato ya evaluado.

## Datos y trazabilidad

`download` consulta el catálogo TML y todos sus archivos CSV. MCP se fija al commit `1813a1309b7ed7ebf1c7e884b32bf675d00e4edf`. Concurrencia máxima cuatro, reintentos acotados, originales y recibos con hash/recepción real. `--seed-mcp` permite reutilizar originales locales de ese commit tras verificar su blob Git. La ejecución devuelve error si quedó una descarga fallida. Un directorio de snapshot existente se reutiliza; usar otro directorio para capturar una versión nueva.

TML se clasifica por circuito y grupo. Los originales no clasificados se conservan como archivo; no se fuerzan a un circuito. Se generan partidos canónicos, cobertura por año/circuito y cuarentena. Se resuelven copias compatibles y se apartan conflictos. Se guardan retiros y formatos no convencionales en el archivo canónico, pero la primera versión del modelo utiliza solo partidos terminados de formato convencional con conteos válidos.

Los IDs ATP y WTA tienen espacios separados. El registro de identidades guarda alias por proveedor, circuito, evidencia, revisor y fecha. La similitud de nombres solo ordena candidatos: nunca asigna automáticamente un jugador. `tourney_date` puede representar la semana del torneo. Por eso no se inventa una hora, y las pruebas aplican 35 días de separación entre la última semana que puede entrar al entrenamiento y el origen del pronóstico.

La descarga incluye MCP para investigación. Su licencia CC BY-NC-SA no acredita permiso para usarlo en un servicio comercial. Los ajustes del modelo de esta implementación utilizan exclusivamente TML, cuya página declara MIT. Los originales descargados hoy no prueban recepción ni publicación en años anteriores.

## Modelo y límites

El modelo de puntos es binomial, con enlace logit, habilidad de saque/resto por jugador y ajustes por superficie. Los efectos tienen priors gaussianos; las celdas de jugador/superficie con poca muestra reciben la población y una incertidumbre de prior al predecir. La verosimilitud se pondera por antigüedad (semivida 365 días). Se calcula MAP con optimización dispersa y precisión de Laplace; la predicción conjunta de los dos parámetros propaga covarianza mediante muestras antitéticas.

Esta es una primera aproximación bayesiana regularizada. La ponderación temporal es una verosimilitud de potencia, no un filtro dinámico de estado latente. Faltan hipótesis experimentales de fatiga, clima, viajes, lesiones y presión. No se incorporan por nombre sin datos ni pruebas.

El motor de puntuación integra primer sacador desconocido y mantiene continuidad del saque entre sets. Resuelve deuce y tie-break sin truncar sus colas. Admite mejor de 3/5, ventaja/no-ad y desempate final a 7/10 en 6-6. No admite sets de ventaja sin desempate, super-tie-break sustitutivo ni sets cortos. La liquidación separada conserva retiros y aplica únicamente perfiles con fuente y vigencia verificadas; hoy cubre Pinnacle para ganador, primer set, totales y hándicaps. Las reglas desconocidas quedan pendientes y bloquean el ROI completo. Las líneas admitidas son enteras y medias; las de cuarto se rechazan.

Produce ganador, primer set, marcador en sets, total de sets, tie-break, hándicap de juegos/sets y totales de juegos. Las probabilidades de estos mercados se derivan de una misma distribución conjunta. Las cuotas justas incluyen la posibilidad de devolución cuando la línea es entera. Sin cuota ofrecida no se muestra valor esperado de una apuesta real.

## Evaluación

`evaluate` ajusta el modelo antes del año elegido, con embargo de 35 días, y lo mantiene congelado durante el año reservado. Compara MAP→Markov con Elo probabilístico y una mezcla de Elo general/superficie igualmente congelados. Dentro de la historia Elo, un periodo se actualiza en bloque para no inventar un orden de partidos.

Se guardan predicciones, log-loss, Brier, acierto e intervalo de diferencia de pérdidas por bloques de periodo. El acierto no selecciona el modelo; no se tunean parámetros en el periodo de prueba. La evaluación inicial usa probabilidades MAP sin integrar la posterior; `predict` sí integra la incertidumbre aproximada. Son variantes declaradas, no métricas intercambiables.

La prueba anual mide un origen de pronóstico fijo y no representa un servicio diario reentrenado. No hay cotizaciones, comisiones ni ejecución real: no se calcula ROI o CLV. La ausencia de recepción histórica acreditada impide presentar el resultado como backtest operativo point-in-time.

`evaluate-markets` utiliza el modelo y la presentación de jugadores ya guardados en una evaluación anual. Comprueba cuatro mercados fijos (22,5 juegos, hándicap A −3,5, tie-break y primer set) frente a frecuencias de entrenamiento por superficie/formato. Las líneas son consultas ilustrativas; no se seleccionan a partir del test ni se confunden esas referencias con cuotas de casas.

La primera ejecución real de 2025/2026 no superó la referencia Elo en log-loss de ganador. Los resultados completos, la cobertura y los próximos límites están en `RESULTADOS.md`. No hay candidato aprobado para publicar picks.

La segunda fase aprende una combinación simétrica entre Markov y Elo usando únicamente predicciones de 2025. No añade una bonificación arbitraria a `p` o `q`; combina probabilidades de ganador en escala logit. Su revisión de 2026 y el walk-forward julio–septiembre son exploratorios porque 2026 ya fue observado. Este híbrido aplica solo a ganador del partido; los demás mercados siguen usando el modelo conjunto original.

## Ampliación ejecutada y cuenta de pago

El titular confirmó plan **de pago** y autorizó **2.000 créditos mensuales** para tenis. La política está en `config/operations.json`; la reserva compartida es 6.000 y se comprueba con saldo reciente. `--policy` carga estos límites; un límite explícito en la línea de ejecución tiene prioridad. La primera muestra histórica ATP/WTA costó 60 créditos y obtuvo cinco eventos con 26 cotizaciones. El informe completo está en `AMPLIACION_20261017.md`.

`--refresh-official` descarga/archiva los órdenes de juego revisados de las finales Shanghai y Wuhan del 18-oct-2026. Verifica los nombres completos, rivalidad, fecha y única hora «no antes de». Después de esa hora requiere estado en vivo; otros torneos o diseños se rechazan. Se añadió `pypdf` a las dependencias. Una URL no configura por sí sola un adaptador para todo el circuito.

`--calibration-root` añade calibradores experimentales por contrato desde `ATP_calibration_v2/calibrators.json` y WTA equivalente antes de guardar el pronóstico. Solo se aplican a 22,5 juegos, hándicap ±3,5 y primer set con simetría; el segundo set y otras líneas conservan probabilidades sin recalibrar. El overlay de campos `experimental_calibrated_*` no es una distribución conjunta calibrada ni una aprobación para apostar. El candidato dinámico nuevo se ejecutó y no superó al híbrido anterior, por lo que no sustituye al candidato conservado.

Ejemplos (definir rutas de datos existentes; desde este checkout):

```powershell
$dataRoot = 'C:\Users\huye\Documents\apuesta proyec\data\tennis\full_20261016'
$ops = 'C:\Users\huye\Documents\apuesta proyec\data\tennis\operations_20261016'
$extension = 'C:\Users\huye\Documents\apuesta proyec\data\tennis\extension_20261017'
$improvements = 'C:\Users\huye\Documents\apuesta proyec\data\tennis\improvements_20261016'
python -m tennis_engine.manage shadow --data-root $dataRoot --models-root "$dataRoot\models" --pools-root $improvements --operations-root $ops --identity-db "$ops\identities.sqlite" --tournament-config apps\tennis\config\tournaments.json --policy apps\tennis\config\operations.json --calibration-root $extension --refresh-official
python -m tennis_engine.manage historical --root $ops --policy apps\tennis\config\operations.json --sport tennis_atp_shanghai_masters --date 2026-10-16T10:00:00Z --bookmakers pinnacle --markets h2h,spreads,totals
python -m tennis_engine.manage evaluate-prospective --operations-root $ops --results "$extension\future_results.json" --output "$extension\prospective_report.json" --protocol "$extension\future_protocol.json"
```

El primer comando usa solo calendario gratuito. Añadir `--capture-odds` habilita gasto exclusivamente dentro de las ventanas verificadas. El segundo comando gasta hasta 30 créditos y no debe repetirse como ejemplo gratuito. `historical` conserva el timestamp del proveedor, pero no presume que sea un cierre.

Para reproducir experimentos usar directorios nuevos:

```powershell
python -m tennis_engine.manage dynamic-experiment --canonical-root 'C:\Users\huye\Documents\apuesta proyec\data\tennis\audit_20261017_v1\canonical_v2' --baseline-root $dataRoot --output "$extension\ATP_dynamic_nueva_version" --circuit ATP
python -m tennis_engine.manage calibrate-derivatives --root $dataRoot --output "$extension\ATP_calibration_nueva_version" --circuit ATP
```

`context` acepta observaciones históricas con inicio/final real, recibo y hash; calcula carga y desplazamiento con cobertura explícita. `freeze-protocol` permite declarar otro periodo realmente futuro con hashes de los artefactos y rechaza sobrescribir un protocolo existente. Los resultados deportivos nuevos requieren revisión independiente, timestamps y original con hash. Una lista de resultados vacía produce métricas no disponibles, nunca cero pérdida.

## Pendientes para operación

- Fuente de estado programado/iniciado con recibo temporal; `commence_time` no se trata como cierre real.
- Ejecutar las capturas prospectivas previstas. El plan y los bloqueos ya existen; falta una fuente oficial fresca que reconcilie cada hora. La selección de casas es dinámica por cobertura y compara precios únicamente para evento, mercado, selección y línea idénticos.
- Prueba futura sellada: 2026 queda como desarrollo exploratorio y no vuelve a presentarse como test final.
- Perfiles de liquidación para cada casa y jurisdicción que se vaya a usar, además de Pinnacle.

Las pruebas cubren conservación de probabilidad, simetría, simulación independiente punto a punto, devoluciones, formatos, conflictos de datos, separación temporal y recuperación binomial con incertidumbre.

## Evaluador comun y carga observable
Ver CARGA_FASE1_20261017.md. BenchmarkEvaluator puntua la interseccion comun; RecentLoadExtractor conserva incertidumbre/recepcion temporal; ModelRunner conecta el hibrido y un ajuste ridge real cuando exista muestra anterior valida. scripts/phase1_load.py reproduce el ensayo archivado con --data-root, --probe-root y --output (directorio nuevo). No activar viajes/clima ni interpretar una abstencion como una probabilidad base duplicada.

## Captura de estados y Weighted Elo
Ver ESTADOS_WELO_20261017.md. scripts/capture_states.py hace un ciclo acotado ATP/WTA con recibos y tope local; no activa programador. scripts/compare_welo.py evalua la adaptacion por bloques contra controles en muestra comun. WeightedEloModel.load_frozen exige SHA-256 y se conecta a ModelRunner mediante lambda case: model.predict(case.player_a,case.player_b). Esta variante no mejora al hibrido actual en la comparacion2026 y no se promueve.

## Sedes verificadas por edicion
Ver SEDES_20261017.md. VenueRegistry conserva fuentes, versiones y enlaces exactos con vigencia local. scripts/build_venues.py reproduce el registro/calendario desde fuentes archivadas, sin red y con --root, --probe-root y --report nuevo. enrich_calendar exige input_timezone=UTC y source_received_at anterior a decision. No deducir techo real, altitud o itinerarios de una sede publicada.

### Sedes pendientes y temporadas: cierre de la muestra (18-oct-2026)
Ver `SEDES_TEMPORADAS_20261018.md`. `scripts/build_venues_complete.py` reproduce sin red el calendario revisado; `FixtureReviews` conserva el original y aplica correcciones por evento con disponibilidad previa. Muestra228/228 con sede principal,48temporadas corregidas,126pruebas aprobadas. La cobertura de coordenadas/elevacion sigue102/228: identidad de sede no equivale a pista ni punto geografico acreditado.

## Reconstruccion retrospectiva 2024/2025
Ver DATASET_HISTORICO_20261018.md. HistoricalDataset prepara distancia geodesica, delta de elevacion y diferencia UTC entre ediciones observadas con evidencia historica; fuentes recibidas hoy, sin validacion asof ficticia. scripts/prepare_historical_dataset.py requiere --registry, --canonical, --raw-root y --output; no consulta servicios.187ediciones enlazadas,2982partidos espacialmente aptos de11240;2025exploratorio, descanso desacoplado, cobertura pendiente documentada. No se han calculado metricas ni ajustado modelos con este conjunto.

Ampliacion de cobertura historica: [COBERTURA_HISTORICA_20261018.md](COBERTURA_HISTORICA_20261018.md). 52 ediciones, 17 recintos originales y 233 bloques por equipos revisados; 5798 partidos aptos. Las coordenadas adicionales pendientes se reportan por separado.

Comparacion retrospectiva ejecutada: [RESULTADOS_ESPACIALES_HISTORICOS_20261018.md](RESULTADOS_ESPACIALES_HISTORICOS_20261018.md). 2833 partidos comunes de2025; mejora minúscula con intervalo que incluye cero. Correccion espacial experimental, sin activacion.

Carga observable por rondas: [CARGA_RONDAS_RESULTADOS_20261018.md](CARGA_RONDAS_RESULTADOS_20261018.md). Experimento con1957partidos comunes, intervalo de mejora incluye cero.194pruebas aprobadas; correccion experimental sin activar; ventanas diarias siguen pendientes de limites temporales.

Cinco sedes prioritarias: [CINCO_SEDES_VERIFICADAS_20261018.md](CINCO_SEDES_VERIFICADAS_20261018.md).264destinos recuperados,6244partidos aptos; Yucatán es referencia amplia de complejo. Modelos y conjuntos anteriores conservados.


## Cierre integral de geografía y auditoría del motor

Versión de datos: data/tennis/historical_geography_complete_20261018 en el workspace principal. 239/240 entradas georreferenciadas, 11.237/11.240 destinos y 6.568 casos aptos. Evaluación fija con 3.353 casos2024 y 3.215casos2025 exploratorios; sin mejora acreditada ni activación. Scripts de revisión y auditoría entregados. audit_complete_geography.py --verify-existing y audit_engine_completion.py --policy <config/operations.json absoluto> --verify-existing verifican los artefactos desde el workspace de datos sin sobrescribirlos. Los gráficos opcionales usan Matplotlib en un entorno de visualización separado. 194 pruebas específicas y 1.315 generales aprobadas; 95 omitidas, dos avisos, Docker ausente.

## Preparación operativa y evaluación financiera (18-oct-2026)

225 pruebas específicas. Captura meteorológica con archivo original y evaluación financiera prospectiva de selecciones simuladas. Estado: evidencia financiera insuficiente; no coloca apuestas ni acredita rentabilidad. Ver [PREPARACION_APUESTAS_20261018.md](PREPARACION_APUESTAS_20261018.md). El protocolo original y los 12 artefactos de modelo permanecen intactos.

## Auditoría y pronósticos contrastados (19-oct-2026 UTC)

Ocho pronósticos ATP de investigación sellados; 246 pruebas. Cuatro programas oficiales y calendario API-Tennis actualizados. 50 nombres WTA y uno ATP tienen varios IDs: exclusión estricta, sin fusiones automáticas. No hay rentabilidad acreditada ni apuestas activadas. Ver [AUDITORIA_PRONOSTICOS_20261019.md](AUDITORIA_PRONOSTICOS_20261019.md).

## Mercados integrados v2 (19-oct-2026)

Diez familias matemáticas y trece claves de The Odds API;294 pruebas. Pruebas con12.052 observaciones de56 casas;500 créditos por cada clave suministrada, más6 de la prueba inicial. La segunda clave coincide con la principal; gasto reconciliado en su registro central. No todas las claves se observaron en cuotas reales; no hay validación financiera ni apuestas activadas. Ver [MERCADOS_INTEGRADOS_20261019.md](MERCADOS_INTEGRADOS_20261019.md).

Auditoría financiera independiente: ver ACREDITACION_FINANCIERA_20261019.md y módulo tennis_finance_v2.312 pruebas; protocolo y modelos originales conservados. Sello RFC3161 de DigiCert acreditado19-oct-2026 antes del estudio. Cero órdenes financieras prospectivas/ROI desconocido: no aprobado para apostar dinero real.

Calidad predictiva sin cuotas: CALIDAD_PREDICTIVA_20261019.md y tennis_quality_v3. Seis modelos, muestra común, bandas/cobertura e incertidumbre;332pruebas. Protocolo futuro separado y versiones anteriores conservadas. No superioridad ni certeza individual acreditadas. Entrega de datos vigente predictive_quality_v3_20261019_v3.

Continuidad autónoma: CONTINUIDAD_AUTONOMA_20261019.md y tennis_continuous_v1. Seguimiento cada2h en el chat; captura acotada cada4h, máximo12consultasAPI-Tennis/díaUTC.18pronósticos prospectivos registrados, cero resultados confirmatorios;342pruebas. Equipo/aplicación deben estar disponibles. Sin gasto de cuotas ni apuestas.

Validación prospectiva de diez mercados: ver VALIDACION_TODOS_MERCADOS_20261019.md y módulo tennis_allmarkets_v1. Primera emisión18partidos/990tareasrelacionadas,110grupos,0resultados; candidato Markov coherente separado de calidad_v3/financiero. Ninguna acreditación anticipada.

Incorporación automática de resultados: tennis_evidence_v1, guía RESULTADOS_Y_EVIDENCIA_20261019.md. Reconciliación de IDs, fuentes, marcadores/tiebreaks y tiempos físicos, con ambos evaluadores congelados. Histórico separado2788partidosterminados/39grupos/diezfamilias. El registro futuro espera sus resultados; no se fabrican datos ni rentabilidad.

## Motor vigente (v7, 19-oct-2026)

Punto de entrada único: `python -m tennis_motor`. Configuración en `config/motor.json`.

```powershell
python -m tennis_motor forecast --circuit ATP --player-a 'Stefanos Tsitsipas' --player-b 'Aleksandar Kovacevic' --surface Hard --date 2026-10-20
python -m tennis_motor seal --protocol RUTA_PROTOCOLO --parents-root RUTA_PADRES --predictions-root RUTA_PRONOSTICOS --output RUTA_INFORME
python -m tennis_motor evaluate --protocol RUTA_PROTOCOLO --predictions-root RUTA_PRONOSTICOS --results RUTA_RESULTADOS --output RUTA_INFORME
```

Cadena: datos canónicos con puente de identidades v3 (`tennis_identity_v2` alias de una semana + `tennis_identity_v3` fecha de nacimiento) → modelo saque/resto MAP (`tennis_engine.model`) → Markov con sobredispersión por partido (`tennis_core_v4`) → objetivo de ganador apilado: mezcla Markov, Elo dinámico ordenado por ronda (`tennis_dynamic_v2`), ranking, puntos, edad, inactividad, carga 14 días y experiencia (`tennis_core_v5.features`, `tennis_core_v7`) → centro re-resuelto para que los diez mercados salgan de una sola distribución conjunta.

Evaluación 2026 (exploratoria, año ya inspeccionado): log-loss ATP 0,5956 / acierto 67,6 %; WTA 0,5946 / 67,9 %. Elo de superficie: 0,6285 / 64,2 % y 0,6221 / 64,8 %.

Los paquetes `tennis_quality_v3`, `tennis_allmarkets_v1`, `tennis_markets_v2`, `tennis_finance_v2`, `tennis_continuous_v1`, `tennis_evidence_v1`, `tennis_core_v4`-`v6` y `tennis_dynamic_v1` quedan como evidencia congelada de estudios anteriores (sus protocolos verifican hashes de código): no se editan ni se usan para pronósticos nuevos. `tennis_continuous_v1` sigue siendo el capturador de calendarios oficiales que produce los registros padre.

### Con cuotas previas (opcional)

`python -m tennis_motor forecast ... --odds-a 1.40 --odds-b 3.00` usa la cuota sin margen como probabilidad de ganador y recentra la mezcla Markov para que todos los mercados sean coherentes con ella. En 2026 el mercado sin margen supera al apilador v7 (ATP 68,5 % frente a 67,1 % de acierto; WTA 69,5 % frente a 68,0 %) y v7 no aporta encima. Validación con cuotas de [tennis-data.co.uk](http://tennis-data.co.uk) descargadas a mano por el titular para un estudio privado sin lucro; no se redistribuyen.

### Cuotas previas en vivo (v8)

**Desde el 24-oct-2026 la fuente es PropLine** (decisión del titular del 23-oct: proveedor fijo de cuotas, una captura horaria compartida por todos los motores). Con `odds_provider: propline` y `propline_root` en la configuración del motor, `tennis_motor forecast` lee con `tennis_odds_propline_v1` la observación más reciente del archivo común recibida antes del pronóstico (como mucho un ciclo, 65 min) y solo si cotiza esa pareja exacta: h2h del partido completo, línea principal, sin cuotas en juego, suspendidas, DFS ni de bolsas; si la pareja aparece dos veces en la misma observación, no hay mercado. El motor no hace peticiones de cuotas y The Odds API no es respaldo: sin cotización en el archivo se usa el apilador v7 (`source: v7_stack`). Cada sellado guarda `live.provider`, recepción, hash y petición del archivo.

Hasta el 24-oct: `python -m tennis_odds_live_v1 --root data/tennis/live_odds_v1` toma una foto h2h (región `eu`) por torneo activo y media jornada UTC; tope 400 créditos/mes y reserva para el consumo de fútbol de la misma cuenta. En producción lo ejecuta el cron del VPS (ver «Ejecución en el VPS»); la antigua tarea de Windows «QuantFut tenis cuotas h2h» quedó desactivada a las 05:00 y 17:00. `tennis_motor forecast` usa la última foto previa si existe (`source: live_snapshot`); el estudio vigente es `core_v8_prospective_20261019`.

### Entrada automática de partidos

`python -m tennis_intake_v1 --root data/tennis/intake_v1 --credential-file .env.api-tennis.local [--no-capture]` pide el calendario a API-Tennis (2 consultas, máximo 4 al día; con `--no-capture` solo usa el calendario archivado). Resuelve el torneo por nombre y por la **edición celebrada en la misma época del año** (±30 días: un mismo nombre puede ser un ATP 250 de arcilla en mayo y un Challenger bajo techo en octubre) y después a los jugadores con identidad estricta (apellido + inicial; una inicial escrita en largo, «Xin. Wang», separa nombres; dos homónimos se separan por el nivel del torneo, gira o Challenger). Desde el 26-oct sella cada partido **una sola vez entre 2,5 h y 10 min antes** de su hora del proveedor, con la foto horaria más reciente de PropLine; si esa hora no trae precio del partido y aún queda otra pasada antes del inicio, espera a la siguiente. Cada sellado guarda en `market_board` **todas las líneas que ofrecen las casas** para ese partido (ganador, ganador de cada set, total y hándicap de juegos del partido y de cada set, total y hándicap de sets, tie-break y, desde el 27-oct, juegos ganados por cada jugador: `player_games_won`, contrato `player_games` en `tennis_player_games_v1`, fuera de los paquetes que hashea el protocolo multi-mercado congelado), cada una con el precio sin margen (media de casas que cotizan los dos lados de la misma línea) y la probabilidad del motor en esa misma línea. `evaluation_latest.json` añade `offered_markets`: por familia, modelo frente a precio al sellar y frente al cierre de PropLine en las mismas líneas, y `stack_on_market_rows`: el apilador v7 en los partidos donde manda el precio. Los nombres de PropLine se emparejan exactos o con el mismo nombre y apellido cuando un lado solo añade nombres intermedios («Leylah Annie Fernandez»), nunca por parecido. Aces, dobles faltas y puntos de quiebre no los modela el motor y quedan fuera. Las horas del proveedor son estimaciones: no son horas físicas verificadas.

### Actualización semanal de datos

`python -m tennis_refresh_v1 plan|run --weekly-root data/tennis/weekly --config apps/tennis/config/motor.json`. `plan` solo consulta el catálogo de TennisMyLife; `run` descarga únicamente los archivos cuyo tamaño o fecha cambiaron (los demás se enlazan desde la instantánea anterior tras verificar su SHA-256), normaliza, aplica los puentes de identidad v2/v3 y, si pasan los chequeos (no se pierden filas, las fechas avanzan, ambos circuitos), cambia `canonical` en `config/motor.json` guardando el anterior en `canonical_history`. La tarea de Windows «QuantFut tenis datos semanales» lo ejecuta los lunes a las 04:00. Los estudios sellados no cambian: cada protocolo fija su propia base.

### Reentrenamiento semanal y validación punto a punto

Desde el 20-oct la actualización semanal también reentrena el modelo de saque/resto (ATP y WTA, unos 20 s) con la base nueva y lo promueve en `config/motor.json` (`models_root`) solo si ambos ajustes convergen. Con la base corregida el modelo ya reconoce a jugadoras que antes quedaban fuera por alias (Rybakina, Eala). `tennis_motor` no rechaza partidos con alguna celda de saque sin entrenar: usa el valor de población, como en los datos con los que se ajustó el apilador.

Match Charting Project (Jeff Sackmann, CC BY-NC-SA; 9.400 partidos, 1,4 millones de puntos): la variación del saque entre partidos es de unas 0,23 unidades logit por servidor (≈0,16 en la semidiferencia, coherente con el sigma 0,2 ajustado); dentro del partido no hay variación extra entre sets ni efecto racha punto a punto. Presión: +1,3 pp ganando el punto al saque en break point y −2 pp en tie-break; su efecto en el hold (≈0,4 pp) y en el tie-break (≈0,1 pp) es despreciable, así que no se modifica el Markov.

### Ejecución en el VPS

El motor corre en el VPS en una imagen propia (`apps/tennis/Dockerfile`, `python:3.12-slim`), aislada de los servicios de fútbol. Datos en `~/quantfut-tenis/data` (montado en `/data`), claves en `~/quantfut-tenis/secrets` (solo lectura) y la imagen activa en `~/quantfut-tenis/IMAGE`. El archivo de PropLine (volumen `quantfut_artifacts`, subcarpeta `propline_shared`) se monta de solo lectura en `/propline`; la imagen lleva `propline_shared.py` de `src/qf/ingest/` copiado al contexto de construcción. El cron del usuario `qf` llama a `scripts/vps_run.sh hourly` en el minuto 25 de cada hora (el calendario de API-Tennis solo en las pasadas de las 00 y 12 UTC, decididas con `date -u`, así que el cambio de horario de Berlín no las mueve) y a `scripts/vps_run.sh weekly` (lunes 10:00 UTC). Ver `DEPLOYS.md`.
