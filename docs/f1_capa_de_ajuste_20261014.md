# F1 — Capa de ajuste de lambdas por bloques (14-oct-2026)

Segunda fase de [la spec de señales del motor](superpowers/specs/2026-10-14-senales-motor-principal-design.md);
plan: [2026-10-14-f1-capa-de-ajuste.md](superpowers/plans/2026-10-14-f1-capa-de-ajuste.md).
Código: `src/qf/model/ajuste.py` y `lineup_challenger.informe_antes_despues`.

## Qué se hizo

- `qf.model.ajuste`: registro de bloques de señales, comparación **incremental**
  (modelo con los bloques A frente a A+B, mismas filas y misma partición), el
  artefacto `ajuste_<versión>.pkl` y un CLI (`python -m qf.model.ajuste`; solo
  escribe con `--guardar`). Sin bloques aceptados devuelve las lambdas base
  exactas. Dixon-Coles y la calibración no se tocan.
- La puerta de `lineup_challenger.fit_and_validate` se extrajo a
  `informe_antes_despues` sin cambiar un solo número (prueba de caracterización).
- Nada se despliega ni se activa en F1: el código vive en el repo.

## Dos defectos de la puerta heredada, corregidos en `ajuste.comparar`

1. **El primer bloque se llevaba el mérito de re-nivelar.** El ajuste incluye un
   intercepto; si las lambdas base están sesgadas, cualquier columna, hasta una
   constante, "ganaba" contra las lambdas crudas. Ahora la referencia del primer
   bloque es un modelo **solo de nivel** (intercepto, sin señales).
2. **Dejaba pasar ruido.** Con ruido puro, la puerta básica (RPS, log-loss, ECE,
   ≥2 ligas) aprobó en 8 de 40 semillas (20 %). Se añade significancia:
   remuestreo pareado por partido de la diferencia de RPS, percentil 95 < 0.

`lineup_challenger.fit_and_validate` conserva su puerta original para el
challenger en sombra; el criterio nuevo vive solo en `ajuste.comparar`.

## Línea base sobre datos reales

Predicciones fuera de muestra del entrenamiento `2026.10.12-221104` (3.608 filas,
12 ligas; 2.525 de ajuste y 1.083 de validación), calculada en el VPS en solo lectura:

| Medida | Lambdas base | Con XI simple |
|---|---|---|
| RPS | 0,21328 (nivel) | 0,21199 |
| Log-loss | 1,04059 | 1,03656 |
| ECE | 0,02706 | 0,02304 |
| ΔRPS medio por partido | | −0,001298 |
| ΔRPS, percentil 95 | | −0,000561 (< 0: significativo) |
| Ligas que mejoran | | 9 de 12 |

- **El XI simple pasa la puerta estricta.** Quedó claro que no se debía al
  intercepto: el modelo de nivel (0,21328) casi coincide con las lambdas crudas
  (0,21329), es decir, no había sesgo de nivel que re-nivelar.
- Ligas donde no mejora: Bundesliga (36 partidos), Ligue 1 (56) y Eredivisie
  (66); muestras pequeñas. Champions tiene solo 5 partidos en la validación.
- Es una ganancia pequeña (0,6 % de RPS) y está medida con XI históricos
  descargados después del partido, no con los capturados antes del inicio. Hasta
  que entre en vivo, sigue siendo `shadow_only` y el CLV sigue sin muestra.
- Las variantes con valor de jugador no pasan la puerta del último entrenamiento
  (`valor` 4 ligas, `masmenos` 5; la `nota` es solo comparación).

## Reentrenamiento

El que pedía la spec para F1 **ya existe**: el entrenamiento del 12-oct incluyó el
xG de API-Football (148 parejas) y no superó la puerta frente a Elo. El cron
repite el día 1 (próximo: **1-nov-2026 03:00 UTC**, 4 h 44 min) con los 5.355 xG
de PitchAPI, FotMob y lo recibido desde entonces. No se lanzó uno manual: habría
gastado ~5 horas de CPU de producción por una diferencia mínima. Se puede
lanzar a petición.

## Siguiente

F2 (cuotas de apertura/cierre y movimiento) y F7 (sello tardío) son los que
permiten que el XI, que ya gana fuera de muestra, entre al motor principal.
