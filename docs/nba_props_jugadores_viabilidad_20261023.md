# NBA — props de jugador: viabilidad real del histórico (23-oct-2026)

Corrige lo que dije en `docs/nba_comparacion_pinnacle_resultado_20261023.md` («no es viable retrospectivamente, ~144.000 créditos, sin lista verificada de jugadores»). Qué se verificó y cómo: documentación oficial de The Odds API (guía v4, páginas de mercados, casas y precios, consultadas hoy), la sonda real de rebotes del 5-oct (OKC–HOU, 10 créditos) y un cálculo propio sobre esa sonda. No se gastó ningún crédito en esta investigación.

## Resumen
| Afirmación anterior | Estado |
| --- | --- |
| «~144.000 créditos» | **Correcta como cifra** (verificada), **incorrecta como conclusión**: depende del plan, no es inviable. Un mes del plan 5M cuesta **$119**. |
| «No hay lista verificada de quién juega» | **No es el obstáculo.** El mercado define el universo (quien tiene línea) y las casas anulan el prop si el jugador no juega; el emparejado con nuestros IDs funcionó 17 de 17. |
| «Puntos de equipo: no verificado» | `team_totals` existe como mercado adicional por evento (casas de EE. UU.), con histórico desde mayo de 2023; cuesta igual que un prop (10 por snapshot y evento). |
| «Siguen siendo solo investigación» | Sigue siendo cierto, pero por otra razón: lo que falta es construir y correr la comparación, y es probable que el mercado gane. |

## Coste (verificado)
- Histórico por evento: **10 × mercados devueltos × regiones** por llamada; solo cuentan los mercados que devuelven datos. Eventos de un snapshot: 1 crédito. Lo confirma la sonda real: un mercado, una región, un partido = 10.
- Seis mercados (`player_points`, `player_rebounds`, `player_assists`, `player_threes`, `player_steals`, `player_blocks`) en la región `us`: **60 créditos por partido y snapshot**. Con 2.415 partidos (2024-25 y 2025-26): **144.900**; con dos snapshots por partido (T-60 y cierre): 289.800.
- Planes de The Odds API (página de precios, hoy): 20K = $30; 100K = $59; **5M = $119**; 15M = $249, por mes, todos con histórico.
- Con un mes de 5M cabe todo: props (2 snapshots) 289.800 + `team_totals` 48.300 + `totals` y `spreads` de Pinnacle 6.500 ≈ **345.000 créditos**; sobra más del 90 % de la bolsa, también para fútbol. Con 100K ($59) cabrían, por ejemplo, 3 mercados en una sola pasada (72.450).
- Descarga: unas 2.415 llamadas por pasada (~1 hora a 1 por segundo) y ~280 MB. No hay límite de velocidad publicado (solo «espaciar las peticiones» ante un 429).

## Qué hay disponible
- Props históricos desde el **3-may-2023**, snapshots cada 5 min, solo con plan de pago (guía v4). 2023-24 también se podría añadir (+1.225 partidos, +73.500 por pasada).
- **Quién cotiza:** la documentación dice que los props cubren «principalmente casas de EE. UU.» (más sitios DFS: PrizePicks, Underdog, Pick6, Dabble). **Pinnacle está en la región `eu` y no se le atribuye ningún prop de jugador.** La sonda real lo confirma: 8 casas de `us` (DraftKings, FanDuel, BetMGM, Caesars/`williamhill_us`, BetRivers, Bovada, BetOnline, Fanatics) y ninguna Pinnacle. La referencia de mercado sería un **consenso sin margen de varias casas**, no Pinnacle.
- **Alternativas de pago** (no verificadas más allá de sus páginas): DunkAPI (planes de $19, $49 y $149 al mes; dice tener «closing prop lines by sportsbook since May 2023» con el resultado de cada línea, una sola captura previa al partido por línea hasta octubre de 2026; uso comercial dentro del propio modelo permitido); SportsDataIO (venta por contacto, descarga masiva en S3, props «desde 2020», precio no público). No encontré ningún conjunto gratuito. The Odds API tiene la ventaja de entregar instantáneas con hora (punto en el tiempo) en el mismo formato que ya usamos.

## El universo de jugadores
- **Retrospectivo:** el universo es «jugadores con línea en el snapshot de T-60 que jugaron». La mayoría de casas anulan el prop si el jugador no juega, así que se compara condicionado a participar, que es exactamente lo que modela v1.x. Hay que confirmar la regla de cada casa antes del protocolo.
- **Prospectivo:** igual: capturar el feed de props al sellar (≈6 créditos por partido, unos 60 por noche) y pronosticar solo a los jugadores que ya tienen línea, con el historial que tenemos. Quedan fuera los de menos de 10 apariciones (novatos) y los traspasados sin equipo confirmado.
- **Prueba con datos reales** (sonda OKC–HOU, rebotes): 17 de 17 nombres emparejan con nuestro histórico y los 17 tienen ≥10 apariciones.

## Lo que ya sugiere la sonda (un partido, n = 17: anecdótico, solo orienta)
- Las probabilidades de «más de» del mercado, sin margen y en consenso, se concentran en **0,503 ± 0,055**: las líneas se ponen en la mediana, así que hay poco margen para distinguirse y toda la información está en pequeñas desviaciones.
- El modelo (con su calibración de RUN071) da 0,530 ± 0,088 y **correlaciona solo 0,47** con el mercado; sin calibrar, la diferencia media es de 12 puntos y el modelo es sistemáticamente más alto. Es coherente con que le faltan emparejamiento, ritmo, uso y rol, y con la sobreconfianza ya medida (en puntos, el filtro ≥70 % acertaba 65 %).
- Expectativa razonable: **el mercado gana**, como en el ganador. Pero solo una muestra grande lo dirá, y las propiedades del error (dónde falla el modelo) son útiles para mejorarlo.

## Propuesta por fases (para decidir)
1. **Prueba barata:** 100 partidos al azar × 2 mercados (puntos, rebotes) en un snapshot = **2.000 créditos**. Valida el flujo completo y da una primera cifra, con barras de error anchas. Antes, 10 créditos de sonda sobre un partido de 2024-25 para confirmar que el histórico llega a esa temporada.
2. **Retrospectivo completo** con un mes de 5M ($119): seis mercados, dos snapshots, `team_totals`, `totals` y `spreads` de Pinnacle (≈345.000 créditos). Con protocolo congelado **antes** de comprar, como en el ganador.
3. **Prospectivo:** captura de props al sellar cada cohorte y comparación sobre pronósticos ya sellados.

Código nuevo necesario (no existe): descarga por evento con caché y topes; emparejado de nombres a IDs; probabilidad de «más de» a la línea de cada casa a partir de la distribución del modelo (`player_distribution`); consenso sin margen; Brier, log loss y peso de información por mercado con bootstrap por fechas; tratamiento de líneas distintas entre casas y de líneas alternativas. Más el protocolo.

## Límites y riesgos
- El consenso de casas de EE. UU. no es Pinnacle: es una referencia distinta (menos afilada en la línea, más margen).
- Las líneas de las casas difieren; se usa la línea modal y se descartan jugadores con una sola casa en el protocolo, o se pondera por número de casas.
- Los sitios DFS (multiplicadores) y las líneas alternativas quedan fuera.
- Instantánea de T-60 frente a cierre: igual que en el ganador, el cierre es más afilado.
- Datos de terceros: respetar los términos (uso propio del modelo; no revender).
