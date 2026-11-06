# Tenis v2, S3 ola 2: referencia independiente del filtro de rating R (5-nov-2026)

Revisor independiente. Código escrito solo desde el plan (`docs/tenis_plan_tecnico_20261105.md` §D.3, §D.6, §D.7,
§J), la documentación de la exportación (`docs/tenis_exportar_pit_20261105.md` + `manifiesto.json`) y la API
pública del simulador (firmas y docstrings de `tenis.simulador`). **No** se leyó `apps/tenis/src/tenis/modelo/`,
`ops/entrenar.py`, `ops/evaluar_wf.py` ni `docs/tenis_modelo_s3_*.md`. Sin red, sin VPS, sin commit.

| Fichero | Qué es |
|---|---|
| `apps/tenis/ops/referencia_rating.py` | Filtro R de referencia + probabilidad del partido propia (cerrada por sets y punto a punto lenta) |
| `apps/tenis/ops/comparar_referencia.py` | Muestra estratificada + casos límite, ejecución de la referencia y comparación |
| `apps/tenis/tests/test_referencia_rating.py` | 40 pruebas (sin ficheros del otro agente ni base) |
| `data/tennis/rediseno_20261104/referencia_rating/` | `muestra.parquet`, `pred_referencia*.parquet`, `comparacion*` |

## 1. Qué implementa la referencia

- **Probabilidad del partido propia.** `p_partido`: juego en forma cerrada, tiebreak y set por programación
  dinámica por diagonales (A saca primero), partido por combinatoria de sets con el set decisivo según
  `formato_decisivo` (tiebreak_7, tiebreak_10, ventaja, supertiebreak_10). `p_partido_lento`: recorrido punto a
  punto con el sacador explícito, arrastre del sacador entre sets y mezcla 50/50 del primer sacador. Coinciden a
  **1e-12** en 7 formatos × 7 pares (confirma de paso que la probabilidad de un set/tiebreak no depende de quién
  saca primero). Con la API pública del simulador (`prob_ganar`): **1e-13** sin Σ y **1e-9** con Σ y q alto.
- **M̄_f** (`m_barra`): E[P(expit(ℓ̄+ρ+e_A), expit(ℓ̄−ρ+e_B))], e ~ N₂(0, Σ), Gauss–Hermite producto sobre la
  base propia de Σ. Reproduce los valores del plan §D.4 (0,775 / 0,694 / 0,700).
- **Filtro** (`Filtro`): estado por jugador x = (θ, d_Clay, d_Grass, d_Hard, d_Indoor, d^ι) ~ N(m, P) 6×6;
  ρ lineal en el estado (vector g); predicción con Σ_m = Σ_ε + (gᵀVg)·[[1,−1],[−1,1]] (= J V Jᵀ con
  J = (g, −g)); actualización de Laplace/Newton exactamente como la escribe el plan, V⁺ = (V⁻¹ + H)⁻¹ y
  m⁺ = m + V⁺∇ℓ(m), con H = −ℓ''(ρ)·g gᵀ (rango 1, Sherman–Morrison; la prueba lo compara con inversas
  explícitas a 1e-12). ℓ' y ℓ'' por diferencias centrales con extrapolación de Richardson (error O(h⁴),
  comprobado < 1e-10 en el estado al cambiar h).
- Fatiga F = Σ λ^Δ·minutos en 96 h, g₁ = F/60, g₂ = max(0, F − F₉₀)/60, φ_j ≥ 0 validado; contextos z_k como
  multiplicador κ(1 + Σγ_k z_k); ι = tierra con `indoor = True`; retiradas, walkovers y descalificados no
  actualizan pero sus minutos cuentan; jugador sin historia y sin ranking ⇒ sin pronóstico.
- Muestra (`comparar_referencia.elegir_muestra`, semilla 20261105): 2.977 partidos 2019-2024 estratificados por
  circuito × año del corte × superficie (63 por estrato) + 25 por circuito de cada caso límite (sin historia con
  y sin ranking, ≥ 3 años de inactividad, fatiga desconocida, mejor de 5, TB10, supertiebreak, ventaja, tierra bajo
  techo, equipos, semana previa a GS, walkover/retirada) = **3.496** partidos. JJOO: 0 (formato `desconocido`).

## 2. Tolerancia: por qué 1e-6 no es alcanzable sin fijar la cuadratura en Ψ

La especificación dice «M̄_f integrada sobre Σ_m» pero no fija **cómo** se integra. Medido:

| Integración de M̄_f | Error frente a la integral exacta (q = 60, convergida < 1e-9) |
|---|---|
| Referencia, Gauss–Hermite producto en la base propia de Σ, q = 11 (solo Σ_ε) | 6e-7 – 2e-6 |
| Referencia, misma regla, q = 11, con J V Jᵀ (1.443 pronósticos WTA, Ψ de demostración) | media 2e-4, máx **8,1e-3**; 99,4 % > 1e-6 |
| Simulador `prob_ganar`, q = 11 por omisión (mismos 1.443) | media 2,4e-6, máx **5,5e-4**; 22,9 % > 1e-6 |
| Simulador `prob_ganar`, q = 21 | máx 5,8e-6; 0,07 % > 1e-6 |
| Simulador q = 40 frente a referencia q = 60 | ≤ 1e-9 (la física y la mezcla coinciden) |

El error crece con var(ρ) (jugadores nuevos con prior de ranking, mejor de 5): el integrando es una sigmoide
empinada en la dirección (1, −1). Además el registro del otro agente (`modelo_s3/entrenar.log`, solo la cola,
para saber si había terminado) anuncia **tablas** de M̄ con «max_error_con_v_q61 ≈ 1,5e-6»: también interpola.
**Tolerancia justificada**: 1e-6 solo si Ψ congela la regla de integración (tipo, q y tablas) y la referencia
usa la misma; si no, la tolerancia honesta de la predicción es el error de cuadratura del otro lado (~1e-5 típico,
hasta ~5e-4 en partidos con prior) y la comparación se hace contra dos columnas: `pi_ref` (exacta, q = 60) y
`pi_ref_sim_q11` (misma ρ y var(ρ) de la referencia integrada con `prob_ganar` q = 11), que separa «cuadratura»
de «filtro».

## 3. Ambigüedades de la especificación (cada una es un hallazgo)

Resueltas en la referencia como dice `referencia_rating.DECISIONES`; probablemente el otro agente las resolvió
de otra forma. Ninguna está fijada por el plan con precisión suficiente para reproducir a 1e-6.

| # | Hueco | Qué dice el plan | Qué hice | Efecto si difiere |
|---|---|---|---|---|
| A1 | Orden de los eventos | §D.3: «por semana, edición y ronda (previas antes)»; §J y la exportación: `visible_resultado_utc` | `orden` de la exportación (vis); predicción en c ve vis < c | Filtro no conmutativo: otro orden ⇒ otro estado |
| A2 | Desempates con la misma vis | Nada (en TML toda una ronda comparte vis) | El de `orden` | Ídem, pequeño |
| A3 | Reloj del estado (Δt) | «τ_θ²·Δt» sin unidad ni instante | Días; reloj = `corte_utc` del partido; Δt < 0 → 0 | Escala de τ y de la inactividad |
| A4 | Forma del aumento por inactividad | «aumento por inactividad (> 60 días)» | Salto aditivo `inact_var` en Var(θ) si Δt > 60 d | Jugadores que vuelven |
| A5 | ¿Paseo aleatorio de d y de d^ι? | τ_d está en Ψ (§D.8), sin fórmula | τ_d²·Δt en cada d_s y en d^ι | Varianza de superficie |
| A6 | Estructura de V | x = (θ_A, θ_B, d_{A,s}, d_{B,s}) y d_{i,·} ~ N₄(0, Σ_d) con Ω | Estado 6×6 completo por jugador (Ω propaga a las otras superficies; cov θ–d se conserva); cov entre jugadores se descarta | Con Ω ≠ I o cov θ–d distinta: otros d y otra var(ρ) |
| A7 | Σ en la verosimilitud de la actualización | «Esa misma Σ_m se usa en el enlace de R» (§D.7) vs Laplace (V es el prior) | Σ_ε al actualizar; Σ_m = Σ_ε + J V Jᵀ al predecir | Paso de Newton más corto o más largo |
| A8 | Derivadas | «diferencias exactas a través de M̄_f», sin paso | Centrales + Richardson, h = 2e-3 (error < 1e-10) | ~4e-8 por paso con h = 1e-3 sin Richardson |
| A9 | ℓ'' ≥ 0 (no cóncavo) | Nada | c = max(−ℓ'', 0) | Raro |
| A10 | T_ref(m) y fin de cada partido k | «terminados en las 96 h anteriores a T_ref(m)» | T_ref = `inicio_utc` o, sin hora, `corte_utc`; fin_k = inicio + minutos si hay hora, si no `visible_resultado_utc` (TML no tiene hora: su vis es el fin conservador de la ronda) | Mayor fuente probable de diferencia de fatiga |
| A11 | Visibilidad de los minutos | Nada | k cuenta solo si vis_k < corte_m | Partidos del mismo día |
| A12 | Minutos desconocidos | §C.5 no lo dice; la exportación deja NULL | Aportan 0 y marcan `fatiga_desconocida` (se pronostica) | Otro podría excluir o imputar |
| A13 | Walkover | «sus minutos sí cuentan» (retiradas) | Walkover = 0 minutos, no marca desconocida | — |
| A14 | Prior r(·) | «θ₀ = r(puntos)» sin forma | θ₀ = a + b·ln(1 + puntos), var `prior_var` | Toda la historia corta |
| A15 | Jugador con n_prev > 0 sin estado | La exportación empieza en 2005 y n_prev cuenta toda la base | Prior de ranking (o `theta_sin_ranking`) | Calentamiento desde 2005, no desde «el primer año disponible» (§J) |
| A16 | Cuándo nace el estado | Nada | En la primera actualización, con el ranking de ese partido; la predicción sin estado usa un prior temporal | Si nace en la predicción, el filtro depende de la muestra |
| A17 | Jugador sin ranking que juega (actualización) | Solo «no se pronostica» | Prior `theta_sin_ranking` | Rivales de qualies |
| A18 | Formato desconocido / superficie NULL | §F.3: no se sella | Ni pronóstico ni actualización (M̄_f no existe); los minutos sí | 7,5 % de los partidos |
| A19 | Prior de d^ι y papel de ζ | Nada | d^ι ~ N(0, var_d_iota), ζ multiplica | Tierra bajo techo |
| A20 | ι con `indoor` NULL (55,6 %) | Nada | ι = 0 | — |
| A21 | Incertidumbre de P en Σ_m (α, β, μ) | §D.7 la incluye | Solo la de R (ℓ̄ fijo en S3) | var(ρ) menor |
| A22 | Nombre del supertiebreak | Exportación `supertiebreak_10`; simulador `super_tiebreak_10` | Traducción explícita | Error o exclusión silenciosa de la Laver Cup |
| A23 | Duplicados TML/SofaScore no fusionados (205) | La exportación avisa | Se consumen dos veces (como vienen) | Doble actualización |
| A24 | Cuadratura de M̄_f | No fijada | q = 20 al actualizar, q = 60 al predecir | Ver §2 |

## 4. Comparación con el otro agente: NO REALIZADA

A las 18:40 del 5-nov `modelo_s3/` solo tenía `entrenar.log` y `prueba_eval/`: **no existían**
`hiperparametros.json` ni `predicciones_wf.parquet` (el registro mostraba el ajuste de la pieza R de WTA en
curso). Por indicación del coordinador (ahorro) no se esperó más. Ninguna cifra de concordancia está medida.

Prueba de humo de la referencia (Ψ de demostración, NO ajustado; WTA, eventos 2005-2024, 582 s): 1.443
pronósticos de la muestra, log-loss 0,637 (0,693 con 0,5), acierto 63,9 %; 32 sin pronóstico por
`jugador_sin_historia` y 10 por formato desconocido. La ruta de comparación se probó contra sí misma
(`comparacion_autoprueba_demo.json`: 100 % dentro de 1e-6 frente a `pi_ref_sim_q11`).

Para correrla cuando existan los ficheros (≈ 10 min WTA + ≈ 35 min ATP por juego de Ψ):

    correr_script_tenis.ps1 apps/tenis/ops/comparar_referencia.py --hiper <modelo_s3/hiperparametros.json> --pred <modelo_s3/predicciones_wf.parquet> [--n 1500] [--col-pi <columna>]

`hiper_desde_json` traduce por alias (`ALIAS`) y **se niega** a correr si el JSON no trae alguna de las claves que
la especificación necesita (ℓ̄, κ, τ_θ, τ_d, umbral y aumento de inactividad, σ_d, Ω, ζ, var de d^ι, φ, λ, F₉₀,
ventana, γ, σ_ε, ρ_ε, prior a/b/var, θ sin ranking, ω): lo que falte es un hallazgo de especificación (A3-A5,
A14-A19 casi seguro faltarán o tendrán otra forma). Si Ψ es por origen (§J), hay que correr un Ψ por origen.
`comparar` clasifica por marcas (prior, historia corta, fatiga, fatiga desconocida, formato) y separa cuadratura
(`pi_ref_sim_q11`) de filtro.
