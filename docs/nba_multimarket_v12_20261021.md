# NBA — multimercado v1.2 (corrección de la auditoría del 19-oct)

Protocolo congelado antes de correr: `apps/nba/multimarket_v12_protocol.json`. Código: `nba.multimarket_v12`. Resultados: `apps/nba/.local/normalized/nba_f6_v12_20261021/comparison_v12.json`. **RUN071 no se tocó**; v1.2 no sustituye ni publica nada (`actionable=false`).

## Qué cambia respecto a v1.1
- Recalibración móvil: la logística se reajusta cada temporada con las dos temporadas anteriores (nunca antes de 2022-23), en vez de una sola calibración fija de 2022-23.
- Ganador: Elo con multiplicador de margen (fórmula 538) y regresión logística sobre [diferencia Elo, back-to-back local, back-to-back visitante], ventaja local implícita en el intercepto.
- Puntos de equipo y total: ventaja local = media de las dos temporadas previas (antes: 1,72 puntos fijos de 2021-22); desplazamiento por descanso y covarianza reestimados con la ventana de entrenamiento.
- Jugadores: peso empírico elegido solo con 2023-24 entre {0; 0,25; 0,5}. Ganó 0,25 (el actual), así que no cambia.
- Intervalos: bootstrap por fechas (antes por partido).

## Resultado (test 2024-25 y 2025-26; Brier, menor es mejor)
| Mercado | Diferencia vs v1.1 sellado | Lectura |
| --- | --- | --- |
| Ganador | −0,0058 y −0,0057; IC95 excluye 0 en ambas | Mejora real. Sesgo local +3,3 → +1,5 pts y +2,4 → −0,9 pts |
| Puntos de equipo | −0,0009 y +0,0007; IC incluye 0 | Neutro |
| Total del partido | 0,0000 y +0,0005; IC incluye 0 | Neutro |
| Jugadores (6) | entre −0,0002 y +0,00004 | Neutro; triples y robos mejoran un poco |

Frente a v1.1 con solo recalibración móvil, el ganador mejora −0,0042 y −0,0039 (IC excluye 0): el margen en el Elo y el descanso aportan más allá de corregir el sesgo.

## Lo que NO se corrigió (necesita datos que no están)
Lesiones y disponibilidad, cuotas de mercado y CLV, rival/ritmo/local para jugadores, posiciones. Sin cuota de cierre sin margen no hay prueba de ventaja sobre el mercado.

## Límites
Temporadas ya inspeccionadas con v1.1: exploratorio, no confirmatorio. Nueve mercados sin corrección por comparaciones múltiples. Para usar v1.2 en pronósticos prospectivos hay que sellar una cohorte nueva con su propio `evaluate`.
