# Tenis: extracción completa y primera versión del motor

Fecha: 16 de octubre de 2026. Estado: **implementado y ejecutado localmente para investigación; candidato sin aprobar para publicar picks**.

## Entregables

- Código independiente en `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis/`.
- Datos y resultados en `C:/Users/huye/Documents/apuesta proyec/data/tennis/full_20261016/`.
- Comandos reproducibles, dependencias, límites y pruebas en el README del módulo.
- Modelos ATP y WTA, recibos de entrenamiento, evaluaciones de 2025 y 2026 y dos consultas hipotéticas de varios mercados.

## Extracción y consolidación

| Resultado | Cantidad |
|---|---:|
| Archivos del catálogo TennisMyLife | 171 |
| Archivos de datos/documentación MCP de la versión fija | 43 |
| Descargas correctas / previstas | 214 / 214 |
| Fallos de descarga | 0 |
| Tamaño total de originales | 593.347.344 bytes |
| Partidos canónicos TML | 492.251 |
| Con formato y conteos de saque aptos para este candidato | 249.938 |

Se comprobó nuevamente el SHA-256 de los 214 originales; todos coinciden con su recibo y con el tamaño del catálogo. Los archivos MCP se contrastaron con los blobs Git de la versión `1813a1309b7ed7ebf1c7e884b32bf675d00e4edf`.

La tabla canónica contiene 394.592 partidos masculinos (202.951 aptos) y 97.659 femeninos (46.987 aptos). Se apartaron 3.923 filas por identidad, fecha, superficie o formato inválido y 15 identidades con versiones contradictorias. La cobertura detallada y los motivos están guardados; esas cantidades no acreditan cobertura de todo el tenis mundial.

Los archivos `ATP_Database.csv` y `atp_matches_amateur.csv` se conservaron como archivo sin forzar su clasificación en los circuitos del modelo. Los partidos sin estadísticas o con retiros/formatos no soportados se conservan fuera del subconjunto de ajuste. Los originales íntegros permiten una revisión posterior.

TML declara MIT en su página. MCP conserva CC BY-NC-SA: se descargó para investigación, pero **no alimenta los modelos ajustados** ni queda acreditado permiso para su uso comercial. No se consumieron cuotas de The Odds API ni créditos de proxy, y no se contrataron servicios.

## Matemática implementada

1. Observaciones binomiales de puntos ganados al saque, con ajuste por habilidad de saque propia, resto del rival y superficie.
2. Priors gaussianos y regularización para jugadores con poca muestra. Ajuste MAP con verosimilitud ponderada por antigüedad; incertidumbre mediante aproximación de Laplace y covarianza conjunta de los dos parámetros.
3. Puntuación punto→juego→set→partido; deuce y tie-break sin truncar colas, continuidad de saque y primer sacador desconocido integrado con probabilidad 1/2.
4. Distribución conjunta de juegos, sets, desempates y ganador del primer set. De ella salen ganador, marcador en sets, totales, hándicaps y tie-breaks con probabilidades compatibles.
5. Cuotas justas con devolución cuando corresponde. Sin una cuota ofrecida no se genera valor esperado de una apuesta real. Las líneas de cuarto se rechazan hasta implementar liquidación dividida.

No es todavía el modelo dinámico avanzado propuesto en toda su extensión. La ponderación de antigüedad no equivale a un proceso latente de estado; faltan efectos validados de fatiga, viajes, lesiones, clima y presión. La aproximación de incertidumbre tampoco incorpora todo el error de especificación.

## Entrenamiento actual

| Modelo | Partidos de entrenamiento | Observaciones de saque | Parámetros | Último periodo incorporado |
|---|---:|---:|---:|---|
| ATP | 74.029 | 148.058 | 6.254 | 9-sep-2026 |
| WTA | 20.614 | 41.228 | 2.344 | 30-ago-2026 |

Se usó historia desde 2018. El origen del candidato actual es 16-oct-2026. Como las fechas de origen pueden representar semanas de torneo, se aplicó un embargo de 35 días para no inventar un orden temporal preciso. Por eso una extracción que incluye resultados de octubre no significa que el candidato ya los incorpore todos a sus habilidades.

## Evaluación real de ganador

Modelos congelados al inicio de cada año y evaluados en los partidos reservados de ese año. Elo y la mezcla de Elo general/superficie siguen el mismo origen temporal. No se hicieron cambios de parámetros para mejorar el resultado observado en 2026.

| Circuito/año | Partidos | Log-loss candidato | Log-loss Elo general/superficie | Acierto candidato |
|---|---:|---:|---:|---:|
| ATP 2025 | 2.539 | 0,65575 | 0,62532 | 63,73 % |
| WTA 2025 | 2.417 | 0,69466 | 0,63278 | 63,30 % |
| ATP 2026 disponible | 2.451 | 0,64466 | 0,62855 | 64,75 % |
| WTA 2026 disponible | 2.146 | 0,65296 | 0,62177 | 66,45 % |

**Menor log-loss es mejor. El candidato no supera a la referencia Elo en estas pruebas.** En 2026, los intervalos del incremento de pérdida por bloques de periodo son ATP [0,00216; 0,03100] y WTA [0,00682; 0,05631]. Un porcentaje de acierto mayor que otro modelo no basta si la calidad de las probabilidades es peor.

Estas cifras corresponden a probabilidades MAP pasadas por Markov. La integración posterior se implementó en las consultas individuales, pero no se atribuyen a esa variante las métricas de la evaluación MAP. Los resultados económicos siguen sin medir.

## Evaluación inicial de otros mercados

Se evaluaron líneas ilustrativas fijas en el mismo conjunto de 2026, con el modelo congelado y sin seleccionar líneas por su resultado. La referencia es la frecuencia del entrenamiento por superficie y formato; **no son cuotas de casas**.

| Mercado | ATP: log-loss candidato / referencia | WTA: log-loss candidato / referencia |
|---|---|---|
| Hándicap A −3,5 juegos | 0,59428 / 0,64241 | 0,61992 / 0,66341 |
| Habrá tie-break | 0,66275 / 0,67237 | 0,55460 / 0,55084 |
| Ganador del primer set | 0,65500 / 0,69315 | 0,66466 / 0,69315 |
| Más de 22,5 juegos | 0,57289 / 0,56788 | 0,68594 / 0,66991 |

El hándicap mejora esta referencia sencilla. Los totales no la mejoran en ninguno de los dos circuitos. Primer set se compara aquí con una referencia de 50/50 por presentación aleatoria de jugadores, que es débil. Ninguno de estos resultados demuestra ventaja frente al mercado ni rentabilidad. No se ha usado el test para elegir un mercado a publicar.

## Evidencia y reproducción

- `download_manifest.json`, `download_summary.json`: recibos, tamaños, hashes y licencias declaradas.
- `canonical/matches.parquet`, `canonical/coverage.json`, `canonical/quarantine.json`: consolidación y exclusiones.
- `experiments/ATP_2025/`, `WTA_2025/`, `ATP_2026/`, `WTA_2026/`: modelos y predicciones reservadas; `evaluation.json` guarda métricas y protocolo.
- `experiments/*_2026/market_evaluation.json` y `heldout_markets.parquet`: evaluación de mercados adicionales.
- `models/ATP_current/`, `models/WTA_current/`: coeficientes, precisión y recibos de ajuste actual.
- `examples/ATP_hypothetical.json`, `WTA_hypothetical.json`: consultas hipotéticas con varios mercados e incertidumbre. No se afirma un encuentro programado ni una cotización real.

Se comprobaron unicidad de IDs canónicos, límites de conteos, fechas de corte y probabilidades complementarias de los ejemplos. Las 17 pruebas específicas pasaron, incluyendo simulación independiente punto a punto, conservación de masa, mejor de cinco, simetría, devoluciones, conflictos de fuentes, separación temporal y recuperación binomial. El arnés general inicial y final pasó con 1.300 pruebas y 88 omitidas. Docker no está disponible y su validación se omitió.

El primer intento del arnés en el checkout nuevo, sin la configuración local, produjo nueve fallos de pruebas heredadas que consultan la base de datos. Se confirmó la causa con una prueba dirigida y se cargó la configuración existente solo en memoria; la repetición completa pasó sin modificar la lógica de los motores. Los tests específicos de tenis no requieren esa configuración. La salida final está en `validation/harness_final.log`.

## Lo que falta para operar

1. **Información temporal mejor:** calendario futuro, horas verificadas y enlace de identidades. Permitirá actualizar habilidades con menos retraso sin usar información posterior al partido.
2. **Mejora y calibración:** usar validación separada para estudiar habilidades dinámicas y calibración; reservar una nueva prueba para los cambios futuros. El test 2026 ya se observó y no será presentado otra vez como una prueba intacta de variantes diseñadas a partir de él.
3. **Cuotas y reglas de cada casa:** definir casas, presupuesto de consultas compartido y liquidación por retiros antes de evaluar EV, CLV o ROI.
4. **Validación prospectiva:** guardar pronósticos antes de los encuentros y medir varios mercados con las cotizaciones disponibles en ese momento.

La implementación local avanza sin esos datos externos. La publicación de picks requiere que el candidato y la selección pasen sus comprobaciones; esta primera versión todavía no lo ha conseguido.

## Segunda fase: correcciones operativas y candidato híbrido

Se añadió un registro de 15.982 jugadores canónicos. La coincidencia aproximada solo presenta candidatos; una identidad de proveedor necesita evidencia y revisión antes de quedar vinculada. Para la muestra actual se revisaron ocho identidades ATP/WTA mediante nombre completo, circuito, evento de The Odds API y perfil oficial. La hora se normaliza a UTC, pero `commence_time` sigue marcada como estimación y no como hora real de inicio ni cierre del mercado.

La captura de cuotas ahora exige límite local, reserva de cuenta y mercados explícitos. Conserva el JSON original, hora de solicitud/recepción, hash y cabeceras de consumo sin guardar la clave. Ante un fallo de red o cabeceras inválidas bloquea nuevas consultas pagadas hasta refrescar el saldo. Compara la mejor cuota solamente para una misma combinación de evento, mercado, selección, descripción y línea; cuotas lay quedan fuera de esa comparación.

En dos partidos de muestra —uno ATP y uno WTA— la cobertura observada fue:

| Casa | Tipos de mercado observados | Cotizaciones |
|---|---:|---:|
| LeoVegas | 7 | 84 |
| Pinnacle | 5 | 52 |
| Coolbet | 5 | 44 |
| Coral | 4 | 24 |
| Ladbrokes UK | 4 | 24 |

LeoVegas incluyó ganador de primer y segundo set; Pinnacle y Coolbet aportaron ganador, hándicaps, totales y líneas alternativas. Esto es una muestra actual, no una garantía de cobertura futura ni de acceso desde una jurisdicción determinada. Se consumieron 19 créditos confirmados; el saldo pasó de 6.844 a 6.825. El registro local reservó conservadoramente 29 al incluir capacidad apartada antes de cada solicitud.

Entre 116 selecciones comparables de esa muestra, Pinnacle tuvo la mayor cuota observada en 46, LeoVegas en 41 y Coolbet en 14; las restantes se repartieron entre cinco casas. Por eso la recomendación no es elegir una sola casa: usar LeoVegas para amplitud, Pinnacle como referencia y frecuente mejor precio, y Coolbet como complemento, siempre sujeto a disponibilidad real de la cuenta.

La combinación de ganador se ajustó con predicciones de 2025, sin tocar los resultados 2026. Los pesos aprendidos fueron 25,28 % Markov / 74,72 % Elo en ATP y 15,62 % / 84,38 % en WTA, además de una escala de calibración. Menor log-loss y Brier es mejor:

| Evaluación | Circuito | Partidos | Híbrido log-loss / Brier | Elo calibrado log-loss / Brier |
|---|---|---:|---:|---:|
| Modelo congelado 2026 | ATP | 2.451 | 0,62243 / 0,21668 | 0,62755 / 0,21896 |
| Modelo congelado 2026 | WTA | 2.146 | 0,61832 / 0,21504 | 0,62186 / 0,21652 |
| Walk-forward mensual jul–sep | ATP | 734 | 0,61585 / 0,21373 | 0,61963 / 0,21554 |
| Walk-forward mensual jul–sep | WTA | 722 | 0,59507 / 0,20443 | 0,60204 / 0,20759 |

Frente a Elo calibrado, el intervalo exploratorio por bloques para la diferencia de log-loss del híbrido fue negativo en el anual ATP y WTA, y en el mensual WTA. En ATP mensual fue [−0,00916; 0,00118], que incluye cero. La mejora ATP mensual aún puede ser ruido. Además hubo comparaciones múltiples y dependencia entre jugadores que ese intervalo no reproduce por completo.

La liquidación mantiene todos los retiros en el libro. Para Pinnacle, con perfil verificado desde el 16-oct-2026, ganador queda válido después de un set completo; totales y hándicaps de partido incompleto quedan anulados salvo que exista una regla más específica. Ganancias, pérdidas, devoluciones y anulaciones permanecen separadas. Una casa o mercado sin regla verificada queda pendiente y hace que el ROI se marque incompleto.

Pasaron 30 pruebas específicas y el arnés general completo: 1.300 aprobadas, 88 omitidas. No se desplegó, publicó ni activó una automatización. El híbrido es un candidato de investigación para ganador del partido; no acredita rentabilidad ni se extiende automáticamente a los otros mercados.
