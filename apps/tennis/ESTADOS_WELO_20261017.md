# Tenis: captura de estados y referencia Weighted Elo

17 de octubre de 2026. Se continúa el plan con dos piezas ejecutadas: registro de observaciones de API-Tennis y comparación de Weighted Elo. El modelo híbrido actual se conserva. No se activaron apuestas, publicación ni cambios en el motor de fútbol.

## Captura real y trazabilidad

Se implementó `tennis_engine/state_capture.py` en el checkout aislado de tenis. Cada consulta guarda respuesta original, parámetros sin credencial, recepción UTC, estado HTTP y SHA-256. Un libro local reserva la consulta antes de ejecutarla: un fallo no dispara reintentos ni libera artificialmente el límite. No se siguen redirecciones y los errores no muestran URLs con credenciales.

La base `data/tennis/state_capture_20261017/states.sqlite` conserva recibos y observaciones sin UPDATE/DELETE. Las correcciones se añaden como versiones nuevas; las consultas históricas se resuelven por su fecha de recepción. Desaparecer del listado en vivo no equivale a terminar. Estados desconocidos, cambios de participantes, retiros y cancelaciones quedan visibles. Una corrección que vuelva de terminado a jugando invalida el resultado anterior al exportar carga para esa decisión, conservando la historia previa.

Se importaron 883 observaciones de cuatro respuestas ya archivadas: recientes, próximos, una fecha histórica de 2025 y listado en vivo. No son 883 nuevas observaciones prospectivas. Luego se hicieron **dos consultas reales nuevas**, una ATP y una WTA, del 17 al 19 de octubre UTC. Añadieron **59 + 54 = 113 observaciones**. Al finalizar, a las 21:56:52 UTC:

| Indicador | Resultado |
|---|---:|
| Eventos distintos, incluidos los históricos importados | 879 |
| Observaciones acumuladas | 996 |
| Eventos observados alguna vez jugando | 5 |
| Conflictos de participantes detectados | 0 |
| Recibos registrados y hashes comprobados | 6, todos válidos |
| Consultas nuevas a The Odds API | 0 |

El capturador tiene un tope local configurable: en esta ejecución se declaró **24 consultas por día UTC**. Cuenta solo solicitudes de este capturador, no los otros consumidores de la cuenta ni las pruebas anteriores. No se ha verificado la cuota o coste del plan de API-Tennis; HTTP 200 no lo demuestra. El plan de The Odds API sigue siendo de pago, con 2.000 créditos mensuales de tenis y reserva compartida de 6.000, sin consumo nuevo en esta fase.

### Qué significan las horas

`first_seen_live_at` y `first_seen_terminal_at` son horas de observación del proveedor. No se rellenan `actual_start` ni `actual_end`: no conocemos un límite superior contractual de latencia. Los intervalos entre observaciones no se presentan como límites garantizados de los eventos reales en pista.

La exportación al extractor de carga verifica fuentes y conserva la incertidumbre temporal. Debe consultarse por separado para cada hora de decisión; no se debe generar una versión con información de hoy para reconstruir decisiones pasadas. El ajuste estricto de carga sigue sin muestra temporal suficiente. La captura mejora trazabilidad y permitirá acumular evidencia, pero no transforma por sí sola una hora recibida en una hora física exacta.

`scripts/capture_states.py` ejecuta un ciclo acotado. **No hay una tarea periódica activada en segundo plano.** Antes de fijar una frecuencia de producción hacen falta los límites del plan y medir la actualización del proveedor; no se dejó un consumidor indefinido de consultas.

## Weighted Elo implementado y evaluado

`tennis_engine/weighted_elo.py` implementa de forma original las ecuaciones del artículo: rating inicial 1.500, probabilidad logística en escala Elo, actualización proporcional al error y peso de juegos del ganador dividido entre todos los juegos. El ganador puede haber ganado menos juegos totales que su rival. El K usado es `250 / (N_previos + 5)^0.4`, con convención de contar los partidos anteriores explícita. No se copiaron fuentes del paquete R.

La actualización de un bloque de un partido implementa esa recursión. Nuestro histórico tiene fechas de periodos, a menudo semanales, por lo que los partidos de un mismo periodo actualizan simultáneamente desde los ratings y contadores anteriores. Es una **adaptación por bloques**, no una reproducción literal del orden diario, los datos o la rentabilidad del estudio. El artefacto puede cargarse para inferencia con hash obligatorio; no permite reanudar entrenamiento con un historial de IDs incompleto.

Se entrenó usando las mismas filas aptas y embargo de 35 días que los modelos base congelados al 1-ene-2026: 65.424 ATP y 18.736 WTA. Se usaron exactamente los mismos encuentros y orientación A/B que la evaluación existente. Los ratings quedaron congelados durante el año para respetar ese protocolo de comparación; no se les dio una ventaja de actualización que el modelo base no tuviera. También se incluyó Elo adaptativo con el mismo K, sin ponderación por marcador, para aislar el efecto de esa ponderación.

Menor log-loss/Brier es mejor:

| Circuito y muestra común | Modelo | Log-loss | Brier |
|---|---|---:|---:|
| ATP, 2.451 | Híbrido actual, protocolo congelado | **0,622427** | **0,216682** |
| ATP, 2.451 | Weighted Elo por bloques | 0,629374 | 0,219274 |
| ATP, 2.451 | Elo adaptativo sin ponderación | 0,635266 | 0,221081 |
| WTA, 2.146 | Híbrido actual, protocolo congelado | **0,618318** | **0,215038** |
| WTA, 2.146 | Weighted Elo por bloques | 0,629068 | 0,219019 |
| WTA, 2.146 | Elo adaptativo sin ponderación | 0,641268 | 0,223536 |

Cobertura: 100 % de los casos del conjunto base elegible utilizado, no de todos los partidos del circuito. Se incluyen ECE, diez intervalos de calibración y contrastes emparejados por periodo en los JSON. Hubo 20 casos ATP y 153 WTA con al menos un jugador sin rating previo en esta muestra de entrenamiento; se conserva el rating inicial y se informa esa limitación.

Weighted Elo mejora frente al Elo adaptativo evaluado, pero no mejora al híbrido actual. Se conserva como referencia y no se promueve. Los intervalos exploratorios por periodo favorecen al híbrido frente a esta variante, pero no resuelven toda la dependencia por jugador ni comparaciones múltiples. El año 2026 ya se observó durante desarrollo: no es una prueba futura intacta. No se calculan CLV ni rentabilidad con estos resultados.

## Archivos y reproducción

Checkout: `C:/Users/huye/.codex/worktrees/tennis-engine/apuesta proyec/apps/tennis/`.

- `tennis_engine/state_capture.py`, `tennis_engine/weighted_elo.py`.
- `scripts/capture_states.py`, `scripts/compare_welo.py`.
- `tests/test_state_welo.py`: 21 pruebas nuevas. Total de tenis: **96 aprobadas**.
- Resultados: `data/tennis/weighted_elo_20261017/ATP_v2/` y `WTA_v2/`, con predicciones, modelos, recibos de fuentes y hashes del código. Los ensayos v1 se conservan.
- Captura: `data/tennis/state_capture_20261017/`, con originales y reporte de las 21:56:52 UTC.

Ejemplos desde el proyecto principal, con PYTHONPATH apuntando al directorio apps/tennis del checkout:

```text
python <checkout>/apps/tennis/scripts/capture_states.py --root data/tennis/state_capture_20261017 --credential-file .env.api-tennis.local --daily-limit 24
python <checkout>/apps/tennis/scripts/compare_welo.py --root data/tennis/full_20261016 --improvements-root data/tennis/improvements_20261016 --output <directorio_nuevo> --circuit ATP
```

Nunca pasar la clave como argumento. La configuración local sigue excluida de Git. No se encontraron apariciones de la clave en los resultados nuevos. Los doce hashes del protocolo futuro original siguen coincidiendo.

## Estado del plan

| Fase | Estado |
|---|---|
| Evaluador común y extractor de carga | Implementados y probados |
| Captura de estados con procedencia | Implementada y probada con dos consultas reales |
| Entrenar carga y compararla en tiempo real | Pendiente de muestra válida |
| Weighted Elo | Implementado, evaluado y conservado como referencia |
| Captura recurrente | Comando acotado listo; frecuencia y ejecución periódica pendientes |
| Sedes, viajes y clima | Pendientes de verificación e integración experimental |
| Rentabilidad prospectiva | Pendiente de resultados futuros y contratos/cuotas comparables |

Fuentes: [API-Tennis](https://api-tennis.com/documentation), [artículo de Weighted Elo](https://cris.unibo.it/retrieve/e1dcb337-ea48-7715-e053-1705fe0a6cc9/Weighted%20ELO%20rating%20predictions%20in%20tennis.pdf). El método se reproduce con las adaptaciones declaradas; no se trasladan sus ganancias históricas a nuestro motor.

Verificacion final general: 1.300 aprobadas, 88 omitidas y dos avisos en 145,62 s; arnes correcto. Docker no disponible. Los hashes de codigo y fuentes coinciden en ambos informes v2.
La pagina publica de API-Tennis anuncia 8.000 solicitudes/dia para Starter y prueba de 14 dias (https://api-tennis.com/), pero eso no identifica el plan ni la vigencia de la cuenta del titular. Se solicito ese dato para fijar la frecuencia recurrente; no se confunde con The Odds API de pago.
