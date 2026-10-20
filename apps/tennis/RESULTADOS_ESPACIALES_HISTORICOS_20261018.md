# Resultado de la comparación espacial retrospectiva

18 de octubre de 2026. La comparación se ejecutó; las variables espaciales no muestran una mejora suficientemente clara para activar la corrección. El resultado no prueba que los viajes carezcan de efecto: evalúa una especificación lineal regularizada y una muestra concreta con procedencia incompleta.

## Muestra y resultado principal

Se ajustó la corrección en 2.965 partidos de desarrollo 2024 y se evaluaron ambos modelos sobre los mismos 2.833 partidos de 2025. Estos representan el 52,68 % de los 5.378 partidos asignados a la partición exploratoria. Los demás no se convierten en ceros ni reciben variables inventadas. Se excluyen resultados no convencionales y faltantes conforme al contrato de la cohorte.

| Métrica, menor es mejor | Base | Base + Espaciales |
|---|---:|---:|
| Log-Loss | 0,638733 | 0,638682 |
| Brier | 0,224394 | 0,224370 |
| ECE, 10 intervalos iguales | 0,026213 | 0,026260 |

La diferencia de Log-Loss, espacial menos base, es −0,00005086. El intervalo descriptivo del 95 % por remuestreo de competiciones es [−0,00015967; +0,00005490]: incluye cero. La diferencia de Brier es −0,00002390, también con intervalo que incluye cero. ECE sube ligeramente. Por tanto, no se declara superioridad ni mejor calibración.

Por circuito, la diferencia de Log-Loss es −0,00000328 en ATP y −0,00008919 en WTA; ambos intervalos incluyen cero. Estas desagregaciones son descriptivas, no una selección de ganador.

## Sensibilidad geográfica

Se repitió el ajuste excluyendo en entrenamiento y evaluación las transiciones cuyo origen o destino tenga tolerancia espacial superior a 1.000 m. Se ajustó con 2.851 partidos y se evaluó con 2.718:

| Métrica | Base | Base + Espaciales |
|---|---:|---:|
| Log-Loss | 0,634892 | 0,634815 |
| Brier | 0,223106 | 0,223076 |
| ECE | 0,025192 | 0,025680 |

La diferencia de Log-Loss es −0,00007648, con intervalo [−0,00019424; +0,00002587]. Sigue sin una mejora clara. Los valores absolutos de esta tabla no deben compararse directamente con la principal para atribuir causalidad: cambió la muestra. Dentro de cada tabla, ambas variantes sí usan exactamente los mismos partidos.

## Cómo se evitó utilizar información futura

La base actual pertenece a la familia de saque/resto Markov combinada con Elo mediante una mezcla simétrica de log-odds. Sus parámetros operativos actuales incorporan información posterior a 2024; no se aplicaron retrospectivamente.

Se reconstruyó esa misma familia en cada origen anual:

1. Para generar predicciones de 2023 se entrenó con información anterior al origen de 2023 y embargo de 35 días. Esas predicciones, con etiquetas anteriores al embargo de 2024, calibran la mezcla de 2024.
2. La base de 2024 usa un modelo de saque/resto y Elo congelados al origen 2024, y la calibración anterior. Sus predicciones alimentan el ajuste espacial de desarrollo.
3. Para 2025, la mezcla se calibra con predicciones de 2024 anteriores al embargo; el modelo de saque/resto y Elo se congelan al origen 2025. Los artefactos de saque/resto de ese origen que ya existían se reutilizaron en solo lectura tras verificar recibos y fuente canónica.
4. La corrección espacial y su escala RMS se ajustan exclusivamente en la partición de desarrollo 2024. No se ajustan con etiquetas de 2025.

La calibración utiliza ediciones de fuente completas anteriores al embargo. La comparación conserva `comparison_block_id`: distintos partidos o rubbers de una misma competición acreditada no se reparten entre entrenamiento y evaluación. Los 201 partidos de frontera permanecen excluidos del ajuste y de la evaluación.

Se reconstruyen coeficientes históricos, no se afirma reproducir los coeficientes actuales ni realizar un nuevo backtest del candidato congelado de octubre de 2026. Las probabilidades de punto son MAP, sin integrar toda la incertidumbre posterior; la base permanece congelada dentro de cada año. No es un walk-forward mensual.

## Corrección probada y alcance

La especificación fijada antes del cálculo es:

`logit(p_espacial) = logit(p_base) + beta · [(x_A − x_B) / RMS_entrenamiento]`.

Se incluyen distancia geodésica entre sedes observadas, cambio de altitud de terreno y diferencia firmada de desfase UTC. No hay intercepto ni centrado, de modo que intercambiar jugadores complementa la probabilidad. La penalización ridge es 1 en unidades de pérdida media, sin búsqueda sobre 2025. Se comparten tres coeficientes entre ATP y WTA; la base y su mezcla se ajustan por circuito.

Los coeficientes normalizados obtenidos son, respectivamente, 0,000831; 0,005015 y 0,004339. La regularización los mantiene cerca de cero. Su signo no constituye una ley fisiológica ni una penalización universal por viaje. El desfase UTC no mide por sí mismo el jet lag residual. No se calculan horas reales de descanso ni se imputan llegadas, vuelos o dobles ausentes.

Las sedes se reconstruyeron con fuentes recibidas en 2026. El resultado es retrospectivo y 2025 ya era exploratorio: no equivale a una validación con información realmente disponible en cada fecha. Los intervalos proceden de 1.000 remuestreos emparejados de competiciones (116 en la principal, 112 en sensibilidad), con semilla 20261018. No recogen toda la dependencia de jugadores entre torneos ni corrigen comparaciones múltiples.

## Decisión y recomendaciones

La corrección queda experimental, sin modificar las probabilidades del motor congelado. Se mantiene la base para operar o seguir midiendo. No hay evidencia nueva de ROI, CLV ni ventaja frente a cuotas ejecutables; esta fase no consultó proveedores deportivos ni consumió créditos de The Odds API.

Para mejorar la investigación:

- Completar las 88 entradas de sede pendientes y los antecedentes desconocidos; una sede de destino conocida no acredita el viaje real.
- Priorizar carga observable y evidencia temporal verificable antes de convertir distancia en fatiga. Conservar ausencias e incertidumbre explícitas.
- Si se estudian otra regularización, no linealidades o coeficientes por circuito, elegirlos mediante bloques temporales internos de 2024. No buscar configuraciones hasta conseguir que 2025 mejore.
- Registrar un protocolo nuevo y un periodo futuro intacto para una selección posterior. El periodo reservado al candidato ya congelado no se reutiliza para seleccionar esta corrección nueva.
- Mantener las ablaciones y la comparación común. Una mejora mínima y sensible a la muestra no justifica añadir complejidad operativa.

## Entrega y verificación

Resultados: `data/tennis/historical_comparison_20261018/`. Incluye protocolo escrito antes de los ajustes, componentes de Markov/Elo por origen, calibraciones, 11.240 predicciones de base, predicciones de las dos comparaciones, informes con métricas y puntos de calibración, `calibration_bins.csv` y auditoría con huellas de los archivos.

Código en el motor aislado: `tennis_engine/historical_comparison.py`, `scripts/run_historical_comparison.py`, `scripts/audit_historical_comparison.py` y `tests/test_historical_comparison.py`. Se aprobaron 182 pruebas de tenis, nueve nuevas. Verifican la exclusión de información futura, identidad/orientación, muestra común, simetría, escala solo de entrenamiento, partición indivisible y sensibilidad. La auditoría reproduce coeficientes y métricas y comprueba los 12 artefactos congelados intactos.

El arnés general inicial y final aprobó 1.310 pruebas, omitió 88 y emitió dos avisos; el final tardó 145,51 segundos. Docker no estaba disponible para esa comprobación. La revisión de formato y la coincidencia por huella de los cuatro archivos entregados también pasaron.

Desde la raíz del proyecto, el script `run_historical_comparison.py --output <directorio_nuevo>` ejecuta el experimento con los archivos locales. Un resultado terminado no se sobrescribe. `audit_historical_comparison.py --output data/tennis/historical_comparison_20261018` verifica el resultado sin volver a entrenar los modelos de base. El protocolo conserva las rutas de entrada y sus huellas; no es necesario proporcionar claves de API.
