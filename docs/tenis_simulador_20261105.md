# Tenis v2, S3-A: simulador analítico del partido (5-nov-2026)

Plan técnico §G (G.1–G.7), §D.2–D.4 y §F.3. Código en `apps/tenis/src/tenis/simulador/`, pruebas en
`apps/tenis/tests/test_simulador_*.py` y mediciones con `apps/tenis/ops/medir_simulador.py <modo>`
(modos: `rapido`, `tiempos`, `a26`, `cuadratura`, `mc`, `sens`, `referencia`, `tb_media`, `perfil`).
Sin base de datos, sin red, sin commit.

## 1. Piezas

| Módulo | Qué hace | Método |
|---|---|---|
| `_comun.py` | Valida p: número finito en el intervalo abierto (0, 1). Valida el lado 'A'/'B'. Impide que salga NaN o infinito | — |
| `juego.py` | g(p) (A31 ec. 5). Deuce p²/(p²+q²), sin truncar. 1 − g(p) se calcula como g(q), sin cancelación. Juego sin ventaja g* (A26). Distribución de puntos con la cola declarada. Media y varianza de puntos (T32 Teor. 2.5) | cerrada |
| `tiebreak.py` | Tiebreak a 7 y a 10 con saque ABBA. PD exacta hasta (K−1, K−1) y cola cerrada w_A/(w_A+w_B). P(A) y P(B) se suman cada una desde la misma PD. Distribución de puntos con cola. Media y varianza (T32 Teor. 3.5) | PD + cerrada |
| `set_.py` | Tabla exacta T_σ(marcador) para TB7, TB10, ventaja y súper TB. Quién saca el set siguiente sale de la paridad (G.2). Los juegos al saque se calculan una vez por nodo y sirven para los dos σ | PD + cerrada |
| `formato.py` | `Formato(mejor_de, decisivo)`. Un formato desconocido da `ValueError`; no hay valor por omisión | — |
| `partido.py` | Conjunta exacta set a set, con el saque propagado entre sets. Primer sacador 50/50 | tensorial + producto de matrices |
| `resultado.py` | `DistPartido` y mercados G.4: ganador, 1.er set, sets, hándicaps, totales, tiebreak sí/no y resumen comprimido (s_A, s_B, G_A, G_B, n_TB) | — |
| `mezcla.py` | M̄_f y conjunta mezclada por Gauss–Hermite (Q² nodos, raíz simétrica de Σ). `verificar_cuadratura` es la compuerta G.5 | cuadratura |
| `inversion.py` | δ* por bisección (tolerancia 1e-10 en δ). Rechaza π si no se alcanza con p ∈ [0,02; 0,98] | bisección |
| `sensibilidad.py` | ∂P(ganar), ∂P(1.er set) y ∂E[juegos] respecto de p_A y p_B, con h = 1e-4 | diferencias centrales |
| `montecarlo.py` | Simulador punto a punto vectorizado con semilla fija. Solo verifica | Monte Carlo |
| `salida.py` | Convierte la conjunta en `contratos.salida.DistribucionPartido` | — |

**Formato de un marcador.** Es una tupla de sets `(juegos_a, juegos_b, tiebreak)`, igual que `SetMarcador` del
contrato. Los puntos del tiebreak no entran en la conjunta, porque harían infinito el soporte; los da aparte
`tiebreak.distribucion_tiebreak`. El súper tiebreak en lugar del 3.er set se anota como el set 1-0 con tiebreak
(convención de `db/LEEME.md`) y cuenta como 1 juego en los totales.

**Cómo se calcula la conjunta.** Se guardan los prefijos de sets todavía vivos con un eje «quién saca el set
siguiente», t. Al añadir un set con resultado o, t' = t XOR paridad(o). La masa mezclada de cada extensión es
Σ_{n,t} w_n·a[n,t,P]·T[n,t,o], es decir, un producto de matrices. Solo los prefijos que siguen vivos se expanden
por nodo. El último set normal y el decisivo se calculan juntos para no expandir el prefijo más grande. Las
etiquetas de los marcadores se crean solo cuando se piden (`marcadores()`).

**Set de ventaja.** Se enumeran los marcadores hasta 50 juegos del ganador, el tope de `SetMarcador`. La masa
restante no se tira: va a dos filas «cola» (gana A / gana B), calculadas en forma cerrada geométrica, con
diferencia de juegos exacta (±2), media de juegos exacta y un mínimo. Así P(ganar) es exacta; no hay error de
truncado. Una línea de totales que cae dentro de la cola da error, no una cifra inventada.

## 2. Error frente a la referencia independiente

La referencia está en `test_simulador_referencia.py`. Es una programación dinámica hacia delante, punto a punto,
con los marcadores reales: no colapsa el deuce, no usa ninguna fórmula cerrada y no importa nada del simulador.
El saque alterna juego a juego y el sacador del set siguiente se lee del estado final, no de la paridad. El
partido se compone por recursión sobre las secuencias de sets.

| Pieza | Casos | Error máximo |
|---|---|---|
| Juego, P(gana) | p ∈ {0,02; 0,3; 0,5; 0,65; 0,9; 0,98} | 3,3e-16 |
| Tiebreak 7/10, P(gana) | 8 pares (incl. 0,95/0,95, 0,98/0,02, 0,02/0,02) × 2 sacadores | 3,9e-16 |
| Tiebreak, cada marcador de puntos | ídem | 2,2e-17 |
| Set TB7/TB10/súper TB, cada marcador **y** sacador siguiente | 8 pares × 2 sacadores | 1,2e-14 |
| Set de ventaja con cola cortada en 12 juegos | 3 pares × 2 sacadores | < 1e-13 |
| Cola cerrada de ventaja frente a la referencia sin corte | 0,65/0,62 | < 1e-12 |
| Partido, cada marcador completo (mejor de 3 TB7/TB10/súper; mejor de 5 TB10) | 3 pares por formato + 1 en mejor de 5 | 7,8e-15 |

**Monte Carlo punto a punto** (`montecarlo.py`, semilla fija). Este camino también comprueba la regla del sacador
siguiente, que en Monte Carlo sale sola de alternar el saque. Se probaron 7 casos (incluidos ventaja, súper TB,
Isner a 5 sets y la mezcla, sorteando la forma del día por partido) con N = 60.000 cada uno. Ganador, 1.er set,
6 líneas de totales y los 15 marcadores más probables quedan todos dentro de 4,5 EE.

## 3. Cifras publicadas y del plan

| Cifra | Publicada | Simulador | Estado |
|---|---|---|---|
| g(0,65) (A26) / g*(0,65) / g(0,6) (T32) | 0,830 / 0,800 / 0,736 | 0,82964 / 0,8002 / 0,7357 | ✔ |
| Puntos del juego, p = 0,5 y 0,6 (T32 Tabla 2) | 6,750 y 7,6875 / 6,484 y 6,708 | idénticos al último decimal | ✔ |
| Puntos del TB7, 0,5/0,5 (T32) | 11,744; DE 2,909 | 11,7441; 2,9086 | ✔ |
| Puntos del TB7, 0,9/0,9 (T32 Fig. 5) | 16,07; DE 8,48 | **16,177; DE 8,792** | ✘ no reproducido: la referencia de puntos da exactamente 16,177/8,792. Seguramente la cifra de la figura viene de una simulación |
| Set, 0,60/0,55 (T32 Tabla 7) | 0,66948; 6-1 0,0947/0,0485; 6-2 0,0952/0,1414; 6-3 0,2042/0,1046; 6-4 0,1053/0,2049; P(6-6) 0,138 | todos iguales al 4.º decimal; P(6-6) 0,1383 | ✔ |
| Partido a 5 sets, TB10 en el 5.º (T32) | 0,7948; 3-0 0,300, 3-1 0,298, 3-2 0,197 | 0,79482; 0,3001 / 0,2975 / 0,1972 | ✔ |
| Partido a 5 sets, TB7 en todos (plan G.3) | 0,7943 | 0,79427 | ✔. La diferencia con T32 (0,7948) es el TB10 del 5.º set, no un error |
| A31 Tablas 3-4 (TB7 en todos) | 0,6/0,5: 0,9513 y 0,9079; 0,7/0,6: 0,9380 y 0,8909 | 0,95133 y 0,90784; dentro de 2e-4 | ✔ |
| A26, inversión (Wimbledon, set final con ventaja) | Sampras–Becker 0,598 → 0,6824/0,6663; Graf–Novotna 0,906 → 0,6265/0,5273 | M = 0,59806 y 0,90593; la inversión recupera las p al 4.º decimal | ✔ |
| Plan D.4 | δ* = 0,0311 (0,6561/0,5939); π = 0,700000 | δ* = 0,031080 (0,65608/0,59392); π = 0,7 ± 1e-10 | ✔ |
| Plan D.4, 0,66/0,60 a 3 sets | 0,775 sin efecto del partido, 0,694 con él | 0,774974 / 0,693793 | ✔ |
| Plan G.3, cuadratura (Cholesky) | Q5 0,693873; Q7 0,693789; Q9 0,693792; Q15 0,693793 | idénticas al 1e-6, reconstruyendo los mismos nodos de Cholesky | ✔ |

**K = logit(m5)/logit(m3) es solo un diagnóstico.** Con 0,60/0,55 sale 1,2632, como dice el plan. Sin forma del
día va de 1,252 a 1,338 (media 1,276 en 14 pares); con la forma del día (0,22/−0,45), de 1,086 a 1,107. El valor
√1,4 = 1,183 queda entre ambos. No es una identidad: depende de p y de Σ.

## 4. Cuadratura (plan G.5)

- Uso la raíz **simétrica** de Σ (V·√Λ·Vᵀ), no la de Cholesky. Así la rejilla de nodos es simétrica A↔B: con
  p_A = p_B, M̄ = 0,5 exacto (< 1e-12), y M̄(p_A, p_B) + M̄(p_B, p_A) = 1 sin error de cuadratura. Además
  converge antes: Q9 = 0,6937931839 frente a Q21 = 0,6937932185 (3,5e-8). Con Cholesky el error era 1,3e-6.
- La compuerta máx |Q9 − Q21| se aplica a ganador, 1.er set, tiebreak, totales 12,5–64,5 y hándicap de juegos
  ±12,5, en 6 pares de p:

| Σ (logit) | Mejor de 3 (todas las reglas) | Mejor de 5 |
|---|---|---|
| A26 H: 0,22 / −0,45 | ≤ 2,3e-7 | ≤ 2,7e-6 |
| A26 M: 0,18 / −0,64 | ≤ 3,5e-8 | ≤ 3,5e-7 |
| H + V = diag(0,01) | ≤ 5,6e-7 | ≤ 6,9e-6 |
| 0,30 / −0,45 + V (0,02–0,03) | ≤ 2,8e-5 | **2,6e-4 ✘** (Q = 11 cumple) |
| 0,40 / 0 | ≤ 8,8e-5 | **3,3e-4 ✘** (Q = 11 cumple) |

  Q = 9 basta con Σ realistas. Con una DE total en logit ≥ ~0,33 en mejor de 5 no basta. Hay que correr
  `verificar_cuadratura` en la compuerta y subir a Q = 11 cuando falle; hoy eso **no** es automático.

## 5. Tiempos

Mezcla completa con 81 nodos (Q = 9), primer sacador 50/50 y Σ de A26 (H). Es el mínimo de varias repeticiones.
La máquina estaba compartida con otros agentes y los tiempos variaron hasta ×2–3 entre corridas; doy el rango.

| Formato | P(ganar) | Conjunta mezclada | Marcadores | Dict de etiquetas | Inversión (33 bisecciones) |
|---|---|---|---|---|---|
| Mejor de 3, TB7 | 1,4–4 ms | **2,3–8 ms** | 1.470 | 1–4 ms | 50–180 ms |
| Mejor de 3, TB10 | 2,6–9 ms | 3,4–10 ms | 1.470 | 1–4 ms | 100–370 ms |
| Mejor de 3, ventaja (hasta 50 juegos) | 2,3–6 ms | 7–16 ms | 9.898 | 11–26 ms | 80–210 ms |
| Mejor de 3, súper TB | 2,4–10 ms | 3–13 ms | 294 | < 1 ms | 80–540 ms |
| Mejor de 5, TB10 | 2,7–12 ms | **52–120 ms** | 216.776 | 0,4–1,1 s | 65–570 ms |
| Mejor de 5, ventaja | 1,2–10 ms | 0,35–0,8 s | 1.455.692 | 4–7 s | 80–420 ms |

En mejor de 3 se cumple «decenas de milisegundos». En mejor de 5 la conjunta tarda 50–120 ms, por los 216.776
marcadores. Pasarla a `DistribucionPartido` (pydantic, una entrada por marcador) tarda 10–25 s; para sellar
conviene el resumen comprimido del plan G.4 (`DistPartido.resumen()`).

## 6. Monte Carlo y su error (plan G.5)

- **N = 80.000** por caso. El mínimo teórico del peor caso (p = 0,5) para que el percentil 99 del error sea
  < 0,5 pp es (2,576·0,5/0,005)² = 66.358.
- Se midió con 20 réplicas independientes × 5 casos (mejor de 3 y de 5, con y sin forma del día) × ganador,
  1.er set y 5–6 líneas de totales: 760 comparaciones con el exacto.
  - |error|: mediana 0,104 pp, p95 0,325 pp, **p99 0,432 pp** (meta < 0,5 pp ✔), máximo 0,511 pp.
  - z = error/EE: media 0,07 y DE 0,98 (lo esperado es 0 y 1). La fracción con |z| > 2,576 es 0,92 % (esperado 1 %).
  - Intervalo: con EE ≤ 0,5/√80.000 = 0,177 pp, el p99 teórico del peor caso es 0,455 pp.
- Tiempo: unos 5 s por simulación de 80.000 partidos en mejor de 3 con la máquina cargada. No va en el camino
  del pronóstico: el pronóstico usa la cuadratura.

## 7. Sensibilidad (plan G.7): cuánto mueve 1 pp de saque

Cambio en P(ganar), en pp, por cada +1 pp en p_A (respecto de p_B el signo es el contrario, con magnitud parecida):

| p_A/p_B | Mejor de 3, sin efecto | Mejor de 3, forma del día | Mejor de 5 TB10, sin efecto | Mejor de 5 TB10, forma del día |
|---|---|---|---|---|
| 0,64/0,64 | +4,98 | +3,37 | +6,25 | +3,70 |
| 0,58/0,55 | +4,84 | +3,24 | +5,79 | +3,49 |
| 0,66/0,60 | +3,66 | +2,99 | +3,90 | +3,21 |
| 0,70/0,60 | +2,17 | +2,40 | +1,76 | +2,48 |

- Un error de 1 pp en el punto al saque llega al partido multiplicado por ~5 en mejor de 3 y por ~6 en mejor de 5,
  con jugadores igualados y sin efecto del partido. La forma del día lo amortigua a ×3,4–3,7.
- El 1.er set se mueve 2,1–3,4 pp por pp.
- Juegos totales: con p_A = p_B = 0,64, +0,11 juegos por pp (mejor de 3) y +0,18 (mejor de 5) en cada jugador.
  Con un favorito, subir p_A acorta el partido (−0,07 a −0,72) y subir p_B lo alarga (+0,16 a +1,18).
- La forma del día baja E[juegos]: con 0,64/0,64, de 25,68 a 23,94 a 3 sets. Los partidos se desequilibran más.

## 7.b Pruebas añadidas

| Archivo | Qué cubre |
|---|---|
| `test_simulador_referencia.py` | La referencia independiente y la comparación de cada pieza (juego, tiebreak, set, ventaja, partido a 3 y a 5) |
| `test_simulador_absurdas.py` | p = 0, 1, negativas, > 1, NaN, inf, texto; extremos 0,02/0,98; caso Isner; formato desconocido, un set, súper TB a 5 |
| `test_simulador_propiedades.py` | Masa 1, simetría marcador a marcador, p_A = p_B ⇒ 0,5 exacto, monotonía, neutralidad del saque y las invariantes de A31, física del marcador con el contrato, mercados coherentes, paso al contrato |
| `test_simulador_publicadas.py` | La tabla de la §3, la cuadratura Q9 frente a Q21 y la compuerta |
| `test_simulador_montecarlo.py` | Monte Carlo frente al exacto, semilla reproducible |
| `test_simulador_sensibilidad.py` | La inversión recupera δ a 1e-9; signos y amplificación; derivadas coherentes con `prob_ganar` |

Suite completa `apps/tenis/tests`: **1.554 aprobadas, 10 omitidas, 0 fallidas** (incluye las del simulador).

## 8. Formatos

**Los soporta el simulador:**
- mejor de 3 con el set decisivo a tiebreak a 7 o a 10, de ventaja, o súper tiebreak a 10 en lugar del 3.er set;
- mejor de 5 con el set decisivo a tiebreak a 7 (US Open hasta 2021), a 10 (Grand Slam desde 2022) o de ventaja.

**No los soporta, y da error explícito:** partido a un set, mejor de 2 o 4, sets a 4, Fast4, NextGen y súper TB
en mejor de 5. g* (juego sin ventaja) existe como función pero no forma parte de ningún formato.

**Hoy los acepta el contrato** (`salida.a_contrato`): mejor de 3 con TB7 o TB10 y mejor de 5 con TB10. Rechaza
con su motivo:
- (a) el súper TB, que el plan F.3 deja fuera del sellado;
- (b) el set decisivo de **ventaja**. **Es un fallo del contrato:** `validar_totales` topa el total en 39 juegos
  (mejor de 3) y 65 (mejor de 5), y `SetMarcador` topa el set en 50 juegos. Pero el propio plan G.6 admite sets
  de ventaja, y un 6-7 7-6 14-12 ya pasa de 39;
- (c) mejor de 5 con TB7 en el decisivo, porque el contrato no lo lista aunque existió.

## 9. Supuestos

- Puntos IID condicionados al sacador; p constante durante el partido; alternancia estándar (ABBA en el tiebreak).
- La forma del día es normal bivariante en logit (plan D.2). Los nodos pueden quedar fuera de [0,02; 0,98]; solo
  el centro se limita, y en la inversión.
- Primer sacador desconocido: mezcla 50/50. «A»/«B» solo para verificar; `firstToServe` no se usa.
- El súper TB cuenta como 1 juego en los totales (convención de casas y de `db/LEEME.md`).

## 10. Pendiente o no cumplido

1. `numpy` no figura en `apps/tenis/pyproject.toml`. No era un archivo editable en este encargo; hay que añadirlo.
2. La compuerta de la cuadratura no sube Q sola cuando Q = 9 no basta (mejor de 5 con Σ grande).
3. Conjunta de mejor de 5: se cumplen «decenas de ms» solo con la máquina libre (52 ms); cargada llega a 120 ms.
   Pasarla al contrato con 216.776 entradas es lento: decidir si se sella el resumen comprimido (G.4).
4. T32 Fig. 5 (TB 0,9/0,9) no se reproduce; el valor exacto está comprobado de forma independiente.
5. Falta la segunda comparación de G.7 (método delta frente a cuadratura), porque necesita J·V·Jᵀ del modelo (D.7),
   que todavía no existe. Monte Carlo sobre una incertidumbre no gaussiana (bootstrap de Ψ) no está implementado;
   `simular` acepta Σ gaussiana solo para verificar.
6. Las pruebas de propiedades usan una rejilla determinista porque `hypothesis` no está instalado.
