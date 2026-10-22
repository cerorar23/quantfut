# Auditoría de los tres motores contra la literatura y con datos (21-oct-2026)

Pregunta del titular: ¿están bien construidos los motores A, B y C? ¿Tienen errores? ¿Qué los haría **más exactos**? El objetivo
es la exactitud del pronóstico, no batir al mercado. Todo lo de este documento es **solo lectura**: no se cambió nada en
producción. Las cifras salen de:
- el walk-forward ampliado (11.920 partidos, 2024-01 → 2026-10);
- un barrido nuevo de 16 configuraciones sobre esos mismos partidos;
- 17.614 partidos de football-data con cierre de Pinnacle;
- la base de producción.

Los scripts están en el scratchpad de la sesión. Los artefactos están en `/srv/quantfut/artifacts/audit/`.

## Resumen

| # | Motor | Hallazgo | Gravedad | Efecto medido |
|---|---|---|---|---|
| A1 | A | El ajuste **no converge**: L-BFGS-B se detiene por el tope de evaluaciones (`success=False`, 367 iteraciones, 23 min) porque el gradiente se calcula por diferencias finitas sobre 776 parámetros | crítico | con gradiente analítico: 3-14 s y convergencia |
| A2 | A | La suma cero por liga incluye **equipos sin datos** (91 con muestra efectiva < 1). El optimizador los usa de holgura y quedan con fuerzas extremas (ataque de hasta ±2,4). Un equipo que vuelve (Hull, Coventry, Cambuur) hereda ese valor | crítico | partidos con un equipo poco conocido: RPS 0,233 → 0,214 (mercado 0,195) |
| A3 | A | El ridge queda diluido por la normalización de los pesos: 0,02 equivale a ~0,001 partidos. En la práctica **no encoge nada** | alto | incluido en c4 |
| A4 | A | La media vida de 180 días nunca se midió (`tune_halflife` existe pero nadie la llama). Lo óptimo es **270 días** | alto | ΔRPS −0,00067 [−0,00118, −0,00016] |
| A5 | A | El calibrador se ajusta solo con el log-loss del 1X2, que no identifica el nivel de goles: baja μ a 1,116 (real 1,233) y deja el «más de 2,5» **4,3 puntos por debajo** de lo real. Fuera de muestra **empeora** el 1X2 | alto | ver tabla de c4 |
| A6 | A | Estructura de marcadores: sobra 0-0 (8,3 % contra 6,9 % real) y falta 2-2 (4,6 % contra 5,9 %); τ de Dixon-Coles solo toca 4 casillas | medio | inflar la diagonal: log-loss del 1X2 −0,0005 |
| A7 | A | El xG mezcla proveedores con escalas distintas (PitchAPI 0,93-0,97 del gol real, FotMob 0,97-1,01, API-Football 0,96) | medio | explica parte del −2 % de goles |
| A8 | A (app) | La agenda de la app muestra el 1X2 del A **también** para equipos que el modelo no conoce (21 de 406 predicciones; p. ej. Coventry local 7,7 % contra 30 % del mercado) | alto (visible) | — |
| B1 | B | De-vig de Shin: correcto. Empata con potencia y aditivo y supera al multiplicativo | ok | — |
| B2 | B | Mercados derivados del anclaje: «ambos marcan» −2 puntos, «local gana por 2+» +2,1 puntos, y en el 79 % de los partidos DC no reproduce a la vez el 1X2 y el total. Los picks publicados no se ven afectados (cada línea pasó su prueba), pero sí la lista de mercados | medio | Poisson bivariado probado: peor en conjunto |
| C1 | C | Córners totales bien calibrados; añadir contexto no aporta | ok | Δlog-verosimilitud +0,0002 |
| C2 | C | Córners **por equipo**: no se usa quién domina el partido | alto | **+0,04 nats/partido** |
| C3 | C | Tarjetas: no se usa lo igualado del partido; prometen algo de más | medio | +0,0097 nats/partido (10× lo del árbitro); Brier mejor en las 3 líneas |
| Q | — | «Cuántico» | — | no hay evidencia (ver §Q) |

**Mejor configuración del A (c4).** Gradiente analítico, suma cero ponderada por muestra efectiva, ridge en partidos
equivalentes (0,5) y media vida de 270 días. Sobre los 11.920 partidos:
- RPS 0,20437 → 0,20353 (−0,00084, IC95 [−0,00137, −0,00031]).
- Log-loss −0,0054.
- Las predicciones de más del 85 % pasan de 138 (89 % prometido, 80,7 % real) a 69 (87,7 % prometido, 84,1 % real).

En la ventana reciente (4.779 partidos desde sep-2025), contra la cadena actual (ajuste + calibrador del 1X2):
- RPS del 1X2: de 0,20684 a 0,20493.
- Log-loss de más/menos 2,5: de 0,6872 a 0,6765.
- Log-loss de ambos marcan: de 0,6970 a 0,6849.

La brecha con Pinnacle baja de +0,0071 a +0,0066. **El mercado sigue siendo más exacto.**

---

## A — Modelo propio (Dixon-Coles)

### Qué está bien (coincide con la literatura)
- **Modelo y objetivo.** Dixon-Coles (1997) con decaimiento exponencial, ataque y defensa por equipo, y ventaja de local
  y nivel de goles por liga con encogimiento parcial. Es la familia que la literatura usa de referencia (Ley, Van de Wiele
  y Van Eetvelde, 2019: Poisson bivariado e independiente con decaimiento son los mejores de su comparación).
- **xG como objetivo.** Mezclarlo con cuasi-verosimilitud de Poisson es correcto. La mezcla 0,65 está cerca del óptimo
  (0,8 da lo mismo; 0,5 y 1,0 son peores).
- **Validación.** Walk-forward, puerta contra Elo, RPS y log-loss a la vez. Constantinou y Fenton (2012) defienden el RPS
  y Wheatcroft (2021) el log-loss/ignorancia. Usar los dos es lo prudente.
- **Calibración.** Global razonable: la temperatura óptima del 1X2 es ≈ 1 (0,95-1,03 según la mitad).

### A1 · El ajuste no converge
`DixonColes.fit` llama a `minimize(..., method="L-BFGS-B")` sin gradiente. scipy lo aproxima con una evaluación por
parámetro: 776 evaluaciones de la verosimilitud de 49.541 partidos por cada paso. Con `maxfun=300000` se agota en
**367 iteraciones**. Medido el 21-oct sobre los datos de producción:
- Resultado: `success=False`, «TOTAL NO. OF F AND G EVALUATIONS EXCEEDS LIMIT», 1.384 s.
- Nadie mira `res.success`.

El prototipo `dc_rapido.py` usa la misma función objetivo con su gradiente exacto (verificado contra diferencias finitas:
error relativo 3·10⁻⁸). Ajusta en **3-14 s**. Además de la exactitud, esto hace posibles cosas que hoy no lo son: barrer
hiperparámetros, el reentrenamiento diario y la versión dinámica (§mejoras).

### A2 y A3 · Equipos fantasma, ascendidos y un ridge que no encoge
- La suma cero `SUM_ZERO·media(ataque de la liga)²` promedia **todos** los equipos de la liga, también los que no juegan
  desde hace años. Como su verosimilitud es ~0, sirven de holgura: el optimizador los mueve para cumplir la restricción y
  terminan con valores extremos (91 equipos con muestra efectiva < 1: |ataque| medio 0,55, máximo 2,39).
- El ridge `0,02·Σ ataque²` se suma a una verosimilitud con pesos normalizados por su media. Un partido reciente pesa ~17
  unidades, así que el ridge vale una milésima de partido.
- Resultado: un ascendido con 3-4 partidos se ajusta a esos 3-4 resultados sin freno.

En el walk-forward, Hull-Aston Villa sale 0,1 % / 99,1 %. Producción lo marca `low`/`both_teams_known=false` y lo saca
de los picks, pero **lo sigue mostrando en la agenda de la app** (A8).

Literatura: los modelos jerárquicos (Baio y Blangiardo, 2010) y la práctica con ascendidos (prior del promedio de los
recién ascendidos, o percentil bajo de la liga) encogen hacia una media con fuerza conocida.

La corrección probada:
- suma cero ponderada por la muestra efectiva;
- ridge expresado en «partidos recientes equivalentes».

Partidos con algún equipo con muestra efectiva < 5 (n = 398): RPS 0,2333 → 0,2136. El mercado está en 0,1952, así que
sigue habiendo margen. El siguiente paso natural es un prior específico para ascendidos.

### A4 · Media vida
| media vida | 120 | **180 (prod.)** | 220* | **270*** | 365* |
|---|---|---|---|---|---|
| ΔRPS vs producción | +0,00056 | (r1 −0,00040) | −0,00072 | **−0,00081** | −0,00075 |

\* con suma cero ponderada y ridge 1 (c6, c1, c3).

Ley et al. (2019), con solo goles en la Premier, encuentran el óptimo en 360-480 días. Con xG la información por partido
es mayor y un óptimo algo más corto (270) es coherente.

### A5 · El calibrador
El 1X2 es casi invariante a escalar λ y μ juntos, así que ajustar `a0, b0` solo con el log-loss del 1X2 deja el nivel de
goles sin identificar:
- El calibrador activo (`cal_2026.09.27`) baja μ un 6 %.
- Sobre los 11.920 partidos empeora el RPS (0,20437 → 0,20479) y deja el «más de 2,5» en 0,481 contra 0,524 real.

Medido en la mitad reciente:
- Con el ajuste corregido (c4), **ningún** calibrador del 1X2 mejora el RPS.
- Un ajuste del nivel de goles con la verosimilitud del **marcador exacto** (2 parámetros) mejora más/menos y ambos marcan
  sin tocar el 1X2.

**Recomendación:** retirar el calibrador del 1X2 y, si se mantiene alguno, ajustarlo con la verosimilitud del marcador.

### A6 · Estructura del marcador
Dixon-Coles solo corrige 0-0, 1-0, 0-1 y 1-1. Los datos piden menos 0-0 y más empates con goles (2-2, z = +6,9).

Inflar la diagonal (Karlis y Ntzoufras: Poisson bivariado inflado en la diagonal) se probó como un parámetro más:
- log-loss del 1X2 −0,0005;
- 2-2 de 4,7 % a 5,2 % (real 6,2 %);
- RPS prácticamente igual.

Es una mejora pequeña pero coherente. La alternativa más completa es la cópula con conteos Weibull (Boshnakov, Kharrat y
McHale, 2017), que permite dependencia positiva y negativa.

### A7 · Escalas del xG
Cociente xG/goles por fuente: PitchAPI 0,93-0,97, FotMob 0,97-1,01, API-Football 0,96, FBref 1,01. Con la mezcla al 65 %,
un proveedor que «da menos xG» hunde el nivel de los partidos que cubre.

Corrección: escalar cada fuente a goles por liga y temporada antes de mezclar. Es barato y no toca la regla de punto en el
tiempo.

### A9 · Lo que no cambia
Con todo corregido, el A sigue a +0,0066 de Pinnacle. La mezcla óptima A+mercado tiene peso 0 para el A (0,19569 con w=0,
0,19585 con w=0,10).

**Para el pronóstico más exacto posible en partidos con cuota, la mejor probabilidad es la del mercado sin margen.** El A
aporta sobre todo coherencia entre mercados y cobertura donde no hay cuota.

## B — Mercado (Pinnacle sin margen)

### B1 · De-vig (17.614 cierres de Pinnacle, 8 ligas + Championship)
| método | RPS | log-loss |
|---|---|---|
| multiplicativo | 0,19660 | 0,97215 |
| aditivo | 0,19655 | 0,97190 |
| potencia | 0,19655 | 0,97190 |
| **Shin (prod.)** | 0,19656 | 0,97193 |

El multiplicativo sobreestima las sorpresas (tramo < 10 %: 7,7 % contra 6,7 % real). Shin lo corrige, como describen
Štrumbelj (2014) y Clarke, Kovalchik e Ingram (2017).

Queda un sesgo residual pequeño en favoritos de 65-80 %: real 72,5 %, Shin 71,6 %. Es la zona de alta probabilidad, y
juega a favor de la prudencia.

### B2 · Mercados derivados del anclaje (1X2 + más/menos 2,5 de cierre → λ, μ → resto)
Se probó con 17.548 partidos y ρ = −0,06, que es lo que hace `market_lambdas`. Positivo en z = lo real supera a lo
predicho.

| mercado derivado | predicho | real | z |
|---|---|---|---|
| ambos marcan | 51,1 % | 53,1 % | +5,3 |
| marca el local | 75,5 % | 76,7 % | +3,8 |
| marca el visitante | 68,0 % | 69,7 % | +5,1 |
| local gana por 2 o más | 24,2 % | 22,1 % | **−6,9** |
| visitante gana por 2 o más | 15,2 % | 14,5 % | −2,7 |
| 0-0 | 7,6 % | 6,6 % | −4,7 |
| 2-2 | 4,5 % | 5,3 % | +4,8 |
| más de 1,5 / más de 3,5 | 75,8 / 30,1 % | 76,2 / 29,8 % | +1,1 / −0,9 |

Además, en el **79 %** de los partidos Dixon-Coles no reproduce a la vez el 1X2 y el total del mercado (residuo > 0,002;
mediana 0,0052). El empate que implica el ajuste es 24,6 % y el del mercado 25,1 %.

**Lectura:** el mercado «sabe» lo que dice la literatura: los goles de los dos equipos no son independientes. Por el
estado del partido (el que pierde ataca y el que gana administra) hay más «ambos marcan», menos goleadas y más empates
con goles. Dixon-Coles con ρ < 0 hace lo contrario en el 0-0.

Los productos publicados están protegidos: cada línea habilitada pasó su prueba histórica en el tramo de 80-95 %.
Ninguna de las que se publican hoy sobrepromete. Pero:
- la **lista de mercados del partido** (ligas sin modelo, lambdas ancladas) arrastra estos sesgos de 1-2 puntos;
- los márgenes («gana por 2+») son el punto más débil.

**¿Lo arregla un Poisson bivariado (dependencia positiva)?** Se probó sobre 5.000 partidos al azar, anclando cada
estructura al mismo 1X2 y total de cierre (p/y = predicho/real):

| estructura | log-verosimilitud del marcador | ambos marcan | local por 2+ | 0-0 |
|---|---|---|---|---|
| **DC ρ=−0,06 (prod.)** | **2,8307** | 0,511/0,539 | 0,246/0,221 | 0,076/0,065 |
| DC ρ=0 | 2,8312 | 0,502/0,539 | 0,244/0,221 | 0,070/0,065 |
| bivariado λ₃=0,15 | 2,8350 | 0,527/0,539 | 0,232/0,221 | 0,077/0,065 |
| bivariado λ₃=0,25 | 2,8434 | 0,545/0,539 | 0,223/0,221 | 0,082/0,065 |

El bivariado arregla ambos marcan y las goleadas pero estropea el 0-0, y en conjunto **es peor**. Los datos piden a la
vez menos 0-0, más «ambos marcan» y menos goleadas. Eso es subdispersión en los goles de cada equipo más dependencia
positiva, y la familia Poisson no lo da. Es exactamente lo que modela la cópula con conteos Weibull de Boshnakov,
Kharrat y McHale (2017).

**Recomendación:**
- mantener Dixon-Coles, que es el mejor de lo probado;
- investigar Weibull + cópula;
- mientras tanto, para la lista de mercados, corregir empíricamente cada mercado derivado (calibración por mercado con
  el histórico) o mostrar solo los que pasan la prueba.

### B3 · Alta probabilidad
Ya medido el 19-oct (`docs/motor_b_por_partido_20261019.md`): sin sobrepromesa significativa. No cambia.

## C — Córners y tarjetas

Medido con football-data: 7 ligas, ajuste en 2019-2022 y prueba en 2022/23-2024/25 (6.988 partidos). Como «contexto» se
usó la supremacía del 1X2 y los goles esperados de cierre. Por la decisión de no usar cuotas en el C, en producción se
usarían las λ del **Motor A**, que son información del modelo propio.

| mercado | producción | con contexto |
|---|---|---|
| córners totales (log-verosimilitud/partido) | −2,61663 | −2,61648 (igual) |
| córners del local | −2,43682 | **−2,39555** |
| córners del visitante | −2,29435 | **−2,25669** |
| tarjetas totales | −2,20491 | **−2,19522** |

- **Córners totales:** bien calibrados en las 5 líneas habilitadas. No hace falta tocarlos.
- **Córners por equipo:** el favorito saca más córners (coeficiente de la supremacía 0,45 en escala logarítmica). El
  modelo actual reparte por ataque y defensa medios y lo ignora. Explica la «calibración irregular» anotada el 9-oct.
- **Tarjetas:** más tarjetas cuanto más igualado el partido (coeficiente de |supremacía| −0,22 y de la probabilidad de
  empate +0,60). Dawson, Dobson, Goddard y Wilson (2007) documentan el efecto del árbitro y la diferencia entre local y
  visitante. Lo igualado del partido aporta 10 veces más que el árbitro medido aquí (+0,0011). Producción promete un poco
  de más en «menos de 4,5»: 55,8 % contra 56,8 % real.
- **Nota de método:** los cocientes de ataque y defensa del C no se ajustan por el rival (un solo paso, sin iterar).
  Con priors tan fuertes (120 partidos ficticios en córners) el efecto es pequeño, pero un GLM binomial negativo con
  ataque y defensa conjuntos es lo estándar.

## Q — Sobre «cuántico»

No hay ningún estudio revisado por pares que muestre ventaja de la computación cuántica (ni de la «probabilidad
cuántica») para pronosticar partidos frente a métodos clásicos. Lo que existe son demostraciones de circuitos, patentes y
marketing. El problema de este sistema no es de cómputo (con el gradiente analítico ajusta en segundos) sino de
especificación y datos. No se recomienda invertir ahí.

## Plan recomendado (en orden; cada paso a producción requiere tu confirmación)

1. **Ajuste del A** (A1-A4): gradiente analítico, suma cero ponderada, ridge en partidos equivalentes, media vida 270 y
   `res.success` registrado y exigido. Reentrenar y pasar la puerta de promoción. Cambia predicciones selladas desde el
   día que se active, no las anteriores.
2. **Calibrador** (A5): retirarlo o reajustarlo con la verosimilitud del marcador. Medir más/menos y ambos marcan en la
   puerta, no solo el 1X2.
3. **Agenda de la app** (A8): con `both_teams_known=false`, mostrar el 1X2 del mercado (Motor B) o no mostrar
   porcentaje.
4. **Motor C**: córners por equipo y tarjetas con el contexto del A. Repetir la prueba histórica de líneas antes de
   habilitarlas.
5. **xG por fuente** (A7) e **inflación de la diagonal** (A6).
6. **Investigación**: con ajustes de segundos ya es viable el modelo dinámico (Koopman y Lit, 2015: Poisson bivariado
   con fuerzas que evolucionan en el tiempo) en lugar del decaimiento exponencial, y un prior específico para ascendidos.

## Referencias
- Dixon, M. y Coles, S. (1997). *Modelling association football scores and inefficiencies in the football betting market*. JRSS C.
- Ley, C., Van de Wiele, T. y Van Eetvelde, H. (2019). *Ranking soccer teams on the basis of their current strength*. Statistical Modelling. [arXiv:1705.09575](https://arxiv.org/pdf/1705.09575)
- Karlis, D. y Ntzoufras, I. (2003/2005). Poisson bivariado e inflado en la diagonal; paquete `bivpois`. [JSS v14i10](https://www.jstatsoft.org/index.php/jss/article/view/v014i10/v14i10.pdf)
- Koopman, S. J. y Lit, R. (2015). *A dynamic bivariate Poisson model for analysing and forecasting match results in the English Premier League*. JRSS A 178(1). [RePEc](https://econpapers.repec.org/RePEc:tin:wpaper:20120099)
- Boshnakov, G., Kharrat, T. y McHale, I. (2017). *A bivariate Weibull count model for forecasting association football scores*. IJF 33(2). [IDEAS](https://ideas.repec.org/a/eee/intfor/v33y2017i2p458-466.html)
- Baio, G. y Blangiardo, M. (2010). *Bayesian hierarchical model for the prediction of football results*. J. Applied Statistics.
- Constantinou, A. y Fenton, N. (2012). *Solving the problem of inadequate scoring rules…* JQAS 8(1). [IDEAS](https://ideas.repec.org/a/bpj/jqsprt/v8y2012i1n12.html)
- Wheatcroft, E. (2021). *Evaluating probabilistic forecasts of football matches: the case against the RPS*. JQAS. [arXiv:1908.08980](https://arxiv.org/pdf/1908.08980)
- Štrumbelj, E. (2014). *On determining probability forecasts from betting odds*. IJF.
- Clarke, S., Kovalchik, S. e Ingram, M. (2017). *Adjusting bookmaker's odds to allow for overround*. AJSS 5(6). [PDF](https://researchbank.swinburne.edu.au/file/2069085d-5d5a-4f9c-9f1c-0c52472396cb/1/PDF%20(Published%20version).pdf)
- Egidi, L., Pauli, F. y Torelli, N. (2018). *Combining historical data and bookmakers' odds in modelling football scores*. [arXiv:1802.08848](https://arxiv.org/pdf/1802.08848)
- Walsh, C. y Joshi, A. (2024). *Machine learning for sports betting: should model selection be based on accuracy or calibration?* MLWA 16. [Bath](https://researchportal.bath.ac.uk/en/publications/machine-learning-for-sports-betting-should-model-selection-be-bas/)
- Dawson, P., Dobson, S., Goddard, J. y Wilson, J. (2007). *Are football referees really biased and inconsistent?* JRSS A. [PDF](https://college.holycross.edu/RePEc/spe/DawsonDobson_Referees.pdf)
- Yip et al. (2024). *Forecasting number of corner kicks taken in association football using compound Poisson distribution*. JORS. [arXiv](https://ar5iv.labs.arxiv.org/html/2112.13001)

## Implementación (22-oct-2026, rama `auditoria/motores-20261021`, sin desplegar)

| Paso | Qué cambia | Verificación |
|---|---|---|
| 1 | `model/dixon_coles.py`: gradiente analítico, suma cero ponderada por muestra efectiva, `ridge_partidos` (0,5) y media vida 270 por defecto; `params.converged`; `train.py` no activa un ajuste que no convergió | `tests/test_dixon_coles_ajuste.py` (gradiente contra diferencias finitas a 1e-4, convergencia, fantasmas acotados, ridge invariante al histórico viejo). Walk-forward 2024-01 → 2026-10 con el código nuevo: **ΔRPS −0,00084 [−0,00137, −0,00031]**, idéntico al prototipo; el walk-forward completo tarda 2 min |
| 2 | `model/calibration.py`: el calibrador se ajusta con la verosimilitud del marcador exacto; la puerta exige mejorar el marcador sin empeorar el RPS ni el log-loss del 1X2 | `tests/test_calibration.py`, con una prueba nueva de que identifica el nivel de goles. En el ensayo en seco el calibrador se **rechaza** (calibrar empeora el 1X2 del modelo corregido) y queda la identidad |
| 3 | `api/mobile.py` (agenda y ficha) y `api/partido_mercados.py`: con `both_teams_known=false` se muestra el 1X2 sin margen del mercado guardado en la misma predicción (o nada), la tarjeta de mercado y las lambdas ancladas a Pinnacle | `tests/test_mobile_delivery.py`, `tests/test_partido_mercados.py` |

**Ensayo en seco del reentrenamiento** (mismo flujo que `train_and_register`, sin escribir ni activar):
- El ajuste final converge, con ρ −0,048.
- Validación del último año: Dixon-Coles RPS 0,20328, Elo 0,20404, mercado 0,19449. La puerta promovería (bate a Elo sobre las mismas 2.025 filas); `ready_for_commercial_picks` sigue en falso por el CLV.
- Hull, Coventry y Cambuur pasan a ataques de −0,15 a −0,25, como corresponde a recién ascendidos.

**Para desplegar (requiere confirmación):**
1. Fusionar.
2. Cambiar `DECAY_HALFLIFE_DAYS=180` → `270` en `~/quantfut/.env`; el `.env` fija 180 y pisaría el nuevo valor por defecto.
3. Desplegar worker y API.
4. Reentrenar: `python -m qf.model.train` activa el modelo si pasa la puerta.

Las predicciones ya selladas no cambian.

**Motor C con el contexto del A (sin cuotas)**, medido con las lambdas del walk-forward nuevo sobre 4.404 partidos de
prueba de la base:
- **Córners por equipo:** log-verosimilitud +0,025 (local) y +0,017 (visitante). La mejora se mantiene, a la mitad de
  la que dan las cuotas.
- **Tarjetas:** mixto. La log-verosimilitud empeora 0,004 y el Brier mejora en las tres líneas, así que no se cambia.
  El modelo actual promete menos de lo que pasa en «menos de 4,5» (63,0 % contra 65,6 % real), en la dirección
  prudente.

Los córners por equipo quedan como siguiente paso: cambian el modelo de líneas ya validadas y exigen repetir su prueba
histórica.
