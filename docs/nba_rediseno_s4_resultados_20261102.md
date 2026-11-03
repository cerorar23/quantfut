# NBA v2 — Sprint 4: props de jugador (2026-11-02)

Biblioteca `nba.v2.props`; evaluación reproducible con `apps/nba/ops/evaluar_s4.py`. Prueba hacia adelante en 2025-26 (27.251 jugador-partido),
contra el cierre de The Odds API (FanDuel, y en su defecto DraftKings, BetMGM o BetOnline; línea más equilibrada de la casa; solo líneas con .5).
Tasa, prior por rol, sobredispersión y residuos de minutos se ajustaron solo con temporadas anteriores; (k, decaimiento) con 2023-24 y 2024-25.

## Modelo

Estadística = minutos × tasa por minuto, con conteo binomial negativa:
- **Tasa:** media con decaimiento (0,97 por partido, hasta 30 partidos) encogida hacia la tasa típica de su nivel de minutos esperados con un peso de
  30 minutos de evidencia previa (jerarquía por rol, 6 niveles).
- **Minutos:** muestras de la distribución condicionada a jugar del Sprint 2 (las casas anulan la apuesta si no juega, así que no se necesita P(juega)).
- **Conteo:** sobredispersión medida con minutos reales: puntos 0,22; rebotes 0,012; asistencias 0,049; triples 0,077. La distribución final es la
  mezcla sobre las 25 muestras de minutos, así la incertidumbre de minutos queda dentro de la cuota.

## Resultados 2025-26

| Estadística | MASE vs media de 5 | Cobertura 80 % | Brier modelo / mercado / media de 5 | Log-pérdida modelo / mercado / media de 5 | Brier vs mercado (IC95) |
|---|---|---|---|---|---|
| Puntos (n 17.185) | 0,959 | 80,9 % | 0,2622 / 0,2494 / 0,2742 | 0,722 / 0,692 / 0,763 | +0,0128 [+0,011, +0,015] |
| Rebotes (n 16.837) | 0,952 | 80,9 % | 0,2549 / 0,2468 / 0,2788 | 0,705 / 0,687 / 0,772 | +0,0081 [+0,007, +0,010] |
| Asistencias (n 15.312) | 0,961 | 81,3 % | 0,2535 / 0,2453 / 0,2708 | 0,703 / 0,684 / 0,752 | +0,0082 [+0,007, +0,010] |
| Triples (n 14.948) | 0,961 | 80,5 % | 0,2451 / 0,2417 / 0,2668 | 0,684 / 0,676 / 0,746 | +0,0034 [+0,002, +0,005] |

Sesgo relativo por minutos esperados (menos de 15 / 15-25 / 25 o más): puntos −3,9 / +2,4 / +0,9 %; rebotes −4,6 / +0,6 / −1,0 %; asistencias −3,6 / +1,0 / +2,3 %; triples −1,0 / +3,1 / −0,7 %.

## Compuertas

- **G-props: cumplida.** Cobertura del 80 % entre 80,5 y 81,3 % en las cuatro (antes, con la v1.5: 73 %); MASE entre 0,95 y 0,96 (≤ 1,00); log-pérdida y Brier mejores que la línea base de la media de 5 partidos en todas; sesgo por rango de minutos dentro de ±5 % (el mayor: sobrepredicción de 4-5 % para quien juega menos de 15 minutos).
- **Contra el mercado: no.** Como en el equipo, el cierre es mejor (Brier +0,003 a +0,013, intervalos que no cruzan 0) y la pendiente de calibración del P(más de la línea) es baja (0,09 puntos, 0,26 rebotes, 0,36 asistencias, 0,61 triples): las desviaciones del modelo respecto de 50 % son sobre todo ruido. La política decidida (probabilidad calibrada, mercado solo como referencia) no exige ganarle.
- Cobertura medida con PIT aleatorizado: el PIT de punto medio da cifras falsas en conteos bajos (daba 88 % en triples con la misma distribución).

## Lo que no entró (y por qué)

- Combos (rebotes + asistencias, PRA), dobles, triples dobles y primer anotador: faltan cierres de mercado para evaluarlos (The Odds API solo trae los cuatro mercados base y PropLine acumula combos desde el 23-oct) y necesitan correlaciones entre estadísticas del mismo jugador (cópula gaussiana por rol, ficha 12). Se hacen cuando haya semanas de cierres de PropLine para medirlos.
- Contexto del partido (ritmo esperado del encuentro, rival, compañeros ausentes): la tasa es del jugador sin ajustar por el partido; es la siguiente mejora medible usando el núcleo del marcador (Sprint 3b).
- La correlación con el resultado del equipo (blowouts) queda para el Monte Carlo conjunto de la Fase 4.
