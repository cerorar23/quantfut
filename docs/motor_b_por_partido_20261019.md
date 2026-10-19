# Motor B y copas europeas: medido por partido (19-oct-2026)

Pedido del titular: arreglar que, en el motor B, totales de goles, ganador y «ambos marcan» «prometen de más», y vigilar el sesgo de
empates en las copas europeas. Lección de los córners el mismo día: **los picks de un mismo partido no son independientes**, así que
todo se mide por partido.

## Motor B por mercado, por partido (todos los picks liquidados de alta probabilidad, base + ampliada)

| Mercado | Picks | Partidos | Prometido | Real | Diferencia | Error estándar por partido | z |
|---|---|---|---|---|---|---|---|
| Totales de goles | 436 | 161 | 77,4 | 75,0 | −2,4 | 2,1 | **−1,2** |
| Ganador (1X2) | 43 | 42 | 72,7 | 65,1 | −7,6 | 7,7 | **−1,0** |
| Córners | 667 | 176 | 75,3 | 73,6 | −1,6 | 2,1 | −0,8 |
| Ambos marcan | 40 | 40 | 66,1 | 62,5 | −3,6 | 7,8 | **−0,5** |
| Marca el local / el visitante | 157 / 125 | 144 / 118 | 79,6 / 76,6 | 79,0 / 79,2 | −0,6 / +2,6 | 3,6 / 3,8 | −0,2 / +0,7 |
| Doble oportunidad | 518 | 243 | 75,8 | 77,4 | +1,7 | 1,7 | +1,0 |
| Hándicap asiático | 714 | 200 | 81,6 | 84,5 | +2,8 | 1,8 | +1,6 |

**Ningún mercado se desvía de forma significativa** (|z| < 1,7). Los −7,6 del ganador y −3,6 de «ambos marcan» son ruido de 40 partidos
(±8 puntos). Los totales tampoco: −2,4 con ±2,1. Las construcciones del B (consenso sin margen y ajuste de lambdas) ya pasaron su
validación de 14.305 partidos de football-data; los picks publicados son demasiado pocos para contradecirla. **No hay nada que corregir
en las probabilidades del B.**

## Copas europeas: los empates

| | Partidos | % empates real | % empates previsto por el modelo (OOS 2025-26) |
|---|---|---|---|
| Champions, toda la historia (2014-2026) | 957 | 20,3 | 21,9 |
| Europa League, toda la historia | 553 | 24,1 | 25,9 |
| Champions 2025-26 | 142 | 18,3 | |
| Europa League 2025-26 | 84 | 11,9 | |

El modelo y Pinnacle esperaban lo mismo en 2025-26 (24,9 % en Europa League) y salió una temporada baja; entre temporadas la frecuencia real
de empates en Europa League va de 11,9 % a 44,4 % con 31 a 84 partidos, es decir, lo que se espera por azar. Frente al historial
de 20,3 % y 24,1 % el modelo no tiene un sesgo. **No se toca.** Se revisa con medio centenar más de partidos por temporada.

## Lo que sí estaba mal: el control mide picks como si fueran independientes

`alta_prob.control()` puede **bloquear un grupo de mercados** con la regla de «fallo grosero» (z ≤ −4 con n ≥ 50). Su z suponía picks
independientes. Un partido genera hasta 4 picks de córners y la ampliada tiene **2.420 picks en solo 222 partidos** (≈ 11 por partido):
la varianza real es mayor, así que un mismo ruido pasaba por «fallo grosero» mucho más a menudo de lo previsto (con picks
correlacionados por 1,4, un z de −4 equivale a −2,8 reales: ~80 veces más bloqueos falsos). El segundo criterio (IC99 remuestreando
semanas) ya agrupaba.

**Corrección** (`alta_prob._varianza`): con `match_id` el z usa la varianza por partido, Σ_partidos(Σ_picks diff)², y se toma la **mayor**
de ella y de la independiente: solo puede volver el bloqueo más prudente, nunca más estricto. Sin `match_id` (llamadas antiguas) es la
de siempre. Las consultas de liquidados (`alta_prob_datos`, `alta_prob_ext`) ahora traen el partido.

Hoy no cambia ninguna decisión: ningún grupo está cerca de bloquearse (todos |z| ≤ 2 con las dos fórmulas). Evita bloqueos falsos futuros.

**Reporte:** el historial de `/alta-probabilidad` (y la tabla de la web) muestra ahora, por mercado, los **partidos distintos** y el margen
de error por partido (`partidos`, `margen_ee`; campos nuevos, el resto del formato no cambia).

## Qué queda del B

El valor del B no está en recalibrar probabilidades (están bien), sino en el **precio**: elegir con el precio en cuenta y los picks de valor
(CLV ≈ +3 %). Eso depende de la puerta comercial y de tu decisión de encenderlos.
