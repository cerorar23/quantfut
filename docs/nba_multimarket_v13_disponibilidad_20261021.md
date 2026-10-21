# NBA — multimercado v1.3: disponibilidad desde reportes oficiales de lesiones

Protocolo congelado antes de correr: `apps/nba/multimarket_v13_protocol.json`. Código: `nba.availability` y `nba.multimarket_v13`. Resultados: `apps/nba/.local/normalized/nba_f6_v13_20261021/comparison_v13.json`. RUN071 y v1.2 no se tocaron; todo es retrospectivo y `actionable=false`.

## Fuentes (todas ya descargadas, sin gasto)
- 816 reportes oficiales de lesiones de la NBA (2021-10 a 2026-04), ya unidos a IDs NBA.
- Hora de salto: api-sports (2022-23 a 2024-25, unido por fecha este y equipos) y, para 2025-26, la hora que traen los propios reportes. Cobertura de partidos observados: 99,5 % / 99,3 % / 99,3 % / 99,2 % por temporada.
- Regla punto-en-el-tiempo: un estado solo cuenta si el reporte se emitió al menos 60 min antes del salto; gana el último válido. Partido sin hora de salto o sin reporte válido = sin información (no «disponible»).

## Qué muestran los datos
Probabilidad de jugar según el estado (media de las temporadas): Out 0,3 %, Doubtful 2,5-3,3 %, Questionable ~48 %, Probable ~89-90 %. En los jugadores listados, el log-loss de participación baja de 0,64-0,70 (tasa base) a 0,45-0,52 con la tabla de estados. Esto cubre el hueco «sin modelo de disponibilidad / DNP» para quienes aparecen en el reporte.

## Resultado (Brier frente a v1.2; menor es mejor; IC95 por fechas)
| Mercado | 2024-25 | 2025-26 | Lectura |
| --- | --- | --- | --- |
| Ganador | −0,0051 | −0,0043 | Mejora; IC excluye 0 en ambas |
| Puntos de equipo | −0,0017 | −0,0025 | Mejora; IC excluye 0 |
| Total del partido | +0,0002 | +0,0006 | Sin cambio |
| Puntos, rebotes, asistencias, triples, robos de jugador | −0,0004 a −0,0019 | −0,0004 a −0,0019 | Mejora pequeña; IC excluye 0 |
| Tapones | 0,0000 | −0,0001 | Sin cambio |

Acumulado desde la v1.1 sellada: el ganador baja ~0,011 de Brier en las temporadas de prueba y el sesgo local queda cerca de 0. Los jugadores usan lesión propia (jugó siendo dudoso rinde menos) y minutos esperados perdidos por compañeros (más oportunidad: coeficiente positivo en puntos y rebotes).

## Límites que importan
- La recepción de cada reporte es retrospectiva: no prueba que estuviera disponible a esa hora. Los reportes vespertinos pueden faltar; las bajas de última hora no se capturan.
- Un jugador sin fila en el reporte se trata como sin información de lesión, no como confirmado sano. «Available» juega solo 68-75 %: puede haber DNP técnico o identidades dudosas; no se interpretó.
- Sigue siendo exploratorio: las temporadas ya se inspeccionaron con v1.1/v1.2 y hay muchos mercados sin corrección por comparaciones múltiples.
- **Cuotas de mercado y CLV siguen sin resolverse.** No hay históricos de cuotas de partido en los repos ya usados (ESPN no devuelve líneas históricas; los CSV de props son muestras sin partido). The Odds API sí los tiene (10 créditos por snapshot), pero el saldo real es 4.092 créditos y fútbol gasta ~300/día hasta el reset del 1-nov, así que no se gastó nada. Pendiente: ~330 snapshots h2h/totals de 2024-25 y 2025-26 (~3.300 créditos) tras el reset, decisión del titular.
- Lo que sigue fuera: posiciones, rival/ritmo para jugadores, ritmo de equipo (los box score de equipo con FGA/FTA/TOV solo llegan a 2023 en los repos descargados).
