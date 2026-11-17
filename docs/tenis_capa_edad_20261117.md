# Tenis v2: capa de edad (17-nov-2026)

Decisión del titular (17-nov-2026): implementar la edad como versión nueva del modelo tras medirla con walk-forward.

## Qué es

Segunda etapa sobre la probabilidad π del filtro congelado (`apps/tenis/src/tenis/modelo/capa_edad.py`):

    logit π' = b · logit π + β · (edad_1 − edad_2) / escala

- Sin intercepto: los lados están en orden pseudoaleatorio, así que π'(A, B) + π'(B, A) = 1 por construcción (prueba incluida).
- Edad de cualquiera de los dos desconocida o fuera de [14, 50] años ⇒ término de edad = 0; solo actúa la pendiente `b`.
- `|edad_1 − edad_2|` se recorta a 20 años. `b` sustituye a la capa de recalibración de pendiente (no se apilan).
- β no tiene signo impuesto. Sale negativo: el jugador más joven rinde por encima de lo que su rating anticipa.
- El filtro, el simulador, la pieza P y los triggers de la base de datos no se tocan.

## Medición (walk-forward 2019-2024, reserva 2025-26 sin tocar)

Para cada temporada T, (b, β) se ajusta con las temporadas 2013..T−1 y se aplica a T (`capa_edad.por_temporada`).
Δ = capa de edad − referencia (negativo = mejora). Código: `apps/tenis/ops/evaluar_wf.py`, informe `evaluacion_wf_capa_edad.json`.

| | ATP | WTA |
|---|---|---|
| Δ log-loss vs capa de pendiente actual | −0,0022 [−0,0028; −0,0017] | −0,0026 [−0,0035; −0,0017] |
| Temporadas que mejoran | 6 de 6 | 5 de 6 (2022: +0,0006) |
| Δ log-loss vs Elo recalibrado (G-línea base) | −0,0087 [−0,0101; −0,0072] | −0,0082 [−0,0103; −0,0060] |
| Con edad conocida / sin edad conocida | −0,0035 / −0,0000 | −0,0029 / −0,0000 |
| Pendiente de calibración (antes → después) | 0,902 → 0,961 [0,931; 0,988] | 0,975 → 1,028 [0,978; 1,078] |
| No-fuga (violaciones) | 0 | 0 |

- Compuerta `G_capa_edad` (nueva): la capa se activa si el IC95 de Δ log-loss frente a la capa de pendiente queda por debajo de 0.
  Pasa en ATP y WTA.
- La mejora se concentra en partidos con más de 5 años de diferencia de edad (≈ −0,007 en ambos circuitos).
- El coeficiente es estable por temporada (β/escala entre −0,11 y −0,17). Medido también por separado en partidos con la edad
  tomada del propio partido de SofaScore y en partidos de TML: mismo efecto, así que el sesgo de supervivencia de las fechas de nacimiento
  no lo explica.
- `G_calibracion` de ATP sigue sin pasar por IC (el IC de la pendiente excluye 1), como antes; la pendiente mejora de 0,902 a 0,961.
- Las predicciones base de `evaluar_wf` no cambian: el sha256 de `predicciones_wf.parquet` coincide con el artefacto oficial (`af77e927…`).

## Coeficientes congelados (ajuste con 2013-2024)

| | b (pendiente) | β | escala (años) | partidos |
|---|---|---|---|---|
| ATP | 0,9603 | −0,1660 | 5,801 | 94.858 |
| WTA | 0,9790 | −0,1524 | 5,766 | 28.682 |

Artefacto: `data/tennis/rediseno_20261104/modelo_s3/hiperparametros_capa_edad.json` (`sha256_contenido`
`55c17ba1c6e28445b0e99b2bfab64c1d7b681766c29d6574c62089a488f41f94`). Se genera con `apps/tenis/ops/congelar_capa_edad.py`, que exige que
la compuerta pase por circuito. El `hiperparametros.json` original queda intacto (vuelta atrás = seguir con ese artefacto).

## Motor

`motor.py` lee las edades al corte con la misma regla que la exportación PIT (`edades_al_corte`: aserción `fecha_nacimiento` visible en el
corte, mayor prioridad de fuente, la más reciente) y aplica la capa solo si el artefacto activo trae `capa_edad` (`aplicar_capa_edad`).
Con capa, las entradas selladas añaden `capa_edad`, `pi_base` y `edad_dif`; sin ella quedan exactamente como antes.

**Hallazgo importante:** `simular_y_sellar_partido` todavía usa valores de demostración (`pi_lado1 = 0.585`, `S_hat = 1.25`); la inferencia real
del filtro solo corre en los scripts de entrenamiento y walk-forward. La capa está lista para cuando el motor use el filtro, pero hoy no
cambia ningún pronóstico en producción.

## Lo que NO se hizo

- Registrar el artefacto nuevo en `artefacto_activo` con una `version_modelo` nueva: decisión de despliegue del titular.
- Edad dentro del filtro (afectando al rating de cada jugador): exigiría reestimar hiperparámetros.
- Variables de actividad reciente (partidos en 14 días, descanso): mejoran otros −0,0014 (ATP) y −0,0021 (WTA) pero con signo contrario a una
  fatiga; sin explicación causal no se adoptan. La fatiga del modelo sigue sin validar (φ1 ≈ 0).

## Reproducir

    python apps/tenis/ops/evaluar_wf.py --dir <carpeta con hiperparametros.json> --reps 1000
    python apps/tenis/ops/congelar_capa_edad.py --dir <la misma carpeta>
    pytest apps/tenis/tests/test_capa_edad.py apps/tenis/tests/test_capa_edad_motor.py   # estas últimas con QF_TEST_PG_DSN
