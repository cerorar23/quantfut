# NBA — props de jugador: modelo v1 contra el mercado (2024-25 y 2025-26)

Protocolo congelado antes de calcular: `apps/nba/nba_props_vs_market_protocol.json` (hash en `apps/nba/.local/normalized/nba_props_market_20261024/protocol_frozen.json`; el programa se niega a correr si cambia). Código: `nba.props_market` (usa la salida de `nba.props_link`). Resultados: `props_market_comparison.json` y `props_blend.json` en esa misma carpeta. Investigación: no genera apuestas, no promueve nada.

## Qué se compara
Probabilidad de «Over» del modelo v1 (binomial negativa + muestra empírica, peso 0,25 elegido en v1.2) **a la línea real** que cotizaron las casas de EE. UU., contra la probabilidad sin margen del mercado (promedio en logit de las casas, una captura 30 min antes del salto). 294.688 unidades (partido, jugador, mercado, línea); se excluyen los jugadores que no jugaron (8.251 filas) y 2.824 unidades sin historial suficiente. El modelo no usa lesiones, rival ni ritmo.

## Resultado (Brier; diferencia = modelo − mercado, positivo = peor el modelo; IC95 por fechas)
| Mercado | 2024-25 | 2025-26 | Peso de información c (2025-26) |
| --- | --- | --- | --- |
| Puntos | +0,0220 [0,019; 0,025] | +0,0214 [0,019; 0,024] | 0,03 [0,00; 0,07] |
| Rebotes | +0,0123 [0,010; 0,014] | +0,0121 [0,010; 0,014] | 0,09 [0,04; 0,14] |
| Asistencias | +0,0127 [0,011; 0,015] | +0,0135 [0,011; 0,015] | 0,01 [−0,05; 0,06] |
| Triples | +0,0092 [0,008; 0,011] | +0,0060 [0,005; 0,008] | 0,17 [0,09; 0,24] |

(`c` = 0 es el mercado, `c` = 1 es el modelo.)

## Lectura
- **El modelo v1 es claramente peor que el mercado en los cuatro mercados y las dos temporadas**: los IC excluyen 0 con holgura. Nadie «es mejor que el mercado» según la regla del protocolo.
- Casi toda la información está en el precio: `c` ≤ 0,17 en todos los casos. Tres mercados no cumplen «añade información». **Rebotes sí cumple la regla literal** (`c` > 0 en ambas temporadas y la mezcla ajustada en 2024-25 mejora a 2025-26: Brier 0,2373 contra 0,2374), pero la mejora es de 0,0001: no tiene valor práctico.
- Consecuencia para el entrenamiento: el modelo base no sirve como predictor autónomo frente a estas líneas. Su papel razonable es **un insumo dentro de un modelo anclado en el mercado** (el logit del mercado más correcciones), no el sustituto del mercado. `props_blend.json` guarda los `c` como prior de investigación (`promoted: false`).
- El mercado tiene sesgo pequeño (+0,01 a +0,02 en la probabilidad de Over) (el del modelo es menor, sobre todo en rebotes): hay margen en calibrar, no en sustituir.

## Límites
Una sola captura temprana (no es cierre); el modelo no usa disponibilidad aunque el mercado la incorpora (parte de la diferencia es información que el mercado ya tenía); casas solo de EE. UU.; 4 mercados × 2 temporadas sin corrección por comparaciones múltiples; el IC de `c` es robusto por fecha (sandwich), no bootstrap.

## Qué sigue
Un modelo de residuo anclado en el logit del mercado, con disponibilidad (v1.3/v1.5), rival y ritmo como variables, entrenado en 2024-25 y evaluado en 2025-26 con el mismo protocolo. Es el uso del archivo que tiene sentido; hay que congelar su protocolo antes de correrlo.
