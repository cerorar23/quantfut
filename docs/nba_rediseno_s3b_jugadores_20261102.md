# NBA v2 — Sprint 3b: jugadores dentro del núcleo (2026-11-02)

Biblioteca `nba.v2.plantilla` (impacto por jugador + minutos esperados de la plantilla); evaluación reproducible con
`apps/nba/ops/evaluar_s3b.py`. Misma prueba que el Sprint 3: 2025-26 hacia adelante contra el cierre de bet365. Hiperparámetros,
tablas de probabilidad de jugar y desviaciones se fijaron solo con temporadas anteriores (validación: 2023-24 y 2024-25).

## Qué se construyó

- **Impacto por jugador:** cada jugador aporta `beta · minutos / 48` al margen de su equipo y `tau · minutos / 48` al total. Se estima con
  mínimos cuadrados ponderados y ridge hacia 0 (= nivel de reemplazo), peso con vida media de 730 días, reajustado cada 21 días solo con
  partidos anteriores. Intercepto (localía) y covariable de descanso sin penalizar. Ridge elegido en validación: λ = 10.
- **Minutos esperados de un partido:** candidatos = quienes jugaron con el equipo en sus últimos 10 partidos o aparecen en el parte y su
  último equipo es este; minutos si juega con el modelo del Sprint 2 (decaimiento 0,70); probabilidad de jugar según el último parte oficial
  o, sin parte, según su tramo de minutos; todo reescalado a los 240 minutos del equipo (lo que no juega un ausente se reparte en proporción).
- **Probabilidad de jugar medida con candidatos reales (2021-23):** Out 0,3 %; Doubtful 3 %; Questionable 51 %; Available 75 %; Probable 91 %.
  Sin parte: 53 % con menos de 15 minutos esperados, 88 % entre 15 y 25, 98 % con 25 o más. Esto resuelve el pendiente del S2 de condicionar
  «sin parte» al rol: el 84 % global mezclaba titulares seguros con jugadores de fondo.
- **Dato nuevo en la base:** `equipo_del_jugador` (migración 0008, métrica 60). La caja por jugador no guardaba con qué equipo figuraba cada uno
  en cada partido y no se deduce sin ambigüedad (traspasos, ids por nombre). Los cargadores histórico y cdn.nba.com ya lo escriben.

## Resultados 2025-26

Con cierre de bet365: ganador n = 1.269, hándicap n = 1.126, total n = 1.113. Brier: ganador / hándicap / total.

| Variante | RMSE margen | RMSE total | Brier ganador | Brier hándicap | Brier total |
|---|---|---|---|---|---|
| Cierre bet365 (referencia) | 14,04 | 18,41 | 0,1981 | 0,2499 | 0,2500 |
| Núcleo de equipo (S3) | 14,49 | 19,12 | 0,2063 | 0,2597 | 0,2605 |
| Jugadores | 14,37 | 19,46 | 0,2051 | 0,2564 | 0,2631 |
| Jugadores con minutos reales (techo) | 14,30 | 19,24 | 0,2038 | 0,2539 | 0,2600 |
| Margen: media de equipo y jugadores; total del equipo | 14,32 | 19,12 | 0,2038 | 0,2559 | 0,2611 |
| **Media de equipo y jugadores (margen y total)** | **14,32** | **19,03** | **0,2038** | **0,2560** | **0,2580** |

- Los jugadores bajan el error del margen de 14,49 a 14,37 (14,32 promediados con el equipo) y el Brier del ganador en 0,0025–0,0045: mejora real
  pero pequeña. Para el total, la regresión de jugadores es peor que el rating de equipo (19,46 frente a 19,12) y solo la media de los dos mejora.
- **El tope no son los minutos:** con los minutos reales del partido (información que no se tiene antes) el error solo baja a 14,30. Predecir bien
  quién juega ya no es el cuello de botella; lo es lo que se sabe de cada jugador.
- **G-equipo sigue sin cumplirse contra el mercado:** el Brier del ganador queda +0,006 por encima del cierre con IC95 [+0,001, +0,010] sin cruzar 0. En validación
  los pesos de mínimos cuadrados para el margen son 0,19 (jugadores), −0,08 (equipo) y 0,96 (mercado). La pendiente de calibración del ganador es 1,14:
  la probabilidad es algo tímida; se recalibra en S5 con la evaluación única, no aquí.
- Cubrir el hándicap y superar el total siguen sin discriminar (pendientes 0,14 y 0,12): el modelo no aporta información que la línea no tenga.

## Decisiones

- El núcleo v2 usa la **media de equipo y jugadores** para margen y total: es la variante con mejor Brier en las tres decisiones y la menos expuesta a un
  rating que no vio a un jugador nuevo.
- No se inventa una ventaja: tal como pide el titular, el objetivo es probabilidad calibrada con el mercado solo como referencia; este sprint la mejora un poco.
- Siguiente palanca medible: un a priori informativo para el impacto de cada jugador (producción por minuto de la caja, `mas_menos` por 48, edad de
  la muestra) en lugar de centrar el ridge en 0, y los titulares confirmados cerca del salto (Rotowire y `titular` de cdn.nba.com, que solo existen
  hacia adelante). Con 5 temporadas de cajas el primero se puede probar ya; el segundo necesita temporadas acumuladas.

## Límites

- Los partes históricos se leen como «último parte del partido»; se asume anterior al salto (los partes oficiales lo son), no se comprobó hora por hora.
- Las tablas de probabilidad de jugar se midieron con 2021-23 y se aplican a validación y prueba; cambian de significado con los años y hay que remedirlas cada temporada.
- Jugadores sin historial reciente (novatos, regresos largos) entran con impacto 0 y minutos por su media previa.
