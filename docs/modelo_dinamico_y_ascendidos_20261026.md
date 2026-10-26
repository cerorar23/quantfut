# Modelo dinámico y prior de ascendidos (26-oct-2026)

Pedido del titular: probar el modelo dinámico (Koopman y Lit, 2015) y un prior para ascendidos sobre el modelo `2026.10.26-020600`.
Todo se midió **en local** (`scripts/entrenamiento_local/mediciones/`), con un walk-forward de **3 años** (12.878 partidos, 13
competiciones, reajuste cada 30 días, misma configuración que el worker) para tener potencia. Las combinaciones se eligen en los
dos primeros años y se evalúan en el tercero, que es el año de la puerta de producción. **Nada de esto cambia producción.**

## 1. Prior de ascendidos: no pasa

Se marcó, solo con datos anteriores al partido, a los equipos en el primer tramo tras un hueco de más de 270 días sin partidos
(ascenso o regreso): 1.924 de los 12.878 partidos tienen alguno.

| Grupo | Partidos | RPS | Goles local / λ | Goles visita / μ | Empate previsto / real |
|---|---:|---:|---:|---:|---:|
| Ningún ascendido | 10.954 | 0,2050 | 1,015 | 1,034 | 0,256 / 0,262 |
| Local ascendido | 911 | 0,2110 | 0,963 | 1,040 | 0,265 / 0,267 |
| Visitante ascendido | 923 | 0,1783 | 1,001 | 1,003 | 0,237 / 0,251 |

Una corrección multiplicativa de λ y μ para el ascendido (ataque `a`, defensa `d`, desvaneciéndose con los partidos jugados),
ajustada por validación cruzada de bloques anuales: **ΔRPS −0,00002 en total (p95 +0,00002)** y −0,0001 a −0,0002 sobre los 1.924
afectados, sin significancia. Los coeficientes cambian de signo entre bloques (`a` de −0,14 a +0,02). El sesgo que se veía en el
último año (empates 29,9 % reales frente a 24,6 % previstos) era ruido de muestra pequeña: con tres años desaparece. La suma cero
ponderada y el ridge en partidos equivalentes (22-oct) ya hacen lo que un prior haría. **No se implementa.**

## 2. Modelo dinámico

### Kalman tal como está en el repo (`qf.model.kalman`)

Sin fuga de los parámetros de liga (se reestiman cada 30 días con lo anterior; el original usa todo el histórico), RPS fuera de
muestra frente al DC 270 (0,20348 en los 3 años, 0,20615 en el último):

| Variante | RPS 3 años | Δ vs DC | RPS último año | Δ vs DC (p95) |
|---|---:|---:|---:|---:|
| Por defecto (varianza 2,5e-4, reversión 1e-3) | 0,20467 | +0,0012 | 0,20791 | +0,0018 (+0,0028) |
| Sin reversión, varianza 1e-4 | 0,20322 | −0,0003 | 0,20635 | +0,0002 (+0,0010) |
| Sin reversión, varianza 3e-5 | 0,20324 | −0,0002 | 0,20553 | −0,0006 (+0,0000) |
| Sin reversión, varianza 1e-5 | 0,20408 | +0,0006 | 0,20578 | −0,0004 (+0,0005) |

La reversión diaria a la media de liga empeora (la fuerza de un equipo no revierte en semanas) y la varianza de proceso buena es
~5 veces menor que la que traía. Con eso el Kalman **empata** con el Dixon-Coles; solo no lo supera de forma significativa.

### La mezcla sí aporta algo pequeño

Mezcla log-lineal de λ y μ de cuatro modelos: DC con media vida 270, 90 y 730 días, y el Kalman (sin reversión, varianza 1e-4,
varianza inicial 0,1). Pesos ajustados solo con los dos primeros años: DC270 −0,135, DC90 0,116, DC730 0,466, Kalman 0,553.

| Periodo | n | RPS DC270 | RPS mezcla | ΔRPS | p95 | Δ log-loss | Brecha con el mercado |
|---|---:|---:|---:|---:|---:|---:|---|
| Año 1 | 4.242 | 0,20056 | 0,19956 | −0,00100 | −0,00062 | −0,0032 | +0,0078 → +0,0068 |
| Año 2 | 4.372 | 0,20370 | 0,20371 | +0,00001 | +0,00048 | −0,0003 | +0,0044 → +0,0044 |
| **Año 3 (fuera de muestra)** | 4.264 | 0,20615 | 0,20536 | **−0,00079** | **−0,00026** | −0,0023 | +0,0087 → +0,0077 |
| 3 años | 12.878 | 0,20348 | 0,20289 | −0,00059 | −0,00033 | −0,0019 | +0,0066 → +0,0060 |

- ECE del 1X2 en el año 3: 0,0151 → 0,0081 (3 años: 0,0101 → 0,0098). Mejora 9 de 13 competiciones.
- **Las copas empeoran** (Champions +0,0026, Europa League +0,0027): el Kalman no tiene el término de fuerza entre ligas del DC.
  Solo en los 4.115 partidos domésticos: **ΔRPS −0,00091 (p95 −0,00040)**.
- Una segunda configuración (varianza 3e-5) da lo mismo: −0,00065 en el año 3, −0,00042 en 3 años.
- Los pesos no son robustos por sí solos: el 50/50 simple de DC270 y Kalman da −0,0002 en el año 3 y no es significativo. Lo
  significativo es la mezcla de cuatro, que además usa un peso negativo en el DC 270 (extrapolación).
- **No es constante:** el año 2 queda en cero. De tres años, la mejora aparece en dos.
- Efecto sobre el hueco con el mercado (0,0096 en el año de producción): ~0,0008, un 8 %.

### Se suma al contexto

Repetida la puerta de contexto con la base mezclada: altitud + impacto del once siguen pasando en las cuatro particiones
(−0,0007 a −0,0010, 10-12 de 13 ligas). Mezcla + contexto ≈ −0,0017 de RPS, un 18 % del hueco.

## Conclusión y coste

- Prior de ascendidos: descartado, sin señal.
- Modelo dinámico: el Kalman solo no mejora; la mezcla con DC a varias medias vidas da **−0,0008 (año de producción), −0,0006
  (3 años)**, significativa, con mejor calibración, pero inestable por año y solo en partidos domésticos.
- **Llevarlo a producción exige** un estado de Kalman persistente que se actualice cada día con los resultados, tres Dixon-Coles
  entrenados en local (270, 90 y 730) y una regla para las copas (usar el DC). Es una arquitectura nueva por ~0,0008 de RPS. No se
  hace sin decisión del titular.
- Reproducir: `wf.py` (walk-forward largo), `kalman_var.py` (Kalman sin fuga), `dinamico.py` (comparación y mezclas),
  `dinamico_puerta.py` (puerta completa con la mezcla elegida) y `ascendidos.py`.
