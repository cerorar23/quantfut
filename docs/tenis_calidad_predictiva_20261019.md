# Calidad predictiva del motor: evaluación ejecutada y criterio futuro

19 de octubre de 2026. **Evaluación técnica completada; calidad predictiva confirmatoria todavía no acreditada.** El motor produce probabilidades de investigación. Esta revisión no usa cuotas, no calcula rentabilidad y no promete certeza individual.

## Resultado de la evaluación común

Se reprodujeron las predicciones archivadas contra sus fuentes y fórmulas. Los seis modelos se evaluaron sobre exactamente los mismos encuentros, orientados al mismo jugador y contrastados con el resultado canónico. Se excluyeron identidades ambiguas y efectos de jugador/superficie no entrenados. Los modelos retrospectivos tienen origen1-ene-2026; no se utilizaron los modelos de octubre para predecir partidos anteriores.

| Circuito | Muestra común / universo archivado | Híbrido Log-Loss | Elo de superficie calibrado | Weighted Elo |
|---|---:|---:|---:|---:|
| ATP | 2.207 / 2.451 (90,0 %) | 0,62956 | 0,63217 | 0,63814 |
| WTA | 581 / 2.146 (27,1 %) | 0,60441 | 0,60775 | 0,60365 |

Menor Log-Loss es mejor. Se calcularon también Brier, ECE, curvas de calibración, aciertos y cobertura para los seis modelos: híbrido, Markov, Elo de superficie, Elo de superficie calibrado, Weighted Elo y Elo adaptativo.

**No se ha demostrado superioridad del híbrido.** Sus diferencias frente a las dos referencias principales tienen intervalos que incluyen cero, tanto al agrupar por torneo como por periodo de fuente. Los cuatro contrastes principales —dos referencias por dos circuitos— incorporan corrección Bonferroni: intervalos98,75 % por contraste, con alfa familiar5 %. El bootstrap no captura toda la dependencia entre jugadores de distintos torneos; la comprobación por periodos es una sensibilidad adicional, no una prueba independiente.

La muestra de2026 ya fue inspeccionada durante el desarrollo. Estas cifras son **exploratorias** y no convierten ese año en un conjunto confirmatorio intacto. No se eligió un modelo ganador retrospectivo para publicarlo como validado.

## Qué significa la confianza que anuncia el modelo

Se eligió siempre el lado con mayor probabilidad, antes de utilizar el resultado. Se revisaron bandas fijas y umbrales50/70/80/90 %, conservando la cobertura: no se buscó retrospectivamente el umbral que más acierta.

Ejemplos del híbrido ATP en la muestra común:

| Probabilidad anunciada | Casos | Probabilidad media | Aciertos observados |
|---|---:|---:|---:|
| 50–60 % | 889 | 54,8 % | 54,6 % |
| 60–70 % | 721 | 64,6 % | 64,9 % |
| 70–80 % | 418 | 73,9 % | 74,6 % |
| 80–90 % | 145 | 84,5 % | 82,8 % |
| 90–100 % | 34 | 93,1 % | 91,2 % |

Los resultados son compatibles con una calibración útil en esta muestra, pero las bandas altas son pequeñas. En la banda80–90 %, el intervalo95 % de acierto por bloques es aproximadamente75,9–89,1 %. No equivale a garantizar que el próximo pronóstico acertará83 % o que cualquier caso individual tiene una probabilidad conocida sin error.

En WTA, la banda90–100 % tiene solo cinco casos. Aunque todos acertaron, **no se presenta un intervalo bootstrap[100 %,100 %] como certeza**: cuando no existe variación observada, ese método no puede estimar el riesgo de un fallo no visto. Se conserva como referencia el intervalo Wilson con supuesto de independencia, cuyo límite inferior ronda56,6 %, y se impide etiquetar esa banda como acreditada.

## Identidades y cobertura

La normalización de acentos detectó **dos grupos ATP y50 WTA** con varios IDs: se añadió Julio César Porras al caso ya conocido de Andre Ilagan. Se conservó una cuarentena reproducible; no se fusionaron IDs por similitud ni se eligió el de mayor frecuencia.

En el universo WTA archivado se excluyeron1.156 casos por identidades ambiguas,350 por efectos de superficie/jugador no entrenados y59 por identidad no disponible en el modelo de origen. En ATP se excluyeron224 por efectos no entrenados y20 por identidad no disponible. Las categorías se aplican secuencialmente, una sola exclusión por caso.

Esto resuelve la **protección frente al uso de una identidad ambigua**, no la reconstrucción de los puentes históricos. Para recuperar esa cobertura hacen falta fuentes que acrediten cada equivalencia y una nueva versión de datos/modelos reentrenados y evaluados. La cuarentena actual utiliza conocimiento actual; no se afirma que estuviera disponible antes de cada partido histórico. Los modelos congelados conservan su entrenamiento original y sus limitaciones.

## Mercados adicionales y fundamento científico

Se revisaron **diez familias en50 grupos de contrato, circuito y formato**, con45.444 probabilidades conservadas tras el filtro común. Cada grupo tiene métricas, bandas y cobertura propias. Son probabilidades Markov coherentes sin una calibración nueva aplicada: no se reutiliza la calibración de una línea en otra ni se declara que todos los mercados estén acreditados. Ganador se mantiene como contrato del protocolo futuro principal; los mercados restantes requieren sus propios protocolos confirmatorios antes de hacer afirmaciones de calidad sobre ellos.

Las publicaciones orientan las hipótesis; no sustituyen la prueba del motor:

- [Angelini, Candila y De Angelis](https://cris.unibo.it/retrieve/e1dcb337-ea48-7715-e053-1705fe0a6cc9/Weighted%20ELO%20rating%20predictions%20in%20tennis.pdf): Weighted Elo utiliza el marcador. La implementación declara su adaptación a bloques de fecha de fuente, porque no conocemos el orden físico completo dentro de cada semana.
- [Hornery y colaboradores](https://pubmed.ncbi.nlm.nih.gov/17326696/): revisión de fatiga y rendimiento con limitaciones metodológicas; no se toma una reducción universal por hora como coeficiente validado del modelo.
- [Maynard y colaboradores](https://pubmed.ncbi.nlm.nih.gov/41272436/): encontraron cambios del sueño con viajes, pero no una correlación significativa entre su alteración y rendimiento competitivo en la muestra estudiada. No se impone una penalización automática de victoria por huso horario.

El candidato futuro principal no incorpora carga, viajes ni clima sin una mejora validada. Resolver la sede de Palm Hills o añadir pronósticos meteorológicos no acredita por sí solo mejor predicción.

## Implementación entregada

`tennis_quality_v3` incorpora cuarentena de identidades, muestra común, incertidumbre por bloques, bandas de confianza, cobertura con umbrales fijos y registro prospectivo sin cuotas. Verifica versiones y reglas, nombres orientados, estado oficial reciente y probabilidades; vuelve a comprobar la vigencia después del cálculo para impedir un sello tardío. Los resultados entran únicamente en una evaluación posterior. Los registros y protocolos se crean sin sobrescribir versiones existentes.

Se entrenaron nuevas referencias Elo adaptativo/Weighted Elo con **los mismos datos y embargo del candidato actual**:74.029 partidos ATP y20.614 WTA. Son referencias futuras, distintas de las de origenenero utilizadas en la comparación histórica. Se conservaron los37 módulos y12 artefactos del estudio financiero anterior.

La entrega tiene **332 pruebas del motor**, incluidas20 nuevas de calidad. Se probaron identidad, orientación, probabilidades inválidas, duplicados, resultados posteriores, versiones alteradas, independencia entre circuitos, casos vacíos, intervalos degenerados, emisión sin cuotas y caducidad durante el cálculo. Las pruebas con entradas artificiales no se contabilizan como encuentros financieros o predictivos reales.

## Protocolo futuro y pendientes que no pueden fabricarse

El protocolo nuevo fija20-oct-2026 00:00UTC a1-jul-2027 00:00UTC. Es separado del financiero y conserva sus versiones. Sus umbrales son decisiones de diseño declaradas antes del estudio, **no una norma universal de certificación**:

- Al menos500 resultados completos y30 bloques de competición por circuito; son mínimos, no una garantía de potencia.
- Comparaciones primarias contra Weighted Elo y Elo de superficie calibrado, con corrección por multiplicidad y revisión en ambos esquemas de bloques.
- Bandas de probabilidad≥70 % con al menos200 observaciones para considerarlas respaldadas; intervalo del error de calibración dentro de±5 puntos porcentuales. Bandas sin muestra suficiente quedan sin acreditar.
- Cobertura mínima20 % al umbral70 % dentro de los casos completados y evaluables. La cobertura de la evaluación parte de pronósticos registrados, **no de todos los partidos del calendario**: rechazos previos y cobertura de calendarios deben auditarse por separado.
- No reajustar el candidato ni seleccionar reglas sobre esa muestra. Informes intermedios son controles operativos; no permiten declarar éxito antes del cierre fijo.

Actualmente hay **cero resultados confirmatorios** en el protocolo nuevo. El evaluador distingue resultados ausentes, retiros fuera del contrato de probabilidad de partido completado y evidencia rechazada. Conserva el requisito de fuentes de resultados y tiempos físicos verificados del contrato existente; una fecha programada o la recepción de un estado no se convierten en hora real. Ese requisito de disponibilidad temporal sigue pendiente para incorporar resultados que no lo cumplan.

Pasar la compuerta estadística permitiría una revisión independiente de fuentes, interpretación y protocolo. Un hash local no demuestra cuándo existió cada pronóstico; el sello anterior de DigiCert tampoco se extiende automáticamente a archivos creados después. No se otorga un certificado académico o institucional ni certeza individual por superar pruebas de software.

Quedan abiertos: acreditar los puentes de identidad para recuperar cobertura, reunir la muestra futura verificable del ganador, y completar calibración/validación confirmatoria propia de los demás mercados. Estos resultados futuros no existen hoy y no pueden reemplazarse por datos artificiales o por volver a evaluar2026.

## Archivos y operación

Entrega vigente: `data/tennis/predictive_quality_v3_20261019_v3/`. Incluye `RESULTADOS.md`, comparaciones ATP/WTA, `identity_quarantine.json`, `all_market_quality.json`, referencias congeladas, `future_quality_protocol.json` y registro futuro vacío. Las dos preparaciones anteriores se conservan con avisos de sustitución por la corrección del intervalo bootstrap degenerado y la comprobación del código activo; no tuvieron pronósticos confirmatorios.

Desde el motor entregado, con su carpeta en `PYTHONPATH`:

```powershell
python -m tennis_quality_v3 seal --protocol RUTA_PROTOCOLO --event RUTA_EVENTO_REVISADO --output-root RUTA_PRONOSTICOS
python -m tennis_quality_v3 evaluate --protocol RUTA_PROTOCOLO --predictions-root RUTA_PRONOSTICOS --results RUTA_RESULTADOS --output RUTA_INFORME_NUEVO
```

El evento revisado exige `event`, `circuit`, `player_ids`, `fixture_receipt` y `tournament_metadata` con el contrato existente de evidencia. No acepta resultados como entradas de pronóstico. No se activó un servicio automático, no se gastaron créditos de cuotas y no se ejecutaron apuestas.

El envío de la nueva huella a DigiCert quedó pendiente: la revisión automática exigió autorización específica para el protocolo predictivo, distinta de la del financiero. No se envió la nueva huella; el protocolo local y sus archivos se conservaron.
