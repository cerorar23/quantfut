# NBA v2 — Sprint 3: núcleo del marcador y mercados de equipo (2026-11-02)

Biblioteca `nba.v2.nucleo` y `nba.v2.mercados`; evaluación reproducible con `apps/nba/ops/evaluar_s3.py` sobre CSV exportados de `nba_datos`.
Prueba hacia adelante en 2025-26 (1.278 partidos; 1.113–1.269 con cierre de bet365 según el mercado). Parámetros, desviaciones y
pesos se ajustaron solo con 2021-22 a 2024-25.

## Qué se construyó

- **Ratings de equipo** (ataque y defensa por equipo, nivel de liga y localía), actualizados partido a partido con el error de puntos; al
  empezar una temporada se conserva el 65 % del rating. Parámetros elegidos por rejilla en las dos últimas temporadas de ajuste:
  tasa 0,045, arrastre 0,65, tasa del nivel de liga 0,01 (la anotación sube cada año; con 0,002 el total iba retrasado).
- **Descanso:** jugar en la noche siguiente a otro partido cuesta ≈ 2,8 puntos de margen por equipo (local −2,3 ± 0,6; visitante +3,2 ± 0,6; sin
  efecto en el total). Medido en los residuos del ajuste y fijado antes de mirar la prueba. Mejora el RMSE del margen de 14,575 a 14,548: poco, pero
  es un efecto real y los ratings dejan de culpar al equipo cansado.
- **Marcador conjunto:** margen y total normales independientes (σ margen 13,80, σ total 18,46, medidas en el ajuste), 20.000 simulaciones por partido,
  puntos enteros, el empate se resuelve con moneda (prórroga). De UNA sola muestra salen ganador, hándicap, total de partido, total de equipo y
  tramos de margen de victoria (`mercados.py`).

## Resultados 2025-26

| Medida | Modelo | Cierre bet365 | Diferencia |
|---|---|---|---|
| RMSE del margen (1.126 partidos con cierre) | 14,49 | 14,04 | modelo peor |
| RMSE del total | 19,12 | 18,41 | modelo peor |
| Brier del ganador (n 1.269) | 0,2063 | 0,1981 | +0,0083 (IC95 +0,003 a +0,013) |
| Brier de cubrir el hándicap (n 1.126) | 0,2603 | 0,2499 | +0,0104 (IC95 +0,004 a +0,017) |
| Brier de superar el total (n 1.113) | 0,2607 | 0,2500 | +0,0107 (IC95 +0,004 a +0,017) |
| Pendiente de calibración del ganador | 1,04 (intercepto +0,04) | — | calibrado |

- RMSE del modelo solo, todos los partidos: margen 14,55 y total 18,96. La v1.5 midió 14,23 y 19,27: el núcleo nuevo mejora el total y empeora el margen,
  y esa comparación es solo orientativa (la v1.5 usa su propio conjunto de partidos).
- Mezclar la línea del mercado con el modelo: pesos de mínimos cuadrados 0,03 para el modelo y 1,03 para la línea (RMSE 14,03 = el mercado solo). Un núcleo
  que solo mira ratings de equipo **no aporta información que el cierre no tenga ya**; era el resultado esperado y coincide con la v1.5.
- Cubrir el hándicap y superar el total: la pendiente de calibración vale ≈ 0,05 y 0,02. Es lo correcto para un modelo sin ventaja sobre la línea: la
  probabilidad de cubrir sale casi igual para todos los partidos (cerca de 50 %) y no discrimina. No es un fallo de calibración sino falta de señal.

## Compuertas

- **G-coherencia: cumplida.** En 320 partidos (1 de cada 4) se comprobó con la simulación real: hándicap y total monótonos en la línea, ganador = hándicap 0,
  tramos de margen suman 1, over + under = 1. 0 violaciones; 7 pruebas unitarias cubren además el reparto de empates exactos (push) a mitades y la
  cota de Fréchet entre mercados.
- **G-equipo: parcial.** El ganador está calibrado (pendiente 1,04) pero el Brier es peor que el del cierre con intervalo que no cruza 0. La política
  ya decidida (probabilidad calibrada, el mercado solo como referencia) no exige ganarle, pero sí exige no estar peor que la v1.5, y ese Brier no se puede
  comparar punto a punto con el documento de la v1.5 (otro conjunto de partidos). Se cierra en S5, donde la evaluación única mide v1.5, v2 y mercado sobre
  los mismos partidos.

## Qué falta para acercarse al cierre

Lo que mueve una línea de la NBA es quién juega. El S2 ya mide la probabilidad de jugar y los minutos esperados por jugador; el siguiente paso
de este mismo núcleo es reemplazar «rating de equipo» por «rating de equipo con sus jugadores esperados»: ajustar ataque y defensa según los minutos
esperados de los ausentes frente a los habituales. Eso exige la tabla de impacto por jugador (S4 la necesita igual para los props) y la lectura punto en
el tiempo de los partes (`nba.dato_a_las`), que hoy no está conectada a estos módulos.

## Decisiones

- La varianza es constante por ahora; la medida por tramos de total esperado o por tipo de partido queda para cuando haya jugadores en el modelo.
- La normal conjunta es la v2.0 paramétrica acordada (D3); las colas (blowouts) y la asimetría se miden en Fase 4 con Monte Carlo antes de cambiar de familia.
- Las líneas enteras con push se excluyen de las métricas de cobertura (la casa devuelve la apuesta); el modelo las reparte a mitades en `mercados.py`.
