# Parley NBA de un solo partido, fase 0: dependencia entre patas (2026-11-19)

Solo lectura. Script: `apps/nba/ops/f50_correlaciones_sgp.py`, sobre la exportación `exportar_entrenamiento.sql` de `nba_datos`
(6.863 partidos y 145.843 filas jugador-partido de 2021-22 a 2026-27, bajadas el 19-nov). Salida completa: `informe_f50.json`.

## Método

- **Hacia adelante y con el motor v2:** para cada temporada de prueba (2024-25, 2025-26 y lo jugado de 2026-27), los props se
  predicen como en `evaluar_s4.py` (tasa por minuto, prior por rol, sobredispersión, residuos de minutos y (k, decaimiento)
  ajustados solo con temporadas anteriores). El marcador sale del núcleo de equipo (`e3.recorrer`, ratings previos a cada partido).
  2023-24 no se puede probar: el motor de props necesita dos temporadas previas desde 2022-23.
- Cada pata se pasa a su puntuación normal z = Φ⁻¹(PIT aleatorio). La correlación de esas z es el parámetro de una cópula gaussiana.
- Solo jugadores con ≥ 20 minutos esperados (los que tienen línea en las casas), condicionado a jugar (las casas anulan si no juega).
- «Pata de 75 %»: que la variable supere su cuantil 25 % pronosticado. Se compara la frecuencia conjunta observada con el producto
  (independencia) y con la cópula. Intervalos: bootstrap de Poisson por partido (400 réplicas).

## Resultados (r de las z; IC 95 % en el JSON)

| Par | 2024-25 | 2025-26 | 2026-27 (262 partidos) | Lift 75 % observado | Lift de la cópula |
|---|---|---|---|---|---|
| Margen – total del partido | −0,016 | +0,029 | −0,028 | 0,98–1,02 | 0,99–1,00 |
| Mismo jugador: puntos – triples | +0,608 | +0,581 | +0,574 | 1,10–1,11 | 1,12–1,13 |
| Mismo jugador: puntos – rebotes | +0,284 | +0,280 | +0,307 | 1,05–1,06 | 1,05–1,06 |
| Mismo jugador: puntos – asistencias | +0,191 | +0,198 | +0,232 | 1,03–1,05 | 1,04 |
| Mismo jugador: rebotes – asistencias | +0,198 | +0,206 | +0,232 | 1,03–1,05 | 1,04 |
| Mismo jugador: rebotes/asistencias – triples | +0,09 a +0,11 | | | 1,02–1,04 | 1,02 |
| Titular: puntos – total del partido | +0,167 | +0,154 | +0,142 | 1,02 | 1,03 |
| Titular: rebotes – total del partido | −0,047 | −0,049 | −0,042 | 0,99 | 0,99 |
| Titular: puntos – margen de su equipo | +0,147 | +0,130 | +0,147 | 1,03 | 1,03 |
| Titular: estadística – \|margen real\| (palizas) | −0,06 a −0,15 | | | no lineal | — |
| Compañeros: puntos – asistencias | +0,065 | +0,063 | +0,072 | 1,01 | 1,01 |
| Compañeros: misma estadística | −0,01 a +0,03 | | | ≈ 1,00 | ≈ 1,00 |
| Rivales: misma estadística | 0,00 a +0,02 | | | ≈ 1,00 | ≈ 1,00 |

## Lectura

1. **Estable entre temporadas:** ningún par se mueve más de ≈ 0,03 entre temporadas y los IC se solapan. La compuerta de la fase 0 se cumple.
2. **La cópula gaussiana reproduce la conjunta de patas de 75 %** con un error de ≤ 0,02 en el lift. La excepción es puntos–triples,
   donde exagera un poco (1,12–1,13 frente a 1,10–1,11): conviene contraer su r o probar una t en la fase 1.
3. **Margen y total son independientes** (r ≈ 0): el núcleo puede seguir simulándolos por separado.
4. **El efecto paliza no es lineal:** en los titulares la estadística baja cuando el partido se decide por mucho, sea cual sea el
   ganador. Una cópula lineal sobre el margen no lo recoge; en la fase 1 va como capa de minutos que depende de |margen|.
5. **Magnitud práctica para patas de alta probabilidad:** el lift es pequeño. Dos patas de 75 % (producto 56,3 %) dan como mucho
   ≈ 62 % (puntos + triples del mismo jugador), ≈ 59 % (puntos + rebotes) y ≈ 57,5 % (prop de titular + total). Entre compañeros
   y rivales, prácticamente nada. Los 1,45–1,59 de `parley_topes_medicion_20261106.md` eran con patas de ≈ 50 % y resultados brutos frente a la línea; además,
   «gana + cubre» es la misma variable (margen) y se calcula de forma exacta, no con la cópula.
6. **Hallazgo aparte, más grande que cualquier correlación:** en los jugadores con ≥ 20 minutos esperados, el prop de **puntos** supera
   su cuantil 25 % pronosticado el 79–82 % de las veces, no el 75 %. Las otras tres estadísticas están entre 74 % y 77 %. La cola baja de
   puntos es demasiado ancha: la probabilidad de «más de» en líneas bajas sale conservadora en unos 5 pp. Hay que corregirlo o recalibrarlo
   antes de validar combinaciones (fase 1), porque una conjunta hereda el error de sus marginales.

## Qué implica para el plan

- Fase 1: cópula gaussiana con estas correlaciones por tipo de par (contraídas hacia la media del grupo), las patas sobre la misma variable
  calculadas de forma exacta, la capa de minutos según |margen| y la corrección de la cola baja de puntos.
- Expectativa realista: el modelo conjunto sirve sobre todo para **no equivocarse** al multiplicar (hasta 10 % relativo en un mismo
  jugador). No crea probabilidad: la conjunta alta sigue saliendo de patas de alta probabilidad y pocas patas.
