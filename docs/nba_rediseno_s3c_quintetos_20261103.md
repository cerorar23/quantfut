# S3c — Impacto por jugador con tramos de quinteto (RAPM) · 3-nov-2026

**Pregunta:** ¿mejora el modelo de jugadores (S3b) si el a priori del impacto sale de tramos de quinteto en vez del más/menos del partido?

**Datos:** 186.325 tramos de 6.131 partidos 2021-26 (`nba_pending_rotations_v6` + marcador de la jugada a jugada `nbastatsv3_*` de shufinskiy/nba_data en `.local/raw`). Control: la suma de cambios de margen de los tramos iguala el margen final en el 99,85 % de los partidos. Tramos de `ops/preparar_stints_s3c.py`; ajuste y comparación con `ops/evaluar_s3c.py` (todo igual a S3b salvo el a priori: ridge ponderado por duración, solo tramos anteriores al corte, decaimiento 730 o 1.500 días).

**Resultado (temporada de prueba 2025-26, n = 1.269 con cuota; hiperparámetros elegidos solo con temporadas anteriores):**

| Variante | RMSE margen antes → después | Brier ganador antes → después |
|---|---|---|
| jugadores solos | 14,380 → 14,342 (lam 10) | 0,2050 → 0,2040 |
| media equipo + jugadores (la del motor 2.1) | 14,329 → 14,289 | 0,2035 → 0,2026 |
| mercado (referencia) | 14,036 | 0,1981 |

Prueba pareada del error cuadrático (1.321 partidos): media equipo + jugadores z = 3,1 a 3,4 en las tres configuraciones probadas; jugadores solos z = 1,0 a 2,2. Mejora real pero pequeña (≈ 0,7 % del MSE); la distancia al mercado (≈ 0,25 de RMSE; Brier +0,0045) sigue casi igual. El total no cambia.

**Conclusión:** los quintetos ayudan un poco y de forma consistente, no cierran la brecha con el mercado. Reentrenar el motor con esto es una decisión del titular; exigiría reajustar `impacto.json` con el a priori RAPM, repetir G-fuga y publicar imagen. No se tocó producción.

**Hallazgo lateral:** la jugada a jugada histórica 2021-26 (con coordenadas en `shotdetail_*`) existe en `.local/raw/github/shufinskiy__nba_data/.../datasets` y NO está en `nba.evento`.

## Reentrenamiento (3-nov-2026, commit 5507291)

`impacto.json` reentrenado con `ops/entrenar_impacto.py … stints.pkl 10 730 0,6 20` (a priori RAPM λ=10, vida 730 d, c=0,6; ridge λ=20; 6.692 partidos, 1.083 jugadores, datos hasta 2026-11-02). El mismo script sin a priori reproduce exactamente el artefacto anterior (c_margen 1,87405, σ 14,0574), así que los datos son los mismos. Validación hacia adelante 2023-24 y 2024-25 (n = 2.638; ojo: son las temporadas con las que se eligieron los hiperparámetros, la prueba limpia es 2025-26 de arriba): RMSE del margen de la mezcla 14,0574 → 13,9908, σ del margen 14,0574 → 13,9908 (la usa el motor al simular). El total no se usa del modelo de jugadores. Anterior guardado en el scratchpad de la sesión como `impacto_anterior_3nov.json` (también está en git, commit previo). 291 pruebas v2 pasan. G-fuga en el VPS (imagen `nba-motor:6b85093`, que lleva este artefacto más el F4.2 de otra sesión): aprobada, 0 diferencias de repetibilidad, 0 fugas, Brier ganador 0,2299 sin alarma, 60 mezclas 2.1 con 0 violaciones de contrato. **Producción sin cambios:** el cron sigue con `imagen_motor` = `nba-motor:233e372` (artefacto anterior).
