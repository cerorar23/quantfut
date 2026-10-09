# NBA: avance de fases — 5 de octubre de 2026

Implementado y ejecutado un incremento de F1–F5. La aplicación NBA conserva
su entorno, configuración, datos y ledger propios. No se modificó la
aplicación de fútbol. Ninguna puerta G0–G9 se aprueba por este incremento;
los escenarios siguen marcados `actionable=false`.

## F1: aislamiento y recuperación local

- Comprobación de fútbol antes/después: 606 pruebas correctas. Se resolvió
  el problema de temporales de pytest usando una carpeta nueva dentro del
  workspace, sin modificar tests de fútbol ni reemplazar su entorno previo.
- Suite NBA: 47 pruebas correctas, incluyendo integridad de archivos,
  fechas/temporadas, identidades, rechazo de respuestas denegadas y fugas
  temporales del experimento de arranque.
- Ensayo de backup/restauración de SQLite de investigación: 15 eventos
  encadenados restaurados con el mismo hash final y triggers inmutables.
  También se restauró un dataset normalizado con SHA256 idéntico. Es un
  checkpoint anterior al experimento de arranque, no una copia del estado
  final de esta sesión. No valida recuperación completa de raw ni G1.
- Postgres/Redis, despliegue y anclaje externo siguen pendientes. Docker
  no está instalado en este entorno: el arnés omite esa comprobación.

## F2/F3: históricos integrados y captura actual

El nuevo comando `import-sdv` integra los box scores SportsDataverse de
2021-22 a 2025-26 con las fechas/registros de equipo NBA ya recibidos.
Comprueba hashes, temporada, tipo de competición, IDs, duplicados, minutos
y sumas de equipo. Produce 154.058 registros en un snapshot independiente.
Las 30 temporadas descargadas siguen disponibles raw; este incremento
normaliza cinco temporadas con referencia fechada.

| Temporada regular | Partidos aceptados antes | Partidos aceptados ahora | Denominador raw |
|---|---:|---:|---:|
| 2021-22 | 14 | 1.171 | 1.230 |
| 2022-23 | 14 | 1.175 | 1.230 |
| 2023-24 | 15 | 1.159 | 1.230 |
| 2024-25 | 1.179 | 1.179 | 1.230 |
| 2025-26 | 1.151 | 1.146 | 1.230 |

La cuarentena conserva las reglas anteriores: `MM:60` no se repara en
silencio. El adaptador v2 también rechaza jugadores sin referencia del
mismo partido/equipo, incluyendo no participantes. Sus 695 IDs rechazados
incluyen competiciones sin referencia fechada, además de discrepancias de
datos; no son 695 partidos regulares defectuosos. Dataset v1 y v2 tienen
bytes idénticos: se verificó igualdad de SHA256 y no se repitió su replay.
Se conservan ambos informes y el ledger registra las dos importaciones.

No se reemplazó el dataset original. En las dos últimas temporadas, la
fuente nueva no resuelve todos los huecos ni es uniformemente mejor. La
comparación de replays encontró 39.205 pronósticos comunes, con 36
resultados observados diferentes entre fuentes. Solo se compararon errores
emparejados donde coincidían rebotes y minutos reales. Esto es sensibilidad
de datos, no selección de fuente por rentabilidad.

`capture-rosters --season-year 2027` recibió las 30 plantillas ESPN para
2026-27: 606 jugadores distintos, sin afiliaciones duplicadas en esa captura.
Las respuestas y su primera recepción UTC se guardan individualmente.
Los IDs llevan namespace `espn`; el histórico usa `nba`. La correspondencia
entre ambos sigue pendiente de evidencia y no se inventa mediante coincidencia
aproximada. La captura completa de una fuente no demuestra plantilla oficial
completa o disponibilidad médica antes de un partido.

La fuente trae 78 entradas de lesión. En 36, el campo de fecha tiene más de
48 horas respecto de la recepción; algunas datan de julio. Ese umbral solo
es diagnóstico y la semántica del campo no está verificada. Ninguna se ha
convertido en disponibilidad médica fiable. «Active» y ausencia de lesión
en la respuesta no equivalen a jugador sano o participante confirmado.

El histórico de lesiones del informe anterior sigue pendiente de validación
contra PDF, zona horaria, identidades y corte anterior al inicio. Las muestras
de props siguen sin contratos/PIT suficientes para evaluar ROI o CLV.

## F4/F5: referencia y experimento de inicio de temporada

Se volvió a evaluar la referencia congelada en 2024-25/2025-26 sobre el
dataset nuevo: 39.225 casos en 2.044 partidos. CRPS 1,3519 frente a 1,3953
de la media móvil/Poisson; error de minutos 4,9780 frente a 5,0821.
Esto no cambia la conclusión comercial: aún no hay evaluación contra cuotas.

El modelo original exige diez apariciones en la misma temporada. Para poder
investigar proyecciones al comenzar 2026-27 se creó un experimento separado,
`startup-research-v0.1`, con protocolo sellado antes de ejecutarlo:

- Usa las últimas 20 apariciones del año inmediatamente anterior, con al
  menos 10 disponibles. Sus minutos actúan como prior de cinco partidos;
  las apariciones nuevas actualizan el prior.
- La tasa Gamma-Poisson combina exposición/rebotes previos con peso 0,25,
  un prior base y datos de la temporada nueva. Se mezcla sobre minutos
  históricos centrados en la proyección.
- Se compara con media móvil de diez apariciones que también puede cruzar
  desde el año anterior. Se excluye todo el día objetivo y otras competiciones.
- Solo evalúa las primeras diez apariciones observadas en el dataset
  conciliado. Las exclusiones pueden desplazar ese conteo respecto del real.
  Rookies o jugadores sin suficiente historial previo generan abstención.
- No incorpora equipo/rol, lesiones, rival o disponibilidad actuales; todos
  los resultados son condicionales a participación. No sustituye el modelo
  anterior ni se promociona por este resultado exploratorio.

Resultados en 2024-25/2025-26:

| Métrica | Candidato de arranque | Referencia |
|---|---:|---:|
| Casos evaluados | 8.264 | mismos casos |
| Partidos distintos | 1.396 | mismos partidos |
| CRPS, menor es mejor | 1,3026 | 1,3763 |
| Error absoluto de minutos | 5,3779 | 5,6229 |
| Error absoluto de rebotes | 1,8958 | 1,9569 |
| Cobertura del intervalo central nominal 80% | 87,94% | 78,57% |

La diferencia de CRPS tiene intervalo bootstrap por partido de
[-0,0839; -0,0629]. Este método no resuelve toda la dependencia temporal o
entre jugadores repetidos. La discreción puede elevar la cobertura del
intervalo central sobre el 80%; ese porcentaje solo no valida calibración.
Los datos históricos ya habían sido inspeccionados: se trata de exploración,
sin búsqueda de parámetros y sin confirmación prospectiva.

Se ejecutó además `startup-scenario` con corte 5-oct-2026 y temporada
2026-27: puede producir una distribución provisional desde 2025-26 sin
esperar diez partidos nuevos. Su salida declara rol/disponibilidad
desconocidos y `actionable=false`. No es una recomendación de apuesta.

## Qué continúa pendiente

Prioridad inmediata: verificar correspondencias ESPN/NBA y obtener
disponibilidad prepartido fiable; después incorporar rol/rotaciones actuales
y evaluar calibración/abstención de las proyecciones de arranque. La
coherencia conjunta de minutos de equipo sigue pendiente. Una mayor
cobertura histórica no resuelve cambios de entrenador, traspasos o rookies.

F6 requiere contratos/cuotas utilizables, revalidación del precio, outbox y
ensayo de Telegram con destino privado. No se activó entrega. F7 requiere
observaciones prospectivas y revisión de promoción; los backtests aquí
documentados no la sustituyen.

## Evidencia reproducible

Todo dentro de `apps/nba/.local/reports/`:

- `sportsdataverse_import_v2_20261005.json`: dataset y cobertura final.
- `sportsdataverse_replay_20261005/`: referencia y pronósticos individuales.
- `source_sensitivity_20261005.json`: comparación entre fuentes.
- `current_rosters_20261005.json` y `current_roster_injury_audit_20261005.json`.
- `startup_replay_20261005/` y `startup_scenario_20261005.json`.
- `recovery_20261005.json`: checkpoint/restauración de investigación.
- `harness_post_startup_20261005.txt`: comprobación final de fútbol.

Protocolo de arranque: `apps/nba/startup_protocol.json`. Comandos de
reproducción en `apps/nba/README.md`. Hashes, manifiesto del código y
ejecuciones se incorporan al registro `nba_plan_fases_auditoria.json`,
preservando la evidencia anterior y manteniendo todas las puertas pendientes.
