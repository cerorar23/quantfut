# Brecha del motor A con Pinnacle, por momento y por liga (19-oct-2026)

Pregunta (propuesta externa): ¿el A pierde sobre todo porque se compara con el cierre? ¿Le gana a la cuota que la casa tenía
publicada en el momento de predecir? Se midió con el walk-forward del candidato 2026.10.19-131830 (4.255 partidos) y las cuotas
de Pinnacle guardadas en `odds_snapshots`. El A del walk-forward no depende de la hora del día (se reajusta cada 30 días), así que se
compara la misma predicción con el precio de cada momento. La medición es de solo lectura.

## Por momento (RPS; positivo = el A es peor)

| Momento | Partidos | A | Pinnacle | Brecha | IC95 |
|---|---|---|---|---|---|
| T-72 h | 251 | 0,2033 | 0,1921 | +0,0112 | [+0,0038, +0,0193] |
| T-24 h | 290 | 0,2052 | 0,1941 | +0,0112 | [+0,0045, +0,0184] |
| T-6 h | 289 | 0,2056 | 0,1937 | +0,0118 | [+0,0047, +0,0195] |
| T-1 h | 287 | 0,2046 | 0,1919 | +0,0126 | [+0,0058, +0,0201] |
| Once confirmado | 219 | 0,2017 | 0,1868 | +0,0150 | [+0,0067, +0,0240] |
| Cierre | 3.669 | 0,2087 | 0,1999 | +0,0088 | [+0,0066, +0,0111] |

Sobre los **mismos 181 partidos** en todos los momentos: Pinnacle mejora de 0,1855 (T-72 h) a 0,1831 (cierre), solo **0,0024**, y de
0,1845 (T-6 h) a 0,1835 (once confirmado), **0,0010**. La brecha del A es +0,0140 en T-72 h y +0,0164 en el cierre.

**Lectura:** el A no le gana al mercado temprano ni de lejos. La información que llega después de T-72 h explica ~15 % de la brecha;
el 85 % restante ya está en el precio a tres días del partido. Comparar contra el cierre es algo injusto, pero no es la causa principal.
El bloque de impacto por jugador (≈ −0,0005) recupera aproximadamente la mitad de lo que el mercado gana al conocerse el once (0,0010).

## Por liga (cierre; el A es mejor cuanto más negativo)

| Liga | n | Brecha | IC95 |
|---|---|---|---|
| Serie A (Italia) | 272 | +0,0037 | [−0,0041, +0,0117] |
| Bundesliga | 299 | +0,0044 | [−0,0020, +0,0108] |
| Primeira (Portugal) | 208 | +0,0056 | [−0,0059, +0,0182] |
| Eredivisie | 219 | +0,0059 | [−0,0043, +0,0165] |
| Ligue 1 | 299 | +0,0068 | [−0,0002, +0,0146] |
| Primera (Argentina) | 513 | +0,0071 | [+0,0013, +0,0135] |
| Premier League | 372 | +0,0093 | [+0,0022, +0,0170] |
| Champions League | 103 | +0,0097 | [−0,0030, +0,0224] |
| Serie A (Brasil) | 411 | +0,0110 | [+0,0040, +0,0179] |
| LaLiga | 270 | +0,0114 | [+0,0034, +0,0193] |
| Liga MX | 173 | +0,0116 | [+0,0018, +0,0209] |
| MLS | 481 | +0,0142 | [+0,0085, +0,0197] |
| Europa League | 49 | +0,0184 | [−0,0039, +0,0416] |

El A está más cerca del mercado en las ligas europeas medianas (Serie A, Bundesliga, Primeira, Eredivisie: el intervalo incluye el 0) y
más lejos en MLS, Liga MX, Brasil y LaLiga. Es lo contrario de la tesis «las ligas opacas son más ineficientes»: ahí el mercado sabe más
que el modelo, probablemente por viajes, altitud y rotaciones que el A no ve. Los intervalos se solapan: es una tendencia, no una clasificación.

## Qué cambia
- No hay atajo temporal: el A necesita mejorar su nivel base, no solo su momento. Los bloques de contexto aportan décimas de milésima.
- La comparación por liga sugiere dónde probar primero un modelo mejorado (ligas con brecha ≤ 0,006) y dónde el A seguirá detrás.
- La muestra por momento (≈ 250 partidos, solo desde el 24-sep) crece cada día con los snapshots de Pinnacle; conviene repetirla en un mes.
