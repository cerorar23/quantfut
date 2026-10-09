# Plan maestro NBA: fases, evidencia y auditoría

**Versión:** 1.1 · **Actualización:** 4 de octubre de 2026 · **Estado:** plan actualizado; implementación pendiente.

**Objetivo:** construir un sistema independiente de pronóstico NBA que estime distribuciones calibradas de minutos, puntos, rebotes y asistencias, cuantifique incertidumbre, permita reproducir sus resultados y entregue alertas estadísticas trazables por Telegram. Evaluar por separado calidad predictiva, comparación con precios observados y utilidad económica del producto. El valor esperado estimado depende de probabilidades y contratos válidos; acierto, CLV o fecha de lanzamiento no certifican rentabilidad.

Este documento consolida las decisiones de la conversación y dirige el orden de implementación. Las tres revisiones anteriores conservan su función de referencias: [investigación y 27 experimentos](nba_2026_27_investigacion_y_plan.md), [aislamiento de fútbol](nba_arquitectura_aislada.md) y [MVP y capacidad](nba_mvp_ejecucion_y_capacidad.md). Si el alcance inicial de una revisión anterior difiere, prevalece el MVP definido aquí; los cambios posteriores deben registrarse y versionarse.

El [registro estructurado](nba_plan_fases_auditoria.json) contiene fases, tareas, dependencias, experimentos y hashes del plan vigente y de su historial. La [versión 1.0](nba_plan_fases_auditable_v1_0.md) y el [registro previo a esta revisión](nba_plan_fases_auditoria_v1_0_pre_v1_1.json) se conservan íntegros. No hay ejecuciones ni puertas aprobadas.

La versión 1.1 integra el [arranque de pretemporada](nba_pretemporada_arranque.md) y la [revisión crítica de CLV, fuentes y QNN](nba_revision_critica_clv_fuentes.md). Estos documentos conservan su explicación detallada; las tareas y criterios operativos actualizados están incorporados aquí.

## 1. Estado real y límites del alcance

| Elemento | Estado comprobado al elaborar el plan |
|---|---|
| Investigación, arquitectura y revisión del MVP | Documentadas, con fuentes y límites de lectura |
| Aplicación `apps/nba/` | No existe todavía |
| Base de datos, modelos y workers NBA | No implementados |
| Captura prospectiva NBA y experimentos E0–E26 | No ejecutados por este trabajo |
| Telegram NBA | Diseñado; no configurado ni activado |
| Rentabilidad propia NBA | No demostrada |

**Alcance inicial:** una familia de estadísticas individuales prepartido, elegida por cobertura antes de evaluar resultados. Rebotes es un candidato provisional; asistencias o puntos pueden sustituirlo mediante una decisión registrada en F2. Empezar con 2–3 operadores accesibles y reglas verificadas. Ampliar familias, periodos y live solo después de auditar el núcleo.

**Automatización incluida:** captura, validación, cálculo de pronósticos, simulación, auditoría y notificaciones. La colocación de apuestas y la gestión de cuentas/fondos quedan fuera del sistema. Las observaciones de ejecución que alguien informe se usan como datos de evaluación, sin operar su cuenta.

**Reglas de diseño:** fútbol y NBA independientes; publicación apagada durante preparación; ninguna captura de pago sin presupuesto NBA definido; credenciales ausentes generan abstención/error explícito. Conservar el orden **predecir → registrar/sellar → revalidar → notificar** y las revisiones como eventos adicionales.

## 2. Mapa de fases y dependencias

| Fase | Resultado | Dependencia | Duración orientativa, sin garantía |
|---|---|---|---|
| **F0** | Alcance y protocolo de evaluación definidos | Ninguna | 1–2 días de trabajo |
| **F1** | Aplicación y operación aisladas | F0 | 2–4 días |
| **F2** | Fuentes, contratos, cobertura y coste auditados | F0; puede avanzar con F1 | 2–4 días |
| **F3** | Ingesta versionada y consultas point-in-time | F1 y F2 | 4–7 días |
| **F4** | Baselines y distribución de minutos | F3 | 3–6 días |
| **F5** | Distribución de estadística y calibración offline | F4 | 4–8 días |
| **F6** | Entrega de pruebas y medición de disponibilidad | F5 | 3–6 días más observación |
| **F7** | Validación prospectiva de un candidato congelado | F6 | Piso propuesto de 60 días; muestra puede exigir más |
| **F8** | Challengers de lesiones, rol y oportunidades | F6 y datos adecuados; separado del candidato F7 | 2–4 semanas por paquete, condicionado a datos |
| **F9** | Operación evaluada y extensiones selectivas | F7; cada extensión tiene validación propia | Continua; sin fecha de beneficio prometida |

Los tiempos de trabajo no incluyen contratación, bloqueos de acceso, correcciones de datos ni espera de muestra. No sumarlos como fecha contractual. La captura puede operar mientras se construyen modelos; un candidato que continúa en F7 no cambia por incorporar F8.

```mermaid
flowchart LR
  F0[F0 Alcance y protocolo] --> F1[F1 Aislamiento]
  F0 --> F2[F2 Cobertura y contratos]
  F1 --> F3[F3 Ingesta y PIT]
  F2 --> F3
  F3 --> F4[F4 Minutos]
  F4 --> F5[F5 Distribución y calibración]
  F5 --> F6[F6 Entrega de pruebas]
  F6 --> F7[F7 Validación prospectiva]
  F6 --> F8[F8 Challengers de contexto]
  F7 --> F9[F9 Operación y ampliaciones]
  F8 -. nueva versión y bloque de prueba .-> F7
```

## 3. Cómo se audita una fase

Cada fase tiene tareas, entregables y una puerta `G0`–`G9`. Su cierre exige un acta con evidencia real. Estados permitidos: `planned`, `in_progress`, `ready_for_review`, `passed`, `failed` y `deferred`. El documento guardado no cambia automáticamente una fase a `passed`.

**Ficha mínima de ejecución:** `run_id`, fase/experimento, responsable y revisor o declaración de autorrevisión, fecha UTC, commit y estado de cambios locales, hashes de fuentes/configuración/modelo, corte temporal, rango de datos, semilla, comando/versión de entorno, supuestos, métricas e intervalos, fallos/faltantes, resultado y motivo. No guardar secretos en logs o manifiestos.

**Ficha de puerta:** versión del criterio fijada antes del test, evidencias referenciadas, resultado de cada criterio, incidencias abiertas, decisión, alcance exacto autorizado y responsable de revisión. Un resultado fallido permanece en el historial. Una modificación del protocolo crea una versión nueva y un nuevo bloque de confirmación.

**Evidencia futura**, todavía no generada:

```text
audits/nba/<run_id>/
  manifest.json           identidad de la ejecución y hashes
  protocol.json           hipótesis, métricas, cortes y criterios previos
  metrics.json            resultados y cobertura
  report.md               interpretación y límites
  gate.json               decisión y evidencias
  artifacts/              tablas/figuras salidas de esa ejecución
```

Raw, modelos y datos personales irán a almacenamiento propio con retención y acceso definidos; el manifiesto los referencia por ID/hash. Nunca añadir credenciales o payloads privados al Git público.

Un hash permite comprobar integridad, pero no demuestra por sí solo origen auténtico o existencia antes del partido. Las predicciones prospectivas requieren hora de recepción, sellado previo y un anclaje verificable fuera del archivo editable; definir su mecanismo en F3. Un replay retrospectivo se etiqueta como tal aunque esté sellado.

## 4. F0 — Alcance, decisiones y protocolo

**Responsabilidad:** producto y revisión metodológica. **Entrada:** documentos existentes.

- **F0.1:** definir usuarios, mercados candidatos, horarios y salidas: distribución calibrada, estimación central, intervalos e información de calidad. Registrar que el primer mercado se decide por cobertura; separar calidad predictiva, diagnóstico de precios y utilidad económica.
- **F0.2:** definir las decisiones pendientes: proveedores/operadores, presupuesto mensual NBA, retención, canal de pruebas y responsable de revisión. Usar acceso local o gratuito mientras no se resuelvan los recursos de pago.
- **F0.3:** preparar protocolo: universo, cortes temporales, baselines, métrica predictiva primaria, mejoras mínimas, tratamiento de faltantes, calendario de lectura y tamaño de muestra. CLV es métrica complementaria de mercado; pretemporada, regular y playoffs tienen resultados separados. Congelar referencia de cierre, reglas de comparabilidad y sensibilidad antes de evaluar CLV.

**Entregables:** alcance versionado, inventario de decisiones, protocolo preliminar y registro de riesgos.

**G0:** objetivos medibles y alcance explícito; decisiones sin resolver identificadas, con efecto concreto. Se puede continuar diseño local; ninguna decisión pendiente se interpreta como presupuesto o destino de mensajes autorizado.

**Relación probabilidades/precio:** para dos resultados exhaustivos sin push/void, cuota decimal `d` y probabilidad `p`, el beneficio esperado por unidad es `p*d - 1`. En el caso general es `p_win*(d-1)-p_loss`, con reglas y probabilidades de push/void explicitadas. Son estimaciones bajo el modelo; no rentabilidad demostrada ni instrucciones de operación de cuentas. No reemplazar probabilidades calibradas por maximizar acierto bruto o movimiento de cuotas.

## 5. F1 — Aislamiento técnico y recuperación

**Responsabilidad:** ingeniería. **Entrada:** F0.

- **F1.1:** preparar `apps/nba/` con `domain/`, `ingest/`, `model/`, `eval/`, `publish/` y API de lectura si hace falta; dependencias y entorno propios. Prohibir imports cruzados `nba`/`qf`.
- **F1.2:** imagen y proyecto Compose propios, Postgres `quantnba` y Redis propio cuando se necesite; volúmenes, redes, secretos y artefactos separados. Roles de runtime sin privilegios de migración.
- **F1.3:** configuración `NBA_*` explícita; sin cargar `.env` de fútbol o usar sus DSN/tokens. Captura pagada y publicación deshabilitadas al inicio.
- **F1.4:** probar aislamiento, límites de recursos y backup/restauración en entorno de pruebas. Registrar que un VPS, disco o cuenta de proveedor compartidos mantienen puntos comunes de fallo.

**Entregables:** build reproducible, mapa de recursos/permisos, informe de aislamiento y recuperación.

**G1:** runtime NBA no importa ni accede a recursos de fútbol; restore y migraciones actúan sobre recursos NBA; caída de un worker NBA no detiene los procesos de fútbol en el ensayo. Límites de capacidad medidos antes de instalar servicios en el host compartido.

**Prerrequisito local antes de escribir código:** ejecutar y resolver el arnés obligatorio del repositorio. La revisión previa encontró que Bash no ejecutó pruebas y que la venv apunta a un intérprete ausente; no tomar aquel `OK` como prueba pasada. Esta tarea documental no implementa esa reparación.

## 6. F2 — Fuentes, contratos y presupuesto

**Responsabilidad:** datos y revisión de producto. **Entrada:** F0. **Experimento:** E0.

- **F2.1:** matriz proveedor × temporada × tipo de temporada × dato × mercado × operador; identidad del jugador, pares de cuotas, histórico, publicación/recepción, revisiones y cobertura. Añadir frescura, disponibilidad, posible feed compartido, duplicación y resolución observada por mercado. Sharp/soft solo son etiquetas provisionales; no garantizan calidad ni retraso de una prop.
- **F2.2:** catálogo versionado de contratos: estadística, periodo, línea, lado, participación, prórroga, push, void, abandono y fuente de liquidación. Promociones/bonos son pagos distintos del efectivo.
- **F2.3:** comprobar ámbitos reales de cuota API, presupuesto y límites; registrar cabeceras de consumo. Reservar fútbol por separado. No asumir que otra key crea otra cuota.
- **F2.4:** escoger y congelar familia inicial/operadores antes de analizar su rendimiento; registrar huecos y criterio de cambio. Definir benchmark de cierre por familia, reglas comunes, política de último precio fresco anterior al inicio real, método de margen y tratamiento de cierre ausente o cambio de línea. No asumir que una marca es referencia válida para todos los contratos.

**Entregables:** matriz de cobertura, diccionario de contratos/reglas, mapa de identidades y presupuesto propuesto.

**G2:** hay cobertura suficiente para el universo acotado, reglas verificables y datos cuya frescura se puede medir. Si no, reducir universo o cambiar fuente y documentarlo; los contratos ambiguos se excluyen.

Para evaluación contra mercado, G2 exige identidad y reglas comparables y una referencia preregistrada. Si falta cierre compatible, el pronóstico deportivo puede estudiarse pero su CLV queda ausente/incomparable. No reconstruir automáticamente cobertura de cuotas desde cobertura deportiva.

Escenario de coste ilustrativo: 3 partidos/día × 6 cortes × 1 mercado × 30 días × 1 región equivalente = **540 créditos/mes**, bajo esos supuestos y sin auxiliares/reintentos. Es cálculo de alcance, no autorización. Validar contra consumo real. La cadencia publicada de props/periodos es 60 s; capturar más rápido no garantiza observaciones nuevas. [Proveedor](https://the-odds-api.com/sports-odds-data/update-intervals.html), [costes y endpoints](https://the-odds-api.com/liveapi/guides/v4/).

## 7. F3 — Ingesta, identidad y datos point-in-time

**Responsabilidad:** ingeniería de datos. **Entrada:** F1 y F2. **Experimento transversal:** E18.

- **F3.1:** archivo raw versionado y captura reanudable de calendario/rosters, box scores, PBP, lesiones/noticias y cuotas. Priorizar histórico deportivo 2023-24–2025-26 y captura de pretemporada actual; ampliar a 2021-22 según cobertura. PBP/tracking, noticias históricas y cuotas tienen inventarios de acceso propios; ninguno se declara completo sin evidencia.
- **F3.2:** normalización por IDs con namespace, vigencia de equipo/rol, versiones de corrección y cuarentena de eventos sin identidad o contrato fiable.
- **F3.3:** construir consultas as-of y validadores PIT; nunca usar una publicación descubierta después como si ya se conociera. Conservar hora del evento, publicación si existe, primera recepción UTC, registro, revisiones y precisión/offset del reloj. Usar reloj monotónico para duraciones locales; resolución del timestamp no demuestra instante exacto de un ajuste externo.
- **F3.4:** pruebas de reconciliación, deduplicación, revisión de PBP y reproducción del mismo corte; anclaje y ledger de decisiones prospectivas.

**Entidades propuestas:** partidos, jugadores/rosters, versiones box score/PBP, quintetos/stints, disponibilidad, contratos/cuotas, capturas, features, predicciones, decisiones de sombra, alertas/intentos y versiones de resultado. Todas dentro de persistencia NBA.

Guardar `season_id` y `season_type` (`preseason`, `regular_season`, `playoffs`) en datos, manifiestos, predicciones y métricas. Publicación, primera recepción, revisiones, reloj/frescura y linaje del feed se conservan como información distinta. Los cierres sirven para evaluar posteriormente y no pueden incorporarse a features de un pronóstico previo.

**G3:** no hay violaciones PIT o identidades ambiguas dentro del conjunto aceptado; cuarentena y cobertura informadas. Reconciliar cinco jugadores por lado cuando sea verificable, 240 minutos-equipo en regulación y 25 por prórroga, marcador/periodos y `PTS = 2·2PM + 3·3PM + FTM`. Declarar tolerancia de redondeo antes de auditar. Rebote de equipo se distingue del individual.

Raw descargado hoy no reconstruye automáticamente noticias/revisiones históricas. `last_update` del mercado no identifica el segundo exacto de cada cambio de jugador. Una pausa/falta de datos se conserva; no crear un estado en vivo artificial.

## 8. F4 — Baselines y distribución de minutos

**Responsabilidad:** modelado estadístico. **Entrada:** F3. **Experimento:** E1.

- **F4.1:** baselines de media reciente y distribución por rol; evaluación por jugador/contexto con splits temporales.
- **F4.2:** modelo jerárquico de minutos con disponibilidad, titularidad, entrenador, rotación conocida, carga y límites verificados. Encogimiento para novatos, cambios de equipo y muestra escasa. Separar disponibilidad, minutos, USG% y oportunidades; USG% no es una proyección de minutos ni de oportunidades de rebote/asistencia.
- **F4.3:** escenarios activo/DNP, competitivo/paliza, faltas y restricción de minutos; reportar incertidumbre y coherencia de minutos-equipo.

**Entregables:** pronósticos de minutos guardados por corte, comparación de baselines, cobertura de intervalos, errores por estrato y model card.

**G4:** salida reproducible, restricciones deportivas coherentes y evaluación posterior al entrenamiento. Si el candidato no mejora el baseline, conservar baseline y registrar fallo; se puede investigar F5, pero no presentar una mejora inexistente.

Minutos reales del partido son resultado, no feature. Pretemporada tiene indicador y tratamiento separado; no fijar rotaciones regulares por una muestra de exhibición. Una línea de prop no identifica minutos implícitos únicos.

Con pretemporadas históricas comparables, contrastar variantes con/sin sus señales usando cortes temporales previos. Elegir peso/variables en train/validación, no con el test futuro. Si falta ese histórico, usar observaciones para escenarios explícitos sin afirmar mejora. Las pruebas de pretemporada no acreditan generalización a regular.

## 9. F5 — Distribución de la estadística y calibración

**Responsabilidad:** modelado y revisión metodológica. **Entrada:** F4. **Experimentos:** E8 básico, E21 si corresponde, E22/E23 básicos.

- **F5.1:** tasa productiva jerárquica por minuto/posesión y contexto. Integrar escenarios de minutos y ritmo en la distribución final; comparar Poisson/binomial negativa según ajuste, sin asumir que más complejidad mejora.
- **F5.2:** extender a puntos mediante volumen de tiros y acierto si esa es la familia elegida. Rebotes/asistencias con oportunidades verificadas son challenger, no dato inventado desde el box score.
- **F5.3:** obtener distribución coherente y probabilidades de categorías del contrato, con masa de push/void diferenciada. Validar monotonicidad entre líneas, sumas y error numérico.
- **F5.4:** calibrar y combinar modelos/mercado solo con predicciones temporales fuera de muestra y precios disponibles al corte. Conservar CRPS/log-score y Brier/log-loss según objetivo; CLV posterior no sustituye esas métricas ni entra en calibración previa. Definir abstención por faltantes, incertidumbre o contexto sin soporte. SBC verifica inferencia bajo un generador supuesto si se usan samplers bayesianos.

**Baselines:** media/tasa simple, minutos + tasa encogida y referencia contemporánea de mercado con supuestos explícitos. Dos cuotas de una línea no identifican toda la distribución ni la probabilidad de push.

**Entregables:** candidato congelable, model card, protocolo final de métricas, resultados fuera de muestra y tabla de errores/abstenciones.

**G5:** distribución válida, cálculo verificable y protocolo listo para confirmación. Registrar si mejora o no al baseline. Ajustar candidatos únicamente en train/validación, nunca con el test final. El candidato técnicamente válido puede ir a sombra aunque su ventaja económica siga sin demostrar.

La incertidumbre predictiva no equivale a confianza de un parámetro, y cobertura conformal no equivale a probabilidad de cobrar. Conservar la variabilidad irreducible del resultado; evitar etiquetas como «95% seguro».

## 10. F6 — Alertas de pruebas y disponibilidad observada

**Responsabilidad:** ingeniería de entrega y evaluación. **Entrada:** F5. **Experimentos:** E5, E17/E19 básicos.

- **F6.1:** ledger propio y outbox durable en Postgres; decisión/sellado previo a salida, intentos, caducidad, deduplicación y correcciones adicionales. Redis no sustituye evidencia durable.
- **F6.2:** canal de pruebas NBA, destinatarios explícitos y mensajes etiquetados como experimentales; configurar credenciales mediante mecanismo privado, sin logs de tokens.
- **F6.3:** registrar recepción/cálculo/sellado/envío/acuse, p50/p95, errores y antigüedad de inputs. Revalidar identidad/estado antes de notificar; omitir datos caducados.
- **F6.4:** replay de demoras, duplicados, revisiones, suspensiones, 429, timeout e incertidumbre de envío. Medir disponibilidad de precios del mismo contrato por operador con la resolución real. E17 compara liderazgo por mercado y linaje/duplicación del feed; separar cambio externo, actualización del proveedor y recepción propia. Los cambios entre snapshots se reportan como intervalos censurados.

**Entregables:** pruebas de transporte/reinicio, ledger de alertas, informe de latencia y disponibilidad.

**G6:** todas las notificaciones del ensayo tienen predicción sellada previa, contrato/versión correctos y caducidad; no hay reintentos ciegos tras estado incierto. El objetivo propuesto de p95 <2 s entre sellado y acuse es técnico y debe medirse; no implica llegada al dispositivo ni disponibilidad de cuota.

Comparar demoras de 0/15/30/60/120 s y 5 min solo donde la resolución lo permita. Con snapshots de 60 s, reportar intervalos o primera observación posterior; no afirmar duración exacta de 45 s. El rango USD 20–250 y las ventanas de 5–30 s o 2–5 min siguen sin demostración propia.

## 11. F7 — Validación prospectiva y puerta de promoción

**Responsabilidad:** evaluación y revisión de producto. **Entrada:** F6. **Experimentos:** E26 y confirmación de E1/E22/E23; E18/E5 continúan.

- **F7.1:** congelar candidato, configuración, universo y criterios antes del bloque prospectivo; todas las predicciones y exclusiones se registran antes del resultado.
- **F7.2:** lecturas programadas, métricas e intervalos por bloques de partidos/días; conservar agrupación y dependencia por jugador. Comparar sobre el mismo universo.
- **F7.3:** informe de calibración, mejora predictiva, incertidumbre, disponibilidad, CLV comparable, costes y análisis económico retrospectivo/simulado, identificado por tipo de evidencia. Reportar cobertura del cierre y sensibilidad a referencias/margen; conservar ausentes e incomparables. Separar regular de pretemporada, precio observado de precio informado como aceptado y CLV bruto de diagnóstico ajustado.
- **F7.4:** revisión documentada: mantener en investigación, reformular o promover el alcance específico respaldado. Un nuevo modelo reinicia su confirmación en datos nuevos.

**Piso de investigación propuesto:** 300 partidos distintos con observaciones pertinentes, 60 días y tres bloques cronológicos. No es autorización ni tamaño suficiente por definición. La familia/operador necesita su propia cobertura; snapshots y múltiples jugadores del mismo partido no son observaciones independientes.

**G7 científico:** criterio predefinido de mejora y calibración satisfecho, sin fugas, con estabilidad y concentración de errores informadas. Separar calidad deportiva de conclusiones sobre cuotas. Resultado inconcluso significa continuar evidencia o reformular; no «pasar por falta de tiempo».

CLV favorable no aprueba G7 por sí solo ni un pronóstico individual correcto demuestra calibración. La puerta para regular se evalúa en datos regulares pertinentes; métricas de pretemporada informan un alcance separado. Cualquier análisis con cierre incompleto declara cobertura y sus posibles sesgos.

**G7 comercial:** además, utilidad verificable del producto para su público, disponibilidad con demoras observadas, cobertura/muestra adecuada y comunicación fiel a la evidencia. Retorno de simulación, benchmark de cierre y ejecuciones que alguien informe voluntariamente son series separadas, no una sola curva de rentabilidad real. Las puertas de fútbol no se alteran.

## 12. F8 — Lesiones, rol y oportunidades

**Responsabilidad:** modelado y datos. **Entrada:** núcleo F6 y datos de contexto suficientes. **Experimentos:** E2/E3/E7/E8 completo/E9/E13.

- **F8.1:** archivar y evaluar noticias capturadas oportunamente; escenarios de baja/retorno precalculados y versión congelada sin noticias como control. E7 compara reacción ante anuncios para contratos/fuentes definidos previamente: movimientos, suspensiones, revisiones, ausentes y tiempos intervalados. No convertir desfases del proveedor en retrasos demostrados de la casa ni asumir beneficiarios rentables.
- **F8.2:** ablación de cuatro brazos: baseline, solo minutos, solo tasa/rol y ambos. Analizar sustituto directo y compañeros secundarios definidos antes del resultado. Separar disponibilidad/minutos de USG% y oportunidades; una baja no redistribuye esas magnitudes de forma idéntica.
- **F8.3:** oportunidades compartidas de rebote/asistencia y regímenes competitivos/paliza, con coherencia conjunta y evaluación de la estadística completa.

**Entregables:** estudios de anuncios, ablaciones, resultado de cada challenger y registro de variantes negativas.

**G8:** mejora adicional replicable y mecanismo documentado con variables disponibles al corte. No atribuir causalidad automática al on/off ni asumir que un suplente hereda todo el uso. Una variante candidata vuelve a F7 con nueva versión y bloque de prueba; no modifica el candidato que ya está bajo confirmación.

## 13. F9 — Operación evaluada y ampliaciones

**Responsabilidad:** operación, revisión estadística y producto. **Entrada:** F7 para el alcance que se pretenda distribuir; evidencia adicional por extensión.

- **F9.1:** definir publicación estadística, model card y dashboard con cobertura, estados de versión, métricas, incidentes y caducidad. Mantener avisos experimentales donde la evidencia no alcance.
- **F9.2:** seguimiento de deriva, rendimiento por estrato, disponibilidad, costes y recuperación. Alertas internas cuando cambian datos/modelo/entrega; suspensión de salidas afectadas y restauración de la versión previamente validada si procede.
- **F9.3:** evaluar capacidad y utilidad comercial: muestras voluntarias y sesgo, cuota/stake ya aceptados si se informan, faltantes y coste de suscripción. No fijar 100 plazas desde un replay ni confundir acuse Telegram con apuesta.
- **F9.4:** priorizar periodos y live en descansos solo con PBP/quintetos/reloj sincronizados; después boosting, modelos espaciales, interacciones y conformal como challengers. Cada extensión vuelve a validación propia.

**G9:** alcance divulgado corresponde a evidencia, recursos y recuperación probados. Una regresión no se oculta; se registra incidente y se limita el componente afectado. Una extensión nunca hereda certificación de otra familia o periodo.

Kelly/optimización de cartera y experimentos cuánticos se conservan como investigación matemática offline. No generan instrucciones de colocación de apuestas o administración de fondos dentro del producto.

E20 exige mismos datos, cortes y presupuesto de ajuste que baselines clásicos competitivos, con coste completo de codificación, simulación/hardware y ejecución. QNN no garantiza evitar problemas de optimización ni acelerar este problema NBA. NGBoost tampoco recibe ventaja por su nombre: requiere su propia comparación temporal. E18 es el control PIT transversal; no existe fase F18.

## 14. Matriz completa de los 27 experimentos

| ID | Hipótesis / objeto | Fase principal | Alcance inicial |
|---|---|---|---|
| E0 | Cobertura, contratos y calidad de captura | F2 | MVP |
| E1 | Minutos y rotaciones frente a baseline | F4 | MVP |
| E2 | Disponibilidad/lesiones | F8 | Posterior al núcleo |
| E3 | Oportunidades de producción | F8 | Según cobertura |
| E4 | Modelado de periodos | F9 | Extensión |
| E5 | Demora y disponibilidad tras alerta | F6 | MVP y continuo |
| E6 | Modelos modernos comparables | F9 | Challenger; baselines simples en F5 |
| E7 | Información adicional tras noticias y desfases por contrato/fuente | F8 | Después del núcleo; tiempos censurados según feed |
| E8 | Minutos frente a tasa/rol | F5 | Básico; ablación completa en F8 |
| E9 | Regímenes competitivo/paliza | F8 | Escenario básico en F4; comparación formal posterior |
| E10 | Volumen/calidad espacial de tiro | F9 | Requiere datos |
| E11 | Rachas y sesgo de selección | F9 | Exploratorio |
| E12 | Rotaciones Q1/H1 | F9 | Extensión de periodos |
| E13 | Competencia por oportunidades | F8 | Challenger conjunto |
| E14 | Faltas y sustituciones | F9 | Requiere PBP fiable |
| E15 | Hypergraph/interacciones de quintetos | F9 | Diferido |
| E16 | Viaje, descanso y carga | F9 | Ablaciones posteriores |
| E17 | Liderazgo por mercado/duplicación y linaje de feeds | F6 | Básico; profundización posterior |
| E18 | PIT, fugas y controles negativos | F3 | Transversal a todas las fases |
| E19 | Resiliencia de entrega y observación | F6 | MVP; seguimiento continuo |
| E20 | Comparación clásica/cuántica | F9 | Exploración offline diferida |
| E21 | Cálculo bayesiano/SBC | F5 | Si el método de inferencia lo requiere |
| E22 | Combinación/calibración temporal | F5 | Básico imprescindible |
| E23 | Abstención y contextos sin soporte | F5 | Básico imprescindible |
| E24 | Conformal online/cambios de régimen | F9 | Con suficiente historial |
| E25 | Riesgo y cartera bajo modelos inciertos | F9 | Estudio offline; sin operación de cuentas |
| E26 | Réplica prospectiva y stress del modelo | F7 | Antes de promoción |

La matriz asigna responsabilidad primaria; E18, seguimiento de datos y auditoría continúan aunque su experimento principal haya terminado. No seleccionar retrospectivamente el experimento ganador entre 27 y presentarlo como prueba confirmatoria.

## 15. Métricas y criterios que se fijan antes del test

| Área | Métricas | Criterio auditable |
|---|---|---|
| Datos | Cobertura, faltantes, duplicados, reconciliación, antigüedad | Cero fugas/identidades ambiguas en datos aceptados; resto en cuarentena y visible |
| Minutos | MAE, CRPS, cobertura/longitud de intervalos | Comparación temporal con mismo universo y mínimos de efecto/muestra preregistrados |
| Estadística | CRPS/log-score, Brier o log-loss del contrato | Elegir una métrica primaria según objetivo; distribución válida y calibración por contexto |
| Generalización | Diferencias por rol, jugador, operador y bloque | Reportar incertidumbre/concentración; muestras escasas no reciben certificación específica |
| Entrega | p50/p95, timeout/429, caducidad, estado incierto | Sellado previo, caducidad y estados reconciliados; p95 <2 s es meta técnica propuesta |
| Disponibilidad | Oferta observada por demora, censura, faltantes | Resolución explícita; no inferir aceptación ni límite de stake del feed |
| Mercado / CLV | Comparación bruta, diagnóstico ajustado por margen, cobertura del cierre y sensibilidad | Mismo contrato; benchmark/cierre fresco preregistrados; sin certificado de ventaja |
| Economía del producto | Costes, análisis simulado, utilidad tras tarifa | Supuestos y series separados; sin afirmaciones de ROI real basadas solo en simulación |

Para una pérdida, definir `d = pérdida_candidato − pérdida_baseline`; una mejora corresponde a `d < 0`. Fijar en validación el efecto mínimo relevante y criterio del intervalo, por ejemplo límite superior IC95 por bloques inferior a ese umbral negativo. Determinar potencia/tamaño antes de abrir test; no crear un umbral después del resultado. Considerar pruebas múltiples y revisiones repetidas.

El piso de 300 partidos no prueba una ventaja pequeña. El cálculo orientativo del documento de investigación muestra que detectar un retorno de 3% puede requerir miles de observaciones bajo supuestos favorables; dependencia y selección pueden aumentar el requisito. No traducir precisión de minutos o cobertura conformal a rentabilidad.

### 15.1. Protocolo obligatorio de CLV cuando exista cobertura

Definir referencia por familia antes del test; no elegir retrospectivamente la que dé mejor resultado. «Cierre» es el último precio compatible recibido antes del inicio real bajo una política de frescura previamente fijada. Conservar publicación/recepción y motivo si falta cierre. Suspensión o cambio de línea no autoriza imputar un precio favorable.

Para un mercado exhaustivo de dos resultados sin push/void, una convención de eliminación del margen es:

```text
p_close = (1/d_close_side) / (1/d_close_side + 1/d_close_opposite)
raw_price_change = d_observed / d_close_side - 1
closing_reference_value = d_observed * p_close - 1
```

La primera es una normalización asumida; la segunda compara precios sin ajustar margen; la tercera estima valor bajo la referencia de cierre. Ninguna identifica automáticamente la probabilidad verdadera o ROI real. Con push/void las dos cuotas no identifican las probabilidades incondicionales: usar una metodología validada que modele esos estados o declarar el diagnóstico no disponible.

Solo comparar el mismo contrato. Over 7.5 y Over 8.5 son resultados diferentes; sin precios de la misma línea o distribución de cierre validada, marcar incomparable. Reportar cobertura, faltantes, métodos, discrepancias entre referencias y concentración por partido/jugador/operador. No confundir cuota vista al emitir con cuota finalmente informada como aceptada.

Contraejemplo hipotético: 2.00 que después cierra en 1.80 da comparación bruta favorable; con probabilidad verdadera 0.45, el beneficio esperado a 2.00 sería -0.10 por unidad. El movimiento no demuestra éxito predictivo ni expectativa positiva. Calibración y pérdidas predictivas permanecen primarias en F5/F7.

### 15.2. Noticias y resolución de observación

E17/E7 deben preregistrar universo de noticias, contratos, fuentes y criterios de movimiento. Medir liderazgo observado por mercado y distinguir linaje compartido, retraso de publicación, feed, recepción y entrega. Los tiempos externos entre dos capturas se modelan como intervalos; timestamps locales precisos no crean conocimiento del segundo exacto del ajuste. No asignar etiquetas sharp/soft como propiedad permanente ni seleccionar solo anuncios con movimientos favorables.

## 16. Paquete de datos y reproducción de un pronóstico

Cada pronóstico debe poder reconstruirse con:

1. IDs estables de partido/jugador y contrato/contexto, si aplica.
2. Corte `as_of`, `season_id`/`season_type`, estado/periodo/reloj y referencias a versiones recibidas hasta ese momento; primera recepción, revisiones y precisión temporal auditables.
3. Modelo, entrenamiento y calibrador con hashes; features y configuración de inferencia.
4. Distribución/intervalos, error de aproximación, flags de calidad y motivo de abstención si lo hubo.
5. Registro/sellado y referencia al anclaje; notificaciones/intentos enlazados al pronóstico.
6. Resultado observado y versión de corrección, reglas de evaluación y métricas obtenidas.
La evaluación de mercado añade `forecast_id`, contrato, precio observado, par de cuotas de cierre, referencia, inicio real, política de frescura, método de margen, resolución de captura, estado comparable/ausente y motivo. Este paquete posterior se guarda separado de los inputs del pronóstico. Su cobertura puede ser menor que la cobertura deportiva.

La reconstrucción usa originales versionados. Una corrección del resultado agrega una nueva evaluación y conserva la anterior. Backtests con datos deportivos revisados se distinguen de captura prospectiva y pruebas de noticias con información recibida a tiempo.

## 17. Calendario, riesgos y decisiones inmediatas

La temporada regular está prevista para el **20 de octubre de 2026**; la apertura sirve como referencia de captura, no como puerta de ventas. [Calendario NBA consultado](https://www.nba.com/news/2026-27-nba-regular-season-schedule). Desde el 3 de octubre, intentar cerrar alcance/aislamiento/auditoría y captura mínima antes del inicio depende de acceso y capacidad técnica. Si un gate no pasa, el calendario se actualiza; no recortar auditoría para aparentar estar listo.

| Riesgo | Evidencia que lo detecta | Respuesta del plan |
|---|---|---|
| Preparación incompleta antes de apertura | Acceso real, cobertura, modelos y puertas pendientes | Captura de pretemporada e histórico reciente priorizados; prototipo experimental y calendario condicionado |
| Mezcla con fútbol | Imports, DSN, permisos y recursos | F1; aislamiento y ensayo de fallo |
| Datos futuros/revisados | Primera recepción y joins as-of | F3/E18; cuarentena y revisión |
| Confianza excesiva al inicio | Errores por novato/rol/entrenador | Priors encogidos, intervalos y abstención |
| Cuotas observadas obsoletas | Feed/recepción y resolución | F2/F6; disponibilidad incierta informada |
| Ventana secundaria inexistente | Universo completo de anuncios | F8; conservar fallos y cambiar hipótesis |
| Modelo complejo sin señal | Baselines y test congelado | F5/F7; resultado negativo, no promoción |
| Gasto o saturación | Contabilidad, límites y carga | F1/F2; detener captura afectada al alcanzar tope |
| Producto poco útil para clientes | Disponibilidad/costes/faltantes | F7/F9; reformular alcance o tarifa propuesta |

Decisiones para F0/F2: familia inicial definitiva, operadores accesibles, proveedor/histórico, presupuesto mensual separado, infraestructura disponible y canal de pruebas. Este plan deja esas entradas visibles y permite avanzar en tareas locales sin inventarlas. No solicita credenciales por chat ni activa compras o canales.

**Arranque de pretemporada:** priorizar captura actual y box scores/minutos recientes mientras se completa el histórico. Probar pronósticos cuando exista un baseline válido; sus errores y la entrega se auditan como experimentales. Peso de señales de exhibición requiere comparación histórica temporal. F7 para regular continúa durante la temporada; una fecha objetivo no rebaja sus criterios.

## 18. Fuentes y fundamento científico

Los fundamentos y límites completos están en el documento de investigación. Referencias clave para implementar y evaluar:

- [EPV de Cervone et al.](https://arxiv.org/abs/1408.0777): metodología de posesiones/tracking; no certificación de una estrategia NBA propia.
- [Tesis de Huang](https://escholarship.org/content/qt6ch8z986/qt6ch8z986_noSplash_03d0c9a86569ba32786e8fa0de1007fd.pdf?t=pfyxts): sustituciones y dinámica de quintetos.
- [NGBoost](https://proceedings.mlr.press/v119/duan20a.html), [SBC](https://arxiv.org/abs/1804.06788) y [calibración](https://arxiv.org/abs/1706.04599): candidatos y herramientas de verificación, sujetos a comparación temporal nueva.
- [Conformalized Quantile Regression](https://arxiv.org/abs/1905.03222), [conformal online](https://arxiv.org/abs/2402.01139) y [preprint 2026 de control de riesgo](https://arxiv.org/abs/2602.20151): líneas de incertidumbre, con supuestos por verificar; no promesa de acierto individual o beneficio.
- [The Odds API](https://the-odds-api.com/liveapi/guides/v4/) y [Telegram Bot API](https://core.telegram.org/bots/api): contratos técnicos y entrega; comprobar versiones/cobertura al implementar.
- [Gneiting y Raftery (2007)](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf): evaluación de probabilidades con scoring propio; CLV no sustituye pérdidas predictivas.
- [McClean et al. (2018)](https://www.nature.com/articles/s41467-018-07090-4) y [Bowles, Ahmed y Schuld (2024)](https://arxiv.org/abs/2403.07059): límites de entrenamiento y benchmarking QNN; sin demostración de ventaja NBA.

Las afirmaciones de casas que usan solo medias móviles, cuartos tasados siempre al 25%, límites universales y oportunidades garantizadas durante minutos no se incorporan como hechos. La evidencia deberá decidir cada hipótesis.

## 19. Checklist de cierre del plan

- [x] Alcance y estado actual diferenciados de implementación.
- [x] F0–F9 con dependencias, tareas, entregables y puertas.
- [x] Aislamiento de fútbol, PIT, sellado y Telegram incluidos.
- [x] Datos, modelos, calibración, incertidumbre y réplica definidos.
- [x] E0–E26 asignados sin exigir ejecutarlos todos para capturar.
- [x] Calendario condicionado y presupuestos pendientes visibles.
- [x] Registro estructurado creado; evidencias de ejecución vacías.
- [x] CLV complementario y protocolo de cierre/comparabilidad definidos.
- [x] Liderazgo por mercado, linaje y resolución temporal incorporados.
- [x] Pretemporada separada y minutos/USG/oportunidades diferenciados.
- [x] Versión anterior preservada y registro 1.1 sincronizado.
- [ ] Implementar las fases y emitir sus actas reales.

Cerrar este checklist documental no equivale a cerrar G0–G9. El siguiente trabajo es F0 y la preparación local de F1/F2, respetando el arnés del repositorio antes de tocar código.

## 20. Historial de la revision 1.1

- Version 1.0 y registro anterior conservados sin alterar sus bytes.
- F0/F5/F7 separan probabilidades calibradas, CLV y utilidad economica.
- F2/F7 definen cierre comparable, frescura, margen y cobertura; CLV no aprueba G7 por si solo.
- F3/F6/F8 exigen precision temporal declarada y liderazgo medido por mercado.
- F3/F4/F7 incorporan pretemporada, historico reciente y metricas separadas.
- F4/F8 distinguen minutos, uso y oportunidades; F9/E20 mantiene benchmarking sin ventaja presumida.
- Se mantienen 10 fases, 37 tareas y 27 experimentos; todas las ejecuciones siguen pendientes.
