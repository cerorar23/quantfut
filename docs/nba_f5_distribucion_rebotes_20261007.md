# NBA-RUN-052 — distribución de rebotes F5

Trabajo del 7 de octubre de 2026, America/Mexico_City; sellos UTC del 8 de octubre. Investigación retrospectiva local. El cierre se comprueba en `checkpoint.json` de la carpeta canónica.

Se avanzó F5 con una distribución de rebotes que combina minutos de RUN-050 y tasa individual encogida hacia un prior fijo. La familia se eligió en validación, antes de evaluar las temporadas posteriores: **binomial negativa**. En **59.816 casos**, el CRPS baja de **1,376733 a 1,332904** frente a la referencia Poisson de media reciente, una reducción descriptiva aproximada del **3,18%**. El error medio baja de **1,944846 a 1,911748 rebotes**. La diferencia es favorable en las tres temporadas y los nueve bloques temporales.

El resultado permite continuar con F6 en investigación. No acredita disponibilidad prepartido, superioridad de mercado, calibración completa ni producción; G0–G9 permanecen pendientes. La familia inicial sigue siendo provisional y este experimento no resuelve los contratos ni las cuotas históricas faltantes.

## Población y fuentes

Se preservan las **159.075 etiquetas de roster**, los **6.150 partidos regulares** y los boxscores originales. Se verifica la capa de namespace de 28 jugadores del partido 0022400942. Se unen los rebotes del boxscore con los minutos de regulación derivados de las rotaciones aceptadas.

Hay **5.840 partidos sin prórroga** y **310 con prórroga**. Los 310 quedan fuera de la historia de tasas y la evaluación de rebotes: sus rebotes completos no son etiquetas de regulación verificadas por periodo. No se reescalan los conteos completos ni se dividen por minutos incompatibles.

La construcción produce **98.644 filas de features**. Del roster completo se excluyen 8.017 filas de partidos con OT, 25.845 de cero exposición en juegos sin OT y 26.569 por historial insuficiente de minutos o tasa sin OT. Estas categorías y las features suman 159.075. Los ceros y las exclusiones siguen en el archivo de etiquetas; no se declaran convocados ni DNP futuros conocidos.

La evaluación es condicional a **exposición positiva observada y partido finalizado sin OT**, condiciones determinadas después del evento. Las features no utilizan el resultado, los minutos ni el equipo actuales como información previa. La exclusión por fecha del evento tampoco demuestra primera recepción histórica o conocimiento de revisiones en aquel corte.

## Protocolo y elección

Protocolo `F5-regulation-rebounds-exploratory-v2`, fijado en el evento local **106**. El evento **105** conserva el intento inicial rechazado antes de validación por un indicador NumPy no serializable. Se corrigió a bool/float nativos y se añadió una regresión JSON. Las etiquetas/features/outcomes se reutilizan byte a byte, con hashes y comparación de AST de sus constructores; fuentes y código del intento anterior quedan archivados.

| Bloque | Temporada | Casos | Uso |
| --- | --- | ---: | --- |
| Entrenamiento | 2021-22 | 19.513 | Ajustar dispersión global NB |
| Validación | 2022-23 | 19.315 | Elegir familia por CRPS |
| Evaluación exploratoria | 2023-24–2025-26 | 59.816 | Evaluar elección congelada |

Tasa individual: hasta veinte apariciones positivas previas, de la misma temporada y sin OT; mínimo diez. Prior heredado de `research-v0.1`: **30 minutos a 0,18 rebotes/minuto**. No se eligieron esos valores a partir de esta validación. El baseline es Poisson con la media de los últimos diez conteos elegibles.

Los minutos de la referencia RUN-050 pueden usar exposición de regulación de partidos anteriores con OT: esa exposición sí tiene etiquetas verificadas. Su distribución previa conserva el encogimiento reciente existente. Toda la fecha objetivo queda fuera de ambas historias.

Familias comparadas en validación:

| Familia | CRPS de validación |
| --- | ---: |
| Poisson de media reciente | 1,381608 |
| Mezcla Poisson de tasa × minutos | 1,336834 |
| Gamma-Poisson con incertidumbre de tasa | 1,336216 |
| Binomial negativa con dispersión entrenada | **1,335636** |

La dispersión se ajusta con el segundo momento del residuo de entrenamiento, descontando la media y la variabilidad de la mezcla de minutos. **φ = 0,02628997**, forma **k = 38,03732**. Su máximo de entrenamiento es 2022-04-10; corte lógico 2022-07-01 dentro del replay. No demuestra que el ajuste existiera o se hubiera recibido entonces.

Parámetros congelados en el evento **107**; familia elegida y congelada en el **108**, antes de la evaluación posterior. La regla previa conserva el baseline si ningún candidato lo mejora en validación y usa un orden fijo para empates. La ventaja de NB sobre Gamma-Poisson en validación es pequeña, **0,000579**; no acredita superioridad universal entre esas familias. No se selecciona un modelo nuevo a partir del resultado posterior.

Las temporadas ya se habían inspeccionado en investigaciones anteriores. La separación de bloques evita usar etiquetas posteriores para ajustar o elegir esta corrida, pero no convierte el histórico en un test confirmatorio intacto.

## Resultado posterior

CRPS discreto de rebotes es la métrica primaria; no se compara numéricamente con CRPS continuo de minutos.

| Temporada | Casos | CRPS baseline → NB | MAE baseline → NB |
| --- | ---: | ---: | ---: |
| 2023-24 | 19.895 | 1,359994 → 1,318165 | 1,925036 → 1,891991 |
| 2024-25 | 19.794 | 1,398604 → 1,352786 | 1,973871 → 1,942351 |
| 2025-26 | 20.127 | 1,371771 → 1,327920 | 1,935882 → 1,901182 |
| Total | **59.816** | **1,376733 → 1,332904** | **1,944846 → 1,911748** |

Diferencia NB menos baseline de CRPS **−0,043829**, intervalo exploratorio 95% por fecha **[−0,047062; −0,040394]**. Bootstrap pareado de 1.000 réplicas, semilla 20261007, estimando una media ponderada por observaciones. No hay corrección por comparaciones múltiples ni confirmación prospectiva. RMSE **2,565692 → 2,520096 rebotes**.

NLL con suelo declarado **1e−300**: **2,375810 → 2,184129**. El baseline asigna probabilidad cero al resultado observado en **ocho casos**, cuyo log-score se limita mediante ese suelo; la NB no requiere recorte. Es un diagnóstico numérico limitado, no un NLL exacto finito de esos ocho casos.

## Calibración discreta y sensibilidad

La cobertura de un intervalo central nominal del 80% no tiene por qué ser exactamente 80% con conteos enteros. Se mide su masa probabilística real:

| Distribución | Cobertura observada | Masa central prevista | Cobertura menos masa |
| --- | ---: | ---: | ---: |
| Baseline | 79,611% | 88,584% | −8,973 puntos porcentuales |
| NB seleccionada | 87,008% | 88,243% | −1,235 puntos porcentuales |
| NB con minutos ampliados, diagnóstico | 88,759% | 88,402% | +0,357 puntos porcentuales |

La sensibilidad con minutos ampliados de RUN-051 se evalúa por separado: **CRPS 1,333808**, ligeramente peor que la referencia NB sin ampliar. No participa en la selección ni reemplaza la referencia principal por su mejor cobertura. No se usan los escenarios de equipo con disponibilidad conocida a posteriori en las métricas predictivas.

PIT aleatorizado determinista por caso para evitar artefactos de discretización. Los diez bins de NB contienen **6.096 / 5.909 / 5.915 / 5.812 / 5.720 / 5.899 / 6.025 / 5.767 / 6.146 / 6.527** casos. Se guardan Brier y tablas de fiabilidad para umbrales de investigación 4,5 / 7,5 / 10,5, además de desgloses por banda de minutos previos. Estos diagnósticos no certifican calibración completa por jugador, rol, equipo o contexto.

## Probabilidades y controles

Cada PMF tiene masa no negativa, suma uno y soporte elegido con información del pronóstico, sin usar el resultado actual. Se comprueba la cola antes de normalizar: tolerancia **1e−10**, cola omitida máxima observada **4,646e−14**. Para una línea entera, push es la masa de ese conteo; para una media línea es cero. Under/push/over conservan masa y las probabilidades over son monótonas al subir la línea.

Son categorías matemáticas condicionales a la población estudiada: `void_probability=None` y contrato real no verificado. Ninguna distribución se convierte en liquidación, cuota justa comercial, EV, CLV o ROI. Las reglas pendientes de las casas y los tickets originales siguen siendo entradas necesarias para esa otra evaluación.

**265 pruebas NBA**, incluidas 31 nuevas sobre identidad, fecha, OT, contaminación de entrenamiento, momentos Poisson/NB, límites de dispersión, colas, PIT, categorías y serialización. Arnés general **768 pruebas / 10 omisiones** antes y después de la corrección final; Docker no disponible. Los logs iniciales de 264 pruebas y el fallo anterior se preservan y no sustituyen la validación final.

La revisión comprueba las 51 corridas y 19.819 evidencias anteriores, los protocolos 105–108, los 98.644 historiales y la elección de validación. Revisa **179.448 PMFs** y calcula sus CRPS con una fórmula independiente; regenera 27 distribuciones representativas y reproduce los resúmenes por fecha/temporada/bloque. Fuentes, resultados, pruebas y versiones quedan enlazados por hashes. Revisión propia, sin revisor independiente ni anclaje externo.

Cero llamadas a proveedores, compras o nuevas parejas de cuotas. Cota ZenRows **2.232/3.200** preservada; recepción original, contratos, liquidaciones reales y gates sin cambios. No se modifica el pronosticador existente de producción.

## Continuación F6

`F6_research_handoff.json` conserva las rutas/hashes del protocolo, ajuste, elección, features, resultados y pronósticos, con estado listo para auditoría temporal de investigación y producción deshabilitada.

Sigue revisar cortes por fuente, revisiones y faltantes; probar fugas y cambios de rol/equipo; fijar un bloque futuro de confirmación que todavía no se haya observado. La captura prospectiva debe guardar recepción UTC real y un anclaje externo, sin retrofechar archivos. Disponibilidad, titularidad, restricciones médicas, ritmo/oponente, oportunidades y etiquetas de OT siguen pendientes para una distribución prepartido completa. F5 continúa en curso y sus diagnósticos no aprueban G5.

Carpeta canónica: `apps/nba/.local/normalized/nba_f5_run52_v2_20261007/`. Código de investigación: `apps/nba/src/nba/rebound_distributions.py`. Validación: `verification.json`; cierre: `checkpoint.json`; registro: `docs/nba_plan_fases_auditoria.json`.
