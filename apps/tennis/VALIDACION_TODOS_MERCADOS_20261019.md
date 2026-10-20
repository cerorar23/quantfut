# Validación prospectiva de los diez mercados — 19 de octubre de 2026

Ampliación implementada, emitida y conectada al seguimiento continuo del mismo chat. Primera emisión: **18 partidos, 11 ATP y 7 WTA; 990 tareas de contrato, 110 grupos observados y cero resultados confirmatorios**. Ningún grupo tiene todavía calidad acreditada. Son 55 tareas relacionadas por encuentro, no 990 partidos independientes.

Se conservan los 37 módulos originales, los 12 artefactos anteriores y los cuatro módulos de calidad ya sellados. Se añaden cuatro módulos independientes `tennis_allmarkets_v1`, 25 pruebas y un generador de vistas legibles. Motor entregado: `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis`.

## Cobertura

| Familia | Tareas registradas | Evaluadas |
|---|---:|---:|
| Ganador del partido | 18 | 0 |
| Ganador de cada set | 54 | 0 |
| Total de juegos del partido | 162 | 0 |
| Hándicap de juegos del partido | 126 | 0 |
| Total de sets | 18 | 0 |
| Hándicap de sets | 36 | 0 |
| Al menos un tiebreak | 18 | 0 |
| Marcador final por sets, vector completo | 18 | 0 |
| Total de juegos de cada set | 270 | 0 |
| Hándicap de juegos de cada set | 270 | 0 |

Mejor de tres: juegos totales 18,5/20,5/21,5/22/22,5/23/23,5/24,5/26,5; hándicaps de juegos de A −5,5/−3,5/−1,5/0/+1,5/+3,5/+5,5; total de sets 2,5 y hándicap de sets de A −1,5/+1,5. Cada set 1–3: ganador, total 8,5/9,5/10/10,5/12,5 y hándicap de A −2,5/−1,5/0/+1,5/+2,5. Además ganador del partido, cualquier tiebreak y los cuatro marcadores terminales conjuntos.

Mejor de cinco: sets 1–5, seis marcadores terminales, totales de sets 3,5/4,5 y juegos totales 30,5/32,5/34,5/36/36,5/38,5/40,5/42,5; los demás hándicaps y líneas por set se conservan. Este formato aún no tiene emisiones. Se separan reglas de tiebreak decisivo a 7 y 10; no se hereda evidencia entre formatos. No se afirma validación de líneas arbitrarias, mercados no acordados como aces/dobles faltas ni ofertas inexistentes en el proveedor.

Las probabilidades incluyen alternativa complementaria y empate/sin acción. Las dos caras no cuentan como muestras independientes. En hándicap, la contraparte usa el signo contrario de la línea. Marcador final se evalúa como una tarea multiclase por partido, sin contar sus cuatro o seis alternativas como observaciones independientes.

## Modelo, fuentes y cronología

Las diez familias utilizan la misma distribución Markov conjunta con parámetros de saque/resto congelados. No se mezclan marginales recalibradas por separado con una distribución conjunta distinta. El ganador Markov puede diferir del híbrido del estudio original, que continúa intacto.

Protocolo independiente creado antes del periodo 20-oct-2026 00:00 UTC a 1-jul-2027 00:00 UTC. Cada registro lleva su hora real nueva y un vínculo al registro original de ganador. **No se retrodató: este protocolo y sus emisiones tienen huellas locales, sin nuevo sello externo DigiCert.** El sello anterior no los cubre; un hash local no acredita por sí solo existencia previa frente a terceros.

La emisión verifica identidades/cuarentenas, parámetros entrenados, reglas, fechas, código congelado y fuentes oficiales/calendario/revisión exacta. Reproduce la probabilidad Markov del registro padre. La evaluación reconstruye la tabla para detectar probabilidades alteradas aunque se recalcule el hash local.

La política nueva permite evidencia archivada de programa y calendario de hasta cuatro horas **solo antes de la hora mínima oficial publicada**. Repite la comprobación después del cálculo. El registro padre tuvo que satisfacer su frescura original al emitirse. Esta declaración independiente no modifica el protocolo anterior de ganador. Si la cota pasó o los recibos caducaron, se abstiene; no renueva fechas ni fuerza consultas.

## Evaluación

Log-Loss y Brier del vector completo; métricas binarias condicionadas a acción con ECE de diez intervalos. El Brier vectorial suma sobre clases sin dividir por su número y es distinto del binario. El marcador final tiene métricas multiclase y calibración de su resultado más probable. En otros contratos, la calibración del vector puede incluir push como clase más probable.

Empates de línea y sets no disputados conservan su masa como push: se incluyen en la puntuación vectorial y se separan de la binaria condicionada. Los retiros, descalificaciones y walkovers quedan fuera del contrato probabilístico de partido completado y dentro del denominador de cobertura. Esta regla matemática no sustituye las reglas financieras de ninguna casa.

Los resultados requieren fuentes verificables, identidad/ganador/marcador compatibles y, cuando corresponde, inicio/final físicos. No se convierten horarios programados o recibos en horas reales. Un resultado inválido mantiene el pronóstico pendiente y visible en cobertura (`rejected_results`); un pronóstico inválido se señala en `rejected_records`. No se seleccionan pérdidas ni se borran observaciones desfavorables.

Cada grupo separa circuito, formato, regla decisiva, familia, selección, línea y set. Criterios fijados: 500 partidos evaluados y 30 bloques de competición por grupo, cobertura ≥80%, cierre del periodo y evidencia de calibración en bandas ≥70% con al menos 200 observaciones y tolerancia de cinco puntos. Son decisiones de diseño, no garantías de potencia o precisión. Los intervalos se calculan por competición y fecha UTC con corrección conservadora por las 528 combinaciones previstas, cinco bandas y ambos agrupamientos; no eliminan toda dependencia por jugadores repetidos. Muestras sin variación no implican certeza.

Cumplir los criterios solo habilita revisión independiente; el evaluador nunca certifica calidad o beneficios. No se reajusta el modelo, se escogen líneas por resultados ni se declara éxito anticipado. Los grupos no observados siguen sin evidencia.

El histórico exploratorio previo se conserva separado: 45.444 probabilidades después del filtro común de identidades, 50 grupos y líneas parcialmente distintas de las nuevas. `historical_context.json` lo enlaza sin convertirlo en evidencia futura ni agregar sus métricas como validación universal.

## Continuidad y archivos

La automatización existente `continuidad-de-validaci-n-predictiva-de-tenis` sigue ACTIVA en el mismo chat cada dos horas; capturas cada cuatro, máximo 12 intentos API-Tennis/día UTC. Se amplió su instrucción para emitir/evaluar las diez familias. Sin duplicar automatizaciones o cambiar límites/notificaciones. Repetición comprobada: 18 ya registrados, cero duplicados.

Raíz: `data/tennis/all_markets_prospective_20261019/`. Archivos:

- `protocol.json`, `predictions/`: método y 18 registros nuevos inmutables.
- `emission_initial.json`, `emission_repeat_check.json`: primera emisión y deduplicación.
- `evaluation_initial.json`: 18 eventos/110 grupos, cero resultados/rechazos.
- `RESUMEN.md`, `PRONOSTICOS_POR_MERCADO.md`: interpretación y probabilidades completas.
- `historical_context.json`: antecedentes exploratorios separados.

Con el motor aislado como directorio de módulos:

```text
python -m tennis_allmarkets_v1 seal --protocol RUTA_PROTOCOL --parents-root RUTA_GANADORES --predictions-root RUTA_MERCADOS --output INFORME_NUEVO
python -m tennis_allmarkets_v1 evaluate --protocol RUTA_PROTOCOL --predictions-root RUTA_MERCADOS --results LISTA_ADMITIDA_NUEVA --output INFORME_NUEVO
```

Cada ejecución genera informes/listas nuevos sin sobrescribir la entrega inicial. La emisión deduplica por evento, sin depender del nombre del archivo padre. No editar módulos congelados: un cambio metodológico exige otra versión y otro estudio futuro.

Cero créditos de The Odds API y cero consultas nuevas de API-Tennis; cero órdenes o apuestas. El estudio financiero permanece limitado a ganador y no se amplían sus autorizaciones. La calidad probabilística no acredita rentabilidad.

Verificación del motor entregado: **367 pruebas aprobadas**, incluidas 25 específicas. Prueban la implementación; la evidencia deportiva futura sigue pendiente.
