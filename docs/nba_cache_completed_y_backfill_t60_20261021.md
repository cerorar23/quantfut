# NBA — caché de `completed()` y backfill de reportes de lesiones cercanos a T-60 (21-oct-2026)

Dos mejoras operativas de la auditoría (`docs/nba_auditoria_motor_20261021.md`, puntos 3 y 7). Ninguna cambia un pronóstico sellado ni las métricas de v1.1-v1.4b.

## 1. Caché por partido en `multimarket_v13_live.completed()`
- Un partido final se descarga una sola vez (`<cache>/games/<id>.json`) y un día cuyos partidos están todos finales no se vuelve a listar (`<cache>/days/<día>.json`). Activar con `--cache CARPETA` en `forecast`; sin él, el comportamiento es el de antes. Una entrada de caché que no coincide con su clave (id, día, temporada, claves) es un error, no un fallo silencioso.
- Fallo explícito: un partido de un día pasado que sigue **en curso** (estado 2) aborta el sellado (`past games not final`), porque descanso y forma saldrían mal. Un partido con estado 1 en fecha pasada (aplazado, nunca jugado) se permite y queda en `completed_games.json` bajo `not_final`. Un box score con otro id que su tarjeta también es error.
- Editar el módulo cambia `live_module_sha256`, que el sellado exige igual al del modelo. Se reajustó en `apps/nba/.local/normalized/nba_f6_live13_model_20261021b`: `fit`, `play_probability`, `observed_share` y temporadas son **idénticos** al modelo anterior; solo cambia ese hash. La cohorte de ensayo (modelo anterior) no se tocó. Para sellar hay que usar el modelo `…b`.
- Pruebas: `tests/test_live_completed_cache.py` (8).

## 2. Backfill de reportes de lesiones a T-60 (`nba.injury_t60`)
**Problema:** el histórico tenía un solo reporte por día (13:30 o 17:30 ET); la regla en vivo usa el último ≥60 min antes del salto. Solo el 2-4 % de los partidos veía un reporte a menos de 1 h del corte (mediana 5,5 h).

**Fuente:** PDF oficiales públicos de `ak-static.cms.nba.com/referee/injury/`. Hasta el 21-dic-2025 hay un archivo por hora (`HHPM`, sellado HH:30 ET); desde el 22-dic-2025, uno cada 15 minutos (`HH_MMPM`, sellado HH:MM). En ese bucket un **403 significa «archivo inexistente»** (los existentes responden 200); se usa un archivo de control conocido cada 50 peticiones para distinguirlo de un bloqueo real, y la descarga se detiene ante cualquier otro estado.

**Qué se hizo:** por cada partido con hora de salto conocida de 2023-24, 2024-25 y 2025-26 se pidió el último archivo sellado ≤ salto − 60 min (retrocediendo hasta 3 pasos si faltaba). 2.148 peticiones a 1 por segundo, tope 2.500, reanudable (`manifest.json` con hash y hora de recepción): **1.910 PDF guardados** en `apps/nba/.local/raw/injury_t60_20261021` y 238 inexistentes. Se parsearon con el parser estricto del repo (0 fallos) y se unieron a IDs NBA: `apps/nba/.local/normalized/nba_injury_t60_20261021/reports.jsonl.gz` (262.723 filas; 2 nombres sin resolver de 248.464). La unión reproduce el 100 % de los IDs de reportes ya unidos antes (3.048 de 3.048).

**Resultado (partidos con un reporte válido a ≤1 h del corte):**
| Temporada | Antes | Después | Mediana de antigüedad al corte |
| --- | --- | --- | --- |
| 2023-24 | 4,2 % | 99,9 % | 5,5 h → 0,5 h |
| 2024-25 | 3,9 % | 99,8 % | 5,5 h → 0,5 h |
| 2025-26 | 2,4 % | 99,9 % | 5,5 h → 0,0 h |

**Diagnóstico descriptivo (post-hoc, sin modelo; filas con box score):** con reportes a T-60 el 14,5 % de las filas cambia de estado (sobre todo «Questionable» → «Available» u «Out») y los estados se afilan: probabilidad de jugar de «Out» 4,3 % → 0,8 %, «Doubtful» 9,6 % → 3,1 %, «Available» 81,5 % → 85,8 %, «Probable» 93,8 % → 93,6 %, «Questionable» 72,7 % → 71,6 %. Esto es lo que el modelo en vivo ya recibe; el entrenamiento retrospectivo no lo veía.

## Límites
- 2022-23 no se cubre: su layout no lo lee el parser estricto y el parser que se usó para esas temporadas no está en el repo. Sigue con lo que había (17:30 ET).
- La recepción es retrospectiva (`first_received_at_utc` = hoy): no prueba que el reporte estuviera disponible a su hora. 238 archivos no existen en la fuente; esos partidos caen al reporte anterior.
- 3.261 filas de reporte (1,2 %) no se unieron a un partido (partidos excluidos del histórico por discrepancias).
- No es todavía una mejora medida del modelo: falta reentrenar con estos reportes.

## Qué sigue
Evaluar con un protocolo congelado nuevo (v1.5) la v1.3 con `reports.jsonl.gz` antiguo + nuevo (los reportes se concatenan; `status_map` ya elige el último válido por jugador y partido) frente a la v1.3 actual en 2024-25 y 2025-26. Es la prueba de si el desajuste entrenamiento/vivo costaba predicción.
