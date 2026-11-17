# Tenis v2: el motor usa el filtro real (17-nov-2026)

Decisión del titular (17-nov-2026): conectar el filtro al motor. Hasta hoy `motor.py` sellaba con valores de demostración
(`pi_lado1 = 0.585`, `S_hat = 1.25`, `var_rho = 0.009`) y el filtro solo corría en los scripts de entrenamiento y evaluación.

## Cómo funciona (plan §H.1: «reproducir el filtro con Ψ congelado, simular, sellar»)

`apps/tenis/src/tenis/inferencia.py`:

1. Lee la evidencia completa de la base en una transacción de solo lectura (`datos.lectura.leer_todo`).
2. La convierte con `exportar_pit.construir(tablas, desde=2005-01-01)` y la pasa por Parquet en memoria, para que los tipos sean
   idénticos a los de la ruta validada. **La ventana desde 2005 es obligatoria**: con todo el histórico (1968-) las probabilidades
   cambian hasta 0,045.
3. Corre el mismo filtro R y la pieza P que `ops/evaluar_wf.py` con el Ψ del artefacto activo y toma, para cada partido, π, Var(ρ) y Ŝ.
4. Deshace la orientación pseudoaleatoria de lados de la exportación para devolver π desde `partido.jugador_1` de la base.

`motor.py`: la pasada (`ejecutar_pasada_motor`) infiere **una sola vez** para todos los partidos dentro de su ventana de sellado
([T_ref − 60 min, T_ref)); si ninguno está en ventana no lee la base ni corre el filtro. σ_ε, ρ_ε y c_inf salen de `psi_r` del artefacto
(como en `muestra_union`); el formato (mejor de, set decisivo) sale de la exportación, no de una suposición. Se aplica la capa de edad si
el artefacto la trae (`docs/tenis_capa_edad_20261117.md`). Las entradas selladas añaden formato, `prior_ranking`, `historia_corta`,
`fatiga_desconocida` y `fuente_pi`.

**Sin pronóstico, no se sella.** Si el partido no se puede pronosticar (jugador sin historia ni ranking, superficie o formato
desconocido, fuera de la exportación, jugadores que no coinciden, π o Ŝ no finitos, sin parámetros del circuito), el motor devuelve
`omitido_sin_modelo` con el motivo y emite alerta (`jugador_sin_historia` o `sin_pronostico`). Si la inferencia entera falla, alerta
`inferencia_fallida` y no sella nada en esa pasada; la siguiente la reintenta. Nunca hay valores por omisión (plan D.6).

## Verificación con datos reales

Base local `tenis_dev` (la misma de la exportación del 5-nov): `conjunto_desde_db` produce 260.165 partidos, 260.165 eventos y 421.864 filas
de estadísticas, con las mismas claves que los ficheros de la exportación. Con el artefacto `hiperparametros_capa_edad.json`, π de
`pronosticar_circuito` frente a `evaluacion_filas.parquet` (walk-forward oficial):

| | partidos comparados | máx \|Δπ\| | media \|Δπ\| |
|---|---|---|---|
| WTA ≤ 2024 | 14.183 de 14.183 | 0,0 | 0,0 |
| ATP ≤ 2024 | 46.558 de 46.558 | 0,0 | 0,0 |

(Sin la ventana desde 2005 la diferencia era de hasta 0,045: así se detectó.)

## Pruebas

`test_inferencia.py`: el filtro del motor coincide con `filtrar` en un mundo sintético; orientación de lados; motivos de omisión; base de datos real con ranking
como prior, favorito en el lado 2 y jugador sin historia; pasada del motor (una sola inferencia, omisión sin historia, nada en ventana ⇒ nada se
infiere). `test_motor_alertas_salud.py` y `test_capa_edad_motor.py` ahora ejercitan el flujo completo (no valores de demostración).
También se corrigió `exportar_pit.construir`: con una base sin ninguna fecha de nacimiento la resta de edades fallaba (columna vacía de
tipo object); no cambia el caso normal.

## Coste y límites

- Una inferencia lee la base entera: ≈ 133 s de lectura y conversión + 31 s (WTA) y 80 s (ATP) de filtro en este equipo con 260.000 partidos.
  Solo ocurre cuando hay partidos en ventana; con el cron horario son dos o tres minutos por pasada. Si molesta, el siguiente paso es el
  estado del filtro en Parquet (`tenis_estado_<circuito>_<fecha>.parquet`, plan H.2), que hoy NO existe.
- Orden de `jugador_1`/`jugador_2`: la base exige id menor primero; el resultado se devuelve siempre desde `partido.jugador_1`.
- Falta, para sellar de verdad: registrar `hiperparametros_capa_edad.json` (o el original) como `artefacto_activo` con una `version_modelo`
  nueva, y un ensayo del motor contra la base de producción cuando se cargue (hoy la base `tenis` real no tiene datos cargados).
