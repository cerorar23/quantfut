# Tenis v2, S3 ola 2: modelo (piezas P, R, C) y walk-forward 2019–2024 (5-nov-2026)

Plan §D, §E, §F, §I, §J, §K.2 S3. Código en `apps/tenis/src/tenis/modelo/`, `apps/tenis/ops/{entrenar,evaluar_wf}.py`,
pruebas `apps/tenis/tests/test_modelo_*.py`. Salidas en `data/tennis/rediseno_20261104/modelo_s3/`:
`hiperparametros.json` (tras el parche §3.b `416d4dee…`; antes `0f2d5a52…3d650`, conservado como `_antes_parche`), `predicciones_wf.parquet` (60.741 filas = todos los
partidos pronosticables 2019–2024, 46.558 ATP + 14.183 WTA; 60.058 liquidan y se evalúan; sha256 de contenido `f1703195…`), `evaluacion_wf.json`, `evaluacion_filas.parquet`,
`entrenar.log`, `evaluar_wf.log`. Reserva 2025–2026: no se leyó (filtro de lectura `temporada <= 2024`, con prueba).
Sin red, sin VPS, sin coste. El mercado no entra en ninguna pieza.

## 1. Qué se construyó

| Módulo | Qué hace |
|---|---|
| `datos.py` | Exportación PIT → arrays por circuito; ids → índices internos (claves, nunca rasgos); etiquetas aparte; liquidación §I.3; deduplica resultados repetidos |
| `tabla.py` | Enlace EXACTO M̄_f: tabla de ln M_ε(ρ) con `mezcla.nodos` + `partido.prob_ganar_nodos` (lo mismo que `prob_ganar`), rejilla 0,01 en ±6, spline cúbico; incertidumbre de parámetros como convolución 1-D exacta en ρ (Gauss–Hermite 16/64 nodos); perdedor por simetría L(−ρ) |
| `estado.py`, `prior_ranking.py`, `superficie.py`, `fatiga.py`, `parametros.py` | Estado (θ, d_C, d_G, d_H, d_I) por jugador; paseo + inactividad > 60 d; prior θ₀ = b·(ln rank − ln 100); Ω equicorrelada; κ_Hard ≡ 1; F a 96 h con λ^Δ, faltante ⇒ desconocida; φ = softplus ≥ 0 |
| `rating.py` | Pieza R: eventos en orden de `visible_resultado_utc` con visible < corte, en bloques simultáneos (Woodbury); Newton/Laplace con g, h de la tabla; walkover/retirada no actualizan |
| `puntos.py` | Pieza P: Kalman sobre logits empíricos del saque (α, β con paseo, a/b por superficie, μ_s con paseo, forma del día σ_ε, ρ_ε); entrega Ŝ, σ_ε, ρ_ε, ℓ̄_s |
| `union.py` | Pieza C con `inversion.invertir` y la MISMA Σ_m de R |
| `recalibracion.py`, `linea_base.py`, `evaluacion.py`, `hiperparametros.py` | Platt sin intercepto con temporadas previas; Elo K = 24 por bloques de visibilidad; bootstrap por partido + inversa de la varianza; MV predictiva un paso (L-BFGS-B paralelo) solo con ≤ 2018 |

Error de la tabla frente al simulador exacto: **2,5e-9** (máx., 24 tablas por circuito, puntos fuera de rejilla; objetivo
< 1e-6). Con v > 0 frente a `prob_ganar` con Q = 61: 1,5e-6 (v = 0,12); el Q = 11 por omisión del simulador se desvía
~5e-4 con v = 0,3 (limitación ya documentada en G.5, no defecto nuevo). Unión C en 240 partidos: |π_logrado − π| ≤ 2,9e-10, 0 rechazos.

## 2. Hiperparámetros (≤ 2018, congelados)

P: σ_ε = 0,180 (ATP) / 0,179 (WTA), ρ_ε = −0,68 / −0,73. R: τ_θ = 0,064/√año en ambos; σ_θ0 = 0,090 / 0,059;
κ (Clay, Grass, Indoor) = 1,006, 1,049, 1,115 (ATP) y 0,931, 0,947, 0,866 (WTA); σ_d = 0,058 / 0,053; λ = 0,5 en los
dos (rejilla {0,5; 0,75; 0,9}, diferencias de −ll ≤ 4,3); **φ1 ≈ 2e-6 y 9e-7 (→ 0), φ2 = 0,0097 / 0,0125** por hora
sobre F90 (177 / 130 min ponderados); γ_preGS = −0,039 / −0,076 (encogido); γ_equipos = γ_JJOO = 0 (sin datos: esos
partidos tienen formato desconocido o se excluyen).

## 3. Compuertas (2019–2024, IC95 bootstrap por partido, 2.000 réplicas, 6 orígenes combinados)

| Compuerta | ATP (n = 46.078) | WTA (n = 13.980) |
|---|---|---|
| **G-línea base** (Δ log-loss vs Elo recalibrado) | **−0,0036 [−0,0051; −0,0022] PASA** | **−0,0045 [−0,0068; −0,0022] PASA** |
| Δ Brier vs Elo recalibrado | −0,0020 [−0,0026; −0,0014] | −0,0020 [−0,0030; −0,0011] |
| vs Elo / vs Elo+superficie | −0,0053 / −0,0026 | −0,0052 / −0,0071 |
| **G-calibración** pendiente; intercepto | **0,796 [0,771; 0,821] FALLA**; −0,007 [−0,025; 0,013] | **0,876 [0,833; 0,920] FALLA**; −0,008 [−0,044; 0,028] |
| (Elo recalibrado, misma prueba) | 0,883 [0,857; 0,911] (también falla) | 1,033 [0,980; 1,082] |
| G-recalibración (capa − sin capa) | −0,0027 [−0,0032; −0,0021] | −0,0010 [−0,0019; −0,0001] |
| G-cordura (Brier mínimo, n ≥ 500) | 0,223 PASA | 0,211 PASA |
| No-fuga (último evento aplicado < corte) | 0 de 160.804 | 0 de 48.535 |
| Reproducibilidad (sha256 de dos corridas) | idéntico | idéntico |

Log-loss del modelo: ATP 0,6391 (Elo rec. 0,6429), WTA 0,6232 (0,6279). Partidos omitidos 2019–2024 (contados):
ATP equipos/JJOO/excluidos 1.511, formato desconocido 1.408, sin historia ni ranking 254, superficie desconocida 186;
WTA 1.266 / 290 / 520 / 0.

**G-calibración falla en los dos circuitos: el modelo está sobreconfiado.** Según el protocolo NO se arregla con la capa
(aunque su compuerta pasa, `pi_lado1` se entrega SIN capa) y se para aquí. Diagnóstico de la causa raíz:
1. La pendiente de Platt ajustada en 2012–2018, **dentro** de la ventana de máxima verosimilitud, ya es 0,84–0,87: la
   sobreconfianza es estructural, no deriva. El modelo no tiene un grado de libertad de «escala» que la MV pueda mover:
   el enlace M̄_f queda fijado por la forma del día de P (σ_ε, ρ_ε estimados con puntos de saque), y la dispersión de
   los resultados es mayor que la que esa Σ_ε explica (heterogeneidad del partido que no se ve en el saque, aproximación
   de campo medio del filtro que infravalora V al descartar covarianzas cruzadas).
2. Dónde: partidos igualados (π ∈ (0,5; 0,6]: pendiente 0,69 ATP / 0,74 WTA), Challenger (0,74), R32 (0,75); en cambio
   GS 1,01, mejor de 5 1,03 y prior=ranking 1,13–1,42 (infraconfiado).
3. Corrección propuesta (parche atómico, para la próxima ola, con prueba de regresión): una varianza extra del partido
   en R, σ_R² sumada a v en el enlace y estimada por MV con ≤ 2018 (o Σ_ε de R estimada en R y no tomada de P),
   por circuito y quizá por nivel (Challenger/gira). No la apliqué: exigiría reentrenar y la orden fue parar.

### 3.b Parche G-calibración (6-nov, aprobado por el titular): σ_R² del partido en el enlace

Implementación: Σ_m += σ_R²·[[1,−1],[−1,1]] en la verosimilitud y en la predicción (`tabla.convolucionar`, convolución
1-D exacta; frente al simulador con Q = 61 < 1e-6); σ_R por circuito por MV con ≤ 2018 y el resto CONGELADO
(`entrenar.py --parche-sigma-r`), después un reajuste corto de todo (4 iteraciones) y σ_R de cada ablación. JSON
anterior en `hiperparametros_antes_parche.json`; nuevo `hiperparametros.json` sha256 `416d4dee…54e5ec`; predicciones
nuevas sha256 `38788d22…` (antes `f1703195…`; antes y después en `*_antes_parche.*`). Pruebas `test_modelo_parche.py`:
σ_R = 0 reproduce bit a bit el sha256 WTA anterior; σ_R = 0,15 sube la pendiente de Platt 2012–2018.

| Compuerta (2019–2024) | ATP antes → después | WTA antes → después |
|---|---|---|
| σ_R estimada (MV ≤ 2018) | — → **0,0010** | — → **0,0036** |
| G-línea base Δ vs Elo rec. | −0,0036 [−0,0051; −0,0022] → igual | −0,0045 [−0,0068; −0,0022] → −0,0045 [−0,0068; −0,0021] |
| G-calibración pendiente | 0,796 [0,771; 0,821] → 0,797 [0,772; 0,821] **FALLA** | 0,876 [0,833; 0,920] → 0,876 [0,832; 0,919] **FALLA** |
| G-recalibración | −0,0027 → −0,0026 | −0,0010 → −0,0010 |
| G-cordura (Brier mín.) | 0,223 → 0,223 | 0,211 → 0,211 |
| No-fuga / reproducibilidad / unión C | 0 / sha idéntico / ≤ 3,1e-10 | 0 / sha idéntico / ≤ 2,9e-10 |
| Ablaciones superficie / fatiga | −0,0033 / +0,0002 (sin cambio) | −0,0017 / −0,0003 (sin cambio) |

Variante registrada Challenger/gira (ATP): σ_R gira 0,000 y Challenger 0,046; 2Δll = 0,98 < 3,84 ⇒ **no justificada**
(en 2019–2024: pendiente 0,798, Δ −0,00005). WTA no tiene Challenger en TML.

**Causa raíz (diagnóstico con los mismos estados, solo ≤ 2018):** la MV rechaza σ_R porque, al entrar en la
verosimilitud, también frena las actualizaciones, y las ganancias del filtro ya están en su óptimo. La sobreconfianza
no es ruido del partido: es que la **varianza predictiva de las medias está infravalorada**. Recalculando π con los
mismos (ρ, v) de 2012–2018: v mediana 0,008–0,009; v + 0,02 solo en la predicción ⇒ pendiente de Platt 0,854 → 0,994
(WTA) y 0,867 → 1,000 (ATP) y log-loss −0,0016 en ambos; v·4 ⇒ 1,04–1,07. El filtro (Laplace de un paso, campo medio
sin covarianzas cruzadas entre jugadores, d por superficie) estima V ~3 veces menor que el error real de θ. Según la
orden, **paro aquí sin aplicar la capa**. Corrección propuesta (siguiente parche, a aprobar): corregir V y no la
observación, con un factor de inflación de la varianza predictiva estimado con ≤ 2018 (o un filtro con covarianza
cruzada/EP). Habría que declarar que la verosimilitud de las actualizaciones y la predicción dejan de usar la misma Σ.

## 4. Ablaciones (informes; Δ = completo − ablación, mismas temporadas)

| | ATP | WTA |
|---|---|---|
| G-superficie global | −0,0033 [−0,0043; −0,0024] | −0,0017 [−0,0030; −0,0004] |
| Tierra / Hierba / Dura / Indoor | −0,0043 / −0,0051 [−0,0107; 0,0005] / −0,0027 / +0,0011 (n.s.) | −0,0039 / −0,0049 (n.s.) / +0,0001 / — |
| G-fatiga global | +0,0002 [0,0000; 0,0003] | −0,0003 [−0,0005; 0,0000] |
| G-fatiga segmento F > F90 (n 10.115 / 3.731) | +0,0006 [−0,0002; 0,0013] | −0,0011 [−0,0021; −0,0001] |

La superficie aporta en los dos circuitos (sobre todo tierra; hierba sin IC concluyente; Indoor ATP neutro). La fatiga:
φ1 → 0 por sí sola; solo queda la bisagra; efecto nulo en ATP y una mejora pequeña en el extremo WTA. **No validada**
(se publica así). Ninguna ablación empeora más de +0,001 con IC, así que no se tocan escalas.

## 5. Dónde falla (Δ vs Elo recalibrado)

Gana con IC en GS (ATP −0,0115), mejor de 5 (−0,0140), primeras rondas R128/R64, prior=ranking (−0,064 ATP, −0,063
WTA) y < 20 partidos WTA (−0,012). No gana con IC en: Challenger ATP (−0,0014 [−0,0034; 0,0006]), Indoor ATP (+0,0008),
semifinales/finales y Q3, favoritos ≥ 0,7 (Δ ≈ 0) y < 20 partidos ATP. Fatiga desconocida: 2,8 % ATP, 1,9 % WTA.

## 6. Supuestos y desviaciones declarados

- Ψ ajustado una sola vez con ≤ 2018 (no por origen como el plan §J); recalibraciones con temporadas 2012..T−1 (las
  ≤ 2018 están dentro de la ventana de MV). Embargo: el último dato de ajuste es de 2018 y el primer corte de 2019 es posterior.
- Fin de un partido previo = su `visible_resultado_utc` (en TML, fin conservador de la ronda): Δ de la fatiga aproximado;
  no validado contra SofaScore (pendiente). Minutos faltantes: fatiga desconocida ⇒ término omitido y marcado (no 0).
- ℓ̄_s fijo (media de μ_s en 2007–2018), sin ζ (tierra bajo techo); indoor desconocido = superficie base (55,6 %).
- Ω equicorrelada (1 parámetro) en lugar de LKJ; P en campo medio y sin ranking en su prior; P sin ablación (solo afecta a Ŝ, S4).
- Prior por ranking: un jugador nuevo toma el rank del primer partido en orden (corte, clave).
- Margen en juegos (ω), efecto por set y G-cierre: fuera de S3. La comparación del Elo con el cierre de la auditoría no se rehízo (requiere mercado).

## 7. Defectos encontrados en paquetes ya hechos

- **Exportación** (`estadisticas_saque.parquet`): 15 filas de SofaScore 2023–2026 con `puntos_saque_ganados >
  puntos_saque` (p. ej. `T189738S498267` lado 1: 76 de 60). La pieza P las descarta con el partido; el cargador o el
  contrato de S2 deberían rechazarlas.
- Simulador: con `cov_parametros` grande (v ≥ 0,3) el Q = 11 por omisión se desvía ~5e-4 (ya listado en G.5 como
  pendiente: Q no sube solo).
