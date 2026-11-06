# Parley v2.1: medición de los topes de cuota por pata (6-nov-2026)

Investigación; no cambia ningún motor, cron, sellado ni publicación. Respalda la política de
`src/qf/publish/parley_v2.py` (`POLITICA` por familia de mercado). Scripts reproducibles en
`scripts/analisis_parley/`. Decisión del usuario: seguir con bet365 donde no hay varias casas.

## Pregunta
Con targets 2.10 / 3.10 / 8.20 / 12.10 (±2 %), mínimo de patas y sin supuesto de +EV, ¿hasta qué cuota
por pata conviene llegar en los targets altos, y qué mercados deben tener techo propio?

## Datos usados (y los que no existen)

| Deporte | Mercados medidos | Casas | Cobertura |
|---|---|---|---|
| Fútbol | 1X2, goles O/U 2.5, hándicap asiático (solo líneas .5) | mejor cuota entre casas (football-data, `Max*`) contra Pinnacle sin margen | 2019-2025, 9 ligas |
| Fútbol | 1X2, 1T 1X2, goles y 1T goles O/U, hándicap y 1T hándicap, córners O/U (solo .5) | solo bet365 (BetsAPI, cuota a 60 min del saque) | ~10.000 partidos, 23 ligas, jul-2023 a oct-2026 |
| Tenis | ganador del partido | mejor cuota contra Pinnacle sin margen | 47.375 partidos, 2015-2026 |
| Tenis | ganador, juegos totales, hándicap de juegos | solo bet365, capturas anteriores al inicio | 20-sep a 25-oct-2026 (≈ 5 semanas) |
| NBA | ganador, hándicap, total de partido, mitad y 1.er cuarto | bet365 (BetsAPI), foto ≥ 60 min antes | 2023-24 a 2025-26 |
| NBA | puntos, rebotes, asistencias, triples de jugador | 7-8 casas de EE. UU., captura a ~30-44 min | 2024-25 y 2025-26 |

**No medibles: no hay precios históricos en el repo ni en el VPS.** Tarjetas, ambos marcan, doble oportunidad,
goles y córners por equipo (solo desde sep/oct-2026, 2-4 casas); córners 1T (sin córners por mitad para
liquidar); tenis con historia larga fuera del ganador; combos de jugador NBA, dobles-dobles, primer canasto
y totales por equipo NBA (desde el 23-oct-2026). Esos mercados conservan el tope 1.80 y se abstienen donde
falte calibración.

## Calibración y coste por pata (cuota máxima entre casas, fútbol y tenis)
Diferencia = acierto real − probabilidad sin margen (pp). Coste = ROI a la cuota de referencia (bet365).

| Mercado | ≤ 2.0 | 2.0–2.5 | 2.5–3.0 |
|---|---|---|---|
| Fútbol 1X2 | +1,3 pp · −3 % | +0,3 pp · −5 % | −0,2 pp · −6 % |
| Fútbol goles O/U 2.5 | +1,0 pp · −3 % | **−1,3 pp · −8 %** | −0,3 pp · −7 % |
| Fútbol hándicap .5 | +0,6 pp · −2 % | −0,7 pp · −4 % | sin muestra |
| Tenis ganador | +0,2 pp · −5 % | +0,8 pp · −4 % | +0,4 pp · −5 % |
| NBA hándicap/total (partido, mitad, cuarto) | 0 pp · −4,5 % | casi no existe | no existe |
| NBA props de jugador (4 mercados) | +0,1 a +0,6 pp · −5 a −6 % | −0,3 a −0,7 pp · −6 a −8 % | **−1,3 a −4,5 pp · −10 a −17 %** |

Solo bet365, 3 temporadas (diferencia · ROI): córners O/U 1.5–1.8 +2,1 pp · −2 %, 1.8–2.1 −0,4 pp · −6 %
(n = 9.808); goles O/U ≈1.9 0 pp · −3,6 %; hándicap ≈1.9 0 pp · −3 %; **1T 1X2 −9 a −11 %** desde 1.8
(n = 29.571); 1T hándicap 1.8–2.1 −7 %. Tenis bet365 (5 semanas, 700-900 partidos por mercado, error ±3 pp o
más): juegos totales, hándicap de juegos y ganador ≈ 1.83; ROI −4 a −16 %.

Los mercados de dos lados con línea .5 (hándicap, total, córners, tenis, NBA) cotizan casi todos a ≈1.91:
no caben en el rango 1.20–1.80 de los targets bajos.

## Simulación diaria (cobertura % / patas medias; tope por pata en targets 8.20 y 12.10)
Búsqueda exacta por partido, una pata por evento, sin repetir eventos entre tickets; hasta 700 días
muestreados por deporte; «todos» = 216 días con fútbol, tenis y NBA.

| Pool | 8.20: 2.0 | 8.20: 2.5 | 8.20: 3.0 | 12.10: 2.0 | 12.10: 2.5 | 12.10: 3.0 |
|---|---|---|---|---|---|---|
| Fútbol (cuota máxima) | 53 / 4,0 | 72 / 3,0 | 75 / 2,8 | 41 / 4,0 | 43 / 3,2 | 47 / 3,0 |
| Tenis | 58 / 4,1 | 66 / 3,2 | 69 / 2,7 | 33 / 5,0 | 40 / 4,0 | 49 / 3,3 |
| NBA partido solo | 33 / 4,0 | 39 / 3,3 | 43 / 3,1 | 5 / 4,4 | 7 / 3,9 | 10 / 3,4 |
| NBA partido + props | 76 / 4,0 | 78 / 3,0 | 79 / 2,9 | 54 / 4,1 | 63 / 3,2 | 65 / 3,0 |
| Todos | 96 / 4,0 | 98 / 3,0 | 98 / 2,5 | 86 / 4,1 | 90 / 3,1 | 92 / 3,0 |
| Fútbol 7 mercados, solo bet365 | 39 / 4,0 | 65 / 3,0 | 68 / 2,4 | 35 / 4,0 | 35 / 3,1 | 43 / 3,0 |

Con una sola casa el coste acumulado del ticket (P·Q − 1) fue −10 a −19 %; mezclando casas, ≈ −1 a 0 %.
El acierto real coincide con la probabilidad esperada dentro del ruido (±2 a 3 pp por celda): ningún tope
muestra descalibración significativa. **No leer el ROI del parley**: la selección favorece cuotas atípicas
y su error es de ±12 a ±20 puntos.

## Mismo partido NBA: producto de marginales (razón conjunta real / producto, IC 95 %)
Local gana + cubre local 1,59 [1,49–1,67]; mismo jugador puntos+triples 1,45 [1,42–1,47]; puntos+rebotes
1,11; rebotes+asistencias 1,07; local gana + Over total 1,05 [0,98–1,13]; local gana + visitante cubre 0,37.
La correlación es real y grande en algunas parejas: multiplicar marginales no vale. Un same-game solo es
ejecutable con distribución conjunta validada y cuota real del paquete.

## Decisiones (qué hace `parley_v2.py`)
- Tope **2.50** en targets 8.20 y 12.10 solo para ganador (1X2, tenis, NBA); **2.10** en líneas (goles,
  hándicap, córners, props). 3.0 no se adopta: solo aporta cobertura en el 12.10 y esas patas son las peor
  calibradas y más caras en props y goles. Lo no medido conserva 1.80; el **1T 1X2 se excluye** (margen 9-11 %).
- Targets bajos: 1.20–1.80; las líneas .5 de dos lados admiten 1.95 (decisión del diseño, no medida al detalle).
- Mejor cuota por contrato entre casas con protección contra cuotas atípicas (mejor oferta descartada si
  supera a la segunda en más de 5 % con ≥ 3 casas): umbral inicial, por calibrar.
- Los cuatro tickets se resuelven a la vez: el orden secuencial reparte la cobertura entre targets sin
  criterio. Haz de 3 por estado y tope por cardinalidad: no se afirma optimalidad global.
- `publicado` solo con probabilidad calibrada e incertidumbre por pata; sin artefacto, `solo_referencia`.

## Errores corregidos durante el análisis
Los CSV de football-data con marca BOM dejaban sin identificador al 19 % de las filas de fútbol; la primera
simulación subestimó la cobertura del fútbol (8.20 a 2.5: 59 % → 72 %; todos 12.10 a 2.5: 76 % → 90 %). Las
tablas de calibración no cambian. Las conclusiones sobre el tope sí se mantienen: el salto grande es de 2.0 a
2.5 (una pata menos) y 3.0 añade poco.

## Límites
- Cuotas máximas entre casas pueden incluir cuotas atípicas o desfasadas; en NBA partido y en bet365 hay una casa.
- Fútbol y tenis históricos sin hora de captura; la simulación usa fechas, no la hora real de decisión.
- Tenis bet365: solo 45 % de las capturas anteriores al inicio y 5 semanas; BetsAPI «prematch» no acredita
  recepción original.
- Props NBA: una captura a ~30-44 min, solo casas de EE. UU.; sin Pinnacle.
- No es un backtest del parley real: no hay calibración 60/20/20, embargo ni versiones congeladas (fase 2).

## Cómo repetirlo
`scripts/analisis_parley/construir_candidatos.py` (fútbol football-data, tenis, NBA y props),
`construir_bet365.py` con las exportaciones de `vps/` (solo lectura del VPS) y `simular_topes.py`
(`python simular_topes.py futbol,tenis,todos 2.0,2.5,3.0 etiqueta`). Salidas en `QF_PARLEY_OUT`.
