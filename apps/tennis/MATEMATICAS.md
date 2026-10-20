# Formulación de la primera versión

Esta formulación describe el código ejecutado. Sus aproximaciones y el resultado desfavorable frente a Elo forman parte del modelo, no quedan ocultos por la notación.

## 1. Datos y estimación de saque/resto

Para cada observación de un jugador i que sirve ante j:

\[
Y_r\mid n_r,p_r\sim\operatorname{Binomial}(n_r,p_r),\qquad
\operatorname{logit}(p_r)=\mu+\gamma_s+S_i-R_j+U_{i,s}-V_{j,s}.
\]

`n` es el total de puntos al saque; `Y` es la suma de puntos ganados al primero y segundo. Los aces y dobles faltas forman parte de esos resultados; no se añaden de nuevo a la suma. El número de puntos disputados con segundo servicio es `svpt − 1stIn`, no `svpt`.

`S/R` representan habilidades de saque/resto; `U/V` desviaciones por superficie. Hard es la referencia del efecto de población. ATP y WTA se ajustan por separado. Los priors son gaussianos propios y evitan indeterminaciones de desplazamiento de los efectos; la descomposición es predictiva, no una identificación causal de sus componentes.

Desviaciones típicas fijadas para este candidato: 0,35 en habilidad general, 0,18 en jugador/superficie, 0,25 en superficie poblacional y 0,60 en intercepto. La media del prior del intercepto es logit(0,62) en ATP y logit(0,58) en WTA. Son decisiones de configuración, no constantes universales estimadas por la literatura.

Los efectos generales se ajustan explícitamente cuando hay al menos 300 puntos históricos y los de jugador/superficie con al menos 900. Las celdas restantes usan la población en el ajuste inicial y añaden incertidumbre del prior en la consulta. Esto es una aproximación de la primera versión, no integración completa de todas las celdas latentes dentro del entrenamiento.

La antigüedad produce pesos `w_r = 2^(−d_r/365)`. La función minimizada es:

\[
L(\beta)=\sum_r w_r\{n_r\log(1+e^{x_r^T\beta})-Y_r x_r^T\beta\}
+\tfrac12(\beta-m)^T\Lambda(\beta-m).
\]

Es una verosimilitud de potencia con regularización gaussiana. No equivale a una caminata aleatoria de habilidades ni a un modelo dinámico completo. Para ese modelo harán falta estados por periodo y un proceso de evolución explícito.

El gradiente y la precisión local utilizados son:

\[
\nabla L=X^T\{w\odot(n\odot p-Y)\}+\Lambda(\beta-m),\qquad
H=X^T\operatorname{diag}(w\odot n\odot p\odot(1-p))X+\Lambda.
\]

Se ajusta el MAP mediante L-BFGS y se utiliza la aproximación de Laplace `β ≈ Normal(β_MAP, H⁻¹)`. Para dos vectores de contraste de saque se obtiene conjuntamente la media y covarianza de sus logits. Se añaden las varianzas de efectos no ajustados según sus priors. Al transformar con la función logística, los dos parámetros conservan su dependencia aproximada.

## 2. De punto a juego

Para un servidor cuya probabilidad de ganar un punto es p, sea r = 1−p. La probabilidad de retener con ventaja es:

\[
G(p)=\sum_{k=0}^{2}\binom{3+k}{k}p^4r^k
+20p^3r^3\frac{p^2}{p^2+r^2}.
\]

El primer término suma victorias antes de deuce. El segundo multiplica la probabilidad de alcanzar deuce por la de ganarlo. La fracción resuelve exactamente la repetición de deuce, sin cortar la cola. Con no-ad se sustituye esa fracción por p.

## 3. Tie-break, set y partido

El desempate sigue la secuencia de servicio uno-dos-dos. La recursión acumula estados de marcador hasta las condiciones de absorción. A partir del empate prolongado, cada par de puntos contiene un saque de cada jugador. Si a y b son las probabilidades de que A gane esos dos puntos, la probabilidad de ganar desde empate es:

\[
D=\frac{ab}{ab+(1-a)(1-b)}.
\]

La inversión del orden del par en la siguiente repetición no cambia esos productos. Así se resuelve la cola infinita a 7 o 10 puntos sin una truncación arbitraria.

El estado del set contiene juegos y próximo sacador; el tie-break cuenta como un juego y cambia quién inicia el set siguiente según las reglas. La distribución del partido conserva sets ganados por cada jugador, juegos acumulados, número de desempates, ganador del primer set y continuidad del saque. El primer sacador desconocido se integra con peso 1/2 por opción: es una hipótesis explícita que puede sustituirse cuando se conozca el sacador.

La versión admite mejor de 3/5, juegos con ventaja/no-ad y desempate del set final a 7/10 en 6-6. No se fuerza esa lógica sobre sets de ventaja histórica, sets cortos o super-tie-break que reemplaza al set. La distribución es exacta **condicionada a p, q constantes y a esas reglas**. La realidad deportiva puede incumplir la independencia o constancia de los puntos.

## 4. Mercados e incertidumbre

Cada mercado es una suma de la misma distribución conjunta sobre los estados que cumplen su condición. Por ejemplo, total mayor de 22,5 suma los estados con al menos 23 juegos; un hándicap A −3,5 suma aquellos en que A consigue cuatro juegos más que B.

Para propagar la incertidumbre aproximada se toman muestras conjuntas de logits, se transforman a p/q y se promedian las probabilidades finales:

\[
P(M\mid\mathcal D)\approx\frac1B\sum_{b=1}^B P(M\mid p^{(b)},q^{(b)},\text{reglas}).
\]

El comando de consulta utiliza muestras antitéticas y declara B. Los percentiles describen incertidumbre de parámetros bajo la aproximación, no un porcentaje garantizado de aciertos futuros ni todo el error de especificación.

Para cuota decimal o, las probabilidades de ganar, devolver y perder dan:

\[
EV=p_{ganar}(o-1)-p_{perder},\qquad
o_{justa}=\frac{1-p_{devolver}}{p_{ganar}}.
\]

La diferencia de probabilidades frente al mercado es otra cantidad. Sin una oferta real no se calcula EV de una apuesta real. Los abandonos requieren sus reglas de liquidación y no quedan valorados por una distribución condicionada a partidos completados.

## 5. Protocolo empírico y resultado

Las fechas pueden ser semanas de torneo. El candidato aplica un embargo de 35 días y evita inventar una secuencia a partir de `match_num`. La evaluación es de origen fijo: modelo y Elo se congelan antes de cada año reservado. No representa actualización diaria ni disponibilidad histórica acreditada.

El primer contraste usa log-loss, Brier y acierto; la comparación principal de probabilidades es log-loss. En 2025 y 2026 el candidato no supera al Elo de referencia. Los intervalos de diferencias por periodo son exploratorios: no capturan necesariamente toda la dependencia entre jugadores a lo largo del tiempo ni corrigen por todas las investigaciones futuras.

La evaluación inicial utiliza parámetros MAP; las consultas individuales integran Laplace. Esa diferencia está indicada en cada resultado. Una nueva variante no podrá utilizar el mismo 2026 ya examinado como si fuera una prueba final intacta. Ver `RESULTADOS.md` para los valores realmente obtenidos.

## 6. Conexión de mercados auditada

El marginal de un set numerado conserva los sets ganados y siguiente sacador. Si el partido ya terminó antes de alcanzar ese set, la masa se informa como devolución en el contrato de investigación. Para el segundo set de un partido completo al mejor de 3/5, esa masa es cero. Las reglas de la casa ante retiro siguen siendo una capa separada.

En una línea entera, la normalización de probabilidades implícitas de una pareja de cuotas estima la probabilidad de victoria condicionada a que no haya devolución. La comparación correcta utiliza `p_ganar / (1 − p_devolver)`, además del margen. El retorno esperado usa `p_ganar × (cuota − 1) − p_perder`.

El híbrido Elo–Markov mejora únicamente la probabilidad de ganador mediante una combinación aprendida en escala logit. No pertenece necesariamente a la misma distribución conjunta de juegos/sets que los mercados Markov sin calibrar. El adaptador identifica ambas familias y no presenta coherencia conjunta entre ellas. Antes de optimizar una cartera de apuestas relacionadas se necesita un modelo conjunto calibrado y tratamiento de retiros.
