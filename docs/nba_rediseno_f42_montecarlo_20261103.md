# NBA v2 — Fase 4, F4.2: Monte Carlo (2026-11-03)

Qué se simula y qué no: **solo el marcador del equipo** (margen y total normales independientes, 199 cuantiles por serie). Los props no usan Monte Carlo: su distribución es una mezcla binomial negativa calculada de forma analítica sobre 25 muestras de minutos, es determinista y no tiene error de simulación. Scripts: `ops/f42_montecarlo.py` y `ops/f42_correlacion_props.py`.

## 1. Convergencia (200 partidos reales de 2025-26 × 20 semillas por tamaño; referencia de 2.000.000 simulaciones con otra semilla)

| Simulaciones | p(gana el local) | P(total más de línea) | P(local cubre −3,5) | Cuantiles 10/90 % (puntos) |
|---|---|---|---|---|
| 1.000 | 1,14 pp · p99 3,80 | 1,26 pp · p99 3,95 | 1,15 pp · p99 3,83 | 0,70 · p99 2,00 |
| 5.000 | 0,51 pp · p99 1,75 | 0,57 pp · p99 1,87 | 0,52 pp · p99 1,68 | 0,32 · p99 1,00 |
| **20.000 (hasta hoy)** | 0,26 pp · p99 0,86 | 0,28 pp · p99 0,94 | 0,25 pp · p99 0,85 | 0,16 · p99 1,00 |
| **100.000 (desde hoy)** | 0,12 pp · p99 0,39 | 0,13 pp · p99 0,43 | 0,12 pp · p99 0,40 | 0,07 · p99 1,00 |

(error absoluto medio y percentil 99; el error típico teórico de una probabilidad de 50 % es 0,35 pp con 20.000 y 0,16 pp con 100.000.)

**Compuerta «error de Monte Carlo < 0,5 pp»**: con 20.000 se cumple en el error medio (0,26 pp) pero no en el 1 % peor (0,86 pp); con 100.000 se cumple también en ese extremo (0,43 pp como máximo). El coste es 0,9 ms → 5,7 ms por partido. **Decisión: el motor de equipo simula 100.000** (`N_SIM`; el número va en `version_modelo`, `…;n=100000;…`). El error de los cuantiles de ±1 punto es el de los marcadores enteros y no baja con más simulaciones.

## 2. Semillas
La semilla es el id del partido: el mismo partido siempre se simula igual y partidos distintos usan flujos distintos. Los flujos de semillas consecutivas (los id de partido lo son) no se correlacionan: correlación media −0,0012 y máximo |r| = 0,019 con 100 pares de 20.000 muestras (lo esperable por azar es ≈ ±0,007 de desviación).

## 3. Reproducibilidad entre máquinas
Con la misma versión de numpy (2.1.3, fijada en las imágenes), el sha256 de las muestras de 4 casos fijos (medias y semillas distintas, incluida la semilla máxima de 32 bits) es **idéntico bit a bit entre Windows (PC de entrenamiento) y Linux (contenedor del VPS)**. Cambiar la versión de numpy podría cambiar las muestras: por eso la versión está fijada y el script `huella` sirve de prueba al actualizarla.

## 4. ¿Hace falta simular los props junto con el resultado?
Medido en 28.181 filas jugador-partido de 2025-26: el error de un prop se mueve junto con el del partido. Correlación con el error del total: puntos +0,13, asistencias +0,10, triples +0,10, rebotes −0,05; con lo desigual que resultó el partido (|margen real|), en titulares (≥ 28 minutos esperados) −0,13 en puntos y rebotes (en los blowouts juegan menos). En términos prácticos: P(jugador anota más de lo esperado Y el total supera lo esperado) = 0,243 observada frente a 0,224 si fueran independientes (+8 % relativo).
**Qué implica:** cada probabilidad por separado (la que se sella y se muestra) es correcta; una probabilidad **conjunta** de prop y partido (combinaciones) no se puede obtener multiplicando. Hoy el producto no ofrece combinaciones de NBA, así que **no se simula de forma conjunta**; si se quisieran, la dependencia medida es el punto de partida (una cópula con correlación ≈ +0,1 con el total y −0,1 con el margen absoluto en titulares) y habría que evaluarla.

## 5. Pruebas y despliegue
- Las pruebas de v2 siguen en verde con 100.000 simulaciones. G-fuga en el VPS (solo lectura): 100 partidos de equipo y 60 de jugadores, 0 diferencias de repetibilidad, 0 fugas, 0 violaciones de contrato en 5.852 distribuciones, mezcla 2.1 en los 60 partidos (aprobada).
- `imagen_motor` = `nba-motor:6b85093` desde las 15:35 UTC; el tick de las 15:40 sin errores. Anterior: `imagen_motor.anterior` (`nba-motor:233e372`). Los sellos existentes (20.000 simulaciones) no se tocan; los nuevos llevan `n=100000` en su versión.
