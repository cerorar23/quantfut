# Parley v2: probabilidad calibrada y control de incertidumbre, sin supuesto +EV

Fecha: 2026-11-06. Entrega de diseño y pseudocódigo; NO modifica el motor activo,
el cron, modelos, base de datos ni publicaciones. El usuario admite implementación
o propuesta y solicita explícitamente pseudocódigo o código. Las casas mezcladas
están autorizadas. Las ganancias y la publicación de cuatro tickets no se garantizan.

Revisión del mismo día por instrucción del usuario: retirados el supuesto y todos
los filtros de valor esperado positivo, incluido el requisito de compensación
individual del 1%. Objetivo: probabilidad de cumplir la cuota, calibración y
control de incertidumbre. El retorno realizado se registra, sin exigir ni prometer
ventaja sobre las casas. Esta revisión sustituye la función objetivo anterior.

## Evidencia revisada

- `src/qf/publish/parley.py`: cinco bandas antiguas, 2–6 patas de cuota
  1.20–1.80, prioridad actual de probabilidad y reparto secuencial de partidos.
- `parley_datos.py`: candidatos exclusivamente de `matches` de fútbol;
  no existe aquí un adaptador de tenis. La FK de `parley_patas.match_id` apunta
  a esa tabla. La selección ocurre antes del sello diario.
- `scripts/crontab`: la línea ejecutable de `qf.publish.daily` es **09:00 UTC**
  (03:00 America/Mexico_City). El comentario que dice 13:00 UTC está desactualizado.
  Cuotas cada 10 min, AF a :20, sombra a :25; PropLine dispone de archivo horario.
  Son configuraciones locales, no comprobación del cron desplegado.
- Tenis: checkout `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis`.
  `tennis_engine.shadow` registra ventanas T−120/T−15 y exige reconciliación de hora,
  participantes y evidencia de estado; eso NO acredita pronósticos válidos para
  todos los eventos futuros a una hora diaria fija. Otro checkout,
  `C:/Users/huye/Documents/qf-tenis-rediseno/apps/tenis`, contiene el rediseño;
  no se debe confundir su modelo experimental con el productor publicado.
- `docs/auditoria_historial_mercados_20261105.md`: muestras prospectivas de tenis
  pequeñas, familias con 16–44 casos y observaciones dependientes entre mercados.
- `src/qf/model/calibration.py`: ya existe calibración coherente de intensidades
  de fútbol; no reemplazarla por calibradores marginales incompatibles.

### Comprobación descriptiva del histórico disponible

Tenis: `data/tennis/tennis_data_manual_processed/odds_matched.parquet`, 53,853
filas. Seleccionar partidos Completed, cuatro precios PSW/PSL/B365W/B365L válidos,
favorito elegido por mayor probabilidad Pinnacle sin margen proporcional,
cuota bet365 1.20–1.80; una observación por partido. Quedan 37,558 eventos únicos
entre 2015-01-04 y 2026-01-13. No se incluyen retiradas.

Fútbol: 48 CSV en `.local/fd_cache`; deduplicación por liga/fecha/local/visitante,
resultado H/D/A, PSH/PSD/PSA y B365H/B365D/B365A válidos; favorito por Pinnacle
sin margen proporcional y precio bet365 1.20–1.80. Quedan 6,866 partidos.

| Muestra | n | P media sin margen | Acierto | ROI a 1 unidad |
|---|---:|---:|---:|---:|
| Fútbol, favorito 1X2 | 6,866 | 63.16% | 64.39% | −3.03% |
| ATP, favorito ganador | 19,882 | 64.83% | 64.87% | −5.53% |
| WTA, favorito ganador | 17,676 | 64.59% | 64.88% | −5.34% |

No son datos nuevos fuera de muestra, probabilidades del motor vigente ni un
backtest del parley. Se eligió bet365 para tener una casa comparable y concreta;
esto no evalúa todavía la mejor oferta entre todas las casas. Faltan instantes
de recepción de esas cuotas para reconstruir la decisión diaria. No asignar una
hora artificial a las fechas ni usar el cierre para simular las 03:35.

## Horario recomendado y convergencia

**03:35 America/Mexico_City = 09:35 UTC**, como candidato operativo inicial,
después de la corrida de fútbol de las 03:00 y la ingestión AF de :20 cuando aplique.
No es un óptimo estadístico demostrado: faltan latencias y cobertura intradía de
los dos productores. Tampoco garantiza incluir tenis de Asia ya empezado.

La garantía debe ser una barrera de disponibilidad, no el reloj:

```python
def ready_to_build(now, football_receipt, tennis_receipt, odds_receipt, artifact):
    # Recibos íntegros; job_id y versión de cada productor, no solo HTTP 200.
    require(all(r.status == "complete" and r.finished_at <= now
                for r in (football_receipt, tennis_receipt, odds_receipt)))
    require(artifact.approved_at <= now < artifact.expires_at)
    # Frescura por evento/contrato; capturarlo hoy no acredita una oferta vigente.
    require(all_selected_contracts_have_received_odds_before(now))
    require(all_selected_forecasts_have_pit_provenance_before(now))
    return True
```

Ventana de candidatos: [decisión + 30 min, decisión + 24 h), identidad inequívoca,
estado programado, horario suficientemente confirmado, cuotas prepartido no
suspendidas, antigüedad máxima inicial de 75 min para archivo horario y
`forecast.valid_until > decisión`. No inferir la vigencia del pronóstico por un
TTL inventado. Valores de 30/75 min son política inicial, no óptimos medidos.

Si a las 03:35 la barrera falla, reintentar cada 5 min hasta las 04:00; registrar
`waiting_sources` o `insufficient_valid_events`, sin sustituir datos faltantes.
No volver a sellar ni recalcular tickets ya publicados. Para decidir el horario
definitivo, archivar durante 30 días cobertura elegible, retraso p95/p99, primera
salida elegible y exclusiones por inicio para ventanas de 15 min entre 02:00 y
06:00; seleccionar por cobertura/frescura en validación, confirmar prospectivamente.

IMPORTANTE: el lote de las 03:00 ya sellado rechaza nuevas selecciones. Un job
de las 03:35 necesita un lote propio versionado de parley, con su cadena y orden
predecir → seleccionar → sellar → publicar, o reestructurar expresamente el
sellado diario. No basta añadir una línea de cron al `_parley()` actual.

## Política de targets

Mantener inicialmente el rango de pata 1.20–1.80 y máximo seis patas; cambiarlo
sería otra estrategia. Cuatro tickets, uno por target, si el conjunto es factible
con todas las restricciones. Tolerancia inicial ±2%, congelada antes de validar:

| ID | Target | Banda inclusiva | Mínimo estructural de patas |
|---|---:|---:|---:|
| 1 | 2.10 | 2.058–2.142 | 2 |
| 2 | 3.10 | 3.038–3.162 | 2 |
| 3 | 8.20 | 8.036–8.364 | 4 |
| 4 | 12.10 | 11.858–12.342 | 5 |

Se necesitan al menos 13 eventos distintos si se conserva la exclusividad diaria;
13 por sí solos no garantizan factibilidad por precios, calidad o disponibilidad.
No duplicar tickets ni ensanchar bandas para completar cuatro.

Por cada contrato exacto (deporte/evento/mercado/periodo/línea/lado/regla de
liquidación), elegir la mayor cuota elegible entre TODAS las casas admitidas por
el adaptador. No exigir misma casa; tampoco aceptar ofertas suspendidas, lay,
boosts personales, identidades ambiguas o reglas de retirada incompatibles.
No agrupar selecciones distintas solo porque el texto comercial sea similar.

## Matemática y función objetivo revisadas

Para patas binarias sin devolución y eventos aproximadamente independientes:

    log(Q) = Σ log(q_i)
    log(P) = Σ log(p_i_calibrada)

La cuota determina la factibilidad; la probabilidad determina la selección. No
se exige p*q > 1 ni retorno esperado positivo por pata o ticket. No se conserva
la compensación del 1% ni `lambda_extra = log(1.01)`.

Menos patas es una preferencia de simplicidad y menor exposición a errores, no
una prueba de mayor acierto a cuota fija. Una combinación de seis favoritos
puede superar a otra de cinco; añadir una pata al ticket intacto, en cambio,
siempre reduce la probabilidad de acertarlas todas si esa probabilidad es <1.
Se comparan tickets completos dentro de la misma banda de cuota.

Política principal B0, respetando la prioridad original de minimizar patas:
1. Maximizar cantidad de targets cubiertos, hasta cuatro, con calidad válida.
2. Minimizar patas totales del conjunto de cuatro tickets.
3. Entre empates, maximizar suma de probabilidades prudentes de cumplir el target
   de cada ticket: aproxima la cantidad esperada de aciertos diarios.
4. Desempatar por cercanía a targets y un identificador estable.

Política candidata B1, solo investigación: permitir más patas si la política
completa demuestra mejor acierto/pago objetivo fuera de muestra, a cuotas y
cobertura comparables, sin deterioro de calibración. Su puntuación es
`sum(P_target_prudente) - lambda_complejidad * total_patas`. Esta lambda NO es vig,
EV ni dinero: es regularización. Predefinir una rejilla pequeña, elegirla SOLO
con validación temporal y congelarla. Si no hay mejora reproducible, seguir B0.
No atribuir significación estadística a dos probabilidades de un ticket aislado.

Si X_j indica que el ticket j cumplió su target, E[Σ X_j] = Σ P(X_j=1), incluso
con dependencia entre tickets. Por eso el objetivo global de aciertos suma
probabilidades, mientras los logaritmos se usan dentro del ticket para cuotas
y productos. Maximizar Σ log(P_ticket) buscaría otro objetivo: bajo independencia,
la probabilidad de acertar TODOS los tickets a la vez. No confundirlos.

El sesgo favorito/no-favorito se estima con pocos parámetros y regularización;
no se añade un bonus fijo a todo favorito. También puede existir por asignación
del margen. La calibración debe establecer cuánto queda en nuestros datos.

### Pseudocódigo revisado

```python
TARGETS = (2.10, 3.10, 8.20, 12.10)
TOLERANCE = 0.02
MIN_LEGS, MAX_LEGS = 2, 6

def construir_dia(snapshot, frozen_artifact):
    require(ready_to_build(snapshot.now, *snapshot.receipts, frozen_artifact))
    legs = normalize_and_validate(snapshot)  # fútbol y tenis
    legs = best_eligible_book_per_exact_contract(legs)  # mezcla autorizada
    legs = attach_frozen_calibration_and_uncertainty(legs, frozen_artifact)
    legs = abstain_outside_validated_domain(legs)  # calidad, no rentabilidad
    options = {}
    for target in TARGETS:
        options[target] = EXACT_ALL(
            legs, cardinality=(MIN_LEGS, MAX_LEGS),
            sum_log_odds=(log(target*(1-TOLERANCE)),
                          log(target*(1+TOLERANCE))),
            at_most_one_contract_per_event=True,
            # Sin restricción de EV. No usar probabilidades condicionadas a no-push.
        )
        for ticket in options[target]:
            ticket.p_calibrated, ticket.p_prudent = evaluate_frozen_ticket(ticket)
    plans = EXACT_GLOBAL_SET_PACKING(
        options, at_most_one_ticket_per_target=True,
        at_most_one_use_per_event_per_day=True)
    require(plans.search_complete)  # timeout != infactibilidad ni óptimo
    best = min(plans, key=lambda plan: (
        -plan.targets_covered,
        plan.total_legs,
        -sum(t.p_prudent for t in plan.tickets),
        plan.sum_abs_log_distance_to_targets,
        plan.stable_ids))
    require(recheck_exact_products_and_conflicts(best))
    return seal_once_and_publish(best, versions=snapshot.versions)
```

`EXACT_ALL` y `EXACT_GLOBAL_SET_PACKING` son pseudocódigo de branch-and-bound o
MILP, no funciones ya implementadas. Puede resolverse con variables binarias
x[contrato,target], bandas de suma log(q), cardinalidad y conflictos globales.
No truncar a los mejores N de cada target y afirmar después que se garantiza
hallar cuatro; esa poda puede eliminar el único conjunto compatible.

`p_prudent` usa incertidumbre de parámetros y calibración a partir de remuestreos
por bloques temporales del TRAIN, sin inventar un descuento uniforme por pata.
Cuando se disponga de escenarios de parámetros conjuntos, agregar la distribución
de P del ticket y tomar un cuantil prudente predefinido, en lugar de multiplicar
límites marginales y tratarlos como una garantía conjunta. El cuantil es una
medida de sensibilidad bajo ese modelo, no una garantía universal de acierto.

### Devoluciones y dependencia

Conservar p_win, p_push, p_loss y condiciones de void/retiro. Nunca sustituir
P(win) por P(win | no push). Enumerar los estados y reglas de pago del ticket
para estimar tanto P(todas ganan) como P(pago >= mínimo target). La segunda es
la métrica de cumplimiento de cuota. No llamar 'cumplió target' a un ticket
que ganó con pago reducido por devolución.

Evitar dos patas del mismo evento en el flujo diario; esto no demuestra que
partidos distintos sean perfectamente independientes. Estudiar dependencia de
errores por jornada/torneo. El producto se etiqueta como aproximación; para NBA
del mismo partido se exige el modelo conjunto descrito en su sección.

## Calibración y validación sin sobreajuste

Contrato histórico mínimo por observación: event_id, deporte, familia, contrato,
p_base, p_win/p_push/p_loss cuando aplique, quote/forecast/decision/result_received_at,
model_training_cutoff, is_oos, resultado, cuota/casa y reglas de liquidación.
Un precio ausente o de cierre posterior a la decisión queda como research_only.
Pinnacle sin margen es referencia de mercado, no 'verdad real' del partido.

```python
def prepare_history(rows, decision_cutoff):
    # Solo resultados realmente recibidos antes de entrenar el artefacto.
    rows = validate_provenance_and_deduplicate(rows)
    require(all(r.forecast_received_at <= r.decision_at < r.event_start
                and r.quote_received_at <= r.decision_at
                and r.model_training_cutoff < r.forecast_received_at
                and r.result_received_at < decision_cutoff and r.is_oos
                for r in rows))
    return equal_total_weight_per_event(rows)

def split_by_time_and_event(rows, fractions=(0.60,0.20,0.20), embargo_days=7):
    # Por fechas completas: ningún evento, timestamp o mercados del mismo
    # encuentro cruza conjuntos. Purga resultados tardíos en cada corte.
    return chronological_grouped_split(rows, fractions, embargo_days)

def fit_calibration(train, validation, protocol):
    # Separar fútbol y tenis; después familias amplias, nunca jugador/árbitro
    # o línea de cuota elegida después de ver rendimientos.
    # Mínimos iniciales: 1,000 eventos efectivos, 100 de cada clase binaria,
    # 26 semanas para grupo; si no, volver al padre del MISMO deporte.
    # Si el padre tampoco es válido: abstenerse o usar baseline validado, sin inventar calibración.
    for group in eligible_broad_groups(train):
        platt = fit_regularized_positive_slope_platt(group)  # logit(p_base)
        # Isotónica solo con >=2,000 eventos y clases suficientes.
        challenger = fit_isotonic_if_eligible(group, min_events=2000)
        select_once_on_validation(platt, challenger,
            metrics=('log_loss','brier','reliability'), baseline='identity')
    return freeze_artifact_with_hash_and_data_cutoff()

def robust_probability(p, artifact, group):
    # Réplicas ajustadas solo con TRAIN y bloques de semana/partido.
    # El cuantil se predefine; no se elige por el ROI de TEST.
    estimates = artifact.block_bootstrap_predictions(p, group)
    return artifact.calibrated(p, group), quantile(estimates, artifact.fixed_quantile)

def evaluate_frozen_strategy(test, strategy, artifact):
    require(no_test_data_in_strategy_or_calibrator(strategy,artifact,test))
    # Replay completo de snapshots a la hora propuesta, no selección de tickets
    # después de saber quién ganó. Registro de TODOS los días, incluso sin ticket.
    return replay_daily_with_settlement_and_paired_week_bootstrap(test)
```

El descuento es prudencial, no una banda simultánea al 95% sobre cientos de
candidatos. Agrupar por semana/torneo en sensibilidad evita contar mercados del
mismo partido como muestras independientes. Mantener la distribución conjunta
del motor original: correcciones marginales para selección se etiquetan aparte
como p_selection_robust; no sobrescribir la matriz de fútbol/tenis publicada.
Los contratos con push necesitan calibración de estados coherente o exclusión.

El 60/20/20 es cronológico y orientativo: prevalece alcanzar mínimos de muestra
y contar con predicciones OOS de base. No reutilizar el último 20% para escoger
regularización, tolerancia, familias o horario. 2025/2026 ya fueron observados en estudios
previos: sus resultados son exploratorios, no una reserva virgen. La confirmación
final debe ser prospectiva tras congelar estrategia, calibrador y datos.

## Métodos científicos prioritarios y A/B continuo

1. Baseline de mercado: comparar métodos de quitar margen (proporcional, power,
   Shin) y, como candidatos de investigación, OO-EPC/FL-GLM de 2026. Seleccionar
   por log-loss/Brier temporal, nunca por el ROI más alto de una búsqueda extensa.
   Usar todos los lados compatibles de una misma casa, línea, periodo y snapshot.
   Agregar probabilidades normalizadas de fuentes comparables; no quitar margen
   a una colección artificial de máximas cuotas de distintas casas.
2. Mezcla regularizada mercado/modelo: ajustar un peso global por deporte/familia
   grande en validación, permitiendo peso cero del modelo propio. En distribuciones
   de marcador/estadística, mezclar distribuciones coherentes; no modificar de forma
   independiente probabilidades que deban sumar uno. No crear pesos por jugador.
3. Selección con abstención: medir curva error-cobertura y excluir datos fuera de
   dominio o poco fiables. Probar controles conformales selectivos en sombra,
   reproduciendo el optimizador completo. Un control válido antes de seleccionar
   el mejor entre miles no se traslada automáticamente al ticket elegido.
4. Cambio de distribución: vigilar cobertura, calibración, disponibilidad, minutos
   NBA y cambios de temporada. Alertar y suspender dominios degradados; una alerta
   no autoriza reentrenar y promocionar automáticamente. La garantía conformal bajo
   intercambiabilidad no se convierte en garantía para series deportivas con drift.
5. Conjunta NBA: simulación coherente de marcador, minutos y jugadores, incertidumbre
   de parámetros y sensibilidad a lesiones/rotaciones. No basta correlación lineal
   ni calibración marginal. Comparar escenarios con resultados reales por partido.

Comparaciones predefinidas, en sombra y con mismos snapshots:
- A: estrategia anterior, solo referencia histórica por cambiar targets/cantidad.
- B0: cuatro targets, mínimo de patas y baseline calibrado de mercado.
- B1: misma política y targets, mezcla mercado/modelo; evaluar primero sin cambiar
  cardinalidad ni abstención para identificar qué componente aporta mejora.
- B2: mejor versión validada anterior más control de incertidumbre/abstención.
- B3: candidato de más patas con regularización por complejidad, solo después de
  comparar lo anterior; no atribuir ganancias a tres cambios simultáneos.

Métrica primaria: acierto de cuota objetivo por target, a cobertura comparable.
Medir además porcentaje de días con 0/1/2/3/4 tickets, Brier, log-loss y curvas
fiabilidad del ticket y de sus patas. Incluir pagos reducidos y anulaciones con
reglas explícitas. Reportar acierto por ticket publicado y por día elegible;
publicar menos no puede presentarse como una mejora sin informar su cobertura.

ROI realizado, unidades y drawdown se mantienen como contabilidad secundaria;
no se exige ni se presupone que sean positivos. Comparar con igual presupuesto
diario además de una unidad por ticket. Estimar intervalos de las diferencias
con bootstrap pareado por bloques de semana; analizar por partido/torneo cuando
haya dependencia. Los errores se agrupan, no se cuentan como patas independientes.

Dividir 60/20/20 por tiempo y eventos; dentro del 60% generar predicciones OOS de
base. Elegir métodos con el 20% de validación y usar el 20% final una sola vez.
Todo periodo ya observado queda exploratorio; reservar confirmación prospectiva.
No convertir el 95% de cobertura de un intervalo conformal en '95% de probabilidad
de ganar': un conjunto de predicción puede incluir ganar Y perder.

Seguimiento operativo diario y revisión predictiva mensual. Evaluación primaria
predefinida a 12 semanas y al menos 200 tickets por target y brazo; estos mínimos
no prueban potencia para mejoras pequeñas. Definir efecto mínimo y potencia antes
de iniciar, corregir múltiples comparaciones y no detener por un pico favorable.
Promover por mejora predictiva reproducible, calibración y cobertura; nunca por
una racha de ROI o por revisar muchas veces el mismo test. Control anytime-valid
es una alternativa de investigación, no una garantía añadida por nombrarlo.

## Integración posterior necesaria

1. Nuevo contrato normalizado fútbol/tenis con snapshot PIT y liquidación común.
2. Tablas versionadas multideporte: strategy_version, target_id, target/banda,
   event_id namespace, probabilidades de estados, cuota/casa/recibos y hashes.
   No reinterpretar escalones antiguos 3–5 como targets nuevos 8.20/12.10.
3. Artefacto de calibración aprobado con dominio, cortes, métricas y hash;
   datos sin prueba de disponibilidad no habilitan calibración de producción.
4. Lote propio de parley de las 03:35, idempotente, selección transaccional,
   sellado antes de cualquier partido. Conservar historial y triggers inmutables.
5. API `/parley`: reglas dinámicas de cuatro targets, versiones, fecha operativa,
   estado/motivos, cuota de referencia multicasa y probabilidad definida claramente.
6. Web/Flutter: textos dinámicos; retirar frases fijas '5 escalones' y 'una casa'.
   Flutter ya recibe el cálculo del servidor: no duplicar optimizador en Dart.
7. Tests: mínimos 2/2/4/5, bandas y bordes exactos, todas las casas del mismo
   contrato, un evento por día, caso donde greedy impide el cuarto target pero
   búsqueda global lo encuentra, ausencia de filtros de rentabilidad, comparación
   entre cardinalidades, datos futuros/duplicados excluidos, push/retiro, solver timeout,
   idempotencia y compatibilidad del historial antiguo.

## Literatura contrastada, disponible al 6 de noviembre de 2026

Las siguientes son fuentes primarias consultadas. Los trabajos arXiv se tratan
como preprints, sin atribuirles revisión por pares por estar en ese repositorio.
Las aplicaciones propuestas al motor son inferencias de ingeniería, no resultados
ya demostrados en nuestro histórico. No se elige un método solo por ser reciente.

| Trabajo / fecha | Qué aporta | Aplicación y límite |
|---|---|---|
| [Forecast Sports Outcomes under Efficient Market Hypothesis](https://arxiv.org/abs/2604.17194), 19-abr-2026, preprint | Evalúa conversión de cuotas a probabilidades en 90,014 partidos de fútbol; propone OO-EPC y un GLM de pocos parámetros para el sesgo favorito/no-favorito. | Compararlos con proporcional/power/Shin y un baseline de mercado. Mejor conversión probabilística no demuestra beneficio económico ni transferencia automática a tenis/props. |
| [The Parlay Puzzle: Expected Utility and Multi-Leg Betting](https://www.karlwhelan.com/Papers/Parlays.pdf), Karl Whelan, may-2026, working paper | Estudia utilidad esperada y composición de combinadas bajo supuestos explícitos; documenta el coste de contratos con muchas patas. | Sustenta comparar combinaciones cortas y costes reales. No demuestra que el menor número de patas maximice siempre acierto a cuota fija. |
| [Prices, Probabilities, and Parlays](https://arxiv.org/abs/2607.14430), 15-jul-2026, preprint | En Kalshi, encuentra calibración dependiente del tiempo hasta liquidación y un sobreprecio adicional en combinaciones entre partidos. | Registrar hora, tipo de producto y cuota real del paquete. Sus resultados sobre un mercado de contratos no se convierten en coeficientes para casas tradicionales o NBA. |
| [ParlayMarket: Automated Market Making for Parlay-style Joint Contracts](https://arxiv.org/abs/2603.22596), 23-mar-2026, versión 3 del 10-ago | Construye precios de contratos conjuntos representando dependencias; resultados de teoría, simulación y datos Kalshi. | Justifica modelar dependencia del NBA same-game. Es un mecanismo de formación de mercado, no un algoritmo probado de pronóstico de jugadores ni una receta de correlación para nuestro motor. |
| [Conformal Selective Prediction with General Risk Control](https://arxiv.org/abs/2603.24704), 25-mar-2026, preprint | SCoRE combina abstención y control del error en los casos seleccionados, bajo supuestos estadísticos. | Candidato para decidir cuándo publicar. Las aplicaciones estudiadas no son apuestas deportivas; validar dependencia, selección del optimizador y cambios temporales antes de afirmar garantías. |
| [Anytime-Valid Conformal Risk Control](https://arxiv.org/abs/2602.04364), 4-feb-2026, preprint | Estudia control de riesgo cuando el conjunto de calibración crece y se revisa repetidamente. | Investigar seguimiento secuencial frente a mirar el mismo test cada día. No garantiza ganar apuestas ni valida automáticamente datos deportivos no estacionarios. |
| [Contract choice, parlay adoption, and sportsbook margins](https://www.sciencedirect.com/science/article/pii/S1544612326007464), 2026, Finance Research Letters, DOI 10.1016/j.frl.2026.110218 | Analiza 547 millones de apuestas NFL de una casa regulada; asocia mayor uso de combinadas con mayores pérdidas, controlando actividad e importe. | Evidencia observacional relevante sobre costes y comportamiento; no un ensayo de nuestra estrategia ni prueba de imposibilidad universal de ganar. Se consultó el resumen editorial indexado; el texto completo devolvió 403. |

La regla operativa es **no asumir ventaja económica**, no afirmar como teorema
que nadie puede superar ninguna cuota. Medir pérdidas y sesgos sigue siendo útil
aunque no se utilicen como filtro. A modo de referencia aritmética, 1/target vale
47.6%, 32.3%, 12.2% y 8.3% para los cuatro targets: son probabilidades de equilibrio
para contratos binarios sin devolución, NO estimaciones de acierto ni límites
universales. El margen y los pagos efectivos impiden inferir P real solo de Q.

Documentación adicional de implementación:
- [Calibración de probabilidades, scikit-learn](https://scikit-learn.org/stable/modules/calibration).

La calibración y optimización descritas son una propuesta. No se ajustó ni promovió
un calibrador, no se ejecutó un backtest temporal del motor v2 y no se ha demostrado
mejora de acierto o rentabilidad. La comprobación descriptiva anterior sí se ejecutó.

## Ampliación solicitada: parley NBA por partido

Decisión adicional del usuario: incorporar NBA con mercados del encuentro y
pronósticos de jugadores; generarlo al sellarse NBA en su horario correspondiente,
con referencia a la ventana de 60 minutos. Se añade un flujo `nba_same_game`,
independiente de los cuatro targets diarios fútbol/tenis; no los sustituye.
Interpretación operativa: un ticket adicional por partido elegible, no cuatro
tickets NBA nuevos ni un ticket que mezcle partidos sin solicitarlo.

### Disparo y horario

- Disparo autorizado principal: evento `nba_forecast_sealed(game_id, seal_hash)`.
  Disparar la evaluación al verificar el sello; construir en la ventana indicada
  abajo. Nunca publicar un ticket con un pronóstico aún no sellado.
- Ventana de referencia: T−60 respecto al inicio confirmado del partido. Si NBA
  se sella en otro horario, manda la hora real de su sello: no anticipar 60 min
  respecto de un sello futuro ni inventar probabilidades antes de que existan.
- A T−60 se puede preparar calendario, disponibilidad y cuotas, o construir si
  el pronóstico vigente ya está sellado. Si todavía no existe, estado
  `waiting_nba_seal`, y despertar con el sello. No modificar el horario del
  productor NBA para satisfacer el consumidor de parleys.
- Si la cohorte se sella antes de T−60, esperar a T−60 y revalidar evidencia y
  precios; si se sella después, consumirla en ese momento. Se conserva la
  antelación mínima inicial de 30 min del plan; un sello más tardío no produce
  ticket bajo esta versión. Cambiar esa antelación exige una versión de política.
- Hora de evaluación: `max(tipoff_utc - 60 min, forecast_sealed_at)`;
  verificar de nuevo `now < tipoff_utc - 30 min` antes de sellar el ticket.
  Conservar zonas UTC; mostrar al usuario America/Mexico_City.
- No confundir la regla de fecha del informe de lesiones con hora de ejecución.
  `multimarket_v13_live.py` valida que el sello preceda al inicio, y
  `injury_t60.py` es una extracción retrospectiva del reporte anterior a T−60;
  ninguno acredita por sí solo un cron de publicación a T−60 en producción.

### Contratos y objetivo del ticket

- Un solo `game_id`, mínimo dos patas: al menos un mercado del partido y un prop
  de un jugador participante. Priorizar dos; límite inicial cuatro, configurable
  en API y versionado. No completar con jugadores dudosos ni contratos sin cuota.
- Partido: ganador, hándicap, total o puntos de equipo cuando el productor,
  calibración y proveedor de precios soporten ese contrato exacto.
- Jugadores: puntos, rebotes, asistencias y sumas P+R/P+A/R+A/P+R+A únicamente
  si la versión sellada los incluye y están habilitados; no suponer que triples,
  robos o tapones están disponibles por existir etiquetas en la interfaz.
- Target NBA no fijado por el usuario: propuesta inicial **2.10 ±2%**, separado
  de los cuatro targets diarios y expuesto como configuración del servidor.
  Rechazar ticket si no hay combinación elegible; no forzar mercados para llenar.
- Conservar snapshot de disponibilidad, probabilidad de participación, minutos,
  contratos/periodos exactos y liquidación de DNP, salida temprana y prórroga.
  Los cambios posteriores al sello no reescriben el pronóstico original.

### Correlación: excepción obligatoria al optimizador independiente

Este ticket combina selecciones del MISMO partido. No aplica la prohibición
general de una pata por evento; se sustituye por máximo un ticket NBA por partido
y prohibición de contratos duplicados, contradictorios o lógicamente redundantes.
La excepción solo existe dentro de `nba_same_game`, no en los tickets diarios.

No multiplicar probabilidades marginales. Puntos de un jugador, total del equipo,
ganador y otras estadísticas comparten minutos, ritmo, prórroga y disponibilidad.
Calibradores individuales aprobados no acreditan una distribución conjunta ni
una correlación concreta. Usar escenarios conjuntos coherentes del partido
(rotaciones, minutos y producción de todos los jugadores), con validación OOS
de combinaciones; si no existe ese modelo, `joint_model_unavailable` y no publicar
una probabilidad conjunta supuestamente acreditada.

La autorización de mezclar casas se conserva. Pero multiplicar las mejores cuotas
simples de distintas casas NO constituye una oferta de same-game parlay. Guardar
por separado `reference_odds_product` y `offered_parlay_odds`; la segunda requiere
una oferta real del conjunto exacto, con sus reglas. Si solo existe la primera,
el ticket es `reference_only`, sin cuota ejecutable ni rendimiento reproducible acreditado.
No retirar por ello la autorización multicasa del plan diario.

Para contratos binarios y cuota real del conjunto:

    P_joint = P(todas las condiciones | escenarios conjuntos disponibles al sello)
    P_target = P(pago real >= mínimo target | escenarios conjuntos)

Con DNP/push/void, calcular el pago de cada escenario con las reglas reales de
la casa y estimar P_target. La cuota combinada puede no descomponerse como producto
de las simples después de una devolución; no reutilizar sin validación el
liquidador independiente. La política principal minimiza patas y desempata por
P_target prudente. El permiso de más patas se estudia como política alternativa
por mejora predictiva conjunta fuera de muestra, sin requisito de rentabilidad. La probabilidad usada para selección debe incorporar incertidumbre
del modelo; aumentar simulaciones solo reduce error Monte Carlo, no el sesgo.

```python
def on_nba_forecast_sealed(receipt, now):
    forecast = verify_sealed_nba_forecast(receipt)
    when = max(forecast.tipoff_utc - minutes(60), forecast.sealed_at)
    if now < when:
        return schedule_once(forecast.game_id, receipt.seal_hash, when)
    if now >= forecast.tipoff_utc - minutes(30):
        return status('missed_pregame_window')
    snapshot = read_pit_inputs(forecast.game_id, as_of=now)
    legs = supported_game_markets_and_player_props(forecast, snapshot)
    require_valid_participation_minutes_rules_and_prices(legs)
    require_validated_joint_model(forecast)
    tickets = enumerate_same_game(legs, min_legs=2, max_legs=4,
                                 require_game_market=True, require_player_prop=True)
    tickets = price_exact_combinations_or_mark_reference_only(tickets, snapshot)
    best = select_shortest_then_highest_prudent_joint_probability(
        tickets, target=2.10, tolerance=0.02)
    return seal_once_and_publish(best, key=(forecast.game_id, 'nba_same_game',
                                           STRATEGY_VERSION),
                                 parent_forecast_hash=receipt.seal_hash)
```

La clave única del ticket no incluye un hash de sello diferente como vía para
duplicar el mismo partido; los reintentos son idempotentes. Registrar el hash padre,
cutoff y cuotas del snapshot. Reprogramaciones anteriores a publicar obligan a
revalidar la ventana; las posteriores se registran sin editar el ticket sellado.

### Calibración, API y validación NBA

- Añadir grupos NBA separados: equipo/partido y props de jugadores. Agrupar por
  partido y fecha; nunca contar miles de props del mismo juego como miles de
  eventos independientes. Mínimos de muestra en partidos efectivos.
- Aplicar el mismo esquema temporal 60/20/20 y modelos base OOS; validar además
  pares/tríos de mercados y sus dependencias. No trasladar el calibrador fútbol
  o tenis a NBA ni inferir calibración conjunta de Brier marginales favorables.
- A/B NBA separado: mínimo de patas vs expansión por calidad predictiva conjunta; cuota real
  del paquete, ROI, cobertura, calibración conjunta, retiros/DNP y pago objetivo.
  Los tickets `reference_only` no se mezclan con ROI ejecutable.
- API: `tipo=nba_same_game`, game_id, target, estado, hora prevista/real, hash
  padre, cuota de referencia/ofrecida, método conjunto y motivos de exclusión.
  La API añade tickets durante el día sin reemplazar el lote fútbol/tenis.
- Flutter/web: leer la nueva sección o colección NBA y actualizar al recibir el
  sello mediante consulta de cambios/polling de la API; no calcular ni decidir
  correlaciones en el cliente. El cliente actual necesitará soporte inicial para
  esa colección; luego horarios, targets y reglas viajarán desde el servidor.
- Tests adicionales: sello antes/después de T−60, ventana de 30 min, identidad
  padre, reintentos sin duplicados, cambio de horario, jugador no disponible,
  contrato no soportado, correlación fuerte donde el producto marginal falla,
  cuota combinada ausente, DNP/devoluciones y publicación dinámica en API.

Estado: ampliación del plan y pseudocódigo; sin activar productor, cron o tickets. Revisión vigente sin filtros de +EV.
