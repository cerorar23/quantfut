# NBA v2 — Fase 4, F4.0: contratos entre los pasos del motor (2026-11-03)

La Fase 4 empieza por las fronteras, no por los modelos. Marco acordado (adaptación del texto del titular a lo que ya existe): esquemas primero, pruebas con datos extremos y con las salidas reales, evaluación solo hacia adelante, módulos pequeños de una sola responsabilidad, MVP iterativo con entrenamiento local y artefactos versionados en el VPS.

## Qué se escribió (`apps/nba/src/nba/contratos/`, Pydantic estricto, sin lógica de modelo)

| Módulo | Contenido |
|---|---|
| `base.py` | `Contrato` (estricto, inmutable, sin campos de más, sin NaN ni infinitos); tipos con unidades: `Probabilidad`, `Minutos` (0–60), `Hash256`, `Tricode`, `Instante` (con zona horaria), `Cuantiles199` (199 valores no decrecientes) |
| `paso_a.py` | **Paso A, estimadores** (hoy ratings, impacto por jugador, minutos y disponibilidad; la interfaz no presupone el tipo de modelo, así que una red o un boosting podrían entrar como retador): `MinutosSiJuega`, `EstimacionJugador`, `DescansoDias`, `SalidaPasoA` |
| `paso_b.py` | **Paso B, fórmulas analíticas**: de las estimaciones a parámetros de distribuciones (`ParametrosMarcador`, `ParametrosConteo`) en `SalidaPasoB` |
| `paso_c.py` | **Paso C, Monte Carlo**: `EntradaMonteCarlo` (parámetros, simulaciones entre 1.000 y 1.000.000, semilla) y `SalidaMonteCarlo` con `DistribucionEquipo` (199 cuantiles por serie) y `DistribucionJugador` (pmf que suma 1, p10 ≤ p50 ≤ p90 dentro del soporte) |

Las dos distribuciones de salida tienen exactamente la forma del JSON que ya se sella en `nba.pronostico`, así que el mismo contrato valida lo que sale del motor, lo que se sella y lo que lee la API.

## Pruebas (`tests/v2/test_contratos.py`, 52)

Cadena A → B → C válida y ida y vuelta por JSON; ~50 casos absurdos o extremos que deben rechazarse (NaN, infinitos, probabilidades fuera de [0, 1], minutos > 60, cuantiles decrecientes o incompletos, pmf que no suma 1, equipo local igual al visitante, instante sin zona horaria, hash mal formado, simulaciones 0 o 2 millones, semilla negativa, campos extra, jugador y estadística repetidos); extremos válidos que sí deben aceptarse (sin plantilla, probabilidad 0 y 1, minutos 0).
La prueba encontró un hueco de mi propio contrato: `descanso_dias` aceptaba un diccionario al que le faltaba un equipo; ahora es un submodelo con los dos campos obligatorios.

**Conformidad con la realidad:** las salidas reales de `motor_equipo` y `motor_jugadores` y todo lo sellado por el motor en una base de prueba cumplen los contratos; además se validaron los **192 pronósticos sellados hoy en producción** (4 de equipo y 188 de jugador): 192 válidos, 0 inválidos.

## Estado y siguiente paso

- Los contratos **todavía no están conectados** al motor ni a la API (primera tarea: solo esquemas). Conectarlos es el paso siguiente: validar justo antes de sellar y al servir, y agregar `pydantic` a las imágenes `nba-motor` y `nba-captura` (hoy solo está en la de la API). Un contrato que rechace debe registrarse como error y alertar, nunca sellar a medias.
- Los adaptadores que producen `SalidaPasoA` y `SalidaPasoB` desde los módulos actuales (`equipo_jugadores`, `motor_jugadores`) aún no existen: hoy esas salidas son diccionarios internos.

## Resto de la Fase 4

F4.1 evaluación de origen móvil (varias temporadas de prueba, con intervalos); F4.2 Monte Carlo (convergencia con 20.000 simulaciones, semillas y reproducibilidad entre máquinas, y si conviene simular props y equipo de forma conjunta); F4.3 estrés (día de 15 partidos con 30 fuentes caídas, casos extremos y propiedades); F4.4 ensayo operativo (restaurar respaldo, volver a una imagen anterior, detectar una cadena manipulada); F4.5 informe final y propuesta de promoción, con la decisión sobre retirar v1 en manos del titular.
