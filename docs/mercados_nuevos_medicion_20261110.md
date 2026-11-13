# Mercados nuevos de NBA y tenis: medición (10-nov-2026)

Código: `src/qf/eval/mercados_nuevos.py` (extraer en el VPS en un contenedor aparte, sin red y de solo lectura; medir en local).
Datos: archivo PropLine 24-oct a 10-nov-2026; 125 partidos NBA y ~450 de tenis con foto de las 10 UTC (la que ve el lote diario).
Probabilidad = consenso de casas sin margen (`referencia.probabilidades`). Intervalos al 95 % remuestreando partidos.

## Qué se midió y qué no
- Hueco = acierto − p prometida. Walk-forward purgado (5 bloques, embargo 1 día) para comparar mercado, calibración Beta y Venn-Abers.
- NO se mide `h2h` de tenis (PropLine lo califica mal) ni aces/dobles faltas (solo casas de fantasía, 17 y 4 eventos).
- Se descartaron dos pasadas por errores propios: usar la cuota que acompaña a la calificación (se mueve en juego: +20 pp falsos) y emparejar mal nombres de equipo (se perdían hándicap, ganador y props).

## Resultados (foto 10 UTC, cualquier casa)
| Mercado | Banda escalera (p≥0,69, cuota 1,25–2,10) | Conclusión |
|---|---|---|
| NBA hándicap partido | n=1082, 125 partidos, +0,3 pp (−3,6 a +4,5) | cumple |
| NBA total partido | n=1457, 125 partidos, +0,0 pp (−3,8 a +4,5) | cumple |
| NBA total de equipo | n=1676, 124 partidos, −1,0 pp (−4,2 a +2,3) | cumple |
| NBA hándicap de periodos | n=780, 65 partidos, +0,7 pp | cumple, poca muestra |
| NBA total de periodos | n=725, 65 partidos, −3,5 pp (−7,9 a +1,6) | sobreestima; no usar en escalera |
| Tenis hándicap de juegos | n=440, 249 partidos, +2,0 pp (−2,1 a +6,1) | cumple |
| Tenis total de juegos | n=898, 319 partidos, +2,7 pp (−0,8 a +6,3) | cumple |
| NBA props (todas) | sin filas con p≥0,69 | solo sirven en parley (bandas 1,20–2,10: hueco −0,5 a +1,1 pp, todos con IC que incluye 0) |
Rendimiento en cuotas de cualquier casa ≈ −4 a 0 % (IC incluye 0 en la banda de escalera): no hay ventaja sobre el mercado, solo calibración.

## Calibración
Beta y Venn-Abers no mejoran al mercado en ninguna familia (Δ log-loss entre −0,0003 y +0,008; ninguna mejora con IC por debajo de 0). ECE del mercado 0,006–0,021. No se promueve ningún calibrador.

## Limitación decisiva
Con las casas de `SOFT_BOOKS` casi no hay cuota: 0 props de NBA y 0 total de juegos de tenis para jugador, ~10 % de los contratos de tenis y ~25 % de los totales de NBA. Los hándicap y totales de partido NBA sí las tienen (3.352 y 3.756 filas). Añadir props exige decidir qué casas cuentan como cobrables.
